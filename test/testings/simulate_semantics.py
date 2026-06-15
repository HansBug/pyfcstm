"""
Shared helpers for simulate semantic fixture tests.

This module loads YAML/FCSTM semantic fixtures from
``test/fixtures/simulate_semantics`` and runs them against
:class:`pyfcstm.simulate.SimulationRuntime`, the generated Python alignment
runtime, or the simulate command processor. It owns the strict fixture schema,
runtime assertion helpers, and callback fixtures used by Python-side simulation
tests.

The module contains:

* :class:`SemanticCase` - Loaded fixture data and source paths.
* :class:`SemanticCaseError` - Schema and fixture-shape diagnostics.
* :func:`load_semantic_case` - Load one fixture by id or YAML path.
* :func:`iter_semantic_cases` - Enumerate fixture cases with optional filters.
* :func:`validate_pure_shared_fixture_boundary` - Check the stricter boundary
  for new cross-runtime shared fixtures.
* :func:`run_simulation_case` - Execute one case against
  :class:`pyfcstm.simulate.SimulationRuntime`.
* :func:`run_cli_command_case` - Execute one CLI-command fixture.

Example::

    >>> case = load_semantic_case("design_basic_simple_transition")
    >>> case.id
    'design_basic_simple_transition'
"""

import importlib.util
import logging
import os
import re
import warnings
from contextlib import contextmanager
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.simulate import (
    CycleResult,
    SimulationRuntime,
    SimulationRuntimeDfsError,
    SimulationRuntimeEventError,
    SimulationRuntimeExpressionError,
)
from pyfcstm.template import extract_template
from pyfcstm.utils.validate import ModelValidationError


FIXTURE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "fixtures", "simulate_semantics")
)
CASE_DIR = os.path.join(FIXTURE_ROOT, "cases")
_ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "id",
    "title",
    "boundary",
    "source",
    "origin",
    "categories",
    "runners",
    "initial",
    "runtime_options",
    "model_build",
    "steps",
    "commands",
    "handlers",
    "expected_failure",
}
_ALLOWED_SOURCE_FIELDS = {"fcstm"}
_ALLOWED_ORIGIN_FIELDS = {"files", "docs", "assertion_types", "notes"}
_ALLOWED_CATEGORIES = {
    "runtime",
    "template_alignment",
    "design_example",
    "scenario_example",
    "hot_start",
    "cli",
    "event_paths",
    "temporary_vars",
    "if_blocks",
    "abstract",
    "pseudo_chain",
    "validation",
    "lifecycle",
}
_ALLOWED_RUNNERS = {"simulation", "generated_python_alignment", "cli_command"}
_PURE_SHARED_BOUNDARY = "pure_shared"
_ALLOWED_BOUNDARIES = {_PURE_SHARED_BOUNDARY}
_ALLOWED_STACK_MODES = {"active", "init_wait"}
_ALLOWED_EXPECT_FIELDS = {
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "stack",
    "cycle_count",
    "return",
    "cycle_result",
    "history",
    "history_length",
    "history_tail",
    "raises",
    "logs",
    "warnings",
    "handler_calls",
    "abstract_handler_errors",
    "error_state",
    "error_info",
    "anonymous_warning_count",
}
_ALLOWED_INITIAL_EXPECT_FIELDS = {
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "stack",
}
_ALLOWED_CLI_EXPECT_FIELDS = {
    "output_contains",
    "output_not_contains",
    "error_contains",
    "should_exit",
    "runtime",
}
_ALLOWED_CLI_RUNTIME_FIELDS = {
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "stack",
    "cycle_count",
}
_ALLOWED_INITIAL_FIELDS = {"state", "vars", "expect"}
_ALLOWED_INITIAL_CONSTRUCTOR_EXPECT_FIELDS = {"raises"}
_ALLOWED_CYCLE_FIELDS = {"events"}
_ALLOWED_MODEL_BUILD_FIELDS = {"expect"}
_ALLOWED_MODEL_BUILD_EXPECT_FIELDS = {"raises"}
_ALLOWED_STACK_FIELDS = {"path", "mode"}
_ALLOWED_RAISES_FIELDS = {
    "type",
    "match",
    "match_kind",
    "cause_type",
    "cause_match",
    "cause_match_kind",
}
_ALLOWED_LOG_FIELDS = {"contains", "not_contains"}
_ALLOWED_LOG_ITEM_FIELDS = {"level", "message", "match_kind"}
_ALLOWED_RUNTIME_OPTION_FIELDS = {"abstract_error_mode"}
_ALLOWED_ABSTRACT_ERROR_MODES = {"raise", "log"}
_ALLOWED_HANDLER_FIELDS = {"action", "behavior", "exception", "write"}
_ALLOWED_HANDLER_BEHAVIORS = {"record_call", "raise_error", "record_var_write_attempt"}
_ALLOWED_HANDLER_EXCEPTION_FIELDS = {"type", "message"}
_ALLOWED_HANDLER_EXCEPTION_TYPES = {"ValueError"}
_ALLOWED_HANDLER_WRITE_FIELDS = {"name", "value"}
_ALLOWED_WARNING_FIELDS = {"contains", "not_contains", "count"}
_ALLOWED_WARNING_ITEM_FIELDS = {"category", "message", "match_kind"}
_ALLOWED_WARNING_CATEGORIES = {"UserWarning"}
_REQUIRED_HANDLER_CALL_FIELDS = {"action", "state", "stage", "vars"}
_ALLOWED_HANDLER_CALL_FIELDS = _REQUIRED_HANDLER_CALL_FIELDS | {
    "active_leaf",
    "call_stage",
    "abstract_target",
    "named_ref",
    "write_attempt",
}
_ALLOWED_WRITE_ATTEMPT_FIELDS = {"name", "value", "succeeded", "error_type", "vars"}
_ALLOWED_ABSTRACT_HANDLER_ERROR_FIELDS = {"action", "type", "message", "match_kind"}
_ALLOWED_ERROR_INFO_FIELDS = {"action", "type", "message", "match_kind"}
_ALLOWED_CYCLE_RESULT_FIELDS = {
    "value",
    "input_events",
    "consumed_events",
    "unconsumed_events",
}
_PURE_SHARED_REQUIRED_RUNNERS = {"simulation", "generated_python_alignment"}
_PURE_SHARED_FORBIDDEN_TOP_LEVEL_FIELDS = {
    "runtime_options",
    "model_build",
    "commands",
    "expected_failure",
}
_PURE_SHARED_FORBIDDEN_EXPECT_FIELDS = {
    "stack",
    "brief_stack",
    "cycle_count",
    "return",
    "history",
    "history_length",
    "history_tail",
    "logs",
    "warnings",
    "abstract_handler_errors",
    "error_state",
    "error_info",
    "anonymous_warning_count",
}
_PURE_SHARED_HANDLER_BEHAVIORS = {"record_call"}
_PURE_SHARED_PUBLIC_EXPECT_FIELDS = {
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "raises",
    "cycle_result",
    "handler_calls",
}
_ALLOWED_HISTORY_FIELDS = {"cycle", "state", "vars", "events"}
_REQUIRED_HISTORY_FIELDS = _ALLOWED_HISTORY_FIELDS
_CLI_OUTPUT_FIELDS = ("output_contains", "output_not_contains", "error_contains")
_EXCEPTION_TYPES = {
    "ModelValidationError": ModelValidationError,
    "SimulationRuntimeDfsError": SimulationRuntimeDfsError,
    "SimulationRuntimeEventError": SimulationRuntimeEventError,
    "SimulationRuntimeExpressionError": SimulationRuntimeExpressionError,
    "ValueError": ValueError,
}
_ALIGNMENT_CONSTRUCTOR_EXCEPTION_TYPES = (
    ValueError,
    ArithmeticError,
    SimulationRuntimeDfsError,
    TypeError,
    KeyError,
)
_ALIGNMENT_CONSTRUCTOR_EXCEPTION_TYPE_NAMES = {
    item.__name__ for item in _ALIGNMENT_CONSTRUCTOR_EXCEPTION_TYPES
}
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class SemanticCaseError(ValueError):
    """
    Raised when a semantic fixture is malformed.

    The exception message includes the fixture case id and YAML path whenever
    that information is available, so loader failures can be traced back to the
    source fixture without inspecting the pytest parameter id.

    :param args: Positional message arguments accepted by
        :class:`ValueError`.
    :type args: object

    Example::

        >>> err = SemanticCaseError("sample (/tmp/sample.yaml): bad field")
        >>> "sample" in str(err)
        True
    """


@dataclass(frozen=True)
class SemanticCase:
    """
    Loaded simulate semantic fixture.

    A semantic case bundles the parsed YAML metadata, source file locations, and
    FCSTM DSL text needed by fixture runners. The object is immutable so tests
    can safely reuse it across parametrized simulation, generated-runtime
    alignment, and CLI-command runners.

    :param data: Parsed fixture YAML mapping.
    :type data: typing.Mapping[str, typing.Any]
    :param yaml_path: Absolute path to the fixture YAML file.
    :type yaml_path: str
    :param fcstm_path: Absolute path to the paired FCSTM source file.
    :type fcstm_path: str
    :param dsl_code: FCSTM DSL source text.
    :type dsl_code: str

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.id
        'design_basic_simple_transition'
    """

    data: Mapping[str, Any]
    yaml_path: str
    fcstm_path: str
    dsl_code: str

    @property
    def id(self) -> str:
        return str(self.data["id"])

    @property
    def runners(self) -> Sequence[str]:
        return tuple(self.data["runners"])


def _case_error(case_id: str, yaml_path: str, message: str) -> SemanticCaseError:
    return SemanticCaseError("%s (%s): %s" % (case_id, yaml_path, message))


def _as_tuple_path(
    value: Any, case: SemanticCase, field_path: str
) -> Optional[Tuple[str, ...]]:
    if value is None:
        return None
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s must be a list of path segments or null" % field_path,
        )
    return tuple(value)


def _normalize_stack(
    value: Any, case: SemanticCase, field_path: str
) -> List[Tuple[Tuple[str, ...], str]]:
    if not isinstance(value, list):
        raise _case_error(case.id, case.yaml_path, "%s must be a list" % field_path)
    result = []
    for index, item in enumerate(value):
        if not isinstance(item, dict):
            raise _case_error(
                case.id,
                case.yaml_path,
                "%s[%d] must be a mapping" % (field_path, index),
            )
        if "path" not in item or item.get("path") is None:
            raise _case_error(
                case.id, case.yaml_path, "%s[%d].path is required" % (field_path, index)
            )
        path = _as_tuple_path(
            item.get("path"), case, "%s[%d].path" % (field_path, index)
        )
        mode = item.get("mode")
        if mode not in _ALLOWED_STACK_MODES:
            raise _case_error(
                case.id,
                case.yaml_path,
                "%s[%d].mode is invalid: %r" % (field_path, index, mode),
            )
        result.append((path, mode))
    return result


def _vars_dict(runtime: Any) -> Dict[str, Any]:
    return dict(runtime.vars)


def _runtime_state_path(runtime: Any) -> Optional[Tuple[str, ...]]:
    if getattr(runtime, "is_ended"):
        return None
    current_state = getattr(runtime, "current_state")
    if current_state is None:
        return None
    return tuple(current_state.path)


def _runtime_stack(runtime: Any) -> List[Tuple[Tuple[str, ...], str]]:
    return [(tuple(path), mode) for path, mode in runtime.brief_stack]


def _standardize_cycle_result(value: Any) -> Dict[str, Any]:
    """
    Convert runtime-specific cycle results into the fixture assertion shape.

    ``CycleResult`` is the simulator-side public result object. Generated
    runtimes may still return ``None`` until their own template contracts grow
    matching metadata, so the compatibility shape always exposes ``value`` and
    adds event-accounting fields only when the result object provides them.

    :param value: Raw value returned by a runtime ``cycle`` call.
    :type value: Any
    :return: Standardized mapping used by ``expect.cycle_result``.
    :rtype: Dict[str, Any]

    Example::

        >>> _standardize_cycle_result(CycleResult(input_events=("Root.A.Go",)))
        {'value': None, 'input_events': ['Root.A.Go'], 'consumed_events': [], 'unconsumed_events': []}
    """
    if isinstance(value, CycleResult):
        return {
            "value": value.value,
            "input_events": list(value.input_events),
            "consumed_events": list(value.consumed_events),
            "unconsumed_events": list(value.unconsumed_events),
        }
    return {"value": value}


def _normalize_history_entries(
    value: Any, case: SemanticCase, field_path: str
) -> List[Dict[str, Any]]:
    if not isinstance(value, list):
        raise _case_error(case.id, case.yaml_path, "%s must be a list" % field_path)
    result = []
    for index, item in enumerate(value):
        item_path = "%s[%d]" % (field_path, index)
        if not isinstance(item, dict):
            raise _case_error(
                case.id, case.yaml_path, "%s must be a mapping" % item_path
            )
        result.append(dict(item))
    return result


def _runtime_history(runtime: Any) -> List[Dict[str, Any]]:
    return [dict(item) for item in getattr(runtime, "history")]


def _assert_history(
    runtime: Any, expect: Mapping[str, Any], case: SemanticCase, field_path: str
) -> None:
    actual_history = None
    if "history_length" in expect:
        actual_history = _runtime_history(runtime)
        assert len(actual_history) == expect["history_length"], (
            "%s %s history_length mismatch: %r != %r"
            % (case.id, field_path, len(actual_history), expect["history_length"])
        )
    if "history" in expect:
        actual_history = _runtime_history(runtime)
        expected_history = _normalize_history_entries(
            expect["history"], case, field_path + ".history"
        )
        assert actual_history == expected_history, (
            "%s %s history mismatch: %r != %r"
            % (case.id, field_path, actual_history, expected_history)
        )
    if "history_tail" in expect:
        actual_history = _runtime_history(runtime)
        expected_tail = _normalize_history_entries(
            expect["history_tail"], case, field_path + ".history_tail"
        )
        actual_tail = actual_history[-len(expected_tail) :] if expected_tail else []
        assert actual_tail == expected_tail, "%s %s history_tail mismatch: %r != %r" % (
            case.id,
            field_path,
            actual_tail,
            expected_tail,
        )


def _assert_cycle_result(
    result: Any, expect: Mapping[str, Any], case: SemanticCase, field_path: str
) -> None:
    if "cycle_result" not in expect:
        return
    actual_result = _standardize_cycle_result(result)
    expected_result = dict(expect["cycle_result"])
    comparable_result = {key: actual_result.get(key) for key in expected_result}
    assert comparable_result == expected_result, (
        "%s %s cycle_result mismatch for declared fields: %r != %r (full actual: %r)"
        % (
            case.id,
            field_path,
            comparable_result,
            expected_result,
            actual_result,
        )
    )


def _handler_call_comparable_record(actual: Mapping[str, Any]) -> Dict[str, Any]:
    result = dict(actual)
    state = actual.get("state")
    # Handler records originally carried only action/state/stage/vars. These
    # compatibility defaults reserve optional metadata slots for richer fixture
    # assertions while preserving old records; handlers that collect concrete
    # metadata can provide these keys directly and they will not be overwritten.
    result.setdefault(
        "active_leaf", state.split(".") if isinstance(state, str) else None
    )
    result.setdefault("call_stage", actual.get("stage"))
    result.setdefault("abstract_target", actual.get("action"))
    result.setdefault("named_ref", None)
    return result


def _assert_handler_calls(
    expect: Mapping[str, Any],
    handler_calls: Optional[Sequence[Mapping[str, Any]]],
    case: SemanticCase,
    field_path: str,
) -> None:
    if "handler_calls" not in expect:
        return
    if handler_calls is None:
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s.handler_calls requires registered fixture handlers" % field_path,
        )
    expected_calls = [dict(item) for item in expect["handler_calls"]]
    actual_calls = [_handler_call_comparable_record(item) for item in handler_calls]
    assert len(actual_calls) == len(expected_calls), (
        "%s %s handler_calls length mismatch: %r != %r"
        % (case.id, field_path, actual_calls, expected_calls)
    )
    for index, expected in enumerate(expected_calls):
        actual = actual_calls[index]
        for key, expected_value in expected.items():
            actual_value = actual.get(key)
            assert actual_value == expected_value, (
                "%s %s handler_calls[%d].%s mismatch: %r != %r"
                % (
                    case.id,
                    field_path,
                    index,
                    key,
                    actual_value,
                    expected_value,
                )
            )


def _normalize_handler_call_records(
    handler_calls: Sequence[Mapping[str, Any]],
) -> List[Dict[str, Any]]:
    return [_handler_call_comparable_record(item) for item in handler_calls]


def _assert_abstract_handler_errors(
    runtime: Any, expect: Mapping[str, Any], case: SemanticCase, field_path: str
) -> None:
    if "abstract_handler_errors" not in expect:
        return
    expected_errors = expect["abstract_handler_errors"]
    actual_errors = [
        {
            "action": action_path,
            "type": type(error).__name__,
            "message": str(error),
        }
        for action_path, error in runtime.abstract_handler_errors
    ]
    assert len(actual_errors) == len(expected_errors), (
        "%s %s abstract_handler_errors length mismatch: %r != %r"
        % (
            case.id,
            field_path,
            actual_errors,
            expected_errors,
        )
    )
    for index, expected in enumerate(expected_errors):
        actual = actual_errors[index]
        if "action" in expected:
            assert actual["action"] == expected["action"], (
                "%s %s abstract_handler_errors[%d].action mismatch: %r != %r"
                % (
                    case.id,
                    field_path,
                    index,
                    actual["action"],
                    expected["action"],
                )
            )
        if "type" in expected:
            assert actual["type"] == expected["type"], (
                "%s %s abstract_handler_errors[%d].type mismatch: %r != %r"
                % (
                    case.id,
                    field_path,
                    index,
                    actual["type"],
                    expected["type"],
                )
            )
        if "message" in expected:
            match_kind = expected.get("match_kind", "substring")
            if match_kind == "substring":
                matched = expected["message"] in actual["message"]
            elif match_kind == "regex":
                matched = re.search(expected["message"], actual["message"]) is not None
            else:
                raise _case_error(
                    case.id,
                    case.yaml_path,
                    "%s.abstract_handler_errors[%d].match_kind is invalid"
                    % (field_path, index),
                )
            assert matched, (
                "%s %s abstract_handler_errors[%d].message mismatch: %r did not match %r"
                % (
                    case.id,
                    field_path,
                    index,
                    actual["message"],
                    expected["message"],
                )
            )


def _assert_error_info(
    runtime: Any, expect: Mapping[str, Any], case: SemanticCase, field_path: str
) -> None:
    if "error_state" in expect:
        actual_error_state = bool(getattr(runtime, "is_error_state"))
        assert actual_error_state is bool(expect["error_state"]), (
            "%s %s error_state mismatch: %r != %r"
            % (case.id, field_path, actual_error_state, expect["error_state"])
        )
    if "error_info" not in expect:
        return
    actual_info = getattr(runtime, "error_info")
    expected_info = expect["error_info"]
    if expected_info is None:
        assert actual_info is None, "%s %s error_info mismatch: %r != None" % (
            case.id,
            field_path,
            actual_info,
        )
        return
    assert actual_info is not None, "%s %s error_info missing" % (case.id, field_path)
    actual_action, actual_error = actual_info
    if "action" in expected_info:
        assert actual_action == expected_info["action"], (
            "%s %s error_info.action mismatch: %r != %r"
            % (case.id, field_path, actual_action, expected_info["action"])
        )
    if "type" in expected_info:
        actual_type = type(actual_error).__name__
        assert actual_type == expected_info["type"], (
            "%s %s error_info.type mismatch: %r != %r"
            % (case.id, field_path, actual_type, expected_info["type"])
        )
    if "message" in expected_info:
        actual_message = str(actual_error)
        match_text = expected_info["message"]
        match_kind = expected_info.get("match_kind", "substring")
        if match_kind == "substring":
            matched = match_text in actual_message
        elif match_kind == "regex":
            matched = re.search(match_text, actual_message) is not None
        else:
            raise _case_error(
                case.id,
                case.yaml_path,
                "%s.error_info.match_kind is invalid" % field_path,
            )
        assert matched, "%s %s error_info.message mismatch: %r did not match %r" % (
            case.id,
            field_path,
            actual_message,
            match_text,
        )


def _assert_runtime_expectation(
    runtime: Any,
    expect: Mapping[str, Any],
    case: SemanticCase,
    field_path: str,
    handler_calls: Optional[Sequence[Mapping[str, Any]]] = None,
) -> None:
    if "ended" in expect:
        actual_ended = bool(getattr(runtime, "is_ended"))
        assert actual_ended is bool(expect["ended"]), (
            "%s %s ended mismatch: %r != %r"
            % (
                case.id,
                field_path,
                actual_ended,
                expect["ended"],
            )
        )

    if "state" in expect:
        expected_path = _as_tuple_path(expect["state"], case, field_path + ".state")
        actual_path = _runtime_state_path(runtime)
        assert actual_path == expected_path, "%s %s state mismatch: %r != %r" % (
            case.id,
            field_path,
            actual_path,
            expected_path,
        )

    actual_vars = _vars_dict(runtime)
    if "vars_exact" in expect:
        assert actual_vars == dict(expect["vars_exact"]), (
            "%s %s vars_exact mismatch: %r != %r"
            % (
                case.id,
                field_path,
                actual_vars,
                expect["vars_exact"],
            )
        )
    if "vars" in expect:
        for name, expected_value in dict(expect["vars"]).items():
            assert actual_vars.get(name) == expected_value, (
                "%s %s var %s mismatch: %r != %r"
                % (
                    case.id,
                    field_path,
                    name,
                    actual_vars.get(name),
                    expected_value,
                )
            )
    if "vars_keys" in expect:
        expected_keys = set(expect["vars_keys"])
        actual_keys = set(actual_vars.keys())
        assert actual_keys == expected_keys, "%s %s vars_keys mismatch: %r != %r" % (
            case.id,
            field_path,
            sorted(actual_keys),
            sorted(expected_keys),
        )
    if "vars_absent" in expect:
        for name in expect["vars_absent"]:
            assert name not in actual_vars, "%s %s unexpected var %s in %r" % (
                case.id,
                field_path,
                name,
                actual_vars,
            )

    if "stack" in expect:
        expected_stack = _normalize_stack(expect["stack"], case, field_path + ".stack")
        actual_stack = _runtime_stack(runtime)
        assert actual_stack == expected_stack, "%s %s stack mismatch: %r != %r" % (
            case.id,
            field_path,
            actual_stack,
            expected_stack,
        )

    if "cycle_count" in expect:
        actual_cycle_count = getattr(runtime, "cycle_count")
        assert actual_cycle_count == expect["cycle_count"], (
            "%s %s cycle_count mismatch: %r != %r"
            % (
                case.id,
                field_path,
                actual_cycle_count,
                expect["cycle_count"],
            )
        )

    _assert_history(runtime, expect, case, field_path)
    _assert_handler_calls(expect, handler_calls, case, field_path)
    _assert_abstract_handler_errors(runtime, expect, case, field_path)
    _assert_error_info(runtime, expect, case, field_path)
    if "anonymous_warning_count" in expect:
        actual_warning_count = len(getattr(runtime, "_warned_anonymous_abstracts"))
        assert actual_warning_count == expect["anonymous_warning_count"], (
            "%s %s anonymous_warning_count mismatch: %r != %r"
            % (
                case.id,
                field_path,
                actual_warning_count,
                expect["anonymous_warning_count"],
            )
        )


def _assert_logs(
    expect: Mapping[str, Any], caplog: Any, case: SemanticCase, field_path: str
) -> None:
    logs = expect.get("logs")
    if not logs:
        return
    if caplog is None:
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s.logs requires pytest caplog fixture" % field_path,
        )
    records = list(caplog.records)
    rendered = ["%s:%s" % (record.levelname, record.getMessage()) for record in records]
    for group_name, should_exist in (("contains", True), ("not_contains", False)):
        for item in logs.get(group_name, []) or []:
            level = str(item.get("level", "WARNING")).upper()
            message = str(item["message"])
            match_kind = item.get("match_kind", "substring")
            matching_records = [
                record for record in records if record.levelname.upper() == level
            ]
            if match_kind == "substring":
                found = any(
                    message in record.getMessage() for record in matching_records
                )
            elif match_kind == "regex":
                pattern = re.compile(message)
                found = any(
                    pattern.search(record.getMessage()) for record in matching_records
                )
            else:
                raise _case_error(
                    case.id,
                    case.yaml_path,
                    "%s.logs.%s has invalid match_kind %r"
                    % (
                        field_path,
                        group_name,
                        match_kind,
                    ),
                )
            assert found is should_exist, "%s %s log %s %r at %s failed; records=%r" % (
                case.id,
                field_path,
                group_name,
                message,
                level,
                rendered,
            )


def _warning_matches(item: Mapping[str, Any], warning_item: Any) -> bool:
    category = item.get("category")
    if category is not None and warning_item.category.__name__ != category:
        return False
    message = str(item["message"])
    warning_message = str(warning_item.message)
    match_kind = item.get("match_kind", "substring")
    if match_kind == "substring":
        return message in warning_message
    if match_kind == "regex":
        return re.search(message, warning_message) is not None
    return False


def _assert_warnings(
    expect: Mapping[str, Any],
    warning_records: Optional[Sequence[Any]],
    case: SemanticCase,
    field_path: str,
) -> None:
    warning_expect = expect.get("warnings")
    if warning_expect is None:
        return
    if warning_records is None:
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s.warnings requires warning capture" % field_path,
        )
    rendered = [
        "%s:%s" % (record.category.__name__, record.message)
        for record in warning_records
    ]
    if "count" in warning_expect:
        assert len(warning_records) == warning_expect["count"], (
            "%s %s warnings count mismatch: %r != %r; records=%r"
            % (
                case.id,
                field_path,
                len(warning_records),
                warning_expect["count"],
                rendered,
            )
        )
    for group_name, should_exist in (("contains", True), ("not_contains", False)):
        for item in warning_expect.get(group_name, []) or []:
            found = any(_warning_matches(item, record) for record in warning_records)
            assert found is should_exist, "%s %s warning %s %r failed; records=%r" % (
                case.id,
                field_path,
                group_name,
                item,
                rendered,
            )


def _assert_text_matches(
    text: str,
    match_text: str,
    match_kind: str,
    case: SemanticCase,
    field_path: str,
    target: str,
) -> None:
    if match_kind == "substring":
        matched = match_text in text
    elif match_kind == "regex":
        matched = re.search(match_text, text) is not None
    else:
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s.%s has invalid match_kind %r" % (field_path, target, match_kind),
        )
    assert matched, "%s %s %s %r did not match %r" % (
        case.id,
        field_path,
        target,
        text,
        match_text,
    )


def _assert_exception(
    exc: BaseException, expect: Mapping[str, Any], case: SemanticCase, field_path: str
) -> None:
    raises = expect["raises"]
    expected_type = raises["type"]
    assert type(exc).__name__ == expected_type, (
        "%s %s exception type mismatch: %s != %s: %s"
        % (
            case.id,
            field_path,
            type(exc).__name__,
            expected_type,
            exc,
        )
    )
    if "match" in raises:
        _assert_text_matches(
            str(exc),
            str(raises["match"]),
            raises.get("match_kind", "substring"),
            case,
            field_path,
            "exception message",
        )
    if "cause_type" in raises:
        cause = exc.__cause__
        assert cause is not None, "%s %s expected exception cause %r" % (
            case.id,
            field_path,
            raises["cause_type"],
        )
        assert type(cause).__name__ == raises["cause_type"], (
            "%s %s exception cause type mismatch: %s != %s: %s"
            % (
                case.id,
                field_path,
                type(cause).__name__,
                raises["cause_type"],
                cause,
            )
        )
    if "cause_match" in raises:
        cause = exc.__cause__
        assert cause is not None, "%s %s expected exception cause message %r" % (
            case.id,
            field_path,
            raises["cause_match"],
        )
        _assert_text_matches(
            str(cause),
            str(raises["cause_match"]),
            raises.get("cause_match_kind", "substring"),
            case,
            field_path,
            "exception cause message",
        )


@contextmanager
def _capture_logs_if_needed(expect: Mapping[str, Any], caplog: Any):
    if expect.get("logs") and caplog is not None:
        caplog.clear()
        with caplog.at_level(logging.DEBUG):
            yield
    else:
        if caplog is not None:
            caplog.clear()
        yield


@contextmanager
def _capture_warnings_if_needed(expect: Mapping[str, Any]):
    if "warnings" in expect:
        with warnings.catch_warnings(record=True) as records:
            warnings.simplefilter("always")
            yield records
    else:
        yield None


def _event_input_from_fixture_item(
    item: Any, runtime: Any, case: SemanticCase, field_path: str
) -> Any:
    if isinstance(item, str):
        return item
    if isinstance(item, dict):
        if set(item.keys()) != {"event"}:
            raise _case_error(
                case.id,
                case.yaml_path,
                "%s event descriptor must contain only event" % field_path,
            )
        path_name = item["event"]
        if not isinstance(path_name, str):
            raise _case_error(
                case.id,
                case.yaml_path,
                "%s.event must be a string" % field_path,
            )
        state_machine = getattr(runtime, "state_machine", None)
        if state_machine is None:
            raise _case_error(
                case.id,
                case.yaml_path,
                "%s.event requires a simulation runtime with state_machine"
                % field_path,
            )
        return state_machine.resolve_event(path_name)
    return item


def _step_events(
    cycle_data: Any, runtime: Any, case: SemanticCase, field_path: str
) -> Any:
    if cycle_data in (None, {}):
        return None
    if isinstance(cycle_data, str):
        return cycle_data
    if not isinstance(cycle_data, dict):
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s.cycle must be a mapping, string, null, or omitted" % field_path,
        )
    events = cycle_data.get("events")
    if events is None:
        return None
    if not isinstance(events, list):
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s.cycle.events must be a list or null" % field_path,
        )
    return [
        _event_input_from_fixture_item(
            item,
            runtime,
            case,
            "%s.cycle.events[%d]" % (field_path, index),
        )
        for index, item in enumerate(events)
    ]


def _run_step(
    runtime: Any,
    step: Mapping[str, Any],
    case: SemanticCase,
    index: int,
    caplog: Any = None,
    handler_calls: Optional[Sequence[Mapping[str, Any]]] = None,
) -> None:
    field_path = "steps[%d]" % index
    if "expect_initial" in step:
        expect = step["expect_initial"]
        _assert_runtime_expectation(
            runtime,
            expect,
            case,
            field_path + ".expect_initial",
            handler_calls=handler_calls,
        )
        return

    expect = step.get("expect") or {}
    events = _step_events(step.get("cycle", {}), runtime, case, field_path)
    with _capture_logs_if_needed(expect, caplog):
        with _capture_warnings_if_needed(expect) as warning_records:
            if "raises" in expect:
                try:
                    runtime.cycle(events)
                except Exception as err:
                    # Runtime/generator errors intentionally propagate through the
                    # fixture contract; expected semantic errors are matched here.
                    _assert_exception(err, expect, case, field_path + ".expect.raises")
                else:
                    raise AssertionError(
                        "%s %s expected exception %r"
                        % (case.id, field_path, expect["raises"])
                    )
            else:
                result = runtime.cycle(events)
                if "return" in expect:
                    actual_value = _standardize_cycle_result(result)["value"]
                    assert actual_value == expect["return"], (
                        "%s %s return mismatch: %r != %r"
                        % (
                            case.id,
                            field_path,
                            actual_value,
                            expect["return"],
                        )
                    )
                _assert_cycle_result(
                    result,
                    expect,
                    case,
                    field_path + ".expect.cycle_result",
                )
    _assert_runtime_expectation(
        runtime,
        expect,
        case,
        field_path + ".expect",
        handler_calls=handler_calls,
    )
    _assert_logs(expect, caplog, case, field_path + ".expect")
    _assert_warnings(expect, warning_records, case, field_path + ".expect")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _parse_dsl(dsl_code: str):
    ast_node = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast_node)


def build_state_machine_from_case(case: SemanticCase):
    """
    Build a state machine model for a semantic fixture.

    The helper parses the case DSL with the normal FCSTM grammar entry and then
    converts the AST into the production model object used by the simulator and
    generated-runtime alignment runner.

    :param case: Semantic fixture to parse.
    :type case: SemanticCase
    :return: Parsed state machine model for the case DSL.
    :rtype: pyfcstm.model.StateMachine
    :raises pyfcstm.dsl.error.GrammarParseError: If the fixture DSL is invalid.
    :raises pyfcstm.utils.validate.ModelValidationError: If model validation
        rejects the parsed DSL.

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> model = build_state_machine_from_case(case)
        >>> model.root_state.name
        'Root'
    """
    return _parse_dsl(case.dsl_code)


def run_model_build_case(case: SemanticCase) -> None:
    """
    Run a semantic fixture that expects model construction diagnostics.

    Model-build cases assert failures that happen before a
    :class:`pyfcstm.simulate.SimulationRuntime` can be constructed. The expected
    exception is matched through the same ``raises`` schema used by executable
    runtime steps.

    :param case: Semantic fixture with a ``model_build`` expectation.
    :type case: SemanticCase
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If model construction succeeds unexpectedly or the
        diagnostic does not match the fixture expectation.
    :raises SemanticCaseError: If the fixture expectation is malformed at
        assertion time.

    Example::

        >>> case = load_semantic_case("validation_action_reference_cycle")
        >>> run_model_build_case(case)
    """
    model_build = case.data["model_build"]
    expect = model_build["expect"]
    try:
        build_state_machine_from_case(case)
    except ModelValidationError as err:
        # ModelValidationError: model-build fixtures intentionally assert
        # documented construction diagnostics through the same exception
        # matcher as runtime steps.
        _assert_exception(err, expect, case, "model_build.expect.raises")
    else:
        raise AssertionError(
            "%s model_build expected exception %r" % (case.id, expect["raises"])
        )


def _initial_constructor_expect(case: SemanticCase) -> Optional[Mapping[str, Any]]:
    initial = case.data.get("initial") or {}
    expect = initial.get("expect")
    if expect is None:
        return None
    return expect


def _initial_constructor_expect_data(initial: Any) -> bool:
    return isinstance(initial, dict) and "expect" in initial


def _capture_construction(build_runtime):
    try:
        return build_runtime(), None
    except _ALIGNMENT_CONSTRUCTOR_EXCEPTION_TYPES as err:
        # ValueError/ArithmeticError/SimulationRuntimeDfsError cover simulator
        # and generated constructor diagnostics; TypeError covers invalid
        # runtime constructor references; KeyError covers generated hook-map
        # lookup misses while installing fixture handlers. Unexpected classes
        # still propagate and surface harness bugs.
        return None, err
    except Exception as err:
        # Generated runtimes define local diagnostic classes inside each emitted
        # module, so classes such as SimulationRuntimeDfsError do not subclass
        # the simulator's imported class. Only the documented constructor
        # diagnostic names are captured for cross-runtime parity; every other
        # exception is re-raised to expose real harness or template bugs.
        if type(err).__name__ not in _ALIGNMENT_CONSTRUCTOR_EXCEPTION_TYPE_NAMES:
            raise
        return None, err


def _assert_constructor_failure(build_runtime, expect, case: SemanticCase) -> None:
    runtime, err = _capture_construction(build_runtime)
    assert runtime is None, "%s initial.expect.raises unexpectedly built runtime" % (
        case.id,
    )
    assert err is not None, "%s initial.expect.raises expected exception %r" % (
        case.id,
        expect["raises"],
    )
    _assert_exception(err, expect, case, "initial.expect.raises")


def _exception_display(error: BaseException) -> str:
    return "%s: %s" % (type(error).__name__, error)


def _assert_aligned_constructor_outcome(
    case: SemanticCase,
    expect: Optional[Mapping[str, Any]],
    simulation_runtime: Any,
    simulation_err: Optional[BaseException],
    generated_runtime: Any,
    generated_err: Optional[BaseException],
) -> None:
    """
    Assert generated-runtime constructor parity for a semantic fixture.

    Constructor alignment has three observable outcomes: both runtimes build
    successfully, both runtimes fail with matching diagnostics, or exactly one
    side fails. The last outcome is a first-class alignment mismatch because
    hot-start and handler-installation bugs can happen before a cycle executes.

    :param case: Semantic fixture being constructed.
    :type case: SemanticCase
    :param expect: Optional ``initial.expect`` mapping.
    :type expect: typing.Mapping[str, typing.Any], optional
    :param simulation_runtime: Constructed simulator runtime, if available.
    :type simulation_runtime: typing.Any
    :param simulation_err: Simulator construction error, if construction
        failed.
    :type simulation_err: BaseException, optional
    :param generated_runtime: Constructed generated runtime, if available.
    :type generated_runtime: typing.Any
    :param generated_err: Generated-runtime construction error, if
        construction failed.
    :type generated_err: BaseException, optional
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If constructor outcomes diverge or do not satisfy
        the fixture expectation.

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> _assert_aligned_constructor_outcome(case, None, object(), None, object(), None)
    """
    if (simulation_err is None) != (generated_err is None):
        if simulation_err is None:
            simulation_text = "built successfully"
            generated_text = _exception_display(generated_err)
        else:
            simulation_text = _exception_display(simulation_err)
            generated_text = "built successfully"
        raise AssertionError(
            "%s constructor one-sided mismatch: simulation=%s, generated=%s"
            % (case.id, simulation_text, generated_text)
        )

    if simulation_err is None and generated_err is None:
        if expect is not None:
            raise AssertionError(
                "%s initial.expect.raises expected constructor failure %r"
                % (case.id, expect["raises"])
            )
        assert simulation_runtime is not None, "%s simulation runtime missing" % case.id
        assert generated_runtime is not None, "%s generated runtime missing" % case.id
        return

    assert simulation_err is not None
    assert generated_err is not None
    if expect is None:
        raise AssertionError(
            "%s constructor failed unexpectedly: simulation=%s, generated=%s"
            % (
                case.id,
                _exception_display(simulation_err),
                _exception_display(generated_err),
            )
        )
    assert type(simulation_err).__name__ == type(generated_err).__name__, (
        "%s constructor exception type mismatch: simulation=%s generated=%s"
        % (
            case.id,
            type(simulation_err).__name__,
            type(generated_err).__name__,
        )
    )
    _assert_exception(simulation_err, expect, case, "initial.expect.raises")
    _assert_exception(generated_err, expect, case, "initial.expect.raises")



def _initial_kwargs(case: SemanticCase) -> Dict[str, Any]:
    initial = case.data.get("initial") or {}
    kwargs = {}
    if initial.get("state") is not None:
        kwargs["initial_state"] = initial["state"]
    if initial.get("vars") is not None:
        kwargs["initial_vars"] = dict(initial["vars"])
    return kwargs


def _simulation_kwargs(case: SemanticCase) -> Dict[str, Any]:
    kwargs = _initial_kwargs(case)
    kwargs.update(dict(case.data.get("runtime_options") or {}))
    return kwargs


def _handler_call_record(ctx: Any) -> Dict[str, Any]:
    record = {
        "action": ctx.action_name,
        "state": ctx.get_full_state_path(),
        "stage": ctx.action_stage,
        "vars": dict(ctx.vars),
    }
    for name in ("active_leaf", "call_stage", "abstract_target", "named_ref"):
        if hasattr(ctx, name):
            value = getattr(ctx, name)
            record[name] = list(value) if isinstance(value, tuple) else value
    return record


def _handler_var_write_record(ctx: Any, name: str, value: Any) -> Dict[str, Any]:
    write_record = {
        "name": name,
        "value": value,
        "succeeded": False,
        "vars": dict(ctx.vars),
    }
    try:
        ctx.vars[name] = value
    except TypeError as err:
        # MappingProxyType and other immutable mappings reject item assignment
        # with TypeError; other exceptions should surface as test bugs.
        write_record["error_type"] = type(err).__name__
    else:
        write_record["succeeded"] = True
        write_record["vars"] = dict(ctx.vars)
    record = _handler_call_record(ctx)
    record["write_attempt"] = write_record
    return record


def _run_fixture_handler(
    handler_data: Mapping[str, Any], ctx: Any, calls: List[Mapping[str, Any]]
) -> None:
    behavior = handler_data["behavior"]
    if behavior == "record_call":
        calls.append(_handler_call_record(ctx))
    elif behavior == "raise_error":
        exception_data = handler_data.get("exception") or {}
        calls.append(_handler_call_record(ctx))
        raise ValueError(exception_data.get("message", "fixture handler error"))
    elif behavior == "record_var_write_attempt":
        write_data = handler_data["write"]
        calls.append(
            _handler_var_write_record(ctx, write_data["name"], write_data["value"])
        )
    else:
        raise ValueError("handlers behavior is invalid: %r" % behavior)


def _register_fixture_handlers(
    runtime: SimulationRuntime, case: SemanticCase
) -> List[Mapping[str, Any]]:
    calls = []
    for handler_data in case.data.get("handlers") or []:
        action_path = handler_data["action"]

        def fixture_handler(ctx, item=handler_data, handler_calls=calls):
            _run_fixture_handler(item, ctx, handler_calls)

        runtime.register_abstract_handler(action_path, fixture_handler)
    return calls


class _GeneratedPythonAlignmentRuntime:
    def __init__(
        self,
        simulation_runtime: SimulationRuntime,
        generated_runtime: Any,
        dsl_code: str,
    ):
        self._simulation_runtime = simulation_runtime
        self._generated_runtime = generated_runtime
        self._dsl_code = dsl_code

    @property
    def state_machine(self):
        """
        Return the simulator model used for fixture event-object descriptors.

        Generated Python alignment cases still resolve YAML ``{event: ...}``
        descriptors through the authoritative :class:`SimulationRuntime`
        model, then pass the resulting model event to both runtimes. The
        generated runtime accepts event-like objects by path today, while the
        simulator verifies that the object belongs to the same model.

        :return: State machine model owned by the simulation runtime.
        :rtype: pyfcstm.model.StateMachine

        Example::

            >>> case = load_semantic_case("event_input_model_event_object")
            >>> runtime = _build_simulation_runtime(case)
            >>> runtime.state_machine is not None
            True
        """
        return self._simulation_runtime.state_machine

    def _generated_brief_stack(self) -> List[Tuple[Tuple[str, ...], str]]:
        state_info = self._generated_runtime._STATE_INFO
        return [
            (tuple(state_info[frame["state"]]["path"]), frame["mode"])
            for frame in self._generated_runtime._stack
        ]

    def _assert_aligned(self, when: str) -> None:
        sim_ended = self._simulation_runtime.is_ended
        gen_ended = self._generated_runtime.is_ended
        assert sim_ended == gen_ended, (
            "%s: is_ended mismatch for DSL:\n%s\nsimulation=%r, generated=%r"
            % (
                when,
                self._dsl_code,
                sim_ended,
                gen_ended,
            )
        )
        sim_vars = dict(self._simulation_runtime.vars)
        gen_vars = dict(self._generated_runtime.vars)
        assert sim_vars == gen_vars, (
            "%s: vars mismatch for DSL:\n%s\nsimulation=%r\ngenerated=%r"
            % (
                when,
                self._dsl_code,
                sim_vars,
                gen_vars,
            )
        )
        if sim_ended:
            assert self._generated_runtime.current_state_path is None, (
                "%s: generated current_state_path should be None after end for DSL:\n%s\npath=%r"
                % (when, self._dsl_code, self._generated_runtime.current_state_path)
            )
        else:
            sim_path = self._simulation_runtime.current_state.path
            gen_path = self._generated_runtime.current_state_path
            assert sim_path == gen_path, (
                "%s: current state mismatch for DSL:\n%s\nsimulation=%r\ngenerated=%r"
                % (
                    when,
                    self._dsl_code,
                    sim_path,
                    gen_path,
                )
            )
        sim_stack = self._simulation_runtime.brief_stack
        gen_stack = self._generated_brief_stack()
        assert sim_stack == gen_stack, (
            "%s: brief_stack mismatch for DSL:\n%s\nsimulation=%r\ngenerated=%r"
            % (
                when,
                self._dsl_code,
                sim_stack,
                gen_stack,
            )
        )
        sim_cycle_count = self._simulation_runtime.cycle_count
        gen_cycle_count = self._generated_runtime.cycle_count
        assert sim_cycle_count == gen_cycle_count, (
            "%s: cycle_count mismatch for DSL:\n%s\nsimulation=%r, generated=%r"
            % (
                when,
                self._dsl_code,
                sim_cycle_count,
                gen_cycle_count,
            )
        )

    @property
    def cycle_count(self) -> int:
        self._assert_aligned("cycle_count access")
        return self._simulation_runtime.cycle_count

    @property
    def vars(self) -> Mapping[str, Any]:
        self._assert_aligned("vars access")
        return self._simulation_runtime.vars

    @property
    def is_ended(self) -> bool:
        self._assert_aligned("is_ended access")
        return self._simulation_runtime.is_ended

    @property
    def current_state(self):
        if self._simulation_runtime.is_ended:
            return self._simulation_runtime.current_state
        self._assert_aligned("current_state access")
        return self._simulation_runtime.current_state

    @property
    def brief_stack(self) -> List[Tuple[Tuple[str, ...], str]]:
        self._assert_aligned("brief_stack access")
        return self._simulation_runtime.brief_stack

    @property
    def history(self) -> List[Dict[str, Any]]:
        """
        Return simulator history after verifying generated-runtime alignment.

        The generated Python runtime does not expose history as a public API.
        Fixture history assertions remain valid for generated-alignment cases by
        first checking that generated state, variables, stack, and cycle count
        still match :class:`SimulationRuntime`, then returning the simulator's
        authoritative history records.

        :return: Runtime history records from the simulator side.
        :rtype: List[Dict[str, Any]]

        Example::

            >>> case = load_semantic_case("cycle_result_history_stable_leaf")
            >>> runtime = _build_simulation_runtime(case)
            >>> isinstance(runtime.history, list)
            True
        """
        self._assert_aligned("history access")
        return self._simulation_runtime.history

    def cycle(self, events: Optional[Sequence[Any]] = None) -> Any:
        sim_result = None
        gen_result = None
        sim_exc = None
        gen_exc = None
        try:
            sim_result = self._simulation_runtime.cycle(events)
        except Exception as err:
            # SimulationRuntime may raise any documented runtime semantic error;
            # alignment compares its class name with the generated runtime.
            sim_exc = err
        try:
            gen_result = self._generated_runtime.cycle(events)
        except Exception as err:
            # Generated runtime has its own local exception classes, so class-name
            # comparison is the stable cross-runtime contract.
            gen_exc = err
        if sim_exc is not None or gen_exc is not None:
            assert sim_exc is not None and gen_exc is not None, (
                "cycle(events=%r) exception mismatch for DSL:\n%s\nsimulation=%r, generated=%r"
                % (events, self._dsl_code, sim_exc, gen_exc)
            )
            assert type(sim_exc).__name__ == type(gen_exc).__name__, (
                "cycle(events=%r) exception type mismatch for DSL:\n%s\nsimulation=%s: %s\ngenerated=%s: %s"
                % (
                    events,
                    self._dsl_code,
                    type(sim_exc).__name__,
                    sim_exc,
                    type(gen_exc).__name__,
                    gen_exc,
                )
            )
            assert str(sim_exc) == str(gen_exc), (
                "cycle(events=%r) exception message mismatch for DSL:\n%s\nsimulation=%s: %s\ngenerated=%s: %s"
                % (
                    events,
                    self._dsl_code,
                    type(sim_exc).__name__,
                    sim_exc,
                    type(gen_exc).__name__,
                    gen_exc,
                )
            )
            sim_cause = sim_exc.__cause__
            gen_cause = gen_exc.__cause__
            assert (sim_cause is None) == (gen_cause is None), (
                "cycle(events=%r) exception cause presence mismatch for DSL:\n%s\nsimulation=%r\ngenerated=%r"
                % (events, self._dsl_code, sim_cause, gen_cause)
            )
            if sim_cause is not None and gen_cause is not None:
                assert type(sim_cause).__name__ == type(gen_cause).__name__, (
                    "cycle(events=%r) exception cause type mismatch for DSL:\n%s\nsimulation=%s: %s\ngenerated=%s: %s"
                    % (
                        events,
                        self._dsl_code,
                        type(sim_cause).__name__,
                        sim_cause,
                        type(gen_cause).__name__,
                        gen_cause,
                    )
                )
                assert str(sim_cause) == str(gen_cause), (
                    "cycle(events=%r) exception cause message mismatch for DSL:\n%s\nsimulation=%s: %s\ngenerated=%s: %s"
                    % (
                        events,
                        self._dsl_code,
                        type(sim_cause).__name__,
                        sim_cause,
                        type(gen_cause).__name__,
                        gen_cause,
                    )
                )
            raise sim_exc
        sim_standardized = _standardize_cycle_result(sim_result)
        gen_standardized = _standardize_cycle_result(gen_result)
        assert sim_standardized.get("value") == gen_standardized.get("value"), (
            "cycle(events=%r) return value mismatch for DSL:\n%s\nsimulation=%r, generated=%r"
            % (events, self._dsl_code, sim_result, gen_result)
        )
        self._assert_aligned("after cycle(events=%r)" % (events,))
        return sim_result


def _build_generated_runtime(
    case: SemanticCase, handler_calls: Optional[List[Mapping[str, Any]]] = None
) -> Any:
    model = build_state_machine_from_case(case)
    with TemporaryDirectory() as template_td:
        template_dir = extract_template("python", template_td)
        with TemporaryDirectory() as output_td:
            StateMachineCodeRenderer(template_dir).render(
                model=model, output_dir=output_td
            )
            module_file = os.path.join(output_td, "machine.py")
            module_name = "generated_python_runtime_%s" % re.sub(r"\W+", "_", case.id)
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            machine_cls = getattr(module, "%sMachine" % model.root_state.name)
            if case.data.get("handlers"):
                generated_calls = handler_calls if handler_calls is not None else []
                hook_handlers = {}
                hook_map = machine_cls.get_abstract_hook_map()
                for handler_data in case.data.get("handlers") or []:
                    hook_name = hook_map[handler_data["action"]]
                    hook_handlers.setdefault(hook_name, []).append(handler_data)

                attrs = {}
                for hook_name, handler_items in hook_handlers.items():

                    def fixture_hook(
                        self,
                        ctx,
                        items=tuple(handler_items),
                        calls=generated_calls,
                    ):
                        for item in items:
                            _run_fixture_handler(item, ctx, calls)

                    attrs[hook_name] = fixture_hook
                machine_cls = type(
                    "%sFixtureHandlers" % machine_cls.__name__, (machine_cls,), attrs
                )
            return machine_cls(**_initial_kwargs(case))


def _build_simulation_runtime(case: SemanticCase) -> SimulationRuntime:
    return SimulationRuntime(
        build_state_machine_from_case(case), **_simulation_kwargs(case)
    )


def run_simulation_case(case: SemanticCase, caplog: Any = None) -> None:
    """
    Run a semantic fixture against :class:`SimulationRuntime`.

    The runner builds the production simulator, installs any fixture-defined
    abstract handlers, executes each step, and applies the strict YAML
    expectations for state, variables, stack, history, cycle result, logs,
    warnings, and handler calls.

    :param case: Semantic fixture to execute with the simulation runner.
    :type case: SemanticCase
    :param caplog: Optional pytest log-capture fixture used when a step asserts
        log output, defaults to ``None``.
    :type caplog: typing.Any, optional
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If runtime behavior differs from the fixture
        expectation.
    :raises SemanticCaseError: If a runtime-only assertion is requested without
        the supporting fixture setup.

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> run_simulation_case(case)
    """
    if "model_build" in case.data:
        run_model_build_case(case)
        return
    initial_expect = _initial_constructor_expect(case)
    if initial_expect is not None:
        _assert_constructor_failure(
            lambda: _build_simulation_runtime(case),
            initial_expect,
            case,
        )
        return
    runtime = _build_simulation_runtime(case)
    handler_calls = _register_fixture_handlers(runtime, case)
    for index, step in enumerate(case.data.get("steps") or []):
        _run_step(
            runtime,
            step,
            case,
            index,
            caplog=caplog,
            handler_calls=handler_calls,
        )


def run_generated_python_alignment_case(case: SemanticCase, caplog: Any = None) -> None:
    """
    Run a semantic fixture against simulation and generated Python runtimes.

    The alignment runner generates the built-in Python runtime for the case DSL,
    executes it beside :class:`SimulationRuntime`, and asserts that state,
    variables, stack, cycle counts, returns, exceptions, and handler calls remain
    aligned after every fixture step.

    :param case: Semantic fixture that includes the
        ``generated_python_alignment`` runner.
    :type case: SemanticCase
    :param caplog: Optional pytest log-capture fixture, defaults to ``None``.
    :type caplog: typing.Any, optional
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If generated runtime behavior diverges from the
        simulator or the fixture expectation.

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> run_generated_python_alignment_case(case)
    """
    generated_handler_calls = []
    simulation_runtime, simulation_err = _capture_construction(
        lambda: _build_simulation_runtime(case)
    )
    generated_runtime, generated_err = _capture_construction(
        lambda: _build_generated_runtime(case, handler_calls=generated_handler_calls)
    )
    initial_expect = _initial_constructor_expect(case)
    _assert_aligned_constructor_outcome(
        case,
        initial_expect,
        simulation_runtime,
        simulation_err,
        generated_runtime,
        generated_err,
    )
    if initial_expect is not None:
        return
    simulation_handler_calls = _register_fixture_handlers(simulation_runtime, case)
    runtime = _GeneratedPythonAlignmentRuntime(
        simulation_runtime, generated_runtime, case.dsl_code
    )
    runtime._assert_aligned("initial build")
    for index, step in enumerate(case.data.get("steps") or []):
        _run_step(
            runtime,
            step,
            case,
            index,
            caplog=caplog,
            handler_calls=simulation_handler_calls,
        )
        simulation_calls = _normalize_handler_call_records(simulation_handler_calls)
        generated_calls = _normalize_handler_call_records(generated_handler_calls)
        assert simulation_calls == generated_calls, (
            "%s steps[%d] handler call mismatch: simulation=%r, generated=%r"
            % (case.id, index, simulation_calls, generated_calls)
        )


def run_cli_command_case(case: SemanticCase) -> None:
    """
    Run a semantic fixture against the simulate CLI command processor.

    CLI-command cases exercise :class:`pyfcstm.entry.simulate.commands.CommandProcessor`
    directly. Each command expectation may assert output text, exit behavior,
    and the backing runtime state after the command has executed.

    :param case: Semantic fixture that uses the ``cli_command`` runner.
    :type case: SemanticCase
    :return: ``None``.
    :rtype: None
    :raises AssertionError: If command output, exit flags, or runtime state do
        not match the fixture expectation.

    Example::

        >>> case = load_semantic_case("cli_init_full_state")
        >>> run_cli_command_case(case)
    """
    state_machine = build_state_machine_from_case(case)
    runtime = SimulationRuntime(state_machine)
    processor = CommandProcessor(runtime, state_machine=state_machine, use_color=False)
    for index, command in enumerate(case.data.get("commands") or []):
        result = processor.process(command["input"])
        expect = command.get("expect") or {}
        output = _strip_ansi(result.output)
        for item in expect.get("output_contains", []) or []:
            assert item in output, "%s commands[%d] output missing %r:\n%s" % (
                case.id,
                index,
                item,
                output,
            )
        for item in expect.get("output_not_contains", []) or []:
            assert item not in output, (
                "%s commands[%d] output unexpectedly contains %r:\n%s"
                % (
                    case.id,
                    index,
                    item,
                    output,
                )
            )
        for item in expect.get("error_contains", []) or []:
            assert item in output, "%s commands[%d] error missing %r:\n%s" % (
                case.id,
                index,
                item,
                output,
            )
        if "should_exit" in expect:
            assert result.should_exit is bool(expect["should_exit"]), (
                "%s commands[%d] should_exit mismatch"
                % (
                    case.id,
                    index,
                )
            )
        if "runtime" in expect:
            _assert_runtime_expectation(
                processor.runtime,
                expect["runtime"],
                case,
                "commands[%d].expect.runtime" % index,
            )


def _validate_vars_contract(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "vars" in expect and "vars_exact" in expect:
        for name, value in dict(expect["vars"]).items():
            if name in expect["vars_exact"] and expect["vars_exact"][name] != value:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s vars and vars_exact conflict for %s" % (field_path, name),
                )
    if "vars_keys" in expect and "vars_absent" in expect:
        overlap = set(expect["vars_keys"]) & set(expect["vars_absent"])
        if overlap:
            raise _case_error(
                case_id,
                yaml_path,
                "%s vars_keys and vars_absent overlap: %r"
                % (
                    field_path,
                    sorted(overlap),
                ),
            )


def _validate_stack(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    for index, item in enumerate(expect.get("stack", []) or []):
        if not isinstance(item, dict):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.stack[%d] must be a mapping" % (field_path, index),
            )
        unknown = set(item.keys()) - _ALLOWED_STACK_FIELDS
        if unknown:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.stack[%d] has unknown fields: %r"
                % (
                    field_path,
                    index,
                    sorted(unknown),
                ),
            )
        if "path" not in item or item.get("path") is None:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.stack[%d].path is required" % (field_path, index),
            )
        path = item.get("path")
        if not isinstance(path, list) or not all(
            isinstance(segment, str) for segment in path
        ):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.stack[%d].path must be a list of strings"
                % (
                    field_path,
                    index,
                ),
            )
        if item.get("mode") not in _ALLOWED_STACK_MODES:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.stack[%d].mode is invalid: %r"
                % (
                    field_path,
                    index,
                    item.get("mode"),
                ),
            )


def _validate_raises(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "raises" not in expect:
        return
    if "return" in expect:
        raise _case_error(
            case_id, yaml_path, "%s cannot combine raises and return" % field_path
        )
    if "cycle_result" in expect:
        raise _case_error(
            case_id,
            yaml_path,
            "%s cannot combine raises and cycle_result" % field_path,
        )
    raises = expect["raises"]
    if not isinstance(raises, dict):
        raise _case_error(
            case_id, yaml_path, "%s.raises must be a mapping" % field_path
        )
    unknown = set(raises.keys()) - _ALLOWED_RAISES_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.raises has unknown fields: %r" % (field_path, sorted(unknown)),
        )
    exc_type = raises.get("type")
    if exc_type not in _EXCEPTION_TYPES:
        raise _case_error(
            case_id, yaml_path, "%s.raises.type is unknown: %r" % (field_path, exc_type)
        )
    if "match" in raises and not isinstance(raises["match"], str):
        raise _case_error(
            case_id, yaml_path, "%s.raises.match must be a string" % field_path
        )
    if raises.get("match_kind", "substring") not in {"substring", "regex"}:
        raise _case_error(
            case_id, yaml_path, "%s.raises.match_kind is invalid" % field_path
        )
    if "cause_type" in raises and not isinstance(raises["cause_type"], str):
        raise _case_error(
            case_id, yaml_path, "%s.raises.cause_type must be a string" % field_path
        )
    if "cause_match" in raises and not isinstance(raises["cause_match"], str):
        raise _case_error(
            case_id, yaml_path, "%s.raises.cause_match must be a string" % field_path
        )
    if raises.get("cause_match_kind", "substring") not in {"substring", "regex"}:
        raise _case_error(
            case_id, yaml_path, "%s.raises.cause_match_kind is invalid" % field_path
        )
    if "cause_match_kind" in raises and "cause_match" not in raises:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.raises.cause_match_kind requires cause_match" % field_path,
        )


def _validate_cycle_result(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "cycle_result" not in expect:
        return
    if "return" in expect:
        raise _case_error(
            case_id,
            yaml_path,
            "%s cannot combine return and cycle_result" % field_path,
        )
    cycle_result = expect["cycle_result"]
    if not isinstance(cycle_result, dict):
        raise _case_error(
            case_id, yaml_path, "%s.cycle_result must be a mapping" % field_path
        )
    unknown = set(cycle_result.keys()) - _ALLOWED_CYCLE_RESULT_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle_result has unknown fields: %r" % (field_path, sorted(unknown)),
        )
    if "value" not in cycle_result:
        raise _case_error(
            case_id, yaml_path, "%s.cycle_result.value is required" % field_path
        )
    for event_field in ("input_events", "consumed_events", "unconsumed_events"):
        if event_field in cycle_result:
            _validate_string_list(
                cycle_result[event_field],
                case_id,
                yaml_path,
                "%s.cycle_result.%s" % (field_path, event_field),
            )


def _validate_history_entries(
    value: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if not isinstance(value, list):
        raise _case_error(case_id, yaml_path, "%s must be a list" % field_path)
    for index, item in enumerate(value):
        item_path = "%s[%d]" % (field_path, index)
        if not isinstance(item, dict):
            raise _case_error(case_id, yaml_path, "%s must be a mapping" % item_path)
        unknown = set(item.keys()) - _ALLOWED_HISTORY_FIELDS
        if unknown:
            raise _case_error(
                case_id,
                yaml_path,
                "%s has unknown fields: %r" % (item_path, sorted(unknown)),
            )
        missing = _REQUIRED_HISTORY_FIELDS - set(item.keys())
        if missing:
            raise _case_error(
                case_id,
                yaml_path,
                "%s missing fields: %r" % (item_path, sorted(missing)),
            )
        if not isinstance(item["cycle"], int):
            raise _case_error(
                case_id, yaml_path, "%s.cycle must be an integer" % item_path
            )
        if not isinstance(item["state"], str):
            raise _case_error(
                case_id, yaml_path, "%s.state must be a string" % item_path
            )
        _validate_vars_mapping(item["vars"], case_id, yaml_path, item_path + ".vars")
        _validate_string_list(item["events"], case_id, yaml_path, item_path + ".events")


def _validate_history(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "history_length" in expect and (
        not isinstance(expect["history_length"], int) or expect["history_length"] < 0
    ):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.history_length must be a non-negative integer" % field_path,
        )
    if "history" in expect:
        _validate_history_entries(
            expect["history"], case_id, yaml_path, field_path + ".history"
        )
    if "history_tail" in expect:
        if not expect["history_tail"]:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.history_tail must be a non-empty list" % field_path,
            )
        _validate_history_entries(
            expect["history_tail"], case_id, yaml_path, field_path + ".history_tail"
        )


def _validate_logs(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    logs = expect.get("logs")
    if not logs:
        return
    if not isinstance(logs, dict):
        raise _case_error(case_id, yaml_path, "%s.logs must be a mapping" % field_path)
    unknown = set(logs.keys()) - _ALLOWED_LOG_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.logs has unknown fields: %r" % (field_path, sorted(unknown)),
        )
    for group_name in ("contains", "not_contains"):
        group_items = logs.get(group_name, []) or []
        if not isinstance(group_items, list):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.logs.%s must be a list" % (field_path, group_name),
            )
        for index, item in enumerate(group_items):
            if not isinstance(item, dict):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.logs.%s[%d] must be a mapping"
                    % (
                        field_path,
                        group_name,
                        index,
                    ),
                )
            if "match" in item:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.logs.%s[%d] must use match_kind, not match"
                    % (
                        field_path,
                        group_name,
                        index,
                    ),
                )
            unknown_item = set(item.keys()) - _ALLOWED_LOG_ITEM_FIELDS
            if unknown_item:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.logs.%s[%d] has unknown fields: %r"
                    % (
                        field_path,
                        group_name,
                        index,
                        sorted(unknown_item),
                    ),
                )
            if "level" in item and not isinstance(item["level"], str):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.logs.%s[%d].level must be a string"
                    % (
                        field_path,
                        group_name,
                        index,
                    ),
                )
            if item.get("match_kind", "substring") not in {"substring", "regex"}:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.logs.%s[%d].match_kind is invalid"
                    % (
                        field_path,
                        group_name,
                        index,
                    ),
                )
            if "message" not in item:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.logs.%s[%d].message is required"
                    % (
                        field_path,
                        group_name,
                        index,
                    ),
                )
            if not isinstance(item["message"], str):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.logs.%s[%d].message must be a string"
                    % (
                        field_path,
                        group_name,
                        index,
                    ),
                )


def _validate_warnings(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    warning_expect = expect.get("warnings")
    if warning_expect is None:
        return
    if not isinstance(warning_expect, dict):
        raise _case_error(
            case_id, yaml_path, "%s.warnings must be a mapping" % field_path
        )
    unknown = set(warning_expect.keys()) - _ALLOWED_WARNING_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.warnings has unknown fields: %r" % (field_path, sorted(unknown)),
        )
    if "count" in warning_expect:
        count = warning_expect["count"]
        if not isinstance(count, int) or count < 0:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.warnings.count must be a non-negative integer" % field_path,
            )
    for group_name in ("contains", "not_contains"):
        group_items = warning_expect.get(group_name, []) or []
        if not isinstance(group_items, list):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.warnings.%s must be a list" % (field_path, group_name),
            )
        for index, item in enumerate(group_items):
            if not isinstance(item, dict):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.warnings.%s[%d] must be a mapping"
                    % (field_path, group_name, index),
                )
            unknown_item = set(item.keys()) - _ALLOWED_WARNING_ITEM_FIELDS
            if unknown_item:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.warnings.%s[%d] has unknown fields: %r"
                    % (field_path, group_name, index, sorted(unknown_item)),
                )
            if "message" not in item:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.warnings.%s[%d].message is required"
                    % (field_path, group_name, index),
                )
            if not isinstance(item["message"], str):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.warnings.%s[%d].message must be a string"
                    % (field_path, group_name, index),
                )
            if item.get("match_kind", "substring") not in {"substring", "regex"}:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.warnings.%s[%d].match_kind is invalid"
                    % (field_path, group_name, index),
                )
            category = item.get("category")
            if category is not None and category not in _ALLOWED_WARNING_CATEGORIES:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.warnings.%s[%d].category is invalid: %r"
                    % (field_path, group_name, index, category),
                )


def _validate_handler_calls(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "handler_calls" not in expect:
        return
    calls = expect["handler_calls"]
    if not isinstance(calls, list):
        raise _case_error(
            case_id, yaml_path, "%s.handler_calls must be a list" % field_path
        )
    for index, item in enumerate(calls):
        if not isinstance(item, dict):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.handler_calls[%d] must be a mapping" % (field_path, index),
            )
        unknown = set(item.keys()) - _ALLOWED_HANDLER_CALL_FIELDS
        if unknown:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.handler_calls[%d] has unknown fields: %r"
                % (field_path, index, sorted(unknown)),
            )
        missing = _REQUIRED_HANDLER_CALL_FIELDS - set(item.keys())
        if missing:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.handler_calls[%d] missing fields: %r"
                % (field_path, index, sorted(missing)),
            )
        for field_name in ("action", "state", "stage"):
            if not isinstance(item[field_name], str):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.handler_calls[%d].%s must be a string"
                    % (field_path, index, field_name),
                )
        _validate_vars_mapping(
            item["vars"],
            case_id,
            yaml_path,
            "%s.handler_calls[%d].vars" % (field_path, index),
        )
        if "write_attempt" in item:
            _validate_write_attempt(
                item["write_attempt"],
                case_id,
                yaml_path,
                "%s.handler_calls[%d].write_attempt" % (field_path, index),
            )
        if "active_leaf" in item:
            _validate_path_segments(
                item["active_leaf"],
                case_id,
                yaml_path,
                "%s.handler_calls[%d].active_leaf" % (field_path, index),
            )
        for field_name in ("call_stage", "abstract_target", "named_ref"):
            if (
                field_name in item
                and item[field_name] is not None
                and not isinstance(item[field_name], str)
            ):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.handler_calls[%d].%s must be a string or null"
                    % (field_path, index, field_name),
                )


def _validate_write_attempt(
    value: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if not isinstance(value, dict):
        raise _case_error(case_id, yaml_path, "%s must be a mapping" % field_path)
    unknown = set(value.keys()) - _ALLOWED_WRITE_ATTEMPT_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "%s has unknown fields: %r" % (field_path, sorted(unknown)),
        )
    for field_name in ("name", "error_type"):
        if field_name in value and not isinstance(value[field_name], str):
            raise _case_error(
                case_id, yaml_path, "%s.%s must be a string" % (field_path, field_name)
            )
    if "name" not in value:
        raise _case_error(case_id, yaml_path, "%s.name is required" % field_path)
    if "value" not in value:
        raise _case_error(case_id, yaml_path, "%s.value is required" % field_path)
    if "succeeded" not in value or not isinstance(value["succeeded"], bool):
        raise _case_error(
            case_id, yaml_path, "%s.succeeded must be a boolean" % field_path
        )
    if "vars" in value:
        _validate_vars_mapping(value["vars"], case_id, yaml_path, field_path + ".vars")


def _validate_abstract_handler_errors(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "abstract_handler_errors" not in expect:
        return
    errors = expect["abstract_handler_errors"]
    if not isinstance(errors, list):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.abstract_handler_errors must be a list" % field_path,
        )
    for index, item in enumerate(errors):
        if not isinstance(item, dict):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.abstract_handler_errors[%d] must be a mapping"
                % (field_path, index),
            )
        unknown = set(item.keys()) - _ALLOWED_ABSTRACT_HANDLER_ERROR_FIELDS
        if unknown:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.abstract_handler_errors[%d] has unknown fields: %r"
                % (field_path, index, sorted(unknown)),
            )
        for field_name in ("action", "type", "message"):
            if field_name in item and not isinstance(item[field_name], str):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s.abstract_handler_errors[%d].%s must be a string"
                    % (field_path, index, field_name),
                )
        if item.get("match_kind", "substring") not in {"substring", "regex"}:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.abstract_handler_errors[%d].match_kind is invalid"
                % (field_path, index),
            )
        if "match_kind" in item and "message" not in item:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.abstract_handler_errors[%d].match_kind requires message"
                % (field_path, index),
            )


def _validate_error_info(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "error_state" in expect and not isinstance(expect["error_state"], bool):
        raise _case_error(
            case_id, yaml_path, "%s.error_state must be a boolean" % field_path
        )
    if "error_info" not in expect:
        return
    if expect["error_info"] is None:
        return
    item = expect["error_info"]
    if not isinstance(item, dict):
        raise _case_error(
            case_id, yaml_path, "%s.error_info must be a mapping" % field_path
        )
    unknown = set(item.keys()) - _ALLOWED_ERROR_INFO_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.error_info has unknown fields: %r" % (field_path, sorted(unknown)),
        )
    for field_name in ("action", "type", "message"):
        if field_name in item and not isinstance(item[field_name], str):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.error_info.%s must be a string" % (field_path, field_name),
            )
    if item.get("match_kind", "substring") not in {"substring", "regex"}:
        raise _case_error(
            case_id, yaml_path, "%s.error_info.match_kind is invalid" % field_path
        )
    if "match_kind" in item and "message" not in item:
        raise _case_error(
            case_id, yaml_path, "%s.error_info.match_kind requires message" % field_path
        )


def _validate_path_segments(
    value: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if value is None:
        return
    if not isinstance(value, list) or not all(
        isinstance(segment, str) for segment in value
    ):
        raise _case_error(
            case_id, yaml_path, "%s must be a list of strings or null" % field_path
        )


def _validate_vars_mapping(
    value: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if not isinstance(value, dict):
        raise _case_error(case_id, yaml_path, "%s must be a mapping" % field_path)


def _validate_string_list(
    value: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if not isinstance(value, list) or not all(isinstance(item, str) for item in value):
        raise _case_error(
            case_id, yaml_path, "%s must be a list of strings" % field_path
        )


def _validate_expect(
    expect: Mapping[str, Any],
    case_id: str,
    yaml_path: str,
    field_path: str,
    runners: Sequence[str],
    allowed_fields: Iterable[str] = _ALLOWED_EXPECT_FIELDS,
) -> None:
    if not isinstance(expect, dict):
        raise _case_error(case_id, yaml_path, "%s must be a mapping" % field_path)
    allowed_set = set(allowed_fields)
    unknown = set(expect.keys()) - allowed_set
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "%s has unknown fields: %r" % (field_path, sorted(unknown)),
        )
    if "generated_python_alignment" in runners:
        unsupported_generated_alignment_fields = {
            "abstract_handler_errors",
            "warnings",
            "error_state",
            "error_info",
            "anonymous_warning_count",
        }
        overlap = unsupported_generated_alignment_fields & set(expect.keys())
        if overlap:
            raise _case_error(
                case_id,
                yaml_path,
                "%s fields are not allowed for generated alignment: %r"
                % (field_path, sorted(overlap)),
            )
    if "state" in expect:
        _validate_path_segments(
            expect["state"], case_id, yaml_path, field_path + ".state"
        )
    for vars_field in ("vars", "vars_exact"):
        if vars_field in expect:
            _validate_vars_mapping(
                expect[vars_field], case_id, yaml_path, field_path + "." + vars_field
            )
    for list_field in ("vars_keys", "vars_absent"):
        if list_field in expect:
            _validate_string_list(
                expect[list_field], case_id, yaml_path, field_path + "." + list_field
            )
    _validate_vars_contract(expect, case_id, yaml_path, field_path)
    _validate_stack(expect, case_id, yaml_path, field_path)
    _validate_raises(expect, case_id, yaml_path, field_path)
    _validate_cycle_result(expect, case_id, yaml_path, field_path)
    _validate_history(expect, case_id, yaml_path, field_path)
    _validate_logs(expect, case_id, yaml_path, field_path)
    _validate_warnings(expect, case_id, yaml_path, field_path)
    _validate_handler_calls(expect, case_id, yaml_path, field_path)
    _validate_abstract_handler_errors(expect, case_id, yaml_path, field_path)
    _validate_error_info(expect, case_id, yaml_path, field_path)
    if "anonymous_warning_count" in expect and (
        not isinstance(expect["anonymous_warning_count"], int)
        or expect["anonymous_warning_count"] < 0
    ):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.anonymous_warning_count must be a non-negative integer" % field_path,
        )


def _validate_model_build(
    model_build: Any, case_id: str, yaml_path: str, runners: Sequence[str]
) -> None:
    if model_build is None:
        return
    if tuple(runners) != ("simulation",):
        raise _case_error(
            case_id,
            yaml_path,
            "model_build is only supported by simulation-only cases",
        )
    if not isinstance(model_build, dict):
        raise _case_error(case_id, yaml_path, "model_build must be a mapping")
    unknown = set(model_build.keys()) - _ALLOWED_MODEL_BUILD_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "model_build has unknown fields: %r" % sorted(unknown),
        )
    expect = model_build.get("expect")
    if not isinstance(expect, dict):
        raise _case_error(case_id, yaml_path, "model_build.expect must be a mapping")
    _validate_expect(
        expect,
        case_id,
        yaml_path,
        "model_build.expect",
        runners,
        allowed_fields=_ALLOWED_MODEL_BUILD_EXPECT_FIELDS,
    )
    if "raises" not in expect:
        raise _case_error(
            case_id,
            yaml_path,
            "model_build.expect.raises is required",
        )
    raises = expect["raises"]
    if raises.get("type") != "ModelValidationError":
        raise _case_error(
            case_id,
            yaml_path,
            "model_build.expect.raises.type must be ModelValidationError",
        )


def _validate_source(source: Any, case_id: str, yaml_path: str) -> None:
    if not isinstance(source, dict):
        raise _case_error(case_id, yaml_path, "source must be a mapping")
    unknown_source = set(source.keys()) - _ALLOWED_SOURCE_FIELDS
    if unknown_source:
        raise _case_error(
            case_id, yaml_path, "source has unknown fields: %r" % sorted(unknown_source)
        )
    if not source.get("fcstm"):
        raise _case_error(case_id, yaml_path, "source.fcstm is required")
    if not isinstance(source["fcstm"], str):
        raise _case_error(case_id, yaml_path, "source.fcstm must be a string")


def _validate_origin(origin: Any, case_id: str, yaml_path: str) -> None:
    if not isinstance(origin, dict):
        raise _case_error(case_id, yaml_path, "origin must be a mapping")
    unknown_origin = set(origin.keys()) - _ALLOWED_ORIGIN_FIELDS
    if unknown_origin:
        raise _case_error(
            case_id, yaml_path, "origin has unknown fields: %r" % sorted(unknown_origin)
        )
    files = origin.get("files")
    if (
        not isinstance(files, list)
        or not files
        or not all(isinstance(item, str) for item in files)
    ):
        raise _case_error(
            case_id, yaml_path, "origin.files must be a non-empty list of strings"
        )
    for field_name in ("docs", "assertion_types", "notes"):
        if field_name in origin:
            _validate_string_list(
                origin[field_name], case_id, yaml_path, "origin." + field_name
            )


def _validate_initial(
    initial: Any, case_id: str, yaml_path: str, runners: Sequence[str]
) -> None:
    if initial is None:
        return
    if not isinstance(initial, dict):
        raise _case_error(case_id, yaml_path, "initial must be a mapping")
    unknown_initial = set(initial.keys()) - _ALLOWED_INITIAL_FIELDS
    if unknown_initial:
        raise _case_error(
            case_id,
            yaml_path,
            "initial has unknown fields: %r" % sorted(unknown_initial),
        )
    if initial.get("state") is not None and not isinstance(initial.get("state"), str):
        raise _case_error(case_id, yaml_path, "initial.state must be a string or null")
    if initial.get("vars") is not None:
        _validate_vars_mapping(initial.get("vars"), case_id, yaml_path, "initial.vars")
    if "expect" not in initial:
        return
    if "state" not in initial:
        raise _case_error(
            case_id,
            yaml_path,
            "initial.expect requires initial.state",
        )
    if "vars" not in initial:
        raise _case_error(
            case_id,
            yaml_path,
            "initial.expect requires initial.vars",
        )
    if "cli_command" in runners:
        raise _case_error(
            case_id,
            yaml_path,
            "initial.expect is not supported for cli_command cases",
        )
    expect = initial["expect"]
    if not isinstance(expect, dict):
        raise _case_error(case_id, yaml_path, "initial.expect must be a mapping")
    _validate_expect(
        expect,
        case_id,
        yaml_path,
        "initial.expect",
        runners,
        allowed_fields=_ALLOWED_INITIAL_CONSTRUCTOR_EXPECT_FIELDS,
    )
    if "raises" not in expect:
        raise _case_error(case_id, yaml_path, "initial.expect.raises is required")


def _validate_runtime_options(
    options: Any, case_id: str, yaml_path: str, runners: Sequence[str]
) -> None:
    if options is None:
        return
    if "simulation" not in runners or "generated_python_alignment" in runners:
        raise _case_error(
            case_id,
            yaml_path,
            "runtime_options are only supported by simulation-only cases",
        )
    if not isinstance(options, dict):
        raise _case_error(case_id, yaml_path, "runtime_options must be a mapping")
    unknown = set(options.keys()) - _ALLOWED_RUNTIME_OPTION_FIELDS
    if unknown:
        raise _case_error(
            case_id,
            yaml_path,
            "runtime_options has unknown fields: %r" % sorted(unknown),
        )
    if (
        "abstract_error_mode" in options
        and options["abstract_error_mode"] not in _ALLOWED_ABSTRACT_ERROR_MODES
    ):
        raise _case_error(
            case_id,
            yaml_path,
            "runtime_options.abstract_error_mode is invalid: %r"
            % options["abstract_error_mode"],
        )


def _validate_cycle_event_item(
    item: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if isinstance(item, str):
        return
    if not isinstance(item, dict):
        raise _case_error(
            case_id,
            yaml_path,
            "%s must be a string or event descriptor" % field_path,
        )
    if set(item.keys()) != {"event"}:
        raise _case_error(
            case_id,
            yaml_path,
            "%s event descriptor must contain only event" % field_path,
        )
    if not isinstance(item["event"], str):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.event must be a string" % field_path,
        )


def _validate_cycle_data(
    cycle_data: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if cycle_data in (None, {}):
        return
    if isinstance(cycle_data, str):
        return
    if not isinstance(cycle_data, dict):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle must be a mapping, string, or null" % field_path,
        )
    unknown_cycle = set(cycle_data.keys()) - _ALLOWED_CYCLE_FIELDS
    if unknown_cycle:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle has unknown fields: %r" % (field_path, sorted(unknown_cycle)),
        )
    if "events" not in cycle_data:
        return
    events = cycle_data["events"]
    if events is None:
        return
    if not isinstance(events, list):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle.events must be a list or null" % field_path,
        )
    for event_index, item in enumerate(events):
        _validate_cycle_event_item(
            item,
            case_id,
            yaml_path,
            "%s.cycle.events[%d]" % (field_path, event_index),
        )


def _validate_handlers(
    handlers: Any, case_id: str, yaml_path: str, runners: Sequence[str]
) -> None:
    if handlers is None:
        return
    if "simulation" not in runners:
        raise _case_error(
            case_id,
            yaml_path,
            "handlers require the simulation runner",
        )
    if not isinstance(handlers, list):
        raise _case_error(case_id, yaml_path, "handlers must be a list")
    for index, item in enumerate(handlers):
        if not isinstance(item, dict):
            raise _case_error(
                case_id,
                yaml_path,
                "handlers[%d] must be a mapping" % index,
            )
        unknown = set(item.keys()) - _ALLOWED_HANDLER_FIELDS
        if unknown:
            raise _case_error(
                case_id,
                yaml_path,
                "handlers[%d] has unknown fields: %r" % (index, sorted(unknown)),
            )
        for field_name in ("action", "behavior"):
            if field_name not in item:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].%s is required" % (index, field_name),
                )
            if not isinstance(item[field_name], str):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].%s must be a string" % (index, field_name),
                )
        if item["behavior"] not in _ALLOWED_HANDLER_BEHAVIORS:
            raise _case_error(
                case_id,
                yaml_path,
                "handlers[%d].behavior is invalid: %r" % (index, item["behavior"]),
            )
        if item["behavior"] != "raise_error" and "exception" in item:
            raise _case_error(
                case_id,
                yaml_path,
                "handlers[%d].exception is only allowed for raise_error" % index,
            )
        if item["behavior"] != "record_var_write_attempt" and "write" in item:
            raise _case_error(
                case_id,
                yaml_path,
                "handlers[%d].write is only allowed for record_var_write_attempt"
                % index,
            )
        if item["behavior"] == "record_var_write_attempt":
            write_data = item.get("write")
            if not isinstance(write_data, dict):
                raise _case_error(
                    case_id, yaml_path, "handlers[%d].write must be a mapping" % index
                )
            unknown_write = set(write_data.keys()) - _ALLOWED_HANDLER_WRITE_FIELDS
            if unknown_write:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].write has unknown fields: %r"
                    % (index, sorted(unknown_write)),
                )
            if "name" not in write_data:
                raise _case_error(
                    case_id, yaml_path, "handlers[%d].write.name is required" % index
                )
            if not isinstance(write_data["name"], str):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].write.name must be a string" % index,
                )
            if "value" not in write_data:
                raise _case_error(
                    case_id, yaml_path, "handlers[%d].write.value is required" % index
                )
        exception_data = item.get("exception")
        if item["behavior"] == "raise_error":
            if exception_data is None:
                exception_data = {}
            if not isinstance(exception_data, dict):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].exception must be a mapping" % index,
                )
            unknown_exception = (
                set(exception_data.keys()) - _ALLOWED_HANDLER_EXCEPTION_FIELDS
            )
            if unknown_exception:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].exception has unknown fields: %r"
                    % (index, sorted(unknown_exception)),
                )
            exception_type = exception_data.get("type", "ValueError")
            if exception_type not in _ALLOWED_HANDLER_EXCEPTION_TYPES:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].exception.type is invalid: %r"
                    % (index, exception_type),
                )
            if "message" in exception_data and not isinstance(
                exception_data["message"], str
            ):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].exception.message must be a string" % index,
                )


def validate_pure_shared_fixture_boundary(
    data: Mapping[str, Any], yaml_path: str
) -> None:
    """
    Validate the stricter shared-fixture boundary for new shared cases.

    The boundary check is intentionally narrower than the full loader schema.
    It is designed for PRs that add or rewrite shared semantic fixtures and
    should not be applied to the existing legacy corpus all at once. The helper
    enforces the pure shared contract: both runtimes must be present, and the
    case may only use the public observation surface that is stable across the
    simulator and generated Python alignment runtime.

    :param data: Parsed fixture YAML mapping.
    :type data: typing.Mapping[str, typing.Any]
    :param yaml_path: Absolute path to the fixture YAML file.
    :type yaml_path: str
    :return: ``None``.
    :rtype: None
    :raises SemanticCaseError: If the fixture violates the new shared boundary.

    Example::

        >>> validate_pure_shared_fixture_boundary(
        ...     {
        ...         "id": "shared_case",
        ...         "runners": ["simulation", "generated_python_alignment"],
        ...         "steps": [
        ...             {
        ...                 "cycle": {},
        ...                 "expect": {
        ...                     "state": ["Root", "A"],
        ...                     "cycle_result": {"value": None},
        ...                 },
        ...             }
        ...         ],
        ...     },
        ...     "/tmp/shared_case.yaml",
        ... )
        >>> validate_pure_shared_fixture_boundary(
        ...     {
        ...         "id": "legacy_case",
        ...         "runners": ["simulation", "generated_python_alignment"],
        ...         "steps": [{"expect": {"return": None}}],
        ...     },
        ...     "/tmp/legacy_case.yaml",
        ... )
        Traceback (most recent call last):
        ...
        test.testings.simulate_semantics.SemanticCaseError: legacy_case (/tmp/legacy_case.yaml): pure shared fixture has forbidden expectation fields: ['return']
    """
    case_id = str(data.get("id", "<unknown>")) if isinstance(data, dict) else "<unknown>"
    if not isinstance(data, dict):
        raise _case_error(case_id, yaml_path, "fixture data must be a mapping")
    runners = data.get("runners")
    if not isinstance(runners, list) or not runners:
        raise _case_error(case_id, yaml_path, "runners must be a non-empty list")
    unknown_runners = set(runners) - _ALLOWED_RUNNERS
    if unknown_runners:
        raise _case_error(
            case_id, yaml_path, "unknown runners: %r" % sorted(unknown_runners)
        )
    if "cli_command" in runners:
        raise _case_error(
            case_id,
            yaml_path,
            "pure shared fixture cannot use cli_command runner",
        )
    missing_runners = _PURE_SHARED_REQUIRED_RUNNERS - set(runners)
    if missing_runners:
        raise _case_error(
            case_id,
            yaml_path,
            "pure shared fixture requires runners: %r" % sorted(missing_runners),
        )
    forbidden_top_level = _PURE_SHARED_FORBIDDEN_TOP_LEVEL_FIELDS & set(data.keys())
    if forbidden_top_level:
        raise _case_error(
            case_id,
            yaml_path,
            "pure shared fixture has forbidden top-level fields: %r"
            % sorted(forbidden_top_level),
        )
    if "initial" in data and data.get("initial") is not None:
        initial = data["initial"]
        if not isinstance(initial, dict):
            raise _case_error(case_id, yaml_path, "initial must be a mapping")
        if "expect" in initial:
            raise _case_error(
                case_id,
                yaml_path,
                "pure shared fixture cannot use initial.expect diagnostics",
            )
    if "handlers" in data:
        handlers = data["handlers"]
        if not isinstance(handlers, list):
            raise _case_error(case_id, yaml_path, "handlers must be a list")
        for handler_index, handler in enumerate(handlers):
            if not isinstance(handler, dict):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d] must be a mapping" % handler_index,
                )
            behavior = handler.get("behavior")
            if behavior not in _PURE_SHARED_HANDLER_BEHAVIORS:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "pure shared fixture only allows handlers[%d] with behavior %r"
                    % (handler_index, sorted(_PURE_SHARED_HANDLER_BEHAVIORS)),
                )
            if "exception" in handler:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "pure shared fixture does not allow handlers[%d].exception"
                    % handler_index,
                )
            if "write" in handler:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "pure shared fixture does not allow handlers[%d].write"
                    % handler_index,
                )
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise _case_error(case_id, yaml_path, "pure shared fixture requires steps")
    if not steps:
        raise _case_error(
            case_id, yaml_path, "pure shared fixture requires non-empty steps"
        )
    for step_index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise _case_error(
                case_id, yaml_path, "steps[%d] must be a mapping" % step_index
            )
        for expect_name in ("expect_initial", "expect"):
            expect = step.get(expect_name)
            if not isinstance(expect, dict):
                continue
            forbidden_expect = _PURE_SHARED_FORBIDDEN_EXPECT_FIELDS & set(expect.keys())
            if forbidden_expect:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "pure shared fixture has forbidden expectation fields: %r"
                    % sorted(forbidden_expect),
                )
            public_expect = _PURE_SHARED_PUBLIC_EXPECT_FIELDS & set(expect.keys())
            if not public_expect:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s requires public observation fields" % expect_name,
                )
            if "handler_calls" in expect and not data.get("handlers"):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handler_calls requires top-level handlers",
                )


def _validate_case_data(data: Mapping[str, Any], yaml_path: str) -> None:
    case_id = str(data.get("id", "<unknown>"))
    unknown = set(data.keys()) - _ALLOWED_TOP_LEVEL_FIELDS
    if unknown:
        raise _case_error(
            case_id, yaml_path, "unknown top-level fields: %r" % sorted(unknown)
        )
    if data.get("schema_version") != 1:
        raise _case_error(case_id, yaml_path, "schema_version must be 1")
    boundary = data.get("boundary")
    if "boundary" in data and (
        not isinstance(boundary, str) or boundary not in _ALLOWED_BOUNDARIES
    ):
        raise _case_error(
            case_id,
            yaml_path,
            "unknown boundary: %r" % boundary,
        )
    if not data.get("id"):
        raise _case_error(case_id, yaml_path, "id is required")
    if not data.get("title") or not isinstance(data.get("title"), str):
        raise _case_error(case_id, yaml_path, "title is required")
    if os.path.splitext(os.path.basename(yaml_path))[0] != case_id:
        raise _case_error(case_id, yaml_path, "id must match YAML file name")
    _validate_source(data.get("source"), case_id, yaml_path)
    _validate_origin(data.get("origin"), case_id, yaml_path)
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise _case_error(case_id, yaml_path, "categories must be a non-empty list")
    unknown_categories = set(categories) - _ALLOWED_CATEGORIES
    if unknown_categories:
        raise _case_error(
            case_id, yaml_path, "unknown categories: %r" % sorted(unknown_categories)
        )
    runners = data.get("runners")
    if not isinstance(runners, list) or not runners:
        raise _case_error(case_id, yaml_path, "runners must be a non-empty list")
    unknown_runners = set(runners) - _ALLOWED_RUNNERS
    if unknown_runners:
        raise _case_error(
            case_id, yaml_path, "unknown runners: %r" % sorted(unknown_runners)
        )
    if "cli_command" in runners and len(runners) != 1:
        raise _case_error(
            case_id, yaml_path, "cli_command cannot be mixed with other runners"
        )
    if "generated_python_alignment" in runners and "simulation" not in runners:
        raise _case_error(
            case_id,
            yaml_path,
            "generated_python_alignment requires the simulation runner",
        )
    _validate_initial(data.get("initial"), case_id, yaml_path, runners)
    _validate_runtime_options(data.get("runtime_options"), case_id, yaml_path, runners)
    _validate_handlers(data.get("handlers"), case_id, yaml_path, runners)
    _validate_model_build(data.get("model_build"), case_id, yaml_path, runners)
    has_model_build = "model_build" in data
    has_steps = "steps" in data
    has_commands = "commands" in data
    if sum(1 for item in (has_model_build, has_steps, has_commands) if item) != 1:
        raise _case_error(
            case_id,
            yaml_path,
            "exactly one of model_build, steps, or commands is required",
        )
    if "cli_command" in runners and not has_commands:
        raise _case_error(case_id, yaml_path, "cli_command cases require commands")
    if "cli_command" not in runners and not has_steps and not has_model_build:
        raise _case_error(case_id, yaml_path, "runtime cases require steps")
    if "expected_failure" in data:
        raise _case_error(
            case_id,
            yaml_path,
            "expected_failure is reserved for inactive regression fixtures",
        )
    has_initial_constructor_expect = _initial_constructor_expect_data(
        data.get("initial")
    )
    if has_initial_constructor_expect:
        if not has_steps:
            raise _case_error(
                case_id,
                yaml_path,
                "initial.expect.raises cases require empty steps",
            )
        if data["steps"]:
            raise _case_error(
                case_id,
                yaml_path,
                "initial.expect.raises cases require empty steps",
            )
    if has_steps:
        if not isinstance(data["steps"], list):
            raise _case_error(case_id, yaml_path, "steps must be a list")
        for index, step in enumerate(data["steps"]):
            if not isinstance(step, dict):
                raise _case_error(
                    case_id, yaml_path, "steps[%d] must be a mapping" % index
                )
            field_path = "steps[%d]" % index
            if "expect_initial" in step:
                unknown_step = set(step.keys()) - {"expect_initial"}
                if unknown_step:
                    raise _case_error(
                        case_id,
                        yaml_path,
                        "%s has unknown fields: %r"
                        % (
                            field_path,
                            sorted(unknown_step),
                        ),
                    )
                _validate_expect(
                    step["expect_initial"],
                    case_id,
                    yaml_path,
                    field_path + ".expect_initial",
                    runners,
                    allowed_fields=_ALLOWED_INITIAL_EXPECT_FIELDS,
                )
            else:
                unknown_step = set(step.keys()) - {"cycle", "expect"}
                if unknown_step:
                    raise _case_error(
                        case_id,
                        yaml_path,
                        "%s has unknown fields: %r"
                        % (
                            field_path,
                            sorted(unknown_step),
                        ),
                    )
                if "cycle" not in step:
                    raise _case_error(
                        case_id,
                        yaml_path,
                        "%s must contain cycle or expect_initial" % field_path,
                    )
                if "expect" not in step:
                    raise _case_error(
                        case_id, yaml_path, "%s.expect is required" % field_path
                    )
                _validate_cycle_data(step.get("cycle"), case_id, yaml_path, field_path)
                _validate_expect(
                    step["expect"], case_id, yaml_path, field_path + ".expect", runners
                )
    if has_commands:
        if not isinstance(data["commands"], list):
            raise _case_error(case_id, yaml_path, "commands must be a list")
        for index, command in enumerate(data["commands"]):
            if not isinstance(command, dict) or "input" not in command:
                raise _case_error(
                    case_id, yaml_path, "commands[%d].input is required" % index
                )
            unknown_command = set(command.keys()) - {"input", "expect"}
            if unknown_command:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "commands[%d] has unknown fields: %r"
                    % (
                        index,
                        sorted(unknown_command),
                    ),
                )
            if not isinstance(command["input"], str):
                raise _case_error(
                    case_id, yaml_path, "commands[%d].input must be a string" % index
                )
            expect = command.get("expect") or {}
            if not isinstance(expect, dict):
                raise _case_error(
                    case_id, yaml_path, "commands[%d].expect must be a mapping" % index
                )
            unknown_expect = set(expect.keys()) - _ALLOWED_CLI_EXPECT_FIELDS
            if unknown_expect:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "commands[%d].expect has unknown fields: %r"
                    % (
                        index,
                        sorted(unknown_expect),
                    ),
                )
            for field_name in _CLI_OUTPUT_FIELDS:
                if field_name in expect:
                    _validate_string_list(
                        expect[field_name],
                        case_id,
                        yaml_path,
                        "commands[%d].expect.%s" % (index, field_name),
                    )
            if "should_exit" in expect and not isinstance(expect["should_exit"], bool):
                raise _case_error(
                    case_id,
                    yaml_path,
                    "commands[%d].expect.should_exit must be a boolean" % index,
                )
            if "runtime" in expect:
                _validate_expect(
                    expect["runtime"],
                    case_id,
                    yaml_path,
                    "commands[%d].expect.runtime" % index,
                    runners,
                    allowed_fields=_ALLOWED_CLI_RUNTIME_FIELDS,
                )


def load_semantic_case(path_or_id: str) -> SemanticCase:
    """
    Load a semantic fixture by case id or YAML path.

    A bare case id is resolved under ``test/fixtures/simulate_semantics/cases``.
    A path ending in ``.yaml`` is loaded directly. The loader validates the
    strict schema before reading the paired FCSTM source file.

    :param path_or_id: Fixture id or path to a YAML fixture file.
    :type path_or_id: str
    :return: Loaded semantic fixture.
    :rtype: SemanticCase
    :raises SemanticCaseError: If the YAML shape, schema fields, or paired FCSTM
        path are invalid.

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> case.yaml_path.endswith("design_basic_simple_transition.yaml")
        True
    """
    yaml_path = path_or_id
    if (
        not yaml_path.endswith(".yaml")
        and os.sep not in yaml_path
        and "/" not in yaml_path
    ):
        yaml_path = os.path.join(CASE_DIR, path_or_id + ".yaml")
    yaml_path = os.path.abspath(yaml_path)
    with open(yaml_path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise SemanticCaseError("%s: fixture YAML must be a mapping" % yaml_path)
    _validate_case_data(data, yaml_path)
    if data.get("boundary") == _PURE_SHARED_BOUNDARY:
        validate_pure_shared_fixture_boundary(data, yaml_path)
    fcstm_path = os.path.join(os.path.dirname(yaml_path), data["source"]["fcstm"])
    if not os.path.isfile(fcstm_path):
        raise _case_error(
            str(data["id"]), yaml_path, "source.fcstm does not exist: %s" % fcstm_path
        )
    with open(fcstm_path, "r", encoding="utf-8") as file:
        dsl_code = file.read()
    return SemanticCase(
        data=data, yaml_path=yaml_path, fcstm_path=fcstm_path, dsl_code=dsl_code
    )


def iter_semantic_cases(
    categories: Optional[Iterable[str]] = None, runners: Optional[Iterable[str]] = None
) -> List[SemanticCase]:
    """
    Iterate semantic fixtures, optionally filtered by categories or runners.

    Filters are subset matches: a case is returned only when it contains every
    requested category and every requested runner. Cases are loaded in sorted
    YAML filename order to keep pytest parametrization stable.

    :param categories: Optional category names that each returned case must
        contain, defaults to ``None``.
    :type categories: typing.Optional[typing.Iterable[str]], optional
    :param runners: Optional runner names that each returned case must contain,
        defaults to ``None``.
    :type runners: typing.Optional[typing.Iterable[str]], optional
    :return: Loaded semantic fixtures matching the filters.
    :rtype: typing.List[SemanticCase]
    :raises SemanticCaseError: If any loaded fixture is malformed.

    Example::

        >>> cases = iter_semantic_cases(runners=["simulation"])
        >>> all("simulation" in case.runners for case in cases)
        True
    """
    category_set = set(categories or [])
    runner_set = set(runners or [])
    result = []
    for name in sorted(os.listdir(CASE_DIR)):
        if not name.endswith(".yaml"):
            continue
        case = load_semantic_case(os.path.join(CASE_DIR, name))
        if category_set and not category_set.issubset(set(case.data["categories"])):
            continue
        if runner_set and not runner_set.issubset(set(case.runners)):
            continue
        result.append(case)
    return result

"""
Shared helpers for simulate semantic fixture tests.

This module loads YAML/FCSTM semantic fixtures from
``test/fixtures/simulate_semantics`` and runs them against
:class:`pyfcstm.simulate.SimulationRuntime` or the generated Python alignment
runtime. It owns the strict fixture schema, runtime assertion helpers, and
callback fixtures used by Python-side simulation tests.

The module contains:

* :class:`SemanticCase` - Loaded fixture data and source paths.
* :class:`SemanticCaseError` - Schema and fixture-shape diagnostics.
* :func:`load_semantic_case` - Load one fixture by id or YAML path.
* :func:`iter_semantic_cases` - Enumerate fixture cases with optional filters.
* :func:`is_runner_excluded` - Check non-default runner exclusions without
  adding them to the default fixture runner set.
* :func:`validate_shared_fixture_contract` - Check the shared public
  observation contract.
* :func:`run_simulation_case` - Execute one case against
  :class:`pyfcstm.simulate.SimulationRuntime`.

Example::

    >>> case = load_semantic_case("design_basic_simple_transition")
    >>> case.id
    'design_basic_simple_transition'
"""

import importlib.util
import os
import re
from dataclasses import dataclass
from tempfile import TemporaryDirectory
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.simulate import (
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
    "title",
    "origin",
    "categories",
    "exclude_runners",
    "initial",
    "steps",
    "handlers",
}
_ALLOWED_ORIGIN_FIELDS = {"files", "docs", "notes"}
_ALLOWED_CATEGORIES = {
    "runtime",
    "template_alignment",
    "design_example",
    "scenario_example",
    "hot_start",
    "event_paths",
    "temporary_vars",
    "if_blocks",
    "abstract",
    "pseudo_chain",
    "validation",
    "lifecycle",
}
_DEFAULT_SHARED_RUNNERS = ("simulation", "generated_python_alignment")
BMC_CORE_RUNNER = "bmc_core"
_ALLOWED_EXCLUDE_RUNNERS = set(_DEFAULT_SHARED_RUNNERS) | {BMC_CORE_RUNNER}
_ALLOWED_EXPECT_FIELDS = {
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "raises",
    "handler_calls",
}
_ALLOWED_INITIAL_FIELDS = {"state", "vars", "expect"}
_ALLOWED_INITIAL_CONSTRUCTOR_EXPECT_FIELDS = {"raises"}
_ALLOWED_RAISES_FIELDS = {
    "type",
    "match",
    "match_kind",
    "cause_type",
    "cause_match",
    "cause_match_kind",
}
_ALLOWED_HANDLER_FIELDS = {"action", "behavior"}
_ALLOWED_HANDLER_BEHAVIORS = {"record_call"}
_REQUIRED_HANDLER_CALL_FIELDS = {"action", "state", "stage", "vars"}
_ALLOWED_HANDLER_CALL_FIELDS = _REQUIRED_HANDLER_CALL_FIELDS | {
    "active_leaf",
    "call_stage",
    "abstract_target",
    "named_ref",
}
_PUBLIC_EXPECT_FIELDS = {
    "state",
    "vars",
    "vars_exact",
    "vars_keys",
    "vars_absent",
    "ended",
    "raises",
    "handler_calls",
}
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
    can safely reuse it across parametrized simulation and generated-runtime
    alignment runners.

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
        return os.path.splitext(os.path.basename(self.yaml_path))[0]

    @property
    def runners(self) -> Sequence[str]:
        return _effective_runners_from_data(self.data, self.id, self.yaml_path)


def is_runner_excluded(case: SemanticCase, runner: str) -> bool:
    """
    Return whether a fixture excludes a non-default runner.

    The shared fixture schema remains exclude-only.  Default simulation and
    generated-runtime runners use :attr:`SemanticCase.runners`; additional
    maintenance runners such as ``"bmc_core"`` are checked directly from
    ``exclude_runners`` so they do not become default simulation coverage.

    :param case: Loaded semantic fixture.
    :type case: SemanticCase
    :param runner: Runner name to check.
    :type runner: str
    :return: Whether ``runner`` appears in ``case.data['exclude_runners']``.
    :rtype: bool
    :raises SemanticCaseError: If ``runner`` is not a known exclude runner.

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> is_runner_excluded(case, BMC_CORE_RUNNER)
        False
    """
    if runner not in _ALLOWED_EXCLUDE_RUNNERS:
        raise _case_error(
            case.id,
            case.yaml_path,
            "unknown runner for exclusion check: %r" % runner,
        )
    return runner in set(case.data.get("exclude_runners") or ())


def _case_error(case_id: str, yaml_path: str, message: str) -> SemanticCaseError:
    return SemanticCaseError("%s (%s): %s" % (case_id, yaml_path, message))


def _validate_runner_list(
    value: Any,
    case_id: str,
    yaml_path: str,
    field_path: str,
    allowed_runners: Iterable[str],
) -> Tuple[str, ...]:
    if not isinstance(value, list) or not value:
        raise _case_error(
            case_id, yaml_path, "%s must be a non-empty list" % field_path
        )
    if not all(isinstance(item, str) for item in value):
        raise _case_error(
            case_id, yaml_path, "%s must be a list of strings" % field_path
        )
    duplicates = sorted(item for item in set(value) if value.count(item) > 1)
    if duplicates:
        raise _case_error(
            case_id,
            yaml_path,
            "%s has duplicate runners: %r" % (field_path, duplicates),
        )
    unknown_runners = set(value) - set(allowed_runners)
    if unknown_runners:
        raise _case_error(
            case_id,
            yaml_path,
            "%s has unknown runners: %r" % (field_path, sorted(unknown_runners)),
        )
    return tuple(value)


def _effective_runners_from_data(
    data: Mapping[str, Any], case_id: str, yaml_path: str
) -> Tuple[str, ...]:
    if "exclude_runners" in data:
        excluded = _validate_runner_list(
            data["exclude_runners"],
            case_id,
            yaml_path,
            "exclude_runners",
            _ALLOWED_EXCLUDE_RUNNERS,
        )
    else:
        excluded = tuple()
    effective = tuple(
        runner for runner in _DEFAULT_SHARED_RUNNERS if runner not in set(excluded)
    )
    if not effective:
        raise _case_error(
            case_id,
            yaml_path,
            "exclude_runners cannot remove all default runners",
        )
    if "generated_python_alignment" in effective and "simulation" not in effective:
        raise _case_error(
            case_id,
            yaml_path,
            "generated_python_alignment requires the simulation runner",
        )
    return effective


def _path_segments_from_dot_string(
    value: Any, case_id: str, yaml_path: str, field_path: str
) -> Optional[Tuple[str, ...]]:
    if value is None:
        return None
    if not isinstance(value, str) or not value:
        raise _case_error(
            case_id,
            yaml_path,
            "%s must be a dot-separated state path string or null" % field_path,
        )
    parts = value.split(".")
    if any(not part for part in parts):
        raise _case_error(
            case_id,
            yaml_path,
            "%s must be a dot-separated state path string or null" % field_path,
        )
    return tuple(parts)


def _as_tuple_path(
    value: Any, case: SemanticCase, field_path: str
) -> Optional[Tuple[str, ...]]:
    return _path_segments_from_dot_string(value, case.id, case.yaml_path, field_path)


def _vars_dict(runtime: Any) -> Dict[str, Any]:
    return dict(runtime.vars)


def _runtime_state_path(runtime: Any) -> Optional[Tuple[str, ...]]:
    if getattr(runtime, "is_ended"):
        return None
    current_state = getattr(runtime, "current_state")
    if current_state is None:
        return None
    return tuple(current_state.path)


def _handler_call_comparable_record(actual: Mapping[str, Any]) -> Dict[str, Any]:
    result = dict(actual)
    state = actual.get("state")
    # Handlers may provide optional metadata directly. When a record omits an
    # optional field, derive the stable public value from required call data.
    result.setdefault("active_leaf", state if isinstance(state, str) else None)
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

    _assert_handler_calls(expect, handler_calls, case, field_path)


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


def _event_input_from_fixture_item(
    item: Any, runtime: Any, case: SemanticCase, field_path: str
) -> Any:
    if isinstance(item, str):
        return item
    raise _case_error(
        case.id,
        case.yaml_path,
        "%s must be a string event path" % field_path,
    )


def _step_events(
    cycle_data: Any, runtime: Any, case: SemanticCase, field_path: str
) -> Any:
    if isinstance(cycle_data, str):
        return cycle_data
    if isinstance(cycle_data, list):
        return [
            _event_input_from_fixture_item(
                item,
                runtime,
                case,
                "%s.cycle[%d]" % (field_path, index),
            )
            for index, item in enumerate(cycle_data)
        ]
    raise _case_error(
        case.id,
        case.yaml_path,
        "%s.cycle must be a string event path or a list of string event paths"
        % field_path,
    )


def _effective_cycle_count(
    step: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> int:
    if "cycle_count" in step:
        cycle_count = step["cycle_count"]
        if not isinstance(cycle_count, int) or isinstance(cycle_count, bool):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.cycle_count must be a non-negative integer" % field_path,
            )
        if cycle_count < 0:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.cycle_count must be a non-negative integer" % field_path,
            )
        return cycle_count
    return 1


def _cycle_input_for_step(
    step: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> Any:
    if "cycle" not in step:
        return []
    cycle_data = step["cycle"]
    if isinstance(cycle_data, str):
        return cycle_data
    if isinstance(cycle_data, list):
        return cycle_data
    if isinstance(cycle_data, dict):
        if not cycle_data:
            raise _case_error(
                case_id, yaml_path, "%s.cycle: {} is not valid v2" % field_path
            )
        if "events" in cycle_data:
            raise _case_error(
                case_id,
                yaml_path,
                "%s.cycle.events is not valid v2; use cycle: <event> or cycle: [<event>]"
                % field_path,
            )
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle must be a string event path or a list of string event paths"
            % field_path,
        )
    if cycle_data is None:
        raise _case_error(
            case_id, yaml_path, "%s.cycle: null is not valid v2" % field_path
        )
    raise _case_error(
        case_id,
        yaml_path,
        "%s.cycle must be a string event path or a list of string event paths"
        % field_path,
    )


def _validate_cycle_input_items(
    cycle_input: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    if isinstance(cycle_input, str):
        return
    if not isinstance(cycle_input, list):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle must be a string event path or a list of string event paths"
            % field_path,
        )
    for index, item in enumerate(cycle_input):
        if not isinstance(item, str):
            raise _case_error(
                case_id,
                yaml_path,
                "%s.cycle[%d] must be a string event path" % (field_path, index),
            )


def _cycle_input_is_non_empty(cycle_input: Any) -> bool:
    if isinstance(cycle_input, str):
        return True
    return bool(cycle_input)


def _validate_step_cycle_shape(
    step: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "cycle" not in step and "cycle_count" not in step:
        raise _case_error(
            case_id,
            yaml_path,
            "%s must contain cycle or cycle_count" % field_path,
        )
    cycle_count = _effective_cycle_count(step, case_id, yaml_path, field_path)
    cycle_input = _cycle_input_for_step(step, case_id, yaml_path, field_path)
    _validate_cycle_input_items(cycle_input, case_id, yaml_path, field_path)
    if cycle_count == 0 and _cycle_input_is_non_empty(cycle_input):
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle_count: 0 cannot have non-empty cycle" % field_path,
        )


def _run_step(
    runtime: Any,
    step: Mapping[str, Any],
    case: SemanticCase,
    index: int,
    handler_calls: Optional[Sequence[Mapping[str, Any]]] = None,
) -> None:
    field_path = "steps[%d]" % index
    expect = step.get("expect") or {}
    cycle_count = _effective_cycle_count(step, case.id, case.yaml_path, field_path)
    cycle_input = _cycle_input_for_step(step, case.id, case.yaml_path, field_path)
    events = _step_events(cycle_input, runtime, case, field_path)
    if "raises" in expect:
        try:
            runtime.cycle(events)
        except Exception as err:
            # Runtime/generator errors intentionally propagate through the
            # fixture contract; expected semantic errors are matched here.
            _assert_exception(err, expect, case, field_path + ".expect.raises")
        else:
            raise AssertionError(
                "%s %s expected exception %r" % (case.id, field_path, expect["raises"])
            )
    else:
        for _ in range(cycle_count):
            runtime.cycle(events)
    _assert_runtime_expectation(
        runtime,
        expect,
        case,
        field_path + ".expect",
        handler_calls=handler_calls,
    )


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
    return _initial_kwargs(case)


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
            record[name] = ".".join(value) if isinstance(value, tuple) else value
    return record


def _run_fixture_handler(
    handler_data: Mapping[str, Any], ctx: Any, calls: List[Mapping[str, Any]]
) -> None:
    behavior = handler_data["behavior"]
    if behavior == "record_call":
        calls.append(_handler_call_record(ctx))
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
        Return the simulator model used for generated-runtime alignment.

        Schema v2 fixtures pass only string event paths or lists of string event
        paths to :meth:`cycle`. The state machine remains available here for
        alignment diagnostics and for callers that need to inspect the
        authoritative simulator model while comparing generated behavior.

        :return: State machine model owned by the simulation runtime.
        :rtype: pyfcstm.model.StateMachine

        Example::

            >>> case = load_semantic_case("event_input_model_event_object")
            >>> runtime = _build_simulation_runtime(case)
            >>> runtime.state_machine is not None
            True
        """
        return self._simulation_runtime.state_machine

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

    def cycle(self, events: Optional[Sequence[Any]] = None) -> Any:
        sim_exc = None
        gen_exc = None
        try:
            sim_result = self._simulation_runtime.cycle(events)
        except Exception as err:
            # SimulationRuntime may raise any documented runtime semantic error;
            # alignment compares its class name with the generated runtime.
            sim_exc = err
        try:
            self._generated_runtime.cycle(events)
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


def run_simulation_case(case: SemanticCase) -> None:
    """
    Run a semantic fixture against :class:`SimulationRuntime`.

    The runner builds the production simulator, installs any fixture-defined
    abstract handlers, executes each step, and applies the strict YAML
    expectations for state, variables, exceptions, and public
    hook-call records.

    :param case: Semantic fixture to execute with the simulation runner.
    :type case: SemanticCase
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
            handler_calls=handler_calls,
        )


def run_generated_python_alignment_case(case: SemanticCase) -> None:
    """
    Run a semantic fixture against simulation and generated Python runtimes.

    The alignment runner generates the built-in Python runtime for the case DSL,
    executes it beside :class:`SimulationRuntime`, and asserts that public state,
    variables, exceptions, and handler calls remain aligned after
    every fixture step.

    :param case: Semantic fixture that includes the
        ``generated_python_alignment`` runner.
    :type case: SemanticCase
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
            handler_calls=simulation_handler_calls,
        )
        simulation_calls = _normalize_handler_call_records(simulation_handler_calls)
        generated_calls = _normalize_handler_call_records(generated_handler_calls)
        assert simulation_calls == generated_calls, (
            "%s steps[%d] handler call mismatch: simulation=%r, generated=%r"
            % (case.id, index, simulation_calls, generated_calls)
        )


def _validate_vars_contract(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "vars" in expect and "vars_exact" in expect:
        raise _case_error(
            case_id,
            yaml_path,
            "%s vars and vars_exact conflict" % field_path,
        )
    if "vars_exact" in expect and "vars_keys" in expect:
        raise _case_error(
            case_id,
            yaml_path,
            "%s vars_exact and vars_keys conflict" % field_path,
        )
    if "vars_exact" in expect and "vars_absent" in expect:
        raise _case_error(
            case_id,
            yaml_path,
            "%s vars_exact and vars_absent conflict" % field_path,
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


def _validate_raises(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    if "raises" not in expect:
        return
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
        if "active_leaf" in item:
            _validate_dot_state_path(
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


def _validate_dot_state_path(
    value: Any, case_id: str, yaml_path: str, field_path: str
) -> None:
    _path_segments_from_dot_string(value, case_id, yaml_path, field_path)


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
    if "state" in expect:
        _validate_dot_state_path(
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
    if "ended" in expect and not isinstance(expect["ended"], bool):
        raise _case_error(case_id, yaml_path, "%s.ended must be a boolean" % field_path)
    if "state" in expect and "ended" in expect:
        if expect["state"] is None and expect["ended"] is False:
            raise _case_error(
                case_id,
                yaml_path,
                "%s state and ended conflict" % field_path,
            )
        if expect["state"] is not None and expect["ended"] is True:
            raise _case_error(
                case_id,
                yaml_path,
                "%s state and ended conflict" % field_path,
            )
    _validate_vars_contract(expect, case_id, yaml_path, field_path)
    _validate_raises(expect, case_id, yaml_path, field_path)
    _validate_handler_calls(expect, case_id, yaml_path, field_path)


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
    for field_name in ("docs", "notes"):
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
    if initial.get("state") is not None:
        _validate_dot_state_path(
            initial.get("state"), case_id, yaml_path, "initial.state"
        )
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


def validate_shared_fixture_contract(data: Mapping[str, Any], yaml_path: str) -> None:
    """
    Validate the shared semantic fixture contract.

    The fixture corpus has a single current schema: every case is shared by
    default, uses exclude-only runner selection, and may only assert public
    observations that are stable across the simulator and generated Python
    alignment runtime. This guard enforces the shared public-observation
    surface; :func:`load_semantic_case` applies the full fixture schema before
    constructing a :class:`SemanticCase`.

    :param data: Parsed fixture YAML mapping.
    :type data: typing.Mapping[str, typing.Any]
    :param yaml_path: Absolute path to the fixture YAML file.
    :type yaml_path: str
    :return: ``None``.
    :rtype: None
    :raises SemanticCaseError: If the fixture violates the shared contract.

    Example::

        >>> validate_shared_fixture_contract(
        ...     {
        ...         "title": "shared case",
        ...         "origin": {"files": ["test/example.py::test_example"]},
        ...         "categories": ["runtime"],
        ...         "steps": [
        ...             {
        ...                 "cycle": [],
        ...                 "expect": {
        ...                     "state": "Root.A",
        ...                     "ended": False,
        ...                 },
        ...             }
        ...         ],
        ...     },
        ...     "/tmp/shared_case.yaml",
        ... )
        >>> validate_shared_fixture_contract(
        ...     {
        ...         "title": "bad case",
        ...         "origin": {"files": ["test/example.py::test_example"]},
        ...         "categories": ["runtime"],
        ...         "steps": [{"cycle": [], "expect": {"bogus": None}}],
        ...     },
        ...     "/tmp/bad_case.yaml",
        ... )
        Traceback (most recent call last):
        ...
        test.testings.simulate_semantics.SemanticCaseError: bad_case (/tmp/bad_case.yaml): steps[0].expect has unknown fields: ['bogus']
    """
    case_id = os.path.splitext(os.path.basename(yaml_path))[0]
    if not isinstance(data, dict):
        raise _case_error(case_id, yaml_path, "fixture data must be a mapping")
    unknown_top_level = set(data.keys()) - _ALLOWED_TOP_LEVEL_FIELDS
    if unknown_top_level:
        raise _case_error(
            case_id,
            yaml_path,
            "unknown top-level fields: %r" % sorted(unknown_top_level),
        )
    has_initial_expect = False
    if "initial" in data and data.get("initial") is not None:
        initial = data["initial"]
        if not isinstance(initial, dict):
            raise _case_error(case_id, yaml_path, "initial must be a mapping")
        has_initial_expect = "expect" in initial
        if has_initial_expect:
            initial_expect = initial["expect"]
            if not isinstance(initial_expect, dict):
                raise _case_error(
                    case_id, yaml_path, "initial.expect must be a mapping"
                )
            unknown_initial_expect = set(initial_expect.keys()) - (
                _ALLOWED_INITIAL_CONSTRUCTOR_EXPECT_FIELDS
            )
            if unknown_initial_expect:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "initial.expect has unknown fields: %r"
                    % sorted(unknown_initial_expect),
                )
            if "raises" not in initial_expect:
                raise _case_error(
                    case_id, yaml_path, "initial.expect.raises is required"
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
            unknown_handler = set(handler.keys()) - _ALLOWED_HANDLER_FIELDS
            if unknown_handler:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d] has unknown fields: %r"
                    % (handler_index, sorted(unknown_handler)),
                )
            behavior = handler.get("behavior")
            if behavior not in _ALLOWED_HANDLER_BEHAVIORS:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "handlers[%d].behavior is invalid: %r" % (handler_index, behavior),
                )
    steps = data.get("steps")
    if not isinstance(steps, list):
        raise _case_error(case_id, yaml_path, "shared fixture requires steps")
    if not steps and not has_initial_expect:
        raise _case_error(case_id, yaml_path, "shared fixture requires non-empty steps")
    for step_index, step in enumerate(steps):
        if not isinstance(step, dict):
            raise _case_error(
                case_id, yaml_path, "steps[%d] must be a mapping" % step_index
            )
        for expect_name in ("expect",):
            expect = step.get(expect_name)
            if not isinstance(expect, dict):
                continue
            field_path = "steps[%d].%s" % (step_index, expect_name)
            unknown_expect = set(expect.keys()) - _PUBLIC_EXPECT_FIELDS
            if unknown_expect:
                raise _case_error(
                    case_id,
                    yaml_path,
                    "%s has unknown fields: %r" % (field_path, sorted(unknown_expect)),
                )
            public_expect = _PUBLIC_EXPECT_FIELDS & set(expect.keys())
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
    case_id = os.path.splitext(os.path.basename(yaml_path))[0]
    unknown = set(data.keys()) - _ALLOWED_TOP_LEVEL_FIELDS
    if unknown:
        raise _case_error(
            case_id, yaml_path, "unknown top-level fields: %r" % sorted(unknown)
        )
    if not data.get("title") or not isinstance(data.get("title"), str):
        raise _case_error(case_id, yaml_path, "title is required")
    _validate_origin(data.get("origin"), case_id, yaml_path)
    categories = data.get("categories")
    if not isinstance(categories, list) or not categories:
        raise _case_error(case_id, yaml_path, "categories must be a non-empty list")
    unknown_categories = set(categories) - _ALLOWED_CATEGORIES
    if unknown_categories:
        raise _case_error(
            case_id, yaml_path, "unknown categories: %r" % sorted(unknown_categories)
        )
    runners = _effective_runners_from_data(data, case_id, yaml_path)
    _validate_initial(data.get("initial"), case_id, yaml_path, runners)
    _validate_handlers(data.get("handlers"), case_id, yaml_path, runners)
    has_steps = "steps" in data
    if not has_steps:
        raise _case_error(case_id, yaml_path, "shared fixture requires steps")
    has_initial_constructor_expect = _initial_constructor_expect_data(
        data.get("initial")
    )
    if has_initial_constructor_expect:
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
            unknown_step = set(step.keys()) - {"cycle", "cycle_count", "expect"}
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
            if "expect" not in step:
                raise _case_error(
                    case_id, yaml_path, "%s.expect is required" % field_path
                )
            _validate_step_cycle_shape(step, case_id, yaml_path, field_path)
            _validate_expect(
                step["expect"], case_id, yaml_path, field_path + ".expect", runners
            )
            if "raises" in step["expect"]:
                cycle_count = _effective_cycle_count(
                    step, case_id, yaml_path, field_path
                )
                if cycle_count != 1:
                    raise _case_error(
                        case_id,
                        yaml_path,
                        "%s.expect.raises requires effective cycle_count == 1"
                        % field_path,
                    )
    validate_shared_fixture_contract(data, yaml_path)


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
    case_id = os.path.splitext(os.path.basename(yaml_path))[0]
    fcstm_path = os.path.join(os.path.dirname(yaml_path), case_id + ".fcstm")
    if not os.path.isfile(fcstm_path):
        raise _case_error(
            case_id, yaml_path, "paired FCSTM source does not exist: %s" % fcstm_path
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

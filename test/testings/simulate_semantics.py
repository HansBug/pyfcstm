"""Shared helpers for simulate semantic fixture tests."""

import importlib.util
import logging
import os
import re
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
    SimulationRuntime,
    SimulationRuntimeDfsError,
    SimulationRuntimeEventError,
    SimulationRuntimeExpressionError,
)
from pyfcstm.template import extract_template


FIXTURE_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, "fixtures", "simulate_semantics")
)
CASE_DIR = os.path.join(FIXTURE_ROOT, "cases")
_REPO_ROOT = os.path.abspath(
    os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
)
_SOURCE_PYTHON_TEMPLATE_DIR = os.path.join(_REPO_ROOT, "templates", "python")

_ALLOWED_TOP_LEVEL_FIELDS = {
    "schema_version",
    "id",
    "title",
    "source",
    "origin",
    "categories",
    "runners",
    "initial",
    "steps",
    "commands",
    "handlers",
    "xfail_current",
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
    "raises",
    "logs",
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
_EXCEPTION_TYPES = {
    "SimulationRuntimeDfsError": SimulationRuntimeDfsError,
    "SimulationRuntimeEventError": SimulationRuntimeEventError,
    "SimulationRuntimeExpressionError": SimulationRuntimeExpressionError,
    "ValueError": ValueError,
}
_ANSI_RE = re.compile(r"\x1b\[[0-9;]*m")


class SemanticCaseError(ValueError):
    """Raised when a semantic fixture is malformed."""


@dataclass(frozen=True)
class SemanticCase:
    """Loaded simulate semantic fixture."""

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


def _assert_runtime_expectation(
    runtime: Any, expect: Mapping[str, Any], case: SemanticCase, field_path: str
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
        text = str(exc)
        match_text = str(raises["match"])
        match_kind = raises.get("match_kind", "substring")
        if match_kind == "substring":
            matched = match_text in text
        elif match_kind == "regex":
            matched = re.search(match_text, text) is not None
        else:
            raise _case_error(
                case.id,
                case.yaml_path,
                "%s.raises has invalid match_kind %r" % (field_path, match_kind),
            )
        assert matched, "%s %s exception message %r did not match %r" % (
            case.id,
            field_path,
            text,
            match_text,
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


def _step_events(
    cycle_data: Any, case: SemanticCase, field_path: str
) -> Optional[List[Any]]:
    if cycle_data in (None, {}):
        return None
    if not isinstance(cycle_data, dict):
        raise _case_error(
            case.id,
            case.yaml_path,
            "%s.cycle must be a mapping, null, or omitted" % field_path,
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
    return list(events)


def _run_step(
    runtime: Any,
    step: Mapping[str, Any],
    case: SemanticCase,
    index: int,
    caplog: Any = None,
) -> None:
    field_path = "steps[%d]" % index
    if "expect_initial" in step:
        expect = step["expect_initial"]
        _assert_runtime_expectation(
            runtime, expect, case, field_path + ".expect_initial"
        )
        return

    expect = step.get("expect") or {}
    events = _step_events(step.get("cycle", {}), case, field_path)
    with _capture_logs_if_needed(expect, caplog):
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
                assert result == expect["return"], "%s %s return mismatch: %r != %r" % (
                    case.id,
                    field_path,
                    result,
                    expect["return"],
                )
    _assert_runtime_expectation(runtime, expect, case, field_path + ".expect")
    _assert_logs(expect, caplog, case, field_path + ".expect")


def _strip_ansi(text: str) -> str:
    return _ANSI_RE.sub("", text)


def _parse_dsl(dsl_code: str):
    ast_node = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast_node)


def build_state_machine_from_case(case: SemanticCase):
    """Build a state machine model for a semantic fixture."""
    return _parse_dsl(case.dsl_code)


def _initial_kwargs(case: SemanticCase) -> Dict[str, Any]:
    initial = case.data.get("initial") or {}
    kwargs = {}
    if initial.get("state") is not None:
        kwargs["initial_state"] = initial["state"]
    if initial.get("vars") is not None:
        kwargs["initial_vars"] = dict(initial["vars"])
    return kwargs


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
            raise sim_exc
        assert sim_result == gen_result, (
            "cycle(events=%r) return mismatch for DSL:\n%s\nsimulation=%r, generated=%r"
            % (events, self._dsl_code, sim_result, gen_result)
        )
        self._assert_aligned("after cycle(events=%r)" % (events,))
        return sim_result


def _build_generated_runtime(case: SemanticCase) -> Any:
    model = build_state_machine_from_case(case)
    if os.path.isdir(_SOURCE_PYTHON_TEMPLATE_DIR):
        with TemporaryDirectory() as output_td:
            StateMachineCodeRenderer(_SOURCE_PYTHON_TEMPLATE_DIR).render(
                model=model, output_dir=output_td
            )
            module_file = os.path.join(output_td, "machine.py")
            module_name = "generated_python_runtime_%s" % re.sub(r"\W+", "_", case.id)
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            machine_cls = getattr(module, "%sMachine" % model.root_state.name)
            return machine_cls(**_initial_kwargs(case))
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
            return machine_cls(**_initial_kwargs(case))


def _build_simulation_runtime(case: SemanticCase) -> SimulationRuntime:
    return SimulationRuntime(
        build_state_machine_from_case(case), **_initial_kwargs(case)
    )


def run_simulation_case(case: SemanticCase, caplog: Any = None) -> None:
    """Run a semantic fixture against :class:`SimulationRuntime`."""
    runtime = _build_simulation_runtime(case)
    for index, step in enumerate(case.data.get("steps") or []):
        _run_step(runtime, step, case, index, caplog=caplog)


def run_generated_python_alignment_case(case: SemanticCase, caplog: Any = None) -> None:
    """Run a semantic fixture against simulation and generated Python runtimes."""
    simulation_runtime = _build_simulation_runtime(case)
    generated_runtime = _build_generated_runtime(case)
    runtime = _GeneratedPythonAlignmentRuntime(
        simulation_runtime, generated_runtime, case.dsl_code
    )
    runtime._assert_aligned("initial build")
    for index, step in enumerate(case.data.get("steps") or []):
        _run_step(runtime, step, case, index, caplog=caplog)


def run_cli_command_case(case: SemanticCase) -> None:
    """Run a semantic fixture against the simulate CLI command processor."""
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
    raises = expect["raises"]
    if not isinstance(raises, dict):
        raise _case_error(
            case_id, yaml_path, "%s.raises must be a mapping" % field_path
        )
    exc_type = raises.get("type")
    if exc_type not in _EXCEPTION_TYPES:
        raise _case_error(
            case_id, yaml_path, "%s.raises.type is unknown: %r" % (field_path, exc_type)
        )
    if raises.get("match_kind", "substring") not in {"substring", "regex"}:
        raise _case_error(
            case_id, yaml_path, "%s.raises.match_kind is invalid" % field_path
        )


def _validate_logs(
    expect: Mapping[str, Any], case_id: str, yaml_path: str, field_path: str
) -> None:
    logs = expect.get("logs")
    if not logs:
        return
    if not isinstance(logs, dict):
        raise _case_error(case_id, yaml_path, "%s.logs must be a mapping" % field_path)
    for group_name in ("contains", "not_contains"):
        for index, item in enumerate(logs.get(group_name, []) or []):
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
    if "generated_python_alignment" in runners and "cycle_count" in expect:
        raise _case_error(
            case_id,
            yaml_path,
            "%s.cycle_count is not allowed for generated alignment" % field_path,
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
    _validate_logs(expect, case_id, yaml_path, field_path)


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


def _validate_initial(initial: Any, case_id: str, yaml_path: str) -> None:
    if initial is None:
        return
    if not isinstance(initial, dict):
        raise _case_error(case_id, yaml_path, "initial must be a mapping")
    unknown_initial = set(initial.keys()) - {"state", "vars"}
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


def _validate_case_data(data: Mapping[str, Any], yaml_path: str) -> None:
    case_id = str(data.get("id", "<unknown>"))
    unknown = set(data.keys()) - _ALLOWED_TOP_LEVEL_FIELDS
    if unknown:
        raise _case_error(
            case_id, yaml_path, "unknown top-level fields: %r" % sorted(unknown)
        )
    if data.get("schema_version") != 1:
        raise _case_error(case_id, yaml_path, "schema_version must be 1")
    if not data.get("id"):
        raise _case_error(case_id, yaml_path, "id is required")
    if not data.get("title") or not isinstance(data.get("title"), str):
        raise _case_error(case_id, yaml_path, "title is required")
    if os.path.splitext(os.path.basename(yaml_path))[0] != case_id:
        raise _case_error(case_id, yaml_path, "id must match YAML file name")
    _validate_source(data.get("source"), case_id, yaml_path)
    _validate_origin(data.get("origin"), case_id, yaml_path)
    _validate_initial(data.get("initial"), case_id, yaml_path)
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
    has_steps = "steps" in data
    has_commands = "commands" in data
    if has_steps == has_commands:
        raise _case_error(
            case_id, yaml_path, "exactly one of steps or commands is required"
        )
    if "cli_command" in runners and not has_commands:
        raise _case_error(case_id, yaml_path, "cli_command cases require commands")
    if "cli_command" not in runners and not has_steps:
        raise _case_error(case_id, yaml_path, "runtime cases require steps")
    if data.get("handlers"):
        raise _case_error(case_id, yaml_path, "handlers is reserved in PR-0 fixtures")
    if data.get("xfail_current"):
        raise _case_error(
            case_id, yaml_path, "xfail_current is reserved in PR-0 active fixtures"
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
                cycle_data = step.get("cycle")
                if cycle_data not in (None, {}) and not isinstance(cycle_data, dict):
                    raise _case_error(
                        case_id,
                        yaml_path,
                        "%s.cycle must be a mapping or null" % field_path,
                    )
                if isinstance(cycle_data, dict) and "events" in cycle_data:
                    events = cycle_data["events"]
                    if events is not None and not isinstance(events, list):
                        raise _case_error(
                            case_id,
                            yaml_path,
                            "%s.cycle.events must be a list or null" % field_path,
                        )
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
    """Load a semantic fixture by case id or YAML path."""
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
    """Iterate semantic fixtures, optionally filtered by categories or runners."""
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

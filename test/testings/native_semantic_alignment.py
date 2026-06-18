"""
Native generated-runtime alignment helpers for semantic fixtures.

This module adapts the schema v2 shared semantic fixture corpus to the built-in
C and C poll templates. It owns the test-side runner names, capability-matrix
validation, native public-observation adapter, and subprocess report helpers
used by the C-family template alignment tests.

The module contains:

* :class:`NativeCapabilityEntry` - One known native alignment capability row.
* :class:`NativeAlignmentResult` - Serializable outcome of one native case run.
* :class:`NativeAlignmentReport` - Aggregate report for one native runner.
* :func:`load_native_capability_matrix` - Load and validate the matrix YAML.
* :func:`run_native_alignment_case` - Execute one case in-process.
* :func:`run_native_alignment_case_subprocess` - Execute one case safely in a
  child process so native crashes do not terminate pytest.

Example::

    >>> from test.testings.simulate_semantics import load_semantic_case
    >>> case = load_semantic_case("design_basic_simple_transition")
    >>> result = run_native_alignment_case("generated_c_alignment", case)
    >>> result.case_id
    'design_basic_simple_transition'
"""

import argparse
import json
import os
import signal
import subprocess
import sys
from dataclasses import asdict, dataclass
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Tuple

import yaml

from pyfcstm.simulate import (
    SimulationRuntimeActionReferenceError,
    SimulationRuntimeDfsError,
    SimulationRuntimeEventError,
    SimulationRuntimeExpressionError,
    SimulationRuntimeTerminalStateError,
)
from test.testings import simulate_semantics
from test.testings.simulate_semantics import (
    SemanticCase,
    iter_semantic_cases,
    load_semantic_case,
)

GENERATED_C_ALIGNMENT = "generated_c_alignment"
GENERATED_C_POLL_ALIGNMENT = "generated_c_poll_alignment"
NATIVE_ALIGNMENT_RUNNERS = (GENERATED_C_ALIGNMENT, GENERATED_C_POLL_ALIGNMENT)
CAPABILITY_MATRIX_PATH = os.path.abspath(
    os.path.join(
        os.path.dirname(__file__),
        os.pardir,
        "fixtures",
        "simulate_semantics",
        "runner_capabilities.yaml",
    )
)
_REQUIRED_CAPABILITY_FIELDS = {
    "runner",
    "case",
    "classification",
    "observation",
    "support",
    "skip_reason",
    "tracking",
    "since",
}
_ALLOWED_CLASSIFICATIONS = {
    "event_resolution",
    "exception_type_mismatch",
    "handler_mismatch",
    "native_crash",
    "native_timeout",
    "parse_render_load",
    "sigfpe",
    "state_or_ended_mismatch",
    "vars_mismatch",
}
# Worker failures are intentionally not allowed in the capability matrix:
# harness/worker bugs must surface as unexpected or mismatched results.
_WORKER_FAILURE_CLASSIFICATION = "worker_failure"
# Windows reports native arithmetic traps as positive NTSTATUS values instead
# of POSIX-style negative signals; these codes are equivalent to SIGFPE for
# alignment classification, while non-arithmetic NTSTATUS values remain native
# crashes.
_WINDOWS_ARITHMETIC_EXCEPTION_NAMES = {
    0xC000008D: "STATUS_FLOAT_DENORMAL_OPERAND",
    0xC000008E: "STATUS_FLOAT_DIVIDE_BY_ZERO",
    0xC000008F: "STATUS_FLOAT_INEXACT_RESULT",
    0xC0000090: "STATUS_FLOAT_INVALID_OPERATION",
    0xC0000091: "STATUS_FLOAT_OVERFLOW",
    0xC0000092: "STATUS_FLOAT_STACK_CHECK",
    0xC0000093: "STATUS_FLOAT_UNDERFLOW",
    0xC0000094: "STATUS_INTEGER_DIVIDE_BY_ZERO",
    0xC0000095: "STATUS_INTEGER_OVERFLOW",
}
_WINDOWS_NATIVE_EXCEPTION_NAMES = {
    0xC0000005: "STATUS_ACCESS_VIOLATION",
    0xC000001D: "STATUS_ILLEGAL_INSTRUCTION",
    0xC000008C: "STATUS_ARRAY_BOUNDS_EXCEEDED",
    0xC0000096: "STATUS_PRIVILEGED_INSTRUCTION",
    **_WINDOWS_ARITHMETIC_EXCEPTION_NAMES,
}
_PARSE_RENDER_LOAD_EXCEPTIONS = (OSError, subprocess.CalledProcessError, AttributeError)
_NATIVE_RUNTIME_EXCEPTIONS = (
    RuntimeError,
    ValueError,
    TypeError,
    KeyError,
    AssertionError,
)
_SIMULATION_RUNTIME_EXCEPTIONS = (
    SimulationRuntimeActionReferenceError,
    SimulationRuntimeDfsError,
    SimulationRuntimeEventError,
    SimulationRuntimeExpressionError,
    SimulationRuntimeTerminalStateError,
    RuntimeError,
    ValueError,
    ArithmeticError,
    TypeError,
    KeyError,
)


class NativeAlignmentMatrixError(ValueError):
    """
    Raised when the native alignment capability matrix is malformed.

    :param args: Positional message arguments accepted by :class:`ValueError`.
    :type args: object

    Example::

        >>> err = NativeAlignmentMatrixError("bad native matrix")
        >>> "matrix" in str(err)
        True
    """


@dataclass(frozen=True)
class NativeCapabilityEntry:
    """
    Known native alignment capability or expected-failure entry.

    :param runner: Native alignment runner name.
    :type runner: str
    :param case: Shared semantic fixture case id.
    :type case: str
    :param classification: Stable failure classification for the case.
    :type classification: str
    :param observation: Public observation family affected by the entry.
    :type observation: str
    :param support: Support status, currently ``"expected_failure"`` for
        native semantic alignment staging entries.
    :type support: str
    :param skip_reason: Human-readable reason for not treating the case as a
        passing gate yet.
    :type skip_reason: str
    :param tracking: URL that tracks the native alignment gap.
    :type tracking: str
    :param since: Stable date, version, or commit for when the entry became
        applicable. This is deliberately not named after a PR or roadmap item.
    :type since: str

    Example::

        >>> entry = NativeCapabilityEntry(
        ...     runner="generated_c_alignment",
        ...     case="demo",
        ...     classification="state_or_ended_mismatch",
        ...     observation="state_or_ended",
        ...     support="expected_failure",
        ...     skip_reason="known gap",
        ...     tracking="https://github.com/HansBug/pyfcstm/",
        ...     since="2026-06-17",
        ... )
        >>> entry.runner
        'generated_c_alignment'
    """

    runner: str
    case: str
    classification: str
    observation: str
    support: str
    skip_reason: str
    tracking: str
    since: str


@dataclass(frozen=True)
class NativeAlignmentResult:
    """
    Serializable result for one native semantic alignment case.

    :param runner: Native alignment runner name.
    :type runner: str
    :param case_id: Shared semantic fixture case id.
    :type case_id: str
    :param status: Outcome status, such as ``"passed"`` or ``"failed"``.
    :type status: str
    :param classification: Optional failure classification.
    :type classification: str, optional
    :param expected_classification: Optional known-failure classification from
        the capability matrix.
    :type expected_classification: str, optional
    :param support: Optional capability support state for the case.
    :type support: str, optional
    :param tracking: Optional URL that tracks the known native gap.
    :type tracking: str, optional
    :param message: Short diagnostic message.
    :type message: str
    :param returncode: Subprocess return code when a child process was used.
    :type returncode: int, optional

    Example::

        >>> result = NativeAlignmentResult("generated_c_alignment", "demo", "passed", None, "ok")
        >>> result.status
        'passed'
    """

    runner: str
    case_id: str
    status: str
    classification: Optional[str]
    message: str
    returncode: Optional[int] = None
    expected_classification: Optional[str] = None
    support: Optional[str] = None
    tracking: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the result to a JSON-serializable dictionary.

        :return: Result fields as a dictionary.
        :rtype: dict

        Example::

            >>> NativeAlignmentResult("r", "c", "passed", None, "ok").to_dict()["status"]
            'passed'
        """
        return asdict(self)


@dataclass(frozen=True)
class NativeAlignmentReport:
    """
    Aggregate native alignment report for one runner.

    :param runner: Native alignment runner name.
    :type runner: str
    :param results: Individual case results.
    :type results: typing.Sequence[NativeAlignmentResult]

    Example::

        >>> report = NativeAlignmentReport("generated_c_alignment", [])
        >>> report.summary()["total"]
        0
    """

    runner: str
    results: Sequence[NativeAlignmentResult]

    def summary(self) -> Dict[str, int]:
        """
        Count results by status.

        :return: Summary dictionary with total and per-status counts.
        :rtype: dict

        Example::

            >>> report = NativeAlignmentReport("r", [NativeAlignmentResult("r", "c", "passed", None, "ok")])
            >>> report.summary()["passed"]
            1
        """
        counts = {"total": len(self.results)}
        for result in self.results:
            counts[result.status] = counts.get(result.status, 0) + 1
        return counts

    def to_dict(self) -> Dict[str, Any]:
        """
        Convert the report to a JSON-serializable dictionary.

        :return: Report fields and summary as a dictionary.
        :rtype: dict

        Example::

            >>> NativeAlignmentReport("r", []).to_dict()["runner"]
            'r'
        """
        return {
            "runner": self.runner,
            "summary": self.summary(),
            "results": [result.to_dict() for result in self.results],
        }


def _matrix_error(message: str) -> NativeAlignmentMatrixError:
    return NativeAlignmentMatrixError("native capability matrix: %s" % message)


def _validate_runner_name(runner: str) -> None:
    if runner not in NATIVE_ALIGNMENT_RUNNERS:
        raise ValueError("unknown native alignment runner: %r" % runner)


def load_native_capability_matrix(
    path: str = CAPABILITY_MATRIX_PATH,
) -> Tuple[NativeCapabilityEntry, ...]:
    """
    Load and validate the native runner capability matrix.

    :param path: Path to the capability YAML file, defaults to the shared
        fixture matrix path.
    :type path: str, optional
    :return: Validated capability entries.
    :rtype: tuple[test.testings.native_semantic_alignment.NativeCapabilityEntry, ...]
    :raises NativeAlignmentMatrixError: If the YAML schema is invalid.

    Example::

        >>> entries = load_native_capability_matrix()
        >>> bool(entries)
        False
    """
    with open(path, "r", encoding="utf-8") as file:
        data = yaml.safe_load(file)
    if not isinstance(data, dict):
        raise _matrix_error("root must be a mapping")
    if data.get("version") != 1:
        raise _matrix_error("version must be 1")
    raw_entries = data.get("known_failures")
    if not isinstance(raw_entries, list):
        raise _matrix_error("known_failures must be a list")

    case_ids = {case.id for case in iter_semantic_cases()}
    seen = set()
    entries = []
    for index, item in enumerate(raw_entries):
        if not isinstance(item, dict):
            raise _matrix_error("known_failures[%d] must be a mapping" % index)
        missing = _REQUIRED_CAPABILITY_FIELDS - set(item.keys())
        if missing:
            raise _matrix_error(
                "known_failures[%d] missing fields: %r" % (index, sorted(missing))
            )
        unknown = set(item.keys()) - _REQUIRED_CAPABILITY_FIELDS
        if unknown:
            raise _matrix_error(
                "known_failures[%d] has unknown fields: %r" % (index, sorted(unknown))
            )
        entry = NativeCapabilityEntry(**item)
        _validate_runner_name(entry.runner)
        if entry.case not in case_ids:
            raise _matrix_error(
                "known_failures[%d] references unknown case %r" % (index, entry.case)
            )
        if entry.classification not in _ALLOWED_CLASSIFICATIONS:
            raise _matrix_error(
                "known_failures[%d] has unknown classification %r"
                % (index, entry.classification)
            )
        if entry.support != "expected_failure":
            raise _matrix_error(
                "known_failures[%d].support must be 'expected_failure'" % index
            )
        if not entry.skip_reason:
            raise _matrix_error("known_failures[%d].skip_reason is required" % index)
        if not entry.tracking.startswith("https://github.com/HansBug/pyfcstm/"):
            raise _matrix_error(
                "known_failures[%d].tracking must be a pyfcstm URL" % index
            )
        if not entry.since:
            raise _matrix_error("known_failures[%d].since is required" % index)
        key = (entry.runner, entry.case)
        if key in seen:
            raise _matrix_error("duplicate entry for runner/case: %r" % (key,))
        seen.add(key)
        entries.append(entry)
    return tuple(entries)


def native_capability_by_runner_case(
    entries: Optional[Iterable[NativeCapabilityEntry]] = None,
) -> Dict[Tuple[str, str], NativeCapabilityEntry]:
    """
    Index capability entries by ``(runner, case_id)``.

    :param entries: Optional entries to index, defaults to loading the matrix.
    :type entries: typing.Iterable[NativeCapabilityEntry], optional
    :return: Mapping from runner/case pairs to entries.
    :rtype: dict

    Example::

        >>> matrix = native_capability_by_runner_case()
        >>> ("generated_c_alignment", "expression_failure_raises_expression_error") in matrix
        True
    """
    source = tuple(entries) if entries is not None else load_native_capability_matrix()
    return {(entry.runner, entry.case): entry for entry in source}


def _native_utils_for_runner(runner: str):
    _validate_runner_name(runner)
    if runner == GENERATED_C_ALIGNMENT:
        from test.template.c import _utils as native_utils
    else:
        from test.template.c_poll import _utils as native_utils
    return native_utils


class _StateProxy:
    def __init__(self, path: Optional[Tuple[str, ...]]):
        self.path = path


def _normalize_events_for_native(events: Any) -> Any:
    if isinstance(events, str):
        return [events]
    return events


def _native_handler_call_record(runtime: Any, ctx: Any) -> Dict[str, Any]:
    return {
        "action": ctx.action_name,
        "state": ctx.get_full_state_path(),
        "stage": ctx.action_stage,
        "vars": {name: ctx.get_var(name) for name in runtime._var_names},
        "active_leaf": ctx.active_leaf,
        "call_stage": ctx.call_stage,
        "abstract_target": ctx.abstract_target,
        "named_ref": ctx.named_ref,
    }


def _install_native_fixture_handlers(
    runtime: Any, case: SemanticCase
) -> List[Mapping[str, Any]]:
    calls = []
    if not case.data.get("handlers"):
        return calls
    hook_map = runtime.get_abstract_hook_map()
    callback_map = {}
    for handler_data in case.data.get("handlers") or []:
        hook_name = hook_map[handler_data["action"]]

        def fixture_handler(
            ctx, machine=runtime, item=handler_data, handler_calls=calls
        ):
            if item["behavior"] == "record_call":
                handler_calls.append(_native_handler_call_record(machine, ctx))
            else:
                raise ValueError("handlers behavior is invalid: %r" % item["behavior"])

        callback_map[hook_name] = fixture_handler
    runtime.install_hooks(callback_map)
    return calls


class _GeneratedNativeAlignmentRuntime:
    def __init__(self, simulation_runtime: Any, native_runtime: Any, dsl_code: str):
        self._simulation_runtime = simulation_runtime
        self._native_runtime = native_runtime
        self._dsl_code = dsl_code

    @property
    def vars(self) -> Mapping[str, Any]:
        return self._native_runtime.vars

    @property
    def is_ended(self) -> bool:
        return self._native_runtime.is_ended

    @property
    def current_state(self) -> Optional[_StateProxy]:
        path = self._native_runtime.current_state_path
        if path is None:
            return None
        return _StateProxy(path)

    def _assert_aligned(self, when: str) -> None:
        sim_ended = self._simulation_runtime.is_ended
        native_ended = self._native_runtime.is_ended
        assert sim_ended == native_ended, (
            "%s: is_ended mismatch for DSL:\n%s\nsimulation=%r, native=%r"
            % (when, self._dsl_code, sim_ended, native_ended)
        )
        sim_vars = dict(self._simulation_runtime.vars)
        native_vars = dict(self._native_runtime.vars)
        comparable_keys = {
            name
            for name, sim_value in sim_vars.items()
            if not (
                isinstance(sim_value, int)
                and not isinstance(sim_value, bool)
                and abs(sim_value) > 9223372036854775807
            )
        }
        comparable_sim_vars = {name: sim_vars[name] for name in comparable_keys}
        comparable_native_vars = {name: native_vars[name] for name in comparable_keys}
        assert comparable_sim_vars == comparable_native_vars, (
            "%s: vars mismatch for DSL:\n%s\nsimulation=%r\nnative=%r"
            % (when, self._dsl_code, comparable_sim_vars, comparable_native_vars)
        )
        if sim_ended:
            assert self._native_runtime.current_state_path is None, (
                "%s: native current_state_path should be None after end for DSL:\n%s\npath=%r"
                % (when, self._dsl_code, self._native_runtime.current_state_path)
            )
        else:
            sim_path = self._simulation_runtime.current_state.path
            native_path = self._native_runtime.current_state_path
            assert sim_path == native_path, (
                "%s: current state mismatch for DSL:\n%s\nsimulation=%r\nnative=%r"
                % (when, self._dsl_code, sim_path, native_path)
            )

    def cycle(self, events: Any = None) -> Any:
        sim_exc = None
        native_exc = None
        native_events = _normalize_events_for_native(events)
        try:
            sim_result = self._simulation_runtime.cycle(events)
        except _SIMULATION_RUNTIME_EXCEPTIONS as err:
            # SimulationRuntime semantic exceptions are compared by class name;
            # unexpected exception classes still propagate and expose harness
            # bugs instead of being converted into alignment mismatches.
            sim_exc = err
        try:
            self._native_runtime.cycle(native_events)
        except _NATIVE_RUNTIME_EXCEPTIONS as err:
            # Native adapters expose generated diagnostics as Python exceptions.
            native_exc = err
        if sim_exc is not None or native_exc is not None:
            assert sim_exc is not None and native_exc is not None, (
                "cycle(events=%r) exception mismatch for DSL:\n%s\nsimulation=%r, native=%r"
                % (events, self._dsl_code, sim_exc, native_exc)
            )
            assert type(sim_exc).__name__ == type(native_exc).__name__, (
                "cycle(events=%r) exception type mismatch for DSL:\n%s\nsimulation=%s: %s\nnative=%s: %s"
                % (
                    events,
                    self._dsl_code,
                    type(sim_exc).__name__,
                    sim_exc,
                    type(native_exc).__name__,
                    native_exc,
                )
            )
            assert str(sim_exc) == str(native_exc), (
                "cycle(events=%r) exception message mismatch for DSL:\n%s\nsimulation=%s: %s\nnative=%s: %s"
                % (
                    events,
                    self._dsl_code,
                    type(sim_exc).__name__,
                    sim_exc,
                    type(native_exc).__name__,
                    native_exc,
                )
            )
            sim_cause = sim_exc.__cause__
            native_cause = native_exc.__cause__
            assert (sim_cause is None) == (native_cause is None), (
                "cycle(events=%r) exception cause presence mismatch for DSL:\n%s\nsimulation=%r, native=%r"
                % (events, self._dsl_code, sim_cause, native_cause)
            )
            if sim_cause is not None and native_cause is not None:
                assert type(sim_cause).__name__ == type(native_cause).__name__, (
                    "cycle(events=%r) exception cause type mismatch for DSL:\n%s\nsimulation=%s: %s\nnative=%s: %s"
                    % (
                        events,
                        self._dsl_code,
                        type(sim_cause).__name__,
                        sim_cause,
                        type(native_cause).__name__,
                        native_cause,
                    )
                )
                assert str(sim_cause) == str(native_cause), (
                    "cycle(events=%r) exception cause message mismatch for DSL:\n%s\nsimulation=%s: %s\nnative=%s: %s"
                    % (
                        events,
                        self._dsl_code,
                        type(sim_cause).__name__,
                        sim_cause,
                        type(native_cause).__name__,
                        native_cause,
                    )
                )
            raise sim_exc
        self._assert_aligned("after cycle(events=%r)" % (events,))
        return sim_result


def _build_native_runtime(runner: str, case: SemanticCase) -> Any:
    native_utils = _native_utils_for_runner(runner)
    return native_utils.build_c_runtime(
        case.dsl_code, **simulate_semantics._initial_kwargs(case)
    )


def _capture_native_construction(runner: str, case: SemanticCase):
    try:
        return _build_native_runtime(runner, case), None
    except _PARSE_RENDER_LOAD_EXCEPTIONS as err:
        # OSError covers shared-library load failures; CalledProcessError covers
        # cmake/build failures; AttributeError covers missing exported symbols.
        return None, err
    except _NATIVE_RUNTIME_EXCEPTIONS as err:
        # RuntimeError/ValueError/TypeError/KeyError/AssertionError cover native
        # wrapper construction and hot-start diagnostics. Unexpected exceptions
        # propagate to expose harness bugs.
        return None, err


def _classify_exception(error: BaseException) -> str:
    message = "%s: %s" % (type(error).__name__, error)
    lowered = message.lower()
    if isinstance(error, _PARSE_RENDER_LOAD_EXCEPTIONS):
        return "parse_render_load"
    if (
        "cmake" in lowered
        or "shared library" in lowered
        or "shared-library" in lowered
        or "exported symbol" in lowered
        or "integer string conversion" in lowered
        or "4300 digits" in lowered
    ):
        return "parse_render_load"
    if "handler call" in lowered or "handler_calls" in lowered:
        return "handler_mismatch"
    if "var" in lowered:
        return "vars_mismatch"
    if "exception" in lowered or "raises" in lowered or "dfs" in lowered:
        return "exception_type_mismatch"
    if (
        "unknown event path" in lowered
        or "cannot resolve event path" in lowered
        or "event resolution" in lowered
    ):
        return "event_resolution"
    if "state" in lowered or "ended" in lowered:
        return "state_or_ended_mismatch"
    return "state_or_ended_mismatch"


def _apply_capability_entry(result: NativeAlignmentResult) -> NativeAlignmentResult:
    if result.status not in {"passed", "failed"}:
        return result

    entry = native_capability_by_runner_case().get((result.runner, result.case_id))
    if entry is None:
        if result.status == "failed":
            return NativeAlignmentResult(
                result.runner,
                result.case_id,
                "unexpected_failure",
                result.classification,
                result.message,
                result.returncode,
            )
        return result

    if result.status == "passed":
        return NativeAlignmentResult(
            result.runner,
            result.case_id,
            "unexpected_pass",
            result.classification,
            "known native alignment gap passed; update the capability matrix",
            result.returncode,
            expected_classification=entry.classification,
            support=entry.support,
            tracking=entry.tracking,
        )

    if result.classification == entry.classification:
        return NativeAlignmentResult(
            result.runner,
            result.case_id,
            "expected_failure",
            result.classification,
            result.message,
            result.returncode,
            expected_classification=entry.classification,
            support=entry.support,
            tracking=entry.tracking,
        )

    return NativeAlignmentResult(
        result.runner,
        result.case_id,
        "classification_mismatch",
        result.classification,
        (
            "%s; expected known-failure classification %s"
            % (result.message, entry.classification)
        ),
        result.returncode,
        expected_classification=entry.classification,
        support=entry.support,
        tracking=entry.tracking,
    )


def _raw_native_alignment_case(
    runner: str, case: SemanticCase
) -> NativeAlignmentResult:
    _validate_runner_name(runner)
    simulation_runtime, simulation_err = simulate_semantics._capture_construction(
        lambda: simulate_semantics._build_simulation_runtime(case)
    )
    native_runtime, native_err = _capture_native_construction(runner, case)
    initial_expect = simulate_semantics._initial_constructor_expect(case)
    try:
        simulate_semantics._assert_aligned_constructor_outcome(
            case,
            initial_expect,
            simulation_runtime,
            simulation_err,
            native_runtime,
            native_err,
        )
        if initial_expect is not None:
            return NativeAlignmentResult(runner, case.id, "passed", None, "passed")
        simulation_handler_calls = simulate_semantics._register_fixture_handlers(
            simulation_runtime, case
        )
        native_handler_calls = _install_native_fixture_handlers(native_runtime, case)
        runtime = _GeneratedNativeAlignmentRuntime(
            simulation_runtime, native_runtime, case.dsl_code
        )
        runtime._assert_aligned("initial build")
        for index, step in enumerate(case.data.get("steps") or []):
            simulate_semantics._run_step(
                runtime,
                step,
                case,
                index,
                handler_calls=simulation_handler_calls,
            )
            simulation_calls = simulate_semantics._normalize_handler_call_records(
                simulation_handler_calls
            )
            native_calls = simulate_semantics._normalize_handler_call_records(
                native_handler_calls
            )
            assert simulation_calls == native_calls, (
                "%s steps[%d] handler call mismatch: simulation=%r, native=%r"
                % (case.id, index, simulation_calls, native_calls)
            )
    except AssertionError as err:
        return NativeAlignmentResult(
            runner, case.id, "failed", _classify_exception(err), str(err)
        )
    except _PARSE_RENDER_LOAD_EXCEPTIONS as err:
        return NativeAlignmentResult(
            runner,
            case.id,
            "failed",
            "parse_render_load",
            "%s: %s" % (type(err).__name__, err),
        )
    except _NATIVE_RUNTIME_EXCEPTIONS as err:
        return NativeAlignmentResult(
            runner,
            case.id,
            "failed",
            _classify_exception(err),
            "%s: %s" % (type(err).__name__, err),
        )
    finally:
        if native_runtime is not None:
            native_runtime.close()
    return NativeAlignmentResult(runner, case.id, "passed", None, "passed")


def run_native_alignment_case(runner: str, case: SemanticCase) -> NativeAlignmentResult:
    """
    Execute one semantic fixture against a native generated runtime.

    :param runner: Native runner name, either ``generated_c_alignment`` or
        ``generated_c_poll_alignment``.
    :type runner: str
    :param case: Semantic fixture to execute.
    :type case: test.testings.simulate_semantics.SemanticCase
    :return: Serializable native alignment result.
    :rtype: test.testings.native_semantic_alignment.NativeAlignmentResult

    Example::

        >>> case = load_semantic_case("design_basic_simple_transition")
        >>> run_native_alignment_case("generated_c_alignment", case).status
        'passed'
    """
    return _apply_capability_entry(_raw_native_alignment_case(runner, case))


def _signal_name(returncode: int) -> str:
    signal_number = -returncode
    try:
        return signal.Signals(signal_number).name
    except ValueError:
        return "signal_%d" % signal_number


def _windows_exception_code(returncode: int) -> Optional[int]:
    unsigned_code = returncode & 0xFFFFFFFF
    if unsigned_code in _WINDOWS_NATIVE_EXCEPTION_NAMES:
        return unsigned_code
    return None


def _classify_worker_returncode(returncode: int) -> Tuple[str, str]:
    windows_code = _windows_exception_code(returncode)
    if windows_code is not None:
        name = _WINDOWS_NATIVE_EXCEPTION_NAMES[windows_code]
        if windows_code in _WINDOWS_ARITHMETIC_EXCEPTION_NAMES:
            return "sigfpe", "native alignment worker terminated by %s" % name
        return "native_crash", "native alignment worker terminated by %s" % name

    if returncode < 0:
        classification = "sigfpe" if returncode == -signal.SIGFPE else "native_crash"
        return (
            classification,
            "native alignment worker terminated by %s" % _signal_name(returncode),
        )

    return (
        _WORKER_FAILURE_CLASSIFICATION,
        "native alignment worker exited with status %s" % returncode,
    )


def _worker_failure_message(completed: subprocess.CompletedProcess) -> str:
    output = (completed.stderr or completed.stdout).strip()
    prefix = _classify_worker_returncode(completed.returncode)[1]
    if output:
        return "%s: %s" % (prefix, output)
    return prefix


def run_native_alignment_case_subprocess(
    runner: str, case_id: str, timeout: int = 240
) -> NativeAlignmentResult:
    """
    Execute one native alignment case in a child Python process.

    Subprocess execution protects pytest from native process crashes such as
    ``SIGFPE`` while preserving a JSON result for ordinary mismatches.

    :param runner: Native runner name.
    :type runner: str
    :param case_id: Semantic fixture id.
    :type case_id: str
    :param timeout: Child-process timeout in seconds, defaults to ``240``.
    :type timeout: int, optional
    :return: Serializable native alignment result.
    :rtype: test.testings.native_semantic_alignment.NativeAlignmentResult

    Example::

        >>> result = run_native_alignment_case_subprocess("generated_c_alignment", "design_basic_simple_transition")
        >>> result.case_id
        'design_basic_simple_transition'
    """
    _validate_runner_name(runner)
    cmd = [
        sys.executable,
        "-m",
        "test.testings.native_semantic_alignment",
        "--worker",
        "--runner",
        runner,
        "--case-id",
        case_id,
    ]
    try:
        completed = subprocess.run(
            cmd,
            cwd=os.path.abspath(
                os.path.join(os.path.dirname(__file__), os.pardir, os.pardir)
            ),
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
            timeout=timeout,
        )
    except subprocess.TimeoutExpired as err:
        return _apply_capability_entry(
            NativeAlignmentResult(
                runner,
                case_id,
                "failed",
                "native_timeout",
                "native alignment worker timed out after %s seconds" % err.timeout,
                None,
            )
        )
    crash_classification, crash_message = _classify_worker_returncode(
        completed.returncode
    )
    if crash_classification != _WORKER_FAILURE_CLASSIFICATION:
        return _apply_capability_entry(
            NativeAlignmentResult(
                runner,
                case_id,
                "failed",
                crash_classification,
                crash_message,
                completed.returncode,
            )
        )
    if completed.returncode != 0:
        return _apply_capability_entry(
            NativeAlignmentResult(
                runner,
                case_id,
                "failed",
                _WORKER_FAILURE_CLASSIFICATION,
                _worker_failure_message(completed),
                completed.returncode,
            )
        )
    lines = [line for line in completed.stdout.splitlines() if line.strip()]
    if not lines:
        return _apply_capability_entry(
            NativeAlignmentResult(
                runner,
                case_id,
                "failed",
                _WORKER_FAILURE_CLASSIFICATION,
                "native alignment worker produced no JSON output",
                completed.returncode,
            )
        )
    try:
        data = json.loads(lines[-1])
    except json.JSONDecodeError as err:
        # json.loads raises JSONDecodeError when the worker exits successfully
        # but does not emit the expected final JSON result line.
        return _apply_capability_entry(
            NativeAlignmentResult(
                runner,
                case_id,
                "failed",
                _WORKER_FAILURE_CLASSIFICATION,
                "native alignment worker produced invalid JSON output: %s" % err,
                completed.returncode,
            )
        )
    return _apply_capability_entry(NativeAlignmentResult(**data))


def run_native_alignment_report(
    runner: str, case_ids: Optional[Sequence[str]] = None, subprocess_mode: bool = True
) -> NativeAlignmentReport:
    """
    Run a native alignment report for selected semantic fixtures.

    :param runner: Native runner name.
    :type runner: str
    :param case_ids: Optional explicit case ids, defaults to all shared cases.
    :type case_ids: typing.Sequence[str], optional
    :param subprocess_mode: Whether to isolate each case in a subprocess,
        defaults to ``True``.
    :type subprocess_mode: bool, optional
    :return: Native alignment report.
    :rtype: test.testings.native_semantic_alignment.NativeAlignmentReport

    Example::

        >>> report = run_native_alignment_report("generated_c_alignment", ["design_basic_simple_transition"])
        >>> report.runner
        'generated_c_alignment'
    """
    _validate_runner_name(runner)
    selected_ids = list(case_ids or [case.id for case in iter_semantic_cases()])
    results = []
    for case_id in selected_ids:
        if subprocess_mode:
            results.append(run_native_alignment_case_subprocess(runner, case_id))
        else:
            results.append(
                run_native_alignment_case(runner, load_semantic_case(case_id))
            )
    return NativeAlignmentReport(runner, results)


def _parse_args(argv: Optional[Sequence[str]]) -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Run native shared semantic alignment."
    )
    parser.add_argument("--runner", choices=NATIVE_ALIGNMENT_RUNNERS, required=True)
    parser.add_argument("--case-id", action="append", dest="case_ids")
    parser.add_argument("--worker", action="store_true")
    parser.add_argument("--in-process", action="store_true")
    return parser.parse_args(argv)


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Command-line entry point for native semantic alignment reports.

    :param argv: Optional command-line arguments without the executable name.
    :type argv: typing.Sequence[str], optional
    :return: Process exit status.
    :rtype: int

    Example::

        >>> main(["--runner", "generated_c_alignment", "--case-id", "design_basic_simple_transition"])
        0
    """
    args = _parse_args(argv)
    if args.worker:
        if not args.case_ids or len(args.case_ids) != 1:
            raise SystemExit("--worker requires exactly one --case-id")
        result = _raw_native_alignment_case(
            args.runner, load_semantic_case(args.case_ids[0])
        )
        print(json.dumps(result.to_dict(), sort_keys=True))
        return 0
    report = run_native_alignment_report(
        args.runner,
        case_ids=args.case_ids,
        subprocess_mode=not args.in_process,
    )
    print(json.dumps(report.to_dict(), indent=2, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

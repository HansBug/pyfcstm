"""Decode and replay bounded model checking witnesses.

This module is the witness layer above :mod:`pyfcstm.bmc.properties`.  It
solves compiled BMC property formulas, decodes SAT models into JSON-stable
macro-step traces, and replays those traces against
:class:`pyfcstm.simulate.SimulationRuntime` as a runtime-alignment oracle.  The
trace deliberately stays at the public cycle boundary: frames, sparse replay
input events, selected BMC case metadata, delta/gamma progress flags, and
abstract-call snapshots. Each step also records ordered consumed events and
derived unconsumed inputs so replay checks the complete public cycle event
accounting contract.

The module contains:

* :class:`BmcSolveResult` - Structured solver status and optional Z3 model.
* :class:`BmcWitnessTrace` - JSON-stable decoded witness root object.
* :class:`BmcReplayResult` - Structured runtime replay result and mismatches.
* :func:`solve_bmc_property` - Solve a compiled property formula.
* :func:`decode_bmc_witness` - Decode one SAT model into a witness trace.
* :func:`replay_bmc_witness` - Replay a witness with ``SimulationRuntime``.

Example::

    >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
    >>> from pyfcstm.bmc.witness import solve_bmc_property, decode_bmc_witness
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> sm = load_state_machine_from_text('state Root;')
    >>> core = build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");'))
    >>> formula = compile_bmc_property(core)
    >>> result = solve_bmc_property(formula)
    >>> result.status
    'sat'
    >>> decode_bmc_witness(formula, result.model).schema_version
    'bmc-witness/v1'
"""

from __future__ import annotations

import io
import math
import copy
import sys
import time
from collections.abc import Iterable as IterableABC
from dataclasses import dataclass, field
from fractions import Fraction
from typing import Any, Callable, Dict, Iterable, Mapping, Optional, Sequence, Tuple

from tabulate import tabulate, tabulate_formats
import z3

from .ast import (
    Active,
    BoolLiteral,
    Called,
    CondBinaryOp,
    CondConditionalOp,
    CondUnaryOp,
    Event,
    NumericComparison,
    Terminated,
)
from .binding import BoundAssumption
from .domain import STATE_INIT_ID, STATE_TERMINATE_ID
from .errors import BmcBuildError
from .properties import BmcPropertyFormula, _lower_predicate
from .query import EventAssumption
from .relation import BmcCaseRelation
from pyfcstm.model import OnAspect, OnStage, StateMachine
from pyfcstm.simulate import ReadOnlyExecutionContext, SimulationRuntime

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

_CanonicalDict = Dict[str, Any]
#: Public solver statuses returned by :class:`BmcSolveResult`.
BmcSolveStatus = Literal["sat", "unsat", "unknown", "timeout"]
_INTERNAL_ISSUE_URL = "https://github.com/HansBug/pyfcstm/issues/new"
_REPLAY_FLOAT_TOLERANCE = 1e-9
_MISSING_REPLAY_OBSERVATION = object()
_PRETTY_STR_MAX_ROWS = 50
_MARKDOWN_TABLE_FORMATS = {"github"}
_EVENT_REASON_PRIORITY = {
    "explicit_true_assumption": 0,
    "property_support": 1,
    "case_positive": 2,
    "negative_case_read": 3,
    "explicit_false_assumption": 4,
    "model_debug": 5,
}
_EVENT_REASON_TAGS = {
    "case_positive": "case",
    "explicit_true_assumption": "assume",
    "property_support": "prop",
    "negative_case_read": "read=false",
    "explicit_false_assumption": "assume=false",
    "model_debug": "debug",
}
_REPLAY_EVENT_REASONS = {
    "case_positive",
    "explicit_true_assumption",
    "property_support",
}
_PRETTY_EXTRA_LEGEND = (
    "extra: I=initial D=delta G=gamma T=terminated N=rows truncated "
    "V=vars hidden E=events truncated C=calls truncated "
    "W=cell width truncated P=full path unavailable R=hidden event reads"
)
_PUBLIC_JSON_MAX_DEPTH = 256


def _internal_error(message: str) -> BmcBuildError:
    return BmcBuildError(
        "%s This is an internal BMC witness consistency error; please open an "
        "issue with a reproducer: %s" % (message, _INTERNAL_ISSUE_URL)
    )


def _validate_pretty_choice(name: str, value: str, choices: Sequence[str]) -> None:
    if value not in choices:
        raise BmcBuildError(
            "%s must be one of %s." % (name, ", ".join(repr(item) for item in choices))
        )


def _validate_optional_non_negative_int(name: str, value: Optional[int]) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value < 0
    ):
        raise BmcBuildError("%s must be a non-negative integer or None." % name)


def _validate_optional_positive_int(name: str, value: Optional[int]) -> None:
    if value is not None and (
        isinstance(value, bool) or not isinstance(value, int) or value <= 0
    ):
        raise BmcBuildError("%s must be a positive integer or None." % name)


def _coerce_public_sequence(
    name: str, value: object, item_type: object, item_description: str
) -> Tuple[Any, ...]:
    if isinstance(value, (str, bytes)) or isinstance(value, Mapping):
        raise BmcBuildError("%s must be a sequence of %s." % (name, item_description))
    if not isinstance(value, IterableABC):
        raise BmcBuildError("%s must be a sequence of %s." % (name, item_description))
    items = tuple(value)
    if not all(isinstance(item, item_type) for item in items):
        raise BmcBuildError("%s must contain %s." % (name, item_description))
    return items


def _is_public_finite_number(value: Any) -> bool:
    if isinstance(value, bool):
        return False
    if isinstance(value, int):
        return True
    if isinstance(value, float):
        return math.isfinite(value)
    return False


def _coerce_public_value_mapping(name: str, value: object) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BmcBuildError("%s must be a mapping." % name)
    result = {}
    for key, item in value.items():
        if not isinstance(key, str) or not key:
            raise BmcBuildError("%s keys must be non-empty strings." % name)
        if not _is_public_finite_number(item):
            raise BmcBuildError("%s.%s must be a finite int or float." % (name, key))
        result[key] = item
    return result


def _coerce_public_json_value(
    path: str, value: object, _stack: Optional[set] = None, _depth: int = 0
) -> Any:
    if _depth > _PUBLIC_JSON_MAX_DEPTH:
        raise BmcBuildError(
            "%s metadata nesting exceeds %d levels." % (path, _PUBLIC_JSON_MAX_DEPTH)
        )
    if value is None or isinstance(value, (bool, str)):
        return value
    if isinstance(value, int):
        return value
    if isinstance(value, float):
        if not math.isfinite(value):
            raise BmcBuildError("%s must be finite for JSON-stable metadata." % path)
        return value
    if _stack is None:
        _stack = set()
    if isinstance(value, Mapping):
        return _coerce_public_json_mapping(path, value, _stack, _depth)
    if isinstance(value, (list, tuple)):
        value_id = id(value)
        if value_id in _stack:
            raise BmcBuildError("%s must not contain cyclic metadata." % path)
        _stack.add(value_id)
        try:
            return [
                _coerce_public_json_value(
                    "%s[%d]" % (path, index), item, _stack, _depth + 1
                )
                for index, item in enumerate(value)
            ]
        finally:
            _stack.remove(value_id)
    raise BmcBuildError("%s must be JSON-stable metadata." % path)


def _coerce_public_json_mapping(
    name: str, value: object, _stack: Optional[set] = None, _depth: int = 0
) -> Dict[str, Any]:
    if not isinstance(value, Mapping):
        raise BmcBuildError("%s must be a mapping." % name)
    if _depth > _PUBLIC_JSON_MAX_DEPTH:
        raise BmcBuildError(
            "%s metadata nesting exceeds %d levels." % (name, _PUBLIC_JSON_MAX_DEPTH)
        )
    if _stack is None:
        _stack = set()
    value_id = id(value)
    if value_id in _stack:
        raise BmcBuildError("%s must not contain cyclic metadata." % name)
    _stack.add(value_id)
    result = {}
    try:
        items = []
        for key, item in value.items():
            if not isinstance(key, str) or not key:
                raise BmcBuildError("%s keys must be non-empty strings." % name)
            items.append((key, item))
        for key, item in sorted(items, key=lambda pair: pair[0]):
            result[key] = _coerce_public_json_value(
                "%s.%s" % (name, key), item, _stack, _depth + 1
            )
        return result
    finally:
        _stack.remove(value_id)


def _validate_optional_reason(name: str, value: Optional[str]) -> None:
    if value is not None and not isinstance(value, str):
        raise BmcBuildError("%s must be a string or None." % name)


def _validate_primary_solve_reason(
    status_name: str, status: Optional[str], reason_name: str, reason: Optional[str]
) -> None:
    _validate_optional_reason(reason_name, reason)
    if reason is not None and status not in {"unknown", "timeout"}:
        raise BmcBuildError(
            "%s must be None unless %s is unknown or timeout."
            % (reason_name, status_name)
        )


def _validate_incomplete_solve_reason(
    status_name: str, status: Optional[str], reason_name: str, reason: Optional[str]
) -> None:
    _validate_optional_reason(reason_name, reason)
    if reason is not None and status in {"sat", "unsat"}:
        raise BmcBuildError(
            "%s must be None when %s is sat or unsat." % (reason_name, status_name)
        )


def _validate_elapsed_ms(value: float) -> None:
    if not _is_public_finite_number(value) or value < 0:
        raise BmcBuildError("elapsed_ms must be a finite non-negative number.")


def _validate_witness_solver_metadata(value: Mapping[str, Any]) -> None:
    status = value.get("status")
    if status is not None and status not in {"sat", "unsat", "unknown", "timeout"}:
        raise BmcBuildError("solver.status must be sat, unsat, unknown, or timeout.")
    incomplete_status = value.get("incomplete_status")
    if incomplete_status is not None and incomplete_status not in {
        "sat",
        "unsat",
        "unknown",
        "timeout",
    }:
        raise BmcBuildError(
            "solver.incomplete_status must be sat, unsat, unknown, timeout, or None."
        )
    if "elapsed_ms" in value:
        _validate_elapsed_ms(value["elapsed_ms"])
    if "incomplete_elapsed_ms" in value:
        _validate_elapsed_ms(value["incomplete_elapsed_ms"])
    if "reason" in value:
        _validate_primary_solve_reason(
            "solver.status", status, "solver.reason", value["reason"]
        )
    if "incomplete_reason" in value:
        _validate_incomplete_solve_reason(
            "solver.incomplete_status",
            incomplete_status,
            "solver.incomplete_reason",
            value["incomplete_reason"],
        )


def _canonical_public_value_mapping(name: str, value: object) -> Dict[str, Any]:
    return dict(sorted(_coerce_public_value_mapping(name, value).items()))


def _public_mismatch_diagnostic_value(value: Any) -> Any:
    if isinstance(value, float) and not math.isfinite(value):
        return str(value)
    return value


def _format_scalar(value: Any) -> str:
    if value is None:
        return "-"
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, Mapping):
        return _format_mapping_inline(value)
    if isinstance(value, (list, tuple)):
        if not value:
            return "-"
        return ", ".join(_format_scalar(item) for item in value)
    return str(value)


def _format_mapping_inline(value: Mapping[str, Any]) -> str:
    if not value:
        return "-"
    return ", ".join(
        "%s=%s" % (key, _format_scalar(item))
        for key, item in sorted(value.items(), key=lambda pair: pair[0])
    )


def _format_path(path: str, mode: str) -> str:
    if mode == "short":
        return path.rsplit(".", 1)[-1]
    return path


def _join_cell_lines(lines: Sequence[str], tablefmt: str) -> str:
    cleaned = [line if line else "-" for line in lines]
    if not cleaned:  # pragma: no cover - public renderers do not pass empty cells here.
        return "-"
    if tablefmt in _MARKDOWN_TABLE_FORMATS:
        return "<br>".join(cleaned)
    return "\n".join(cleaned)


def _limit_text_line(line: str, max_cell_width: Optional[int]) -> Tuple[str, bool]:
    if max_cell_width is None or len(line) <= max_cell_width:
        return line, False
    if max_cell_width <= 1:
        return "…", True
    return line[: max_cell_width - 1] + "…", True


def _limited_cell(
    lines: Sequence[str],
    tablefmt: str,
    max_items: Optional[int] = None,
    max_cell_width: Optional[int] = 72,
    truncation_marker: Optional[str] = None,
) -> Tuple[str, Tuple[str, ...]]:
    markers = []
    selected = list(lines)
    if max_items is not None and len(selected) > max_items:
        hidden_count = len(selected) - max_items
        selected = selected[:max_items] + ["… (+%d more)" % hidden_count]
        if truncation_marker is not None:
            markers.append(truncation_marker)
    width_limited = []
    width_truncated = False
    for line in selected:
        limited, truncated = _limit_text_line(line, max_cell_width)
        width_limited.append(limited)
        width_truncated = width_truncated or truncated
    if width_truncated:
        markers.append("W")
    return _join_cell_lines(width_limited, tablefmt), tuple(markers)


def _state_label(frame_or_state: Any) -> str:
    if isinstance(frame_or_state, BmcWitnessFrame):
        if frame_or_state.state is not None:
            return frame_or_state.state
        if frame_or_state.sentinel is not None:
            return frame_or_state.sentinel
        return "-"
    if isinstance(frame_or_state, BmcRuntimeFrame):
        if frame_or_state.state is not None:
            return frame_or_state.state
        if frame_or_state.terminated:
            return "terminated"
        return "-"
    if frame_or_state is None:  # pragma: no cover - defensive for malformed traces.
        return "-"
    return str(frame_or_state)


def _via_text(
    source: Any,
    target: Any,
    via_mode: str,
    tablefmt: str,
    max_cell_width: Optional[int],
    terminated_absorb: bool = False,
) -> Tuple[str, Tuple[str, ...]]:
    if terminated_absorb:
        return "-", ()
    source_text = _state_label(source)
    target_text = _state_label(target)
    if source_text == "-" and target_text == "-":
        return "-", ()
    endpoint = "%s --> %s" % (source_text, target_text)
    markers = []
    if via_mode == "full":
        markers.append("P")
    cell, width_markers = _limited_cell(
        (endpoint,), tablefmt, max_cell_width=max_cell_width
    )
    markers.extend(width_markers)
    return cell, tuple(markers)


def _merge_event_reasons(
    events: Sequence["BmcWitnessEvent"],
) -> Tuple["BmcWitnessEvent", ...]:
    by_path: Dict[str, BmcWitnessEvent] = {}
    order = []
    for event in events:
        if event.path not in by_path:
            by_path[event.path] = event
            order.append(event.path)
            continue
        current = by_path[event.path]
        if (
            _EVENT_REASON_PRIORITY[event.reason]
            < _EVENT_REASON_PRIORITY[current.reason]
        ):
            by_path[event.path] = event
    return tuple(by_path[path] for path in order)


def _unconsumed_event_paths(
    input_events: Sequence[str], consumed_events: Sequence[str]
) -> Tuple[str, ...]:
    consumed = set(consumed_events)
    return tuple(path for path in input_events if path not in consumed)


def _event_display(event: "BmcWitnessEvent", event_reason: str) -> str:
    tag = _EVENT_REASON_TAGS[event.reason]
    if event_reason == "always":
        return "%s[%s]" % (event.path, tag)
    if event_reason == "never" and event.reason in _REPLAY_EVENT_REASONS:
        return event.path
    if event_reason == "never":
        return "%s[%s]" % (event.path, tag)
    if event.reason == "case_positive":
        return event.path
    return "%s[%s]" % (event.path, tag)


def _event_cell(
    input_events: Sequence["BmcWitnessEvent"],
    event_reads: Sequence["BmcWitnessEvent"],
    events_mode: str,
    event_reason: str,
    tablefmt: str,
    max_events: Optional[int],
    max_cell_width: Optional[int],
) -> Tuple[str, Tuple[str, ...]]:
    if events_mode == "none":
        return "-", ()
    if events_mode == "input":
        events = tuple(
            event for event in input_events if event.reason in _REPLAY_EVENT_REASONS
        )
    else:
        events = tuple(input_events) + tuple(event_reads)
    lines = [
        _event_display(event, event_reason) for event in _merge_event_reasons(events)
    ]
    if not lines:
        return "-", ()
    return _limited_cell(
        lines,
        tablefmt,
        max_items=max_events,
        max_cell_width=max_cell_width,
        truncation_marker="E",
    )


def _runtime_event_cell(
    input_events: Sequence[str],
    unconsumed_events: Sequence[str],
    events_mode: str,
    tablefmt: str,
    max_events: Optional[int],
    max_cell_width: Optional[int],
) -> Tuple[str, Tuple[str, ...]]:
    if events_mode == "none" or not input_events:
        return "-", ()
    unconsumed = set(unconsumed_events)
    lines = [
        "%s[unconsumed]" % event if event in unconsumed else str(event)
        for event in input_events
    ]
    return _limited_cell(
        lines,
        tablefmt,
        max_items=max_events,
        max_cell_width=max_cell_width,
        truncation_marker="E",
    )


def _call_summary_lines(
    calls: Sequence["BmcWitnessCallRecord"], call_path: str
) -> Tuple[str, ...]:
    counts: Dict[str, int] = {}
    order = []
    for call in calls:
        if call.action_name not in counts:
            counts[call.action_name] = 0
            order.append(call.action_name)
        counts[call.action_name] += 1
    return tuple(
        "%s(%d)" % (_format_path(action_name, call_path), counts[action_name])
        for action_name in order
    )


def _call_expanded_line(
    call: "BmcWitnessCallRecord", call_path: str, call_details: str
) -> str:
    fields = []
    if call_details == "full":
        fields.extend(
            [
                ("stage", call.stage),
                ("role", call.role),
                ("state", call.state),
                ("active", call.active_leaf),
            ]
        )
        if call.named_ref is not None:
            fields.append(("named_ref", call.named_ref))
    else:
        fields.append(("state", call.state))
    for key in sorted(call.snapshot):
        fields.append((key, call.snapshot[key]))
    detail = ", ".join("%s=%s" % (key, _format_scalar(value)) for key, value in fields)
    return "%s{%s}" % (_format_path(call.action_name, call_path), detail)


def _call_cell(
    calls: Sequence["BmcWitnessCallRecord"],
    calls_mode: str,
    call_path: str,
    call_details: str,
    tablefmt: str,
    max_call_groups: Optional[int],
    max_cell_width: Optional[int],
) -> Tuple[str, Tuple[str, ...]]:
    if calls_mode == "none" or not calls:
        return "-", ()
    if calls_mode == "summary":
        lines = _call_summary_lines(calls, call_path)
    else:
        lines = tuple(
            _call_expanded_line(call, call_path, call_details) for call in calls
        )
    return _limited_cell(
        lines,
        tablefmt,
        max_items=max_call_groups,
        max_cell_width=max_cell_width,
        truncation_marker="C",
    )


def _ordered_var_names(
    frames: Sequence[Any], vars_order: str, max_var_columns: Optional[int]
) -> Tuple[Tuple[str, ...], bool]:
    names = []
    seen = set()
    for frame in frames:
        for name in getattr(frame, "vars", {}):
            if name not in seen:
                names.append(name)
                seen.add(name)
    if vars_order == "alpha":
        names = sorted(names)
    hidden = max_var_columns is not None and len(names) > max_var_columns
    if hidden:
        names = names[:max_var_columns]
    return tuple(names), hidden


def _tabulate_table(
    rows: Sequence[Sequence[Any]], headers: Sequence[str], tablefmt: str
) -> str:
    return tabulate(
        rows,
        headers=headers,
        tablefmt=tablefmt,
        disable_numparse=True,
    )


def _format_extra(markers: Sequence[str]) -> str:
    ordered = []
    for marker in ("I", "D", "G", "T", "N", "V", "E", "C", "W", "P", "R"):
        if marker in markers and marker not in ordered:
            ordered.append(marker)
    return "".join(ordered) if ordered else "-"


def _trace_preamble(trace: "BmcWitnessTrace") -> str:
    kind = trace.property.get("kind", "property")
    bound = trace.property.get("bound")
    status = trace.solver.get("status", "-")
    if bound is None:
        spec = str(kind)
    else:
        spec = "%s<=%s" % (kind, bound)
    return "BmcWitnessTrace[%s, %s] frames=%d steps=%d" % (
        spec,
        status,
        len(trace.frames),
        len(trace.steps),
    )


def _runtime_trace_preamble(trace: "BmcRuntimeTrace") -> str:
    return "BmcRuntimeTrace frames=%d steps=%d" % (len(trace.frames), len(trace.steps))


def _coerce_pretty_options(
    verbose: bool,
    events_mode: str,
    event_reason: str,
    calls_mode: str,
    call_details: str,
    via_mode: str,
    show_case: bool,
    show_ids: bool,
    show_legend: bool,
) -> Tuple[str, str, str, str, str, bool, bool, bool]:
    if not isinstance(verbose, bool):
        raise BmcBuildError("verbose must be bool.")
    if not isinstance(show_case, bool):
        raise BmcBuildError("show_case must be bool.")
    if not isinstance(show_ids, bool):
        raise BmcBuildError("show_ids must be bool.")
    if not isinstance(show_legend, bool):
        raise BmcBuildError("show_legend must be bool.")
    if verbose:
        return "all", "always", "expanded", "full", "full", True, True, True
    return (
        events_mode,
        event_reason,
        calls_mode,
        call_details,
        via_mode,
        show_case,
        show_ids,
        show_legend,
    )


def _render_witness_trace(
    trace: "BmcWitnessTrace",
    *,
    tablefmt: str,
    verbose: bool,
    max_rows: Optional[int],
    max_events: Optional[int],
    max_call_groups: Optional[int],
    max_cell_width: Optional[int],
    max_var_columns: Optional[int],
    vars_order: str,
    events_mode: str,
    event_reason: str,
    calls_mode: str,
    call_path: str,
    call_details: str,
    via_mode: str,
    show_case: bool,
    show_ids: bool,
    show_legend: bool,
) -> str:
    (
        events_mode,
        event_reason,
        calls_mode,
        call_details,
        via_mode,
        show_case,
        show_ids,
        show_legend,
    ) = _coerce_pretty_options(
        verbose,
        events_mode,
        event_reason,
        calls_mode,
        call_details,
        via_mode,
        show_case,
        show_ids,
        show_legend,
    )
    _validate_trace_pretty_options(
        max_rows,
        max_events,
        max_call_groups,
        max_cell_width,
        max_var_columns,
        vars_order,
        events_mode,
        event_reason,
        calls_mode,
        call_path,
        call_details,
        via_mode,
    )
    var_names, hidden_vars = _ordered_var_names(
        trace.frames, vars_order, max_var_columns
    )
    headers = ["frame"]
    if show_ids:
        headers.extend(["step", "source_frame", "target_frame", "case_kind"])
    if show_case:
        headers.append("case")
    headers.extend(["via", "state", "progress"])
    headers.extend("[%s]" % name for name in var_names)
    headers.extend(["events", "calls", "extra"])
    rows = []
    for frame in trace.frames:
        step = next(
            (item for item in trace.steps if item.target_frame == frame.index), None
        )
        markers = []
        if frame.index == 0:
            via = "-"
            progress = "initial"
            events = "-"
            calls = "-"
            markers.append("I")
        elif step is None:
            via = "-"
            progress = "frame"
            events = "-"
            calls = "-"
        else:
            via, via_markers = _via_text(
                step.source_state,
                step.target_state,
                via_mode,
                tablefmt,
                max_cell_width,
                terminated_absorb=frame.terminated and step.case_kind == "absorb",
            )
            markers.extend(via_markers)
            progress, progress_markers = _limited_cell(
                (step.progress,), tablefmt, max_cell_width=max_cell_width
            )
            markers.extend(progress_markers)
            events, event_markers = _event_cell(
                step.input_events,
                step.event_reads,
                events_mode,
                event_reason,
                tablefmt,
                max_events,
                max_cell_width,
            )
            markers.extend(event_markers)
            calls, call_markers = _call_cell(
                step.abstract_calls,
                calls_mode,
                call_path,
                call_details,
                tablefmt,
                max_call_groups,
                max_cell_width,
            )
            markers.extend(call_markers)
            if step.delta:
                markers.append("D")
            if step.gamma:
                markers.append("G")
            if step.event_reads and events_mode == "input":
                markers.append("R")
        if frame.terminated:
            markers.append("T")
        if hidden_vars:
            markers.append("V")
        row = [str(frame.index)]
        if show_ids:
            if step is None:
                row.extend(["-", "-", "-", "-"])
            else:
                row.extend(
                    [
                        str(step.index),
                        str(step.source_frame),
                        str(step.target_frame),
                        step.case_kind,
                    ]
                )
        if show_case:
            row.append(step.case_label if step is not None else "-")
        state, state_markers = _limited_cell(
            (_state_label(frame),), tablefmt, max_cell_width=max_cell_width
        )
        markers.extend(state_markers)
        row.extend([via, state, progress])
        for name in var_names:
            value, var_markers = _limited_cell(
                (_format_scalar(frame.vars.get(name)),),
                tablefmt,
                max_cell_width=max_cell_width,
            )
            markers.extend(var_markers)
            row.append(value)
        row.extend([events, calls, _format_extra(markers)])
        rows.append(row)
    rows = _limit_rows(rows, max_rows, len(headers))
    parts = [_trace_preamble(trace), "", _tabulate_table(rows, headers, tablefmt)]
    if show_legend:
        parts.extend(["", _PRETTY_EXTRA_LEGEND])
    return "\n".join(parts)


def _limit_rows(
    rows: Sequence[Sequence[str]], max_rows: Optional[int], width: int
) -> Sequence[Sequence[str]]:
    if max_rows is None or len(rows) <= max_rows:
        return rows
    hidden = len(rows) - max_rows
    truncated = [list(row) for row in rows[:max_rows]]
    marker_row = ["-"] * width
    marker_row[0] = "…"
    if width >= 4:
        marker_row[3] = "… (+%d more rows)" % hidden
    else:  # pragma: no cover - all public trace tables have at least four columns.
        marker_row[-1] = "… (+%d more rows)" % hidden
    marker_row[-1] = _format_extra(("N",))
    truncated.append(marker_row)
    return truncated


def _validate_trace_pretty_options(
    max_rows: Optional[int],
    max_events: Optional[int],
    max_call_groups: Optional[int],
    max_cell_width: Optional[int],
    max_var_columns: Optional[int],
    vars_order: str,
    events_mode: str,
    event_reason: str,
    calls_mode: str,
    call_path: str,
    call_details: str,
    via_mode: str,
) -> None:
    _validate_optional_non_negative_int("max_rows", max_rows)
    _validate_optional_non_negative_int("max_events", max_events)
    _validate_optional_non_negative_int("max_call_groups", max_call_groups)
    _validate_optional_positive_int("max_cell_width", max_cell_width)
    _validate_optional_non_negative_int("max_var_columns", max_var_columns)
    _validate_pretty_choice("vars_order", vars_order, ("domain", "alpha"))
    _validate_pretty_choice("events_mode", events_mode, ("input", "all", "none"))
    _validate_pretty_choice("event_reason", event_reason, ("auto", "always", "never"))
    _validate_pretty_choice("calls_mode", calls_mode, ("none", "summary", "expanded"))
    _validate_pretty_choice("call_path", call_path, ("full", "short"))
    _validate_pretty_choice("call_details", call_details, ("state_vars", "full"))
    _validate_pretty_choice("via_mode", via_mode, ("endpoint", "full"))


def _render_runtime_trace(
    trace: "BmcRuntimeTrace",
    *,
    tablefmt: str,
    verbose: bool,
    max_rows: Optional[int],
    max_events: Optional[int],
    max_call_groups: Optional[int],
    max_cell_width: Optional[int],
    max_var_columns: Optional[int],
    vars_order: str,
    events_mode: str,
    event_reason: str,
    calls_mode: str,
    call_path: str,
    call_details: str,
    via_mode: str,
    show_case: bool,
    show_ids: bool,
    show_legend: bool,
) -> str:
    (
        events_mode,
        event_reason,
        calls_mode,
        call_details,
        via_mode,
        show_case,
        show_ids,
        show_legend,
    ) = _coerce_pretty_options(
        verbose,
        events_mode,
        event_reason,
        calls_mode,
        call_details,
        via_mode,
        show_case,
        show_ids,
        show_legend,
    )
    _validate_trace_pretty_options(
        max_rows,
        max_events,
        max_call_groups,
        max_cell_width,
        max_var_columns,
        vars_order,
        events_mode,
        event_reason,
        calls_mode,
        call_path,
        call_details,
        via_mode,
    )
    var_names, hidden_vars = _ordered_var_names(
        trace.frames, vars_order, max_var_columns
    )
    headers = ["frame"]
    if show_ids:
        headers.append("step")
    headers.extend(["via", "state", "progress"])
    headers.extend("[%s]" % name for name in var_names)
    headers.extend(["events", "calls", "extra"])
    rows = []
    for frame in trace.frames:
        step = (
            trace.steps[frame.index - 1]
            if 0 < frame.index <= len(trace.steps)
            else None
        )
        markers = []
        if frame.index == 0:
            via = "-"
            progress = "initial"
            events = "-"
            calls = "-"
            markers.append("I")
        elif step is None:
            via = "-"
            progress = "runtime_frame"
            events = "-"
            calls = "-"
        else:
            source = (
                trace.frames[frame.index - 1]
                if frame.index - 1 < len(trace.frames)
                else None
            )
            via, via_markers = _via_text(
                source,
                frame,
                via_mode,
                tablefmt,
                max_cell_width,
                terminated_absorb=frame.terminated
                and getattr(source, "terminated", False),
            )
            markers.extend(via_markers)
            progress = "runtime_step"
            events, event_markers = _runtime_event_cell(
                step.input_events,
                step.unconsumed_events,
                events_mode,
                tablefmt,
                max_events,
                max_cell_width,
            )
            markers.extend(event_markers)
            if step.unconsumed_events:
                markers.append("R")
            calls, call_markers = _call_cell(
                step.abstract_calls,
                calls_mode,
                call_path,
                call_details,
                tablefmt,
                max_call_groups,
                max_cell_width,
            )
            markers.extend(call_markers)
        if frame.terminated:
            markers.append("T")
        if hidden_vars:
            markers.append("V")
        row = [str(frame.index)]
        if show_ids:
            row.append(str(step.index) if step is not None else "-")
        state, state_markers = _limited_cell(
            (_state_label(frame),), tablefmt, max_cell_width=max_cell_width
        )
        markers.extend(state_markers)
        row.extend([via, state, progress])
        for name in var_names:
            value, var_markers = _limited_cell(
                (_format_scalar(frame.vars.get(name)),),
                tablefmt,
                max_cell_width=max_cell_width,
            )
            markers.extend(var_markers)
            row.append(value)
        row.extend([events, calls, _format_extra(markers)])
        rows.append(row)
    rows = _limit_rows(rows, max_rows, len(headers))
    parts = [
        _runtime_trace_preamble(trace),
        "",
        _tabulate_table(rows, headers, tablefmt),
    ]
    if show_legend:
        parts.extend(["", _PRETTY_EXTRA_LEGEND])
    return "\n".join(parts)


def _render_replay_result(result: "BmcReplayResult", **kwargs: Any) -> str:
    trace_text = _render_runtime_trace(result.runtime_trace, **kwargs)
    status = "ok" if result.ok else "mismatch"
    parts = [
        "BmcReplayResult[%s] mismatches=%d" % (status, len(result.mismatches)),
        "",
        trace_text,
    ]
    if result.mismatches:
        parts.append("")
        for mismatch in result.mismatches:
            parts.append(
                "MISMATCH %s: %s != %s"
                % (
                    mismatch.path,
                    _format_scalar(mismatch.expected),
                    _format_scalar(mismatch.actual),
                )
            )
    return "\n".join(parts)


def _canonical_for_pretty(obj: Any) -> Mapping[str, Any]:
    if isinstance(obj, BmcSolveResult):
        return obj.to_canonical()
    if isinstance(obj, BmcEventDecodePolicy):
        return obj.to_canonical()
    if isinstance(obj, BmcWitnessEvent):
        return obj.to_canonical()
    if isinstance(obj, BmcWitnessCallRecord):
        return obj.to_canonical()
    if isinstance(obj, BmcWitnessFrame):
        return obj.to_canonical()
    if isinstance(obj, BmcWitnessStep):
        return obj.to_canonical()
    if isinstance(obj, BmcRuntimeFrame):
        return obj.to_canonical()
    if isinstance(obj, BmcRuntimeStep):
        return obj.to_canonical()
    if isinstance(obj, BmcReplayMismatch):
        return obj.to_canonical()
    return {"value": obj}  # pragma: no cover - mixin is only used by known classes.


def _render_field_value_object(obj: Any, tablefmt: str) -> str:
    rows = []
    for key, value in _canonical_for_pretty(obj).items():
        if key == "node":
            continue
        rows.append((key, _format_scalar(value)))
    return "\n".join(
        [
            obj.__class__.__name__,
            _tabulate_table(rows, ("field", "value"), tablefmt),
        ]
    )


def _render_pretty_object(
    obj: Any,
    *,
    tablefmt: str,
    verbose: bool,
    max_rows: Optional[int],
    max_events: Optional[int],
    max_call_groups: Optional[int],
    max_cell_width: Optional[int],
    max_var_columns: Optional[int],
    vars_order: str,
    events_mode: str,
    event_reason: str,
    calls_mode: str,
    call_path: str,
    call_details: str,
    via_mode: str,
    show_case: bool,
    show_ids: bool,
    show_legend: bool,
) -> str:
    if not isinstance(tablefmt, str) or not tablefmt:
        raise BmcBuildError("tablefmt must be a non-empty string.")
    if tablefmt not in tabulate_formats:
        raise BmcBuildError(
            "tablefmt must be a tabulate-supported format, got %r." % tablefmt
        )
    kwargs = {
        "tablefmt": tablefmt,
        "verbose": verbose,
        "max_rows": max_rows,
        "max_events": max_events,
        "max_call_groups": max_call_groups,
        "max_cell_width": max_cell_width,
        "max_var_columns": max_var_columns,
        "vars_order": vars_order,
        "events_mode": events_mode,
        "event_reason": event_reason,
        "calls_mode": calls_mode,
        "call_path": call_path,
        "call_details": call_details,
        "via_mode": via_mode,
        "show_case": show_case,
        "show_ids": show_ids,
        "show_legend": show_legend,
    }
    if isinstance(obj, BmcWitnessTrace):
        return _render_witness_trace(obj, **kwargs)
    if isinstance(obj, BmcRuntimeTrace):
        return _render_runtime_trace(obj, **kwargs)
    if isinstance(obj, BmcReplayResult):
        return _render_replay_result(obj, **kwargs)
    return _render_field_value_object(obj, tablefmt)


class _PrettyPrintableMixin:
    def pretty_print(
        self,
        *,
        file: Optional[Any] = None,
        tablefmt: str = "simple",
        verbose: bool = False,
        max_rows: Optional[int] = None,
        max_events: Optional[int] = 6,
        max_call_groups: Optional[int] = 6,
        max_cell_width: Optional[int] = 72,
        max_var_columns: Optional[int] = None,
        vars_order: str = "domain",
        events_mode: str = "input",
        event_reason: str = "auto",
        calls_mode: str = "summary",
        call_path: str = "full",
        call_details: str = "state_vars",
        via_mode: str = "endpoint",
        show_case: bool = False,
        show_ids: bool = False,
        show_legend: bool = True,
        end: str = "\n",
    ) -> None:
        """Print a human-readable representation.

        :param file: File-like object to write to, defaults to ``sys.stdout``.
        :type file: object, optional
        :param tablefmt: ``tabulate`` table format, defaults to ``"simple"``.
        :type tablefmt: str, optional
        :param verbose: Whether to enable the verbose audit view, defaults to
            ``False``.
        :type verbose: bool, optional
        :param max_rows: Maximum trace rows to show, defaults to ``None``.
        :type max_rows: int, optional
        :param max_events: Maximum event lines per step, defaults to ``6``.
        :type max_events: int, optional
        :param max_call_groups: Maximum call lines per step, defaults to ``6``.
        :type max_call_groups: int, optional
        :param max_cell_width: Maximum logical cell-line width, defaults to
            ``72``.
        :type max_cell_width: int, optional
        :param max_var_columns: Maximum variable columns, defaults to ``None``.
        :type max_var_columns: int, optional
        :param vars_order: Variable column order, defaults to ``"domain"``.
        :type vars_order: str, optional
        :param events_mode: Event display mode, defaults to ``"input"``.
        :type events_mode: str, optional
        :param event_reason: Event reason tag mode, defaults to ``"auto"``.
        :type event_reason: str, optional
        :param calls_mode: Abstract-call display mode, defaults to
            ``"summary"``.
        :type calls_mode: str, optional
        :param call_path: Abstract-call path display mode, defaults to
            ``"full"``.
        :type call_path: str, optional
        :param call_details: Expanded call detail mode, defaults to
            ``"state_vars"``.
        :type call_details: str, optional
        :param via_mode: Transition path display mode, defaults to
            ``"endpoint"``.
        :type via_mode: str, optional
        :param show_case: Whether to show selected BMC case labels, defaults to
            ``False``.
        :type show_case: bool, optional
        :param show_ids: Whether to show debug id columns, defaults to
            ``False``.
        :type show_ids: bool, optional
        :param show_legend: Whether to append the ``extra`` legend, defaults to
            ``True``.
        :type show_legend: bool, optional
        :param end: String appended after output, defaults to a newline.
        :type end: str, optional
        :return: ``None``.
        :rtype: None

        Example::

            >>> BmcWitnessEvent('Root.Go', 'case_positive').to_text().splitlines()[0]
            'BmcWitnessEvent'
        """
        if file is None:
            file = sys.stdout
        if not isinstance(end, str):
            raise BmcBuildError("end must be str.")
        text = _render_pretty_object(
            self,
            tablefmt=tablefmt,
            verbose=verbose,
            max_rows=max_rows,
            max_events=max_events,
            max_call_groups=max_call_groups,
            max_cell_width=max_cell_width,
            max_var_columns=max_var_columns,
            vars_order=vars_order,
            events_mode=events_mode,
            event_reason=event_reason,
            calls_mode=calls_mode,
            call_path=call_path,
            call_details=call_details,
            via_mode=via_mode,
            show_case=show_case,
            show_ids=show_ids,
            show_legend=show_legend,
        )
        file.write(text)
        file.write(end)

    def to_text(self, **kwargs: Any) -> str:
        """Return a human-readable representation as text.

        :param kwargs: Pretty-print options except ``file`` and ``end``.
        :type kwargs: object
        :return: Rendered text.
        :rtype: str
        :raises pyfcstm.bmc.errors.BmcBuildError: If ``file`` or ``end`` is
            passed to this string-returning helper.

        Example::

            >>> BmcWitnessEvent('Root.Go', 'case_positive').to_text().startswith('BmcWitnessEvent')
            True
        """
        if "file" in kwargs or "end" in kwargs:
            raise BmcBuildError("to_text does not accept file or end.")
        buffer = io.StringIO()
        self.pretty_print(file=buffer, end="", **kwargs)
        return buffer.getvalue()

    def __str__(self) -> str:
        """Return the default terminal-friendly representation.

        Trace-like objects cap this implicit display at the first 50 rows so a
        direct ``print(obj)`` remains practical in terminals.  Use
        :meth:`to_text` or :meth:`pretty_print` with ``max_rows=None`` when the
        full table is required.

        :return: Rendered text.
        :rtype: str

        Example::

            >>> str(BmcWitnessEvent('Root.Go', 'case_positive')).splitlines()[0]
            'BmcWitnessEvent'
        """
        return self.to_text(max_rows=_PRETTY_STR_MAX_ROWS)


def _require_formula(formula: object) -> BmcPropertyFormula:
    if not isinstance(formula, BmcPropertyFormula):
        raise BmcBuildError("formula must be BmcPropertyFormula.")
    return formula


def _require_model(model: object) -> z3.ModelRef:
    if not isinstance(model, z3.ModelRef):
        raise BmcBuildError("model must be z3.ModelRef.")
    return model


def _z3_bool_value(model: z3.ModelRef, expr: z3.BoolRef) -> bool:
    value = model.eval(expr, model_completion=True)
    if z3.is_true(value):
        return True
    if z3.is_false(value):
        return False
    raise _internal_error("Z3 expression did not evaluate to a Boolean: %s." % expr)


def _decimal_text_to_int(text: str) -> int:
    sign = -1 if text.startswith("-") else 1
    digits = text[1:] if sign < 0 else text
    if not digits.isdigit():  # pragma: no cover - Z3 integer text is decimal.
        raise _internal_error("Z3 integer numeral is not decimal text: %s." % text)
    result = 0
    chunk_size = 1000
    for start in range(0, len(digits), chunk_size):
        chunk = digits[start : start + chunk_size]
        result = result * (10 ** len(chunk)) + int(chunk)
    return sign * result


def _z3_int_value(model: z3.ModelRef, expr: z3.ArithRef) -> int:
    value = model.eval(expr, model_completion=True)
    if z3.is_int_value(value):
        return _decimal_text_to_int(value.as_string())
    raise _internal_error("Z3 expression did not evaluate to an integer: %s." % expr)


def _z3_number_value(
    model: z3.ModelRef, expr: z3.ArithRef, declared_type: Optional[str] = None
) -> Any:
    value = model.eval(expr, model_completion=True)
    if z3.is_int_value(value):
        return _decimal_text_to_int(value.as_string())
    if z3.is_rational_value(value):
        rational = Fraction(value.numerator_as_long(), value.denominator_as_long())
        if declared_type == "int" and rational.denominator == 1:
            return rational.numerator
        return float(rational)
    raise _internal_error(
        "Z3 expression did not evaluate to a numeric value: %s." % expr
    )


def _solve(
    expr: z3.BoolRef, timeout_ms: Optional[int]
) -> Tuple[BmcSolveStatus, Optional[z3.ModelRef], Optional[str], float]:
    solver = z3.Solver()
    if timeout_ms is not None:
        if (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or timeout_ms <= 0
        ):
            raise BmcBuildError("timeout_ms must be a positive integer or None.")
        solver.set(timeout=timeout_ms)
    solver.add(expr)
    start = time.monotonic()
    status = solver.check()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    if status == z3.sat:
        return "sat", solver.model(), None, elapsed_ms
    if status == z3.unsat:
        return "unsat", None, None, elapsed_ms
    reason = solver.reason_unknown()
    if reason == "timeout":
        return "timeout", None, reason, elapsed_ms
    return "unknown", None, reason, elapsed_ms


@dataclass(frozen=True)
class BmcSolveResult(_PrettyPrintableMixin):
    """Structured result for one BMC property solve.

    The raw Z3 models are intentionally kept as Python attributes rather than
    JSON fields.  Callers can pass :attr:`model` to
    :func:`decode_bmc_witness` when :attr:`status` is ``"sat"`` while
    :meth:`to_canonical` remains JSON-stable for logs and tests.  Verdict
    properties such as :attr:`property_satisfied`, :attr:`witness_found`, and
    :attr:`counterexample_found` translate solver objective satisfiability into
    user-facing bounded property results.  Manually constructed SAT results
    must carry their SAT model, and non-SAT results must not carry a model, so
    the public status and replay payload cannot diverge.

    :param formula: Compiled BMC property formula that was solved.
    :type formula: pyfcstm.bmc.properties.BmcPropertyFormula
    :param status: Solver status for ``formula.solve_formula``.
    :type status: str
    :param model: SAT model for ``formula.solve_formula``, defaults to ``None``.
    :type model: z3.ModelRef, optional
    :param reason: Raw solver reason for ``"unknown"`` or ``"timeout"``
        primary statuses, defaults to ``None``.
    :type reason: str, optional
    :param elapsed_ms: Objective solve wall time in milliseconds, defaults to
        ``0.0``.
    :type elapsed_ms: float, optional
    :param timeout_ms: Configured timeout in milliseconds, defaults to ``None``.
    :type timeout_ms: int, optional
    :param incomplete_status: Solver status for the incomplete-bound formula,
        defaults to ``None``.
    :type incomplete_status: str, optional
    :param incomplete_model: SAT model for the incomplete-bound formula,
        defaults to ``None``.
    :type incomplete_model: z3.ModelRef, optional
    :param incomplete_reason: Raw solver reason for an inconclusive
        incomplete-bound solve, or a diagnostic reason when that solve was not
        executed, defaults to ``None``.
    :type incomplete_reason: str, optional
    :param diagnostics: Solver-level diagnostics, defaults to ``()``.
    :type diagnostics: Tuple[str, ...], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the solve result payload is
        malformed.

    Example::

        >>> import z3
        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> sm = load_state_machine_from_text('state Root;')
        >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
        >>> result = solve_bmc_property(formula)
        >>> result.to_canonical()['status'] in {'sat', 'unsat', 'unknown', 'timeout'}
        True
    """

    formula: BmcPropertyFormula
    status: BmcSolveStatus
    model: Optional[z3.ModelRef] = field(default=None, repr=False, compare=False)
    reason: Optional[str] = None
    elapsed_ms: float = 0.0
    timeout_ms: Optional[int] = None
    incomplete_status: Optional[BmcSolveStatus] = None
    incomplete_model: Optional[z3.ModelRef] = field(
        default=None, repr=False, compare=False
    )
    incomplete_reason: Optional[str] = None
    diagnostics: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _require_formula(self.formula)
        if self.status not in {"sat", "unsat", "unknown", "timeout"}:
            raise BmcBuildError("status must be sat, unsat, unknown, or timeout.")
        if self.model is not None and not isinstance(self.model, z3.ModelRef):
            raise BmcBuildError("model must be z3.ModelRef or None.")
        if self.incomplete_status is not None and self.incomplete_status not in {
            "sat",
            "unsat",
            "unknown",
            "timeout",
        }:
            raise BmcBuildError(
                "incomplete_status must be sat, unsat, unknown, timeout, or None."
            )
        if self.incomplete_model is not None and not isinstance(
            self.incomplete_model, z3.ModelRef
        ):
            raise BmcBuildError("incomplete_model must be z3.ModelRef or None.")
        _validate_primary_solve_reason("status", self.status, "reason", self.reason)
        _validate_elapsed_ms(self.elapsed_ms)
        _validate_incomplete_solve_reason(
            "incomplete_status",
            self.incomplete_status,
            "incomplete_reason",
            self.incomplete_reason,
        )
        if self.timeout_ms is not None and (
            isinstance(self.timeout_ms, bool)
            or not isinstance(self.timeout_ms, int)
            or self.timeout_ms <= 0
        ):
            raise BmcBuildError("timeout_ms must be a positive integer or None.")
        object.__setattr__(
            self,
            "diagnostics",
            _coerce_public_sequence("diagnostics", self.diagnostics, str, "strings"),
        )
        if self.status == "sat" and self.model is None:
            raise BmcBuildError("model is required when status is sat.")
        if self.status != "sat" and self.model is not None:
            raise BmcBuildError("model must be None unless status is sat.")
        if self.incomplete_status == "sat" and self.incomplete_model is None:
            raise BmcBuildError(
                "incomplete_model is required when incomplete_status is sat."
            )
        if self.incomplete_status != "sat" and self.incomplete_model is not None:
            raise BmcBuildError(
                "incomplete_model must be None unless incomplete_status is sat."
            )

    @property
    def kind(self) -> str:
        """Return the property kind.

        :return: Property kind.
        :rtype: str

        Example::

            >>> from pyfcstm.bmc.query import BmcProperty
            >>> from pyfcstm.bmc.properties import BmcPropertyFormula, _lower_predicate
            >>> # ``kind`` is copied from the solved formula.
        """
        return self.formula.kind

    @property
    def polarity(self) -> str:
        """Return whether SAT is a witness or counterexample.

        :return: Formula polarity.
        :rtype: str

        Example::

            >>> # For reach properties, SAT is a witness.
        """
        return self.formula.polarity

    @property
    def incomplete(self) -> bool:
        """Return whether the verdict is known to be horizon-incomplete.

        Solver ``unknown`` and ``timeout`` statuses are always incomplete.  A
        response property is also incomplete when the primary objective is
        ``"unsat"`` and its suffix diagnostic was not solved, was inconclusive,
        or can still contain an uncovered trigger window.  If the primary
        response objective is ``"sat"``, the counterexample verdict is already
        decisive even when a separate suffix diagnostic would also be
        satisfiable.

        :return: Whether the solve result carries an incomplete verdict.
        :rtype: bool

        Example::

            >>> from pyfcstm.bmc.witness import BmcSolveResult
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
            >>> BmcSolveResult(formula, 'timeout', reason='timeout').incomplete
            True
        """
        if self.status in {"unknown", "timeout"}:
            return True
        if self.kind != "response" or self.status != "unsat":
            return False
        if z3.is_false(self.formula.incomplete_formula):
            return False
        return self.incomplete_status in {
            None,
            "sat",
            "unknown",
            "timeout",
        }

    @property
    def witness_found(self) -> bool:
        """Return whether the primary objective found a positive witness.

        :return: ``True`` when SAT means a witness and the primary objective is
            satisfiable.
        :rtype: bool

        Example::

            >>> import z3
            >>> from pyfcstm.bmc.witness import BmcSolveResult
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
            >>> solver = z3.Solver()
            >>> solver.add(z3.BoolVal(True))
            >>> solver.check() == z3.sat
            True
            >>> BmcSolveResult(formula, 'sat', model=solver.model()).witness_found
            True
        """
        return self.status == "sat" and self.polarity == "witness"

    @property
    def counterexample_found(self) -> bool:
        """Return whether the primary objective found a counterexample.

        :return: ``True`` when SAT means a violation trace and the primary
            objective is satisfiable.
        :rtype: bool

        Example::

            >>> import z3
            >>> from pyfcstm.bmc.witness import BmcSolveResult
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check forbid <= 1: active("Root");')))
            >>> solver = z3.Solver()
            >>> solver.add(z3.BoolVal(True))
            >>> solver.check() == z3.sat
            True
            >>> BmcSolveResult(formula, 'sat', model=solver.model()).counterexample_found
            True
        """
        return self.status == "sat" and self.polarity == "counterexample"

    @property
    def property_satisfied(self) -> Optional[bool]:
        """Return the user-facing bounded property verdict.

        This verdict translates the solver objective status through
        :attr:`polarity`.  Witness objectives are satisfied exactly when SAT
        finds a witness.  Counterexample objectives are satisfied exactly when
        the counterexample search is UNSAT, except response properties whose
        suffix diagnostic is unsolved, satisfiable, or inconclusive remain
        incomplete.

        :return: ``True`` if the bounded property is satisfied, ``False`` if it
            is violated or lacks a required witness, and ``None`` if the result
            is incomplete.
        :rtype: Optional[bool]

        Example::

            >>> from pyfcstm.bmc.witness import BmcSolveResult
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: terminated();')))
            >>> BmcSolveResult(formula, 'unsat').property_satisfied
            False
        """
        if self.status in {"unknown", "timeout"}:
            return None
        if self.status == "sat":
            return self.polarity == "witness"
        if self.kind == "response" and self.incomplete:
            return None
        return self.polarity == "counterexample"

    @property
    def outcome(self) -> str:
        """Return a stable user-facing outcome label.

        :return: One of ``"property_satisfied"``, ``"property_violated"``,
            ``"witness_found"``, ``"no_witness"``, ``"incomplete"``,
            ``"timeout"``, or ``"unknown"``.
        :rtype: str

        Example::

            >>> from pyfcstm.bmc.witness import BmcSolveResult
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: terminated();')))
            >>> BmcSolveResult(formula, 'unsat').outcome
            'no_witness'
        """
        if self.status == "timeout":
            return "timeout"
        if self.status == "unknown":
            return "unknown"
        if self.status == "sat":
            if self.polarity == "witness":
                return "witness_found"
            return "property_violated"
        if self.kind == "response" and self.incomplete:
            return "incomplete"
        if self.polarity == "witness":
            return "no_witness"
        return "property_satisfied"

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable solve summary.

        Raw Z3 models are excluded because they are not JSON values.  The
        decoded witness carries model assignments in stable frame and step
        fields after :func:`decode_bmc_witness` succeeds.

        :return: Canonical solve result.
        :rtype: Dict[str, object]

        Example::

            >>> import z3
            >>> from pyfcstm.bmc.witness import BmcSolveResult
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
            >>> BmcSolveResult(formula, 'unsat').to_canonical()['status']
            'unsat'
        """
        return {
            "node": "bmc_solve_result",
            "kind": self.kind,
            "polarity": self.polarity,
            "status": self.status,
            "property_satisfied": self.property_satisfied,
            "witness_found": self.witness_found,
            "counterexample_found": self.counterexample_found,
            "incomplete": self.incomplete,
            "outcome": self.outcome,
            "reason": self.reason,
            "elapsed_ms": self.elapsed_ms,
            "timeout_ms": self.timeout_ms,
            "has_model": self.model is not None,
            "incomplete_status": self.incomplete_status,
            "incomplete_reason": self.incomplete_reason,
            "has_incomplete_model": self.incomplete_model is not None,
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class BmcEventDecodePolicy(_PrettyPrintableMixin):
    """Policy for decoding sparse replay events from a SAT model.

    The default policy emits the canonical replay-minimal event set plus debug
    reads for negative or false assumptions.  It intentionally does not expose
    a mode that dumps every true Z3 event Boolean because model completion can
    make irrelevant event symbols true and pollute replay inputs.

    :param include_debug_reads: Whether to include non-replay event reads in
        :attr:`BmcWitnessStep.event_reads`, defaults to ``True``.
    :type include_debug_reads: bool, optional
    :param include_property_support: Whether response-trigger support events
        may be added when they are required to replay a response counterexample,
        defaults to ``True``. If disabled, decoding still succeeds when support
        is unnecessary, but fails loudly rather than emitting a non-faithful
        trace when support is required.
    :type include_property_support: bool, optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If a policy flag is malformed.

    Example::

        >>> BmcEventDecodePolicy().include_debug_reads
        True
    """

    include_debug_reads: bool = True
    include_property_support: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.include_debug_reads, bool):
            raise BmcBuildError("include_debug_reads must be bool.")
        if not isinstance(self.include_property_support, bool):
            raise BmcBuildError("include_property_support must be bool.")

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable event decode policy.

        :return: Canonical event decode policy.
        :rtype: Dict[str, object]

        Example::

            >>> BmcEventDecodePolicy().to_canonical()['include_debug_reads']
            True
        """
        return {
            "node": "bmc_event_decode_policy",
            "include_debug_reads": self.include_debug_reads,
            "include_property_support": self.include_property_support,
        }


@dataclass(frozen=True)
class BmcWitnessEvent(_PrettyPrintableMixin):
    """Replay input event decoded for one BMC step.

    :param path: Fully qualified event path.
    :type path: str
    :param reason: Decode reason such as ``"case_positive"``.
    :type reason: str
    :param model_value: Boolean value observed in the SAT model.
    :type model_value: bool
    :raises pyfcstm.bmc.errors.BmcBuildError: If the event payload is
        malformed.

    Example::

        >>> BmcWitnessEvent('Root.Go', 'case_positive').to_canonical()['path']
        'Root.Go'
    """

    path: str
    reason: str
    model_value: bool = True

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path:
            raise BmcBuildError("event path must be a non-empty string.")
        if self.reason not in {
            "case_positive",
            "explicit_true_assumption",
            "property_support",
            "negative_case_read",
            "explicit_false_assumption",
            "model_debug",
        }:
            raise BmcBuildError("Unsupported witness event reason: %r." % self.reason)
        if not isinstance(self.model_value, bool):
            raise BmcBuildError("model_value must be bool.")

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable event dictionary.

        :return: Canonical event dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> BmcWitnessEvent('Root.Go', 'case_positive').to_canonical()['reason']
            'case_positive'
        """
        return {
            "path": self.path,
            "reason": self.reason,
            "model_value": self.model_value,
        }


@dataclass(frozen=True)
class BmcWitnessCallRecord(_PrettyPrintableMixin):
    """Decoded abstract-call occurrence for one selected macro-step case.

    :param ordinal: Call ordinal within the selected case.
    :type ordinal: int
    :param action_name: Resolved abstract action path.
    :type action_name: str
    :param stage: Runtime call stage.
    :type stage: str
    :param role: Runtime action-block role.
    :type role: str
    :param state: Calling state path.
    :type state: str
    :param active_leaf: Active leaf path visible to the handler.
    :type active_leaf: str
    :param named_ref: Named ``ref`` callsite path, defaults to ``None``.
    :type named_ref: str, optional
    :param snapshot: Persistent variable snapshot before the handler call,
        defaults to ``{}``.
    :type snapshot: Mapping[str, object], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the call-record payload is
        malformed.

    Example::

        >>> rec = BmcWitnessCallRecord(0, 'Root.A.Hook', 'during', 'leaf_during', 'Root.A', 'Root.A')
        >>> rec.to_canonical()['ordinal']
        0
    """

    ordinal: int
    action_name: str
    stage: str
    role: str
    state: str
    active_leaf: str
    named_ref: Optional[str] = None
    snapshot: Mapping[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if (
            isinstance(self.ordinal, bool)
            or not isinstance(self.ordinal, int)
            or self.ordinal < 0
        ):
            raise BmcBuildError("ordinal must be a non-negative integer.")
        for field_name in ("action_name", "stage", "role", "state", "active_leaf"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise BmcBuildError("%s must be a non-empty string." % field_name)
        if self.named_ref is not None and (
            not isinstance(self.named_ref, str) or not self.named_ref
        ):
            raise BmcBuildError("named_ref must be a non-empty string or None.")
        object.__setattr__(
            self, "snapshot", _coerce_public_value_mapping("snapshot", self.snapshot)
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable call record.

        :return: Canonical call record.
        :rtype: Dict[str, object]

        Example::

            >>> BmcWitnessCallRecord(0, 'Root.A.Hook', 'during', 'leaf_during', 'Root.A', 'Root.A').to_canonical()['action_name']
            'Root.A.Hook'
        """
        return {
            "ordinal": self.ordinal,
            "action_name": self.action_name,
            "stage": self.stage,
            "role": self.role,
            "state": self.state,
            "active_leaf": self.active_leaf,
            "named_ref": self.named_ref,
            "snapshot": _canonical_public_value_mapping("snapshot", self.snapshot),
        }


@dataclass(frozen=True)
class BmcWitnessFrame(_PrettyPrintableMixin):
    """Decoded public frame in a BMC witness trace.

    :param index: Frame index.
    :type index: int
    :param state_id: Normal state id or ``None`` for sentinels.
    :type state_id: int, optional
    :param state: Normal state path or ``None`` for sentinels.
    :type state: str, optional
    :param sentinel: ``"init"``, ``"terminated"``, or ``None``.
    :type sentinel: str, optional
    :param terminated: Whether this frame is terminated.
    :type terminated: bool
    :param vars: Persistent variable values.
    :type vars: Mapping[str, object]
    :raises pyfcstm.bmc.errors.BmcBuildError: If the frame payload is
        malformed.

    Example::

        >>> BmcWitnessFrame(0, None, None, 'init', False, {}).to_canonical()['sentinel']
        'init'
    """

    index: int
    state_id: Optional[int]
    state: Optional[str]
    sentinel: Optional[str]
    terminated: bool
    vars: Mapping[str, Any]

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise BmcBuildError("frame index must be a non-negative integer.")
        if self.state_id is not None and (
            isinstance(self.state_id, bool) or not isinstance(self.state_id, int)
        ):
            raise BmcBuildError("state_id must be an integer or None.")
        if self.state is not None and (
            not isinstance(self.state, str) or not self.state
        ):
            raise BmcBuildError("state must be a non-empty string or None.")
        if self.sentinel not in {None, "init", "terminated"}:
            raise BmcBuildError("sentinel must be init, terminated, or None.")
        if self.sentinel is not None and (
            self.state_id is not None or self.state is not None
        ):
            raise BmcBuildError("sentinel frames must not set state_id or state.")
        if not isinstance(self.terminated, bool):
            raise BmcBuildError("terminated must be bool.")
        if self.sentinel == "init" and self.terminated:
            raise BmcBuildError("init sentinel frames must not be terminated.")
        if self.sentinel == "terminated" and not self.terminated:
            raise BmcBuildError("terminated sentinel frames must be terminated.")
        object.__setattr__(
            self, "vars", _coerce_public_value_mapping("vars", self.vars)
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable frame dictionary.

        :return: Canonical frame.
        :rtype: Dict[str, object]

        Example::

            >>> BmcWitnessFrame(0, None, None, 'init', False, {}).to_canonical()['state'] is None
            True
        """
        return {
            "index": self.index,
            "state_id": self.state_id,
            "state": self.state,
            "sentinel": self.sentinel,
            "terminated": self.terminated,
            "vars": _canonical_public_value_mapping("vars", self.vars),
        }


@dataclass(frozen=True)
class BmcWitnessStep(_PrettyPrintableMixin):
    """Decoded macro-step witness entry.

    :param index: Step index.
    :type index: int
    :param source_frame: Source frame index.
    :type source_frame: int
    :param target_frame: Target frame index.
    :type target_frame: int
    :param case_label: Selected BMC case label.
    :type case_label: str
    :param case_kind: Selected BMC case kind, such as ``"initial"``,
        ``"transition"``, ``"fallback"``, ``"delta"``, or ``"absorb"``.
    :type case_kind: str
    :param progress: Replay-friendly progress classification.
    :type progress: str
    :param source_state: Source state path or ``None`` for sentinels.
    :type source_state: str, optional
    :param target_state: Target state path or ``None`` for sentinels.
    :type target_state: str, optional
    :param delta: Decoded ``Delta_i`` flag.
    :type delta: bool
    :param gamma: Decoded ``Gamma_i`` flag.
    :type gamma: bool
    :param input_events: Sparse replay input events whose reasons are replay
        inputs and whose model values are ``True``, defaults to ``()``.
    :type input_events: Sequence[BmcWitnessEvent], optional
    :param event_reads: Debug-only event reads, defaults to ``()``.
    :type event_reads: Sequence[BmcWitnessEvent], optional
    :param abstract_calls: Decoded abstract-call records, defaults to ``()``.
    :type abstract_calls: Sequence[BmcWitnessCallRecord], optional
    :param consumed_events: Event paths consumed by selected evented
        transitions in micro-step order, defaults to ``()``.
    :type consumed_events: Sequence[str], optional
    :param unconsumed_events: Replay input event paths not consumed by the
        selected macro path. ``None`` derives the value from ``input_events``
        and ``consumed_events``, defaults to ``None``.
    :type unconsumed_events: Sequence[str], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the step payload is
        malformed.

    Example::

        >>> step = BmcWitnessStep(0, 0, 1, 'Root::fallback::Root::0', 'fallback', 'fallback_gamma', 'Root', 'Root', False, True)
        >>> step.to_canonical()['progress']
        'fallback_gamma'
    """

    index: int
    source_frame: int
    target_frame: int
    case_label: str
    case_kind: str
    progress: str
    source_state: Optional[str]
    target_state: Optional[str]
    delta: bool
    gamma: bool
    input_events: Sequence[BmcWitnessEvent] = ()
    event_reads: Sequence[BmcWitnessEvent] = ()
    abstract_calls: Sequence[BmcWitnessCallRecord] = ()
    consumed_events: Sequence[str] = ()
    unconsumed_events: Optional[Sequence[str]] = None

    def __post_init__(self) -> None:
        for field_name in ("index", "source_frame", "target_frame"):
            value = getattr(self, field_name)
            if isinstance(value, bool) or not isinstance(value, int) or value < 0:
                raise BmcBuildError("%s must be a non-negative integer." % field_name)
        for field_name in ("case_label", "case_kind", "progress"):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise BmcBuildError("%s must be a non-empty string." % field_name)
        for field_name in ("source_state", "target_state"):
            value = getattr(self, field_name)
            if value is not None and (not isinstance(value, str) or not value):
                raise BmcBuildError(
                    "%s must be a non-empty string or None." % field_name
                )
        if not isinstance(self.delta, bool) or not isinstance(self.gamma, bool):
            raise BmcBuildError("delta and gamma must be bool.")
        object.__setattr__(
            self,
            "input_events",
            _coerce_public_sequence(
                "input_events",
                self.input_events,
                BmcWitnessEvent,
                "BmcWitnessEvent objects",
            ),
        )
        object.__setattr__(
            self,
            "event_reads",
            _coerce_public_sequence(
                "event_reads",
                self.event_reads,
                BmcWitnessEvent,
                "BmcWitnessEvent objects",
            ),
        )
        for event in self.input_events:
            if event.reason not in _REPLAY_EVENT_REASONS:
                raise BmcBuildError(
                    "input_events must contain only replay input event reasons."
                )
            if event.model_value is not True:
                raise BmcBuildError("input_events must have model_value true.")
        for event in self.event_reads:
            if event.reason in _REPLAY_EVENT_REASONS:
                raise BmcBuildError(
                    "event_reads must contain only debug event reasons."
                )
        for field_name in ("input_events", "event_reads"):
            paths = [event.path for event in getattr(self, field_name)]
            if len(paths) != len(set(paths)):
                raise BmcBuildError(
                    "%s must contain at most one event per path." % field_name
                )
        object.__setattr__(
            self,
            "abstract_calls",
            _coerce_public_sequence(
                "abstract_calls",
                self.abstract_calls,
                BmcWitnessCallRecord,
                "BmcWitnessCallRecord objects",
            ),
        )
        object.__setattr__(
            self,
            "consumed_events",
            _coerce_public_sequence(
                "consumed_events", self.consumed_events, str, "strings"
            ),
        )
        input_paths = self.input_event_paths
        if any(path not in set(input_paths) for path in self.consumed_events):
            raise BmcBuildError(
                "consumed_events must reference replay input event paths."
            )
        expected_unconsumed = _unconsumed_event_paths(input_paths, self.consumed_events)
        if self.unconsumed_events is None:
            object.__setattr__(self, "unconsumed_events", expected_unconsumed)
        else:
            object.__setattr__(
                self,
                "unconsumed_events",
                _coerce_public_sequence(
                    "unconsumed_events",
                    self.unconsumed_events,
                    str,
                    "strings",
                ),
            )
        if tuple(self.unconsumed_events) != expected_unconsumed:
            raise BmcBuildError(
                "unconsumed_events must equal input events minus consumed events."
            )

    @property
    def input_event_paths(self) -> Tuple[str, ...]:
        """Return replay input event paths in witness order.

        :return: Event paths.
        :rtype: Tuple[str, ...]

        Example::

            >>> step = BmcWitnessStep(0, 0, 1, 'c', 'fallback', 'fallback_gamma', 'Root', 'Root', False, True)
            >>> step.input_event_paths
            ()
        """
        return tuple(item.path for item in self.input_events)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable step dictionary.

        :return: Canonical step.
        :rtype: Dict[str, object]

        Example::

            >>> step = BmcWitnessStep(0, 0, 1, 'c', 'fallback', 'fallback_gamma', 'Root', 'Root', False, True)
            >>> step.to_canonical()['delta']
            False
        """
        return {
            "index": self.index,
            "source_frame": self.source_frame,
            "target_frame": self.target_frame,
            "case_label": self.case_label,
            "case_kind": self.case_kind,
            "progress": self.progress,
            "source_state": self.source_state,
            "target_state": self.target_state,
            "delta": self.delta,
            "gamma": self.gamma,
            "input_events": [item.to_canonical() for item in self.input_events],
            "event_reads": [item.to_canonical() for item in self.event_reads],
            "abstract_calls": [item.to_canonical() for item in self.abstract_calls],
            "consumed_events": list(self.consumed_events),
            "unconsumed_events": list(self.unconsumed_events),
        }


@dataclass(frozen=True)
class BmcWitnessTrace(_PrettyPrintableMixin):
    """Decoded BMC witness trace.

    The metadata dictionaries are public JSON-stable payloads.  They may
    contain strings, booleans, ``None``, finite numeric values, nested mappings,
    and lists, but not arbitrary Python objects or non-finite floating-point
    values. The ``bmc-witness/v1`` step schema includes canonical replay input
    events, ordered consumed event paths, and presence-derived unconsumed event
    paths.

    :param property: Property metadata.
    :type property: Mapping[str, object]
    :param solver: Solver metadata.
    :type solver: Mapping[str, object]
    :param initial: Initial replay metadata.
    :type initial: Mapping[str, object]
    :param frames: Decoded frames.
    :type frames: Sequence[BmcWitnessFrame]
    :param steps: Decoded steps.
    :type steps: Sequence[BmcWitnessStep]
    :param diagnostics: Witness diagnostics, defaults to ``()``.
    :type diagnostics: Sequence[str], optional
    :param schema_version: Witness schema version, defaults to
        ``"bmc-witness/v1"``.
    :type schema_version: str, optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the trace payload is
        malformed or violates public witness invariants.

    Example::

        >>> trace = BmcWitnessTrace({'kind': 'reach'}, {'status': 'sat'}, {'mode': 'cold'}, (), ())
        >>> trace.to_canonical()['schema_version']
        'bmc-witness/v1'
    """

    property: Mapping[str, Any]
    solver: Mapping[str, Any]
    initial: Mapping[str, Any]
    frames: Sequence[BmcWitnessFrame]
    steps: Sequence[BmcWitnessStep]
    diagnostics: Sequence[str] = ()
    schema_version: str = "bmc-witness/v1"

    def __post_init__(self) -> None:
        if self.schema_version != "bmc-witness/v1":
            raise BmcBuildError(
                "Unsupported witness schema version: %r." % self.schema_version
            )
        if not isinstance(self.property, Mapping):
            raise BmcBuildError("property must be a mapping.")
        if not isinstance(self.solver, Mapping):
            raise BmcBuildError("solver must be a mapping.")
        if not isinstance(self.initial, Mapping):
            raise BmcBuildError("initial must be a mapping.")
        property_metadata = _coerce_public_json_mapping("property", self.property)
        solver_metadata = _coerce_public_json_mapping("solver", self.solver)
        initial_metadata = _coerce_public_json_mapping("initial", self.initial)
        _validate_witness_solver_metadata(solver_metadata)
        object.__setattr__(self, "property", property_metadata)
        object.__setattr__(self, "solver", solver_metadata)
        object.__setattr__(self, "initial", initial_metadata)
        object.__setattr__(
            self,
            "frames",
            _coerce_public_sequence(
                "frames", self.frames, BmcWitnessFrame, "BmcWitnessFrame objects"
            ),
        )
        object.__setattr__(
            self,
            "steps",
            _coerce_public_sequence(
                "steps", self.steps, BmcWitnessStep, "BmcWitnessStep objects"
            ),
        )
        object.__setattr__(
            self,
            "diagnostics",
            _coerce_public_sequence("diagnostics", self.diagnostics, str, "strings"),
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable witness dictionary.

        :return: Canonical witness.
        :rtype: Dict[str, object]

        Example::

            >>> trace = BmcWitnessTrace({'kind': 'reach'}, {'status': 'sat'}, {'mode': 'cold'}, (), ())
            >>> trace.to_canonical()['steps']
            []
        """
        solver_metadata = _coerce_public_json_mapping("solver", self.solver)
        _validate_witness_solver_metadata(solver_metadata)
        return {
            "schema_version": self.schema_version,
            "property": _coerce_public_json_mapping("property", self.property),
            "solver": solver_metadata,
            "initial": _coerce_public_json_mapping("initial", self.initial),
            "frames": [item.to_canonical() for item in self.frames],
            "steps": [item.to_canonical() for item in self.steps],
            "diagnostics": list(self.diagnostics),
        }


@dataclass(frozen=True)
class BmcRuntimeFrame(_PrettyPrintableMixin):
    """Runtime frame captured during witness replay.

    :param index: Frame index.
    :type index: int
    :param state: Runtime state path or ``None`` when terminated.
    :type state: str, optional
    :param terminated: Whether the runtime is ended.
    :type terminated: bool
    :param vars: Persistent runtime variables.
    :type vars: Mapping[str, object]
    :raises pyfcstm.bmc.errors.BmcBuildError: If the runtime-frame payload is
        malformed.

    Example::

        >>> BmcRuntimeFrame(0, 'Root', False, {}).to_canonical()['state']
        'Root'
    """

    index: int
    state: Optional[str]
    terminated: bool
    vars: Mapping[str, Any]

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise BmcBuildError("runtime frame index must be a non-negative integer.")
        if self.state is not None and (
            not isinstance(self.state, str) or not self.state
        ):
            raise BmcBuildError(
                "runtime frame state must be a non-empty string or None."
            )
        if not isinstance(self.terminated, bool):
            raise BmcBuildError("runtime frame terminated must be bool.")
        object.__setattr__(
            self,
            "vars",
            _coerce_public_value_mapping("runtime frame vars", self.vars),
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable runtime frame.

        :return: Canonical runtime frame.
        :rtype: Dict[str, object]

        Example::

            >>> BmcRuntimeFrame(0, None, True, {}).to_canonical()['terminated']
            True
        """
        return {
            "index": self.index,
            "state": self.state,
            "terminated": self.terminated,
            "vars": _canonical_public_value_mapping("runtime frame vars", self.vars),
        }


@dataclass(frozen=True)
class BmcRuntimeStep(_PrettyPrintableMixin):
    """Runtime step captured during witness replay.

    :param index: Step index.
    :type index: int
    :param input_events: Runtime input events.
    :type input_events: Sequence[str]
    :param consumed_events: Runtime consumed events.
    :type consumed_events: Sequence[str]
    :param unconsumed_events: Runtime unconsumed events.
    :type unconsumed_events: Sequence[str]
    :param abstract_calls: Handler call records captured in this step.
    :type abstract_calls: Sequence[BmcWitnessCallRecord]
    :param delta: Runtime Delta observation, defaults to ``False``.
    :type delta: bool, optional
    :param cycle_count_before: Runtime cycle count before the call, or ``None``
        for a synthetic terminated absorb step.
    :type cycle_count_before: int, optional
    :param cycle_count_after: Runtime cycle count after the call, or ``None``
        for a synthetic terminated absorb step.
    :type cycle_count_after: int, optional
    :param history_entry: Deep-copied five-field runtime history entry, or
        ``None`` when the step is synthetic or history retention is disabled.
    :type history_entry: Mapping[str, object], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the runtime-step payload is
        malformed.

    Example::

        >>> BmcRuntimeStep(0, (), (), (), ()).to_canonical()['delta']
        False
    """

    index: int
    input_events: Sequence[str]
    consumed_events: Sequence[str]
    unconsumed_events: Sequence[str]
    abstract_calls: Sequence[BmcWitnessCallRecord]
    delta: bool = False
    cycle_count_before: Optional[int] = None
    cycle_count_after: Optional[int] = None
    history_entry: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise BmcBuildError("runtime step index must be a non-negative integer.")
        if not isinstance(self.delta, bool):
            raise BmcBuildError("runtime step delta must be bool.")
        for field_name in ("cycle_count_before", "cycle_count_after"):
            value = getattr(self, field_name)
            if value is not None and (
                isinstance(value, bool) or not isinstance(value, int) or value < 0
            ):
                raise BmcBuildError(
                    "runtime step %s must be a non-negative integer or None."
                    % field_name
                )
        if (self.cycle_count_before is None) != (self.cycle_count_after is None):
            raise BmcBuildError(
                "runtime step cycle_count_before and cycle_count_after must both be set or None."
            )
        if self.history_entry is not None:
            object.__setattr__(
                self,
                "history_entry",
                copy.deepcopy(
                    _coerce_public_json_mapping(
                        "runtime step history_entry", self.history_entry
                    )
                ),
            )
        object.__setattr__(
            self,
            "input_events",
            _coerce_public_sequence("input_events", self.input_events, str, "strings"),
        )
        object.__setattr__(
            self,
            "consumed_events",
            _coerce_public_sequence(
                "consumed_events", self.consumed_events, str, "strings"
            ),
        )
        object.__setattr__(
            self,
            "unconsumed_events",
            _coerce_public_sequence(
                "unconsumed_events", self.unconsumed_events, str, "strings"
            ),
        )
        object.__setattr__(
            self,
            "abstract_calls",
            _coerce_public_sequence(
                "abstract_calls",
                self.abstract_calls,
                BmcWitnessCallRecord,
                "BmcWitnessCallRecord objects",
            ),
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable runtime step.

        :return: Canonical runtime step.
        :rtype: Dict[str, object]

        Example::

            >>> BmcRuntimeStep(0, (), (), (), ()).to_canonical()['input_events']
            []
        """
        return {
            "index": self.index,
            "input_events": list(self.input_events),
            "consumed_events": list(self.consumed_events),
            "unconsumed_events": list(self.unconsumed_events),
            "abstract_calls": [item.to_canonical() for item in self.abstract_calls],
            "delta": self.delta,
            "cycle_count_before": self.cycle_count_before,
            "cycle_count_after": self.cycle_count_after,
            "history_entry": (
                None
                if self.history_entry is None
                else _coerce_public_json_mapping(
                    "runtime step history_entry", self.history_entry
                )
            ),
        }


@dataclass(frozen=True)
class BmcRuntimeTrace(_PrettyPrintableMixin):
    """Runtime replay trace.

    :param frames: Runtime frames.
    :type frames: Sequence[BmcRuntimeFrame]
    :param steps: Runtime steps.
    :type steps: Sequence[BmcRuntimeStep]
    :raises pyfcstm.bmc.errors.BmcBuildError: If the runtime-trace payload is
        malformed.

    Example::

        >>> BmcRuntimeTrace((), ()).to_canonical()['frames']
        []
    """

    frames: Sequence[BmcRuntimeFrame]
    steps: Sequence[BmcRuntimeStep]

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "frames",
            _coerce_public_sequence(
                "runtime trace frames",
                self.frames,
                BmcRuntimeFrame,
                "BmcRuntimeFrame objects",
            ),
        )
        object.__setattr__(
            self,
            "steps",
            _coerce_public_sequence(
                "runtime trace steps",
                self.steps,
                BmcRuntimeStep,
                "BmcRuntimeStep objects",
            ),
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable runtime trace.

        :return: Canonical runtime trace.
        :rtype: Dict[str, object]

        Example::

            >>> BmcRuntimeTrace((), ()).to_canonical()['steps']
            []
        """
        return {
            "frames": [item.to_canonical() for item in self.frames],
            "steps": [item.to_canonical() for item in self.steps],
        }


@dataclass(frozen=True)
class BmcReplayMismatch(_PrettyPrintableMixin):
    """Structured replay mismatch.

    :param path: Dotted or indexed mismatch path.
    :type path: str
    :param expected: Expected value from the witness.
    :type expected: object
    :param actual: Actual value observed from runtime replay.
    :type actual: object
    :param message: Human-readable mismatch summary.
    :type message: str
    :param tolerance: Float tolerance used for comparison, defaults to ``None``.
    :type tolerance: float, optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the mismatch payload is
        malformed.

    Example::

        >>> BmcReplayMismatch('frames[1].state', 'A', 'B', 'state mismatch').path
        'frames[1].state'
    """

    path: str
    expected: Any
    actual: Any
    message: str
    tolerance: Optional[float] = None

    def __post_init__(self) -> None:
        if not isinstance(self.path, str) or not self.path:
            raise BmcBuildError("mismatch path must be a non-empty string.")
        if not isinstance(self.message, str) or not self.message:
            raise BmcBuildError("mismatch message must be a non-empty string.")
        if self.tolerance is not None and (
            isinstance(self.tolerance, bool)
            or not isinstance(self.tolerance, (int, float))
            or self.tolerance < 0
            or not math.isfinite(float(self.tolerance))
        ):
            raise BmcBuildError(
                "mismatch tolerance must be a finite non-negative number or None."
            )
        object.__setattr__(
            self,
            "expected",
            _coerce_public_json_value("mismatch expected", self.expected),
        )
        object.__setattr__(
            self, "actual", _coerce_public_json_value("mismatch actual", self.actual)
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable mismatch dictionary.

        :return: Canonical mismatch.
        :rtype: Dict[str, object]

        Example::

            >>> BmcReplayMismatch('x', 1, 2, 'bad').to_canonical()['actual']
            2
        """
        return {
            "path": self.path,
            "expected": _coerce_public_json_value("mismatch expected", self.expected),
            "actual": _coerce_public_json_value("mismatch actual", self.actual),
            "message": self.message,
            "tolerance": self.tolerance,
        }


@dataclass(frozen=True)
class BmcReplayResult(_PrettyPrintableMixin):
    """Result of replaying a BMC witness through ``SimulationRuntime``.

    :param witness: Witness that was replayed.
    :type witness: BmcWitnessTrace
    :param runtime_trace: Captured runtime trace.
    :type runtime_trace: BmcRuntimeTrace
    :param mismatches: Structured replay mismatches, defaults to ``()``.
    :type mismatches: Sequence[BmcReplayMismatch], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the replay result payload is
        malformed.

    Example::

        >>> trace = BmcWitnessTrace({'kind': 'reach'}, {'status': 'sat'}, {'mode': 'cold'}, (), ())
        >>> BmcReplayResult(trace, BmcRuntimeTrace((), ())).ok
        True
    """

    witness: BmcWitnessTrace
    runtime_trace: BmcRuntimeTrace
    mismatches: Sequence[BmcReplayMismatch] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.witness, BmcWitnessTrace):
            raise BmcBuildError("witness must be BmcWitnessTrace.")
        if not isinstance(self.runtime_trace, BmcRuntimeTrace):
            raise BmcBuildError("runtime_trace must be BmcRuntimeTrace.")
        object.__setattr__(
            self,
            "mismatches",
            _coerce_public_sequence(
                "mismatches",
                self.mismatches,
                BmcReplayMismatch,
                "BmcReplayMismatch objects",
            ),
        )

    @property
    def ok(self) -> bool:
        """Return whether replay had no mismatches.

        :return: ``True`` when replay matched the witness.
        :rtype: bool

        Example::

            >>> trace = BmcWitnessTrace({'kind': 'reach'}, {'status': 'sat'}, {'mode': 'cold'}, (), ())
            >>> BmcReplayResult(trace, BmcRuntimeTrace((), ())).ok
            True
        """
        return not self.mismatches

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable replay result.

        :return: Canonical replay result.
        :rtype: Dict[str, object]

        Example::

            >>> trace = BmcWitnessTrace({'kind': 'reach'}, {'status': 'sat'}, {'mode': 'cold'}, (), ())
            >>> BmcReplayResult(trace, BmcRuntimeTrace((), ())).to_canonical()['ok']
            True
        """
        return {
            "ok": self.ok,
            "runtime_trace": self.runtime_trace.to_canonical(),
            "mismatches": [item.to_canonical() for item in self.mismatches],
        }


class _HandlerCallRecorder:
    def __init__(self, role_resolver: "_AbstractCallRoleResolver") -> None:
        self.role_resolver = role_resolver
        self.calls: list[BmcWitnessCallRecord] = []
        self._context_call_counts: Dict[Tuple[str, str, str], int] = {}

    def begin_step(self) -> None:
        self._context_call_counts = {}

    def end_step(self) -> None:
        self._context_call_counts = {}

    def handler(self, ctx: ReadOnlyExecutionContext) -> None:
        key = self.role_resolver.context_key(ctx)
        occurrence_index = self._context_call_counts.get(key, 0)
        self._context_call_counts[key] = occurrence_index + 1
        role = self.role_resolver.resolve(ctx, occurrence_index)
        self.calls.append(
            BmcWitnessCallRecord(
                ordinal=len(self.calls),
                action_name=ctx.abstract_target or ctx.action_name,
                stage=ctx.call_stage or ctx.action_stage,
                role=role,
                state=ctx.get_full_state_path(),
                active_leaf=".".join(ctx.active_leaf or ctx.state_path),
                named_ref=ctx.named_ref,
                snapshot=dict(ctx.vars),
            )
        )


class _AbstractCallRoleResolver:
    def __init__(
        self,
        named_roles: Mapping[str, str],
        context_roles: Mapping[Tuple[str, str, str], Sequence[str]],
    ) -> None:
        self.named_roles = dict(named_roles)
        self.context_roles = {
            key: tuple(values) for key, values in context_roles.items()
        }

    def context_key(self, ctx: ReadOnlyExecutionContext) -> Tuple[str, str, str]:
        return (
            ctx.abstract_target or ctx.action_name,
            ctx.call_stage or ctx.action_stage,
            ctx.get_full_state_path(),
        )

    def resolve(self, ctx: ReadOnlyExecutionContext, occurrence_index: int = 0) -> str:
        if ctx.named_ref is not None:
            return self._named_role(ctx.named_ref)
        key = self.context_key(ctx)
        if key in self.context_roles:
            candidates = self.context_roles[key]
            if occurrence_index < len(candidates):
                return candidates[occurrence_index]
            raise _internal_error(
                "Runtime abstract call %r at %s exceeded replay role metadata: %r."
                % (key[0], key[2], candidates)
            )
        return self._named_role(key[0])

    def _named_role(self, action_name: str) -> str:
        try:
            return self.named_roles[action_name]
        except KeyError as err:
            # KeyError: every named abstract call observed from the runtime
            # should have a matching model action, ref callsite, or contextual
            # unnamed-ref entry. Missing entries indicate that witness replay
            # can no longer independently classify the call role.
            raise _internal_error(
                "Runtime abstract call %r has no replay role metadata." % action_name
            ) from err


def _iter_actions(state_machine: StateMachine) -> Iterable[object]:
    for state in state_machine.walk_states():
        for attr_name in (
            "on_enters",
            "on_durings",
            "on_exits",
            "on_during_aspects",
        ):
            for action in getattr(state, attr_name, ()) or ():
                yield action


def _role_for_action(action: object) -> Optional[str]:
    if isinstance(action, OnAspect):
        if action.stage == "during" and action.aspect == "before":
            return "aspect_during_before"
        if action.stage == "during" and action.aspect == "after":
            return "aspect_during_after"
        raise _internal_error(
            "Unsupported aspect action role for %s." % action.func_name
        )
    if isinstance(action, OnStage):
        if action.stage == "enter":
            return "state_enter"
        if action.stage == "exit":
            return "state_exit"
        if action.stage == "during" and action.aspect == "before":
            return "plain_during_before"
        if action.stage == "during" and action.aspect == "after":
            return "plain_during_after"
        if action.stage == "during":
            return "leaf_during"
        raise _internal_error(
            "Unsupported stage action role for %s." % action.func_name
        )
    return None


def _resolved_abstract_target(action: object) -> Optional[str]:
    current = action
    seen_ids = set()
    while getattr(current, "ref", None) is not None:
        current_id = id(current)
        if current_id in seen_ids:
            return None
        seen_ids.add(current_id)
        current = current.ref
    if (
        getattr(current, "is_abstract", False)
        and getattr(current, "name", None) is not None
    ):
        return current.func_name
    return None


def _runtime_state_paths_for_action(action: object) -> Tuple[str, ...]:
    parent = getattr(action, "parent", None)
    if parent is None:
        raise _internal_error("Lifecycle action %r has no parent state." % action)
    return (".".join(parent.path),)


def _record_context_role(
    context_roles: Dict[Tuple[str, str, str], list[str]],
    action: object,
    role: Optional[str],
    state_path: str,
) -> None:
    if role is None:
        return
    target = _resolved_abstract_target(action)
    if target is None:
        return
    stage = getattr(action, "stage", None)
    if not isinstance(stage, str):
        raise _internal_error("Lifecycle action %r has no call stage." % action)
    context_roles.setdefault((target, stage, state_path), []).append(role)


def _abstract_call_role_resolver(
    state_machine: StateMachine,
) -> _AbstractCallRoleResolver:
    named_roles = {}
    context_roles: Dict[Tuple[str, str, str], list[str]] = {}
    for action in _iter_actions(state_machine):
        role = _role_for_action(action)
        if role is None:
            continue
        if getattr(action, "name", None) is not None:
            named_roles[action.func_name] = role
        target = _resolved_abstract_target(action)
        if target is not None and getattr(action, "ref", None) is None:
            named_roles.setdefault(target, role)
    for state in state_machine.walk_states():
        if getattr(state, "is_leaf_state", False) and not getattr(
            state, "is_pseudo", False
        ):
            leaf_path = ".".join(state.path)
            for _, action in state.iter_on_during_aspect_recursively():
                _record_context_role(
                    context_roles,
                    action,
                    _role_for_action(action),
                    leaf_path,
                )
    for action in _iter_actions(state_machine):
        if isinstance(action, OnAspect):
            continue
        role = _role_for_action(action)
        if role is None:
            continue
        parent = getattr(action, "parent", None)
        stage = getattr(action, "stage", None)
        aspect = getattr(action, "aspect", None)
        if (
            stage in {"enter", "exit"}
            or aspect in {"before", "after"}
            or (
                stage == "during"
                and parent is not None
                and not getattr(parent, "is_leaf_state", False)
            )
        ):
            for state_path in _runtime_state_paths_for_action(action):
                _record_context_role(context_roles, action, role, state_path)
    return _AbstractCallRoleResolver(named_roles, context_roles)


def _abstract_action_role_map(state_machine: StateMachine) -> Mapping[str, str]:
    return _abstract_call_role_resolver(state_machine).named_roles


def _iter_resolved_abstract_action_paths(
    state_machine: StateMachine,
) -> Tuple[str, ...]:
    paths = set()
    for action in _iter_actions(state_machine):
        current = action
        seen_ids = set()
        while getattr(current, "ref", None) is not None:
            current_id = id(current)
            if current_id in seen_ids:
                break
            seen_ids.add(current_id)
            current = current.ref
        if (
            getattr(current, "is_abstract", False)
            and getattr(current, "name", None) is not None
        ):
            paths.add(current.func_name)
    return tuple(sorted(paths))


def _register_recorder(
    runtime: SimulationRuntime,
    recorder: _HandlerCallRecorder,
    abstract_handlers: Optional[
        Mapping[str, Callable[[ReadOnlyExecutionContext], None]]
    ],
) -> None:
    handlers = abstract_handlers or {}
    action_paths = _iter_resolved_abstract_action_paths(runtime.state_machine)
    known_paths = set(action_paths)
    unknown_paths = sorted(set(handlers) - known_paths)
    if unknown_paths:
        raise BmcBuildError(
            "abstract_handlers contains unknown abstract action paths: %s."
            % ", ".join(unknown_paths)
        )
    non_callable_paths = sorted(
        path for path, handler in handlers.items() if not callable(handler)
    )
    if non_callable_paths:
        raise BmcBuildError(
            "abstract_handlers contains non-callable handlers for: %s."
            % ", ".join(non_callable_paths)
        )
    for action_path in action_paths:
        user_handler = handlers.get(action_path)
        if user_handler is None:
            runtime.register_abstract_handler(action_path, recorder.handler)
        else:

            def wrapper(ctx: ReadOnlyExecutionContext, handler=user_handler) -> None:
                recorder.handler(ctx)
                handler(ctx)

            runtime.register_abstract_handler(action_path, wrapper)


def solve_bmc_property(
    formula: BmcPropertyFormula,
    *,
    timeout_ms: Optional[int] = None,
    check_incomplete: bool = True,
) -> BmcSolveResult:
    """Solve a compiled BMC property formula.

    The primary status always comes from :attr:`BmcPropertyFormula.solve_formula`.
    When ``check_incomplete`` is true and the formula has a non-false
    incomplete-bound observation, the incomplete formula is solved separately
    and reported without changing the primary status.

    :param formula: Compiled BMC property formula.
    :type formula: pyfcstm.bmc.properties.BmcPropertyFormula
    :param timeout_ms: Optional Z3 timeout in milliseconds, defaults to
        ``None``.
    :type timeout_ms: int, optional
    :param check_incomplete: Whether to solve incomplete-bound diagnostics,
        defaults to ``True``.
    :type check_incomplete: bool, optional
    :return: Structured solve result.
    :rtype: BmcSolveResult
    :raises pyfcstm.bmc.errors.BmcBuildError: If arguments are malformed.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> sm = load_state_machine_from_text('state Root;')
        >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
        >>> solve_bmc_property(formula).status
        'sat'
    """
    checked = _require_formula(formula)
    if not isinstance(check_incomplete, bool):
        raise BmcBuildError("check_incomplete must be bool.")
    status, model, reason, elapsed_ms = _solve(checked.solve_formula, timeout_ms)
    incomplete_status = None
    incomplete_model = None
    incomplete_reason = None
    diagnostics = list(checked.diagnostics)
    if check_incomplete and not z3.is_false(checked.incomplete_formula):
        (
            incomplete_status,
            incomplete_model,
            incomplete_reason,
            incomplete_elapsed_ms,
        ) = _solve(checked.incomplete_solve_formula, timeout_ms)
        diagnostics.append("incomplete_elapsed_ms=%.3f" % incomplete_elapsed_ms)
    elif not check_incomplete and not z3.is_false(checked.incomplete_formula):
        incomplete_reason = "incomplete check disabled"
        diagnostics.append("incomplete_check=disabled")
    return BmcSolveResult(
        formula=checked,
        status=status,
        model=model,
        reason=reason,
        elapsed_ms=elapsed_ms,
        timeout_ms=timeout_ms,
        incomplete_status=incomplete_status,
        incomplete_model=incomplete_model,
        incomplete_reason=incomplete_reason,
        diagnostics=tuple(diagnostics),
    )


def _frame_for_index(
    formula: BmcPropertyFormula, model: z3.ModelRef, index: int
) -> BmcWitnessFrame:
    core = formula.core
    state_id = _z3_int_value(model, core.symbols.frame_state(index))
    variables = {}
    for var in core.context.domain.variables:
        variables[var.name] = _z3_number_value(
            model, core.symbols.frame_var(index, var.name), var.declared_type
        )
    if state_id == STATE_INIT_ID:
        return BmcWitnessFrame(index, None, None, "init", False, variables)
    if state_id == STATE_TERMINATE_ID:
        return BmcWitnessFrame(index, None, None, "terminated", True, variables)
    entry = core.context.domain.state_by_id(state_id)
    return BmcWitnessFrame(index, state_id, entry.path, None, False, variables)


def _selected_relation(
    model: z3.ModelRef, relations: Sequence[BmcCaseRelation], step_index: int
) -> BmcCaseRelation:
    selected = [item for item in relations if _z3_bool_value(model, item.selector)]
    if len(selected) != 1:
        raise _internal_error(
            "Expected exactly one selected case at step %d, got %d."
            % (step_index, len(selected))
        )
    return selected[0]


def _event_model_value(
    formula: BmcPropertyFormula, model: z3.ModelRef, step: int, path: str
) -> bool:
    return _z3_bool_value(model, formula.core.symbols.event_input(step, path))


def _case_positive_events(
    formula: BmcPropertyFormula, model: z3.ModelRef, relation: BmcCaseRelation
) -> Tuple[BmcWitnessEvent, ...]:
    result = []
    for use in relation.case.used_events:
        if use.polarity == "positive" and _event_model_value(
            formula, model, relation.step_index, use.path
        ):
            result.append(BmcWitnessEvent(use.path, "case_positive", True))
    return tuple(result)


def _debug_event_reads(
    formula: BmcPropertyFormula, model: z3.ModelRef, relation: BmcCaseRelation
) -> Tuple[BmcWitnessEvent, ...]:
    result = []
    for use in sorted(
        relation.case.used_events,
        key=lambda item: (item.event_id, item.path, item.reason),
    ):
        if use.polarity == "negative":
            result.append(
                BmcWitnessEvent(
                    use.path,
                    "negative_case_read",
                    _event_model_value(formula, model, relation.step_index, use.path),
                )
            )
    return tuple(result)


def _explicit_assumption_events(
    formula: BmcPropertyFormula, model: z3.ModelRef, step_index: int
) -> Tuple[Tuple[BmcWitnessEvent, ...], Tuple[BmcWitnessEvent, ...]]:
    inputs = []
    reads = []
    for assumption in formula.core.context.bound_query.assumptions:
        if not isinstance(assumption, BoundAssumption) or assumption.kind != "event":
            continue
        if step_index not in assumption.cycles:
            continue
        source = assumption.source
        if not isinstance(source, EventAssumption):
            continue
        for event_id in assumption.resolved_event_ids:
            path = formula.core.context.domain.event_id_to_path(event_id)
            model_value = _event_model_value(formula, model, step_index, path)
            if source.expected:
                inputs.append(
                    BmcWitnessEvent(path, "explicit_true_assumption", model_value)
                )
            else:
                reads.append(
                    BmcWitnessEvent(path, "explicit_false_assumption", model_value)
                )
    return tuple(inputs), tuple(reads)


def _collect_event_atoms(expr: object) -> Tuple[Event, ...]:
    atoms = []
    if isinstance(expr, Event):
        atoms.append(expr)
    elif isinstance(expr, CondUnaryOp):
        atoms.extend(_collect_event_atoms(expr.operand))
    elif isinstance(expr, CondBinaryOp):
        atoms.extend(_collect_event_atoms(expr.left))
        atoms.extend(_collect_event_atoms(expr.right))
    elif isinstance(expr, CondConditionalOp):
        atoms.extend(_collect_event_atoms(expr.condition))
        atoms.extend(_collect_event_atoms(expr.if_true))
        atoms.extend(_collect_event_atoms(expr.if_false))
    elif isinstance(expr, NumericComparison):
        return ()
    elif isinstance(expr, (BoolLiteral, Active, Terminated, Called)):
        return ()
    return tuple(atoms)


def _response_trigger_event_paths(formula: BmcPropertyFormula) -> Tuple[str, ...]:
    if formula.kind != "response":
        return ()
    trigger = formula.core.context.bound_query.property.source.trigger
    paths = []
    for atom in _collect_event_atoms(trigger):
        if atom.selector != "current":
            # Response replay can only synthesize current-cycle input events.
            # Events bound to other selectors are properties of other frames or
            # steps and must already be satisfied by the fixed witness trace.
            continue
        # Binding has already resolved the path against the domain. Re-look it
        # up here so typo-like forged objects fail loudly instead of entering
        # the witness as a short-name event.
        entry = formula.core.context.domain.event_by_path(atom.event_path)
        paths.append(entry.path)
    return tuple(dict.fromkeys(paths))


def _response_trigger_is_true_under_events(
    formula: BmcPropertyFormula,
    model: z3.ModelRef,
    step_index: int,
    true_event_paths: Iterable[str],
) -> bool:
    if formula.kind != "response":
        return False
    trigger = formula.core.context.bound_query.property.source.trigger
    if trigger is None:  # pragma: no cover - BmcProperty validates response shape.
        raise _internal_error("response property is missing a trigger predicate.")
    lowered = _lower_predicate(
        formula.core,
        trigger,
        frame_index=step_index,
        step_index=step_index,
        context="response_trigger",
        path="property.trigger",
    )
    selected_paths = set(true_event_paths)
    substitutions = tuple(
        (
            formula.core.symbols.event_input(step_index, path),
            z3.BoolVal(path in selected_paths),
        )
        for path in _response_trigger_event_paths(formula)
    )
    value = lowered.good
    if substitutions:
        value = z3.substitute(value, *substitutions)
    return _z3_bool_value(model, value)


def _property_support_events(
    formula: BmcPropertyFormula,
    model: z3.ModelRef,
    step_index: int,
    existing_paths: Iterable[str],
    event_policy: BmcEventDecodePolicy,
) -> Tuple[BmcWitnessEvent, ...]:
    if formula.kind != "response":
        return ()
    model_true_paths = tuple(
        path
        for path in _response_trigger_event_paths(formula)
        if _event_model_value(formula, model, step_index, path)
    )
    if not _response_trigger_is_true_under_events(
        formula, model, step_index, model_true_paths
    ):
        return ()
    existing = set(existing_paths)
    if _response_trigger_is_true_under_events(formula, model, step_index, existing):
        return ()
    if not event_policy.include_property_support:
        raise BmcBuildError(
            "Response witness replay requires property-support events at step %d, "
            "but include_property_support is false." % step_index
        )
    event_order = {
        entry.path: index
        for index, entry in enumerate(formula.core.context.domain.events)
    }
    candidates = sorted(
        (
            path
            for path in _response_trigger_event_paths(formula)
            if path not in existing
            and _event_model_value(formula, model, step_index, path)
        ),
        key=lambda path: event_order[path],
    )
    support = []
    selected = set(existing)
    for path in candidates:
        selected.add(path)
        support.append(BmcWitnessEvent(path, "property_support", True))
        if _response_trigger_is_true_under_events(formula, model, step_index, selected):
            return tuple(support)
    raise _internal_error(  # pragma: no cover - guarded by the full-model precheck.
        "Response trigger remained false after adding all true support events "
        "at step %d." % step_index
    )


def _event_inputs_for_step(
    formula: BmcPropertyFormula,
    model: z3.ModelRef,
    relation: BmcCaseRelation,
    event_policy: BmcEventDecodePolicy,
) -> Tuple[Tuple[BmcWitnessEvent, ...], Tuple[BmcWitnessEvent, ...]]:
    case_events = _case_positive_events(formula, model, relation)
    assumption_events, assumption_reads = _explicit_assumption_events(
        formula, model, relation.step_index
    )
    replay_inputs = _merge_event_reasons(assumption_events + case_events)
    support_events = _property_support_events(
        formula,
        model,
        relation.step_index,
        (item.path for item in replay_inputs),
        event_policy,
    )
    inputs = _merge_event_reasons(replay_inputs + support_events)
    if event_policy.include_debug_reads:
        reads = _merge_event_reasons(
            _debug_event_reads(formula, model, relation) + assumption_reads
        )
    else:
        reads = ()
    return inputs, reads


def _progress_for(relation: BmcCaseRelation, delta: bool, gamma: bool) -> str:
    if delta or relation.case.kind == "delta":
        return "semantic_delta"
    if gamma and relation.case.kind == "fallback":
        return "fallback_gamma"
    if relation.case.kind == "absorb":
        return "terminated_absorb"
    if relation.case.kind == "initial":
        return "initial"
    if relation.case.kind == "transition":
        return "transition"
    return relation.case.kind


def _decode_calls(
    formula: BmcPropertyFormula, model: z3.ModelRef, relation: BmcCaseRelation
) -> Tuple[BmcWitnessCallRecord, ...]:
    variable_types = {
        variable.name: variable.declared_type
        for variable in formula.core.context.domain.variables
    }
    calls = []
    for record in relation.call_records:
        snapshot = {
            name: _z3_number_value(model, expr, variable_types.get(name))
            for name, expr in sorted(record.snapshot.items())
        }
        calls.append(
            BmcWitnessCallRecord(
                ordinal=record.ordinal,
                action_name=record.action_name,
                stage=record.stage,
                role=record.role,
                state=record.state_path,
                active_leaf=record.active_leaf_path,
                named_ref=record.named_ref,
                snapshot=snapshot,
            )
        )
    return tuple(calls)


def _decode_step(
    formula: BmcPropertyFormula,
    model: z3.ModelRef,
    step_index: int,
    frames: Sequence[BmcWitnessFrame],
    event_policy: BmcEventDecodePolicy,
) -> BmcWitnessStep:
    step_relation = formula.core.steps[step_index]
    relation = _selected_relation(model, step_relation.case_relations, step_index)
    delta = _z3_bool_value(model, formula.core.symbols.delta_flag(step_index))
    gamma = _z3_bool_value(model, formula.core.symbols.gamma_flag(step_index))
    input_events, event_reads = _event_inputs_for_step(
        formula, model, relation, event_policy
    )
    consumed_events = tuple(relation.case.consumed_events)
    unconsumed_events = _unconsumed_event_paths(
        tuple(item.path for item in input_events), consumed_events
    )
    source = frames[step_index]
    target = frames[step_index + 1]
    return BmcWitnessStep(
        index=step_index,
        source_frame=step_index,
        target_frame=step_index + 1,
        case_label=relation.case.label,
        case_kind=relation.case.kind,
        progress=_progress_for(relation, delta, gamma),
        source_state=source.state,
        target_state=target.state,
        delta=delta,
        gamma=gamma,
        input_events=input_events,
        event_reads=event_reads,
        abstract_calls=_decode_calls(formula, model, relation),
        consumed_events=consumed_events,
        unconsumed_events=unconsumed_events,
    )


def _initial_metadata(
    formula: BmcPropertyFormula, frames: Sequence[BmcWitnessFrame]
) -> _CanonicalDict:
    initial = formula.core.context.bound_query.initial.source
    if not frames:
        raise _internal_error("Decoded witness trace has no frames.")
    first = frames[0]
    return {
        "mode": initial.mode,
        "state": first.state,
        "sentinel": first.sentinel,
        "vars": dict(sorted(first.vars.items())),
    }


def decode_bmc_witness(
    formula: BmcPropertyFormula,
    model: z3.ModelRef,
    *,
    event_policy: Optional[BmcEventDecodePolicy] = None,
) -> BmcWitnessTrace:
    """Decode a SAT model into a macro-step witness trace.

    The decoder consumes selected case relations and trace symbols produced by
    earlier BMC layers.  It does not re-expand macro paths, and it intentionally
    emits only sparse replay input events instead of every true event Boolean in
    the Z3 model.

    :param formula: Compiled BMC property formula whose solve formula was SAT.
    :type formula: pyfcstm.bmc.properties.BmcPropertyFormula
    :param model: Z3 model returned for ``formula.solve_formula``.
    :type model: z3.ModelRef
    :param event_policy: Optional sparse event decode policy, defaults to
        ``None`` which uses :class:`BmcEventDecodePolicy`.
    :type event_policy: BmcEventDecodePolicy, optional
    :return: Decoded witness trace.
    :rtype: BmcWitnessTrace
    :raises pyfcstm.bmc.errors.BmcBuildError: If inputs are malformed or the
        model violates internal witness consistency assumptions.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
        >>> from pyfcstm.bmc.witness import solve_bmc_property, decode_bmc_witness
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> sm = load_state_machine_from_text('state Root;')
        >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
        >>> result = solve_bmc_property(formula)
        >>> decode_bmc_witness(formula, result.model).frames[0].sentinel
        'init'
    """
    checked = _require_formula(formula)
    checked_model = _require_model(model)
    if event_policy is None:
        event_policy = BmcEventDecodePolicy()
    elif not isinstance(event_policy, BmcEventDecodePolicy):
        raise BmcBuildError("event_policy must be BmcEventDecodePolicy or None.")
    frames = tuple(
        _frame_for_index(checked, checked_model, frame.index)
        for frame in checked.core.context.domain.frames
    )
    steps = tuple(
        _decode_step(checked, checked_model, step.index, frames, event_policy)
        for step in checked.core.context.domain.steps
    )
    solver = {
        "status": "sat",
        "reason": None,
        "incomplete_status": None,
    }
    prop = {
        "kind": checked.kind,
        "polarity": checked.polarity,
        "bound": checked.bound,
        "case_label": checked.case_label,
        "response_window": checked.response_window,
    }
    return BmcWitnessTrace(
        property=prop,
        solver=solver,
        initial=_initial_metadata(checked, frames),
        frames=frames,
        steps=steps,
        diagnostics=checked.diagnostics,
    )


def _runtime_state(runtime: SimulationRuntime) -> Optional[str]:
    if runtime.is_ended:
        return None
    return ".".join(runtime.current_state.path)


def _runtime_frame(runtime: SimulationRuntime, index: int) -> BmcRuntimeFrame:
    return BmcRuntimeFrame(
        index=index,
        state=_runtime_state(runtime),
        terminated=runtime.is_ended,
        vars=dict(runtime.vars),
    )


def _compare_values(
    mismatches: list[BmcReplayMismatch], path: str, expected: Any, actual: Any
) -> None:
    if isinstance(expected, bool) or isinstance(actual, bool):
        if not isinstance(expected, bool) or not isinstance(actual, bool):
            mismatches.append(
                BmcReplayMismatch(path, expected, actual, "value type mismatch")
            )
        elif expected != actual:
            mismatches.append(
                BmcReplayMismatch(path, expected, actual, "value mismatch")
            )
        return
    expected_is_number = isinstance(expected, (int, float))
    actual_is_number = isinstance(actual, (int, float))
    if expected_is_number or actual_is_number:
        if not _is_public_finite_number(expected) or not _is_public_finite_number(
            actual
        ):
            mismatches.append(
                BmcReplayMismatch(
                    path,
                    _public_mismatch_diagnostic_value(expected),
                    _public_mismatch_diagnostic_value(actual),
                    "numeric value mismatch",
                )
            )
            return
        if isinstance(expected, float) or isinstance(actual, float):
            expected_fraction = (
                Fraction.from_float(expected)
                if isinstance(expected, float)
                else Fraction(expected)
            )
            actual_fraction = (
                Fraction.from_float(actual)
                if isinstance(actual, float)
                else Fraction(actual)
            )
            if abs(expected_fraction - actual_fraction) > Fraction.from_float(
                _REPLAY_FLOAT_TOLERANCE
            ):
                mismatches.append(
                    BmcReplayMismatch(
                        path,
                        expected,
                        actual,
                        "float value mismatch",
                        _REPLAY_FLOAT_TOLERANCE,
                    )
                )
            return
        if expected != actual:
            mismatches.append(
                BmcReplayMismatch(path, expected, actual, "value mismatch")
            )
        return
    if type(expected) is not type(actual):
        mismatches.append(
            BmcReplayMismatch(path, expected, actual, "value type mismatch")
        )
        return
    if expected != actual:
        mismatches.append(BmcReplayMismatch(path, expected, actual, "value mismatch"))


def _compare_mapping_keys(
    mismatches: list[BmcReplayMismatch],
    path: str,
    expected: Mapping[str, Any],
    actual: Mapping[str, Any],
    message: str,
) -> Tuple[str, ...]:
    expected_keys = set(expected)
    actual_keys = set(actual)
    if expected_keys != actual_keys:
        mismatches.append(
            BmcReplayMismatch(
                path,
                tuple(sorted(expected_keys)),
                tuple(sorted(actual_keys)),
                message,
            )
        )
    return tuple(sorted(expected_keys & actual_keys))


def _compare_frame(
    mismatches: list[BmcReplayMismatch],
    witness: BmcWitnessFrame,
    runtime: BmcRuntimeFrame,
    init_runtime_state: Optional[str] = None,
) -> None:
    common_var_names = _compare_mapping_keys(
        mismatches,
        "frames[%d].vars" % witness.index,
        witness.vars,
        runtime.vars,
        "variable key set mismatch",
    )
    if witness.sentinel == "init":
        if init_runtime_state != runtime.state:
            mismatches.append(
                BmcReplayMismatch(
                    "frames[%d].state" % witness.index,
                    init_runtime_state,
                    runtime.state,
                    "init sentinel state mismatch",
                )
            )
        if runtime.terminated:
            mismatches.append(
                BmcReplayMismatch(
                    "frames[%d].terminated" % witness.index,
                    False,
                    runtime.terminated,
                    "init sentinel terminated mismatch",
                )
            )
        for name in common_var_names:
            _compare_values(
                mismatches,
                "frames[%d].vars.%s" % (witness.index, name),
                witness.vars[name],
                runtime.vars[name],
            )
        return
    expected_state = None if witness.terminated else witness.state
    if expected_state != runtime.state:
        mismatches.append(
            BmcReplayMismatch(
                "frames[%d].state" % witness.index,
                expected_state,
                runtime.state,
                "state mismatch",
            )
        )
    if witness.terminated != runtime.terminated:
        mismatches.append(
            BmcReplayMismatch(
                "frames[%d].terminated" % witness.index,
                witness.terminated,
                runtime.terminated,
                "terminated mismatch",
            )
        )
    for name in common_var_names:
        _compare_values(
            mismatches,
            "frames[%d].vars.%s" % (witness.index, name),
            witness.vars[name],
            runtime.vars[name],
        )


def _compare_calls(
    mismatches: list[BmcReplayMismatch],
    index: int,
    expected: Sequence[BmcWitnessCallRecord],
    actual: Sequence[BmcWitnessCallRecord],
) -> None:
    if len(expected) != len(actual):
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].abstract_calls" % index,
                len(expected),
                len(actual),
                "abstract call count mismatch",
            )
        )
        return
    for call_index, (left, right) in enumerate(zip(expected, actual)):
        left_canon = left.to_canonical()
        right_canon = right.to_canonical()
        for key in (
            "action_name",
            "stage",
            "role",
            "state",
            "active_leaf",
            "named_ref",
        ):
            if left_canon[key] != right_canon[key]:
                mismatches.append(
                    BmcReplayMismatch(
                        "steps[%d].abstract_calls[%d].%s" % (index, call_index, key),
                        left_canon[key],
                        right_canon[key],
                        "abstract call metadata mismatch",
                    )
                )
        common_snapshot_names = _compare_mapping_keys(
            mismatches,
            "steps[%d].abstract_calls[%d].snapshot" % (index, call_index),
            left.snapshot,
            right.snapshot,
            "abstract call snapshot key set mismatch",
        )
        for name in common_snapshot_names:
            _compare_values(
                mismatches,
                "steps[%d].abstract_calls[%d].snapshot.%s" % (index, call_index, name),
                left.snapshot[name],
                right.snapshot[name],
            )


def _compare_history_entry(
    mismatches: list[BmcReplayMismatch],
    index: int,
    expected: Optional[Mapping[str, Any]],
    actual: Optional[Mapping[str, Any]],
) -> None:
    path = "steps[%d].history_entry" % index
    if expected is None or actual is None:
        if expected != actual:
            mismatches.append(
                BmcReplayMismatch(path, expected, actual, "history entry presence mismatch")
            )
        return
    common_keys = _compare_mapping_keys(
        mismatches,
        path,
        expected,
        actual,
        "history entry key set mismatch",
    )
    for key in common_keys:
        value_path = "%s.%s" % (path, key)
        if isinstance(expected[key], Mapping) and isinstance(actual[key], Mapping):
            common_var_names = _compare_mapping_keys(
                mismatches,
                value_path,
                expected[key],
                actual[key],
                "history entry mapping key set mismatch",
            )
            for name in common_var_names:
                _compare_values(
                    mismatches,
                    "%s.%s" % (value_path, name),
                    expected[key][name],
                    actual[key][name],
                )
        else:
            _compare_values(mismatches, value_path, expected[key], actual[key])


def _compare_step(
    mismatches: list[BmcReplayMismatch],
    witness: BmcWitnessStep,
    runtime: BmcRuntimeStep,
    expected_history: object = _MISSING_REPLAY_OBSERVATION,
) -> None:
    is_absorb = witness.case_kind == "absorb"
    expected_delta = False if is_absorb else witness.delta
    if expected_delta != runtime.delta:
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].delta" % witness.index,
                expected_delta,
                runtime.delta,
                "delta mismatch",
            )
        )
    expected_before = None if is_absorb else witness.index
    expected_after = None if is_absorb else witness.index + 1
    if expected_before != runtime.cycle_count_before:
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].cycle_count_before" % witness.index,
                expected_before,
                runtime.cycle_count_before,
                "cycle count before mismatch",
            )
        )
    if expected_after != runtime.cycle_count_after:
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].cycle_count_after" % witness.index,
                expected_after,
                runtime.cycle_count_after,
                "cycle count after mismatch",
            )
        )
    if expected_history is not _MISSING_REPLAY_OBSERVATION:
        _compare_history_entry(
            mismatches,
            witness.index,
            expected_history,
            runtime.history_entry,
        )
    if tuple(witness.input_event_paths) != tuple(runtime.input_events):
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].input_events" % witness.index,
                tuple(witness.input_event_paths),
                tuple(runtime.input_events),
                "input events mismatch",
            )
        )
    if tuple(witness.consumed_events) != tuple(runtime.consumed_events):
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].consumed_events" % witness.index,
                tuple(witness.consumed_events),
                tuple(runtime.consumed_events),
                "consumed events mismatch",
            )
        )
    if tuple(witness.unconsumed_events) != tuple(runtime.unconsumed_events):
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].unconsumed_events" % witness.index,
                tuple(witness.unconsumed_events),
                tuple(runtime.unconsumed_events),
                "unconsumed events mismatch",
            )
        )
    _compare_calls(
        mismatches, witness.index, witness.abstract_calls, runtime.abstract_calls
    )


def _compare_trace_shape(
    mismatches: list[BmcReplayMismatch], witness: BmcWitnessTrace
) -> None:
    if len(witness.frames) != len(witness.steps) + 1:
        mismatches.append(
            BmcReplayMismatch(
                "frames",
                len(witness.steps) + 1,
                len(witness.frames),
                "frame/step length mismatch",
            )
        )
    for position, frame in enumerate(witness.frames):
        if frame.index != position:
            mismatches.append(
                BmcReplayMismatch(
                    "frames[%d].index" % position,
                    position,
                    frame.index,
                    "frame index mismatch",
                )
            )
    for position, step in enumerate(witness.steps):
        if step.index != position:
            mismatches.append(
                BmcReplayMismatch(
                    "steps[%d].index" % position,
                    position,
                    step.index,
                    "step index mismatch",
                )
            )
        if step.source_frame != position:
            mismatches.append(
                BmcReplayMismatch(
                    "steps[%d].source_frame" % position,
                    position,
                    step.source_frame,
                    "step source frame mismatch",
                )
            )
        if step.target_frame != position + 1:
            mismatches.append(
                BmcReplayMismatch(
                    "steps[%d].target_frame" % position,
                    position + 1,
                    step.target_frame,
                    "step target frame mismatch",
                )
            )


def _initial_runtime(
    state_machine: StateMachine, witness: BmcWitnessTrace
) -> Optional[SimulationRuntime]:
    first = witness.frames[0] if witness.frames else None
    if first is not None and first.sentinel == "terminated":
        return None
    initial_vars = dict(first.vars) if first is not None else None
    initial_state = (
        first.state if first is not None and first.sentinel is None else None
    )
    if initial_state is None:
        return SimulationRuntime(state_machine, initial_vars=initial_vars)
    return SimulationRuntime(
        state_machine,
        initial_state=initial_state,
        initial_vars=initial_vars,
    )


def replay_bmc_witness(
    state_machine: StateMachine,
    witness: BmcWitnessTrace,
    *,
    abstract_handlers: Optional[
        Mapping[str, Callable[[ReadOnlyExecutionContext], None]]
    ] = None,
) -> BmcReplayResult:
    """Replay a decoded witness with ``SimulationRuntime``.

    Replay compares only macro-observable runtime data: states, termination,
    persistent variables, event accounting, and abstract handler contexts.  BMC
    case labels remain witness-side debug metadata because the runtime does not
    expose selected case labels.

    :param state_machine: State machine used for replay.
    :type state_machine: pyfcstm.model.StateMachine
    :param witness: Decoded BMC witness trace.
    :type witness: BmcWitnessTrace
    :param abstract_handlers: Optional user handlers wrapped after the recorder,
        defaults to ``None``.
    :type abstract_handlers: Mapping[str, Callable], optional
    :return: Replay result with structured mismatches.
    :rtype: BmcReplayResult
    :raises pyfcstm.bmc.errors.BmcBuildError: If inputs are malformed.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
        >>> from pyfcstm.bmc.witness import solve_bmc_property, decode_bmc_witness, replay_bmc_witness
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> sm = load_state_machine_from_text('state Root;')
        >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
        >>> result = solve_bmc_property(formula)
        >>> replay_bmc_witness(sm, decode_bmc_witness(formula, result.model)).ok
        True
    """
    if not isinstance(state_machine, StateMachine):
        raise BmcBuildError("state_machine must be StateMachine.")
    if not isinstance(witness, BmcWitnessTrace):
        raise BmcBuildError("witness must be BmcWitnessTrace.")
    if abstract_handlers is not None and not isinstance(abstract_handlers, Mapping):
        raise BmcBuildError("abstract_handlers must be a mapping or None.")
    runtime = _initial_runtime(state_machine, witness)
    recorder = _HandlerCallRecorder(_abstract_call_role_resolver(state_machine))
    frames = []
    steps = []
    mismatches: list[BmcReplayMismatch] = []
    _compare_trace_shape(mismatches, witness)
    if runtime is None:
        terminated_vars = dict(witness.frames[0].vars) if witness.frames else {}
        runtime_frames = tuple(
            BmcRuntimeFrame(index, None, True, dict(terminated_vars))
            for index, _frame in enumerate(witness.frames)
        )
        runtime_steps = tuple(
            BmcRuntimeStep(step.index, (), (), (), ()) for step in witness.steps
        )
        runtime_trace = BmcRuntimeTrace(runtime_frames, runtime_steps)
        for frame, runtime_frame in zip(witness.frames, runtime_frames):
            _compare_frame(mismatches, frame, runtime_frame)
        for step, runtime_step in zip(witness.steps, runtime_steps):
            _compare_step(mismatches, step, runtime_step)
        return BmcReplayResult(witness, runtime_trace, tuple(mismatches))
    _register_recorder(runtime, recorder, abstract_handlers)
    frames.append(_runtime_frame(runtime, 0))
    init_runtime_state = (
        frames[0].state
        if witness.frames and witness.frames[0].sentinel == "init"
        else None
    )
    if witness.frames:
        _compare_frame(mismatches, witness.frames[0], frames[0], init_runtime_state)
    for step in witness.steps:
        call_start = len(recorder.calls)
        terminated_absorb = runtime.is_ended
        cycle_count_before = None if terminated_absorb else runtime.cycle_count
        recorder.begin_step()
        result = runtime.cycle(step.input_event_paths)
        recorder.end_step()
        cycle_count_after = None if terminated_absorb else runtime.cycle_count
        history_entry = None
        if (
            not terminated_absorb
            and cycle_count_after > cycle_count_before
            and runtime.history
        ):
            history_entry = copy.deepcopy(runtime.history[-1])
        step_calls = tuple(
            BmcWitnessCallRecord(
                ordinal=idx,
                action_name=call.action_name,
                stage=call.stage,
                role=call.role,
                state=call.state,
                active_leaf=call.active_leaf,
                named_ref=call.named_ref,
                snapshot=call.snapshot,
            )
            for idx, call in enumerate(recorder.calls[call_start:])
        )
        runtime_step = BmcRuntimeStep(
            index=step.index,
            input_events=result.input_events,
            consumed_events=result.consumed_events,
            unconsumed_events=result.unconsumed_events,
            abstract_calls=step_calls,
            delta=result.delta,
            cycle_count_before=cycle_count_before,
            cycle_count_after=cycle_count_after,
            history_entry=history_entry,
        )
        steps.append(runtime_step)
        expected_history = None
        if step.case_kind != "absorb":
            target_frame = (
                witness.frames[step.target_frame]
                if 0 <= step.target_frame < len(witness.frames)
                else None
            )
            if target_frame is not None:
                expected_history = {
                    "cycle": step.index + 1,
                    "state": (
                        "(terminated)"
                        if target_frame.terminated
                        else (
                            init_runtime_state
                            if target_frame.sentinel == "init"
                            else target_frame.state
                        )
                    ),
                    "vars": dict(target_frame.vars),
                    "events": list(step.input_event_paths),
                    "delta": step.delta,
                }
        _compare_step(mismatches, step, runtime_step, expected_history)
        runtime_frame = _runtime_frame(runtime, step.target_frame)
        frames.append(runtime_frame)
        if step.target_frame < len(witness.frames):
            _compare_frame(
                mismatches,
                witness.frames[step.target_frame],
                runtime_frame,
                init_runtime_state,
            )
    return BmcReplayResult(
        witness=witness,
        runtime_trace=BmcRuntimeTrace(tuple(frames), tuple(steps)),
        mismatches=tuple(mismatches),
    )


__all__ = [
    "BmcSolveStatus",
    "BmcEventDecodePolicy",
    "BmcSolveResult",
    "BmcWitnessEvent",
    "BmcWitnessCallRecord",
    "BmcWitnessFrame",
    "BmcWitnessStep",
    "BmcWitnessTrace",
    "BmcRuntimeFrame",
    "BmcRuntimeStep",
    "BmcRuntimeTrace",
    "BmcReplayMismatch",
    "BmcReplayResult",
    "solve_bmc_property",
    "decode_bmc_witness",
    "replay_bmc_witness",
]

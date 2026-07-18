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
* :class:`BmcFeasibilityCheck` and :class:`BmcFeasibilityResult` - Staged
  evidence for the admissible BMC scenario.
* :class:`BmcWitnessTrace` - JSON-stable decoded witness root object.
* :class:`BmcReplayResult` - Structured runtime replay result and mismatches.
* :func:`solve_bmc_property` - Solve a compiled property formula.
* :func:`decode_bmc_witness` - Decode one SAT model into a witness trace.
* :func:`decode_bmc_result_trace` - Decode a role-selected model from a solve
  result.
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
    >>> decode_bmc_witness(formula, result.model).steps[0].delta
    False
"""

from __future__ import annotations

import io
import math
import sys
import time
from collections.abc import Iterable as IterableABC
from dataclasses import dataclass, field
from fractions import Fraction
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    cast,
)

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
    if status in {"unknown", "timeout"} and reason == "":
        raise BmcBuildError(
            "%s must be non-empty when %s is unknown or timeout."
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
    if status in {"unknown", "timeout"} and reason == "":
        raise BmcBuildError(
            "%s must be non-empty when %s is unknown or timeout."
            % (reason_name, status_name)
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
        if value["incomplete_elapsed_ms"] is not None:
            _validate_elapsed_ms(cast(float, value["incomplete_elapsed_ms"]))
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
    for field_name in ("model_status", "primary_status"):
        field_value = value.get(field_name)
        if field_value is not None and field_value not in {
            "sat",
            "unsat",
            "unknown",
            "timeout",
        }:
            raise BmcBuildError(
                "solver.%s must be sat, unsat, unknown, timeout, or None." % field_name
            )
    if "primary_reason" in value:
        _validate_primary_solve_reason(
            "solver.primary_status",
            value.get("primary_status"),
            "solver.primary_reason",
            value["primary_reason"],
        )
    if "primary_elapsed_ms" in value:
        _validate_elapsed_ms(value["primary_elapsed_ms"])


def _validate_witness_verdict(model_role: str, verdict: Mapping[str, Any]) -> None:
    required = {
        "property_satisfied",
        "witness_found",
        "counterexample_found",
        "incomplete",
        "outcome",
    }
    missing = required.difference(verdict)
    if missing:
        raise BmcBuildError(
            "verdict is missing required fields: %s." % ", ".join(sorted(missing))
        )
    expected = {
        "primary_witness": {
            "property_satisfied": True,
            "witness_found": True,
            "counterexample_found": False,
            "incomplete": False,
            "outcome": "witness_found",
        },
        "primary_counterexample": {
            "property_satisfied": False,
            "witness_found": False,
            "counterexample_found": True,
            "incomplete": False,
            "outcome": "property_violated",
        },
        "incomplete_suffix": {
            "property_satisfied": None,
            "witness_found": False,
            "counterexample_found": False,
            "incomplete": True,
            "outcome": "incomplete",
        },
    }[model_role]
    for field_name, expected_value in expected.items():
        if verdict.get(field_name) != expected_value:
            raise BmcBuildError(
                "verdict.%s is inconsistent with model_role=%r."
                % (field_name, model_role)
            )


def _validate_role_aware_witness_property(
    model_role: str, value: Mapping[str, Any]
) -> None:
    """Bind role-aware witness metadata to its property discriminator."""
    required = {"kind", "polarity"}
    missing = required.difference(value)
    if missing:
        raise BmcBuildError(
            "role-aware witness property is missing: %s." % ", ".join(sorted(missing))
        )
    kind = value["kind"]
    polarity = value["polarity"]
    if kind not in {
        "reach",
        "forbid",
        "invariant",
        "must_reach",
        "exists_always",
        "response",
        "cover",
    }:
        raise BmcBuildError("role-aware witness property.kind is invalid: %r." % kind)
    if polarity not in {"witness", "counterexample"}:
        raise BmcBuildError(
            "role-aware witness property.polarity is invalid: %r." % polarity
        )
    expected_polarity = {
        "reach": "witness",
        "exists_always": "witness",
        "cover": "witness",
        "forbid": "counterexample",
        "invariant": "counterexample",
        "must_reach": "counterexample",
        "response": "counterexample",
    }[kind]
    if polarity != expected_polarity:
        raise BmcBuildError(
            "role-aware witness property.polarity does not match property.kind "
            "%r." % kind
        )
    expected = {
        "primary_witness": {"polarity": "witness"},
        "primary_counterexample": {"polarity": "counterexample"},
        "incomplete_suffix": {
            "kind": "response",
            "polarity": "counterexample",
        },
    }[model_role]
    for field_name, expected_value in expected.items():
        if value[field_name] != expected_value:
            raise BmcBuildError(
                "role-aware witness property.%s is inconsistent with "
                "model_role=%r." % (field_name, model_role)
            )


def _validate_role_aware_witness_solver_metadata(
    model_role: str, value: Mapping[str, Any]
) -> None:
    required = {
        "model_status",
        "primary_status",
        "incomplete_status",
        "primary_reason",
        "incomplete_reason",
        "primary_elapsed_ms",
        "incomplete_elapsed_ms",
    }
    missing = required.difference(value)
    if missing:
        raise BmcBuildError(
            "role-aware witness solver metadata is missing: %s."
            % ", ".join(sorted(missing))
        )
    legacy_only = {"status", "reason", "elapsed_ms"}.intersection(value)
    if legacy_only:
        raise BmcBuildError(
            "role-aware witness solver metadata cannot contain raw-model fields: %s."
            % ", ".join(sorted(legacy_only))
        )
    model_status = value["model_status"]
    primary_status = value["primary_status"]
    incomplete_status = value["incomplete_status"]
    if model_status != "sat":
        raise BmcBuildError("role-aware witness model_status must be sat.")
    if model_role in {"primary_witness", "primary_counterexample"}:
        if primary_status != "sat" or incomplete_status is not None:
            raise BmcBuildError(
                "primary model roles require primary sat and no suffix status."
            )
        if value["incomplete_elapsed_ms"] is not None:
            raise BmcBuildError("primary model roles require no suffix elapsed time.")
    elif primary_status != "unsat" or incomplete_status != "sat":
        raise BmcBuildError(
            "incomplete_suffix requires primary unsat and incomplete sat."
        )
    elif value["incomplete_elapsed_ms"] is None:
        raise BmcBuildError(
            "incomplete_suffix requires a non-null suffix elapsed time."
        )
    if value["primary_reason"] is not None:
        raise BmcBuildError(
            "role-aware witness solver metadata requires primary_reason=None."
        )
    if (
        value["incomplete_status"] in {"sat", "unsat"}
        and value["incomplete_reason"] is not None
    ):
        raise BmcBuildError(
            "role-aware completed suffix metadata requires incomplete_reason=None."
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
    status = trace.solver.get("status", trace.solver.get("model_status", "-"))
    if bound is None:
        spec = str(kind)
    else:
        spec = "%s<=%s" % (kind, bound)
    role = "" if trace.model_role is None else ", %s" % trace.model_role
    return "BmcWitnessTrace[%s, %s%s] frames=%d steps=%d" % (
        spec,
        status,
        role,
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
    role = "" if result.model_role is None else " role=%s" % result.model_role
    parts = [
        "BmcReplayResult[%s]%s mismatches=%d" % (status, role, len(result.mismatches)),
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
    if isinstance(obj, BmcFeasibilityCheck):
        return obj.to_canonical()
    if isinstance(obj, BmcFeasibilityRefinementCheck):
        return obj.to_canonical()
    if isinstance(obj, BmcFeasibilityResult):
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


@dataclass(frozen=True)
class _BmcSolvePresentation:
    """Human-readable semantic summary for one solver result."""

    headline: str
    scenario: str
    primary_search: str
    response_horizon: Optional[str]
    conclusion: str
    severity: str
    evidence: Tuple[str, ...]


def _solve_bound_phrase(result: "BmcSolveResult") -> str:
    bound = result.formula.bound
    return "%d macro-step" % bound if bound == 1 else "%d macro-steps" % bound


def _solve_search_kind(result: "BmcSolveResult") -> str:
    return "WITNESS" if result.polarity == "witness" else "COUNTEREXAMPLE"


def _solve_scenario(result: "BmcSolveResult", outcome: str) -> str:
    feasibility = result._validated_feasibility()
    if outcome == "scenario_infeasible":
        return "INFEASIBLE"
    if outcome == "feasibility_unknown":
        if feasibility.assumptions.origin == "checked":
            return "UNKNOWN"
        return "NOT CHECKED"
    if outcome == "feasibility_timeout":
        if feasibility.assumptions.origin == "checked":
            return "TIMED OUT"
        return "NOT CHECKED"
    if outcome in {"unknown", "timeout"}:
        return "NOT CHECKED"
    return "FEASIBLE"


def _solve_response_horizon(result: "BmcSolveResult", outcome: str) -> Optional[str]:
    if result.kind != "response":
        return None
    if outcome in {
        "scenario_infeasible",
        "feasibility_unknown",
        "feasibility_timeout",
        "unknown",
        "timeout",
    }:
        return None
    if outcome == "property_satisfied":
        return "CLOSED" if result.incomplete_status == "unsat" else "NOT NEEDED"
    if outcome == "incomplete":
        if result.incomplete_status == "sat":
            return "OPEN"
        if result.incomplete_status == "unknown":
            return "UNKNOWN"
        if result.incomplete_status == "timeout":
            return "TIMED OUT"
        if result.incomplete_reason == "incomplete check disabled":
            return "DISABLED"
        return "NOT CHECKED"
    return None


def _solve_failure_evidence(result: "BmcSolveResult") -> Tuple[str, ...]:
    feasibility = result._validated_feasibility()
    stage = feasibility.infeasible_stage
    details = {
        "kernel": "No admissible execution exists in the bounded solver kernel.",
        "initialization": "Adding initialization constraints leaves no admissible execution.",
        "assumptions": "Adding assumptions leaves no admissible execution.",
    }
    if stage is not None:
        return (
            "Failure boundary: %s" % stage.upper(),
            "Failure detail: %s" % details[stage],
        )
    reason = next(
        (
            check.reason
            for check in (
                feasibility.kernel,
                feasibility.initialization,
                feasibility.assumptions,
            )
            if check.reason is not None
        ),
        None,
    )
    if reason is None:
        reason = next(
            (
                diagnostic
                for diagnostic in result.diagnostics
                if diagnostic.startswith("feasibility_")
            ),
            None,
        )
    suffix = " (%s)" % reason if reason is not None else ""
    return (
        "Failure boundary: NOT LOCALIZED",
        "Localization: %s%s" % (feasibility.localization_status.upper(), suffix),
        "Failure detail: The scenario is infeasible, but the first failing "
        "cumulative boundary was not localized.",
    )


def _solve_exception_evidence(
    result: "BmcSolveResult", outcome: str, response_horizon: Optional[str]
) -> Tuple[str, ...]:
    """Return semantic evidence for an inconclusive BMC result.

    The structured result keeps low-level reasons in solver fields and
    diagnostics.  Human output also needs the responsible stage and reason in
    its Evidence section so callers do not have to inspect the Details table.
    """
    feasibility = result._validated_feasibility()
    if outcome in {"feasibility_unknown", "feasibility_timeout"}:
        assumptions = feasibility.assumptions
        if assumptions.origin == "checked":
            status = "TIMED OUT" if assumptions.status == "timeout" else "UNKNOWN"
            reason = assumptions.reason or "not provided"
            return (
                "Feasibility stage: ASSUMPTIONS",
                "Feasibility status: %s" % status,
                "Feasibility reason: %s" % reason,
            )
        return (
            "Feasibility stage: ASSUMPTIONS (NOT CHECKED)",
            "Feasibility reason: shared timeout budget exhausted before "
            "assumptions check.",
        )
    if outcome in {"unknown", "timeout"}:
        reason = result.reason or "not provided"
        return ("Primary reason: %s" % reason,)
    if outcome == "incomplete":
        if response_horizon in {"UNKNOWN", "TIMED OUT"}:
            return (
                "Horizon reason: %s" % (result.incomplete_reason or "not provided"),
            )
        if response_horizon == "OPEN":
            return (
                "Horizon reason: response obligation remains open beyond the "
                "current bounded horizon.",
            )
        if response_horizon == "NOT CHECKED":
            return (
                "Horizon reason: shared timeout budget exhausted before suffix check.",
            )
        if response_horizon == "DISABLED":
            return ("Horizon reason: response horizon check was disabled.",)
    return ()


def _solve_conclusion(
    result: "BmcSolveResult", outcome: str, response_horizon: Optional[str]
) -> str:
    feasibility = result._validated_feasibility()
    bound = _solve_bound_phrase(result)
    kind = result.kind
    search_kind = _solve_search_kind(result).lower()
    if outcome == "witness_found":
        return (
            "At least one admissible execution satisfies the %s objective "
            "within %s." % (kind, bound)
        )
    if outcome == "no_witness":
        return "No admissible execution satisfies the %s objective within %s." % (
            kind,
            bound,
        )
    if outcome == "property_violated":
        return (
            "At least one admissible execution violates the %s property within %s."
            % (kind, bound)
        )
    if outcome == "property_satisfied":
        if kind == "response" and response_horizon == "NOT NEEDED":
            return (
                "The response horizon is complete and no counterexample exists; "
                "every admissible execution within %s satisfies the response property."
                % bound
            )
        if kind == "response":
            return (
                "The response horizon check found no open obligation; every "
                "admissible execution within %s satisfies the response property."
                % bound
            )
        return "Every admissible execution within %s satisfies the %s property." % (
            bound,
            kind,
        )
    if outcome == "scenario_infeasible":
        return (
            "No admissible execution exists within %s; the property was not evaluated."
            % bound
        )
    if outcome == "feasibility_unknown":
        return (
            "Scenario feasibility is unknown, so the primary UNSAT result cannot "
            "be interpreted as a property verdict."
        )
    if outcome == "feasibility_timeout":
        if feasibility.assumptions.origin == "checked":
            return (
                "Scenario feasibility timed out, so the primary UNSAT result "
                "cannot be interpreted as a property verdict."
            )
        return (
            "Scenario feasibility was not checked because the shared timeout "
            "budget was exhausted; no property verdict is available."
        )
    if outcome == "unknown":
        return (
            "The primary %s search returned unknown; no property verdict is available."
            % search_kind
        )
    if outcome == "timeout":
        return (
            "The primary %s search timed out; no property verdict is available."
            % search_kind
        )
    if outcome == "incomplete":
        conclusions = {
            "NOT NEEDED": "The response horizon is complete and no counterexample exists.",
            "CLOSED": "The response horizon check found no open obligation.",
            "OPEN": (
                "An admissible finite prefix leaves a response obligation open "
                "beyond the current horizon; no bounded property verdict is available."
            ),
            "UNKNOWN": (
                "The response horizon check returned unknown; no bounded property "
                "verdict is available."
            ),
            "TIMED OUT": (
                "The response horizon check timed out; no bounded property verdict "
                "is available."
            ),
            "NOT CHECKED": (
                "The response horizon was not checked because the shared timeout "
                "budget was exhausted; no bounded property verdict is available."
            ),
            "DISABLED": (
                "The response horizon check was disabled; no bounded property "
                "verdict is available."
            ),
        }
        return conclusions[response_horizon or "NOT CHECKED"]
    raise BmcBuildError("Unsupported BMC outcome: %s" % outcome)


def _solve_presentation(result: "BmcSolveResult") -> _BmcSolvePresentation:
    outcome = result.outcome
    response_horizon = _solve_response_horizon(result, outcome)
    headlines = {
        "witness_found": "PROPERTY HOLDS WITHIN BOUND; WITNESS FOUND",
        "no_witness": "PROPERTY DOES NOT HOLD WITHIN BOUND; NO WITNESS",
        "property_violated": "PROPERTY DOES NOT HOLD WITHIN BOUND; COUNTEREXAMPLE FOUND",
        "property_satisfied": "PROPERTY GUARANTEED WITHIN BOUND; NO COUNTEREXAMPLE",
        "scenario_infeasible": "SCENARIO INFEASIBLE; PROPERTY NOT EVALUATED",
        "feasibility_unknown": "SCENARIO FEASIBILITY UNKNOWN; PROPERTY NOT EVALUATED",
        "feasibility_timeout": "SCENARIO FEASIBILITY TIMED OUT; PROPERTY NOT EVALUATED",
        "unknown": "PROPERTY INCONCLUSIVE; PRIMARY CHECK UNKNOWN",
        "timeout": "PROPERTY INCONCLUSIVE; PRIMARY CHECK TIMED OUT",
        "incomplete": "PROPERTY INCONCLUSIVE; RESPONSE HORIZON INCOMPLETE",
    }
    evidence = []
    if outcome == "scenario_infeasible":
        evidence.extend(_solve_failure_evidence(result))
    else:
        evidence.extend(_solve_exception_evidence(result, outcome, response_horizon))
    if result.status == "sat":
        role = (
            "PRIMARY WITNESS"
            if result.polarity == "witness"
            else "PRIMARY COUNTEREXAMPLE"
        )
        evidence.append("Model role: %s" % role)
        evidence.append("Model evidence: SAT model available.")
    elif result.available_model_roles == ("incomplete_suffix",):
        evidence.append("Model role: INCOMPLETE SUFFIX")
        evidence.append("Model evidence: SAT suffix model available.")
    else:
        evidence.append("Model evidence: no SAT model available.")
    severity = {
        "witness_found": "green",
        "property_satisfied": "green",
        "no_witness": "red",
        "property_violated": "red",
    }.get(outcome, "yellow")
    return _BmcSolvePresentation(
        headline=headlines[outcome],
        scenario=_solve_scenario(result, outcome),
        primary_search="%s = %s" % (_solve_search_kind(result), result.status.upper()),
        response_horizon=response_horizon,
        conclusion=_solve_conclusion(result, outcome, response_horizon),
        severity=severity,
        evidence=tuple(evidence),
    )


def _render_solve_result(result: "BmcSolveResult", tablefmt: str) -> str:
    presentation = _solve_presentation(result)
    lines = [
        "BmcSolveResult: %s" % presentation.headline,
        "Scenario: %s" % presentation.scenario,
        "Primary search: %s" % presentation.primary_search,
    ]
    if presentation.response_horizon is not None:
        lines.append("Response horizon: %s" % presentation.response_horizon)
    lines.append("Conclusion: %s" % presentation.conclusion)
    lines.append("Evidence:")
    lines.extend("  %s" % item for item in presentation.evidence)
    lines.extend(("", "Details:", _render_field_value_object(result, tablefmt)))
    return "\n".join(lines)


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
    if isinstance(obj, BmcSolveResult):
        return _render_solve_result(obj, tablefmt)
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


_FEASIBILITY_ORIGINS = {"checked", "inferred", "not_checked"}
_FEASIBILITY_REFINEMENT_NAMES = {
    "component_initialization",
    "domain_initialization",
    "component_assumptions",
    "domain_assumptions",
    "unsat_core",
    "unsat_core_minimization",
}
_FEASIBILITY_REFINEMENT_STATUSES = {
    "sat",
    "unsat",
    "complete",
    "unknown",
    "timeout",
}
_FEASIBILITY_COMPONENT_REFINEMENT_NAMES = {
    "component_initialization",
    "domain_initialization",
    "component_assumptions",
    "domain_assumptions",
}
_FEASIBILITY_CORE_REFINEMENT_NAMES = {
    "unsat_core",
    "unsat_core_minimization",
}
_FEASIBILITY_TIMEOUT_BEFORE_ASSUMPTIONS = (
    "feasibility_timeout:deadline_exhausted_before_assumptions_check"
)
_SUFFIX_TIMEOUT_BEFORE_CHECK = "suffix_timeout:deadline_exhausted_before_suffix_check"

_BMC_MODEL_ROLES = {
    "primary_witness",
    "primary_counterexample",
    "incomplete_suffix",
}


def _validate_optional_elapsed_ms(name: str, value: Optional[float]) -> None:
    if value is not None:
        _validate_elapsed_ms(value)


def _validate_feasibility_check_payload(
    status: Optional[BmcSolveStatus],
    origin: str,
    reason: Optional[str],
    elapsed_ms: Optional[float],
) -> None:
    if origin not in _FEASIBILITY_ORIGINS:
        raise BmcBuildError(
            "origin must be checked, inferred, or not_checked, got %r." % origin
        )
    if status is not None and status not in {
        "sat",
        "unsat",
        "unknown",
        "timeout",
    }:
        raise BmcBuildError("status must be sat, unsat, unknown, timeout, or None.")
    _validate_optional_reason("reason", reason)
    _validate_optional_elapsed_ms("elapsed_ms", elapsed_ms)
    if origin == "not_checked":
        if status is not None or reason is not None or elapsed_ms is not None:
            raise BmcBuildError(
                "not_checked feasibility evidence requires status, reason, and "
                "elapsed_ms to be None."
            )
        return
    if origin == "inferred":
        if status != "sat" or reason is not None or elapsed_ms is not None:
            raise BmcBuildError(
                "inferred feasibility evidence requires sat status and no "
                "reason or elapsed_ms."
            )
        return
    if status is None or elapsed_ms is None:
        raise BmcBuildError(
            "checked feasibility evidence requires status and elapsed_ms."
        )
    if status in {"sat", "unsat"} and reason is not None:
        raise BmcBuildError(
            "checked sat/unsat feasibility evidence requires reason=None."
        )
    if status in {"unknown", "timeout"} and not reason:
        raise BmcBuildError(
            "checked unknown/timeout feasibility evidence requires a non-empty reason."
        )


@dataclass(frozen=True)
class BmcFeasibilityCheck(_PrettyPrintableMixin):
    """Evidence for one cumulative BMC feasibility stage.

    :param status: Solver status for the cumulative stage, or ``None`` when the
        stage was not checked.
    :type status: str, optional
    :param origin: Evidence origin: ``checked``, ``inferred``, or
        ``not_checked``.
    :type origin: str
    :param reason: Non-empty solver reason for an unknown or timeout check,
        defaults to ``None``.
    :type reason: str, optional
    :param elapsed_ms: Elapsed time for a real stage check, defaults to ``None``.
    :type elapsed_ms: float, optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the evidence combination is
        inconsistent.

    Example::

        >>> BmcFeasibilityCheck(status="sat", origin="inferred").to_canonical()
        {'status': 'sat', 'origin': 'inferred', 'reason': None, 'elapsed_ms': None}
    """

    status: Optional[BmcSolveStatus]
    origin: str
    reason: Optional[str] = None
    elapsed_ms: Optional[float] = None

    def __post_init__(self) -> None:
        _validate_feasibility_check_payload(
            self.status, self.origin, self.reason, self.elapsed_ms
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return the JSON-stable stage evidence mapping.

        :return: Canonical stage evidence.
        :rtype: Dict[str, object]

        Example::

            >>> BmcFeasibilityCheck(None, "not_checked").to_canonical()["status"] is None
            True
        """
        return {
            "status": self.status,
            "origin": self.origin,
            "reason": self.reason,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True)
class BmcFeasibilityRefinementCheck(_PrettyPrintableMixin):
    """Evidence for an optional feasibility refinement probe.

    :param name: Stable refinement probe name.
    :type name: str
    :param status: Probe status.
    :type status: str
    :param reason: Solver reason for unknown or timeout, defaults to ``None``.
    :type reason: str, optional
    :param elapsed_ms: Probe elapsed time, defaults to ``None``.
    :type elapsed_ms: float, optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the probe payload is invalid.

    Example::

        >>> BmcFeasibilityRefinementCheck(
        ...     "unsat_core", "complete", elapsed_ms=0.5
        ... ).to_canonical()["status"]
        'complete'
    """

    name: str
    status: str
    reason: Optional[str] = None
    elapsed_ms: Optional[float] = None

    def __post_init__(self) -> None:
        if self.name not in _FEASIBILITY_REFINEMENT_NAMES:
            raise BmcBuildError(
                "Unsupported feasibility refinement name: %r." % self.name
            )
        if self.status not in _FEASIBILITY_REFINEMENT_STATUSES:
            raise BmcBuildError(
                "Unsupported feasibility refinement status: %r." % self.status
            )
        _validate_optional_reason("reason", self.reason)
        _validate_optional_elapsed_ms("elapsed_ms", self.elapsed_ms)
        if (
            self.status == "complete"
            and self.name in _FEASIBILITY_COMPONENT_REFINEMENT_NAMES
        ):
            raise BmcBuildError(
                "component/domain feasibility refinement cannot use status=complete."
            )
        if self.status in {"sat", "unsat", "complete"} and self.reason is not None:
            raise BmcBuildError(
                "Completed feasibility refinement requires reason=None."
            )
        if self.status in {"unknown", "timeout"} and not self.reason:
            raise BmcBuildError(
                "Unknown/timeout feasibility refinement requires a non-empty reason."
            )
        if self.elapsed_ms is None:
            raise BmcBuildError("Feasibility refinement requires elapsed_ms.")
        if (
            self.status == "complete"
            and self.name not in _FEASIBILITY_CORE_REFINEMENT_NAMES
        ):
            raise BmcBuildError(
                "Only unsat-core feasibility refinement can use status=complete."
            )

    def to_canonical(self) -> _CanonicalDict:
        """Return the JSON-stable refinement mapping.

        :return: Canonical refinement evidence.
        :rtype: Dict[str, object]

        Example::

            >>> BmcFeasibilityRefinementCheck(
            ...     "unsat_core", "complete", elapsed_ms=0.5
            ... ).to_canonical()["name"]
            'unsat_core'
        """
        return {
            "name": self.name,
            "status": self.status,
            "reason": self.reason,
            "elapsed_ms": self.elapsed_ms,
        }


@dataclass(frozen=True)
class BmcFeasibilityResult(_PrettyPrintableMixin):
    """Structured cumulative feasibility evidence for a BMC solve.

    ``assumptions`` being checked UNSAT proves that the admissible scenario is
    empty even when the deadline prevents deeper localization.  In that case
    ``scenario_infeasible`` is true while ``infeasible_stage`` remains ``None``
    and ``localization_status`` remains ``not_checked`` only when no checked SAT
    prefix already identifies the first weaker stage.  A checked SAT
    ``initialization`` stage localizes the failure to ``assumptions``; a checked
    SAT ``kernel`` followed by checked UNSAT ``initialization`` localizes it to
    ``initialization``.  ``inferred`` SAT stages are conclusions from a stronger
    checked SAT prefix, not additional solver calls.  Because these stages are
    cumulative, a localized ``initialization`` failure also requires checked
    UNSAT ``assumptions`` evidence, and a localized ``kernel`` failure requires
    checked UNSAT evidence for both outer stages.  This keeps direct public
    constructors and canonical JSON payloads closed under the same evidence
    contract as :func:`solve_bmc_property`.

    :param kernel: Evidence for ``K_N``.
    :type kernel: BmcFeasibilityCheck
    :param initialization: Evidence for ``S_init``.
    :type initialization: BmcFeasibilityCheck
    :param assumptions: Evidence for ``S_assume``.
    :type assumptions: BmcFeasibilityCheck
    :param infeasible_stage: First localized infeasible stage, defaults to
        ``None``.
    :type infeasible_stage: str, optional
    :param localization_status: Localization status, defaults to
        ``"not_checked"``.
    :type localization_status: str, optional
    :param refinement_status: Optional refinement aggregate, defaults to
        ``"not_requested"``.
    :type refinement_status: str, optional
    :param refinement_reason: Aggregate refinement reason, defaults to ``None``.
    :type refinement_reason: str, optional
    :param refinement_checks: Executed refinement checks, defaults to ``()``.
    :type refinement_checks: Sequence[BmcFeasibilityRefinementCheck], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If stage evidence is inconsistent.

    Example::

        >>> sat = BmcFeasibilityCheck("sat", "inferred")
        >>> BmcFeasibilityResult(
        ...     sat, sat, sat, localization_status="not_needed"
        ... ).localization_status
        'not_needed'
    """

    kernel: BmcFeasibilityCheck
    initialization: BmcFeasibilityCheck
    assumptions: BmcFeasibilityCheck
    infeasible_stage: Optional[str] = None
    localization_status: str = "not_checked"
    refinement_status: str = "not_requested"
    refinement_reason: Optional[str] = None
    refinement_checks: Sequence[BmcFeasibilityRefinementCheck] = ()

    def __post_init__(self) -> None:
        checks = (self.kernel, self.initialization, self.assumptions)
        if not all(isinstance(item, BmcFeasibilityCheck) for item in checks):
            raise BmcBuildError("All feasibility stages must be BmcFeasibilityCheck.")
        if self.infeasible_stage not in {
            None,
            "kernel",
            "initialization",
            "assumptions",
        }:
            raise BmcBuildError(
                "Unsupported infeasible_stage: %r." % self.infeasible_stage
            )
        if self.localization_status not in {
            "not_needed",
            "not_checked",
            "complete",
            "unknown",
            "timeout",
        }:
            raise BmcBuildError(
                "Unsupported localization_status: %r." % self.localization_status
            )
        if self.refinement_status not in {
            "not_requested",
            "not_needed",
            "complete",
            "partial",
            "unknown",
            "timeout",
        }:
            raise BmcBuildError(
                "Unsupported refinement_status: %r." % self.refinement_status
            )
        _validate_optional_reason("refinement_reason", self.refinement_reason)
        if self.refinement_status in {"not_requested", "not_needed", "complete"}:
            if self.refinement_reason is not None:
                raise BmcBuildError(
                    "refinement_reason must be None for completed or unused refinement."
                )
        elif (
            self.refinement_status in {"unknown", "timeout"}
            and not self.refinement_reason
        ):
            raise BmcBuildError(
                "Unknown/timeout refinement requires a non-empty refinement_reason."
            )
        if (
            self.infeasible_stage is not None
            and self.refinement_status != "not_requested"
        ):
            raise BmcBuildError(
                "localized infeasible stages require refinement_status=not_requested."
            )
        object.__setattr__(
            self,
            "refinement_checks",
            _coerce_public_sequence(
                "refinement_checks",
                self.refinement_checks,
                BmcFeasibilityRefinementCheck,
                "BmcFeasibilityRefinementCheck objects",
            ),
        )
        inconclusive = any(
            item.origin == "checked" and item.status in {"unknown", "timeout"}
            for item in checks
        )
        if inconclusive and self.infeasible_stage is not None:
            raise BmcBuildError(
                "unknown/timeout feasibility evidence cannot claim a localized "
                "infeasible_stage."
            )
        if self.infeasible_stage is not None:
            if self.localization_status != "complete":
                raise BmcBuildError(
                    "infeasible_stage requires localization_status=complete."
                )
            selected = getattr(self, self.infeasible_stage)
            if selected.origin != "checked" or selected.status != "unsat":
                raise BmcBuildError(
                    "infeasible_stage requires checked/unsat evidence for the "
                    "selected stage."
                )
            if (
                self.infeasible_stage == "initialization"
                and self.kernel.status != "sat"
            ):
                raise BmcBuildError(
                    "initialization infeasible_stage requires a SAT prefix."
                )
            if (
                self.infeasible_stage == "initialization"
                and self.kernel.origin != "checked"
            ):
                raise BmcBuildError(
                    "initialization infeasible_stage requires checked kernel evidence."
                )
            if self.infeasible_stage == "initialization" and (
                self.assumptions.origin != "checked"
                or self.assumptions.status != "unsat"
            ):
                raise BmcBuildError(
                    "initialization infeasible_stage requires checked UNSAT "
                    "assumptions evidence."
                )
            if self.infeasible_stage == "assumptions" and (
                self.kernel.status != "sat" or self.initialization.status != "sat"
            ):
                raise BmcBuildError(
                    "assumptions infeasible_stage requires a SAT prefix."
                )
            if (
                self.infeasible_stage == "assumptions"
                and self.initialization.origin != "checked"
            ):
                raise BmcBuildError(
                    "assumptions infeasible_stage requires checked initialization "
                    "evidence."
                )
            if self.infeasible_stage == "kernel" and (
                self.initialization.origin != "checked"
                or self.initialization.status != "unsat"
                or self.assumptions.origin != "checked"
                or self.assumptions.status != "unsat"
            ):
                raise BmcBuildError(
                    "kernel infeasible_stage requires checked UNSAT initialization "
                    "and assumptions evidence."
                )
        elif self.localization_status == "complete":
            raise BmcBuildError(
                "localization_status=complete requires infeasible_stage."
            )
        if (
            any(
                item.status in {"unknown", "timeout"} and item.origin == "checked"
                for item in checks
            )
            and self.localization_status == "not_needed"
        ):
            raise BmcBuildError(
                "unknown/timeout feasibility evidence cannot use localization_status="
                "not_needed."
            )
        all_sat = all(item.status == "sat" for item in checks)
        all_inferred_sat = all(
            item.status == "sat" and item.origin == "inferred" for item in checks
        )
        for index, item in enumerate(checks):
            if item.origin != "inferred":
                continue
            if all_inferred_sat and self.localization_status == "not_needed":
                continue
            if not any(
                stronger.origin == "checked" and stronger.status == "sat"
                for stronger in checks[index + 1 :]
            ):
                raise BmcBuildError(
                    "cumulative feasibility inferred evidence requires a stronger "
                    "checked SAT stage."
                )
        if all_sat and self.localization_status != "not_needed":
            raise BmcBuildError(
                "all SAT feasibility stages require localization_status=not_needed."
            )
        if self.localization_status in {"unknown", "timeout"} and not inconclusive:
            raise BmcBuildError(
                "localization_status=unknown/timeout requires checked "
                "unknown/timeout feasibility evidence."
            )
        if self.initialization.status == "sat" and self.kernel.status != "sat":
            raise BmcBuildError(
                "cumulative feasibility evidence cannot claim SAT initialization "
                "after a non-SAT kernel stage."
            )
        if self.assumptions.status == "sat" and self.initialization.status != "sat":
            raise BmcBuildError(
                "cumulative feasibility evidence cannot claim SAT assumptions "
                "after a non-SAT initialization stage."
            )
        if (
            self.initialization.status == "sat"
            and self.assumptions.status == "unsat"
            and (
                self.infeasible_stage != "assumptions"
                or self.localization_status != "complete"
            )
        ):
            raise BmcBuildError(
                "checked SAT initialization with UNSAT assumptions requires "
                "complete assumptions localization."
            )
        if (
            self.kernel.status == "sat"
            and self.initialization.status == "unsat"
            and (
                self.infeasible_stage != "initialization"
                or self.localization_status != "complete"
            )
        ):
            raise BmcBuildError(
                "checked SAT kernel with UNSAT initialization requires complete "
                "initialization localization."
            )
        if self.kernel.status == "unsat" and (
            self.initialization.status == "sat" or self.assumptions.status == "sat"
        ):
            raise BmcBuildError(
                "cumulative feasibility evidence cannot claim SAT after kernel UNSAT."
            )
        if self.initialization.status == "unsat" and self.assumptions.status == "sat":
            raise BmcBuildError(
                "cumulative feasibility evidence cannot claim SAT after initialization UNSAT."
            )
        if self.localization_status == "not_needed" and not all_sat:
            raise BmcBuildError(
                "localization_status=not_needed requires all SAT feasibility stages."
            )
        if (
            self.refinement_status in {"not_requested", "not_needed"}
            and self.refinement_checks
        ):
            raise BmcBuildError(
                "A refinement status without executed checks cannot contain checks."
            )
        if (
            self.refinement_status in {"complete", "partial"}
            and not self.refinement_checks
        ):
            raise BmcBuildError(
                "A completed or partial refinement requires executed checks."
            )

    @property
    def scenario_infeasible(self) -> bool:
        """Return whether cumulative assumptions are proven UNSAT.

        :return: ``True`` when ``S_assume`` was checked UNSAT.
        :rtype: bool

        Example::

            >>> sat = BmcFeasibilityCheck("sat", "inferred")
            >>> BmcFeasibilityResult(
            ...     sat, sat, sat, localization_status="not_needed"
            ... ).scenario_infeasible
            False
        """
        return self.assumptions.status == "unsat"

    def to_canonical(self) -> _CanonicalDict:
        """Return the JSON-stable feasibility mapping.

        :return: Canonical feasibility evidence.
        :rtype: Dict[str, object]

        Example::

            >>> sat = BmcFeasibilityCheck("sat", "inferred")
            >>> BmcFeasibilityResult(
            ...     sat, sat, sat, localization_status="not_needed"
            ... ).to_canonical()["infeasible_stage"] is None
            True
        """
        return {
            "kernel": self.kernel.to_canonical(),
            "initialization": self.initialization.to_canonical(),
            "assumptions": self.assumptions.to_canonical(),
            "infeasible_stage": self.infeasible_stage,
            "localization_status": self.localization_status,
            "refinement_status": self.refinement_status,
            "refinement_reason": self.refinement_reason,
            "refinement_checks": [
                item.to_canonical() for item in self.refinement_checks
            ],
        }


def _inferred_feasibility() -> BmcFeasibilityResult:
    """Build SAT prefix evidence inferred from one primary SAT model."""
    sat = BmcFeasibilityCheck("sat", "inferred")
    return BmcFeasibilityResult(
        kernel=sat,
        initialization=sat,
        assumptions=sat,
        localization_status="not_needed",
        refinement_status="not_needed",
    )


def _not_checked_feasibility() -> BmcFeasibilityResult:
    """Build fail-closed evidence for a primary inconclusive solve."""
    not_checked = BmcFeasibilityCheck(None, "not_checked")
    return BmcFeasibilityResult(
        kernel=not_checked,
        initialization=not_checked,
        assumptions=not_checked,
        localization_status="not_checked",
        refinement_status="not_needed",
    )


def _is_not_checked_feasibility(value: BmcFeasibilityResult) -> bool:
    """Return whether a result carries only inconclusive-stage evidence."""
    return (
        all(
            item.origin == "not_checked" and item.status is None
            for item in (value.kernel, value.initialization, value.assumptions)
        )
        and value.infeasible_stage is None
        and value.localization_status == "not_checked"
        and value.refinement_status in {"not_requested", "not_needed"}
        and not value.refinement_checks
    )


def _has_nonempty_incomplete_formula(formula: BmcPropertyFormula) -> bool:
    """Return whether a response formula has a real suffix diagnostic."""
    return not z3.is_false(formula.incomplete_formula)


def _has_diagnostic(result: "BmcSolveResult", marker: str) -> bool:
    """Return whether a stable diagnostic marker is present."""
    return marker in result.diagnostics


@dataclass(frozen=True)
class BmcSolveResult(_PrettyPrintableMixin):
    """Structured result for one BMC property solve.

    The default string representation starts with the same polarity-aware
    bounded verdict vocabulary used by the CLI, then includes the canonical
    field table.  Runtime replay is intentionally represented by the separate
    :class:`BmcReplayResult`; the CLI combines both objects and can therefore
    override the headline when replay mismatches.

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
    :param incomplete_elapsed_ms: Secondary-check elapsed time, defaults to
        ``None``.
    :type incomplete_elapsed_ms: float, optional
    :param total_elapsed_ms: End-to-end Python-side elapsed time for this public
        solve call, including staged-result construction, defaults to ``None``.
    :type total_elapsed_ms: float, optional
    :param feasibility: Staged scenario-feasibility evidence, defaults to
        ``None`` for SAT and inconclusive direct constructors.
    :type feasibility: BmcFeasibilityResult, optional
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
    incomplete_elapsed_ms: Optional[float] = None
    total_elapsed_ms: Optional[float] = None
    feasibility: Optional[BmcFeasibilityResult] = None

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
        _validate_optional_elapsed_ms(
            "incomplete_elapsed_ms", self.incomplete_elapsed_ms
        )
        _validate_optional_elapsed_ms("total_elapsed_ms", self.total_elapsed_ms)
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
        if self.incomplete_status is None:
            if self.incomplete_elapsed_ms is not None:
                raise BmcBuildError(
                    "incomplete_elapsed_ms must be None when suffix was not checked."
                )
        elif self.incomplete_elapsed_ms is None:
            raise BmcBuildError(
                "incomplete_elapsed_ms is required when suffix has a status."
            )
        feasibility = self.feasibility
        if feasibility is None:
            if self.status == "sat":
                feasibility = _inferred_feasibility()
            elif self.status in {"unknown", "timeout"}:
                feasibility = _not_checked_feasibility()
            else:
                raise BmcBuildError(
                    "feasibility evidence is required for primary unsat results."
                )
            object.__setattr__(self, "feasibility", feasibility)
        elif not isinstance(feasibility, BmcFeasibilityResult):
            raise BmcBuildError("feasibility must be BmcFeasibilityResult or None.")
        if self.status in {"unknown", "timeout"} and not _is_not_checked_feasibility(
            feasibility
        ):
            raise BmcBuildError(
                "primary unknown/timeout results require all feasibility stages "
                "to be not_checked."
            )
        if (
            self.status == "unsat"
            and _is_not_checked_feasibility(feasibility)
            and not _has_diagnostic(self, _FEASIBILITY_TIMEOUT_BEFORE_ASSUMPTIONS)
        ):
            raise BmcBuildError(
                "primary unsat results with all not_checked feasibility evidence "
                "require a deadline exhaustion diagnostic."
            )
        if self.status == "sat" and not (
            feasibility.kernel.origin == "inferred"
            and feasibility.initialization.origin == "inferred"
            and feasibility.assumptions.origin == "inferred"
            and feasibility.kernel.status == "sat"
            and feasibility.initialization.status == "sat"
            and feasibility.assumptions.status == "sat"
        ):
            raise BmcBuildError(
                "primary sat results require inferred SAT feasibility evidence."
            )
        if self.status != "sat" and feasibility.assumptions.origin == "inferred":
            raise BmcBuildError(
                "assumptions inferred feasibility evidence requires primary status=sat."
            )
        if self.status == "unsat":
            checks = (
                feasibility.kernel,
                feasibility.initialization,
                feasibility.assumptions,
            )
            for index, check in enumerate(checks[:-1]):
                if (
                    check.origin == "checked"
                    and check.status in {"unknown", "timeout"}
                    and any(
                        later.origin == "not_checked" for later in checks[index + 1 :]
                    )
                ):
                    raise BmcBuildError(
                        "inconclusive feasibility evidence cannot be followed by "
                        "not_checked stages."
                    )
        if self.incomplete_status is not None and self.kind != "response":
            raise BmcBuildError(
                "incomplete status is only valid for response properties."
            )
        if self.incomplete_status is not None and not _has_nonempty_incomplete_formula(
            self.formula
        ):
            raise BmcBuildError(
                "incomplete status requires a non-empty suffix formula."
            )
        if self.incomplete_status is not None and self.status != "unsat":
            raise BmcBuildError("incomplete status requires a primary UNSAT result.")
        if self.status == "sat" and feasibility.scenario_infeasible:
            raise BmcBuildError("primary sat result cannot be scenario_infeasible.")
        if self.incomplete_status == "sat" and (
            feasibility.scenario_infeasible or feasibility.assumptions.status != "sat"
        ):
            raise BmcBuildError(
                "incomplete suffix model requires SAT assumptions feasibility evidence."
            )
        if self.total_elapsed_ms is None:
            total = self.elapsed_ms + (self.incomplete_elapsed_ms or 0.0)
            object.__setattr__(self, "total_elapsed_ms", total)

    def _validated_feasibility(self) -> BmcFeasibilityResult:
        """Return validated feasibility evidence for internal consumers.

        :return: Non-optional feasibility evidence.
        :rtype: BmcFeasibilityResult
        :raises pyfcstm.bmc.errors.BmcBuildError: If an object bypassed normal
            dataclass initialization and has no feasibility evidence.
        """
        feasibility = self.feasibility
        if feasibility is None:
            raise _internal_error("BmcSolveResult feasibility evidence is missing.")
        return feasibility

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
        or can still contain an uncovered trigger window.  A proven
        ``scenario_infeasible`` result is not horizon-incomplete because it is a
        definitive non-verdict, while a feasibility timeout before the
        assumptions check remains incomplete.  If the primary response
        objective is ``"sat"``, the counterexample verdict is already decisive
        even when a separate suffix diagnostic would also be satisfiable.

        :return: Whether the solve result carries an incomplete verdict.
        :rtype: bool

        Example::

            >>> from pyfcstm.bmc.witness import BmcSolveResult, solve_bmc_property
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: active("Root");')))
            >>> BmcSolveResult(formula, 'timeout', reason='timeout').incomplete
            True
        """
        feasibility = self._validated_feasibility()
        if feasibility.scenario_infeasible:
            return False
        if _has_diagnostic(self, _FEASIBILITY_TIMEOUT_BEFORE_ASSUMPTIONS):
            return True
        if self.status in {"unknown", "timeout"}:
            return True
        if feasibility.assumptions.status in {"unknown", "timeout"}:
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
            >>> from pyfcstm.bmc.witness import BmcSolveResult, solve_bmc_property
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
            >>> from pyfcstm.bmc.witness import BmcSolveResult, solve_bmc_property
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
            is violated or lacks a required witness, and ``None`` if the
            property cannot be evaluated because the result is incomplete, the
            scenario is infeasible, or feasibility timed out.
        :rtype: Optional[bool]

        Example::

            >>> from pyfcstm.bmc.witness import BmcSolveResult, solve_bmc_property
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: terminated();')))
            >>> solve_bmc_property(formula).property_satisfied
            False
        """
        feasibility = self._validated_feasibility()
        if feasibility.scenario_infeasible:
            return None
        if _has_diagnostic(self, _FEASIBILITY_TIMEOUT_BEFORE_ASSUMPTIONS):
            return None
        if self.status in {"unknown", "timeout"}:
            return None
        if feasibility.assumptions.status in {"unknown", "timeout"}:
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
            ``"scenario_infeasible"``, ``"feasibility_timeout"``,
            ``"feasibility_unknown"``, ``"timeout"``, or ``"unknown"``.
        :rtype: str

        Example::

            >>> from pyfcstm.bmc.witness import BmcSolveResult, solve_bmc_property
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: terminated();')))
            >>> solve_bmc_property(formula).outcome
            'no_witness'
        """
        feasibility = self._validated_feasibility()
        if feasibility.scenario_infeasible:
            return "scenario_infeasible"
        if _has_diagnostic(self, _FEASIBILITY_TIMEOUT_BEFORE_ASSUMPTIONS):
            return "feasibility_timeout"
        if self.status == "timeout":
            return "timeout"
        if self.status == "unknown":
            return "unknown"
        if feasibility.assumptions.status == "timeout":
            return "feasibility_timeout"
        if feasibility.assumptions.status == "unknown":
            return "feasibility_unknown"
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
            >>> from pyfcstm.bmc.witness import BmcSolveResult, solve_bmc_property
            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> sm = load_state_machine_from_text('state Root;')
            >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(sm).prepare('check reach <= 1: terminated();')))
            >>> solve_bmc_property(formula).to_canonical()['status']
            'unsat'
        """
        feasibility = self._validated_feasibility()
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
            "incomplete_elapsed_ms": self.incomplete_elapsed_ms,
            "has_incomplete_model": self.incomplete_model is not None,
            "total_elapsed_ms": self.total_elapsed_ms,
            "feasibility": feasibility.to_canonical(),
            "available_model_roles": list(self.available_model_roles),
            "diagnostics": list(self.diagnostics),
        }

    @property
    def available_model_roles(self) -> Tuple[str, ...]:
        """Return the result model channels that contain SAT evidence.

        :return: Ordered available model roles.
        :rtype: Tuple[str, ...]

        Example::

            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> from pyfcstm.bmc.witness import solve_bmc_property
            >>> sm = load_state_machine_from_text("state Root;")
            >>> formula = compile_bmc_property(
            ...     build_bmc_core_formula(
            ...         BmcEngine(sm).prepare(
            ...             'check reach <= 1: active("Root");'
            ...         )
            ...     )
            ... )
            >>> solve_bmc_property(formula).available_model_roles
            ('primary_witness',)
        """
        if self.status == "sat":
            if self.polarity == "witness":
                return ("primary_witness",)
            return ("primary_counterexample",)
        feasibility = self._validated_feasibility()
        if (
            self.status == "unsat"
            and self.incomplete_status == "sat"
            and self.kind == "response"
            and _has_nonempty_incomplete_formula(self.formula)
            and feasibility.assumptions.status == "sat"
        ):
            return ("incomplete_suffix",)
        return ()


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
        During replay, ``"absorb"`` is a terminal no-op with a synthetic
        runtime Delta observation of false; its witness Delta flag is still
        compared so forged payloads are reported.
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
    values. The witness step schema includes canonical replay input events,
    ordered consumed event paths, and presence-derived unconsumed event paths.

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
    :param model_role: Selected model role for role-aware traces, defaults to
        ``None`` for raw-model traces.
    :type model_role: str, optional
    :param verdict: Detached verdict for role-aware traces, defaults to
        ``None``.
    :type verdict: Mapping[str, object], optional
    :raises pyfcstm.bmc.errors.BmcBuildError: If the trace payload is
        malformed or violates public witness invariants.

    Example::

        >>> trace = BmcWitnessTrace({'kind': 'reach'}, {'status': 'sat'}, {'mode': 'cold'}, (), ())
        >>> sorted(trace.to_canonical())
        ['diagnostics', 'frames', 'initial', 'property', 'solver', 'steps']
    """

    property: Mapping[str, Any]
    solver: Mapping[str, Any]
    initial: Mapping[str, Any]
    frames: Sequence[BmcWitnessFrame]
    steps: Sequence[BmcWitnessStep]
    diagnostics: Sequence[str] = ()
    model_role: Optional[str] = None
    verdict: Optional[Mapping[str, Any]] = None

    def __post_init__(self) -> None:
        role_aware = self.model_role is not None or self.verdict is not None
        if (self.model_role is None) != (self.verdict is None):
            raise BmcBuildError(
                "model_role and verdict must either both be present or both be absent."
            )
        if self.model_role is not None and self.model_role not in _BMC_MODEL_ROLES:
            raise BmcBuildError("Unsupported witness model_role: %r." % self.model_role)
        if role_aware:
            model_role = self.model_role
            if model_role is None:
                raise BmcBuildError(
                    "model_role and verdict must either both be present or both be absent."
                )
            verdict = self.verdict
            if not isinstance(verdict, Mapping):
                raise BmcBuildError("role-aware witness requires verdict metadata.")
            verdict = _coerce_public_json_mapping("verdict", verdict)
            _validate_witness_verdict(model_role, verdict)
            object.__setattr__(self, "verdict", verdict)
        if not isinstance(self.property, Mapping):
            raise BmcBuildError("property must be a mapping.")
        if not isinstance(self.solver, Mapping):
            raise BmcBuildError("solver must be a mapping.")
        if not isinstance(self.initial, Mapping):
            raise BmcBuildError("initial must be a mapping.")
        property_metadata = _coerce_public_json_mapping("property", self.property)
        solver_metadata = _coerce_public_json_mapping("solver", self.solver)
        initial_metadata = _coerce_public_json_mapping("initial", self.initial)
        if role_aware:
            model_role = self.model_role
            if model_role is None:
                raise BmcBuildError(
                    "model_role and verdict must either both be present or both be absent."
                )
            _validate_role_aware_witness_property(model_role, property_metadata)
        _validate_witness_solver_metadata(solver_metadata)
        role_solver_fields = {
            "model_status",
            "primary_status",
            "primary_reason",
            "primary_elapsed_ms",
        }
        if not role_aware and role_solver_fields.intersection(solver_metadata):
            raise BmcBuildError(
                "role-aware solver metadata requires model_role and verdict."
            )
        if role_aware:
            model_role = self.model_role
            if model_role is None:
                raise BmcBuildError(
                    "model_role and verdict must either both be present or both be absent."
                )
            _validate_role_aware_witness_solver_metadata(model_role, solver_metadata)
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
        role_aware = self.model_role is not None or self.verdict is not None
        if (self.model_role is None) != (self.verdict is None):
            raise BmcBuildError(
                "model_role and verdict must either both be present or both be absent."
            )
        if role_aware:
            model_role = self.model_role
            if model_role is None:
                raise BmcBuildError(
                    "model_role and verdict must either both be present or both be absent."
                )
            _validate_role_aware_witness_solver_metadata(model_role, solver_metadata)
            verdict = self.verdict
            if not isinstance(verdict, Mapping):
                raise BmcBuildError("role-aware witness requires verdict metadata.")
            _validate_witness_verdict(
                model_role,
                _coerce_public_json_mapping("verdict", verdict),
            )
        return {
            **(
                {"model_role": self.model_role, "verdict": self.verdict}
                if role_aware
                else {}
            ),
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

    def __post_init__(self) -> None:
        if (
            isinstance(self.index, bool)
            or not isinstance(self.index, int)
            or self.index < 0
        ):
            raise BmcBuildError("runtime step index must be a non-negative integer.")
        if not isinstance(self.delta, bool):
            raise BmcBuildError("runtime step delta must be bool.")
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
    :param model_role: Model role copied from the witness, defaults to ``None``
        for raw-model traces.
    :type model_role: str, optional
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
    model_role: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.witness, BmcWitnessTrace):
            raise BmcBuildError("witness must be BmcWitnessTrace.")
        if not isinstance(self.runtime_trace, BmcRuntimeTrace):
            raise BmcBuildError("runtime_trace must be BmcRuntimeTrace.")
        if self.model_role is None:
            object.__setattr__(self, "model_role", self.witness.model_role)
        elif self.model_role not in _BMC_MODEL_ROLES:
            raise BmcBuildError("Unsupported replay model_role: %r." % self.model_role)
        if self.witness.model_role != self.model_role:
            raise BmcBuildError("replay model_role must match the witness model_role.")
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
        payload = {
            "ok": self.ok,
            "runtime_trace": self.runtime_trace.to_canonical(),
            "mismatches": [item.to_canonical() for item in self.mismatches],
        }
        if self.model_role is not None:
            payload["model_role"] = self.model_role
        return payload


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


class _SolveBudget:
    """Track one optional deadline shared by all staged solver checks."""

    def __init__(self, timeout_ms: Optional[int]) -> None:
        if timeout_ms is not None and (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or timeout_ms <= 0
        ):
            raise BmcBuildError("timeout_ms must be a positive integer or None.")
        self.timeout_ms = timeout_ms
        self.deadline = (
            None if timeout_ms is None else time.monotonic() + timeout_ms / 1000.0
        )

    def remaining_ms(self) -> Optional[int]:
        if self.deadline is None:
            return None
        remaining = int((self.deadline - time.monotonic()) * 1000.0)
        return remaining if remaining >= 1 else None


def _check_with_budget(
    solver: z3.Solver, budget: _SolveBudget
) -> Tuple[
    BmcSolveStatus,
    Optional[z3.ModelRef],
    Optional[str],
    float,
    bool,
]:
    remaining = budget.remaining_ms()
    # ``timeout_ms=None`` leaves ``deadline`` and ``remaining`` unset, so this
    # path intentionally calls Z3 without setting a solver timeout.
    if budget.deadline is not None and remaining is None:
        return "timeout", None, "deadline_exhausted_before_check", 0.0, False
    if remaining is not None:
        solver.set(timeout=remaining)
    start = time.monotonic()
    status = solver.check()
    elapsed_ms = (time.monotonic() - start) * 1000.0
    if status == z3.sat:
        return "sat", solver.model(), None, elapsed_ms, True
    if status == z3.unsat:
        return "unsat", None, None, elapsed_ms, True
    reason = solver.reason_unknown() or "unknown"
    if reason == "timeout":
        return "timeout", None, reason, elapsed_ms, True
    return "unknown", None, reason, elapsed_ms, True


def _feasibility_check(
    status: BmcSolveStatus,
    reason: Optional[str],
    elapsed_ms: float,
    check_started: bool = True,
) -> BmcFeasibilityCheck:
    if not check_started:
        return _stage_not_checked()
    return BmcFeasibilityCheck(
        status=status,
        origin="checked",
        reason=reason,
        elapsed_ms=elapsed_ms,
    )


def _stage_not_checked() -> BmcFeasibilityCheck:
    return BmcFeasibilityCheck(status=None, origin="not_checked")


def _build_feasibility(
    kernel: BmcFeasibilityCheck,
    initialization: BmcFeasibilityCheck,
    assumptions: BmcFeasibilityCheck,
    *,
    infeasible_stage: Optional[str] = None,
    localization_status: str = "not_needed",
    refinement_status: str = "not_needed",
) -> BmcFeasibilityResult:
    return BmcFeasibilityResult(
        kernel=kernel,
        initialization=initialization,
        assumptions=assumptions,
        infeasible_stage=infeasible_stage,
        localization_status=localization_status,
        refinement_status=refinement_status,
    )


def _make_solve_result(
    formula: BmcPropertyFormula,
    *,
    status: BmcSolveStatus,
    model: Optional[z3.ModelRef],
    reason: Optional[str],
    elapsed_ms: float,
    timeout_ms: Optional[int],
    incomplete_status: Optional[BmcSolveStatus],
    incomplete_model: Optional[z3.ModelRef],
    incomplete_reason: Optional[str],
    incomplete_elapsed_ms: Optional[float],
    diagnostics: Sequence[str],
    feasibility: BmcFeasibilityResult,
    started_at: float,
) -> BmcSolveResult:
    return BmcSolveResult(
        formula=formula,
        status=status,
        model=model,
        reason=reason,
        elapsed_ms=elapsed_ms,
        timeout_ms=timeout_ms,
        incomplete_status=incomplete_status,
        incomplete_model=incomplete_model,
        incomplete_reason=incomplete_reason,
        diagnostics=tuple(diagnostics),
        incomplete_elapsed_ms=incomplete_elapsed_ms,
        total_elapsed_ms=(time.monotonic() - started_at) * 1000.0,
        feasibility=feasibility,
    )


def solve_bmc_property(
    formula: BmcPropertyFormula,
    *,
    timeout_ms: Optional[int] = None,
    check_incomplete: bool = True,
) -> BmcSolveResult:
    """Solve a compiled BMC property formula.

    The primary status comes from :attr:`BmcPropertyFormula.solve_formula`.
    A primary UNSAT result first checks the admissible scenario formula
    ``S_assume`` and, when necessary, localizes the failure through ``S_init``
    and ``K_N`` before exposing a property verdict.  Response suffix checks
    run only after ``S_assume`` is SAT.  All staged checks share one optional
    deadline; ``timeout_ms=None`` leaves Z3's timeout unset.

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
    budget = _SolveBudget(timeout_ms)
    started_at = time.monotonic()
    core = checked.core
    solver = z3.Solver()
    solver.add(core.domain_formula, core.transition_formula)
    solver.push()
    solver.add(core.initial_formula)
    solver.push()
    solver.add(core.environment_formula)
    solver.push()
    solver.add(checked.objective_formula)

    status, model, reason, elapsed_ms, _ = _check_with_budget(solver, budget)
    diagnostics = list(checked.diagnostics)
    if status == "sat":
        feasibility = _inferred_feasibility()
        return _make_solve_result(
            checked,
            status=status,
            model=model,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )
    if status in {"unknown", "timeout"}:
        feasibility = _not_checked_feasibility()
        diagnostics.append("feasibility_%s:primary" % status)
        return _make_solve_result(
            checked,
            status=status,
            model=model,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )

    solver.pop()  # Remove the primary objective and retain S_assume.
    (
        assumptions_status,
        assumptions_model,
        assumptions_reason,
        assumptions_elapsed,
        assumptions_started,
    ) = _check_with_budget(solver, budget)
    assumptions = _feasibility_check(
        assumptions_status,
        assumptions_reason,
        assumptions_elapsed,
        assumptions_started,
    )
    if not assumptions_started:
        feasibility = _build_feasibility(
            _stage_not_checked(),
            _stage_not_checked(),
            assumptions,
            localization_status="not_checked",
            refinement_status="not_needed",
        )
        diagnostics.append(_FEASIBILITY_TIMEOUT_BEFORE_ASSUMPTIONS)
        return _make_solve_result(
            checked,
            status=status,
            model=None,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )
    if assumptions_status in {"unknown", "timeout"}:
        feasibility = _build_feasibility(
            _stage_not_checked(),
            _stage_not_checked(),
            assumptions,
            localization_status=assumptions_status,
            refinement_status="not_needed",
        )
        diagnostics.append("feasibility_%s:assumptions" % assumptions_status)
        return _make_solve_result(
            checked,
            status=status,
            model=None,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )

    if assumptions_status == "sat":
        sat = BmcFeasibilityCheck("sat", "inferred")
        feasibility = _build_feasibility(
            sat,
            sat,
            assumptions,
            localization_status="not_needed",
            refinement_status="not_needed",
        )
        incomplete_status = None
        incomplete_model = None
        incomplete_reason = None
        incomplete_elapsed_ms = None
        if not z3.is_false(checked.incomplete_formula):
            if check_incomplete:
                solver.push()
                solver.add(checked.incomplete_formula)
                (
                    incomplete_status,
                    incomplete_model,
                    incomplete_reason,
                    incomplete_elapsed_ms,
                    incomplete_started,
                ) = _check_with_budget(solver, budget)
                solver.pop()
                if not incomplete_started:
                    incomplete_status = None
                    incomplete_model = None
                    incomplete_reason = None
                    incomplete_elapsed_ms = None
                    diagnostics.append(_SUFFIX_TIMEOUT_BEFORE_CHECK)
                else:
                    diagnostics.append(
                        "incomplete_elapsed_ms=%.3f" % incomplete_elapsed_ms
                    )
            else:
                incomplete_reason = "incomplete check disabled"
                diagnostics.append("incomplete_check=disabled")
        return _make_solve_result(
            checked,
            status=status,
            model=None,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=incomplete_status,
            incomplete_model=incomplete_model,
            incomplete_reason=incomplete_reason,
            incomplete_elapsed_ms=incomplete_elapsed_ms,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )

    # S_assume is UNSAT. Locate the first weaker unsatisfiable stage without
    # running any response suffix query.
    solver.pop()  # Remove ENV_N and retain S_init.
    (
        initialization_status,
        _,
        initialization_reason,
        initialization_elapsed,
        initialization_started,
    ) = _check_with_budget(solver, budget)
    initialization = _feasibility_check(
        initialization_status,
        initialization_reason,
        initialization_elapsed,
        initialization_started,
    )
    if not initialization_started:
        feasibility = _build_feasibility(
            _stage_not_checked(),
            initialization,
            assumptions,
            localization_status="not_checked",
            refinement_status="not_requested",
        )
        diagnostics.append(
            "feasibility_timeout:deadline_exhausted_before_initialization_check"
        )
        return _make_solve_result(
            checked,
            status=status,
            model=None,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )
    if initialization_status in {"unknown", "timeout"}:
        feasibility = _build_feasibility(
            _stage_not_checked(),
            initialization,
            assumptions,
            localization_status=initialization_status,
            refinement_status="not_requested",
        )
        diagnostics.append("feasibility_%s:initialization" % initialization_status)
        return _make_solve_result(
            checked,
            status=status,
            model=None,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )

    if initialization_status == "sat":
        sat = BmcFeasibilityCheck("sat", "inferred")
        feasibility = _build_feasibility(
            sat,
            initialization,
            assumptions,
            infeasible_stage="assumptions",
            localization_status="complete",
            refinement_status="not_requested",
        )
        return _make_solve_result(
            checked,
            status=status,
            model=None,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )

    solver.pop()  # Remove I_0 and retain K_N.
    (
        kernel_status,
        _,
        kernel_reason,
        kernel_elapsed,
        kernel_started,
    ) = _check_with_budget(solver, budget)
    kernel = _feasibility_check(
        kernel_status, kernel_reason, kernel_elapsed, kernel_started
    )
    if not kernel_started:
        feasibility = _build_feasibility(
            kernel,
            initialization,
            assumptions,
            localization_status="not_checked",
            refinement_status="not_requested",
        )
        diagnostics.append("feasibility_timeout:deadline_exhausted_before_kernel_check")
        return _make_solve_result(
            checked,
            status=status,
            model=None,
            reason=reason,
            elapsed_ms=elapsed_ms,
            timeout_ms=timeout_ms,
            incomplete_status=None,
            incomplete_model=None,
            incomplete_reason=None,
            incomplete_elapsed_ms=None,
            diagnostics=diagnostics,
            feasibility=feasibility,
            started_at=started_at,
        )
    if kernel_status in {"unknown", "timeout"}:
        feasibility = _build_feasibility(
            kernel,
            initialization,
            assumptions,
            localization_status=kernel_status,
            refinement_status="not_requested",
        )
    else:
        feasibility = _build_feasibility(
            kernel,
            initialization,
            assumptions,
            infeasible_stage="kernel" if kernel_status == "unsat" else "initialization",
            localization_status="complete",
            refinement_status="not_requested",
        )
    if kernel_status in {"unknown", "timeout"}:
        diagnostics.append("feasibility_%s:kernel" % kernel_status)
    return _make_solve_result(
        checked,
        status=status,
        model=None,
        reason=reason,
        elapsed_ms=elapsed_ms,
        timeout_ms=timeout_ms,
        incomplete_status=None,
        incomplete_model=None,
        incomplete_reason=None,
        incomplete_elapsed_ms=None,
        diagnostics=diagnostics,
        feasibility=feasibility,
        started_at=started_at,
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


def _decode_witness_trace(
    formula: BmcPropertyFormula,
    model: z3.ModelRef,
    *,
    event_policy: Optional[BmcEventDecodePolicy],
    model_role: Optional[str],
    solver_metadata: Mapping[str, Any],
    verdict: Optional[Mapping[str, Any]],
) -> BmcWitnessTrace:
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
    prop = {
        "kind": checked.kind,
        "polarity": checked.polarity,
        "bound": checked.bound,
        "case_label": checked.case_label,
        "response_window": checked.response_window,
    }
    return BmcWitnessTrace(
        property=prop,
        solver=solver_metadata,
        initial=_initial_metadata(checked, frames),
        frames=frames,
        steps=steps,
        diagnostics=checked.diagnostics,
        model_role=model_role,
        verdict=verdict,
    )


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
    solver = {
        "status": "sat",
        "reason": None,
        "incomplete_status": None,
    }
    return _decode_witness_trace(
        formula,
        model,
        event_policy=event_policy,
        model_role=None,
        solver_metadata=solver,
        verdict=None,
    )


def decode_bmc_result_trace(
    result: BmcSolveResult,
    *,
    source: str = "primary",
    event_policy: Optional[BmcEventDecodePolicy] = None,
) -> BmcWitnessTrace:
    """Decode one model channel from a structured BMC solve result.

    :param result: Structured result returned by :func:`solve_bmc_property`.
    :type result: BmcSolveResult
    :param source: Model channel, either ``"primary"`` or
        ``"incomplete_suffix"``, defaults to ``"primary"``.
    :type source: str, optional
    :param event_policy: Optional sparse event decode policy, defaults to
        ``None``.
    :type event_policy: BmcEventDecodePolicy, optional
    :return: Role-aware witness trace carrying the selected model role.
    :rtype: BmcWitnessTrace
    :raises pyfcstm.bmc.errors.BmcBuildError: If the requested model channel is
        unavailable or the result is not internally consistent.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula, compile_bmc_property
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> formula = compile_bmc_property(build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: active("Root");')))
        >>> trace = decode_bmc_result_trace(solve_bmc_property(formula))
        >>> trace.model_role
        'primary_witness'
    """
    if not isinstance(result, BmcSolveResult):
        raise BmcBuildError("result must be BmcSolveResult.")
    if source not in {"primary", "incomplete_suffix"}:
        raise BmcBuildError(
            "source must be primary or incomplete_suffix, got %r." % source
        )
    if source == "primary":
        if result.status != "sat" or result.model is None:
            raise BmcBuildError(
                "primary model channel requires a primary SAT result with a model."
            )
        role = (
            "primary_witness"
            if result.polarity == "witness"
            else "primary_counterexample"
        )
        verdict = {
            "property_satisfied": result.property_satisfied,
            "witness_found": result.witness_found,
            "counterexample_found": result.counterexample_found,
            "incomplete": result.incomplete,
            "outcome": result.outcome,
        }
        solver_metadata = {
            "model_status": "sat",
            "primary_status": result.status,
            "incomplete_status": result.incomplete_status,
            "primary_reason": result.reason,
            "incomplete_reason": result.incomplete_reason,
            "primary_elapsed_ms": result.elapsed_ms,
            "incomplete_elapsed_ms": result.incomplete_elapsed_ms,
        }
        return _decode_witness_trace(
            result.formula,
            result.model,
            event_policy=event_policy,
            model_role=role,
            solver_metadata=solver_metadata,
            verdict=verdict,
        )

    if result.kind != "response":
        raise BmcBuildError(
            "incomplete_suffix model channel requires a response result."
        )
    if result.status != "unsat":
        raise BmcBuildError("incomplete_suffix model channel requires primary UNSAT.")
    feasibility = result._validated_feasibility()
    if feasibility.scenario_infeasible:
        raise BmcBuildError(
            "scenario-infeasible results cannot expose an incomplete suffix model."
        )
    if feasibility.assumptions.status != "sat":
        raise BmcBuildError(
            "incomplete_suffix model channel requires SAT assumptions feasibility."
        )
    if not _has_nonempty_incomplete_formula(result.formula):
        raise BmcBuildError(
            "incomplete_suffix model channel requires a non-empty suffix formula."
        )
    if result.incomplete_status != "sat" or result.incomplete_model is None:
        raise BmcBuildError(
            "incomplete_suffix model channel requires a SAT suffix result."
        )
    solver_metadata = {
        "model_status": "sat",
        "primary_status": result.status,
        "incomplete_status": result.incomplete_status,
        "primary_reason": result.reason,
        "incomplete_reason": result.incomplete_reason,
        "primary_elapsed_ms": result.elapsed_ms,
        "incomplete_elapsed_ms": result.incomplete_elapsed_ms,
    }
    verdict = {
        "property_satisfied": None,
        "witness_found": False,
        "counterexample_found": False,
        "incomplete": True,
        "outcome": "incomplete",
    }
    return _decode_witness_trace(
        result.formula,
        result.incomplete_model,
        event_policy=event_policy,
        model_role="incomplete_suffix",
        solver_metadata=solver_metadata,
        verdict=verdict,
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


def _compare_step(
    mismatches: list[BmcReplayMismatch],
    witness: BmcWitnessStep,
    runtime: BmcRuntimeStep,
) -> None:
    # Absorb has a synthetic runtime observation of false, but its witness
    # Delta remains observable input and must be checked for forged payloads.
    expected_delta = witness.delta
    if expected_delta != runtime.delta:
        mismatches.append(
            BmcReplayMismatch(
                "steps[%d].delta" % witness.index,
                expected_delta,
                runtime.delta,
                "delta mismatch",
            )
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
        recorder.begin_step()
        result = runtime.cycle(step.input_event_paths)
        recorder.end_step()
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
        )
        steps.append(runtime_step)
        _compare_step(mismatches, step, runtime_step)
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
    "BmcFeasibilityCheck",
    "BmcFeasibilityRefinementCheck",
    "BmcFeasibilityResult",
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
    "decode_bmc_result_trace",
    "decode_bmc_witness",
    "replay_bmc_witness",
]

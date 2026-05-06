"""
Static (no-SMT-required-on-the-business-side) pre-checks for the SysDeSim
import / validate pipeline.

These detectors are designed to run *before* :func:`solve_sysdesim_state_coexistence`
to catch the most common modeling / scenario mistakes that surface as
``UNSAT`` from the downstream SMT layer with an opaque reason. By running them
ahead of time we can produce structured, repair-actionable diagnostics that
both humans and LLMs can use to fix the model directly.

The module contains:

* :func:`run_sysdesim_static_pre_checks` - Public Python API entry.
* :func:`detect_temporal_constraints_unsat` - Encode duration constraints +
  lifeline order in Z3, extract the unsat core to expose the exact set of
  contradicting constraints when the timing system itself is infeasible.
* :func:`detect_query_state_name_unknown` - Resolve user-provided Phase11
  query state references against the actual machine state space; if the name
  cannot be resolved, return a Levenshtein-based suggestion.
* :func:`detect_target_state_never_entered` - Verify the queried states
  actually appear in the imported scenario trace, and analyze inbound
  transitions for the missing target to explain why the scenario fails to
  drive into it.
* :func:`detect_signal_dropped_in_state` - Spot signal emissions whose
  target machine has a transition for the signal *somewhere*, but where the
  active state at emission time is not the source of any matching transition.

.. note::

   The Z3 unsat-core technique used in
   :func:`detect_temporal_constraints_unsat` follows the canonical
   ``Solver.set(unsat_core=True) + Solver.assert_and_track(...)`` pattern;
   see Microsoft's *Programming Z3* and the *z3guide* article on cores and
   satisfying subsets.

Example::

    >>> from pyfcstm.convert.sysdesim import run_sysdesim_static_pre_checks
    >>> diagnostics = run_sysdesim_static_pre_checks(
    ...     xml_path='./model.xml',
    ...     left_machine_alias='StateMachine__Control_region2',
    ...     left_state_ref='H.M',
    ...     right_machine_alias='StateMachine__Control_region3',
    ...     right_state_ref='X',
    ... )
    >>> for diag in diagnostics:  # doctest: +SKIP
    ...     print(diag.level, diag.code, diag.message)
"""

from __future__ import annotations

import re
from decimal import Decimal
from typing import Any, Dict, List, Optional, Set, Tuple

import z3

from .ir import IrDiagnostic
from .timeline_verify import (
    SysDeSimPhase10Report,
    SysDeSimTimelineMachineTrace,
    build_sysdesim_phase10_report,
)


_TIME_LITERAL_PATTERN = re.compile(
    r"^\s*(-?\d+(?:\.\d+)?)\s*(ms|s|min|h)?\s*$", re.IGNORECASE
)
_TIME_UNIT_FACTOR = {
    None: Decimal("1"),
    "": Decimal("1"),
    "s": Decimal("1"),
    "ms": Decimal("0.001"),
    "min": Decimal("60"),
    "h": Decimal("3600"),
}


def _parse_time_seconds(text: Optional[str]) -> Optional[Decimal]:
    """
    Parse a literal duration string such as ``"10s"`` into a :class:`Decimal`
    number of seconds.

    :param text: Source literal text or ``None``.
    :type text: str, optional
    :return: Parsed seconds or ``None`` if input is ``None``.
    :rtype: decimal.Decimal, optional
    :raises ValueError: If the literal cannot be parsed.
    """
    if text is None:
        return None
    match = _TIME_LITERAL_PATTERN.match(text)
    if match is None:
        raise ValueError("Unsupported time literal: {!r}".format(text))
    value = Decimal(match.group(1))
    unit_key = (match.group(2) or "").lower()
    # ``_TIME_LITERAL_PATTERN``'s second capture group restricts unit_key to one
    # of the keys present in ``_TIME_UNIT_FACTOR`` (or empty string), so the
    # lookup below cannot return ``None`` in practice. Default to seconds as a
    # belt-and-suspenders safety net.
    factor = _TIME_UNIT_FACTOR.get(unit_key, _TIME_UNIT_FACTOR[""])
    return value * factor


def _format_seconds(value: Decimal) -> str:
    """Format one :class:`Decimal` seconds value as a stable user-facing string."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        text = "0"
    return "{}s".format(text)


def _display_event_name(event) -> Optional[str]:
    """Return the modeler-visible event name (``extra_name`` when set, else ``name``)."""
    if event is None:
        return None
    extra = getattr(event, "extra_name", None)
    if extra:
        return str(extra)
    name = getattr(event, "name", None)
    if name:
        return str(name)
    return None


def _display_state_name(state) -> Optional[str]:
    """Return the modeler-visible state name (``extra_name`` when set, else ``name``)."""
    if state is None:
        return None
    extra = getattr(state, "extra_name", None)
    if extra:
        return str(extra)
    name = getattr(state, "name", None)
    if name:
        return str(name)
    return None


def _friendly_step_label(step) -> str:
    """
    Human-friendly label for one scenario step, suitable for diagnostic
    messages targeted at modelers (no internal ``sNN`` step ids leak out).

    The label is derived from the artifacts the modeler can actually see
    on the original SysDeSim sequence diagram or in the XML:

    * emit actions surface their signal name (e.g. ``"Sig9"``);
    * SetInput actions surface the assignment text (e.g. ``"y=2300"``);
    * outbound-only messages surface as ``"-->Sig"`` based on the step's
      ``outbound_signal=...`` note (ASCII arrow, terminal-safe);
    * self-messages surface as ``"self-message"``;
    * any remaining anchor step falls back to a neutral
      ``"(anchor #N)"`` marker derived from the step's order index, never
      the raw ``sNN`` step id.

    :param step: One scenario step (typically
        :class:`SysDeSimTimelineScenarioStep`).
    :return: A short, modeler-recognizable label.
    :rtype: str
    """
    for action in getattr(step, "actions", ()) or ():
        event_name = getattr(action, "event_name", None)
        if event_name:
            return str(event_name)
        input_name = getattr(action, "input_name", None)
        if input_name:
            value_text = getattr(action, "value_text", None)
            if value_text is None:
                return str(input_name)
            return "{}={}".format(input_name, value_text)
    for note in getattr(step, "notes", ()) or ():
        if isinstance(note, str) and note.startswith("outbound_signal="):
            signal = note.split("=", 1)[1].strip() or "?"
            return "-->{}".format(signal)
        if note == "self_message":
            return "self-message"
    order_index = getattr(step, "order_index", None)
    if isinstance(order_index, int):
        return "(anchor #{})".format(order_index)
    return "(anchor)"


def _levenshtein(a: str, b: str) -> int:
    """Compute the Levenshtein distance between two strings (small inputs only)."""
    if a == b:
        return 0
    if not a:
        return len(b)
    if not b:
        return len(a)
    previous = list(range(len(b) + 1))
    for i, ca in enumerate(a, 1):
        current = [i]
        for j, cb in enumerate(b, 1):
            insert_cost = current[j - 1] + 1
            delete_cost = previous[j] + 1
            replace_cost = previous[j - 1] + (0 if ca == cb else 1)
            current.append(min(insert_cost, delete_cost, replace_cost))
        previous = current
    return previous[-1]


def _candidate_state_paths_for_alias(
    phase10_report: SysDeSimPhase10Report, alias: str
) -> Tuple[str, ...]:
    """Return all known leaf-or-composite state paths for one machine alias."""
    for output in phase10_report.phase9_report.outputs:
        if output.output_name == alias:
            return tuple(
                ".".join(state.path) for state in output.machine.walk_states()
            )
    return ()


def _machine_for_alias(phase10_report: SysDeSimPhase10Report, alias: str):
    for output in phase10_report.phase9_report.outputs:
        if output.output_name == alias:
            return output.machine
    return None


def _trace_for_alias(
    phase10_report: SysDeSimPhase10Report, alias: str
) -> Optional[SysDeSimTimelineMachineTrace]:
    for trace in phase10_report.traces:
        if trace.machine_alias == alias:
            return trace
    return None


def _state_in_trace(trace: SysDeSimTimelineMachineTrace, state_path: str) -> bool:
    """Whether *state_path* appears anywhere in this region's trace."""
    if trace.initial_state_path == state_path:
        return True
    for step in trace.steps:
        if step.post_state_path == state_path or step.stabilized_state_path == state_path:
            return True
    for window in trace.state_windows:
        if window.state_path == state_path:
            return True
    return False


def _resolve_state_path(machine, state_ref: str) -> Optional[str]:
    """Mirror of :func:`timeline_verify._resolve_state_path` returning ``None`` on miss."""
    if machine is None:
        return None
    ref_tokens = tuple(t for t in state_ref.split(".") if t)
    path_candidates: List[str] = []
    suffix_candidates: List[str] = []
    for state in machine.walk_states():
        path_tokens = tuple(state.path)
        path_name = ".".join(path_tokens)
        if state_ref == path_name or state_ref == ".".join(state.path[1:]):
            return path_name
        if (
            len(ref_tokens) >= 2
            and len(ref_tokens) <= len(path_tokens)
            and path_tokens[-len(ref_tokens):] == ref_tokens
        ):
            suffix_candidates.append(path_name)
        if state.name == state_ref:
            path_candidates.append(path_name)
    if len(path_candidates) == 1:
        return path_candidates[0]
    if len(suffix_candidates) == 1:
        return suffix_candidates[0]
    return None


# =============================================================================
# Detector: temporal_constraints_unsat (Z3 unsat-core based)
# =============================================================================


def detect_temporal_constraints_unsat(
    phase10_report: SysDeSimPhase10Report,
) -> List[IrDiagnostic]:
    """
    Detect contradictions among DurationConstraint / TimeConstraint / lifeline
    order using Z3 with unsat-core extraction.

    The detector encodes the imported scenario as a system of linear
    inequalities over Z3 ``Real`` variables (one per step time symbol). Each
    duration constraint and each implicit lifeline-order edge is asserted via
    :py:meth:`z3.Solver.assert_and_track` so that the solver can report a
    minimal unsatisfiable subset. When the subset is non-empty we surface a
    structured ``error``-level diagnostic listing exactly which constraints
    cause the timing system to be infeasible, plus repair hints derived from
    the most common attribution mistakes seen in real models.

    :param phase10_report: Phase10 report produced by the import pipeline.
    :type phase10_report: SysDeSimPhase10Report
    :return: List of diagnostics; empty if the timing system is satisfiable.
    :rtype: list[IrDiagnostic]
    """
    scenario = phase10_report.scenario
    steps = scenario.steps
    if not steps:
        return []

    step_labels: Dict[str, str] = {
        step.step_id: _friendly_step_label(step) for step in steps
    }

    solver = z3.Solver()
    solver.set(unsat_core=True)

    time_vars: Dict[str, z3.ArithRef] = {}
    for step in steps:
        var = z3.Real(step.time_symbol)
        time_vars[step.step_id] = var
        solver.add(var >= 0)

    # Per-constraint metadata so we can render the FULL bound expression
    # ("0s <= t(R) - t(L) <= 10s" / "t(R) - t(L) == 1s" / etc.) instead of
    # one half-bound per row in the unsat core display.
    constraint_meta: Dict[str, Dict[str, Any]] = {}
    track_to_payload: Dict[str, Dict[str, Any]] = {}

    for previous_step, next_step in zip(steps, steps[1:]):
        track_name = "lifeline:{}->{}".format(previous_step.step_id, next_step.step_id)
        solver.assert_and_track(
            time_vars[next_step.step_id] >= time_vars[previous_step.step_id],
            track_name,
        )
        track_to_payload[track_name] = {
            "kind": "lifeline_order",
            "left_label": step_labels[previous_step.step_id],
            "right_label": step_labels[next_step.step_id],
            "expression": "t({left}) <= t({right})".format(
                left=step_labels[previous_step.step_id],
                right=step_labels[next_step.step_id],
            ),
        }

    for constraint in scenario.temporal_constraints:
        left_var = time_vars.get(constraint.left_step_id)
        right_var = time_vars.get(constraint.right_step_id)
        if left_var is None or right_var is None:
            continue
        try:
            min_seconds = _parse_time_seconds(constraint.min_seconds_text)
            max_seconds = _parse_time_seconds(constraint.max_seconds_text)
        except ValueError:
            continue
        left_label = step_labels.get(
            constraint.left_step_id, constraint.left_step_id
        )
        right_label = step_labels.get(
            constraint.right_step_id, constraint.right_step_id
        )
        diff = right_var - left_var
        if min_seconds is not None:
            track_name = "lo:{}".format(constraint.constraint_id)
            if constraint.strict_lower:
                solver.assert_and_track(diff > z3.RealVal(str(min_seconds)), track_name)
            else:
                solver.assert_and_track(
                    diff >= z3.RealVal(str(min_seconds)), track_name
                )
            track_to_payload[track_name] = {
                "kind": "duration_lower_bound",
                "constraint_id": constraint.constraint_id,
            }
        if max_seconds is not None:
            track_name = "hi:{}".format(constraint.constraint_id)
            solver.assert_and_track(diff <= z3.RealVal(str(max_seconds)), track_name)
            track_to_payload[track_name] = {
                "kind": "duration_upper_bound",
                "constraint_id": constraint.constraint_id,
            }
        constraint_meta[constraint.constraint_id] = {
            "constraint_id": constraint.constraint_id,
            "constraint_kind": constraint.kind,
            "left_label": left_label,
            "right_label": right_label,
            "min_seconds": min_seconds,
            "max_seconds": max_seconds,
            "strict_lower": constraint.strict_lower,
            "expression": _format_duration_expression(
                left_label, right_label, min_seconds, max_seconds, constraint.strict_lower
            ),
        }

    check_result = solver.check()
    if check_result != z3.unsat:
        return []

    raw_core = solver.unsat_core()
    core_names = sorted(str(item) for item in raw_core)

    # Group unsat-core entries: lifeline order edges keep one row each;
    # duration constraints get folded into one row per constraint_id so
    # we render the full bound expression rather than half a bound.
    lifeline_rows: List[Dict[str, Any]] = []
    duration_constraint_ids: List[str] = []
    seen_constraint_ids: Set[str] = set()
    for track_name in core_names:
        payload = track_to_payload.get(track_name)
        if payload is None:  # pragma: no cover - defensive
            continue
        if payload["kind"] == "lifeline_order":
            lifeline_rows.append(payload)
        else:
            cid = payload["constraint_id"]
            if cid not in seen_constraint_ids:
                seen_constraint_ids.add(cid)
                duration_constraint_ids.append(cid)

    duration_rows = [constraint_meta[cid] for cid in duration_constraint_ids]
    related_messages: List[str] = sorted(
        {row["left_label"] for row in duration_rows + lifeline_rows}
        | {row["right_label"] for row in duration_rows + lifeline_rows}
    )

    suggestion_constraint_id: Optional[str] = None
    suggestion_reason: Optional[str] = None
    if duration_rows:
        # Heuristic: pick the equality DurationConstraint with the smallest
        # bound — empirically this is the constraint most often mis-attached
        # by modelers (a tight ``{1s}`` bracket placed on the wrong pair of
        # messages). It is the cheapest one to investigate first.
        equalities = [
            row
            for row in duration_rows
            if row["min_seconds"] is not None
            and row["max_seconds"] is not None
            and row["min_seconds"] == row["max_seconds"]
        ]
        if equalities:
            equalities.sort(key=lambda r: r["min_seconds"])
            tight = equalities[0]
            suggestion_constraint_id = tight["constraint_id"]
            suggestion_reason = (
                "DurationConstraint `{cid}` (== {bound}) bridges messages "
                "`{left}` and `{right}` on the sequence diagram; verify whether "
                "its two endpoints were dragged onto the intended "
                "MessageOccurrence specifications. Tight equality brackets "
                "attached to the wrong pair of messages are the single most "
                "common cause of contradictory timing systems in SysDeSim "
                "exports.".format(
                    cid=suggestion_constraint_id,
                    bound=_format_seconds(tight["min_seconds"]),
                    left=tight["left_label"],
                    right=tight["right_label"],
                )
            )

    hints: List[str] = []
    if suggestion_reason:
        hints.append(suggestion_reason)
    hints.append(
        "Or: re-check the top-to-bottom lifeline ordering of messages "
        + ", ".join("`{}`".format(label) for label in related_messages)
        + " on the sequence diagram. Their visual order implies a non-negative "
        + "delta that may conflict with one of the duration constraints above. "
        + "Reordering the messages is sometimes the right fix instead of "
        + "relaxing a duration value."
    )
    hints.append(
        "Run `pyfcstm sysdesim validate -i <xml> --report-file <out.json>` to "
        "inspect every temporal constraint individually before editing."
    )

    total_entries = len(duration_rows) + len(lifeline_rows)
    message_lines = [
        "Imported scenario timing constraints are mutually unsatisfiable.",
        "Z3 unsat core (minimal contradicting set, {} entr{}):".format(
            total_entries, "y" if total_entries == 1 else "ies"
        ),
    ]
    for row in duration_rows:
        message_lines.append(
            "  - {expr}    (DurationConstraint id={cid})".format(
                expr=row["expression"], cid=row["constraint_id"]
            )
        )
    for row in lifeline_rows:
        message_lines.append("  - lifeline order:  {expr}".format(expr=row["expression"]))

    diagnostic = IrDiagnostic(
        level="error",
        code="temporal_constraints_unsat",
        message="\n".join(message_lines),
        source_id=duration_constraint_ids[0] if duration_constraint_ids else None,
        details={
            "method": "z3_unsat_core",
            "involved_constraint_ids": sorted(duration_constraint_ids),
            "involved_messages": related_messages,
            "duration_rows": duration_rows,
            "lifeline_rows": lifeline_rows,
            "suggested_first_culprit_constraint_id": suggestion_constraint_id,
        },
        hints=hints,
    )
    return [diagnostic]


def _format_duration_expression(
    left_label: str,
    right_label: str,
    min_seconds: Optional[Decimal],
    max_seconds: Optional[Decimal],
    strict_lower: bool,
) -> str:
    """
    Render one DurationConstraint as a single human-readable inequality.

    Output forms (rounded for readability, no internal step IDs):

    * ``min == max``: ``t(R) - t(L) == 10s``
    * ``min < max``: ``0s <= t(R) - t(L) <= 10s`` (with ``<`` if the lower
      bound is strict)
    * only ``min`` set: ``t(R) - t(L) >= 5s`` (or ``> 5s`` when strict)
    * only ``max`` set: ``t(R) - t(L) <= 10s``

    :param left_label: Friendly label for the left endpoint.
    :type left_label: str
    :param right_label: Friendly label for the right endpoint.
    :type right_label: str
    :param min_seconds: Lower bound in seconds, or ``None`` if unbounded below.
    :type min_seconds: decimal.Decimal, optional
    :param max_seconds: Upper bound in seconds, or ``None`` if unbounded above.
    :type max_seconds: decimal.Decimal, optional
    :param strict_lower: Whether the lower bound is a strict ``>`` (otherwise ``>=``).
    :type strict_lower: bool
    :return: A single-line inequality string.
    :rtype: str
    """
    diff_text = "t({}) - t({})".format(right_label, left_label)
    if min_seconds is not None and max_seconds is not None:
        if min_seconds == max_seconds and not strict_lower:
            return "{diff} == {bound}".format(
                diff=diff_text, bound=_format_seconds(min_seconds)
            )
        lo_op = "<" if strict_lower else "<="
        return "{lo} {lo_op} {diff} <= {hi}".format(
            lo=_format_seconds(min_seconds),
            lo_op=lo_op,
            diff=diff_text,
            hi=_format_seconds(max_seconds),
        )
    if min_seconds is not None:  # pragma: no cover - both bounds always present in real exports
        op = ">" if strict_lower else ">="
        return "{diff} {op} {bound}".format(
            diff=diff_text, op=op, bound=_format_seconds(min_seconds)
        )
    if max_seconds is not None:  # pragma: no cover - both bounds always present in real exports
        return "{diff} <= {bound}".format(
            diff=diff_text, bound=_format_seconds(max_seconds)
        )
    return "{diff} (unbounded)".format(diff=diff_text)  # pragma: no cover - never emitted


# =============================================================================
# Detector: query_state_name_unknown
# =============================================================================


def detect_query_state_name_unknown(
    phase10_report: SysDeSimPhase10Report,
    *,
    left_machine_alias: Optional[str] = None,
    left_state_ref: Optional[str] = None,
    right_machine_alias: Optional[str] = None,
    right_state_ref: Optional[str] = None,
) -> List[IrDiagnostic]:
    """
    Validate that user-provided Phase11 query state references actually
    resolve in the chosen machine's state space. Surface Levenshtein-based
    suggestions for misspellings.

    :param phase10_report: Phase10 report.
    :type phase10_report: SysDeSimPhase10Report
    :param left_machine_alias: Left machine alias for the query, defaults to ``None``.
    :type left_machine_alias: str, optional
    :param left_state_ref: Left state reference, defaults to ``None``.
    :type left_state_ref: str, optional
    :param right_machine_alias: Right machine alias for the query, defaults to ``None``.
    :type right_machine_alias: str, optional
    :param right_state_ref: Right state reference, defaults to ``None``.
    :type right_state_ref: str, optional
    :return: List of diagnostics; empty if both refs resolve cleanly.
    :rtype: list[IrDiagnostic]
    """
    diagnostics: List[IrDiagnostic] = []
    pairs = [
        ("left", left_machine_alias, left_state_ref),
        ("right", right_machine_alias, right_state_ref),
    ]
    for side, alias, ref in pairs:
        if alias is None or ref is None:
            continue
        machine = _machine_for_alias(phase10_report, alias)
        if machine is None:
            continue
        resolved = _resolve_state_path(machine, ref)
        if resolved is not None:
            continue
        candidates = _candidate_state_paths_for_alias(phase10_report, alias)
        suggestions = sorted(
            candidates,
            key=lambda path: (
                _levenshtein(ref.lower(), path.split(".")[-1].lower()),
                _levenshtein(ref.lower(), path.lower()),
            ),
        )[:3]
        diagnostics.append(
            IrDiagnostic(
                level="error",
                code="query_state_name_unknown",
                message=(
                    "{side} state reference {ref!r} cannot be resolved against "
                    "machine {alias!r}.".format(side=side.title(), ref=ref, alias=alias)
                ),
                source_id=alias,
                details={
                    "side": side,
                    "machine_alias": alias,
                    "state_ref": ref,
                    "available_states": list(candidates),
                    "closest_matches": suggestions,
                },
                hints=[
                    "Did you mean: {}?".format(", ".join(suggestions))
                    if suggestions
                    else "No close match found; check the machine alias as well.",
                    "All resolvable state names for {alias}: {names}.".format(
                        alias=alias, names=", ".join(candidates) or "(none)"
                    ),
                ],
            )
        )
    return diagnostics


# =============================================================================
# Detector: target_state_never_entered
# =============================================================================


def detect_target_state_never_entered(
    phase10_report: SysDeSimPhase10Report,
    *,
    left_machine_alias: Optional[str] = None,
    left_state_ref: Optional[str] = None,
    right_machine_alias: Optional[str] = None,
    right_state_ref: Optional[str] = None,
) -> List[IrDiagnostic]:
    """
    Verify that the queried target states actually appear in the imported
    scenario trace. When a target is missing, analyze inbound transitions to
    explain why the scenario fails to drive the region into that state.

    :param phase10_report: Phase10 report.
    :type phase10_report: SysDeSimPhase10Report
    :param left_machine_alias: Left machine alias for the query, defaults to ``None``.
    :type left_machine_alias: str, optional
    :param left_state_ref: Left state reference, defaults to ``None``.
    :type left_state_ref: str, optional
    :param right_machine_alias: Right machine alias for the query, defaults to ``None``.
    :type right_machine_alias: str, optional
    :param right_state_ref: Right state reference, defaults to ``None``.
    :type right_state_ref: str, optional
    :return: List of diagnostics; empty if both targets occur in the trace.
    :rtype: list[IrDiagnostic]
    """
    diagnostics: List[IrDiagnostic] = []
    pairs = [
        ("left", left_machine_alias, left_state_ref),
        ("right", right_machine_alias, right_state_ref),
    ]
    for side, alias, ref in pairs:
        if alias is None or ref is None:
            continue
        machine = _machine_for_alias(phase10_report, alias)
        trace = _trace_for_alias(phase10_report, alias)
        if machine is None or trace is None:
            continue
        resolved = _resolve_state_path(machine, ref)
        if resolved is None:
            # query_state_name_unknown already covers this.
            continue
        if _state_in_trace(trace, resolved):
            continue
        analysis = _analyze_unreachability(machine, trace, resolved, phase10_report)
        diagnostics.append(
            IrDiagnostic(
                level="error",
                code="target_state_never_entered",
                message=(
                    "{side} target state {state!r} (machine {alias!r}) "
                    "is never entered in the imported scenario.".format(
                        side=side.title(), state=resolved, alias=alias
                    )
                ),
                source_id=alias,
                details={
                    "side": side,
                    "machine_alias": alias,
                    "state_path": resolved,
                    "inbound_transitions": analysis["inbound_transitions"],
                    "trigger_signal_emit_steps": analysis["trigger_signal_emit_steps"],
                    "states_visited": analysis["states_visited"],
                },
                hints=analysis["hints"],
            )
        )
    return diagnostics


def _analyze_unreachability(
    machine,
    trace: SysDeSimTimelineMachineTrace,
    target_state_path: str,
    phase10_report: SysDeSimPhase10Report,
) -> Dict[str, Any]:
    """
    Build a structured why-not-reached analysis for one target state.

    Identifies inbound transitions to the target state and inspects, for each
    such transition T, whether T's trigger signal was emitted in the scenario
    and whether the region was in T's source state at the moment of emission.
    """
    inbound: List[Dict[str, Any]] = []
    for state in machine.walk_states():
        for tr in state.transitions:
            target_name = getattr(tr, "to_state", None)
            if not isinstance(target_name, str):  # pragma: no cover - defensive
                # Pseudostate / SingletonMark targets like ``[*]`` are not
                # interesting for unreachability analysis; skip them safely.
                continue
            if not target_state_path.endswith(target_name):
                continue
            event = getattr(tr, "event", None)
            event_internal_name = getattr(event, "name", None) if event else None
            event_display_name = _display_event_name(event)
            from_name = getattr(tr, "from_state", None)
            if not isinstance(from_name, str):  # pragma: no cover - defensive
                continue
            inbound.append(
                {
                    "from_state_local": from_name,
                    "owning_composite_path": ".".join(state.path),
                    "to_state_local": target_name,
                    "trigger_event_name": event_internal_name,
                    "trigger_signal_name": event_display_name,
                }
            )

    state_at_step: Dict[str, str] = {}
    for step in trace.steps:
        state_at_step[step.step_id] = step.pre_state_path
    step_label_by_id: Dict[str, str] = {
        step.step_id: _friendly_step_label(step)
        for step in phase10_report.scenario.steps
    }

    states_visited = sorted(
        {trace.initial_state_path}
        | {step.post_state_path for step in trace.steps if step.post_state_path}
        | {step.stabilized_state_path for step in trace.steps if step.stabilized_state_path}
        | {window.state_path for window in trace.state_windows}
    )

    trigger_emit_records: List[Dict[str, Any]] = []
    for inbound_entry in inbound:
        trigger_name = inbound_entry["trigger_event_name"]
        if not trigger_name:  # pragma: no cover - completion-only inbound has no signal to emit
            # Inbound transitions without an explicit trigger (UML completion
            # transitions) cannot be exercised by emitting a signal — they
            # fire automatically once the source state is reached. They are
            # handled implicitly by the source's reachability check.
            continue
        for scen_step in phase10_report.scenario.steps:
            actions = getattr(scen_step, "actions", ()) or ()
            for action in actions:
                event_name = getattr(action, "event_name", None)
                if not event_name:
                    continue
                if event_name.lower() != trigger_name.lower():
                    continue
                pre_state = state_at_step.get(scen_step.step_id, trace.initial_state_path)
                expected_source_local = inbound_entry["from_state_local"]
                expected_source_path_options = [
                    expected_source_local,
                    "{}.{}".format(
                        inbound_entry["owning_composite_path"], expected_source_local
                    ),
                ]
                ok = pre_state.endswith(
                    "." + expected_source_local
                ) or pre_state == expected_source_local or pre_state in expected_source_path_options
                trigger_emit_records.append(
                    {
                        "step_label": step_label_by_id.get(
                            scen_step.step_id, _friendly_step_label(scen_step)
                        ),
                        "trigger_signal_name": inbound_entry.get(
                            "trigger_signal_name"
                        )
                        or trigger_name,
                        "expected_source_state": expected_source_local,
                        "actual_pre_state": pre_state,
                        "did_fire": ok,
                    }
                )
                break

    hints: List[str] = []
    if not inbound:
        hints.append(
            "No transition in machine `{alias}` targets state `{state}`; the "
            "state may be structurally unreachable in the model itself "
            "(dead state).".format(
                alias=trace.machine_alias, state=target_state_path
            )
        )
    else:
        if not trigger_emit_records:
            trigger_signals = sorted(
                {
                    inbound_entry.get("trigger_signal_name")
                    or inbound_entry.get("trigger_event_name")
                    or "(none)"
                    for inbound_entry in inbound
                }
            )
            hints.append(
                "Inbound transitions exist via signals {triggers}, but none of "
                "those signals were emitted by the imported scenario. Add a "
                "message for one such signal on the sequence diagram (or check "
                "the signal-name spelling).".format(
                    triggers=", ".join("`{}`".format(s) for s in trigger_signals)
                )
            )
        else:
            dropped = [r for r in trigger_emit_records if not r["did_fire"]]
            if dropped:
                first = dropped[0]
                hints.append(
                    "Signal `{sig}` was emitted at message `{step}`, but the "
                    "region was in state `{actual}` at that moment, not the "
                    "required source state `{expected}`. The signal was "
                    "silently dropped; either reorder messages on the sequence "
                    "diagram so the prerequisite transition fires first, or add "
                    "the missing prerequisite signal before this message."
                    .format(
                        sig=first["trigger_signal_name"],
                        step=first["step_label"],
                        actual=first["actual_pre_state"],
                        expected=first["expected_source_state"],
                    )
                )

    return {
        "inbound_transitions": inbound,
        "trigger_signal_emit_steps": trigger_emit_records,
        "states_visited": states_visited,
        "hints": hints,
    }


# =============================================================================
# Detector: signal_dropped_in_state (warning level)
# =============================================================================


def detect_signal_dropped_in_state(
    phase10_report: SysDeSimPhase10Report,
) -> List[IrDiagnostic]:
    """
    Surface ``warning``-level diagnostics for signals that were emitted in
    the scenario but not consumed by any transition in the machine where the
    signal *can* be consumed (i.e. the machine has a transition for the
    signal somewhere, just not from the active state at emit time).

    :param phase10_report: Phase10 report.
    :type phase10_report: SysDeSimPhase10Report
    :return: List of warning diagnostics, possibly empty.
    :rtype: list[IrDiagnostic]
    """
    diagnostics: List[IrDiagnostic] = []
    for output in phase10_report.phase9_report.outputs:
        machine = output.machine
        alias = output.output_name
        trace = _trace_for_alias(phase10_report, alias)
        if trace is None:  # pragma: no cover - every Phase9 output produces a Phase10 trace
            continue
        signal_to_sources: Dict[str, List[Tuple[str, str]]] = {}
        signal_display_names: Dict[str, str] = {}
        for state in machine.walk_states():
            for tr in state.transitions:
                event = getattr(tr, "event", None)
                event_name = getattr(event, "name", None) if event else None
                from_name = getattr(tr, "from_state", None)
                to_name = getattr(tr, "to_state", None)
                if not isinstance(event_name, str):  # pragma: no cover - defensive
                    continue
                if not isinstance(from_name, str) or not isinstance(to_name, str):  # pragma: no cover - defensive
                    continue
                key = event_name.lower()
                signal_to_sources.setdefault(key, []).append((from_name, to_name))
                if key not in signal_display_names:
                    signal_display_names[key] = (
                        _display_event_name(event) or event_name
                    )

        if not signal_to_sources:  # pragma: no cover - main shell + region outputs always carry events here
            continue

        step_label_by_id = {
            step.step_id: _friendly_step_label(step)
            for step in phase10_report.scenario.steps
        }
        state_at_step = {step.step_id: step.pre_state_path for step in trace.steps}
        for scen_step in phase10_report.scenario.steps:
            actions = getattr(scen_step, "actions", ()) or ()
            for action in actions:
                event_name = getattr(action, "event_name", None)
                if not isinstance(event_name, str):
                    continue
                lookup = signal_to_sources.get(event_name.lower())
                if not lookup:
                    continue
                pre_state = state_at_step.get(scen_step.step_id, trace.initial_state_path)
                source_locals = sorted({src for src, _ in lookup})
                pre_path_tokens = pre_state.split(".") if pre_state else []
                # A signal can be consumed if any source-state is the active
                # state itself or an ancestor (for force-transitions like
                # ``! Composite -> X`` defined on a parent composite).
                consumed = any(src in pre_path_tokens for src in source_locals)
                if consumed:
                    continue
                signal_display = signal_display_names.get(
                    event_name.lower(), event_name
                )
                step_label = step_label_by_id.get(
                    scen_step.step_id, _friendly_step_label(scen_step)
                )
                diagnostics.append(
                    IrDiagnostic(
                        level="warning",
                        code="signal_dropped_in_state",
                        message=(
                            "Signal `{sig}` emitted at message `{step}` was "
                            "silently dropped in machine `{alias}` "
                            "(active state was `{pre}`; transitions for this "
                            "signal exist only from {srcs}).".format(
                                sig=signal_display,
                                step=step_label,
                                alias=alias,
                                pre=pre_state,
                                srcs=", ".join(
                                    "`{}`".format(s) for s in source_locals
                                ),
                            )
                        ),
                        source_id=alias,
                        details={
                            "machine_alias": alias,
                            "step_label": step_label,
                            "signal": signal_display,
                            "pre_state_path": pre_state,
                            "transition_source_states": source_locals,
                        },
                        hints=[
                            "If signal `{sig}` was meant to advance machine "
                            "`{alias}`, make sure the region is in {srcs} "
                            "before this message (by emitting the prerequisite "
                            "signal first or moving this message later on the "
                            "sequence diagram).".format(
                                sig=signal_display,
                                alias=alias,
                                srcs=" or ".join(
                                    "`{}`".format(s) for s in source_locals
                                ),
                            ),
                            "If `{sig}` genuinely targets a different "
                            "machine, ignore this warning — it is an "
                            "informational hint.".format(sig=signal_display),
                        ],
                    )
                )
    return diagnostics


# =============================================================================
# Public API
# =============================================================================


def run_sysdesim_static_pre_checks(
    *,
    xml_path: Optional[str] = None,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
    left_machine_alias: Optional[str] = None,
    left_state_ref: Optional[str] = None,
    right_machine_alias: Optional[str] = None,
    right_state_ref: Optional[str] = None,
    phase10_report: Optional[SysDeSimPhase10Report] = None,
) -> List[IrDiagnostic]:
    """
    Run all static pre-checks against a SysDeSim XML or pre-built Phase10 report.

    Either *xml_path* or *phase10_report* must be provided. When *phase10_report*
    is omitted, the function will internally invoke
    :func:`build_sysdesim_phase10_report` against *xml_path*.

    :param xml_path: SysDeSim XML path, optional if ``phase10_report`` is given.
    :type xml_path: str, optional
    :param machine_name: Optional machine name selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration.
    :type tick_duration_ms: float, optional
    :param left_machine_alias: Optional left machine alias (Phase11 query).
    :type left_machine_alias: str, optional
    :param left_state_ref: Optional left state ref (Phase11 query).
    :type left_state_ref: str, optional
    :param right_machine_alias: Optional right machine alias (Phase11 query).
    :type right_machine_alias: str, optional
    :param right_state_ref: Optional right state ref (Phase11 query).
    :type right_state_ref: str, optional
    :param phase10_report: Pre-built Phase10 report. Bypasses XML import.
    :type phase10_report: SysDeSimPhase10Report, optional
    :return: Diagnostics produced by all detectors, in stable detector order.
    :rtype: list[IrDiagnostic]
    :raises ValueError: If neither ``xml_path`` nor ``phase10_report`` is given.

    Example::

        >>> diagnostics = run_sysdesim_static_pre_checks(
        ...     xml_path='./model.xml',
        ...     left_machine_alias='StateMachine__Control_region2',
        ...     left_state_ref='H.M',
        ...     right_machine_alias='StateMachine__Control_region3',
        ...     right_state_ref='X',
        ... )
        >>> any(d.level == 'error' for d in diagnostics)  # doctest: +SKIP
        True
    """
    if phase10_report is None:
        if xml_path is None:
            raise ValueError("Either xml_path or phase10_report must be provided.")
        phase10_report = build_sysdesim_phase10_report(
            xml_path,
            machine_name=machine_name,
            interaction_name=interaction_name,
            tick_duration_ms=tick_duration_ms,
        )

    diagnostics: List[IrDiagnostic] = []
    diagnostics.extend(detect_temporal_constraints_unsat(phase10_report))
    diagnostics.extend(
        detect_query_state_name_unknown(
            phase10_report,
            left_machine_alias=left_machine_alias,
            left_state_ref=left_state_ref,
            right_machine_alias=right_machine_alias,
            right_state_ref=right_state_ref,
        )
    )
    diagnostics.extend(
        detect_target_state_never_entered(
            phase10_report,
            left_machine_alias=left_machine_alias,
            left_state_ref=left_state_ref,
            right_machine_alias=right_machine_alias,
            right_state_ref=right_state_ref,
        )
    )
    diagnostics.extend(detect_signal_dropped_in_state(phase10_report))
    diagnostics.extend(detect_signal_in_uninitialized_window(phase10_report))
    return diagnostics


# =============================================================================
# Detector: signal_in_uninitialized_window (warning level)
# =============================================================================


def detect_signal_in_uninitialized_window(
    phase10_report: SysDeSimPhase10Report,
) -> List[IrDiagnostic]:
    """
    Surface ``warning``-level diagnostics for signals (inbound or outbound)
    that fire at a scenario step before every input variable required by
    every region of the machine has been observed at least once.

    Phase 10 trace replay applies strict-init semantics: variables not yet
    bound by a ``SetInput`` action are kept as ``NaN`` so guards that
    reference them evaluate to ``False`` (no transition fires on a default
    ``0.0`` proxy). A signal that arrives in this "uninitialized window" is
    therefore *steering the machines under partial knowledge*. The detector
    flags each such signal so the modeler can decide whether to (a) move the
    relevant ``SetInput`` invariants earlier on the sequence diagram, or (b)
    accept the warning as intentional.

    :param phase10_report: Phase10 report.
    :type phase10_report: SysDeSimPhase10Report
    :return: List of warning diagnostics, possibly empty.
    :rtype: list[IrDiagnostic]
    """
    diagnostics: List[IrDiagnostic] = []

    # Required scenario-side input names per machine alias.
    required_per_machine: Dict[str, Set[str]] = {
        binding.machine_alias: set(binding.input_map.keys())
        for binding in phase10_report.bindings
    }
    if not any(required_per_machine.values()):
        return diagnostics

    initialized_per_machine: Dict[str, Set[str]] = {
        alias: set() for alias in required_per_machine
    }

    def _step_signal_label(step) -> Optional[str]:
        """Pick a human-friendly label for the signal carried by *step*."""
        for action in getattr(step, "actions", ()) or ():
            event_name = getattr(action, "event_name", None)
            if event_name:
                return "emit({})".format(event_name)
        for note in getattr(step, "notes", ()) or ():
            if isinstance(note, str) and note.startswith("outbound_signal="):
                signal = note.split("=", 1)[1].strip()
                if signal:
                    return "{}-->".format(signal)
        return None

    for step in phase10_report.scenario.steps:
        # 1. Apply SetInput actions (record what just got initialized).
        set_input_names = set()
        for action in getattr(step, "actions", ()) or ():
            if getattr(action, "kind", None) == "set_input":
                input_name = getattr(action, "input_name", None)
                if isinstance(input_name, str) and input_name:
                    set_input_names.add(input_name)
        for alias, required in required_per_machine.items():
            initialized_per_machine[alias].update(set_input_names & required)

        # 2. Check whether this step carries a signal.
        signal_label = _step_signal_label(step)
        if signal_label is None:
            continue

        # 3. List machines whose required inputs are not all bound yet.
        unmet_rows: List[Tuple[str, List[str]]] = []
        for alias, required in required_per_machine.items():
            missing = required - initialized_per_machine[alias]
            if missing:
                unmet_rows.append((alias, sorted(missing)))
        if not unmet_rows:
            continue

        # 4. Emit the warning.
        unmet_text = ", ".join(
            "{alias} (missing: {missing})".format(
                alias=alias, missing=", ".join(missing)
            )
            for alias, missing in unmet_rows
        )
        diagnostics.append(
            IrDiagnostic(
                level="warning",
                code="signal_in_uninitialized_window",
                message=(
                    "Signal `{label}` at scenario step `{step}` arrives before "
                    "every required scenario input has been observed in the "
                    "imported trajectory. Strict-init semantics keep "
                    "uninitialized variables at NaN, so any guard that "
                    "references one of them silently evaluates to False; "
                    "transitions gated by such a guard will not fire here. "
                    "Affected machines: {unmet}".format(
                        label=signal_label,
                        step=step.step_id,
                        unmet=unmet_text,
                    )
                ),
                source_id=step.step_id,
                details={
                    "step_id": step.step_id,
                    "signal_label": signal_label,
                    "missing_inputs_per_machine": [
                        {"machine_alias": alias, "missing_inputs": missing}
                        for alias, missing in unmet_rows
                    ],
                },
                hints=[
                    "If the missing inputs are meant to be set before this "
                    "signal, drag the corresponding `name=value` "
                    "StateInvariant marker(s) above this message on the "
                    "sequence diagram.",
                    "If the signal is genuinely meant to fire under partial "
                    "knowledge (e.g. an external trigger that does not depend "
                    "on those variables), this warning is informational.",
                ],
            )
        )
    return diagnostics


__all__ = [
    "detect_query_state_name_unknown",
    "detect_signal_dropped_in_state",
    "detect_signal_in_uninitialized_window",
    "detect_target_state_never_entered",
    "detect_temporal_constraints_unsat",
    "run_sysdesim_static_pre_checks",
]

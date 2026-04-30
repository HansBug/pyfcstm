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
from typing import Any, Dict, Iterable, List, Mapping, Optional, Sequence, Set, Tuple

import z3

from .ir import IrDiagnostic
from .timeline_verify import (
    SysDeSimNormalizedTemporalConstraint,
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
    factor = _TIME_UNIT_FACTOR.get(unit_key)
    if factor is None:
        raise ValueError("Unsupported time unit in literal: {!r}".format(text))
    return value * factor


def _format_seconds(value: Decimal) -> str:
    """Format one :class:`Decimal` seconds value as a stable user-facing string."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        text = "0"
    return "{}s".format(text)


def _step_event_label(step) -> Optional[str]:
    """Best-effort human label for the action a step performs (emit / set-input)."""
    actions = getattr(step, "actions", ())
    if not actions:
        return None
    for action in actions:
        event_name = getattr(action, "event_name", None)
        if event_name:
            return event_name
        input_name = getattr(action, "input_name", None)
        if input_name:
            return input_name
    return None


def _format_constraint_text(
    constraint: SysDeSimNormalizedTemporalConstraint,
    step_labels: Mapping[str, Optional[str]],
) -> str:
    """Render a duration constraint as ``t(Sig9) -> t(Sig6) in [10s, 10s]``."""
    lhs_label = step_labels.get(constraint.left_step_id) or constraint.left_step_id
    rhs_label = step_labels.get(constraint.right_step_id) or constraint.right_step_id
    pieces = []
    if constraint.min_seconds_text is not None:
        pieces.append(
            "{} {}".format(">" if constraint.strict_lower else ">=", constraint.min_seconds_text)
        )
    if constraint.max_seconds_text is not None:
        pieces.append("<= {}".format(constraint.max_seconds_text))
    bound_text = " AND ".join(pieces) if pieces else "(unbounded)"
    return "t({}) - t({}) {}  [step {} -> step {}, kind={}]".format(
        rhs_label,
        lhs_label,
        bound_text,
        constraint.left_step_id,
        constraint.right_step_id,
        constraint.kind,
    )


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

    step_labels: Dict[str, Optional[str]] = {
        step.step_id: _step_event_label(step) for step in steps
    }
    step_index: Dict[str, int] = {step.step_id: idx for idx, step in enumerate(steps)}

    solver = z3.Solver()
    solver.set(unsat_core=True)

    time_vars: Dict[str, z3.ArithRef] = {}
    for step in steps:
        var = z3.Real(step.time_symbol)
        time_vars[step.step_id] = var
        solver.add(var >= 0)

    track_to_payload: Dict[str, Dict[str, Any]] = {}

    for previous_step, next_step in zip(steps, steps[1:]):
        track_name = "lifeline:{}->{}".format(previous_step.step_id, next_step.step_id)
        solver.assert_and_track(
            time_vars[next_step.step_id] >= time_vars[previous_step.step_id],
            track_name,
        )
        track_to_payload[track_name] = {
            "kind": "lifeline_order",
            "left_step_id": previous_step.step_id,
            "right_step_id": next_step.step_id,
            "left_label": step_labels.get(previous_step.step_id),
            "right_label": step_labels.get(next_step.step_id),
            "human": "lifeline order: t({left}) <= t({right})".format(
                left=step_labels.get(previous_step.step_id) or previous_step.step_id,
                right=step_labels.get(next_step.step_id) or next_step.step_id,
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
                "constraint_kind": constraint.kind,
                "left_step_id": constraint.left_step_id,
                "right_step_id": constraint.right_step_id,
                "left_label": step_labels.get(constraint.left_step_id),
                "right_label": step_labels.get(constraint.right_step_id),
                "bound_seconds": _format_seconds(min_seconds),
                "human": "{} {} {}".format(
                    "t({}) - t({})".format(
                        step_labels.get(constraint.right_step_id)
                        or constraint.right_step_id,
                        step_labels.get(constraint.left_step_id)
                        or constraint.left_step_id,
                    ),
                    ">" if constraint.strict_lower else ">=",
                    _format_seconds(min_seconds),
                ),
            }
        if max_seconds is not None:
            track_name = "hi:{}".format(constraint.constraint_id)
            solver.assert_and_track(diff <= z3.RealVal(str(max_seconds)), track_name)
            track_to_payload[track_name] = {
                "kind": "duration_upper_bound",
                "constraint_id": constraint.constraint_id,
                "constraint_kind": constraint.kind,
                "left_step_id": constraint.left_step_id,
                "right_step_id": constraint.right_step_id,
                "left_label": step_labels.get(constraint.left_step_id),
                "right_label": step_labels.get(constraint.right_step_id),
                "bound_seconds": _format_seconds(max_seconds),
                "human": "t({}) - t({}) <= {}".format(
                    step_labels.get(constraint.right_step_id)
                    or constraint.right_step_id,
                    step_labels.get(constraint.left_step_id)
                    or constraint.left_step_id,
                    _format_seconds(max_seconds),
                ),
            }

    check_result = solver.check()
    if check_result != z3.unsat:
        return []

    raw_core = solver.unsat_core()
    core_names = [str(item) for item in raw_core]
    core_names.sort()
    core_payloads = [track_to_payload[name] for name in core_names if name in track_to_payload]

    duration_payloads = [p for p in core_payloads if p["kind"].startswith("duration_")]
    lifeline_payloads = [p for p in core_payloads if p["kind"] == "lifeline_order"]

    duration_constraint_ids = sorted(
        {p["constraint_id"] for p in duration_payloads if "constraint_id" in p}
    )

    related_steps: Set[str] = set()
    for payload in core_payloads:
        related_steps.add(payload["left_step_id"])
        related_steps.add(payload["right_step_id"])

    suggestion_constraint_id: Optional[str] = None
    suggestion_reason: Optional[str] = None
    if duration_payloads:
        # Heuristic: pick the equality constraint with the smallest bound — empirically this
        # is the constraint most often mis-attached by modelers (e.g. {1s} put onto the
        # wrong message endpoints when the modeler meant a longer Sig6→SigX delay). It is
        # the cheapest to investigate first.
        equality_payloads = [
            p for p in duration_payloads if p["kind"] == "duration_lower_bound"
        ]
        if equality_payloads:
            equality_payloads.sort(
                key=lambda p: Decimal(p["bound_seconds"].rstrip("s")) if p["bound_seconds"][:-1] else Decimal("0")
            )
            tight_payload = equality_payloads[0]
            suggestion_constraint_id = tight_payload["constraint_id"]
            suggestion_reason = (
                "DurationConstraint `{cid}` with bound {bound} bridges {left} and "
                "{right}; verify whether its endpoints were attached to the intended "
                "MessageOccurrenceSpecifications. Tight equality bounds with the wrong "
                "endpoints are the single most common cause of contradictory timing "
                "systems in SysDeSim exports.".format(
                    cid=suggestion_constraint_id,
                    bound=tight_payload["bound_seconds"],
                    left=tight_payload["left_label"] or tight_payload["left_step_id"],
                    right=tight_payload["right_label"] or tight_payload["right_step_id"],
                )
            )

    hints: List[str] = []
    if suggestion_reason:
        hints.append(suggestion_reason)
    hints.append(
        "Or: re-check the lifeline ordering (top-to-bottom) of messages "
        + ", ".join(
            sorted(
                {
                    p["left_label"] or p["left_step_id"]
                    for p in core_payloads
                    if p.get("left_label") or p.get("left_step_id")
                }
                | {
                    p["right_label"] or p["right_step_id"]
                    for p in core_payloads
                    if p.get("right_label") or p.get("right_step_id")
                }
            )
        )
        + ". Their visual order on the sequence diagram implies a "
        + "non-negative delta that may conflict with one of the duration constraints "
        + "above. Reordering the messages on the sequence diagram is sometimes "
        + "the right fix instead of relaxing a duration value."
    )
    hints.append(
        "Run `pyfcstm sysdesim validate -i <xml> --report-file <out.json>` to "
        "inspect every temporal constraint individually before editing."
    )

    message_lines = [
        "Imported scenario timing constraints are mutually unsatisfiable.",
        "Z3 unsat core (minimal contradicting set, {} entries):".format(len(core_payloads)),
    ]
    for payload in duration_payloads + lifeline_payloads:
        suffix = ""
        if payload["kind"].startswith("duration_") and payload.get("constraint_id"):
            suffix = " [constraint_id={}]".format(payload["constraint_id"])
        message_lines.append("  - {}{}".format(payload["human"], suffix))

    diagnostic = IrDiagnostic(
        level="error",
        code="temporal_constraints_unsat",
        message="\n".join(message_lines),
        source_id=duration_constraint_ids[0] if duration_constraint_ids else None,
        details={
            "method": "z3_unsat_core",
            "involved_constraint_ids": duration_constraint_ids,
            "involved_steps": sorted(related_steps),
            "core": core_payloads,
            "suggested_first_culprit_constraint_id": suggestion_constraint_id,
        },
        hints=hints,
    )
    return [diagnostic]


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
            if not isinstance(target_name, str):
                continue
            if not target_state_path.endswith(target_name):
                continue
            event = getattr(tr, "event", None)
            event_name = getattr(event, "name", None) if event else None
            from_name = getattr(tr, "from_state", None)
            if not isinstance(from_name, str):
                continue
            inbound.append(
                {
                    "from_state_local": from_name,
                    "owning_composite_path": ".".join(state.path),
                    "to_state_local": target_name,
                    "trigger_event_name": event_name,
                }
            )

    scenario_steps_by_id = {s.step_id: s for s in phase10_report.scenario.steps}
    state_at_step: Dict[str, str] = {}
    for step in trace.steps:
        state_at_step[step.step_id] = step.pre_state_path

    states_visited = sorted(
        {trace.initial_state_path}
        | {step.post_state_path for step in trace.steps if step.post_state_path}
        | {step.stabilized_state_path for step in trace.steps if step.stabilized_state_path}
        | {window.state_path for window in trace.state_windows}
    )

    trigger_emit_records: List[Dict[str, Any]] = []
    for inbound_entry in inbound:
        trigger_name = inbound_entry["trigger_event_name"]
        if not trigger_name:
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
                        "step_id": scen_step.step_id,
                        "trigger_event_name": trigger_name,
                        "expected_source_state": expected_source_local,
                        "actual_pre_state": pre_state,
                        "did_fire": ok,
                    }
                )
                break

    hints: List[str] = []
    if not inbound:
        hints.append(
            "No transition in machine {!r} targets state {!r}; the state may be "
            "structurally unreachable in the model itself (dead state).".format(
                trace.machine_alias, target_state_path
            )
        )
    else:
        if not trigger_emit_records:
            triggers = sorted({i["trigger_event_name"] or "(none)" for i in inbound})
            hints.append(
                "Inbound transitions exist via signals {triggers}, but none of "
                "those signals were emitted by the imported scenario. Add an "
                "emission of one such signal (or check signal-name spelling).".format(
                    triggers=", ".join(triggers)
                )
            )
        else:
            dropped = [r for r in trigger_emit_records if not r["did_fire"]]
            if dropped:
                first = dropped[0]
                hints.append(
                    "Signal {sig!r} was emitted at step {step}, but the region "
                    "was in state {actual!r} at that moment, not the required "
                    "source state {expected!r}. The signal was silently dropped; "
                    "either reorder messages so the prerequisite transition fires "
                    "first, or add the missing prerequisite signal before this "
                    "step.".format(
                        sig=first["trigger_event_name"],
                        step=first["step_id"],
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
        if trace is None:
            continue
        signal_to_sources: Dict[str, List[Tuple[str, str]]] = {}
        # Map state name -> set of ancestor state names (including self) for hierarchy
        # awareness; force-transitions like ``! H -> G : /SIG`` are owned by H but
        # apply to every descendant of H (UML "force" semantics).
        ancestor_names: Dict[str, Set[str]] = {}
        for state in machine.walk_states():
            ancestor_names.setdefault(state.name, set()).update(state.path)
            for tr in state.transitions:
                event = getattr(tr, "event", None)
                event_name = getattr(event, "name", None) if event else None
                from_name = getattr(tr, "from_state", None)
                to_name = getattr(tr, "to_state", None)
                if not isinstance(event_name, str):
                    continue
                if not isinstance(from_name, str) or not isinstance(to_name, str):
                    continue
                signal_to_sources.setdefault(event_name.lower(), []).append(
                    (from_name, to_name)
                )

        if not signal_to_sources:
            continue

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
                # The signal can be consumed if any of the source states is the
                # active state itself OR an ancestor on the active state's path
                # (for force-transitions like ``! Composite -> X``).
                consumed = any(
                    src in pre_path_tokens for src in source_locals
                )
                if consumed:
                    continue
                diagnostics.append(
                    IrDiagnostic(
                        level="warning",
                        code="signal_dropped_in_state",
                        message=(
                            "Signal {sig!r} emitted at step {step} was silently "
                            "dropped in machine {alias!r} (pre-state={pre}; "
                            "transitions for this signal exist only from {srcs}).".format(
                                sig=event_name,
                                step=scen_step.step_id,
                                alias=alias,
                                pre=pre_state,
                                srcs=", ".join(repr(s) for s in source_locals),
                            )
                        ),
                        source_id=alias,
                        details={
                            "machine_alias": alias,
                            "step_id": scen_step.step_id,
                            "signal": event_name,
                            "pre_state_path": pre_state,
                            "transition_source_states": source_locals,
                        },
                        hints=[
                            "If the signal was meant to advance machine {alias!r}, "
                            "make sure the region is in {srcs} before this step "
                            "(by emitting the prerequisite signal first or moving "
                            "this signal later in the lifeline).".format(
                                alias=alias, srcs=" or ".join(source_locals)
                            ),
                            "If the signal genuinely targets a different machine, "
                            "ignore this warning — it is an informational hint.",
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
    return diagnostics


__all__ = [
    "detect_query_state_name_unknown",
    "detect_signal_dropped_in_state",
    "detect_target_state_never_entered",
    "detect_temporal_constraints_unsat",
    "run_sysdesim_static_pre_checks",
]

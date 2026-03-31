"""
Phase9/10/11 timeline verification helpers for SysDeSim inputs.

This module closes the current SysDeSim importer loop in three pragmatic
stages:

* Phase9 keeps the FCSTM compatibility export as a reviewable output family and
  reparses the generated DSL back into :class:`pyfcstm.model.StateMachine`
  objects.
* Phase10 turns the Phase7/8 import IR into a small timeline scenario,
  machine-level bindings, and runtime-derived state traces.
* Phase11 compiles the resulting time symbols plus hidden auto-transition
  anchors into Z3 constraints so state coexistence queries can return either a
  concrete witness or an exact ``unsat`` result.

The implementation is intentionally conservative. It does not try to solve the
entire generic timeline language here; instead it focuses on the currently
supported SysDeSim subset and keeps every intermediate layer inspectable.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from decimal import Decimal
from typing import Dict, Iterable, List, Optional, Tuple

import z3

from ...dsl import parse_with_grammar_entry
from ...model import StateMachine, parse_dsl_node_to_state_machine
from ...simulate import SimulationRuntime
from .convert import build_sysdesim_conversion_report, convert_sysdesim_xml_to_dsls
from .timeline import (
    SysDeSimPhase78Report,
    SysDeSimTimelineEmitAction,
    SysDeSimTimelineSetInputAction,
    SysDeSimTimelineStepTimeWindow,
    build_sysdesim_phase78_report,
)

_TIME_LITERAL = re.compile(
    r"^\s*([+-]?(?:[0-9]+(?:\.[0-9]+)?|\.[0-9]+))\s*(ms|s|sec|min|m|h)\s*$",
    re.IGNORECASE,
)
_TIME_UNITS = {
    "ms": Decimal("0.001"),
    "s": Decimal("1"),
    "sec": Decimal("1"),
    "m": Decimal("60"),
    "min": Decimal("60"),
    "h": Decimal("3600"),
}


@dataclass(frozen=True)
class SysDeSimTimelineScenarioEmitAction:
    """Scenario-level emit action derived from one inbound message step."""

    kind: str
    event_name: str


@dataclass(frozen=True)
class SysDeSimTimelineScenarioSetInputAction:
    """Scenario-level input update derived from one state invariant step."""

    kind: str
    input_name: str
    value_text: str


@dataclass(frozen=True)
class SysDeSimTimelineScenarioStep:
    """One ordered scenario step ready for runtime/timing work."""

    step_id: str
    time_symbol: str
    actions: Tuple[object, ...]
    source_observation_ids: Tuple[str, ...]
    source_kinds: Tuple[str, ...]
    notes: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimNormalizedTemporalConstraint:
    """One normalized between-symbol temporal constraint."""

    constraint_id: str
    kind: str
    left_step_id: str
    right_step_id: str
    left_time_symbol: str
    right_time_symbol: str
    min_seconds_text: Optional[str]
    max_seconds_text: Optional[str]
    strict_lower: bool
    note: Optional[str]


@dataclass(frozen=True)
class SysDeSimPhase9Output:
    """One compatibility-export output reparsed into the public model layer."""

    output_name: str
    dsl_code: str
    machine: StateMachine
    define_names: Tuple[str, ...]
    event_runtime_refs: Tuple[str, ...]
    semantic_note: Optional[str]
    diagnostic_codes: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimPhase9Report:
    """Phase9 closing report for compatibility output family reuse."""

    selected_machine_name: str
    selected_interaction_name: str
    phase78_report: SysDeSimPhase78Report
    outputs: Tuple[SysDeSimPhase9Output, ...]
    diagnostics: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimTimelineMachineBinding:
    """Name binding from scenario-layer actions to one FCSTM output machine."""

    machine_alias: str
    event_map: Dict[str, str]
    input_map: Dict[str, str]


@dataclass(frozen=True)
class SysDeSimTimelineAutoOccurrence:
    """Hidden auto-transition occurrence inserted between two observed steps."""

    machine_alias: str
    source_step_id: str
    occurrence_index: int
    occurrence_symbol: str
    from_state_path: str
    to_state_path: str
    right_observation_step_id: Optional[str]
    right_emit_step_id: Optional[str]
    note: Optional[str]


@dataclass(frozen=True)
class SysDeSimTimelineStateWindow:
    """One open interval where a machine state is assumed to hold."""

    machine_alias: str
    source_step_id: str
    state_path: str
    start_symbol: str
    end_symbol: str
    note: Optional[str]


@dataclass(frozen=True)
class SysDeSimTimelineStepExecution:
    """One machine trace item aligned to one scenario step."""

    step_id: str
    time_symbol: str
    pre_state_path: str
    post_state_path: str
    stabilized_state_path: str
    bound_event_path: Optional[str]
    applied_inputs: Tuple[Tuple[str, str, str], ...]
    auto_occurrences: Tuple[SysDeSimTimelineAutoOccurrence, ...]
    vars_snapshot: Tuple[Tuple[str, str], ...]
    source_observation_ids: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimTimelineMachineTrace:
    """Runtime-derived per-machine trajectory for the imported scenario."""

    machine_alias: str
    initial_state_path: str
    initial_vars: Tuple[Tuple[str, str], ...]
    steps: Tuple[SysDeSimTimelineStepExecution, ...]
    state_windows: Tuple[SysDeSimTimelineStateWindow, ...]


@dataclass(frozen=True)
class SysDeSimTimelineScenario:
    """Minimal scenario object produced from the SysDeSim Phase7/8 IR."""

    name: Optional[str]
    steps: Tuple[SysDeSimTimelineScenarioStep, ...]
    temporal_constraints: Tuple[SysDeSimNormalizedTemporalConstraint, ...]


@dataclass(frozen=True)
class SysDeSimPhase10Report:
    """Phase10 runtime/binding report ready for SMT querying."""

    phase9_report: SysDeSimPhase9Report
    scenario: SysDeSimTimelineScenario
    bindings: Tuple[SysDeSimTimelineMachineBinding, ...]
    traces: Tuple[SysDeSimTimelineMachineTrace, ...]
    diagnostics: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimTimelineWitnessStep:
    """One witness row shown in the final coexistence report."""

    step_id: str
    time_symbol: str
    time_value_text: str
    actions: Tuple[str, ...]
    machine_states: Tuple[Tuple[str, str], ...]
    source_observation_ids: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimStateCoexistenceResult:
    """Exact Z3 result for one two-machine state coexistence query."""

    status: str
    solver_status: str
    left_machine_alias: str
    left_state_path: str
    right_machine_alias: str
    right_state_path: str
    observation_kind: Optional[str]
    reason: Optional[str]
    time_values: Tuple[Tuple[str, str], ...]
    witness_steps: Tuple[SysDeSimTimelineWitnessStep, ...]
    witness_notes: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimStateCoexistenceConstraintPreview:
    """Human-readable constraint preview for one coexistence query."""

    left_machine_alias: str
    left_state_path: str
    right_machine_alias: str
    right_state_path: str
    symbol_meanings: Tuple[Tuple[str, str], ...]
    base_constraints: Tuple[str, ...]
    query_summary: str
    query_constraint: str
    candidate_count: int
    candidate_notes: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimStateCoexistenceTimelinePoint:
    """One concrete point on the solved coexistence timeline."""

    symbol: str
    time_value_text: str
    point_kind: str
    point_label: str
    actions: Tuple[str, ...]
    machine_states: Tuple[Tuple[str, str], ...]
    is_coexistent: bool


@dataclass(frozen=True)
class SysDeSimStateCoexistenceTimelineReport:
    """One single solved timeline focused on state coexistence review."""

    status: str
    solver_status: str
    time_domain: str
    left_machine_alias: str
    left_state_path: str
    right_machine_alias: str
    right_state_path: str
    reason: Optional[str]
    first_coexistence_symbol: Optional[str]
    first_coexistence_time_text: Optional[str]
    first_coexistence_note: Optional[str]
    timeline_points: Tuple[SysDeSimStateCoexistenceTimelinePoint, ...]


def _format_decimal(value: Decimal) -> str:
    """Format one decimal value as stable plain text for Z3 and reports."""
    text = format(value, "f")
    if "." in text:
        text = text.rstrip("0").rstrip(".")
    if text in {"", "-0"}:
        return "0"
    return text


def _format_runtime_number(value: object) -> str:
    """Format one runtime variable value into stable text."""
    if isinstance(value, bool):
        return "true" if value else "false"
    if isinstance(value, int):
        return str(value)
    if isinstance(value, float):
        return _format_decimal(Decimal(str(value)))
    return str(value)


def _parse_time_literal_seconds(text: str) -> Decimal:
    """Parse one time literal such as ``10s`` or ``5ms`` into seconds."""
    match = _TIME_LITERAL.fullmatch(text)
    if match is None:
        raise ValueError("Unsupported time literal: {!r}".format(text))
    value = Decimal(match.group(1))
    unit = match.group(2).lower()
    return value * _TIME_UNITS[unit]


def _parse_interval_text(
    value_text: str,
) -> Tuple[Optional[str], Optional[str]]:
    """Parse one ``20s-30s`` or ``10s`` interval into min/max seconds text."""
    text = value_text.strip()
    if not text:
        return None, None
    if "-" in text:
        left_text, right_text = [item.strip() for item in text.split("-", 1)]
        left = _parse_time_literal_seconds(left_text)
        right = _parse_time_literal_seconds(right_text)
        return _format_decimal(left), _format_decimal(right)
    value = _parse_time_literal_seconds(text)
    rendered = _format_decimal(value)
    return rendered, rendered


def _collect_transition_event_runtime_refs(machine: StateMachine) -> Tuple[str, ...]:
    """Collect runtime event references that actually trigger transitions."""
    refs = []
    seen = set()
    for state in machine.walk_states():
        for transition in state.transitions:
            if transition.event is None:
                continue
            runtime_ref = "/" + ".".join(transition.event.path[1:])
            if runtime_ref in seen:
                continue
            seen.add(runtime_ref)
            refs.append(runtime_ref)
    return tuple(refs)


def _build_phase9_output(
    output_name: str,
    dsl_code: str,
    semantic_note: Optional[str],
    diagnostic_codes: Iterable[str],
) -> SysDeSimPhase9Output:
    """Parse one emitted DSL output back into the public state-machine model."""
    parsed = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    machine = parse_dsl_node_to_state_machine(parsed)
    return SysDeSimPhase9Output(
        output_name=output_name,
        dsl_code=dsl_code,
        machine=machine,
        define_names=tuple(sorted(machine.defines.keys())),
        event_runtime_refs=_collect_transition_event_runtime_refs(machine),
        semantic_note=semantic_note,
        diagnostic_codes=tuple(sorted(set(diagnostic_codes))),
    )


def build_sysdesim_phase9_report(
    xml_path: str,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
) -> SysDeSimPhase9Report:
    """
    Build the Phase9 compatibility-export closing report.

    :param xml_path: Source SysDeSim XML path.
    :type xml_path: str
    :param machine_name: Optional machine selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration for compatibility export.
    :type tick_duration_ms: float, optional
    :return: Parsed output family plus shared Phase7/8 context.
    :rtype: SysDeSimPhase9Report
    """
    phase78_report = build_sysdesim_phase78_report(
        xml_path, machine_name=machine_name, interaction_name=interaction_name
    )
    conversion_report = build_sysdesim_conversion_report(
        xml_path,
        machine_name=machine_name,
        tick_duration_ms=tick_duration_ms,
    )
    output_dsl_map = convert_sysdesim_xml_to_dsls(
        xml_path,
        machine_name=machine_name,
        tick_duration_ms=tick_duration_ms,
    )
    conversion_index = {
        item.output_name: item for item in conversion_report.outputs
    }
    outputs = []
    diagnostics = []
    for output_name, dsl_code in output_dsl_map.items():
        output_report = conversion_index[output_name]
        outputs.append(
            _build_phase9_output(
                output_name=output_name,
                dsl_code=dsl_code,
                semantic_note=output_report.semantic_note,
                diagnostic_codes=(item.code for item in output_report.diagnostics),
            )
        )
        diagnostics.extend(item.code for item in output_report.diagnostics)

    return SysDeSimPhase9Report(
        selected_machine_name=phase78_report.selected_machine_name,
        selected_interaction_name=phase78_report.selected_interaction_name,
        phase78_report=phase78_report,
        outputs=tuple(outputs),
        diagnostics=tuple(sorted(set(diagnostics))),
    )


def _build_scenario_steps(
    report: SysDeSimPhase78Report,
) -> Tuple[SysDeSimTimelineScenarioStep, ...]:
    """Convert Phase8 steps into scenario-layer step objects."""
    steps = []
    for item in report.steps:
        actions = []
        for action in item.actions:
            if isinstance(action, SysDeSimTimelineEmitAction):
                actions.append(
                    SysDeSimTimelineScenarioEmitAction(
                        kind="emit", event_name=action.scenario_event_name
                    )
                )
            elif isinstance(action, SysDeSimTimelineSetInputAction):
                actions.append(
                    SysDeSimTimelineScenarioSetInputAction(
                        kind="set_input",
                        input_name=action.input_name,
                        value_text=action.value_text,
                    )
                )
        steps.append(
            SysDeSimTimelineScenarioStep(
                step_id=item.step_id,
                time_symbol="t" + item.step_id[1:],
                actions=tuple(actions),
                source_observation_ids=item.source_observation_ids,
                source_kinds=item.source_kinds,
                notes=item.notes,
            )
        )
    return tuple(steps)


def _build_normalized_temporal_constraints(
    scenario_steps: Tuple[SysDeSimTimelineScenarioStep, ...],
    report: SysDeSimPhase78Report,
) -> Tuple[SysDeSimNormalizedTemporalConstraint, ...]:
    """Normalize duration constraints and legacy time-windows into one shape."""
    step_index = {item.step_id: index for index, item in enumerate(scenario_steps)}
    step_map = {item.step_id: item for item in scenario_steps}
    constraints = []

    for item in report.duration_constraints:
        min_text, max_text = _parse_interval_text(item.value_text)
        constraints.append(
            SysDeSimNormalizedTemporalConstraint(
                constraint_id=item.constraint_id,
                kind="duration_constraint",
                left_step_id=item.left_step_id,
                right_step_id=item.right_step_id,
                left_time_symbol=step_map[item.left_step_id].time_symbol,
                right_time_symbol=step_map[item.right_step_id].time_symbol,
                min_seconds_text=min_text,
                max_seconds_text=max_text,
                strict_lower=False,
                note=None,
            )
        )

    for item in report.time_windows:
        left_step = _resolve_time_window_left_step(scenario_steps, item)
        if left_step is None:
            continue
        min_text, max_text = _parse_interval_text(item.value_text)
        constraints.append(
            SysDeSimNormalizedTemporalConstraint(
                constraint_id=item.constraint_id,
                kind="inferred_duration_constraint",
                left_step_id=left_step.step_id,
                right_step_id=item.step_id,
                left_time_symbol=left_step.time_symbol,
                right_time_symbol=step_map[item.step_id].time_symbol,
                min_seconds_text=min_text,
                max_seconds_text=max_text,
                strict_lower=True,
                note=(
                    "TimeConstraint lowered to a between-step duration using "
                    "the immediately preceding observed step as the left endpoint."
                ),
            )
        )

    constraints.sort(
        key=lambda item: (
            step_index[item.left_step_id],
            step_index[item.right_step_id],
            item.constraint_id,
        )
    )
    return tuple(constraints)


def _resolve_time_window_left_step(
    scenario_steps: Tuple[SysDeSimTimelineScenarioStep, ...],
    item: SysDeSimTimelineStepTimeWindow,
) -> Optional[SysDeSimTimelineScenarioStep]:
    """Infer the left endpoint used to reinterpret one legacy time-window."""
    for index, step in enumerate(scenario_steps):
        if step.step_id != item.step_id:
            continue
        if index <= 0:
            return None
        return scenario_steps[index - 1]
    return None


def _build_machine_binding(
    output: SysDeSimPhase9Output, report: SysDeSimPhase78Report
) -> SysDeSimTimelineMachineBinding:
    """Build one scenario-to-machine binding from Phase7 candidates."""
    event_map = {}
    input_map = {}
    available_event_refs = set(output.event_runtime_refs)
    available_define_names = set(output.define_names)

    for item in report.event_candidates:
        if not item.emit_allowed or not item.machine_event_path:
            continue
        if item.machine_event_path in available_event_refs:
            event_map[item.scenario_event_name] = item.machine_event_path

    for item in report.input_candidates:
        if item.role != "external_input":
            continue
        for local_name in item.machine_local_names:
            if local_name in available_define_names:
                input_map[item.normalized_name] = local_name
                break

    return SysDeSimTimelineMachineBinding(
        machine_alias=output.output_name,
        event_map=event_map,
        input_map=input_map,
    )


def _find_next_emit_step_id(
    steps: Tuple[SysDeSimTimelineScenarioStep, ...],
    start_index: int,
) -> Optional[str]:
    """Return the next step after ``start_index`` that still emits an event."""
    for step in steps[start_index + 1 :]:
        if any(
            isinstance(action, SysDeSimTimelineScenarioEmitAction)
            for action in step.actions
        ):
            return step.step_id
    return None


def _resolve_bound_event(
    step: SysDeSimTimelineScenarioStep,
    binding: SysDeSimTimelineMachineBinding,
) -> Optional[str]:
    """Resolve one scenario step's machine-facing event for a specific binding."""
    for action in step.actions:
        if not isinstance(action, SysDeSimTimelineScenarioEmitAction):
            continue
        return binding.event_map.get(action.event_name)
    return None


def _coerce_runtime_input(define_type: str, value_text: str) -> object:
    """Convert one scenario value text into a runtime-ready Python value."""
    if define_type == "int":
        return int(Decimal(value_text))
    if define_type == "float":
        return float(value_text)
    return value_text


def _current_auto_transition(runtime: SimulationRuntime):
    """Return the first unconditional outgoing transition of the current leaf state."""
    for transition in runtime.current_state.transitions_from:
        if transition.event is None and transition.guard is None:
            return transition
    return None


def _build_state_windows(
    machine_alias: str,
    steps: Tuple[SysDeSimTimelineStepExecution, ...],
    scenario_steps: Tuple[SysDeSimTimelineScenarioStep, ...],
) -> Tuple[SysDeSimTimelineStateWindow, ...]:
    """Build open-interval state windows from one runtime trace."""
    if len(steps) < 2:
        return ()
    step_by_id = {item.step_id: item for item in steps}
    windows = []
    for index, scenario_step in enumerate(scenario_steps[:-1]):
        current = step_by_id[scenario_step.step_id]
        next_step = scenario_steps[index + 1]
        if current.auto_occurrences:
            first = current.auto_occurrences[0]
            windows.append(
                SysDeSimTimelineStateWindow(
                    machine_alias=machine_alias,
                    source_step_id=current.step_id,
                    state_path=current.post_state_path,
                    start_symbol=current.time_symbol,
                    end_symbol=first.occurrence_symbol,
                    note="before_hidden_auto",
                )
            )
            previous_symbol = first.occurrence_symbol
            previous_state = first.to_state_path
            for item in current.auto_occurrences[1:]:
                windows.append(
                    SysDeSimTimelineStateWindow(
                        machine_alias=machine_alias,
                        source_step_id=current.step_id,
                        state_path=previous_state,
                        start_symbol=previous_symbol,
                        end_symbol=item.occurrence_symbol,
                        note="between_hidden_auto",
                    )
                )
                previous_symbol = item.occurrence_symbol
                previous_state = item.to_state_path
            windows.append(
                SysDeSimTimelineStateWindow(
                    machine_alias=machine_alias,
                    source_step_id=current.step_id,
                    state_path=previous_state,
                    start_symbol=previous_symbol,
                    end_symbol=next_step.time_symbol,
                    note="after_hidden_auto",
                )
            )
        else:
            windows.append(
                SysDeSimTimelineStateWindow(
                    machine_alias=machine_alias,
                    source_step_id=current.step_id,
                    state_path=current.post_state_path,
                    start_symbol=current.time_symbol,
                    end_symbol=next_step.time_symbol,
                    note="stable_between_steps",
                )
            )
    return tuple(windows)


def _build_machine_trace(
    output: SysDeSimPhase9Output,
    binding: SysDeSimTimelineMachineBinding,
    scenario: SysDeSimTimelineScenario,
) -> SysDeSimTimelineMachineTrace:
    """Execute one scenario over one output machine with runtime-assisted closure."""
    runtime = SimulationRuntime(output.machine, abstract_error_mode="log")
    runtime.cycle([])

    trace_steps = []
    for index, step in enumerate(scenario.steps):
        pre_state_path = ".".join(runtime.current_state.path)
        applied_inputs = []
        for action in step.actions:
            if not isinstance(action, SysDeSimTimelineScenarioSetInputAction):
                continue
            local_name = binding.input_map.get(action.input_name)
            if local_name is None or local_name not in output.machine.defines:
                continue
            define = output.machine.defines[local_name]
            runtime.vars[local_name] = _coerce_runtime_input(
                define.type, action.value_text
            )
            applied_inputs.append((action.input_name, local_name, action.value_text))

        bound_event_path = _resolve_bound_event(step, binding)
        runtime.cycle([bound_event_path] if bound_event_path else [])
        post_state_path = ".".join(runtime.current_state.path)

        auto_occurrences = []
        right_emit_step_id = _find_next_emit_step_id(scenario.steps, index)
        right_observation_step_id = (
            scenario.steps[index + 1].step_id
            if index + 1 < len(scenario.steps)
            else None
        )
        auto_index = 0
        while auto_index < 16:
            auto_transition = _current_auto_transition(runtime)
            if auto_transition is None:
                break
            from_state_path = ".".join(runtime.current_state.path)
            auto_index += 1
            occurrence_symbol = "tau__{alias}__{step_id}__{index}".format(
                alias=output.output_name, step_id=step.step_id, index=auto_index
            )
            runtime.cycle([])
            to_state_path = ".".join(runtime.current_state.path)
            auto_occurrences.append(
                SysDeSimTimelineAutoOccurrence(
                    machine_alias=output.output_name,
                    source_step_id=step.step_id,
                    occurrence_index=auto_index,
                    occurrence_symbol=occurrence_symbol,
                    from_state_path=from_state_path,
                    to_state_path=to_state_path,
                    right_observation_step_id=right_observation_step_id,
                    right_emit_step_id=right_emit_step_id,
                    note=(
                        "Hidden auto-transition closure bounded by the next "
                        "observed step; the next machine-facing emit remains a "
                        "weaker outer semantic bound."
                    ),
                )
            )

        trace_steps.append(
            SysDeSimTimelineStepExecution(
                step_id=step.step_id,
                time_symbol=step.time_symbol,
                pre_state_path=pre_state_path,
                post_state_path=post_state_path,
                stabilized_state_path=".".join(runtime.current_state.path),
                bound_event_path=bound_event_path,
                applied_inputs=tuple(applied_inputs),
                auto_occurrences=tuple(auto_occurrences),
                vars_snapshot=tuple(
                    (name, _format_runtime_number(value))
                    for name, value in sorted(runtime.vars.items())
                ),
                source_observation_ids=step.source_observation_ids,
            )
        )

    return SysDeSimTimelineMachineTrace(
        machine_alias=output.output_name,
        initial_state_path=".".join(runtime.history[0]["state"].split("."))
        if runtime.history
        else ".".join(runtime.current_state.path),
        initial_vars=tuple(
            (name, _format_runtime_number(value))
            for name, value in sorted(runtime.history[0]["vars"].items())
        )
        if runtime.history
        else tuple((name, _format_runtime_number(value)) for name, value in sorted(runtime.vars.items())),
        steps=tuple(trace_steps),
        state_windows=_build_state_windows(
            output.output_name, tuple(trace_steps), scenario.steps
        ),
    )


def build_sysdesim_phase10_report(
    xml_path: str,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
) -> SysDeSimPhase10Report:
    """
    Build the Phase10 runtime/binding report.

    :param xml_path: Source SysDeSim XML path.
    :type xml_path: str
    :param machine_name: Optional machine selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration for compatibility export.
    :type tick_duration_ms: float, optional
    :return: Scenario, bindings, and per-output machine traces.
    :rtype: SysDeSimPhase10Report
    """
    phase9_report = build_sysdesim_phase9_report(
        xml_path,
        machine_name=machine_name,
        interaction_name=interaction_name,
        tick_duration_ms=tick_duration_ms,
    )
    scenario_steps = _build_scenario_steps(phase9_report.phase78_report)
    scenario = SysDeSimTimelineScenario(
        name=phase9_report.selected_interaction_name,
        steps=scenario_steps,
        temporal_constraints=_build_normalized_temporal_constraints(
            scenario_steps, phase9_report.phase78_report
        ),
    )

    bindings = []
    traces = []
    diagnostics = list(phase9_report.diagnostics)
    for output in phase9_report.outputs:
        binding = _build_machine_binding(output, phase9_report.phase78_report)
        bindings.append(binding)
        traces.append(_build_machine_trace(output, binding, scenario))

    return SysDeSimPhase10Report(
        phase9_report=phase9_report,
        scenario=scenario,
        bindings=tuple(bindings),
        traces=tuple(traces),
        diagnostics=tuple(sorted(set(diagnostics))),
    )


def _symbol_vars(
    phase10_report: SysDeSimPhase10Report,
) -> Dict[str, z3.ArithRef]:
    """Create Z3 real variables for step times and hidden auto times."""
    symbols = {}
    for step in phase10_report.scenario.steps:
        symbols[step.time_symbol] = z3.Real(step.time_symbol)
    for trace in phase10_report.traces:
        for step in trace.steps:
            for item in step.auto_occurrences:
                symbols[item.occurrence_symbol] = z3.Real(item.occurrence_symbol)
    return symbols


def _build_base_time_constraints(
    phase10_report: SysDeSimPhase10Report,
    symbol_vars: Dict[str, z3.ArithRef],
) -> List[z3.BoolRef]:
    """Build monotonic, duration, and hidden-auto timing constraints."""
    constraints = []
    steps = phase10_report.scenario.steps
    if steps:
        constraints.append(symbol_vars[steps[0].time_symbol] >= z3.RealVal("0"))
    for left, right in zip(steps, steps[1:]):
        constraints.append(
            symbol_vars[left.time_symbol] <= symbol_vars[right.time_symbol]
        )

    for item in phase10_report.scenario.temporal_constraints:
        dt = symbol_vars[item.right_time_symbol] - symbol_vars[item.left_time_symbol]
        if item.min_seconds_text is not None:
            constraints.append(dt >= z3.RealVal(item.min_seconds_text))
        if item.max_seconds_text is not None:
            constraints.append(dt <= z3.RealVal(item.max_seconds_text))
        if item.strict_lower:
            constraints.append(dt > z3.RealVal("0"))

    step_time_by_id = {
        step.step_id: symbol_vars[step.time_symbol]
        for step in phase10_report.scenario.steps
    }
    for trace in phase10_report.traces:
        for step in trace.steps:
            previous_symbol = step_time_by_id[step.step_id]
            for item in step.auto_occurrences:
                constraints.append(symbol_vars[item.occurrence_symbol] > previous_symbol)
                if item.right_observation_step_id is not None:
                    constraints.append(
                        symbol_vars[item.occurrence_symbol]
                        < step_time_by_id[item.right_observation_step_id]
                    )
                elif item.right_emit_step_id is not None:
                    constraints.append(
                        symbol_vars[item.occurrence_symbol]
                        < step_time_by_id[item.right_emit_step_id]
                    )
                previous_symbol = symbol_vars[item.occurrence_symbol]
    return constraints


def _resolve_state_path(machine: StateMachine, state_ref: str) -> str:
    """Resolve one leaf-like state reference into a unique dot-separated path."""
    path_candidates = []
    suffix_candidates = []
    ref_tokens = tuple(token for token in state_ref.split(".") if token)
    for state in machine.walk_states():
        path_tokens = tuple(state.path)
        path_name = ".".join(path_tokens)
        if state_ref == path_name or state_ref == ".".join(state.path[1:]):
            return path_name
        if (
            len(ref_tokens) >= 2
            and len(ref_tokens) <= len(path_tokens)
            and path_tokens[-len(ref_tokens) :] == ref_tokens
        ):
            suffix_candidates.append(path_name)
        if state.name == state_ref:
            path_candidates.append(path_name)
    if len(path_candidates) == 1:
        return path_candidates[0]
    if len(suffix_candidates) == 1:
        return suffix_candidates[0]
    if not path_candidates:
        if len(suffix_candidates) > 1:
            raise LookupError(
                "State reference {!r} is ambiguous: {}.".format(
                    state_ref, ", ".join(suffix_candidates)
                )
            )
        raise LookupError("State reference {!r} not found.".format(state_ref))
    raise LookupError(
        "State reference {!r} is ambiguous: {}.".format(
            state_ref, ", ".join(path_candidates)
        )
    )


def _trace_index_by_alias(
    phase10_report: SysDeSimPhase10Report,
) -> Dict[str, SysDeSimTimelineMachineTrace]:
    """Build a lookup table from machine alias to its runtime trace."""
    return {item.machine_alias: item for item in phase10_report.traces}


def _output_index_by_alias(
    phase10_report: SysDeSimPhase10Report,
) -> Dict[str, SysDeSimPhase9Output]:
    """Build a lookup table from machine alias to its Phase9 output."""
    return {item.output_name: item for item in phase10_report.phase9_report.outputs}


@dataclass(frozen=True)
class _PreparedStateCoexistenceProblem:
    """Shared prepared state used by solve and preview helpers."""

    phase10_report: SysDeSimPhase10Report
    symbol_vars: Dict[str, z3.ArithRef]
    base_constraints: Tuple[z3.BoolRef, ...]
    left_state_path: str
    right_state_path: str
    candidate_terms: Tuple[z3.BoolRef, ...]
    candidate_meta: Tuple[Tuple[str, str, Optional[str], Optional[str]], ...]
    candidate_count: int
    query_summary: str
    candidate_notes: Tuple[str, ...]


def _z3_value_to_text(model: z3.ModelRef, expr: z3.ExprRef) -> str:
    """Render one model value into stable decimal text."""
    value = model.evaluate(expr, model_completion=True)
    if z3.is_rational_value(value):
        if value.denominator_as_long() == 1:
            return str(value.numerator_as_long())
        fraction = Decimal(value.numerator_as_long()) / Decimal(
            value.denominator_as_long()
        )
        return _format_decimal(fraction)
    return str(value)


def _step_by_id(
    trace: SysDeSimTimelineMachineTrace, step_id: str
) -> SysDeSimTimelineStepExecution:
    """Resolve one trace execution by step id."""
    for item in trace.steps:
        if item.step_id == step_id:
            return item
    raise KeyError(
        "Step {!r} not found in trace {!r}.".format(step_id, trace.machine_alias)
    )


def _describe_post_step_reason(
    machine_alias: str,
    state_path: str,
    trace: SysDeSimTimelineMachineTrace,
    step_id: str,
) -> str:
    """Build a short, user-facing reason for one post-step state occupancy."""
    execution = _step_by_id(trace, step_id)
    first_seen_step_id = None
    for item in trace.steps:
        if item.post_state_path == state_path:
            first_seen_step_id = item.step_id
            break

    if first_seen_step_id == step_id:
        previous_execution = None
        for index, item in enumerate(trace.steps):
            if item.step_id == step_id and index > 0:
                previous_execution = trace.steps[index - 1]
                break
        if (
            previous_execution is not None
            and previous_execution.stabilized_state_path == state_path
            and previous_execution.post_state_path != state_path
        ):
            return (
                "{alias} 在 `{prev_step}` 先到 `{post_state}`，再经隐藏 auto 于 `{step}` 观测前到达 `{state}`。".format(
                    alias=machine_alias,
                    prev_step=previous_execution.step_id,
                    post_state=previous_execution.post_state_path,
                    step=step_id,
                    state=state_path,
                )
            )
        if execution.bound_event_path:
            return (
                "{alias} 在 `{step}` 因事件 `{event}` 到达 `{state}`。".format(
                    alias=machine_alias,
                    step=step_id,
                    event=execution.bound_event_path,
                    state=state_path,
                )
            )
        return "{alias} 在 `{step}` 时到达 `{state}`。".format(
            alias=machine_alias,
            step=step_id,
            state=state_path,
        )

    return "{alias} 从 `{first}` 起已保持 `{state}`，到 `{step}` 观测时仍然成立。".format(
        alias=machine_alias,
        first=first_seen_step_id,
        state=state_path,
        step=step_id,
    )


def _build_candidate_summary_notes(
    left_machine_alias: str,
    left_state_path: str,
    left_trace: SysDeSimTimelineMachineTrace,
    right_machine_alias: str,
    right_state_path: str,
    right_trace: SysDeSimTimelineMachineTrace,
    post_step_matches: Tuple[str, ...],
    open_interval_matches: Tuple[Tuple[str, str, str, str], ...],
) -> Tuple[str, ...]:
    """Summarize raw candidate points into a small user-facing explanation set."""
    notes = []

    if post_step_matches:
        preview_ids = ", ".join(post_step_matches[:6])
        if len(post_step_matches) > 6:
            preview_ids = "{}, ...".format(preview_ids)
        notes.append(
            "离散观测点上共有 {count} 个可构造共存的位置：{steps}。".format(
                count=len(post_step_matches),
                steps=preview_ids,
            )
        )
        first_step_id = post_step_matches[0]
        notes.append(
            "最早可在 `post_step({step})` 构造：{left_reason} {right_reason}".format(
                step=first_step_id,
                left_reason=_describe_post_step_reason(
                    left_machine_alias, left_state_path, left_trace, first_step_id
                ),
                right_reason=_describe_post_step_reason(
                    right_machine_alias, right_state_path, right_trace, first_step_id
                ),
            )
        )

    if open_interval_matches:
        left_start, left_end, right_start, right_end = open_interval_matches[0]
        notes.append(
            "若要求严格正时长区间，最早可取两侧窗口的重叠部分："
            "`{left_alias}` 在 `({left_start}, {left_end})` 持有 `{left_state}`，"
            "`{right_alias}` 在 `({right_start}, {right_end})` 持有 `{right_state}`。"
            " 只要选择这两段的公共时间点，就能构造出连续时间上的共存。".format(
                left_alias=left_machine_alias,
                left_start=left_start,
                left_end=left_end,
                left_state=left_state_path,
                right_alias=right_machine_alias,
                right_start=right_start,
                right_end=right_end,
                right_state=right_state_path,
            )
        )

    if not notes:
        left_seen = any(item.post_state_path == left_state_path for item in left_trace.steps)
        right_seen = any(item.post_state_path == right_state_path for item in right_trace.steps)
        if not left_seen:
            notes.append(
                "`{alias}` 的 `{state}` 在当前导入轨迹里一次都没有出现，所以不存在可构造的共存点。".format(
                    alias=left_machine_alias,
                    state=left_state_path,
                )
            )
        elif not right_seen:
            notes.append(
                "`{alias}` 的 `{state}` 在当前导入轨迹里一次都没有出现，所以不存在可构造的共存点。".format(
                    alias=right_machine_alias,
                    state=right_state_path,
                )
            )
        else:
            notes.append("未发现任何可构造的 `post_step` 或 `open_interval` 共存位置。")

    return tuple(notes)


def _preview_items(items: Tuple[str, ...], prefix: str) -> str:
    """Render a short preview list for one query-summary sentence."""
    if not items:
        return ""
    preview = [prefix.format(item) for item in items[:6]]
    if len(items) > 6:
        preview.append("...")
    return "、".join(preview)


def _build_query_summary(
    left_machine_alias: str,
    left_state_path: str,
    right_machine_alias: str,
    right_state_path: str,
    post_step_matches: Tuple[str, ...],
    open_interval_matches: Tuple[Tuple[str, str, str, str], ...],
) -> str:
    """Explain the coexistence query in direct user-facing language."""
    if post_step_matches and open_interval_matches:
        left_start, left_end, right_start, right_end = open_interval_matches[0]
        return (
            "查询逻辑：接受两类证据。"
            " 第一类是命中任一离散观测点 {points}；"
            " 第二类是连续时间窗口重叠，例如 `{left_alias}` 的 `{left_state}`"
            " 可落在 `({left_start}, {left_end})`，同时 `{right_alias}` 的"
            " `{right_state}` 可落在 `({right_start}, {right_end})`。"
            " 只要任一类成立，就说明这两个状态可共存。"
        ).format(
            points=_preview_items(post_step_matches, "post_step({})"),
            left_alias=left_machine_alias,
            left_state=left_state_path,
            left_start=left_start,
            left_end=left_end,
            right_alias=right_machine_alias,
            right_state=right_state_path,
            right_start=right_start,
            right_end=right_end,
        )

    if post_step_matches:
        return (
            "查询逻辑：这是一个“离散观测点取逻辑或”的查询。"
            " 只要命中任一观测点 {points}，就说明 `{left_alias}` 的 `{left_state}`"
            " 与 `{right_alias}` 的 `{right_state}` 可以在同一个观测时刻共存。"
        ).format(
            points=_preview_items(post_step_matches, "post_step({})"),
            left_alias=left_machine_alias,
            left_state=left_state_path,
            right_alias=right_machine_alias,
            right_state=right_state_path,
        )

    if open_interval_matches:
        left_start, left_end, right_start, right_end = open_interval_matches[0]
        return (
            "查询逻辑：这是一个“连续时间窗口重叠”的查询。"
            " 只要 `{left_alias}` 的 `{left_state}` 可落在 `({left_start}, {left_end})`，"
            " 且 `{right_alias}` 的 `{right_state}` 可落在 `({right_start}, {right_end})`，"
            " 并且两段区间存在公共时间点，就能构造出共存。"
        ).format(
            left_alias=left_machine_alias,
            left_state=left_state_path,
            left_start=left_start,
            left_end=left_end,
            right_alias=right_machine_alias,
            right_state=right_state_path,
            right_start=right_start,
            right_end=right_end,
        )

    return (
        "查询逻辑：当前导入轨迹里没有任何候选观测位置，因此不存在可构造的共存点，"
        " 这个查询恒为假。"
    )


def _prepare_state_coexistence_problem(
    xml_path: str,
    left_machine_alias: str,
    left_state_ref: str,
    right_machine_alias: str,
    right_state_ref: str,
    observation_scope: str,
    machine_name: Optional[str],
    interaction_name: Optional[str],
    tick_duration_ms: Optional[float],
) -> _PreparedStateCoexistenceProblem:
    """Prepare one coexistence query into runtime traces plus Z3 terms."""
    phase10_report = build_sysdesim_phase10_report(
        xml_path,
        machine_name=machine_name,
        interaction_name=interaction_name,
        tick_duration_ms=tick_duration_ms,
    )
    output_index = _output_index_by_alias(phase10_report)
    trace_index = _trace_index_by_alias(phase10_report)

    if left_machine_alias not in output_index:
        raise KeyError("Unknown machine alias: {!r}".format(left_machine_alias))
    if right_machine_alias not in output_index:
        raise KeyError("Unknown machine alias: {!r}".format(right_machine_alias))

    left_state_path = _resolve_state_path(
        output_index[left_machine_alias].machine, left_state_ref
    )
    right_state_path = _resolve_state_path(
        output_index[right_machine_alias].machine, right_state_ref
    )

    symbol_vars = _symbol_vars(phase10_report)
    base_constraints = tuple(_build_base_time_constraints(phase10_report, symbol_vars))
    left_trace = trace_index[left_machine_alias]
    right_trace = trace_index[right_machine_alias]

    candidate_terms = []
    candidate_meta = []
    post_step_matches = []
    open_interval_matches = []

    if observation_scope in {"post_step", "both"}:
        for left_step, right_step in zip(left_trace.steps, right_trace.steps):
            if (
                left_step.post_state_path == left_state_path
                and right_step.post_state_path == right_state_path
            ):
                candidate_terms.append(z3.BoolVal(True))
                candidate_meta.append(("post_step", left_step.step_id, None, None))
                post_step_matches.append(left_step.step_id)

    if observation_scope in {"open_interval", "both"}:
        left_windows = [
            item for item in left_trace.state_windows if item.state_path == left_state_path
        ]
        right_windows = [
            item
            for item in right_trace.state_windows
            if item.state_path == right_state_path
        ]
        for left_window in left_windows:
            for right_window in right_windows:
                candidate_terms.append(
                    z3.And(
                        symbol_vars[left_window.start_symbol]
                        < symbol_vars[right_window.end_symbol],
                        symbol_vars[right_window.start_symbol]
                        < symbol_vars[left_window.end_symbol],
                    )
                )
                candidate_meta.append(
                    (
                        "open_interval",
                        left_window.source_step_id,
                        left_window.start_symbol,
                        left_window.end_symbol,
                    )
                )
                open_interval_matches.append(
                    (
                        left_window.start_symbol,
                        left_window.end_symbol,
                        right_window.start_symbol,
                        right_window.end_symbol,
                    )
                )

    candidate_notes = _build_candidate_summary_notes(
        left_machine_alias=left_machine_alias,
        left_state_path=left_state_path,
        left_trace=left_trace,
        right_machine_alias=right_machine_alias,
        right_state_path=right_state_path,
        right_trace=right_trace,
        post_step_matches=tuple(post_step_matches),
        open_interval_matches=tuple(open_interval_matches),
    )
    query_summary = _build_query_summary(
        left_machine_alias=left_machine_alias,
        left_state_path=left_state_path,
        right_machine_alias=right_machine_alias,
        right_state_path=right_state_path,
        post_step_matches=tuple(post_step_matches),
        open_interval_matches=tuple(open_interval_matches),
    )

    return _PreparedStateCoexistenceProblem(
        phase10_report=phase10_report,
        symbol_vars=symbol_vars,
        base_constraints=base_constraints,
        left_state_path=left_state_path,
        right_state_path=right_state_path,
        candidate_terms=tuple(candidate_terms),
        candidate_meta=tuple(candidate_meta),
        candidate_count=len(candidate_terms),
        query_summary=query_summary,
        candidate_notes=tuple(candidate_notes),
    )


def _build_witness_steps(
    phase10_report: SysDeSimPhase10Report,
    model: z3.ModelRef,
    symbol_vars: Dict[str, z3.ArithRef],
) -> Tuple[SysDeSimTimelineWitnessStep, ...]:
    """Build the readable witness step table from one satisfying model."""
    witness_steps = []
    for step in phase10_report.scenario.steps:
        states = []
        for trace in phase10_report.traces:
            execution = next(item for item in trace.steps if item.step_id == step.step_id)
            state_text = execution.post_state_path
            if execution.stabilized_state_path != execution.post_state_path:
                state_text = "{} -> {}".format(
                    execution.post_state_path, execution.stabilized_state_path
                )
            states.append((trace.machine_alias, state_text))

        actions = []
        for action in step.actions:
            if isinstance(action, SysDeSimTimelineScenarioEmitAction):
                actions.append("emit({})".format(action.event_name))
            elif isinstance(action, SysDeSimTimelineScenarioSetInputAction):
                actions.append(
                    "SetInput({}={})".format(action.input_name, action.value_text)
                )

        witness_steps.append(
            SysDeSimTimelineWitnessStep(
                step_id=step.step_id,
                time_symbol=step.time_symbol,
                time_value_text=_z3_value_to_text(model, symbol_vars[step.time_symbol]),
                actions=tuple(actions),
                machine_states=tuple(states),
                source_observation_ids=step.source_observation_ids,
            )
        )
    return tuple(witness_steps)


def _render_scenario_actions(actions: Tuple[object, ...]) -> Tuple[str, ...]:
    """Render one scenario action tuple into short human-readable text."""
    rendered = []
    for action in actions:
        if isinstance(action, SysDeSimTimelineScenarioEmitAction):
            rendered.append("emit({})".format(action.event_name))
        elif isinstance(action, SysDeSimTimelineScenarioSetInputAction):
            rendered.append(
                "SetInput({}={})".format(action.input_name, action.value_text)
            )
    return tuple(rendered)


def _decimal_from_text(value_text: str) -> Decimal:
    """Convert one stable decimal text into :class:`decimal.Decimal`."""
    return Decimal(value_text)


def build_sysdesim_state_coexistence_timeline_report(
    xml_path: str,
    left_machine_alias: str,
    left_state_ref: str,
    right_machine_alias: str,
    right_state_ref: str,
    observation_scope: str = "both",
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
) -> SysDeSimStateCoexistenceTimelineReport:
    """
    Build one single solved timeline for a coexistence query.

    The report intentionally focuses on one witness timeline only. When the
    query is satisfiable, it returns each observed step and each hidden
    auto-transition occurrence with their solved times and the current state of
    every imported output machine after that point.

    :param xml_path: Source SysDeSim XML path.
    :type xml_path: str
    :param left_machine_alias: Output alias of the first machine.
    :type left_machine_alias: str
    :param left_state_ref: State name or full path inside the first machine.
    :type left_state_ref: str
    :param right_machine_alias: Output alias of the second machine.
    :type right_machine_alias: str
    :param right_state_ref: State name or full path inside the second machine.
    :type right_state_ref: str
    :param observation_scope: ``post_step``, ``open_interval``, or ``both``.
    :type observation_scope: str
    :param machine_name: Optional machine selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration for compatibility export.
    :type tick_duration_ms: float, optional
    :return: One concise solved timeline report.
    :rtype: SysDeSimStateCoexistenceTimelineReport
    """
    coexistence = solve_sysdesim_state_coexistence(
        xml_path=xml_path,
        left_machine_alias=left_machine_alias,
        left_state_ref=left_state_ref,
        right_machine_alias=right_machine_alias,
        right_state_ref=right_state_ref,
        observation_scope=observation_scope,
        machine_name=machine_name,
        interaction_name=interaction_name,
        tick_duration_ms=tick_duration_ms,
    )
    if coexistence.status != "sat":
        return SysDeSimStateCoexistenceTimelineReport(
            status=coexistence.status,
            solver_status=coexistence.solver_status,
            time_domain="real",
            left_machine_alias=coexistence.left_machine_alias,
            left_state_path=coexistence.left_state_path,
            right_machine_alias=coexistence.right_machine_alias,
            right_state_path=coexistence.right_state_path,
            reason=coexistence.reason,
            first_coexistence_symbol=None,
            first_coexistence_time_text=None,
            first_coexistence_note=None,
            timeline_points=(),
        )

    phase10_report = build_sysdesim_phase10_report(
        xml_path,
        machine_name=machine_name,
        interaction_name=interaction_name,
        tick_duration_ms=tick_duration_ms,
    )
    time_value_by_symbol = dict(coexistence.time_values)
    machine_order = [trace.machine_alias for trace in phase10_report.traces]
    current_states = {
        trace.machine_alias: trace.initial_state_path for trace in phase10_report.traces
    }

    events = []
    order = 0
    for scenario_step in phase10_report.scenario.steps:
        step_updates = []
        for trace in phase10_report.traces:
            execution = _step_by_id(trace, scenario_step.step_id)
            step_updates.append((trace.machine_alias, execution.post_state_path))
        events.append(
            {
                "time_text": time_value_by_symbol[scenario_step.time_symbol],
                "time_value": _decimal_from_text(
                    time_value_by_symbol[scenario_step.time_symbol]
                ),
                "order": order,
                "symbol": scenario_step.time_symbol,
                "point_kind": "step",
                "point_label": scenario_step.step_id,
                "actions": _render_scenario_actions(scenario_step.actions),
                "updates": tuple(step_updates),
            }
        )
        order += 1

        for trace in phase10_report.traces:
            execution = _step_by_id(trace, scenario_step.step_id)
            for occurrence in execution.auto_occurrences:
                events.append(
                    {
                        "time_text": time_value_by_symbol[occurrence.occurrence_symbol],
                        "time_value": _decimal_from_text(
                            time_value_by_symbol[occurrence.occurrence_symbol]
                        ),
                        "order": order,
                        "symbol": occurrence.occurrence_symbol,
                        "point_kind": "auto",
                        "point_label": occurrence.source_step_id,
                        "actions": (
                            "hidden_auto({}: {} -> {})".format(
                                trace.machine_alias,
                                occurrence.from_state_path,
                                occurrence.to_state_path,
                            ),
                        ),
                        "updates": (
                            (trace.machine_alias, occurrence.to_state_path),
                        ),
                    }
                )
                order += 1

    events.sort(key=lambda item: (item["time_value"], item["order"]))

    timeline_points = []
    first_symbol = None
    first_time_text = None
    first_note = None
    for event in events:
        for machine_alias, state_path in event["updates"]:
            current_states[machine_alias] = state_path
        machine_states = tuple(
            (machine_alias, current_states[machine_alias])
            for machine_alias in machine_order
        )
        is_coexistent = (
            current_states[left_machine_alias] == coexistence.left_state_path
            and current_states[right_machine_alias] == coexistence.right_state_path
        )
        if first_symbol is None and is_coexistent:
            first_symbol = event["symbol"]
            first_time_text = event["time_text"]
            first_note = (
                "从 `{symbol}` 对应的时刻开始，`{left_alias}` 处于 `{left_state}`，"
                "`{right_alias}` 处于 `{right_state}`，因此两者开始共存。"
            ).format(
                symbol=event["symbol"],
                left_alias=left_machine_alias,
                left_state=coexistence.left_state_path,
                right_alias=right_machine_alias,
                right_state=coexistence.right_state_path,
            )
        timeline_points.append(
            SysDeSimStateCoexistenceTimelinePoint(
                symbol=event["symbol"],
                time_value_text=event["time_text"],
                point_kind=event["point_kind"],
                point_label=event["point_label"],
                actions=event["actions"],
                machine_states=machine_states,
                is_coexistent=is_coexistent,
            )
        )

    return SysDeSimStateCoexistenceTimelineReport(
        status=coexistence.status,
        solver_status=coexistence.solver_status,
        time_domain="real",
        left_machine_alias=coexistence.left_machine_alias,
        left_state_path=coexistence.left_state_path,
        right_machine_alias=coexistence.right_machine_alias,
        right_state_path=coexistence.right_state_path,
        reason=None,
        first_coexistence_symbol=first_symbol,
        first_coexistence_time_text=first_time_text,
        first_coexistence_note=first_note,
        timeline_points=tuple(timeline_points),
    )


def build_sysdesim_state_coexistence_constraint_preview(
    xml_path: str,
    left_machine_alias: str,
    left_state_ref: str,
    right_machine_alias: str,
    right_state_ref: str,
    observation_scope: str = "both",
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
) -> SysDeSimStateCoexistenceConstraintPreview:
    """
    Build a human-readable Z3 constraint preview for one coexistence query.

    :param xml_path: Source SysDeSim XML path.
    :type xml_path: str
    :param left_machine_alias: Output alias of the first machine.
    :type left_machine_alias: str
    :param left_state_ref: State name or full path inside the first machine.
    :type left_state_ref: str
    :param right_machine_alias: Output alias of the second machine.
    :type right_machine_alias: str
    :param right_state_ref: State name or full path inside the second machine.
    :type right_state_ref: str
    :param observation_scope: ``post_step``, ``open_interval``, or ``both``.
    :type observation_scope: str
    :param machine_name: Optional machine selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration for compatibility export.
    :type tick_duration_ms: float, optional
    :return: Symbol meanings plus the concrete Z3 constraints.
    :rtype: SysDeSimStateCoexistenceConstraintPreview
    """
    if observation_scope not in {"post_step", "open_interval", "both"}:
        raise ValueError("Unsupported observation_scope: {!r}".format(observation_scope))

    prepared = _prepare_state_coexistence_problem(
        xml_path=xml_path,
        left_machine_alias=left_machine_alias,
        left_state_ref=left_state_ref,
        right_machine_alias=right_machine_alias,
        right_state_ref=right_state_ref,
        observation_scope=observation_scope,
        machine_name=machine_name,
        interaction_name=interaction_name,
        tick_duration_ms=tick_duration_ms,
    )

    symbol_meanings = []
    for step in prepared.phase10_report.scenario.steps:
        symbol_meanings.append(
            (
                step.time_symbol,
                "场景 step `{}` 的观测时刻。".format(step.step_id),
            )
        )
    for trace in prepared.phase10_report.traces:
        for step in trace.steps:
            for item in step.auto_occurrences:
                symbol_meanings.append(
                    (
                        item.occurrence_symbol,
                        "隐藏 auto occurrence：{} 在 step `{}` 之后的内部发生时刻。".format(
                            "{} -> {}".format(item.from_state_path, item.to_state_path),
                            item.source_step_id,
                        ),
                    )
                )

    if prepared.candidate_terms:
        query_constraint = str(z3.Or(*prepared.candidate_terms))
    else:
        query_constraint = str(z3.BoolVal(False))

    return SysDeSimStateCoexistenceConstraintPreview(
        left_machine_alias=left_machine_alias,
        left_state_path=prepared.left_state_path,
        right_machine_alias=right_machine_alias,
        right_state_path=prepared.right_state_path,
        symbol_meanings=tuple(symbol_meanings),
        base_constraints=tuple(str(item) for item in prepared.base_constraints),
        query_summary=prepared.query_summary,
        query_constraint=query_constraint,
        candidate_count=prepared.candidate_count,
        candidate_notes=prepared.candidate_notes,
    )


def solve_sysdesim_state_coexistence(
    xml_path: str,
    left_machine_alias: str,
    left_state_ref: str,
    right_machine_alias: str,
    right_state_ref: str,
    observation_scope: str = "both",
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
) -> SysDeSimStateCoexistenceResult:
    """
    Solve whether two machine states can coexist under the imported timeline.

    :param xml_path: Source SysDeSim XML path.
    :type xml_path: str
    :param left_machine_alias: Output alias of the first machine.
    :type left_machine_alias: str
    :param left_state_ref: State name or full path inside the first machine.
    :type left_state_ref: str
    :param right_machine_alias: Output alias of the second machine.
    :type right_machine_alias: str
    :param right_state_ref: State name or full path inside the second machine.
    :type right_state_ref: str
    :param observation_scope: ``post_step``, ``open_interval``, or ``both``.
    :type observation_scope: str
    :param machine_name: Optional machine selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration for compatibility export.
    :type tick_duration_ms: float, optional
    :return: Exact Z3 result plus witness when satisfiable.
    :rtype: SysDeSimStateCoexistenceResult
    """
    if observation_scope not in {"post_step", "open_interval", "both"}:
        raise ValueError("Unsupported observation_scope: {!r}".format(observation_scope))

    prepared = _prepare_state_coexistence_problem(
        xml_path=xml_path,
        left_machine_alias=left_machine_alias,
        left_state_ref=left_state_ref,
        right_machine_alias=right_machine_alias,
        right_state_ref=right_state_ref,
        observation_scope=observation_scope,
        machine_name=machine_name,
        interaction_name=interaction_name,
        tick_duration_ms=tick_duration_ms,
    )
    phase10_report = prepared.phase10_report
    symbol_vars = prepared.symbol_vars
    base_constraints = list(prepared.base_constraints)
    left_state_path = prepared.left_state_path
    right_state_path = prepared.right_state_path

    base_solver = z3.Solver()
    base_solver.add(*base_constraints)
    base_status = base_solver.check()
    if base_status != z3.sat:
        return SysDeSimStateCoexistenceResult(
            status="unsat",
            solver_status=str(base_status),
            left_machine_alias=left_machine_alias,
            left_state_path=left_state_path,
            right_machine_alias=right_machine_alias,
            right_state_path=right_state_path,
            observation_kind=None,
            reason="The imported scenario timing constraints are themselves unsatisfiable.",
            time_values=(),
            witness_steps=(),
            witness_notes=("base_timing_unsat",),
        )

    candidate_terms = list(prepared.candidate_terms)
    candidate_meta = list(prepared.candidate_meta)

    if candidate_terms:
        violation = z3.Or(*candidate_terms)
    else:
        violation = z3.BoolVal(False)

    solver = z3.Solver()
    solver.add(*base_constraints)
    solver.add(violation)
    result = solver.check()

    if result == z3.sat:
        model = solver.model()
        observation_kind = None
        witness_notes = []
        for meta, term in zip(candidate_meta, candidate_terms):
            if z3.is_true(model.evaluate(term, model_completion=True)):
                observation_kind = meta[0]
                if observation_kind == "post_step":
                    witness_notes.append("violation_at_post_step={}".format(meta[1]))
                else:
                    witness_notes.append(
                        "violation_interval={}..{}".format(meta[2], meta[3])
                    )
                break

        ordered_symbols = sorted(symbol_vars)
        return SysDeSimStateCoexistenceResult(
            status="sat",
            solver_status="sat",
            left_machine_alias=left_machine_alias,
            left_state_path=left_state_path,
            right_machine_alias=right_machine_alias,
            right_state_path=right_state_path,
            observation_kind=observation_kind,
            reason=None,
            time_values=tuple(
                (symbol, _z3_value_to_text(model, symbol_vars[symbol]))
                for symbol in ordered_symbols
            ),
            witness_steps=_build_witness_steps(phase10_report, model, symbol_vars),
            witness_notes=tuple(witness_notes),
        )

    if candidate_terms:
        reason = (
            "Both states appear in the discrete trajectories, but the timing "
            "constraints leave no overlapping observation point."
        )
    else:
        trace_index = _trace_index_by_alias(phase10_report)
        left_trace = trace_index[left_machine_alias]
        right_trace = trace_index[right_machine_alias]
        left_seen = any(
            item.post_state_path == left_state_path or item.stabilized_state_path == left_state_path
            for item in left_trace.steps
        ) or any(item.state_path == left_state_path for item in left_trace.state_windows)
        right_seen = any(
            item.post_state_path == right_state_path or item.stabilized_state_path == right_state_path
            for item in right_trace.steps
        ) or any(item.state_path == right_state_path for item in right_trace.state_windows)
        if not left_seen and not right_seen:
            reason = "Neither queried state appears anywhere in the imported trajectories."
        elif not left_seen:
            reason = "The left queried state never appears in the imported trajectory."
        elif not right_seen:
            reason = "The right queried state never appears in the imported trajectory."
        else:
            reason = (
                "The queried states appear separately, but never on the same "
                "post-step point or open interval."
            )

    return SysDeSimStateCoexistenceResult(
        status="unsat",
        solver_status=str(result),
        left_machine_alias=left_machine_alias,
        left_state_path=left_state_path,
        right_machine_alias=right_machine_alias,
        right_state_path=right_state_path,
        observation_kind=None,
        reason=reason,
        time_values=(),
        witness_steps=(),
        witness_notes=(),
    )


__all__ = [
    "SysDeSimNormalizedTemporalConstraint",
    "SysDeSimPhase9Output",
    "SysDeSimPhase9Report",
    "SysDeSimPhase10Report",
    "SysDeSimStateCoexistenceConstraintPreview",
    "SysDeSimStateCoexistenceResult",
    "SysDeSimStateCoexistenceTimelinePoint",
    "SysDeSimStateCoexistenceTimelineReport",
    "SysDeSimTimelineAutoOccurrence",
    "SysDeSimTimelineMachineBinding",
    "SysDeSimTimelineMachineTrace",
    "SysDeSimTimelineScenario",
    "SysDeSimTimelineScenarioEmitAction",
    "SysDeSimTimelineScenarioSetInputAction",
    "SysDeSimTimelineScenarioStep",
    "SysDeSimTimelineStateWindow",
    "SysDeSimTimelineStepExecution",
    "SysDeSimTimelineWitnessStep",
    "build_sysdesim_state_coexistence_constraint_preview",
    "build_sysdesim_state_coexistence_timeline_report",
    "build_sysdesim_phase9_report",
    "build_sysdesim_phase10_report",
    "solve_sysdesim_state_coexistence",
]

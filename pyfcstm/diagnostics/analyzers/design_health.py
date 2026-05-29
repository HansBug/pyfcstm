"""Design-health diagnostics derived from inspect-surface data."""

import re
from typing import TYPE_CHECKING, Iterable, List

from ...utils.validate import ModelDiagnostic
from .data_flow import collect_data_flow_warnings
from .redundancy import collect_redundancy_warnings
from .structural import collect_structural_warnings

if TYPE_CHECKING:  # pragma: no cover - import-time type hints only
    from ..inspect import (
        ActionInfo,
        EventInfo,
        ForcedTransitionInfo,
        StateInfo,
        TransitionInfo,
        VariableInfo,
    )


def collect_design_health_warnings(
    states: Iterable['StateInfo'],
    transitions: Iterable['TransitionInfo'],
    variables: Iterable['VariableInfo'],
    events: Iterable['EventInfo'],
    actions: Iterable['ActionInfo'],
    forced_transitions: Iterable['ForcedTransitionInfo'],
    reachability_graph,
) -> List[ModelDiagnostic]:
    """Collect design-health warning diagnostics from inspect payloads."""
    diagnostics: List[ModelDiagnostic] = []
    states = list(states)
    transitions = list(transitions)
    variables = list(variables)
    events = list(events)
    actions = list(actions)
    forced_transitions = list(forced_transitions)
    diagnostics.extend(_unreachable_state_diagnostics(states, reachability_graph))
    diagnostics.extend(_guard_const_false_diagnostics(transitions))
    diagnostics.extend(_unused_event_diagnostics(events))
    diagnostics.extend(collect_structural_warnings(
        states,
        transitions,
        actions,
        forced_transitions,
        reachability_graph,
    ))
    diagnostics.extend(collect_data_flow_warnings(variables))
    diagnostics.extend(collect_redundancy_warnings(transitions, events))
    return diagnostics


def _unreachable_state_diagnostics(states, reachability_graph) -> List[ModelDiagnostic]:
    if not states:
        return []
    root_path = states[0].path
    reachable = set(reachability_graph.get(root_path, ()))
    reachable.add(root_path)
    diagnostics: List[ModelDiagnostic] = []
    for state in states:
        if state.is_pseudo or state.path in reachable:
            continue
        diagnostics.append(
            ModelDiagnostic(
                code='W_UNREACHABLE_STATE',
                severity='warning',
                message=f'State {state.path!r} is unreachable from the root entry path.',
                refs={'state_path': state.path},
            )
        )
    return diagnostics


def _guard_const_false_diagnostics(transitions) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for transition in transitions:
        if _is_minimal_const_false_guard(transition.guard):
            diagnostics.append(
                ModelDiagnostic(
                    code='W_GUARD_CONST_FALSE',
                    severity='warning',
                    message=(
                        f'Transition {transition.from_path!r} -> {transition.to_path!r} '
                        'has a guard that is statically false.'
                    ),
                    refs={'transition_span': None, 'folded_value': False},
                )
            )
    return diagnostics


def _is_minimal_const_false_guard(guard_text) -> bool:
    if guard_text is None:
        return False
    normalized = guard_text.strip().lower()
    if normalized in {'false', '0'}:
        return True
    match = re.match(r'^\s*([+-]?\d+)\s*==\s*([+-]?\d+)\s*$', guard_text)
    if match is not None:
        return int(match.group(1)) != int(match.group(2))
    return False


def _unused_event_diagnostics(events) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for event in events:
        if not event.is_declared or event.is_used:
            continue
        diagnostics.append(
            ModelDiagnostic(
                code='W_UNUSED_EVENT',
                severity='warning',
                message=f'Event {event.qualified_name!r} is declared but never used.',
                refs={
                    'event_qualified_name': event.qualified_name,
                    'scope': event.scope,
                },
            )
        )
    return diagnostics

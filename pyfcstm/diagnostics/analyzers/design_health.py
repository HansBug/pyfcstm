"""Design-health diagnostics derived from inspect-surface data."""

from typing import TYPE_CHECKING, Iterable, List, Optional

from ...utils.validate import ModelDiagnostic
from .const_fold import collect_const_fold_warnings
from .data_flow import collect_data_flow_warnings
from .naming import collect_naming_warnings
from .redundancy import collect_redundancy_warnings
from .structural import collect_structural_warnings
from .thresholds import collect_threshold_warnings
from .transition_info import collect_transition_infos
from .type_shape import collect_type_warnings

if TYPE_CHECKING:  # pragma: no cover - import-time type hints only
    from ..inspect import (
        ActionInfo,
        EventInfo,
        ForcedTransitionInfo,
        ModelMetrics,
        StateInfo,
        TransitionInfo,
        VariableInfo,
    )
    from ...model.model import StateMachine


def collect_design_health_warnings(
    states: Iterable['StateInfo'],
    transitions: Iterable['TransitionInfo'],
    variables: Iterable['VariableInfo'],
    events: Iterable['EventInfo'],
    actions: Iterable['ActionInfo'],
    forced_transitions: Iterable['ForcedTransitionInfo'],
    metrics: 'ModelMetrics',
    reachability_graph,
    root_state_path: Optional[str] = None,
    deep_hierarchy_threshold: int = 6,
    large_composite_threshold: int = 12,
    var_to_leaf_ratio_threshold: float = 2.0,
    machine: Optional['StateMachine'] = None,
) -> List[ModelDiagnostic]:
    """Collect design-health warning diagnostics from inspect payloads."""
    diagnostics: List[ModelDiagnostic] = []
    states = list(states)
    transitions = list(transitions)
    variables = list(variables)
    events = list(events)
    actions = list(actions)
    forced_transitions = list(forced_transitions)
    resolved_root_state_path = _resolve_root_state_path(states, root_state_path)
    diagnostics.extend(_unreachable_state_diagnostics(
        states,
        reachability_graph,
        resolved_root_state_path,
    ))
    diagnostics.extend(collect_const_fold_warnings(machine))
    diagnostics.extend(_unused_event_diagnostics(events))
    diagnostics.extend(collect_structural_warnings(
        states,
        transitions,
        actions,
        forced_transitions,
        reachability_graph,
        root_state_path=resolved_root_state_path,
    ))
    diagnostics.extend(collect_threshold_warnings(
        states,
        metrics,
        deep_hierarchy_threshold=deep_hierarchy_threshold,
        large_composite_threshold=large_composite_threshold,
        var_to_leaf_ratio_threshold=var_to_leaf_ratio_threshold,
    ))
    diagnostics.extend(collect_naming_warnings(actions))
    diagnostics.extend(collect_type_warnings(variables))
    diagnostics.extend(collect_data_flow_warnings(variables))
    diagnostics.extend(collect_redundancy_warnings(transitions, events, states))
    diagnostics.extend(collect_transition_infos(states, transitions))
    return diagnostics


def _resolve_root_state_path(states, root_state_path):
    if root_state_path is not None:
        return root_state_path
    if not states:
        return None
    return states[0].path


def _unreachable_state_diagnostics(states, reachability_graph, root_state_path) -> List[ModelDiagnostic]:
    if not states or root_state_path is None:
        return []
    reachable = set(reachability_graph.get(root_state_path, ()))
    reachable.add(root_state_path)
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

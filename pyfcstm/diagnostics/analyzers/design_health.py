"""Design-health diagnostics derived from inspect-surface data.

The reachability helper keeps the root itself in the result, even when the
inspect graph only lists outgoing paths:

    >>> sorted(_reachable_state_paths({'Root': ('Root.Active',)}, 'Root'))
    ['Root', 'Root.Active']
"""

import re
from dataclasses import replace
from typing import TYPE_CHECKING, Iterable, List, Optional

from ..suggested_fix import refs_with_suggested_fix
from ...utils.validate import ModelDiagnostic
from .combo import collect_combo_warnings
from .const_fold import collect_const_fold_warnings
from .data_flow import collect_data_flow_warnings
from .naming import collect_naming_warnings
from .numeric import collect_numeric_warnings
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
    diagnostics.extend(_unreachable_transition_diagnostics(
        states,
        transitions,
        reachability_graph,
        resolved_root_state_path,
    ))
    diagnostics.extend(
        collect_const_fold_warnings(machine)
        if machine is not None
        else _guard_const_false_diagnostics(transitions)
    )
    diagnostics.extend(collect_combo_warnings(machine))
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
    diagnostics.extend(collect_data_flow_warnings(variables, machine))
    diagnostics.extend(collect_redundancy_warnings(transitions, events, states))
    diagnostics.extend(collect_transition_infos(states, transitions))
    diagnostics.extend(collect_numeric_warnings(machine))
    return _with_suggested_fixes(diagnostics)


def _with_suggested_fixes(diagnostics: List[ModelDiagnostic]) -> List[ModelDiagnostic]:
    return [
        replace(diag, refs=refs_with_suggested_fix(diag.code, diag.refs))
        for diag in diagnostics
    ]


def _resolve_root_state_path(states, root_state_path):
    if root_state_path is not None:
        return root_state_path
    if not states:
        return None
    return states[0].path


def _unreachable_state_diagnostics(states, reachability_graph, root_state_path) -> List[ModelDiagnostic]:
    if not states or root_state_path is None:
        return []
    reachable = _reachable_state_paths(reachability_graph, root_state_path)
    diagnostics: List[ModelDiagnostic] = []
    for state in states:
        if not state.is_leaf or state.is_pseudo or state.path in reachable:
            continue
        diagnostics.append(
            ModelDiagnostic(
                code='W_UNREACHABLE_STATE',
                severity='warning',
                message=f'State {state.path!r} is unreachable from the root entry path.',
                span=state.span,
                refs={'state_path': state.path},
            )
        )
    return diagnostics


def _reachable_state_paths(reachability_graph, root_state_path):
    reachable = set(reachability_graph.get(root_state_path, ()))
    reachable.add(root_state_path)
    return reachable


def _unreachable_transition_diagnostics(
        states,
        transitions,
        reachability_graph,
        root_state_path,
) -> List[ModelDiagnostic]:
    """Report authored transitions outside the guard-agnostic topology.

    A normal transition is selected from its source state.  An initial
    transition is selected by the composite that owns its ``[*]`` entry; its
    owner is recoverable from the direct target path in the inspect payload.
    Combo relay edges are projected to one warning per authored combo origin so
    generated edges do not multiply one source finding.
    """
    if not states or root_state_path is None:
        return []
    state_paths = {state.path for state in states}
    reachable = _reachable_state_paths(reachability_graph, root_state_path)
    diagnostics: List[ModelDiagnostic] = []
    emitted_combo_origins = set()
    for transition in transitions:
        combo_origin_ids = tuple(sorted({
            ref.origin_id
            for ref in transition.combo_origin_refs
            if isinstance(ref.origin_id, str)
        }))
        if combo_origin_ids:
            for origin_id in combo_origin_ids:
                if origin_id in emitted_combo_origins:
                    continue
                emitted_combo_origins.add(origin_id)
                origin_ref = next(
                    (
                        ref for ref in transition.combo_origin_refs
                        if ref.origin_id == origin_id
                    ),
                    None,
                )
                if origin_ref is None or origin_ref.target_path is None:
                    continue
                source_state_path = origin_ref.source_path
                selection_owner_path = origin_ref.selection_owner_path
                lookup_path = selection_owner_path or source_state_path
                if lookup_path is None:
                    continue
                if lookup_path in reachable:
                    continue
                diagnostics.append(ModelDiagnostic(
                    code='W_UNREACHABLE_TRANSITION',
                    severity='warning',
                    message=(
                        f'Transition {origin_id!r} has a source outside the '
                        'guard-agnostic root-reachable topology.'
                    ),
                    span=transition.span if origin_ref is None else origin_ref.transition_span,
                    refs={
                        'reason': 'source_unreachable',
                        'verification_scope': 'topological_only',
                        'from_path': '[*]' if source_state_path is None else source_state_path,
                        'to_path': origin_ref.target_path,
                        'source_state_path': source_state_path,
                        'selection_owner_path': selection_owner_path,
                        'transition_index': None,
                        'forced_origin': None,
                        'combo_origin_ids': [origin_id],
                    },
                ))
            continue

        source_state_path, selection_owner_path = _transition_selection_paths(
            transition,
            state_paths,
        )
        if selection_owner_path is None or selection_owner_path not in state_paths:
            continue
        if selection_owner_path in reachable:
            continue

        forced_expansion = transition.is_forced
        diagnostics.append(ModelDiagnostic(
            code='W_UNREACHABLE_TRANSITION',
            severity='warning',
            message=(
                (
                    f'Generated forced transition expansion '
                    f'{transition.from_path!r} -> {transition.to_path!r} '
                    'has a source outside the guard-agnostic root-reachable topology.'
                )
                if forced_expansion else (
                    f'Transition {transition.from_path!r} -> {transition.to_path!r} '
                    'has a source outside the guard-agnostic root-reachable topology.'
                )
            ),
            span=transition.span,
            refs={
                'reason': 'source_unreachable',
                'verification_scope': 'topological_only',
                'from_path': transition.from_path,
                'to_path': transition.to_path,
                'source_state_path': source_state_path,
                'selection_owner_path': selection_owner_path if transition.from_path == '[*]' else None,
                'transition_index': transition.transition_index,
                'forced_origin': transition.forced_origin,
                'combo_origin_ids': list(combo_origin_ids),
            },
        ))
    return diagnostics


def _transition_selection_paths(transition, state_paths):
    if transition.from_path != '[*]':
        return transition.from_path, transition.from_path
    if transition.to_path == '[*]' or '.' not in transition.to_path:
        return None, None
    owner_path = transition.to_path.rsplit('.', 1)[0]
    if owner_path not in state_paths:
        return None, None
    return None, owner_path


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
                    span=transition.span,
                    refs={
                        'transition_span': transition.span,
                        'folded_value': False,
                        'from_path': transition.from_path,
                        'to_path': transition.to_path,
                        'guard_text': transition.guard,
                        'transition_index': transition.transition_index,
                    },
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
                span=event.span,
                refs={
                    'event_qualified_name': event.qualified_name,
                    'scope': event.scope,
                },
            )
        )
    return diagnostics

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
from .region_order import collect_region_order_diagnostics
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
        RegionInfo,
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
    regions: Iterable['RegionInfo'] = (),
) -> List[ModelDiagnostic]:
    """
    Collect design-health diagnostics from the inspect payloads of one model.

    This is the aggregator behind :func:`pyfcstm.diagnostics.inspect_model`: it
    runs reachability, structural, threshold, naming, type, data-flow,
    redundancy, transition-info, numeric and region-ordering analyses and
    attaches suggested fixes. A model that declares regions is judged with
    ``regions`` so that region entry selections, region containers and the
    ordering of sibling regions are covered; the model-based analyzers need
    ``machine`` for that.

    :param states: Inspect state records.
    :type states: Iterable[pyfcstm.diagnostics.inspect.StateInfo]
    :param transitions: Inspect transition records.
    :type transitions: Iterable[pyfcstm.diagnostics.inspect.TransitionInfo]
    :param variables: Inspect variable records.
    :type variables: Iterable[pyfcstm.diagnostics.inspect.VariableInfo]
    :param events: Inspect event records.
    :type events: Iterable[pyfcstm.diagnostics.inspect.EventInfo]
    :param actions: Inspect action records.
    :type actions: Iterable[pyfcstm.diagnostics.inspect.ActionInfo]
    :param forced_transitions: Inspect forced-transition records.
    :type forced_transitions: Iterable[pyfcstm.diagnostics.inspect.ForcedTransitionInfo]
    :param metrics: Aggregate metrics of the model.
    :type metrics: pyfcstm.diagnostics.inspect.ModelMetrics
    :param reachability_graph: State path to the state paths it reaches.
    :type reachability_graph: Mapping[str, Sequence[str]]
    :param root_state_path: Root state path, defaults to the first state.
    :type root_state_path: str, optional
    :param deep_hierarchy_threshold: Depth above which ``W_DEEP_HIERARCHY``
        fires, defaults to ``6``.
    :type deep_hierarchy_threshold: int, optional
    :param large_composite_threshold: Child count above which
        ``W_LARGE_COMPOSITE`` fires, defaults to ``12``.
    :type large_composite_threshold: int, optional
    :param var_to_leaf_ratio_threshold: Ratio above which
        ``W_HIGH_VAR_TO_LEAF_RATIO`` fires, defaults to ``2.0``.
    :type var_to_leaf_ratio_threshold: float, optional
    :param machine: The model as written, for the analyzers that read model
        objects, defaults to ``None``.
    :type machine: pyfcstm.model.model.StateMachine, optional
    :param regions: Inspect region records, defaults to ``()``.
    :type regions: Iterable[pyfcstm.diagnostics.inspect.RegionInfo], optional
    :return: All design-health diagnostics, each with its suggested fix.
    :rtype: List[pyfcstm.utils.validate.ModelDiagnostic]

    Example::

        >>> from pyfcstm.diagnostics import inspect_model
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> machine = load_state_machine_from_text('state Root { state A; state B; [*] -> A; }')
        >>> [item.code for item in inspect_model(machine).diagnostics if item.code == 'W_UNREACHABLE_STATE']
        ['W_UNREACHABLE_STATE']
    """
    diagnostics: List[ModelDiagnostic] = []
    states = list(states)
    transitions = list(transitions)
    variables = list(variables)
    events = list(events)
    actions = list(actions)
    forced_transitions = list(forced_transitions)
    regions = list(regions)
    resolved_root_state_path = _resolve_root_state_path(states, root_state_path)
    diagnostics.extend(_unreachable_state_diagnostics(
        states,
        reachability_graph,
        resolved_root_state_path,
    ))
    diagnostics.extend(_unreachable_initial_transition_diagnostics(
        states,
        transitions,
        reachability_graph,
        resolved_root_state_path,
        regions,
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
        regions=regions,
    ))
    diagnostics.extend(collect_threshold_warnings(
        states,
        metrics,
        deep_hierarchy_threshold=deep_hierarchy_threshold,
        large_composite_threshold=large_composite_threshold,
        var_to_leaf_ratio_threshold=var_to_leaf_ratio_threshold,
        regions=regions,
    ))
    diagnostics.extend(collect_naming_warnings(actions))
    diagnostics.extend(collect_type_warnings(variables))
    diagnostics.extend(collect_data_flow_warnings(variables, machine))
    diagnostics.extend(collect_redundancy_warnings(transitions, events, states))
    diagnostics.extend(collect_transition_infos(states, transitions))
    diagnostics.extend(collect_numeric_warnings(machine))
    diagnostics.extend(collect_region_order_diagnostics(machine))
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


def _unreachable_initial_transition_diagnostics(
        states,
        transitions,
        reachability_graph,
        root_state_path,
        regions=(),
) -> List[ModelDiagnostic]:
    """Keep owner-level findings for unreachable composite entry selections."""
    if not states or root_state_path is None:
        return []
    state_paths = {state.path for state in states}
    # A region is entered with its owner, so its entry selection is as
    # reachable as the owner state.
    region_owner = {region.path: region.owner_path for region in regions}
    reachable = _reachable_state_paths(reachability_graph, root_state_path)
    diagnostics: List[ModelDiagnostic] = []
    for transition in transitions:
        if transition.from_path != '[*]' or '.' not in transition.to_path:
            continue
        owner_path = transition.to_path.rsplit('.', 1)[0]
        owner_path = region_owner.get(owner_path, owner_path)
        if owner_path not in state_paths or owner_path in reachable:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_UNREACHABLE_TRANSITION',
            severity='warning',
            message=(
                f'Authored transition {transition.from_path!r} -> '
                f'{transition.to_path!r} is unreachable for reasons: '
                'unreachable_source_state.'
            ),
            span=transition.span,
            refs={
                'from_path': transition.from_path,
                'to_path': transition.to_path,
                'transition_index': transition.transition_index,
                'reasons': ['unreachable_source_state'],
                'source_path': transition.source_path,
                'source_state_path': None,
                'selection_owner_path': owner_path,
                'forced_origin': transition.forced_origin,
                'combo_origin_ids': [],
            },
        ))
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

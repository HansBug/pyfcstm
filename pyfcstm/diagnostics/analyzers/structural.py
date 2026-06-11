"""Structural design-health diagnostics."""

from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Set

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import ActionInfo, ForcedTransitionInfo, StateInfo, TransitionInfo


def collect_structural_warnings(
    states: Iterable['StateInfo'],
    transitions: Iterable['TransitionInfo'],
    actions: Iterable['ActionInfo'],
    forced_transitions: Iterable['ForcedTransitionInfo'],
    reachability_graph,
    root_state_path: Optional[str] = None,
) -> List[ModelDiagnostic]:
    states = list(states)
    transitions = list(transitions)
    actions = list(actions)
    forced_transitions = list(forced_transitions)
    diagnostics: List[ModelDiagnostic] = []
    diagnostics.extend(_deadlock_leaf_warnings(states, transitions))
    diagnostics.extend(_initial_unconditional_missing_warnings(states))
    diagnostics.extend(_forced_never_expands_warnings(forced_transitions))
    diagnostics.extend(_aspect_no_descendant_leaf_warnings(states))
    diagnostics.extend(_dead_named_action_warnings(
        states,
        actions,
        reachability_graph,
        root_state_path,
    ))
    return diagnostics


def _aspect_no_descendant_leaf_warnings(states) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for state in states:
        if not state.is_composite:
            continue
        descendant_leaf_count = sum(
            1
            for desc in states
            if desc.path != state.path
            and desc.path.startswith(state.path + '.')
            and desc.is_leaf
            and not desc.is_pseudo
        )
        if descendant_leaf_count > 0:
            continue
        if state.aspect_before:
            diagnostics.append(_aspect_no_descendant_leaf_diagnostic(state, 'before'))
        if state.aspect_after:
            diagnostics.append(_aspect_no_descendant_leaf_diagnostic(state, 'after'))
    return diagnostics


def _aspect_no_descendant_leaf_diagnostic(state, aspect) -> ModelDiagnostic:
    return ModelDiagnostic(
        code='W_ASPECT_NO_DESCENDANT_LEAF',
        severity='warning',
        message=(
            f'Composite state {state.path!r} declares >> during '
            f'{aspect} but has no descendant non-pseudo leaf state.'
        ),
        span=state.span,
        refs={
            'composite_path': state.path,
            'aspect': aspect,
        },
    )


def _deadlock_leaf_warnings(states, transitions) -> List[ModelDiagnostic]:
    outgoing: Dict[str, int] = {}
    for t in transitions:
        if t.from_path != '[*]':
            outgoing[t.from_path] = outgoing.get(t.from_path, 0) + 1
    diagnostics: List[ModelDiagnostic] = []
    for state in states:
        if not state.is_leaf or state.is_pseudo:
            continue
        if outgoing.get(state.path, 0) > 0:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_DEADLOCK_LEAF',
            span=state.span,
            severity='warning',
            message=f'Leaf state {state.path!r} has no outgoing transition.',
            refs=_deadlock_leaf_refs(state),
        ))
    return diagnostics


def _deadlock_leaf_refs(state) -> Dict[str, str]:
    refs = {
        'state_path': state.path,
        'reason': 'no_outgoing_transition',
    }
    if state.parent_path is not None:
        refs['parent_path'] = state.parent_path
    return refs


def _initial_unconditional_missing_warnings(states) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    states_by_path = {state.path: state for state in states}
    for state in states:
        if not state.is_composite:
            continue
        unconditional = [
            item for item in state.initial_targets
            if item.get('is_unconditional') is True
        ]
        if unconditional:
            continue
        refs = {
            'composite_path': state.path,
            'existing_conditional_count': len(state.initial_targets),
        }
        first_child_name = _first_child_name(state, states_by_path)
        if first_child_name is not None:
            refs['first_child_name'] = first_child_name
        diagnostics.append(ModelDiagnostic(
            code='W_INITIAL_UNCONDITIONAL_MISSING',
            span=state.span,
            severity='warning',
            message=(
                f'Composite state {state.path!r} has no unconditional '
                '[*] entry transition.'
            ),
            refs=refs,
        ))
    return diagnostics


def _first_child_name(state, states_by_path) -> Optional[str]:
    for child_path in state.substates:
        child = states_by_path.get(child_path)
        if child is not None and not child.is_pseudo:
            return child_path.rsplit('.', 1)[-1]
    return None


def _forced_never_expands_warnings(forced_transitions) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for item in forced_transitions:
        if item.expansion_count > 0:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_FORCED_NEVER_EXPANDS',
            span=item.span,
            severity='warning',
            message=(
                f'Forced transition {item.original_raw!r} declares no '
                'concrete expansion in its state scope.'
            ),
            refs={
                'state_path': item.state_path,
                'original_raw': item.original_raw,
            },
        ))
    return diagnostics


def _dead_named_action_warnings(
        states,
        actions,
        reachability_graph,
        root_state_path=None,
) -> List[ModelDiagnostic]:
    if not states and root_state_path is None:
        return []
    root_path = root_state_path or states[0].path
    reachable = set(reachability_graph.get(root_path, ()))
    reachable.add(root_path)
    reachable_action_states = _expand_leaf_reachability_to_action_states(
        states,
        reachable,
    )
    referenced: Set[str] = {
        action.ref_target
        for action in actions
        if action.ref_target is not None and action.state_path in reachable_action_states
    }
    diagnostics: List[ModelDiagnostic] = []
    for action in actions:
        if not action.name or action.is_ref:
            continue
        if action.signature in referenced:
            continue
        if action.state_path in reachable_action_states:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_DEAD_NAMED_ACTION',
            span=action.span,
            severity='warning',
            message=f'Named action {action.signature!r} is unreachable and unreferenced.',
            refs={
                'function_name': action.name,
                'defined_in': action.state_path,
            },
        ))
    return diagnostics


def _expand_leaf_reachability_to_action_states(states, reachable):
    """Expand reachable leaves to ancestor states that can host actions.

    Some callers pass a leaf-only topology view, while the default inspect
    graph may already contain composite paths. Actions can be declared on
    composite states, so a composite is action-reachable when it is already
    reachable or when any reachable descendant leaf sits below it.

    :param states: Inspect state payloads.
    :type states: Iterable[StateInfo]
    :param reachable: Reachable state paths from the root reachability view.
    :type reachable: Iterable[str]
    :return: Reachable paths including ancestor composites of reachable leaves.
    :rtype: Set[str]

    Examples::

        >>> from pyfcstm.diagnostics import StateInfo
        >>> root = StateInfo(
        ...     path='Root',
        ...     name='Root',
        ...     parent_path=None,
        ...     is_leaf=False,
        ...     is_pseudo=False,
        ...     is_composite=True,
        ...     substates=('Root.A',),
        ...     initial_targets=(),
        ...     entry_actions=(),
        ...     during_actions=(),
        ...     exit_actions=(),
        ...     aspect_before=(),
        ...     aspect_after=(),
        ...     has_abstract_action=False,
        ... )
        >>> leaf = StateInfo(
        ...     path='Root.A',
        ...     name='A',
        ...     parent_path='Root',
        ...     is_leaf=True,
        ...     is_pseudo=False,
        ...     is_composite=False,
        ...     substates=(),
        ...     initial_targets=(),
        ...     entry_actions=(),
        ...     during_actions=(),
        ...     exit_actions=(),
        ...     aspect_before=(),
        ...     aspect_after=(),
        ...     has_abstract_action=False,
        ... )
        >>> sorted(_expand_leaf_reachability_to_action_states((root, leaf), {'Root.A'}))
        ['Root', 'Root.A']
    """
    reachable_states = set(reachable)
    for state in states:
        if state.path in reachable_states:
            continue
        prefix = state.path + '.'
        if any(path.startswith(prefix) for path in reachable):
            reachable_states.add(state.path)
    return reachable_states

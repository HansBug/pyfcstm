"""Redundancy and overlap design-health diagnostics."""

from collections import Counter
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Tuple

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import EventInfo, StateInfo, TransitionInfo


def collect_redundancy_warnings(
    transitions: Iterable['TransitionInfo'],
    events: Iterable['EventInfo'],
    states: Iterable['StateInfo'] = (),
) -> List[ModelDiagnostic]:
    transitions = list(transitions)
    states = list(states)
    diagnostics: List[ModelDiagnostic] = []
    diagnostics.extend(_redundant_transition_warnings(transitions))
    diagnostics.extend(_self_transition_nop_warnings(transitions, states))
    diagnostics.extend(_effect_self_assign_warnings(transitions))
    diagnostics.extend(_forced_overrides_normal_warnings(transitions))
    diagnostics.extend(_shadowed_event_warnings(events))
    return diagnostics


def _transition_trigger_key(t: 'TransitionInfo') -> Tuple[str, str, object, object]:
    return t.from_path, t.to_path, t.event, t.guard


def _transition_behavior_key(t: 'TransitionInfo') -> Tuple[str, str, object, object, object]:
    return t.from_path, t.to_path, t.event, t.guard, t.effect


def _redundant_transition_warnings(
        transitions: Iterable['TransitionInfo'],
) -> List[ModelDiagnostic]:
    groups: Dict[Tuple[str, str, object, object, object], List['TransitionInfo']] = {}
    for t in transitions:
        if t.from_path == '[*]':
            continue
        groups.setdefault(_transition_behavior_key(t), []).append(t)
    diagnostics: List[ModelDiagnostic] = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        from_path, to_path, _, _, _ = key
        diagnostics.append(ModelDiagnostic(
            code='W_REDUNDANT_TRANSITION',
            span=items[0].span,
            severity='warning',
            message=(
                f'Transition {from_path!r} -> {to_path!r} is duplicated '
                'with the same event, guard, and effect.'
            ),
            refs={
                'from_path': from_path,
                'to_path': to_path,
                'duplicate_spans': [item.span for item in items],
                'transition_index': items[0].transition_index,
            },
        ))
    return diagnostics


def _self_transition_nop_warnings(
        transitions: Iterable['TransitionInfo'],
        states: Iterable['StateInfo'],
) -> List[ModelDiagnostic]:
    states_by_path = {state.path: state for state in states}
    diagnostics: List[ModelDiagnostic] = []
    for t in transitions:
        if t.from_path != t.to_path:
            continue
        if t.event is not None or t.guard is not None or t.effect is not None:
            continue
        if not _is_lifecycle_free_leaf(t.from_path, states_by_path):
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_SELF_TRANSITION_NOP',
            span=t.span,
            severity='warning',
            message=(
                f'Self transition on {t.from_path!r} has no trigger, '
                'guard, effect, or re-entry lifecycle behavior.'
            ),
            refs={
                'state_path': t.from_path,
                'from_path': t.from_path,
                'to_path': t.to_path,
                'transition_span': t.span,
                'transition_index': t.transition_index,
            },
        ))
    return diagnostics


def _is_lifecycle_free_leaf(
        state_path: str,
        states_by_path: Dict[str, 'StateInfo'],
) -> bool:
    state = states_by_path.get(state_path)
    if state is None or not state.is_leaf or state.is_pseudo:
        return False
    if (
        state.entry_actions
        or state.during_actions
        or state.exit_actions
        or state.aspect_before
        or state.aspect_after
    ):
        return False
    parts = state_path.split('.')
    for index in range(1, len(parts)):
        ancestor = states_by_path.get('.'.join(parts[:index]))
        if ancestor is not None and (ancestor.aspect_before or ancestor.aspect_after):
            return False
    return True


def _effect_self_assign_warnings(transitions: Iterable['TransitionInfo']) -> List[ModelDiagnostic]:
    transitions = list(transitions)
    subjects_by_id = {
        id(t): _public_transition_subject_for_effect_diagnostic(t)
        for t in transitions
    }
    counts = Counter(
        (subjects_by_id[id(t)]['state_path'], var_name)
        for t in transitions
        for var_name in getattr(t, 'effect_self_assigns', ())
    )
    diagnostics: List[ModelDiagnostic] = []
    for t in transitions:
        subject = subjects_by_id[id(t)]
        effect_self_assigns = getattr(t, 'effect_self_assigns', ())
        effect_self_assign_spans = getattr(t, 'effect_self_assign_spans', ())
        for index, var_name in enumerate(effect_self_assigns):
            refs = {
                'state_path': subject['state_path'],
                'transition_span': subject['transition_span'],
                'var_name': var_name,
                'transition_index': t.transition_index,
            }
            refs.update(subject['extra_refs'])
            if (
                subject['can_anchor']
                and subject['state_path'] != '[*]'
                and counts[(subject['state_path'], var_name)] == 1
            ):
                refs['effect_self_assign_anchor'] = var_name
            diagnostics.append(ModelDiagnostic(
                code='W_EFFECT_SELF_ASSIGN',
                span=(
                    effect_self_assign_spans[index]
                    if index < len(effect_self_assign_spans)
                    and effect_self_assign_spans[index] is not None
                    else t.span
                ),
                severity='warning',
                message=f'Transition effect assigns {var_name!r} to itself.',
                refs=refs,
            ))
    return diagnostics


def _public_transition_subject_for_effect_diagnostic(t: 'TransitionInfo') -> Dict[str, object]:
    origin_ref = next(iter(getattr(t, 'combo_origin_refs', ())), None)
    transition_span = getattr(origin_ref, 'transition_span', None) or t.span
    projection_key = getattr(t, 'combo_projection_key', None)
    extra_refs: Dict[str, object] = {}

    if origin_ref is None:
        return {
            'state_path': t.from_path,
            'transition_span': transition_span,
            'extra_refs': extra_refs,
            'can_anchor': True,
        }

    state_path = t.from_path
    if projection_key is None or len(projection_key) < 2:
        extra_refs.update({
            'from_path': state_path,
            'generated_state_path': t.from_path,
            'generated_from_path': t.from_path,
            'generated_to_path': t.to_path,
            'combo_origin_id': origin_ref.origin_id,
        })
        return {
            'state_path': state_path,
            'transition_span': transition_span,
            'extra_refs': extra_refs,
            'can_anchor': False,
        }

    owner_path = projection_key[0]
    projection_kind = projection_key[1]
    can_anchor = False
    if projection_kind == 'state' and len(projection_key) >= 3:
        source_path = projection_key[2]
        if isinstance(source_path, tuple):
            state_path = '.'.join(source_path)
            can_anchor = True
        elif isinstance(source_path, str):
            state_path = source_path
            can_anchor = True
    elif projection_kind == 'entry':
        state_path = '[*]'
        if isinstance(owner_path, tuple):
            extra_refs['combo_owner_path'] = '.'.join(owner_path)
        elif isinstance(owner_path, str):
            extra_refs['combo_owner_path'] = owner_path

    extra_refs.update({
        'from_path': state_path,
        'generated_state_path': t.from_path,
        'generated_from_path': t.from_path,
        'generated_to_path': t.to_path,
        'combo_origin_id': origin_ref.origin_id,
    })
    return {
        'state_path': state_path,
        'transition_span': transition_span,
        'extra_refs': extra_refs,
        'can_anchor': can_anchor,
    }


def _forced_overrides_normal_warnings(transitions: Iterable['TransitionInfo']) -> List[ModelDiagnostic]:
    normal_by_key = {
        _transition_trigger_key(t): t
        for t in transitions
        if not t.is_forced
    }
    diagnostics: List[ModelDiagnostic] = []
    for t in transitions:
        normal_transition = normal_by_key.get(_transition_trigger_key(t))
        if not t.is_forced or normal_transition is None:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_FORCED_OVERRIDES_NORMAL',
            span=t.span,
            severity='warning',
            message=(
                f'Forced transition {t.from_path!r} -> {t.to_path!r} '
                'duplicates a normal transition.'
            ),
            refs={
                'from_path': t.from_path,
                'to_path': t.to_path,
                'forced_declaration_span': t.span,
                'normal_transition_span': normal_transition.span,
            },
        ))
    return diagnostics


def _shadowed_event_warnings(events: Iterable['EventInfo']) -> List[ModelDiagnostic]:
    by_leaf_name: Dict[str, List['EventInfo']] = {}
    for event in events:
        leaf = event.qualified_name.rsplit('.', 1)[-1]
        by_leaf_name.setdefault(leaf, []).append(event)
    diagnostics: List[ModelDiagnostic] = []
    for event_name, items in by_leaf_name.items():
        chain_like = [
            item for item in items
            if item.scope in {'chain', 'absolute'}
        ]
        local_like = [item for item in items if item.scope == 'local']
        if not chain_like or not local_like:
            continue
        for local_event in local_like:
            shadowing_event = _find_shadowing_event(local_event, chain_like)
            if shadowing_event is None:
                continue
            diagnostics.append(ModelDiagnostic(
                code='W_SHADOWED_EVENT',
                span=local_event.span,
                severity='warning',
                message=(
                    f'Local event {local_event.qualified_name!r} shadows '
                    f'a chain event named {event_name!r}.'
                ),
                refs={
                    'event_name': event_name,
                    'local_path': local_event.qualified_name,
                    'chain_path': shadowing_event.qualified_name,
                },
            ))
    return diagnostics


def _find_shadowing_event(
        local_event: 'EventInfo',
        chain_like: Iterable['EventInfo'],
) -> Optional['EventInfo']:
    local_owner = _event_owner_path(local_event.qualified_name)
    candidates = [
        item for item in chain_like
        if _is_same_or_ancestor_scope(
            local_owner,
            _event_owner_path(item.qualified_name),
        )
    ]
    if not candidates:
        return None
    return max(
        candidates,
        key=lambda item: len(_event_owner_path(item.qualified_name)),
    )


def _event_owner_path(qualified_name: str) -> str:
    if '.' not in qualified_name:
        return ''
    return qualified_name.rsplit('.', 1)[0]


def _is_same_or_ancestor_scope(local_owner: str, broader_owner: str) -> bool:
    if broader_owner == '':
        return True
    return local_owner == broader_owner or local_owner.startswith(f'{broader_owner}.')

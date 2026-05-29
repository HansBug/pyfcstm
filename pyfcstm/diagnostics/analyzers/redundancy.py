"""Redundancy and overlap design-health diagnostics."""

from typing import TYPE_CHECKING, Dict, Iterable, List, Tuple

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import EventInfo, TransitionInfo


def collect_redundancy_warnings(
    transitions: Iterable['TransitionInfo'],
    events: Iterable['EventInfo'],
) -> List[ModelDiagnostic]:
    transitions = list(transitions)
    diagnostics: List[ModelDiagnostic] = []
    diagnostics.extend(_redundant_transition_warnings(transitions))
    diagnostics.extend(_self_transition_nop_warnings(transitions))
    diagnostics.extend(_effect_self_assign_warnings(transitions))
    diagnostics.extend(_forced_overrides_normal_warnings(transitions))
    diagnostics.extend(_shadowed_event_warnings(events))
    return diagnostics


def _transition_key(t) -> Tuple[str, str, object, object]:
    return t.from_path, t.to_path, t.event, t.guard


def _redundant_transition_warnings(transitions) -> List[ModelDiagnostic]:
    groups: Dict[Tuple[str, str, object, object], List[object]] = {}
    for t in transitions:
        if t.from_path == '[*]':
            continue
        groups.setdefault(_transition_key(t), []).append(t)
    diagnostics: List[ModelDiagnostic] = []
    for key, items in groups.items():
        if len(items) < 2:
            continue
        from_path, to_path, _, _ = key
        diagnostics.append(ModelDiagnostic(
            code='W_REDUNDANT_TRANSITION',
            severity='warning',
            message=(
                f'Transition {from_path!r} -> {to_path!r} is duplicated '
                'with the same event and guard.'
            ),
            refs={
                'from_path': from_path,
                'to_path': to_path,
                'duplicate_spans': [
                    f'{item.from_path}->{item.to_path}#{index}'
                    for index, item in enumerate(items, 1)
                ],
            },
        ))
    return diagnostics


def _self_transition_nop_warnings(transitions) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for t in transitions:
        if t.from_path != t.to_path:
            continue
        if t.event is not None or t.guard is not None or t.effect is not None:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_SELF_TRANSITION_NOP',
            severity='warning',
            message=f'Self transition on {t.from_path!r} has no trigger, guard, or effect.',
            refs={'state_path': t.from_path},
        ))
    return diagnostics


def _effect_self_assign_warnings(transitions) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for t in transitions:
        if t.effect is None:
            continue
        parts = [part.strip() for part in t.effect.split(';') if part.strip()]
        for part in parts:
            if '=' not in part:
                continue
            left, right = [item.strip() for item in part.split('=', 1)]
            if left and left == right:
                diagnostics.append(ModelDiagnostic(
                    code='W_EFFECT_SELF_ASSIGN',
                    severity='warning',
                    message=f'Transition effect assigns {left!r} to itself.',
                    refs={
                        'state_path': t.from_path,
                        'transition_span': None,
                        'var_name': left,
                    },
                ))
    return diagnostics


def _forced_overrides_normal_warnings(transitions) -> List[ModelDiagnostic]:
    normal = {
        _transition_key(t)
        for t in transitions
        if not t.is_forced
    }
    diagnostics: List[ModelDiagnostic] = []
    for t in transitions:
        if not t.is_forced or _transition_key(t) not in normal:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_FORCED_OVERRIDES_NORMAL',
            severity='warning',
            message=(
                f'Forced transition {t.from_path!r} -> {t.to_path!r} '
                'duplicates a normal transition.'
            ),
            refs={
                'from_path': t.from_path,
                'to_path': t.to_path,
                'forced_span': None,
                'normal_span': None,
            },
        ))
    return diagnostics


def _shadowed_event_warnings(events) -> List[ModelDiagnostic]:
    by_leaf_name: Dict[str, List[object]] = {}
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


def _find_shadowing_event(local_event, chain_like):
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

"""Informational transition diagnostics."""

from typing import TYPE_CHECKING, Iterable, List

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import StateInfo, TransitionInfo


def collect_transition_infos(
    states: Iterable['StateInfo'],
    transitions: Iterable['TransitionInfo'],
) -> List[ModelDiagnostic]:
    """Collect non-blocking transition observations."""
    states_by_path = {state.path: state for state in states}
    diagnostics: List[ModelDiagnostic] = []
    diagnostics.extend(_composite_self_transition_infos(
        states_by_path,
        transitions,
    ))
    diagnostics.extend(_eventless_guardless_transition_infos(transitions))
    return diagnostics


def _composite_self_transition_infos(states_by_path, transitions) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for transition in transitions:
        if transition.from_path != transition.to_path:
            continue
        state = states_by_path.get(transition.from_path)
        if state is None or not state.is_composite:
            continue
        diagnostics.append(ModelDiagnostic(
            code='I_TRANSITION_TO_SELF_VIA_PARENT',
            severity='info',
            message=(
                f'Composite state {transition.from_path!r} transitions '
                'to itself and may intentionally re-enter children.'
            ),
            refs={
                'state_path': transition.from_path,
                'crosses_composite': True,
            },
        ))
    return diagnostics


def _eventless_guardless_transition_infos(transitions) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for transition in transitions:
        if transition.from_path == '[*]':
            continue
        if transition.event is not None or transition.guard is not None:
            continue
        diagnostics.append(ModelDiagnostic(
            code='I_TRANSITION_NEVER_EVENT_TRIGGERED',
            severity='info',
            message=(
                f'Transition {transition.from_path!r} -> '
                f'{transition.to_path!r} has no event or guard.'
            ),
            refs={
                'from_path': transition.from_path,
                'to_path': transition.to_path,
                'transition_span': None,
            },
        ))
    return diagnostics

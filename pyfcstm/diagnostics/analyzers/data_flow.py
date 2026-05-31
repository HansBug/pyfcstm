"""Variable data-flow design-health diagnostics."""

from typing import TYPE_CHECKING, Any, Iterable, List, Optional

from ...dsl import EXIT_STATE, INIT_STATE
from ...utils.validate import ModelDiagnostic
from .use_def import collect_expr_variables

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import VariableInfo
    from ...model.model import StateMachine

_INIT_MARK = '[*]'
_EXIT_MARK = '[*]'


def collect_data_flow_warnings(
        variables: Iterable['VariableInfo'],
        machine: Optional['StateMachine'] = None,
) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    variables = list(variables)
    for variable in variables:
        read_states = set(variable.read_in_states)
        read_states.update(src for src, _ in variable.read_in_guards)
        write_states = set(variable.written_in_states)
        write_states.update(src for src, _ in variable.written_in_effects)
        if not variable.affects_guard_directly and not variable.affects_guard_indirectly:
            if variable.abstract_actions_in_scope:
                diagnostics.append(ModelDiagnostic(
                    code='I_UNREFERENCED_VAR_MAYBE_ABSTRACT',
                    severity='info',
                    message=(
                        f'Variable {variable.name!r} does not affect any '
                        'transition guard, but abstract actions may use it.'
                    ),
                    refs={
                        'var_name': variable.name,
                        'abstract_actions_in_scope': list(variable.abstract_actions_in_scope),
                    },
                ))
            else:
                diagnostics.append(ModelDiagnostic(
                    code='W_UNREFERENCED_VAR',
                    severity='warning',
                    message=(
                        f'Variable {variable.name!r} does not affect any '
                        'transition guard.'
                    ),
                    refs={
                        'var_name': variable.name,
                        'init_value': variable.init_value,
                    },
                ))
            continue
        if read_states and not write_states:
            diagnostics.append(ModelDiagnostic(
                code='W_UNWRITTEN_READ_VAR',
                severity='warning',
                message=(
                    f'Variable {variable.name!r} is read but never written '
                    'by any action or transition effect.'
                ),
                refs={
                    'var_name': variable.name,
                    'read_states': sorted(read_states),
                    'init_value': variable.init_value,
                },
            ))
        if write_states and not read_states:
            diagnostics.append(ModelDiagnostic(
                code='W_WRITE_ONLY_VAR',
                severity='warning',
                message=f'Variable {variable.name!r} is written but never read.',
                refs={
                    'var_name': variable.name,
                    'written_states': sorted(write_states),
                },
            ))
    diagnostics.extend(_guard_vars_never_change_diagnostics(variables, machine))
    return diagnostics


def _guard_vars_never_change_diagnostics(
        variables: List['VariableInfo'],
        machine: Optional['StateMachine'],
) -> List[ModelDiagnostic]:
    if machine is None:
        return []
    written_vars = {
        variable.name
        for variable in variables
        if variable.written_in_states or variable.written_in_effects
    }
    declared_vars = {variable.name for variable in variables}
    diagnostics: List[ModelDiagnostic] = []
    for state in machine.walk_states():
        for transition in state.transitions:
            if transition.guard is None:
                continue
            guard_vars = sorted(
                v for v in collect_expr_variables(transition.guard)
                if v in declared_vars
            )
            if not guard_vars:
                continue
            if any(v in written_vars for v in guard_vars):
                continue
            from_path = _transition_endpoint(
                state,
                transition.from_state,
                is_source=True,
            )
            to_path = _transition_endpoint(
                state,
                transition.to_state,
                is_source=False,
            )
            diagnostics.append(ModelDiagnostic(
                code='W_GUARD_VARS_NEVER_CHANGE',
                severity='warning',
                message=(
                    'Transition guard reads only variables that are never '
                    'changed by actions or effects.'
                ),
                refs={
                    'from_path': from_path,
                    'to_path': to_path,
                    'guard_vars': guard_vars,
                },
            ))
    return diagnostics


def _state_path(state: Any) -> str:
    path = getattr(state, 'path', None)
    if not path:  # pragma: no cover
        return ''
    return '.'.join(p for p in path if p is not None)


def _resolve_sibling_path(parent_state: Any, name: str) -> str:
    parent_path = _state_path(parent_state)
    return f'{parent_path}.{name}' if parent_path else name


def _transition_endpoint(parent_state: Any, marker_or_name: Any, is_source: bool) -> str:
    if marker_or_name is INIT_STATE:
        return _INIT_MARK
    if marker_or_name is EXIT_STATE:
        return _EXIT_MARK
    if isinstance(marker_or_name, str):
        return _resolve_sibling_path(parent_state, marker_or_name)
    return str(marker_or_name)  # pragma: no cover

"""Variable data-flow design-health diagnostics."""

from typing import TYPE_CHECKING, Dict, Iterable, List, Set, Tuple

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import VariableInfo


def collect_data_flow_warnings(
    variables: Iterable['VariableInfo'],
    reachability_graph,
) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    variables = list(variables)
    diagnostics.extend(_guard_vars_never_change_diagnostics(variables))
    for variable in variables:
        diagnostics.extend(_variable_usage_diagnostics(variable, reachability_graph))
    return diagnostics


def _variable_usage_diagnostics(
    variable: 'VariableInfo',
    reachability_graph,
) -> List[ModelDiagnostic]:
    read_states = _read_states(variable)
    write_states = _write_states(variable)
    if not read_states and not write_states:
        return [_unreferenced_var_diagnostic(variable)]
    if read_states and not write_states:
        return [_unwritten_read_var_diagnostic(variable, read_states)]
    if write_states and not read_states:
        return [_write_only_var_diagnostic(variable, write_states)]

    final_writes = _final_write_locations(variable, read_states, reachability_graph)
    if final_writes:
        return [
            ModelDiagnostic(
                code='W_VARIABLE_NEVER_READ_AFTER_FINAL_WRITE',
                severity='warning',
                message=(
                    f'Variable {variable.name!r} has final write sites '
                    'with no reachable later read.'
                ),
                refs={
                    'var_name': variable.name,
                    'write_locations': final_writes,
                },
            )
        ]
    return []


def _read_states(variable: 'VariableInfo') -> Set[str]:
    read_states = set(variable.read_in_states)
    read_states.update(src for src, _ in variable.read_in_guards)
    return read_states


def _write_states(variable: 'VariableInfo') -> Set[str]:
    write_states = set(variable.written_in_states)
    write_states.update(src for src, _ in variable.written_in_effects)
    return write_states


def _unreferenced_var_diagnostic(variable: 'VariableInfo') -> ModelDiagnostic:
    if variable.abstract_actions_in_scope:
        return ModelDiagnostic(
            code='I_UNREFERENCED_VAR_MAYBE_ABSTRACT',
            severity='info',
            message=(
                f'Variable {variable.name!r} is unused in DSL statements, '
                'but abstract actions may use it externally.'
            ),
            refs={
                'var_name': variable.name,
                'abstract_actions_in_scope': list(variable.abstract_actions_in_scope),
            },
        )
    return ModelDiagnostic(
        code='W_UNREFERENCED_VAR',
        severity='warning',
        message=f'Variable {variable.name!r} is never read or written.',
        refs={
            'var_name': variable.name,
            'init_value': variable.init_value,
        },
    )


def _unwritten_read_var_diagnostic(
    variable: 'VariableInfo',
    read_states: Set[str],
) -> ModelDiagnostic:
    return ModelDiagnostic(
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
    )


def _write_only_var_diagnostic(
    variable: 'VariableInfo',
    write_states: Set[str],
) -> ModelDiagnostic:
    return ModelDiagnostic(
        code='W_WRITE_ONLY_VAR',
        severity='warning',
        message=f'Variable {variable.name!r} is written but never read.',
        refs={
            'var_name': variable.name,
            'written_states': sorted(write_states),
        },
    )


def _guard_vars_never_change_diagnostics(
    variables: List['VariableInfo'],
) -> List[ModelDiagnostic]:
    writes_by_var = {
        variable.name: _write_states(variable)
        for variable in variables
    }
    guard_vars: Dict[Tuple[str, str], Set[str]] = {}
    for variable in variables:
        for edge in variable.read_in_guards:
            guard_vars.setdefault(edge, set()).add(variable.name)

    diagnostics: List[ModelDiagnostic] = []
    for edge, names in sorted(guard_vars.items()):
        never_changed = sorted(
            name for name in names
            if not writes_by_var.get(name)
        )
        if len(never_changed) != len(names):
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_GUARD_VARS_NEVER_CHANGE',
            severity='warning',
            message=(
                f'Transition {edge[0]!r} -> {edge[1]!r} guard only reads '
                'variables that never change.'
            ),
            refs={
                'transition_span': None,
                'guard_vars': never_changed,
            },
        ))
    return diagnostics


def _final_write_locations(
    variable: 'VariableInfo',
    read_states: Set[str],
    reachability_graph,
) -> List[str]:
    out: List[str] = []
    for state_path in variable.written_in_states:
        if _has_reachable_read(state_path, read_states, reachability_graph):
            continue
        out.append(state_path)
    for from_path, to_path in variable.written_in_effects:
        if to_path != '[*]' and _has_reachable_read(to_path, read_states, reachability_graph):
            continue
        out.append(f'{from_path}->{to_path}')
    return sorted(set(out))


def _has_reachable_read(
    start_path: str,
    read_states: Set[str],
    reachability_graph,
) -> bool:
    if start_path in read_states:
        return True
    for reachable in reachability_graph[start_path]:
        if reachable in read_states:
            return True
    return False

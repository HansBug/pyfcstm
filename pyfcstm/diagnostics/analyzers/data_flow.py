"""Variable data-flow design-health diagnostics."""

from typing import TYPE_CHECKING, Iterable, List

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import VariableInfo


def collect_data_flow_warnings(variables: Iterable['VariableInfo']) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for variable in variables:
        read_states = set(variable.read_in_states)
        read_states.update(src for src, _ in variable.read_in_guards)
        write_states = set(variable.written_in_states)
        write_states.update(src for src, _ in variable.written_in_effects)
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
    return diagnostics

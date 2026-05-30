"""Type-shape design-health diagnostics."""

from typing import TYPE_CHECKING, Iterable, List, Optional

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import VariableInfo


def collect_type_warnings(
    variables: Iterable['VariableInfo'],
) -> List[ModelDiagnostic]:
    """Collect diagnostics for simple type-shape hazards."""
    variables = list(variables)
    diagnostics: List[ModelDiagnostic] = []
    diagnostics.extend(_literal_init_narrowing_warnings(variables))
    diagnostics.extend(_literal_assignment_narrowing_warnings(variables))
    return diagnostics


def _literal_init_narrowing_warnings(variables) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for variable in variables:
        if variable.type != 'int' or not _is_float_literal_text(variable.init_value):
            continue
        diagnostics.append(_narrowing_diagnostic(
            variable.name,
            variable.init_value,
        ))
    return diagnostics


def _literal_assignment_narrowing_warnings(variables) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for variable in variables:
        if variable.type != 'int':
            continue
        for source_expr in variable.float_literal_assignments:
            diagnostics.append(_narrowing_diagnostic(variable.name, source_expr))
    return diagnostics


def _narrowing_diagnostic(var_name: str, source_expr: str) -> ModelDiagnostic:
    return ModelDiagnostic(
        code='W_LITERAL_TYPE_NARROWING',
        severity='warning',
        message=(
            f'Integer variable {var_name!r} receives float literal '
            f'expression {source_expr!r}.'
        ),
        refs={
            'var_name': var_name,
            'target_type': 'int',
            'source_expr': source_expr,
        },
    )


def _is_float_literal_text(text: Optional[str]) -> bool:
    if text is None:
        return False
    value = text.strip()
    if not value:
        return False
    lowered = value.lower()
    if lowered in {'pi', 'e', 'tau'}:
        return True
    return any(ch in lowered for ch in ('.', 'e')) and _looks_numeric(lowered)


def _looks_numeric(text: str) -> bool:
    try:
        float(text)
    except ValueError:
        return False
    return True

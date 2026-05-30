"""Threshold-based design-health diagnostics."""

from typing import TYPE_CHECKING, Iterable, List

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import ModelMetrics, StateInfo


def collect_threshold_warnings(
    states: Iterable['StateInfo'],
    metrics: 'ModelMetrics',
    *,
    deep_hierarchy_threshold: int,
    large_composite_threshold: int,
    var_to_leaf_ratio_threshold: float,
) -> List[ModelDiagnostic]:
    """Collect warnings controlled by inspect-model threshold options."""
    states = list(states)
    diagnostics: List[ModelDiagnostic] = []
    diagnostics.extend(_high_var_to_leaf_ratio_warnings(
        metrics,
        var_to_leaf_ratio_threshold,
    ))
    diagnostics.extend(_deep_hierarchy_warnings(
        states,
        metrics,
        deep_hierarchy_threshold,
    ))
    diagnostics.extend(_large_composite_warnings(
        states,
        large_composite_threshold,
    ))
    return diagnostics


def _high_var_to_leaf_ratio_warnings(metrics, threshold) -> List[ModelDiagnostic]:
    actual = metrics.var_to_leaf_ratio
    if actual <= threshold:
        return []
    return [ModelDiagnostic(
        code='W_HIGH_VAR_TO_LEAF_RATIO',
        severity='warning',
        message=(
            f'Variable-to-leaf ratio {actual!r} exceeds threshold '
            f'{threshold!r}.'
        ),
        refs={
            'n_vars': metrics.n_variables,
            'n_leaf_states': metrics.n_states_leaf,
            'actual': actual,
            'threshold': threshold,
        },
    )]


def _deep_hierarchy_warnings(states, metrics, threshold) -> List[ModelDiagnostic]:
    actual = metrics.max_hierarchy_depth
    if actual <= threshold:
        return []
    deepest = [
        state.path for state in states
        if state.path.count('.') == actual
    ]
    deepest_path = sorted(deepest)[0] if deepest else ''
    return [ModelDiagnostic(
        code='W_DEEP_HIERARCHY',
        severity='warning',
        message=(
            f'Hierarchy depth {actual!r} exceeds threshold '
            f'{threshold!r}.'
        ),
        refs={
            'max_depth': actual,
            'deepest_path': deepest_path,
            'actual': actual,
            'threshold': threshold,
        },
    )]


def _large_composite_warnings(states, threshold) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    for state in states:
        if not state.is_composite:
            continue
        actual = len(state.substates)
        if actual <= threshold:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_LARGE_COMPOSITE',
            severity='warning',
            message=(
                f'Composite state {state.path!r} has {actual!r} direct '
                f'children, exceeding threshold {threshold!r}.'
            ),
            refs={
                'composite_path': state.path,
                'n_children': actual,
                'actual': actual,
                'threshold': threshold,
            },
        ))
    return diagnostics

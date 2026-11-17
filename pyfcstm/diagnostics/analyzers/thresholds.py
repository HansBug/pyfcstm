"""Threshold-based design-health diagnostics."""

from typing import TYPE_CHECKING, Iterable, List

from ...utils.validate import ModelDiagnostic

if TYPE_CHECKING:  # pragma: no cover
    from ..inspect import ModelMetrics, RegionInfo, StateInfo


def collect_threshold_warnings(
    states: Iterable['StateInfo'],
    metrics: 'ModelMetrics',
    *,
    deep_hierarchy_threshold: int,
    large_composite_threshold: int,
    var_to_leaf_ratio_threshold: float,
    regions: Iterable['RegionInfo'] = (),
) -> List[ModelDiagnostic]:
    """
    Collect warnings controlled by inspect-model threshold options.

    :param states: Inspect state records.
    :type states: Iterable[pyfcstm.diagnostics.inspect.StateInfo]
    :param metrics: Aggregate metrics of the model.
    :type metrics: pyfcstm.diagnostics.inspect.ModelMetrics
    :param deep_hierarchy_threshold: Depth above which ``W_DEEP_HIERARCHY``
        fires.
    :type deep_hierarchy_threshold: int
    :param large_composite_threshold: Direct-child count above which
        ``W_LARGE_COMPOSITE`` fires; a region counts its own child states.
    :type large_composite_threshold: int
    :param var_to_leaf_ratio_threshold: Ratio above which
        ``W_HIGH_VAR_TO_LEAF_RATIO`` fires.
    :type var_to_leaf_ratio_threshold: float
    :param regions: Inspect region records, defaults to ``()``.
    :type regions: Iterable[pyfcstm.diagnostics.inspect.RegionInfo], optional
    :return: Threshold diagnostics.
    :rtype: List[pyfcstm.utils.validate.ModelDiagnostic]

    Example::

        >>> from pyfcstm.diagnostics import inspect_model
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> machine = load_state_machine_from_text(
        ...     'state Root { region Work { state A; state B; state C; [*] -> A; } }')
        >>> report = inspect_model(machine, large_composite_threshold=2)
        >>> [item.refs['composite_path'] for item in report.diagnostics
        ...  if item.code == 'W_LARGE_COMPOSITE']
        ['Root.Work']
    """
    states = list(states)
    diagnostics: List[ModelDiagnostic] = []
    diagnostics.extend(_high_var_to_leaf_ratio_warnings(
        metrics,
        var_to_leaf_ratio_threshold,
        states,
    ))
    diagnostics.extend(_deep_hierarchy_warnings(
        states,
        metrics,
        deep_hierarchy_threshold,
    ))
    diagnostics.extend(_large_composite_warnings(
        states,
        large_composite_threshold,
        regions,
    ))
    return diagnostics


def _high_var_to_leaf_ratio_warnings(metrics, threshold, states) -> List[ModelDiagnostic]:
    actual = metrics.var_to_leaf_ratio
    if actual <= threshold:
        return []
    anchor_state = states[0] if states else None
    return [ModelDiagnostic(
        code='W_HIGH_VAR_TO_LEAF_RATIO',
        span=getattr(anchor_state, 'span', None),
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
    deepest_state = next((state for state in states if state.path == deepest_path), None)
    return [ModelDiagnostic(
        code='W_DEEP_HIERARCHY',
        span=getattr(deepest_state, 'span', None),
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


def _large_composite_warnings(states, threshold, regions=()) -> List[ModelDiagnostic]:
    diagnostics: List[ModelDiagnostic] = []
    # A region groups states like a composite does, so it counts its children.
    for state in (*states, *regions):
        if not getattr(state, 'is_composite', True):
            continue
        actual = len(state.substates)
        if actual <= threshold:
            continue
        diagnostics.append(ModelDiagnostic(
            code='W_LARGE_COMPOSITE',
            span=state.span,
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

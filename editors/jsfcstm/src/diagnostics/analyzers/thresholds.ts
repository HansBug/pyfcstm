import type {ModelDiagnosticJson, ModelMetrics, StateInfo} from '../inspect';

export interface ThresholdOptions {
    deepHierarchyThreshold: number;
    largeCompositeThreshold: number;
    varToLeafRatioThreshold: number;
}

export function collectThresholdWarnings(
    states: StateInfo[],
    metrics: ModelMetrics,
    options: ThresholdOptions,
): ModelDiagnosticJson[] {
    return [
        ...collectHighVarToLeafRatioWarnings(metrics, options.varToLeafRatioThreshold),
        ...collectDeepHierarchyWarnings(states, metrics, options.deepHierarchyThreshold),
        ...collectLargeCompositeWarnings(states, options.largeCompositeThreshold),
    ];
}

function collectHighVarToLeafRatioWarnings(
    metrics: ModelMetrics,
    threshold: number,
): ModelDiagnosticJson[] {
    const actual = metrics.var_to_leaf_ratio;
    if (actual <= threshold) return [];
    return [{
        code: 'W_HIGH_VAR_TO_LEAF_RATIO',
        severity: 'warning',
        message: `Variable-to-leaf ratio ${JSON.stringify(actual)} exceeds threshold ${JSON.stringify(threshold)}.`,
        span: null,
        refs: {
            n_vars: metrics.n_variables,
            n_leaf_states: metrics.n_states_leaf,
            actual,
            threshold,
        },
    }];
}

function collectDeepHierarchyWarnings(
    states: StateInfo[],
    metrics: ModelMetrics,
    threshold: number,
): ModelDiagnosticJson[] {
    const actual = metrics.max_hierarchy_depth;
    if (actual <= threshold) return [];
    const deepest = states
        .filter(state => state.path.split('.').length - 1 === actual)
        .map(state => state.path)
        .sort()[0] ?? '';
    return [{
        code: 'W_DEEP_HIERARCHY',
        severity: 'warning',
        message: `Hierarchy depth ${JSON.stringify(actual)} exceeds threshold ${JSON.stringify(threshold)}.`,
        span: null,
        refs: {
            max_depth: actual,
            deepest_path: deepest,
            actual,
            threshold,
        },
    }];
}

function collectLargeCompositeWarnings(
    states: StateInfo[],
    threshold: number,
): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const state of states) {
        if (!state.is_composite) continue;
        const actual = state.substates.length;
        if (actual <= threshold) continue;
        out.push({
            code: 'W_LARGE_COMPOSITE',
            severity: 'warning',
            message: `Composite state ${JSON.stringify(state.path)} has ${JSON.stringify(actual)} direct children, exceeding threshold ${JSON.stringify(threshold)}.`,
            span: null,
            refs: {
                composite_path: state.path,
                n_children: actual,
                actual,
                threshold,
            },
        });
    }
    return out;
}

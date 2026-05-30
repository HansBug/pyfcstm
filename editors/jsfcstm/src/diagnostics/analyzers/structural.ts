import type {
    ActionInfo,
    ForcedTransitionInfo,
    ModelDiagnosticJson,
    StateInfo,
    TransitionInfo,
} from '../inspect';

export function collectStructuralWarnings(
    states: StateInfo[],
    transitions: TransitionInfo[],
    actions: ActionInfo[],
    forcedTransitions: ForcedTransitionInfo[],
    reachabilityGraph: Record<string, string[]>,
    rootStatePath?: string,
): ModelDiagnosticJson[] {
    return [
        ...collectDeadlockLeafWarnings(states, transitions),
        ...collectInitialUnconditionalMissingWarnings(states),
        ...collectForcedNeverExpandsWarnings(forcedTransitions),
        ...collectDeadNamedActionWarnings(states, actions, reachabilityGraph, rootStatePath),
    ];
}

function collectDeadlockLeafWarnings(
    states: StateInfo[],
    transitions: TransitionInfo[],
): ModelDiagnosticJson[] {
    const outgoing: Record<string, number> = {};
    for (const transition of transitions) {
        if (transition.from_path === '[*]') continue;
        outgoing[transition.from_path] = (outgoing[transition.from_path] ?? 0) + 1;
    }
    const out: ModelDiagnosticJson[] = [];
    for (const state of states) {
        if (!state.is_leaf || state.is_pseudo) continue;
        if ((outgoing[state.path] ?? 0) > 0) continue;
        out.push({
            code: 'W_DEADLOCK_LEAF',
            severity: 'warning',
            message: `Leaf state ${JSON.stringify(state.path)} has no outgoing transition.`,
            span: null,
            refs: {
                state_path: state.path,
                reason: 'no_outgoing_transition',
            },
        });
    }
    return out;
}

function collectInitialUnconditionalMissingWarnings(states: StateInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const state of states) {
        if (!state.is_composite) continue;
        const hasUnconditional = state.initial_targets.some(item => item.is_unconditional);
        if (hasUnconditional) continue;
        out.push({
            code: 'W_INITIAL_UNCONDITIONAL_MISSING',
            severity: 'warning',
            message: `Composite state ${JSON.stringify(state.path)} has no unconditional [*] entry transition.`,
            span: null,
            refs: {
                composite_path: state.path,
                existing_conditional_count: state.initial_targets.length,
            },
        });
    }
    return out;
}

function collectForcedNeverExpandsWarnings(
    forcedTransitions: ForcedTransitionInfo[],
): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const item of forcedTransitions) {
        if (item.expansion_count > 0) continue;
        out.push({
            code: 'W_FORCED_NEVER_EXPANDS',
            severity: 'warning',
            message: `Forced transition ${JSON.stringify(item.original_raw)} declares no concrete expansion in its state scope.`,
            span: null,
            refs: {
                state_path: item.state_path,
                original_raw: item.original_raw,
            },
        });
    }
    return out;
}

function collectDeadNamedActionWarnings(
    states: StateInfo[],
    actions: ActionInfo[],
    reachabilityGraph: Record<string, string[]>,
    rootStatePath?: string,
): ModelDiagnosticJson[] {
    if (states.length === 0 && rootStatePath === undefined) return [];
    const rootPath = rootStatePath ?? states[0].path;
    const reachable = new Set<string>(reachabilityGraph[rootPath] ?? []);
    reachable.add(rootPath);
    const referenced = new Set(
        actions
            .filter(action => reachable.has(action.state_path))
            .map(action => action.ref_target)
            .filter((item): item is string => item !== null),
    );
    const out: ModelDiagnosticJson[] = [];
    for (const action of actions) {
        if (!action.name || action.is_ref) continue;
        if (referenced.has(action.signature)) continue;
        if (reachable.has(action.state_path)) continue;
        out.push({
            code: 'W_DEAD_NAMED_ACTION',
            severity: 'warning',
            message: `Named action ${JSON.stringify(action.signature)} is unreachable and unreferenced.`,
            span: null,
            refs: {
                function_name: action.name,
                defined_in: action.state_path,
            },
        });
    }
    return out;
}

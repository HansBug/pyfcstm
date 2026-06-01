import type {ModelDiagnosticJson, StateInfo, TransitionInfo} from '../inspect';

export function collectTransitionInfos(
    states: StateInfo[],
    transitions: TransitionInfo[],
): ModelDiagnosticJson[] {
    const statesByPath = new Map(states.map(state => [state.path, state]));
    return [
        ...collectCompositeSelfTransitionInfos(statesByPath, transitions),
        ...collectEventlessGuardlessTransitionInfos(transitions),
    ];
}

function collectCompositeSelfTransitionInfos(
    statesByPath: Map<string, StateInfo>,
    transitions: TransitionInfo[],
): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        if (transition.from_path !== transition.to_path) continue;
        const state = statesByPath.get(transition.from_path);
        if (!state || !state.is_composite) continue;
        out.push({
            code: 'I_TRANSITION_TO_SELF_VIA_PARENT',
            severity: 'info',
            message: `Composite state ${JSON.stringify(transition.from_path)} transitions to itself and may intentionally re-enter children.`,
            span: null,
            refs: {
                state_path: transition.from_path,
                crosses_composite: true,
            },
        });
    }
    return out;
}

function collectEventlessGuardlessTransitionInfos(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (let transitionIndex = 0; transitionIndex < transitions.length; transitionIndex += 1) {
        const transition = transitions[transitionIndex];
        if (transition.from_path === '[*]') continue;
        if (transition.event !== null || transition.guard !== null) continue;
        out.push({
            code: 'I_TRANSITION_NEVER_EVENT_TRIGGERED',
            severity: 'info',
            message: `Transition ${JSON.stringify(transition.from_path)} -> ${JSON.stringify(transition.to_path)} has no event or guard.`,
            span: null,
            refs: {
                from_path: transition.from_path,
                to_path: transition.to_path,
                transition_span: null,
                transition_index: transitionIndex,
            },
        });
    }
    return out;
}

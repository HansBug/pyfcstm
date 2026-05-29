import type {EventInfo, ModelDiagnosticJson, TransitionInfo} from '../inspect';

export function collectRedundancyWarnings(
    transitions: TransitionInfo[],
    events: EventInfo[],
): ModelDiagnosticJson[] {
    return [
        ...collectRedundantTransitionWarnings(transitions),
        ...collectSelfTransitionNopWarnings(transitions),
        ...collectEffectSelfAssignWarnings(transitions),
        ...collectForcedOverridesNormalWarnings(transitions),
        ...collectShadowedEventWarnings(events),
    ];
}

function transitionKey(transition: TransitionInfo): string {
    return JSON.stringify([
        transition.from_path,
        transition.to_path,
        transition.event,
        transition.guard,
    ]);
}

function collectRedundantTransitionWarnings(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const groups = new Map<string, TransitionInfo[]>();
    for (const transition of transitions) {
        if (transition.from_path === '[*]') continue;
        const key = transitionKey(transition);
        groups.set(key, [...(groups.get(key) ?? []), transition]);
    }
    const out: ModelDiagnosticJson[] = [];
    for (const items of groups.values()) {
        if (items.length < 2) continue;
        const first = items[0];
        out.push({
            code: 'W_REDUNDANT_TRANSITION',
            severity: 'warning',
            message: `Transition ${JSON.stringify(first.from_path)} -> ${JSON.stringify(first.to_path)} is duplicated with the same event and guard.`,
            span: null,
            refs: {
                from_path: first.from_path,
                to_path: first.to_path,
                duplicate_spans: items.map((item, index) => `${item.from_path}->${item.to_path}#${index + 1}`),
            },
        });
    }
    return out;
}

function collectSelfTransitionNopWarnings(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        if (transition.from_path !== transition.to_path) continue;
        if (transition.event !== null || transition.guard !== null || transition.effect !== null) continue;
        out.push({
            code: 'W_SELF_TRANSITION_NOP',
            severity: 'warning',
            message: `Self transition on ${JSON.stringify(transition.from_path)} has no trigger, guard, or effect.`,
            span: null,
            refs: {state_path: transition.from_path},
        });
    }
    return out;
}

function collectEffectSelfAssignWarnings(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        if (transition.effect === null) continue;
        const parts = transition.effect.split(';').map(item => item.trim()).filter(Boolean);
        for (const part of parts) {
            if (!part.includes('=')) continue;
            const [leftRaw, rightRaw] = part.split('=', 2);
            const left = leftRaw.trim();
            const right = rightRaw.trim();
            if (!left || left !== right) continue;
            out.push({
                code: 'W_EFFECT_SELF_ASSIGN',
                severity: 'warning',
                message: `Transition effect assigns ${JSON.stringify(left)} to itself.`,
                span: null,
                refs: {
                    state_path: transition.from_path,
                    transition_span: null,
                    var_name: left,
                },
            });
        }
    }
    return out;
}

function collectForcedOverridesNormalWarnings(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const normal = new Set(transitions.filter(t => !t.is_forced).map(transitionKey));
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        if (!transition.is_forced || !normal.has(transitionKey(transition))) continue;
        out.push({
            code: 'W_FORCED_OVERRIDES_NORMAL',
            severity: 'warning',
            message: `Forced transition ${JSON.stringify(transition.from_path)} -> ${JSON.stringify(transition.to_path)} duplicates a normal transition.`,
            span: null,
            refs: {
                from_path: transition.from_path,
                to_path: transition.to_path,
                forced_span: null,
                normal_span: null,
            },
        });
    }
    return out;
}

function collectShadowedEventWarnings(events: EventInfo[]): ModelDiagnosticJson[] {
    const byName = new Map<string, EventInfo[]>();
    for (const event of events) {
        const leaf = event.qualified_name.split('.').at(-1) ?? event.qualified_name;
        byName.set(leaf, [...(byName.get(leaf) ?? []), event]);
    }
    const out: ModelDiagnosticJson[] = [];
    for (const [eventName, items] of byName.entries()) {
        const chainLike = items.filter(item => item.scope === 'chain' || item.scope === 'absolute');
        const localLike = items.filter(item => item.scope === 'local');
        if (chainLike.length === 0 || localLike.length === 0) continue;
        for (const localEvent of localLike) {
            out.push({
                code: 'W_SHADOWED_EVENT',
                severity: 'warning',
                message: `Local event ${JSON.stringify(localEvent.qualified_name)} shadows a chain event named ${JSON.stringify(eventName)}.`,
                span: null,
                refs: {
                    event_name: eventName,
                    local_path: localEvent.qualified_name,
                    chain_path: chainLike[0].qualified_name,
                },
            });
        }
    }
    return out;
}

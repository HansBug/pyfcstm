import type {EventInfo, ModelDiagnosticJson, StateInfo, TransitionInfo} from '../inspect';

export function collectRedundancyWarnings(
    transitions: TransitionInfo[],
    events: EventInfo[],
    states: StateInfo[] = [],
): ModelDiagnosticJson[] {
    return [
        ...collectRedundantTransitionWarnings(transitions),
        ...collectSelfTransitionNopWarnings(transitions, states),
        ...collectEffectSelfAssignWarnings(transitions),
        ...collectForcedOverridesNormalWarnings(transitions),
        ...collectShadowedEventWarnings(events),
    ];
}

function transitionTriggerKey(transition: TransitionInfo): string {
    return JSON.stringify([
        transition.from_path,
        transition.to_path,
        transition.event,
        transition.guard,
    ]);
}

function transitionBehaviorKey(transition: TransitionInfo): string {
    return JSON.stringify([
        transition.from_path,
        transition.to_path,
        transition.event,
        transition.guard,
        transition.effect,
    ]);
}

function collectRedundantTransitionWarnings(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const groups = new Map<string, TransitionInfo[]>();
    for (const transition of transitions) {
        if (transition.from_path === '[*]') continue;
        const key = transitionBehaviorKey(transition);
        groups.set(key, [...(groups.get(key) ?? []), transition]);
    }
    const out: ModelDiagnosticJson[] = [];
    for (const items of groups.values()) {
        if (items.length < 2) continue;
        const first = items[0];
        out.push({
            code: 'W_REDUNDANT_TRANSITION',
            severity: 'warning',
            message: `Transition ${JSON.stringify(first.from_path)} -> ${JSON.stringify(first.to_path)} is duplicated with the same event, guard, and effect.`,
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

function collectSelfTransitionNopWarnings(transitions: TransitionInfo[], states: StateInfo[]): ModelDiagnosticJson[] {
    const statesByPath = new Map(states.map(state => [state.path, state]));
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        if (transition.from_path !== transition.to_path) continue;
        if (transition.event !== null || transition.guard !== null || transition.effect !== null) continue;
        if (!isLifecycleFreeLeaf(transition.from_path, statesByPath)) continue;
        out.push({
            code: 'W_SELF_TRANSITION_NOP',
            severity: 'warning',
            message: `Self transition on ${JSON.stringify(transition.from_path)} has no trigger, guard, effect, or re-entry lifecycle behavior.`,
            span: null,
            refs: {state_path: transition.from_path},
        });
    }
    return out;
}

function isLifecycleFreeLeaf(statePath: string, statesByPath: Map<string, StateInfo>): boolean {
    const state = statesByPath.get(statePath);
    if (!state || !state.is_leaf || state.is_pseudo) return false;
    if (
        state.entry_actions.length > 0 ||
        state.during_actions.length > 0 ||
        state.exit_actions.length > 0 ||
        state.aspect_before.length > 0 ||
        state.aspect_after.length > 0
    ) {
        return false;
    }
    const parts = statePath.split('.');
    for (let index = 1; index < parts.length; index += 1) {
        const ancestor = statesByPath.get(parts.slice(0, index).join('.'));
        if (ancestor && (ancestor.aspect_before.length > 0 || ancestor.aspect_after.length > 0)) {
            return false;
        }
    }
    return true;
}

function collectEffectSelfAssignWarnings(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const counts = new Map<string, number>();
    for (const transition of transitions) {
        for (const varName of transition.effect_self_assigns) {
            const key = JSON.stringify([transition.from_path, varName]);
            counts.set(key, (counts.get(key) ?? 0) + 1);
        }
    }
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        for (const varName of transition.effect_self_assigns) {
            const refs: Record<string, unknown> = {
                state_path: transition.from_path,
                transition_span: null,
                var_name: varName,
            };
            if (
                transition.from_path !== '[*]' &&
                counts.get(JSON.stringify([transition.from_path, varName])) === 1
            ) {
                refs.effect_self_assign_anchor = varName;
            }
            out.push({
                code: 'W_EFFECT_SELF_ASSIGN',
                severity: 'warning',
                message: `Transition effect assigns ${JSON.stringify(varName)} to itself.`,
                span: null,
                refs,
            });
        }
    }
    return out;
}

function collectForcedOverridesNormalWarnings(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const normal = new Set(transitions.filter(t => !t.is_forced).map(transitionTriggerKey));
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        if (!transition.is_forced || !normal.has(transitionTriggerKey(transition))) continue;
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
            const shadowingEvent = findShadowingEvent(localEvent, chainLike);
            if (!shadowingEvent) continue;
            out.push({
                code: 'W_SHADOWED_EVENT',
                severity: 'warning',
                message: `Local event ${JSON.stringify(localEvent.qualified_name)} shadows a chain event named ${JSON.stringify(eventName)}.`,
                span: null,
                refs: {
                    event_name: eventName,
                    local_path: localEvent.qualified_name,
                    chain_path: shadowingEvent.qualified_name,
                },
            });
        }
    }
    return out;
}

function findShadowingEvent(localEvent: EventInfo, chainLike: EventInfo[]): EventInfo | undefined {
    const localOwner = eventOwnerPath(localEvent.qualified_name);
    const candidates = chainLike.filter(item =>
        isSameOrAncestorScope(localOwner, eventOwnerPath(item.qualified_name))
    );
    candidates.sort((a, b) => eventOwnerPath(b.qualified_name).length - eventOwnerPath(a.qualified_name).length);
    return candidates[0];
}

function eventOwnerPath(qualifiedName: string): string {
    const index = qualifiedName.lastIndexOf('.');
    return index < 0 ? '' : qualifiedName.slice(0, index);
}

function isSameOrAncestorScope(localOwner: string, broaderOwner: string): boolean {
    if (broaderOwner === '') return true;
    return localOwner === broaderOwner || localOwner.startsWith(`${broaderOwner}.`);
}

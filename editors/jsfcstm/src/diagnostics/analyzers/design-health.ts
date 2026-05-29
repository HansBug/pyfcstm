import type {EventInfo, ModelDiagnosticJson, StateInfo, TransitionInfo} from '../inspect';

export function collectDesignHealthWarnings(
    states: StateInfo[],
    transitions: TransitionInfo[],
    events: EventInfo[],
    reachabilityGraph: Record<string, string[]>,
): ModelDiagnosticJson[] {
    return [
        ...collectUnreachableStateDiagnostics(states, reachabilityGraph),
        ...collectGuardConstFalseDiagnostics(transitions),
        ...collectUnusedEventDiagnostics(events),
    ];
}

function collectUnreachableStateDiagnostics(
    states: StateInfo[],
    reachabilityGraph: Record<string, string[]>,
): ModelDiagnosticJson[] {
    if (states.length === 0) return [];
    const rootPath = states[0].path;
    const reachable = new Set<string>(reachabilityGraph[rootPath] ?? []);
    reachable.add(rootPath);
    const out: ModelDiagnosticJson[] = [];
    for (const state of states) {
        if (state.is_pseudo || reachable.has(state.path)) continue;
        out.push({
            code: 'W_UNREACHABLE_STATE',
            severity: 'warning',
            message: `State ${JSON.stringify(state.path)} is unreachable from the root entry path.`,
            span: null,
            refs: {state_path: state.path},
        });
    }
    return out;
}

function collectGuardConstFalseDiagnostics(transitions: TransitionInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const transition of transitions) {
        if (!isMinimalConstFalseGuard(transition.guard)) continue;
        out.push({
            code: 'W_GUARD_CONST_FALSE',
            severity: 'warning',
            message: `Transition ${JSON.stringify(transition.from_path)} -> ${JSON.stringify(transition.to_path)} has a guard that is statically false.`,
            span: null,
            refs: {transition_span: null, folded_value: false},
        });
    }
    return out;
}

function isMinimalConstFalseGuard(guard: string | null): boolean {
    if (guard === null) return false;
    const normalized = guard.trim().toLowerCase();
    if (normalized === 'false' || normalized === '0') return true;
    const match = /^\s*([+-]?\d+)\s*==\s*([+-]?\d+)\s*$/.exec(guard);
    return match !== null && normalizeDecimalInteger(match[1]) !== normalizeDecimalInteger(match[2]);
}

function normalizeDecimalInteger(value: string): string {
    let sign = '';
    let digits = value;
    if (digits.startsWith('+') || digits.startsWith('-')) {
        sign = digits[0] === '-' ? '-' : '';
        digits = digits.slice(1);
    }
    digits = digits.replace(/^0+/, '');
    if (digits === '') return '0';
    return sign + digits;
}

function collectUnusedEventDiagnostics(events: EventInfo[]): ModelDiagnosticJson[] {
    const out: ModelDiagnosticJson[] = [];
    for (const event of events) {
        if (!event.is_declared || event.is_used) continue;
        out.push({
            code: 'W_UNUSED_EVENT',
            severity: 'warning',
            message: `Event ${JSON.stringify(event.qualified_name)} is declared but never used.`,
            span: null,
            refs: {
                event_qualified_name: event.qualified_name,
                scope: event.scope,
            },
        });
    }
    return out;
}

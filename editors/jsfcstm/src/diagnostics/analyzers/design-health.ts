import type {
    ActionInfo,
    EventInfo,
    ForcedTransitionInfo,
    ModelDiagnosticJson,
    ModelMetrics,
    StateInfo,
    TransitionInfo,
    VariableInfo,
} from '../inspect';
import type {StateMachine} from '../../model/runtime';
import {refsWithSuggestedFix} from '../suggested-fix';
import {collectConstFoldWarnings} from './const-fold';
import {collectDataFlowWarnings} from './data-flow';
import {collectNamingWarnings} from './naming';
import {collectRedundancyWarnings} from './redundancy';
import {collectStructuralWarnings} from './structural';
import {collectThresholdWarnings, type ThresholdOptions} from './thresholds';
import {collectTransitionInfos} from './transition-info';
import {collectTypeWarnings} from './type-shape';

export function collectDesignHealthWarnings(
    states: StateInfo[],
    transitions: TransitionInfo[],
    variables: VariableInfo[],
    events: EventInfo[],
    actions: ActionInfo[],
    forcedTransitions: ForcedTransitionInfo[],
    metrics: ModelMetrics,
    reachabilityGraph: Record<string, string[]>,
    rootStatePath?: string,
    thresholds?: ThresholdOptions,
    machine?: StateMachine,
): ModelDiagnosticJson[] {
    const thresholdOptions = thresholds ?? {
        deepHierarchyThreshold: 6,
        largeCompositeThreshold: 12,
        varToLeafRatioThreshold: 2.0,
    };
    const diagnostics = [
        ...collectUnreachableStateDiagnostics(states, reachabilityGraph, rootStatePath),
        ...(machine ? collectConstFoldWarnings(machine) : collectGuardConstFalseDiagnostics(transitions)),
        ...collectUnusedEventDiagnostics(events),
        ...collectStructuralWarnings(
            states,
            transitions,
            actions,
            forcedTransitions,
            reachabilityGraph,
            rootStatePath,
        ),
        ...collectThresholdWarnings(states, metrics, thresholdOptions),
        ...collectNamingWarnings(actions),
        ...collectTypeWarnings(variables),
        ...collectDataFlowWarnings(variables, machine),
        ...collectRedundancyWarnings(transitions, events, states),
        ...collectTransitionInfos(states, transitions),
    ];
    return diagnostics.map(diag => ({
        ...diag,
        refs: refsWithSuggestedFix(diag.code, diag.refs),
    }));
}

function collectUnreachableStateDiagnostics(
    states: StateInfo[],
    reachabilityGraph: Record<string, string[]>,
    rootStatePath?: string,
): ModelDiagnosticJson[] {
    if (states.length === 0) return [];
    const rootPath = rootStatePath ?? states[0].path;
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

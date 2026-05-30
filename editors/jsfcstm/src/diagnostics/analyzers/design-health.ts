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
    return [
        ...collectUnreachableStateDiagnostics(states, reachabilityGraph, rootStatePath),
        ...collectConstFoldWarnings(machine),
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
        ...collectDataFlowWarnings(variables),
        ...collectRedundancyWarnings(transitions, events, states),
        ...collectTransitionInfos(states, transitions),
    ];
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

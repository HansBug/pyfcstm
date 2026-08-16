import type {
    ActionInfo,
    EventInfo,
    ForcedTransitionInfo,
    ModelDiagnosticJson,
    ModelMetrics,
    ModelSpanJson,
    StateInfo,
    TransitionInfo,
    VariableInfo,
} from '../inspect';
import type {StateMachine} from '../../model/runtime';
import {refsWithSuggestedFix} from '../suggested-fix';
import {collectComboWarnings} from './combo';
import {collectConstFoldWarnings} from './const-fold';
import {collectDataFlowWarnings} from './data-flow';
import {collectNamingWarnings} from './naming';
import {collectNumericWarnings} from './numeric';
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
        ...collectUnreachableTransitionDiagnostics(states, transitions, reachabilityGraph, rootStatePath),
        ...(machine ? collectConstFoldWarnings(machine) : collectGuardConstFalseDiagnostics(transitions)),
        ...(machine ? collectComboWarnings(machine) : []),
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
        ...(machine ? collectNumericWarnings(machine) : []),
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

function collectUnreachableTransitionDiagnostics(
    states: StateInfo[],
    transitions: TransitionInfo[],
    reachabilityGraph: Record<string, string[]>,
    rootStatePath?: string,
): ModelDiagnosticJson[] {
    if (states.length === 0) return [];
    const rootPath = rootStatePath ?? states[0].path;
    const statePaths = new Set(states.map(state => state.path));
    const reachable = new Set<string>(reachabilityGraph[rootPath] ?? []);
    reachable.add(rootPath);
    const emittedComboOrigins = new Set<string>();
    const comboEndpoints = buildComboOriginEndpoints(transitions);
    const out: ModelDiagnosticJson[] = [];

    for (const transition of transitions) {
        const comboOriginIds = Array.from(new Set(
            transition.combo_origin_refs
                .map(ref => ref.origin_id)
                .filter((originId): originId is string => typeof originId === 'string'),
        )).sort();
        if (comboOriginIds.length > 0) {
            for (const originId of comboOriginIds) {
                if (emittedComboOrigins.has(originId)) continue;
                emittedComboOrigins.add(originId);
                const originRef = transition.combo_origin_refs.find(ref => ref.origin_id === originId);
                const endpoint = comboEndpoints.get(originId);
                if (!originRef || !endpoint?.targetPath) continue;
                const lookupPath = endpoint.selectionOwnerPath ?? endpoint.sourcePath;
                if (!lookupPath || reachable.has(lookupPath)) continue;
                out.push({
                    code: 'W_UNREACHABLE_TRANSITION',
                    severity: 'warning',
                    message: `Transition ${JSON.stringify(endpoint.sourcePath ?? '[*]')} -> ${JSON.stringify(endpoint.targetPath)} has a source outside the guard-agnostic root-reachable topology.`,
                    span: originRef?.transition_span ?? null,
                    refs: {
                        reason: 'source_unreachable',
                        verification_scope: 'topological_only',
                        from_path: endpoint.sourcePath ?? '[*]',
                        to_path: endpoint.targetPath,
                        source_state_path: endpoint.sourcePath,
                        selection_owner_path: endpoint.selectionOwnerPath,
                        transition_index: null,
                        forced_origin: null,
                        combo_origin_ids: [originId],
                    },
                });
            }
            continue;
        }

        const selection = transitionSelectionPaths(transition, statePaths);
        if (!selection.ownerPath || !statePaths.has(selection.ownerPath)) continue;
        if (reachable.has(selection.ownerPath)) continue;

        const message = transition.is_forced
            ? `Generated forced transition expansion ${JSON.stringify(transition.from_path)} -> ${JSON.stringify(transition.to_path)} has a source outside the guard-agnostic root-reachable topology.`
            : `Transition ${JSON.stringify(transition.from_path)} -> ${JSON.stringify(transition.to_path)} has a source outside the guard-agnostic root-reachable topology.`;
        out.push({
            code: 'W_UNREACHABLE_TRANSITION',
            severity: 'warning',
            message,
            span: transitionSourceSpan(transition),
            refs: {
                reason: 'source_unreachable',
                verification_scope: 'topological_only',
                from_path: transition.from_path,
                to_path: transition.to_path,
                source_state_path: selection.sourcePath,
                selection_owner_path: selection.sourcePath === null ? selection.ownerPath : null,
                transition_index: transition.transition_index,
                forced_origin: transition.forced_origin,
                combo_origin_ids: comboOriginIds,
            },
        });
    }
    return out;
}

interface ComboOriginEndpoints {
    sourcePath: string | null;
    selectionOwnerPath: string | null;
    targetPath: string | null;
}

function buildComboOriginEndpoints(
    transitions: TransitionInfo[],
): Map<string, ComboOriginEndpoints> {
    const endpoints = new Map<string, ComboOriginEndpoints>();
    for (const transition of transitions) {
        const projection = comboProjectionEndpoints(transition);
        for (const ref of transition.combo_origin_refs) {
            const current = endpoints.get(ref.origin_id) ?? {
                sourcePath: null,
                selectionOwnerPath: null,
                targetPath: null,
            };
            current.sourcePath = ref.source_path ?? projection.sourcePath ?? current.sourcePath;
            current.selectionOwnerPath = ref.selection_owner_path
                ?? projection.selectionOwnerPath
                ?? current.selectionOwnerPath;
            if (ref.target_path !== null) {
                current.targetPath = ref.target_path;
            } else if (ref.role === 'terminal') {
                current.targetPath = transition.to_path;
            }
            endpoints.set(ref.origin_id, current);
        }
    }
    return endpoints;
}

function comboProjectionEndpoints(
    transition: TransitionInfo,
): ComboOriginEndpoints {
    const projection = transition.combo_projection_key;
    if (!Array.isArray(projection) || !Array.isArray(projection[0])) {
        return {
            sourcePath: transition.from_path === '[*]' ? null : transition.from_path,
            selectionOwnerPath: null,
            targetPath: null,
        };
    }
    const ownerPath = projection[0].every(item => typeof item === 'string')
        ? (projection[0] as string[]).join('.')
        : null;
    if (projection[1] === 'entry') {
        return {sourcePath: null, selectionOwnerPath: ownerPath, targetPath: null};
    }
    const sourcePath = Array.isArray(projection[2])
        && projection[2].every(item => typeof item === 'string')
        ? (projection[2] as string[]).join('.')
        : null;
    return {sourcePath, selectionOwnerPath: null, targetPath: null};
}

function transitionSelectionPaths(
    transition: TransitionInfo,
    statePaths: Set<string>,
): {sourcePath: string | null; ownerPath: string | null} {
    if (transition.from_path !== '[*]') {
        return {sourcePath: transition.from_path, ownerPath: transition.from_path};
    }
    if (transition.to_path === '[*]' || !transition.to_path.includes('.')) {
        return {sourcePath: null, ownerPath: null};
    }
    const ownerPath = transition.to_path.slice(0, transition.to_path.lastIndexOf('.'));
    if (!statePaths.has(ownerPath)) return {sourcePath: null, ownerPath: null};
    return {sourcePath: null, ownerPath};
}

function transitionSourceSpan(transition: TransitionInfo): ModelSpanJson | null {
    const range = transition.__sourceRange;
    if (!range) return null;
    return {
        line: range.start.line + 1,
        column: range.start.character + 1,
        end_line: range.end.line + 1,
        end_column: range.end.character + 1,
    };
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
            refs: {
                transition_span: null,
                folded_value: false,
                from_path: transition.from_path,
                to_path: transition.to_path,
                guard_text: transition.guard,
                transition_index: transition.transition_index,
            },
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

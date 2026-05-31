/**
 * Structured model inspection for jsfcstm, mirrored from the pyfcstm
 * ``pyfcstm.diagnostics.inspect_model`` entry point.
 *
 * The public field shape, view-graph derivation, and ``toJson()`` output
 * are kept byte-equivalent to the pyfcstm side so that the shared
 * ``pyfcstm/diagnostics/schema.json`` contract validates either side's
 * output. Layer 2 strictness: anything pyfcstm produces, jsfcstm must
 * produce too, including design-health diagnostics derived from the
 * inspect surface.
 */

import {
    BinaryOp,
    BooleanExpr,
    ConditionalOp,
    Event,
    Expr,
    Float,
    IfBlock,
    Integer,
    OnAspect,
    OnStage,
    Operation,
    OperationStatement,
    StateMachine,
    Transition,
    UFunc,
    UnaryOp,
    Variable,
} from '../model/runtime';
import {collectDesignHealthWarnings} from './analyzers';
import type {RawFcstmModelForcedTransition} from '../model/raw';

const INIT_MARK = '[*]';
const EXIT_MARK = '[*]';
const FLOAT_EPSILON = 1e-10;

export const DEFAULT_DEEP_HIERARCHY_THRESHOLD = 6;
export const DEFAULT_LARGE_COMPOSITE_THRESHOLD = 12;
export const DEFAULT_VAR_TO_LEAF_RATIO_THRESHOLD = 2.0;

const OP_PRECEDENCE: Record<string, number> = {
    'function_call': 90,
    'unary+': 80,
    'unary-': 80,
    '!': 80,
    'not': 80,
    '**': 70,
    '*': 60,
    '/': 60,
    '%': 60,
    '+': 50,
    '-': 50,
    '<<': 40,
    '>>': 40,
    '&': 35,
    '^': 30,
    '|': 25,
    '<': 20,
    '>': 20,
    '<=': 20,
    '>=': 20,
    '==': 20,
    '!=': 20,
    '&&': 15,
    'and': 15,
    '||': 10,
    'or': 10,
    '?:': 5,
};

/**
 * Per-state structural summary.
 */
export interface StateInfo {
    path: string;
    name: string;
    parent_path: string | null;
    is_leaf: boolean;
    is_pseudo: boolean;
    is_composite: boolean;
    substates: string[];
    initial_targets: InitialTargetInfo[];
    entry_actions: string[];
    during_actions: string[];
    exit_actions: string[];
    aspect_before: string[];
    aspect_after: string[];
    has_abstract_action: boolean;
}

/**
 * One ``[*] -> X`` entry transition declared inside a composite state.
 */
export interface InitialTargetInfo {
    target: string;
    guard: string | null;
    event: string | null;
    is_unconditional: boolean;
}

/**
 * Per-transition structural summary.
 */
export interface TransitionInfo {
    from_path: string;
    to_path: string;
    event: string | null;
    event_scope: 'local' | 'chain' | 'absolute' | null;
    guard: string | null;
    effect: string | null;
    effect_self_assigns: string[];
    is_forced: boolean;
    forced_origin: string | null;
}

/**
 * Per-variable structural summary plus participation flags.
 */
export interface VariableInfo {
    name: string;
    type: string;
    init_value: string;
    read_in_states: string[];
    written_in_states: string[];
    read_in_guards: Array<[string, string]>;
    written_in_effects: Array<[string, string]>;
    read_in_action_stages: Array<[string, string]>;
    written_in_action_stages: Array<[string, string]>;
    read_in_guard_occurrences: Array<[string, string, string]>;
    read_in_effect_occurrences: Array<[string, string, string]>;
    read_after_write_action_stages: Array<[string, string]>;
    read_after_write_effect_occurrences: Array<[string, string, string]>;
    written_in_effect_occurrences: Array<[string, string, string]>;
    participates_directly: boolean;
    participates_indirectly: boolean;
    abstract_actions_in_scope: string[];
    float_literal_assignments: string[];
}

export interface InspectModelOptions {
    deepHierarchyThreshold?: number;
    largeCompositeThreshold?: number;
    varToLeafRatioThreshold?: number;
}

/**
 * Per-event structural summary.
 */
export interface EventInfo {
    qualified_name: string;
    scope: 'local' | 'chain' | 'absolute';
    used_by: Array<[string, string]>;
    is_declared: boolean;
    is_used: boolean;
}

/**
 * Per-action structural summary.
 */
export interface ActionInfo {
    signature: string;
    state_path: string;
    name: string | null;
    stage: string;
    aspect: string | null;
    is_ref: boolean;
    ref_target: string | null;
    is_attached: boolean;
}

/**
 * Per-forced-transition declaration summary.
 */
export interface ForcedTransitionInfo {
    state_path: string;
    from_path: string;
    to_path: string;
    event: string | null;
    event_scope: 'local' | 'chain' | 'absolute' | null;
    guard: string | null;
    original_raw: string;
    expansion_count: number;
}

/**
 * Aggregate model metrics.
 */
export interface ModelMetrics {
    n_states_leaf: number;
    n_states_composite: number;
    n_states_pseudo: number;
    max_hierarchy_depth: number;
    n_transitions_normal: number;
    n_transitions_forced: number;
    n_events: number;
    n_variables: number;
    var_to_leaf_ratio: number;
    aspect_coverage: Record<string, number>;
    abstract_action_inventory: string[];
}

/**
 * Top-level structured view of a state machine model.
 */
export interface ModelInspect {
    root_state_path: string;
    states: StateInfo[];
    transitions: TransitionInfo[];
    variables: VariableInfo[];
    events: EventInfo[];
    actions: ActionInfo[];
    forced_transitions: ForcedTransitionInfo[];
    metrics: ModelMetrics;
    reachability_graph: Record<string, string[]>;
    event_emission_map: Record<string, string[]>;
    var_dataflow: Record<string, { reads: string[]; writes: string[] }>;
    aspect_impact_map: Record<string, string[]>;
    action_ref_graph: Record<string, string[]>;
    diagnostics: ModelDiagnosticJson[];
}

/**
 * JSON-shaped diagnostic payload used inside :class:`ModelInspect`.
 */
export interface ModelDiagnosticJson {
    code: string;
    severity: 'error' | 'warning' | 'info';
    message: string;
    span: {
        start_line: number;
        start_col: number;
        end_line: number;
        end_col: number;
    } | null;
    refs: Record<string, unknown>;
}

/**
 * Run the structural inspector against a jsfcstm state-machine model.
 */
export function inspectModel(machine: StateMachine, options: InspectModelOptions = {}): ModelInspect {
    const deepHierarchyThreshold = normalizeIntThreshold(
        'deepHierarchyThreshold',
        options.deepHierarchyThreshold ?? DEFAULT_DEEP_HIERARCHY_THRESHOLD,
    );
    const largeCompositeThreshold = normalizeIntThreshold(
        'largeCompositeThreshold',
        options.largeCompositeThreshold ?? DEFAULT_LARGE_COMPOSITE_THRESHOLD,
    );
    const varToLeafRatioThreshold = normalizeNumberThreshold(
        'varToLeafRatioThreshold',
        options.varToLeafRatioThreshold ?? DEFAULT_VAR_TO_LEAF_RATIO_THRESHOLD,
    );
    const rootStatePath = dottedPath(machine.rootState.path);
    const states = buildStateInfos(machine);
    const transitions = buildTransitionInfos(machine);
    const variables = buildVariableInfos(machine, states);
    const events = buildEventInfos(machine);
    const actions = buildActionInfos(machine);
    const forcedTransitions = buildForcedTransitionInfos(machine);
    const metrics = buildMetrics(states, transitions, variables, events);
    const reachabilityGraph = buildReachabilityGraph(states, transitions);
    return {
        root_state_path: rootStatePath,
        states,
        transitions,
        variables,
        events,
        actions,
        forced_transitions: forcedTransitions,
        metrics,
        reachability_graph: reachabilityGraph,
        event_emission_map: buildEventEmissionMap(events),
        var_dataflow: buildVarDataflow(variables),
        aspect_impact_map: buildAspectImpactMap(states),
        action_ref_graph: buildActionRefGraph(machine),
        diagnostics: collectDesignHealthWarnings(
            states,
            transitions,
            variables,
            events,
            actions,
            forcedTransitions,
            metrics,
            reachabilityGraph,
            rootStatePath,
            {
                deepHierarchyThreshold,
                largeCompositeThreshold,
                varToLeafRatioThreshold,
            },
            machine,
        ),
    };
}

function normalizeIntThreshold(name: string, value: number): number {
    if (!Number.isFinite(value) || !Number.isInteger(value)) {
        throw new Error(`${name} must be an integer threshold, got ${JSON.stringify(value)}`);
    }
    return value;
}

function normalizeNumberThreshold(name: string, value: number): number {
    if (typeof value !== 'number' || !Number.isFinite(value)) {
        throw new Error(`${name} must be a finite numeric threshold, got ${JSON.stringify(value)}`);
    }
    return value;
}

/**
 * Serialize a :class:`ModelInspect` to a plain JSON object. This is a
 * no-op identity for jsfcstm since the data shape already matches the
 * shared contract, but kept as a function for symmetry with pyfcstm.
 */
export function inspectModelToJson(inspect: ModelInspect): ModelInspect {
    return JSON.parse(JSON.stringify(inspect));
}

// ---------------------------------------------------------------------------
// Implementation
// ---------------------------------------------------------------------------

function dottedPath(path: readonly string[]): string {
    return path.filter(p => p !== null && p !== undefined).join('.');
}

function resolveSiblingPath(parentPath: readonly string[], name: string): string {
    const parent = dottedPath(parentPath);
    return parent ? `${parent}.${name}` : name;
}

function buildStateInfos(machine: StateMachine): StateInfo[] {
    const out: StateInfo[] = [];
    for (const state of machine.allStates) {
        const path = dottedPath(state.path);
        const parentPath = state.parentPath ? dottedPath(state.parentPath) : null;
        const isLeaf = state.isLeafState;
        const isPseudo = state.isPseudo;
        const isComposite = !isLeaf;
        const substates = Object.keys(state.substates).map(name =>
            resolveSiblingPath(state.path, name),
        );
        const actions = collectStateActions(state);
        out.push({
            path,
            name: state.name,
            parent_path: parentPath || null,
            is_leaf: isLeaf,
            is_pseudo: isPseudo,
            is_composite: isComposite,
            substates,
            initial_targets: buildInitialTargets(state),
            entry_actions: actions.entry,
            during_actions: actions.during,
            exit_actions: actions.exit,
            aspect_before: actions.aspectBefore,
            aspect_after: actions.aspectAfter,
            has_abstract_action: actions.hasAbstract,
        });
    }
    return out;
}

interface CollectedStateActions {
    entry: string[];
    during: string[];
    exit: string[];
    aspectBefore: string[];
    aspectAfter: string[];
    hasAbstract: boolean;
}

function collectStateActions(state: {
    onEnters: OnStage[];
    onDurings: OnStage[];
    onExits: OnStage[];
    onDuringAspects: OnAspect[];
}): CollectedStateActions {
    const entry = state.onEnters.map(stageLabel);
    const during = state.onDurings.map(stageLabel);
    const exit = state.onExits.map(stageLabel);
    const aspectBefore = state.onDuringAspects
        .filter(a => a.aspect === 'before')
        .map(aspectLabel);
    const aspectAfter = state.onDuringAspects
        .filter(a => a.aspect === 'after')
        .map(aspectLabel);
    const hasAbstract = [
        ...state.onEnters,
        ...state.onDurings,
        ...state.onExits,
        ...state.onDuringAspects,
    ].some(a => a.isAbstract);
    return {entry, during, exit, aspectBefore, aspectAfter, hasAbstract};
}

function stageLabel(action: OnStage): string {
    if (action.name) return action.name;
    if (action.isRef && action.ref && (action.ref as {name?: string}).name) {
        return `ref:${(action.ref as {name?: string}).name}`;
    }
    return '<inline>';
}

function aspectLabel(action: OnAspect): string {
    if (action.name) return action.name;
    if (action.isRef && action.ref && (action.ref as {name?: string}).name) {
        return `ref:${(action.ref as {name?: string}).name}`;
    }
    return '<inline>';
}

function buildInitialTargets(state: {
    path: string[];
    transitions: Transition[];
}): InitialTargetInfo[] {
    const out: InitialTargetInfo[] = [];
    for (const transition of state.transitions) {
        if (transition.fromState !== 'INIT_STATE') continue;
        const targetName = transition.toState;
        const target = typeof targetName === 'string' && targetName !== 'EXIT_STATE'
            ? resolveSiblingPath(state.path, targetName)
            : EXIT_MARK;
        const guard = exprText(transition.guard);
        const event = transition.event ? transition.event.name : null;
        out.push({
            target,
            guard,
            event,
            is_unconditional: guard === null && event === null,
        });
    }
    return out;
}

function buildTransitionInfos(machine: StateMachine): TransitionInfo[] {
    const out: TransitionInfo[] = [];
    for (const state of machine.allStates) {
        for (const t of state.transitions) {
            out.push({
                from_path: transitionEndpoint(state.path, t.fromState, true),
                to_path: transitionEndpoint(state.path, t.toState, false),
                event: t.event ? t.event.pathName : null,
                event_scope: t.event ? (t.triggerScope ?? null) : null,
                guard: exprText(t.guard),
                effect: effectsText(t.effects),
                effect_self_assigns: effectSelfAssigns(t.effects),
                is_forced: !!t.forced,
                forced_origin: t.forced ? t.text : null,
            });
        }
    }
    return out;
}

function transitionEndpoint(
    parentPath: readonly string[],
    marker: string,
    isSource: boolean,
): string {
    if (marker === 'INIT_STATE') return INIT_MARK;
    if (marker === 'EXIT_STATE') return EXIT_MARK;
    return resolveSiblingPath(parentPath, marker);
}

function buildVariableInfos(machine: StateMachine, states: StateInfo[]): VariableInfo[] {
    const readsByState: Record<string, string[]> = {};
    const writesByState: Record<string, string[]> = {};
    const readGuards: Record<string, Array<[string, string]>> = {};
    const writtenEffects: Record<string, Array<[string, string]>> = {};
    const readActionStages: Record<string, Array<[string, string]>> = {};
    const writtenActionStages: Record<string, Array<[string, string]>> = {};
    const readGuardOccurrences: Record<string, Array<[string, string, string]>> = {};
    const readEffectOccurrences: Record<string, Array<[string, string, string]>> = {};
    const readAfterWriteActionStages: Record<string, Array<[string, string]>> = {};
    const readAfterWriteEffectOccurrences: Record<string, Array<[string, string, string]>> = {};
    const writtenEffectOccurrences: Record<string, Array<[string, string, string]>> = {};
    const floatLiteralAssignments: Record<string, string[]> = {};
    for (const name of Object.keys(machine.defines)) {
        readsByState[name] = [];
        writesByState[name] = [];
        readGuards[name] = [];
        writtenEffects[name] = [];
        readActionStages[name] = [];
        writtenActionStages[name] = [];
        readGuardOccurrences[name] = [];
        readEffectOccurrences[name] = [];
        readAfterWriteActionStages[name] = [];
        readAfterWriteEffectOccurrences[name] = [];
        writtenEffectOccurrences[name] = [];
        floatLiteralAssignments[name] = [];
    }
    const stateLookup: Record<string, StateInfo> = {};
    for (const info of states) {
        stateLookup[info.path] = info;
    }
    for (const state of machine.allStates) {
        const path = dottedPath(state.path);
        const localFloatAssigns: Record<string, string[]> = {};
        for (const [stageName, collection] of stateActionCollections(state)) {
            const stageOperations: OperationStatement[] = [];
            for (const action of collection) {
                stageOperations.push(...(action.operations ?? []));
                if (action.operations && action.operations.length > 0) {
                    const localReads: string[] = [];
                    const localWrites: string[] = [];
                    for (const stmt of action.operations) {
                        walkStmtReadsWrites(stmt, localReads, localWrites);
                    }
                    for (const name of localReads) {
                        if (name in readsByState) {
                            readsByState[name].push(path);
                            readActionStages[name].push([path, stageName]);
                        }
                    }
                    for (const name of localWrites) {
                        if (name in writesByState) {
                            writesByState[name].push(path);
                            writtenActionStages[name].push([path, stageName]);
                        }
                    }
                }
                for (const stmt of action.operations ?? []) {
                    walkStmtFloatLiteralAssignments(stmt, localFloatAssigns);
                }
            }
            for (const name of blockReadsAfterWrites(stageOperations)) {
                if (name in readAfterWriteActionStages) {
                    readAfterWriteActionStages[name].push([path, stageName]);
                }
            }
        }
        for (const [name, assignments] of Object.entries(localFloatAssigns)) {
            if (name in floatLiteralAssignments) {
                floatLiteralAssignments[name].push(...assignments);
            }
        }
        state.transitions.forEach((t, index) => {
            const fromPath = transitionEndpoint(state.path, t.fromState, true);
            const toPath = transitionEndpoint(state.path, t.toState, false);
            const occurrenceKey = `${path}#${index + 1}`;
            if (t.guard) {
                for (const v of walkExprVariables(t.guard)) {
                    if (v in readGuards) {
                        readGuards[v].push([fromPath, toPath]);
                        readGuardOccurrences[v].push([fromPath, toPath, occurrenceKey]);
                    }
                }
            }
            for (const stmt of t.effects ?? []) {
                const localReads: string[] = [];
                const localWrites: string[] = [];
                const localFloatEffectAssigns: Record<string, string[]> = {};
                walkStmtReadsWrites(stmt, localReads, localWrites);
                walkStmtFloatLiteralAssignments(stmt, localFloatEffectAssigns);
                for (const v of localReads) {
                    if (v in readsByState) {
                        readsByState[v].push(fromPath);
                        readEffectOccurrences[v].push([fromPath, toPath, occurrenceKey]);
                    }
                }
                for (const v of localWrites) {
                    if (v in writtenEffects) {
                        writtenEffects[v].push([fromPath, toPath]);
                        writtenEffectOccurrences[v].push([fromPath, toPath, occurrenceKey]);
                    }
                }
                for (const [v, assignments] of Object.entries(localFloatEffectAssigns)) {
                    if (v in floatLiteralAssignments) {
                        floatLiteralAssignments[v].push(...assignments);
                    }
                }
            }
            for (const v of blockReadsAfterWrites(t.effects ?? [])) {
                if (v in readAfterWriteEffectOccurrences) {
                    readAfterWriteEffectOccurrences[v].push([fromPath, toPath, occurrenceKey]);
                }
            }
        });
    }

    const dedupe = (xs: string[]): string[] => Array.from(new Set(xs));
    const dedupePairs = (pairs: Array<[string, string]>): Array<[string, string]> => {
        const seen = new Set<string>();
        const out: Array<[string, string]> = [];
        for (const p of pairs) {
            const k = `${p[0]}${p[1]}`;
            if (!seen.has(k)) {
                seen.add(k);
                out.push(p);
            }
        }
        return out;
    };
    const dedupeTriples = (triples: Array<[string, string, string]>): Array<[string, string, string]> => {
        const seen = new Set<string>();
        const out: Array<[string, string, string]> = [];
        for (const triple of triples) {
            const key = `${triple[0]}\u0001${triple[1]}\u0001${triple[2]}`;
            if (!seen.has(key)) {
                seen.add(key);
                out.push(triple);
            }
        }
        return out;
    };

    const out: VariableInfo[] = [];
    for (const name of Object.keys(machine.defines)) {
        const def = machine.defines[name];
        const readStates = dedupe(readsByState[name]);
        const writtenStates = dedupe(writesByState[name]);
        const readGuardEntries = dedupePairs(readGuards[name]);
        const writtenEffectEntries = dedupePairs(writtenEffects[name]);
        const readActionStageEntries = dedupePairs(readActionStages[name]);
        const writtenActionStageEntries = dedupePairs(writtenActionStages[name]);
        const readGuardOccurrenceEntries = dedupeTriples(readGuardOccurrences[name]);
        const readEffectOccurrenceEntries = dedupeTriples(readEffectOccurrences[name]);
        const readAfterWriteActionStageEntries = dedupePairs(readAfterWriteActionStages[name]);
        const readAfterWriteEffectOccurrenceEntries = dedupeTriples(readAfterWriteEffectOccurrences[name]);
        const writtenEffectOccurrenceEntries = dedupeTriples(writtenEffectOccurrences[name]);
        const participatesDirectly = readStates.length > 0 ||
            readGuardEntries.length > 0 ||
            writtenStates.length > 0 ||
            writtenEffectEntries.length > 0;
        const abstractActions = abstractActionsInScope(
            stateLookup,
            readStates,
            writtenStates,
            states,
        );
        out.push({
            name,
            type: def.type,
            init_value: exprText(def.init) ?? '',
            read_in_states: readStates,
            written_in_states: writtenStates,
            read_in_guards: readGuardEntries,
            written_in_effects: writtenEffectEntries,
            read_in_action_stages: readActionStageEntries,
            written_in_action_stages: writtenActionStageEntries,
            read_in_guard_occurrences: readGuardOccurrenceEntries,
            read_in_effect_occurrences: readEffectOccurrenceEntries,
            read_after_write_action_stages: readAfterWriteActionStageEntries,
            read_after_write_effect_occurrences: readAfterWriteEffectOccurrenceEntries,
            written_in_effect_occurrences: writtenEffectOccurrenceEntries,
            participates_directly: participatesDirectly,
            participates_indirectly: false,
            abstract_actions_in_scope: abstractActions,
            float_literal_assignments: dedupe(floatLiteralAssignments[name]),
        });
    }
    return out;
}

function stateActionCollections(state: {
    onEnters: OnStage[];
    onDurings: OnStage[];
    onExits: OnStage[];
    onDuringAspects: OnAspect[];
}): Array<[string, Array<OnStage | OnAspect>]> {
    return [
        ['enter', state.onEnters],
        ['during', state.onDurings],
        ['exit', state.onExits],
        ['during_aspect', state.onDuringAspects],
    ];
}

function walkExprVariables(expr: Expr | null | undefined): string[] {
    if (!expr) return [];
    const out: string[] = [];
    walkExprCollect(expr, out);
    return out;
}

function walkExprCollect(expr: Expr, out: string[]): void {
    const anyExpr = expr as unknown as {
        pyModelType: string;
        name?: string;
        x?: Expr;
        y?: Expr;
        cond?: Expr;
        ifTrue?: Expr;
        ifFalse?: Expr;
    };
    switch (anyExpr.pyModelType) {
        case 'Variable':
            if (anyExpr.name) out.push(anyExpr.name);
            return;
        case 'UnaryOp':
        case 'UFunc':
            if (anyExpr.x) walkExprCollect(anyExpr.x, out);
            return;
        case 'BinaryOp':
            if (anyExpr.x) walkExprCollect(anyExpr.x, out);
            if (anyExpr.y) walkExprCollect(anyExpr.y, out);
            return;
        case 'ConditionalOp':
            if (anyExpr.cond) walkExprCollect(anyExpr.cond, out);
            if (anyExpr.ifTrue) walkExprCollect(anyExpr.ifTrue, out);
            if (anyExpr.ifFalse) walkExprCollect(anyExpr.ifFalse, out);
            return;
        default:
            return;
    }
}

function walkStmtReadsWrites(
    stmt: OperationStatement,
    reads: string[],
    writes: string[],
): void {
    if (stmt instanceof Operation) {
        writes.push(stmt.varName);
        for (const v of walkExprVariables(stmt.expr)) reads.push(v);
        return;
    }
    if (stmt instanceof IfBlock) {
        for (const branch of stmt.branches) {
            if (branch.condition) {
                for (const v of walkExprVariables(branch.condition)) reads.push(v);
            }
            for (const inner of branch.statements) {
                walkStmtReadsWrites(inner, reads, writes);
            }
        }
    }
}

function blockReadsAfterWrites(statements: OperationStatement[]): string[] {
    const [readsAfterWrites] = blockReadsAfterWritesFrom(statements, new Set<string>());
    return Array.from(readsAfterWrites);
}

function blockReadsAfterWritesFrom(
    statements: OperationStatement[],
    priorWrites: Set<string>,
): [Set<string>, Set<string>] {
    const readsAfterWrites = new Set<string>();
    let writes = new Set(priorWrites);
    for (const stmt of statements) {
        if (stmt instanceof Operation) {
            for (const name of walkExprVariables(stmt.expr)) {
                if (writes.has(name)) readsAfterWrites.add(name);
            }
            writes.add(stmt.varName);
            continue;
        }
        if (stmt instanceof IfBlock) {
            for (const branch of stmt.branches) {
                if (branch.condition) {
                    for (const name of walkExprVariables(branch.condition)) {
                        if (writes.has(name)) readsAfterWrites.add(name);
                    }
                }
            }
            const branchWrites = new Set(writes);
            for (const branch of stmt.branches) {
                const [branchReads, branchResultWrites] = blockReadsAfterWritesFrom(
                    branch.statements,
                    new Set(writes),
                );
                for (const name of branchReads) readsAfterWrites.add(name);
                for (const name of branchResultWrites) branchWrites.add(name);
            }
            writes = branchWrites;
        }
    }
    return [readsAfterWrites, writes];
}

function effectSelfAssigns(effects: OperationStatement[] | undefined): string[] {
    const out: string[] = [];
    for (const stmt of effects ?? []) {
        walkStmtSelfAssigns(stmt, out);
    }
    return Array.from(new Set(out));
}

function walkStmtSelfAssigns(stmt: OperationStatement, out: string[]): void {
    if (stmt instanceof Operation) {
        if (stmt.expr instanceof Variable && stmt.expr.name === stmt.varName) {
            out.push(stmt.varName);
        }
        return;
    }
    if (stmt instanceof IfBlock) {
        for (const branch of stmt.branches) {
            for (const inner of branch.statements) {
                walkStmtSelfAssigns(inner, out);
            }
        }
    }
}

function walkStmtFloatLiteralAssignments(
    stmt: OperationStatement,
    out: Record<string, string[]>,
): void {
    if (stmt instanceof Operation) {
        if (stmt.expr instanceof Float) {
            out[stmt.varName] = [...(out[stmt.varName] ?? []), exprText(stmt.expr) ?? ''];
        }
        return;
    }
    if (stmt instanceof IfBlock) {
        for (const branch of stmt.branches) {
            for (const inner of branch.statements) {
                walkStmtFloatLiteralAssignments(inner, out);
            }
        }
    }
}

function canonicalBinaryOperator(op: string): string {
    if (op === 'and') return '&&';
    if (op === 'or') return '||';
    return op;
}

function canonicalUnaryOperator(op: string): string {
    return op === 'not' ? '!' : op;
}

function unaryPrecedenceKey(op: string): string {
    const canonical = canonicalUnaryOperator(op);
    return canonical === '+' || canonical === '-' ? `unary${canonical}` : canonical;
}

function exprPrecedence(expr: Expr): number | null {
    if (expr instanceof BinaryOp) return OP_PRECEDENCE[canonicalBinaryOperator(expr.op)] ?? null;
    if (expr instanceof UnaryOp) return OP_PRECEDENCE[unaryPrecedenceKey(expr.op)] ?? null;
    if (expr instanceof ConditionalOp) return OP_PRECEDENCE['?:'];
    return null;
}

function normalizeDecimalDigits(raw: string): string {
    const normalized = raw.replace(/^0+/, '');
    return normalized.length > 0 ? normalized : '0';
}

function addSmallDecimal(raw: string, value: number): string {
    if (value === 0) return raw;
    let carry = value;
    const out: string[] = [];
    for (let index = raw.length - 1; index >= 0; index -= 1) {
        const total = Number(raw[index]) + carry;
        out.push(String(total % 10));
        carry = Math.floor(total / 10);
    }
    while (carry > 0) {
        out.push(String(carry % 10));
        carry = Math.floor(carry / 10);
    }
    return out.reverse().join('');
}

function multiplySmallDecimal(raw: string, factor: number): string {
    if (raw === '0' || factor === 0) return '0';
    let carry = 0;
    const out: string[] = [];
    for (let index = raw.length - 1; index >= 0; index -= 1) {
        const total = Number(raw[index]) * factor + carry;
        out.push(String(total % 10));
        carry = Math.floor(total / 10);
    }
    while (carry > 0) {
        out.push(String(carry % 10));
        carry = Math.floor(carry / 10);
    }
    return out.reverse().join('');
}

function convertRadixDigitsToDecimal(digits: string, radix: number): string {
    let value = '0';
    for (const char of digits.toLowerCase()) {
        const digit = parseInt(char, radix);
        value = addSmallDecimal(multiplySmallDecimal(value, radix), digit);
    }
    return value;
}

function integerText(expr: Integer): string {
    const raw = expr.text.trim();
    if (/^\d+$/.test(raw)) return normalizeDecimalDigits(raw);
    if (/^0[xX][0-9a-fA-F]+$/.test(raw)) {
        return convertRadixDigitsToDecimal(raw.slice(2), 16);
    }
    if (/^0[bB][01]+$/.test(raw)) {
        return convertRadixDigitsToDecimal(raw.slice(2), 2);
    }
    return String(Math.trunc(expr.value));
}

function floatText(expr: Float): string {
    if (Math.abs(expr.value - Math.PI) < FLOAT_EPSILON) return 'pi';
    if (Math.abs(expr.value - Math.E) < FLOAT_EPSILON) return 'E';
    if (Math.abs(expr.value - Math.PI * 2) < FLOAT_EPSILON) return 'tau';
    if (Number.isInteger(expr.value)) return `${expr.value}.0`;
    return String(expr.value);
}

function formatExpr(expr: Expr): string {
    if (expr instanceof Integer) return integerText(expr);
    if (expr instanceof Float) return floatText(expr);
    if (expr instanceof BooleanExpr) return expr.value ? 'true' : 'false';
    if (expr instanceof Variable) return expr.name;
    if (expr instanceof UFunc) return `${expr.func}(${formatExpr(expr.x)})`;
    if (expr instanceof UnaryOp) {
        const op = canonicalUnaryOperator(expr.op);
        const myPrecedence = OP_PRECEDENCE[unaryPrecedenceKey(expr.op)];
        let value = formatExpr(expr.x);
        const valuePrecedence = exprPrecedence(expr.x);
        if (valuePrecedence !== null && valuePrecedence <= myPrecedence) {
            value = `(${value})`;
        }
        return `${op}${value}`;
    }
    if (expr instanceof BinaryOp) {
        const op = canonicalBinaryOperator(expr.op);
        const myPrecedence = OP_PRECEDENCE[op];
        let left = formatExpr(expr.x);
        const leftPrecedence = exprPrecedence(expr.x);
        if (leftPrecedence !== null && leftPrecedence < myPrecedence) {
            left = `(${left})`;
        }
        let right = formatExpr(expr.y);
        const rightPrecedence = exprPrecedence(expr.y);
        if (rightPrecedence !== null && rightPrecedence <= myPrecedence) {
            right = `(${right})`;
        }
        return `${left} ${op} ${right}`;
    }
    if (expr instanceof ConditionalOp) {
        const myPrecedence = OP_PRECEDENCE['?:'];
        let whenTrue = formatExpr(expr.ifTrue);
        const truePrecedence = exprPrecedence(expr.ifTrue);
        if (truePrecedence !== null && truePrecedence <= myPrecedence) {
            whenTrue = `(${whenTrue})`;
        }
        let whenFalse = formatExpr(expr.ifFalse);
        const falsePrecedence = exprPrecedence(expr.ifFalse);
        if (falsePrecedence !== null && falsePrecedence <= myPrecedence) {
            whenFalse = `(${whenFalse})`;
        }
        return `(${formatExpr(expr.cond)}) ? ${whenTrue} : ${whenFalse}`;
    }
    return expr.text;
}

function statementText(stmt: OperationStatement): string {
    if (stmt instanceof Operation) {
        return `${stmt.varName} = ${formatExpr(stmt.expr)};`;
    }
    if (stmt instanceof IfBlock) {
        const firstBranch = stmt.branches[0];
        if (!firstBranch || firstBranch.condition === null) return stmt.text;
        const lines: string[] = [`if [${formatExpr(firstBranch.condition)}] {`];
        for (let index = 0; index < stmt.branches.length; index += 1) {
            const branch = stmt.branches[index];
            if (index > 0) {
                if (branch.condition === null) {
                    lines.push('} else {');
                } else {
                    lines.push(`} else if [${formatExpr(branch.condition)}] {`);
                }
            }
            for (const inner of branch.statements) {
                for (const line of statementText(inner).split('\n')) {
                    lines.push(line.trim().length > 0 ? `    ${line}` : line);
                }
            }
        }
        lines.push('}');
        return lines.join('\n');
    }
    return stmt.text;
}

function exprText(expr: Expr | null | undefined): string | null {
    return expr ? formatExpr(expr) : null;
}

function effectsText(effects: OperationStatement[] | undefined): string | null {
    if (!effects || effects.length === 0) return null;
    const parts = effects.map(statementText).filter(text => text.length > 0);
    return parts.length ? parts.join(' ') : null;
}

function abstractActionsInScope(
    stateLookup: Record<string, StateInfo>,
    readStates: string[],
    writtenStates: string[],
    states: StateInfo[],
): string[] {
    const touched = new Set<string>([...readStates, ...writtenStates]);
    if (touched.size === 0) {
        return states
            .filter(info => info.has_abstract_action)
            .map(info => `${info.path}:<abstract>`);
    }
    const out: string[] = [];
    for (const path of Array.from(touched).sort()) {
        const info = stateLookup[path];
        if (!info || !info.has_abstract_action) continue;
        const label = `${info.path}:<abstract>`;
        if (!out.includes(label)) out.push(label);
    }
    return out;
}

function buildEventInfos(machine: StateMachine): EventInfo[] {
    const users: Record<string, Array<[string, string]>> = {};
    const scopes: Record<string, 'local' | 'chain' | 'absolute'> = {};
    const declared: Record<string, boolean> = {};
    for (const event of machine.allEvents ?? []) {
        const qn = event.pathName;
        if (!users[qn]) users[qn] = [];
        scopes[qn] = scopeFromEventOrigins(event);
        declared[qn] = event.declared;
    }
    for (const state of machine.allStates) {
        for (const t of state.transitions) {
            if (!t.event) continue;
            const qn = t.event.pathName;
            const fromPath = transitionEndpoint(state.path, t.fromState, true);
            const toPath = transitionEndpoint(state.path, t.toState, false);
            if (!users[qn]) users[qn] = [];
            users[qn].push([fromPath, toPath]);
            scopes[qn] = t.triggerScope ?? 'absolute';
            declared[qn] = declared[qn] ?? t.event.declared;
        }
    }
    const out: EventInfo[] = [];
    for (const qn of Object.keys(users).sort()) {
        const usedBy = users[qn];
        out.push({
            qualified_name: qn,
            scope: scopes[qn] ?? 'absolute',
            used_by: usedBy,
            is_declared: declared[qn] ?? false,
            is_used: usedBy.length > 0,
        });
    }
    return out;
}

function buildActionInfos(machine: StateMachine): ActionInfo[] {
    const out: ActionInfo[] = [];
    for (const state of machine.allStates) {
        for (const collection of [state.onEnters, state.onDurings, state.onExits, state.onDuringAspects]) {
            for (const action of collection) {
                out.push({
                    signature: functionSignature(state.path, action),
                    state_path: dottedPath(state.path),
                    name: action.name ?? null,
                    stage: action.stage,
                    aspect: action.aspect ?? null,
                    is_ref: action.isRef,
                    ref_target: action.isRef && action.ref
                        ? functionSignature(undefined, action.ref as unknown as OnStage)
                        : null,
                    is_attached: true,
                });
            }
        }
    }
    return out;
}

function buildForcedTransitionInfos(machine: StateMachine): ForcedTransitionInfo[] {
    return (machine.forcedTransitions as RawFcstmModelForcedTransition[]).map(item => ({
        state_path: dottedPath(item.statePath ?? item.state_path),
        from_path: item.fromPath ?? item.from_path,
        to_path: item.toPath ?? item.to_path,
        event: item.event ?? null,
        event_scope: item.event ? (item.event_scope ?? null) : null,
        guard: item.guard ?? null,
        original_raw: item.originalRaw ?? item.original_raw,
        expansion_count: item.expansionCount ?? item.expansion_count,
    }));
}

function scopeFromEventOrigins(event: Event): 'local' | 'chain' | 'absolute' {
    const scopes = event.origins.filter(origin => origin !== 'declared');
    if (scopes.includes('local')) return 'local';
    if (scopes.includes('absolute')) return 'absolute';
    return 'chain';
}

function buildMetrics(
    states: StateInfo[],
    transitions: TransitionInfo[],
    variables: VariableInfo[],
    events: EventInfo[],
): ModelMetrics {
    const nPseudo = states.filter(s => s.is_pseudo).length;
    const nLeaf = states.filter(s => s.is_leaf && !s.is_pseudo).length;
    const nComposite = states.filter(s => s.is_composite).length;
    const nNormal = transitions.filter(t => !t.is_forced).length;
    const nForced = transitions.filter(t => t.is_forced).length;
    const aspectCoverage: Record<string, number> = {};
    for (const s of states) {
        if (!(s.is_composite && (s.aspect_before.length > 0 || s.aspect_after.length > 0))) continue;
        aspectCoverage[s.path] = states.filter(d =>
            d.path !== s.path &&
            d.path.startsWith(`${s.path}.`) &&
            d.is_leaf &&
            !d.is_pseudo,
        ).length;
    }
    const abstractInventory = states.filter(s => s.has_abstract_action).map(s => s.path).sort();
    const depth = states.reduce(
        (acc, s) => Math.max(acc, (s.path.match(/\./g) ?? []).length),
        0,
    );
    return {
        n_states_leaf: nLeaf,
        n_states_composite: nComposite,
        n_states_pseudo: nPseudo,
        max_hierarchy_depth: depth,
        n_transitions_normal: nNormal,
        n_transitions_forced: nForced,
        n_events: events.length,
        n_variables: variables.length,
        var_to_leaf_ratio: variables.length / Math.max(nLeaf, 1),
        aspect_coverage: aspectCoverage,
        abstract_action_inventory: abstractInventory,
    };
}

function buildReachabilityGraph(
    states: StateInfo[],
    transitions: TransitionInfo[],
): Record<string, string[]> {
    const adjacency: Record<string, Set<string>> = {};
    const initialEdges: Record<string, Set<string>> = {};
    for (const s of states) {
        adjacency[s.path] = new Set();
        initialEdges[s.path] = new Set();
    }
    for (const t of transitions) {
        if (t.from_path === INIT_MARK || t.to_path === EXIT_MARK) continue;
        adjacency[t.from_path]?.add(t.to_path);
    }
    for (const s of states) {
        if (s.is_composite && s.initial_targets.length > 0) {
            for (const it of s.initial_targets) {
                if (it.target !== EXIT_MARK) {
                    initialEdges[s.path].add(it.target);
                }
            }
        }
    }
    const out: Record<string, string[]> = {};
    for (const s of states) {
        const seen = new Set<string>();
        const queue: string[] = [s.path];
        while (queue.length > 0) {
            const cur = queue.shift()!;
            const next = Array.from(
                new Set([
                    ...(adjacency[cur] ? Array.from(adjacency[cur]) : []),
                    ...(initialEdges[cur] ? Array.from(initialEdges[cur]) : []),
                ]),
            ).sort();
            for (const nxt of next) {
                if (seen.has(nxt) || nxt === s.path) continue;
                seen.add(nxt);
                queue.push(nxt);
            }
        }
        out[s.path] = Array.from(seen).sort();
    }
    return out;
}

function buildEventEmissionMap(events: EventInfo[]): Record<string, string[]> {
    const out: Record<string, string[]> = {};
    for (const e of events) {
        if (!e.is_used) continue;
        const froms = Array.from(
            new Set(e.used_by.filter(p => p[0] !== INIT_MARK).map(p => p[0])),
        ).sort();
        out[e.qualified_name] = froms;
    }
    return out;
}

function buildVarDataflow(variables: VariableInfo[]): Record<string, {reads: string[]; writes: string[]}> {
    const out: Record<string, {reads: string[]; writes: string[]}> = {};
    for (const v of variables) {
        out[v.name] = {
            reads: Array.from(new Set(v.read_in_states)).sort(),
            writes: Array.from(new Set(v.written_in_states)).sort(),
        };
    }
    return out;
}

function buildAspectImpactMap(states: StateInfo[]): Record<string, string[]> {
    const out: Record<string, string[]> = {};
    for (const s of states) {
        if (!(s.is_composite && (s.aspect_before.length > 0 || s.aspect_after.length > 0))) continue;
        out[s.path] = states.filter(d =>
            d.path !== s.path &&
            d.path.startsWith(`${s.path}.`) &&
            d.is_leaf &&
            !d.is_pseudo,
        ).map(d => d.path).sort();
    }
    return out;
}

function buildActionRefGraph(machine: StateMachine): Record<string, string[]> {
    const edges: Record<string, string[]> = {};
    for (const state of machine.allStates) {
        for (const collection of [state.onEnters, state.onDurings, state.onExits, state.onDuringAspects]) {
            for (const action of collection) {
                const source = functionSignature(state.path, action);
                if (action.isRef && action.ref) {
                    const target = functionSignature(undefined, action.ref as unknown as OnStage);
                    if (!edges[source]) edges[source] = [];
                    edges[source].push(target);
                } else if (!edges[source]) {
                    edges[source] = [];
                }
            }
        }
    }
    const out: Record<string, string[]> = {};
    for (const key of Object.keys(edges)) {
        out[key] = Array.from(new Set(edges[key])).sort();
    }
    return out;
}

function functionSignature(defaultPath: readonly string[] | undefined, action: OnStage | OnAspect): string {
    const actionPath = (action as unknown as {statePath?: string[]}).statePath;
    let normalized = '';
    if (actionPath && actionPath.length > 0) {
        normalized = dottedPath(actionPath.slice(0, -1));
        if (!normalized && defaultPath) normalized = dottedPath(defaultPath);
    } /* c8 ignore start -- defensive: OnStage/OnAspect always set statePath */ else if (defaultPath) {
        // Reserved for future action synthesizers that emit actions
        // without ``statePath``. The grammar-driven path always sets
        // statePath (see ``model/runtime.ts:OnStage.statePath`` /
        // ``OnAspect.statePath``).
        normalized = dottedPath(defaultPath);
    } /* c8 ignore stop */
    const leaf = actionPath && actionPath.length > 0
        ? actionPath[actionPath.length - 1] ?? '<inline>'
        : action.name ?? '<inline>';
    return normalized ? `${normalized}:${leaf}` : leaf;
}

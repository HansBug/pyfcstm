/**
 * Structured model inspection for jsfcstm, mirrored from the pyfcstm
 * Layer 2 PR-A entry point ``pyfcstm.diagnostics.inspect_model``.
 *
 * The public field shape, view-graph derivation, and ``toJson()`` output
 * are kept byte-equivalent to the pyfcstm side so that the shared
 * ``pyfcstm/diagnostics/schema.json`` contract validates either side's
 * output. Layer 2 strictness: anything pyfcstm produces, jsfcstm must
 * produce too. PR-B / PR-C will populate the ``diagnostics`` array;
 * PR-A keeps it empty.
 */

import {
    Event,
    Expr,
    IfBlock,
    OnAspect,
    OnStage,
    Operation,
    OperationStatement,
    StateMachine,
    Transition,
} from '../model/runtime';
import {collectB1Diagnostics} from './analyzers';

const INIT_MARK = '[*]';
const EXIT_MARK = '[*]';

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
    participates_directly: boolean;
    participates_indirectly: boolean;
    abstract_actions_in_scope: string[];
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
 * PR-A keeps this empty; PR-B / PR-C populate it.
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
export function inspectModel(machine: StateMachine): ModelInspect {
    const states = buildStateInfos(machine);
    const transitions = buildTransitionInfos(machine);
    const variables = buildVariableInfos(machine, states);
    const events = buildEventInfos(machine);
    const metrics = buildMetrics(states, transitions, variables, events);
    const reachabilityGraph = buildReachabilityGraph(states, transitions);
    return {
        root_state_path: dottedPath(machine.rootState.path),
        states,
        transitions,
        variables,
        events,
        metrics,
        reachability_graph: reachabilityGraph,
        event_emission_map: buildEventEmissionMap(events),
        var_dataflow: buildVarDataflow(variables),
        aspect_impact_map: buildAspectImpactMap(states),
        action_ref_graph: buildActionRefGraph(machine),
        diagnostics: collectB1Diagnostics(states, transitions, events, reachabilityGraph),
    };
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
                is_forced: !!t.forced,
                forced_origin: null,
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
    for (const name of Object.keys(machine.defines)) {
        readsByState[name] = [];
        writesByState[name] = [];
        readGuards[name] = [];
        writtenEffects[name] = [];
    }
    const stateLookup: Record<string, StateInfo> = {};
    for (const info of states) {
        stateLookup[info.path] = info;
    }
    for (const state of machine.allStates) {
        const path = dottedPath(state.path);
        const {reads, writes} = collectActionReadsWrites(state);
        for (const name of Object.keys(reads)) {
            if (name in readsByState) readsByState[name].push(path);
        }
        for (const name of Object.keys(writes)) {
            if (name in writesByState) writesByState[name].push(path);
        }
        for (const t of state.transitions) {
            const fromPath = transitionEndpoint(state.path, t.fromState, true);
            const toPath = transitionEndpoint(state.path, t.toState, false);
            if (t.guard) {
                for (const v of walkExprVariables(t.guard)) {
                    if (v in readGuards) readGuards[v].push([fromPath, toPath]);
                }
            }
            for (const stmt of t.effects ?? []) {
                const localReads: string[] = [];
                const localWrites: string[] = [];
                walkStmtReadsWrites(stmt, localReads, localWrites);
                for (const v of localReads) {
                    if (v in readsByState) readsByState[v].push(fromPath);
                }
                for (const v of localWrites) {
                    if (v in writtenEffects) writtenEffects[v].push([fromPath, toPath]);
                }
            }
        }
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

    const out: VariableInfo[] = [];
    for (const name of Object.keys(machine.defines)) {
        const def = machine.defines[name];
        const readStates = dedupe(readsByState[name]);
        const writtenStates = dedupe(writesByState[name]);
        const readGuardEntries = dedupePairs(readGuards[name]);
        const writtenEffectEntries = dedupePairs(writtenEffects[name]);
        const participatesDirectly = readStates.length > 0 || readGuardEntries.length > 0;
        const abstractActions = abstractActionsInScope(
            stateLookup,
            readStates,
            writtenStates,
        );
        out.push({
            name,
            type: def.type,
            init_value: exprText(def.init) ?? '',
            read_in_states: readStates,
            written_in_states: writtenStates,
            read_in_guards: readGuardEntries,
            written_in_effects: writtenEffectEntries,
            participates_directly: participatesDirectly,
            participates_indirectly: false,
            abstract_actions_in_scope: abstractActions,
        });
    }
    return out;
}

function collectActionReadsWrites(state: {
    onEnters: OnStage[];
    onDurings: OnStage[];
    onExits: OnStage[];
    onDuringAspects: OnAspect[];
}): {reads: Record<string, true>; writes: Record<string, true>} {
    const reads: Record<string, true> = {};
    const writes: Record<string, true> = {};
    for (const collection of [state.onEnters, state.onDurings, state.onExits, state.onDuringAspects]) {
        for (const action of collection) {
            if (!action.operations || action.operations.length === 0) continue;
            const localReads: string[] = [];
            const localWrites: string[] = [];
            for (const stmt of action.operations) {
                walkStmtReadsWrites(stmt, localReads, localWrites);
            }
            for (const v of localReads) reads[v] = true;
            for (const v of localWrites) writes[v] = true;
        }
    }
    return {reads, writes};
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

function exprText(expr: Expr | null | undefined): string | null {
    if (!expr) return null;
    const text = (expr as unknown as {text?: string}).text;
    if (typeof text === 'string' && text.length > 0) return text;
    /* c8 ignore next 2 */
    return null;  // defensive: grammar always sets .text on Expr; this fallback covers future Expr subclasses that don't
}

function effectsText(effects: OperationStatement[] | undefined): string | null {
    if (!effects || effects.length === 0) return null;
    const parts: string[] = [];
    for (const stmt of effects) {
        const t = (stmt as unknown as {text?: string}).text;
        if (typeof t === 'string' && t.length > 0) parts.push(t);
    }
    return parts.length ? parts.join(' ') : null;
}

function abstractActionsInScope(
    stateLookup: Record<string, StateInfo>,
    readStates: string[],
    writtenStates: string[],
): string[] {
    const touched = new Set<string>([...readStates, ...writtenStates]);
    if (touched.size === 0) return [];
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

function scopeFromEventOrigins(event: Event): 'local' | 'chain' | 'absolute' {
    if (event.origins.includes('local')) return 'local';
    if (event.origins.includes('absolute')) return 'absolute';
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
        var_to_leaf_ratio: nLeaf > 0 ? variables.length / nLeaf : 0,
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

/**
 * History pseudo-states (``[H]`` / ``[H*]``) lowered into plain FCSTM.
 *
 * Mirrors ``pyfcstm.model.history``: after forced and combo transitions are
 * concrete edges, every used history owner gets one ``__hist_<owner>``
 * record written by the exits of its stoppable leaves, and the machine gets
 * one shared ``__hist_goto`` restore target. A history entry computes the
 * target once in its effect; one guarded route per (composite, child) steers
 * the restore over preorder id ranges; the remaining user initials of those
 * composites are gated so a blocked restore rejects the whole transition.
 * The lowered model, the diagnostics and the owner metadata must stay equal
 * to pyfcstm's for the same source.
 */
import type {FcstmAstHistoryDefinition, FcstmAstStateDefinition, FcstmHistoryKind} from '../ast';
import {createRange, type TextRange} from '../utils/text';
import type {
    FcstmModelHistoryDiagnostic,
    FcstmModelHistoryRole,
    RawFcstmModelExpression as Expr,
    RawFcstmModelNamedFunction,
    RawFcstmModelOnStage,
    RawFcstmModelOperation,
    RawFcstmModelOperationStatement,
    RawFcstmModelHistoryOwner,
    RawFcstmModelState as State,
    RawFcstmModelTransition as Transition,
    RawFcstmModelVarDefine,
} from './raw';
import type {
    Expr as ModelExpr,
    OperationStatement as ModelOperationStatement,
    State as ModelState,
    StateMachine as ModelStateMachine,
    Transition as ModelTransition,
} from './runtime';

export const HISTORY_PREFIX = '__hist_';
export const HISTORY_MARKERS: Record<FcstmHistoryKind, string> = {shallow: '[H]', deep: '[H*]'};

const GOTO_TAG = 'goto';
// Every target-language identifier conversion collapses runs of underscores,
// so ``__hist_x`` and ``_hist_x`` meet in generated code.
const RESERVED_IN_HISTORY_MODELS = /^_+hist_/;
const ZERO: TextRange = createRange(0, 0, 0, 0);

type Path = string[];
const key = (path: Path): string => path.join('.');
const isPrefix = (prefix: Path, path: Path): boolean => prefix.every((name, index) => path[index] === name);

export interface HistoryLoweringInput {
    astRoot: FcstmAstStateDefinition;
    rootState: State;
    defines: Record<string, RawFcstmModelVarDefine>;
    allStates: State[];
    allActions: RawFcstmModelNamedFunction[];
    statesByPath: Map<string, State>;
    filePath: string;
}

export interface HistoryLoweringResult {
    owners: RawFcstmModelHistoryOwner[];
    diagnostics: FcstmModelHistoryDiagnostic[];
}

function walk(state: State, out: State[] = []): State[] {
    out.push(state);
    for (const child of Object.values(state.substates)) walk(child, out);
    return out;
}

function walkAst(node: FcstmAstStateDefinition, path: Path = [], out: Array<[Path, FcstmAstStateDefinition]> = []) {
    const current = [...path, node.name];
    out.push([current, node]);
    for (const child of node.substates) walkAst(child, current, out);
    return out;
}

function operations(statements: RawFcstmModelOperationStatement[], out: RawFcstmModelOperation[] = []) {
    for (const statement of statements) {
        if (statement.kind === 'ifBlock') {
            for (const branch of statement.branches) operations(branch.statements, out);
        } else {
            out.push(statement);
        }
    }
    return out;
}

function stateOperations(state: State): RawFcstmModelOperation[] {
    const out: RawFcstmModelOperation[] = [];
    for (const action of [...state.onEnters, ...state.onDurings, ...state.onExits, ...state.onDuringAspects]) {
        operations(action.operations, out);
    }
    for (const transition of state.transitions) operations(transition.effects, out);
    return out;
}

function variable(name: string): Expr {
    return {kind: 'variable', pyModelType: 'Variable', range: ZERO, text: name, name};
}

function integer(value: number): Expr {
    return {kind: 'integer', pyModelType: 'Integer', range: ZERO, text: String(value), value};
}

function binary(x: Expr, op: string, y: Expr): Expr {
    return {kind: 'binaryOp', pyModelType: 'BinaryOp', range: ZERO, text: '', x, op, y};
}

function conditional(cond: Expr, ifTrue: Expr, ifFalse: Expr): Expr {
    return {
        kind: 'conditionalOp', pyModelType: 'ConditionalOp', range: ZERO, text: '',
        cond, ifTrue, if_true: ifTrue, ifFalse, if_false: ifFalse,
    };
}

function assign(name: string, expr: Expr): RawFcstmModelOperation {
    return {kind: 'operation', pyModelType: 'Operation', range: ZERO, text: '', varName: name, var_name: name, expr};
}

class HistoryLowering {
    private readonly states = new Map<string, State>();
    private readonly paths: Path[] = [];
    private readonly ids = new Map<string, number>();
    private readonly goto = HISTORY_PREFIX + GOTO_TAG;
    private readonly diagnostics: FcstmModelHistoryDiagnostic[] = [];
    // [owner path, kind] of every invalid declaration, as JSON keys.
    private readonly invalid = new Set<string>();

    constructor(private readonly input: HistoryLoweringInput) {
        walk(input.rootState).forEach((state, index) => {
            this.states.set(key(state.path), state);
            this.paths.push(state.path);
            this.ids.set(key(state.path), index + 1);
        });
    }

    private emit(
        code: string,
        severity: 'error' | 'warning',
        message: string,
        range: TextRange,
        refs: Record<string, string>,
    ): void {
        this.diagnostics.push({code, severity, message, range, refs});
    }

    private checkReservedNames(usesHistory: boolean): void {
        const seen = new Set<string>();
        const check = (identifier: string, kind: string, range: TextRange): void => {
            const seenKey = `${kind}:${identifier}`;
            if (seen.has(seenKey)) return;
            seen.add(seenKey);
            const refs = {identifier, identifier_kind: kind};
            if (usesHistory && RESERVED_IN_HISTORY_MODELS.test(identifier)) {
                this.emit(
                    'E_HISTORY_RESERVED_PREFIX',
                    'error',
                    `Identifier '${identifier}' collides with the names history lowering generates (prefix '${HISTORY_PREFIX}').`,
                    range,
                    refs,
                );
            } else if (!usesHistory && identifier.startsWith(HISTORY_PREFIX)) {
                this.emit(
                    'W_HISTORY_RESERVED_PREFIX',
                    'warning',
                    `Identifier '${identifier}' uses the prefix '${HISTORY_PREFIX}' reserved for history lowering.`,
                    range,
                    refs,
                );
            }
        };
        for (const [name, define] of Object.entries(this.input.defines)) check(name, 'variable', define.range);
        for (const state of this.states.values()) check(state.name, 'state', state.range);
        for (const state of this.states.values()) {
            for (const operation of stateOperations(state)) {
                if (!(operation.var_name in this.input.defines)) check(operation.var_name, 'temporary', operation.range);
            }
        }
    }

    private resolveDefault(owner: State, path: Path): State | undefined {
        let state: State | undefined = owner;
        for (const name of path) {
            state = state.substates[name];
            if (!state) return undefined;
        }
        return state;
    }

    private declarations(): Map<string, Map<FcstmHistoryKind, [Path, FcstmAstHistoryDefinition]>> {
        const declared = new Map<string, Map<FcstmHistoryKind, [Path, FcstmAstHistoryDefinition]>>();
        for (const [path, node] of walkAst(this.input.astRoot)) {
            for (const decl of node.histories) {
                const owner = this.states.get(key(path));
                /* c8 ignore next -- every AST state is built into the model. */
                if (!owner) continue;
                const target = this.resolveDefault(owner, decl.defaultPath);
                let reason: string | undefined;
                if (owner === this.input.rootState) reason = 'root_owner';
                else if (owner.isLeafState) reason = 'leaf_owner';
                else if (declared.get(key(path))?.has(decl.historyKind)) reason = 'duplicate';
                else if (decl.historyKind === 'shallow' && decl.defaultPath.length !== 1) reason = 'default_not_direct_child';
                else if (!target) reason = 'default_not_found';
                else if (target.isPseudo) reason = 'default_pseudo';
                if (reason) {
                    this.invalid.add(JSON.stringify([key(path), decl.historyKind]));
                    this.emit(
                        'E_HISTORY_DECLARATION_INVALID',
                        'error',
                        `Invalid history declaration in ${key(path)} (${reason}):\n`
                            + `${HISTORY_MARKERS[decl.historyKind]} -> ${decl.defaultPath.join('.')};`,
                        decl.range,
                        {
                            owner_path: key(path),
                            kind: decl.historyKind,
                            default: decl.defaultPath.join('.'),
                            reason,
                        },
                    );
                    continue;
                }
                if (!declared.has(key(path))) declared.set(key(path), new Map());
                declared.get(key(path))!.set(decl.historyKind, [[...decl.defaultPath], decl]);
            }
        }
        return declared;
    }

    private targets(
        declared: Map<string, Map<FcstmHistoryKind, [Path, FcstmAstHistoryDefinition]>>,
    ): Array<[Transition, Path, FcstmHistoryKind]> {
        const found: Array<[Transition, Path, FcstmHistoryKind]> = [];
        const reported = new Set<string>();
        for (const scope of this.states.values()) {
            for (const transition of scope.transitions) {
                const kind = transition.targetHistory;
                if (!kind) continue;
                const owner = scope.substates[transition.toState];
                // A missing target is reported as a dangling transition.
                if (!owner) continue;
                if (declared.get(key(owner.path))?.has(kind)) {
                    found.push([transition, owner.path, kind]);
                    continue;
                }
                // An invalid declaration is already reported; its targets are not undeclared.
                if (this.invalid.has(JSON.stringify([key(owner.path), kind]))) continue;
                const reportKey = JSON.stringify([owner.path, kind, transition.range]);
                if (reported.has(reportKey)) continue;
                reported.add(reportKey);
                this.emit(
                    'E_HISTORY_TARGET_UNDECLARED',
                    'error',
                    `${key(owner.path)} does not declare ${kind} history ([${kind === 'shallow' ? 'H' : 'H*'}] -> ...;), `
                        + `so it cannot be entered through ${owner.name}.${HISTORY_MARKERS[kind]}.`,
                    transition.range,
                    {owner_path: key(owner.path), kind},
                );
            }
        }
        return found;
    }

    private eq(name: string, value: number): Expr {
        return binary(variable(name), '==', integer(value));
    }

    private range(name: string, lo: number, hi: number): Expr {
        if (lo === hi) return this.eq(name, lo);
        return binary(binary(variable(name), '>=', integer(lo)), '&&', binary(variable(name), '<=', integer(hi)));
    }

    private id(path: Path): number {
        return this.ids.get(key(path))!;
    }

    private inSubtree(path: Path): Expr {
        const ids = this.paths.filter(item => isPrefix(path, item)).map(item => this.id(item));
        return this.range(this.goto, this.id(path), Math.max(...ids));
    }

    private stoppableLeaves(path: Path): Path[] {
        return this.paths.filter(item => item.length > path.length && isPrefix(path, item) && this.states.get(key(item))!.isStoppable);
    }

    private restoreTarget(owner: RawFcstmModelHistoryOwner, kind: FcstmHistoryKind): Expr {
        const record = owner.record_variable;
        const fallback = this.id([...owner.owner_path, ...owner.defaults[kind]!]);
        if (kind === 'deep') {
            return conditional(binary(variable(record), '!=', integer(0)), variable(record), integer(fallback));
        }
        let expr = integer(fallback);
        const ownerState = this.states.get(key(owner.owner_path))!;
        for (const child of Object.values(ownerState.substates).reverse()) {
            const leaves = child.isStoppable
                ? [this.id(child.path)]
                : this.stoppableLeaves(child.path).map(item => this.id(item));
            if (leaves.length > 0) {
                expr = conditional(
                    this.range(record, Math.min(...leaves), Math.max(...leaves)),
                    integer(this.id(child.path)),
                    expr,
                );
            }
        }
        return expr;
    }

    private possibleTargets(owner: RawFcstmModelHistoryOwner, kinds: Set<FcstmHistoryKind>): Path[] {
        const base = owner.owner_path;
        const found: Path[] = [...kinds].sort().map(kind => [...base, ...owner.defaults[kind]!]);
        const leaves = Object.keys(owner.leaf_ids).map(leaf => [...base, ...leaf.split('.')]);
        if (kinds.has('deep')) found.push(...leaves);
        if (kinds.has('shallow')) {
            for (const child of Object.values(this.states.get(key(base))!.substates)) {
                if (leaves.some(leaf => isPrefix(child.path, leaf))) found.push(child.path);
            }
        }
        return found;
    }

    private ownerTags(ownerPaths: Path[]): Map<string, string> {
        const tags = new Map<string, string>();
        const taken = new Set([GOTO_TAG]);
        const collapse = (text: string): string => text.replace(/_+/g, '_');
        for (const path of ownerPaths) {
            const base = path.slice(1).join('_');
            let tag = base;
            let index = 1;
            while (taken.has(collapse(tag))) {
                index += 1;
                tag = `${base}_${index}`;
            }
            taken.add(collapse(tag));
            tags.set(key(path), tag);
        }
        return tags;
    }

    private define(name: string): RawFcstmModelVarDefine {
        return {
            kind: 'varDefine', pyModelType: 'VarDefine', range: ZERO, text: `def int ${name} = 0;`,
            name, type: 'int', init: integer(0), role: 'control',
        };
    }

    private newTransition(
        parent: State,
        toState: string,
        guard: Expr,
        effects: RawFcstmModelOperationStatement[],
        role: FcstmModelHistoryRole,
        range: TextRange,
    ): Transition {
        const targetStatePath = parent.substates[toState].path;
        // A route has no source text; a gate entry stands at the evented initial it guards.
        const sourcePath = range === ZERO ? undefined : this.input.filePath;
        return {
            kind: 'transition', pyModelType: 'Transition', range, text: '',
            fromState: 'INIT_STATE', from_state: 'INIT_STATE', toState, to_state: toState,
            guard, effects,
            parentPath: parent.path, parent_path: parent.path,
            targetStatePath, target_state_path: targetStatePath,
            sourceKind: 'init', targetKind: 'state', transitionKind: 'entry', forced: false,
            declaredInStatePath: parent.path, declared_in_state_path: parent.path,
            sourcePath, source_path: sourcePath,
            combo_origin_refs: [], combo_projection_key: null, combo_projection_order_key: null,
            combo_reuse_group_id: null, combo_priority_run_identity: null, combo_priority_run_index: null,
            historyRole: role, history_role: role,
        };
    }

    private gateState(parent: State, name: string, range: TextRange): State {
        const path = [...parent.path, name];
        return {
            kind: 'state', pyModelType: 'State', range, text: `pseudo state ${name};`, name, path,
            pathName: key(path), path_name: key(path),
            substates: {}, events: {}, transitions: [], namedFunctions: {}, named_functions: {},
            onEnters: [], on_enters: [], onDurings: [], on_durings: [], onExits: [], on_exits: [],
            onDuringAspects: [], on_during_aspects: [],
            parentPath: parent.path, parent_path: parent.path,
            substateNameToId: {}, substate_name_to_id: {},
            isPseudo: true, is_pseudo: true, isLeafState: true, is_leaf_state: true,
            isRootState: false, is_root_state: false, isStoppable: false, is_stoppable: false,
            isHistoryGate: true, is_history_gate: true,
        };
    }

    private recordExit(leaf: State, ops: RawFcstmModelOperation[]): RawFcstmModelOnStage {
        const statePath = [...leaf.path, null];
        const funcName = [...leaf.path, '<unnamed>'].join('.');
        return {
            kind: 'onStage', pyModelType: 'OnStage', range: leaf.range, text: '',
            stage: 'exit', operations: ops,
            isAbstract: false, is_abstract: false, isRef: false, is_ref: false, isAspect: false, is_aspect: false,
            mode: 'operations', statePath, state_path: statePath, funcName, func_name: funcName,
            parentPath: leaf.path, parent_path: leaf.path, refResolved: false, ref_resolved: false,
        };
    }

    run(): HistoryLoweringResult {
        const astStates = walkAst(this.input.astRoot);
        const usesHistory = astStates.some(([, node]) => node.histories.length > 0)
            || [...this.states.values()].some(state => state.transitions.some(item => item.targetHistory));
        this.checkReservedNames(usesHistory);
        if (!usesHistory) return {owners: [], diagnostics: this.diagnostics};

        const declared = this.declarations();
        const targets = this.targets(declared);
        const used = new Map<string, Set<FcstmHistoryKind>>();
        for (const [, ownerPath, kind] of targets) {
            if (!used.has(key(ownerPath))) used.set(key(ownerPath), new Set());
            used.get(key(ownerPath))!.add(kind);
        }
        for (const [ownerKey, kinds] of declared) {
            for (const [kind, [, decl]] of kinds) {
                if (used.get(ownerKey)?.has(kind)) continue;
                const ownerName = ownerKey.split('.').pop();
                this.emit(
                    'W_HISTORY_UNUSED',
                    'warning',
                    `${ownerKey} declares ${kind} history, but no transition enters ${ownerName}.${HISTORY_MARKERS[kind]}.`,
                    decl.range,
                    {owner_path: ownerKey, kind},
                );
            }
        }
        if (used.size === 0) return {owners: [], diagnostics: this.diagnostics};

        const ownerPaths = this.paths.filter(path => used.has(key(path)));
        const tags = this.ownerTags(ownerPaths);
        const owners = new Map<string, RawFcstmModelHistoryOwner>();
        for (const path of ownerPaths) {
            const recordVariable = HISTORY_PREFIX + tags.get(key(path))!;
            const defaults: RawFcstmModelHistoryOwner['defaults'] = {};
            for (const [kind, [defaultPath]] of declared.get(key(path))!) defaults[kind] = defaultPath;
            const leafIds: Record<string, number> = {};
            for (const leaf of this.stoppableLeaves(path)) leafIds[key(leaf.slice(path.length))] = this.id(leaf);
            owners.set(key(path), {
                ownerPath: path, owner_path: path,
                recordVariable, record_variable: recordVariable,
                gotoVariable: this.goto, goto_variable: this.goto,
                defaults, leafIds, leaf_ids: leafIds,
            });
        }

        this.input.defines[this.goto] = this.define(this.goto);
        for (const owner of owners.values()) this.input.defines[owner.record_variable] = this.define(owner.record_variable);

        // 1. record: each stoppable leaf writes its id into every owner above it
        for (const path of this.paths) {
            const leaf = this.states.get(key(path))!;
            if (!leaf.isStoppable) continue;
            const ops = [...owners.values()]
                .filter(owner => isPrefix(owner.owner_path, path) && path.length > owner.owner_path.length)
                .map(owner => assign(owner.record_variable, integer(this.id(path))));
            if (ops.length === 0) continue;
            const action = this.recordExit(leaf, ops);
            leaf.onExits.push(action);
            this.input.allActions.push(action);
        }

        // 2. entry: the history transition computes the restore target once
        for (const [transition, ownerPath, kind] of targets) {
            transition.effects = [
                ...transition.effects,
                assign(this.goto, this.restoreTarget(owners.get(key(ownerPath))!, kind)),
            ];
        }

        // 3 + 4. routes and gates on every composite a restore passes through
        const hops = new Map<string, string[]>();
        const restoreTargets = new Map<string, Path>();
        for (const [ownerKey, owner] of owners) {
            for (const target of this.possibleTargets(owner, used.get(ownerKey)!)) {
                restoreTargets.set(key(target), target);
                for (let depth = owner.owner_path.length; depth < target.length; depth += 1) {
                    const hopKey = key(target.slice(0, depth));
                    if (!hops.has(hopKey)) hops.set(hopKey, []);
                    const bucket = hops.get(hopKey)!;
                    if (!bucket.includes(target[depth])) bucket.push(target[depth]);
                }
            }
        }
        const compositeTargets = new Set(
            [...restoreTargets.keys()].filter(targetKey => !this.states.get(targetKey)!.isLeafState),
        );

        let gateCount = 0;
        const hosts = [...new Set([...hops.keys(), ...compositeTargets])]
            .sort((left, right) => this.ids.get(left)! - this.ids.get(right)!);
        for (const compKey of hosts) {
            const comp = this.states.get(compKey)!;
            let gate = this.eq(this.goto, 0);
            if (compositeTargets.has(compKey)) gate = binary(gate, '||', this.eq(this.goto, this.id(comp.path)));
            const pending = [...(hops.get(compKey) ?? [])];
            for (const transition of comp.transitions.filter(item => item.fromState === 'INIT_STATE')) {
                const child = comp.substates[transition.toState];
                const userGuard = transition.guard;
                transition.historyUserGuard = userGuard;
                transition.history_user_guard = userGuard;
                if (!transition.event && transition.effects.length === 0 && pending.includes(transition.toState)) {
                    // Merge the user's plain initial with the route to the same child.
                    pending.splice(pending.indexOf(transition.toState), 1);
                    const allowed = userGuard ? binary(gate, '&&', userGuard) : gate;
                    transition.guard = binary(allowed, '||', this.inSubtree(child.path));
                    transition.effects = [assign(
                        this.goto,
                        child.isLeafState
                            ? integer(0)
                            : conditional(this.inSubtree(child.path), variable(this.goto), integer(0)),
                    )];
                    transition.historyRole = 'merged';
                    transition.history_role = 'merged';
                    continue;
                }
                // Clear first: when this initial itself enters a nested
                // history, its effect already sets goto for the next owner.
                transition.effects = [assign(this.goto, integer(0)), ...transition.effects];
                transition.historyRole = 'gated';
                transition.history_role = 'gated';
                if (!transition.event) {
                    transition.guard = userGuard ? binary(gate, '&&', userGuard) : gate;
                    continue;
                }
                gateCount += 1;
                const gateName = `${HISTORY_PREFIX}gate_${gateCount}`;
                const gateState = this.gateState(comp, gateName, transition.range);
                comp.substates[gateName] = gateState;
                comp.substateNameToId[gateName] = Object.keys(comp.substateNameToId).length;
                comp.substate_name_to_id = comp.substateNameToId;
                this.input.allStates.push(gateState);
                this.input.statesByPath.set(gateState.pathName, gateState);
                const entry = this.newTransition(comp, gateName, gate, [], 'gate', transition.range);
                comp.transitions[comp.transitions.indexOf(transition)] = entry;
                transition.fromState = gateName;
                transition.from_state = gateName;
                transition.sourceKind = 'state';
                transition.sourceStatePath = gateState.path;
                transition.source_state_path = gateState.path;
                transition.transitionKind = 'normal';
                const scope = transition.triggerScope === 'absolute' ? 'absolute' : 'chain';
                transition.triggerScope = scope;
                transition.trigger_scope = scope;
                comp.transitions.push(transition);
            }
            const routes = pending.map(name => {
                const child = comp.substates[name];
                return this.newTransition(
                    comp,
                    name,
                    this.inSubtree(child.path),
                    child.isLeafState ? [assign(this.goto, integer(0))] : [],
                    'route',
                    ZERO,
                );
            });
            comp.transitions.splice(0, 0, ...routes);
        }

        return {owners: [...owners.values()], diagnostics: this.diagnostics};
    }
}

/**
 * Lower every history construct of a freshly built raw machine in place.
 *
 * Adds the hidden variables to ``input.defines``, appends record writes to
 * leaf exits, extends history entries, and rewrites the initial transitions
 * of every composite a restore passes through.
 */
export function lowerHistory(input: HistoryLoweringInput): HistoryLoweringResult {
    return new HistoryLowering(input).run();
}

// Static analyses judge what the author wrote, so they read a lowered machine
// through the helpers below, exactly as pyfcstm's do.

const GENERATED_ROLES: ReadonlySet<string> = new Set(['route', 'gate']);
const REWRITTEN_ROLES: ReadonlySet<string> = new Set(['merged', 'gated']);

/** Whether history lowering generated ``transition``: a route initial or a gate entry. */
export function isHistoryGenerated(transition: ModelTransition): boolean {
    return transition.historyRole !== undefined && GENERATED_ROLES.has(transition.historyRole);
}

/** The guard the author wrote, before lowering conjoined restore conditions onto it. */
export function authoredGuard(transition: ModelTransition): ModelExpr | undefined {
    return transition.historyRole !== undefined && REWRITTEN_ROLES.has(transition.historyRole)
        ? transition.historyUserGuard
        : transition.guard;
}

/**
 * The effect statements the author wrote, without the ``__hist_goto``
 * assignments lowering adds. A transition lowering did not rewrite keeps all
 * of its effects: a model without history may still name a variable
 * ``__hist_goto``.
 */
export function authoredEffects(transition: ModelTransition): ModelOperationStatement[] {
    if (transition.historyRole === undefined && transition.targetHistory === undefined) return transition.effects;
    const goto = HISTORY_PREFIX + GOTO_TAG;
    return transition.effects.filter(statement => (statement as {varName?: string}).varName !== goto);
}

/**
 * ``[composite path, child path]`` entries history defaults add to structural
 * reachability, as dotted paths in first-use order: one per step of the default
 * path of every history kind some transition enters. A restore with a record
 * only re-enters states already reached, so only the defaults add any.
 */
export function historyDefaultEdges(machine: ModelStateMachine): Array<[string, string]> {
    const owners = new Map(machine.historyOwners.map(owner => [key(owner.ownerPath), owner]));
    const edges: Array<[string, string]> = [];
    const seen = new Set<string>();
    const visit = (scope: ModelState): void => {
        for (const transition of scope.transitions) {
            const kind = transition.targetHistory;
            if (!kind) continue;
            const owner = owners.get(key([...scope.path, transition.toState]));
            const defaultPath = owner?.defaults[kind];
            if (!owner || !defaultPath) continue;
            let path = owner.ownerPath;
            for (const name of defaultPath) {
                const child = [...path, name];
                const edgeKey = JSON.stringify([path, child]);
                if (!seen.has(edgeKey)) {
                    seen.add(edgeKey);
                    edges.push([key(path), key(child)]);
                }
                path = child;
            }
        }
        Object.values(scope.substates).forEach(visit);
    };
    visit(machine.rootState);
    return edges;
}

/**
 * Every transition with its owning state, in the order reports number them:
 * authored transitions parent-first as written, an evented initial lowering
 * moved behind a gate at the place of its gate entry, then the edges lowering
 * generated, parent-first. A machine without history keeps its plain order.
 */
export function orderedTransitions(root: ModelState): Array<[ModelState, ModelTransition]> {
    const authored: Array<[ModelState, ModelTransition]> = [];
    const generated: Array<[ModelState, ModelTransition]> = [];
    const visit = (state: ModelState): void => {
        const behindGate = new Map<string, ModelTransition>();
        for (const transition of state.transitions) {
            if (state.substates[transition.fromState]?.isHistoryGate) behindGate.set(transition.fromState, transition);
        }
        const moved = new Set(behindGate.values());
        for (const transition of state.transitions) {
            if (transition.historyRole === 'gate') {
                authored.push([state, behindGate.get(transition.toState)!]);
                generated.push([state, transition]);
            } else if (transition.historyRole === 'route') {
                generated.push([state, transition]);
            } else if (!moved.has(transition)) {
                authored.push([state, transition]);
            }
        }
        Object.values(state.substates).forEach(visit);
    };
    visit(root);
    return [...authored, ...generated];
}

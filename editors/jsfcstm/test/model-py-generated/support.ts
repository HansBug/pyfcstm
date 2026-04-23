import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir, writeFile} from '../support';

export type PyGeneratedSnapshot = Record<string, unknown>;

export interface PyGeneratedSourceFile {
    0: string;
    1: string;
}

interface PyGeneratedModelCaseBase {
    name: string;
    relativeSourcePath: string;
    expected: PyGeneratedSnapshot;
}

export interface PyGeneratedSingleFileModelCase extends PyGeneratedModelCaseBase {
    source: string;
    files?: never;
    entryFile?: never;
}

export interface PyGeneratedWorkspaceModelCase extends PyGeneratedModelCaseBase {
    source: null;
    files: PyGeneratedSourceFile[];
    entryFile: string;
}

export type PyGeneratedModelCase = PyGeneratedSingleFileModelCase | PyGeneratedWorkspaceModelCase;

function pathName(path: string[]): string {
    return path.join('.');
}

function normalizeExpr(expr: {
    pyModelType: string;
    value?: number | boolean;
    name?: string;
    op?: string;
    func?: string;
    x?: unknown;
    y?: unknown;
    cond?: unknown;
    ifTrue?: unknown;
    ifFalse?: unknown;
}): unknown {
    switch (expr.pyModelType) {
        case 'Integer':
        case 'Float':
        case 'Boolean':
            return {
                type: expr.pyModelType,
                value: expr.value,
            };
        case 'Variable':
            return {
                type: 'Variable',
                name: expr.name,
            };
        case 'UnaryOp':
            return {
                type: 'UnaryOp',
                op: expr.op,
                x: normalizeExpr(expr.x as Parameters<typeof normalizeExpr>[0]),
            };
        case 'BinaryOp':
            return {
                type: 'BinaryOp',
                op: expr.op,
                x: normalizeExpr(expr.x as Parameters<typeof normalizeExpr>[0]),
                y: normalizeExpr(expr.y as Parameters<typeof normalizeExpr>[0]),
            };
        case 'ConditionalOp':
            return {
                type: 'ConditionalOp',
                cond: normalizeExpr(expr.cond as Parameters<typeof normalizeExpr>[0]),
                if_true: normalizeExpr(expr.ifTrue as Parameters<typeof normalizeExpr>[0]),
                if_false: normalizeExpr(expr.ifFalse as Parameters<typeof normalizeExpr>[0]),
            };
        case 'UFunc':
            return {
                type: 'UFunc',
                func: expr.func,
                x: normalizeExpr(expr.x as Parameters<typeof normalizeExpr>[0]),
            };
        default:
            throw new Error(`Unsupported model expression: ${expr.pyModelType}`);
    }
}

function normalizeStatement(statement: {
    pyModelType: string;
    var_name?: string;
    expr?: Parameters<typeof normalizeExpr>[0];
    branches?: Array<{
        condition: Parameters<typeof normalizeExpr>[0] | null;
        statements: Array<Parameters<typeof normalizeStatement>[0]>;
    }>;
}): unknown {
    if (statement.pyModelType === 'Operation') {
        return {
            type: 'Operation',
            var_name: statement.var_name,
            expr: normalizeExpr(statement.expr!),
        };
    }

    if (statement.pyModelType === 'IfBlock') {
        return {
            type: 'IfBlock',
            branches: (statement.branches || []).map(branch => ({
                condition: branch.condition ? normalizeExpr(branch.condition) : null,
                statements: branch.statements.map(item => normalizeStatement(item)),
            })),
        };
    }

    throw new Error(`Unsupported model statement: ${statement.pyModelType}`);
}

function normalizeAction(action: {
    pyModelType: string;
    stage: string;
    aspect?: string;
    name?: string;
    doc?: string;
    operations: Array<Parameters<typeof normalizeStatement>[0]>;
    is_abstract: boolean;
    is_ref: boolean;
    is_aspect: boolean;
    state_path: Array<string | null>;
    func_name: string;
    parent?: {path: string[]};
    ref_state_path?: string[];
    ref_resolved: boolean;
    ref_target_qualified_name?: string;
}): unknown {
    return {
        type: action.pyModelType,
        stage: action.stage,
        aspect: action.aspect ?? null,
        name: action.name ?? null,
        doc: action.doc ?? null,
        operations: action.operations.map(operation => normalizeStatement(operation)),
        is_abstract: action.is_abstract,
        is_ref: action.is_ref,
        is_aspect: action.is_aspect,
        state_path: action.state_path,
        func_name: action.func_name,
        parent: action.parent ? pathName(action.parent.path) : null,
        ref_state_path: action.ref_state_path ?? null,
        ref_resolved: action.ref_resolved,
        ref_target_qualified_name: action.ref_target_qualified_name ?? null,
    };
}

function normalizeTransition(transition: {
    from_state: string;
    to_state: string;
    event?: {path_name: string};
    guard?: Parameters<typeof normalizeExpr>[0];
    effects: Array<Parameters<typeof normalizeStatement>[0]>;
    parent?: {path: string[]};
}): unknown {
    return {
        from_state: transition.from_state,
        to_state: transition.to_state,
        event: transition.event?.path_name ?? null,
        guard: transition.guard ? normalizeExpr(transition.guard) : null,
        effects: transition.effects.map(effect => normalizeStatement(effect)),
        parent: transition.parent ? pathName(transition.parent.path) : null,
    };
}

function normalizeEvent(event: {
    name: string;
    state_path: string[];
    path: string[];
    path_name: string;
    extra_name?: string;
}): unknown {
    return {
        name: event.name,
        state_path: event.state_path,
        path: event.path,
        path_name: event.path_name,
        extra_name: event.extra_name ?? null,
    };
}

function normalizeState(state: {
    name: string;
    path: string[];
    parent?: {path: string[]};
    substates: Record<string, unknown>;
    events: Record<string, {
        name: string;
        state_path: string[];
        path: string[];
        path_name: string;
        extra_name?: string;
    }>;
    transitions: Array<Parameters<typeof normalizeTransition>[0]>;
    named_functions: Record<string, Parameters<typeof normalizeAction>[0]>;
    on_enters: Array<Parameters<typeof normalizeAction>[0]>;
    on_durings: Array<Parameters<typeof normalizeAction>[0]>;
    on_exits: Array<Parameters<typeof normalizeAction>[0]>;
    on_during_aspects: Array<Parameters<typeof normalizeAction>[0]>;
    substate_name_to_id: Record<string, number>;
    extra_name?: string;
    is_pseudo: boolean;
    is_leaf_state: boolean;
    is_root_state: boolean;
    is_stoppable: boolean;
    abstract_on_enters: Array<{func_name: string}>;
    non_abstract_on_enters: Array<{func_name: string}>;
    abstract_on_durings: Array<{func_name: string}>;
    non_abstract_on_durings: Array<{func_name: string}>;
    abstract_on_exits: Array<{func_name: string}>;
    non_abstract_on_exits: Array<{func_name: string}>;
    abstract_on_during_aspects: Array<{func_name: string}>;
    non_abstract_on_during_aspects: Array<{func_name: string}>;
    init_transitions: Array<Parameters<typeof normalizeTransition>[0]>;
    transitions_from: Array<Parameters<typeof normalizeTransition>[0]>;
    transitions_to: Array<Parameters<typeof normalizeTransition>[0]>;
    transitions_entering_children: Array<Parameters<typeof normalizeTransition>[0]>;
    transitions_entering_children_simplified: Array<Parameters<typeof normalizeTransition>[0] | null>;
    list_on_enters(isAbstract?: boolean, withIds?: boolean): Array<{func_name: string} | [number, {func_name: string}]>;
    list_on_durings(isAbstract?: boolean, aspect?: 'before' | 'after', withIds?: boolean): Array<{func_name: string} | [number, {func_name: string}]>;
    list_on_exits(isAbstract?: boolean, withIds?: boolean): Array<{func_name: string} | [number, {func_name: string}]>;
    list_on_during_aspects(isAbstract?: boolean, aspect?: 'before' | 'after', withIds?: boolean): Array<{func_name: string} | [number, {func_name: string}]>;
    list_on_during_aspect_recursively(isAbstract?: boolean, withIds?: boolean): Array<
        [{path: string[]}, {func_name: string}] | [number, {path: string[]}, {func_name: string}]
    >;
    walk_states(): Iterable<{path: string[]}>;
}): unknown {
    const listWithIds = (
        items: Array<{func_name: string} | [number, {func_name: string}]>
    ): unknown[] => items.map(item => Array.isArray(item) ? [item[0], item[1].func_name] : item.func_name);

    const recursiveListWithIds = (
        items: Array<
            [{path: string[]}, {func_name: string}] | [number, {path: string[]}, {func_name: string}]
        >
    ): unknown[] => items.map(item => {
        if (Array.isArray(item) && typeof item[0] === 'number') {
            const tuple = item as [number, {path: string[]}, {func_name: string}];
            return [tuple[0], pathName(tuple[1].path), tuple[2].func_name];
        }
        const tuple = item as [{path: string[]}, {func_name: string}];
        return [pathName(tuple[0].path), tuple[1].func_name];
    });

    return {
        name: state.name,
        path: state.path,
        parent: state.parent ? pathName(state.parent.path) : null,
        substates: Object.keys(state.substates),
        events: Object.fromEntries(
            Object.entries(state.events)
                .sort(([left], [right]) => left.localeCompare(right))
                .map(([name, event]) => [name, normalizeEvent(event)])
        ),
        transitions: state.transitions.map(transition => normalizeTransition(transition)),
        named_functions: Object.fromEntries(
            Object.entries(state.named_functions)
                .sort(([left], [right]) => left.localeCompare(right))
                .map(([name, action]) => [name, normalizeAction(action)])
        ),
        on_enters: state.on_enters.map(action => normalizeAction(action)),
        on_durings: state.on_durings.map(action => normalizeAction(action)),
        on_exits: state.on_exits.map(action => normalizeAction(action)),
        on_during_aspects: state.on_during_aspects.map(action => normalizeAction(action)),
        substate_name_to_id: state.substate_name_to_id,
        extra_name: state.extra_name ?? null,
        is_pseudo: state.is_pseudo,
        is_leaf_state: state.is_leaf_state,
        is_root_state: state.is_root_state,
        is_stoppable: state.is_stoppable,
        abstract_on_enters: state.abstract_on_enters.map(action => action.func_name),
        non_abstract_on_enters: state.non_abstract_on_enters.map(action => action.func_name),
        abstract_on_durings: state.abstract_on_durings.map(action => action.func_name),
        non_abstract_on_durings: state.non_abstract_on_durings.map(action => action.func_name),
        abstract_on_exits: state.abstract_on_exits.map(action => action.func_name),
        non_abstract_on_exits: state.non_abstract_on_exits.map(action => action.func_name),
        abstract_on_during_aspects: state.abstract_on_during_aspects.map(action => action.func_name),
        non_abstract_on_during_aspects: state.non_abstract_on_during_aspects.map(action => action.func_name),
        init_transitions: state.init_transitions.map(transition => normalizeTransition(transition)),
        transitions_from: state.transitions_from.map(transition => normalizeTransition(transition)),
        transitions_to: state.transitions_to.map(transition => normalizeTransition(transition)),
        transitions_entering_children: state.transitions_entering_children.map(transition => normalizeTransition(transition)),
        transitions_entering_children_simplified: state.transitions_entering_children_simplified.map(
            transition => transition ? normalizeTransition(transition) : null
        ),
        list_on_enters: listWithIds(state.list_on_enters(undefined, false)),
        list_on_enters_with_ids: listWithIds(state.list_on_enters(undefined, true)),
        list_on_durings: listWithIds(state.list_on_durings(undefined, undefined, false)),
        list_on_durings_with_ids: listWithIds(state.list_on_durings(undefined, undefined, true)),
        list_on_exits: listWithIds(state.list_on_exits(undefined, false)),
        list_on_exits_with_ids: listWithIds(state.list_on_exits(undefined, true)),
        list_on_during_aspects: listWithIds(state.list_on_during_aspects(undefined, undefined, false)),
        list_on_during_aspects_with_ids: listWithIds(state.list_on_during_aspects(undefined, undefined, true)),
        list_on_during_aspect_recursively: recursiveListWithIds(
            state.list_on_during_aspect_recursively(undefined, false)
        ),
        list_on_during_aspect_recursively_with_ids: recursiveListWithIds(
            state.list_on_during_aspect_recursively(undefined, true)
        ),
        walk_states: Array.from(state.walk_states()).map(item => pathName(item.path)),
    };
}

function normalizeAstChainId(node: {
    path: string[];
    is_absolute: boolean;
}): unknown {
    return {
        __class__: 'ChainID',
        path: node.path,
        is_absolute: node.is_absolute,
    };
}

function normalizeAstExpr(expr: {
    pyNodeType: string;
    raw?: string;
    name?: string;
    expr?: unknown;
    expr1?: unknown;
    expr2?: unknown;
    cond?: unknown;
    value_true?: unknown;
    value_false?: unknown;
    func?: string;
    op?: string;
}): unknown {
    switch (expr.pyNodeType) {
        case 'Boolean':
        case 'Integer':
        case 'HexInt':
        case 'Float':
        case 'Constant':
            return {
                __class__: expr.pyNodeType,
                raw: expr.raw,
            };
        case 'Name':
            return {
                __class__: 'Name',
                name: expr.name,
            };
        case 'Paren':
            return {
                __class__: 'Paren',
                expr: normalizeAstExpr(expr.expr as Parameters<typeof normalizeAstExpr>[0]),
            };
        case 'UnaryOp':
            return {
                __class__: 'UnaryOp',
                op: expr.op,
                expr: normalizeAstExpr(expr.expr as Parameters<typeof normalizeAstExpr>[0]),
            };
        case 'BinaryOp':
            return {
                __class__: 'BinaryOp',
                expr1: normalizeAstExpr(expr.expr1 as Parameters<typeof normalizeAstExpr>[0]),
                op: expr.op,
                expr2: normalizeAstExpr(expr.expr2 as Parameters<typeof normalizeAstExpr>[0]),
            };
        case 'ConditionalOp':
            return {
                __class__: 'ConditionalOp',
                cond: normalizeAstExpr(expr.cond as Parameters<typeof normalizeAstExpr>[0]),
                value_true: normalizeAstExpr(expr.value_true as Parameters<typeof normalizeAstExpr>[0]),
                value_false: normalizeAstExpr(expr.value_false as Parameters<typeof normalizeAstExpr>[0]),
            };
        case 'UFunc':
            return {
                __class__: 'UFunc',
                func: expr.func,
                expr: normalizeAstExpr(expr.expr as Parameters<typeof normalizeAstExpr>[0]),
            };
        default:
            throw new Error(`Unsupported AST expression: ${expr.pyNodeType}`);
    }
}

function normalizeAstOperation(statement: {
    kind: string;
    name?: string;
    expr?: Parameters<typeof normalizeAstExpr>[0];
    branches?: Array<{
        condition: Parameters<typeof normalizeAstExpr>[0] | null;
        statements: Array<Parameters<typeof normalizeAstOperation>[0]>;
    }>;
}): unknown {
    if (statement.kind === 'assignmentStatement') {
        return {
            __class__: 'OperationAssignment',
            name: statement.name,
            expr: normalizeAstExpr(statement.expr!),
        };
    }

    if (statement.kind === 'ifStatement') {
        return {
            __class__: 'OperationIf',
            branches: (statement.branches || []).map(branch => ({
                __class__: 'OperationIfBranch',
                condition: branch.condition ? normalizeAstExpr(branch.condition) : null,
                statements: branch.statements.map(item => normalizeAstOperation(item)),
            })),
        };
    }

    throw new Error(`Unsupported AST operation kind: ${statement.kind}`);
}

function normalizeAstAction(action: {
    pyNodeType: string;
    name?: string;
    aspect?: string;
    doc?: string;
    mode: string;
    operations?: Array<Parameters<typeof normalizeAstOperation>[0]>;
    ref?: {path: string[]; is_absolute: boolean};
}): unknown {
    return {
        __class__: action.pyNodeType,
        name: action.name ?? null,
        aspect: action.pyNodeType.startsWith('During') ? (action.aspect ?? null) : null,
        doc: action.mode === 'abstract' ? (action.doc ?? null) : null,
        operations: action.mode === 'operations'
            ? (action.operations || []).map(operation => normalizeAstOperation(operation))
            : null,
        ref: action.mode === 'ref' && action.ref ? normalizeAstChainId(action.ref) : null,
    };
}

function normalizeAstTransition(transition: {
    from_state: string;
    to_state: string;
    event_id?: {path: string[]; is_absolute: boolean};
    condition_expr?: Parameters<typeof normalizeAstExpr>[0];
    post_operations: Array<Parameters<typeof normalizeAstOperation>[0]>;
}): unknown {
    return {
        __class__: 'TransitionDefinition',
        from_state: transition.from_state,
        to_state: transition.to_state,
        event_id: transition.event_id ? normalizeAstChainId(transition.event_id) : null,
        condition_expr: transition.condition_expr ? normalizeAstExpr(transition.condition_expr) : null,
        post_operations: transition.post_operations.map(operation => normalizeAstOperation(operation)),
    };
}

function normalizeAstState(state: {
    name: string;
    extra_name?: string;
    events: Array<{name: string; extra_name?: string}>;
    substates: Array<Parameters<typeof normalizeAstState>[0]>;
    transitions: Array<Parameters<typeof normalizeAstTransition>[0]>;
    enters: Array<Parameters<typeof normalizeAstAction>[0]>;
    durings: Array<Parameters<typeof normalizeAstAction>[0]>;
    exits: Array<Parameters<typeof normalizeAstAction>[0]>;
    during_aspects: Array<Parameters<typeof normalizeAstAction>[0]>;
    is_pseudo: boolean;
}): unknown {
    return {
        __class__: 'StateDefinition',
        name: state.name,
        extra_name: state.extra_name ?? null,
        events: state.events.map(event => ({
            __class__: 'EventDefinition',
            name: event.name,
            extra_name: event.extra_name ?? null,
        })),
        substates: state.substates.map(item => normalizeAstState(item)),
        transitions: state.transitions.map(item => normalizeAstTransition(item)),
        enters: state.enters.map(item => normalizeAstAction(item)),
        durings: state.durings.map(item => normalizeAstAction(item)),
        exits: state.exits.map(item => normalizeAstAction(item)),
        during_aspects: state.during_aspects.map(item => normalizeAstAction(item)),
        is_pseudo: state.is_pseudo,
    };
}

function normalizeAstProgram(program: {
    definitions: Array<{
        name: string;
        type: string;
        expr: Parameters<typeof normalizeAstExpr>[0];
    }>;
    root_state: Parameters<typeof normalizeAstState>[0];
}): unknown {
    return {
        __class__: 'StateMachineDSLProgram',
        definitions: program.definitions.map(definition => ({
            __class__: 'DefAssignment',
            name: definition.name,
            type: definition.type,
            expr: normalizeAstExpr(definition.expr),
        })),
        root_state: normalizeAstState(program.root_state),
    };
}

function normalizeStateMachine(stateMachine: {
    defines: Record<string, {
        name: string;
        type: string;
        init: Parameters<typeof normalizeExpr>[0];
    }>;
    rootState: {name: string};
    walk_states(): Iterable<Parameters<typeof normalizeState>[0]>;
    allEvents?: Array<Parameters<typeof normalizeEvent>[0]>;
    allActions?: Array<{func_name: string}>;
    to_ast_node(): {
        definitions: Array<{
            name: string;
            type: string;
            expr: Parameters<typeof normalizeAstExpr>[0];
        }>;
        root_state: Parameters<typeof normalizeAstState>[0];
    };
}): PyGeneratedSnapshot {
    const walkedStates = Array.from(stateMachine.walk_states());
    const allEvents = walkedStates.flatMap(state => Object.values(state.events));
    const allActions = walkedStates.flatMap(state => [
        ...state.on_enters,
        ...state.on_durings,
        ...state.on_exits,
        ...state.on_during_aspects,
    ]);
    return {
        defines: Object.fromEntries(
            Object.entries(stateMachine.defines)
                .sort(([left], [right]) => left.localeCompare(right))
                .map(([name, definition]) => [name, {
                    type: definition.type,
                    init: normalizeExpr(definition.init),
                }])
        ),
        root_state: stateMachine.rootState.name,
        walk_states: walkedStates.map(state => pathName(state.path)),
        all_events: allEvents.map(event => normalizeEvent(event)),
        all_actions: allActions.map(action => action.func_name),
        states: Object.fromEntries(
            walkedStates.map(state => [pathName(state.path), normalizeState(state)])
        ),
        ast: normalizeAstProgram(stateMachine.to_ast_node()),
    };
}

function sanitizeSlug(text: string): string {
    return text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
}

function isWorkspaceModelCase(testCase: PyGeneratedModelCase): testCase is PyGeneratedWorkspaceModelCase {
    return testCase.source === null;
}

export function runPyGeneratedModelCase(testCase: PyGeneratedModelCase): void {
    describe(`jsfcstm pyfcstm-generated model sample: ${testCase.relativeSourcePath}`, () => {
        it(`matches pyfcstm for ${testCase.name}`, async () => {
            let model: ReturnType<typeof packageModule.buildStateMachineModel> | Awaited<ReturnType<InstanceType<typeof packageModule.FcstmWorkspaceGraph>['getStateMachineModelForFile']>>;
            if (isWorkspaceModelCase(testCase)) {
                const dir = trackTempDir(`jsfcstm-py-generated-${sanitizeSlug(testCase.relativeSourcePath || testCase.name)}-`);
                for (const [relativePath, text] of testCase.files) {
                    writeFile(path.join(dir, relativePath), text);
                }

                const graph = new packageModule.FcstmWorkspaceGraph();
                model = await graph.getStateMachineModelForFile(path.join(dir, testCase.entryFile));
            } else {
                assert.equal(testCase.files, undefined);
                assert.equal(testCase.entryFile, undefined);
                const document = createDocument(
                    testCase.source,
                    `/tmp/${sanitizeSlug(testCase.relativeSourcePath || testCase.name)}.fcstm`
                );
                const ast = await packageModule.parseAstDocument(document);
                assert.ok(ast);
                model = packageModule.buildStateMachineModel(ast);
            }

            assert.ok(model);
            assert.deepEqual(normalizeStateMachine(model!), testCase.expected);
        });
    });
}

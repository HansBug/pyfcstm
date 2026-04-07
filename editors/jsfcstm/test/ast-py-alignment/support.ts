import assert from 'node:assert/strict';

import {createDocument, packageModule} from '../support';

export type PySnapshot = Record<string, unknown>;

export interface PyAlignmentCase {
    name: string;
    text: string;
    expected: PySnapshot;
}

export const INIT_STATE = 'INIT_STATE';
export const EXIT_STATE = 'EXIT_STATE';
export const ALL = 'ALL';

function withDefined(target: PySnapshot, key: string, value: unknown): void {
    if (value !== undefined) {
        target[key] = value;
    }
}

function normalizeChainId(node: packageModule.FcstmAstChainPath): PySnapshot {
    return {
        __class__: 'ChainID',
        path: node.path,
        is_absolute: node.is_absolute,
    };
}

function normalizeExpression(expr: packageModule.FcstmAstExpression): PySnapshot {
    switch (expr.pyNodeType) {
        case 'Boolean':
        case 'Integer':
        case 'HexInt':
        case 'Float':
            return {
                __class__: expr.pyNodeType,
                raw: expr.raw,
            };
        case 'Constant':
            return {
                __class__: 'Constant',
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
                expr: normalizeExpression(expr.expr),
            };
        case 'UnaryOp':
            return {
                __class__: 'UnaryOp',
                op: expr.op,
                expr: normalizeExpression(expr.expr),
            };
        case 'BinaryOp':
            return {
                __class__: 'BinaryOp',
                expr1: normalizeExpression(expr.expr1),
                op: expr.op,
                expr2: normalizeExpression(expr.expr2),
            };
        case 'ConditionalOp':
            return {
                __class__: 'ConditionalOp',
                cond: normalizeExpression(expr.cond),
                value_true: normalizeExpression(expr.value_true),
                value_false: normalizeExpression(expr.value_false),
            };
        case 'UFunc':
            return {
                __class__: 'UFunc',
                func: expr.func,
                expr: normalizeExpression(expr.expr),
            };
        default:
            throw new Error(`Unsupported expression snapshot node: ${expr.pyNodeType}`);
    }
}

function normalizeOperationStatement(
    statement: packageModule.FcstmAstOperationStatement
): PySnapshot {
    if (statement.kind === 'assignmentStatement') {
        return {
            __class__: 'OperationAssignment',
            name: statement.name,
            expr: normalizeExpression(statement.expr),
        };
    }

    if (statement.kind === 'ifStatement') {
        return {
            __class__: 'OperationIf',
            branches: statement.branches.map(branch => {
                const branchSnapshot: PySnapshot = {
                    __class__: 'OperationIfBranch',
                    statements: branch.statements.map(normalizeOperationStatement),
                };
                withDefined(
                    branchSnapshot,
                    'condition',
                    branch.condition ? normalizeExpression(branch.condition) : undefined
                );
                return branchSnapshot;
            }),
        };
    }

    throw new Error(`Unsupported operation snapshot node: ${statement.kind}`);
}

function normalizeAction(action: packageModule.FcstmAstAction): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: action.pyNodeType,
    };

    withDefined(snapshot, 'name', action.name);
    if (action.pyNodeType.startsWith('During')) {
        withDefined(snapshot, 'aspect', action.aspect);
    }
    if (action.mode === 'operations') {
        snapshot.operations = (action.operations || []).map(normalizeOperationStatement);
    }
    if (action.mode === 'abstract') {
        withDefined(snapshot, 'doc', action.doc);
    }
    if (action.mode === 'ref' && action.ref) {
        snapshot.ref = normalizeChainId(action.ref);
    }

    return snapshot;
}

function normalizeTransition(
    transition: packageModule.FcstmAstTransition | packageModule.FcstmAstForcedTransition
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: transition.pyNodeType,
        from_state: transition.from_state,
        to_state: transition.to_state,
    };

    withDefined(snapshot, 'event_id', transition.event_id ? normalizeChainId(transition.event_id) : undefined);
    withDefined(
        snapshot,
        'condition_expr',
        transition.condition_expr ? normalizeExpression(transition.condition_expr) : undefined
    );
    if (transition.kind === 'transition') {
        snapshot.post_operations = transition.post_operations.map(normalizeOperationStatement);
    }

    return snapshot;
}

function normalizeImportDefSelector(
    selector: packageModule.FcstmAstImportDefSelector
): PySnapshot {
    switch (selector.kind) {
        case 'importDefExactSelector':
            return {
                __class__: 'ImportDefExactSelector',
                name: selector.name,
            };
        case 'importDefSetSelector':
            return {
                __class__: 'ImportDefSetSelector',
                names: selector.names,
            };
        case 'importDefPatternSelector':
            return {
                __class__: 'ImportDefPatternSelector',
                pattern: selector.pattern,
            };
        case 'importDefFallbackSelector':
            return {
                __class__: 'ImportDefFallbackSelector',
            };
        default:
            throw new Error(`Unsupported import selector snapshot node: ${selector.kind}`);
    }
}

function normalizeImportMapping(
    mapping: packageModule.FcstmAstImportMapping
): PySnapshot {
    if (mapping.kind === 'importDefMapping') {
        return {
            __class__: 'ImportDefMapping',
            selector: normalizeImportDefSelector(mapping.selector),
            target_template: {
                __class__: 'ImportDefTargetTemplate',
                template: mapping.target_template.template,
            },
        };
    }

    const snapshot: PySnapshot = {
        __class__: 'ImportEventMapping',
        source_event: normalizeChainId(mapping.source_event),
        target_event: normalizeChainId(mapping.target_event),
    };
    withDefined(snapshot, 'extra_name', mapping.extra_name);
    return snapshot;
}

function normalizeState(state: packageModule.FcstmAstStateDefinition): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'StateDefinition',
        name: state.name,
        events: state.events.map(event => {
            const eventSnapshot: PySnapshot = {
                __class__: 'EventDefinition',
                name: event.name,
            };
            withDefined(eventSnapshot, 'extra_name', event.extra_name);
            return eventSnapshot;
        }),
        imports: state.imports.map(importStatement => {
            const importSnapshot: PySnapshot = {
                __class__: 'ImportStatement',
                source_path: importStatement.source_path,
                alias: importStatement.alias,
                mappings: importStatement.mappings.map(normalizeImportMapping),
            };
            withDefined(importSnapshot, 'extra_name', importStatement.extra_name);
            return importSnapshot;
        }),
        substates: state.substates.map(normalizeState),
        transitions: state.transitions.map(normalizeTransition),
        enters: state.enters.map(normalizeAction),
        durings: state.durings.map(normalizeAction),
        exits: state.exits.map(normalizeAction),
        during_aspects: state.during_aspects.map(normalizeAction),
        force_transitions: state.force_transitions.map(normalizeTransition),
        is_pseudo: state.is_pseudo,
    };
    withDefined(snapshot, 'extra_name', state.extra_name);
    return snapshot;
}

function normalizeProgram(program: packageModule.FcstmAstDocument): PySnapshot {
    return {
        __class__: 'StateMachineDSLProgram',
        definitions: program.definitions.map(definition => ({
            __class__: 'DefAssignment',
            name: definition.name,
            type: definition.type,
            expr: normalizeExpression(definition.expr),
        })),
        root_state: normalizeState(program.root_state!),
    };
}

function sanitizeSlug(text: string): string {
    return text
        .toLowerCase()
        .replace(/[^a-z0-9]+/g, '-')
        .replace(/^-+|-+$/g, '');
}

export async function assertPyAlignmentCase(testCase: PyAlignmentCase): Promise<void> {
    const document = createDocument(
        testCase.text,
        `/tmp/${sanitizeSlug(testCase.name || 'ast-py-alignment')}.fcstm`
    );
    const ast = await packageModule.parseAstDocument(document);

    assert.ok(ast);
    assert.deepEqual(normalizeProgram(ast!), testCase.expected);
}

export function runPyAlignmentCases(suiteName: string, cases: PyAlignmentCase[]): void {
    describe(suiteName, () => {
        for (const testCase of cases) {
            it(`matches pyfcstm for ${testCase.name}`, async () => {
                await assertPyAlignmentCase(testCase);
            });
        }
    });
}

export function lines(...items: string[]): string {
    return items.join('\n');
}

export function chain(path: string[], is_absolute = false): PySnapshot {
    return {
        __class__: 'ChainID',
        path,
        is_absolute,
    };
}

export function boolLiteral(raw: string): PySnapshot {
    return {
        __class__: 'Boolean',
        raw,
    };
}

export function intLiteral(raw: string): PySnapshot {
    return {
        __class__: 'Integer',
        raw,
    };
}

export function hexInt(raw: string): PySnapshot {
    return {
        __class__: 'HexInt',
        raw,
    };
}

export function floatLiteral(raw: string): PySnapshot {
    return {
        __class__: 'Float',
        raw,
    };
}

export function constant(raw: string): PySnapshot {
    return {
        __class__: 'Constant',
        raw,
    };
}

export function nameExpr(name: string): PySnapshot {
    return {
        __class__: 'Name',
        name,
    };
}

export function paren(expr: PySnapshot): PySnapshot {
    return {
        __class__: 'Paren',
        expr,
    };
}

export function unary(op: string, expr: PySnapshot): PySnapshot {
    return {
        __class__: 'UnaryOp',
        op,
        expr,
    };
}

export function binary(expr1: PySnapshot, op: string, expr2: PySnapshot): PySnapshot {
    return {
        __class__: 'BinaryOp',
        expr1,
        op,
        expr2,
    };
}

export function conditional(cond: PySnapshot, value_true: PySnapshot, value_false: PySnapshot): PySnapshot {
    return {
        __class__: 'ConditionalOp',
        cond,
        value_true,
        value_false,
    };
}

export function ufunc(func: string, expr: PySnapshot): PySnapshot {
    return {
        __class__: 'UFunc',
        func,
        expr,
    };
}

export function defAssignment(name: string, type: string, expr: PySnapshot): PySnapshot {
    return {
        __class__: 'DefAssignment',
        name,
        type,
        expr,
    };
}

export function assign(name: string, expr: PySnapshot): PySnapshot {
    return {
        __class__: 'OperationAssignment',
        name,
        expr,
    };
}

export function ifBranch(condition: PySnapshot | undefined, statements: PySnapshot[]): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'OperationIfBranch',
        statements,
    };
    withDefined(snapshot, 'condition', condition);
    return snapshot;
}

export function ifStatement(branches: PySnapshot[]): PySnapshot {
    return {
        __class__: 'OperationIf',
        branches,
    };
}

export function eventDefinition(name: string, extra_name?: string): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'EventDefinition',
        name,
    };
    withDefined(snapshot, 'extra_name', extra_name);
    return snapshot;
}

export function importDefExactSelector(name: string): PySnapshot {
    return {
        __class__: 'ImportDefExactSelector',
        name,
    };
}

export function importDefSetSelector(names: string[]): PySnapshot {
    return {
        __class__: 'ImportDefSetSelector',
        names,
    };
}

export function importDefPatternSelector(pattern: string): PySnapshot {
    return {
        __class__: 'ImportDefPatternSelector',
        pattern,
    };
}

export function importDefFallbackSelector(): PySnapshot {
    return {
        __class__: 'ImportDefFallbackSelector',
    };
}

export function importDefMapping(selector: PySnapshot, template: string): PySnapshot {
    return {
        __class__: 'ImportDefMapping',
        selector,
        target_template: {
            __class__: 'ImportDefTargetTemplate',
            template,
        },
    };
}

export function importEventMapping(
    source_event: PySnapshot,
    target_event: PySnapshot,
    extra_name?: string
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'ImportEventMapping',
        source_event,
        target_event,
    };
    withDefined(snapshot, 'extra_name', extra_name);
    return snapshot;
}

export function importStatement(
    source_path: string,
    alias: string,
    mappings: PySnapshot[] = [],
    extra_name?: string
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'ImportStatement',
        source_path,
        alias,
        mappings,
    };
    withDefined(snapshot, 'extra_name', extra_name);
    return snapshot;
}

export function transition(
    from_state: string,
    to_state: string,
    options: {
        event_id?: PySnapshot;
        condition_expr?: PySnapshot;
        post_operations?: PySnapshot[];
    } = {}
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'TransitionDefinition',
        from_state,
        to_state,
        post_operations: options.post_operations || [],
    };
    withDefined(snapshot, 'event_id', options.event_id);
    withDefined(snapshot, 'condition_expr', options.condition_expr);
    return snapshot;
}

export function forceTransition(
    from_state: string,
    to_state: string,
    options: {
        event_id?: PySnapshot;
        condition_expr?: PySnapshot;
    } = {}
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'ForceTransitionDefinition',
        from_state,
        to_state,
    };
    withDefined(snapshot, 'event_id', options.event_id);
    withDefined(snapshot, 'condition_expr', options.condition_expr);
    return snapshot;
}

function actionSnapshot(
    className: string,
    options: {
        operations?: PySnapshot[];
        name?: string;
        aspect?: string;
        doc?: string;
        ref?: PySnapshot;
    } = {}
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: className,
    };

    withDefined(snapshot, 'name', options.name);
    withDefined(snapshot, 'aspect', options.aspect);
    if (options.operations) {
        snapshot.operations = options.operations;
    }
    withDefined(snapshot, 'doc', options.doc);
    withDefined(snapshot, 'ref', options.ref);
    return snapshot;
}

export function enterOperations(operations: PySnapshot[] = [], name?: string): PySnapshot {
    return actionSnapshot('EnterOperations', {operations, name});
}

export function enterAbstract(name?: string, doc?: string): PySnapshot {
    return actionSnapshot('EnterAbstractFunction', {name, doc});
}

export function enterRef(ref: PySnapshot, name?: string): PySnapshot {
    return actionSnapshot('EnterRefFunction', {name, ref});
}

export function duringOperations(
    operations: PySnapshot[] = [],
    options: {aspect?: string; name?: string} = {}
): PySnapshot {
    return actionSnapshot('DuringOperations', {
        operations,
        aspect: options.aspect,
        name: options.name,
    });
}

export function duringAbstract(
    options: {aspect?: string; name?: string; doc?: string} = {}
): PySnapshot {
    return actionSnapshot('DuringAbstractFunction', options);
}

export function duringRef(
    ref: PySnapshot,
    options: {aspect?: string; name?: string} = {}
): PySnapshot {
    return actionSnapshot('DuringRefFunction', {
        ref,
        aspect: options.aspect,
        name: options.name,
    });
}

export function exitOperations(operations: PySnapshot[] = [], name?: string): PySnapshot {
    return actionSnapshot('ExitOperations', {operations, name});
}

export function exitAbstract(name?: string, doc?: string): PySnapshot {
    return actionSnapshot('ExitAbstractFunction', {name, doc});
}

export function exitRef(ref: PySnapshot, name?: string): PySnapshot {
    return actionSnapshot('ExitRefFunction', {name, ref});
}

export function duringAspectOperations(
    operations: PySnapshot[] = [],
    options: {aspect: string; name?: string}
): PySnapshot {
    return actionSnapshot('DuringAspectOperations', {
        operations,
        aspect: options.aspect,
        name: options.name,
    });
}

export function duringAspectAbstract(
    options: {aspect: string; name?: string; doc?: string}
): PySnapshot {
    return actionSnapshot('DuringAspectAbstractFunction', options);
}

export function duringAspectRef(
    ref: PySnapshot,
    options: {aspect: string; name?: string}
): PySnapshot {
    return actionSnapshot('DuringAspectRefFunction', {
        ref,
        aspect: options.aspect,
        name: options.name,
    });
}

export function state(
    name: string,
    options: {
        extra_name?: string;
        events?: PySnapshot[];
        imports?: PySnapshot[];
        substates?: PySnapshot[];
        transitions?: PySnapshot[];
        enters?: PySnapshot[];
        durings?: PySnapshot[];
        exits?: PySnapshot[];
        during_aspects?: PySnapshot[];
        force_transitions?: PySnapshot[];
        is_pseudo?: boolean;
    } = {}
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'StateDefinition',
        name,
        events: options.events || [],
        imports: options.imports || [],
        substates: options.substates || [],
        transitions: options.transitions || [],
        enters: options.enters || [],
        durings: options.durings || [],
        exits: options.exits || [],
        during_aspects: options.during_aspects || [],
        force_transitions: options.force_transitions || [],
        is_pseudo: options.is_pseudo || false,
    };
    withDefined(snapshot, 'extra_name', options.extra_name);
    return snapshot;
}

export function rootState(
    options: {
        extra_name?: string;
        events?: PySnapshot[];
        imports?: PySnapshot[];
        substates?: PySnapshot[];
        transitions?: PySnapshot[];
        enters?: PySnapshot[];
        durings?: PySnapshot[];
        exits?: PySnapshot[];
        during_aspects?: PySnapshot[];
        force_transitions?: PySnapshot[];
        is_pseudo?: boolean;
    } = {}
): PySnapshot {
    return state('Root', options);
}

export function program(root_state: PySnapshot, definitions: PySnapshot[] = []): PySnapshot {
    return {
        __class__: 'StateMachineDSLProgram',
        definitions,
        root_state,
    };
}

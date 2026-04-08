/**
 * Runtime model classes for jsfcstm.
 *
 * The builder first creates raw serializable objects. This module hydrates
 * those raw shapes into stable runtime classes whose property and method
 * surface intentionally follows ``pyfcstm.model`` closely enough for users who
 * already know the Python implementation.
 */
import type {
    FcstmAstAction,
    FcstmAstChainPath,
    FcstmAstDocument,
    FcstmAstEventDefinition,
    FcstmAstExpression,
    FcstmAstIfBranch,
    FcstmAstIfStatement,
    FcstmAstOperationBlock,
    FcstmAstOperationStatement,
    FcstmAstStateDefinition,
    FcstmAstTransition,
    FcstmAstVariableDefinition,
} from '../ast';
import {createRange, type TextRange} from '../utils/text';
import type {
    FcstmModelActionPath,
    RawFcstmModelBinaryOp,
    RawFcstmModelBoolean,
    RawFcstmModelConditionalOp,
    RawFcstmModelEvent,
    RawFcstmModelExpression,
    RawFcstmModelFloat,
    RawFcstmModelIfBlock,
    RawFcstmModelIfBlockBranch,
    RawFcstmModelInteger,
    RawFcstmModelLookups,
    RawFcstmModelNamedFunction,
    RawFcstmModelNodeBase,
    RawFcstmModelOnAspect,
    RawFcstmModelOnStage,
    RawFcstmModelOperation,
    RawFcstmModelOperationStatement,
    RawFcstmModelState,
    RawFcstmModelStateMachine,
    RawFcstmModelTransition,
    RawFcstmModelUFunc,
    RawFcstmModelUnaryOp,
    RawFcstmModelVarDefine,
    RawFcstmModelVariable,
} from './raw';

const ZERO_RANGE = createRange(0, 0, 0, 0);
const FLOAT_EPSILON = 1e-10;

type DuringRecursiveTuple =
    | [State, OnStage | OnAspect]
    | [number, State, OnStage | OnAspect];

function cloneRange(range: TextRange | undefined): TextRange {
    if (!range) {
        return ZERO_RANGE;
    }
    return createRange(
        range.start.line,
        range.start.character,
        range.end.line,
        range.end.character
    );
}

function actionPathName(path: FcstmModelActionPath): string {
    return path.map(segment => segment === null ? '<unnamed>' : segment).join('.');
}

function statePathName(path: string[]): string {
    return path.join('.');
}

function operationBlockText(statements: OperationStatement[]): string {
    if (statements.length === 0) {
        return '{}';
    }
    const lines = statements.map(statement => statement.text || '');
    return `{\n${lines.join('\n')}\n}`;
}

function eventPathToChainPath(
    path: string[],
    ownerPath: string[]
): FcstmAstChainPath {
    const isRelative = path.length >= ownerPath.length && ownerPath.every((item, index) => path[index] === item);
    const segments = isRelative ? path.slice(ownerPath.length) : path.slice(1);
    return {
        kind: 'chainPath',
        pyNodeType: 'ChainID',
        range: ZERO_RANGE,
        text: isRelative ? segments.join('.') : `/${segments.join('.')}`,
        isAbsolute: !isRelative,
        is_absolute: !isRelative,
        segments,
        path: segments,
    };
}

function actionRefToChainPath(
    refStatePath: string[],
    ownerPath: string[]
): FcstmAstChainPath {
    const isRelative = refStatePath.length >= ownerPath.length
        && ownerPath.every((item, index) => refStatePath[index] === item);
    const segments = isRelative ? refStatePath.slice(ownerPath.length) : refStatePath.slice(1);
    return {
        kind: 'chainPath',
        pyNodeType: 'ChainID',
        range: ZERO_RANGE,
        text: isRelative ? segments.join('.') : `/${segments.join('.')}`,
        isAbsolute: !isRelative,
        is_absolute: !isRelative,
        segments,
        path: segments,
    };
}

function actionPyNodeType(
    stage: 'enter' | 'during' | 'exit',
    mode: 'operations' | 'abstract' | 'ref',
    isAspect: boolean
): FcstmAstAction['pyNodeType'] {
    if (isAspect) {
        if (mode === 'abstract') {
            return 'DuringAspectAbstractFunction';
        }
        if (mode === 'ref') {
            return 'DuringAspectRefFunction';
        }
        return 'DuringAspectOperations';
    }

    if (stage === 'enter') {
        if (mode === 'abstract') {
            return 'EnterAbstractFunction';
        }
        if (mode === 'ref') {
            return 'EnterRefFunction';
        }
        return 'EnterOperations';
    }
    if (stage === 'exit') {
        if (mode === 'abstract') {
            return 'ExitAbstractFunction';
        }
        if (mode === 'ref') {
            return 'ExitRefFunction';
        }
        return 'ExitOperations';
    }
    if (mode === 'abstract') {
        return 'DuringAbstractFunction';
    }
    if (mode === 'ref') {
        return 'DuringRefFunction';
    }
    return 'DuringOperations';
}

/**
 * Common runtime fields shared by all model classes.
 */
export abstract class ModelNode {
    /**
     * Stable node kind used by jsfcstm.
     */
    kind: string;

    /**
     * Python-facing model type name.
     */
    pyModelType: RawFcstmModelNodeBase['pyModelType'];

    /**
     * Source range captured from the originating AST node.
     */
    range: TextRange;

    /**
     * Original source text for the node.
     */
    text: string;

    protected constructor(kind: string, pyModelType: RawFcstmModelNodeBase['pyModelType'], range: TextRange, text: string) {
        this.kind = kind;
        this.pyModelType = pyModelType;
        this.range = cloneRange(range);
        this.text = text;
    }
}

/**
 * Base class for normalized model expressions.
 */
export abstract class Expr extends ModelNode {
    /**
     * Convert the expression back into a jsfcstm AST expression node.
     */
    abstract to_ast_node(): FcstmAstExpression;
}

/**
 * Integer literal expression aligned with ``pyfcstm.model.expr.Integer``.
 */
export class Integer extends Expr {
    value: number;

    constructor(raw: RawFcstmModelInteger) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.value = raw.value;
    }

    /**
     * Convert the expression back into an AST integer literal.
     */
    to_ast_node(): FcstmAstExpression {
        const rawValue = String(Math.trunc(this.value));
        return {
            kind: 'expression',
            pyNodeType: 'Integer',
            range: cloneRange(this.range),
            text: rawValue,
            expressionKind: 'literal',
            expressionType: 'num',
            literalType: 'number',
            valueText: rawValue,
            raw: rawValue,
        };
    }
}

/**
 * Floating-point expression aligned with ``pyfcstm.model.expr.Float``.
 */
export class Float extends Expr {
    value: number;

    constructor(raw: RawFcstmModelFloat) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.value = raw.value;
    }

    /**
     * Convert the expression back into a float or recognized constant AST node.
     */
    to_ast_node(): FcstmAstExpression {
        let rawValue: string | null = null;
        let pyNodeType: FcstmAstExpression['pyNodeType'] = 'Float';
        let expressionKind: FcstmAstExpression['expressionKind'] = 'literal';

        if (Math.abs(this.value - Math.PI) < FLOAT_EPSILON) {
            rawValue = 'pi';
            pyNodeType = 'Constant';
            expressionKind = 'mathConst';
        } else if (Math.abs(this.value - Math.E) < FLOAT_EPSILON) {
            rawValue = 'E';
            pyNodeType = 'Constant';
            expressionKind = 'mathConst';
        } else if (Math.abs(this.value - Math.PI * 2) < FLOAT_EPSILON) {
            rawValue = 'tau';
            pyNodeType = 'Constant';
            expressionKind = 'mathConst';
        } else {
            rawValue = String(this.value);
        }

        if (expressionKind === 'mathConst') {
            return {
                kind: 'expression',
                pyNodeType: pyNodeType as 'Constant',
                range: cloneRange(this.range),
                text: rawValue,
                expressionKind: 'mathConst',
                expressionType: 'num',
                name: rawValue,
                raw: rawValue,
            };
        }

        return {
            kind: 'expression',
            pyNodeType: 'Float',
            range: cloneRange(this.range),
            text: rawValue,
            expressionKind: 'literal',
            expressionType: 'num',
            literalType: 'number',
            valueText: rawValue,
            raw: rawValue,
        };
    }
}

/**
 * Boolean literal expression aligned with ``pyfcstm.model.expr.Boolean``.
 */
export class BooleanExpr extends Expr {
    value: boolean;

    constructor(raw: RawFcstmModelBoolean) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.value = Boolean(raw.value);
    }

    /**
     * Convert the expression back into a boolean AST node.
     */
    to_ast_node(): FcstmAstExpression {
        const rawValue = this.value ? 'true' : 'false';
        return {
            kind: 'expression',
            pyNodeType: 'Boolean',
            range: cloneRange(this.range),
            text: rawValue,
            expressionKind: 'literal',
            expressionType: 'cond',
            literalType: 'boolean',
            valueText: rawValue,
            raw: rawValue,
        };
    }
}

/**
 * Variable reference expression aligned with ``pyfcstm.model.expr.Variable``.
 */
export class Variable extends Expr {
    name: string;

    constructor(raw: RawFcstmModelVariable) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.name = raw.name;
    }

    /**
     * Convert the variable reference back into an AST identifier node.
     */
    to_ast_node(): FcstmAstExpression {
        return {
            kind: 'expression',
            pyNodeType: 'Name',
            range: cloneRange(this.range),
            text: this.name,
            expressionKind: 'identifier',
            expressionType: 'num',
            name: this.name,
        };
    }
}

/**
 * Unary operator expression aligned with ``pyfcstm.model.expr.UnaryOp``.
 */
export class UnaryOp extends Expr {
    op: string;
    x: Expr;

    constructor(raw: RawFcstmModelUnaryOp, x: Expr) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.op = raw.op;
        this.x = x;
    }

    /**
     * Convert the unary expression back into an AST node.
     */
    to_ast_node(): FcstmAstExpression {
        const expr = this.x.to_ast_node();
        return {
            kind: 'expression',
            pyNodeType: 'UnaryOp',
            range: cloneRange(this.range),
            text: this.text,
            expressionKind: 'unary',
            expressionType: 'num',
            operator: this.op,
            op: this.op,
            operand: expr,
            expr,
        };
    }
}

/**
 * Binary operator expression aligned with ``pyfcstm.model.expr.BinaryOp``.
 */
export class BinaryOp extends Expr {
    x: Expr;
    op: string;
    y: Expr;

    constructor(raw: RawFcstmModelBinaryOp, x: Expr, y: Expr) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.x = x;
        this.op = raw.op;
        this.y = y;
    }

    /**
     * Convert the binary expression back into an AST node.
     */
    to_ast_node(): FcstmAstExpression {
        const left = this.x.to_ast_node();
        const right = this.y.to_ast_node();
        return {
            kind: 'expression',
            pyNodeType: 'BinaryOp',
            range: cloneRange(this.range),
            text: this.text,
            expressionKind: 'binary',
            expressionType: 'num',
            operator: this.op,
            op: this.op,
            left,
            expr1: left,
            right,
            expr2: right,
        };
    }
}

/**
 * Conditional expression aligned with ``pyfcstm.model.expr.ConditionalOp``.
 */
export class ConditionalOp extends Expr {
    cond: Expr;
    ifTrue: Expr;
    if_true: Expr;
    ifFalse: Expr;
    if_false: Expr;

    constructor(raw: RawFcstmModelConditionalOp, cond: Expr, ifTrue: Expr, ifFalse: Expr) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.cond = cond;
        this.ifTrue = ifTrue;
        this.if_true = ifTrue;
        this.ifFalse = ifFalse;
        this.if_false = ifFalse;
    }

    /**
     * Convert the conditional expression back into an AST node.
     */
    to_ast_node(): FcstmAstExpression {
        const cond = this.cond.to_ast_node();
        const whenTrue = this.ifTrue.to_ast_node();
        const whenFalse = this.ifFalse.to_ast_node();
        return {
            kind: 'expression',
            pyNodeType: 'ConditionalOp',
            range: cloneRange(this.range),
            text: this.text,
            expressionKind: 'conditional',
            expressionType: 'num',
            condition: cond,
            cond,
            whenTrue,
            valueTrue: whenTrue,
            value_true: whenTrue,
            whenFalse,
            valueFalse: whenFalse,
            value_false: whenFalse,
        };
    }
}

/**
 * Unary math-function call aligned with ``pyfcstm.model.expr.UFunc``.
 */
export class UFunc extends Expr {
    func: string;
    x: Expr;

    constructor(raw: RawFcstmModelUFunc, x: Expr) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.func = raw.func;
        this.x = x;
    }

    /**
     * Convert the function call back into an AST node.
     */
    to_ast_node(): FcstmAstExpression {
        const argument = this.x.to_ast_node();
        return {
            kind: 'expression',
            pyNodeType: 'UFunc',
            range: cloneRange(this.range),
            text: this.text,
            expressionKind: 'function',
            expressionType: 'num',
            functionName: this.func,
            func: this.func,
            argument,
            expr: argument,
        };
    }
}

/**
 * Base class for executable model statements.
 */
export abstract class OperationStatement extends ModelNode {
    /**
     * Convert the statement back into a jsfcstm AST operation node.
     */
    abstract to_ast_node(): FcstmAstOperationStatement;
}

/**
 * Assignment statement aligned with ``pyfcstm.model.model.Operation``.
 */
export class Operation extends OperationStatement {
    varName: string;
    var_name: string;
    expr: Expr;

    constructor(raw: RawFcstmModelOperation, expr: Expr) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.varName = raw.varName;
        this.var_name = raw.var_name;
        this.expr = expr;
    }

    /**
     * Convert the assignment back into an AST statement.
     */
    to_ast_node(): FcstmAstOperationStatement {
        const expr = this.expr.to_ast_node();
        return {
            kind: 'assignmentStatement',
            pyNodeType: 'OperationAssignment',
            range: cloneRange(this.range),
            text: this.text,
            targetName: this.varName,
            name: this.varName,
            expression: expr,
            expr,
        };
    }
}

/**
 * Single branch inside a normalized ``if`` block.
 */
export class IfBlockBranch extends ModelNode {
    condition: Expr | null;
    statements: OperationStatement[];

    constructor(raw: RawFcstmModelIfBlockBranch, condition: Expr | null, statements: OperationStatement[]) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.condition = condition;
        this.statements = statements;
    }

    /**
     * Convert the branch back into an AST branch node.
     */
    to_ast_node(): FcstmAstIfBranch {
        return {
            kind: 'ifBranch',
            pyNodeType: 'OperationIfBranch',
            range: cloneRange(this.range),
            text: this.text,
            condition: this.condition ? this.condition.to_ast_node() : null,
            statements: this.statements.map(statement => statement.to_ast_node()),
            block: {
                kind: 'operationBlock',
                range: cloneRange(this.range),
                text: operationBlockText(this.statements),
                statements: this.statements.map(statement => statement.to_ast_node()),
            },
        };
    }
}

/**
 * Normalized ``if / else if / else`` block.
 */
export class IfBlock extends OperationStatement {
    branches: IfBlockBranch[];

    constructor(raw: RawFcstmModelIfBlock, branches: IfBlockBranch[]) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.branches = branches;
    }

    /**
     * Convert the if-block back into an AST statement.
     */
    to_ast_node(): FcstmAstOperationStatement {
        return {
            kind: 'ifStatement',
            pyNodeType: 'OperationIf',
            range: cloneRange(this.range),
            text: this.text,
            branches: this.branches.map(branch => branch.to_ast_node()),
        } as FcstmAstIfStatement;
    }
}

/**
 * Variable definition aligned with ``pyfcstm.model.model.VarDefine``.
 */
export class VarDefine extends ModelNode {
    name: string;
    type: 'int' | 'float';
    init: Expr;

    constructor(raw: RawFcstmModelVarDefine, init: Expr) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.name = raw.name;
        this.type = raw.type;
        this.init = init;
    }

    /**
     * Convert the variable definition back into an AST node.
     */
    to_ast_node(): FcstmAstVariableDefinition {
        const expr = this.init.to_ast_node();
        return {
            kind: 'variableDefinition',
            pyNodeType: 'DefAssignment',
            range: cloneRange(this.range),
            text: this.text,
            name: this.name,
            type: this.type,
            valueType: this.type,
            deftype: this.type,
            initializer: expr,
            expr,
        };
    }
}

/**
 * Event definition aligned with ``pyfcstm.model.model.Event``.
 */
export class Event extends ModelNode {
    name: string;
    statePath: string[];
    state_path: string[];
    path: string[];
    pathName: string;
    path_name: string;
    extraName?: string;
    extra_name?: string;
    declared: boolean;
    origins: Array<'declared' | 'local' | 'chain' | 'absolute'>;

    constructor(raw: RawFcstmModelEvent) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.name = raw.name;
        this.statePath = [...raw.statePath];
        this.state_path = this.statePath;
        this.path = [...raw.path];
        this.pathName = raw.pathName;
        this.path_name = raw.path_name;
        this.extraName = raw.extraName;
        this.extra_name = raw.extra_name;
        this.declared = raw.declared;
        this.origins = [...raw.origins];
    }

    /**
     * Convert the event back into an AST event definition node.
     */
    to_ast_node(): FcstmAstEventDefinition {
        return {
            kind: 'eventDefinition',
            pyNodeType: 'EventDefinition',
            range: cloneRange(this.range),
            text: this.text || this.name,
            name: this.name,
            displayName: this.extraName,
            extraName: this.extraName,
            extra_name: this.extra_name,
        };
    }
}

/**
 * Shared lifecycle-action runtime behavior.
 */
abstract class LifecycleActionBase extends ModelNode {
    stage: 'enter' | 'during' | 'exit';
    aspect?: 'before' | 'after';
    name?: string;
    doc?: string;
    operations: OperationStatement[];
    isAbstract: boolean;
    is_abstract: boolean;
    isRef: boolean;
    is_ref: boolean;
    isAspect: boolean;
    is_aspect: boolean;
    mode: 'operations' | 'abstract' | 'ref';
    statePath: FcstmModelActionPath;
    state_path: FcstmModelActionPath;
    funcName: string;
    func_name: string;
    parentPath: string[];
    parent_path: string[];
    refStatePath?: string[];
    ref_state_path?: string[];
    refResolved: boolean;
    ref_resolved: boolean;
    refTargetQualifiedName?: string;
    ref_target_qualified_name?: string;
    ref?: OnStage | OnAspect;
    protected parentState?: State;

    protected constructor(raw: RawFcstmModelOnStage | RawFcstmModelOnAspect, operations: OperationStatement[]) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.stage = raw.stage;
        this.aspect = raw.aspect;
        this.name = raw.name;
        this.doc = raw.doc;
        this.operations = operations;
        this.isAbstract = raw.isAbstract;
        this.is_abstract = raw.is_abstract;
        this.isRef = raw.isRef;
        this.is_ref = raw.is_ref;
        this.isAspect = raw.isAspect;
        this.is_aspect = raw.is_aspect;
        this.mode = raw.mode;
        this.statePath = [...raw.statePath];
        this.state_path = this.statePath;
        this.funcName = raw.funcName;
        this.func_name = raw.func_name;
        this.parentPath = [...raw.parentPath];
        this.parent_path = this.parentPath;
        this.refStatePath = raw.refStatePath ? [...raw.refStatePath] : undefined;
        this.ref_state_path = this.refStatePath;
        this.refResolved = raw.refResolved;
        this.ref_resolved = raw.ref_resolved;
        this.refTargetQualifiedName = raw.refTargetQualifiedName;
        this.ref_target_qualified_name = raw.ref_target_qualified_name;
    }

    /**
     * Owning state of the lifecycle action.
     */
    get parent(): State | undefined {
        return this.parentState;
    }

    set parent(newParent: State | undefined) {
        this.parentState = newParent;
    }

    protected createOperationBlock(): FcstmAstOperationBlock | undefined {
        if (this.mode !== 'operations') {
            return undefined;
        }
        return {
            kind: 'operationBlock',
            range: cloneRange(this.range),
            text: operationBlockText(this.operations),
            statements: this.operations.map(operation => operation.to_ast_node()),
        };
    }

    protected toActionAst(isAspect: boolean): FcstmAstAction {
        const operations = this.operations.map(operation => operation.to_ast_node());
        const operationBlock = this.createOperationBlock();
        const refPath = this.refStatePath
            ? actionRefToChainPath(this.refStatePath, this.statePath.slice(0, -1).filter((item): item is string => item !== null))
            : undefined;
        return {
            kind: 'action',
            pyNodeType: actionPyNodeType(this.stage, this.mode, isAspect),
            range: cloneRange(this.range),
            text: this.text,
            stage: this.stage,
            aspect: this.aspect,
            isGlobalAspect: isAspect,
            mode: this.mode,
            name: this.name,
            operationBlock,
            operation_block: operationBlock,
            operations,
            operationsList: operations,
            refPath,
            ref: refPath,
            doc: this.doc,
        };
    }

    /**
     * Convert the lifecycle action back into an AST action node.
     */
    abstract to_ast_node(): FcstmAstAction;
}

/**
 * Enter/during/exit action aligned with ``pyfcstm.model.model.OnStage``.
 */
export class OnStage extends LifecycleActionBase {
    constructor(raw: RawFcstmModelOnStage, operations: OperationStatement[]) {
        super(raw, operations);
    }

    /**
     * Convert the action back into an AST node.
     */
    to_ast_node(): FcstmAstAction {
        return this.toActionAst(false);
    }
}

/**
 * Aspect during-action aligned with ``pyfcstm.model.model.OnAspect``.
 */
export class OnAspect extends LifecycleActionBase {
    stage: 'during';
    isAspect: true;
    is_aspect: true;

    constructor(raw: RawFcstmModelOnAspect, operations: OperationStatement[]) {
        super(raw, operations);
        this.stage = 'during';
        this.isAspect = true;
        this.is_aspect = true;
    }

    /**
     * Convert the aspect action back into an AST node.
     */
    to_ast_node(): FcstmAstAction {
        return this.toActionAst(true);
    }
}

/**
 * Transition aligned with ``pyfcstm.model.model.Transition``.
 */
export class Transition extends ModelNode {
    fromState: string | 'INIT_STATE';
    from_state: string | 'INIT_STATE';
    toState: string | 'EXIT_STATE';
    to_state: string | 'EXIT_STATE';
    event?: Event;
    guard?: Expr;
    effects: OperationStatement[];
    parentPath: string[];
    parent_path: string[];
    sourceStatePath?: string[];
    source_state_path?: string[];
    targetStatePath?: string[];
    target_state_path?: string[];
    sourceKind: 'init' | 'state';
    targetKind: 'state' | 'exit';
    transitionKind: 'entry' | 'normal' | 'exit' | 'normalAll' | 'exitAll';
    forced: boolean;
    declaredInStatePath: string[];
    declared_in_state_path: string[];
    triggerScope?: 'local' | 'chain' | 'absolute';
    trigger_scope?: 'local' | 'chain' | 'absolute';
    protected parentState?: State;

    constructor(raw: RawFcstmModelTransition, event: Event | undefined, guard: Expr | undefined, effects: OperationStatement[]) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.fromState = raw.fromState;
        this.from_state = raw.from_state;
        this.toState = raw.toState;
        this.to_state = raw.to_state;
        this.event = event;
        this.guard = guard;
        this.effects = effects;
        this.parentPath = [...raw.parentPath];
        this.parent_path = this.parentPath;
        this.sourceStatePath = raw.sourceStatePath ? [...raw.sourceStatePath] : undefined;
        this.source_state_path = this.sourceStatePath;
        this.targetStatePath = raw.targetStatePath ? [...raw.targetStatePath] : undefined;
        this.target_state_path = this.targetStatePath;
        this.sourceKind = raw.sourceKind;
        this.targetKind = raw.targetKind;
        this.transitionKind = raw.transitionKind;
        this.forced = raw.forced;
        this.declaredInStatePath = [...raw.declaredInStatePath];
        this.declared_in_state_path = this.declaredInStatePath;
        this.triggerScope = raw.triggerScope;
        this.trigger_scope = raw.trigger_scope;
    }

    /**
     * Owning state of the transition.
     */
    get parent(): State | undefined {
        return this.parentState;
    }

    set parent(newParent: State | undefined) {
        this.parentState = newParent;
    }

    /**
     * Convert the transition back into a jsfcstm AST transition node.
     */
    to_ast_node(): FcstmAstTransition {
        return State.transition_to_ast_node(this.parent, this);
    }
}

/**
 * Hierarchical state aligned with ``pyfcstm.model.model.State``.
 */
export class State extends ModelNode {
    name: string;
    path: string[];
    pathName: string;
    path_name: string;
    substates: Record<string, State>;
    events: Record<string, Event>;
    transitions: Transition[];
    namedFunctions: Record<string, OnStage | OnAspect>;
    named_functions: Record<string, OnStage | OnAspect>;
    onEnters: OnStage[];
    on_enters: OnStage[];
    onDurings: OnStage[];
    on_durings: OnStage[];
    onExits: OnStage[];
    on_exits: OnStage[];
    onDuringAspects: OnAspect[];
    on_during_aspects: OnAspect[];
    parentPath?: string[];
    parent_path?: string[];
    substateNameToId: Record<string, number>;
    substate_name_to_id: Record<string, number>;
    extraName?: string;
    extra_name?: string;
    isPseudo: boolean;
    is_pseudo: boolean;
    isLeafState: boolean;
    isRootState: boolean;
    isStoppable: boolean;
    protected parentState?: State;

    constructor(raw: RawFcstmModelState) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.name = raw.name;
        this.path = [...raw.path];
        this.pathName = raw.pathName;
        this.path_name = raw.path_name;
        this.substates = {};
        this.events = {};
        this.transitions = [];
        this.namedFunctions = {};
        this.named_functions = this.namedFunctions;
        this.onEnters = [];
        this.on_enters = this.onEnters;
        this.onDurings = [];
        this.on_durings = this.onDurings;
        this.onExits = [];
        this.on_exits = this.onExits;
        this.onDuringAspects = [];
        this.on_during_aspects = this.onDuringAspects;
        this.parentPath = raw.parentPath ? [...raw.parentPath] : undefined;
        this.parent_path = this.parentPath;
        this.substateNameToId = {...raw.substateNameToId};
        this.substate_name_to_id = this.substateNameToId;
        this.extraName = raw.extraName;
        this.extra_name = raw.extra_name;
        this.isPseudo = raw.isPseudo;
        this.is_pseudo = raw.is_pseudo;
        this.isLeafState = raw.isLeafState;
        this.isRootState = raw.isRootState;
        this.isStoppable = raw.isStoppable;
    }

    /**
     * Parent state, or ``undefined`` for the root state.
     */
    get parent(): State | undefined {
        return this.parentState;
    }

    set parent(newParent: State | undefined) {
        this.parentState = newParent;
        this.isRootState = newParent === undefined;
        this.isStoppable = this.isLeafState && !this.isPseudo;
    }

    /**
     * Stable computed leaf-state flag aligned with the Python property.
     */
    get is_leaf_state(): boolean {
        return this.isLeafState;
    }

    /**
     * Stable computed root-state flag aligned with the Python property.
     */
    get is_root_state(): boolean {
        return this.isRootState;
    }

    /**
     * Stable computed stoppable-state flag aligned with the Python property.
     */
    get is_stoppable(): boolean {
        return this.isStoppable;
    }

    /**
     * Initial transitions that enter this state's children.
     */
    get init_transitions(): Transition[] {
        return this.transitions.filter(transition => transition.fromState === 'INIT_STATE');
    }

    /**
     * Transitions leaving this state in the parent scope.
     */
    get transitions_from(): Transition[] {
        if (this.parent) {
            return this.parent.transitions.filter(transition => transition.fromState === this.name);
        }
        return [new Transition({
            kind: 'transition',
            pyModelType: 'Transition',
            range: ZERO_RANGE,
            text: '',
            fromState: this.name,
            from_state: this.name,
            toState: 'EXIT_STATE',
            to_state: 'EXIT_STATE',
            effects: [],
            parentPath: [],
            parent_path: [],
            sourceKind: 'state',
            targetKind: 'exit',
            transitionKind: 'exit',
            forced: false,
            declaredInStatePath: this.path,
            declared_in_state_path: this.path,
        }, undefined, undefined, [])];
    }

    /**
     * Transitions entering this state in the parent scope.
     */
    get transitions_to(): Transition[] {
        if (this.parent) {
            return this.parent.transitions.filter(transition => transition.toState === this.name);
        }
        return [new Transition({
            kind: 'transition',
            pyModelType: 'Transition',
            range: ZERO_RANGE,
            text: '',
            fromState: 'INIT_STATE',
            from_state: 'INIT_STATE',
            toState: this.name,
            to_state: this.name,
            effects: [],
            parentPath: [],
            parent_path: [],
            sourceKind: 'init',
            targetKind: 'state',
            transitionKind: 'entry',
            forced: false,
            declaredInStatePath: this.path,
            declared_in_state_path: this.path,
        }, undefined, undefined, [])];
    }

    /**
     * Transitions whose source is ``INIT_STATE`` inside this state.
     */
    get transitions_entering_children(): Transition[] {
        return this.transitions.filter(transition => transition.fromState === 'INIT_STATE');
    }

    /**
     * Simplified child-entry transition list aligned with pyfcstm behavior.
     */
    get transitions_entering_children_simplified(): Array<Transition | null> {
        const transitions: Array<Transition | null> = [];
        for (const transition of this.transitions) {
            if (transition.fromState === 'INIT_STATE') {
                transitions.push(transition);
                if (!transition.event && !transition.guard) {
                    break;
                }
            }
        }
        if (
            transitions.length === 0
            || (transitions[transitions.length - 1] instanceof Transition
                && ((transitions[transitions.length - 1] as Transition).event
                    || (transitions[transitions.length - 1] as Transition).guard))
        ) {
            transitions.push(null);
        }
        return transitions;
    }

    /**
     * List enter actions with optional abstract filtering and 1-based ids.
     */
    list_on_enters(isAbstract?: boolean, withIds = false): Array<OnStage | [number, OnStage]> {
        return this.filterActions(this.onEnters, isAbstract, undefined, withIds);
    }

    /**
     * Abstract enter actions.
     */
    get abstract_on_enters(): OnStage[] {
        return this.list_on_enters(true, false) as OnStage[];
    }

    /**
     * Non-abstract enter actions.
     */
    get non_abstract_on_enters(): OnStage[] {
        return this.list_on_enters(false, false) as OnStage[];
    }

    /**
     * List during actions with optional abstract/aspect filtering.
     */
    list_on_durings(isAbstract?: boolean, aspect?: 'before' | 'after', withIds = false): Array<OnStage | [number, OnStage]> {
        return this.filterActions(this.onDurings, isAbstract, aspect, withIds);
    }

    /**
     * Abstract during actions.
     */
    get abstract_on_durings(): OnStage[] {
        return this.list_on_durings(true, undefined, false) as OnStage[];
    }

    /**
     * Non-abstract during actions.
     */
    get non_abstract_on_durings(): OnStage[] {
        return this.list_on_durings(false, undefined, false) as OnStage[];
    }

    /**
     * List exit actions with optional abstract filtering and 1-based ids.
     */
    list_on_exits(isAbstract?: boolean, withIds = false): Array<OnStage | [number, OnStage]> {
        return this.filterActions(this.onExits, isAbstract, undefined, withIds);
    }

    /**
     * Abstract exit actions.
     */
    get abstract_on_exits(): OnStage[] {
        return this.list_on_exits(true, false) as OnStage[];
    }

    /**
     * Non-abstract exit actions.
     */
    get non_abstract_on_exits(): OnStage[] {
        return this.list_on_exits(false, false) as OnStage[];
    }

    /**
     * List during-aspect actions with optional abstract/aspect filtering.
     */
    list_on_during_aspects(isAbstract?: boolean, aspect?: 'before' | 'after', withIds = false): Array<OnAspect | [number, OnAspect]> {
        return this.filterActions(this.onDuringAspects, isAbstract, aspect, withIds);
    }

    /**
     * Abstract during-aspect actions.
     */
    get abstract_on_during_aspects(): OnAspect[] {
        return this.list_on_during_aspects(true, undefined, false) as OnAspect[];
    }

    /**
     * Non-abstract during-aspect actions.
     */
    get non_abstract_on_during_aspects(): OnAspect[] {
        return this.list_on_during_aspects(false, undefined, false) as OnAspect[];
    }

    /**
     * Yield ``before`` aspect actions from root to the current state.
     */
    *iter_on_during_before_aspect_recursively(isAbstract?: boolean, withIds = false): Generator<DuringRecursiveTuple, void, void> {
        if (this.parent) {
            yield* this.parent.iter_on_during_before_aspect_recursively(isAbstract, withIds);
        }
        const items = this.list_on_during_aspects(isAbstract, 'before', withIds);
        for (const item of items) {
            if (withIds) {
                const [id, action] = item as [number, OnAspect];
                yield [id, this, action];
            } else {
                yield [this, item as OnAspect];
            }
        }
    }

    /**
     * Yield ``after`` aspect actions from the current state back to the root.
     */
    *iter_on_during_after_aspect_recursively(isAbstract?: boolean, withIds = false): Generator<DuringRecursiveTuple, void, void> {
        const items = this.list_on_during_aspects(isAbstract, 'after', withIds);
        for (const item of items) {
            if (withIds) {
                const [id, action] = item as [number, OnAspect];
                yield [id, this, action];
            } else {
                yield [this, item as OnAspect];
            }
        }
        if (this.parent) {
            yield* this.parent.iter_on_during_after_aspect_recursively(isAbstract, withIds);
        }
    }

    /**
     * Yield all during actions in pyfcstm execution order.
     */
    *iter_on_during_aspect_recursively(isAbstract?: boolean, withIds = false): Generator<DuringRecursiveTuple, void, void> {
        if (!this.is_pseudo) {
            yield* this.iter_on_during_before_aspect_recursively(isAbstract, withIds);
        }
        const durings = this.list_on_durings(isAbstract, undefined, withIds);
        for (const item of durings) {
            if (withIds) {
                const [id, action] = item as [number, OnStage];
                yield [id, this, action];
            } else {
                yield [this, item as OnStage];
            }
        }
        if (!this.is_pseudo) {
            yield* this.iter_on_during_after_aspect_recursively(isAbstract, withIds);
        }
    }

    /**
     * Collect all recursively effective during actions in execution order.
     */
    list_on_during_aspect_recursively(isAbstract?: boolean, withIds = false): DuringRecursiveTuple[] {
        return Array.from(this.iter_on_during_aspect_recursively(isAbstract, withIds));
    }

    private filterActions<T extends OnStage | OnAspect>(
        actions: T[],
        isAbstract?: boolean,
        aspect?: 'before' | 'after',
        withIds = false
    ): Array<T | [number, T]> {
        const result: Array<T | [number, T]> = [];
        actions.forEach((action, index) => {
            if (isAbstract !== undefined && action.is_abstract !== isAbstract) {
                return;
            }
            if (aspect !== undefined && action.aspect !== aspect) {
                return;
            }
            if (withIds) {
                result.push([index + 1, action]);
            } else {
                result.push(action);
            }
        });
        return result;
    }

    /**
     * Convert a transition into an AST transition node in this state's scope.
     */
    static transition_to_ast_node(owner: State | undefined, transition: Transition): FcstmAstTransition {
        const currentPath = owner?.path || [];
        const eventId = transition.event
            ? eventPathToChainPath(transition.event.path, currentPath)
            : undefined;
        const guard = transition.guard?.to_ast_node();
        const postOperations = transition.effects.map(effect => effect.to_ast_node());
        return {
            kind: 'transition',
            pyNodeType: 'TransitionDefinition',
            range: cloneRange(transition.range),
            text: transition.text,
            sourceStateName: transition.fromState === 'INIT_STATE' ? undefined : transition.fromState,
            targetStateName: transition.toState === 'EXIT_STATE' ? undefined : transition.toState,
            sourceKind: transition.fromState === 'INIT_STATE' ? 'init' : 'state',
            targetKind: transition.toState === 'EXIT_STATE' ? 'exit' : 'state',
            trigger: eventId ? {
                kind: 'chainTrigger',
                range: cloneRange(eventId.range),
                text: eventId.text,
                eventPath: eventId,
            } : undefined,
            guard,
            effect: postOperations.length > 0 ? {
                kind: 'operationBlock',
                range: cloneRange(transition.range),
                text: operationBlockText(transition.effects),
                statements: postOperations,
            } : undefined,
            fromState: transition.fromState,
            from_state: transition.from_state,
            toState: transition.toState,
            to_state: transition.to_state,
            eventId,
            event_id: eventId,
            conditionExpr: guard,
            condition_expr: guard,
            postOperations,
            post_operations: postOperations,
            transitionKind: transition.transitionKind === 'entry' || transition.transitionKind === 'normal' || transition.transitionKind === 'exit'
                ? transition.transitionKind
                : 'normal',
        };
    }

    /**
     * Convert a transition into an AST transition node in this state's scope.
     */
    to_transition_ast_node(transition: Transition): FcstmAstTransition {
        return State.transition_to_ast_node(this, transition);
    }

    /**
     * Convert the state back into an AST state definition node.
     */
    to_ast_node(): FcstmAstStateDefinition {
        const events = Object.values(this.events).map(event => event.to_ast_node());
        const substates = Object.values(this.substates).map(state => state.to_ast_node());
        const transitions = this.transitions.map(transition => this.to_transition_ast_node(transition));
        const enters = this.onEnters.map(action => action.to_ast_node());
        const durings = this.onDurings.map(action => action.to_ast_node());
        const exits = this.onExits.map(action => action.to_ast_node());
        const duringAspects = this.onDuringAspects.map(action => action.to_ast_node());
        const statements = [
            ...events,
            ...substates,
            ...transitions,
            ...enters,
            ...durings,
            ...exits,
            ...duringAspects,
        ];

        return {
            kind: 'stateDefinition',
            pyNodeType: 'StateDefinition',
            range: cloneRange(this.range),
            text: this.text,
            name: this.name,
            displayName: this.extraName,
            extraName: this.extraName,
            extra_name: this.extra_name,
            pseudo: this.isPseudo,
            isPseudo: this.isPseudo,
            is_pseudo: this.is_pseudo,
            composite: Object.keys(this.substates).length > 0,
            statements,
            events,
            imports: [],
            substates,
            transitions,
            enters,
            durings,
            exits,
            duringAspects,
            during_aspects: duringAspects,
            forceTransitions: [],
            force_transitions: [],
        };
    }

    /**
     * Walk the state and all of its descendants in preorder.
     */
    *walk_states(): Generator<State, void, void> {
        yield this;
        for (const state of Object.values(this.substates)) {
            yield* state.walk_states();
        }
    }

    /**
     * Resolve an event reference relative to this state.
     */
    resolve_event(eventRef: string): Event {
        if (!eventRef) {
            throw new Error('Event reference cannot be empty');
        }

        let targetStatePath: string[];
        let eventName: string;

        if (eventRef.startsWith('/')) {
            const relativePath = eventRef.slice(1);
            if (!relativePath) {
                throw new Error('Absolute event reference cannot be just "/"');
            }
            const rootState = this.getRootState();
            const pathParts = relativePath.split('.');
            if (!pathParts.every(Boolean)) {
                throw new Error(`Invalid absolute event reference: ${JSON.stringify(eventRef)}`);
            }
            eventName = pathParts[pathParts.length - 1];
            targetStatePath = [...rootState.path, ...pathParts.slice(0, -1)];
        } else if (eventRef.startsWith('.')) {
            let dotCount = 0;
            while (dotCount < eventRef.length && eventRef[dotCount] === '.') {
                dotCount += 1;
            }
            const remainingPath = eventRef.slice(dotCount);
            if (!remainingPath) {
                throw new Error(`Parent-relative event reference cannot end with dots: ${JSON.stringify(eventRef)}`);
            }
            let currentState: State | undefined = this;
            for (let index = 0; index < dotCount; index += 1) {
                if (!currentState?.parent) {
                    throw new Error(
                        `Parent-relative event reference ${JSON.stringify(eventRef)} goes beyond root state`
                    );
                }
                currentState = currentState.parent;
            }
            const pathParts = remainingPath.split('.');
            if (!pathParts.every(Boolean)) {
                throw new Error(`Invalid parent-relative event reference: ${JSON.stringify(eventRef)}`);
            }
            eventName = pathParts[pathParts.length - 1];
            targetStatePath = [...(currentState?.path || []), ...pathParts.slice(0, -1)];
        } else {
            const pathParts = eventRef.split('.');
            if (!pathParts.every(Boolean)) {
                throw new Error(`Invalid relative event reference: ${JSON.stringify(eventRef)}`);
            }
            eventName = pathParts[pathParts.length - 1];
            targetStatePath = [...this.path, ...pathParts.slice(0, -1)];
        }

        const rootState = this.getRootState();
        let currentState: State = rootState;
        for (const stateName of targetStatePath.slice(1)) {
            const nextState = currentState.substates[stateName];
            if (!nextState) {
                throw new Error(`State ${JSON.stringify(statePathName(targetStatePath))} not found while resolving ${JSON.stringify(eventRef)}`);
            }
            currentState = nextState;
        }

        const event = currentState.events[eventName];
        if (!event) {
            throw new Error(`Event ${JSON.stringify(eventName)} not found in state ${JSON.stringify(statePathName(targetStatePath))}`);
        }
        return event;
    }

    private getRootState(): State {
        let currentState: State = this;
        while (currentState.parent) {
            currentState = currentState.parent;
        }
        return currentState;
    }
}

/**
 * Root state-machine model aligned with ``pyfcstm.model.model.StateMachine``.
 */
export class StateMachine extends ModelNode {
    filePath: string;
    defines: Record<string, VarDefine>;
    rootState: State;
    root_state: State;
    allStates: State[];
    all_states: State[];
    allEvents: Event[];
    all_events: Event[];
    allTransitions: Transition[];
    all_transitions: Transition[];
    allActions: Array<OnStage | OnAspect>;
    all_actions: Array<OnStage | OnAspect>;
    lookups: FcstmModelLookups;

    constructor(raw: RawFcstmModelStateMachine, rootState: State, lookups: FcstmModelLookups) {
        super(raw.kind, raw.pyModelType, raw.range, raw.text);
        this.filePath = raw.filePath;
        this.defines = {};
        this.rootState = rootState;
        this.root_state = rootState;
        this.allStates = [];
        this.all_states = this.allStates;
        this.allEvents = [];
        this.all_events = this.allEvents;
        this.allTransitions = [];
        this.all_transitions = this.allTransitions;
        this.allActions = [];
        this.all_actions = this.allActions;
        this.lookups = lookups;
    }

    /**
     * Convert the full state machine back into an AST document.
     */
    to_ast_node(): FcstmAstDocument {
        const definitions = Object.values(this.defines).map(definition => definition.to_ast_node());
        return {
            kind: 'document',
            pyNodeType: 'StateMachineDSLProgram',
            range: cloneRange(this.range),
            text: this.text,
            filePath: this.filePath,
            variables: definitions,
            definitions,
            rootState: this.rootState.to_ast_node(),
            root_state: this.rootState.to_ast_node(),
        };
    }

    /**
     * Walk all states in the machine in preorder.
     */
    *walk_states(): Generator<State, void, void> {
        yield* this.rootState.walk_states();
    }

    /**
     * Resolve a fully-qualified event path.
     */
    resolve_event(eventPath: string): Event {
        if (!eventPath) {
            throw new Error('Event path cannot be empty');
        }
        const pathParts = eventPath.split('.');
        if (pathParts.length < 2 || !pathParts.every(Boolean)) {
            throw new Error(`Invalid event path: ${JSON.stringify(eventPath)}`);
        }

        let currentState = this.rootState;
        if (pathParts[0] !== currentState.name) {
            throw new Error(
                `Event path root ${JSON.stringify(pathParts[0])} does not match state machine root ${JSON.stringify(currentState.name)}`
            );
        }

        for (const stateName of pathParts.slice(1, -1)) {
            const nextState = currentState.substates[stateName];
            if (!nextState) {
                throw new Error(`State ${JSON.stringify(stateName)} not found while resolving ${JSON.stringify(eventPath)}`);
            }
            currentState = nextState;
        }

        const eventName = pathParts[pathParts.length - 1];
        const event = currentState.events[eventName];
        if (!event) {
            throw new Error(`Event ${JSON.stringify(eventName)} not found while resolving ${JSON.stringify(eventPath)}`);
        }
        return event;
    }
}

/**
 * Flattened model lookups that always point at hydrated runtime instances.
 */
export interface FcstmModelLookups {
    definesByName: Record<string, VarDefine>;
    statesByPath: Record<string, State>;
    eventsByPathName: Record<string, Event>;
    namedFunctionsByPath: Record<string, OnStage | OnAspect>;
    transitionsByParentPath: Record<string, Transition[]>;
}

/**
 * Public type aliases exposed to package consumers.
 */
export type FcstmModelNodeBase = ModelNode;
export type FcstmModelExpression = Expr;
export type FcstmModelInteger = Integer;
export type FcstmModelFloat = Float;
export type FcstmModelBoolean = BooleanExpr;
export type FcstmModelVariable = Variable;
export type FcstmModelUnaryOp = UnaryOp;
export type FcstmModelBinaryOp = BinaryOp;
export type FcstmModelConditionalOp = ConditionalOp;
export type FcstmModelUFunc = UFunc;
export type FcstmModelOperationStatement = OperationStatement;
export type FcstmModelOperation = Operation;
export type FcstmModelIfBlockBranch = IfBlockBranch;
export type FcstmModelIfBlock = IfBlock;
export type FcstmModelVarDefine = VarDefine;
export type FcstmModelEvent = Event;
export type FcstmModelOnStage = OnStage;
export type FcstmModelOnAspect = OnAspect;
export type FcstmModelNamedFunction = OnStage | OnAspect;
export type FcstmModelTransition = Transition;
export type FcstmModelState = State;
export type FcstmModelStateMachine = StateMachine;

interface HydrationContext {
    cache: WeakMap<object, unknown>;
}

function hydrateExpression(raw: RawFcstmModelExpression, context: HydrationContext): Expr {
    const cached = context.cache.get(raw as object);
    if (cached) {
        return cached as Expr;
    }

    let expression: Expr;
    switch (raw.kind) {
        case 'integer':
            expression = new Integer(raw as RawFcstmModelInteger);
            break;
        case 'float':
            expression = new Float(raw as RawFcstmModelFloat);
            break;
        case 'boolean':
            expression = new BooleanExpr(raw as RawFcstmModelBoolean);
            break;
        case 'variable':
            expression = new Variable(raw as RawFcstmModelVariable);
            break;
        case 'unaryOp': {
            const unary = raw as RawFcstmModelUnaryOp;
            expression = new UnaryOp(unary, hydrateExpression(unary.x, context));
            break;
        }
        case 'binaryOp': {
            const binary = raw as RawFcstmModelBinaryOp;
            expression = new BinaryOp(
                binary,
                hydrateExpression(binary.x, context),
                hydrateExpression(binary.y, context)
            );
            break;
        }
        case 'conditionalOp': {
            const conditional = raw as RawFcstmModelConditionalOp;
            expression = new ConditionalOp(
                conditional,
                hydrateExpression(conditional.cond, context),
                hydrateExpression(conditional.ifTrue, context),
                hydrateExpression(conditional.ifFalse, context)
            );
            break;
        }
        case 'ufunc': {
            const func = raw as RawFcstmModelUFunc;
            expression = new UFunc(func, hydrateExpression(func.x, context));
            break;
        }
        default:
            throw new Error(`Unsupported raw expression kind: ${(raw as RawFcstmModelNodeBase).kind}`);
    }

    context.cache.set(raw as object, expression);
    return expression;
}

function hydrateOperationStatement(
    raw: RawFcstmModelOperationStatement,
    context: HydrationContext
): OperationStatement {
    const cached = context.cache.get(raw as object);
    if (cached) {
        return cached as OperationStatement;
    }

    let statement: OperationStatement;
    if (raw.kind === 'operation') {
        statement = new Operation(raw as RawFcstmModelOperation, hydrateExpression((raw as RawFcstmModelOperation).expr, context));
    } else {
        const ifBlock = raw as RawFcstmModelIfBlock;
        const branches = ifBlock.branches.map(branch => hydrateIfBlockBranch(branch, context));
        statement = new IfBlock(ifBlock, branches);
    }

    context.cache.set(raw as object, statement);
    return statement;
}

function hydrateIfBlockBranch(
    raw: RawFcstmModelIfBlockBranch,
    context: HydrationContext
): IfBlockBranch {
    const cached = context.cache.get(raw as object);
    if (cached) {
        return cached as IfBlockBranch;
    }

    const branch = new IfBlockBranch(
        raw,
        raw.condition ? hydrateExpression(raw.condition, context) : null,
        raw.statements.map(statement => hydrateOperationStatement(statement, context))
    );
    context.cache.set(raw as object, branch);
    return branch;
}

function hydrateEvent(raw: RawFcstmModelEvent, context: HydrationContext): Event {
    const cached = context.cache.get(raw as object);
    if (cached) {
        return cached as Event;
    }
    const event = new Event(raw);
    context.cache.set(raw as object, event);
    return event;
}

function hydrateAction(
    raw: RawFcstmModelNamedFunction,
    context: HydrationContext
): OnStage | OnAspect {
    const cached = context.cache.get(raw as object);
    if (cached) {
        return cached as OnStage | OnAspect;
    }

    const operations = raw.operations.map(operation => hydrateOperationStatement(operation, context));
    const action = raw.kind === 'onAspect'
        ? new OnAspect(raw as RawFcstmModelOnAspect, operations)
        : new OnStage(raw as RawFcstmModelOnStage, operations);
    context.cache.set(raw as object, action);
    return action;
}

function hydrateTransition(
    raw: RawFcstmModelTransition,
    context: HydrationContext
): Transition {
    const cached = context.cache.get(raw as object);
    if (cached) {
        return cached as Transition;
    }

    const transition = new Transition(
        raw,
        raw.event ? hydrateEvent(raw.event, context) : undefined,
        raw.guard ? hydrateExpression(raw.guard, context) : undefined,
        raw.effects.map(effect => hydrateOperationStatement(effect, context))
    );
    context.cache.set(raw as object, transition);
    return transition;
}

function hydrateState(
    raw: RawFcstmModelState,
    context: HydrationContext,
    parent?: State
): State {
    const cached = context.cache.get(raw as object);
    if (cached) {
        const existing = cached as State;
        if (parent) {
            existing.parent = parent;
        }
        return existing;
    }

    const state = new State(raw);
    state.parent = parent;
    context.cache.set(raw as object, state);

    for (const [name, substate] of Object.entries(raw.substates)) {
        state.substates[name] = hydrateState(substate, context, state);
    }
    for (const [name, event] of Object.entries(raw.events)) {
        state.events[name] = hydrateEvent(event, context);
    }
    state.transitions = raw.transitions.map(transition => {
        const hydrated = hydrateTransition(transition, context);
        hydrated.parent = state;
        return hydrated;
    });
    state.onEnters = raw.onEnters.map(action => {
        const hydrated = hydrateAction(action, context) as OnStage;
        hydrated.parent = state;
        return hydrated;
    });
    state.on_enters = state.onEnters;
    state.onDurings = raw.onDurings.map(action => {
        const hydrated = hydrateAction(action, context) as OnStage;
        hydrated.parent = state;
        return hydrated;
    });
    state.on_durings = state.onDurings;
    state.onExits = raw.onExits.map(action => {
        const hydrated = hydrateAction(action, context) as OnStage;
        hydrated.parent = state;
        return hydrated;
    });
    state.on_exits = state.onExits;
    state.onDuringAspects = raw.onDuringAspects.map(action => {
        const hydrated = hydrateAction(action, context) as OnAspect;
        hydrated.parent = state;
        return hydrated;
    });
    state.on_during_aspects = state.onDuringAspects;
    for (const [name, action] of Object.entries(raw.namedFunctions)) {
        const hydrated = hydrateAction(action, context);
        hydrated.parent = state;
        state.namedFunctions[name] = hydrated;
    }
    state.named_functions = state.namedFunctions;
    state.isLeafState = Object.keys(state.substates).length === 0;
    state.isRootState = state.parent === undefined;
    state.isStoppable = state.isLeafState && !state.isPseudo;
    state.is_pseudo = state.isPseudo;

    return state;
}

/**
 * Hydrate a raw state-machine graph into runtime class instances.
 */
export function hydrateStateMachine(raw: RawFcstmModelStateMachine): StateMachine {
    const context: HydrationContext = {
        cache: new WeakMap<object, unknown>(),
    };

    const rootState = hydrateState(raw.rootState, context);
    const lookups: FcstmModelLookups = {
        definesByName: {},
        statesByPath: {},
        eventsByPathName: {},
        namedFunctionsByPath: {},
        transitionsByParentPath: {},
    };
    const stateMachine = new StateMachine(raw, rootState, lookups);
    context.cache.set(raw as object, stateMachine);

    for (const [name, definition] of Object.entries(raw.defines)) {
        const hydrated = new VarDefine(definition, hydrateExpression(definition.init, context));
        stateMachine.defines[name] = hydrated;
        lookups.definesByName[name] = hydrated;
    }

    stateMachine.allStates = raw.allStates.map(state => hydrateState(state, context));
    stateMachine.all_states = stateMachine.allStates;
    stateMachine.allEvents = raw.allEvents.map(event => hydrateEvent(event, context));
    stateMachine.all_events = stateMachine.allEvents;
    stateMachine.allTransitions = raw.allTransitions.map(transition => hydrateTransition(transition, context));
    stateMachine.all_transitions = stateMachine.allTransitions;
    stateMachine.allActions = raw.allActions.map(action => hydrateAction(action, context));
    stateMachine.all_actions = stateMachine.allActions;

    for (const [path, state] of Object.entries(raw.lookups.statesByPath)) {
        lookups.statesByPath[path] = hydrateState(state, context);
    }
    for (const [path, event] of Object.entries(raw.lookups.eventsByPathName)) {
        lookups.eventsByPathName[path] = hydrateEvent(event, context);
    }
    for (const [path, action] of Object.entries(raw.lookups.namedFunctionsByPath)) {
        lookups.namedFunctionsByPath[path] = hydrateAction(action, context);
    }
    for (const [path, transitions] of Object.entries(raw.lookups.transitionsByParentPath)) {
        lookups.transitionsByParentPath[path] = transitions.map(transition => hydrateTransition(transition, context));
    }

    for (const action of stateMachine.allActions) {
        if (action.ref_state_path) {
            const target = lookups.namedFunctionsByPath[statePathName(action.ref_state_path)];
            if (target) {
                action.ref = target;
                action.refResolved = true;
                action.ref_resolved = true;
                action.refTargetQualifiedName = target.func_name;
                action.ref_target_qualified_name = target.func_name;
            }
        }
    }

    return stateMachine;
}

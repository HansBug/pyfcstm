import type {TextRange} from '../utils/text';

export type FcstmPyNodeType =
    | 'StateMachineDSLProgram'
    | 'DefAssignment'
    | 'ChainID'
    | 'StateDefinition'
    | 'EventDefinition'
    | 'TransitionDefinition'
    | 'ForceTransitionDefinition'
    | 'ImportStatement'
    | 'ImportDefExactSelector'
    | 'ImportDefSetSelector'
    | 'ImportDefPatternSelector'
    | 'ImportDefFallbackSelector'
    | 'ImportDefTargetTemplate'
    | 'ImportDefMapping'
    | 'ImportEventMapping'
    | 'OperationAssignment'
    | 'OperationIfBranch'
    | 'OperationIf'
    | 'EnterOperations'
    | 'EnterAbstractFunction'
    | 'EnterRefFunction'
    | 'ExitOperations'
    | 'ExitAbstractFunction'
    | 'ExitRefFunction'
    | 'DuringOperations'
    | 'DuringAbstractFunction'
    | 'DuringRefFunction'
    | 'DuringAspectOperations'
    | 'DuringAspectAbstractFunction'
    | 'DuringAspectRefFunction'
    | 'Boolean'
    | 'Integer'
    | 'HexInt'
    | 'Float'
    | 'Constant'
    | 'Name'
    | 'Paren'
    | 'UnaryOp'
    | 'BinaryOp'
    | 'ConditionalOp'
    | 'UFunc';

export type FcstmAstSpecialStateMark = 'INIT_STATE' | 'EXIT_STATE' | 'ALL';

export interface FcstmAstNodeBase {
    kind: string;
    pyNodeType?: FcstmPyNodeType;
    range: TextRange;
    text: string;
}

export interface FcstmAstDocument extends FcstmAstNodeBase {
    kind: 'document';
    pyNodeType: 'StateMachineDSLProgram';
    filePath: string;
    variables: FcstmAstVariableDefinition[];
    definitions: FcstmAstVariableDefinition[];
    rootState?: FcstmAstStateDefinition;
    root_state?: FcstmAstStateDefinition;
}

export interface FcstmAstVariableDefinition extends FcstmAstNodeBase {
    kind: 'variableDefinition';
    pyNodeType: 'DefAssignment';
    name: string;
    valueType: 'int' | 'float';
    deftype: 'int' | 'float';
    initializer: FcstmAstExpression;
    expr: FcstmAstExpression;
}

export interface FcstmAstStateDefinition extends FcstmAstNodeBase {
    kind: 'stateDefinition';
    pyNodeType: 'StateDefinition';
    name: string;
    displayName?: string;
    extraName?: string;
    extra_name?: string;
    pseudo: boolean;
    isPseudo: boolean;
    is_pseudo: boolean;
    composite: boolean;
    statements: FcstmAstStateStatement[];
    events: FcstmAstEventDefinition[];
    imports: FcstmAstImportStatement[];
    substates: FcstmAstStateDefinition[];
    transitions: FcstmAstTransition[];
    enters: FcstmAstAction[];
    durings: FcstmAstAction[];
    exits: FcstmAstAction[];
    duringAspects: FcstmAstAction[];
    during_aspects: FcstmAstAction[];
    forceTransitions: FcstmAstForcedTransition[];
    force_transitions: FcstmAstForcedTransition[];
}

export type FcstmAstStateStatement =
    | FcstmAstStateDefinition
    | FcstmAstTransition
    | FcstmAstForcedTransition
    | FcstmAstAction
    | FcstmAstEventDefinition
    | FcstmAstImportStatement;

export interface FcstmAstEventDefinition extends FcstmAstNodeBase {
    kind: 'eventDefinition';
    pyNodeType: 'EventDefinition';
    name: string;
    displayName?: string;
    extraName?: string;
    extra_name?: string;
}

export interface FcstmAstChainPath extends FcstmAstNodeBase {
    kind: 'chainPath';
    pyNodeType: 'ChainID';
    isAbsolute: boolean;
    is_absolute: boolean;
    segments: string[];
    path: string[];
}

export interface FcstmAstLocalTrigger extends FcstmAstNodeBase {
    kind: 'localTrigger';
    eventName: string;
}

export interface FcstmAstChainTrigger extends FcstmAstNodeBase {
    kind: 'chainTrigger';
    eventPath: FcstmAstChainPath;
}

export type FcstmAstTrigger = FcstmAstLocalTrigger | FcstmAstChainTrigger;

export interface FcstmAstTransitionBase extends FcstmAstNodeBase {
    sourceStateName?: string;
    targetStateName?: string;
    sourceKind: 'init' | 'state' | 'all';
    targetKind: 'state' | 'exit';
    trigger?: FcstmAstTrigger;
    guard?: FcstmAstExpression;
    effect?: FcstmAstOperationBlock;
    fromState?: string | FcstmAstSpecialStateMark;
    from_state?: string | FcstmAstSpecialStateMark;
    toState?: string | FcstmAstSpecialStateMark;
    to_state?: string | FcstmAstSpecialStateMark;
    eventId?: FcstmAstChainPath;
    event_id?: FcstmAstChainPath;
    conditionExpr?: FcstmAstExpression;
    condition_expr?: FcstmAstExpression;
    postOperations: FcstmAstOperationStatement[];
    post_operations: FcstmAstOperationStatement[];
}

export interface FcstmAstTransition extends FcstmAstTransitionBase {
    kind: 'transition';
    pyNodeType: 'TransitionDefinition';
    transitionKind: 'entry' | 'normal' | 'exit';
}

export interface FcstmAstForcedTransition extends FcstmAstTransitionBase {
    kind: 'forcedTransition';
    pyNodeType: 'ForceTransitionDefinition';
    transitionKind: 'normal' | 'exit' | 'normalAll' | 'exitAll';
}

export interface FcstmAstAction extends FcstmAstNodeBase {
    kind: 'action';
    pyNodeType:
        | 'EnterOperations'
        | 'EnterAbstractFunction'
        | 'EnterRefFunction'
        | 'ExitOperations'
        | 'ExitAbstractFunction'
        | 'ExitRefFunction'
        | 'DuringOperations'
        | 'DuringAbstractFunction'
        | 'DuringRefFunction'
        | 'DuringAspectOperations'
        | 'DuringAspectAbstractFunction'
        | 'DuringAspectRefFunction';
    stage: 'enter' | 'during' | 'exit';
    aspect?: 'before' | 'after';
    isGlobalAspect: boolean;
    mode: 'operations' | 'abstract' | 'ref';
    name?: string;
    operations?: FcstmAstOperationBlock;
    operationsList: FcstmAstOperationStatement[];
    refPath?: FcstmAstChainPath;
    ref?: FcstmAstChainPath;
    doc?: string;
}

export interface FcstmAstImportDefTargetTemplate extends FcstmAstNodeBase {
    kind: 'importDefTargetTemplate';
    pyNodeType: 'ImportDefTargetTemplate';
    template: string;
}

export interface FcstmAstImportStatement extends FcstmAstNodeBase {
    kind: 'importStatement';
    pyNodeType: 'ImportStatement';
    sourcePath: string;
    source_path: string;
    alias: string;
    displayName?: string;
    extraName?: string;
    extra_name?: string;
    pathRange: TextRange;
    aliasRange: TextRange;
    mappings: FcstmAstImportMapping[];
}

export type FcstmAstImportMapping = FcstmAstImportDefMapping | FcstmAstImportEventMapping;

export interface FcstmAstImportDefSelectorBase extends FcstmAstNodeBase {
    kind: string;
    pyNodeType:
        | 'ImportDefExactSelector'
        | 'ImportDefSetSelector'
        | 'ImportDefPatternSelector'
        | 'ImportDefFallbackSelector';
}

export interface FcstmAstImportDefFallbackSelector extends FcstmAstImportDefSelectorBase {
    kind: 'importDefFallbackSelector';
    pyNodeType: 'ImportDefFallbackSelector';
}

export interface FcstmAstImportDefSetSelector extends FcstmAstImportDefSelectorBase {
    kind: 'importDefSetSelector';
    pyNodeType: 'ImportDefSetSelector';
    names: string[];
}

export interface FcstmAstImportDefPatternSelector extends FcstmAstImportDefSelectorBase {
    kind: 'importDefPatternSelector';
    pyNodeType: 'ImportDefPatternSelector';
    pattern: string;
}

export interface FcstmAstImportDefExactSelector extends FcstmAstImportDefSelectorBase {
    kind: 'importDefExactSelector';
    pyNodeType: 'ImportDefExactSelector';
    name: string;
}

export type FcstmAstImportDefSelector =
    | FcstmAstImportDefFallbackSelector
    | FcstmAstImportDefSetSelector
    | FcstmAstImportDefPatternSelector
    | FcstmAstImportDefExactSelector;

export interface FcstmAstImportDefMapping extends FcstmAstNodeBase {
    kind: 'importDefMapping';
    pyNodeType: 'ImportDefMapping';
    selector: FcstmAstImportDefSelector;
    targetTemplate: string;
    targetTemplateNode: FcstmAstImportDefTargetTemplate;
    target_template: FcstmAstImportDefTargetTemplate;
}

export interface FcstmAstImportEventMapping extends FcstmAstNodeBase {
    kind: 'importEventMapping';
    pyNodeType: 'ImportEventMapping';
    sourceEvent: FcstmAstChainPath;
    source_event: FcstmAstChainPath;
    targetEvent: FcstmAstChainPath;
    target_event: FcstmAstChainPath;
    displayName?: string;
    extraName?: string;
    extra_name?: string;
}

export interface FcstmAstOperationBlock extends FcstmAstNodeBase {
    kind: 'operationBlock';
    statements: FcstmAstOperationStatement[];
}

export type FcstmAstOperationStatement =
    | FcstmAstAssignmentStatement
    | FcstmAstIfStatement
    | FcstmAstEmptyStatement;

export interface FcstmAstAssignmentStatement extends FcstmAstNodeBase {
    kind: 'assignmentStatement';
    pyNodeType: 'OperationAssignment';
    targetName: string;
    name: string;
    expression: FcstmAstExpression;
    expr: FcstmAstExpression;
}

export interface FcstmAstIfBranch extends FcstmAstNodeBase {
    kind: 'ifBranch';
    pyNodeType: 'OperationIfBranch';
    condition: FcstmAstExpression | null;
    statements: FcstmAstOperationStatement[];
    block: FcstmAstOperationBlock;
}

export interface FcstmAstIfStatement extends FcstmAstNodeBase {
    kind: 'ifStatement';
    pyNodeType: 'OperationIf';
    branches: FcstmAstIfBranch[];
    elseBlock?: FcstmAstOperationBlock;
}

export interface FcstmAstEmptyStatement extends FcstmAstNodeBase {
    kind: 'emptyStatement';
}

export type FcstmAstExpression =
    | FcstmAstLiteralExpression
    | FcstmAstIdentifierExpression
    | FcstmAstMathConstExpression
    | FcstmAstUnaryExpression
    | FcstmAstBinaryExpression
    | FcstmAstFunctionExpression
    | FcstmAstConditionalExpression
    | FcstmAstParenthesizedExpression;

export interface FcstmAstExpressionBase extends FcstmAstNodeBase {
    pyNodeType:
        | 'Boolean'
        | 'Integer'
        | 'HexInt'
        | 'Float'
        | 'Constant'
        | 'Name'
        | 'Paren'
        | 'UnaryOp'
        | 'BinaryOp'
        | 'ConditionalOp'
        | 'UFunc';
    expressionKind: string;
    expressionType: 'init' | 'num' | 'cond';
}

export interface FcstmAstLiteralExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'literal';
    pyNodeType: 'Boolean' | 'Integer' | 'HexInt' | 'Float';
    literalType: 'number' | 'boolean';
    valueText: string;
    raw: string;
}

export interface FcstmAstIdentifierExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'identifier';
    pyNodeType: 'Name';
    name: string;
}

export interface FcstmAstMathConstExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'mathConst';
    pyNodeType: 'Constant';
    name: string;
    raw: string;
}

export interface FcstmAstUnaryExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'unary';
    pyNodeType: 'UnaryOp';
    operator: string;
    op: string;
    operand: FcstmAstExpression;
    expr: FcstmAstExpression;
}

export interface FcstmAstBinaryExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'binary';
    pyNodeType: 'BinaryOp';
    operator: string;
    op: string;
    left: FcstmAstExpression;
    expr1: FcstmAstExpression;
    right: FcstmAstExpression;
    expr2: FcstmAstExpression;
}

export interface FcstmAstFunctionExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'function';
    pyNodeType: 'UFunc';
    functionName: string;
    func: string;
    argument: FcstmAstExpression;
    expr: FcstmAstExpression;
}

export interface FcstmAstConditionalExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'conditional';
    pyNodeType: 'ConditionalOp';
    condition: FcstmAstExpression;
    cond: FcstmAstExpression;
    whenTrue: FcstmAstExpression;
    valueTrue: FcstmAstExpression;
    value_true: FcstmAstExpression;
    whenFalse: FcstmAstExpression;
    valueFalse: FcstmAstExpression;
    value_false: FcstmAstExpression;
}

export interface FcstmAstParenthesizedExpression extends FcstmAstExpressionBase {
    kind: 'expression';
    expressionKind: 'parenthesized';
    pyNodeType: 'Paren';
    expression: FcstmAstExpression;
    expr: FcstmAstExpression;
}

export type StateMachineDSLProgram = FcstmAstDocument;
export type DefAssignment = FcstmAstVariableDefinition;
export type StateDefinition = FcstmAstStateDefinition;
export type EventDefinition = FcstmAstEventDefinition;
export type ChainID = FcstmAstChainPath;
export type TransitionDefinition = FcstmAstTransition;
export type ForceTransitionDefinition = FcstmAstForcedTransition;
export type ImportStatement = FcstmAstImportStatement;
export type ImportDefTargetTemplate = FcstmAstImportDefTargetTemplate;
export type ImportDefMapping = FcstmAstImportDefMapping;
export type ImportEventMapping = FcstmAstImportEventMapping;
export type OperationAssignment = FcstmAstAssignmentStatement;
export type OperationIfBranch = FcstmAstIfBranch;
export type OperationIf = FcstmAstIfStatement;
export type Expr = FcstmAstExpression;

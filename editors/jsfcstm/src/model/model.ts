/* c8 ignore start */
/**
 * Stable, pyfcstm-aligned state-machine model types for jsfcstm.
 *
 * This layer sits above the AST and semantic document. It keeps the core
 * object vocabulary close to ``pyfcstm.model`` while remaining serializable and
 * editor-friendly for JavaScript consumers.
 */
import type {TextRange} from '../utils/text';

/**
 * Stable action path representation.
 *
 * The final segment is ``null`` for unnamed lifecycle actions so the shape can
 * mirror Python's ``state_path`` tuples.
 */
export type FcstmModelActionPath = Array<string | null>;

/**
 * Shared base fields for all public model nodes.
 */
export interface FcstmModelNodeBase {
    kind: string;
    pyModelType:
        | 'StateMachine'
        | 'VarDefine'
        | 'State'
        | 'Event'
        | 'Transition'
        | 'OnStage'
        | 'OnAspect'
        | 'Operation'
        | 'IfBlock'
        | 'IfBlockBranch'
        | 'Integer'
        | 'Float'
        | 'Boolean'
        | 'Variable'
        | 'UnaryOp'
        | 'BinaryOp'
        | 'ConditionalOp'
        | 'UFunc';
    range: TextRange;
    text: string;
}

/**
 * Shared expression fields aligned with ``pyfcstm.model.expr``.
 */
export interface FcstmModelExpressionBase extends FcstmModelNodeBase {
    kind:
        | 'integer'
        | 'float'
        | 'boolean'
        | 'variable'
        | 'unaryOp'
        | 'binaryOp'
        | 'conditionalOp'
        | 'ufunc';
}

/**
 * Integer literal expression.
 */
export interface FcstmModelInteger extends FcstmModelExpressionBase {
    kind: 'integer';
    pyModelType: 'Integer';
    value: number;
}

/**
 * Floating-point expression.
 *
 * Named math constants such as ``pi`` and ``tau`` are normalized into this
 * value form to match Python's model layer.
 */
export interface FcstmModelFloat extends FcstmModelExpressionBase {
    kind: 'float';
    pyModelType: 'Float';
    value: number;
}

/**
 * Boolean literal expression.
 */
export interface FcstmModelBoolean extends FcstmModelExpressionBase {
    kind: 'boolean';
    pyModelType: 'Boolean';
    value: boolean;
}

/**
 * Variable-reference expression.
 */
export interface FcstmModelVariable extends FcstmModelExpressionBase {
    kind: 'variable';
    pyModelType: 'Variable';
    name: string;
}

/**
 * Unary operator expression.
 */
export interface FcstmModelUnaryOp extends FcstmModelExpressionBase {
    kind: 'unaryOp';
    pyModelType: 'UnaryOp';
    op: string;
    x: FcstmModelExpression;
}

/**
 * Binary operator expression.
 */
export interface FcstmModelBinaryOp extends FcstmModelExpressionBase {
    kind: 'binaryOp';
    pyModelType: 'BinaryOp';
    x: FcstmModelExpression;
    op: string;
    y: FcstmModelExpression;
}

/**
 * Conditional operator expression.
 */
export interface FcstmModelConditionalOp extends FcstmModelExpressionBase {
    kind: 'conditionalOp';
    pyModelType: 'ConditionalOp';
    cond: FcstmModelExpression;
    ifTrue: FcstmModelExpression;
    if_true: FcstmModelExpression;
    ifFalse: FcstmModelExpression;
    if_false: FcstmModelExpression;
}

/**
 * Unary math-function call expression.
 */
export interface FcstmModelUFunc extends FcstmModelExpressionBase {
    kind: 'ufunc';
    pyModelType: 'UFunc';
    func: string;
    x: FcstmModelExpression;
}

/**
 * Union of all public model expression nodes.
 */
export type FcstmModelExpression =
    | FcstmModelInteger
    | FcstmModelFloat
    | FcstmModelBoolean
    | FcstmModelVariable
    | FcstmModelUnaryOp
    | FcstmModelBinaryOp
    | FcstmModelConditionalOp
    | FcstmModelUFunc;

/**
 * Operation assignment statement.
 */
export interface FcstmModelOperation extends FcstmModelNodeBase {
    kind: 'operation';
    pyModelType: 'Operation';
    varName: string;
    var_name: string;
    expr: FcstmModelExpression;
}

/**
 * Single branch in a model-layer ``if`` block.
 */
export interface FcstmModelIfBlockBranch extends FcstmModelNodeBase {
    kind: 'ifBlockBranch';
    pyModelType: 'IfBlockBranch';
    condition: FcstmModelExpression | null;
    statements: FcstmModelOperationStatement[];
}

/**
 * ``if / else if / else`` model statement.
 */
export interface FcstmModelIfBlock extends FcstmModelNodeBase {
    kind: 'ifBlock';
    pyModelType: 'IfBlock';
    branches: FcstmModelIfBlockBranch[];
}

/**
 * Union of executable operation statements.
 */
export type FcstmModelOperationStatement = FcstmModelOperation | FcstmModelIfBlock;

/**
 * Variable definition entry.
 */
export interface FcstmModelVarDefine extends FcstmModelNodeBase {
    kind: 'varDefine';
    pyModelType: 'VarDefine';
    name: string;
    type: 'int' | 'float';
    init: FcstmModelExpression;
}

/**
 * Event entry scoped to a specific state path.
 */
export interface FcstmModelEvent extends FcstmModelNodeBase {
    kind: 'event';
    pyModelType: 'Event';
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
}

/**
 * Shared lifecycle-action fields.
 */
export interface FcstmModelActionBase extends FcstmModelNodeBase {
    stage: 'enter' | 'during' | 'exit';
    aspect?: 'before' | 'after';
    name?: string;
    doc?: string;
    operations: FcstmModelOperationStatement[];
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
}

/**
 * Entry/during/exit action aligned with ``pyfcstm.model.OnStage``.
 */
export interface FcstmModelOnStage extends FcstmModelActionBase {
    kind: 'onStage';
    pyModelType: 'OnStage';
}

/**
 * During-aspect action aligned with ``pyfcstm.model.OnAspect``.
 */
export interface FcstmModelOnAspect extends FcstmModelActionBase {
    kind: 'onAspect';
    pyModelType: 'OnAspect';
    stage: 'during';
    isAspect: true;
    is_aspect: true;
}

/**
 * Union of public named-function/action model nodes.
 */
export type FcstmModelNamedFunction = FcstmModelOnStage | FcstmModelOnAspect;

/**
 * Transition entry aligned with ``pyfcstm.model.Transition``.
 */
export interface FcstmModelTransition extends FcstmModelNodeBase {
    kind: 'transition';
    pyModelType: 'Transition';
    fromState: string | 'INIT_STATE';
    from_state: string | 'INIT_STATE';
    toState: string | 'EXIT_STATE';
    to_state: string | 'EXIT_STATE';
    event?: FcstmModelEvent;
    guard?: FcstmModelExpression;
    effects: FcstmModelOperationStatement[];
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
}

/**
 * Hierarchical state entry aligned with ``pyfcstm.model.State``.
 */
export interface FcstmModelState extends FcstmModelNodeBase {
    kind: 'state';
    pyModelType: 'State';
    name: string;
    path: string[];
    pathName: string;
    path_name: string;
    substates: Record<string, FcstmModelState>;
    events: Record<string, FcstmModelEvent>;
    transitions: FcstmModelTransition[];
    namedFunctions: Record<string, FcstmModelNamedFunction>;
    named_functions: Record<string, FcstmModelNamedFunction>;
    onEnters: FcstmModelOnStage[];
    on_enters: FcstmModelOnStage[];
    onDurings: FcstmModelOnStage[];
    on_durings: FcstmModelOnStage[];
    onExits: FcstmModelOnStage[];
    on_exits: FcstmModelOnStage[];
    onDuringAspects: FcstmModelOnAspect[];
    on_during_aspects: FcstmModelOnAspect[];
    parentPath?: string[];
    parent_path?: string[];
    substateNameToId: Record<string, number>;
    substate_name_to_id: Record<string, number>;
    extraName?: string;
    extra_name?: string;
    isPseudo: boolean;
    is_pseudo: boolean;
    isLeafState: boolean;
    is_leaf_state: boolean;
    isRootState: boolean;
    is_root_state: boolean;
    isStoppable: boolean;
    is_stoppable: boolean;
}

/**
 * Common flattened lookups exposed alongside the recursive model graph.
 */
export interface FcstmModelLookups {
    definesByName: Record<string, FcstmModelVarDefine>;
    statesByPath: Record<string, FcstmModelState>;
    eventsByPathName: Record<string, FcstmModelEvent>;
    namedFunctionsByPath: Record<string, FcstmModelNamedFunction>;
    transitionsByParentPath: Record<string, FcstmModelTransition[]>;
}

/**
 * Root state-machine model aligned with ``pyfcstm.model.StateMachine``.
 */
export interface FcstmModelStateMachine extends FcstmModelNodeBase {
    kind: 'stateMachine';
    pyModelType: 'StateMachine';
    filePath: string;
    defines: Record<string, FcstmModelVarDefine>;
    rootState: FcstmModelState;
    root_state: FcstmModelState;
    allStates: FcstmModelState[];
    all_states: FcstmModelState[];
    allEvents: FcstmModelEvent[];
    all_events: FcstmModelEvent[];
    allTransitions: FcstmModelTransition[];
    all_transitions: FcstmModelTransition[];
    allActions: FcstmModelNamedFunction[];
    all_actions: FcstmModelNamedFunction[];
    lookups: FcstmModelLookups;
}
/* c8 ignore stop */

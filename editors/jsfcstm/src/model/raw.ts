/* c8 ignore file */
/**
 * Raw model node shapes used while building the jsfcstm model graph.
 *
 * These interfaces are intentionally plain-data only. ``builder.ts`` produces
 * these raw objects first, then ``runtime.ts`` hydrates them into pyfcstm-like
 * runtime classes with methods, parent links, and derived properties.
 */
import type {TextRange} from '../utils/text';

/**
 * Stable lifecycle-action path.
 *
 * The last segment is ``null`` for unnamed actions so the shape mirrors the
 * Python model's ``state_path`` tuple.
 */
export type FcstmModelActionPath = Array<string | null>;

/**
 * Shared raw fields for all model nodes.
 */
export interface RawFcstmModelNodeBase {
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
export interface RawFcstmModelExpressionBase extends RawFcstmModelNodeBase {
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

export interface RawFcstmModelInteger extends RawFcstmModelExpressionBase {
    kind: 'integer';
    pyModelType: 'Integer';
    value: number;
}

export interface RawFcstmModelFloat extends RawFcstmModelExpressionBase {
    kind: 'float';
    pyModelType: 'Float';
    value: number;
}

export interface RawFcstmModelBoolean extends RawFcstmModelExpressionBase {
    kind: 'boolean';
    pyModelType: 'Boolean';
    value: boolean;
}

export interface RawFcstmModelVariable extends RawFcstmModelExpressionBase {
    kind: 'variable';
    pyModelType: 'Variable';
    name: string;
}

export interface RawFcstmModelUnaryOp extends RawFcstmModelExpressionBase {
    kind: 'unaryOp';
    pyModelType: 'UnaryOp';
    op: string;
    x: RawFcstmModelExpression;
}

export interface RawFcstmModelBinaryOp extends RawFcstmModelExpressionBase {
    kind: 'binaryOp';
    pyModelType: 'BinaryOp';
    x: RawFcstmModelExpression;
    op: string;
    y: RawFcstmModelExpression;
}

export interface RawFcstmModelConditionalOp extends RawFcstmModelExpressionBase {
    kind: 'conditionalOp';
    pyModelType: 'ConditionalOp';
    cond: RawFcstmModelExpression;
    ifTrue: RawFcstmModelExpression;
    if_true: RawFcstmModelExpression;
    ifFalse: RawFcstmModelExpression;
    if_false: RawFcstmModelExpression;
}

export interface RawFcstmModelUFunc extends RawFcstmModelExpressionBase {
    kind: 'ufunc';
    pyModelType: 'UFunc';
    func: string;
    x: RawFcstmModelExpression;
}

export type RawFcstmModelExpression =
    | RawFcstmModelInteger
    | RawFcstmModelFloat
    | RawFcstmModelBoolean
    | RawFcstmModelVariable
    | RawFcstmModelUnaryOp
    | RawFcstmModelBinaryOp
    | RawFcstmModelConditionalOp
    | RawFcstmModelUFunc;

export interface RawFcstmModelOperation extends RawFcstmModelNodeBase {
    kind: 'operation';
    pyModelType: 'Operation';
    varName: string;
    var_name: string;
    expr: RawFcstmModelExpression;
}

export interface RawFcstmModelIfBlockBranch extends RawFcstmModelNodeBase {
    kind: 'ifBlockBranch';
    pyModelType: 'IfBlockBranch';
    condition: RawFcstmModelExpression | null;
    statements: RawFcstmModelOperationStatement[];
}

export interface RawFcstmModelIfBlock extends RawFcstmModelNodeBase {
    kind: 'ifBlock';
    pyModelType: 'IfBlock';
    branches: RawFcstmModelIfBlockBranch[];
}

export type RawFcstmModelOperationStatement =
    | RawFcstmModelOperation
    | RawFcstmModelIfBlock;

export interface RawFcstmModelVarDefine extends RawFcstmModelNodeBase {
    kind: 'varDefine';
    pyModelType: 'VarDefine';
    name: string;
    type: 'int' | 'float';
    init: RawFcstmModelExpression;
}

export interface RawFcstmModelEvent extends RawFcstmModelNodeBase {
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

export interface RawFcstmModelActionBase extends RawFcstmModelNodeBase {
    stage: 'enter' | 'during' | 'exit';
    aspect?: 'before' | 'after';
    name?: string;
    doc?: string;
    operations: RawFcstmModelOperationStatement[];
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

export interface RawFcstmModelOnStage extends RawFcstmModelActionBase {
    kind: 'onStage';
    pyModelType: 'OnStage';
}

export interface RawFcstmModelOnAspect extends RawFcstmModelActionBase {
    kind: 'onAspect';
    pyModelType: 'OnAspect';
    stage: 'during';
    isAspect: true;
    is_aspect: true;
}

export type RawFcstmModelNamedFunction = RawFcstmModelOnStage | RawFcstmModelOnAspect;

export interface RawFcstmModelTransition extends RawFcstmModelNodeBase {
    kind: 'transition';
    pyModelType: 'Transition';
    fromState: string | 'INIT_STATE';
    from_state: string | 'INIT_STATE';
    toState: string | 'EXIT_STATE';
    to_state: string | 'EXIT_STATE';
    event?: RawFcstmModelEvent;
    guard?: RawFcstmModelExpression;
    effects: RawFcstmModelOperationStatement[];
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

export interface RawFcstmModelState extends RawFcstmModelNodeBase {
    kind: 'state';
    pyModelType: 'State';
    name: string;
    path: string[];
    pathName: string;
    path_name: string;
    substates: Record<string, RawFcstmModelState>;
    events: Record<string, RawFcstmModelEvent>;
    transitions: RawFcstmModelTransition[];
    namedFunctions: Record<string, RawFcstmModelNamedFunction>;
    named_functions: Record<string, RawFcstmModelNamedFunction>;
    onEnters: RawFcstmModelOnStage[];
    on_enters: RawFcstmModelOnStage[];
    onDurings: RawFcstmModelOnStage[];
    on_durings: RawFcstmModelOnStage[];
    onExits: RawFcstmModelOnStage[];
    on_exits: RawFcstmModelOnStage[];
    onDuringAspects: RawFcstmModelOnAspect[];
    on_during_aspects: RawFcstmModelOnAspect[];
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
    /** Source file this state was imported from (import-root only). */
    importedFromFile?: string;
    imported_from_file?: string;
}

export interface RawFcstmModelLookups {
    definesByName: Record<string, RawFcstmModelVarDefine>;
    statesByPath: Record<string, RawFcstmModelState>;
    eventsByPathName: Record<string, RawFcstmModelEvent>;
    namedFunctionsByPath: Record<string, RawFcstmModelNamedFunction>;
    transitionsByParentPath: Record<string, RawFcstmModelTransition[]>;
}

export interface RawFcstmModelStateMachine extends RawFcstmModelNodeBase {
    kind: 'stateMachine';
    pyModelType: 'StateMachine';
    filePath: string;
    defines: Record<string, RawFcstmModelVarDefine>;
    rootState: RawFcstmModelState;
    root_state: RawFcstmModelState;
    allStates: RawFcstmModelState[];
    all_states: RawFcstmModelState[];
    allEvents: RawFcstmModelEvent[];
    all_events: RawFcstmModelEvent[];
    allTransitions: RawFcstmModelTransition[];
    all_transitions: RawFcstmModelTransition[];
    allActions: RawFcstmModelNamedFunction[];
    all_actions: RawFcstmModelNamedFunction[];
    lookups: RawFcstmModelLookups;
}

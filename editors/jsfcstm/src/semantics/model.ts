/**
 * Semantic model types derived from the jsfcstm AST.
 *
 * These structures capture pyfcstm-compatible symbol identities and the
 * resolved relationships that editor features need for hover, import analysis,
 * workspace graph assembly, and navigation.
 */
import type {
    FcstmAstAction,
    FcstmAstDocument,
    FcstmAstEventDefinition,
    FcstmAstExpression,
    FcstmAstForcedTransition,
    FcstmAstImportDefMapping,
    FcstmAstImportEventMapping,
    FcstmAstImportStatement,
    FcstmAstStateDefinition,
    FcstmAstTransition,
    FcstmAstVariableDefinition,
} from '../ast';
import type {TextRange} from '../utils/text';

export type FcstmSemanticSymbolKind =
    | 'file'
    | 'module'
    | 'machine'
    | 'variable'
    | 'state'
    | 'event'
    | 'transition'
    | 'action'
    | 'import';

/**
 * Stable identity for a semantic symbol inside a parsed FCSTM workspace.
 */
export interface FcstmSymbolIdentity {
    id: string;
    kind: FcstmSemanticSymbolKind;
    name: string;
    qualifiedName: string;
    path: string[];
}

/**
 * Semantic record for a source file.
 */
export interface FcstmSemanticFile {
    identity: FcstmSymbolIdentity;
    filePath: string;
    range: TextRange;
}

/**
 * Semantic record for a module-level FCSTM document.
 */
export interface FcstmSemanticModule {
    identity: FcstmSymbolIdentity;
    fileId: string;
    filePath: string;
    rootStateId?: string;
}

/**
 * Semantic record for the root state machine object in a module.
 */
export interface FcstmSemanticMachine {
    identity: FcstmSymbolIdentity;
    moduleId: string;
    rootStateId?: string;
}

/**
 * Semantic variable entry aligned with a ``DefAssignment`` AST node.
 */
export interface FcstmSemanticVariable {
    identity: FcstmSymbolIdentity;
    name: string;
    valueType: 'int' | 'float';
    initializer: FcstmAstExpression;
    ast: FcstmAstVariableDefinition;
    range: TextRange;
}

/**
 * Semantic state entry aligned with a ``StateDefinition`` AST node.
 */
export interface FcstmSemanticState {
    identity: FcstmSymbolIdentity;
    name: string;
    displayName?: string;
    pseudo: boolean;
    composite: boolean;
    range: TextRange;
    ast: FcstmAstStateDefinition;
    parentStateId?: string;
    childStateIds: string[];
}

/**
 * Semantic event entry, including implicit events synthesized from transitions.
 */
export interface FcstmSemanticEvent {
    identity: FcstmSymbolIdentity;
    name: string;
    displayName?: string;
    range: TextRange;
    statePath: string[];
    declared: boolean;
    origins: Array<'declared' | 'local' | 'chain' | 'absolute'>;
    absolutePathText?: string;
    declarationAst?: FcstmAstEventDefinition;
}

/**
 * Resolved event reference attached to a transition trigger.
 */
export interface FcstmSemanticEventReference {
    scope: 'local' | 'chain' | 'absolute';
    rawText: string;
    range: TextRange;
    eventId: string;
    normalizedPath: string[];
    qualifiedName: string;
    absolutePathText?: string;
}

/**
 * Resolved or unresolved action reference attached to a ref-style action.
 */
export interface FcstmSemanticActionReference {
    rawPath: string;
    range: TextRange;
    targetActionId?: string;
    targetQualifiedName?: string;
    resolved: boolean;
}

/**
 * Semantic action entry aligned with a lifecycle action AST node.
 */
export interface FcstmSemanticAction {
    identity: FcstmSymbolIdentity;
    stage: 'enter' | 'during' | 'exit';
    aspect?: 'before' | 'after';
    isGlobalAspect: boolean;
    mode: 'operations' | 'abstract' | 'ref';
    name?: string;
    range: TextRange;
    ast: FcstmAstAction;
    ownerStateId: string;
    ownerStatePath: string[];
    operationsText?: string;
    ref?: FcstmSemanticActionReference;
    doc?: string;
}

/**
 * Expanded transition generated from a forced-transition definition.
 */
export interface FcstmExpandedForceTransition {
    sourceStateId: string;
    sourceStatePath: string[];
    mode: 'direct' | 'exitToParent';
    targetKind: 'state' | 'exit';
    targetStateId?: string;
    targetStatePath?: string[];
}

/**
 * Semantic transition entry aligned with either a normal or forced transition AST node.
 */
export interface FcstmSemanticTransition {
    identity: FcstmSymbolIdentity;
    transitionKind: 'entry' | 'normal' | 'exit' | 'normalAll' | 'exitAll';
    forced: boolean;
    range: TextRange;
    ast: FcstmAstTransition | FcstmAstForcedTransition;
    ownerStateId: string;
    ownerStatePath: string[];
    sourceStateName?: string;
    targetStateName?: string;
    sourceKind: 'init' | 'state' | 'all';
    targetKind: 'state' | 'exit';
    sourceStateId?: string;
    sourceStatePath?: string[];
    targetStateId?: string;
    targetStatePath?: string[];
    trigger?: FcstmSemanticEventReference;
    guard?: FcstmAstExpression;
    effectText?: string;
    expandedTransitions: FcstmExpandedForceTransition[];
}

/**
 * Semantic import entry aligned with an ``ImportStatement`` AST node.
 */
export interface FcstmSemanticImport {
    identity: FcstmSymbolIdentity;
    range: TextRange;
    pathRange: TextRange;
    aliasRange: TextRange;
    ast: FcstmAstImportStatement;
    ownerStateId: string;
    ownerStatePath: string[];
    sourcePath: string;
    alias: string;
    displayName?: string;
    mountedStatePath: string[];
    defMappings: FcstmAstImportDefMapping[];
    eventMappings: FcstmAstImportEventMapping[];
    resolvedFile?: string;
    entryFile?: string;
    exists: boolean;
    missing: boolean;
    targetModuleId?: string;
    targetRootStateName?: string;
    sourceVariables: string[];
    sourceAbsoluteEvents: string[];
    mappedVariables: string[];
    mappedAbsoluteEvents: string[];
}

/**
 * Lightweight summary used by workspace import hydration and editor UIs.
 */
export interface FcstmSemanticSummary {
    rootStateName?: string;
    explicitVariables: string[];
    absoluteEvents: string[];
}

/**
 * Precomputed lookup tables for common semantic resolution paths.
 */
export interface FcstmSemanticLookups {
    statesByPath: Record<string, FcstmSemanticState>;
    actionsByPath: Record<string, FcstmSemanticAction>;
    eventsByQualifiedName: Record<string, FcstmSemanticEvent>;
    importsByPath: Record<string, FcstmSemanticImport>;
}

/**
 * Full semantic document produced from a jsfcstm AST.
 */
export interface FcstmSemanticDocument {
    kind: 'semanticDocument';
    file: FcstmSemanticFile;
    module: FcstmSemanticModule;
    machine: FcstmSemanticMachine;
    ast: FcstmAstDocument | null;
    variables: FcstmSemanticVariable[];
    states: FcstmSemanticState[];
    events: FcstmSemanticEvent[];
    transitions: FcstmSemanticTransition[];
    actions: FcstmSemanticAction[];
    imports: FcstmSemanticImport[];
    summary: FcstmSemanticSummary;
    lookups: FcstmSemanticLookups;
}

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

export interface FcstmSymbolIdentity {
    id: string;
    kind: FcstmSemanticSymbolKind;
    name: string;
    qualifiedName: string;
    path: string[];
}

export interface FcstmSemanticFile {
    identity: FcstmSymbolIdentity;
    filePath: string;
    range: TextRange;
}

export interface FcstmSemanticModule {
    identity: FcstmSymbolIdentity;
    fileId: string;
    filePath: string;
    rootStateId?: string;
}

export interface FcstmSemanticMachine {
    identity: FcstmSymbolIdentity;
    moduleId: string;
    rootStateId?: string;
}

export interface FcstmSemanticVariable {
    identity: FcstmSymbolIdentity;
    name: string;
    valueType: 'int' | 'float';
    initializer: FcstmAstExpression;
    ast: FcstmAstVariableDefinition;
    range: TextRange;
}

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

export interface FcstmSemanticEventReference {
    scope: 'local' | 'chain' | 'absolute';
    rawText: string;
    range: TextRange;
    eventId: string;
    normalizedPath: string[];
    qualifiedName: string;
    absolutePathText?: string;
}

export interface FcstmSemanticActionReference {
    rawPath: string;
    range: TextRange;
    targetActionId?: string;
    targetQualifiedName?: string;
    resolved: boolean;
}

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

export interface FcstmExpandedForceTransition {
    sourceStateId: string;
    sourceStatePath: string[];
    mode: 'direct' | 'exitToParent';
    targetKind: 'state' | 'exit';
    targetStateId?: string;
    targetStatePath?: string[];
}

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

export interface FcstmSemanticSummary {
    rootStateName?: string;
    explicitVariables: string[];
    absoluteEvents: string[];
}

export interface FcstmSemanticLookups {
    statesByPath: Record<string, FcstmSemanticState>;
    actionsByPath: Record<string, FcstmSemanticAction>;
    eventsByQualifiedName: Record<string, FcstmSemanticEvent>;
    importsByPath: Record<string, FcstmSemanticImport>;
}

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

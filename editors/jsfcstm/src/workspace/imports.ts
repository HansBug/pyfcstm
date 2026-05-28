import * as path from 'path';
import {pathToFileURL} from 'node:url';

import type {FcstmSemanticDocument, FcstmSemanticImport} from '../semantics';
import {
    createRange,
    FcstmDiagnostic,
    getDocumentFilePath,
    rangeContains,
    TextDocumentLike,
    TextPositionLike,
    TextRange,
} from '../utils/text';
import {FCSTM_DIAGNOSTIC_CODES} from '../editor/analyzers';
import {
    type FcstmImportCycle,
    type FcstmWorkspaceGraph,
    getWorkspaceGraph,
    resolveImportReference,
} from './graph';

export interface ImportEntry {
    sourcePath: string;
    alias: string;
    extraName?: string;
    statePath: string[];
    pathRange: TextRange;
    aliasRange: TextRange;
    statementRange: TextRange;
}

export interface ParsedDocumentInfo {
    imports: ImportEntry[];
    explicitVariables: string[];
    rootStateName?: string;
    absoluteEvents: string[];
}

export interface ResolvedImportTarget {
    sourcePath: string;
    resolvedFile?: string;
    exists: boolean;
    entryFile?: string;
    missing: boolean;
    rootStateName?: string;
    absoluteEvents: string[];
    explicitVariables: string[];
}

export interface ImportCycle {
    files: string[];
}

function fallbackImportRange(): TextRange {
    return createRange(0, 0, 0, 1);
}

function toFileUri(filePath: string): string {
    return filePath ? pathToFileURL(filePath).toString() : 'untitled:fcstm';
}

function toImportEntry(semanticImport: FcstmSemanticImport): ImportEntry {
    return {
        sourcePath: semanticImport.sourcePath,
        alias: semanticImport.alias,
        extraName: semanticImport.displayName,
        statePath: semanticImport.ownerStatePath,
        pathRange: semanticImport.pathRange,
        aliasRange: semanticImport.aliasRange,
        statementRange: semanticImport.range,
    };
}

function toResolvedImportTarget(semanticImport: FcstmSemanticImport): ResolvedImportTarget {
    return {
        sourcePath: semanticImport.sourcePath,
        resolvedFile: semanticImport.resolvedFile,
        exists: semanticImport.exists,
        entryFile: semanticImport.entryFile,
        missing: semanticImport.missing,
        rootStateName: semanticImport.targetRootStateName,
        absoluteEvents: [...semanticImport.mappedAbsoluteEvents],
        explicitVariables: [...semanticImport.mappedVariables],
    };
}

function toParsedDocumentInfo(semantic: FcstmSemanticDocument | null): ParsedDocumentInfo {
    if (!semantic) {
        return {
            imports: [],
            explicitVariables: [],
            absoluteEvents: [],
        };
    }

    return {
        imports: semantic.imports.map(toImportEntry),
        explicitVariables: [...semantic.summary.explicitVariables],
        rootStateName: semantic.summary.rootStateName,
        absoluteEvents: [...semantic.summary.absoluteEvents],
    };
}

function normalizeFile(filePath: string): string {
    return path.normalize(path.resolve(filePath));
}

export class FcstmImportWorkspaceIndex {
    constructor(private readonly graph: FcstmWorkspaceGraph = getWorkspaceGraph()) {}

    async parseDocument(document: TextDocumentLike): Promise<ParsedDocumentInfo> {
        const semantic = await this.graph.getSemanticDocument(document);
        return toParsedDocumentInfo(semantic);
    }

    async resolveImportsForDocument(document: TextDocumentLike): Promise<ResolvedImportTarget[]> {
        const semantic = await this.graph.getSemanticDocument(document);
        return semantic ? semantic.imports.map(toResolvedImportTarget) : [];
    }

    async getResolvedImportAtPosition(
        document: TextDocumentLike,
        position: TextPositionLike
    ): Promise<{ entry: ImportEntry; target: ResolvedImportTarget } | null> {
        const semantic = await this.graph.getSemanticDocument(document);
        if (!semantic) {
            return null;
        }

        const targetImport = semantic.imports.find(item => (
            rangeContains(item.pathRange, position)
            || rangeContains(item.aliasRange, position)
        ));
        if (!targetImport) {
            return null;
        }

        return {
            entry: toImportEntry(targetImport),
            target: toResolvedImportTarget(targetImport),
        };
    }

    async collectImportDiagnostics(document: TextDocumentLike): Promise<FcstmDiagnostic[]> {
        const diagnostics: FcstmDiagnostic[] = [];
        const ownerFile = getDocumentFilePath(document);
        const snapshot = await this.graph.buildSnapshotForDocument(document);
        const semantic = snapshot.nodes[snapshot.rootFile]?.semantic;
        if (!semantic) {
            return diagnostics;
        }

        // Build a name → state lookup per composite scope so we can
        // detect "import alias clashes with a sibling regular state",
        // matching pyfcstm/model/imports.py:_resolve_import_node_into_state.
        const siblingNamesByScope = new Map<string, Map<string, {name: string; range: typeof semanticImport.aliasRange}>>();
        type ImportLike = typeof semantic.imports[number];
        let semanticImport!: ImportLike;
        for (const state of semantic.states ?? []) {
            const ownerPath = state.identity.qualifiedName.split('.').slice(0, -1).join('.');
            const scopeKey = ownerPath || '<root>';
            let bucket = siblingNamesByScope.get(scopeKey);
            if (!bucket) {
                bucket = new Map();
                siblingNamesByScope.set(scopeKey, bucket);
            }
            bucket.set(state.name, {name: state.name, range: state.range});
        }

        const stateAliasSeen = new Map<string, Map<string, FcstmSemanticImport>>();
        for (semanticImport of semantic.imports) {
            const stateKey = semanticImport.ownerStatePath.join('.') || '<root>';
            let aliasMap = stateAliasSeen.get(stateKey);
            if (!aliasMap) {
                aliasMap = new Map<string, FcstmSemanticImport>();
                stateAliasSeen.set(stateKey, aliasMap);
            }

            const firstAlias = aliasMap.get(semanticImport.alias);
            if (firstAlias) {
                diagnostics.push({
                    range: semanticImport.aliasRange,
                    message: `Duplicate import alias ${JSON.stringify(semanticImport.alias)} in state ${JSON.stringify(stateKey)}.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.importAliasConflict,
                    relatedInformation: [{
                        location: {
                            uri: toFileUri(ownerFile),
                            range: firstAlias.aliasRange,
                        },
                        message: `First declaration of alias ${JSON.stringify(semanticImport.alias)} is here.`,
                    }],
                });
            } else {
                aliasMap.set(semanticImport.alias, semanticImport);
            }

            // Check alias vs sibling regular-state name.
            const scopeKey = stateKey;
            const siblings = siblingNamesByScope.get(scopeKey);
            const conflictingState = siblings?.get(semanticImport.alias);
            if (conflictingState) {
                diagnostics.push({
                    range: semanticImport.aliasRange,
                    message: `Import alias ${JSON.stringify(semanticImport.alias)} conflicts with an existing child state in ${JSON.stringify(stateKey)}.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.importAliasConflict,
                    relatedInformation: [{
                        location: {
                            uri: toFileUri(ownerFile),
                            range: conflictingState.range,
                        },
                        message: `Existing state ${JSON.stringify(conflictingState.name)} is declared here.`,
                    }],
                });
            }

            if (semanticImport.missing) {
                diagnostics.push({
                    range: semanticImport.pathRange,
                    message: `Import source ${JSON.stringify(semanticImport.sourcePath)} cannot be resolved from ${JSON.stringify(path.dirname(ownerFile))}.`,
                    severity: 'error',
                    source: 'fcstm',
                    code: FCSTM_DIAGNOSTIC_CODES.importNotFound,
                });
            }
        }

        for (const cycle of snapshot.cycles) {
            const firstHop = cycle.files[1];
            const cycleImport = semantic.imports.find(item => item.entryFile && normalizeFile(item.entryFile) === firstHop);
            diagnostics.push({
                range: cycleImport?.pathRange || fallbackImportRange(),
                message: `Circular import detected: ${cycle.files.map(item => path.basename(item)).join(' -> ')}.`,
                // pyfcstm imports.py reports circular imports as a hard
                // failure (SyntaxError); Layer 2 aligns to error severity
                // so jsfcstm and pyfcstm agree on the blocking nature.
                severity: 'error',
                source: 'fcstm',
                code: FCSTM_DIAGNOSTIC_CODES.importCircular,
            });
        }

        return diagnostics;
    }
}

let workspaceIndexInstance: FcstmImportWorkspaceIndex | null = null;

export function getImportWorkspaceIndex(): FcstmImportWorkspaceIndex {
    if (!workspaceIndexInstance) {
        workspaceIndexInstance = new FcstmImportWorkspaceIndex();
    }

    return workspaceIndexInstance;
}

export {getWorkspaceGraph, resolveImportReference};
export type {FcstmImportCycle};

import * as path from 'path';

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

        const targetImport = semantic.imports.find(item => rangeContains(item.pathRange, position));
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

        const stateAliasSeen = new Map<string, Set<string>>();
        for (const semanticImport of semantic.imports) {
            const stateKey = semanticImport.ownerStatePath.join('.') || '<root>';
            let aliasSet = stateAliasSeen.get(stateKey);
            if (!aliasSet) {
                aliasSet = new Set<string>();
                stateAliasSeen.set(stateKey, aliasSet);
            }

            if (aliasSet.has(semanticImport.alias)) {
                diagnostics.push({
                    range: semanticImport.aliasRange,
                    message: `Duplicate import alias ${JSON.stringify(semanticImport.alias)} in state ${JSON.stringify(stateKey)}.`,
                    severity: 'error',
                    source: 'fcstm',
                });
            } else {
                aliasSet.add(semanticImport.alias);
            }

            if (semanticImport.missing) {
                diagnostics.push({
                    range: semanticImport.pathRange,
                    message: `Import source ${JSON.stringify(semanticImport.sourcePath)} cannot be resolved from ${JSON.stringify(path.dirname(ownerFile))}.`,
                    severity: 'error',
                    source: 'fcstm',
                });
            }
        }

        for (const cycle of snapshot.cycles) {
            const firstHop = cycle.files[1];
            const cycleImport = semantic.imports.find(item => item.entryFile && normalizeFile(item.entryFile) === firstHop);
            diagnostics.push({
                range: cycleImport?.pathRange || fallbackImportRange(),
                message: `Circular import detected: ${cycle.files.map(item => path.basename(item)).join(' -> ')}.`,
                severity: 'warning',
                source: 'fcstm',
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

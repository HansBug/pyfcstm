import * as vscode from 'vscode';
import {
    FcstmImportWorkspaceIndex as CoreImportWorkspaceIndex,
    getImportWorkspaceIndex as getCoreImportWorkspaceIndex,
    type ImportEntry as CoreImportEntry,
    type ParsedDocumentInfo as CoreParsedDocumentInfo,
    type ResolvedImportTarget,
} from '@pyfcstm/jsfcstm';
import {toVscodeDiagnostic, toVscodeRange} from './vscode-converters';

export interface ImportEntry extends Omit<CoreImportEntry, 'pathRange' | 'aliasRange' | 'statementRange'> {
    pathRange: vscode.Range;
    aliasRange: vscode.Range;
    statementRange: vscode.Range;
}

export interface ParsedDocumentInfo extends Omit<CoreParsedDocumentInfo, 'imports'> {
    imports: ImportEntry[];
}

function toImportEntry(entry: CoreImportEntry): ImportEntry {
    return {
        ...entry,
        pathRange: toVscodeRange(entry.pathRange),
        aliasRange: toVscodeRange(entry.aliasRange),
        statementRange: toVscodeRange(entry.statementRange),
    };
}

export class FcstmImportWorkspaceIndex {
    private readonly core: CoreImportWorkspaceIndex;

    constructor(core?: CoreImportWorkspaceIndex) {
        this.core = core || new CoreImportWorkspaceIndex();
    }

    async parseDocument(document: vscode.TextDocument): Promise<ParsedDocumentInfo> {
        const parsed = await this.core.parseDocument(document);
        return {
            ...parsed,
            imports: parsed.imports.map(item => toImportEntry(item)),
        };
    }

    async resolveImportsForDocument(document: vscode.TextDocument): Promise<ResolvedImportTarget[]> {
        return this.core.resolveImportsForDocument(document);
    }

    async getResolvedImportAtPosition(
        document: vscode.TextDocument,
        position: vscode.Position
    ): Promise<{ entry: ImportEntry; target: ResolvedImportTarget } | null> {
        const resolved = await this.core.getResolvedImportAtPosition(document, position);
        if (!resolved) {
            return null;
        }

        return {
            entry: toImportEntry(resolved.entry),
            target: resolved.target,
        };
    }

    async collectImportDiagnostics(document: vscode.TextDocument): Promise<vscode.Diagnostic[]> {
        const diagnostics = await this.core.collectImportDiagnostics(document);
        return diagnostics.map(item => toVscodeDiagnostic(item));
    }
}

let workspaceIndexInstance: FcstmImportWorkspaceIndex | null = null;

export function getImportWorkspaceIndex(): FcstmImportWorkspaceIndex {
    if (!workspaceIndexInstance) {
        workspaceIndexInstance = new FcstmImportWorkspaceIndex(getCoreImportWorkspaceIndex());
    }
    return workspaceIndexInstance;
}

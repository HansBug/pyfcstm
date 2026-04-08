import {fileURLToPath} from 'node:url';

import {
    CodeAction,
    CancellationToken,
    CompletionItem,
    Diagnostic,
    DocumentHighlight,
    DocumentLink,
    DocumentSymbol,
    Hover,
    InitializeResult,
    Location,
    Position,
    Range,
    ServerCapabilities,
    SymbolInformation,
    TextDocumentContentChangeEvent,
    TextDocumentItem,
    TextDocumentSyncKind,
    WorkspaceEdit,
    WorkspaceFolder,
} from 'vscode-languageserver/node';
import {TextDocument} from 'vscode-languageserver-textdocument';

import {getJsFcstmPackageInfo} from '../config';
import {
    collectCodeActions,
    collectCompletionItems,
    collectDocumentDiagnostics,
    collectDocumentHighlights,
    collectDocumentLinks,
    collectDocumentSymbols,
    collectReferences,
    collectWorkspaceSymbols,
    planRename,
    prepareRename,
    resolveDefinitionLocation,
    resolveHover,
} from '../editor';
import type {TextDocumentLike} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {
    toLspCompletionItem,
    toLspCodeAction,
    toLspDiagnostic,
    toLspDocumentHighlight,
    toLspDocumentLink,
    toLspDocumentSymbol,
    toLspHover,
    toLspLocation,
    toLspWorkspaceEdit,
    toLspWorkspaceSymbol,
} from './converters';

export interface FcstmPublishedDiagnostics {
    uri: string;
    version: number;
    diagnostics: Diagnostic[];
}

export type FcstmTimerHandle = unknown;

export interface FcstmLanguageServerScheduler {
    setTimeout(callback: () => void | Promise<void>, delayMs: number): FcstmTimerHandle;
    clearTimeout(timer: FcstmTimerHandle): void;
}

export interface FcstmLanguageServerCoreOptions {
    debounceMs?: number;
    onDiagnostics?: (publication: FcstmPublishedDiagnostics) => void | Promise<void>;
    scheduler?: FcstmLanguageServerScheduler;
}

interface ManagedTimer {
    uri: string;
    version: number;
    handle: FcstmTimerHandle;
}

function createScheduler(): FcstmLanguageServerScheduler {
    return {
        setTimeout(callback, delayMs) {
            return setTimeout(() => {
                void callback();
            }, delayMs);
        },
        clearTimeout(timer) {
            clearTimeout(timer as NodeJS.Timeout);
        },
    };
}

function uriToFilePath(uri: string): string | undefined {
    if (!uri.startsWith('file:')) {
        return undefined;
    }

    try {
        return fileURLToPath(uri);
    } catch {
        return undefined;
    }
}

function toDocumentLike(document: TextDocument): TextDocumentLike {
    const text = document.getText();
    const lines = text.split('\n');
    const filePath = uriToFilePath(document.uri);

    return {
        filePath,
        uri: filePath ? {fsPath: filePath} : undefined,
        lineCount: lines.length,
        getText() {
            return text;
        },
        lineAt(line: number) {
            return {
                text: lines[line] || '',
            };
        },
    };
}

function shouldCancel(token?: CancellationToken): boolean {
    return Boolean(token?.isCancellationRequested);
}

/**
 * Protocol-neutral FCSTM language server core.
 *
 * This class owns text-document sync, debounce, workspace-folder tracking,
 * and request dispatch, but it does not depend on the VSCode extension host.
 */
export class FcstmLanguageServerCore {
    private readonly documents = new Map<string, TextDocument>();
    private readonly diagnosticsTimers = new Map<string, ManagedTimer>();
    private readonly workspaceFolders = new Map<string, WorkspaceFolder>();
    private readonly debounceMs: number;
    private readonly scheduler: FcstmLanguageServerScheduler;
    private readonly onDiagnostics: (publication: FcstmPublishedDiagnostics) => void | Promise<void>;

    constructor(options: FcstmLanguageServerCoreOptions = {}) {
        this.debounceMs = options.debounceMs ?? 300;
        this.scheduler = options.scheduler || createScheduler();
        this.onDiagnostics = options.onDiagnostics || (() => undefined);
    }

    getInitializeResult(): InitializeResult {
        const packageInfo = getJsFcstmPackageInfo();
        return {
            capabilities: this.getServerCapabilities(),
            serverInfo: {
                name: packageInfo.name,
                version: packageInfo.version,
            },
        };
    }

    getServerCapabilities(): ServerCapabilities {
        return {
            textDocumentSync: TextDocumentSyncKind.Incremental,
            documentSymbolProvider: true,
            completionProvider: {
                resolveProvider: false,
                triggerCharacters: ['.', ':', '/'],
            },
            hoverProvider: true,
            definitionProvider: true,
            referencesProvider: true,
            documentHighlightProvider: true,
            renameProvider: {
                prepareProvider: true,
            },
            documentLinkProvider: {
                resolveProvider: false,
            },
            workspaceSymbolProvider: true,
            codeActionProvider: true,
            workspace: {
                workspaceFolders: {
                    supported: true,
                    changeNotifications: true,
                },
            },
        };
    }

    async openTextDocument(
        textDocument: TextDocumentItem,
        token?: CancellationToken
    ): Promise<void> {
        const document = TextDocument.create(
            textDocument.uri,
            textDocument.languageId,
            textDocument.version,
            textDocument.text
        );
        this.documents.set(textDocument.uri, document);
        this.syncOverlay(document);
        await this.publishDiagnostics(textDocument.uri, document.version, token);
    }

    async changeTextDocument(
        uri: string,
        version: number,
        contentChanges: TextDocumentContentChangeEvent[]
    ): Promise<void> {
        const currentDocument = this.documents.get(uri);
        if (!currentDocument) {
            return;
        }

        const updatedDocument = TextDocument.update(currentDocument, contentChanges, version);
        this.documents.set(uri, updatedDocument);
        this.syncOverlay(updatedDocument);
        this.scheduleDiagnostics(uri, version);
    }

    async saveTextDocument(uri: string, token?: CancellationToken): Promise<void> {
        const document = this.documents.get(uri);
        if (!document) {
            return;
        }

        this.syncOverlay(document);
        await this.publishDiagnostics(uri, document.version, token);
    }

    async closeTextDocument(uri: string): Promise<void> {
        this.clearDiagnosticsTimer(uri);
        const document = this.documents.get(uri);
        if (document) {
            this.removeOverlay(document.uri);
        }
        this.documents.delete(uri);
        await this.onDiagnostics({
            uri,
            version: 0,
            diagnostics: [],
        });
    }

    async setWorkspaceFolders(workspaceFolders: WorkspaceFolder[]): Promise<void> {
        this.workspaceFolders.clear();
        for (const folder of workspaceFolders) {
            this.workspaceFolders.set(folder.uri, folder);
        }

        await this.revalidateOpenDocuments();
    }

    async applyWorkspaceFolderChange(
        added: WorkspaceFolder[],
        removed: WorkspaceFolder[]
    ): Promise<void> {
        for (const folder of removed) {
            this.workspaceFolders.delete(folder.uri);
        }
        for (const folder of added) {
            this.workspaceFolders.set(folder.uri, folder);
        }

        await this.revalidateOpenDocuments();
    }

    getTrackedWorkspaceFolders(): WorkspaceFolder[] {
        return [...this.workspaceFolders.values()];
    }

    hasDocument(uri: string): boolean {
        return this.documents.has(uri);
    }

    async provideDocumentSymbols(
        uri: string,
        token?: CancellationToken
    ): Promise<DocumentSymbol[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const symbols = await collectDocumentSymbols(document);
        if (shouldCancel(token)) {
            return [];
        }

        return symbols.map(item => toLspDocumentSymbol(item));
    }

    async provideCompletionItems(
        uri: string,
        position: Position,
        token?: CancellationToken
    ): Promise<CompletionItem[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const items = await collectCompletionItems(document, position);
        if (shouldCancel(token)) {
            return [];
        }

        return items.map(item => toLspCompletionItem(item));
    }

    async provideHover(
        uri: string,
        position: Position,
        token?: CancellationToken
    ): Promise<Hover | null> {
        if (shouldCancel(token)) {
            return null;
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return null;
        }

        const hover = await resolveHover(document, position);
        if (!hover || shouldCancel(token)) {
            return null;
        }

        return toLspHover(hover);
    }

    async provideDefinition(
        uri: string,
        position: Position,
        token?: CancellationToken
    ): Promise<Location[] | null> {
        if (shouldCancel(token)) {
            return null;
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return null;
        }

        const definition = await resolveDefinitionLocation(document, position);
        if (!definition || shouldCancel(token)) {
            return null;
        }

        return [toLspLocation(definition)];
    }

    async provideReferences(
        uri: string,
        position: Position,
        includeDeclaration: boolean,
        token?: CancellationToken
    ): Promise<Location[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const references = await collectReferences(document, position, includeDeclaration);
        if (shouldCancel(token)) {
            return [];
        }

        return references.map(item => toLspLocation(item));
    }

    async provideDocumentHighlights(
        uri: string,
        position: Position,
        token?: CancellationToken
    ): Promise<DocumentHighlight[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const highlights = await collectDocumentHighlights(document, position);
        if (shouldCancel(token)) {
            return [];
        }

        return highlights.map(item => toLspDocumentHighlight(item));
    }

    async providePrepareRename(
        uri: string,
        position: Position,
        token?: CancellationToken
    ): Promise<Range | null> {
        if (shouldCancel(token)) {
            return null;
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return null;
        }

        const rename = await prepareRename(document, position);
        if (!rename || shouldCancel(token)) {
            return null;
        }

        return toLspLocation({
            uri,
            range: rename.range,
        }).range;
    }

    async provideRename(
        uri: string,
        position: Position,
        newName: string,
        token?: CancellationToken
    ): Promise<WorkspaceEdit | null> {
        if (shouldCancel(token)) {
            return null;
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return null;
        }

        const edit = await planRename(document, position, newName);
        if (!edit || shouldCancel(token)) {
            return null;
        }

        return toLspWorkspaceEdit(edit);
    }

    async provideWorkspaceSymbols(
        query: string,
        token?: CancellationToken
    ): Promise<SymbolInformation[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const symbols = await collectWorkspaceSymbols(this.getOpenDocuments(), query);
        if (shouldCancel(token)) {
            return [];
        }

        return symbols.map(item => toLspWorkspaceSymbol(item));
    }

    async provideDocumentLinks(
        uri: string,
        token?: CancellationToken
    ): Promise<DocumentLink[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const links = await collectDocumentLinks(document);
        if (shouldCancel(token)) {
            return [];
        }

        return links.map(item => toLspDocumentLink(item));
    }

    async provideCodeActions(
        uri: string,
        range: Range,
        diagnostics: Diagnostic[],
        token?: CancellationToken
    ): Promise<CodeAction[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const actions = await collectCodeActions(document, range, diagnostics.map(item => ({
            range: item.range,
            message: item.message,
            severity: item.severity === 1 ? 'error' : 'warning',
            source: item.source || 'fcstm',
            code: item.code ? String(item.code) : undefined,
            data: item.data as Record<string, unknown> | undefined,
        })));
        if (shouldCancel(token)) {
            return [];
        }

        return actions.map(item => toLspCodeAction(item));
    }

    dispose(): void {
        for (const uri of [...this.diagnosticsTimers.keys()]) {
            this.clearDiagnosticsTimer(uri);
        }
        for (const document of this.documents.values()) {
            this.removeOverlay(document.uri);
        }
        this.documents.clear();
        this.workspaceFolders.clear();
    }

    private getDocumentLike(uri: string): TextDocumentLike | undefined {
        const document = this.documents.get(uri);
        return document ? toDocumentLike(document) : undefined;
    }

    private getOpenDocuments(): TextDocumentLike[] {
        return [...this.documents.values()].map(item => toDocumentLike(item));
    }

    private scheduleDiagnostics(uri: string, version: number): void {
        this.clearDiagnosticsTimer(uri);

        const handle = this.scheduler.setTimeout(async () => {
            this.diagnosticsTimers.delete(uri);
            await this.publishDiagnostics(uri, version);
        }, this.debounceMs);

        this.diagnosticsTimers.set(uri, {uri, version, handle});
    }

    private syncOverlay(document: TextDocument): void {
        const filePath = uriToFilePath(document.uri);
        if (!filePath) {
            return;
        }

        getWorkspaceGraph().setOverlay(filePath, document.getText());
    }

    private removeOverlay(uri: string): void {
        const filePath = uriToFilePath(uri);
        if (!filePath) {
            return;
        }

        getWorkspaceGraph().removeOverlay(filePath);
    }

    private clearDiagnosticsTimer(uri: string): void {
        const timer = this.diagnosticsTimers.get(uri);
        if (!timer) {
            return;
        }

        this.scheduler.clearTimeout(timer.handle);
        this.diagnosticsTimers.delete(uri);
    }

    private async revalidateOpenDocuments(): Promise<void> {
        for (const document of this.documents.values()) {
            await this.publishDiagnostics(document.uri, document.version);
        }
    }

    private async publishDiagnostics(
        uri: string,
        expectedVersion: number,
        token?: CancellationToken
    ): Promise<void> {
        if (shouldCancel(token)) {
            return;
        }

        const document = this.documents.get(uri);
        if (!document || document.version !== expectedVersion) {
            return;
        }

        const diagnostics = await collectDocumentDiagnostics(toDocumentLike(document));
        if (shouldCancel(token)) {
            return;
        }

        const currentDocument = this.documents.get(uri);
        if (!currentDocument || currentDocument.version !== expectedVersion) {
            return;
        }

        await this.onDiagnostics({
            uri,
            version: expectedVersion,
            diagnostics: diagnostics.map(item => toLspDiagnostic(item)),
        });
    }
}

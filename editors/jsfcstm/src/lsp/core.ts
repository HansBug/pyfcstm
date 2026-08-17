import * as path from 'node:path';
import {fileURLToPath} from 'node:url';

import {
    CodeAction,
    CancellationToken,
    CompletionItem,
    Diagnostic,
    DocumentHighlight,
    DocumentLink,
    DocumentSymbol,
    FoldingRange,
    FormattingOptions,
    Hover,
    InitializeResult,
    Location,
    Position,
    Range,
    SelectionRange,
    SemanticTokens,
    ServerCapabilities,
    SymbolInformation,
    TextDocumentContentChangeEvent,
    TextDocumentItem,
    TextDocumentSyncKind,
    TextEdit,
    WorkspaceEdit,
    WorkspaceFolder,
} from 'vscode-languageserver/node';
import {TextDocument} from 'vscode-languageserver-textdocument';

import {getJsFcstmPackageInfo} from '../config';
import {
    collectCodeActions,
    collectCompletionItems,
    collectDocumentDiagnosticsByUri,
    collectDocumentHighlights,
    collectDocumentLinks,
    collectDocumentSymbols,
    collectFoldingRanges,
    collectReferences,
    collectSelectionRanges,
    collectSemanticTokens,
    collectWorkspaceSymbols,
    formatDocumentText,
    getFcstmSemanticTokensLegend,
    planRename,
    prepareRename,
    resolveDefinitionLocation,
    resolveHover,
} from '../editor';
import type {FcstmFormatOptions} from '../editor/formatter';
import type {TextDocumentLike} from '../utils/text';
import {getWorkspaceGraph} from '../workspace';
import {
    toLspCompletionItem,
    toLspCodeAction,
    toLspDiagnostic,
    toLspDocumentHighlight,
    toLspDocumentLink,
    toLspDocumentSymbol,
    toLspFoldingRange,
    toLspHover,
    toLspLocation,
    toLspRange,
    toLspSelectionRange,
    toLspSemanticTokens,
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
    collectDocumentDiagnostics?: typeof collectDocumentDiagnosticsByUri;
    formatOptions?: FcstmFormatOptions;
}

interface ManagedTimer {
    uri: string;
    version: number;
    handle: FcstmTimerHandle;
}

const FCSTM_COMPLETION_TRIGGER_CHARACTERS = [
    '.', ':', '/',
    ...'ABCDEFGHIJKLMNOPQRSTUVWXYZ',
    ...'abcdefghijklmnopqrstuvwxyz',
    '_',
];

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
    } catch (err) {
        // Node's fileURLToPath throws TypeError (subclass: ERR_INVALID_URL_SCHEME,
        // ERR_INVALID_FILE_URL_HOST, ERR_INVALID_FILE_URL_PATH) for any URI
        // that fails the file:// validation rules. Treat those as "uri is
        // not a usable filesystem path" and return undefined; anything
        // outside that class is a programmer bug and must surface.
        if (!(err instanceof TypeError)) {
            throw err;
        }
        return undefined;
    }
}

function normalizeFilePath(filePath: string): string {
    return path.normalize(path.resolve(filePath));
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

function diagnosticContributionKey(diagnostic: Diagnostic): string {
    if (
        diagnostic.code === 'W_UNREACHABLE_TRANSITION'
        && diagnostic.data
        && typeof diagnostic.data === 'object'
        && !Array.isArray(diagnostic.data)
    ) {
        const data = diagnostic.data as Record<string, unknown>;
        const reason = data.reason;
        const sourcePath = data.source_path;
        if (typeof reason === 'string' && typeof sourcePath === 'string') {
            // Host-assembled and child-local topology findings may differ in
            // projected paths, messages, and transition indexes. The authored
            // source span plus authored topology endpoints is their stable
            // identity, while reason prevents unrelated topology findings on
            // that span from collapsing. Do not use transition_index here:
            // assembled and standalone models can number the same transition
            // differently.
            return JSON.stringify([
                diagnostic.code,
                reason,
                sourcePath,
                diagnostic.range,
                data.from_path ?? null,
                data.to_path ?? null,
                data.source_state_path ?? null,
                data.selection_owner_path ?? null,
                data.forced_origin ?? null,
                data.combo_origin_ids ?? [],
                data.mount_path ?? null,
            ]);
        }
    }
    return JSON.stringify([
        diagnostic.code ?? null,
        diagnostic.severity ?? null,
        diagnostic.source ?? null,
        diagnostic.range,
        diagnostic.data ?? null,
        diagnostic.relatedInformation ?? null,
    ]);
}

function unreachableTransitionAuthoredKey(diagnostic: Diagnostic): string | null {
    if (
        diagnostic.code !== 'W_UNREACHABLE_TRANSITION'
        || !diagnostic.data
        || typeof diagnostic.data !== 'object'
        || Array.isArray(diagnostic.data)
    ) {
        return null;
    }
    const data = diagnostic.data as Record<string, unknown>;
    if (typeof data.reason !== 'string' || typeof data.source_path !== 'string') {
        return null;
    }
    // This identity deliberately ignores projected paths and mount_path. A
    // local child result and its assembled host result describe one authored
    // transition, while distinct mount_path values describe distinct runtime
    // instances that must remain visible.
    return JSON.stringify([
        diagnostic.code,
        data.reason,
        data.source_path,
        diagnostic.range,
        data.forced_origin ?? null,
        data.combo_origin_ids ?? [],
    ]);
}

function isAssembledMountDiagnostic(diagnostic: Diagnostic): boolean {
    if (
        diagnostic.code !== 'W_UNREACHABLE_TRANSITION'
        || !diagnostic.data
        || typeof diagnostic.data !== 'object'
        || Array.isArray(diagnostic.data)
    ) {
        return false;
    }
    const mountPath = (diagnostic.data as Record<string, unknown>).mount_path;
    return typeof mountPath === 'string' && mountPath.length > 0;
}

/**
 * Protocol-neutral FCSTM language server core.
 *
 * This class owns text-document sync, debounce, workspace-folder tracking,
 * and request dispatch, but it does not depend on the VSCode extension host.
 */
export class FcstmLanguageServerCore {
    private readonly documents = new Map<string, TextDocument>();
    private readonly diagnosticContributions = new Map<string, Map<string, Diagnostic[]>>();
    private readonly diagnosticGenerations = new Map<string, number>();
    private readonly diagnosticsTimers = new Map<string, ManagedTimer>();
    private readonly workspaceFolders = new Map<string, WorkspaceFolder>();
    private readonly debounceMs: number;
    private readonly scheduler: FcstmLanguageServerScheduler;
    private readonly collectDocumentDiagnostics: typeof collectDocumentDiagnosticsByUri;
    private readonly onDiagnostics: (publication: FcstmPublishedDiagnostics) => void | Promise<void>;
    private formatOptions: FcstmFormatOptions;

    constructor(options: FcstmLanguageServerCoreOptions = {}) {
        this.debounceMs = options.debounceMs ?? 300;
        this.scheduler = options.scheduler || createScheduler();
        this.collectDocumentDiagnostics = options.collectDocumentDiagnostics || collectDocumentDiagnosticsByUri;
        this.onDiagnostics = options.onDiagnostics || (() => undefined);
        this.formatOptions = {...(options.formatOptions || {})};
    }

    /**
     * Update the formatter options held by the core. Clients should call
     * this when VSCode settings change (typically from a
     * ``workspace/didChangeConfiguration`` notification). Unspecified
     * fields fall back to the existing values so partial updates work.
     */
    setFormatOptions(options: FcstmFormatOptions): void {
        this.formatOptions = {...this.formatOptions, ...options};
    }

    getFormatOptions(): FcstmFormatOptions {
        return {...this.formatOptions};
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
                triggerCharacters: FCSTM_COMPLETION_TRIGGER_CHARACTERS,
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
            foldingRangeProvider: true,
            selectionRangeProvider: true,
            semanticTokensProvider: {
                legend: getFcstmSemanticTokensLegend(),
                full: true,
            },
            workspaceSymbolProvider: true,
            codeActionProvider: true,
            documentFormattingProvider: true,
            documentRangeFormattingProvider: true,
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
        await this.scheduleAffectedDiagnostics(textDocument.uri);
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
        await this.scheduleAffectedDiagnostics(uri);
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
        this.nextDiagnosticGeneration(uri);
        const document = this.documents.get(uri);
        if (document) {
            this.removeOverlay(document.uri);
        }
        this.documents.delete(uri);
        const previous = this.diagnosticContributions.get(uri);
        this.diagnosticContributions.delete(uri);
        const targets = new Set(previous?.keys() || []);
        if (targets.size === 0) targets.add(uri);
        await this.publishDiagnosticTargets(targets);
        await this.scheduleAffectedDiagnostics(uri);
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

    async provideFoldingRanges(
        uri: string,
        token?: CancellationToken
    ): Promise<FoldingRange[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const ranges = await collectFoldingRanges(document);
        if (shouldCancel(token)) {
            return [];
        }

        return ranges.map(item => toLspFoldingRange(item));
    }

    async provideSelectionRanges(
        uri: string,
        positions: Position[],
        token?: CancellationToken
    ): Promise<SelectionRange[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        const ranges = await collectSelectionRanges(document, positions);
        if (shouldCancel(token)) {
            return [];
        }

        return ranges.map(item => toLspSelectionRange(item));
    }

    async provideSemanticTokens(
        uri: string,
        token?: CancellationToken
    ): Promise<SemanticTokens> {
        if (shouldCancel(token)) {
            return {data: []};
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return {data: []};
        }

        const tokens = await collectSemanticTokens(document);
        if (shouldCancel(token)) {
            return {data: []};
        }

        return toLspSemanticTokens(tokens);
    }

    async provideDocumentFormatting(
        uri: string,
        options: FormattingOptions,
        token?: CancellationToken
    ): Promise<TextEdit[]> {
        if (shouldCancel(token)) {
            return [];
        }

        const document = this.getDocumentLike(uri);
        if (!document) {
            return [];
        }

        // Precedence: an explicit ``fcstm.format.indentSize`` setting wins;
        // otherwise fall back to the editor's ``tabSize`` (only honored when
        // the editor is inserting spaces).
        const configured = this.formatOptions.indentSize;
        const resolvedIndent = configured && configured > 0
            ? configured
            : (options.insertSpaces === false ? 4 : options.tabSize || 4);

        const edits = formatDocumentText(document, {
            ...this.formatOptions,
            indentSize: resolvedIndent,
        });
        if (shouldCancel(token)) {
            return [];
        }

        return edits.map(edit => ({
            range: toLspRange(edit.range),
            newText: edit.newText,
        }));
    }

    async provideDocumentRangeFormatting(
        uri: string,
        _range: Range,
        options: FormattingOptions,
        token?: CancellationToken
    ): Promise<TextEdit[]> {
        // The formatter only supports whole-document normalization. Clients
        // that request range formatting receive the same result as a full
        // format, which keeps indentation consistent across the range.
        return this.provideDocumentFormatting(uri, options, token);
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
            severity: item.severity === 1
                ? 'error'
                : item.severity === 3
                    ? 'info'
                    : 'warning',
            source: item.source || 'fcstm',
            code: item.code ? String(item.code) : undefined,
            data: item.data as Record<string, unknown> | undefined,
            relatedInformation: item.relatedInformation?.map(info => ({
                location: {
                    uri: info.location.uri,
                    range: info.location.range,
                },
                message: info.message,
            })),
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
        this.diagnosticContributions.clear();
        this.diagnosticGenerations.clear();
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
        const generation = this.nextDiagnosticGeneration(uri);

        const handle = this.scheduler.setTimeout(async () => {
            this.diagnosticsTimers.delete(uri);
            await this.publishDiagnostics(uri, version, undefined, generation);
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

    private nextDiagnosticGeneration(uri: string): number {
        const generation = (this.diagnosticGenerations.get(uri) || 0) + 1;
        this.diagnosticGenerations.set(uri, generation);
        return generation;
    }

    private async revalidateOpenDocuments(): Promise<void> {
        for (const document of this.documents.values()) {
            await this.publishDiagnostics(document.uri, document.version);
        }
    }

    private async scheduleAffectedDiagnostics(changedUri: string): Promise<void> {
        const changedFile = uriToFilePath(changedUri);
        if (!changedFile) return;

        const normalizedChangedFile = normalizeFilePath(changedFile);
        for (const document of this.documents.values()) {
            if (document.uri === changedUri) continue;

            const snapshot = await getWorkspaceGraph().buildSnapshotForDocument(toDocumentLike(document));
            if (!snapshot.order.includes(normalizedChangedFile)) continue;

            this.scheduleDiagnostics(document.uri, document.version);
        }
    }

    private async publishDiagnostics(
        uri: string,
        expectedVersion: number,
        token?: CancellationToken,
        expectedGeneration?: number,
    ): Promise<void> {
        if (shouldCancel(token)) {
            return;
        }

        const generation = expectedGeneration ?? this.nextDiagnosticGeneration(uri);

        const document = this.documents.get(uri);
        if (!document || document.version !== expectedVersion) {
            return;
        }

        const publications = await this.collectDocumentDiagnostics(toDocumentLike(document), uri);
        if (shouldCancel(token)) {
            return;
        }

        const currentDocument = this.documents.get(uri);
        if (
            !currentDocument
            || currentDocument.version !== expectedVersion
            || this.diagnosticGenerations.get(uri) !== generation
        ) {
            return;
        }

        const next = new Map<string, Diagnostic[]>();
        for (const [targetUri, diagnostics] of publications) {
            next.set(targetUri, diagnostics.map(item => toLspDiagnostic(item)));
        }
        const previous = this.diagnosticContributions.get(uri);
        const targets = new Set([
            ...(previous?.keys() || []),
            ...next.keys(),
        ]);
        this.diagnosticContributions.set(uri, next);
        await this.publishDiagnosticTargets(targets);
    }

    private async publishDiagnosticTargets(targets: Iterable<string>): Promise<void> {
        for (const targetUri of targets) {
            const diagnostics: Diagnostic[] = [];
            const seen = new Set<string>();
            const contributions = [...this.diagnosticContributions.values()]
                .flatMap(contribution => contribution.get(targetUri) || []);
            const assembledAuthoredKeys = new Set(
                contributions
                    .filter(isAssembledMountDiagnostic)
                    .map(unreachableTransitionAuthoredKey)
                    .filter((key): key is string => key !== null),
            );
            for (const diagnostic of contributions) {
                const authoredKey = unreachableTransitionAuthoredKey(diagnostic);
                if (
                    authoredKey !== null
                    && !isAssembledMountDiagnostic(diagnostic)
                    && assembledAuthoredKeys.has(authoredKey)
                ) {
                    // An assembled host result is authoritative for an
                    // imported transition when it is available. Keep the
                    // standalone child result only when no mount explains it.
                    continue;
                }
                const key = diagnosticContributionKey(diagnostic);
                if (seen.has(key)) continue;
                seen.add(key);
                diagnostics.push(diagnostic);
            }
            await this.onDiagnostics({
                uri: targetUri,
                version: this.documents.get(targetUri)?.version || 0,
                diagnostics,
            });
        }
    }
}

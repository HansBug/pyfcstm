import assert from 'node:assert/strict';
import * as path from 'node:path';
import {pathToFileURL} from 'node:url';

import {
    CodeActionKind,
    CompletionItemKind,
    DiagnosticSeverity,
    DocumentHighlightKind,
    InsertTextFormat,
    MarkupKind,
    SymbolKind,
} from 'vscode-languageserver/node';
import {TextDocument} from 'vscode-languageserver-textdocument';

import {
    packageModule,
    trackTempDir,
    withPatchedProperty,
    writeFile,
} from './support';

interface HandlerMap {
    initialize?: (params: { workspaceFolders?: Array<{ uri: string; name: string }> }) => Promise<unknown> | unknown;
    open?: (params: { textDocument: { uri: string; languageId: string; version: number; text: string } }) => Promise<void> | void;
    change?: (params: { textDocument: { uri: string; version: number }; contentChanges: Array<{ text: string }> }) => Promise<void> | void;
    save?: (params: { textDocument: { uri: string } }) => Promise<void> | void;
    close?: (params: { textDocument: { uri: string } }) => Promise<void> | void;
    symbol?: (params: { textDocument: { uri: string } }, token?: unknown) => Promise<unknown> | unknown;
    completion?: (params: { textDocument: { uri: string }; position: { line: number; character: number } }, token?: unknown) => Promise<unknown> | unknown;
    hover?: (params: { textDocument: { uri: string }; position: { line: number; character: number } }, token?: unknown) => Promise<unknown> | unknown;
    definition?: (params: { textDocument: { uri: string }; position: { line: number; character: number } }, token?: unknown) => Promise<unknown> | unknown;
    references?: (params: { textDocument: { uri: string }; position: { line: number; character: number }; context: { includeDeclaration: boolean } }, token?: unknown) => Promise<unknown> | unknown;
    highlights?: (params: { textDocument: { uri: string }; position: { line: number; character: number } }, token?: unknown) => Promise<unknown> | unknown;
    prepareRename?: (params: { textDocument: { uri: string }; position: { line: number; character: number } }, token?: unknown) => Promise<unknown> | unknown;
    rename?: (params: { textDocument: { uri: string }; position: { line: number; character: number }; newName: string }, token?: unknown) => Promise<unknown> | unknown;
    links?: (params: { textDocument: { uri: string } }, token?: unknown) => Promise<unknown> | unknown;
    folding?: (params: { textDocument: { uri: string } }, token?: unknown) => Promise<unknown> | unknown;
    selection?: (params: { textDocument: { uri: string }; positions: Array<{ line: number; character: number }> }, token?: unknown) => Promise<unknown> | unknown;
    semanticTokens?: (params: { textDocument: { uri: string } }, token?: unknown) => Promise<unknown> | unknown;
    workspaceSymbol?: (params: { query: string }, token?: unknown) => Promise<unknown> | unknown;
    codeAction?: (params: { textDocument: { uri: string }; range: { start: { line: number; character: number }; end: { line: number; character: number } }; context: { diagnostics: unknown[] } }, token?: unknown) => Promise<unknown> | unknown;
    initialized?: () => void;
    shutdown?: () => void;
}

class FakeConnection {
    readonly handlers: HandlerMap = {};
    readonly diagnostics: Array<{ uri: string; version?: number; diagnostics: unknown[] }> = [];
    workspaceFolderHandler?: (event: { added: Array<{ uri: string; name: string }>; removed: Array<{ uri: string; name: string }> }) => Promise<void> | void;
    listenCount = 0;

    readonly workspace = {
        onDidChangeWorkspaceFolders: (
            callback: (event: { added: Array<{ uri: string; name: string }>; removed: Array<{ uri: string; name: string }> }) => Promise<void> | void
        ) => {
            this.workspaceFolderHandler = callback;
        },
    };

    readonly languages = {
        semanticTokens: {
            on: (callback: HandlerMap['semanticTokens']) => {
                this.handlers.semanticTokens = callback;
            },
        },
    };

    sendDiagnostics(payload: { uri: string; version?: number; diagnostics: unknown[] }): void {
        this.diagnostics.push(payload);
    }

    listen(): void {
        this.listenCount += 1;
    }

    onInitialize(callback: HandlerMap['initialize']): void {
        this.handlers.initialize = callback;
    }

    onDidOpenTextDocument(callback: HandlerMap['open']): void {
        this.handlers.open = callback;
    }

    onDidChangeTextDocument(callback: HandlerMap['change']): void {
        this.handlers.change = callback;
    }

    onDidSaveTextDocument(callback: HandlerMap['save']): void {
        this.handlers.save = callback;
    }

    onDidCloseTextDocument(callback: HandlerMap['close']): void {
        this.handlers.close = callback;
    }

    onDocumentSymbol(callback: HandlerMap['symbol']): void {
        this.handlers.symbol = callback;
    }

    onCompletion(callback: HandlerMap['completion']): void {
        this.handlers.completion = callback;
    }

    onHover(callback: HandlerMap['hover']): void {
        this.handlers.hover = callback;
    }

    onDefinition(callback: HandlerMap['definition']): void {
        this.handlers.definition = callback;
    }

    onReferences(callback: HandlerMap['references']): void {
        this.handlers.references = callback;
    }

    onDocumentHighlight(callback: HandlerMap['highlights']): void {
        this.handlers.highlights = callback;
    }

    onPrepareRename(callback: HandlerMap['prepareRename']): void {
        this.handlers.prepareRename = callback;
    }

    onRenameRequest(callback: HandlerMap['rename']): void {
        this.handlers.rename = callback;
    }

    onDocumentLinks(callback: HandlerMap['links']): void {
        this.handlers.links = callback;
    }

    onFoldingRanges(callback: HandlerMap['folding']): void {
        this.handlers.folding = callback;
    }

    onSelectionRanges(callback: HandlerMap['selection']): void {
        this.handlers.selection = callback;
    }

    onWorkspaceSymbol(callback: HandlerMap['workspaceSymbol']): void {
        this.handlers.workspaceSymbol = callback;
    }

    onCodeAction(callback: HandlerMap['codeAction']): void {
        this.handlers.codeAction = callback;
    }

    onInitialized(callback: HandlerMap['initialized']): void {
        this.handlers.initialized = callback;
    }

    onShutdown(callback: HandlerMap['shutdown']): void {
        this.handlers.shutdown = callback;
    }
}

function toUri(filePath: string): string {
    return pathToFileURL(filePath).toString();
}

describe('jsfcstm lsp coverage support', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('covers navigation helpers and converter branches', async () => {
        const importIndex = packageModule.getImportWorkspaceIndex();
        const workspaceGraph = packageModule.getWorkspaceGraph();
        const document = {
            getText() {
                return 'state Root;';
            },
            lineCount: 1,
            lineAt() {
                return {text: 'state Root;'};
            },
            filePath: '/tmp/nav.fcstm',
            uri: {fsPath: '/tmp/nav.fcstm'},
        };

        const nullDefinition = await withPatchedProperty(
            importIndex,
            'getResolvedImportAtPosition',
            async () => null,
            async () => packageModule.resolveDefinitionLocation(document, {line: 0, character: 0})
        );
        assert.equal(nullDefinition, null);

        const resolvedDefinition = await withPatchedProperty(
            importIndex,
            'getResolvedImportAtPosition',
            async () => ({
                entry: {
                    sourcePath: './worker.fcstm',
                    alias: 'Worker',
                    statePath: [],
                    pathRange: packageModule.createRange(0, 0, 0, 10),
                    aliasRange: packageModule.createRange(0, 0, 0, 6),
                    statementRange: packageModule.createRange(0, 0, 0, 20),
                },
                target: {
                    sourcePath: './worker.fcstm',
                    exists: true,
                    missing: false,
                    entryFile: '/tmp/worker.fcstm',
                    absoluteEvents: [],
                    explicitVariables: [],
                },
            }),
            async () => packageModule.resolveDefinitionLocation(document, {line: 0, character: 0})
        );
        assert.equal(resolvedDefinition?.uri, toUri('/tmp/worker.fcstm'));

        const noSemanticLinks = await withPatchedProperty(
            workspaceGraph,
            'getSemanticDocument',
            async () => null,
            async () => packageModule.collectDocumentLinks(document)
        );
        assert.deepEqual(noSemanticLinks, []);

        const links = await withPatchedProperty(
            workspaceGraph,
            'getSemanticDocument',
            async () => ({
                imports: [
                    {
                        entryFile: undefined,
                        resolvedFile: undefined,
                        missing: false,
                        pathRange: packageModule.createRange(0, 0, 0, 1),
                    },
                    {
                        entryFile: undefined,
                        resolvedFile: '/tmp/fallback.fcstm',
                        missing: false,
                        targetRootStateName: undefined,
                        pathRange: packageModule.createRange(0, 1, 0, 2),
                    },
                    {
                        entryFile: '/tmp/worker.fcstm',
                        resolvedFile: '/tmp/worker.fcstm',
                        missing: false,
                        targetRootStateName: 'WorkerRoot',
                        pathRange: packageModule.createRange(0, 2, 0, 3),
                    },
                    {
                        entryFile: '/tmp/missing.fcstm',
                        resolvedFile: '/tmp/missing.fcstm',
                        missing: true,
                        pathRange: packageModule.createRange(0, 3, 0, 4),
                    },
                ],
            }),
            async () => packageModule.collectDocumentLinks(document)
        );
        assert.equal(links.length, 2);
        assert.equal(links[0].target, toUri('/tmp/fallback.fcstm'));
        assert.equal(links[0].tooltip, 'Open imported module');
        assert.equal(links[1].target, toUri('/tmp/worker.fcstm'));
        assert.equal(links[1].tooltip, 'Open imported module WorkerRoot');

        const errorDiagnostic = packageModule.toLspDiagnostic({
            range: packageModule.createRange(0, 0, 0, 1),
            message: 'Broken',
            severity: 'error',
            source: 'fcstm',
            relatedInformation: [{
                location: {
                    uri: toUri('/tmp/original.fcstm'),
                    range: packageModule.createRange(1, 0, 1, 5),
                },
                message: 'Original diagnostic anchor',
            }],
        });
        const warningDiagnostic = packageModule.toLspDiagnostic({
            range: packageModule.createRange(0, 1, 0, 2),
            message: 'Warn',
            severity: 'warning',
            source: 'fcstm',
        });
        assert.equal(errorDiagnostic.severity, DiagnosticSeverity.Error);
        assert.equal(warningDiagnostic.severity, DiagnosticSeverity.Warning);
        assert.equal(errorDiagnostic.relatedInformation?.[0]?.location.uri, toUri('/tmp/original.fcstm'));

        assert.equal(packageModule.toLspSymbolKind('variable'), SymbolKind.Variable);
        assert.equal(packageModule.toLspSymbolKind('event'), SymbolKind.Event);
        assert.equal(packageModule.toLspSymbolKind('class'), SymbolKind.Class);
        assert.equal(packageModule.toLspSymbolKind('function'), SymbolKind.Function);
        assert.equal(packageModule.toLspSymbolKind('module'), SymbolKind.Module);

        const symbol = packageModule.toLspDocumentSymbol({
            name: 'Root',
            detail: '',
            kind: 'class',
            range: packageModule.createRange(0, 0, 2, 1),
            selectionRange: packageModule.createRange(0, 0, 0, 4),
            children: [{
                name: 'Start',
                detail: 'Event',
                kind: 'event',
                range: packageModule.createRange(1, 0, 1, 5),
                selectionRange: packageModule.createRange(1, 0, 1, 5),
                children: [],
            }],
        });
        assert.equal(symbol.kind, SymbolKind.Class);
        assert.equal(symbol.children?.[0]?.kind, SymbolKind.Event);

        const snippetCompletion = packageModule.toLspCompletionItem({
            label: 'sin',
            kind: 'function',
            detail: '(x)',
            documentation: 'Sine function',
            insertText: 'sin($1)$0',
            insertTextFormat: 'snippet',
            sortText: '2_sin',
        });
        const plainCompletion = packageModule.toLspCompletionItem({
            label: 'state',
            kind: 'keyword',
            insertText: 'state',
        });
        assert.equal(snippetCompletion.kind, CompletionItemKind.Function);
        assert.equal(snippetCompletion.insertTextFormat, InsertTextFormat.Snippet);
        assert.equal(plainCompletion.insertTextFormat, InsertTextFormat.PlainText);
        assert.equal(snippetCompletion.documentation?.kind, MarkupKind.Markdown);

        const docHover = packageModule.toLspHover({
            kind: 'doc',
            doc: {
                title: 'Keyword',
                description: 'Description only',
            },
        });
        const importHover = packageModule.toLspHover({
            kind: 'import',
            title: 'Imported Module',
            sourcePath: './worker.fcstm',
            resolvedFile: '/tmp/worker.fcstm',
            explicitVariables: ['counter'],
            absoluteEvents: ['/Start'],
            range: packageModule.createRange(0, 0, 0, 10),
        });
        assert.match(docHover.contents.value, /Description only/);
        assert.match(importHover.contents.value, /Resolved path/);
        assert.match(importHover.contents.value, /counter/);
        assert.match(importHover.contents.value, /\/Start/);

        const location = packageModule.toLspLocation({
            uri: toUri('/tmp/worker.fcstm'),
            range: packageModule.createRange(0, 0, 0, 0),
        });
        assert.equal(location.uri, toUri('/tmp/worker.fcstm'));

        const link = packageModule.toLspDocumentLink({
            range: packageModule.createRange(0, 0, 0, 5),
            target: toUri('/tmp/worker.fcstm'),
        });
        assert.equal(link.target, toUri('/tmp/worker.fcstm'));
        assert.equal(link.tooltip, undefined);

        const highlight = packageModule.toLspDocumentHighlight({
            range: packageModule.createRange(0, 0, 0, 5),
            kind: 'write',
        });
        assert.equal(highlight.kind, DocumentHighlightKind.Write);

        const workspaceEdit = packageModule.toLspWorkspaceEdit({
            changes: {
                [toUri('/tmp/worker.fcstm')]: [{
                    range: packageModule.createRange(0, 0, 0, 5),
                    newText: 'WorkerRenamed',
                }],
            },
        });
        assert.equal(workspaceEdit.changes?.[toUri('/tmp/worker.fcstm')]?.[0]?.newText, 'WorkerRenamed');

        const workspaceSymbol = packageModule.toLspWorkspaceSymbol({
            name: 'Worker',
            kind: 'state',
            containerName: 'Root',
            location: {
                uri: toUri('/tmp/worker.fcstm'),
                range: packageModule.createRange(0, 0, 0, 5),
            },
        });
        assert.equal(workspaceSymbol.containerName, 'Root');
        assert.equal(workspaceSymbol.kind, SymbolKind.Class);

        const importWorkspaceSymbol = packageModule.toLspWorkspaceSymbol({
            name: 'Worker',
            kind: 'import',
            containerName: 'Root',
            location: {
                uri: toUri('/tmp/worker.fcstm'),
                range: packageModule.createRange(0, 0, 0, 5),
            },
        });
        assert.equal(importWorkspaceSymbol.kind, SymbolKind.Module);

        const codeAction = packageModule.toLspCodeAction({
            title: 'Remove unresolved import',
            kind: 'quickfix',
            diagnostics: [{
                range: packageModule.createRange(0, 0, 0, 5),
                message: 'missing import',
                severity: 'error',
                source: 'fcstm',
                code: packageModule.FCSTM_DIAGNOSTIC_CODES.missingImport,
            }],
            edit: {
                changes: {
                    [toUri('/tmp/worker.fcstm')]: [{
                        range: packageModule.createRange(0, 0, 0, 5),
                        newText: '',
                    }],
                },
            },
        });
        assert.equal(codeAction.kind, CodeActionKind.QuickFix);
        assert.equal(codeAction.edit?.changes?.[toUri('/tmp/worker.fcstm')]?.[0]?.newText, '');

        const foldingRange = packageModule.toLspFoldingRange({
            startLine: 0,
            endLine: 3,
            kind: 'region',
        });
        assert.equal(foldingRange.kind, 'region');

        const selectionRange = packageModule.toLspSelectionRange({
            range: packageModule.createRange(0, 0, 0, 4),
            parent: {
                range: packageModule.createRange(0, 0, 1, 0),
            },
        });
        assert.deepEqual(selectionRange.parent?.range, packageModule.toLspRange(packageModule.createRange(0, 0, 1, 0)));

        const semanticTokens = packageModule.toLspSemanticTokens({data: [0, 0, 4, 0, 0]});
        assert.deepEqual(semanticTokens.data, [0, 0, 4, 0, 0]);
    });

    it('covers default scheduler behavior and internal core guard branches', async () => {
        const dir = trackTempDir('jsfcstm-lsp-internal-');
        const hostFile = path.join(dir, 'host.fcstm');
        const hostUri = toUri(hostFile);
        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const core = new packageModule.FcstmLanguageServerCore({
            debounceMs: 10,
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });
        const diagnosticsModule = require('../dist/editor/diagnostics.js') as typeof import('../dist/editor/diagnostics');
        const completionModule = require('../dist/editor/completion.js') as typeof import('../dist/editor/completion');
        const foldingModule = require('../dist/editor/folding.js') as typeof import('../dist/editor/folding');
        const hoverModule = require('../dist/editor/hover.js') as typeof import('../dist/editor/hover');
        const navigationModule = require('../dist/editor/navigation.js') as typeof import('../dist/editor/navigation');
        const selectionModule = require('../dist/editor/selection.js') as typeof import('../dist/editor/selection');
        const semanticTokensModule = require('../dist/editor/semantic-tokens.js') as typeof import('../dist/editor/semantic-tokens');
        const symbolsModule = require('../dist/editor/symbols.js') as typeof import('../dist/editor/symbols');

        await core.openTextDocument({
            uri: 'untitled:memory.fcstm',
            languageId: 'fcstm',
            version: 1,
            text: 'state Root;',
        });
        await core.openTextDocument({
            uri: 'file://%',
            languageId: 'fcstm',
            version: 1,
            text: 'state Root;',
        });
        await core.changeTextDocument('untitled:absent.fcstm', 1, [{text: 'state Root;'}]);
        await core.changeTextDocument('untitled:memory.fcstm', 2, [{text: 'state Root'}]);
        await core.changeTextDocument('untitled:memory.fcstm', 3, [{text: 'state Root;'}]);
        await new Promise(resolve => setTimeout(resolve, 40));
        assert.ok(publications.some(item => item.version === 3));

        await core.saveTextDocument('untitled:missing.fcstm');
        await core.closeTextDocument('untitled:missing.fcstm');
        assert.deepEqual(publications.at(-1), {
            uri: 'untitled:missing.fcstm',
            version: 0,
            diagnostics: [],
        });

        assert.deepEqual(await core.provideDocumentSymbols('untitled:absent.fcstm'), []);
        assert.deepEqual(await core.provideCompletionItems('untitled:absent.fcstm', {line: 0, character: 0}), []);
        assert.equal(await core.provideHover('untitled:absent.fcstm', {line: 0, character: 0}), null);
        assert.equal(await core.provideDefinition('untitled:absent.fcstm', {line: 0, character: 0}), null);
        assert.deepEqual(await core.provideDocumentLinks('untitled:absent.fcstm'), []);
        assert.deepEqual(await core.provideFoldingRanges('untitled:absent.fcstm'), []);
        assert.deepEqual(await core.provideSelectionRanges('untitled:absent.fcstm', [{line: 0, character: 0}]), []);
        assert.deepEqual(await core.provideSemanticTokens('untitled:absent.fcstm'), {data: []});

        await core.openTextDocument({
            uri: hostUri,
            languageId: 'fcstm',
            version: 1,
            text: 'state Root;',
        });

        await (core as unknown as { publishDiagnostics: (uri: string, version: number, token?: unknown) => Promise<void> }).publishDiagnostics(
            hostUri,
            1,
            {isCancellationRequested: true}
        );
        await (core as unknown as { publishDiagnostics: (uri: string, version: number) => Promise<void> }).publishDiagnostics(
            'file:///missing.fcstm',
            1
        );
        await (core as unknown as { publishDiagnostics: (uri: string, version: number) => Promise<void> }).publishDiagnostics(
            hostUri,
            99
        );

        assert.equal(
            await core.provideHover(hostUri, {line: 0, character: 0}, {isCancellationRequested: true}),
            null
        );
        assert.equal(
            await core.provideDefinition(hostUri, {line: 0, character: 0}, {isCancellationRequested: true}),
            null
        );
        assert.deepEqual(
            await core.provideDocumentLinks(hostUri, {isCancellationRequested: true}),
            []
        );
        assert.deepEqual(
            await core.provideFoldingRanges(hostUri, {isCancellationRequested: true}),
            []
        );
        assert.deepEqual(
            await core.provideSelectionRanges(
                hostUri,
                [{line: 0, character: 0}],
                {isCancellationRequested: true}
            ),
            []
        );
        assert.deepEqual(
            await core.provideSemanticTokens(hostUri, {isCancellationRequested: true}),
            {data: []}
        );
        assert.deepEqual(
            await core.provideReferences(hostUri, {line: 0, character: 0}, true, {isCancellationRequested: true}),
            []
        );
        assert.deepEqual(
            await core.provideDocumentHighlights(hostUri, {line: 0, character: 0}, {isCancellationRequested: true}),
            []
        );
        assert.equal(
            await core.providePrepareRename(hostUri, {line: 0, character: 0}, {isCancellationRequested: true}),
            null
        );
        assert.equal(
            await core.provideRename(hostUri, {line: 0, character: 0}, 'Renamed', {isCancellationRequested: true}),
            null
        );
        assert.deepEqual(
            await core.provideWorkspaceSymbols('root', {isCancellationRequested: true}),
            []
        );
        assert.deepEqual(
            await core.provideCodeActions(
                hostUri,
                packageModule.toLspRange(packageModule.createRange(0, 0, 0, 1)),
                [],
                {isCancellationRequested: true}
            ),
            []
        );

        const symbolsCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                symbolsModule,
                'collectDocumentSymbols',
                async () => {
                    symbolsCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideDocumentSymbols(hostUri, symbolsCancelToken)
            ),
            []
        );

        const completionCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                completionModule,
                'collectCompletionItems',
                async () => {
                    completionCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideCompletionItems(hostUri, {line: 0, character: 0}, completionCancelToken)
            ),
            []
        );

        const foldingCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                foldingModule,
                'collectFoldingRanges',
                async () => {
                    foldingCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideFoldingRanges(hostUri, foldingCancelToken)
            ),
            []
        );

        const selectionCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                selectionModule,
                'collectSelectionRanges',
                async () => {
                    selectionCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideSelectionRanges(
                    hostUri,
                    [{line: 0, character: 0}],
                    selectionCancelToken
                )
            ),
            []
        );

        const semanticTokensCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                semanticTokensModule,
                'collectSemanticTokens',
                async () => {
                    semanticTokensCancelToken.isCancellationRequested = true;
                    return {data: [0, 0, 4, 0, 0]};
                },
                async () => core.provideSemanticTokens(hostUri, semanticTokensCancelToken)
            ),
            {data: []}
        );

        const lateCancelToken = {isCancellationRequested: false};
        await withPatchedProperty(
            diagnosticsModule,
            'collectDocumentDiagnostics',
            async () => {
                lateCancelToken.isCancellationRequested = true;
                return [];
            },
            async () => {
                await (core as unknown as { publishDiagnostics: (uri: string, version: number, token?: unknown) => Promise<void> }).publishDiagnostics(
                    hostUri,
                    1,
                    lateCancelToken
                );
            }
        );

        await withPatchedProperty(
            diagnosticsModule,
            'collectDocumentDiagnostics',
            async () => {
                (core as unknown as { documents: Map<string, TextDocument> }).documents.set(
                    hostUri,
                    TextDocument.create(hostUri, 'fcstm', 2, 'state Root;')
                );
                return [];
            },
            async () => {
                await (core as unknown as { publishDiagnostics: (uri: string, version: number) => Promise<void> }).publishDiagnostics(
                    hostUri,
                    1
                );
            }
        );

        assert.equal(
            await withPatchedProperty(
                hoverModule,
                'resolveHover',
                async () => null,
                async () => core.provideHover(hostUri, {line: 0, character: 0})
            ),
            null
        );

        const hoverCancelToken = {isCancellationRequested: false};
        assert.equal(
            await withPatchedProperty(
                hoverModule,
                'resolveHover',
                async () => {
                    hoverCancelToken.isCancellationRequested = true;
                    return {
                        kind: 'doc',
                        doc: {
                            title: 'State Definition',
                            description: 'Late cancellation branch',
                        },
                    } as const;
                },
                async () => core.provideHover(hostUri, {line: 0, character: 0}, hoverCancelToken)
            ),
            null
        );

        assert.equal(
            await withPatchedProperty(
                navigationModule,
                'resolveDefinitionLocation',
                async () => null,
                async () => core.provideDefinition(hostUri, {line: 0, character: 0})
            ),
            null
        );

        const definitionCancelToken = {isCancellationRequested: false};
        assert.equal(
            await withPatchedProperty(
                navigationModule,
                'resolveDefinitionLocation',
                async () => {
                    definitionCancelToken.isCancellationRequested = true;
                    return {
                        uri: hostUri,
                        range: packageModule.createRange(0, 0, 0, 1),
                    };
                },
                async () => core.provideDefinition(hostUri, {line: 0, character: 0}, definitionCancelToken)
            ),
            null
        );

        const linksCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                navigationModule,
                'collectDocumentLinks',
                async () => {
                    linksCancelToken.isCancellationRequested = true;
                    return [{
                        target: hostUri,
                        range: packageModule.createRange(0, 0, 0, 1),
                    }];
                },
                async () => core.provideDocumentLinks(hostUri, linksCancelToken)
            ),
            []
        );

        const referencesModule = require('../dist/editor/references.js') as typeof import('../dist/editor/references');
        const codeActionsModule = require('../dist/editor/code-actions.js') as typeof import('../dist/editor/code-actions');

        const referencesCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                referencesModule,
                'collectReferences',
                async () => {
                    referencesCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideReferences(hostUri, {line: 0, character: 0}, true, referencesCancelToken)
            ),
            []
        );

        const highlightCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                referencesModule,
                'collectDocumentHighlights',
                async () => {
                    highlightCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideDocumentHighlights(hostUri, {line: 0, character: 0}, highlightCancelToken)
            ),
            []
        );

        assert.equal(
            await withPatchedProperty(
                referencesModule,
                'prepareRename',
                async () => null,
                async () => core.providePrepareRename(hostUri, {line: 0, character: 0})
            ),
            null
        );

        const prepareRenameCancelToken = {isCancellationRequested: false};
        assert.equal(
            await withPatchedProperty(
                referencesModule,
                'prepareRename',
                async () => {
                    prepareRenameCancelToken.isCancellationRequested = true;
                    return {
                        range: packageModule.createRange(0, 0, 0, 4),
                        placeholder: 'Root',
                    };
                },
                async () => core.providePrepareRename(hostUri, {line: 0, character: 0}, prepareRenameCancelToken)
            ),
            null
        );

        assert.equal(
            await withPatchedProperty(
                referencesModule,
                'planRename',
                async () => null,
                async () => core.provideRename(hostUri, {line: 0, character: 0}, 'Renamed')
            ),
            null
        );

        const renameCancelToken = {isCancellationRequested: false};
        assert.equal(
            await withPatchedProperty(
                referencesModule,
                'planRename',
                async () => {
                    renameCancelToken.isCancellationRequested = true;
                    return {
                        changes: {
                            [hostUri]: [{
                                range: packageModule.createRange(0, 0, 0, 4),
                                newText: 'Renamed',
                            }],
                        },
                    };
                },
                async () => core.provideRename(hostUri, {line: 0, character: 0}, 'Renamed', renameCancelToken)
            ),
            null
        );

        const workspaceSymbolsCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                referencesModule,
                'collectWorkspaceSymbols',
                async () => {
                    workspaceSymbolsCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideWorkspaceSymbols('root', workspaceSymbolsCancelToken)
            ),
            []
        );

        const codeActionsCancelToken = {isCancellationRequested: false};
        assert.deepEqual(
            await withPatchedProperty(
                codeActionsModule,
                'collectCodeActions',
                async () => {
                    codeActionsCancelToken.isCancellationRequested = true;
                    return [];
                },
                async () => core.provideCodeActions(
                    hostUri,
                    packageModule.toLspRange(packageModule.createRange(0, 0, 0, 1)),
                    [],
                    codeActionsCancelToken
                )
            ),
            []
        );

        (core as unknown as { clearDiagnosticsTimer: (uri: string) => void }).clearDiagnosticsTimer('file:///no-timer.fcstm');
        (core as unknown as { removeOverlay: (uri: string) => void }).removeOverlay('untitled:no-overlay.fcstm');
        await core.applyWorkspaceFolderChange(
            [],
            [{uri: toUri(dir), name: 'fixture'}]
        );

        core.dispose();
    });

    it('covers server bootstrap wiring and default start entrypoint', async () => {
        const dir = trackTempDir('jsfcstm-lsp-server-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        const fakeConnection = new FakeConnection();
        const lspNodeModule = require('vscode-languageserver/node') as typeof import('vscode-languageserver/node');

        writeFile(workerFile, 'state Worker;');
        const hostText = [
            'def int counter = 0;',
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '}',
        ].join('\n');

        const server = packageModule.createFcstmLanguageServer(fakeConnection as never);
        server.listen();
        assert.equal(fakeConnection.listenCount, 1);

        const initializeResult = await fakeConnection.handlers.initialize?.({
            workspaceFolders: [{uri: toUri(dir), name: 'fixture'}],
        }) as {
            capabilities?: {
                definitionProvider?: boolean;
                referencesProvider?: boolean;
                codeActionProvider?: boolean;
                foldingRangeProvider?: boolean;
                selectionRangeProvider?: boolean;
                semanticTokensProvider?: { legend?: { tokenTypes?: string[] } };
            };
        };
        assert.equal(initializeResult.capabilities?.definitionProvider, true);
        assert.equal(initializeResult.capabilities?.referencesProvider, true);
        assert.equal(initializeResult.capabilities?.codeActionProvider, true);
        assert.equal(initializeResult.capabilities?.foldingRangeProvider, true);
        assert.equal(initializeResult.capabilities?.selectionRangeProvider, true);
        assert.ok(initializeResult.capabilities?.semanticTokensProvider?.legend?.tokenTypes?.includes('class'));
        const initializeWithoutFolders = await fakeConnection.handlers.initialize?.({}) as { capabilities?: { hoverProvider?: boolean } };
        assert.equal(initializeWithoutFolders.capabilities?.hoverProvider, true);

        await fakeConnection.handlers.open?.({
            textDocument: {
                uri: toUri(hostFile),
                languageId: 'fcstm',
                version: 1,
                text: hostText,
            },
        });
        await fakeConnection.handlers.change?.({
            textDocument: {
                uri: toUri(hostFile),
                version: 2,
            },
            contentChanges: [{text: hostText}],
        });
        await fakeConnection.handlers.save?.({
            textDocument: {uri: toUri(hostFile)},
        });

        const symbols = await fakeConnection.handlers.symbol?.({
            textDocument: {uri: toUri(hostFile)},
        }) as Array<{ name: string }>;
        const completionItems = await fakeConnection.handlers.completion?.({
            textDocument: {uri: toUri(hostFile)},
            position: {line: 1, character: 2},
        }) as Array<{ label: string }>;
        const hover = await fakeConnection.handlers.hover?.({
            textDocument: {uri: toUri(hostFile)},
            position: {line: 1, character: 2},
        }) as { contents?: { value?: string } };
        const definition = await fakeConnection.handlers.definition?.({
            textDocument: {uri: toUri(hostFile)},
            position: {line: 2, character: 15},
        }) as Array<{ uri: string }>;
        const references = await fakeConnection.handlers.references?.({
            textDocument: {uri: toUri(hostFile)},
            position: {line: 2, character: hostText.split('\n')[2].indexOf('Worker') + 1},
            context: {includeDeclaration: true},
        }) as Array<{ uri: string }>;
        const highlights = await fakeConnection.handlers.highlights?.({
            textDocument: {uri: toUri(hostFile)},
            position: {line: 2, character: hostText.split('\n')[2].indexOf('Worker') + 1},
        }) as Array<{ kind: number }>;
        const prepareRename = await fakeConnection.handlers.prepareRename?.({
            textDocument: {uri: toUri(hostFile)},
            position: {line: 2, character: hostText.split('\n')[2].indexOf('Worker') + 1},
        }) as { start: { line: number } };
        const rename = await fakeConnection.handlers.rename?.({
            textDocument: {uri: toUri(hostFile)},
            position: {line: 2, character: hostText.split('\n')[2].indexOf('Worker') + 1},
            newName: 'Motor',
        }) as { changes?: Record<string, unknown[]> };
        const links = await fakeConnection.handlers.links?.({
            textDocument: {uri: toUri(hostFile)},
        }) as Array<{ target: string }>;
        const foldingRanges = await fakeConnection.handlers.folding?.({
            textDocument: {uri: toUri(hostFile)},
        }) as Array<{ startLine: number; endLine: number }>;
        const selectionRanges = await fakeConnection.handlers.selection?.({
            textDocument: {uri: toUri(hostFile)},
            positions: [{line: 2, character: hostText.split('\n')[2].indexOf('Worker') + 1}],
        }) as Array<{ range: { start: { line: number } }; parent?: unknown }>;
        const semanticTokens = await fakeConnection.handlers.semanticTokens?.({
            textDocument: {uri: toUri(hostFile)},
        }) as { data: number[] };
        const workspaceSymbols = await fakeConnection.handlers.workspaceSymbol?.({
            query: 'work',
        }) as Array<{ name: string }>;
        const codeActions = await fakeConnection.handlers.codeAction?.({
            textDocument: {uri: toUri(hostFile)},
            range: packageModule.toLspRange(packageModule.createRange(0, 0, 3, 1)),
            context: {diagnostics: []},
        }) as unknown[];

        assert.ok(symbols.some(item => item.name === 'Root'));
        assert.ok(completionItems.some(item => item.label === 'counter'));
        assert.match(hover.contents?.value || '', /State Definition/);
        assert.equal(definition[0]?.uri, toUri(workerFile));
        assert.ok(references.length >= 1);
        assert.ok(highlights.length >= 1);
        assert.ok(prepareRename);
        assert.ok(Object.values(rename.changes || {}).flat().length >= 1);
        assert.equal(links[0]?.target, toUri(workerFile));
        assert.ok(foldingRanges.some(item => item.startLine === 1 && item.endLine === 3));
        assert.equal(selectionRanges[0]?.range.start.line, 2);
        assert.ok(selectionRanges[0]?.parent);
        assert.ok(semanticTokens.data.length > 0);
        assert.ok(workspaceSymbols.some(item => item.name === 'Worker'));
        assert.deepEqual(codeActions, []);

        fakeConnection.handlers.initialized?.();
        await fakeConnection.workspaceFolderHandler?.({
            added: [{uri: toUri(path.join(dir, 'nested')), name: 'nested'}],
            removed: [],
        });

        await fakeConnection.handlers.close?.({
            textDocument: {uri: toUri(hostFile)},
        });
        assert.ok(fakeConnection.diagnostics.length >= 2);

        fakeConnection.handlers.shutdown?.();

        const bootstrapConnection = new FakeConnection();
        await withPatchedProperty(
            lspNodeModule,
            'createConnection',
            () => bootstrapConnection as never,
            async () => {
                packageModule.startFcstmLanguageServer();
            }
        );
        assert.equal(bootstrapConnection.listenCount, 1);
    });
});

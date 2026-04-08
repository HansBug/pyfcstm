import assert from 'node:assert/strict';
import * as path from 'node:path';
import {pathToFileURL} from 'node:url';

import {
    CompletionItemKind,
    DiagnosticSeverity,
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
    links?: (params: { textDocument: { uri: string } }, token?: unknown) => Promise<unknown> | unknown;
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

    onDocumentLinks(callback: HandlerMap['links']): void {
        this.handlers.links = callback;
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
        });
        const warningDiagnostic = packageModule.toLspDiagnostic({
            range: packageModule.createRange(0, 1, 0, 2),
            message: 'Warn',
            severity: 'warning',
            source: 'fcstm',
        });
        assert.equal(errorDiagnostic.severity, DiagnosticSeverity.Error);
        assert.equal(warningDiagnostic.severity, DiagnosticSeverity.Warning);

        assert.equal(packageModule.toLspSymbolKind('variable'), SymbolKind.Variable);
        assert.equal(packageModule.toLspSymbolKind('event'), SymbolKind.Event);
        assert.equal(packageModule.toLspSymbolKind('class'), SymbolKind.Class);

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
        const hoverModule = require('../dist/editor/hover.js') as typeof import('../dist/editor/hover');
        const navigationModule = require('../dist/editor/navigation.js') as typeof import('../dist/editor/navigation');
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
        }) as { capabilities?: { definitionProvider?: boolean } };
        assert.equal(initializeResult.capabilities?.definitionProvider, true);
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
        const links = await fakeConnection.handlers.links?.({
            textDocument: {uri: toUri(hostFile)},
        }) as Array<{ target: string }>;

        assert.ok(symbols.some(item => item.name === 'Root'));
        assert.ok(completionItems.some(item => item.label === 'counter'));
        assert.match(hover.contents?.value || '', /State Definition/);
        assert.equal(definition[0]?.uri, toUri(workerFile));
        assert.equal(links[0]?.target, toUri(workerFile));

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

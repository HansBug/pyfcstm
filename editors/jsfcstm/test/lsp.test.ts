import assert from 'node:assert/strict';
import * as path from 'node:path';
import {pathToFileURL} from 'node:url';

import {TextDocumentSyncKind} from 'vscode-languageserver/node';
import type {CancellationToken, MarkupContent} from 'vscode-languageserver/node';

import {packageModule, trackTempDir, writeFile} from './support';

class TestScheduler implements packageModule.FcstmLanguageServerScheduler {
    private nextId = 1;
    private readonly timers = new Map<number, () => void | Promise<void>>();

    setTimeout(callback: () => void | Promise<void>, _delayMs: number): number {
        const id = this.nextId++;
        this.timers.set(id, callback);
        return id;
    }

    clearTimeout(timer: unknown): void {
        this.timers.delete(timer as number);
    }

    async flushAll(): Promise<void> {
        const pending = [...this.timers.values()];
        this.timers.clear();
        for (const callback of pending) {
            await callback();
        }
    }

    size(): number {
        return this.timers.size;
    }
}

function toUri(filePath: string): string {
    return pathToFileURL(filePath).toString();
}

function makeTextDocumentItem(filePath: string, text: string, version = 1): {
    uri: string;
    languageId: string;
    version: number;
    text: string;
} {
    return {
        uri: toUri(filePath),
        languageId: 'fcstm',
        version,
        text,
    };
}

describe('jsfcstm lsp core', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('provides LSP capabilities, symbols, completion, hover, definition, and document links', async () => {
        const dir = trackTempDir('jsfcstm-lsp-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');

        writeFile(workerFile, 'state Worker;');

        const hostText = [
            'def int counter = 0;',
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '}',
        ].join('\n');

        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const core = new packageModule.FcstmLanguageServerCore({
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });

        await core.openTextDocument(makeTextDocumentItem(hostFile, hostText));

        const initializeResult = core.getInitializeResult();
        assert.equal(initializeResult.capabilities.textDocumentSync, TextDocumentSyncKind.Incremental);
        assert.equal(initializeResult.capabilities.definitionProvider, true);
        assert.equal(initializeResult.capabilities.referencesProvider, true);
        assert.equal(initializeResult.capabilities.documentHighlightProvider, true);
        assert.equal(initializeResult.capabilities.workspaceSymbolProvider, true);
        assert.equal(initializeResult.capabilities.codeActionProvider, true);
        assert.equal(initializeResult.capabilities.renameProvider?.prepareProvider, true);
        assert.deepEqual(
            initializeResult.capabilities.completionProvider?.triggerCharacters,
            ['.', ':', '/']
        );
        assert.equal(publications.length, 1);
        assert.deepEqual(publications[0].diagnostics, []);

        const symbols = await core.provideDocumentSymbols(toUri(hostFile));
        assert.equal(symbols[0]?.name, 'counter');
        assert.equal(symbols[1]?.name, 'Root');

        const completionItems = await core.provideCompletionItems(toUri(hostFile), {
            line: 1,
            character: 2,
        });
        assert.ok(completionItems.some(item => item.label === 'state'));
        assert.ok(completionItems.some(item => item.label === 'counter'));

        const keywordHover = await core.provideHover(toUri(hostFile), {
            line: 1,
            character: 2,
        });
        const keywordHoverContent = keywordHover?.contents as MarkupContent | undefined;
        assert.equal(keywordHoverContent?.kind, 'markdown');
        assert.match(keywordHoverContent?.value || '', /State Definition/);

        const definition = await core.provideDefinition(toUri(hostFile), {
            line: 2,
            character: 15,
        });
        assert.equal(definition?.[0]?.uri, toUri(workerFile));

        const references = await core.provideReferences(toUri(hostFile), {
            line: 2,
            character: hostText.split('\n')[2].indexOf('Worker') + 1,
        }, true);
        assert.ok(references.length >= 1);

        const highlights = await core.provideDocumentHighlights(toUri(hostFile), {
            line: 2,
            character: hostText.split('\n')[2].indexOf('Worker') + 1,
        });
        assert.ok(highlights.length >= 1);

        const renameRange = await core.providePrepareRename(toUri(hostFile), {
            line: 2,
            character: hostText.split('\n')[2].indexOf('Worker') + 1,
        });
        assert.ok(renameRange);

        const renameEdit = await core.provideRename(toUri(hostFile), {
            line: 2,
            character: hostText.split('\n')[2].indexOf('Worker') + 1,
        }, 'Motor');
        assert.ok(Object.values(renameEdit?.changes || {}).flat().length >= 1);

        const links = await core.provideDocumentLinks(toUri(hostFile));
        assert.equal(links.length, 1);
        assert.equal(links[0].target, toUri(workerFile));

        const workspaceSymbols = await core.provideWorkspaceSymbols('work');
        assert.ok(workspaceSymbols.some(item => item.name === 'Worker'));

        const codeActions = await core.provideCodeActions(
            toUri(hostFile),
            packageModule.toLspRange(packageModule.createRange(0, 0, 3, 1)),
            []
        );
        assert.deepEqual(codeActions, []);

        core.dispose();
    });

    it('debounces diagnostics and only publishes the latest document version', async () => {
        const dir = trackTempDir('jsfcstm-lsp-debounce-');
        const hostFile = path.join(dir, 'host.fcstm');
        const scheduler = new TestScheduler();
        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const core = new packageModule.FcstmLanguageServerCore({
            scheduler,
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });

        await core.openTextDocument(makeTextDocumentItem(hostFile, 'state Root;'));
        assert.equal(publications.length, 1);

        await core.changeTextDocument(toUri(hostFile), 2, [{text: 'state Root'}]);
        assert.equal(scheduler.size(), 1);

        await core.changeTextDocument(toUri(hostFile), 3, [{text: 'state Root;'}]);
        assert.equal(scheduler.size(), 1);

        await scheduler.flushAll();

        assert.equal(publications.length, 2);
        assert.equal(publications[1].version, 3);
        assert.deepEqual(publications[1].diagnostics, []);

        await core.closeTextDocument(toUri(hostFile));
        assert.equal(core.hasDocument(toUri(hostFile)), false);
        assert.deepEqual(publications[2], {
            uri: toUri(hostFile),
            version: 0,
            diagnostics: [],
        });

        core.dispose();
    });

    it('keeps workspace overlays in sync so import-aware hover sees unsaved target changes', async () => {
        const dir = trackTempDir('jsfcstm-lsp-overlay-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');

        writeFile(workerFile, 'state Worker;');
        writeFile(hostFile, 'state Root {\n    import "./worker.fcstm" as Worker;\n}');

        const core = new packageModule.FcstmLanguageServerCore();
        await core.openTextDocument(makeTextDocumentItem(
            hostFile,
            'state Root {\n    import "./worker.fcstm" as Worker;\n}'
        ));
        await core.openTextDocument(makeTextDocumentItem(workerFile, 'state Worker;'));

        await core.changeTextDocument(toUri(workerFile), 2, [{text: 'state ChangedWorker;'}]);

        const hover = await core.provideHover(toUri(hostFile), {
            line: 1,
            character: 15,
        });

        const hoverContent = hover?.contents as MarkupContent | undefined;
        assert.equal(hoverContent?.kind, 'markdown');
        assert.match(hoverContent?.value || '', /ChangedWorker/);

        core.dispose();
    });

    it('supports workspace-folder revalidation and request cancellation', async () => {
        const dir = trackTempDir('jsfcstm-lsp-workspace-');
        const hostFile = path.join(dir, 'host.fcstm');
        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const core = new packageModule.FcstmLanguageServerCore({
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });

        await core.openTextDocument(makeTextDocumentItem(hostFile, 'state Root;'));
        await core.setWorkspaceFolders([{uri: toUri(dir), name: 'fixture'}]);
        await core.applyWorkspaceFolderChange([{uri: toUri(path.join(dir, 'nested')), name: 'nested'}], []);

        assert.equal(core.getTrackedWorkspaceFolders().length, 2);
        assert.ok(publications.length >= 3);

        const cancelledToken = {isCancellationRequested: true} as CancellationToken;
        const cancelledHover = await core.provideHover(toUri(hostFile), {line: 0, character: 2}, cancelledToken);
        const cancelledSymbols = await core.provideDocumentSymbols(toUri(hostFile), cancelledToken);
        const cancelledCompletions = await core.provideCompletionItems(
            toUri(hostFile),
            {line: 0, character: 2},
            cancelledToken
        );

        assert.equal(cancelledHover, null);
        assert.deepEqual(cancelledSymbols, []);
        assert.deepEqual(cancelledCompletions, []);

        core.dispose();
    });
});

import assert from 'node:assert/strict';
import * as path from 'node:path';
import {pathToFileURL} from 'node:url';

import {CodeActionKind, DiagnosticSeverity, TextDocumentSyncKind} from 'vscode-languageserver/node';
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
            '    event Done;',
            '    import "./worker.fcstm" as Worker;',
            '    [*] -> Worker;',
            '    Worker -> [*] : Done;',
            '}',
        ].join('\n');
        const importLine = 3;

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
        assert.equal(initializeResult.capabilities.foldingRangeProvider, true);
        assert.equal(initializeResult.capabilities.selectionRangeProvider, true);
        assert.equal(initializeResult.capabilities.renameProvider?.prepareProvider, true);
        const triggerCharacters = initializeResult.capabilities.completionProvider?.triggerCharacters || [];
        assert.ok(triggerCharacters.includes('.'));
        assert.ok(triggerCharacters.includes(':'));
        assert.ok(triggerCharacters.includes('/'));
        assert.ok(triggerCharacters.includes('I'));
        assert.ok(triggerCharacters.includes('Y'));
        assert.ok(triggerCharacters.includes('_'));
        assert.ok(initializeResult.capabilities.semanticTokensProvider?.legend.tokenTypes.includes('class'));
        assert.equal(publications.length, 1);
        assert.deepEqual(publications[0].diagnostics.map(item => item.code), ['W_UNREFERENCED_VAR']);

        const symbols = await core.provideDocumentSymbols(toUri(hostFile));
        assert.equal(symbols[0]?.name, 'counter');
        assert.equal(symbols[1]?.name, 'Root');
        assert.ok(symbols[1]?.children?.some(item => item.name === 'Imports'));
        assert.ok(symbols[1]?.children
            ?.find(item => item.name === 'Imports')
            ?.children?.some(item => item.name === 'Worker'));

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
            line: importLine,
            character: 15,
        });
        assert.equal(definition?.[0]?.uri, toUri(workerFile));

        const references = await core.provideReferences(toUri(hostFile), {
            line: importLine,
            character: hostText.split('\n')[importLine].indexOf('Worker') + 1,
        }, true);
        assert.ok(references.length >= 1);

        const highlights = await core.provideDocumentHighlights(toUri(hostFile), {
            line: importLine,
            character: hostText.split('\n')[importLine].indexOf('Worker') + 1,
        });
        assert.ok(highlights.length >= 1);

        const renameRange = await core.providePrepareRename(toUri(hostFile), {
            line: importLine,
            character: hostText.split('\n')[importLine].indexOf('Worker') + 1,
        });
        assert.ok(renameRange);

        const renameEdit = await core.provideRename(toUri(hostFile), {
            line: importLine,
            character: hostText.split('\n')[importLine].indexOf('Worker') + 1,
        }, 'Motor');
        assert.ok(Object.values(renameEdit?.changes || {}).flat().length >= 1);

        const links = await core.provideDocumentLinks(toUri(hostFile));
        assert.equal(links.length, 1);
        assert.equal(links[0].target, toUri(workerFile));

        const foldingRanges = await core.provideFoldingRanges(toUri(hostFile));
        assert.ok(foldingRanges.some(item => item.startLine === 1 && item.endLine === 6));

        const selectionRanges = await core.provideSelectionRanges(toUri(hostFile), [{
            line: importLine,
            character: hostText.split('\n')[importLine].indexOf('Worker') + 1,
        }]);
        assert.deepEqual(selectionRanges[0]?.range, {
            start: {line: importLine, character: hostText.split('\n')[importLine].indexOf('Worker')},
            end: {line: importLine, character: hostText.split('\n')[importLine].indexOf('Worker') + 'Worker'.length},
        });
        assert.ok(selectionRanges[0]?.parent);

        const semanticTokens = await core.provideSemanticTokens(toUri(hostFile));
        assert.ok(semanticTokens.data.length > 0);

        const workspaceSymbols = await core.provideWorkspaceSymbols('work');
        assert.ok(workspaceSymbols.some(item => item.name === 'Worker'));

        const codeActions = await core.provideCodeActions(
            toUri(hostFile),
            packageModule.toLspRange(packageModule.createRange(0, 0, 3, 1)),
            []
        );
        assert.ok(codeActions.some(item => (
            item.kind === CodeActionKind.QuickFix
            && item.diagnostics?.some(diagnostic => diagnostic.code === 'W_UNREFERENCED_VAR')
        )));

        core.dispose();
    });

    it('preserves diagnostic severity and related information on code actions', async () => {
        const dir = trackTempDir('jsfcstm-lsp-codeaction-');
        const hostFile = path.join(dir, 'host.fcstm');
        const hostUri = toUri(hostFile);
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : if [missing > 0];',
            '}',
        ].join('\n');
        const core = new packageModule.FcstmLanguageServerCore();
        await core.openTextDocument(makeTextDocumentItem(hostFile, text));

        const missingColumn = text.split('\n')[4].indexOf('missing');
        const diagnosticRange = packageModule.toLspRange(packageModule.createRange(
            4,
            missingColumn,
            4,
            missingColumn + 'missing'.length,
        ));
        const actions = await core.provideCodeActions(
            hostUri,
            diagnosticRange,
            [{
                range: diagnosticRange,
                message: 'Variable "missing" is not defined.',
                severity: DiagnosticSeverity.Information,
                source: 'fcstm',
                code: packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVar,
                relatedInformation: [{
                    location: {
                        uri: hostUri,
                        range: packageModule.toLspRange(packageModule.createRange(1, 4, 1, 12)),
                    },
                    message: 'Related state declaration.',
                }],
            }]
        );

        const action = actions.find(item => /Define "missing"/.test(item.title));
        assert.ok(action, `expected define-variable action, got ${JSON.stringify(actions)}`);
        const actionDiagnostic = action.diagnostics?.[0];
        assert.equal(actionDiagnostic?.severity, DiagnosticSeverity.Information);
        assert.equal(actionDiagnostic?.relatedInformation?.[0]?.message, 'Related state declaration.');
        assert.equal(actionDiagnostic?.relatedInformation?.[0]?.location.uri, hostUri);

        core.dispose();
    });

    it('publishes imported transition diagnostics under the authored source URI', async () => {
        const dir = trackTempDir('jsfcstm-lsp-imported-diagnostics-');
        const childFile = path.join(dir, 'child.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        const childText = [
            'state Child {',
            '    state Reach;',
            '    state Orphan;',
            '    state Done;',
            '    state OrphanGroup {',
            '        state Nested;',
            '        [*] -> Nested;',
            '    }',
            '    [*] -> Reach;',
            '    Orphan -> Done;',
            '}',
        ].join('\n');
        writeFile(childFile, childText);
        const hostText = [
            'state Root {',
            '    import "./child.fcstm" as Imported;',
            '    [*] -> Imported;',
            '}',
        ].join('\n');
        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const core = new packageModule.FcstmLanguageServerCore({
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });

        await core.openTextDocument(makeTextDocumentItem(hostFile, hostText));

        const childPublication = publications.find(item => item.uri === toUri(childFile));
        assert.ok(childPublication, JSON.stringify(publications));
        assert.equal(childPublication.version, 0);
        assert.equal(childPublication.diagnostics.length, 2, JSON.stringify(childPublication));
        assert.ok(childPublication.diagnostics.every(item => item.code === 'W_UNREACHABLE_TRANSITION'));
        assert.deepEqual(
            childPublication.diagnostics.map(item => item.range.start.line).sort((a, b) => a - b),
            [6, 9],
        );
        const hostPublication = publications.find(item => item.uri === toUri(hostFile));
        assert.ok(hostPublication, JSON.stringify(publications));
        assert.equal(
            hostPublication.diagnostics.some(item => item.code === 'W_UNREACHABLE_TRANSITION'),
            false,
        );

        await core.openTextDocument(makeTextDocumentItem(childFile, childText));
        const reopenedChildPublication = publications.at(-1);
        assert.equal(reopenedChildPublication?.uri, toUri(childFile));
        assert.equal(
            reopenedChildPublication?.diagnostics.filter(item => item.code === 'W_UNREACHABLE_TRANSITION').length,
            2,
            JSON.stringify(reopenedChildPublication),
        );

        core.dispose();
    });

    it('keeps distinct unreachable forced expansions under one declaration', async () => {
        const dir = trackTempDir('jsfcstm-lsp-forced-expansion-identity-');
        const filePath = path.join(dir, 'machine.fcstm');
        const text = [
            'state Root {',
            '    state Group {',
            '        state Reach;',
            '        state LostA;',
            '        state LostB;',
            '        state Done;',
            '        [*] -> Reach;',
            '        !* -> Done :: Panic;',
            '    }',
            '    [*] -> Group;',
            '}',
        ].join('\n');
        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const core = new packageModule.FcstmLanguageServerCore({
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });

        await core.openTextDocument(makeTextDocumentItem(filePath, text));

        const publication = publications.find(item => item.uri === toUri(filePath));
        assert.ok(publication, JSON.stringify(publications));
        const unreachable = publication.diagnostics.filter(
            item => item.code === 'W_UNREACHABLE_TRANSITION',
        );
        assert.equal(unreachable.length, 2, JSON.stringify(publication));
        assert.deepEqual(
            unreachable.map(item => item.data?.source_state_path).sort(),
            ['Root.Group.LostA', 'Root.Group.LostB'],
        );

        core.dispose();
    });

    it('revalidates importing roots after an imported document changes', async () => {
        const dir = trackTempDir('jsfcstm-lsp-imported-refresh-');
        const childFile = path.join(dir, 'child.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        const childUri = toUri(childFile);
        const hostUri = toUri(hostFile);
        const staleChildText = [
            'state Child {',
            '    state Reach;',
            '    state Orphan;',
            '    state Done;',
            '    [*] -> Reach;',
            '    Orphan -> Done;',
            '}',
        ].join('\n');
        const cleanChildText = [
            'state Child {',
            '    state Reach;',
            '    state Done;',
            '    [*] -> Reach;',
            '    Reach -> Done;',
            '}',
        ].join('\n');
        const hostText = [
            'state Root {',
            '    import "./child.fcstm" as Imported;',
            '    [*] -> Imported;',
            '}',
        ].join('\n');
        writeFile(childFile, staleChildText);

        const scheduler = new TestScheduler();
        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const core = new packageModule.FcstmLanguageServerCore({
            scheduler,
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });

        await core.openTextDocument(makeTextDocumentItem(hostFile, hostText));
        await core.openTextDocument(makeTextDocumentItem(childFile, staleChildText));
        await scheduler.flushAll();
        assert.ok(publications.some(item => (
            item.uri === childUri
            && item.diagnostics.some(diagnostic => diagnostic.code === 'W_UNREACHABLE_TRANSITION')
        )), JSON.stringify(publications));

        await core.changeTextDocument(childUri, 2, [{text: cleanChildText}]);
        await scheduler.flushAll();

        const latestHostPublication = [...publications].reverse().find(item => item.uri === hostUri);
        const latestChildPublication = [...publications].reverse().find(item => item.uri === childUri);
        assert.ok(latestHostPublication);
        assert.ok(latestChildPublication);
        assert.equal(
            latestHostPublication.diagnostics.some(diagnostic => diagnostic.code === 'W_UNREACHABLE_TRANSITION'),
            false,
            JSON.stringify(latestHostPublication),
        );
        assert.equal(
            latestChildPublication.diagnostics.some(diagnostic => diagnostic.code === 'W_UNREACHABLE_TRANSITION'),
            false,
            JSON.stringify(latestChildPublication),
        );

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

        const cleanText = 'state Root { event Done; state Idle; [*] -> Idle; Idle -> [*] : Done; }';
        await core.openTextDocument(makeTextDocumentItem(hostFile, cleanText));
        assert.equal(publications.length, 1);

        await core.changeTextDocument(toUri(hostFile), 2, [{text: 'state Root'}]);
        assert.equal(scheduler.size(), 1);

        await core.changeTextDocument(toUri(hostFile), 3, [{text: cleanText}]);
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

    it('does not let an older dependency revalidation restore stale diagnostics', async () => {
        const dir = trackTempDir('jsfcstm-lsp-diagnostic-generation-');
        const childFile = path.join(dir, 'child.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        const childUri = toUri(childFile);
        const hostUri = toUri(hostFile);
        const staleChildText = [
            'state Child {',
            '    state Reach;',
            '    state Orphan;',
            '    state Done;',
            '    [*] -> Reach;',
            '    Orphan -> Done;',
            '}',
        ].join('\n');
        const cleanChildText = [
            'state Child {',
            '    state Reach;',
            '    state Done;',
            '    [*] -> Reach;',
            '    Reach -> Done;',
            '}',
        ].join('\n');
        const hostText = [
            'state Root {',
            '    import "./child.fcstm" as Imported;',
            '    [*] -> Imported;',
            '}',
        ].join('\n');
        writeFile(childFile, staleChildText);

        const staleResult = new Map<string, packageModule.FcstmDiagnostic[]>([
            [hostUri, [{
                range: packageModule.createRange(0, 0, 0, 1),
                message: 'stale imported warning',
                severity: 'warning',
                source: 'fcstm',
                code: 'W_UNREACHABLE_TRANSITION',
            }]],
        ]);
        const emptyResult = new Map<string, packageModule.FcstmDiagnostic[]>([[hostUri, []]]);
        let hostCalls = 0;
        let resolveOld: ((value: Map<string, packageModule.FcstmDiagnostic[]>) => void) | undefined;
        let resolveNew: ((value: Map<string, packageModule.FcstmDiagnostic[]>) => void) | undefined;
        const oldResult = new Promise<Map<string, packageModule.FcstmDiagnostic[]>>(resolve => {
            resolveOld = resolve;
        });
        const newResult = new Promise<Map<string, packageModule.FcstmDiagnostic[]>>(resolve => {
            resolveNew = resolve;
        });
        const collector = (async (_document: unknown, rootUri: string) => {
            if (rootUri !== hostUri) return new Map<string, packageModule.FcstmDiagnostic[]>([[rootUri, []]]);
            hostCalls += 1;
            if (hostCalls === 1) return emptyResult;
            if (hostCalls === 2) return oldResult;
            return newResult;
        }) as typeof packageModule.collectDocumentDiagnosticsByUri;

        const scheduler = new TestScheduler();
        const publications: packageModule.FcstmPublishedDiagnostics[] = [];
        const injectedCore = new packageModule.FcstmLanguageServerCore({
            scheduler,
            collectDocumentDiagnostics: collector,
            onDiagnostics(publication) {
                publications.push(publication);
            },
        });

        await injectedCore.openTextDocument(makeTextDocumentItem(hostFile, hostText));
        await injectedCore.openTextDocument(makeTextDocumentItem(childFile, staleChildText));

        const oldFlush = scheduler.flushAll();
        await new Promise<void>(resolve => setImmediate(resolve));
        assert.equal(hostCalls, 2);

        await injectedCore.changeTextDocument(childUri, 2, [{text: cleanChildText}]);
        const newFlush = scheduler.flushAll();
        await new Promise<void>(resolve => setImmediate(resolve));
        assert.equal(hostCalls, 3);

        resolveNew?.(emptyResult);
        await newFlush;
        resolveOld?.(staleResult);
        await oldFlush;

        const latestHostPublication = [...publications].reverse().find(item => item.uri === hostUri);
        assert.ok(latestHostPublication, JSON.stringify(publications));
        assert.deepEqual(latestHostPublication.diagnostics, []);
        injectedCore.dispose();
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

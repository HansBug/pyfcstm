#!/usr/bin/env node

const fs = require('fs');
const os = require('os');
const path = require('path');
const Module = require('module');

const originalRequire = Module.prototype.require;

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fcstm-preview-verify-'));
const previewFile = path.join(tempDir, 'preview.fcstm');
const distExtensionFile = path.resolve(__dirname, '..', 'dist', 'extension.js');

function createDocument(filePath, text) {
    const lines = () => text.split('\n');
    return {
        languageId: 'fcstm',
        fileName: filePath,
        uri: {
            scheme: 'file',
            fsPath: filePath,
            toString() { return this.fsPath; },
        },
        getText() { return text; },
        lineCount: lines().length,
        lineAt(line) { return {text: lines()[line] || ''}; },
        update(newText) { text = newText; },
    };
}

function createDisposable(callback = () => {}) {
    return {dispose: callback};
}

const workspaceListeners = {open: [], change: [], save: [], close: []};
const windowListeners = {activeEditor: []};
const registeredCommands = new Map();
const createdPanels = [];
const warningMessages = [];
const infoMessages = [];
const errorMessages = [];
const showTextDocumentCalls = [];

const vscode = {
    Uri: {
        joinPath(base, ...segments) {
            return {fsPath: path.join(base.fsPath, ...segments), toString() { return this.fsPath; }};
        },
        file(p) { return {scheme: 'file', fsPath: p, toString() { return 'file://' + p; }}; },
        parse(s) {
            const p = s.replace(/^file:\/\//, '');
            return {scheme: 'file', fsPath: p, toString() { return s; }};
        },
    },
    ViewColumn: {Active: 1, One: 1, Beside: 2},
    Range: class {
        constructor(start, end) { this.start = start; this.end = end; }
    },
    Position: class {
        constructor(line, character) { this.line = line; this.character = character; }
    },
    TextEditorRevealType: {InCenterIfOutsideViewport: 2},
    commands: {
        registerCommand(name, callback) {
            registeredCommands.set(name, callback);
            return createDisposable(() => registeredCommands.delete(name));
        },
    },
    workspace: {
        textDocuments: [],
        fs: {
            async writeFile(uri, buffer) {
                fs.writeFileSync(uri.fsPath, buffer);
            },
        },
        openTextDocument(resource) {
            const p = typeof resource === 'string' ? resource : resource.fsPath;
            const existing = this.textDocuments.find(d => d.uri.fsPath === p);
            if (existing) return Promise.resolve(existing);
            const text = fs.readFileSync(p, 'utf8');
            const doc = createDocument(p, text);
            this.textDocuments.push(doc);
            return Promise.resolve(doc);
        },
        onDidOpenTextDocument(cb) { workspaceListeners.open.push(cb); return createDisposable(); },
        onDidChangeTextDocument(cb) { workspaceListeners.change.push(cb); return createDisposable(); },
        onDidSaveTextDocument(cb) { workspaceListeners.save.push(cb); return createDisposable(); },
        onDidCloseTextDocument(cb) { workspaceListeners.close.push(cb); return createDisposable(); },
    },
    window: {
        activeTextEditor: null,
        createOutputChannel() { return createDisposable(); },
        createWebviewPanel(viewType, title, showOptions) {
            const disposeListeners = [];
            const panel = {
                viewType, title, showOptions,
                revealCalls: [],
                postedMessages: [],
                webview: {
                    cspSource: 'vscode-resource://fcstm',
                    html: '',
                    receiveMessageListeners: [],
                    asWebviewUri(r) { return {toString() { return 'vscode-resource:' + r.fsPath; }}; },
                    onDidReceiveMessage(l) { panel.webview.receiveMessageListeners.push(l); return createDisposable(); },
                    postMessage(m) { panel.postedMessages.push(m); return Promise.resolve(true); },
                },
                onDidDispose(l) { disposeListeners.push(l); return createDisposable(); },
                reveal(column, preserveFocus) { panel.revealCalls.push({column, preserveFocus}); },
                dispose() {
                    while (disposeListeners.length > 0) {
                        const l = disposeListeners.pop();
                        if (l) l();
                    }
                },
            };
            createdPanels.push(panel);
            return panel;
        },
        onDidChangeActiveTextEditor(cb) { windowListeners.activeEditor.push(cb); return createDisposable(); },
        showWarningMessage(m) { warningMessages.push(m); return Promise.resolve(m); },
        showInformationMessage(m) { infoMessages.push(m); return Promise.resolve(m); },
        showErrorMessage(m) { errorMessages.push(m); return Promise.resolve(m); },
        showTextDocument(doc, opts) {
            showTextDocumentCalls.push({doc, opts});
            return Promise.resolve({
                revealRange(range, type) {},
            });
        },
        showSaveDialog(opts) {
            return Promise.resolve(opts.defaultUri || null);
        },
    },
};

class MockLanguageClient {
    start() { return createDisposable(); }
    stop() { return Promise.resolve(); }
}

Module.prototype.require = function(id) {
    if (id === 'vscode') return vscode;
    if (id === 'vscode-languageclient/node') {
        return {
            CloseAction: {Restart: 1},
            ErrorAction: {Continue: 1},
            LanguageClient: MockLanguageClient,
            RevealOutputChannelOn: {Never: 0},
            TransportKind: {ipc: 1},
        };
    }
    return originalRequire.apply(this, arguments);
};

function fireWorkspaceChange(document) {
    for (const listener of workspaceListeners.change) listener({document});
}

function fireWebviewMessage(panel, message) {
    for (const l of panel.webview.receiveMessageListeners) l(message);
}

function fireActiveEditor(editor) {
    vscode.window.activeTextEditor = editor;
    for (const l of windowListeners.activeEditor) l(editor);
}

function sleep(ms) { return new Promise(r => setTimeout(r, ms)); }

async function main() {
    const distBundle = fs.readFileSync(distExtensionFile, 'utf8');
    if (distBundle.includes('FCSTM embedded Mermaid runtime')
        || distBundle.includes('loadMermaidBrowserBundle')
        || /mermaid\.min\.js/.test(distBundle)
        || distBundle.includes('@fcstm/mermaid-inline')) {
        throw new Error('Bundled dist/extension.js still wires up the Mermaid webview runtime — remove it.');
    }
    if (!distBundle.includes('FCSTM embedded ELK runtime')) {
        throw new Error('Bundled dist/extension.js does not embed the ELK runtime.');
    }
    if (!distBundle.includes('FCSTM embedded preview-webview bundle')) {
        throw new Error('Bundled dist/extension.js does not embed the preview-webview Vue bundle.');
    }
    const webviewBundlePath = path.resolve(__dirname, '..', 'dist', 'preview-webview.js');
    if (!fs.existsSync(webviewBundlePath)) {
        throw new Error(`preview-webview bundle missing at ${webviewBundlePath}.`);
    }
    const webviewBundle = fs.readFileSync(webviewBundlePath, 'utf8');
    if (!/new ELK\b/.test(webviewBundle)) {
        throw new Error('preview-webview bundle does not instantiate the ELK layout engine.');
    }
    if (!webviewBundle.includes('createApp') || !webviewBundle.includes('NConfigProvider')) {
        throw new Error('preview-webview bundle does not bootstrap the Vue 3 + Naive UI shell.');
    }

    fs.writeFileSync(previewFile, [
        'def int counter = 0;',
        'state Fleet {',
        '    event Start named "Go & Run";',
        '    state Idle;',
        '    state Running;',
        '    [*] -> Idle;',
        '    Idle -> Running : Start effect {',
        '        counter = counter + 1;',
        '        counter = counter + 2;',
        '    };',
        '    Running -> [*] : Start;',
        '}',
    ].join('\n'));

    const document = createDocument(previewFile, fs.readFileSync(previewFile, 'utf8'));
    const editor = {document};
    vscode.workspace.textDocuments = [document];
    vscode.window.activeTextEditor = null;

    const extension = require('../out/extension.js');
    const context = {
        subscriptions: [],
        extensionUri: {fsPath: path.resolve(__dirname, '..')},
        asAbsolutePath(r) { return path.resolve(path.join(__dirname, '..', r)); },
    };

    extension.activate(context);

    for (const name of ['fcstm.preview.open', 'fcstm.preview.openAlone', 'fcstm.preview.toggle']) {
        if (!registeredCommands.has(name)) throw new Error(`Command not registered: ${name}`);
    }

    await registeredCommands.get('fcstm.preview.open')(document.uri);
    await sleep(900);

    if (createdPanels.length !== 1) {
        throw new Error(`Expected 1 preview panel, got ${createdPanels.length}.`);
    }
    const panel = createdPanels[0];
    if (panel.showOptions.viewColumn !== vscode.ViewColumn.Beside) {
        throw new Error('Preview panel was not opened beside the editor.');
    }
    if (!panel.webview.html.includes('FCSTM Preview')) {
        throw new Error('Preview webview HTML was not initialized.');
    }
    if (!panel.webview.html.includes('FCSTM embedded ELK runtime')) {
        throw new Error('Preview webview HTML does not embed the ELK runtime.');
    }
    if (panel.webview.html.includes('mermaid') || panel.webview.html.includes('stateDiagram-v2')) {
        throw new Error('Preview webview HTML still references Mermaid.');
    }
    if (!panel.webview.html.includes('FCSTM embedded preview-webview bundle')) {
        throw new Error('Preview webview HTML does not embed the Vue preview bundle.');
    }
    if (!panel.webview.html.includes('window.__FCSTM_INITIAL_STATE__')) {
        throw new Error('Preview webview HTML does not seed __FCSTM_INITIAL_STATE__.');
    }
    if (!panel.webview.html.includes('<div id="app">')) {
        throw new Error('Preview webview HTML does not expose the Vue mount point.');
    }
    // Markers from the Vue/Naive UI bundle proper.
    if (!panel.webview.html.includes('fcstm-toolbar')) {
        throw new Error('Preview webview bundle does not ship the Toolbar component.');
    }
    if (!panel.webview.html.includes('fcstm-stage')) {
        throw new Error('Preview webview bundle does not ship the Stage component.');
    }
    if (!panel.webview.html.includes('fcstm-details')) {
        throw new Error('Preview webview bundle does not ship the Details panel component.');
    }
    if (panel.postedMessages.length === 0) {
        throw new Error('Preview panel did not receive any rendered state.');
    }

    const firstMessage = panel.postedMessages[panel.postedMessages.length - 1];
    if (!firstMessage.payload) {
        throw new Error('Rendered preview payload is missing.');
    }
    if (firstMessage.rootStateName !== 'Fleet') {
        throw new Error(`Unexpected root state in preview: ${JSON.stringify(firstMessage.rootStateName)}`);
    }
    if (firstMessage.payload.graph.id !== '__canvas__') {
        throw new Error('Preview payload graph root should be __canvas__.');
    }
    if (!Array.isArray(firstMessage.payload.graph.children) || firstMessage.payload.graph.children.length === 0) {
        throw new Error('Preview payload graph has no children.');
    }
    const rootFleet = firstMessage.payload.graph.children.find(c => c.fcstm && c.fcstm.qualifiedName === 'Fleet');
    if (!rootFleet) {
        throw new Error('Preview payload graph should contain Fleet state.');
    }
    if (!rootFleet.children || rootFleet.children.length === 0) {
        throw new Error('Fleet state should contain Idle and Running children.');
    }
    const hasIdle = rootFleet.children.some(c => c.fcstm && c.fcstm.qualifiedName === 'Fleet.Idle');
    const hasRunning = rootFleet.children.some(c => c.fcstm && c.fcstm.qualifiedName === 'Fleet.Running');
    if (!hasIdle || !hasRunning) {
        throw new Error('Fleet children should include Idle and Running.');
    }
    if (!firstMessage.previewOptions || firstMessage.previewOptions.transitionEffectMode !== 'hide') {
        throw new Error('Preview payload does not expose resolved preview options.');
    }
    // Effect notes are now an internal payload field consumed by the
    // optional Details / inline-note rendering; the bare presence of the
    // array is enough.
    if (!Array.isArray(firstMessage.effectNotes)) {
        throw new Error('Preview payload does not expose the effectNotes field.');
    }
    if (!Array.isArray(firstMessage.sharedEvents) || firstMessage.sharedEvents.length !== 1) {
        throw new Error('Preview payload does not expose shared-event metadata.');
    }
    if (!Array.isArray(firstMessage.collapsedStateIds)) {
        throw new Error('Preview payload does not expose collapsed-state-ids.');
    }
    if (!Array.isArray(firstMessage.payload.states) || firstMessage.payload.states.length < 2) {
        throw new Error('Preview payload must expose flattened state details for the Details panel.');
    }
    if (!firstMessage.payload.states.some(s => s.qualifiedName === 'Fleet.Idle' && s.kind === 'leaf')) {
        throw new Error('Preview payload states do not include Fleet.Idle as a leaf.');
    }
    if (!Array.isArray(firstMessage.payload.transitions) || firstMessage.payload.transitions.length < 1) {
        throw new Error('Preview payload must expose flattened transition details for the Details panel.');
    }
    const initialTransition = firstMessage.payload.transitions.find(t => t.from === 'Fleet.Idle' && t.to === 'Fleet.Running');
    if (!initialTransition || !initialTransition.eventLabel) {
        throw new Error('Preview payload transitions do not carry the Idle→Running event label.');
    }
    if (!panel.webview.html.includes('fcstm-details__title') && !panel.webview.html.includes('fcstm-details')) {
        throw new Error('Preview webview HTML does not expose the Details side panel.');
    }

    fireWebviewMessage(panel, {
        type: 'patchOptions',
        options: {
            transitionEffectMode: 'inline',
            showVariableDefinitions: false,
            eventVisualizationMode: 'none',
        },
    });
    await sleep(520);

    const optionUpdatedMessage = panel.postedMessages[panel.postedMessages.length - 1];
    if (optionUpdatedMessage.previewOptions.transitionEffectMode !== 'inline') {
        throw new Error('Preview options patch did not round-trip through the extension host.');
    }
    if (optionUpdatedMessage.variables.length !== 0) {
        throw new Error('Variables should be hidden when showVariableDefinitions is false.');
    }
    if (optionUpdatedMessage.sharedEvents.length !== 0) {
        throw new Error('Shared event legend should be hidden when eventVisualizationMode is none.');
    }
    if (optionUpdatedMessage.effectNotes.length !== 0) {
        throw new Error('Effect notes should be hidden outside note mode.');
    }

    // Collapse state round-trip
    fireWebviewMessage(panel, {type: 'setCollapsed', collapsed: ['Fleet']});
    await sleep(520);
    const collapsedMessage = panel.postedMessages[panel.postedMessages.length - 1];
    if (!collapsedMessage.collapsedStateIds.includes('Fleet')) {
        throw new Error('Collapsed state ids did not round-trip through the extension host.');
    }
    const collapsedFleet = collapsedMessage.payload.graph.children.find(c => c.fcstm && c.fcstm.qualifiedName === 'Fleet');
    if (!collapsedFleet || !collapsedFleet.fcstm.collapsed) {
        throw new Error('Fleet state should be marked collapsed in the payload.');
    }

    // Uncollapse to proceed with further checks
    fireWebviewMessage(panel, {type: 'setCollapsed', collapsed: []});
    await sleep(520);

    // Reveal source round-trip
    fireWebviewMessage(panel, {
        type: 'revealSource',
        range: {start: {line: 1, character: 0}, end: {line: 1, character: 11}},
    });
    await sleep(320);
    if (showTextDocumentCalls.length === 0) {
        throw new Error('revealSource did not invoke showTextDocument.');
    }

    // Export SVG round-trip
    const exportSvgPath = path.join(tempDir, 'export-test.svg');
    vscode.window.showSaveDialog = () => Promise.resolve(vscode.Uri.file(exportSvgPath));
    fireWebviewMessage(panel, {type: 'exportSvg', svg: '<svg xmlns="http://www.w3.org/2000/svg"></svg>'});
    await sleep(320);
    if (!fs.existsSync(exportSvgPath)) {
        throw new Error('exportSvg did not produce an SVG file.');
    }

    // Export PNG round-trip
    const exportPngPath = path.join(tempDir, 'export-test.png');
    vscode.window.showSaveDialog = () => Promise.resolve(vscode.Uri.file(exportPngPath));
    const pngBase64 = Buffer.from([0x89, 0x50, 0x4e, 0x47]).toString('base64');
    fireWebviewMessage(panel, {type: 'exportPng', base64: pngBase64});
    await sleep(320);
    if (!fs.existsSync(exportPngPath)) {
        throw new Error('exportPng did not produce a PNG file.');
    }

    document.update([
        'def int counter = 0;',
        'state Fleet {',
        '    event Start named "Go & Run";',
        '    state Ready;',
        '    state Maintenance;',
        '    [*] -> Ready;',
        '    Ready -> Maintenance : Start;',
        '}',
    ].join('\n'));
    fireWorkspaceChange(document);
    await sleep(520);

    const updatedMessage = panel.postedMessages[panel.postedMessages.length - 1];
    const rootFleet2 = updatedMessage.payload.graph.children.find(c => c.fcstm && c.fcstm.qualifiedName === 'Fleet');
    if (!rootFleet2 || !rootFleet2.children.some(c => c.fcstm && c.fcstm.qualifiedName === 'Fleet.Maintenance')) {
        throw new Error('Preview did not update after document edits.');
    }

    const secondFile = path.join(tempDir, 'other.fcstm');
    fs.writeFileSync(secondFile, [
        'state Machine {',
        '    state Ready;',
        '    [*] -> Ready;',
        '}',
    ].join('\n'));
    const secondDocument = createDocument(secondFile, fs.readFileSync(secondFile, 'utf8'));
    vscode.workspace.textDocuments.push(secondDocument);
    await registeredCommands.get('fcstm.preview.open')(secondDocument.uri);
    await sleep(900);

    const resourceMessage = panel.postedMessages[panel.postedMessages.length - 1];
    if (resourceMessage.rootStateName !== 'Machine') {
        throw new Error('Preview command did not switch when invoked with an explicit resource URI.');
    }

    vscode.window.activeTextEditor = editor;
    fireActiveEditor({document: secondDocument});
    await sleep(520);

    const switchedMessage = panel.postedMessages[panel.postedMessages.length - 1];
    if (switchedMessage.rootStateName !== 'Machine') {
        throw new Error('Preview did not follow active-editor changes.');
    }

    // Toggle: closing then re-opening
    await registeredCommands.get('fcstm.preview.toggle')();
    await sleep(320);
    // Panel should be disposed
    // Re-run toggle to open again
    await registeredCommands.get('fcstm.preview.toggle')();
    await sleep(900);
    if (createdPanels.length !== 2) {
        throw new Error(`Toggle should have created a second panel after close+open; got ${createdPanels.length}.`);
    }

    const manifest = require('../package.json');
    const commandIds = (manifest.contributes.commands || []).map(i => i.command);
    for (const need of ['fcstm.preview.open', 'fcstm.preview.openAlone', 'fcstm.preview.toggle']) {
        if (!commandIds.includes(need)) throw new Error(`Manifest does not contribute command: ${need}`);
    }
    const keybindings = (manifest.contributes.keybindings || []).map(i => i.command);
    if (!keybindings.includes('fcstm.preview.open') || !keybindings.includes('fcstm.preview.toggle')) {
        throw new Error('Manifest does not bind preview keybindings.');
    }

    console.log('✅ Phase 9 preview (ELK) verification passed');
    console.log(`   Panel title: ${panel.title}`);
    console.log(`   Initial status: ${firstMessage.statusText}`);
    console.log(`   Root state: ${firstMessage.rootStateName}`);
    console.log(`   Graph children: ${firstMessage.payload.graph.children.length}`);
    console.log(`   Effect notes: ${firstMessage.effectNotes.length}`);

    await extension.deactivate();
}

main().catch(error => {
    console.error(`❌ Phase 9 preview verification failed: ${error.message}`);
    process.exitCode = 1;
}).finally(() => {
    Module.prototype.require = originalRequire;
    fs.rmSync(tempDir, {recursive: true, force: true});
});

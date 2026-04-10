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
            toString() {
                return this.fsPath;
            },
        },
        getText() {
            return text;
        },
        lineCount: lines().length,
        lineAt(line) {
            return {
                text: lines()[line] || '',
            };
        },
        update(newText) {
            text = newText;
        },
    };
}

function createDisposable(callback = () => {}) {
    return {
        dispose: callback,
    };
}

const workspaceListeners = {
    open: [],
    change: [],
    save: [],
    close: [],
};

const windowListeners = {
    activeEditor: [],
};

const registeredCommands = new Map();
const createdPanels = [];
const warningMessages = [];

const vscode = {
    Uri: {
        joinPath(base, ...segments) {
            return {
                fsPath: path.join(base.fsPath, ...segments),
                toString() {
                    return this.fsPath;
                },
            };
        },
    },
    ViewColumn: {
        Beside: 2,
    },
    commands: {
        registerCommand(name, callback) {
            registeredCommands.set(name, callback);
            return createDisposable(() => registeredCommands.delete(name));
        },
    },
    workspace: {
        textDocuments: [],
        openTextDocument(resource) {
            const resourcePath = typeof resource === 'string' ? resource : resource.fsPath;
            const existingDocument = this.textDocuments.find(document => document.uri.fsPath === resourcePath);
            if (existingDocument) {
                return Promise.resolve(existingDocument);
            }

            const text = fs.readFileSync(resourcePath, 'utf8');
            const document = createDocument(resourcePath, text);
            this.textDocuments.push(document);
            return Promise.resolve(document);
        },
        onDidOpenTextDocument(callback) {
            workspaceListeners.open.push(callback);
            return createDisposable();
        },
        onDidChangeTextDocument(callback) {
            workspaceListeners.change.push(callback);
            return createDisposable();
        },
        onDidSaveTextDocument(callback) {
            workspaceListeners.save.push(callback);
            return createDisposable();
        },
        onDidCloseTextDocument(callback) {
            workspaceListeners.close.push(callback);
            return createDisposable();
        },
    },
    window: {
        activeTextEditor: null,
        createOutputChannel() {
            return createDisposable();
        },
        createWebviewPanel(viewType, title, showOptions) {
            const disposeListeners = [];
            const panel = {
                viewType,
                title,
                showOptions,
                revealCalls: [],
                postedMessages: [],
                webview: {
                    cspSource: 'vscode-resource://fcstm',
                    html: '',
                    asWebviewUri(resource) {
                        return {
                            toString() {
                                return `vscode-resource:${resource.fsPath}`;
                            },
                        };
                    },
                    onDidReceiveMessage() {
                        return createDisposable();
                    },
                    postMessage(message) {
                        panel.postedMessages.push(message);
                        return Promise.resolve(true);
                    },
                },
                onDidDispose(listener) {
                    disposeListeners.push(listener);
                    return createDisposable();
                },
                reveal(column, preserveFocus) {
                    panel.revealCalls.push({column, preserveFocus});
                },
                dispose() {
                    while (disposeListeners.length > 0) {
                        const listener = disposeListeners.pop();
                        if (listener) {
                            listener();
                        }
                    }
                },
            };
            createdPanels.push(panel);
            return panel;
        },
        onDidChangeActiveTextEditor(callback) {
            windowListeners.activeEditor.push(callback);
            return createDisposable();
        },
        showWarningMessage(message) {
            warningMessages.push(message);
            return Promise.resolve(message);
        },
    },
};

class MockLanguageClient {
    start() {
        return createDisposable();
    }

    stop() {
        return Promise.resolve();
    }
}

Module.prototype.require = function(id) {
    if (id === 'vscode') {
        return vscode;
    }
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
    for (const listener of workspaceListeners.change) {
        listener({document});
    }
}

function fireActiveEditor(editor) {
    vscode.window.activeTextEditor = editor;
    for (const listener of windowListeners.activeEditor) {
        listener(editor);
    }
}

function sleep(ms) {
    return new Promise(resolve => setTimeout(resolve, ms));
}

async function main() {
    const distBundle = fs.readFileSync(distExtensionFile, 'utf8');
    if (distBundle.includes('svgdom') || distBundle.includes('elkjs/lib/elk.bundled.js')) {
        throw new Error('The bundled dist/extension.js still contains the removed ELK/SVG preview stack.');
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
        asAbsolutePath(relativePath) {
            return path.resolve(path.join(__dirname, '..', relativePath));
        },
    };

    extension.activate(context);

    if (!registeredCommands.has('fcstm.preview.open')) {
        throw new Error('Preview command was not registered.');
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
    if (panel.postedMessages.length === 0) {
        throw new Error('Preview panel did not receive any rendered state.');
    }

    const firstMessage = panel.postedMessages[panel.postedMessages.length - 1];
    if (!panel.webview.html.includes('FCSTM embedded Mermaid runtime')) {
        throw new Error('Preview webview HTML does not embed the Mermaid runtime.');
    }
    if (panel.webview.html.includes('node_modules/mermaid') || panel.webview.html.includes('dist/webview/mermaid.min.js')) {
        throw new Error('Preview webview HTML still references an external Mermaid script.');
    }
    if (!firstMessage.mermaidSource || !firstMessage.mermaidSource.includes('stateDiagram-v2')) {
        throw new Error('Rendered preview Mermaid source is missing.');
    }
    if (firstMessage.rootStateName !== 'Fleet') {
        throw new Error(`Unexpected root state in preview: ${JSON.stringify(firstMessage.rootStateName)}`);
    }
    if (!firstMessage.mermaidSource.includes('[*] -->')) {
        throw new Error('Preview Mermaid source does not contain start transitions.');
    }
    if (firstMessage.mermaidSource.includes('state "Fleet"')) {
        throw new Error('Preview Mermaid source should flatten the root state wrapper.');
    }
    if (!firstMessage.mermaidSource.includes('state "Idle"')) {
        throw new Error('Preview Mermaid source does not contain the expected child states.');
    }
    if (!firstMessage.mermaidSource.includes('Go & Run')) {
        throw new Error('Preview Mermaid source does not expose the shared event label.');
    }
    if (!Array.isArray(firstMessage.sharedEvents) || firstMessage.sharedEvents.length !== 1) {
        throw new Error('Preview payload does not expose shared-event metadata.');
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
    if (!updatedMessage.mermaidSource.includes('Maintenance')) {
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

    const manifest = require('../package.json');
    const commandIds = (manifest.contributes.commands || []).map(item => item.command);
    if (!commandIds.includes('fcstm.preview.open')) {
        throw new Error('Manifest does not contribute the preview command.');
    }
    const editorContextCommands = ((manifest.contributes.menus || {})['editor/context'] || []).map(item => item.command);
    if (!editorContextCommands.includes('fcstm.preview.open')) {
        throw new Error('Manifest does not expose the preview command in the editor context menu.');
    }
    const explorerContextCommands = ((manifest.contributes.menus || {})['explorer/context'] || []).map(item => item.command);
    if (!explorerContextCommands.includes('fcstm.preview.open')) {
        throw new Error('Manifest does not expose the preview command in the explorer context menu.');
    }
    const keybindingCommands = (manifest.contributes.keybindings || []).map(item => item.command);
    if (!keybindingCommands.includes('fcstm.preview.open')) {
        throw new Error('Manifest does not contribute a preview keybinding.');
    }

    console.log('✅ Phase 9 preview verification passed');
    console.log(`   Panel title: ${panel.title}`);
    console.log(`   Initial status: ${firstMessage.statusText}`);
    console.log(`   Updated root: ${switchedMessage.rootStateName}`);

    await extension.deactivate();
}

main().catch(error => {
    console.error(`❌ Phase 9 preview verification failed: ${error.message}`);
    process.exitCode = 1;
}).finally(() => {
    Module.prototype.require = originalRequire;
    fs.rmSync(tempDir, {recursive: true, force: true});
});

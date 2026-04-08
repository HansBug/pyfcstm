import {
    Connection,
    createConnection,
    ProposedFeatures,
} from 'vscode-languageserver/node';

import {FcstmLanguageServerCore} from './core';

/**
 * Bind the FCSTM language server core to a concrete LSP connection.
 */
export function createFcstmLanguageServer(
    connection: Connection = createConnection(ProposedFeatures.all)
): {
    connection: Connection;
    core: FcstmLanguageServerCore;
    listen(): void;
} {
    const core = new FcstmLanguageServerCore({
        onDiagnostics(publication) {
            connection.sendDiagnostics({
                uri: publication.uri,
                version: publication.version,
                diagnostics: publication.diagnostics,
            });
        },
    });

    connection.onInitialize(async params => {
        await core.setWorkspaceFolders(params.workspaceFolders || []);
        return core.getInitializeResult();
    });

    connection.onDidOpenTextDocument(async params => {
        await core.openTextDocument(params.textDocument);
    });

    connection.onDidChangeTextDocument(async params => {
        await core.changeTextDocument(
            params.textDocument.uri,
            params.textDocument.version,
            params.contentChanges
        );
    });

    connection.onDidSaveTextDocument(async params => {
        await core.saveTextDocument(params.textDocument.uri);
    });

    connection.onDidCloseTextDocument(async params => {
        await core.closeTextDocument(params.textDocument.uri);
    });

    connection.onDocumentSymbol(async (params, token) => {
        return core.provideDocumentSymbols(params.textDocument.uri, token);
    });

    connection.onCompletion(async (params, token) => {
        return core.provideCompletionItems(params.textDocument.uri, params.position, token);
    });

    connection.onHover(async (params, token) => {
        return core.provideHover(params.textDocument.uri, params.position, token);
    });

    connection.onDefinition(async (params, token) => {
        return core.provideDefinition(params.textDocument.uri, params.position, token);
    });

    connection.onDocumentLinks(async (params, token) => {
        return core.provideDocumentLinks(params.textDocument.uri, token);
    });

    connection.onInitialized(() => {
        connection.workspace.onDidChangeWorkspaceFolders(async event => {
            await core.applyWorkspaceFolderChange(event.added, event.removed);
        });
    });

    connection.onShutdown(() => {
        core.dispose();
    });

    return {
        connection,
        core,
        listen() {
            connection.listen();
        },
    };
}

/**
 * Start the FCSTM language server on stdio / IPC transports provided by the
 * vscode-languageserver runtime.
 */
export function startFcstmLanguageServer(): void {
    createFcstmLanguageServer().listen();
}

import * as path from 'path';

import * as vscode from 'vscode';
import {
    CloseAction,
    ErrorAction,
    LanguageClient,
    LanguageClientOptions,
    RevealOutputChannelOn,
    ServerOptions,
    TransportKind,
} from 'vscode-languageclient/node';

let client: LanguageClient | null = null;

/**
 * Activate the FCSTM VSCode extension.
 *
 * The extension host stays intentionally thin. All FCSTM language semantics
 * are served through the bundled jsfcstm-based language server.
 */
export function activate(context: vscode.ExtensionContext): void {
    const serverModule = context.asAbsolutePath(path.join('dist', 'server.js'));
    const outputChannel = vscode.window.createOutputChannel('FCSTM Language Server');

    const serverOptions: ServerOptions = {
        run: {
            module: serverModule,
            transport: TransportKind.ipc,
        },
        debug: {
            module: serverModule,
            transport: TransportKind.ipc,
            options: {
                execArgv: ['--nolazy', '--inspect=6009'],
            },
        },
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            {scheme: 'file', language: 'fcstm'},
            {scheme: 'untitled', language: 'fcstm'},
        ],
        outputChannel,
        revealOutputChannelOn: RevealOutputChannelOn.Never,
        errorHandler: {
            error() {
                return ErrorAction.Continue;
            },
            closed() {
                return CloseAction.Restart;
            },
        },
    };

    client = new LanguageClient(
        'fcstmLanguageServer',
        'FCSTM Language Server',
        serverOptions,
        clientOptions
    );

    context.subscriptions.push(outputChannel, client.start());
}

/**
 * Stop the language client during extension shutdown.
 */
export async function deactivate(): Promise<void> {
    if (!client) {
        return;
    }

    const currentClient = client;
    client = null;
    await currentClient.stop();
}

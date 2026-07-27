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

import {FcstmPreviewController} from './preview';

let client: LanguageClient | null = null;
let previewController: FcstmPreviewController | null = null;

/**
 * Activate the FCSTM VSCode extension.
 *
 * The extension host stays intentionally thin. All FCSTM language semantics
 * are served through the bundled jsfcstm-based language server.
 */
export async function activate(context: vscode.ExtensionContext): Promise<void> {
    const serverModule = context.asAbsolutePath(path.join('dist', 'server.js'));
    // ``LanguageClientOptions.outputChannel`` needs a ``LogOutputChannel``: the
    // client logs through ``info``/``warn``/``error``/``debug``, which a plain
    // output channel does not provide.
    const outputChannel = vscode.window.createOutputChannel('FCSTM Language Server', {log: true});

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

    const readFormatSettings = () => {
        const cfg = vscode.workspace.getConfiguration('fcstm');
        const indentSize = cfg.get<number>('format.indentSize');
        return {
            fcstm: {
                format: {
                    indentSize: indentSize && indentSize > 0 ? indentSize : undefined,
                    elseOnSameLine: cfg.get<boolean>('format.elseOnSameLine'),
                    collapseBlankLines: cfg.get<boolean>('format.collapseBlankLines'),
                    alignMultilineBlockComments: cfg.get<boolean>('format.alignMultilineBlockComments'),
                },
            },
        };
    };

    const clientOptions: LanguageClientOptions = {
        documentSelector: [
            {scheme: 'file', language: 'fcstm'},
            {scheme: 'untitled', language: 'fcstm'},
        ],
        outputChannel,
        revealOutputChannelOn: RevealOutputChannelOn.Never,
        initializationOptions: readFormatSettings(),
        synchronize: {
            configurationSection: 'fcstm',
        },
        errorHandler: {
            error() {
                return {action: ErrorAction.Continue};
            },
            closed() {
                return {action: CloseAction.Restart};
            },
        },
    };

    client = new LanguageClient(
        'fcstmLanguageServer',
        'FCSTM Language Server',
        serverOptions,
        clientOptions
    );

    previewController = new FcstmPreviewController(context);
    context.subscriptions.push(outputChannel, previewController);
    // ``start()`` resolves once the server is up; it is no longer a disposable,
    // so shutdown goes through ``client.stop()`` in ``deactivate`` instead.
    await client.start();
}

/**
 * Stop the language client during extension shutdown.
 */
export async function deactivate(): Promise<void> {
    if (previewController) {
        previewController.dispose();
        previewController = null;
    }

    if (!client) {
        return;
    }

    const currentClient = client;
    client = null;
    await currentClient.stop();
}

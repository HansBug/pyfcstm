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
 * are served through the bundled jsfcstm-based language server. Activation
 * deliberately does not wait for, or fail with, the language server: the
 * preview feature works without it.
 */
export function activate(context: vscode.ExtensionContext): void {
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
    // ``start()`` is no longer a disposable, so shutdown goes through
    // ``client.stop()`` in ``deactivate`` instead. It is intentionally not
    // awaited: activation would otherwise block on the initialize handshake,
    // and a rejected activation makes VSCode drop the extension without
    // disposing ``context.subscriptions`` or calling ``deactivate``, which
    // would take the server-independent preview feature down with it.
    client.start().catch((err: unknown) => {
        outputChannel.error('FCSTM language server failed to start', err);
    });
}

/**
 * Stop the language client during extension shutdown.
 *
 * Shutdown degrades gracefully: a language client that never reached the
 * running state cannot be stopped, and that must not turn into a deactivation
 * failure.
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
    try {
        await currentClient.stop();
    } catch (err) {
        // ``BaseLanguageClient.stop()`` rejects with an ``Error`` whenever the
        // client is not in the running state: the server could not be forked,
        // the initialize handshake failed, or the window closed while the
        // handshake was still in flight. Nothing is left to shut down in those
        // cases, so record the reason instead of failing deactivation.
        if (!(err instanceof Error)) {
            throw err;
        }
        console.error('FCSTM language client was not running at shutdown:', err.message);
    }
}

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
        // On every rejection path reachable here the client has already written
        // the failure to the output channel with a forced reveal, so nothing is
        // dropped silently. This handler only keeps the rejection from going
        // unhandled, and deliberately does not write to the channel itself: the
        // rejection can land after ``deactivate`` disposed it, and every log
        // method on a disposed channel throws. In that same window the client's
        // own log throws too, so ``err`` there is the channel error rather than
        // the startup cause -- one more reason to keep this handler trivial.
        console.error('FCSTM language server failed to start:', err);
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
        // ``stop()`` must be called even when it is known to reject: the node
        // transport reaps the forked server process in a ``finally`` attached to
        // ``shutdown()``, and that runs on the rejection path too. Guarding this
        // call behind ``isRunning()`` would look tidier and would leak the child.
        //
        // Not every non-running state rejects. ``stopped`` and ``initial``
        // return early and resolve, and ``initial`` is what the ``Restart``
        // close action leaves behind. What does reject is ``starting`` and
        // ``startFailed`` -- the server could not be forked, the initialize
        // handshake failed, or the window closed mid-handshake -- plus a
        // ``stopping`` client with no stop promise, which rejects with a
        // different message. The client throws no dedicated subclass, so
        // ``Error`` is the narrowest class available here; anything else is
        // unexpected and propagates.
        //
        // Reaping is best effort. The transport gives the child two seconds,
        // but the extension host usually exits first, so the real guarantee is
        // the server's own parent-liveness watchdog: it is armed at startup
        // from ``--clientProcessId`` and exits within about three seconds of
        // the host going away.
        if (!(err instanceof Error)) {
            throw err;
        }
        console.error('FCSTM language client was not running at shutdown:', err.message);
    }
}

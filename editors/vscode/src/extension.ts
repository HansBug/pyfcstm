/**
 * FCSTM Language Support Extension for VSCode
 *
 * This extension provides language support for FCSTM (Finite State Machine) DSL,
 * including syntax highlighting, snippets, and parser-backed features.
 */

import * as vscode from 'vscode';
import { getParser } from './parser';
import { FcstmDiagnosticsProvider } from './diagnostics';
import { FcstmDocumentSymbolProvider } from './symbols';
import { FcstmCompletionProvider } from './completion';
import { FcstmHoverProvider } from './hover';

/**
 * Extension activation
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('FCSTM Language Support extension is now active');

    // Initialize parser
    const parser = getParser();

    // Register diagnostics provider (P0.3)
    const diagnosticsProvider = new FcstmDiagnosticsProvider();
    diagnosticsProvider.register(context);

    // Register document symbol provider (P0.4)
    const symbolProvider = new FcstmDocumentSymbolProvider();
    context.subscriptions.push(
        vscode.languages.registerDocumentSymbolProvider(
            { language: 'fcstm' },
            symbolProvider
        )
    );

    // Register completion provider (P0.5)
    const completionProvider = new FcstmCompletionProvider();
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            { language: 'fcstm' },
            completionProvider,
            '.', ':', '/'  // Trigger characters
        )
    );

    // Register hover provider (P0.6)
    const hoverProvider = new FcstmHoverProvider();
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { language: 'fcstm' },
            hoverProvider
        )
    );

    // Register a simple command to test parser availability
    const testParserCommand = vscode.commands.registerCommand(
        'fcstm.testParser',
        async () => {
            const isAvailable = parser.isAvailable();
            if (isAvailable) {
                vscode.window.showInformationMessage('FCSTM parser is available');
            } else {
                vscode.window.showWarningMessage(
                    'FCSTM parser runtime is not available. Please rebuild the extension artifacts.'
                );
            }
        }
    );

    context.subscriptions.push(testParserCommand);
}

/**
 * Extension deactivation
 */
export function deactivate() {
    console.log('FCSTM Language Support extension is now deactivated');
}

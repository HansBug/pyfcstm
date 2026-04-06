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
import { FcstmDefinitionProvider } from './definition';

/**
 * Extension activation
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('[FCSTM Extension] Starting activation...');
    console.log('[FCSTM Extension] Extension path:', context.extensionPath);

    // Initialize parser
    const parser = getParser();
    console.log('[FCSTM Extension] Parser instance created');

    // Register diagnostics provider (P0.3)
    console.log('[FCSTM Extension] Registering diagnostics provider...');
    const diagnosticsProvider = new FcstmDiagnosticsProvider();
    diagnosticsProvider.register(context);
    console.log('[FCSTM Extension] Diagnostics provider registered');

    // Register document symbol provider (P0.4)
    console.log('[FCSTM Extension] Registering document symbol provider...');
    const symbolProvider = new FcstmDocumentSymbolProvider();
    context.subscriptions.push(
        vscode.languages.registerDocumentSymbolProvider(
            { language: 'fcstm' },
            symbolProvider
        )
    );
    console.log('[FCSTM Extension] Document symbol provider registered');

    // Register completion provider (P0.5)
    console.log('[FCSTM Extension] Registering completion provider...');
    const completionProvider = new FcstmCompletionProvider();
    context.subscriptions.push(
        vscode.languages.registerCompletionItemProvider(
            { language: 'fcstm' },
            completionProvider,
            '.', ':', '/'  // Trigger characters
        )
    );
    console.log('[FCSTM Extension] Completion provider registered');

    // Register hover provider (P0.6)
    console.log('[FCSTM Extension] Registering hover provider...');
    const hoverProvider = new FcstmHoverProvider();
    context.subscriptions.push(
        vscode.languages.registerHoverProvider(
            { language: 'fcstm' },
            hoverProvider
        )
    );
    console.log('[FCSTM Extension] Hover provider registered');

    // Register definition provider for import navigation
    console.log('[FCSTM Extension] Registering definition provider...');
    const definitionProvider = new FcstmDefinitionProvider();
    context.subscriptions.push(
        vscode.languages.registerDefinitionProvider(
            { language: 'fcstm' },
            definitionProvider
        )
    );
    console.log('[FCSTM Extension] Definition provider registered');

    // Register a simple command to test parser availability
    const testParserCommand = vscode.commands.registerCommand(
        'fcstm.testParser',
        async () => {
            console.log('[FCSTM Extension] Test parser command invoked');
            const isAvailable = parser.isAvailable();
            console.log('[FCSTM Extension] Parser available:', isAvailable);

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

    console.log('[FCSTM Extension] FCSTM Language Support extension is now active');
}

/**
 * Extension deactivation
 */
export function deactivate() {
    console.log('FCSTM Language Support extension is now deactivated');
}

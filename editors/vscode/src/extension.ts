/**
 * FCSTM Language Support Extension for VSCode
 *
 * This extension provides language support for FCSTM (Finite State Machine) DSL,
 * including syntax highlighting, snippets, and parser-backed features.
 */

import * as vscode from 'vscode';
import { getParser } from './parser';

/**
 * Extension activation
 */
export function activate(context: vscode.ExtensionContext) {
    console.log('FCSTM Language Support extension is now active');

    // Initialize parser
    const parser = getParser();

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

    // Future: Register diagnostic provider, completion provider, etc.
    // These will be implemented in P0.3, P0.4, P0.5, P0.6
}

/**
 * Extension deactivation
 */
export function deactivate() {
    console.log('FCSTM Language Support extension is now deactivated');
}

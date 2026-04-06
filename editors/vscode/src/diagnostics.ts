/**
 * FCSTM Diagnostics Provider
 *
 * This module provides syntax diagnostics for FCSTM documents by parsing
 * them with the ANTLR-based parser and converting parse errors to VSCode diagnostics.
 */

import * as vscode from 'vscode';
import { getParser, ParseError } from './parser';
import { getImportWorkspaceIndex } from './imports';

/**
 * Diagnostics provider for FCSTM documents
 */
export class FcstmDiagnosticsProvider {
    private readonly diagnosticCollection: vscode.DiagnosticCollection;
    private readonly parser = getParser();
    private readonly importIndex = getImportWorkspaceIndex();
    private readonly documentVersions = new Map<string, number>();

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('fcstm');
    }

    /**
     * Register the diagnostics provider
     */
    register(context: vscode.ExtensionContext): void {
        context.subscriptions.push(this.diagnosticCollection);

        // Parse on document open
        context.subscriptions.push(
            vscode.workspace.onDidOpenTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.updateDiagnostics(document);
                }
            })
        );

        // Parse on document save
        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.updateDiagnostics(document);
                }
            })
        );

        // Parse on document change (debounced)
        context.subscriptions.push(
            vscode.workspace.onDidChangeTextDocument(event => {
                if (event.document.languageId === 'fcstm') {
                    this.scheduleDiagnostics(event.document);
                }
            })
        );

        // Clear diagnostics on document close
        context.subscriptions.push(
            vscode.workspace.onDidCloseTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.diagnosticCollection.delete(document.uri);
                    this.documentVersions.delete(document.uri.toString());
                }
            })
        );

        // Parse all open FCSTM documents
        vscode.workspace.textDocuments.forEach(document => {
            if (document.languageId === 'fcstm') {
                this.updateDiagnostics(document);
            }
        });
    }

    private debounceTimers = new Map<string, NodeJS.Timeout>();

    /**
     * Schedule diagnostics update with debouncing
     */
    private scheduleDiagnostics(document: vscode.TextDocument): void {
        const uri = document.uri.toString();

        // Clear existing timer
        const existingTimer = this.debounceTimers.get(uri);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        // Schedule new update
        const timer = setTimeout(() => {
            this.updateDiagnostics(document);
            this.debounceTimers.delete(uri);
        }, 500); // 500ms debounce

        this.debounceTimers.set(uri, timer);
    }

    /**
     * Update diagnostics for a document
     */
    private async updateDiagnostics(document: vscode.TextDocument): Promise<void> {
        const uri = document.uri.toString();
        const currentVersion = document.version;

        // Store document version
        this.documentVersions.set(uri, currentVersion);

        try {
            const text = document.getText();
            const parseResult = await this.parser.parse(text);

            // Check if document version changed during parsing
            if (this.documentVersions.get(uri) !== currentVersion) {
                return; // Document changed, skip this result
            }

            const diagnostics = parseResult.errors.map(error =>
                this.convertToDiagnostic(error, document)
            );
            diagnostics.push(...await this.importIndex.collectImportDiagnostics(document));

            this.diagnosticCollection.set(document.uri, diagnostics);
        } catch (error) {
            console.error('Error updating diagnostics:', error);
        }
    }

    /**
     * Convert parser error to VSCode diagnostic
     */
    private convertToDiagnostic(
        error: ParseError,
        document: vscode.TextDocument
    ): vscode.Diagnostic {
        const line = Math.max(0, Math.min(error.line, document.lineCount - 1));
        const lineText = document.lineAt(line).text;
        const column = Math.max(0, Math.min(error.column, lineText.length));

        // Create range for the error
        // Try to highlight the problematic token
        let endColumn = column + 1;

        // If we're at a word character, extend to the end of the word
        if (column < lineText.length && /\w/.test(lineText[column])) {
            while (endColumn < lineText.length && /\w/.test(lineText[endColumn])) {
                endColumn++;
            }
        }
        // If we're at a special character, highlight just that character
        else if (column < lineText.length) {
            endColumn = column + 1;
        }

        const range = new vscode.Range(
            new vscode.Position(line, column),
            new vscode.Position(line, endColumn)
        );

        const severity = error.severity === 'error'
            ? vscode.DiagnosticSeverity.Error
            : vscode.DiagnosticSeverity.Warning;

        const diagnostic = new vscode.Diagnostic(range, error.message, severity);
        diagnostic.source = 'fcstm';

        return diagnostic;
    }

    /**
     * Dispose the diagnostics provider
     */
    dispose(): void {
        this.diagnosticCollection.dispose();
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();
    }
}

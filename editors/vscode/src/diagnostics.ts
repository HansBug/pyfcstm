import * as vscode from 'vscode';
import {collectDocumentDiagnostics} from '@pyfcstm/jsfcstm';
import {toVscodeDiagnostic} from './vscode-converters';

export class FcstmDiagnosticsProvider {
    private readonly diagnosticCollection: vscode.DiagnosticCollection;
    private readonly documentVersions = new Map<string, number>();
    private debounceTimers = new Map<string, NodeJS.Timeout>();

    constructor() {
        this.diagnosticCollection = vscode.languages.createDiagnosticCollection('fcstm');
    }

    register(context: vscode.ExtensionContext): void {
        context.subscriptions.push(this.diagnosticCollection);

        context.subscriptions.push(
            vscode.workspace.onDidOpenTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.updateDiagnostics(document);
                }
            })
        );

        context.subscriptions.push(
            vscode.workspace.onDidSaveTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.updateDiagnostics(document);
                }
            })
        );

        context.subscriptions.push(
            vscode.workspace.onDidChangeTextDocument(event => {
                if (event.document.languageId === 'fcstm') {
                    this.scheduleDiagnostics(event.document);
                }
            })
        );

        context.subscriptions.push(
            vscode.workspace.onDidCloseTextDocument(document => {
                if (document.languageId === 'fcstm') {
                    this.diagnosticCollection.delete(document.uri);
                    this.documentVersions.delete(document.uri.toString());
                }
            })
        );

        vscode.workspace.textDocuments.forEach(document => {
            if (document.languageId === 'fcstm') {
                this.updateDiagnostics(document);
            }
        });
    }

    private scheduleDiagnostics(document: vscode.TextDocument): void {
        const uri = document.uri.toString();
        const existingTimer = this.debounceTimers.get(uri);
        if (existingTimer) {
            clearTimeout(existingTimer);
        }

        const timer = setTimeout(() => {
            this.updateDiagnostics(document);
            this.debounceTimers.delete(uri);
        }, 500);

        this.debounceTimers.set(uri, timer);
    }

    private async updateDiagnostics(document: vscode.TextDocument): Promise<void> {
        const uri = document.uri.toString();
        const currentVersion = document.version;
        this.documentVersions.set(uri, currentVersion);

        try {
            const diagnostics = await collectDocumentDiagnostics(document);
            if (this.documentVersions.get(uri) !== currentVersion) {
                return;
            }

            this.diagnosticCollection.set(
                document.uri,
                diagnostics.map(item => toVscodeDiagnostic(item))
            );
        } catch (error) {
            console.error('Error updating diagnostics:', error);
        }
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();
    }
}

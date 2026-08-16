import * as vscode from 'vscode';
import {collectDocumentDiagnosticsByUri} from '@pyfcstm/jsfcstm';
import {toVscodeDiagnostic} from './vscode-converters';

function diagnosticContributionKey(diagnostic: vscode.Diagnostic): string {
    return JSON.stringify([
        diagnostic.code ?? null,
        diagnostic.severity ?? null,
        diagnostic.source ?? null,
        diagnostic.range,
        diagnostic.relatedInformation ?? null,
    ]);
}

export class FcstmDiagnosticsProvider {
    private readonly diagnosticCollection: vscode.DiagnosticCollection;
    private readonly documentVersions = new Map<string, number>();
    private readonly diagnosticContributions = new Map<string, Map<string, vscode.Diagnostic[]>>();
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
                    const uri = document.uri.toString();
                    const previous = this.diagnosticContributions.get(uri);
                    this.diagnosticContributions.delete(uri);
                    this.documentVersions.delete(uri);
                    const targets = new Set(previous?.keys() || []);
                    if (targets.size === 0) targets.add(uri);
                    this.publishDiagnosticTargets(targets);
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
            const publications = await collectDocumentDiagnosticsByUri(document, uri);
            if (this.documentVersions.get(uri) !== currentVersion) {
                return;
            }

            const next = new Map<string, vscode.Diagnostic[]>();
            for (const [targetUri, diagnostics] of publications) {
                next.set(targetUri, diagnostics.map(item => toVscodeDiagnostic(item)));
            }
            const previous = this.diagnosticContributions.get(uri);
            const targets = new Set([
                ...(previous?.keys() || []),
                ...next.keys(),
            ]);
            this.diagnosticContributions.set(uri, next);
            this.publishDiagnosticTargets(targets);
        } catch (error) {
            console.error('Error updating diagnostics:', error);
        }
    }

    private publishDiagnosticTargets(targets: Iterable<string>): void {
        for (const targetUri of targets) {
            const diagnostics: vscode.Diagnostic[] = [];
            const seen = new Set<string>();
            for (const contribution of this.diagnosticContributions.values()) {
                for (const diagnostic of contribution.get(targetUri) || []) {
                    const key = diagnosticContributionKey(diagnostic);
                    if (seen.has(key)) continue;
                    seen.add(key);
                    diagnostics.push(diagnostic);
                }
            }
            this.diagnosticCollection.set(vscode.Uri.parse(targetUri), diagnostics);
        }
    }

    dispose(): void {
        this.diagnosticCollection.dispose();
        this.debounceTimers.forEach(timer => clearTimeout(timer));
        this.debounceTimers.clear();
        this.diagnosticContributions.clear();
    }
}

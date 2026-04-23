import * as vscode from 'vscode';
import {getWorkspaceGraph} from '@pyfcstm/jsfcstm';

function getWorkspaceFilePath(document: vscode.TextDocument): string | null {
    return document.uri.fsPath || document.fileName || null;
}

export class FcstmWorkspaceSync {
    private readonly graph = getWorkspaceGraph();

    register(context: vscode.ExtensionContext): void {
        const syncDocument = (document: vscode.TextDocument) => {
            if (document.languageId !== 'fcstm') {
                return;
            }

            const filePath = getWorkspaceFilePath(document);
            if (!filePath) {
                return;
            }

            this.graph.setOverlay(filePath, document.getText());
        };

        const removeDocument = (document: vscode.TextDocument) => {
            if (document.languageId !== 'fcstm') {
                return;
            }

            const filePath = getWorkspaceFilePath(document);
            if (!filePath) {
                return;
            }

            this.graph.removeOverlay(filePath);
        };

        context.subscriptions.push(
            vscode.workspace.onDidOpenTextDocument(syncDocument),
            vscode.workspace.onDidChangeTextDocument(event => syncDocument(event.document)),
            vscode.workspace.onDidSaveTextDocument(syncDocument),
            vscode.workspace.onDidCloseTextDocument(removeDocument)
        );

        vscode.workspace.textDocuments.forEach(syncDocument);
    }
}

/**
 * FCSTM definition provider for import paths.
 */

import * as vscode from 'vscode';
import { getImportWorkspaceIndex } from './imports';

export class FcstmDefinitionProvider implements vscode.DefinitionProvider {
    async provideDefinition(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken
    ): Promise<vscode.Definition | null> {
        const index = getImportWorkspaceIndex();
        const resolved = await index.getResolvedImportAtPosition(document, position);
        if (!resolved || !resolved.target.entryFile) {
            return null;
        }

        return new vscode.Location(
            vscode.Uri.file(resolved.target.entryFile),
            new vscode.Position(0, 0)
        );
    }
}

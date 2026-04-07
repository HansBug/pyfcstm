import * as vscode from 'vscode';
import {collectDocumentSymbols} from '@pyfcstm/jsfcstm';
import {toVscodeDocumentSymbol} from './vscode-converters';

export class FcstmDocumentSymbolProvider implements vscode.DocumentSymbolProvider {
    async provideDocumentSymbols(
        document: vscode.TextDocument,
        _token: vscode.CancellationToken
    ): Promise<vscode.DocumentSymbol[]> {
        try {
            const symbols = await collectDocumentSymbols(document);
            return symbols.map(symbol => toVscodeDocumentSymbol(symbol));
        } catch (error) {
            console.error('Error extracting symbols:', error);
            return [];
        }
    }
}

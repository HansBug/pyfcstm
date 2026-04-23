import * as vscode from 'vscode';
import {collectCompletionItems} from '@pyfcstm/jsfcstm';
import {toVscodeCompletionItem} from './vscode-converters';

export class FcstmCompletionProvider implements vscode.CompletionItemProvider {
    async provideCompletionItems(
        document: vscode.TextDocument,
        position: vscode.Position,
        _token: vscode.CancellationToken,
        _context: vscode.CompletionContext
    ): Promise<vscode.CompletionItem[]> {
        const items = await collectCompletionItems(document, position);
        return items.map(item => toVscodeCompletionItem(item));
    }
}

import * as vscode from 'vscode';
import type {
    FcstmCompletionItem,
    FcstmDiagnostic,
    FcstmDocumentSymbol,
    FcstmSymbolKind,
    TextRange,
} from '@pyfcstm/jsfcstm';

function createPosition(line: number, character: number): vscode.Position {
    return new vscode.Position(line, character);
}

export function createVscodeRange(
    startLine: number,
    startCharacter: number,
    endLine: number,
    endCharacter: number
): vscode.Range {
    const RangeCtor = vscode.Range as unknown as { new (...args: unknown[]): vscode.Range; length?: number };
    if ((RangeCtor.length || 0) <= 2) {
        return new RangeCtor(
            createPosition(startLine, startCharacter),
            createPosition(endLine, endCharacter)
        );
    }

    return new RangeCtor(startLine, startCharacter, endLine, endCharacter);
}

export function toVscodeRange(range: TextRange): vscode.Range {
    return createVscodeRange(
        range.start.line,
        range.start.character,
        range.end.line,
        range.end.character
    );
}

export function toVscodeDiagnostic(item: FcstmDiagnostic): vscode.Diagnostic {
    const severity = item.severity === 'error'
        ? vscode.DiagnosticSeverity.Error
        : vscode.DiagnosticSeverity.Warning;
    const diagnostic = new vscode.Diagnostic(toVscodeRange(item.range), item.message, severity);
    diagnostic.source = item.source;
    return diagnostic;
}

export function toVscodeSymbolKind(kind: FcstmSymbolKind): vscode.SymbolKind {
    switch (kind) {
        case 'variable':
            return vscode.SymbolKind.Variable;
        case 'event':
            return vscode.SymbolKind.Event;
        case 'class':
        default:
            return vscode.SymbolKind.Class;
    }
}

export function toVscodeDocumentSymbol(symbol: FcstmDocumentSymbol): vscode.DocumentSymbol {
    const documentSymbol = new vscode.DocumentSymbol(
        symbol.name,
        symbol.detail,
        toVscodeSymbolKind(symbol.kind),
        toVscodeRange(symbol.range),
        toVscodeRange(symbol.selectionRange)
    );
    documentSymbol.children.push(...symbol.children.map(child => toVscodeDocumentSymbol(child)));
    return documentSymbol;
}

export function toVscodeCompletionItem(item: FcstmCompletionItem): vscode.CompletionItem {
    const kindMap: Record<FcstmCompletionItem['kind'], vscode.CompletionItemKind> = {
        keyword: vscode.CompletionItemKind.Keyword,
        constant: vscode.CompletionItemKind.Constant,
        function: vscode.CompletionItemKind.Function,
        variable: vscode.CompletionItemKind.Variable,
        class: vscode.CompletionItemKind.Class,
        event: vscode.CompletionItemKind.Event,
    };

    const completionItem = new vscode.CompletionItem(item.label, kindMap[item.kind]);
    if (item.detail) {
        completionItem.detail = item.detail;
    }
    if (item.documentation) {
        completionItem.documentation = new vscode.MarkdownString(item.documentation);
    }
    if (item.insertText) {
        completionItem.insertText = item.insertTextFormat === 'snippet'
            ? new vscode.SnippetString(item.insertText)
            : item.insertText;
    }
    if (item.sortText) {
        completionItem.sortText = item.sortText;
    }
    return completionItem;
}

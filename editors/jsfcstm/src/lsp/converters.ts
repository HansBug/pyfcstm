import {
    CodeAction,
    CodeActionKind,
    CompletionItem,
    CompletionItemKind,
    Diagnostic,
    DiagnosticSeverity,
    DocumentHighlight,
    DocumentHighlightKind,
    DocumentLink,
    DocumentSymbol,
    FoldingRange,
    Hover,
    InsertTextFormat,
    Location,
    MarkupKind,
    Position,
    Range,
    SelectionRange,
    SymbolInformation,
    SymbolKind,
    SemanticTokens,
    TextEdit,
    WorkspaceEdit,
} from 'vscode-languageserver/node';

import type {
    FcstmCompletionItem,
} from '../editor/completion';
import type {FcstmCodeAction} from '../editor/code-actions';
import type {FcstmHoverResult} from '../editor/hover';
import type {
    FcstmDefinitionLocation,
    FcstmDocumentHighlight,
    FcstmDocumentLink,
    FcstmFoldingRange,
    FcstmSelectionRange,
    FcstmWorkspaceEdit,
    FcstmWorkspaceSymbol,
} from '../editor';
import type {FcstmDocumentSymbol, FcstmSymbolKind} from '../editor/symbols';
import type {FcstmDiagnostic, TextPositionLike, TextRange} from '../utils/text';

function createPosition(line: number, character: number): Position {
    return {line, character};
}

export function toLspPosition(position: TextPositionLike): Position {
    return createPosition(position.line, position.character);
}

export function toLspRange(range: TextRange): Range {
    return {
        start: toLspPosition(range.start),
        end: toLspPosition(range.end),
    };
}

export function toLspDiagnostic(item: FcstmDiagnostic): Diagnostic {
    return {
        range: toLspRange(item.range),
        message: item.message,
        severity: item.severity === 'error'
            ? DiagnosticSeverity.Error
            : DiagnosticSeverity.Warning,
        source: item.source,
        code: item.code,
        data: item.data,
        relatedInformation: item.relatedInformation?.map(info => ({
            location: {
                uri: info.location.uri,
                range: toLspRange(info.location.range),
            },
            message: info.message,
        })),
    };
}

export function toLspSymbolKind(kind: FcstmSymbolKind): SymbolKind {
    switch (kind) {
        case 'module':
            return SymbolKind.Module;
        case 'function':
            return SymbolKind.Function;
        case 'variable':
            return SymbolKind.Variable;
        case 'event':
            return SymbolKind.Event;
        case 'class':
        default:
            return SymbolKind.Class;
    }
}

export function toLspDocumentSymbol(symbol: FcstmDocumentSymbol): DocumentSymbol {
    return {
        name: symbol.name,
        detail: symbol.detail,
        kind: toLspSymbolKind(symbol.kind),
        range: toLspRange(symbol.range),
        selectionRange: toLspRange(symbol.selectionRange),
        children: symbol.children.map(child => toLspDocumentSymbol(child)),
    };
}

export function toLspCompletionItem(item: FcstmCompletionItem): CompletionItem {
    const kindMap: Record<FcstmCompletionItem['kind'], CompletionItemKind> = {
        keyword: CompletionItemKind.Keyword,
        constant: CompletionItemKind.Constant,
        function: CompletionItemKind.Function,
        variable: CompletionItemKind.Variable,
        class: CompletionItemKind.Class,
        event: CompletionItemKind.Event,
    };

    return {
        label: item.label,
        kind: kindMap[item.kind],
        detail: item.detail,
        documentation: item.documentation
            ? {
                kind: MarkupKind.Markdown,
                value: item.documentation,
            }
            : undefined,
        insertText: item.insertText,
        insertTextFormat: item.insertTextFormat === 'snippet'
            ? InsertTextFormat.Snippet
            : InsertTextFormat.PlainText,
        sortText: item.sortText,
    };
}

function makeMarkdownHover(title: string, body: string[], range?: TextRange): Hover {
    return {
        contents: {
            kind: MarkupKind.Markdown,
            value: [`**${title}**`, ...body].join('\n\n'),
        },
        range: range ? toLspRange(range) : undefined,
    };
}

export function toLspHover(hover: FcstmHoverResult): Hover {
    if (hover.kind === 'doc') {
        const body = [hover.doc.description];
        if (hover.doc.example) {
            body.push(`**Example:**\n\n${hover.doc.example}`);
        }
        return makeMarkdownHover(hover.doc.title, body);
    }

    const body = [`Path: \`${hover.sourcePath}\``];
    if (hover.entryFile) {
        body.push(`Resolved file: \`${hover.entryFile}\``);
    } else if (hover.resolvedFile) {
        body.push(`Resolved path: \`${hover.resolvedFile}\``);
    }
    if (hover.rootStateName) {
        body.push(`Root state: \`${hover.rootStateName}\``);
    }
    if (hover.explicitVariables.length > 0) {
        body.push(`Variables: \`${hover.explicitVariables.join('`, `')}\``);
    }
    if (hover.absoluteEvents.length > 0) {
        body.push(`Absolute events: \`${hover.absoluteEvents.join('`, `')}\``);
    }

    return makeMarkdownHover(hover.title, body, hover.range);
}

export function toLspLocation(location: FcstmDefinitionLocation): Location {
    return {
        uri: location.uri,
        range: toLspRange(location.range),
    };
}

export function toLspDocumentLink(link: FcstmDocumentLink): DocumentLink {
    return {
        range: toLspRange(link.range),
        target: link.target,
        tooltip: link.tooltip,
    };
}

export function toLspDocumentHighlight(highlight: FcstmDocumentHighlight): DocumentHighlight {
    const kindMap: Record<FcstmDocumentHighlight['kind'], DocumentHighlightKind> = {
        text: DocumentHighlightKind.Text,
        read: DocumentHighlightKind.Read,
        write: DocumentHighlightKind.Write,
    };

    return {
        range: toLspRange(highlight.range),
        kind: kindMap[highlight.kind],
    };
}

function toLspTextEdit(edit: { range: TextRange; newText: string }): TextEdit {
    return {
        range: toLspRange(edit.range),
        newText: edit.newText,
    };
}

export function toLspWorkspaceEdit(edit: FcstmWorkspaceEdit): WorkspaceEdit {
    return {
        changes: Object.fromEntries(
            Object.entries(edit.changes).map(([uri, edits]) => [uri, edits.map(item => toLspTextEdit(item))])
        ),
    };
}

export function toLspWorkspaceSymbol(symbol: FcstmWorkspaceSymbol): SymbolInformation {
    const kindMap: Record<FcstmWorkspaceSymbol['kind'], SymbolKind> = {
        variable: SymbolKind.Variable,
        tempVariable: SymbolKind.Variable,
        state: SymbolKind.Class,
        event: SymbolKind.Event,
        action: SymbolKind.Function,
        import: SymbolKind.Module,
    };
    return {
        name: symbol.name,
        containerName: symbol.containerName,
        kind: kindMap[symbol.kind],
        location: toLspLocation(symbol.location),
    };
}

/**
 * Convert jsfcstm folding metadata into an LSP ``FoldingRange``.
 */
export function toLspFoldingRange(range: FcstmFoldingRange): FoldingRange {
    return {
        startLine: range.startLine,
        endLine: range.endLine,
        startCharacter: range.startCharacter,
        endCharacter: range.endCharacter,
        kind: range.kind,
    };
}

/**
 * Convert nested jsfcstm selection ranges into the recursive LSP shape.
 */
export function toLspSelectionRange(range: FcstmSelectionRange): SelectionRange {
    return {
        range: toLspRange(range.range),
        parent: range.parent ? toLspSelectionRange(range.parent) : undefined,
    };
}

/**
 * Pass through semantic tokens while keeping a named converter API.
 */
export function toLspSemanticTokens(tokens: SemanticTokens): SemanticTokens {
    return tokens;
}

export function toLspCodeAction(action: FcstmCodeAction): CodeAction {
    const kindMap: Record<FcstmCodeAction['kind'], CodeActionKind> = {
        quickfix: CodeActionKind.QuickFix,
        'refactor.rename': CodeActionKind.RefactorRewrite,
    };

    return {
        title: action.title,
        kind: kindMap[action.kind],
        diagnostics: action.diagnostics?.map(item => toLspDiagnostic(item)),
        edit: action.edit ? toLspWorkspaceEdit(action.edit) : undefined,
    };
}

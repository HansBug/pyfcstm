import {getParser, ParseError} from '../dsl/parser';
import {
    createRange,
    FcstmDiagnostic,
    TextDocumentLike,
} from '../utils/text';
import {getImportWorkspaceIndex} from '../workspace/imports';

export function convertParseErrorToDiagnostic(
    error: ParseError,
    document: TextDocumentLike
): FcstmDiagnostic {
    const safeLineCount = Math.max(1, document.lineCount);
    const line = Math.max(0, Math.min(error.line, safeLineCount - 1));
    const lineText = document.lineAt(line).text;
    const column = Math.max(0, Math.min(error.column, lineText.length));

    let endColumn = column + 1;
    if (column < lineText.length && /\w/.test(lineText[column])) {
        while (endColumn < lineText.length && /\w/.test(lineText[endColumn])) {
            endColumn++;
        }
    } else if (column < lineText.length) {
        endColumn = column + 1;
    }

    return {
        range: createRange(line, column, line, endColumn),
        message: error.message,
        severity: error.severity,
        source: 'fcstm',
    };
}

export async function collectDocumentDiagnostics(
    document: TextDocumentLike
): Promise<FcstmDiagnostic[]> {
    const parseResult = await getParser().parse(document.getText());
    const diagnostics = parseResult.errors.map(error => convertParseErrorToDiagnostic(error, document));
    diagnostics.push(...await getImportWorkspaceIndex().collectImportDiagnostics(document));
    return diagnostics;
}

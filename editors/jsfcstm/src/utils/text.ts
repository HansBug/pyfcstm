export interface TextPositionLike {
    line: number;
    character: number;
}

export interface TextRange {
    start: TextPositionLike;
    end: TextPositionLike;
}

export interface TextLineLike {
    text: string;
}

export interface TextDocumentLike {
    getText(): string;
    lineCount: number;
    lineAt(line: number): TextLineLike;
    filePath?: string;
    uri?: { fsPath?: string };
}

export interface TokenLike {
    line?: number;
    column?: number;
    text?: string;
}

export interface ParseTreeNode {
    start?: TokenLike;
    stop?: TokenLike;
    children?: ParseTreeNode[];
    getText?: () => string;
    constructor?: { name: string };
    pseudo?: TokenLike;
    deftype?: TokenLike;
    state_id?: TokenLike;
    event_name?: TokenLike;
    extra_name?: TokenLike;
    import_path?: TokenLike;
    state_alias?: TokenLike;
    target_text?: TokenLike;
    func_name?: TokenLike;
    aspect?: TokenLike;
    raw_doc?: TokenLike;
    from_state?: TokenLike;
    to_state?: TokenLike;
    from_id?: TokenLike;
    selector_pattern?: TokenLike;
    selector_name?: TokenLike;
    selector_items?: TokenLike[];
    op?: TokenLike;
    isabs?: TokenLike;
    source_event?: { getText?: () => string };
    target_event?: { getText?: () => string };
}

export type FcstmDiagnosticSeverity = 'error' | 'warning';

export interface FcstmDiagnostic {
    range: TextRange;
    message: string;
    severity: FcstmDiagnosticSeverity;
    source: string;
    code?: string;
    data?: Record<string, unknown>;
}

export function createRange(
    startLine: number,
    startCharacter: number,
    endLine: number,
    endCharacter: number
): TextRange {
    return {
        start: {
            line: startLine,
            character: startCharacter,
        },
        end: {
            line: endLine,
            character: endCharacter,
        },
    };
}

export function cloneRange(range: TextRange): TextRange {
    return createRange(
        range.start.line,
        range.start.character,
        range.end.line,
        range.end.character
    );
}

export function getDocumentFilePath(document: TextDocumentLike): string {
    return document.filePath || document.uri?.fsPath || '';
}

export function tokenText(token?: TokenLike): string {
    return token?.text || '';
}

export function makeTokenRange(
    token: TokenLike | undefined,
    document: TextDocumentLike
): TextRange | undefined {
    if (!token || token.line == null || token.column == null) {
        return undefined;
    }

    const safeLineCount = Math.max(1, document.lineCount);
    const line = Math.max(0, Math.min((token.line || 1) - 1, safeLineCount - 1));
    const lineText = document.lineAt(line).text;
    const column = Math.max(0, Math.min(token.column || 0, lineText.length));
    const text = token.text || '';
    const end = Math.max(column + 1, Math.min(column + text.length, lineText.length));
    return createRange(line, column, line, end);
}

export function makeNodeRange(
    node: ParseTreeNode,
    document: TextDocumentLike
): TextRange | undefined {
    const startToken = node.start;
    const stopToken = node.stop;
    if (
        !startToken
        || !stopToken
        || startToken.line == null
        || startToken.column == null
        || stopToken.line == null
        || stopToken.column == null
    ) {
        return undefined;
    }

    const safeLineCount = Math.max(1, document.lineCount);
    const startLine = Math.max(0, Math.min(startToken.line - 1, safeLineCount - 1));
    const endLine = Math.max(0, Math.min(stopToken.line - 1, safeLineCount - 1));
    const endColumn = Math.max(
        stopToken.column + 1,
        stopToken.column + (stopToken.text ? stopToken.text.length : 1)
    );

    return createRange(startLine, startToken.column, endLine, endColumn);
}

export function fallbackRangeFromText(
    document: TextDocumentLike,
    text: string,
    search: string,
    startLine = 0
): TextRange {
    const lines = text.split('\n');
    for (let line = startLine; line < lines.length; line++) {
        const column = lines[line].indexOf(search);
        if (column >= 0) {
            return createRange(line, column, line, column + search.length);
        }
    }

    const safeLineCount = Math.max(1, document.lineCount);
    return createRange(0, 0, 0, safeLineCount > 0 ? 1 : 0);
}

export function rangeContains(range: TextRange, position: TextPositionLike): boolean {
    if (position.line < range.start.line || position.line > range.end.line) {
        return false;
    }
    if (position.line === range.start.line && position.character < range.start.character) {
        return false;
    }
    if (position.line === range.end.line && position.character > range.end.character) {
        return false;
    }
    return true;
}

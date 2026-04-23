import {createRange, TextDocumentLike, TextRange} from '../utils/text';

const IDENTIFIER_RE = /[A-Za-z0-9_]/;

function escapeRegex(text: string): string {
    return text.replace(/[.*+?^${}()|[\]\\]/g, '\\$&');
}

function isIdentifierBoundary(text: string, index: number): boolean {
    if (index < 0 || index >= text.length) {
        return true;
    }

    return !IDENTIFIER_RE.test(text[index]);
}

/**
 * Return a range length that is stable enough for choosing the narrowest hit.
 */
export function rangeLength(range: TextRange): number {
    if (range.start.line === range.end.line) {
        return Math.max(0, range.end.character - range.start.character);
    }

    return (range.end.line - range.start.line) * 10000
        + Math.max(0, range.end.character - range.start.character);
}

/**
 * Check whether two ranges overlap.
 */
export function rangeIntersects(left: TextRange, right: TextRange): boolean {
    if (left.end.line < right.start.line || right.end.line < left.start.line) {
        return false;
    }
    if (left.end.line === right.start.line && left.end.character < right.start.character) {
        return false;
    }
    if (right.end.line === left.start.line && right.end.character < left.start.character) {
        return false;
    }
    return true;
}

/**
 * Find an identifier occurrence inside a larger AST node range.
 *
 * Some grammar nodes only expose a full statement range. This helper narrows
 * the range back to the named segment that editor features should edit.
 */
export function findIdentifierRange(
    document: TextDocumentLike,
    name: string | undefined,
    outerRange: TextRange,
    options: {preferLast?: boolean} = {}
): TextRange {
    if (!name) {
        return outerRange;
    }

    const matcher = new RegExp(escapeRegex(name), 'g');
    let best: TextRange | null = null;
    const startLine = Math.max(0, outerRange.start.line);
    const endLine = Math.max(startLine, Math.min(document.lineCount - 1, outerRange.end.line));

    for (let line = startLine; line <= endLine; line++) {
        const lineText = document.lineAt(line).text;
        const lineStart = line === outerRange.start.line ? outerRange.start.character : 0;
        const lineEnd = line === outerRange.end.line ? outerRange.end.character : lineText.length;
        const slice = lineText.slice(lineStart, Math.max(lineStart, lineEnd));
        matcher.lastIndex = 0;

        let match: RegExpExecArray | null;
        while ((match = matcher.exec(slice)) !== null) {
            const column = lineStart + match.index;
            const afterColumn = column + name.length;
            if (!isIdentifierBoundary(lineText, column - 1) || !isIdentifierBoundary(lineText, afterColumn)) {
                continue;
            }

            const range = createRange(line, column, line, afterColumn);
            if (!options.preferLast) {
                return range;
            }
            best = range;
        }
    }

    return best || outerRange;
}

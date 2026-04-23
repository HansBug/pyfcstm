/**
 * Conservative FCSTM document formatter.
 *
 * The formatter normalizes indentation by brace depth, trims trailing
 * whitespace on every line, and collapses runs of blank lines to a single
 * blank line. It deliberately does NOT rewrite inner token spacing or
 * reformat expressions — the FCSTM lexer skips ``//`` and ``#`` line
 * comments, so an AST-level pretty printer would silently drop them. A
 * text-level scanner that respects strings and ``/* ... *\/`` comments
 * preserves every comment style and every intentional inline space.
 */
import type {TextDocumentLike, TextRange} from '../utils/text';
import {createRange} from '../utils/text';

export interface FcstmFormatOptions {
    /**
     * Number of spaces used for one indentation level. Defaults to 4 to match
     * the project style used by the built-in ``templates/`` corpus.
     */
    indentSize?: number;

    /**
     * When ``true`` (default), three or more consecutive blank lines are
     * collapsed into a single blank line.
     */
    collapseBlankLines?: boolean;
}

export interface FcstmTextEdit {
    range: TextRange;
    newText: string;
}

interface ScanResult {
    /** Indent depth contributed by braces entirely on this logical line. */
    indentBefore: number;
    indentAfter: number;
    /** ``true`` if this line is purely blank after trimming. */
    isBlank: boolean;
    /** ``true`` while the scanner is still inside an unterminated ``/* *\/`` block. */
    inBlockComment: boolean;
    /**
     * Character offset of the first real ``#`` line-comment marker on this
     * line, or -1 if this line does not start a ``#`` line comment outside
     * of strings and block comments. Used by the formatter to normalize
     * Python-style line comments into ``//`` form.
     */
    hashCommentAt: number;
}

/**
 * Scan a single source line with awareness of string literals and block
 * comments carried across from previous lines. Returns the net indent
 * contribution and the running block-comment state.
 */
function scanLine(
    line: string,
    inBlockCommentIn: boolean
): ScanResult {
    let indentAfter = 0;
    let indentBefore = 0;
    let inBlockComment = inBlockCommentIn;
    let inString: '"' | '\'' | null = null;
    let hashCommentAt = -1;

    const trimmed = line.trim();
    const isBlank = trimmed.length === 0;

    for (let i = 0; i < line.length; i++) {
        const char = line[i];
        const next = i + 1 < line.length ? line[i + 1] : '';

        if (inBlockComment) {
            if (char === '*' && next === '/') {
                inBlockComment = false;
                i += 1;
            }
            continue;
        }

        if (inString) {
            if (char === '\\') {
                // Skip the next char so escape sequences do not exit the string early.
                i += 1;
                continue;
            }
            if (char === inString) {
                inString = null;
            }
            continue;
        }

        if (char === '/' && next === '*') {
            inBlockComment = true;
            i += 1;
            continue;
        }
        if (char === '/' && next === '/') {
            break;
        }
        if (char === '#') {
            hashCommentAt = i;
            break;
        }
        if (char === '"' || char === '\'') {
            inString = char;
            continue;
        }
        if (char === '{' || char === '[') {
            indentAfter += 1;
        } else if (char === '}' || char === ']') {
            if (indentAfter > 0) {
                indentAfter -= 1;
            } else {
                indentBefore += 1;
            }
        }
    }

    return {indentBefore, indentAfter, isBlank, inBlockComment, hashCommentAt};
}

/**
 * Rewrite a line so that a Python-style ``#`` line comment becomes the
 * canonical ``//`` form. ``//`` is chosen because FCSTM is otherwise a
 * C-family language (braces, semicolons, ``::``/``:``/``->``), and VSCode's
 * line-comment toggle inserts ``//`` as well, so the muscle memory lines up.
 *
 * A single space is inserted after the ``//`` marker when the original
 * ``#`` had no space, so ``#note`` becomes ``// note``. Lines inside
 * strings or multiline ``/* *\/`` regions (which FCSTM treats as semantic
 * ``raw_doc`` payload, NOT as discardable comments) are never touched.
 */
function normalizeHashComment(line: string, hashCommentAt: number): string {
    if (hashCommentAt < 0) {
        return line;
    }
    const before = line.slice(0, hashCommentAt);
    const after = line.slice(hashCommentAt + 1);
    const needsSpace = after.length > 0 && after[0] !== ' ' && after[0] !== '\t';
    return `${before}//${needsSpace ? ' ' : ''}${after}`;
}

function detectLineEnding(text: string): string {
    const first = text.indexOf('\n');
    if (first < 0) {
        return '\n';
    }
    if (first > 0 && text[first - 1] === '\r') {
        return '\r\n';
    }
    return '\n';
}

/**
 * Produce whole-document text edits that normalize indentation, trailing
 * whitespace, and blank-line runs.
 *
 * The return shape is intentionally kept as a single edit that replaces the
 * whole document rather than a minimal diff. LSP clients apply this
 * atomically and it avoids subtle range-clipping issues around the last line.
 */
export function formatDocumentText(
    document: TextDocumentLike,
    options: FcstmFormatOptions = {}
): FcstmTextEdit[] {
    const indentSize = options.indentSize && options.indentSize > 0
        ? options.indentSize
        : 4;
    const collapseBlankLines = options.collapseBlankLines !== false;

    const originalText = document.getText();
    const lineEnding = detectLineEnding(originalText);

    // Split the document into lines while preserving whether a trailing
    // newline was present, so we can reproduce it faithfully.
    const hasTrailingNewline = /\r?\n$/.test(originalText);
    const normalized = originalText.replace(/\r\n/g, '\n');
    const rawLines = normalized.split('\n');
    if (hasTrailingNewline && rawLines.length > 0 && rawLines[rawLines.length - 1] === '') {
        rawLines.pop();
    }

    const formattedLines: string[] = [];
    let depth = 0;
    let inBlockComment = false;
    let consecutiveBlank = 0;

    for (const rawLineOriginal of rawLines) {
        const scan = scanLine(rawLineOriginal, inBlockComment);
        const rawLine = normalizeHashComment(rawLineOriginal, scan.hashCommentAt);
        const stripped = rawLine.replace(/[\t ]+$/g, '').trim();

        if (scan.isBlank) {
            if (collapseBlankLines) {
                consecutiveBlank += 1;
                if (consecutiveBlank <= 1) {
                    formattedLines.push('');
                }
            } else {
                formattedLines.push('');
            }
            inBlockComment = scan.inBlockComment;
            continue;
        }

        consecutiveBlank = 0;

        const effectiveDepth = Math.max(0, depth - scan.indentBefore);
        const indentation = inBlockComment
            // Preserve the user's original leading whitespace for lines
            // that are entirely inside a block comment so we do not move
            // ``*`` continuation markers around.
            ? rawLine.slice(0, rawLine.length - rawLine.replace(/^[\t ]+/, '').length)
            : ' '.repeat(effectiveDepth * indentSize);

        formattedLines.push(indentation + stripped);
        depth = effectiveDepth + scan.indentAfter;
        inBlockComment = scan.inBlockComment;
    }

    let formatted = formattedLines.join(lineEnding);
    if (hasTrailingNewline) {
        formatted += lineEnding;
    }

    if (formatted === originalText) {
        return [];
    }

    const fullRange = computeFullRange(originalText);
    return [{range: fullRange, newText: formatted}];
}

function computeFullRange(text: string): TextRange {
    if (!text) {
        return createRange(0, 0, 0, 0);
    }
    const normalized = text.replace(/\r\n/g, '\n');
    const lines = normalized.split('\n');
    const lastLineIndex = lines.length - 1;
    const lastLineLength = lines[lastLineIndex].length;
    return createRange(0, 0, lastLineIndex, lastLineLength);
}

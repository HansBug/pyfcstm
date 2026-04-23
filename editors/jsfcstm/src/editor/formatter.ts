/**
 * FCSTM document formatter.
 *
 * The formatter tokenizes the source with a private lexer that preserves
 * every comment style (``//``, ``#``, and ``/* *\/``) as its own token, then
 * re-emits the stream with canonical spacing, 4-space indentation per brace
 * level, and multi-line layout for every non-empty brace block. Declaration
 * order is never changed because the token walk is strictly sequential and
 * the formatter only edits whitespace / delimiters.
 *
 * Key rules the output satisfies:
 *
 * 1. ``#`` line comments are normalized into the canonical ``//`` form so the
 *    file stays in one comment dialect. ``/* *\/`` is NEVER touched because
 *    FCSTM uses it as the ``raw_doc`` payload for ``abstract`` actions.
 * 2. Every brace block that contains statements is multi-line:
 *    ``effect{a=0;b=1;}`` becomes
 *    ``effect {\n    a = 0;\n    b = 1;\n}``. Empty ``{}`` stays inline.
 * 3. Binary operators get one space on each side (``a=b`` → ``a = b``); unary
 *    ``+``/``-`` attached to an operand do not gain a space (``-3`` stays
 *    ``-3``).
 * 4. Statement-terminating ``;`` sticks to the token on its left; ``,`` has
 *    no space before and one space after; ``(`` / ``[`` have no space after
 *    and ``)`` / ``]`` / ``;`` have no space before.
 * 5. Trailing line comments glued to code (``foo;// bar``) get a single
 *    space gap before the marker and one after it, yielding
 *    ``foo; // bar``. Standalone ``//`` / ``#`` lines keep their column
 *    and original padding.
 * 6. Runs of blank lines collapse to one.
 */
import type {TextDocumentLike, TextRange} from '../utils/text';
import {createRange} from '../utils/text';

export interface FcstmFormatOptions {
    /** Number of spaces per indent level. Defaults to 4. */
    indentSize?: number;
    /** Collapse 3+ blank lines into one blank line. Defaults to true. */
    collapseBlankLines?: boolean;
}

export interface FcstmTextEdit {
    range: TextRange;
    newText: string;
}

type TokKind =
    | 'ws'           // horizontal whitespace only (no newlines)
    | 'nl'           // a single newline (LF or CRLF)
    | 'blkCom'       // ``/* ... *\/`` — semantic raw_doc payload
    | 'lineCom'      // ``//`` or ``#`` line comment
    | 'str'          // string literal
    | 'num'          // numeric literal (int / hex / bin / float / sci)
    | 'ident'        // identifier or keyword
    | 'pseudoInit'   // ``[*]``
    | 'punct';       // anything else: single- or multi-char operator / delimiter

interface Tok {
    kind: TokKind;
    text: string;
    marker?: '//' | '#';
    body?: string;
}

const MULTI_CHAR_OPS = [
    '**', '<<', '>>', '<=', '>=', '==', '!=', '&&', '||', '->', '::',
];

const BINARY_OPS = new Set([
    '=', '==', '!=', '<', '>', '<=', '>=',
    '+', '-', '*', '/', '%', '**',
    '&', '|', '^', '<<', '>>',
    '&&', '||',
    '->', '::',
    '?',
]);

/** Builtin unary-function names from the FCSTM lexer's UFUNC_NAME rule. */
const UFUNC_NAMES = new Set([
    'sin', 'cos', 'tan', 'asin', 'acos', 'atan',
    'sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh',
    'sqrt', 'cbrt', 'exp', 'log', 'log10', 'log2', 'log1p',
    'abs', 'ceil', 'floor', 'round', 'trunc', 'sign',
]);

/** Whether a token looks like an operand (left side of a binary op). */
function isOperandLike(tok: Tok | null): boolean {
    if (!tok) return false;
    if (tok.kind === 'num' || tok.kind === 'ident' || tok.kind === 'str'
        || tok.kind === 'pseudoInit') {
        return true;
    }
    if (tok.kind === 'punct') {
        return tok.text === ')' || tok.text === ']';
    }
    return false;
}

/**
 * Is this ``/`` acting as the leading marker of a chain-id path such as
 * ``/GlobalEvent`` or ``ref /CleanupHook`` rather than as a division
 * operator? A path prefix is recognized when the token immediately before
 * the ``/`` is a scope introducer (``:``) or the ``ref`` keyword.
 */
function isChainIdPrefixSlash(tokens: Tok[], idx: number): boolean {
    if (idx < 1) return false;
    const slash = tokens[idx];
    if (slash.kind !== 'punct' || slash.text !== '/') return false;
    const prev = tokens[idx - 1];
    if (prev.kind === 'punct' && prev.text === ':') return true;
    if (prev.kind === 'ident' && prev.text === 'ref') return true;
    return false;
}

function tokenize(src: string): Tok[] {
    const tokens: Tok[] = [];
    const n = src.length;
    let i = 0;

    while (i < n) {
        const c = src[i];
        const d = i + 1 < n ? src[i + 1] : '';

        // Newlines
        if (c === '\n') {
            tokens.push({kind: 'nl', text: '\n'});
            i += 1;
            continue;
        }
        if (c === '\r') {
            if (d === '\n') {
                tokens.push({kind: 'nl', text: '\r\n'});
                i += 2;
            } else {
                tokens.push({kind: 'nl', text: '\r'});
                i += 1;
            }
            continue;
        }
        // Horizontal whitespace
        if (c === ' ' || c === '\t') {
            let j = i + 1;
            while (j < n && (src[j] === ' ' || src[j] === '\t')) j += 1;
            tokens.push({kind: 'ws', text: src.slice(i, j)});
            i = j;
            continue;
        }
        // Block comment
        if (c === '/' && d === '*') {
            const end = src.indexOf('*/', i + 2);
            const j = end < 0 ? n : end + 2;
            tokens.push({kind: 'blkCom', text: src.slice(i, j)});
            i = j;
            continue;
        }
        // ``//`` line comment
        if (c === '/' && d === '/') {
            const nlPos = findNewline(src, i);
            const text = src.slice(i, nlPos);
            tokens.push({kind: 'lineCom', text, marker: '//', body: text.slice(2)});
            i = nlPos;
            continue;
        }
        // ``#`` line comment
        if (c === '#') {
            const nlPos = findNewline(src, i);
            const text = src.slice(i, nlPos);
            tokens.push({kind: 'lineCom', text, marker: '#', body: text.slice(1)});
            i = nlPos;
            continue;
        }
        // String literals
        if (c === '"' || c === '\'') {
            const quote = c;
            let j = i + 1;
            while (j < n && src[j] !== quote) {
                if (src[j] === '\\' && j + 1 < n) {
                    j += 2;
                } else if (src[j] === '\n' || src[j] === '\r') {
                    break;
                } else {
                    j += 1;
                }
            }
            if (j < n && src[j] === quote) j += 1;
            tokens.push({kind: 'str', text: src.slice(i, j)});
            i = j;
            continue;
        }
        // Pseudo-init marker ``[*]``
        if (c === '[' && src[i + 1] === '*' && src[i + 2] === ']') {
            tokens.push({kind: 'pseudoInit', text: '[*]'});
            i += 3;
            continue;
        }
        // Numbers (hex, binary, decimal, optional fractional + exponent)
        if (c >= '0' && c <= '9') {
            let j = i;
            if (c === '0' && (src[i + 1] === 'x' || src[i + 1] === 'X')) {
                j = i + 2;
                while (j < n && /[0-9a-fA-F]/.test(src[j])) j += 1;
            } else if (c === '0' && (src[i + 1] === 'b' || src[i + 1] === 'B')) {
                j = i + 2;
                while (j < n && (src[j] === '0' || src[j] === '1')) j += 1;
            } else {
                while (j < n && src[j] >= '0' && src[j] <= '9') j += 1;
                if (src[j] === '.') {
                    j += 1;
                    while (j < n && src[j] >= '0' && src[j] <= '9') j += 1;
                }
                if (src[j] === 'e' || src[j] === 'E') {
                    j += 1;
                    if (src[j] === '+' || src[j] === '-') j += 1;
                    while (j < n && src[j] >= '0' && src[j] <= '9') j += 1;
                }
            }
            tokens.push({kind: 'num', text: src.slice(i, j)});
            i = j;
            continue;
        }
        // Identifier
        if (/[a-zA-Z_]/.test(c)) {
            let j = i + 1;
            while (j < n && /[a-zA-Z0-9_]/.test(src[j])) j += 1;
            tokens.push({kind: 'ident', text: src.slice(i, j)});
            i = j;
            continue;
        }
        // Multi-char operators first
        const twoChar = c + d;
        if (MULTI_CHAR_OPS.includes(twoChar)) {
            tokens.push({kind: 'punct', text: twoChar});
            i += 2;
            continue;
        }
        // Single-char punctuation
        tokens.push({kind: 'punct', text: c});
        i += 1;
    }

    return tokens;
}

function findNewline(src: string, start: number): number {
    let j = start;
    while (j < src.length && src[j] !== '\n' && src[j] !== '\r') j += 1;
    return j;
}

/**
 * Normalize a line-comment token into its canonical rendered form. ``#``
 * becomes ``//``, and a single space is inserted after the marker when the
 * body has content but no leading whitespace. Existing padding is NEVER
 * collapsed so banner-style comments survive verbatim.
 */
function renderLineComment(tok: Tok): string {
    const body = tok.body || '';
    const needsSpace = body.length > 0 && body[0] !== ' ' && body[0] !== '\t';
    return `//${needsSpace ? ' ' : ''}${body}`.replace(/[ \t]+$/, '');
}

/**
 * Decide whether two successive real (code) tokens want a space between
 * them. ``tokens`` is the full logical-line buffer and ``currentIdx`` is
 * the position of ``next`` inside that buffer, so the rule for unary
 * ``+``/``-`` can look two steps back.
 */
function separatorBetween(
    prev: Tok,
    next: Tok,
    tokens: Tok[],
    currentIdx: number
): string {
    const pt = prev.text;
    const nt = next.text;
    const beforePrev = currentIdx >= 2 ? tokens[currentIdx - 2] : null;

    // Chain-id prefix: a ``/`` that leads a path (``/Event`` after ``:``,
    // or ``/path`` after ``ref``) keeps its leading space — ``ref /path``
    // stays readable — but hugs the identifier that follows, so the result
    // reads ``ref /path`` rather than ``ref / path``.
    if (prev.kind === 'punct' && pt === '/' && isChainIdPrefixSlash(tokens, currentIdx - 1)) {
        return '';
    }

    // Tokens that always hug on the left.
    if (next.kind === 'punct' && (nt === ';' || nt === ',' || nt === ')' || nt === ']' || nt === '.' || nt === '}')) {
        return '';
    }
    // Tokens that always hug on the right.
    if (prev.kind === 'punct' && (pt === '(' || pt === '[' || pt === '.')) {
        return '';
    }
    // Unary ``+``/``-``: tight against the operand when the token BEFORE the
    // operator is itself a non-operand (start of statement, another operator,
    // ``(``, ``[``, ``,``, ``;``, ``=``, etc.).
    if (prev.kind === 'punct' && (pt === '+' || pt === '-')
        && !isOperandLike(beforePrev)) {
        return '';
    }
    // Unary ``!`` / ``not``: always tight to its operand.
    if (prev.kind === 'punct' && pt === '!') {
        return '';
    }
    if (prev.kind === 'ident' && prev.text === 'not') {
        return ' ';
    }
    // Function call: no space between a UFUNC name and its ``(``.
    if (prev.kind === 'ident' && UFUNC_NAMES.has(prev.text)
        && next.kind === 'punct' && nt === '(') {
        return '';
    }
    // Dotted paths: no space on either side of ``.``.
    if (next.kind === 'punct' && nt === '.') return '';
    // ``{`` after any real content (keyword / ident / ``)``) gets one space.
    if (next.kind === 'punct' && nt === '{') return ' ';
    // Binary operators between tokens: one space on each side.
    if (prev.kind === 'punct' && BINARY_OPS.has(pt)) return ' ';
    if (next.kind === 'punct' && BINARY_OPS.has(nt)) return ' ';
    // ``,`` / ``;`` / ``:`` produce a space after themselves; hug-left is
    // already handled above.
    if (prev.kind === 'punct' && (pt === ',' || pt === ';' || pt === ':')) return ' ';
    if (next.kind === 'punct' && nt === ':') return ' ';
    // Ident / number / string / pseudo followed by same → space.
    return ' ';
}

/**
 * Walk logical lines. A logical line ends at ``{`` (after the brace),
 * ``}`` (the brace forms its own line), or ``;`` (after the semicolon).
 * Line comments keep their association with the line they trail.
 */
interface LogicalChunk {
    kind: 'line' | 'blankMarker';
    depth: number;
    tokens: Tok[];         // real tokens for this line (no ws / nl)
    trailing?: Tok;        // trailing line-comment attached to the line
    leadingBlockComments?: Tok[];  // standalone blkCom tokens emitted before the line
}

function groupLogicalLines(tokens: Tok[]): LogicalChunk[] {
    const chunks: LogicalChunk[] = [];
    let depth = 0;
    let currentLineDepth = 0;
    let buffer: Tok[] = [];
    let pendingDepthBump = 0;   // applied after next commit
    let blankRun = 0;
    // ``true`` when the most recently pushed chunk was a standalone line
    // comment (or another pre-committed chunk) whose source-line terminator
    // newline has not been consumed yet. Prevents that terminator from
    // being mis-counted as a blank-line marker.
    let expectLineTerminator = false;
    let pendingLeadingBlkComs: Tok[] = [];

    const lineHasContent = () => buffer.length > 0 || pendingLeadingBlkComs.length > 0;

    const commit = (trailing?: Tok) => {
        if (buffer.length === 0 && !trailing && pendingLeadingBlkComs.length === 0) {
            // Still apply a pending depth bump even when nothing was committed
            // (defensive; normal flow always has at least the ``{`` in buffer).
            depth += pendingDepthBump;
            pendingDepthBump = 0;
            currentLineDepth = depth;
            return;
        }
        chunks.push({
            kind: 'line',
            depth: currentLineDepth,
            tokens: buffer,
            trailing,
            leadingBlockComments: pendingLeadingBlkComs.length > 0 ? pendingLeadingBlkComs : undefined,
        });
        buffer = [];
        pendingLeadingBlkComs = [];
        depth += pendingDepthBump;
        pendingDepthBump = 0;
        currentLineDepth = depth;
    };

    const endsWithPunct = (text: string): boolean => {
        if (buffer.length === 0) return false;
        const last = buffer[buffer.length - 1];
        return last.kind === 'punct' && last.text === text;
    };

    const emitBlankMarker = () => {
        if (chunks.length === 0) return;
        const last = chunks[chunks.length - 1];
        if (last.kind === 'blankMarker') return;
        chunks.push({kind: 'blankMarker', depth: 0, tokens: []});
    };

    for (let i = 0; i < tokens.length; i++) {
        const t = tokens[i];

        if (t.kind === 'ws') continue;

        if (t.kind === 'nl') {
            if (lineHasContent()) {
                commit();
                blankRun = 0;
                expectLineTerminator = false;
            } else if (expectLineTerminator) {
                // This newline is the source-line terminator for the chunk
                // we just pushed without consuming a newline. Consume it.
                expectLineTerminator = false;
                blankRun = 0;
            } else {
                blankRun += 1;
                // Any source newline beyond the one that terminated the
                // previous line counts as a blank-line candidate.
                if (blankRun >= 1) emitBlankMarker();
            }
            continue;
        }

        if (t.kind === 'lineCom') {
            if (lineHasContent()) {
                commit(t);
                blankRun = 0;
                expectLineTerminator = true;
            } else {
                if (blankRun >= 1) emitBlankMarker();
                chunks.push({
                    kind: 'line',
                    depth,
                    tokens: [],
                    trailing: t,
                    leadingBlockComments: pendingLeadingBlkComs.length > 0 ? pendingLeadingBlkComs : undefined,
                });
                pendingLeadingBlkComs = [];
                blankRun = 0;
                expectLineTerminator = true;
            }
            continue;
        }

        if (t.kind === 'blkCom') {
            if (buffer.length > 0) {
                buffer.push(t);
            } else {
                pendingLeadingBlkComs.push(t);
            }
            blankRun = 0;
            continue;
        }

        // Real code token. If the current buffer ended with a line-terminating
        // punctuation (``{``, ``}``, or ``;``), that logical line is complete.
        // Commit it before starting the next one so each statement / brace
        // lives on its own line.
        if (endsWithPunct('{') || endsWithPunct('}') || endsWithPunct(';')) {
            commit();
        }

        blankRun = 0;

        if (t.kind === 'punct') {
            if (t.text === '{') {
                buffer.push(t);
                pendingDepthBump = 1;
                continue;
            }
            if (t.text === '}') {
                if (buffer.length > 0) commit();
                depth = Math.max(0, depth - 1);
                currentLineDepth = depth;
                buffer.push(t);
                continue;
            }
            if (t.text === ';') {
                buffer.push(t);
                continue;
            }
        }

        buffer.push(t);
    }

    if (lineHasContent()) {
        commit();
    }
    return mergeInlinePatterns(chunks);
}

/**
 * Post-pass that keeps a few idiomatic inline patterns compact:
 *
 * - ``{}`` — empty brace blocks stay on a single line.
 * - ``} else {`` — the else clause joins the closing brace so the output
 *   uses conventional K&R-style ``if {} else {}`` layout.
 */
function mergeInlinePatterns(chunks: LogicalChunk[]): LogicalChunk[] {
    const merged: LogicalChunk[] = [];
    for (const chunk of chunks) {
        const prev = merged[merged.length - 1];

        // Empty block merge: previous line ends with ``{`` and this line is
        // just ``}`` at the same depth. If the closing ``}`` carries a
        // trailing comment, carry it over so ``during after { }// note``
        // becomes ``during after {} // note``.
        if (
            prev
            && prev.kind === 'line'
            && chunk.kind === 'line'
            && chunk.tokens.length === 1
            && chunk.tokens[0].kind === 'punct'
            && chunk.tokens[0].text === '}'
            && (!chunk.leadingBlockComments || chunk.leadingBlockComments.length === 0)
            && prev.tokens.length > 0
            && prev.tokens[prev.tokens.length - 1].kind === 'punct'
            && prev.tokens[prev.tokens.length - 1].text === '{'
            && !prev.trailing
        ) {
            prev.tokens.push(chunk.tokens[0]);
            if (chunk.trailing) prev.trailing = chunk.trailing;
            continue;
        }

        // Orphan semicolon merge: if the previous line ended with ``}`` and
        // the next line is just ``;``, the ``;`` is a no-op state statement
        // that wandered away from its block. Glue it back onto the ``}``
        // line so the output reads ``};`` rather than splitting ``;`` onto
        // its own visual line.
        if (
            prev
            && prev.kind === 'line'
            && chunk.kind === 'line'
            && chunk.tokens.length === 1
            && chunk.tokens[0].kind === 'punct'
            && chunk.tokens[0].text === ';'
            && !chunk.trailing
            && (!chunk.leadingBlockComments || chunk.leadingBlockComments.length === 0)
            && prev.tokens.length > 0
            && prev.tokens[prev.tokens.length - 1].kind === 'punct'
            && prev.tokens[prev.tokens.length - 1].text === '}'
        ) {
            prev.tokens.push(chunk.tokens[0]);
            continue;
        }

        // ``} else {`` merge: three chunks in a row where the middle is
        // ``else`` (possibly followed by ``if [cond] {``).
        if (
            prev
            && prev.kind === 'line'
            && chunk.kind === 'line'
            && chunk.tokens.length > 0
            && chunk.tokens[0].kind === 'ident'
            && chunk.tokens[0].text === 'else'
            && !prev.trailing
            && prev.tokens.length > 0
            && prev.tokens[prev.tokens.length - 1].kind === 'punct'
            && prev.tokens[prev.tokens.length - 1].text === '}'
            && (!prev.leadingBlockComments || prev.leadingBlockComments.length === 0)
        ) {
            for (const t of chunk.tokens) prev.tokens.push(t);
            if (chunk.trailing) prev.trailing = chunk.trailing;
            continue;
        }

        merged.push(chunk);
    }
    return merged;
}

function renderLine(chunk: LogicalChunk, indentSize: number): string {
    const indent = ' '.repeat(chunk.depth * indentSize);
    const leading = (chunk.leadingBlockComments || [])
        .map(t => indent + t.text.replace(/[ \t]+$/, ''))
        .join('\n');

    if (chunk.tokens.length === 0) {
        const comment = chunk.trailing ? indent + renderLineComment(chunk.trailing) : '';
        if (leading.length > 0 && comment.length > 0) return leading + '\n' + comment;
        return leading + comment;
    }

    let body = '';
    for (let i = 0; i < chunk.tokens.length; i++) {
        const tok = chunk.tokens[i];
        if (i === 0) {
            body += tok.text;
            continue;
        }
        const prev = chunk.tokens[i - 1];
        if (tok.kind === 'blkCom') {
            body += ' ' + tok.text;
            continue;
        }
        if (prev.kind === 'blkCom') {
            body += ' ' + tok.text;
            continue;
        }
        body += separatorBetween(prev, tok, chunk.tokens, i) + tok.text;
    }

    const trailing = chunk.trailing ? ' ' + renderLineComment(chunk.trailing) : '';
    const line = (indent + body + trailing).replace(/[ \t]+$/, '');
    if (leading.length > 0) {
        return leading + '\n' + line;
    }
    return line;
}

function detectLineEnding(text: string): string {
    const first = text.indexOf('\n');
    if (first < 0) return '\n';
    if (first > 0 && text[first - 1] === '\r') return '\r\n';
    return '\n';
}

function computeFullRange(text: string): TextRange {
    if (!text) return createRange(0, 0, 0, 0);
    const normalized = text.replace(/\r\n/g, '\n');
    const lines = normalized.split('\n');
    const lastLineIndex = lines.length - 1;
    const lastLineLength = lines[lastLineIndex].length;
    return createRange(0, 0, lastLineIndex, lastLineLength);
}

/**
 * Format a whole FCSTM document. Returns a single whole-document edit, or an
 * empty array when the source is already well-formed.
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

    const tokens = tokenize(originalText);
    const chunks = groupLogicalLines(tokens);

    const outputLines: string[] = [];
    let lastEmittedKind: 'line' | 'blank' | null = null;

    const lastToken = (c: LogicalChunk): Tok | null => (
        c.tokens.length > 0 ? c.tokens[c.tokens.length - 1] : null
    );
    const firstToken = (c: LogicalChunk): Tok | null => (
        c.tokens.length > 0 ? c.tokens[0] : null
    );

    for (let ci = 0; ci < chunks.length; ci++) {
        const chunk = chunks[ci];
        if (chunk.kind === 'blankMarker') {
            // Peek neighbors. A blank line adjacent to a ``{`` (the block
            // has just opened) or to a ``}`` (the block is about to close)
            // is visual noise more often than it is intentional spacing,
            // so the formatter drops those. Blank lines between two
            // ``ident`` / statement lines stay.
            let prevLineChunk: LogicalChunk | null = null;
            for (let j = ci - 1; j >= 0; j--) {
                if (chunks[j].kind === 'line') {
                    prevLineChunk = chunks[j];
                    break;
                }
            }
            let nextLineChunk: LogicalChunk | null = null;
            for (let j = ci + 1; j < chunks.length; j++) {
                if (chunks[j].kind === 'line') {
                    nextLineChunk = chunks[j];
                    break;
                }
            }
            const prevLast = prevLineChunk ? lastToken(prevLineChunk) : null;
            const nextFirst = nextLineChunk ? firstToken(nextLineChunk) : null;
            const adjacentOpenBrace = prevLast
                && prevLast.kind === 'punct'
                && prevLast.text === '{';
            const adjacentCloseBrace = nextFirst
                && nextFirst.kind === 'punct'
                && nextFirst.text === '}';

            if (adjacentOpenBrace || adjacentCloseBrace) continue;
            if (!collapseBlankLines || lastEmittedKind === 'line') {
                outputLines.push('');
                lastEmittedKind = 'blank';
            }
            continue;
        }
        const rendered = renderLine(chunk, indentSize);
        if (rendered.length === 0) continue;
        for (const physicalLine of rendered.split('\n')) {
            outputLines.push(physicalLine);
        }
        lastEmittedKind = 'line';
    }

    // Trim trailing blank lines — keep exactly one final newline.
    while (outputLines.length > 0 && outputLines[outputLines.length - 1] === '') {
        outputLines.pop();
    }

    let formatted = outputLines.join('\n');
    const hadTrailingNewline = /\r?\n$/.test(originalText);
    if (hadTrailingNewline && formatted.length > 0) {
        formatted += '\n';
    }
    if (lineEnding === '\r\n') {
        formatted = formatted.replace(/\n/g, '\r\n');
    }

    if (formatted === originalText) return [];
    return [{range: computeFullRange(originalText), newText: formatted}];
}

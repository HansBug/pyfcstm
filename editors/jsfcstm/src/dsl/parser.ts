const antlr4 = require('antlr4') as {
    InputStream: new (input: string) => unknown;
    CommonTokenStream: new (lexer: unknown) => unknown;
};

// Documented expected throw classes from antlr4 runtime when parse() or
// nextToken() blows up on malformed input:
//   * RecognitionException (antlr4's own error base) and its subclasses
//     LexerNoViableAltException, NoViableAltException,
//     InputMismatchException, FailedPredicateException,
//     ParseCancellationException.
//   * RangeError / TypeError raised by antlr4 internals when decision-DFA
//     state lookups touch undefined entries (this happens on malformed
//     input where the lexer fails before the parser context is ready).
//
// All of those subclass ``Error``. The only thing we still re-raise are
// non-Error throws (raw strings, numbers) which can only happen if a
// caller misuses the parser API and indicates a programmer bug.
function isExpectedAntlrError(err: unknown): boolean {
    return err instanceof Error;
}

// eslint-disable-next-line @typescript-eslint/no-var-requires
const GrammarLexer = require('./grammar/GrammarLexer').default;
// eslint-disable-next-line @typescript-eslint/no-var-requires
const GrammarParser = require('./grammar/GrammarParser').default;

type GeneratedLexerClass = new (input: unknown) => {
    removeErrorListeners(): void;
    addErrorListener(listener: unknown): void;
    nextToken(): { text?: string; line?: number; column?: number; type?: number };
};

type GeneratedParserClass = new (tokens: unknown) => {
    removeErrorListeners(): void;
    addErrorListener(listener: unknown): void;
    buildParseTrees: boolean;
    state_machine_dsl(): unknown;
};

interface GeneratedParserModules {
    GrammarLexer: GeneratedLexerClass;
    GrammarParser: GeneratedParserClass;
}

export interface ParseError {
    line: number;
    column: number;
    message: string;
    severity: 'error' | 'warning';
}

export interface ParseResult {
    success: boolean;
    errors: ParseError[];
}

export interface LexToken {
    text: string;
    line: number;
    column: number;
}

function formatTokenText(tokenText: string | undefined): string {
    if (!tokenText || tokenText === '<EOF>') {
        return 'end of file';
    }

    return JSON.stringify(tokenText);
}

const CONDITION_CARET_MESSAGE = 'Invalid condition operator "^": "^" is numeric bitwise xor; use "xor" for boolean exclusive-or in guard conditions.';
const CONDITION_ARROW_MESSAGE = 'Invalid condition operator "->": use "=>" or "implies" for boolean implication; "->" is only for transitions.';

function guardBodyOnLine(lineText: string | undefined, column: number | undefined): string | null {
    if (!lineText) {
        return null;
    }

    const end = column == null
        ? lineText.length
        : Math.max(0, Math.min(lineText.length, column + 1));
    const prefix = lineText.slice(0, end);
    const pattern = /\bif\s*\[/g;
    let match: RegExpExecArray | null;
    let start: number | null = null;

    while ((match = pattern.exec(prefix)) !== null) {
        start = match.index + match[0].length;
    }

    if (start == null) {
        return null;
    }

    const rest = lineText.slice(start);
    const close = rest.indexOf(']');
    return close === -1 ? rest : rest.slice(0, close);
}

function stripOuterParens(text: string): string {
    let value = text.trim();
    while (value.startsWith('(') && value.endsWith(')')) {
        value = value.slice(1, -1).trim();
    }
    return value;
}

function isSimpleBoolLikeAtom(text: string): boolean {
    const value = stripOuterParens(text)
        .replace(/^(?:!|not\b)\s*/i, '')
        .trim();
    return /^(?:true|false|[a-zA-Z_][a-zA-Z0-9_]*)$/i.test(value);
}

function containsConditionOperator(text: string): boolean {
    return /(?:==|!=|<=|>=|<|>|&&|\|\||=>|\band\b|\bor\b|\bimplies\b|\bxor\b|\biff\b)/i.test(text);
}

function hasConditionLevelCaret(guardBody: string): boolean {
    for (let index = guardBody.indexOf('^'); index !== -1; index = guardBody.indexOf('^', index + 1)) {
        const left = guardBody.slice(0, index);
        const right = guardBody.slice(index + 1);
        if (
            (containsConditionOperator(left) && containsConditionOperator(right))
            || (isSimpleBoolLikeAtom(left) && isSimpleBoolLikeAtom(right))
        ) {
            return true;
        }
    }
    return false;
}

function isConditionCaretError(
    message: string,
    tokenText: string | undefined,
    lineText: string | undefined,
    column: number | undefined
): boolean {
    if (tokenText === '^') {
        return true;
    }

    const guardBody = guardBodyOnLine(lineText, column);
    return !!(
        guardBody
        && hasConditionLevelCaret(guardBody)
        && /expecting '\]'|missing '\]'|mismatched input|no viable alternative at input/i.test(message)
    );
}

function normalizeSyntaxMessage(
    message: string,
    tokenText?: string,
    lineText?: string,
    column?: number
): string {
    if (
        tokenText === '[*]'
        && /no viable alternative at input 'state[^']*\[\*\]'/i.test(message)
    ) {
        return 'Missing semicolon before "[*]".';
    }

    if (/missing ';'|expecting ';'|missing SEMI|expecting SEMI/i.test(message)) {
        if (tokenText === 'def') {
            return 'Missing semicolon after variable definition';
        } else if (tokenText === 'state') {
            return 'Missing semicolon after previous statement';
        } else if (tokenText === '}') {
            return 'Missing semicolon after operation statement';
        } else if (tokenText && /^[a-zA-Z_][a-zA-Z0-9_]*$/.test(tokenText)) {
            return 'Missing semicolon after previous statement';
        }
        return `Missing semicolon before ${formatTokenText(tokenText)}.`;
    }

    if (/missing '\]'|expecting '\]'|missing RBRACK|expecting RBRACK/i.test(message)) {
        if (isConditionCaretError(message, tokenText, lineText, column)) {
            return CONDITION_CARET_MESSAGE;
        }
        if (tokenText === '->') {
            return CONDITION_ARROW_MESSAGE;
        }
        return 'Missing closing bracket in guard condition.';
    }

    if (/missing '\}'|expecting '\}'|missing RBRACE|expecting RBRACE/i.test(message)) {
        if (tokenText === '<EOF>') {
            return 'Missing closing brace - check for unclosed state definitions or action blocks';
        }
        return 'Missing closing brace before end of file.';
    }

    if (/missing '\{'|expecting '\{'|missing LBRACE|expecting LBRACE/i.test(message)) {
        return 'Missing opening brace for block';
    }

    if (/missing '\['|expecting '\['|missing LBRACK|expecting LBRACK/i.test(message)) {
        return 'Missing opening bracket for guard condition';
    }

    if (/missing '->'|expecting '->'|missing ARROW|expecting ARROW/i.test(message)) {
        return 'Missing transition arrow \'->\'';
    }

    if (/missing '='|expecting '='|missing ASSIGN|expecting ASSIGN/i.test(message)) {
        return 'Missing equals sign in assignment or definition';
    }

    if (/extraneous input/i.test(message)) {
        if (tokenText === '<EOF>') {
            return 'Unexpected end of file - missing closing brace';
        } else if (tokenText === '}') {
            return 'Extra closing brace - check for mismatched braces';
        } else if (tokenText === 'during') {
            return 'Unexpected \'during\' keyword - missing closing brace before this line';
        }
        return `Unexpected token ${formatTokenText(tokenText)}.`;
    }

    if (/mismatched input/i.test(message)) {
        if (
            /expecting \{';', 'named'\}/i.test(message)
            || /expecting \{(?:NAMED|SEMI), (?:NAMED|SEMI)\}/i.test(message)
        ) {
            return 'Missing semicolon after event definition';
        }
        return `Unexpected token ${formatTokenText(tokenText)}.`;
    }

    if (/no viable alternative at input/i.test(message)) {
        if (isConditionCaretError(message, tokenText, lineText, column)) {
            return CONDITION_CARET_MESSAGE;
        }

        if (tokenText) {
            const tokenLower = tokenText.toLowerCase();
            const stateMatches = tokenLower.match(/state/g);

            if (stateMatches && stateMatches.length >= 2) {
                return 'Missing semicolon between state definitions';
            }

            if (tokenLower.includes('state') && /enter|exit|during/.test(tokenLower)) {
                return 'Missing opening brace or semicolon before lifecycle action';
            }

            if (tokenLower.includes('state') && tokenText.length > 10) {
                return 'Missing semicolon after state definition';
            }

            if (tokenText.includes('=>')) {
                return 'Invalid operator - use \'->\' for transitions, not \'=>\'';
            }

            if (/abstract|ref/.test(tokenLower) && tokenText.includes('}')) {
                return 'Missing semicolon after abstract function or reference definition';
            }
        }
        return 'Invalid syntax - check for missing semicolons, braces, or operators';
    }

    if (/token recognition error/i.test(message)) {
        if (tokenText && tokenText.includes('"')) {
            return 'Unclosed string literal - add closing quote';
        }
        return `Unexpected token ${formatTokenText(tokenText)}.`;
    }

    return `Invalid syntax: ${message}`;
}

class CollectingErrorListener {
    private readonly errors: ParseError[];
    private readonly lines: string[];

    constructor(errors: ParseError[], sourceText = '') {
        this.errors = errors;
        this.lines = sourceText.split(/\r\n|\r|\n/);
    }

    syntaxError(
        _recognizer: unknown,
        offendingSymbol: { line?: number; column?: number; text?: string } | null,
        line: number,
        column: number,
        msg: string,
        _e: unknown
    ): void {
        const tokenText = offendingSymbol?.text;
        const normalizedMessage = normalizeSyntaxMessage(
            msg,
            tokenText,
            this.lines[line - 1],
            column
        );

        this.errors.push({
            line: line - 1,
            column,
            message: normalizedMessage,
            severity: 'error',
        });
    }

    reportAmbiguity(): void {
        this.errors.push({
            line: 0,
            column: 0,
            message: 'Ambiguous syntax - add parentheses to make condition precedence explicit.',
            severity: 'error',
        });
    }

    reportAttemptingFullContext(): void {
        // ANTLR emits this during normal adaptive prediction for some valid
        // condition expressions; it is not a syntax error.
    }

    reportContextSensitivity(): void {
        // Same diagnostic channel as full-context prediction, not a hard parse
        // failure for editor/parser consumers.
    }
}

export class FcstmParser {
    private readonly modules: GeneratedParserModules;

    constructor() {
        this.modules = {
            GrammarLexer: GrammarLexer as GeneratedLexerClass,
            GrammarParser: GrammarParser as GeneratedParserClass,
        };
    }

    isAvailable(): boolean {
        return this.modules !== null;
    }

    async parse(text: string): Promise<ParseResult> {
        if (!this.modules) {
            return {
                success: false,
                errors: [{
                    line: 0,
                    column: 0,
                    message: 'Parser runtime is not available.',
                    severity: 'error',
                }],
            };
        }

        try {
            const errors: ParseError[] = [];
            const errorListener = new CollectingErrorListener(errors, text);
            const input = new antlr4.InputStream(text);
            const lexer = new this.modules.GrammarLexer(input);
            lexer.removeErrorListeners();
            lexer.addErrorListener(errorListener);

            const tokens = new antlr4.CommonTokenStream(lexer);
            const parser = new this.modules.GrammarParser(tokens);
            parser.buildParseTrees = false;
            parser.removeErrorListeners();
            parser.addErrorListener(errorListener);

            parser.state_machine_dsl();

            return {
                success: errors.length === 0,
                errors,
            };
        } catch (error) {
            if (!isExpectedAntlrError(error)) {
                throw error;
            }
            return {
                success: false,
                errors: [{
                    line: 0,
                    column: 0,
                    message: `Parser error: ${error}`,
                    severity: 'error',
                }],
            };
        }
    }

    async parseTree(text: string): Promise<unknown | null> {
        if (!this.modules) {
            return null;
        }

        try {
            const errors: ParseError[] = [];
            const errorListener = new CollectingErrorListener(errors, text);
            const input = new antlr4.InputStream(text);
            const lexer = new this.modules.GrammarLexer(input);
            lexer.removeErrorListeners();
            lexer.addErrorListener(errorListener);

            const tokens = new antlr4.CommonTokenStream(lexer);
            const parser = new this.modules.GrammarParser(tokens);
            parser.buildParseTrees = true;
            parser.removeErrorListeners();
            parser.addErrorListener(errorListener);

            return parser.state_machine_dsl();
        } catch (error) {
            if (!isExpectedAntlrError(error)) {
                throw error;
            }
            return null;
        }
    }

    async lex(text: string): Promise<LexToken[]> {
        if (!this.modules) {
            return [];
        }

        try {
            const input = new antlr4.InputStream(text);
            const lexer = new this.modules.GrammarLexer(input);
            const tokens: LexToken[] = [];

            while (true) {
                const token = lexer.nextToken();
                if (!token || token.type === -1) {
                    break;
                }

                tokens.push({
                    text: token.text || '',
                    line: (token.line || 1) - 1,
                    column: token.column || 0,
                });
            }

            return tokens;
        } catch (error) {
            if (!isExpectedAntlrError(error)) {
                throw error;
            }
            return [];
        }
    }
}

let parserInstance: FcstmParser | null = null;

export function getParser(): FcstmParser {
    if (!parserInstance) {
        parserInstance = new FcstmParser();
    }
    return parserInstance;
}

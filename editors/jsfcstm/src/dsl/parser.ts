const antlr4 = require('antlr4') as {
    InputStream: new (input: string) => unknown;
    CommonTokenStream: new (lexer: unknown) => unknown;
};

// eslint-disable-next-line @typescript-eslint/no-var-requires
const GrammarLexer = require('./grammar/GrammarLexer').default;
// eslint-disable-next-line @typescript-eslint/no-var-requires
const GrammarParser = require('./grammar/GrammarParser').default;

type GeneratedLexerClass = new (input: unknown) => {
    removeErrorListeners(): void;
    addErrorListener(listener: unknown): void;
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

function formatTokenText(tokenText: string | undefined): string {
    if (!tokenText || tokenText === '<EOF>') {
        return 'end of file';
    }

    return JSON.stringify(tokenText);
}

function normalizeSyntaxMessage(message: string, tokenText?: string): string {
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
        if (/expecting ';'|expecting SEMI/i.test(message)) {
            if (tokenText === 'state') {
                return 'Missing semicolon after previous state definition';
            } else if (tokenText === '}') {
                return 'Missing semicolon before closing brace';
            }
            return 'Missing semicolon on previous line';
        } else if (/expecting '='|expecting ASSIGN/i.test(message)) {
            return 'Missing equals sign in variable definition';
        } else if (
            /expecting \{';', 'named'\}/i.test(message)
            || /expecting \{(?:NAMED|SEMI), (?:NAMED|SEMI)\}/i.test(message)
        ) {
            return 'Missing semicolon after event definition';
        }
        return `Unexpected token ${formatTokenText(tokenText)}.`;
    }

    if (/no viable alternative at input/i.test(message)) {
        if (tokenText) {
            const tokenLower = tokenText.toLowerCase();

            if (tokenLower.includes('state') && (tokenLower.match(/state/g) || []).length >= 2) {
                return 'Missing semicolon between state definitions';
            }

            if (tokenLower.includes('state') && /enter|exit|during/.test(tokenLower)) {
                return 'Missing opening brace or semicolon before lifecycle action';
            }

            if (tokenLower.includes('state') && tokenText.length > 10) {
                return 'Missing semicolon after state definition';
            }

            if (tokenText.includes('=')) {
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

    constructor(errors: ParseError[]) {
        this.errors = errors;
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
        const normalizedMessage = normalizeSyntaxMessage(msg, tokenText);

        this.errors.push({
            line: line - 1,
            column,
            message: normalizedMessage,
            severity: 'error',
        });
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
            const errorListener = new CollectingErrorListener(errors);
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
            const errorListener = new CollectingErrorListener(errors);
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
        } catch {
            return null;
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

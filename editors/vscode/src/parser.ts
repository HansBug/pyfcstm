/**
 * FCSTM Parser Adapter for VSCode Extension
 *
 * This module provides pure JavaScript parsing capabilities for FCSTM documents
 * in the VSCode extension by using ANTLR-generated lexer/parser artifacts.
 */

const antlr4 = require('antlr4') as {
    InputStream: new (input: string) => unknown;
    CommonTokenStream: new (lexer: unknown) => unknown;
};

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

type DefaultExportModule<T> = {
    default: T;
};

/**
 * Represents a parse error with location information
 */
export interface ParseError {
    line: number;
    column: number;
    message: string;
    severity: 'error' | 'warning';
}

/**
 * Result of parsing an FCSTM document
 */
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
    // Special case: state followed by [*] without semicolon
    if (
        tokenText === '[*]'
        && /no viable alternative at input 'state[^']*\[\*\]'/i.test(message)
    ) {
        return 'Missing semicolon before "[*]".';
    }

    // Missing semicolon patterns
    if (/missing ';'|expecting ';'/i.test(message)) {
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

    // Missing closing bracket
    if (/missing '\]'|expecting '\]'/i.test(message)) {
        return 'Missing closing bracket in guard condition.';
    }

    // Missing closing brace
    if (/missing '\}'|expecting '\}'/i.test(message)) {
        if (tokenText === '<EOF>') {
            return 'Missing closing brace - check for unclosed state definitions or action blocks';
        }
        return 'Missing closing brace before end of file.';
    }

    // Missing opening brace
    if (/missing '\{'|expecting '\{'/i.test(message)) {
        return 'Missing opening brace for block';
    }

    // Missing opening bracket
    if (/missing '\['|expecting '\['/i.test(message)) {
        return 'Missing opening bracket for guard condition';
    }

    // Missing transition arrow
    if (/missing '->'|expecting '->'/i.test(message)) {
        return 'Missing transition arrow \'->\'';
    }

    // Missing equals sign
    if (/missing '='|expecting '='/i.test(message)) {
        return 'Missing equals sign in assignment or definition';
    }

    // Extraneous input patterns
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

    // Mismatched input patterns
    if (/mismatched input/i.test(message)) {
        if (/expecting ';'/i.test(message)) {
            if (tokenText === 'state') {
                return 'Missing semicolon after previous state definition';
            } else if (tokenText === '}') {
                return 'Missing semicolon before closing brace';
            }
            return 'Missing semicolon on previous line';
        } else if (/expecting '='/i.test(message)) {
            return 'Missing equals sign in variable definition';
        } else if (/expecting \{';', 'named'\}/i.test(message)) {
            return 'Missing semicolon after event definition';
        }
        return `Unexpected token ${formatTokenText(tokenText)}.`;
    }

    // No viable alternative patterns
    if (/no viable alternative at input/i.test(message)) {
        if (tokenText) {
            const tokenLower = tokenText.toLowerCase();

            // Pattern: stateXXXstate (missing semicolon between states)
            if (tokenLower.includes('state') && (tokenLower.match(/state/g) || []).length >= 2) {
                return 'Missing semicolon between state definitions';
            }

            // Pattern: stateXXXenter/exit/during (missing brace or semicolon)
            if (tokenLower.includes('state') && /enter|exit|during/.test(tokenLower)) {
                return 'Missing opening brace or semicolon before lifecycle action';
            }

            // Pattern: stateXXXID (missing semicolon after state)
            if (tokenLower.includes('state') && tokenText.length > 10) {
                return 'Missing semicolon after state definition';
            }

            // Pattern: Active= (wrong arrow operator)
            if (tokenText.includes('=')) {
                return 'Invalid operator - use \'->\' for transitions, not \'=>\'';
            }

            // Pattern: enterabstractXXX} (missing semicolon after abstract)
            if (/abstract|ref/.test(tokenLower) && tokenText.includes('}')) {
                return 'Missing semicolon after abstract function or reference definition';
            }
        }
        return 'Invalid syntax - check for missing semicolons, braces, or operators';
    }

    // Token recognition error
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
        message: string,
        _error: unknown
    ): void {
        const tokenText = offendingSymbol?.text;
        this.errors.push({
            line: Math.max((line || offendingSymbol?.line || 1) - 1, 0),
            column: column ?? offendingSymbol?.column ?? 0,
            message: normalizeSyntaxMessage(message, tokenText),
            severity: 'error'
        });
    }
}

/**
 * Parser adapter for FCSTM documents
 */
export class FcstmParser {
    private modules: GeneratedParserModules | null = null;
    private readonly readyPromise: Promise<void>;

    constructor() {
        this.readyPromise = this.loadGeneratedModules();
    }

    private async loadGeneratedModules(): Promise<void> {
        try {
            const nativeImport = new Function('specifier', 'return import(specifier);') as (
                specifier: string
            ) => Promise<DefaultExportModule<GeneratedLexerClass> | DefaultExportModule<GeneratedParserClass>>;
            const [lexerModule, parserModule] = await Promise.all([
                nativeImport('../parser/GrammarLexer.js') as Promise<DefaultExportModule<GeneratedLexerClass>>,
                nativeImport('../parser/GrammarParser.js') as Promise<DefaultExportModule<GeneratedParserClass>>
            ]);

            this.modules = {
                GrammarLexer: lexerModule.default,
                GrammarParser: parserModule.default
            };
        } catch {
            this.modules = null;
        }
    }

    /**
     * Parse FCSTM document text
     *
     * @param text The FCSTM document text to parse
     * @returns Parse result with success status and any errors
     */
    async parse(text: string): Promise<ParseResult> {
        await this.readyPromise;

        if (!this.modules) {
            return {
                success: false,
                errors: [{
                    line: 0,
                    column: 0,
                    message: 'Parser runtime is not available.',
                    severity: 'error'
                }]
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
                errors
            };
        } catch (error) {
            return {
                success: false,
                errors: [{
                    line: 0,
                    column: 0,
                    message: `Parser error: ${error}`,
                    severity: 'error'
                }]
            };
        }
    }

    /**
     * Check if the parser is available
     */
    isAvailable(): boolean {
        return this.modules !== null;
    }
}

/**
 * Singleton parser instance
 */
let parserInstance: FcstmParser | null = null;

/**
 * Get the parser instance
 */
export function getParser(): FcstmParser {
    if (!parserInstance) {
        parserInstance = new FcstmParser();
    }
    return parserInstance;
}

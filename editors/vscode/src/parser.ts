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
    if (
        tokenText === '[*]'
        && /no viable alternative at input 'state[^']*\[\*\]'/i.test(message)
    ) {
        return 'Missing semicolon before "[*]".';
    }

    if (/missing ';'|expecting ';'/i.test(message)) {
        return `Missing semicolon before ${formatTokenText(tokenText)}.`;
    }

    if (/missing '\]'|expecting '\]'/i.test(message)) {
        return 'Missing closing bracket in guard condition.';
    }

    if (
        /missing '\}'|expecting '\}'/i.test(message)
        || (tokenText === '<EOF>' && /mismatched input|extraneous input|no viable alternative/i.test(message))
    ) {
        return 'Missing closing brace before end of file.';
    }

    if (/token recognition error/i.test(message)) {
        return `Unexpected token ${formatTokenText(tokenText)}.`;
    }

    if (/extraneous input|mismatched input|no viable alternative/i.test(message)) {
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

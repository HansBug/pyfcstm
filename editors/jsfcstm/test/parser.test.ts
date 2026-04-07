import assert from 'node:assert/strict';

import {packageModule, parserModule} from './support';

interface SyntheticSyntaxError {
    message: string;
    tokenText?: string;
    line?: number;
    column?: number;
}

function createParserWithSyntheticErrors(
    syntheticErrors: SyntheticSyntaxError[],
    options: {
        throwError?: Error;
        returnValue?: unknown;
    } = {}
): parserModule.FcstmParser & { modules: unknown } {
    let parserListener: {
        syntaxError(
            recognizer: unknown,
            offendingSymbol: { text?: string } | null,
            line: number,
            column: number,
            msg: string,
            e: unknown
        ): void;
    };

    class FakeLexer {
        removeErrorListeners(): void {
            // no-op
        }

        addErrorListener(): void {
            // no-op
        }
    }

    class FakeParser {
        buildParseTrees = false;

        removeErrorListeners(): void {
            // no-op
        }

        addErrorListener(listener: typeof parserListener): void {
            parserListener = listener;
        }

        state_machine_dsl(): unknown {
            for (const error of syntheticErrors) {
                parserListener.syntaxError(
                    null,
                    error.tokenText == null ? null : {text: error.tokenText},
                    error.line ?? 1,
                    error.column ?? 0,
                    error.message,
                    null
                );
            }

            if (options.throwError) {
                throw options.throwError;
            }

            return options.returnValue ?? {kind: 'synthetic-tree'};
        }
    }

    const parser = new parserModule.FcstmParser() as parserModule.FcstmParser & { modules: unknown };
    parser.modules = {
        GrammarLexer: FakeLexer,
        GrammarParser: FakeParser,
    };
    return parser;
}

describe('jsfcstm parser real grammar coverage', () => {
    const validCases = [
        'state Root;',
        'def int counter = 0;\nstate Root;',
        'def float temperature = 25.5;\nstate System { state Active; state Idle; [*] -> Active; Active -> Idle :: Pause; }',
        'state Root { pseudo state Junction; }',
        'state Root { event Start named "Start Event"; state Child; }',
        'state Root { enter { counter = 0; } during { counter = counter + 1; } exit { counter = 0; } }',
        'state Root { during before { counter = 0; } during after { counter = 1; } state Child; [*] -> Child; }',
        'state Root { >> during before { counter = counter + 1; } >> during after { counter = 0; } state Child; }',
        'state Root { ! Child -> Error :: Fault; state Child; state Error; }',
        'state Root { Child -> Parent : if [x > 0 && y < 10] effect { counter = counter + 1; } state Child; state Parent; }',
        'state Root { import "./worker.fcstm" as Worker named "Worker Module" { def sensor_* -> io_$1; event /Start -> /Bus.Start named "Bus Start"; } }',
        'state Root { event Start; state A; state B; A -> B : /Start; }',
    ];

    for (const inputText of validCases) {
        it(`parses valid DSL from the Python test corpus: ${inputText.split('\n')[0]}`, async () => {
            const result = await packageModule.getParser().parse(inputText);
            assert.equal(result.success, true);
            assert.deepEqual(result.errors, []);
        });
    }

    it('builds parse trees for valid DSL', async () => {
        const tree = await packageModule.getParser().parseTree(
            'def int counter = 0;\nstate Root { state Active; [*] -> Active; }'
        );
        assert.ok(tree);
    });

    const invalidCases = [
        {
            name: 'missing semicolon after variable definition',
            inputText: 'def int counter = 0\nstate Root;',
            expectedMessage: /semicolon/i,
        },
        {
            name: 'missing semicolon after state definition',
            inputText: 'state Root {\n    state Active\n    state Idle;\n}',
            expectedMessage: /semicolon/i,
        },
        {
            name: 'missing semicolon after operation statement',
            inputText: 'state Root { enter { counter = 0 } }',
            expectedMessage: /operation statement|semicolon/i,
        },
        {
            name: 'missing closing bracket in guard condition',
            inputText: 'state Root { state A; state B; A -> B : if [counter > 10; }',
            expectedMessage: /bracket/i,
        },
        {
            name: 'missing closing brace in state definition',
            inputText: 'state Root { state Active { enter { counter = 0; } state Idle; }',
            expectedMessage: /brace/i,
        },
        {
            name: 'invalid transition operator',
            inputText: 'state Root { state A; state B; A => B; }',
            expectedMessage: /operator|->/i,
        },
        {
            name: 'missing equals in variable definition',
            inputText: 'def int counter 0;\nstate Root;',
            expectedMessage: /equals/i,
        },
        {
            name: 'unclosed string literal',
            inputText: 'state Root { state Active named "Active State; state Idle; }',
            expectedMessage: /string|token/i,
        },
        {
            name: 'missing brackets in condition',
            inputText: 'state Root { state A; state B; A -> B : if counter > 10; }',
            expectedMessage: /bracket/i,
        },
        {
            name: 'missing semicolon after event definition',
            inputText: 'state Root { event MyEvent\nstate Active; }',
            expectedMessage: /semicolon/i,
        },
        {
            name: 'missing semicolon after abstract action',
            inputText: 'state Root { state Active { enter abstract InitHardware } }',
            expectedMessage: /semicolon/i,
        },
    ];

    for (const testCase of invalidCases) {
        it(`normalizes real parser errors for ${testCase.name}`, async () => {
            const result = await packageModule.getParser().parse(testCase.inputText);
            assert.equal(result.success, false);
            assert.ok(result.errors.length >= 1);
            assert.match(result.errors[0].message, testCase.expectedMessage);
        });
    }
});

describe('jsfcstm parser error normalization branches', () => {
    const cases: Array<{
        name: string;
        error: SyntheticSyntaxError;
        expected: string;
    }> = [
        {
            name: 'special [*] missing semicolon pattern',
            error: {
                message: "no viable alternative at input 'stateActive[*]'",
                tokenText: '[*]',
            },
            expected: 'Missing semicolon before "[*]".',
        },
        {
            name: 'missing semicolon after definition keyword',
            error: {message: "missing ';'", tokenText: 'def'},
            expected: 'Missing semicolon after variable definition',
        },
        {
            name: 'missing semicolon after previous statement before state',
            error: {message: "expecting ';'", tokenText: 'state'},
            expected: 'Missing semicolon after previous statement',
        },
        {
            name: 'missing semicolon after operation statement',
            error: {message: 'missing SEMI', tokenText: '}'},
            expected: 'Missing semicolon after operation statement',
        },
        {
            name: 'missing semicolon before generic token',
            error: {message: "expecting ';'", tokenText: ')'},
            expected: 'Missing semicolon before ")".',
        },
        {
            name: 'missing closing bracket',
            error: {message: "missing ']'", tokenText: ';'},
            expected: 'Missing closing bracket in guard condition.',
        },
        {
            name: 'missing closing brace at eof',
            error: {message: "missing '}'", tokenText: '<EOF>'},
            expected: 'Missing closing brace - check for unclosed state definitions or action blocks',
        },
        {
            name: 'missing closing brace before generic token',
            error: {message: "expecting '}'", tokenText: 'state'},
            expected: 'Missing closing brace before end of file.',
        },
        {
            name: 'missing opening brace',
            error: {message: "expecting '{'", tokenText: 'enter'},
            expected: 'Missing opening brace for block',
        },
        {
            name: 'missing opening bracket',
            error: {message: "missing '['", tokenText: 'counter'},
            expected: 'Missing opening bracket for guard condition',
        },
        {
            name: 'missing transition arrow',
            error: {message: "expecting '->'", tokenText: 'Idle'},
            expected: 'Missing transition arrow \'->\'',
        },
        {
            name: 'missing equals sign',
            error: {message: "missing '='", tokenText: '0'},
            expected: 'Missing equals sign in assignment or definition',
        },
        {
            name: 'extraneous eof input',
            error: {message: 'extraneous input', tokenText: '<EOF>'},
            expected: 'Unexpected end of file - missing closing brace',
        },
        {
            name: 'extraneous closing brace',
            error: {message: 'extraneous input', tokenText: '}'},
            expected: 'Extra closing brace - check for mismatched braces',
        },
        {
            name: 'extraneous during keyword',
            error: {message: 'extraneous input', tokenText: 'during'},
            expected: 'Unexpected \'during\' keyword - missing closing brace before this line',
        },
        {
            name: 'extraneous generic token',
            error: {message: 'extraneous input', tokenText: '@@'},
            expected: 'Unexpected token "@@".',
        },
        {
            name: 'mismatched missing semicolon after previous state',
            error: {message: "mismatched input 'state' expecting ';'", tokenText: 'state'},
            expected: 'Missing semicolon after previous statement',
        },
        {
            name: 'mismatched missing semicolon before closing brace',
            error: {message: "mismatched input '}' expecting ';'", tokenText: '}'},
            expected: 'Missing semicolon after operation statement',
        },
        {
            name: 'mismatched missing semicolon previous line fallback',
            error: {message: "mismatched input 'identifier' expecting ';'", tokenText: 'identifier'},
            expected: 'Missing semicolon after previous statement',
        },
        {
            name: 'mismatched equals in definition',
            error: {message: "mismatched input '0' expecting '='", tokenText: '0'},
            expected: 'Missing equals sign in assignment or definition',
        },
        {
            name: 'mismatched event definition terminator',
            error: {message: "mismatched input 'state' expecting {';', 'named'}", tokenText: 'state'},
            expected: 'Missing semicolon after event definition',
        },
        {
            name: 'mismatched generic token fallback',
            error: {message: "mismatched input 'foo' expecting BAR", tokenText: 'foo'},
            expected: 'Unexpected token "foo".',
        },
        {
            name: 'no viable alternative between states',
            error: {message: 'no viable alternative at input', tokenText: 'statestate'},
            expected: 'Missing semicolon between state definitions',
        },
        {
            name: 'no viable alternative before lifecycle action',
            error: {message: 'no viable alternative at input', tokenText: 'stateenter'},
            expected: 'Missing opening brace or semicolon before lifecycle action',
        },
        {
            name: 'no viable alternative after state definition',
            error: {message: 'no viable alternative at input', tokenText: 'stateVeryLongName'},
            expected: 'Missing semicolon after state definition',
        },
        {
            name: 'no viable alternative invalid operator',
            error: {message: 'no viable alternative at input', tokenText: 'A=>B'},
            expected: 'Invalid operator - use \'->\' for transitions, not \'=>\'',
        },
        {
            name: 'no viable alternative missing abstract terminator',
            error: {message: 'no viable alternative at input', tokenText: 'abstractInit}'},
            expected: 'Missing semicolon after abstract function or reference definition',
        },
        {
            name: 'no viable alternative generic fallback',
            error: {message: 'no viable alternative at input', tokenText: 'oops'},
            expected: 'Invalid syntax - check for missing semicolons, braces, or operators',
        },
        {
            name: 'token recognition error for string literal',
            error: {message: 'token recognition error', tokenText: '"unterminated'},
            expected: 'Unclosed string literal - add closing quote',
        },
        {
            name: 'token recognition generic fallback',
            error: {message: 'token recognition error', tokenText: '%'},
            expected: 'Unexpected token "%".',
        },
        {
            name: 'generic syntax fallback',
            error: {message: 'weird syntax', tokenText: 'foo'},
            expected: 'Invalid syntax: weird syntax',
        },
    ];

    for (const testCase of cases) {
        it(`maps ${testCase.name}`, async () => {
            const parser = createParserWithSyntheticErrors([testCase.error]);
            const result = await parser.parse('ignored');

            assert.equal(result.success, false);
            assert.equal(result.errors.length, 1);
            assert.equal(result.errors[0].message, testCase.expected);
            assert.equal(result.errors[0].line, (testCase.error.line ?? 1) - 1);
            assert.equal(result.errors[0].column, testCase.error.column ?? 0);
            assert.equal(result.errors[0].severity, 'error');
        });
    }

    it('reports unavailable parser runtime in parse()', async () => {
        const parser = new parserModule.FcstmParser() as parserModule.FcstmParser & { modules: unknown };
        parser.modules = null;

        assert.equal(parser.isAvailable(), false);

        const result = await parser.parse('state Root;');
        assert.equal(result.success, false);
        assert.deepEqual(result.errors, [{
            line: 0,
            column: 0,
            message: 'Parser runtime is not available.',
            severity: 'error',
        }]);
    });

    it('returns null parse trees when parser runtime is unavailable', async () => {
        const parser = new parserModule.FcstmParser() as parserModule.FcstmParser & { modules: unknown };
        parser.modules = null;

        const tree = await parser.parseTree('state Root;');
        assert.equal(tree, null);
    });

    it('reports parser exceptions from parse()', async () => {
        const parser = createParserWithSyntheticErrors([], {
            throwError: new Error('boom'),
        });

        const result = await parser.parse('state Root;');
        assert.equal(result.success, false);
        assert.match(result.errors[0].message, /Parser error: Error: boom/);
    });

    it('returns null from parseTree() when parser execution throws', async () => {
        const parser = createParserWithSyntheticErrors([], {
            throwError: new Error('boom'),
        });

        const tree = await parser.parseTree('state Root;');
        assert.equal(tree, null);
    });

    it('caches the shared parser singleton', () => {
        assert.equal(packageModule.getParser(), packageModule.getParser());
    });
});

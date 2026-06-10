import assert from 'node:assert/strict';

import {createDocument, editorModule, packageModule, sliceByRange} from './support';

const SEMANTIC_RECOVERY_CODES = new Set(['E_UNDEFINED_VAR', 'E_TYPE_MISMATCH']);
const DSL_IDENTIFIER_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

function rangeKey(range: {start: {line: number; character: number}; end: {line: number; character: number}}): string {
    return `${range.start.line}:${range.start.character}-${range.end.line}:${range.end.character}`;
}

describe('diagnostics parse recovery', () => {
    const cases = [
        {
            name: 'integer identifier used as a guard condition',
            text: [
                'def int x = 0;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    [*] -> A;',
                '    A -> B : if [x];',
                '}',
            ].join('\n'),
        },
        {
            name: 'missing variable name in a definition',
            text: [
                'def int = 0;',
                'state Root;',
            ].join('\n'),
        },
        {
            name: 'empty transition guard',
            text: [
                'state Root {',
                '    state A;',
                '    state B;',
                '    [*] -> A;',
                '    A -> B : if [];',
                '}',
            ].join('\n'),
        },
        {
            name: 'empty assignment RHS in an action block',
            text: [
                'def int x = 0;',
                'state Root {',
                '    state A { enter { y = ; } }',
                '    [*] -> A;',
                '}',
            ].join('\n'),
        },
    ];

    for (const testCase of cases) {
        it(`keeps parse diagnostics but suppresses empty semantic diagnostics for ${testCase.name}`, async () => {
            const document = createDocument(testCase.text, `/tmp/parse-recovery-${testCase.name}.fcstm`);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            const parseDiagnostics = diagnostics.filter(item => item.code === undefined);
            assert.ok(parseDiagnostics.length > 0, `expected parse diagnostic for ${testCase.name}: ${JSON.stringify(diagnostics)}`);

            const parseRanges = new Set(parseDiagnostics.map(item => rangeKey(item.range)));
            const semanticDiagnostics = diagnostics.filter(item => item.code !== undefined);
            const semanticRecoveryDiagnostics = semanticDiagnostics.filter(item => SEMANTIC_RECOVERY_CODES.has(String(item.code)));
            const invalidSemanticDiagnostics = semanticRecoveryDiagnostics.filter(item => (
                packageModule.rangeIsEmptyOrInvalid(item.range)
                || sliceByRange(testCase.text, item.range).length === 0
                || item.data?.var_name === ''
                || item.data?.expr_text === ''
                || parseRanges.has(rangeKey(item.range))
            ));

            assert.deepEqual(
                invalidSemanticDiagnostics.map(item => ({
                    code: item.code,
                    message: item.message,
                    range: item.range,
                    slice: sliceByRange(testCase.text, item.range),
                    data: item.data,
                })),
                [],
            );

            const zeroWidthSemanticDiagnostics = semanticDiagnostics.filter(item => packageModule.rangeIsEmptyOrInvalid(item.range));
            assert.deepEqual(
                zeroWidthSemanticDiagnostics.map(item => ({
                    code: item.code,
                    message: item.message,
                    range: item.range,
                    slice: sliceByRange(testCase.text, item.range),
                    data: item.data,
                })),
                [],
            );

            const invalidVariableNameDiagnostics = diagnostics.filter(item => (
                typeof item.data?.var_name === 'string'
                && !DSL_IDENTIFIER_PATTERN.test(item.data.var_name)
            ));
            assert.deepEqual(
                invalidVariableNameDiagnostics.map(item => ({
                    code: item.code,
                    message: item.message,
                    range: item.range,
                    slice: sliceByRange(testCase.text, item.range),
                    data: item.data,
                })),
                [],
            );
        });
    }

    it('suppresses final recovery diagnostics with empty data or zero-width ranges', () => {
        const parseDiagnostic = {
            range: packageModule.createRange(0, 8, 0, 9),
            message: 'parse error',
            severity: 'error' as const,
            source: 'fcstm',
        };
        const parseDiagnostics = [parseDiagnostic];
        const makeDiagnostic = (
            code: string,
            data: Record<string, unknown>,
            range = packageModule.createRange(0, 4, 0, 5),
        ) => ({
            range,
            message: code,
            severity: 'error' as const,
            source: 'fcstm',
            code,
            data,
        });

        assert.equal(packageModule.shouldSuppressParseRecoveryDiagnostic(parseDiagnostic, parseDiagnostics), false);
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('E_UNDEFINED_VAR', {var_name: ''}),
                parseDiagnostics,
            ),
            true,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('E_UNDEFINED_VAR', {var_name: '1bad'}),
                parseDiagnostics,
            ),
            true,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('E_UNDEFINED_VAR', {var_name: 'valid_name'}),
                parseDiagnostics,
            ),
            false,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('E_TYPE_MISMATCH', {expr_text: ''}),
                parseDiagnostics,
            ),
            true,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('E_TYPE_MISMATCH', {expr_text: 'x'}),
                parseDiagnostics,
            ),
            false,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('W_UNREFERENCED_VAR', {var_name: 'not-a-name'}),
                parseDiagnostics,
            ),
            true,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('W_UNREFERENCED_VAR', {var_name: 'unused'}),
                parseDiagnostics,
            ),
            false,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('W_SOME_FUTURE_RECOVERY', {}, packageModule.createRange(1, 2, 1, 2)),
                parseDiagnostics,
            ),
            true,
        );
        assert.equal(
            packageModule.shouldSuppressParseRecoveryDiagnostic(
                makeDiagnostic('E_UNDEFINED_VAR', {var_name: ''}),
                [],
            ),
            false,
        );
    });

    it('shares the range emptiness predicate across analyzer and final-filter guards', () => {
        assert.equal(packageModule.rangeIsEmptyOrInvalid(packageModule.createRange(1, 2, 0, 9)), true);
        assert.equal(packageModule.rangeIsEmptyOrInvalid(packageModule.createRange(1, 2, 1, 2)), true);
        assert.equal(packageModule.rangeIsEmptyOrInvalid(packageModule.createRange(1, 2, 1, 3)), false);
    });

    it('does not emit type mismatches for recovered empty expressions', () => {
        const diagnostics: unknown[] = [];
        editorModule.checkExpression({
            expressionKind: 'identifier',
            name: '',
            range: packageModule.createRange(0, 0, 0, 0),
        }, 'boolean', diagnostics);
        editorModule.checkExpression({
            expressionKind: 'identifier',
            name: 'x',
            text: 'x',
            range: packageModule.createRange(0, 3, 0, 3),
        }, 'boolean', diagnostics);

        assert.deepEqual(diagnostics, []);
    });
});

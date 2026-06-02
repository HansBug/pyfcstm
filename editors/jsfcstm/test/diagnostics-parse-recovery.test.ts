import assert from 'node:assert/strict';

import {createDocument, packageModule, sliceByRange} from './support';

const SEMANTIC_RECOVERY_CODES = new Set(['E_UNDEFINED_VAR', 'E_TYPE_MISMATCH']);
const DSL_IDENTIFIER_PATTERN = /^[A-Za-z_][A-Za-z0-9_]*$/;

function rangeIsEmptyOrInvalid(range: {start: {line: number; character: number}; end: {line: number; character: number}}): boolean {
    if (range.end.line < range.start.line) return true;
    if (range.end.line === range.start.line && range.end.character <= range.start.character) return true;
    return false;
}

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
                rangeIsEmptyOrInvalid(item.range)
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

            const zeroWidthSemanticDiagnostics = semanticDiagnostics.filter(item => rangeIsEmptyOrInvalid(item.range));
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
});

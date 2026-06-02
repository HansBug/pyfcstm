import assert from 'node:assert/strict';

import {createDocument, packageModule, sliceByRange} from './support';

describe('inspect span/range contract', () => {
    it('converts pyfcstm Span coordinates to LSP Range', () => {
        assert.deepEqual(
            packageModule.spanToRange({line: 2, column: 5, end_line: 2, end_column: 8}),
            packageModule.createRange(1, 4, 1, 7),
        );
        assert.deepEqual(
            packageModule.spanToRange({line: 2, column: 5, end_line: 4, end_column: 3}),
            packageModule.createRange(1, 4, 3, 2),
        );
        assert.deepEqual(
            packageModule.spanToRange({
                start: {line: 1, character: 2},
                end: {line: 1, character: 6},
            }),
            packageModule.createRange(1, 2, 1, 6),
        );
        assert.equal(packageModule.spanToRange(null), null);
        assert.equal(packageModule.spanToRange({line: 0, column: 5, end_line: 0, end_column: 8}), null);
    });

    it('uses spanToRange for inspect-derived span refs and source slices', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B :: Go;',
            '    A -> B :: Go;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/inspect-span-to-range.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        assert.ok(semantic, 'expected semantic document');

        const forcedSpan = {line: 5, column: 5, end_line: 5, end_column: 20};
        const normalSpan = {line: 6, column: 5, end_line: 6, end_column: 19};
        const resolved = packageModule.resolveRangeFromRefsDetailed(document, semantic, {
            forced_declaration_span: forcedSpan,
            normal_transition_span: normalSpan,
        });

        assert.equal(sliceByRange(text, resolved.range!).trim(), '!A -> B :: Go;');
        assert.equal(sliceByRange(text, packageModule.spanToRange(normalSpan)!).trim(), 'A -> B :: Go;');
    });
});

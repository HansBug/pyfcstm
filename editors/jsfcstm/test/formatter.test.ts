import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

describe('jsfcstm formatter', () => {
    it('normalizes indentation by brace depth using spaces', () => {
        const source = [
            'def int counter = 0;',
            'state Root {',
            'state Inner {',
            '[*] -> Active;',
            'state Active;',
            '}',
            '}',
            '',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-indent.fcstm');

        const edits = packageModule.formatDocumentText(document);
        assert.equal(edits.length, 1);
        const expected = [
            'def int counter = 0;',
            'state Root {',
            '    state Inner {',
            '        [*] -> Active;',
            '        state Active;',
            '    }',
            '}',
            '',
        ].join('\n');
        assert.equal(edits[0].newText, expected);
    });

    it('honors the requested indent size', () => {
        const source = [
            'state Root {',
            'state Child;',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-size.fcstm');

        const edits = packageModule.formatDocumentText(document, {indentSize: 2});
        assert.equal(edits.length, 1);
        assert.equal(edits[0].newText, [
            'state Root {',
            '  state Child;',
            '}',
        ].join('\n'));
    });

    it('trims trailing whitespace and collapses consecutive blank lines', () => {
        const source = [
            'state Root {   ',
            '',
            '',
            '',
            '    state Child;',
            '    ',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-blanks.fcstm');

        const edits = packageModule.formatDocumentText(document);
        assert.equal(edits.length, 1);
        assert.equal(edits[0].newText, [
            'state Root {',
            '',
            '    state Child;',
            '',
            '}',
        ].join('\n'));
    });

    it('does not touch string literals, /* */ raw_doc payloads, or well-indented // lines', () => {
        const source = [
            '// top comment',
            '/* block comment */',
            'state Root {',
            '    // braces inside a line comment: { } should be ignored',
            '    event Fired named "value with { and } inside";',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-comments.fcstm');

        const edits = packageModule.formatDocumentText(document);
        assert.equal(edits.length, 0, 'already well-formed content should produce no edits');
    });

    it('normalizes Python-style "#" line comments into "//" form with a space gap', () => {
        const source = [
            '# top comment',
            '#note without space',
            'state Root {',
            '    # python-style comment inside Root',
            '    state Child; # trailing',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-hash-to-slash.fcstm');

        const edits = packageModule.formatDocumentText(document);
        assert.equal(edits.length, 1);
        const out = edits[0].newText;
        assert.ok(out.includes('// top comment'));
        assert.ok(out.includes('// note without space'),
            'bare "#note" should gain a space so it reads as "// note"');
        assert.ok(out.includes('// python-style comment inside Root'));
        assert.ok(out.includes('// trailing'));
        // No "#" line-comment markers should remain.
        assert.ok(!/(^|[^0-9a-zA-Z_])#(?!!)/.test(out),
            '"#" comment markers should have been replaced');
    });

    it('leaves "#" alone inside string literals and inside /* */ raw_doc blocks', () => {
        const source = [
            'state Root {',
            '    event Tagged named "value with # sharp inside";',
            '    enter abstract Setup /* note with # sharp inside */',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-hash-safe.fcstm');

        const edits = packageModule.formatDocumentText(document);
        // The document is already correctly indented; the "#" characters
        // inside string / raw_doc should not trigger any rewrite.
        assert.equal(edits.length, 0);
    });

    it('is idempotent under a second format pass', () => {
        const source = [
            'state Root {',
            'state Inner {',
            '    state Leaf;',
            '}',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-idem.fcstm');

        const first = packageModule.formatDocumentText(document)[0].newText;
        const second = packageModule.formatDocumentText(
            createDocument(first, '/tmp/fmt-idem-2.fcstm')
        );
        assert.equal(second.length, 0);
    });

    it('handles CRLF line endings without losing them', () => {
        const source = ['state Root {', '    state Child;', '}', ''].join('\r\n');
        const document = createDocument(source, '/tmp/fmt-crlf.fcstm');

        const edits = packageModule.formatDocumentText(document);
        if (edits.length === 0) {
            // Already well formed; acceptable.
            return;
        }
        assert.ok(edits[0].newText.includes('\r\n'));
        assert.ok(!edits[0].newText.includes('\n\r'));
    });

    it('returns no edits when the document is already formatted', () => {
        const source = [
            'def int counter = 0;',
            'state Root {',
            '    state Child;',
            '}',
            '',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-ok.fcstm');

        const edits = packageModule.formatDocumentText(document);
        assert.equal(edits.length, 0);
    });

    it('does not step on leading whitespace of lines inside an unterminated block comment', () => {
        const source = [
            'state Root {',
            '    /*',
            '     * Important notes here.',
            '     */',
            '    state Child;',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-block-comment.fcstm');

        const edits = packageModule.formatDocumentText(document);
        assert.equal(edits.length, 0);
    });

    it('preserves every comment and every trailing-comment line when re-indenting', () => {
        // Deliberately wrong indentation with line, shell, and trailing
        // comments mixed in. All three comment styles must survive and
        // end up with the correct leading indent for their depth.
        const source = [
            'state Root {',
            '// top of Root',
            '   # python-style inside Root',
            '   state Inner { // inline comment',
            '   state Leaf; /* block-style trailing */',
            '   } // closing Inner',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-comments-preserve.fcstm');

        const edits = packageModule.formatDocumentText(document);
        assert.equal(edits.length, 1);
        const out = edits[0].newText;
        // Every comment line or trailing comment must still be present.
        // "#" line comments get normalized into "//" form but the text survives.
        assert.ok(out.includes('// top of Root'));
        assert.ok(out.includes('// python-style inside Root'));
        assert.ok(out.includes('// inline comment'));
        assert.ok(out.includes('/* block-style trailing */'));
        assert.ok(out.includes('// closing Inner'));
        // Line-count must match exactly — no line was dropped or merged.
        assert.equal(out.split('\n').length, source.split('\n').length);
    });

    it('never reorders declarations of the same kind', () => {
        // Inputs that exercise the "action order must be preserved" rule:
        // multiple enters/during/exits/transitions inside one state, and
        // multiple state siblings at the same level.
        const source = [
            'state Root {',
            '    enter Init1 { counter = 1; }',
            '    enter Init2 { counter = 2; }',
            '    enter Init3 { counter = 3; }',
            '    during { counter = counter + 1; }',
            '    exit ExitA { counter = 0; }',
            '    exit ExitB { counter = 0; }',
            '    state First;',
            '    state Second;',
            '    state Third;',
            '    [*] -> First;',
            '    First -> Second;',
            '    Second -> Third;',
            '    Third -> [*];',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-order.fcstm');

        const edits = packageModule.formatDocumentText(document);
        const out = edits.length === 0 ? source : edits[0].newText;

        // Position of each marker must be strictly increasing: formatter must
        // not move anything past anything else of its kind.
        const markers = [
            'Init1', 'Init2', 'Init3',
            'ExitA', 'ExitB',
            'First', 'Second', 'Third',
        ];
        let lastIndex = -1;
        for (const marker of markers) {
            const at = out.indexOf(marker);
            assert.ok(at > lastIndex, `marker ${marker} moved out of order`);
            lastIndex = at;
        }
    });

    it('keeps intentional single blank lines between top-level blocks while folding long blank runs', () => {
        const source = [
            'def int counter = 0;',
            '',
            '',
            '',
            'state Root {',
            '    state A;',
            '',
            '',
            '',
            '    state B;',
            '}',
        ].join('\n');
        const document = createDocument(source, '/tmp/fmt-blanks-top.fcstm');

        const edits = packageModule.formatDocumentText(document);
        const out = edits.length === 0 ? source : edits[0].newText;

        // Long blank runs should collapse to exactly one.
        assert.ok(!/\n\n\n/.test(out), 'expected no runs of three or more newlines');
        // But a single intentional blank line must survive.
        assert.ok(/counter = 0;\n\nstate Root/.test(out));
    });
});

import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

/**
 * Fields that reference source location and therefore are expected to
 * differ between the pre-format and post-format ASTs. The equivalence
 * check compares only the structural shape of the tree, so these
 * location / text fields are stripped before comparing.
 */
const META_FIELDS = new Set([
    'range',
    'nameRange',
    'pathRange',
    'aliasRange',
    'text',
    'filePath',
]);

/**
 * Normalize a ``raw_doc`` string the way pyfcstm's
 * ``format_multiline_comment`` does: strip leading whitespace, optional
 * leading ``*`` marker, and any residual per-line indentation. Two
 * comments that differ only in ``*``-alignment compare equal under this
 * rule, which is exactly the invariant the formatter guarantees —
 * content is preserved, alignment may shift.
 */
function normalizeDocText(s: string): string {
    return s
        .split('\n')
        .map(line => line.replace(/^[\t ]*\*?[\t ]?/, '').replace(/[\t ]+$/g, ''))
        .join('\n')
        .trim();
}

function stripAstMetadata(value: unknown, parentKey?: string): unknown {
    if (Array.isArray(value)) {
        return value.map(item => stripAstMetadata(item));
    }
    if (value && typeof value === 'object') {
        const out: Record<string, unknown> = {};
        for (const [key, val] of Object.entries(value)) {
            if (META_FIELDS.has(key)) continue;
            out[key] = stripAstMetadata(val, key);
        }
        return out;
    }
    if (typeof value === 'string' && parentKey === 'doc') {
        return normalizeDocText(value);
    }
    return value;
}

async function astFor(source: string, filePath: string): Promise<unknown> {
    const doc = createDocument(source, filePath);
    const ast = await packageModule.parseAstDocument(doc);
    assert.ok(ast, `expected parseAstDocument to return an AST for ${filePath}`);
    return stripAstMetadata(ast);
}

async function assertFormatPreservesAst(source: string, label: string): Promise<string> {
    const before = await astFor(source, `/tmp/${label}-before.fcstm`);
    const doc = createDocument(source, `/tmp/${label}.fcstm`);
    const edits = packageModule.formatDocumentText(doc);
    const formatted = edits.length === 0 ? source : edits[0].newText;
    const after = await astFor(formatted, `/tmp/${label}-after.fcstm`);
    assert.deepEqual(
        after,
        before,
        `formatter produced a semantically different AST for case "${label}"`
    );
    return formatted;
}

describe('jsfcstm formatter AST equivalence', () => {
    it('preserves AST when the input is a small hand-rolled document', async () => {
        const source = [
            'def int  counter=0;',
            '   def float temperature =  25.5  ;',
            '',
            'state Root {',
            '    enter { counter = counter + 1; }',
            '    [*] -> Idle;',
            '    state Idle;',
            '}',
        ].join('\n');
        await assertFormatPreservesAst(source, 'small-doc');
    });

    it('preserves AST for a transition with guard and effect on one line', async () => {
        const source = [
            'def int counter = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B :if[counter >= 10]effect{counter=0;counter=counter+1;};',
            '}',
        ].join('\n');
        await assertFormatPreservesAst(source, 'transition');
    });

    it('preserves AST for nested if/else inside a during block', async () => {
        const source = [
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '    during {',
            '        if [x > 0] { x = 1; }',
            '        else if [x < 0] { x = -1; }',
            '        else { x = 0; }',
            '    }',
            '}',
        ].join('\n');
        await assertFormatPreservesAst(source, 'if-else');
    });

    it('preserves AST for abstract actions with /* */ raw_doc', async () => {
        const source = [
            'state Root {',
            '    enter abstract Setup /* single-line doc */',
            '    during abstract Step /* multi-line',
            '      * line two',
            '      * line three',
            '      */',
            '    state Leaf;',
            '    [*] -> Leaf;',
            '}',
        ].join('\n');
        await assertFormatPreservesAst(source, 'raw-doc');
    });

    it('preserves AST for forced transitions and event declarations', async () => {
        const source = [
            'state Root {',
            '    event Fatal named "Fatal error";',
            '    event Warn;',
            '    !* -> Error :: Fatal;',
            '    state Active;',
            '    state Error;',
            '    [*] -> Active;',
            '    Active -> Error :: Warn;',
            '}',
        ].join('\n');
        await assertFormatPreservesAst(source, 'forced');
    });

    it('preserves AST for aspect blocks and ref actions', async () => {
        const source = [
            'state Root {',
            '    >> during before {}',
            '    >> during after { }',
            '    state Child {',
            '        enter Boot { }',
            '        enter ref /Root.Boot;',
            '    }',
            '    [*] -> Child;',
            '}',
        ].join('\n');
        await assertFormatPreservesAst(source, 'aspect-ref');
    });

    it('is idempotent — format(format(x)) == format(x) on every messy case', async () => {
        const cases: Array<{label: string; source: string}> = [
            {
                label: 'def-norm',
                source: [
                    'def int  counter=0;',
                    'def float temperature =  25.5  ;',
                    'state Root { state Leaf; [*] -> Leaf; }',
                ].join('\n'),
            },
            {
                label: 'inline-block',
                source: [
                    'state Root {',
                    '    enter{counter=0;counter=counter+1;}',
                    '    state Child;',
                    '    [*] -> Child;',
                    '}',
                ].join('\n'),
            },
            {
                label: 'raw-doc-inline',
                source: [
                    'state Root {',
                    '    enter abstract Init /* one',
                    '      * two',
                    '      */',
                    '    state Child;',
                    '    [*] -> Child;',
                    '}',
                ].join('\n'),
            },
        ];
        for (const {label, source} of cases) {
            const first = await assertFormatPreservesAst(source, `idem-${label}-1`);
            await assertFormatPreservesAst(first, `idem-${label}-2`);
            const doc = createDocument(first, `/tmp/idem-${label}-recheck.fcstm`);
            const secondEdits = packageModule.formatDocumentText(doc);
            assert.equal(
                secondEdits.length, 0,
                `second format of case "${label}" should yield no further edits`
            );
        }
    });

    it('preserves AST when the full playground document is formatted', async () => {
        // A dense corpus exercising most constructs at once. Use a
        // compact but realistic sample so any regression in operator
        // handling or structural emission trips the AST check.
        const source = [
            'def int  counter=0;',
            '   def float temperature =  25.5  ;',
            '',
            '',
            'state System {',
            '    enter{counter=0;}',
            ' enter Init2 {temperature=25.0;}',
            '    enter abstract Bringup /* prepare hardware',
            '      * and wait for stable clocks',
            '      */',
            '',
            '    event Critical named "critical";',
            '    event Resume;',
            '',
            '    !* -> ErrorState :: Critical;',
            '    >> during before {counter=counter+1;}',
            '    >> during after  { counter=counter;}',
            '',
            '    [*] -> Initializing ;',
            '    state Initializing { enter{counter=0;} Initializing -> Running :if[counter >= 10]effect{counter=0;temperature=20.0;}; }',
            '    state Running {',
            '       state Active {',
            '         during { counter=counter+1; if[counter>100]{counter=0;}else{counter=counter;} }',
            '       }',
            '       state Idle;',
            '       [*] -> Active;',
            '       Active -> Idle :: Resume;',
            '       Idle -> Active :: Resume;',
            '    }',
            '    state ErrorState { enter{counter=counter+1;} }',
            '    Running -> ErrorState :if[temperature > 100.0];',
            '    ErrorState -> Running :if[counter > 0];',
            '    ErrorState -> [*];',
            '}',
        ].join('\n');
        await assertFormatPreservesAst(source, 'playground');
    });

    it('respects elseOnSameLine option while keeping the AST identical', async () => {
        const source = [
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '    during {',
            '        if [x > 0] { x = 1; } else { x = 0; }',
            '    }',
            '}',
        ].join('\n');
        const doc = createDocument(source, '/tmp/else-option.fcstm');
        const allmanEdits = packageModule.formatDocumentText(doc, {elseOnSameLine: false});
        const allmanText = allmanEdits.length === 0 ? source : allmanEdits[0].newText;
        assert.ok(
            /}\s*\n\s*else\s*\{/.test(allmanText),
            'expected Allman-style `}\\nelse {` when elseOnSameLine is false'
        );
        // AST must still match.
        const astBefore = await astFor(source, '/tmp/else-before.fcstm');
        const astAfter = await astFor(allmanText, '/tmp/else-allman.fcstm');
        assert.deepEqual(astAfter, astBefore);
    });

    it('respects indentSize option while keeping the AST identical', async () => {
        const source = [
            'state Root {',
            '    state Inner {',
            '        state Leaf;',
            '        [*] -> Leaf;',
            '    }',
            '    [*] -> Inner;',
            '}',
        ].join('\n');
        const doc = createDocument(source, '/tmp/indent-opt.fcstm');
        const twoSpaceEdits = packageModule.formatDocumentText(doc, {indentSize: 2});
        const twoSpaceText = twoSpaceEdits.length === 0 ? source : twoSpaceEdits[0].newText;
        assert.ok(
            /^  state Inner \{$/m.test(twoSpaceText),
            'expected 2-space indent for the first nested line'
        );
        const astBefore = await astFor(source, '/tmp/indent-before.fcstm');
        const astAfter = await astFor(twoSpaceText, '/tmp/indent-two.fcstm');
        assert.deepEqual(astAfter, astBefore);
    });
});

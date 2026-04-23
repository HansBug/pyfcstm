import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

function format(source: string, options?: Parameters<typeof packageModule.formatDocumentText>[1]): string {
    const doc = createDocument(source, '/tmp/fmt.fcstm');
    const edits = packageModule.formatDocumentText(doc, options);
    if (edits.length === 0) return source;
    return edits[0].newText;
}

describe('jsfcstm formatter', () => {
    it('normalizes spacing inside `def` statements', () => {
        const input = [
            'def int  counter=0;',
            '   def float temperature =  25.5  ;',
            'def int error_count=0;',
        ].join('\n');
        const expected = [
            'def int counter = 0;',
            'def float temperature = 25.5;',
            'def int error_count = 0;',
        ].join('\n');
        assert.equal(format(input), expected);
    });

    it('expands single-line brace blocks into multi-line form with four-space indent', () => {
        const input = [
            'state Root {',
            '    Initializing -> Running :if[counter >= 10]effect{counter=0;temperature=20.0;};',
            '}',
        ].join('\n');
        const expected = [
            'state Root {',
            '    Initializing -> Running : if [counter >= 10] effect {',
            '        counter = 0;',
            '        temperature = 20.0;',
            '    };',
            '}',
        ].join('\n');
        assert.equal(format(input), expected);
    });

    it('normalizes spacing around binary operators while leaving unary intact', () => {
        const input = [
            'state Root {',
            '    enter { counter=counter+1; temperature=-25.5+counter; }',
            '}',
        ].join('\n');
        const expected = [
            'state Root {',
            '    enter {',
            '        counter = counter + 1;',
            '        temperature = -25.5 + counter;',
            '    }',
            '}',
        ].join('\n');
        assert.equal(format(input), expected);
    });

    it('honors the requested indent size while still using spaces', () => {
        const input = [
            'state Root {',
            'state Child;',
            '}',
        ].join('\n');
        assert.equal(format(input, {indentSize: 2}), [
            'state Root {',
            '  state Child;',
            '}',
        ].join('\n'));
    });

    it('collapses runs of 3+ blank lines to one and drops blanks adjacent to braces', () => {
        const input = [
            'def int counter = 0;',
            '',
            '',
            '',
            'state Root {',
            '',
            '',
            '    state Child;',
            '',
            '}',
        ].join('\n');
        const expected = [
            'def int counter = 0;',
            '',
            'state Root {',
            '    state Child;',
            '}',
        ].join('\n');
        assert.equal(format(input), expected);
    });

    it('preserves all three comment styles: //, #, and /* */ (with # normalized to //)', () => {
        const input = [
            '// top line comment',
            '# python-style comment',
            '/* standalone block comment */',
            'state Root {',
            '    enter abstract Init /* raw_doc payload — stays verbatim */',
            '    state Child; // trailing line comment',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(out.includes('// top line comment'));
        assert.ok(out.includes('// python-style comment'),
            '"#" must be normalized to "//"');
        assert.ok(out.includes('/* standalone block comment */'));
        assert.ok(out.includes('/* raw_doc payload — stays verbatim */'),
            'raw_doc /* */ must be preserved verbatim');
        assert.ok(out.includes('// trailing line comment'));
    });

    it('never reorders declarations of the same kind', () => {
        const input = [
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
        const out = format(input);
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

    it('keeps empty brace blocks inline: `during after {}`', () => {
        const input = [
            'state Root {',
            '    during after { }',
            '    state Child;',
            '}',
        ].join('\n');
        const expected = [
            'state Root {',
            '    during after {}',
            '    state Child;',
            '}',
        ].join('\n');
        assert.equal(format(input), expected);
    });

    it('keeps `} else {` on one line (K&R style)', () => {
        const input = [
            'state Root {',
            '    during {',
            '        if [counter > 0] { counter = 1; }',
            '        else { counter = 0; }',
            '    }',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(/} else {/.test(out), 'expected `} else {` to merge onto one line');
    });

    it('chain-id prefix `/` hugs the identifier: `ref /Path`, `: /Event`', () => {
        const input = [
            'state Root {',
            '    state Child;',
            '    [*] -> Child;',
            '    Child -> Child :/GlobalEvent;',
            '    exit ref/cleanupHook;',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(/: \/GlobalEvent/.test(out),
            '`:` should keep its space but hug `/GlobalEvent`');
        assert.ok(/ref \/cleanupHook/.test(out),
            '`ref` should keep its space but hug `/cleanupHook`');
        assert.ok(!/ref \/ cleanupHook/.test(out),
            '`/` should not gain a trailing space');
    });

    it('UFUNC calls stay tight: `sin(x)`, `sqrt(y)`', () => {
        const input = [
            'def float a = 0.0;',
            'state Root {',
            '    enter { a = sin(a) + sqrt(a); }',
            '    state Child;',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(out.includes('sin(a) + sqrt(a)'));
        assert.ok(!out.includes('sin (a)'));
        assert.ok(!out.includes('sqrt (a)'));
    });

    it('`if [cond]` gets a space between `if` and `[`', () => {
        const input = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B :if[counter > 0];',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(/: if \[counter > 0\]/.test(out));
    });

    it('trailing line comments glued to code gain a space gap', () => {
        const input = [
            'state Root {',
            '    state Idle;// no gap',
            '    state Active;#glued hash',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(out.includes('state Idle; // no gap'));
        assert.ok(out.includes('state Active; // glued hash'));
    });

    it('bare `//note` gains a space after the marker', () => {
        const input = [
            'state Root {',
            '    //tight comment',
            '    state Child;',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(out.includes('// tight comment'));
        assert.ok(!out.includes('//tight'));
    });

    it('intentional multi-space padding inside comments is preserved', () => {
        const input = [
            '//    ============= Section banner =============',
            '//    === Intentional column alignment ===',
            'state Root;',
        ].join('\n');
        const out = format(input);
        assert.ok(out.includes('//    ============= Section banner ============='));
        assert.ok(out.includes('//    === Intentional column alignment ==='));
    });

    it('is idempotent under a second format pass', () => {
        const input = [
            'def int  x=1;',
            'state Root {',
            '    enter{x=x+1;}',
            '    state Child;',
            '}',
        ].join('\n');
        const first = format(input);
        const second = format(first);
        assert.equal(first, second, 'formatter must be idempotent');
    });

    it('handles CRLF line endings by preserving them', () => {
        const input = ['state Root {', '    state Child;', '}', ''].join('\r\n');
        const out = format(input);
        if (out === input) return;
        assert.ok(out.includes('\r\n'));
        assert.ok(!/[^\r]\n/.test(out),
            'all newlines must be CRLF when the input uses CRLF');
    });

    it('expands aspect blocks `>> during before { ... }` to multi-line', () => {
        const input = [
            'state Root {',
            '    >> during before {counter = counter + 1;}',
            '    state Child;',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(out.includes('>> during before {\n        counter = counter + 1;\n    }'));
    });

    it('preserves /* */ raw_doc for abstract actions without touching its content', () => {
        const input = [
            'state Root {',
            '    enter abstract Init /* Line one of the doc.',
            '    * Line two stays where it is.',
            '    * Line three ends. */',
            '    state Child;',
            '}',
        ].join('\n');
        const out = format(input);
        assert.ok(out.includes('/* Line one of the doc.'));
        assert.ok(out.includes('* Line two stays where it is.'));
        assert.ok(out.includes('* Line three ends. */'));
    });

    it('runs on a realistic messy document and yields a fully normalized result', () => {
        // This test is the canonical smoke test: if it breaks, the formatter
        // has drifted in behaviour and we need to either update the golden
        // output or the implementation.
        const messy = [
            'def int  counter=0;',
            '   def float temperature =  25.5  ;',
            '',
            '',
            '',
            '     state System {',
            '    enter {  counter = 0;error_count=0;}',
            ' enter Init2 { temperature = 25.0;}',
            '',
            '       event CriticalFailure named "critical failure";',
            '',
            '    [*] -> Initializing ;',
            'state Initializing {',
            'enter {  counter = 0 ;}',
            '   Initializing -> Running :if[counter >= 10]effect{counter=0;temperature=20.0;};',
            '}',
            '}',
        ].join('\n');
        const expected = [
            'def int counter = 0;',
            'def float temperature = 25.5;',
            '',
            'state System {',
            '    enter {',
            '        counter = 0;',
            '        error_count = 0;',
            '    }',
            '    enter Init2 {',
            '        temperature = 25.0;',
            '    }',
            '',
            '    event CriticalFailure named "critical failure";',
            '',
            '    [*] -> Initializing;',
            '    state Initializing {',
            '        enter {',
            '            counter = 0;',
            '        }',
            '        Initializing -> Running : if [counter >= 10] effect {',
            '            counter = 0;',
            '            temperature = 20.0;',
            '        };',
            '    }',
            '}',
        ].join('\n');
        assert.equal(format(messy), expected);
    });
});

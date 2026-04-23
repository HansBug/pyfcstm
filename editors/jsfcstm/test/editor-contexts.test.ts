/**
 * Editor-context completion tests from a FCSTM author's perspective.
 *
 * These tests complement `completion.test.ts` with positional coverage
 * for the scenarios a real user runs into while typing a `.fcstm` file:
 * transition targets, trigger scopes, guard and effect bodies, lifecycle
 * blocks, and visibility rules. They also pin down the currently known
 * editor-experience gaps via `it.skip` entries so the gaps stay visible
 * in one place.
 */
import assert from 'node:assert/strict';

import {
    createDocument,
    packageModule,
} from './support';

type CompletionItem = Awaited<ReturnType<typeof packageModule.collectCompletionItems>>[number];

function labels(items: CompletionItem[], kind?: CompletionItem['kind']): string[] {
    return items
        .filter(item => kind === undefined || item.kind === kind)
        .map(item => item.label);
}

function has(items: CompletionItem[], label: string, kind?: CompletionItem['kind']): boolean {
    return items.some(item => item.label === label && (kind === undefined || item.kind === kind));
}

function endOfLine(text: string, line: number): { line: number; character: number } {
    const lines = text.split('\n');
    return {line, character: (lines[line] || '').length};
}

describe('jsfcstm editor-context completion', () => {

    // -----------------------------------------------------------------
    // A. Transition target position
    // -----------------------------------------------------------------
    describe('transition target position', () => {
        it('offers sibling states and [*] after `A -> `', async () => {
            const text = [
                'state Root {',
                '    state Idle;',
                '    state Active;',
                '    state Running;',
                '    Idle -> ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/target-after-arrow.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'Active', 'class'),
                `expected sibling "Active" among: ${labels(items, 'class').join(', ')}`);
            assert.ok(has(items, 'Running', 'class'));
            assert.ok(has(items, '[*]', 'keyword'));
            // The state being transitioned from is itself visible (Idle).
            assert.ok(has(items, 'Idle', 'class'));
        });

        it('offers sibling states after `[*] -> `', async () => {
            const text = [
                'state Root {',
                '    state First;',
                '    state Second;',
                '    [*] -> ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/target-after-initial.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 3));

            assert.ok(has(items, 'First', 'class'));
            assert.ok(has(items, 'Second', 'class'));
        });

        it('does not offer the enclosing state name as a transition target', async () => {
            const text = [
                'state Root {',
                '    state Idle;',
                '    state Active;',
                '    Idle -> ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/target-no-self.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 3));

            assert.equal(has(items, 'Root'), false,
                'the enclosing composite state should not be a visible transition target');
        });

        it('filters transition targets to siblings of the source state', async () => {
            const text = [
                'state Root {',
                '    state Outer {',
                '        state A;',
                '        state B;',
                '        A -> ',
                '    }',
                '    state SiblingOfOuter;',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/target-scope.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'B', 'class'));
            assert.ok(has(items, 'A', 'class'));
            assert.equal(has(items, 'SiblingOfOuter'), false,
                'states in a different scope must not appear as targets');
        });
    });

    // -----------------------------------------------------------------
    // B. Transition trigger position
    // -----------------------------------------------------------------
    describe('transition trigger position', () => {
        it('offers local `::` events declared on the source state', async () => {
            const text = [
                'state Root {',
                '    state A {',
                '        event LocalE;',
                '    }',
                '    state B;',
                '    A -> B :: ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/trigger-local.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 5));

            assert.ok(has(items, 'LocalE', 'event'),
                `expected "LocalE" among: ${labels(items, 'event').join(', ')}`);
        });

        it('offers absolute `/` events declared at the root', async () => {
            const text = [
                'state Root {',
                '    event GlobalE;',
                '    state A;',
                '    state B;',
                '    A -> B : /',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/trigger-absolute.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, '/GlobalE', 'event'),
                `expected "/GlobalE" among: ${labels(items, 'event').join(', ')}`);
        });

        it('offers chain `:` events and `if` / `/` after `A -> B : `', async () => {
            const text = [
                'state Root {',
                '    event ParentE;',
                '    state A;',
                '    state B;',
                '    A -> B : ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/trigger-chain.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'ParentE', 'event'),
                `expected "ParentE" (chain event) but got: ${labels(items).join(', ')}`);
            assert.ok(has(items, 'if', 'keyword'),
                'after a bare `: ` the user may also start a guard with `if`');
            assert.ok(has(items, '/', 'keyword'),
                'after a bare `: ` the user may also start an absolute path with `/`');
            // `effect` is NOT grammatically valid directly after `:` — must
            // follow an event, guard, or live on the `A -> B effect` path.
            assert.equal(has(items, 'effect', 'keyword'), false,
                '`effect` is not a valid token directly after `:`');
        });
    });

    // -----------------------------------------------------------------
    // C. Guard body
    // -----------------------------------------------------------------
    describe('guard body', () => {
        it('offers variables, math primitives and logical operators inside `if [│]`', async () => {
            const text = [
                'def int counter = 0;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    A -> B : if [',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/guard-vars.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'counter', 'variable'),
                `expected "counter" but got: ${labels(items).join(', ')}`);
            assert.ok(has(items, 'pi', 'constant'));
            assert.ok(has(items, 'sin', 'function'));
            assert.ok(has(items, 'and', 'keyword'));
            assert.ok(has(items, 'not', 'keyword'));
            // Structural state-body keywords must NOT appear inside a guard.
            assert.equal(has(items, 'state', 'keyword'), false);
            assert.equal(has(items, 'enter', 'keyword'), false);
        });

        it('still offers variables inside `if [counter > │]` on the rhs of a comparison', async () => {
            const text = [
                'def int counter = 0;',
                'def int threshold = 5;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    A -> B : if [counter > ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/guard-rhs.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 5));

            assert.ok(has(items, 'threshold', 'variable'),
                `expected "threshold" on the rhs but got: ${labels(items).join(', ')}`);
            assert.ok(has(items, 'counter', 'variable'));
            assert.ok(has(items, 'pi', 'constant'));
        });
    });

    // -----------------------------------------------------------------
    // D. Effect block — should be solid
    // -----------------------------------------------------------------
    describe('effect block', () => {
        it('offers variables, functions and math constants inside `effect { │ }`', async () => {
            const text = [
                'def int x = 0;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    A -> B effect {',
                '        ',
                '    }',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/effect-body.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 5, character: 8});

            assert.ok(has(items, 'x', 'variable'));
            assert.ok(has(items, 'sin', 'function'));
            assert.ok(has(items, 'pi', 'constant'));
        });
    });

    // -----------------------------------------------------------------
    // E. Lifecycle blocks (enter / during / exit)
    // -----------------------------------------------------------------
    describe('lifecycle blocks', () => {
        const blocks: Array<'enter' | 'during' | 'exit'> = ['enter', 'during', 'exit'];

        for (const block of blocks) {
            it(`offers variables and math primitives inside \`${block} { │ }\``, async () => {
                const text = [
                    'def int n = 0;',
                    'state Root {',
                    `    ${block} {`,
                    '        ',
                    '    }',
                    '}',
                ].join('\n');
                const doc = createDocument(text, `/tmp/lifecycle-${block}.fcstm`);
                const items = await packageModule.collectCompletionItems(doc, {line: 3, character: 8});

                assert.ok(has(items, 'n', 'variable'),
                    `expected declared variable in ${block} body; got: ${labels(items).join(', ')}`);
                assert.ok(has(items, 'sqrt', 'function'));
                assert.ok(has(items, 'pi', 'constant'));
                assert.ok(has(items, 'if', 'keyword'),
                    `expected \`if\` keyword in ${block} body for control flow`);
            });
        }

        it('offers `else` after an `if [...] { } ` block inside `during`', async () => {
            const text = [
                'def int counter = 0;',
                'state Root {',
                '    during {',
                '        if [counter > 0] {',
                '            counter = 1;',
                '        } ',
                '    }',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/lifecycle-else.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 5, character: 10});

            assert.ok(has(items, 'else', 'keyword'));
        });
    });

    // -----------------------------------------------------------------
    // F. Top-level / state body skeleton
    // -----------------------------------------------------------------
    describe('document skeleton positions', () => {
        it('offers `state` / `def` / `import` at the top of an empty document', async () => {
            const doc = createDocument('', '/tmp/empty.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 0, character: 0});

            for (const expected of ['state', 'def', 'import', 'pseudo']) {
                assert.ok(has(items, expected, 'keyword'),
                    `expected keyword "${expected}" in empty document; got: ${labels(items, 'keyword').join(', ')}`);
            }
        });

        it('offers state-body keywords inside an empty `state Root { │ }`', async () => {
            const text = 'state Root {\n    \n}';
            const doc = createDocument(text, '/tmp/empty-state-body.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 4});

            // State-body starters: declarations + lifecycle stages + aspect
            // marker + pseudo-state marker + forced-transition marker.
            // `def` is deliberately excluded — variable declarations live at
            // the top level only.
            for (const expected of ['state', 'event', 'enter', 'during', 'exit', 'pseudo']) {
                assert.ok(has(items, expected, 'keyword'),
                    `expected state-body keyword "${expected}" but got keywords: ${labels(items, 'keyword').join(', ')}`);
            }
            assert.equal(has(items, 'def'), false,
                '`def` is a top-level-only declaration and must not appear inside a state body');
        });

        it('offers `before` / `after` after typing `>> during ` at the state body level', async () => {
            const text = 'state Root {\n    >> during \n}';
            const doc = createDocument(text, '/tmp/aspect-keyword.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 1));

            assert.ok(has(items, 'before', 'keyword'));
            assert.ok(has(items, 'after', 'keyword'));
        });
    });

    // -----------------------------------------------------------------
    // G. Context filters (comments / strings)
    // -----------------------------------------------------------------
    describe('context filters', () => {
        it('returns no completions inside line comments', async () => {
            const text = '// state ';
            const items = await packageModule.collectCompletionItems(
                createDocument(text, '/tmp/line-comment.fcstm'),
                {line: 0, character: text.length}
            );
            assert.deepEqual(items, []);
        });

        it('returns no completions inside block comments', async () => {
            const text = '/* TODO: state ';
            const items = await packageModule.collectCompletionItems(
                createDocument(text, '/tmp/block-comment.fcstm'),
                {line: 0, character: text.length}
            );
            assert.deepEqual(items, []);
        });

        it('returns no completions inside a `named "..."` string', async () => {
            const text = 'state Root named "';
            const items = await packageModule.collectCompletionItems(
                createDocument(text, '/tmp/string.fcstm'),
                {line: 0, character: text.length}
            );
            assert.deepEqual(items, []);
        });
    });

    // -----------------------------------------------------------------
    // H. Post-transition-target keywords
    // -----------------------------------------------------------------
    describe('post-transition-target keywords', () => {
        it('offers `::`, `:`, `if`, `effect` after `A -> B │`', async () => {
            const text = [
                'state Root {',
                '    state A;',
                '    state B;',
                '    A -> B ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/post-target.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 3));

            assert.ok(has(items, '::', 'keyword'));
            assert.ok(has(items, ':', 'keyword'));
            assert.ok(has(items, 'if', 'keyword'));
            assert.ok(has(items, 'effect', 'keyword'));
            // No math / variable noise at this position.
            assert.equal(items.some(item => item.kind === 'constant'), false);
            assert.equal(items.some(item => item.kind === 'function'), false);
            assert.equal(items.some(item => item.kind === 'variable'), false);
        });

        it('offers `effect` after `A -> B : if [...] │`', async () => {
            const text = [
                'def int n = 0;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    A -> B : if [n > 0] ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/post-guard-close.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'effect', 'keyword'));
            assert.equal(items.length, 1,
                `post-guard-close should only offer \`effect\`, got: ${labels(items).join(', ')}`);
        });

        it('offers `effect` after `A -> B :: Event │` (completed local trigger)', async () => {
            const text = [
                'state Root {',
                '    event Start;',
                '    state A;',
                '    state B;',
                '    A -> B :: Start ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/post-local-trigger.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'effect', 'keyword'));
            // `if` is deliberately NOT offered — the grammar disallows guards
            // after an event trigger.
            assert.equal(has(items, 'if', 'keyword'), false,
                'the grammar forbids `if` guards after an event trigger');
        });

        it('offers `effect` after `A -> B : Event │` (completed chain trigger)', async () => {
            const text = [
                'state Root {',
                '    event Ready;',
                '    state A;',
                '    state B;',
                '    A -> B : Ready ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/post-chain-trigger.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'effect', 'keyword'));
            assert.equal(has(items, 'if', 'keyword'), false,
                'the grammar forbids `if` guards after an event trigger');
        });

        it('completes `effect` from a partial `e` after `]`', async () => {
            const text = [
                'def int n = 0;',
                'state Root {',
                '    state A;',
                '    state B;',
                '    A -> B : if [n > 0] e',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/partial-effect.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, 'effect', 'keyword'));
        });
    });

    // -----------------------------------------------------------------
    // I-prelude. Inline lifecycle blocks (nested on one line)
    // -----------------------------------------------------------------
    describe('inline nested lifecycle bodies', () => {
        it('detects `state A { enter { │ }` as an operation-block body', async () => {
            const text = 'state Root { state A { enter { \n    }\n}';
            const doc = createDocument(text, '/tmp/inline-enter.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 0, character: 31});

            assert.ok(has(items, 'if', 'keyword'),
                `expected operation-block keywords inside nested inline \`enter {\`; got: ${labels(items, 'keyword').join(', ')}`);
            assert.ok(has(items, 'pi', 'constant'));
            assert.equal(has(items, 'state', 'keyword'), false,
                'structural starters must not appear inside an operation body');
        });

        it('detects `state A { effect { │ }` chained on one line as well', async () => {
            // This is written weirdly but is a legitimate transient state
            // during editing (user pasted a line they are refactoring).
            const text = 'state Root { state A; state B; A -> B effect { \n    }\n}';
            const doc = createDocument(text, '/tmp/inline-effect.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 0, character: 47});

            assert.ok(has(items, 'if', 'keyword'));
            assert.ok(has(items, 'pi', 'constant'));
        });
    });

    // -----------------------------------------------------------------
    // I-b. Post-keyword narrowing for `pseudo` and `!`
    // -----------------------------------------------------------------
    describe('post-keyword narrowing', () => {
        it('offers only `state` after `pseudo │`', async () => {
            const text = 'state Root {\n    pseudo \n}';
            const doc = createDocument(text, '/tmp/pseudo-alone.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 11});

            assert.ok(has(items, 'state', 'keyword'));
            assert.equal(items.length, 1,
                `after \`pseudo \` only \`state\` is valid; got: ${labels(items).join(', ')}`);
        });

        it('offers only `->` after a forced-transition source `!Foo │`', async () => {
            const text = [
                'state Root {',
                '    state Foo;',
                '    state Bar;',
                '    !Foo ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/forced-source.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 3));

            assert.ok(has(items, '->', 'keyword'));
            assert.equal(items.length, 1,
                `after a forced-transition source only the arrow is valid; got: ${labels(items).join(', ')}`);
        });

        it('offers state targets after `!Foo -> │` (arrow already written)', async () => {
            const text = [
                'state Root {',
                '    state Foo;',
                '    state Bar;',
                '    !Foo -> ',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/forced-target.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 3));

            assert.ok(has(items, 'Foo', 'class'));
            assert.ok(has(items, 'Bar', 'class'));
            assert.ok(has(items, '[*]', 'keyword'));
        });
    });

    // -----------------------------------------------------------------
    // I. Aspect / lifecycle modifier narrowing
    // -----------------------------------------------------------------
    describe('aspect and lifecycle modifiers', () => {
        it('offers only `during` after `>> `', async () => {
            const text = 'state Root {\n    >> \n}';
            const doc = createDocument(text, '/tmp/shift.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 7});

            assert.ok(has(items, 'during', 'keyword'));
            assert.equal(items.length, 1,
                `after \`>> \` only \`during\` is valid; got: ${labels(items).join(', ')}`);
        });

        it('offers only `before` / `after` after `>> during `', async () => {
            const text = 'state Root {\n    >> during \n}';
            const doc = createDocument(text, '/tmp/shift-during.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 14});

            assert.ok(has(items, 'before', 'keyword'));
            assert.ok(has(items, 'after', 'keyword'));
            assert.equal(items.length, 2);
        });

        it('offers only `abstract` after `>> during before `', async () => {
            const text = 'state Root {\n    >> during before \n}';
            const doc = createDocument(text, '/tmp/shift-during-before.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 21});

            assert.ok(has(items, 'abstract', 'keyword'));
            assert.equal(items.length, 1);
        });

        it('offers `abstract` / `ref` after `enter `', async () => {
            const text = 'state Root {\n    enter \n}';
            const doc = createDocument(text, '/tmp/enter-mod.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 10});

            assert.ok(has(items, 'abstract', 'keyword'));
            assert.ok(has(items, 'ref', 'keyword'));
            assert.equal(items.length, 2);
        });

        it('returns an empty list after `enter abstract ` (new identifier slot)', async () => {
            const text = 'state Root {\n    enter abstract \n}';
            const doc = createDocument(text, '/tmp/enter-abstract.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 19});

            assert.deepEqual(items, []);
        });
    });

    // -----------------------------------------------------------------
    // J. Variable-definition RHS
    // -----------------------------------------------------------------
    describe('variable definition positions', () => {
        it('offers `int` and `float` after `def `', async () => {
            const text = 'def ';
            const doc = createDocument(text, '/tmp/def-type.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 0, character: 4});

            assert.ok(has(items, 'int', 'keyword'));
            assert.ok(has(items, 'float', 'keyword'));
            assert.equal(items.length, 2);
        });

        it('returns an empty list after `def int ` (new identifier slot)', async () => {
            const text = 'def int ';
            const doc = createDocument(text, '/tmp/def-ident.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 0, character: 8});

            assert.deepEqual(items, []);
        });

        it('offers variables and math primitives inside `def int x = │`', async () => {
            const text = 'def int y = 1;\ndef int x = ';
            const doc = createDocument(text, '/tmp/def-rhs.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 12});

            assert.ok(has(items, 'y', 'variable'));
            assert.ok(has(items, 'pi', 'constant'));
            assert.ok(has(items, 'sin', 'function'));
            // Structural keywords must NOT leak into an expression context.
            assert.equal(has(items, 'state', 'keyword'), false);
            assert.equal(has(items, 'enter', 'keyword'), false);
        });
    });

    // -----------------------------------------------------------------
    // K. Identifier / naming slots — no completions expected
    // -----------------------------------------------------------------
    describe('identifier naming slots', () => {
        const slotPrefixes: Array<{label: string; prefix: string}> = [
            {label: 'state', prefix: 'state '},
            {label: 'pseudo state', prefix: 'pseudo state '},
            {label: 'event', prefix: 'event '},
            {label: 'def int', prefix: 'def int '},
        ];
        for (const {label, prefix} of slotPrefixes) {
            it(`returns nothing after \`${prefix.trim()} \` (new identifier slot, ${label})`, async () => {
                const text = `state Root {\n    ${prefix}\n}`;
                const pos = {line: 1, character: 4 + prefix.length};
                const doc = createDocument(text, `/tmp/naming-${label.replace(/\s+/g, '_')}.fcstm`);
                const items = await packageModule.collectCompletionItems(doc, pos);

                assert.deepEqual(items, []);
            });
        }
    });

    // -----------------------------------------------------------------
    // L. State body starter narrowing
    // -----------------------------------------------------------------
    describe('state body starters', () => {
        it('does not offer mid-keyword tokens at the start of a state-body line', async () => {
            const text = 'state Root {\n    \n}';
            const doc = createDocument(text, '/tmp/state-body-narrow.fcstm');
            const items = await packageModule.collectCompletionItems(doc, {line: 1, character: 4});

            // Precise set: structural starters, aspect & pseudo-state markers,
            // and the forced-transition marker. Everything else must stay out.
            for (const notOffered of [
                'abstract', 'ref', 'effect', 'if', 'else',
                'named', 'as', 'before', 'after', 'and', 'or', 'not',
                'int', 'float', 'def',
            ]) {
                assert.equal(has(items, notOffered, 'keyword'), false,
                    `keyword "${notOffered}" must not appear at a fresh state-body line`);
            }
            // And math primitives / functions must not appear at the start
            // of a statement slot either.
            assert.equal(items.some(item => item.kind === 'constant'), false);
            assert.equal(items.some(item => item.kind === 'function'), false);
        });
    });

    // -----------------------------------------------------------------
    // M. Invalid-syntax narrow guards
    // -----------------------------------------------------------------
    describe('invalid-syntax positions', () => {
        it('offers nothing after the invalid `::/` sequence', async () => {
            const text = [
                'state Root {',
                '    state A;',
                '    state B;',
                '    A -> B :: /',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/invalid-double-colon-slash.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 3));

            assert.deepEqual(items, [], '`::/` is not grammatically valid; offer nothing');
        });
    });

    // -----------------------------------------------------------------
    // N. In-file absolute-path completions
    // -----------------------------------------------------------------
    describe('absolute-path completions', () => {
        it('resolves `/RootName.│` as the root state itself, not a missing nested state', async () => {
            // Previously the path resolver descended from the root looking
            // for a child named after the root; on the common `/RootName.*`
            // form that pattern never matched and returned no completions.
            const text = [
                'state HVAC {',
                '    event PowerOn;',
                '    state Off;',
                '    state On;',
                '    Off -> On : /HVAC.',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/abs-root-prefix.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 4));

            assert.ok(has(items, '/HVAC.Off', 'class'),
                `expected "/HVAC.Off" but got: ${labels(items).join(', ')}`);
            assert.ok(has(items, '/HVAC.On', 'class'));
            assert.ok(has(items, '/HVAC.PowerOn', 'event'));
        });

        it('completes events under an in-file absolute path `/Parent.│`', async () => {
            const text = [
                'state Root {',
                '    state Parent {',
                '        event Ready;',
                '        event Done;',
                '    }',
                '    state Consumer;',
                '    state Idle;',
                '    Idle -> Consumer : /Parent.',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/absolute-path.fcstm');
            const items = await packageModule.collectCompletionItems(doc, endOfLine(text, 7));

            assert.ok(
                has(items, '/Parent.Ready', 'event') || has(items, '/Parent.Done', 'event'),
                `expected events under /Parent.*; got events: ${labels(items, 'event').join(', ')}`
            );
        });
    });
});

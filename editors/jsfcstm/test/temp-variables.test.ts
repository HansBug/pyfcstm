/**
 * Reference / highlight / definition coverage for block-local temporary
 * variables.
 *
 * Per the FCSTM DSL: assigning to an undeclared name inside an
 * `enter / during / exit / effect` block creates a temporary variable whose
 * scope is the entire block (including nested `if / else` branches) and
 * whose lifetime ends when the block finishes.
 *
 * These tests pin down:
 *  - Temps declared in one block are isolated from same-named temps in
 *    sibling or unrelated blocks.
 *  - Temps DO span nested `if / else` branches within the same block.
 *  - The earliest assignment becomes the "definition" anchor for go-to-def.
 *  - Temps never shadow or cross-link globals of the same name.
 *  - Temps do not leak out into workspace symbol queries.
 */
import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

type Position = { line: number; character: number };
type Range = { start: Position; end: Position };
type Reference = { uri: string; range: Range; role: 'definition' | 'reference' | 'write' };

function slice(doc: ReturnType<typeof createDocument>, range: Range): string {
    const text = doc.lineAt(range.start.line).text;
    return text.slice(range.start.character, range.end.character);
}

function posOfNth(
    doc: ReturnType<typeof createDocument>,
    line: number,
    needle: string,
    occurrenceIndex = 0
): Position {
    const text = doc.lineAt(line).text;
    let idx = -1;
    for (let i = 0; i <= occurrenceIndex; i++) {
        idx = text.indexOf(needle, idx + 1);
        if (idx < 0) {
            throw new Error(`"${needle}" occurrence ${occurrenceIndex} not found on line ${line}`);
        }
    }
    return {line, character: idx + Math.min(1, needle.length - 1)};
}

function countRoles(refs: Reference[]): Record<string, number> {
    const counts: Record<string, number> = {};
    for (const r of refs) {
        counts[r.role] = (counts[r.role] || 0) + 1;
    }
    return counts;
}

describe('jsfcstm block-local temporary variables', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    // ------------------------------------------------------------------
    // The exact scenario from the user's report: deeply nested if / else
    // chain where temps are read and written across branches.
    // ------------------------------------------------------------------
    describe('nested if / else branches inside one `during` block', () => {
        const text = [
            'def int x = 0;',                                          // 0
            'def int y = 0;',                                          // 1
            'def int z = 0;',                                          // 2
            'def int flag = 0;',                                       // 3
            '',                                                         // 4
            'state Root {',                                            // 5
            '    state Active {',                                      // 6
            '        during {',                                        // 7
            '            tmp = x + 1;',                               // 8
            '',                                                         // 9
            '            if [flag > 0] {',                             // 10
            '                tmp = tmp + 10;',                        // 11
            '',                                                         // 12
            '                if [y > 5] {',                            // 13
            '                    bonus = y + 2;',                     // 14
            '                    z = tmp + bonus;',                   // 15
            '                } else {',                                // 16
            '                    z = tmp - y;',                        // 17
            '                }',                                        // 18
            '            } else if [x > 3] {',                         // 19
            '                tmp = tmp + 20;',                         // 20
            '                z = tmp;',                                // 21
            '            } else {',                                    // 22
            '                z = tmp;',                                // 23
            '            }',                                            // 24
            '',                                                         // 25
            '            x = z + tmp;',                                // 26
            '        }',                                                // 27
            '    }',                                                    // 28
            '',                                                         // 29
            '    [*] -> Active;',                                      // 30
            '}',                                                        // 31
        ].join('\n');

        it('clicking any `tmp` groups all 10 occurrences across branches under one key', async () => {
            const doc = createDocument(text, '/tmp/temp-nested.fcstm');
            const refs = await packageModule.collectReferences(doc, posOfNth(doc, 8, 'tmp'), true) as Reference[];
            assert.equal(refs.length, 10);
            for (const r of refs) {
                assert.equal(slice(doc, r.range), 'tmp');
            }
            assert.deepEqual(
                countRoles(refs),
                {definition: 1, write: 2, reference: 7},
                `expected 1 definition + 2 writes + 7 references for tmp, got ${JSON.stringify(countRoles(refs))}`
            );
        });

        it('clicking `tmp` from a deeply-nested if branch still surfaces every other occurrence', async () => {
            const doc = createDocument(text, '/tmp/temp-nested-inner.fcstm');
            // L15 "z = tmp + bonus" — tmp is third token
            const refs = await packageModule.collectReferences(doc, posOfNth(doc, 15, 'tmp'), true) as Reference[];
            assert.equal(refs.length, 10, 'inner-branch click must still group with the outer-scope tmp');
            const lines = refs.map(r => r.range.start.line).sort((a, b) => a - b);
            assert.deepEqual(lines, [8, 11, 11, 15, 17, 20, 20, 21, 23, 26]);
        });

        it('go-to-definition on `tmp` from any usage jumps to the earliest assignment', async () => {
            const doc = createDocument(text, '/tmp/temp-nested-def.fcstm');
            // From any occurrence of `tmp` the definition should land on L8
            // (the first `tmp = x + 1;`).
            for (const click of [[8, 'tmp'], [11, 'tmp'], [15, 'tmp'], [26, 'tmp']] as const) {
                const def = await packageModule.resolveDefinitionLocation(doc, posOfNth(doc, click[0], click[1]));
                assert.ok(def, `expected a definition from L${click[0]}`);
                assert.equal(def!.range.start.line, 8,
                    `go-to-def from L${click[0]} should hit L8 (earliest tmp assignment)`);
            }
        });

        it('`bonus` scoped within the same block is a distinct temp from `tmp`', async () => {
            const doc = createDocument(text, '/tmp/temp-bonus.fcstm');
            const refs = await packageModule.collectReferences(doc, posOfNth(doc, 14, 'bonus'), true) as Reference[];
            assert.equal(refs.length, 2);
            assert.deepEqual(countRoles(refs), {definition: 1, reference: 1});
            for (const r of refs) {
                assert.equal(slice(doc, r.range), 'bonus');
            }
            // Must NOT cross-link with `tmp` occurrences.
            assert.equal(refs.some(r => slice(doc, r.range) === 'tmp'), false);
        });

        it('globals (`x` / `z` / `y`) referenced from inside the block keep the global identity', async () => {
            const doc = createDocument(text, '/tmp/temp-globals.fcstm');
            const refs = await packageModule.collectReferences(doc, posOfNth(doc, 8, 'x'), true) as Reference[];
            // Global `x` at L0 decl, used at L8 (RHS), L19 (guard), L26 (LHS write).
            assert.equal(refs.length, 4);
            assert.ok(refs.some(r => r.role === 'definition' && r.range.start.line === 0),
                `global x must still resolve to its top-level declaration`);
        });
    });

    // ------------------------------------------------------------------
    // Sibling lifecycle blocks: same-named temps must stay isolated.
    // ------------------------------------------------------------------
    describe('sibling block isolation', () => {
        const text = [
            'def int x = 0;',                           // 0
            'state Root {',                             // 1
            '    state A {',                            // 2
            '        enter {',                          // 3
            '            temp = x + 1;',                // 4
            '            x = temp;',                    // 5
            '        }',                                // 6
            '        during {',                         // 7
            '            temp = x * 2;',                // 8 — same name, different scope
            '            x = temp;',                    // 9
            '        }',                                // 10
            '        exit {',                           // 11
            '            temp = 99;',                  // 12 — same name, third scope
            '            x = temp;',                    // 13
            '        }',                                // 14
            '    }',                                    // 15
            '    state B {',                            // 16
            '        during {',                         // 17
            '            temp = 1;',                    // 18 — fourth independent temp
            '        }',                                // 19
            '    }',                                    // 20
            '    [*] -> A;',                            // 21
            '}',                                        // 22
        ].join('\n');

        it('each lifecycle action has its own independent `temp`', async () => {
            const doc = createDocument(text, '/tmp/temp-sibling.fcstm');

            const fromEnter = await packageModule.collectReferences(doc, posOfNth(doc, 4, 'temp'), true) as Reference[];
            assert.equal(fromEnter.length, 2, 'enter-block temp should have 2 occurrences');
            assert.deepEqual(fromEnter.map(r => r.range.start.line).sort((a, b) => a - b), [4, 5]);

            const fromDuring = await packageModule.collectReferences(doc, posOfNth(doc, 8, 'temp'), true) as Reference[];
            assert.equal(fromDuring.length, 2, 'during-block temp should have 2 occurrences');
            assert.deepEqual(fromDuring.map(r => r.range.start.line).sort((a, b) => a - b), [8, 9]);

            const fromExit = await packageModule.collectReferences(doc, posOfNth(doc, 12, 'temp'), true) as Reference[];
            assert.equal(fromExit.length, 2);
            assert.deepEqual(fromExit.map(r => r.range.start.line).sort((a, b) => a - b), [12, 13]);

            const fromB = await packageModule.collectReferences(doc, posOfNth(doc, 18, 'temp'), true) as Reference[];
            assert.equal(fromB.length, 1, `state B's during-block temp is orphan, only the write itself`);

            // Cross-block non-links: the enter-block click must NOT surface
            // the during / exit / B.during occurrences.
            for (const r of fromEnter) {
                assert.ok([4, 5].includes(r.range.start.line),
                    `enter-block temp query leaked to L${r.range.start.line}`);
            }
        });
    });

    // ------------------------------------------------------------------
    // Temp declared in one branch but used in a sibling branch — this is
    // invalid at runtime ("using before first assignment") but the editor
    // should still group them since they share a name within the block.
    // ------------------------------------------------------------------
    describe('branch-local reads before assignment still group', () => {
        const text = [
            'def int x = 0;',                           // 0
            'state Root {',                             // 1
            '    state A {',                            // 2
            '        during {',                         // 3
            '            if [x > 0] {',                 // 4
            '                temp = x;',                // 5 first/only assignment
            '            } else {',                     // 6
            '                x = temp;',                // 7 RHS read in sibling branch
            '            }',                            // 8
            '        }',                                // 9
            '    }',                                    // 10
            '    [*] -> A;',                            // 11
            '}',                                        // 12
        ].join('\n');

        it('temp read in else-branch still links back to the assignment in if-branch', async () => {
            const doc = createDocument(text, '/tmp/temp-branches.fcstm');
            const refs = await packageModule.collectReferences(doc, posOfNth(doc, 5, 'temp'), true) as Reference[];
            assert.equal(refs.length, 2);
            assert.deepEqual(
                countRoles(refs),
                {definition: 1, reference: 1},
                'assignment in if-branch should be definition; read in else-branch should be reference'
            );

            const def = await packageModule.resolveDefinitionLocation(doc, posOfNth(doc, 7, 'temp'));
            assert.ok(def);
            assert.equal(def!.range.start.line, 5,
                `go-to-definition from an else-branch read should still land on the if-branch assignment`);
        });
    });

    // ------------------------------------------------------------------
    // Transition effect blocks have their own temp scope.
    // ------------------------------------------------------------------
    describe('transition effect-block temp scope', () => {
        const text = [
            'def int x = 0;',                                          // 0
            'state Root {',                                            // 1
            '    state A;',                                            // 2
            '    state B;',                                            // 3
            '    A -> B effect {',                                     // 4
            '        acc = x + 1;',                                    // 5
            '        x = acc * 2;',                                    // 6
            '    };',                                                   // 7
            '    state C;',                                            // 8
            '    state D;',                                            // 9
            '    C -> D effect {',                                     // 10
            '        acc = 42;',                                       // 11 — different effect, different scope
            '        x = acc;',                                        // 12
            '    };',                                                   // 13
            '    [*] -> A;',                                           // 14
            '}',                                                        // 15
        ].join('\n');

        it('effect blocks on different transitions own independent temps', async () => {
            const doc = createDocument(text, '/tmp/temp-effect.fcstm');

            const fromFirst = await packageModule.collectReferences(doc, posOfNth(doc, 5, 'acc'), true) as Reference[];
            assert.equal(fromFirst.length, 2);
            assert.deepEqual(fromFirst.map(r => r.range.start.line).sort((a, b) => a - b), [5, 6]);

            const fromSecond = await packageModule.collectReferences(doc, posOfNth(doc, 11, 'acc'), true) as Reference[];
            assert.equal(fromSecond.length, 2);
            assert.deepEqual(fromSecond.map(r => r.range.start.line).sort((a, b) => a - b), [11, 12]);
        });
    });

    // ------------------------------------------------------------------
    // Temp-variable discovery must walk unary / function / conditional
    // expressions too, not just plain identifiers or binary operators.
    // ------------------------------------------------------------------
    describe('expression-shape coverage inside temp scopes', () => {
        const text = [
            'def int sensor = 1;',                                     // 0
            'def int fallback = 2;',                                   // 1
            'def int mode = 0;',                                       // 2
            'def int output = 0;',                                     // 3
            'state Root {',                                            // 4
            '    state A {',                                            // 5
            '        during {',                                         // 6
            '            tmp = (mode > 0) ? abs(sensor) : -fallback;',  // 7
            '            output = tmp;',                                // 8
            '        }',                                                // 9
            '    }',                                                    // 10
            '    [*] -> A;',                                            // 11
            '}',                                                        // 12
        ].join('\n');

        it('links temps and globals through conditional, function, and unary expressions', async () => {
            const doc = createDocument(text, '/tmp/temp-expression-shapes.fcstm');

            const tempRefs = await packageModule.collectReferences(doc, posOfNth(doc, 7, 'tmp'), true) as Reference[];
            assert.equal(tempRefs.length, 2);
            assert.deepEqual(countRoles(tempRefs), {definition: 1, reference: 1});

            const sensorRefs = await packageModule.collectReferences(doc, posOfNth(doc, 7, 'sensor'), true) as Reference[];
            assert.deepEqual(sensorRefs.map(r => r.range.start.line).sort((a, b) => a - b), [0, 7]);

            const fallbackRefs = await packageModule.collectReferences(doc, posOfNth(doc, 7, 'fallback'), true) as Reference[];
            assert.deepEqual(fallbackRefs.map(r => r.range.start.line).sort((a, b) => a - b), [1, 7]);

            const modeRefs = await packageModule.collectReferences(doc, posOfNth(doc, 7, 'mode'), true) as Reference[];
            assert.deepEqual(modeRefs.map(r => r.range.start.line).sort((a, b) => a - b), [2, 7]);
        });
    });

    // ------------------------------------------------------------------
    // Temps must never leak out as workspace symbols.
    // ------------------------------------------------------------------
    describe('workspace symbol hygiene', () => {
        it('temp variables are not returned by workspace symbol search', async () => {
            const text = [
                'def int persisted = 0;',
                'state Root {',
                '    state A {',
                '        during {',
                '            my_tmp = persisted + 1;',
                '            persisted = my_tmp;',
                '        }',
                '    }',
                '    [*] -> A;',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/temp-workspace.fcstm');
            const symbols = await packageModule.collectWorkspaceSymbols([doc], 'my_tmp');
            assert.deepEqual(symbols, [],
                'temp variables must not surface as workspace symbols');

            const persistedSymbols = await packageModule.collectWorkspaceSymbols([doc], 'persisted');
            assert.ok(persistedSymbols.length >= 1,
                'global `persisted` must still be indexed as a workspace symbol');
        });
    });
});

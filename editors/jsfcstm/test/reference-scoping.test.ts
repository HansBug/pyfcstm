/**
 * Scope-aware reference / highlight / go-to-definition coverage.
 *
 * The FCSTM runtime treats `::`, `:` and `/` as three DISTINCT event
 * scopes — a local `::Event` at source state `Src` is a different runtime
 * event from a chain `:Event` at the parent scope or an absolute `/Event`
 * at the root. Reference / highlight / rename behaviour must reflect that
 * distinction, and must never cross-link two identifiers just because they
 * share a name.
 *
 * This file pins down that behaviour by exercising click-like queries at
 * every interesting position in a hand-written machine, then asserting the
 * returned occurrences match the logically-identical event / state /
 * variable only.
 */
import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

type Position = { line: number; character: number };
type Range = { start: Position; end: Position };
type Location = { uri: string; range: Range };
type Reference = Location & { role: 'definition' | 'reference' | 'write' };
type Highlight = { range: Range; kind: 'text' | 'read' | 'write' };

function slice(doc: ReturnType<typeof createDocument>, range: Range): string {
    const text = doc.lineAt(range.start.line).text;
    return text.slice(range.start.character, range.end.character);
}

function posOfNth(doc: ReturnType<typeof createDocument>, line: number, needle: string, occurrenceIndex = 0): Position {
    const text = doc.lineAt(line).text;
    let idx = -1;
    for (let i = 0; i <= occurrenceIndex; i++) {
        idx = text.indexOf(needle, idx + 1);
        if (idx < 0) {
            throw new Error(`"${needle}" occurrence ${occurrenceIndex} not found on line ${line}: ${JSON.stringify(text)}`);
        }
    }
    return {line, character: idx + Math.min(1, needle.length - 1)};
}

function refsAt(doc: ReturnType<typeof createDocument>, position: Position): Promise<Reference[]> {
    return packageModule.collectReferences(doc, position, true);
}

function highlightsAt(doc: ReturnType<typeof createDocument>, position: Position): Promise<Highlight[]> {
    return packageModule.collectDocumentHighlights(doc, position);
}

function defAt(doc: ReturnType<typeof createDocument>, position: Position): Promise<Location | null> {
    return packageModule.resolveDefinitionLocation(doc, position);
}

function assertSameSlice(doc: ReturnType<typeof createDocument>, items: Array<{range: Range}>, expected: string): void {
    for (const item of items) {
        assert.equal(slice(doc, item.range), expected,
            `expected every occurrence to slice "${expected}", got ${JSON.stringify(slice(doc, item.range))} at L${item.range.start.line}:${item.range.start.character}`);
    }
}

describe('jsfcstm reference scoping', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    // ------------------------------------------------------------------
    // Scope distinction: `::` vs `:` vs `/` for same-named event `Evt`
    // ------------------------------------------------------------------
    describe('event scope distinction (:: vs : vs /)', () => {
        // Machine layout (simplified):
        //   Root                       <- declares event Evt (root scope)
        //     A                        <- declares event Evt (chain scope inside A)
        //       B, C                   <- leaf states
        //       B -> C :: Evt          <- local: Root.A.B.Evt (no declaration)
        //       B -> C :  Evt          <- chain: Root.A.Evt   (= A.Evt decl)
        //       B -> C : /Evt          <- absolute: Root.Evt  (= root Evt decl)
        //     D                        <- leaf state
        //     A -> D :: Evt            <- local at Root: Root.A.Evt (= A.Evt decl)
        //     A -> D :  Evt            <- chain at Root: Root.Evt   (= root Evt decl)
        const text = [
            'state Root {',                          // 0
            '    event Evt;',                        // 1 Root.Evt decl
            '    state A {',                         // 2
            '        event Evt;',                    // 3 Root.A.Evt decl
            '        state B;',                      // 4
            '        state C;',                      // 5
            '        [*] -> B;',                     // 6
            '        B -> C :: Evt;',                // 7 Root.A.B.Evt local (unique)
            '        B -> C : Evt;',                 // 8 Root.A.Evt chain  (= L3)
            '        B -> C : /Evt;',                // 9 Root.Evt absolute (= L1)
            '    }',                                  // 10
            '    state D;',                          // 11
            '    [*] -> A;',                         // 12
            '    A -> D :: Evt;',                    // 13 Root.A.Evt local at A (= L3)
            '    A -> D : Evt;',                     // 14 Root.Evt chain at root (= L1)
            '}',                                      // 15
        ].join('\n');

        it('local `::Evt` at leaf B is a unique event: only the click highlights', async () => {
            const doc = createDocument(text, '/tmp/scope-local-leaf.fcstm');
            const pos = posOfNth(doc, 7, 'Evt');
            const refs = await refsAt(doc, pos);
            const highlights = await highlightsAt(doc, pos);
            const definition = await defAt(doc, pos);

            // This local event is implicit — never declared anywhere. It
            // should surface exactly one occurrence (the click itself) and
            // must NOT pull in the `event Evt;` declarations at L1 or L3.
            assert.deepEqual(
                refs.map(r => [r.range.start.line, r.role]),
                [[7, 'reference']],
                `local :: event at a leaf state should not cross-link declared scopes`
            );
            assert.deepEqual(highlights.map(h => h.range.start.line), [7]);
            assertSameSlice(doc, refs, 'Evt');
            // No declared `event Evt;` at `Root.A.B`, so no formal definition.
            assert.equal(definition, null);
        });

        it('chain `: Evt` inside A groups with A\'s declaration and the `::Evt` at A', async () => {
            const doc = createDocument(text, '/tmp/scope-chain-A.fcstm');
            const pos = posOfNth(doc, 8, 'Evt');
            const refs = await refsAt(doc, pos);
            const highlights = await highlightsAt(doc, pos);
            const definition = await defAt(doc, pos);

            // `:Evt` at owner `A` resolves to `Root.A.Evt`. L3 is the
            // declaration, L13's `:: Evt` also resolves to `Root.A.Evt`
            // because its source is `A`.
            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [3, 8, 13]);
            assert.deepEqual(highlights.map(h => h.range.start.line).sort((a,b) => a-b), [3, 8, 13]);
            // Must NOT include the root-scoped `Evt` at L1 / L9 / L14.
            assert.equal(refs.some(r => r.range.start.line === 1), false);
            assert.equal(refs.some(r => r.range.start.line === 9), false);
            assert.equal(refs.some(r => r.range.start.line === 14), false);
            // Must NOT include the leaf-local `::Evt` at L7 either.
            assert.equal(refs.some(r => r.range.start.line === 7), false);

            assert.ok(definition);
            assert.equal(definition!.range.start.line, 3,
                `go-to-definition from a chain \`: Evt\` inside A should navigate to Root.A.Evt at L3`);
        });

        it('absolute `/Evt` groups only with the root Evt declaration and its sibling references', async () => {
            const doc = createDocument(text, '/tmp/scope-absolute.fcstm');
            const pos = posOfNth(doc, 9, 'Evt');
            const refs = await refsAt(doc, pos);
            const highlights = await highlightsAt(doc, pos);
            const definition = await defAt(doc, pos);

            // Absolute scope resolves to Root.Evt. L1 is the decl, L14's
            // chain `: Evt` at the root owner also resolves to Root.Evt.
            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [1, 9, 14]);
            assert.deepEqual(highlights.map(h => h.range.start.line).sort((a,b) => a-b), [1, 9, 14]);
            assert.equal(refs.some(r => r.range.start.line === 3), false);
            assert.equal(refs.some(r => r.range.start.line === 7), false);
            assert.equal(refs.some(r => r.range.start.line === 8), false);
            assert.equal(refs.some(r => r.range.start.line === 13), false);

            assert.ok(definition);
            assert.equal(definition!.range.start.line, 1);
        });

        it('local `::Evt` at A (source=A, owner=Root) matches the A scope, not the root scope', async () => {
            const doc = createDocument(text, '/tmp/scope-local-A-source.fcstm');
            const pos = posOfNth(doc, 13, 'Evt');
            const refs = await refsAt(doc, pos);

            // L13's `::Evt` has source state A, so it resolves to Root.A.Evt
            // — the SAME event as L8's chain `: Evt` inside A and L3's decl.
            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [3, 8, 13]);
            assert.equal(refs.some(r => r.range.start.line === 1), false,
                `local :: at A must not cross-link the root-scope Evt declaration`);
        });

        it('chain `: Evt` at the root owner resolves to the root declaration', async () => {
            const doc = createDocument(text, '/tmp/scope-chain-root.fcstm');
            const pos = posOfNth(doc, 14, 'Evt');
            const refs = await refsAt(doc, pos);

            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [1, 9, 14]);
        });

        it('clicking the root `event Evt;` declaration surfaces only root-scope references', async () => {
            const doc = createDocument(text, '/tmp/scope-root-decl.fcstm');
            const pos = posOfNth(doc, 1, 'Evt');
            const refs = await refsAt(doc, pos);

            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [1, 9, 14]);
            assert.equal(refs.some(r => r.range.start.line === 3), false);
            assert.equal(refs.some(r => r.range.start.line === 7), false);
            assert.equal(refs.some(r => r.range.start.line === 8), false);
            assert.equal(refs.some(r => r.range.start.line === 13), false);
        });

        it('clicking the A-scope `event Evt;` declaration surfaces only A-scope references', async () => {
            const doc = createDocument(text, '/tmp/scope-a-decl.fcstm');
            const pos = posOfNth(doc, 3, 'Evt');
            const refs = await refsAt(doc, pos);

            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [3, 8, 13]);
            assert.equal(refs.some(r => r.range.start.line === 1), false);
            assert.equal(refs.some(r => r.range.start.line === 9), false);
            assert.equal(refs.some(r => r.range.start.line === 14), false);
        });
    });

    // ------------------------------------------------------------------
    // Same-named STATES at different scope levels must stay distinct
    // ------------------------------------------------------------------
    describe('state scope distinction', () => {
        const text = [
            'state Root {',                          // 0
            '    state Child;',                      // 1 Root.Child
            '    state Container {',                 // 2
            '        state Child;',                  // 3 Root.Container.Child
            '        state Other;',                  // 4
            '        [*] -> Child;',                 // 5 -> Root.Container.Child
            '        Child -> Other;',               // 6 Root.Container.Child
            '    }',                                  // 7
            '    [*] -> Child;',                     // 8 -> Root.Child
            '    Child -> Container;',               // 9 Root.Child
            '}',                                      // 10
        ].join('\n');

        it('outer `Child` references only outer-scope occurrences', async () => {
            const doc = createDocument(text, '/tmp/state-scope-outer.fcstm');
            const pos = posOfNth(doc, 1, 'Child');
            const refs = await refsAt(doc, pos);

            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [1, 8, 9]);
            assert.equal(refs.some(r => r.range.start.line === 3), false,
                `outer Child must not highlight inner Child declaration`);
            assert.equal(refs.some(r => r.range.start.line === 5), false);
            assert.equal(refs.some(r => r.range.start.line === 6), false);
        });

        it('inner `Child` references only inner-scope occurrences', async () => {
            const doc = createDocument(text, '/tmp/state-scope-inner.fcstm');
            const pos = posOfNth(doc, 3, 'Child');
            const refs = await refsAt(doc, pos);

            assert.deepEqual(refs.map(r => r.range.start.line).sort((a,b) => a-b), [3, 5, 6]);
            assert.equal(refs.some(r => r.range.start.line === 1), false);
            assert.equal(refs.some(r => r.range.start.line === 8), false);
            assert.equal(refs.some(r => r.range.start.line === 9), false);
        });
    });

    // ------------------------------------------------------------------
    // State-segment click navigation inside absolute / chain event paths
    // ------------------------------------------------------------------
    describe('state-segment navigation in dotted paths', () => {
        const text = [
            'state Root {',                          // 0
            '    state Parent {',                    // 1
            '        event Evt;',                    // 2 Root.Parent.Evt
            '        state Inner;',                  // 3
            '    }',                                  // 4
            '    state A;',                          // 5
            '    state B;',                          // 6
            '    [*] -> A;',                         // 7
            '    A -> B : /Parent.Evt;',             // 8 abs path, 2 segments
            '    A -> B : /Parent.Inner.Evt;',       // 9 abs path, 3 segments (implicit last event)
            '}',                                      // 10
        ].join('\n');

        it('click on `Parent` segment in /Parent.Evt navigates to the Parent state', async () => {
            const doc = createDocument(text, '/tmp/abs-parent-segment.fcstm');
            const pos = posOfNth(doc, 8, 'Parent');
            const definition = await defAt(doc, pos);
            const refs = await refsAt(doc, pos);

            assert.ok(definition);
            assert.equal(definition!.range.start.line, 1,
                `clicking on Parent in /Parent.Evt should go to the Parent state declaration`);
            // The declaration and both absolute-path segments should show up.
            const parentLines = refs.filter(r => slice(doc, r.range) === 'Parent').map(r => r.range.start.line).sort((a,b) => a-b);
            assert.deepEqual(parentLines, [1, 8, 9]);
        });

        it('click on `Inner` segment in /Parent.Inner.Evt navigates to the Inner state', async () => {
            const doc = createDocument(text, '/tmp/abs-inner-segment.fcstm');
            const pos = posOfNth(doc, 9, 'Inner');
            const definition = await defAt(doc, pos);

            assert.ok(definition);
            assert.equal(definition!.range.start.line, 3,
                `clicking on Inner in /Parent.Inner.Evt should go to the Inner state declaration`);
        });

        it('click on the final event segment in /Parent.Evt navigates to the declared event', async () => {
            const doc = createDocument(text, '/tmp/abs-event-segment.fcstm');
            const pos = posOfNth(doc, 8, 'Evt');
            const definition = await defAt(doc, pos);

            assert.ok(definition);
            assert.equal(definition!.range.start.line, 2);
        });
    });

    // ------------------------------------------------------------------
    // State-segment click navigation inside action ref paths
    // ------------------------------------------------------------------
    describe('state-segment navigation in action refs', () => {
        const text = [
            'state Root {',                          // 0
            '    state Parent {',                    // 1
            '        enter SetUp { }',               // 2 Root.Parent.SetUp
            '    }',                                  // 3
            '    state A {',                         // 4
            '        enter ref /Parent.SetUp;',      // 5 abs path to the action
            '    }',                                  // 6
            '}',                                      // 7
        ].join('\n');

        it('click on `Parent` in the ref path navigates to the Parent state declaration', async () => {
            const doc = createDocument(text, '/tmp/ref-path-parent.fcstm');
            const pos = posOfNth(doc, 5, 'Parent');
            const definition = await defAt(doc, pos);

            assert.ok(definition);
            assert.equal(definition!.range.start.line, 1);
        });

        it('click on `SetUp` in the ref path navigates to the action definition', async () => {
            const doc = createDocument(text, '/tmp/ref-path-setup.fcstm');
            const pos = posOfNth(doc, 5, 'SetUp');
            const definition = await defAt(doc, pos);

            assert.ok(definition);
            assert.equal(definition!.range.start.line, 2);
        });
    });

    // ------------------------------------------------------------------
    // Variable references inside guards, effects, enter/during/exit blocks
    // ------------------------------------------------------------------
    describe('variable references across block types', () => {
        const text = [
            'def int counter = 0;',                   // 0
            'def int threshold = 5;',                 // 1
            'state Root {',                           // 2
            '    state A;',                           // 3
            '    state B;',                           // 4
            '    [*] -> A;',                          // 5
            '    A -> B : if [counter >= threshold] effect { counter = 0; };', // 6
            '    state Inner {',                      // 7
            '        enter { threshold = threshold + 1; }', // 8
            '        during { counter = counter + 1; }',    // 9
            '    }',                                  // 10
            '}',                                      // 11
        ].join('\n');

        function countRoles(refs: Reference[]): Record<string, number> {
            const counts: Record<string, number> = {};
            for (const r of refs) {
                counts[r.role] = (counts[r.role] || 0) + 1;
            }
            return counts;
        }

        it('click on `counter` in any usage gathers all 5 occurrences (decl + guard + effect + during write + during read)', async () => {
            const doc = createDocument(text, '/tmp/var-counter.fcstm');
            const refs = await refsAt(doc, posOfNth(doc, 6, 'counter'));

            assert.equal(refs.length, 5);
            assert.deepEqual(countRoles(refs), {definition: 1, reference: 2, write: 2});
            assertSameSlice(doc, refs, 'counter');
        });

        it('click on `threshold` in any usage gathers all 4 occurrences (decl + guard + enter write + enter read)', async () => {
            const doc = createDocument(text, '/tmp/var-threshold.fcstm');
            const refs = await refsAt(doc, posOfNth(doc, 8, 'threshold'));

            assert.equal(refs.length, 4);
            assert.deepEqual(countRoles(refs), {definition: 1, reference: 2, write: 1});
            assertSameSlice(doc, refs, 'threshold');
        });
    });

    // ------------------------------------------------------------------
    // Ghost occurrences must not leak through when the parser fails
    // ------------------------------------------------------------------
    describe('resilience against parser edge cases', () => {
        it('an event name that collides with a reserved token produces no ghost definition occurrence', async () => {
            // The grammar reserves `E` as the mathematical constant. A
            // user writing `event E;` fails to parse and the semantic
            // builder falls back to an unnamed event. We must not emit a
            // zero-width occurrence at the top of the document for that
            // broken event, otherwise every cross-document query picks up
            // the ghost.
            const text = [
                'state Root {',
                '    event E;',
                '    state A;',
                '    [*] -> A;',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/reserved-event-name.fcstm');

            const occurrences = await packageModule.collectSymbolOccurrences(doc);
            const ghosts = occurrences.filter(o =>
                o.range.start.line === 0
                && o.range.start.character === 0
                && o.range.end.line === 0
                && o.range.end.character === 0
            );
            assert.deepEqual(ghosts, [],
                `no ghost L0:0-0 occurrences should be emitted for broken event declarations`);

            const eventOccs = occurrences.filter(o => o.kind === 'event' && !o.name);
            assert.deepEqual(eventOccs, [],
                `no empty-named event occurrence should leak through`);
        });
    });
});

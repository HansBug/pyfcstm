/**
 * Outline layout + detail invariants.
 *
 * The outline previously wrapped every lifecycle / aspect action behind a
 * double `Actions → Lifecycle / Aspects` container, stamped transitions
 * with cryptic internal-kind details ("normal local trigger"), and gave
 * composite states an empty detail string. This file pins down the
 * redesigned behaviour:
 *
 *   - Lifecycle / aspect actions are direct children of their owning
 *     state and use the Method icon (distinct from transition Function
 *     icon).
 *   - Action detail carries the actual mode: a body preview for
 *     operation blocks, `abstract`, or `ref <path>`.
 *   - Transition detail surfaces semantic role (initial / terminal /
 *     forced), the guard text, and an `effect` marker.
 *   - Composite states get a shape summary (`3 states · 5 transitions ·
 *     2 events`) as their detail.
 *   - Imports still surface as their own group so import aliases stay
 *     discoverable in the outline.
 */
import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

type DocumentSymbol = Awaited<ReturnType<typeof packageModule.collectDocumentSymbols>>[number];

function findByName(symbols: readonly DocumentSymbol[], name: string): DocumentSymbol | undefined {
    return symbols.find(item => item.name === name);
}

function findPath(root: DocumentSymbol, path: string[]): DocumentSymbol | undefined {
    let current: DocumentSymbol | undefined = root;
    for (const segment of path) {
        if (!current) {
            return undefined;
        }
        current = findByName(current.children, segment);
    }
    return current;
}

describe('jsfcstm outline layout redesign', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    // ------------------------------------------------------------------
    // Actions are flattened — no more Actions/Lifecycle/Aspects wrappers
    // ------------------------------------------------------------------
    describe('lifecycle / aspect actions', () => {
        const text = [
            'def int counter = 0;',                  // 0
            'state Root {',                          // 1
            '    enter { counter = 0; }',            // 2
            '    during { counter = counter + 1; }', // 3
            '    exit { counter = 0; }',             // 4
            '    >> during before { counter = 1; }', // 5
            '    >> during after abstract Audit;',   // 6
            '    state Leaf;',                       // 7
            '    [*] -> Leaf;',                      // 8
            '}',                                      // 9
        ].join('\n');

        it('places lifecycle and aspect actions directly under the state', async () => {
            const doc = createDocument(text, '/tmp/outline-actions.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const root = findByName(symbols, 'Root');
            assert.ok(root);

            // Child names in source order: 3 lifecycle, 2 aspect, then
            // the grouped States and Transitions containers.
            const childNames = root!.children.map(item => item.name);
            assert.ok(childNames.includes('enter'));
            assert.ok(childNames.includes('during'));
            assert.ok(childNames.includes('exit'));
            assert.ok(childNames.includes('>> during before'));
            assert.ok(childNames.includes('Audit'),
                'aspect-abstract `>> during after abstract Audit` is labelled by the action name');
            assert.ok(childNames.includes('States'));
            assert.ok(childNames.includes('Transitions'));
            // Must not resurrect the old double-wrapping:
            assert.equal(childNames.includes('Actions'), false);
            assert.equal(childNames.includes('Lifecycle'), false);
            assert.equal(childNames.includes('Aspects'), false);
        });

        it('uses the Method kind for lifecycle + aspect actions', async () => {
            const doc = createDocument(text, '/tmp/outline-actions-kind.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const root = findByName(symbols, 'Root')!;

            for (const name of ['enter', 'during', 'exit', '>> during before']) {
                const action = findByName(root.children, name);
                assert.ok(action, `expected child "${name}" in outline`);
                assert.equal(action!.kind, 'method',
                    `"${name}" should use the Method icon`);
            }
        });

        it('action detail shows a compact body preview for operation blocks', async () => {
            const doc = createDocument(text, '/tmp/outline-actions-detail.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const root = findByName(symbols, 'Root')!;

            const enterAction = findByName(root.children, 'enter');
            assert.ok(enterAction);
            assert.match(enterAction!.detail, /^\{ counter\s*=\s*0;\s*\}$/,
                `enter detail should summarise its body, got ${JSON.stringify(enterAction!.detail)}`);
        });

        it('abstract and ref actions expose single-word detail strings', async () => {
            const refText = [
                'state Root {',
                '    enter Setup { }',
                '    state Child {',
                '        enter abstract Init;',
                '        exit ref /Setup;',
                '    }',
                '    [*] -> Child;',
                '}',
            ].join('\n');
            const doc = createDocument(refText, '/tmp/outline-abstract-ref.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const child = findPath(findByName(symbols, 'Root')!, ['States', 'Child']);
            assert.ok(child);

            const init = findByName(child!.children, 'Init');
            assert.equal(init?.detail, 'abstract');
            assert.equal(init?.kind, 'method');

            const ref = findByName(child!.children, 'exit ref /Setup');
            assert.equal(ref?.detail, 'ref /Setup');
            assert.equal(ref?.kind, 'method');
        });
    });

    // ------------------------------------------------------------------
    // Transition detail is semantically meaningful, not internal-kind jargon
    // ------------------------------------------------------------------
    describe('transition detail', () => {
        const text = [
            'def int counter = 0;',                                          // 0
            'state Root {',                                                  // 1
            '    event Start;',                                              // 2
            '    event Stop;',                                               // 3
            '    state A;',                                                  // 4
            '    state B;',                                                  // 5
            '    state Fault;',                                              // 6
            '    [*] -> A;',                                                 // 7 initial
            '    A -> B :: Start;',                                          // 8 plain event
            '    B -> A :: Stop;',                                           // 9 plain event
            '    A -> Fault : if [counter > 10];',                           // 10 guard only
            '    A -> Fault : if [counter > 20] effect { counter = 0; };',  // 11 guard + effect
            '    B -> A effect { counter = counter + 1; };',                 // 12 effect only
            '    !* -> Fault :: Stop;',                                      // 13 forced
            '    Fault -> [*];',                                             // 14 terminal
            '}',                                                              // 15
        ].join('\n');

        it('initial transitions carry `initial` as detail', async () => {
            const doc = createDocument(text, '/tmp/outline-initial.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const transitions = findPath(findByName(symbols, 'Root')!, ['Transitions']);
            const initial = findByName(transitions!.children, '[*] -> A');
            assert.equal(initial?.detail, 'initial');
        });

        it('terminal `-> [*]` transitions carry `terminal` as detail', async () => {
            const doc = createDocument(text, '/tmp/outline-terminal.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const transitions = findPath(findByName(symbols, 'Root')!, ['Transitions']);
            const terminal = findByName(transitions!.children, 'Fault -> [*]');
            assert.ok(terminal);
            assert.match(terminal!.detail, /terminal/);
        });

        it('plain event-triggered transitions have empty detail (label already says it all)', async () => {
            const doc = createDocument(text, '/tmp/outline-plain-event.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const transitions = findPath(findByName(symbols, 'Root')!, ['Transitions']);
            const plain = findByName(transitions!.children, 'A -> B :: Start');
            assert.equal(plain?.detail, '');
        });

        it('guarded transitions surface the guard text in detail', async () => {
            const doc = createDocument(text, '/tmp/outline-guard.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const transitions = findPath(findByName(symbols, 'Root')!, ['Transitions']);
            const guarded = transitions!.children.find(item => item.detail.includes('counter > 10'));
            assert.ok(guarded, `expected a transition with detail containing the guard text`);
            assert.match(guarded!.detail, /if \[counter > 10\]/);
            assert.equal(guarded!.detail.includes('effect'), false,
                'the guard-only transition must not claim `effect`');
        });

        it('guard + effect transitions list both in the detail', async () => {
            const doc = createDocument(text, '/tmp/outline-guard-effect.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const transitions = findPath(findByName(symbols, 'Root')!, ['Transitions']);
            const combo = transitions!.children.find(item => item.detail.includes('counter > 20'));
            assert.ok(combo);
            assert.match(combo!.detail, /if \[counter > 20\] effect/);
        });

        it('effect-only transitions have `effect` as detail', async () => {
            const doc = createDocument(text, '/tmp/outline-effect-only.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const transitions = findPath(findByName(symbols, 'Root')!, ['Transitions']);
            const effectOnly = transitions!.children.find(item =>
                item.name.startsWith('B -> A') && item.detail === 'effect');
            assert.ok(effectOnly,
                `expected the effect-only B -> A transition to have detail 'effect'`);
        });

        it('forced-transition detail includes `forced`', async () => {
            const doc = createDocument(text, '/tmp/outline-forced.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const transitions = findPath(findByName(symbols, 'Root')!, ['Transitions']);
            const forced = transitions!.children.find(item => item.name.startsWith('!*'));
            assert.ok(forced);
            assert.match(forced!.detail, /forced/);
        });
    });

    // ------------------------------------------------------------------
    // Composite state detail is a compact shape summary
    // ------------------------------------------------------------------
    describe('composite state detail', () => {
        it('summarises nested children as `N states · N transitions · N events`', async () => {
            const text = [
                'state Root {',                 // 0
                '    event E1;',                // 1
                '    event E2;',                // 2
                '    state A;',                 // 3
                '    state B;',                 // 4
                '    state C;',                 // 5
                '    [*] -> A;',                // 6
                '    A -> B;',                  // 7
                '    B -> C;',                  // 8
                '}',                             // 9
            ].join('\n');
            const doc = createDocument(text, '/tmp/outline-state-detail.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const root = findByName(symbols, 'Root')!;
            assert.equal(root.detail, '3 states · 3 transitions · 2 events');
        });

        it('pseudo-state detail is still the marker string', async () => {
            const text = 'state Root {\n    pseudo state Junction;\n}';
            const doc = createDocument(text, '/tmp/outline-pseudo.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const junction = findPath(findByName(symbols, 'Root')!, ['States', 'Junction']);
            assert.equal(junction?.detail, 'pseudo state');
        });

        it('named states prefer their display name over the shape summary', async () => {
            const text = 'state Root named "Main System" { state Child; }';
            const doc = createDocument(text, '/tmp/outline-named-state.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const root = findByName(symbols, 'Root');
            assert.equal(root?.detail, 'Main System');
        });

        it('leaf states (no children) have empty detail', async () => {
            const text = 'state Root { state Leaf; [*] -> Leaf; }';
            const doc = createDocument(text, '/tmp/outline-leaf.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const leaf = findPath(findByName(symbols, 'Root')!, ['States', 'Leaf']);
            assert.equal(leaf?.detail, '');
        });
    });

    // ------------------------------------------------------------------
    // Imports stay in their own group
    // ------------------------------------------------------------------
    describe('imports group', () => {
        it('collects imports under a dedicated group with their source path as detail', async () => {
            const text = [
                'state Root {',
                '    import "./worker.fcstm" as Worker;',
                '    import "./other.fcstm" as Other;',
                '    [*] -> Worker;',
                '}',
            ].join('\n');
            const doc = createDocument(text, '/tmp/outline-imports.fcstm');
            const symbols = await packageModule.collectDocumentSymbols(doc);
            const imports = findPath(findByName(symbols, 'Root')!, ['Imports']);
            assert.ok(imports);
            assert.deepEqual(
                imports!.children.map(item => item.name),
                ['Worker', 'Other']
            );
            assert.equal(findByName(imports!.children, 'Worker')?.detail, './worker.fcstm');
        });
    });
});

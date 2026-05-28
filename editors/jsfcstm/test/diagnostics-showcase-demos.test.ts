/**
 * End-to-end diagnostic alignment: feed self-contained DSL fixtures
 * through ``collectDocumentDiagnostics`` (the exact call path that the
 * bundled VSCode extension uses) and assert the emitted ``code`` set.
 *
 * Each fixture's DSL is inlined here so the test is hermetic — it does
 * NOT read any file outside the test bundle. The same DSL bodies are
 * mirrored on disk under ``demo/diagnostics-showcase/`` for owners who
 * want to visually inspect what the VSIX shows; the demo files are not
 * load-bearing for these assertions.
 *
 * If you add a new diagnostic, append a SHOWCASE entry here.
 */
import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

interface ShowcaseFixture {
    /** Identifier used as the mocha case name and the synthetic file path. */
    name: string;
    /** Full DSL body. */
    dsl: string;
    /** Codes that MUST fire (each entry is asserted present). */
    mustFire: string[];
    /**
     * Codes that may legitimately fire as side effects of the same
     * malformed input. They are not enforced — but listing them keeps
     * the test material readable.
     */
    sideEffects?: string[];
    /** Codes that MUST NOT fire (catches regressions where we over-report). */
    mustNotFire?: string[];
}

const SHOWCASE: ShowcaseFixture[] = [
    {
        name: '01-undefined-variable',
        dsl: [
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [unknown_var > 0];',
            '    Active -> Idle : if [counter > 5] effect { counter = counter + mystery_input; };',
            '}',
        ].join('\n'),
        mustFire: ['E_UNDEFINED_VAR', 'E_UNDEFINED_VAR'],
        mustNotFire: ['E_INITIAL_TRANSITION_INVALID', 'E_DURING_ASPECT_INVALID'],
    },
    {
        name: '02-duplicate-variable',
        dsl: [
            'def int counter = 0;',
            'def float temp = 25.0;',
            'def int unrelated = 42;',
            'def int counter = 1;',
            'def float temp = 30.0;',
            '',
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '}',
        ].join('\n'),
        mustFire: ['E_DUPLICATE_VAR', 'E_DUPLICATE_VAR'],
        mustNotFire: ['E_DUPLICATE_STATE'],
    },
    {
        name: '03-missing-state',
        dsl: [
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    GhostState -> Idle :: Wake;',
            '    Active -> NoSuchTarget :: Halt;',
            '}',
        ].join('\n'),
        mustFire: ['E_MISSING_STATE', 'E_DANGLING_TRANSITION'],
        sideEffects: ['W_UNREACHABLE_STATE', 'W_GUARD_CONST_FALSE'],
    },
    {
        name: '04-duplicate-state',
        dsl: [
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    state Idle;',
            '    [*] -> Idle;',
            '    Active -> Idle :: Stop;',
            '}',
        ].join('\n'),
        mustFire: ['E_DUPLICATE_STATE'],
        sideEffects: ['W_UNREACHABLE_STATE', 'W_GUARD_CONST_FALSE'],
    },
    {
        name: '05-duplicate-function-name',
        dsl: [
            'state Root {',
            '    state System {',
            '        enter Initialize {}',
            '        enter Initialize {}',
            '        state Idle;',
            '        [*] -> Idle;',
            '    }',
            '    [*] -> System;',
            '}',
        ].join('\n'),
        mustFire: ['E_DUPLICATE_FUNCTION_NAME'],
        mustNotFire: ['E_INITIAL_TRANSITION_INVALID'],
    },
    {
        name: '06-pseudo-not-leaf',
        dsl: [
            'state Root {',
            '    pseudo state BadPseudo {',
            '        state Inner;',
            '        [*] -> Inner;',
            '    }',
            '    state Idle;',
            '    [*] -> Idle;',
            '}',
        ].join('\n'),
        mustFire: ['E_PSEUDO_NOT_LEAF'],
        sideEffects: ['W_UNREACHABLE_STATE'],
    },
    {
        name: '07-during-aspect-invalid',
        dsl: [
            'def int counter = 0;',
            'state Root {',
            '    state Idle {',
            '        >> during before { counter = counter + 1; }',
            '    }',
            '    [*] -> Idle;',
            '}',
        ].join('\n'),
        mustFire: ['E_DURING_ASPECT_INVALID'],
        // Bug guard: a state that has actions but no substates must still
        // be classified as a leaf, so the initial-transition analyzer
        // must NOT fire here.
        mustNotFire: ['E_INITIAL_TRANSITION_INVALID'],
    },
    {
        name: '08-initial-transition-invalid',
        dsl: [
            'state Root {',
            '    state Outer {',
            '        state InnerScope {',
            '            state Leaf;',
            '        }',
            '        [*] -> InnerScope;',
            '    }',
            '    [*] -> Outer;',
            '}',
        ].join('\n'),
        mustFire: ['E_INITIAL_TRANSITION_INVALID'],
        sideEffects: ['W_UNREACHABLE_STATE'],
    },
    {
        name: '09-named-function-ref-not-found',
        dsl: [
            'state Root {',
            '    state Idle {',
            '        enter ref NoSuch.Action;',
            '    }',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active :: Go;',
            '}',
        ].join('\n'),
        mustFire: ['E_NAMED_FUNCTION_REF_NOT_FOUND'],
        // Bug guard: ``state Idle { enter ref ... }`` has no substates,
        // so the initial-transition analyzer must NOT fire.
        mustNotFire: ['E_INITIAL_TRANSITION_INVALID'],
    },
    {
        name: '10-forced-transition-expansion',
        dsl: [
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    !Ghost -> Idle :: Panic;',
            '    Active -> Idle :: Stop;',
            '}',
        ].join('\n'),
        mustFire: ['E_FORCED_TRANSITION_EXPANSION'],
        sideEffects: ['W_UNREACHABLE_STATE', 'W_GUARD_CONST_FALSE'],
    },
    {
        name: '11-temporary-read-before-assign',
        dsl: [
            'state Root {',
            '    state Idle {',
            '        enter {',
            '            tracker = compute_me + 1;',
            '            compute_me = tracker * 2;',
            '        }',
            '    }',
            '    [*] -> Idle;',
            '}',
        ].join('\n'),
        mustFire: ['E_UNDEFINED_VAR'],
        // Bug guard: the enter-block-bearing leaf state must not trigger
        // the composite initial-transition check.
        mustNotFire: ['E_INITIAL_TRANSITION_INVALID'],
    },
    {
        name: '12-warnings-mixed',
        dsl: [
            'state Root {',
            '    event Unused;',
            '    state Idle;',
            '    state Active;',
            '    state OrphanState;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [false];',
            '}',
        ].join('\n'),
        mustFire: ['W_UNREACHABLE_STATE', 'W_GUARD_CONST_FALSE', 'W_UNUSED_EVENT'],
    },
];

function tallyCodes(codes: Array<string | undefined>): Map<string, number> {
    const tally = new Map<string, number>();
    for (const code of codes) {
        if (!code) continue;
        tally.set(code, (tally.get(code) ?? 0) + 1);
    }
    return tally;
}

function consumeOne(tally: Map<string, number>, code: string): boolean {
    const n = tally.get(code) ?? 0;
    if (n === 0) return false;
    if (n === 1) tally.delete(code);
    else tally.set(code, n - 1);
    return true;
}

describe('diagnostics showcase: jsfcstm collectDocumentDiagnostics parity', () => {
    for (const fixture of SHOWCASE) {
        it(`${fixture.name} emits the expected diagnostic catalog`, async () => {
            const syntheticPath = `/tmp/jsfcstm-showcase-${fixture.name}.fcstm`;
            const doc = createDocument(fixture.dsl, syntheticPath);
            const diagnostics = await packageModule.collectDocumentDiagnostics(doc);
            const codes = diagnostics.map(item => item.code);
            const tally = tallyCodes(codes);

            // 1. Every code listed under ``mustFire`` must appear at
            //    least the declared number of times.
            for (const expected of fixture.mustFire) {
                assert.ok(
                    consumeOne(tally, expected),
                    `expected ${expected} to fire on ${fixture.name}, got [${codes.join(', ')}]`,
                );
            }

            // 2. None of the ``mustNotFire`` codes are allowed.
            for (const banned of fixture.mustNotFire ?? []) {
                assert.ok(
                    !codes.includes(banned),
                    `${banned} should NOT fire on ${fixture.name}, got [${codes.join(', ')}]`,
                );
            }

            // 3. Anything left over after consuming mustFire entries
            //    must be a declared side effect (or a leftover instance
            //    of a mustFire code, which is also fine).
            const allowedExtras = new Set<string>([
                ...fixture.mustFire,
                ...(fixture.sideEffects ?? []),
            ]);
            for (const code of tally.keys()) {
                assert.ok(
                    allowedExtras.has(code),
                    `${fixture.name} emitted unexpected code ${code} (declared mustFire=[${fixture.mustFire.join(', ')}], sideEffects=[${(fixture.sideEffects ?? []).join(', ')}])`,
                );
            }

            // 4. Every diagnostic must carry a non-empty ``code`` —
            //    catches grammar parse errors leaking through with no
            //    structured code, which would still appear in the
            //    VSCode Problems panel but bypass the
            //    jsfcstm/pyfcstm catalog.
            for (const d of diagnostics) {
                assert.ok(
                    typeof d.code === 'string' && d.code.length > 0,
                    `${fixture.name} produced a diagnostic without a code: ${JSON.stringify(d)}`,
                );
            }
        });
    }
});

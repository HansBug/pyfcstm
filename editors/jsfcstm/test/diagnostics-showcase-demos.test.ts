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
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir, writeFile} from './support';

interface ShowcaseFixture {
    /** Identifier used as the mocha case name and the synthetic file path. */
    name: string;
    /**
     * Single-file DSL body. Mutually exclusive with ``files``.
     */
    dsl?: string;
    /**
     * Multi-file workspace fixture for import-related diagnostics. Keys
     * are relative file names; ``entry`` selects which file to feed
     * through ``collectDocumentDiagnostics``. All file contents come
     * from this object — no on-disk fixtures are read.
     */
    files?: Record<string, string>;
    /** When ``files`` is set, identifies the file to run diagnostics on. */
    entry?: string;
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
        mustNotFire: ['E_INITIAL_TRANSITION_INVALID'],
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
        // I-f scenario (a): leaf state with a *local* ``during after``
        // (no ``>>``). pyfcstm flags this; jsfcstm now does too.
        name: '07a-during-aspect-leaf-local-aspect',
        dsl: [
            'def int counter = 0;',
            'state Root {',
            '    state Idle {',
            '        during after { counter = counter + 1; }',
            '    }',
            '    [*] -> Idle;',
            '}',
        ].join('\n'),
        mustFire: ['E_DURING_ASPECT_INVALID'],
        mustNotFire: ['E_INITIAL_TRANSITION_INVALID'],
    },
    {
        // I-f scenario (b): composite state with a *bare* ``during`` (no
        // aspect). Composite during must pick before/after — pyfcstm
        // already enforces this and jsfcstm now matches.
        name: '07b-during-aspect-composite-bare',
        dsl: [
            'def int counter = 0;',
            'state Root {',
            '    state Outer {',
            '        during { counter = counter + 1; }',
            '        state Inner;',
            '        [*] -> Inner;',
            '    }',
            '    [*] -> Outer;',
            '}',
        ].join('\n'),
        mustFire: ['E_DURING_ASPECT_INVALID'],
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
    {
        name: '13-import-not-found',
        files: {
            'host.fcstm': [
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./absent.fcstm" as Worker;',
                '}',
            ].join('\n'),
        },
        entry: 'host.fcstm',
        mustFire: ['E_IMPORT_NOT_FOUND'],
        sideEffects: ['W_UNREACHABLE_STATE'],
    },
    {
        name: '14-import-alias-conflict',
        files: {
            'host.fcstm': [
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./worker.fcstm" as Idle;',
                '}',
            ].join('\n'),
            'worker.fcstm': 'state Worker;',
        },
        entry: 'host.fcstm',
        mustFire: ['E_IMPORT_ALIAS_CONFLICT'],
        sideEffects: ['W_UNREACHABLE_STATE', 'W_GUARD_CONST_FALSE'],
    },
    {
        name: '15-import-duplicate-mapping',
        files: {
            // Worker declares ``sensor`` so the pyfcstm def-mapping
            // pipeline runs (it short-circuits on an empty imported
            // module). jsfcstm independently detects the duplicate
            // mapping AST nodes.
            'host.fcstm': [
                'state Root {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./worker.fcstm" as Worker {',
                '        def sensor -> io_a;',
                '        def sensor -> io_a;',
                '    }',
                '}',
            ].join('\n'),
            'worker.fcstm': 'def int sensor = 0;\nstate Worker;',
        },
        entry: 'host.fcstm',
        mustFire: ['E_IMPORT_DUPLICATE_MAPPING'],
        sideEffects: ['W_UNREACHABLE_STATE'],
    },
    {
        name: '16-import-circular',
        files: {
            'a.fcstm': [
                'state A {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./b.fcstm" as B;',
                '}',
            ].join('\n'),
            'b.fcstm': [
                'state B {',
                '    state Idle;',
                '    [*] -> Idle;',
                '    import "./a.fcstm" as A;',
                '}',
            ].join('\n'),
        },
        entry: 'a.fcstm',
        mustFire: ['E_IMPORT_CIRCULAR'],
        // Cycle detection often surfaces secondary diagnostics on the
        // alias path; we accept any of these as benign side effects.
        sideEffects: [
            'W_UNREACHABLE_STATE',
            'W_GUARD_CONST_FALSE',
            'W_UNUSED_EVENT',
            'E_IMPORT_NOT_FOUND',
            'E_IMPORT_ALIAS_CONFLICT',
        ],
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
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    for (const fixture of SHOWCASE) {
        it(`${fixture.name} emits the expected diagnostic catalog`, async () => {
            let doc;
            if (fixture.files && fixture.entry) {
                // Multi-file workspace fixture: materialize every file
                // declared in ``fixture.files`` to a fresh tmp dir, then
                // run diagnostics on the entry file. File contents are
                // still inlined in this .ts source — we never read any
                // external .fcstm.
                const dir = trackTempDir(`jsfcstm-showcase-${fixture.name}-`);
                let entryPath: string | undefined;
                for (const [relative, body] of Object.entries(fixture.files)) {
                    const absolute = path.join(dir, relative);
                    writeFile(absolute, body);
                    if (relative === fixture.entry) {
                        entryPath = absolute;
                    }
                }
                if (!entryPath) {
                    throw new Error(
                        `fixture ${fixture.name}: entry ${fixture.entry} not found in files`,
                    );
                }
                doc = createDocument(fixture.files[fixture.entry], entryPath);
            } else if (fixture.dsl) {
                const syntheticPath = `/tmp/jsfcstm-showcase-${fixture.name}.fcstm`;
                doc = createDocument(fixture.dsl, syntheticPath);
            } else {
                throw new Error(`fixture ${fixture.name}: neither dsl nor files+entry is set`);
            }
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

            // 5. Schema-enum payload checks. These guard against
            //    schema↔emit drift — see ``pyfcstm/diagnostics/codes.yaml``
            //    for the authoritative enums on each code.
            //    Extend this block when adding new codes whose payload
            //    has an enumerated field.
            const VALID_INITIAL_TRANSITION_REASONS = new Set([
                'missing_entry',
                'target_not_child',
            ]);
            const VALID_REFERENCED_IN = new Set([
                'guard',
                'effect',
                'enter',
                'during',
                'exit',
                'during_aspect',
                'init',
            ]);
            for (const d of diagnostics) {
                if (d.code === 'E_INITIAL_TRANSITION_INVALID') {
                    const reason = (d.data as { reason?: string } | undefined)?.reason;
                    assert.ok(
                        reason !== undefined && VALID_INITIAL_TRANSITION_REASONS.has(reason),
                        `${fixture.name}: E_INITIAL_TRANSITION_INVALID emitted with reason=${JSON.stringify(reason)}, expected one of [${[...VALID_INITIAL_TRANSITION_REASONS].join(', ')}]`,
                    );
                }
                if (d.code === 'E_UNDEFINED_VAR') {
                    const ri = (d.data as { referenced_in?: string } | undefined)?.referenced_in;
                    if (ri !== undefined) {
                        assert.ok(
                            VALID_REFERENCED_IN.has(ri),
                            `${fixture.name}: E_UNDEFINED_VAR emitted with referenced_in=${JSON.stringify(ri)}, expected one of [${[...VALID_REFERENCED_IN].join(', ')}]`,
                        );
                    }
                }
            }

            // 6. Schema-driven required-field payload check. M2 from
            //    PR #115 final review: previously this loop hard-coded
            //    only the E_IMPORT_* required field list. Switch to
            //    consulting ``loadCodesRegistry()`` so every catalogued
            //    code is validated against its declared schema — the
            //    mirror of pyfcstm's ``_schema_check.py`` runtime
            //    helper. Any emit-site that fails to fill a required
            //    field now surfaces in the mocha run.
            const registry = packageModule.loadCodesRegistry();
            for (const d of diagnostics) {
                const spec = registry[d.code];
                if (!spec || !spec.refs) {
                    continue;
                }
                const required = Object.entries(spec.refs)
                    .filter(entry => entry[1].required === true)
                    .map(entry => entry[0]);
                if (required.length === 0) {
                    continue;
                }
                const data = d.data as Record<string, unknown> | undefined;
                for (const field of required) {
                    assert.ok(
                        data !== undefined
                            && data[field] !== undefined
                            && data[field] !== null,
                        `${fixture.name}: ${d.code} missing required data field "${field}", got data=${JSON.stringify(data)}`,
                    );
                }
                // M2 second half: validate enum-typed fields against
                // their declared enum.
                if (data !== undefined) {
                    for (const [field, fieldSpec] of Object.entries(spec.refs)) {
                        if (!fieldSpec.enum || data[field] === undefined) {
                            continue;
                        }
                        assert.ok(
                            fieldSpec.enum.includes(data[field] as string),
                            `${fixture.name}: ${d.code} data.${field}=${JSON.stringify(data[field])} not in declared enum [${fieldSpec.enum.join(', ')}]`,
                        );
                    }
                }
            }
        });
    }
});

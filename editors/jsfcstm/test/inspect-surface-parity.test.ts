import assert from 'node:assert/strict';

import {createDocument, packageModule, withPatchedProperty} from './support';

const SUPPRESSED_FROM_INSPECT_SURFACE = new Set([
    'W_UNREACHABLE_STATE',
    'W_UNUSED_EVENT',
]);

const TARGETED_FIXTURES: Array<{name: string; code: string; text: string}> = [
    {
        name: 'unwritten read variable',
        code: 'W_UNWRITTEN_READ_VAR',
        text: `
def int source = 0;
def int guard_value = 0;
state Root {
    state Idle { during { guard_value = source + 1; } }
    state Done;
    [*] -> Idle;
    Idle -> Done : if [guard_value > 0];
}
`,
    },
    {
        name: 'constant during assignment',
        code: 'W_DURING_CONST_ASSIGN',
        text: `
def int stable = 0;
state Root {
    state Idle {
        during { stable = 20; }
    }
    [*] -> Idle;
    Idle -> [*] : if [stable > 0];
}
`,
    },
    {
        name: 'constant false guard expression',
        code: 'W_GUARD_CONST_FALSE',
        text: `
state Root {
    state Idle;
    state Blocked;
    [*] -> Idle;
    Idle -> Blocked : if [1 == 2];
}
`,
    },
    {
        name: 'eventless unguarded transition info',
        code: 'I_TRANSITION_NEVER_EVENT_TRIGGERED',
        text: `
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B;
}
`,
    },
    {
        name: 'large composite',
        code: 'W_LARGE_COMPOSITE',
        text: `
state Root {
    state S1 {
        state S2 {
            state S3 {
                state S4 {
                    state S5 {
                        state S6 {
                            state S7;
                            [*] -> S7;
                        }
                        [*] -> S6;
                    }
                    [*] -> S5;
                }
                [*] -> S4;
            }
            [*] -> S3;
        }
        [*] -> S2;
    }
    state A2;
    state A3;
    state A4;
    state A5;
    state A6;
    state A7;
    state A8;
    state A9;
    state A10;
    state A11;
    state A12;
    state A13;
    [*] -> S1;
}
`,
    },
    {
        name: 'deep hierarchy',
        code: 'W_DEEP_HIERARCHY',
        text: `
state Root {
    state S1 {
        state S2 {
            state S3 {
                state S4 {
                    state S5 {
                        state S6 {
                            state S7;
                            [*] -> S7;
                        }
                        [*] -> S6;
                    }
                    [*] -> S5;
                }
                [*] -> S4;
            }
            [*] -> S3;
        }
        [*] -> S2;
    }
    [*] -> S1;
}
`,
    },
    {
        name: 'literal type narrowing',
        code: 'W_LITERAL_TYPE_NARROWING',
        text: `
def int truncated = 3.5;
state Root {
    state A;
    [*] -> A;
}
`,
    },
];

function isInspectSurfaceCode(code: unknown): code is string {
    return typeof code === 'string' && (code.startsWith('W_') || code.startsWith('I_'));
}

function stableKey(code: string, refs: unknown): string {
    return JSON.stringify([code, refs ?? null]);
}

async function inspectDiagnosticKeys(text: string, filePath: string): Promise<string[]> {
    const document = createDocument(text, filePath);
    const ast = await packageModule.parseAstDocument(document);
    const model = packageModule.buildStateMachineModel(ast);
    assert.ok(model, 'expected state-machine model');
    return packageModule.inspectModel(model).diagnostics
        .filter(item => isInspectSurfaceCode(item.code))
        .filter(item => !SUPPRESSED_FROM_INSPECT_SURFACE.has(item.code))
        .map(item => stableKey(item.code, item.refs))
        .sort();
}

async function editorDiagnosticKeys(text: string, filePath: string): Promise<string[]> {
    const document = createDocument(text, filePath);
    const diagnostics = await packageModule.collectDocumentDiagnostics(document);
    return diagnostics
        .filter(item => isInspectSurfaceCode(item.code))
        .map(item => stableKey(item.code as string, item.data ?? null))
        .sort();
}

function assertBagCovers(actualKeys: string[], expectedKeys: string[]): void {
    const remaining = new Map<string, number>();
    for (const key of actualKeys) {
        remaining.set(key, (remaining.get(key) ?? 0) + 1);
    }

    const missing: string[] = [];
    for (const key of expectedKeys) {
        const count = remaining.get(key) ?? 0;
        if (count <= 0) {
            missing.push(key);
            continue;
        }
        remaining.set(key, count - 1);
    }

    assert.deepEqual(missing, []);
}

async function semanticFor(text: string, filePath: string) {
    const document = createDocument(text, filePath);
    const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
    assert.ok(semantic, 'expected semantic document');
    return {document, semantic};
}

describe('editor inspect diagnostics surface parity', () => {
    for (const fixture of TARGETED_FIXTURES) {
        it(`surfaces ${fixture.code} from ${fixture.name}`, async () => {
            const document = createDocument(fixture.text, `/tmp/${fixture.code}.fcstm`);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            assert.ok(
                diagnostics.some(item => item.code === fixture.code),
                `expected collectDocumentDiagnostics to surface ${fixture.code}`,
            );
        });
    }

    it('covers inspectModel W/I code+refs bag except deduped editor-analyzer codes', async () => {
        for (const fixture of TARGETED_FIXTURES) {
            const filePath = `/tmp/parity-${fixture.code}.fcstm`;
            assertBagCovers(
                await editorDiagnosticKeys(fixture.text, filePath),
                await inspectDiagnosticKeys(fixture.text, filePath),
            );
        }
    });

    it('surfaces inspect diagnostics without suggested fixes, including W_WRITE_ONLY_VAR', async () => {
        const text = `
def int write_only = 0;
state Root {
    state Idle { enter { write_only = 1; } }
    [*] -> Idle;
}
`;
        const document = createDocument(text, '/tmp/synthetic-write-only.fcstm');
        const inspectModule = await import('../dist/diagnostics/inspect');

        await withPatchedProperty(inspectModule, 'inspectModel', (() => ({
            root_state_path: 'Root',
            states: [],
            transitions: [],
            variables: [],
            events: [],
            actions: [],
            forced_transitions: [],
            metrics: {
                n_states_leaf: 0,
                n_states_composite: 0,
                n_states_pseudo: 0,
                max_hierarchy_depth: 0,
                n_transitions_normal: 0,
                n_transitions_forced: 0,
                n_events: 0,
                n_variables: 0,
                var_to_leaf_ratio: 0,
                aspect_coverage: {},
                abstract_action_inventory: [],
            },
            reachability_graph: {},
            event_emission_map: {},
            var_dataflow: {},
            aspect_impact_map: {},
            action_ref_graph: {},
            diagnostics: [{
                code: 'W_WRITE_ONLY_VAR',
                severity: 'warning',
                message: 'Synthetic write-only variable diagnostic.',
                span: null,
                refs: {
                    var_name: 'write_only',
                    written_states: ['Root.Idle'],
                },
            }],
        })) as typeof inspectModule.inspectModel, async () => {
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            const diagnostic = diagnostics.find(item => item.code === 'W_WRITE_ONLY_VAR');
            assert.ok(diagnostic, 'expected W_WRITE_ONLY_VAR to be surfaced');
            assert.equal(diagnostic.data?.var_name, 'write_only');
            assert.equal(
                document.lineAt(diagnostic.range.start.line).text.includes('def int write_only = 0;'),
                true,
            );
        });
    });

    it('deduplicates editor-covered literal false guards while keeping inspect-only const folds', async () => {
        const literalFalse = `
state Root {
    state Idle;
    state Blocked;
    [*] -> Idle;
    Idle -> Blocked : if [false];
}
`;
        const literalDiagnostics = await packageModule.collectDocumentDiagnostics(
            createDocument(literalFalse, '/tmp/literal-false-guard.fcstm'),
        );
        assert.equal(
            literalDiagnostics.filter(item => item.code === 'W_GUARD_CONST_FALSE').length,
            1,
        );

        const foldedFalse = `
state Root {
    state Idle;
    state Blocked;
    [*] -> Idle;
    Idle -> Blocked : if [1 == 2];
}
`;
        const foldedDiagnostics = await packageModule.collectDocumentDiagnostics(
            createDocument(foldedFalse, '/tmp/folded-false-guard.fcstm'),
        );
        const folded = foldedDiagnostics.find(item => item.code === 'W_GUARD_CONST_FALSE');
        assert.ok(folded, 'expected inspect-only constant false guard diagnostic');
        assert.deepEqual(folded.data, {
            transition_span: null,
            folded_value: false,
            from_path: 'Root.Idle',
            to_path: 'Root.Blocked',
        });
    });

    it('keeps inspect-only folded false guards when literal false guards share the file', async () => {
        const text = `
state Root {
    state Idle;
    state LiteralBlocked;
    state FoldedBlocked;
    [*] -> Idle;
    Idle -> LiteralBlocked : if [false];
    Idle -> FoldedBlocked : if [1 == 2];
}
`;
        const diagnostics = await packageModule.collectDocumentDiagnostics(
            createDocument(text, '/tmp/mixed-false-guards.fcstm'),
        );
        const guardRefs = diagnostics
            .filter(item => item.code === 'W_GUARD_CONST_FALSE')
            .map(item => item.data)
            .sort((a, b) => JSON.stringify(a).localeCompare(JSON.stringify(b)));

        assert.deepEqual(guardRefs, [
            {
                transition_span: null,
                folded_value: false,
                from_path: 'Root.Idle',
                to_path: 'Root.FoldedBlocked',
            },
            {
                transition_span: null,
                folded_value: false,
                from_path: 'Root.Idle',
                to_path: 'Root.LiteralBlocked',
            },
        ]);
    });

    it('keeps same-endpoint inspect-only folded false guards when a literal false guard exists', async () => {
        const text = `
state Root {
    state Idle;
    state Blocked;
    [*] -> Idle;
    Idle -> Blocked : if [false];
    Idle -> Blocked : if [1 == 2];
}
`;
        const filePath = '/tmp/same-endpoint-mixed-false-guards.fcstm';
        const diagnostics = await packageModule.collectDocumentDiagnostics(
            createDocument(text, filePath),
        );
        const guardRefs = diagnostics
            .filter(item => item.code === 'W_GUARD_CONST_FALSE')
            .map(item => item.data);

        assert.deepEqual(guardRefs, [
            {
                transition_span: null,
                folded_value: false,
                from_path: 'Root.Idle',
                to_path: 'Root.Blocked',
            },
            {
                transition_span: null,
                folded_value: false,
                from_path: 'Root.Idle',
                to_path: 'Root.Blocked',
            },
        ]);
        assertBagCovers(
            await editorDiagnosticKeys(text, filePath),
            await inspectDiagnosticKeys(text, filePath),
        );
    });

    it('keeps the async semantic analyzer wrapper aligned with the shared implementation', async () => {
        const text = `
state Root {
    event Unused;
    state Idle;
    [*] -> Idle;
}
`;
        const document = createDocument(text, '/tmp/semantic-wrapper.fcstm');
        const diagnostics = await packageModule.collectSemanticAnalysisDiagnostics(document);

        assert.ok(
            diagnostics.some(item => item.code === 'W_UNUSED_EVENT'),
            'expected the async wrapper to reuse semantic analyzer diagnostics',
        );
    });

    it('returns parse diagnostics without requiring a semantic snapshot', async () => {
        const document = createDocument('state Root {', '/tmp/parse-only.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);

        assert.ok(diagnostics.length > 0, 'expected parser diagnostics for malformed input');
        assert.ok(diagnostics.every(item => item.source === 'fcstm'));
    });

    it('does not let unkeyed existing diagnostics consume inspect diagnostics', async () => {
        const text = `
state Root {
    state Idle;
    [*] -> Idle;
}
`;
        const {document, semantic} = await semanticFor(text, '/tmp/unkeyed-existing-diagnostic.fcstm');
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(
            document,
            semantic,
            [{
                code: 'W_DEADLOCK_LEAF',
                severity: 'warning' as const,
                message: 'Leaf state has no outgoing transition.',
                span: null,
                refs: {
                    state_path: 'Root.Idle',
                    parent_path: 'Root',
                    reason: 'no_outgoing_transition',
                },
            }],
            [{
                range: packageModule.createRange(0, 0, 0, 1),
                message: 'Parser diagnostic without a stable code.',
                severity: 'error' as const,
                source: 'fcstm',
            }],
        );

        assert.equal(diagnostics.length, 1);
        assert.equal(diagnostics[0].code, 'W_DEADLOCK_LEAF');
    });

    it('tolerates workspace snapshots without root node data', async () => {
        const text = `
state Root;
`;
        const document = createDocument(text, '/tmp/no-semantic-snapshot.fcstm');
        const graph = packageModule.getWorkspaceGraph();

        await withPatchedProperty(graph, 'buildSnapshotForDocument', (async () => ({
            rootFile: document.filePath,
            nodes: {},
        })) as typeof graph.buildSnapshotForDocument, async () => {
            assert.deepEqual(await packageModule.collectDocumentDiagnostics(document), []);
        });
    });

    it('resolves representative inspect refs to editor source ranges', async () => {
        const text = `
def int counter = 0;
state Root {
    event Tick;
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done : Tick;
}
`;
        const {document, semantic} = await semanticFor(text, '/tmp/inspect-ranges.fcstm');
        const transitionRange = packageModule.createRange(6, 4, 6, 24);
        const duplicateRange = packageModule.createRange(3, 10, 3, 14);

        const stateRange = packageModule.resolveRangeFromRefs(document, semantic, {state_path: 'Root.Idle'});
        assert.equal(document.lineAt(stateRange!.start.line).text.slice(
            stateRange!.start.character,
            stateRange!.end.character,
        ), 'Idle');

        const fromPathRange = packageModule.resolveRangeFromRefs(document, semantic, {
            from_path: 'Root.Idle',
            to_path: 'Root.Done',
            transition_span: null,
        });
        assert.equal(document.lineAt(fromPathRange!.start.line).text.slice(
            fromPathRange!.start.character,
            fromPathRange!.end.character,
        ), 'Idle');

        const variableRange = packageModule.resolveRangeFromRefs(document, semantic, {var_name: 'counter'});
        assert.equal(document.lineAt(variableRange!.start.line).text.includes('def int counter = 0;'), true);

        const eventRange = packageModule.resolveRangeFromRefs(document, semantic, {event_qualified_name: 'Root.Tick'});
        assert.equal(document.lineAt(eventRange!.start.line).text.slice(
            eventRange!.start.character,
            eventRange!.end.character,
        ), 'Tick');

        assert.deepEqual(
            packageModule.resolveRangeFromRefs(document, semantic, {transition_span: transitionRange}),
            transitionRange,
        );
        assert.deepEqual(
            packageModule.resolveRangeFromRefs(document, semantic, {transition_span: null, duplicate_spans: [duplicateRange]}),
            duplicateRange,
        );
        assert.equal(
            packageModule.resolveRangeFromRefs(document, semantic, {duplicate_spans: ['not-a-range']}),
            null,
        );
        assert.equal(packageModule.resolveRangeFromRefs(document, semantic, null), null);
    });

    it('resolves missing and implicit event refs without requiring declarations', async () => {
        const text = `
state Root {
    state Idle;
    state Done;
    [*] -> Idle;
    Idle -> Done :: Tick;
}
`;
        const {document, semantic} = await semanticFor(text, '/tmp/implicit-event-ranges.fcstm');

        assert.equal(
            packageModule.resolveRangeFromRefs(document, semantic, {event_qualified_name: 'Root.Missing'}),
            null,
        );
        const implicitEventRange = packageModule.resolveRangeFromRefs(
            document,
            semantic,
            {event_qualified_name: 'Root.Idle.Tick'},
        );
        assert.ok(implicitEventRange, 'expected implicit transition event range');
        assert.equal(document.lineAt(implicitEventRange.start.line).text.slice(
            implicitEventRange.start.character,
            implicitEventRange.end.character,
        ), 'Tick');
    });
});

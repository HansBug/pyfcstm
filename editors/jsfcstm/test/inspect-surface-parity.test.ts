import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

const SUPPRESSED_FROM_INSPECT_SURFACE = new Set([
    'W_UNREACHABLE_STATE',
    'W_GUARD_CONST_FALSE',
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
    });
});

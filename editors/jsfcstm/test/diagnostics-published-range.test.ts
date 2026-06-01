import assert from 'node:assert/strict';

import {createDocument, packageModule, sliceByRange} from './support';

function fullDocumentSlice(text: string): string {
    const lines = text.split('\n');
    return sliceByRange(text, packageModule.createRange(
        0,
        0,
        lines.length - 1,
        lines[lines.length - 1]?.length ?? 0,
    ));
}

describe('diagnostics published ranges', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('anchors deadlock leaf diagnostics on the leaf states instead of fix insertion points', async () => {
        const text = [
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    pseudo state C;',
            '    state D;',
            '    state F;',
            '',
            '    [*] -> A;',
            '',
            '    A -> B : if [x >= 48 && x % 7 == 1] effect {',
            '        x = x + 10;',
            '    };',
            '    B -> D : if [x % 4 == 0];',
            '',
            '    A -> C : if [x % 7 != 1];',
            '    C -> F : if [x % 4 != 1];',
            '    C -> A effect {',
            '        x = x + 1;',
            '    };',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/published-deadlock.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const deadlocks = diagnostics
            .filter(item => item.code === 'W_DEADLOCK_LEAF')
            .sort((a, b) => String(a.data?.state_path).localeCompare(String(b.data?.state_path)));

        assert.equal(deadlocks.length, 2, JSON.stringify(diagnostics));
        assert.deepEqual(deadlocks.map(item => item.data?.state_path), ['Root.D', 'Root.F']);
        assert.equal(sliceByRange(text, deadlocks[0].range), 'D');
        assert.equal(sliceByRange(text, deadlocks[1].range), 'F');
        assert.notDeepEqual(deadlocks[0].range, packageModule.createRange(6, 0, 6, 0));
        assert.notDeepEqual(deadlocks[1].range, packageModule.createRange(7, 0, 7, 0));

        const fixEditDiagnostics = packageModule.collectInspectDiagnosticsFromItems(
            document,
            await packageModule.getWorkspaceGraph().getSemanticDocument(document),
            deadlocks.map(item => ({
                code: item.code,
                severity: item.severity,
                message: item.message,
                span: null,
                refs: item.data,
            })),
            [],
            {rangeMode: 'fix-edit'},
        );
        const fixEditRanges = fixEditDiagnostics
            .sort((a, b) => String(a.data?.state_path).localeCompare(String(b.data?.state_path)))
            .map(item => item.range);
        assert.deepEqual(fixEditRanges[0], packageModule.createRange(6, 0, 6, 0));
        assert.deepEqual(fixEditRanges[1], packageModule.createRange(7, 0, 7, 0));
    });

    it('anchors missing unconditional initial diagnostics on the composite state', async () => {
        const text = [
            'def int ready = 0;',
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle : if [ready > 0];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/published-initial.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnostics.find(item => item.code === 'W_INITIAL_UNCONDITIONAL_MISSING');

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range), 'Root');
        assert.notDeepEqual(diagnostic.range, packageModule.createRange(4, 0, 4, 0));
    });

    it('keeps delete-style suggested diagnostics on the concrete problem statement', async () => {
        const text = [
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B effect {',
            '        x = x;',
            '    };',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/published-self-assign.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnostics.find(item => item.code === 'W_EFFECT_SELF_ASSIGN');

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), 'x = x;');
        assert.notEqual(sliceByRange(text, diagnostic.range), 'A');
    });

    it('keeps quick-fix edit ranges separate from published problem ranges', async () => {
        const text = [
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/published-deadlock-action-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnostics.find(item => item.code === 'W_DEADLOCK_LEAF');

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range), 'Idle');

        const actions = await packageModule.collectCodeActions(document, diagnostic.range, [diagnostic]);
        const action = actions.find(item => /exit transition/.test(item.title));
        assert.ok(action, `expected exit-transition quick fix, got ${JSON.stringify(actions)}`);
        const edit = Object.values(action.edit?.changes || {}).flat()[0];
        assert.ok(edit, 'expected quick-fix edit');
        assert.deepEqual(edit.range, packageModule.createRange(2, 0, 2, 0));
        assert.notDeepEqual(edit.range, diagnostic.range);
        assert.match(edit.newText, /Idle -> \[\*\];\n/);
    });


    it('does not unlock missing-initial quick fixes from unrelated initial transitions', async () => {
        const text = [
            'def int ready = 0;',
            'state Root {',
            '    state Idle;',
            '    state Standby;',
            '    [*] -> Idle : if [ready > 0];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/published-initial-unrelated-transition.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnostics.find(item => item.code === 'W_INITIAL_UNCONDITIONAL_MISSING');

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        const actions = await packageModule.collectCodeActions(
            document,
            diagnostics.find(item => item.code === 'W_DEADLOCK_LEAF' && item.data?.state_path === 'Root.Standby')!.range,
            diagnostics,
        );
        assert.equal(
            actions.some(item => /fallback entry transition/.test(item.title)),
            false,
            `unrelated sibling range must not unlock missing-initial quick fix: ${JSON.stringify(actions)}`,
        );
    });

    it('keeps full-document fallback observable when refs cannot identify a problem range', async () => {
        const text = 'state Root;\n';
        const document = createDocument(text, '/tmp/published-full-fallback.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        assert.ok(semantic);

        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(
            document,
            semantic,
            [{
                code: 'W_HIGH_VAR_TO_LEAF_RATIO',
                severity: 'warning' as const,
                message: 'Variable count is high compared with leaf states.',
                span: null,
                refs: {actual: 3, threshold: 2},
            }],
        );

        assert.equal(diagnostics.length, 1);
        assert.equal(sliceByRange(text, diagnostics[0].range), fullDocumentSlice(text));
        assert.equal(diagnostics[0].data?.__rangeFallback, 'full_document');
    });

    it('marks duplicate-variable inspect fallback as first-of-ambiguous instead of full document', async () => {
        const text = [
            'def int x = 0;',
            'def float x = 1.0;',
            'state Root {',
            '    state Idle;',
            '    [*] -> Idle;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/published-duplicate-var.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnostics.find(item => item.code === 'W_UNREFERENCED_VAR');

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range), 'def int x = 0;');
        assert.equal(diagnostic.data?.__rangeFallback, 'first_of_ambiguous');
        assert.notEqual(sliceByRange(text, diagnostic.range), fullDocumentSlice(text));
    });
});

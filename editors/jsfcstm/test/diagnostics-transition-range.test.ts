import assert from 'node:assert/strict';

import {createDocument, packageModule, sliceByRange} from './support';

function targetDiagnostics(diagnostics: any[], code: string): any[] {
    return diagnostics.filter(item => item.code === code);
}

describe('diagnostics transition body ranges', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('anchors guard const diagnostics on the guard expression', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    state C;',
            '    [*] -> A;',
            '    A -> B : if [(1 + 2) == 3];',
            '    B -> C : if [(0x0F & 0xF0) != 0];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-guard-ranges.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const constTrue = targetDiagnostics(diagnostics, 'W_GUARD_CONST_TRUE')[0];
        const constFalse = targetDiagnostics(diagnostics, 'W_GUARD_CONST_FALSE')[0];

        assert.ok(constTrue, JSON.stringify(diagnostics));
        assert.ok(constFalse, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, constTrue.range), '(1 + 2) == 3');
        assert.equal(sliceByRange(text, constFalse.range), '(0x0F & 0xF0) != 0');
        assert.notEqual(sliceByRange(text, constTrue.range), 'A');
        assert.notEqual(sliceByRange(text, constFalse.range), 'B');
    });

    it('anchors eventless guardless transition diagnostics on the transition statement', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-eventless-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'I_TRANSITION_NEVER_EVENT_TRIGGERED')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), 'A -> B;');
        assert.notEqual(sliceByRange(text, diagnostic.range), 'A');
    });

    it('anchors redundant transition diagnostics on a duplicate transition statement', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '    A -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-redundant-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'W_REDUNDANT_TRANSITION')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), 'A -> B;');
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
        assert.notEqual(sliceByRange(text, diagnostic.range), 'A');
    });

    it('anchors no-op self-transition diagnostics on the self-transition statement', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    [*] -> A;',
            '    A -> A;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-self-nop-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'W_SELF_TRANSITION_NOP')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), 'A -> A;');
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
        assert.notEqual(sliceByRange(text, diagnostic.range), 'A');
    });

    it('keeps self-assignment diagnostics on the concrete effect statement', async () => {
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
        const document = createDocument(text, '/tmp/transition-self-assign-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'W_EFFECT_SELF_ASSIGN')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), 'x = x;');
    });

    it('uses transition_index refs to disambiguate repeated eventless transitions', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '    A -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-index-eventless-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const neverTriggered = targetDiagnostics(diagnostics, 'I_TRANSITION_NEVER_EVENT_TRIGGERED');

        assert.equal(neverTriggered.length, 2, JSON.stringify(diagnostics));
        assert.deepEqual(
            neverTriggered.map(item => sliceByRange(text, item.range).trim()),
            ['A -> B;', 'A -> B;'],
        );
        assert.deepEqual(
            neverTriggered.map(item => item.range.start.line),
            [4, 5],
        );
        assert.deepEqual(
            neverTriggered.map(item => item.data?.__rangeFallback ?? null),
            [null, null],
        );
    });

    it('disambiguates equivalent guard diagnostics by transition index', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : if [1 == 1];',
            '    A -> B : if [1 == 1];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-index-guard-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const constTrue = targetDiagnostics(diagnostics, 'W_GUARD_CONST_TRUE');

        assert.equal(constTrue.length, 2, JSON.stringify(diagnostics));
        assert.deepEqual(
            constTrue.map(item => sliceByRange(text, item.range).trim()),
            ['1 == 1', '1 == 1'],
        );
        assert.deepEqual(
            constTrue.map(item => item.range.start.line),
            [4, 5],
        );
        assert.deepEqual(
            constTrue.map(item => item.data?.__rangeFallback ?? null),
            [null, null],
        );
    });

    it('keeps nested parent transition guard diagnostics on guard expressions', async () => {
        const text = [
            'state Root {',
            '    state P {',
            '        state A;',
            '        state B;',
            '        [*] -> A;',
            '        A -> B : if [1 == 1];',
            '    }',
            '    state C;',
            '    [*] -> P;',
            '    P -> C : if [1 == 1];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-nested-parent-guard-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const constTrue = targetDiagnostics(diagnostics, 'W_GUARD_CONST_TRUE');

        assert.equal(constTrue.length, 2, JSON.stringify(diagnostics));
        assert.deepEqual(
            constTrue.map(item => sliceByRange(text, item.range).trim()),
            ['1 == 1', '1 == 1'],
        );
        assert.deepEqual(
            constTrue.map(item => item.range.start.line).sort((a, b) => a - b),
            [5, 9],
        );
        assert.deepEqual(
            constTrue.map(item => item.data?.__rangeFallback ?? null),
            [null, null],
        );
    });

    it('keeps forced-transition index offsets from moving guard diagnostics to state identifiers', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !* -> B :: FatalError;',
            '    A -> B : if [1 == 1];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-forced-offset-guard-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'W_GUARD_CONST_TRUE')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), '1 == 1');
        assert.equal(diagnostic.data?.transition_index, 3);
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
    });

    it('uses model-order transition indexes for nested repeated eventless transitions', async () => {
        const text = [
            'state Root {',
            '    state A {',
            '        state X;',
            '        state Y;',
            '        [*] -> X;',
            '        X -> Y;',
            '        X -> Y;',
            '    }',
            '    [*] -> A;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-nested-eventless-index-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const neverTriggered = targetDiagnostics(diagnostics, 'I_TRANSITION_NEVER_EVENT_TRIGGERED');

        assert.equal(neverTriggered.length, 2, JSON.stringify(diagnostics));
        assert.deepEqual(
            neverTriggered.map(item => sliceByRange(text, item.range).trim()),
            ['X -> Y;', 'X -> Y;'],
        );
        assert.deepEqual(
            neverTriggered.map(item => item.range.start.line),
            [5, 6],
        );
        assert.deepEqual(
            neverTriggered.map(item => item.data?.transition_index),
            [2, 3],
        );
        assert.deepEqual(
            neverTriggered.map(item => item.data?.__rangeFallback ?? null),
            [null, null],
        );
    });

    it('anchors forced eventless transition diagnostics on the forced statement', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-forced-eventless-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'I_TRANSITION_NEVER_EVENT_TRIGGERED')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), '!A -> B;');
        assert.equal(diagnostic.data?.transition_index, 0);
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
    });

    it('anchors all-source forced transition diagnostics on the forced statement', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !* -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-forced-all-eventless-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const transitionDiagnostics = diagnostics
            .filter(item => (
                item.code === 'I_TRANSITION_NEVER_EVENT_TRIGGERED' ||
                item.code === 'W_SELF_TRANSITION_NOP'
            ))
            .sort((a, b) => Number(a.data?.transition_index) - Number(b.data?.transition_index));

        assert.equal(transitionDiagnostics.length, 3, JSON.stringify(diagnostics));
        assert.deepEqual(
            transitionDiagnostics.map(item => [
                item.code,
                item.data?.transition_index,
                sliceByRange(text, item.range).trim(),
                item.data?.__rangeFallback,
            ]),
            [
                ['I_TRANSITION_NEVER_EVENT_TRIGGERED', 0, '!* -> B;', undefined],
                ['W_SELF_TRANSITION_NOP', 1, '!* -> B;', undefined],
                ['I_TRANSITION_NEVER_EVENT_TRIGGERED', 1, '!* -> B;', undefined],
            ],
        );
    });

    it('anchors forced constant guard diagnostics on the forced guard expression', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B : if [1 == 1];',
            '    !A -> B : if [1 == 2];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-forced-guard-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const constTrue = targetDiagnostics(diagnostics, 'W_GUARD_CONST_TRUE')[0];
        const constFalse = targetDiagnostics(diagnostics, 'W_GUARD_CONST_FALSE')[0];

        assert.ok(constTrue, JSON.stringify(diagnostics));
        assert.ok(constFalse, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, constTrue.range).trim(), '1 == 1');
        assert.equal(sliceByRange(text, constFalse.range).trim(), '1 == 2');
        assert.equal(constTrue.data?.transition_index, 0);
        assert.equal(constFalse.data?.transition_index, 1);
        assert.equal(constTrue.data?.__rangeFallback, undefined);
        assert.equal(constFalse.data?.__rangeFallback, undefined);
    });

    it('keeps literal false guards after forced transitions anchored to the guard', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !* -> B :: FatalError;',
            '    A -> B : if [false];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-literal-false-forced-offset-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'W_GUARD_CONST_FALSE')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), 'false');
        assert.equal(diagnostic.data?.transition_index, 3);
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
    });

    it('marks transition_not_found when refs cannot match any transition', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-index-not-found-marker.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'I_TRANSITION_NEVER_EVENT_TRIGGERED',
            severity: 'info' as const,
            message: 'Synthetic unmatched transition diagnostic.',
            span: null,
            refs: {
                from_path: 'Root.A',
                to_path: 'Root.B',
                transition_span: null,
                transition_index: 99,
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(diagnostics[0].data?.__rangeFallback, 'transition_not_found');
    });

    it('resolves normalized guard refs by transition index', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : if [(0x0F & 0xF0) != 0];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-normalized-guard-text-range.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'W_GUARD_CONST_FALSE',
            severity: 'warning' as const,
            message: 'Synthetic normalized guard diagnostic.',
            span: null,
            refs: {
                transition_span: null,
                folded_value: false,
                from_path: 'Root.A',
                to_path: 'Root.B',
                guard_text: '15 & 240 != 0',
                transition_index: 1,
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(sliceByRange(text, diagnostics[0].range).trim(), '(0x0F & 0xF0) != 0');
        assert.equal(diagnostics[0].data?.__rangeFallback, undefined);
    });

    it('keeps js inspect transition indexes aligned with Python parent-first order', async () => {
        const text = [
            'state Root {',
            '    state A {',
            '        state X;',
            '        state Y;',
            '        [*] -> X;',
            '        X -> Y;',
            '        X -> Y;',
            '    }',
            '    [*] -> A;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-nested-model-order.fcstm');
        const ast = await packageModule.parseAstDocument(document);
        const machine = packageModule.buildStateMachineModel(ast);
        const report = packageModule.inspectModel(machine);

        assert.deepEqual(
            report.transitions.map(item => [item.transition_index, item.from_path, item.to_path]),
            [
                [0, '[*]', 'Root.A'],
                [1, '[*]', 'Root.A.X'],
                [2, 'Root.A.X', 'Root.A.Y'],
                [3, 'Root.A.X', 'Root.A.Y'],
            ],
        );
    });


    it('keeps JS inspect transition indexes aligned for forced nested transitions', async () => {
        const text = [
            'state Root {',
            '    state A {',
            '        state X;',
            '        state Y;',
            '        [*] -> X;',
            '        X -> Y;',
            '        X -> Y;',
            '    }',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B :: Fatal;',
            '    A -> B : if [false];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-forced-nested-model-order.fcstm');
        const ast = await packageModule.parseAstDocument(document);
        const machine = packageModule.buildStateMachineModel(ast);
        const report = packageModule.inspectModel(machine);

        assert.deepEqual(
            report.transitions.map(item => [item.transition_index, item.from_path, item.to_path, item.is_forced]),
            [
                [0, 'Root.A', 'Root.B', true],
                [1, '[*]', 'Root.A', false],
                [2, 'Root.A', 'Root.B', false],
                [3, 'Root.A.X', '[*]', true],
                [4, 'Root.A.Y', '[*]', true],
                [5, '[*]', 'Root.A.X', false],
                [6, 'Root.A.X', 'Root.A.Y', false],
                [7, 'Root.A.X', 'Root.A.Y', false],
            ],
        );
    });

    it('marks fallback when duplicate transitions omit transition_index', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '    A -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-index-missing-marker.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'I_TRANSITION_NEVER_EVENT_TRIGGERED',
            severity: 'info' as const,
            message: 'Transition "Root.A" -> "Root.B" has no event or guard.',
            span: null,
            refs: {
                from_path: 'Root.A',
                to_path: 'Root.B',
                transition_span: null,
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(sliceByRange(text, diagnostics[0].range).trim(), 'A -> B;');
        assert.equal(diagnostics[0].data?.__rangeFallback, 'transition_ambiguous');
    });

    it('marks fallback when duplicate transitions provide an invalid transition_index type', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B;',
            '    A -> B;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-index-invalid-marker.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'I_TRANSITION_NEVER_EVENT_TRIGGERED',
            severity: 'info' as const,
            message: 'Transition "Root.A" -> "Root.B" has no event or guard.',
            span: null,
            refs: {
                from_path: 'Root.A',
                to_path: 'Root.B',
                transition_span: null,
                transition_index: '1',
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(sliceByRange(text, diagnostics[0].range).trim(), 'A -> B;');
        assert.equal(diagnostics[0].data?.__rangeFallback, 'transition_ambiguous');
    });


    it('uses transition_index to resolve out-of-order self-assignment diagnostics', async () => {
        const text = [
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    state C;',
            '    [*] -> A;',
            '    A -> B effect { x = x; };',
            '    A -> C effect { x = x; };',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-self-assign-index-range.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [
            {
                code: 'W_EFFECT_SELF_ASSIGN',
                severity: 'warning' as const,
                message: 'second transition self-assign first',
                span: null,
                refs: {
                    state_path: 'Root.A',
                    transition_span: null,
                    var_name: 'x',
                    transition_index: 2,
                },
            },
            {
                code: 'W_EFFECT_SELF_ASSIGN',
                severity: 'warning' as const,
                message: 'first transition self-assign second',
                span: null,
                refs: {
                    state_path: 'Root.A',
                    transition_span: null,
                    var_name: 'x',
                    transition_index: 1,
                },
            },
        ]);

        assert.equal(diagnostics.length, 2);
        assert.deepEqual(
            diagnostics.map(item => [item.message, item.range.start.line, sliceByRange(text, item.range).trim()]),
            [
                ['second transition self-assign first', 7, 'x = x;'],
                ['first transition self-assign second', 6, 'x = x;'],
            ],
        );
        assert.deepEqual(
            diagnostics.map(item => item.data?.__rangeFallback ?? null),
            [null, null],
        );
    });

    it('marks self-assignment transition fallback when the concrete statement cannot be resolved', async () => {
        const text = [
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B effect {',
            '        x = x + 1;',
            '    };',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-self-assign-fallback-marker.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'W_EFFECT_SELF_ASSIGN',
            severity: 'warning' as const,
            message: 'Transition effect assigns "x" to itself.',
            span: null,
            refs: {
                state_path: 'Root.A',
                transition_span: null,
                var_name: 'x',
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(sliceByRange(text, diagnostics[0].range).trim(), 'effect {\n        x = x + 1;\n    }');
        assert.equal(diagnostics[0].data?.__rangeFallback, 'effect_fallback');
    });
});

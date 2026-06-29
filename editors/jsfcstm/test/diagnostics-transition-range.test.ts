import assert from 'node:assert/strict';
import * as path from 'node:path';

import {collectRedundancyWarnings} from '../src/diagnostics/analyzers/redundancy';
import {createDocument, packageModule, sliceByRange, trackTempDir, writeFile} from './support';

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

    it('treats uppercase boolean literal guards as true values', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    state C;',
            '    [*] -> A;',
            '    A -> B : if [True];',
            '    B -> C : if [TRUE];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/transition-uppercase-boolean-guard-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const constTrue = targetDiagnostics(diagnostics, 'W_GUARD_CONST_TRUE');
        const constFalse = targetDiagnostics(diagnostics, 'W_GUARD_CONST_FALSE');

        assert.equal(constFalse.length, 0, JSON.stringify(diagnostics));
        assert.equal(constTrue.length, 2, JSON.stringify(diagnostics));
        assert.deepEqual(
            constTrue.map(item => [
                sliceByRange(text, item.range).trim(),
                item.data?.folded_value,
                item.data?.guard_text,
                item.data?.__rangeFallback,
            ]),
            [
                ['True', true, 'true', undefined],
                ['TRUE', true, 'true', undefined],
            ],
        );
    });


    it('keeps import-aware transition diagnostics on source-owned ranges', async () => {
        const dir = trackTempDir('jsfcstm-transition-import-range-');
        const childFile = path.join(dir, 'child.fcstm');
        const hostFile = path.join(dir, 'main.fcstm');
        writeFile(childFile, [
            'def int x = 0;',
            'state Child {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : if [1 == 1];',
            '    A -> B effect { x = x; };',
            '}',
        ].join('\n'));
        const hostText = [
            'state Root {',
            '    import "./child.fcstm" as Imported;',
            '    state Local;',
            '    [*] -> Imported;',
            '    Imported -> Local : if [True];',
            '}',
        ].join('\n');
        const document = createDocument(hostText, hostFile);
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const transitionCodes = new Set([
            'W_GUARD_CONST_TRUE',
            'W_EFFECT_SELF_ASSIGN',
            'I_TRANSITION_NEVER_EVENT_TRIGGERED',
        ]);
        const transitionDiagnostics = diagnostics.filter(item => transitionCodes.has(String(item.code)));
        const constTrue = targetDiagnostics(diagnostics, 'W_GUARD_CONST_TRUE');

        assert.equal(constTrue.length, 1, JSON.stringify(diagnostics));
        assert.equal(constTrue[0].data?.from_path, 'Root.Imported');
        assert.equal(constTrue[0].data?.to_path, 'Root.Local');
        assert.equal(sliceByRange(hostText, constTrue[0].range).trim(), 'True');
        assert.equal(constTrue[0].data?.__rangeFallback, undefined);
        assert.equal(targetDiagnostics(diagnostics, 'W_EFFECT_SELF_ASSIGN').length, 0, JSON.stringify(diagnostics));
        assert.equal(
            targetDiagnostics(diagnostics, 'I_TRANSITION_NEVER_EVENT_TRIGGERED').length,
            0,
            JSON.stringify(diagnostics),
        );
        assert.deepEqual(
            transitionDiagnostics.map(item => item.data?.__rangeFallback).filter(Boolean),
            [],
        );
    });

    it('anchors forced override diagnostics on the forced declaration with related normal transition', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B :: Go;',
            '    A -> B :: Go;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/forced-override-related-normal-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = targetDiagnostics(diagnostics, 'W_FORCED_OVERRIDES_NORMAL')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostic.range).trim(), '!A -> B :: Go;');
        assert.equal(diagnostic.data?.forced_declaration_span !== undefined, true);
        assert.equal(diagnostic.data?.normal_transition_span !== undefined, true);
        assert.equal(diagnostic.data?.forced_span, undefined);
        assert.equal(diagnostic.data?.normal_span, undefined);
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
        assert.ok(diagnostic.relatedInformation?.length, JSON.stringify(diagnostic));
        assert.equal(sliceByRange(text, diagnostic.relatedInformation[0].location.range).trim(), 'A -> B :: Go;');
    });

    it('uses the wildcard forced declaration range for each forced override expansion', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    state C;',
            '    [*] -> A;',
            '    !* -> C : Reset;',
            '    A -> C : Reset;',
            '    B -> C : Reset;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/forced-override-wildcard-related-range.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const forcedOverrides = targetDiagnostics(diagnostics, 'W_FORCED_OVERRIDES_NORMAL')
            .sort((left, right) => String(left.data?.from_path).localeCompare(String(right.data?.from_path)));

        assert.equal(forcedOverrides.length, 2, JSON.stringify(diagnostics));
        assert.deepEqual(
            forcedOverrides.map(item => [
                item.data?.from_path,
                item.data?.to_path,
                sliceByRange(text, item.range).trim(),
                item.relatedInformation?.map((info: any) => sliceByRange(text, info.location.range).trim()),
                item.data?.__rangeFallback,
            ]),
            [
                ['Root.A', 'Root.C', '!* -> C : Reset;', ['A -> C : Reset;'], undefined],
                ['Root.B', 'Root.C', '!* -> C : Reset;', ['B -> C : Reset;'], undefined],
            ],
        );
    });

    it('keeps normal transition spans out of primary range fallback', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B :: Go;',
            '    A -> B :: Go;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/forced-override-normal-span-fallback.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        const forcedRange = packageModule.createRange(4, 4, 4, 20);
        const normalRange = packageModule.createRange(5, 4, 5, 19);

        assert.deepEqual(
            packageModule.resolveRangeFromRefsDetailed(document, semantic, {forced_span: forcedRange}).range,
            forcedRange,
        );
        assert.equal(
            packageModule.resolveRangeFromRefsDetailed(document, semantic, {normal_span: normalRange}).range,
            null,
        );
    });

    it('omits forced override related information when the normal span is unavailable', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B :: Go;',
            '    A -> B :: Go;',
            '}',
        ].join('\n');
        const semanticDocument = createDocument(text, '/tmp/forced-override-null-related-semantic.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(semanticDocument);
        const document = {
            getText() {
                return text;
            },
            lineCount: text.split('\n').length,
            lineAt(line: number) {
                return {text: text.split('\n')[line] || ''};
            },
        };
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'W_FORCED_OVERRIDES_NORMAL',
            severity: 'warning' as const,
            message: 'Synthetic forced override without a normal span.',
            span: null,
            refs: {
                from_path: 'Root.A',
                to_path: 'Root.B',
                forced_declaration_span: packageModule.createRange(4, 4, 4, 20),
                normal_transition_span: null,
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(sliceByRange(text, diagnostics[0].range).trim(), '!A -> B :: Go;');
        assert.equal(diagnostics[0].relatedInformation, undefined);
    });

    it('uses an untitled URI for forced override related information without a document file path', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    !A -> B :: Go;',
            '    A -> B :: Go;',
            '}',
        ].join('\n');
        const semanticDocument = createDocument(text, '/tmp/forced-override-untitled-related-semantic.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(semanticDocument);
        const document = {
            getText() {
                return text;
            },
            lineCount: text.split('\n').length,
            lineAt(line: number) {
                return {text: text.split('\n')[line] || ''};
            },
        };
        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'W_FORCED_OVERRIDES_NORMAL',
            severity: 'warning' as const,
            message: 'Synthetic forced override with an untitled document.',
            span: null,
            refs: {
                from_path: 'Root.A',
                to_path: 'Root.B',
                forced_declaration_span: packageModule.createRange(4, 4, 4, 20),
                normal_transition_span: packageModule.createRange(5, 4, 5, 19),
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(diagnostics[0].relatedInformation?.[0]?.location.uri, 'untitled:fcstm');
        assert.equal(
            sliceByRange(text, diagnostics[0].relatedInformation![0].location.range).trim(),
            'A -> B :: Go;',
        );
    });

    it('skips forced override analyzer warnings when no normal trigger matches', () => {
        const diagnostics = collectRedundancyWarnings(
            [{
                from_path: 'Root.A',
                to_path: 'Root.B',
                event: 'Root.A.Go',
                event_scope: 'local',
                guard: null,
                effect: null,
                effect_self_assigns: [],
                is_forced: true,
                forced_origin: 'Root.A',
                transition_index: 1,
            }],
            [],
            [],
        );

        assert.deepEqual(targetDiagnostics(diagnostics, 'W_FORCED_OVERRIDES_NORMAL'), []);
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

    it('keeps combo warning primary and related ranges on original combo terms', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B :: E1 + E1;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/combo-warning-ranges.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        assert.ok(semantic, 'expected semantic document');

        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'W_COMBO_DUPLICATE_EVENT',
            severity: 'warning',
            message: 'Synthetic duplicate combo event.',
            span: {line: 5, column: 20, end_line: 5, end_column: 22},
            refs: {
                origin_id: 'Root:A->B::: E1 + E1',
                event_name: 'Root.A.E1',
                term_index: 1,
                first_term_index: 0,
                term_text: 'E1',
                first_term_text: 'E1',
                transition_span: {line: 5, column: 5, end_line: 5, end_column: 23},
                trigger_span: {line: 5, column: 12, end_line: 5, end_column: 23},
                term_span: {line: 5, column: 20, end_line: 5, end_column: 22},
                first_term_span: {line: 5, column: 15, end_line: 5, end_column: 17},
            },
        }]);

        assert.equal(diagnostics.length, 1, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostics[0].range), 'E1');
        assert.equal(diagnostics[0].range.start.character, 19);
        assert.equal(diagnostics[0].data?.__rangeFallback, undefined);
        assert.equal(
            sliceByRange(text, diagnostics[0].relatedInformation![0].location.range),
            'E1',
        );
        assert.equal(diagnostics[0].relatedInformation![0].location.range.start.character, 14);
        assert.equal(
            sliceByRange(text, diagnostics[0].relatedInformation![1].location.range).trim(),
            'A -> B :: E1 + E1;',
        );
    });

    it('adds prior guard related information for combo prefix guard warnings', async () => {
        const text = [
            'def int x = 1;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : [x > 0] + [x > -1];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/combo-prefix-guard-related.fcstm');
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        assert.ok(semantic, 'expected semantic document');

        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'W_COMBO_GUARD_PREFIX_IMPLIED',
            severity: 'warning',
            message: 'Synthetic implied combo guard.',
            span: null,
            refs: {
                origin_id: 'Root:A->B:: [x > 0] + [x > -1]',
                term_index: 1,
                prior_term_index: 0,
                term_text: '[x > -1]',
                prior_term_text: '[x > 0]',
                transition_span: {line: 6, column: 5, end_line: 6, end_column: 33},
                trigger_span: {line: 6, column: 12, end_line: 6, end_column: 33},
                term_span: {line: 6, column: 24, end_line: 6, end_column: 32},
                value_span: {line: 6, column: 25, end_line: 6, end_column: 31},
                prior_term_span: {line: 6, column: 14, end_line: 6, end_column: 21},
                prior_value_span: {line: 6, column: 15, end_line: 6, end_column: 20},
            },
        }]);

        assert.equal(diagnostics.length, 1, JSON.stringify(diagnostics));
        assert.equal(sliceByRange(text, diagnostics[0].range), '[x > -1]');
        assert.equal(diagnostics[0].data?.__rangeFallback, undefined);
        assert.equal(
            sliceByRange(text, diagnostics[0].relatedInformation![0].location.range),
            '[x > 0]',
        );
    });

    it('emits combo guard warnings through the real document diagnostics path', async () => {
        const text = [
            'def int x = 1;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : [(1 + 2) == 3] + [(1 + 2) == 4];',
            '    A -> B : [x > 0] + [x > -1];',
            '    A -> B : [x > 0] + [x < 0];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/combo-real-guard-warning-ranges.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const byCode = new Map(diagnostics.map(item => [item.code, item]));
        const constTrue = byCode.get('W_COMBO_GUARD_CONST_TRUE');
        const constFalse = byCode.get('W_COMBO_GUARD_CONST_FALSE');
        const implied = byCode.get('W_COMBO_GUARD_PREFIX_IMPLIED');
        const contradicts = byCode.get('W_COMBO_GUARD_PREFIX_CONTRADICTS');

        assert.ok(constTrue, JSON.stringify(diagnostics.map(item => item.code)));
        assert.ok(constFalse, JSON.stringify(diagnostics.map(item => item.code)));
        assert.ok(implied, JSON.stringify(diagnostics.map(item => item.code)));
        assert.ok(contradicts, JSON.stringify(diagnostics.map(item => item.code)));
        assert.equal(sliceByRange(text, constTrue.range), '[(1 + 2) == 3]');
        assert.equal(sliceByRange(text, constFalse.range), '[(1 + 2) == 4]');
        assert.equal(sliceByRange(text, implied.range), '[x > -1]');
        assert.equal(sliceByRange(text, contradicts.range), '[x < 0]');
        assert.equal(
            sliceByRange(text, implied.relatedInformation![0].location.range),
            '[x > 0]',
        );
        assert.equal(
            sliceByRange(text, contradicts.relatedInformation![0].location.range),
            '[x > 0]',
        );
        assert.equal(implied.data?.__rangeFallback, undefined);
        assert.equal(contradicts.data?.__rangeFallback, undefined);
    });

    it('emits complex prior guard combo warnings through the real document diagnostics path', async () => {
        const text = [
            'def int x = 1;',
            'def int y = 1;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : [x > 0 && y > 0] + [x > 0];',
            '    A -> B : [x > 0 && y > 0] + [x < 0];',
            '    A -> B : [x >= 0 && x <= 0] + [x != 0];',
            '    A -> B : [x > 0] + [x > 0 || y > 0];',
            '    A -> B : [x > 0] + [not (x > 0)];',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/combo-real-complex-guard-warning-ranges.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const implied = diagnostics.filter(item => item.code === 'W_COMBO_GUARD_PREFIX_IMPLIED');
        const contradicts = diagnostics.filter(item => item.code === 'W_COMBO_GUARD_PREFIX_CONTRADICTS');

        assert.equal(implied.length, 2, JSON.stringify(diagnostics.map(item => item.data)));
        assert.equal(contradicts.length, 3, JSON.stringify(diagnostics.map(item => item.data)));

        const complexImplied = implied.find(item => item.data?.term_text === '[x > 0]');
        const orImplied = implied.find(item => item.data?.term_text === '[x > 0 || y > 0]');
        const complexContradiction = contradicts.find(item => item.data?.term_text === '[x < 0]');
        const singletonContradiction = contradicts.find(item => item.data?.term_text === '[x != 0]');
        const notContradiction = contradicts.find(item => item.data?.term_text === '[!(x > 0)]');

        assert.ok(complexImplied, JSON.stringify(implied.map(item => item.data)));
        assert.ok(orImplied, JSON.stringify(implied.map(item => item.data)));
        assert.ok(complexContradiction, JSON.stringify(contradicts.map(item => item.data)));
        assert.ok(singletonContradiction, JSON.stringify(contradicts.map(item => item.data)));
        assert.ok(notContradiction, JSON.stringify(contradicts.map(item => item.data)));

        assert.equal(sliceByRange(text, complexImplied.range), '[x > 0]');
        assert.equal(sliceByRange(text, orImplied.range), '[x > 0 || y > 0]');
        assert.equal(sliceByRange(text, complexContradiction.range), '[x < 0]');
        assert.equal(sliceByRange(text, singletonContradiction.range), '[x != 0]');
        assert.equal(sliceByRange(text, notContradiction.range), '[not (x > 0)]');
        assert.equal(notContradiction.data?.term_text, '[!(x > 0)]');

        assert.equal(
            sliceByRange(text, complexImplied.relatedInformation![0].location.range),
            '[x > 0 && y > 0]',
        );
        assert.equal(
            sliceByRange(text, orImplied.relatedInformation![0].location.range),
            '[x > 0]',
        );
        assert.equal(
            sliceByRange(text, complexContradiction.relatedInformation![0].location.range),
            '[x > 0 && y > 0]',
        );
        assert.equal(
            sliceByRange(text, singletonContradiction.relatedInformation![0].location.range),
            '[x >= 0 && x <= 0]',
        );
        assert.equal(
            sliceByRange(text, notContradiction.relatedInformation![0].location.range),
            '[x > 0]',
        );
        assert.equal(complexImplied.data?.prior_term_text, '[x > 0 && y > 0]');
        assert.equal(orImplied.data?.prior_term_text, '[x > 0]');
        assert.equal(complexContradiction.data?.prior_term_text, '[x > 0 && y > 0]');
        assert.equal(singletonContradiction.data?.prior_term_text, '[x >= 0 && x <= 0]');
        assert.equal(notContradiction.data?.prior_term_text, '[x > 0]');
        for (const diagnostic of [...implied, ...contradicts]) {
            assert.equal(diagnostic.data?.__rangeFallback, undefined);
        }
    });

    it('emits duplicate combo event warnings through the real document diagnostics path', async () => {
        const text = [
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B :: E1 + E1;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/combo-real-warning-ranges.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const duplicateEvents = diagnostics.filter(item => item.code === 'W_COMBO_DUPLICATE_EVENT');

        assert.equal(duplicateEvents.length, 1, JSON.stringify(duplicateEvents.map(item => item.data)));
        const diagnostic = duplicateEvents[0];
        assert.equal(sliceByRange(text, diagnostic.range), 'E1');
        assert.equal(diagnostic.range.start.character, 19);
        assert.equal(
            sliceByRange(text, diagnostic.relatedInformation![0].location.range),
            'E1',
        );
        assert.equal(diagnostic.relatedInformation![0].location.range.start.character, 14);
        assert.equal(
            sliceByRange(text, diagnostic.relatedInformation![1].location.range).trim(),
            'A -> B :: E1 + E1;',
        );
    });

    it('deduplicates entry and exit combo event warnings on the inspect-backed document path', async () => {
        const cases = [{
            text: [
                'state Root {',
                '    state A;',
                '    [*] -> A :: Boot + Boot;',
                '}',
            ].join('\n'),
            filePath: '/tmp/combo-entry-duplicate-real-warning-ranges.fcstm',
            transitionText: '[*] -> A :: Boot + Boot;',
            repeatedTerm: 'Boot',
            originId: 'Root:__init__->A::: Boot + Boot',
        }, {
            text: [
                'state Root {',
                '    state A;',
                '    [*] -> A;',
                '    A -> [*] :: Done + Done;',
                '}',
            ].join('\n'),
            filePath: '/tmp/combo-exit-duplicate-real-warning-ranges.fcstm',
            transitionText: 'A -> [*] :: Done + Done;',
            repeatedTerm: 'Done',
            originId: 'Root:A->__exit__::: Done + Done',
        }];

        for (const item of cases) {
            const document = createDocument(item.text, item.filePath);
            const diagnostics = await packageModule.collectDocumentDiagnostics(document);
            const duplicateEvents = diagnostics.filter(diag => diag.code === 'W_COMBO_DUPLICATE_EVENT');

            assert.equal(duplicateEvents.length, 1, JSON.stringify(duplicateEvents.map(diag => diag.data)));
            const diagnostic = duplicateEvents[0];
            assert.equal(sliceByRange(item.text, diagnostic.range), item.repeatedTerm);
            assert.equal(
                sliceByRange(item.text, diagnostic.relatedInformation![0].location.range),
                item.repeatedTerm,
            );
            assert.equal(
                sliceByRange(item.text, diagnostic.relatedInformation![1].location.range).trim(),
                item.transitionText,
            );
            assert.equal(diagnostic.data?.origin_id, item.originId);
        }
    });

});

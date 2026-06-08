import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir} from './support';

describe('jsfcstm diagnostics', () => {
    it('converts parse errors into document diagnostics with clamped ranges', () => {
        const document = createDocument('state Root;', '/tmp/diagnostic.fcstm');

        const wordDiagnostic = packageModule.convertParseErrorToDiagnostic({
            line: 0,
            column: 6,
            message: 'Broken symbol',
            severity: 'error',
        }, document);
        assert.deepEqual(wordDiagnostic.range, packageModule.createRange(0, 6, 0, 10));
        assert.equal(wordDiagnostic.source, 'fcstm');

        const punctuationDiagnostic = packageModule.convertParseErrorToDiagnostic({
            line: 0,
            column: 5,
            message: 'Punctuation issue',
            severity: 'warning',
        }, document);
        assert.deepEqual(punctuationDiagnostic.range, packageModule.createRange(0, 5, 0, 6));
        assert.equal(punctuationDiagnostic.severity, 'warning');

        const clampedDiagnostic = packageModule.convertParseErrorToDiagnostic({
            line: 99,
            column: 99,
            message: 'Out of bounds',
            severity: 'error',
        }, document);
        assert.deepEqual(clampedDiagnostic.range, packageModule.createRange(0, 11, 0, 12));
    });

    it('collects parse diagnostics from invalid DSL inspired by pyfcstm/test_error.py', async () => {
        const document = createDocument(
            'def int counter = 0\nstate Root;',
            '/tmp/broken.fcstm'
        );

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.ok(diagnostics.some(item => /semicolon/i.test(item.message)));
    });

    it('collects import diagnostics together with parse diagnostics', async () => {
        const dir = trackTempDir('jsfcstm-diagnostics-');
        const hostFile = path.join(dir, 'host.fcstm');
        const document = createDocument(
            'state Root {\n    import "./missing.fcstm" as Missing;\n}',
            hostFile
        );

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.ok(diagnostics.some(item => /cannot be resolved/i.test(item.message)));
    });

    it('keeps condition logical operator diagnostics on the intended side of the DSL boundary', async () => {
        const legalDocument = createDocument([
            'def int a = 0;',
            'def int b = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B : if [a > 0 => b > 0];',
            '    B -> A : if [a > 0 xor b > 0];',
            '    A -> A : if [a > 0 iff b > 0];',
            '}',
        ].join('\n'), '/tmp/legal-logical-diagnostics.fcstm');
        const legalDiagnostics = await packageModule.collectDocumentDiagnostics(legalDocument);
        assert.equal(legalDiagnostics.some(item => item.severity === 'error'), false);

        const caretDocument = createDocument(
            'state Root { state A; state B; A -> B : if [true ^ false]; }',
            '/tmp/condition-caret-diagnostic.fcstm'
        );
        const caretDiagnostics = await packageModule.collectDocumentDiagnostics(caretDocument);
        assert.ok(caretDiagnostics.some(item => /numeric bitwise xor.*use "xor"/i.test(item.message)));

        const conditionArrowDocument = createDocument(
            'state Root { state A; state B; A -> B : if [true -> false]; }',
            '/tmp/condition-arrow-diagnostic.fcstm'
        );
        const conditionArrowDiagnostics = await packageModule.collectDocumentDiagnostics(conditionArrowDocument);
        assert.ok(conditionArrowDiagnostics.some(item => /use "=>" or "implies".*"->" is only for transitions/i.test(item.message)));

        const transitionDocument = createDocument(
            'state Root { state A; state B; A => B; }',
            '/tmp/transition-implication-diagnostic.fcstm'
        );
        const transitionDiagnostics = await packageModule.collectDocumentDiagnostics(transitionDocument);
        assert.ok(transitionDiagnostics.some(item => /use '->' for transitions, not '=>'/i.test(item.message)));

        const numericDocument = createDocument([
            'def int x = 0;',
            'def int a = 0;',
            'def int b = 0;',
            'state Root {',
            '    state A { enter { x = a ^ b; } }',
            '    [*] -> A;',
            '}',
        ].join('\n'), '/tmp/numeric-caret-diagnostic.fcstm');
        const numericDiagnostics = await packageModule.collectDocumentDiagnostics(numericDocument);
        assert.equal(numericDiagnostics.some(item => item.severity === 'error'), false);
    });
});

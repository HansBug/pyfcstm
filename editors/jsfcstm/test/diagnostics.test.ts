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
});

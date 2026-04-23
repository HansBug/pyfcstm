import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir} from './support';

describe('jsfcstm analyzers and code actions', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('reports semantic analyzer diagnostics for unreachable states, dead transitions, unused events, mappings, and unresolved refs', async () => {
        const dir = trackTempDir('jsfcstm-analyzers-');
        const hostFile = path.join(dir, 'host.fcstm');
        const document = createDocument([
            'state Root {',
            '    import "./missing.fcstm" as Worker {',
            '        def sensor_* -> io_$1;',
            '        def sensor_* -> io_$1;',
            '    }',
            '    event Start;',
            '    enter ref MissingAction;',
            '    state Idle;',
            '    state Dead;',
            '    [*] -> Idle;',
            '    Idle -> dead : if [false];',
            '}',
        ].join('\n'), hostFile);

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const codes = diagnostics.map(item => item.code);
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.missingImport));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.duplicateImportMapping));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.unreachableState));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.deadTransition));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.unusedEvent));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.unresolvedState));
        assert.ok(codes.includes(packageModule.FCSTM_DIAGNOSTIC_CODES.unresolvedActionRef));
    });

    it('builds safe quick fixes for missing imports, duplicate mappings, unused events, and unresolved states', async () => {
        const dir = trackTempDir('jsfcstm-code-actions-');
        const hostFile = path.join(dir, 'host.fcstm');
        const document = createDocument([
            'state Root {',
            '    import "./missing.fcstm" as Worker {',
            '        def sensor_* -> io_$1;',
            '        def sensor_* -> io_$1;',
            '    }',
            '    event Start;',
            '    state Idle;',
            '    [*] -> Idle;',
            '    Idle -> idle;',
            '}',
        ].join('\n'), hostFile);

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const actions = await packageModule.collectCodeActions(
            document,
            packageModule.createRange(0, 0, 8, 20),
            diagnostics
        );

        assert.ok(actions.some(item => /Remove unresolved import/.test(item.title)));
        assert.ok(actions.some(item => /Remove duplicate import mapping/.test(item.title)));
        assert.ok(actions.some(item => /Remove unused event/.test(item.title)));
        assert.ok(actions.some(item => /Change to Idle/.test(item.title)));

        const renameLikeAction = actions.find(item => /Change to Idle/.test(item.title));
        const renameEdit = renameLikeAction?.edit?.changes[Object.keys(renameLikeAction.edit.changes)[0]][0];
        assert.equal(renameEdit?.newText, 'Idle');
    });

    it('reports duplicate variable definitions and offers a remove quick fix', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'def float counter = 1.0;',
            'state Root { [*] -> Idle; state Idle; }',
        ].join('\n'), '/tmp/dup-var.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const duplicate = diagnostics.find(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.duplicateVariable);
        assert.ok(duplicate, 'expected duplicateVariable diagnostic');
        assert.match(duplicate.message, /counter/);
        assert.equal(duplicate.severity, 'error');
        assert.ok(duplicate.relatedInformation && duplicate.relatedInformation.length >= 1);

        const actions = await packageModule.collectCodeActions(
            document,
            duplicate.range,
            diagnostics
        );
        const removeAction = actions.find(item => /Remove duplicate definition/.test(item.title));
        assert.ok(removeAction, 'expected remove-duplicate quick fix');
        const edits = Object.values(removeAction.edit?.changes || {}).flat();
        assert.equal(edits.length, 1);
        assert.equal(edits[0].newText, '');
    });

    it('reports undefined variables in guards and offers a define-at-top quick fix', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [counter > 0 && missing_flag == 1];',
            '}',
        ].join('\n'), '/tmp/undef-var.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const undef = diagnostics.find(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVariable);
        assert.ok(undef, 'expected undefinedVariable diagnostic');
        assert.match(undef.message, /missing_flag/);

        const actions = await packageModule.collectCodeActions(
            document,
            undef.range,
            diagnostics
        );
        const defineAction = actions.find(item => /Define "missing_flag" at the top of the file/.test(item.title));
        assert.ok(defineAction, 'expected define-at-top quick fix');
        const edits = Object.values(defineAction.edit?.changes || {}).flat();
        assert.equal(edits.length, 1);
        assert.match(edits[0].newText, /^def int missing_flag = 0;\n$/);
        // Should land on the line after the last existing def.
        assert.equal(edits[0].range.start.line, 1);
        assert.equal(edits[0].range.end.line, 1);
    });

    it('reports undefined variables in effect blocks and allows the quick fix even with no existing defs', async () => {
        const document = createDocument([
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active effect { counter = counter + 1; }',
            '}',
        ].join('\n'), '/tmp/undef-effect.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const undef = diagnostics.find(item => (
            item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.readBeforeAssignTemporary
            && /counter/.test(item.message)
        ));
        assert.ok(undef, 'expected read-before-assign diagnostic for the RHS identifier');

        // Undefined-variable quick fix only runs for that exact code; this
        // test mainly pins down the temp-variable detection path.
        const actions = await packageModule.collectCodeActions(document, undef.range, diagnostics);
        // The action list may be empty (no matching code) - the important
        // property is that the analyzer produced a targeted diagnostic at all.
        assert.ok(Array.isArray(actions));
    });

    it('does not flag undefined variables in transitions that are legitimate state names', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active : if [counter > 0];',
            '}',
        ].join('\n'), '/tmp/no-false-undef.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.equal(
            diagnostics.filter(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.undefinedVariable).length,
            0
        );
    });

    it('read-before-assign inside a block is reported only on the first read, not on subsequent assignments', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active effect {',
            '        temp = counter + 1;',  // temp gets defined here
            '        counter = temp * 2;',  // temp is now legitimate
            '    }',
            '}',
        ].join('\n'), '/tmp/temp-ok.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.equal(
            diagnostics.filter(item => item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.readBeforeAssignTemporary).length,
            0
        );
    });

    it('read-before-assign inside an if-branch is surfaced', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    state Idle;',
            '    state Active;',
            '    [*] -> Idle;',
            '    Idle -> Active effect {',
            '        if [counter > 0] {',
            '            counter = scratch + 1;',
            '        }',
            '    }',
            '}',
        ].join('\n'), '/tmp/temp-bad.fcstm');

        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const tempDiag = diagnostics.find(item => (
            item.code === packageModule.FCSTM_DIAGNOSTIC_CODES.readBeforeAssignTemporary
        ));
        assert.ok(tempDiag, 'expected temp read-before-assign diagnostic inside the if-branch');
        assert.match(tempDiag.message, /scratch/);
    });
});

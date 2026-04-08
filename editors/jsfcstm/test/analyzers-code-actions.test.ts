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
});

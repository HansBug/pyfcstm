import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, sliceByRange, trackTempDir} from './support';

function diagnosticsByCode(diagnostics: any[], code: string): any[] {
    return diagnostics.filter(item => item.code === code);
}

function fullDocumentSlice(text: string): string {
    const lines = text.split('\n');
    return sliceByRange(text, packageModule.createRange(
        0,
        0,
        lines.length - 1,
        lines[lines.length - 1]?.length ?? 0,
    ));
}

describe('diagnostics declaration ranges', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('anchors dead named action diagnostics on the action declaration name', async () => {
        const text = [
            'state Root {',
            '    state Live;',
            '    state Orphan {',
            '        enter Dead { }',
            '    }',
            '    [*] -> Live;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/declaration-dead-action.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnosticsByCode(diagnostics, 'W_DEAD_NAMED_ACTION')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(diagnostic.data?.defined_in, 'Root.Orphan');
        assert.equal(sliceByRange(text, diagnostic.range), 'Dead');
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
        assert.notEqual(sliceByRange(text, diagnostic.range), 'Orphan');
        assert.notEqual(sliceByRange(text, diagnostic.range), fullDocumentSlice(text));
    });

    it('anchors named action shadow diagnostics on the inner action and relates the outer action', async () => {
        const text = [
            'state Root {',
            '    enter Sync { }',
            '    state Child {',
            '        enter Sync { }',
            '    }',
            '    [*] -> Child;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/declaration-action-shadow.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnosticsByCode(diagnostics, 'W_NAMED_ACTION_SHADOWS_ANCESTOR')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(diagnostic.data?.inner_state_path, 'Root.Child');
        assert.equal(diagnostic.data?.outer_state_path, 'Root');
        assert.equal(sliceByRange(text, diagnostic.range), 'Sync');
        assert.equal(diagnostic.range.start.line, 3);
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
        assert.ok(diagnostic.relatedInformation?.length, JSON.stringify(diagnostic));
        assert.equal(sliceByRange(text, diagnostic.relatedInformation[0].location.range), 'Sync');
        assert.equal(diagnostic.relatedInformation[0].location.range.start.line, 1);
    });

    it('uses the nearest ancestor action as related information in deep shadow chains', async () => {
        const text = [
            'state Root {',
            '    enter Sync { }',
            '    state A {',
            '        enter Sync { }',
            '        state B { enter Sync { } }',
            '        [*] -> B;',
            '    }',
            '    [*] -> A;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/declaration-action-shadow-deep.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnosticsByCode(diagnostics, 'W_NAMED_ACTION_SHADOWS_ANCESTOR')
            .find(item => item.data?.inner_state_path === 'Root.A.B');

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(diagnostic.data?.outer_state_path, 'Root.A');
        assert.equal(sliceByRange(text, diagnostic.range), 'Sync');
        assert.equal(diagnostic.range.start.line, 4);
        assert.ok(diagnostic.relatedInformation?.length, JSON.stringify(diagnostic));
        assert.equal(sliceByRange(text, diagnostic.relatedInformation[0].location.range), 'Sync');
        assert.equal(diagnostic.relatedInformation[0].location.range.start.line, 3);
    });

    it('anchors shadowed event diagnostics on the local event and relates the broader event', async () => {
        const text = [
            'state Root {',
            '    event Tick;',
            '    state Active;',
            '    state Idle;',
            '    [*] -> Active;',
            '    Active -> Idle : Tick;',
            '    Active -> Idle :: Tick;',
            '}',
        ].join('\n');
        const document = createDocument(text, '/tmp/declaration-shadowed-event.fcstm');
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        const diagnostic = diagnosticsByCode(diagnostics, 'W_SHADOWED_EVENT')[0];

        assert.ok(diagnostic, JSON.stringify(diagnostics));
        assert.equal(diagnostic.data?.local_path, 'Root.Active.Tick');
        assert.equal(diagnostic.data?.chain_path, 'Root.Tick');
        assert.equal(sliceByRange(text, diagnostic.range), 'Tick');
        assert.equal(diagnostic.range.start.line, 6);
        assert.equal(diagnostic.data?.__rangeFallback, undefined);
        assert.ok(diagnostic.relatedInformation?.length, JSON.stringify(diagnostic));
        assert.equal(sliceByRange(text, diagnostic.relatedInformation[0].location.range), 'Tick');
        assert.equal(diagnostic.relatedInformation[0].location.range.start.line, 1);
    });

    it('does not map imported declaration diagnostics onto unrelated host-document ranges', async () => {
        const dir = trackTempDir('jsfcstm-declaration-import-range-');
        const childFile = path.join(dir, 'child.fcstm');
        const hostText = [
            'state Root {',
            '    state Imported {',
            '        state Orphan {',
            '            enter Dead { }',
            '        }',
            '    }',
            '    [*] -> Imported;',
            '}',
        ].join('\n');
        const document = createDocument(hostText, path.join(dir, 'main.fcstm'));
        const semantic = await packageModule.getWorkspaceGraph().getSemanticDocument(document);
        assert.ok(semantic);
        semantic.lookups.statesByPath['Root.Imported'].ast.importedFromFile = childFile;

        const diagnostics = packageModule.collectInspectDiagnosticsFromItems(document, semantic, [{
            code: 'W_DEAD_NAMED_ACTION',
            severity: 'warning' as const,
            message: 'Synthetic imported dead action.',
            span: null,
            refs: {
                function_name: 'Dead',
                defined_in: 'Root.Imported.Orphan',
            },
        }]);

        assert.equal(diagnostics.length, 1);
        assert.equal(sliceByRange(hostText, diagnostics[0].range), fullDocumentSlice(hostText));
        assert.equal(diagnostics[0].data?.__rangeFallback, 'full_document');
        assert.notEqual(sliceByRange(hostText, diagnostics[0].range), 'Dead');
    });
});

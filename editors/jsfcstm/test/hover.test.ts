import assert from 'node:assert/strict';
import * as path from 'node:path';

import {
    createDocument,
    hoverModule,
    packageModule,
    trackTempDir,
    withPatchedProperty,
    writeFile,
} from './support';

describe('jsfcstm hover support', () => {
    it('finds hover docs for operators, pseudo markers, and keywords', () => {
        const localEventLine = 'StateA -> StateB :: LocalEvent;';
        const chainEventLine = 'StateA -> StateB :ChainEvent;';
        const absoluteEventLine = 'StateA -> StateB : /GlobalEvent;';
        const pseudoStateLine = '[*] -> Root;';

        assert.equal(
            packageModule.findHoverInfo(localEventLine, localEventLine.indexOf('::'), '')?.title,
            'Local Event Scope'
        );
        assert.equal(
            packageModule.findHoverInfo(chainEventLine, chainEventLine.indexOf(':'), '')?.title,
            'Chain Event Scope'
        );
        assert.equal(
            packageModule.findHoverInfo(absoluteEventLine, absoluteEventLine.indexOf('/'), '')?.title,
            'Absolute Event Scope'
        );
        assert.equal(
            packageModule.findHoverInfo(pseudoStateLine, pseudoStateLine.indexOf('[*]') + 1, '')?.title,
            'Pseudo-State Marker'
        );
        assert.equal(
            packageModule.findHoverInfo('>> during before { }', 3, '')?.title,
            'Global During Before Aspect'
        );
        assert.equal(
            packageModule.findHoverInfo('>> during after { }', 3, '')?.title,
            'Global During After Aspect'
        );
        assert.equal(
            packageModule.findHoverInfo('during before { }', 2, '')?.title,
            'During Before Aspect'
        );
        assert.equal(
            packageModule.findHoverInfo('during after { }', 2, '')?.title,
            'During After Aspect'
        );
        assert.equal(
            packageModule.findHoverInfo('state Root;', 2, 'state')?.title,
            'State Definition'
        );
        assert.equal(packageModule.findHoverInfo('plain text', 0, ''), null);
        assert.equal(packageModule.findHoverInfo('state Root;', 5, ''), null);
    });

    it('exposes the keyword hover documentation table', () => {
        assert.equal(hoverModule.HOVER_DOCS.import.title, 'Import Statement');
        assert.equal(hoverModule.HOVER_DOCS['::'].title, 'Local Event Scope');
        assert.equal(hoverModule.HOVER_DOCS.effect.title, 'Transition Effect');
    });

    it('resolves documentation and import hovers', async () => {
        const dir = trackTempDir('jsfcstm-hover-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        writeFile(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

        const keywordDocument = createDocument('state Root;', hostFile);
        const keywordHover = await packageModule.resolveHover(keywordDocument, {line: 0, character: 2});
        assert.equal(keywordHover?.kind, 'doc');
        assert.equal(keywordHover?.doc.title, 'State Definition');

        const importDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" as Worker;\n}',
            hostFile
        );
        const importHover = await packageModule.resolveHover(importDocument, {line: 1, character: 15});
        assert.equal(importHover?.kind, 'import');
        assert.equal(importHover?.rootStateName, 'Worker');
        assert.deepEqual(importHover?.explicitVariables, ['speed']);
        assert.deepEqual(importHover?.absoluteEvents, ['/Start']);

        const nullHover = await packageModule.resolveHover(keywordDocument, {line: 0, character: 11});
        assert.equal(nullHover, null);
    });

    it('returns null when import resolution does not find a target', async () => {
        const index = packageModule.getImportWorkspaceIndex();
        const document = createDocument('state Root;', '/tmp/no-import.fcstm');

        await withPatchedProperty(index, 'getResolvedImportAtPosition', async () => null, async () => {
            const hover = await packageModule.resolveHover(document, {line: 0, character: 11});
            assert.equal(hover, null);
        });
    });
});

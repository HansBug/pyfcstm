import assert from 'node:assert/strict';
import * as path from 'node:path';
import {pathToFileURL} from 'node:url';

import {createDocument, packageModule, trackTempDir, writeFile} from './support';

function charOf(document: ReturnType<typeof createDocument>, line: number, marker: string, offset = 0): number {
    return document.lineAt(line).text.indexOf(marker) + offset;
}

describe('jsfcstm semantic navigation and rename support', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    it('collects references, highlights, and rename edits for imported aliases', async () => {
        const dir = trackTempDir('jsfcstm-refs-import-');
        const hostFile = path.join(dir, 'host.fcstm');
        const workerFile = path.join(dir, 'worker.fcstm');

        writeFile(workerFile, [
            'state WorkerRoot {',
            '    state Idle;',
            '}',
        ].join('\n'));
        const hostDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '    [*] -> Worker;',
            '    Worker -> Worker;',
            '}',
        ].join('\n'), hostFile);

        const definition = await packageModule.resolveDefinitionLocation(hostDocument, {
            line: 2,
            character: charOf(hostDocument, 2, 'Worker') + 1,
        });
        assert.equal(definition?.uri, pathToFileURL(workerFile).toString());

        const pathDefinition = await packageModule.resolveDefinitionLocation(hostDocument, {
            line: 1,
            character: charOf(hostDocument, 1, './worker.fcstm') + 2,
        });
        assert.equal(pathDefinition?.uri, pathToFileURL(workerFile).toString());

        const references = await packageModule.collectReferences(hostDocument, {
            line: 1,
            character: charOf(hostDocument, 1, 'Worker') + 1,
        });
        assert.equal(references.length, 5);

        const highlights = await packageModule.collectDocumentHighlights(hostDocument, {
            line: 3,
            character: charOf(hostDocument, 3, 'Worker') + 1,
        });
        assert.equal(highlights.length, 5);
        assert.ok(highlights.some(item => item.kind === 'text'));
        assert.ok(highlights.some(item => item.kind === 'read'));

        const rename = await packageModule.planRename(hostDocument, {
            line: 1,
            character: charOf(hostDocument, 1, 'Worker') + 1,
        }, 'Motor');
        const renameEdits = rename?.changes[pathToFileURL(hostFile).toString()] || [];
        assert.equal(renameEdits.length, 4);
        assert.ok(renameEdits.every((item: {newText: string}) => item.newText === 'Motor'));

        const pathHighlights = await packageModule.collectDocumentHighlights(hostDocument, {
            line: 1,
            character: charOf(hostDocument, 1, './worker.fcstm') + 2,
        });
        assert.equal(pathHighlights.length, 5);
        const pathReferences = await packageModule.collectReferences(hostDocument, {
            line: 1,
            character: charOf(hostDocument, 1, './worker.fcstm') + 2,
        });
        assert.equal(pathReferences.length, 5);
    });

    it('collects references and rename edits for variables and named actions', async () => {
        const filePath = '/tmp/jsfcstm-refs-local.fcstm';
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    enter ResetCounter {',
            '        counter = counter + 1;',
            '    }',
            '    exit ref ResetCounter;',
            '    [*] -> Idle;',
            '    state Idle;',
            '    Idle -> Idle : if [counter > 0] effect { counter = counter + 1; }',
            '}',
        ].join('\n'), filePath);

        const variableRefs = await packageModule.collectReferences(document, {
            line: 0,
            character: charOf(document, 0, 'counter') + 1,
        });
        assert.equal(variableRefs.length, 6);

        const variableRename = await packageModule.planRename(document, {
            line: 0,
            character: charOf(document, 0, 'counter') + 1,
        }, 'ticks');
        assert.equal(Object.values(variableRename?.changes || {}).flat().length, 6);

        const actionRefs = await packageModule.collectReferences(document, {
            line: 2,
            character: charOf(document, 2, 'ResetCounter') + 1,
        });
        assert.equal(actionRefs.length, 2);

        const actionRename = await packageModule.planRename(document, {
            line: 5,
            character: charOf(document, 5, 'ResetCounter') + 1,
        }, 'ResetTicks');
        assert.equal(Object.values(actionRename?.changes || {}).flat().length, 2);
    });

    it('collects workspace symbols across imported files', async () => {
        const dir = trackTempDir('jsfcstm-workspace-symbols-');
        const hostFile = path.join(dir, 'host.fcstm');
        const workerFile = path.join(dir, 'worker.fcstm');

        writeFile(workerFile, [
            'def int speed = 0;',
            'state Worker {',
            '    event Start;',
            '}',
        ].join('\n'));

        const hostDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as WorkerModule;',
            '    [*] -> WorkerModule;',
            '}',
        ].join('\n'), hostFile);

        const symbols = await packageModule.collectWorkspaceSymbols([hostDocument], 'work');
        assert.ok(symbols.some(item => item.name === 'WorkerModule'));
        assert.ok(symbols.some(item => item.name === 'Worker'));
    });

    it('links declared events to all matching transition references, including keyword-range hits', async () => {
        const filePath = '/tmp/jsfcstm-event-refs.fcstm';
        const document = createDocument([
            'state Root {',
            '    event Start;',
            '    state Idle;',
            '    state Running;',
            '    [*] -> Idle;',
            '    Idle -> Running : Start;',
            '    Running -> Idle : /Start;',
            '}',
        ].join('\n'), filePath);

        const declarationRefs = await packageModule.collectReferences(document, {
            line: 1,
            character: charOf(document, 1, 'Start') + 1,
        });
        assert.equal(declarationRefs.length, 3);

        const keywordHighlights = await packageModule.collectDocumentHighlights(document, {
            line: 1,
            character: charOf(document, 1, 'event') + 1,
        });
        assert.equal(keywordHighlights.length, 3);
        assert.ok(keywordHighlights.some(item => item.kind === 'text'));
        assert.ok(keywordHighlights.some(item => item.kind === 'read'));

        const keywordRefs = await packageModule.collectReferences(document, {
            line: 1,
            character: charOf(document, 1, 'event') + 1,
        });
        assert.equal(keywordRefs.length, 3);
    });

    it('resolves event declarations by AST name range instead of matching display-name text', async () => {
        const filePath = '/tmp/jsfcstm-event-display-name.fcstm';
        const document = createDocument([
            'state Root {',
            '    state Idle {',
            '        event E2 named \'fuck E2\';',
            '    }',
            '    Idle -> Idle :: E2;',
            '}',
        ].join('\n'), filePath);

        const definition = await packageModule.resolveDefinitionLocation(document, {
            line: 4,
            character: charOf(document, 4, 'E2') + 1,
        });
        assert.equal(definition?.range.start.line, 2);
        assert.equal(definition?.range.start.character, charOf(document, 2, 'E2'));
    });

    it('links import event mappings to host and imported event/state definitions', async () => {
        const dir = trackTempDir('jsfcstm-import-event-mapping-');
        const hostFile = path.join(dir, 'fleet.fcstm');
        const motorFile = path.join(dir, 'modules', 'motor.fcstm');

        writeFile(motorFile, [
            'state Motor {',
            '    event Start;',
            '    state Bus {',
            '        event Stop;',
            '        event Alarm;',
            '    }',
            '}',
        ].join('\n'));

        const document = createDocument([
            'state Fleet {',
            '    event Start;',
            '    state Bus {',
            '        event Stop;',
            '        event Alarm;',
            '    };',
            '    import "./modules/motor.fcstm" as LeftMotor named "Left Motor" {',
            '        event /Start -> Start named "Fleet Start";',
            '        event /Bus.Stop -> /Bus.Stop;',
            '    }',
            '    import "./modules/motor.fcstm" as RightMotor named "Right Motor" {',
            '        event /Start -> Start named "Fleet Start";',
            '        event /Bus.Stop -> /Bus.Stop;',
            '    }',
            '    [*] -> LeftMotor;',
            '    LeftMotor -> RightMotor;',
            '}',
        ].join('\n'), hostFile);
        const leftStartTargetCharacter = document.lineAt(7).text.indexOf('Start', document.lineAt(7).text.indexOf('->')) + 1;
        const leftStopSourceCharacter = document.lineAt(8).text.indexOf('Stop') + 1;
        const leftBusTargetCharacter = document.lineAt(8).text.indexOf('Bus', document.lineAt(8).text.indexOf('->')) + 1;
        const leftStopTargetCharacter = document.lineAt(8).text.lastIndexOf('Stop') + 1;
        const rightStopTargetCharacter = document.lineAt(12).text.lastIndexOf('Stop') + 1;

        const hostTargetRefs = await packageModule.collectReferences(document, {
            line: 7,
            character: leftStartTargetCharacter,
        });
        assert.equal(hostTargetRefs.length, 3);

        const hostTargetHighlights = await packageModule.collectDocumentHighlights(document, {
            line: 12,
            character: rightStopTargetCharacter,
        });
        assert.equal(hostTargetHighlights.length, 3);

        const hostEventDefinition = await packageModule.resolveDefinitionLocation(document, {
            line: 8,
            character: leftStopTargetCharacter,
        });
        assert.equal(hostEventDefinition?.uri, pathToFileURL(hostFile).toString());
        assert.equal(hostEventDefinition?.range.start.line, 3);

        const hostStateDefinition = await packageModule.resolveDefinitionLocation(document, {
            line: 8,
            character: leftBusTargetCharacter,
        });
        assert.equal(hostStateDefinition?.uri, pathToFileURL(hostFile).toString());
        assert.equal(hostStateDefinition?.range.start.line, 2);

        const sourceEventRefs = await packageModule.collectReferences(document, {
            line: 7,
            character: charOf(document, 7, 'Start') + 1,
        });
        assert.equal(sourceEventRefs.length, 3);

        const sourceEventDefinition = await packageModule.resolveDefinitionLocation(document, {
            line: 8,
            character: leftStopSourceCharacter,
        });
        assert.equal(sourceEventDefinition?.uri, pathToFileURL(motorFile).toString());
        assert.equal(sourceEventDefinition?.range.start.line, 3);
    });
});

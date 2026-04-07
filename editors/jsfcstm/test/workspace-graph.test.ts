import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir, writeFile} from './support';

describe('jsfcstm workspace graph', () => {
    it('hydrates imported summaries and mappings across multiple files', async () => {
        const dir = trackTempDir('jsfcstm-graph-');
        const hostFile = path.join(dir, 'host.fcstm');
        const workerFile = path.join(dir, 'worker.fcstm');

        writeFile(workerFile, [
            'def int sensor_temp = 0;',
            'state Worker {',
            '    event Start;',
            '}',
        ].join('\n'));

        const hostDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker {',
            '        def sensor_* -> io_$1;',
            '        event /Start -> /Bus.Start;',
            '    }',
            '}',
        ].join('\n'), hostFile);

        const graph = new packageModule.FcstmWorkspaceGraph();
        const snapshot = await graph.buildSnapshotForDocument(hostDocument);
        assert.deepEqual(snapshot.order.sort(), [hostFile, workerFile].sort());
        assert.equal(snapshot.cycles.length, 0);

        const rootImport = snapshot.nodes[hostFile].semantic?.imports[0];
        assert.ok(rootImport);
        assert.equal(rootImport?.targetRootStateName, 'Worker');
        assert.deepEqual(rootImport?.sourceVariables, ['sensor_temp']);
        assert.deepEqual(rootImport?.mappedVariables, ['io_temp']);
        assert.deepEqual(rootImport?.sourceAbsoluteEvents, ['/Start']);
        assert.deepEqual(rootImport?.mappedAbsoluteEvents, ['/Bus.Start']);
    });

    it('prefers overlay content over disk files and can clear overlays again', async () => {
        const dir = trackTempDir('jsfcstm-graph-overlay-');
        const hostFile = path.join(dir, 'host.fcstm');
        const workerFile = path.join(dir, 'worker.fcstm');

        writeFile(workerFile, [
            'def int sensor_temp = 0;',
            'state Worker {',
            '    event Start;',
            '}',
        ].join('\n'));

        const hostDocument = createDocument('state Root { import "./worker.fcstm" as Worker; }', hostFile);
        const graph = new packageModule.FcstmWorkspaceGraph();

        let snapshot = await graph.buildSnapshotForDocument(hostDocument);
        let rootImport = snapshot.nodes[hostFile].semantic?.imports[0];
        assert.deepEqual(rootImport?.mappedVariables, ['sensor_temp']);
        assert.deepEqual(rootImport?.mappedAbsoluteEvents, ['/Start']);

        graph.setOverlay(workerFile, [
            'def int sensor_speed = 0;',
            'state Worker {',
            '    event Speed;',
            '}',
        ].join('\n'));

        snapshot = await graph.buildSnapshotForDocument(hostDocument);
        rootImport = snapshot.nodes[hostFile].semantic?.imports[0];
        assert.deepEqual(rootImport?.mappedVariables, ['sensor_speed']);
        assert.deepEqual(rootImport?.mappedAbsoluteEvents, ['/Speed']);

        graph.removeOverlay(workerFile);
        snapshot = await graph.buildSnapshotForDocument(hostDocument);
        rootImport = snapshot.nodes[hostFile].semantic?.imports[0];
        assert.deepEqual(rootImport?.mappedVariables, ['sensor_temp']);
        assert.deepEqual(rootImport?.mappedAbsoluteEvents, ['/Start']);

        graph.setOverlay(workerFile, 'state Worker;');
        graph.clearOverlays();
        snapshot = await graph.buildSnapshotForDocument(hostDocument);
        rootImport = snapshot.nodes[hostFile].semantic?.imports[0];
        assert.deepEqual(rootImport?.mappedVariables, ['sensor_temp']);
    });

    it('detects import cycles and exposes the shared singleton graph', async () => {
        const dir = trackTempDir('jsfcstm-graph-cycle-');
        const aFile = path.join(dir, 'a.fcstm');
        const bFile = path.join(dir, 'b.fcstm');

        writeFile(aFile, 'state A { import "./b.fcstm" as B; }');
        writeFile(bFile, 'state B { import "./a.fcstm" as A; }');

        const graph = new packageModule.FcstmWorkspaceGraph();
        const snapshot = await graph.buildSnapshotForFile(aFile);
        assert.equal(snapshot.cycles.length, 1);
        assert.deepEqual(snapshot.cycles[0].files.map((item: string) => path.basename(item)), [
            'a.fcstm',
            'b.fcstm',
            'a.fcstm',
        ]);

        const sharedA = packageModule.getWorkspaceGraph();
        const sharedB = packageModule.getWorkspaceGraph();
        assert.equal(sharedA, sharedB);
    });
});

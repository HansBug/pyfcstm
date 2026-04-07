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

    it('covers private graph fallbacks for caching, missing targets, and null semantics', async () => {
        const dir = trackTempDir('jsfcstm-graph-private-');
        const hostFile = path.join(dir, 'host.fcstm');
        const workerFile = path.join(dir, 'worker.fcstm');

        writeFile(workerFile, 'state Worker;');

        const graph = new packageModule.FcstmWorkspaceGraph() as packageModule.FcstmWorkspaceGraph & {
            createTraversalState(): {
                nodes: Map<string, unknown>;
                order: string[];
                cycles: Array<{files: string[]}>;
                cycleKeys: Set<string>;
                stack: string[];
            };
            traverseDocument(
                document: ReturnType<typeof createDocument>,
                filePath: string,
                state: {
                    nodes: Map<string, unknown>;
                    order: string[];
                    cycles: Array<{files: string[]}>;
                    cycleKeys: Set<string>;
                    stack: string[];
                }
            ): Promise<unknown>;
            traverseFile(filePath: string, state: unknown): Promise<unknown>;
            loadDocument(filePath: string): ReturnType<typeof createDocument> | null;
            recordCycle(
                files: string[],
                state: {
                    nodes: Map<string, unknown>;
                    order: string[];
                    cycles: Array<{files: string[]}>;
                    cycleKeys: Set<string>;
                    stack: string[];
                }
            ): void;
            hydrateImport(semanticImport: {
                exists: boolean;
                missing: boolean;
                entryFile?: string;
                sourceVariables: string[];
                sourceAbsoluteEvents: string[];
                mappedVariables: string[];
                mappedAbsoluteEvents: string[];
            }, targetSemantic: null, targetFile: string): void;
        };
        const document = createDocument('state Root { import "./worker.fcstm" as Worker; }', hostFile);

        const state = graph.createTraversalState();
        const firstNode = await graph.traverseDocument(document, hostFile, state);
        const secondNode = await graph.traverseDocument(document, hostFile, state);
        assert.equal(firstNode, secondNode);

        const originalTraverseFile = graph.traverseFile;
        graph.traverseFile = async () => undefined;
        try {
            const missingTargetState = graph.createTraversalState();
            await graph.traverseDocument(document, hostFile, missingTargetState);
            assert.equal(
                (missingTargetState.nodes.get(hostFile) as {imports: Array<{target?: unknown}>}).imports[0].target,
                undefined
            );
        } finally {
            graph.traverseFile = originalTraverseFile;
        }

        const missingImport = {
            exists: false,
            missing: true,
            entryFile: undefined,
            sourceVariables: ['x'],
            sourceAbsoluteEvents: ['/E'],
            mappedVariables: ['x'],
            mappedAbsoluteEvents: ['/E'],
        };
        graph.hydrateImport(missingImport, null, workerFile);
        assert.equal(missingImport.exists, true);
        assert.equal(missingImport.missing, false);
        assert.equal(missingImport.entryFile, workerFile);
        assert.deepEqual(missingImport.sourceVariables, []);
        assert.deepEqual(missingImport.mappedAbsoluteEvents, []);

        const cycleState = graph.createTraversalState();
        graph.recordCycle([hostFile, workerFile, hostFile], cycleState);
        graph.recordCycle([hostFile, workerFile, hostFile], cycleState);
        assert.equal(cycleState.cycles.length, 1);

        assert.equal(graph.loadDocument(path.join(dir, 'missing.fcstm')), null);
    });

    it('returns a null-semantic node when parser output is unavailable', async () => {
        const dir = trackTempDir('jsfcstm-graph-null-semantic-');
        const filePath = path.join(dir, 'broken.fcstm');
        const document = createDocument('state Root;', filePath);
        const graph = new packageModule.FcstmWorkspaceGraph();
        const parser = packageModule.getParser();
        const original = parser.parseTree;
        parser.parseTree = async () => null;

        try {
            const snapshot = await graph.buildSnapshotForDocument(document);
            assert.equal(snapshot.nodes[filePath].ast, null);
            assert.equal(snapshot.nodes[filePath].semantic, null);
        } finally {
            parser.parseTree = original;
        }
    });

    it('covers memory-document and missing-file snapshot helpers', async () => {
        const graph = new packageModule.FcstmWorkspaceGraph();
        const memoryDocument = {
            lineCount: 1,
            getText() {
                return 'state Root;';
            },
            lineAt() {
                return {text: 'state Root;'};
            },
        } as packageModule.TextDocumentLike;

        const memorySnapshot = await graph.buildSnapshotForDocument(memoryDocument);
        assert.equal(memorySnapshot.rootFile, '<memory>');
        assert.deepEqual(memorySnapshot.order, ['<memory>']);
        assert.equal(memorySnapshot.nodes['<memory>'].semantic?.summary.rootStateName, 'Root');

        const missingFile = path.join(trackTempDir('jsfcstm-graph-missing-'), 'missing.fcstm');
        const missingSnapshot = await graph.buildSnapshotForFile(missingFile);
        assert.deepEqual(missingSnapshot.order, []);
        assert.deepEqual(missingSnapshot.nodes, {});
        assert.equal(await graph.getSemanticDocumentForFile(missingFile), null);
    });
});

import assert from 'node:assert/strict';
import * as path from 'node:path';

import {
    createDocument,
    packageModule,
    trackTempDir,
    withPatchedProperty,
    writeFile,
} from './support';

describe('jsfcstm import workspace support', () => {
    it('resolves direct files, directory imports, absolute paths, and missing references', () => {
        const dir = trackTempDir('jsfcstm-resolve-');
        const directFile = path.join(dir, 'worker.fcstm');
        const packageDir = path.join(dir, 'package');

        writeFile(directFile, 'state Worker;');
        writeFile(path.join(packageDir, 'main.fcstm'), 'state PackageRoot;');

        const direct = packageModule.resolveImportReference(path.join(dir, 'host.fcstm'), './worker.fcstm');
        assert.equal(direct.exists, true);
        assert.equal(direct.missing, false);
        assert.equal(direct.entryFile, directFile);

        const folder = packageModule.resolveImportReference(path.join(dir, 'host.fcstm'), './package');
        assert.equal(folder.exists, true);
        assert.equal(folder.entryFile, path.join(packageDir, 'main.fcstm'));

        const absolute = packageModule.resolveImportReference(path.join(dir, 'host.fcstm'), directFile);
        assert.equal(absolute.exists, true);
        assert.equal(absolute.entryFile, directFile);

        const missing = packageModule.resolveImportReference(path.join(dir, 'host.fcstm'), './missing');
        assert.equal(missing.exists, false);
        assert.equal(missing.missing, true);
    });

    it('returns an empty parse result when parseTree is unavailable', async () => {
        const index = new packageModule.FcstmImportWorkspaceIndex();
        const parser = packageModule.getParser();
        const document = createDocument('state Root;', '/tmp/parse-null.fcstm');

        await withPatchedProperty(parser, 'parseTree', async () => null, async () => {
            const parsed = await index.parseDocument(document);
            assert.deepEqual(parsed, {
                imports: [],
                explicitVariables: [],
                absoluteEvents: [],
            });
        });
    });

    it('parses imports, variables, root states, and absolute events from real DSL', async () => {
        const dir = trackTempDir('jsfcstm-parse-imports-');
        const hostFile = path.join(dir, 'host.fcstm');
        const text = [
            'def int counter = 0;',
            'state Root {',
            '    event Start;',
            '    state Host {',
            '        import "./worker.fcstm" as Worker named "Worker Module" {',
            '            def sensor_* -> io_$1;',
            '            event /Start -> /Bus.Start named "Bus Start";',
            '        }',
            '    }',
            '}',
        ].join('\n');
        const document = createDocument(text, hostFile);
        const index = new packageModule.FcstmImportWorkspaceIndex();

        const parsed = await index.parseDocument(document);
        assert.deepEqual(parsed.explicitVariables, ['counter']);
        assert.equal(parsed.rootStateName, 'Root');
        assert.deepEqual(parsed.absoluteEvents, ['/Start']);
        assert.equal(parsed.imports.length, 1);
        assert.equal(parsed.imports[0].alias, 'Worker');
        assert.equal(parsed.imports[0].extraName, 'Worker Module');
        assert.deepEqual(parsed.imports[0].statePath, ['Root', 'Host']);
    });

    it('resolves imported summaries and import targets at a cursor position', async () => {
        const dir = trackTempDir('jsfcstm-import-targets-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');

        writeFile(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

        const text = 'state Root {\n    import "./worker.fcstm" as Worker;\n}';
        const document = createDocument(text, hostFile);
        const index = new packageModule.FcstmImportWorkspaceIndex();

        const resolved = await index.resolveImportsForDocument(document);
        assert.equal(resolved.length, 1);
        assert.equal(resolved[0].entryFile, workerFile);
        assert.equal(resolved[0].rootStateName, 'Worker');
        assert.deepEqual(resolved[0].explicitVariables, ['speed']);
        assert.deepEqual(resolved[0].absoluteEvents, ['/Start']);

        const atPosition = await index.getResolvedImportAtPosition(document, {line: 1, character: 15});
        assert.ok(atPosition);
        assert.equal(atPosition?.entry.alias, 'Worker');
        assert.equal(atPosition?.target.entryFile, workerFile);

        const outsideImport = await index.getResolvedImportAtPosition(document, {line: 0, character: 3});
        assert.equal(outsideImport, null);
    });

    it('reports duplicate aliases, missing imports, and circular imports', async () => {
        const dir = trackTempDir('jsfcstm-import-diagnostics-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');

        writeFile(workerFile, 'state Worker;');

        const duplicateDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '    import "./worker.fcstm" as Worker;',
            '    import "./missing.fcstm" as Missing;',
            '}',
        ].join('\n'), hostFile);

        const index = new packageModule.FcstmImportWorkspaceIndex();
        const duplicateDiagnostics = await index.collectImportDiagnostics(duplicateDocument);
        assert.ok(duplicateDiagnostics.some((item: { message: string }) => /Duplicate import alias/.test(item.message)));
        assert.ok(duplicateDiagnostics.some((item: { message: string }) => /cannot be resolved/.test(item.message)));

        writeFile(path.join(dir, 'a.fcstm'), 'state A { import "./b.fcstm" as B; }');
        writeFile(path.join(dir, 'b.fcstm'), 'state B { import "./a.fcstm" as A; }');
        const cycleDocument = createDocument(
            'state A { import "./b.fcstm" as B; }',
            path.join(dir, 'a.fcstm')
        );

        const cycleDiagnostics = await index.collectImportDiagnostics(cycleDocument);
        assert.ok(cycleDiagnostics.some((item: { message: string }) => /circular import/i.test(item.message)));
    });

    it('shares the singleton import workspace index', () => {
        assert.equal(packageModule.getImportWorkspaceIndex(), packageModule.getImportWorkspaceIndex());
    });

    it('covers null-semantic and fallback-range branches with a stub graph', async () => {
        const graph = {
            async getSemanticDocument() {
                return null;
            },
            async buildSnapshotForDocument() {
                return {
                    rootFile: '/tmp/stub.fcstm',
                    nodes: {
                        '/tmp/stub.fcstm': {
                            semantic: {
                                imports: [],
                            },
                        },
                    },
                    cycles: [{files: ['/tmp/stub.fcstm', '/tmp/other.fcstm', '/tmp/stub.fcstm']}],
                };
            },
        } as unknown as packageModule.FcstmWorkspaceGraph;
        const index = new packageModule.FcstmImportWorkspaceIndex(graph);
        const document = createDocument('state Root;', '/tmp/stub.fcstm');

        assert.deepEqual(await index.resolveImportsForDocument(document), []);
        assert.equal(await index.getResolvedImportAtPosition(document, {line: 0, character: 0}), null);
        const diagnostics = await index.collectImportDiagnostics(document);
        assert.equal(diagnostics.length, 1);
        assert.deepEqual(diagnostics[0].range, packageModule.createRange(0, 0, 0, 1));
    });

    it('returns no diagnostics when snapshot semantic data is unavailable', async () => {
        const graph = {
            async getSemanticDocument() {
                return null;
            },
            async buildSnapshotForDocument() {
                return {
                    rootFile: '/tmp/stub.fcstm',
                    nodes: {},
                    cycles: [],
                };
            },
        } as unknown as packageModule.FcstmWorkspaceGraph;
        const index = new packageModule.FcstmImportWorkspaceIndex(graph);
        const document = createDocument('state Root;', '/tmp/stub.fcstm');

        assert.deepEqual(await index.collectImportDiagnostics(document), []);
    });

    // PR-A-coverage: exercise the model-assembly rewrite paths through
    // a successful workspace import. The worker file uses every
    // expression operator kind (parenthesized, unary, conditional,
    // function call, binary) plus if-statements and forced transitions,
    // all referencing variables that the host import remaps. This
    // drives ``rewriteExpressionVariables`` through every switch case
    // plus ``rewriteOperationStatementVariables`` through the
    // if-statement branch plus the forced-transition rewrite loop in
    // ``rewriteStateMachineDocumentVariables``.
    it('rewrites all expression-kind nodes when an import remaps variables', async () => {
        const dir = trackTempDir('jsfcstm-rewrite-all-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');

        writeFile(workerFile,
            'def int counter = 0;\n'
            + 'def int threshold = 10;\n'
            + 'state Worker {\n'
            + '    state Idle;\n'
            + '    state Active;\n'
            + '    [*] -> Idle;\n'
            + '    Idle -> Active : if [(counter + 1) > 0 && (counter > threshold ? 1 : 0) > 0 && abs(-counter) < threshold];\n'
            + '    Active -> Idle :: Pause effect {\n'
            + '        if [counter > 0] { counter = counter - 1; } else { counter = 0; }\n'
            + '    };\n'
            + '    !* -> Active : if [counter > 100];\n'
            + '}\n',
        );
        const document = createDocument(
            'state Root {\n'
            + '    state Hub;\n'
            + '    [*] -> Hub;\n'
            + '    import "./worker.fcstm" as Sub {\n'
            + '        def counter -> remote_counter;\n'
            + '        def threshold -> remote_threshold;\n'
            + '    }\n'
            + '}\n',
            hostFile,
        );
        // Successful import should produce no diagnostics on either end.
        const diagnostics = await packageModule.collectDocumentDiagnostics(document);
        assert.deepEqual(diagnostics, [],
            `expected clean import, got ${JSON.stringify(diagnostics)}`);
    });
});

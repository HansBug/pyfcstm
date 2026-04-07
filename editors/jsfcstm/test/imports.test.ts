import assert from 'node:assert/strict';
import * as path from 'node:path';

import {
    createDocument,
    createNode,
    createToken,
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
        const index = new packageModule.FcstmImportWorkspaceIndex() as packageModule.FcstmImportWorkspaceIndex & {
            parser: { parseTree(text: string): Promise<unknown | null> };
        };
        const document = createDocument('state Root;', '/tmp/parse-null.fcstm');

        await withPatchedProperty(index, 'parser', {
            async parseTree() {
                return null;
            },
        }, async () => {
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
        assert.ok(duplicateDiagnostics.some(item => /Duplicate import alias/.test(item.message)));
        assert.ok(duplicateDiagnostics.some(item => /cannot be resolved/.test(item.message)));

        writeFile(path.join(dir, 'a.fcstm'), 'state A { import "./b.fcstm" as B; }');
        writeFile(path.join(dir, 'b.fcstm'), 'state B { import "./a.fcstm" as A; }');
        const cycleDocument = createDocument(
            'state A { import "./b.fcstm" as B; }',
            path.join(dir, 'a.fcstm')
        );

        const cycleDiagnostics = await index.collectImportDiagnostics(cycleDocument);
        assert.ok(cycleDiagnostics.some(item => /circular import/i.test(item.message)));
    });

    it('covers private import summary and cycle helpers', () => {
        const dir = trackTempDir('jsfcstm-import-private-');
        const ownerFile = path.join(dir, 'owner.fcstm');
        const moduleFile = path.join(dir, 'module.fcstm');
        const missingFile = path.join(dir, 'missing.fcstm');
        const nestedA = path.join(dir, 'nested-a.fcstm');
        const nestedB = path.join(dir, 'nested-b.fcstm');

        writeFile(ownerFile, 'state Owner;');
        writeFile(moduleFile, 'def int speed = 0;\nevent Start;\nimport "./missing.fcstm" as Missing;\nstate Module;');
        writeFile(nestedA, 'state NestedA { import "./nested-b.fcstm" as NestedB; }');
        writeFile(nestedB, 'state NestedB { import "./owner.fcstm" as Owner; }');

        const index = new packageModule.FcstmImportWorkspaceIndex() as packageModule.FcstmImportWorkspaceIndex & {
            readFileSummary(filePath: string): {
                filePath: string;
                exists: boolean;
                rootStateName?: string;
                explicitVariables: string[];
                absoluteEvents: string[];
                imports: Array<{ sourcePath: string; resolvedFile?: string; missing: boolean }>;
            };
            summarizeTextFile(filePath: string, text: string): {
                rootStateName?: string;
                explicitVariables: string[];
                absoluteEvents: string[];
                imports: Array<{ sourcePath: string; resolvedFile?: string; missing: boolean }>;
            };
            detectCycle(ownerFile: string, currentFile: string, chain: string[]): { files: string[] } | null;
        };

        const missingSummary = index.readFileSummary(missingFile);
        assert.equal(missingSummary.exists, false);
        assert.equal(index.readFileSummary(missingFile), missingSummary);

        const existingSummary = index.readFileSummary(moduleFile);
        assert.equal(existingSummary.exists, true);
        assert.equal(existingSummary.rootStateName, 'Module');
        assert.deepEqual(existingSummary.explicitVariables, ['speed']);
        assert.deepEqual(existingSummary.absoluteEvents, ['/Start']);
        assert.equal(existingSummary.imports[0].missing, true);

        const summarized = index.summarizeTextFile(ownerFile, 'def float temp = 1.0;\nstate Root;');
        assert.equal(summarized.rootStateName, 'Root');
        assert.deepEqual(summarized.explicitVariables, ['temp']);

        assert.deepEqual(index.detectCycle(ownerFile, ownerFile, [ownerFile]), {
            files: [ownerFile, ownerFile],
        });
        assert.equal(index.detectCycle(ownerFile, missingFile, []), null);
        assert.equal(index.detectCycle(ownerFile, moduleFile, [ownerFile]), null);
        assert.deepEqual(index.detectCycle(ownerFile, nestedA, [ownerFile]), {
            files: [ownerFile, nestedA, nestedB, ownerFile],
        });
    });

    it('covers synthetic tree extraction branches and fallback ranges', () => {
        const documentText = [
            'state Root {',
            '    import "./worker.fcstm" as Worker named "Worker Module";',
            '}',
        ].join('\n');
        const document = createDocument(documentText, '/tmp/synthetic-imports.fcstm');
        const index = new packageModule.FcstmImportWorkspaceIndex() as packageModule.FcstmImportWorkspaceIndex & {
            extractFromTree(tree: packageModule.ParseTreeNode, documentLike: packageModule.TextDocumentLike): packageModule.ParsedDocumentInfo;
        };

        const tree = createNode('StateMachineDSLProgramContext', [
            createNode('CompositeStateDefinitionContext', [
                createNode('State_bodyContext', [
                    undefined as unknown as packageModule.ParseTreeNode,
                    createNode('Event_definitionContext', [], {
                        event_name: createToken('Start', 1, 6),
                    }),
                    createNode('Import_event_mappingContext', [], {
                        source_event: {
                            getText() {
                                return '/Reset';
                            },
                        },
                    }),
                    createNode('Import_statementContext', [], {
                        import_path: {
                            text: '"./worker.fcstm"',
                        },
                        state_alias: {
                            text: 'Worker',
                        },
                        extra_name: {
                            text: '"Worker Module"',
                        },
                    }),
                ]),
            ], {
                state_id: createToken('Root', 1, 6),
            }),
        ]);

        const parsed = index.extractFromTree(tree, document);
        assert.equal(parsed.rootStateName, 'Root');
        assert.deepEqual(parsed.absoluteEvents.sort(), ['/Reset', '/Start']);
        assert.equal(parsed.imports.length, 1);
        assert.equal(parsed.imports[0].sourcePath, './worker.fcstm');
        assert.equal(parsed.imports[0].alias, 'Worker');
        assert.equal(parsed.imports[0].extraName, 'Worker Module');
        assert.deepEqual(parsed.imports[0].pathRange, packageModule.createRange(1, 11, 1, 27));
        assert.deepEqual(parsed.imports[0].aliasRange, packageModule.createRange(1, 31, 1, 37));
    });
});

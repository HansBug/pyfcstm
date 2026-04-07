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
});

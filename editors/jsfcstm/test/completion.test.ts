import assert from 'node:assert/strict';
import * as path from 'node:path';

import {
    createDocument,
    completionModule,
    packageModule,
    trackTempDir,
    withPatchedProperty,
    writeFile,
} from './support';

describe('jsfcstm completion support', () => {
    it('detects comment and string contexts', () => {
        assert.equal(packageModule.isInComment('value // comment'), true);
        assert.equal(packageModule.isInComment('value # comment'), true);
        assert.equal(packageModule.isInComment('value /* block'), true);
        assert.equal(packageModule.isInComment('value /* closed */'), false);

        assert.equal(packageModule.isInString('"open string'), true);
        assert.equal(packageModule.isInString('\'open string'), true);
        assert.equal(packageModule.isInString('"escaped \\" quote"'), false);
        assert.equal(packageModule.isInString('plain text'), false);
    });

    it('returns no completions inside comments or strings', async () => {
        const commentDocument = createDocument('// state', '/tmp/comment.fcstm');
        const stringDocument = createDocument('"state"', '/tmp/string.fcstm');

        const commentItems = await packageModule.collectCompletionItems(commentDocument, {line: 0, character: 8});
        const stringItems = await packageModule.collectCompletionItems(stringDocument, {line: 0, character: 6});

        assert.deepEqual(commentItems, []);
        assert.deepEqual(stringItems, []);
    });

    it('returns keyword, math, symbol, and import-aware completions', async () => {
        const dir = trackTempDir('jsfcstm-completion-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        writeFile(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

        const beforeAliasDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" \n}',
            hostFile
        );
        const beforeNamedDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" as Worker\n}',
            hostFile
        );
        const importHeaderDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" as Worker {\n}\n}',
            hostFile
        );
        const importBodyDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker {',
            '        ',
            '    }',
            '}',
        ].join('\n'), hostFile);
        const generalDocument = createDocument(
            'def int counter = 0;\nstate Root { event Start; }',
            '/tmp/general.fcstm'
        );

        const beforeAlias = await packageModule.collectCompletionItems(beforeAliasDocument, {line: 1, character: 27});
        assert.ok(beforeAlias.some(item => item.label === 'as' && item.kind === 'keyword'));

        const beforeNamed = await packageModule.collectCompletionItems(beforeNamedDocument, {line: 1, character: 37});
        assert.ok(beforeNamed.some(item => item.label === 'named' && item.kind === 'keyword'));

        const importHeader = await packageModule.collectCompletionItems(importHeaderDocument, {
            line: 1,
            character: importHeaderDocument.lineAt(1).text.length,
        });
        assert.ok(importHeader.some(item => item.label === 'def' && item.kind === 'keyword'));
        assert.ok(importHeader.some(item => item.label === 'event' && item.kind === 'keyword'));

        const importBody = await packageModule.collectCompletionItems(importBodyDocument, {line: 2, character: 8});
        assert.ok(importBody.some(item => item.label === 'speed' && item.kind === 'variable'));
        assert.ok(importBody.some(item => item.label === '/Start' && item.kind === 'event'));

        const generalItems = await packageModule.collectCompletionItems(generalDocument, {line: 1, character: 5});
        assert.ok(generalItems.some(item => item.label === 'state' && item.kind === 'keyword'));
        assert.ok(generalItems.some(item => item.label === 'pi' && item.kind === 'constant'));
        assert.ok(generalItems.some(item => item.label === 'sin' && item.kind === 'function'));
        assert.ok(generalItems.some(item => item.label === 'counter' && item.kind === 'variable'));
        assert.ok(generalItems.some(item => item.label === 'Root' && item.kind === 'class'));
        assert.ok(generalItems.some(item => item.label === 'Start' && item.kind === 'event'));
        assert.ok(generalItems.some(item => item.label === 'sin' && item.insertTextFormat === 'snippet'));
    });

    it('handles parser-null and missing-import-target completion branches', async () => {
        const parser = packageModule.getParser();
        const index = packageModule.getImportWorkspaceIndex();
        const document = createDocument(
            'state Root {\n    import "./missing.fcstm" as Missing {\n    }\n}',
            '/tmp/missing-import.fcstm'
        );

        await withPatchedProperty(parser, 'parseTree', async () => null, async () => {
            const items = await packageModule.collectCompletionItems(document, {line: 0, character: 3});
            assert.ok(items.some(item => item.label === 'state'));
            assert.equal(items.some(item => item.label === 'Missing'), false);
        });

        await withPatchedProperty(index, 'resolveImportsForDocument', async () => [], async () => {
            const items = await packageModule.collectCompletionItems(document, {line: 2, character: 4});
            assert.ok(items.some(item => item.label === 'def'));
            assert.equal(items.some(item => item.detail === 'Imported variable'), false);
        });
    });

    it('gracefully falls back to keyword completions when semantic AST building cannot recover', async () => {
        const document = createDocument('def ', '/tmp/incomplete-definition.fcstm');

        const items = await packageModule.collectCompletionItems(document, {line: 0, character: 4});

        assert.ok(items.some(item => item.label === 'int' && item.kind === 'keyword'));
        assert.ok(items.some(item => item.label === 'pi' && item.kind === 'constant'));
        assert.ok(items.some(item => item.label === 'sin' && item.kind === 'function'));
    });

    it('falls back to parse-tree symbol completions when semantic construction fails on partial input', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'def int count = 1;',
            'state Root {',
            '    enter {',
            '        cou',
            '    }',
            '}',
        ].join('\n'), '/tmp/partial-symbol.fcstm');

        const items = await packageModule.collectCompletionItems(document, {line: 4, character: 11});

        assert.ok(items.some(item => item.label === 'counter' && item.kind === 'variable'));
        assert.ok(items.some(item => item.label === 'count' && item.kind === 'variable'));
    });

    it('exposes stable keyword, constant, and function catalogs', () => {
        assert.ok(completionModule.KEYWORDS.includes('state'));
        assert.ok(completionModule.KEYWORDS.includes('import'));
        assert.ok(completionModule.MATH_CONSTANTS.some(item => item.name === 'pi'));
        assert.ok(completionModule.MATH_FUNCTIONS.some(item => item.name === 'sqrt'));
    });
});

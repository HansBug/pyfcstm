const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const packageJson = require('../package.json');
const packageModule = require('../dist/index.js');

const tempDirs = [];

function trackTempDir(prefix) {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), prefix));
    tempDirs.push(dir);
    return dir;
}

function writeFile(filePath, text) {
    fs.mkdirSync(path.dirname(filePath), {recursive: true});
    fs.writeFileSync(filePath, text);
}

function createDocument(text, filePath) {
    const lines = text.split('\n');
    return {
        filePath,
        uri: {
            fsPath: filePath,
            toString() {
                return this.fsPath;
            },
        },
        lineCount: lines.length,
        getText() {
            return text;
        },
        lineAt(line) {
            return {
                text: lines[line] || '',
            };
        },
    };
}

afterEach(() => {
    while (tempDirs.length > 0) {
        const dir = tempDirs.pop();
        fs.rmSync(dir, {recursive: true, force: true});
    }
});

describe('jsfcstm package metadata', () => {
    it('exports package metadata', () => {
        const info = packageModule.getJsFcstmPackageInfo();
        assert.equal(info.name, packageJson.name);
        assert.equal(info.version, packageJson.version);
        assert.equal(info.description, packageJson.description);
        assert.equal(packageModule.JSFCSTM_PACKAGE_NAME, packageJson.name);
        assert.equal(packageModule.JSFCSTM_PACKAGE_VERSION, packageJson.version);
    });
});

describe('jsfcstm text helpers', () => {
    it('builds and clones ranges', () => {
        const range = packageModule.createRange(1, 2, 3, 4);
        const clone = packageModule.cloneRange(range);
        assert.deepEqual(clone, range);
        assert.notEqual(clone, range);
    });

    it('resolves document file paths from filePath or uri', () => {
        const directDocument = createDocument('state Root;', '/tmp/direct.fcstm');
        assert.equal(packageModule.getDocumentFilePath(directDocument), '/tmp/direct.fcstm');

        const uriDocument = {
            getText() {
                return 'state Root;';
            },
            lineCount: 1,
            lineAt() {
                return {text: 'state Root;'};
            },
            uri: {
                fsPath: '/tmp/from-uri.fcstm',
            },
        };
        assert.equal(packageModule.getDocumentFilePath(uriDocument), '/tmp/from-uri.fcstm');
    });

    it('handles token and node range helpers', () => {
        const document = createDocument('state Root;', '/tmp/range.fcstm');

        assert.equal(packageModule.tokenText(undefined), '');
        assert.equal(packageModule.tokenText({text: 'Root'}), 'Root');
        assert.equal(packageModule.makeTokenRange(undefined, document), undefined);
        assert.equal(packageModule.makeNodeRange({}, document), undefined);

        const tokenRange = packageModule.makeTokenRange({line: 1, column: 6, text: 'Root'}, document);
        assert.deepEqual(tokenRange, packageModule.createRange(0, 6, 0, 10));

        const nodeRange = packageModule.makeNodeRange({
            start: {line: 1, column: 0, text: 'state'},
            stop: {line: 1, column: 6, text: 'Root'},
        }, document);
        assert.deepEqual(nodeRange, packageModule.createRange(0, 0, 0, 10));
    });

    it('finds fallback ranges and position containment', () => {
        const text = ['def int counter = 0;', 'state Root;'].join('\n');
        const document = createDocument(text, '/tmp/fallback.fcstm');

        const found = packageModule.fallbackRangeFromText(document, text, 'counter');
        assert.deepEqual(found, packageModule.createRange(0, 8, 0, 15));

        const fallback = packageModule.fallbackRangeFromText(document, text, 'missing');
        assert.deepEqual(fallback, packageModule.createRange(0, 0, 0, 1));

        assert.equal(packageModule.rangeContains(found, {line: 0, character: 10}), true);
        assert.equal(packageModule.rangeContains(found, {line: 1, character: 0}), false);
    });
});

describe('jsfcstm parser and diagnostics', () => {
    it('parses valid documents and exposes a singleton parser', async () => {
        const parser = packageModule.getParser();
        assert.equal(parser.isAvailable(), true);
        assert.equal(packageModule.getParser(), parser);

        const parseResult = await parser.parse('def int counter = 0;\nstate Root;');
        assert.equal(parseResult.success, true);
        assert.equal(parseResult.errors.length, 0);

        const tree = await parser.parseTree('state Root;');
        assert.ok(tree);
    });

    it('normalizes syntax errors into user-facing diagnostics', async () => {
        const parser = packageModule.getParser();
        const parseResult = await parser.parse('def int counter = 0\nstate Root;');
        assert.equal(parseResult.success, false);
        assert.ok(parseResult.errors.some(item => /semicolon/i.test(item.message)));
    });

    it('converts parse errors into stable document diagnostics', () => {
        const document = createDocument('state Root;', '/tmp/diagnostic.fcstm');
        const diagnostic = packageModule.convertParseErrorToDiagnostic({
            line: 0,
            column: 6,
            message: 'Broken symbol',
            severity: 'error',
        }, document);
        assert.deepEqual(diagnostic.range, packageModule.createRange(0, 6, 0, 10));
        assert.equal(diagnostic.source, 'fcstm');

        const punctuationDiagnostic = packageModule.convertParseErrorToDiagnostic({
            line: 0,
            column: 5,
            message: 'Punctuation issue',
            severity: 'warning',
        }, document);
        assert.deepEqual(punctuationDiagnostic.range, packageModule.createRange(0, 5, 0, 6));
        assert.equal(punctuationDiagnostic.severity, 'warning');
    });

    it('collects parse and import diagnostics together', async () => {
        const dir = trackTempDir('jsfcstm-diagnostics-');
        const missingPath = path.join(dir, 'missing.fcstm');
        const brokenDocument = createDocument('def int counter = 0\nstate Root;', path.join(dir, 'broken.fcstm'));
        const missingImportDocument = createDocument(
            'state Root {\n    import "./missing.fcstm" as Missing;\n}',
            path.join(dir, 'imports.fcstm')
        );

        const parseDiagnostics = await packageModule.collectDocumentDiagnostics(brokenDocument);
        assert.ok(parseDiagnostics.some(item => /semicolon/i.test(item.message)));

        const importDiagnostics = await packageModule.collectDocumentDiagnostics(missingImportDocument);
        assert.ok(importDiagnostics.some(item => item.message.includes(path.basename(missingPath))));
    });
});

describe('jsfcstm import workspace support', () => {
    it('resolves direct files, directory imports, and missing references', () => {
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

        const missing = packageModule.resolveImportReference(path.join(dir, 'host.fcstm'), './missing');
        assert.equal(missing.exists, false);
        assert.equal(missing.missing, true);
    });

    it('parses imports, variables, root state names, and root absolute events', async () => {
        const dir = trackTempDir('jsfcstm-parse-imports-');
        const hostFile = path.join(dir, 'host.fcstm');
        const text = [
            'def int counter = 0;',
            'state Root {',
            '    event Start;',
            '    state Host {',
            '        import "./worker.fcstm" as Worker;',
            '    }',
            '}',
        ].join('\n');
        const document = createDocument(text, hostFile);
        const importIndex = new packageModule.FcstmImportWorkspaceIndex();

        const parsed = await importIndex.parseDocument(document);
        assert.deepEqual(parsed.explicitVariables, ['counter']);
        assert.equal(parsed.rootStateName, 'Root');
        assert.deepEqual(parsed.absoluteEvents, ['/Start']);
        assert.equal(parsed.imports.length, 1);
        assert.equal(parsed.imports[0].alias, 'Worker');
        assert.deepEqual(parsed.imports[0].statePath, ['Root', 'Host']);
    });

    it('resolves imported summaries and import targets at a cursor position', async () => {
        const dir = trackTempDir('jsfcstm-import-targets-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        writeFile(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

        const text = 'state Root {\n    import "./worker.fcstm" as Worker;\n}';
        const document = createDocument(text, hostFile);
        const importIndex = new packageModule.FcstmImportWorkspaceIndex();

        const resolved = await importIndex.resolveImportsForDocument(document);
        assert.equal(resolved.length, 1);
        assert.equal(resolved[0].entryFile, workerFile);
        assert.equal(resolved[0].rootStateName, 'Worker');
        assert.deepEqual(resolved[0].explicitVariables, ['speed']);
        assert.deepEqual(resolved[0].absoluteEvents, ['/Start']);

        const atPosition = await importIndex.getResolvedImportAtPosition(document, {line: 1, character: 15});
        assert.ok(atPosition);
        assert.equal(atPosition.entry.alias, 'Worker');
        assert.equal(atPosition.target.entryFile, workerFile);
    });

    it('reports duplicate aliases and circular imports', async () => {
        const dir = trackTempDir('jsfcstm-import-diagnostics-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        writeFile(workerFile, 'state Worker;');

        const duplicateDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '    import "./worker.fcstm" as Worker;',
            '}',
        ].join('\n'), hostFile);

        const importIndex = new packageModule.FcstmImportWorkspaceIndex();
        const duplicateDiagnostics = await importIndex.collectImportDiagnostics(duplicateDocument);
        assert.ok(duplicateDiagnostics.some(item => /Duplicate import alias/.test(item.message)));

        writeFile(path.join(dir, 'a.fcstm'), 'state A { import "./b.fcstm" as B; }');
        writeFile(path.join(dir, 'b.fcstm'), 'state B { import "./a.fcstm" as A; }');
        const cycleDocument = createDocument(
            fs.readFileSync(path.join(dir, 'a.fcstm'), 'utf8'),
            path.join(dir, 'a.fcstm')
        );

        const cycleDiagnostics = await importIndex.collectImportDiagnostics(cycleDocument);
        assert.ok(cycleDiagnostics.some(item => /circular import/i.test(item.message)));
    });
});

describe('jsfcstm symbol extraction', () => {
    it('collects flattened symbol names from parse trees', async () => {
        const tree = await packageModule.getParser().parseTree([
            'def int counter = 0;',
            'state Root {',
            '    event Start;',
            '    state Child;',
            '}',
        ].join('\n'));

        const symbols = packageModule.collectSymbolsFromTree(tree);
        assert.deepEqual(symbols.variables, ['counter']);
        assert.deepEqual(symbols.states.sort(), ['Child', 'Root']);
        assert.deepEqual(symbols.events, ['Start']);
    });

    it('extracts nested document symbols', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root {',
            '    event Start;',
            '    pseudo state Junction;',
            '    state Child;',
            '}',
        ].join('\n'), '/tmp/symbols.fcstm');

        const symbols = await packageModule.collectDocumentSymbols(document);
        assert.equal(symbols.length, 2);
        assert.equal(symbols[0].name, 'counter');
        assert.equal(symbols[0].kind, 'variable');
        assert.equal(symbols[1].name, 'Root');
        assert.equal(symbols[1].kind, 'class');
        assert.ok(symbols[1].children.some(item => item.name === 'Start' && item.kind === 'event'));
        assert.ok(symbols[1].children.some(item => item.name === 'Junction' && item.detail === 'pseudo state'));
        assert.ok(symbols[1].children.some(item => item.name === 'Child' && item.kind === 'class'));
    });
});

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
        const importBlockDocument = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker {',
            '        ',
            '    }',
            '}',
        ].join('\n'), hostFile);

        const beforeAlias = await packageModule.collectCompletionItems(beforeAliasDocument, {line: 1, character: 27});
        assert.ok(beforeAlias.some(item => item.label === 'as' && item.kind === 'keyword'));

        const beforeNamed = await packageModule.collectCompletionItems(beforeNamedDocument, {line: 1, character: 37});
        assert.ok(beforeNamed.some(item => item.label === 'named' && item.kind === 'keyword'));

        const importBlock = await packageModule.collectCompletionItems(importBlockDocument, {line: 2, character: 8});
        assert.ok(importBlock.some(item => item.label === 'def' && item.kind === 'keyword'));
        assert.ok(importBlock.some(item => item.label === 'event' && item.kind === 'keyword'));
        assert.ok(importBlock.some(item => item.label === 'speed' && item.kind === 'variable'));
        assert.ok(importBlock.some(item => item.label === '/Start' && item.kind === 'event'));

        const generalDocument = createDocument('def int counter = 0;\nstate Root;', '/tmp/general.fcstm');
        const generalItems = await packageModule.collectCompletionItems(generalDocument, {line: 1, character: 5});
        assert.ok(generalItems.some(item => item.label === 'state' && item.kind === 'keyword'));
        assert.ok(generalItems.some(item => item.label === 'pi' && item.kind === 'constant'));
        assert.ok(generalItems.some(item => item.label === 'sin' && item.kind === 'function'));
        assert.ok(generalItems.some(item => item.label === 'counter' && item.kind === 'variable'));
        assert.ok(generalItems.some(item => item.label === 'Root' && item.kind === 'class'));
    });
});

describe('jsfcstm hover support', () => {
    it('finds hover docs for operators and keywords', () => {
        const localEventLine = 'StateA -> StateB :: LocalEvent;';
        const chainEventLine = 'StateA -> StateB :ChainEvent;';
        const absoluteEventLine = 'StateA -> StateB : /GlobalEvent;';
        const pseudoStateLine = '[*] -> Root;';
        const localEventHover = packageModule.findHoverInfo(localEventLine, localEventLine.indexOf('::'), '');
        assert.equal(localEventHover.title, 'Local Event Scope');

        const chainEventHover = packageModule.findHoverInfo(chainEventLine, chainEventLine.indexOf(':'), '');
        assert.equal(chainEventHover.title, 'Chain Event Scope');

        const absoluteEventHover = packageModule.findHoverInfo(
            absoluteEventLine,
            absoluteEventLine.indexOf('/'),
            ''
        );
        assert.equal(absoluteEventHover.title, 'Absolute Event Scope');

        const pseudoStateHover = packageModule.findHoverInfo(pseudoStateLine, pseudoStateLine.indexOf('[*]') + 1, '');
        assert.equal(pseudoStateHover.title, 'Pseudo-State Marker');

        const keywordHover = packageModule.findHoverInfo('state Root;', 2, 'state');
        assert.equal(keywordHover.title, 'State Definition');
    });

    it('resolves documentation and import hovers', async () => {
        const dir = trackTempDir('jsfcstm-hover-');
        const workerFile = path.join(dir, 'worker.fcstm');
        const hostFile = path.join(dir, 'host.fcstm');
        writeFile(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

        const keywordDocument = createDocument('state Root;', hostFile);
        const keywordHover = await packageModule.resolveHover(keywordDocument, {line: 0, character: 2});
        assert.equal(keywordHover.kind, 'doc');
        assert.equal(keywordHover.doc.title, 'State Definition');

        const importDocument = createDocument(
            'state Root {\n    import "./worker.fcstm" as Worker;\n}',
            hostFile
        );
        const importHover = await packageModule.resolveHover(importDocument, {line: 1, character: 15});
        assert.equal(importHover.kind, 'import');
        assert.equal(importHover.rootStateName, 'Worker');
        assert.deepEqual(importHover.explicitVariables, ['speed']);
        assert.deepEqual(importHover.absoluteEvents, ['/Start']);

        const nullHover = await packageModule.resolveHover(keywordDocument, {line: 0, character: 10});
        assert.equal(nullHover, null);
    });
});

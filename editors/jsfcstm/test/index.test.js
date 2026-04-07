const assert = require('node:assert/strict');
const fs = require('node:fs');
const os = require('node:os');
const path = require('node:path');

const packageJson = require('../package.json');
const packageModule = require('../dist/index.js');

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

async function runTest(name, fn) {
    await fn();
    console.log(`ok - ${name}`);
}

async function testPackageInfo() {
    const info = packageModule.getJsFcstmPackageInfo();
    assert.equal(info.name, packageJson.name);
    assert.equal(info.version, packageJson.version);
    assert.equal(info.description, packageJson.description);
    assert.equal(packageModule.JSFCSTM_PACKAGE_NAME, packageJson.name);
    assert.equal(packageModule.JSFCSTM_PACKAGE_VERSION, packageJson.version);
}

async function testParserAndDiagnostics() {
    const parser = packageModule.getParser();
    const parseResult = await parser.parse('def int counter = 0;\nstate Root;');
    assert.equal(parseResult.success, true);
    assert.equal(parseResult.errors.length, 0);

    const brokenDocument = createDocument('def int counter = 0\nstate Root;', path.join(process.cwd(), 'broken.fcstm'));
    const diagnostics = await packageModule.collectDocumentDiagnostics(brokenDocument);
    assert.ok(diagnostics.some(item => /semicolon/i.test(item.message)));
}

async function testDocumentSymbols() {
    const document = createDocument(
        [
            'def int counter = 0;',
            'state Root {',
            '    event Start;',
            '    state Child;',
            '}',
        ].join('\n'),
        path.join(process.cwd(), 'symbols.fcstm')
    );

    const symbols = await packageModule.collectDocumentSymbols(document);
    assert.equal(symbols.length, 2);
    assert.equal(symbols[0].name, 'counter');
    assert.equal(symbols[0].kind, 'variable');
    assert.equal(symbols[1].name, 'Root');
    assert.equal(symbols[1].kind, 'class');
    assert.ok(symbols[1].children.some(item => item.name === 'Start' && item.kind === 'event'));
    assert.ok(symbols[1].children.some(item => item.name === 'Child' && item.kind === 'class'));
}

async function testImportsAndDiagnostics() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jsfcstm-imports-'));
    const workerFile = path.join(dir, 'worker.fcstm');
    const hostFile = path.join(dir, 'host.fcstm');
    fs.writeFileSync(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

    const hostText = 'state Root {\n    import "./worker.fcstm" as Worker;\n}';
    const hostDocument = createDocument(hostText, hostFile);

    const importIndex = new packageModule.FcstmImportWorkspaceIndex();
    const resolved = await importIndex.resolveImportsForDocument(hostDocument);
    assert.equal(resolved.length, 1);
    assert.equal(resolved[0].entryFile, workerFile);
    assert.equal(resolved[0].rootStateName, 'Worker');
    assert.ok(resolved[0].explicitVariables.includes('speed'));
    assert.ok(resolved[0].absoluteEvents.includes('/Start'));

    fs.writeFileSync(path.join(dir, 'a.fcstm'), 'state A { import "./b.fcstm" as B; }');
    fs.writeFileSync(path.join(dir, 'b.fcstm'), 'state B { import "./a.fcstm" as A; }');
    const cycleDocument = createDocument(fs.readFileSync(path.join(dir, 'a.fcstm'), 'utf8'), path.join(dir, 'a.fcstm'));
    const cycleDiagnostics = await importIndex.collectImportDiagnostics(cycleDocument);
    assert.ok(cycleDiagnostics.some(item => /circular import/i.test(item.message)));
}

async function testCompletionAndHover() {
    const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'jsfcstm-completion-'));
    const workerFile = path.join(dir, 'worker.fcstm');
    const hostFile = path.join(dir, 'host.fcstm');
    fs.writeFileSync(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');

    const hostText = [
        'state Root {',
        '    import "./worker.fcstm" as Worker {',
        '        ',
        '    }',
        '}',
    ].join('\n');
    const hostDocument = createDocument(hostText, hostFile);

    const completionItems = await packageModule.collectCompletionItems(hostDocument, {line: 2, character: 8});
    assert.ok(completionItems.some(item => item.label === 'speed' && item.kind === 'variable'));
    assert.ok(completionItems.some(item => item.label === '/Start' && item.kind === 'event'));

    const hoverDoc = await packageModule.resolveHover(hostDocument, {line: 0, character: 3});
    assert.ok(hoverDoc);
    assert.equal(hoverDoc.kind, 'doc');
    assert.equal(hoverDoc.doc.title, 'State Definition');

    const importHoverDocument = createDocument(
        'state Root {\n    import "./worker.fcstm" as Worker;\n}',
        hostFile
    );
    const importHover = await packageModule.resolveHover(importHoverDocument, {line: 1, character: 15});
    assert.ok(importHover);
    assert.equal(importHover.kind, 'import');
    assert.equal(importHover.rootStateName, 'Worker');
}

async function main() {
    await runTest('package info exports package metadata', testPackageInfo);
    await runTest('parser and diagnostics work from jsfcstm', testParserAndDiagnostics);
    await runTest('document symbols are extracted in jsfcstm', testDocumentSymbols);
    await runTest('import resolution and diagnostics live in jsfcstm', testImportsAndDiagnostics);
    await runTest('completion and hover are resolved in jsfcstm', testCompletionAndHover);
    console.log('jsfcstm unit tests passed');
}

main().catch(error => {
    console.error(error);
    process.exit(1);
});

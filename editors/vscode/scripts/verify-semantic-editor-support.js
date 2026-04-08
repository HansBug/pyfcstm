#!/usr/bin/env node

/**
 * Semantic editor support verification for the bundled jsfcstm-based extension.
 *
 * This script validates the editor behaviors that now live in @pyfcstm/jsfcstm:
 * - scope-aware completion for states and imported aliases
 * - event declaration keyword hits resolve to the same event identity
 * - import aliases and import paths participate in references/highlights/definition
 */

const fs = require('fs');
const os = require('os');
const path = require('path');

const {
    collectCompletionItems,
    collectDocumentHighlights,
    collectReferences,
    getWorkspaceGraph,
    resolveDefinitionLocation,
} = require('@pyfcstm/jsfcstm');

const {pathToFileURL} = require('url');

const colors = {
    reset: '\x1b[0m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    cyan: '\x1b[36m',
    yellow: '\x1b[33m',
};

const CHECKMARK = '✅';
const CROSSMARK = '❌';

let passed = 0;
let failed = 0;

class MockDocument {
    constructor(filePath, text) {
        this.filePath = filePath;
        this.uri = {
            fsPath: filePath,
            toString() {
                return pathToFileURL(filePath).toString();
            },
        };
        this.languageId = 'fcstm';
        this.version = 1;
        this.text = text;
        this.lines = text.split('\n');
        this.lineCount = this.lines.length;
    }

    getText() {
        return this.text;
    }

    lineAt(line) {
        return {
            text: this.lines[line] || '',
        };
    }
}

class TestCase {
    constructor(id, description, testFn) {
        this.id = id;
        this.description = description;
        this.testFn = testFn;
    }
}

function assert(condition, message) {
    if (!condition) {
        throw new Error(message);
    }
}

function charOf(document, line, marker, offset = 0) {
    const index = document.lineAt(line).text.indexOf(marker);
    if (index < 0) {
        throw new Error(`Marker ${JSON.stringify(marker)} not found on line ${line}`);
    }
    return index + offset;
}

function writeFile(filePath, text) {
    fs.mkdirSync(path.dirname(filePath), {recursive: true});
    fs.writeFileSync(filePath, text);
}

function makeTempDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'fcstm-vscode-semantic-'));
}

async function runTest(testCase) {
    try {
        getWorkspaceGraph().clearOverlays();
        await testCase.testFn();
        console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        passed++;
        return true;
    } catch (error) {
        console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
        if (error.stack) {
            const stackLines = error.stack.split('\n').slice(1, 4);
            stackLines.forEach(line => console.log(`  ${colors.yellow}${line.trim()}${colors.reset}`));
        }
        failed++;
        return false;
    } finally {
        getWorkspaceGraph().clearOverlays();
    }
}

const tests = [
    new TestCase(
        'SEM-01',
        'Completion for transition targets stays within the current scope and excludes outside/deep states',
        async () => {
            const document = new MockDocument('/tmp/verify-semantic-scope.fcstm', [
                'state Root {',
                '    import "./root.fcstm" as RootWorker;',
                '    state Parent {',
                '        import "./parent.fcstm" as ParentWorker;',
                '        state Leaf;',
                '        state Hidden {',
                '            state DeepHidden;',
                '        }',
                '        Leaf -> ',
                '    }',
                '    state Outside {',
                '        import "./outside.fcstm" as OutsideWorker;',
                '        state DeepOutside;',
                '    }',
                '}',
            ].join('\n'));

            const items = await collectCompletionItems(document, {
                line: 8,
                character: document.lineAt(8).text.length,
            });
            const labels = new Set(items.map(item => item.label));

            assert(labels.has('Leaf'), 'Direct child state should be suggested');
            assert(labels.has('Hidden'), 'Sibling child state should be suggested');
            assert(labels.has('ParentWorker'), 'Current scope import alias should be suggested');
            assert(!labels.has('Parent'), 'Current scope state should not be suggested as a transition target');
            assert(!labels.has('DeepHidden'), 'Deep child state should not be suggested');
            assert(!labels.has('Outside'), 'Outer sibling state should not be suggested');
            assert(!labels.has('RootWorker'), 'Ancestor import alias should not be suggested');
            assert(!labels.has('OutsideWorker'), 'Outside scope import alias should not be suggested');
            assert(!labels.has('DeepOutside'), 'Outside deep state should not be suggested');
        }
    ),
    new TestCase(
        'SEM-02',
        'Clicking the event declaration keyword resolves highlights and references for the same event identity',
        async () => {
            const document = new MockDocument('/tmp/verify-semantic-events.fcstm', [
                'state Root {',
                '    event Start;',
                '    state Idle;',
                '    state Running;',
                '    [*] -> Idle;',
                '    Idle -> Running : Start;',
                '    Running -> Idle : /Start;',
                '}',
            ].join('\n'));

            const highlights = await collectDocumentHighlights(document, {
                line: 1,
                character: charOf(document, 1, 'event') + 1,
            });
            assert(highlights.length === 3, `Expected 3 highlights, got ${highlights.length}`);
            assert(highlights.some(item => item.kind === 'text'), 'Definition highlight should be included');
            assert(highlights.some(item => item.kind === 'read'), 'Reference highlights should be included');

            const references = await collectReferences(document, {
                line: 1,
                character: charOf(document, 1, 'event') + 1,
            });
            assert(references.length === 3, `Expected 3 references, got ${references.length}`);
        }
    ),
    new TestCase(
        'SEM-03',
        'Import alias references and import path clicks share references/highlights and jump to the imported module root',
        async () => {
            const dir = makeTempDir();
            const workerFile = path.join(dir, 'worker.fcstm');
            const hostFile = path.join(dir, 'host.fcstm');

            writeFile(workerFile, [
                'state WorkerRoot {',
                '    state Idle;',
                '}',
            ].join('\n'));

            const document = new MockDocument(hostFile, [
                'state Root {',
                '    import "./worker.fcstm" as Worker;',
                '    [*] -> Worker;',
                '    Worker -> Worker;',
                '}',
            ].join('\n'));

            const aliasDefinition = await resolveDefinitionLocation(document, {
                line: 2,
                character: charOf(document, 2, 'Worker') + 1,
            });
            assert(aliasDefinition, 'Alias usage should resolve to a definition');
            assert(aliasDefinition.uri === pathToFileURL(workerFile).toString(), 'Alias usage should jump to imported file');
            assert(aliasDefinition.range.start.line === 0, 'Imported definition should point at the imported root start');

            const pathDefinition = await resolveDefinitionLocation(document, {
                line: 1,
                character: charOf(document, 1, './worker.fcstm') + 2,
            });
            assert(pathDefinition, 'Import path should resolve to a definition');
            assert(pathDefinition.uri === pathToFileURL(workerFile).toString(), 'Import path should jump to imported file');

            const pathHighlights = await collectDocumentHighlights(document, {
                line: 1,
                character: charOf(document, 1, './worker.fcstm') + 2,
            });
            assert(pathHighlights.length === 5, `Expected 5 import highlights, got ${pathHighlights.length}`);

            const pathReferences = await collectReferences(document, {
                line: 1,
                character: charOf(document, 1, './worker.fcstm') + 2,
            });
            assert(pathReferences.length === 5, `Expected 5 import references, got ${pathReferences.length}`);
        }
    ),
];

async function main() {
    console.log(`${colors.cyan}FCSTM VSCode Semantic Editor Support Verification${colors.reset}`);
    console.log(`${colors.cyan}=================================================${colors.reset}`);

    for (const testCase of tests) {
        await runTest(testCase);
    }

    console.log();
    console.log(`${colors.cyan}Summary${colors.reset}`);
    console.log(`${colors.cyan}-------${colors.reset}`);
    console.log(`Total checkpoints: ${tests.length}`);
    console.log(`Passed: ${passed}`);
    console.log(`Failed: ${failed}`);

    if (failed === 0) {
        console.log(`${colors.green}All semantic editor support verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    }

    console.log(`${colors.red}Some semantic editor support verification checkpoints failed.${colors.reset}`);
    process.exit(1);
}

main().catch(error => {
    console.error(`${colors.red}${error.stack || error.message}${colors.reset}`);
    process.exit(1);
});

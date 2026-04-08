#!/usr/bin/env node

/**
 * Semantic editor support verification for the bundled jsfcstm-based extension.
 *
 * This script validates the editor behaviors that now live in @pyfcstm/jsfcstm:
 * - scope-aware completion for states and imported aliases
 * - incomplete target edits keep semantic completion alive
 * - partial symbols typed on empty lines still surface visible state and event symbols
 * - event declaration keyword hits resolve to the same event identity
 * - import aliases and import paths participate in references/highlights/definition
 * - import event mappings participate in state/event references and definitions
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
    new TestCase(
        'SEM-04',
        'Import event mappings resolve to local and imported event/state definitions',
        async () => {
            const dir = makeTempDir();
            const motorFile = path.join(dir, 'modules', 'motor.fcstm');
            const hostFile = path.join(dir, 'fleet.fcstm');

            writeFile(motorFile, [
                'state Motor {',
                '    event Start;',
                '    state Bus {',
                '        event Stop;',
                '        event Alarm;',
                '    }',
                '}',
            ].join('\n'));

            const document = new MockDocument(hostFile, [
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
            ].join('\n'));

            const hostStartTarget = await collectReferences(document, {
                line: 7,
                character: document.lineAt(7).text.indexOf('Start', document.lineAt(7).text.indexOf('->')) + 1,
            });
            assert(hostStartTarget.length === 3, `Expected 3 local Start references, got ${hostStartTarget.length}`);

            const hostStopDefinition = await resolveDefinitionLocation(document, {
                line: 8,
                character: document.lineAt(8).text.lastIndexOf('Stop') + 1,
            });
            assert(hostStopDefinition, 'Mapped local Stop should resolve to a definition');
            assert(hostStopDefinition.uri === pathToFileURL(hostFile).toString(), 'Mapped local Stop should resolve in the host file');
            assert(hostStopDefinition.range.start.line === 3, 'Mapped local Stop should point at state Bus event Stop');

            const hostBusDefinition = await resolveDefinitionLocation(document, {
                line: 8,
                character: document.lineAt(8).text.indexOf('Bus', document.lineAt(8).text.indexOf('->')) + 1,
            });
            assert(hostBusDefinition, 'Mapped /Bus.Stop state segment should resolve to a definition');
            assert(hostBusDefinition.uri === pathToFileURL(hostFile).toString(), 'Mapped Bus segment should resolve in the host file');
            assert(hostBusDefinition.range.start.line === 2, 'Mapped Bus segment should point at state Bus');

            const importedStopDefinition = await resolveDefinitionLocation(document, {
                line: 8,
                character: document.lineAt(8).text.indexOf('Stop') + 1,
            });
            assert(importedStopDefinition, 'Imported source Stop should resolve to a definition');
            assert(importedStopDefinition.uri === pathToFileURL(motorFile).toString(), 'Imported source Stop should jump to the imported file');
            assert(importedStopDefinition.range.start.line === 3, 'Imported source Stop should point at imported event Stop');
        }
    ),
    new TestCase(
        'SEM-05',
        'User-reported incomplete target edits still get scope-correct completions',
        async () => {
            const baseText = [
                'def int a = 0;',
                'def int b = 0x0 * 0;',
                'def int round_count = 0;  // define variables',
                'state TrafficLight {',
                '    state InService {',
                '        state Red;',
                '        state Yellow;',
                '        state Green;',
                '        Green -> Yellow effect {',
                '        };',
                '    }',
                '    state Idle;',
                '    [*] -> InService;',
                '    InService -> Idle :: Maintain;',
                '    Idle -> Idle :: E2;',
                '    Idle -> [*];',
                '}',
            ].join('\n');

            const rootDocument = new MockDocument('/tmp/verify-semantic-root-target.fcstm', baseText.replace(
                '    Idle -> [*];',
                '    Idle -> Id'
            ));
            const rootLine = rootDocument.lineCount - 2;
            const rootItems = await collectCompletionItems(rootDocument, {
                line: rootLine,
                character: rootDocument.lineAt(rootLine).text.length,
            });
            const rootLabels = new Set(rootItems.map(item => item.label));
            assert(rootLabels.has('Idle'), 'Top-level target completion should include Idle');
            assert(rootLabels.has('InService'), 'Top-level target completion should include InService');
            assert(!rootLabels.has('Yellow'), 'Top-level target completion should not include nested Yellow');

            const nestedDocument = new MockDocument('/tmp/verify-semantic-nested-target.fcstm', baseText.replace(
                '        Green -> Yellow effect {',
                '        Green -> Yel effect {'
            ));
            const nestedLine = 8;
            const nestedItems = await collectCompletionItems(nestedDocument, {
                line: nestedLine,
                character: nestedDocument.lineAt(nestedLine).text.indexOf('Yel') + 'Yel'.length,
            });
            const nestedLabels = new Set(nestedItems.map(item => item.label));
            assert(nestedLabels.has('Yellow'), 'Nested target completion should include Yellow');
            assert(nestedLabels.has('Red'), 'Nested target completion should include Red');
            assert(nestedLabels.has('Green'), 'Nested target completion should include Green');
            assert(!nestedLabels.has('Idle'), 'Nested target completion should not include outer Idle');
        }
    ),
    new TestCase(
        'SEM-06',
        'Typing partial symbols on an otherwise empty line still suggests visible states and events',
        async () => {
            const rootDocument = new MockDocument('/tmp/verify-semantic-empty-line-root.fcstm', [
                'state Root {',
                '    state Idle;',
                '    event InitDone;',
                '    Id',
                '}',
            ].join('\n'));
            const rootItems = await collectCompletionItems(rootDocument, {
                line: 3,
                character: rootDocument.lineAt(3).text.length,
            });
            const rootLabels = new Set(rootItems.map(item => item.label));
            assert(rootLabels.has('Idle'), 'Blank-line root completion should include Idle');

            const eventDocument = new MockDocument('/tmp/verify-semantic-empty-line-event.fcstm', [
                'state Root {',
                '    event InitDone;',
                '    Ini',
                '}',
            ].join('\n'));
            const eventItems = await collectCompletionItems(eventDocument, {
                line: 2,
                character: eventDocument.lineAt(2).text.length,
            });
            const eventLabels = new Set(eventItems.map(item => item.label));
            assert(eventLabels.has('InitDone'), 'Blank-line completion should include visible events');

            const nestedDocument = new MockDocument('/tmp/verify-semantic-empty-line-nested.fcstm', [
                'state Root {',
                '    state InService {',
                '        state Yellow;',
                '        Yel',
                '    }',
                '}',
            ].join('\n'));
            const nestedItems = await collectCompletionItems(nestedDocument, {
                line: 3,
                character: nestedDocument.lineAt(3).text.length,
            });
            const nestedLabels = new Set(nestedItems.map(item => item.label));
            assert(nestedLabels.has('Yellow'), 'Blank-line nested completion should include Yellow');
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

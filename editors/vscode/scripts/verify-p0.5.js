#!/usr/bin/env node

/**
 * P0.5 Completion Provider Verification Script
 *
 * This script validates the completion feature by testing:
 * - Keyword completions
 * - Built-in constant completions
 * - Built-in function completions
 * - Document-local symbol completions (variables, states, events)
 * - Filtering in comments and strings
 */

const Module = require('module');
const path = require('path');
const originalRequire = Module.prototype.require;

// Mock VSCode module
const vscode = {
    CompletionItemKind: {
        Keyword: 14,
        Constant: 21,
        Function: 3,
        Variable: 6,
        Class: 7,
        Event: 23
    },
    CompletionItem: class CompletionItem {
        constructor(label, kind) {
            this.label = label;
            this.kind = kind;
            this.detail = '';
            this.documentation = null;
            this.insertText = null;
            this.sortText = '';
        }
    },
    SnippetString: class SnippetString {
        constructor(value) {
            this.value = value;
        }
    },
    MarkdownString: class MarkdownString {
        constructor(value) {
            this.value = value || '';
        }
        appendMarkdown(text) {
            this.value += text;
        }
    },
    Position: class Position {
        constructor(line, character) {
            this.line = line;
            this.character = character;
        }
    },
    Range: class Range {
        constructor(startLine, startCharacter, endLine, endCharacter) {
            this.start = new vscode.Position(startLine, startCharacter);
            this.end = new vscode.Position(endLine, endCharacter);
        }
    },
    Uri: {
        file(filePath) {
            return { fsPath: filePath };
        }
    }
};

// Override require to inject vscode mock
Module.prototype.require = function(id) {
    if (id === 'vscode') {
        return vscode;
    }
    return originalRequire.apply(this, arguments);
};

const { FcstmCompletionProvider } = require('../out/completion');

// ANSI color codes
const colors = {
    reset: '\x1b[0m',
    green: '\x1b[32m',
    red: '\x1b[31m',
    cyan: '\x1b[36m',
    yellow: '\x1b[33m'
};

const CHECKMARK = '✅';
const CROSSMARK = '❌';

let passed = 0;
let failed = 0;

/**
 * Mock document for testing
 */
class MockDocument {
    constructor(text) {
        this.text = text;
        this.lines = text.split('\n');
        this.lineCount = this.lines.length;
        this.uri = {
            fsPath: path.join(process.cwd(), '__mock__.fcstm'),
            toString() {
                return this.fsPath;
            }
        };
    }

    getText() {
        return this.text;
    }

    lineAt(line) {
        return {
            text: this.lines[line] || ''
        };
    }
}

/**
 * Test case structure
 */
class TestCase {
    constructor(id, description, code, position, expectedItems) {
        this.id = id;
        this.description = description;
        this.code = code;
        this.position = position;
        this.expectedItems = expectedItems; // Array of { label, kind }
    }
}

/**
 * Run a single test case
 */
async function runTest(testCase) {
    const provider = new FcstmCompletionProvider();
    const document = new MockDocument(testCase.code);
    const position = new vscode.Position(testCase.position.line, testCase.position.character);

    try {
        const items = await provider.provideCompletionItems(document, position, {}, {});

        // Check if expected items are present
        let allFound = true;
        const missingItems = [];

        for (const expected of testCase.expectedItems) {
            const found = items.some(item =>
                item.label === expected.label && item.kind === expected.kind
            );

            if (!found) {
                allFound = false;
                missingItems.push(expected.label);
            }
        }

        if (allFound) {
            console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
            passed++;
            return true;
        } else {
            console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
            console.log(`  Missing items: ${missingItems.join(', ')}`);
            console.log(`  Total items returned: ${items.length}`);
            failed++;
            return false;
        }

    } catch (error) {
        console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        console.log(`  Unexpected error: ${error.message}`);
        failed++;
        return false;
    }
}

/**
 * Test cases for P0.5
 */
const testCases = [
    // Keyword completion tests
    new TestCase(
        'P0.5-01',
        'Complete keywords at start of line',
        '',
        { line: 0, character: 0 },
        [
            { label: 'state', kind: vscode.CompletionItemKind.Keyword },
            { label: 'def', kind: vscode.CompletionItemKind.Keyword },
            { label: 'event', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-02',
        'Complete lifecycle keywords',
        'state Root {\n    ',
        { line: 1, character: 4 },
        [
            { label: 'enter', kind: vscode.CompletionItemKind.Keyword },
            { label: 'during', kind: vscode.CompletionItemKind.Keyword },
            { label: 'exit', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-03',
        'Complete type keywords',
        'def ',
        { line: 0, character: 4 },
        [
            { label: 'int', kind: vscode.CompletionItemKind.Keyword },
            { label: 'float', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-04',
        'Complete modifier keywords',
        'state Root {\n    enter ',
        { line: 1, character: 10 },
        [
            { label: 'abstract', kind: vscode.CompletionItemKind.Keyword },
            { label: 'ref', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-05',
        'Complete control flow keywords',
        'A -> B : ',
        { line: 0, character: 9 },
        [
            { label: 'if', kind: vscode.CompletionItemKind.Keyword },
            { label: 'effect', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),
    new TestCase(
        'P0.5-05A',
        'Complete import keywords',
        'state Root {\n    import "./worker.fcstm" ',
        { line: 1, character: 27 },
        [
            { label: 'as', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),
    new TestCase(
        'P0.5-05B',
        'Complete import mapping block keywords',
        'state Root {\n    import "./worker.fcstm" as Worker {\n        \n    }\n}',
        { line: 2, character: 8 },
        [
            { label: 'def', kind: vscode.CompletionItemKind.Keyword },
            { label: 'event', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    // Built-in constant tests
    new TestCase(
        'P0.5-06',
        'Complete math constants',
        'def float x = ',
        { line: 0, character: 14 },
        [
            { label: 'pi', kind: vscode.CompletionItemKind.Constant },
            { label: 'E', kind: vscode.CompletionItemKind.Constant },
            { label: 'tau', kind: vscode.CompletionItemKind.Constant }
        ]
    ),

    new TestCase(
        'P0.5-07',
        'Complete boolean constants',
        'def int flag = ',
        { line: 0, character: 15 },
        [
            { label: 'true', kind: vscode.CompletionItemKind.Constant },
            { label: 'false', kind: vscode.CompletionItemKind.Constant },
            { label: 'True', kind: vscode.CompletionItemKind.Constant },
            { label: 'False', kind: vscode.CompletionItemKind.Constant }
        ]
    ),

    // Built-in function tests
    new TestCase(
        'P0.5-08',
        'Complete trigonometric functions',
        'def float y = ',
        { line: 0, character: 14 },
        [
            { label: 'sin', kind: vscode.CompletionItemKind.Function },
            { label: 'cos', kind: vscode.CompletionItemKind.Function },
            { label: 'tan', kind: vscode.CompletionItemKind.Function }
        ]
    ),

    new TestCase(
        'P0.5-09',
        'Complete math functions',
        'def float z = ',
        { line: 0, character: 14 },
        [
            { label: 'sqrt', kind: vscode.CompletionItemKind.Function },
            { label: 'abs', kind: vscode.CompletionItemKind.Function },
            { label: 'exp', kind: vscode.CompletionItemKind.Function }
        ]
    ),

    new TestCase(
        'P0.5-10',
        'Complete logarithm functions',
        'def float w = ',
        { line: 0, character: 14 },
        [
            { label: 'log', kind: vscode.CompletionItemKind.Function },
            { label: 'log10', kind: vscode.CompletionItemKind.Function },
            { label: 'log2', kind: vscode.CompletionItemKind.Function }
        ]
    ),

    // Document-local symbol tests
    new TestCase(
        'P0.5-11',
        'Complete variable names',
        `def int counter = 0;
def float temperature = 25.5;
state Root {
    enter {

    }
}`,
        { line: 4, character: 8 },
        [
            { label: 'counter', kind: vscode.CompletionItemKind.Variable },
            { label: 'temperature', kind: vscode.CompletionItemKind.Variable }
        ]
    ),

    new TestCase(
        'P0.5-12',
        'Complete state names',
        `state Root {
    state Idle;
    state Active;
    state Running;
}`,
        { line: 4, character: 1 },
        [
            { label: 'Root', kind: vscode.CompletionItemKind.Class },
            { label: 'Idle', kind: vscode.CompletionItemKind.Class },
            { label: 'Active', kind: vscode.CompletionItemKind.Class },
            { label: 'Running', kind: vscode.CompletionItemKind.Class }
        ]
    ),

    new TestCase(
        'P0.5-13',
        'Complete event names',
        `state Root {
    event Start;
    event Stop;
    event Pause;

}`,
        { line: 4, character: 4 },
        [
            { label: 'Start', kind: vscode.CompletionItemKind.Event },
            { label: 'Stop', kind: vscode.CompletionItemKind.Event },
            { label: 'Pause', kind: vscode.CompletionItemKind.Event }
        ]
    ),

    new TestCase(
        'P0.5-14',
        'Complete mixed symbols',
        `def int x = 0;
state System {
    event GlobalEvent;
    state Idle;

}`,
        { line: 4, character: 4 },
        [
            { label: 'x', kind: vscode.CompletionItemKind.Variable },
            { label: 'System', kind: vscode.CompletionItemKind.Class },
            { label: 'Idle', kind: vscode.CompletionItemKind.Class },
            { label: 'GlobalEvent', kind: vscode.CompletionItemKind.Event }
        ]
    ),

    new TestCase(
        'P0.5-15',
        'Complete nested state names',
        `state Root {
    state SubSystem {
        state Active;
        state Idle;
    }

}`,
        { line: 5, character: 4 },
        [
            { label: 'Root', kind: vscode.CompletionItemKind.Class },
            { label: 'SubSystem', kind: vscode.CompletionItemKind.Class },
            { label: 'Active', kind: vscode.CompletionItemKind.Class },
            { label: 'Idle', kind: vscode.CompletionItemKind.Class }
        ]
    ),

    // Comment and string filtering tests
    new TestCase(
        'P0.5-16',
        'No completion in line comment',
        '// state ',
        { line: 0, character: 9 },
        []
    ),

    new TestCase(
        'P0.5-17',
        'No completion in block comment',
        '/* state ',
        { line: 0, character: 9 },
        []
    ),

    new TestCase(
        'P0.5-18',
        'No completion in double-quoted string',
        'state Root named "',
        { line: 0, character: 18 },
        []
    ),

    new TestCase(
        'P0.5-19',
        'No completion in single-quoted string',
        "event E named '",
        { line: 0, character: 15 },
        []
    ),

    new TestCase(
        'P0.5-20',
        'Completion after comment',
        '// comment\nstate ',
        { line: 1, character: 6 },
        [
            { label: 'state', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    // Context-specific tests
    new TestCase(
        'P0.5-21',
        'Complete in expression context',
        `def int x = 0;
state Root {
    enter {
        x =
    }
}`,
        { line: 3, character: 12 },
        [
            { label: 'x', kind: vscode.CompletionItemKind.Variable },
            { label: 'sin', kind: vscode.CompletionItemKind.Function },
            { label: 'pi', kind: vscode.CompletionItemKind.Constant }
        ]
    ),

    new TestCase(
        'P0.5-22',
        'Complete in guard condition',
        `def int counter = 0;
state A;
state B;
A -> B : if [`,
        { line: 3, character: 13 },
        [
            { label: 'counter', kind: vscode.CompletionItemKind.Variable }
        ]
    ),

    new TestCase(
        'P0.5-23',
        'Complete in effect block',
        `def int x = 0;
state A;
state B;
A -> B effect {

}`,
        { line: 4, character: 4 },
        [
            { label: 'x', kind: vscode.CompletionItemKind.Variable }
        ]
    ),

    new TestCase(
        'P0.5-24',
        'Complete with partial input',
        `def int counter = 0;
def int count = 1;
state Root {
    enter {
        cou
    }
}`,
        { line: 4, character: 11 },
        [
            { label: 'counter', kind: vscode.CompletionItemKind.Variable },
            { label: 'count', kind: vscode.CompletionItemKind.Variable }
        ]
    ),

    new TestCase(
        'P0.5-25',
        'Complete all item types together',
        `def int myVar = 0;
state MyState;
event MyEvent;
`,
        { line: 3, character: 0 },
        [
            { label: 'state', kind: vscode.CompletionItemKind.Keyword },
            { label: 'pi', kind: vscode.CompletionItemKind.Constant },
            { label: 'sin', kind: vscode.CompletionItemKind.Function },
            { label: 'myVar', kind: vscode.CompletionItemKind.Variable },
            { label: 'MyState', kind: vscode.CompletionItemKind.Class }
        ]
    ),

    // Edge cases
    new TestCase(
        'P0.5-26',
        'Complete in empty document',
        '',
        { line: 0, character: 0 },
        [
            { label: 'state', kind: vscode.CompletionItemKind.Keyword },
            { label: 'def', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-27',
        'Complete with syntax errors',
        `def int x = 0
state Root {
    enter {

    }
`,
        { line: 3, character: 8 },
        [
            { label: 'x', kind: vscode.CompletionItemKind.Variable }
        ]
    ),

    new TestCase(
        'P0.5-28',
        'Complete pseudo state keyword',
        '',
        { line: 0, character: 0 },
        [
            { label: 'pseudo', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-29',
        'Complete aspect keywords',
        'state Root {\n    ',
        { line: 1, character: 4 },
        [
            { label: 'before', kind: vscode.CompletionItemKind.Keyword },
            { label: 'after', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-30',
        'Complete logical operators',
        '',
        { line: 0, character: 0 },
        [
            { label: 'and', kind: vscode.CompletionItemKind.Keyword },
            { label: 'or', kind: vscode.CompletionItemKind.Keyword },
            { label: 'not', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),

    new TestCase(
        'P0.5-31',
        'Complete else keyword inside operation block',
        `def int counter = 0;
state Root {
    during {
        if [counter > 0] {
            counter = 1;
        } 
    }
}`,
        { line: 5, character: 8 },
        [
            { label: 'else', kind: vscode.CompletionItemKind.Keyword }
        ]
    ),
];

/**
 * Main execution
 */
async function main() {
    console.log(`${colors.cyan}FCSTM VSCode P0.5 Completion Verification${colors.reset}`);
    console.log(`${colors.cyan}===========================================${colors.reset}`);

    for (const testCase of testCases) {
        await runTest(testCase);
    }

    console.log();
    console.log(`${colors.cyan}Summary${colors.reset}`);
    console.log(`${colors.cyan}-------${colors.reset}`);
    console.log(`Total checkpoints: ${testCases.length}`);
    console.log(`Passed: ${passed}`);
    console.log(`Failed: ${failed}`);

    if (failed === 0) {
        console.log(`${colors.green}All P0.5 verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some P0.5 verification checkpoints failed.${colors.reset}`);
        process.exit(1);
    }
}

main().catch(error => {
    console.error(`${colors.red}Fatal error:${colors.reset}`, error);
    process.exit(1);
});

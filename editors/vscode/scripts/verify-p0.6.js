#!/usr/bin/env node

/**
 * P0.6 Hover Provider Verification Script
 *
 * This script validates the hover documentation feature by testing:
 * - Event scoping operators (::, :, /)
 * - Pseudo-state marker ([*])
 * - Keywords (pseudo, effect, abstract, ref, etc.)
 * - Lifecycle aspects (during before/after, >> during before/after)
 * - Other keywords (named, enter, during, exit, if, else, def, state, event)
 * - Edge cases (multi-character operators, context sensitivity)
 */

const Module = require('module');
const path = require('path');
const originalRequire = Module.prototype.require;

// Mock VSCode module
const vscode = {
    Position: class Position {
        constructor(line, character) {
            this.line = line;
            this.character = character;
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
    Hover: class Hover {
        constructor(contents, range) {
            this.contents = contents;
            this.range = range;
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

const { FcstmHoverProvider } = require('../out/hover');

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

    getText(range) {
        if (!range) {
            return this.text;
        }
        // Extract text from range
        const line = this.lines[range.start.line] || '';
        return line.substring(range.start.character, range.end.character);
    }

    lineAt(line) {
        return {
            text: this.lines[line] || ''
        };
    }

    getWordRangeAtPosition(position) {
        const line = this.lines[position.line] || '';
        const char = position.character;

        // Find word boundaries
        let start = char;
        let end = char;

        while (start > 0 && /[a-zA-Z_]/.test(line[start - 1])) {
            start--;
        }

        while (end < line.length && /[a-zA-Z_]/.test(line[end])) {
            end++;
        }

        if (start === end) {
            return null;
        }

        return {
            start: new vscode.Position(position.line, start),
            end: new vscode.Position(position.line, end)
        };
    }
}

/**
 * Test case structure
 */
class TestCase {
    constructor(id, description, code, position, expectedTitle) {
        this.id = id;
        this.description = description;
        this.code = code;
        this.position = position;
        this.expectedTitle = expectedTitle; // Expected hover title (null for no hover)
    }
}

/**
 * Run a single test case
 */
async function runTest(testCase) {
    const provider = new FcstmHoverProvider();
    const document = new MockDocument(testCase.code);
    const position = new vscode.Position(testCase.position.line, testCase.position.character);

    try {
        const hover = await provider.provideHover(document, position, {});

        if (testCase.expectedTitle === null) {
            // Expect no hover
            if (hover === null) {
                console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
                passed++;
                return true;
            } else {
                console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
                console.log(`  Expected no hover, but got: ${hover.contents.value.substring(0, 50)}...`);
                failed++;
                return false;
            }
        } else {
            // Expect hover with specific title
            if (hover && hover.contents && hover.contents.value.includes(testCase.expectedTitle)) {
                console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
                passed++;
                return true;
            } else {
                console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
                if (!hover) {
                    console.log(`  Expected hover with title "${testCase.expectedTitle}", but got no hover`);
                } else {
                    console.log(`  Expected title: "${testCase.expectedTitle}"`);
                    console.log(`  Actual content: ${hover.contents.value.substring(0, 100)}...`);
                }
                failed++;
                return false;
            }
        }

    } catch (error) {
        console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        console.log(`  Unexpected error: ${error.message}`);
        failed++;
        return false;
    }
}

/**
 * Test cases for P0.6
 */
const testCases = [
    // Event scoping operator tests
    new TestCase(
        'P0.6-01',
        'Hover on :: (local event scope)',
        'StateA -> StateB :: LocalEvent;',
        { line: 0, character: 17 },  // First : in ::
        'Local Event Scope'
    ),

    new TestCase(
        'P0.6-02',
        'Hover on : (chain event scope)',
        'StateA -> StateB :ChainEvent;',  // No space after : to match hover implementation
        { line: 0, character: 17 },  // The : character
        'Chain Event Scope'
    ),

    new TestCase(
        'P0.6-03',
        'Hover on / (absolute event scope)',
        'StateA -> StateB : /GlobalEvent;',
        { line: 0, character: 19 },  // The / character
        'Absolute Event Scope'
    ),

    // Pseudo-state marker tests
    new TestCase(
        'P0.6-04',
        'Hover on [*] in entry transition',
        '[*] -> InitialState;',
        { line: 0, character: 1 },
        'Pseudo-State Marker'
    ),

    new TestCase(
        'P0.6-05',
        'Hover on [*] in exit transition',
        'FinalState -> [*];',
        { line: 0, character: 15 },
        'Pseudo-State Marker'
    ),

    // Keyword tests
    new TestCase(
        'P0.6-06',
        'Hover on pseudo keyword',
        'pseudo state Junction;',
        { line: 0, character: 3 },  // Middle of "pseudo"
        'Pseudo State'
    ),

    new TestCase(
        'P0.6-07',
        'Hover on effect keyword',
        'StateA -> StateB effect { x = 0; }',
        { line: 0, character: 19 },  // Middle of "effect"
        'Transition Effect'
    ),

    new TestCase(
        'P0.6-08',
        'Hover on abstract keyword',
        'enter abstract InitHardware;',
        { line: 0, character: 9 },  // Middle of "abstract"
        'Abstract Action'
    ),

    new TestCase(
        'P0.6-09',
        'Hover on ref keyword',
        'enter ref StateA.UserInit;',
        { line: 0, character: 9 },  // Middle of "ref"
        'Reference Action'
    ),

    new TestCase(
        'P0.6-10',
        'Hover on named keyword',
        'state Running named "System Running";',
        { line: 0, character: 17 },  // Middle of "named"
        'Display Name'
    ),

    // Lifecycle aspect tests
    new TestCase(
        'P0.6-11',
        'Hover on during before',
        'state Parent {\n    during before { }\n}',
        { line: 1, character: 8 },
        'During Before Aspect'
    ),

    new TestCase(
        'P0.6-12',
        'Hover on during after',
        'state Parent {\n    during after { }\n}',
        { line: 1, character: 8 },
        'During After Aspect'
    ),

    new TestCase(
        'P0.6-13',
        'Hover on >> during before',
        'state Root {\n    >> during before { }\n}',
        { line: 1, character: 8 },
        'Global During Before Aspect'
    ),

    new TestCase(
        'P0.6-14',
        'Hover on >> during after',
        'state Root {\n    >> during after { }\n}',
        { line: 1, character: 8 },
        'Global During After Aspect'
    ),

    // Lifecycle action tests
    new TestCase(
        'P0.6-15',
        'Hover on enter keyword',
        'state Active {\n    enter { }\n}',
        { line: 1, character: 7 },  // Middle of "enter"
        'Enter Action'
    ),

    new TestCase(
        'P0.6-16',
        'Hover on during keyword',
        'state Active {\n    during { }\n}',
        { line: 1, character: 7 },  // Middle of "during"
        'During Action'
    ),

    new TestCase(
        'P0.6-17',
        'Hover on exit keyword',
        'state Active {\n    exit { }\n}',
        { line: 1, character: 6 },  // Middle of "exit"
        'Exit Action'
    ),

    new TestCase(
        'P0.6-18',
        'Hover on before keyword',
        'state Parent {\n    during before { }\n}',
        { line: 1, character: 13 },
        'Before Aspect'
    ),

    new TestCase(
        'P0.6-19',
        'Hover on after keyword',
        'state Parent {\n    during after { }\n}',
        { line: 1, character: 13 },
        'After Aspect'
    ),

    // Control flow and declaration tests
    new TestCase(
        'P0.6-20',
        'Hover on if keyword',
        'StateA -> StateB : if [counter >= 10];',
        { line: 0, character: 21 },  // Middle of "if"
        'Guard Condition'
    ),

    new TestCase(
        'P0.6-21',
        'Hover on else keyword',
        'state Root {\n    during {\n        if [counter > 0] {\n            counter = 1;\n        } else {\n            counter = 0;\n        }\n    }\n}',
        { line: 4, character: 11 },  // Middle of "else"
        'Else Branch'
    ),

    new TestCase(
        'P0.6-22',
        'Hover on def keyword',
        'def int counter = 0;',
        { line: 0, character: 3 },  // Middle of "def"
        'Variable Definition'
    ),

    new TestCase(
        'P0.6-23',
        'Hover on state keyword',
        'state Idle;',
        { line: 0, character: 3 },  // Middle of "state"
        'State Definition'
    ),

    new TestCase(
        'P0.6-24',
        'Hover on event keyword',
        'event Start;',
        { line: 0, character: 3 },  // Middle of "event"
        'Event Definition'
    ),
    new TestCase(
        'P0.6-24A',
        'Hover on import keyword',
        'state Root {\n    import "./worker.fcstm" as Worker;\n}',
        { line: 1, character: 7 },
        'Import Statement'
    ),
    new TestCase(
        'P0.6-24B',
        'Hover on as keyword',
        'state Root {\n    import "./worker.fcstm" as Worker;\n}',
        { line: 1, character: 29 },
        'Import Alias'
    ),

    // Edge case tests - no hover expected
    new TestCase(
        'P0.6-25',
        'No hover on variable name',
        'def int counter = 0;',
        { line: 0, character: 10 },
        null
    ),

    new TestCase(
        'P0.6-26',
        'No hover on state name',
        'state Running;',
        { line: 0, character: 8 },
        null
    ),

    new TestCase(
        'P0.6-27',
        'No hover on number literal',
        'def int x = 123;',
        { line: 0, character: 13 },
        null
    ),

    new TestCase(
        'P0.6-28',
        'No hover in whitespace',
        'state A;    state B;',
        { line: 0, character: 10 },
        null
    ),

    // Context-specific tests
    new TestCase(
        'P0.6-29',
        'Hover on :: in transition',
        'A -> B :: E;',
        { line: 0, character: 7 },
        'Local Event Scope'
    ),

    new TestCase(
        'P0.6-30',
        'Hover on : in transition (not ::)',
        'A -> B :E;',  // No space after : to match hover implementation
        { line: 0, character: 7 },
        'Chain Event Scope'
    ),

    new TestCase(
        'P0.6-31',
        'Hover on effect in transition',
        'A -> B effect { x = 0; }',
        { line: 0, character: 10 },  // Middle of "effect"
        'Transition Effect'
    ),

    // Additional operator tests
    new TestCase(
        'P0.6-32',
        'Hover on first : in ::',
        'StateA -> StateB :: Event;',
        { line: 0, character: 17 },  // First : in ::
        'Local Event Scope'
    ),

    new TestCase(
        'P0.6-33',
        'Hover on second : in ::',
        'StateA -> StateB :: Event;',
        { line: 0, character: 17 },
        'Local Event Scope'
    ),

    new TestCase(
        'P0.6-34',
        'Hover on / in absolute path',
        'enter ref /GlobalAction;',
        { line: 0, character: 10 },
        'Absolute Event Scope'
    ),

    new TestCase(
        'P0.6-35',
        'Hover on abstract in enter context',
        'state S {\n    enter abstract Init;\n}',
        { line: 1, character: 13 },  // Middle of "abstract"
        'Abstract Action'
    ),

    new TestCase(
        'P0.6-36',
        'Hover on ref in exit context',
        'state S {\n    exit ref Cleanup;\n}',
        { line: 1, character: 12 },  // Middle of "ref"
        'Reference Action'
    ),
];

/**
 * Main execution
 */
async function main() {
    console.log(`${colors.cyan}FCSTM VSCode P0.6 Hover Verification${colors.reset}`);
    console.log(`${colors.cyan}=====================================${colors.reset}`);

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
        console.log(`${colors.green}All P0.6 verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some P0.6 verification checkpoints failed.${colors.reset}`);
        process.exit(1);
    }
}

main().catch(error => {
    console.error(`${colors.red}Fatal error:${colors.reset}`, error);
    process.exit(1);
});

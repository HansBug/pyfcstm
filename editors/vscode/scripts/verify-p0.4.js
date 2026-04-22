#!/usr/bin/env node

/**
 * P0.4 Document Symbols Verification Script
 *
 * This script validates the document symbols feature by testing:
 * - Variable symbol extraction
 * - State symbol extraction (leaf and composite)
 * - Pseudo state symbol extraction
 * - Event symbol extraction
 * - Nested state hierarchy
 * - Symbol names and details
 */

const Module = require('module');
const originalRequire = Module.prototype.require;

// Mock VSCode module
const vscode = {
    SymbolKind: {
        Module: 1,
        Class: 5,
        Function: 11,
        Variable: 13,
        Event: 24,
    },
    DocumentSymbol: class DocumentSymbol {
        constructor(name, detail, kind, range, selectionRange) {
            this.name = name;
            this.detail = detail;
            this.kind = kind;
            this.range = range;
            this.selectionRange = selectionRange;
            this.children = [];
        }
    },
    Range: class Range {
        constructor(start, end) {
            this.start = start;
            this.end = end;
        }
    },
    Position: class Position {
        constructor(line, character) {
            this.line = line;
            this.character = character;
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

const { FcstmParser } = require('../out/parser');
const { FcstmDocumentSymbolProvider } = require('../out/symbols');

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
 * Mock VSCode document for testing
 */
class MockDocument {
    constructor(text) {
        this.text = text;
        this.lines = text.split('\n');
        this.lineCount = this.lines.length;
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
    constructor(id, description, code, expectedSymbols) {
        this.id = id;
        this.description = description;
        this.code = code;
        this.expectedSymbols = expectedSymbols; // Array of { name, kind, detail?, children? }
    }
}

/**
 * Symbol kind enum (matching VSCode)
 */
const SymbolKind = vscode.SymbolKind;

// ---------------------------------------------------------------------------
// Builders for expected document-symbol trees.
//
// jsfcstm now groups state children into intermediate "module" containers:
//   <State>
//     Events (module)       -> list of event entries
//     Transitions (module)  -> list of transition entries
//     Actions (module)      -> Lifecycle / Aspects sub-groups
//         Lifecycle (module)
//         Aspects   (module)
//     States (module)       -> nested states
// ---------------------------------------------------------------------------

function plural(count, singular, pluralForm) {
    const word = count === 1 ? singular : (pluralForm || singular + 's');
    return `${count} ${word}`;
}

function variable(name, type) {
    return { name, kind: SymbolKind.Variable, detail: type };
}

function state(name, detail = '', children) {
    if (children === undefined) {
        return { name, kind: SymbolKind.Class, detail };
    }
    return { name, kind: SymbolKind.Class, detail, children };
}

function pseudoState(name) {
    return { name, kind: SymbolKind.Class, detail: 'pseudo state' };
}

function event(name, detail = '') {
    return { name, kind: SymbolKind.Event, detail };
}

function transition(label, detail) {
    return { name: label, kind: SymbolKind.Function, detail };
}

function actionEntry(name, detail) {
    return { name, kind: SymbolKind.Function, detail };
}

function eventsGroup(children) {
    return {
        name: 'Events',
        kind: SymbolKind.Module,
        detail: plural(children.length, 'event'),
        children,
    };
}

function transitionsGroup(children) {
    return {
        name: 'Transitions',
        kind: SymbolKind.Module,
        detail: plural(children.length, 'transition'),
        children,
    };
}

function statesGroup(children) {
    return {
        name: 'States',
        kind: SymbolKind.Module,
        detail: plural(children.length, 'state'),
        children,
    };
}

function lifecycleGroup(children) {
    return {
        name: 'Lifecycle',
        kind: SymbolKind.Module,
        detail: plural(children.length, 'action'),
        children,
    };
}

function aspectsGroup(children) {
    return {
        name: 'Aspects',
        kind: SymbolKind.Module,
        detail: plural(children.length, 'aspect'),
        children,
    };
}

function actionsGroup(children) {
    const total = children.reduce((n, g) => n + (g.children ? g.children.length : 0), 0);
    return {
        name: 'Actions',
        kind: SymbolKind.Module,
        detail: plural(total, 'action entry', 'action entries'),
        children,
    };
}

/**
 * Check if symbol matches expected
 */
function symbolMatches(actual, expected) {
    if (actual.name !== expected.name) {
        return { match: false, reason: `Name mismatch: expected "${expected.name}", got "${actual.name}"` };
    }

    if (actual.kind !== expected.kind) {
        return { match: false, reason: `Kind mismatch: expected ${expected.kind}, got ${actual.kind}` };
    }

    if (expected.detail !== undefined && actual.detail !== expected.detail) {
        return { match: false, reason: `Detail mismatch: expected "${expected.detail}", got "${actual.detail}"` };
    }

    if (expected.children) {
        if (!actual.children || actual.children.length !== expected.children.length) {
            return {
                match: false,
                reason: `Children count mismatch: expected ${expected.children.length}, got ${actual.children?.length || 0}`
            };
        }

        for (let i = 0; i < expected.children.length; i++) {
            const childResult = symbolMatches(actual.children[i], expected.children[i]);
            if (!childResult.match) {
                return { match: false, reason: `Child ${i}: ${childResult.reason}` };
            }
        }
    }

    return { match: true };
}

/**
 * Run a single test case
 */
async function runTest(testCase) {
    const provider = new FcstmDocumentSymbolProvider();
    const document = new MockDocument(testCase.code);

    try {
        const symbols = await provider.provideDocumentSymbols(document, {});

        // Check symbol count
        const expectedCount = testCase.expectedSymbols.length;
        const actualCount = symbols.length;

        if (actualCount !== expectedCount) {
            console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
            console.log(`  Expected ${expectedCount} symbol(s), got ${actualCount}`);
            if (actualCount > 0) {
                console.log(`  Actual symbols:`);
                symbols.forEach((sym, idx) => {
                    console.log(`    ${idx + 1}. ${sym.name} (kind: ${sym.kind}, detail: "${sym.detail}")`);
                });
            }
            failed++;
            return false;
        }

        // Check each symbol
        for (let i = 0; i < expectedCount; i++) {
            const result = symbolMatches(symbols[i], testCase.expectedSymbols[i]);
            if (!result.match) {
                console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
                console.log(`  Symbol ${i + 1}: ${result.reason}`);
                failed++;
                return false;
            }
        }

        console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        passed++;
        return true;

    } catch (error) {
        console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        console.log(`  Unexpected error: ${error.message}`);
        console.log(`  Stack: ${error.stack}`);
        failed++;
        return false;
    }
}

/**
 * Test cases for P0.4
 */
const testCases = [
    // Variable extraction tests
    new TestCase(
        'P0.4-01',
        'Extract single int variable',
        'def int counter = 0;',
        [
            { name: 'counter', kind: SymbolKind.Variable, detail: 'int' }
        ]
    ),

    new TestCase(
        'P0.4-02',
        'Extract single float variable',
        'def float temperature = 25.5;',
        [
            { name: 'temperature', kind: SymbolKind.Variable, detail: 'float' }
        ]
    ),

    new TestCase(
        'P0.4-03',
        'Extract multiple variables',
        `def int x = 0;
def int y = 1;
def float z = 2.5;`,
        [
            { name: 'x', kind: SymbolKind.Variable, detail: 'int' },
            { name: 'y', kind: SymbolKind.Variable, detail: 'int' },
            { name: 'z', kind: SymbolKind.Variable, detail: 'float' }
        ]
    ),

    new TestCase(
        'P0.4-04',
        'Extract variable with hex value',
        'def int flags = 0xFF;',
        [
            { name: 'flags', kind: SymbolKind.Variable, detail: 'int' }
        ]
    ),

    // State extraction tests
    new TestCase(
        'P0.4-05',
        'Extract single leaf state',
        'state Idle;',
        [
            { name: 'Idle', kind: SymbolKind.Class, detail: '' }
        ]
    ),

    new TestCase(
        'P0.4-06',
        'Extract named leaf state',
        'state Running named "System Running";',
        [
            { name: 'Running', kind: SymbolKind.Class, detail: 'System Running' }
        ]
    ),

    new TestCase(
        'P0.4-07',
        'Extract pseudo state',
        'pseudo state Junction;',
        [
            { name: 'Junction', kind: SymbolKind.Class, detail: 'pseudo state' }
        ]
    ),

    new TestCase(
        'P0.4-08',
        'Extract composite state with no children',
        'state Root { }',
        [
            { name: 'Root', kind: SymbolKind.Class, detail: '', children: [] }
        ]
    ),

    new TestCase(
        'P0.4-09',
        'Extract composite state with leaf children',
        `state Root {
    state Child1;
    state Child2;
}`,
        [
            state('Root', '', [
                statesGroup([state('Child1'), state('Child2')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-10',
        'Extract nested composite states',
        `state Root {
    state Level1 {
        state Level2;
    }
}`,
        [
            state('Root', '', [
                statesGroup([
                    state('Level1', '', [
                        statesGroup([state('Level2')]),
                    ]),
                ]),
            ]),
        ]
    ),

    // Event extraction tests
    new TestCase(
        'P0.4-11',
        'Extract simple event',
        `state Root {
    event Start;
}`,
        [
            state('Root', '', [
                eventsGroup([event('Start')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-12',
        'Extract named event',
        `state Root {
    event Stop named "Stop Event";
}`,
        [
            state('Root', '', [
                eventsGroup([event('Stop', 'Stop Event')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-13',
        'Extract multiple events',
        `state Root {
    event Start;
    event Stop;
    event Pause;
}`,
        [
            state('Root', '', [
                eventsGroup([event('Start'), event('Stop'), event('Pause')]),
            ]),
        ]
    ),

    // Mixed extraction tests
    new TestCase(
        'P0.4-14',
        'Extract variables and states',
        `def int x = 0;
state Root;`,
        [
            { name: 'x', kind: SymbolKind.Variable, detail: 'int' },
            { name: 'Root', kind: SymbolKind.Class, detail: '' }
        ]
    ),

    new TestCase(
        'P0.4-15',
        'Extract variables, states, and events',
        `def int counter = 0;
state System {
    event Start;
    state Idle;
}`,
        [
            variable('counter', 'int'),
            state('System', '', [
                eventsGroup([event('Start')]),
                statesGroup([state('Idle')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-16',
        'Extract complex hierarchy',
        `def int x = 0;
def float y = 1.0;
state Root {
    event GlobalEvent;
    state SubSystem {
        event LocalEvent;
        state Active;
        state Idle;
    }
}`,
        [
            variable('x', 'int'),
            variable('y', 'float'),
            state('Root', '', [
                eventsGroup([event('GlobalEvent')]),
                statesGroup([
                    state('SubSystem', '', [
                        eventsGroup([event('LocalEvent')]),
                        statesGroup([state('Active'), state('Idle')]),
                    ]),
                ]),
            ]),
        ]
    ),

    // Edge cases
    new TestCase(
        'P0.4-17',
        'Extract state with lifecycle actions',
        `def int x = 0;
state Root {
    enter { x = 0; }
    during { x = x + 1; }
    exit { x = 0; }
}`,
        [
            variable('x', 'int'),
            state('Root', '', [
                actionsGroup([
                    lifecycleGroup([
                        actionEntry('enter', 'enter action operations'),
                        actionEntry('during', 'during action operations'),
                        actionEntry('exit', 'exit action operations'),
                    ]),
                ]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-18',
        'Extract state with transitions',
        `state Root {
    state A;
    state B;
    [*] -> A;
    A -> B;
}`,
        [
            state('Root', '', [
                transitionsGroup([
                    transition('[*] -> A', 'entry'),
                    transition('A -> B', 'normal'),
                ]),
                statesGroup([state('A'), state('B')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-19',
        'Extract multiple top-level states in composite',
        `state Root {
    state State1;
    state State2;
    state State3;
}`,
        [
            state('Root', '', [
                statesGroup([state('State1'), state('State2'), state('State3')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-20',
        'Extract deeply nested states',
        `state L1 {
    state L2 {
        state L3 {
            state L4;
        }
    }
}`,
        [
            state('L1', '', [
                statesGroup([
                    state('L2', '', [
                        statesGroup([
                            state('L3', '', [
                                statesGroup([state('L4')]),
                            ]),
                        ]),
                    ]),
                ]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-21',
        'Extract state with aspect actions',
        `def int x = 0;
state Root {
    >> during before { x = 0; }
    >> during after { x = 1; }
    state Child;
}`,
        [
            variable('x', 'int'),
            state('Root', '', [
                actionsGroup([
                    aspectsGroup([
                        actionEntry('during before', 'during aspect before global operations'),
                        actionEntry('during after', 'during aspect after global operations'),
                    ]),
                ]),
                statesGroup([state('Child')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-22',
        'Extract mixed pseudo and normal states',
        `state Root {
    state Normal;
    pseudo state Junction;
    state Another;
}`,
        [
            state('Root', '', [
                statesGroup([
                    state('Normal'),
                    pseudoState('Junction'),
                    state('Another'),
                ]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-23',
        'Extract named composite state',
        'state Root named "Root State" { state Child; }',
        [
            state('Root', 'Root State', [
                statesGroup([state('Child')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-24',
        'Extract state with abstract actions',
        `state Root {
    enter abstract Init;
    exit abstract Cleanup;
}`,
        [
            state('Root', '', [
                actionsGroup([
                    lifecycleGroup([
                        actionEntry('Init', 'enter action abstract'),
                        actionEntry('Cleanup', 'exit action abstract'),
                    ]),
                ]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-25',
        'Extract state with reference actions',
        `state Root {
    enter ref /GlobalInit;
    exit ref /GlobalCleanup;
}`,
        [
            state('Root', '', [
                actionsGroup([
                    lifecycleGroup([
                        actionEntry('enter ref', 'enter action ref /GlobalInit'),
                        actionEntry('exit ref', 'exit action ref /GlobalCleanup'),
                    ]),
                ]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-26',
        'Extract variables with complex expressions',
        `def int a = 0xFF * 2;
def float b = 3.14 + 1.0;
def int c = (1 << 4) | 0x0F;`,
        [
            { name: 'a', kind: SymbolKind.Variable, detail: 'int' },
            { name: 'b', kind: SymbolKind.Variable, detail: 'float' },
            { name: 'c', kind: SymbolKind.Variable, detail: 'int' }
        ]
    ),

    new TestCase(
        'P0.4-27',
        'Extract sibling states at same level',
        `state Root {
    state Branch1 {
        state Leaf1;
    }
    state Branch2 {
        state Leaf2;
    }
}`,
        [
            state('Root', '', [
                statesGroup([
                    state('Branch1', '', [
                        statesGroup([state('Leaf1')]),
                    ]),
                    state('Branch2', '', [
                        statesGroup([state('Leaf2')]),
                    ]),
                ]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-28',
        'Extract events with single quotes in name',
        `state Root {
    event E1 named 'Event One';
}`,
        [
            state('Root', '', [
                eventsGroup([event('E1', 'Event One')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-29',
        'Extract complete traffic light example',
        `def int counter = 0;
def float temperature = 25.5;
state TrafficLight {
    event Start;
    event Stop;
    state Red;
    state Yellow;
    state Green;
}`,
        [
            variable('counter', 'int'),
            variable('temperature', 'float'),
            state('TrafficLight', '', [
                eventsGroup([event('Start'), event('Stop')]),
                statesGroup([state('Red'), state('Yellow'), state('Green')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-30',
        'Extract state machine with all symbol types',
        `def int x = 0;
def float y = 1.0;
state System named "Main System" {
    event GlobalStart named "Global Start Event";
    event GlobalStop;

    pseudo state Junction;

    state SubSystem {
        event LocalEvent;
        state Active named "Active State";
        state Idle;
    }
}`,
        [
            variable('x', 'int'),
            variable('y', 'float'),
            state('System', 'Main System', [
                eventsGroup([
                    event('GlobalStart', 'Global Start Event'),
                    event('GlobalStop'),
                ]),
                statesGroup([
                    pseudoState('Junction'),
                    state('SubSystem', '', [
                        eventsGroup([event('LocalEvent')]),
                        statesGroup([
                            state('Active', 'Active State'),
                            state('Idle'),
                        ]),
                    ]),
                ]),
            ]),
        ]
    ),

    // Partial parsing tests (with syntax errors)
    new TestCase(
        'P0.4-31',
        'Extract symbols from code with missing semicolon',
        `def int x = 0
state Root;`,
        [
            { name: 'x', kind: SymbolKind.Variable, detail: 'int' },
            { name: 'Root', kind: SymbolKind.Class, detail: '' }
        ]
    ),

    new TestCase(
        'P0.4-32',
        'Extract symbols from code with unclosed brace',
        `def int x = 0;
state Root {
    state Child;`,
        [
            variable('x', 'int'),
            state('Root', '', [
                statesGroup([state('Child')]),
            ]),
        ]
    ),

    new TestCase(
        'P0.4-33',
        'Extract symbols with comments',
        `// Variable definitions
def int x = 0;  // counter
/* Multi-line comment
   about the state */
state Root;`,
        [
            { name: 'x', kind: SymbolKind.Variable, detail: 'int' },
            { name: 'Root', kind: SymbolKind.Class, detail: '' }
        ]
    ),

    new TestCase(
        'P0.4-34',
        'Extract empty composite state',
        `state Empty { }`,
        [
            { name: 'Empty', kind: SymbolKind.Class, detail: '', children: [] }
        ]
    ),

    new TestCase(
        'P0.4-35',
        'Extract state with only transitions (no child states)',
        `state Root {
    [*] -> [*];
}`,
        [
            state('Root', '', [
                transitionsGroup([
                    transition('[*] -> ?', 'entry'),
                    transition('[*] -> ?', 'entry'),
                ]),
            ]),
        ]
    ),
];

/**
 * Main execution
 */
async function main() {
    console.log(`${colors.cyan}FCSTM VSCode P0.4 Document Symbols Verification${colors.reset}`);
    console.log(`${colors.cyan}================================================${colors.reset}`);

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
        console.log(`${colors.green}All P0.4 verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some P0.4 verification checkpoints failed.${colors.reset}`);
        process.exit(1);
    }
}

main().catch(error => {
    console.error(`${colors.red}Fatal error:${colors.reset}`, error);
    process.exit(1);
});

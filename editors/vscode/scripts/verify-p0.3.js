#!/usr/bin/env node

/**
 * P0.3 Syntax Diagnostics Verification Script
 *
 * This script validates the syntax diagnostics feature by testing:
 * - Error detection for various syntax errors
 * - Error message quality and accuracy
 * - Error position reporting
 * - Partial parsing and error recovery
 */

const { FcstmParser } = require('../out/parser');

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
 * Test case structure
 */
class TestCase {
    constructor(id, description, code, expectedErrors) {
        this.id = id;
        this.description = description;
        this.code = code;
        this.expectedErrors = expectedErrors; // Array of { line?, column?, messagePattern? }
    }
}

/**
 * Run a single test case
 */
async function runTest(testCase) {
    const parser = new FcstmParser();

    try {
        const result = await parser.parse(testCase.code);

        // Check if error count matches
        const expectedCount = testCase.expectedErrors.length;
        const actualCount = result.errors.length;

        if (expectedCount === 0 && actualCount === 0) {
            // Valid code, no errors expected
            console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
            passed++;
            return true;
        }

        if (actualCount !== expectedCount) {
            console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
            console.log(`  Expected ${expectedCount} error(s), got ${actualCount}`);
            if (actualCount > 0) {
                console.log(`  Actual errors:`);
                result.errors.forEach((err, idx) => {
                    console.log(`    ${idx + 1}. Line ${err.line + 1}, Col ${err.column}: ${err.message}`);
                });
            }
            failed++;
            return false;
        }

        // Check error details
        let allMatch = true;
        for (let i = 0; i < expectedCount; i++) {
            const expected = testCase.expectedErrors[i];
            const actual = result.errors[i];

            if (expected.line !== undefined && actual.line !== expected.line) {
                console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
                console.log(`  Error ${i + 1}: Expected line ${expected.line}, got ${actual.line}`);
                allMatch = false;
                break;
            }

            if (expected.messagePattern && !expected.messagePattern.test(actual.message)) {
                console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
                console.log(`  Error ${i + 1}: Message doesn't match pattern`);
                console.log(`  Expected pattern: ${expected.messagePattern}`);
                console.log(`  Actual message: ${actual.message}`);
                allMatch = false;
                break;
            }
        }

        if (allMatch) {
            console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
            passed++;
            return true;
        } else {
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
 * Test cases for P0.3
 */
const testCases = [
    // Valid code tests (no errors expected)
    new TestCase(
        'P0.3-01',
        'Valid minimal state machine',
        'state Root;',
        []
    ),

    new TestCase(
        'P0.3-02',
        'Valid variable definition',
        `def int counter = 0;
state Root;`,
        []
    ),

    new TestCase(
        'P0.3-03',
        'Valid composite state with transitions',
        `state System {
    state Idle;
    state Active;
    [*] -> Idle;
    Idle -> Active;
}`,
        []
    ),

    new TestCase(
        'P0.3-04',
        'Valid guarded transition',
        `def int x = 0;
state Root {
    state A;
    state B;
    A -> B : if [x > 10];
}`,
        []
    ),

    new TestCase(
        'P0.3-05',
        'Valid effect block',
        `def int x = 0;
state Root {
    state A;
    state B;
    A -> B effect { x = 1; };
}`,
        []
    ),

    new TestCase(
        'P0.3-06',
        'Valid lifecycle actions',
        `def int x = 0;
state Root {
    enter { x = 0; }
    during { x = x + 1; }
    exit { x = 0; }
}`,
        []
    ),

    new TestCase(
        'P0.3-07',
        'Valid aspect actions',
        `def int x = 0;
state Root {
    >> during before { x = 0; }
    >> during after { x = 1; }
    state Child;
}`,
        []
    ),

    new TestCase(
        'P0.3-08',
        'Valid abstract action',
        `state Root {
    enter abstract Init;
}`,
        []
    ),

    new TestCase(
        'P0.3-09',
        'Valid reference action',
        `state Root {
    enter ref /GlobalInit;
}`,
        []
    ),

    new TestCase(
        'P0.3-10',
        'Valid event definition',
        `state Root {
    event Start;
    event Stop named "Stop Event";
}`,
        []
    ),

    // Error detection tests
    new TestCase(
        'P0.3-11',
        'Missing semicolon after variable definition',
        'def int x = 0',
        [{ line: 0, messagePattern: /semicolon/i }]
    ),

    new TestCase(
        'P0.3-12',
        'Missing semicolon after state definition',
        'state Root',
        [{ line: 0, messagePattern: /semicolon/i }]
    ),

    new TestCase(
        'P0.3-13',
        'Missing semicolon after transition',
        `state Root {
    state A;
    state B;
    A -> B
}`,
        [{ messagePattern: /semicolon|unexpected.*}|syntax/i }]
    ),

    new TestCase(
        'P0.3-14',
        'Missing opening brace for composite state',
        `state Root
    state Child;
}`,
        [{ messagePattern: /brace|semicolon/i }]
    ),

    new TestCase(
        'P0.3-15',
        'Missing closing brace for composite state',
        `state Root {
    state Child;`,
        [{ messagePattern: /brace/i }]
    ),

    new TestCase(
        'P0.3-16',
        'Missing opening brace for enter block',
        `state Root {
    enter x = 0; }
}`,
        [
            { messagePattern: /operator|syntax/i },
            { messagePattern: /brace|syntax/i }
        ]
    ),

    new TestCase(
        'P0.3-17',
        'Missing closing brace for enter block',
        `def int x = 0;
state Root {
    enter { x = 0;
}`,
        [{ messagePattern: /brace/i }]
    ),

    new TestCase(
        'P0.3-18',
        'Missing opening bracket for guard',
        `def int x = 0;
state Root {
    state A;
    state B;
    A -> B : if x > 10];
}`,
        [{ messagePattern: /bracket/i }]
    ),

    new TestCase(
        'P0.3-19',
        'Missing closing bracket for guard',
        `def int x = 0;
state Root {
    state A;
    state B;
    A -> B : if [x > 10;
}`,
        [{ messagePattern: /bracket/i }]
    ),

    new TestCase(
        'P0.3-20',
        'Invalid transition operator (=>)',
        `state Root {
    state A;
    state B;
    A => B;
}`,
        [{ messagePattern: /operator|arrow|syntax/i }]
    ),

    new TestCase(
        'P0.3-21',
        'Missing equals in variable definition',
        'def int x 0;',
        [
            { messagePattern: /equals|=/i },
            { messagePattern: /brace|syntax/i }
        ]
    ),

    new TestCase(
        'P0.3-22',
        'Missing semicolon after operation in enter block',
        `def int x = 0;
state Root {
    enter {
        x = 0
        x = 1;
    }
}`,
        [{ messagePattern: /semicolon/i }]
    ),

    new TestCase(
        'P0.3-23',
        'Invalid keyword in state name position',
        'state if;',
        [{ messagePattern: /syntax|unexpected/i }]
    ),

    new TestCase(
        'P0.3-24',
        'Missing state keyword before name',
        `Root {
    state Child;
}`,
        [{ messagePattern: /syntax|unexpected/i }]
    ),

    new TestCase(
        'P0.3-25',
        'Missing type in variable definition',
        'def x = 0;',
        [
            { messagePattern: /int|float|type/i },
            { messagePattern: /brace|syntax/i }
        ]
    ),

    new TestCase(
        'P0.3-26',
        'Extra closing brace',
        `state Root {
    state Child;
}}`,
        [{ messagePattern: /brace|unexpected/i }]
    ),

    new TestCase(
        'P0.3-27',
        'Missing transition arrow',
        `state Root {
    state A;
    state B;
    A B;
}`,
        [{ messagePattern: /arrow|->|syntax/i }]
    ),

    new TestCase(
        'P0.3-28',
        'Invalid character in identifier',
        'state Root-State;',
        [{ messagePattern: /syntax|unexpected/i }]
    ),

    new TestCase(
        'P0.3-29',
        'Missing semicolon before [*]',
        `state Root {
    state A
    [*] -> A;
}`,
        [{ messagePattern: /semicolon/i }]
    ),

    new TestCase(
        'P0.3-30',
        'Unclosed string literal',
        `state Root {
    event E named "Unclosed;
}`,
        [
            { messagePattern: /unexpected/i },
            { messagePattern: /unexpected/i }
        ]
    ),

    new TestCase(
        'P0.3-31',
        'Multiple missing semicolons',
        `def int x = 0
def int y = 1
state Root;`,
        [
            { messagePattern: /semicolon/i },
            { messagePattern: /semicolon/i }
        ]
    ),

    new TestCase(
        'P0.3-32',
        'Missing semicolon after event definition',
        `state Root {
    event Start
    state Child;
}`,
        [{ messagePattern: /semicolon/i }]
    ),

    new TestCase(
        'P0.3-33',
        'Invalid expression in guard',
        `def int x = 0;
state Root {
    state A;
    state B;
    A -> B : if [x +];
}`,
        [{ messagePattern: /syntax|expression/i }]
    ),

    new TestCase(
        'P0.3-34',
        'Missing effect keyword before block',
        `def int x = 0;
state Root {
    state A;
    state B;
    A -> B { x = 1; };
}`,
        [
            { messagePattern: /unexpected/i },
            { messagePattern: /unexpected/i }
        ]
    ),

    new TestCase(
        'P0.3-35',
        'Invalid during aspect without before/after',
        `state Root {
    >> during { }
    state Child;
}`,
        [{ messagePattern: /syntax|before|after/i }]
    ),
];

/**
 * Main execution
 */
async function main() {
    console.log(`${colors.cyan}FCSTM VSCode P0.3 Diagnostics Verification${colors.reset}`);
    console.log(`${colors.cyan}============================================${colors.reset}`);

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
        console.log(`${colors.green}All P0.3 verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some P0.3 verification checkpoints failed.${colors.reset}`);
        process.exit(1);
    }
}

main().catch(error => {
    console.error(`${colors.red}Fatal error:${colors.reset}`, error);
    process.exit(1);
});

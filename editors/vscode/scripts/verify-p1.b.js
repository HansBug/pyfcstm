#!/usr/bin/env node

/**
 * P1.B Language Configuration Verification Script
 *
 * This script validates the FCSTM VSCode language configuration by testing:
 * - Word pattern coverage for FCSTM-specific token forms
 * - Bracket, auto-closing, and surrounding pair declarations
 * - Package manifest wiring for the language configuration file
 */

const fs = require('fs');
const path = require('path');

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

const configPath = path.join(__dirname, '..', 'language-configuration.json');
const packagePath = path.join(__dirname, '..', 'package.json');

const languageConfig = JSON.parse(fs.readFileSync(configPath, 'utf8'));
const packageJson = JSON.parse(fs.readFileSync(packagePath, 'utf8'));
const wordPattern = new RegExp(languageConfig.wordPattern, 'g');

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

function matchExactly(sample, expected) {
    const matches = sample.match(wordPattern) || [];
    assert(
        matches.length === expected.length,
        `Expected ${expected.length} match(es) for ${JSON.stringify(sample)}, got ${matches.length}: ${matches.join(', ')}`
    );
    assert(
        JSON.stringify(matches) === JSON.stringify(expected),
        `Expected matches ${JSON.stringify(expected)} for ${JSON.stringify(sample)}, got ${JSON.stringify(matches)}`
    );
}

async function runTest(testCase) {
    try {
        await testCase.testFn();
        console.log(`${colors.green}${CHECKMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        passed++;
        return true;
    } catch (error) {
        console.log(`${colors.red}${CROSSMARK}${colors.reset} [${testCase.id}] ${testCase.description}`);
        console.log(`  ${colors.red}Error: ${error.message}${colors.reset}`);
        failed++;
        return false;
    }
}

const tests = [
    new TestCase(
        'P1.B-01',
        'Package manifest contributes the FCSTM language configuration file',
        () => {
            const fcstmLanguage = (packageJson.contributes.languages || []).find(item => item.id === 'fcstm');
            assert(fcstmLanguage, 'FCSTM language contribution not found');
            assert(fcstmLanguage.configuration === './language-configuration.json', 'FCSTM language configuration path is incorrect');
        }
    ),
    new TestCase(
        'P1.B-02',
        'Bracket pairs include braces, brackets, and parentheses',
        () => {
            const brackets = languageConfig.brackets || [];
            assert(JSON.stringify(brackets) === JSON.stringify([
                ['{', '}'],
                ['[', ']'],
                ['(', ')']
            ]), `Unexpected brackets: ${JSON.stringify(brackets)}`);
        }
    ),
    new TestCase(
        'P1.B-03',
        'Auto-closing pairs include FCSTM structural delimiters and comments',
        () => {
            const autoPairs = languageConfig.autoClosingPairs || [];
            const expected = [
                { open: '{', close: '}' },
                { open: '[', close: ']' },
                { open: '(', close: ')' },
                { open: '"', close: '"', notIn: ['string', 'comment'] },
                { open: "'", close: "'", notIn: ['string', 'comment'] },
                { open: '/*', close: '*/', notIn: ['string', 'comment'] }
            ];
            assert(JSON.stringify(autoPairs) === JSON.stringify(expected), `Unexpected autoClosingPairs: ${JSON.stringify(autoPairs)}`);
        }
    ),
    new TestCase(
        'P1.B-04',
        'Surrounding pairs support braces, brackets, parentheses, and quotes',
        () => {
            const surroundingPairs = languageConfig.surroundingPairs || [];
            const expected = [
                ['{', '}'],
                ['[', ']'],
                ['(', ')'],
                ['"', '"'],
                ["'", "'"]
            ];
            assert(JSON.stringify(surroundingPairs) === JSON.stringify(expected), `Unexpected surroundingPairs: ${JSON.stringify(surroundingPairs)}`);
        }
    ),
    new TestCase(
        'P1.B-05',
        'Word pattern matches simple identifiers',
        () => {
            matchExactly('StateA', ['StateA']);
            matchExactly('counter_1', ['counter_1']);
        }
    ),
    new TestCase(
        'P1.B-06',
        'Word pattern keeps dotted references as a single token',
        () => {
            matchExactly('StateA.UserInit', ['StateA.UserInit']);
            matchExactly('Parent.Child.Grandchild', ['Parent.Child.Grandchild']);
        }
    ),
    new TestCase(
        'P1.B-07',
        'Word pattern keeps absolute event names as a single token',
        () => {
            matchExactly('/GlobalEvent', ['/GlobalEvent']);
            matchExactly('/Root.Module.Event', ['/Root.Module.Event']);
        }
    ),
    new TestCase(
        'P1.B-08',
        'Word pattern keeps local event syntax grouped as ::EventName',
        () => {
            matchExactly('::EventName', ['::EventName']);
            matchExactly('StateA -> StateB ::LocalEvent;', ['StateA', 'StateB', '::LocalEvent']);
        }
    ),
    new TestCase(
        'P1.B-09',
        'Word pattern recognizes pseudo-state token [*]',
        () => {
            matchExactly('[*]', ['[*]']);
            matchExactly('[*] -> Active;', ['[*]', 'Active']);
        }
    ),
    new TestCase(
        'P1.B-10',
        'Word pattern recognizes decimal, float, scientific, hex, and binary literals',
        () => {
            matchExactly('123', ['123']);
            matchExactly('-42', ['-42']);
            matchExactly('25.5', ['25.5']);
            matchExactly('3.14e-5', ['3.14e-5']);
            matchExactly('0xFF', ['0xFF']);
            matchExactly('0b1010', ['0b1010']);
        }
    ),
    new TestCase(
        'P1.B-11',
        'Word pattern excludes punctuation outside FCSTM token forms',
        () => {
            matchExactly('StateA -> StateB;', ['StateA', 'StateB']);
            matchExactly('effect { counter = 0; }', ['effect', 'counter', '0']);
        }
    ),
    new TestCase(
        'P1.B-12',
        'Region folding markers remain configured',
        () => {
            assert(languageConfig.folding && languageConfig.folding.markers, 'Folding markers are missing');
            assert(languageConfig.folding.markers.start === '^\\s*//\\s*#?region\\b', 'Unexpected folding start marker');
            assert(languageConfig.folding.markers.end === '^\\s*//\\s*#?endregion\\b', 'Unexpected folding end marker');
        }
    )
];

async function main() {
    console.log(`${colors.cyan}FCSTM VSCode P1.B Language Configuration Verification${colors.reset}`);
    console.log(`${colors.cyan}==================================================${colors.reset}`);

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
        console.log(`${colors.green}All P1.B verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some P1.B verification checkpoints failed.${colors.reset}`);
        process.exit(1);
    }
}

main().catch(error => {
    console.error(`${colors.red}Fatal error:${colors.reset}`, error);
    process.exit(1);
});

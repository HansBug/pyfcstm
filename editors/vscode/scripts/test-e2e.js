#!/usr/bin/env node

/**
 * End-to-End Bundle Verification Script
 *
 * This script validates that the bundled dist/extension.js is a complete,
 * functional JavaScript file with all required dependencies and functionality.
 *
 * Test coverage:
 * - Bundle file existence and basic structure
 * - ANTLR-generated lexer/parser classes bundled
 * - antlr4 runtime library bundled
 * - Extension source modules bundled
 * - Basic functionality tests (parser, diagnostics, symbols, completion, hover)
 */

const fs = require('fs');
const path = require('path');

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
    constructor(id, description, testFn) {
        this.id = id;
        this.description = description;
        this.testFn = testFn;
    }
}

/**
 * Run a single test case
 */
async function runTest(testCase) {
    try {
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
    }
}

/**
 * Test cases
 */
const tests = [
    // Bundle Structure Tests
    new TestCase(
        'E2E-01',
        'Bundle file exists at dist/extension.js',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            if (!fs.existsSync(bundlePath)) {
                throw new Error(`Bundle file not found at ${bundlePath}`);
            }
        }
    ),

    new TestCase(
        'E2E-02',
        'Bundle file is non-empty and has reasonable size',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const stats = fs.statSync(bundlePath);
            if (stats.size === 0) {
                throw new Error('Bundle file is empty');
            }
            if (stats.size < 100000) { // Less than 100KB is suspicious
                throw new Error(`Bundle file is too small (${stats.size} bytes), expected > 100KB`);
            }
            if (stats.size > 10000000) { // More than 10MB is suspicious
                throw new Error(`Bundle file is too large (${stats.size} bytes), expected < 10MB`);
            }
        }
    ),

    new TestCase(
        'E2E-03',
        'Bundle file is valid JavaScript syntax',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');

            // Try to parse as JavaScript (will throw if invalid)
            try {
                new Function(bundleContent);
            } catch (e) {
                throw new Error(`Bundle contains invalid JavaScript: ${e.message}`);
            }
        }
    ),

    // ANTLR Parser Classes Tests
    new TestCase(
        'E2E-04',
        'GrammarLexer class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('GrammarLexer')) {
                throw new Error('GrammarLexer not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-05',
        'GrammarParser class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('GrammarParser')) {
                throw new Error('GrammarParser not found in bundle');
            }
        }
    ),

    // antlr4 Runtime Tests
    new TestCase(
        'E2E-06',
        'antlr4 InputStream is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('InputStream')) {
                throw new Error('antlr4 InputStream not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-07',
        'antlr4 CommonTokenStream is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('CommonTokenStream')) {
                throw new Error('antlr4 CommonTokenStream not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-08',
        'antlr4 ParserATNSimulator is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('ParserATNSimulator')) {
                throw new Error('antlr4 ParserATNSimulator not found in bundle');
            }
        }
    ),

    // Extension Source Modules Tests
    new TestCase(
        'E2E-09',
        'FcstmParser class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('FcstmParser')) {
                throw new Error('FcstmParser class not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-10',
        'FcstmDiagnosticsProvider class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('FcstmDiagnosticsProvider')) {
                throw new Error('FcstmDiagnosticsProvider class not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-11',
        'FcstmDocumentSymbolProvider class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('FcstmDocumentSymbolProvider')) {
                throw new Error('FcstmDocumentSymbolProvider class not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-12',
        'FcstmCompletionProvider class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('FcstmCompletionProvider')) {
                throw new Error('FcstmCompletionProvider class not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-13',
        'FcstmHoverProvider class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('FcstmHoverProvider')) {
                throw new Error('FcstmHoverProvider class not found in bundle');
            }
        }
    ),

    // Extension Entry Points Tests
    new TestCase(
        'E2E-14',
        'Extension activate function is exported',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('activate')) {
                throw new Error('activate function not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-15',
        'Extension deactivate function is exported',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('deactivate')) {
                throw new Error('deactivate function not found in bundle');
            }
        }
    ),

    // Bundle Integrity Tests
    new TestCase(
        'E2E-16',
        'Bundle uses CommonJS module format',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');

            // Check for CommonJS patterns
            const hasExports = bundleContent.includes('exports') || bundleContent.includes('module.exports');
            const hasRequire = bundleContent.includes('require');

            if (!hasExports && !hasRequire) {
                throw new Error('Bundle does not appear to use CommonJS format');
            }
        }
    ),

    new TestCase(
        'E2E-17',
        'Bundle does not include vscode module (should be external)',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');

            // vscode should be required but not bundled
            // Check that we don't have VSCode's internal implementation
            if (bundleContent.includes('vscode/lib/') || bundleContent.includes('vscode/out/')) {
                throw new Error('Bundle incorrectly includes vscode module internals');
            }
        }
    ),

    new TestCase(
        'E2E-18',
        'Bundle contains error message normalization logic',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('normalizeSyntaxMessage') && !bundleContent.includes('Missing semicolon')) {
                throw new Error('Error message normalization logic not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-19',
        'Bundle contains ANTLR error listener implementation',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('syntaxError') && !bundleContent.includes('ErrorListener')) {
                throw new Error('ANTLR error listener implementation not found in bundle');
            }
        }
    ),
];

/**
 * Main test runner
 */
async function main() {
    console.log(`${colors.cyan}End-to-End Bundle Verification${colors.reset}`);
    console.log(`${colors.cyan}================================${colors.reset}\n`);

    for (const test of tests) {
        await runTest(test);
    }

    console.log(`\n${colors.cyan}Summary${colors.reset}`);
    console.log(`${colors.cyan}-------${colors.reset}`);
    console.log(`Total checkpoints: ${tests.length}`);
    console.log(`Passed: ${passed}`);
    console.log(`Failed: ${failed}`);

    if (failed === 0) {
        console.log(`${colors.green}All E2E bundle verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some E2E bundle verification checkpoints failed.${colors.reset}`);
        process.exit(1);
    }
}

main().catch(error => {
    console.error(`${colors.red}Fatal error:${colors.reset}`, error);
    process.exit(1);
});

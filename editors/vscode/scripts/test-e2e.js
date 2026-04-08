#!/usr/bin/env node

/**
 * End-to-End Bundle Verification Script
 *
 * This script validates that the bundled dist/extension.js and dist/server.js
 * are complete JavaScript outputs with the required client/server wiring.
 *
 * Test coverage:
 * - Client/server bundle existence and basic structure
 * - ANTLR-generated lexer/parser classes bundled into the server bundle
 * - antlr4 runtime library bundled into the server bundle
 * - Language client/server entry points bundled correctly
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
        'Bundle file exists at dist/server.js',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            if (!fs.existsSync(bundlePath)) {
                throw new Error(`Bundle file not found at ${bundlePath}`);
            }
        }
    ),

    new TestCase(
        'E2E-03',
        'Client and server bundles are non-empty and have reasonable size',
        async () => {
            const clientBundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const serverBundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            const clientStats = fs.statSync(clientBundlePath);
            const serverStats = fs.statSync(serverBundlePath);

            if (clientStats.size === 0) {
                throw new Error('Client bundle is empty');
            }
            if (serverStats.size === 0) {
                throw new Error('Server bundle is empty');
            }
            if (clientStats.size < 10000) {
                throw new Error(`Client bundle is too small (${clientStats.size} bytes), expected > 10KB`);
            }
            if (serverStats.size < 100000) {
                throw new Error(`Server bundle is too small (${serverStats.size} bytes), expected > 100KB`);
            }
            if (clientStats.size > 10000000 || serverStats.size > 10000000) {
                throw new Error('Bundle file is suspiciously large (> 10MB)');
            }
        }
    ),

    new TestCase(
        'E2E-04',
        'Client and server bundles are valid JavaScript syntax',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const serverBundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            const bundleContents = [
                fs.readFileSync(bundlePath, 'utf8'),
                fs.readFileSync(serverBundlePath, 'utf8'),
            ];

            for (const bundleContent of bundleContents) {
                try {
                    new Function(bundleContent);
                } catch (e) {
                    throw new Error(`Bundle contains invalid JavaScript: ${e.message}`);
                }
            }
        }
    ),

    // ANTLR Parser Classes Tests
    new TestCase(
        'E2E-04',
        'GrammarLexer class is bundled',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
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
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
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
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
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
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
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
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('ParserATNSimulator')) {
                throw new Error('antlr4 ParserATNSimulator not found in bundle');
            }
        }
    ),

    // Extension Source Modules Tests
    new TestCase(
        'E2E-09',
        'FcstmParser class is bundled into the server',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('FcstmParser')) {
                throw new Error('FcstmParser class not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-10',
        'FcstmLanguageServerCore class is bundled into the server',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('FcstmLanguageServerCore')) {
                throw new Error('FcstmLanguageServerCore class not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-11',
        'Server bundle contains vscode-languageserver connection wiring',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('createConnection') || !bundleContent.includes('sendDiagnostics')) {
                throw new Error('Language server connection wiring not found in server bundle');
            }
        }
    ),

    new TestCase(
        'E2E-12',
        'Client bundle contains vscode-languageclient wiring',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('LanguageClient') || !bundleContent.includes('TransportKind')) {
                throw new Error('LanguageClient wiring not found in client bundle');
            }
        }
    ),

    new TestCase(
        'E2E-13',
        'Client bundle references the bundled server entrypoint',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'extension.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('server.js') || !bundleContent.includes('fcstmLanguageServer')) {
                throw new Error('Bundled server entrypoint not referenced by the client');
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
        'Client and server bundles use CommonJS module format',
        async () => {
            for (const fileName of ['extension.js', 'server.js']) {
                const bundlePath = path.join(__dirname, '..', 'dist', fileName);
                const bundleContent = fs.readFileSync(bundlePath, 'utf8');
                const hasExports = bundleContent.includes('exports') || bundleContent.includes('module.exports');
                const hasRequire = bundleContent.includes('require');

                if (!hasExports && !hasRequire) {
                    throw new Error(`${fileName} does not appear to use CommonJS format`);
                }
            }
        }
    ),

    new TestCase(
        'E2E-17',
        'Client bundle does not include vscode module internals',
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
        'Server bundle contains error message normalization logic',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
            const bundleContent = fs.readFileSync(bundlePath, 'utf8');
            if (!bundleContent.includes('normalizeSyntaxMessage') && !bundleContent.includes('Missing semicolon')) {
                throw new Error('Error message normalization logic not found in bundle');
            }
        }
    ),

    new TestCase(
        'E2E-19',
        'Server bundle contains ANTLR error listener implementation',
        async () => {
            const bundlePath = path.join(__dirname, '..', 'dist', 'server.js');
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

#!/usr/bin/env node

/**
 * Import-aware VSCode editor support verification script.
 *
 * This script verifies the new lightweight import-aware editor capabilities:
 * - import path resolution, including directory entry imports via main.fcstm
 * - missing import diagnostics
 * - circular import diagnostics
 * - go to definition for import paths
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const Module = require('module');
const originalRequire = Module.prototype.require;

const vscode = {
    DiagnosticSeverity: {
        Error: 0,
        Warning: 1,
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
    Diagnostic: class Diagnostic {
        constructor(range, message, severity) {
            this.range = range;
            this.message = message;
            this.severity = severity;
            this.source = undefined;
        }
    },
    Location: class Location {
        constructor(uri, range) {
            this.uri = uri;
            this.range = range;
        }
    },
    Uri: {
        file(filePath) {
            return { fsPath: filePath };
        }
    }
};

Module.prototype.require = function(id) {
    if (id === 'vscode') {
        return vscode;
    }
    return originalRequire.apply(this, arguments);
};

const { FcstmImportWorkspaceIndex } = require('../out/imports');
const { FcstmDefinitionProvider } = require('../out/definition');

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

class MockDocument {
    constructor(filePath, text) {
        this.uri = { fsPath: filePath, toString: () => filePath };
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
            text: this.lines[line] || ''
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

function makeTempDir() {
    return fs.mkdtempSync(path.join(os.tmpdir(), 'fcstm-vscode-phase8-'));
}

const tests = [
    new TestCase(
        'P8-01',
        'Workspace index resolves direct imported file and extracts root summary',
        async () => {
            const dir = makeTempDir();
            const workerFile = path.join(dir, 'worker.fcstm');
            const hostFile = path.join(dir, 'host.fcstm');
            fs.writeFileSync(workerFile, 'def int speed = 0;\nstate Worker {\n    event Start;\n}');
            const text = 'state Root {\n    import "./worker.fcstm" as Worker;\n}';
            const document = new MockDocument(hostFile, text);
            const index = new FcstmImportWorkspaceIndex();
            const resolved = await index.resolveImportsForDocument(document);
            assert(resolved.length === 1, `Expected 1 resolved import, got ${resolved.length}`);
            assert(resolved[0].entryFile === workerFile, `Unexpected entry file: ${resolved[0].entryFile}`);
            assert(resolved[0].rootStateName === 'Worker', `Unexpected root state: ${resolved[0].rootStateName}`);
            assert(resolved[0].explicitVariables.includes('speed'), 'Imported variable summary missing speed');
            assert(resolved[0].absoluteEvents.includes('/Start'), 'Imported absolute event summary missing /Start');
        }
    ),
    new TestCase(
        'P8-02',
        'Workspace index resolves directory imports through main.fcstm',
        async () => {
            const dir = makeTempDir();
            const moduleDir = path.join(dir, 'motor');
            fs.mkdirSync(moduleDir);
            const mainFile = path.join(moduleDir, 'main.fcstm');
            const hostFile = path.join(dir, 'host.fcstm');
            fs.writeFileSync(mainFile, 'state MotorRoot { event Start; }');
            const text = 'state Root {\n    import "./motor" as Motor;\n}';
            const document = new MockDocument(hostFile, text);
            const index = new FcstmImportWorkspaceIndex();
            const resolved = await index.resolveImportsForDocument(document);
            assert(resolved[0].entryFile === mainFile, `Expected main.fcstm entry, got ${resolved[0].entryFile}`);
            assert(resolved[0].rootStateName === 'MotorRoot', `Unexpected root state: ${resolved[0].rootStateName}`);
        }
    ),
    new TestCase(
        'P8-03',
        'Import diagnostics report missing import files',
        async () => {
            const dir = makeTempDir();
            const hostFile = path.join(dir, 'host.fcstm');
            const text = 'state Root {\n    import "./missing.fcstm" as Missing;\n}';
            const document = new MockDocument(hostFile, text);
            const index = new FcstmImportWorkspaceIndex();
            const diagnostics = await index.collectImportDiagnostics(document);
            assert(diagnostics.some(item => /cannot be resolved/i.test(item.message)), 'Missing-file diagnostic not found');
        }
    ),
    new TestCase(
        'P8-04',
        'Import diagnostics report circular imports',
        async () => {
            const dir = makeTempDir();
            const aFile = path.join(dir, 'a.fcstm');
            const bFile = path.join(dir, 'b.fcstm');
            fs.writeFileSync(aFile, 'state A { import "./b.fcstm" as B; }');
            fs.writeFileSync(bFile, 'state B { import "./a.fcstm" as A; }');
            const document = new MockDocument(aFile, fs.readFileSync(aFile, 'utf8'));
            const index = new FcstmImportWorkspaceIndex();
            const diagnostics = await index.collectImportDiagnostics(document);
            assert(diagnostics.some(item => /circular import/i.test(item.message)), 'Circular import diagnostic not found');
        }
    ),
    new TestCase(
        'P8-05',
        'Definition provider jumps from import path to target file',
        async () => {
            const dir = makeTempDir();
            const workerFile = path.join(dir, 'worker.fcstm');
            const hostFile = path.join(dir, 'host.fcstm');
            fs.writeFileSync(workerFile, 'state Worker;');
            const text = 'state Root {\n    import "./worker.fcstm" as Worker;\n}';
            const document = new MockDocument(hostFile, text);
            const provider = new FcstmDefinitionProvider();
            const location = await provider.provideDefinition(document, new vscode.Position(1, 15), {});
            assert(location, 'Expected definition location, got null');
            assert(location.uri.fsPath === workerFile, `Expected target ${workerFile}, got ${location.uri.fsPath}`);
        }
    )
];

async function main() {
    console.log(`${colors.cyan}FCSTM VSCode Import Editor Support Verification${colors.reset}`);
    console.log(`${colors.cyan}================================================${colors.reset}`);

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
        console.log(`${colors.green}All import editor support verification checkpoints passed.${colors.reset}`);
        process.exit(0);
    } else {
        console.log(`${colors.red}Some import editor support verification checkpoints failed.${colors.reset}`);
        process.exit(1);
    }
}

main().catch(error => {
    console.error(`${colors.red}Fatal error:${colors.reset}`, error);
    process.exit(1);
});

const fs = require('fs');
const path = require('path');
const yaml = require('js-yaml');

const packageDir = path.resolve(__dirname, '..');
const sourceDir = path.join(packageDir, 'src', 'dsl', 'grammar');
const targetDir = path.join(packageDir, 'dist', 'dsl', 'grammar');

// pyfcstm is the single source of truth for the shared diagnostics
// schema and the diagnostic code registry; sync both into jsfcstm
// ``dist/diagnostics`` so the published npm package and the bundled
// VSIX carry the same contract resources and the JS side can
// validate / dispatch against them at runtime.
//
// ``codes.yaml`` is converted to ``codes.json`` during sync so the
// jsfcstm consumer needs no YAML dependency; pyfcstm keeps the YAML
// source for hand-editing comfort.
const repoRoot = path.resolve(packageDir, '..', '..');
const sharedSchemaSource = path.join(repoRoot, 'pyfcstm', 'diagnostics', 'schema.json');
const sharedSchemaSrcTarget = path.join(packageDir, 'src', 'diagnostics', 'schema.json');
const sharedSchemaDistTarget = path.join(packageDir, 'dist', 'diagnostics', 'schema.json');
const sharedCodesSource = path.join(repoRoot, 'pyfcstm', 'diagnostics', 'codes.yaml');
const sharedCodesSrcTarget = path.join(packageDir, 'src', 'diagnostics', 'codes.json');
const sharedCodesDistTarget = path.join(packageDir, 'dist', 'diagnostics', 'codes.json');

function ensureSourceExists() {
    if (!fs.existsSync(sourceDir)) {
        throw new Error(`Generated grammar source directory not found: ${sourceDir}`);
    }
}

function ensureSharedSchemaExists() {
    if (!fs.existsSync(sharedSchemaSource)) {
        throw new Error(
            `Shared diagnostics schema not found: ${sharedSchemaSource}. ` +
            `It must be checked in under pyfcstm/diagnostics/schema.json.`
        );
    }
}

function copyTree(sourcePath, targetPath) {
    const stat = fs.statSync(sourcePath);
    if (stat.isDirectory()) {
        fs.mkdirSync(targetPath, {recursive: true});
        for (const child of fs.readdirSync(sourcePath)) {
            copyTree(path.join(sourcePath, child), path.join(targetPath, child));
        }
        return;
    }

    fs.mkdirSync(path.dirname(targetPath), {recursive: true});
    fs.copyFileSync(sourcePath, targetPath);
}

function copyFile(source, target) {
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.copyFileSync(source, target);
}

function writeJson(target, payload) {
    fs.mkdirSync(path.dirname(target), {recursive: true});
    fs.writeFileSync(target, JSON.stringify(payload, null, 2) + '\n');
}

function syncSharedSchemaSrc() {
    ensureSharedSchemaExists();
    copyFile(sharedSchemaSource, sharedSchemaSrcTarget);
}

function syncSharedSchemaDist() {
    ensureSharedSchemaExists();
    copyFile(sharedSchemaSource, sharedSchemaDistTarget);
}

function syncSharedCodesSrc() {
    if (!fs.existsSync(sharedCodesSource)) {
        throw new Error(
            `Shared diagnostic codes registry not found: ${sharedCodesSource}. ` +
            `It must be checked in under pyfcstm/diagnostics/codes.yaml.`
        );
    }
    const text = fs.readFileSync(sharedCodesSource, 'utf-8');
    const registry = yaml.load(text);
    writeJson(sharedCodesSrcTarget, registry);
    writeJson(sharedCodesDistTarget, registry);
}

const args = new Set(process.argv.slice(2));
const phase = args.has('--phase=src')
    ? 'src'
    : args.has('--phase=dist')
        ? 'dist'
        : 'all';

function runSrcPhase() {
    syncSharedSchemaSrc();
    syncSharedCodesSrc();
}

function runDistPhase() {
    ensureSourceExists();
    fs.rmSync(targetDir, {recursive: true, force: true});
    copyTree(sourceDir, targetDir);
    syncSharedSchemaDist();
}

function main() {
    if (phase === 'src') {
        runSrcPhase();
        return;
    }
    if (phase === 'dist') {
        runDistPhase();
        return;
    }
    runSrcPhase();
    runDistPhase();
}

main();

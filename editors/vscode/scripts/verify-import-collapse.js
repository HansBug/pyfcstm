#!/usr/bin/env node
// Verifies task 18: import-boundary states default to collapsed, and
// the user can expand one layer at a time. Mirrors the seed logic from
// ``PreviewManager.refresh`` without actually booting VSCode.
//
// Strategy:
//   1. Build the payload once with ``collapsedStateIds: []``.
//   2. Collect every state whose ``importedFromFile`` is set.
//   3. Rebuild the payload with those ids in ``collapsedStateIds``.
//   4. Dump the graph for both runs so we can compare visible children.

const fs = require('fs');
const path = require('path');
const Module = require('module');

const fixture = process.argv[2];
const outDir = process.argv[3];
if (!fixture || !outDir) {
    console.error('usage: verify-import-collapse.js <fixture.fcstm> <out-dir>');
    process.exit(2);
}
fs.mkdirSync(outDir, {recursive: true});

const originalRequire = Module.prototype.require;
Module.prototype.require = function(id) {
    if (id === 'vscode') {
        return {
            Uri: {file: (p) => ({scheme: 'file', fsPath: p, toString: () => 'file://' + p})},
            workspace: {textDocuments: []},
        };
    }
    return originalRequire.apply(this, arguments);
};
const {buildFcstmDiagramWebviewPayload} =
    require(path.resolve(__dirname, '..', 'node_modules', '@pyfcstm', 'jsfcstm'));
Module.prototype.require = originalRequire;

function createDocument(filePath) {
    const text = fs.readFileSync(filePath, 'utf8');
    const lines = () => text.split('\n');
    return {
        languageId: 'fcstm',
        fileName: filePath,
        uri: {scheme: 'file', fsPath: filePath, toString: () => 'file://' + filePath},
        getText: () => text,
        lineCount: lines().length,
        lineAt: (line) => ({text: lines()[line] || ''}),
    };
}

function listElkLeafIds(root) {
    const ids = [];
    const walk = (n) => {
        if (!n) return;
        ids.push(n.id);
        (n.children || []).forEach(walk);
    };
    walk(root);
    return ids;
}

(async () => {
    const doc = createDocument(fixture);

    console.log('=== pass 1: collapsed=[] ===');
    const pass1 = await buildFcstmDiagramWebviewPayload(doc, {}, {collapsedStateIds: new Set()});
    const boundaries = pass1.states
        .filter(s => s.importedFromFile)
        .map(s => s.qualifiedName);
    console.log('import boundaries:', boundaries);
    console.log('elk ids (pass 1):', listElkLeafIds(pass1.graph.children[0]).slice(0, 20));

    console.log('\n=== pass 2: collapsed = import boundaries ===');
    const pass2 = await buildFcstmDiagramWebviewPayload(doc, {}, {
        collapsedStateIds: new Set(boundaries),
    });
    console.log('elk ids (pass 2):', listElkLeafIds(pass2.graph.children[0]).slice(0, 20));

    // Write both payloads for eyeball inspection.
    fs.writeFileSync(path.join(outDir, 'pass1.json'), JSON.stringify(pass1, null, 2));
    fs.writeFileSync(path.join(outDir, 'pass2.json'), JSON.stringify(pass2, null, 2));

    // Simulate the "user expands only Factory.Line" case.
    const partial = new Set(boundaries);
    partial.delete('Factory.Line');    // expand Line; Robot stays collapsed.
    console.log('\n=== pass 3: Line expanded, Robot still collapsed ===');
    const pass3 = await buildFcstmDiagramWebviewPayload(doc, {}, {
        collapsedStateIds: partial,
    });
    console.log('elk ids (pass 3):', listElkLeafIds(pass3.graph.children[0]).slice(0, 30));
    fs.writeFileSync(path.join(outDir, 'pass3.json'), JSON.stringify(pass3, null, 2));

    // Also write three preview HTMLs so the user can screenshot them.
    const previewOptions = {};
    const webviewJs = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.js'), 'utf8');
    const webviewCss = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.css'), 'utf8');
    const elkJs = fs.readFileSync(path.resolve(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'), 'utf8');

    function writeHtml(name, payload, collapsed) {
        const state = {
            title: path.basename(fixture),
            filePath: fixture,
            rootStateName: payload.machineName,
            payload,
            previewOptions: payload.options,
            collapsedStateIds: Array.from(collapsed),
            emptyTitle: path.basename(fixture),
            emptyMessage: 'No diagram',
            summary: [],
            variables: [],
            sharedEvents: [],
            effectNotes: [],
        };
        const stub = '<script>window.acquireVsCodeApi=()=>({postMessage:()=>{},getState:()=>null,setState:()=>{}});</script>';
        const init = `<script>window.__FCSTM_INITIAL_STATE__=${JSON.stringify(state).replace(/</g, '\\u003c')};</script>`;
        const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>${webviewCss}
html,body,#app{margin:0;padding:0;height:100%;min-height:100%;background:#fff;}
</style></head><body>${stub}<div id="app"></div>${init}<script>${elkJs}</script><script>${webviewJs}</script></body></html>`;
        fs.writeFileSync(path.join(outDir, name + '.html'), html);
    }

    writeHtml('pass1-default-collapsed', pass2, boundaries);
    writeHtml('pass2-line-expanded-robot-collapsed', pass3, Array.from(partial));
    writeHtml('pass3-all-expanded', pass1, []);
    console.log('\ndone. inspect', outDir + '/pass{1,2,3}.json + *.html');
})().catch(err => { console.error(err); process.exit(1); });

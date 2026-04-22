#!/usr/bin/env node
/*
 * Debug harness: boots the actual preview HTML inside headless Chrome
 * via the DevTools Protocol, feeds it a real diagram payload (built from
 * a fixture .fcstm), then dumps console messages + the post-bootstrap
 * stage/details DOM so we can see why a preview renders blank.
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const {spawn, spawnSync} = require('child_process');

const Module = require('module');
const originalRequire = Module.prototype.require;

const tempDir = fs.mkdtempSync(path.join(os.tmpdir(), 'fcstm-preview-debug-'));
// leave tempDir on disk on purpose so we can inspect preview.html

// Mock enough of the vscode / workspace graph to satisfy the extension-host
// modules when we import buildFcstmDiagramWebviewPayload below.
Module.prototype.require = function(id) {
    if (id === 'vscode') {
        return {
            Uri: {file: (p) => ({scheme: 'file', fsPath: p, toString: () => 'file://' + p})},
            workspace: {textDocuments: []},
        };
    }
    return originalRequire.apply(this, arguments);
};

const {buildFcstmDiagramWebviewPayload, resolveFcstmDiagramPreviewOptions} =
    require(path.resolve(__dirname, '..', 'node_modules', '@pyfcstm', 'jsfcstm'));

Module.prototype.require = originalRequire;

function createDocument(filePath) {
    const text = fs.readFileSync(filePath, 'utf8');
    const lines = () => text.split('\n');
    return {
        languageId: 'fcstm',
        fileName: filePath,
        uri: {scheme: 'file', fsPath: filePath, toString() { return 'file://' + filePath; }},
        getText() { return text; },
        lineCount: lines().length,
        lineAt(line) { return {text: lines()[line] || ''}; },
    };
}

// Read webview HTML by requiring the compiled preview module and calling
// createPreviewHtml via the exported symbol. Since that helper is internal
// we cheat by reading the module source and locating the template.
function extractCreatePreviewHtml() {
    const previewJs = fs.readFileSync(path.resolve(__dirname, '..', 'out', 'preview.js'), 'utf8');
    // The simpler approach: instantiate the same HTML machinery by requiring
    // out/preview.js and re-using its internal template. Node doesn't expose
    // it, so we reimplement a thin wrapper with the essentials.
    // Instead, we inline-load preview.js, grab its createPreviewHtml via a
    // side channel we append below.
    const shim = previewJs + '\nmodule.exports.__createPreviewHtml = createPreviewHtml;';
    const shimPath = path.join(__dirname, '..', 'out', '_preview-debug-shim.js');
    fs.writeFileSync(shimPath, shim);
    delete require.cache[shimPath];
    Module.prototype.require = function(id) {
        if (id === 'vscode') {
            return {Uri: {}, workspace: {textDocuments: []}};
        }
        return originalRequire.apply(this, arguments);
    };
    const mod = require(shimPath);
    Module.prototype.require = originalRequire;
    return mod.__createPreviewHtml;
}

function fakeWebview() {
    return {cspSource: 'vscode-resource://debug'};
}

async function buildWebviewHtml(fixturePath) {
    const createPreviewHtml = extractCreatePreviewHtml();
    const doc = createDocument(fixturePath);
    const payload = await buildFcstmDiagramWebviewPayload(doc, 'normal');
    const resolvedOptions = resolveFcstmDiagramPreviewOptions('normal');
    const initialState = {
        title: path.basename(fixturePath),
        filePath: fixturePath,
        rootStateName: payload ? payload.machineName : undefined,
        payload: payload || undefined,
        previewOptions: resolvedOptions,
        collapsedStateIds: [],
        emptyTitle: path.basename(fixturePath),
        emptyMessage: 'Loading preview',
        summary: [],
        variables: [],
        sharedEvents: [],
        effectNotes: [],
        diagnostics: [],
        status: 'ok',
        statusText: 'Live preview',
    };
    return createPreviewHtml(fakeWebview(), '/* elk runtime inlined below */', initialState);
}

function locateChrome() {
    for (const cand of ['google-chrome', 'google-chrome-stable', 'chromium', 'chromium-browser']) {
        const r = spawnSync('which', [cand]);
        if (r.status === 0 && r.stdout.toString().trim()) return r.stdout.toString().trim();
    }
    return null;
}

function rpcSend(ws, id, method, params) {
    return new Promise((resolve, reject) => {
        const listener = (msg) => {
            const body = JSON.parse(msg.toString());
            if (body.id === id) {
                ws.off('message', listener);
                if (body.error) reject(new Error(body.error.message));
                else resolve(body.result);
            }
        };
        ws.on('message', listener);
        ws.send(JSON.stringify({id, method, params}));
    });
}

async function main() {
    const fixture = process.argv[2] || path.resolve(__dirname, '..', '..', 'jsfcstm', 'test', 'fixtures', 'visual', '01-simple-leaf.fcstm');
    const chrome = locateChrome();
    if (!chrome) {
        console.log('\x1b[33m⚠\x1b[0m chromium not found on PATH — skipping preview-in-Chrome verification.');
        return;
    }
    const html = await buildWebviewHtml(fixture);

    // Write the elkjs runtime directly because our createPreviewHtml was
    // invoked with a placeholder instead of the real bundle.
    const elkPath = path.resolve(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js');
    const elkSrc = fs.readFileSync(elkPath, 'utf8');
    // Use a function replacer so $ tokens in elkSrc aren't interpreted.
    const withElk = html.replace('/* elk runtime inlined below */', () => elkSrc);
    // Stub ``acquireVsCodeApi`` so the webview script can bootstrap outside
    // of the real VSCode host. CSP forbids inline <script> without a nonce,
    // so we relax CSP to script-src * for this debug harness only.
    const stub = '<script>window.acquireVsCodeApi = () => ({ postMessage:()=>{}, getState:()=>null, setState:()=>{} });</script>';
    const patchedHtml = withElk
        .replace(/script-src [^;]+;/, "script-src * 'unsafe-inline' 'unsafe-eval';")
        .replace('<body>', () => '<body>' + stub);

    const htmlFile = path.join(tempDir, 'preview.html');
    fs.writeFileSync(htmlFile, patchedHtml);
    // eslint-disable-next-line no-console
    console.log('HTML written to', htmlFile);

    // Launch chromium with remote debugging; we'll talk DevTools Protocol.
    const port = 9222;
    const proc = spawn(chrome, [
        '--headless=new',
        '--disable-gpu',
        '--hide-scrollbars',
        '--no-sandbox',
        '--remote-debugging-port=' + port,
        '--window-size=1600,1200',
        'file://' + htmlFile,
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    let stderrBuf = '';
    proc.stderr.on('data', d => { stderrBuf += d.toString(); });

    try {
        // Wait for the debugging endpoint
        const endpoint = await new Promise((resolve, reject) => {
            const startedAt = Date.now();
            const tryFetch = () => {
                http.get({host: '127.0.0.1', port, path: '/json/version'}, res => {
                    let body = '';
                    res.on('data', c => body += c);
                    res.on('end', () => resolve(JSON.parse(body)));
                }).on('error', () => {
                    if (Date.now() - startedAt > 8000) return reject(new Error('chrome did not expose devtools'));
                    setTimeout(tryFetch, 150);
                });
            };
            tryFetch();
        });

        const pagesList = await new Promise((resolve, reject) => {
            http.get({host: '127.0.0.1', port, path: '/json'}, res => {
                let body = '';
                res.on('data', c => body += c);
                res.on('end', () => resolve(JSON.parse(body)));
            }).on('error', reject);
        });
        const pageWs = pagesList.find(p => p.type === 'page').webSocketDebuggerUrl;

        let WebSocket;
        try { WebSocket = require('ws'); } catch (e) {
            console.log('\x1b[33m⚠\x1b[0m ws module missing — skipping preview-in-Chrome verification (install with `npm install --no-save ws`).');
            return;
        }
        const ws = new WebSocket(pageWs);
        await new Promise((resolve, reject) => { ws.once('open', resolve); ws.once('error', reject); });
        ws.off = ws.removeListener;

        const consoleLogs = [];
        const pageErrors = [];
        ws.on('message', (msg) => {
            const body = JSON.parse(msg.toString());
            if (body.method === 'Runtime.consoleAPICalled') {
                const args = body.params.args.map(a => a.value != null ? a.value : (a.description || JSON.stringify(a)));
                consoleLogs.push('[' + body.params.type + '] ' + args.join(' '));
            } else if (body.method === 'Runtime.exceptionThrown') {
                pageErrors.push(body.params.exceptionDetails);
            }
        });

        let id = 0;
        await rpcSend(ws, ++id, 'Runtime.enable');
        await rpcSend(ws, ++id, 'Page.enable');
        await new Promise(r => setTimeout(r, 2000));

        const domInfo = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `JSON.stringify({
                stageEmpty: {
                    hidden: document.getElementById('stage-empty').classList.contains('hidden'),
                    title: document.getElementById('stage-empty-title').textContent,
                    message: document.getElementById('stage-empty-message').textContent.slice(0, 400),
                },
                svgPresent: !!document.querySelector('#viewport-inner svg'),
                svgChildren: document.querySelector('#viewport-inner svg') ? document.querySelectorAll('#viewport-inner svg > *').length : 0,
                detailsEmpty: document.getElementById('details-empty').textContent.slice(0, 200),
                title: document.getElementById('title').textContent,
            })`,
            returnByValue: true,
        });

        ws.close();

        const state = JSON.parse(domInfo.result.value);
        // Ignore the missing acquireVsCodeApi ReferenceError — the stub
        // injection happens before the webview script, so we only see it
        // if the harness itself failed to stub. The harness stub is there
        // for a reason: upstream we expect no other errors.
        const fatalErrors = pageErrors.filter(e => {
            const desc = (e.exception && e.exception.description) || e.text || '';
            if (/acquireVsCodeApi is not defined/.test(desc)) return false;
            return true;
        });

        const checks = [];
        const record = (label, ok, details) => {
            checks.push({label, ok, details});
            const mark = ok ? '\x1b[32m✅\x1b[0m' : '\x1b[31m❌\x1b[0m';
            console.log(mark + ' ' + label + (details && !ok ? ' — ' + details : ''));
        };

        record('no page errors in console', fatalErrors.length === 0,
            fatalErrors.map(e => (e.exception && e.exception.description) || e.text || JSON.stringify(e)).join('\n'));
        record('viewport SVG renders', state.svgPresent === true,
            'stageEmpty=' + JSON.stringify(state.stageEmpty));
        record('SVG has actual children (diagram not empty)', state.svgChildren > 0,
            'svgChildren=' + state.svgChildren);
        record('stage-empty is hidden when preview is ready', state.stageEmpty.hidden === true,
            'stageEmpty=' + JSON.stringify(state.stageEmpty));
        record('title shows the root state', /Switch/.test(state.title),
            'title=' + JSON.stringify(state.title));

        const passed = checks.filter(c => c.ok).length;
        const failed = checks.length - passed;
        console.log('');
        console.log('\x1b[36mSummary\x1b[0m');
        console.log('\x1b[36m-------\x1b[0m');
        console.log('Total checkpoints: ' + checks.length);
        console.log('Passed: ' + passed);
        console.log('Failed: ' + failed);
        if (failed > 0) {
            console.log('=== console logs ===');
            for (const line of consoleLogs) console.log(line);
            console.log('=== page errors ===');
            for (const err of pageErrors) console.log(JSON.stringify(err, null, 2));
            console.error('\x1b[31mPreview-in-Chrome verification failed.\x1b[0m');
            process.exitCode = 1;
        } else {
            console.log('\x1b[32mAll preview-in-Chrome checkpoints passed.\x1b[0m');
        }
    } finally {
        proc.kill();
    }
}

main().catch(err => {
    console.error('verify-preview-renders failed:', err);
    process.exit(1);
});

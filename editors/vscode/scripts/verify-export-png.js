#!/usr/bin/env node
// Boots the preview webview, triggers the Export flow, intercepts
// the exportDiagram postMessage, and writes the PNG payload to disk
// so we can verify it contains only the diagram (no UI chrome).
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const {spawn, spawnSync} = require('child_process');
const Module = require('module');

const fixture = process.argv[2];
const outDir = process.argv[3];
if (!fixture || !outDir) {
    console.error('usage: verify-export-png.js <fixture.fcstm> <out-dir>');
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
const {buildFcstmDiagramWebviewPayload, resolveFcstmDiagramPreviewOptions} =
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

function locateChrome() {
    for (const name of ['chromium', 'chromium-browser', 'google-chrome', 'google-chrome-stable']) {
        const res = spawnSync('which', [name]);
        if (res.status === 0 && res.stdout.toString().trim()) return res.stdout.toString().trim();
    }
    return null;
}
function rpcSend(ws, id, method, params) {
    return new Promise((resolve, reject) => {
        const handler = (raw) => {
            const body = JSON.parse(raw.toString());
            if (body.id === id) {
                ws.off('message', handler);
                if (body.error) reject(new Error(body.error.message));
                else resolve(body.result);
            }
        };
        ws.on('message', handler);
        ws.send(JSON.stringify({id, method, params: params || {}}));
    });
}

(async () => {
    const chrome = locateChrome();
    if (!chrome) { console.error('chromium not found'); process.exit(1); }
    const previewOptions = resolveFcstmDiagramPreviewOptions({});
    const doc = createDocument(fixture);
    const payload = await buildFcstmDiagramWebviewPayload(doc, {}, {collapsedStateIds: new Set()});
    const state = {
        title: path.basename(fixture),
        filePath: fixture,
        rootStateName: payload.machineName,
        payload,
        previewOptions,
        collapsedStateIds: [],
        emptyTitle: path.basename(fixture),
        emptyMessage: 'No diagram',
        summary: [],
        variables: [],
        sharedEvents: [],
        effectNotes: [],
    };
    const webviewJs = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.js'), 'utf8');
    const webviewCss = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.css'), 'utf8');
    const elkJs = fs.readFileSync(path.resolve(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'), 'utf8');
    const init = `<script>window.__FCSTM_INITIAL_STATE__=${JSON.stringify(state).replace(/</g, '\\u003c')};
window.__fcstmPosted=[];
window.acquireVsCodeApi=()=>({postMessage:(m)=>{window.__fcstmPosted.push(m);},getState:()=>null,setState:()=>{}});
</script>`;
    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>${webviewCss}
html,body,#app{margin:0;padding:0;height:100%;background:#fff;}</style></head>
<body>${init}<div id="app"></div><script>${elkJs}</script><script>${webviewJs}</script></body></html>`;
    const htmlFile = path.join(outDir, 'preview.html');
    fs.writeFileSync(htmlFile, html);

    const port = 9363;
    const proc = spawn(chrome, [
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-sandbox',
        '--remote-debugging-port=' + port, '--window-size=1800,1200',
        'file://' + htmlFile,
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    try {
        await new Promise((resolve, reject) => {
            const t0 = Date.now();
            const poll = () => {
                http.get({host: '127.0.0.1', port, path: '/json/version'}, res => {
                    let b = ''; res.on('data', c => b += c);
                    res.on('end', () => resolve(JSON.parse(b)));
                }).on('error', () => {
                    if (Date.now() - t0 > 8000) return reject(new Error('chrome timeout'));
                    setTimeout(poll, 150);
                });
            };
            poll();
        });
        const pages = await new Promise((resolve, reject) => {
            http.get({host: '127.0.0.1', port, path: '/json'}, res => {
                let b = ''; res.on('data', c => b += c);
                res.on('end', () => resolve(JSON.parse(b)));
            }).on('error', reject);
        });
        const WebSocket = require('ws');
        const ws = new WebSocket(pages.find(p => p.type === 'page').webSocketDebuggerUrl);
        await new Promise((resolve, reject) => { ws.once('open', resolve); ws.once('error', reject); });
        ws.off = ws.removeListener;
        let id = 0;
        await rpcSend(ws, ++id, 'Runtime.enable');

        // Wait for ELK to finish the layout.
        await new Promise(r => setTimeout(r, 3000));

        // Trigger the Export flow by dispatching the keyboard shortcut.
        await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `window.dispatchEvent(new CustomEvent('fcstm-export'))`,
        });

        // Give the canvas pipeline a moment to render the PNG.
        await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: 'new Promise(r => setTimeout(r, 2500))',
            awaitPromise: true,
        });

        // Pull the intercepted postMessage payload.
        const msgs = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: 'JSON.stringify(window.__fcstmPosted.filter(m=>m && m.type==="exportDiagram"))',
            returnByValue: true,
        });
        const payloadStr = msgs.result.value || '[]';
        const posted = JSON.parse(payloadStr);
        if (!posted.length) {
            console.error('no exportDiagram posted — check extension flow');
            process.exit(3);
        }
        const {svg, pngBase64, pdfBase64} = posted[0];
        fs.writeFileSync(path.join(outDir, 'exported.svg'), svg);
        fs.writeFileSync(path.join(outDir, 'exported.png'), Buffer.from(pngBase64, 'base64'));
        console.log('wrote exported.svg (' + svg.length + ' bytes)');
        console.log('wrote exported.png (' + Buffer.byteLength(pngBase64, 'base64') + ' bytes)');
        if (pdfBase64) {
            fs.writeFileSync(path.join(outDir, 'exported.pdf'), Buffer.from(pdfBase64, 'base64'));
            console.log('wrote exported.pdf (' + Buffer.byteLength(pdfBase64, 'base64') + ' bytes)');
        } else {
            console.log('pdfBase64 missing from exportDiagram payload');
        }

        ws.close();
    } finally {
        proc.kill('SIGTERM');
    }
})().catch(err => { console.error(err); process.exit(1); });

#!/usr/bin/env node
// Verifies task 19: the bottom DetailsPanel + BottomPanels live in a
// bounded, resizable, collapsible drawer. Captures three states:
//   1. 01-default       — drawer at its default height
//   2. 02-collapsed     — drawer collapsed via the toggle button
//   3. 03-dragged-up    — drawer resized to a larger height via the drag handle
const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const {spawn, spawnSync} = require('child_process');
const Module = require('module');

const fixture = process.argv[2];
const outDir = process.argv[3];
if (!fixture || !outDir) {
    console.error('usage: verify-bottom-drawer.js <fixture.fcstm> <out-dir>');
    process.exit(2);
}
fs.mkdirSync(outDir, {recursive: true});

const originalRequire = Module.prototype.require;
Module.prototype.require = function(id) {
    if (id === 'vscode') return {
        Uri: {file: (p) => ({scheme: 'file', fsPath: p, toString: () => 'file://' + p})},
        workspace: {textDocuments: []},
    };
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
        getText: () => text, lineCount: lines().length,
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
        title: path.basename(fixture), filePath: fixture,
        rootStateName: payload.machineName, payload, previewOptions,
        collapsedStateIds: [], emptyTitle: path.basename(fixture),
        emptyMessage: 'No diagram',
        summary: [
            {label: 'States', value: '5 leaf · 2 composite'},
            {label: 'Transitions', value: '14 (1 forced)'},
            {label: 'Events', value: 'Pause · Resume · Tick · Heartbeat'},
        ],
        variables: ['counter: int = 0', 'temperature: float = 25.0', 'error_count: int = 0'],
        sharedEvents: [],
        effectNotes: [],
    };
    const webviewJs = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.js'), 'utf8');
    const webviewCss = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.css'), 'utf8');
    const elkJs = fs.readFileSync(path.resolve(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'), 'utf8');
    const init = `<script>
// Clear any persisted drawer state so each run starts predictable.
try { localStorage.removeItem('fcstm.preview.drawerHeight'); localStorage.removeItem('fcstm.preview.drawerCollapsed'); } catch {}
window.__FCSTM_INITIAL_STATE__=${JSON.stringify(state).replace(/</g, '\\u003c')};
window.acquireVsCodeApi=()=>({postMessage:()=>{},getState:()=>null,setState:()=>{}});
</script>`;
    const html = `<!DOCTYPE html><html><head><meta charset="UTF-8"><style>${webviewCss}
html,body,#app{margin:0;padding:0;height:100%;background:#fff;}</style></head>
<body>${init}<div id="app"></div><script>${elkJs}</script><script>${webviewJs}</script></body></html>`;
    fs.writeFileSync(path.join(outDir, 'preview.html'), html);

    const port = 9373;
    const proc = spawn(chrome, [
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-sandbox',
        '--remote-debugging-port=' + port, '--window-size=1600,1200',
        'file://' + path.join(outDir, 'preview.html'),
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    try {
        await new Promise((resolve, reject) => {
            const t0 = Date.now();
            const poll = () => http.get({host: '127.0.0.1', port, path: '/json/version'}, res => {
                let b = ''; res.on('data', c => b += c);
                res.on('end', () => resolve(JSON.parse(b)));
            }).on('error', () => {
                if (Date.now() - t0 > 8000) return reject(new Error('chrome timeout'));
                setTimeout(poll, 150);
            });
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
        await rpcSend(ws, ++id, 'Page.enable');
        await new Promise(r => setTimeout(r, 1500));
        await rpcSend(ws, ++id, 'Runtime.evaluate', {expression: 'new Promise(r => setTimeout(r, 1500))', awaitPromise: true});

        async function shot(name) {
            await rpcSend(ws, ++id, 'Runtime.evaluate', {
                expression: 'new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))',
                awaitPromise: true,
            });
            const r = await rpcSend(ws, ++id, 'Page.captureScreenshot', {format: 'png'});
            fs.writeFileSync(path.join(outDir, name + '.png'), Buffer.from(r.data, 'base64'));
            console.log('shot:', name);
        }

        // Read drawer geometry for later moves.
        const geom = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => {
                const drawer = document.querySelector('.fcstm-bottom-drawer');
                const handle = document.querySelector('.fcstm-bottom-drawer__handle');
                const toggle = document.querySelector('.fcstm-bottom-drawer__toggle');
                if (!drawer || !handle || !toggle) return null;
                const dr = drawer.getBoundingClientRect();
                const hr = handle.getBoundingClientRect();
                const tr = toggle.getBoundingClientRect();
                return {drawerHeight: dr.height, handleY: hr.top + hr.height/2, handleX: hr.left + hr.width/2, toggleX: tr.left + tr.width/2, toggleY: tr.top + tr.height/2};
            })()`,
            returnByValue: true,
        });
        console.log('drawer geometry:', geom.result.value);

        // 1) default
        await shot('01-default');

        // 2) collapse via toggle click
        const gv = geom.result.value;
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mousePressed', x: gv.toggleX, y: gv.toggleY, button: 'left', clickCount: 1});
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mouseReleased', x: gv.toggleX, y: gv.toggleY, button: 'left', clickCount: 1});
        await new Promise(r => setTimeout(r, 300));
        await shot('02-collapsed');

        // Expand again to test drag.
        const toggleAgain = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => {
                const t = document.querySelector('.fcstm-bottom-drawer__toggle');
                if (!t) return null;
                const r = t.getBoundingClientRect();
                return {x: r.left + r.width/2, y: r.top + r.height/2};
            })()`,
            returnByValue: true,
        });
        const t2 = toggleAgain.result.value;
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mousePressed', x: t2.x, y: t2.y, button: 'left', clickCount: 1});
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mouseReleased', x: t2.x, y: t2.y, button: 'left', clickCount: 1});
        await new Promise(r => setTimeout(r, 300));

        // 3) drag the handle up by 120px so drawer becomes larger.
        const g2 = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => {
                const h = document.querySelector('.fcstm-bottom-drawer__handle');
                const d = document.querySelector('.fcstm-bottom-drawer');
                if (!h || !d) return null;
                const hr = h.getBoundingClientRect();
                return {hx: hr.left + hr.width/2, hy: hr.top + hr.height/2, startHeight: d.getBoundingClientRect().height};
            })()`,
            returnByValue: true,
        });
        const g = g2.result.value;
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mousePressed', x: g.hx, y: g.hy, button: 'left', clickCount: 1});
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mouseMoved', x: g.hx, y: g.hy - 150, buttons: 1});
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mouseReleased', x: g.hx, y: g.hy - 150, button: 'left'});
        await new Promise(r => setTimeout(r, 300));
        const after = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `document.querySelector('.fcstm-bottom-drawer').getBoundingClientRect().height`,
            returnByValue: true,
        });
        console.log('height start:', g.startHeight, '→ after drag:', after.result.value);
        await shot('03-dragged-up');

        ws.close();
    } finally {
        proc.kill('SIGTERM');
    }
})().catch(err => { console.error(err); process.exit(1); });

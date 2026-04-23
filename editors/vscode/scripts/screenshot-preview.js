#!/usr/bin/env node
/*
 * One-off harness that renders a given .fcstm fixture into the bundled
 * preview HTML, boots it in headless Chrome, and saves the rendered
 * SVG + a PNG screenshot so a human can eyeball the layout.
 *
 * Usage: node scripts/screenshot-preview.js <fixture.fcstm> [out-dir]
 */

const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const {spawn, spawnSync} = require('child_process');
const Module = require('module');

const fixture = process.argv[2];
if (!fixture) {
    console.error('usage: node screenshot-preview.js <fixture.fcstm> [out-dir]');
    process.exit(1);
}
const outDir = process.argv[3] || fs.mkdtempSync(path.join(os.tmpdir(), 'fcstm-screenshot-'));
fs.mkdirSync(outDir, {recursive: true});
console.log('output dir:', outDir);

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
    const envChrome = process.env.CHROME_BIN || process.env.PUPPETEER_EXECUTABLE_PATH;
    if (envChrome && fs.existsSync(envChrome)) return envChrome;
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

async function buildPreviewHtml(fixturePath) {
    const previewOptions = resolveFcstmDiagramPreviewOptions({});
    const doc = createDocument(fixturePath);
    const payload = await buildFcstmDiagramWebviewPayload(doc, {}, {collapsedStateIds: new Set()});

    const state = {
        title: path.basename(fixturePath),
        filePath: fixturePath,
        rootStateName: payload ? payload.machineName : undefined,
        payload: payload || undefined,
        previewOptions,
        collapsedStateIds: [],
        emptyTitle: path.basename(fixturePath),
        emptyMessage: 'No diagram',
        summary: [],
        variables: [],
        sharedEvents: [],
        effectNotes: [],
    };

    const webviewJs = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.js'), 'utf8');
    const webviewCss = fs.readFileSync(path.resolve(__dirname, '..', 'dist', 'preview-webview.css'), 'utf8');
    const elkJs = fs.readFileSync(path.resolve(__dirname, '..', 'node_modules', 'elkjs', 'lib', 'elk.bundled.js'), 'utf8');

    const stub = `<script>window.acquireVsCodeApi = () => ({ postMessage:()=>{}, getState:()=>null, setState:()=>{} });</script>`;
    const init = `<script>window.__FCSTM_INITIAL_STATE__ = ${JSON.stringify(state).replace(/</g, '\\u003c')};</script>`;
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>${webviewCss}
html, body, #app { margin: 0; padding: 0; height: 100%; min-height: 100%; background: #ffffff; }
</style></head><body>
${stub}
<div id="app"></div>
${init}
<script>${elkJs}</script>
<script>${webviewJs}</script>
</body></html>`;
}

(async () => {
    const chrome = locateChrome();
    if (!chrome) {
        console.error('chromium not found');
        process.exit(1);
    }
    const html = await buildPreviewHtml(fixture);
    const htmlFile = path.join(outDir, 'preview.html');
    fs.writeFileSync(htmlFile, html);
    console.log('html:', htmlFile);

    const port = 9333;
    const proc = spawn(chrome, [
        '--headless=new',
        '--disable-gpu',
        '--hide-scrollbars',
        '--no-sandbox',
        '--remote-debugging-port=' + port,
        '--window-size=1200,1800',
        'file://' + htmlFile,
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    try {
        const endpoint = await new Promise((resolve, reject) => {
            const startedAt = Date.now();
            const tryFetch = () => {
                http.get({host: '127.0.0.1', port, path: '/json/version'}, res => {
                    let body = ''; res.on('data', c => body += c);
                    res.on('end', () => resolve(JSON.parse(body)));
                }).on('error', () => {
                    if (Date.now() - startedAt > 8000) return reject(new Error('chrome did not expose devtools'));
                    setTimeout(tryFetch, 150);
                });
            };
            tryFetch();
        });

        const pages = await new Promise((resolve, reject) => {
            http.get({host: '127.0.0.1', port, path: '/json'}, res => {
                let body = ''; res.on('data', c => body += c);
                res.on('end', () => resolve(JSON.parse(body)));
            }).on('error', reject);
        });
        const pageWs = pages.find(p => p.type === 'page').webSocketDebuggerUrl;
        const WebSocket = require('ws');
        const ws = new WebSocket(pageWs);
        await new Promise((resolve, reject) => { ws.once('open', resolve); ws.once('error', reject); });
        ws.off = ws.removeListener;

        let id = 0;
        await rpcSend(ws, ++id, 'Runtime.enable');
        await rpcSend(ws, ++id, 'Page.enable');

        // Wait for layout to stabilize.
        await new Promise(r => setTimeout(r, 1500));
        // Extra settle — the elk layout runs async after mount.
        await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: 'new Promise(r => setTimeout(r, 1500))',
            awaitPromise: true,
        });

        // Dump the rendered SVG.
        const svgDump = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => { const s = document.querySelector('.fcstm-stage__inner svg'); return s ? s.outerHTML : ''; })()`,
            returnByValue: true,
        });
        const svgFile = path.join(outDir, 'preview.svg');
        fs.writeFileSync(svgFile, svgDump.result.value || '<!-- no svg -->');
        console.log('svg:', svgFile);

        // Fit the SVG, then screenshot.
        await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => {
                const svg = document.querySelector('.fcstm-stage__inner svg');
                if (!svg) return;
                const w = parseFloat(svg.getAttribute('width') || '0');
                const h = parseFloat(svg.getAttribute('height') || '0');
                document.body.style.width = (w + 64) + 'px';
                document.body.style.height = (h + 64) + 'px';
            })()`,
        });
        const metrics = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => ({w: document.body.scrollWidth, h: document.body.scrollHeight}))()`,
            returnByValue: true,
        });
        await rpcSend(ws, ++id, 'Emulation.setDeviceMetricsOverride', {
            width: Math.max(1200, metrics.result.value.w),
            height: Math.max(900, metrics.result.value.h),
            deviceScaleFactor: 1,
            mobile: false,
        });
        const shot = await rpcSend(ws, ++id, 'Page.captureScreenshot', {
            format: 'png',
            captureBeyondViewport: true,
        });
        const pngFile = path.join(outDir, 'preview.png');
        fs.writeFileSync(pngFile, Buffer.from(shot.data, 'base64'));
        console.log('png:', pngFile);

        ws.close();
    } finally {
        proc.kill('SIGTERM');
    }
})();

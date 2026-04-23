#!/usr/bin/env node
// Visual verification harness for selected + hover highlight rendering.
//
// Drives the preview into four visual states and captures a PNG of each:
//   1. 01-baseline         — no selection, no hover
//   2. 02-selected         — one composite marked .fcstm-selected via JS
//                            (identical to what applySelection does)
//   3. 03-selected-hover   — same composite also hovered by a real
//                            mouseMoved event at its title area
//   4. 04-selected-child   — mouse moved into a nested leaf inside
//                            the selected composite
//
// Run:
//   node editors/vscode/scripts/verify-selection-render.js \
//     test_selfloop.fcstm /tmp/fcstm-sel [composite-id]
//
// If [composite-id] is omitted, the first composite discovered wins.

const fs = require('fs');
const os = require('os');
const path = require('path');
const http = require('http');
const {spawn, spawnSync} = require('child_process');
const Module = require('module');

const fixture = process.argv[2];
const outDir = process.argv[3];
const wantedId = process.argv[4] || null;
if (!fixture || !outDir) {
    console.error('usage: verify-selection-render.js <fixture.fcstm> <out-dir> [composite-id]');
    process.exit(2);
}
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

    // Use a dark-flavoured background so the orange halo is obvious.
    const stub = `<script>window.acquireVsCodeApi = () => ({ postMessage:()=>{}, getState:()=>null, setState:()=>{} });</script>`;
    const init = `<script>window.__FCSTM_INITIAL_STATE__ = ${JSON.stringify(state).replace(/</g, '\\u003c')};</script>`;
    return `<!DOCTYPE html>
<html><head><meta charset="UTF-8"><style>${webviewCss}
html, body, #app { margin: 0; padding: 0; height: 100%; min-height: 100%; background: #1a222e; }
body.vscode-dark { background: #1a222e; }
</style></head><body class="vscode-dark fcstm-mode-dark">
${stub}
<div id="app"></div>
${init}
<script>${elkJs}</script>
<script>${webviewJs}</script>
</body></html>`;
}

(async () => {
    const chrome = locateChrome();
    if (!chrome) { console.error('chromium not found'); process.exit(1); }
    const html = await buildPreviewHtml(fixture);
    const htmlFile = path.join(outDir, 'preview.html');
    fs.writeFileSync(htmlFile, html);
    console.log('html:', htmlFile);

    const port = 9343;
    const proc = spawn(chrome, [
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-sandbox',
        '--remote-debugging-port=' + port, '--window-size=1400,1600',
        'file://' + htmlFile,
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    try {
        await new Promise((resolve, reject) => {
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
        await rpcSend(ws, ++id, 'DOM.enable');
        await rpcSend(ws, ++id, 'CSS.enable');

        // Give ELK a second to lay out the graph async.
        await new Promise(r => setTimeout(r, 1500));
        await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: 'new Promise(r => setTimeout(r, 1500))',
            awaitPromise: true,
        });

        // Fit the viewport to the stage so our mouse-coordinate math stays honest.
        await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => {
                const svg = document.querySelector('.fcstm-stage__inner svg');
                if (!svg) return;
                const w = parseFloat(svg.getAttribute('width') || '0');
                const h = parseFloat(svg.getAttribute('height') || '0');
                document.body.style.width = (w + 200) + 'px';
                document.body.style.height = (h + 200) + 'px';
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

        async function shot(name) {
            await rpcSend(ws, ++id, 'Runtime.evaluate', {
                expression: 'new Promise(r => requestAnimationFrame(() => requestAnimationFrame(r)))',
                awaitPromise: true,
            });
            const res = await rpcSend(ws, ++id, 'Page.captureScreenshot', {
                format: 'png', captureBeyondViewport: true,
            });
            const pngFile = path.join(outDir, name + '.png');
            fs.writeFileSync(pngFile, Buffer.from(res.data, 'base64'));
            console.log('shot:', pngFile);
        }

        // 1) baseline — before any selection or hover.
        await shot('01-baseline');

        // Scan composites and note positions for later mouse-move events.
        const info = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => {
                const items = [];
                for (const el of document.querySelectorAll('[data-fcstm-kind="composite-state"][data-fcstm-id]')) {
                    const id = el.getAttribute('data-fcstm-id');
                    const rect = el.getBoundingClientRect();
                    // Since ELK lays children as DOM siblings of their composite
                    // rather than descendants, collect descendants by id prefix.
                    const children = [];
                    for (const c of document.querySelectorAll('[data-fcstm-kind="state"][data-fcstm-id]')) {
                        const cid = c.getAttribute('data-fcstm-id');
                        if (cid === id) continue;
                        if (!cid.startsWith(id + '.')) continue;
                        const r = c.getBoundingClientRect();
                        children.push({id: cid, cx: r.left + r.width / 2, cy: r.top + r.height / 2});
                    }
                    items.push({id, headerX: rect.left + 100, headerY: rect.top + 15, children});
                }
                return items;
            })()`,
            returnByValue: true,
        });
        const composites = info.result.value;
        if (!composites.length) { console.error('no composite found'); process.exit(3); }
        const pick = (wantedId && composites.find(c => c.id === wantedId)) || composites[0];
        console.log('selecting composite:', pick.id, 'children:', pick.children.map(c => c.id));

        // 2) selected — directly toggle the class, mirroring applySelection().
        await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => {
                const id = ${JSON.stringify(pick.id)};
                // Exactly what applySelection does today: tag every node with matching id.
                for (const el of document.querySelectorAll('[data-fcstm-kind][data-fcstm-id]')) {
                    if (el.getAttribute('data-fcstm-id') === id) el.classList.add('fcstm-selected');
                }
                return document.querySelectorAll('.fcstm-selected').length;
            })()`,
            returnByValue: true,
        });
        // Park the mouse somewhere harmless so :hover isn't already set.
        await rpcSend(ws, ++id, 'Input.dispatchMouseEvent', {type: 'mouseMoved', x: 5, y: 5, buttons: 0});
        await new Promise(r => setTimeout(r, 200));
        await shot('02-selected');

        // 3) selected + hover on composite — force :hover via CSS protocol.
        async function forceHover(selector) {
            // Clear any prior forced pseudo by re-querying and re-forcing.
            const root = await rpcSend(ws, ++id, 'DOM.getDocument', {});
            const node = await rpcSend(ws, ++id, 'DOM.querySelector', {
                nodeId: root.root.nodeId, selector,
            });
            if (!node || !node.nodeId) return false;
            await rpcSend(ws, ++id, 'CSS.forcePseudoState', {
                nodeId: node.nodeId, forcedPseudoClasses: ['hover'],
            });
            return node.nodeId;
        }
        async function clearHoverOn(nodeId) {
            if (!nodeId) return;
            await rpcSend(ws, ++id, 'CSS.forcePseudoState', {nodeId, forcedPseudoClasses: []});
        }
        const selfHoverId = await forceHover(`[data-fcstm-kind="composite-state"][data-fcstm-id=${JSON.stringify(pick.id)}]`);
        await new Promise(r => setTimeout(r, 150));
        await shot('03-selected-hover-self');
        await clearHoverOn(selfHoverId);

        // 4) selected + hover on a nested leaf.
        if (pick.children[0]) {
            const leaf = pick.children[0];
            const childHoverId = await forceHover(`[data-fcstm-kind="state"][data-fcstm-id=${JSON.stringify(leaf.id)}]`);
            await new Promise(r => setTimeout(r, 150));
            await shot('04-selected-hover-child');
            await clearHoverOn(childHoverId);
        }

        // Dump the SVG for later inspection.
        const svgDump = await rpcSend(ws, ++id, 'Runtime.evaluate', {
            expression: `(() => { const s = document.querySelector('.fcstm-stage__inner svg'); return s ? s.outerHTML : ''; })()`,
            returnByValue: true,
        });
        fs.writeFileSync(path.join(outDir, 'preview.svg'), svgDump.result.value || '');

        ws.close();
    } finally {
        proc.kill('SIGTERM');
    }
})().catch(err => { console.error(err); process.exit(1); });

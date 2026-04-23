#!/usr/bin/env node
// Minimal headless-Chrome snapshotter: takes a list of .html files,
// loads each one, waits for ELK to settle, and writes alongside .png.
const fs = require('fs');
const path = require('path');
const http = require('http');
const {spawn, spawnSync} = require('child_process');

const files = process.argv.slice(2);
if (!files.length) { console.error('usage: shot-html.js <a.html> [b.html ...]'); process.exit(2); }

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
    const port = 9353;
    const proc = spawn(chrome, [
        '--headless=new', '--disable-gpu', '--hide-scrollbars', '--no-sandbox',
        '--remote-debugging-port=' + port, '--window-size=1400,1600',
        'about:blank',
    ], {stdio: ['ignore', 'pipe', 'pipe']});

    try {
        await new Promise((resolve, reject) => {
            const startedAt = Date.now();
            const tryFetch = () => {
                http.get({host: '127.0.0.1', port, path: '/json/version'}, res => {
                    let body = ''; res.on('data', c => body += c);
                    res.on('end', () => resolve(JSON.parse(body)));
                }).on('error', () => {
                    if (Date.now() - startedAt > 8000) return reject(new Error('chrome timeout'));
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

        for (const htmlPath of files) {
            const abs = path.resolve(htmlPath);
            await rpcSend(ws, ++id, 'Page.navigate', {url: 'file://' + abs});
            await new Promise(r => setTimeout(r, 1400));
            await rpcSend(ws, ++id, 'Runtime.evaluate', {
                expression: 'new Promise(r => setTimeout(r, 1400))',
                awaitPromise: true,
            });
            await rpcSend(ws, ++id, 'Runtime.evaluate', {
                expression: `(() => {
                    const svg = document.querySelector('.fcstm-stage__inner svg');
                    if (!svg) return;
                    const w = parseFloat(svg.getAttribute('width') || '0');
                    const h = parseFloat(svg.getAttribute('height') || '0');
                    document.body.style.width = (w + 120) + 'px';
                    document.body.style.height = (h + 200) + 'px';
                })()`,
            });
            const metrics = await rpcSend(ws, ++id, 'Runtime.evaluate', {
                expression: `(() => ({w: document.documentElement.scrollWidth, h: document.documentElement.scrollHeight}))()`,
                returnByValue: true,
            });
            await rpcSend(ws, ++id, 'Emulation.setDeviceMetricsOverride', {
                width: Math.max(1200, metrics.result.value.w),
                // +32 buffer so the last CSS-bordered panel keeps its
                // bottom stroke in the capture.
                height: Math.max(900, metrics.result.value.h + 32),
                deviceScaleFactor: 1,
                mobile: false,
            });
            const shot = await rpcSend(ws, ++id, 'Page.captureScreenshot', {
                format: 'png', captureBeyondViewport: true,
            });
            const pngPath = abs.replace(/\.html$/, '.png');
            fs.writeFileSync(pngPath, Buffer.from(shot.data, 'base64'));
            console.log('png:', pngPath);
        }

        ws.close();
    } finally {
        proc.kill('SIGTERM');
    }
})().catch(err => { console.error(err); process.exit(1); });

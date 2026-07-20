import {createApp} from 'vue';
import ELK from 'elkjs/lib/elk.bundled.js';
import App from './App.vue';

interface StandaloneExportPayload {
    svg: string;
    pngBase64: string;
    pdfBase64: string;
}

function decodeBase64(value: string): Uint8Array {
    const raw = atob(value);
    const bytes = new Uint8Array(raw.length);
    for (let index = 0; index < raw.length; index += 1) bytes[index] = raw.charCodeAt(index);
    return bytes;
}

function download(name: string, data: BlobPart, type: string): void {
    const url = URL.createObjectURL(new Blob([data], {type}));
    const anchor = document.createElement('a');
    anchor.href = url;
    anchor.download = name;
    anchor.click();
    setTimeout(() => URL.revokeObjectURL(url), 0);
}

function showExportMenu(payload: StandaloneExportPayload): void {
    document.getElementById('fcstm-standalone-export-menu')?.remove();
    const menu = document.createElement('div');
    menu.id = 'fcstm-standalone-export-menu';
    menu.setAttribute('role', 'dialog');
    menu.setAttribute('aria-label', '选择导出格式');
    menu.style.cssText = 'position:fixed;right:18px;top:138px;z-index:1000;display:flex;gap:6px;align-items:center;padding:10px;border:1px solid #9bb9d8;border-radius:8px;background:#fff;box-shadow:0 6px 24px rgba(0,0,0,.18);font:13px sans-serif;color:#1f2937';
    const title = document.createElement('span');
    title.textContent = '下载图形：';
    menu.appendChild(title);
    const choices: Array<[string, () => void]> = [
        ['SVG', () => download('diagram.svg', payload.svg, 'image/svg+xml;charset=utf-8')],
        ['PNG', () => download('diagram.png', decodeBase64(payload.pngBase64), 'image/png')],
        ['PDF', () => download('diagram.pdf', decodeBase64(payload.pdfBase64), 'application/pdf')],
    ];
    for (const [label, action] of choices) {
        const button = document.createElement('button');
        button.type = 'button';
        button.textContent = label;
        button.style.cssText = 'border:1px solid #9bb9d8;border-radius:5px;padding:4px 9px;background:#f5f9fd;color:#1f2937;cursor:pointer';
        button.addEventListener('click', () => { action(); menu.remove(); });
        menu.appendChild(button);
    }
    const close = document.createElement('button');
    close.type = 'button';
    close.textContent = '×';
    close.setAttribute('aria-label', '关闭导出菜单');
    close.style.cssText = 'border:0;background:transparent;font-size:18px;line-height:1;cursor:pointer;color:#6b7280';
    close.addEventListener('click', () => menu.remove());
    menu.appendChild(close);
    document.body.appendChild(menu);
}

window.addEventListener('fcstm-emit', event => {
    const detail = (event as CustomEvent<{type?: string; payload?: unknown}>).detail;
    if (detail?.type === 'exportDiagram' && detail.payload && typeof detail.payload === 'object') {
        const payload = detail.payload as StandaloneExportPayload;
        (window as unknown as {__FCSTM_LAST_EXPORT__?: StandaloneExportPayload}).__FCSTM_LAST_EXPORT__ = payload;
        showExportMenu(payload);
    } else if (detail?.type === 'exportError') {
        reportFatal('导出失败', String(detail.payload || '未知导出错误'));
    }
});

// The VSCode host normally injects this constructor before the Vue bundle.
// Standalone HTML supplies the same contract from its self-contained bundle.
(window as unknown as {ELK: typeof ELK}).ELK = ELK;

function reportFatal(title: string, message: string): void {
    const app = document.getElementById('app');
    if (!app) return;
    const pre = document.createElement('pre');
    pre.style.cssText = 'margin:16px;padding:12px;border:1px solid #c44;background:#fee;white-space:pre-wrap';
    pre.textContent = `${title}\n\n${message}`;
    app.appendChild(pre);
}

window.addEventListener('error', event => {
    reportFatal('预览脚本错误', `${event.message || '未知错误'}\n${(event.error as Error | undefined)?.stack || ''}`);
});
window.addEventListener('unhandledrejection', event => {
    const reason = event.reason as Error | undefined;
    reportFatal('预览异步错误', `${reason?.message || String(event.reason)}\n${reason?.stack || ''}`);
});

createApp(App).mount('#app');

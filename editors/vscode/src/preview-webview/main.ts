/**
 * Entry point for the FCSTM preview webview.
 *
 * The extension host bundles this file as a self-contained IIFE and
 * inlines it into the webview HTML along with:
 *   - the elkjs bundle (provides global ``ELK``),
 *   - a serialised ``window.__FCSTM_INITIAL_STATE__`` for the Vue root,
 *   - an ``acquireVsCodeApi`` stub injected by VS Code.
 */
import {createApp} from 'vue';
import App from './App.vue';
import {bridge} from './composables/useBridge';

// Surface runtime errors inside the stage-empty panel so a blank preview
// is never the only signal.
window.addEventListener('error', (ev) => {
    reportFatal('Preview script error', (ev.message || 'Unknown error') + '\n' +
        (ev.error && (ev.error as Error).stack ? (ev.error as Error).stack : ''));
});
window.addEventListener('unhandledrejection', (ev) => {
    const reason = ev.reason;
    const msg = (reason && (reason as Error).message ? (reason as Error).message : String(reason)) + '\n' +
        (reason && (reason as Error).stack ? (reason as Error).stack : '');
    reportFatal('Preview promise error', msg);
});

function reportFatal(title: string, message: string) {
    try {
        const app = document.getElementById('app');
        if (!app) return;
        const pre = document.createElement('pre');
        pre.style.cssText = 'margin:16px;padding:12px;border:1px solid #c44;background:#fee;white-space:pre-wrap';
        pre.textContent = title + '\n\n' + message;
        app.appendChild(pre);
    } catch { /* best effort */ }
}

// Mark the body with modifier-held class so Stage CSS can show the
// code-tracking cursor when the user is about to Ctrl/Cmd+click.
function updateModifierClass(ev: KeyboardEvent) {
    const held = Boolean(ev.ctrlKey || ev.metaKey);
    document.body.classList.toggle('modifier-held', held);
}
window.addEventListener('keydown', updateModifierClass);
window.addEventListener('keyup', updateModifierClass);
window.addEventListener('blur', () => document.body.classList.remove('modifier-held'));

// Relay export + copy events from Stage → extension host via the bridge.
window.addEventListener('fcstm-emit', (ev: Event) => {
    const detail = (ev as CustomEvent).detail as {type: string; payload: string};
    const api = bridge();
    if (detail.type === 'exportSvg') {
        api.postMessage({type: 'exportSvg', svg: detail.payload});
    } else if (detail.type === 'exportPng') {
        api.postMessage({type: 'exportPng', base64: detail.payload});
    } else if (detail.type === 'exportError') {
        api.postMessage({type: 'exportError', message: detail.payload});
    } else if (detail.type === 'copyDone') {
        api.postMessage({type: 'copyDone', message: detail.payload});
    } else if (detail.type === 'copyError') {
        api.postMessage({type: 'copyError', message: detail.payload});
    }
});

createApp(App).mount('#app');

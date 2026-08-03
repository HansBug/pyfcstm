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
    const detail = (ev as CustomEvent).detail as {type: string; payload: unknown};
    const api = bridge();
    if (detail.type === 'exportDiagram') {
        // `failed` has to travel with the payload: the formats settle
        // independently now, so dropping it left the host offering a format it
        // never received and writing a zero-byte file with a success message.
        const p = detail.payload as {
            svg: string; pngBase64: string; pdfBase64: string; failed?: string[];
        };
        api.postMessage({
            type: 'exportDiagram',
            svg: p.svg,
            pngBase64: p.pngBase64,
            pdfBase64: p.pdfBase64,
            failed: p.failed || [],
        });
    } else if (detail.type === 'exportError') {
        api.postMessage({type: 'exportError', message: detail.payload as string});
    } else if (detail.type === 'copyDone') {
        api.postMessage({type: 'copyDone', message: detail.payload as string});
    } else if (detail.type === 'copyError') {
        api.postMessage({type: 'copyError', message: detail.payload as string});
    }
});

// Give this host the ability to outline text, by asking the extension host to
// ask an installed `pyfcstm[viz]`.
//
// `expandSvgForExport` looks for `window.__FCSTM_EXPAND_SVG__`; the standalone
// Python viewer injects one, and until now the editor webview had none, so its
// SVG download silently depended on fonts the reader might not have. The
// webview cannot do the work itself -- no fonts, no rasteriser -- and bundling
// those would add 17.7 MB for one locale or 59.4 MB for all of them.
//
// The canonical document is sent as-is rather than the host re-rendering from
// the `.fcstm` source, so the palette and colour mode on screen are the ones in
// the exported file.
const pendingExpansions = new Map<string, {
    resolve: (svg: string) => void;
    reject: (error: Error) => void;
}>();
let expansionSequence = 0;

window.addEventListener('message', (event: MessageEvent) => {
    const data = event.data as {type?: string; requestId?: string; svg?: string; error?: string};
    if (!data || data.type !== 'expandSvgResult' || typeof data.requestId !== 'string') return;
    const pending = pendingExpansions.get(data.requestId);
    if (!pending) return;
    pendingExpansions.delete(data.requestId);
    if (typeof data.svg === 'string') pending.resolve(data.svg);
    // A reply with neither an SVG nor a reason is still a reply, and rejecting
    // it is what turns it into the export's error instead of a hung download.
    else pending.reject(new Error(data.error || 'the extension host could not expand this diagram'));
});

(window as unknown as {__FCSTM_EXPAND_SVG__?: (svg: string) => Promise<string>}).__FCSTM_EXPAND_SVG__ =
    (svg: string) => new Promise<string>((resolve, reject) => {
        const requestId = `expand-${++expansionSequence}`;
        pendingExpansions.set(requestId, {resolve, reject});
        bridge().postMessage({type: 'expandSvg', requestId, svg} as never);
    });

createApp(App).mount('#app');

import {createApp} from 'vue';
import ELK from 'elkjs/lib/elk.bundled.js';
import App from './App.vue';

interface StandaloneExportPayload {
    svg: string;
    pngBase64: string;
    pdfBase64: string;
    /** Formats this export could not produce, with the reason for each. */
    failed?: string[];
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
    menu.setAttribute('aria-label', 'Choose an export format');
    menu.style.cssText = 'position:fixed;right:18px;top:138px;z-index:1000;display:flex;gap:6px;align-items:center;padding:10px;border:1px solid #9bb9d8;border-radius:8px;background:#fff;box-shadow:0 6px 24px rgba(0,0,0,.18);font:13px sans-serif;color:#1f2937';
    const title = document.createElement('span');
    title.textContent = 'Download diagram:';
    menu.appendChild(title);
    // Only formats this export actually produced are offered; a very large
    // diagram can exceed the browser's raster limits while its vector output
    // remains perfect, and a button that downloads nothing is worse than none.
    const choices: Array<[string, () => void]> = [
        ['SVG', () => download('diagram.svg', payload.svg, 'image/svg+xml;charset=utf-8')],
    ];
    if (payload.pngBase64) {
        choices.push(['PNG', () => download('diagram.png', decodeBase64(payload.pngBase64), 'image/png')]);
    }
    if (payload.pdfBase64) {
        choices.push(['PDF', () => download('diagram.pdf', decodeBase64(payload.pdfBase64), 'application/pdf')]);
    }
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
    close.setAttribute('aria-label', 'Close the export menu');
    close.style.cssText = 'border:0;background:transparent;font-size:18px;line-height:1;cursor:pointer;color:#6b7280';
    close.addEventListener('click', () => menu.remove());
    menu.appendChild(close);
    if (payload.failed && payload.failed.length > 0) {
        const note = document.createElement('div');
        note.style.cssText = 'flex-basis:100%;font-size:12px;color:#b45309';
        note.textContent = `Unavailable for this diagram — ${payload.failed.join('; ')}`;
        menu.style.flexWrap = 'wrap';
        menu.appendChild(note);
    }
    document.body.appendChild(menu);
}

window.addEventListener('fcstm-emit', event => {
    const detail = (event as CustomEvent<{type?: string; payload?: unknown}>).detail;
    if (detail?.type === 'exportDiagram' && detail.payload && typeof detail.payload === 'object') {
        const payload = detail.payload as StandaloneExportPayload;
        (window as unknown as {__FCSTM_LAST_EXPORT__?: StandaloneExportPayload}).__FCSTM_LAST_EXPORT__ = payload;
        showExportMenu(payload);
    } else if (detail?.type === 'exportError') {
        reportFatal('Export failed', String(detail.payload || 'Unknown export error'));
    }
});

// The VSCode host normally injects this constructor before the Vue bundle.
// Standalone HTML supplies the same contract from its self-contained bundle.
(window as unknown as {ELK: typeof ELK}).ELK = ELK;

/**
 * Stamp the document's style nonce onto every stylesheet created at runtime.
 *
 * The component library renders its CSS on first mount instead of shipping a
 * static stylesheet, so those elements are not covered by the build-time hash
 * in `style-src`. Without the nonce the policy rejects them and the controls
 * render unstyled — transparent popups, no shadow, no width constraint.
 *
 * The nonce is public, not secret: it appears in the policy, in the bootstrap
 * script, and on `window`, and it is a pure function of the document's own
 * bytes. Hash-pinning the bootstrap prevents tampering, not reading. So the
 * accepted trade-off is that `style-src` no longer makes an external
 * stylesheet load structurally impossible the way a hash-only list did — a
 * nonce matches `<link rel=stylesheet>` from any origin. That is only
 * reachable through a markup-injection primitive, and the two sinks that
 * reach this document escape everything: the highlighted source is escaped
 * per fragment before it becomes a text node, and the rendered SVG routes
 * every model string through the renderer's XML escaping. Keep both
 * invariants when touching either path; the durable fix is to precompute the
 * runtime stylesheets at build time so the nonce can be dropped entirely.
 */
function adoptStyleNonce(): void {
    const nonce = (window as unknown as {__FCSTM_STYLE_NONCE__?: string}).__FCSTM_STYLE_NONCE__;
    if (!nonce) return;
    const createElement = document.createElement.bind(document);
    document.createElement = ((tagName: string, options?: ElementCreationOptions) => {
        const element = createElement(tagName, options);
        if (String(tagName).toLowerCase() === 'style') {
            element.setAttribute('nonce', nonce);
            (element as HTMLStyleElement).nonce = nonce;
        }
        return element;
    }) as typeof document.createElement;
}

adoptStyleNonce();

function reportFatal(title: string, message: string): void {
    const app = document.getElementById('app');
    if (!app) return;
    const pre = document.createElement('pre');
    pre.dataset.fcstmFatal = 'true';
    pre.style.cssText = 'margin:16px;padding:12px;border:1px solid #c44;background:#fee;white-space:pre-wrap';
    pre.textContent = `${title}\n\n${message}`;
    app.appendChild(pre);
}

window.addEventListener('error', event => {
    reportFatal('Preview script error', `${event.message || 'Unknown error'}\n${(event.error as Error | undefined)?.stack || ''}`);
});
window.addEventListener('unhandledrejection', event => {
    const reason = event.reason as Error | undefined;
    reportFatal('Preview async error', `${reason?.message || String(event.reason)}\n${reason?.stack || ''}`);
});

/**
 * Decode the embedded font faces before the first paint.
 *
 * Layout and every raster/vector export depend on the bundled metrics, so the
 * viewer waits for them. Returns the faces that never became available plus
 * any rejection reason; the caller degrades instead of leaving a blank page,
 * because fonts are an appearance resource and the diagram itself is still
 * usable without them.
 */
async function loadEmbeddedFonts(): Promise<{missing: string[]; reasons: string[]}> {
    // Settles immediately here (no face is pending yet); kept because the
    // explicit per-face load below is what actually waits.
    await document.fonts.ready;
    const locale = ((window as unknown as {
        __FCSTM_INITIAL_STATE__?: {previewOptions?: {cjkLocale?: string}};
    }).__FCSTM_INITIAL_STATE__?.previewOptions?.cjkLocale || 'sc').toLowerCase();
    const cjkFamily = ({sc: 'Noto Sans SC', tc: 'Noto Sans TC', hk: 'Noto Sans HK', jp: 'Noto Sans JP', kr: 'Noto Sans KR'} as Record<string, string>)[locale] || 'Noto Sans SC';
    const requiredFaces: Array<[string, number]> = [
        ['JetBrains Mono', 400],
        ['JetBrains Mono', 500],
        ['JetBrains Mono', 700],
        [cjkFamily, 400],
        [cjkFamily, 700],
    ];
    const probes = requiredFaces.map(([family, weight]) => {
        const probe = document.createElement('span');
        probe.textContent = family.startsWith('Noto Sans') ? '中日한' : 'ABC123';
        probe.style.cssText = 'position:fixed;left:-10000px;top:-10000px;visibility:hidden;white-space:nowrap';
        probe.style.fontFamily = `"${family}"`;
        probe.style.fontWeight = String(weight);
        document.body.appendChild(probe);
        return probe;
    });
    // allSettled instead of a catch: `DOMException` and every other decode
    // failure derive from `Error`, so an `instanceof Error` guard would swallow
    // unrelated bugs and relabel them as a missing font. Collecting the
    // rejection reasons keeps the real cause visible in the report.
    const attempts = await Promise.allSettled([
        ...[...document.fonts].map(face => face.load()),
        ...requiredFaces.map(([family, weight]) => document.fonts.load(
            `${weight} 12px "${family}"`,
            family.startsWith('Noto Sans') ? '中日한' : 'ABC123',
        )),
    ]);
    probes.forEach(probe => probe.remove());
    return {
        missing: requiredFaces
            .filter(([family, weight]) => !document.fonts.check(
                `${weight} 12px "${family}"`,
                family.startsWith('Noto Sans') ? '中日한' : 'ABC123',
            ))
            .map(([family, weight]) => `${family}/${weight}`),
        reasons: attempts
            .filter((item): item is PromiseRejectedResult => item.status === 'rejected')
            .map(item => String(item.reason)),
    };
}

async function mountStandalone(): Promise<void> {
    if (document.readyState === 'loading') {
        await new Promise<void>(resolve => document.addEventListener('DOMContentLoaded', () => resolve(), {once: true}));
    }
    const fonts = document.fonts ? await loadEmbeddedFonts() : {missing: [], reasons: []};
    createApp(App).mount('#app');
    if (fonts.missing.length > 0 || fonts.reasons.length > 0) {
        const details = [`Unavailable: ${fonts.missing.join(', ') || 'none'}`];
        if (fonts.reasons.length > 0) details.push(`Reasons: ${fonts.reasons.join('; ')}`);
        reportFatal('Embedded fonts unavailable', `The diagram and source may fall back to substitute fonts.\n${details.join('\n')}`);
    }
}

void mountStandalone();

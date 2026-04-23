import type {WebviewInboundMessage, PreviewWebviewState} from '../types';

export interface VsCodeApi {
    postMessage(message: WebviewInboundMessage): void;
    getState(): PreviewWebviewState | null;
    setState(state: PreviewWebviewState): void;
}

declare global {
    interface Window {
        acquireVsCodeApi: () => VsCodeApi;
    }
}

let cached: VsCodeApi | null = null;

export function bridge(): VsCodeApi {
    if (cached) return cached;
    if (typeof window !== 'undefined' && typeof window.acquireVsCodeApi === 'function') {
        cached = window.acquireVsCodeApi();
        return cached;
    }
    // Fallback so the bundle is loadable outside a real webview host.
    cached = {
        postMessage() { /* noop */ },
        getState() { return null; },
        setState() { /* noop */ },
    };
    return cached;
}

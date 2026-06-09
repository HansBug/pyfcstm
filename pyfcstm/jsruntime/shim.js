/**
 * Host-environment shim for the pyfcstm JS bundle.
 *
 * mini-racer provides a bare V8 sandbox: no `window`, no `global`, no
 * `setTimeout`, no `atob`/`btoa`, no `TextEncoder`/`TextDecoder`. The
 * jsfcstm bundle (and the elkjs / resvg-wasm code paths it pulls in)
 * silently expects a few of these. This file is loaded into the JS
 * context BEFORE `bundle.js`.
 *
 * Compatibility notes (covered in detail in issue #89):
 *
 *   - `globalThis.window` and `globalThis.global` MUST be aliased so
 *     the GWT-compiled elkjs runtime can pick a `$wnd`. We must NOT
 *     alias `globalThis.self`, otherwise `elk-worker.min.js` decides
 *     it is running inside a Web Worker and installs a `self.onmessage`
 *     handler instead of exporting its `Worker` class.
 *
 *   - `setTimeout` is invoked by elkjs's PromisedWorker shim with a
 *     0ms delay to break the call stack. Running synchronously is
 *     fine — V8 drains the microtask queue at end-of-script anyway.
 */

globalThis.global = globalThis;
globalThis.window = globalThis;

globalThis.setTimeout = function (fn) {
    try { fn(); } catch (e) { /* swallow — host has no event loop */ }
    return 0;
};
globalThis.clearTimeout = function () { /* noop */ };

globalThis.console = globalThis.console || {
    log: function () {}, warn: function () {}, error: function () {},
};

if (typeof globalThis.atob === 'undefined') {
    globalThis.atob = function (s) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        s = String(s).replace(/=+$/, '');
        let out = '';
        for (let bc = 0, bs, buffer, i = 0;
             (buffer = s.charAt(i++));
             ~buffer && (bs = bc % 4 ? bs * 64 + buffer : buffer, bc++ % 4)
                ? (out += String.fromCharCode(255 & bs >> (-2 * bc & 6)))
                : 0) {
            buffer = chars.indexOf(buffer);
        }
        return out;
    };
}

if (typeof globalThis.btoa === 'undefined') {
    globalThis.btoa = function (s) {
        const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
        let out = '';
        let i = 0;
        while (i < s.length) {
            const a = s.charCodeAt(i++);
            const b = i < s.length ? s.charCodeAt(i++) : NaN;
            const c = i < s.length ? s.charCodeAt(i++) : NaN;
            out += chars[a >> 2]
                + chars[((a & 3) << 4) | (isNaN(b) ? 0 : (b >> 4))]
                + (isNaN(b) ? '=' : chars[((b & 15) << 2) | (isNaN(c) ? 0 : (c >> 6))])
                + (isNaN(c) ? '=' : chars[c & 63]);
        }
        return out;
    };
}

if (typeof globalThis.TextEncoder === 'undefined') {
    globalThis.TextEncoder = function TextEncoder() {};
    globalThis.TextEncoder.prototype.encode = function (str) {
        str = String(str || '');
        const bytes = [];
        for (let i = 0; i < str.length; i++) {
            let c = str.charCodeAt(i);
            if (c < 0x80) {
                bytes.push(c);
            } else if (c < 0x800) {
                bytes.push(0xc0 | (c >> 6), 0x80 | (c & 0x3f));
            } else if (c < 0xd800 || c >= 0xe000) {
                bytes.push(0xe0 | (c >> 12),
                           0x80 | ((c >> 6) & 0x3f),
                           0x80 | (c & 0x3f));
            } else {
                i++;
                c = 0x10000 + (((c & 0x3ff) << 10) | (str.charCodeAt(i) & 0x3ff));
                bytes.push(0xf0 | (c >> 18),
                           0x80 | ((c >> 12) & 0x3f),
                           0x80 | ((c >> 6) & 0x3f),
                           0x80 | (c & 0x3f));
            }
        }
        return new Uint8Array(bytes);
    };
    globalThis.TextEncoder.prototype.encodeInto = function (str, view) {
        const enc = this.encode(str);
        view.set(enc.subarray(0, view.length));
        return {
            read: str.length,
            written: Math.min(enc.length, view.length),
        };
    };
}

if (typeof globalThis.TextDecoder === 'undefined') {
    globalThis.TextDecoder = function TextDecoder() {};
    globalThis.TextDecoder.prototype.decode = function (buf) {
        if (!buf) return '';
        const u = buf instanceof Uint8Array
            ? buf
            : new Uint8Array(buf.buffer || buf);
        let out = '';
        let i = 0;
        while (i < u.length) {
            const b = u[i++];
            if (b < 0x80) {
                out += String.fromCharCode(b);
            } else if ((b & 0xe0) === 0xc0) {
                out += String.fromCharCode(((b & 0x1f) << 6) | (u[i++] & 0x3f));
            } else if ((b & 0xf0) === 0xe0) {
                out += String.fromCharCode(
                    ((b & 0x0f) << 12)
                    | ((u[i++] & 0x3f) << 6)
                    | (u[i++] & 0x3f)
                );
            } else {
                const cp = ((b & 0x07) << 18)
                    | ((u[i++] & 0x3f) << 12)
                    | ((u[i++] & 0x3f) << 6)
                    | (u[i++] & 0x3f);
                const x = cp - 0x10000;
                out += String.fromCharCode(0xd800 + (x >> 10),
                                            0xdc00 + (x & 0x3ff));
            }
        }
        return out;
    };
}

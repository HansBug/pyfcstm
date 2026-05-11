// ELK.js (GWT-compiled) initializes ``$wnd`` via:
//
//   var $wnd;
//   if (typeof window !== 'undefined')      $wnd = window;
//   else if (typeof global !== 'undefined') $wnd = global;  // nodejs
//   else if (typeof self !== 'undefined')   $wnd = self;    // web worker
//
// Inside mini-racer's bare V8 isolate none of those three names exist,
// so ELK ends up with ``$wnd === undefined`` and later throws when it
// touches ``$wnd.Error.stackTraceLimit``. Expose ``global`` as
// ``globalThis`` so ELK picks the nodejs branch and does NOT attempt
// to spawn a Web Worker (which mini-racer does not provide).
if (typeof globalThis.global === "undefined") {
  globalThis.global = globalThis;
}

// mini-racer's built-in setTimeout is implemented on top of
// ``Atomics.waitAsync(view, 0, 0, delay).value.then(...)``, which throws
// when ``Atomics.waitAsync`` returns the synchronous form (delay = 0).
// ELK's FakeWorker uses ``setTimeout(fn, 0)`` to schedule async layout
// messages, so we override setTimeout with a Promise-microtask backed
// implementation that is safe across all delay values.
(function () {
  var hasNativeIssue = false;
  try {
    var r = Atomics.waitAsync(new Int32Array(new SharedArrayBuffer(4)), 0, 0, 0);
    if (!r || typeof r.value !== "object" || typeof r.value.then !== "function") {
      hasNativeIssue = true;
    }
  } catch (_err) {
    hasNativeIssue = true;
  }
  if (hasNativeIssue) {
    var origSetTimeout = globalThis.setTimeout;
    globalThis.setTimeout = function (fn, delay) {
      // Same-tick scheduling is sufficient inside the mini-racer isolate:
      // there is no real wall clock to wait against, and ELK only needs
      // setTimeout(fn, 0) to break the dispatch loop into microtasks.
      Promise.resolve().then(function () {
        try {
          fn();
        } catch (_e) {
          /* match browser/node behavior: uncaught timer errors do not
             propagate synchronously */
        }
      });
      return 0;
    };
    globalThis.clearTimeout = function () {};
  }
})();

// Minimal TextEncoder / TextDecoder polyfills for the bare V8 isolate that
// hosts this bundle (mini-racer does not ship the WHATWG Encoding API).
//
// Only utf-8 is implemented because the only consumer (resvg-wasm /
// wasm-bindgen glue) hard-codes "utf-8". Decoding is greedy: malformed
// sequences are rendered as the unicode replacement character. Encoding
// follows RFC 3629 and emits 1- to 4-byte sequences.

if (typeof globalThis.TextEncoder === "undefined") {
  globalThis.TextEncoder = class TextEncoder {
    constructor() {
      this.encoding = "utf-8";
    }
    encode(text) {
      const str = text === undefined ? "" : String(text);
      const out = [];
      for (let i = 0; i < str.length; i++) {
        let code = str.charCodeAt(i);
        if (code < 0x80) {
          out.push(code);
          continue;
        }
        if (code < 0x800) {
          out.push(0xc0 | (code >> 6));
          out.push(0x80 | (code & 0x3f));
          continue;
        }
        if (code >= 0xd800 && code <= 0xdbff && i + 1 < str.length) {
          const low = str.charCodeAt(i + 1);
          if (low >= 0xdc00 && low <= 0xdfff) {
            const cp = 0x10000 + ((code - 0xd800) << 10) + (low - 0xdc00);
            out.push(0xf0 | (cp >> 18));
            out.push(0x80 | ((cp >> 12) & 0x3f));
            out.push(0x80 | ((cp >> 6) & 0x3f));
            out.push(0x80 | (cp & 0x3f));
            i++;
            continue;
          }
        }
        out.push(0xe0 | (code >> 12));
        out.push(0x80 | ((code >> 6) & 0x3f));
        out.push(0x80 | (code & 0x3f));
      }
      return new Uint8Array(out);
    }
    encodeInto(text, dest) {
      const buf = this.encode(text);
      const written = Math.min(buf.length, dest.length);
      dest.set(buf.subarray(0, written));
      return { read: text.length, written: written };
    }
  };
}

if (typeof globalThis.TextDecoder === "undefined") {
  globalThis.TextDecoder = class TextDecoder {
    constructor(label, options) {
      this.encoding = "utf-8";
      this.fatal = !!(options && options.fatal);
      this.ignoreBOM = !!(options && options.ignoreBOM);
    }
    decode(input) {
      if (input === undefined) return "";
      const view =
        input instanceof Uint8Array
          ? input
          : new Uint8Array(input.buffer ? input.buffer : input);
      let out = "";
      let i = 0;
      while (i < view.length) {
        const b0 = view[i++];
        if (b0 < 0x80) {
          out += String.fromCharCode(b0);
          continue;
        }
        if ((b0 & 0xe0) === 0xc0) {
          const b1 = view[i++] & 0x3f;
          out += String.fromCharCode(((b0 & 0x1f) << 6) | b1);
          continue;
        }
        if ((b0 & 0xf0) === 0xe0) {
          const b1 = view[i++] & 0x3f;
          const b2 = view[i++] & 0x3f;
          out += String.fromCharCode(((b0 & 0x0f) << 12) | (b1 << 6) | b2);
          continue;
        }
        if ((b0 & 0xf8) === 0xf0) {
          const b1 = view[i++] & 0x3f;
          const b2 = view[i++] & 0x3f;
          const b3 = view[i++] & 0x3f;
          let cp = ((b0 & 0x07) << 18) | (b1 << 12) | (b2 << 6) | b3;
          cp -= 0x10000;
          out += String.fromCharCode(0xd800 + (cp >> 10));
          out += String.fromCharCode(0xdc00 + (cp & 0x3ff));
          continue;
        }
        if (this.fatal) {
          throw new TypeError("malformed utf-8 sequence");
        }
        out += "�";
      }
      return out;
    }
  };
}

if (typeof globalThis.FinalizationRegistry === "undefined") {
  // The wasm-bindgen glue tolerates this being a no-op (it's only used to
  // free heap pointers when the GC sweeps; we leak instead, which is fine
  // for the bounded lifetime of a single render call inside a long-running
  // V8 isolate).
  globalThis.FinalizationRegistry = class FinalizationRegistry {
    constructor() {}
    register() {}
    unregister() {}
  };
}

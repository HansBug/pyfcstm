// pyfcstm sysdesim sequence-diagram renderer.
//
// Entry point that exposes the IIFE global ``PyfcstmSysdesim``. The Python
// side (mini-racer) loads this bundle once, then calls ``PyfcstmSysdesim.render``
// per diagram. The renderer is self-contained: it does not require ELK.js or
// any DOM API and produces an SVG string directly.
//
// PNG output is provided through ``PyfcstmSysdesim.renderPng``; it relies on
// the resvg-wasm renderer bundled into this artifact. Because mini-racer's
// V8 isolate cannot ``await`` top-level promises, callers drive PNG init in
// three steps:
//
//   1. ``PyfcstmSysdesim.startPngInit()`` kicks off WASM instantiation.
//   2. Subsequent eval calls let V8 drain microtasks, which advances the
//      promise chain.
//   3. ``PyfcstmSysdesim.isPngReady()`` reports completion (or rethrows the
//      init error). Callers spin on it before invoking ``renderPng``.

import "./polyfills.js";
import { renderSequenceSvg, RENDERER_VERSION } from "./sequence_svg.js";
import { Resvg, initWasm } from "@resvg/resvg-wasm";
// esbuild's ``binary`` loader inlines the wasm bytes as a Uint8Array literal.
import resvgWasmBytes from "@resvg/resvg-wasm/index_bg.wasm";
// Default fallback font for Latin / European glyphs. The renderer's V8
// isolate has no access to system fonts; without a buffer here, ``resvg``
// silently drops every ``<text>`` glyph in the rasterized output. CJK glyphs
// still need a user-supplied font (passed through ``options.fontBuffersB64``).
import dejavuSansBytes from "./fonts/DejaVuSans.ttf";

let _pngInitState = "idle"; // idle | pending | ready | error
let _pngInitError = null;

export function render(timelineJson, options) {
  return renderSequenceSvg(timelineJson, options || {});
}

export function version() {
  return RENDERER_VERSION;
}

export function startPngInit() {
  if (_pngInitState === "ready" || _pngInitState === "pending") {
    return _pngInitState;
  }
  _pngInitState = "pending";
  // initWasm returns a Promise. mini-racer drains microtasks between eval
  // calls, so callers spin on isPngReady() until this resolves.
  initWasm(resvgWasmBytes).then(
    () => {
      _pngInitState = "ready";
    },
    (err) => {
      _pngInitState = "error";
      _pngInitError = err;
    }
  );
  return _pngInitState;
}

export function isPngReady() {
  if (_pngInitState === "error") {
    throw new Error(
      "resvg-wasm init failed: " +
        (_pngInitError && _pngInitError.message
          ? _pngInitError.message
          : String(_pngInitError))
    );
  }
  return _pngInitState === "ready";
}

export function pngInitState() {
  return _pngInitState;
}

const BASE64_ALPHABET =
  "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";

function uint8ToBase64(bytes) {
  // mini-racer's V8 isolate does not expose ``btoa`` so encode by hand.
  // Process 3 bytes -> 4 base64 chars per iteration with explicit padding
  // for the trailing 1- or 2-byte tail.
  let out = "";
  const len = bytes.length;
  let i = 0;
  while (i + 3 <= len) {
    const b0 = bytes[i++];
    const b1 = bytes[i++];
    const b2 = bytes[i++];
    out += BASE64_ALPHABET[b0 >> 2];
    out += BASE64_ALPHABET[((b0 & 0x03) << 4) | (b1 >> 4)];
    out += BASE64_ALPHABET[((b1 & 0x0f) << 2) | (b2 >> 6)];
    out += BASE64_ALPHABET[b2 & 0x3f];
  }
  if (i < len) {
    const b0 = bytes[i];
    const b1 = i + 1 < len ? bytes[i + 1] : 0;
    out += BASE64_ALPHABET[b0 >> 2];
    out += BASE64_ALPHABET[((b0 & 0x03) << 4) | (b1 >> 4)];
    if (i + 1 < len) {
      out += BASE64_ALPHABET[(b1 & 0x0f) << 2];
      out += "=";
    } else {
      out += "==";
    }
  }
  return out;
}

function base64ToUint8(text) {
  // mini-racer's V8 isolate does not expose ``atob`` so decode by hand.
  const lookup = new Uint8Array(256);
  for (let i = 0; i < BASE64_ALPHABET.length; i++) {
    lookup[BASE64_ALPHABET.charCodeAt(i)] = i;
  }
  const padding = text.endsWith("==") ? 2 : text.endsWith("=") ? 1 : 0;
  const len = (text.length / 4) * 3 - padding;
  const out = new Uint8Array(len);
  let outPtr = 0;
  for (let i = 0; i < text.length; i += 4) {
    const a = lookup[text.charCodeAt(i)];
    const b = lookup[text.charCodeAt(i + 1)];
    const c = lookup[text.charCodeAt(i + 2)];
    const d = lookup[text.charCodeAt(i + 3)];
    out[outPtr++] = (a << 2) | (b >> 4);
    if (outPtr < len) out[outPtr++] = ((b & 0x0f) << 4) | (c >> 2);
    if (outPtr < len) out[outPtr++] = ((c & 0x03) << 6) | d;
  }
  return out;
}

export function renderPng(timelineJson, options) {
  if (_pngInitState !== "ready") {
    throw new Error(
      "PNG renderer not initialized. Call startPngInit() and spin on " +
        "isPngReady() before invoking renderPng()."
    );
  }
  const svgText = renderSequenceSvg(timelineJson, options || {});
  // Compose font buffers: the bundled fallback first, then any user-supplied
  // overrides (so ``resvg`` picks the user font for glyphs they cover and
  // falls back to DejaVu for the rest). All buffers are passed by reference;
  // resvg-wasm will copy them across the wasm boundary as needed.
  const fontBuffers = [dejavuSansBytes];
  if (options && Array.isArray(options.fontBuffersB64)) {
    for (const b64 of options.fontBuffersB64) {
      try {
        fontBuffers.push(base64ToUint8(b64));
      } catch (err) {
        // Surface decode errors with a helpful prefix instead of a cryptic
        // base64 trace from resvg-wasm.
        throw new Error("invalid base64 font buffer: " + (err && err.message));
      }
    }
  }
  const resvgOptions = Object.assign({}, (options && options.resvg) || {});
  // Splice in the font buffers under resvg's CustomFontsOptions key. The
  // wrapper class sees ``font.fontBuffers`` and forwards the buffers as a
  // separate argument.
  resvgOptions.font = Object.assign(
    {},
    resvgOptions.font || {},
    { fontBuffers: fontBuffers }
  );
  const resvg = new Resvg(svgText, resvgOptions);
  const rendered = resvg.render();
  const pngBytes = rendered.asPng();
  rendered.free();
  resvg.free();
  return uint8ToBase64(pngBytes);
}

// pyfcstm topology verification renderer.
//
// Entry point that exposes the IIFE global ``PyfcstmTopology``. Driven by
// mini-racer from the Python side. Mirrors sysdesim_render's async-handoff
// pattern because ELK.js layout and resvg-wasm initialization both return
// Promises that mini-racer cannot directly ``await``.
//
// Render lifecycle:
//
//   1. ``PyfcstmTopology.startRender(payloadJson, optionsJson)`` kicks off
//      the ELK layout. Returns the initial state ('pending').
//   2. Python eval calls drain microtasks, advancing the Promise chain.
//   3. ``PyfcstmTopology.renderState()`` reports 'pending'/'ready'/'error'.
//   4. ``PyfcstmTopology.renderResult()`` returns the SVG string (or throws
//      if the renderer raised).
//
// PNG lifecycle:
//
//   1. ``PyfcstmTopology.startPngInit()`` instantiates resvg-wasm.
//   2. Spin on ``PyfcstmTopology.pngInitState()`` until 'ready'.
//   3. ``PyfcstmTopology.renderPng(payload, options)`` (sync) returns
//      base64-encoded PNG bytes.

import "./polyfills.js";
import { renderTopologySvg, RENDERER_VERSION } from "./topology_svg.js";
import { Resvg, initWasm } from "@resvg/resvg-wasm";
// esbuild's ``binary`` loader inlines the wasm bytes as a Uint8Array literal.
import resvgWasmBytes from "@resvg/resvg-wasm/index_bg.wasm";
import dejavuSansBytes from "./fonts/DejaVuSans.ttf";

let _pngInitState = "idle";
let _pngInitError = null;

let _renderState = "idle"; // idle | pending | ready | error
let _renderResult = null;
let _renderError = null;

export function version() {
  return RENDERER_VERSION;
}

export function startRender(payloadJson, optionsJson) {
  _renderState = "pending";
  _renderResult = null;
  _renderError = null;
  let payload;
  let options;
  try {
    payload = typeof payloadJson === "string" ? JSON.parse(payloadJson) : payloadJson;
    options = optionsJson ? (typeof optionsJson === "string" ? JSON.parse(optionsJson) : optionsJson) : {};
  } catch (err) {
    _renderState = "error";
    _renderError = err;
    return _renderState;
  }
  renderTopologySvg(payload, options).then(
    (svg) => {
      _renderResult = svg;
      _renderState = "ready";
    },
    (err) => {
      _renderError = err;
      _renderState = "error";
    }
  );
  return _renderState;
}

export function renderState() {
  return _renderState;
}

export function renderResult() {
  if (_renderState === "error") {
    throw new Error(
      "Topology render failed: " +
        (_renderError && _renderError.message ? _renderError.message : String(_renderError))
    );
  }
  if (_renderState !== "ready") {
    throw new Error("Topology render not finished; state=" + _renderState);
  }
  const result = _renderResult;
  // Reset so the next call starts fresh.
  _renderState = "idle";
  _renderResult = null;
  return result;
}

export function startPngInit() {
  if (_pngInitState === "ready" || _pngInitState === "pending") {
    return _pngInitState;
  }
  _pngInitState = "pending";
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
        (_pngInitError && _pngInitError.message ? _pngInitError.message : String(_pngInitError))
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

export function renderPng(svgText, options) {
  if (_pngInitState !== "ready") {
    throw new Error(
      "PNG renderer not initialized. Call startPngInit() and spin on pngInitState() before invoking renderPng()."
    );
  }
  options = options || {};
  const fontBuffers = [dejavuSansBytes];
  if (Array.isArray(options.fontBuffersB64)) {
    for (const b64 of options.fontBuffersB64) {
      try {
        fontBuffers.push(base64ToUint8(b64));
      } catch (err) {
        throw new Error("invalid base64 font buffer: " + (err && err.message));
      }
    }
  }
  const resvgOptions = Object.assign({}, options.resvg || {});
  resvgOptions.font = Object.assign({}, resvgOptions.font || {}, { fontBuffers: fontBuffers });
  const resvg = new Resvg(svgText, resvgOptions);
  const rendered = resvg.render();
  const pngBytes = rendered.asPng();
  rendered.free();
  resvg.free();
  return uint8ToBase64(pngBytes);
}

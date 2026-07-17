/* global resvg037 */

// This file is appended to the pinned resvg binding by the asset builder.
// It exposes only byte-oriented operations needed by the Python host; no DOM,
// file, network, eval, or dynamic-function capability is added.
(() => {
  const root = globalThis;
  let fontBuffers = [];

  function decodeBase64(value) {
    const raw = atob(String(value || ""));
    const bytes = new Uint8Array(raw.length);
    for (let index = 0; index < raw.length; index += 1) {
      bytes[index] = raw.charCodeAt(index);
    }
    return bytes;
  }

  function encodeBase64(bytes) {
    const chars =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    let result = "";
    for (let index = 0; index < bytes.length; index += 3) {
      const first = bytes[index];
      const second = index + 1 < bytes.length ? bytes[index + 1] : 0;
      const third = index + 2 < bytes.length ? bytes[index + 2] : 0;
      result += chars[first >> 2];
      result += chars[((first & 3) << 4) | (second >> 4)];
      result +=
        index + 1 < bytes.length
          ? chars[((second & 15) << 2) | (third >> 6)]
          : "=";
      result += index + 2 < bytes.length ? chars[third & 63] : "=";
    }
    return result;
  }

  function options(scale) {
    return {
      fitTo: { mode: "zoom", value: Number(scale) > 0 ? Number(scale) : 1 },
      background: "#ffffff",
      font: {
        fontBuffers,
        loadSystemFonts: false,
        defaultFontFamily: "JetBrains Mono",
        monospaceFamily: "JetBrains Mono",
      },
      shapeRendering: 2,
      textRendering: 2,
    };
  }

  root.__pyfcstm_resvg_init = function (wasmBase64) {
    root.__pyfcstm_resvg_status = "pending";
    root.__pyfcstm_resvg_error = null;
    WebAssembly.compile(decodeBase64(wasmBase64))
      .then((module) => resvg037.initWasm(module))
      .then(
        () => {
          root.__pyfcstm_resvg_status = "ok";
        },
        (error) => {
          root.__pyfcstm_resvg_status = "error";
          root.__pyfcstm_resvg_error = String((error && error.stack) || error);
        },
      );
  };

  root.__pyfcstm_resvg_register_font = function (fontBase64) {
    fontBuffers = [decodeBase64(fontBase64)];
    return true;
  };

  root.__pyfcstm_resvg_png = function (svg, scale) {
    const image = new resvg037.Resvg(String(svg), options(scale)).render();
    return encodeBase64(image.asPng());
  };

  root.__pyfcstm_resvg_expand = function (svg) {
    return new resvg037.Resvg(String(svg), options(1)).toString();
  };
})();

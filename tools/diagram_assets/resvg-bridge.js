/* global resvg */

// This file is appended to the pinned resvg binding by the asset builder.
// It exposes only byte-oriented operations needed by the Python host; no DOM,
// file, network, eval, or dynamic-function capability is added.
(() => {
  const root = globalThis;
  let fontBuffers = [];
  let cjkFamily = "Noto Sans SC";
  let contextToken = "";

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
        defaultFontFamily: cjkFamily,
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
      .then((module) => resvg.initWasm(module))
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

  root.__pyfcstm_resvg_register_fonts = function (fontBase64List, family) {
    if (!Array.isArray(fontBase64List) || fontBase64List.length === 0) {
      throw new Error("at least one embedded font is required");
    }
    fontBuffers = fontBase64List.map((fontBase64) => decodeBase64(fontBase64));
    cjkFamily = String(family || cjkFamily);
    return fontBuffers.length;
  };

  root.__pyfcstm_resvg_register_font = function (fontBase64) {
    fontBuffers.push(decodeBase64(fontBase64));
    return fontBuffers.length;
  };

  root.__pyfcstm_bind_context_token = function (token) {
    contextToken = String(token || "");
    return contextToken;
  };

  root.__pyfcstm_resvg_metrics = function () {
    return JSON.stringify({
      activeContext: contextToken ? 1 : 0,
      contextToken,
      registeredFonts: fontBuffers.length,
    });
  };

  root.__pyfcstm_resvg_png = function (svg, scale) {
    const renderer = new resvg.Resvg(String(svg), options(scale));
    try {
      const image = renderer.render();
      try {
        return encodeBase64(image.asPng());
      } finally {
        image.free();
      }
    } finally {
      renderer.free();
    }
  };

  root.__pyfcstm_resvg_expand = function (svg) {
    const renderer = new resvg.Resvg(String(svg), options(1));
    try {
      return renderer.toString();
    } finally {
      renderer.free();
    }
  };
})();

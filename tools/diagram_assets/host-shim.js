// Minimal deterministic host for the embedded ES2017 bundle.
//
// The shim intentionally does not expose ``self``, filesystem APIs, network
// APIs, eval, or Function. The renderer entry installs its Promise timer only
// after the explicit ``__pyfcstm_embedded_host`` marker is set by Python.
globalThis.global = globalThis;
globalThis.window = globalThis;
globalThis.console = globalThis.console || {
  log: function () {},
  warn: function () {},
  error: function () {},
};

if (typeof globalThis.atob === "undefined") {
  globalThis.atob = function (value) {
    const chars =
      "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
    const input = String(value).replace(/=+$/, "");
    let output = "";
    for (let index = 0; index < input.length; index += 4) {
      const a = chars.indexOf(input.charAt(index));
      const b = chars.indexOf(input.charAt(index + 1));
      const c =
        index + 2 < input.length ? chars.indexOf(input.charAt(index + 2)) : -1;
      const d =
        index + 3 < input.length ? chars.indexOf(input.charAt(index + 3)) : -1;
      output += String.fromCharCode((a << 2) | (b >> 4));
      if (c >= 0) output += String.fromCharCode(((b & 15) << 4) | (c >> 2));
      if (d >= 0) output += String.fromCharCode(((c & 3) << 6) | d);
    }
    return output;
  };
}

if (typeof globalThis.TextEncoder === "undefined") {
  globalThis.TextEncoder = function TextEncoder() {};
  globalThis.TextEncoder.prototype.encode = function (value) {
    const text = String(value || "");
    const bytes = [];
    for (let index = 0; index < text.length; index += 1) {
      let code = text.charCodeAt(index);
      if (code < 128) {
        bytes.push(code);
      } else if (code < 2048) {
        bytes.push(192 | (code >> 6), 128 | (code & 63));
      } else if (code < 55296 || code >= 57344) {
        bytes.push(
          224 | (code >> 12),
          128 | ((code >> 6) & 63),
          128 | (code & 63),
        );
      } else {
        index += 1;
        code =
          65536 + (((code & 1023) << 10) | (text.charCodeAt(index) & 1023));
        bytes.push(
          240 | (code >> 18),
          128 | ((code >> 12) & 63),
          128 | ((code >> 6) & 63),
          128 | (code & 63),
        );
      }
    }
    return new Uint8Array(bytes);
  };
}

if (typeof globalThis.TextDecoder === "undefined") {
  globalThis.TextDecoder = function TextDecoder() {};
  globalThis.TextDecoder.prototype.decode = function (buffer) {
    if (!buffer) return "";
    const bytes =
      buffer instanceof Uint8Array
        ? buffer
        : new Uint8Array(buffer.buffer || buffer);
    let output = "";
    for (let index = 0; index < bytes.length; ) {
      const first = bytes[index++];
      if (first < 128) {
        output += String.fromCharCode(first);
      } else if ((first & 224) === 192) {
        output += String.fromCharCode(
          ((first & 31) << 6) | (bytes[index++] & 63),
        );
      } else if ((first & 240) === 224) {
        output += String.fromCharCode(
          ((first & 15) << 12) |
            ((bytes[index++] & 63) << 6) |
            (bytes[index++] & 63),
        );
      } else {
        const codePoint =
          ((first & 7) << 18) |
          ((bytes[index++] & 63) << 12) |
          ((bytes[index++] & 63) << 6) |
          (bytes[index++] & 63);
        const adjusted = codePoint - 65536;
        output += String.fromCharCode(
          55296 + (adjusted >> 10),
          56320 + (adjusted & 1023),
        );
      }
    }
    return output;
  };
}

// MiniRacer does not provide a browser security boundary. Keep the embedded
// renderer unable to create or evaluate arbitrary JavaScript, including when
// a future bundle accidentally references these ambient V8 capabilities.
Object.defineProperty(globalThis, "eval", {
  value: undefined,
  writable: false,
  configurable: false,
});
Object.defineProperty(globalThis, "Function", {
  value: undefined,
  writable: false,
  configurable: false,
});

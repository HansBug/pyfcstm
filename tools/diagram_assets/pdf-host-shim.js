// Host capabilities the PDF writer needs at module-initialisation time.
//
// This is a separate asset, evaluated before the PDF bundle, for the same reason
// ``host-shim.js`` is: jsPDF reads ``navigator`` while its module body runs, and
// a bundler hoists that above anything the entry file assigns. Installing these
// from inside the bundle is therefore too late -- the bundle throws
// ``ReferenceError: navigator is not defined`` before its own first statement.
//
// The DOM contract lives in the bundle instead, because it is built on the
// ``xmldom`` implementation the bundle carries, and nothing in a module body
// needs it: only the export call does.
//
// Nothing here relaxes the boundary ``host-shim.js`` sets. ``eval`` and
// ``Function`` stay unavailable, and neither ``jspdf`` nor ``svg2pdf.js``
// references them.
globalThis.navigator = globalThis.navigator || {
    userAgent: "pyfcstm-embedded",
    language: "en",
};

if (typeof globalThis.btoa === "undefined") {
    // ``host-shim.js`` provides ``atob`` but not its counterpart, and jsPDF
    // encodes embedded streams with it.
    globalThis.btoa = function (value) {
        const alphabet =
            "ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/";
        const text = String(value);
        let output = "";
        for (let index = 0; index < text.length; index += 3) {
            const first = text.charCodeAt(index) & 0xff;
            const second =
                index + 1 < text.length ? text.charCodeAt(index + 1) & 0xff : undefined;
            const third =
                index + 2 < text.length ? text.charCodeAt(index + 2) & 0xff : undefined;
            output += alphabet[first >> 2];
            output +=
                alphabet[
                    ((first & 3) << 4) | (second === undefined ? 0 : second >> 4)
                ];
            output +=
                second === undefined
                    ? "="
                    : alphabet[
                          ((second & 15) << 2) | (third === undefined ? 0 : third >> 6)
                      ];
            output += third === undefined ? "=" : alphabet[third & 63];
        }
        return output;
    };
}

/**
 * Bundle entry for pyfcstm's embedded JS runtime.
 *
 * Produces a single self-contained IIFE consumed by `pyfcstm.jsruntime`:
 *
 *   - jsfcstm pipeline: parser → AST → state-machine model → diagram IR
 *     → ELK graph → ELK layout → SVG string
 *   - SVG → PNG: @resvg/resvg-wasm; the host (Python) compiles + supplies
 *     the WASM bytes through `__fcstm_init_wasm`, then optionally feeds
 *     a default font through `__fcstm_register_font`
 *
 * The bundle exposes three entry points on `globalThis`:
 *
 *   __fcstm_init_wasm(b64WasmBytes)  -> Promise (drained at script end)
 *   __fcstm_register_font(b64Bytes)  -> stores font for later renders
 *   __fcstm_export(format, dsl, optionsJson, scale) -> kicks off render;
 *      caller polls __fcstm_export_result (base64) / __fcstm_export_error
 */
const ELK = require('elkjs/lib/elk-api').default;
const {Worker} = require('elkjs/lib/elk-worker.min');
const elk = new ELK({workerFactory: url => new Worker(url)});

const {getParser} = require('@pyfcstm/jsfcstm/dsl');
const {buildAstFromTree} = require('@pyfcstm/jsfcstm/ast');
const {buildStateMachineModel} = require('@pyfcstm/jsfcstm/model');
const {
    buildFcstmDiagramFromStateMachine,
    buildFcstmElkGraph,
    resolveFcstmDiagramPreviewOptions,
    renderFcstmDiagramSvg,
} = require('@pyfcstm/jsfcstm/diagram');

const resvgBinding = require('@resvg/resvg-wasm');

let resvgFontBuffers = [];

function makeDoc(text) {
    const lines = String(text || '').split(/\r?\n/);
    return {
        getText: () => text,
        lineCount: lines.length,
        lineAt: (i) => ({text: lines[i] || ''}),
        filePath: 'inline.fcstm',
    };
}

function bytesFromBase64(b64) {
    const bin = atob(String(b64 || ''));
    const a = new Uint8Array(bin.length);
    for (let i = 0; i < bin.length; i++) a[i] = bin.charCodeAt(i);
    return a;
}

function bytesToBase64(u8) {
    const chars = 'ABCDEFGHIJKLMNOPQRSTUVWXYZabcdefghijklmnopqrstuvwxyz0123456789+/';
    let s = '';
    for (let i = 0; i < u8.length; i += 3) {
        const b1 = u8[i];
        const b2 = u8[i + 1] != null ? u8[i + 1] : 0;
        const b3 = u8[i + 2] != null ? u8[i + 2] : 0;
        s += chars[b1 >> 2]
            + chars[((b1 & 3) << 4) | (b2 >> 4)]
            + (i + 1 < u8.length ? chars[((b2 & 15) << 2) | (b3 >> 6)] : '=')
            + (i + 2 < u8.length ? chars[b3 & 63] : '=');
    }
    return s;
}

globalThis.__fcstm_init_wasm = function (b64WasmBytes) {
    globalThis.__fcstm_wasm_status = 'pending';
    globalThis.__fcstm_wasm_error = null;
    const bytes = bytesFromBase64(b64WasmBytes);
    WebAssembly.compile(bytes).then(
        (mod) => resvgBinding.initWasm(mod)
    ).then(
        () => { globalThis.__fcstm_wasm_status = 'ok'; },
        (e) => {
            globalThis.__fcstm_wasm_status = 'error';
            globalThis.__fcstm_wasm_error = String((e && e.stack) || e);
        }
    );
};

globalThis.__fcstm_register_font = function (b64FontBytes) {
    resvgFontBuffers = [bytesFromBase64(b64FontBytes)];
};

async function pipelineSvg(text, optionsJson) {
    const userOptions = optionsJson ? JSON.parse(optionsJson) : {};
    const options = resolveFcstmDiagramPreviewOptions(userOptions);
    const doc = makeDoc(text);
    const tree = await getParser().parseTree(text);
    if (!tree) throw new Error('FCSTM parser returned no tree');
    const ast = buildAstFromTree(tree, doc);
    if (!ast) throw new Error('AST construction failed');
    const sm = buildStateMachineModel(ast);
    if (!sm) {
        throw new Error('State-machine model construction failed (likely a DSL parse / semantic error)');
    }
    const diagram = buildFcstmDiagramFromStateMachine(sm);
    if (!diagram) throw new Error('Diagram IR construction failed');
    const graph = buildFcstmElkGraph(diagram, options);
    const laid = await elk.layout(graph);
    return {svg: renderFcstmDiagramSvg(laid, options), options};
}

function rasterize(svg, scale) {
    const safeScale = Number(scale) > 0 ? Number(scale) : 1.0;
    const resvgOptions = {
        fitTo: {mode: 'zoom', value: safeScale},
        font: {
            fontBuffers: resvgFontBuffers,
            loadSystemFonts: false,
            defaultFontFamily: 'JetBrains Mono',
        },
    };
    const r = new resvgBinding.Resvg(svg, resvgOptions);
    const rendered = r.render();
    return rendered.asPng();
}

globalThis.__fcstm_export = function (format, dsl, optionsJson, scale) {
    globalThis.__fcstm_export_result = null;
    globalThis.__fcstm_export_error = null;
    pipelineSvg(dsl, optionsJson).then(
        ({svg}) => {
            try {
                if (format === 'svg') {
                    // SVG is text. Base64-encode the UTF-8 bytes so the
                    // Python side can use one transport for everything.
                    const enc = new TextEncoder().encode(svg);
                    globalThis.__fcstm_export_result = bytesToBase64(enc);
                } else if (format === 'png') {
                    const png = rasterize(svg, scale);
                    globalThis.__fcstm_export_result = bytesToBase64(png);
                } else {
                    throw new Error('Unsupported format: ' + format);
                }
            } catch (e) {
                globalThis.__fcstm_export_error = String((e && e.stack) || e);
            }
        },
        (e) => {
            globalThis.__fcstm_export_error = String((e && e.stack) || e);
        }
    );
};

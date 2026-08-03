/**
 * Framework-neutral browser diagram export helpers.
 *
 * The module owns SVG normalization and the vector PDF path. Hosts provide
 * the optional resvg expansion callback; the Python standalone host supplies
 * it from the embedded WASM asset, while a later headless host can provide a
 * DOM-compatible implementation without copying this export logic.
 */

import {jsPDF} from 'jspdf';
import {svg2pdf} from 'svg2pdf.js';

export type SvgExpander = (svg: string) => Promise<string>;

function parseSvg(source: string): SVGElement {
    const parsed = new DOMParser().parseFromString(String(source), 'image/svg+xml');
    const root = parsed.documentElement;
    if (!root || root.nodeName.toLowerCase() !== 'svg') {
        throw new Error('SVG export produced no root element');
    }
    return root as unknown as SVGElement;
}

/**
 * Remove browser-only text halos before passing SVG to svg2pdf.js.
 */
export function prepareSvgForPdf(source: string): string {
    const root = parseSvg(source);
    root.querySelectorAll('[data-fcstm-kind="transition-label"] text[paint-order="stroke"]').forEach(text => {
        text.removeAttribute('paint-order');
        text.removeAttribute('stroke');
        text.removeAttribute('stroke-width');
        text.removeAttribute('stroke-linejoin');
    });
    return new XMLSerializer().serializeToString(root);
}

/**
 * Expand a canonical SVG for a self-contained download when a host provides
 * the shared resvg callback. Hosts without that optional callback retain the
 * canonical SVG for interactive use, but should not claim it is expanded.
 */
export async function expandSvgForExport(
    source: string,
    expand?: SvgExpander,
): Promise<string> {
    const canonical = String(source);
    parseSvg(canonical);
    if (!expand) return canonical;
    const expanded = await expand(canonical);
    parseSvg(expanded);
    return expanded;
}

/**
 * Largest accepted export scale.
 *
 * These three are product limits rather than host capabilities, and they behave
 * differently from `RASTER_MAX_SIDE` and `RASTER_MAX_AREA` below: an export past
 * a product limit is *refused*, while one past a host capability is *clamped*.
 * The distinction matters because a clamp is silent -- asking for 4x and getting
 * 2.7x looks like success -- and a caller who chose a scale deserves to be told
 * their choice was not honoured.
 *
 * Every value here is deliberately stricter than its host-capability
 * counterpart, so the refusal always fires first and the clamp is a defensive
 * second layer that ordinary input never reaches.
 * `assertExportLimitsAreStricterThanHostLimits` pins that ordering.
 *
 * The same numbers are enforced on the Python export path, and
 * `tools/check_diagram_export_limits.py` fails if the two sides drift apart.
 */
export const EXPORT_MAX_SCALE = 4;

/**
 * Scale the viewer's PNG download uses.
 *
 * It lives here rather than at the call site so the parity checks and the
 * documentation can name one value instead of restating a literal that the export
 * path is free to change underneath them.
 */
export const EXPORT_PNG_SCALE = 2;

/** Largest accepted scaled edge, in device pixels. */
export const EXPORT_MAX_EDGE_PX = 16384;

/** Largest accepted scaled pixel count. */
export const EXPORT_MAX_PIXELS = 16777216;

/** Reported when an export exceeds a product limit rather than a host one. */
export class DiagramExportLimitError extends Error {
    readonly limitName: string;

    constructor(message: string, limitName: string) {
        super(message);
        this.name = 'DiagramExportLimitError';
        this.limitName = limitName;
    }
}

/**
 * Refuse an export whose scaled size exceeds a product limit.
 *
 * The multiplication happens here, before any canvas is allocated, so an
 * impossible request is named instead of being discovered by the rasteriser
 * failing. The message carries the original size, the scaled size, the limit that
 * fired and what to change, because "too large" on its own does not tell a caller
 * which scale would have fitted.
 *
 * @param width  Diagram width in CSS pixels.
 * @param height Diagram height in CSS pixels.
 * @param scale  Requested scale factor.
 */
export function assertWithinExportLimits(
    width: number,
    height: number,
    scale: number,
): {width: number; height: number} {
    if (!Number.isFinite(scale) || scale <= 0) {
        throw new RangeError(`scale must be a finite positive number; got ${scale}`);
    }
    if (scale > EXPORT_MAX_SCALE) {
        throw new RangeError(`scale must be at most ${EXPORT_MAX_SCALE}; got ${scale}`);
    }
    const scaledWidth = Math.ceil(Math.max(1, width) * scale);
    const scaledHeight = Math.ceil(Math.max(1, height) * scale);
    const origin =
        `${width}x${height} at scale ${scale} gives ${scaledWidth}x${scaledHeight}`;
    const advice = 'lower scale and retry';
    for (const [name, value] of [
        ['width', scaledWidth],
        ['height', scaledHeight],
    ] as Array<[string, number]>) {
        if (value > EXPORT_MAX_EDGE_PX) {
            throw new DiagramExportLimitError(
                `${origin}, whose ${name} exceeds the ${EXPORT_MAX_EDGE_PX}px limit; ${advice}`,
                'edge',
            );
        }
    }
    const pixels = scaledWidth * scaledHeight;
    if (pixels > EXPORT_MAX_PIXELS) {
        throw new DiagramExportLimitError(
            `${origin}, which is ${pixels} pixels and exceeds the ${EXPORT_MAX_PIXELS} limit; ${advice}`,
            'pixels',
        );
    }
    return {width: scaledWidth, height: scaledHeight};
}

/**
 * Largest canvas side a browser will rasterise, in device pixels.
 *
 * Chrome refuses anything past 65535 and `toBlob` then yields null with no
 * error; Firefox stops at 32767 and Safari at 16384. The standalone viewer is
 * a plain HTML file that can be opened in any of them, so the lowest common
 * limit that still leaves room for detail is used.
 */
export const RASTER_MAX_SIDE = 32767;

/**
 * Largest canvas area a browser will rasterise, in device pixels.
 */
export const RASTER_MAX_AREA = 268435456;

/**
 * Largest scale at or below `requested` whose canvas a browser will accept.
 *
 * A tall diagram at the nominal 2x exceeded the side limit, and `toBlob` then
 * returned null — which took the SVG and PDF down with it and left a large
 * model with no export at all. Scaling down loses raster detail; the vector
 * formats still carry the full drawing.
 *
 * @param width  Diagram width in CSS pixels.
 * @param height Diagram height in CSS pixels.
 * @param requested Preferred scale factor.
 */
export function rasterScaleWithinLimits(
    width: number,
    height: number,
    requested: number,
): number {
    const w = Math.max(1, width);
    const h = Math.max(1, height);
    // Rounding happens at the call site and `ceil` can add a pixel per side,
    // so both bounds are computed against the rounded size rather than the
    // exact one. The area budget already allowed for that; the side budget did
    // not, and `RASTER_MAX_SIDE / h` alone let `Math.ceil(h * fit)` land on
    // 32768 for 6311 heights between 1 and 60000 at a width of 600 -- starting
    // at 16577, which is where the side bound first becomes the binding one
    // rather than at the 32767 limit itself.
    let fit = Math.min(
        requested,
        (RASTER_MAX_SIDE - 1) / w,
        (RASTER_MAX_SIDE - 1) / h,
        Math.sqrt(RASTER_MAX_AREA / (w * h)),
    );
    const rounded = (Math.ceil(w * fit) + 1) * (Math.ceil(h * fit) + 1);
    if (rounded > RASTER_MAX_AREA) {
        fit *= Math.sqrt(RASTER_MAX_AREA / rounded);
    }
    return fit;
}

/**
 * Assert every product limit is stricter than the host capability it shadows.
 *
 * If a product limit were ever raised past its host counterpart, the clamp below
 * would start firing for input the refusal had already let through, and the two
 * export paths would disagree again -- silently, because a clamped export still
 * succeeds. Calling this from a test keeps that ordering a checked property
 * rather than a comment.
 */
export function assertExportLimitsAreStricterThanHostLimits(): void {
    if (EXPORT_MAX_EDGE_PX >= RASTER_MAX_SIDE) {
        throw new Error(
            `the export edge limit (${EXPORT_MAX_EDGE_PX}) must stay below the ` +
                `host limit (${RASTER_MAX_SIDE})`,
        );
    }
    if (EXPORT_MAX_PIXELS >= RASTER_MAX_AREA) {
        throw new Error(
            `the export pixel limit (${EXPORT_MAX_PIXELS}) must stay below the ` +
                `host limit (${RASTER_MAX_AREA})`,
        );
    }
}

/**
 * Largest page dimension jsPDF will accept, in PDF units.
 *
 * Anything beyond this is clamped by the library without an error, so a page
 * built from raw diagram bounds loses whatever falls outside.
 */
export const PDF_MAX_UNITS = 14400;

/**
 * Render one diagram-sized vector PDF from a canonical SVG.
 *
 * `source` is the renderer's canonical output, not an expanded document. The
 * order matters and is not interchangeable: halo removal matches the `<text>`
 * elements that carry a stroke paint order, and expansion replaces those with
 * paths. A caller that expands first hands over a document in which the halos
 * can no longer be found, and each one is then drawn into the PDF as a white
 * shape over its own glyphs.
 *
 * @param source Canonical SVG from the renderer.
 * @param bounds Diagram size, which becomes the page size.
 * @param expand Optional expander; without one the canonical document is used
 *     as-is, and text depends on fonts the reader may not have.
 */
export async function renderVectorPdf(
    source: string,
    bounds: {width: number; height: number},
    expand?: SvgExpander,
): Promise<Uint8Array> {
    const width = Math.max(1, bounds.width);
    const height = Math.max(1, bounds.height);
    // jsPDF refuses a page larger than PDF_MAX_UNITS and clamps it silently,
    // which cut the bottom 39% off a 300-state diagram while the export still
    // reported success. Scale the whole drawing to fit instead: a PDF unit is
    // arbitrary for a diagram, so this costs absolute size and nothing else,
    // and the page keeps the diagram's aspect ratio.
    const fit = Math.min(1, PDF_MAX_UNITS / Math.max(width, height));
    // Clamped after multiplying, not just before: `width * (CAP / width)` lands
    // a couple of ulps above CAP for about a tenth of integer sizes, which is
    // geometrically irrelevant but still trips jsPDF's clamp warning.
    const pageWidth = Math.min(PDF_MAX_UNITS, width * fit);
    const pageHeight = Math.min(PDF_MAX_UNITS, height * fit);
    const normalized = prepareSvgForPdf(source);
    const expanded = await expandSvgForExport(normalized, expand);
    const svg = parseSvg(expanded);
    const pdf = new jsPDF({
        orientation: pageWidth > pageHeight ? 'landscape' : 'portrait',
        unit: 'pt',
        format: [pageWidth, pageHeight],
        compress: true,
    });
    await svg2pdf(svg, pdf, {
        x: 0,
        y: 0,
        width: pageWidth,
        height: pageHeight,
        loadExternalStyleSheets: false,
    });
    return new Uint8Array(pdf.output('arraybuffer') as ArrayBuffer);
}

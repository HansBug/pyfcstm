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
    const fit = Math.min(
        requested,
        RASTER_MAX_SIDE / w,
        RASTER_MAX_SIDE / h,
        Math.sqrt(RASTER_MAX_AREA / (w * h)),
    );
    // Rounding happens at the call site, and `ceil` can add a pixel to each
    // side. Leave room for both so the rounded canvas is still inside the area
    // cap, which browsers enforce exactly.
    const rounded = (Math.ceil(w * fit) + 1) * (Math.ceil(h * fit) + 1);
    return rounded <= RASTER_MAX_AREA ? fit : fit * Math.sqrt(RASTER_MAX_AREA / rounded);
}

/**
 * Largest page dimension jsPDF will accept, in PDF units.
 *
 * Anything beyond this is clamped by the library without an error, so a page
 * built from raw diagram bounds loses whatever falls outside.
 */
export const PDF_MAX_UNITS = 14400;

/**
 * Render one diagram-sized vector PDF from the shared expanded SVG path.
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

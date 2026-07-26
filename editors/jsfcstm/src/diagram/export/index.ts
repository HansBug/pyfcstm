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
 * Render one diagram-sized vector PDF from the shared expanded SVG path.
 */
export async function renderVectorPdf(
    source: string,
    bounds: {width: number; height: number},
    expand?: SvgExpander,
): Promise<Uint8Array> {
    const width = Math.max(1, bounds.width);
    const height = Math.max(1, bounds.height);
    const normalized = prepareSvgForPdf(source);
    const expanded = await expandSvgForExport(normalized, expand);
    const svg = parseSvg(expanded);
    const pdf = new jsPDF({
        orientation: width > height ? 'landscape' : 'portrait',
        unit: 'pt',
        format: [width, height],
        compress: true,
    });
    await svg2pdf(svg, pdf, {
        x: 0,
        y: 0,
        width,
        height,
        loadExternalStyleSheets: false,
    });
    return new Uint8Array(pdf.output('arraybuffer') as ArrayBuffer);
}

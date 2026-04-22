/**
 * Pure laid-out-ELK-graph -> SVG string renderer.
 *
 * Each SVG element carries ``data-fcstm-*`` attributes so the webview
 * (or any downstream consumer) can map click/hover events back to the
 * original DSL source range.
 */
import type {
    FcstmElkEdge,
    FcstmElkNode,
    ResolvedFcstmDiagramPreviewOptions,
} from './model';
import type {TextRange} from '../utils/text';

/**
 * Visual tokens. Leaf, composite, and pseudo states each get a distinct
 * silhouette so they are trivially identifiable at a glance.
 *
 * - leaf: clean white card with a single-stroke blue border and a soft
 *   drop shadow.
 * - composite: tinted blue background, a slightly thicker border, and a
 *   chip-like title strip to separate the children from the header.
 * - pseudo (DSL-marked): warm sand fill with a dashed amber border so the
 *   ``pseudo`` DSL marker reads visually on the diagram.
 */
const STYLE = {
    canvasPadding: 28,
    leafFill: '#ffffff',
    leafStroke: '#5a92c4',
    leafStrokeWidth: 1.4,
    leafRadius: 10,
    compositeFill: '#edf4fb',
    compositeTitleFill: '#dce9f5',
    compositeStroke: '#2d6aa8',
    compositeStrokeWidth: 1.8,
    compositeRadius: 16,
    pseudoStateFill: '#fdf3e1',
    pseudoStateStroke: '#b07a36',
    pseudoStrokeWidth: 1.4,
    pseudoDash: '6 3',
    titleColor: '#183b61',
    mutedTitleColor: '#3a5878',
    initFill: '#2d6aa8',
    exitOuterStroke: '#2d6aa8',
    exitInnerFill: '#2d6aa8',
    edgeStroke: '#3470a8',
    edgeLabelText: '#1e476e',
    edgeLabelHalo: '#ffffff',
    edgeLabelGuardColor: '#9c5d00',
    edgeLabelEventColor: '#2d6aa8',
    edgeLabelEffectColor: '#4a6b8c',
    fontFamily: '"JetBrains Mono","Fira Code",Consolas,monospace',
    forcedEdgeDasharray: '6 4',
    entryEdgeWeight: 1.7,
    normalEdgeWeight: 1.4,
};

/** First Unicode char of each transition-label line decides its role. */
const LABEL_GLYPH_EVENT = '●';
const LABEL_GLYPH_GUARD = '◇';
const LABEL_GLYPH_EFFECT = '▸';

function escapeXml(value: unknown): string {
    return String(value ?? '').replace(/[&<>"']/g, ch => ({
        '&': '&amp;',
        '<': '&lt;',
        '>': '&gt;',
        '"': '&quot;',
        "'": '&apos;',
    })[ch] as string);
}

function quote(attr: string, value: unknown): string {
    return `${attr}="${escapeXml(value)}"`;
}

function rangeAttrs(prefix: string, range: TextRange | undefined): string {
    if (!range) {
        return '';
    }
    return [
        `data-${prefix}-start-line="${range.start.line}"`,
        `data-${prefix}-start-character="${range.start.character}"`,
        `data-${prefix}-end-line="${range.end.line}"`,
        `data-${prefix}-end-character="${range.end.character}"`,
    ].join(' ');
}

function colorForLabelLine(line: string, fallback: string): string {
    if (line.startsWith(LABEL_GLYPH_GUARD)) return STYLE.edgeLabelGuardColor;
    if (line.startsWith(LABEL_GLYPH_EFFECT)) return STYLE.edgeLabelEffectColor;
    if (line.startsWith(LABEL_GLYPH_EVENT)) return STYLE.edgeLabelEventColor;
    return fallback;
}

/** SVG renderer entry point. */
export function renderFcstmDiagramSvg(
    canvas: FcstmElkNode,
    options: ResolvedFcstmDiagramPreviewOptions
): string {
    const width = Math.ceil(canvas.width || 0) + STYLE.canvasPadding;
    const height = Math.ceil(canvas.height || 0) + STYLE.canvasPadding;
    const out: string[] = [];

    out.push(
        `<svg xmlns="http://www.w3.org/2000/svg" ` +
        `viewBox="0 0 ${width} ${height}" ` +
        `width="${width}" height="${height}" ` +
        `${quote('font-family', STYLE.fontFamily)} font-size="14" ` +
        `data-fcstm-canvas="true" data-fcstm-direction="${options.direction}">`
    );
    out.push(renderDefs());
    out.push(`<rect x="0" y="0" width="${width}" height="${height}" fill="transparent"/>`);

    const drawNode = (node: FcstmElkNode, offsetX: number, offsetY: number, depth: number): void => {
        const x = (node.x || 0) + offsetX;
        const y = (node.y || 0) + offsetY;
        const w = node.width || 0;
        const h = node.height || 0;
        const meta = node.fcstm;
        if (!meta) {
            for (const child of node.children || []) {
                drawNode(child, x, y, depth + 1);
            }
            for (const edge of node.edges || []) {
                drawEdge(edge, x, y, out);
            }
            return;
        }

        if (meta.kind === 'canvas') {
            for (const child of node.children || []) {
                drawNode(child, x, y, depth + 1);
            }
            for (const edge of node.edges || []) {
                drawEdge(edge, x, y, out);
            }
            return;
        }

        if (meta.kind === 'pseudoInit') {
            out.push(
                `<circle cx="${x + w / 2}" cy="${y + h / 2}" r="${Math.min(w, h) / 2}" ` +
                `fill="${STYLE.initFill}" ` +
                `${quote('data-fcstm-kind', 'pseudo-init')} ` +
                `${quote('data-fcstm-id', node.id)}/>`
            );
            return;
        }

        if (meta.kind === 'pseudoExit') {
            const r = Math.min(w, h) / 2;
            const cx = x + w / 2;
            const cy = y + h / 2;
            out.push(
                `<g ${quote('data-fcstm-kind', 'pseudo-exit')} ${quote('data-fcstm-id', node.id)}>` +
                `<circle cx="${cx}" cy="${cy}" r="${r}" fill="#ffffff" stroke="${STYLE.exitOuterStroke}" stroke-width="1.6"/>` +
                `<circle cx="${cx}" cy="${cy}" r="${Math.max(0, r - 4)}" fill="${STYLE.exitInnerFill}"/>` +
                `</g>`
            );
            return;
        }

        const isComposite = Boolean(meta.composite) && !meta.collapsed;
        const isPseudo = Boolean(meta.pseudo);
        const labelText = node.labels?.[0]?.text || meta.qualifiedName || node.id;

        let fill: string;
        let stroke: string;
        let strokeWidth: number;
        let radius: number;
        let extraAttrs = '';
        let variant: 'leaf' | 'composite' | 'pseudo';

        if (isPseudo) {
            variant = 'pseudo';
            fill = STYLE.pseudoStateFill;
            stroke = STYLE.pseudoStateStroke;
            strokeWidth = STYLE.pseudoStrokeWidth;
            radius = STYLE.leafRadius;
            extraAttrs = `stroke-dasharray="${STYLE.pseudoDash}" `;
        } else if (isComposite) {
            variant = 'composite';
            fill = STYLE.compositeFill;
            stroke = STYLE.compositeStroke;
            strokeWidth = STYLE.compositeStrokeWidth;
            radius = STYLE.compositeRadius;
        } else {
            variant = 'leaf';
            fill = STYLE.leafFill;
            stroke = STYLE.leafStroke;
            strokeWidth = STYLE.leafStrokeWidth;
            radius = STYLE.leafRadius;
        }

        out.push(
            `<g ${quote('data-fcstm-kind', isComposite ? 'composite-state' : 'state')} ` +
            `${quote('data-fcstm-id', meta.qualifiedName || node.id)} ` +
            `${quote('data-fcstm-variant', variant)} ` +
            `${quote('data-fcstm-pseudo', String(isPseudo))} ` +
            `${quote('data-fcstm-composite', String(Boolean(meta.composite)))} ` +
            `${quote('data-fcstm-collapsed', String(Boolean(meta.collapsed)))} ` +
            `${rangeAttrs('fcstm-range', meta.sourceRange)}>`
        );

        // Leaf cards get a subtle drop shadow for visual lift; composites
        // use a flatter look so nested children stand out instead.
        const shadow = variant === 'leaf' ? ' filter="url(#fcstm-leaf-shadow)"' : '';
        out.push(
            `<rect x="${x}" y="${y}" width="${w}" height="${h}" ` +
            `rx="${radius}" ry="${radius}" ` +
            `fill="${fill}" stroke="${stroke}" stroke-width="${strokeWidth}" ` +
            extraAttrs +
            shadow +
            ` />`
        );

        if (isComposite) {
            // Title strip: a soft tint band that doubles as a hit target for
            // the chevron, keeping the composite header visually distinct
            // from its children.
            const titleHeight = 32;
            out.push(
                `<path d="M${x + radius},${y} L${x + w - radius},${y} ` +
                `Q${x + w},${y} ${x + w},${y + radius} L${x + w},${y + titleHeight} ` +
                `L${x},${y + titleHeight} L${x},${y + radius} ` +
                `Q${x},${y} ${x + radius},${y} Z" ` +
                `fill="${STYLE.compositeTitleFill}" stroke="none"/>`
            );
            out.push(
                `<text x="${x + 16}" y="${y + 21}" fill="${STYLE.titleColor}" ` +
                `font-weight="700" font-size="14">${escapeXml(labelText)}</text>`
            );
            out.push(
                `<line x1="${x}" y1="${y + titleHeight}" x2="${x + w}" y2="${y + titleHeight}" ` +
                `stroke="${STYLE.compositeStroke}" stroke-opacity="0.35" stroke-width="1"/>`
            );
        } else {
            // Leaf / pseudo: a centered label, nothing else. Detail summaries
            // live in the Details side panel.
            out.push(
                `<text x="${x + w / 2}" y="${y + h / 2 + 5}" fill="${STYLE.titleColor}" ` +
                `font-weight="600" text-anchor="middle">${escapeXml(labelText)}</text>`
            );
            if (isPseudo) {
                // A small pseudo-state tag at the top-left so the variant is
                // unmistakable even if the dashed border blends in.
                out.push(
                    `<text x="${x + 10}" y="${y + 14}" fill="${STYLE.pseudoStateStroke}" ` +
                    `font-size="10" font-weight="700" letter-spacing="0.04em">pseudo</text>`
                );
            }
        }

        if (isComposite || meta.collapsed) {
            const chevronX = x + w - 22;
            const chevronY = y + 16;
            const collapsed = Boolean(meta.collapsed);
            const path = collapsed
                ? `M${chevronX},${chevronY} l4,4 l4,-4`
                : `M${chevronX},${chevronY + 2} l4,-4 l4,4`;
            out.push(
                `<path d="${path}" fill="none" stroke="${STYLE.titleColor}" ` +
                `stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" ` +
                `data-fcstm-kind="chevron" ` +
                `${quote('data-fcstm-id', meta.qualifiedName || node.id)} ` +
                `${rangeAttrs('fcstm-range', meta.sourceRange)}/>`
            );
        }

        out.push('</g>');

        if (!meta.collapsed) {
            for (const child of node.children || []) {
                drawNode(child, x, y, depth + 1);
            }
            for (const edge of node.edges || []) {
                drawEdge(edge, x, y, out);
            }
        }
    };

    drawNode(canvas, 0, 0, 0);
    out.push('</svg>');
    return out.join('\n');
}

function drawEdge(edge: FcstmElkEdge, ox: number, oy: number, out: string[]): void {
    const meta = edge.fcstm;
    const kind = meta?.transitionKind || 'normal';
    const forced = Boolean(meta?.forced);
    const color = meta?.eventColor || STYLE.edgeStroke;
    const weight = kind === 'entry' || kind === 'exit' ? STYLE.entryEdgeWeight : STYLE.normalEdgeWeight;
    const dasharray = forced ? STYLE.forcedEdgeDasharray : '';

    for (const section of edge.sections || []) {
        const pts = [
            [section.startPoint.x + ox, section.startPoint.y + oy],
            ...(section.bendPoints || []).map(pt => [pt.x + ox, pt.y + oy]),
            [section.endPoint.x + ox, section.endPoint.y + oy],
        ];
        const d = pts.map(([x, y], i) => `${i === 0 ? 'M' : 'L'}${x.toFixed(2)},${y.toFixed(2)}`).join(' ');
        out.push(
            `<path ${quote('d', d)} fill="none" stroke="${color}" stroke-width="${weight}" ` +
            (dasharray ? `stroke-dasharray="${dasharray}" ` : '') +
            `marker-end="url(#fcstm-arrow)" ` +
            `${quote('data-fcstm-kind', 'transition')} ` +
            `${quote('data-fcstm-id', meta?.transitionId || edge.id)} ` +
            `${rangeAttrs('fcstm-range', meta?.sourceRange)} ` +
            `/>`
        );
    }

    // Transition labels: no background rectangle anymore. Each line is
    // rendered with a white stroke halo (paint-order stroke then fill) so
    // text stays legible even when the label crosses another edge.
    for (const label of edge.labels || []) {
        const lx = (label.x || 0) + ox;
        const ly = (label.y || 0) + oy;
        const lh = label.height || 0;
        out.push(
            `<g ${quote('data-fcstm-kind', 'transition-label')} ` +
            `${quote('data-fcstm-id', meta?.transitionId || edge.id)} ` +
            `${rangeAttrs('fcstm-range', meta?.sourceRange)}>`
        );
        const lines = String(label.text).split('\n');
        const lineOffset = lh / Math.max(1, lines.length);
        for (const [i, line] of lines.entries()) {
            const lineColor = colorForLabelLine(line, color);
            out.push(
                `<text x="${lx + 2}" y="${ly + lineOffset * (i + 0.7) + 2}" ` +
                `fill="${lineColor}" font-size="12" font-weight="500" ` +
                `paint-order="stroke" stroke="${STYLE.edgeLabelHalo}" stroke-width="3" stroke-linejoin="round">` +
                `${escapeXml(line)}</text>`
            );
        }
        out.push('</g>');
    }
}

function renderDefs(): string {
    return [
        '<defs>',
        `<marker id="fcstm-arrow" viewBox="0 0 10 10" refX="9" refY="5" `,
        `markerWidth="10" markerHeight="10" orient="auto-start-reverse" markerUnits="userSpaceOnUse">`,
        `<path d="M0,0 L10,5 L0,10 z" fill="${STYLE.edgeStroke}"/>`,
        '</marker>',
        // Soft drop shadow reserved for leaf states.
        '<filter id="fcstm-leaf-shadow" x="-10%" y="-10%" width="120%" height="130%">',
        '<feGaussianBlur in="SourceAlpha" stdDeviation="1.4"/>',
        '<feOffset dx="0" dy="1"/>',
        '<feComponentTransfer><feFuncA type="linear" slope="0.18"/></feComponentTransfer>',
        '<feMerge><feMergeNode/><feMergeNode in="SourceGraphic"/></feMerge>',
        '</filter>',
        '</defs>',
    ].join('');
}

export const __svgRendererInternals = {
    STYLE,
    escapeXml,
    rangeAttrs,
    LABEL_GLYPH_EVENT,
    LABEL_GLYPH_GUARD,
    LABEL_GLYPH_EFFECT,
};

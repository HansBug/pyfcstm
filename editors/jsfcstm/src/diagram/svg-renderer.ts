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

/** Visual tokens used throughout the renderer. */
const STYLE = {
    canvasPadding: 24,
    stateFill: '#ffffff',
    stateStroke: '#7da9d7',
    stateTitleColor: '#183b61',
    compositeFill: '#f4f8fc',
    compositeStroke: '#8cb3dc',
    pseudoStateFill: '#f3e6e6',
    pseudoStateStroke: '#b07575',
    initFill: '#2d6aa8',
    exitOuterStroke: '#2d6aa8',
    exitInnerFill: '#2d6aa8',
    edgeStroke: '#3470a8',
    edgeLabelBg: '#ffffff',
    edgeLabelBorder: '#c2d4e8',
    edgeLabelText: '#183b61',
    fontFamily: '"JetBrains Mono","Fira Code",Consolas,monospace',
    forcedEdgeDasharray: '6 4',
    entryEdgeWeight: 1.7,
    normalEdgeWeight: 1.4,
};

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

        // Regular state node.
        const isComposite = Boolean(meta.composite);
        const isPseudo = Boolean(meta.pseudo);
        const isLeaf = !isComposite || meta.collapsed;
        const fill = isPseudo
            ? STYLE.pseudoStateFill
            : isComposite && !meta.collapsed
                ? STYLE.compositeFill
                : STYLE.stateFill;
        const stroke = isPseudo ? STYLE.pseudoStateStroke : isComposite ? STYLE.compositeStroke : STYLE.stateStroke;
        const labelText = node.labels?.[0]?.text || meta.qualifiedName || node.id;

        out.push(
            `<g ${quote('data-fcstm-kind', isComposite ? 'composite-state' : 'state')} ` +
            `${quote('data-fcstm-id', meta.qualifiedName || node.id)} ` +
            `${quote('data-fcstm-pseudo', String(isPseudo))} ` +
            `${quote('data-fcstm-composite', String(isComposite))} ` +
            `${quote('data-fcstm-collapsed', String(Boolean(meta.collapsed)))} ` +
            `${rangeAttrs('fcstm-range', meta.sourceRange)}>`
        );
        out.push(
            `<rect x="${x}" y="${y}" width="${w}" height="${h}" ` +
            `rx="${isComposite ? 16 : 10}" ry="${isComposite ? 16 : 10}" ` +
            `fill="${fill}" stroke="${stroke}" stroke-width="1.6" ` +
            (isPseudo ? 'stroke-dasharray="4 3" ' : '') +
            `/>`
        );

        // Title text: composite titles are anchored top-left inside the box;
        // leaf titles center inside the box.
        if (isComposite && !meta.collapsed) {
            out.push(
                `<text x="${x + 16}" y="${y + 22}" fill="${STYLE.stateTitleColor}" ` +
                `font-weight="700" font-size="14">${escapeXml(labelText)}</text>`
            );
            // Draw the title strip separator line for visual clarity.
            out.push(
                `<line x1="${x + 8}" y1="${y + 30}" x2="${x + w - 8}" y2="${y + 30}" ` +
                `stroke="${STYLE.compositeStroke}" stroke-opacity="0.55" stroke-width="1"/>`
            );
        } else {
            const detailLines = [...(meta.eventLabels || []), ...(meta.actionLabels || [])];
            if (detailLines.length === 0) {
                out.push(
                    `<text x="${x + w / 2}" y="${y + h / 2 + 5}" fill="${STYLE.stateTitleColor}" ` +
                    `font-weight="600" text-anchor="middle">${escapeXml(labelText)}</text>`
                );
            } else {
                const titleY = y + 22;
                out.push(
                    `<text x="${x + w / 2}" y="${titleY}" fill="${STYLE.stateTitleColor}" ` +
                    `font-weight="700" text-anchor="middle">${escapeXml(labelText)}</text>`
                );
                out.push(
                    `<line x1="${x + 8}" y1="${titleY + 6}" x2="${x + w - 8}" y2="${titleY + 6}" ` +
                    `stroke="${STYLE.stateStroke}" stroke-opacity="0.4" stroke-width="1"/>`
                );
                let lineY = titleY + 22;
                for (const line of detailLines) {
                    out.push(
                        `<text x="${x + 12}" y="${lineY}" fill="${STYLE.stateTitleColor}" ` +
                        `font-size="12" font-weight="400">${escapeXml(line)}</text>`
                    );
                    lineY += 16;
                }
            }
        }

        // Collapse/expand chevron for composite states
        if (isComposite) {
            const chevronX = x + w - 22;
            const chevronY = y + 14;
            const collapsed = Boolean(meta.collapsed);
            const path = collapsed
                ? `M${chevronX},${chevronY} l4,4 l4,-4`
                : `M${chevronX},${chevronY + 2} l4,-4 l4,4`;
            out.push(
                `<path d="${path}" fill="none" stroke="${STYLE.stateTitleColor}" ` +
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

    for (const label of edge.labels || []) {
        const lx = (label.x || 0) + ox;
        const ly = (label.y || 0) + oy;
        const lw = label.width || 0;
        const lh = label.height || 0;
        out.push(
            `<g ${quote('data-fcstm-kind', 'transition-label')} ` +
            `${quote('data-fcstm-id', meta?.transitionId || edge.id)} ` +
            `${rangeAttrs('fcstm-range', meta?.sourceRange)}>`
        );
        out.push(
            `<rect x="${lx - 4}" y="${ly - 2}" width="${lw + 8}" height="${lh + 4}" ` +
            `rx="5" ry="5" fill="${STYLE.edgeLabelBg}" stroke="${STYLE.edgeLabelBorder}" stroke-width="0.8"/>`
        );
        // Multi-line labels are split by literal newline and rendered as
        // separate tspan blocks.
        const lines = String(label.text).split('\n');
        const lineOffset = lh / Math.max(1, lines.length);
        for (const [i, line] of lines.entries()) {
            out.push(
                `<text x="${lx + 4}" y="${ly + lineOffset * (i + 0.7) + 2}" ` +
                `fill="${color}" font-size="12">${escapeXml(line)}</text>`
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
        '</defs>',
    ].join('');
}

export const __svgRendererInternals = { STYLE, escapeXml, rangeAttrs };

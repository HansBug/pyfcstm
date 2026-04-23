/**
 * Detect orthogonal edge crossings in a laid-out graph so the renderer
 * can draw drawio / Visio style "bridge" humps when two edges have to
 * cross. The rule is deterministic: a vertical segment hops over every
 * horizontal segment from a different edge that it crosses. Horizontal
 * segments stay straight. This keeps exactly one side responsible for
 * the hop so two crossing edges produce one visible arc, not two.
 */
import type {PreviewElkEdge, PreviewElkNode} from '../types';

export interface ResolvedSegment {
    edgeId: string;
    sectionIdx: number;
    segmentIdx: number;
    orientation: 'h' | 'v';
    x1: number;
    y1: number;
    x2: number;
    y2: number;
}

export type CrossingIndex = Map<string, number[]>;

function segmentKey(edgeId: string, sectionIdx: number, segmentIdx: number): string {
    return `${edgeId}::${sectionIdx}::${segmentIdx}`;
}

function pushSegmentsForEdge(
    edge: PreviewElkEdge,
    ox: number,
    oy: number,
    out: ResolvedSegment[]
): void {
    const edgeId = edge.id;
    (edge.sections || []).forEach((section, sectionIdx) => {
        const pts: Array<{x: number; y: number}> = [
            {x: section.startPoint.x + ox, y: section.startPoint.y + oy},
            ...(section.bendPoints || []).map(p => ({x: p.x + ox, y: p.y + oy})),
            {x: section.endPoint.x + ox, y: section.endPoint.y + oy},
        ];
        for (let i = 0; i + 1 < pts.length; i++) {
            const a = pts[i];
            const b = pts[i + 1];
            if (Math.abs(a.x - b.x) < 0.5 && Math.abs(a.y - b.y) < 0.5) continue;
            const orientation: 'h' | 'v' = Math.abs(a.y - b.y) < Math.abs(a.x - b.x) ? 'h' : 'v';
            out.push({
                edgeId,
                sectionIdx,
                segmentIdx: i,
                orientation,
                x1: a.x,
                y1: a.y,
                x2: b.x,
                y2: b.y,
            });
        }
    });
}

/**
 * Walk the laid-out tree recursively and emit every edge segment in
 * canvas (absolute) coordinates.
 */
export function collectSegments(
    node: PreviewElkNode,
    ox: number = 0,
    oy: number = 0
): ResolvedSegment[] {
    const out: ResolvedSegment[] = [];
    walk(node, ox, oy, out);
    return out;
}

function walk(node: PreviewElkNode, ox: number, oy: number, out: ResolvedSegment[]): void {
    const x = (node.x || 0) + ox;
    const y = (node.y || 0) + oy;
    const meta = node.fcstm;
    const skip = meta && meta.collapsed;
    if (!skip) {
        for (const child of node.children || []) {
            walk(child, x, y, out);
        }
        for (const edge of node.edges || []) {
            pushSegmentsForEdge(edge, x, y, out);
        }
    }
}

/**
 * Build a ``CrossingIndex`` that maps each vertical segment's key to
 * the y-coordinates where it should emit a bridge hump. A crossing is
 * counted only when the two segments come from different edges and the
 * intersection is strictly interior to both (touching at an endpoint
 * does not count — that is the normal "edge meets node" case).
 */
export function buildCrossingIndex(segments: ResolvedSegment[]): CrossingIndex {
    const horizontals: ResolvedSegment[] = [];
    const verticals: ResolvedSegment[] = [];
    for (const s of segments) {
        if (s.orientation === 'h') horizontals.push(s);
        else verticals.push(s);
    }
    const index: CrossingIndex = new Map();
    const EPS = 0.5;

    for (const v of verticals) {
        const vx = v.x1;
        const vyMin = Math.min(v.y1, v.y2);
        const vyMax = Math.max(v.y1, v.y2);
        const crossings: number[] = [];
        for (const h of horizontals) {
            if (h.edgeId === v.edgeId) continue;
            const hy = h.y1;
            const hxMin = Math.min(h.x1, h.x2);
            const hxMax = Math.max(h.x1, h.x2);
            // Strict interior intersection on both segments, with an
            // epsilon guard so two edges landing on the same node port
            // do not record a false positive.
            if (vx <= hxMin + EPS || vx >= hxMax - EPS) continue;
            if (hy <= vyMin + EPS || hy >= vyMax - EPS) continue;
            crossings.push(hy);
        }
        if (crossings.length === 0) continue;
        crossings.sort((a, b) => a - b);
        index.set(segmentKey(v.edgeId, v.sectionIdx, v.segmentIdx), crossings);
    }

    return index;
}

export function crossingsFor(
    index: CrossingIndex,
    edgeId: string,
    sectionIdx: number,
    segmentIdx: number
): number[] | undefined {
    return index.get(segmentKey(edgeId, sectionIdx, segmentIdx));
}

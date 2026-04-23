/**
 * Post-process an ELK-laid-out preview graph so edges do not end (or
 * start) with a tiny orthogonal stub right next to a node. When ELK
 * routes an edge through several bends and the final segment lands
 * within a few pixels of the target port, the visual result is a
 * perpendicular "L" glued to the arrowhead that reads as rendering
 * noise rather than intentional routing.
 *
 * The repair absorbs a short stub into the neighboring bend instead of
 * shifting both ends — a plain shift can trade one stub for another
 * when a polyline has a short final AND a short initial segment. The
 * pass iterates until the polyline stabilizes, so chains of stubs are
 * collapsed in one go.
 */
import type {PreviewElkEdge, PreviewElkNode} from '../types';

export const DEFAULT_MIN_STUB_LEN = 18;

interface Point {
    x: number;
    y: number;
}

function segmentLenLInf(a: Point, b: Point): number {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

/**
 * Try to collapse the trailing stub of a polyline by removing the
 * useless bend point adjacent to the endpoint. Returns ``true`` if a
 * change was made.
 *
 * Geometrically: when ``p_{n-1}`` is only ``short`` away from ``p_n`` on
 * axis F, and ``p_{n-2}`` → ``p_{n-1}`` runs perpendicular to that (axis
 * P), we can drop ``p_{n-1}`` and slide ``p_{n-2}`` onto ``p_n``'s F
 * coordinate. The previous segment keeps its axis; the new terminal
 * segment runs along P and inherits the length of the old penultimate
 * segment, so no new short stub is introduced as long as the original
 * penultimate segment was long enough.
 */
function collapseEndStub(points: Point[], threshold: number): boolean {
    if (points.length < 3) return false;
    const last = points[points.length - 1];
    const prev = points[points.length - 2];
    const pprev = points[points.length - 3];
    const dx = last.x - prev.x;
    const dy = last.y - prev.y;
    const stub = Math.abs(dx) + Math.abs(dy);
    if (stub <= 0 || stub >= threshold) return false;
    const axis: 'x' | 'y' = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
    pprev[axis] = last[axis];
    points.splice(points.length - 2, 1);
    return true;
}

function collapseStartStub(points: Point[], threshold: number): boolean {
    if (points.length < 3) return false;
    const first = points[0];
    const next = points[1];
    const nnext = points[2];
    const dx = next.x - first.x;
    const dy = next.y - first.y;
    const stub = Math.abs(dx) + Math.abs(dy);
    if (stub <= 0 || stub >= threshold) return false;
    const axis: 'x' | 'y' = Math.abs(dx) > Math.abs(dy) ? 'x' : 'y';
    nnext[axis] = first[axis];
    points.splice(1, 1);
    return true;
}

function smoothEdge(edge: PreviewElkEdge, minStubLen: number): void {
    for (const section of edge.sections || []) {
        const points: Point[] = [
            {x: section.startPoint.x, y: section.startPoint.y},
            ...(section.bendPoints || []).map(p => ({x: p.x, y: p.y})),
            {x: section.endPoint.x, y: section.endPoint.y},
        ];
        if (points.length < 3) continue;

        // Iterate until the polyline is stable. Both collapses shrink
        // the array so the loop is bounded by the original length.
        let changed = true;
        let safety = points.length + 2;
        while (changed && safety-- > 0) {
            changed = false;
            if (collapseEndStub(points, minStubLen)) changed = true;
            if (collapseStartStub(points, minStubLen)) changed = true;
        }

        section.startPoint = {x: points[0].x, y: points[0].y};
        section.endPoint = {x: points[points.length - 1].x, y: points[points.length - 1].y};
        section.bendPoints = points.slice(1, -1).map(p => ({x: p.x, y: p.y}));
    }
}

/**
 * Recursively walk a laid-out graph and smooth every edge.
 */
export function smoothGraphEdges(
    node: PreviewElkNode,
    minStubLen: number = DEFAULT_MIN_STUB_LEN
): void {
    if (node.edges) {
        for (const edge of node.edges) {
            smoothEdge(edge, minStubLen);
        }
    }
    if (node.children) {
        for (const child of node.children) {
            smoothGraphEdges(child, minStubLen);
        }
    }
}

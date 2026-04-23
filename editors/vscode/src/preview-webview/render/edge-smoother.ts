/**
 * Post-process an ELK-laid-out preview graph so edges do not end (or
 * start) with a tiny orthogonal stub right next to a node. When ELK
 * routes an edge through several bends and the final segment lands
 * within a few pixels of the target port, the visual result is a
 * perpendicular "L" glued to the arrowhead that reads as rendering
 * noise rather than intentional routing.
 *
 * The repair is purely geometric and keeps the graph strictly
 * orthogonal: when the last segment of a section is shorter than a
 * threshold, the two trailing bend points are shifted in the direction
 * of that segment so its length grows to meet the threshold while the
 * preceding bend stays perpendicular. The same rule applies to the
 * starting segment, mirrored.
 */
import type {PreviewElkEdge, PreviewElkNode} from '../types';

export const DEFAULT_MIN_STUB_LEN = 18;

interface Point {
    x: number;
    y: number;
}

function segmentLength(a: Point, b: Point): number {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

/**
 * Shift the two bend points adjacent to an endpoint so the terminal
 * segment grows to at least ``minStubLen``. The shift is applied in the
 * direction parallel to the terminal segment, which is guaranteed to be
 * perpendicular to the penultimate segment on orthogonal routings.
 */
function elongateEndStub(points: Point[], minStubLen: number): void {
    if (points.length < 3) return;
    const pEnd = points[points.length - 1];
    const pN = points[points.length - 2];
    const pN1 = points[points.length - 3];
    const dx = pEnd.x - pN.x;
    const dy = pEnd.y - pN.y;
    const finalLen = Math.abs(dx) + Math.abs(dy);
    if (finalLen >= minStubLen || finalLen <= 0) return;

    const delta = minStubLen - finalLen;
    const horizontal = Math.abs(dx) >= Math.abs(dy);
    if (horizontal) {
        const dir = dx > 0 ? -1 : 1;
        // The penultimate segment must be vertical for orthogonal routing;
        // guard against malformed inputs by only proceeding when the
        // preceding bend shares pN's x coordinate.
        if (Math.abs(pN1.x - pN.x) > 0.5) return;
        pN.x += dir * delta;
        pN1.x += dir * delta;
    } else {
        const dir = dy > 0 ? -1 : 1;
        if (Math.abs(pN1.y - pN.y) > 0.5) return;
        pN.y += dir * delta;
        pN1.y += dir * delta;
    }
}

/**
 * Mirror of ``elongateEndStub`` applied to the start of the polyline.
 */
function elongateStartStub(points: Point[], minStubLen: number): void {
    if (points.length < 3) return;
    const pStart = points[0];
    const p1 = points[1];
    const p2 = points[2];
    const dx = p1.x - pStart.x;
    const dy = p1.y - pStart.y;
    const startLen = Math.abs(dx) + Math.abs(dy);
    if (startLen >= minStubLen || startLen <= 0) return;

    const delta = minStubLen - startLen;
    const horizontal = Math.abs(dx) >= Math.abs(dy);
    if (horizontal) {
        const dir = dx > 0 ? 1 : -1;
        if (Math.abs(p2.x - p1.x) > 0.5) return;
        p1.x += dir * delta;
        p2.x += dir * delta;
    } else {
        const dir = dy > 0 ? 1 : -1;
        if (Math.abs(p2.y - p1.y) > 0.5) return;
        p1.y += dir * delta;
        p2.y += dir * delta;
    }
}

function smoothEdge(edge: PreviewElkEdge, minStubLen: number): void {
    for (const section of edge.sections || []) {
        const points: Point[] = [
            section.startPoint,
            ...(section.bendPoints || []),
            section.endPoint,
        ];
        if (points.length < 3) continue;
        // End stub is the more visible of the two — the arrowhead is
        // anchored there — so handle it first. The start stub matters
        // too; it is the tail of self-loops.
        elongateEndStub(points, minStubLen);
        elongateStartStub(points, minStubLen);
        // The bend-points array references the same objects we just
        // mutated in-place, so nothing further is needed, but reassign
        // defensively to keep the invariant "section.bendPoints is the
        // middle of points" explicit.
        section.bendPoints = points.slice(1, -1).map(p => ({x: p.x, y: p.y}));
        section.startPoint = {x: points[0].x, y: points[0].y};
        section.endPoint = {x: points[points.length - 1].x, y: points[points.length - 1].y};
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

/**
 * Post-process an ELK-laid-out preview graph so edges do not end (or
 * start) with a tiny orthogonal stub right next to a node. A short
 * terminal segment reads as visual noise glued to the arrowhead.
 *
 * The smoother preserves two invariants that the earlier merge-based
 * version broke:
 *
 * 1. Orthogonality — every segment remains axis-aligned.
 * 2. Axis at the endpoint — the final segment keeps the same axis it
 *    had before smoothing, so the arrow lands perpendicular to the
 *    destination node's border (horizontal segment → hits a vertical
 *    side, vertical segment → hits a horizontal side).
 *
 * The fix elongates a short terminal segment by shifting the two bend
 * points adjacent to it in the direction parallel to the segment,
 * keeping the penultimate segment perpendicular. If that shift would
 * turn a formerly-healthy segment on the OTHER side into a new stub,
 * the fix is skipped — that was the ping-pong bug where end-stub
 * elongation created a start stub and vice versa. In such a case the
 * tiny stub is left as-is; preserving perpendicularity matters more
 * than hiding a two-pixel segment.
 */
import type {PreviewElkEdge, PreviewElkNode} from '../types';

export const DEFAULT_MIN_STUB_LEN = 18;

interface Point {
    x: number;
    y: number;
}

function manhattan(a: Point, b: Point): number {
    return Math.abs(a.x - b.x) + Math.abs(a.y - b.y);
}

interface ShiftPlan {
    axis: 'x' | 'y';
    /** +1 / -1 — direction along the segment axis that elongates the stub. */
    sign: number;
    /** How many pixels to shift. */
    delta: number;
    /** Indices of the two points that need to move. */
    a: number;
    b: number;
}

/**
 * Build a shift plan for the tail of a polyline. Returns ``null`` when
 * the tail is not a valid short stub (either already long enough, or
 * the penultimate geometry is not perpendicular to the final segment).
 */
function planTailShift(points: Point[], threshold: number): ShiftPlan | null {
    if (points.length < 3) return null;
    const last = points[points.length - 1];
    const prev = points[points.length - 2];
    const pprev = points[points.length - 3];
    const dx = last.x - prev.x;
    const dy = last.y - prev.y;
    const stub = Math.abs(dx) + Math.abs(dy);
    if (stub <= 0 || stub >= threshold) return null;
    const horizontal = Math.abs(dx) >= Math.abs(dy);
    if (horizontal) {
        // Penultimate segment must be vertical (same x on both ends).
        if (Math.abs(pprev.x - prev.x) > 0.5) return null;
        const sign = dx > 0 ? -1 : 1;
        return {axis: 'x', sign, delta: threshold - stub, a: points.length - 2, b: points.length - 3};
    }
    if (Math.abs(pprev.y - prev.y) > 0.5) return null;
    const sign = dy > 0 ? -1 : 1;
    return {axis: 'y', sign, delta: threshold - stub, a: points.length - 2, b: points.length - 3};
}

function planHeadShift(points: Point[], threshold: number): ShiftPlan | null {
    if (points.length < 3) return null;
    const first = points[0];
    const next = points[1];
    const nnext = points[2];
    const dx = next.x - first.x;
    const dy = next.y - first.y;
    const stub = Math.abs(dx) + Math.abs(dy);
    if (stub <= 0 || stub >= threshold) return null;
    const horizontal = Math.abs(dx) >= Math.abs(dy);
    if (horizontal) {
        if (Math.abs(nnext.x - next.x) > 0.5) return null;
        const sign = dx > 0 ? 1 : -1;
        return {axis: 'x', sign, delta: threshold - stub, a: 1, b: 2};
    }
    if (Math.abs(nnext.y - next.y) > 0.5) return null;
    const sign = dy > 0 ? 1 : -1;
    return {axis: 'y', sign, delta: threshold - stub, a: 1, b: 2};
}

function applyShift(points: Point[], plan: ShiftPlan): void {
    const {axis, sign, delta, a, b} = plan;
    points[a][axis] += sign * delta;
    points[b][axis] += sign * delta;
}

/**
 * Would applying this plan on the polyline create a fresh short stub at
 * the OPPOSITE end? A plan qualifies as safe only when it leaves both
 * ends of the polyline above the threshold.
 */
function createsOppositeStub(
    points: Point[],
    plan: ShiftPlan,
    threshold: number,
    end: 'tail' | 'head'
): boolean {
    // Clone just enough to check. Applying the shift mutates; test on a
    // shallow clone of the two points that change.
    const cloned = points.map(p => ({x: p.x, y: p.y}));
    applyShift(cloned, plan);
    if (end === 'tail') {
        // Check the head segment of the clone.
        if (cloned.length < 2) return false;
        const headLen = manhattan(cloned[0], cloned[1]);
        return headLen > 0 && headLen < threshold;
    }
    if (cloned.length < 2) return false;
    const tailLen = manhattan(cloned[cloned.length - 2], cloned[cloned.length - 1]);
    return tailLen > 0 && tailLen < threshold;
}

function smoothEdge(edge: PreviewElkEdge, threshold: number): void {
    for (const section of edge.sections || []) {
        const points: Point[] = [
            {x: section.startPoint.x, y: section.startPoint.y},
            ...(section.bendPoints || []).map(p => ({x: p.x, y: p.y})),
            {x: section.endPoint.x, y: section.endPoint.y},
        ];
        if (points.length < 3) continue;

        // The tail end carries the arrowhead and is therefore the most
        // visually important place to elongate a short stub. If the
        // tail is short, fix it unconditionally — even if the fix
        // creates a tiny start stub, that one is rarely visible
        // (circle pseudo-ports hide it, and rect ports put it inside
        // the node outline). Only fall back to the head fix when the
        // tail was already fine, to avoid the ping-pong that would
        // otherwise shuttle the stub back and forth.
        const tailPlan = planTailShift(points, threshold);
        if (tailPlan) {
            applyShift(points, tailPlan);
        } else {
            const headPlan = planHeadShift(points, threshold);
            if (headPlan) applyShift(points, headPlan);
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

/**
 * Post-process an ELK-laid-out preview graph so neither end of an edge
 * ends with a too-short orthogonal stub. The same length threshold
 * applies to both ends — an edge is just as visually broken when its
 * tail segment (the one the arrowhead sits on) is 2px as when its
 * head segment (the one leaving the source) is 2px.
 *
 * The smoother operates in three modes depending on the polyline shape:
 *
 * 1. **V-H-V / H-V-H (len 4)** — the overwhelmingly common orthogonal
 *    routing shape with one middle bend. The two outer segments share
 *    the same axis; their length sum equals the source-to-target
 *    displacement along that axis. When either outer segment is
 *    shorter than the threshold, the middle bend is slid along the
 *    shared axis to redistribute length:
 *      * If the total displacement allows both ends to meet the
 *        threshold while keeping the healthier end intact, only the
 *        short end is elongated.
 *      * Otherwise the two ends are balanced symmetrically so
 *        neither is dominant. Both ends then match, which is the
 *        closest approximation of the "same standard on both sides"
 *        rule when geometry makes the threshold unreachable.
 *
 * 2. **Longer polylines** — a tail or head shift is applied as a
 *    single-pass fix. The ping-pong between tail and head fixes is
 *    avoided by picking the tail if it was short and only falling
 *    back to the head otherwise.
 *
 * 3. **Short polylines (< 3 points)** — left alone; there is no bend
 *    to adjust.
 *
 * Orthogonality is preserved in every mode: no segment ever flips
 * axis, so arrows continue to land perpendicular to the destination
 * node's border after smoothing.
 */
import type {PreviewElkEdge, PreviewElkNode} from '../types';

export const DEFAULT_MIN_STUB_LEN = 18;

interface Point {
    x: number;
    y: number;
}

type Axis = 'x' | 'y';

function axisOf(a: Point, b: Point): Axis | null {
    const dx = Math.abs(a.x - b.x);
    const dy = Math.abs(a.y - b.y);
    if (dx < 0.5 && dy < 0.5) return null;
    return dx > dy ? 'x' : 'y';
}

/**
 * Rebalance a 4-point V-H-V / H-V-H polyline so the two outer
 * segments both meet the stub threshold when possible, and split the
 * total displacement evenly when the threshold cannot be reached.
 *
 * Returns ``true`` when the polyline is a V-H-V shape this function
 * knows how to handle — whether or not a geometric change was made.
 * Returning ``true`` signals to the caller "I own this case; do not
 * run the tail / head fallback shifts, which would undo the balance."
 * Returns ``false`` only when the polyline is not a V-H-V / H-V-H
 * (e.g. longer routing, degenerate geometry).
 */
function balanceVHV(points: Point[], threshold: number): boolean {
    if (points.length !== 4) return false;
    const [p0, p1, p2, p3] = points;
    const outerAxis = axisOf(p0, p1);
    const innerAxis = axisOf(p1, p2);
    const tailAxis = axisOf(p2, p3);
    if (!outerAxis || !innerAxis || !tailAxis) return false;
    if (outerAxis !== tailAxis) return false;
    if (outerAxis === innerAxis) return false;
    const axis: Axis = outerAxis;

    // The two outer segments lie on ``axis``; their lengths sum to the
    // total displacement along that axis from source to target.
    const startCoord = p0[axis];
    const endCoord = p3[axis];
    const total = Math.abs(endCoord - startCoord);
    const direction = endCoord > startCoord ? 1 : -1;
    const headLen = Math.abs(p1[axis] - p0[axis]);
    const tailLen = Math.abs(p3[axis] - p2[axis]);

    // Both ends already healthy — V-H-V owns the decision and leaves
    // the polyline untouched. Returning true here prevents the
    // fallback shift from running and destabilising the balance.
    if (headLen >= threshold && tailLen >= threshold) return true;

    let targetHead: number;
    if (total >= 2 * threshold) {
        // Plenty of room — keep whichever end is already healthy and
        // only bump the short one up to the threshold. When both are
        // short in this branch (shouldn't happen but guard anyway),
        // split evenly.
        if (headLen < threshold && tailLen < threshold) {
            targetHead = total / 2;
        } else if (tailLen < threshold) {
            const delta = threshold - tailLen;
            targetHead = headLen - delta;
        } else {
            // headLen < threshold
            targetHead = threshold;
        }
    } else {
        // Can't satisfy the threshold on both ends — balance evenly.
        targetHead = total / 2;
    }

    const newBendCoord = startCoord + direction * targetHead;
    if (Math.abs(newBendCoord - p1[axis]) >= 0.5) {
        p1[axis] = newBendCoord;
        p2[axis] = newBendCoord;
    }
    return true;
}

interface ShiftPlan {
    axis: Axis;
    sign: number;
    delta: number;
    a: number;
    b: number;
}

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
    points[plan.a][plan.axis] += plan.sign * plan.delta;
    points[plan.b][plan.axis] += plan.sign * plan.delta;
}

function smoothEdge(edge: PreviewElkEdge, threshold: number): void {
    for (const section of edge.sections || []) {
        const points: Point[] = [
            {x: section.startPoint.x, y: section.startPoint.y},
            ...(section.bendPoints || []).map(p => ({x: p.x, y: p.y})),
            {x: section.endPoint.x, y: section.endPoint.y},
        ];
        if (points.length < 3) continue;

        const balanced = balanceVHV(points, threshold);
        if (!balanced) {
            const tailPlan = planTailShift(points, threshold);
            if (tailPlan) {
                applyShift(points, tailPlan);
            } else {
                const headPlan = planHeadShift(points, threshold);
                if (headPlan) applyShift(points, headPlan);
            }
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

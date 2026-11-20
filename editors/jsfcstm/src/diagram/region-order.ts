/**
 * Keep the sections of a region owner in declaration order.
 *
 * Regions run in the order they are written, so the picture has to show them
 * in that order. They have no edges between them, which leaves ELK free to
 * shuffle them to cut crossings, and it does: a model with regions A, B, C came
 * back as C, A, B. ELK's own ordering options either do nothing for the nested
 * layout this renderer uses or crash it, so the order is restored after layout
 * instead. Regions are connected to nothing outside themselves, so moving one
 * sideways cannot disturb an edge, and the owner keeps its size because the
 * regions keep their widths and the gaps between them.
 *
 * ELK normally puts the regions of one owner on a single row (a single column
 * for a left-to-right diagram). If it ever does not, the graph is laid out
 * again with a chain of invisible edges between consecutive regions, which
 * pins the order at the cost of a longer diagram.
 *
 * Once the order is settled the regions are tiled over the owner's body, the
 * way a PlantUML concurrent state is drawn: no region has a border of its own
 * and a dashed divider separates neighbours. :func:`tileRegionSections` does
 * that, and it is the last step of both layout paths.
 */
import {collectSegments, type ResolvedSegment} from './render/crossings';
import {smoothGraphEdges} from './render/edge-smoother';
import {regionTitleMinWidth} from './elk-graph';
import type {FcstmElkEdge, FcstmElkGraph, FcstmElkNode} from './model';

function regionChildren(node: FcstmElkNode): FcstmElkNode[] {
    return (node.children || []).filter(child => child.fcstm!.region);
}

/**
 * Reorder the region sections of every owner in a laid-out graph.
 *
 * @param laidOut Graph returned by ``elk.layout``; positions are rewritten.
 * @param horizontal Whether sibling regions share a row, which is the case for
 *   a top-to-bottom diagram.
 * @returns ``false`` when some owner's regions do not sit on one row or column,
 *   in which case that owner is left as ELK placed it.
 */
export function orderRegionSections(laidOut: FcstmElkNode, horizontal: boolean): boolean {
    let ok = true;
    const along = (n: FcstmElkNode) => (horizontal ? n.x : n.y) as number;
    const alongSize = (n: FcstmElkNode) => (horizontal ? n.width : n.height) as number;
    const across = (n: FcstmElkNode) => (horizontal ? n.y : n.x) as number;
    const acrossSize = (n: FcstmElkNode) => (horizontal ? n.height : n.width) as number;
    const visit = (node: FcstmElkNode): void => {
        const regions = regionChildren(node);
        if (regions.length > 1) {
            const lo = Math.max(...regions.map(across));
            const hi = Math.min(...regions.map(region => across(region) + acrossSize(region)));
            if (lo >= hi) {
                ok = false;
            } else {
                const slots = [...regions].sort((a, b) => along(a) - along(b));
                const gaps = slots.slice(1).map((slot, index) => along(slot) - (along(slots[index]) + alongSize(slots[index])));
                let cursor = along(slots[0]);
                // Sections start on one line: the shorter ones would otherwise
                // float in the middle of the row.
                const edge = Math.min(...regions.map(across));
                [...regions]
                    .sort((a, b) => a.fcstm!.ordinal! - b.fcstm!.ordinal!)
                    .forEach((region, index) => {
                        if (horizontal) { region.x = cursor; region.y = edge; } else { region.y = cursor; region.x = edge; }
                        cursor += alongSize(region) + (gaps[index] || 0);
                    });
            }
        }
        (node.children || []).forEach(visit);
    };
    visit(laidOut);
    return ok;
}

/**
 * Add a chain of invisible edges between consecutive regions of every owner.
 *
 * The edges only fix the order in which ELK lays the regions out; the
 * renderer skips them (``fcstm.kind === 'regionOrder'``).
 *
 * @returns The same graph, modified in place.
 */
export function pinRegionOrder<T extends FcstmElkNode>(graph: T): T {
    const visit = (node: FcstmElkNode): void => {
        const regions = regionChildren(node)
            .sort((a, b) => a.fcstm!.ordinal! - b.fcstm!.ordinal!);
        for (let index = 0; index + 1 < regions.length; index += 1) {
            const edge: FcstmElkEdge = {
                id: `${node.id}:order${index}`,
                sources: [regions[index].id],
                targets: [regions[index + 1].id],
                fcstm: {kind: 'regionOrder', transitionId: '', transitionKind: 'normal'},
            };
            node.edges!.push(edge);
        }
        (node.children || []).forEach(visit);
    };
    visit(graph);
    return graph;
}

/**
 * Height of the title bar a composite draws across the top of its body
 * (``render/svg.ts`` paints the same 32px); the tiled regions start below it.
 */
const OWNER_TITLE_BAR_HEIGHT = 32;
/** Gap kept between a divider and the content of the regions on either side. */
const DIVIDER_CONTENT_MARGIN = 8;
/**
 * Distance from an edge beyond which a divider gains nothing by moving
 * further away; among positions that clear every edge by this much the one
 * nearest the middle of the free corridor is taken.
 */
const DIVIDER_EDGE_CLEARANCE = 24;
const num = (value: number | undefined): number => value as number;

function sortedByOrdinal(regions: FcstmElkNode[]): FcstmElkNode[] {
    return [...regions].sort((a, b) => num(a.fcstm!.ordinal) - num(b.fcstm!.ordinal));
}

/** Translate what a region holds (children, edge sections and labels) by ``dx``, ``dy``. */
function shiftContent(region: FcstmElkNode, dx: number, dy: number): void {
    for (const child of region.children || []) {
        child.x = num(child.x) + dx;
        child.y = num(child.y) + dy;
    }
    const move = (point: {x: number; y: number}) => {
        point.x += dx;
        point.y += dy;
    };
    for (const edge of region.edges || []) {
        for (const section of edge.sections || []) {
            move(section.startPoint);
            move(section.endPoint);
            (section.bendPoints || []).forEach(move);
        }
        for (const label of edge.labels || []) {
            label.x = num(label.x) + dx;
            label.y = num(label.y) + dy;
        }
    }
}

/**
 * The span (in the region's own coordinates) its states, edges and edge labels
 * occupy along one axis; a region that holds nothing, such as a collapsed one,
 * counts as occupying its whole box.
 */
function contentSpan(region: FcstmElkNode, alongX: boolean): [number, number] {
    const values: number[] = [];
    const pick = (x: number, y: number) => values.push(alongX ? x : y);
    for (const child of region.children || []) {
        pick(num(child.x), num(child.y));
        pick(num(child.x) + num(child.width), num(child.y) + num(child.height));
    }
    for (const edge of region.edges || []) {
        for (const section of edge.sections || []) {
            [section.startPoint, ...(section.bendPoints || []), section.endPoint].forEach(p => pick(p.x, p.y));
        }
        for (const label of edge.labels || []) {
            pick(num(label.x), num(label.y));
            pick(num(label.x) + label.width, num(label.y) + label.height);
        }
    }
    if (values.length === 0) return [0, alongX ? num(region.width) : num(region.height)];
    return [Math.min(...values), Math.max(...values)];
}

/**
 * Choose where a divider goes inside the free corridor ``[lo, hi]``.
 *
 * ``edges`` are the coordinates, along the same axis, of every edge segment
 * that runs across the owner's body. The position that keeps the most distance
 * from all of them wins, but distance only counts up to
 * ``DIVIDER_EDGE_CLEARANCE``; positions tied on it are ranked by closeness
 * to the middle of the corridor, so a divider with nothing near it sits in the
 * middle and one next to an edge steps aside only as far as it has to.
 */
function pickDivider(lo: number, hi: number, edges: number[]): number {
    const mid = (lo + hi) / 2;
    const near = edges.filter(at => at > lo - DIVIDER_EDGE_CLEARANCE && at < hi + DIVIDER_EDGE_CLEARANCE).sort((a, b) => a - b);
    const candidates = [lo, mid, hi];
    near.forEach((at, index) => {
        candidates.push(at - DIVIDER_EDGE_CLEARANCE, at + DIVIDER_EDGE_CLEARANCE);
        if (index > 0) candidates.push((near[index - 1] + at) / 2);
    });
    const ranked = candidates
        .map(raw => {
            const at = Math.round(Math.min(hi, Math.max(lo, raw)));
            return {
                at,
                room: Math.min(DIVIDER_EDGE_CLEARANCE, ...near.map(edge => Math.abs(at - edge))),
                offCentre: Math.abs(at - mid),
            };
        })
        .sort((a, b) => (b.room - a.room) || (a.offCentre - b.offCentre));
    return ranked[0].at;
}

interface RegionOwner {
    node: FcstmElkNode;
    /** Absolute position of the owner's top-left corner. */
    x: number;
    y: number;
}

/**
 * Tile the regions of every owner over the owner's body.
 *
 * Run after the order of the regions is settled. Regions are connected to
 * nothing outside themselves, so each one can grow to fill the body without
 * touching an edge: all regions of an owner get the same extent across the
 * owner (the full body height for a row, the full width for a column) and
 * neighbours meet on a divider. A region that grows towards the origin has the
 * difference added to its content, so every state, edge and label keeps its
 * absolute position and the owner keeps its size. The renderer then draws no
 * border around such a region and a dashed divider on its ``dividerBefore``
 * side.
 *
 * Where a divider goes is not fixed: the space between the content of two
 * neighbours is empty, so it moves within that space to stay clear of the
 * vertical segments (horizontal ones for a column) of edges that run along the
 * owner's body, which would otherwise read as a continuation of the divider.
 * Edge positions are taken as the renderer will draw them, after
 * :func:`smoothGraphEdges`.
 *
 * Regions sit in a row when they are in order along x without overlapping,
 * which is what the top-to-bottom layout gives, and in a column otherwise,
 * which is what the left-to-right layout and the pinned layout give.
 *
 * @param laidOut Graph returned by ``elk.layout`` with the regions in order;
 *   positions and sizes of regions are rewritten, a graph without regions is
 *   left untouched.
 */
export function tileRegionSections(laidOut: FcstmElkNode): void {
    const owners: RegionOwner[] = [];
    const find = (node: FcstmElkNode, x: number, y: number): void => {
        if (regionChildren(node).length > 0) owners.push({node, x, y});
        for (const child of node.children || []) find(child, x + num(child.x), y + num(child.y));
    };
    find(laidOut, 0, 0);
    if (owners.length === 0) return;

    // Edges are looked up on a smoothed copy: the smoother runs after layout
    // and nudges stubs, and the divider has to clear the edges as drawn.
    const settled = JSON.parse(JSON.stringify(laidOut)) as FcstmElkNode;
    smoothGraphEdges(settled);
    const segments: ResolvedSegment[] = collectSegments(settled);

    for (const {node, x: ox, y: oy} of owners) {
        const regions = sortedByOrdinal(regionChildren(node));
        const width = num(node.width);
        const height = num(node.height);
        const row = regions.every((region, index) =>
            index === 0 || num(region.x) >= num(regions[index - 1].x) + num(regions[index - 1].width));
        // Only segments that run across the body (parallel to a divider) can
        // be mistaken for one: vertical ones beside a row, horizontal ones
        // beside a column, within the owner's extent along the divider.
        const crossing = segments
            .filter(segment => segment.orientation === (row ? 'v' : 'h'))
            .filter(segment => {
                const [from, to] = row ? [segment.y1, segment.y2] : [segment.x1, segment.x2];
                const [start, end] = row ? [oy, oy + height] : [ox, ox + width];
                return Math.max(from, to) >= start && Math.min(from, to) <= end;
            })
            .map(segment => (row ? segment.x1 - ox : segment.y1 - oy));

        const cuts: number[] = [];
        regions.slice(1).forEach((next, index) => {
            const prev = regions[index];
            const [, prevEnd] = contentSpan(prev, row);
            const [nextStart] = contentSpan(next, row);
            const prevOrigin = num(row ? prev.x : prev.y);
            const nextOrigin = num(row ? next.x : next.y);
            let lo = prevOrigin + prevEnd + DIVIDER_CONTENT_MARGIN;
            if (row) {
                // The region before the divider starts at the previous divider
                // (or the owner's edge) and has to hold its own title and
                // collapse button; its box was made wide enough for them.
                const tileStart = index === 0 ? 0 : cuts[index - 1];
                lo = Math.max(lo, tileStart + regionTitleMinWidth(prev.labels![0].width));
            }
            let hi = Math.max(lo, nextOrigin + nextStart - DIVIDER_CONTENT_MARGIN);
            if (!row) {
                // The title of the region after the divider sits just below it.
                hi = Math.max(lo, hi - OWNER_TITLE_BAR_HEIGHT);
            }
            cuts.push(pickDivider(lo, hi, crossing));
        });

        regions.forEach((region, index) => {
            const oldX = num(region.x);
            const oldY = num(region.y);
            const first = index === 0;
            const last = index === regions.length - 1;
            if (row) {
                region.x = first ? 0 : cuts[index - 1];
                region.width = (last ? width : cuts[index]) - region.x;
                region.y = OWNER_TITLE_BAR_HEIGHT;
                region.height = height - OWNER_TITLE_BAR_HEIGHT;
            } else {
                region.y = first ? OWNER_TITLE_BAR_HEIGHT : cuts[index - 1];
                region.height = (last ? height : cuts[index]) - region.y;
                region.x = 0;
                region.width = width;
            }
            // Children and edges are relative to the region: keep them where they were.
            shiftContent(region, oldX - num(region.x), oldY - num(region.y));
            region.fcstm!.dividerBefore = first ? undefined : (row ? 'vertical' : 'horizontal');
        });
    }
}

/** The part of elkjs this module needs. */
export interface FcstmElkLayoutEngine {
    layout(graph: FcstmElkNode): Promise<FcstmElkNode>;
}

/**
 * Lay out a diagram graph, keep its regions in declaration order and tile
 * them over their owner (:func:`tileRegionSections`).
 *
 * Use this instead of calling ``elk.layout`` directly. A graph without regions
 * is laid out exactly as before.
 *
 * @param elk An elkjs instance.
 * @param graph Graph from :func:`buildFcstmElkGraph`; it is not modified.
 */
export async function layoutFcstmGraph(
    elk: FcstmElkLayoutEngine,
    graph: FcstmElkGraph,
): Promise<FcstmElkNode> {
    const copy = () => JSON.parse(JSON.stringify(graph)) as FcstmElkGraph;
    const laidOut = await elk.layout(copy());
    const horizontal = graph.layoutOptions['elk.direction'] !== 'RIGHT';
    if (orderRegionSections(laidOut, horizontal)) {
        tileRegionSections(laidOut);
        return laidOut;
    }
    const pinned = await elk.layout(pinRegionOrder(copy()));
    tileRegionSections(pinned);
    return pinned;
}

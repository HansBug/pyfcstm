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
 */
import type {FcstmElkEdge, FcstmElkGraph, FcstmElkNode} from './model';

function regionChildren(node: FcstmElkNode): FcstmElkNode[] {
    return (node.children || []).filter(child => child.fcstm?.region);
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
    const along = (n: FcstmElkNode) => (horizontal ? n.x : n.y) || 0;
    const alongSize = (n: FcstmElkNode) => (horizontal ? n.width : n.height) || 0;
    const across = (n: FcstmElkNode) => (horizontal ? n.y : n.x) || 0;
    const acrossSize = (n: FcstmElkNode) => (horizontal ? n.height : n.width) || 0;
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
                    .sort((a, b) => (a.fcstm?.ordinal || 0) - (b.fcstm?.ordinal || 0))
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
            .sort((a, b) => (a.fcstm?.ordinal || 0) - (b.fcstm?.ordinal || 0));
        for (let index = 0; index + 1 < regions.length; index += 1) {
            const edge: FcstmElkEdge = {
                id: `${node.id}:order${index}`,
                sources: [regions[index].id],
                targets: [regions[index + 1].id],
                fcstm: {kind: 'regionOrder', transitionId: '', transitionKind: 'normal'},
            };
            (node.edges = node.edges || []).push(edge);
        }
        (node.children || []).forEach(visit);
    };
    visit(graph);
    return graph;
}

/** The part of elkjs this module needs. */
export interface FcstmElkLayoutEngine {
    layout(graph: FcstmElkNode): Promise<FcstmElkNode>;
}

/**
 * Lay out a diagram graph and keep its regions in declaration order.
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
    if (orderRegionSections(laidOut, horizontal)) return laidOut;
    return elk.layout(pinRegionOrder(copy()));
}

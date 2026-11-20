/**
 * Geometry helpers shared by the region layout tests: where a node really is
 * on the canvas, which regions an owner has, and whether they tile the owner.
 */
import assert from 'node:assert/strict';

import ELK from 'elkjs/lib/elk.bundled.js';

import {
    buildFcstmDiagramFromDocument,
    buildFcstmElkGraph,
    layoutFcstmGraph,
    resolveFcstmDiagramPreviewOptions,
    smoothGraphEdges,
} from '@pyfcstm/jsfcstm/diagram';
import type {FcstmElkNode} from '../src/diagram/model';
import {createDocument} from './support';

/** Title bar the owner draws above the regions. */
export const TITLE_BAR = 32;

export interface Box {
    x: number;
    y: number;
    width: number;
    height: number;
}

export function findNode(root: FcstmElkNode, id: string): FcstmElkNode | undefined {
    if (root.id === id) return root;
    for (const child of root.children || []) {
        const hit = findNode(child, id);
        if (hit) return hit;
    }
    return undefined;
}

export function regionsOf(owner: FcstmElkNode): FcstmElkNode[] {
    return (owner.children || [])
        .filter(child => child.fcstm?.region)
        .sort((a, b) => (a.fcstm?.ordinal as number) - (b.fcstm?.ordinal as number));
}

/** Every node that owns regions, with its absolute box. */
export function regionOwners(root: FcstmElkNode): Array<{owner: FcstmElkNode; box: Box}> {
    const found: Array<{owner: FcstmElkNode; box: Box}> = [];
    const visit = (node: FcstmElkNode, ox: number, oy: number): void => {
        const x = ox + (node.x || 0);
        const y = oy + (node.y || 0);
        if (regionsOf(node).length > 0) {
            found.push({owner: node, box: {x, y, width: node.width as number, height: node.height as number}});
        }
        for (const child of node.children || []) visit(child, x, y);
    };
    visit(root, 0, 0);
    return found;
}

/**
 * Where everything that is not a region sits on the canvas: node boxes, and
 * the points and labels of every edge. Regions are left out because tiling is
 * allowed to move and resize them; what they hold must not move.
 */
export function contentGeometry(root: FcstmElkNode): Map<string, number[]> {
    const geometry = new Map<string, number[]>();
    const visit = (node: FcstmElkNode, ox: number, oy: number): void => {
        const x = ox + (node.x || 0);
        const y = oy + (node.y || 0);
        if (node.fcstm?.kind !== 'canvas' && !node.fcstm?.region) {
            geometry.set(`node ${node.id}`, [x, y, node.width as number, node.height as number]);
        }
        for (const edge of node.edges || []) {
            const numbers: number[] = [];
            for (const section of edge.sections || []) {
                [section.startPoint, ...(section.bendPoints || []), section.endPoint]
                    .forEach(point => numbers.push(point.x + x, point.y + y));
            }
            for (const label of edge.labels || []) numbers.push((label.x as number) + x, (label.y as number) + y);
            geometry.set(`edge ${edge.id}`, numbers);
        }
        for (const child of node.children || []) visit(child, x, y);
    };
    visit(root, 0, 0);
    return geometry;
}

/**
 * Assert that the regions of an owner tile its body: same extent across, each
 * starting where the previous one ends, the first against the title bar (or
 * the owner's left edge) and the last against the far edge, and one divider
 * flag per boundary on the side that faces the previous region.
 */
export function assertTiled(owner: FcstmElkNode, arrangement: 'row' | 'column'): void {
    const regions = regionsOf(owner);
    const width = owner.width as number;
    const height = owner.height as number;
    assert.ok(regions.length > 0, `${owner.id} has regions`);
    regions.forEach((region, index) => {
        const x = region.x as number;
        const y = region.y as number;
        const w = region.width as number;
        const h = region.height as number;
        if (arrangement === 'row') {
            assert.equal(y, TITLE_BAR, `${region.id} starts under the title bar`);
            assert.equal(h, height - TITLE_BAR, `${region.id} reaches the bottom`);
            if (index === 0) assert.equal(x, 0);
            if (index > 0) {
                const previous = regions[index - 1];
                assert.equal(x, (previous.x as number) + (previous.width as number), `${region.id} abuts ${previous.id}`);
            }
            if (index === regions.length - 1) assert.equal(x + w, width);
        } else {
            assert.equal(x, 0, `${region.id} starts at the left edge`);
            assert.equal(w, width, `${region.id} spans the owner`);
            if (index === 0) assert.equal(y, TITLE_BAR);
            if (index > 0) {
                const previous = regions[index - 1];
                assert.equal(y, (previous.y as number) + (previous.height as number), `${region.id} abuts ${previous.id}`);
            }
            if (index === regions.length - 1) assert.equal(y + h, height);
        }
        // A divider sits on a whole pixel so that its dashes are drawn crisp.
        if (index > 0) assert.ok(Number.isInteger(arrangement === 'row' ? x : y), `${region.id} divider at ${arrangement === 'row' ? x : y}`);
        assert.equal(
            region.fcstm?.dividerBefore,
            index === 0 ? undefined : (arrangement === 'row' ? 'vertical' : 'horizontal'),
            `${region.id} divider`,
        );
    });
}

/** Build, lay out with the public entry point and smooth the way the viewers do. */
export async function layoutSource(
    source: string,
    direction: 'TB' | 'LR',
    collapsed: string[] = [],
) {
    const diagram = await buildFcstmDiagramFromDocument(createDocument(source, '/tmp/region-layout.fcstm'));
    assert.ok(diagram);
    const options = resolveFcstmDiagramPreviewOptions({direction} as never);
    const graph = buildFcstmElkGraph(diagram!, options, {collapsedStateIds: new Set(collapsed)});
    const laid = await layoutFcstmGraph(new ELK(), graph);
    smoothGraphEdges(laid);
    return {laid, options, graph};
}

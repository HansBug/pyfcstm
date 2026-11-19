import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as path from 'node:path';

import ELK from 'elkjs/lib/elk.bundled.js';

import {
    buildFcstmDiagramFromDocument,
    buildFcstmElkGraph,
    collectSegments,
    layoutFcstmGraph,
    orderRegionSections,
    renderFcstmDiagramSvg,
    resolveFcstmDiagramPreviewOptions,
    smoothGraphEdges,
    tileRegionSections,
} from '@pyfcstm/jsfcstm/diagram';
import type {FcstmElkNode} from '../src/diagram/model';
import {
    Box,
    assertTiled,
    contentGeometry,
    layoutSource,
    regionOwners,
    regionsOf,
} from './region-geometry';
import {ELEVATOR_SOURCE, JOB_SOURCE, NESTED_SOURCE, PLAIN_SOURCE, REGION_SOURCES} from './region-sources';
import {createDocument} from './support';

const DIRECTIONS = ['TB', 'LR'] as const;
type Direction = typeof DIRECTIONS[number];

const round = (value: number) => Math.round(value * 1e6) / 1e6;

/** What the old layout produced: regions ordered but not yet tiled. */
async function orderedOnly(source: string, direction: Direction): Promise<FcstmElkNode> {
    const diagram = await buildFcstmDiagramFromDocument(createDocument(source, '/tmp/region-divider.fcstm'));
    assert.ok(diagram);
    const options = resolveFcstmDiagramPreviewOptions({direction} as never);
    const graph = buildFcstmElkGraph(diagram!, options);
    const laid = await new ELK().layout(JSON.parse(JSON.stringify(graph)));
    assert.equal(orderRegionSections(laid, direction === 'TB'), true);
    return laid;
}

/** The span of a region's content along ``x`` (``alongX``) or ``y``, in its own coordinates. */
function contentRange(region: FcstmElkNode, alongX: boolean): [number, number] {
    const values: number[] = [];
    const take = (x: number, y: number) => values.push(alongX ? x : y);
    for (const child of region.children || []) {
        take(child.x as number, child.y as number);
        take((child.x as number) + (child.width as number), (child.y as number) + (child.height as number));
    }
    for (const edge of region.edges || []) {
        for (const section of edge.sections || []) {
            [section.startPoint, ...(section.bendPoints || []), section.endPoint].forEach(point => take(point.x, point.y));
        }
        for (const label of edge.labels || []) {
            take(label.x as number, label.y as number);
            take((label.x as number) + label.width, (label.y as number) + label.height);
        }
    }
    return [Math.min(...values), Math.max(...values)];
}

/** Absolute position of every divider: where it is, and how far it runs. */
function dividersOf(root: FcstmElkNode, direction: Direction): Array<{at: number; from: number; to: number}> {
    const lines: Array<{at: number; from: number; to: number}> = [];
    for (const {owner, box} of regionOwners(root)) {
        for (const region of regionsOf(owner).slice(1)) {
            const x = box.x + (region.x as number);
            const y = box.y + (region.y as number);
            lines.push(direction === 'TB'
                ? {at: x, from: y, to: y + (region.height as number)}
                : {at: y, from: x, to: x + (region.width as number)});
        }
    }
    return lines;
}

/** Every divider is 12px or more from every edge segment that runs along it. */
function assertDividersClearOfEdges(laid: FcstmElkNode, direction: Direction): void {
    const segments = collectSegments(laid).filter(segment => segment.orientation === (direction === 'TB' ? 'v' : 'h'));
    const dividers = dividersOf(laid, direction);
    assert.ok(dividers.length > 0);
    for (const line of dividers) {
        for (const segment of segments) {
            const [a, b] = direction === 'TB' ? [segment.y1, segment.y2] : [segment.x1, segment.x2];
            if (Math.max(a, b) < line.from || Math.min(a, b) > line.to) continue;
            const at = direction === 'TB' ? segment.x1 : segment.y1;
            assert.ok(Math.abs(at - line.at) >= 12, `${segment.edgeId} at ${at}, divider at ${line.at}`);
        }
    }
}

describe('regions tiled into their owner', () => {
    for (const [name, source] of REGION_SOURCES) {
        for (const direction of DIRECTIONS) {
            const arrangement = direction === 'TB' ? 'row' : 'column';

            it(`tiles ${name} without moving a state, an edge or an owner, ${direction}`, async () => {
                const laid = await orderedOnly(source, direction);
                const before = contentGeometry(laid);
                tileRegionSections(laid);
                const after = contentGeometry(laid);
                assert.deepEqual([...after.keys()], [...before.keys()]);
                for (const [key, numbers] of before) {
                    assert.deepEqual((after.get(key) as number[]).map(round), numbers.map(round), key);
                }
                const owners = regionOwners(laid);
                assert.ok(owners.length > 0);
                owners.forEach(({owner}) => assertTiled(owner, arrangement));
            });

            it(`keeps what a region holds on its own side of the dividers in ${name}, ${direction}`, async () => {
                const {laid} = await layoutSource(source, direction);
                for (const {owner} of regionOwners(laid)) {
                    const regions = regionsOf(owner);
                    regions.forEach((region, index) => {
                        const alongX = direction === 'TB';
                        const [start, end] = contentRange(region, alongX);
                        const size = (alongX ? region.width : region.height) as number;
                        // Room beside a divider; the far edges of the outer regions are the owner's border.
                        assert.ok(start >= (index > 0 ? 8 : 0) - 1e-6, `${region.id} start ${start}`);
                        assert.ok(size - end >= (index < regions.length - 1 ? 8 : 0) - 1e-6, `${region.id} end ${size - end}`);
                        if (!alongX && index > 0) {
                            // The title of a stacked region sits right under its divider.
                            assert.ok(start >= 8 + 32 - 1e-6, `${region.id} title room ${start}`);
                        }
                    });
                }
            });

            it(`keeps every divider at least 12px from the edges that run along it in ${name}, ${direction}`, async () => {
                assertDividersClearOfEdges((await layoutSource(source, direction)).laid, direction);
            });
        }
    }

    // Cases where the middle of the gap between two regions is the very spot an
    // edge of the owner runs through, so a plain tiling would draw the divider
    // on top of that edge (the first one even continues the edge it hangs from).
    const COLLISIONS: Array<[string, string, Direction, string, number]> = [
        ['nested', NESTED_SOURCE, 'TB', 'Workflow.Job.A.Q', 0],
        ['job', JOB_SOURCE, 'TB', 'Workflow.Job', 0],
        ['elevator', ELEVATOR_SOURCE, 'LR', 'Elevator.Serving', 0],
        ['elevator', ELEVATOR_SOURCE, 'LR', 'Elevator.Serving', 1],
    ];
    for (const [name, source, direction, ownerId, boundary] of COLLISIONS) {
        it(`moves a divider off an edge that would have run along it: ${name} ${direction} ${ownerId} #${boundary}`, async () => {
            const laid = await orderedOnly(source, direction);
            smoothGraphEdges(laid);
            const found = regionOwners(laid).find(item => item.owner.id === ownerId) as {owner: FcstmElkNode; box: Box};
            const regions = regionsOf(found.owner);
            const [first, second] = [regions[boundary], regions[boundary + 1]];
            const alongX = direction === 'TB';
            const gapMiddle = alongX
                ? ((first.x as number) + (first.width as number) + (second.x as number)) / 2
                : ((first.y as number) + (first.height as number) + (second.y as number)) / 2;
            const origin = alongX ? found.box.x : found.box.y;
            const near = collectSegments(laid)
                .filter(segment => segment.orientation === (alongX ? 'v' : 'h'))
                .filter(segment => {
                    const [a, b] = alongX ? [segment.y1, segment.y2] : [segment.x1, segment.x2];
                    const [from, to] = alongX
                        ? [found.box.y, found.box.y + found.box.height]
                        : [found.box.x, found.box.x + found.box.width];
                    return Math.max(a, b) >= from && Math.min(a, b) <= to;
                })
                .map(segment => (alongX ? segment.x1 : segment.y1) - origin)
                .filter(at => Math.abs(at - gapMiddle) < 12);
            assert.ok(near.length > 0, `an edge lies within 12px of the gap middle ${gapMiddle}`);

            tileRegionSections(laid);
            const divider = (alongX ? second.x : second.y) as number;
            for (const at of near) assert.ok(Math.abs(at - divider) >= 12, `divider ${divider} against edge ${at}`);
            // It stepped aside only as far as it had to: the gap is not left for the owner's edge.
            assert.ok(Math.abs(divider - gapMiddle) < 40, `${divider} against ${gapMiddle}`);
        });
    }

    it('puts a divider in the middle of the free space when no edge is near it', async () => {
        const source = `input int x;
state Root {
    region One { [*] -> A; state A; state B; A -> B : if [x > 0]; }
    region Two { [*] -> C; state C; }
}
`;
        const {laid} = await layoutSource(source, 'TB');
        const [one, two] = regionsOf(laid.children![0]);
        const [, oneEnd] = contentRange(one, true);
        const [twoStart] = contentRange(two, true);
        const left = (two.x as number) + twoStart - ((one.x as number) + oneEnd);
        const room = left / 2;
        // Equal room on both sides of the divider, give or take the rounding to a whole pixel.
        assert.ok(Math.abs(((two.x as number) - ((one.x as number) + oneEnd)) - room) <= 1, `${room}`);
    });

    it('keeps the divider clear of the title of the region before it', async () => {
        const source = (name: string) => `state Root {
    region ${name} { [*] -> A; state A; }
    region Other { [*] -> C; state C; }
}
`;
        const short = (await layoutSource(source('A'), 'TB')).laid;
        const long = (await layoutSource(source('AVeryLongRegionNameThatIsWiderThanItsOwnContent'), 'TB')).laid;
        const dividerOf = (laid: FcstmElkNode) => regionsOf(laid.children![0])[1].x as number;
        assert.ok(dividerOf(long) > dividerOf(short), `${dividerOf(long)} against ${dividerOf(short)}`);
        // The second region still starts before its own content.
        const [, second] = regionsOf(long.children![0]);
        assert.ok(contentRange(second, true)[0] >= 0);
    });

    it('lets a single region fill its owner with no divider', async () => {
        const source = `input int x;
state Root {
    region Only { [*] -> A; state A; state B; A -> B : if [x > 0]; }
}
`;
        for (const direction of DIRECTIONS) {
            const {laid} = await layoutSource(source, direction);
            const owner = laid.children![0];
            assertTiled(owner, 'row');
            assert.equal(regionsOf(owner).length, 1);
            assert.equal(dividersOf(laid, direction).length, 0);
        }
    });

    for (const direction of DIRECTIONS) {
        it(`tiles an owner with a collapsed region and leaves a collapsed owner alone, ${direction}`, async () => {
            const collapsed = await layoutSource(NESTED_SOURCE, direction, ['Workflow.Job.B', 'Workflow.Job.A.Q']);
            const owners = regionOwners(collapsed.laid);
            assert.deepEqual(owners.map(item => item.owner.id), ['Workflow.Job']);
            assertTiled(owners[0].owner, direction === 'TB' ? 'row' : 'column');
            const b = regionsOf(owners[0].owner)[1];
            assert.equal(b.fcstm?.collapsed, true);
            assert.equal((b.children || []).length, 0);

            const owner = await layoutSource(NESTED_SOURCE, direction, ['Workflow.Job']);
            assert.deepEqual(regionOwners(owner.laid), []);
        });
    }

    for (const direction of DIRECTIONS) {
        it(`tiles a region that has no states next to one that has, ${direction}`, async () => {
            const source = `state Root {
    region Empty { }
    region Busy { [*] -> C; state C; }
}
`;
            const {laid, options} = await layoutSource(source, direction);
            const owner = laid.children![0];
            assertTiled(owner, direction === 'TB' ? 'row' : 'column');
            const [empty] = regionsOf(owner);
            assert.equal(empty.children, undefined);
            const svg = renderFcstmDiagramSvg(laid, options);
            assert.equal((svg.match(/<rect class="fcstm-region-hit"/g) || []).length, 2);
            assert.equal((svg.match(/<g [^>]*data-fcstm-id="Root\.Empty"[^>]*data-fcstm-composite="false"/g) || []).length, 1);
        });
    }

    it('tiles the output of an engine that leaves out empty bend point lists', async () => {
        const diagram = await buildFcstmDiagramFromDocument(createDocument(NESTED_SOURCE, '/tmp/region-divider.fcstm'));
        const options = resolveFcstmDiagramPreviewOptions({direction: 'TB'} as never);
        const graph = buildFcstmElkGraph(diagram!, options);
        const elk = new ELK();
        const stripping = {
            async layout(input: FcstmElkNode) {
                const laid = await elk.layout(JSON.parse(JSON.stringify(input)));
                const strip = (node: FcstmElkNode): void => {
                    for (const edge of node.edges || []) {
                        for (const section of edge.sections || []) {
                            if (section.bendPoints && section.bendPoints.length === 0) delete section.bendPoints;
                        }
                    }
                    (node.children || []).forEach(strip);
                };
                strip(laid);
                return laid;
            },
        };
        const laid = await layoutFcstmGraph(stripping as never, graph);
        regionOwners(laid).forEach(({owner}) => assertTiled(owner, 'row'));
        // Straight edges did lose their list in this run, so the tiler really met sections without one.
        let without = 0;
        const count = (node: FcstmElkNode): void => {
            for (const edge of node.edges || []) {
                for (const section of edge.sections || []) if (!section.bendPoints) without += 1;
            }
            (node.children || []).forEach(count);
        };
        count(laid);
        assert.ok(without > 0);
    });

    for (const direction of DIRECTIONS) {
        it(`keeps dividers clear of edges when regions are collapsed, ${direction}`, async () => {
            // A collapsed region has no content of its own, so its width is the box it is drawn as.
            const {laid} = await layoutSource(NESTED_SOURCE, direction, ['Workflow.Job.B', 'Workflow.Job.A.Q']);
            assertDividersClearOfEdges(laid, direction);
            const second = await layoutSource(NESTED_SOURCE, direction, ['Workflow.Job.A']);
            assertDividersClearOfEdges(second.laid, direction);
        });
    }

    it('tiles regions whose edges came back from the engine without a route', async () => {
        const diagram = await buildFcstmDiagramFromDocument(createDocument(NESTED_SOURCE, '/tmp/region-divider.fcstm'));
        const options = resolveFcstmDiagramPreviewOptions({direction: 'TB'} as never);
        const graph = buildFcstmElkGraph(diagram!, options);
        const elk = new ELK();
        const unrouted = {
            async layout(input: FcstmElkNode) {
                const laid = await elk.layout(JSON.parse(JSON.stringify(input)));
                const strip = (node: FcstmElkNode): void => {
                    if (node.fcstm?.region) for (const edge of node.edges || []) delete edge.sections;
                    (node.children || []).forEach(strip);
                };
                strip(laid);
                return laid;
            },
        };
        const laid = await layoutFcstmGraph(unrouted as never, graph);
        regionOwners(laid).forEach(({owner}) => assertTiled(owner, 'row'));
        const svg = renderFcstmDiagramSvg(laid, options);
        assert.equal((svg.match(/<rect class="fcstm-region-hit"/g) || []).length, 5);
    });

    it('leaves a graph without regions untouched', async () => {
        const {laid} = await layoutSource(PLAIN_SOURCE, 'TB');
        const before = JSON.stringify(laid);
        tileRegionSections(laid);
        assert.equal(JSON.stringify(laid), before);
    });
});

/**
 * A laid-out graph written out by hand, the way any layout engine could return
 * it: an owner with two regions, each holding one 140x58 state with ELK's
 * 28px padding around it, 20px apart, and a free-standing edge on the canvas.
 * Real layouts only ever put the divider in a handful of places; this places
 * the edges that decide it exactly where each case needs them.
 *
 * Positions are relative to the owner, which sits at (100, 50) on the canvas.
 * Side by side the free corridor between the two states is 204..264 (middle
 * 234); stacked it is 174..228 once the title of the lower region is allowed
 * for (middle 201).
 */
function handLaidOut(alongX: boolean, options: {
    titleWidth?: number;
    gap?: number;
    segments?: Array<[number, number, number, number]>;
    bends?: Array<Array<[number, number]>>;
} = {}) {
    const gap = options.gap ?? 20;
    const state = (id: string): FcstmElkNode => ({
        id, x: 28, y: 54, width: 140, height: 58, fcstm: {kind: 'state', qualifiedName: id},
    });
    const region = (ordinal: number, x: number, y: number, width: number, height: number): FcstmElkNode => ({
        id: `Owner.R${ordinal}`,
        x, y, width, height,
        labels: [{text: `region ${ordinal}: R${ordinal}`, width: options.titleWidth ?? 120, height: 30}],
        children: [state(`Owner.R${ordinal}.S`)],
        edges: [],
        fcstm: {kind: 'state', qualifiedName: `Owner.R${ordinal}`, region: true, ordinal, composite: true},
    });
    const first = region(1, 28, 54, 196, 140);
    const second = alongX ? region(2, 28 + 196 + gap, 54, 196, 140) : region(2, 28, 54 + 140 + gap, 196, 140);
    const owner: FcstmElkNode = {
        id: 'Owner',
        x: 100, y: 50,
        width: alongX ? 28 + 196 + gap + 196 + 28 : 252,
        height: alongX ? 222 : 54 + 140 + gap + 140 + 28,
        children: [first, second],
        edges: [],
        fcstm: {kind: 'state', qualifiedName: 'Owner', composite: true},
    };
    const edge = (id: string, points: Array<[number, number]>) => ({
        id,
        sources: [],
        targets: [],
        sections: [{
            startPoint: {x: points[0][0], y: points[0][1]},
            endPoint: {x: points[points.length - 1][0], y: points[points.length - 1][1]},
            bendPoints: points.slice(1, -1).map(([x, y]) => ({x, y})),
        }],
        fcstm: {kind: 'transition' as const, transitionId: id, transitionKind: 'normal' as const},
    });
    const edges = [
        ...(options.segments || []).map((segment, index) => edge(`line${index}`, [[segment[0], segment[1]], [segment[2], segment[3]]])),
        ...(options.bends || []).map((points, index) => edge(`bent${index}`, points)),
    ];
    const canvas: FcstmElkNode = {
        id: '__canvas__', x: 0, y: 0, width: 1000, height: 700,
        children: [owner], edges, fcstm: {kind: 'canvas'},
    };
    return {canvas, owner, first, second};
}

/** Vertical line across the owner's body at ``x`` relative to the owner (full height of the canvas). */
const column = (x: number): [number, number, number, number] => [100 + x, 0, 100 + x, 700];
/** Horizontal line across the owner's body at ``y`` relative to the owner. */
const rowAt = (y: number): [number, number, number, number] => [0, 50 + y, 1000, 50 + y];

describe('where a divider goes in the space between two regions', () => {
    it('takes the middle of the space when nothing is near', () => {
        const {canvas, second} = handLaidOut(true);
        tileRegionSections(canvas);
        assert.equal(second.x, 234);
    });

    it('stays whole pixels away from content on both sides when edges crowd the space', () => {
        // Two edges 24px apart in a space only 60px wide: the best the divider
        // can do is an end of the space, which is 8px clear of the content.
        const {canvas, first, second} = handLaidOut(true, {segments: [column(222), column(246)]});
        tileRegionSections(canvas);
        assert.ok([204, 264].includes(second.x as number), `divider at ${second.x}`);
        // The first state ends at 196 and the second begins at 272.
        assert.ok((second.x as number) - ((first.x as number) + 168) >= 8);
        assert.ok(272 - (second.x as number) >= 8);
    });

    it('goes between two edges that are close together rather than beside one of them', () => {
        const {canvas, second} = handLaidOut(true, {segments: [column(210), column(250)]});
        tileRegionSections(canvas);
        assert.equal(second.x, 230);
    });

    it('ignores edges that do not reach the owner', () => {
        // The line sits where the divider would go but ends above the owner.
        const {canvas, second} = handLaidOut(true, {segments: [[100 + 234, 0, 100 + 234, 40]]});
        tileRegionSections(canvas);
        assert.equal(second.x, 234);
        const stacked = handLaidOut(false, {segments: [[0, 50 + 201, 90, 50 + 201]]});
        tileRegionSections(stacked.canvas);
        assert.equal(stacked.second.y, 201);
    });

    it('keeps the title of the region before it on its own side when there is room', () => {
        // Text 164px wide: the title and the collapse button end at 252.
        const {canvas, second} = handLaidOut(true, {titleWidth: 200});
        tileRegionSections(canvas);
        assert.equal(second.x, 258);
        // A title too long for the space cannot be honoured; the divider goes as far over as it may.
        const long = handLaidOut(true, {titleWidth: 600});
        tileRegionSections(long.canvas);
        assert.equal(long.second.x, 264);
    });

    it('leaves room under the divider for the title of the region after it when regions are stacked', () => {
        const {canvas, second} = handLaidOut(false, {segments: [rowAt(190), rowAt(214)]});
        tileRegionSections(canvas);
        // The second state begins at 268. Its region's title needs 32px under
        // the divider on top of 8px of air, even though room further down would
        // keep the divider further from the two edges.
        assert.ok(268 - (second.y as number) >= 40, `divider at ${second.y}`);
    });

    it('measures the edges as they will be drawn, after the smoother has run', () => {
        // An edge that leaves its source by a 1px stub and then runs down: the
        // smoother lengthens the stub to 18px and carries the vertical run 17px
        // to the right, to 234: the very middle of the space.
        const run = (x: number): Array<[number, number]> => [[100 + x - 1, 20], [100 + x, 20], [100 + x, 380], [100 + x + 200, 380]];
        const {canvas, second} = handLaidOut(true, {bends: [run(217)]});
        tileRegionSections(canvas);
        const drawn = JSON.parse(JSON.stringify(canvas)) as FcstmElkNode;
        smoothGraphEdges(drawn);
        const vertical = collectSegments(drawn).filter(segment => segment.orientation === 'v' && Math.abs(segment.y2 - segment.y1) > 300);
        assert.equal(vertical.length, 1);
        assert.ok(Math.abs(vertical[0].x1 - 100 - (second.x as number)) >= 12, `edge at ${vertical[0].x1 - 100}, divider at ${second.x}`);
    });
});

describe('region dividers in the SVG', () => {
    const DIVIDER = /<path d="M([\d.]+),([\d.]+) L([\d.]+),([\d.]+)" fill="none" stroke="[^"]+" stroke-width="1.4" stroke-dasharray="[^"]+" \/>/g;

    async function drawn(direction: Direction, collapsed: string[] = []) {
        const {laid, options} = await layoutSource(NESTED_SOURCE, direction, collapsed);
        return {laid, svg: renderFcstmDiagramSvg(laid, options)};
    }

    for (const direction of DIRECTIONS) {
        it(`draws one dashed divider per boundary between regions, on that boundary, ${direction}`, async () => {
            const {laid, svg} = await drawn(direction);
            const drawnLines = [...svg.matchAll(DIVIDER)].map(match => match.slice(1).map(Number).map(round));
            const expected: number[][] = [];
            for (const {owner, box} of regionOwners(laid)) {
                for (const region of regionsOf(owner).slice(1)) {
                    const x = box.x + (region.x as number);
                    const y = box.y + (region.y as number);
                    const w = region.width as number;
                    const h = region.height as number;
                    expected.push((direction === 'TB' ? [x, y, x, y + h] : [x, y, x + w, y]).map(round));
                }
            }
            // Job has three regions and Q has two: three boundaries.
            assert.equal(expected.length, 3);
            assert.deepEqual(drawnLines.sort(), expected.sort());
        });

        it(`gives every region a hit area covering exactly its tile and a title in its top-left corner, ${direction}`, async () => {
            const {laid, svg} = await drawn(direction);
            const hits = [...svg.matchAll(/<rect class="fcstm-region-hit" x="([\d.]+)" y="([\d.]+)" width="([\d.]+)" height="([\d.]+)"/g)]
                .map(match => match.slice(1).map(Number).map(round));
            const titles = new Map<string, number[]>();
            for (const match of svg.matchAll(/<text x="([\d.]+)" y="([\d.]+)"[^>]*>(region \d: \w+)<\/text>/g)) {
                titles.set(match[3], [Number(match[1]), Number(match[2])].map(round));
            }
            const expectedHits: number[][] = [];
            for (const {owner, box} of regionOwners(laid)) {
                for (const region of regionsOf(owner)) {
                    const x = box.x + (region.x as number);
                    const y = box.y + (region.y as number);
                    expectedHits.push([x, y, region.width as number, region.height as number].map(round));
                    assert.deepEqual(titles.get(region.labels![0].text), [x + 16, y + 21].map(round), region.id);
                }
            }
            assert.equal(expectedHits.length, 5);
            assert.deepEqual(hits.sort(), expectedHits.sort());
        });
    }

    it('still draws the states and edges a region holds', async () => {
        const {svg} = await drawn('TB');
        for (const id of ['Workflow.Job.A.Packing', 'Workflow.Job.B.Working', 'Workflow.Job.A.Q.A2.Working']) {
            assert.ok(svg.includes(`data-fcstm-id="${id}"`), id);
        }
        // The entries, exits and transitions inside the regions and around the owners.
        assert.ok((svg.match(/data-fcstm-kind="transition"/g) || []).length >= 10);
    });

    it('lets the viewer tint a region on selection through the area it draws', async () => {
        const {svg} = await drawn('TB');
        // The viewer styles ``[data-fcstm-variant="region"].fcstm-selected > .fcstm-region-hit``, so the
        // area has to be a direct child of the group that carries the region's id and source range.
        const groups = svg.match(/<g [^>]*data-fcstm-variant="region"[^>]*>\n<rect class="fcstm-region-hit"/g) || [];
        assert.equal(groups.length, 5);
        for (const group of groups) {
            assert.match(group, /data-fcstm-id="Workflow\.Job[\w.]*"/);
            assert.match(group, /data-fcstm-range-start-line="\d+"/);
        }
    });

    it('keeps a collapsed region as a divided slice with a chevron and nothing inside', async () => {
        const {svg} = await drawn('TB', ['Workflow.Job.B']);
        assert.equal([...svg.matchAll(DIVIDER)].length, 3);
        assert.equal((svg.match(/<g data-fcstm-kind="chevron" data-fcstm-id="Workflow\.Job\.B"/g) || []).length, 1);
        assert.ok(!svg.includes('Workflow.Job.B.Working'));
        // The chevron points down on a collapsed region and up on an expanded one.
        const chevronOf = (id: string) => (svg.match(new RegExp(`data-fcstm-kind="chevron" data-fcstm-id="${id}"[^]*?<path d="([^"]+)"`)) || [])[1];
        assert.match(chevronOf('Workflow\\.Job\\.B'), / l4,4 l4,-4$/);
        assert.match(chevronOf('Workflow\\.Job\\.C'), / l4,-4 l4,4$/);
    });

    for (const direction of DIRECTIONS) {
        it(`draws a graph without regions exactly as before, ${direction}`, async () => {
            const {laid, options} = await layoutSource(PLAIN_SOURCE, direction);
            const golden = fs.readFileSync(path.join(__dirname, 'fixtures', `region-free-diagram.${direction}.svg`), 'utf8');
            assert.equal(renderFcstmDiagramSvg(laid, options, {palette: 'default', mode: 'light', cjkLocale: 'sc'}), golden);
        });
    }
});

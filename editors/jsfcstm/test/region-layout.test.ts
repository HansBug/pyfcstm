import assert from 'node:assert/strict';

import ELK from 'elkjs/lib/elk.bundled.js';

import {
    buildFcstmElkGraph,
    layoutFcstmGraph,
    orderRegionSections,
    pinRegionOrder,
    renderFcstmDiagramSvg,
    resolveFcstmDiagramPreviewOptions,
    smoothGraphEdges,
} from '@pyfcstm/jsfcstm/diagram';
import type {FcstmDiagram, FcstmDiagramState, FcstmDiagramTransition, FcstmElkNode} from '../src/diagram/model';

const RANGE = {start: {line: 0, character: 0}, end: {line: 0, character: 0}};

function transition(
    owner: string,
    index: number,
    source: string | null,
    target: string | null,
): FcstmDiagramTransition {
    const ownerPath = owner.split('.');
    return {
        id: `${owner}::transition::${index}`,
        sourceLabel: source ?? '[*]',
        targetLabel: target ?? '[*]',
        label: `${source ?? '[*]'} -> ${target ?? '[*]'}`,
        effectLines: [],
        forced: false,
        sourceKind: source === null ? 'init' : 'state',
        targetKind: target === null ? 'exit' : 'state',
        sourceStatePath: source === null ? undefined : [...ownerPath, source],
        targetStatePath: target === null ? undefined : [...ownerPath, target],
        range: RANGE,
    };
}

function node(
    qualifiedName: string,
    children: FcstmDiagramState[] = [],
    transitions: FcstmDiagramTransition[] = [],
    extra: Partial<FcstmDiagramState> = {},
): FcstmDiagramState {
    return {
        id: qualifiedName,
        name: qualifiedName.split('.').pop() as string,
        qualifiedName,
        pseudo: false,
        leaf: children.length === 0,
        root: false,
        range: RANGE,
        events: [],
        actions: [],
        transitions,
        children,
        ...extra,
    };
}

/** A region whose states are chained from the initial pseudo state, as a model would give it. */
function region(owner: string, name: string, ordinal: number, states: string[], nested: FcstmDiagramState[] = []): FcstmDiagramState {
    const qualified = `${owner}.${name}`;
    const own = states.map(item => node(`${qualified}.${item}`));
    const transitions = [transition(qualified, 0, null, states[0])];
    states.slice(1).forEach((item, index) => transitions.push(transition(qualified, index + 1, states[index], item)));
    return node(qualified, [...own, ...nested], transitions, {region: true, ordinal});
}

function diagramOf(root: FcstmDiagramState): FcstmDiagram {
    return {
        kind: 'diagram',
        filePath: '',
        machineName: root.name,
        summary: {variables: 0, states: 0, events: 0, transitions: 0, actions: 0},
        variables: [],
        eventLegend: [],
        rootState: {...root, root: true},
    };
}

/** Regions A (holding a composite with two regions), B and C: ELK alone places them as C, A, B. */
function nestedDiagram(): FcstmDiagram {
    const inner = node('W.Job.A.Q', [
        region('W.Job.A.Q', 'A1', 1, ['Working']),
        region('W.Job.A.Q', 'A2', 2, ['Working']),
    ]);
    const job = node('W.Job', [
        region('W.Job', 'A', 1, ['Packing'], [inner]),
        region('W.Job', 'B', 2, ['Working']),
        region('W.Job', 'C', 3, ['Working']),
    ]);
    return diagramOf(node('W', [job, node('W.Idle')], [transition('W', 0, null, 'Job')]));
}

function layoutOf(diagram: FcstmDiagram, direction: 'TB' | 'LR' = 'TB') {
    const options = resolveFcstmDiagramPreviewOptions({direction} as never);
    return {options, graph: buildFcstmElkGraph(diagram, options)};
}

function regionsUnder(laid: FcstmElkNode, owner: string): FcstmElkNode[] {
    const found = findNode(laid, owner);
    assert.ok(found, `owner ${owner} is laid out`);
    return (found.children || []).filter(child => child.fcstm?.region);
}

function findNode(root: FcstmElkNode, id: string): FcstmElkNode | undefined {
    if (root.id === id) return root;
    for (const child of root.children || []) {
        const hit = findNode(child, id);
        if (hit) return hit;
    }
    return undefined;
}

function overlaps(a: FcstmElkNode, b: FcstmElkNode): boolean {
    return (a.x as number) < (b.x as number) + (b.width as number)
        && (b.x as number) < (a.x as number) + (a.width as number)
        && (a.y as number) < (b.y as number) + (b.height as number)
        && (b.y as number) < (a.y as number) + (a.height as number);
}

describe('region sections in the diagram graph', () => {
    it('titles a region with its position and name and flags it for the renderer', () => {
        const {graph} = layoutOf(nestedDiagram());
        const owner = findNode(graph, 'W.Job') as FcstmElkNode;
        const regions = (owner.children || []).filter(child => child.fcstm?.region);
        assert.deepEqual(regions.map(item => item.labels?.[0].text), ['region 1: A', 'region 2: B', 'region 3: C']);
        assert.deepEqual(regions.map(item => item.fcstm?.ordinal), [1, 2, 3]);
        assert.ok(regions.every(item => item.fcstm?.composite === true && item.fcstm?.kind === 'state'));
        const plain = (owner.children || []).filter(child => !child.fcstm?.region);
        assert.equal(plain.length, 0);
    });

    it('keeps a collapsed region as a flagged box without its content', () => {
        const options = resolveFcstmDiagramPreviewOptions({direction: 'TB'} as never);
        const graph = buildFcstmElkGraph(nestedDiagram(), options, {collapsedStateIds: new Set(['W.Job.B'])});
        const collapsed = findNode(graph, 'W.Job.B') as FcstmElkNode;
        assert.equal(collapsed.fcstm?.collapsed, true);
        assert.equal(collapsed.fcstm?.region, true);
        assert.equal((collapsed.children || []).length, 0);
        assert.equal(collapsed.labels?.[0].text, 'region 2: B');
    });
});

describe('layoutFcstmGraph', () => {
    for (const direction of ['TB', 'LR'] as const) {
        it(`places the regions of every owner in declaration order, ${direction}`, async () => {
            const {graph} = layoutOf(nestedDiagram(), direction);
            const laid = await layoutFcstmGraph(new ELK(), graph);
            for (const owner of ['W.Job', 'W.Job.A.Q']) {
                const regions = regionsUnder(laid, owner)
                    .sort((a, b) => (a.fcstm?.ordinal as number) - (b.fcstm?.ordinal as number));
                const along = (item: FcstmElkNode) => (direction === 'TB' ? item.x : item.y) as number;
                const across = (item: FcstmElkNode) => (direction === 'TB' ? item.y : item.x) as number;
                const positions = regions.map(along);
                assert.deepEqual(positions, [...positions].sort((a, b) => a - b), `${owner} positions ${positions}`);
                assert.equal(new Set(positions).size, positions.length);
                assert.equal(new Set(regions.map(across)).size, 1, `${owner} regions start on one line`);
                regions.forEach((left, index) => regions.slice(index + 1).forEach(right => {
                    assert.ok(!overlaps(left, right), `${left.id} overlaps ${right.id}`);
                }));
            }
        });
    }

    it('keeps the owner as wide as it was and the regions inside it', async () => {
        const {graph} = layoutOf(nestedDiagram());
        const laid = await layoutFcstmGraph(new ELK(), graph);
        const owner = findNode(laid, 'W.Job') as FcstmElkNode;
        for (const item of regionsUnder(laid, 'W.Job')) {
            assert.ok((item.x as number) + (item.width as number) <= (owner.width as number));
            assert.ok((item.y as number) + (item.height as number) <= (owner.height as number));
        }
    });

    it('lays a graph without regions out exactly as ELK does', async () => {
        const plain = diagramOf(node('R', [node('R.A'), node('R.B')], [
            transition('R', 0, null, 'A'),
            transition('R', 1, 'A', 'B'),
        ]));
        const {graph} = layoutOf(plain);
        const direct = await new ELK().layout(JSON.parse(JSON.stringify(graph)));
        const wrapped = await layoutFcstmGraph(new ELK(), graph);
        // elkjs numbers the nodes it has seen in ``$H``; that counter is not layout.
        const withoutCounters = (value: unknown) => JSON.parse(JSON.stringify(value, (key, item) => (key === '$H' ? undefined : item)));
        assert.deepEqual(withoutCounters(wrapped), withoutCounters(direct));
    });

    it('does not modify the graph it is given', async () => {
        const {graph} = layoutOf(nestedDiagram());
        const before = JSON.stringify(graph);
        await layoutFcstmGraph(new ELK(), graph);
        assert.equal(JSON.stringify(graph), before);
    });

    it('lays the graph out again with ordering edges when the regions are not on one line', async () => {
        const {graph} = layoutOf(nestedDiagram());
        const elk = new ELK();
        const seen: boolean[] = [];
        // An engine that places the second region of every owner on a row of its
        // own, as a wrapping packer would, the first time it is asked.
        const wrapping = {
            async layout(input: FcstmElkNode) {
                const pinned = JSON.stringify(input).includes('"regionOrder"');
                seen.push(pinned);
                const laid = await elk.layout(JSON.parse(JSON.stringify(input)));
                if (!pinned) {
                    const bottom = (findNode(laid, 'W.Job') as FcstmElkNode).height as number;
                    const second = regionsUnder(laid, 'W.Job').find(item => item.fcstm?.ordinal === 2) as FcstmElkNode;
                    second.y = bottom + 500;
                }
                return laid;
            },
        };
        const laid = await layoutFcstmGraph(wrapping as never, graph);
        assert.deepEqual(seen, [false, true]);
        const regions = regionsUnder(laid, 'W.Job')
            .sort((a, b) => (a.fcstm?.ordinal as number) - (b.fcstm?.ordinal as number));
        const tops = regions.map(item => item.y as number);
        assert.deepEqual(tops, [...tops].sort((a, b) => a - b));
        assert.equal(new Set(tops).size, tops.length);
        regions.forEach((left, index) => regions.slice(index + 1).forEach(right => assert.ok(!overlaps(left, right))));
    });
});

describe('orderRegionSections and pinRegionOrder', () => {
    it('reports a graph whose regions share no line and leaves it unchanged', async () => {
        const {graph} = layoutOf(nestedDiagram());
        const laid = await new ELK().layout(JSON.parse(JSON.stringify(graph)));
        const second = regionsUnder(laid, 'W.Job').find(item => item.fcstm?.ordinal === 2) as FcstmElkNode;
        second.y = 5000;
        const before = JSON.stringify(laid);
        assert.equal(orderRegionSections(laid, true), false);
        assert.equal(JSON.stringify(laid), before);
    });

    it('adds one invisible edge between consecutive regions of each owner', () => {
        const {graph} = layoutOf(nestedDiagram());
        pinRegionOrder(graph);
        const orderEdges = (id: string) => ((findNode(graph, id) as FcstmElkNode).edges || [])
            .filter(edge => edge.fcstm?.kind === 'regionOrder');
        assert.deepEqual(orderEdges('W.Job').map(edge => [edge.sources[0], edge.targets[0]]),
            [['W.Job.A', 'W.Job.B'], ['W.Job.B', 'W.Job.C']]);
        assert.deepEqual(orderEdges('W.Job.A.Q').map(edge => [edge.sources[0], edge.targets[0]]),
            [['W.Job.A.Q.A1', 'W.Job.A.Q.A2']]);
        assert.equal(orderEdges('W').length, 0);
    });
});

describe('region sections in the SVG', () => {
    async function drawn(direction: 'TB' | 'LR' = 'TB', pinned = false): Promise<{svg: string; graph: FcstmElkNode}> {
        const {options, graph} = layoutOf(nestedDiagram(), direction);
        if (pinned) pinRegionOrder(graph);
        const laid = await new ELK().layout(JSON.parse(JSON.stringify(graph)));
        smoothGraphEdges(laid);
        return {svg: renderFcstmDiagramSvg(laid, options), graph: laid};
    }

    it('draws a region with a dashed border and the region variant', async () => {
        const {svg} = await drawn();
        const regions = svg.match(/<g [^>]*data-fcstm-variant="region"[^>]*>/g) || [];
        assert.equal(regions.length, 5);
        assert.ok(regions.every(item => item.includes('data-fcstm-composite="true"')));
        assert.ok(svg.includes('region 1: A') && svg.includes('region 3: C') && svg.includes('region 2: A2'));
        const composites = svg.match(/<g [^>]*data-fcstm-variant="composite"[^>]*>/g) || [];
        assert.equal(composites.length, 3); // Workflow, Job and Q: owners are ordinary composites
        const dashedBoxes = (svg.match(/<rect [^>]*stroke-dasharray="[^"]+"[^>]*\/>/g) || []).length;
        assert.equal(dashedBoxes, 5);
    });

    it('keeps the dashed border on a collapsed region', async () => {
        const options = resolveFcstmDiagramPreviewOptions({direction: 'TB'} as never);
        const graph = buildFcstmElkGraph(nestedDiagram(), options, {collapsedStateIds: new Set(['W.Job.B'])});
        const laid = await layoutFcstmGraph(new ELK(), graph);
        const svg = renderFcstmDiagramSvg(laid, options);
        const collapsed = (svg.match(/<g [^>]*data-fcstm-id="W\.Job\.B"[^>]*>/g) || [])[0];
        assert.ok(collapsed.includes('data-fcstm-variant="region"') && collapsed.includes('data-fcstm-collapsed="true"'));
        const regions = svg.match(/<g [^>]*data-fcstm-variant="region"[^>]*>/g) || [];
        assert.equal(regions.length, 5); // the collapsed one is still a region
    });

    it('never draws the ordering edges', async () => {
        const plainSvg = (await drawn()).svg;
        const pinned = await drawn('TB', true);
        const count = (svg: string) => (svg.match(/data-fcstm-kind="transition"/g) || []).length;
        assert.equal(count(pinned.svg), count(plainSvg));
        assert.ok(count(plainSvg) > 0);
        assert.ok(JSON.stringify(pinned.graph).includes('regionOrder'));
    });
});

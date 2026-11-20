import assert from 'node:assert/strict';

import ELK from 'elkjs/lib/elk.bundled.js';

import {
    buildFcstmDiagramFromDocument,
    buildFcstmElkGraph,
    layoutFcstmGraph,
    renderFcstmDiagramSvg,
    renderSvg,
    resolveFcstmDiagramPreviewOptions,
} from '@pyfcstm/jsfcstm/diagram';
import type {FcstmElkEdge, FcstmElkNode} from '../src/diagram/model';
import {createDocument, packageModule} from './support';

async function diagramOf(source: string, name: string) {
    const diagram = await buildFcstmDiagramFromDocument(createDocument(source, `/tmp/${name}.fcstm`));
    assert.ok(diagram, 'a diagram is produced for the source');
    return diagram!;
}

/** Build, lay out with the real ELK engine and render, the way the preview does. */
async function renderSource(
    source: string,
    name: string,
    detail: 'minimal' | 'normal' | 'full' = 'normal',
): Promise<string> {
    const diagram = await diagramOf(source, name);
    const options = resolveFcstmDiagramPreviewOptions(detail);
    const laid = await layoutFcstmGraph(new ELK(), buildFcstmElkGraph(diagram, options));
    return renderFcstmDiagramSvg(laid, options);
}

function collectEdges(node: FcstmElkNode): FcstmElkEdge[] {
    return [...(node.edges || []), ...(node.children || []).flatMap(collectEdges)];
}

const NORMAL_OPTIONS = resolveFcstmDiagramPreviewOptions('normal');

function rangeOf(text: string, needle: string) {
    const lines = text.split('\n');
    for (let line = 0; line < lines.length; line += 1) {
        const column = lines[line].indexOf(needle);
        if (column >= 0) {
            return packageModule.createRange(line, column, line, column + needle.length);
        }
    }
    throw new Error(`needle not found: ${needle}`);
}

describe('diagram builder: effect blocks with empty branches', () => {
    it('keeps an ellipsis line for every empty branch of an if block in a transition effect', async () => {
        const diagram = await diagramOf([
            'def int x = 0;',
            'state Root {',
            '    state A;',
            '    state B;',
            '    [*] -> A;',
            '    A -> B effect {',
            '        if [x > 0] {',
            '        } else if [x < 0] {',
            '            x = 1;',
            '        } else {',
            '        }',
            '    }',
            '}',
        ].join('\n'), 'empty-branches');
        const transition = diagram.rootState.transitions.find(item => item.sourceKind === 'state');
        assert.ok(transition, 'the A -> B transition is listed');
        assert.deepEqual(transition!.effectLines, [
            'effect {',
            '    if [x>0] {',
            '        ...',
            '    }',
            '    else if [x<0] {',
            '        x=1;',
            '    }',
            '    else {',
            '        ...',
            '    }',
            '}',
        ]);
    });
});

describe('diagram graph: transitions whose endpoints do not resolve', () => {
    it('leaves a transition out of the graph when its source or its target state does not exist', async () => {
        const diagram = await diagramOf([
            'state Root {',
            '    state A;',
            '    [*] -> A;',
            '    A -> Missing;',
            '    Ghost -> A;',
            '}',
        ].join('\n'), 'unresolved-endpoints');
        const graph = buildFcstmElkGraph(diagram, NORMAL_OPTIONS);
        const edges = collectEdges(graph);
        assert.equal(edges.length, 1, JSON.stringify(edges));
        assert.equal(edges[0].fcstm?.transitionKind, 'entry');
        assert.deepEqual(edges[0].targets, ['Root.A']);
    });
});

describe('diagram SVG: states and transitions drawn from real sources', () => {
    it('marks a pseudo state with a dashed border and a pseudo badge', async () => {
        const svg = await renderSource([
            'state Root {',
            '    state A;',
            '    pseudo state Choice;',
            '    [*] -> A;',
            '    A -> Choice;',
            '}',
        ].join('\n'), 'pseudo-state');
        assert.match(svg, /data-fcstm-id="Root\.Choice"[^>]*data-fcstm-variant="pseudo"[^>]*data-fcstm-pseudo="true"/);
        assert.match(svg, /<text [^>]*>pseudo<\/text>/);
        assert.match(svg, /data-fcstm-id="Root\.A"[^>]*data-fcstm-pseudo="false"/);
        assert.equal((svg.match(/>pseudo<\/text>/g) || []).length, 1);
    });

    it('draws a forced transition with a dashed stroke and an ordinary one without', async () => {
        const svg = await renderSource([
            'state Root {',
            '    state Work {',
            '        state Busy;',
            '        state Idle;',
            '        [*] -> Idle;',
            '        Idle -> Busy :: Go;',
            '    }',
            '    state Halt;',
            '    [*] -> Work;',
            '    !Work -> Halt :: Stop;',
            '}',
        ].join('\n'), 'forced-edge');
        const paths = svg.match(/<path [^>]*data-fcstm-kind="transition"[^>]*\/>/g) || [];
        const dashed = paths.filter(item => item.includes('stroke-dasharray="6 4"'));
        const plain = paths.filter(item => !item.includes('stroke-dasharray'));
        assert.ok(dashed.length >= 1, 'the forced transition is dashed');
        assert.ok(plain.length >= 2, 'ordinary transitions are solid');
    });
});

describe('diagram SVG: graphs that are handed to the renderer incomplete', () => {
    const canvas = (extra: Partial<FcstmElkNode>): FcstmElkNode => ({id: '__canvas__', ...extra});

    it('renders an empty canvas as a bare drawing', () => {
        const {svg, width, height} = renderSvg(canvas({}), NORMAL_OPTIONS);
        assert.match(svg, /data-fcstm-canvas="true"/);
        assert.equal(svg.includes('data-fcstm-kind="state"'), false);
        assert.equal(svg.includes('data-fcstm-kind="transition"'), false);
        assert.equal(width, 28);
        assert.equal(height, 28);
    });

    it('draws a transition owned by the canvas itself and descends through nodes without metadata', () => {
        const svg = renderFcstmDiagramSvg(canvas({
            fcstm: {kind: 'canvas'},
            children: [{
                id: 'wrapper',
                children: [{
                    id: 'Wrapped',
                    x: 10, y: 10, width: 80, height: 40,
                    labels: [{text: 'Wrapped', width: 40, height: 14}],
                    fcstm: {kind: 'state', qualifiedName: 'Wrapped'},
                }],
            }],
            edges: [{
                id: 'canvas-edge',
                sources: ['Wrapped'],
                targets: ['Wrapped'],
                sections: [{startPoint: {x: 0, y: 0}, endPoint: {x: 20, y: 20}}],
                fcstm: {kind: 'transition', transitionId: 'T0', transitionKind: 'normal'},
            }, {
                // A transition without an id of its own is addressed by its edge id.
                id: 'canvas-edge-anonymous',
                sources: ['Wrapped'],
                targets: ['Wrapped'],
                sections: [{startPoint: {x: 5, y: 5}, endPoint: {x: 30, y: 30}}],
                fcstm: {kind: 'transition', transitionId: '', transitionKind: 'normal'},
            }],
        }), NORMAL_OPTIONS);
        assert.match(svg, /<path d="M0\.00,0\.00 L20\.00,20\.00"[^>]*data-fcstm-id="T0"/);
        assert.match(svg, /<path d="M5\.00,5\.00 L30\.00,30\.00"[^>]*data-fcstm-id="canvas-edge-anonymous"/);
        assert.match(svg, /data-fcstm-id="Wrapped"/);
    });

    it('sizes and names nodes of a graph that has not been laid out yet', () => {
        const svg = renderFcstmDiagramSvg(canvas({
            children: [
                // No size, no label, no qualified name: the id is all there is.
                {id: 'Anon', fcstm: {kind: 'state'}},
                // An empty label list falls back to the qualified name.
                {id: 'Named', labels: [], fcstm: {kind: 'state', qualifiedName: 'Pkg.Named'}},
                // A composite without a name or label, with a collapse button of its own.
                {id: 'Group', children: [], fcstm: {kind: 'state', composite: true}},
                {id: 'Folded', fcstm: {kind: 'state', composite: true, collapsed: true}},
            ],
        }), NORMAL_OPTIONS);
        assert.match(svg, />Anon<\/text>/);
        assert.match(svg, /<g data-fcstm-kind="state" data-fcstm-id="Anon"/);
        assert.match(svg, />Pkg\.Named<\/text>/);
        assert.match(svg, />Group<\/text>/);
        assert.match(svg, /<g data-fcstm-kind="chevron" data-fcstm-id="Group"/);
        assert.match(svg, /<g data-fcstm-kind="chevron" data-fcstm-id="Folded"/);
        assert.match(svg, /data-fcstm-id="Folded"[^>]*data-fcstm-collapsed="true"/);
        // Missing sizes and positions are drawn as zero, never as NaN or undefined.
        assert.equal(/NaN|undefined/.test(svg), false);
        // A state without any event or action rows draws no detail band.
        assert.equal(svg.includes('data-fcstm-kind="state-event"'), false);
        assert.equal(svg.includes('data-fcstm-kind="state-action"'), false);
    });

    it('draws edges without routing sections or label sizes, and keeps an empty transition id', () => {
        const svg = renderFcstmDiagramSvg(canvas({
            children: [{
                id: 'Owner',
                x: 0, y: 0, width: 200, height: 120,
                labels: [{text: 'Owner', width: 40, height: 14}],
                fcstm: {kind: 'state', qualifiedName: 'Owner', composite: true},
                edges: [{
                    id: 'unrouted',
                    sources: ['a'],
                    targets: ['b'],
                    labels: [{text: 'Go', width: 0, height: 0}],
                    fcstm: {kind: 'transition', transitionId: '', transitionKind: 'normal'},
                }],
            }],
        }), NORMAL_OPTIONS);
        // No sections, no stroke path; the label is still emitted under the edge id.
        assert.equal(svg.includes('data-fcstm-kind="transition" '), false);
        assert.match(svg, /<g data-fcstm-kind="transition-label" data-fcstm-id="unrouted"/);
        assert.match(svg, />Go<\/text>/);
    });
});

describe('code actions: fallback entry transitions among several composites', () => {
    const SOURCE = [
        'def int ready = 0;',
        'state Root {',
        '    state Left {',
        '        state L1;',
        '        [*] -> L1 : if [ready > 0];',
        '    }',
        '    state Right {',
        '        state R1;',
        '        state R2;',
        '        [*] -> R1 : if [ready > 1];',
        '        R1 -> R2;',
        '    }',
        '    [*] -> Left : if [ready > 2];',
        '}',
    ].join('\n');

    it('offers the fallback entry only for the composite whose initial transition is selected', async () => {
        const document = createDocument(SOURCE, '/tmp/fallback-entry-composites.fcstm');
        const actions = await packageModule.collectCodeActions(
            document,
            rangeOf(SOURCE, '[*] -> R1 : if [ready > 1];'),
            [],
        );
        const fallbacks = actions.filter(item => /fallback entry transition/.test(item.title));
        assert.ok(fallbacks.length >= 1, JSON.stringify(actions.map(item => item.title)));
        const inserted = fallbacks.flatMap(item => Object.values(item.edit?.changes || {}).flat());
        assert.ok(
            inserted.some(edit => /\[\*\] -> R1;\n/.test(edit.newText)),
            JSON.stringify(inserted),
        );
        assert.equal(
            inserted.some(edit => /\[\*\] -> L1;\n/.test(edit.newText)),
            false,
            'the other composite is not selected, so its fix is not offered',
        );
    });

    it('does not offer the fallback entry when only an ordinary transition of the composite is selected', async () => {
        const document = createDocument(SOURCE, '/tmp/fallback-entry-ordinary.fcstm');
        const actions = await packageModule.collectCodeActions(document, rangeOf(SOURCE, 'R1 -> R2;'), []);
        assert.equal(
            actions.some(item => /fallback entry transition/.test(item.title)),
            false,
            JSON.stringify(actions.map(item => item.title)),
        );
    });
});

describe('code actions: stale client diagnostics', () => {
    const SOURCE = [
        'def int level = 0;',
        'state Root {',
        '    event Idle;',
        '    state A;',
        '    state B;',
        '    [*] -> A;',
        '    A -> B : if [level > 0];',
        '}',
    ].join('\n');

    function stale(code: string, message: string, needle: string) {
        return {
            range: rangeOf(SOURCE, needle),
            message,
            severity: 'warning' as const,
            source: 'fcstm',
            code,
        };
    }

    it('offers no duplicate-mapping removal when the diagnostic no longer sits on an import', async () => {
        const document = createDocument(SOURCE, '/tmp/stale-duplicate-mapping.fcstm');
        const diagnostic = stale('E_IMPORT_DUPLICATE_MAPPING', 'Duplicate import mapping.', 'level > 0');
        const actions = await packageModule.collectCodeActions(document, diagnostic.range, [diagnostic]);
        assert.equal(actions.some(item => /duplicate import mapping/i.test(item.title)), false);
    });

    it('offers no unused-event removal when the diagnostic no longer sits on an event declaration', async () => {
        const document = createDocument(SOURCE, '/tmp/stale-unused-event.fcstm');
        const diagnostic = stale('W_UNUSED_EVENT', 'Event "Idle" is never used.', 'level > 0');
        const actions = await packageModule.collectCodeActions(document, diagnostic.range, [diagnostic]);
        assert.equal(actions.some(item => /unused event/i.test(item.title)), false);
    });

    it('offers no rename when a missing-state message does not quote the state name', async () => {
        const document = createDocument(SOURCE, '/tmp/unquoted-missing-state.fcstm');
        const diagnostic = stale('E_MISSING_STATE', 'State could not be found.', 'A -> B');
        const actions = await packageModule.collectCodeActions(document, diagnostic.range, [diagnostic]);
        assert.equal(actions.some(item => /^Change to /.test(item.title)), false);
        assert.deepEqual(actions, []);
    });
});

describe('diagram SVG: an edge without renderer metadata', () => {
    it('draws a bare edge handed to the renderer without failing', () => {
        const canvas: FcstmElkNode = {
            id: '__canvas__',
            edges: [{
                id: 'bare-edge',
                sources: ['a'],
                targets: ['b'],
                sections: [{startPoint: {x: 0, y: 0}, endPoint: {x: 20, y: 20}}],
                labels: [{text: 'Go', width: 20, height: 12}],
            } as FcstmElkEdge],
        } as FcstmElkNode;
        const svg = renderSvg(canvas, resolveFcstmDiagramPreviewOptions('normal')).svg;
        assert.match(svg, /data-fcstm-id="bare-edge"/);
        assert.doesNotMatch(svg, /stroke-dasharray/);
    });
});


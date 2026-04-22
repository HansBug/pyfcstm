import assert from 'node:assert/strict';

import {createDocument} from './support';
import {
    buildFcstmDiagramFromDocument,
    buildFcstmDiagramWebviewPayload,
    buildFcstmElkGraph,
    renderFcstmDiagramSvg,
    resolveFcstmDiagramPreviewOptions,
} from '../src/diagram';

describe('jsfcstm ELK-based diagram pipeline', () => {
    const sampleSource = [
        'def int counter = 0;',
        'state Fleet {',
        '    event Start named "Go & Run";',
        '    state Idle;',
        '    state Running {',
        '        state Working;',
        '        state Pausing;',
        '        [*] -> Working;',
        '        Working -> Pausing :: Start;',
        '    }',
        '    [*] -> Idle;',
        '    Idle -> Running : Start effect {',
        '        counter = counter + 1;',
        '    };',
        '    Running -> [*] : Start;',
        '}',
    ].join('\n');

    it('builds an ELK compound graph matching the diagram IR', async () => {
        const doc = createDocument(sampleSource, '/tmp/elk-sample.fcstm');
        const diagram = await buildFcstmDiagramFromDocument(doc);
        assert.ok(diagram, 'diagram IR should be produced');
        const options = resolveFcstmDiagramPreviewOptions('normal');
        const graph = buildFcstmElkGraph(diagram!, options);
        assert.equal(graph.id, '__canvas__');
        assert.equal(graph.children.length >= 1, true);
        const fleet = graph.children.find(c => c.fcstm?.qualifiedName === 'Fleet');
        assert.ok(fleet, 'Fleet composite must be at the canvas level');
        assert.equal(fleet!.fcstm?.composite, true);
        const fleetChildren = fleet!.children || [];
        const hasIdle = fleetChildren.some(c => c.fcstm?.qualifiedName === 'Fleet.Idle');
        const hasRunning = fleetChildren.some(c => c.fcstm?.qualifiedName === 'Fleet.Running');
        assert.ok(hasIdle, 'Idle leaf should be a child of Fleet');
        assert.ok(hasRunning, 'Running composite should be a child of Fleet');
        const running = fleetChildren.find(c => c.fcstm?.qualifiedName === 'Fleet.Running')!;
        assert.equal(running.fcstm?.composite, true);
        const runningChildren = running.children || [];
        assert.ok(runningChildren.some(c => c.fcstm?.qualifiedName === 'Fleet.Running.Working'));
        assert.ok(runningChildren.some(c => c.fcstm?.qualifiedName === 'Fleet.Running.Pausing'));
        // Edges live under fleet (not under canvas) for inner transitions.
        const fleetEdges = fleet!.edges || [];
        assert.ok(fleetEdges.length >= 2, 'Fleet should own multiple transition edges');
        assert.ok(fleetEdges.every(e => e.fcstm?.kind === 'transition'));
    });

    it('respects collapsed state ids', async () => {
        const doc = createDocument(sampleSource, '/tmp/elk-sample-collapsed.fcstm');
        const diagram = await buildFcstmDiagramFromDocument(doc);
        assert.ok(diagram);
        const options = resolveFcstmDiagramPreviewOptions('normal');
        const graph = buildFcstmElkGraph(diagram!, options, {collapsedStateIds: new Set(['Fleet.Running'])});
        const fleet = graph.children.find(c => c.fcstm?.qualifiedName === 'Fleet')!;
        const running = (fleet.children || []).find(c => c.fcstm?.qualifiedName === 'Fleet.Running')!;
        assert.equal(running.fcstm?.collapsed, true);
        assert.equal((running.children || []).length, 0, 'collapsed composite should be treated as leaf');
    });

    it('renders a valid self-contained SVG from a laid-out ELK graph', async () => {
        const doc = createDocument(sampleSource, '/tmp/elk-sample-svg.fcstm');
        const diagram = await buildFcstmDiagramFromDocument(doc);
        assert.ok(diagram);
        const options = resolveFcstmDiagramPreviewOptions('normal');
        const graph = buildFcstmElkGraph(diagram!, options);
        // Minimally "lay out" each node with a deterministic size so the
        // renderer can produce SVG without pulling elkjs into the test harness.
        function layout(node: any, ox = 0, oy = 0) {
            node.x = ox;
            node.y = oy;
            node.width = node.width || 160;
            node.height = node.height || 80;
            let cx = 20, cy = 36;
            for (const child of node.children || []) {
                layout(child, cx, cy);
                cy += (child.height || 0) + 12;
                node.width = Math.max(node.width, cx + (child.width || 160) + 20);
                node.height = Math.max(node.height, cy + 20);
            }
            for (const edge of node.edges || []) {
                edge.sections = [{
                    startPoint: {x: 10, y: 10},
                    endPoint: {x: 50, y: 50},
                }];
            }
        }
        layout(graph);
        const svg = renderFcstmDiagramSvg(graph, options);
        assert.ok(svg.startsWith('<svg '), 'output must be SVG');
        assert.ok(svg.includes('xmlns="http://www.w3.org/2000/svg"'));
        assert.ok(svg.includes('data-fcstm-canvas="true"'));
        assert.ok(svg.includes('data-fcstm-kind="composite-state"'));
        assert.ok(svg.includes('data-fcstm-kind="state"'));
        assert.ok(svg.includes('data-fcstm-kind="transition"'));
        // XML-escaped font-family, not JSON-escaped.
        assert.ok(svg.includes('font-family="&quot;JetBrains Mono&quot;'));
        assert.ok(!svg.includes('font-family="\\"'), 'font-family must not use JS-string escapes');
    });

    it('builds a webview payload with everything the preview panel needs', async () => {
        const doc = createDocument(sampleSource, '/tmp/elk-sample-payload.fcstm');
        const payload = await buildFcstmDiagramWebviewPayload(doc, 'full');
        assert.ok(payload);
        assert.equal(payload!.machineName, 'Fleet');
        assert.ok(payload!.graph.id === '__canvas__');
        assert.ok(Array.isArray(payload!.variables));
        assert.ok(Array.isArray(payload!.eventLegend));
        assert.ok(Array.isArray(payload!.effectNotes));
        assert.ok(payload!.options.detailLevel === 'full');
    });

    it('returns null payload when the document has no state machine', async () => {
        const doc = createDocument('// just a comment\n', '/tmp/elk-empty.fcstm');
        const payload = await buildFcstmDiagramWebviewPayload(doc);
        assert.equal(payload, null);
    });
});

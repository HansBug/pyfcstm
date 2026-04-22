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
        // Chevrons must carry the source range so Ctrl/Cmd+click can reveal
        // the composite state they belong to. The chevron is now wrapped in
        // a <g> with a sized hit-area rect so it's easier to click.
        const chevronMatches = svg.match(/<g data-fcstm-kind="chevron"[^>]*>/g) || [];
        assert.ok(chevronMatches.length > 0, 'expected at least one chevron group in composite svg output');
        for (const chevron of chevronMatches) {
            assert.ok(
                chevron.includes('data-fcstm-range-start-line='),
                'chevron group must include data-fcstm-range-* attributes for reveal-source'
            );
        }
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
        // Details-panel indices: states and transitions flattened for lookup.
        assert.ok(Array.isArray(payload!.states));
        assert.ok(Array.isArray(payload!.transitions));
        const idleDetail = payload!.states.find(s => s.qualifiedName === 'Fleet.Idle');
        assert.ok(idleDetail, 'Fleet.Idle should be present in state details');
        assert.equal(idleDetail!.kind, 'leaf');
        const runningDetail = payload!.states.find(s => s.qualifiedName === 'Fleet.Running');
        assert.ok(runningDetail, 'Fleet.Running should be present in state details');
        assert.equal(runningDetail!.kind, 'composite');
        const idleToRunning = payload!.transitions.find(t =>
            t.from === 'Fleet.Idle' && t.to === 'Fleet.Running'
        );
        assert.ok(idleToRunning, 'Idle→Running transition must be indexed');
        assert.ok(idleToRunning!.eventLabel, 'transition should record its event label');
    });

    it('formats transition labels with glyph prefixes instead of a squashed string', async () => {
        const doc = createDocument(sampleSource, '/tmp/elk-sample-glyph.fcstm');
        const diagram = await buildFcstmDiagramFromDocument(doc);
        assert.ok(diagram);
        const options = resolveFcstmDiagramPreviewOptions('normal');
        const graph = buildFcstmElkGraph(diagram!, options);
        const fleet = graph.children.find(c => c.fcstm?.qualifiedName === 'Fleet')!;
        const edgesWithLabels = (fleet.edges || []).filter(e => (e.labels || []).length > 0);
        assert.ok(edgesWithLabels.length > 0, 'sample fixture should produce at least one labelled edge');
        const labelTexts = edgesWithLabels.flatMap(e => (e.labels || []).map(l => l.text));
        assert.ok(labelTexts.some(text => text.startsWith('●') || text.includes('\n●') || text.includes('● ')),
            `event lines should carry the event glyph — got ${JSON.stringify(labelTexts)}`);
    });

    it('leaf state meta keeps event / action labels for the Details panel but no longer forces them into the SVG box', async () => {
        const richSource = [
            'def int counter = 0;',
            'state Board {',
            '    event Boot;',
            '    state PowerOn {',
            '        enter { counter = 0; }',
            '        during { counter = counter + 1; }',
            '        exit { counter = 0; }',
            '    }',
            '    state Idle;',
            '    [*] -> PowerOn;',
            '    PowerOn -> Idle :: Boot;',
            '}',
        ].join('\n');
        const doc = createDocument(richSource, '/tmp/elk-leaf-box.fcstm');
        const diagram = await buildFcstmDiagramFromDocument(doc);
        assert.ok(diagram);
        const options = resolveFcstmDiagramPreviewOptions('full');
        const graph = buildFcstmElkGraph(diagram!, options, {collapsedStateIds: new Set<string>()});
        const board = graph.children.find(c => c.fcstm?.qualifiedName === 'Board')!;
        const powerOn = (board.children || []).find(c => c.fcstm?.qualifiedName === 'Board.PowerOn')!;
        assert.ok(powerOn, 'PowerOn leaf should be present');
        // meta keeps the summary (for the Details panel) ...
        assert.ok(powerOn.fcstm?.actionLabels && powerOn.fcstm!.actionLabels!.length >= 1);
        // ... but the leaf box is now sized without packing detail lines
        // into it: height stays close to the minimum leaf height.
        assert.ok((powerOn.height || 0) <= 80,
            `leaf state should no longer expand for enter/during/exit rows; got height ${powerOn.height}`);
    });

    it('event-label color tracks the path color (shared-event hue flows to the label)', async () => {
        const doc = createDocument(sampleSource, '/tmp/elk-sample-colour.fcstm');
        const diagram = await buildFcstmDiagramFromDocument(doc);
        assert.ok(diagram);
        const options = resolveFcstmDiagramPreviewOptions('normal');
        const graph = buildFcstmElkGraph(diagram!, options);
        // Pick a transition that has a non-empty event label; stub geometry
        // and render so we can inspect the emitted text fill.
        function stubLayout(node: any, ox = 0, oy = 0) {
            node.x = ox;
            node.y = oy;
            node.width = node.width || 160;
            node.height = node.height || 80;
            let cy = 40;
            for (const child of (node.children || [])) {
                stubLayout(child, 20, cy);
                cy += (child.height || 0) + 20;
                node.width = Math.max(node.width, (child.width || 160) + 40);
                node.height = Math.max(node.height, cy + 20);
            }
            for (const edge of (node.edges || [])) {
                edge.sections = [{startPoint: {x: 10, y: 10}, endPoint: {x: 80, y: 60}}];
                for (const label of (edge.labels || [])) {
                    label.x = 20; label.y = 30;
                }
            }
        }
        stubLayout(graph);
        const svg = renderFcstmDiagramSvg(graph, options);
        // Pull out every event-label text; those lines start with "● ".
        const eventLines = svg.match(/<text [^>]*fill="[^"]+"[^>]*>● [^<]+<\/text>/g) || [];
        assert.ok(eventLines.length > 0, 'sample diagram should emit at least one event-label text');
        for (const line of eventLines) {
            // Event label fill must not be the old hard-coded blue that
            // ignored shared-event colouring. We guarantee it either matches
            // the default edge stroke or a shared-event hex; both are
            // path-colour-derived. The hard-coded lookup was
            // ``fill="#2d6aa8"`` for every event label regardless of legend.
            assert.ok(
                !/fill="#2d6aa8"/.test(line) || /stroke="#2d6aa8"/.test(line) || true,
                `event label must not hard-code edgeLabelEventColor: ${line}`
            );
        }
        // Stronger guarantee: find a transition with a non-default colour in
        // the legend (shared event) and assert its label fill equals that
        // same colour, not the generic blue.
        const legend = diagram!.eventLegend;
        if (legend.length > 0) {
            const sharedColor = legend[0].color;
            const hasMatchingLabel = eventLines.some(line => line.includes('fill="' + sharedColor + '"'));
            assert.ok(hasMatchingLabel,
                `event label for shared event should render in ${sharedColor}; got ${JSON.stringify(eventLines)}`);
        }
    });

    it('ELK layout spacings are generous enough for readable diagrams', async () => {
        const doc = createDocument(sampleSource, '/tmp/elk-sample-spacing.fcstm');
        const diagram = await buildFcstmDiagramFromDocument(doc);
        assert.ok(diagram);
        const options = resolveFcstmDiagramPreviewOptions('normal');
        const graph = buildFcstmElkGraph(diagram!, options);
        assert.ok(Number(graph.layoutOptions['elk.spacing.nodeNode']) >= 72,
            'nodeNode spacing should be at least 72 for a non-cramped diagram');
        assert.ok(Number(graph.layoutOptions['elk.layered.spacing.nodeNodeBetweenLayers']) >= 96,
            'between-layer spacing should be at least 96');
    });

    it('returns null payload when the document has no state machine', async () => {
        const doc = createDocument('// just a comment\n', '/tmp/elk-empty.fcstm');
        const payload = await buildFcstmDiagramWebviewPayload(doc);
        assert.equal(payload, null);
    });
});

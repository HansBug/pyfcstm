import assert from 'node:assert/strict';
import * as path from 'node:path';

import {
    createDocument,
    packageModule,
    trackTempDir,
    writeFile,
} from './support';

describe('jsfcstm diagram preview', () => {
    afterEach(() => {
        packageModule.getWorkspaceGraph().clearOverlays();
    });

    const zeroRange = {
        start: {line: 0, character: 0},
        end: {line: 0, character: 0},
    };

    it('builds diagram IR with hierarchy, shared-event coloring, and transition semantics', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state TrafficLight {',
            '    event Tick named "Cycle";',
            '    enter Setup {',
            '        counter = 0;',
            '    }',
            '    state Idle;',
            '    state Running;',
            '    state Done;',
            '    [*] -> Idle;',
            '    Idle -> Running : Tick effect {',
            '        counter = counter + 1;',
            '    };',
            '    Running -> Done : Tick;',
            '    Done -> [*] : if [counter > 0];',
            '}',
        ].join('\n'), '/tmp/diagram-model.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const model = packageModule.buildStateMachineModel(ast);
        const diagram = packageModule.buildFcstmDiagramFromStateMachine(model);

        assert.ok(diagram);
        assert.equal(diagram!.machineName, 'TrafficLight');
        assert.deepEqual(diagram!.summary, {
            variables: 1,
            states: 4,
            events: 1,
            transitions: 4,
            actions: 1,
        });
        assert.equal(diagram!.variables[0].name, 'counter');
        assert.equal(diagram!.rootState.children.length, 3);
        assert.equal(diagram!.rootState.events[0].qualifiedName, 'TrafficLight.Tick');
        assert.equal(diagram!.rootState.actions[0].label, 'enter Setup');
        assert.equal(diagram!.eventLegend.length, 1);
        assert.equal(diagram!.eventLegend[0].qualifiedName, 'TrafficLight.Tick');
        assert.equal(diagram!.eventLegend[0].label, 'Cycle (Tick)');
        assert.equal(diagram!.eventLegend[0].transitionCount, 2);
        assert.equal(diagram!.rootState.transitions[1].triggerLabel, ': Cycle (Tick)');
        assert.equal(diagram!.rootState.transitions[1].label, 'Idle -> Running : Cycle (Tick) effect');
        assert.deepEqual(diagram!.rootState.transitions[1].effectLines, [
            'effect {',
            '    counter=counter+1;',
            '}',
        ]);
        assert.equal(diagram!.rootState.transitions[1].eventColor, diagram!.rootState.transitions[2].eventColor);
        assert.ok(diagram!.rootState.transitions[1].eventColor);
        assert.equal(diagram!.rootState.transitions[3].guardLabel, 'counter>0');
    });

    it('renders an SVG statechart with escaped labels, arrows, markers, notes, and legend panels', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root named "Root <Main>" {',
            '    event Start named "Go & Run";',
            '    state Idle;',
            '    state Running;',
            '    [*] -> Idle;',
            '    Idle -> Running : Start effect {',
            '        counter = counter + 1;',
            '    };',
            '    Running -> [*] : Start;',
            '}',
        ].join('\n'), '/tmp/diagram-svg.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const model = packageModule.buildStateMachineModel(ast);
        const diagram = packageModule.buildFcstmDiagramFromStateMachine(model);
        const svg = await packageModule.renderFcstmDiagramSvg(diagram!);

        assert.match(svg, /<svg[\s\S]*FCSTM preview for Root/);
        assert.match(svg, /Root &lt;Main&gt; \(Root\)/);
        assert.match(svg, /Go &amp; Run/);
        assert.match(svg, /class="fcstm-panel fcstm-variable-panel"/);
        assert.match(svg, /class="fcstm-panel fcstm-event-legend"/);
        assert.match(svg, /class="fcstm-start-node"/);
        assert.match(svg, /class="fcstm-end-node-ring"/);
        assert.match(svg, /class="fcstm-transition-path"/);
        assert.match(svg, /class="fcstm-transition-label-box"/);
        assert.match(svg, /class="fcstm-transition-note-box"/);
        assert.match(svg, /: Go &amp; Run \(Start\)/);
        assert.match(svg, /effect \{/);
        assert.match(svg, /counter=counter\+1;/);
    });

    it('covers builder fallbacks for null models, missing legend lookups, forced labels, and empty effect bodies', () => {
        assert.equal(packageModule.buildFcstmDiagramFromStateMachine(null), null);

        const repeatedEvent = {
            name: 'Missing',
            pathName: 'Root.Missing',
            extraName: undefined,
            declared: false,
            origins: ['chain'],
            statePath: ['Elsewhere'],
            path: ['Root', 'Missing'],
            range: zeroRange,
        };
        const singleEvent = {
            name: 'Solo',
            pathName: 'Root.Solo',
            extraName: undefined,
            declared: false,
            origins: ['absolute'],
            statePath: ['Root'],
            path: ['Root', 'Solo'],
            range: zeroRange,
        };
        const enterRefAction = {
            name: undefined,
            statePath: ['Root', null],
            stage: 'enter',
            aspect: undefined,
            mode: 'ref',
            is_abstract: false,
            is_ref: true,
            is_aspect: false,
            operations: [],
            funcName: 'FallbackFunc',
            refStatePath: ['Root', 'Shared'],
            refTargetQualifiedName: undefined,
            range: zeroRange,
        };
        const emptyDuringAction = {
            name: undefined,
            statePath: ['Root'],
            stage: 'during',
            aspect: undefined,
            mode: 'operations',
            is_abstract: false,
            is_ref: false,
            is_aspect: false,
            operations: [],
            funcName: 'Root.during',
            refStatePath: undefined,
            refTargetQualifiedName: undefined,
            range: zeroRange,
        };
        const aspectAction = {
            name: undefined,
            statePath: ['Root'],
            stage: 'during',
            aspect: 'before',
            mode: 'abstract',
            is_abstract: true,
            is_ref: false,
            is_aspect: true,
            operations: [],
            funcName: 'Watcher',
            refStatePath: undefined,
            refTargetQualifiedName: undefined,
            range: zeroRange,
        };
        const transitions = [
            {
                fromState: 'A',
                toState: 'B',
                event: repeatedEvent,
                guard: undefined,
                effects: [{text: ''}],
                parentPath: ['Root'],
                sourceKind: 'state',
                targetKind: 'state',
                forced: true,
                sourceStatePath: ['Root', 'A'],
                targetStatePath: ['Root', 'B'],
                triggerScope: 'chain',
                range: zeroRange,
            },
            {
                fromState: 'B',
                toState: 'C',
                event: repeatedEvent,
                guard: undefined,
                effects: [],
                parentPath: ['Root'],
                sourceKind: 'state',
                targetKind: 'state',
                forced: false,
                sourceStatePath: ['Root', 'B'],
                targetStatePath: ['Root', 'C'],
                triggerScope: 'chain',
                range: zeroRange,
            },
            {
                fromState: 'C',
                toState: 'EXIT_STATE',
                event: singleEvent,
                guard: undefined,
                effects: [],
                parentPath: ['Root'],
                sourceKind: 'state',
                targetKind: 'exit',
                forced: false,
                sourceStatePath: ['Root', 'C'],
                targetStatePath: undefined,
                triggerScope: 'absolute',
                range: zeroRange,
            },
        ];
        const machine = {
            filePath: '/tmp/stub.fcstm',
            defines: {},
            allStates: [{}, {}, {}],
            allEvents: [repeatedEvent, singleEvent],
            allTransitions: transitions,
            allActions: [enterRefAction, emptyDuringAction, aspectAction],
            lookups: {eventsByPathName: {}},
            rootState: {
                name: 'Root',
                pathName: 'Root',
                extraName: undefined,
                isPseudo: false,
                isLeafState: false,
                isRootState: true,
                range: zeroRange,
                events: {},
                onEnters: [enterRefAction],
                onDurings: [emptyDuringAction],
                onExits: [],
                onDuringAspects: [aspectAction],
                transitions,
                substates: {},
            },
        };

        const diagram = packageModule.buildFcstmDiagramFromStateMachine(machine as never);

        assert.ok(diagram);
        assert.equal(diagram!.eventLegend.length, 1);
        assert.equal(diagram!.eventLegend[0].label, 'Missing');
        assert.equal(diagram!.rootState.actions[0].qualifiedName, 'Root.<unnamed>');
        assert.equal(diagram!.rootState.actions[0].label, 'enter ref Root.Shared');
        assert.equal(diagram!.rootState.actions[1].label, 'during {}');
        assert.equal(diagram!.rootState.actions[2].label, '>> during before abstract Watcher');
        assert.equal(diagram!.rootState.transitions[0].label, '! A -> B : /Missing effect');
        assert.deepEqual(diagram!.rootState.transitions[0].effectLines, [
            'effect {',
            '    ...',
            '}',
        ]);
        assert.equal(diagram!.rootState.transitions[2].triggerLabel, ': /Solo');
        assert.equal(
            packageModule.formatFcstmDiagramTransitionLabel('A', 'B', ': /Solo', 'x>0', false, true),
            '! A -> B : /Solo if [x>0]'
        );
    });

    it('renders synthetic diagrams that cover self-loops, skipped links, vertical routing, and memory subtitles', async () => {
        const leafState = (name: string) => ({
            id: `Root.${name}`,
            name,
            qualifiedName: `Root.${name}`,
            pseudo: false,
            leaf: true,
            root: false,
            range: zeroRange,
            events: [],
            actions: [],
            transitions: [],
            children: [],
        });
        const diagram = {
            kind: 'diagram',
            filePath: '',
            machineName: 'Synthetic',
            summary: {
                variables: 0,
                states: 6,
                events: 0,
                transitions: 5,
                actions: 0,
            },
            variables: [],
            eventLegend: [],
            rootState: {
                id: 'Root',
                name: 'Root',
                qualifiedName: 'Root',
                pseudo: false,
                leaf: false,
                root: true,
                range: zeroRange,
                events: [],
                actions: [],
                children: ['A', 'B', 'C', 'D', 'E'].map(leafState),
                transitions: [
                    {
                        id: 'init',
                        sourceLabel: '[*]',
                        targetLabel: 'A',
                        label: '[*] -> A',
                        effectLines: [],
                        forced: false,
                        sourceKind: 'init',
                        targetKind: 'state',
                        range: zeroRange,
                    },
                    {
                        id: 'self',
                        sourceLabel: 'A',
                        targetLabel: 'A',
                        label: 'A -> A',
                        triggerLabel: ': Ping',
                        guardLabel: 'x>0',
                        effectLines: [],
                        forced: true,
                        sourceKind: 'state',
                        targetKind: 'state',
                        range: zeroRange,
                    },
                    {
                        id: 'vertical',
                        sourceLabel: 'B',
                        targetLabel: 'E',
                        label: 'B -> E',
                        effectLines: [],
                        forced: false,
                        sourceKind: 'state',
                        targetKind: 'state',
                        range: zeroRange,
                    },
                    {
                        id: 'exit',
                        sourceLabel: 'C',
                        targetLabel: '[*]',
                        label: 'C -> [*]',
                        effectLines: [],
                        forced: false,
                        sourceKind: 'state',
                        targetKind: 'exit',
                        range: zeroRange,
                    },
                    {
                        id: 'skip',
                        sourceLabel: 'Ghost',
                        targetLabel: 'Missing',
                        label: 'Ghost -> Missing',
                        effectLines: [],
                        forced: false,
                        sourceKind: 'state',
                        targetKind: 'state',
                        range: zeroRange,
                    },
                ],
            },
        };

        const svg = await packageModule.renderFcstmDiagramSvg(diagram as never, {
            minWidth: 640,
        });

        assert.match(svg, /&lt;memory&gt;/);
        assert.ok(!svg.includes('fcstm-variable-panel'));
        assert.ok(!svg.includes('fcstm-event-legend'));
        assert.match(svg, /forced transition/);
        assert.match(svg, /if \[x&gt;0\]/);
        assert.match(svg, /class="fcstm-start-node"/);
        assert.match(svg, /class="fcstm-end-node-ring"/);
        assert.match(svg, /data-state-id="Root\.E"/);
        assert.doesNotMatch(svg, /Ghost -&gt; Missing/);
    });

    it('builds diagram IR from documents while honoring imported-file overlays', async () => {
        const dir = trackTempDir('jsfcstm-diagram-overlay-');
        const hostFile = path.join(dir, 'main.fcstm');
        const workerFile = path.join(dir, 'modules', 'motor.fcstm');
        const hostText = [
            'state Fleet {',
            '    import "./modules/motor.fcstm" as LeftMotor;',
            '    [*] -> LeftMotor;',
            '}',
        ].join('\n');

        writeFile(hostFile, hostText);
        writeFile(workerFile, [
            'state MotorRoot {',
            '    state Idle;',
            '}',
        ].join('\n'));

        const graph = packageModule.getWorkspaceGraph();
        graph.setOverlay(workerFile, [
            'state MotorRoot {',
            '    state Idle;',
            '    state Running;',
            '    [*] -> Idle;',
            '    Idle -> Running;',
            '}',
        ].join('\n'));

        const diagram = await packageModule.buildFcstmDiagramFromDocument(
            createDocument(hostText, hostFile)
        );

        assert.ok(diagram);
        assert.equal(diagram!.rootState.children.length, 1);
        assert.equal(diagram!.rootState.children[0].name, 'LeftMotor');
        assert.deepEqual(
            diagram!.rootState.children[0].children.map(child => child.name),
            ['Idle', 'Running']
        );
        assert.equal(diagram!.rootState.children[0].transitions[1].label, 'Idle -> Running');
    });
});

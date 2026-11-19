import assert from 'node:assert/strict';

import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir, writeFile} from './support';
import {
    buildFcstmDiagramFromDocument,
    buildFcstmDiagramFromWorkspaceSnapshot,
    buildFcstmElkGraph,
    resolveFcstmDiagramPreviewOptions,
} from '@pyfcstm/jsfcstm/diagram';
import type {FcstmDiagramState} from '../src/diagram/model';

const SOURCE = `
input int fault;
input int requested;
control int permit = 0;
output int motor = 0;

state Controller {
    event Start;
    [*] -> Idle;
    state Idle;
    state Running {
        region Safety {
            [*] -> Normal;
            state Normal;
            state Tripped;
            Normal -> Tripped : if [fault != 0];
        }
        region Motion {
            [*] -> Off;
            state Off;
            state On;
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [active("/Running.Safety.Tripped")];
            Off -> On : if [!active("Controller.Running.Safety.Normal") || active( "Controller.Running.Safety.Tripped" )];
        }
    }
    Idle -> Running : /Start;
}
`;

async function build(source: string = SOURCE) {
    const diagram = await buildFcstmDiagramFromDocument(createDocument(source, '/tmp/region-diagram.fcstm'));
    assert.ok(diagram);
    return diagram!;
}

function find(state: FcstmDiagramState, name: string): FcstmDiagramState {
    if (state.qualifiedName === name) return state;
    for (const child of state.children) {
        const found = child.qualifiedName === name || name.startsWith(`${child.qualifiedName}.`)
            ? find(child, name) : undefined;
        if (found) return found;
    }
    throw new Error(`no node ${name}`);
}

describe('region diagram snapshot', () => {
    it('lists the regions of a state as ordered child sections', async () => {
        const diagram = await build();
        const running = find(diagram.rootState, 'Controller.Running');
        assert.deepEqual(running.children.map(child => [child.name, child.region, child.ordinal]),
            [['Safety', true, 1], ['Motion', true, 2]]);
        assert.equal(running.leaf, false);
        assert.deepEqual(find(running, 'Controller.Running.Safety').children.map(child => child.name),
            ['Normal', 'Tripped']);
    });

    it('does not mark ordinary states as regions', async () => {
        const diagram = await build();
        const idle = find(diagram.rootState, 'Controller.Idle');
        assert.equal(idle.region, undefined);
        assert.equal(idle.ordinal, undefined);
        assert.equal('region' in idle, false);
    });

    it('counts states without regions and transitions with them', async () => {
        const diagram = await build();
        assert.equal(diagram.summary.states, 7);
        assert.equal(diagram.summary.transitions, 8);
    });

    it('shows the full path of every active query in a guard', async () => {
        const diagram = await build();
        const motion = find(diagram.rootState, 'Controller.Running.Motion');
        const labels = motion.transitions.map(item => item.label);
        assert.ok(labels.some(label => label.includes('if [active("Controller.Running.Safety.Tripped")]')), labels.join('\n'));
        assert.ok(labels.some(label => label.includes(
            'if [!active("Controller.Running.Safety.Normal")||active("Controller.Running.Safety.Tripped")]')), labels.join('\n'));
        assert.ok(labels.some(label => label.includes('if [permit!=0&&requested!=0]')));
    });

    it('titles each region section with its execution position', async () => {
        const diagram = await build();
        const graph = buildFcstmElkGraph(diagram, resolveFcstmDiagramPreviewOptions('normal'));
        const titles: string[] = [];
        const visit = (node: any): void => {
            if (node.fcstm?.region) titles.push(node.fcstm.title ?? node.labels?.[0]?.text);
            (node.children ?? []).forEach(visit);
        };
        visit(graph);
        assert.equal(titles.length, 2);
        assert.ok(titles[0].includes('region 1: Safety'), titles[0]);
        assert.ok(titles[1].includes('region 2: Motion'), titles[1]);
    });

    it('shows active queries in effects with the full path of the state they name', async () => {
        const diagram = await build(`def int x = 0;
            state Root {
                state A { state P; [*] -> P; }
                state B;
                [*] -> A;
                A -> B effect {
                    if [active("Root.A.P")] { x = 1; }
                    else if [!active("/B")] { x = (active("Root.A.P")) ? 2 : 3; }
                    else { x = 4; }
                }
            }`);
        const effect = diagram.rootState.transitions.find(item => item.effectLines.length > 0)!.effectLines;
        assert.deepEqual(effect.filter(line => /active/.test(line)), [
            '    if [active("Root.A.P")] {',
            '    else if [!active("Root.B")] {',
            '        x=(active("Root.A.P"))?2:3;',
        ]);
    });

    it('shows the instance path for the queries of an imported module, in guards and effects', async () => {
        const directory = trackTempDir('jsfcstm-region-diagram-import-');
        const module = path.join(directory, 'module.fcstm');
        const host = path.join(directory, 'host.fcstm');
        writeFile(module, `def int y = 0; state Sub {
            region A { [*] -> X; state X; state Y; X -> Y : if [active("/A.X")];
                Y -> X effect { if [active("Sub.A.Y")] { y = 1; } } }
            region B { [*] -> Z; state Z; Z -> Z : if [active("Sub.A.Y")]; }
        }`);
        writeFile(host, 'def int y = 0; state Host { import "module.fcstm" as Mod; [*] -> Mod; }');
        const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
        const diagram = buildFcstmDiagramFromWorkspaceSnapshot(snapshot, host)!;
        assert.ok(diagram);
        const transitions: Array<{label: string; effectLines: string[]}> = [];
        const visit = (state: FcstmDiagramState): void => {
            transitions.push(...state.transitions);
            state.children.forEach(visit);
        };
        visit(diagram.rootState);
        assert.deepEqual(transitions.filter(item => /active/.test(item.label)).map(item => item.label).sort(), [
            'X -> Y if [active("Host.Mod.A.X")]',
            'Z -> Z if [active("Host.Mod.A.Y")]',
        ]);
        assert.ok(transitions.some(item => item.effectLines.includes('        if [active("Host.Mod.A.Y")] {')
            || item.effectLines.includes('    if [active("Host.Mod.A.Y")] {')));
    });

    it('resolves an absolute event path of a region transition in an imported module', async () => {
        const directory = trackTempDir('jsfcstm-region-diagram-event-');
        const module = path.join(directory, 'm.fcstm');
        const host = path.join(directory, 'h.fcstm');
        writeFile(module, `state M { region R { event Tick; state On; state Off; [*] -> On;
            On -> Off : /R.Tick; Off -> On : Tick; } }`);
        writeFile(host, 'state Root { import "./m.fcstm" as A; [*] -> A; }');
        const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
        const diagram = buildFcstmDiagramFromWorkspaceSnapshot(snapshot, host)!;
        assert.ok(diagram);
        const events: Array<string | undefined> = [];
        const visit = (state: FcstmDiagramState): void => {
            events.push(...state.transitions.map(item => item.eventQualifiedName));
            state.children.forEach(visit);
        };
        visit(diagram.rootState);
        assert.deepEqual(events.filter(Boolean), ['Root.A.R.Tick', 'Root.A.R.Tick']);
        assert.deepEqual(diagram.eventLegend.map(item => [item.qualifiedName, item.transitionCount]), [['Root.A.R.Tick', 2]]);
    });
});


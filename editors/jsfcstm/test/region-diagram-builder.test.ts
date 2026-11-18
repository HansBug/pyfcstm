import assert from 'node:assert/strict';

import {createDocument} from './support';
import {
    buildFcstmDiagramFromDocument,
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
});

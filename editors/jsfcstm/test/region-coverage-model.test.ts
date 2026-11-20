import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir, writeFile} from './support';

async function model(source: string, filePath: string = '/tmp/region-coverage-model.fcstm') {
    const ast = await packageModule.parseAstDocument(createDocument(source, filePath));
    assert.ok(ast);
    const result = packageModule.buildStateMachineModel(ast!);
    assert.ok(result);
    return result!;
}

async function importedModel(moduleText: string, hostText: string) {
    const directory = trackTempDir('jsfcstm-region-coverage-');
    const host = path.join(directory, 'host.fcstm');
    writeFile(path.join(directory, 'module.fcstm'), moduleText);
    writeFile(host, hostText);
    const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
    const machine = snapshot.nodes[host].model;
    assert.ok(machine);
    return machine!;
}

describe('guards of forced transitions are echoed in canonical form', () => {
    const SOURCE = `
def int x = 0;
def int y = 0;
def float f = 0.0;
state Root {
    state A;
    state B;
    state Err;
    [*] -> A;
    A -> B : if [x > 0];
    !A -> Err : if [x - (y - 1) > 0];
    !A -> Err : if [((x > 0) ? ((y > 0) ? 1 : 2) : ((y > 1) ? 3 : 4)) > 0];
    !A -> Err : if [((x > 0) ? 1 : 2) > 0];
    !A -> Err : if [abs(x) > 1 && f < 1.5];
    !A -> Err : if [f > pi];
    !B -> Err : if [true];
    !B -> Err : if [false];
}`;

    it('parenthesises right operands, nested conditionals and keeps functions, floats and booleans', async () => {
        const machine = await model(SOURCE);
        const guards = machine.forcedTransitions.map(item => item.guard);
        assert.deepEqual(guards, [
            'x - (y - 1) > 0',
            '((x > 0) ? ((y > 0) ? 1 : 2) : ((y > 1) ? 3 : 4)) > 0',
            '((x > 0) ? 1 : 2) > 0',
            'abs(x) > 1 && f < 1.5',
            'f > pi',
            'true',
            'false',
        ]);
        assert.equal(machine.forcedTransitions[0].originalRaw, '! A -> Err : if [x - (y - 1) > 0];');
    });
});

describe('event references resolve through scopes', () => {
    it('finds an event owned by a uniquely named state elsewhere in the machine', async () => {
        const machine = await model(`
state Root {
    state A { state Deep; [*] -> Deep; }
    state C;
    [*] -> C;
    C -> A : Deep.Go;
}`);
        const transition = machine.allTransitions.find(item => item.event);
        assert.equal(transition?.event?.pathName, 'Root.A.Deep.Go');
        assert.equal(machine.resolve_event('Root.A.Deep.Go').name, 'Go');
    });

    it('does not pick an event owner when a state name is ambiguous', async () => {
        const machine = await model(`
state Root {
    state A { state Twin; [*] -> Twin; }
    state B { state Twin; [*] -> Twin; }
    state C;
    [*] -> C;
    C -> A : Twin.Go;
}`);
        const transition = machine.allTransitions.find(item => item.event);
        assert.equal(transition?.event, undefined);
    });
});

describe('event lookup on the runtime model', () => {
    const SOURCE = `
state Root {
    event Top;
    state Run {
        event Local;
        region Left { event Tick; state L; [*] -> L; }
        region Right { state R; [*] -> R; }
    }
    state Idle;
    [*] -> Idle;
    Idle -> Run :: Go;
    Run -> Idle : Back;
}`;

    it('resolves absolute, relative and parent-relative references from a state', async () => {
        const machine = await model(SOURCE);
        const run = machine.rootState.substates.Run;
        const left = run.regions.Left;
        assert.equal(run.resolve_event('/Top').pathName, 'Root.Top');
        assert.equal(run.resolve_event('/Run.Local').pathName, 'Root.Run.Local');
        assert.equal(run.resolve_event('/Run.Left.Tick').pathName, 'Root.Run.Left.Tick');
        assert.equal(run.resolve_event('Left.Tick').pathName, 'Root.Run.Left.Tick');
        assert.equal(run.resolve_event('Local').pathName, 'Root.Run.Local');
        assert.equal(left.resolve_event('.Local').pathName, 'Root.Run.Local');
        assert.equal(left.resolve_event('..Top').pathName, 'Root.Top');
    });

    it('rejects malformed references with a precise message', async () => {
        const machine = await model(SOURCE);
        const run = machine.rootState.substates.Run;
        assert.throws(() => run.resolve_event(''), /Event reference cannot be empty/);
        assert.throws(() => run.resolve_event('/'), /cannot be just "\/"/);
        assert.throws(() => run.resolve_event('/Run..Local'), /Invalid absolute event reference/);
        assert.throws(() => run.resolve_event('.'), /cannot end with dots/);
        assert.throws(() => run.resolve_event('...Top'), /goes beyond root state/);
        assert.throws(() => run.resolve_event('.Run..Local'), /Invalid parent-relative event reference/);
        assert.throws(() => run.resolve_event('Left..Tick'), /Invalid relative event reference/);
        assert.throws(() => run.resolve_event('Nowhere.Tick'), /State "Root.Run.Nowhere" not found/);
        assert.throws(() => run.resolve_event('Missing'), /Event "Missing" not found in state "Root.Run"/);
    });

    it('resolves fully-qualified paths on the machine and rejects bad ones', async () => {
        const machine = await model(SOURCE);
        assert.equal(machine.resolve_event('Root.Run.Left.Tick').name, 'Tick');
        assert.throws(() => machine.resolve_event(''), /Event path cannot be empty/);
        assert.throws(() => machine.resolve_event('Tick'), /Invalid event path/);
        assert.throws(() => machine.resolve_event('Root..Tick'), /Invalid event path/);
        assert.throws(() => machine.resolve_event('Other.Tick'), /does not match state machine root/);
        assert.throws(() => machine.resolve_event('Root.Nowhere.Tick'), /State "Nowhere" not found/);
        assert.throws(() => machine.resolve_event('Root.Run.Missing'), /Event "Missing" not found/);
    });
});

describe('combo triggers declared in interleaved order', () => {
    it('groups later alternatives of the same source around the first one', async () => {
        const machine = await model(`
def int c = 0;
def int d = 0;
state Root {
    state A;
    state B;
    state X;
    state Y;
    [*] -> A;
    A -> X : E1 + [c > 0];
    B -> Y : E2 + [c > 0];
    A -> X : E1 + [d > 0];
}`);
        const fromA = machine.rootState.transitions.filter(item => item.fromState === 'A');
        const fromB = machine.rootState.transitions.filter(item => item.fromState === 'B');
        assert.equal(fromA.length, 1);
        assert.equal(fromB.length, 1);
        const relayStates = Object.keys(machine.rootState.substates).filter(name => name.startsWith('__combo_'));
        assert.equal(relayStates.length, 2);
    });
});

describe('imported modules with lifecycle actions in every position', () => {
    const MODULE = `
def int counter = 0;
state Worker {
    event Ping;
    enter Boot { counter = 1; }
    exit Cleanup { counter = counter - 1; }
    exit abstract Notify;
    exit ref /Cleanup;
    >> during before Prep { counter = counter + 1; }
    >> during after abstract Observe;
    >> during after ref /Prep;
    state Idle {
        exit Drain { counter = 0; }
        >> during before Warm { counter = counter + 2; }
        exit ref /Cleanup;
    }
    state Busy;
    [*] -> Idle;
    Idle -> Busy :: Go;
    !Busy -> Idle : /Ping;
    !Busy -> Idle : if [counter > 3];
}`;

    it('maps variables and prefixes absolute paths in exits, aspects and forced transitions', async () => {
        const machine = await importedModel(MODULE, `
def int total = 0;
state Host {
    import "./module.fcstm" as Mod { def counter -> total; }
    [*] -> Mod;
}`);
        const worker = machine.rootState.substates.Mod;
        assert.ok(worker);
        const targets = (items: any[]) => items.flatMap(item => (item.operations ?? []).map((op: any) => op.varName));
        assert.deepEqual(targets(worker.onEnters), ['total']);
        assert.deepEqual(targets(worker.onExits), ['total']);
        assert.deepEqual(targets(worker.onDuringAspects), ['total']);
        assert.deepEqual(targets(worker.substates.Idle.onExits), ['total']);
        assert.deepEqual(targets(worker.substates.Idle.onDuringAspects), ['total']);
        const refTargets = (items: any[]) => items.filter(item => item.isRef).map(item => item.refTargetQualifiedName);
        assert.deepEqual(refTargets(worker.onExits), ['Host.Mod.Cleanup']);
        assert.deepEqual(refTargets(worker.onDuringAspects), ['Host.Mod.Prep']);
        assert.deepEqual(refTargets(worker.substates.Idle.onExits), ['Host.Mod.Cleanup']);
        const forced = machine.forcedTransitions.map(item => [item.fromPath, item.toPath, item.event, item.guard]);
        assert.deepEqual(forced, [
            ['Host.Mod.Busy', 'Host.Mod.Idle', 'Host.Mod.Ping', undefined],
            ['Host.Mod.Busy', 'Host.Mod.Idle', undefined, 'total > 3'],
        ]);
    });
});

describe('imports that cannot be resolved', () => {
    it('leaves the machine buildable when an import target file is missing', async () => {
        const machine = await importedModel('state Unused;', `
state Host {
    state A;
    import "./missing.fcstm" as Missing;
    [*] -> A;
}`);
        assert.deepEqual(Object.keys(machine.rootState.substates), ['A']);
    });
});

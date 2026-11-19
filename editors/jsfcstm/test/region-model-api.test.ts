import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, editorModule, packageModule, trackTempDir, writeFile} from './support';
import {buildFcstmDiagramFromDocument, buildFcstmElkGraph, resolveFcstmDiagramPreviewOptions} from '@pyfcstm/jsfcstm/diagram';

const SOURCE = `
def int x = 0;
state Root {
    state Run {
        region Safety {
            [*] -> Normal;
            state Normal;
            state Tripped;
            Normal -> Tripped : if [x != 0];
        }
        region Motion {
            [*] -> Off;
            state Off;
            state On { region Inner { [*] -> Deep; state Deep; } }
            Off -> On : if [((active("Root.Run.Safety.Tripped")) ? 1 : 0) > 0];
            On -> Off : if [!active("Root.Run.Safety.Normal") && !active("Missing.Path")];
        }
    }
    state Idle;
    [*] -> Idle;
    Idle -> Run : if [True];
}`;

async function model(source: string = SOURCE) {
    const ast = await packageModule.parseAstDocument(createDocument(source, '/tmp/region-model.fcstm'));
    const result = packageModule.buildStateMachineModel(ast!);
    assert.ok(result);
    return result!;
}

describe('region model access', () => {
    it('walks regions in declaration order, outer before inner, and states without regions', async () => {
        const machine = await model();
        assert.deepEqual([...machine.walk_regions()].map(item => item.pathName), [
            'Root.Run.Safety', 'Root.Run.Motion', 'Root.Run.Motion.On.Inner']);
        assert.equal(machine.has_regions, true);
        assert.deepEqual([...machine.walk_states()].map(item => item.name),
            ['Root', 'Run', 'Normal', 'Tripped', 'Off', 'On', 'Deep', 'Idle']);
    });

    it('reports no regions for a machine without them', async () => {
        const machine = await model('state Root { state A; [*] -> A; }');
        assert.equal(machine.has_regions, false);
        assert.deepEqual([...machine.walk_regions()], []);
    });

    it('looks up an immediate child scope as a state first and a region second', async () => {
        const machine = await model();
        const run = machine.rootState.substates.Run;
        assert.equal(run.namespace_child('Safety')?.isRegion, true);
        assert.equal(machine.rootState.namespace_child('Idle')?.isRegion, false);
        assert.equal(run.namespace_child('Nothing'), undefined);
    });

    it('exports a state with regions back to an AST that declares the regions in order', async () => {
        const machine = await model();
        const node = machine.rootState.substates.Run.to_ast_node();
        assert.deepEqual(node.regions.map(item => item.name), ['Safety', 'Motion']);
        const motion = node.regions[1];
        assert.deepEqual(motion.substates.map(item => item.name), ['Off', 'On']);
        assert.equal(motion.transitions.length, 3);
        assert.equal(motion.substates[1].regions[0].name, 'Inner');
    });

    it('keeps an unresolved query as written and shows resolved ones with their full path', async () => {
        const machine = await model();
        const guards = machine.allTransitions.filter(item => item.guard).map(item => item.guard!);
        const texts = guards.map(item => packageModule.resolvedExprText(item));
        assert.ok(texts.some(text => text.includes('active("Root.Run.Safety.Tripped")')), texts.join('\n'));
        assert.ok(texts.some(text => text.includes('!active("Root.Run.Safety.Normal")&&!active("Missing.Path")')), texts.join('\n'));
        const queries = (function collect(expr: any): any[] {
            if (expr.constructor.name === 'ActiveStateQuery') return [expr];
            return [expr.x, expr.y, expr.cond, expr.ifTrue, expr.ifFalse].filter(Boolean).flatMap(collect);
        })(guards[guards.length - 1]);
        const query = queries.find(item => item.path === 'Missing.Path');
        assert.equal(query.statePath, null);
        assert.equal(query.to_ast_node().path, 'Missing.Path');
    });

    const unresolved: Array<[string, string]> = [
        ['/Run.Safety', 'a path naming a region'],
        ['Root.Idle.', 'an empty segment'],
        ['Other.Idle', 'a wrong root'],
        ['Root.Absent', 'an unknown state'],
        ['/Run.Safety.Normal', 'a root-relative path'],
    ];
    for (const [written, label] of unresolved) {
        it(`binds ${written} (${label}) only when it names a state`, async () => {
            const machine = await model(`state Root { state Run { region Safety { [*] -> Normal; state Normal; } } state Idle;
                [*] -> Idle; Idle -> Run : if [active("${written}")]; }`);
            const guard = machine.allTransitions.find(item => item.guard)!.guard as any;
            const expectResolved = written === '/Run.Safety.Normal';
            assert.deepEqual(guard.statePath, expectResolved ? ['Root', 'Run', 'Safety', 'Normal'] : null);
        });
    }

    it('does not bind a query to a pseudo state', async () => {
        const machine = await model(`state Root { pseudo state P; state Idle; [*] -> Idle; Idle -> P : if [active("Root.P")]; }`);
        assert.equal((machine.allTransitions.find(item => item.guard)!.guard as any).statePath, null);
    });
});

describe('region analysis of owners and roots', () => {
    async function codes(source: string) {
        const document = createDocument(source, '/tmp/region-analysis.fcstm');
        const ast = await packageModule.parseAstDocument(document);
        return editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(
            packageModule.buildSemanticDocument(ast!)!, document).map(item => item.code);
    }

    it('accepts a root that is itself the parallel owner', async () => {
        assert.deepEqual(await codes(
            'state Root { region A { state X; [*] -> X; } region B { state Y; [*] -> Y; X2 } }'.replace(' X2', '')), []);
    });

    it('reports a state that only an unreachable region path could reach', async () => {
        const found = await codes(
            'state Root { region A { state X; state Dead; [*] -> X; } region B { state Y; [*] -> Y; } }');
        assert.deepEqual(found, ['W_UNREACHABLE_STATE']);
    });

    it('gives a state in a region its own initial transition requirement', async () => {
        const found = await codes(
            'state Root { region A { state X { state C; } [*] -> X; } }');
        assert.deepEqual(found, ['W_UNREACHABLE_STATE', 'E_INITIAL_TRANSITION_INVALID']);
    });

    it('does not let a forced transition of the owner reach into regions', async () => {
        const found = await codes(`state Root { state P { region A { state X; [*] -> X; } region B { state Y; [*] -> Y; } }
            state Q; [*] -> P; ! P -> Q :: Go; }`);
        assert.deepEqual(found, []);
    });
});

describe('imported modules with regions', () => {
    it('rebases the active queries of an imported module onto its instance path', async () => {
        const directory = trackTempDir('jsfcstm-region-import-');
        const module = path.join(directory, 'module.fcstm');
        const host = path.join(directory, 'host.fcstm');
        writeFile(module, `state Sub {
            region A { [*] -> X; state X; state Y; X -> Y : if [active("/A.X")]; Y -> X : if [active("Sub.A.X")]; }
            region B { [*] -> Z; state Z; Z -> Z : if [active("Elsewhere.Z")]; }
        }`);
        writeFile(host, 'state Host { import "module.fcstm" as Mod; [*] -> Mod; }');
        const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
        const machine = snapshot.nodes[host].model!;
        assert.ok(machine);
        const texts = machine.allTransitions.filter(item => item.guard).map(item => packageModule.resolvedExprText(item.guard!));
        assert.equal(texts.filter(text => text === 'active("Host.Mod.A.X")').length, 2, texts.join('\n'));
        assert.ok(texts.includes('active("Elsewhere.Z")'));
        assert.equal(machine.rootState.substates.Mod.regions.A.isRegion, true);
    });
});

describe('region titles in the diagram graph', () => {
    it('keeps the display name of an ordinary state next to a region title', async () => {
        const diagram = await buildFcstmDiagramFromDocument(createDocument(
            `state Root { state P named "Parent" { region A { state X; [*] -> X; } } [*] -> P; }`, '/tmp/named.fcstm'));
        const graph = buildFcstmElkGraph(diagram!, resolveFcstmDiagramPreviewOptions('normal'));
        const text = JSON.stringify(graph);
        assert.ok(text.includes('Parent (P)'));
        assert.ok(text.includes('region 1: A'));
    });

    it('numbers the regions of the semantic document from one, like the model', async () => {
        const ast = await packageModule.parseAstDocument(createDocument(SOURCE, '/tmp/region-semantic.fcstm'));
        const regions = packageModule.buildSemanticDocument(ast!)!.states.filter(item => item.isRegion);
        assert.deepEqual(regions.map(item => [item.name, item.ordinal]), [['Safety', 1], ['Motion', 2], ['Inner', 1]]);
    });
});

describe('history inside regions', () => {
    const HISTORY_SOURCE = `state Root { state P {
        region R {
            state S { [H*] -> A.Q; state A { state Q; [*] -> Q; } state B; [*] -> A; A -> B :: G; B -> A :: H; }
            state T; [*] -> S; S -> T :: Out; T -> S.[H*] :: Re;
        }
        region R2 { state Y; [*] -> Y; }
    } [*] -> P; }`;

    it('counts a transition of a region as entering history and lowers the history', async () => {
        const document = createDocument(HISTORY_SOURCE, '/tmp/region-history.fcstm');
        const ast = await packageModule.parseAstDocument(document);
        const machine = packageModule.buildStateMachineModel(ast!)!;
        assert.deepEqual(machine.historyOwners.map(owner => owner.ownerPath.join('.')), ['Root.P.R.S']);
        const codes = (await editorModule.collectDocumentDiagnostics(document)).map(item => item.code);
        assert.ok(!codes.includes('W_HISTORY_UNUSED'), codes.join(','));
    });

    it('reports a region transition that enters history its target does not declare', async () => {
        const document = createDocument(`state Root { state P {
            region R { state S; state T; [*] -> S; S -> T :: Out; T -> S.[H] :: Re; }
            region R2 { state Y; [*] -> Y; }
        } [*] -> P; }`, '/tmp/region-history-undeclared.fcstm');
        const codes = (await editorModule.collectDocumentDiagnostics(document)).map(item => item.code);
        assert.ok(codes.includes('E_HISTORY_TARGET_UNDECLARED'), codes.join(','));
    });
});


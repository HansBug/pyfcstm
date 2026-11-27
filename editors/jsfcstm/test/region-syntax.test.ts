import assert from 'node:assert/strict';
import * as path from 'node:path';
import {createDocument, editorModule, packageModule, trackTempDir, writeFile} from './support';

describe('ordered region syntax', () => {
    it('retains named regions, source order, nested scopes and documentation', async () => {
        const source = `state Root {
            /* motor region */
            region Motor {
                state Running { region Inner { state Idle; [*] -> Idle; } }
                event stop;
                [*] -> Running;
                Running -> [*] :: stop;
                ! * -> [*] : if [True];
                >> during before prepare { value = 1; }
                >> during after abstract observe;
                >> during before reuse ref /Root.prepare;
                ;
            }
            region Sensor { state Ready; [*] -> Ready; }
        }`;
        const ast = await packageModule.parseAstDocument(createDocument(source, '/tmp/regions.fcstm'));
        assert.ok(ast?.rootState);
        const root = ast.rootState;
        assert.deepEqual(root.substates, []);
        assert.equal(root.composite, true);
        assert.deepEqual(root.regions.map(region => region.name), ['Motor', 'Sensor']);
        const motor = root.regions[0];
        assert.equal(motor.kind, 'regionDefinition');
        assert.equal(motor.pyNodeType, 'RegionDefinition');
        assert.equal(motor.doc, 'motor region');
        assert.deepEqual(motor.range.start, {line: 2, character: 12});
        assert.equal(motor.substates[0].regions[0].name, 'Inner');
        assert.equal(motor.events[0].name, 'stop');
        assert.equal(motor.transitions.length, 2);
        assert.equal(motor.forceTransitions.length, 1);
        assert.deepEqual(motor.duringAspects.map(action => action.pyNodeType), [
            'DuringAspectOperations', 'DuringAspectAbstractFunction', 'DuringAspectRefFunction',
        ]);
        assert.equal(root.statements[0], motor);
        assert.equal(motor.during_aspects, motor.duringAspects);
        assert.equal(motor.force_transitions, motor.forceTransitions);
    });
    for (const name of ['Only', 'Region', 'Active']) {
        it(`parses a single empty region named ${name}`, async () => {
            const ast = await packageModule.parseAstDocument(createDocument(
                `state Root { region ${name} {} }`, '/tmp/empty-region.fcstm'));
            const region = ast!.rootState!.regions[0];
            assert.equal(region.name, name);
            assert.deepEqual(region.statements, []);
            assert.deepEqual(region.events, []);
            assert.equal(ast!.rootState!.composite, true);
        });
    }
    for (const body of ['enter {}', 'during {}', 'during before {}', 'exit {}',
        'def int x = 0;', 'region Nested {}', 'import "a.fcstm" as A;', '[H] -> A;']) {
        it(`rejects region-owned ${body}`, async () => {
            const result = await packageModule.getParser().parse(`state Root { region R { ${body} } }`);
            assert.equal(result.success, false);
        });
    }
    for (const body of ['region R { state A; [*] -> A; }', 'state A { region R { state B; [*] -> B; } } [*] -> A;']) {
        it(`builds an executable region model without refusing: ${body}`, async () => {
            const document = createDocument(`state Root { ${body} }`, '/tmp/region-model.fcstm');
            const ast = await packageModule.parseAstDocument(document);
            assert.ok(ast);
            assert.ok(packageModule.buildStateMachineModel(ast));
            const diagnostics = editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(
                packageModule.buildSemanticDocument(ast)!, document);
            assert.deepEqual(diagnostics.filter(item => item.severity === 'error'), []);
        });
    }
    it('builds a model through recursive imports of a region machine', async () => {
        const directory = trackTempDir('jsfcstm-regions-');
        const leaf = path.join(directory, 'leaf.fcstm');
        const middle = path.join(directory, 'middle.fcstm');
        const host = path.join(directory, 'host.fcstm');
        writeFile(leaf, 'state Leaf { region R { state A; [*] -> A; } }');
        writeFile(middle, 'state Middle { import "leaf.fcstm" as Leaf; [*] -> Leaf; }');
        writeFile(host, 'state Host { import "middle.fcstm" as Middle; [*] -> Middle; }');
        const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
        assert.ok(snapshot.nodes[leaf].model);
        assert.ok(snapshot.nodes[host].model);
        assert.equal(snapshot.nodes[host].bindingDiagnostic, undefined);
    });
});

import assert from 'node:assert/strict';
import * as path from 'node:path';
import {createDocument, packageModule, trackTempDir, writeFile} from './support';

const source = `input int sensor;
param int limit = 2;
output int result = 0;
control int counter = 0;
state Root {
    enter { counter = sensor; }
    state A {
        during { if [sensor > limit] { result = counter; } else { result = 0; } }
    }
    state B;
    [*] -> A;
    A -> B : if [sensor > limit] effect { counter = counter + 1; }
}`;

describe('variable access report contract', () => {
    it('locates actions, guards, effects and nested statements with role supply', async () => {
        const ast = await packageModule.parseAstDocument(createDocument(source, '/tmp/access.fcstm'));
        const model = packageModule.buildStateMachineModel(ast)!;
        const report = packageModule.inspectModel(model);
        const sensor = report.variables.find(v => v.name === 'sensor')!;
        assert.equal(sensor.external_supply, 'cycle');
        assert.deepEqual(sensor.diagnostic_policy, {unused: false, unwritten: false, write_only: false, constant_guard: false});
        assert.deepEqual(sensor.write_sites, []);
        assert.deepEqual(sensor.read_sites.map(s => [s.kind, s.state_path, s.statement_path]), [
            ['action', 'Root', [0]], ['guard', 'Root', []], ['action', 'Root.A', [0, 0]],
        ]);
        assert.ok(sensor.read_sites.every(s => s.source_path === '/tmp/access.fcstm' && s.span !== null));
        const result = report.variables.find(v => v.name === 'result')!;
        assert.deepEqual(result.write_sites.map(s => s.statement_path), [[0, 0, 0], [0, 1, 0]]);
        assert.ok(result.write_sites.every(s => s.action_index === 1 && s.action === report.actions[1].signature));
        const counter = report.variables.find(v => v.name === 'counter')!;
        assert.equal(counter.external_supply, 'none');
        assert.equal(counter.diagnostic_policy.unused, true);
        const effect = counter.write_sites[1];
        assert.equal(report.transitions[effect.transition_index!].from_path, 'Root.A');
        assert.equal(report.variables.find(v => v.name === 'limit')!.external_supply, 'construction');
        assert.deepEqual(counter.written_in_effects, [['Root.A', 'Root.B']]);
    });

    it('preserves separate import instances and their authored file', async () => {
        const dir = trackTempDir('jsfcstm-access-sites-');
        const leaf = path.join(dir, 'leaf.fcstm');
        writeFile(leaf, 'input int value; output int result = 0; state Leaf { enter { result = value; } }');
        writeFile(path.join(dir, 'child.fcstm'), 'state Child { import "./leaf.fcstm" as Leaf { var value -> inner; var result -> result; } [*] -> Leaf; }');
        const host = path.join(dir, 'host.fcstm');
        writeFile(host, 'input int shared; state Host { import "./child.fcstm" as A { var inner -> shared; var result -> a_result; } import "./child.fcstm" as B { var inner -> shared; var result -> b_result; } [*] -> A; A -> B; }');
        const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
        assert.equal(snapshot.nodes[host].modelAuthority, 'assembled');
        const report = packageModule.inspectModel(snapshot.nodes[host].model!);
        const shared = report.variables.find(v => v.name === 'shared')!;
        assert.deepEqual(shared.read_sites.map(s => s.state_path), ['Host.A.Leaf', 'Host.B.Leaf']);
        assert.deepEqual(shared.read_sites.map(s => s.source_path), [leaf, leaf]);
        assert.deepEqual(shared.read_sites[0].span, shared.read_sites[1].span);
    });
});

for (const stage of ['enter', 'during', 'exit', 'during before', 'during after', '>> during before', '>> during after']) {
    it(`variable access report contract covers ${stage} and duplicate inline names`, async () => {
        const text = `input int sensor; output int result = 0; state Root {
            ${stage} { result = sensor + sensor; }
            ${stage} { result = sensor; }
            ${stage === 'during' ? '' : 'state A; [*] -> A;'} }`;
        const ast = await packageModule.parseAstDocument(createDocument(text, '/tmp/lifecycle.fcstm'));
        const report = packageModule.inspectModel(packageModule.buildStateMachineModel(ast)!);
        const sensor = report.variables[0];
        assert.deepEqual(sensor.read_sites.map(s => s.action_index), [0, 1]);
        assert.deepEqual(sensor.read_sites.map(s => s.statement_path), [[0], [0]]);
        assert.equal(sensor.read_sites[0].action, sensor.read_sites[1].action);
        assert.equal(report.variables[1].write_sites.length, 2);
    });
}

it('variable access report contract records nested and unreachable branches', async () => {
    const text = `input int sensor; output int result = 0; state Root { during {
        if [sensor > 0] {
            if [sensor < 2] { result = sensor; } else { result = 2; }
        } else if [sensor < 0] { result = 3; } else { result = 4; }
        if [0 > 1] { result = 5; }
    } }`;
    const ast = await packageModule.parseAstDocument(createDocument(text, '/tmp/nested.fcstm'));
    const report = packageModule.inspectModel(packageModule.buildStateMachineModel(ast)!);
    assert.deepEqual(report.variables[0].read_sites.map(s => s.statement_path), [[0, 0], [0, 0, 0, 0], [0, 0, 0, 0, 0], [0, 1]]);
    assert.deepEqual(report.variables[1].write_sites.map(s => s.statement_path), [
        [0, 0, 0, 0, 0], [0, 0, 0, 1, 0], [0, 1, 0], [0, 2, 0], [1, 0, 0],
    ]);
});

it('variable access report contract retains definition sites for cross-file action references', async () => {
    const dir = trackTempDir('jsfcstm-action-reference-');
    const child = path.join(dir, 'child.fcstm');
    writeFile(child, 'input int sensor; output int result = 0; state Child { enter Setup { result = sensor; } }');
    const host = path.join(dir, 'host.fcstm');
    writeFile(host, 'state Root { import "./child.fcstm" as Child; state A { enter ref /Child.Setup; } [*] -> A; }');
    const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
    const report = packageModule.inspectModel(snapshot.nodes[host].model!);
    const sites = report.variables.find(v => v.role === 'input')!.read_sites;
    assert.equal(sites.length, 1);
    assert.equal(sites[0].source_path, child);
    assert.equal(sites[0].state_path, 'Root.Child');
    assert.ok(report.actions.some(a => a.is_ref && a.state_path === 'Root.A'));
});

it('variable access report contract includes JSON spans and bundled schema fields', async () => {
    const ast = await packageModule.parseAstDocument(createDocument(source, '/tmp/access.fcstm'));
    const report = packageModule.inspectModel(packageModule.buildStateMachineModel(ast)!);
    const payload = JSON.parse(JSON.stringify(report));
    assert.deepEqual(payload.variables[0].read_sites[0].span, {line: 6, column: 13, end_line: 6, end_column: 30});
    const schema = packageModule.loadInspectModelSchema() as any;
    const variableSchema = schema.definitions.VariableInfo;
    for (const field of ['role', 'external_supply', 'diagnostic_policy', 'read_sites', 'write_sites']) {
        assert.ok(variableSchema.required.includes(field));
    }
    assert.deepEqual(variableSchema.properties.external_supply.enum, ['none', 'cycle', 'construction']);
    assert.deepEqual(Object.keys(payload.variables[0].read_sites[0]).sort(), schema.definitions.VariableAccessSite.required.slice().sort());
    assert.equal('schema_version' in payload, false);
});

it('variable access DSL retains branch and assignment ranges', async () => {
    const text = 'input int sensor; output int result = 0; state Root { during { if [sensor > 0] { result = sensor; } else { result = 0; } } }';
    const ast = await packageModule.parseAstDocument(createDocument(text, '/tmp/ast-access.fcstm'));
    assert.deepEqual(ast.variables.map(v => v.role), ['input', 'output']);
    const conditional = ast.rootState!.durings[0].operationsList[0];
    assert.equal(conditional.kind, 'ifStatement');
    if (conditional.kind !== 'ifStatement') throw new Error('Expected conditional AST');
    for (const [index, branch] of conditional.branches.entries()) {
        const assignment = branch.statements[0];
        assert.equal(assignment.kind, 'assignmentStatement');
        assert.equal(text.slice(assignment.range.start.character, assignment.range.end.character), `result = ${index ? '0' : 'sensor'};`);
        assert.ok(branch.range.start.character <= assignment.range.start.character);
        assert.ok(branch.range.end.character >= assignment.range.end.character);
    }
});

it('variable access model retains imported nested source, names and roles', async () => {
    const dir = trackTempDir('jsfcstm-model-access-');
    const leaf = path.join(dir, 'leaf.fcstm');
    writeFile(leaf, 'input int sensor; param int limit = 1; output int result = 0; state Leaf { during { if [sensor > limit] { if [sensor > 2] { result = sensor; } } } }');
    const host = path.join(dir, 'host.fcstm');
    writeFile(host, 'input int shared; state Host { import "./leaf.fcstm" as A { var sensor -> shared; var limit -> A_limit; var result -> A_result; } import "./leaf.fcstm" as B { var sensor -> shared; var limit -> B_limit; var result -> B_result; } [*] -> A; A -> B; }');
    const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
    const model = snapshot.nodes[host].model!;
    assert.equal(model.defines.shared.role, 'input');
    for (const name of ['A', 'B']) {
        const state = model.rootState.substates[name];
        assert.equal(state.importedFromFile, leaf);
        const block = state.onDurings[0].operations[0] as any;
        assert.equal(block.kind, 'ifBlock');
        assert.equal(block.branches[0].condition.x.name, 'shared');
        const assignment = block.branches[0].statements[0].branches[0].statements[0];
        assert.equal(assignment.varName, `${name}_result`);
        assert.equal(assignment.expr.name, 'shared');
        assert.equal(model.defines[`${name}_limit`].role, 'param');
        assert.equal(model.defines[`${name}_result`].role, 'output');
    }
});

it('variable access report contract treats programmatic zero-width ranges as missing', async () => {
    const ast = await packageModule.parseAstDocument(createDocument(source, ''));
    // The public AST builder accepts programmatically supplied source ranges.
    const clearRanges = (node: any): void => {
        if (!node || typeof node !== 'object') return;
        for (const [key, value] of Object.entries(node)) {
            if (key === 'range') node[key] = {start: {line: 0, character: 0}, end: {line: 0, character: 0}};
            else clearRanges(value);
        }
    };
    clearRanges(ast);
    const model = packageModule.buildStateMachineModel(ast)!;
    const report = packageModule.inspectModel(model);
    assert.equal(report.variables[0].read_sites[0].span, null);
    assert.equal(report.variables[0].read_sites[0].source_path, null);
});

it('variable access report contract indexes expanded combo transitions', async () => {
    const text = 'input int sensor; output int result = 0; state Root { state A; state B; [*] -> A; A -> B :: Begin + [sensor > 0] + End effect { result = sensor; } }';
    const ast = await packageModule.parseAstDocument(createDocument(text, '/tmp/combo.fcstm'));
    const report = packageModule.inspectModel(packageModule.buildStateMachineModel(ast)!);
    const [sensor, result] = report.variables;
    assert.ok(result.write_sites.length > 0);
    assert.ok(sensor.read_sites.some(s => s.kind === 'guard'));
    assert.ok(sensor.read_sites.some(s => s.kind === 'effect'));
    for (const site of [...sensor.read_sites, ...result.write_sites]) {
        assert.ok(report.transitions[site.transition_index!].combo_origin_refs.length > 0);
        assert.equal(site.state_path, 'Root');
        assert.ok(site.span);
    }
});

it('variable access report contract does not invent abstract or initializer accesses', async () => {
    const ast = await packageModule.parseAstDocument(createDocument(
        'param int limit = 1; output int result = 0; state Root { enter abstract Compute; }', '/tmp/abstract.fcstm'));
    const report = packageModule.inspectModel(packageModule.buildStateMachineModel(ast)!);
    for (const variable of report.variables) {
        assert.deepEqual(variable.read_sites, []);
        assert.deepEqual(variable.write_sites, []);
        assert.ok(variable.abstract_actions_in_scope.length > 0);
    }
});

it('variable access report contract keeps host provenance for forced guards inside imports', async () => {
    const dir = trackTempDir('jsfcstm-forced-access-');
    writeFile(path.join(dir, 'leaf.fcstm'), 'state Leaf { state X; state Y; [*] -> X; X -> Y; }');
    const host = path.join(dir, 'host.fcstm');
    writeFile(host, 'input int sensor; state Root { import "./leaf.fcstm" as A; state B; [*] -> A; !* -> B : if [sensor > 0]; }');
    const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
    const report = packageModule.inspectModel(snapshot.nodes[host].model!);
    const sites = report.variables[0].read_sites;
    assert.ok(sites.some(site => site.state_path.startsWith('Root.A')));
    for (const site of sites) {
        assert.equal(site.source_path, host);
        assert.ok(site.span);
        assert.equal(report.transitions[site.transition_index!].is_forced, true);
        assert.equal(report.transitions[site.transition_index!].source_path, host);
    }
});

for (const role of ['input', 'param', 'control', 'output']) {
    it(`variable access report contract keeps every shared ${role} instance`, async () => {
        const dir = trackTempDir('jsfcstm-shared-role-access-');
        const leaf = path.join(dir, 'leaf.fcstm');
        const initializer = role === 'input' ? '' : ' = 1';
        const writable = role === 'control' || role === 'output';
        const body = 'result = value;' + (writable ? ' value = value + 1;' : '');
        writeFile(leaf, `${role} int value${initializer}; output int result = 0; state Leaf { during { ${body} } }`);
        const host = path.join(dir, 'host.fcstm');
        writeFile(host, `${role} int shared${initializer}; state Host {
            import "./leaf.fcstm" as A { var value -> shared; var result -> a_result; }
            import "./leaf.fcstm" as B { var value -> shared; var result -> b_result; }
            [*] -> A; A -> B; }`);
        const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
        const report = packageModule.inspectModel(snapshot.nodes[host].model!);
        const shared = report.variables.find(variable => variable.name === 'shared')!;
        assert.deepEqual(shared.read_sites.map(site => site.state_path), writable ? ['Host.A', 'Host.A', 'Host.B', 'Host.B'] : ['Host.A', 'Host.B']);
        assert.deepEqual(shared.write_sites.map(site => site.state_path), writable ? ['Host.A', 'Host.B'] : []);
        assert.ok([...shared.read_sites, ...shared.write_sites].every(site => site.source_path === leaf));
        assert.deepEqual(shared.read_sites.map(site => site.action_index), writable ? [0, 0, 1, 1] : [0, 1]);
        assert.equal(shared.diagnostic_policy.unused, role === 'control');
    });
}

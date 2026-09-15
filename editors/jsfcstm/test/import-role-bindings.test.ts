import assert from 'node:assert/strict';
import * as path from 'node:path';
import {createDocument, editorModule, packageModule, trackTempDir, writeFile} from './support';

const roles = ['param', 'input', 'control', 'output'] as const;
const targets = {param: ['param'], input: [...roles], control: ['control', 'output'], output: ['control', 'output']};
function declaration(role: string, name: string, numeric = 'int', value = '1'): string {
    return `${role} ${numeric} ${name}${role === 'input' ? '' : ` = ${value}`};`;
}

describe('assembled binding interfaces', () => {
    for (const source of roles) for (const target of roles) {
        for (const [sourceType, targetType] of [['int', 'int'], ['float', 'float'], ['int', 'float'], ['float', 'int']]) {
            it(`${source} ${sourceType} binds as ${target} ${targetType}`, async () => {
                const dir = trackTempDir('jsfcstm-role-binding-');
                writeFile(path.join(dir, 'child.fcstm'), declaration(source, 'value', sourceType) + ' state Child;');
                const host = path.join(dir, 'host.fcstm');
                writeFile(host, declaration(target, 'shared', targetType, '9') + ' state Host { import "./child.fcstm" as Child { var value -> shared; } [*] -> Child; }');
                const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
                const node = snapshot.nodes[host];
                if (!targets[source].includes(target) || sourceType !== targetType) {
                    assert.equal(node.modelAuthority, 'local');
                    assert.equal(node.bindingDiagnostic!.diagnostic.code, 'E_IMPORT_DUPLICATE_MAPPING');
                    return;
                }
                assert.equal(node.modelAuthority, 'assembled');
                const model = node.model!;
                const define = model.defines.shared;
                assert.deepEqual(Object.keys(model.defines), ['shared']);
                assert.equal(define.role, target);
                assert.equal(define.type, targetType);
                const report = packageModule.inspectModel(model);
                const variable = report.variables.find(item => item.name === 'shared')!;
                assert.equal(variable.role, target);
                assert.equal(variable.external_supply, target === 'input' ? 'cycle' : target === 'param' ? 'construction' : 'none');
                assert.ok(Object.values(variable.diagnostic_policy).every(value => value === (target === 'control')));
                const partitions = {param: model.parameters, input: model.inputs, control: model.control_variables, output: model.output_variables};
                for (const role of roles) {
                    assert.deepEqual(Object.keys(partitions[role]), role === target ? ['shared'] : []);
                    if (role === target) assert.equal(partitions[role].shared, define);
                }
                assert.deepEqual(define.sourceDeclarations!.map(item => item.declaration.role), [target, source]);
                assert.equal(define.sourceDeclarations![1].declaration.name, 'value');
                assert.equal(define.sourceDeclarations![1].bindings[0].targetName, 'shared');
            });
        }
    }
});

describe('source ownership before binding', () => {
    for (const [source, target] of [['input', 'control'], ['input', 'output'], ['input', 'param'], ['param', 'param']]) {
        for (const body of ['enter { value = 2; }', 'during before { value = 2; }', 'during after { value = 2; }', '>> during before { value = 2; } state A; [*] -> A;', '>> during after { value = 2; } state A; [*] -> A;', 'enter Set { value = 2; } exit ref Set;', 'state A; [*] -> A effect { value = 2; };', 'state A; [*] -> A; A -> [*] effect { value = 2; };', 'exit { value = 2; }', 'during { if [1 == 0] { value = 2; } else { if [1 == 1] { value = 3; } } }', 'state A { enter { value = 2; } } [*] -> A;', 'state A; state B; [*] -> A; A -> B effect { value = 2; }']) {
            it(`rejects ${source} write in ${body} before binding to ${target}`, async () => {
                const dir = trackTempDir('jsfcstm-source-ownership-');
                const child = path.join(dir, 'child.fcstm');
                writeFile(child, declaration(source, 'value') + ` state Child { ${body} }`);
                const host = path.join(dir, 'host.fcstm');
                const text = declaration(target, 'shared') + ' state Host { import "./child.fcstm" as Child { var value -> shared; } }';
                writeFile(host, text);
                const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
                assert.equal(snapshot.nodes[host].modelAuthority, 'local');
                const diagnostic = snapshot.nodes[host].bindingDiagnostic!;
                assert.equal(diagnostic.filePath, child);
                assert.equal(diagnostic.diagnostic.code, source === 'input' ? 'E_INPUT_WRITE' : 'E_PARAM_WRITE');
                const publications = await editorModule.collectDocumentDiagnosticsByUri(createDocument(text, host));
                assert.ok([...publications.values()].flat().some(item => item.code === diagnostic.diagnostic.code));
            });
        }
    }
});

describe('implicit binding ownership', () => {
    for (const first of roles) for (const second of roles) {
        it(`does not infer a host role from ${first} then ${second}`, async () => {
            const dir = trackTempDir('jsfcstm-implicit-role-');
            writeFile(path.join(dir, 'a.fcstm'), declaration(first, 'value') + ' state A;');
            writeFile(path.join(dir, 'b.fcstm'), declaration(second, 'value') + ' state B;');
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, 'state Host { import "./a.fcstm" as A { var value -> shared; } import "./b.fcstm" as B { var value -> shared; } [*] -> A; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            const valid = first === second && first !== 'input';
            assert.equal(snapshot.nodes[host].modelAuthority, valid ? 'assembled' : 'local');
            if (valid) assert.equal(snapshot.nodes[host].model!.defines.shared.role, first);
        });
    }
});

describe('nested parameter binding', () => {
    for (const outer of roles) {
        it(`checks the intermediate param contract before binding to ${outer}`, async () => {
            const dir = trackTempDir('jsfcstm-nested-parameter-');
            writeFile(path.join(dir, 'leaf.fcstm'), 'input int sample; state Leaf;');
            writeFile(path.join(dir, 'child.fcstm'), 'param int configured = 3; state Child { import "./leaf.fcstm" as Leaf { var sample -> configured; } [*] -> Leaf; }');
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, declaration(outer, 'shared', 'int', '9') + ' state Host { import "./child.fcstm" as Child { var configured -> shared; } [*] -> Child; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, outer === 'param' ? 'assembled' : 'local');
            if (outer === 'param') {
                const definition = snapshot.nodes[host].model!.parameters.shared;
                assert.deepEqual(definition.sourceDeclarations!.map(item => item.declaration.role), ['param', 'param', 'input']);
                assert.deepEqual(definition.sourceDeclarations!.map(item => item.bindings.length), [0, 1, 2]);
            } else {
                assert.equal(snapshot.nodes[host].bindingDiagnostic!.diagnostic.data!.binding_reason, 'role_mismatch');
            }
        });
    }
});

describe('implicit nested source ownership', () => {
    for (const role of ['input', 'param']) {
        it(`rejects a write to an imported ${role} before outer binding`, async () => {
            const dir = trackTempDir('jsfcstm-nested-source-');
            writeFile(path.join(dir, 'leaf.fcstm'), declaration(role, 'value') + ' state Leaf;');
            const child = path.join(dir, 'child.fcstm');
            writeFile(child, 'state Child { import "./leaf.fcstm" as Leaf { var value -> shared; } enter { shared = 2; } [*] -> Leaf; }');
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, declaration(role === 'input' ? 'control' : 'param', 'target') + ' state Host { import "./child.fcstm" as Child { var shared -> target; } [*] -> Child; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'local');
            const diagnostic = snapshot.nodes[host].bindingDiagnostic!;
            assert.equal(diagnostic.filePath, child);
            assert.equal(diagnostic.diagnostic.code, role === 'input' ? 'E_INPUT_WRITE' : 'E_PARAM_WRITE');
        });
    }
});

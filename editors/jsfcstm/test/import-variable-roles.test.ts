import assert from 'node:assert/strict';
import * as path from 'node:path';

import {createDocument, packageModule, trackTempDir, writeFile} from './support';

const roles = ['control', 'input', 'param', 'output'] as const;

function declaration(role: string, name: string): string {
    return `${role} int ${name}${role === 'input' ? '' : ' = 1'};`;
}

describe('import variable mapping syntax', () => {
    for (const spelling of ['var', 'def']) {
        for (const [selector, target] of [['value', 'shared'], ['{a, b}', 'Host_$0'], ['sensor_*', 'Host_$1'], ['*', 'Host_$0']]) {
            it(`parses ${spelling} mapping with selector ${selector}`, async () => {
                const ast = await packageModule.parseAstDocument(createDocument(
                    `state Host { import "./child.fcstm" as Child { ${spelling} ${selector} -> ${target}; } }`,
                    '/tmp/import-host.fcstm'
                ));
                const mapping = ast.rootState!.imports[0].mappings[0];
                assert.equal(mapping.pyNodeType, spelling === 'var' ? 'ImportVariableMapping' : 'ImportDefMapping');
                assert.equal((mapping as {spelling?: string}).spelling, spelling);
            });
        }
    }
});

describe('import role preservation', () => {
    for (const source of roles) {
        for (const target of roles) {
            it(`checks ${source} binding to ${target}`, async () => {
                const dir = trackTempDir('jsfcstm-import-roles-');
                writeFile(path.join(dir, 'child.fcstm'), declaration(source, 'value') + ' state Child;');
                const host = path.join(dir, 'host.fcstm');
                writeFile(host, declaration(target, 'shared') + ' state Host { import "./child.fcstm" as Child { def value -> shared; } [*] -> Child; }');
                const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
                assert.equal(snapshot.nodes[host].modelAuthority, source === target ? 'assembled' : 'local');
            });
        }
    }
});

describe('import binding diagnostics', () => {
    it('publishes a role conflict at the import through the public editor API', async () => {
        const {editorModule} = await import('./support');
        const dir = trackTempDir('jsfcstm-import-diagnostic-');
        writeFile(path.join(dir, 'child.fcstm'), 'input int value; state Child;');
        const host = path.join(dir, 'host.fcstm');
        const source = 'param int shared = 1; state Host { import "./child.fcstm" as Child { var value -> shared; } }';
        writeFile(host, source);
        const publications = await editorModule.collectDocumentDiagnosticsByUri(createDocument(source, host));
        const conflicts = [...publications.values()].flat().filter(item => item.code === 'E_IMPORT_DUPLICATE_MAPPING');
        assert.equal(conflicts.length, 1);
        assert.match(conflicts[0].message, /role/);
        assert.equal(conflicts[0].data?.duplicated_name, 'shared');
        assert.equal(source.slice(conflicts[0].range.start.character, conflicts[0].range.end.character), 'import "./child.fcstm" as Child { var value -> shared; }');
    });
});

describe('import declaration provenance', () => {
    it('retains both recursive instances when sharing a host input', async () => {
        const dir = trackTempDir('jsfcstm-import-provenance-');
        writeFile(path.join(dir, 'leaf.fcstm'), 'input int value; state Leaf;');
        writeFile(path.join(dir, 'child.fcstm'), 'input int inner; state Child { import "./leaf.fcstm" as Leaf { var value -> inner; } [*] -> Leaf; }');
        const host = path.join(dir, 'host.fcstm');
        writeFile(host, 'input int shared; state Host { import "./child.fcstm" as A { var inner -> shared; } import "./child.fcstm" as B { var inner -> shared; } [*] -> A; }');
        const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
        const sources = snapshot.nodes[host].model!.defines.shared.sourceDeclarations!;
        assert.deepEqual(sources.map(item => item.declaration.name), ['shared', 'inner', 'value', 'inner', 'value']);
        assert.deepEqual(sources.map(item => item.bindings.length), [0, 1, 2, 1, 2]);
        assert.equal(sources[2].filePath, path.join(dir, 'leaf.fcstm'));
        assert.deepEqual(sources[2].bindings.map(item => item.alias), ['Leaf', 'A']);
        assert.deepEqual(sources[4].bindings.map(item => item.alias), ['Leaf', 'B']);
    });
});

describe('shared imported defaults', () => {
    for (const role of ['control', 'param', 'output']) {
        it(`merges equal ${role} defaults regardless of source coordinates`, async () => {
            const dir = trackTempDir('jsfcstm-import-defaults-');
            writeFile(path.join(dir, 'a.fcstm'), `${role} int short = 1; state A;`);
            writeFile(path.join(dir, 'b.fcstm'), `\n${role} int longer_name = 1; state B;`);
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, 'state Host { import "./a.fcstm" as A { var short -> shared; } import "./b.fcstm" as B { var longer_name -> shared; } [*] -> A; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'assembled');
            assert.deepEqual(Object.keys(snapshot.nodes[host].model!.defines), ['shared']);
        });
    }
});

describe('import binding failures', () => {
    for (const role of roles) {
        for (const explicit of [false, true]) {
            it(`rejects numeric type mismatches for ${role}, explicit host ${explicit}`, async () => {
                const dir = trackTempDir('jsfcstm-import-types-');
                writeFile(path.join(dir, 'a.fcstm'), declaration(role, 'value') + ' state A;');
                writeFile(path.join(dir, 'b.fcstm'), `${role} float value${role === 'input' ? '' : ' = 1.0'}; state B;`);
                const host = path.join(dir, 'host.fcstm');
                const prefix = explicit ? declaration(role, 'shared') : '';
                const firstImport = explicit ? '' : 'import "./a.fcstm" as A { var value -> shared; }';
                writeFile(host, `${prefix} state Host { ${firstImport} import "./b.fcstm" as B { var value -> shared; } [*] -> B; }`);
                const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
                assert.equal(snapshot.nodes[host].modelAuthority, 'local');
                assert.match(snapshot.nodes[host].bindingDiagnostic!.diagnostic.message, /type/);
            });
        }
    }
    for (const role of roles) {
        it(`rejects implicit shared ${role} with incompatible ownership or defaults`, async () => {
            const dir = trackTempDir('jsfcstm-import-conflict-');
            writeFile(path.join(dir, 'a.fcstm'), declaration(role, 'value') + ' state A;');
            writeFile(path.join(dir, 'b.fcstm'), `${role} int value${role === 'input' ? '' : ' = 2'}; state B;`);
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, 'state Host { import "./a.fcstm" as A { var value -> shared; } import "./b.fcstm" as B { var value -> shared; } [*] -> A; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'local');
            assert.match(snapshot.nodes[host].bindingDiagnostic!.diagnostic.message, role === 'input' ? /explicit/ : /initial values/);
        });
    }
    it('publishes a nested conflict against its declaring file', async () => {
        const {editorModule} = await import('./support');
        const dir = trackTempDir('jsfcstm-import-nested-diagnostic-');
        writeFile(path.join(dir, 'leaf.fcstm'), 'input int value; state Leaf;');
        const child = path.join(dir, 'child.fcstm');
        writeFile(child, 'param int shared = 1; state Child { import "./leaf.fcstm" as Leaf { var value -> shared; } }');
        const host = path.join(dir, 'host.fcstm');
        const source = 'state Host { import "./child.fcstm" as Child; }';
        writeFile(host, source);
        const publications = await editorModule.collectDocumentDiagnosticsByUri(createDocument(source, host));
        const entries = [...publications].filter(([, items]) => items.some(item => item.code === 'E_IMPORT_DUPLICATE_MAPPING'));
        assert.equal(entries.length, 1);
        assert.ok(entries[0][0].endsWith('/child.fcstm'));
    });
});

describe('import initializer validation', () => {
    for (const [source, hostDeclaration, code] of [
        ['input int value = 1;', 'input int shared;', 'E_DYNAMIC_INPUT_INITIALIZER'],
        ['param int value;', 'param int shared = 1;', 'E_VARIABLE_INITIALIZER_REQUIRED'],
    ]) {
        it(`does not let host defaults hide ${code}`, async () => {
            const dir = trackTempDir('jsfcstm-import-initializer-');
            writeFile(path.join(dir, 'child.fcstm'), source + ' state Child;');
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, hostDeclaration + ' state Host { import "./child.fcstm" as Child { var value -> shared; } [*] -> Child; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'local');
            assert.equal(snapshot.nodes[host].bindingDiagnostic!.diagnostic.code, code);
        });
    }
});

describe('canonical variable mapping assembly', () => {
    for (const role of roles) {
        for (const [selector, target, expected] of [
            ['value', 'chosen', 'chosen'],
            ['{value}', 'Host_$0', 'Host_value'],
            ['v*', 'Host_$1', 'Host_alue'],
            ['*', 'Host_$0', 'Host_value'],
        ]) {
            it(`preserves ${role} through selector ${selector}`, async () => {
                const dir = trackTempDir('jsfcstm-import-selector-');
                writeFile(path.join(dir, 'child.fcstm'), declaration(role, 'value') + ' state Child;');
                const host = path.join(dir, 'host.fcstm');
                writeFile(host, `state Host { import "./child.fcstm" as Child { var ${selector} -> ${target}; } [*] -> Child; }`);
                const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
                assert.equal(snapshot.nodes[host].modelAuthority, 'assembled');
                const definitions = snapshot.nodes[host].model!.defines;
                assert.deepEqual(Object.keys(definitions), [expected]);
                const expectedRole = role === 'input' ? 'input_dynamic' : role === 'param' ? 'input_static' : role;
                assert.equal(definitions[expected].role, expectedRole);
                assert.equal(definitions[expected].type, 'int');
            });
        }
        it(`preserves the numeric type of a newly created ${role} target`, async () => {
            const dir = trackTempDir('jsfcstm-import-float-');
            writeFile(path.join(dir, 'child.fcstm'), `${role} float value${role === 'input' ? '' : ' = 1.5'}; state Child;`);
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, 'state Host { import "./child.fcstm" as Child { var value -> shared; } [*] -> Child; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].model!.defines.shared.type, 'float');
        });
    }
});

describe('imported writer inspection', () => {
    for (const role of ['control', 'output']) {
        it(`keeps both writers of a shared ${role}`, async () => {
            const dir = trackTempDir('jsfcstm-import-writers-');
            writeFile(path.join(dir, 'child.fcstm'), `${role} int value = 0; state Child { enter { value = 1; } }`);
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, `${role} int shared = 0; state Host { import "./child.fcstm" as A { var value -> shared; } import "./child.fcstm" as B { var value -> shared; } [*] -> A; A -> B; }`);
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'assembled');
            const report = packageModule.inspectModel(snapshot.nodes[host].model!);
            const variable = report.variables.find(item => item.name === 'shared')!;
            assert.deepEqual([...variable.written_in_states].sort(), ['Host.A', 'Host.B']);
            assert.ok(report.diagnostics.every(item => item.severity !== 'error'));
        });
    }
});

describe('recursive role bindings', () => {
    for (const source of roles) {
        for (const target of roles) {
            it(`keeps ${source} through flattening before binding to ${target}`, async () => {
                const dir = trackTempDir('jsfcstm-recursive-roles-');
                writeFile(path.join(dir, 'leaf.fcstm'), declaration(source, 'value') + ' state Leaf;');
                writeFile(path.join(dir, 'child.fcstm'), 'state Child { import "./leaf.fcstm" as Leaf { var value -> inner; } [*] -> Leaf; }');
                const host = path.join(dir, 'host.fcstm');
                writeFile(host, declaration(target, 'shared') + ' state Host { import "./child.fcstm" as Child { var inner -> shared; } [*] -> Child; }');
                const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
                assert.equal(snapshot.nodes[host].modelAuthority, source === target ? 'assembled' : 'local');
                if (source !== target) {
                    assert.equal(snapshot.nodes[host].bindingDiagnostic!.diagnostic.data!.binding_reason, 'role_mismatch');
                }
            });
        }
    }
});

describe('explicit host defaults', () => {
    for (const role of ['control', 'param', 'output']) {
        it(`keeps the host ${role} default despite different imported defaults`, async () => {
            const dir = trackTempDir('jsfcstm-host-default-');
            writeFile(path.join(dir, 'a.fcstm'), `${role} int a = 1; state A;`);
            writeFile(path.join(dir, 'b.fcstm'), `${role} int b = 2; state B;`);
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, `${role} int shared = 9; state Host { import "./a.fcstm" as A { var a -> shared; } import "./b.fcstm" as B { var b -> shared; } [*] -> A; }`);
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'assembled');
            assert.equal(snapshot.nodes[host].model!.defines.shared.init!.to_ast_node().text, '9');
        });
    }
});

describe('duplicate imported declarations', () => {
    for (const role of roles) {
        it(`rejects two ${role} declarations mapped to one target in an import`, async () => {
            const dir = trackTempDir('jsfcstm-duplicate-target-');
            writeFile(path.join(dir, 'child.fcstm'), declaration(role, 'a') + declaration(role, 'b') + ' state Child;');
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, 'state Host { import "./child.fcstm" as Child { var {a, b} -> shared; } [*] -> Child; }');
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'local');
            assert.deepEqual(Object.keys(snapshot.nodes[host].model!.defines), []);
        });
    }
    for (const first of roles) {
        for (const second of roles) {
            it(`rejects duplicate source names with roles ${first} and ${second}`, async () => {
                const dir = trackTempDir('jsfcstm-duplicate-source-');
                writeFile(path.join(dir, 'child.fcstm'), declaration(first, 'value') + declaration(second, 'value') + ' state Child;');
                const host = path.join(dir, 'host.fcstm');
                writeFile(host, 'state Host { import "./child.fcstm" as Child { var value -> shared; } [*] -> Child; }');
                const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
                assert.equal(snapshot.nodes[host].modelAuthority, 'local');
                assert.equal(snapshot.nodes[host].bindingDiagnostic!.diagnostic.code, 'E_DUPLICATE_VAR');
            });
        }
    }
});

describe('rendered variable names', () => {
    for (const [name, selector, target] of [
        ['value', 'value', 'var'],
        ['value', 'value', 'param'],
        ['value', 'value', 'state'],
        ['x_', 'x_*', '*$state'],
        ['prefix_input', 'prefix_*', '$1'],
        ['prefix_1', 'prefix_*', '$1'],
        ['value', 'value*', '$1'],
    ]) {
        it(`rejects invalid target from ${selector} -> ${target}`, async () => {
            const dir = trackTempDir('jsfcstm-import-identifier-');
            writeFile(path.join(dir, 'child.fcstm'), declaration('control', name) + ' state Child;');
            const host = path.join(dir, 'host.fcstm');
            writeFile(host, `state Host { import "./child.fcstm" as Child { var ${selector} -> ${target}; } [*] -> Child; }`);
            const snapshot = await new packageModule.FcstmWorkspaceGraph().buildSnapshotForFile(host);
            assert.equal(snapshot.nodes[host].modelAuthority, 'local');
            assert.match(snapshot.nodes[host].bindingDiagnostic!.diagnostic.message, /identifier/);
        });
    }
});

import assert from 'node:assert/strict';
import * as fs from 'node:fs';
import * as path from 'node:path';
import {createDocument, editorModule, packageModule, trackTempDir, writeFile} from './support';

const diagnosticsModule = require('@pyfcstm/jsfcstm/diagnostics') as typeof import('@pyfcstm/jsfcstm/diagnostics');

async function diagnose(source: string) {
    const document = createDocument(source, '/tmp/region-diagnostics.fcstm');
    const ast = await packageModule.parseAstDocument(document);
    assert.ok(ast);
    return editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(
        packageModule.buildSemanticDocument(ast)!, document);
}

const GOOD_REGIONS = 'region A { state X; [*] -> X; } region B { state Y; [*] -> Y; }';

describe('region diagnostics', () => {
    it('accepts a well-formed parallel owner and valid queries without any diagnostics', async () => {
        const diagnostics = await diagnose(`
            def int x = 0;
            state Root {
                state P { ${GOOD_REGIONS} }
                state Q { during { if [active("Root.P.A.X") && active("/P.B.Y")] { x = 1; } } }
                [*] -> P;
                P -> Q :: Go;
                Q -> P :: Back;
            }`);
        assert.deepEqual(diagnostics.map(item => item.code), []);
    });

    it('reports E_REGION_STRUCTURE empty_region', async () => {
        const found = (await diagnose('state Root { region Empty {} }')).filter(item => item.code === 'E_REGION_STRUCTURE');
        assert.equal(found.length, 1);
        assert.equal(found[0].severity, 'error');
        assert.deepEqual(found[0].data, {
            namespace_path: 'Root.Empty', reason: 'empty_region', source_path: '/tmp/region-diagnostics.fcstm',
        });
    });

    it('reports E_REGION_STRUCTURE history_boundary', async () => {
        const found = (await diagnose(
            'state Root { state S { [H] -> A; state A; state B { region R { state X; [*] -> X; } } [*] -> A; } [*] -> S; }',
        )).filter(item => item.code === 'E_REGION_STRUCTURE');
        assert.deepEqual(found.map(item => item.data?.reason), ['history_boundary']);
    });

    it('reports E_DUPLICATE_REGION with the first declaration', async () => {
        const found = (await diagnose(
            'state Root { region A { state X; [*] -> X; }\nregion A { state Y; [*] -> Y; } }',
        )).filter(item => item.code === 'E_DUPLICATE_REGION');
        assert.equal(found.length, 1);
        assert.equal(found[0].data?.region_name, 'A');
        assert.equal(found[0].data?.owner_path, 'Root');
        assert.equal((found[0].data?.previous_span as {start: {line: number}}).start.line, 0);
        assert.equal(found[0].range.start.line, 1);
    });

    const targets: Array<[string, string, string]> = [
        ['active("Other.A")', 'invalid_path', 'Other.A'],
        ['active("Root.Missing")', 'not_found', 'Root.Missing'],
        ['active("Root.P.A.Nothing")', 'not_found', 'Root.P.A.Nothing'],
        ['active("Root.P.A")', 'region', 'Root.P.A'],
        ['active("Root.Ghost")', 'pseudo', 'Root.Ghost'],
        ['active("Root..P")', 'invalid_path', 'Root..P'],
    ];
    for (const [query, reason, statePath] of targets) {
        it(`reports E_ACTIVE_QUERY_TARGET ${reason} for ${query}`, async () => {
            const found = (await diagnose(
                `state Root { state P { ${GOOD_REGIONS} } pseudo state Ghost; [*] -> P; P -> Ghost; during before { if [${query}] {} } }`,
            )).filter(item => item.code === 'E_ACTIVE_QUERY_TARGET');
            assert.equal(found.length, 1);
            assert.deepEqual(found[0].data, {state_path: statePath, reason, source_path: '/tmp/region-diagnostics.fcstm'});
        });
    }

    it('skips query binding while the region structure is invalid', async () => {
        const codes = (await diagnose(
            'state Root { region Empty {} during before { if [active("Root.Missing")] {} } }')).map(item => item.code);
        assert.ok(codes.includes('E_REGION_STRUCTURE'));
        assert.ok(!codes.includes('E_ACTIVE_QUERY_TARGET'));
    });
});

describe('region diagnostics without a root state', () => {
    it('reports nothing for a document that declares no state', async () => {
        const document = createDocument('def int x = 0;', '/tmp/region-empty.fcstm');
        const ast = await packageModule.parseAstDocument(document);
        const semantic = ast ? packageModule.buildSemanticDocument(ast) : null;
        if (semantic) {
            const found = editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(semantic, document);
            assert.deepEqual(found.filter(item => /REGION|ACTIVE/.test(item.code)), []);
        }
    });
});

describe('region documents in the editor', () => {
    async function publish(source: string) {
        const document = createDocument(source, '/tmp/region-editor.fcstm');
        const publications = await editorModule.collectDocumentDiagnosticsByUri(document);
        return [...publications.values()].flat();
    }

    it('raises no diagnostics for a well-formed document with regions and queries', async () => {
        const found = await publish(`def int x = 0;
            state Root {
                [*] -> Run;
                state Run {
                    region A { [*] -> S1; state S1; state S2; S1 -> S2 :: Go; S2 -> S1 :: Back; }
                    region B { [*] -> T1; state T1; state T2; T1 -> T2 : if [active("Root.Run.A.S2")]; T2 -> T1 :: Back; }
                }
                state Off;
                Run -> Off :: Stop;
                Off -> Run :: Start;
            }`);
        assert.deepEqual(found.map(item => item.code), []);
    });

    it('raises no diagnostics for a well-formed document that only uses queries', async () => {
        const found = await publish(`def int x = 0;
            state Root {
                [*] -> A;
                state A { during { if [active("Root.B")] { x = 1; } } }
                state B;
                A -> B : if [active("Root.A") && x > 0];
                B -> A :: Back;
            }`);
        assert.deepEqual(found.map(item => item.code), []);
    });

    it('points the repeated region at the previous one of the same name', async () => {
        const document = createDocument(
            `state Root {
                region A { state X; [*] -> X; }
                region A { state Y; [*] -> Y; }
                region A { state Z; [*] -> Z; }
            }`, '/tmp/region-triple.fcstm');
        const ast = await packageModule.parseAstDocument(document);
        const found = editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(
            packageModule.buildSemanticDocument(ast!)!, document).filter(item => item.code === 'E_DUPLICATE_REGION');
        assert.deepEqual(found.map(item => (item.data?.previous_span as {start: {line: number}}).start.line), [1, 2]);
    });

    it('does not reject a query that enters an imported module', async () => {
        const directory = trackTempDir('jsfcstm-region-editor-import-');
        const module = path.join(directory, 'mod.fcstm');
        const host = path.join(directory, 'host.fcstm');
        writeFile(module, 'state Sub { state Par { region L { [*] -> L1; state L1; } } [*] -> Par; }');
        writeFile(host, `state Root { state M { import "mod.fcstm" as Mod; [*] -> Mod; }
            state Q; [*] -> Q; Q -> M : if [active("Root.M.Mod.Par.L.L1")]; M -> Q :: Back; }`);
        const document = createDocument(fs.readFileSync(host, 'utf8'), host);
        const found = (await editorModule.collectDocumentDiagnosticsByUri(document));
        assert.deepEqual([...found.values()].flat().filter(item => item.code === 'E_ACTIVE_QUERY_TARGET'), []);
    });

    it('still rejects an unknown path next to an import alias', async () => {
        const found = await publish(`state Root { state M { import "mod.fcstm" as Mod; [*] -> Mod; }
            state Q; [*] -> Q; Q -> M : if [active("Root.M.Nothing")]; M -> Q :: Back; }`);
        assert.deepEqual(found.filter(item => item.code === 'E_ACTIVE_QUERY_TARGET').map(item => item.data?.reason), ['not_found']);
    });

    it('does not crash the editor on a document that only uses active queries', async () => {
        const document = createDocument(`def int n = 0;
            state Root { state A; state B { during { if [active("Root.A")] { n = 1; } } }
              [*] -> A; A -> B : if [n > 0]; B -> A :: Back; }`, '/tmp/region-actions.fcstm');
        const actions = await editorModule.collectCodeActions(document, {
            start: {line: 0, character: 0}, end: {line: 3, character: 0},
        }, []);
        assert.ok(Array.isArray(actions));
    });
});

describe('structural inspector support', () => {
    it('refuses machines with regions or active queries explicitly', async () => {
        for (const source of [
            'state Root { region A { state X; [*] -> X; } }',
            'state Root { state A; [*] -> A; A -> A : if [active("Root.A")]; }',
        ]) {
            const ast = await packageModule.parseAstDocument(createDocument(source, '/tmp/inspect.fcstm'));
            const machine = packageModule.buildStateMachineModel(ast!)!;
            assert.equal(diagnosticsModule.isInspectable(machine), false);
            assert.throws(() => diagnosticsModule.inspectModel(machine), /does not support machines with regions or active\(\) queries/);
        }
        const plain = packageModule.buildStateMachineModel(
            (await packageModule.parseAstDocument(createDocument('state Root { state A; [*] -> A; }', '/tmp/plain.fcstm')))!)!;
        assert.equal(diagnosticsModule.isInspectable(plain), true);
        assert.equal(diagnosticsModule.inspectModel(plain).root_state_path, 'Root');
    });
});

describe('queries shared by one transition and the public inspect collector', () => {
    it('reports a bad query of a guard-only combo trigger once', async () => {
        const document = createDocument(
            'state Root { state On; [*] -> On; On -> [*] : [active("Root.Missing")]; }', '/tmp/region-combo.fcstm');
        const ast = await packageModule.parseAstDocument(document);
        const found = editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(
            packageModule.buildSemanticDocument(ast!)!, document).filter(item => item.code === 'E_ACTIVE_QUERY_TARGET');
        assert.equal(found.length, 1);
    });

    it('returns no inspect diagnostics for machines with regions or active queries', async () => {
        for (const source of [
            'state Root { region A { state X; [*] -> X; } }',
            'state Root { state A; [*] -> A; A -> A : if [active("Root.A")]; }',
        ]) {
            const document = createDocument(source, '/tmp/inspect-collector.fcstm');
            const ast = await packageModule.parseAstDocument(document);
            const semantic = packageModule.buildSemanticDocument(ast!)!;
            const machine = packageModule.buildStateMachineModel(ast!)!;
            assert.deepEqual(editorModule.collectInspectModelDiagnostics(document, semantic, machine), []);
        }
    });
});


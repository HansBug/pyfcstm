import assert from 'node:assert/strict';
import {createDocument, editorModule, packageModule} from './support';

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

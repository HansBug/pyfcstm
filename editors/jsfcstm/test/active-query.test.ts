import assert from 'node:assert/strict';
import {createDocument, editorModule, packageModule} from './support';

describe('active-state condition syntax', () => {
    for (const [literal, expected] of [
        ['"/Root.Motor.Running"', '/Root.Motor.Running'], ["'Ready'", 'Ready'],
        ['""', ''], [String.raw`"quote\"slash\\tab\t"`, 'quote"slash\\tab\t'],
        [String.raw`"\u72b6\x41\101"`, '状AA'],
    ]) {
        it(`decodes ${literal} as a typed condition atom`, async () => {
            const source = `state Root { during { if [active(${literal})] {} } }`;
            const ast = await packageModule.parseAstDocument(createDocument(source, '/tmp/active.fcstm'));
            const statement = ast!.rootState!.durings[0].operationsList[0];
            assert.equal(statement.kind, 'ifStatement');
            if (statement.kind !== 'ifStatement') throw new Error('expected if statement');
            const condition = statement.branches[0].condition!;
            assert.equal(condition.expressionKind, 'activeStateQuery');
            assert.equal(condition.pyNodeType, 'ActiveStateQuery');
            assert.equal(condition.expressionType, 'cond');
            assert.equal(condition.path, expected);
            assert.equal(source.slice(condition.range.start.character, condition.range.end.character), `active(${literal})`);
        });
    }
    for (const body of [
        '[*] -> A : if [active("B")];', 'A -> B : if [active("A")];',
        'A -> B :: go + [active("A")];', '! A -> B : if [active("A")];',
        'during { if [!active("A") && active("B") || False] {} }',
        'enter { x = (active("A")) ? 1 : 0; }',
        'A -> B effect { if [active("A") iff True] {} }',
        '>> during after { if [(active("A")) ? active("B") : True] {} }',
    ]) {
        it(`parses and explicitly refuses model construction for ${body}`, async () => {
            const document = createDocument(`def int x = 0; state Root { state A; state B; ${body} }`, '/tmp/active-model.fcstm');
            const ast = await packageModule.parseAstDocument(document);
            assert.ok(ast);
            assert.equal(packageModule.buildStateMachineModel(ast), null);
            const diagnostics = editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(
                packageModule.buildSemanticDocument(ast)!, document);
            assert.ok(diagnostics.length > 0);
            assert.ok(diagnostics.every(item => item.code === 'E_UNSUPPORTED_FEATURE' && item.data?.feature === 'active'));
        });
    }
    for (const expression of ['active()', 'active(A)', 'active(1)', 'active("A", "B")',
        'active("A") + 1 > 0', 'active("A") > 0']) {
        it(`rejects invalid query ${expression}`, async () => {
            const result = await packageModule.getParser().parse(`state Root { during { if [${expression}] {} } }`);
            assert.equal(result.success, false);
        });
    }
    for (const word of ['region', 'active']) {
        it(`preserves ${word} as an identifier in ordinary executable models`, async () => {
            const ast = await packageModule.parseAstDocument(createDocument(
                `def int ${word} = 0; state ${word} { state A; [*] -> A; A -> [*] : if [${word} > 0]; }`,
                '/tmp/contextual.fcstm'));
            assert.equal(ast!.variables[0].name, word);
            assert.equal(packageModule.buildStateMachineModel(ast)!.rootState.name, word);
        });
    }
});

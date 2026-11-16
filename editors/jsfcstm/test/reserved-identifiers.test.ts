import assert from 'node:assert/strict';
import {createDocument, packageModule} from './support';

describe('reserved identifiers', () => {
    for (const word of ['region', 'active']) {
        for (const source of [
            `def int ${word} = 0; state Root;`, `state ${word};`,
            `state Root { region ${word} {} }`, `state Root { event ${word}; }`,
            `state Root { enter ${word} {} }`, `state Root { exit abstract ${word}; }`,
            `state Root { during ${word} ref /Root.run; }`,
            `state Root { >> during before ${word} {} }`,
            `state Root { [*] -> ${word}; }`, `state Root { ${word} -> End; }`,
            `state Root { Start -> End :: ${word}; }`,
            `state Root { !${word} -> End; }`, `state Root { [H*] -> Child.${word}; }`,
            `state Root { enter { ${word} = 1; } }`,
            `def int x = ${word} + 1; state Root;`,
        ]) {
            it(`rejects reserved name: ${source}`, async () => {
                const result = await packageModule.getParser().parse(source);
                assert.equal(result.success, false);
            });
        }
    }
    for (const word of ['region', 'active', 'state', 'pseudo', 'enter', 'exit', 'during',
        'before', 'after', 'abstract', 'ref', 'effect', 'if', 'else', 'def', 'var',
        'input', 'control', 'param', 'output', 'event', 'import', 'as', 'named',
        'int', 'float', 'and', 'or', 'not', 'implies', 'iff', 'xor', 'pi', 'E',
        'tau', 'True', 'true', 'TRUE', 'False', 'false', 'FALSE', 'sin', 'log1p']) {
        for (const body of [
            `import "child.fcstm" as ${word};`,
            `import "child.fcstm" as Child { var ${word} -> shared; }`,
            `import "child.fcstm" as Child { var {value, ${word}} -> shared; }`,
            `import "child.fcstm" as Child { var value -> ${word}; }`,
            `import "child.fcstm" as Child { event ${word} -> /Root.done; }`,
            `import "child.fcstm" as Child { event done -> /Root.${word}; }`,
        ]) {
            it(`rejects import keyword: ${body}`, async () => {
                const result = await packageModule.getParser().parse(`state Root { ${body} }`);
                assert.equal(result.success, false);
            });
        }
    }
    for (const word of ['ordinary', 'Active', 'Region', 'active_flag', 'region_count']) {
        it(`retains whole-word case-sensitive identifier ${word}`, async () => {
            const ast = await packageModule.parseAstDocument(createDocument(
                `def int ${word} = 0; state Root { state ${word}; [*] -> ${word}; }`, '/tmp/names.fcstm'));
            assert.equal(ast!.definitions[0].name, word);
            assert.equal(ast!.rootState!.substates[0].name, word);
        });
    }
});

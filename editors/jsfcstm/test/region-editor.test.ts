import assert from 'node:assert/strict';

import {createDocument, editorModule, packageModule} from './support';

const CONTROLLER = `input int fault;
input int requested;
control int permit = 0;
output int motor = 0;

state Controller {
    event Start;
    event Stop;
    [*] -> Idle;
    state Idle { during { motor = 0; } }

    state Running {
        enter { permit = 0; }
        region Safety {
            >> during before { permit = 1; }
            [*] -> Normal;
            state Normal {
                during {
                    if [fault != 0] { permit = 0; }
                }
            }
            state Tripped;
            Normal -> Tripped : if [fault != 0];
        }
        region Motion {
            event Kick;
            [*] -> Off;
            state Off { during { motor = 0; } }
            state On {
                during {
                    if [active("Controller.Running.Safety.Tripped")] { motor = 0; }
                    else { motor = 1; }
                }
            }
            Off -> On : if [permit != 0 && requested != 0];
            On -> Off : if [active("/Running.Safety.Tripped")];
            On -> Off : Kick;
        }
    }

    Idle -> Running : /Start;
    !Running -> Idle : /Stop;
}
`;

async function foldingOf(source: string) {
    return packageModule.collectFoldingRanges(createDocument(source, '/tmp/region-editor.fcstm'));
}

async function codesOf(source: string) {
    const document = createDocument(source, '/tmp/region-editor.fcstm');
    const ast = await packageModule.parseAstDocument(document);
    assert.ok(ast);
    return editorModule.collectSemanticAnalysisDiagnosticsFromSemantic(
        packageModule.buildSemanticDocument(ast!)!, document);
}

describe('folding ranges of regions', () => {
    it('folds a region block like a state block, from its line to the closing brace', async () => {
        const ranges = await foldingOf(CONTROLLER);
        const pairs = ranges.map(item => [item.startLine, item.endLine]);
        assert.deepEqual(pairs, [[5, 42], [11, 38], [13, 23], [16, 20], [24, 37], [28, 33], [30, 31]]);
        assert.ok(ranges.every(item => item.kind === 'region'));
    });

    it('folds a region nested inside a state of a region', async () => {
        const ranges = await foldingOf(`state Root {
    state Outer {
        region A {
            state Inner {
                region B {
                    state X;
                    [*] -> X;
                }
            }
            [*] -> Inner;
        }
    }
    [*] -> Outer;
}`);
        assert.deepEqual(ranges.map(item => [item.startLine, item.endLine]),
            [[0, 13], [1, 11], [2, 10], [3, 8], [4, 7]]);
    });

    it('leaves a one-line region unfolded', async () => {
        const ranges = await foldingOf('state Root { region A { state X; [*] -> X; } [*] -> A; }');
        assert.deepEqual(ranges, []);
    });

    it('does not change the ranges of a document without regions', async () => {
        const ranges = await foldingOf(`state Root {
    [*] -> A;
    state A {
        enter {
            x = 1;
        }
    }
}`);
        assert.deepEqual(ranges.map(item => [item.startLine, item.endLine]), [[0, 7], [2, 6]]);
    });
});

describe('diagnostics that regions do not double up', () => {
    it('reports a duplicate region name once, as E_DUPLICATE_REGION', async () => {
        const found = await codesOf('state Root { region A { state X; [*] -> X; } region A { state Y; [*] -> Y; } }');
        assert.deepEqual(found.filter(item => item.code === 'E_DUPLICATE_REGION').length, 1);
        assert.deepEqual(found.filter(item => item.code === 'E_DUPLICATE_STATE'), []);
    });

    it('still reports a duplicate state inside a region and one beside regions', async () => {
        const found = await codesOf(`state Root { state P {
            region A { state X; state X; [*] -> X; }
            region B { state Y; [*] -> Y; } }
            state P; [*] -> P; }`);
        assert.deepEqual(found.filter(item => item.code === 'E_DUPLICATE_STATE').map(item => item.data?.state_name), ['X', 'P']);
    });

    it('reports an empty region as E_REGION_STRUCTURE only, not as a missing initial transition', async () => {
        const found = await codesOf('state Root { region Empty {} }');
        assert.equal(found.filter(item => item.code === 'E_REGION_STRUCTURE').length, 1);
        assert.deepEqual(found.filter(item => item.code === 'E_INITIAL_TRANSITION_INVALID'), []);
    });

    it('still asks a region that has states for its initial transition', async () => {
        const found = await codesOf('state Root { region F { state X; } region G { state Y; [*] -> Y; } }');
        assert.deepEqual(found.filter(item => item.code === 'E_INITIAL_TRANSITION_INVALID').map(item => item.data?.composite_path), ['Root.F']);
    });

    it('still asks an ordinary composite for its initial transition', async () => {
        const found = await codesOf('state Root { state A { state B; } [*] -> A; }');
        assert.deepEqual(found.filter(item => item.code === 'E_INITIAL_TRANSITION_INVALID').map(item => item.data?.composite_path), ['Root.A']);
    });
});

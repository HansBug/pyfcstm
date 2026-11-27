import assert from 'node:assert/strict';
import {createDocument, packageModule} from './support';

describe('exclusive state region structure', () => {
    for (const statement of ['state Child;', 'import "child.fcstm" as Child;',
        '[*] -> R;', 'A -> B;', 'A -> [*];', '!A -> B;', '! * -> [*];', '[H] -> A;']) {
        for (const before of [false, true]) {
            it(`rejects ${statement} ${before ? 'before' : 'after'} regions`, async () => {
                const region = 'region R { state A; [*] -> A; }';
                const body = before ? `${statement} ${region}` : `${region} ${statement}`;
                const result = await packageModule.getParser().parse(`state Root { ${body} }`);
                assert.equal(result.success, false);
            });
        }
    }
    it('retains interleaved owner declarations and ordered regions', async () => {
        const ast = await packageModule.parseAstDocument(createDocument(`state Root named "Owner" {
            enter setup {} event start;
            region Second { state A; [*] -> A; }
            during before init {} >> during before sample {} ;
            region First { state B; [*] -> B; }
            during after finish {} >> during after observe {} exit cleanup {}
        }`, '/tmp/owner.fcstm'));
        const owner = ast!.rootState!;
        assert.deepEqual(owner.regions.map(item => item.name), ['Second', 'First']);
        assert.deepEqual(owner.enters.map(item => item.name), ['setup']);
        assert.deepEqual(owner.durings.map(item => item.name), ['init', 'finish']);
        assert.deepEqual(owner.duringAspects.map(item => item.name), ['sample', 'observe']);
        assert.deepEqual(owner.exits.map(item => item.name), ['cleanup']);
        assert.deepEqual(owner.events.map(item => item.name), ['start']);
        assert.deepEqual(owner.statements.map(item => item.kind), [
            'action', 'eventDefinition', 'regionDefinition', 'action', 'action',
            'regionDefinition', 'action', 'action', 'action',
        ]);
    });
});

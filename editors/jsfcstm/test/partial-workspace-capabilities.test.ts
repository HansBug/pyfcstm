import assert from 'node:assert/strict';
import {buildStateMachineModelFromWorkspaceSnapshot} from '../src/workspace/model-assembly';
import {createDocument, packageModule} from './support';

describe('partial workspace capability boundaries', () => {
    it('does not produce a model for an absent or unparsed workspace root', () => {
        const file = '/tmp/absent.fcstm';
        for (const nodes of [{}, {[file]: {}}, {[file]: {ast: null, semantic: null}}]) {
            assert.equal(buildStateMachineModelFromWorkspaceSnapshot({nodes} as any, file), null);
        }
    });

    it('builds a region model when the semantic snapshot is unavailable', async () => {
        const file = '/tmp/partial-region.fcstm';
        const ast = await packageModule.parseAstDocument(createDocument(
            'state Root { region Motor { state Idle; [*] -> Idle; } }', file));
        assert.ok(ast);
        const model = buildStateMachineModelFromWorkspaceSnapshot({nodes: {
            [file]: {ast, semantic: null},
        }} as any, file);
        assert.ok(model);
        assert.deepEqual(Object.keys(model.rootState.regions), ['Motor']);
    });
});

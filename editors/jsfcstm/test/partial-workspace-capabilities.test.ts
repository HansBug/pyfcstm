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

    it('still rejects unsupported syntax when the semantic snapshot is unavailable', async () => {
        const file = '/tmp/partial-region.fcstm';
        const ast = await packageModule.parseAstDocument(createDocument('state Root { region Motor {} }', file));
        assert.ok(ast);
        assert.equal(buildStateMachineModelFromWorkspaceSnapshot({nodes: {
            [file]: {ast, semantic: null},
        }} as any, file), null);
    });
});

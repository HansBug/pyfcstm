import assert from 'node:assert/strict';

import {
    createDocument,
    packageModule,
    withPatchedProperty,
} from './support';

interface DecodedSemanticToken {
    line: number;
    character: number;
    length: number;
    type: string;
}

function decodeSemanticTokens(tokens: {data: number[]}, legend: {tokenTypes: string[]}): DecodedSemanticToken[] {
    const decoded: DecodedSemanticToken[] = [];
    let line = 0;
    let character = 0;

    for (let index = 0; index < tokens.data.length; index += 5) {
        line += tokens.data[index];
        character = tokens.data[index] === 0
            ? character + tokens.data[index + 1]
            : tokens.data[index + 1];
        decoded.push({
            line,
            character,
            length: tokens.data[index + 2],
            type: legend.tokenTypes[tokens.data[index + 3]],
        });
    }

    return decoded;
}

describe('jsfcstm editor experience helpers', () => {
    it('collects folding ranges from AST regions and multiline comments, with comment fallback', async () => {
        const graph = packageModule.getWorkspaceGraph();
        const document = createDocument([
            '/* header',
            ' * details */',
            'state Root {',
            '    import "./worker.fcstm" as Worker {',
            '        event Start -> /Mounted.Start;',
            '    }',
            '    enter Setup {',
            '        if [counter > 0] {',
            '            counter = counter - 1;',
            '        } else {',
            '            counter = 0;',
            '        }',
            '    }',
            '}',
        ].join('\n'), '/tmp/folding.fcstm');
        const snapshot = {
            rootFile: '/tmp/folding.fcstm',
            nodes: {
                '/tmp/folding.fcstm': {
                    ast: {
                        kind: 'document',
                        range: packageModule.createRange(0, 0, 13, 1),
                        rootState: {
                            kind: 'stateDefinition',
                            range: packageModule.createRange(2, 0, 13, 1),
                            imports: [{
                                kind: 'importStatement',
                                range: packageModule.createRange(3, 4, 5, 5),
                            }],
                            enters: [{
                                kind: 'action',
                                range: packageModule.createRange(6, 4, 12, 5),
                                operationBlock: {
                                    kind: 'operationBlock',
                                    range: packageModule.createRange(6, 16, 12, 5),
                                    statements: [{
                                        kind: 'ifStatement',
                                        range: packageModule.createRange(7, 8, 11, 9),
                                        branches: [
                                            {
                                                kind: 'ifBranch',
                                                range: packageModule.createRange(7, 8, 9, 9),
                                            },
                                            {
                                                kind: 'ifBranch',
                                                range: packageModule.createRange(9, 15, 11, 9),
                                            },
                                        ],
                                    }],
                                },
                            }],
                        },
                    },
                },
            },
        };

        await withPatchedProperty(graph, 'buildSnapshotForDocument', async () => snapshot, async () => {
            const ranges = await packageModule.collectFoldingRanges(document);
            assert.deepEqual(ranges, [
                {startLine: 0, endLine: 1, kind: 'comment'},
                {startLine: 2, endLine: 13, kind: 'region'},
                {startLine: 3, endLine: 5, kind: 'imports'},
                {startLine: 6, endLine: 12, kind: 'region'},
                {startLine: 7, endLine: 9, kind: 'region'},
                {startLine: 7, endLine: 11, kind: 'region'},
                {startLine: 9, endLine: 11, kind: 'region'},
            ]);
        });

        await withPatchedProperty(graph, 'buildSnapshotForDocument', async () => ({
            rootFile: '/tmp/folding.fcstm',
            nodes: {
                '/tmp/folding.fcstm': {
                    ast: null,
                },
            },
        }), async () => {
            const ranges = await packageModule.collectFoldingRanges(document);
            assert.deepEqual(ranges, [
                {startLine: 0, endLine: 1, kind: 'comment'},
            ]);
        });
    });

    it('collects nested selection ranges and falls back to a point selection when needed', async () => {
        const graph = packageModule.getWorkspaceGraph();
        const document = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '}',
            '',
        ].join('\n'), '/tmp/selection.fcstm');

        await withPatchedProperty(graph, 'buildSnapshotForDocument', async () => ({
            rootFile: '/tmp/selection.fcstm',
            nodes: {
                '/tmp/selection.fcstm': {
                    ast: {
                        kind: 'document',
                        range: packageModule.createRange(0, 0, 2, 1),
                        rootState: {
                            kind: 'stateDefinition',
                            range: packageModule.createRange(0, 0, 2, 1),
                            imports: [{
                                kind: 'importStatement',
                                range: packageModule.createRange(1, 4, 1, 37),
                            }],
                        },
                    },
                },
            },
        }), async () => {
            const [aliasRange] = await packageModule.collectSelectionRanges(document, [{
                line: 1,
                character: 33,
            }]);
            assert.deepEqual(aliasRange.range, packageModule.createRange(1, 31, 1, 37));
            assert.deepEqual(aliasRange.parent?.range, packageModule.createRange(1, 4, 1, 37));
            assert.deepEqual(aliasRange.parent?.parent?.range, packageModule.createRange(0, 0, 2, 1));

            const [pointRange] = await packageModule.collectSelectionRanges(document, [{
                line: 3,
                character: 0,
            }]);
            assert.deepEqual(pointRange.range, packageModule.createRange(3, 0, 3, 0));
            assert.equal(pointRange.parent, undefined);
        });
    });

    it('collects semantic tokens for lexical constructs and semantic symbol occurrences', async () => {
        const document = createDocument([
            '/* block',
            'comment */',
            'def int counter = 0;',
            '// line comment',
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '    enter Setup {',
            '        counter = counter + 1;',
            '    }',
            '    event Start named "Go";',
            '    Child -> Root :: Tick;',
            '}',
        ].join('\n'), '/tmp/semantic-tokens.fcstm');
        const referencesModule = require('../dist/editor/references.js') as typeof import('../dist/editor/references');
        const legend = packageModule.getFcstmSemanticTokensLegend();

        await withPatchedProperty(referencesModule, 'collectSymbolOccurrences', async () => ([
            {
                key: 'state:Root',
                kind: 'state',
                name: 'Root',
                qualifiedName: 'Root',
                filePath: '/tmp/semantic-tokens.fcstm',
                range: packageModule.createRange(4, 6, 4, 10),
                role: 'definition',
                renameable: true,
            },
            {
                key: 'import:Worker',
                kind: 'import',
                name: 'Worker',
                qualifiedName: 'Root.Worker',
                filePath: '/tmp/semantic-tokens.fcstm',
                range: packageModule.createRange(5, 31, 5, 37),
                role: 'definition',
                renameable: true,
            },
            {
                key: 'action:Setup',
                kind: 'action',
                name: 'Setup',
                qualifiedName: 'Root.Setup',
                filePath: '/tmp/semantic-tokens.fcstm',
                range: packageModule.createRange(6, 10, 6, 15),
                role: 'definition',
                renameable: true,
            },
            {
                key: 'var:counter',
                kind: 'variable',
                name: 'counter',
                qualifiedName: 'counter',
                filePath: '/tmp/semantic-tokens.fcstm',
                range: packageModule.createRange(2, 8, 2, 15),
                role: 'definition',
                renameable: true,
            },
            {
                key: 'event:Start',
                kind: 'event',
                name: 'Start',
                qualifiedName: 'Root.Start',
                filePath: '/tmp/semantic-tokens.fcstm',
                range: packageModule.createRange(9, 10, 9, 15),
                role: 'definition',
                renameable: true,
            },
        ]), async () => {
            const tokens = await packageModule.collectSemanticTokens(document);
            const decoded = decodeSemanticTokens(tokens, legend);
            const types = new Set(decoded.map(item => item.type));

            assert.deepEqual(legend.tokenTypes, [
                'keyword',
                'type',
                'class',
                'function',
                'variable',
                'property',
                'namespace',
                'string',
                'comment',
                'operator',
            ]);
            assert.ok(types.has('comment'));
            assert.ok(types.has('string'));
            assert.ok(types.has('keyword'));
            assert.ok(types.has('type'));
            assert.ok(types.has('operator'));
            assert.ok(types.has('class'));
            assert.ok(types.has('namespace'));
            assert.ok(types.has('function'));
            assert.ok(types.has('variable'));
            assert.ok(types.has('property'));
        });
    });
});

import assert from 'node:assert/strict';

import {
    createDocument,
    createLeafTextNode,
    createNode,
    createToken,
    packageModule,
    withPatchedProperty,
} from './support';

describe('jsfcstm symbol extraction', () => {
    it('collects flattened symbol names from parse trees, including duplicates and ignored nodes', () => {
        const tree = createNode('StateMachineDSLProgramContext', [
            createNode('Def_assignmentContext', [
                createLeafTextNode('def'),
                createLeafTextNode('int'),
                createLeafTextNode('counter'),
            ]),
            createNode('Def_assignmentContext', [
                createLeafTextNode('def'),
                createLeafTextNode('int'),
                createLeafTextNode('counter'),
            ]),
            createNode('CompositeStateDefinitionContext', [
                createLeafTextNode('state'),
                createLeafTextNode('Root'),
                undefined as unknown as packageModule.ParseTreeNode,
            ]),
            createNode('LeafStateDefinitionContext', [
                createLeafTextNode('state'),
                createLeafTextNode('Child'),
            ]),
            createNode('Event_definitionContext', [
                createLeafTextNode('event'),
                createLeafTextNode('Start'),
            ]),
            createNode('UnknownContext', [
                createLeafTextNode('ignored'),
            ]),
        ]);

        const symbols = packageModule.collectSymbolsFromTree(tree);
        assert.deepEqual(symbols.variables, ['counter']);
        assert.deepEqual(symbols.states.sort(), ['Child', 'Root']);
        assert.deepEqual(symbols.events, ['Start']);
    });

    it('extracts document symbols for variables, states, events, pseudo states, and named items', () => {
        const document = createDocument([
            'def int counter = 0;',
            'state Root named "System Root" {',
            '    event Start named "Start Event";',
            '    pseudo state Junction;',
            '    state Child;',
            '}',
        ].join('\n'), '/tmp/symbols.fcstm');

        const tree = createNode('StateMachineDSLProgramContext', [
            createNode('Def_assignmentContext', [
                createLeafTextNode('def'),
                createLeafTextNode('int'),
                createLeafTextNode('counter'),
            ], {
                start: createToken('def', 1, 0),
                stop: createToken(';', 1, 19),
            }),
            createNode('CompositeStateDefinitionContext', [
                createLeafTextNode('state'),
                createLeafTextNode('Root'),
                createLeafTextNode('named'),
                createLeafTextNode('"System Root"'),
                createNode('State_bodyContext', [
                    createNode('Event_definitionContext', [
                        createLeafTextNode('event'),
                        createLeafTextNode('Start'),
                        createLeafTextNode('named'),
                        createLeafTextNode('"Start Event"'),
                    ], {
                        start: createToken('event', 3, 4),
                        stop: createToken(';', 3, 35),
                    }),
                    createNode('LeafStateDefinitionContext', [
                        createLeafTextNode('pseudo'),
                        createLeafTextNode('state'),
                        createLeafTextNode('Junction'),
                    ], {
                        start: createToken('pseudo', 4, 4),
                        stop: createToken(';', 4, 25),
                    }),
                    createNode('LeafStateDefinitionContext', [
                        createLeafTextNode('state'),
                        createLeafTextNode('Child'),
                    ], {
                        start: createToken('state', 5, 4),
                        stop: createToken(';', 5, 15),
                    }),
                ]),
            ], {
                start: createToken('state', 2, 0),
                stop: createToken('}', 6, 0),
            }),
        ]);

        const symbols = packageModule.extractDocumentSymbolsFromTree(tree, document);
        assert.equal(symbols.length, 2);
        assert.equal(symbols[0].name, 'counter');
        assert.equal(symbols[0].detail, 'int');
        assert.equal(symbols[1].name, 'Root');
        assert.equal(symbols[1].detail, 'System Root');
        assert.ok(symbols[1].children.some(item => item.name === 'Start' && item.detail === 'Start Event'));
        assert.ok(symbols[1].children.some(item => item.name === 'Junction' && item.detail === 'pseudo state'));
        assert.ok(symbols[1].children.some(item => item.name === 'Child' && item.kind === 'class'));
    });

    it('gracefully skips malformed symbol nodes through internal catch branches', () => {
        const document = createDocument('state Root;', '/tmp/malformed-symbols.fcstm');
        const throwingNode = createNode('LeafStateDefinitionContext', [{
            getText() {
                throw new Error('boom');
            },
        } as packageModule.ParseTreeNode], {
            start: createToken('state', 1, 0),
            stop: createToken(';', 1, 10),
        });

        const tree = createNode('StateMachineDSLProgramContext', [
            createNode('Def_assignmentContext', [{
                getText() {
                    throw new Error('boom');
                },
            } as packageModule.ParseTreeNode], {
                start: createToken('def', 1, 0),
                stop: createToken(';', 1, 10),
            }),
            createNode('CompositeStateDefinitionContext', [
                createLeafTextNode('state'),
                createLeafTextNode('Root'),
                createNode('State_bodyContext', [
                    createNode('Event_definitionContext', [{
                        getText() {
                            throw new Error('boom');
                        },
                    } as packageModule.ParseTreeNode], {
                        start: createToken('event', 1, 0),
                        stop: createToken(';', 1, 10),
                    }),
                    throwingNode,
                ]),
            ], {
                start: createToken('state', 1, 0),
                stop: createToken(';', 1, 10),
            }),
        ]);

        const symbols = packageModule.extractDocumentSymbolsFromTree(tree, document);
        assert.equal(symbols.length, 1);
        assert.equal(symbols[0].name, 'Root');
        assert.equal(symbols[0].children.length, 0);
    });

    it('returns null-equivalent results for incomplete variable, event, and state nodes', () => {
        const document = createDocument('state Root;', '/tmp/incomplete-symbols.fcstm');
        const tree = createNode('StateMachineDSLProgramContext', [
            createNode('Def_assignmentContext', [
                createLeafTextNode('def'),
                createLeafTextNode('int'),
            ], {
                start: createToken('def', 1, 0),
                stop: createToken(';', 1, 3),
            }),
            createNode('LeafStateDefinitionContext', [
                createLeafTextNode('state'),
            ], {
                start: createToken('state', 1, 0),
                stop: createToken(';', 1, 5),
            }),
            createNode('CompositeStateDefinitionContext', [
                createLeafTextNode('state'),
                createLeafTextNode('Root'),
                createNode('State_bodyContext', [
                    createNode('Event_definitionContext', [
                        createLeafTextNode('event'),
                    ], {
                        start: createToken('event', 1, 0),
                        stop: createToken(';', 1, 5),
                    }),
                ]),
            ], {
                start: createToken('state', 1, 0),
                stop: createToken('}', 1, 10),
            }),
        ]);

        const flatSymbols = packageModule.collectSymbolsFromTree(tree);
        assert.deepEqual(flatSymbols.variables, []);
        assert.deepEqual(flatSymbols.events, []);
        assert.deepEqual(flatSymbols.states, ['Root']);

        const documentSymbols = packageModule.extractDocumentSymbolsFromTree(tree, document);
        assert.equal(documentSymbols.length, 1);
        assert.equal(documentSymbols[0].name, 'Root');
        assert.equal(documentSymbols[0].children.length, 0);
    });

    it('handles sparse parse tree nodes while extracting document symbols', () => {
        const document = createDocument('state Root;', '/tmp/sparse-symbols.fcstm');
        const sparseTree = createNode('StateMachineDSLProgramContext', [
            {constructor: {name: 'Def_assignmentContext'}} as packageModule.ParseTreeNode,
            createNode('LeafStateDefinitionContext', [
                createLeafTextNode('state'),
                {} as packageModule.ParseTreeNode,
            ]),
            createNode('Event_definitionContext', [
                createLeafTextNode('event'),
                {} as packageModule.ParseTreeNode,
            ]),
            createNode('CompositeStateDefinitionContext', [
                createLeafTextNode('state'),
                createLeafTextNode('Root'),
                createLeafTextNode('named'),
                {} as packageModule.ParseTreeNode,
                {constructor: {name: 'State_bodyContext'}} as packageModule.ParseTreeNode,
                createNode('State_bodyContext', [
                    {} as packageModule.ParseTreeNode,
                    createNode('Event_definitionContext', [
                        createLeafTextNode('event'),
                        createLeafTextNode('Start'),
                        createLeafTextNode('named'),
                        {} as packageModule.ParseTreeNode,
                    ]),
                    createNode('LeafStateDefinitionContext', [
                        createLeafTextNode('state'),
                        {} as packageModule.ParseTreeNode,
                    ]),
                    createNode('CompositeStateDefinitionContext', [
                        createLeafTextNode('state'),
                        createLeafTextNode('Nested'),
                    ]),
                ]),
            ]),
            {} as packageModule.ParseTreeNode,
        ]);

        assert.deepEqual(packageModule.collectSymbolsFromTree({} as packageModule.ParseTreeNode), {
            variables: [],
            states: [],
            events: [],
        });
        assert.deepEqual(packageModule.extractDocumentSymbolsFromTree({} as packageModule.ParseTreeNode, document), []);

        const symbols = packageModule.extractDocumentSymbolsFromTree(sparseTree, document);
        assert.equal(symbols.length, 1);
        assert.equal(symbols[0].name, 'Root');
        assert.equal(symbols[0].detail, '');
        assert.ok(symbols[0].children.some(item => item.name === 'Start' && item.detail === ''));
        assert.ok(symbols[0].children.some(item => item.name === 'Nested' && item.kind === 'class'));
    });

    it('collects document symbols through the public parser-backed entry point', async () => {
        const document = createDocument(
            'def int counter = 0;\nstate Root { event Start; state Child; }',
            '/tmp/public-symbols.fcstm'
        );

        const symbols = await packageModule.collectDocumentSymbols(document);
        assert.equal(symbols.length, 2);
        assert.equal(symbols[0].name, 'counter');
        assert.equal(symbols[1].name, 'Root');
    });

    it('returns an empty list when collectDocumentSymbols cannot build a parse tree', async () => {
        const parser = packageModule.getParser();
        const document = createDocument('state Root;', '/tmp/no-tree.fcstm');

        await withPatchedProperty(parser, 'parseTree', async () => null, async () => {
            const symbols = await packageModule.collectDocumentSymbols(document);
            assert.deepEqual(symbols, []);
        });
    });

    it('collects semantic document symbols for pseudo states and declared events', async () => {
        const document = createDocument('state Root;', '/tmp/semantic-symbols.fcstm');
        const rootRange = packageModule.createRange(0, 0, 0, 10);
        const eventRange = packageModule.createRange(0, 2, 0, 8);
        const rootStateId = 'state:/tmp/semantic-symbols.fcstm:Root:1';
        const pseudoStateId = 'state:/tmp/semantic-symbols.fcstm:Root.Junction:2';
        const semantic = {
            variables: [],
            states: [
                {
                    identity: {
                        id: rootStateId,
                        kind: 'state',
                        name: 'Root',
                        qualifiedName: 'Root',
                        path: ['Root'],
                    },
                    name: 'Root',
                    displayName: 'System Root',
                    pseudo: false,
                    composite: true,
                    range: rootRange,
                    childStateIds: [pseudoStateId],
                },
                {
                    identity: {
                        id: pseudoStateId,
                        kind: 'state',
                        name: 'Junction',
                        qualifiedName: 'Root.Junction',
                        path: ['Root', 'Junction'],
                    },
                    name: 'Junction',
                    pseudo: true,
                    composite: false,
                    range: rootRange,
                    parentStateId: rootStateId,
                    childStateIds: [],
                },
            ],
            events: [
                {
                    identity: {
                        id: 'event:/tmp/semantic-symbols.fcstm:Root.Start:3',
                        kind: 'event',
                        name: 'Start',
                        qualifiedName: 'Root.Start',
                        path: ['Root', 'Start'],
                    },
                    name: 'Start',
                    displayName: 'Start Event',
                    range: eventRange,
                    statePath: ['Root'],
                    declared: true,
                    origins: ['declared'],
                },
            ],
        } as unknown as packageModule.FcstmSemanticDocument;
        const graph = packageModule.getWorkspaceGraph();

        await withPatchedProperty(graph, 'getSemanticDocument', async () => semantic, async () => {
            const symbols = await packageModule.collectDocumentSymbols(document);
            assert.equal(symbols.length, 1);
            assert.equal(symbols[0].name, 'Root');
            assert.equal(symbols[0].detail, 'System Root');
            assert.ok(symbols[0].children.some(item => item.name === 'Start' && item.detail === 'Start Event'));
            assert.ok(symbols[0].children.some(item => item.name === 'Junction' && item.detail === 'pseudo state'));
        });
    });
});

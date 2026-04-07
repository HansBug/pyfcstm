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
});

import assert from 'node:assert/strict';

import {
    createDocument,
    createLeafTextNode,
    createNode,
    createToken,
    packageModule,
} from './support';

describe('jsfcstm AST builder', () => {
    it('builds a structured AST for variables, actions, forced transitions, and imports', async () => {
        const document = createDocument([
            'def int counter = 0;',
            'def float temperature = 25.5;',
            'state Root named "System Root" {',
            '    event Start named "Start Event";',
            '    enter Init {',
            '        counter = counter + 1;',
            '        if [counter > 0] {',
            '            temperature = temperature + 1.0;',
            '        } else {',
            '            temperature = 0.0;',
            '        }',
            '    }',
            '    during before ref /Shared.Setup;',
            '    !* -> [*] : /Fault;',
            '    import "./worker.fcstm" as Worker named "Worker Module" {',
            '        def sensor_* -> io_$1;',
            '        event /Start -> /Bus.Start named "Bus Start";',
            '    }',
            '    pseudo state Junction;',
            '}',
        ].join('\n'), '/tmp/ast.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        assert.ok(ast);
        assert.equal(ast?.pyNodeType, 'StateMachineDSLProgram');
        assert.equal(ast?.definitions, ast?.variables);
        assert.equal(ast?.root_state, ast?.rootState);
        assert.equal(ast?.variables.length, 2);
        assert.deepEqual(ast?.variables.map(item => [item.name, item.valueType]), [
            ['counter', 'int'],
            ['temperature', 'float'],
        ]);
        assert.deepEqual(ast?.variables.map(item => [item.pyNodeType, item.deftype, item.expr.pyNodeType]), [
            ['DefAssignment', 'int', 'Integer'],
            ['DefAssignment', 'float', 'Float'],
        ]);
        assert.equal(ast?.rootState?.name, 'Root');
        assert.equal(ast?.rootState?.displayName, 'System Root');
        assert.equal(ast?.rootState?.pyNodeType, 'StateDefinition');
        assert.equal(ast?.rootState?.extra_name, 'System Root');
        assert.equal(ast?.rootState?.composite, true);
        assert.equal(ast?.rootState?.enters.length, 1);
        assert.equal(ast?.rootState?.durings.length, 1);
        assert.equal(ast?.rootState?.force_transitions.length, 1);
        assert.equal(ast?.rootState?.imports.length, 1);
        assert.equal(ast?.rootState?.substates.length, 1);

        const statements = ast?.rootState?.statements || [];
        const event = statements.find(item => item.kind === 'eventDefinition');
        assert.equal(event?.kind, 'eventDefinition');
        assert.equal(event?.displayName, 'Start Event');
        assert.equal(event?.pyNodeType, 'EventDefinition');
        assert.equal(event?.extra_name, 'Start Event');

        const enterAction = statements.find(item => item.kind === 'action' && item.stage === 'enter');
        assert.equal(enterAction?.kind, 'action');
        assert.equal(enterAction?.name, 'Init');
        assert.equal(enterAction?.pyNodeType, 'EnterOperations');
        assert.equal(enterAction?.operationsList, enterAction?.operations?.statements);
        assert.equal(enterAction?.operations?.statements.length, 2);
        const ifStatement = enterAction?.operations?.statements[1];
        assert.equal(ifStatement?.kind, 'ifStatement');
        assert.equal(ifStatement?.pyNodeType, 'OperationIf');
        assert.equal(ifStatement?.branches.length, 2);
        assert.equal(ifStatement?.branches[0].pyNodeType, 'OperationIfBranch');
        assert.equal(ifStatement?.branches[0].condition?.pyNodeType, 'BinaryOp');
        assert.equal(ifStatement?.branches[1].condition, null);
        assert.equal(ifStatement?.branches[1].statements.length, 1);
        assert.ok(ifStatement?.elseBlock);

        const refAction = statements.find(item => item.kind === 'action' && item.mode === 'ref');
        assert.equal(refAction?.kind, 'action');
        assert.equal(refAction?.refPath?.text, '/Shared.Setup');
        assert.equal(refAction?.pyNodeType, 'DuringRefFunction');
        assert.equal(refAction?.ref, refAction?.refPath);
        assert.equal(refAction?.aspect, 'before');

        const forcedTransition = statements.find(item => item.kind === 'forcedTransition');
        assert.equal(forcedTransition?.kind, 'forcedTransition');
        assert.equal(forcedTransition?.pyNodeType, 'ForceTransitionDefinition');
        assert.equal(forcedTransition?.transitionKind, 'exitAll');
        assert.equal(forcedTransition?.sourceKind, 'all');
        assert.equal(forcedTransition?.targetKind, 'exit');
        assert.equal(forcedTransition?.trigger?.kind, 'chainTrigger');
        assert.equal(forcedTransition?.trigger?.eventPath.text, '/Fault');
        assert.equal(forcedTransition?.from_state, 'ALL');
        assert.equal(forcedTransition?.to_state, 'EXIT_STATE');
        assert.equal(forcedTransition?.event_id?.pyNodeType, 'ChainID');
        assert.deepEqual(forcedTransition?.event_id?.path, ['Fault']);

        const importStatement = statements.find(item => item.kind === 'importStatement');
        assert.equal(importStatement?.kind, 'importStatement');
        assert.equal(importStatement?.pyNodeType, 'ImportStatement');
        assert.equal(importStatement?.sourcePath, './worker.fcstm');
        assert.equal(importStatement?.source_path, './worker.fcstm');
        assert.equal(importStatement?.alias, 'Worker');
        assert.equal(importStatement?.displayName, 'Worker Module');
        assert.equal(importStatement?.extra_name, 'Worker Module');
        assert.deepEqual(importStatement?.pathRange.start, {line: 14, character: 11});
        assert.deepEqual(importStatement?.aliasRange.start, {line: 14, character: 31});
        assert.equal(importStatement?.mappings.length, 2);
        assert.equal(importStatement?.mappings[0].kind, 'importDefMapping');
        assert.equal(importStatement?.mappings[0].pyNodeType, 'ImportDefMapping');
        assert.equal(importStatement?.mappings[0].selector.kind, 'importDefPatternSelector');
        assert.equal(importStatement?.mappings[0].selector.pyNodeType, 'ImportDefPatternSelector');
        assert.equal(importStatement?.mappings[0].selector.pattern, 'sensor_*');
        assert.equal(importStatement?.mappings[0].targetTemplate, 'io_$1');
        assert.equal(importStatement?.mappings[0].target_template.pyNodeType, 'ImportDefTargetTemplate');
        assert.equal(importStatement?.mappings[0].target_template.template, 'io_$1');
        assert.equal(importStatement?.mappings[1].kind, 'importEventMapping');
        assert.equal(importStatement?.mappings[1].pyNodeType, 'ImportEventMapping');
        assert.equal(importStatement?.mappings[1].sourceEvent.text, '/Start');
        assert.equal(importStatement?.mappings[1].source_event, importStatement?.mappings[1].sourceEvent);
        assert.equal(importStatement?.mappings[1].targetEvent.text, '/Bus.Start');
        assert.equal(importStatement?.mappings[1].extra_name, 'Bus Start');

        const pseudoState = statements.find(item => item.kind === 'stateDefinition' && item.name === 'Junction');
        assert.equal(pseudoState?.kind, 'stateDefinition');
        assert.equal(pseudoState?.pseudo, true);
        assert.equal(pseudoState?.is_pseudo, true);
    });

    it('returns null when no parse tree can be produced', async () => {
        const parser = packageModule.getParser();
        const document = createDocument('state Root;', '/tmp/no-ast.fcstm');
        const original = parser.parseTree;
        parser.parseTree = async () => null;

        try {
            const ast = await packageModule.parseAstDocument(document);
            assert.equal(ast, null);
        } finally {
            parser.parseTree = original;
        }
    });

    it('covers additional expression, selector, and trigger variants from real DSL', async () => {
        const document = createDocument([
            'def int mask = 0xFF;',
            'state Root {',
            '    enter {',
            '        value = abs(-mask);',
            '        choice = (mask > 0) ? 1 : 0;',
            '        ;',
            '    }',
            '    during {',
            '        constant_value = (pi);',
            '    }',
            '    during abstract Tick;',
            '    during ref Shared.Run;',
            '    import "./worker.fcstm" as Worker {',
            '        def {left,right} -> grouped;',
            '        def exact -> renamed;',
            '        def * -> kept;',
            '        ;',
            '    }',
            '    state A;',
            '    A -> Root;',
            '}',
        ].join('\n'), '/tmp/ast-extra.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const enterAction = ast?.rootState?.enters[0];
        assert.equal(enterAction?.operationsList.length, 3);
        assert.equal(enterAction?.operationsList[0].kind, 'assignmentStatement');
        assert.equal(enterAction?.operationsList[0].expr.pyNodeType, 'UFunc');
        assert.equal(enterAction?.operationsList[0].expr.expr.pyNodeType, 'UnaryOp');
        assert.equal(enterAction?.operationsList[1].expr.pyNodeType, 'ConditionalOp');
        assert.equal(enterAction?.operationsList[1].expr.cond.pyNodeType, 'BinaryOp');
        assert.equal(enterAction?.operationsList[2].kind, 'emptyStatement');

        assert.deepEqual(ast?.rootState?.durings.map(item => item.pyNodeType), [
            'DuringOperations',
            'DuringAbstractFunction',
            'DuringRefFunction',
        ]);
        assert.equal(ast?.rootState?.durings[0].operationsList[0].expr.pyNodeType, 'Paren');
        assert.equal(ast?.rootState?.durings[0].operationsList[0].expr.expr.pyNodeType, 'Constant');

        const importStatement = ast?.rootState?.imports[0];
        assert.equal(importStatement?.mappings.length, 3);
        assert.deepEqual(importStatement?.mappings.map(item => item.pyNodeType), [
            'ImportDefMapping',
            'ImportDefMapping',
            'ImportDefMapping',
        ]);
        assert.equal(importStatement?.mappings[0].selector.pyNodeType, 'ImportDefSetSelector');
        assert.equal(importStatement?.mappings[1].selector.pyNodeType, 'ImportDefExactSelector');
        assert.equal(importStatement?.mappings[2].selector.pyNodeType, 'ImportDefFallbackSelector');

        const plainTransition = ast?.rootState?.transitions[0];
        assert.equal(plainTransition?.trigger, undefined);
        assert.equal(plainTransition?.event_id, undefined);
    });

    it('covers synthetic AST fallback branches that the grammar rarely emits directly', () => {
        const document = createDocument([
            'state Root {',
            '    enter { }',
            '}',
        ].join('\n'), '/tmp/ast-synthetic.fcstm');

        const tree = createNode('StateMachineDSLProgramContext', [
            createNode('CompositeStateDefinitionContext', [
                createNode('State_inner_statementContext', [
                    createNode('EnterOperationsContext', [
                        createNode('Operational_statement_setContext', [
                            createNode('Operational_statementContext', []),
                            createNode('Operational_statementContext', [
                                createNode('Operational_assignmentContext', [
                                    createNode('UnknownExprContext', [], {
                                        start: createToken('mystery', 1, 0),
                                        stop: createToken('mystery', 1, 6),
                                        getText() {
                                            return 'mystery';
                                        },
                                    }),
                                ], {
                                    start: createToken('value', 1, 0),
                                    stop: createToken(';', 1, 14),
                                    getText() {
                                        return 'value=mystery;';
                                    },
                                }),
                            ]),
                            createNode('Operational_statementContext', [
                                createNode('If_statementContext', [
                                    createNode('LiteralExprCondContext', [
                                        createNode('Bool_literalContext', [], {
                                            start: createToken('true', 1, 0),
                                            stop: createToken('true', 1, 3),
                                            getText() {
                                                return 'true';
                                            },
                                        }),
                                    ], {
                                        start: createToken('true', 1, 0),
                                        stop: createToken('true', 1, 3),
                                        getText() {
                                            return 'true';
                                        },
                                    }),
                                    createNode('Operation_blockContext', [], {
                                        start: createToken('{', 1, 8),
                                        stop: createToken('}', 1, 9),
                                        getText() {
                                            return '{}';
                                        },
                                    }),
                            ], {
                                start: createToken('if', 1, 0),
                                stop: createToken('}', 1, 9),
                                getText() {
                                    return 'if[true]{}';
                                },
                            }),
                        ]),
                        ]),
                    ], {
                        start: createToken('enter', 1, 4),
                        stop: createToken('}', 1, 20),
                        getText() {
                            return 'enter{}';
                        },
                    }),
                ]),
                createNode('State_inner_statementContext', [
                    createNode('Import_statementContext', [
                        createNode('Import_mapping_statementContext', [
                            createNode('Import_def_mappingContext', [
                                createNode('ImportDefExactSelectorContext', [], {
                                    selector_name: createToken('exact', 1, 0),
                                    getText() {
                                        return 'exact';
                                    },
                                }),
                                createNode('Import_def_target_templateContext', [], {
                                    target_text: createToken('target', 1, 0),
                                    getText() {
                                        return 'target';
                                    },
                                }),
                            ], {
                                getText() {
                                    return 'def exact -> target;';
                                },
                            }),
                        ]),
                        createNode('Import_mapping_statementContext', []),
                    ], {
                        import_path: createToken('"./worker.fcstm"', 1, 0),
                        state_alias: createToken('Worker', 1, 18),
                        start: createToken('import', 1, 0),
                        stop: createToken('}', 1, 40),
                        getText() {
                            return 'import"./worker.fcstm"asWorker{;}';
                        },
                    }),
                ]),
                createNode('State_inner_statementContext', [
                    createNode('UnknownContext', [
                        createLeafTextNode('ignored'),
                    ]),
                ]),
            ], {
                state_id: createToken('Root', 1, 6),
                extra_name: createToken('RootAlias', 1, 12),
                start: createToken('state', 1, 0),
                stop: createToken('}', 3, 0),
                getText() {
                    return 'stateRoot{}';
                },
            }),
        ], {
            start: createToken('state', 1, 0),
            stop: createToken('}', 3, 0),
            getText() {
                return document.getText();
            },
        });

        const ast = packageModule.buildAstFromTree(tree, document);
        assert.ok(ast);
        assert.equal(ast?.rootState?.displayName, 'RootAlias');
        assert.equal(ast?.rootState?.statements.length, 2);
        assert.equal(ast?.rootState?.enters[0].operationsList[0].kind, 'emptyStatement');
        assert.equal(ast?.rootState?.enters[0].operationsList[1].kind, 'assignmentStatement');
        assert.equal(ast?.rootState?.enters[0].operationsList[1].expr.pyNodeType, 'Name');
        assert.equal(ast?.rootState?.enters[0].operationsList[2].kind, 'ifStatement');
        assert.equal(ast?.rootState?.enters[0].operationsList[2].branches[0].statements.length, 0);
        assert.equal(ast?.rootState?.imports[0].mappings.length, 1);

        assert.equal(packageModule.buildAstFromTree(null as unknown as packageModule.ParseTreeNode, document), null);
    });

    it('covers remaining action pyNodeType variants for enter/exit/during-aspect nodes', async () => {
        const document = createDocument([
            'state Root {',
            '    enter abstract EnterHook;',
            '    exit { ; }',
            '    exit abstract ExitHook;',
            '    exit ref /Shared.Cleanup;',
            '    >> during before { ; }',
            '    >> during after abstract AuditHook;',
            '    >> during before ref /Shared.BeforeHook;',
            '}',
        ].join('\n'), '/tmp/ast-actions.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        assert.deepEqual(ast?.rootState?.statements.map(item => item.kind === 'action' ? item.pyNodeType : item.kind), [
            'EnterAbstractFunction',
            'ExitOperations',
            'ExitAbstractFunction',
            'ExitRefFunction',
            'DuringAspectOperations',
            'DuringAspectAbstractFunction',
            'DuringAspectRefFunction',
        ]);
        assert.equal(ast?.rootState?.exits[0].operationsList[0].kind, 'emptyStatement');
        assert.deepEqual(ast?.rootState?.during_aspects.map(item => item.pyNodeType), [
            'DuringAspectOperations',
            'DuringAspectAbstractFunction',
            'DuringAspectRefFunction',
        ]);
    });
});

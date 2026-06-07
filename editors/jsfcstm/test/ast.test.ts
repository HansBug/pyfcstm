import assert from 'node:assert/strict';

import {
    createDocument,
    createLeafTextNode,
    createNode,
    createToken,
    packageModule,
} from './support';

const COND_PRIORITY_OPERATORS = [
    '==',
    '!=',
    'iff',
    '&&',
    'and',
    'xor',
    '^',
    '||',
    'or',
    '=>',
    'implies',
] as const;

const COND_PRIORITY: Record<string, number> = {
    '==': 50,
    '!=': 50,
    iff: 50,
    '&&': 40,
    and: 40,
    xor: 30,
    '^': 30,
    '||': 20,
    or: 20,
    '=>': 10,
    implies: 10,
};

const COND_RIGHT_ASSOC = new Set(['=>', 'implies']);

const COND_CANONICAL_OP: Record<string, string> = {
    and: '&&',
    or: '||',
    '^': 'xor',
    implies: '=>',
};

function canonicalCondOp(operator: string): string {
    return COND_CANONICAL_OP[operator] || operator;
}

function condAtom(name: string): Record<string, unknown> {
    return {
        pyNodeType: 'BinaryOp',
        op: '>',
        expr1: {pyNodeType: 'Name', name},
        expr2: {pyNodeType: 'Integer', raw: '0'},
    };
}

function expectedCondChain(operators: readonly string[]): Record<string, unknown> {
    const values = [condAtom('a')];
    const ops: string[] = [];

    function reduceOnce(): void {
        const op = ops.pop();
        const right = values.pop();
        const left = values.pop();
        assert.ok(op);
        assert.ok(left);
        assert.ok(right);
        values.push({
            pyNodeType: 'BinaryOp',
            expr1: left,
            op: canonicalCondOp(op),
            expr2: right,
        });
    }

    operators.forEach((op, index) => {
        while (ops.length > 0) {
            const top = ops[ops.length - 1];
            const incomingPrecedence = COND_PRIORITY[op];
            const topPrecedence = COND_PRIORITY[top];
            const shouldReduce = COND_RIGHT_ASSOC.has(op)
                ? incomingPrecedence < topPrecedence
                : incomingPrecedence <= topPrecedence;
            if (!shouldReduce) break;
            reduceOnce();
        }
        ops.push(op);
        values.push(condAtom(['b', 'c', 'd'][index]));
    });

    while (ops.length > 0) {
        reduceOnce();
    }

    assert.equal(values.length, 1);
    return values[0];
}

function condChainText(operators: readonly string[]): string {
    const names = ['a', 'b', 'c', 'd'];
    const parts = [`${names[0]} > 0`];
    operators.forEach((operator, index) => {
        parts.push(operator, `${names[index + 1]} > 0`);
    });
    return parts.join(' ');
}

function normalizeCondExpression(expression: Record<string, any>): Record<string, unknown> {
    switch (expression.pyNodeType) {
        case 'BinaryOp':
            return {
                pyNodeType: 'BinaryOp',
                expr1: normalizeCondExpression(expression.expr1),
                op: expression.op,
                expr2: normalizeCondExpression(expression.expr2),
            };
        case 'Name':
            return {
                pyNodeType: 'Name',
                name: expression.name,
            };
        case 'Integer':
            return {
                pyNodeType: 'Integer',
                raw: expression.raw,
            };
        default:
            throw new Error(`Unexpected expression node: ${expression.pyNodeType}`);
    }
}

function condOperatorChains(): string[][] {
    const chains: string[][] = [];
    for (let length = 1; length <= 3; length += 1) {
        function visit(prefix: string[]): void {
            if (prefix.length === length) {
                chains.push(prefix);
                return;
            }
            for (const operator of COND_PRIORITY_OPERATORS) {
                visit([...prefix, operator]);
            }
        }
        visit([]);
    }
    return chains;
}

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
        assert.equal(enterAction?.operationsList, enterAction?.operations);
        assert.equal(enterAction?.operationBlock?.statements.length, 2);
        assert.equal(enterAction?.operations?.length, 2);
        const ifStatement = enterAction?.operations?.[1];
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
        assert.equal(enterAction?.operationsList.length, 2);
        assert.equal(enterAction?.operationsList[0].kind, 'assignmentStatement');
        assert.equal(enterAction?.operationsList[0].expr.pyNodeType, 'UFunc');
        assert.equal(enterAction?.operationsList[0].expr.expr.pyNodeType, 'UnaryOp');
        assert.equal(enterAction?.operationsList[1].expr.pyNodeType, 'ConditionalOp');
        assert.equal(enterAction?.operationsList[1].expr.cond.pyNodeType, 'BinaryOp');

        assert.deepEqual(ast?.rootState?.durings.map(item => item.pyNodeType), [
            'DuringOperations',
            'DuringAbstractFunction',
            'DuringRefFunction',
        ]);
        assert.equal(ast?.rootState?.durings[0].operationsList[0].expr.pyNodeType, 'Paren');
        assert.equal(ast?.rootState?.durings[0].operationsList[0].expr.expr.pyNodeType, 'Constant');
        assert.equal(ast?.rootState?.durings[1].aspect, undefined);

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
        assert.equal(ast?.rootState?.enters[0].operationsList[0].kind, 'assignmentStatement');
        assert.equal(ast?.rootState?.enters[0].operationsList[0].expr.pyNodeType, 'Name');
        assert.equal(ast?.rootState?.enters[0].operationsList[1].kind, 'ifStatement');
        assert.equal(ast?.rootState?.enters[0].operationsList[1].branches[0].statements.length, 0);
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
        assert.deepEqual(ast?.rootState?.exits[0].operationsList, []);
        assert.deepEqual(ast?.rootState?.during_aspects.map(item => item.pyNodeType), [
            'DuringAspectOperations',
            'DuringAspectAbstractFunction',
            'DuringAspectRefFunction',
        ]);
    });

    // I-c from PR #115 review: ``state.composite`` was changed by PR-A
    // from "has braces" to "substates ∪ imports > 0". This means a
    // brace-only state that has actions but no substates and no imports
    // is now a leaf (``composite=false``). Pin that contract here so a
    // future regression in ``ast/builder.ts`` shows up immediately.
    it('classifies a brace-only state with actions but no substates/imports as a leaf', async () => {
        const document = createDocument([
            'def int x = 0;',
            'state Root {',
            '    state Idle {',
            '        enter { x = x + 1; }',
            '        exit { x = x - 1; }',
            '    }',
            '    [*] -> Idle;',
            '}',
        ].join('\n'), '/tmp/ast-brace-only-leaf.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        const idle = ast?.rootState?.substates.find(item => item.name === 'Idle');
        assert.ok(idle);
        assert.equal(idle?.composite, false);
        // ``Root`` is composite because it contains Idle as a substate.
        assert.equal(ast?.rootState?.composite, true);
    });

    // PR-A-coverage push: empty / whitespace-only multi-line comments
    // on abstract actions exercise ``formatMultilineComment`` empty-
    // and whitespace-only branches (builder.ts:176-177).
    it('normalizes empty and whitespace-only multi-line abstract-action docs', async () => {
        // Pure empty /* */ — special-cased early in formatMultilineComment.
        const docEmpty = createDocument(
            'state Root { state Idle { enter abstract X /* */; } [*] -> Idle; }',
            '/tmp/ast-empty-doc.fcstm',
        );
        const astEmpty = await packageModule.parseAstDocument(docEmpty);
        const actionEmpty = astEmpty?.rootState?.substates?.[0]?.enters?.[0];
        assert.equal(actionEmpty?.doc, '');
        // Multi-line whitespace-only — exercises the "nonEmptyLines
        // empty after trim" branch.
        const docWs = createDocument(
            'state Root {\n    state Idle {\n        enter abstract X /*\n   \n   \n*/;\n    }\n    [*] -> Idle;\n}',
            '/tmp/ast-ws-doc.fcstm',
        );
        const astWs = await packageModule.parseAstDocument(docWs);
        const actionWs = astWs?.rootState?.substates?.[0]?.enters?.[0];
        assert.equal(actionWs?.doc, '');
    });

    // PR-A-coverage push: exercise the string-escape branches in
    // ``decodeEscapedString`` (builder.ts:81-130). The grammar accepts
    // most C-style escapes inside named strings; the rare \b backspace
    // and \NNN octal branches need explicit DSL coverage.
    it('decodes \\b backspace and octal escapes inside named strings', async () => {
        // \b backspace (line 93-94 region)
        const docB = createDocument(
            'state Root named "alpha\\bgamma" { state A; [*] -> A; }',
            '/tmp/ast-escape-b.fcstm',
        );
        const astB = await packageModule.parseAstDocument(docB);
        assert.equal(astB?.rootState?.displayName, 'alpha\bgamma');
        // \NNN octal (decodeEscapedString octal branch)
        const docOct = createDocument(
            'state Root named "x\\101y" { state A; [*] -> A; }',
            '/tmp/ast-escape-octal.fcstm',
        );
        const astOct = await packageModule.parseAstDocument(docOct);
        // \101 = 0o101 = 'A'
        assert.equal(astOct?.rootState?.displayName, 'xAy');
    });

    // I-c sibling test: a state that owns nothing but an ``import``
    // (no explicit substates) MUST be classified as composite because
    // the import resolves into a substate during workspace assembly.
    // The grammar-level ``composite`` flag has to anticipate this.
    it('classifies an import-only state as composite', async () => {
        const document = createDocument([
            'state Root {',
            '    import "./worker.fcstm" as Worker;',
            '}',
        ].join('\n'), '/tmp/ast-import-only-composite.fcstm');

        const ast = await packageModule.parseAstDocument(document);
        assert.equal(ast?.rootState?.composite, true);
        assert.equal(ast?.rootState?.substates.length, 0);
        assert.equal(ast?.rootState?.imports.length, 1);
    });
});

describe('jsfcstm AST condition operator precedence', () => {
    for (const operators of condOperatorChains()) {
        it(`parses condition operator chain: ${operators.join(' ')}`, async () => {
            const guard = condChainText(operators);
            const document = createDocument([
                'state Root {',
                '    state A;',
                '    state B;',
                `    A -> B : if [${guard}];`,
                '}',
            ].join('\n'), `/tmp/ast-cond-${operators.join('-')}.fcstm`);

            const ast = await packageModule.parseAstDocument(document);
            const expression = ast?.rootState?.transitions[0].condition_expr;

            assert.ok(expression);
            assert.deepEqual(
                normalizeCondExpression(expression as unknown as Record<string, any>),
                expectedCondChain(operators),
            );
        });
    }
});

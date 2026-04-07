import assert from 'node:assert/strict';

import {createDocument, packageModule} from './support';

type PySnapshot = Record<string, unknown>;

function withDefined(target: PySnapshot, key: string, value: unknown): void {
    if (value !== undefined) {
        target[key] = value;
    }
}

function normalizeChainId(node: packageModule.FcstmAstChainPath): PySnapshot {
    return {
        __class__: 'ChainID',
        path: node.path,
        is_absolute: node.is_absolute,
    };
}

function normalizeExpression(expr: packageModule.FcstmAstExpression): PySnapshot {
    switch (expr.pyNodeType) {
        case 'Boolean':
        case 'Integer':
        case 'HexInt':
        case 'Float':
            return {
                __class__: expr.pyNodeType,
                raw: expr.raw,
            };
        case 'Constant':
            return {
                __class__: 'Constant',
                raw: expr.raw,
            };
        case 'Name':
            return {
                __class__: 'Name',
                name: expr.name,
            };
        case 'Paren':
            return {
                __class__: 'Paren',
                expr: normalizeExpression(expr.expr),
            };
        case 'UnaryOp':
            return {
                __class__: 'UnaryOp',
                op: expr.op,
                expr: normalizeExpression(expr.expr),
            };
        case 'BinaryOp':
            return {
                __class__: 'BinaryOp',
                expr1: normalizeExpression(expr.expr1),
                op: expr.op,
                expr2: normalizeExpression(expr.expr2),
            };
        case 'ConditionalOp':
            return {
                __class__: 'ConditionalOp',
                cond: normalizeExpression(expr.cond),
                value_true: normalizeExpression(expr.value_true),
                value_false: normalizeExpression(expr.value_false),
            };
        case 'UFunc':
            return {
                __class__: 'UFunc',
                func: expr.func,
                expr: normalizeExpression(expr.expr),
            };
        default:
            throw new Error(`Unsupported expression snapshot node: ${expr.pyNodeType}`);
    }
}

function normalizeOperationStatement(
    statement: packageModule.FcstmAstOperationStatement
): PySnapshot {
    if (statement.kind === 'assignmentStatement') {
        return {
            __class__: 'OperationAssignment',
            name: statement.name,
            expr: normalizeExpression(statement.expr),
        };
    }

    if (statement.kind === 'ifStatement') {
        return {
            __class__: 'OperationIf',
            branches: statement.branches.map(branch => ({
                __class__: 'OperationIfBranch',
                ...(branch.condition ? {condition: normalizeExpression(branch.condition)} : {}),
                statements: branch.statements.map(normalizeOperationStatement),
            })),
        };
    }

    throw new Error(`Unsupported operation snapshot node: ${statement.kind}`);
}

function normalizeAction(action: packageModule.FcstmAstAction): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: action.pyNodeType,
    };

    withDefined(snapshot, 'name', action.name);
    if (action.pyNodeType.startsWith('During')) {
        withDefined(snapshot, 'aspect', action.aspect);
    }
    if (action.mode === 'operations') {
        snapshot.operations = (action.operations || []).map(normalizeOperationStatement);
    }
    if (action.mode === 'abstract') {
        withDefined(snapshot, 'doc', action.doc);
    }
    if (action.mode === 'ref' && action.ref) {
        snapshot.ref = normalizeChainId(action.ref);
    }

    return snapshot;
}

function normalizeTransition(
    transition: packageModule.FcstmAstTransition | packageModule.FcstmAstForcedTransition
): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: transition.pyNodeType,
        from_state: transition.from_state,
        to_state: transition.to_state,
    };

    withDefined(snapshot, 'event_id', transition.event_id ? normalizeChainId(transition.event_id) : undefined);
    withDefined(
        snapshot,
        'condition_expr',
        transition.condition_expr ? normalizeExpression(transition.condition_expr) : undefined
    );
    if (transition.kind === 'transition') {
        snapshot.post_operations = transition.post_operations.map(normalizeOperationStatement);
    }

    return snapshot;
}

function normalizeImportMapping(
    mapping: packageModule.FcstmAstImportMapping
): PySnapshot {
    if (mapping.kind === 'importDefMapping') {
        return {
            __class__: 'ImportDefMapping',
            selector: normalizeImportDefSelector(mapping.selector),
            target_template: {
                __class__: 'ImportDefTargetTemplate',
                template: mapping.target_template.template,
            },
        };
    }

    const snapshot: PySnapshot = {
        __class__: 'ImportEventMapping',
        source_event: normalizeChainId(mapping.source_event),
        target_event: normalizeChainId(mapping.target_event),
    };
    withDefined(snapshot, 'extra_name', mapping.extra_name);
    return snapshot;
}

function normalizeImportDefSelector(
    selector: packageModule.FcstmAstImportDefSelector
): PySnapshot {
    switch (selector.kind) {
        case 'importDefExactSelector':
            return {
                __class__: 'ImportDefExactSelector',
                name: selector.name,
            };
        case 'importDefSetSelector':
            return {
                __class__: 'ImportDefSetSelector',
                names: selector.names,
            };
        case 'importDefPatternSelector':
            return {
                __class__: 'ImportDefPatternSelector',
                pattern: selector.pattern,
            };
        case 'importDefFallbackSelector':
            return {
                __class__: 'ImportDefFallbackSelector',
            };
        default:
            throw new Error(`Unsupported import selector snapshot node: ${selector.kind}`);
    }
}

function normalizeState(state: packageModule.FcstmAstStateDefinition): PySnapshot {
    const snapshot: PySnapshot = {
        __class__: 'StateDefinition',
        name: state.name,
        events: state.events.map(event => {
            const eventSnapshot: PySnapshot = {
                __class__: 'EventDefinition',
                name: event.name,
            };
            withDefined(eventSnapshot, 'extra_name', event.extra_name);
            return eventSnapshot;
        }),
        imports: state.imports.map(importStatement => {
            const importSnapshot: PySnapshot = {
                __class__: 'ImportStatement',
                source_path: importStatement.source_path,
                alias: importStatement.alias,
                mappings: importStatement.mappings.map(normalizeImportMapping),
            };
            withDefined(importSnapshot, 'extra_name', importStatement.extra_name);
            return importSnapshot;
        }),
        substates: state.substates.map(normalizeState),
        transitions: state.transitions.map(normalizeTransition),
        enters: state.enters.map(normalizeAction),
        durings: state.durings.map(normalizeAction),
        exits: state.exits.map(normalizeAction),
        during_aspects: state.during_aspects.map(normalizeAction),
        force_transitions: state.force_transitions.map(normalizeTransition),
        is_pseudo: state.is_pseudo,
    };
    withDefined(snapshot, 'extra_name', state.extra_name);
    return snapshot;
}

function normalizeProgram(program: packageModule.FcstmAstDocument): PySnapshot {
    return {
        __class__: 'StateMachineDSLProgram',
        definitions: program.definitions.map(definition => ({
            __class__: 'DefAssignment',
            name: definition.name,
            type: definition.type,
            expr: normalizeExpression(definition.expr),
        })),
        root_state: normalizeState(program.root_state!),
    };
}

describe('jsfcstm AST pyfcstm alignment', () => {
    const cases: Array<{
        name: string;
        text: string;
        expected: PySnapshot;
    }> = [
        {
            name: 'lifecycle, import, and forced transition structure',
            text: [
                'def int counter = 0;',
                'state Root named "System Root" {',
                '    event Start named "Start Event";',
                '    enter Init {',
                '        counter = counter + 1;',
                '    }',
                '    during before ref /Shared.Setup;',
                '    !* -> [*] : /Fault;',
                '    import "./worker.fcstm" as Worker named "Worker Module" {',
                '        def sensor_* -> io_$1;',
                '        event /Start -> /Bus.Start named "Bus Start";',
                '    }',
                '    pseudo state Junction;',
                '}',
            ].join('\n'),
            expected: {
                __class__: 'StateMachineDSLProgram',
                definitions: [
                    {
                        __class__: 'DefAssignment',
                        name: 'counter',
                        type: 'int',
                        expr: {__class__: 'Integer', raw: '0'},
                    },
                ],
                root_state: {
                    __class__: 'StateDefinition',
                    name: 'Root',
                    extra_name: 'System Root',
                    events: [
                        {__class__: 'EventDefinition', name: 'Start', extra_name: 'Start Event'},
                    ],
                    imports: [
                        {
                            __class__: 'ImportStatement',
                            source_path: './worker.fcstm',
                            alias: 'Worker',
                            extra_name: 'Worker Module',
                            mappings: [
                                {
                                    __class__: 'ImportDefMapping',
                                    selector: {__class__: 'ImportDefPatternSelector', pattern: 'sensor_*'},
                                    target_template: {__class__: 'ImportDefTargetTemplate', template: 'io_$1'},
                                },
                                {
                                    __class__: 'ImportEventMapping',
                                    source_event: {__class__: 'ChainID', path: ['Start'], is_absolute: true},
                                    target_event: {__class__: 'ChainID', path: ['Bus', 'Start'], is_absolute: true},
                                    extra_name: 'Bus Start',
                                },
                            ],
                        },
                    ],
                    substates: [
                        {
                            __class__: 'StateDefinition',
                            name: 'Junction',
                            events: [],
                            imports: [],
                            substates: [],
                            transitions: [],
                            enters: [],
                            durings: [],
                            exits: [],
                            during_aspects: [],
                            force_transitions: [],
                            is_pseudo: true,
                        },
                    ],
                    transitions: [],
                    enters: [
                        {
                            __class__: 'EnterOperations',
                            name: 'Init',
                            operations: [
                                {
                                    __class__: 'OperationAssignment',
                                    name: 'counter',
                                    expr: {
                                        __class__: 'BinaryOp',
                                        expr1: {__class__: 'Name', name: 'counter'},
                                        op: '+',
                                        expr2: {__class__: 'Integer', raw: '1'},
                                    },
                                },
                            ],
                        },
                    ],
                    durings: [
                        {
                            __class__: 'DuringRefFunction',
                            aspect: 'before',
                            ref: {__class__: 'ChainID', path: ['Shared', 'Setup'], is_absolute: true},
                        },
                    ],
                    exits: [],
                    during_aspects: [],
                    force_transitions: [
                        {
                            __class__: 'ForceTransitionDefinition',
                            from_state: 'ALL',
                            to_state: 'EXIT_STATE',
                            event_id: {__class__: 'ChainID', path: ['Fault'], is_absolute: true},
                        },
                    ],
                    is_pseudo: false,
                },
            },
        },
        {
            name: 'expressions and import selectors align with pyfcstm',
            text: [
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
            ].join('\n'),
            expected: {
                __class__: 'StateMachineDSLProgram',
                definitions: [
                    {
                        __class__: 'DefAssignment',
                        name: 'mask',
                        type: 'int',
                        expr: {__class__: 'HexInt', raw: '0xFF'},
                    },
                ],
                root_state: {
                    __class__: 'StateDefinition',
                    name: 'Root',
                    events: [],
                    imports: [
                        {
                            __class__: 'ImportStatement',
                            source_path: './worker.fcstm',
                            alias: 'Worker',
                            mappings: [
                                {
                                    __class__: 'ImportDefMapping',
                                    selector: {__class__: 'ImportDefSetSelector', names: ['left', 'right']},
                                    target_template: {__class__: 'ImportDefTargetTemplate', template: 'grouped'},
                                },
                                {
                                    __class__: 'ImportDefMapping',
                                    selector: {__class__: 'ImportDefExactSelector', name: 'exact'},
                                    target_template: {__class__: 'ImportDefTargetTemplate', template: 'renamed'},
                                },
                                {
                                    __class__: 'ImportDefMapping',
                                    selector: {__class__: 'ImportDefFallbackSelector'},
                                    target_template: {__class__: 'ImportDefTargetTemplate', template: 'kept'},
                                },
                            ],
                        },
                    ],
                    substates: [
                        {
                            __class__: 'StateDefinition',
                            name: 'A',
                            events: [],
                            imports: [],
                            substates: [],
                            transitions: [],
                            enters: [],
                            durings: [],
                            exits: [],
                            during_aspects: [],
                            force_transitions: [],
                            is_pseudo: false,
                        },
                    ],
                    transitions: [
                        {
                            __class__: 'TransitionDefinition',
                            from_state: 'A',
                            to_state: 'Root',
                            post_operations: [],
                        },
                    ],
                    enters: [
                        {
                            __class__: 'EnterOperations',
                            operations: [
                                {
                                    __class__: 'OperationAssignment',
                                    name: 'value',
                                    expr: {
                                        __class__: 'UFunc',
                                        func: 'abs',
                                        expr: {
                                            __class__: 'UnaryOp',
                                            op: '-',
                                            expr: {__class__: 'Name', name: 'mask'},
                                        },
                                    },
                                },
                                {
                                    __class__: 'OperationAssignment',
                                    name: 'choice',
                                    expr: {
                                        __class__: 'ConditionalOp',
                                        cond: {
                                            __class__: 'BinaryOp',
                                            expr1: {__class__: 'Name', name: 'mask'},
                                            op: '>',
                                            expr2: {__class__: 'Integer', raw: '0'},
                                        },
                                        value_true: {__class__: 'Integer', raw: '1'},
                                        value_false: {__class__: 'Integer', raw: '0'},
                                    },
                                },
                            ],
                        },
                    ],
                    durings: [
                        {
                            __class__: 'DuringOperations',
                            operations: [
                                {
                                    __class__: 'OperationAssignment',
                                    name: 'constant_value',
                                    expr: {
                                        __class__: 'Paren',
                                        expr: {__class__: 'Constant', raw: 'pi'},
                                    },
                                },
                            ],
                        },
                        {
                            __class__: 'DuringAbstractFunction',
                            name: 'Tick',
                        },
                        {
                            __class__: 'DuringRefFunction',
                            ref: {__class__: 'ChainID', path: ['Shared', 'Run'], is_absolute: false},
                        },
                    ],
                    exits: [],
                    during_aspects: [],
                    force_transitions: [],
                    is_pseudo: false,
                },
            },
        },
        {
            name: 'exit and during-aspect action families align with pyfcstm',
            text: [
                'state Root {',
                '    enter abstract EnterHook;',
                '    exit { ; }',
                '    exit abstract ExitHook;',
                '    exit ref /Shared.Cleanup;',
                '    >> during before { ; }',
                '    >> during after abstract AuditHook;',
                '    >> during before ref /Shared.BeforeHook;',
                '}',
            ].join('\n'),
            expected: {
                __class__: 'StateMachineDSLProgram',
                definitions: [],
                root_state: {
                    __class__: 'StateDefinition',
                    name: 'Root',
                    events: [],
                    imports: [],
                    substates: [],
                    transitions: [],
                    enters: [
                        {__class__: 'EnterAbstractFunction', name: 'EnterHook'},
                    ],
                    durings: [],
                    exits: [
                        {__class__: 'ExitOperations', operations: []},
                        {__class__: 'ExitAbstractFunction', name: 'ExitHook'},
                        {
                            __class__: 'ExitRefFunction',
                            ref: {__class__: 'ChainID', path: ['Shared', 'Cleanup'], is_absolute: true},
                        },
                    ],
                    during_aspects: [
                        {__class__: 'DuringAspectOperations', aspect: 'before', operations: []},
                        {__class__: 'DuringAspectAbstractFunction', name: 'AuditHook', aspect: 'after'},
                        {
                            __class__: 'DuringAspectRefFunction',
                            aspect: 'before',
                            ref: {__class__: 'ChainID', path: ['Shared', 'BeforeHook'], is_absolute: true},
                        },
                    ],
                    force_transitions: [],
                    is_pseudo: false,
                },
            },
        },
        {
            name: 'doc formatting and operator aliases align with pyfcstm',
            text: [
                'def int counter = 0;',
                'state Root {',
                '    enter abstract Setup /*',
                '        Prepare root',
                '          align indent',
                '    */',
                '    state A;',
                '    state B;',
                '    A -> B : if [counter > 0 and not false] effect {',
                '        counter = 0;',
                '        if [counter > 1 or false] {',
                '            counter = 2;',
                '        }',
                '    }',
                '    B -> A :: Resume;',
                '}',
            ].join('\n'),
            expected: {
                __class__: 'StateMachineDSLProgram',
                definitions: [
                    {
                        __class__: 'DefAssignment',
                        name: 'counter',
                        type: 'int',
                        expr: {__class__: 'Integer', raw: '0'},
                    },
                ],
                root_state: {
                    __class__: 'StateDefinition',
                    name: 'Root',
                    events: [],
                    imports: [],
                    substates: [
                        {
                            __class__: 'StateDefinition',
                            name: 'A',
                            events: [],
                            imports: [],
                            substates: [],
                            transitions: [],
                            enters: [],
                            durings: [],
                            exits: [],
                            during_aspects: [],
                            force_transitions: [],
                            is_pseudo: false,
                        },
                        {
                            __class__: 'StateDefinition',
                            name: 'B',
                            events: [],
                            imports: [],
                            substates: [],
                            transitions: [],
                            enters: [],
                            durings: [],
                            exits: [],
                            during_aspects: [],
                            force_transitions: [],
                            is_pseudo: false,
                        },
                    ],
                    transitions: [
                        {
                            __class__: 'TransitionDefinition',
                            from_state: 'A',
                            to_state: 'B',
                            condition_expr: {
                                __class__: 'BinaryOp',
                                expr1: {
                                    __class__: 'BinaryOp',
                                    expr1: {__class__: 'Name', name: 'counter'},
                                    op: '>',
                                    expr2: {__class__: 'Integer', raw: '0'},
                                },
                                op: '&&',
                                expr2: {
                                    __class__: 'UnaryOp',
                                    op: '!',
                                    expr: {__class__: 'Boolean', raw: 'false'},
                                },
                            },
                            post_operations: [
                                {
                                    __class__: 'OperationAssignment',
                                    name: 'counter',
                                    expr: {__class__: 'Integer', raw: '0'},
                                },
                                {
                                    __class__: 'OperationIf',
                                    branches: [
                                        {
                                            __class__: 'OperationIfBranch',
                                            condition: {
                                                __class__: 'BinaryOp',
                                                expr1: {
                                                    __class__: 'BinaryOp',
                                                    expr1: {__class__: 'Name', name: 'counter'},
                                                    op: '>',
                                                    expr2: {__class__: 'Integer', raw: '1'},
                                                },
                                                op: '||',
                                                expr2: {__class__: 'Boolean', raw: 'false'},
                                            },
                                            statements: [
                                                {
                                                    __class__: 'OperationAssignment',
                                                    name: 'counter',
                                                    expr: {__class__: 'Integer', raw: '2'},
                                                },
                                            ],
                                        },
                                    ],
                                },
                            ],
                        },
                        {
                            __class__: 'TransitionDefinition',
                            from_state: 'B',
                            to_state: 'A',
                            event_id: {__class__: 'ChainID', path: ['B', 'Resume'], is_absolute: false},
                            post_operations: [],
                        },
                    ],
                    enters: [
                        {
                            __class__: 'EnterAbstractFunction',
                            name: 'Setup',
                            doc: 'Prepare root\n  align indent',
                        },
                    ],
                    durings: [],
                    exits: [],
                    during_aspects: [],
                    force_transitions: [],
                    is_pseudo: false,
                },
            },
        },
    ];

    for (const testCase of cases) {
        it(`matches pyfcstm for ${testCase.name}`, async () => {
            const document = createDocument(testCase.text, `/tmp/${testCase.name.replace(/\s+/g, '-')}.fcstm`);
            const ast = await packageModule.parseAstDocument(document);
            assert.ok(ast);
            assert.deepEqual(normalizeProgram(ast!), testCase.expected);
        });
    }
});

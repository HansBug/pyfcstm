import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: program structure', [
    {
        name: 'lifecycle import and forced transition structure',
        text: py.lines(
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
            '}'
        ),
        expected: py.program(py.rootState({
            extra_name: 'System Root',
            events: [
                py.eventDefinition('Start', 'Start Event'),
            ],
            imports: [
                py.importStatement('./worker.fcstm', 'Worker', [
                    py.importDefMapping(
                        py.importDefPatternSelector('sensor_*'),
                        'io_$1'
                    ),
                    py.importEventMapping(
                        py.chain(['Start'], true),
                        py.chain(['Bus', 'Start'], true),
                        'Bus Start'
                    ),
                ], 'Worker Module'),
            ],
            substates: [
                py.state('Junction', {is_pseudo: true}),
            ],
            enters: [
                py.enterOperations([
                    py.assign(
                        'counter',
                        py.binary(py.nameExpr('counter'), '+', py.intLiteral('1'))
                    ),
                ], 'Init'),
            ],
            durings: [
                py.duringRef(py.chain(['Shared', 'Setup'], true), {aspect: 'before'}),
            ],
            force_transitions: [
                py.forceTransition(py.ALL, py.EXIT_STATE, {
                    event_id: py.chain(['Fault'], true),
                }),
            ],
        }), [
            py.defAssignment('counter', 'int', py.intLiteral('0')),
        ]),
    },
    {
        name: 'expressions and import selectors align with pyfcstm',
        text: py.lines(
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
            '}'
        ),
        expected: py.program(py.rootState({
            imports: [
                py.importStatement('./worker.fcstm', 'Worker', [
                    py.importDefMapping(
                        py.importDefSetSelector(['left', 'right']),
                        'grouped'
                    ),
                    py.importDefMapping(
                        py.importDefExactSelector('exact'),
                        'renamed'
                    ),
                    py.importDefMapping(
                        py.importDefFallbackSelector(),
                        'kept'
                    ),
                ]),
            ],
            substates: [
                py.state('A'),
            ],
            transitions: [
                py.transition('A', 'Root'),
            ],
            enters: [
                py.enterOperations([
                    py.assign(
                        'value',
                        py.ufunc('abs', py.unary('-', py.nameExpr('mask')))
                    ),
                    py.assign(
                        'choice',
                        py.conditional(
                            py.binary(py.nameExpr('mask'), '>', py.intLiteral('0')),
                            py.intLiteral('1'),
                            py.intLiteral('0')
                        )
                    ),
                ]),
            ],
            durings: [
                py.duringOperations([
                    py.assign(
                        'constant_value',
                        py.paren(py.constant('pi'))
                    ),
                ]),
                py.duringAbstract({name: 'Tick'}),
                py.duringRef(py.chain(['Shared', 'Run'])),
            ],
        }), [
            py.defAssignment('mask', 'int', py.hexInt('0xFF')),
        ]),
    },
    {
        name: 'doc formatting and operator aliases align with pyfcstm',
        text: py.lines(
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
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('A'),
                py.state('B'),
            ],
            transitions: [
                py.transition('A', 'B', {
                    condition_expr: py.binary(
                        py.binary(py.nameExpr('counter'), '>', py.intLiteral('0')),
                        '&&',
                        py.unary('!', py.boolLiteral('false'))
                    ),
                    post_operations: [
                        py.assign('counter', py.intLiteral('0')),
                        py.ifStatement([
                            py.ifBranch(
                                py.binary(
                                    py.binary(py.nameExpr('counter'), '>', py.intLiteral('1')),
                                    '||',
                                    py.boolLiteral('false')
                                ),
                                [
                                    py.assign('counter', py.intLiteral('2')),
                                ]
                            ),
                        ]),
                    ],
                }),
                py.transition('B', 'A', {
                    event_id: py.chain(['B', 'Resume']),
                }),
            ],
            enters: [
                py.enterAbstract('Setup', 'Prepare root\n  align indent'),
            ],
        }), [
            py.defAssignment('counter', 'int', py.intLiteral('0')),
        ]),
    },
    {
        name: 'nested composite state structure aligns with pyfcstm',
        text: py.lines(
            'state Root {',
            '    state Active {',
            '        enter {',
            '            counter = 0;',
            '        }',
            '        state Processing;',
            '        state Waiting;',
            '        [*] -> Processing;',
            '        Processing -> Waiting :: Done;',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('Active', {
                    substates: [
                        py.state('Processing'),
                        py.state('Waiting'),
                    ],
                    transitions: [
                        py.transition(py.INIT_STATE, 'Processing'),
                        py.transition('Processing', 'Waiting', {
                            event_id: py.chain(['Processing', 'Done']),
                        }),
                    ],
                    enters: [
                        py.enterOperations([
                            py.assign('counter', py.intLiteral('0')),
                        ]),
                    ],
                }),
            ],
        })),
    },
    {
        name: 'stage ordering shaped nested actions align with pyfcstm',
        text: py.lines(
            'state Root {',
            '    >> during before abstract Monitor;',
            '    state Running {',
            '        during before {',
            '            counter = counter + 1;',
            '        }',
            '        during after ref /Shared.Cleanup;',
            '        state Active;',
            '        [*] -> Active;',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('Running', {
                    substates: [
                        py.state('Active'),
                    ],
                    transitions: [
                        py.transition(py.INIT_STATE, 'Active'),
                    ],
                    durings: [
                        py.duringOperations([
                            py.assign(
                                'counter',
                                py.binary(py.nameExpr('counter'), '+', py.intLiteral('1'))
                            ),
                        ], {aspect: 'before'}),
                        py.duringRef(py.chain(['Shared', 'Cleanup'], true), {aspect: 'after'}),
                    ],
                }),
            ],
            during_aspects: [
                py.duringAspectAbstract({
                    aspect: 'before',
                    name: 'Monitor',
                }),
            ],
        })),
    },
]);

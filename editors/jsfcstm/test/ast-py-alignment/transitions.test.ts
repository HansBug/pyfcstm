import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: transitions', [
    {
        name: 'entry transition families',
        text: py.lines(
            'state Root {',
            '    state StateA;',
            '    state StateB;',
            '    [*] -> StateA;',
            '    [*] -> StateB : chain1;',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('StateA'),
                py.state('StateB'),
            ],
            transitions: [
                py.transition(py.INIT_STATE, 'StateA'),
                py.transition(py.INIT_STATE, 'StateB', {
                    event_id: py.chain(['chain1']),
                }),
            ],
        })),
    },
    {
        name: 'guarded and effectful entry transitions',
        text: py.lines(
            'state Root {',
            '    state StateC;',
            '    state StateD;',
            '    [*] -> StateC : if [x > 10];',
            '    [*] -> StateD effect {',
            '        a = 5;',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('StateC'),
                py.state('StateD'),
            ],
            transitions: [
                py.transition(py.INIT_STATE, 'StateC', {
                    condition_expr: py.binary(py.nameExpr('x'), '>', py.intLiteral('10')),
                }),
                py.transition(py.INIT_STATE, 'StateD', {
                    post_operations: [
                        py.assign('a', py.intLiteral('5')),
                    ],
                }),
            ],
        })),
    },
    {
        name: 'normal transition event scopes',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> B :: Resume;',
            '    A -> B : chain.id;',
            '    A -> B : /System.Resume;',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('A'),
                py.state('B'),
            ],
            transitions: [
                py.transition('A', 'B', {
                    event_id: py.chain(['A', 'Resume']),
                }),
                py.transition('A', 'B', {
                    event_id: py.chain(['chain', 'id']),
                }),
                py.transition('A', 'B', {
                    event_id: py.chain(['System', 'Resume'], true),
                }),
            ],
        })),
    },
    {
        name: 'normal transition conditions and effects',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> B : if [x != y && z == 10];',
            '    A -> B effect {',
            '        a = cos(b);',
            '        d = 30;',
            '    }',
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
                        py.binary(py.nameExpr('x'), '!=', py.nameExpr('y')),
                        '&&',
                        py.binary(py.nameExpr('z'), '==', py.intLiteral('10'))
                    ),
                }),
                py.transition('A', 'B', {
                    post_operations: [
                        py.assign('a', py.ufunc('cos', py.nameExpr('b'))),
                        py.assign('d', py.intLiteral('30')),
                    ],
                }),
            ],
        })),
    },
    {
        name: 'exit transition families',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> [*];',
            '    B -> [*] : chain7;',
            '    A -> [*] : if [x >= 100];',
            '    B -> [*] effect {',
            '        a = 50;',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('A'),
                py.state('B'),
            ],
            transitions: [
                py.transition('A', py.EXIT_STATE),
                py.transition('B', py.EXIT_STATE, {
                    event_id: py.chain(['chain7']),
                }),
                py.transition('A', py.EXIT_STATE, {
                    condition_expr: py.binary(py.nameExpr('x'), '>=', py.intLiteral('100')),
                }),
                py.transition('B', py.EXIT_STATE, {
                    post_operations: [
                        py.assign('a', py.intLiteral('50')),
                    ],
                }),
            ],
        })),
    },
    {
        name: 'guard and effect combination keeps pyfcstm operator normalization',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> B : if [counter > 0 and not false] effect {',
            '        counter = 0;',
            '        if [counter > 1 or false] {',
            '            counter = 2;',
            '        }',
            '    }',
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
            ],
        })),
    },
]);

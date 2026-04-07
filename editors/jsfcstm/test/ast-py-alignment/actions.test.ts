import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: actions and operation blocks', [
    {
        name: 'enter action families',
        text: py.lines(
            'state Root {',
            '    enter {',
            '        x = 10;',
            '        y = 20;',
            '    }',
            '    enter initFunc {',
            '        x = 10;',
            '    }',
            '    enter abstract setupFunc /* Initialize state variables */',
            '    enter ref /absolute.chain.id;',
            '}'
        ),
        expected: py.program(py.rootState({
            enters: [
                py.enterOperations([
                    py.assign('x', py.intLiteral('10')),
                    py.assign('y', py.intLiteral('20')),
                ]),
                py.enterOperations([
                    py.assign('x', py.intLiteral('10')),
                ], 'initFunc'),
                py.enterAbstract('setupFunc', 'Initialize state variables'),
                py.enterRef(py.chain(['absolute', 'chain', 'id'], true)),
            ],
        })),
    },
    {
        name: 'during action families',
        text: py.lines(
            'state Root {',
            '    during {',
            '        x = 10;',
            '    }',
            '    during before funcName {',
            '        x = 10;',
            '        y = 20;',
            '    }',
            '    during after abstract funcName /* after aspect documentation */',
            '    during funcName ref chain.id;',
            '    during before ref /absolute.chain.id;',
            '}'
        ),
        expected: py.program(py.rootState({
            durings: [
                py.duringOperations([
                    py.assign('x', py.intLiteral('10')),
                ]),
                py.duringOperations([
                    py.assign('x', py.intLiteral('10')),
                    py.assign('y', py.intLiteral('20')),
                ], {aspect: 'before', name: 'funcName'}),
                py.duringAbstract({
                    aspect: 'after',
                    name: 'funcName',
                    doc: 'after aspect documentation',
                }),
                py.duringRef(py.chain(['chain', 'id']), {name: 'funcName'}),
                py.duringRef(py.chain(['absolute', 'chain', 'id'], true), {aspect: 'before'}),
            ],
        })),
    },
    {
        name: 'exit action families',
        text: py.lines(
            'state Root {',
            '    exit {',
            '        x = 10;',
            '        y = 20;',
            '    }',
            '    exit setupState {',
            '        x = 10;',
            '        y = x + 5;',
            '    }',
            '    exit abstract /* Setup initial conditions */',
            '    exit onExit ref utils.init;',
            '}'
        ),
        expected: py.program(py.rootState({
            exits: [
                py.exitOperations([
                    py.assign('x', py.intLiteral('10')),
                    py.assign('y', py.intLiteral('20')),
                ]),
                py.exitOperations([
                    py.assign('x', py.intLiteral('10')),
                    py.assign(
                        'y',
                        py.binary(py.nameExpr('x'), '+', py.intLiteral('5'))
                    ),
                ], 'setupState'),
                py.exitAbstract(undefined, 'Setup initial conditions'),
                py.exitRef(py.chain(['utils', 'init']), 'onExit'),
            ],
        })),
    },
    {
        name: 'during aspect families',
        text: py.lines(
            'state Root {',
            '    >> during before {',
            '        ;',
            '        x = 10;',
            '        ;',
            '    }',
            '    >> during after funcName {',
            '        x = 10;',
            '        y = 20;',
            '    }',
            '    >> during before abstract /* this is documentation */',
            '    >> during after ref /root.complex.nested.chain;',
            '}'
        ),
        expected: py.program(py.rootState({
            during_aspects: [
                py.duringAspectOperations([
                    py.assign('x', py.intLiteral('10')),
                ], {aspect: 'before'}),
                py.duringAspectOperations([
                    py.assign('x', py.intLiteral('10')),
                    py.assign('y', py.intLiteral('20')),
                ], {aspect: 'after', name: 'funcName'}),
                py.duringAspectAbstract({
                    aspect: 'before',
                    doc: 'this is documentation',
                }),
                py.duringAspectRef(
                    py.chain(['root', 'complex', 'nested', 'chain'], true),
                    {aspect: 'after'}
                ),
            ],
        })),
    },
    {
        name: 'empty abstract documentation normalizes like pyfcstm',
        text: py.lines(
            'state Root {',
            '    enter abstract /* */',
            '    during after abstract /*',
            '    */',
            '    exit abstract /*    */',
            '    >> during before abstract /* */',
            '}'
        ),
        expected: py.program(py.rootState({
            enters: [
                py.enterAbstract(undefined, ''),
            ],
            durings: [
                py.duringAbstract({aspect: 'after', doc: ''}),
            ],
            exits: [
                py.exitAbstract(undefined, ''),
            ],
            during_aspects: [
                py.duringAspectAbstract({aspect: 'before', doc: ''}),
            ],
        })),
    },
    {
        name: 'if else if else blocks inside enter operations',
        text: py.lines(
            'state Root {',
            '    enter {',
            '        if [x > 0] {',
            '            y = 1;',
            '        } else if [x == 0] {',
            '            y = 0;',
            '        } else {',
            '            y = -1;',
            '        }',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            enters: [
                py.enterOperations([
                    py.ifStatement([
                        py.ifBranch(
                            py.binary(py.nameExpr('x'), '>', py.intLiteral('0')),
                            [
                                py.assign('y', py.intLiteral('1')),
                            ]
                        ),
                        py.ifBranch(
                            py.binary(py.nameExpr('x'), '==', py.intLiteral('0')),
                            [
                                py.assign('y', py.intLiteral('0')),
                            ]
                        ),
                        py.ifBranch(undefined, [
                            py.assign('y', py.unary('-', py.intLiteral('1'))),
                        ]),
                    ]),
                ]),
            ],
        })),
    },
    {
        name: 'nested if blocks and trailing statements inside during operations',
        text: py.lines(
            'state Root {',
            '    during {',
            '        if [mode == 0] {',
            '            if [temp > 80] {',
            '                level = 3;',
            '            } else {',
            '                level = 1;',
            '            }',
            '        } else {',
            '            level = 0;',
            '        }',
            '        z = y + 1;',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            durings: [
                py.duringOperations([
                    py.ifStatement([
                        py.ifBranch(
                            py.binary(py.nameExpr('mode'), '==', py.intLiteral('0')),
                            [
                                py.ifStatement([
                                    py.ifBranch(
                                        py.binary(py.nameExpr('temp'), '>', py.intLiteral('80')),
                                        [
                                            py.assign('level', py.intLiteral('3')),
                                        ]
                                    ),
                                    py.ifBranch(undefined, [
                                        py.assign('level', py.intLiteral('1')),
                                    ]),
                                ]),
                            ]
                        ),
                        py.ifBranch(undefined, [
                            py.assign('level', py.intLiteral('0')),
                        ]),
                    ]),
                    py.assign(
                        'z',
                        py.binary(py.nameExpr('y'), '+', py.intLiteral('1'))
                    ),
                ]),
            ],
        })),
    },
]);

import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: conditions and operations', [
    {
        name: 'boolean literal and unary guard conditions',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> B : if [true];',
            '    A -> B : if [not false];',
            '    A -> B : if [!(1 < 2)];',
            '}'
        ),
        expected: py.program(py.rootState({
            substates: [
                py.state('A'),
                py.state('B'),
            ],
            transitions: [
                py.transition('A', 'B', {
                    condition_expr: py.boolLiteral('true'),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.unary('!', py.boolLiteral('false')),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.unary(
                        '!',
                        py.paren(py.binary(py.intLiteral('1'), '<', py.intLiteral('2')))
                    ),
                }),
            ],
        })),
    },
    {
        name: 'logical precedence guard conditions',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> B : if [true && false || true];',
            '    A -> B : if [false || true && true];',
            '    A -> B : if [(true || false) && false];',
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
                        py.binary(py.boolLiteral('true'), '&&', py.boolLiteral('false')),
                        '||',
                        py.boolLiteral('true')
                    ),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.binary(
                        py.boolLiteral('false'),
                        '||',
                        py.binary(py.boolLiteral('true'), '&&', py.boolLiteral('true'))
                    ),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.binary(
                        py.paren(py.binary(py.boolLiteral('true'), '||', py.boolLiteral('false'))),
                        '&&',
                        py.boolLiteral('false')
                    ),
                }),
            ],
        })),
    },
    {
        name: 'arithmetic comparison guard conditions',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> B : if [1 + 2 * 3 < 10];',
            '    A -> B : if [(1 + 2) * 3 > 5];',
            '    A -> B : if [10 - 5 / 2.5 == 8];',
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
                        py.binary(
                            py.intLiteral('1'),
                            '+',
                            py.binary(py.intLiteral('2'), '*', py.intLiteral('3'))
                        ),
                        '<',
                        py.intLiteral('10')
                    ),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.binary(
                        py.binary(
                            py.paren(py.binary(py.intLiteral('1'), '+', py.intLiteral('2'))),
                            '*',
                            py.intLiteral('3')
                        ),
                        '>',
                        py.intLiteral('5')
                    ),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.binary(
                        py.binary(
                            py.intLiteral('10'),
                            '-',
                            py.binary(py.intLiteral('5'), '/', py.floatLiteral('2.5'))
                        ),
                        '==',
                        py.intLiteral('8')
                    ),
                }),
            ],
        })),
    },
    {
        name: 'bitwise and constant guard conditions',
        text: py.lines(
            'state Root {',
            '    state A;',
            '    state B;',
            '    A -> B : if [1 << 2 == 4];',
            '    A -> B : if [5 & 3 == 1];',
            '    A -> B : if [pi > 3];',
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
                        py.binary(py.intLiteral('1'), '<<', py.intLiteral('2')),
                        '==',
                        py.intLiteral('4')
                    ),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.binary(
                        py.binary(py.intLiteral('5'), '&', py.intLiteral('3')),
                        '==',
                        py.intLiteral('1')
                    ),
                }),
                py.transition('A', 'B', {
                    condition_expr: py.binary(
                        py.constant('pi'),
                        '>',
                        py.intLiteral('3')
                    ),
                }),
            ],
        })),
    },
    {
        name: 'operation expression families in enter blocks',
        text: py.lines(
            'state Root {',
            '    enter {',
            '        sine = sin(pi / 2);',
            '        logarithm = log(100);',
            '        absolute = abs(-5);',
            '        rounded = round(3.7);',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            enters: [
                py.enterOperations([
                    py.assign('sine', py.ufunc('sin', py.binary(py.constant('pi'), '/', py.intLiteral('2')))),
                    py.assign('logarithm', py.ufunc('log', py.intLiteral('100'))),
                    py.assign('absolute', py.ufunc('abs', py.unary('-', py.intLiteral('5')))),
                    py.assign('rounded', py.ufunc('round', py.floatLiteral('3.7'))),
                ]),
            ],
        })),
    },
    {
        name: 'operation precedence families in during blocks',
        text: py.lines(
            'state Root {',
            '    during {',
            '        result = 2 + 3 * 4;',
            '        grouped = (2 + 3) * 4;',
            '        complex = 2 * 3 + 4 * 5;',
            '        mixed = 2 ** 3 * 4 + 5 / 2 - 1;',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            durings: [
                py.duringOperations([
                    py.assign(
                        'result',
                        py.binary(py.intLiteral('2'), '+', py.binary(py.intLiteral('3'), '*', py.intLiteral('4')))
                    ),
                    py.assign(
                        'grouped',
                        py.binary(py.paren(py.binary(py.intLiteral('2'), '+', py.intLiteral('3'))), '*', py.intLiteral('4'))
                    ),
                    py.assign(
                        'complex',
                        py.binary(
                            py.binary(py.intLiteral('2'), '*', py.intLiteral('3')),
                            '+',
                            py.binary(py.intLiteral('4'), '*', py.intLiteral('5'))
                        )
                    ),
                    py.assign(
                        'mixed',
                        py.binary(
                            py.binary(
                                py.binary(
                                    py.binary(py.intLiteral('2'), '**', py.intLiteral('3')),
                                    '*',
                                    py.intLiteral('4')
                                ),
                                '+',
                                py.binary(py.intLiteral('5'), '/', py.intLiteral('2'))
                            ),
                            '-',
                            py.intLiteral('1')
                        )
                    ),
                ]),
            ],
        })),
    },
    {
        name: 'bitwise nested and composed function operations',
        text: py.lines(
            'state Root {',
            '    exit {',
            '        bitwise_mix = (5 & 3) | (2 << 1);',
            '        nested = ((2 + 3) * (4 - 1)) / 2;',
            '        func_nest = sin(cos(pi));',
            '        complex_func = log(abs(sin(pi) + 5));',
            '    }',
            '}'
        ),
        expected: py.program(py.rootState({
            exits: [
                py.exitOperations([
                    py.assign(
                        'bitwise_mix',
                        py.binary(
                            py.paren(py.binary(py.intLiteral('5'), '&', py.intLiteral('3'))),
                            '|',
                            py.paren(py.binary(py.intLiteral('2'), '<<', py.intLiteral('1')))
                        )
                    ),
                    py.assign(
                        'nested',
                        py.binary(
                            py.paren(
                                py.binary(
                                    py.paren(py.binary(py.intLiteral('2'), '+', py.intLiteral('3'))),
                                    '*',
                                    py.paren(py.binary(py.intLiteral('4'), '-', py.intLiteral('1')))
                                )
                            ),
                            '/',
                            py.intLiteral('2')
                        )
                    ),
                    py.assign(
                        'func_nest',
                        py.ufunc('sin', py.ufunc('cos', py.constant('pi')))
                    ),
                    py.assign(
                        'complex_func',
                        py.ufunc(
                            'log',
                            py.ufunc(
                                'abs',
                                py.binary(py.ufunc('sin', py.constant('pi')), '+', py.intLiteral('5'))
                            )
                        )
                    ),
                ]),
            ],
        })),
    },
]);

import * as py from './support';

py.runPyAlignmentCases('jsfcstm AST pyfcstm alignment: definitions and expressions', [
    {
        name: 'scalar and signed literal definitions',
        text: py.lines(
            'def int x = 5;',
            'def int negative = -10;',
            'def int positive = +15;',
            'def float y = 3.14;',
            'def float tiny = 1.5e-4;',
            'state Root;'
        ),
        expected: py.program(py.rootState(), [
            py.defAssignment('x', 'int', py.intLiteral('5')),
            py.defAssignment('negative', 'int', py.unary('-', py.intLiteral('10'))),
            py.defAssignment('positive', 'int', py.unary('+', py.intLiteral('15'))),
            py.defAssignment('y', 'float', py.floatLiteral('3.14')),
            py.defAssignment('tiny', 'float', py.floatLiteral('1.5e-4')),
        ]),
    },
    {
        name: 'hex and named constant definitions',
        text: py.lines(
            'def int hex_value = 0x1A;',
            'def int hex_large = 0xFFFF;',
            'def float pi_const = pi;',
            'def float e_const = E;',
            'def float tau_const = tau;',
            'state Root;'
        ),
        expected: py.program(py.rootState(), [
            py.defAssignment('hex_value', 'int', py.hexInt('0x1A')),
            py.defAssignment('hex_large', 'int', py.hexInt('0xFFFF')),
            py.defAssignment('pi_const', 'float', py.constant('pi')),
            py.defAssignment('e_const', 'float', py.constant('E')),
            py.defAssignment('tau_const', 'float', py.constant('tau')),
        ]),
    },
    {
        name: 'grouped arithmetic and parenthesized unary definitions',
        text: py.lines(
            'def int grouped = (10 + 5);',
            'def float complex_group = ((3.0 + 2.0) * 4.0);',
            'def int negative_expr = -(5);',
            'state Root;'
        ),
        expected: py.program(py.rootState(), [
            py.defAssignment(
                'grouped',
                'int',
                py.paren(py.binary(py.intLiteral('10'), '+', py.intLiteral('5')))
            ),
            py.defAssignment(
                'complex_group',
                'float',
                py.paren(
                    py.binary(
                        py.paren(py.binary(py.floatLiteral('3.0'), '+', py.floatLiteral('2.0'))),
                        '*',
                        py.floatLiteral('4.0')
                    )
                )
            ),
            py.defAssignment(
                'negative_expr',
                'int',
                py.unary('-', py.paren(py.intLiteral('5')))
            ),
        ]),
    },
    {
        name: 'bitwise operator definitions',
        text: py.lines(
            'def int bit_shift_left = 1 << 3;',
            'def int bit_shift_right = 16 >> 2;',
            'def int bit_and = 5 & 3;',
            'def int bit_or = 5 | 3;',
            'def int bit_xor = 5 ^ 3;',
            'state Root;'
        ),
        expected: py.program(py.rootState(), [
            py.defAssignment('bit_shift_left', 'int', py.binary(py.intLiteral('1'), '<<', py.intLiteral('3'))),
            py.defAssignment('bit_shift_right', 'int', py.binary(py.intLiteral('16'), '>>', py.intLiteral('2'))),
            py.defAssignment('bit_and', 'int', py.binary(py.intLiteral('5'), '&', py.intLiteral('3'))),
            py.defAssignment('bit_or', 'int', py.binary(py.intLiteral('5'), '|', py.intLiteral('3'))),
            py.defAssignment('bit_xor', 'int', py.binary(py.intLiteral('5'), '^', py.intLiteral('3'))),
        ]),
    },
    {
        name: 'power remainder and arithmetic precedence definitions',
        text: py.lines(
            'def float power = 2.0 ** 3.0;',
            'def int remainder = 10 % 3;',
            'def float complex = 2.0 * 3.0 + 4.0;',
            'state Root;'
        ),
        expected: py.program(py.rootState(), [
            py.defAssignment('power', 'float', py.binary(py.floatLiteral('2.0'), '**', py.floatLiteral('3.0'))),
            py.defAssignment('remainder', 'int', py.binary(py.intLiteral('10'), '%', py.intLiteral('3'))),
            py.defAssignment(
                'complex',
                'float',
                py.binary(
                    py.binary(py.floatLiteral('2.0'), '*', py.floatLiteral('3.0')),
                    '+',
                    py.floatLiteral('4.0')
                )
            ),
        ]),
    },
]);

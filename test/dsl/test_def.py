import pytest

from pyfcstm.dsl import GrammarParseError, parse_with_grammar_entry
from pyfcstm.dsl.node import *


@pytest.mark.unittest
class TestDSLCondition:
    @pytest.mark.parametrize(['input_text', 'expected'], [
        ('def int x = 5;', DefAssignment(name='x', type='int', expr=Integer(raw='5'))),
        # Simple integer definition with literal value
        ('def int counter = 0;', DefAssignment(name='counter', type='int', expr=Integer(raw='0'))),
        # Integer definition initialized to zero
        ('def int negative = -10;',
         DefAssignment(name='negative', type='int', expr=UnaryOp(op='-', expr=Integer(raw='10')))),
        # Integer definition with negative value
        ('def float y = 3.14;', DefAssignment(name='y', type='float', expr=Float(raw='3.14'))),
        # Simple float definition with decimal value
        ('def float pi_value = 3.14159;', DefAssignment(name='pi_value', type='float', expr=Float(raw='3.14159'))),
        # Float definition with more precision
        ('def float negative_float = -2.5;',
         DefAssignment(name='negative_float', type='float', expr=UnaryOp(op='-', expr=Float(raw='2.5')))),
        # Float definition with negative value
        ('def float scientific = 1.5e3;', DefAssignment(name='scientific', type='float', expr=Float(raw='1.5e3'))),
        # Float definition using scientific notation
        ('def float tiny = 1.5e-4;', DefAssignment(name='tiny', type='float', expr=Float(raw='1.5e-4'))),
        # Float definition using negative exponent
        ('def int hex_value = 0x1A;', DefAssignment(name='hex_value', type='int', expr=HexInt(raw='0x1A'))),
        # Integer definition using hexadecimal notation
        ('def int hex_large = 0xFFFF;', DefAssignment(name='hex_large', type='int', expr=HexInt(raw='0xFFFF'))),
        # Integer definition with larger hex value
        ('def float pi_const = pi;', DefAssignment(name='pi_const', type='float', expr=Constant(raw='pi'))),
        # Float definition using pi constant
        ('def float e_const = E;', DefAssignment(name='e_const', type='float', expr=Constant(raw='E'))),
        # Float definition using E constant
        ('def float tau_const = tau;', DefAssignment(name='tau_const', type='float', expr=Constant(raw='tau'))),
        # Float definition using tau constant
        ('def int grouped = (10 + 5);', DefAssignment(name='grouped', type='int', expr=Paren(
            expr=BinaryOp(expr1=Integer(raw='10'), op='+', expr2=Integer(raw='5'))))),
        # Integer definition with parenthesized expression
        ('def float complex_group = ((3.0 + 2.0) * 4.0);', DefAssignment(name='complex_group', type='float', expr=Paren(
            expr=BinaryOp(expr1=Paren(expr=BinaryOp(expr1=Float(raw='3.0'), op='+', expr2=Float(raw='2.0'))), op='*',
                          expr2=Float(raw='4.0'))))),  # Float definition with nested parentheses
        ('def int positive = +15;',
         DefAssignment(name='positive', type='int', expr=UnaryOp(op='+', expr=Integer(raw='15')))),
        # Integer definition with explicit positive sign
        ('def int negative_expr = -(5);',
         DefAssignment(name='negative_expr', type='int', expr=UnaryOp(op='-', expr=Paren(expr=Integer(raw='5'))))),
        # Integer definition with parenthesized negative expression
        ('def int sum = 5 + 3;',
         DefAssignment(name='sum', type='int', expr=BinaryOp(expr1=Integer(raw='5'), op='+', expr2=Integer(raw='3')))),
        # Integer definition with addition
        ('def int difference = 10 - 4;', DefAssignment(name='difference', type='int',
                                                       expr=BinaryOp(expr1=Integer(raw='10'), op='-',
                                                                     expr2=Integer(raw='4')))),
        # Integer definition with subtraction
        ('def float product = 2.5 * 3.0;', DefAssignment(name='product', type='float',
                                                         expr=BinaryOp(expr1=Float(raw='2.5'), op='*',
                                                                       expr2=Float(raw='3.0')))),
        # Float definition with multiplication
        ('def float quotient = 10.0 / 2.0;', DefAssignment(name='quotient', type='float',
                                                           expr=BinaryOp(expr1=Float(raw='10.0'), op='/',
                                                                         expr2=Float(raw='2.0')))),
        # Float definition with division
        ('def int remainder = 10 % 3;', DefAssignment(name='remainder', type='int',
                                                      expr=BinaryOp(expr1=Integer(raw='10'), op='%',
                                                                    expr2=Integer(raw='3')))),
        # Integer definition with modulo operation
        ('def float power = 2.0 ** 3.0;', DefAssignment(name='power', type='float',
                                                        expr=BinaryOp(expr1=Float(raw='2.0'), op='**',
                                                                      expr2=Float(raw='3.0')))),
        # Float definition with power operation
        ('def int bit_shift_left = 1 << 3;', DefAssignment(name='bit_shift_left', type='int',
                                                           expr=BinaryOp(expr1=Integer(raw='1'), op='<<',
                                                                         expr2=Integer(raw='3')))),
        # Integer definition with left shift
        ('def int bit_shift_right = 16 >> 2;', DefAssignment(name='bit_shift_right', type='int',
                                                             expr=BinaryOp(expr1=Integer(raw='16'), op='>>',
                                                                           expr2=Integer(raw='2')))),
        # Integer definition with right shift
        ('def int bit_and = 5 & 3;', DefAssignment(name='bit_and', type='int',
                                                   expr=BinaryOp(expr1=Integer(raw='5'), op='&',
                                                                 expr2=Integer(raw='3')))),
        # Integer definition with bitwise AND
        ('def int bit_or = 5 | 3;', DefAssignment(name='bit_or', type='int',
                                                  expr=BinaryOp(expr1=Integer(raw='5'), op='|',
                                                                expr2=Integer(raw='3')))),
        # Integer definition with bitwise OR
        ('def int bit_xor = 5 ^ 3;', DefAssignment(name='bit_xor', type='int',
                                                   expr=BinaryOp(expr1=Integer(raw='5'), op='^',
                                                                 expr2=Integer(raw='3')))),
        # Integer definition with bitwise XOR
        ('def float complex = 2.0 * 3.0 + 4.0;', DefAssignment(name='complex', type='float', expr=BinaryOp(
            expr1=BinaryOp(expr1=Float(raw='2.0'), op='*', expr2=Float(raw='3.0')), op='+', expr2=Float(raw='4.0')))),
        # Float definition with multiple operations
        ('def int complex_int = 2 * (3 + 4) - 5;', DefAssignment(name='complex_int', type='int', expr=BinaryOp(
            expr1=BinaryOp(expr1=Integer(raw='2'), op='*',
                           expr2=Paren(expr=BinaryOp(expr1=Integer(raw='3'), op='+', expr2=Integer(raw='4')))), op='-',
            expr2=Integer(raw='5')))),  # Integer definition with mixed operations
        ('def float nested = 2.0 ** (3.0 + 1.0);', DefAssignment(name='nested', type='float',
                                                                 expr=BinaryOp(expr1=Float(raw='2.0'), op='**',
                                                                               expr2=Paren(
                                                                                   expr=BinaryOp(expr1=Float(raw='3.0'),
                                                                                                 op='+', expr2=Float(
                                                                                           raw='1.0')))))),
        # Float definition with nested operations
        ('def float sine = sin(0.5);',
         DefAssignment(name='sine', type='float', expr=UFunc(func='sin', expr=Float(raw='0.5')))),
        # Float definition using sine function
        ('def float cosine = cos(pi);',
         DefAssignment(name='cosine', type='float', expr=UFunc(func='cos', expr=Constant(raw='pi')))),
        # Float definition using cosine function with constant
        ('def float sqrt_val = sqrt(16.0);',
         DefAssignment(name='sqrt_val', type='float', expr=UFunc(func='sqrt', expr=Float(raw='16.0')))),
        # Float definition using square root function
        ('def float log_val = log(100.0);',
         DefAssignment(name='log_val', type='float', expr=UFunc(func='log', expr=Float(raw='100.0')))),
        # Float definition using logarithm function
        ('def float abs_val = abs(-15.0);', DefAssignment(name='abs_val', type='float', expr=UFunc(func='abs',
                                                                                                   expr=UnaryOp(op='-',
                                                                                                                expr=Float(
                                                                                                                    raw='15.0'))))),
        # Float definition using absolute value function
    ])
    def test_positive_cases(self, input_text, expected):
        assert parse_with_grammar_entry(input_text, entry_name='def_assignment') == expected

    @pytest.mark.parametrize(['input_text', 'expected_str'], [
        ('def int x = 5;', 'def int x = 5;'),  # Simple integer definition with literal value
        ('def int counter = 0;', 'def int counter = 0;'),  # Integer definition initialized to zero
        ('def int negative = -10;', 'def int negative = -10;'),  # Integer definition with negative value
        ('def float y = 3.14;', 'def float y = 3.14;'),  # Simple float definition with decimal value
        ('def float pi_value = 3.14159;', 'def float pi_value = 3.14159;'),  # Float definition with more precision
        ('def float negative_float = -2.5;', 'def float negative_float = -2.5;'),
        # Float definition with negative value
        ('def float scientific = 1.5e3;', 'def float scientific = 1.5e3;'),
        # Float definition using scientific notation
        ('def float tiny = 1.5e-4;', 'def float tiny = 1.5e-4;'),  # Float definition using negative exponent
        ('def int hex_value = 0x1A;', 'def int hex_value = 0x1a;'),  # Integer definition using hexadecimal notation
        ('def int hex_large = 0xFFFF;', 'def int hex_large = 0xffff;'),  # Integer definition with larger hex value
        ('def float pi_const = pi;', 'def float pi_const = pi;'),  # Float definition using pi constant
        ('def float e_const = E;', 'def float e_const = E;'),  # Float definition using E constant
        ('def float tau_const = tau;', 'def float tau_const = tau;'),  # Float definition using tau constant
        ('def int grouped = (10 + 5);', 'def int grouped = (10 + 5);'),
        # Integer definition with parenthesized expression
        ('def float complex_group = ((3.0 + 2.0) * 4.0);', 'def float complex_group = ((3.0 + 2.0) * 4.0);'),
        # Float definition with nested parentheses
        ('def int positive = +15;', 'def int positive = +15;'),  # Integer definition with explicit positive sign
        ('def int negative_expr = -(5);', 'def int negative_expr = -(5);'),
        # Integer definition with parenthesized negative expression
        ('def int sum = 5 + 3;', 'def int sum = 5 + 3;'),  # Integer definition with addition
        ('def int difference = 10 - 4;', 'def int difference = 10 - 4;'),  # Integer definition with subtraction
        ('def float product = 2.5 * 3.0;', 'def float product = 2.5 * 3.0;'),  # Float definition with multiplication
        ('def float quotient = 10.0 / 2.0;', 'def float quotient = 10.0 / 2.0;'),  # Float definition with division
        ('def int remainder = 10 % 3;', 'def int remainder = 10 % 3;'),  # Integer definition with modulo operation
        ('def float power = 2.0 ** 3.0;', 'def float power = 2.0 ** 3.0;'),  # Float definition with power operation
        ('def int bit_shift_left = 1 << 3;', 'def int bit_shift_left = 1 << 3;'),  # Integer definition with left shift
        ('def int bit_shift_right = 16 >> 2;', 'def int bit_shift_right = 16 >> 2;'),
        # Integer definition with right shift
        ('def int bit_and = 5 & 3;', 'def int bit_and = 5 & 3;'),  # Integer definition with bitwise AND
        ('def int bit_or = 5 | 3;', 'def int bit_or = 5 | 3;'),  # Integer definition with bitwise OR
        ('def int bit_xor = 5 ^ 3;', 'def int bit_xor = 5 ^ 3;'),  # Integer definition with bitwise XOR
        ('def float complex = 2.0 * 3.0 + 4.0;', 'def float complex = 2.0 * 3.0 + 4.0;'),
        # Float definition with multiple operations
        ('def int complex_int = 2 * (3 + 4) - 5;', 'def int complex_int = 2 * (3 + 4) - 5;'),
        # Integer definition with mixed operations
        ('def float nested = 2.0 ** (3.0 + 1.0);', 'def float nested = 2.0 ** (3.0 + 1.0);'),
        # Float definition with nested operations
        ('def float sine = sin(0.5);', 'def float sine = sin(0.5);'),  # Float definition using sine function
        ('def float cosine = cos(pi);', 'def float cosine = cos(pi);'),
        # Float definition using cosine function with constant
        ('def float sqrt_val = sqrt(16.0);', 'def float sqrt_val = sqrt(16.0);'),
        # Float definition using square root function
        ('def float log_val = log(100.0);', 'def float log_val = log(100.0);'),
        # Float definition using logarithm function
        ('def float abs_val = abs(-15.0);', 'def float abs_val = abs(-15.0);'),
        # Float definition using absolute value function
    ])
    def test_positive_cases_str(self, input_text, expected_str):
        assert str(parse_with_grammar_entry(input_text, entry_name='def_assignment')) == expected_str

    @pytest.mark.parametrize(['input_text'], [
        ('int x = 5;',),  # Missing 'def' keyword at the beginning
        ('def x = 5;',),  # Missing type specification (int or float)
        ('def string name = "John";',),  # Invalid type 'string' not supported in grammar
        ('def bool flag = true;',),  # Invalid type 'bool' not supported in grammar
        ('def int = 10;',),  # Missing identifier after type
        ('def int count 5;',),  # Missing equals sign between identifier and value
        ('def int z = 42',),  # Missing semicolon at the end
        ('def int invalid = 3 + ;',),  # Incomplete binary expression
        ('def float broken = 3.0 * ;',),  # Missing right operand in multiplication
        ('def int error = * 5;',),  # Missing left operand in multiplication
        # ('def int decimal = 3.14;',),  # Using float literal in int definition
        ('def float text = "hello";',),  # Using string literal in float definition
        ('def int wrong = 5 $ 3;',),  # Invalid operator '$' in expression
        # ('def float invalid = 3.0 ++ 2.0;',),  # Invalid operator '++' in expression
        ('def float invalid_func = notAFunction(5.0);',),  # Using undefined function
        ('def float missing_arg = sin();',),  # Missing argument in function call
        ('def float extra_args = sin(1.0, 2.0);',),  # Too many arguments in function call
        ('def int comparison = 5 > 3;',),  # Boolean comparison not allowed in init_expression
        ('def int logical = true && false;',),  # Logical operation not allowed in init_expression
        ('def int conditional = (5 > 3) ? 1 : 0;',),  # Conditional expression not allowed in init_expression
        ('def int wrong_assign := 10;',),  # Using ':=' instead of '=' for definition
        ('def int a = 1, b = 2;',),  # Multiple definitions not allowed in one statement
        ('def float incomplete = sin 0.5;',),  # Missing parentheses in function call
        ('def int extra tokens = 5;',),  # Extra tokens in definition
        ('def = int x 5;',),  # Wrong order of tokens in definition
    ])
    def test_negative_cases(self, input_text):
        with pytest.raises(GrammarParseError) as ei:
            parse_with_grammar_entry(input_text, entry_name='def_assignment')
            # parse_condition(input_text)

        err = ei.value
        assert isinstance(err, GrammarParseError)
        assert len(err.errors) > 0
        # assert len([e for e in err.errors if isinstance(e, SyntaxFailError)]) > 0
        assert f'Found {len(err.errors)} errors during parsing:' in err.args[0]

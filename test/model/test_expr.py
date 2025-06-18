import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.expr import *


@pytest.mark.unittest
class TestModelExpr:
    @pytest.mark.parametrize(['expr_text', 'expected_expr'], [
        ('42', Integer(value=42)),  # Integer literal 42
        ('3.14', Float(value=3.14)),  # Floating point literal 3.14
        ('0x2A', Integer(value=42)),  # Hexadecimal integer literal 42
        ('pi', Float(value=3.141592653589793)),  # Mathematical constant pi
        ('E', Float(value=2.718281828459045)),  # Mathematical constant E (Euler's number)
        ('tau', Float(value=6.283185307179586)),  # Mathematical constant tau (2*pi)
        ('x', Variable(name='x')),  # Variable reference to x
        ('-5', UnaryOp(op='-', x=Integer(value=5))),  # Negative integer literal 5
        ('+7', UnaryOp(op='+', x=Integer(value=7))),  # Positive integer literal 7
        ('a + b', BinaryOp(x=Variable(name='a'), op='+', y=Variable(name='b'))),  # Addition of variables a and b
        ('x - y', BinaryOp(x=Variable(name='x'), op='-', y=Variable(name='y'))),  # Subtraction of y from x
        ('p * q', BinaryOp(x=Variable(name='p'), op='*', y=Variable(name='q'))),  # Multiplication of variables p and q
        ('m / n', BinaryOp(x=Variable(name='m'), op='/', y=Variable(name='n'))),  # Division of m by n
        ('i % j', BinaryOp(x=Variable(name='i'), op='%', y=Variable(name='j'))),  # Modulo operation of i by j
        ('2 ** 3', BinaryOp(x=Integer(value=2), op='**', y=Integer(value=3))),  # 2 raised to the power of 3
        ('a << 2', BinaryOp(x=Variable(name='a'), op='<<', y=Integer(value=2))),  # Left bit shift of a by 2 bits
        ('b >> 1', BinaryOp(x=Variable(name='b'), op='>>', y=Integer(value=1))),  # Right bit shift of b by 1 bit
        ('x & y', BinaryOp(x=Variable(name='x'), op='&', y=Variable(name='y'))),  # Bitwise AND of x and y
        ('p | q', BinaryOp(x=Variable(name='p'), op='|', y=Variable(name='q'))),  # Bitwise OR of p and q
        ('m ^ n', BinaryOp(x=Variable(name='m'), op='^', y=Variable(name='n'))),  # Bitwise XOR of m and n
        ('sin(x)', UFunc(func='sin', x=Variable(name='x'))),  # Sine of x
        ('cos(theta)', UFunc(func='cos', x=Variable(name='theta'))),  # Cosine of theta
        ('sqrt(2)', UFunc(func='sqrt', x=Integer(value=2))),  # Square root of 2
        ('log(x)', UFunc(func='log', x=Variable(name='x'))),  # Natural logarithm of x
        ('abs(-7)', UFunc(func='abs', x=UnaryOp(op='-', x=Integer(value=7)))),  # Absolute value of -7
        ('(a + b)', BinaryOp(x=Variable(name='a'), op='+', y=Variable(name='b'))),  # Parenthesized addition of a and b
        ('(x * y) + z',
         BinaryOp(x=BinaryOp(x=Variable(name='x'), op='*', y=Variable(name='y')), op='+', y=Variable(name='z'))),
        # Addition of the product of x and y with z
        ('(x > y) ? a : b',
         ConditionalOp(cond=BinaryOp(x=Variable(name='x'), op='>', y=Variable(name='y')), if_true=Variable(name='a'),
                       if_false=Variable(name='b'))),  # If x is greater than y, return a, otherwise return b
        ('(flag == 0x2) ? 1 : 0',
         ConditionalOp(cond=BinaryOp(x=Variable(name='flag'), op='==', y=Integer(value=2)), if_true=Integer(value=1),
                       if_false=Integer(value=0))),  # If flag equals 0x2, return 1, otherwise return 0
        ('sin(x) + cos(y)',
         BinaryOp(x=UFunc(func='sin', x=Variable(name='x')), op='+', y=UFunc(func='cos', x=Variable(name='y')))),
        # Addition of sine of x and cosine of y
        ('(a + b) * (c - d)', BinaryOp(x=BinaryOp(x=Variable(name='a'), op='+', y=Variable(name='b')), op='*',
                                       y=BinaryOp(x=Variable(name='c'), op='-', y=Variable(name='d')))),
        # Product of the sum of a and b with the difference of c and d
        ('log(x ** 2 + 1)', UFunc(func='log',
                                  x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='**', y=Integer(value=2)), op='+',
                                             y=Integer(value=1)))),  # Natural logarithm of x squared plus 1
        ('(a & b) | (c & d)', BinaryOp(x=BinaryOp(x=Variable(name='a'), op='&', y=Variable(name='b')), op='|',
                                       y=BinaryOp(x=Variable(name='c'), op='&', y=Variable(name='d')))),
        # Bitwise OR of (a AND b) with (c AND d)
        ('sqrt(x * x + y * y)', UFunc(func='sqrt',
                                      x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='*', y=Variable(name='x')), op='+',
                                                 y=BinaryOp(x=Variable(name='y'), op='*', y=Variable(name='y'))))),
        # Square root of the sum of squares of x and y (Euclidean distance)
        ('abs(x) + abs(y)',
         BinaryOp(x=UFunc(func='abs', x=Variable(name='x')), op='+', y=UFunc(func='abs', x=Variable(name='y')))),
        # Sum of absolute values of x and y (Manhattan distance)
        ('sin(2 * pi * f * t + phi)', UFunc(func='sin', x=BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Integer(value=2), op='*', y=Float(value=3.141592653589793)), op='*',
                       y=Variable(name='f')), op='*', y=Variable(name='t')), op='+', y=Variable(name='phi')))),
        # Sine wave with frequency f, time t, and phase phi
        ('(x ** 2 + y ** 2 <= r ** 2) ? 1 : 0', ConditionalOp(cond=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='**', y=Integer(value=2)), op='+',
                       y=BinaryOp(x=Variable(name='y'), op='**', y=Integer(value=2))), op='<=',
            y=BinaryOp(x=Variable(name='r'), op='**', y=Integer(value=2))), if_true=Integer(value=1),
            if_false=Integer(value=0))),
        # Check if point (x,y) is within circle of radius r
        ('log(abs(x) + sqrt(x ** 2 + 1))', UFunc(func='log',
                                                 x=BinaryOp(x=UFunc(func='abs', x=Variable(name='x')), op='+',
                                                            y=UFunc(func='sqrt', x=BinaryOp(
                                                                x=BinaryOp(x=Variable(name='x'), op='**',
                                                                           y=Integer(value=2)), op='+',
                                                                y=Integer(value=1)))))),
        # Logarithm of a complex mathematical expression
        ('(a << 2) & (b >> 1) | (c ^ d)', BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='<<', y=Integer(value=2)), op='&',
                       y=BinaryOp(x=Variable(name='b'), op='>>', y=Integer(value=1))), op='|',
            y=BinaryOp(x=Variable(name='c'), op='^', y=Variable(name='d')))),
        # Complex bitwise operation combining shift, AND, OR, and XOR
        ('(sin(x) ** 2 + cos(x) ** 2) * (1 + tan(y) ** 2) / (1 + tanh(z) ** 2)', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=UFunc(func='sin', x=Variable(name='x')), op='**', y=Integer(value=2)), op='+',
                       y=BinaryOp(x=UFunc(func='cos', x=Variable(name='x')), op='**', y=Integer(value=2))), op='*',
            y=BinaryOp(x=Integer(value=1), op='+',
                       y=BinaryOp(x=UFunc(func='tan', x=Variable(name='y')), op='**', y=Integer(value=2)))), op='/',
            y=BinaryOp(x=Integer(value=1),
                       op='+', y=BinaryOp(
                    x=UFunc(func='tanh',
                            x=Variable(
                                name='z')),
                    op='**', y=Integer(
                        value=2))))),
        # Complex trigonometric identity expression
        ('(a + b) * (c - d) / ((e + f) * (g - h)) ** (i % j)', BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='+', y=Variable(name='b')), op='*',
                       y=BinaryOp(x=Variable(name='c'), op='-', y=Variable(name='d'))), op='/', y=BinaryOp(
                x=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='+', y=Variable(name='f')), op='*',
                           y=BinaryOp(x=Variable(name='g'), op='-', y=Variable(name='h'))), op='**',
                y=BinaryOp(x=Variable(name='i'), op='%', y=Variable(name='j'))))),
        # Complex arithmetic expression with multiple operations and groupings
        ('log(sqrt(x ** 2 + y ** 2)) + atan(2 * y)', BinaryOp(x=UFunc(func='log', x=UFunc(func='sqrt', x=BinaryOp(
            x=BinaryOp(x=Variable(name='x'), op='**', y=Integer(value=2)), op='+',
            y=BinaryOp(x=Variable(name='y'), op='**', y=Integer(value=2))))), op='+', y=UFunc(func='atan', x=BinaryOp(
            x=Integer(value=2), op='*', y=Variable(name='y'))))),  # Logarithm of distance plus angle calculation
        ('(x > y) ? (a < b) ? p : q : (c < d) ? m : n',
         ConditionalOp(cond=BinaryOp(x=Variable(name='x'), op='>', y=Variable(name='y')),
                       if_true=ConditionalOp(cond=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')),
                                             if_true=Variable(name='p'), if_false=Variable(name='q')),
                       if_false=ConditionalOp(cond=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d')),
                                              if_true=Variable(name='m'), if_false=Variable(name='n')))),
        # Nested conditional expression with multiple conditions
        ('sin(cos(tan(x))) + log(exp(sqrt(abs(y))))',
         BinaryOp(x=UFunc(func='sin', x=UFunc(func='cos', x=UFunc(func='tan', x=Variable(name='x')))), op='+',
                  y=UFunc(func='log',
                          x=UFunc(func='exp', x=UFunc(func='sqrt', x=UFunc(func='abs', x=Variable(name='y'))))))),
        # Nested function calls with various mathematical functions
        ('((a & b) | (c ^ d)) << ((e + f) % 8)', BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='&', y=Variable(name='b')), op='|',
                       y=BinaryOp(x=Variable(name='c'), op='^', y=Variable(name='d'))), op='<<',
            y=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='+', y=Variable(name='f')), op='%', y=Integer(value=8)))),
        # Bitwise operations combined with arithmetic for shift amount
        ('(x ** 2 + y ** 2 + z ** 2) ** 0.5', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='**', y=Integer(value=2)), op='+',
                       y=BinaryOp(x=Variable(name='y'), op='**', y=Integer(value=2))), op='+',
            y=BinaryOp(x=Variable(name='z'), op='**', y=Integer(value=2))), op='**', y=Float(value=0.5))),
        # Calculation of 3D Euclidean distance using exponentiation
        ('(a > b && c < d) ? (e + f) * g : (h - i) / j', ConditionalOp(
            cond=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='>', y=Variable(name='b')), op='&&',
                          y=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d'))),
            if_true=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='+', y=Variable(name='f')), op='*',
                             y=Variable(name='g')),
            if_false=BinaryOp(x=BinaryOp(x=Variable(name='h'), op='-', y=Variable(name='i')), op='/',
                              y=Variable(name='j')))),  # Conditional expression with logical AND in condition
        ('sin(2 * pi * f * t) * exp(-t / tau) + A * cos(omega * t + phi)', BinaryOp(x=BinaryOp(x=UFunc(func='sin',
                                                                                                       x=BinaryOp(
                                                                                                           x=BinaryOp(
                                                                                                               x=BinaryOp(
                                                                                                                   x=Integer(
                                                                                                                       value=2),
                                                                                                                   op='*',
                                                                                                                   y=Float(
                                                                                                                       value=3.141592653589793)),
                                                                                                               op='*',
                                                                                                               y=Variable(
                                                                                                                   name='f')),
                                                                                                           op='*',
                                                                                                           y=Variable(
                                                                                                               name='t'))),
                                                                                               op='*',
                                                                                               y=UFunc(func='exp',
                                                                                                       x=BinaryOp(
                                                                                                           x=UnaryOp(
                                                                                                               op='-',
                                                                                                               x=Variable(
                                                                                                                   name='t')),
                                                                                                           op='/',
                                                                                                           y=Float(
                                                                                                               value=6.283185307179586)))),
                                                                                    op='+',
                                                                                    y=BinaryOp(x=Variable(name='A'),
                                                                                               op='*',
                                                                                               y=UFunc(func='cos',
                                                                                                       x=BinaryOp(
                                                                                                           x=BinaryOp(
                                                                                                               x=Variable(
                                                                                                                   name='omega'),
                                                                                                               op='*',
                                                                                                               y=Variable(
                                                                                                                   name='t')),
                                                                                                           op='+',
                                                                                                           y=Variable(
                                                                                                               name='phi')))))),
        # Damped sinusoidal oscillation with offset
        ('(((x & 0xFF) << 16) | ((y & 0xFF) << 8) | (z & 0xFF))', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='&', y=Integer(value=255)), op='<<', y=Integer(value=16)),
            op='|',
            y=BinaryOp(x=BinaryOp(x=Variable(name='y'), op='&', y=Integer(value=255)), op='<<', y=Integer(value=8))),
            op='|',
            y=BinaryOp(x=Variable(name='z'), op='&',
                       y=Integer(value=255)))),
        # RGB color value packing using bitwise operations

    ])
    def test_num_expression_parse_to_model(self, expr_text, expected_expr):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='num_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert pytest.approx(expected_expr) == expr

    @pytest.mark.parametrize(['expr_text', 'expected_expr'], [
        ('true', Boolean(value=True)),  # Boolean literal true
        ('false', Boolean(value=False)),  # Boolean literal false
        ('True', Boolean(value=True)),  # Boolean literal True (alternative syntax)
        ('False', Boolean(value=False)),  # Boolean literal False (alternative syntax)
        ('x > y', BinaryOp(x=Variable(name='x'), op='>', y=Variable(name='y'))),  # Check if x is greater than y
        ('a < b', BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b'))),  # Check if a is less than b
        ('m >= n', BinaryOp(x=Variable(name='m'), op='>=', y=Variable(name='n'))),
        # Check if m is greater than or equal to n
        ('p <= q', BinaryOp(x=Variable(name='p'), op='<=', y=Variable(name='q'))),
        # Check if p is less than or equal to q
        ('x == y', BinaryOp(x=Variable(name='x'), op='==', y=Variable(name='y'))),  # Check if x equals y
        ('a != b', BinaryOp(x=Variable(name='a'), op='!=', y=Variable(name='b'))),  # Check if a is not equal to b
        ('!(x > y)', UnaryOp(op='!', x=BinaryOp(x=Variable(name='x'), op='>', y=Variable(name='y')))),
        # Logical NOT of the comparison x > y
        ('not (a == b)', UnaryOp(op='!', x=BinaryOp(x=Variable(name='a'), op='==', y=Variable(name='b')))),
        # Logical NOT of the comparison a equals b (alternative syntax)
        ('(a > 0) && (b < 1)', BinaryOp(x=BinaryOp(x=Variable(name='a'), op='>', y=Integer(value=0)), op='&&',
                                        y=BinaryOp(x=Variable(name='b'), op='<', y=Integer(value=1)))),
        # Logical AND of a > 0 and b < 1
        ('(x == 0) || (y != 1)', BinaryOp(x=BinaryOp(x=Variable(name='x'), op='==', y=Integer(value=0)), op='||',
                                          y=BinaryOp(x=Variable(name='y'), op='!=', y=Integer(value=1)))),
        # Logical OR of x == 0 and y != 1
        ('(p > 0) and (q < 1)', BinaryOp(x=BinaryOp(x=Variable(name='p'), op='>', y=Integer(value=0)), op='&&',
                                         y=BinaryOp(x=Variable(name='q'), op='<', y=Integer(value=1)))),
        # Logical AND of p > 0 and q < 1 (alternative syntax)
        ('(m == 0) or (n != 1)', BinaryOp(x=BinaryOp(x=Variable(name='m'), op='==', y=Integer(value=0)), op='||',
                                          y=BinaryOp(x=Variable(name='n'), op='!=', y=Integer(value=1)))),
        # Logical OR of m == 0 and n != 1 (alternative syntax)
        ('(x > y)', BinaryOp(x=Variable(name='x'), op='>', y=Variable(name='y'))),
        # Parenthesized comparison of x and y
        ('!(a < b)', UnaryOp(op='!', x=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')))),
        # Negation of the comparison a < b
        ('(x > y) ? (a < b) : (c < d)', ConditionalOp(cond=BinaryOp(x=Variable(name='x'), op='>', y=Variable(name='y')),
                                                      if_true=BinaryOp(x=Variable(name='a'), op='<',
                                                                       y=Variable(name='b')),
                                                      if_false=BinaryOp(x=Variable(name='c'), op='<',
                                                                        y=Variable(name='d')))),
        # If x > y, check a < b, otherwise check c < d
        ('(x > 0) ? true : false',
         ConditionalOp(cond=BinaryOp(x=Variable(name='x'), op='>', y=Integer(value=0)), if_true=Boolean(value=True),
                       if_false=Boolean(value=False))),  # If x > 0, return true, otherwise return false
        ('x > 0 && y > 0', BinaryOp(x=BinaryOp(x=Variable(name='x'), op='>', y=Integer(value=0)), op='&&',
                                    y=BinaryOp(x=Variable(name='y'), op='>', y=Integer(value=0)))),
        # Check if both x and y are positive
        ('a < b || c < d', BinaryOp(x=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')), op='||',
                                    y=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d')))),
        # Check if either a < b or c < d is true
        ('(x >= min) && (x <= max)',
         BinaryOp(x=BinaryOp(x=Variable(name='x'), op='>=', y=Variable(name='min')), op='&&',
                  y=BinaryOp(x=Variable(name='x'), op='<=', y=Variable(name='max')))),
        # Check if x is within range [min, max]
        ('!(a == b) && !(c == d)',
         BinaryOp(x=UnaryOp(op='!', x=BinaryOp(x=Variable(name='a'), op='==', y=Variable(name='b'))), op='&&',
                  y=UnaryOp(op='!', x=BinaryOp(x=Variable(name='c'), op='==', y=Variable(name='d'))))),
        # Check if both a != b and c != d
        ('(temp > 100) || (pressure > 200)',
         BinaryOp(x=BinaryOp(x=Variable(name='temp'), op='>', y=Integer(value=100)), op='||',
                  y=BinaryOp(x=Variable(name='pressure'), op='>', y=Integer(value=200)))),
        # Check if either temperature exceeds 100 or pressure exceeds 200
        ('x == y && y == z', BinaryOp(x=BinaryOp(x=Variable(name='x'), op='==', y=Variable(name='y')), op='&&',
                                      y=BinaryOp(x=Variable(name='y'), op='==', y=Variable(name='z')))),
        # Check if all three values are equal
        ('(a < b && c < d) || (e < f && g < h)', BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')), op='&&',
                       y=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d'))), op='||',
            y=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='<', y=Variable(name='f')), op='&&',
                       y=BinaryOp(x=Variable(name='g'), op='<', y=Variable(name='h'))))),
        # Check if either both a < b and c < d, or both e < f and g < h
        ('(x > 0) ? (y > 0) : (z > 0)', ConditionalOp(cond=BinaryOp(x=Variable(name='x'), op='>', y=Integer(value=0)),
                                                      if_true=BinaryOp(x=Variable(name='y'), op='>',
                                                                       y=Integer(value=0)),
                                                      if_false=BinaryOp(x=Variable(name='z'), op='>',
                                                                        y=Integer(value=0)))),
        # If x is positive, check if y is positive, otherwise check if z is positive
        ('!(a < b || c < d) && (e < f)', BinaryOp(x=UnaryOp(op='!', x=BinaryOp(
            x=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')), op='||',
            y=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d')))), op='&&',
                                                  y=BinaryOp(x=Variable(name='e'), op='<', y=Variable(name='f')))),
        # Check if both NOT(a < b OR c < d) and e < f
        ('(x == 0) || (y != 0 && z == 0)',
         BinaryOp(x=BinaryOp(x=Variable(name='x'), op='==', y=Integer(value=0)), op='||',
                  y=BinaryOp(x=BinaryOp(x=Variable(name='y'), op='!=', y=Integer(value=0)), op='&&',
                             y=BinaryOp(x=Variable(name='z'), op='==', y=Integer(value=0))))),
        # Check if x is 0 OR (y is not 0 AND z is 0)
        ('(a > b && c > d) || (e > f && g > h) || (i > j && k > l)', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='>', y=Variable(name='b')), op='&&',
                       y=BinaryOp(x=Variable(name='c'), op='>', y=Variable(name='d'))), op='||',
            y=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='>', y=Variable(name='f')), op='&&',
                       y=BinaryOp(x=Variable(name='g'), op='>', y=Variable(name='h')))), op='||', y=BinaryOp(
            x=BinaryOp(x=Variable(name='i'), op='>', y=Variable(name='j')), op='&&',
            y=BinaryOp(x=Variable(name='k'), op='>', y=Variable(name='l'))))),
        # Complex condition with multiple AND and OR combinations
        ('!((x < y) && (z < w)) || (p == q && r != s)', BinaryOp(x=UnaryOp(op='!', x=BinaryOp(
            x=BinaryOp(x=Variable(name='x'), op='<', y=Variable(name='y')), op='&&',
            y=BinaryOp(x=Variable(name='z'), op='<', y=Variable(name='w')))), op='||', y=BinaryOp(
            x=BinaryOp(x=Variable(name='p'), op='==', y=Variable(name='q')), op='&&',
            y=BinaryOp(x=Variable(name='r'), op='!=', y=Variable(name='s'))))),
        # Negation of a conjunction combined with another conjunction
        ('((a < b) ? c < d : e < f) && ((g < h) ? i < j : k < l)', BinaryOp(
            x=ConditionalOp(cond=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')),
                            if_true=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d')),
                            if_false=BinaryOp(x=Variable(name='e'), op='<', y=Variable(name='f'))), op='&&',
            y=ConditionalOp(cond=BinaryOp(x=Variable(name='g'), op='<', y=Variable(name='h')),
                            if_true=BinaryOp(x=Variable(name='i'), op='<', y=Variable(name='j')),
                            if_false=BinaryOp(x=Variable(name='k'), op='<', y=Variable(name='l'))))),
        # Logical AND of two conditional expressions
        ('(x == y) == (a == b) && (c != d) != (e != f)', BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='==', y=Variable(name='y')), op='==',
                       y=BinaryOp(x=Variable(name='a'), op='==', y=Variable(name='b'))), op='&&',
            y=BinaryOp(x=BinaryOp(x=Variable(name='c'), op='!=', y=Variable(name='d')), op='!=',
                       y=BinaryOp(x=Variable(name='e'), op='!=', y=Variable(name='f'))))),
        # Equality comparison of equality comparisons
        (
                '(a > 0 && b > 0) || (c > 0 && d > 0) ? (e > 0 || f > 0) && (g > 0 || h > 0) : (i > 0 && j > 0) || (k > 0 && l > 0)',
                BinaryOp(x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='>', y=Integer(value=0)), op='&&',
                                    y=BinaryOp(x=Variable(name='b'), op='>', y=Integer(value=0))), op='||',
                         y=ConditionalOp(
                             cond=BinaryOp(x=BinaryOp(x=Variable(name='c'), op='>', y=Integer(value=0)), op='&&',
                                           y=BinaryOp(x=Variable(name='d'), op='>', y=Integer(value=0))),
                             if_true=BinaryOp(
                                 x=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='>', y=Integer(value=0)), op='||',
                                            y=BinaryOp(x=Variable(name='f'), op='>', y=Integer(value=0))), op='&&',
                                 y=BinaryOp(x=BinaryOp(x=Variable(name='g'), op='>', y=Integer(value=0)), op='||',
                                            y=BinaryOp(x=Variable(name='h'), op='>', y=Integer(value=0)))),
                             if_false=BinaryOp(
                                 x=BinaryOp(x=BinaryOp(x=Variable(name='i'), op='>', y=Integer(value=0)), op='&&',
                                            y=BinaryOp(x=Variable(name='j'), op='>', y=Integer(value=0))), op='||',
                                 y=BinaryOp(x=BinaryOp(x=Variable(name='k'), op='>', y=Integer(value=0)), op='&&',
                                            y=BinaryOp(x=Variable(name='l'), op='>', y=Integer(value=0))))))),
        # Conditional expression with complex conditions
        ('!(a < b) && !(c < d) || !(e < f) && !(g < h)', BinaryOp(
            x=BinaryOp(x=UnaryOp(op='!', x=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b'))), op='&&',
                       y=UnaryOp(op='!', x=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d')))), op='||',
            y=BinaryOp(x=UnaryOp(op='!', x=BinaryOp(x=Variable(name='e'), op='<', y=Variable(name='f'))), op='&&',
                       y=UnaryOp(op='!', x=BinaryOp(x=Variable(name='g'), op='<', y=Variable(name='h')))))),
        # Complex expression with multiple negations and logical operators
        ('(x > 0 && y > 0 && z > 0) || (x < 0 && y < 0 && z < 0)', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='>', y=Integer(value=0)), op='&&',
                       y=BinaryOp(x=Variable(name='y'), op='>', y=Integer(value=0))), op='&&',
            y=BinaryOp(x=Variable(name='z'), op='>', y=Integer(value=0))), op='||', y=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='<', y=Integer(value=0)), op='&&',
                       y=BinaryOp(x=Variable(name='y'), op='<', y=Integer(value=0))), op='&&',
            y=BinaryOp(x=Variable(name='z'), op='<', y=Integer(value=0))))),
        # Check if all coordinates are positive or all are negative
        ('(a == 1 || a == 2 || a == 3) && (b == 1 || b == 2 || b == 3)', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='==', y=Integer(value=1)), op='||',
                       y=BinaryOp(x=Variable(name='a'), op='==', y=Integer(value=2))), op='||',
            y=BinaryOp(x=Variable(name='a'), op='==', y=Integer(value=3))), op='&&', y=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='b'), op='==', y=Integer(value=1)), op='||',
                       y=BinaryOp(x=Variable(name='b'), op='==', y=Integer(value=2))), op='||',
            y=BinaryOp(x=Variable(name='b'), op='==', y=Integer(value=3))))),
        # Check if both a and b are one of the values 1, 2, or 3
        ('((x > y) ? x : y) > ((a > b) ? a : b)', BinaryOp(
            x=ConditionalOp(cond=BinaryOp(x=Variable(name='x'), op='>', y=Variable(name='y')),
                            if_true=Variable(name='x'), if_false=Variable(name='y')), op='>',
            y=ConditionalOp(cond=BinaryOp(x=Variable(name='a'), op='>', y=Variable(name='b')),
                            if_true=Variable(name='a'), if_false=Variable(name='b')))),
        # Compare the maximum of x and y with the maximum of a and b
        ('!((a < b) ? c < d : e < f) && ((g < h) ? !(i < j) : !(k < l))', BinaryOp(x=UnaryOp(op='!', x=ConditionalOp(
            cond=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')),
            if_true=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d')),
            if_false=BinaryOp(x=Variable(name='e'), op='<', y=Variable(name='f')))), op='&&', y=ConditionalOp(
            cond=BinaryOp(x=Variable(name='g'), op='<', y=Variable(name='h')),
            if_true=UnaryOp(op='!', x=BinaryOp(x=Variable(name='i'), op='<', y=Variable(name='j'))),
            if_false=UnaryOp(op='!', x=BinaryOp(x=Variable(name='k'), op='<', y=Variable(name='l')))))),
        # Complex expression with negations and conditional expressions
        ('(a == b && c == d) || (e == f && g == h) || (i == j && k == l) || (m == n && o == p)', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='==', y=Variable(name='b')), op='&&',
                                  y=BinaryOp(x=Variable(name='c'), op='==', y=Variable(name='d'))), op='||',
                       y=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='==', y=Variable(name='f')), op='&&',
                                  y=BinaryOp(x=Variable(name='g'), op='==', y=Variable(name='h')))), op='||',
            y=BinaryOp(x=BinaryOp(x=Variable(name='i'), op='==', y=Variable(name='j')), op='&&',
                       y=BinaryOp(x=Variable(name='k'), op='==', y=Variable(name='l')))), op='||', y=BinaryOp(
            x=BinaryOp(x=Variable(name='m'), op='==', y=Variable(name='n')), op='&&',
            y=BinaryOp(x=Variable(name='o'), op='==', y=Variable(name='p'))))),
        # Multiple equality checks combined with AND and OR
        ('((a < b) && (c < d)) ? ((e < f) || (g < h)) : ((i < j) && (k < l)) || ((m < n) || (o < p))', ConditionalOp(
            cond=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')), op='&&',
                          y=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d'))),
            if_true=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='<', y=Variable(name='f')), op='||',
                             y=BinaryOp(x=Variable(name='g'), op='<', y=Variable(name='h'))), if_false=BinaryOp(
                x=BinaryOp(x=BinaryOp(x=Variable(name='i'), op='<', y=Variable(name='j')), op='&&',
                           y=BinaryOp(x=Variable(name='k'), op='<', y=Variable(name='l'))), op='||',
                y=BinaryOp(x=BinaryOp(x=Variable(name='m'), op='<', y=Variable(name='n')), op='||',
                           y=BinaryOp(x=Variable(name='o'), op='<', y=Variable(name='p')))))),
        # Complex conditional with multiple comparisons
        ('(x >= min && x <= max) || (y >= min && y <= max) || (z >= min && z <= max)', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='x'), op='>=', y=Variable(name='min')), op='&&',
                       y=BinaryOp(x=Variable(name='x'), op='<=', y=Variable(name='max'))), op='||',
            y=BinaryOp(x=BinaryOp(x=Variable(name='y'), op='>=', y=Variable(name='min')), op='&&',
                       y=BinaryOp(x=Variable(name='y'), op='<=', y=Variable(name='max')))), op='||', y=BinaryOp(
            x=BinaryOp(x=Variable(name='z'), op='>=', y=Variable(name='min')), op='&&',
            y=BinaryOp(x=Variable(name='z'), op='<=', y=Variable(name='max'))))),
        # Check if any of x, y, or z is within range [min, max]
        ('!((a < b || c < d) && (e < f || g < h)) || !((i < j || k < l) && (m < n || o < p))', BinaryOp(
            x=UnaryOp(op='!', x=BinaryOp(
                x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='<', y=Variable(name='b')), op='||',
                           y=BinaryOp(x=Variable(name='c'), op='<', y=Variable(name='d'))), op='&&',
                y=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='<', y=Variable(name='f')), op='||',
                           y=BinaryOp(x=Variable(name='g'), op='<', y=Variable(name='h'))))), op='||', y=UnaryOp(op='!',
                                                                                                                 x=BinaryOp(
                                                                                                                     x=BinaryOp(
                                                                                                                         x=BinaryOp(
                                                                                                                             x=Variable(
                                                                                                                                 name='i'),
                                                                                                                             op='<',
                                                                                                                             y=Variable(
                                                                                                                                 name='j')),
                                                                                                                         op='||',
                                                                                                                         y=BinaryOp(
                                                                                                                             x=Variable(
                                                                                                                                 name='k'),
                                                                                                                             op='<',
                                                                                                                             y=Variable(
                                                                                                                                 name='l'))),
                                                                                                                     op='&&',
                                                                                                                     y=BinaryOp(
                                                                                                                         x=BinaryOp(
                                                                                                                             x=Variable(
                                                                                                                                 name='m'),
                                                                                                                             op='<',
                                                                                                                             y=Variable(
                                                                                                                                 name='n')),
                                                                                                                         op='||',
                                                                                                                         y=BinaryOp(
                                                                                                                             x=Variable(
                                                                                                                                 name='o'),
                                                                                                                             op='<',
                                                                                                                             y=Variable(
                                                                                                                                 name='p'))))))),
        # Complex expression with negations of conjunctions of disjunctions
        ('((a > 0 && b > 0) || (c > 0 && d > 0)) == ((e > 0 && f > 0) || (g > 0 && h > 0))', BinaryOp(x=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='a'), op='>', y=Integer(value=0)), op='&&',
                       y=BinaryOp(x=Variable(name='b'), op='>', y=Integer(value=0))), op='||',
            y=BinaryOp(x=BinaryOp(x=Variable(name='c'), op='>', y=Integer(value=0)), op='&&',
                       y=BinaryOp(x=Variable(name='d'), op='>', y=Integer(value=0)))), op='==', y=BinaryOp(
            x=BinaryOp(x=BinaryOp(x=Variable(name='e'), op='>', y=Integer(value=0)), op='&&',
                       y=BinaryOp(x=Variable(name='f'), op='>', y=Integer(value=0))), op='||',
            y=BinaryOp(x=BinaryOp(x=Variable(name='g'), op='>', y=Integer(value=0)), op='&&',
                       y=BinaryOp(x=Variable(name='h'), op='>', y=Integer(value=0)))))),
        # Compare equality of two complex boolean expressions
    ])
    def test_cond_expression_parse_to_model(self, expr_text, expected_expr):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='cond_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert pytest.approx(expected_expr) == expr

    @pytest.mark.parametrize(['expr_text', 'expected_str'], [
        ('42', '42'),  # Integer literal 42
        ('3.14', '3.14'),  # Floating point literal 3.14
        ('0x2A', '42'),  # Hexadecimal integer literal 42
        ('pi', 'pi'),  # Mathematical constant pi
        ('E', 'E'),  # Mathematical constant E (Euler's number)
        ('tau', 'tau'),  # Mathematical constant tau (2*pi)
        ('x', 'x'),  # Variable reference to x
        ('-5', '-5'),  # Negative integer literal 5
        ('+7', '+7'),  # Positive integer literal 7
        ('a + b', 'a + b'),  # Addition of variables a and b
        ('x - y', 'x - y'),  # Subtraction of y from x
        ('p * q', 'p * q'),  # Multiplication of variables p and q
        ('m / n', 'm / n'),  # Division of m by n
        ('i % j', 'i % j'),  # Modulo operation of i by j
        ('2 ** 3', '2 ** 3'),  # 2 raised to the power of 3
        ('a << 2', 'a << 2'),  # Left bit shift of a by 2 bits
        ('b >> 1', 'b >> 1'),  # Right bit shift of b by 1 bit
        ('x & y', 'x & y'),  # Bitwise AND of x and y
        ('p | q', 'p | q'),  # Bitwise OR of p and q
        ('m ^ n', 'm ^ n'),  # Bitwise XOR of m and n
        ('sin(x)', 'sin(x)'),  # Sine of x
        ('cos(theta)', 'cos(theta)'),  # Cosine of theta
        ('sqrt(2)', 'sqrt(2)'),  # Square root of 2
        ('log(x)', 'log(x)'),  # Natural logarithm of x
        ('abs(-7)', 'abs(-7)'),  # Absolute value of -7
        ('(a + b)', 'a + b'),  # Parenthesized addition of a and b
        ('(x * y) + z', 'x * y + z'),  # Addition of the product of x and y with z
        ('(x > y) ? a : b', '(x > y) ? a : b'),  # If x is greater than y, return a, otherwise return b
        ('(flag == 0x2) ? 1 : 0', '(flag == 2) ? 1 : 0'),  # If flag equals 0x2, return 1, otherwise return 0
        ('sin(x) + cos(y)', 'sin(x) + cos(y)'),  # Addition of sine of x and cosine of y
        ('(a + b) * (c - d)', '(a + b) * (c - d)'),  # Product of the sum of a and b with the difference of c and d
        ('log(x ** 2 + 1)', 'log(x ** 2 + 1)'),  # Natural logarithm of x squared plus 1
        ('(a & b) | (c & d)', 'a & b | c & d'),  # Bitwise OR of (a AND b) with (c AND d)
        ('sqrt(x * x + y * y)', 'sqrt(x * x + y * y)'),
        # Square root of the sum of squares of x and y (Euclidean distance)
        ('abs(x) + abs(y)', 'abs(x) + abs(y)'),  # Sum of absolute values of x and y (Manhattan distance)
        ('sin(2 * pi * f * t + phi)', 'sin(2 * pi * f * t + phi)'),  # Sine wave with frequency f, time t, and phase phi
        ('(x ** 2 + y ** 2 <= r ** 2) ? 1 : 0', '(x ** 2 + y ** 2 <= r ** 2) ? 1 : 0'),
        # Check if point (x,y) is within circle of radius r
        ('log(abs(x) + sqrt(x ** 2 + 1))', 'log(abs(x) + sqrt(x ** 2 + 1))'),
        # Logarithm of a complex mathematical expression
        ('(a << 2) & (b >> 1) | (c ^ d)', 'a << 2 & b >> 1 | c ^ d'),
        # Complex bitwise operation combining shift, AND, OR, and XOR
        ('(sin(x) ** 2 + cos(x) ** 2) * (1 + tan(y) ** 2) / (1 + tanh(z) ** 2)',
         '(sin(x) ** 2 + cos(x) ** 2) * (1 + tan(y) ** 2) / (1 + tanh(z) ** 2)'),
        # Complex trigonometric identity expression
        ('(a + b) * (c - d) / ((e + f) * (g - h)) ** (i % j)', '(a + b) * (c - d) / ((e + f) * (g - h)) ** (i % j)'),
        # Complex arithmetic expression with multiple operations and groupings
        ('log(sqrt(x ** 2 + y ** 2)) + atan(2 * y)', 'log(sqrt(x ** 2 + y ** 2)) + atan(2 * y)'),
        # Logarithm of distance plus angle calculation
        ('(x > y) ? (a < b) ? p : q : (c < d) ? m : n', '(x > y) ? ((a < b) ? p : q) : ((c < d) ? m : n)'),
        # Nested conditional expression with multiple conditions
        ('sin(cos(tan(x))) + log(exp(sqrt(abs(y))))', 'sin(cos(tan(x))) + log(exp(sqrt(abs(y))))'),
        # Nested function calls with various mathematical functions
        ('((a & b) | (c ^ d)) << ((e + f) % 8)', '(a & b | c ^ d) << (e + f) % 8'),
        # Bitwise operations combined with arithmetic for shift amount
        ('(x ** 2 + y ** 2 + z ** 2) ** 0.5', '(x ** 2 + y ** 2 + z ** 2) ** 0.5'),
        # Calculation of 3D Euclidean distance using exponentiation
        ('(a > b && c < d) ? (e + f) * g : (h - i) / j', '(a > b && c < d) ? (e + f) * g : (h - i) / j'),
        # Conditional expression with logical AND in condition
        ('sin(2 * pi * f * t) * exp(-t / tau) + A * cos(omega * t + phi)',
         'sin(2 * pi * f * t) * exp(-t / tau) + A * cos(omega * t + phi)'),  # Damped sinusoidal oscillation with offset
        ('(((x & 0xFF) << 16) | ((y & 0xFF) << 8) | (z & 0xFF))', '(x & 255) << 16 | (y & 255) << 8 | z & 255'),
        # RGB color value packing using bitwise operations
    ])
    def test_num_expression_parse_to_model_str(self, expr_text, expected_str):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='num_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert expected_str == str(expr)

    @pytest.mark.parametrize(['expr_text', 'expected_str'], [
        ('true', 'True'),  # Boolean literal true
        ('false', 'False'),  # Boolean literal false
        ('True', 'True'),  # Boolean literal True (alternative syntax)
        ('False', 'False'),  # Boolean literal False (alternative syntax)
        ('x > y', 'x > y'),  # Check if x is greater than y
        ('a < b', 'a < b'),  # Check if a is less than b
        ('m >= n', 'm >= n'),  # Check if m is greater than or equal to n
        ('p <= q', 'p <= q'),  # Check if p is less than or equal to q
        ('x == y', 'x == y'),  # Check if x equals y
        ('a != b', 'a != b'),  # Check if a is not equal to b
        ('!(x > y)', '!(x > y)'),  # Logical NOT of the comparison x > y
        ('not (a == b)', '!(a == b)'),  # Logical NOT of the comparison a equals b (alternative syntax)
        ('(a > 0) && (b < 1)', 'a > 0 && b < 1'),  # Logical AND of a > 0 and b < 1
        ('(x == 0) || (y != 1)', 'x == 0 || y != 1'),  # Logical OR of x == 0 and y != 1
        ('(p > 0) and (q < 1)', 'p > 0 && q < 1'),  # Logical AND of p > 0 and q < 1 (alternative syntax)
        ('(m == 0) or (n != 1)', 'm == 0 || n != 1'),  # Logical OR of m == 0 and n != 1 (alternative syntax)
        ('(x > y)', 'x > y'),  # Parenthesized comparison of x and y
        ('!(a < b)', '!(a < b)'),  # Negation of the comparison a < b
        ('(x > y) ? (a < b) : (c < d)', '(x > y) ? a < b : c < d'),  # If x > y, check a < b, otherwise check c < d
        ('(x > 0) ? true : false', '(x > 0) ? True : False'),  # If x > 0, return true, otherwise return false
        ('x > 0 && y > 0', 'x > 0 && y > 0'),  # Check if both x and y are positive
        ('a < b || c < d', 'a < b || c < d'),  # Check if either a < b or c < d is true
        ('(x >= min) && (x <= max)', 'x >= min && x <= max'),  # Check if x is within range [min, max]
        ('!(a == b) && !(c == d)', '!(a == b) && !(c == d)'),  # Check if both a != b and c != d
        ('(temp > 100) || (pressure > 200)', 'temp > 100 || pressure > 200'),
        # Check if either temperature exceeds 100 or pressure exceeds 200
        ('x == y && y == z', 'x == y && y == z'),  # Check if all three values are equal
        ('(a < b && c < d) || (e < f && g < h)', 'a < b && c < d || e < f && g < h'),
        # Check if either both a < b and c < d, or both e < f and g < h
        ('(x > 0) ? (y > 0) : (z > 0)', '(x > 0) ? y > 0 : z > 0'),
        # If x is positive, check if y is positive, otherwise check if z is positive
        ('!(a < b || c < d) && (e < f)', '!(a < b || c < d) && e < f'),  # Check if both NOT(a < b OR c < d) and e < f
        ('(x == 0) || (y != 0 && z == 0)', 'x == 0 || y != 0 && z == 0'),  # Check if x is 0 OR (y is not 0 AND z is 0)
        ('(a > b && c > d) || (e > f && g > h) || (i > j && k > l)',
         'a > b && c > d || e > f && g > h || i > j && k > l'),
        # Complex condition with multiple AND and OR combinations
        ('!((x < y) && (z < w)) || (p == q && r != s)', '!(x < y && z < w) || p == q && r != s'),
        # Negation of a conjunction combined with another conjunction
        ('((a < b) ? c < d : e < f) && ((g < h) ? i < j : k < l)',
         '((a < b) ? c < d : e < f) && ((g < h) ? i < j : k < l)'),  # Logical AND of two conditional expressions
        ('(x == y) == (a == b) && (c != d) != (e != f)', 'x == y == (a == b) && c != d != (e != f)'),
        # Equality comparison of equality comparisons
        (
                '(a > 0 && b > 0) || (c > 0 && d > 0) ? (e > 0 || f > 0) && (g > 0 || h > 0) : (i > 0 && j > 0) || (k > 0 && l > 0)',
                'a > 0 && b > 0 || ((c > 0 && d > 0) ? (e > 0 || f > 0) && (g > 0 || h > 0) : i > 0 && j > 0 || k > 0 && l > 0)'),
        # Conditional expression with complex conditions
        ('!(a < b) && !(c < d) || !(e < f) && !(g < h)', '!(a < b) && !(c < d) || !(e < f) && !(g < h)'),
        # Complex expression with multiple negations and logical operators
        (
                '(x > 0 && y > 0 && z > 0) || (x < 0 && y < 0 && z < 0)',
                'x > 0 && y > 0 && z > 0 || x < 0 && y < 0 && z < 0'),
        # Check if all coordinates are positive or all are negative
        ('(a == 1 || a == 2 || a == 3) && (b == 1 || b == 2 || b == 3)',
         '(a == 1 || a == 2 || a == 3) && (b == 1 || b == 2 || b == 3)'),
        # Check if both a and b are one of the values 1, 2, or 3
        ('((x > y) ? x : y) > ((a > b) ? a : b)', '((x > y) ? x : y) > ((a > b) ? a : b)'),
        # Compare the maximum of x and y with the maximum of a and b
        ('!((a < b) ? c < d : e < f) && ((g < h) ? !(i < j) : !(k < l))',
         '!((a < b) ? c < d : e < f) && ((g < h) ? !(i < j) : !(k < l))'),
        # Complex expression with negations and conditional expressions
        ('(a == b && c == d) || (e == f && g == h) || (i == j && k == l) || (m == n && o == p)',
         'a == b && c == d || e == f && g == h || i == j && k == l || m == n && o == p'),
        # Multiple equality checks combined with AND and OR
        ('((a < b) && (c < d)) ? ((e < f) || (g < h)) : ((i < j) && (k < l)) || ((m < n) || (o < p))',
         '(a < b && c < d) ? e < f || g < h : i < j && k < l || (m < n || o < p)'),
        # Complex conditional with multiple comparisons
        ('(x >= min && x <= max) || (y >= min && y <= max) || (z >= min && z <= max)',
         'x >= min && x <= max || y >= min && y <= max || z >= min && z <= max'),
        # Check if any of x, y, or z is within range [min, max]
        ('!((a < b || c < d) && (e < f || g < h)) || !((i < j || k < l) && (m < n || o < p))',
         '!((a < b || c < d) && (e < f || g < h)) || !((i < j || k < l) && (m < n || o < p))'),
        # Complex expression with negations of conjunctions of disjunctions
        ('((a > 0 && b > 0) || (c > 0 && d > 0)) == ((e > 0 && f > 0) || (g > 0 && h > 0))',
         '(a > 0 && b > 0 || c > 0 && d > 0) == (e > 0 && f > 0 || g > 0 && h > 0)'),
        # Compare equality of two complex boolean expressions
    ])
    def test_cond_expression_parse_to_model_str(self, expr_text, expected_str):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='cond_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert expected_str == str(expr)

    @pytest.mark.parametrize(['expr_text', ], [
        ('42',),  # Integer literal 42
        ('3.14',),  # Floating point literal 3.14
        ('0x2A',),  # Hexadecimal integer literal 42
        ('pi',),  # Mathematical constant pi
        ('E',),  # Mathematical constant E (Euler's number)
        ('tau',),  # Mathematical constant tau (2*pi)
        ('x',),  # Variable reference to x
        ('-5',),  # Negative integer literal 5
        ('+7',),  # Positive integer literal 7
        ('a + b',),  # Addition of variables a and b
        ('x - y',),  # Subtraction of y from x
        ('p * q',),  # Multiplication of variables p and q
        ('m / n',),  # Division of m by n
        ('i % j',),  # Modulo operation of i by j
        ('2 ** 3',),  # 2 raised to the power of 3
        ('a << 2',),  # Left bit shift of a by 2 bits
        ('b >> 1',),  # Right bit shift of b by 1 bit
        ('x & y',),  # Bitwise AND of x and y
        ('p | q',),  # Bitwise OR of p and q
        ('m ^ n',),  # Bitwise XOR of m and n
        ('sin(x)',),  # Sine of x
        ('cos(theta)',),  # Cosine of theta
        ('sqrt(2)',),  # Square root of 2
        ('log(x)',),  # Natural logarithm of x
        ('abs(-7)',),  # Absolute value of -7
        ('(a + b)',),  # Parenthesized addition of a and b
        ('(x * y) + z',),  # Addition of the product of x and y with z
        ('(x > y) ? a : b',),  # If x is greater than y, return a, otherwise return b
        ('(flag == 0x2) ? 1 : 0',),  # If flag equals 0x2, return 1, otherwise return 0
        ('sin(x) + cos(y)',),  # Addition of sine of x and cosine of y
        ('(a + b) * (c - d)',),  # Product of the sum of a and b with the difference of c and d
        ('log(x ** 2 + 1)',),  # Natural logarithm of x squared plus 1
        ('(a & b) | (c & d)',),  # Bitwise OR of (a AND b) with (c AND d)
        ('sqrt(x * x + y * y)',),  # Square root of the sum of squares of x and y (Euclidean distance)
        ('abs(x) + abs(y)',),  # Sum of absolute values of x and y (Manhattan distance)
        ('sin(2 * pi * f * t + phi)',),  # Sine wave with frequency f, time t, and phase phi
        ('(x ** 2 + y ** 2 <= r ** 2) ? 1 : 0',),  # Check if point (x,y) is within circle of radius r
        ('log(abs(x) + sqrt(x ** 2 + 1))',),  # Logarithm of a complex mathematical expression
        ('(a << 2) & (b >> 1) | (c ^ d)',),  # Complex bitwise operation combining shift, AND, OR, and XOR
        ('(sin(x) ** 2 + cos(x) ** 2) * (1 + tan(y) ** 2) / (1 + tanh(z) ** 2)',),
        # Complex trigonometric identity expression
        ('(a + b) * (c - d) / ((e + f) * (g - h)) ** (i % j)',),
        # Complex arithmetic expression with multiple operations and groupings
        ('log(sqrt(x ** 2 + y ** 2)) + atan(2 * y)',),  # Logarithm of distance plus angle calculation
        ('(x > y) ? (a < b) ? p : q : (c < d) ? m : n',),  # Nested conditional expression with multiple conditions
        ('sin(cos(tan(x))) + log(exp(sqrt(abs(y))))',),  # Nested function calls with various mathematical functions
        ('((a & b) | (c ^ d)) << ((e + f) % 8)',),  # Bitwise operations combined with arithmetic for shift amount
        ('(x ** 2 + y ** 2 + z ** 2) ** 0.5',),  # Calculation of 3D Euclidean distance using exponentiation
        ('(a > b && c < d) ? (e + f) * g : (h - i) / j',),  # Conditional expression with logical AND in condition
        ('sin(2 * pi * f * t) * exp(-t / tau) + A * cos(omega * t + phi)',),
        # Damped sinusoidal oscillation with offset
        ('(((x & 0xFF) << 16) | ((y & 0xFF) << 8) | (z & 0xFF))',),  # RGB color value packing using bitwise operations
    ])
    def test_num_expression_parse_to_model_consistency(self, expr_text):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='num_expression')
        expr = parse_expr_node_to_expr(ast_node)
        ast_node_2 = parse_with_grammar_entry(str(expr.to_ast_node()), entry_name='num_expression')
        expr2 = parse_expr_node_to_expr(ast_node_2)
        assert pytest.approx(expr) == expr2

    @pytest.mark.parametrize(['expr_text', ], [
        ('true',),  # Boolean literal true
        ('false',),  # Boolean literal false
        ('True',),  # Boolean literal True (alternative syntax)
        ('False',),  # Boolean literal False (alternative syntax)
        ('x > y',),  # Check if x is greater than y
        ('a < b',),  # Check if a is less than b
        ('m >= n',),  # Check if m is greater than or equal to n
        ('p <= q',),  # Check if p is less than or equal to q
        ('x == y',),  # Check if x equals y
        ('a != b',),  # Check if a is not equal to b
        ('!(x > y)',),  # Logical NOT of the comparison x > y
        ('not (a == b)',),  # Logical NOT of the comparison a equals b (alternative syntax)
        ('(a > 0) && (b < 1)',),  # Logical AND of a > 0 and b < 1
        ('(x == 0) || (y != 1)',),  # Logical OR of x == 0 and y != 1
        ('(p > 0) and (q < 1)',),  # Logical AND of p > 0 and q < 1 (alternative syntax)
        ('(m == 0) or (n != 1)',),  # Logical OR of m == 0 and n != 1 (alternative syntax)
        ('(x > y)',),  # Parenthesized comparison of x and y
        ('!(a < b)',),  # Negation of the comparison a < b
        ('(x > y) ? (a < b) : (c < d)',),  # If x > y, check a < b, otherwise check c < d
        ('(x > 0) ? true : false',),  # If x > 0, return true, otherwise return false
        ('x > 0 && y > 0',),  # Check if both x and y are positive
        ('a < b || c < d',),  # Check if either a < b or c < d is true
        ('(x >= min) && (x <= max)',),  # Check if x is within range [min, max]
        ('!(a == b) && !(c == d)',),  # Check if both a != b and c != d
        ('(temp > 100) || (pressure > 200)',),  # Check if either temperature exceeds 100 or pressure exceeds 200
        ('x == y && y == z',),  # Check if all three values are equal
        ('(a < b && c < d) || (e < f && g < h)',),  # Check if either both a < b and c < d, or both e < f and g < h
        ('(x > 0) ? (y > 0) : (z > 0)',),  # If x is positive, check if y is positive, otherwise check if z is positive
        ('!(a < b || c < d) && (e < f)',),  # Check if both NOT(a < b OR c < d) and e < f
        ('(x == 0) || (y != 0 && z == 0)',),  # Check if x is 0 OR (y is not 0 AND z is 0)
        ('(a > b && c > d) || (e > f && g > h) || (i > j && k > l)',),
        # Complex condition with multiple AND and OR combinations
        ('!((x < y) && (z < w)) || (p == q && r != s)',),  # Negation of a conjunction combined with another conjunction
        ('((a < b) ? c < d : e < f) && ((g < h) ? i < j : k < l)',),  # Logical AND of two conditional expressions
        ('(x == y) == (a == b) && (c != d) != (e != f)',),  # Equality comparison of equality comparisons
        (
                '(a > 0 && b > 0) || (c > 0 && d > 0) ? (e > 0 || f > 0) && (g > 0 || h > 0) : (i > 0 && j > 0) || (k > 0 && l > 0)',),
        # Conditional expression with complex conditions
        ('!(a < b) && !(c < d) || !(e < f) && !(g < h)',),
        # Complex expression with multiple negations and logical operators
        ('(x > 0 && y > 0 && z > 0) || (x < 0 && y < 0 && z < 0)',),
        # Check if all coordinates are positive or all are negative
        ('(a == 1 || a == 2 || a == 3) && (b == 1 || b == 2 || b == 3)',),
        # Check if both a and b are one of the values 1, 2, or 3
        ('((x > y) ? x : y) > ((a > b) ? a : b)',),  # Compare the maximum of x and y with the maximum of a and b
        ('!((a < b) ? c < d : e < f) && ((g < h) ? !(i < j) : !(k < l))',),
        # Complex expression with negations and conditional expressions
        ('(a == b && c == d) || (e == f && g == h) || (i == j && k == l) || (m == n && o == p)',),
        # Multiple equality checks combined with AND and OR
        ('((a < b) && (c < d)) ? ((e < f) || (g < h)) : ((i < j) && (k < l)) || ((m < n) || (o < p))',),
        # Complex conditional with multiple comparisons
        ('(x >= min && x <= max) || (y >= min && y <= max) || (z >= min && z <= max)',),
        # Check if any of x, y, or z is within range [min, max]
        ('!((a < b || c < d) && (e < f || g < h)) || !((i < j || k < l) && (m < n || o < p))',),
        # Complex expression with negations of conjunctions of disjunctions
        ('((a > 0 && b > 0) || (c > 0 && d > 0)) == ((e > 0 && f > 0) || (g > 0 && h > 0))',),
        # Compare equality of two complex boolean expressions
    ])
    def test_cond_expression_parse_to_model_consistency(self, expr_text):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='cond_expression')
        expr = parse_expr_node_to_expr(ast_node)
        ast_node_2 = parse_with_grammar_entry(str(expr.to_ast_node()), entry_name='cond_expression')
        expr2 = parse_expr_node_to_expr(ast_node_2)
        assert pytest.approx(expr) == expr2

    @pytest.mark.parametrize(['expr_text', 'expected_variables'], [
        ('42', []),  # Integer literal 42
        ('3.14', []),  # Floating point literal 3.14
        ('0x2A', []),  # Hexadecimal integer literal 42
        ('pi', []),  # Mathematical constant pi
        ('E', []),  # Mathematical constant E (Euler's number)
        ('tau', []),  # Mathematical constant tau (2*pi)
        ('x', [Variable(name='x')]),  # Variable reference to x
        ('-5', []),  # Negative integer literal 5
        ('+7', []),  # Positive integer literal 7
        ('a + b', [Variable(name='a'), Variable(name='b')]),  # Addition of variables a and b
        ('x - y', [Variable(name='x'), Variable(name='y')]),  # Subtraction of y from x
        ('p * q', [Variable(name='p'), Variable(name='q')]),  # Multiplication of variables p and q
        ('m / n', [Variable(name='m'), Variable(name='n')]),  # Division of m by n
        ('i % j', [Variable(name='i'), Variable(name='j')]),  # Modulo operation of i by j
        ('2 ** 3', []),  # 2 raised to the power of 3
        ('a << 2', [Variable(name='a')]),  # Left bit shift of a by 2 bits
        ('b >> 1', [Variable(name='b')]),  # Right bit shift of b by 1 bit
        ('x & y', [Variable(name='x'), Variable(name='y')]),  # Bitwise AND of x and y
        ('p | q', [Variable(name='p'), Variable(name='q')]),  # Bitwise OR of p and q
        ('m ^ n', [Variable(name='m'), Variable(name='n')]),  # Bitwise XOR of m and n
        ('sin(x)', [Variable(name='x')]),  # Sine of x
        ('cos(theta)', [Variable(name='theta')]),  # Cosine of theta
        ('sqrt(2)', []),  # Square root of 2
        ('log(x)', [Variable(name='x')]),  # Natural logarithm of x
        ('abs(-7)', []),  # Absolute value of -7
        ('(a + b)', [Variable(name='a'), Variable(name='b')]),  # Parenthesized addition of a and b
        ('(x * y) + z', [Variable(name='x'), Variable(name='y'), Variable(name='z')]),
        # Addition of the product of x and y with z
        ('(x > y) ? a : b', [Variable(name='x'), Variable(name='y'), Variable(name='a'), Variable(name='b')]),
        # If x is greater than y, return a, otherwise return b
        ('(flag == 0x2) ? 1 : 0', [Variable(name='flag')]),  # If flag equals 0x2, return 1, otherwise return 0
        ('sin(x) + cos(y)', [Variable(name='x'), Variable(name='y')]),  # Addition of sine of x and cosine of y
        ('(a + b) * (c - d)', [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d')]),
        # Product of the sum of a and b with the difference of c and d
        ('log(x ** 2 + 1)', [Variable(name='x')]),  # Natural logarithm of x squared plus 1
        ('(a & b) | (c & d)', [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d')]),
        # Bitwise OR of (a AND b) with (c AND d)
        ('sqrt(x * x + y * y)', [Variable(name='x'), Variable(name='y')]),
        # Square root of the sum of squares of x and y (Euclidean distance)
        ('abs(x) + abs(y)', [Variable(name='x'), Variable(name='y')]),
        # Sum of absolute values of x and y (Manhattan distance)
        ('sin(2 * pi * f * t + phi)', [Variable(name='f'), Variable(name='t'), Variable(name='phi')]),
        # Sine wave with frequency f, time t, and phase phi
        ('(x ** 2 + y ** 2 <= r ** 2) ? 1 : 0', [Variable(name='x'), Variable(name='y'), Variable(name='r')]),
        # Check if point (x,y) is within circle of radius r
        ('log(abs(x) + sqrt(x ** 2 + 1))', [Variable(name='x')]),  # Logarithm of a complex mathematical expression
        ('(a << 2) & (b >> 1) | (c ^ d)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d')]),
        # Complex bitwise operation combining shift, AND, OR, and XOR
        ('(sin(x) ** 2 + cos(x) ** 2) * (1 + tan(y) ** 2) / (1 + tanh(z) ** 2)',
         [Variable(name='x'), Variable(name='y'), Variable(name='z')]),  # Complex trigonometric identity expression
        ('(a + b) * (c - d) / ((e + f) * (g - h)) ** (i % j)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j')]),
        # Complex arithmetic expression with multiple operations and groupings
        ('log(sqrt(x ** 2 + y ** 2)) + atan(2 * y)', [Variable(name='x'), Variable(name='y')]),
        # Logarithm of distance plus angle calculation
        ('(x > y) ? (a < b) ? p : q : (c < d) ? m : n',
         [Variable(name='x'), Variable(name='y'), Variable(name='a'), Variable(name='b'), Variable(name='p'),
          Variable(name='q'), Variable(name='c'), Variable(name='d'), Variable(name='m'), Variable(name='n')]),
        # Nested conditional expression with multiple conditions
        ('sin(cos(tan(x))) + log(exp(sqrt(abs(y))))', [Variable(name='x'), Variable(name='y')]),
        # Nested function calls with various mathematical functions
        ('((a & b) | (c ^ d)) << ((e + f) % 8)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f')]),  # Bitwise operations combined with arithmetic for shift amount
        ('(x ** 2 + y ** 2 + z ** 2) ** 0.5', [Variable(name='x'), Variable(name='y'), Variable(name='z')]),
        # Calculation of 3D Euclidean distance using exponentiation
        ('(a > b && c < d) ? (e + f) * g : (h - i) / j',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j')]),
        # Conditional expression with logical AND in condition
        ('sin(2 * pi * f * t) * exp(-t / tau) + A * cos(omega * t + phi)',
         [Variable(name='f'), Variable(name='t'), Variable(name='A'), Variable(name='omega'), Variable(name='phi')]),
        # Damped sinusoidal oscillation with offset
        ('(((x & 0xFF) << 16) | ((y & 0xFF) << 8) | (z & 0xFF))',
         [Variable(name='x'), Variable(name='y'), Variable(name='z')]),
        # RGB color value packing using bitwise operations
    ])
    def test_num_expression_parse_to_model_list_variables(self, expr_text, expected_variables):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='num_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert expected_variables == expr.list_variables()

    @pytest.mark.parametrize(['expr_text', 'expected_variables'], [
        ('true', []),  # Boolean literal true
        ('false', []),  # Boolean literal false
        ('True', []),  # Boolean literal True (alternative syntax)
        ('False', []),  # Boolean literal False (alternative syntax)
        ('x > y', [Variable(name='x'), Variable(name='y')]),  # Check if x is greater than y
        ('a < b', [Variable(name='a'), Variable(name='b')]),  # Check if a is less than b
        ('m >= n', [Variable(name='m'), Variable(name='n')]),  # Check if m is greater than or equal to n
        ('p <= q', [Variable(name='p'), Variable(name='q')]),  # Check if p is less than or equal to q
        ('x == y', [Variable(name='x'), Variable(name='y')]),  # Check if x equals y
        ('a != b', [Variable(name='a'), Variable(name='b')]),  # Check if a is not equal to b
        ('!(x > y)', [Variable(name='x'), Variable(name='y')]),  # Logical NOT of the comparison x > y
        ('not (a == b)', [Variable(name='a'), Variable(name='b')]),
        # Logical NOT of the comparison a equals b (alternative syntax)
        ('(a > 0) && (b < 1)', [Variable(name='a'), Variable(name='b')]),  # Logical AND of a > 0 and b < 1
        ('(x == 0) || (y != 1)', [Variable(name='x'), Variable(name='y')]),  # Logical OR of x == 0 and y != 1
        ('(p > 0) and (q < 1)', [Variable(name='p'), Variable(name='q')]),
        # Logical AND of p > 0 and q < 1 (alternative syntax)
        ('(m == 0) or (n != 1)', [Variable(name='m'), Variable(name='n')]),
        # Logical OR of m == 0 and n != 1 (alternative syntax)
        ('(x > y)', [Variable(name='x'), Variable(name='y')]),  # Parenthesized comparison of x and y
        ('!(a < b)', [Variable(name='a'), Variable(name='b')]),  # Negation of the comparison a < b
        ('(x > y) ? (a < b) : (c < d)',
         [Variable(name='x'), Variable(name='y'), Variable(name='a'), Variable(name='b'), Variable(name='c'),
          Variable(name='d')]),  # If x > y, check a < b, otherwise check c < d
        ('(x > 0) ? true : false', [Variable(name='x')]),  # If x > 0, return true, otherwise return false
        ('x > 0 && y > 0', [Variable(name='x'), Variable(name='y')]),  # Check if both x and y are positive
        ('a < b || c < d', [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d')]),
        # Check if either a < b or c < d is true
        ('(x >= min) && (x <= max)', [Variable(name='x'), Variable(name='min'), Variable(name='max')]),
        # Check if x is within range [min, max]
        ('!(a == b) && !(c == d)', [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d')]),
        # Check if both a != b and c != d
        ('(temp > 100) || (pressure > 200)', [Variable(name='temp'), Variable(name='pressure')]),
        # Check if either temperature exceeds 100 or pressure exceeds 200
        ('x == y && y == z', [Variable(name='x'), Variable(name='y'), Variable(name='z')]),
        # Check if all three values are equal
        ('(a < b && c < d) || (e < f && g < h)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h')]),
        # Check if either both a < b and c < d, or both e < f and g < h
        ('(x > 0) ? (y > 0) : (z > 0)', [Variable(name='x'), Variable(name='y'), Variable(name='z')]),
        # If x is positive, check if y is positive, otherwise check if z is positive
        ('!(a < b || c < d) && (e < f)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f')]),  # Check if both NOT(a < b OR c < d) and e < f
        ('(x == 0) || (y != 0 && z == 0)', [Variable(name='x'), Variable(name='y'), Variable(name='z')]),
        # Check if x is 0 OR (y is not 0 AND z is 0)
        ('(a > b && c > d) || (e > f && g > h) || (i > j && k > l)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j'),
          Variable(name='k'), Variable(name='l')]),  # Complex condition with multiple AND and OR combinations
        ('!((x < y) && (z < w)) || (p == q && r != s)',
         [Variable(name='x'), Variable(name='y'), Variable(name='z'), Variable(name='w'), Variable(name='p'),
          Variable(name='q'), Variable(name='r'), Variable(name='s')]),
        # Negation of a conjunction combined with another conjunction
        ('((a < b) ? c < d : e < f) && ((g < h) ? i < j : k < l)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j'),
          Variable(name='k'), Variable(name='l')]),  # Logical AND of two conditional expressions
        ('(x == y) == (a == b) && (c != d) != (e != f)',
         [Variable(name='x'), Variable(name='y'), Variable(name='a'), Variable(name='b'), Variable(name='c'),
          Variable(name='d'), Variable(name='e'), Variable(name='f')]),  # Equality comparison of equality comparisons
        (
                '(a > 0 && b > 0) || (c > 0 && d > 0) ? (e > 0 || f > 0) && (g > 0 || h > 0) : (i > 0 && j > 0) || (k > 0 && l > 0)',
                [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
                 Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j'),
                 Variable(name='k'), Variable(name='l')]),  # Conditional expression with complex conditions
        ('!(a < b) && !(c < d) || !(e < f) && !(g < h)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h')]),
        # Complex expression with multiple negations and logical operators
        ('(x > 0 && y > 0 && z > 0) || (x < 0 && y < 0 && z < 0)',
         [Variable(name='x'), Variable(name='y'), Variable(name='z')]),
        # Check if all coordinates are positive or all are negative
        ('(a == 1 || a == 2 || a == 3) && (b == 1 || b == 2 || b == 3)', [Variable(name='a'), Variable(name='b')]),
        # Check if both a and b are one of the values 1, 2, or 3
        ('((x > y) ? x : y) > ((a > b) ? a : b)',
         [Variable(name='x'), Variable(name='y'), Variable(name='a'), Variable(name='b')]),
        # Compare the maximum of x and y with the maximum of a and b
        ('!((a < b) ? c < d : e < f) && ((g < h) ? !(i < j) : !(k < l))',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j'),
          Variable(name='k'), Variable(name='l')]),  # Complex expression with negations and conditional expressions
        ('(a == b && c == d) || (e == f && g == h) || (i == j && k == l) || (m == n && o == p)',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j'),
          Variable(name='k'), Variable(name='l'), Variable(name='m'), Variable(name='n'), Variable(name='o'),
          Variable(name='p')]),  # Multiple equality checks combined with AND and OR
        ('((a < b) && (c < d)) ? ((e < f) || (g < h)) : ((i < j) && (k < l)) || ((m < n) || (o < p))',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j'),
          Variable(name='k'), Variable(name='l'), Variable(name='m'), Variable(name='n'), Variable(name='o'),
          Variable(name='p')]),  # Complex conditional with multiple comparisons
        ('(x >= min && x <= max) || (y >= min && y <= max) || (z >= min && z <= max)',
         [Variable(name='x'), Variable(name='min'), Variable(name='max'), Variable(name='y'), Variable(name='z')]),
        # Check if any of x, y, or z is within range [min, max]
        ('!((a < b || c < d) && (e < f || g < h)) || !((i < j || k < l) && (m < n || o < p))',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h'), Variable(name='i'), Variable(name='j'),
          Variable(name='k'), Variable(name='l'), Variable(name='m'), Variable(name='n'), Variable(name='o'),
          Variable(name='p')]),  # Complex expression with negations of conjunctions of disjunctions
        ('((a > 0 && b > 0) || (c > 0 && d > 0)) == ((e > 0 && f > 0) || (g > 0 && h > 0))',
         [Variable(name='a'), Variable(name='b'), Variable(name='c'), Variable(name='d'), Variable(name='e'),
          Variable(name='f'), Variable(name='g'), Variable(name='h')]),
        # Compare equality of two complex boolean expressions
    ])
    def test_cond_expression_parse_to_model_list_variables(self, expr_text, expected_variables):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='cond_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert expected_variables == expr.list_variables()

    @pytest.mark.parametrize(['expr_text', 'expected_value'], [
        ('42', 42),  # Integer literal 42
        ('3.14', 3.14),  # Floating-point literal 3.14
        ('0x2A', 42),  # Hexadecimal integer literal 0x2A (42 in decimal)
        ('pi', 3.141592653589793),  # Mathematical constant pi
        ('E', 2.718281828459045),  # Mathematical constant E (Euler's number)
        ('-5', -5),  # Negative integer literal -5
        ('+3.14', 3.14),  # Positive floating-point literal 3.14
        ('2 + 3', 5),  # Addition of integers 2 and 3
        ('7 - 4', 3),  # Subtraction of 4 from 7
        ('6 * 8', 48),  # Multiplication of 6 and 8
        ('15 / 3', 5.0),  # Division of 15 by 3
        ('10 % 3', 1),  # Modulo operation: remainder of 10 divided by 3
        ('5 & 3', 1),  # Bitwise AND of 5 and 3
        ('5 | 3', 7),  # Bitwise OR of 5 and 3
        ('5 ^ 3', 6),  # Bitwise XOR of 5 and 3
        ('5 << 2', 20),  # Left shift of 5 by 2 bits
        ('20 >> 2', 5),  # Right shift of 20 by 2 bits
        ('2 ** 3', 8),  # 2 raised to the power of 3
        ('3 ** 2 ** 2', 81),  # 3 raised to the power of (2 raised to the power of 2)
        ('sin(pi/2)', 1.0),  # Sine function applied to pi/2
        ('cos(0)', 1.0),  # Cosine function applied to 0
        ('sqrt(16)', 4.0),  # Square root of 16
        ('log10(100)', 2.0),  # Base-10 logarithm of 100
        ('(5 > 3) ? 10 : 20', 10),  # If 5 > 3 then 10 else 20
        ('(2 == 2) ? 5 : 6', 5),  # If 2 equals 2 then 5 else 6
        ('(3 + 4) * (7 - 2)', 35),  # Product of (3 + 4) and (7 - 2)
        ('sin(pi/4) ** 2 + cos(pi/4) ** 2', 1.0),  # Sum of squared sine and cosine of pi/4
        ('(5 > 3 && 2 < 4) ? sqrt(16) : cbrt(27)', 4.0),  # If both 5 > 3 and 2 < 4 then sqrt(16) else cbrt(27)
        ('log(E ** 2) * (3 + 4 * 5) / (2 ** 3 - 1)', 6.571428571428571),
        # Complex expression combining logarithm, exponentiation, and arithmetic operations
        ('abs(-5) + ceil(3.2) + floor(3.8) + round(3.5)', 16),
        # Sum of absolute value, ceiling, floor, and round functions
    ])
    def test_num_expression_parse_to_model_call_without_variables(self, expr_text, expected_value):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='num_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert pytest.approx(expected_value) == expr()

    @pytest.mark.parametrize(['expr_text', 'expected_value'], [
        ('true', True),  # Boolean literal true
        ('false', False),  # Boolean literal false
        ('TRUE', True),  # Boolean literal TRUE (alternative syntax)
        ('!true', False),  # Logical NOT of true
        ('not false', True),  # Logical NOT of false (alternative syntax)
        ('5 > 3', True),  # Greater than comparison: 5 > 3
        ('10 <= 10', True),  # Less than or equal comparison: 10 <= 10
        ('7 == 7', True),  # Equality comparison: 7 equals 7
        ('4 != 5', True),  # Inequality comparison: 4 not equal to 5
        ('(5 > 3) == (6 > 4)', True),  # Equality comparison between two conditions
        ('(2 < 1) != (3 < 2)', False),  # Inequality comparison between two conditions
        ('true && true', True),  # Logical AND of two true values
        ('false || true', True),  # Logical OR of false and true
        ('true and false', False),  # Logical AND of true and false (alternative syntax)
        ('false or false', False),  # Logical OR of two false values (alternative syntax)
        ('(5 > 3) && (2 < 4)', True),  # Logical AND of two comparison expressions
        ('!(5 < 3) || (7 >= 10)', True),  # Logical OR of negated comparison and another comparison
        ('(true) ? false : true', False),  # If true then false else true
        ('(5 > 3) ? (2 == 2) : (1 != 1)', True),  # If 5 > 3 then check if 2 equals 2 else check if 1 not equals 1
        ('(3 * 4 > 10) && (20 / 5 == 4)', True),  # Logical AND of two complex comparisons
        ('(sin(pi/2) > 0.9) || (cos(0) < 0.5)', True),  # Logical OR of trigonometric function comparisons
        ('((5 > 3) && (2 < 4)) || ((1 == 1) && (0 != 1))', True),  # Nested logical operations with comparisons
        ('(true && false) || (true && true)', True),  # Combination of logical AND and OR operations
        ('(((5 > 3) && (2 < 4)) || ((1 == 1) && (0 != 1))) && (true || false)', True),
        # Multi-level nesting of logical operations
        ('!(5 < 3) && !(2 > 4) && (3 == 3)', True),  # Multiple negations combined with logical AND
        ('sqrt(16) == 4 && log10(1000) == 3', True),  # Comparisons involving mathematical functions
        ('(sin(0) ** 2 + cos(0) ** 2) == 1', True),  # Trigonometric identity comparison
        ('((5 * 3 > 10) && (20 / 5 == 4)) || ((sin(pi/2) > 0.9) && (cos(0) > 0.5))', True),
        # Complex combination of arithmetic, comparison, and trigonometric functions
        ('(2 ** 3 == 8) ? ((4 * 5 > 15) && (30 / 6 <= 5)) : ((sqrt(16) == 4) || (log10(100) != 2))', True),
        # Complex conditional expression with nested comparisons
        ('!((sin(pi/4) ** 2 + cos(pi/4) ** 2 != 1) || (E ** log(1) != 1)) && (pi > 3)', True),
        # Complex expression with mathematical functions, constants, and logical operations
        ('( 2 > 3) ? ( 1 == 2) : (3 == 3)', True),  # Negative condition test
    ])
    def test_cond_expression_parse_to_model_call_without_variables(self, expr_text, expected_value):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='cond_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert pytest.approx(expected_value) == expr()

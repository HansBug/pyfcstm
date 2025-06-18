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

    @pytest.mark.parametrize(['expr_text', 'a', 'b', 'c', 'expected_value'], [
        ('a + b - c', 74, -15, -66, 125),  # Sum of a and b, subtracted by c
        ('a * b / c', 58, -86, 67, -74.44776119402985),  # Product of a and b, divided by c
        ('a % b + c', -92, -5, 66, 64),  # Remainder of a divided by b, plus c
        ('a ** b + c', -57, -87, 97, 97.0),  # a raised to the power of b, plus c
        ('(a + b) * c', -3, -74, -31, 2387),  # Sum of a and b, multiplied by c
        ('a * b ** c', 21, 61, 37, 23956490147809644945650599739257499248964335447281388226410457516241),
        # a multiplied by b raised to the power of c
        ('sin(a) + cos(b) - tan(c)', -47, 10, 94, -0.7096665550603087),
        # Sum of sine of a and cosine of b, minus tangent of c
        ('a << b | c', -42, 6, 59, -2629),  # a left-shifted by b bits, bitwise OR with c
        ('a & b ^ c', 34, 29, 87, 87),  # Bitwise AND of a and b, XOR with c
        ('(a + b) % (c + 1)', 73, -76, -80, -3),  # Remainder when sum of a and b is divided by c plus 1
        ('sqrt(a**2 + b**2) - c', 35, 65, -81, 154.824115301167),  # Pythagorean calculation of a and b, minus c
        ('log(a) * exp(b) / log10(c)', 49, 47, 52, 5.854304377385308e+20),
        # Natural log of a times e raised to b, divided by log base 10 of c
        ('(a + b) ** (c % 3) + sin(a * b)', 21, 14, -8, 34.03389001073747),
        # Sum of a and b raised to power of c modulo 3, plus sine of a times b
        ('abs(a - b) * sign(c) + floor(a/c)', 66, 44, 34, 23),
        # Absolute difference of a and b multiplied by sign of c, plus floor division of a by c
        ('(a << 2) & (b >> 1) | (c ^ a)', -11, -35, 51, -58),
        # a left-shifted by 2 bits AND b right-shifted by 1 bit, OR with XOR of c and a
        ('(a > b) ? c : a + b', -33, -33, -7, -66),  # c if a is greater than b, otherwise a plus b
        ('(a == b) ? a * c : b - c', -57, 5, 92, -87),  # a times c if a equals b, otherwise b minus c
        ('(a <= c && b >= c) ? a + b + c : a * b * c', 24, -72, 38, -65664),
        # Sum of a, b, and c if a is less than or equal to c AND b is greater than or equal to c, otherwise product of a, b, and c
        ('cos(a) + sin(b) * tan(c % pi)', 40, -84, -99, -19.064541814849775),
        # Cosine of a plus sine of b multiplied by tangent of c modulo pi
        ('log(abs(a - b)) + sqrt(c ** 2)', 75, 7, 86, 90.21950770517611),
        # Natural log of absolute difference between a and b, plus square root of c squared
        ('((a + b) % c) ** (a & b) + sin(a * b / c)', 14, -32, -35, 1.231509825101539),
        # Remainder of a plus b divided by c, raised to power of a AND b, plus sine of a times b divided by c
        ('(a > b) ? sqrt(a**2 - b**2) : cbrt(c**3 - a**3)', -77, -44, 20, 77.44716482057184),
        # Square root of difference of squares if a > b, otherwise cube root of difference of cubes
        ('log2(a) * (b << 3) + (c & 0xFF) - round(sin(a * pi))', 67, 9, 17, 453.7584217129596),
        # Log base 2 of a times b left-shifted by 3, plus c AND 0xFF, minus rounded sine of a times pi
        ('(a ** b % c) * (a & b | c) + abs(a - b + c)', -14, 50, -93, 2159),
        # a raised to b modulo c, multiplied by bitwise operations, plus absolute value of a minus b plus c
        ('(a > b && b < c) ? (a + b) * c : (a - b) / c', -83, -54, 9, -3.2222222222222223),
        # Product of sum of a and b with c if a > b AND b < c, otherwise quotient of a minus b divided by c
        ('sin(a) * cos(b) * tan(c) + sqrt(a**2 + b**2 + c**2)', -83, -63, -82, 132.91202185631857),
        # Product of trigonometric functions plus 3D distance calculation
        ('((a & b) | (b ^ c)) ** (a % 3) + log(abs(a - b) + 1)', -93, -17, -75, 5.343805421853684),
        # Complex bitwise operation raised to power of a modulo 3, plus log of absolute difference plus 1
        ('(a > b) ? (b > c) ? a + b : b + c : (a > c) ? a + c : b * c', -3, -84, -11, -95),
        # Nested conditional expression with various arithmetic combinations
        ('floor(sqrt(a**2 + b**2)) * ceil(log(c + 1)) + round(sin(a * b * c))', 13, 72, 82, 365),
        # Floor of Pythagorean calculation times ceiling of log, plus rounded sine of product
        ('(a ** b % c) * ((a << 2) & (b >> 1)) + abs(sin(a) * cos(b) - tan(c))', -17, -71, -69, 0.41264222158717123),
        # Modular exponentiation times bitwise shift operations, plus absolute difference of trigonometric functions
    ])
    def test_num_expression_parse_to_model_call_with_variables(self, expr_text, a, b, c, expected_value):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='num_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert pytest.approx(expected_value) == expr(a=a, b=b, c=c)

    @pytest.mark.parametrize(['expr_text', 'a', 'b', 'c', 'expected_value'], [
        ('a > b', -38, -90, -6, True),  # a is greater than b
        ('a > b', 17, -42, -45, True),  # a is greater than b
        ('a > b', 21, -76, 93, True),  # a is greater than b
        ('a > b', -79, 24, -37, False),  # a is greater than b
        ('a > b', 30, 64, 94, False),  # a is greater than b
        ('a > b', -75, 88, -29, False),  # a is greater than b
        ('a == b', 58, 58, -68, True),  # a equals b
        ('a == b', 98, 98, 49, True),  # a equals b
        ('a == b', -7, -7, 62, True),  # a equals b
        ('a == b', -47, 47, 34, False),  # a equals b
        ('a == b', 24, -69, -52, False),  # a equals b
        ('a == b', 78, 12, 1, False),  # a equals b
        ('a != c', 6, 59, -18, True),  # a is not equal to c
        ('a != c', -94, 15, 60, True),  # a is not equal to c
        ('a != c', -4, -57, -5, True),  # a is not equal to c
        ('a != c', -22, -51, -22, False),  # a is not equal to c
        ('a != c', -79, 21, -79, False),  # a is not equal to c
        ('a != c', -9, 38, -9, False),  # a is not equal to c
        ('a >= b && b <= c', 86, -21, 88, True),  # a is greater than or equal to b AND b is less than or equal to c
        ('a >= b && b <= c', 36, 30, 94, True),  # a is greater than or equal to b AND b is less than or equal to c
        ('a >= b && b <= c', -49, -88, -58, True),  # a is greater than or equal to b AND b is less than or equal to c
        ('a >= b && b <= c', -38, 0, -5, False),  # a is greater than or equal to b AND b is less than or equal to c
        ('a >= b && b <= c', -59, 92, -20, False),  # a is greater than or equal to b AND b is less than or equal to c
        ('a >= b && b <= c', 20, 67, 9, False),  # a is greater than or equal to b AND b is less than or equal to c
        ('a < b || b > c', -5, -9, -92, True),  # a is less than b OR b is greater than c
        ('a < b || b > c', 26, 95, -39, True),  # a is less than b OR b is greater than c
        ('a < b || b > c', -29, 73, -74, True),  # a is less than b OR b is greater than c
        ('a < b || b > c', -49, -51, 79, False),  # a is less than b OR b is greater than c
        ('a < b || b > c', 67, -97, 12, False),  # a is less than b OR b is greater than c
        ('a < b || b > c', -28, -84, -24, False),  # a is less than b OR b is greater than c
        ('!(a == b) && c > 0', -99, -13, 51, True),  # a is not equal to b AND c is greater than 0
        ('!(a == b) && c > 0', 12, -32, 57, True),  # a is not equal to b AND c is greater than 0
        ('!(a == b) && c > 0', -86, 97, 72, True),  # a is not equal to b AND c is greater than 0
        ('!(a == b) && c > 0', 80, 80, -26, False),  # a is not equal to b AND c is greater than 0
        ('!(a == b) && c > 0', 47, 48, -20, False),  # a is not equal to b AND c is greater than 0
        ('!(a == b) && c > 0', 86, -38, -78, False),  # a is not equal to b AND c is greater than 0
        ('a > b && b > c && a > c', 27, -5, -25, True),
        # a is greater than b AND b is greater than c AND a is greater than c
        ('a > b && b > c && a > c', 78, -53, -70, True),
        # a is greater than b AND b is greater than c AND a is greater than c
        ('a > b && b > c && a > c', 20, 12, -79, True),
        # a is greater than b AND b is greater than c AND a is greater than c
        ('a > b && b > c && a > c', -66, 5, 73, False),
        # a is greater than b AND b is greater than c AND a is greater than c
        ('a > b && b > c && a > c', -36, 24, -75, False),
        # a is greater than b AND b is greater than c AND a is greater than c
        ('a > b && b > c && a > c', -81, -98, 36, False),
        # a is greater than b AND b is greater than c AND a is greater than c
        ('a == b || b == c || a == c', 7, 33, 7, True),  # a equals b OR b equals c OR a equals c
        ('a == b || b == c || a == c', 88, 88, -24, True),  # a equals b OR b equals c OR a equals c
        ('a == b || b == c || a == c', -77, -77, -4, True),  # a equals b OR b equals c OR a equals c
        ('a == b || b == c || a == c', 69, -90, -87, False),  # a equals b OR b equals c OR a equals c
        ('a == b || b == c || a == c', -39, -92, -24, False),  # a equals b OR b equals c OR a equals c
        ('a == b || b == c || a == c', -100, -17, 26, False),  # a equals b OR b equals c OR a equals c
        ('a >= 0 && b >= 0 && c >= 0', 68, 35, 56, True),  # a, b, and c are all non-negative
        ('a >= 0 && b >= 0 && c >= 0', 48, 23, 13, True),  # a, b, and c are all non-negative
        ('a >= 0 && b >= 0 && c >= 0', 97, 1, 68, True),  # a, b, and c are all non-negative
        ('a >= 0 && b >= 0 && c >= 0', 78, 17, -30, False),  # a, b, and c are all non-negative
        ('a >= 0 && b >= 0 && c >= 0', -49, -14, 88, False),  # a, b, and c are all non-negative
        ('a >= 0 && b >= 0 && c >= 0', -48, 81, -16, False),  # a, b, and c are all non-negative
        ('a < b + c && b < a + c && c < a + b', 68, 63, 82, True),
        # Triangle inequality: each side is less than sum of other two sides
        ('a < b + c && b < a + c && c < a + b', 88, 54, 60, True),
        # Triangle inequality: each side is less than sum of other two sides
        ('a < b + c && b < a + c && c < a + b', 29, 32, 41, True),
        # Triangle inequality: each side is less than sum of other two sides
        ('a < b + c && b < a + c && c < a + b', -65, 86, -55, False),
        # Triangle inequality: each side is less than sum of other two sides
        ('a < b + c && b < a + c && c < a + b', 33, -17, -61, False),
        # Triangle inequality: each side is less than sum of other two sides
        ('a < b + c && b < a + c && c < a + b', 96, -19, 4, False),
        # Triangle inequality: each side is less than sum of other two sides
        ('(a > b) ? (b > c) : (a > c)', 19, 54, 13, True),  # If a > b then check if b > c, otherwise check if a > c
        ('(a > b) ? (b > c) : (a > c)', 73, 57, 15, True),  # If a > b then check if b > c, otherwise check if a > c
        ('(a > b) ? (b > c) : (a > c)', -2, -84, -99, True),  # If a > b then check if b > c, otherwise check if a > c
        ('(a > b) ? (b > c) : (a > c)', -15, -67, -61, False),  # If a > b then check if b > c, otherwise check if a > c
        ('(a > b) ? (b > c) : (a > c)', 91, 1, 39, False),  # If a > b then check if b > c, otherwise check if a > c
        ('(a > b) ? (b > c) : (a > c)', -55, -47, 20, False),  # If a > b then check if b > c, otherwise check if a > c
        ('a**2 + b**2 == c**2', -66, 0, -66, True),  # Pythagorean theorem: a squared plus b squared equals c squared
        ('a**2 + b**2 == c**2', 60, 25, -65, True),  # Pythagorean theorem: a squared plus b squared equals c squared
        ('a**2 + b**2 == c**2', 80, 0, -80, True),  # Pythagorean theorem: a squared plus b squared equals c squared
        ('a**2 + b**2 == c**2', -27, -88, -68, False),  # Pythagorean theorem: a squared plus b squared equals c squared
        ('a**2 + b**2 == c**2', 12, 78, -33, False),  # Pythagorean theorem: a squared plus b squared equals c squared
        ('a**2 + b**2 == c**2', -72, -94, 98, False),  # Pythagorean theorem: a squared plus b squared equals c squared
        ('a % 2 == 0 && b % 2 == 0 && c % 2 == 0', -32, -48, -72, True),  # a, b, and c are all even numbers
        ('a % 2 == 0 && b % 2 == 0 && c % 2 == 0', -24, -56, 20, True),  # a, b, and c are all even numbers
        ('a % 2 == 0 && b % 2 == 0 && c % 2 == 0', 60, 90, 70, True),  # a, b, and c are all even numbers
        ('a % 2 == 0 && b % 2 == 0 && c % 2 == 0', 17, 52, -94, False),  # a, b, and c are all even numbers
        ('a % 2 == 0 && b % 2 == 0 && c % 2 == 0', 42, -11, -5, False),  # a, b, and c are all even numbers
        ('a % 2 == 0 && b % 2 == 0 && c % 2 == 0', 89, 31, -57, False),  # a, b, and c are all even numbers
        ('(a > 0) ? b > 0 && c > 0 : b < 0 && c < 0', 49, 32, 5, True),
        # If a is positive, check if b and c are positive, otherwise check if b and c are negative
        ('(a > 0) ? b > 0 && c > 0 : b < 0 && c < 0', 86, 46, 31, True),
        # If a is positive, check if b and c are positive, otherwise check if b and c are negative
        ('(a > 0) ? b > 0 && c > 0 : b < 0 && c < 0', 31, 81, 46, True),
        # If a is positive, check if b and c are positive, otherwise check if b and c are negative
        ('(a > 0) ? b > 0 && c > 0 : b < 0 && c < 0', -38, 92, -17, False),
        # If a is positive, check if b and c are positive, otherwise check if b and c are negative
        ('(a > 0) ? b > 0 && c > 0 : b < 0 && c < 0', -38, 22, -10, False),
        # If a is positive, check if b and c are positive, otherwise check if b and c are negative
        ('(a > 0) ? b > 0 && c > 0 : b < 0 && c < 0', -76, 87, -86, False),
        # If a is positive, check if b and c are positive, otherwise check if b and c are negative
        ('(a + b > c) && (a + c > b) && (b + c > a)', 52, 52, 85, True),
        # Sum of any two variables is greater than the third (triangle inequality)
        ('(a + b > c) && (a + c > b) && (b + c > a)', 45, 91, 71, True),
        # Sum of any two variables is greater than the third (triangle inequality)
        ('(a + b > c) && (a + c > b) && (b + c > a)', 100, 58, 43, True),
        # Sum of any two variables is greater than the third (triangle inequality)
        ('(a + b > c) && (a + c > b) && (b + c > a)', 64, 32, -85, False),
        # Sum of any two variables is greater than the third (triangle inequality)
        ('(a + b > c) && (a + c > b) && (b + c > a)', 64, -44, -19, False),
        # Sum of any two variables is greater than the third (triangle inequality)
        ('(a + b > c) && (a + c > b) && (b + c > a)', -27, -40, -60, False),
        # Sum of any two variables is greater than the third (triangle inequality)
        ('(a > b && b > c) || (a < b && b < c)', -18, -35, -79, True),
        # Variables are in strictly ascending or descending order
        ('(a > b && b > c) || (a < b && b < c)', 50, 55, 87, True),
        # Variables are in strictly ascending or descending order
        ('(a > b && b > c) || (a < b && b < c)', 91, -8, -73, True),
        # Variables are in strictly ascending or descending order
        ('(a > b && b > c) || (a < b && b < c)', -20, -78, 78, False),
        # Variables are in strictly ascending or descending order
        ('(a > b && b > c) || (a < b && b < c)', 4, -26, 100, False),
        # Variables are in strictly ascending or descending order
        ('(a > b && b > c) || (a < b && b < c)', 16, 94, -36, False),
        # Variables are in strictly ascending or descending order
        ('(a == b && b != c) || (a != b && b == c) || (a == c && c != b)', 53, -32, 53, True),
        # Exactly two of the three variables are equal
        ('(a == b && b != c) || (a != b && b == c) || (a == c && c != b)', 2, 2, -70, True),
        # Exactly two of the three variables are equal
        ('(a == b && b != c) || (a != b && b == c) || (a == c && c != b)', 88, 88, -43, True),
        # Exactly two of the three variables are equal
        ('(a == b && b != c) || (a != b && b == c) || (a == c && c != b)', -44, 94, 63, False),
        # Exactly two of the three variables are equal
        ('(a == b && b != c) || (a != b && b == c) || (a == c && c != b)', -85, 71, 30, False),
        # Exactly two of the three variables are equal
        ('(a == b && b != c) || (a != b && b == c) || (a == c && c != b)', 47, 56, -81, False),
        # Exactly two of the three variables are equal
        ('a**2 + b**2 > c**2 && a > 0 && b > 0 && c > 0', 35, 46, 26, True),
        # Forms an acute triangle (all sides positive and Pythagorean inequality)
        ('a**2 + b**2 > c**2 && a > 0 && b > 0 && c > 0', 22, 44, 30, True),
        # Forms an acute triangle (all sides positive and Pythagorean inequality)
        ('a**2 + b**2 > c**2 && a > 0 && b > 0 && c > 0', 83, 53, 68, True),
        # Forms an acute triangle (all sides positive and Pythagorean inequality)
        ('a**2 + b**2 > c**2 && a > 0 && b > 0 && c > 0', 9, -12, 28, False),
        # Forms an acute triangle (all sides positive and Pythagorean inequality)
        ('a**2 + b**2 > c**2 && a > 0 && b > 0 && c > 0', -18, -86, -52, False),
        # Forms an acute triangle (all sides positive and Pythagorean inequality)
        ('a**2 + b**2 > c**2 && a > 0 && b > 0 && c > 0', 11, -87, 71, False),
        # Forms an acute triangle (all sides positive and Pythagorean inequality)
        ('!(a < b) && !(b < c) && !(a < c)', 51, 34, -96, True),
        # None of the variables is less than any other (all are equal)
        ('!(a < b) && !(b < c) && !(a < c)', 20, -25, -69, True),
        # None of the variables is less than any other (all are equal)
        ('!(a < b) && !(b < c) && !(a < c)', 8, -53, -60, True),
        # None of the variables is less than any other (all are equal)
        ('!(a < b) && !(b < c) && !(a < c)', 52, -20, 38, False),
        # None of the variables is less than any other (all are equal)
        ('!(a < b) && !(b < c) && !(a < c)', -41, 69, -17, False),
        # None of the variables is less than any other (all are equal)
        ('!(a < b) && !(b < c) && !(a < c)', -90, 55, 70, False),
        # None of the variables is less than any other (all are equal)
        ('(a > 0 && b > 0 && c < 0) || (a > 0 && b < 0 && c > 0) || (a < 0 && b > 0 && c > 0)', 33, -5, 25, True),
        # Exactly one of the variables is negative
        ('(a > 0 && b > 0 && c < 0) || (a > 0 && b < 0 && c > 0) || (a < 0 && b > 0 && c > 0)', 44, 10, -30, True),
        # Exactly one of the variables is negative
        ('(a > 0 && b > 0 && c < 0) || (a > 0 && b < 0 && c > 0) || (a < 0 && b > 0 && c > 0)', 99, -91, 22, True),
        # Exactly one of the variables is negative
        ('(a > 0 && b > 0 && c < 0) || (a > 0 && b < 0 && c > 0) || (a < 0 && b > 0 && c > 0)', -4, 44, -77, False),
        # Exactly one of the variables is negative
        ('(a > 0 && b > 0 && c < 0) || (a > 0 && b < 0 && c > 0) || (a < 0 && b > 0 && c > 0)', -7, -94, 54, False),
        # Exactly one of the variables is negative
        ('(a > 0 && b > 0 && c < 0) || (a > 0 && b < 0 && c > 0) || (a < 0 && b > 0 && c > 0)', -3, 58, -72, False),
        # Exactly one of the variables is negative
        ('(a > b) ? ((b > c) ? a > c : a < c) : ((a > c) ? b > c : b < c)', 73, 58, 9, True),
        # Nested conditional expression comparing all three variables
        ('(a > b) ? ((b > c) ? a > c : a < c) : ((a > c) ? b > c : b < c)', 10, 33, -46, True),
        # Nested conditional expression comparing all three variables
        ('(a > b) ? ((b > c) ? a > c : a < c) : ((a > c) ? b > c : b < c)', 45, -37, 98, True),
        # Nested conditional expression comparing all three variables
        ('(a > b) ? ((b > c) ? a > c : a < c) : ((a > c) ? b > c : b < c)', 95, -96, 91, False),
        # Nested conditional expression comparing all three variables
        ('(a > b) ? ((b > c) ? a > c : a < c) : ((a > c) ? b > c : b < c)', 90, -95, -1, False),
        # Nested conditional expression comparing all three variables
        ('(a > b) ? ((b > c) ? a > c : a < c) : ((a > c) ? b > c : b < c)', 77, -4, 38, False),
        # Nested conditional expression comparing all three variables
        ('(a % 2 == 0 && b % 2 == 0) || (a % 2 != 0 && b % 2 != 0) ? c % 2 == 0 : c % 2 != 0', 98, -80, -5, True),
        # c is even if a and b are both even or both odd, otherwise c is odd
        ('(a % 2 == 0 && b % 2 == 0) || (a % 2 != 0 && b % 2 != 0) ? c % 2 == 0 : c % 2 != 0', 94, -58, 2, True),
        # c is even if a and b are both even or both odd, otherwise c is odd
        ('(a % 2 == 0 && b % 2 == 0) || (a % 2 != 0 && b % 2 != 0) ? c % 2 == 0 : c % 2 != 0', -46, -75, 9, True),
        # c is even if a and b are both even or both odd, otherwise c is odd
        ('(a % 2 == 0 && b % 2 == 0) || (a % 2 != 0 && b % 2 != 0) ? c % 2 == 0 : c % 2 != 0', 75, 79, -37, False),
        # c is even if a and b are both even or both odd, otherwise c is odd
        ('(a % 2 == 0 && b % 2 == 0) || (a % 2 != 0 && b % 2 != 0) ? c % 2 == 0 : c % 2 != 0', 43, -33, 43, False),
        # c is even if a and b are both even or both odd, otherwise c is odd
        ('(a % 2 == 0 && b % 2 == 0) || (a % 2 != 0 && b % 2 != 0) ? c % 2 == 0 : c % 2 != 0', 12, -61, -14, False),
        # c is even if a and b are both even or both odd, otherwise c is odd
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 == c**2 || b**2 + c**2 == a**2 || a**2 + c**2 == b**2)', 15, 20, 25,
         True),  # Forms a right triangle (all sides positive and Pythagorean theorem holds for some combination)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 == c**2 || b**2 + c**2 == a**2 || a**2 + c**2 == b**2)', 32, 68, 60,
         True),  # Forms a right triangle (all sides positive and Pythagorean theorem holds for some combination)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 == c**2 || b**2 + c**2 == a**2 || a**2 + c**2 == b**2)', 52, 20, 48,
         True),  # Forms a right triangle (all sides positive and Pythagorean theorem holds for some combination)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 == c**2 || b**2 + c**2 == a**2 || a**2 + c**2 == b**2)', 57, 56, 0,
         False),  # Forms a right triangle (all sides positive and Pythagorean theorem holds for some combination)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 == c**2 || b**2 + c**2 == a**2 || a**2 + c**2 == b**2)', 13, 43, 63,
         False),  # Forms a right triangle (all sides positive and Pythagorean theorem holds for some combination)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 == c**2 || b**2 + c**2 == a**2 || a**2 + c**2 == b**2)', -30, -89,
         18, False),  # Forms a right triangle (all sides positive and Pythagorean theorem holds for some combination)
        (
                '(a <= b && b <= c) || (a <= c && c <= b) || (b <= a && a <= c) || (b <= c && c <= a) || (c <= a && a <= b) || (c <= b && b <= a)',
                -26, -52, -66, True),  # The three variables can be arranged in non-decreasing order
        (
                '(a <= b && b <= c) || (a <= c && c <= b) || (b <= a && a <= c) || (b <= c && c <= a) || (c <= a && a <= b) || (c <= b && b <= a)',
                -99, 10, -32, True),  # The three variables can be arranged in non-decreasing order
        (
                '(a <= b && b <= c) || (a <= c && c <= b) || (b <= a && a <= c) || (b <= c && c <= a) || (c <= a && a <= b) || (c <= b && b <= a)',
                90, -33, -31, True),  # The three variables can be arranged in non-decreasing order
        ('(a == b && b == c) || (a != b && b != c && a != c)', -90, 10, 73, True),
        # Either all three variables are equal or all three are different
        ('(a == b && b == c) || (a != b && b != c && a != c)', 52, -94, -71, True),
        # Either all three variables are equal or all three are different
        ('(a == b && b == c) || (a != b && b != c && a != c)', -46, 28, 73, True),
        # Either all three variables are equal or all three are different
        ('(a == b && b == c) || (a != b && b != c && a != c)', -42, 21, 21, False),
        # Either all three variables are equal or all three are different
        ('(a == b && b == c) || (a != b && b != c && a != c)', 65, -24, -24, False),
        # Either all three variables are equal or all three are different
        ('(a == b && b == c) || (a != b && b != c && a != c)', -76, -73, -76, False),
        # Either all three variables are equal or all three are different
        (
                '(a > 0 && b > 0 && c > 0) && (a + b > c && b + c > a && a + c > b) && (a**2 + b**2 > c**2 && b**2 + c**2 > a**2 && a**2 + c**2 > b**2)',
                45, 79, 70, True),  # Forms a valid acute triangle (triangle inequality and all angles are acute)
        (
                '(a > 0 && b > 0 && c > 0) && (a + b > c && b + c > a && a + c > b) && (a**2 + b**2 > c**2 && b**2 + c**2 > a**2 && a**2 + c**2 > b**2)',
                91, 78, 70, True),  # Forms a valid acute triangle (triangle inequality and all angles are acute)
        (
                '(a > 0 && b > 0 && c > 0) && (a + b > c && b + c > a && a + c > b) && (a**2 + b**2 > c**2 && b**2 + c**2 > a**2 && a**2 + c**2 > b**2)',
                65, 80, 47, True),  # Forms a valid acute triangle (triangle inequality and all angles are acute)
        (
                '(a > 0 && b > 0 && c > 0) && (a + b > c && b + c > a && a + c > b) && (a**2 + b**2 > c**2 && b**2 + c**2 > a**2 && a**2 + c**2 > b**2)',
                -70, -4, 85, False),  # Forms a valid acute triangle (triangle inequality and all angles are acute)
        (
                '(a > 0 && b > 0 && c > 0) && (a + b > c && b + c > a && a + c > b) && (a**2 + b**2 > c**2 && b**2 + c**2 > a**2 && a**2 + c**2 > b**2)',
                -30, -51, -94, False),  # Forms a valid acute triangle (triangle inequality and all angles are acute)
        (
                '(a > 0 && b > 0 && c > 0) && (a + b > c && b + c > a && a + c > b) && (a**2 + b**2 > c**2 && b**2 + c**2 > a**2 && a**2 + c**2 > b**2)',
                -83, 11, 60, False),  # Forms a valid acute triangle (triangle inequality and all angles are acute)
        (
                '!(a == b || b == c || a == c) && ((a > b && a > c) || (b > a && b > c) || (c > a && c > b)) && ((a < b && a < c) || (b < a && b < c) || (c < a && c < b))',
                -1, 11, 48, True),  # All values are different, and there is both a maximum and minimum value
        (
                '!(a == b || b == c || a == c) && ((a > b && a > c) || (b > a && b > c) || (c > a && c > b)) && ((a < b && a < c) || (b < a && b < c) || (c < a && c < b))',
                35, 48, 76, True),  # All values are different, and there is both a maximum and minimum value
        (
                '!(a == b || b == c || a == c) && ((a > b && a > c) || (b > a && b > c) || (c > a && c > b)) && ((a < b && a < c) || (b < a && b < c) || (c < a && c < b))',
                -11, -98, -29, True),  # All values are different, and there is both a maximum and minimum value
        (
                '!(a == b || b == c || a == c) && ((a > b && a > c) || (b > a && b > c) || (c > a && c > b)) && ((a < b && a < c) || (b < a && b < c) || (c < a && c < b))',
                -7, 20, -7, False),  # All values are different, and there is both a maximum and minimum value
        (
                '!(a == b || b == c || a == c) && ((a > b && a > c) || (b > a && b > c) || (c > a && c > b)) && ((a < b && a < c) || (b < a && b < c) || (c < a && c < b))',
                -35, 32, 32, False),  # All values are different, and there is both a maximum and minimum value
        (
                '!(a == b || b == c || a == c) && ((a > b && a > c) || (b > a && b > c) || (c > a && c > b)) && ((a < b && a < c) || (b < a && b < c) || (c < a && c < b))',
                1, 57, 1, False),  # All values are different, and there is both a maximum and minimum value
        (
                '((a % 2 == 0) ? b % 2 == 0 : c % 2 == 0) && ((b % 2 == 0) ? a % 2 == 0 : c % 2 == 0) && ((c % 2 == 0) ? a % 2 == 0 : b % 2 == 0)',
                -38, 42, -41, True),  # Complex parity relationship between variables
        (
                '((a % 2 == 0) ? b % 2 == 0 : c % 2 == 0) && ((b % 2 == 0) ? a % 2 == 0 : c % 2 == 0) && ((c % 2 == 0) ? a % 2 == 0 : b % 2 == 0)',
                -8, 66, 18, True),  # Complex parity relationship between variables
        (
                '((a % 2 == 0) ? b % 2 == 0 : c % 2 == 0) && ((b % 2 == 0) ? a % 2 == 0 : c % 2 == 0) && ((c % 2 == 0) ? a % 2 == 0 : b % 2 == 0)',
                -64, 30, 53, True),  # Complex parity relationship between variables
        (
                '((a % 2 == 0) ? b % 2 == 0 : c % 2 == 0) && ((b % 2 == 0) ? a % 2 == 0 : c % 2 == 0) && ((c % 2 == 0) ? a % 2 == 0 : b % 2 == 0)',
                -34, -31, 67, False),  # Complex parity relationship between variables
        (
                '((a % 2 == 0) ? b % 2 == 0 : c % 2 == 0) && ((b % 2 == 0) ? a % 2 == 0 : c % 2 == 0) && ((c % 2 == 0) ? a % 2 == 0 : b % 2 == 0)',
                29, 36, -27, False),  # Complex parity relationship between variables
        (
                '((a % 2 == 0) ? b % 2 == 0 : c % 2 == 0) && ((b % 2 == 0) ? a % 2 == 0 : c % 2 == 0) && ((c % 2 == 0) ? a % 2 == 0 : b % 2 == 0)',
                -80, 65, -63, False),  # Complex parity relationship between variables
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 + c**2 >= 2 * (a*b + b*c + a*c))', 6, 5, 62, True),
        # The sum of squares is at least twice the sum of products (related to variance)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 + c**2 >= 2 * (a*b + b*c + a*c))', 100, 6, 53, True),
        # The sum of squares is at least twice the sum of products (related to variance)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 + c**2 >= 2 * (a*b + b*c + a*c))', 70, 12, 22, True),
        # The sum of squares is at least twice the sum of products (related to variance)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 + c**2 >= 2 * (a*b + b*c + a*c))', 54, -64, 68, False),
        # The sum of squares is at least twice the sum of products (related to variance)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 + c**2 >= 2 * (a*b + b*c + a*c))', -90, -24, 93, False),
        # The sum of squares is at least twice the sum of products (related to variance)
        ('(a > 0 && b > 0 && c > 0) && (a**2 + b**2 + c**2 >= 2 * (a*b + b*c + a*c))', 64, -4, 30, False),
        # The sum of squares is at least twice the sum of products (related to variance)
        (
                '(a > b) ? ((b > c) ? ((a > c) ? a > b + c : a < b + c) : ((a > c) ? b < a + c : b > a + c)) : ((a > c) ? ((b > c) ? a < b + c : a > b + c) : ((b > c) ? a + c > b : a + c < b))',
                -8, 64, -49, True),  # Highly nested conditional expression with complex inequality relationships
        (
                '(a > b) ? ((b > c) ? ((a > c) ? a > b + c : a < b + c) : ((a > c) ? b < a + c : b > a + c)) : ((a > c) ? ((b > c) ? a < b + c : a > b + c) : ((b > c) ? a + c > b : a + c < b))',
                5, 55, 54, True),  # Highly nested conditional expression with complex inequality relationships
        (
                '(a > b) ? ((b > c) ? ((a > c) ? a > b + c : a < b + c) : ((a > c) ? b < a + c : b > a + c)) : ((a > c) ? ((b > c) ? a < b + c : a > b + c) : ((b > c) ? a + c > b : a + c < b))',
                80, -39, -10, True),  # Highly nested conditional expression with complex inequality relationships
        (
                '(a > b) ? ((b > c) ? ((a > c) ? a > b + c : a < b + c) : ((a > c) ? b < a + c : b > a + c)) : ((a > c) ? ((b > c) ? a < b + c : a > b + c) : ((b > c) ? a + c > b : a + c < b))',
                70, 75, -24, False),  # Highly nested conditional expression with complex inequality relationships
        (
                '(a > b) ? ((b > c) ? ((a > c) ? a > b + c : a < b + c) : ((a > c) ? b < a + c : b > a + c)) : ((a > c) ? ((b > c) ? a < b + c : a > b + c) : ((b > c) ? a + c > b : a + c < b))',
                -99, -12, -95, False),  # Highly nested conditional expression with complex inequality relationships
        (
                '(a > b) ? ((b > c) ? ((a > c) ? a > b + c : a < b + c) : ((a > c) ? b < a + c : b > a + c)) : ((a > c) ? ((b > c) ? a < b + c : a > b + c) : ((b > c) ? a + c > b : a + c < b))',
                -29, 90, -29, False),  # Highly nested conditional expression with complex inequality relationships
    ])
    def test_cond_expression_parse_to_model_call_with_variables(self, expr_text, a, b, c, expected_value):
        ast_node = parse_with_grammar_entry(expr_text, entry_name='cond_expression')
        expr = parse_expr_node_to_expr(ast_node)
        assert pytest.approx(expected_value) == expr(a=a, b=b, c=c)

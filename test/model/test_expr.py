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

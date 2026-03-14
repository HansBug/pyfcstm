"""
Unit tests for Z3 solver expression conversion.

This module tests the conversion of pyfcstm expressions to Z3 solver expressions,
including literals, variables, operators, and variable creation utilities.
"""

import warnings
import pytest
import z3

from pyfcstm.model.expr import (
    Integer, Float, Boolean, Variable,
    BinaryOp, UnaryOp, ConditionalOp, UFunc, parse_expr
)
from pyfcstm.model.model import VarDefine
from pyfcstm.dsl.parse import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine
from pyfcstm.solver.expr import (
    expr_to_z3,
    create_z3_vars_from_models
)


@pytest.mark.unittest
class TestExprToZ3:
    """Test conversion of pyfcstm expressions to Z3 expressions."""

    def test_integer_literal(self):
        """Test conversion of integer literals."""
        expr = Integer(42)
        z3_vars = {}
        result = expr_to_z3(expr, z3_vars)
        assert z3.is_int_value(result)
        assert result.as_long() == 42

    def test_float_literal(self):
        """Test conversion of float literals."""
        expr = Float(3.14)
        z3_vars = {}
        result = expr_to_z3(expr, z3_vars)
        # Check if it's a real value by checking the sort
        assert result.sort() == z3.RealSort()

    def test_boolean_literal(self):
        """Test conversion of boolean literals."""
        expr_true = Boolean(True)
        expr_false = Boolean(False)
        z3_vars = {}

        result_true = expr_to_z3(expr_true, z3_vars)
        result_false = expr_to_z3(expr_false, z3_vars)

        assert z3.is_true(result_true)
        assert z3.is_false(result_false)

    def test_variable(self):
        """Test conversion of variables."""
        z3_vars = {'x': z3.Int('x')}
        expr = Variable('x')
        result = expr_to_z3(expr, z3_vars)
        assert result.eq(z3_vars['x'])

    def test_variable_not_found(self):
        """Test error when variable is not in dictionary."""
        z3_vars = {}
        expr = Variable('unknown')
        with pytest.raises(ValueError, match="Variable 'unknown' not found"):
            expr_to_z3(expr, z3_vars)

    def test_binary_arithmetic_operators(self):
        """Test arithmetic binary operators."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')
        five = Integer(5)

        # Addition
        expr_add = BinaryOp(x=x_var, op='+', y=five)
        result_add = expr_to_z3(expr_add, z3_vars)

        solver = z3.Solver()
        solver.add(result_add == 10)
        assert solver.check() == z3.sat
        assert solver.model()[z3_vars['x']].as_long() == 5

        # Subtraction
        expr_sub = BinaryOp(x=x_var, op='-', y=five)
        result_sub = expr_to_z3(expr_sub, z3_vars)

        solver = z3.Solver()
        solver.add(result_sub == 5)
        assert solver.check() == z3.sat
        assert solver.model()[z3_vars['x']].as_long() == 10

        # Multiplication
        expr_mul = BinaryOp(x=x_var, op='*', y=Integer(3))
        result_mul = expr_to_z3(expr_mul, z3_vars)

        solver = z3.Solver()
        solver.add(result_mul == 15)
        assert solver.check() == z3.sat
        assert solver.model()[z3_vars['x']].as_long() == 5

    def test_binary_comparison_operators(self):
        """Test comparison binary operators."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')
        ten = Integer(10)

        # Greater than
        expr_gt = BinaryOp(x=x_var, op='>', y=ten)
        result_gt = expr_to_z3(expr_gt, z3_vars)

        solver = z3.Solver()
        solver.add(result_gt)
        solver.add(z3_vars['x'] == 15)
        assert solver.check() == z3.sat

        # Less than or equal
        expr_le = BinaryOp(x=x_var, op='<=', y=ten)
        result_le = expr_to_z3(expr_le, z3_vars)

        solver = z3.Solver()
        solver.add(result_le)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

        # Greater than or equal
        expr_ge = BinaryOp(x=x_var, op='>=', y=ten)
        result_ge = expr_to_z3(expr_ge, z3_vars)

        solver = z3.Solver()
        solver.add(result_ge)
        solver.add(z3_vars['x'] == 10)
        assert solver.check() == z3.sat

        # Equal
        expr_eq = BinaryOp(x=x_var, op='==', y=ten)
        result_eq = expr_to_z3(expr_eq, z3_vars)

        solver = z3.Solver()
        solver.add(result_eq)
        assert solver.check() == z3.sat
        assert solver.model()[z3_vars['x']].as_long() == 10

    def test_binary_logical_operators(self):
        """Test logical binary operators."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        # AND operator
        expr_and = BinaryOp(
            x=BinaryOp(x=x_var, op='>', y=Integer(5)),
            op='&&',
            y=BinaryOp(x=y_var, op='<', y=Integer(10))
        )
        result_and = expr_to_z3(expr_and, z3_vars)

        solver = z3.Solver()
        solver.add(result_and)
        solver.add(z3_vars['x'] == 7)
        solver.add(z3_vars['y'] == 8)
        assert solver.check() == z3.sat

        # OR operator
        expr_or = BinaryOp(
            x=BinaryOp(x=x_var, op='<', y=Integer(0)),
            op='||',
            y=BinaryOp(x=x_var, op='>', y=Integer(100))
        )
        result_or = expr_to_z3(expr_or, z3_vars)

        solver = z3.Solver()
        solver.add(result_or)
        solver.add(z3_vars['x'] == 150)
        assert solver.check() == z3.sat

    # Note: Bitwise operators are not supported on Z3 Int types
    # They require BitVec types which is a different approach
    # Skipping bitwise operator tests

    def test_math_function_abs(self):
        """Test absolute value function."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # abs(x) with negative value
        expr_abs = UFunc(func='abs', x=x_var)
        result_abs = expr_to_z3(expr_abs, z3_vars)

        solver = z3.Solver()
        solver.add(result_abs == 5)
        solver.add(z3_vars['x'] == -5)
        assert solver.check() == z3.sat

        # abs(x) with positive value
        solver = z3.Solver()
        solver.add(result_abs == 5)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_math_function_sign(self):
        """Test sign function."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr_sign = UFunc(func='sign', x=x_var)
        result_sign = expr_to_z3(expr_sign, z3_vars)

        # sign(positive) = 1
        solver = z3.Solver()
        solver.add(result_sign == 1)
        solver.add(z3_vars['x'] == 10)
        assert solver.check() == z3.sat

        # sign(negative) = -1
        solver = z3.Solver()
        solver.add(result_sign == -1)
        solver.add(z3_vars['x'] == -10)
        assert solver.check() == z3.sat

        # sign(zero) = 0
        solver = z3.Solver()
        solver.add(result_sign == 0)
        solver.add(z3_vars['x'] == 0)
        assert solver.check() == z3.sat

    def test_math_function_floor(self):
        """Test floor function."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr_floor = UFunc(func='floor', x=x_var)
        result_floor = expr_to_z3(expr_floor, z3_vars)

        solver = z3.Solver()
        solver.add(result_floor == 3)
        solver.add(z3_vars['x'] == z3.RealVal(3.7))
        assert solver.check() == z3.sat

    def test_math_function_ceil(self):
        """Test ceiling function."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr_ceil = UFunc(func='ceil', x=x_var)
        result_ceil = expr_to_z3(expr_ceil, z3_vars)

        solver = z3.Solver()
        solver.add(result_ceil == 4)
        solver.add(z3_vars['x'] == z3.RealVal(3.2))
        assert solver.check() == z3.sat

    def test_math_function_trunc(self):
        """Test truncate function."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr_trunc = UFunc(func='trunc', x=x_var)
        result_trunc = expr_to_z3(expr_trunc, z3_vars)

        # Truncate positive number
        solver = z3.Solver()
        solver.add(result_trunc == 3)
        solver.add(z3_vars['x'] == z3.RealVal(3.7))
        assert solver.check() == z3.sat

        # Truncate negative number
        solver = z3.Solver()
        solver.add(result_trunc == -3)
        solver.add(z3_vars['x'] == z3.RealVal(-3.7))
        assert solver.check() == z3.sat

    def test_math_function_round(self):
        """Test round function."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr_round = UFunc(func='round', x=x_var)
        result_round = expr_to_z3(expr_round, z3_vars)

        solver = z3.Solver()
        solver.add(result_round == 4)
        solver.add(z3_vars['x'] == z3.RealVal(3.6))
        assert solver.check() == z3.sat

    def test_math_function_sqrt(self):
        """Test square root function."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr_sqrt = UFunc(func='sqrt', x=x_var)
        result_sqrt = expr_to_z3(expr_sqrt, z3_vars)

        # Just verify it converts without error
        assert result_sqrt is not None

    def test_math_function_unsupported(self):
        """Test that unsupported functions raise NotImplementedError."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        # Test trigonometric function
        expr_sin = UFunc(func='sin', x=x_var)
        with pytest.raises(NotImplementedError, match="Trigonometric function 'sin'"):
            expr_to_z3(expr_sin, z3_vars)

        # Test logarithmic function
        expr_log = UFunc(func='log', x=x_var)
        with pytest.raises(NotImplementedError, match="Logarithmic function 'log'"):
            expr_to_z3(expr_log, z3_vars)

        # Test exponential function
        expr_exp = UFunc(func='exp', x=x_var)
        with pytest.raises(NotImplementedError, match="Mathematical function 'exp'"):
            expr_to_z3(expr_exp, z3_vars)

        # Test hyperbolic function
        expr_sinh = UFunc(func='sinh', x=x_var)
        with pytest.raises(NotImplementedError, match="Hyperbolic function 'sinh'"):
            expr_to_z3(expr_sinh, z3_vars)

        # Test unknown function (not in any category)
        expr_unknown = UFunc(func='unknown_func', x=x_var)
        with pytest.raises(NotImplementedError, match="Mathematical function 'unknown_func' is not supported"):
            expr_to_z3(expr_unknown, z3_vars)

    def test_unary_operators(self):
        """Test unary operators."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # Negation
        expr_neg = UnaryOp(op='-', x=x_var)
        result_neg = expr_to_z3(expr_neg, z3_vars)

        solver = z3.Solver()
        solver.add(result_neg == -5)
        assert solver.check() == z3.sat
        assert solver.model()[z3_vars['x']].as_long() == 5

        # Logical NOT
        expr_not = UnaryOp(op='!', x=BinaryOp(x=x_var, op='>', y=Integer(10)))
        result_not = expr_to_z3(expr_not, z3_vars)

        solver = z3.Solver()
        solver.add(result_not)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_conditional_operator(self):
        """Test ternary conditional operator."""
        z3_vars = {'x': z3.Int('x'), 'result': z3.Int('result')}
        x_var = Variable('x')

        # result = (x > 10) ? 1 : 0
        expr_cond = ConditionalOp(
            cond=BinaryOp(x=x_var, op='>', y=Integer(10)),
            if_true=Integer(1),
            if_false=Integer(0)
        )
        result_cond = expr_to_z3(expr_cond, z3_vars)

        solver = z3.Solver()
        solver.add(z3_vars['result'] == result_cond)
        solver.add(z3_vars['x'] == 15)
        assert solver.check() == z3.sat
        assert solver.model()[z3_vars['result']].as_long() == 1

        solver = z3.Solver()
        solver.add(z3_vars['result'] == result_cond)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat
        assert solver.model()[z3_vars['result']].as_long() == 0

    def test_complex_expression(self):
        """Test complex nested expression."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        # (x + 5) * (y - 3) > 20
        # With x=5, y=5: (5+5)*(5-3) = 10*2 = 20, which is NOT > 20
        # So we need x=6, y=5: (6+5)*(5-3) = 11*2 = 22 > 20
        expr = BinaryOp(
            x=BinaryOp(
                x=BinaryOp(x=x_var, op='+', y=Integer(5)),
                op='*',
                y=BinaryOp(x=y_var, op='-', y=Integer(3))
            ),
            op='>',
            y=Integer(20)
        )
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result)
        solver.add(z3_vars['x'] == 6)
        solver.add(z3_vars['y'] == 5)
        assert solver.check() == z3.sat


@pytest.mark.unittest
class TestCreateZ3Vars:
    """Test creation of Z3 variables from model objects."""

    def test_create_z3_vars_from_list_of_vardefines_int(self):
        """Test creating Z3 variables from list of integer VarDefine."""
        dsl_code = '''
        def int counter = 0;
        def int flags = 0xFF;
        state System {
            state Idle;
            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)

        z3_vars = create_z3_vars_from_models(list(sm.defines.values()))

        assert 'counter' in z3_vars
        assert 'flags' in z3_vars
        assert z3.is_int(z3_vars['counter'])
        assert z3.is_int(z3_vars['flags'])

    def test_create_z3_vars_from_list_of_vardefines_float(self):
        """Test creating Z3 variables from list of float VarDefine."""
        dsl_code = '''
        def float temperature = 25.0;
        def float pressure = 1.0;
        state System {
            state Idle;
            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)

        z3_vars = create_z3_vars_from_models(list(sm.defines.values()))

        assert 'temperature' in z3_vars
        assert 'pressure' in z3_vars
        assert z3.is_real(z3_vars['temperature'])
        assert z3.is_real(z3_vars['pressure'])

    def test_create_z3_vars_from_list_of_vardefines_mixed(self):
        """Test creating Z3 variables from list of mixed type VarDefine."""
        dsl_code = '''
        def int counter = 0;
        def float temperature = 25.0;
        state System {
            state Idle;
            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)

        z3_vars = create_z3_vars_from_models(list(sm.defines.values()))

        assert len(z3_vars) == 2
        assert z3.is_int(z3_vars['counter'])
        assert z3.is_real(z3_vars['temperature'])

    def test_create_z3_vars_from_list_of_vardefines_bool(self):
        """Test creating Z3 boolean variables from manual VarDefine models."""
        z3_vars = create_z3_vars_from_models([
            VarDefine(name='enabled', type='bool', init=Boolean(False)),
            VarDefine(name='ready', type='bool', init=Boolean(True)),
        ])

        assert len(z3_vars) == 2
        assert z3.is_bool(z3_vars['enabled'])
        assert z3.is_bool(z3_vars['ready'])

    def test_create_z3_vars_from_list_of_vardefines_mixed_with_bool(self):
        """Test creating mixed Z3 variables including boolean definitions."""
        z3_vars = create_z3_vars_from_models([
            VarDefine(name='counter', type='int', init=Integer(0)),
            VarDefine(name='temperature', type='float', init=Float(25.0)),
            VarDefine(name='enabled', type='bool', init=Boolean(False)),
        ])

        assert len(z3_vars) == 3
        assert z3.is_int(z3_vars['counter'])
        assert z3.is_real(z3_vars['temperature'])
        assert z3.is_bool(z3_vars['enabled'])

    def test_create_z3_vars_from_single_vardefine(self):
        """Test creating Z3 variables from single VarDefine."""
        dsl_code = '''
        def int x = 0;
        state System {
            state Idle;
            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)

        z3_vars = create_z3_vars_from_models(list(sm.defines.values())[0])

        assert len(z3_vars) == 1
        assert 'x' in z3_vars
        assert z3.is_int(z3_vars['x'])

    def test_create_z3_vars_from_vardefines_unsupported_type(self):
        """Test error for unsupported variable type."""
        # Manually create a VarDefine with unsupported type
        var_def = VarDefine(name='data', type='string', init=Integer(0))

        with pytest.raises(ValueError, match="Unsupported variable type 'string'"):
            create_z3_vars_from_models([var_def])

    def test_create_z3_vars_from_statemachine(self):
        """Test creating Z3 variables from StateMachine."""
        dsl_code = '''
        def int counter = 0;
        def float temperature = 25.0;
        state System {
            state Idle;
            [*] -> Idle;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)

        z3_vars = create_z3_vars_from_models(sm)

        assert len(z3_vars) == 2
        assert 'counter' in z3_vars
        assert 'temperature' in z3_vars
        assert z3.is_int(z3_vars['counter'])
        assert z3.is_real(z3_vars['temperature'])

    def test_create_z3_vars_from_models_invalid_type(self):
        """Test error for invalid input type."""
        with pytest.raises(TypeError, match="Unsupported input type"):
            create_z3_vars_from_models("invalid")


@pytest.mark.unittest
class TestExprToZ3EdgeCases:
    """Test edge cases and error handling for expression conversion."""

    def test_bitwise_operators_with_warnings(self):
        """Test bitwise operators produce warnings (but may fail on Int)."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        # Test bitwise AND - produces warning but may fail on Int
        expr_and = BinaryOp(x=x_var, op='&', y=y_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result_and = expr_to_z3(expr_and, z3_vars)
                # If it succeeds, verify warning was issued
                assert len(w) == 1
                assert "bitwise and" in str(w[0].message).lower()
                assert result_and is not None
            except TypeError:
                # Expected on Z3 Int - bitwise ops don't work
                # But warning should still have been issued before the error
                assert len(w) == 1
                assert "bitwise and" in str(w[0].message).lower()

        # Test bitwise OR
        expr_or = BinaryOp(x=x_var, op='|', y=y_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result_or = expr_to_z3(expr_or, z3_vars)
                assert len(w) == 1
                assert "bitwise or" in str(w[0].message).lower()
                assert result_or is not None
            except TypeError:
                assert len(w) == 1
                assert "bitwise or" in str(w[0].message).lower()

        # Test bitwise XOR
        expr_xor = BinaryOp(x=x_var, op='^', y=y_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result_xor = expr_to_z3(expr_xor, z3_vars)
                assert len(w) == 1
                assert "bitwise xor" in str(w[0].message).lower()
                assert result_xor is not None
            except TypeError:
                assert len(w) == 1
                assert "bitwise xor" in str(w[0].message).lower()

        # Test left shift
        expr_lshift = BinaryOp(x=x_var, op='<<', y=Integer(2))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result_lshift = expr_to_z3(expr_lshift, z3_vars)
                assert len(w) == 1
                assert "left shift" in str(w[0].message).lower()
                assert result_lshift is not None
            except TypeError:
                assert len(w) == 1
                assert "left shift" in str(w[0].message).lower()

        # Test right shift
        expr_rshift = BinaryOp(x=x_var, op='>>', y=Integer(2))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result_rshift = expr_to_z3(expr_rshift, z3_vars)
                assert len(w) == 1
                assert "right shift" in str(w[0].message).lower()
                assert result_rshift is not None
            except TypeError:
                assert len(w) == 1
                assert "right shift" in str(w[0].message).lower()

    def test_nested_conditionals(self):
        """Test nested conditional expressions."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        # (x > 0) ? ((y > 0) ? 1 : 2) : 3
        expr = ConditionalOp(
            cond=BinaryOp(x=x_var, op='>', y=Integer(0)),
            if_true=ConditionalOp(
                cond=BinaryOp(x=y_var, op='>', y=Integer(0)),
                if_true=Integer(1),
                if_false=Integer(2)
            ),
            if_false=Integer(3)
        )
        result = expr_to_z3(expr, z3_vars)

        # Test x > 0, y > 0 => 1
        solver = z3.Solver()
        solver.add(result == 1)
        solver.add(z3_vars['x'] == 5)
        solver.add(z3_vars['y'] == 5)
        assert solver.check() == z3.sat

        # Test x > 0, y <= 0 => 2
        solver = z3.Solver()
        solver.add(result == 2)
        solver.add(z3_vars['x'] == 5)
        solver.add(z3_vars['y'] == -5)
        assert solver.check() == z3.sat

        # Test x <= 0 => 3
        solver = z3.Solver()
        solver.add(result == 3)
        solver.add(z3_vars['x'] == -5)
        assert solver.check() == z3.sat

    def test_mixed_int_and_real(self):
        """Test expressions mixing int and real types."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Real('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        # x + y (int + real)
        expr = BinaryOp(x=x_var, op='+', y=y_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == z3.RealVal(10.5))
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_division_by_zero_constraint(self):
        """Test that division by zero can be constrained."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        # x / y
        expr = BinaryOp(x=x_var, op='/', y=y_var)
        result = expr_to_z3(expr, z3_vars)

        # Add constraint that y != 0
        solver = z3.Solver()
        solver.add(result == 5)
        solver.add(z3_vars['y'] != 0)
        assert solver.check() == z3.sat

    def test_modulo_operation(self):
        """Test modulo operation."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # x % 10
        expr = BinaryOp(x=x_var, op='%', y=Integer(10))
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 3)
        solver.add(z3_vars['x'] == 23)
        assert solver.check() == z3.sat

    def test_power_operation(self):
        """Test power operation with different patterns."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        # x ** constant (no warning expected)
        expr_const = BinaryOp(x=x_var, op='**', y=Integer(2))
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result_const = expr_to_z3(expr_const, z3_vars)
            # Should not produce warning for x ** constant
            assert len(w) == 0

        solver = z3.Solver()
        solver.add(result_const == 25)
        solver.add(z3_vars['x'] > 0)
        assert solver.check() == z3.sat

        # constant ** x (warning expected)
        expr_exp = BinaryOp(x=Integer(2), op='**', y=x_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result_exp = expr_to_z3(expr_exp, z3_vars)
            assert len(w) == 1
            assert "variable exponent" in str(w[0].message).lower()

        # x ** y (warning expected - worst case)
        expr_both = BinaryOp(x=x_var, op='**', y=y_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result_both = expr_to_z3(expr_both, z3_vars)
            assert len(w) == 1
            assert "two variables" in str(w[0].message).lower()

    def test_unary_plus(self):
        """Test unary plus operator."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UnaryOp(op='+', x=x_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 5)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_unary_bitwise_not(self):
        """Test unary bitwise NOT operator with warning."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UnaryOp(op='~', x=x_var)

        # Should produce a warning (but may fail on Int)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            try:
                result = expr_to_z3(expr, z3_vars)
                # If it succeeds, verify warning was issued
                assert len(w) == 1
                assert "bitwise not" in str(w[0].message).lower()
                assert result is not None
            except TypeError:
                # Expected on Z3 Int - bitwise NOT doesn't work
                # But warning should still have been issued before the error
                assert len(w) == 1
                assert "bitwise not" in str(w[0].message).lower()

    def test_logical_not_keyword(self):
        """Test logical NOT with 'not' keyword."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UnaryOp(op='not', x=BinaryOp(x=x_var, op='>', y=Integer(10)))
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_logical_and_keyword(self):
        """Test logical AND with 'and' keyword."""
        z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
        x_var = Variable('x')
        y_var = Variable('y')

        expr = BinaryOp(
            x=BinaryOp(x=x_var, op='>', y=Integer(0)),
            op='and',
            y=BinaryOp(x=y_var, op='<', y=Integer(10))
        )
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result)
        solver.add(z3_vars['x'] == 5)
        solver.add(z3_vars['y'] == 5)
        assert solver.check() == z3.sat

    def test_logical_or_keyword(self):
        """Test logical OR with 'or' keyword."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = BinaryOp(
            x=BinaryOp(x=x_var, op='<', y=Integer(0)),
            op='or',
            y=BinaryOp(x=x_var, op='>', y=Integer(10))
        )
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result)
        solver.add(z3_vars['x'] == 15)
        assert solver.check() == z3.sat

    def test_not_equal_operator(self):
        """Test not equal operator."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = BinaryOp(x=x_var, op='!=', y=Integer(10))
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_abs_with_real(self):
        """Test absolute value with real numbers."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr = UFunc(func='abs', x=x_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == z3.RealVal(5.5))
        solver.add(z3_vars['x'] == z3.RealVal(-5.5))
        assert solver.check() == z3.sat

    def test_sign_with_real(self):
        """Test sign function with real numbers."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr = UFunc(func='sign', x=x_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == z3.RealVal(1))
        solver.add(z3_vars['x'] == z3.RealVal(3.14))
        assert solver.check() == z3.sat

    def test_floor_with_int(self):
        """Test floor function with integer (should return same value)."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='floor', x=x_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 5)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_ceil_with_int(self):
        """Test ceiling function with integer (should return same value)."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='ceil', x=x_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 5)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_trunc_with_int(self):
        """Test truncate function with integer (should return same value)."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='trunc', x=x_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 5)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_round_with_int(self):
        """Test round function with integer (should return same value)."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='round', x=x_var)
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 5)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_sqrt_with_int_auto_convert(self):
        """Test that sqrt with integer auto-converts to Real silently."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='sqrt', x=x_var)

        # Should NOT produce a warning (silent conversion)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = expr_to_z3(expr, z3_vars)
            assert len(w) == 0

        # Verify it still produces a result
        assert result is not None

    def test_floor_with_int_no_warning(self):
        """Test floor with Int produces no warning."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='floor', x=x_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = expr_to_z3(expr, z3_vars)
            # Should not produce warning
            assert len(w) == 0

        assert result is not None

    def test_ceil_with_int_no_warning(self):
        """Test ceil with Int produces no warning."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='ceil', x=x_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = expr_to_z3(expr, z3_vars)
            # Should not produce warning
            assert len(w) == 0

        assert result is not None

    def test_trunc_with_int_no_warning(self):
        """Test trunc with Int produces no warning."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='trunc', x=x_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = expr_to_z3(expr, z3_vars)
            # Should not produce warning
            assert len(w) == 0

        assert result is not None

    def test_round_with_int_no_warning(self):
        """Test round with Int produces no warning."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        expr = UFunc(func='round', x=x_var)
        with warnings.catch_warnings(record=True) as w:
            warnings.simplefilter("always")
            result = expr_to_z3(expr, z3_vars)
            # Should not produce warning
            assert len(w) == 0

        assert result is not None

    def test_cbrt_raises_error(self):
        """Test that cbrt raises NotImplementedError."""
        z3_vars = {'x': z3.Real('x')}
        x_var = Variable('x')

        expr = UFunc(func='cbrt', x=x_var)
        with pytest.raises(NotImplementedError, match="cbrt.*not directly supported"):
            expr_to_z3(expr, z3_vars)

    def test_unsupported_binary_operator(self):
        """Test that unsupported binary operator raises ValueError."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # Create a BinaryOp with an invalid operator
        expr = BinaryOp(x=x_var, op='@@@', y=Integer(5))
        with pytest.raises(ValueError, match="Unsupported binary operator"):
            expr_to_z3(expr, z3_vars)

    def test_unsupported_unary_operator(self):
        """Test that unsupported unary operator raises ValueError."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # Create a UnaryOp with an invalid operator
        expr = UnaryOp(op='@@@', x=x_var)
        with pytest.raises(ValueError, match="Unsupported unary operator"):
            expr_to_z3(expr, z3_vars)

    def test_unsupported_expression_type(self):
        """Test that unsupported expression type raises ValueError."""
        z3_vars = {}

        # Create a mock expression type
        class UnsupportedExpr:
            pass

        expr = UnsupportedExpr()
        with pytest.raises(ValueError, match="Unsupported expression type"):
            expr_to_z3(expr, z3_vars)

    def test_complex_nested_expression(self):
        """Test complex nested expression with multiple operators."""
        z3_vars = {'a': z3.Int('a'), 'b': z3.Int('b'), 'c': z3.Int('c')}
        a_var = Variable('a')
        b_var = Variable('b')
        c_var = Variable('c')

        # ((a + b) * c) > (a - b)
        expr = BinaryOp(
            x=BinaryOp(
                x=BinaryOp(x=a_var, op='+', y=b_var),
                op='*',
                y=c_var
            ),
            op='>',
            y=BinaryOp(x=a_var, op='-', y=b_var)
        )
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result)
        solver.add(z3_vars['a'] == 5)
        solver.add(z3_vars['b'] == 3)
        solver.add(z3_vars['c'] == 2)
        assert solver.check() == z3.sat

    def test_boolean_literal_in_expression(self):
        """Test boolean literals in expressions."""
        z3_vars = {}

        expr_true = Boolean(True)
        expr_false = Boolean(False)

        result_true = expr_to_z3(expr_true, z3_vars)
        result_false = expr_to_z3(expr_false, z3_vars)

        assert z3.is_true(result_true)
        assert z3.is_false(result_false)

    def test_zero_values(self):
        """Test expressions with zero values."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # x + 0
        expr = BinaryOp(x=x_var, op='+', y=Integer(0))
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 5)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_negative_numbers(self):
        """Test expressions with negative numbers."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # x + (-5)
        expr = BinaryOp(x=x_var, op='+', y=Integer(-5))
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result == 0)
        solver.add(z3_vars['x'] == 5)
        assert solver.check() == z3.sat

    def test_large_numbers(self):
        """Test expressions with large numbers."""
        z3_vars = {'x': z3.Int('x')}
        x_var = Variable('x')

        # x > 1000000
        expr = BinaryOp(x=x_var, op='>', y=Integer(1000000))
        result = expr_to_z3(expr, z3_vars)

        solver = z3.Solver()
        solver.add(result)
        solver.add(z3_vars['x'] == 1000001)
        assert solver.check() == z3.sat

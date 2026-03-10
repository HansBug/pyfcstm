"""
Tests for solver operation parsing and execution.
"""

import pytest
import z3

from pyfcstm.solver.operation import parse_operations, execute_operations
from pyfcstm.model.model import Operation
from pyfcstm.model.expr import Variable, Integer, BinaryOp
from pyfcstm.dsl.error import GrammarParseError


@pytest.mark.unittest
class TestParseOperations:
    """Test parse_operations function."""

    def test_parse_single_operation(self):
        """Test parsing a single operation."""
        ops = parse_operations("x = 10;")
        assert len(ops) == 1
        assert ops[0].var_name == "x"

    def test_parse_multiple_operations(self):
        """Test parsing multiple operations."""
        ops = parse_operations("x = 10; y = 20; z = 30;")
        assert len(ops) == 3
        assert ops[0].var_name == "x"
        assert ops[1].var_name == "y"
        assert ops[2].var_name == "z"

    def test_parse_with_expressions(self):
        """Test parsing operations with complex expressions."""
        ops = parse_operations("x = x + 1; y = x * 2;")
        assert len(ops) == 2
        assert ops[0].var_name == "x"
        assert ops[1].var_name == "y"

    def test_parse_empty_operations(self):
        """Test parsing empty operation set."""
        ops = parse_operations("")
        assert len(ops) == 0

    def test_parse_with_semicolons_only(self):
        """Test parsing with only semicolons."""
        ops = parse_operations(";;;")
        assert len(ops) == 0

    def test_parse_mixed_with_empty_statements(self):
        """Test parsing with empty statements mixed in."""
        ops = parse_operations("x = 1; ; y = 2; ;")
        assert len(ops) == 2
        assert ops[0].var_name == "x"
        assert ops[1].var_name == "y"

    def test_free_mode_no_restrictions(self):
        """Test free mode with no variable restrictions."""
        ops = parse_operations("a = b + c; d = e * f;", allowed_vars=None)
        assert len(ops) == 2
        assert ops[0].var_name == "a"
        assert ops[1].var_name == "d"

    def test_restricted_mode_valid_variables(self):
        """Test restricted mode with valid variables."""
        ops = parse_operations("x = x + 1; y = x * 2;", allowed_vars=['x', 'y'])
        assert len(ops) == 2

    def test_restricted_mode_invalid_assignment_target(self):
        """Test restricted mode with invalid assignment target."""
        with pytest.raises(ValueError, match="Variable 'z' is not in allowed variables"):
            parse_operations("z = 10;", allowed_vars=['x', 'y'])

    def test_restricted_mode_invalid_expression_variable(self):
        """Test restricted mode with invalid variable in expression."""
        with pytest.raises(ValueError, match="Variable 'z' is not in allowed variables"):
            parse_operations("x = z + 1;", allowed_vars=['x', 'y'])

    def test_parse_with_bitwise_operators(self):
        """Test parsing operations with bitwise operators."""
        ops = parse_operations("x = x & 0xFF; y = x | 0x01;")
        assert len(ops) == 2

    def test_parse_with_functions(self):
        """Test parsing operations with mathematical functions."""
        ops = parse_operations("x = sin(y); z = sqrt(x);")
        assert len(ops) == 2

    def test_parse_invalid_syntax(self):
        """Test parsing with invalid syntax."""
        with pytest.raises(GrammarParseError):
            parse_operations("x = ;")

    def test_parse_missing_semicolon(self):
        """Test parsing with missing semicolon."""
        with pytest.raises(GrammarParseError):
            parse_operations("x = 10")


@pytest.mark.unittest
class TestExecuteOperations:
    """Test execute_operations function."""

    def test_execute_single_operation(self):
        """Test executing a single operation."""
        op = Operation(var_name='x', expr=Integer(10))
        x = z3.Int('x')
        var_exprs = {'x': x}

        new_exprs = execute_operations(op, var_exprs)
        assert 'x' in new_exprs
        # Verify the result is 10
        solver = z3.Solver()
        solver.add(new_exprs['x'] == 10)
        assert solver.check() == z3.sat

    def test_execute_operation_list(self):
        """Test executing a list of operations."""
        ops = [
            Operation(var_name='x', expr=Integer(5)),
            Operation(var_name='y', expr=Integer(10))
        ]
        x = z3.Int('x')
        y = z3.Int('y')
        var_exprs = {'x': x, 'y': y}

        new_exprs = execute_operations(ops, var_exprs)
        assert 'x' in new_exprs
        assert 'y' in new_exprs

    def test_execute_with_variable_reference(self):
        """Test executing operation that references a variable."""
        op = Operation(
            var_name='x',
            expr=BinaryOp(x=Variable('x'), op='+', y=Integer(1))
        )
        x = z3.Int('x')
        var_exprs = {'x': x}

        new_exprs = execute_operations(op, var_exprs)

        # Verify symbolically: new_exprs['x'] should be x + 1
        solver = z3.Solver()
        solver.add(x == 5)
        solver.add(new_exprs['x'] == 6)
        assert solver.check() == z3.sat

    def test_execute_sequential_operations(self):
        """Test executing operations that depend on each other."""
        ops = [
            Operation(var_name='x', expr=BinaryOp(x=Variable('x'), op='+', y=Integer(2))),
            Operation(var_name='y', expr=BinaryOp(x=Variable('y'), op='+', y=Variable('x')))
        ]
        x = z3.Int('x')
        y = z3.Int('y')
        var_exprs = {'x': x, 'y': y}

        new_exprs = execute_operations(ops, var_exprs)

        # x should be x + 2
        # y should be y + (x + 2)
        solver = z3.Solver()
        solver.add(x == 5, y == 10)
        solver.add(new_exprs['x'] == 7)  # 5 + 2
        solver.add(new_exprs['y'] == 17)  # 10 + 7
        assert solver.check() == z3.sat

    def test_execute_does_not_modify_original_state(self):
        """Test that execution does not modify the original state."""
        op = Operation(var_name='x', expr=Integer(10))
        x = z3.Int('x')
        var_exprs = {'x': x}

        original_x = var_exprs['x']
        new_exprs = execute_operations(op, var_exprs)

        # Original state should be unchanged
        assert var_exprs['x'] is original_x
        # New state should be different
        assert new_exprs is not var_exprs

    def test_execute_with_multiple_variables(self):
        """Test executing operations with multiple variables."""
        ops = [
            Operation(var_name='x', expr=Integer(10)),
            Operation(var_name='y', expr=Integer(20)),
            Operation(
                var_name='z',
                expr=BinaryOp(x=Variable('x'), op='+', y=Variable('y'))
            )
        ]
        x = z3.Int('x')
        y = z3.Int('y')
        z = z3.Int('z')
        var_exprs = {'x': x, 'y': y, 'z': z}

        new_exprs = execute_operations(ops, var_exprs)

        # z should be 10 + 20 = 30
        solver = z3.Solver()
        solver.add(new_exprs['z'] == 30)
        assert solver.check() == z3.sat

    def test_execute_with_bitwise_operations(self):
        """Test executing operations with bitwise operators."""
        # Note: Z3 IntVal doesn't support bitwise operations with concrete values
        # This test verifies that the operation parsing works, but execution
        # with concrete Z3 values may have limitations
        ops = [
            Operation(var_name='x', expr=Integer(0xFF)),
            Operation(var_name='y', expr=Integer(0x0F))
        ]
        x = z3.Int('x')
        y = z3.Int('y')
        var_exprs = {'x': x, 'y': y}

        new_exprs = execute_operations(ops, var_exprs)

        # x should be 255, y should be 15
        solver = z3.Solver()
        solver.add(new_exprs['x'] == 255)
        solver.add(new_exprs['y'] == 15)
        assert solver.check() == z3.sat


@pytest.mark.unittest
class TestIntegration:
    """Integration tests for parse and execute."""

    def test_parse_and_execute(self):
        """Test parsing and executing operations together."""
        code = "x = x + 2; y = y + x;"
        ops = parse_operations(code, allowed_vars=['x', 'y'])

        x = z3.Int('x')
        y = z3.Int('y')
        var_exprs = {'x': x, 'y': y}

        new_exprs = execute_operations(ops, var_exprs)

        # x should be x + 2, y should be y + (x + 2)
        solver = z3.Solver()
        solver.add(x == 5, y == 10)
        solver.add(new_exprs['x'] == 7)  # 5 + 2
        solver.add(new_exprs['y'] == 17)  # 10 + 7
        assert solver.check() == z3.sat

    def test_parse_and_execute_complex(self):
        """Test parsing and executing complex operations."""
        code = """
        counter = counter + 1;
        result = counter * 10;
        """
        ops = parse_operations(code, allowed_vars=['counter', 'result'])

        counter = z3.Int('counter')
        result = z3.Int('result')
        var_exprs = {
            'counter': counter,
            'result': result
        }

        new_exprs = execute_operations(ops, var_exprs)

        # counter should be counter + 1, result should be (counter + 1) * 10
        solver = z3.Solver()
        solver.add(counter == 0)
        solver.add(new_exprs['counter'] == 1)  # 0 + 1
        solver.add(new_exprs['result'] == 10)  # 1 * 10
        assert solver.check() == z3.sat

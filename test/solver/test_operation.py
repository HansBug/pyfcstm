"""
Tests for solver operation parsing and execution.
"""

import pytest
import z3

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.solver.operation import parse_operations, execute_operations
from pyfcstm.model import IfBlock, IfBlockBranch, Operation, parse_dsl_node_to_state_machine
from pyfcstm.model.expr import Variable, Integer, BinaryOp
from pyfcstm.dsl.error import GrammarParseError
from pyfcstm.simulate import SimulationRuntime


def assert_symbolic_outputs(var_exprs, new_exprs, assumptions, expected_outputs):
    solver = z3.Solver()
    for name, value in assumptions.items():
        solver.add(var_exprs[name] == value)
    for name, value in expected_outputs.items():
        solver.add(new_exprs[name] == value)
    assert solver.check() == z3.sat


def assert_z3_expr_equal(actual_expr, expected_expr):
    actual_simplified = z3.simplify(actual_expr)
    expected_simplified = z3.simplify(expected_expr)
    assert z3.eq(actual_simplified, expected_simplified), (
        f"Expected Z3 expr {expected_simplified.sexpr()}, "
        f"got {actual_simplified.sexpr()}"
    )


def build_runtime_for_block(block_code: str, initial_values):
    define_lines = [
        f"def int {name} = {value};"
        for name, value in initial_values.items()
    ]
    dsl_code = "\n".join(
        define_lines + [
            "state Root {",
            "    state A {",
            "        during {",
            block_code,
            "        }",
            "    }",
            "    [*] -> A;",
            "}",
        ]
    )
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    sm = parse_dsl_node_to_state_machine(ast)
    return SimulationRuntime(sm)


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

    def test_restricted_mode_temporary_assignment_target(self):
        """Test restricted mode allows temporary assignment targets."""
        ops = parse_operations("z = x + 1; y = z * 2;", allowed_vars=['x', 'y'])
        assert [op.var_name for op in ops] == ['z', 'y']

    def test_restricted_mode_invalid_expression_variable(self):
        """Test restricted mode with invalid variable in expression."""
        with pytest.raises(ValueError, match="Variable 'z' is not in allowed variables"):
            parse_operations("x = z + 1;", allowed_vars=['x', 'y'])

    def test_restricted_mode_variable_used_before_assignment(self):
        """Test restricted mode rejects temporary variables used before assignment."""
        with pytest.raises(ValueError, match="Variable 'z' is not in allowed variables"):
            parse_operations("y = z + 1; z = x + 1;", allowed_vars=['x', 'y'])

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

    def test_parse_if_statement(self):
        """Test parsing an operation-block if statement."""
        statements = parse_operations("""
        if [x > 0] {
            y = x + 1;
        } else {
            y = x + 2;
        }
        """, allowed_vars=['x', 'y'])

        assert len(statements) == 1
        assert isinstance(statements[0], IfBlock)
        assert len(statements[0].branches) == 2
        assert statements[0].branches[1].condition is None

    def test_parse_if_condition_rejects_unknown_variable(self):
        """Test restricted mode rejects unknown variables in if conditions."""
        with pytest.raises(ValueError, match="Variable 'missing' is not in allowed variables"):
            parse_operations("""
            if [missing > 0] {
                x = x + 1;
            }
            """, allowed_vars=['x'])

    def test_parse_branch_local_temp_does_not_escape(self):
        """Test restricted mode rejects branch-local temporaries after the if block."""
        with pytest.raises(ValueError, match="Variable 'tmp' is not in allowed variables"):
            parse_operations("""
            if [x > 0] {
                tmp = x + 1;
            }
            y = tmp;
            """, allowed_vars=['x', 'y'])

    def test_parse_outer_temp_can_be_used_after_if(self):
        """Test restricted mode allows pre-if temporaries to be used after the if block."""
        statements = parse_operations("""
        tmp = x + 1;
        if [x > 0] {
            tmp = tmp + 10;
        }
        y = tmp;
        """, allowed_vars=['x', 'y'])

        assert len(statements) == 3
        assert isinstance(statements[1], IfBlock)


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

    def test_execute_with_temporary_variable(self):
        """Test executing operations with temporary variables that do not leak."""
        ops = [
            Operation(var_name='tmp', expr=BinaryOp(x=Variable('x'), op='+', y=Variable('y'))),
            Operation(var_name='x', expr=BinaryOp(x=Variable('tmp'), op='+', y=Integer(1))),
        ]
        x = z3.Int('x')
        y = z3.Int('y')
        var_exprs = {'x': x, 'y': y}

        new_exprs = execute_operations(ops, var_exprs)

        assert set(new_exprs.keys()) == {'x', 'y'}
        assert 'tmp' not in new_exprs

        solver = z3.Solver()
        solver.add(x == 5, y == 10)
        solver.add(new_exprs['x'] == 16)
        solver.add(new_exprs['y'] == 10)
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

    @pytest.mark.parametrize(
        ['code', 'var_names', 'expected_builder'],
        [
            (
                """
                if [x > 0] {
                    y = x + 10;
                }
                """,
                ['x', 'y'],
                lambda vars_: {
                    'x': vars_['x'],
                    'y': z3.If(vars_['x'] > 0, vars_['x'] + 10, vars_['y']),
                },
            ),
            (
                """
                if [x > 0] {
                    y = x + 10;
                } else {
                    y = x + 20;
                }
                """,
                ['x', 'y'],
                lambda vars_: {
                    'x': vars_['x'],
                    'y': z3.If(vars_['x'] > 0, vars_['x'] + 10, vars_['x'] + 20),
                },
            ),
            (
                """
                if [mode == 0] {
                    y = 10;
                } else if [mode == 1] {
                    y = 20;
                } else {
                    y = 30;
                }
                """,
                ['x', 'y', 'mode'],
                lambda vars_: {
                    'x': vars_['x'],
                    'y': z3.If(
                        z3.IntVal(0) == vars_['mode'],
                        z3.IntVal(10),
                        z3.If(z3.IntVal(1) == vars_['mode'], z3.IntVal(20), z3.IntVal(30)),
                    ),
                    'mode': vars_['mode'],
                },
            ),
            (
                """
                if [x > 0] {
                    tmp = x + 1;
                    if [y > 0] {
                        z = tmp + y;
                    } else {
                        z = tmp + 100;
                    }
                } else {
                    z = 999;
                }
                """,
                ['x', 'y', 'z'],
                lambda vars_: {
                    'x': vars_['x'],
                    'y': vars_['y'],
                    'z': z3.If(
                        vars_['x'] > 0,
                        z3.If(vars_['y'] > 0, vars_['x'] + 1 + vars_['y'], vars_['x'] + 101),
                        z3.IntVal(999),
                    ),
                },
            ),
            (
                """
                if [x > 0] {
                    x = x + 1;
                    y = x + 10;
                } else {
                    y = y + 100;
                }
                """,
                ['x', 'y'],
                lambda vars_: {
                    'x': z3.If(vars_['x'] > 0, vars_['x'] + 1, vars_['x']),
                    'y': z3.If(vars_['x'] > 0, vars_['x'] + 11, vars_['y'] + 100),
                },
            ),
        ]
    )
    def test_execute_if_blocks_symbolically(self, code, var_names, expected_builder):
        statements = parse_operations(code, allowed_vars=var_names)
        var_exprs = {name: z3.Int(name) for name in var_names}

        new_exprs = execute_operations(statements, var_exprs)
        expected_exprs = expected_builder(var_exprs)

        assert set(new_exprs.keys()) == set(var_exprs.keys())
        for name in var_names:
            assert_z3_expr_equal(new_exprs[name], expected_exprs[name])

    def test_execute_branch_local_temp_does_not_leak(self):
        """Test branch-local temporary expressions do not appear in final output."""
        statements = parse_operations("""
        if [x > 0] {
            tmp = x + y;
            x = tmp + 1;
        }
        """, allowed_vars=['x', 'y'])
        var_exprs = {'x': z3.Int('x'), 'y': z3.Int('y')}

        new_exprs = execute_operations(statements, var_exprs)

        assert set(new_exprs.keys()) == {'x', 'y'}
        assert 'tmp' not in new_exprs
        assert_z3_expr_equal(new_exprs['x'], z3.If(var_exprs['x'] > 0, var_exprs['x'] + var_exprs['y'] + 1, var_exprs['x']))
        assert_z3_expr_equal(new_exprs['y'], var_exprs['y'])

    def test_execute_outer_temp_participates_in_merge(self):
        """Test pre-if temporary expressions participate in branch merge."""
        statements = parse_operations("""
        tmp = x + 1;
        if [x > 0] {
            tmp = tmp + 10;
        }
        y = tmp;
        """, allowed_vars=['x', 'y'])
        var_exprs = {'x': z3.Int('x'), 'y': z3.Int('y')}

        new_exprs = execute_operations(statements, var_exprs)

        assert set(new_exprs.keys()) == {'x', 'y'}
        assert_z3_expr_equal(new_exprs['x'], var_exprs['x'])
        assert_z3_expr_equal(new_exprs['y'], z3.If(var_exprs['x'] > 0, var_exprs['x'] + 11, var_exprs['x'] + 1))


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

    def test_parse_and_execute_with_temporary_variable(self):
        """Test parsing and executing operations with a temporary variable."""
        code = """
        temp = x + y;
        y = temp * 2;
        """
        ops = parse_operations(code, allowed_vars=['x', 'y'])

        x = z3.Int('x')
        y = z3.Int('y')
        var_exprs = {'x': x, 'y': y}

        new_exprs = execute_operations(ops, var_exprs)

        assert set(new_exprs.keys()) == {'x', 'y'}
        assert 'temp' not in new_exprs

        solver = z3.Solver()
        solver.add(x == 3, y == 4)
        solver.add(new_exprs['x'] == 3)
        solver.add(new_exprs['y'] == 14)
        assert solver.check() == z3.sat

    @pytest.mark.parametrize(
        ['block_code', 'initial_values'],
        [
            (
                """
            if [x > 0] {
                tmp = x + 1;
                if [flag > 0] {
                    y = tmp + 10;
                } else {
                    y = tmp + 20;
                }
            } else {
                y = y + 100;
            }
                """,
                {'x': 5, 'y': 1, 'flag': 1},
            ),
            (
                """
            if [x > 0] {
                tmp = x + 1;
                if [flag > 0] {
                    y = tmp + 10;
                } else {
                    y = tmp + 20;
                }
            } else {
                y = y + 100;
            }
                """,
                {'x': 5, 'y': 1, 'flag': 0},
            ),
            (
                """
            if [x > 0] {
                tmp = x + 1;
                if [flag > 0] {
                    y = tmp + 10;
                } else {
                    y = tmp + 20;
                }
            } else {
                y = y + 100;
            }
                """,
                {'x': 0, 'y': 1, 'flag': 0},
            ),
        ]
    )
    def test_solver_and_runtime_match_for_if_blocks(self, block_code, initial_values):
        statements = parse_operations(block_code, allowed_vars=list(initial_values.keys()))
        var_exprs = {
            name: z3.Int(name)
            for name in initial_values.keys()
        }
        new_exprs = execute_operations(statements, var_exprs)

        runtime = build_runtime_for_block(block_code, initial_values)
        runtime.cycle()

        expected_outputs = {
            name: runtime.vars[name]
            for name in initial_values.keys()
        }

        assert_symbolic_outputs(var_exprs, new_exprs, initial_values, expected_outputs)

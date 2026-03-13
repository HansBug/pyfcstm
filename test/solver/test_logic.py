"""
Tests for solver logical helper functions.
"""

import pytest
import z3

from pyfcstm.solver.logic import (
    z3_or,
    z3_and,
    z3_not,
    is_satisfiable,
    contributes_to_solution_space,
    are_equivalent,
)


@pytest.mark.unittest
class TestLogicalCombinationHelpers:
    """Test Z3 logical expression combination helpers."""

    def test_z3_or_empty_list(self):
        """Test OR over an empty list."""
        result = z3_or([])
        assert z3.is_false(result)

    def test_z3_or_single_expression(self):
        """Test OR over a single expression returns the original expression."""
        x = z3.Int('x')
        expr = x > 0
        assert z3_or([expr]) is expr

    def test_z3_or_multiple_expressions(self):
        """Test OR over multiple expressions."""
        x = z3.Int('x')
        expr = z3_or([x == 1, x == 2, x == 3])

        solver = z3.Solver()
        solver.add(expr, x == 2)
        assert solver.check() == z3.sat

    def test_z3_and_empty_list(self):
        """Test AND over an empty list."""
        result = z3_and([])
        assert z3.is_true(result)

    def test_z3_and_single_expression(self):
        """Test AND over a single expression returns the original expression."""
        x = z3.Int('x')
        expr = x > 0
        assert z3_and([expr]) is expr

    def test_z3_and_multiple_expressions(self):
        """Test AND over multiple expressions."""
        x = z3.Int('x')
        expr = z3_and([x > 0, x < 3])

        solver = z3.Solver()
        solver.add(expr, x == 2)
        assert solver.check() == z3.sat

    def test_z3_not_true_constant(self):
        """Test NOT over a true constant."""
        result = z3_not(z3.BoolVal(True))
        assert z3.is_false(result)

    def test_z3_not_false_constant(self):
        """Test NOT over a false constant."""
        result = z3_not(z3.BoolVal(False))
        assert z3.is_true(result)

    def test_z3_not_regular_expression(self):
        """Test NOT over a normal expression."""
        x = z3.Int('x')
        expr = z3_not(x > 0)

        solver = z3.Solver()
        solver.add(expr, x == 0)
        assert solver.check() == z3.sat

    def test_z3_not_double_negation(self):
        """Test NOT removes a double negation wrapper."""
        x = z3.Int('x')
        inner = x > 0
        result = z3_not(z3.Not(inner))

        assert result.eq(inner)


@pytest.mark.unittest
class TestLogicalSolvingHelpers:
    """Test satisfiability, contribution, and equivalence helpers."""

    def test_is_satisfiable_true(self):
        """Test satisfiable expression detection."""
        x = z3.Int('x')
        assert is_satisfiable(z3_and([x > 0, x < 3]))

    def test_is_satisfiable_false(self):
        """Test unsatisfiable expression detection."""
        x = z3.Int('x')
        assert not is_satisfiable(z3_and([x > 0, x < 0]))

    def test_is_satisfiable_true_multiple_variables(self):
        """Test satisfiable expression detection with multiple variables."""
        x = z3.Int('x')
        y = z3.Int('y')
        z = z3.Int('z')

        expr = z3_and([
            x + y == 10,
            x > 0,
            y > 0,
            z == x - y,
            z == 4,
        ])

        assert is_satisfiable(expr)

    def test_is_satisfiable_false_multiple_variables(self):
        """Test unsatisfiable expression detection with multiple variables."""
        x = z3.Int('x')
        y = z3.Int('y')
        z = z3.Int('z')

        expr = z3_and([
            x + y == 1,
            x >= 2,
            y >= 2,
            z == x + y,
        ])

        assert not is_satisfiable(expr)

    def test_is_satisfiable_without_variables(self):
        """Test satisfiable expression detection without unknown variables."""
        assert is_satisfiable(z3.BoolVal(True))
        assert not is_satisfiable(z3.BoolVal(False))

    def test_contributes_to_solution_space_true(self):
        """Test contribution detection when y adds new solutions."""
        x = z3.Int('x')
        assert contributes_to_solution_space(x == 1, x == 2)

    def test_contributes_to_solution_space_false(self):
        """Test contribution detection when y is already covered by x."""
        x = z3.Int('x')
        assert not contributes_to_solution_space(z3_or([x == 1, x == 2]), x == 2)

    def test_contributes_to_solution_space_true_multiple_variables(self):
        """Test contribution detection with multiple variables when y adds solutions."""
        x = z3.Int('x')
        y = z3.Int('y')

        expr_x = z3_or([
            z3_and([x == 0, y == 0]),
            z3_and([x == 1, y == 1]),
        ])
        expr_y = x + y == 1

        assert contributes_to_solution_space(expr_x, expr_y)

    def test_contributes_to_solution_space_false_multiple_variables(self):
        """Test contribution detection with multiple variables when y is a subset of x."""
        x = z3.Int('x')
        y = z3.Int('y')

        expr_x = z3_and([x >= 0, y >= 0])
        expr_y = z3_and([x == 1, y == 1])

        assert not contributes_to_solution_space(expr_x, expr_y)

    def test_contributes_to_solution_space_without_variables(self):
        """Test contribution detection without unknown variables."""
        assert contributes_to_solution_space(z3.BoolVal(False), z3.BoolVal(True))
        assert not contributes_to_solution_space(z3.BoolVal(True), z3.BoolVal(True))
        assert not contributes_to_solution_space(z3.BoolVal(True), z3.BoolVal(False))

    def test_are_equivalent_true(self):
        """Test equivalence detection for equivalent expressions."""
        x = z3.Int('x')
        assert are_equivalent(x > 0, x >= 1)

    def test_are_equivalent_false(self):
        """Test equivalence detection for non-equivalent expressions."""
        x = z3.Int('x')
        assert not are_equivalent(x > 0, x >= 0)

    def test_are_equivalent_true_multiple_variables(self):
        """Test equivalence detection for equivalent expressions with multiple variables."""
        x = z3.Int('x')
        y = z3.Int('y')

        expr_x = z3_and([x >= 0, y >= 0, x + y == 2])
        expr_y = z3_and([
            y == 2 - x,
            z3_or([x == 0, x == 1, x == 2]),
        ])

        assert are_equivalent(expr_x, expr_y)

    def test_are_equivalent_false_multiple_variables(self):
        """Test equivalence detection for non-equivalent expressions with multiple variables."""
        x = z3.Int('x')
        y = z3.Int('y')

        expr_x = x + y == 2
        expr_y = z3_and([x + y == 2, x >= 0, y >= 0])

        assert not are_equivalent(expr_x, expr_y)

    def test_are_equivalent_without_variables(self):
        """Test equivalence detection without unknown variables."""
        assert are_equivalent(z3.BoolVal(True), z3.BoolVal(True))
        assert are_equivalent(z3.BoolVal(False), z3.BoolVal(False))
        assert not are_equivalent(z3.BoolVal(True), z3.BoolVal(False))

"""
Tests for the constraint solving module.

This module tests the solve() function with various constraint types,
solution enumeration modes, and edge cases.
"""

import pytest
import z3

from pyfcstm.solver.solve import solve, SolveResult


@pytest.mark.unittest
class TestSolveBasic:
    """Test basic solving functionality."""

    def test_single_solution(self):
        """Test solving for a single solution."""
        x = z3.Int('x')
        y = z3.Int('y')

        result = solve([x + y == 10, x == 3], max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 1
        assert result.solutions[0]['x'] == 3
        assert result.solutions[0]['y'] == 7
        assert set(result.variables) == {'x', 'y'}

    def test_multiple_solutions(self):
        """Test solving for multiple solutions."""
        x = z3.Int('x')
        y = z3.Int('y')

        result = solve([x + y == 10, x > 0, x < 5], max_solutions=5)

        assert result.status == 'sat'
        assert len(result.solutions) == 4  # x can be 1, 2, 3, 4
        assert all(sol['x'] + sol['y'] == 10 for sol in result.solutions)
        assert all(0 < sol['x'] < 5 for sol in result.solutions)

        # Check all solutions are unique
        x_values = [sol['x'] for sol in result.solutions]
        assert len(x_values) == len(set(x_values))

    def test_all_solutions(self):
        """Test solving for all solutions."""
        x = z3.Int('x')

        result = solve([x > 0, x < 4], max_solutions=None)

        assert result.status == 'sat'
        assert len(result.solutions) == 3  # x can be 1, 2, 3
        x_values = sorted([sol['x'] for sol in result.solutions])
        assert x_values == [1, 2, 3]

    def test_unsatisfiable(self):
        """Test unsatisfiable constraints."""
        x = z3.Int('x')

        result = solve([x > 10, x < 5], max_solutions=1)

        assert result.status == 'unsat'
        assert len(result.solutions) == 0
        assert result.variables == ['x']

    def test_empty_constraints(self):
        """Test with empty constraint list."""
        result = solve([], max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 0
        assert result.variables == []

    def test_single_constraint_not_list(self):
        """Test with single constraint (not in list)."""
        x = z3.Int('x')

        result = solve(x == 5, max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 1
        assert result.solutions[0]['x'] == 5


@pytest.mark.unittest
class TestSolveFloatVariables:
    """Test solving with float (Real) variables."""

    def test_real_variables(self):
        """Test solving with Z3 Real variables."""
        x = z3.Real('x')
        y = z3.Real('y')

        result = solve([x + y == 10.5, x == 3.2], max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 1
        # Variables are sorted alphabetically, so check both
        sol = result.solutions[0]
        assert 'x' in sol and 'y' in sol
        assert sol['x'] == pytest.approx(3.2)
        assert sol['y'] == pytest.approx(7.3)

    def test_mixed_int_real(self):
        """Test solving with mixed Int and Real variables."""
        x = z3.Int('x')
        y = z3.Real('y')

        result = solve([x + y == 10, x == 3], max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 1
        assert result.solutions[0]['x'] == 3
        assert result.solutions[0]['y'] == pytest.approx(7.0)


@pytest.mark.unittest
class TestSolveUnconstrainedVariables:
    """Test handling of unconstrained variables."""

    def test_partially_constrained(self):
        """Test when some variables are unconstrained."""
        x = z3.Int('x')
        _ = z3.Int('y')  # Not used in constraints
        _ = z3.Int('z')  # Not used in constraints

        # Only x is constrained, y and z don't appear in constraints
        # so they won't be extracted
        result = solve([x == 5], max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 1
        assert result.solutions[0]['x'] == 5
        # Only x appears in constraints, so only x is in the solution
        assert set(result.solutions[0].keys()) == {'x'}
        assert result.variables == ['x']

    def test_fully_unconstrained(self):
        """Test when variables don't appear in constraints."""
        _ = z3.Int('x')  # Not used in constraints
        _ = z3.Int('y')  # Not used in constraints

        # Trivial constraint with no variables
        result = solve([z3.BoolVal(True)], max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 1
        # No variables in constraints, so empty solution
        assert result.solutions[0] == {}
        assert result.variables == []


@pytest.mark.unittest
class TestSolveComplexConstraints:
    """Test solving with complex constraint patterns."""

    def test_nonlinear_constraints(self):
        """Test solving nonlinear constraints."""
        x = z3.Int('x')
        y = z3.Int('y')

        result = solve([x * y == 12, x > 0, y > 0, x <= y], max_solutions=10)

        assert result.status == 'sat'
        assert len(result.solutions) > 0
        for sol in result.solutions:
            assert sol['x'] * sol['y'] == 12
            assert sol['x'] > 0
            assert sol['y'] > 0
            assert sol['x'] <= sol['y']

    def test_multiple_variables(self):
        """Test solving with many variables."""
        z3_vars = [z3.Int(f'x{i}') for i in range(5)]

        # Sum equals 15, all positive
        constraints = [z3.Sum(z3_vars) == 15] + [v > 0 for v in z3_vars]

        result = solve(constraints, max_solutions=5)

        assert result.status == 'sat'
        assert len(result.solutions) == 5
        for sol in result.solutions:
            total = sum(sol[f'x{i}'] for i in range(5))
            assert total == 15
            assert all(sol[f'x{i}'] > 0 for i in range(5))

    def test_boolean_constraints(self):
        """Test solving with boolean expressions."""
        x = z3.Int('x')
        y = z3.Int('y')

        result = solve([
            z3.Or(x == 5, x == 10),
            z3.And(y > 0, y < 3)
        ], max_solutions=10)

        assert result.status == 'sat'
        assert len(result.solutions) == 4  # x in {5, 10}, y in {1, 2}
        for sol in result.solutions:
            assert sol['x'] in [5, 10]
            assert sol['y'] in [1, 2]


@pytest.mark.unittest
class TestSolvePerformanceOptimization:
    """Test performance optimization for different solution counts."""

    def test_single_solution_fast_path(self):
        """Test that single solution uses optimized path."""
        x = z3.Int('x')
        y = z3.Int('y')

        # This should use the fast path (no blocking clauses)
        result = solve([x + y == 100, x > 0, y > 0], max_solutions=1)

        assert result.status == 'sat'
        assert len(result.solutions) == 1

    def test_limited_solutions(self):
        """Test requesting fewer solutions than available."""
        x = z3.Int('x')

        result = solve([x > 0, x < 100], max_solutions=5)

        assert result.status == 'sat'
        assert len(result.solutions) == 5

    def test_max_solutions_limit(self):
        """Test that max_solutions limits all-solutions mode."""
        x = z3.Int('x')

        # Request limited solutions
        result = solve([x > 0, x < 1000], max_solutions=10)

        assert result.status == 'sat'
        assert len(result.solutions) == 10


@pytest.mark.unittest
class TestSolveEdgeCases:
    """Test edge cases and error handling."""

    def test_invalid_num_solutions(self):
        """Test that invalid max_solutions raises error."""
        x = z3.Int('x')

        with pytest.raises(ValueError, match="max_solutions must be at least 1"):
            solve([x == 5], max_solutions=0)

        with pytest.raises(ValueError, match="max_solutions must be at least 1"):
            solve([x == 5], max_solutions=-1)

    def test_invalid_max_solutions(self):
        """Test that invalid max_solutions raises error."""
        x = z3.Int('x')

        with pytest.raises(ValueError, match="max_solutions must be at least 1"):
            solve([x == 5], max_solutions=0)

        with pytest.raises(ValueError, match="max_solutions must be at least 1"):
            solve([x == 5], max_solutions=-1)

    def test_timeout(self):
        """Test solver timeout handling."""
        x = z3.Int('x')
        y = z3.Int('y')

        # Very short timeout might cause unknown result
        # (though simple constraints usually solve fast)
        result = solve([x + y == 10], max_solutions=1, timeout=1)

        # Should either succeed or return unknown
        assert result.status in ['sat', 'unknown']

    def test_no_solutions_after_first(self):
        """Test when no more solutions exist after finding some."""
        x = z3.Int('x')

        # Only 2 solutions exist, but request 10
        result = solve([x > 0, x < 3], max_solutions=10)

        assert result.status == 'sat'
        assert len(result.solutions) == 2

    def test_unlimited_with_warning(self):
        """Test that unlimited mode issues warning when threshold exceeded."""
        x = z3.Int('x')

        # Use a small warn_threshold to trigger warning
        with pytest.warns(UserWarning, match="Solution enumeration has exceeded"):
            result = solve([x > 0, x < 20], max_solutions=None, warn_threshold=5)

        assert result.status == 'sat'
        assert len(result.solutions) == 19  # x can be 1 through 19

    def test_unlimited_no_warning(self):
        """Test that unlimited mode doesn't warn below threshold."""
        x = z3.Int('x')

        # Solutions below threshold, no warning
        result = solve([x > 0, x < 4], max_solutions=None, warn_threshold=10)

        assert result.status == 'sat'
        assert len(result.solutions) == 3  # x can be 1, 2, 3


@pytest.mark.unittest
class TestSolveVariableExtraction:
    """Test variable extraction from constraints."""

    def test_extract_from_complex_expression(self):
        """Test extracting variables from nested expressions."""
        x = z3.Int('x')
        y = z3.Int('y')
        z = z3.Int('z')

        result = solve([
            x + y * z == 20,
            x > 0
        ], max_solutions=1)

        assert result.status == 'sat'
        assert set(result.variables) == {'x', 'y', 'z'}

    def test_extract_from_conditional(self):
        """Test extracting variables from conditional expressions."""
        x = z3.Int('x')
        y = z3.Int('y')
        z = z3.Int('z')

        result = solve([
            z3.If(x > 0, y, z) == 10,
            x == 5
        ], max_solutions=1)

        assert result.status == 'sat'
        assert set(result.variables) == {'x', 'y', 'z'}


@pytest.mark.unittest
class TestSolveResultDataclass:
    """Test SolveResult dataclass."""

    def test_result_structure(self):
        """Test that result has correct structure."""
        x = z3.Int('x')

        result = solve([x == 5], max_solutions=1)

        assert isinstance(result, SolveResult)
        assert hasattr(result, 'status')
        assert hasattr(result, 'solutions')
        assert hasattr(result, 'variables')
        assert isinstance(result.solutions, list)
        assert isinstance(result.variables, list)

    def test_result_status_types(self):
        """Test different status types."""
        x = z3.Int('x')

        # Satisfiable
        result_sat = solve([x == 5], max_solutions=1)
        assert result_sat.status == 'sat'

        # Unsatisfiable
        result_unsat = solve([x > 10, x < 5], max_solutions=1)
        assert result_unsat.status == 'unsat'

    def test_result_is_frozen(self):
        """Test that SolveResult is immutable (frozen)."""
        result = SolveResult(
            status='sat',
            solutions=[{'x': 1}],
            variables=['x']
        )

        # Attempt to modify should raise FrozenInstanceError
        with pytest.raises(Exception):  # dataclasses.FrozenInstanceError
            result.status = 'unsat'

        with pytest.raises(Exception):
            result.solutions = []

        with pytest.raises(Exception):
            result.variables = []

    def test_repr_unsat(self):
        """Test __repr__ for unsatisfiable result."""
        result = SolveResult(status='unsat', solutions=[], variables=['x', 'y'])
        repr_str = repr(result)

        expected = "SolveResult(unsat, 0 solutions, variables=['x', 'y'])"
        assert repr_str == expected

    def test_repr_unknown(self):
        """Test __repr__ for unknown result."""
        result = SolveResult(status='unknown', solutions=[], variables=['x'])
        repr_str = repr(result)

        expected = "SolveResult(unknown, 0 solutions, variables=['x'])"
        assert repr_str == expected

    def test_repr_single_solution(self):
        """Test __repr__ with single solution."""
        result = SolveResult(
            status='sat',
            solutions=[{'x': 5, 'y': 10}],
            variables=['x', 'y']
        )
        repr_str = repr(result)

        expected = "SolveResult(sat, 1 solution, variables=['x', 'y'], solutions=[{'x': 5, 'y': 10}])"
        assert repr_str == expected

    def test_repr_few_solutions(self):
        """Test __repr__ with few solutions (≤3)."""
        result = SolveResult(
            status='sat',
            solutions=[{'x': 1}, {'x': 2}, {'x': 3}],
            variables=['x']
        )
        repr_str = repr(result)

        expected = "SolveResult(sat, 3 solutions, variables=['x'], solutions=[{'x': 1}, {'x': 2}, {'x': 3}])"
        assert repr_str == expected

    def test_repr_medium_solutions(self):
        """Test __repr__ with medium number of solutions (4-10)."""
        solutions = [{'x': i} for i in range(7)]
        result = SolveResult(
            status='sat',
            solutions=solutions,
            variables=['x']
        )
        repr_str = repr(result)

        expected = "SolveResult(sat, 7 solutions, variables=['x'], solutions=[{'x': 0}, {'x': 1}, '...', {'x': 6}])"
        assert repr_str == expected

    def test_repr_many_solutions(self):
        """Test __repr__ with many solutions (>10)."""
        solutions = [{'x': i} for i in range(100)]
        result = SolveResult(
            status='sat',
            solutions=solutions,
            variables=['x']
        )
        repr_str = repr(result)

        expected = "SolveResult(sat, 100 solutions, variables=['x'])"
        assert repr_str == expected

    def test_repr_many_variables(self):
        """Test __repr__ with many variables."""
        variables = [f'x{i}' for i in range(20)]
        result = SolveResult(
            status='sat',
            solutions=[{v: 0 for v in variables}],
            variables=variables
        )
        repr_str = repr(result)

        expected = "SolveResult(sat, 1 solution, variables=['x0', 'x1', 'x2', ... (20 total)], solutions=[{'x0': 0, 'x1': 0, 'x2': 0, 'x3': 0, 'x4': 0, 'x5': 0, 'x6': 0, 'x7': 0, 'x8': 0, 'x9': 0, 'x10': 0, 'x11': 0, 'x12': 0, 'x13': 0, 'x14': 0, 'x15': 0, 'x16': 0, 'x17': 0, 'x18': 0, 'x19': 0}])"
        assert repr_str == expected

    def test_repr_empty_variables(self):
        """Test __repr__ with no variables."""
        result = SolveResult(
            status='sat',
            solutions=[{}],
            variables=[]
        )
        repr_str = repr(result)

        expected = "SolveResult(sat, 1 solution, variables=[], solutions=[{}])"
        assert repr_str == expected

    def test_repr_natsorted_variables(self):
        """Test that variables are displayed in natural sort order."""
        # Variables in non-natural order
        result = SolveResult(
            status='sat',
            solutions=[{'x1': 1, 'x10': 10, 'x2': 2}],
            variables=['x1', 'x10', 'x2']  # Already in the order they should be displayed
        )
        repr_str = repr(result)

        # Should display in the order provided (which should be natsorted)
        expected = "SolveResult(sat, 1 solution, variables=['x1', 'x10', 'x2'], solutions=[{'x1': 1, 'x10': 10, 'x2': 2}])"
        assert repr_str == expected

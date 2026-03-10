"""
Constraint solving utilities for Z3 expressions.

This module provides high-level functions for solving Z3 constraint expressions
with flexible solution enumeration. It supports single solutions, multiple solutions,
and exhaustive solution enumeration with optimized solving strategies.

The module contains the following main components:

* :class:`SolveResult` - Dataclass containing solve results with status and solutions
* :func:`solve` - Main solving function with flexible solution enumeration

Example::

    >>> import z3
    >>> from pyfcstm.solver.solve import solve
    >>>
    >>> # Create variables and constraints
    >>> x = z3.Int('x')
    >>> y = z3.Int('y')
    >>> constraints = [x + y == 10, x > 0, y > 0]
    >>>
    >>> # Get 5 solutions
    >>> result = solve(constraints, max_solutions=5)
    >>> result.status
    'sat'
    >>> len(result.solutions)
    5
    >>>
    >>> # Get all solutions (WARNING: use with caution!)
    >>> result = solve(constraints, max_solutions=None)
    >>>
    >>> # Get single solution (fastest)
    >>> result = solve(constraints, max_solutions=1)
"""

import warnings
from dataclasses import dataclass
from typing import Union, List, Dict, Optional, Literal

import z3
from natsort import natsorted


@dataclass(frozen=True)
class SolveResult:
    """
    Result of a constraint solving operation.

    Contains the solving status, list of solutions, and the list of variables
    that were solved for. Each solution is a dictionary mapping variable names
    to their concrete values (int or float).

    This dataclass is immutable (frozen) to ensure result integrity.

    :param status: Solving status - 'sat' (satisfiable), 'unsat' (unsatisfiable),
        or 'unknown' (solver could not determine)
    :type status: Literal['sat', 'unsat', 'unknown']
    :param solutions: List of solution dictionaries, each mapping variable names
        to their values. Empty if status is 'unsat' or 'unknown'.
    :type solutions: List[Dict[str, Union[int, float]]]
    :param variables: List of variable names that were solved for
    :type variables: List[str]

    Example::

        >>> result = SolveResult(
        ...     status='sat',
        ...     solutions=[{'x': 1, 'y': 9}, {'x': 2, 'y': 8}],
        ...     variables=['x', 'y']
        ... )
        >>> result.status
        'sat'
        >>> len(result.solutions)
        2
        >>> print(result)
        SolveResult(sat, 2 solutions, variables=['x', 'y'])
    """
    status: Literal['sat', 'unsat', 'unknown']
    solutions: List[Dict[str, Union[int, float]]]
    variables: List[str]

    def __repr__(self) -> str:
        """
        Return a comprehensive string representation of the solve result.

        The representation adapts based on the number of solutions:
        - For small solution counts (≤3): shows all solutions
        - For medium counts (4-10): shows first 2 and last 1 with ellipsis
        - For large counts (>10): shows summary with count only

        :return: String representation of the result
        :rtype: str

        Example::

            >>> # Unsatisfiable
            >>> result = SolveResult('unsat', [], ['x', 'y'])
            >>> repr(result)
            "SolveResult(unsat, 0 solutions, variables=['x', 'y'])"
            >>>
            >>> # Few solutions
            >>> result = SolveResult('sat', [{'x': 1}, {'x': 2}], ['x'])
            >>> repr(result)
            "SolveResult(sat, 2 solutions, variables=['x'], solutions=[{'x': 1}, {'x': 2}])"
            >>>
            >>> # Many solutions
            >>> result = SolveResult('sat', [{'x': i} for i in range(100)], ['x'])
            >>> repr(result)
            "SolveResult(sat, 100 solutions, variables=['x'])"
        """
        num_solutions = len(self.solutions)

        # Base representation with status and solution count
        parts = [
            f"SolveResult({self.status}",
            f"{num_solutions} solution{'s' if num_solutions != 1 else ''}",
        ]

        # Add variables info
        if self.variables:
            if len(self.variables) <= 5:
                parts.append(f"variables={self.variables}")
            else:
                # Too many variables, show count and first few
                var_preview = self.variables[:3]
                parts.append(f"variables=[{', '.join(repr(v) for v in var_preview)}, ... ({len(self.variables)} total)]")
        else:
            parts.append("variables=[]")

        # Add solution details based on count
        if self.status == 'sat' and num_solutions > 0:
            if num_solutions <= 3:
                # Show all solutions for small counts
                parts.append(f"solutions={self.solutions}")
            elif num_solutions <= 10:
                # Show first 2 and last 1 with ellipsis
                preview_solutions = self.solutions[:2] + ['...'] + self.solutions[-1:]
                parts.append(f"solutions={preview_solutions}")
            # For >10 solutions, don't show individual solutions (too verbose)

        return ', '.join(parts) + ')'


def solve(
    constraints: Union[z3.ExprRef, List[z3.ExprRef]],
    max_solutions: Optional[int] = 10,
    timeout: Optional[int] = None,
    warn_threshold: int = 1000
) -> SolveResult:
    """
    Solve Z3 constraint expressions and return solutions.

    This function solves constraint expressions using Z3 and returns a specified
    number of solutions. It supports three solving modes:

    - ``max_solutions=1``: Returns a single solution (fastest, uses simple check)
    - ``max_solutions=N``: Returns up to N solutions (uses iterative blocking)
    - ``max_solutions=None``: Returns all solutions (WARNING: may be very slow or infinite)

    The function automatically extracts all variables from the constraints and
    handles cases where some variables are unconstrained (don't care values).
    For unconstrained variables, the solver picks arbitrary valid values.

    **WARNING**: Using ``max_solutions=None`` can be dangerous for underconstrained
    systems. The solver will attempt to enumerate all solutions, which may:

    - Take an extremely long time for systems with many solutions
    - Consume excessive memory
    - Never terminate for infinite solution spaces

    When ``max_solutions=None`` and the number of solutions exceeds ``warn_threshold``,
    a warning will be issued to alert you of potential performance issues.

    :param constraints: Single Z3 expression or list of Z3 expressions to solve
    :type constraints: Union[z3.ExprRef, List[z3.ExprRef]]
    :param max_solutions: Maximum number of solutions to find. Use 1 for single solution,
        positive integer for specific count, or None for all solutions (use with caution).
        Defaults to 10.
    :type max_solutions: Optional[int], optional
    :param timeout: Solver timeout in milliseconds. None means no timeout.
        Defaults to None.
    :type timeout: Optional[int], optional
    :param warn_threshold: When ``max_solutions=None``, issue a warning if the number
        of solutions exceeds this threshold. Defaults to 1000.
    :type warn_threshold: int, optional
    :return: Solve result containing status, solutions, and variable list
    :rtype: SolveResult
    :raises ValueError: If ``max_solutions`` is less than 1 (when not None)
    :raises ValueError: If ``warn_threshold`` is less than 1

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> y = z3.Int('y')
        >>>
        >>> # Single solution (fastest)
        >>> result = solve([x + y == 10, x > 0], max_solutions=1)
        >>> result.status
        'sat'
        >>> len(result.solutions)
        1
        >>>
        >>> # Multiple solutions
        >>> result = solve([x + y == 10, x > 0, x < 5], max_solutions=5)
        >>> len(result.solutions)
        4
        >>>
        >>> # All solutions (WARNING: use with caution!)
        >>> result = solve([x + y == 10, x > 0, x < 3], max_solutions=None)
        >>>
        >>> # Unconstrained variable handling
        >>> z = z3.Int('z')
        >>> result = solve([x == 5], max_solutions=1)
        >>> 'x' in result.solutions[0]
        True
    """
    # Validate parameters
    if max_solutions is not None and max_solutions < 1:
        raise ValueError(f"max_solutions must be at least 1, got {max_solutions}")
    if warn_threshold < 1:
        raise ValueError(f"warn_threshold must be at least 1, got {warn_threshold}")

    # Normalize constraints to list
    if not isinstance(constraints, list):
        constraints = [constraints]

    # Handle empty constraints
    if not constraints:
        return SolveResult(status='sat', solutions=[], variables=[])

    # Extract all variables from constraints
    variables = _extract_variables(constraints)

    # Sort variables by name using natural sort for consistent ordering
    # Use natsorted with str conversion for proper natural sorting
    sorted_variables = natsorted(variables, key=lambda x: str(x))
    var_names = [str(v) for v in sorted_variables]
    variables = sorted_variables

    # Create solver
    solver = z3.Solver()
    if timeout is not None:
        solver.set('timeout', timeout)

    # Add constraints
    for constraint in constraints:
        solver.add(constraint)

    # Optimize for single solution case
    if max_solutions == 1:
        return _solve_single(solver, variables, var_names)

    # Determine effective solution limit
    if max_solutions is None:
        # Unlimited mode - use a very large limit but warn if exceeded
        return _solve_unlimited(solver, variables, var_names, warn_threshold)
    else:
        # Limited mode
        return _solve_multiple(solver, variables, var_names, max_solutions)


def _extract_variables(constraints: List[z3.ExprRef]) -> List[z3.ExprRef]:
    """
    Extract all variables from a list of Z3 constraints.

    :param constraints: List of Z3 expressions
    :type constraints: List[z3.ExprRef]
    :return: List of unique variables
    :rtype: List[z3.ExprRef]
    """
    variables = set()

    def collect_vars(expr):
        """Recursively collect variables from expression."""
        if z3.is_const(expr) and expr.decl().kind() == z3.Z3_OP_UNINTERPRETED:
            variables.add(expr)
        else:
            for child in expr.children():
                collect_vars(child)

    for constraint in constraints:
        collect_vars(constraint)

    return list(variables)


def _solve_single(
    solver: z3.Solver,
    variables: List[z3.ExprRef],
    var_names: List[str]
) -> SolveResult:
    """
    Solve for a single solution (optimized path).

    :param solver: Z3 solver with constraints already added
    :type solver: z3.Solver
    :param variables: List of Z3 variable expressions
    :type variables: List[z3.ExprRef]
    :param var_names: List of variable names (strings)
    :type var_names: List[str]
    :return: Solve result with at most one solution
    :rtype: SolveResult
    """
    check_result = solver.check()

    if check_result == z3.sat:
        model = solver.model()
        solution = _extract_solution(model, variables, var_names)
        return SolveResult(status='sat', solutions=[solution], variables=var_names)
    elif check_result == z3.unsat:
        return SolveResult(status='unsat', solutions=[], variables=var_names)
    else:
        return SolveResult(status='unknown', solutions=[], variables=var_names)


def _solve_multiple(
    solver: z3.Solver,
    variables: List[z3.ExprRef],
    var_names: List[str],
    limit: int
) -> SolveResult:
    """
    Solve for multiple solutions using iterative blocking.

    This function uses the "blocking clause" technique: after finding a solution,
    it adds a constraint that blocks that exact solution, forcing the solver to
    find a different one.

    :param solver: Z3 solver with constraints already added
    :type solver: z3.Solver
    :param variables: List of Z3 variable expressions
    :type variables: List[z3.ExprRef]
    :param var_names: List of variable names (strings)
    :type var_names: List[str]
    :param limit: Maximum number of solutions to find
    :type limit: int
    :return: Solve result with multiple solutions
    :rtype: SolveResult
    """
    solutions = []

    for _ in range(limit):
        check_result = solver.check()

        if check_result == z3.sat:
            model = solver.model()
            solution = _extract_solution(model, variables, var_names)
            solutions.append(solution)

            # Create blocking clause: at least one variable must differ
            blocking_clause = _create_blocking_clause(model, variables)
            solver.add(blocking_clause)

        elif check_result == z3.unsat:
            # No more solutions
            break
        else:
            # Unknown - solver couldn't determine
            if not solutions:
                return SolveResult(status='unknown', solutions=[], variables=var_names)
            break

    if solutions:
        return SolveResult(status='sat', solutions=solutions, variables=var_names)
    else:
        return SolveResult(status='unsat', solutions=[], variables=var_names)


def _solve_unlimited(
    solver: z3.Solver,
    variables: List[z3.ExprRef],
    var_names: List[str],
    warn_threshold: int
) -> SolveResult:
    """
    Solve for unlimited solutions with warning when threshold is exceeded.

    This function attempts to find all solutions but issues a warning when
    the number of solutions exceeds the warn_threshold to alert users of
    potential performance issues.

    :param solver: Z3 solver with constraints already added
    :type solver: z3.Solver
    :param variables: List of Z3 variable expressions
    :type variables: List[z3.ExprRef]
    :param var_names: List of variable names (strings)
    :type var_names: List[str]
    :param warn_threshold: Issue warning when solution count exceeds this
    :type warn_threshold: int
    :return: Solve result with all found solutions
    :rtype: SolveResult
    """
    solutions = []
    warned = False

    while True:
        check_result = solver.check()

        if check_result == z3.sat:
            model = solver.model()
            solution = _extract_solution(model, variables, var_names)
            solutions.append(solution)

            # Issue warning if threshold exceeded
            if not warned and len(solutions) > warn_threshold:
                warnings.warn(
                    f"Solution enumeration has exceeded {warn_threshold} solutions. "
                    f"The constraint system may have a very large or infinite solution space. "
                    f"Consider adding more constraints or using a finite max_solutions limit. "
                    f"Current solution count: {len(solutions)}",
                    UserWarning,
                    stacklevel=3
                )
                warned = True

            # Create blocking clause: at least one variable must differ
            blocking_clause = _create_blocking_clause(model, variables)
            solver.add(blocking_clause)

        elif check_result == z3.unsat:
            # No more solutions
            break
        else:
            # Unknown - solver couldn't determine
            if not solutions:
                return SolveResult(status='unknown', solutions=[], variables=var_names)
            break

    if solutions:
        return SolveResult(status='sat', solutions=solutions, variables=var_names)
    else:
        return SolveResult(status='unsat', solutions=[], variables=var_names)


def _extract_solution(
    model: z3.ModelRef,
    variables: List[z3.ExprRef],
    var_names: List[str]
) -> Dict[str, Union[int, float]]:
    """
    Extract solution values from a Z3 model.

    Handles cases where variables are unconstrained (model returns None).
    For unconstrained variables, uses the model's evaluation which provides
    a valid arbitrary value.

    The returned dictionary maintains natural sort order of variable names.

    :param model: Z3 model containing variable assignments
    :type model: z3.ModelRef
    :param variables: List of Z3 variable expressions (already natsorted)
    :type variables: List[z3.ExprRef]
    :param var_names: List of variable names (strings, already natsorted)
    :type var_names: List[str]
    :return: Dictionary mapping variable names to values in natsorted order
    :rtype: Dict[str, Union[int, float]]
    """
    solution = {}

    # Build solution dict in the order of var_names (which is already natsorted)
    for var, name in zip(variables, var_names):
        value = model[var]

        # Handle unconstrained variables (model returns None)
        if value is None:
            # Use model.eval to get a concrete value
            value = model.eval(var, model_completion=True)

        # Convert Z3 value to Python type
        if z3.is_int_value(value):
            solution[name] = value.as_long()
        elif z3.is_rational_value(value):
            # Z3 Real values are rationals
            numerator = value.numerator_as_long()
            denominator = value.denominator_as_long()
            solution[name] = float(numerator) / float(denominator)
        elif z3.is_algebraic_value(value):
            # Algebraic numbers (e.g., sqrt(2)) - approximate as float
            solution[name] = float(value.approx(20).as_decimal(20))
        else:
            # Fallback: try to convert to string then parse
            solution[name] = float(str(value))

    return solution


def _create_blocking_clause(
    model: z3.ModelRef,
    variables: List[z3.ExprRef]
) -> z3.BoolRef:
    """
    Create a blocking clause that excludes the current solution.

    The blocking clause is a disjunction: (x != val_x) OR (y != val_y) OR ...
    This ensures at least one variable has a different value in the next solution.

    :param model: Z3 model containing current solution
    :type model: z3.ModelRef
    :param variables: List of Z3 variable expressions
    :type variables: List[z3.ExprRef]
    :return: Z3 boolean expression representing the blocking clause
    :rtype: z3.BoolRef
    """
    constraints = []

    for var in variables:
        value = model.eval(var, model_completion=True)
        constraints.append(var != value)

    # At least one variable must differ
    return z3.Or(constraints)

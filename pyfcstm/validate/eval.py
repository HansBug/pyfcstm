"""
Module for evaluating Z3 expressions with given variable values.

This module provides functionality to evaluate Z3 expressions by substituting
variables with concrete values and solving the resulting constraints.
"""

from typing import Dict, Union

import z3

from .solve import z3_to_python


def z3_evaluate(expr: z3.ExprRef, variables: Dict[str, z3.ExprRef], values: Dict[str, Union[int, float, None]]):
    """
    Evaluate a Z3 expression with given variable assignments.

    This function evaluates a Z3 expression by creating a solver, adding constraints
    that bind each variable to its corresponding value, and then evaluating the
    expression under the resulting model. None values are treated as 0.

    :param expr: The Z3 expression to evaluate.
    :type expr: z3.ExprRef
    :param variables: A dictionary mapping variable names to their Z3 expression references.
    :type variables: Dict[str, z3.ExprRef]
    :param values: A dictionary mapping variable names to their concrete values.
                   None values will be converted to 0.
    :type values: Dict[str, Union[int, float, None]]

    :return: The evaluated result converted to a Python native type.
    :rtype: Union[int, float, bool, str]

    :raises AssertionError: If the solver cannot find a satisfying assignment (should not
                           occur with valid inputs as we're just assigning concrete values).

    Example::
        >>> import z3
        >>> x = z3.Int('x')
        >>> y = z3.Int('y')
        >>> expr = x + y * 2
        >>> variables = {'x': x, 'y': y}
        >>> values = {'x': 5, 'y': 3}
        >>> z3_evaluate(expr, variables, values)
        11
    """
    values = {key: (value if value is not None else 0) for key, value in values.items()}
    solver = z3.Solver()
    for name in variables.keys():
        solver.add(variables[name] == values[name])

    assert solver.check() == z3.sat
    model = solver.model()
    return z3_to_python(model.evaluate(expr))

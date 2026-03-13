"""
Logical helper utilities for Z3 boolean expressions.

This module provides small, solver-oriented helpers for combining boolean
expressions and answering common satisfiability questions. The combination
helpers keep the input expressions intact and only wrap them with the thinnest
useful Z3 logical constructor.

The module contains the following main components:

* :func:`z3_or` - Build an n-ary logical OR from boolean expressions
* :func:`z3_and` - Build an n-ary logical AND from boolean expressions
* :func:`is_satisfiable` - Check whether a boolean expression is satisfiable
* :func:`contributes_to_solution_space` - Check whether ``y`` adds solutions beyond ``x``
* :func:`are_equivalent` - Check whether two boolean expressions are equivalent

Example::

    >>> import z3
    >>> from pyfcstm.solver.logic import z3_or, is_satisfiable, are_equivalent
    >>> x = z3.Int('x')
    >>> expr = z3_or([x == 1, x == 2])
    >>> is_satisfiable(expr)
    True
    >>> are_equivalent(x > 0, x >= 1)
    True
"""

from typing import List

import z3


def z3_or(expressions: List[z3.BoolRef]) -> z3.BoolRef:
    """
    Build a logical OR from a list of boolean expressions.

    For solver friendliness, this function avoids creating unnecessary wrapper
    nodes for the most common degenerate cases:

    - Empty list: returns ``False``
    - Single expression: returns that expression directly
    - Multiple expressions: returns ``z3.Or(*expressions)``

    The input expressions themselves are not rewritten, flattened, or
    simplified.

    :param expressions: Boolean expressions to combine
    :type expressions: List[z3.BoolRef]
    :return: Combined OR expression
    :rtype: z3.BoolRef

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> expr = z3_or([x == 1, x == 2])
        >>> isinstance(expr, z3.BoolRef)
        True
    """
    if not expressions:
        return z3.BoolVal(False)
    if len(expressions) == 1:
        return expressions[0]
    return z3.Or(*expressions)


def z3_and(expressions: List[z3.BoolRef]) -> z3.BoolRef:
    """
    Build a logical AND from a list of boolean expressions.

    For solver friendliness, this function avoids creating unnecessary wrapper
    nodes for the most common degenerate cases:

    - Empty list: returns ``True``
    - Single expression: returns that expression directly
    - Multiple expressions: returns ``z3.And(*expressions)``

    The input expressions themselves are not rewritten, flattened, or
    simplified.

    :param expressions: Boolean expressions to combine
    :type expressions: List[z3.BoolRef]
    :return: Combined AND expression
    :rtype: z3.BoolRef

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> expr = z3_and([x > 0, x < 3])
        >>> isinstance(expr, z3.BoolRef)
        True
    """
    if not expressions:
        return z3.BoolVal(True)
    if len(expressions) == 1:
        return expressions[0]
    return z3.And(*expressions)


def _check_sat(*constraints: z3.BoolRef) -> z3.CheckSatResult:
    """
    Check satisfiability of boolean constraints with a fresh solver.

    :param constraints: Boolean constraints to assert into the solver
    :type constraints: z3.BoolRef
    :return: Z3 satisfiability result
    :rtype: z3.CheckSatResult
    """
    solver = z3.Solver()
    solver.add(*constraints)
    return solver.check()


def is_satisfiable(expr: z3.BoolRef) -> bool:
    """
    Check whether a boolean expression has a satisfying assignment.

    This function returns ``True`` only when Z3 reports ``sat``. If Z3 reports
    ``unsat`` or ``unknown``, the function returns ``False``.

    :param expr: Boolean expression to check
    :type expr: z3.BoolRef
    :return: ``True`` if the expression is satisfiable, otherwise ``False``
    :rtype: bool

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> is_satisfiable(x > 0)
        True
    """
    return _check_sat(expr) == z3.sat


def contributes_to_solution_space(x: z3.BoolRef, y: z3.BoolRef) -> bool:
    """
    Check whether ``y`` contributes new solutions beyond ``x``.

    This answers whether there exists a model satisfying ``(!x) && y``. In
    other words, if one were to replace ``x`` with ``x || y``, this function
    checks whether ``y`` expands the solution space.

    This function returns ``True`` only when Z3 reports ``sat``. If Z3 reports
    ``unsat`` or ``unknown``, the function returns ``False``.

    :param x: Existing boolean expression
    :type x: z3.BoolRef
    :param y: Candidate boolean expression to add
    :type y: z3.BoolRef
    :return: ``True`` if ``y`` adds new solutions beyond ``x``, otherwise ``False``
    :rtype: bool

    Example::

        >>> import z3
        >>> v = z3.Int('v')
        >>> contributes_to_solution_space(v == 1, v == 2)
        True
    """
    return _check_sat(z3.Not(x), y) == z3.sat


def are_equivalent(x: z3.BoolRef, y: z3.BoolRef) -> bool:
    """
    Check whether two boolean expressions are logically equivalent.

    The equivalence check is solved by checking satisfiability of the symmetric
    difference between ``x`` and ``y``. For solver efficiency, the symmetric
    difference is encoded as ``x != y``, which is logically equivalent to
    ``(!x && y) || (!y && x)`` for boolean expressions.

    This function returns ``True`` only when Z3 proves the symmetric difference
    unsatisfiable. If Z3 reports ``sat`` or ``unknown``, the function returns
    ``False``.

    :param x: First boolean expression
    :type x: z3.BoolRef
    :param y: Second boolean expression
    :type y: z3.BoolRef
    :return: ``True`` if the expressions are equivalent, otherwise ``False``
    :rtype: bool

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> are_equivalent(x > 0, x >= 1)
        True
    """
    return _check_sat(x != y) == z3.unsat

"""
Z3-based solving helpers for pyfcstm models and expressions.

This package groups the main solver-facing entry points used by the project:
expression translation, reverse conversion from Z3 back into model
expressions, variable creation, logical relation checks, symbolic operation
execution, direct constraint solving, and lightweight substitution over Z3
expression trees.

The package exports:

* :func:`expr_to_z3` - Convert pyfcstm expressions to Z3 expressions.
* :func:`z3_to_expr` - Convert Z3 expressions back to pyfcstm expressions.
* :func:`create_z3_vars_from_state_machine` - Create Z3 variables from a state machine.
* :func:`create_z3_vars_from_models` - Create Z3 variables from model objects.
* :func:`z3_or` - Combine boolean expressions with logical OR.
* :func:`z3_and` - Combine boolean expressions with logical AND.
* :func:`z3_not` - Negate a boolean expression.
* :func:`is_satisfiable` - Check whether a boolean expression is satisfiable.
* :func:`contributes_to_solution_space` - Check whether one expression adds new solutions to another.
* :func:`are_equivalent` - Check whether two boolean expressions are logically equivalent.
* :func:`solve` - Solve Z3 constraint expressions with flexible solution enumeration.
* :class:`SolveResult` - Dataclass containing solve results.
* :func:`substitute_and_literalize` - Substitute named values into Z3 trees and fold grounded subexpressions.
* :func:`parse_operations` - Parse DSL operation code into operations for symbolic execution.
* :func:`execute_operations` - Execute operations on Z3 variable-expression mappings.

Example::

    >>> import z3
    >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
    >>> from pyfcstm.solver import expr_to_z3, solve, substitute_and_literalize
    >>> x = z3.Int('x')
    >>> y = z3.Int('y')
    >>> expr = BinaryOp(x=Variable('x'), op='+', y=Integer(5))
    >>> z3_expr = expr_to_z3(expr, {'x': x})
    >>> solve([z3_expr == 10, y > 0], max_solutions=1).status
    'sat'
    >>> substitute_and_literalize(x + y + 2, {'x': 3})
    y + 5
"""

from .expr import expr_to_z3, create_z3_vars_from_models
from .logic import (
    z3_or,
    z3_and,
    z3_not,
    is_satisfiable,
    contributes_to_solution_space,
    are_equivalent,
)
from .operation import parse_operations, execute_operations
from .reverse_expr import z3_to_expr
from .solve import solve, SolveResult
from .substitute import substitute_and_literalize
from .vars import create_z3_vars_from_state_machine

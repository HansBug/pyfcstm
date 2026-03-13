"""
Z3 solver integration for pyfcstm expressions.

This module provides utilities for converting pyfcstm expression objects
to Z3 solver expressions, enabling constraint solving and symbolic execution
capabilities for state machine models.

The module contains the following main components:

* :func:`expr_to_z3` - Convert pyfcstm expressions to Z3 expressions
* :func:`z3_to_expr` - Convert Z3 expressions back to pyfcstm expressions
* :func:`create_z3_vars_from_state_machine` - Create Z3 variables from a state machine
* :func:`create_z3_vars_from_models` - Create Z3 variables from model objects
* :func:`z3_or` - Combine boolean expressions with logical OR
* :func:`z3_and` - Combine boolean expressions with logical AND
* :func:`z3_not` - Negate a boolean expression
* :func:`is_satisfiable` - Check whether a boolean expression is satisfiable
* :func:`contributes_to_solution_space` - Check whether one expression adds new solutions to another
* :func:`are_equivalent` - Check whether two boolean expressions are logically equivalent
* :func:`solve` - Solve Z3 constraint expressions with flexible solution enumeration
* :class:`SolveResult` - Dataclass containing solve results
* :func:`parse_operations` - Parse DSL operation code string to list of Operations
* :func:`execute_operations` - Execute operations on Z3 variable expression dictionary (symbolic execution)

Example::

    >>> from pyfcstm.solver import expr_to_z3, create_z3_vars_from_models, solve
    >>> from pyfcstm.model.expr import Variable, Integer, BinaryOp
    >>> import z3
    >>>
    >>> # Create Z3 variables
    >>> z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
    >>>
    >>> # Convert expression to Z3
    >>> expr = BinaryOp(x=Variable('x'), op='+', y=Integer(5))
    >>> z3_expr = expr_to_z3(expr, z3_vars)
    >>>
    >>> # Solve constraints
    >>> result = solve([z3_expr == 10, z3_vars['y'] > 0], max_solutions=5)
    >>> result.status
    'sat'
    >>>
    >>> # Parse and execute operations symbolically
    >>> from pyfcstm.solver import parse_operations, execute_operations
    >>> ops = parse_operations("x = x + 2; y = y + x;", allowed_vars=['x', 'y'])
    >>> x, y = z3.Int('x'), z3.Int('y')
    >>> var_exprs = {'x': x, 'y': y}
    >>> new_exprs = execute_operations(ops, var_exprs)
    >>> # new_exprs['x'] is: x + 2
    >>> # new_exprs['y'] is: y + (x + 2)
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
from .vars import create_z3_vars_from_state_machine

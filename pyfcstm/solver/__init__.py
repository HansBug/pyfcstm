"""
Z3 solver integration for pyfcstm expressions.

This module provides utilities for converting pyfcstm expression objects
to Z3 solver expressions, enabling constraint solving and symbolic execution
capabilities for state machine models.

The module contains the following main components:

* :func:`expr_to_z3` - Convert pyfcstm expressions to Z3 expressions
* :func:`create_z3_vars_from_models` - Create Z3 variables from model objects
* :func:`solve` - Solve Z3 constraint expressions with flexible solution enumeration
* :class:`SolveResult` - Dataclass containing solve results

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
"""

from .expr import expr_to_z3, create_z3_vars_from_models
from .solve import solve, SolveResult

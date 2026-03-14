"""
Operation parsing and execution utilities for Z3 solver integration.

This module provides functions to parse DSL operation code strings into
Operation objects and execute operations on Z3 variable dictionaries.

The module contains the following main components:

* :func:`parse_operations` - Parse DSL operation code string to list of Operations
* :func:`execute_operations` - Execute operations on Z3 variable dictionary

Example::

    >>> from pyfcstm.solver.operation import parse_operations, execute_operations
    >>> import z3
    >>>
    >>> # Parse operations from DSL string
    >>> ops = parse_operations("x = x + 1; y = x * 2;", allowed_vars=['x', 'y'])
    >>>
    >>> # Execute operations on Z3 variables
    >>> z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
    >>> z3_state = {'x': z3.IntVal(5), 'y': z3.IntVal(0)}
    >>> new_state = execute_operations(ops, z3_state, z3_vars)
    >>> # new_state['x'] represents the Z3 expression: 5 + 1
    >>> # new_state['y'] represents the Z3 expression: (5 + 1) * 2
"""

from typing import List, Dict, Optional, Union

import z3

from .expr import expr_to_z3
from ..dsl.parse import parse_with_grammar_entry
from ..model.expr import parse_expr_node_to_expr
from ..model.model import Operation


def parse_operations(
    code: str,
    allowed_vars: Optional[List[str]] = None
) -> List[Operation]:
    """
    Parse DSL operation code string into a list of Operation objects.

    This function parses a DSL code string containing operation statements
    (variable assignments) and converts them into Operation objects. It can
    optionally validate that expressions only reference variables that are
    already available at that point in the block. Unknown assignment targets
    are treated as block-local temporary variables.

    :param code: DSL operation code string to parse
    :type code: str
    :param allowed_vars: List of initially available variable names, or ``None`` for free mode
    :type allowed_vars: Optional[List[str]]
    :return: List of parsed Operation objects
    :rtype: List[Operation]
    :raises ValueError: If an expression references a variable that is not yet available
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails

    Example::

        >>> ops = parse_operations("x = x + 1; y = 10;", allowed_vars=['x', 'y'])
        >>> len(ops)
        2
        >>> ops[0].var_name
        'x'

        >>> # Free mode - no variable restrictions
        >>> ops = parse_operations("a = b + c;", allowed_vars=None)

        >>> # Restricted mode - raises ValueError for variables used before assignment
        >>> ops = parse_operations("y = z + 1; z = 1;", allowed_vars=['x', 'y'])
        Traceback (most recent call last):
            ...
        ValueError: Variable 'z' is not in allowed variables: ['x', 'y']
    """
    # Parse the DSL code using operational_statement_set entry point
    parsed_node = parse_with_grammar_entry(code, "operational_statement_set")

    # Convert parsed nodes to Operation objects
    operations = []
    for op_node in parsed_node:
        # Convert expression node to Expr object
        expr = parse_expr_node_to_expr(op_node.expr)

        # Create Operation object
        operation = Operation(
            var_name=op_node.name,
            expr=expr
        )
        operations.append(operation)

    # Validate variables if allowed_vars is specified
    if allowed_vars is not None:
        allowed_set = set(allowed_vars)

        for operation in operations:
            # Check variables used in expression
            for var in operation.expr.list_variables():
                if var.name not in allowed_set:
                    raise ValueError(
                        f"Variable '{var.name}' is not in allowed variables: {allowed_vars}"
                    )

            allowed_set.add(operation.var_name)

    return operations


def execute_operations(
    operations: Union[Operation, List[Operation]],
    var_exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Execute operations on a Z3 variable expression dictionary.

    This function takes a list of operations and executes them sequentially
    on a variable expression dictionary. Each operation updates the state by
    assigning a new Z3 expression to a variable. The operations are executed
    in order, so later operations can reference the results of earlier operations.

    This performs symbolic execution - expressions are built up symbolically
    rather than being evaluated to concrete values.

    :param operations: Single operation or list of operations to execute
    :type operations: Union[Operation, List[Operation]]
    :param var_exprs: Dictionary mapping variable names to current Z3 expressions
    :type var_exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: New variable expression dictionary with updated global Z3 expressions
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :raises ValueError: If a variable referenced in an expression is not available in the current block scope

    Example::

        >>> import z3
        >>> from pyfcstm.model.model import Operation
        >>> from pyfcstm.model.expr import Variable, Integer, BinaryOp
        >>>
        >>> # Create Z3 symbolic variables
        >>> x = z3.Int('x')
        >>> y = z3.Int('y')
        >>> var_exprs = {'x': x, 'y': y}
        >>>
        >>> # Create operations: x = x + 2; y = y + x;
        >>> op1 = Operation(var_name='x', expr=BinaryOp(x=Variable('x'), op='+', y=Integer(2)))
        >>> op2 = Operation(var_name='y', expr=BinaryOp(x=Variable('y'), op='+', y=Variable('x')))
        >>>
        >>> # Execute operations symbolically
        >>> new_exprs = execute_operations([op1, op2], var_exprs)
        >>> # new_exprs['x'] is the Z3 expression: x + 2
        >>> # new_exprs['y'] is the Z3 expression: y + (x + 2)
        >>>
        >>> # Can verify with solver
        >>> solver = z3.Solver()
        >>> solver.add(x == 5, y == 10)
        >>> solver.add(new_exprs['x'] == 7)  # 5 + 2
        >>> solver.add(new_exprs['y'] == 17)  # 10 + 7
        >>> solver.check()
        sat
    """
    # Handle single operation
    if isinstance(operations, Operation):
        operations = [operations]

    original_var_names = list(var_exprs.keys())

    # Create a copy of the state to avoid modifying the original
    current_exprs = dict(var_exprs)

    # Execute each operation in sequence
    for operation in operations:
        # Convert the operation's expression to Z3 using current expressions
        z3_expr = expr_to_z3(operation.expr, current_exprs)

        # Update the expressions with the new expression
        current_exprs[operation.var_name] = z3_expr

    return {name: current_exprs[name] for name in original_var_names}

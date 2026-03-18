"""
Operation parsing and execution utilities for Z3 solver integration.

This module provides functions to parse DSL operation code strings into
operation statements and execute them on Z3 variable dictionaries.

The module contains the following main components:

* :func:`parse_operations` - Parse DSL operation code string to statement tree
* :func:`execute_operations` - Execute operation statements on a Z3 variable dictionary

Example::

    >>> from pyfcstm.solver.operation import parse_operations, execute_operations
    >>> import z3
    >>>
    >>> # Parse operation statements from DSL string
    >>> ops = parse_operations("x = x + 1; y = x * 2;", allowed_vars=['x', 'y'])
    >>>
    >>> # Execute operations on Z3 variables
    >>> z3_vars = {'x': z3.Int('x'), 'y': z3.Int('y')}
    >>> z3_state = {'x': z3.IntVal(5), 'y': z3.IntVal(0)}
    >>> new_state = execute_operations(ops, z3_state)
    >>> # new_state['x'] represents the Z3 expression: 5 + 1
    >>> # new_state['y'] represents the Z3 expression: (5 + 1) * 2
"""

from typing import List, Dict, Optional, Union

import z3

from .expr import expr_to_z3
from ..dsl.parse import parse_with_grammar_entry
from ..dsl import node as dsl_nodes
from ..model.expr import parse_expr_node_to_expr
from ..model.model import IfBlock, IfBlockBranch, Operation, OperationStatement


def parse_operations(
    code: str,
    allowed_vars: Optional[List[str]] = None
) -> List[OperationStatement]:
    """
    Parse DSL operation code string into a list of operation statements.

    This function parses a DSL code string containing operation statements
    (assignments and ``if`` blocks) and converts them into model-layer
    operation statements. It can optionally validate that expressions only
    reference variables that are already available at that point in the block.
    Unknown assignment targets are treated as block-local temporary variables.

    :param code: DSL operation code string to parse
    :type code: str
    :param allowed_vars: List of initially available variable names, or ``None`` for free mode
    :type allowed_vars: Optional[List[str]]
    :return: List of parsed operation statements
    :rtype: List[OperationStatement]
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
    parsed_node = parse_with_grammar_entry(code, "operational_statement_set")

    def _validate_expression_variables(expr, available_names: set) -> None:
        for var in expr.list_variables():
            if var.name not in available_names:
                raise ValueError(
                    f"Variable '{var.name}' is not in allowed variables: {allowed_vars}"
                )

    def _convert_statements(
            statements: List[dsl_nodes.OperationalStatement],
            available_names: Optional[set],
    ) -> List[OperationStatement]:
        converted = []
        current_names = None if available_names is None else set(available_names)

        for statement in statements:
            if isinstance(statement, dsl_nodes.OperationAssignment):
                expr = parse_expr_node_to_expr(statement.expr)
                if current_names is not None:
                    _validate_expression_variables(expr, current_names)
                    current_names.add(statement.name)

                converted.append(Operation(var_name=statement.name, expr=expr))
                continue

            if isinstance(statement, dsl_nodes.OperationIf):
                base_names = None if current_names is None else set(current_names)
                branches = []

                for branch in statement.branches:
                    condition = None
                    if branch.condition is not None:
                        condition = parse_expr_node_to_expr(branch.condition)
                        if base_names is not None:
                            _validate_expression_variables(condition, base_names)

                    branch_names = None if base_names is None else set(base_names)
                    branch_statements = _convert_statements(branch.statements, branch_names)
                    branches.append(
                        IfBlockBranch(
                            condition=condition,
                            statements=branch_statements,
                        )
                    )

                converted.append(IfBlock(branches=branches))
                continue

            raise TypeError(f'Unknown operational statement node type {type(statement)!r}.')

        return converted

    initial_names = None if allowed_vars is None else set(allowed_vars)
    return _convert_statements(parsed_node, initial_names)


def _execute_operation_statements_symbolically(
        statements: List[OperationStatement],
        exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]],
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Execute a sequence of operation statements symbolically.

    :param statements: Statements to execute in order.
    :type statements: List[OperationStatement]
    :param exprs: Current symbolic environment.
    :type exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Updated symbolic environment.
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    """
    current_exprs = dict(exprs)

    for statement in statements:
        if isinstance(statement, Operation):
            current_exprs[statement.var_name] = expr_to_z3(statement.expr, current_exprs)
        elif isinstance(statement, IfBlock):
            current_exprs = _execute_if_block_symbolically(statement, current_exprs)
        else:
            raise TypeError(f'Unknown operation statement type {type(statement)!r}.')

    return current_exprs


def _execute_if_block_symbolically(
        if_block: IfBlock,
        exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]],
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Execute an ``if`` block symbolically with branch-local merge semantics.

    Each branch is symbolically executed from the same pre-``if`` environment.
    Only names that were already visible before entering the ``if`` block
    participate in the final merge. This keeps branch-local temporary
    variables out of the merged outer environment.

    :param if_block: If-block to execute.
    :type if_block: IfBlock
    :param exprs: Current symbolic environment.
    :type exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: Merged symbolic environment after the if-block.
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    """
    base_exprs = dict(exprs)
    visible_names = tuple(base_exprs.keys())
    branch_results = []

    for branch in if_block.branches:
        branch_results.append((
            expr_to_z3(branch.condition, base_exprs)
            if branch.condition is not None
            else None,
            _execute_operation_statements_symbolically(branch.statements, base_exprs),
        ))

    merged_exprs = dict(base_exprs)
    for name in visible_names:
        merged_value = base_exprs[name]
        for branch_condition, branch_exprs in reversed(branch_results):
            if branch_condition is None:
                merged_value = branch_exprs[name]
            else:
                merged_value = z3.If(branch_condition, branch_exprs[name], merged_value)

        merged_exprs[name] = merged_value

    return merged_exprs


def execute_operations(
    operations: Union[OperationStatement, List[OperationStatement]],
    var_exprs: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Execute operation statements on a Z3 variable expression dictionary.

    This function takes one operation statement or a statement list and
    symbolically executes it against a variable-expression dictionary.
    Assignments update the current symbolic environment directly, while ``if``
    blocks evaluate each branch from the same pre-``if`` environment and then
    merge only the names that were already visible before entering the block.
    Statements are executed in order, so later statements can reference the
    results of earlier ones.

    This performs symbolic execution - expressions are built up symbolically
    rather than being evaluated to concrete values.

    :param operations: Single statement or list of statements to execute
    :type operations: Union[OperationStatement, List[OperationStatement]]
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
    if isinstance(operations, OperationStatement):
        operations = [operations]

    original_var_names = list(var_exprs.keys())
    current_exprs = _execute_operation_statements_symbolically(operations, var_exprs)

    return {name: current_exprs[name] for name in original_var_names}

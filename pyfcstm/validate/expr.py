"""
This module provides utilities for converting fcstm DSL expressions to Z3 expressions
and performing various operations on Z3 expressions.

The module includes:
- Mapping of operators to Z3 functions
- Conversion functions from DSL expressions to Z3 expressions
- Utilities for simplifying Z3 expressions
"""

from typing import Dict, List

from z3 import ExprRef, IntVal, RealVal, BoolVal, Not, And, Or, If, simplify, Then, Goal

from ..model import Expr, Integer, Float, Boolean, Variable, UnaryOp, BinaryOp, ConditionalOp, UFunc, Operation

# Mapping of operator symbols to Z3 functions
_Z3_OP_FUNCTIONS = {
    # Unary operators
    "unary+": lambda x: x,  # Positive sign is the original value in Z3
    "unary-": lambda x: -x,  # Z3 supports negation
    "!": lambda x: Not(x),  # Logical NOT
    "not": lambda x: Not(x),  # Logical NOT

    # Binary operators
    "**": lambda x, y: x ** y,  # Power operation
    "*": lambda x, y: x * y,  # Multiplication
    "/": lambda x, y: x / y,  # Division
    "%": lambda x, y: x % y,  # Modulo (integers only)
    "+": lambda x, y: x + y,  # Addition
    "-": lambda x, y: x - y,  # Subtraction
    "<<": lambda x, y: x << y,  # Left shift (integers only)
    ">>": lambda x, y: x >> y,  # Right shift (integers only)
    "&": lambda x, y: x & y,  # Bitwise AND (integers only)
    "^": lambda x, y: x ^ y,  # Bitwise XOR (integers only)
    "|": lambda x, y: x | y,  # Bitwise OR (integers only)
    "<": lambda x, y: x < y,  # Less than
    ">": lambda x, y: x > y,  # Greater than
    "<=": lambda x, y: x <= y,  # Less than or equal
    ">=": lambda x, y: x >= y,  # Greater than or equal
    "==": lambda x, y: x == y,  # Equal
    "!=": lambda x, y: x != y,  # Not equal
    "&&": lambda x, y: And(x, y),  # Logical AND
    "and": lambda x, y: And(x, y),  # Logical AND
    "||": lambda x, y: Or(x, y),  # Logical OR
    "or": lambda x, y: Or(x, y),  # Logical OR

    # Ternary operator
    "?:": lambda condition, true_value, false_value: If(condition, true_value, false_value)
}

# Mapping of mathematical functions to Z3 implementations
_Z3_MATH_FUNCTIONS = {
    'abs': lambda x: If(x >= 0, x, -x),
    'sqrt': lambda x: x ** (RealVal(1) / RealVal(2)),
    'cbrt': lambda x: x ** (RealVal(1) / RealVal(3)),
    'sign': lambda x: If(x > 0, 1, If(x < 0, -1, 0)),
}


def _raw_model_expr_to_z3_expr(expr: Expr, variables: Dict[str, ExprRef]) -> ExprRef:
    """
    Convert a raw fcstm DSL expression to a Z3 expression.

    :param expr: The fcstm DSL expression to convert.
    :type expr: Expr
    :param variables: Dictionary mapping variable names to Z3 expressions.
    :type variables: Dict[str, ExprRef]

    :return: The converted Z3 expression.
    :rtype: ExprRef
    :raises ValueError: If an unsupported math function is encountered.
    :raises TypeError: If an unknown expression type is encountered.

    Example::
        >>> from z3 import Int
        >>> vars = {'x': Int('x')}
        >>> expr = Integer(42)
        >>> _raw_model_expr_to_z3_expr(expr, vars)
        42
    """
    if isinstance(expr, Integer):
        return IntVal(expr.value)
    elif isinstance(expr, Float):
        return RealVal(expr.value)
    elif isinstance(expr, Boolean):
        return BoolVal(expr.value)
    elif isinstance(expr, Variable):
        return variables[expr.name]
    elif isinstance(expr, UnaryOp):
        x = _raw_model_expr_to_z3_expr(expr.x, variables)
        return _Z3_OP_FUNCTIONS[expr.op_mark](x)
    elif isinstance(expr, BinaryOp):
        x = _raw_model_expr_to_z3_expr(expr.x, variables)
        y = _raw_model_expr_to_z3_expr(expr.y, variables)
        return _Z3_OP_FUNCTIONS[expr.op_mark](x, y)
    elif isinstance(expr, ConditionalOp):
        cond = _raw_model_expr_to_z3_expr(expr.cond, variables)
        if_true = _raw_model_expr_to_z3_expr(expr.if_true, variables)
        if_false = _raw_model_expr_to_z3_expr(expr.if_false, variables)
        return _Z3_OP_FUNCTIONS[expr.op_mark](cond, if_true, if_false)
    elif isinstance(expr, UFunc):
        if expr.func in _Z3_MATH_FUNCTIONS:
            x = _raw_model_expr_to_z3_expr(expr.x, variables)
            return _Z3_MATH_FUNCTIONS[expr.func](x)
        else:
            raise ValueError(f'Unsupported math functions for z3 solver - {expr.to_ast_node()}')
    else:
        raise TypeError(f'Unknown fcstm DSL expression type - {expr!r}')


def model_expr_to_z3_expr(x: Expr, variables: Dict[str, ExprRef]) -> ExprRef:
    """
    Convert a fcstm DSL expression to a Z3 expression.

    This is a wrapper function around :func:`_raw_model_expr_to_z3_expr` that provides
    a cleaner interface for external use.

    :param x: The fcstm DSL expression to convert.
    :type x: Expr
    :param variables: Dictionary mapping variable names to Z3 expressions.
    :type variables: Dict[str, ExprRef]

    :return: The converted Z3 expression.
    :rtype: ExprRef

    Example::
        >>> from z3 import Int
        >>> vars = {'x': Int('x')}
        >>> expr = Variable('x')
        >>> model_expr_to_z3_expr(expr, vars)
        x
    """
    return _raw_model_expr_to_z3_expr(
        expr=x,
        variables=variables,
    )


def operations_to_z3_vars(operations: List[Operation], variables: Dict[str, ExprRef]) -> Dict[str, ExprRef]:
    """
    Convert a list of operations to Z3 variables.

    This function processes a list of operations and creates a new dictionary of Z3 variables
    by evaluating each operation's expression and adding it to the variables dictionary.

    :param operations: List of operations to convert.
    :type operations: List[Operation]
    :param variables: Initial dictionary of Z3 variables.
    :type variables: Dict[str, ExprRef]

    :return: Updated dictionary with new Z3 variables from operations.
    :rtype: Dict[str, ExprRef]

    Example::
        >>> from z3 import Int
        >>> vars = {'x': Int('x')}
        >>> ops = [Operation(var_name='y', expr=Variable('x'))]
        >>> operations_to_z3_vars(ops, vars)
        {'x': x, 'y': x}
    """
    variables = dict(variables)
    for ef in operations:
        variables[ef.var_name] = model_expr_to_z3_expr(ef.expr, variables)
    return variables


def to_z3_expr(x) -> ExprRef:
    """
    Convert a Python value to a Z3 expression.

    :param x: The value to convert. Can be an ExprRef, int, float, or bool.
    :type x: Union[ExprRef, int, float, bool]

    :return: The converted Z3 expression.
    :rtype: ExprRef
    :raises TypeError: If the value type is not supported.

    Example::
        >>> to_z3_expr(42)
        42
        >>> to_z3_expr(3.14)
        3.14
        >>> to_z3_expr(True)
        True
    """
    if isinstance(x, ExprRef):
        return x
    elif isinstance(x, int):
        return IntVal(x)
    elif isinstance(x, float):
        return RealVal(x)
    elif isinstance(x, bool):
        return BoolVal(x)
    else:
        raise TypeError(f'Unknown value type - {x!r}')


def comprehensive_simplify(expr: ExprRef) -> ExprRef:
    """
    Perform comprehensive simplification on a Z3 expression.

    This function applies multiple simplification strategies to a Z3 expression:
    1. Basic algebraic simplification
    2. Advanced tactics including context simplification, value propagation, and equation solving
    3. Final simplification pass

    :param expr: The Z3 expression to simplify.
    :type expr: ExprRef

    :return: The simplified Z3 expression.
    :rtype: ExprRef

    Example::
        >>> from z3 import Int
        >>> x = Int('x')
        >>> expr = x + 0
        >>> comprehensive_simplify(expr)
        x
    """
    # Step 1: Basic simplification
    result = simplify(expr, algebraic=True)

    # Step 2: Use advanced strategies
    tactics = Then('simplify', 'ctx-simplify', 'propagate-values', 'solve-eqs')
    goal = Goal()
    goal.add(result)
    try:
        simplified_goals = tactics(goal)
        if len(simplified_goals[0]) > 0:
            result = And(*simplified_goals[0]) if len(simplified_goals[0]) > 1 else simplified_goals[0][0]
    except:
        pass

    # Note: Steps 3 and 4 (pattern-based and interval-based simplification) are commented out
    # in the original code and not implemented here

    # Step 5: Final simplification
    result = simplify(result, algebraic=True)

    return result

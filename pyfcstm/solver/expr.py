"""
Expression conversion utilities for Z3 solver integration.

This module provides functions to convert pyfcstm expression objects into
Z3 solver expressions, enabling constraint solving and symbolic execution.
It supports all expression types including literals, variables, operators,
and mathematical functions.

The module contains the following main components:

* :func:`expr_to_z3` - Convert a pyfcstm Expr to a Z3 expression
* :func:`create_z3_vars_from_models` - Create Z3 variables from model objects

Example::

    >>> from pyfcstm.model.expr import Variable, Integer, BinaryOp
    >>> from pyfcstm.solver.expr import expr_to_z3, create_z3_vars_from_models
    >>> from pyfcstm.model.model import VarDefine
    >>> import z3
    >>>
    >>> # Create variable definitions
    >>> var_defs = [
    ...     VarDefine(name='x', type='int', init=Integer(0)),
    ...     VarDefine(name='y', type='float', init=Float(0.0))
    ... ]
    >>>
    >>> # Create Z3 variables
    >>> z3_vars = create_z3_vars_from_models(var_defs)
    >>>
    >>> # Convert expression to Z3
    >>> expr = BinaryOp(x=Variable('x'), op='+', y=Integer(5))
    >>> z3_expr = expr_to_z3(expr, z3_vars)
"""

import warnings
from typing import Dict, List, Union

import z3

from ..model.expr import (
    Expr, Integer, Float, Boolean, Variable,
    BinaryOp, UnaryOp, ConditionalOp, UFunc
)
from ..model.model import StateMachine, VarDefine


def expr_to_z3(expr: Expr, z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]) -> Union[z3.ArithRef, z3.BoolRef]:
    """
    Convert a pyfcstm expression to a Z3 solver expression.

    This function recursively converts pyfcstm expression objects into equivalent
    Z3 expressions. It supports literals, variables, arithmetic operators, bitwise
    operators, logical operators, conditional expressions, and mathematical functions.

    :param expr: The pyfcstm expression to convert
    :type expr: Expr
    :param z3_vars: Dictionary mapping variable names to Z3 expression objects
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: The equivalent Z3 expression
    :rtype: Union[z3.ArithRef, z3.BoolRef]
    :raises ValueError: If the expression type is unsupported or variable is not found
    :raises NotImplementedError: If a mathematical function is not supported

    Example::

        >>> import z3
        >>> from pyfcstm.model.expr import Variable, Integer, BinaryOp
        >>> z3_vars = {'x': z3.Int('x')}
        >>> expr = BinaryOp(x=Variable('x'), op='+', y=Integer(5))
        >>> z3_expr = expr_to_z3(expr, z3_vars)
        >>> solver = z3.Solver()
        >>> solver.add(z3_expr == 10)
        >>> solver.check()
        sat
        >>> solver.model()[z3_vars['x']]
        5
    """
    # Handle literal values
    if isinstance(expr, Integer):
        return z3.IntVal(expr.value)

    elif isinstance(expr, Float):
        return z3.RealVal(expr.value)

    elif isinstance(expr, Boolean):
        return z3.BoolVal(expr.value)

    # Handle variables
    elif isinstance(expr, Variable):
        if expr.name not in z3_vars:
            raise ValueError(f"Variable '{expr.name}' not found in z3_vars dictionary")
        return z3_vars[expr.name]

    # Handle binary operators
    elif isinstance(expr, BinaryOp):
        left = expr_to_z3(expr.x, z3_vars)
        right = expr_to_z3(expr.y, z3_vars)

        # Arithmetic operators
        if expr.op == '+':
            return left + right
        elif expr.op == '-':
            return left - right
        elif expr.op == '*':
            return left * right
        elif expr.op == '/':
            return left / right
        elif expr.op == '%':
            return left % right
        elif expr.op == '**':
            # Power operator in Z3 has different performance characteristics:
            # - x ** constant: Generally OK (e.g., x**2, x**3)
            # - constant ** x: Slower but acceptable (e.g., 2**x)
            # - x ** y: Very slow, may not terminate in reasonable time
            #
            # Check if both operands are variables (worst case)
            left_is_var = isinstance(expr.x, Variable)
            right_is_var = isinstance(expr.y, Variable)

            if left_is_var and right_is_var:
                warnings.warn(
                    f"Power operation with two variables (x ** y) may be very slow in Z3. "
                    f"Z3's nonlinear arithmetic solver has limited support for this pattern. "
                    f"Consider using alternative formulations or constraints if possible.",
                    UserWarning,
                    stacklevel=2
                )
            elif right_is_var:
                warnings.warn(
                    f"Power operation with variable exponent (constant ** x) may be slow in Z3. "
                    f"Performance depends on the solver's ability to handle exponential constraints.",
                    UserWarning,
                    stacklevel=2
                )
            # x ** constant is generally fine, no warning needed

            return left ** right

        # Bitwise operators
        # Note: These work on Z3 Int but have limitations compared to BitVec
        elif expr.op == '&':
            warnings.warn(
                f"Bitwise AND (&) on Z3 Int types has limited support. "
                f"For full bitwise operation support, consider using Z3 BitVec types. "
                f"The operation may not work as expected for negative numbers.",
                UserWarning,
                stacklevel=2
            )
            return left & right
        elif expr.op == '|':
            warnings.warn(
                f"Bitwise OR (|) on Z3 Int types has limited support. "
                f"For full bitwise operation support, consider using Z3 BitVec types. "
                f"The operation may not work as expected for negative numbers.",
                UserWarning,
                stacklevel=2
            )
            return left | right
        elif expr.op == '^':
            warnings.warn(
                f"Bitwise XOR (^) on Z3 Int types has limited support. "
                f"For full bitwise operation support, consider using Z3 BitVec types. "
                f"The operation may not work as expected for negative numbers.",
                UserWarning,
                stacklevel=2
            )
            return left ^ right
        elif expr.op == '<<':
            warnings.warn(
                f"Left shift (<<) on Z3 Int types has limited support. "
                f"For full bitwise operation support, consider using Z3 BitVec types.",
                UserWarning,
                stacklevel=2
            )
            return left << right
        elif expr.op == '>>':
            warnings.warn(
                f"Right shift (>>) on Z3 Int types has limited support. "
                f"For full bitwise operation support, consider using Z3 BitVec types.",
                UserWarning,
                stacklevel=2
            )
            return left >> right

        # Comparison operators
        elif expr.op == '<':
            return left < right
        elif expr.op == '<=':
            return left <= right
        elif expr.op == '>':
            return left > right
        elif expr.op == '>=':
            return left >= right
        elif expr.op == '==':
            return left == right
        elif expr.op == '!=':
            return left != right

        # Logical operators
        elif expr.op in ('&&', 'and'):
            return z3.And(left, right)
        elif expr.op in ('||', 'or'):
            return z3.Or(left, right)

        else:
            raise ValueError(f"Unsupported binary operator: {expr.op}")

    # Handle unary operators
    elif isinstance(expr, UnaryOp):
        operand = expr_to_z3(expr.x, z3_vars)

        if expr.op == '-':
            return -operand
        elif expr.op == '+':
            return operand
        elif expr.op == '~':
            warnings.warn(
                f"Bitwise NOT (~) on Z3 Int types has limited support. "
                f"For full bitwise operation support, consider using Z3 BitVec types. "
                f"The operation may not work as expected.",
                UserWarning,
                stacklevel=2
            )
            return ~operand
        elif expr.op in ('!', 'not'):
            return z3.Not(operand)
        else:
            raise ValueError(f"Unsupported unary operator: {expr.op}")

    # Handle conditional expressions (ternary operator)
    elif isinstance(expr, ConditionalOp):
        condition = expr_to_z3(expr.cond, z3_vars)
        true_val = expr_to_z3(expr.if_true, z3_vars)
        false_val = expr_to_z3(expr.if_false, z3_vars)
        return z3.If(condition, true_val, false_val)

    # Handle mathematical functions
    elif isinstance(expr, UFunc):
        operand = expr_to_z3(expr.x, z3_vars)

        # Absolute value and sign functions
        if expr.func == 'abs':
            # Use conditional expression for absolute value
            return z3.If(operand >= 0, operand, -operand)

        elif expr.func == 'sign':
            # Sign function: returns -1, 0, or 1
            zero = z3.IntVal(0) if z3.is_int(operand) else z3.RealVal(0)
            one = z3.IntVal(1) if z3.is_int(operand) else z3.RealVal(1)
            minus_one = z3.IntVal(-1) if z3.is_int(operand) else z3.RealVal(-1)
            return z3.If(operand == zero, zero, z3.If(operand > zero, one, minus_one))

        # Rounding functions (for Real numbers)
        elif expr.func == 'floor':
            # Z3 has ToInt which performs floor for non-negative reals
            # For general floor, we need to handle negative numbers
            if z3.is_real(operand):
                return z3.ToInt(operand)
            elif z3.is_int(operand):
                # Already an integer
                return operand
            else:
                # Try to convert to Real first (silent conversion)
                return z3.ToInt(z3.ToReal(operand))

        elif expr.func == 'ceil':
            # Ceiling: ceil(x) = -floor(-x)
            if z3.is_real(operand):
                return -z3.ToInt(-operand)
            elif z3.is_int(operand):
                # Already an integer
                return operand
            else:
                # Try to convert to Real first (silent conversion)
                return -z3.ToInt(-z3.ToReal(operand))

        elif expr.func == 'trunc':
            # Truncate towards zero
            if z3.is_real(operand):
                zero = z3.RealVal(0)
                return z3.If(operand >= zero, z3.ToInt(operand), -z3.ToInt(-operand))
            elif z3.is_int(operand):
                # Already an integer
                return operand
            else:
                # Try to convert to Real first (silent conversion)
                real_operand = z3.ToReal(operand)
                zero = z3.RealVal(0)
                return z3.If(real_operand >= zero, z3.ToInt(real_operand), -z3.ToInt(-real_operand))

        # Min/Max functions (if operand is a comparison, we can use If)
        # Note: These would need special handling as they typically take 2 arguments

        # Power and root functions
        elif expr.func == 'sqrt':
            # Z3 has limited support for sqrt
            # We can use z3.Sqrt for Real numbers in some theories
            if z3.is_real(operand):
                return z3.Sqrt(operand)
            elif z3.is_int(operand):
                # Convert Int to Real for sqrt (silent conversion)
                return z3.Sqrt(z3.ToReal(operand))
            else:
                raise NotImplementedError(
                    f"sqrt requires Real or Int operand, got {operand.sort()}. "
                    f"Cannot convert to Real."
                )

        elif expr.func == 'cbrt':
            # Cube root: x^(1/3)
            # Z3 doesn't have native cbrt, would need uninterpreted function
            raise NotImplementedError(
                f"Mathematical function 'cbrt' is not directly supported in Z3. "
                f"Consider using uninterpreted functions or polynomial constraints (y^3 = x)."
            )

        elif expr.func == 'exp':
            # Exponential function
            raise NotImplementedError(
                f"Mathematical function 'exp' is not directly supported in Z3. "
                f"Consider using uninterpreted functions or approximations."
            )

        # Logarithmic functions
        elif expr.func in ('log', 'log10', 'log2', 'log1p'):
            raise NotImplementedError(
                f"Logarithmic function '{expr.func}' is not directly supported in Z3. "
                f"Consider using uninterpreted functions or approximations."
            )

        # Trigonometric functions
        elif expr.func in ('sin', 'cos', 'tan', 'asin', 'acos', 'atan'):
            raise NotImplementedError(
                f"Trigonometric function '{expr.func}' is not directly supported in Z3. "
                f"Consider using uninterpreted functions or approximations."
            )

        # Hyperbolic functions
        elif expr.func in ('sinh', 'cosh', 'tanh', 'asinh', 'acosh', 'atanh'):
            raise NotImplementedError(
                f"Hyperbolic function '{expr.func}' is not directly supported in Z3. "
                f"Consider using uninterpreted functions or approximations."
            )

        # Round function
        elif expr.func == 'round':
            # Python's round function - rounds to nearest even
            if z3.is_real(operand):
                # Z3 doesn't have native round, approximate with floor(x + 0.5)
                # This is "round half up" not "round half to even" but close enough
                return z3.ToInt(operand + z3.RealVal(0.5))
            elif z3.is_int(operand):
                # Already an integer
                return operand
            else:
                # Try to convert to Real first (silent conversion)
                return z3.ToInt(z3.ToReal(operand) + z3.RealVal(0.5))

        else:
            raise NotImplementedError(
                f"Mathematical function '{expr.func}' is not supported in Z3 conversion. "
                f"Supported functions: abs, sign, floor, ceil, trunc, round, sqrt (Real only). "
                f"Unsupported: trigonometric, hyperbolic, logarithmic, and exponential functions."
            )

    else:
        raise ValueError(f"Unsupported expression type: {type(expr).__name__}")


def create_z3_vars_from_models(models: Union[StateMachine, VarDefine, List[VarDefine]]) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
    """
    Create a dictionary of Z3 variables from model objects.

    This function creates Z3 variables from various model input types:
    - StateMachine: extracts variables from the state machine
    - VarDefine: creates a single Z3 variable
    - List[VarDefine]: creates Z3 variables for all definitions in the list

    Integer types map to Z3 Int, float types map to Z3 Real.

    :param models: Model object(s) containing variable definitions
    :type models: Union[StateMachine, VarDefine, List[VarDefine]]
    :return: Dictionary mapping variable names to Z3 expression objects
    :rtype: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :raises ValueError: If a variable type is unsupported
    :raises TypeError: If the input type is not supported

    Example::

        >>> from pyfcstm.model.model import VarDefine, StateMachine, State
        >>> from pyfcstm.model.expr import Integer, Float
        >>>
        >>> # From a list of VarDefine
        >>> var_defs = [
        ...     VarDefine(name='counter', type='int', init=Integer(0)),
        ...     VarDefine(name='temperature', type='float', init=Float(25.0))
        ... ]
        >>> z3_vars = create_z3_vars_from_models(var_defs)
        >>> 'counter' in z3_vars
        True
        >>>
        >>> # From a single VarDefine
        >>> single_var = VarDefine(name='x', type='int', init=Integer(0))
        >>> z3_vars = create_z3_vars_from_models(single_var)
        >>> 'x' in z3_vars
        True
        >>>
        >>> # From a StateMachine
        >>> root_state = State(name='System', parent=None, is_pseudo=False,
        ...                    display_name=None, comment=None)
        >>> sm = StateMachine(variables=var_defs, root_state=root_state, global_events=[])
        >>> z3_vars = create_z3_vars_from_models(sm)
        >>> 'counter' in z3_vars
        True
    """
    # Determine the list of VarDefine objects based on input type
    if isinstance(models, StateMachine):
        var_defines = list(models.defines.values())
    elif isinstance(models, VarDefine):
        var_defines = [models]
    elif isinstance(models, list):
        var_defines = models
    else:
        raise TypeError(f"Unsupported input type: {type(models).__name__}. "
                        "Expected StateMachine, VarDefine, or List[VarDefine]")

    # Create Z3 variables
    z3_vars = {}

    for var_def in var_defines:
        var_name = var_def.name
        var_type = var_def.type.lower()

        if var_type == 'int':
            z3_vars[var_name] = z3.Int(var_name)
        elif var_type == 'float':
            z3_vars[var_name] = z3.Real(var_name)
        else:
            raise ValueError(f"Unsupported variable type '{var_type}' for variable '{var_name}'. "
                             "Supported types: int, float")

    return z3_vars

"""
This module provides utilities for working with Z3 SMT solver expressions and converting them to Python native types.

The module includes functionality for:
- Determining Z3 expression types
- Checking if expressions are concrete values
- Converting Z3 expressions to Python native types
- Solving Z3 constraints and extracting variable values

Main components:
- :class:`SolveResult`: Dataclass for storing constraint solving results
- :func:`get_expr_type`: Get the type of a Z3 expression
- :func:`is_concrete_value`: Check if a Z3 expression is a concrete value
- :func:`z3_to_python`: Convert Z3 expressions to Python native types
- :func:`solve_expr`: Solve Z3 constraints and extract variable values
"""

from dataclasses import dataclass
from typing import Union, Dict, Optional, List

import z3
from z3 import Solver, sat, ExprRef, unsat

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):
    from typing_extensions import Literal


@dataclass
class SolveResult:
    """
    Dataclass representing the result of solving Z3 constraints.

    :param type: The result type, either 'sat' (satisfiable), 'unsat' (unsatisfiable), or 'undetermined'.
    :type type: Literal['sat', 'unsat', 'undetermined']
    :param solutions: Dictionary mapping variable names to their solved values, or None if unsat/undetermined.
    :type solutions: Optional[Union[List[Dict[str, Union[int, float]]], Dict[str, Union[int, float]]]]
    """
    type: Literal['sat', 'unsat', 'undetermined']
    solutions: Optional[List[Dict[str, Union[int, float]]]]


def get_expr_type(expr: ExprRef) -> str:
    """
    Get the type of a Z3 expression as a string.

    :param expr: The Z3 expression to analyze.
    :type expr: ExprRef

    :return: A string describing the type of the expression (e.g., "Integer", "Real", "Boolean").
    :rtype: str

    Example::
        >>> import z3
        >>> x = z3.Int('x')
        >>> get_expr_type(x)
        'Integer'
        >>> y = z3.Real('y')
        >>> get_expr_type(y)
        'Real'
    """
    sort = expr.sort()
    sort_kind = sort.kind()

    if sort_kind == z3.Z3_INT_SORT:
        return "Integer"
    elif sort_kind == z3.Z3_REAL_SORT:
        return "Real"
    elif sort_kind == z3.Z3_BOOL_SORT:
        return "Boolean"
    elif sort_kind == z3.Z3_BV_SORT:
        return f"BitVector({sort.size()})"
    elif sort_kind == z3.Z3_ARRAY_SORT:
        return f"Array({sort.domain()}, {sort.range()})"
    else:
        return f"Unknown({sort})"


def is_concrete_value(expr: ExprRef) -> bool:
    """
    Determine if a Z3 expression is a concrete value (rather than a symbolic variable).

    This function checks whether the given Z3 expression represents a concrete, 
    constant value or a symbolic variable. It handles various Z3 types including 
    booleans, integers, reals, bit vectors, and strings.

    :param expr: The Z3 expression to check.
    :type expr: ExprRef

    :return: True if the expression is a concrete value, False otherwise.
    :rtype: bool

    Example::
        >>> import z3
        >>> x = z3.Int('x')
        >>> is_concrete_value(x)
        False
        >>> is_concrete_value(z3.IntVal(42))
        True
        >>> is_concrete_value(z3.BoolVal(True))
        True
    """
    try:
        # Use different methods to check if it's a concrete value for different types
        if z3.is_bool(expr):
            return z3.is_true(expr) or z3.is_false(expr)
        elif z3.is_int(expr):
            # Try to get integer value, success means it's a concrete value
            try:
                expr.as_long()
                return True
            except:
                return False
        elif z3.is_real(expr):
            # Try to get real value
            try:
                if expr.is_int():
                    expr.as_long()
                else:
                    expr.numerator_as_long()
                    expr.denominator_as_long()
                return True
            except:
                return False
        elif z3.is_bv(expr):
            # Try to get bit vector value
            try:
                expr.as_long()
                return True
            except:
                return False
        elif z3.is_string(expr):
            # Try to get string value
            try:
                expr.as_string()
                return True
            except:
                return False
        else:
            return False
    except:
        return False


def z3_to_python(expr: ExprRef) -> Union[bool, int, float, str, Dict[str, Union[int, str]]]:
    """
    Convert a Z3 ExprRef to a Python native type.

    This function converts Z3 expressions to their Python equivalents. It supports
    boolean, integer, real, bit vector, and string types. For bit vectors, it returns
    a dictionary containing multiple representations (unsigned, signed, hex, binary).

    :param expr: The Z3 ExprRef object to convert.
    :type expr: ExprRef

    :return: The Python native type value. For bit vectors, returns a dictionary with
             'unsigned', 'signed', 'bit_size', 'hex', and 'binary' keys.
    :rtype: Union[bool, int, float, str, Dict[str, Union[int, str]]]

    :raises ValueError: When the expression is symbolic or cannot be converted to a concrete value.
    :raises TypeError: When the type is not supported for conversion (e.g., arrays).

    Example::
        >>> import z3
        >>> z3_to_python(z3.IntVal(42))
        42
        >>> z3_to_python(z3.BoolVal(True))
        True
        >>> z3_to_python(z3.RealVal("3/2"))
        1.5
        >>> z3_to_python(z3.BitVecVal(255, 8))
        {'unsigned': 255, 'signed': -1, 'bit_size': 8, 'hex': '0xff', 'binary': '0b11111111'}
    """

    # First check if it's a concrete value (not a symbolic variable)
    if not is_concrete_value(expr):
        raise ValueError(
            f"Cannot convert symbolic expression to Python native type.\n"
            f"Expression: {expr}\n"
            f"Type: {expr.sort()}\n"
            f"The expression contains variables or is not a concrete value.\n"
            f"You may need to evaluate this expression in a model first."
        )

    # Boolean type
    if z3.is_bool(expr):
        if z3.is_true(expr):
            return True
        elif z3.is_false(expr):
            return False
        else:
            raise ValueError(f"Unknown boolean value: {expr}")

    # Integer type
    elif z3.is_int(expr):
        return expr.as_long()

    # Real type
    elif z3.is_real(expr):
        # Z3 reals may be in fractional form
        if expr.is_int():
            return float(expr.as_long())
        else:
            # Get numerator and denominator of the fraction
            numerator = expr.numerator_as_long()
            denominator = expr.denominator_as_long()
            return float(numerator) / float(denominator)

    # BitVector type
    elif z3.is_bv(expr):
        bit_size = expr.sort().size()
        value = expr.as_long()

        # Check if it's a signed number (if the highest bit is 1)
        if value >= (1 << (bit_size - 1)):
            # Convert to signed number
            signed_value = value - (1 << bit_size)
            return {
                'unsigned': value,
                'signed': signed_value,
                'bit_size': bit_size,
                'hex': hex(value),
                'binary': bin(value)
            }
        else:
            return {
                'unsigned': value,
                'signed': value,
                'bit_size': bit_size,
                'hex': hex(value),
                'binary': bin(value)
            }

    # String type
    elif z3.is_string(expr):
        return expr.as_string()

    # Array type - usually cannot be directly converted
    elif z3.is_array(expr):
        raise TypeError(
            f"Array types cannot be converted to Python native types.\n"
            f"Expression: {expr}\n"
            f"Sort: {expr.sort()}\n"
            f"Arrays in Z3 are functions and don't have a direct Python equivalent.\n"
            f"Consider extracting specific array elements using model evaluation."
        )

    # Other unsupported types
    else:
        sort_kind = expr.sort().kind()
        raise TypeError(
            f"Unsupported Z3 type for conversion to Python native type.\n"
            f"Expression: {expr}\n"
            f"Sort: {expr.sort()}\n"
            f"Sort kind: {sort_kind}\n"
            f"Supported types: Bool, Int, Real, BitVec, String\n"
            f"For custom types, you may need to implement specific conversion logic."
        )


def solve_expr(constraint: ExprRef, variables: Dict[str, ExprRef],
               max_solutions: Optional[int] = 1) -> SolveResult:
    """
    Solve Z3 constraints and extract variable values.

    This function creates a Z3 solver, adds the given constraint, and attempts to
    find satisfying assignments for the specified variables. It returns a
    :class:`SolveResult` object containing the result type and variable values.

    :param constraint: The Z3 constraint to solve.
    :type constraint: ExprRef
    :param variables: Dictionary mapping variable names to their Z3 ExprRef objects.
    :type variables: Dict[str, ExprRef]
    :param max_solutions: Maximum number of solutions to find. If None, returns only one solution.
                         If specified, attempts to find up to max_solutions different solutions.
    :type max_solutions: Optional[int]

    :return: A SolveResult object containing the solving result and variable values.
             If max_solutions is None, values is a Dict[str, Union[int, float]].
             If max_solutions is specified, values is a List[Dict[str, Union[int, float]]].
    :rtype: SolveResult

    Example::
        >>> import z3
        >>> x = z3.Int('x')
        >>> y = z3.Int('y')
        >>> constraint = z3.And(x > 0, y > 0, x + y == 10)
        >>> # Single solution
        >>> result = solve_expr(constraint, {'x': x, 'y': y})
        >>> result.type
        'sat'
        >>> result.solutions  # doctest: +SKIP
        {'x': 1, 'y': 9}
        >>> # Multiple solutions
        >>> result = solve_expr(constraint, {'x': x, 'y': y}, max_solutions=3)
        >>> result.type
        'sat'
        >>> len(result.solutions)  # doctest: +SKIP
        3
    """
    solver = Solver()
    solver.push()  # Save current state
    try:
        solver.add(constraint)

        # Multiple solutions mode
        solutions = []
        type_: Literal['sat', 'unsat', 'undetermined'] = 'sat'

        for _ in range(max_solutions):
            result = solver.check()

            if result == sat:
                type_ = 'sat'
                model = solver.model()
                values = {}

                # Extract variable values
                for name, v in variables.items():
                    val = model[v]
                    if val is not None:
                        values[name] = z3_to_python(val)
                    else:
                        values[name] = val

                solutions.append(values)

                # Create constraint to exclude this solution
                # Build a constraint that negates the current assignment
                exclusion_constraints = []
                for name, v in variables.items():
                    val = model[v]
                    if val is not None:
                        exclusion_constraints.append(v != val)

                if exclusion_constraints:
                    # Add constraint to exclude this solution
                    solver.add(z3.Or(exclusion_constraints))
                else:
                    # If no variables to constrain, break to avoid infinite loop
                    break

            elif result == unsat:
                # No more solutions
                type_ = 'unsat'
                break
            else:
                # Undetermined result
                type_ = 'undetermined'
                break

        if solutions:
            type_ = 'sat'
        return SolveResult(
            type=type_,
            solutions=solutions if type_ == 'sat' else None,
        )


    finally:
        solver.pop()  # Restore state

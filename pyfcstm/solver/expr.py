"""
Expression conversion utilities for Z3 solver integration.

This module provides functions to convert pyfcstm expression objects into
Z3 solver expressions, enabling constraint solving and symbolic execution.
It supports all expression types including literals, variables, operators,
and mathematical functions.

The module contains the following main components:

* :func:`expr_to_z3` - Convert a pyfcstm model expression to a Z3 expression
* :func:`create_z3_vars_from_models` - Create Z3 variables from model objects

Example::

    >>> from pyfcstm.model.expr import Variable, Integer, Float, BinaryOp
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

from typing import Dict, List, Union

import z3

from ..model.expr import Expr
from ..model.model import StateMachine, VarDefine
from ..semantics.adapters import expression_from_model
from ..semantics.catalog import lookup
from ..semantics.symbolic import SymbolicFailure, SymbolicSession, translate


def python_round_to_z3(operand: Union[z3.ArithRef, z3.BoolRef]) -> z3.ArithRef:
    """Return a Z3 expression matching Python single-argument ``round``.

    Python rounds half-way cases to the nearest even integer.  Keeping this
    helper in the shared solver layer prevents raw verify algorithms from
    drifting away from runtime expression semantics.

    :param operand: Integer or real Z3 operand.
    :type operand: Union[z3.ArithRef, z3.BoolRef]
    :return: Rounded integer expression.
    :rtype: z3.ArithRef

    Example::

        >>> import z3
        >>> x = z3.Real("x")
        >>> rounded = python_round_to_z3(x)
        >>> solver = z3.Solver()
        >>> solver.add(x == z3.RealVal("2.5"), rounded != 2)
        >>> solver.check()
        unsat
    """
    return lookup("round").symbolic(operand)


def expr_to_z3(
    expr: Expr, z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
) -> Union[z3.ArithRef, z3.BoolRef]:
    """
    Convert a pyfcstm expression to a Z3 solver expression.

    The translation follows the FCSTM operator catalog
    (:mod:`pyfcstm.semantics.catalog`): ``/`` is true division, ``%`` takes the
    sign of the divisor, ``0 ** 0`` is ``1`` and ``sign`` is integer valued.
    Bitwise operators and transcendental functions have no exact encoding and
    raise :class:`NotImplementedError`.  Runtime-definedness conditions such as
    non-zero divisors are not part of the result; use
    :func:`pyfcstm.solver.domain.translate_expr_domain` to obtain them.

    :param expr: The pyfcstm expression to convert
    :type expr: pyfcstm.model.expr.Expr
    :param z3_vars: Dictionary mapping variable names to Z3 expression objects
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :return: The equivalent Z3 expression
    :rtype: Union[z3.ArithRef, z3.BoolRef]
    :raises ValueError: If the expression type is unsupported, a variable is
        not found, or a logical operator receives a non-Boolean operand
    :raises NotImplementedError: If an operator or function has no exact Z3
        encoding
    :raises TypeError: If Z3 operators reject the operand sorts
    :raises z3.Z3Exception: If Z3 rejects the operand sorts

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
    try:
        node = expression_from_model(expr)
    except TypeError as err:
        # TypeError: the object is not a model expression.
        raise ValueError(str(err)) from None
    try:
        return translate(node, z3_vars, SymbolicSession(track_definedness=False))[0]
    except SymbolicFailure as err:
        # SymbolicFailure: the expression has no Z3 translation; callers of
        # this function receive the underlying exception.
        raise (err.error if err.error is not None else ValueError(err.reason)) from None


def create_z3_vars_from_models(
    models: Union[StateMachine, VarDefine, List[VarDefine]],
) -> Dict[str, Union[z3.ArithRef, z3.BoolRef]]:
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

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.model.model import VarDefine
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
        >>> # From a StateMachine parsed through the public DSL pipeline.
        >>> source = '''
        ... def int counter = 0;
        ... state System;
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> z3_vars = create_z3_vars_from_models(machine)
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
        raise TypeError(
            f"Unsupported input type: {type(models).__name__}. "
            "Expected StateMachine, VarDefine, or List[VarDefine]"
        )

    # Create Z3 variables
    z3_vars = {}

    for var_def in var_defines:
        var_name = var_def.name
        var_type = var_def.type.lower()

        if var_type == "int":
            z3_vars[var_name] = z3.Int(var_name)
        elif var_type == "float":
            z3_vars[var_name] = z3.Real(var_name)
        else:
            raise ValueError(
                f"Unsupported variable type '{var_type}' for variable '{var_name}'. "
                "Supported types: int, float"
            )

    return z3_vars

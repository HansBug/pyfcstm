"""
Z3 variable creation helpers for state machine models.

This module focuses on converting :class:`pyfcstm.model.model.StateMachine`
variable definitions into symbolic Z3 variables. It provides a narrow API for
solver workflows that start from a parsed state machine model rather than from
individual variable definitions.

The module contains the following main component:

* :func:`create_z3_vars_from_state_machine` - Create Z3 variables from a state machine

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.solver.vars import create_z3_vars_from_state_machine
    >>> ast = parse_with_grammar_entry(
    ...     "def int counter = 0; state System { state Idle; [*] -> Idle; }",
    ...     "state_machine_dsl"
    ... )
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> z3_vars = create_z3_vars_from_state_machine(sm)
    >>> sorted(z3_vars)
    ['counter']
"""

from typing import Dict, Iterable, Union

import z3

from ..model.model import StateMachine, VarDefine

Z3Variable = Union[z3.ArithRef, z3.BoolRef]


def _create_z3_vars_from_var_defines(var_defines: Iterable[VarDefine]) -> Dict[str, Z3Variable]:
    """
    Create Z3 variables from variable definitions.

    :param var_defines: Variable definitions to convert
    :type var_defines: Iterable[VarDefine]
    :return: Dictionary mapping variable names to Z3 variables
    :rtype: Dict[str, Z3Variable]
    :raises ValueError: If a variable type is unsupported
    """
    z3_vars: Dict[str, Z3Variable] = {}

    for var_def in var_defines:
        var_name = var_def.name
        var_type = var_def.type.lower()

        if var_type == 'int':
            z3_vars[var_name] = z3.Int(var_name)
        elif var_type == 'float':
            z3_vars[var_name] = z3.Real(var_name)
        else:
            raise ValueError(
                f"Unsupported variable type '{var_type}' for variable '{var_name}'. "
                f"Supported types: int, float"
            )

    return z3_vars


def create_z3_vars_from_state_machine(state_machine: StateMachine) -> Dict[str, Z3Variable]:
    """
    Create a dictionary of Z3 variables from a state machine.

    The returned dictionary uses variable names from
    :attr:`pyfcstm.model.model.StateMachine.defines` as keys. DSL ``int``
    variables become :func:`z3.Int` variables and DSL ``float`` variables
    become :func:`z3.Real` variables.

    :param state_machine: State machine containing variable definitions
    :type state_machine: StateMachine
    :return: Dictionary mapping variable names to Z3 variables
    :rtype: Dict[str, Z3Variable]
    :raises ValueError: If a variable type is unsupported

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> ast = parse_with_grammar_entry(
        ...     "def float temperature = 25.0; state System { state Idle; [*] -> Idle; }",
        ...     "state_machine_dsl"
        ... )
        >>> sm = parse_dsl_node_to_state_machine(ast)
        >>> z3_vars = create_z3_vars_from_state_machine(sm)
        >>> 'temperature' in z3_vars
        True
    """
    return _create_z3_vars_from_var_defines(state_machine.defines.values())

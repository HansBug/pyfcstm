"""Lifecycle first-cycle encoding helpers.

This module exposes lifecycle helpers used by the first-cycle
``enter``/``during`` SMT-local algorithm.  The implementation lives in
:mod:`pyfcstm.verify.encoding._core`; this topic module documents the intended
import surface.

Example::

    >>> from pyfcstm.dsl.parse import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.verify.encoding.lifecycle import _concrete_during_operations
    >>> code = "def int x = 0; state Root { state A { during { x = x + 2; } } [*] -> A; }"
    >>> machine = parse_dsl_node_to_state_machine(
    ...     parse_with_grammar_entry(code, "state_machine_dsl")
    ... )
    >>> _concrete_during_operations(machine.root_state.substates["A"])[0].var_name
    'x'
"""

from ._core import (
    _action_operations,
    _concrete_during_operations,
    _conditional_conditions_from_expr,
    _conditional_conditions_from_operations,
    _enter_condition_descriptors_for_context,
)

__all__ = [
    "_action_operations",
    "_concrete_during_operations",
    "_conditional_conditions_from_expr",
    "_conditional_conditions_from_operations",
    "_enter_condition_descriptors_for_context",
]

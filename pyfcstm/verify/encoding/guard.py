"""Guard encoding helpers.

This topic module exposes guard translation helpers from
:mod:`pyfcstm.verify.encoding._core`.  It keeps algorithm modules from
depending on the full internal core module when they only need transition
guard encoding.

Example::

    >>> from pyfcstm.dsl.parse import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.verify.encoding.guard import _guard_z3_or_result
    >>> code = "def int x = 0; state Root { state A; state B; [*] -> A; A -> B : if [x > 0]; }"
    >>> machine = parse_dsl_node_to_state_machine(
    ...     parse_with_grammar_entry(code, "state_machine_dsl")
    ... )
    >>> guard, z3_vars, domains, result = _guard_z3_or_result(
    ...     machine.root_state.transitions[1],
    ...     tuple(machine.defines.values()),
    ... )
    >>> guard, sorted(z3_vars), domains, result
    (0 < x, ['x'], (), None)
"""

from ._core import _guard_z3_or_result

__all__ = ["_guard_z3_or_result"]

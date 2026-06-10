"""Root-initial-path and initializer encoding helpers.

The helpers in this module expose the initial-value and root-initial-path
encoding pieces used by SMT-local verification algorithms.  They are thin
re-exports from :mod:`pyfcstm.verify.encoding._core`.

Example::

    >>> import z3
    >>> from pyfcstm.dsl.parse import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.verify.encoding.initial import _build_init_constraints_or_result
    >>> code = "def int x = 0; state Root { state A; [*] -> A; }"
    >>> machine = parse_dsl_node_to_state_machine(
    ...     parse_with_grammar_entry(code, "state_machine_dsl")
    ... )
    >>> _build_init_constraints_or_result(
    ...     tuple(machine.defines.values()),
    ...     {"x": z3.Int("x")},
    ... )
    ((0 == x,), None)
"""

from ._core import (
    _InitialPathContext,
    _InitialPathSearchContext,
    _build_init_constraints_or_result,
    _is_root_initial_leaf,
    _root_initial_path_context,
    _root_initial_path_contexts,
    _root_initial_path_transitions,
    _state_path_from_root,
)

__all__ = [
    "_InitialPathContext",
    "_InitialPathSearchContext",
    "_build_init_constraints_or_result",
    "_is_root_initial_leaf",
    "_root_initial_path_context",
    "_root_initial_path_contexts",
    "_root_initial_path_transitions",
    "_state_path_from_root",
]

"""Transition trigger encoding helpers.

This module exposes transition trigger and ordering helpers.  Trigger encoding
combines optional event booleans, guard expressions, and guard
runtime-definedness constraints without importing diagnostics policy.

Example::

    >>> import z3
    >>> from pyfcstm.dsl.parse import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.verify.encoding.trigger import _transition_trigger_or_result
    >>> code = "def int x = 0; state Root { state A; state B; [*] -> A; A -> B :: Go; }"
    >>> machine = parse_dsl_node_to_state_machine(
    ...     parse_with_grammar_entry(code, "state_machine_dsl")
    ... )
    >>> trigger, domains, result = _transition_trigger_or_result(
    ...     machine.root_state.transitions[1],
    ...     {"x": z3.Int("x")},
    ... )
    >>> trigger, domains, result
    (__event__4:Root1:A2:Go, (), None)
"""

from ._core import (
    _event_bool_name,
    _iter_ordered_outgoing,
    _state_has_definite_stable_entry,
    _transition_has_definite_stable_continuation,
    _transition_payload,
    _transition_trigger_or_result,
)

__all__ = [
    "_event_bool_name",
    "_iter_ordered_outgoing",
    "_state_has_definite_stable_entry",
    "_transition_has_definite_stable_continuation",
    "_transition_payload",
    "_transition_trigger_or_result",
]

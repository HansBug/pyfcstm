"""Transition trigger encoding helpers."""

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

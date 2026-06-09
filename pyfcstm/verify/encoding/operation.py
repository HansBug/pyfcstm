"""Operation-block path-sensitive encoding helpers."""

from ._core import (
    _effect_guard_context_or_result,
    _execute_effects_under_guard_or_result,
    _execute_operation_prefix_conditions_and_vars_or_result,
    _execute_operation_prefix_conditions_or_result,
    _execute_operations_or_result,
)

__all__ = [
    "_effect_guard_context_or_result",
    "_execute_effects_under_guard_or_result",
    "_execute_operation_prefix_conditions_and_vars_or_result",
    "_execute_operation_prefix_conditions_or_result",
    "_execute_operations_or_result",
]

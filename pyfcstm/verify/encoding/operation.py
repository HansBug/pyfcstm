"""Operation-block path-sensitive encoding helpers.

The operation helpers execute concrete FCSTM operation blocks while preserving
path predicates and runtime-definedness constraints.  They are used by effect
and lifecycle algorithms that need the post-state symbolic store.

Example::

    >>> import z3
    >>> from pyfcstm.solver.operation import parse_operations
    >>> from pyfcstm.verify.encoding.operation import _execute_operations_or_result
    >>> ops = parse_operations("x = x + 1;", ["x"])
    >>> env, result = _execute_operations_or_result(ops, {"x": z3.IntVal(1)})
    >>> result is None
    True
    >>> z3.simplify(env["x"])
    2
"""

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

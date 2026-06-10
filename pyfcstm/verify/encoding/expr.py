"""Expression definedness encoding helpers.

This thin module exposes the expression-related helpers implemented in
:mod:`pyfcstm.verify.encoding._core`.  Algorithm modules import from this topic
module when they need guard expression values, ternary condition points, or
runtime-definedness constraints.

Example::

    >>> import z3
    >>> from pyfcstm.model.expr import BinaryOp, Variable
    >>> from pyfcstm.verify.encoding.expr import _expr_z3_and_domains_or_result
    >>> x, y = z3.Ints("x y")
    >>> value, domains, result = _expr_z3_and_domains_or_result(
    ...     BinaryOp(Variable("x"), "/", Variable("y")),
    ...     {"x": x, "y": y},
    ... )
    >>> value, domains, result
    (x/y, (y != 0,), None)
"""

from ._core import (
    _ConditionPoint,
    _append_expr_domain_constraints,
    _binary_z3_or_result,
    _build_type_constraints,
    _definedness_feasibility_or_result,
    _expr_conditions_and_z3_or_result,
    _expr_to_z3_or_result,
    _expr_z3_and_domains_or_result,
    _path_reachability_or_result,
    _ufunc_z3_or_result,
    _unary_z3_or_result,
    _z3_vars,
)

__all__ = [
    "_ConditionPoint",
    "_append_expr_domain_constraints",
    "_binary_z3_or_result",
    "_build_type_constraints",
    "_definedness_feasibility_or_result",
    "_expr_conditions_and_z3_or_result",
    "_expr_to_z3_or_result",
    "_expr_z3_and_domains_or_result",
    "_path_reachability_or_result",
    "_ufunc_z3_or_result",
    "_unary_z3_or_result",
    "_z3_vars",
]

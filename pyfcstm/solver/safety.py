"""Optional expression safety scans for downstream SMT callers.

The core solver and verify algorithms are intentionally full-power by default:
they translate the requested expression and let Z3 try the query.  This module
provides a separate syntactic scanner for callers such as diagnostics adapters
that want to apply their own policy before invoking those core algorithms.

Example::

    >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
    >>> expr = BinaryOp(Variable("x"), "*", Variable("y"))
    >>> check_expr_safety(expr).reason
    'nonlinear'
"""

from dataclasses import dataclass
from typing import Optional, Sequence

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

from ..model.expr import BinaryOp, Expr, UFunc, UnaryOp
from ..model.model import IfBlock, Operation, OperationStatement

SafetyReason = Literal[
    "bitwise",
    "transcendental",
    "double_var_power",
    "variable_exponent",
    "nonlinear",
]

_BITWISE_BINARY_OPERATORS = frozenset({"&", "|", "^", "<<", ">>"})
_TRANSCENDENTAL_FUNCTIONS = frozenset(
    {
        "sin",
        "cos",
        "tan",
        "asin",
        "acos",
        "atan",
        "sinh",
        "cosh",
        "tanh",
        "asinh",
        "acosh",
        "atanh",
        "exp",
        "log",
        "log10",
        "log2",
        "log1p",
        "cbrt",
    }
)


@dataclass(frozen=True)
class SafetyCheck:
    """Result of an optional solver-safety expression scan.

    :param safe: Whether the expression or operation block passes the optional
        downstream policy.
    :type safe: bool
    :param reason: First unsafe reason found, defaults to ``None``.
    :type reason: Optional[SafetyReason], optional
    :param offending_node: First expression node that triggered the unsafe
        result, defaults to ``None``.
    :type offending_node: Optional[pyfcstm.model.expr.Expr], optional

    Example::

        >>> check = SafetyCheck(safe=False, reason="nonlinear")
        >>> check.safe
        False
        >>> check.reason
        'nonlinear'
    """

    safe: bool
    reason: Optional[SafetyReason] = None
    offending_node: Optional[Expr] = None


def _contains_variable(expr: Expr) -> bool:
    """Return whether an expression tree contains at least one variable.

    :param expr: Expression to inspect.
    :type expr: pyfcstm.model.expr.Expr
    :return: ``True`` if a :class:`pyfcstm.model.expr.Variable` appears.
    :rtype: bool

    Example::

        >>> from pyfcstm.model.expr import Integer, Variable
        >>> _contains_variable(Variable("x"))
        True
        >>> _contains_variable(Integer(1))
        False
    """
    return bool(expr.list_variables())


def _unsafe(reason: SafetyReason, offending_node: Expr) -> SafetyCheck:
    """Create an unsafe result for a specific node.

    :param reason: Safety reason.
    :type reason: SafetyReason
    :param offending_node: Node that caused the result.
    :type offending_node: pyfcstm.model.expr.Expr
    :return: Policy rejection result.
    :rtype: SafetyCheck

    Example::

        >>> from pyfcstm.model.expr import Integer
        >>> result = _unsafe("bitwise", Integer(1))
        >>> result.safe
        False
        >>> result.reason
        'bitwise'
    """
    return SafetyCheck(safe=False, reason=reason, offending_node=offending_node)


def check_expr_safety(expr: Optional[Expr]) -> SafetyCheck:
    """Run an optional downstream policy scan over an expression.

    :param expr: Expression to scan, or ``None`` for optional missing
        expressions.
    :type expr: Optional[pyfcstm.model.expr.Expr]
    :return: Safety-policy result.  The first policy-rejected node in pre-order
        traversal is reported when a hazard is found.
    :rtype: SafetyCheck

    Example::

        >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
        >>> check_expr_safety(Integer(1)).safe
        True
        >>> expr = BinaryOp(Variable("x"), "*", Variable("y"))
        >>> check_expr_safety(expr).reason
        'nonlinear'
    """
    if expr is None:
        return SafetyCheck(safe=True)

    if isinstance(expr, BinaryOp):
        if expr.op in _BITWISE_BINARY_OPERATORS:
            return _unsafe("bitwise", expr)
        if expr.op == "*" and _contains_variable(expr.x) and _contains_variable(expr.y):
            return _unsafe("nonlinear", expr)
        if expr.op in {"/", "%"} and _contains_variable(expr.y):
            return _unsafe("nonlinear", expr)
        if expr.op == "**":
            left_has_variable = _contains_variable(expr.x)
            right_has_variable = _contains_variable(expr.y)
            if left_has_variable and right_has_variable:
                return _unsafe("double_var_power", expr)
            if right_has_variable:
                return _unsafe("variable_exponent", expr)

    if isinstance(expr, UnaryOp) and expr.op == "~":
        return _unsafe("bitwise", expr)

    if isinstance(expr, UFunc) and expr.func in _TRANSCENDENTAL_FUNCTIONS:
        return _unsafe("transcendental", expr)

    for child in expr._iter_subs():
        child_result = check_expr_safety(child)
        if not child_result.safe:
            return child_result

    return SafetyCheck(safe=True)


def check_expr_safety_for_effect(ops: Sequence[OperationStatement]) -> SafetyCheck:
    """Run an optional downstream policy scan over an operation block.

    :param ops: Operation statements from an ``enter`` / ``during`` / ``exit``
        / ``effect`` block.
    :type ops: Sequence[OperationStatement]
    :return: First policy-rejected expression result, or a safe result if all
        scanned expressions are acceptable.
    :rtype: SafetyCheck

    Example::

        >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
        >>> from pyfcstm.model.model import Operation
        >>> ops = [Operation("x", BinaryOp(Variable("x"), "*", Variable("y")))]
        >>> check_expr_safety_for_effect(ops).reason
        'nonlinear'
    """
    for statement in ops:
        if isinstance(statement, Operation):
            expr_result = check_expr_safety(statement.expr)
            if not expr_result.safe:
                return expr_result
            continue

        if isinstance(statement, IfBlock):
            for branch in statement.branches:
                condition_result = check_expr_safety(branch.condition)
                if not condition_result.safe:
                    return condition_result

                branch_result = check_expr_safety_for_effect(branch.statements)
                if not branch_result.safe:
                    return branch_result
            continue

        raise TypeError(f"Unknown operation statement type {type(statement)!r}.")

    return SafetyCheck(safe=True)

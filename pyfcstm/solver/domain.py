"""Runtime-definedness translation for solver-layer expressions.

This module keeps FCSTM expression runtime-domain constraints separate from
the Z3 value expression.  Z3 arithmetic operators are total, while FCSTM
runtime expression evaluation is not: division by zero, modulo by zero, and
square root of a negative value are runtime-domain failures.  Callers decide
when to add the returned definedness constraints to a solver.
"""

from collections.abc import Iterable
from dataclasses import dataclass
from typing import Callable, Dict, List, Optional, Sequence, Tuple, Union

import z3

from pyfcstm.model.expr import (
    BinaryOp,
    Boolean,
    ConditionalOp,
    Expr,
    Float,
    Integer,
    UFunc,
    UnaryOp,
    Variable,
)

from .expr import _apply_binary_z3, _apply_ufunc_z3, _apply_unary_z3, expr_to_z3
from .logical import is_sat

_Z3Expr = Union[z3.ArithRef, z3.BoolRef]
_Z3Vars = Dict[str, _Z3Expr]


@dataclass(frozen=True)
class DomainSource:
    """Pure source metadata for domain constraints and failures."""

    label: Optional[str] = None
    step: Optional[int] = None
    snapshot: Optional[str] = None
    prefix_id: Optional[str] = None


@dataclass(frozen=True)
class DomainConstraint:
    """Runtime-definedness constraint plus optional source metadata."""

    constraint: z3.ExprRef
    source: Optional[DomainSource] = None


@dataclass(frozen=True)
class TranslationFailure:
    """Expected expression translation failure in pure solver-layer form."""

    kind: str
    reason: str
    source: Optional[DomainSource] = None


@dataclass(frozen=True)
class BranchFeasibility:
    """Recorded branch reachability query for conditional expressions."""

    selector: z3.ExprRef
    status: str
    source: Optional[DomainSource] = None


@dataclass(frozen=True)
class ExprDomain:
    """Domain-aware translation result for one expression.

    ``expr_constraints`` is reserved for future solver-only value constraints.
    The current translator does not populate it; every path returns ``()``.
    """

    z3_expr: Optional[_Z3Expr]
    expr_constraints: Tuple[z3.ExprRef, ...] = ()
    assumptions: Tuple[z3.ExprRef, ...] = ()
    definedness_constraints: Tuple[DomainConstraint, ...] = ()
    failure: Optional[TranslationFailure] = None
    feasibility_checks: Tuple[BranchFeasibility, ...] = ()


def _failure_from_exception(
    err: Union[NotImplementedError, ValueError, TypeError, z3.Z3Exception],
    source: Optional[DomainSource],
) -> TranslationFailure:
    """Convert an expected translation exception to a pure failure object."""
    if isinstance(err, NotImplementedError):
        return TranslationFailure("not_implemented", str(err), source=source)
    if isinstance(err, ValueError):
        return TranslationFailure("value_error", str(err), source=source)
    if isinstance(err, TypeError):
        return TranslationFailure("type_error", str(err), source=source)
    if isinstance(err, z3.Z3Exception):
        return TranslationFailure("z3_error", str(err), source=source)
    raise AssertionError(f"Unexpected translation exception: {type(err).__name__}") from err


def _failure_result(
    failure: TranslationFailure,
    *,
    assumptions: Sequence[z3.ExprRef],
    definedness_constraints: Sequence[DomainConstraint] = (),
    feasibility_checks: Sequence[BranchFeasibility] = (),
) -> ExprDomain:
    """Build a failed expression-domain result."""
    return ExprDomain(
        z3_expr=None,
        assumptions=tuple(assumptions),
        definedness_constraints=tuple(definedness_constraints),
        failure=failure,
        feasibility_checks=tuple(feasibility_checks),
    )


def _expr_to_z3_or_failure(
    expr: Expr,
    z3_vars: _Z3Vars,
    source: Optional[DomainSource],
) -> Tuple[Optional[_Z3Expr], Optional[TranslationFailure]]:
    """Translate through ``expr_to_z3`` and normalize expected failures."""
    try:
        return expr_to_z3(expr, z3_vars), None
    except NotImplementedError as err:
        # NotImplementedError: expr_to_z3 raises this for supported expression
        # nodes whose math function is intentionally unsupported by Z3.
        return None, _failure_from_exception(err, source)
    except ValueError as err:
        # ValueError: expr_to_z3 raises this for unknown variables, unknown
        # operators, and unsupported expression object types.
        return None, _failure_from_exception(err, source)
    except TypeError as err:
        # TypeError: Python/Z3 operator overloads can reject malformed operand
        # combinations before Z3 wraps the failure.
        return None, _failure_from_exception(err, source)
    except z3.Z3Exception as err:
        # Z3Exception: Z3 rejects sort/operator-domain mismatches.
        return None, _failure_from_exception(err, source)


def _apply_or_failure(
    func: Callable[[], _Z3Expr],
    source: Optional[DomainSource],
) -> Tuple[Optional[_Z3Expr], Optional[TranslationFailure]]:
    """Run a Z3 operation and normalize only documented failure classes."""
    try:
        return func(), None
    except NotImplementedError as err:
        # NotImplementedError: math functions may be intentionally unsupported.
        return None, _failure_from_exception(err, source)
    except ValueError as err:
        # ValueError: operator/function dispatch rejects unknown names.
        return None, _failure_from_exception(err, source)
    except TypeError as err:
        # TypeError: Python/Z3 operators reject unsupported operand sorts.
        return None, _failure_from_exception(err, source)
    except z3.Z3Exception as err:
        # Z3Exception: Z3 rejects sort/operator-domain mismatches.
        return None, _failure_from_exception(err, source)


def _with_parts(
    z3_expr: Optional[_Z3Expr],
    *,
    assumptions: Sequence[z3.ExprRef],
    definedness_constraints: Sequence[DomainConstraint] = (),
    failure: Optional[TranslationFailure] = None,
    feasibility_checks: Sequence[BranchFeasibility] = (),
) -> ExprDomain:
    """Build an expression-domain result from collected pieces."""
    return ExprDomain(
        z3_expr=z3_expr,
        assumptions=tuple(assumptions),
        definedness_constraints=tuple(definedness_constraints),
        failure=failure,
        feasibility_checks=tuple(feasibility_checks),
    )


def _constraint_exprs(items: Sequence[DomainConstraint]) -> Tuple[z3.ExprRef, ...]:
    """Return raw Z3 constraints from domain constraint objects."""
    return tuple(item.constraint for item in items)


def _branch_feasibility(
    selector: z3.ExprRef,
    *,
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    condition_domains: Sequence[DomainConstraint],
    source: Optional[DomainSource],
    timeout_ms: Optional[int],
) -> BranchFeasibility:
    """Check whether one conditional value branch is reachable."""
    result = is_sat(
        (
            *assumptions,
            *path_conditions,
            *_constraint_exprs(condition_domains),
            selector,
        ),
        timeout_ms=timeout_ms,
    )
    status = result.kind if result.kind in ("sat", "unsat") else "unknown"
    return BranchFeasibility(selector=selector, status=status, source=source)


def _translate_expr_domain(
    expr: Expr,
    z3_vars: _Z3Vars,
    *,
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    source: Optional[DomainSource],
    prune_unreachable: bool,
    timeout_ms: Optional[int],
) -> ExprDomain:
    """Recursive implementation for domain-aware expression translation."""
    if isinstance(expr, (Integer, Float, Boolean, Variable)):
        z3_expr, failure = _expr_to_z3_or_failure(expr, z3_vars, source)
        if failure is not None:
            return _failure_result(failure, assumptions=assumptions)
        return _with_parts(z3_expr, assumptions=assumptions)

    if isinstance(expr, ConditionalOp):
        return _translate_conditional_domain(
            expr,
            z3_vars,
            assumptions=assumptions,
            path_conditions=path_conditions,
            source=source,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )

    if isinstance(expr, BinaryOp):
        left = _translate_expr_domain(
            expr.x,
            z3_vars,
            assumptions=assumptions,
            path_conditions=path_conditions,
            source=source,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )
        if left.failure is not None:
            return left
        right = _translate_expr_domain(
            expr.y,
            z3_vars,
            assumptions=assumptions,
            path_conditions=(
                *path_conditions,
                *_constraint_exprs(left.definedness_constraints),
            ),
            source=source,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )
        if right.failure is not None:
            return _failure_result(
                right.failure,
                assumptions=assumptions,
                definedness_constraints=(
                    *left.definedness_constraints,
                    *right.definedness_constraints,
                ),
                feasibility_checks=(
                    *left.feasibility_checks,
                    *right.feasibility_checks,
                ),
            )

        domains = [*left.definedness_constraints, *right.definedness_constraints]
        if expr.op in ("/", "%"):
            try:
                domains.append(DomainConstraint(right.z3_expr != 0, source=source))
            except TypeError as err:
                # TypeError: malformed divisor expressions may not compare to zero.
                return _failure_result(
                    _failure_from_exception(err, source),
                    assumptions=assumptions,
                    definedness_constraints=domains,
                )
            except z3.Z3Exception as err:
                # Z3Exception: Z3 can reject divisor comparison sort mismatches.
                return _failure_result(
                    _failure_from_exception(err, source),
                    assumptions=assumptions,
                    definedness_constraints=domains,
                )

        z3_expr, failure = _apply_or_failure(
            lambda: _apply_binary_z3(
                expr.op,
                left.z3_expr,
                right.z3_expr,
                expr.x,
                expr.y,
                warning_stacklevel=6,
            ),
            source,
        )
        return _with_parts(
            z3_expr,
            assumptions=assumptions,
            definedness_constraints=domains,
            failure=failure,
            feasibility_checks=(
                *left.feasibility_checks,
                *right.feasibility_checks,
            ),
        )

    if isinstance(expr, UnaryOp):
        operand = _translate_expr_domain(
            expr.x,
            z3_vars,
            assumptions=assumptions,
            path_conditions=path_conditions,
            source=source,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )
        if operand.failure is not None:
            return operand
        z3_expr, failure = _apply_or_failure(
            lambda: _apply_unary_z3(
                expr.op,
                operand.z3_expr,
                warning_stacklevel=6,
            ),
            source,
        )
        return _with_parts(
            z3_expr,
            assumptions=assumptions,
            definedness_constraints=operand.definedness_constraints,
            failure=failure,
            feasibility_checks=operand.feasibility_checks,
        )

    if isinstance(expr, UFunc):
        operand = _translate_expr_domain(
            expr.x,
            z3_vars,
            assumptions=assumptions,
            path_conditions=path_conditions,
            source=source,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )
        if operand.failure is not None:
            return operand
        domains = list(operand.definedness_constraints)
        if expr.func == "sqrt":
            try:
                domains.append(DomainConstraint(operand.z3_expr >= 0, source=source))
            except TypeError as err:
                # TypeError: malformed sqrt operands may not compare to zero.
                return _failure_result(
                    _failure_from_exception(err, source),
                    assumptions=assumptions,
                    definedness_constraints=domains,
                )
            except z3.Z3Exception as err:
                # Z3Exception: Z3 can reject sqrt operand sort comparisons.
                return _failure_result(
                    _failure_from_exception(err, source),
                    assumptions=assumptions,
                    definedness_constraints=domains,
                )
        z3_expr, failure = _apply_or_failure(
            lambda: _apply_ufunc_z3(expr.func, operand.z3_expr),
            source,
        )
        return _with_parts(
            z3_expr,
            assumptions=assumptions,
            definedness_constraints=domains,
            failure=failure,
            feasibility_checks=operand.feasibility_checks,
        )

    return _failure_result(
        TranslationFailure(
            "value_error",
            f"Unsupported expression type: {type(expr).__name__}",
            source=source,
        ),
        assumptions=assumptions,
    )


def _translate_conditional_domain(
    expr: ConditionalOp,
    z3_vars: _Z3Vars,
    *,
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    source: Optional[DomainSource],
    prune_unreachable: bool,
    timeout_ms: Optional[int],
) -> ExprDomain:
    """Translate a conditional expression with runtime short-circuit semantics."""
    condition = _translate_expr_domain(
        expr.cond,
        z3_vars,
        assumptions=assumptions,
        path_conditions=path_conditions,
        source=source,
        prune_unreachable=prune_unreachable,
        timeout_ms=timeout_ms,
    )
    if condition.failure is not None:
        return condition

    condition_domains = condition.definedness_constraints
    true_selector = condition.z3_expr
    try:
        false_selector = z3.Not(condition.z3_expr)
    except TypeError as err:
        # TypeError: malformed ternary conditions may not be Boolean values.
        return _failure_result(
            _failure_from_exception(err, source),
            assumptions=assumptions,
            definedness_constraints=condition_domains,
            feasibility_checks=condition.feasibility_checks,
        )
    except z3.Z3Exception as err:
        # Z3Exception: Z3 rejects non-Boolean ternary conditions.
        return _failure_result(
            _failure_from_exception(err, source),
            assumptions=assumptions,
            definedness_constraints=condition_domains,
            feasibility_checks=condition.feasibility_checks,
        )
    feasibility_checks: List[BranchFeasibility] = list(condition.feasibility_checks)
    if prune_unreachable:
        true_check = _branch_feasibility(
            true_selector,
            assumptions=assumptions,
            path_conditions=path_conditions,
            condition_domains=condition_domains,
            source=source,
            timeout_ms=timeout_ms,
        )
        false_check = _branch_feasibility(
            false_selector,
            assumptions=assumptions,
            path_conditions=path_conditions,
            condition_domains=condition_domains,
            source=source,
            timeout_ms=timeout_ms,
        )
        feasibility_checks.extend((true_check, false_check))
        true_reachable = true_check.status != "unsat"
        false_reachable = false_check.status != "unsat"
    else:
        true_reachable = True
        false_reachable = True

    branch_path = (*path_conditions, *_constraint_exprs(condition_domains))
    true_result = false_result = None
    if true_reachable:
        true_result = _translate_expr_domain(
            expr.if_true,
            z3_vars,
            assumptions=assumptions,
            path_conditions=(*branch_path, true_selector),
            source=source,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )
        feasibility_checks.extend(true_result.feasibility_checks)
        if true_result.failure is not None:
            return _failure_result(
                true_result.failure,
                assumptions=assumptions,
                definedness_constraints=(
                    *condition_domains,
                    *true_result.definedness_constraints,
                ),
                feasibility_checks=feasibility_checks,
            )
    if false_reachable:
        false_result = _translate_expr_domain(
            expr.if_false,
            z3_vars,
            assumptions=assumptions,
            path_conditions=(*branch_path, false_selector),
            source=source,
            prune_unreachable=prune_unreachable,
            timeout_ms=timeout_ms,
        )
        feasibility_checks.extend(false_result.feasibility_checks)
        if false_result.failure is not None:
            return _failure_result(
                false_result.failure,
                assumptions=assumptions,
                definedness_constraints=(
                    *condition_domains,
                    *false_result.definedness_constraints,
                ),
                feasibility_checks=feasibility_checks,
            )

    if not true_reachable and not false_reachable:
        return _failure_result(
            TranslationFailure(
                "no_reachable_branch",
                "Conditional expression has no reachable value branch.",
                source=source,
            ),
            assumptions=assumptions,
            definedness_constraints=condition_domains,
            feasibility_checks=feasibility_checks,
        )

    if true_reachable and not false_reachable:
        return _with_parts(
            true_result.z3_expr,
            assumptions=assumptions,
            definedness_constraints=(
                *condition_domains,
                *true_result.definedness_constraints,
            ),
            feasibility_checks=feasibility_checks,
        )
    if false_reachable and not true_reachable:
        return _with_parts(
            false_result.z3_expr,
            assumptions=assumptions,
            definedness_constraints=(
                *condition_domains,
                *false_result.definedness_constraints,
            ),
            feasibility_checks=feasibility_checks,
        )

    domains: List[DomainConstraint] = list(condition_domains)
    for item in true_result.definedness_constraints:
        domains.append(
            DomainConstraint(
                z3.Implies(condition.z3_expr, item.constraint),
                source=item.source,
            )
        )
    for item in false_result.definedness_constraints:
        domains.append(
            DomainConstraint(
                z3.Implies(z3.Not(condition.z3_expr), item.constraint),
                source=item.source,
            )
        )
    z3_expr, failure = _apply_or_failure(
        lambda: z3.If(condition.z3_expr, true_result.z3_expr, false_result.z3_expr),
        source,
    )
    return _with_parts(
        z3_expr,
        assumptions=assumptions,
        definedness_constraints=domains,
        failure=failure,
        feasibility_checks=feasibility_checks,
    )


def translate_expr_domain(
    expr: Expr,
    z3_vars: _Z3Vars,
    *,
    assumptions: Sequence[z3.ExprRef] = (),
    path_conditions: Sequence[z3.ExprRef] = (),
    source: Optional[DomainSource] = None,
    prune_unreachable: bool = True,
    timeout_ms: Optional[int] = None,
) -> ExprDomain:
    """Translate an expression and return runtime-definedness metadata.

    :param expr: Expression to translate.
    :type expr: Expr
    :param z3_vars: Symbolic variable mapping.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param assumptions: Caller-known facts preserved on the result.
    :type assumptions: Sequence[z3.ExprRef], optional
    :param path_conditions: Current path predicates used only for branch
        feasibility pruning; they are not stored on the result.
    :type path_conditions: Sequence[z3.ExprRef], optional
    :param source: Optional pure source metadata.
    :type source: Optional[DomainSource], optional
    :param prune_unreachable: Whether to skip value branches proved unreachable,
        defaults to ``True``.
    :type prune_unreachable: bool, optional
    :param timeout_ms: Optional timeout for branch reachability checks.
    :type timeout_ms: Optional[int], optional
    :return: Domain-aware expression translation.
    :rtype: ExprDomain
    """
    return _translate_expr_domain(
        expr,
        z3_vars,
        assumptions=tuple(assumptions),
        path_conditions=tuple(path_conditions),
        source=source,
        prune_unreachable=prune_unreachable,
        timeout_ms=timeout_ms,
    )


def merge_definedness_constraints(*items) -> Tuple[DomainConstraint, ...]:
    """Flatten expression-domain and domain-constraint inputs in order.

    Each returned constraint must hold at the evaluation point.  The helper does
    not run a solver and does not remove contradictory constraints.
    """
    merged: List[DomainConstraint] = []
    for item in items:
        if isinstance(item, DomainConstraint):
            merged.append(item)
        elif isinstance(item, ExprDomain):
            merged.extend(item.definedness_constraints)
        elif isinstance(item, Iterable) and not isinstance(item, (str, bytes)):
            for sub_item in item:
                if not isinstance(sub_item, DomainConstraint):
                    raise TypeError(
                        "Unsupported definedness item: {type_name}".format(
                            type_name=type(sub_item).__name__,
                        )
                    )
                merged.append(sub_item)
        else:
            raise TypeError(
                "Unsupported definedness item: {type_name}".format(
                    type_name=type(item).__name__,
                )
            )
    return tuple(merged)


__all__ = [
    "BranchFeasibility",
    "DomainConstraint",
    "DomainSource",
    "ExprDomain",
    "TranslationFailure",
    "merge_definedness_constraints",
    "translate_expr_domain",
]

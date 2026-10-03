"""Runtime-definedness translation for solver-layer expressions.

This module keeps FCSTM expression runtime-domain constraints separate from
the Z3 value expression.  Z3 arithmetic operators are total, while FCSTM
runtime expression evaluation is not: division by zero, modulo by zero, zero
raised to a negative power, a negative number raised to a fractional power,
and square root of a negative value are runtime-domain failures.  Callers
decide when to add the returned definedness constraints to a solver.

Translation uses the symbolic interpretation of :mod:`pyfcstm.semantics`, so
the value and definedness semantics are those of the operator catalog, and
the right operand of ``&&``, ``||`` and ``=>`` contributes constraints only
under the condition in which it is evaluated.

Example::

    >>> import z3
    >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
    >>> from pyfcstm.solver.domain import translate_expr_domain
    >>> # Division produces both a value expression and a divisor guard.
    >>> expr = BinaryOp(x=Variable("x"), op="/", y=Integer(2))
    >>> result = translate_expr_domain(expr, {"x": z3.Int("x")})
    >>> result.failure is None
    True
    >>> len(result.definedness_constraints)
    1
"""

from collections.abc import Iterable
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Sequence, Tuple, Union

import z3

from pyfcstm.model.expr import Expr

from .logical import is_sat
from ..semantics.adapters import expression_from_model
from ..semantics.symbolic import (
    ConditionObservation,
    SymbolicFailure,
    SymbolicSession,
    translate,
)

_Z3Expr = Union[z3.ArithRef, z3.BoolRef]
_Z3Vars = Dict[str, _Z3Expr]


@dataclass(frozen=True)
class DomainSource:
    """Pure source metadata for domain constraints and failures.

    This object records where a solver-layer runtime-definedness constraint or
    translation failure came from without importing verification or diagnostics
    types.  All fields are optional so callers can attach only the provenance
    they know at the current expression point.

    :param label: Human-readable source label, defaults to ``None``.
    :type label: Optional[str], optional
    :param step: Operation-step index associated with the source, defaults to
        ``None``.
    :type step: Optional[int], optional
    :param snapshot: Name of the symbolic snapshot, defaults to ``None``.
    :type snapshot: Optional[str], optional
    :param prefix_id: Path or branch prefix identifier, defaults to ``None``.
    :type prefix_id: Optional[str], optional
    :param operation: Name of the operation whose domain this constraint guards,
        such as ``"division"`` or ``"sqrt"``, defaults to ``None``.
    :type operation: Optional[str], optional

    Example::

        >>> # Callers attach only the source fields they know.
        >>> source = DomainSource(label="guard", step=0)
        >>> source.label
        'guard'
        >>> DomainSource(label="assumption", operation="sqrt").operation
        'sqrt'
    """

    label: Optional[str] = None
    step: Optional[int] = None
    snapshot: Optional[str] = None
    prefix_id: Optional[str] = None
    #: Two operations can produce domain conditions of the same shape -- a
    #: divisor check and a non-negativity check both compare one operand against
    #: zero -- so a consumer cannot recover the operation from the constraint.
    #: Recording it here is what lets an explanation name the real operation
    #: instead of guessing one.
    operation: Optional[str] = None


@dataclass(frozen=True)
class DomainConstraint:
    """Runtime-definedness constraint plus optional source metadata.

    :param constraint: Z3 predicate that must hold for FCSTM runtime expression
        evaluation to be defined.
    :type constraint: z3.ExprRef
    :param source: Optional source metadata for diagnostics or evidence,
        defaults to ``None``.
    :type source: Optional[DomainSource], optional
    :param kind: Catalog error kind the constraint rules out, such as
        ``"division_by_zero"``, or ``None`` when unknown; not compared,
        defaults to ``None``.
    :type kind: Optional[str], optional

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> # The constraint records the runtime precondition for a divisor.
        >>> item = DomainConstraint(x != 0, DomainSource(label="divisor"))
        >>> item.source.label
        'divisor'
    """

    constraint: z3.ExprRef
    source: Optional[DomainSource] = None
    kind: Optional[str] = field(default=None, compare=False, repr=False)


@dataclass(frozen=True)
class TranslationFailure:
    """Expected expression translation failure in pure solver-layer form.

    :param kind: Normalized failure kind such as ``"not_implemented"`` or
        ``"z3_error"``.
    :type kind: str
    :param reason: Human-readable failure reason.
    :type reason: str
    :param source: Optional source metadata, defaults to ``None``.
    :type source: Optional[DomainSource], optional

    Example::

        >>> # Failures remain pure solver-layer data without verify imports.
        >>> failure = TranslationFailure("value_error", "bad expression")
        >>> failure.kind
        'value_error'
    """

    kind: str
    reason: str
    source: Optional[DomainSource] = None


@dataclass(frozen=True)
class BranchFeasibility:
    """Recorded branch reachability query for conditional expressions.

    :param selector: Z3 predicate selecting the branch.
    :type selector: z3.ExprRef
    :param status: Normalized reachability status: ``"sat"``, ``"unsat"``,
        or ``"unknown"``.
    :type status: str
    :param source: Optional source metadata, defaults to ``None``.
    :type source: Optional[DomainSource], optional

    Example::

        >>> import z3
        >>> # A satisfiable selector means the branch may contribute evidence.
        >>> check = BranchFeasibility(z3.BoolVal(True), "sat")
        >>> check.status
        'sat'
    """

    selector: z3.ExprRef
    status: str
    source: Optional[DomainSource] = None


@dataclass(frozen=True)
class ExprDomain:
    """Domain-aware translation result for one expression.

    ``expr_constraints`` is reserved for future solver-only value constraints.
    The current translator does not populate it; every path returns ``()``.

    :param z3_expr: Translated Z3 value expression, or ``None`` when
        translation failed.
    :type z3_expr: Optional[Union[z3.ArithRef, z3.BoolRef]]
    :param expr_constraints: Solver-only constraints associated with the value
        expression, defaults to ``()``.
    :type expr_constraints: Tuple[z3.ExprRef, ...], optional
    :param assumptions: Caller-supplied facts preserved on the result, defaults
        to ``()``.
    :type assumptions: Tuple[z3.ExprRef, ...], optional
    :param definedness_constraints: Runtime-definedness constraints that must
        hold before using :attr:`z3_expr`, defaults to ``()``.
    :type definedness_constraints: Tuple[DomainConstraint, ...], optional
    :param failure: Expected translation failure, defaults to ``None``.
    :type failure: Optional[TranslationFailure], optional
    :param feasibility_checks: Branch reachability checks performed while
        pruning conditional expressions, defaults to ``()``.
    :type feasibility_checks: Tuple[BranchFeasibility, ...], optional

    Example::

        >>> import z3
        >>> # A minimal successful result only needs a translated value.
        >>> result = ExprDomain(z3.IntVal(1))
        >>> result.z3_expr
        1
    """

    z3_expr: Optional[_Z3Expr]
    expr_constraints: Tuple[z3.ExprRef, ...] = ()
    assumptions: Tuple[z3.ExprRef, ...] = ()
    definedness_constraints: Tuple[DomainConstraint, ...] = ()
    failure: Optional[TranslationFailure] = None
    feasibility_checks: Tuple[BranchFeasibility, ...] = ()


def _check(facts: Sequence[z3.ExprRef], timeout_ms: Optional[int]) -> str:
    return is_sat(tuple(facts), timeout_ms=timeout_ms).kind


def _translate_expr_domain(
    expr: Expr,
    z3_vars: _Z3Vars,
    *,
    assumptions: Sequence[z3.ExprRef],
    path_conditions: Sequence[z3.ExprRef],
    source: Optional[DomainSource],
    prune_unreachable: bool,
    timeout_ms: Optional[int],
    observe_conditions: bool = False,
    checker=None,
) -> Tuple[ExprDomain, Tuple[ConditionObservation, ...]]:
    """Translate an expression and also return the tested conditions.

    :param expr: Expression to translate.
    :type expr: pyfcstm.model.expr.Expr
    :param z3_vars: Variable-name to Z3 expression mapping.
    :type z3_vars: Dict[str, Union[z3.ArithRef, z3.BoolRef]]
    :param assumptions: Caller-known facts preserved on the result.
    :type assumptions: Sequence[z3.ExprRef]
    :param path_conditions: Predicates needed to reach the expression.
    :type path_conditions: Sequence[z3.ExprRef]
    :param source: Optional source metadata for constraints and failures.
    :type source: Optional[DomainSource]
    :param prune_unreachable: Whether to skip lazy branches proved unreachable.
    :type prune_unreachable: bool
    :param timeout_ms: Optional solver timeout for branch reachability checks.
    :type timeout_ms: Optional[int]
    :param observe_conditions: Whether to record the conditions tested by
        conditional expressions, defaults to ``False``.
    :type observe_conditions: bool, optional
    :param checker: Reachability checker replacing the solver's
        :func:`pyfcstm.solver.logical.is_sat`, defaults to ``None``.
    :type checker: Optional[Callable[[Sequence[z3.ExprRef], Optional[int]], str]], optional
    :return: Domain-aware translation and the observed conditions.
    :rtype: Tuple[ExprDomain, Tuple[pyfcstm.semantics.symbolic.ConditionObservation, ...]]
    """
    assumptions = tuple(assumptions)
    session = SymbolicSession(
        assumptions=assumptions,
        path_conditions=tuple(path_conditions),
        checker=(checker or _check) if prune_unreachable else None,
        timeout_ms=timeout_ms,
        observe_conditions=observe_conditions,
    )
    failure = None
    value = None
    try:
        value, _ = translate(expression_from_model(expr), z3_vars, session)
    except TypeError as err:
        # TypeError: the object is not a model expression.
        failure = TranslationFailure("value_error", str(err), source=source)
    except SymbolicFailure as err:
        # SymbolicFailure: the expression has no Z3 translation, for example
        # an unsupported function or a non-Boolean logical operand.
        failure = TranslationFailure(err.kind, err.reason, source=source)
    result = ExprDomain(
        z3_expr=value,
        assumptions=assumptions,
        definedness_constraints=tuple(
            DomainConstraint(fact.constraint, source=source, kind=fact.kind)
            for fact in session.definedness
        ),
        failure=failure,
        feasibility_checks=tuple(
            BranchFeasibility(check.selector, check.status, source=source)
            for check in session.checks
        ),
    )
    return result, tuple(session.conditions)


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
    :type expr: pyfcstm.model.expr.Expr
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

    Example::

        >>> import z3
        >>> from pyfcstm.model.expr import BinaryOp, Integer, Variable
        >>> # Runtime-definedness stays separate from the Z3 value expression.
        >>> expr = BinaryOp(x=Variable("x"), op="/", y=Integer(3))
        >>> result = translate_expr_domain(expr, {"x": z3.Int("x")})
        >>> result.failure is None
        True
        >>> bool(result.definedness_constraints)
        True
    """
    return _translate_expr_domain(
        expr,
        z3_vars,
        assumptions=assumptions,
        path_conditions=path_conditions,
        source=source,
        prune_unreachable=prune_unreachable,
        timeout_ms=timeout_ms,
    )[0]


def merge_definedness_constraints(*items) -> Tuple[DomainConstraint, ...]:
    """Flatten expression-domain and domain-constraint inputs in order.

    Each returned constraint must hold at the evaluation point.  The helper does
    not run a solver and does not remove contradictory constraints.

    :param items: Domain constraints, :class:`ExprDomain` objects, or iterables
        of domain constraints to flatten.
    :type items: object
    :return: Domain constraints in source order.
    :rtype: Tuple[DomainConstraint, ...]
    :raises TypeError: If any item is not a supported domain-constraint shape.

    Example::

        >>> import z3
        >>> # Flattening preserves the exact constraint object supplied.
        >>> item = DomainConstraint(z3.Int("x") != 0)
        >>> merge_definedness_constraints(item) == (item,)
        True
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

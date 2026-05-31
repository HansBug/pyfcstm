"""Small logical predicates around Z3 solver checks.

This module provides thin, timeout-aware wrappers for the satisfiability,
validity, and overlap queries needed by the verify algorithms.  The wrappers
intentionally keep the result shape small so callers can handle ``unknown`` and
``timeout`` without parsing Z3-specific status objects.
"""

from dataclasses import dataclass
from typing import List, Optional, cast

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

import z3


@dataclass(frozen=True)
class SatResult:
    """Result returned by solver logical helpers.

    :param kind: Solver outcome.  ``'sat'`` and ``'unsat'`` keep their normal
        satisfiability meaning for :func:`is_sat` and :func:`is_overlap`; for
        :func:`is_valid`, ``'sat'`` means the input formula is valid and
        ``'unsat'`` means it is not valid.
    :type kind: Literal['sat', 'unsat', 'unknown', 'timeout']
    :param model: Z3 model for satisfiable :func:`is_sat` calls when explicitly
        requested, defaults to ``None``.
    :type model: Optional[z3.ModelRef], optional
    """

    kind: Literal["sat", "unsat", "unknown", "timeout"]
    model: Optional[z3.ModelRef] = None


def _check_solver(solver: z3.Solver, *, get_model: bool = False) -> SatResult:
    """Run a configured solver and normalize the Z3 result.

    :param solver: Z3 solver with all constraints and options already set.
    :type solver: z3.Solver
    :param get_model: Whether to include a model for satisfiable results,
        defaults to ``False``.
    :type get_model: bool, optional
    :return: Normalized solver result.
    :rtype: SatResult
    """
    result = solver.check()
    if result == z3.sat:
        return SatResult(kind="sat", model=solver.model() if get_model else None)
    if result == z3.unsat:
        return SatResult(kind="unsat")

    reason = solver.reason_unknown()
    if reason == "timeout":
        return SatResult(kind="timeout")
    return SatResult(kind="unknown")


def is_sat(
    constraints: List[z3.ExprRef], *, timeout_ms: int, get_model: bool = False
) -> SatResult:
    """Check whether a list of Z3 constraints is satisfiable.

    :param constraints: Constraints to add to a fresh Z3 solver.
    :type constraints: List[z3.ExprRef]
    :param timeout_ms: Z3 timeout in milliseconds.  This is keyword-only and
        required by design.
    :type timeout_ms: int
    :param get_model: Whether to return a model when the constraints are
        satisfiable, defaults to ``False``.
    :type get_model: bool, optional
    :return: Satisfiability result.
    :rtype: SatResult

    Example::

        >>> import z3
        >>> x = z3.Int('x')
        >>> is_sat([x == 1], timeout_ms=1000).kind
        'sat'
    """
    solver = z3.Solver()
    solver.set("timeout", timeout_ms)
    solver.add(*constraints)
    return _check_solver(solver, get_model=get_model)


def is_valid(formula: z3.ExprRef, *, timeout_ms: int) -> SatResult:
    """Check whether a Z3 formula is valid.

    The helper checks the satisfiability of ``Not(formula)``.  The result kind
    is flipped for definite outcomes: ``'sat'`` means the original formula is
    valid, and ``'unsat'`` means the original formula is not valid.  ``unknown``
    and ``timeout`` are propagated unchanged.

    :param formula: Formula to prove valid.
    :type formula: z3.ExprRef
    :param timeout_ms: Z3 timeout in milliseconds.  This is keyword-only and
        required by design.
    :type timeout_ms: int
    :return: Validity result.
    :rtype: SatResult
    """
    negated_formula = cast(z3.ExprRef, z3.Not(formula))
    negated = is_sat([negated_formula], timeout_ms=timeout_ms)
    if negated.kind == "sat":
        return SatResult(kind="unsat")
    if negated.kind == "unsat":
        return SatResult(kind="sat")
    return negated


def is_overlap(
    formula_a: z3.ExprRef, formula_b: z3.ExprRef, *, timeout_ms: int
) -> SatResult:
    """Check whether two formulas can hold at the same time.

    :param formula_a: First formula.
    :type formula_a: z3.ExprRef
    :param formula_b: Second formula.
    :type formula_b: z3.ExprRef
    :param timeout_ms: Z3 timeout in milliseconds.  This is keyword-only and
        required by design.
    :type timeout_ms: int
    :return: ``'sat'`` if the formulas overlap, ``'unsat'`` if they are
        disjoint, or an indeterminate solver result.
    :rtype: SatResult
    """
    overlap_formula = cast(z3.ExprRef, z3.And(formula_a, formula_b))
    return is_sat([overlap_formula], timeout_ms=timeout_ms)

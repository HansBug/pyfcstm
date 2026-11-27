"""Small logical predicates around Z3 solver checks.

This module provides thin wrappers for satisfiability, validity, and overlap
queries needed by the verify algorithms.  The wrappers keep the result shape
small so callers can handle ``unknown`` and ``timeout`` without parsing
Z3-specific status objects.

The helpers treat ``timeout_ms=None`` as the no-timeout path and do not configure
Z3's ``timeout`` parameter in that case.  Any non-``None`` value is forwarded to
Z3 unchanged.  Callers that need a bounded resource policy must validate their
own budget before calling these infrastructure helpers.

Example::

    >>> import z3
    >>> x = z3.Int("x")
    >>> is_sat([x == 1]).kind
    'sat'
    >>> is_valid(x == x).kind
    'sat'
"""

import contextlib
import threading
from dataclasses import dataclass
from typing import Dict, Iterable, Iterator, Optional, Tuple, cast

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

    Example::

        >>> result = SatResult(kind="unsat")
        >>> result.kind
        'unsat'
        >>> result.model is None
        True
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

    Example::

        >>> import z3
        >>> solver = z3.Solver()
        >>> solver.add(z3.Int("x") == 1)
        >>> _check_solver(solver).kind
        'sat'
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
    constraints: Iterable[z3.ExprRef],
    *,
    timeout_ms: Optional[int] = None,
    get_model: bool = False,
) -> SatResult:
    """Check whether an iterable of Z3 constraints is satisfiable.

    The constraints are solved in a Z3 context created for this call, so the
    answer depends on the constraints alone and not on what the process solved
    before. For a non-linear query that matters: an earlier model extracted from
    the shared main context could turn ``sat`` into ``unknown``. A returned model
    is translated back into the context of the constraints.

    :param constraints: Constraints to add to a fresh Z3 solver.
    :type constraints: Iterable[z3.ExprRef]
    :param timeout_ms: Optional value forwarded unchanged to Z3's ``timeout``
        parameter.  ``None`` means the helper does not configure a solver
        timeout.  Values rejected by Z3 propagate as Z3 errors; callers that
        need a finite positive budget must validate it before calling, defaults
        to ``None``.
    :type timeout_ms: Optional[int], optional
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
    constraints = tuple(constraints)
    memo = None
    memo_key = None
    if timeout_ms is None and not get_model:
        # Without a timeout and without a model the answer is a function of
        # the constraints alone, which is exactly what the private context
        # below guarantees.  Nothing constrains an empty conjunction, and,
        # while :func:`answer_memo` is open, a conjunction that was already
        # decided keeps its answer.
        if not constraints:
            return _SAT
        memo = getattr(_MEMO, "table", None)
        if memo is not None:
            memo_key = _memo_key(constraints)
            if memo_key is not None:
                known = memo.get(memo_key)
                if known is not None:
                    return known[0]
    # Z3 keeps state in the context it works in, and for a non-linear query
    # that state decides whether the answer is ``sat`` or ``unknown``: one
    # model extracted earlier in the process, from any solver of the shared
    # main context, was enough to change it. Every call therefore works in a
    # context of its own, so the answer depends on the constraints alone.
    source = constraints[0].ctx if constraints else z3.main_ctx()
    context = z3.Context()
    solver = z3.Solver(ctx=context)
    if timeout_ms is not None:
        solver.set("timeout", timeout_ms)
    solver.add(*(item.translate(context) for item in constraints))
    result = _check_solver(solver, get_model=get_model)
    if result.model is not None:
        return SatResult(kind=result.kind, model=result.model.translate(source))
    if memo_key is not None and result.kind in ("sat", "unsat"):
        if len(memo) >= _MEMO.limit:
            memo.clear()
        # The constraints are stored with the answer: a Z3 term id is only
        # unique while its term is alive, so the entry keeps them alive.
        memo[memo_key] = (result, constraints)
    return result


_SAT = SatResult(kind="sat")


class _MemoSlot(threading.local):
    """Per-thread table of the definite answers of the open :func:`answer_memo`.

    :ivar table: Answers by query key, or ``None`` when no memo is open.
    :vartype table: Optional[Dict[tuple, tuple]]
    :ivar limit: Number of answers after which the table is emptied.
    :vartype limit: int
    """

    def __init__(self) -> None:
        self.table: Optional[Dict[tuple, tuple]] = None
        self.limit = 0


_MEMO = _MemoSlot()


@contextlib.contextmanager
def answer_memo(limit: int = 1024) -> Iterator[None]:
    """Remember the definite answers of :func:`is_sat` while the block runs.

    A caller that asks the same question again and again, as building a
    bounded-model-checking formula does for every step, can open a memo around
    that work.  Inside it, a query without timeout and without a model is
    solved once per distinct sequence of constraint terms; ``unknown`` and
    ``timeout`` answers are never kept.  The table is dropped when the
    outermost block exits, and a block opened inside another one joins it and
    keeps the limit of the outer one.  Answers keep their constraint terms
    alive, so the table is emptied whenever it holds ``limit`` of them.

    :param limit: Number of remembered answers after which the table is
        emptied, defaults to ``1024``.
    :type limit: int, optional
    :return: A context manager yielding ``None``.
    :rtype: Iterator[None]

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> with answer_memo():
        ...     first = is_sat([x > 1, x < 3])
        ...     second = is_sat([x > 1, x < 3])
        >>> first.kind, second is first
        ('sat', True)
        >>> is_sat([x > 1, x < 3]) is first
        False
    """
    if _MEMO.table is not None:
        yield
        return
    _MEMO.table = {}
    _MEMO.limit = limit
    try:
        yield
    finally:
        _MEMO.table = None


def _memo_key(constraints: Tuple[z3.ExprRef, ...]) -> Optional[tuple]:
    """Return a key naming a constraint sequence by the identity of its terms.

    Terms of one context are hash-consed, so two structurally equal terms share
    one id for as long as either is alive.  A sequence mixing contexts has no
    key and is always solved.

    :param constraints: Constraints of one satisfiability query.
    :type constraints: Tuple[z3.ExprRef, ...]
    :return: Hashable key, or ``None`` when the query must not be memoised.
    :rtype: Optional[tuple]

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> low, high = x > 0, x < 2
        >>> _memo_key((low, high)) == _memo_key((x > 0, x < 2))
        True
        >>> _memo_key((low,)) == _memo_key((high,))
        False
    """
    context = constraints[0].ctx
    context_ref = context.ref()
    ids = []
    for item in constraints:
        if item.ctx is not context:
            return None
        ids.append(_ast_id(context_ref, item.as_ast()))
    return (id(context), tuple(ids))


_ast_id = z3.Z3_get_ast_id


def is_valid(formula: z3.ExprRef, *, timeout_ms: Optional[int] = None) -> SatResult:
    """Check whether a Z3 formula is valid.

    The helper checks the satisfiability of ``Not(formula)``.  The result kind
    is flipped for definite outcomes: ``'sat'`` means the original formula is
    valid, and ``'unsat'`` means the original formula is not valid.  ``unknown``
    and ``timeout`` are propagated unchanged.

    :param formula: Formula to prove valid.
    :type formula: z3.ExprRef
    :param timeout_ms: Optional value forwarded through :func:`is_sat`.  ``None``
        means no solver timeout is configured, defaults to ``None``.
    :type timeout_ms: Optional[int], optional
    :return: Validity result.
    :rtype: SatResult

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> is_valid(x == x).kind
        'sat'
        >>> is_valid(x > 0).kind
        'unsat'
    """
    negated_formula = cast(z3.ExprRef, z3.Not(formula))
    negated = is_sat([negated_formula], timeout_ms=timeout_ms)
    if negated.kind == "sat":
        return SatResult(kind="unsat")
    if negated.kind == "unsat":
        return SatResult(kind="sat")
    return negated


def is_overlap(
    formula_a: z3.ExprRef,
    formula_b: z3.ExprRef,
    *,
    timeout_ms: Optional[int] = None,
) -> SatResult:
    """Check whether two formulas can hold at the same time.

    :param formula_a: First formula.
    :type formula_a: z3.ExprRef
    :param formula_b: Second formula.
    :type formula_b: z3.ExprRef
    :param timeout_ms: Optional value forwarded through :func:`is_sat`.  ``None``
        means no solver timeout is configured, defaults to ``None``.
    :type timeout_ms: Optional[int], optional
    :return: ``'sat'`` if the formulas overlap, ``'unsat'`` if they are
        disjoint, or an indeterminate solver result.
    :rtype: SatResult

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> is_overlap(x > 0, x < 2).kind
        'sat'
        >>> is_overlap(x > 0, x < 0).kind
        'unsat'
    """
    overlap_formula = cast(z3.ExprRef, z3.And(formula_a, formula_b))
    return is_sat([overlap_formula], timeout_ms=timeout_ms)

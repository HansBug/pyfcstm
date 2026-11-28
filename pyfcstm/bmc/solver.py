"""Shared Z3 construction and checking-budget primitives for the BMC pipeline.

The BMC solver uses one monotonic optional budget across primary solving,
feasibility localization, and later refinement checks.  ``None`` deliberately
means that no Z3 timeout is configured and no hidden deadline is introduced.
This module contains solver selection and budget/check mechanics; verdict interpretation,
source provenance, and explanation policy belong to other BMC layers.

The leading underscore on implementation helper names is intentional. They
are shared internal primitives, not part of the public BMC API.  Their exact
``check_started`` and reason semantics are documented here because later
internal modules depend on them.

This module is an extraction of primitives that previously lived inside the
witness layer, and the extraction is behavior-preserving except for one
documented point: :meth:`_SolveBudget.remaining_ms` now rounds a partial
millisecond up instead of truncating it.  A finite budget therefore performs
one more real check where the predecessor would have reported
``deadline_exhausted_before_check`` with up to a millisecond still left.

Example::

    >>> import z3
    >>> budget = _SolveBudget(None)
    >>> _check_with_budget(z3.Solver(), budget)[0]
    'sat'
"""

from __future__ import annotations

import functools
import math
import time
from typing import (
    Any,
    Callable,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import z3

from ..solver.context import (
    Deferred,
    IsolatedSolver,
    current_owner,
    declare,
    isolated_owner,
)
from .errors import BmcBuildError

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

BmcSolveStatus = Literal["sat", "unsat", "unknown", "timeout"]

SOLVER_PROFILES = ("default", "logic", "tactic")
SOLVER_CONTEXTS = ("fresh", "shared")
_LOGIC_PROBES = (
    ("QF_LIA", "is-qflia"),
    ("QF_LRA", "is-qflra"),
    ("QF_LIRA", "is-qflira"),
    ("QF_NIA", "is-qfnia"),
    ("QF_NRA", "is-qfnra"),
    ("NIRA", "is-nira"),
)

_F = TypeVar("_F", bound=Callable[..., Any])


def _core_parts(core: Any) -> Tuple[z3.BoolRef, ...]:
    """Return the four formulas of a core, or ``()`` for anything else.

    :param core: Candidate :class:`pyfcstm.bmc.relation.BmcCoreFormula`.
    :type core: Any
    :return: Domain, transition, initial and environment formulas.
    :rtype: Tuple[z3.BoolRef, ...]
    """
    parts = tuple(
        getattr(core, name, None)
        for name in (
            "domain_formula",
            "transition_formula",
            "initial_formula",
            "environment_formula",
        )
    )
    return parts if all(isinstance(part, z3.BoolRef) for part in parts) else ()


def _resolving_unsliced(function: _F) -> _F:
    """Complete a waiting declaration once the unsliced core is known.

    Wraps the function that turns a sliced core into the unsliced one.  When
    the solve in progress is waiting on a sliced core, the declaration is
    made from the sliced and the unsliced formulas together, before any
    solver exists.

    :param function: Function mapping a core to its unsliced core.
    :type function: Callable[..., Any]
    :return: Wrapper with the same signature.
    :rtype: Callable[..., Any]
    """

    @functools.wraps(function)
    def wrapper(core: Any) -> Any:
        full = function(core)
        owner = current_owner()
        if (
            full is not core
            and owner is not None
            and owner.linear
            and owner.linear[-1][0] is None
        ):
            terms = tuple(owner.deferred) + _core_parts(full)
            del owner.linear[-1]
            owner.deferred = ()
            owner.linear.append(declare(owner, terms))
        return full

    return cast(_F, wrapper)


def _core_fragment(
    core: Any = None, *args: Any, **kwargs: Any
) -> Union[bool, Tuple[z3.BoolRef, ...]]:
    """Return the formulas a solve over a core formula may assert.

    A core that cone slicing actually shortened is answered with a
    :class:`Deferred` tuple: such a solve also reaches the unsliced formula,
    which is not known here.

    :param core: First argument of the wrapped function, expected to be a
        :class:`pyfcstm.bmc.relation.BmcCoreFormula`.
    :type core: Any
    :return: Domain, transition, initial and environment formulas, as a
        :class:`Deferred` tuple for a sliced core; ``False`` when the caller
        asked for ``solver_context="shared"``; ``()`` when the argument is
        something else and the function will reject it.
    :rtype: Union[bool, Tuple[z3.BoolRef, ...]]
    """
    if kwargs.get("solver_context") == "shared":
        return False
    parts = _core_parts(core)
    if parts and getattr(getattr(core, "cone_slice", None), "dropped_variables", None):
        return Deferred(parts)
    return parts


def _property_fragment(
    formula: Any = None, *args: Any, **kwargs: Any
) -> Union[bool, Tuple[z3.BoolRef, ...]]:
    """Return the formulas a solve of a property formula may assert.

    :param formula: First argument of the wrapped function, expected to be a
        :class:`pyfcstm.bmc.properties.BmcPropertyFormula`.
    :type formula: Any
    :return: Core formulas, objective and response suffix, as a
        :class:`Deferred` tuple when the core was sliced; ``False`` when the
        caller asked for ``solver_context="shared"``; ``()`` when the
        argument is something else and the function will reject it.
    :rtype: Union[bool, Tuple[z3.BoolRef, ...]]
    """
    if kwargs.get("solver_context") == "shared":
        return False
    core = _core_fragment(getattr(formula, "core", None))
    rest = (
        getattr(formula, "objective_formula", None),
        getattr(formula, "incomplete_formula", None),
    )
    if not core or not all(isinstance(part, z3.BoolRef) for part in rest):
        return ()
    if isinstance(core, Deferred):
        return Deferred(tuple(core) + cast(Tuple[z3.BoolRef, ...], rest))
    return cast(Tuple[z3.BoolRef, ...], core) + cast(Tuple[z3.BoolRef, ...], rest)


def _solver_for_profile(
    profile: str, expressions: Sequence[z3.ExprRef] = ()
) -> Tuple[Union[z3.Solver, "IsolatedSolver"], Optional[str]]:
    """Build a solver without asserting or rewriting the supplied expressions.

    During a solve declared linear (:func:`in_solve_context`) the solver
    lives in the fresh context of that solve and is returned wrapped in an
    :class:`IsolatedSolver`.  Otherwise it is the plain Z3 solver, created
    with exactly the calls used before isolation existed.

    :param profile: ``default``, ``logic`` or ``tactic``. Explanation callers
        deliberately pass ``default``: their assumption cores and proof
        checks must remain independent of the main solver's tactics.
    :type profile: str
    :param expressions: Every expression that any staged check may assert,
        including the response suffix. Used only for logic classification.
    :type expressions: Sequence[z3.ExprRef]
    :return: Empty solver and selected logic, or ``None`` for default/tactic
        and for an unrecognized fragment that falls back to default.
    :rtype: Tuple[Union[z3.Solver, IsolatedSolver], Optional[str]]
    :raises BmcBuildError: If the requested profile is unsupported.
    """
    if isinstance(profile, bool) or profile not in SOLVER_PROFILES:
        raise BmcBuildError("solver_profile must be one of default, logic, or tactic.")
    owner = isolated_owner()
    if owner is not None and expressions:
        declared = owner.linear[-1][1]
        if not frozenset(term.get_id() for term in expressions) <= declared:
            # Formulas the declaration did not cover: classify them as well,
            # and solve where they were built unless they are linear too.
            if not declare(owner, tuple(expressions))[0]:
                owner = None
    context = owner.context if owner is not None else None
    if profile == "default":
        if owner is None:
            return z3.Solver(), None
        return IsolatedSolver(z3.Solver(ctx=context), owner), None
    if profile == "tactic":
        if owner is None:
            return z3.Then(
                "simplify", "propagate-values", "solve-eqs", "smt"
            ).solver(), None
        return IsolatedSolver(
            z3.Then(
                "simplify", "propagate-values", "solve-eqs", "smt", ctx=context
            ).solver(),
            owner,
        ), None
    goal = z3.Goal()
    # Goal.add(False) erases other assertions. Guard each root for this
    # syntactic probe so an impossible objective cannot hide nonlinear terms
    # needed later when the solver pops back to a feasible scenario.
    guard = z3.Bool("solver_profile_probe")
    for expression in expressions:
        goal.add(z3.Implies(guard, expression))
    selected = None
    for logic, probe_name in _LOGIC_PROBES:
        if z3.Probe(probe_name)(goal) > 0.5:
            selected = logic
            break
    if owner is None:
        if selected is None:
            return z3.Solver(), None
        return z3.SolverFor(selected), selected
    if selected is None:
        return IsolatedSolver(z3.Solver(ctx=context), owner), None
    return IsolatedSolver(z3.SolverFor(selected, ctx=context), owner), selected


class _SolveBudget:
    """Monotonic total budget shared by a sequence of Z3 checks.

    :param timeout_ms: Positive total budget in milliseconds, or ``None`` to
        leave Z3's timeout unset and allow unbounded execution.
    :type timeout_ms: Optional[int]
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``timeout_ms`` is neither
        ``None`` nor a positive integer.  ``bool`` is rejected even though it
        is an ``int`` subclass.

    Example::

        >>> print(_SolveBudget(None).remaining_ms())
        None
    """

    def __init__(self, timeout_ms: Optional[int]) -> None:
        if timeout_ms is not None and (
            isinstance(timeout_ms, bool)
            or not isinstance(timeout_ms, int)
            or timeout_ms <= 0
        ):
            raise BmcBuildError("timeout_ms must be a positive integer or None.")
        self.timeout_ms = timeout_ms
        self.deadline = (
            None if timeout_ms is None else time.monotonic() + timeout_ms / 1000.0
        )

    def remaining_ms(self) -> Optional[int]:
        """Return remaining whole milliseconds, or ``None`` when unavailable.

        ``None`` covers two different situations that callers must not merge:
        an unbounded budget, where ``deadline`` is ``None``, and an exhausted
        finite budget.  :func:`_check_with_budget` separates them by also
        testing ``deadline``; a caller that only inspects this return value
        cannot tell "no limit" from "no time left".

        A partial millisecond is rounded up rather than truncated, so a finite
        budget spends its last fraction of a millisecond on a real check
        instead of reporting exhaustion.  This differs from the truncating
        predecessor this budget was extracted from, and is the one intentional
        behavior change in that extraction.

        :return: Remaining whole milliseconds, never above the configured total
            budget; ``None`` for an unbounded or already exhausted budget.
        :rtype: Optional[int]

        Example::

            >>> print(_SolveBudget(None).remaining_ms())
            None
        """
        if self.deadline is None:
            return None
        remaining_seconds = self.deadline - time.monotonic()
        if remaining_seconds <= 0:
            return None
        remaining_ms = max(1, int(math.ceil(remaining_seconds * 1000.0)))
        # Rounding up can land one millisecond above the requested total budget:
        # ``deadline`` is ``t0 + timeout_ms / 1000.0``, and that float addition
        # can round upward, so ``deadline - t0`` may exceed ``timeout_ms / 1000``
        # (with ``t0 = 1e7`` and ``timeout_ms = 1`` the ceiling above yields 2).
        # Clamping keeps a finite budget an honest upper bound for Z3.
        return min(cast(int, self.timeout_ms), remaining_ms)


def _check_solver(
    solver: z3.Solver, assumptions: Sequence[z3.BoolRef], budgeted: bool
) -> Optional[z3.CheckSatResult]:
    """Run one solver check and report a budget cancellation as ``None``.

    When a timeout fires inside some Z3 engines (observed in the non-linear
    arithmetic engine), ``check`` raises ``Z3Exception('canceled')`` instead of
    returning ``unknown``.  A budgeted check treats exactly that exception as an
    undecided result; every other Z3 error, and a cancellation while no timeout
    is set, still propagates.

    :param solver: Solver to check.
    :type solver: z3.Solver
    :param assumptions: Assumption literals handed to ``check``.
    :type assumptions: Sequence[z3.BoolRef]
    :param budgeted: Whether a solver timeout was set for this check.
    :type budgeted: bool
    :return: The Z3 result, or ``None`` when the budget cancelled the check.
    :rtype: Optional[z3.CheckSatResult]
    :raises z3.Z3Exception: For any Z3 error other than a budget cancellation.

    Example::

        >>> import z3
        >>> _check_solver(z3.Solver(), (), True)
        sat
    """
    try:
        return solver.check(*assumptions)
    except z3.Z3Exception as err:
        # Z3Exception: raised by ``check`` when the timeout cancels the search
        # inside an engine that signals it by exception; only the message
        # ``canceled`` under a set timeout is a budget cut, anything else is a
        # real Z3 error.
        message = err.value
        if isinstance(message, bytes):
            message = message.decode("utf-8", "replace")
        if budgeted and message == "canceled":
            return None
        raise


def _check_with_budget(
    solver: z3.Solver, budget: _SolveBudget
) -> Tuple[
    BmcSolveStatus,
    Optional[z3.ModelRef],
    Optional[str],
    float,
    bool,
]:
    """Check one solver while preserving the shared-budget contract.

    :param solver: Z3 solver to check.
    :type solver: z3.Solver
    :param budget: Shared monotonic solve budget.
    :type budget: _SolveBudget
    :return: ``(status, model, reason, elapsed_ms, check_started)``.  Status is
        ``sat``, ``unsat``, ``unknown``, or ``timeout``; a pre-check deadline
        exhaustion returns ``check_started=False``.
    :rtype: Tuple[BmcSolveStatus, Optional[z3.ModelRef], Optional[str], float, bool]

    Example::

        >>> import z3
        >>> _check_with_budget(z3.Solver(), _SolveBudget(None))[0]
        'sat'
    """
    remaining = budget.remaining_ms()
    # ``timeout_ms=None`` leaves ``deadline`` and ``remaining`` unset, so this
    # path intentionally calls Z3 without setting a solver timeout.
    if budget.deadline is not None and remaining is None:
        return "timeout", None, "deadline_exhausted_before_check", 0.0, False
    if remaining is not None:
        solver.set(timeout=remaining)
    start = time.monotonic()
    status = _check_solver(solver, (), remaining is not None)
    elapsed_ms = (time.monotonic() - start) * 1000.0
    if status is None:
        return "unknown", None, "canceled", elapsed_ms, True
    if status == z3.sat:
        return "sat", solver.model(), None, elapsed_ms, True
    if status == z3.unsat:
        return "unsat", None, None, elapsed_ms, True
    reason = solver.reason_unknown() or "unknown"
    if reason == "timeout":
        return "timeout", None, reason, elapsed_ms, True
    return "unknown", None, reason, elapsed_ms, True


def _free_symbols(expression: z3.ExprRef) -> List[z3.ExprRef]:
    """Return the uninterpreted constants of an expression in first-seen order.

    This is :func:`z3.z3util.get_vars` with each shared subterm visited once.
    Case conditions read the acceptance of earlier candidates, so they are
    shared DAGs whose tree unfolding grows exponentially with nesting depth;
    ``get_vars`` walks that unfolding.

    :param expression: Expression to scan.
    :type expression: z3.ExprRef
    :return: Distinct constants in the preorder ``get_vars`` reports them.
    :rtype: List[z3.ExprRef]

    Example::

        >>> import z3
        >>> x, a = z3.Int("x"), z3.Bool("a")
        >>> shared = z3.Or(a, x > 1)
        >>> _free_symbols(z3.And(shared, z3.Not(shared), x == 2))
        [a, x]
    """
    found: List[z3.ExprRef] = []
    seen = set()
    pending = [expression]
    while pending:
        term = pending.pop()
        if term.get_id() in seen:
            continue
        seen.add(term.get_id())
        if z3.is_const(term):
            if term.decl().kind() == z3.Z3_OP_UNINTERPRETED:
                found.append(term)
        else:
            pending.extend(reversed(term.children()))
    return found


__all__ = []

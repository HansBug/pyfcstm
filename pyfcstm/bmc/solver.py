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
import threading
import time
import weakref
from typing import (
    Any,
    Callable,
    Dict,
    FrozenSet,
    List,
    Optional,
    Sequence,
    Tuple,
    TypeVar,
    Union,
    cast,
)

import z3

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


# Linear integer, real and mixed arithmetic, in the form formulas have before
# any simplification: subtraction, negation, ``abs``, integer/real conversion
# and division or modulo by a numeral included.  Z3 decides every query of
# this fragment, so the numbering of terms changes only the search path and,
# with it, which model is returned.  The ``is-qf*`` probes used for logic
# selection are stricter: they expect a simplified goal and reject ``x - y``.
_LINEAR_PROBE = "is-lira"

_F = TypeVar("_F", bound=Callable[..., Any])


class _SolveContextOwner:
    """State of one solve: its fresh context and where its solvers run.

    :ivar context: Fresh context, created when first needed.
    :vartype context: Optional[z3.Context]
    :ivar linear: Declarations of the wrapped functions currently running on
        this solve, outermost first.  Each one pairs the decision, ``True``
        for "solve in the fresh context", ``False`` for "solve where the
        formula was built" and ``None`` for "not decided yet, solve where
        the formula was built until it is", with the identities of the
        declared formulas.
    :vartype linear: List[Tuple[Optional[bool], FrozenSet[int]]]
    :ivar sliced: Formulas of a sliced core waiting for the unsliced one.
    :vartype sliced: Tuple[z3.ExprRef, ...]
    :ivar translated: Declared formulas already translated into the fresh
        context, by identity; the original is kept so the identity stays
        taken for as long as the entry exists.
    :vartype translated: Dict[int, Tuple[z3.ExprRef, z3.ExprRef]]
    :ivar used: Whether any solver of this solve was created in the fresh
        context.
    :vartype used: bool
    """

    __slots__ = ("context", "linear", "sliced", "translated", "used", "__weakref__")

    def __init__(self) -> None:
        self.context: Optional[z3.Context] = None
        self.linear: List[Tuple[Optional[bool], FrozenSet[int]]] = []
        self.sliced: Tuple[z3.ExprRef, ...] = ()
        self.translated: Dict[int, Tuple[z3.ExprRef, z3.ExprRef]] = {}
        self.used = False


class _SolveContextSlot(threading.local):
    """Per-thread weak reference to the owner of the solve in progress.

    :ivar owner: Weak reference to the owner created by the outermost
        function wrapped with :func:`_in_solve_context` on this thread.
    :vartype owner: Optional[weakref.ReferenceType]
    """

    def __init__(self) -> None:
        self.owner: Optional["weakref.ReferenceType[_SolveContextOwner]"] = None


_SLOT = _SolveContextSlot()


def _current_owner() -> Optional[_SolveContextOwner]:
    """Return the owner of the solve in progress on this thread.

    :return: Owner, or ``None`` outside every wrapped function.
    :rtype: Optional[_SolveContextOwner]
    """
    reference = _SLOT.owner
    return reference() if reference is not None else None


def _solver_context_in_use() -> str:
    """Tell where the solvers of the solve in progress ran.

    :return: ``"fresh"`` when at least one solver was created in the fresh
        context of this solve, otherwise ``"shared"``.
    :rtype: str

    Example::

        >>> _solver_context_in_use()
        'shared'
    """
    owner = _current_owner()
    return "fresh" if owner is not None and owner.used else "shared"


def _isolated_owner() -> Optional[_SolveContextOwner]:
    """Return the solve whose fresh context solvers should be created in.

    :return: Owner of the solve in progress when its innermost declaration is
        linear, otherwise ``None``.
    :rtype: Optional[_SolveContextOwner]

    Example::

        >>> print(_isolated_owner())
        None
    """
    owner = _current_owner()
    if owner is None or not owner.linear or not owner.linear[-1][0]:
        return None
    return owner


_CARDINALITY_KINDS = frozenset(
    (
        z3.Z3_OP_PB_AT_MOST,
        z3.Z3_OP_PB_AT_LEAST,
        z3.Z3_OP_PB_LE,
        z3.Z3_OP_PB_GE,
        z3.Z3_OP_PB_EQ,
    )
)


def _without_cardinality(term: z3.ExprRef) -> List[z3.ExprRef]:
    """Split a conjunction and replace cardinality atoms by their arguments.

    An event cardinality assumption is a pseudo-Boolean atom over Boolean
    terms.  Z3 decides such atoms together with linear arithmetic, but the
    linear-arithmetic probe rejects them, so they are taken out before the
    probe runs and their arguments are probed in their place.

    :param term: Boolean term.
    :type term: z3.ExprRef
    :return: Conjuncts of ``term`` with each cardinality atom replaced by its
        arguments.
    :rtype: List[z3.ExprRef]
    """
    found: List[z3.ExprRef] = []
    pending = [term]
    while pending:
        item = pending.pop()
        if z3.is_and(item):
            pending.extend(item.children())
        elif z3.is_app(item) and item.decl().kind() in _CARDINALITY_KINDS:
            found.extend(item.children())
        else:
            found.append(item)
    return found


def _is_linear(terms: Sequence[z3.ExprRef], context: z3.Context) -> bool:
    """Tell whether Z3 decides every query over the given terms.

    The answer is yes for linear integer, real and mixed arithmetic, also
    when an event cardinality assumption stands next to it and when a factor
    is a constant expression such as ``0 - 2`` that only Z3's simplifier
    turns into a numeral.  The probe runs in ``context``, which must be the
    context of ``terms`` and not the one the formula was built in, so that
    asking the question creates nothing there.

    :param terms: Boolean terms of ``context``.
    :type terms: Sequence[z3.ExprRef]
    :param context: Context the terms live in.
    :type context: z3.Context
    :return: ``True`` when the terms stay inside the fragment.
    :rtype: bool

    Example::

        >>> import z3
        >>> context = z3.Context()
        >>> x, y = z3.Ints("x y", context)
        >>> _is_linear([x - 2 * y > 3, x % 3 == 1], context)
        True
        >>> _is_linear([x * (y - y + 2) > 3], context)
        True
        >>> _is_linear([x * y > 3], context), _is_linear([x % y == 1], context)
        (False, False)
    """
    probe = z3.Probe(_LINEAR_PROBE, context)
    goal = z3.Goal(ctx=context)
    # Goal.add(False) erases other assertions; guard each root as the logic
    # classification of :func:`_solver_for_profile` does.
    guard = z3.Bool("solver_fragment_probe", context)
    for term in terms:
        goal.add(z3.Implies(guard, term))
    if probe(goal) > 0.5:
        return True
    # Second look, for the two shapes the probe rejects although Z3 decides
    # them: cardinality atoms, and factors that are constant expressions.
    relaxed = z3.Goal(ctx=context)
    for term in terms:
        for part in _without_cardinality(term):
            relaxed.add(z3.Implies(guard, part))
    return probe(z3.Tactic("simplify", context)(relaxed)[0]) > 0.5


class _Sliced(tuple):
    """Formulas of a core that cone slicing shortened.

    Such a solve also solves over the unsliced core: the runtime-safety check
    always, the property itself when a sliced witness fails to replay.  The
    declaration therefore waits until :func:`_resolving_unsliced` has seen
    that core.
    """

    __slots__ = ()


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
        owner = _current_owner()
        if (
            full is not core
            and owner is not None
            and owner.linear
            and owner.linear[-1][0] is None
        ):
            terms = tuple(owner.sliced) + _core_parts(full)
            del owner.linear[-1]
            owner.sliced = ()
            owner.linear.append(_declare(owner, terms))
        return full

    return cast(_F, wrapper)


def _declare(
    owner: _SolveContextOwner, terms: Sequence[z3.ExprRef]
) -> Tuple[bool, FrozenSet[int]]:
    """Decide where the solvers of a call asserting ``terms`` run.

    Formulas are translated into the fresh context of the solve, created on
    first use, and classified there, so asking creates nothing in the context
    the formulas were built in.

    :param owner: Solve the call belongs to.
    :type owner: _SolveContextOwner
    :param terms: Formulas the call may assert.
    :type terms: Sequence[z3.ExprRef]
    :return: Decision and the identities of the formulas.
    :rtype: Tuple[bool, FrozenSet[int]]
    """
    identities = frozenset(term.get_id() for term in terms)
    if owner.context is None:
        owner.context = z3.Context()
    translated = []
    for term in terms:
        known = owner.translated.get(term.get_id())
        if known is None:
            known = owner.translated[term.get_id()] = (
                term,
                term.translate(owner.context),
            )
        translated.append(known[1])
    linear = _is_linear(translated, owner.context)
    del translated
    if not linear and not any(entry[0] for entry in owner.linear):
        # Nothing of this solve will run in the fresh context: give it back.
        owner.translated.clear()
        owner.context = None
    return linear, identities


def _core_fragment(
    core: Any = None, *args: Any, **kwargs: Any
) -> Union[bool, Tuple[z3.BoolRef, ...]]:
    """Return the formulas a solve over a core formula may assert.

    A core that cone slicing actually shortened is answered with a
    :class:`_Sliced` tuple: such a solve also reaches the unsliced formula,
    which is not known here.

    :param core: First argument of the wrapped function, expected to be a
        :class:`pyfcstm.bmc.relation.BmcCoreFormula`.
    :type core: Any
    :return: Domain, transition, initial and environment formulas, as a
        :class:`_Sliced` tuple for a sliced core; ``False`` when the caller
        asked for ``solver_context="shared"``; ``()`` when the argument is
        something else and the function will reject it.
    :rtype: Union[bool, Tuple[z3.BoolRef, ...]]
    """
    if kwargs.get("solver_context") == "shared":
        return False
    parts = _core_parts(core)
    if parts and getattr(getattr(core, "cone_slice", None), "dropped_variables", None):
        return _Sliced(parts)
    return parts


def _property_fragment(
    formula: Any = None, *args: Any, **kwargs: Any
) -> Union[bool, Tuple[z3.BoolRef, ...]]:
    """Return the formulas a solve of a property formula may assert.

    :param formula: First argument of the wrapped function, expected to be a
        :class:`pyfcstm.bmc.properties.BmcPropertyFormula`.
    :type formula: Any
    :return: Core formulas, objective and response suffix, as a
        :class:`_Sliced` tuple when the core was sliced; ``False`` when the
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
    if isinstance(core, _Sliced):
        return _Sliced(tuple(core) + cast(Tuple[z3.BoolRef, ...], rest))
    return cast(Tuple[z3.BoolRef, ...], core) + cast(Tuple[z3.BoolRef, ...], rest)


def _in_solve_context(
    fragment: Optional[Callable[..., Union[bool, Sequence[z3.ExprRef]]]] = None,
    own: bool = True,
) -> Callable[[_F], _F]:
    """Make a solving function choose once where its solvers run.

    Z3 numbers every term inside a context, hands the numbers of released terms
    out again, and orders its search by those numbers.  A solver created in the
    context where a formula was built therefore explores, and returns models,
    according to everything that context has held before: the same formula can
    take a different path, and yield a different witness, after an unrelated
    change to how it was constructed or to what the process solved earlier.

    For quantifier-free linear arithmetic Z3 decides every query, so the path
    changes only which model is returned.  When ``fragment`` says the call
    stays in that fragment, the solvers the call creates through
    :func:`_solver_for_profile` share one fresh context, in which the
    numbering follows the asserted formulas and the order of the calls alone.
    A Z3 context costs megabytes and milliseconds to create, which is why
    the solvers of one solve share it instead of owning one each.

    Outside that fragment Z3 may answer ``unknown``, and whether it does also
    depends on the numbering, so no renumbering keeps the verdicts it reaches
    today.  Such a call, and everything it calls, solves where the formula
    was built, exactly as a call made without this wrapper.

    A wrapped function called from another one joins the solve in progress.
    With ``own=False`` it also adopts the declaration in force; a function
    that solves over different formulas makes its own, and a declaration can
    never turn linear again inside a non-linear one.

    The slot holds only a weak reference to an owner that lives in the
    wrapper's frame, so the solve ends with that frame even if an interrupt
    skips the explicit reset.

    :param fragment: Given the arguments of the call, returns the formulas it
        may assert, ``False`` to solve where the formula was built without
        asking, or ``()`` to make no declaration; defaults to ``None`` for
        "never declares".
    :type fragment: Callable[..., Union[bool, Sequence[z3.ExprRef]]], optional
    :param own: Whether to declare even when a declaration is in force,
        defaults to ``True``.
    :type own: bool, optional
    :return: Decorator keeping the signature and documentation of the function.
    :rtype: Callable[[Callable[..., Any]], Callable[..., Any]]

    Example::

        >>> import z3
        >>> x, y = z3.Ints("x y")
        >>> @_in_solve_context(lambda *terms: terms)
        ... def isolated(*terms):
        ...     return _isolated_owner() is not None
        >>> isolated(x + y > 1), isolated(x * y > 1)
        (True, False)
    """

    def decorate(function: _F) -> _F:
        @functools.wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            owner = _current_owner()
            created = None
            if owner is None:
                # The slot holds a weak reference, so an interrupt between
                # these two lines cannot leave a solve behind: the owner dies
                # with this frame and the reference goes dead with it.
                created = owner = _SolveContextOwner()
                _SLOT.owner = weakref.ref(owner)
            depth = len(owner.linear)
            try:
                if fragment is not None and (own or not owner.linear):
                    terms = fragment(*args, **kwargs)
                    if terms is False:
                        owner.linear.append((False, frozenset()))
                    elif isinstance(terms, _Sliced):
                        owner.sliced = tuple(terms)
                        owner.linear.append((None, frozenset()))
                    elif terms:
                        owner.linear.append(_declare(owner, terms))
                return function(*args, **kwargs)
            finally:
                del owner.linear[depth:]
                if created is not None:
                    _SLOT.owner = None

        return cast(_F, wrapper)

    return decorate


class _IsolatedSolver:
    """Z3 solver of another context, used with terms of the caller's context.

    Assertions and assumptions are translated into the solver's context,
    models and unsat cores are translated back, so callers keep working with
    the terms they built.

    :param solver: Solver living in the fresh context of a solve.
    :type solver: z3.Solver
    :param owner: Solve the solver belongs to; it holds the fresh context and
        the formulas already translated into it.
    :type owner: _SolveContextOwner

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> owner = _SolveContextOwner()
        >>> owner.context = z3.Context()
        >>> solver = _IsolatedSolver(z3.Solver(ctx=owner.context), owner)
        >>> solver.add(x > 2, x < 4)
        >>> solver.check(), solver.model().eval(x)
        (sat, 3)
    """

    __slots__ = ("_context", "_home", "_solver", "_translated")

    def __init__(self, solver: z3.Solver, owner: _SolveContextOwner) -> None:
        owner.used = True
        self._solver = solver
        self._context = cast(z3.Context, owner.context)
        self._translated = owner.translated
        self._home = z3.main_ctx()

    def _inward(self, term: z3.ExprRef) -> z3.ExprRef:
        """Translate one caller-side term into the solver's context.

        :param term: Z3 term of the caller's context.
        :type term: z3.ExprRef
        :return: The same term in the solver's context.
        :rtype: z3.ExprRef
        """
        self._home = term.ctx
        known = self._translated.get(term.get_id())
        if known is not None and known[0].eq(term):
            return known[1]
        return term.translate(self._context)

    def add(self, *expressions: z3.BoolRef) -> None:
        """Assert expressions of the caller's context.

        :param expressions: Boolean terms.
        :type expressions: z3.BoolRef
        :return: ``None``.
        :rtype: None
        """
        self._solver.add(*[self._inward(item) for item in expressions])

    def push(self) -> None:
        """Open a backtracking scope.

        :return: ``None``.
        :rtype: None
        """
        self._solver.push()

    def pop(self) -> None:
        """Close the innermost backtracking scope.

        :return: ``None``.
        :rtype: None
        """
        self._solver.pop()

    def set(self, *args: Any, **keys: Any) -> None:
        """Set solver parameters, as :meth:`z3.Solver.set` does.

        :return: ``None``.
        :rtype: None
        """
        self._solver.set(*args, **keys)

    def check(self, *assumptions: z3.BoolRef) -> z3.CheckSatResult:
        """Check satisfiability under assumptions of the caller's context.

        :param assumptions: Boolean literals.
        :type assumptions: z3.BoolRef
        :return: ``z3.sat``, ``z3.unsat`` or ``z3.unknown``.
        :rtype: z3.CheckSatResult
        """
        return self._solver.check(*[self._inward(item) for item in assumptions])

    def model(self) -> z3.ModelRef:
        """Return the model of the last check in the caller's context.

        :return: Model whose values evaluate terms of the caller's context.
        :rtype: z3.ModelRef
        """
        return self._solver.model().translate(self._home)

    def unsat_core(self) -> List[z3.BoolRef]:
        """Return the unsat core of the last check in the caller's context.

        :return: Assumption literals in the order Z3 reported them.
        :rtype: List[z3.BoolRef]
        """
        return [literal.translate(self._home) for literal in self._solver.unsat_core()]

    def reason_unknown(self) -> str:
        """Return Z3's reason for the last ``unknown`` result.

        :return: Reason text.
        :rtype: str
        """
        return self._solver.reason_unknown()

    def statistics(self) -> z3.Statistics:
        """Return the statistics of the underlying solver.

        :return: Z3 statistics object.
        :rtype: z3.Statistics
        """
        return self._solver.statistics()


def _solver_for_profile(
    profile: str, expressions: Sequence[z3.ExprRef] = ()
) -> Tuple[Union[z3.Solver, "_IsolatedSolver"], Optional[str]]:
    """Build a solver without asserting or rewriting the supplied expressions.

    During a solve declared linear (:func:`_in_solve_context`) the solver
    lives in the fresh context of that solve and is returned wrapped in an
    :class:`_IsolatedSolver`.  Otherwise it is the plain Z3 solver, created
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
    :rtype: Tuple[Union[z3.Solver, _IsolatedSolver], Optional[str]]
    :raises BmcBuildError: If the requested profile is unsupported.
    """
    if isinstance(profile, bool) or profile not in SOLVER_PROFILES:
        raise BmcBuildError("solver_profile must be one of default, logic, or tactic.")
    owner = _isolated_owner()
    if owner is not None and expressions:
        declared = owner.linear[-1][1]
        if not frozenset(term.get_id() for term in expressions) <= declared:
            # Formulas the declaration did not cover: classify them as well,
            # and solve where they were built unless they are linear too.
            if not _declare(owner, tuple(expressions))[0]:
                owner = None
    context = owner.context if owner is not None else None
    if profile == "default":
        if owner is None:
            return z3.Solver(), None
        return _IsolatedSolver(z3.Solver(ctx=context), owner), None
    if profile == "tactic":
        if owner is None:
            return z3.Then(
                "simplify", "propagate-values", "solve-eqs", "smt"
            ).solver(), None
        return _IsolatedSolver(
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
        return _IsolatedSolver(z3.Solver(ctx=context), owner), None
    return _IsolatedSolver(z3.SolverFor(selected, ctx=context), owner), selected


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

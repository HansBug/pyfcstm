"""
Solving in a Z3 context of its own, so the answer follows from the formula alone.

Z3 numbers every term inside a context, hands the numbers of released terms out
again, and orders its search by those numbers.  A solver created in the context
where a formula was built therefore explores, and returns models, according to
everything that context has held before.  This module lets a solving function
declare the formulas it may assert, decides once whether they stay inside the
fragment Z3 decides, and, when they do, creates every solver of the call in one
fresh context.  Terms are translated in, models and unsat cores are translated
back, so callers keep working with the terms they built.

The module contains:

* :func:`in_solve_context` - Decorator that makes a function choose where its
  solvers run
* :class:`IsolatedSolver` - Solver of another context driven with the caller's terms
* :class:`SolveContextOwner` - State of the solve in progress on a thread
* :class:`Deferred` - Marker for a declaration that waits for more formulas
* :func:`declare` - Decide where the solvers of a call asserting some terms run
* :func:`is_linear` - Tell whether Z3 decides every query over some terms
* :func:`current_owner`, :func:`isolated_owner`, :func:`solver_context_in_use` -
  Read the state of the solve in progress

.. note::
   Outside linear arithmetic Z3 may answer ``unknown``, and whether it does
   depends on the numbering, so no renumbering keeps the verdicts it reaches
   today.  Such a call keeps solving where its formulas were built.

Example::

    >>> import z3
    >>> x, y = z3.Ints("x y")
    >>> @in_solve_context(lambda *terms: terms)
    ... def isolated(*terms):
    ...     return isolated_owner() is not None
    >>> isolated(x + y > 1), isolated(x * y > 1)
    (True, False)
"""

from __future__ import annotations

import functools
import threading
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

__all__ = [
    "Deferred",
    "IsolatedSolver",
    "LINEAR_PROBE",
    "SolveContextOwner",
    "current_owner",
    "declare",
    "in_solve_context",
    "is_linear",
    "isolated_owner",
    "solver_context_in_use",
]



# Linear integer, real and mixed arithmetic, in the form formulas have before
# any simplification: subtraction, negation, ``abs``, integer/real conversion
# and division or modulo by a numeral included.  Z3 decides every query of
# this fragment, so the numbering of terms changes only the search path and,
# with it, which model is returned.  The ``is-qf*`` probes used for logic
# selection are stricter: they expect a simplified goal and reject ``x - y``.
LINEAR_PROBE = "is-lira"

_F = TypeVar("_F", bound=Callable[..., Any])


class SolveContextOwner:
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
    :ivar deferred: Formulas of a declaration that waits for more formulas
        (see :class:`Deferred`).
    :vartype deferred: Tuple[z3.ExprRef, ...]
    :ivar translated: Declared formulas already translated into the fresh
        context, by identity; the original is kept so the identity stays
        taken for as long as the entry exists.
    :vartype translated: Dict[int, Tuple[z3.ExprRef, z3.ExprRef]]
    :ivar used: Whether any solver of this solve was created in the fresh
        context.
    :vartype used: bool
    """

    __slots__ = ("context", "linear", "deferred", "translated", "used", "__weakref__")

    def __init__(self) -> None:
        self.context: Optional[z3.Context] = None
        self.linear: List[Tuple[Optional[bool], FrozenSet[int]]] = []
        self.deferred: Tuple[z3.ExprRef, ...] = ()
        self.translated: Dict[int, Tuple[z3.ExprRef, z3.ExprRef]] = {}
        self.used = False


class _SolveContextSlot(threading.local):
    """Per-thread weak reference to the owner of the solve in progress.

    :ivar owner: Weak reference to the owner created by the outermost
        function wrapped with :func:`in_solve_context` on this thread.
    :vartype owner: Optional[weakref.ReferenceType]
    """

    def __init__(self) -> None:
        self.owner: Optional["weakref.ReferenceType[SolveContextOwner]"] = None


_SLOT = _SolveContextSlot()


def current_owner() -> Optional[SolveContextOwner]:
    """Return the owner of the solve in progress on this thread.

    :return: Owner, or ``None`` outside every wrapped function.
    :rtype: Optional[SolveContextOwner]
    """
    reference = _SLOT.owner
    return reference() if reference is not None else None


def solver_context_in_use() -> str:
    """Tell where the solvers of the solve in progress ran.

    :return: ``"fresh"`` when at least one solver was created in the fresh
        context of this solve, otherwise ``"shared"``.
    :rtype: str

    Example::

        >>> solver_context_in_use()
        'shared'
    """
    owner = current_owner()
    return "fresh" if owner is not None and owner.used else "shared"


def isolated_owner() -> Optional[SolveContextOwner]:
    """Return the solve whose fresh context solvers should be created in.

    :return: Owner of the solve in progress when its innermost declaration is
        linear, otherwise ``None``.
    :rtype: Optional[SolveContextOwner]

    Example::

        >>> print(isolated_owner())
        None
    """
    owner = current_owner()
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


def is_linear(terms: Sequence[z3.ExprRef], context: z3.Context) -> bool:
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
        >>> is_linear([x - 2 * y > 3, x % 3 == 1], context)
        True
        >>> is_linear([x * (y - y + 2) > 3], context)
        True
        >>> is_linear([x * y > 3], context), is_linear([x % y == 1], context)
        (False, False)
    """
    probe = z3.Probe(LINEAR_PROBE, context)
    goal = z3.Goal(ctx=context)
    # Goal.add(False) erases other assertions; guard each root as the logic
    # classification of the BMC solver profiles does.
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


class Deferred(tuple):
    """Formulas of a call whose declaration must wait for more formulas.

    A function wrapped by :func:`in_solve_context` returns this from its
    ``fragment`` when the call may also solve over formulas that are not known
    yet.  The call then runs without a decision, in the context where its
    formulas were built, until the caller completes the declaration through
    :attr:`SolveContextOwner.deferred` and :func:`declare`.

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> Deferred((x > 1,)) == (x > 1,)
        True
        >>> isinstance(Deferred(), tuple)
        True
    """

    __slots__ = ()


def declare(
    owner: SolveContextOwner, terms: Sequence[z3.ExprRef]
) -> Tuple[bool, FrozenSet[int]]:
    """Decide where the solvers of a call asserting ``terms`` run.

    Formulas are translated into the fresh context of the solve, created on
    first use, and classified there, so asking creates nothing in the context
    the formulas were built in.

    :param owner: Solve the call belongs to.
    :type owner: SolveContextOwner
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
    linear = is_linear(translated, owner.context)
    del translated
    if not linear and not any(entry[0] for entry in owner.linear):
        # Nothing of this solve will run in the fresh context: give it back.
        owner.translated.clear()
        owner.context = None
    return linear, identities


def in_solve_context(
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
    :func:`isolated_owner` share one fresh context, in which the numbering
    follows the asserted formulas and the order of the calls alone.
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
        asking, a :class:`Deferred` tuple to decide later, or ``()`` to make no
        declaration; defaults to ``None`` for "never declares".
    :type fragment: Callable[..., Union[bool, Sequence[z3.ExprRef]]], optional
    :param own: Whether to declare even when a declaration is in force,
        defaults to ``True``.
    :type own: bool, optional
    :return: Decorator keeping the signature and documentation of the function.
    :rtype: Callable[[Callable[..., Any]], Callable[..., Any]]

    Example::

        >>> import z3
        >>> x, y = z3.Ints("x y")
        >>> @in_solve_context(lambda *terms: terms)
        ... def isolated(*terms):
        ...     return isolated_owner() is not None
        >>> isolated(x + y > 1), isolated(x * y > 1)
        (True, False)
    """

    def decorate(function: _F) -> _F:
        @functools.wraps(function)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            owner = current_owner()
            created = None
            if owner is None:
                # The slot holds a weak reference, so an interrupt between
                # these two lines cannot leave a solve behind: the owner dies
                # with this frame and the reference goes dead with it.
                created = owner = SolveContextOwner()
                _SLOT.owner = weakref.ref(owner)
            depth = len(owner.linear)
            try:
                if fragment is not None and (own or not owner.linear):
                    terms = fragment(*args, **kwargs)
                    if terms is False:
                        owner.linear.append((False, frozenset()))
                    elif isinstance(terms, Deferred):
                        owner.deferred = tuple(terms)
                        owner.linear.append((None, frozenset()))
                    elif terms:
                        owner.linear.append(declare(owner, terms))
                return function(*args, **kwargs)
            finally:
                del owner.linear[depth:]
                if created is not None:
                    _SLOT.owner = None

        return cast(_F, wrapper)

    return decorate


class IsolatedSolver:
    """Z3 solver of another context, used with terms of the caller's context.

    Assertions and assumptions are translated into the solver's context,
    models and unsat cores are translated back, so callers keep working with
    the terms they built.

    :param solver: Solver living in the fresh context of a solve.
    :type solver: z3.Solver
    :param owner: Solve the solver belongs to; it holds the fresh context and
        the formulas already translated into it.
    :type owner: SolveContextOwner

    Example::

        >>> import z3
        >>> x = z3.Int("x")
        >>> owner = SolveContextOwner()
        >>> owner.context = z3.Context()
        >>> solver = IsolatedSolver(z3.Solver(ctx=owner.context), owner)
        >>> solver.add(x > 2, x < 4)
        >>> solver.check(), solver.model().eval(x)
        (sat, 3)
    """

    __slots__ = ("_context", "_home", "_solver", "_translated")

    def __init__(self, solver: z3.Solver, owner: SolveContextOwner) -> None:
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

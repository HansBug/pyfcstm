"""
Runtime-safety obligation of a bounded model check.

A query about business behaviour says nothing about whether the model itself
can fail at runtime: a reachable division by zero, math domain error or
rejected writeback stops the simulator no matter what the query asks.  Before
evaluating the business property, the checker therefore asks whether any
runtime error is reachable within the bound.  A reachable error is the third
kind of verification result, *runtime error*: the business property is not
evaluated, because no execution reaching the error can continue.

The error formula is built from the runtime-error sites of the relation.
Each site carries the condition under which the operation is actually
evaluated and raises its error.  An error at step ``k`` needs a valid prefix
``D_N ∧ I_0 ∧ T_0 ∧ … ∧ T_{k-1}`` and the environment assumptions about frames
and steps up to ``k``; nothing is assumed about the frames after the error,
which the runtime never produces.  Initializer errors need only the domain
and the assumptions about frame 0.

The module contains:

* :class:`BmcRuntimeSafetyResult` - Outcome of the runtime-safety check.
* :func:`runtime_error_formula` - Build the runtime-error reachability formula.
* :func:`check_runtime_safety` - Run the check for a core formula.

Example::

    >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
    >>> from pyfcstm.bmc.safety import check_runtime_safety
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text(
    ...     'input int d; def float x = 0.0;'
    ...     'state Root { [*] -> A; state A { during { x = 10 / d; } } }'
    ... )
    >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check invariant <= 2: x >= 0;'))
    >>> result = check_runtime_safety(core)
    >>> result.status, result.error.kind, result.error.step
    ('violated', 'division_by_zero', 0)
"""

import math
from dataclasses import dataclass, field, replace
from typing import Any, Dict, List, Optional, Tuple

import z3

from .errors import BmcBuildError
from .relation import BmcCoreFormula, BmcRuntimeErrorSite
from .solver import _check_with_budget, _solver_for_profile, _SolveBudget

__all__ = [
    "BmcRuntimeSafetyResult",
    "runtime_error_formula",
    "check_runtime_safety",
]

#: Runtime-safety statuses.
RUNTIME_SAFETY_STATUSES = ("safe", "violated", "unknown", "timeout", "not_applicable")


@dataclass(frozen=True)
class BmcRuntimeSafetyResult:
    """
    Outcome of the runtime-safety check of one bounded query.

    :param status: ``"safe"`` when no runtime error is reachable within the
        bound, ``"violated"`` when one is, ``"unknown"`` or ``"timeout"`` when
        the solver could not decide, and ``"not_applicable"`` when the model
        has no operation that can raise a runtime error.
    :type status: str
    :param sites: Number of runtime-error sites checked.
    :type sites: int
    :param elapsed_ms: Solver time in milliseconds.
    :type elapsed_ms: float
    :param error: First site, in evaluation order, that the solver model
        reaches with its error raised; set only when ``status`` is
        ``"violated"``, defaults to ``None``.
    :type error: Optional[pyfcstm.bmc.relation.BmcRuntimeErrorSite]
    :param reason: Solver reason for ``"unknown"`` and ``"timeout"``,
        defaults to ``None``.
    :type reason: Optional[str]
    :param model: Solver model of the error prefix; set only when ``status``
        is ``"violated"``; not compared, defaults to ``None``.
    :type model: Optional[z3.ModelRef]
    :param core: Core formula the check ran on, used to decode ``model``;
        not compared, defaults to ``None``.
    :type core: Optional[pyfcstm.bmc.relation.BmcCoreFormula]
    :raises pyfcstm.bmc.errors.BmcBuildError: If the fields are inconsistent.

    Example::

        >>> from pyfcstm.bmc.safety import BmcRuntimeSafetyResult
        >>> BmcRuntimeSafetyResult("safe", 2, 1.5).to_canonical()
        {'elapsed_ms': 1.5, 'error': None, 'reason': None, 'sites': 2, 'status': 'safe'}
    """

    status: str
    sites: int
    elapsed_ms: float
    error: Optional[BmcRuntimeErrorSite] = None
    reason: Optional[str] = None
    model: Optional[z3.ModelRef] = field(default=None, repr=False, compare=False)
    core: Optional[BmcCoreFormula] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        if self.status not in RUNTIME_SAFETY_STATUSES:
            raise BmcBuildError("Unsupported runtime safety status: %r." % (self.status,))
        violated = self.status == "violated"
        if violated != (self.error is not None) or violated != (self.model is not None):
            raise BmcBuildError("Only a violated runtime safety check carries an error and a model.")
        if (self.status in ("unknown", "timeout")) != (self.reason is not None):
            raise BmcBuildError("Only an undecided runtime safety check carries a reason.")

    def to_canonical(self) -> Dict[str, Any]:
        """
        Return a JSON-stable dictionary.

        :return: Status, number of sites, elapsed time, reason and error site.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.safety import BmcRuntimeSafetyResult
            >>> BmcRuntimeSafetyResult("not_applicable", 0, 0.0).to_canonical()["status"]
            'not_applicable'
        """
        return {
            "elapsed_ms": self.elapsed_ms,
            "error": None if self.error is None else self.error.to_canonical(),
            "reason": self.reason,
            "sites": self.sites,
            "status": self.status,
        }


def _environment_up_to(core: BmcCoreFormula, last: int) -> Tuple[z3.BoolRef, ...]:
    # Assumption instances about frames and steps after the failing one
    # constrain states the runtime never reaches, so they are left out.
    selected: List[z3.BoolRef] = []
    for group in core._tracked_groups:
        if group.stage != "assumptions":
            continue
        frame = group.refs.get("frame", -1)
        step = group.refs.get("step", -1)
        if frame <= last and step <= last:
            selected.extend(group.expressions)
    return tuple(selected)


def _sites(core: BmcCoreFormula) -> Tuple[BmcRuntimeErrorSite, ...]:
    # Initializers run first, then the steps; each step lists its sites in
    # runtime evaluation order, so the first site a model satisfies is the
    # error the runtime raises.
    return tuple(core._initial_error_sites) + tuple(
        site for step in core.steps for site in step.runtime_error_sites
    )


def _holds(model: z3.ModelRef, condition: z3.BoolRef) -> bool:
    value = model.eval(condition, model_completion=True)
    if not (z3.is_true(value) or z3.is_false(value)):
        value = z3.simplify(z3.substitute(value, *_algebraic_floors(value)))
    return z3.is_true(value)


def _algebraic_floors(value: z3.ExprRef) -> List[Tuple[z3.ExprRef, z3.ExprRef]]:
    # ToInt of an irrational algebraic number, such as the square root of an
    # int writeback, is the one ground term Z3 neither simplifies nor
    # decides.  An irrational number is never an integer, so a close rational
    # approximation has the same floor.
    floors = []
    pending = [value]
    while pending:
        term = pending.pop()
        if z3.is_to_int(term) and z3.is_algebraic_value(term.arg(0)):
            floor = math.floor(term.arg(0).approx(20).as_fraction())
            floors.append((term, z3.IntVal(floor)))
        else:
            pending.extend(term.children())
    return floors


def runtime_error_formula(core: BmcCoreFormula) -> Tuple[z3.BoolRef, Tuple[BmcRuntimeErrorSite, ...]]:
    """
    Build the formula that holds exactly when a runtime error is reachable.

    :param core: Core formula of a prepared query.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :return: The reachability formula and the sites it covers, in evaluation
        order.  The formula is ``False`` when there are no sites.
    :rtype: Tuple[z3.BoolRef, Tuple[pyfcstm.bmc.relation.BmcRuntimeErrorSite, ...]]

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.bmc.safety import runtime_error_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> core = build_bmc_core_formula(BmcEngine(load_state_machine_from_text('state Root;'))
        ...     .prepare('check reach <= 1: terminated();'))
        >>> runtime_error_formula(core)
        (False, ())
    """
    sites = _sites(core)
    disjuncts: List[z3.BoolRef] = []
    initial = [site.condition for site in core._initial_error_sites]
    if initial:
        disjuncts.append(z3.And(core.domain_formula, *_environment_up_to(core, 0), z3.Or(*initial)))
    prefix: List[z3.BoolRef] = [core.domain_formula, core.initial_formula]
    for step in core.steps:
        step_sites = [site.condition for site in step.runtime_error_sites]
        if step_sites:
            disjuncts.append(
                z3.And(*prefix, *_environment_up_to(core, step.step_index), z3.Or(*step_sites))
            )
        prefix.append(step.formula)
    if not disjuncts:
        return z3.BoolVal(False), sites
    return (disjuncts[0] if len(disjuncts) == 1 else z3.Or(*disjuncts)), sites


def check_runtime_safety(
    core: BmcCoreFormula,
    *,
    timeout_ms: Optional[int] = None,
    solver_profile: str = "default",
) -> BmcRuntimeSafetyResult:
    """
    Check whether a runtime error is reachable within the bound.

    :param core: Core formula of a prepared query.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param timeout_ms: Positive solver timeout in milliseconds, defaults to
        ``None`` for no limit.
    :type timeout_ms: Optional[int], optional
    :param solver_profile: ``"default"``, ``"logic"`` or ``"tactic"``,
        defaults to ``"default"``.
    :type solver_profile: str, optional
    :return: The check result.
    :rtype: BmcRuntimeSafetyResult
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``core`` is not a core
        formula, or the timeout or profile is invalid.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.bmc.safety import check_runtime_safety
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text(
        ...     'input int d; def int x = 0;'
        ...     'state Root { [*] -> A; state A { during { x = 10 / d; } } }'
        ... )
        >>> context = BmcEngine(model).prepare(
        ...     'assume always: d == 2;\\ncheck invariant <= 2: x >= 0;'
        ... )
        >>> check_runtime_safety(build_bmc_core_formula(context)).status
        'safe'
    """
    if not isinstance(core, BmcCoreFormula):
        raise BmcBuildError("core must be BmcCoreFormula.")
    return _check_runtime_safety(core, timeout_ms, solver_profile)[0]


def _unsliced(core: BmcCoreFormula) -> BmcCoreFormula:
    # Cone slicing drops operations the query cannot observe, but any of them
    # can still raise, so the check runs on the core built without slicing.
    if core.cone_slice is None or not core.cone_slice.dropped_variables:
        return core
    from .pipeline import compile_bmc_query

    context = core.context
    return compile_bmc_query(
        context.model,
        context.source_text if context.source_text is not None else context.query,
        options=replace(context.options, cone_slicing=False),
        query_source_path=context.query_source_path,
    ).core


def _check_runtime_safety(
    core: BmcCoreFormula,
    timeout_ms: Optional[int],
    solver_profile: str,
) -> Tuple[BmcRuntimeSafetyResult, Optional[_SolveBudget]]:
    # The shared budget starts only when a solver check is about to run, so a
    # model without runtime-error sites spends none of it.
    core = _unsliced(core)
    formula, sites = runtime_error_formula(core)
    if not sites:
        return BmcRuntimeSafetyResult("not_applicable", 0, 0.0), None
    budget = _SolveBudget(timeout_ms)
    solver, _logic = _solver_for_profile(solver_profile, (formula,))
    solver.add(formula)
    status, model, reason, elapsed_ms, _started = _check_with_budget(solver, budget)
    if status == "unsat":
        return BmcRuntimeSafetyResult("safe", len(sites), elapsed_ms), budget
    if status != "sat":
        return (
            BmcRuntimeSafetyResult(status, len(sites), elapsed_ms, reason=reason or status),
            budget,
        )
    # Sites are listed in evaluation order and each one holds only where its
    # operation is reached, so the first one the model raises is the error
    # the runtime reports.
    for error in sites:
        if _holds(model, error.condition):
            break
    else:  # pragma: no cover - the model satisfies a disjunction of the sites.
        raise BmcBuildError("runtime error model raises none of its sites.")
    return (
        BmcRuntimeSafetyResult(
            "violated", len(sites), elapsed_ms, error=error, model=model, core=core
        ),
        budget,
    )

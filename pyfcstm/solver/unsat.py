"""Property-neutral UNSAT core queries with explicit fixed background.

Source handles remain attached to the original constraints. A verified core is
only evidence that its conjunction with the background is unsatisfiable; it is
not a derivation, a minimum-cardinality core, or a property verdict. This module
also supplies the extraction and deletion checks used by scenario explanations.

Example::

    >>> import z3
    >>> x = z3.Int("x")
    >>> query = UnsatQuery("bounds", (
    ...     UnsatConstraint("lower", (x > 0,)),
    ...     UnsatConstraint("upper", (x <= 0,)),
    ... ))
    >>> result = explain_unsat_core(query)
    >>> result.solver_status, result.core_ids, result.subset_minimality
    ('unsat', ('lower', 'upper'), 'proven')
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any, Optional, Sequence, Tuple

import z3

from .budget import SolveBudget

__all__ = [
    "UnsatConstraint",
    "UnsatQuery",
    "UnsatExplanation",
    "explain_unsat_core",
]


@dataclass(frozen=True)
class UnsatConstraint:
    """An independently named formula group and an opaque source handle.

    :param stable_id: Non-empty occurrence identifier, not a formula hash.
    :type stable_id: str
    :param expressions: Non-empty Boolean Z3 expressions in one context.
    :type expressions: Tuple[z3.BoolRef, ...]
    :param source: Caller-owned source object, preserved by identity; defaults
        to ``None``. It may contain multiple source occurrences or construction
        dependencies. The checker neither interprets nor validates it; it is
        metadata, never a premise or proof certificate.
    :type source: object, optional
    :raises ValueError: For an empty identifier or expression group, or mixed
        Z3 contexts.
    :raises TypeError: For a non-string identifier or non-Boolean expression.

    Example::

        >>> UnsatConstraint("guard", (z3.BoolVal(False),)).stable_id
        'guard'
    """

    stable_id: str
    expressions: Tuple[z3.BoolRef, ...]
    source: Any = None

    def __post_init__(self):
        if not isinstance(self.stable_id, str):
            raise TypeError("constraint stable_id must be a string")
        if not self.stable_id:
            raise ValueError("constraint stable_id must not be empty")
        expressions = tuple(self.expressions)
        if not expressions:
            raise ValueError("constraint expressions must not be empty")
        if any(not z3.is_bool(expression) for expression in expressions):
            raise TypeError("constraint expressions must be Boolean Z3 expressions")
        if any(expression.ctx != expressions[0].ctx for expression in expressions):
            raise ValueError("constraint expressions must share one Z3 context")
        object.__setattr__(self, "expressions", expressions)


@dataclass(frozen=True)
class UnsatQuery:
    """An exact named conjunction with a fixed, explicit background.

    The queried formula is the conjunction of every expression in both
    collections. No property polarity is inferred from ``query_id``.

    :param query_id: Non-empty caller-defined query/phase identity.
    :type query_id: str
    :param constraints: Removable named groups considered for the core.
    :type constraints: Tuple[UnsatConstraint, ...]
    :param background: Named groups retained in every check, defaults to ``()``.
    :type background: Tuple[UnsatConstraint, ...], optional
    :raises TypeError: For a non-string identity or non-constraint member.
    :raises ValueError: For an empty identity, duplicate group identifiers or
        expressions belonging to different Z3 contexts.

    Example::

        >>> explain_unsat_core(UnsatQuery("empty", ())).solver_status
        'sat'
    """

    query_id: str
    constraints: Tuple[UnsatConstraint, ...]
    background: Tuple[UnsatConstraint, ...] = ()

    def __post_init__(self):
        if not isinstance(self.query_id, str):
            raise TypeError("query_id must be a string")
        if not self.query_id:
            raise ValueError("query_id must not be empty")
        constraints, background = tuple(self.constraints), tuple(self.background)
        groups = constraints + background
        if any(not isinstance(group, UnsatConstraint) for group in groups):
            raise TypeError("query members must be UnsatConstraint values")
        if len({group.stable_id for group in groups}) != len(groups):
            raise ValueError(
                "query constraint and background identifiers must be unique"
            )
        if groups and any(
            group.expressions[0].ctx != groups[0].expressions[0].ctx for group in groups
        ):
            raise ValueError("query expressions must share one Z3 context")
        object.__setattr__(self, "constraints", constraints)
        object.__setattr__(self, "background", background)


@dataclass(frozen=True)
class ProbeRecord:
    """One refinement solver invocation and its outcome.

    :param name: Probe name such as ``component`` or ``domain``.
    :type name: str
    :param status: Solver status reported for the probe.
    :type status: str
    :param started: Whether the solver check actually ran.
    :type started: bool
    :param elapsed_ms: Wall-clock duration of the check.
    :type elapsed_ms: float
    :param reason: Why an undetermined probe ended, defaults to ``None``.  It
        is required for ``unknown`` and ``timeout`` so a degraded probe can
        always explain itself.
    :type reason: Optional[str], optional

    Example::

        >>> ProbeRecord("component", "unsat", True, 0.5).started
        True
    """

    name: str
    status: str
    started: bool
    elapsed_ms: float
    reason: Optional[str] = None


@dataclass(frozen=True)
class CoreExtraction:
    """Sound source groups that already make the target unsatisfiable.

    :param groups: Core member groups ordered by ``stable_id``.
    :type groups: Tuple[Any, ...]
    :param status: ``complete``, ``unknown`` or ``timeout``.
    :type status: str
    :param reason: Why extraction degraded, defaults to ``None``.
    :type reason: Optional[str], optional
    :param checks: Solver invocations in execution order, defaults to ``()``.
    :type checks: Tuple[ProbeRecord, ...], optional
    :param solver_status: Full-query solver result, defaults to ``unknown``.
    :type solver_status: str, optional
    :param core_check: Independent subset check, defaults to ``not_checked``.
    :type core_check: str, optional

    Example::

        >>> CoreExtraction((), "timeout", "budget exhausted").status
        'timeout'
    """

    groups: Tuple[Any, ...] = ()
    status: str = "complete"
    reason: Optional[str] = None
    checks: Tuple[ProbeRecord, ...] = ()
    solver_status: str = "unknown"
    core_check: str = "not_checked"


def _run_probe(
    solver: z3.Solver,
    budget: SolveBudget,
    name: str,
    assumptions: Sequence[z3.BoolRef],
) -> Tuple[str, ProbeRecord]:
    """Run one budgeted probe and record whether the check actually started.

    An exhausted budget returns a not-started record. Otherwise Z3 receives
    the remaining rounded millisecond timeout. Solver timeout granularity and
    Python orchestration overhead can extend elapsed time past the deadline.

    :param solver: Refinement solver to query.
    :type solver: z3.Solver
    :param budget: Budget shared with the mandatory solve.
    :type budget: pyfcstm.solver.budget.SolveBudget
    :param name: Frozen refinement check name for the ledger.
    :type name: str
    :param assumptions: Boolean formulas to assume for this probe.
    :type assumptions: Sequence[z3.BoolRef]
    :return: Resolved status and the record describing the attempt.
    :rtype: Tuple[str, ProbeRecord]

    Example::

        >>> import z3
        >>> from pyfcstm.solver.budget import SolveBudget
        >>> status, record = _run_probe(z3.Solver(), SolveBudget(None), "unsat_core", ())
        >>> status
        'sat'
    """
    remaining = budget.remaining_ms()
    if budget.deadline is not None and remaining is None:
        return "timeout", ProbeRecord(
            name, "timeout", False, 0.0, "budget exhausted before the probe started"
        )
    if remaining is not None:
        solver.set(timeout=remaining)
    start = time.monotonic()
    status = solver.check(*assumptions)
    elapsed = (time.monotonic() - start) * 1000.0
    if status == z3.unsat:
        return "unsat", ProbeRecord(name, "unsat", True, elapsed)
    if status == z3.sat:
        return "sat", ProbeRecord(name, "sat", True, elapsed)
    reason = solver.reason_unknown() or "unknown"
    resolved = "timeout" if reason == "timeout" else "unknown"
    return resolved, ProbeRecord(name, resolved, True, elapsed, reason)


def _step_record(
    extraction: ProbeRecord, recheck: ProbeRecord, status: str
) -> ProbeRecord:
    """Collapse the two calls of the core step into one reportable record.

    The frozen result shape carries a single ``unsat_core`` entry, so the
    published timing is the whole step and the status describes the step rather
    than one solver verdict inside it.

    :param extraction: Record of the formula-assumption extraction check.
    :type extraction: ProbeRecord
    :param recheck: Record of the independent soundness recheck.
    :type recheck: ProbeRecord
    :param status: Step outcome to publish.
    :type status: str
    :return: One record covering both calls.
    :rtype: ProbeRecord

    Example::

        >>> a = ProbeRecord("unsat_core", "unsat", True, 1.0)
        >>> b = ProbeRecord("unsat_core", "unsat", True, 2.0)
        >>> _step_record(a, b, "complete").elapsed_ms
        3.0
    """
    return ProbeRecord(
        "unsat_core",
        status,
        extraction.started or recheck.started,
        extraction.elapsed_ms + recheck.elapsed_ms,
        recheck.reason or extraction.reason,
    )


def _probe_outcome_reason(what: str, record: "ProbeRecord") -> str:
    """Describe a probe outcome without claiming a verdict it never produced.

    A probe whose budget was already spent never ran, so saying it "returned"
    anything would contradict the published ledger, which records started probes
    only: a reader would see a returned verdict beside an empty ledger.

    :param what: Human name of the probe, used as the sentence subject.
    :type what: str
    :param record: The probe record, whose ``started`` flag decides the wording.
    :type record: ProbeRecord
    :return: One clause describing what happened to that probe.
    :rtype: str

    Example::

        >>> started = ProbeRecord("component_assumptions", "timeout", True, 1.0, None)
        >>> _probe_outcome_reason("component probe", started)
        'component probe returned timeout'
        >>> skipped = ProbeRecord("component_assumptions", "timeout", False, 0.0, "no budget")
        >>> _probe_outcome_reason("component probe", skipped)
        'component probe did not start: no budget'
    """
    if record.started:
        return "%s returned %s" % (what, record.status)
    return "%s did not start: %s" % (what, record.reason)


@dataclass(frozen=True)
class MinimizedCore:
    """A source core after deterministic deletion shrink and its acceptance run.

    Shrink only ever deletes members, so ``groups`` stays sound no matter where
    the budget ran out.  ``reduction`` and ``subset_minimality`` therefore say how
    far minimization got rather than how the core was built.

    :param groups: Surviving core member groups, ordered by ``stable_id``.
    :type groups: Tuple[Any, ...]
    :param reduction: ``raw``, ``partial_minimized`` or ``subset_minimal``.
    :type reduction: str
    :param subset_minimality: ``proven`` or ``not_proven``.
    :type subset_minimality: str
    :param status: ``complete``, ``unknown`` or ``timeout`` for the whole phase.
    :type status: str
    :param reason: Why minimization degraded, defaults to ``None``.
    :type reason: Optional[str], optional
    :param record: The single aggregate ledger entry for this phase, defaults to
        ``None`` when no trial ran at all.
    :type record: Optional[ProbeRecord], optional

    Example::

        >>> minimized = MinimizedCore((), "raw", "not_proven", "timeout", "no budget")
        >>> minimized.reduction, minimized.subset_minimality
        ('raw', 'not_proven')
    """

    groups: Tuple[Any, ...]
    reduction: str
    subset_minimality: str
    status: str = "complete"
    reason: Optional[str] = None
    record: Optional[ProbeRecord] = None


def _trial_solver(groups, background=()) -> z3.Solver:
    """Return a solver asserting every expression of the given groups.

    :param groups: Groups whose conjunction is being tested.
    :type groups: Sequence[Any]
    :param background: Fixed groups asserted alongside the candidate.
    :type background: tuple
    :return: A solver holding exactly those expressions.
    :rtype: z3.Solver

    Example::

        >>> _trial_solver(()).check() == z3.sat
        True
    """
    all_groups = tuple(background) + tuple(groups)
    context = all_groups[0].expressions[0].ctx if all_groups else None
    solver = z3.Solver(ctx=context)
    for group in all_groups:
        for expression in group.expressions:
            solver.add(expression)
    return solver


def _minimize_core(
    extraction: CoreExtraction, budget: SolveBudget, background=()
) -> MinimizedCore:
    """Shrink a sound source core to a subset-minimal one and verify it.

    The loop follows the frozen algorithm: walk the members in ``stable_id``
    order, drop one, and keep the smaller set only when it is still unsat.  A
    satisfiable trial proves the member is load-bearing; an undetermined one
    proves nothing, so the member stays and the phase can only end partial; an
    exhausted budget stops immediately and returns what has been reached.

    Because every step only deletes, the returned groups are unsat whenever the
    input was.  ``subset_minimality`` is upgraded to ``proven`` only after a
    second pass re-checks every surviving member on its own, so the published
    claim rests on the final core rather than on the shrink history.

    :param extraction: The sound raw core to shrink.
    :type extraction: CoreExtraction
    :param budget: Shared deadline, checked before each solver invocation.
    :type budget: pyfcstm.solver.budget.SolveBudget
    :param background: Fixed groups retained in every deletion and acceptance check.
    :type background: tuple
    :return: The minimized core and the aggregate record for the phase.
    :rtype: MinimizedCore

    Example::

        >>> from pyfcstm.solver.budget import SolveBudget
        >>> empty = CoreExtraction(())
        >>> _minimize_core(empty, SolveBudget(None)).reduction
        'raw'
    """
    candidate = list(extraction.groups)
    if not candidate:
        # Nothing to shrink, and nothing to claim about a core that has no
        # members: the caller decides whether an empty extraction is publishable.
        return MinimizedCore((), "raw", "not_proven", extraction.status)

    started = 0
    degraded = None
    started_at = time.perf_counter()
    # Test even the last member: the background may be SAT or independently
    # UNSAT. Only a solver result can justify keeping it or returning an empty core.
    for group in tuple(candidate):
        trial = [item for item in candidate if item.stable_id != group.stable_id]
        verdict, record = _run_probe(
            _trial_solver(trial, background), budget, "unsat_core_minimization", ()
        )
        if not record.started:
            degraded = "budget exhausted before a deletion trial started"
            break
        started += 1
        if verdict == "unsat":
            candidate = trial
        elif verdict == "sat":
            continue
        elif verdict == "timeout":
            degraded = "deletion trial timed out"
            break
        else:
            degraded = "deletion trial returned unknown"

    if degraded is None:
        status = "complete"
    elif "timed out" in degraded or "budget exhausted" in degraded:
        # §9.3 groups an exhausted budget with a timed-out trial: both mean the
        # deadline stopped minimization, which is a different report from a
        # solver that ran and gave up.
        status = "timeout"
    else:
        status = "unknown"

    proven = False
    if status == "complete":
        proven = True
        for group in tuple(candidate):
            remaining = [
                item for item in candidate if item.stable_id != group.stable_id
            ]
            verdict, record = _run_probe(
                _trial_solver(remaining, background),
                budget,
                "unsat_core_minimization",
                (),
            )
            if not record.started or verdict != "sat":
                proven = False
                status = "timeout" if verdict == "timeout" else "unknown"
                degraded = (
                    "acceptance check for %s did not return sat" % group.stable_id
                )
                break
            started += 1

    if proven:
        reduction = "subset_minimal"
    elif started:
        reduction = "partial_minimized"
    else:
        reduction = "raw"

    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    aggregate = (
        ProbeRecord(
            "unsat_core_minimization",
            status,
            True,
            elapsed_ms,
            degraded,
        )
        if started
        else None
    )
    return MinimizedCore(
        tuple(candidate),
        reduction,
        "proven" if proven else "not_proven",
        status,
        degraded,
        aggregate,
    )


def _extract_constraint_core(targets, background, budget, selected_ids=None):
    """Extract or verify a selected subset against exactly its fixed background."""
    solver = (
        _trial_solver((), background)
        if background
        else z3.Solver(ctx=targets[0].expressions[0].ctx if targets else None)
    )
    by_formula = {}
    assumptions = []
    for group in targets:
        expression = z3.And(*group.expressions)
        # Z3 accepts compound assumptions and returns their original ASTs in
        # the core. FreshBool names can alias authored symbols such as core!0.
        # Identical groups need only one representative; explicit selections
        # below still preserve the caller's chosen source occurrences.
        by_formula.setdefault(expression.get_id(), group)
        assumptions.append(expression)

    status, record = _run_probe(solver, budget, "unsat_core", assumptions)
    if status != "unsat":
        return CoreExtraction(
            (),
            status,
            _probe_outcome_reason("core extraction", record),
            (record,),
            status,
        )
    if selected_ids is None:
        selected = [
            by_formula[expression.get_id()] for expression in solver.unsat_core()
        ]
    else:
        selected = [group for group in targets if group.stable_id in selected_ids]
    ordered = tuple(sorted(selected, key=lambda group: group.stable_id))
    verifier = _trial_solver(ordered, background)
    recheck, verify_record = _run_probe(verifier, budget, "unsat_core", ())
    check = "verified" if recheck == "unsat" else recheck
    checks = (
        _step_record(
            record, verify_record, "complete" if recheck == "unsat" else recheck
        ),
    )
    if recheck != "unsat":
        return CoreExtraction(
            (),
            "timeout" if recheck == "timeout" else "unknown",
            "selected core did not re-check as unsat (%s)" % recheck,
            checks,
            status,
            check,
        )
    return CoreExtraction(ordered, "complete", None, checks, status, check)


@dataclass(frozen=True)
class UnsatExplanation:
    """Evidence for one query, without a property verdict or invented derivation.

    Instances are returned by :func:`explain_unsat_core`. ``core_ids=None``
    means no verified core; ``core_ids=()`` means the fixed background alone
    was rechecked UNSAT. ``solver_status`` always refers to the entire query,
    even when a supplied subset fails its independent check.

    :param query: The original query, including source handles and background.
    :type query: UnsatQuery
    :param solver_status: ``sat``, ``unsat``, ``unknown`` or ``timeout``.
    :type solver_status: str
    :param core_ids: Verified removable group identifiers, or ``None``.
    :type core_ids: Optional[Tuple[str, ...]]
    :param core_check: ``verified``, ``not_checked``, ``sat``, ``unknown`` or ``timeout``.
    :type core_check: str
    :param subset_minimality: ``proven`` or ``not_proven`` relative to the background.
    :type subset_minimality: str
    :param reduction: ``raw``, ``partial_minimized`` or ``subset_minimal``.
    :type reduction: str
    :param stop_reason: Explanation failure or minimization interruption, if any.
    :type stop_reason: Optional[str]
    :param checks: Budgeted extraction/recheck and optional minimization records.
    :type checks: Tuple[ProbeRecord, ...]
    :param derivation_status: ``not_attempted``; a core is not a derivation.
    :type derivation_status: str
    :param proof_status: ``not_attempted``; no source-level proof is constructed.
    :type proof_status: str
    """

    query: UnsatQuery
    solver_status: str
    core_ids: Optional[Tuple[str, ...]]
    core_check: str
    subset_minimality: str
    reduction: str
    stop_reason: Optional[str]
    checks: Tuple[ProbeRecord, ...]
    derivation_status: str = "not_attempted"
    proof_status: str = "not_attempted"

    @property
    def background_conflict(self) -> bool:
        """Whether the fixed background alone was verified unsatisfiable.

        :return: ``True`` for a verified empty tracked core.
        :rtype: bool
        """
        return self.core_ids == () and self.core_check == "verified"


def explain_unsat_core(query, *, selected_ids=None, minimize=True, timeout_ms=None):
    """Check an exact query and return a rechecked, source-bearing conflict core.

    Extraction, rechecking and deterministic deletion share one monotonic
    deadline. No solver work runs until this function is called. A caller's
    selected subset is checked without adding omitted constraints back. Use
    ``minimize=False`` to retain exactly those source identifiers, even when
    another occurrence has an identical formula. The result sorts identifiers;
    it does not preserve selection order. With ``minimize=True`` (the default),
    the verified selection may be reduced further. A SAT or UNKNOWN query
    produces no core, not an exception or a property verdict.

    :param query: Exact formula groups and fixed background.
    :type query: UnsatQuery
    :param selected_ids: Optional subset of removable identifiers to verify;
        ``None`` asks Z3 to select a core. An empty sequence tests the background.
    :type selected_ids: Optional[Sequence[str]], optional
    :param minimize: Shrink a verified core, including an explicitly selected
        one, and verify subset minimality; defaults to ``True``. Set to
        ``False`` when explaining an existing selected set without changing it.
        Does not search for minimum cardinality.
    :type minimize: bool, optional
    :param timeout_ms: Shared positive millisecond budget, or ``None`` (unbounded).
    :type timeout_ms: Optional[int], optional
    :return: Solver result and independently qualified core evidence.
    :rtype: UnsatExplanation
    :raises TypeError: For a wrong query, selection member or minimization type.
    :raises ValueError: For unknown or duplicate selected identifiers.
    :raises ValueError: For an invalid timeout.

    Example::

        >>> query = UnsatQuery("false", (UnsatConstraint("rule", (z3.BoolVal(False),)),))
        >>> explain_unsat_core(query, minimize=False).core_ids
        ('rule',)
    """
    if not isinstance(query, UnsatQuery):
        raise TypeError("query must be a UnsatQuery")
    if not isinstance(minimize, bool):
        raise TypeError("minimize must be a bool")
    if selected_ids is not None:
        if isinstance(selected_ids, str):
            raise TypeError(
                "selected_ids must be a sequence of identifiers, not a string"
            )
        selected_ids = tuple(selected_ids)
        if any(not isinstance(item, str) for item in selected_ids):
            raise TypeError("selected_ids must contain strings")
        known = {group.stable_id for group in query.constraints}
        if (
            len(set(selected_ids)) != len(selected_ids)
            or not set(selected_ids) <= known
        ):
            raise ValueError(
                "selected_ids must be unique removable constraint identifiers"
            )
    budget = SolveBudget(timeout_ms)
    extraction = _extract_constraint_core(
        query.constraints, query.background, budget, selected_ids
    )
    verified = extraction.core_check == "verified"
    reduced = MinimizedCore(extraction.groups, "raw", "not_proven")
    if verified and minimize:
        if not extraction.groups:
            reduced = MinimizedCore((), "subset_minimal", "proven")
        else:
            reduced = _minimize_core(extraction, budget, query.background)
    checks = extraction.checks
    if reduced.record is not None:
        checks += (reduced.record,)
    return UnsatExplanation(
        query,
        extraction.solver_status,
        tuple(group.stable_id for group in reduced.groups) if verified else None,
        extraction.core_check,
        reduced.subset_minimality,
        reduced.reduction,
        extraction.reason or reduced.reason,
        checks,
    )

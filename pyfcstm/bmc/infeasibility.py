"""Classification probes and sound source-core extraction for BMC scenarios.

When the mandatory verdict has localized the first infeasible stage, this
module answers the two remaining questions: *how* that stage is infeasible,
and *which* tracked source groups already suffice to make it infeasible.

The orchestration here never rebuilds a formula.  It reuses the aggregate
:class:`z3.BoolRef` values the relation builder already produced, drives a
dedicated refinement solver through activation literals, and shares one
monotonic budget with the mandatory solve so an optional explanation can never
outlive the caller's timeout.

The module contains:

* :func:`partition_tracked_groups` - split tracked groups into the four
  aggregates and assert the split reproduces them
* :func:`classify_infeasibility` - run the fewest probes that determine one of
  the seven classifications
* :func:`extract_source_core` - map an unsat core back to sound source groups
* :func:`build_core_item` - give one tracked group its public reading
* :func:`explain_infeasibility` - the single entry point that turns solver work
  into a published :class:`~pyfcstm.bmc.explanation.BmcInfeasibilityExplanation`

.. note::
   Public explanation values live in :mod:`pyfcstm.bmc.explanation`, which
   stays free of Z3.  This module is the only side that touches the solver, so
   the dependency direction is one-way.

Example::

    >>> from pyfcstm.bmc.infeasibility import AGGREGATE_SELECTORS
    >>> sorted(AGGREGATE_SELECTORS)
    ['domain', 'environment', 'initial', 'transition']
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from types import MappingProxyType
from typing import (
    TYPE_CHECKING,
    Any,
    Callable,
    Dict,
    Mapping,
    Optional,
    Sequence,
    Tuple,
    Union,
)

import z3

from .errors import BmcBuildError
from .explanation import (
    BmcConflictNarrative,
    # Private because the frozen public surface must not grow to expose it, and
    # cross-module because the fact vocabulary is owned in one place: a second
    # copy of "which keys does this tag imply" is how the two sides drift apart.
    _readable,
    index_value,
    CLASSIFICATION_SCOPES,
    SCOPE_AGGREGATES,
    category_role,
    constraint_aggregate,
    MAX_SOURCE_EXCERPT_CHARS,
    BmcConflictCore,
    BmcConstraintRef,
    BmcCoreItem,
    BmcInfeasibilityExplanation,
    build_conflict_narrative,
    human_text_for_fact,
)
from .provenance import (
    # Private: the binding check has to name a frame symbol the same way the
    # published facts were named from it, and a second reading of the encoding
    # would be a second place to keep in step.
    _frame_variable_name,
    BmcTrackedConstraint,
    SourceDocumentRegistry,
    normalized_fact_for,
)
from .solver import _SolveBudget, _check_with_budget

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for annotations only
    from .relation import BmcCoreFormula


def _aggregate_of(group: BmcTrackedConstraint) -> str:
    """Return the aggregate a tracked group belongs to, or ``""`` when unknown.

    The rule itself lives in the solver-free data layer, so the partition here
    and the scope check on a published core cannot disagree.

    :param group: Tracked source group to classify.
    :type group: pyfcstm.bmc.provenance.BmcTrackedConstraint
    :return: Aggregate name, or an empty string when the group fits none.
    :rtype: str

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint
        >>> group = BmcTrackedConstraint(
        ...     "initial.where.definedness.0000", "initialization",
        ...     "definedness", (True,), BmcSourceRef("generated", None, None),
        ... )
        >>> _aggregate_of(group)
        'initial'
    """
    try:
        return constraint_aggregate(group.stage, group.category)
    except ValueError:
        # constraint_aggregate raises ValueError for a stage/category pairing
        # it does not recognize; the caller reports that as builder drift.
        return ""


#: Predicate per aggregate; the kernel stage covers both domain and transition.
AGGREGATE_SELECTORS: "Mapping[str, Callable[[BmcTrackedConstraint], bool]]" = (
    MappingProxyType(
        {
            name: (lambda group, expected=name: _aggregate_of(group) == expected)
            for name in ("domain", "transition", "initial", "environment")
        }
    )
)

#: Aggregates that make up the target formula of every published scope.  The
#: table itself lives in the solver-free data layer next to the scope
#: vocabulary, so the published core's membership rule and the candidate set
#: used here are the same object rather than two lists kept in step by hand.
SCOPE_TARGETS: "Mapping[str, Tuple[str, ...]]" = SCOPE_AGGREGATES

_STAGE_FALLBACK_BY_STAGE = MappingProxyType(
    {
        "initialization": "initialization_stage_fallback",
        "assumptions": "assumptions_stage_fallback",
    }
)


@dataclass(frozen=True)
class TrackedGroupPartition:
    """Tracked source groups split into the four aggregate formulas.

    :param domain: Groups making up ``D_N``.
    :type domain: Tuple[pyfcstm.bmc.provenance.BmcTrackedConstraint, ...]
    :param initial: Groups making up ``I_0``.
    :type initial: Tuple[pyfcstm.bmc.provenance.BmcTrackedConstraint, ...]
    :param transition: Groups making up ``T_N``.
    :type transition: Tuple[pyfcstm.bmc.provenance.BmcTrackedConstraint, ...]
    :param environment: Groups making up ``ENV_N``.
    :type environment: Tuple[pyfcstm.bmc.provenance.BmcTrackedConstraint, ...]

    Example::

        >>> partition = TrackedGroupPartition((), (), (), ())
        >>> partition.domain
        ()
    """

    domain: Tuple[BmcTrackedConstraint, ...]
    initial: Tuple[BmcTrackedConstraint, ...]
    transition: Tuple[BmcTrackedConstraint, ...]
    environment: Tuple[BmcTrackedConstraint, ...]

    def groups_for(self, scope: str) -> Tuple[BmcTrackedConstraint, ...]:
        """Return the ordered target groups of one published scope.

        :param scope: Diagnostic or stage-fallback scope name.
        :type scope: str
        :return: Groups whose conjunction is the scope's target formula.
        :rtype: Tuple[pyfcstm.bmc.provenance.BmcTrackedConstraint, ...]
        :raises pyfcstm.bmc.errors.BmcBuildError: If the scope is unknown.

        Example::

            >>> TrackedGroupPartition((), (), (), ()).groups_for("kernel")
            ()
        """
        if scope not in SCOPE_TARGETS:
            raise BmcBuildError("Unsupported conflict core scope: %r." % scope)
        groups = []
        for name in SCOPE_TARGETS[scope]:
            groups.extend(getattr(self, name))
        return tuple(groups)


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
class ClassificationOutcome:
    """Result of the component and domain probes for one localized stage.

    :param classification: Structured classification, or ``None`` when the
        probes could not finish honestly.
    :type classification: Optional[str]
    :param scope: Diagnostic scope, or the stage fallback when unclassified.
    :type scope: str
    :param status: ``complete``, ``unknown`` or ``timeout``.
    :type status: str
    :param reason: Why the classification degraded, defaults to ``None``.
    :type reason: Optional[str], optional
    :param checks: Probe records in execution order, defaults to ``()``.
    :type checks: Tuple[ProbeRecord, ...], optional

    Example::

        >>> ClassificationOutcome("kernel_conflict", "kernel", "complete").scope
        'kernel'
    """

    classification: Optional[str]
    scope: str
    status: str
    reason: Optional[str] = None
    checks: Tuple[ProbeRecord, ...] = ()


@dataclass(frozen=True)
class CoreExtraction:
    """Sound source groups that already make the target unsatisfiable.

    :param groups: Core member groups ordered by ``stable_id``.
    :type groups: Tuple[pyfcstm.bmc.provenance.BmcTrackedConstraint, ...]
    :param status: ``complete``, ``unknown`` or ``timeout``.
    :type status: str
    :param reason: Why extraction degraded, defaults to ``None``.
    :type reason: Optional[str], optional
    :param checks: Solver invocations in execution order, defaults to ``()``.
    :type checks: Tuple[ProbeRecord, ...], optional

    Example::

        >>> CoreExtraction((), "timeout", "budget exhausted").status
        'timeout'
    """

    groups: Tuple[BmcTrackedConstraint, ...] = ()
    status: str = "complete"
    reason: Optional[str] = None
    checks: Tuple[ProbeRecord, ...] = ()


@dataclass(frozen=True)
class ExplanationOutcome:
    """A published explanation together with the checks that produced it.

    The explanation itself has a frozen nine-field shape that deliberately
    excludes solver telemetry, so the probe ledger travels beside it for the
    caller that fills the aggregate feasibility fields.

    :param explanation: Public explanation for the localized stage.
    :type explanation: pyfcstm.bmc.explanation.BmcInfeasibilityExplanation
    :param checks: Probe records in execution order, defaults to ``()``.
    :type checks: Tuple[ProbeRecord, ...], optional

    Example::

        >>> from pyfcstm.bmc.explanation import BmcInfeasibilityExplanation
        >>> outcome = ExplanationOutcome(
        ...     BmcInfeasibilityExplanation(
        ...         "formal", "none", "timeout", None, reason="budget spent",
        ...     ),
        ... )
        >>> outcome.checks
        ()
    """

    explanation: BmcInfeasibilityExplanation
    checks: Tuple[ProbeRecord, ...] = ()


def _conjunction(groups: Sequence[BmcTrackedConstraint]) -> z3.BoolRef:
    """Conjoin every expression of an ordered group sequence.

    An empty sequence yields ``True`` so a scope whose target happens to carry
    no group still produces a well-formed formula instead of failing.

    :param groups: Ordered tracked groups to conjoin.
    :type groups: Sequence[pyfcstm.bmc.provenance.BmcTrackedConstraint]
    :return: Conjunction of every expression, in registration order.
    :rtype: z3.BoolRef

    Example::

        >>> _conjunction(()).sexpr()
        'true'
    """
    expressions = [item for group in groups for item in group.expressions]
    if not expressions:
        return z3.BoolVal(True)
    if len(expressions) == 1:
        return expressions[0]
    return z3.And(*expressions)


def partition_tracked_groups(core: "BmcCoreFormula") -> TrackedGroupPartition:
    """Split tracked groups into aggregates and verify the split is faithful.

    The relation builder derives each aggregate by slicing its ordered group
    ledger, and those slice boundaries are not persisted.  ``stage`` and
    ``category`` only correlate with that order, so this function rebuilds each
    aggregate from the partition and compares S-expressions before returning.
    A mismatch means the builder changed and the partition can no longer be
    trusted to describe a published core scope.

    :param core: Core formula carrying the tracked group ledger.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :return: Groups split into the four aggregates.
    :rtype: TrackedGroupPartition
    :raises pyfcstm.bmc.errors.BmcBuildError: If a group matches no aggregate
        or a rebuilt aggregate differs from the builder's own formula.

    Example::

        >>> from pyfcstm.bmc import build_bmc_core_formula
        >>> from pyfcstm.bmc.engine import BmcEngine
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> machine = load_state_machine_from_text("state Root;")
        >>> context = BmcEngine(machine).prepare(
        ...     'check reach <= 1: active("Root");'
        ... )
        >>> partition = partition_tracked_groups(build_bmc_core_formula(context))
        >>> bool(partition.domain)
        True
    """
    buckets: Dict[str, list] = {name: [] for name in AGGREGATE_SELECTORS}
    for group in core._tracked_groups:
        for name, predicate in AGGREGATE_SELECTORS.items():
            if predicate(group):
                buckets[name].append(group)
                break
        else:
            raise BmcBuildError(  # pragma: no cover - every registered pairing has a selector.
                "tracked group %r has no aggregate selector (stage=%r, category=%r)."
                % (group.stable_id, group.stage, group.category)
            )

    partition = TrackedGroupPartition(
        domain=tuple(buckets["domain"]),
        initial=tuple(buckets["initial"]),
        transition=tuple(buckets["transition"]),
        environment=tuple(buckets["environment"]),
    )

    for name, formula in (
        ("domain", core.domain_formula),
        ("initial", core.initial_formula),
        ("transition", core.transition_formula),
        ("environment", core.environment_formula),
    ):
        rebuilt = _conjunction(getattr(partition, name))
        if rebuilt.sexpr() != formula.sexpr():
            raise BmcBuildError(  # pragma: no cover - the partition is rebuilt from the same groups.
                "rebuilt %s aggregate does not match the relation builder output; "
                "the tracked group registration order changed." % name
            )
    return partition


def _activation_solver(
    partition: TrackedGroupPartition,
) -> Tuple[z3.Solver, Dict[str, z3.BoolRef]]:
    """Build a refinement solver gated by one literal per aggregate.

    Each aggregate enters the solver as ``literal -> aggregate`` so a probe can
    switch whole formulas on and off through assumptions.  The property
    objective is never added, which keeps scenario reasoning independent of
    what the query was asking about.

    :param partition: Tracked groups split into the four aggregates.
    :type partition: TrackedGroupPartition
    :return: The solver and its activation literal per aggregate name.
    :rtype: Tuple[z3.Solver, Dict[str, z3.BoolRef]]

    Example::

        >>> solver, literals = _activation_solver(
        ...     TrackedGroupPartition((), (), (), ())
        ... )
        >>> sorted(literals)
        ['domain', 'environment', 'initial', 'transition']
    """
    solver = z3.Solver()
    literals: Dict[str, z3.BoolRef] = {}
    for name in ("domain", "transition", "initial", "environment"):
        literal = z3.Bool("g_%s" % name)
        literals[name] = literal
        solver.add(z3.Implies(literal, _conjunction(getattr(partition, name))))
    return solver, literals


def _run_probe(
    solver: z3.Solver,
    budget: _SolveBudget,
    name: str,
    assumptions: Sequence[z3.BoolRef],
) -> Tuple[str, ProbeRecord]:
    """Run one budgeted probe and record whether the check actually started.

    The probe never outlives the shared deadline: an exhausted budget returns
    a not-started record instead of launching a check that would extend the
    caller's timeout.

    :param solver: Refinement solver to query.
    :type solver: z3.Solver
    :param budget: Budget shared with the mandatory solve.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :param name: Frozen refinement check name for the ledger.
    :type name: str
    :param assumptions: Activation literals to assume for this probe.
    :type assumptions: Sequence[z3.BoolRef]
    :return: Resolved status and the record describing the attempt.
    :rtype: Tuple[str, ProbeRecord]

    Example::

        >>> import z3
        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> status, record = _run_probe(z3.Solver(), _SolveBudget(None), "unsat_core", ())
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

    :param extraction: Record of the labelled extraction check.
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


def classify_infeasibility(
    core: "BmcCoreFormula", stage: str, budget: _SolveBudget
) -> ClassificationOutcome:
    """Determine how a localized stage is infeasible, using the fewest probes.

    The kernel stage needs no probe: it has no weaker component or domain
    formula, so localization alone already fixes ``kernel_conflict``.  The
    other two stages ask at most two questions and stop as soon as the answer
    is determined.  When a probe cannot finish inside the shared budget, the
    result degrades to the stage fallback rather than guessing a cause.

    :param core: Core formula carrying the tracked group ledger.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param stage: Localized infeasible stage.
    :type stage: str
    :param budget: Budget shared with the mandatory solve.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :return: Classification, scope and probe records.
    :rtype: ClassificationOutcome
    :raises pyfcstm.bmc.errors.BmcBuildError: If the stage is unsupported or
        the tracked group partition no longer matches the builder output.

    Example::

        >>> from pyfcstm.bmc import build_bmc_core_formula
        >>> from pyfcstm.bmc.engine import BmcEngine
        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> machine = load_state_machine_from_text("state Root;")
        >>> context = BmcEngine(machine).prepare(
        ...     'check reach <= 1: active("Root");'
        ... )
        >>> core = build_bmc_core_formula(context)
        >>> classify_infeasibility(core, "kernel", _SolveBudget(None)).classification
        'kernel_conflict'
    """
    if stage == "kernel":
        return ClassificationOutcome("kernel_conflict", "kernel", "complete")
    if stage not in _STAGE_FALLBACK_BY_STAGE:
        raise BmcBuildError("Unsupported infeasible stage: %r." % stage)

    fallback_scope = _STAGE_FALLBACK_BY_STAGE[stage]
    partition = partition_tracked_groups(core)
    solver, literals = _activation_solver(partition)

    component_literal = literals[
        "initial" if stage == "initialization" else "environment"
    ]
    component_name = "component_%s" % stage
    domain_name = "domain_%s" % stage
    checks = []

    status, record = _run_probe(solver, budget, component_name, (component_literal,))
    checks.append(record)
    if status in ("unknown", "timeout"):
        return ClassificationOutcome(
            None,
            fallback_scope,
            status,
            _probe_outcome_reason("component probe", record),
            tuple(checks),
        )
    if status == "unsat":
        classification = (
            "initialization_self_conflict"
            if stage == "initialization"
            else "assumptions_self_conflict"
        )
        return ClassificationOutcome(
            classification,
            CLASSIFICATION_SCOPES[classification],
            "complete",
            None,
            tuple(checks),
        )

    status, record = _run_probe(
        solver, budget, domain_name, (literals["domain"], component_literal)
    )
    checks.append(record)
    if status in ("unknown", "timeout"):
        return ClassificationOutcome(
            None,
            fallback_scope,
            status,
            _probe_outcome_reason("domain probe", record),
            tuple(checks),
        )
    if status == "unsat":
        # ``assumptions_domain_conflict`` is reached by excluding every state a
        # frame could hold: the domain aggregate enumerates them, so ruling all of
        # them out at one frame contradicts it.  The benchmark corpus case
        # ``state_domain`` does exactly that and lands here with an
        # ``assumptions_domain`` scope.
        #
        # ``initialization_domain_conflict`` is the same shape on the other stage
        # and has no producing path, because the initializer cannot put frame 0
        # outside the domain it is checked against.  Every ``init_target`` pins
        # ``F_0_state`` to one literal -- ``cold`` to -3, ``terminated`` to -1, a
        # named state to its id -- and the domain aggregate for that frame is the
        # disjunction over exactly those values, sentinels included.  So any
        # assignment satisfying the initial component already satisfies the frame-0
        # domain, which makes the domain probe satisfiable whenever the component
        # probe above was, and the unsat branch unreachable from this stage.  An
        # optional ``WHERE`` cannot change that: it constrains the same frame, so it
        # either leaves the component satisfiable, in which case the reasoning holds,
        # or contradicts the pin and is reported as ``initialization_self_conflict``
        # before the domain probe runs.
        #
        # The assumptions side reaches the shape because it can constrain a frame the
        # initializer did not pin, which is what ``assume at 1: !active(...)`` on
        # every state does.
        #
        # Two earlier versions of this comment gave reasons that do not hold.  The
        # grammar does admit the exclusion -- ``init_clause`` carries an optional
        # ``WHERE`` over the full condition language -- and ``cold`` does pin frame 0
        # rather than leaving it free, so the argument cannot rest on the component
        # probe refusing every ``WHERE``.  ``init cold where !active("Root.A") &&
        # !active("Root.B") && !terminated();`` leaves the component probe satisfiable
        # and lands in ``initialization_kernel_conflict``; that query is a case in
        # ``test_classification_on_real_queries``.
        #
        # Whether it should stay in the frozen vocabulary is a contract decision
        # recorded on the tracking issue, not one this branch settles.  An earlier
        # attempt to reach it forged the aggregate formula, which the test boundary
        # rules out.
        classification = (
            "initialization_domain_conflict"
            if stage == "initialization"
            else "assumptions_domain_conflict"
        )
    else:
        classification = (
            "initialization_kernel_conflict"
            if stage == "initialization"
            else "assumptions_prefix_conflict"
        )
    return ClassificationOutcome(
        classification,
        CLASSIFICATION_SCOPES[classification],
        "complete",
        None,
        tuple(checks),
    )


def extract_source_core(
    core: "BmcCoreFormula", scope: str, budget: _SolveBudget
) -> CoreExtraction:
    """Extract a sound source core for one scope and re-verify it.

    Every target group gets its own activation literal, so the solver's unsat
    core maps back to whole source groups instead of anonymous clauses.  The
    result is only published when the returned labels resolve to exactly one
    in-scope group each and the resulting conjunction is still unsatisfiable.

    :param core: Core formula carrying the tracked group ledger.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param scope: Diagnostic or stage-fallback scope to prove.
    :type scope: str
    :param budget: Budget shared with the mandatory solve.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :return: Ordered core groups, or a degraded status with a reason.  A core
        that fails its own recheck is withheld and reported as degraded, not
        raised, so an optional explanation never turns a usable verdict into a
        crash.
    :rtype: CoreExtraction
    :raises pyfcstm.bmc.errors.BmcBuildError: If the scope is unknown, or a
        returned label cannot be mapped back to exactly one in-scope group.

    Example::

        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> from pyfcstm.bmc.infeasibility import SCOPE_TARGETS
        >>> "assumptions_component" in SCOPE_TARGETS
        True
    """
    if scope not in SCOPE_TARGETS:
        raise BmcBuildError("Unsupported conflict core scope: %r." % scope)

    partition = partition_tracked_groups(core)
    targets = partition.groups_for(scope)
    if not targets:
        return CoreExtraction(
            (), "unknown", "scope %r selected no source group" % scope
        )

    solver = z3.Solver()
    by_label: Dict[str, BmcTrackedConstraint] = {}
    labels = []
    for group in targets:
        # A stable id is metadata and never enters a group's expressions, so
        # the partition assertion cannot see two groups sharing one id: the
        # rebuilt aggregates stay identical.  Without this check the second
        # group would silently overwrite the first in by_label, one activation
        # literal would gate two different formulas, and the core would map
        # back to the wrong group.
        label_name = "core_%s" % group.stable_id
        if label_name in by_label:
            raise BmcBuildError(  # pragma: no cover - the builder assigns one stable id per group.
                "two tracked groups share the stable id %r." % group.stable_id
            )
        label = z3.Bool(label_name)
        by_label[label_name] = group
        labels.append(label)
        solver.add(z3.Implies(label, _conjunction((group,))))

    status, record = _run_probe(solver, budget, "unsat_core", labels)
    if status in ("unknown", "timeout"):
        return CoreExtraction(
            (), status, _probe_outcome_reason("core extraction", record), (record,)
        )
    if status == "sat":
        return CoreExtraction(
            (),
            "unknown",
            "internal mismatch: target formula for scope %r is satisfiable, so "
            "the localized stage and this scope disagree" % scope,
            (record,),
        )

    selected = []
    for literal in solver.unsat_core():
        name = literal.decl().name()
        group = by_label.get(name)
        if group is None:
            # Z3 returns a subset of the assumption literals, so this cannot
            # normally fire.  Degrading rather than raising keeps the check that
            # already ran in the ledger: the solver call happened, and reporting
            # an empty ledger would deny work the deadline actually spent.
            return CoreExtraction(
                (),
                "unknown",
                "internal mismatch: unsat core returned the unknown activation "
                "label %r for scope %r" % (name, scope),
                (record,),
            )
        selected.append(group)

    if not selected:
        # Every assertion here is guarded by a label, so an UNSAT result always
        # names at least one of them.  Degrading keeps a hypothetical empty
        # core from reaching BmcConflictCore, which would reject it as a crash
        # rather than as a reportable outcome.
        return CoreExtraction(
            (), "unknown", "solver returned an empty unsat core", (record,)
        )

    ordered = tuple(sorted(selected, key=lambda group: group.stable_id))
    verifier = z3.Solver()
    verifier.add(_conjunction(ordered))
    # The recheck is a second solver call of the same extraction step, so it
    # shares the caller's budget rather than running unbounded.
    recheck, verify_record = _run_probe(verifier, budget, "unsat_core", ())
    if recheck != "unsat":
        return CoreExtraction(
            (),
            "unknown" if recheck != "timeout" else "timeout",
            "extracted core for scope %r did not re-check as unsat (%s)"
            % (scope, recheck),
            (_step_record(record, verify_record, recheck),),
        )
    # The published ledger reports one entry for the whole step, matching the
    # frozen result shape: 'complete' says extraction *and* the independent
    # recheck both succeeded, which is stronger evidence than either raw
    # solver verdict on its own.  Two entries sharing the name would instead
    # read as the same check having run twice.
    return CoreExtraction(
        ordered, "complete", None, (_step_record(record, verify_record, "complete"),)
    )


@dataclass(frozen=True)
class MinimizedCore:
    """A source core after deterministic deletion shrink and its acceptance run.

    Shrink only ever deletes members, so ``groups`` stays sound no matter where
    the budget ran out.  ``reduction`` and ``subset_minimality`` therefore say how
    far minimization got rather than how the core was built.

    :param groups: Surviving core member groups, ordered by ``stable_id``.
    :type groups: Tuple[pyfcstm.bmc.provenance.BmcTrackedConstraint, ...]
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

    groups: Tuple["BmcTrackedConstraint", ...]
    reduction: str
    subset_minimality: str
    status: str = "complete"
    reason: Optional[str] = None
    record: Optional[ProbeRecord] = None


def _trial_solver(groups: Sequence["BmcTrackedConstraint"]) -> z3.Solver:
    """Return a solver asserting every expression of the given groups.

    :param groups: Groups whose conjunction is being tested.
    :type groups: Sequence[pyfcstm.bmc.provenance.BmcTrackedConstraint]
    :return: A solver holding exactly those expressions.
    :rtype: z3.Solver

    Example::

        >>> _trial_solver(()).check() == z3.sat
        True
    """
    solver = z3.Solver()
    for group in groups:
        for expression in group.expressions:
            solver.add(expression)
    return solver


def minimize_source_core(
    core: "BmcCoreFormula", extraction: CoreExtraction, budget: _SolveBudget
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

    :param core: The compiled core formula the groups came from.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param extraction: The sound raw core to shrink.
    :type extraction: CoreExtraction
    :param budget: Shared solver budget; never exceeded.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :return: The minimized core and the aggregate record for the phase.
    :rtype: MinimizedCore

    Example::

        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> empty = CoreExtraction(())
        >>> minimize_source_core(None, empty, _SolveBudget(None)).reduction
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
    # Every member gets its trial, including the last one.  The empty set is
    # satisfiable, so a trial that would empty the candidate always comes back
    # sat and the member is kept -- that is what makes deleting unconditionally
    # safe here, and it is also why the trial has to run: skipping it would leave
    # a one-member core claiming minimality no check ever established, and the
    # phase record that carries the claim would be missing entirely.
    for group in tuple(candidate):
        trial = [item for item in candidate if item.stable_id != group.stable_id]
        verdict, record = _run_probe(
            _trial_solver(trial), budget, "unsat_core_minimization", ()
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
                _trial_solver(remaining), budget, "unsat_core_minimization", ()
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


def _semantic_role(category: str) -> str:
    """Map a tracked group category onto its frozen semantic role.

    The mapping itself lives in the solver-free data layer so the public
    constructors and this orchestration cannot drift apart.

    :param category: Group category assigned by the relation builder.
    :type category: str
    :return: One of the frozen semantic roles.
    :rtype: str
    :raises pyfcstm.bmc.errors.BmcBuildError: If the category matches no known
        prefix, which means a new group family was added without deciding how a
        reader should understand it.

    Example::

        >>> _semantic_role("assumption.frame")
        'assumption'
    """
    try:
        return category_role(category)
    except ValueError as err:
        # category_family raises ValueError for an unregistered prefix; the
        # orchestration reports builder-side drift as a build error.
        raise BmcBuildError(
            "tracked group category %r has no semantic role." % category
        ) from err


def _indices(refs: Mapping[str, object], key: str) -> Tuple[int, ...]:
    """Read a sorted index tuple out of a tracked group's structural metadata.

    The relation builder records one index per group under a singular key
    (``frame``, ``step``), so that spelling is authoritative.  The plural
    spelling is also accepted because the public field is a tuple and a future
    group may well constrain several frames at once.

    ``bool`` is excluded deliberately: it is an ``int`` subclass in Python but
    is not a frame index, and letting it through would publish ``True`` where
    the schema promises an integer.

    :param refs: Structural metadata recorded by the relation builder.
    :type refs: Mapping[str, object]
    :param key: Singular metadata key such as ``frame`` or ``step``.
    :type key: str
    :return: Sorted, de-duplicated, non-negative indices; empty when absent.
    :rtype: Tuple[int, ...]

    Example::

        >>> _indices({"frame": 2}, "frame")
        (2,)
        >>> _indices({"frames": [1, 0, 1]}, "frame")
        (0, 1)
    """

    found = []
    for name in (key, "%ss" % key):
        if name not in refs:
            continue
        value = refs[name]
        # The singular spelling records one index directly, so it is the only
        # one that unwraps a bare value.  The plural spelling must be a sequence,
        # which is the container rule the public constructor applies: accepting a
        # scalar there too would make the two doors disagree on the same field
        # value, with only a comment claiming otherwise.
        if name == key and not isinstance(value, (list, tuple)):
            entries = (value,)
        elif isinstance(value, (list, tuple)):
            entries = value
        else:
            raise BmcBuildError(
                "tracked group metadata %r must be a list or tuple of indices, "
                "got %r." % (name, value)
            )
        for entry in entries:
            try:
                found.append(index_value(entry, name))
            except ValueError as err:
                # index_value refuses anything that is not a non-negative
                # integer index.  Filtering it out instead would publish
                # frames/steps that contradict the refs mapping beside them,
                # with nothing recorded anywhere; the frozen boundary asks for a
                # fail-closed internal mismatch on inconsistent provenance.
                raise BmcBuildError(
                    "tracked group metadata %r is not an index: %s" % (name, err)
                ) from err
    return tuple(sorted(set(found)))


#: Metadata keys whose values the reader interprets as indices.
_INDEX_REF_KEYS = ("frame", "frames", "step", "steps")


def _canonical_refs_value(key: str, value: object) -> object:
    """Return one metadata value in the form it is published under.

    Only the index keys are touched, and only because :func:`_indices` has
    already asserted they hold indices: a value that is not one fails closed
    before this point.  Every other key is free-form metadata and is republished
    untouched, since a whole-valued float elsewhere may well mean a measurement
    rather than a position.

    :param key: Metadata key the value was recorded under.
    :type key: str
    :param value: Recorded metadata value.
    :type value: object
    :return: The value as it should appear in the published mapping.
    :rtype: object

    Example::

        >>> _canonical_refs_value("frame", 1.0)
        1
        >>> _canonical_refs_value("threshold", 1.0)
        1.0
    """
    if key not in _INDEX_REF_KEYS:
        return value
    if isinstance(value, (list, tuple)):
        return tuple(index_value(item, key) for item in value)
    return index_value(value, key)


@dataclass(frozen=True)
class ForcedValue:
    """A variable value the core's non-assumption groups leave no choice about.

    The narrative needs this to explain a value carried across a step.  It cannot
    derive it itself: the transition relation holds one case per outgoing
    transition, and which case fires is a solver question, not a syntactic one.

    :param variable: Model variable name.
    :type variable: str
    :param frame: Frame index the value belongs to.
    :type frame: int
    :param value: The forced value, an ``int`` for an integer variable and a
        ``float`` for a real one, matching the shape the fact recognizer
        publishes so the narrative can compare the two directly.
    :type value: Union[int, float]
    :param supporting_ids: Stable ids of the groups that force it.
    :type supporting_ids: Tuple[str, ...]

    Example::

        >>> ForcedValue("x", 1, 1, ("transition.step.0000",)).value
        1
    """

    variable: str
    frame: int
    value: Union[int, float]
    supporting_ids: Tuple[str, ...]


def derive_forced_values(
    core: "BmcCoreFormula",
    items: Sequence["BmcCoreItem"],
    budget: _SolveBudget,
) -> Tuple[Tuple[ForcedValue, ...], Optional[ProbeRecord]]:
    """Establish which variable values the core's prefix admits no alternative to.

    For each variable an assumption pins, the groups that are *not* assumptions
    are solved on their own.  If they are satisfiable and additionally exclude
    every other value for that frame variable, the prefix forces the one they
    give, and the narrative may say so.  Both facts are checked -- a model value
    alone would only be one witness among possibly many.

    A probe that cannot start, times out or comes back undetermined yields no
    forced value for that variable, so the narrative degrades instead of claiming
    a derivation the solver did not support.

    :param core: The compiled core formula, used for its trace symbols.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param items: The published core members, in stable-id order.
    :type items: Sequence[pyfcstm.bmc.explanation.BmcCoreItem]
    :param budget: Remaining solver budget shared with every other probe.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :return: The forced values, and one aggregate probe record when any probe ran.
    :rtype: Tuple[Tuple[ForcedValue, ...], Optional[ProbeRecord]]

    Example::

        >>> derive_forced_values(None, (), _SolveBudget(None))
        ((), None)
    """
    targets = []
    prefix = []
    for item in items:
        fact = item.normalized_fact
        if item.constraint.stage == "assumptions":
            # Both persistent variable types reach here.  Gating on ``int``
            # excluded every float model from the propagation pattern, which the
            # contract lists without a type qualifier.
            if _readable(item, "variable_comparison") and isinstance(
                fact["value"], (int, float)
            ):
                targets.append((fact["variable"], fact["frame"]))
        else:
            prefix.append(item.constraint.stable_id)
    if not targets or not prefix:
        return (), None
    groups = {group.stable_id: group for group in core._tracked_groups}
    expressions = [
        expression
        for stable_id in prefix
        if stable_id in groups
        for expression in groups[stable_id].expressions
    ]
    if not expressions:
        return (), None
    started = 0
    status = "complete"
    reason = None
    started_at = time.perf_counter()
    derived = []
    # The degradation branches below are deliberately untested.  Which tier a run
    # lands in -- budget spent before the first solve, a solve that timed out, a
    # solver that came back undetermined -- is decided by the host clock and the
    # solver's own search, not by anything a fixture controls; a test pinning one
    # of them fails on a slower machine, which this project has already paid for
    # twice.  The two stable ends are covered: a full budget derives the value,
    # and a prefix that admits several values derives nothing.
    #
    # The unsatisfiable-prefix branch is a different case: it cannot be reached
    # through a proven-minimal core at all, because every member of such a core is
    # load-bearing, so dropping the assumptions has to leave the rest satisfiable.
    # It stays as stated defensive code for the degraded cores that skip that
    # proof.
    for variable, frame in targets:
        symbol = core.symbols.frame_var(frame, variable)
        solver = z3.Solver()
        for expression in expressions:
            solver.add(expression)
        verdict, record = _run_probe(solver, budget, "value_propagation", ())
        if not record.started:
            status, reason = "timeout", "budget exhausted before a prefix solve started"
            break
        started += 1
        if verdict != "sat":
            # An unsatisfiable prefix means the conflict does not need the
            # assumption at all, and an undetermined one supports nothing.
            if verdict != "unsat":
                status, reason = (
                    ("timeout", "prefix solve timed out")
                    if verdict == "timeout"
                    else ("unknown", "prefix solve returned unknown")
                )
            continue
        # The probe reports only a verdict, so the witness is read from the
        # solver it just checked -- still the same assertion set, so the model is
        # the one that verdict belongs to.
        candidate = solver.model().eval(symbol, model_completion=True)
        if isinstance(candidate, z3.IntNumRef):
            value = candidate.as_long()
        elif isinstance(candidate, z3.RatNumRef):
            # A real witness is published as a float, the same shape the fact
            # recognizer uses for a real variable, so the two agree when the
            # narrative compares them.
            try:
                value = float(candidate.as_fraction())
            except OverflowError:
                # OverflowError: the witness does not fit a Python float.  No
                # forced value is derived, so the narrative degrades rather than
                # the explanation failing and taking the verdict with it.
                continue
        else:
            # An algebraic or otherwise unrepresentable witness has no published
            # shape; the narrative degrades rather than rendering an
            # approximation as if it were the value.
            continue
        solver.add(symbol != candidate)
        verdict, record = _run_probe(solver, budget, "value_propagation", ())
        if not record.started:
            status, reason = "timeout", "budget exhausted before the uniqueness check"
            break
        started += 1
        if verdict == "unsat":
            derived.append(ForcedValue(variable, frame, value, tuple(prefix)))
        elif verdict != "sat":
            status, reason = (
                ("timeout", "uniqueness check timed out")
                if verdict == "timeout"
                else ("unknown", "uniqueness check returned unknown")
            )
    if not started:
        return tuple(derived), None
    elapsed_ms = (time.perf_counter() - started_at) * 1000.0
    return tuple(derived), ProbeRecord(
        "value_propagation", status, True, elapsed_ms, reason
    )


def build_core_item(
    group: BmcTrackedConstraint,
    registry: Optional[SourceDocumentRegistry] = None,
    declared: Optional[Sequence[str]] = None,
    state_paths: Optional[Mapping[int, str]] = None,
) -> BmcCoreItem:
    """Turn one tracked source group into a publishable core member.

    The reading is deterministic and structural: the semantic role comes from
    the group's category, the excerpt from the source registry, and the human
    sentence from the same ordered fields.  Nothing here guesses domain
    meaning, so an unrecognized group degrades to its structural facts instead
    of to an invented explanation.

    :param group: Tracked source group selected into the core.
    :type group: pyfcstm.bmc.provenance.BmcTrackedConstraint
    :param registry: Source documents used to quote the authored text,
        defaults to ``None``.
    :type registry: Optional[pyfcstm.bmc.provenance.SourceDocumentRegistry],
        optional
    :param declared: The model's variable names, so a published fact names the
        variable that was declared rather than the encoder's rendering of it.
        Without them the fact falls back to the symbol body, which is correct for
        every name short enough to survive truncation intact.  Defaults to
        ``None``.
    :type declared: Optional[Sequence[str]], optional
    :param state_paths: State code to authored path, so a sentence names the state
        the reader wrote rather than the encoding's number.  Defaults to ``None``.
    :type state_paths: Optional[Mapping[int, str]], optional
    :return: Core member carrying identity, provenance and its reading.
    :rtype: pyfcstm.bmc.explanation.BmcCoreItem
    :raises pyfcstm.bmc.errors.BmcBuildError: If the category has no frozen
        semantic role.

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint
        >>> group = BmcTrackedConstraint(
        ...     "assumption.0000.frame.0000", "assumptions", "assumption.frame",
        ...     (True,), BmcSourceRef("generated", None, None),
        ... )
        >>> build_core_item(group).semantic_role
        'assumption'
    """
    frames = _indices(group.refs, "frame")
    steps = _indices(group.refs, "step")
    summary = "%s group %s" % (group.category, group.stable_id)
    # The index keys are republished in the same canonical form the dedicated
    # fields use.  Reading 1.0 as frame 1 and then echoing 1.0 back under 'frame'
    # would have two published fields disagree about one fact's JSON type, and
    # refs is the mapping machine consumers are told to read.
    published_refs = {
        key: _canonical_refs_value(key, group.refs[key]) for key in sorted(group.refs)
    }
    reference = BmcConstraintRef(
        stable_id=group.stable_id,
        stage=group.stage,
        category=group.category,
        source=group.source_ref,
        summary=summary,
        frames=frames,
        steps=steps,
        refs=published_refs,
    )
    excerpt = None if registry is None else registry.excerpt(group.source_ref)
    truncated = excerpt is not None and len(excerpt) > MAX_SOURCE_EXCERPT_CHARS
    if truncated:
        excerpt = excerpt[:MAX_SOURCE_EXCERPT_CHARS]
    role = _semantic_role(group.category)
    # Machine consumers dispatch on this tag rather than on human text.  The
    # recognizers live in the provenance layer, which owns fact generation; a
    # shape none of them reads keeps its identity under "structural_constraint"
    # instead of inviting a guess.  Frames, steps and refs stay in the constraint
    # reference above: publishing them here as well would give a reader two
    # copies of the same values and blur which keys are the fact itself.
    fact = normalized_fact_for(group, declared)
    return BmcCoreItem(
        constraint=reference,
        semantic_role=role,
        source_excerpt=excerpt,
        source_excerpt_truncated=truncated,
        normalized_fact=fact,
        human_text=human_text_for_fact(role, fact, state_paths),
        editable=group.source_ref.kind in ("fcstm", "fbmcq"),
    )


#: How a proof fact re-encodes as a z3 constraint, per fact tag.
#:
#: Only the tags a rule can read appear here.  A tag with no encoding cannot be
#: proved equivalent to anything, so its member fails the binding check and the
#: proof is not published -- which is the contract's answer for a source group that
#: does not normalize losslessly.
_BINDING_ENCODERS = {
    "variable_equality": lambda fact, symbol: symbol == fact["value"],
    "variable_bound": lambda fact, symbol: {
        "ge": symbol >= fact["value"],
        "gt": symbol > fact["value"],
        "le": symbol <= fact["value"],
        "lt": symbol < fact["value"],
    }[fact["operator"]],
    "definedness_guard": lambda fact, symbol: symbol != fact["forbidden"],
    "state_domain": lambda fact, symbol: z3.Or(
        *[symbol == state for state in fact["states"]]
    ),
    "state_exclusion": lambda fact, symbol: symbol != fact["state"],
}


def check_core_bindings(
    core: "BmcCoreFormula",
    facts: Sequence[Tuple[str, Mapping[str, object]]],
    budget: _SolveBudget,
) -> Tuple[bool, ProbeRecord]:
    """Prove each proof fact equivalent to the source group it restates.

    ``core_binding`` is a claim that an input node says exactly what its member
    says, and the contract is explicit that it is not a trust label: the fact is
    re-encoded and both directions are refuted separately, because one direction
    alone permits a fact that is weaker or stronger than the group it stands for.
    A fact implied by its group but not implying it would let a proof rest on less
    than the model requires; the reverse would let it rest on more.

    Anything short of both directions failing to be refuted -- an unknown, a
    timeout, a tag with no encoding, a group whose symbol cannot be located --
    means the binding is not established and the proof is not published.

    :param core: The core formula whose tracked groups the facts came from.
    :type core: BmcCoreFormula
    :param facts: Member ids paired with the fact each restates.
    :type facts: Sequence[Tuple[str, Mapping[str, object]]]
    :param budget: The shared solve budget.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :return: Whether every binding held, the ledger entry for the phase, and which
        requirement each unit-scoped binding matched, keyed by member id.  A member
        bound against its whole group does not appear in that mapping.
    :rtype: Tuple[bool, ProbeRecord, Dict[str, Tuple[int, int]]]

    Example::

        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> held, record, units = check_core_bindings(None, (), _SolveBudget(None))
        >>> held, record.status, units
        (False, 'unknown', {})
    """
    started_at = time.perf_counter()

    def elapsed() -> float:
        return (time.perf_counter() - started_at) * 1000.0

    if not facts:
        # Nothing was bound, so nothing may rest on a binding.  Reporting this as a
        # completed phase was the previous shape and it was wrong twice over: a
        # consumer reading ``complete`` would believe equivalences were established,
        # and the published ledger refuses a completed check that carries a reason,
        # so a query reaching here raised out of the solve chain instead of
        # degrading.  An unestablished binding is what this is.
        return (
            False,
            ProbeRecord(
                "core_binding",
                "unknown",
                True,
                elapsed(),
                "no core member states a fact this check can encode",
            ),
            {},
        )

    groups = {group.stable_id: group for group in core._tracked_groups}
    # The encoder truncates a symbol's body at a fixed width and appends a digest,
    # so reading a name back from the symbol alone recovers the truncation.  The
    # declared names are what the published facts were resolved against, and the
    # binding has to resolve the same way or a long name stops matching itself.
    declared = _declared_variable_names(core)
    unit_bindings: Dict[str, Tuple[int, int]] = {}
    for stable_id, fact in facts:
        group = groups.get(stable_id)
        kind = fact.get("kind")
        encoder = _BINDING_ENCODERS.get(kind)
        if group is None or (encoder is None and kind not in _UNIT_BOUND_ENCODERS):
            return (
                False,
                ProbeRecord(
                    "core_binding",
                    "unknown",
                    True,
                    elapsed(),
                    "no equivalence check exists for %s" % stable_id,
                ),
                {},
            )
        conjunction = (
            z3.And(*group.expressions) if group.expressions else z3.BoolVal(True)
        )
        if kind in _UNIT_BOUND_ENCODERS:
            # A group holding one requirement per case is a conjunction, and a fact
            # states one of them.  Both directions still have to fail refutation --
            # against that one requirement rather than against the whole group, which
            # the fact could not imply.  Which requirement it was travels with the
            # node so a reader sees the proportion covered rather than being told
            # "the transition relation" and left to find the part that mattered.
            outcome = _bind_against_one_unit(
                _UNIT_BOUND_ENCODERS[kind], fact, conjunction, declared, budget
            )
            if outcome.attribution is None:
                return (
                    False,
                    ProbeRecord(
                        "core_binding",
                        outcome.status,
                        True,
                        elapsed(),
                        "%s for %s" % (outcome.reason, stable_id),
                    ),
                    {},
                )
            unit_bindings[stable_id] = outcome.attribution
            continue
        symbol = _binding_symbol(conjunction, fact, declared)
        if symbol is None:
            return (
                False,
                ProbeRecord(
                    "core_binding",
                    "unknown",
                    True,
                    elapsed(),
                    "the group behind %s names no symbol this fact could restate"
                    % stable_id,
                ),
                {},
            )
        encoded = encoder(fact, symbol)
        for direction, claim in (
            ("group implies fact", z3.And(conjunction, z3.Not(encoded))),
            ("fact implies group", z3.And(encoded, z3.Not(conjunction))),
        ):
            solver = z3.Solver()
            solver.add(claim)
            status, _, reason, _, _ = _check_with_budget(solver, budget)
            if status != "unsat":
                # Three outcomes share one status word and must not share one
                # sentence.  A timeout says raise the budget; an undecidable shape
                # says the solver cannot answer this and retrying will not help; a
                # refutation says the fact and its group genuinely differ, which is
                # a defect on the building side rather than a limit on this one.
                # The frozen phase vocabulary has no word for the last, so the
                # reason carries it.
                explanation = {
                    "sat": "was refuted: the fact is not equivalent to its group",
                    "unknown": "could not be decided by the solver",
                }.get(status, "ran out of budget")
                return (
                    False,
                    ProbeRecord(
                        "core_binding",
                        # The solver's own word, not its negation.  These were swapped
                        # once, so each payload advised the opposite of what it meant.
                        "timeout" if status == "timeout" else "unknown",
                        True,
                        elapsed(),
                        "%s %s for %s%s"
                        % (
                            direction,
                            explanation,
                            stable_id,
                            ": %s" % reason if reason else "",
                        ),
                    ),
                    {},
                )
    return (
        True,
        ProbeRecord("core_binding", "complete", True, elapsed(), None),
        unit_bindings,
    )


def _declared_variable_names(core: "BmcCoreFormula"):
    """Return the variable names the model declares, for symbol resolution.

    Recovering a name from a symbol alone reads back the encoder's truncation; the
    declarations are the full names the published facts were resolved against, so
    the binding resolves the same way.
    """
    domain = getattr(getattr(core, "context", None), "domain", None)
    entries = getattr(domain, "variables", None) or ()
    return tuple(sorted(entry.name for entry in entries))


def _state_names(core: "BmcCoreFormula"):
    """Return what the model calls each state, for the reader-facing prose.

    Facts carry states as the encoding numbers them, which is what the rules compare
    but not what the author wrote.  The path is what the reader-facing surfaces
    already spell a state as -- the core items' human text says ``state Root.A`` --
    so the proof reading uses the same spelling rather than inventing a second one.
    The published facts keep the index: ``normalized_fact`` is the machine's half of
    the contract and is compared, not read.
    """
    domain = getattr(getattr(core, "context", None), "domain", None)
    entries = getattr(domain, "states", None) or ()
    return {entry.id: entry.path for entry in entries}


#: Which published fact kinds bind against one requirement of their group.
#:
#: A group that holds one requirement per case is a conjunction, and a fact states
#: one of them: the fact cannot imply the whole group, so the bidirectional check
#: runs against the requirement instead.  Membership here is what selects that
#: reading, and the encoder beside it is the one that rebuilds the requirement's own
#: shape rather than a single symbol's constraint.
_UNIT_BOUND_ENCODERS = {}  # populated below, after the encoders are defined


class _UnitBindingOutcome:
    """What one unit-scoped binding attempt established, or why it did not.

    :param attribution: ``(unit_index, unit_count)`` when exactly one requirement
        was proved equivalent, otherwise ``None``.
    :type attribution: Optional[Tuple[int, int]]
    :param status: The ledger status to report when nothing was established.
    :type status: str
    :param reason: What fell short, phrased for the ledger.
    :type reason: Optional[str]
    """

    __slots__ = ("attribution", "status", "reason")

    def __init__(self, attribution=None, status="complete", reason=None):
        self.attribution = attribution
        self.status = status
        self.reason = reason


def _bind_against_one_unit(encoder, fact, conjunction, declared, budget):
    """Prove a fact equivalent to exactly one requirement of its group.

    Both directions are refuted against the requirement, exactly as the whole-group
    check does against the group.  Ambiguity is refused rather than resolved: a fact
    equivalent to two requirements identifies neither, and publishing the first would
    make ``unit_index`` a number the reader cannot rely on.

    :param encoder: The re-encoder for this fact kind.
    :type encoder: Callable
    :param fact: The published fact.
    :type fact: Mapping[str, Any]
    :param conjunction: The group's own conjunction.
    :type conjunction: z3.BoolRef
    :param declared: Model variable names for symbol resolution.
    :type declared: Optional[Iterable[str]]
    :param budget: The shared solve budget.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :return: The outcome, carrying the attribution when one was established.
    :rtype: _UnitBindingOutcome
    """
    from .provenance import conjunctive_units

    symbols = _binding_symbols(conjunction, declared)
    encoded = encoder(fact, symbols)
    if encoded is None:
        return _UnitBindingOutcome(
            status="unknown",
            reason="the fact names something its group does not mention",
        )
    units = conjunctive_units(conjunction)
    matched = []
    for index, unit in enumerate(units):
        held = True
        for claim in (
            z3.And(unit, z3.Not(encoded)),
            z3.And(encoded, z3.Not(unit)),
        ):
            solver = z3.Solver()
            solver.add(claim)
            status, _, reason, _, _ = _check_with_budget(solver, budget)
            if status == "timeout":
                return _UnitBindingOutcome(
                    status="timeout",
                    reason="ran out of budget while binding one requirement%s"
                    % (": %s" % reason if reason else ""),
                )
            if status != "unsat":
                held = False
                break
        if held:
            matched.append(index)
    if len(matched) != 1:
        return _UnitBindingOutcome(
            status="unknown",
            reason=(
                "no requirement of the group is equivalent to the fact"
                if not matched
                else "%d requirements of the group are equivalent to the fact"
                % len(matched)
            ),
        )
    return _UnitBindingOutcome(attribution=(matched[0], len(units)))


def _binding_symbols(expression, declared=None) -> Dict[Tuple[int, Any], Any]:
    """Index every frame symbol a group mentions, by frame and subject.

    :func:`_binding_symbol` answers "which symbol is this fact about" for a fact
    that is about one.  A transition case is about several -- the variable before
    the step and after it, the operand when that is a variable, and whichever slots
    its condition names -- so the symbols are indexed once and read by key.

    The key's subject is the declared variable name, or ``None`` for a frame's own
    state slot.  Both come out of the expressions being compared, so the two sides
    of an equivalence talk about the same objects by construction rather than by
    agreeing on how a symbol is spelled.

    :param expression: The group's conjunction.
    :type expression: z3.BoolRef
    :param declared: Model variable names to resolve symbols against, defaults to
        ``None``.
    :type declared: Optional[Iterable[str]], optional
    :return: ``(frame, subject)`` mapped to the symbol, subject ``None`` for a slot.
    :rtype: Dict[Tuple[int, Any], Any]
    """
    indexed: Dict[Tuple[int, Any], Any] = {}
    for symbol in z3.z3util.get_vars(expression):
        frame = _symbol_frame(symbol)
        if frame is None:
            continue
        if str(symbol) == "F_%d_state" % frame:
            indexed[(frame, None)] = symbol
            continue
        name = _frame_variable_name(symbol, declared)
        if name is not None:
            indexed[(frame, name)] = symbol
    return indexed


#: How a condition member re-encodes, keyed by the fact category it arrives as.
#:
#: A condition's members are ordinary facts, so they are encoded by the same
#: reasoning as any other -- but against the symbol table of the group they came
#: from rather than against one symbol, since a condition may name several frames.
def _encode_condition_member(member: Mapping[str, Any], symbols) -> Optional[Any]:
    """Re-encode one member of a case's selection condition.

    :param member: One published condition fact.
    :type member: Mapping[str, Any]
    :param symbols: The group's symbol table from :func:`_binding_symbols`.
    :type symbols: Mapping[Tuple[int, Any], Any]
    :return: The constraint, or ``None`` when the member names nothing the group
        mentions or carries a relation with no encoding.
    :rtype: Optional[Any]
    """
    kind = member.get("kind")
    frame = member.get("frame")
    if not isinstance(frame, int):
        return None
    if kind == "state_membership":
        symbol = symbols.get((frame, None))
        if symbol is None:
            return None
        required = symbol == member.get("state")
        return z3.Not(required) if member.get("excluded") else required
    if kind == "variable_comparison":
        symbol = symbols.get((frame, member.get("variable")))
        if symbol is None:
            return None
        value = member.get("value")
        relation = {
            "eq": lambda: symbol == value,
            "ne": lambda: symbol != value,
            "ge": lambda: symbol >= value,
            "gt": lambda: symbol > value,
            "le": lambda: symbol <= value,
            "lt": lambda: symbol < value,
        }.get(member.get("operator"))
        return None if relation is None else relation()
    return None


def _encode_transition_case(fact: Mapping[str, Any], symbols) -> Optional[Any]:
    """Re-encode a transition case as the conditional assignment it states.

    The shape produced is the one a decomposed step requirement has --
    ``Implies(condition, target == source <op> operand)`` -- because that is what
    the equivalence is checked against.  A fact whose condition or operand names
    something the group does not mention has no re-encoding, and the binding then
    fails rather than comparing against a constraint built from a guess.

    :param fact: The published transition-case fact.
    :type fact: Mapping[str, Any]
    :param symbols: The group's symbol table from :func:`_binding_symbols`.
    :type symbols: Mapping[Tuple[int, Any], Any]
    :return: The constraint, or ``None`` when the fact cannot be re-encoded.
    :rtype: Optional[Any]
    """
    frame, target_frame = fact.get("frame"), fact.get("target_frame")
    variable = fact.get("variable")
    if not isinstance(frame, int) or not isinstance(target_frame, int):
        return None
    source = symbols.get((frame, variable))
    target = symbols.get((target_frame, variable))
    if source is None or target is None:
        return None
    if "operand_variable" in fact:
        operand = symbols.get((frame, fact.get("operand_variable")))
        if operand is None:
            return None
    else:
        operand = fact.get("operand")
        if operand is None:
            return None
    # ``operator`` rather than ``operation``: this check runs on the *rule* fact, the
    # one ``proof_facts_for_core`` produced, and the two vocabularies name this field
    # differently on purpose.  Reading the published name here found nothing and the
    # binding failed with "the fact names something its group does not mention",
    # which points at the symbols rather than at the field it was actually about.
    combine = {
        "add": lambda: source + operand,
        "sub": lambda: source - operand,
        "mul": lambda: source * operand,
        "div": lambda: source / operand,
    }.get(fact.get("operator"))
    if combine is None:
        return None
    members = fact.get("condition") or ()
    encoded_members = [_encode_condition_member(member, symbols) for member in members]
    if not encoded_members or any(part is None for part in encoded_members):
        return None
    return z3.Implies(z3.And(*encoded_members), target == combine())


#: Registered after the encoder it names, so the table cannot reference a
#: function that does not exist yet.
_UNIT_BOUND_ENCODERS["transition_case"] = _encode_transition_case


def _binding_symbol(expression, fact: Mapping[str, object], declared=None):
    """Return the frame symbol a fact is about, taken from its own group.

    Matching by name would depend on how symbols are spelled; taking the symbol out
    of the very expressions being compared means the two sides of the equivalence
    talk about the same object by construction.
    """
    frame = fact.get("frame")
    if frame is None:
        return None
    symbols = sorted(z3.z3util.get_vars(expression), key=lambda item: str(item))
    variable = fact.get("variable")
    if variable is None or fact.get("state_slot"):
        # A state fact speaks about the frame's own state slot rather than about a
        # declared variable, so it is matched by position in the encoding rather
        # than by a name the query wrote.  A positive requirement carries the slot's
        # subject name so the rules can compare it; an exclusion carries none.  Both
        # mean the same symbol.
        #
        # Which branch a fact takes is decided by its ``state_slot`` flag, never by
        # its subject's spelling.  Two arguments for why that spelling could not
        # also be a declared name were both wrong -- ``state`` is a keyword only in
        # the lexer's default mode, and the target-template rule admits ``$`` -- so
        # a model may well declare a variable named the same.  Its requirements
        # carry no flag and reach the declared branch below, as they should.
        for symbol in symbols:
            if str(symbol) == "F_%d_state" % frame:
                return symbol
        return None
    for symbol in symbols:
        if _symbol_frame(symbol) != frame:
            continue
        if _frame_variable_name(symbol, declared) == variable:
            return symbol
    return None


def _symbol_frame(symbol) -> Optional[int]:
    """Return the frame a ``F_<frame>_...`` symbol belongs to.

    The frame is the only part of the name that survives the encoding intact -- the
    body is truncated and the digest is a hash -- so it is read positionally rather
    than by parsing the whole name.
    """
    parts = str(symbol).split("_")
    if len(parts) < 2 or parts[0] != "F":
        return None
    try:
        return int(parts[1])
    except ValueError:
        # A symbol whose second segment is not a frame index is not a frame symbol.
        return None


def explain_infeasibility(
    core: "BmcCoreFormula",
    stage: str,
    budget: _SolveBudget,
    requested_mode: str = "formal",
    registry: Optional[SourceDocumentRegistry] = None,
) -> ExplanationOutcome:
    """Classify a localized stage and publish the strongest honest artifact.

    This is the single entry point that turns solver work into public data.
    It classifies first, then spends whatever budget is left on a source core,
    and reports exactly what it managed to deliver: a classification without a
    core still ships as ``partial``, and a classification that never completed
    degrades to the stage fallback rather than to a guess.

    :param core: Core formula carrying the tracked group ledger.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param stage: Localized infeasible stage.
    :type stage: str
    :param budget: Budget shared with the mandatory solve.
    :type budget: pyfcstm.bmc.solver._SolveBudget
    :param requested_mode: Explanation depth the caller asked for, defaults to
        ``'formal'``.
    :type requested_mode: str, optional
    :param registry: Source documents used to quote authored text.  Defaults
        to ``None``, which reuses the registry the prepared context already
        built, so a core quotes real FCSTM/FBMCQ text without the caller
        having to supply it.
    :type registry: Optional[pyfcstm.bmc.provenance.SourceDocumentRegistry],
        optional
    :return: Public explanation plus the probe ledger that produced it.
    :rtype: ExplanationOutcome
    :raises pyfcstm.bmc.errors.BmcBuildError: If the stage is unsupported or
        the tracked group partition no longer matches the builder output.

    Example::

        >>> from pyfcstm.bmc import build_bmc_core_formula
        >>> from pyfcstm.bmc.engine import BmcEngine
        >>> from pyfcstm.bmc.solver import _SolveBudget
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> machine = load_state_machine_from_text("state Root;")
        >>> context = BmcEngine(machine).prepare(
        ...     'check reach <= 1: active("Root");'
        ... )
        >>> outcome = explain_infeasibility(
        ...     build_bmc_core_formula(context), "kernel", _SolveBudget(None),
        ... )
        >>> outcome.explanation.classification
        'kernel_conflict'
    """
    started = time.monotonic()
    if registry is None:
        # Read the field directly rather than through getattr: the prepared
        # context always builds a registry, so a rename must surface as an
        # AttributeError instead of silently blanking every excerpt.
        registry = core.context._source_registry
    # The declared names let a published fact name the variable the author wrote
    # rather than the encoder's truncation of it.
    declared = tuple(core.context.model.defines)
    # The domain's own table, so a sentence can name ``Root.A`` instead of the
    # number the encoding gave it.
    state_paths = {
        entry["id"]: entry["path"]
        for entry in core.context.domain.to_canonical()["states"]
    }
    outcome = classify_infeasibility(core, stage, budget)
    # An unclassified stage still has a target the mandatory solve already
    # proved unsatisfiable, so the remaining budget goes into a fallback core
    # rather than being left unspent.  Giving up here would withhold the source
    # lines purely because the *shape* of the conflict stayed undetermined.
    try:
        extraction = extract_source_core(core, outcome.scope, budget)
    except BmcBuildError as err:
        # Kept as stated defensive code, and unreachable through any public path:
        # extraction fails closed on corrupt group metadata, which the builder
        # does not produce.  If it ever did, the classification probes would have
        # spent the caller's deadline already, and letting the error leave this
        # function would drop their records -- the same denial of executed work the
        # guards inside extraction avoid.  That is why it degrades rather than
        # propagates.
        return ExplanationOutcome(
            BmcInfeasibilityExplanation(
                requested_mode=requested_mode,
                achieved_mode="none",
                status="partial" if outcome.classification is not None else "unknown",
                classification=outcome.classification,
                reason="internal mismatch while extracting the core: %s" % err,
                elapsed_ms=(time.monotonic() - started) * 1000.0,
            ),
            outcome.checks,
        )
    elapsed_ms = (time.monotonic() - started) * 1000.0
    checks = outcome.checks + extraction.checks
    if outcome.classification is None and not extraction.groups:
        # Nothing usable came back, so the aggregate summarizes every stage
        # that failed rather than only the first.  A spent deadline outranks an
        # undecided solver: reporting 'unknown' when the budget actually ran
        # out sends the reader looking for solver incompleteness instead of
        # raising their timeout.
        statuses = [outcome.status, extraction.status]
        reasons = [entry for entry in (outcome.reason, extraction.reason) if entry]
        return ExplanationOutcome(
            BmcInfeasibilityExplanation(
                requested_mode=requested_mode,
                achieved_mode="none",
                status="timeout" if "timeout" in statuses else outcome.status,
                classification=None,
                reason="; ".join(reasons) or outcome.reason,
                elapsed_ms=elapsed_ms,
            ),
            checks,
        )
    if not extraction.groups:
        # The classification is sound on its own, so it is still published;
        # only the core slot degrades.  Dropping it here would throw away the
        # answer the caller actually asked for.
        #
        # The status is 'partial' rather than the extraction's own status: a
        # usable classification means part of the request was delivered, and
        # the frozen truth table reserves 'unknown'/'timeout' for the case
        # where nothing at all could be established.
        return ExplanationOutcome(
            BmcInfeasibilityExplanation(
                requested_mode=requested_mode,
                achieved_mode="none",
                status="partial",
                classification=outcome.classification,
                reason=extraction.reason,
                elapsed_ms=elapsed_ms,
            ),
            checks,
        )

    minimized = minimize_source_core(core, extraction, budget)
    if minimized.record is not None:
        # One aggregate phase record, not one per deletion trial: the ledger
        # names decisions a reader can act on, and trial count is an artifact of
        # the core's size.
        checks = checks + (minimized.record,)
    elapsed_ms = (time.monotonic() - started) * 1000.0
    try:
        published = BmcConflictCore(
            scope=outcome.scope,
            formula_summary="target formula of scope %s" % outcome.scope,
            granularity="source_group",
            # Shrink only ever deletes, so whatever it returns is still sound;
            # these two fields say how far the deletion pass actually got.
            reduction=minimized.reduction,
            subset_minimality=minimized.subset_minimality,
            items=tuple(
                build_core_item(group, registry, declared, state_paths)
                for group in minimized.groups
            ),
        )
    except (BmcBuildError, ValueError, TypeError) as err:
        # BmcBuildError: this module found builder-side drift while mapping.
        # ValueError / TypeError: a public constructor in the data layer refused
        # the mapped payload, for example because a group's stage and category
        # place it outside the scope being published.
        #
        # All three mean the artifact cannot be published.  None of them may
        # take the mandatory verdict with it, and the ledger stays: solver work
        # already happened, so reverting to "nothing was requested" would hide
        # checks that ran.
        return ExplanationOutcome(
            BmcInfeasibilityExplanation(
                requested_mode=requested_mode,
                achieved_mode="none",
                status=(
                    # A surviving classification is usable metadata, which the
                    # frozen table calls partial.  With nothing left to report
                    # the same table asks for unknown instead.
                    "partial" if outcome.classification is not None else "unknown"
                ),
                classification=outcome.classification,
                reason="core mapping failed after the solver work: %s" % err,
                elapsed_ms=elapsed_ms,
            ),
            checks,
        )
    # The probe runs on the published members, so it can only ever support a
    # derivation about groups the reader was shown.
    forced_values, propagation_record = derive_forced_values(
        core, published.items, budget
    )
    if propagation_record is not None:
        checks = checks + (propagation_record,)
    narrative = build_conflict_narrative(published, forced_values, state_paths)
    formal_is_complete = (
        outcome.classification is not None
        and minimized.subset_minimality == "proven"
        and narrative.derivation_status == "complete"
    )
    if formal_is_complete and requested_mode == "formal":
        # Every condition the frozen table names for a complete formal artifact
        # holds: a diagnostic classification, a proven-minimal core and a closed
        # derivation.  Such an explanation carries no reason, because nothing
        # about it was degraded.
        return ExplanationOutcome(
            BmcInfeasibilityExplanation(
                requested_mode=requested_mode,
                achieved_mode="formal",
                status="complete",
                classification=outcome.classification,
                core=published,
                narrative=narrative,
                elapsed_ms=elapsed_ms,
            ),
            checks,
        )
    if formal_is_complete:
        # A complete formal artifact is what a proof is built on top of, so this is
        # where the deeper tier is attempted.  Either it closes and the run reaches
        # the depth that was asked for, or it does not and the formal artifact is
        # published unchanged with a reason naming what fell short.
        from .proof import build_domain_proof, proof_facts_for_core
        from .proof_text import linearize_proof

        proof_facts = proof_facts_for_core(published.items)
        # The binding check comes first: a graph built on facts that were never
        # shown equivalent to their members would carry ``core_binding`` as a trust
        # label, which the contract forbids outright.
        bound, binding_record, unit_bindings = check_core_bindings(
            core, proof_facts, budget
        )
        checks = checks + (binding_record,)
        if bound:
            # One table for both artifacts: a node's own sentence and the reading
            # built from it are two spellings of the same state to the same reader.
            state_names = _state_names(core)
            proof, proof_record = build_domain_proof(
                published.scope,
                proof_facts,
                budget,
                member_ids=[item.constraint.stable_id for item in published.items],
                state_names=state_names,
            )
            checks = checks + (proof_record,)
        else:
            proof, proof_record = None, binding_record
        if proof is not None:
            # The narrative is rebuilt from the graph rather than kept from the
            # formal tier: at proof depth every sentence has to cite the node behind
            # it, which a narrative written without a graph cannot do.
            steps = linearize_proof(
                proof,
                state_names=state_names,
                core_categories=[item.constraint.category for item in published.items],
            )
            proof_narrative = BmcConflictNarrative(
                "complete",
                steps[-1].text,
                narrative.summary,
                steps,
                narrative.review_surfaces,
            )
            return ExplanationOutcome(
                BmcInfeasibilityExplanation(
                    requested_mode=requested_mode,
                    achieved_mode="proof",
                    status="complete",
                    classification=outcome.classification,
                    core=published,
                    proof=proof,
                    narrative=proof_narrative,
                    elapsed_ms=elapsed_ms,
                ),
                checks,
            )
        # The frozen table reserves 'complete' for the depth that was asked for, and
        # the reason has to name why the proof did not close rather than describe the
        # formal artifact, which is not what fell short.
        return ExplanationOutcome(
            BmcInfeasibilityExplanation(
                requested_mode=requested_mode,
                achieved_mode="formal",
                status="partial",
                classification=outcome.classification,
                core=published,
                narrative=narrative,
                reason=(
                    "the formal explanation is complete, but %s"
                    % (proof_record.reason or "no verifiable proof DAG was produced")
                ),
                elapsed_ms=elapsed_ms,
            ),
            checks,
        )
    if outcome.classification is None:
        reason = (
            "classification degraded to the %s scope (%s); the published core "
            "is sound but not proven minimal" % (outcome.scope, outcome.reason)
        )
    elif minimized.subset_minimality != "proven":
        # Name the deletion pass that stopped early rather than the missing
        # narrative: an unproven core is the weaker of the two shortfalls, and
        # reporting the stronger one first would send the reader to the wrong
        # remedy.
        reason = "sound source core published without a minimality proof (%s)" % (
            minimized.reason or minimized.status
        )
    else:
        # The core is proven minimal and the classification finished, so the
        # shortfall is the derivation: the recognizers read no pattern that closes
        # the chain, which the narrative already reports as structural_only.
        reason = (
            "subset-minimal source core published with a %s derivation"
            % narrative.derivation_status
        )
    return ExplanationOutcome(
        BmcInfeasibilityExplanation(
            requested_mode=requested_mode,
            achieved_mode="formal",
            status="partial",
            classification=outcome.classification,
            core=published,
            narrative=narrative,
            reason=reason,
            elapsed_ms=elapsed_ms,
        ),
        checks,
    )


__all__ = [
    "AGGREGATE_SELECTORS",
    "ClassificationOutcome",
    "CoreExtraction",
    "ExplanationOutcome",
    "ForcedValue",
    "ProbeRecord",
    "SCOPE_TARGETS",
    "TrackedGroupPartition",
    "build_core_item",
    "check_core_bindings",
    "classify_infeasibility",
    "derive_forced_values",
    "explain_infeasibility",
    "extract_source_core",
    "partition_tracked_groups",
]

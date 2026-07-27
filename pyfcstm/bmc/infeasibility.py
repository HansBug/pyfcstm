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
from typing import TYPE_CHECKING, Callable, Dict, Mapping, Optional, Sequence, Tuple

import z3

from .errors import BmcBuildError
from .explanation import (
    CLASSIFICATION_SCOPES,
    MAX_SOURCE_EXCERPT_CHARS,
    BmcConflictCore,
    BmcConstraintRef,
    BmcCoreItem,
    BmcInfeasibilityExplanation,
)
from .provenance import BmcTrackedConstraint, SourceDocumentRegistry
from .solver import _SolveBudget

if TYPE_CHECKING:  # pragma: no cover - import cycle guard for annotations only
    from .relation import BmcCoreFormula

#: Category prefix to frozen semantic role.  The relation builder names every
#: group after the domain concept it encodes, so the prefix already carries the
#: role and no guessing is needed.
_SEMANTIC_ROLE_BY_PREFIX = (
    ("domain.", "domain_rule"),
    ("initial.", "initial_fact"),
    ("transition.", "transition_rule"),
    ("assumption.", "assumption"),
    ("definedness", "definedness"),
)


def _is_domain_group(group: BmcTrackedConstraint) -> bool:
    """Report whether a kernel group belongs to the domain aggregate.

    :param group: Tracked source group to classify.
    :type group: pyfcstm.bmc.provenance.BmcTrackedConstraint
    :return: ``True`` when the group is part of ``D_N``.
    :rtype: bool

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint
        >>> group = BmcTrackedConstraint(
        ...     "domain.frame.0000.state", "kernel", "domain.frame_state",
        ...     (True,), BmcSourceRef("generated", None, None),
        ... )
        >>> _is_domain_group(group)
        True
    """
    return group.stage == "kernel" and group.category.startswith("domain")


def _is_transition_group(group: BmcTrackedConstraint) -> bool:
    """Report whether a kernel group belongs to the transition aggregate.

    :param group: Tracked source group to classify.
    :type group: pyfcstm.bmc.provenance.BmcTrackedConstraint
    :return: ``True`` when the group is part of ``T_N``.
    :rtype: bool

    Example::

        >>> from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint
        >>> group = BmcTrackedConstraint(
        ...     "transition.step.0000", "kernel", "transition.step", (True,),
        ...     BmcSourceRef("generated", None, None),
        ... )
        >>> _is_transition_group(group)
        True
    """
    return group.stage == "kernel" and group.category.startswith("transition")


#: Predicate per aggregate; the kernel stage covers both domain and transition.
AGGREGATE_SELECTORS: "Mapping[str, Callable[[BmcTrackedConstraint], bool]]" = (
    MappingProxyType(
        {
            "domain": _is_domain_group,
            "transition": _is_transition_group,
            "initial": lambda group: group.stage == "initialization",
            "environment": lambda group: group.stage == "assumptions",
        }
    )
)

#: Aggregates that make up the target formula of every published scope.
SCOPE_TARGETS: "Mapping[str, Tuple[str, ...]]" = MappingProxyType(
    {
        "kernel": ("domain", "transition"),
        "initialization_component": ("initial",),
        "initialization_domain": ("domain", "initial"),
        "initialization_prefix": ("domain", "transition", "initial"),
        "assumptions_component": ("environment",),
        "assumptions_domain": ("domain", "environment"),
        "assumptions_prefix": ("domain", "transition", "initial", "environment"),
        "initialization_stage_fallback": ("domain", "transition", "initial"),
        "assumptions_stage_fallback": (
            "domain",
            "transition",
            "initial",
            "environment",
        ),
    }
)

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
            raise BmcBuildError(
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
            raise BmcBuildError(
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
            "component probe returned %s" % status,
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
            "domain probe returned %s" % status,
            tuple(checks),
        )
    if status == "unsat":
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
            raise BmcBuildError(
                "two tracked groups share the stable id %r." % group.stable_id
            )
        label = z3.Bool(label_name)
        by_label[label_name] = group
        labels.append(label)
        solver.add(z3.Implies(label, _conjunction((group,))))

    status, record = _run_probe(solver, budget, "unsat_core", labels)
    if status in ("unknown", "timeout"):
        return CoreExtraction(
            (), status, "core extraction returned %s" % status, (record,)
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
            # normally fire; it turns a hypothetical solver-contract violation
            # into a named error instead of an obscure crash further down.
            raise BmcBuildError(
                "unsat core returned unknown activation label %r." % name
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
    # shares the caller's budget and is recorded rather than run unbounded.
    recheck, verify_record = _run_probe(verifier, budget, "unsat_core", ())
    checks = (record, verify_record)
    if recheck != "unsat":
        return CoreExtraction(
            (),
            "unknown" if recheck != "timeout" else "timeout",
            "extracted core for scope %r did not re-check as unsat (%s)"
            % (scope, recheck),
            checks,
        )
    return CoreExtraction(ordered, "complete", None, checks)


def _semantic_role(category: str) -> str:
    """Map a tracked group category onto its frozen semantic role.

    :param category: Group category assigned by the relation builder.
    :type category: str
    :return: One of the frozen semantic roles.
    :rtype: str
    :raises pyfcstm.bmc.errors.BmcBuildError: If the category matches no known
        prefix, which means a new group family was added without deciding how
        a reader should understand it.

    Example::

        >>> _semantic_role("assumption.frame")
        'assumption'
    """
    for prefix, role in _SEMANTIC_ROLE_BY_PREFIX:
        if category.startswith(prefix):
            return role
    raise BmcBuildError("tracked group category %r has no semantic role." % category)


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

    def _usable(value: object) -> bool:
        return isinstance(value, int) and not isinstance(value, bool) and value >= 0

    found = []
    for name in (key, "%ss" % key):
        value = refs.get(name)
        if _usable(value):
            found.append(value)
        elif isinstance(value, (list, tuple)):
            found.extend(item for item in value if _usable(item))
    return tuple(sorted(set(found)))


def build_core_item(
    group: BmcTrackedConstraint,
    registry: Optional[SourceDocumentRegistry] = None,
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
    reference = BmcConstraintRef(
        stable_id=group.stable_id,
        stage=group.stage,
        category=group.category,
        source=group.source_ref,
        summary=summary,
        frames=frames,
        steps=steps,
        refs={key: group.refs[key] for key in sorted(group.refs)},
    )
    excerpt = None if registry is None else registry.excerpt(group.source_ref)
    truncated = excerpt is not None and len(excerpt) > MAX_SOURCE_EXCERPT_CHARS
    if truncated:
        excerpt = excerpt[:MAX_SOURCE_EXCERPT_CHARS]
    location = group.source_ref.path or group.source_ref.kind
    human_text = "%s constraint %s from %s" % (
        _semantic_role(group.category).replace("_", " "),
        group.stable_id,
        location,
    )
    return BmcCoreItem(
        constraint=reference,
        semantic_role=_semantic_role(group.category),
        source_excerpt=excerpt,
        source_excerpt_truncated=truncated,
        normalized_fact={
            # Machine consumers dispatch on this tag rather than on human
            # text.  No semantic recognizer runs at this stage, so every fact
            # honestly declares itself structural instead of guessing a
            # domain reading.
            "kind": "structural_constraint",
            "stable_id": group.stable_id,
            "stage": group.stage,
            "category": group.category,
            "frames": list(frames),
            "steps": list(steps),
            # The builder's own metadata is carried through in sorted order so
            # a machine reader sees which assumption, transition or variable
            # the conflict came from, not only its frame index.
            "refs": {key: group.refs[key] for key in sorted(group.refs)},
        },
        human_text=human_text,
        editable=group.source_ref.kind in ("fcstm", "fbmcq"),
    )


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
    outcome = classify_infeasibility(core, stage, budget)
    # An unclassified stage still has a target the mandatory solve already
    # proved unsatisfiable, so the remaining budget goes into a fallback core
    # rather than being left unspent.  Giving up here would withhold the source
    # lines purely because the *shape* of the conflict stayed undetermined.
    extraction = extract_source_core(core, outcome.scope, budget)
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

    published = BmcConflictCore(
        scope=outcome.scope,
        formula_summary="target formula of scope %s" % outcome.scope,
        granularity="source_group",
        # No deletion check has run yet, so the core is sound but not claimed
        # minimal; PR-level minimization upgrades both fields together.
        reduction="raw",
        subset_minimality="not_proven",
        items=tuple(build_core_item(group, registry) for group in extraction.groups),
    )
    if outcome.classification is None:
        reason = (
            "classification degraded to the %s scope (%s); the published core "
            "is sound but not proven minimal" % (outcome.scope, outcome.reason)
        )
    else:
        reason = "sound source core published without a minimality proof"
    return ExplanationOutcome(
        BmcInfeasibilityExplanation(
            requested_mode=requested_mode,
            achieved_mode="formal",
            status="partial",
            classification=outcome.classification,
            core=published,
            reason=reason,
            elapsed_ms=elapsed_ms,
        ),
        checks,
    )


__all__ = [
    "AGGREGATE_SELECTORS",
    "SCOPE_TARGETS",
    "ClassificationOutcome",
    "CoreExtraction",
    "ExplanationOutcome",
    "ProbeRecord",
    "TrackedGroupPartition",
    "build_core_item",
    "classify_infeasibility",
    "explain_infeasibility",
    "extract_source_core",
    "partition_tracked_groups",
]

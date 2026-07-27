"""TDD contracts for infeasibility classification and sound source cores.

Every case here drives the public preparation and relation builders with real
FCSTM and FBMCQ text, so the probes and cores under test run against the same
formulas a user would get.
"""

from __future__ import annotations

from dataclasses import replace

import z3
import pytest
from z3.z3util import get_vars

from pyfcstm.bmc import build_bmc_core_formula, compile_bmc_property
from pyfcstm.bmc.engine import BmcEngine
from pyfcstm.bmc.errors import BmcBuildError
from pyfcstm.bmc.explanation import (
    CLASSIFICATION_SCOPES,
    STAGE_FALLBACK_SCOPES,
    _SCOPE_STAGES,
)
from pyfcstm.bmc.infeasibility import (
    AGGREGATE_SELECTORS,
    MAX_SOURCE_EXCERPT_CHARS,
    SCOPE_TARGETS,
    _activation_solver,
    _indices,
    _semantic_role,
    build_core_item,
    classify_infeasibility,
    explain_infeasibility,
    extract_source_core,
    partition_tracked_groups,
)
from pyfcstm.bmc.provenance import (
    BmcSourceRef,
    BmcTrackedConstraint,
    SourceDocumentRegistry,
)
from pyfcstm.bmc.solver import _SolveBudget
from pyfcstm.bmc.witness import solve_bmc_property
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.utils.validate import Span

pytestmark = pytest.mark.unittest

_MODEL = """def int x = 0;
state Root {
    event Go;
    state A;
    state B;
    [*] -> A;
    A -> B :: Go;
}"""


def _core_formula(query: str, model_text: str = _MODEL):
    machine = load_state_machine_from_text(model_text)
    context = BmcEngine(machine).prepare(query)
    return build_bmc_core_formula(context)


def test_partition_reproduces_every_aggregate_formula() -> None:
    """The selector partition is asserted, never assumed.

    The authoritative grouping lives in the relation builder's registration
    order, which is not persisted.  Rebuilding each aggregate from the
    partition and comparing S-expressions keeps this module honest if that
    order ever changes.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume event("Root.Go", 0) == true; '
        'check reach <= 2: active("Root.B");'
    )
    partition = partition_tracked_groups(core)

    rebuilt = {
        "domain": partition.domain,
        "initial": partition.initial,
        "transition": partition.transition,
        "environment": partition.environment,
    }
    expected = {
        "domain": core.domain_formula,
        "initial": core.initial_formula,
        "transition": core.transition_formula,
        "environment": core.environment_formula,
    }
    for name, groups in rebuilt.items():
        exprs = [item for group in groups for item in group.expressions]
        combined = exprs[0] if len(exprs) == 1 else z3.And(*exprs)
        assert combined.sexpr() == expected[name].sexpr(), name


def test_partition_never_includes_case_groups() -> None:
    """Case provenance describes cases, not canonical transition conjuncts."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    partition = partition_tracked_groups(core)

    selected = {
        group.stable_id
        for groups in (
            partition.domain,
            partition.initial,
            partition.transition,
            partition.environment,
        )
        for group in groups
    }
    case_ids = {group.stable_id for group in core._tracked_case_groups}

    assert case_ids
    assert selected.isdisjoint(case_ids)


def test_every_scope_has_a_frozen_target() -> None:
    """All seven diagnostic scopes and both fallbacks resolve to a target."""
    assert set(SCOPE_TARGETS) == set(CLASSIFICATION_SCOPES.values()) | set(
        STAGE_FALLBACK_SCOPES
    )
    assert set(AGGREGATE_SELECTORS) == {
        "domain",
        "initial",
        "transition",
        "environment",
    }


@pytest.mark.parametrize(
    "query, stage, expected",
    [
        (
            'init state("Root.A") where x == 1 && x == 2; '
            'check reach <= 2: active("Root.B");',
            "initialization",
            "initialization_self_conflict",
        ),
        (
            'init state("Root.A") where x == 0; '
            'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
            'check reach <= 2: active("Root.B");',
            "assumptions",
            "assumptions_self_conflict",
        ),
        (
            'init state("Root.A") where x == 0; '
            'assume at 0: var("x") == 7; '
            'check reach <= 2: active("Root.B");',
            "assumptions",
            "assumptions_prefix_conflict",
        ),
    ],
)
def test_classification_on_real_queries(query, stage, expected) -> None:
    """Real FCSTM and FBMCQ text drives the classification probes."""
    core = _core_formula(query)
    outcome = classify_infeasibility(core, stage, _SolveBudget(None))

    assert outcome.classification == expected
    assert outcome.scope == CLASSIFICATION_SCOPES[expected]


def test_kernel_stage_needs_no_probe() -> None:
    """The kernel stage is classified without spending a solver check."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    outcome = classify_infeasibility(core, "kernel", _SolveBudget(None))

    assert outcome.classification == "kernel_conflict"
    assert outcome.scope == "kernel"
    assert outcome.checks == ()


def test_exhausted_budget_stops_before_any_probe() -> None:
    """A spent budget yields a timeout outcome instead of a forced check."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 7; '
        'check reach <= 2: active("Root.B");'
    )
    budget = _SolveBudget(1)
    budget.deadline = budget.deadline - 10.0

    outcome = classify_infeasibility(core, "assumptions", budget)

    assert outcome.classification is None
    assert outcome.status == "timeout"
    assert outcome.scope == "assumptions_stage_fallback"
    assert all(not check.started for check in outcome.checks)


def test_source_core_members_recheck_as_unsat() -> None:
    """A published core must independently prove its target unsatisfiable."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    outcome = classify_infeasibility(core, "assumptions", _SolveBudget(None))
    extraction = extract_source_core(core, outcome.scope, _SolveBudget(None))

    assert extraction.groups
    solver = z3.Solver()
    for group in extraction.groups:
        for expression in group.expressions:
            solver.add(expression)
    assert solver.check() == z3.unsat


def test_source_core_stays_inside_its_scope() -> None:
    """Core members never escape the group set the scope selected."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    partition = partition_tracked_groups(core)
    outcome = classify_infeasibility(core, "assumptions", _SolveBudget(None))
    extraction = extract_source_core(core, outcome.scope, _SolveBudget(None))

    allowed = {
        group.stable_id
        for name in SCOPE_TARGETS[outcome.scope]
        for group in getattr(partition, name)
    }
    selected = {group.stable_id for group in extraction.groups}

    assert selected
    assert selected <= allowed


def test_self_conflict_core_is_not_widened_to_the_prefix() -> None:
    """An assumptions self-conflict keeps the narrow component scope."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    outcome = classify_infeasibility(core, "assumptions", _SolveBudget(None))

    assert outcome.scope == "assumptions_component"
    assert outcome.scope != "assumptions_prefix"


def test_core_extraction_is_deterministic() -> None:
    """Repeated extraction yields the same ordered stable-id tuple."""
    query = (
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    runs = []
    for _ in range(3):
        core = _core_formula(query)
        outcome = classify_infeasibility(core, "assumptions", _SolveBudget(None))
        extraction = extract_source_core(core, outcome.scope, _SolveBudget(None))
        runs.append(tuple(sorted(g.stable_id for g in extraction.groups)))

    assert len(set(runs)) == 1


def _contains(expression, needle) -> bool:
    """Report whether ``needle`` occurs anywhere in an expression tree.

    Identity is decided with Z3's structural equality rather than rendered
    text, so a check cannot pass merely because the property kind happens not
    to appear as a token.
    """
    if expression.eq(needle):
        return True
    return any(_contains(child, needle) for child in expression.children())


def test_objective_formula_never_enters_the_refinement_solver() -> None:
    """The property objective stays out of every scenario core check.

    The objective is compared by AST identity against every assertion the
    refinement solver holds and against every published core expression.  A
    string search would be vacuous: ``reach`` is a query keyword, not a Z3
    symbol, so it never appears in the encoded formula either way.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    objective = compile_bmc_property(core).objective_formula
    partition = partition_tracked_groups(core)
    solver, literals = _activation_solver(partition)

    assertions = list(solver.assertions())
    assert len(assertions) == len(literals)
    assert not any(_contains(item, objective) for item in assertions)

    outcome = classify_infeasibility(core, "assumptions", _SolveBudget(None))
    extraction = extract_source_core(core, outcome.scope, _SolveBudget(None))
    published = [
        expression for group in extraction.groups for expression in group.expressions
    ]

    assert published
    assert not any(_contains(item, objective) for item in published)


def test_a_planted_objective_is_detected_by_the_guard() -> None:
    """The objective guard fails when an objective really does leak in.

    Without this, the guard above could silently become vacuous again: it must
    be shown to reject the very situation it claims to exclude.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; '
        'check reach <= 2: active("Root.B");'
    )
    objective = compile_bmc_property(core).objective_formula

    assert _contains(z3.And(objective, z3.BoolVal(True)), objective)


def test_unknown_scope_is_rejected_by_every_entry_point() -> None:
    """A scope outside the frozen nine never silently selects nothing."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    partition = partition_tracked_groups(core)

    for call in (
        lambda: partition.groups_for("bogus_scope"),
        lambda: extract_source_core(core, "bogus_scope", _SolveBudget(None)),
    ):
        with pytest.raises(BmcBuildError, match="Unsupported conflict core scope"):
            call()


def test_unknown_stage_is_rejected() -> None:
    """Only the three localized stages can be classified."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    with pytest.raises(BmcBuildError, match="Unsupported infeasible stage"):
        classify_infeasibility(core, "bogus_stage", _SolveBudget(None))


def test_partition_rejects_a_group_with_no_aggregate() -> None:
    """A new group family must be assigned an aggregate, not silently dropped."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    displaced = replace(core._tracked_groups[0], stage="mystery")
    tampered = replace(
        core, _tracked_groups=(displaced,) + tuple(core._tracked_groups[1:])
    )

    with pytest.raises(BmcBuildError, match="no aggregate selector"):
        partition_tracked_groups(tampered)


def test_partition_rejects_a_rebuilt_aggregate_that_drifted() -> None:
    """The rebuilt aggregate is compared, not trusted."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    initial = [g for g in core._tracked_groups if g.stage == "initialization"]
    moved = replace(initial[0], stage="assumptions", category="assumption.frame")
    tampered = replace(
        core,
        _tracked_groups=tuple(
            moved if g.stable_id == moved.stable_id else g for g in core._tracked_groups
        ),
    )

    with pytest.raises(BmcBuildError, match="does not match the relation builder"):
        partition_tracked_groups(tampered)


def test_a_live_budget_sets_a_solver_timeout() -> None:
    """Every probe runs under the caller's remaining deadline, not unbounded."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    seen = []
    original = z3.Solver.set

    def record(self, *args, **kwargs):
        seen.append(kwargs.get("timeout"))
        return original(self, *args, **kwargs)

    z3.Solver.set = record
    try:
        outcome = classify_infeasibility(core, "assumptions", _SolveBudget(60_000))
    finally:
        z3.Solver.set = original

    assert outcome.classification == "assumptions_self_conflict"
    assert seen
    assert all(isinstance(value, int) and value > 0 for value in seen)


def test_no_budget_leaves_the_solver_timeout_unset() -> None:
    """``timeout_ms=None`` must not impose a hidden deadline."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    seen = []
    original = z3.Solver.set

    def record(self, *args, **kwargs):
        seen.append(kwargs.get("timeout"))
        return original(self, *args, **kwargs)

    z3.Solver.set = record
    try:
        classify_infeasibility(core, "assumptions", _SolveBudget(None))
    finally:
        z3.Solver.set = original

    assert seen == []


def test_exhausted_budget_stops_before_the_core_recheck() -> None:
    """The final soundness recheck is budgeted like every other probe."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )

    class OneShotBudget:
        """Grants exactly one probe, then reports the deadline as spent."""

        deadline = 1.0

        def __init__(self):
            self.calls = 0

        def remaining_ms(self):
            self.calls += 1
            return 60_000 if self.calls == 1 else None

    budget = OneShotBudget()
    extraction = extract_source_core(core, "assumptions_component", budget)

    assert budget.calls == 2
    assert extraction.groups == ()
    assert extraction.status == "timeout"
    assert "did not re-check as unsat" in extraction.reason
    assert [check.started for check in extraction.checks] == [True, False]


def test_a_scope_with_no_target_group_degrades_instead_of_publishing() -> None:
    """An empty target cannot prove anything, so nothing is published.

    A query without assumptions has no environment group at all, so asking for
    the assumptions component scope selects nothing.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    extraction = extract_source_core(core, "assumptions_component", _SolveBudget(None))

    assert extraction.groups == ()
    assert extraction.status == "unknown"
    assert "selected no source group" in extraction.reason


def test_a_satisfiable_target_is_reported_as_an_internal_mismatch() -> None:
    """A SAT target means the scope disagrees with the localized stage."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 0; '
        'check reach <= 2: active("Root.B");'
    )
    extraction = extract_source_core(core, "assumptions_component", _SolveBudget(None))

    assert extraction.groups == ()
    assert extraction.status == "unknown"
    assert "internal mismatch" in extraction.reason


def test_semantic_role_covers_every_produced_category() -> None:
    """Every category the relation builder emits has a frozen reading."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume event("Root.Go", 0) == true; '
        'check reach <= 2: active("Root.B");'
    )
    roles = {
        group.category: _semantic_role(group.category)
        for group in core._tracked_groups + core._tracked_case_groups
    }

    assert set(roles.values()) <= {
        "domain_rule",
        "initial_fact",
        "transition_rule",
        "assumption",
        "definedness",
    }
    assert roles["domain.frame_state"] == "domain_rule"
    assert roles["initial.variable"] == "initial_fact"
    assert roles["transition.step"] == "transition_rule"
    assert roles["assumption.frame"] == "assumption"


def test_an_unknown_category_has_no_invented_reading() -> None:
    """A new group family must decide its reading, not fall back silently."""
    with pytest.raises(BmcBuildError, match="no semantic role"):
        _semantic_role("mystery.group")


@pytest.mark.parametrize(
    "refs, expected",
    [
        ({}, ()),
        ({"frames": None}, ()),
        ({"frames": 3}, (3,)),
        ({"frames": True}, ()),
        ({"frames": [2, 0, 2]}, (0, 2)),
        ({"frames": (1, "x")}, (1,)),
        ({"frames": "nope"}, ()),
    ],
)
def test_index_metadata_is_normalized_deterministically(refs, expected) -> None:
    """Frame and step indices are sorted, de-duplicated and type-checked."""
    assert _indices(refs, "frames") == expected


def test_core_items_quote_authored_source_when_a_registry_is_given() -> None:
    """An editable core member points back at the text the author wrote."""
    machine = load_state_machine_from_text(_MODEL)
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    core = build_bmc_core_formula(context)
    group = next(g for g in core._tracked_groups if g.source_ref.kind == "fbmcq")

    item = build_core_item(group)

    assert item.constraint.stable_id == group.stable_id
    assert item.semantic_role == _semantic_role(group.category)
    assert item.editable is True
    assert item.normalized_fact["stage"] == group.stage
    assert item.human_text


def test_generated_core_items_are_not_editable_entry_points() -> None:
    """A generated conjunct has no authored line for a user to change."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    group = next(g for g in core._tracked_groups if g.source_ref.kind == "generated")

    item = build_core_item(group)

    assert item.editable is False
    assert item.source_excerpt is None


def test_explain_publishes_a_classification_and_a_mapped_core() -> None:
    """The orchestration answers both questions a localized stage leaves open."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    outcome = explain_infeasibility(core, "assumptions", _SolveBudget(None))
    explanation = outcome.explanation

    assert explanation.classification == "assumptions_self_conflict"
    assert explanation.achieved_mode == "formal"
    assert explanation.status == "partial"
    assert explanation.core.scope == "assumptions_component"
    assert explanation.core.reduction == "raw"
    assert explanation.core.subset_minimality == "not_proven"
    assert [item.constraint.stable_id for item in explanation.core.items] == sorted(
        item.constraint.stable_id for item in explanation.core.items
    )
    assert outcome.checks


def test_explain_keeps_the_classification_when_the_core_degrades() -> None:
    """Losing the core must not lose the answer the caller asked for.

    A usable classification means part of the request was delivered, so the
    frozen truth table calls this ``partial``.  Passing the extraction's own
    ``unknown``/``timeout`` through would claim nothing was established, which
    is the status reserved for a classification that never completed.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )

    class ClassifyOnlyBudget:
        """Grants the classification probe, then reports the deadline spent."""

        deadline = 1.0

        def __init__(self):
            self.calls = 0

        def remaining_ms(self):
            self.calls += 1
            return 60_000 if self.calls == 1 else None

    outcome = explain_infeasibility(core, "assumptions", ClassifyOnlyBudget())
    explanation = outcome.explanation

    assert explanation.classification == "assumptions_self_conflict"
    assert explanation.achieved_mode == "none"
    assert explanation.core is None
    assert explanation.status == "partial"
    assert explanation.reason


def test_explain_degrades_to_a_stage_fallback_without_a_classification() -> None:
    """An unfinished classification never guesses a cause."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 7; '
        'check reach <= 2: active("Root.B");'
    )
    budget = _SolveBudget(1)
    budget.deadline = budget.deadline - 10.0

    outcome = explain_infeasibility(core, "assumptions", budget)

    assert outcome.explanation.classification is None
    assert outcome.explanation.achieved_mode == "none"
    assert outcome.explanation.status == "timeout"
    assert outcome.checks


def test_explain_reports_kernel_without_spending_a_classification_probe() -> None:
    """The kernel stage is classified structurally, then given a core."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    outcome = explain_infeasibility(core, "kernel", _SolveBudget(None))

    assert outcome.explanation.classification == "kernel_conflict"
    assert all(check.name == "unsat_core" for check in outcome.checks)


def test_explain_records_the_requested_mode_it_was_asked_for() -> None:
    """``proof`` degrades to the formal artifact but keeps the request honest."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    outcome = explain_infeasibility(
        core, "assumptions", _SolveBudget(None), requested_mode="proof"
    )

    assert outcome.explanation.requested_mode == "proof"
    assert outcome.explanation.achieved_mode == "formal"


def _frame_symbol(core, name: str = "F_0_state"):
    """Return a real frame-state symbol out of the builder's domain formula."""
    for variable in get_vars(core.domain_formula):
        if variable.decl().name() == name:
            return variable
    raise AssertionError("no %s symbol in the domain formula" % name)


def _with_aggregate(core, aggregate: str, expression):
    """Replace one aggregate and its tracked groups consistently.

    Both halves move together so ``partition_tracked_groups`` still reproduces
    the builder's own formula.  The expressions stay real Z3 terms over the
    real frame symbols, so the classifier is exercised against production
    formula objects rather than against a hand-built stub.
    """
    stage, category = {
        "initial": ("initialization", "initial.where"),
        "environment": ("assumptions", "assumption.frame"),
        "transition": ("kernel", "transition.step"),
    }[aggregate]
    kept = tuple(
        group
        for group in core._tracked_groups
        if not AGGREGATE_SELECTORS[aggregate](group)
    )
    injected = BmcTrackedConstraint(
        stable_id="contract.%s" % aggregate,
        stage=stage,
        category=category,
        expressions=(expression,),
        source_ref=BmcSourceRef("generated", None, None),
    )
    field = {
        "initial": "initial_formula",
        "environment": "environment_formula",
        "transition": "transition_formula",
    }[aggregate]
    return replace(core, _tracked_groups=kept + (injected,), **{field: expression})


@pytest.mark.parametrize(
    "aggregate, stage, expected",
    [
        ("initial", "initialization", "initialization_domain_conflict"),
        ("environment", "assumptions", "assumptions_domain_conflict"),
    ],
)
def test_domain_conflicts_are_classified_against_production_formulas(
    aggregate, stage, expected
) -> None:
    """A component that only conflicts with ``D_N`` is named a domain conflict.

    No authored query in this suite reaches this branch: the binder resolves
    every state reference to a value the domain already admits.  That is an
    observation about the queries tried here, not a proof of impossibility, so
    the branch is pinned against the real domain formula and a real frame
    symbol instead of being left untested.  If a natural witness turns up
    later it should replace this contract test.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; '
        'check reach <= 2: active("Root.B");'
    )
    out_of_domain = _frame_symbol(core) == 99
    assert z3.Solver().check(out_of_domain) == z3.sat

    tampered = _with_aggregate(core, aggregate, out_of_domain)
    outcome = classify_infeasibility(tampered, stage, _SolveBudget(None))

    assert outcome.classification == expected
    assert outcome.scope == CLASSIFICATION_SCOPES[expected]
    assert [check.name for check in outcome.checks] == [
        "component_%s" % stage,
        "domain_%s" % stage,
    ]


def test_initialization_kernel_conflict_is_reachable_from_authored_text() -> None:
    """An initializer that only the transition relation rejects is a kernel conflict.

    A guard whose runtime definedness fails leaves the encoded step with no
    successor, because an undefined guard must block the transition rather
    than quietly read as false.  ``D_N`` and ``I_0`` are then satisfiable
    together while the full kernel is not, which is exactly this
    classification.  Driving it from authored FCSTM keeps the branch pinned to
    behaviour a user can actually produce.
    """
    source = """def int x = 1;
def int y = 0;
state Root {
    state A { during { x = x + 1; } }
    state B;
    [*] -> A;
    A -> B : if [x / y > 0];
}"""
    core = _core_formula(
        'init state("Root.A") where x == 1 && y == 0; '
        'check reach <= 1: active("Root.A");',
        source,
    )
    with_domain = z3.Solver()
    with_domain.add(core.domain_formula, core.initial_formula)
    with_transition = z3.Solver()
    with_transition.add(
        core.domain_formula, core.transition_formula, core.initial_formula
    )

    assert with_domain.check() == z3.sat
    assert with_transition.check() == z3.unsat

    outcome = classify_infeasibility(core, "initialization", _SolveBudget(None))

    assert outcome.classification == "initialization_kernel_conflict"
    assert outcome.scope == "initialization_prefix"


def test_a_divergent_guard_reaches_the_kernel_conflict_through_the_public_solve() -> (
    None
):
    """The same conflict is what a user sees from the public entry point."""
    machine = load_state_machine_from_text(
        """def int x = 1;
def int y = 0;
state Root {
    state A { during { x = x + 1; } }
    state B;
    [*] -> A;
    A -> B : if [x / y > 0];
}"""
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 1 && y == 0; '
        'check reach <= 1: active("Root.A");'
    )
    result = solve_bmc_property(
        compile_bmc_property(build_bmc_core_formula(context)),
        infeasibility_explanation="formal",
    )
    explanation = result.feasibility.explanation

    assert result.feasibility.infeasible_stage == "initialization"
    assert explanation.classification == "initialization_kernel_conflict"
    assert explanation.core.scope == "initialization_prefix"


class _UnknownAfter:
    """A solver wrapper that reports ``unknown`` from the n-th check onwards.

    Real ``unknown`` outcomes depend on solver heuristics and wall-clock time,
    which cannot be pinned in a test.  Wrapping the production solver keeps
    every other behaviour real while making the degradation deterministic.
    """

    def __init__(self, real, counter, threshold, reason, once=False):
        self._real = real
        self._counter = counter
        self._threshold = threshold
        self._reason = reason
        self._once = once
        self._degraded = False

    def check(self, *assumptions):
        self._counter[0] += 1
        hit = (
            self._counter[0] == self._threshold
            if self._once
            else self._counter[0] >= self._threshold
        )
        if hit:
            self._degraded = True
            return z3.unknown
        self._degraded = False
        return self._real.check(*assumptions)

    def reason_unknown(self):
        return self._reason if self._degraded else self._real.reason_unknown()

    def __getattr__(self, name):
        return getattr(self._real, name)


def _patch_solver(counter, threshold, reason, once=False):
    """Swap in a solver wrapper that degrades at a chosen check.

    ``once`` degrades only that single check, which is what a transient
    ``unknown`` looks like; otherwise every later check degrades too.
    """
    real = z3.Solver

    def factory(*args, **kwargs):
        return _UnknownAfter(real(*args, **kwargs), counter, threshold, reason, once)

    return real, factory


@pytest.mark.parametrize(
    "threshold, reason, expected_status, expected_probe",
    [
        (1, "incomplete", "unknown", "component_assumptions"),
        (1, "timeout", "timeout", "component_assumptions"),
        (2, "incomplete", "unknown", "domain_assumptions"),
    ],
)
def test_an_undetermined_probe_degrades_to_the_stage_fallback(
    threshold, reason, expected_status, expected_probe
) -> None:
    """A probe that cannot decide never guesses a classification."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 7; '
        'check reach <= 2: active("Root.B");'
    )
    counter = [0]
    real, factory = _patch_solver(counter, threshold, reason)
    z3.Solver = factory
    try:
        outcome = classify_infeasibility(core, "assumptions", _SolveBudget(None))
    finally:
        z3.Solver = real

    assert outcome.classification is None
    assert outcome.scope == "assumptions_stage_fallback"
    assert outcome.status == expected_status
    assert outcome.checks[-1].name == expected_probe
    assert outcome.checks[-1].status == expected_status
    assert outcome.checks[-1].reason == reason
    assert outcome.checks[-1].started is True


def test_an_undetermined_core_extraction_publishes_nothing() -> None:
    """An undecided extraction withholds the core instead of guessing one."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    counter = [0]
    real, factory = _patch_solver(counter, 1, "incomplete")
    z3.Solver = factory
    try:
        extraction = extract_source_core(
            core, "assumptions_component", _SolveBudget(None)
        )
    finally:
        z3.Solver = real

    assert extraction.groups == ()
    assert extraction.status == "unknown"
    assert "core extraction returned unknown" in extraction.reason


def test_scope_stage_table_is_derived_from_the_scope_targets() -> None:
    """The two scope tables are hand-synced, so they are pinned to each other.

    ``SCOPE_TARGETS`` lives beside the solver and ``_SCOPE_STAGES`` lives in the
    Z3-free data layer, so they cannot share one definition.  Deriving one from
    the other here turns a silent drift into a failing test: a scope that gains
    an aggregate but keeps its old stage set would let a core member escape the
    formula its scope actually proves.
    """
    stage_of_aggregate = {
        "domain": "kernel",
        "transition": "kernel",
        "initial": "initialization",
        "environment": "assumptions",
    }

    assert set(stage_of_aggregate) == set(AGGREGATE_SELECTORS)
    for scope, aggregates in SCOPE_TARGETS.items():
        derived = {stage_of_aggregate[name] for name in aggregates}

        assert derived == set(_SCOPE_STAGES[scope]), scope


def test_a_published_core_quotes_the_authored_query_text() -> None:
    """The end-to-end path answers "which source lines suffice", not just "how".

    The prepared context already owns a source registry, so the orchestration
    reuses it by default.  Without that wiring every ``source_excerpt`` would
    be ``None`` in production while still passing every component test.
    """
    machine = load_state_machine_from_text(_MODEL)
    query = (
        'init state("Root.A") where x == 0;\n'
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 2: active("Root.B");\n'
    )
    context = BmcEngine(machine).prepare(query, query_source_path="prop.fbmcq")
    core = build_bmc_core_formula(context)

    outcome = explain_infeasibility(core, "assumptions", _SolveBudget(None))
    items = outcome.explanation.core.items

    assert [item.source_excerpt for item in items] == [
        'assume at 0: var("x") == 1;',
        'assume at 0: var("x") == 2;',
    ]
    assert all(item.editable for item in items)
    assert all(item.constraint.source.path == "prop.fbmcq" for item in items)
    assert [item.constraint.source.span.line for item in items] == [2, 3]


def test_an_explicit_registry_overrides_the_context_default() -> None:
    """A caller may still supply its own documents, for example for a UI."""
    machine = load_state_machine_from_text(_MODEL)
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 1 && x == 2; '
        'check reach <= 2: active("Root.B");'
    )
    core = build_bmc_core_formula(context)

    outcome = explain_infeasibility(
        core,
        "initialization",
        _SolveBudget(None),
        registry=SourceDocumentRegistry({}),
    )

    assert outcome.explanation.classification == "initialization_self_conflict"
    assert all(item.source_excerpt is None for item in outcome.explanation.core.items)


@pytest.mark.parametrize("separator", ["\n", "\r\n", "\r"])
def test_core_excerpts_survive_every_line_separator(separator) -> None:
    """Quoted text stays correct whatever the query file's line endings are.

    Both grammars only advance the lexer's line counter on ``LF``, so a lone
    ``CR`` file is genuinely one line as far as spans are concerned.  The
    excerpt must still name the right constraint under all three separators;
    rewriting a lone ``CR`` into a line break would invent positions the lexer
    never produced and silently drop the excerpt instead.
    """
    machine = load_state_machine_from_text(_MODEL)
    query = separator.join(
        [
            'init state("Root.A") where x == 0;',
            'assume at 0: var("x") == 1;',
            'assume at 0: var("x") == 2;',
            'check reach <= 2: active("Root.B");',
            "",
        ]
    )
    context = BmcEngine(machine).prepare(query, query_source_path="q.fbmcq")

    outcome = explain_infeasibility(
        build_bmc_core_formula(context), "assumptions", _SolveBudget(None)
    )
    items = outcome.explanation.core.items

    assert [item.source_excerpt for item in items] == [
        'assume at 0: var("x") == 1;',
        'assume at 0: var("x") == 2;',
    ]


def test_programmatic_queries_stay_editable_without_an_excerpt() -> None:
    """A query with no path keeps its authored kind instead of faking one.

    Upstream forbids disguising an ``fbmcq`` constraint as ``generated`` just
    because no path is available, so the entry stays editable and only the
    excerpt is absent.
    """
    machine = load_state_machine_from_text(_MODEL)
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )

    outcome = explain_infeasibility(
        build_bmc_core_formula(context), "assumptions", _SolveBudget(None)
    )
    items = outcome.explanation.core.items

    assert [item.constraint.source.kind for item in items] == ["fbmcq", "fbmcq"]
    assert all(item.editable for item in items)
    assert all(item.source_excerpt is None for item in items)


def test_a_long_excerpt_is_cut_and_declares_the_cut() -> None:
    """A published excerpt is bounded and never shortened silently.

    One very long authored line would otherwise put an unbounded slice of the
    user's source into canonical JSON.  The cut happens at the publication
    point and ``source_excerpt_truncated`` states that it happened, so a
    consumer can tell a complete quote from a clipped one.
    """
    machine = load_state_machine_from_text(_MODEL)
    padding = " " * (MAX_SOURCE_EXCERPT_CHARS + 500)
    query = (
        'init state("Root.A") where x == 0;\n'
        'assume at 0:%s var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 2: active("Root.B");\n' % padding
    )
    context = BmcEngine(machine).prepare(query, query_source_path="q.fbmcq")

    outcome = explain_infeasibility(
        build_bmc_core_formula(context), "assumptions", _SolveBudget(None)
    )
    items = outcome.explanation.core.items
    long_item = max(items, key=lambda item: len(item.source_excerpt or ""))
    short_item = min(items, key=lambda item: len(item.source_excerpt or ""))

    assert len(long_item.source_excerpt) == MAX_SOURCE_EXCERPT_CHARS
    assert long_item.source_excerpt_truncated is True
    assert short_item.source_excerpt == 'assume at 0: var("x") == 2;'
    assert short_item.source_excerpt_truncated is False


def test_an_excerpt_at_the_limit_is_not_reported_as_cut() -> None:
    """The bound is inclusive, so an exactly-sized excerpt stays whole."""
    reference = BmcSourceRef(
        "fbmcq", "q.fbmcq", Span(1, 1, 1, MAX_SOURCE_EXCERPT_CHARS + 1)
    )
    document = "x" * MAX_SOURCE_EXCERPT_CHARS
    group = BmcTrackedConstraint(
        "assumption.0000.frame.0000",
        "assumptions",
        "assumption.frame",
        (True,),
        reference,
    )

    item = build_core_item(
        group, SourceDocumentRegistry({}, query_documents={"q.fbmcq": document})
    )

    assert len(item.source_excerpt) == MAX_SOURCE_EXCERPT_CHARS
    assert item.source_excerpt_truncated is False


def test_two_groups_sharing_a_stable_id_fail_closed() -> None:
    """One activation literal may never gate two different source groups.

    A stable id is metadata and never enters the expressions, so the partition
    assertion cannot notice the collision: the rebuilt aggregates are
    identical.  Left unchecked, the second group would overwrite the first in
    the label map and the core would name the wrong source.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    environment = [g for g in core._tracked_groups if g.stage == "assumptions"]
    collided = replace(environment[1], stable_id=environment[0].stable_id)
    tampered = replace(
        core,
        _tracked_groups=tuple(
            collided if group is environment[1] else group
            for group in core._tracked_groups
        ),
    )

    assert partition_tracked_groups(tampered)

    with pytest.raises(BmcBuildError, match="share the stable id"):
        extract_source_core(tampered, "assumptions_component", _SolveBudget(None))


def test_an_unclassified_stage_still_gets_a_fallback_core() -> None:
    """Remaining budget goes into a fallback core, not to waste.

    The mandatory solve already proved the stage target unsatisfiable, so an
    undetermined *shape* is no reason to withhold the source lines.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    counter = [0]
    real, factory = _patch_solver(counter, 1, "incomplete", once=True)
    z3.Solver = factory
    try:
        outcome = explain_infeasibility(core, "assumptions", _SolveBudget(None))
    finally:
        z3.Solver = real

    explanation = outcome.explanation

    assert explanation.classification is None
    assert explanation.achieved_mode == "formal"
    assert explanation.status == "partial"
    assert explanation.core.scope == "assumptions_stage_fallback"
    assert "degraded" in explanation.reason
    assert explanation.core.items

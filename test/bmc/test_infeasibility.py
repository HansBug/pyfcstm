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
    SCOPE_AGGREGATES,
    STAGE_FALLBACK_SCOPES,
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
    # The step is reported once; it started, because extraction ran before the
    # recheck was refused.
    assert [check.name for check in extraction.checks] == ["unsat_core"]
    assert extraction.checks[0].started is True
    assert extraction.checks[0].status == "timeout"


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
    """Every category the relation builder emits maps to one frozen reading.

    The expected role is pinned per category rather than checked for mere
    membership in the vocabulary: a mapping that silently moved a whole family
    to a different role would still satisfy a membership assertion.
    """
    expected = {
        "domain.frame_state": "domain_rule",
        "domain.variable": "domain_rule",
        "initial.target": "initial_fact",
        "initial.variable": "initial_fact",
        "initial.where": "initial_fact",
        "transition.step": "transition_rule",
        "transition.case": "transition_rule",
        "assumption.frame": "assumption",
        "assumption.event": "assumption",
        "assumption.cardinality": "assumption",
        "definedness": "definedness",
    }
    for category, role in expected.items():
        assert _semantic_role(category) == role, category

    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume event("Root.Go", 0) == true; '
        'check reach <= 2: active("Root.B");'
    )
    produced = {
        group.category for group in core._tracked_groups + core._tracked_case_groups
    }

    assert produced
    assert produced <= set(expected)
    for category in produced:
        assert _semantic_role(category) == expected[category], category


def test_an_unknown_category_has_no_invented_reading() -> None:
    """A new group family must decide its reading, not fall back silently."""
    with pytest.raises(BmcBuildError, match="no semantic role"):
        _semantic_role("mystery.group")


@pytest.mark.parametrize(
    "refs, expected",
    [
        ({}, ()),
        ({"frames": 3}, (3,)),
        ({"frames": [2, 0, 2]}, (0, 2)),
        # A whole-valued float names an index; the public constructor accepts
        # one, so this reader must not answer differently.
        ({"frames": 1.0}, (1,)),
        ({"frames": [2.0, 0]}, (0, 2)),
    ],
)
def test_index_metadata_is_normalized_deterministically(refs, expected) -> None:
    """Frame and step indices are sorted, de-duplicated and type-checked."""
    assert _indices(refs, "frames") == expected


@pytest.mark.parametrize(
    "refs",
    [
        {"frames": None},
        {"frames": True},
        {"frames": (1, "x")},
        {"frames": "nope"},
        {"frames": 1.5},
        {"frames": -1.0},
        {"frames": [1, True]},
        {"frames": {"a": 1}},
        {"frames": [float("nan")]},
    ],
)
def test_unusable_index_metadata_fails_closed(refs) -> None:
    """Metadata that is present but not an index is a mismatch, not a filter.

    Dropping the bad entry would publish ``frames``/``steps`` that contradict
    the ``refs`` mapping beside them, with the disagreement recorded nowhere.
    The frozen boundary asks for a fail-closed internal mismatch on inconsistent
    label/provenance mapping, and the public constructor already refuses the
    same values, so filtering here would also make the two doors disagree.
    """
    with pytest.raises(BmcBuildError, match="is not an index"):
        _indices(refs, "frames")


def test_index_keys_are_published_the_same_way_in_both_fields() -> None:
    """``frames`` and ``refs`` must not disagree about one fact's JSON type.

    The dedicated field canonicalizes a whole-valued float to an integer, so
    echoing the original float back under the same key would publish two
    different types for one position.  ``refs`` is the mapping machine consumers
    are told to read, so the divergence would be visible exactly there.  Keys
    that are not indices stay untouched: a whole-valued float elsewhere may well
    be a measurement.
    """
    group = BmcTrackedConstraint(
        "assumption.0000.frame.0000",
        "assumptions",
        "assumption.frame",
        (True,),
        BmcSourceRef("generated", None, None),
        refs={"frame": 1.0, "step": 2.0, "kind": "state", "threshold": 2.5},
    )

    canonical = build_core_item(group).constraint.to_canonical()

    assert canonical["frames"] == [1]
    assert canonical["steps"] == [2]
    assert canonical["refs"]["frame"] == 1
    assert canonical["refs"]["step"] == 2
    assert type(canonical["refs"]["frame"]) is type(canonical["frames"][0])
    # Free-form metadata is republished as recorded.
    assert canonical["refs"]["threshold"] == 2.5
    assert canonical["refs"]["kind"] == "state"


def test_both_published_copies_of_the_metadata_are_byte_identical() -> None:
    """One item publishes ``refs`` twice, so the two copies must match as JSON.

    Equality is blind to this: ``1 == 1.0`` in Python, so an ``==`` assertion
    over the two mappings passes even when one holds an int and the other a
    float.  Comparing the serialized text is what makes the difference visible,
    and JSON type is exactly what a machine consumer reads.
    """
    import json

    group = BmcTrackedConstraint(
        "assumption.0000.frame.0000",
        "assumptions",
        "assumption.frame",
        (True,),
        BmcSourceRef("generated", None, None),
        refs={"frame": 1.0, "step": [2.0], "assumption": 0},
    )

    canonical = build_core_item(group).to_canonical()
    constraint_refs = canonical["constraint"]["refs"]
    fact_refs = canonical["normalized_fact"]["refs"]

    assert json.dumps(constraint_refs, sort_keys=True) == json.dumps(
        fact_refs, sort_keys=True
    )
    # And the fact's own two views of one index agree as well.
    assert canonical["normalized_fact"]["frames"] == [1]
    assert json.dumps(fact_refs["frame"]) == "1"


def test_plural_index_keys_are_canonicalized_element_by_element() -> None:
    """A recorded sequence of indices is canonicalized the same way."""
    group = BmcTrackedConstraint(
        "assumption.0000.frame.0000",
        "assumptions",
        "assumption.frame",
        (True,),
        BmcSourceRef("generated", None, None),
        refs={"frames": [1.0, 0], "steps": (2.0,)},
    )

    canonical = build_core_item(group).constraint.to_canonical()

    assert canonical["frames"] == [0, 1]
    assert canonical["refs"]["frames"] == [1, 0]
    assert canonical["refs"]["steps"] == [2]
    assert [type(value) for value in canonical["refs"]["frames"]] == [int, int]


def test_only_the_singular_metadata_key_unwraps_a_bare_index() -> None:
    """The plural key follows the same container rule as the public field.

    The singular spelling records one index, so unwrapping it is the reader's
    documented job.  The plural spelling is a sequence, and the public
    constructor refuses a scalar for it; accepting one here would leave the two
    doors disagreeing on the same field value while a comment claimed they
    agreed.
    """
    from pyfcstm.bmc.explanation import BmcConstraintRef

    # Singular: a bare index is the recorded form.
    assert _indices({"frame": 1}, "frame") == (1,)
    # Plural: a scalar is refused, exactly as the constructor refuses it.
    with pytest.raises(BmcBuildError, match="must be a list or tuple"):
        _indices({"frames": 1}, "frame")
    with pytest.raises(TypeError, match="must be a list or tuple"):
        BmcConstraintRef(
            "g0",
            "initialization",
            "initial.target",
            BmcSourceRef("generated", None, None),
            "s",
            frames=1,
        )
    # A sequence under either spelling stays acceptable.
    assert _indices({"frame": [1, 0]}, "frame") == (0, 1)
    assert _indices({"frames": [1, 0]}, "frame") == (0, 1)


def test_absent_index_metadata_is_not_a_mismatch() -> None:
    """A group with no frame constraint records no frame key at all."""
    assert _indices({"kind": "state"}, "frames") == ()
    assert _indices({}, "steps") == ()


def test_mapped_and_direct_indices_agree_on_whole_valued_floats() -> None:
    """One recorded index must not depend on which door it came through.

    ``build_core_item`` reads the builder's metadata while the public
    constructor takes an already-built tuple.  When the two canonicalize
    differently, the mapped path drops an index that the direct path keeps, and
    the published core disagrees with the metadata it was built from without
    anything failing.
    """
    from pyfcstm.bmc.explanation import BmcConstraintRef

    group = BmcTrackedConstraint(
        "initial.where",
        "initialization",
        "initial.where",
        (True,),
        BmcSourceRef("generated", None, None),
        refs={"frame": 1.0, "step": 2.0},
    )
    mapped = build_core_item(group).constraint
    direct = BmcConstraintRef(
        "initial.where",
        "initialization",
        "initial.where",
        BmcSourceRef("generated", None, None),
        "s",
        frames=(1.0,),
        steps=(2.0,),
    )

    assert mapped.frames == direct.frames == (1,)
    assert mapped.steps == direct.steps == (2,)


def test_core_items_quote_authored_source_when_a_registry_is_given() -> None:
    """An editable core member points back at the text the author wrote.

    The registry is passed explicitly here so the excerpt itself is asserted,
    not merely the identity fields that would still be filled in without one.
    """
    machine = load_state_machine_from_text(_MODEL)
    query = (
        'init state("Root.A") where x == 0;\n'
        'assume at 0: var("x") == 1;\n'
        'check reach <= 2: active("Root.B");\n'
    )
    context = BmcEngine(machine).prepare(query, query_source_path="q.fbmcq")
    core = build_bmc_core_formula(context)
    registry = context._source_registry
    group = next(g for g in core._tracked_groups if g.source_ref.kind == "fbmcq")

    item = build_core_item(group, registry)

    assert item.source_excerpt == registry.excerpt(group.source_ref)
    assert item.source_excerpt
    assert item.source_excerpt_truncated is False
    assert item.constraint.stable_id == group.stable_id
    assert item.semantic_role == _semantic_role(group.category)
    assert item.editable is True
    assert item.normalized_fact["kind"] == "structural_constraint"
    assert item.normalized_fact["stage"] == group.stage
    assert item.human_text


def test_a_core_item_without_a_registry_has_no_excerpt() -> None:
    """Identity survives without documents; the quotation does not."""
    core = _core_formula(
        'init state("Root.A") where x == 0; check reach <= 2: active("Root.B");'
    )
    group = core._tracked_groups[0]

    item = build_core_item(group)

    assert item.source_excerpt is None
    assert item.constraint.stable_id == group.stable_id


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


def test_the_scope_target_table_has_a_single_definition() -> None:
    """The candidate set and the published-core rule are the same table.

    Two isomorphic tables kept in step by hand is exactly how a definedness
    group came to be selected into a scope that then rejected it.
    """
    assert SCOPE_TARGETS is SCOPE_AGGREGATES
    assert set(SCOPE_TARGETS) == set(CLASSIFICATION_SCOPES.values()) | set(
        STAGE_FALLBACK_SCOPES
    )
    for scope, aggregates in SCOPE_TARGETS.items():
        assert set(aggregates) <= set(AGGREGATE_SELECTORS), scope


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


def test_an_unnamed_query_yields_a_core_without_source_slices() -> None:
    """Programmatic input maps to groups and a classification, but not to lines.

    ``prepare`` only records a span when the caller names the query's origin, so
    an in-memory query has nothing to slice.  The frozen contract permits that:
    ``path`` and ``span`` are optional precisely for programmatic input.  Pinning
    it here keeps the condition visible, so the absent excerpt is read as "this
    query was never given a path" rather than as a broken source mapping.
    """
    machine = load_state_machine_from_text(_MODEL)
    query = (
        'init state("Root.A") where x == 0;\n'
        'assume at 0: var("x") == 1;\n'
        'assume at 0: var("x") == 2;\n'
        'check reach <= 2: active("Root.B");\n'
    )
    context = BmcEngine(machine).prepare(query)
    core = build_bmc_core_formula(context)

    outcome = explain_infeasibility(core, "assumptions", _SolveBudget(None))
    items = outcome.explanation.core.items

    # The classification and the group-level mapping are unaffected.
    assert outcome.explanation.classification == "assumptions_self_conflict"
    assert outcome.explanation.core.scope == "assumptions_component"
    assert [item.semantic_role for item in items] == ["assumption", "assumption"]
    assert [item.constraint.category for item in items] == [
        "assumption.frame",
        "assumption.frame",
    ]
    # Only the line-level slice is missing, and it is missing for one reason.
    assert all(item.constraint.source.path is None for item in items)
    assert all(item.constraint.source.span is None for item in items)
    assert all(item.source_excerpt is None for item in items)


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


class _ScriptedSolver:
    """Return a scripted verdict for each check, then defer to the real solver.

    Mixing an ``unknown`` classification with a ``timeout`` extraction cannot
    be produced on demand from real inputs, yet the two happen together as soon
    as a non-linear query makes Z3 give up and the shared deadline then runs
    out.  Only Z3's verdict is scripted here; the aggregation under test is
    production code.
    """

    def __init__(self, real, script, counter):
        self._real = real
        self._script = script
        self._counter = counter
        self._reason = ""

    def check(self, *assumptions):
        index = self._counter[0]
        self._counter[0] += 1
        verdict = self._script[index] if index < len(self._script) else None
        if verdict is None:
            self._reason = ""
            return self._real.check(*assumptions)
        self._reason = verdict
        return z3.unknown

    def reason_unknown(self):
        return self._reason or self._real.reason_unknown()

    def __getattr__(self, name):
        return getattr(self._real, name)


@pytest.mark.parametrize(
    "script",
    [
        ["incomplete", "timeout"],
        ["timeout", "incomplete"],
    ],
)
def test_a_spent_deadline_outranks_an_undecided_probe(script) -> None:
    """When nothing is usable, the aggregate reports the timeout.

    Reporting ``unknown`` while the ledger records a timeout sends the reader
    hunting for solver incompleteness when the real fix is a larger budget, so
    the frozen table gives timeout priority and asks for every reason to be
    summarized in check order.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 7; '
        'check reach <= 2: active("Root.B");'
    )
    counter = [0]
    real = z3.Solver

    def factory(*args, **kwargs):
        return _ScriptedSolver(real(*args, **kwargs), script, counter)

    z3.Solver = factory
    try:
        outcome = explain_infeasibility(core, "assumptions", _SolveBudget(None))
    finally:
        z3.Solver = real

    explanation = outcome.explanation

    assert explanation.classification is None
    assert explanation.achieved_mode == "none"
    assert explanation.status == "timeout"
    assert {check.status for check in outcome.checks} == {"unknown", "timeout"}
    assert ";" in explanation.reason
    assert "component probe" in explanation.reason
    assert "core extraction" in explanation.reason


def test_an_all_unknown_run_stays_unknown() -> None:
    """Timeout priority must not relabel a run that never timed out."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 7; '
        'check reach <= 2: active("Root.B");'
    )
    counter = [0]
    real = z3.Solver

    def factory(*args, **kwargs):
        return _ScriptedSolver(
            real(*args, **kwargs), ["incomplete", "incomplete"], counter
        )

    z3.Solver = factory
    try:
        outcome = explain_infeasibility(core, "assumptions", _SolveBudget(None))
    finally:
        z3.Solver = real

    assert outcome.explanation.status == "unknown"


def test_the_role_and_aggregate_rules_have_one_definition_each() -> None:
    """The orchestration reads the data layer instead of keeping its own copies.

    Two questions are deliberately separate: the category says what kind of
    fact a group is, while the stage says which aggregate formula contains it.
    Deriving the aggregate from the category is what let a definedness group be
    selected into a scope that then rejected it.
    """
    from pyfcstm.bmc.explanation import (
        CATEGORY_ROLES,
        category_role,
        constraint_aggregate,
    )

    for category in ("domain.frame_state", "transition.step", "assumption.frame"):
        assert _semantic_role(category) == category_role(category)
    assert set(CATEGORY_ROLES) == {
        "domain.",
        "initial.",
        "transition.",
        "assumption.",
        "definedness",
    }

    # A definedness group reads as definedness wherever it was lowered, but its
    # aggregate follows the stage.
    assert category_role("definedness") == "definedness"
    assert constraint_aggregate("initialization", "definedness") == "initial"
    assert constraint_aggregate("assumptions", "definedness") == "environment"

    # The selectors used by the partition agree with that same rule.
    for stage, category, aggregate in (
        ("kernel", "domain.frame_state", "domain"),
        ("kernel", "transition.step", "transition"),
        ("initialization", "definedness", "initial"),
        ("assumptions", "definedness", "environment"),
    ):
        group = BmcTrackedConstraint(
            "probe", stage, category, (True,), BmcSourceRef("generated", None, None)
        )
        selected = [
            name for name, predicate in AGGREGATE_SELECTORS.items() if predicate(group)
        ]
        assert selected == [aggregate], (stage, category)


def test_a_definedness_constraint_reaches_the_public_explanation() -> None:
    """A guard that needs runtime definedness must not break the public API.

    The definedness groups the builder emits live in the initialization and
    assumptions stages, never in the kernel.  Deriving their aggregate from the
    category instead of the stage made the extraction select one and the core
    constructor then reject it, raising past every degradation path.
    """
    machine = load_state_machine_from_text(
        "def int x = 1;\ndef int y = 0;\n"
        "state Root { state A; state B; [*] -> A; A -> B; }"
    )
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x / y > 0; check reach <= 2: active("Root.B");'
    )
    core = build_bmc_core_formula(context)

    definedness = [g for g in core._tracked_groups if g.category == "definedness"]
    assert definedness
    assert {g.stage for g in definedness} == {"initialization"}

    result = solve_bmc_property(
        compile_bmc_property(core), infeasibility_explanation="formal"
    )
    explanation = result.feasibility.explanation

    assert result.feasibility.infeasible_stage == "initialization"
    assert explanation.core.scope == "initialization_component"
    assert "definedness" in {item.semantic_role for item in explanation.core.items}


def test_a_generated_member_says_it_has_no_authored_line() -> None:
    """A generated constraint explains its missing excerpt instead of hiding it.

    A published core mixes authored entries that quote real lines with
    generated ones that cannot.  Reading "from generated" beside three quoted
    entries looks like the tool failed to find this one's source, so the
    sentence states outright that there is none.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 7; '
        'check reach <= 2: active("Root.B");'
    )
    generated = next(
        group for group in core._tracked_groups if group.source_ref.kind == "generated"
    )

    item = build_core_item(generated)

    assert item.source_excerpt is None
    assert item.editable is False
    assert "no single authored line" in item.human_text
    assert "generated from the model" in item.human_text


def test_an_authored_member_names_its_file() -> None:
    """An authored constraint keeps pointing at the document it came from."""
    machine = load_state_machine_from_text(_MODEL)
    context = BmcEngine(machine).prepare(
        'init state("Root.A") where x == 0;\n'
        'assume at 0: var("x") == 1;\n'
        'check reach <= 2: active("Root.B");\n',
        query_source_path="q.fbmcq",
    )
    core = build_bmc_core_formula(context)
    authored = next(
        group for group in core._tracked_groups if group.source_ref.kind == "fbmcq"
    )

    item = build_core_item(authored, context._source_registry)

    assert "q.fbmcq" in item.human_text
    assert "no single authored line" not in item.human_text


def test_an_unmappable_label_keeps_the_check_that_produced_it() -> None:
    """A solver-contract violation degrades without denying the work it did.

    The extraction check has already run by the time the labels are mapped
    back, so raising past that point would publish an empty ledger for a
    deadline that was actually spent.
    """
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    real = z3.Solver

    class UnknownLabelSolver:
        """Return an activation literal the extraction never registered."""

        def __init__(self, *args, **kwargs):
            self._inner = real(*args, **kwargs)

        def unsat_core(self):
            return [z3.Bool("core_not_a_registered_label")]

        def __getattr__(self, name):
            return getattr(self._inner, name)

    z3.Solver = UnknownLabelSolver
    try:
        extraction = extract_source_core(
            core, "assumptions_component", _SolveBudget(None)
        )
    finally:
        z3.Solver = real

    assert extraction.groups == ()
    assert extraction.status == "unknown"
    assert "internal mismatch" in extraction.reason
    assert "unknown activation label" in extraction.reason
    assert [check.started for check in extraction.checks] == [True]

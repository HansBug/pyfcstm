"""TDD contracts for infeasibility classification and sound source cores.

Every case here drives the public preparation and relation builders with real
FCSTM and FBMCQ text, so the probes and cores under test run against the same
formulas a user would get.
"""

from __future__ import annotations

import z3
import pytest

from pyfcstm.bmc import build_bmc_core_formula
from pyfcstm.bmc.engine import BmcEngine
from pyfcstm.bmc.explanation import CLASSIFICATION_SCOPES, STAGE_FALLBACK_SCOPES
from pyfcstm.bmc.infeasibility import (
    AGGREGATE_SELECTORS,
    SCOPE_TARGETS,
    classify_infeasibility,
    extract_source_core,
    partition_tracked_groups,
)
from pyfcstm.bmc.solver import _SolveBudget
from pyfcstm.model import load_state_machine_from_text

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


def test_objective_formula_never_enters_the_refinement_solver() -> None:
    """The property objective stays out of every scenario core check."""
    core = _core_formula(
        'init state("Root.A") where x == 0; '
        'assume at 0: var("x") == 1; assume at 0: var("x") == 2; '
        'check reach <= 2: active("Root.B");'
    )
    outcome = classify_infeasibility(core, "assumptions", _SolveBudget(None))
    extraction = extract_source_core(core, outcome.scope, _SolveBudget(None))

    rendered = " ".join(
        expression.sexpr()
        for group in extraction.groups
        for expression in group.expressions
    )

    assert "reach" not in rendered

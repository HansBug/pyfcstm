"""Solver choices preserve public BMC verdicts and replayable evidence."""

from dataclasses import replace

import pytest
import z3

from pyfcstm.bmc import (
    BmcBuildError,
    compile_bmc_query,
    decode_bmc_result_trace,
    replay_bmc_witness,
    solve_bmc_property,
)
from pyfcstm.model import load_state_machine_from_text


pytestmark = pytest.mark.unittest


def test_default_preserves_staged_assertions_and_scopes(monkeypatch):
    """The public solve path keeps the generic solver's four assertion levels."""
    formula = compile_bmc_query(
        load_state_machine_from_text("state Root;"),
        'init cold where false; check reach <= 1: active("Root");',
    )
    core = formula.core
    baseline = z3.Solver()
    baseline.add(core.domain_formula, core.transition_formula)
    for expression in (
        core.initial_formula,
        core.environment_formula,
        formula.objective_formula,
    ):
        baseline.push()
        baseline.add(expression)
    expected = []
    for depth in (3, 2, 1, 0):
        expected.append((baseline.sexpr(), depth))
        if depth:
            baseline.pop()

    original_solver = z3.Solver
    observed = []

    def recording_solver():
        solver = original_solver()
        original_check = solver.check

        def check(*assumptions):
            observed.append((solver.sexpr(), solver.num_scopes()))
            return original_check(*assumptions)

        solver.check = check
        return solver

    monkeypatch.setattr(z3, "Solver", recording_solver)
    result = solve_bmc_property(formula)
    assert result.outcome == "scenario_infeasible"
    assert observed == expected


@pytest.mark.parametrize(
    "declarations,condition,logic",
    [
        ("def int x = 0;", "x > 0", "QF_LIA"),
        ("def int x = 0; def float y = 0.0;", "x + y > 0.0", "QF_LIRA"),
        ("def int x = 0; def int y = 1;", "x / y == 2", "QF_NIA"),
        ("def int x = 0;", "x / 3 == 2", None),
        ("def float x = 1.0;", "sqrt(x) > 2.0", "NIRA"),
    ],
)
def test_logic_profile_uses_the_whole_query(declarations, condition, logic):
    """An absent response suffix is false; it must not erase the probe input."""
    machine = load_state_machine_from_text(declarations + " state Root;")
    formula = compile_bmc_query(
        machine,
        'init state("Root") havoc * where %s; '
        'check reach <= 1: active("Root");' % condition,
    )
    result = solve_bmc_property(formula, solver_profile="logic")
    assert result.solver_profile == "logic"
    assert result.solver_logic == logic
    assert result.status == "sat"
    assert result.property_satisfied is True
    assert replay_bmc_witness(machine, decode_bmc_result_trace(result)).ok


@pytest.mark.parametrize("profile", ["default", "logic", "tactic"])
@pytest.mark.parametrize(
    "query,status,outcome,role",
    [
        (
            'check reach <= 1: active("Root");',
            "sat",
            "witness_found",
            "primary_witness",
        ),
        (
            'check forbid <= 1: active("Root");',
            "sat",
            "property_violated",
            "primary_counterexample",
        ),
        ("check reach <= 1: terminated();", "unsat", "no_witness", None),
        (
            "check response <= 1: trigger true -> within 2 false;",
            "unsat",
            "incomplete",
            "incomplete_suffix",
        ),
        (
            'init cold where false; check reach <= 1: active("Root");',
            "unsat",
            "scenario_infeasible",
            None,
        ),
    ],
)
def test_profiles_keep_verdicts_and_replay(profile, query, status, outcome, role):
    machine = load_state_machine_from_text("state Root;")
    result = solve_bmc_property(
        compile_bmc_query(machine, query), solver_profile=profile
    )
    assert result.status == status
    assert result.outcome == outcome
    assert result.to_canonical()["solver_profile"] == profile
    assert result.solver_statistics
    assert all(
        type(value) in (int, float) for value in result.solver_statistics.values()
    )
    if role is not None:
        trace = decode_bmc_result_trace(
            result,
            source="incomplete_suffix" if role == "incomplete_suffix" else "primary",
        )
        assert trace.model_role == role
        assert replay_bmc_witness(machine, trace).ok


@pytest.mark.parametrize("profile", ["default", "logic", "tactic"])
@pytest.mark.parametrize("depth", ["formal", "proof"])
def test_explanations_keep_a_verified_minimal_core(profile, depth):
    machine = load_state_machine_from_text("def int x = 0; state Root;")
    formula = compile_bmc_query(
        machine,
        'init state("Root"); assume at 0: var("x") == 1; '
        'check reach <= 1: active("Root");',
    )
    result = solve_bmc_property(
        formula, solver_profile=profile, infeasibility_explanation=depth
    )
    assert result.outcome == "scenario_infeasible"
    explanation = result.feasibility.explanation
    assert explanation.core.items
    assert explanation.core.subset_minimality == "proven"
    assert explanation.achieved_mode == depth


@pytest.mark.parametrize("profile", [None, True, 1, [], "", "Logic", "fast"])
def test_invalid_profile_is_a_public_argument_error(profile):
    formula = compile_bmc_query(
        load_state_machine_from_text("state Root;"), 'check reach <= 1: active("Root");'
    )
    with pytest.raises(BmcBuildError, match="solver_profile"):
        solve_bmc_property(formula, solver_profile=profile)


@pytest.mark.parametrize(
    "changes",
    [
        {"solver_profile": "fast"},
        {"solver_logic": "QF_LIA"},
        {"solver_profile": "logic", "solver_logic": "wrong"},
        {"solver_statistics": {"conflicts": True}},
        {"solver_statistics": {"conflicts": -1}},
        {"solver_statistics": {"conflicts": float("inf")}},
    ],
)
def test_result_rejects_invalid_solver_metadata(changes):
    formula = compile_bmc_query(
        load_state_machine_from_text("state Root;"), 'check reach <= 1: active("Root");'
    )
    result = solve_bmc_property(formula)
    with pytest.raises(BmcBuildError, match="solver_"):
        replace(result, **changes)


def test_tactic_is_constructed_only_for_the_main_solver(monkeypatch):
    """Observe real Z3 constructors along a public proof request."""
    machine = load_state_machine_from_text("def int x = 0; state Root;")
    formula = compile_bmc_query(
        machine,
        'init state("Root"); assume at 0: var("x") == 1; '
        'check reach <= 1: active("Root");',
    )
    original_then, original_solver = z3.Then, z3.Solver
    constructors = []

    def tactic(*args, **kwargs):
        constructors.append("tactic")
        return original_then(*args, **kwargs)

    def generic(*args, **kwargs):
        constructors.append("default")
        return original_solver(*args, **kwargs)

    monkeypatch.setattr(z3, "Then", tactic)
    monkeypatch.setattr(z3, "Solver", generic)
    result = solve_bmc_property(
        formula, solver_profile="tactic", infeasibility_explanation="proof"
    )
    assert result.feasibility.explanation.achieved_mode == "proof"
    assert constructors[0] == "tactic"
    assert constructors.count("tactic") == 1
    assert constructors.count("default") > 1

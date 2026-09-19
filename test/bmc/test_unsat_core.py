"""Property-neutral core extraction with explicit, source-bearing background."""

import pytest
import z3

from pyfcstm.bmc import BmcBuildError
from pyfcstm.bmc.unsat import (
    BmcUnsatConstraint,
    BmcUnsatQuery,
    explain_unsat_core,
)

pytestmark = pytest.mark.unittest


def test_background_is_retained_during_extraction_and_minimization():
    x, y = z3.Ints("x y")
    source = {"file": "controller.fcstm", "line": 12}
    guard = BmcUnsatConstraint("guard", (x < y,), source)
    query = BmcUnsatQuery(
        "candidate_order", (BmcUnsatConstraint("post", (x >= y,)),), (guard,)
    )
    result = explain_unsat_core(query)
    assert result.query is query
    assert result.query.background[0].source is source
    assert result.solver_status == "unsat"
    assert result.core_check == "verified"
    assert result.core_ids == ("post",)
    assert result.subset_minimality == "proven"
    assert result.derivation_status == "not_attempted"
    assert result.proof_status == "not_attempted"


def test_background_conflict_has_a_verified_empty_tracked_core():
    x = z3.Int("x")
    query = BmcUnsatQuery(
        "init",
        (),
        (
            BmcUnsatConstraint("lower", (x > 0,)),
            BmcUnsatConstraint("upper", (x <= 0,)),
        ),
    )
    result = explain_unsat_core(query)
    assert result.solver_status == "unsat"
    assert result.core_ids == ()
    assert result.core_check == "verified"
    assert result.subset_minimality == "proven"
    assert result.background_conflict


def test_selected_core_is_checked_without_adding_removed_assumptions():
    x = z3.Int("x")
    query = BmcUnsatQuery(
        "scenario",
        (
            BmcUnsatConstraint("positive", (x > 0,)),
            BmcUnsatConstraint("negative", (x < 0,)),
            BmcUnsatConstraint("unrelated", (x < 100,)),
        ),
    )
    bad = explain_unsat_core(query, selected_ids=("positive", "unrelated"))
    assert bad.solver_status == "unsat"
    assert bad.core_check == "sat"
    assert bad.core_ids is None
    assert bad.subset_minimality == "not_proven"
    good = explain_unsat_core(query, selected_ids=("positive", "negative"))
    assert good.core_ids == ("negative", "positive")
    assert good.core_check == "verified"


def test_sat_and_no_constraints_are_not_explained_as_unsat():
    result = explain_unsat_core(BmcUnsatQuery("empty", ()))
    assert result.solver_status == "sat"
    assert result.core_ids is None
    assert result.core_check == "not_checked"
    assert not result.background_conflict


def test_repeated_formulas_keep_distinct_source_occurrences():
    x = z3.Int("x")
    first = BmcUnsatConstraint("line10", (x > 0,), "model:10")
    second = BmcUnsatConstraint("line20", (x > 0,), "model:20")
    query = BmcUnsatQuery(
        "duplicate",
        (
            first,
            second,
            BmcUnsatConstraint("post", (x <= 0,)),
        ),
    )
    result = explain_unsat_core(query, minimize=False)
    assert result.core_check == "verified"
    assert result.subset_minimality == "not_proven"
    assert len(result.core_ids) == 2
    assert query.constraints[0] is first and query.constraints[1] is second


@pytest.mark.parametrize(
    "kind,predicate", [("reach", "x > 0"), ("invariant", "x == 0")]
)
def test_actual_property_objectives_share_the_core_contract(kind, predicate):
    from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
    from pyfcstm.model import load_state_machine_from_text

    machine = load_state_machine_from_text("def int x = 0; state Root;")
    formula = compile_bmc_query(machine, "check %s <= 1: %s;" % (kind, predicate))
    verdict = solve_bmc_property(formula)
    query = BmcUnsatQuery(
        kind,
        (
            BmcUnsatConstraint("scenario", (formula.core.core,)),
            BmcUnsatConstraint("objective", (formula.objective_formula,)),
        ),
    )
    result = explain_unsat_core(query)
    assert result.solver_status == "unsat"
    assert result.core_check == "verified"
    assert verdict.property_satisfied is (kind == "invariant")


@pytest.mark.parametrize("background", [False, True])
def test_labels_cannot_alias_authored_boolean_symbols(background):
    # Names resembling the legacy activation scheme remain ordinary inputs.
    authored = z3.Bool("core_positive")
    positive = BmcUnsatConstraint("positive", (authored,))
    negative = BmcUnsatConstraint("negative", (z3.Not(authored),))
    query = BmcUnsatQuery(
        "labels",
        (negative,) if background else (positive, negative),
        (positive,) if background else (),
    )
    result = explain_unsat_core(query)
    assert result.core_check == "verified"
    assert result.subset_minimality == "proven"


def test_authored_fresh_style_name_cannot_change_query_satisfiability():
    context = z3.Context()
    authored = z3.Bool("core!0", ctx=context)
    query = BmcUnsatQuery(
        "authored_symbol", (BmcUnsatConstraint("negative", (z3.Not(authored),)),)
    )
    result = explain_unsat_core(query)
    assert result.solver_status == "sat"
    assert result.core_ids is None


def test_compound_formula_assumptions_map_back_to_whole_source_groups():
    x, y, z = z3.Ints("x y z")
    source = object()
    query = BmcUnsatQuery(
        "ordered_chain",
        (
            BmcUnsatConstraint("chain", (x < y, y < z), source),
            BmcUnsatConstraint("post", (z <= x,)),
        ),
    )
    result = explain_unsat_core(query)
    assert result.core_ids == ("chain", "post")
    assert result.query.constraints[0].source is source
    assert result.core_check == "verified"
    assert result.subset_minimality == "proven"


@pytest.mark.parametrize(
    "identifier,error", [(None, TypeError), (1, TypeError), ("", ValueError)]
)
def test_constraint_identifiers_are_validated(identifier, error):
    with pytest.raises(error):
        BmcUnsatConstraint(identifier, (z3.BoolVal(True),))


@pytest.mark.parametrize(
    "expressions,error",
    [
        ((), ValueError),
        ((True,), TypeError),
        ((z3.Int("x"),), TypeError),
        (None, TypeError),
    ],
)
def test_constraints_require_nonempty_boolean_expression_groups(expressions, error):
    with pytest.raises(error):
        BmcUnsatConstraint("source", expressions)


def test_contexts_are_checked_and_nondefault_contexts_work():
    context = z3.Context()
    x = z3.Int("x", ctx=context)
    first = BmcUnsatConstraint("positive", (x > 0,))
    second = BmcUnsatConstraint("negative", (x < 0,))
    for background in (False, True):
        query = BmcUnsatQuery(
            "context",
            (second,) if background else (first, second),
            (first,) if background else (),
        )
        assert explain_unsat_core(query).core_check == "verified"
    default = BmcUnsatConstraint("default", (z3.BoolVal(True),))
    with pytest.raises(ValueError, match="context"):
        BmcUnsatQuery("mixed", (first, default))
    with pytest.raises(ValueError, match="context"):
        BmcUnsatConstraint("mixed", (x > 0, z3.BoolVal(True)))


@pytest.mark.parametrize(
    "identifier,error", [(None, TypeError), (False, TypeError), ("", ValueError)]
)
def test_query_identity_is_required(identifier, error):
    with pytest.raises(error):
        BmcUnsatQuery(identifier, ())


def test_query_members_and_occurrences_are_validated():
    constraint = BmcUnsatConstraint("source", (z3.BoolVal(False),))
    with pytest.raises(TypeError):
        BmcUnsatQuery("wrong", (False,))
    with pytest.raises(ValueError, match="unique"):
        BmcUnsatQuery("duplicate", (constraint,), (constraint,))
    mutable = [constraint]
    query = BmcUnsatQuery("snapshot", mutable)
    mutable.clear()
    assert query.constraints == (constraint,)
    assert explain_unsat_core(query).core_ids == ("source",)


@pytest.mark.parametrize(
    "options,error",
    [
        ({"selected_ids": ("missing",)}, ValueError),
        ({"selected_ids": ("source", "source")}, ValueError),
        ({"selected_ids": (1,)}, TypeError),
        ({"selected_ids": "source"}, TypeError),
        ({"minimize": 1}, TypeError),
        ({"timeout_ms": 0}, BmcBuildError),
    ],
)
def test_call_options_reject_invalid_inputs(options, error):
    query = BmcUnsatQuery(
        "options", (BmcUnsatConstraint("source", (z3.BoolVal(False),)),)
    )
    with pytest.raises(error):
        explain_unsat_core(query, **options)


def test_wrong_query_type_is_rejected():
    with pytest.raises(TypeError):
        explain_unsat_core(False)


def test_redundant_supplied_core_is_minimized_only_when_requested():
    x = z3.Int("x")
    query = BmcUnsatQuery(
        "shrink",
        (
            BmcUnsatConstraint("a", (x > 0,)),
            BmcUnsatConstraint("b", (x < 0,)),
            BmcUnsatConstraint("c", (x < 100,)),
        ),
    )
    selected = ("a", "b", "c")
    raw = explain_unsat_core(query, selected_ids=selected, minimize=False)
    assert raw.core_ids == selected and raw.reduction == "raw"
    shrunk = explain_unsat_core(query, selected_ids=selected)
    assert shrunk.core_ids == ("a", "b")
    assert shrunk.subset_minimality == "proven"
    empty = explain_unsat_core(query, selected_ids=())
    assert empty.solver_status == "unsat" and empty.core_check == "sat"


@pytest.mark.parametrize("phase", [0, 1, 2, 4])
@pytest.mark.parametrize("reason", ["incomplete", "timeout"])
def test_solver_uncertainty_preserves_only_verified_evidence(
    monkeypatch, phase, reason
):
    # Solver UNKNOWN/timeout is a real dependency outcome, injected at the Z3
    # boundary rather than by replacing an internal invariant or core mapping.
    original_check = z3.Solver.check
    calls = []

    def check(solver, *assumptions):
        calls.append(len(assumptions))
        if len(calls) - 1 == phase:
            return z3.unknown
        return original_check(solver, *assumptions)

    monkeypatch.setattr(z3.Solver, "check", check)
    monkeypatch.setattr(z3.Solver, "reason_unknown", lambda solver: reason)
    x = z3.Int("x")
    query = BmcUnsatQuery(
        "uncertain",
        (
            BmcUnsatConstraint("lower", (x > 0,)),
            BmcUnsatConstraint("upper", (x < 0,)),
        ),
    )
    result = explain_unsat_core(query)
    assert result.subset_minimality == "not_proven"
    assert result.stop_reason
    if phase == 0:
        assert result.solver_status == ("timeout" if reason == "timeout" else "unknown")
        assert result.core_check == "not_checked" and result.core_ids is None
    elif phase == 1:
        assert result.solver_status == "unsat"
        assert result.core_check == ("timeout" if reason == "timeout" else "unknown")
        assert result.core_ids is None
    else:
        assert result.solver_status == "unsat" and result.core_check == "verified"
        assert result.core_ids == ("lower", "upper")


def test_finite_budget_is_shared_by_every_solver_check(monkeypatch):
    original_set = z3.Solver.set
    timeouts = []

    def record(solver, *args, **kwargs):
        timeouts.append(kwargs["timeout"])
        return original_set(solver, *args, **kwargs)

    monkeypatch.setattr(z3.Solver, "set", record)
    query = BmcUnsatQuery(
        "deadline", (BmcUnsatConstraint("false", (z3.BoolVal(False),)),)
    )
    result = explain_unsat_core(query, timeout_ms=10000)
    assert result.subset_minimality == "proven"
    assert len(timeouts) == 4
    assert all(
        0 < later <= earlier <= 10000 for earlier, later in zip(timeouts, timeouts[1:])
    )


def test_background_conflict_can_remove_every_selected_member():
    query = BmcUnsatQuery(
        "background",
        (BmcUnsatConstraint("extra", (z3.BoolVal(True),)),),
        (BmcUnsatConstraint("background", (z3.BoolVal(False),)),),
    )
    result = explain_unsat_core(query, selected_ids=("extra",))
    assert result.background_conflict
    assert result.core_ids == ()
    assert result.subset_minimality == "proven"


def test_empty_scenario_extraction_does_not_claim_minimality():
    from pyfcstm.bmc import compile_bmc_query
    from pyfcstm.bmc.infeasibility import extract_source_core, minimize_source_core
    from pyfcstm.bmc.solver import _SolveBudget
    from pyfcstm.model import load_state_machine_from_text

    model = load_state_machine_from_text("def int x = 0; state Root;")
    core = compile_bmc_query(model, "check reach <= 1: x > 0;").core
    budget = _SolveBudget(None)
    extraction = extract_source_core(core, "assumptions_component", budget)
    assert extraction.groups == ()
    result = minimize_source_core(core, extraction, budget)
    assert result.reduction == "raw"
    assert result.subset_minimality == "not_proven"

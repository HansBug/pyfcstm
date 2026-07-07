"""Property compiler tests for BMC objectives."""

from __future__ import annotations

from dataclasses import replace

import pytest
import z3

from pyfcstm.bmc.ast import Called, Case
from pyfcstm.bmc.binding import BoundBmcQuery, BoundProperty
from pyfcstm.bmc import (
    BmcBuildError,
    BmcEngine,
    BmcPropertyFormula,
    InvalidBmcQuery,
    UnsupportedBmcQuery,
    build_bmc_core_formula,
    compile_bmc_property,
)
from pyfcstm.bmc.query import BmcProperty, BmcQuery
from pyfcstm.model import load_state_machine_from_text


def _solver(*constraints):
    solver = z3.Solver()
    solver.add(*constraints)
    return solver


def _core(dsl: str, query: str):
    model = load_state_machine_from_text(dsl)
    return build_bmc_core_formula(BmcEngine(model).prepare(query))


_EVENT_DSL = """
state Root {
    event Go;
    state A;
    state B;
    [*] -> A;
    A -> B : Go;
}
"""


@pytest.mark.unittest
def test_compile_property_supports_nested_numeric_and_condition_predicates() -> None:
    """Property predicates reuse the core numeric and condition expression lowerer."""
    dsl = """
    def int x = 1;
    def int y = 0;
    state Root;
    """
    formula = compile_bmc_property(
        _core(
            dsl,
            "check reach <= 1: "
            "((x > 0) ? sqrt(x) : abs(y)) >= 0 "
            "&& ((x > 0) ? true : y == 0) "
            "&& -x < 0 && !false;",
        )
    )

    assert _solver(formula.solve_formula).check() == z3.sat


@pytest.mark.unittest
def test_property_formula_public_validation_rejects_bad_constructor_shapes() -> None:
    """The public property result object rejects forged non-Boolean payloads."""
    formula = compile_bmc_property(
        _core("state Root;", 'check reach <= 1: active("Root");')
    )
    kwargs = dict(
        core=formula.core,
        kind=formula.kind,
        polarity=formula.polarity,
        objective_formula=formula.objective_formula,
        solve_formula=formula.solve_formula,
        incomplete_formula=formula.incomplete_formula,
        incomplete_solve_formula=formula.incomplete_solve_formula,
        diagnostics=formula.diagnostics,
        case_label=formula.case_label,
        response_window=formula.response_window,
    )

    with pytest.raises(BmcBuildError, match="core must be BmcCoreFormula"):
        compile_bmc_property(object())
    with pytest.raises(BmcBuildError, match="kind must be a non-empty string"):
        BmcPropertyFormula(**dict(kwargs, kind=""))
    with pytest.raises(BmcBuildError, match="Unsupported property kind"):
        BmcPropertyFormula(**dict(kwargs, kind="proof"))
    with pytest.raises(BmcBuildError, match="polarity"):
        BmcPropertyFormula(**dict(kwargs, polarity="proof"))
    with pytest.raises(BmcBuildError, match="does not match property kind"):
        BmcPropertyFormula(**dict(kwargs, polarity="counterexample"))
    with pytest.raises(BmcBuildError, match="objective_formula"):
        BmcPropertyFormula(**dict(kwargs, objective_formula=z3.IntVal(1)))
    with pytest.raises(BmcBuildError, match="diagnostics"):
        BmcPropertyFormula(**dict(kwargs, diagnostics=("ok", 1)))
    with pytest.raises(BmcBuildError, match="diagnostics"):
        BmcPropertyFormula(**dict(kwargs, diagnostics="oops"))
    with pytest.raises(BmcBuildError, match="diagnostics"):
        BmcPropertyFormula(**dict(kwargs, diagnostics=None))
    with pytest.raises(BmcBuildError, match="case_label"):
        BmcPropertyFormula(**dict(kwargs, case_label=1))
    with pytest.raises(BmcBuildError, match="case_label is only valid"):
        BmcPropertyFormula(**dict(kwargs, case_label="Root::transition::Root::0"))
    with pytest.raises(BmcBuildError, match="case_label must be a non-empty"):
        BmcPropertyFormula(**dict(kwargs, kind="cover", case_label=None))
    with pytest.raises(BmcBuildError, match="response_window"):
        BmcPropertyFormula(**dict(kwargs, response_window=True))
    with pytest.raises(BmcBuildError, match="response_window"):
        BmcPropertyFormula(**dict(kwargs, response_window=0))
    with pytest.raises(BmcBuildError, match="response_window is only valid"):
        BmcPropertyFormula(**dict(kwargs, response_window=1))
    with pytest.raises(BmcBuildError, match="response_window must be a positive"):
        BmcPropertyFormula(**dict(kwargs, kind="response", polarity="counterexample"))


@pytest.mark.unittest
def test_compile_reach_witness_covers_frame_zero_and_final_frame() -> None:
    """Reach is SAT when any frame in ``F_0..F_N`` satisfies the predicate."""
    frame_zero = compile_bmc_property(
        _core(_EVENT_DSL, 'init state("Root.A"); check reach <= 1: active("Root.A");')
    )
    final_frame = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            'check reach <= 1: active("Root.B");',
        )
    )
    unreachable = compile_bmc_property(
        _core(_EVENT_DSL, 'init state("Root.A"); check reach <= 1: terminated();')
    )

    assert frame_zero.kind == "reach"
    assert frame_zero.polarity == "witness"
    assert _solver(frame_zero.solve_formula).check() == z3.sat
    assert _solver(final_frame.solve_formula).check() == z3.sat
    assert _solver(unreachable.solve_formula).check() == z3.unsat


@pytest.mark.unittest
def test_compile_forbid_and_invariant_are_counterexample_objectives() -> None:
    """Forbid/invariant SAT means a violation trace, not a healthy proof."""
    forbid_bad = compile_bmc_property(
        _core(_EVENT_DSL, 'init state("Root.A"); check forbid <= 1: active("Root.A");')
    )
    forbid_absent = compile_bmc_property(
        _core(_EVENT_DSL, 'init state("Root.A"); check forbid <= 1: terminated();')
    )
    invariant_holds = compile_bmc_property(
        _core(_EVENT_DSL, 'init state("Root.A"); check invariant <= 1: active("Root");')
    )
    invariant_bad = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            'check invariant <= 1: active("Root.A");',
        )
    )

    assert forbid_bad.polarity == "counterexample"
    assert invariant_bad.polarity == "counterexample"
    assert _solver(forbid_bad.solve_formula).check() == z3.sat
    assert _solver(forbid_absent.solve_formula).check() == z3.unsat
    assert _solver(invariant_holds.solve_formula).check() == z3.unsat
    assert _solver(invariant_bad.solve_formula).check() == z3.sat


@pytest.mark.unittest
def test_compile_definedness_failures_are_safety_counterexamples() -> None:
    """Undefined property predicates violate safety-style objectives."""
    dsl = """
    def int x = 1;
    def int y = 0;
    state Root;
    """
    invariant = compile_bmc_property(_core(dsl, "check invariant <= 1: x / y > 0;"))
    forbid = compile_bmc_property(_core(dsl, "check forbid <= 1: x / y > 0;"))

    assert _solver(invariant.solve_formula).check() == z3.sat
    assert _solver(forbid.solve_formula).check() == z3.sat


@pytest.mark.unittest
def test_compile_liveness_definedness_failures_are_not_witnesses() -> None:
    """Undefined liveness predicates do not become successful witnesses."""
    dsl = """
    def int x = 1;
    def int y = 0;
    state Root;
    """
    reach = compile_bmc_property(_core(dsl, "check reach <= 1: x / y > 0;"))
    exists_always = compile_bmc_property(
        _core(dsl, "check exists_always <= 1: x / y > 0;")
    )
    must_reach = compile_bmc_property(_core(dsl, "check must_reach <= 1: x / y > 0;"))

    assert _solver(reach.solve_formula).check() == z3.unsat
    assert _solver(exists_always.solve_formula).check() == z3.unsat
    assert _solver(must_reach.solve_formula).check() == z3.sat


@pytest.mark.unittest
def test_compile_must_reach_and_exists_always_polarities() -> None:
    """Must-reach searches for misses; exists-always searches for witnesses."""
    must_reach_miss = compile_bmc_property(
        _core(
            _EVENT_DSL, 'init state("Root.A"); check must_reach <= 1: active("Root.B");'
        )
    )
    must_reach_forced = compile_bmc_property(
        _core(
            _EVENT_DSL, 'init state("Root.A"); check must_reach <= 1: active("Root.A");'
        )
    )
    exists_always_yes = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); check exists_always <= 1: active("Root");',
        )
    )
    exists_always_no = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            'check exists_always <= 1: active("Root.A");',
        )
    )

    assert must_reach_miss.polarity == "counterexample"
    assert exists_always_yes.polarity == "witness"
    assert _solver(must_reach_miss.solve_formula).check() == z3.sat
    assert _solver(must_reach_forced.solve_formula).check() == z3.unsat
    assert _solver(exists_always_yes.solve_formula).check() == z3.sat
    assert _solver(exists_always_no.solve_formula).check() == z3.unsat


def _case_label(dsl: str, query: str, kind: str) -> str:
    core = _core(dsl, query)
    return next(
        relation.case.label
        for step in core.steps
        for relation in step.case_relations
        if relation.case.kind == kind
    )


@pytest.mark.unittest
def test_compile_cover_accepts_transition_and_fallback_but_not_internal_cases() -> None:
    """Cover targets public macro cases and rejects diagnostic/internal labels."""
    transition_label = _case_label(
        _EVENT_DSL,
        'init state("Root.A"); check reach <= 1: active("Root.B");',
        "transition",
    )
    transition = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            'check cover <= 1: case("%s");' % transition_label,
        )
    )
    constrained_unreachable = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == false; '
            'check cover <= 1: case("%s");' % transition_label,
        )
    )
    fallback_dsl = """
    def int x = 0;
    state Root {
        state A;
        state B;
        [*] -> A;
        A -> B : if [x > 0];
    }
    """
    fallback_label = _case_label(
        fallback_dsl,
        'init state("Root.A"); check reach <= 1: active("Root.A");',
        "fallback",
    )
    fallback = compile_bmc_property(
        _core(
            fallback_dsl,
            'init state("Root.A"); check cover <= 1: case("%s");' % fallback_label,
        )
    )
    initial_label = _case_label(
        "state Root;", 'check reach <= 1: active("Root");', "initial"
    )
    delta_label = _case_label(
        "state Root;", 'check reach <= 1: active("Root");', "delta"
    )
    absorb_label = _case_label(
        "state Root;", "init terminated; check reach <= 1: terminated();", "absorb"
    )

    assert transition.polarity == "witness"
    assert transition.case_label == transition_label
    assert _solver(transition.solve_formula).check() == z3.sat
    assert _solver(constrained_unreachable.solve_formula).check() == z3.unsat
    assert _solver(fallback.solve_formula).check() == z3.sat
    for label, cover_query_prefix in (
        (initial_label, ""),
        (delta_label, ""),
        (absorb_label, "init terminated; "),
    ):
        with pytest.raises(InvalidBmcQuery, match="not coverable"):
            compile_bmc_property(
                _core(
                    "state Root;",
                    cover_query_prefix + 'check cover <= 1: case("%s");' % label,
                )
            )
    with pytest.raises(InvalidBmcQuery, match="schema"):
        compile_bmc_property(_core("state Root;", 'check cover <= 1: case("bad");'))
    with pytest.raises(InvalidBmcQuery, match="kind"):
        compile_bmc_property(
            _core("state Root;", 'check cover <= 1: case("Root::weird::Root::0");')
        )
    with pytest.raises(InvalidBmcQuery, match="unknown"):
        compile_bmc_property(
            _core(
                "state Root;",
                'check cover <= 1: case("Root::transition::Root::999");',
            )
        )


@pytest.mark.unittest
def test_compile_response_strict_successor_and_incomplete_suffix() -> None:
    """Response uses strict successor frames and exposes incomplete suffixes."""
    satisfied = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            'check response <= 1: trigger event("Root.Go", current) -> within 1 active("Root.B");',
        )
    )
    strict_violation = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            'check response <= 1: trigger event("Root.Go", current) -> within 1 active("Root.A");',
        )
    )
    absent = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == false; '
            'check response <= 1: trigger event("Root.Go", current) -> within 1 active("Root.B");',
        )
    )
    incomplete = compile_bmc_property(
        _core(
            _EVENT_DSL,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            'check response <= 1: trigger event("Root.Go", current) -> within 2 active("Root.A");',
        )
    )

    assert satisfied.kind == "response"
    assert satisfied.polarity == "counterexample"
    assert satisfied.response_window == 1
    assert _solver(satisfied.solve_formula).check() == z3.unsat
    assert _solver(satisfied.incomplete_solve_formula).check() == z3.unsat
    assert _solver(strict_violation.solve_formula).check() == z3.sat
    assert _solver(absent.solve_formula).check() == z3.unsat
    assert _solver(incomplete.solve_formula).check() == z3.unsat
    assert _solver(incomplete.incomplete_solve_formula).check() == z3.sat


@pytest.mark.unittest
def test_compile_response_honors_strict_successor_window_boundaries() -> None:
    """Response excludes the trigger frame and includes the last window frame."""
    dsl = """
    state Root {
        event Go;
        state A;
        state B;
        state C;
        [*] -> A;
        A -> B : Go;
        B -> C : if [true];
    }
    """
    trigger_frame_not_enough = compile_bmc_property(
        _core(
            dsl,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            "check response <= 2: "
            'trigger event("Root.Go", current) -> within 2 active("Root.A");',
        )
    )
    last_window_frame = compile_bmc_property(
        _core(
            dsl,
            'init state("Root.A"); assume event("Root.Go", 0) == true; '
            "check response <= 2: "
            'trigger event("Root.Go", current) -> within 2 active("Root.C");',
        )
    )

    assert _solver(trigger_frame_not_enough.solve_formula).check() == z3.sat
    assert _solver(last_window_frame.solve_formula).check() == z3.unsat
    assert _solver(last_window_frame.incomplete_solve_formula).check() == z3.unsat


@pytest.mark.unittest
def test_compile_response_treats_trigger_undefined_as_counterexample() -> None:
    """An undefined response trigger is a violation, not a vacuous pass."""
    dsl = """
    def int x = 1;
    def int y = 0;
    state Root;
    """
    objective = compile_bmc_property(
        _core(dsl, 'check response <= 1: trigger x / y > 0 -> within 1 active("Root");')
    )

    assert _solver(objective.solve_formula).check() == z3.sat


@pytest.mark.unittest
def test_compile_property_rejects_step_atoms_outside_allowed_contexts() -> None:
    """Property compilation and binding keep frame/step atoms separated."""
    with pytest.raises(InvalidBmcQuery, match="event_not_allowed"):
        BmcEngine(load_state_machine_from_text(_EVENT_DSL)).prepare(
            'check reach <= 1: event("Root.Go", current);'
        )
    with pytest.raises(InvalidBmcQuery, match="event_not_allowed"):
        BmcEngine(load_state_machine_from_text(_EVENT_DSL)).prepare(
            'check response <= 1: trigger true -> within 1 event("Root.Go", current);'
        )
    with pytest.raises(InvalidBmcQuery, match="cover_predicate"):
        BmcEngine(load_state_machine_from_text(_EVENT_DSL)).prepare(
            'check cover <= 1: case("Root::transition::Root::0") && true;'
        )
    with pytest.raises(InvalidBmcQuery, match="unsupported_called_atom"):
        BmcEngine(load_state_machine_from_text(_EVENT_DSL)).prepare(
            'check reach <= 1: called("Hook");'
        )


@pytest.mark.unittest
def test_compile_property_rechecks_case_atom_context_for_forged_core() -> None:
    """Compiler-level validation rejects non-frame atoms in forged objectives."""
    base = _core("state Root;", 'check reach <= 1: active("Root");')
    bad_property = BmcProperty("reach", 1, predicate=Case("Root::transition::Root::0"))
    bad_query = BmcQuery(
        property=bad_property,
        initial=base.context.query.initial,
        assumptions=base.context.query.assumptions,
    )
    bad_bound_query = BoundBmcQuery(
        bad_query,
        base.context.bound_query.initial,
        base.context.bound_query.assumptions,
        BoundProperty(bad_property),
        base.context.bound_query.references,
    )
    bad_context = replace(base.context, query=bad_query, bound_query=bad_bound_query)

    with pytest.raises(UnsupportedBmcQuery, match="case atoms"):
        compile_bmc_property(replace(base, context=bad_context))

    called_property = BmcProperty("reach", 1, predicate=Called("Hook"))
    called_query = BmcQuery(
        property=called_property,
        initial=base.context.query.initial,
        assumptions=base.context.query.assumptions,
    )
    called_bound_query = BoundBmcQuery(
        called_query,
        base.context.bound_query.initial,
        base.context.bound_query.assumptions,
        BoundProperty(called_property),
        base.context.bound_query.references,
    )
    called_context = replace(
        base.context, query=called_query, bound_query=called_bound_query
    )
    with pytest.raises(UnsupportedBmcQuery, match="abstract call trace"):
        compile_bmc_property(replace(base, context=called_context))


@pytest.mark.unittest
def test_property_formula_canonical_schema_is_stable() -> None:
    """Canonical summaries expose the planned handoff fields."""
    formula = compile_bmc_property(
        _core("state Root;", 'check reach <= 1: active("Root");')
    )
    canonical = formula.to_canonical()

    assert canonical["node"] == "bmc_property_formula"
    assert canonical["kind"] == "reach"
    assert canonical["polarity"] == "witness"
    assert canonical["bound"] == 1
    assert set(canonical["formulas"]) == {
        "objective",
        "solve",
        "incomplete",
        "incomplete_solve",
    }
    assert canonical["formulas"]["objective"] == formula.objective_formula.sexpr()
    assert canonical["formulas"]["solve"] == formula.solve_formula.sexpr()
    assert canonical["formulas"]["incomplete"] == formula.incomplete_formula.sexpr()
    assert (
        canonical["formulas"]["incomplete_solve"]
        == formula.incomplete_solve_formula.sexpr()
    )
    assert canonical["case_label"] is None
    assert canonical["response_window"] is None

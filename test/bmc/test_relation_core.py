"""Core formula tests for BMC relation building."""

from __future__ import annotations

import z3
import pytest

from pyfcstm.bmc import (
    BmcEngine,
    STATE_TERMINATE_ID,
    UnsupportedBmcQuery,
    build_bmc_core_formula,
)
from pyfcstm.model import load_state_machine_from_text


def _solver(*constraints):
    solver = z3.Solver()
    solver.add(*constraints)
    return solver


@pytest.mark.unittest
def test_core_formula_constrains_initial_state_and_variable_initializers() -> None:
    """I_0 fixes the source state and every persistent initializer."""
    model = load_state_machine_from_text(
        """
        def int x = 2;
        def float y = 0.5;
        state Root {
            state A;
            [*] -> A;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)
    root_a = context.domain.state_path_to_id("Root.A")

    assert core.to_canonical()["node"] == "bmc_core_formula"
    assert _solver(core.core, core.symbols.frame_state(0) != root_a).check() == z3.unsat
    assert _solver(core.core, core.symbols.frame_var(0, "x") != 2).check() == z3.unsat
    assert (
        _solver(core.core, core.symbols.frame_var(0, "y") != z3.RealVal("1/2")).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_terminated_initial_uses_terminate_source_and_absorb_case() -> None:
    """Initial terminated mode constrains F_0 and produces an absorb relation."""
    model = load_state_machine_from_text("state Root;")
    context = BmcEngine(model).prepare(
        "init terminated;\ncheck reach <= 1: terminated();"
    )
    core = build_bmc_core_formula(context)

    assert (
        _solver(core.core, core.symbols.frame_state(0) != STATE_TERMINATE_ID).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, core.symbols.frame_state(1) != STATE_TERMINATE_ID).check()
        == z3.unsat
    )
    assert [rel.case.kind for rel in core.steps[0].case_relations] == ["absorb"]


@pytest.mark.unittest
def test_bound_two_uses_recurrence_absorb_after_initial_termination() -> None:
    """Steps after the initial step use recurrence sources, including sentinels."""
    model = load_state_machine_from_text("state Root;")
    context = BmcEngine(model).prepare("check reach <= 2: terminated();")
    core = build_bmc_core_formula(context)

    assert len(core.steps) == 2
    assert any(
        relation.case.kind == "absorb"
        and relation.case.source_state_id == STATE_TERMINATE_ID
        for relation in core.steps[1].case_relations
    )
    assert (
        _solver(core.core, core.symbols.frame_state(2) != STATE_TERMINATE_ID).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_initial_where_only_constrains_i0_not_macro_case_partition() -> None:
    """Initial ``where`` predicates enter ``I_0`` without changing cases."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B : if [x == 0];
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A") where x > 0;\ncheck reach <= 1: active("Root.B");'
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.unsat
    assert "0 < F_0_x" in str(core.initial_formula)
    assert any(
        relation.case.target_state_path == "Root.B"
        for relation in core.steps[0].case_relations
    )
    assert all(
        "where" not in relation.case.label for relation in core.steps[0].case_relations
    )


@pytest.mark.unittest
def test_action_lowering_failure_is_structured_unsupported() -> None:
    """Action operation failures are surfaced as BMC unsupported diagnostics."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A { during { x = sin(x); } }
            [*] -> A;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.A");'
    )

    with pytest.raises(UnsupportedBmcQuery, match="action block leaf_during"):
        build_bmc_core_formula(context)


@pytest.mark.unittest
def test_guard_lowering_failure_is_structured_unsupported() -> None:
    """Guard expression failures are surfaced as BMC unsupported diagnostics."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            state B;
            [*] -> A;
            A -> B : if [sin(x) > 0];
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");'
    )

    with pytest.raises(UnsupportedBmcQuery, match="guard g0"):
        build_bmc_core_formula(context)


@pytest.mark.unittest
def test_case_relation_uses_implication_not_global_and_and_carries_vars() -> None:
    """An unselected case must not force its target, and unwritten vars carry."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        def int keep = 5;
        state Root {
            event Go;
            state A;
            state B;
            [*] -> A;
            A -> B : Go effect { x = x + 10; }
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");'
    )
    core = build_bmc_core_formula(context)
    go = core.symbols.event_input(0, "Root.Go")
    state_b = context.domain.state_path_to_id("Root.B")
    state_a = context.domain.state_path_to_id("Root.A")
    relations = {
        relation.case.kind: relation for relation in core.steps[0].case_relations
    }

    assert set(relations) == {"fallback", "transition"}
    assert _solver(core.core, go).check() == z3.sat
    assert (
        _solver(core.core, go, core.symbols.frame_state(1) != state_b).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, go, core.symbols.frame_var(1, "x") != 10).check() == z3.unsat
    )
    assert (
        _solver(
            core.core,
            go,
            core.symbols.frame_var(1, "keep") != core.symbols.frame_var(0, "keep"),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core,
            go,
            core.symbols.case_selector(0, relations["fallback"].case.label),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, z3.Not(go), core.symbols.frame_state(1) != state_a).check()
        == z3.unsat
    )

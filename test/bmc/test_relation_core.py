"""Core formula tests for BMC relation building."""

from __future__ import annotations

import z3
import pytest

from pyfcstm.bmc import (
    BmcEngine,
    STATE_INIT_ID,
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
def test_initial_havoc_variable_skips_initializer_but_where_constrains_frame0() -> None:
    """``havoc { x }`` removes only ``x``'s initializer from ``I_0``."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        def int keep = 5;
        state Root {
            state A;
            [*] -> A;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A") havoc { x } where x == 7; '
        'check reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.sat
    assert _solver(core.core, core.symbols.frame_var(0, "x") != 7).check() == z3.unsat
    assert (
        _solver(core.core, core.symbols.frame_var(0, "keep") != 5).check() == z3.unsat
    )


@pytest.mark.unittest
def test_initial_where_without_havoc_keeps_initializer_and_can_be_unsat() -> None:
    """Initial ``where`` remains a relation and never overrides initializers."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A;
            [*] -> A;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A") where x == 7; check reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.unsat


@pytest.mark.unittest
def test_initial_havoc_all_skips_failing_initializer_definedness() -> None:
    """``havoc *`` skips both initializer value and definedness constraints."""
    model = load_state_machine_from_text(
        """
        def int bad = 1 / 0;
        state Root {
            state Safe;
            [*] -> Safe;
        }
        """
    )
    no_havoc = build_bmc_core_formula(
        BmcEngine(model).prepare(
            'init state("Root.Safe"); check reach <= 1: active("Root.Safe");'
        )
    )
    with_havoc = build_bmc_core_formula(
        BmcEngine(model).prepare(
            'init state("Root.Safe") havoc * where bad == 7; '
            'check reach <= 1: active("Root.Safe");'
        )
    )

    assert _solver(no_havoc.core).check() == z3.unsat
    assert _solver(with_havoc.core).check() == z3.sat
    assert (
        _solver(with_havoc.core, with_havoc.symbols.frame_var(0, "bad") != 7).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_terminated_initial_havoc_policy_constrains_and_carries_vars() -> None:
    """Terminated initial policy constrains ``F_0`` vars before absorb carries."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root;
        """
    )
    context = BmcEngine(model).prepare(
        "init terminated havoc * where x == 3; check reach <= 1: terminated();"
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.sat
    assert _solver(core.core, core.symbols.frame_var(0, "x") != 3).check() == z3.unsat
    assert _solver(core.core, core.symbols.frame_var(1, "x") != 3).check() == z3.unsat


@pytest.mark.unittest
def test_initial_havoc_all_is_valid_for_empty_variable_domain() -> None:
    """Wildcard initial ``havoc`` is a no-op when the model has no variables."""
    model = load_state_machine_from_text("state Root;")
    context = BmcEngine(model).prepare(
        'init cold havoc * where active("Root"); check reach <= 1: active("Root");'
    )
    core = build_bmc_core_formula(context)

    assert _solver(core.core).check() == z3.sat
    assert core.context.bound == 1


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
def test_recurrence_absorb_rejects_event_inputs_after_termination() -> None:
    """Terminated runtime steps cannot observe external event inputs."""
    model = load_state_machine_from_text(
        """
        state Root {
            event Go;
            state A;
            [*] -> A;
            A -> [*] : /Go;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A");\n'
        'assume event("Root.Go", 0) == true;\n'
        "check reach <= 2: terminated();"
    )
    core = build_bmc_core_formula(context)
    go_after_termination = core.symbols.event_input(1, "Root.Go")

    assert _solver(core.core).check() == z3.sat
    assert _solver(core.core, go_after_termination).check() == z3.unsat
    assert _solver(core.core, z3.Not(go_after_termination)).check() == z3.sat


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
            z3.Or(core.symbols.delta_flag(0), core.symbols.gamma_flag(0)),
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


@pytest.mark.unittest
def test_step_relation_canonical_exposes_progress_observation_constraints() -> None:
    """Canonical step dumps include Delta_i, Gamma_i, and mutual exclusion."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A {
                during { x = x + 1; }
            }
            [*] -> A;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.A");'
    )
    step = build_bmc_core_formula(context).steps[0].to_canonical()

    assert "delta_constraint" in step
    assert "gamma_constraint" in step
    assert "progress_mutex_constraint" in step
    assert "Delta_0" in step["delta_constraint"]
    assert "Gamma_0" in step["gamma_constraint"]
    assert "Not(And(Delta_0, Gamma_0))" in step["progress_mutex_constraint"]


@pytest.mark.unittest
def test_cold_no_progress_delta_stutters_state_and_vars() -> None:
    """Failed cold entry exposes Delta_i and keeps the init frame unchanged."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Start;
            enter { x = x + 100; }
            state A;
            [*] -> A :: Start;
        }
        """
    )
    context = BmcEngine(model).prepare('check reach <= 1: active("Root");')
    core = build_bmc_core_formula(context)
    no_start = z3.Not(core.symbols.event_input(0, "Root.Start"))

    assert _solver(core.core, no_start).check() == z3.sat
    assert (
        _solver(core.core, no_start, z3.Not(core.symbols.delta_flag(0))).check()
        == z3.unsat
    )
    assert _solver(core.core, no_start, core.symbols.gamma_flag(0)).check() == z3.unsat
    assert (
        _solver(
            core.core, no_start, core.symbols.frame_state(1) != STATE_INIT_ID
        ).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, no_start, core.symbols.frame_var(1, "x") != 0).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, core.symbols.delta_flag(0), core.symbols.gamma_flag(0)
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_cold_init_later_event_executes_root_entry_and_reaches_leaf() -> None:
    """Cold init can stutter first, then consume an event and run root entry."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Start;
            enter { x = x + 7; }
            state A;
            [*] -> A :: Start;
        }
        """
    )
    context = BmcEngine(model).prepare('check reach <= 2: active("Root.A");')
    core = build_bmc_core_formula(context)
    state_a = context.domain.state_path_to_id("Root.A")
    no_start_0 = z3.Not(core.symbols.event_input(0, "Root.Start"))
    start_1 = core.symbols.event_input(1, "Root.Start")

    assert _solver(core.core, no_start_0, start_1).check() == z3.sat
    assert (
        _solver(
            core.core, no_start_0, start_1, z3.Not(core.symbols.delta_flag(0))
        ).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, no_start_0, start_1, core.symbols.gamma_flag(0)).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, no_start_0, start_1, core.symbols.frame_state(1) != STATE_INIT_ID
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core,
            no_start_0,
            start_1,
            z3.Or(core.symbols.delta_flag(1), core.symbols.gamma_flag(1)),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, no_start_0, start_1, core.symbols.frame_state(2) != state_a
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, no_start_0, start_1, core.symbols.frame_var(2, "x") != 7
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_hot_composite_delta_then_event_unlocks_without_replaying_entry() -> None:
    """Hot composite recurrence can stutter, then descend without enter replay."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state Gate {
                event Open;
                enter { x = x + 100; }
                state Leaf;
                [*] -> Leaf :: Open;
            }
            [*] -> Gate;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.Gate");\ncheck reach <= 2: active("Root.Gate.Leaf");'
    )
    core = build_bmc_core_formula(context)
    state_gate = context.domain.state_path_to_id("Root.Gate")
    state_leaf = context.domain.state_path_to_id("Root.Gate.Leaf")
    no_open_0 = z3.Not(core.symbols.event_input(0, "Root.Gate.Open"))
    open_1 = core.symbols.event_input(1, "Root.Gate.Open")

    assert _solver(core.core, no_open_0, open_1).check() == z3.sat
    assert (
        _solver(
            core.core, no_open_0, open_1, z3.Not(core.symbols.delta_flag(0))
        ).check()
        == z3.unsat
    )
    assert (
        _solver(core.core, no_open_0, open_1, core.symbols.gamma_flag(0)).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, no_open_0, open_1, core.symbols.frame_state(1) != state_gate
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, no_open_0, open_1, core.symbols.frame_var(1, "x") != 0
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core,
            no_open_0,
            open_1,
            z3.Or(core.symbols.delta_flag(1), core.symbols.gamma_flag(1)),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, no_open_0, open_1, core.symbols.frame_state(2) != state_leaf
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core, no_open_0, open_1, core.symbols.frame_var(2, "x") != 0
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_stable_leaf_fallback_gamma_commits_during_actions() -> None:
    """Stable fallback exposes Gamma_i while committing during-only actions."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A {
                during { x = x + 1; }
            }
            [*] -> A;
        }
        """
    )
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)
    state_a = context.domain.state_path_to_id("Root.A")

    assert _solver(core.core).check() == z3.sat
    assert _solver(core.core, z3.Not(core.symbols.gamma_flag(0))).check() == z3.unsat
    assert _solver(core.core, core.symbols.delta_flag(0)).check() == z3.unsat
    assert (
        _solver(core.core, core.symbols.frame_state(1) != state_a).check() == z3.unsat
    )
    assert _solver(core.core, core.symbols.frame_var(1, "x") != 1).check() == z3.unsat


@pytest.mark.unittest
def test_active_state_uses_ancestor_or_self_and_init_root_projection() -> None:
    """Public active(...) observes ancestors and maps STATE_INIT to root only."""
    model = load_state_machine_from_text(
        """
        state Root {
            state Parent {
                state Child;
                [*] -> Child;
            }
            state Sibling;
            [*] -> Parent;
        }
        """
    )
    context = BmcEngine(model).prepare('check reach <= 1: active("Root");')
    core = build_bmc_core_formula(context)
    parent_id = context.domain.state_path_to_id("Root.Parent")
    child_id = context.domain.state_path_to_id("Root.Parent.Child")

    assert (
        _solver(
            core.symbols.frame_state(0) == parent_id,
            z3.Not(core.symbols.active_state(0, "Root")),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == parent_id,
            z3.Not(core.symbols.active_state(0, "Root.Parent")),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == parent_id,
            core.symbols.active_state(0, "Root.Sibling"),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == child_id,
            z3.Not(core.symbols.active_state(0, "Root")),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == child_id,
            z3.Not(core.symbols.active_state(0, "Root.Parent")),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == child_id,
            z3.Not(core.symbols.active_state(0, "Root.Parent.Child")),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == child_id,
            core.symbols.active_state(0, "Root.Sibling"),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == STATE_INIT_ID,
            z3.Not(core.symbols.active_state(0, "Root")),
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.symbols.frame_state(0) == STATE_INIT_ID,
            core.symbols.active_state(0, "Root.Parent"),
        ).check()
        == z3.unsat
    )
    terminate_path = context.domain.state_by_id(STATE_TERMINATE_ID).path
    assert z3.is_false(core.symbols.active_state(0, terminate_path))

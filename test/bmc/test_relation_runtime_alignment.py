"""Runtime-alignment tests for BMC relation lowering."""

from __future__ import annotations

from pathlib import Path

import z3
import pytest

from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.simulate.runtime import SimulationRuntimeExpressionError

_MACRO_ALIGNMENT_FIXTURE = (
    Path(__file__).with_name("fixtures") / "macro_runtime_alignment.fcstm"
)


def _solver(*constraints):
    solver = z3.Solver()
    solver.add(*constraints)
    return solver


def _runtime_state(runtime):
    if runtime.is_ended:
        return None
    return ".".join(runtime.current_state.path)


def _event_constraints(core, step_index, events):
    selected = set(events)
    return tuple(
        core.symbols.event_input(step_index, event.path)
        if event.path in selected
        else z3.Not(core.symbols.event_input(step_index, event.path))
        for event in core.context.domain.events
    )


def _assert_relation_matches_runtime(
    dsl,
    query_text,
    *,
    initial_state=None,
    initial_vars=None,
    events=(),
):
    model = load_state_machine_from_text(dsl)
    runtime_kwargs = {}
    if initial_state is not None:
        runtime_kwargs["initial_state"] = initial_state
    if initial_vars is not None:
        runtime_kwargs["initial_vars"] = dict(initial_vars)
    runtime = SimulationRuntime(model, **runtime_kwargs)
    runtime.cycle(list(events))

    context = BmcEngine(model).prepare(query_text)
    core = build_bmc_core_formula(context)
    fixed_events = _event_constraints(core, 0, events)
    expected_state = _runtime_state(runtime)
    expected_state_id = (
        core.context.domain.state_path_to_id(expected_state)
        if expected_state is not None
        else -1
    )

    if expected_state is None:
        from pyfcstm.bmc import STATE_TERMINATE_ID

        expected_state_id = STATE_TERMINATE_ID
    assert (
        _solver(
            core.core,
            *fixed_events,
            core.symbols.frame_state(1) != expected_state_id,
        ).check()
        == z3.unsat
    )
    for name, value in runtime.vars.items():
        assert (
            _solver(
                core.core,
                *fixed_events,
                core.symbols.frame_var(1, name) != value,
            ).check()
            == z3.unsat
        )

    selected = [
        relation
        for relation in core.steps[0].case_relations
        if _solver(core.core, *fixed_events, relation.selector).check() == z3.sat
    ]
    assert len(selected) == 1
    assert selected[0].case.target_state_id == expected_state_id
    return core, selected[0], runtime


def _macro_alignment_fixture_with_initializers(x, y):
    dsl = _MACRO_ALIGNMENT_FIXTURE.read_text()
    dsl = dsl.replace("def int x = 0;", "def int x = %d;" % x, 1)
    dsl = dsl.replace("def int y = 0;", "def int y = %d;" % y, 1)
    return dsl


@pytest.mark.unittest
def test_relation_cold_init_enter_initial_effect_and_during_match_runtime() -> None:
    """Cold initialization lowers entry effects and first leaf ``during``."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 0;
        state Root {
            state A {
                enter { x = x + 1; }
                during { x = x + 2; }
            }
            [*] -> A effect { x = x + 4; }
        }
        """,
        'check reach <= 1: active("Root.A");',
    )

    assert selected.case.kind == "initial"
    assert runtime.vars == {"x": 7}
    assert (
        _solver(
            core.core,
            core.symbols.frame_var(1, "x") != core.symbols.frame_var(0, "x") + 7,
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_relation_action_ifblock_matches_simulation_runtime() -> None:
    """Action-local ``if`` is lowered by solver.operation, not macro splitting."""
    model = load_state_machine_from_text(
        """
        def int x = 2;
        state Root {
            state A {
                during {
                    if [x > 0] { x = x + 1; } else { x = x - 1; }
                }
            }
            [*] -> A;
        }
        """
    )
    runtime = SimulationRuntime(model, initial_state="Root.A", initial_vars={"x": 2})
    runtime.cycle([])
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)

    assert runtime.vars == {"x": 3}
    assert len(core.steps[0].case_relations) == 1
    assert core.steps[0].case_relations[0].case.condition.variables == ()
    assert (
        _solver(core.core, core.symbols.frame_var(1, "x") != runtime.vars["x"]).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_relation_event_transition_effect_matches_simulation_runtime() -> None:
    """Event transition effects and target states align with one runtime cycle."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            event Go;
            state A;
            state B { enter { x = x + 2; } }
            [*] -> A;
            A -> B : Go effect { x = x + 10; }
        }
        """
    )
    runtime = SimulationRuntime(model, initial_state="Root.A", initial_vars={"x": 0})
    runtime.cycle(["Root.Go"])
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");'
    )
    core = build_bmc_core_formula(context)
    state_b = context.domain.state_path_to_id("Root.B")

    assert ".".join(runtime.current_state.path) == "Root.B"
    assert runtime.vars == {"x": 12}
    assert (
        _solver(
            core.core,
            core.symbols.event_input(0, "Root.Go"),
            core.symbols.frame_state(1) != state_b,
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core,
            core.symbols.event_input(0, "Root.Go"),
            core.symbols.frame_var(1, "x") != runtime.vars["x"],
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_relation_exit_effect_enter_order_matches_simulation_runtime() -> None:
    """Exit, transition effect, and target enter blocks keep runtime order."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 0;
        state Root {
            event Go;
            state A { exit { x = x + 5; } }
            state B { enter { x = x + 2; } }
            [*] -> A;
            A -> B : Go effect { x = x + 10; }
        }
        """,
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");',
        initial_state="Root.A",
        initial_vars={"x": 0},
        events=("Root.Go",),
    )

    assert selected.case.kind == "transition"
    assert runtime.vars == {"x": 17}
    assert selected.post_var_exprs["x"].decl().name() == "+"
    assert (
        _solver(
            core.core,
            core.symbols.event_input(0, "Root.Go"),
            core.symbols.frame_var(1, "x") != 17,
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_relation_transition_priority_accepted_masks_match_runtime() -> None:
    """Later transitions are masked by accepted earlier transitions."""
    model = load_state_machine_from_text(
        """
        def int x = 5;
        state Root {
            state A;
            state B;
            state C;
            [*] -> A;
            A -> B : if [x > 0];
            A -> C : if [x < 10];
        }
        """
    )
    runtime = SimulationRuntime(model, initial_state="Root.A", initial_vars={"x": 5})
    runtime.cycle([])
    context = BmcEngine(model).prepare(
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");'
    )
    core = build_bmc_core_formula(context)
    state_b = context.domain.state_path_to_id("Root.B")
    state_c = context.domain.state_path_to_id("Root.C")
    selected_b = [
        relation
        for relation in core.steps[0].case_relations
        if relation.case.target_state_id == state_b
    ][0]
    masked_c = [
        relation
        for relation in core.steps[0].case_relations
        if relation.case.target_state_id == state_c
    ][0]

    assert ".".join(runtime.current_state.path) == "Root.B"
    assert "accepted:%s" % selected_b.case.label in masked_c.case.condition.variables
    assert _solver(core.core, selected_b.selector).check() == z3.sat
    assert _solver(core.core, masked_c.selector).check() == z3.unsat
    assert (
        _solver(core.core, core.symbols.frame_state(1) != state_b).check() == z3.unsat
    )


@pytest.mark.unittest
def test_relation_fallback_negates_failed_guard_and_runs_during() -> None:
    """Fallback cases lower negative guard requirements before actions."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = -1;
        state Root {
            state A { during { x = x + 1; } }
            state B;
            [*] -> A;
            A -> B : if [x > 0];
        }
        """,
        'init state("Root.A");\ncheck reach <= 1: active("Root.A");',
        initial_state="Root.A",
        initial_vars={"x": -1},
    )

    assert selected.case.kind == "fallback"
    assert runtime.vars == {"x": 0}
    assert any(
        atom.startswith("accepted:") for atom in selected.case.condition.variables
    )
    assert "Not" in str(selected.antecedent)
    assert _solver(core.core, core.symbols.frame_var(1, "x") != 0).check() == z3.unsat


@pytest.mark.unittest
def test_relation_guard_definedness_blocks_fallback_false_witness() -> None:
    """Undefined transition guards cannot be converted into fallback traces."""
    model = load_state_machine_from_text(
        """
        def int x = 1;
        def int y = 0;
        state Root {
            state A { during { x = x + 1; } }
            state B;
            [*] -> A;
            A -> B : if [x / y > 0];
        }
        """
    )
    runtime = SimulationRuntime(
        model, initial_state="Root.A", initial_vars={"x": 1, "y": 0}
    )
    with pytest.raises(SimulationRuntimeExpressionError, match="division by zero"):
        runtime.cycle([])
    context = BmcEngine(model).prepare(
        'init state("Root.A") where x == 1 && y == 0;\n'
        'check reach <= 1: active("Root.A");'
    )
    core = build_bmc_core_formula(context)
    fallback = next(
        relation
        for relation in core.steps[0].case_relations
        if relation.case.kind == "fallback"
    )

    assert _solver(core.core).check() == z3.unsat
    assert _solver(core.core, fallback.selector).check() == z3.unsat
    assert any(
        "F_0_y" in str(item.constraint) for item in fallback.definedness_constraints
    )


@pytest.mark.unittest
def test_relation_pseudo_guard_anchor_uses_prefix_actions() -> None:
    """Pseudo guards are lowered after prior transition effects execute."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 0;
        state Root {
            state A;
            pseudo state Route;
            state B;
            state C;
            [*] -> A;
            A -> Route effect { x = x + 2; }
            Route -> B : if [x >= 2];
            Route -> C;
        }
        """,
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");',
        initial_state="Root.A",
        initial_vars={"x": 0},
    )

    assert selected.case.target_state_path == "Root.B"
    assert runtime.vars == {"x": 2}
    assert any(
        "F_0_x" in str(term) and "+ 2" in str(term)
        for term in selected.guard_terms.values()
    )
    assert _solver(core.core, core.symbols.frame_var(1, "x") != 2).check() == z3.unsat


@pytest.mark.unittest
def test_relation_hot_pseudo_guard_has_no_stable_prefix_action() -> None:
    """Hot-starting at a pseudo source does not inherit other source prefixes."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 0;
        state Root {
            state A;
            pseudo state Route;
            state B;
            state C;
            [*] -> A;
            A -> Route effect { x = x + 2; }
            Route -> B : if [x >= 2];
            Route -> C;
        }
        """,
        'init state("Root.Route");\ncheck reach <= 1: active("Root.C");',
        initial_state="Root.Route",
        initial_vars={"x": 0},
    )

    assert selected.case.target_state_path == "Root.C"
    assert runtime.vars == {"x": 0}
    assert all("+ 2" not in str(term) for term in selected.guard_terms.values())
    assert _solver(core.core, core.symbols.frame_var(1, "x") != 0).check() == z3.unsat


@pytest.mark.unittest
def test_relation_parent_continuation_guard_uses_prefixed_exit_effects() -> None:
    """Parent continuation guards see prefix actions before selecting Done."""
    core, selected, runtime = _assert_relation_matches_runtime(
        _macro_alignment_fixture_with_initializers(11, 0),
        'init state("Root.System.A");\ncheck reach <= 1: active("Root.Done");',
        initial_state="Root.System.A",
        initial_vars={"x": 11, "y": 0},
        events=("Root.System.A.Tick",),
    )

    assert selected.case.target_state_path == "Root.Done"
    assert runtime.vars == {"x": 11113, "y": 11036}
    assert [guard.reason for guard in selected.case.guard_requirements] == [
        "pseudo_guard",
        "parent_continuation_guard",
    ]
    assert any(
        "F_0_y" in str(term) and "+ 10" in str(term) and "+ 20" in str(term)
        for term in selected.guard_terms.values()
    )
    assert (
        _solver(
            core.core,
            *_event_constraints(core, 0, ("Root.System.A.Tick",)),
            core.symbols.frame_var(1, "y") != runtime.vars["y"],
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_relation_rejected_parent_continuation_rolls_back_to_fallback() -> None:
    """Rejected pseudo and parent candidates do not leak rolled-back effects."""
    core, selected, runtime = _assert_relation_matches_runtime(
        _macro_alignment_fixture_with_initializers(11, -200),
        'init state("Root.System.A");\ncheck reach <= 1: active("Root.System.A");',
        initial_state="Root.System.A",
        initial_vars={"x": 11, "y": -200},
        events=("Root.System.A.Tick",),
    )

    assert selected.case.kind == "fallback"
    assert selected.case.target_state_path == "Root.System.A"
    assert runtime.vars == {"x": 1012, "y": 800}
    assert (
        _solver(
            core.core,
            *_event_constraints(core, 0, ("Root.System.A.Tick",)),
            core.symbols.frame_var(1, "x") != runtime.vars["x"],
        ).check()
        == z3.unsat
    )
    assert (
        _solver(
            core.core,
            *_event_constraints(core, 0, ("Root.System.A.Tick",)),
            core.symbols.frame_var(1, "y") != runtime.vars["y"],
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
def test_relation_hot_composite_initial_descent_matches_runtime() -> None:
    """Hot-starting a composite lowers its initial descent without parent enter."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 0;
        state Root {
            state Parent {
                enter { x = x + 100; }
                state Child { enter { x = x + 2; } }
                [*] -> Child effect { x = x + 4; }
            }
            [*] -> Parent;
        }
        """,
        'init state("Root.Parent");\ncheck reach <= 1: active("Root.Parent.Child");',
        initial_state="Root.Parent",
        initial_vars={"x": 0},
    )

    assert selected.case.kind == "initial"
    assert [block.runtime_role for block in selected.case.action_blocks] == [
        "transition_effect",
        "state_enter",
    ]
    assert runtime.vars == {"x": 6}
    assert _solver(core.core, core.symbols.frame_var(1, "x") != 6).check() == z3.unsat


@pytest.mark.unittest
def test_relation_temporary_variables_do_not_enter_post_var_pool() -> None:
    """Block-local temporaries can drive assignments but not post-var metadata."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 1;
        state Root {
            state A {
                during {
                    tmp = x + 1;
                    x = tmp + 1;
                }
            }
            [*] -> A;
        }
        """,
        'init state("Root.A");\ncheck reach <= 1: active("Root.A");',
        initial_state="Root.A",
        initial_vars={"x": 1},
    )

    assert runtime.vars == {"x": 3}
    assert set(selected.post_var_exprs) == {"x"}
    assert "tmp" not in selected.post_var_exprs
    assert _solver(core.core, core.symbols.frame_var(1, "x") != 3).check() == z3.unsat


@pytest.mark.unittest
def test_relation_root_leaf_exit_matches_runtime_termination() -> None:
    """A root leaf exit transition lowers to the terminate sentinel."""
    core, selected, runtime = _assert_relation_matches_runtime(
        "state Root;",
        'init state("Root");\ncheck reach <= 1: terminated();',
        initial_state="Root",
        initial_vars={},
    )

    from pyfcstm.bmc import STATE_TERMINATE_ID

    assert runtime.is_ended
    assert selected.case.kind == "transition"
    assert selected.case.target_state_id == STATE_TERMINATE_ID
    assert (
        _solver(
            core.core,
            core.symbols.frame_state(1) != STATE_TERMINATE_ID,
        ).check()
        == z3.unsat
    )


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("events", "expected_x"),
    [
        ((), 111107),
        (("Root.Go",), 111145),
    ],
)
def test_relation_multiple_lifecycle_and_aspect_blocks_match_runtime(
    events,
    expected_x,
) -> None:
    """Repeated lifecycle/aspect blocks are executed in recorded order."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 0;
        state Root {
            event Go;
            >> during before { x = x + 100; }
            >> during before { x = x + 1000; }
            >> during after { x = x + 10000; }
            >> during after { x = x + 100000; }
            state A {
                enter { x = x + 1; }
                enter { x = x + 2; }
                during { x = x + 3; }
                during { x = x + 4; }
                exit { x = x + 5; }
                exit { x = x + 6; }
            }
            state B {
                enter { x = x + 7; }
                enter { x = x + 8; }
                during { x = x + 9; }
                during { x = x + 10; }
            }
            [*] -> A;
            A -> B : Go;
        }
        """,
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");',
        initial_state="Root.A",
        initial_vars={"x": 0},
        events=events,
    )

    assert runtime.vars == {"x": expected_x}
    assert selected.post_var_exprs["x"] is not core.symbols.frame_var(0, "x")
    assert _solver(core.core, *_event_constraints(core, 0, events)).check() == z3.sat


@pytest.mark.unittest
def test_relation_abstract_actions_are_noop_writebacks() -> None:
    """Abstract action blocks are occurrence metadata and no-op for variables."""
    core, selected, runtime = _assert_relation_matches_runtime(
        """
        def int x = 0;
        state Root {
            event Go;
            >> during before abstract RootBefore;
            >> during after abstract RootAfter;
            state A {
                enter abstract AEnter;
                during abstract ADuring;
                exit abstract AExit;
            }
            state B;
            [*] -> A;
            A -> B : Go;
        }
        """,
        'init state("Root.A");\ncheck reach <= 1: active("Root.B");',
        initial_state="Root.A",
        initial_vars={"x": 0},
        events=("Root.Go",),
    )

    assert runtime.vars == {"x": 0}
    assert all(block.is_abstract for block in selected.case.action_blocks)
    assert selected.post_var_exprs["x"].eq(core.symbols.frame_var(0, "x"))

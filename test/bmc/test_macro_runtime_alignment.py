"""Runtime-alignment tests for BMC macro-step expansion."""

from __future__ import annotations

from pathlib import Path

import pytest

from pyfcstm.bmc import (
    STATE_DIAGNOSTIC_ID,
    STATE_TERMINATE_ID,
    BmcBuildError,
    build_bmc_domain,
)
from pyfcstm.bmc.expand import expand_macro_step_cases
from pyfcstm.bmc.query import InitialSpec
from pyfcstm.bmc.source import source_from_initial_spec, stable_leaf_source
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

_FIXTURE = Path(__file__).with_name("fixtures") / "macro_runtime_alignment.fcstm"


@pytest.fixture(scope="module")
def alignment_model():
    """Load the checked-in macro expansion alignment fixture."""
    return load_state_machine_from_text(_FIXTURE.read_text(encoding="utf-8"))


@pytest.fixture(scope="module")
def alignment_domain(alignment_model):
    """Build the BMC domain for the macro expansion alignment fixture."""
    return build_bmc_domain(alignment_model, bound=1)


def _case_eval(case, x, y, events=()):
    values = {"x": x, "y": y}
    for variable in case.condition.variables:
        if variable.startswith("event:"):
            values[variable] = variable[len("event:") :] in events
        elif variable.startswith("guard:"):
            values[variable] = _eval_guard_atom(variable[len("guard:") :], x, y)
    return case.condition.evaluate(values)


def _eval_guard_atom(atom, x, y):
    expr = atom.replace("pre:x", "x").replace("pre:y", "y")
    safe_globals = {"__builtins__": {}}
    try:
        return bool(eval(expr, safe_globals, {"x": x, "y": y}))
    except (NameError, SyntaxError, TypeError, ValueError, ZeroDivisionError) as err:
        # NameError: guard atom references a variable outside this test helper's
        # fixture scope; SyntaxError: malformed atom text from the expander;
        # TypeError/ValueError/ZeroDivisionError: Python rejects the numeric
        # expression while emulating runtime guard evaluation.
        raise BmcBuildError("cannot evaluate guard atom %r" % atom) from err


def _updates(case):
    return {item.variable_name: item.expression for item in case.var_update}


def _runtime_after(model, initial_state, x=0, y=0, events=()):
    runtime = SimulationRuntime(
        model,
        initial_state=initial_state,
        initial_vars={"x": x, "y": y},
    )
    runtime.cycle(list(events))
    state_path = (
        "(terminated)" if runtime.is_ended else ".".join(runtime.current_state.path)
    )
    return state_path, dict(runtime.vars)


def _selected_case(formal, x, y, events=()):
    matching = [case for case in formal.cases if _case_eval(case, x, y, events)]
    assert len(matching) == 1, [case.label for case in matching]
    return matching[0]


@pytest.mark.unittest
def test_issue_fixture_stable_leaf_cases_match_golden_table(alignment_domain):
    """The A-source expansion matches the issue fixture's partition and recipes."""
    source = stable_leaf_source(alignment_domain, "Root.System.A")
    formal = expand_macro_step_cases(source)

    by_target_kind = {
        (case.kind, case.target_state_path): case for case in formal.cases
    }
    trap = by_target_kind[("transition", "Root.System.Trap.TrapLeaf")]
    route_b = next(
        case
        for case in formal.success_cases
        if case.kind == "transition" and case.target_state_path == "Root.System.B"
    )
    done = by_target_kind[("transition", "Root.Done")]
    fallback = by_target_kind[("fallback", "Root.System.A")]

    assert _updates(trap) == {"x": "pre:x + 1420", "y": "pre:y + 1010"}
    assert _updates(route_b) == {"x": "2 * pre:x + 1007", "y": "pre:y + 1011"}
    assert _updates(done) == {"x": "pre:x + 11102", "y": "pre:y + 11036"}
    assert _updates(fallback) == {"x": "pre:x + 1001", "y": "pre:y + 1000"}

    tick = "Root.System.A.Tick"
    arm = "Root.System.Trap.Arm"
    expected = [
        (trap, 0, 0, (tick, arm)),
        (route_b, 0, 0, (tick,)),
        (done, 11, 0, (tick,)),
        (fallback, 0, 0, ()),
        (fallback, 11, -200, (tick,)),
    ]
    for selected, x, y, events in expected:
        assert _selected_case(formal, x, y, events) is selected

    assert sorted(event.path for event in trap.used_events) == [
        "Root.System.A.Tick",
        "Root.System.Trap.Arm",
    ]
    assert any(
        event.path == "Root.System.Trap.Arm" and event.reason == "priority"
        for event in route_b.used_events
    )


@pytest.mark.unittest
def test_issue_fixture_stable_leaf_cases_align_with_simulation_runtime(
    alignment_model,
    alignment_domain,
):
    """Every representative A-source runtime example selects the expected case."""
    formal = expand_macro_step_cases(
        stable_leaf_source(alignment_domain, "Root.System.A")
    )
    tick = "Root.System.A.Tick"
    arm = "Root.System.Trap.Arm"
    examples = [
        (0, 0, (), "Root.System.A", {"x": 1001, "y": 1000}),
        (0, 0, (tick, arm), "Root.System.Trap.TrapLeaf", {"x": 1420, "y": 1010}),
        (0, 0, (tick,), "Root.System.B", {"x": 1007, "y": 1011}),
        (11, 0, (tick,), "Root.Done", {"x": 11113, "y": 11036}),
        (11, -200, (tick,), "Root.System.A", {"x": 1012, "y": 800}),
    ]

    for x, y, events, expected_state, expected_vars in examples:
        case = _selected_case(formal, x, y, events)
        runtime_state, runtime_vars = _runtime_after(
            alignment_model,
            "Root.System.A",
            x=x,
            y=y,
            events=events,
        )
        assert case.target_state_path == expected_state
        assert runtime_state == expected_state
        assert runtime_vars == expected_vars


@pytest.mark.unittest
def test_non_stoppable_hot_composite_delta_and_evented_initial_aligns_with_runtime(
    alignment_model,
    alignment_domain,
):
    """Hot Trap expansion splits Arm success from the semantic diagnostic delta."""
    source = source_from_initial_spec(
        alignment_domain,
        InitialSpec(mode="state", state_path="Root.System.Trap"),
    )
    formal = expand_macro_step_cases(source)
    arm = "Root.System.Trap.Arm"

    success = _selected_case(formal, 0, 0, (arm,))
    delta = _selected_case(formal, 0, 0, ())

    assert success.kind == "initial"
    assert success.target_state_path == "Root.System.Trap.TrapLeaf"
    assert _updates(success) == {"x": "pre:x + 1400", "y": "pre:y + 1000"}
    assert delta.kind == "delta"
    assert delta.target_state_id == STATE_DIAGNOSTIC_ID
    assert _updates(delta) == {"x": "pre:x", "y": "pre:y"}

    runtime_state, runtime_vars = _runtime_after(
        alignment_model,
        "Root.System.Trap",
        events=(arm,),
    )
    assert runtime_state == success.target_state_path
    assert runtime_vars == {"x": 1400, "y": 1000}

    runtime = SimulationRuntime(
        alignment_model,
        initial_state="Root.System.Trap",
        initial_vars={"x": 0, "y": 0},
    )
    runtime.cycle([])
    assert ".".join(runtime.current_state.path) == "Root.System.Trap"
    assert runtime.vars == {"x": 0, "y": 0}


@pytest.mark.unittest
def test_cold_root_initial_cycle_aligns_with_runtime(alignment_model, alignment_domain):
    """Cold entry expansion includes root/System initial descent and first during."""
    formal = expand_macro_step_cases(
        source_from_initial_spec(alignment_domain, InitialSpec())
    )
    case = _selected_case(formal, 0, 0, ())

    assert case.kind == "initial"
    assert case.target_state_path == "Root.System.A"
    assert _updates(case) == {"x": "pre:x + 1011", "y": "pre:y + 1001"}

    runtime = SimulationRuntime(alignment_model)
    runtime.cycle([])
    assert ".".join(runtime.current_state.path) == "Root.System.A"
    assert runtime.vars == {"x": 1011, "y": 1001}


@pytest.mark.unittest
def test_pseudo_hot_start_and_parent_continuation_cases(alignment_domain):
    """Expansion covers pseudo routing and exit-to-parent continuation guards."""
    source = source_from_initial_spec(
        alignment_domain,
        InitialSpec(mode="state", state_path="Root.System.Route"),
    )
    formal = expand_macro_step_cases(source)

    to_b = _selected_case(formal, 0, 0, ())
    to_done = _selected_case(formal, 13, 8, ())
    delta = _selected_case(formal, 13, 7, ())

    assert to_b.kind == "initial"
    assert to_b.target_state_path == "Root.System.B"
    assert _updates(to_b) == {"x": "2 * pre:x + 1003", "y": "pre:y + 1001"}
    assert to_done.kind == "initial"
    assert to_done.target_state_path == "Root.Done"
    assert _updates(to_done) == {"x": "pre:x + 11100", "y": "pre:y + 11026"}
    assert delta.kind == "delta"
    assert delta.target_state_id == STATE_DIAGNOSTIC_ID


@pytest.mark.unittest
def test_plain_before_boundary_and_aspect_before_each_run_once():
    """Plain boundary and aspect-before actions stay runtime-aligned."""
    model = load_state_machine_from_text(
        """
        def int x = 1;
        state Root {
            state Parent {
                during before { x = x + 10; }
                >> during before { x = x * 2; }
                state A {
                    enter { x = x + 1; }
                    during { x = x + 3; }
                }
                [*] -> A;
            }
            [*] -> Parent;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(source_from_initial_spec(domain, InitialSpec()))
    case = _selected_case(formal, 1, 0, ())

    assert case.kind == "initial"
    assert case.target_state_path == "Root.Parent.A"
    assert _updates(case) == {"x": "2 * pre:x + 25"}

    runtime = SimulationRuntime(model)
    runtime.cycle([])
    assert ".".join(runtime.current_state.path) == case.target_state_path
    assert runtime.vars == {"x": 27}


@pytest.mark.unittest
def test_rejected_guarded_pseudo_pair_loop_falls_back_like_runtime():
    """Repeated pseudo frontiers are failed candidates, not recursion leaks."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            pseudo state P;
            pseudo state Q;
            [*] -> A;
            A -> P : if [x < 10];
            P -> Q;
            Q -> P;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))

    case = _selected_case(formal, 0, 0, ())

    assert case.kind == "fallback"
    assert case.target_state_path == "Root.A"
    assert case.failed_conditions
    assert _updates(case) == {"x": "pre:x + 1"}

    runtime = SimulationRuntime(
        model,
        initial_state="Root.A",
        initial_vars={"x": 0},
    )
    runtime.cycle([])
    assert ".".join(runtime.current_state.path) == case.target_state_path
    assert runtime.vars == {"x": 1}


@pytest.mark.unittest
def test_rejected_pseudo_loop_allows_later_transition_and_matches_runtime():
    """Validation-skipped pseudo loops do not mask later accepted transitions."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 1; } }
            pseudo state Loop;
            state Done;
            [*] -> A;
            A -> Loop :: Go;
            A -> Done :: Go;
            Loop -> Loop;
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))
    go = "Root.A.Go"

    selected = _selected_case(formal, 0, 0, (go,))
    fallback = _selected_case(formal, 0, 0, ())

    assert selected.kind == "transition"
    assert selected.target_state_path == "Root.Done"
    assert fallback.kind == "fallback"
    assert fallback.target_state_path == "Root.A"
    assert fallback.failed_conditions

    runtime = SimulationRuntime(
        model,
        initial_state="Root.A",
        initial_vars={"x": 0},
    )
    runtime.cycle([go])
    assert ".".join(runtime.current_state.path) == selected.target_state_path
    assert runtime.vars == {"x": 0}


@pytest.mark.unittest
def test_variable_progressing_pseudo_loop_reaches_stable_runtime_target():
    """Variable-progressing pseudo validation loops match runtime outcomes."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 10; } }
            pseudo state P;
            state B;
            [*] -> A;
            A -> P : if [x < 3];
            P -> P : if [x < 3] effect { x = x + 1; }
            P -> B : if [x >= 3];
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))

    for initial_x in (0, 1, 2):
        selected = _selected_case(formal, initial_x, 0, ())
        runtime = SimulationRuntime(
            model,
            initial_state="Root.A",
            initial_vars={"x": initial_x},
        )
        runtime.cycle([])

        assert selected.kind == "transition"
        assert selected.target_state_path == "Root.B"
        assert _updates(selected) == {"x": "3"}
        assert ".".join(runtime.current_state.path) == "Root.B"
        assert runtime.vars == {"x": 3}

    fallback = _selected_case(formal, 3, 0, ())
    runtime = SimulationRuntime(
        model,
        initial_state="Root.A",
        initial_vars={"x": 3},
    )
    runtime.cycle([])

    assert fallback.kind == "fallback"
    assert fallback.target_state_path == "Root.A"
    assert _updates(fallback) == {"x": "pre:x + 10"}
    assert ".".join(runtime.current_state.path) == "Root.A"
    assert runtime.vars == {"x": 13}


@pytest.mark.unittest
def test_variable_progressing_pseudo_loop_with_exit_priority_aligns_with_runtime():
    """Threshold pseudo-loop acceleration preserves declaration priority."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            state A { during { x = x + 10; } }
            pseudo state P;
            state B;
            [*] -> A;
            A -> P : if [x < 3];
            P -> B : if [x >= 3];
            P -> P : if [x < 3] effect { x = x + 1; }
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(stable_leaf_source(domain, "Root.A"))

    for initial_x in (0, 1, 2):
        selected = _selected_case(formal, initial_x, 0, ())
        runtime = SimulationRuntime(
            model,
            initial_state="Root.A",
            initial_vars={"x": initial_x},
        )
        runtime.cycle([])

        assert selected.kind == "transition"
        assert selected.target_state_path == "Root.B"
        assert _updates(selected) == {"x": "3"}
        assert ".".join(runtime.current_state.path) == "Root.B"
        assert runtime.vars == {"x": 3}

    fallback = _selected_case(formal, 3, 0, ())
    assert fallback.kind == "fallback"
    assert fallback.target_state_path == "Root.A"
    assert _updates(fallback) == {"x": "pre:x + 10"}


@pytest.mark.unittest
def test_cold_leaf_root_enters_and_stabilizes_instead_of_terminating():
    """Cold root leaf expansion follows initialization, not root synthetic exit."""
    model = load_state_machine_from_text(
        """
        def int x = 0;
        state Root {
            enter { x = x + 10; }
            during { x = x + 1; }
        }
        """
    )
    domain = build_bmc_domain(model, bound=1)
    formal = expand_macro_step_cases(source_from_initial_spec(domain, InitialSpec()))
    case = _selected_case(formal, 0, 0, ())

    assert case.kind == "initial"
    assert case.target_state_path == "Root"
    assert _updates(case) == {"x": "pre:x + 11"}

    runtime = SimulationRuntime(model)
    runtime.cycle([])
    assert ".".join(runtime.current_state.path) == "Root"
    assert runtime.vars == {"x": 11}

    hot_formal = expand_macro_step_cases(
        source_from_initial_spec(domain, InitialSpec(mode="state", state_path="Root"))
    )
    hot_case = _selected_case(hot_formal, 0, 0, ())
    assert hot_case.kind == "transition"
    assert hot_case.target_state_id == STATE_TERMINATE_ID
    assert hot_case.target_state_path == "__terminate__"
    assert _updates(hot_case) == {"x": "pre:x"}

    hot_runtime = SimulationRuntime(
        model,
        initial_state="Root",
        initial_vars={"x": 0},
    )
    hot_runtime.cycle([])
    assert hot_runtime.is_ended is True
    assert hot_runtime.vars == {"x": 0}

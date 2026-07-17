"""Focused regression tests for simulator Delta macro-step semantics."""

import logging

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import (
    SimulationRuntime,
    SimulationRuntimeDfsError,
    SimulationRuntimeExpressionError,
)


def _runtime(dsl, **kwargs):
    ast = parse_with_grammar_entry(dsl, "state_machine_dsl")
    model = parse_dsl_node_to_state_machine(ast)
    return SimulationRuntime(model, **kwargs)


def test_blocked_hot_start_is_a_stuttering_delta():
    runtime = _runtime(
        """
        def int permit = 2;
        def int ticks = 5;
        state Controller {
            state Standby;
            state Cluster {
                state Ready { during { ticks = ticks + 2; } }
                [*] -> Ready : if [permit == 7];
            }
            [*] -> Standby;
        }
        """,
        initial_state="Controller.Cluster",
        initial_vars={"permit": 2, "ticks": 5},
    )

    first = runtime.cycle()
    second = runtime.cycle()

    assert first.delta is True
    assert second.delta is True
    assert runtime.current_state.path == ("Controller", "Cluster")
    assert runtime.vars == {"permit": 2, "ticks": 5}
    assert runtime.cycle_count == 2
    assert [entry["delta"] for entry in runtime.history] == [True, True]
    assert all(entry["events"] == [] for entry in runtime.history)


def test_delta_preserves_input_occurrences_and_marks_them_unconsumed():
    runtime = _runtime(
        """
        state Root {
            event First;
            event Second;
            pseudo state P;
            state A;
            [*] -> A;
        }
        """,
        initial_state="Root.P",
        initial_vars={},
    )

    result = runtime.cycle(["Root.First", "Root.First", "Root.Second"])

    assert result.delta is True
    assert result.input_events == ("Root.First", "Root.First", "Root.Second")
    assert result.consumed_events == ()
    assert result.unconsumed_events == result.input_events
    assert runtime.history[-1]["events"] == list(result.input_events)


def test_no_outgoing_pseudo_does_not_run_during_or_abstract_handler():
    calls = []
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            pseudo state P {
                during { x = 1 / x; }
                during abstract Tick;
            }
            state A;
            [*] -> A;
        }
        """,
        initial_state="Root.P",
        initial_vars={"x": 0},
    )
    runtime.register_abstract_handler(
        "Root.P.Tick", lambda context: calls.append(context)
    )

    result = runtime.cycle()

    assert result.delta is True
    assert runtime.vars["x"] == 0
    assert calls == []


def test_cold_delta_keeps_root_entry_deferred_until_event_unlock():
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            enter { x = x + 1; }
            state A { during { x = x + 10; } }
            [*] -> A :: Start;
        }
        """
    )

    delta = runtime.cycle()
    ordinary = runtime.cycle("Root.Start")

    assert delta.delta is True
    assert runtime.history[0]["delta"] is True
    assert ordinary.delta is False
    assert runtime.vars["x"] == 11
    assert runtime.current_state.path == ("Root", "A")


def test_event_unlock_after_hot_delta_is_ordinary_success():
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            state Locked {
                state Ready { during { x = x + 1; } }
                [*] -> Ready :: Unlock;
            }
            [*] -> Locked;
        }
        """,
        initial_state="Root.Locked",
        initial_vars={"x": 0},
    )

    delta = runtime.cycle()
    ordinary = runtime.cycle("Root.Locked.Unlock")

    assert delta.delta is True
    assert ordinary.delta is False
    assert runtime.current_state.path == ("Root", "Locked", "Ready")
    assert runtime.vars["x"] == 1


def test_changed_pseudo_self_loop_remains_a_dfs_error():
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            pseudo state P {
                during { x = x + 1; }
            }
            state A;
            [*] -> A;
            P -> P;
        }
        """,
        initial_state="Root.P",
        initial_vars={"x": 0},
    )

    with pytest.raises(SimulationRuntimeDfsError):
        runtime.cycle()

    assert runtime.cycle_count == 0
    assert runtime.history == []


def test_delta_flag_resets_after_ordinary_success_and_error():
    runtime = _runtime(
        """
        def int x = 0;
        state Root {
            state A;
            state B { during { x = 1 / x; } }
            [*] -> A;
            A -> B :: Go;
        }
        """
    )

    assert runtime.cycle().delta is False
    with pytest.raises(SimulationRuntimeExpressionError):
        runtime.cycle("Root.A.Go")
    assert runtime.cycle_count == 1
    assert runtime.history[-1]["delta"] is False


def test_committed_only_delta_does_not_report_consumed_events(monkeypatch, caplog):
    runtime = _runtime(
        """
        state Root {
            event Go;
            state A;
            [*] -> A;
        }
        """
    )
    calls = []

    def fake_run_cycle(
        stack,
        vars_,
        d_events,
        *,
        ended=False,
        validate_post_child_exit=True,
        consumed_events=None,
        is_validation_mode=False,
    ):
        calls.append(is_validation_mode)
        if not is_validation_mode:
            consumed_events.append("Root.Go")
        return is_validation_mode, ended

    monkeypatch.setattr(runtime, "_run_cycle_on_context", fake_run_cycle)

    caplog.set_level(logging.WARNING, logger="pyfcstm.simulate")
    result = runtime.cycle("Root.Go")

    assert calls == [True, False]
    assert result.delta is True
    assert result.consumed_events == ()
    assert result.unconsumed_events == ("Root.Go",)
    assert runtime.cycle_count == 1
    assert runtime.history == [
        {
            "cycle": 1,
            "state": "Root",
            "vars": {},
            "events": ["Root.Go"],
            "delta": True,
        }
    ]
    warnings = [
        record for record in caplog.records if record.levelno == logging.WARNING
    ]
    assert len(warnings) == 1
    assert warnings[0].getMessage() == (
        "Cycle 1 completed as Delta - State: Root; no stoppable successor was committed"
    )

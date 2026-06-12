"""
Unit tests for simulation history retention updates.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


_HISTORY_DSL = """
def int ticks = 0;
state System {
    state Idle {
        during { ticks = ticks + 1; }
    }
    state Active {
        during { ticks = ticks + 10; }
    }
    [*] -> Idle;
    Idle -> Active :: Start;
    Active -> Idle :: Stop;
}
"""


def _build_runtime(**kwargs):
    ast = parse_with_grammar_entry(_HISTORY_DSL, "state_machine_dsl")
    return SimulationRuntime(parse_dsl_node_to_state_machine(ast), **kwargs)


def _advance_to_cycle(runtime, cycle_count):
    if runtime.cycle_count == 0 and cycle_count > 0:
        runtime.cycle()

    while runtime.cycle_count < cycle_count:
        if runtime.current_state.name == "Idle":
            runtime.cycle("System.Idle.Start")
        else:
            runtime.cycle("System.Active.Stop")


def _history_cycles(runtime):
    return [entry["cycle"] for entry in runtime.history]


@pytest.mark.unittest
def test_shrinking_unlimited_history_converges_on_next_successful_cycle():
    runtime = _build_runtime()

    _advance_to_cycle(runtime, 30)
    assert len(runtime.history) == 30
    assert _history_cycles(runtime) == list(range(1, 31))

    runtime.history_size = 5
    _advance_to_cycle(runtime, 31)

    assert len(runtime.history) == 5
    assert _history_cycles(runtime) == [27, 28, 29, 30, 31]

    _advance_to_cycle(runtime, 70)

    assert len(runtime.history) == 5
    assert _history_cycles(runtime) == [66, 67, 68, 69, 70]


@pytest.mark.unittest
def test_constructor_history_size_retains_latest_entries():
    runtime = _build_runtime(history_size=5)

    _advance_to_cycle(runtime, 70)

    assert len(runtime.history) == 5
    assert _history_cycles(runtime) == [66, 67, 68, 69, 70]


@pytest.mark.unittest
def test_shrinking_integer_history_size_converges_on_next_successful_cycle():
    runtime = _build_runtime(history_size=20)

    _advance_to_cycle(runtime, 30)
    assert len(runtime.history) == 20
    assert _history_cycles(runtime) == list(range(11, 31))

    runtime.history_size = 3
    _advance_to_cycle(runtime, 31)

    assert len(runtime.history) == 3
    assert _history_cycles(runtime) == [29, 30, 31]


@pytest.mark.unittest
def test_zero_history_size_keeps_history_empty_after_successful_cycles():
    runtime = _build_runtime()

    _advance_to_cycle(runtime, 3)
    assert len(runtime.history) == 3

    runtime.history_size = 0
    _advance_to_cycle(runtime, 4)
    assert runtime.history == []

    _advance_to_cycle(runtime, 5)
    assert runtime.history == []


@pytest.mark.unittest
def test_widening_history_size_does_not_restore_discarded_entries():
    runtime = _build_runtime(history_size=5)

    _advance_to_cycle(runtime, 10)
    assert _history_cycles(runtime) == [6, 7, 8, 9, 10]

    runtime.history_size = 50
    _advance_to_cycle(runtime, 11)

    assert _history_cycles(runtime) == [6, 7, 8, 9, 10, 11]

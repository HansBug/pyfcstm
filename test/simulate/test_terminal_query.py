"""
Unit tests for terminal runtime query contracts.
"""

import re

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeTerminalStateError


def _build_runtime(dsl_code, **kwargs):
    ast = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    return SimulationRuntime(parse_dsl_node_to_state_machine(ast), **kwargs)


@pytest.mark.unittest
def test_current_state_raises_terminal_state_error_after_runtime_ends():
    runtime = _build_runtime(
        """
state Root {
    state A;
    [*] -> A;
    A -> [*];
}
"""
    )

    runtime.cycle()
    runtime.cycle()

    assert runtime.is_ended is True
    assert runtime.brief_stack == []
    assert runtime.vars == {}
    assert len(runtime.history) == 2
    assert runtime.cycle_count == 2
    assert runtime.is_error_state is False
    assert runtime.error_info is None
    assert runtime.abstract_handler_errors == []

    with pytest.raises(
        SimulationRuntimeTerminalStateError,
        match=r"current_state.*ended.*is_ended",
    ):
        runtime.current_state


@pytest.mark.unittest
def test_terminal_state_error_remains_index_error_compatible():
    runtime = _build_runtime(
        """
state Root {
    state A;
    [*] -> A;
    A -> [*];
}
"""
    )

    runtime.cycle()
    runtime.cycle()

    with pytest.raises(IndexError) as exc_info:
        runtime.current_state

    assert isinstance(exc_info.value, SimulationRuntimeTerminalStateError)


@pytest.mark.unittest
def test_error_state_keeps_current_state_available():
    runtime = _build_runtime(
        """
state Root {
    state A {
        enter abstract Boom;
    }
    [*] -> A;
}
""",
        abstract_error_mode="raise",
    )

    def boom(_ctx):
        raise RuntimeError("boom")

    runtime.register_abstract_handler("Root.A.Boom", boom)

    with pytest.raises(RuntimeError, match=re.escape("boom")):
        runtime.cycle()

    assert runtime.is_error_state is True
    assert runtime.is_ended is False
    assert runtime.current_state.path == ("Root",)
    assert runtime.brief_stack == [(("Root",), "init_wait")]

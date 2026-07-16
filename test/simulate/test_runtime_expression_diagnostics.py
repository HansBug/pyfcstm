"""
Unit tests for runtime expression diagnostics and debug-safe logging.
"""

import logging
import re

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeExpressionError


def _build_runtime(dsl_code):
    ast = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    return SimulationRuntime(parse_dsl_node_to_state_machine(ast))


@pytest.mark.unittest
def test_transition_effect_type_error_is_wrapped_and_rolls_back():
    runtime = _build_runtime(
        """
def int x = 0;
def float y = 1.5;
state Root {
    state A { during { x = x + 1; } }
    state B { during { x = x + 10; } }
    [*] -> A;
    A -> B :: Go effect {
        tmp = y + 0.5;
        x = x + 100;
        y = tmp << 1;
    };
}
"""
    )
    runtime.cycle()

    with pytest.raises(
        SimulationRuntimeExpressionError,
        match=re.escape("operation assignment to 'y' evaluation failed"),
    ) as exc_info:
        runtime.cycle(["Root.A.Go"])

    assert isinstance(exc_info.value.__cause__, TypeError)
    assert "unsupported operand type" in str(exc_info.value.__cause__)
    assert runtime.current_state.path == ("Root", "A")
    assert runtime.brief_stack == [
        (("Root",), "active"),
        (("Root", "A"), "active"),
    ]
    assert runtime.vars == {"x": 1, "y": 1.5}
    assert runtime.cycle_count == 1
    assert runtime.history == [
        {
            "cycle": 1,
            "state": "Root.A",
            "vars": {"x": 1, "y": 1.5},
            "events": [],
            "delta": False,
        }
    ]


@pytest.mark.unittest
def test_large_integer_cycle_does_not_depend_on_disabled_debug_logging():
    runtime = _build_runtime(
        """
def int x = 0;

state Root {
    state A {
        during { x = 10 ** 5000; }
    }
    [*] -> A;
}
"""
    )
    runtime.logger.setLevel(logging.INFO)

    runtime.cycle()

    assert runtime.current_state.path == ("Root", "A")
    assert isinstance(runtime.vars["x"], int)
    assert runtime.vars["x"] == 10 ** 5000
    assert runtime.cycle_count == 1
    assert len(runtime.history) == 1


@pytest.mark.unittest
def test_large_integer_cycle_uses_safe_debug_logging(caplog):
    runtime = _build_runtime(
        """
def int x = 0;

state Root {
    state A {
        during { x = 10 ** 5000; }
    }
    [*] -> A;
}
"""
    )

    with caplog.at_level(logging.DEBUG):
        runtime.cycle()

    assert runtime.current_state.path == ("Root", "A")
    assert isinstance(runtime.vars["x"], int)
    assert runtime.vars["x"] == 10 ** 5000
    assert runtime.cycle_count == 1
    assert len(runtime.history) == 1
    assert "int<5001 digits>" in caplog.text

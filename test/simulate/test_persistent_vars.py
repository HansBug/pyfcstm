"""Tests for SimulationRuntime persistent variable normalization."""

import math

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


def build_state_machine(dsl_code: str):
    """
    Build a state machine model from FCSTM DSL text.

    :param dsl_code: FCSTM DSL source code to parse.
    :type dsl_code: str
    :return: Parsed state machine model used by the simulator tests.
    :rtype: pyfcstm.model.StateMachine

    Example::

        >>> sm = build_state_machine("def int x = 0; state Root { state A; [*] -> A; }")
        >>> sm.root_state.name
        'Root'
    """
    ast = parse_with_grammar_entry(dsl_code, "state_machine_dsl")
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestPersistentVariableInitialization:
    """Test persistent variable initialization normalization."""

    def test_default_initializer_rejects_non_integer_float_for_int(self):
        """Reject non-integer float initializer for an int variable."""
        dsl_code = """
def int count = 3.5;
def int marker = 0;
state Root {
    state A { during { marker = marker + 1; } }
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(
            ValueError,
            match="count.*int.*non-integer float",
        ):
            SimulationRuntime(sm)

    def test_hot_start_without_initial_vars_raises(self):
        """Reject hot start when initial_vars is not provided."""
        dsl_code = """
def int count = 0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="initial_vars must be provided"):
            SimulationRuntime(sm, initial_state="Root.A")

    def test_initial_vars_rejects_unknown_variable(self):
        """Reject initial_vars entries that do not name declared variables."""
        dsl_code = """
def int count = 0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="Variable 'missing' not defined"):
            SimulationRuntime(sm, initial_vars={"count": 0, "missing": 1})

    def test_hot_start_rejects_missing_initial_vars_entries(self):
        """Reject hot start when initial_vars omits any declared variable."""
        dsl_code = """
def int count = 0;
def float reading = 0.0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="initial_vars must provide all variables"):
            SimulationRuntime(
                sm,
                initial_state="Root.A",
                initial_vars={"count": 0},
            )

    @pytest.mark.parametrize(
        ("value", "expected"),
        [
            (True, "must not be bool"),
            ("1", "must be int or float"),
            ([1], "must be int or float"),
        ],
    )
    def test_initial_vars_rejects_bool_and_non_numeric_values(self, value, expected):
        """Reject bool and non-numeric initial_vars before they enter vars."""
        dsl_code = """
def int count = 0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match=expected):
            SimulationRuntime(sm, initial_state="Root.A", initial_vars={"count": value})

    def test_initial_vars_override_skips_failed_default_initializer(self):
        """Allow initial_vars to override a failing default initializer."""
        dsl_code = """
def float recovered = 1.0 / 0.0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"recovered": 5.0},
        )

        assert runtime.vars == {"recovered": 5.0}
        assert type(runtime.vars["recovered"]) is float
        assert runtime.current_state.path == ("Root", "A")

    def test_uncovered_failed_default_initializer_still_reports(self):
        """Still report a failing default initializer when no override exists."""
        dsl_code = """
def float recovered = 1.0 / 0.0;
def int marker = 0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="recovered.*initializer"):
            SimulationRuntime(sm, initial_vars={"marker": 1})

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_initial_vars_rejects_non_finite_int_values(self, value):
        """Reject NaN and infinity before int conversion leaks Python errors."""
        dsl_code = """
def int counter = 0;
def float reading = 0.0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="counter.*int.*finite"):
            SimulationRuntime(
                sm,
                initial_state="Root.A",
                initial_vars={"counter": value, "reading": 0.0},
            )

    def test_initial_vars_converts_float_variable_int_input_to_float(self):
        """Normalize Python int input for a float variable to Python float."""
        dsl_code = """
def float x = 1.0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        runtime = SimulationRuntime(sm, initial_state="Root.A", initial_vars={"x": 5})

        assert runtime.vars["x"] == 5.0
        assert type(runtime.vars["x"]) is float

    @pytest.mark.parametrize("value", [float("nan"), float("inf"), float("-inf")])
    def test_initial_vars_rejects_non_finite_float_values(self, value):
        """Reject non-finite float values for persistent float variables."""
        dsl_code = """
def float x = 0.0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="x.*float.*finite"):
            SimulationRuntime(sm, initial_state="Root.A", initial_vars={"x": value})

    def test_initial_vars_rejects_huge_int_for_float_without_overflow_error(self):
        """Reject huge Python int input for float variables with stable diagnostics."""
        dsl_code = """
def float x = 0.0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="x.*float.*finite"):
            SimulationRuntime(sm, initial_state="Root.A", initial_vars={"x": 2**2000})

    def test_normalization_rejects_unknown_persistent_variable(self):
        """Reject helper calls for variables not defined by the state machine."""
        dsl_code = """
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        with pytest.raises(ValueError, match="Variable 'missing' not defined"):
            runtime._normalize_persistent_value("missing", 1, "test source")

    def test_normalization_rejects_unsupported_persistent_type(self):
        """Reject persistent declarations outside the FCSTM int/float type set."""
        dsl_code = """
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        sm.defines["counter"].type = "double"

        with pytest.raises(ValueError, match="unsupported persistent type 'double'"):
            runtime._normalize_persistent_value("counter", 1, "test source")


@pytest.mark.unittest
class TestPersistentVariableWriteback:
    """Test persistent variable normalization for operation writeback."""

    def test_operation_writeback_rejects_non_integer_float_for_int_and_rolls_back(self):
        """Reject temporary float writeback to int without partial commit."""
        dsl_code = """
def int count = 0;
def int marker = 0;
state Root {
    state A {
        during {
            tmp = 1.5;
            count = tmp;
            marker = marker + 1;
        }
    }
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        with pytest.raises(ValueError, match="count.*int.*non-integer float"):
            runtime.cycle()

        assert runtime.vars == {"count": 0, "marker": 0}
        assert runtime.brief_stack == [(("Root",), "init_wait")]
        assert runtime.history == []
        assert "tmp" not in runtime.vars

    def test_operation_writeback_converts_integer_float_to_int(self):
        """Convert integer-valued float writeback to Python int."""
        dsl_code = """
def int count = 0;
state Root {
    state A {
        during {
            tmp = 10.0;
            count = tmp;
        }
    }
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        runtime.cycle()

        assert runtime.vars["count"] == 10
        assert type(runtime.vars["count"]) is int

    def test_operation_writeback_converts_int_to_float(self):
        """Convert int writeback to a float persistent variable."""
        dsl_code = """
def float reading = 0.0;
state Root {
    state A {
        during { reading = 5; }
    }
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        runtime.cycle()

        assert runtime.vars["reading"] == 5.0
        assert type(runtime.vars["reading"]) is float

    def test_operation_writeback_rejects_huge_int_for_float_and_rolls_back(self):
        """Reject huge integer writeback to float without leaking OverflowError."""
        dsl_code = """
def float reading = 0.0;
def int marker = 0;
state Root {
    state A {
        during {
            reading = 1 << 2000;
            marker = marker + 1;
        }
    }
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        with pytest.raises(ValueError, match="reading.*float.*finite"):
            runtime.cycle()

        assert runtime.vars == {"reading": 0.0, "marker": 0}
        assert runtime.history == []

    def test_enter_action_writeback_rejects_non_integer_float_and_rolls_back(self):
        """Reject enter action writeback to int without committing cycle changes."""
        dsl_code = """
def int count = 0;
def int marker = 0;
state Root {
    state A {
        enter { count = 1.5; }
        during { marker = marker + 1; }
    }
    [*] -> A;
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        with pytest.raises(ValueError, match="count.*int.*non-integer float"):
            runtime.cycle()

        assert runtime.vars == {"count": 0, "marker": 0}
        assert runtime.brief_stack == [(("Root",), "init_wait")]
        assert runtime.history == []

    def test_transition_effect_writeback_rejects_non_integer_float_and_rolls_back(self):
        """Reject transition effect writeback to int without committing transition."""
        dsl_code = """
def int count = 0;
def int marker = 0;
state Root {
    state A { during { marker = marker + 1; } }
    state B;
    [*] -> A;
    A -> B :: Go effect { count = 1.5; }
}
"""
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        with pytest.raises(ValueError, match="count.*int.*non-integer float"):
            runtime.cycle("Root.A.Go")

        assert runtime.vars == {"count": 0, "marker": 1}
        assert runtime.current_state.path == ("Root", "A")
        assert len(runtime.history) == 1

    @pytest.mark.parametrize("expr", ["0.0 / 0.0", "1.0 / 0.0"])
    def test_operation_writeback_rejects_non_finite_float_values(self, expr):
        """Reject operation results that would write non-finite floats."""
        dsl_code = (
            """
def float reading = 0.0;
state Root {
    state A {
        during { reading = %s; }
    }
    [*] -> A;
}
"""
            % expr
        )
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)

        with pytest.raises((ValueError, ArithmeticError)):
            runtime.cycle()

        assert math.isfinite(runtime.vars["reading"])
        assert runtime.vars["reading"] == 0.0
        assert runtime.history == []

"""
Unit tests for solver variable helpers.
"""

import pytest
import z3

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.solver.vars import create_z3_vars_from_state_machine


@pytest.mark.unittest
class TestCreateZ3VarsFromStateMachine:
    """Test StateMachine-to-Z3 variable conversion."""

    def test_create_z3_vars_from_state_machine_mixed_types(self):
        """Test creating Z3 variables from parsed DSL variable definitions."""
        ast = parse_with_grammar_entry(
            """
            def int counter = 0;
            def float temperature = 25.0;

            state System {
                state Idle;
                [*] -> Idle;
            }
            """,
            entry_name="state_machine_dsl",
        )
        state_machine = parse_dsl_node_to_state_machine(ast)

        z3_vars = create_z3_vars_from_state_machine(state_machine)

        assert set(z3_vars.keys()) == {"counter", "temperature"}
        assert z3.is_int(z3_vars["counter"])
        assert z3.is_real(z3_vars["temperature"])
        assert str(z3_vars["counter"]) == "counter"
        assert str(z3_vars["temperature"]) == "temperature"

    def test_create_z3_vars_from_state_machine_without_defines(self):
        """Test creating Z3 variables from a state machine without variable definitions."""
        ast = parse_with_grammar_entry(
            """
            state System {
                state Idle;
                [*] -> Idle;
            }
            """,
            entry_name="state_machine_dsl",
        )
        state_machine = parse_dsl_node_to_state_machine(ast)

        assert create_z3_vars_from_state_machine(state_machine) == {}

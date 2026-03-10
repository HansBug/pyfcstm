"""
Unit tests for CLI init command functionality.

This module tests the init command in both interactive and batch modes.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.entry.simulate.commands import CommandProcessor


def build_state_machine(dsl_code: str):
    """Helper to build state machine from DSL code."""
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestCLIInitCommand:
    """Test CLI init command functionality."""

    def test_init_command_basic(self):
        """Test basic init command with leaf state."""
        dsl_code = '''
def int counter = 0;
def int flag = 0;
state System {
    state Idle {
        during { counter = counter + 1; }
    }
    state Active {
        during { counter = counter + 10; }
    }
    [*] -> Idle;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        # Execute init command
        result = processor.process('init System.Active counter=5 flag=1')

        # Should succeed
        assert not result.should_exit
        assert 'Initialized from state: System.Active' in result.output
        assert 'System.Active' in result.output

        # Verify runtime was replaced
        assert processor.runtime.current_state.path == ('System', 'Active')
        assert processor.runtime.vars['counter'] == 5
        assert processor.runtime.vars['flag'] == 1

    def test_init_command_with_hex_value(self):
        """Test init command with hexadecimal values."""
        dsl_code = '''
def int flags = 0;
def int mask = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init Root.A flags=0xFF mask=0x10')

        assert not result.should_exit
        assert processor.runtime.vars['flags'] == 255
        assert processor.runtime.vars['mask'] == 16

    def test_init_command_with_binary_value(self):
        """Test init command with binary values."""
        dsl_code = '''
def int bits = 0;
def int pattern = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init Root.A bits=0b1010 pattern=0b11')

        assert not result.should_exit
        assert processor.runtime.vars['bits'] == 10
        assert processor.runtime.vars['pattern'] == 3

    def test_init_command_with_float_value(self):
        """Test init command with float values."""
        dsl_code = '''
def float temp = 0.0;
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init Root.A temp=25.5 counter=10')

        assert not result.should_exit
        assert processor.runtime.vars['temp'] == 25.5
        assert processor.runtime.vars['counter'] == 10

    def test_init_command_with_scientific_notation(self):
        """Test init command with scientific notation."""
        dsl_code = '''
def float value = 0.0;
def int count = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init Root.A value=1.5e2 count=0')

        assert not result.should_exit
        assert processor.runtime.vars['value'] == 150.0
        assert processor.runtime.vars['count'] == 0

    def test_init_command_missing_variables(self):
        """Test init command with missing variables."""
        dsl_code = '''
def int x = 0;
def int y = 0;
def int z = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init Root.A x=10 z=30')

        assert not result.should_exit
        assert 'Error: All variables must be provided' in result.output
        assert 'Missing:' in result.output
        assert 'y' in result.output

    def test_init_command_invalid_state_path(self):
        """Test init command with invalid state path."""
        dsl_code = '''
def int counter = 0;
state System {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init System.B counter=0')

        assert not result.should_exit
        assert 'Initialization failed' in result.output

    def test_init_command_invalid_variable_name(self):
        """Test init command with invalid variable name."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init Root.A counter=0 invalid=10')

        assert not result.should_exit
        assert 'Initialization failed' in result.output

    def test_init_command_invalid_value_format(self):
        """Test init command with invalid value format."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init Root.A counter=abc')

        assert not result.should_exit
        assert 'Error: Invalid numeric value' in result.output

    def test_init_command_no_arguments(self):
        """Test init command without arguments."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        result = processor.process('init')

        assert not result.should_exit
        assert 'Usage: init' in result.output

    def test_init_command_then_cycle(self):
        """Test init command followed by cycle execution."""
        dsl_code = '''
def int counter = 0;
state System {
    state Active {
        during { counter = counter + 10; }
    }
    [*] -> Active;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        # Init from Active with counter=5
        result = processor.process('init System.Active counter=5')
        assert not result.should_exit
        assert processor.runtime.vars['counter'] == 5

        # Execute cycle
        result = processor.process('cycle')
        assert not result.should_exit
        assert processor.runtime.vars['counter'] == 15

        # Execute another cycle
        result = processor.process('cycle')
        assert not result.should_exit
        assert processor.runtime.vars['counter'] == 25

    def test_init_command_composite_state(self):
        """Test init command with composite state."""
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state Idle {
            during { counter = counter + 1; }
        }
        [*] -> Idle;
    }
    [*] -> System;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        # Init from composite state
        result = processor.process('init Root.System counter=0')
        assert not result.should_exit

        # First cycle should trigger initial transition
        result = processor.process('cycle')
        assert not result.should_exit
        assert processor.runtime.current_state.path == ('Root', 'System', 'Idle')
        assert processor.runtime.vars['counter'] == 1


@pytest.mark.unittest
class TestCLIInitCommandIntegration:
    """Integration tests for init command with complex scenarios."""

    def test_init_water_heater_from_heating(self):
        """Test init command with water heater example."""
        dsl_code = '''
def int water_temp = 55;
def int draw_count = 0;
state Root {
    state Standby {
        during {
            water_temp = water_temp - 1;
        }
    }

    state Heating {
        during {
            water_temp = water_temp + 4;
        }
    }

    [*] -> Standby;
    Standby -> Heating : if [water_temp <= 50];
    Heating -> Standby : if [water_temp >= 60];
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        # Init from Heating state with low temperature
        result = processor.process('init Root.Heating water_temp=52 draw_count=0')
        assert not result.should_exit
        assert processor.runtime.current_state.path == ('Root', 'Heating')
        assert processor.runtime.vars['water_temp'] == 52

        # Execute cycles
        for i in range(3):
            result = processor.process('cycle')
            assert not result.should_exit

        # Should have transitioned to Standby
        assert processor.runtime.current_state.path == ('Root', 'Standby')
        assert processor.runtime.vars['water_temp'] == 59

    def test_init_multiple_times(self):
        """Test multiple init commands in sequence."""
        dsl_code = '''
def int counter = 0;
state System {
    state A {
        during { counter = counter + 1; }
    }
    state B {
        during { counter = counter + 10; }
    }
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, state_machine=sm, use_color=False)

        # First init
        result = processor.process('init System.A counter=5')
        assert not result.should_exit
        assert processor.runtime.vars['counter'] == 5

        result = processor.process('cycle')
        assert processor.runtime.vars['counter'] == 6

        # Second init (reset)
        result = processor.process('init System.B counter=100')
        assert not result.should_exit
        assert processor.runtime.current_state.path == ('System', 'B')
        assert processor.runtime.vars['counter'] == 100

        result = processor.process('cycle')
        assert processor.runtime.vars['counter'] == 110

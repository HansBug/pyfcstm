"""
Unit tests for hot start functionality in SimulationRuntime.

This module tests the hot start feature that allows starting the runtime
from an arbitrary state without executing enter actions.
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


def build_state_machine(dsl_code: str):
    """Helper to build state machine from DSL code."""
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestHotStartLeafState:
    """Test hot start from leaf stoppable states."""

    def test_hot_start_from_leaf_state_string_path(self):
        """Test hot start from leaf state using string path."""
        dsl_code = '''
def int counter = 0;
state System {
    state Idle {
        during { counter = counter + 1; }
    }
    state Active {
        during { counter = counter + 10; }
    }
    [*] -> Idle;
    Idle -> Active :: Start;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="System.Active",
            initial_vars={"counter": 0}
        )

        # Should start from Active state
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 0
        assert runtime._initialized is True

        # First cycle should execute Active's during
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 10

        # Multiple cycles
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 20
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 30

    def test_hot_start_from_leaf_state_tuple_path(self):
        """Test hot start from leaf state using tuple path."""
        dsl_code = '''
def int counter = 0;
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
        runtime = SimulationRuntime(
            sm,
            initial_state=('System', 'Active'),
            initial_vars={"counter": 0}
        )

        assert runtime.current_state.path == ('System', 'Active')
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 10
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 20

    def test_hot_start_from_leaf_state_with_vars(self):
        """Test hot start with variable overrides."""
        dsl_code = '''
def int counter = 0;
def int flag = 0;
state System {
    state Active {
        during { counter = counter + flag; }
    }
    [*] -> Active;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="System.Active",
            initial_vars={"counter": 10, "flag": 5}
        )

        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 10
        assert runtime.vars['flag'] == 5

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 15
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 20
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 25

    def test_initial_vars_requires_all_variables(self):
        """Test that initial_vars must provide all variables."""
        dsl_code = '''
def int x = 1;
def int y = 2;
def int z = 3;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        # Missing y - should fail
        with pytest.raises(ValueError, match="initial_vars must provide all variables"):
            SimulationRuntime(
                sm,
                initial_state="Root.A",
                initial_vars={"x": 10, "z": 30}
            )

    def test_initial_vars_without_initial_state(self):
        """Test that initial_vars works without initial_state."""
        dsl_code = '''
def int x = 1;
def int y = 2;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_vars={"x": 10, "y": 20}
        )

        # Variables should be overridden
        assert runtime.vars['x'] == 10
        assert runtime.vars['y'] == 20

        # Should start from root (normal initialization)
        assert runtime.current_state.path == ('Root',)
        assert runtime._initialized is False

        # First cycle should enter A
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')


@pytest.mark.unittest
class TestHotStartCompositeState:
    """Test hot start from composite states."""

    def test_hot_start_from_composite_state_with_init(self):
        """Test hot start from composite state with valid initial transition."""
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state Idle {
            during { counter = counter + 1; }
        }
        state Active {
            during { counter = counter + 10; }
        }
        [*] -> Idle;
    }
    [*] -> System;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.System",
            initial_vars={"counter": 0}
        )

        # Should be in System with init_wait mode
        assert runtime.current_state.path == ('Root', 'System')
        assert runtime.stack[-1].mode == 'init_wait'

        # First cycle should trigger initial transition to Idle
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'Idle')
        assert runtime.vars['counter'] == 1

        # Multiple cycles
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'Idle')
        assert runtime.vars['counter'] == 2
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'Idle')
        assert runtime.vars['counter'] == 3

    def test_hot_start_from_composite_state_no_init(self):
        """Test hot start from composite state without initial transition."""
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state Idle;
        state Dummy;
        [*] -> Dummy;  # Add initial transition to satisfy syntax
        # But we'll hot start to System, not use this transition
    }
    [*] -> System;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.System",
            initial_vars={"counter": 0}
        )

        # Should be in System with init_wait mode
        assert runtime.current_state.path == ('Root', 'System')

        # First cycle should trigger initial transition to Dummy
        runtime.cycle()

        # Should enter Dummy (the initial transition target)
        assert runtime.current_state.path == ('Root', 'System', 'Dummy')


@pytest.mark.unittest
class TestHotStartPseudoState:
    """Test hot start from pseudo states."""

    def test_hot_start_from_pseudo_state(self):
        """Test hot start from pseudo state with valid transition."""
        dsl_code = '''
def int counter = 0;
state Root {
    pseudo state Init;
    state Ready {
        during { counter = counter + 1; }
    }
    [*] -> Init;
    Init -> Ready;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.Init",
            initial_vars={"counter": 0}
        )

        # Should start from Init (pseudo state)
        assert runtime.current_state.path == ('Root', 'Init')
        assert runtime.current_state.is_pseudo is True

        # First cycle should transition to Ready
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Ready')
        assert runtime.vars['counter'] == 1

        # Multiple cycles
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Ready')
        assert runtime.vars['counter'] == 2


@pytest.mark.unittest
class TestHotStartErrorHandling:
    """Test error handling in hot start."""

    def test_invalid_state_path_root_mismatch(self):
        """Test error when root state name doesn't match."""
        dsl_code = '''
def int counter = 0;
state System {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="State path root 'Root' does not match"):
            SimulationRuntime(
                sm,
                initial_state="Root.A",
                initial_vars={"counter": 0}
            )

    def test_invalid_state_path_not_found(self):
        """Test error when state doesn't exist."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="State 'B' not found"):
            SimulationRuntime(
                sm,
                initial_state="Root.B",
                initial_vars={"counter": 0}
            )

    def test_invalid_state_path_empty(self):
        """Test error with empty state path."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="State path cannot be empty"):
            SimulationRuntime(
                sm,
                initial_state="",
                initial_vars={"counter": 0}
            )

    def test_initial_state_requires_initial_vars(self):
        """Test that initial_state requires initial_vars."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="initial_vars must be provided when initial_state is specified"):
            SimulationRuntime(sm, initial_state="Root.A")

    def test_invalid_variable_name(self):
        """Test error when variable doesn't exist."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="Variable 'invalid' not defined"):
            SimulationRuntime(
                sm,
                initial_state="Root.A",
                initial_vars={"counter": 0, "invalid": 10}
            )

    def test_invalid_variable_type_int_float(self):
        """Test error when assigning non-integer float to int variable."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        with pytest.raises(ValueError, match="is int type, cannot assign float"):
            SimulationRuntime(
                sm,
                initial_state="Root.A",
                initial_vars={"counter": 10.5}
            )

    def test_valid_variable_type_int_from_integer_float(self):
        """Test that integer-valued float can be assigned to int variable."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"counter": 10.0}
        )

        # Should convert to int
        assert runtime.vars['counter'] == 10
        assert isinstance(runtime.vars['counter'], int)

    def test_invalid_state_ref_type(self):
        """Test error with invalid state reference type."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        with pytest.raises(TypeError, match="state_ref must be str, tuple, or State"):
            SimulationRuntime(
                sm,
                initial_state=123,  # type: ignore
                initial_vars={"counter": 0}
            )


@pytest.mark.unittest
class TestHotStartStateObject:
    """Test hot start using State object."""

    def test_hot_start_with_state_object(self):
        """Test hot start using State object directly."""
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
        active_state = sm.root_state.substates['Active']

        runtime = SimulationRuntime(
            sm,
            initial_state=active_state,
            initial_vars={"counter": 0}
        )

        assert runtime.current_state.path == ('System', 'Active')
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 10

    def test_hot_start_with_foreign_state_object(self):
        """Test error when State object doesn't belong to state machine."""
        dsl_code1 = '''
def int counter = 0;
state System1 {
    state A;
    [*] -> A;
}
'''
        dsl_code2 = '''
def int counter = 0;
state System2 {
    state B;
    [*] -> B;
}
'''
        sm1 = build_state_machine(dsl_code1)
        sm2 = build_state_machine(dsl_code2)

        state_from_sm2 = sm2.root_state.substates['B']

        with pytest.raises(ValueError, match="does not belong to this state machine"):
            SimulationRuntime(
                sm1,
                initial_state=state_from_sm2,
                initial_vars={"counter": 0}
            )


@pytest.mark.unittest
class TestHotStartStackStructure:
    """Test that hot start constructs correct stack structure."""

    def test_leaf_state_stack_structure(self):
        """Test stack structure for leaf state hot start."""
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state Active;
        [*] -> Active;
    }
    [*] -> System;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.System.Active",
            initial_vars={"counter": 0}
        )

        # Stack should have 3 frames: Root, System, Active
        assert len(runtime.stack) == 3

        # Root: active (child running)
        assert runtime.stack[0].state.name == 'Root'
        assert runtime.stack[0].mode == 'active'

        # System: active (child running)
        assert runtime.stack[1].state.name == 'System'
        assert runtime.stack[1].mode == 'active'

        # Active: active (leaf state, will execute during on first cycle)
        assert runtime.stack[2].state.name == 'Active'
        assert runtime.stack[2].mode == 'active'

    def test_composite_state_stack_structure(self):
        """Test stack structure for composite state hot start."""
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state Active;
        [*] -> Active;
    }
    [*] -> System;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.System",
            initial_vars={"counter": 0}
        )

        # Stack should have 2 frames: Root, System
        assert len(runtime.stack) == 2

        # Root: active (child running)
        assert runtime.stack[0].state.name == 'Root'
        assert runtime.stack[0].mode == 'active'

        # System: init_wait (composite target, trigger DFS)
        assert runtime.stack[1].state.name == 'System'
        assert runtime.stack[1].mode == 'init_wait'


@pytest.mark.unittest
class TestHotStartIntegration:
    """Integration tests for hot start with cycle execution."""

    def test_hot_start_then_transition(self):
        """Test hot start followed by normal transitions."""
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
    A -> B :: Go;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="System.A",
            initial_vars={"counter": 5}
        )

        # Start from A with counter=5
        assert runtime.current_state.path == ('System', 'A')
        assert runtime.vars['counter'] == 5

        # Cycle in A
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'A')
        assert runtime.vars['counter'] == 6

        # Another cycle in A
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'A')
        assert runtime.vars['counter'] == 7

        # Transition to B
        runtime.cycle(['System.A.Go'])
        assert runtime.current_state.path == ('System', 'B')
        assert runtime.vars['counter'] == 17

        # Multiple cycles in B
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'B')
        assert runtime.vars['counter'] == 27
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'B')
        assert runtime.vars['counter'] == 37

    def test_hot_start_deep_nesting(self):
        """Test hot start with deeply nested states."""
        dsl_code = '''
def int counter = 0;
state Root {
    state L1 {
        state L2 {
            state L3 {
                state Leaf {
                    during { counter = counter + 1; }
                }
                [*] -> Leaf;
            }
            [*] -> L3;
        }
        [*] -> L2;
    }
    [*] -> L1;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.L1.L2.L3.Leaf",
            initial_vars={"counter": 0}
        )

        # Should have 5 frames in stack
        assert len(runtime.stack) == 5
        assert runtime.current_state.path == ('Root', 'L1', 'L2', 'L3', 'Leaf')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'L1', 'L2', 'L3', 'Leaf')
        assert runtime.vars['counter'] == 1
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'L1', 'L2', 'L3', 'Leaf')
        assert runtime.vars['counter'] == 2
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'L1', 'L2', 'L3', 'Leaf')
        assert runtime.vars['counter'] == 3


@pytest.mark.unittest
class TestHotStartComplexExamples:
    """Test hot start with complex real-world examples running multiple cycles."""

    def test_hot_start_water_heater_from_heating(self):
        """Test hot start from water heater Heating state with 10+ cycles."""
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
    Standby -> Standby :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
    Heating -> Standby : if [water_temp >= 60];
    Heating -> Heating :: HotWaterDraw effect {
        water_temp = water_temp - 8;
        draw_count = draw_count + 1;
    };
}
'''
        sm = build_state_machine(dsl_code)
        # Hot start from Heating state with low temperature
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.Heating",
            initial_vars={"water_temp": 52, "draw_count": 0}
        )

        # Should start from Heating
        assert runtime.current_state.path == ('Root', 'Heating')
        assert runtime.vars['water_temp'] == 52
        assert runtime.vars['draw_count'] == 0

        # Cycle 1: Heating, temp increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Heating')
        assert runtime.vars['water_temp'] == 56

        # Cycle 2: Heating, temp increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Heating')
        assert runtime.vars['water_temp'] == 60

        # Cycle 3: Transition to Standby (temp >= 60)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Standby')
        assert runtime.vars['water_temp'] == 59

        # Cycle 4-8: Standby, temp decreases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Standby')
        assert runtime.vars['water_temp'] == 58

        runtime.cycle()
        assert runtime.vars['water_temp'] == 57

        runtime.cycle()
        assert runtime.vars['water_temp'] == 56

        runtime.cycle()
        assert runtime.vars['water_temp'] == 55

        runtime.cycle()
        assert runtime.vars['water_temp'] == 54

        # Cycle 9: Hot water draw event
        runtime.cycle(['Root.Standby.HotWaterDraw'])
        assert runtime.current_state.path == ('Root', 'Standby')
        assert runtime.vars['water_temp'] == 45
        assert runtime.vars['draw_count'] == 1

        # Cycle 10: Transition to Heating (temp <= 50)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Heating')
        assert runtime.vars['water_temp'] == 49

        # Cycle 11-12: Continue heating
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Heating')
        assert runtime.vars['water_temp'] == 53

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Heating')
        assert runtime.vars['water_temp'] == 57

    def test_hot_start_ac_charger_from_charging(self):
        """Test hot start from AC charger Charging state with 10+ cycles."""
        dsl_code = '''
def int soc = 70;
def int sessions = 0;
state Root {
    state Idle;

    state Charging {
        during {
            soc = soc + 10;
        }
    }

    state Complete;

    [*] -> Idle;
    Idle -> Charging :: PlugIn;
    Charging -> Complete : if [soc >= 100];
    Charging -> Idle :: Unplug effect {
        sessions = sessions + 1;
    };
    Complete -> Idle :: Unplug effect {
        sessions = sessions + 1;
    };
}
'''
        sm = build_state_machine(dsl_code)
        # Hot start from Charging state with 85% SOC
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.Charging",
            initial_vars={"soc": 85, "sessions": 0}
        )

        # Should start from Charging
        assert runtime.current_state.path == ('Root', 'Charging')
        assert runtime.vars['soc'] == 85
        assert runtime.vars['sessions'] == 0

        # Cycle 1: Charging, soc increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Charging')
        assert runtime.vars['soc'] == 95

        # Cycle 2: Charging, soc increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Charging')
        assert runtime.vars['soc'] == 105

        # Cycle 3: Transition to Complete (soc >= 100)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Complete')
        assert runtime.vars['soc'] == 105

        # Cycle 4-8: Stay in Complete
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Complete')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Complete')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Complete')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Complete')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Complete')

        # Cycle 9: Unplug event
        runtime.cycle(['Root.Complete.Unplug'])
        assert runtime.current_state.path == ('Root', 'Idle')
        assert runtime.vars['sessions'] == 1

        # Cycle 10-12: Stay in Idle
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Idle')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Idle')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Idle')

    def test_hot_start_elevator_door_from_opening(self):
        """Test hot start from elevator door Opening state with 10+ cycles."""
        dsl_code = '''
def int door_pos = 0;
def int hold = 0;
def int reopen_count = 0;
state Root {
    state Closed {
        during {
            hold = 0;
        }
    }

    state Opening {
        during {
            door_pos = door_pos + 50;
        }
    }

    state Opened {
        during {
            hold = hold + 1;
        }
    }

    state Closing {
        during {
            door_pos = door_pos - 50;
        }
    }

    [*] -> Closed;
    Closed -> Opening :: HallCall effect {
        hold = 0;
    };
    Opening -> Opened : if [door_pos >= 100] effect {
        hold = 0;
    };
    Opened -> Closing : if [hold >= 2];
    Closing -> Opened :: BeamBlocked effect {
        reopen_count = reopen_count + 1;
        door_pos = 100;
        hold = 0;
    };
    Closing -> Closed : if [door_pos <= 0] effect {
        hold = 0;
    };
}
'''
        sm = build_state_machine(dsl_code)
        # Hot start from Opening state with door partially open
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.Opening",
            initial_vars={"door_pos": 50, "hold": 0, "reopen_count": 0}
        )

        # Should start from Opening
        assert runtime.current_state.path == ('Root', 'Opening')
        assert runtime.vars['door_pos'] == 50

        # Cycle 1: Opening, door_pos increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Opening')
        assert runtime.vars['door_pos'] == 100

        # Cycle 2: Transition to Opened (door_pos >= 100)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Opened')
        assert runtime.vars['hold'] == 1

        # Cycle 3: Opened, hold increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Opened')
        assert runtime.vars['hold'] == 2

        # Cycle 4: Transition to Closing (hold >= 2)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Closing')
        assert runtime.vars['door_pos'] == 50

        # Cycle 5: Closing, door_pos decreases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Closing')
        assert runtime.vars['door_pos'] == 0

        # Cycle 6: Transition to Closed (door_pos <= 0)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Closed')
        assert runtime.vars['hold'] == 0

        # Cycle 7-9: Stay in Closed
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Closed')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Closed')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Closed')

        # Cycle 10: HallCall event
        runtime.cycle(['Root.Closed.HallCall'])
        assert runtime.current_state.path == ('Root', 'Opening')
        assert runtime.vars['door_pos'] == 50

        # Cycle 11-12: Continue opening
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Opening')
        assert runtime.vars['door_pos'] == 100

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'Opened')
        assert runtime.vars['hold'] == 1

    def test_hot_start_ats_from_starting_gen(self):
        """Test hot start from ATS StartingGen state with 10+ cycles."""
        dsl_code = '''
def int warmup = 0;
def int transfer_count = 0;
state Root {
    state OnMains {
        during {
            warmup = 0;
        }
    }

    state StartingGen {
        during {
            warmup = warmup + 1;
        }
    }

    state OnGenerator;

    [*] -> OnMains;
    OnMains -> StartingGen :: GridFail effect {
        warmup = 0;
    };
    StartingGen -> OnGenerator : if [warmup >= 2] effect {
        transfer_count = transfer_count + 1;
    };
    OnGenerator -> OnMains :: GridRestore effect {
        transfer_count = transfer_count + 1;
        warmup = 0;
    };
}
'''
        sm = build_state_machine(dsl_code)
        # Hot start from StartingGen state with warmup in progress
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.StartingGen",
            initial_vars={"warmup": 1, "transfer_count": 0}
        )

        # Should start from StartingGen
        assert runtime.current_state.path == ('Root', 'StartingGen')
        assert runtime.vars['warmup'] == 1
        assert runtime.vars['transfer_count'] == 0

        # Cycle 1: StartingGen, warmup increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'StartingGen')
        assert runtime.vars['warmup'] == 2

        # Cycle 2: Transition to OnGenerator (warmup >= 2)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnGenerator')
        assert runtime.vars['transfer_count'] == 1

        # Cycle 3-7: Stay in OnGenerator
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnGenerator')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnGenerator')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnGenerator')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnGenerator')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnGenerator')

        # Cycle 8: GridRestore event
        runtime.cycle(['Root.OnGenerator.GridRestore'])
        assert runtime.current_state.path == ('Root', 'OnMains')
        assert runtime.vars['transfer_count'] == 2
        assert runtime.vars['warmup'] == 0

        # Cycle 9-12: Stay in OnMains
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnMains')
        assert runtime.vars['warmup'] == 0

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnMains')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnMains')

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'OnMains')

    def test_hot_start_traffic_signal_from_ped_phase(self):
        """Test hot start from traffic signal PedestrianPhase composite state with 10+ cycles."""
        dsl_code = '''
def int green_ticks = 0;
def int request_latched = 0;
def int yellow_ticks = 0;
def int walk_ticks = 0;
state Root {
    state MainGreen {
        during {
            green_ticks = green_ticks + 1;
        }
    }

    state PedestrianPhase {
        state MainYellow {
            during {
                yellow_ticks = yellow_ticks + 1;
            }
        }

        state PedWalk {
            during {
                walk_ticks = walk_ticks + 1;
            }
        }

        [*] -> MainYellow;
        MainYellow -> PedWalk : if [yellow_ticks >= 1];
        PedWalk -> [*] : if [walk_ticks >= 2];
    }

    [*] -> MainGreen;
    MainGreen -> PedestrianPhase : if [request_latched == 1 && green_ticks >= 3] effect {
        request_latched = 0;
        yellow_ticks = 0;
        walk_ticks = 0;
    };
    MainGreen -> MainGreen :: PedRequest effect {
        request_latched = 1;
    };
    PedestrianPhase -> MainGreen effect {
        green_ticks = 0;
        yellow_ticks = 0;
        walk_ticks = 0;
    };
}
'''
        sm = build_state_machine(dsl_code)
        # Hot start from PedestrianPhase composite state
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.PedestrianPhase",
            initial_vars={
                "green_ticks": 0,
                "request_latched": 0,
                "yellow_ticks": 0,
                "walk_ticks": 0
            }
        )

        # Should start from PedestrianPhase with init_wait mode
        assert runtime.current_state.path == ('Root', 'PedestrianPhase')
        assert runtime.stack[-1].mode == 'init_wait'

        # Cycle 1: Trigger initial transition to MainYellow
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'PedestrianPhase', 'MainYellow')
        assert runtime.vars['yellow_ticks'] == 1

        # Cycle 2: Transition to PedWalk (yellow_ticks >= 1)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'PedestrianPhase', 'PedWalk')
        assert runtime.vars['walk_ticks'] == 1

        # Cycle 3: PedWalk, walk_ticks increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'PedestrianPhase', 'PedWalk')
        assert runtime.vars['walk_ticks'] == 2

        # Cycle 4: Exit PedestrianPhase (walk_ticks >= 2), transition to MainGreen
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'MainGreen')
        assert runtime.vars['green_ticks'] == 1
        assert runtime.vars['yellow_ticks'] == 0
        assert runtime.vars['walk_ticks'] == 0

        # Cycle 5-7: MainGreen, green_ticks increases
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'MainGreen')
        assert runtime.vars['green_ticks'] == 2

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'MainGreen')
        assert runtime.vars['green_ticks'] == 3

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'MainGreen')
        assert runtime.vars['green_ticks'] == 4

        # Cycle 8: PedRequest event
        runtime.cycle(['Root.MainGreen.PedRequest'])
        assert runtime.current_state.path == ('Root', 'MainGreen')
        assert runtime.vars['request_latched'] == 1
        assert runtime.vars['green_ticks'] == 5

        # Cycle 9: Transition to PedestrianPhase (request_latched == 1 && green_ticks >= 3)
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'PedestrianPhase', 'MainYellow')
        assert runtime.vars['request_latched'] == 0
        assert runtime.vars['yellow_ticks'] == 1

        # Cycle 10-12: Continue through pedestrian phase
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'PedestrianPhase', 'PedWalk')
        assert runtime.vars['walk_ticks'] == 1

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'PedestrianPhase', 'PedWalk')
        assert runtime.vars['walk_ticks'] == 2

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'MainGreen')
        assert runtime.vars['green_ticks'] == 1


@pytest.mark.unittest
class TestHotStartWithLifecycleActions:
    """Test hot start with enter/exit/during/aspect actions."""

    def test_hot_start_skips_enter_actions(self):
        """Test that hot start skips enter actions."""
        dsl_code = '''
def int enter_count = 0;
def int during_count = 0;
state Root {
    state A {
        enter { enter_count = enter_count + 1; }
        during { during_count = during_count + 1; }
    }
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"enter_count": 0, "during_count": 0}
        )

        # enter_count should still be 0 (enter action not executed)
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['enter_count'] == 0
        assert runtime.vars['during_count'] == 0

        # First cycle executes during action
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['enter_count'] == 0  # Still 0
        assert runtime.vars['during_count'] == 1

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['enter_count'] == 0
        assert runtime.vars['during_count'] == 2

        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['enter_count'] == 0
        assert runtime.vars['during_count'] == 3

    def test_hot_start_with_aspect_actions(self):
        """Test hot start with aspect actions (>> during before/after)."""
        dsl_code = '''
def int before_count = 0;
def int during_count = 0;
def int after_count = 0;
state Root {
    >> during before {
        before_count = before_count + 1;
    }

    >> during after {
        after_count = after_count + 1;
    }

    state A {
        during { during_count = during_count + 1; }
    }

    state B {
        during { during_count = during_count + 10; }
    }

    [*] -> A;
    A -> B :: Go;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"before_count": 0, "during_count": 0, "after_count": 0}
        )

        # Initial state check
        assert runtime.current_state.path == ('Root', 'A')

        # First cycle: aspect before -> during -> aspect after
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['before_count'] == 1
        assert runtime.vars['during_count'] == 1
        assert runtime.vars['after_count'] == 1

        # Second cycle
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['before_count'] == 2
        assert runtime.vars['during_count'] == 2
        assert runtime.vars['after_count'] == 2

        # Third cycle
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['before_count'] == 3
        assert runtime.vars['during_count'] == 3
        assert runtime.vars['after_count'] == 3

        # Transition to B
        runtime.cycle(['Root.A.Go'])
        assert runtime.current_state.path == ('Root', 'B')
        assert runtime.vars['before_count'] == 4
        assert runtime.vars['during_count'] == 13  # 3 + 10
        assert runtime.vars['after_count'] == 4

        # Multiple cycles in B
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'B')
        assert runtime.vars['before_count'] == 5
        assert runtime.vars['during_count'] == 23
        assert runtime.vars['after_count'] == 5

    def test_hot_start_with_composite_during_before_after(self):
        """Test hot start with composite state during before/after."""
        dsl_code = '''
def int enter_count = 0;
def int during_count = 0;
def int exit_count = 0;
state Root {
    state System {
        enter { enter_count = enter_count + 1; }
        exit { exit_count = exit_count + 1; }

        state A {
            during { during_count = during_count + 1; }
        }

        state B {
            during { during_count = during_count + 10; }
        }

        [*] -> A;
        A -> B :: Go;
    }
    [*] -> System;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.System.A",
            initial_vars={
                "enter_count": 0,
                "during_count": 0,
                "exit_count": 0
            }
        )

        # Hot start skips enter action
        assert runtime.current_state.path == ('Root', 'System', 'A')
        assert runtime.vars['enter_count'] == 0

        # First cycle in A
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'A')
        assert runtime.vars['during_count'] == 1

        # Second cycle in A
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'A')
        assert runtime.vars['during_count'] == 2

        # Transition A -> B (child-to-child)
        runtime.cycle(['Root.System.A.Go'])
        assert runtime.current_state.path == ('Root', 'System', 'B')
        assert runtime.vars['during_count'] == 12  # 2 + 10

        # Multiple cycles in B
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'B')
        assert runtime.vars['during_count'] == 22
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'B')
        assert runtime.vars['during_count'] == 32

    def test_hot_start_with_nested_aspect_actions(self):
        """Test hot start with nested aspect actions."""
        dsl_code = '''
def int root_before = 0;
def int root_after = 0;
def int system_before = 0;
def int system_after = 0;
def int during_count = 0;
state Root {
    >> during before {
        root_before = root_before + 1;
    }

    >> during after {
        root_after = root_after + 1;
    }

    state System {
        >> during before {
            system_before = system_before + 1;
        }

        >> during after {
            system_after = system_after + 1;
        }

        state A {
            during { during_count = during_count + 1; }
        }

        [*] -> A;
    }

    [*] -> System;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.System.A",
            initial_vars={
                "root_before": 0,
                "root_after": 0,
                "system_before": 0,
                "system_after": 0,
                "during_count": 0
            }
        )

        # Initial state check
        assert runtime.current_state.path == ('Root', 'System', 'A')

        # First cycle: all aspect actions execute
        # Order: root_before -> system_before -> during -> system_after -> root_after
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'A')
        assert runtime.vars['root_before'] == 1
        assert runtime.vars['system_before'] == 1
        assert runtime.vars['during_count'] == 1
        assert runtime.vars['system_after'] == 1
        assert runtime.vars['root_after'] == 1

        # Second cycle
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'A')
        assert runtime.vars['root_before'] == 2
        assert runtime.vars['system_before'] == 2
        assert runtime.vars['during_count'] == 2
        assert runtime.vars['system_after'] == 2
        assert runtime.vars['root_after'] == 2

        # Third cycle
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'System', 'A')
        assert runtime.vars['root_before'] == 3
        assert runtime.vars['system_before'] == 3
        assert runtime.vars['during_count'] == 3
        assert runtime.vars['system_after'] == 3
        assert runtime.vars['root_after'] == 3

    def test_hot_start_with_exit_actions(self):
        """Test that exit actions execute normally after hot start."""
        dsl_code = '''
def int exit_a = 0;
def int exit_b = 0;
def int enter_b = 0;
state Root {
    state A {
        exit { exit_a = exit_a + 1; }
    }

    state B {
        enter { enter_b = enter_b + 1; }
        exit { exit_b = exit_b + 1; }
    }

    [*] -> A;
    A -> B :: Go;
    B -> [*] :: Exit;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"exit_a": 0, "exit_b": 0, "enter_b": 0}
        )

        # Initial state check
        assert runtime.current_state.path == ('Root', 'A')

        # Transition A -> B (exit_a should execute, enter_b should execute)
        runtime.cycle(['Root.A.Go'])
        assert runtime.current_state.path == ('Root', 'B')
        assert runtime.vars['exit_a'] == 1
        assert runtime.vars['enter_b'] == 1
        assert runtime.vars['exit_b'] == 0

        # Cycle in B
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'B')
        assert runtime.vars['exit_a'] == 1
        assert runtime.vars['enter_b'] == 1
        assert runtime.vars['exit_b'] == 0

        # Exit from B (exit_b should execute)
        runtime.cycle(['Root.B.Exit'])
        assert runtime.vars['exit_b'] == 1

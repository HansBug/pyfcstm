"""
Edge case and performance tests for hot start functionality.

This module tests boundary conditions, performance, and edge cases
for the hot start feature.
"""

import pytest
import time

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


def build_state_machine(dsl_code: str):
    """Helper to build state machine from DSL code."""
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    return parse_dsl_node_to_state_machine(ast)


@pytest.mark.unittest
class TestHotStartEdgeCases:
    """Test edge cases and boundary conditions."""

    def test_hot_start_from_root_state(self):
        """Test hot start from root state."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during { counter = counter + 1; }
    }
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root",
            initial_vars={"counter": 0}
        )

        # Should be at root with init_wait mode
        assert runtime.current_state.path == ('Root',)
        assert runtime.stack[-1].mode == 'init_wait'

        # First cycle should trigger initial transition
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['counter'] == 1

    def test_hot_start_deeply_nested_state(self):
        """Test hot start with deeply nested states (10+ levels)."""
        # Build a 10-level deep state machine
        dsl_code = '''
def int counter = 0;
state L0 {
    state L1 {
        state L2 {
            state L3 {
                state L4 {
                    state L5 {
                        state L6 {
                            state L7 {
                                state L8 {
                                    state L9 {
                                        state Leaf {
                                            during { counter = counter + 1; }
                                        }
                                        [*] -> Leaf;
                                    }
                                    [*] -> L9;
                                }
                                [*] -> L8;
                            }
                            [*] -> L7;
                        }
                        [*] -> L6;
                    }
                    [*] -> L5;
                }
                [*] -> L4;
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
            initial_state="L0.L1.L2.L3.L4.L5.L6.L7.L8.L9.Leaf",
            initial_vars={"counter": 0}
        )

        # Should have 11 frames in stack (L0 through Leaf)
        assert len(runtime.stack) == 11
        assert runtime.current_state.path == ('L0', 'L1', 'L2', 'L3', 'L4', 'L5', 'L6', 'L7', 'L8', 'L9', 'Leaf')

        # Execute cycles
        runtime.cycle()
        assert runtime.vars['counter'] == 1

        runtime.cycle()
        assert runtime.vars['counter'] == 2

    def test_hot_start_with_many_variables(self):
        """Test hot start with many variables (50+)."""
        # Generate DSL with 50 variables
        var_defs = '\n'.join([f'def int var{i} = {i};' for i in range(50)])
        dsl_code = f'''
{var_defs}
state Root {{
    state A;
    [*] -> A;
}}
'''
        sm = build_state_machine(dsl_code)

        # Create initial_vars dict with all 50 variables
        initial_vars = {f'var{i}': i * 10 for i in range(50)}

        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars=initial_vars
        )

        # Verify all variables are set correctly
        for i in range(50):
            assert runtime.vars[f'var{i}'] == i * 10

    def test_hot_start_with_zero_values(self):
        """Test hot start with all zero values."""
        dsl_code = '''
def int x = 10;
def int y = 20;
def float z = 30.5;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"x": 0, "y": 0, "z": 0.0}
        )

        assert runtime.vars['x'] == 0
        assert runtime.vars['y'] == 0
        assert runtime.vars['z'] == 0.0

    def test_hot_start_with_negative_values(self):
        """Test hot start with negative values."""
        dsl_code = '''
def int x = 0;
def float y = 0.0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"x": -100, "y": -25.5}
        )

        assert runtime.vars['x'] == -100
        assert runtime.vars['y'] == -25.5

    def test_hot_start_with_large_values(self):
        """Test hot start with very large values."""
        dsl_code = '''
def int big_int = 0;
def float big_float = 0.0;
state Root {
    state A;
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"big_int": 2**31 - 1, "big_float": 1e308}
        )

        assert runtime.vars['big_int'] == 2**31 - 1
        assert runtime.vars['big_float'] == 1e308

    def test_hot_start_state_with_special_characters_in_name(self):
        """Test hot start with state names containing underscores."""
        dsl_code = '''
def int counter = 0;
state Root {
    state State_With_Underscores {
        during { counter = counter + 1; }
    }
    [*] -> State_With_Underscores;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.State_With_Underscores",
            initial_vars={"counter": 0}
        )

        assert runtime.current_state.path == ('Root', 'State_With_Underscores')
        runtime.cycle()
        assert runtime.vars['counter'] == 1

    def test_hot_start_then_immediate_transition(self):
        """Test hot start followed by immediate transition."""
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
            initial_vars={"counter": 0}
        )

        # Immediately trigger transition
        runtime.cycle(['System.A.Go'])
        assert runtime.current_state.path == ('System', 'B')
        assert runtime.vars['counter'] == 10

    def test_hot_start_with_guard_condition_immediately_true(self):
        """Test hot start where guard condition is immediately true."""
        dsl_code = '''
def int counter = 100;
state System {
    state A {
        during { counter = counter + 1; }
    }
    state B {
        during { counter = counter + 10; }
    }
    [*] -> A;
    A -> B : if [counter >= 100];
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="System.A",
            initial_vars={"counter": 100}
        )

        # First cycle should trigger automatic transition
        runtime.cycle()
        assert runtime.current_state.path == ('System', 'B')
        assert runtime.vars['counter'] == 110


@pytest.mark.unittest
class TestHotStartPerformance:
    """Performance tests for hot start functionality."""

    def test_hot_start_performance_vs_default(self):
        """Compare hot start performance vs default initialization."""
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

        # Measure default initialization time
        start_time = time.time()
        for _ in range(100):
            runtime = SimulationRuntime(sm)
            runtime.cycle()  # Reach leaf state
        default_time = time.time() - start_time

        # Measure hot start time
        start_time = time.time()
        for _ in range(100):
            runtime = SimulationRuntime(
                sm,
                initial_state="Root.L1.L2.L3.Leaf",
                initial_vars={"counter": 0}
            )
            runtime.cycle()  # Already at leaf state
        hot_start_time = time.time() - start_time

        # Hot start should be faster or comparable
        # (Allow some variance due to system load)
        assert hot_start_time < default_time * 1.5

    def test_hot_start_with_many_cycles(self):
        """Test hot start followed by many cycles."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during { counter = counter + 1; }
    }
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_state="Root.A",
            initial_vars={"counter": 0}
        )

        # Execute 1000 cycles
        start_time = time.time()
        for _ in range(1000):
            runtime.cycle()
        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (< 1 second)
        assert elapsed_time < 1.0
        assert runtime.vars['counter'] == 1000

    def test_hot_start_repeated_initialization(self):
        """Test repeated hot start initialization performance."""
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

        # Create 1000 runtime instances with hot start
        start_time = time.time()
        for i in range(1000):
            runtime = SimulationRuntime(
                sm,
                initial_state="System.A" if i % 2 == 0 else "System.B",
                initial_vars={"counter": i}
            )
        elapsed_time = time.time() - start_time

        # Should complete in reasonable time (< 2 seconds)
        assert elapsed_time < 2.0


@pytest.mark.unittest
class TestHotStartRobustness:
    """Robustness tests for hot start functionality."""

    def test_hot_start_preserves_state_machine_integrity(self):
        """Test that hot start doesn't modify the state machine model."""
        dsl_code = '''
def int counter = 0;
state System {
    state A {
        during { counter = counter + 1; }
    }
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        # Store original state machine properties
        original_root_name = sm.root_state.name
        original_var_count = len(sm.defines)

        # Create multiple runtimes with hot start
        for i in range(10):
            runtime = SimulationRuntime(
                sm,
                initial_state="System.A",
                initial_vars={"counter": i * 10}
            )
            runtime.cycle()

        # Verify state machine is unchanged
        assert sm.root_state.name == original_root_name
        assert len(sm.defines) == original_var_count

    def test_hot_start_multiple_runtimes_independent(self):
        """Test that multiple hot start runtimes are independent."""
        dsl_code = '''
def int counter = 0;
state System {
    state A {
        during { counter = counter + 1; }
    }
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)

        # Create multiple runtimes with different initial values
        runtime1 = SimulationRuntime(
            sm,
            initial_state="System.A",
            initial_vars={"counter": 10}
        )
        runtime2 = SimulationRuntime(
            sm,
            initial_state="System.A",
            initial_vars={"counter": 100}
        )

        # Execute cycles independently
        runtime1.cycle()
        runtime2.cycle()

        # Verify independence
        assert runtime1.vars['counter'] == 11
        assert runtime2.vars['counter'] == 101

        runtime1.cycle()
        assert runtime1.vars['counter'] == 12
        assert runtime2.vars['counter'] == 101  # Unchanged

    def test_hot_start_with_initial_vars_only(self):
        """Test using initial_vars without initial_state."""
        dsl_code = '''
def int x = 1;
def int y = 2;
state Root {
    state A {
        during { x = x + y; }
    }
    [*] -> A;
}
'''
        sm = build_state_machine(dsl_code)
        runtime = SimulationRuntime(
            sm,
            initial_vars={"x": 10, "y": 20}
        )

        # Should start from root (normal initialization)
        assert runtime.current_state.path == ('Root',)
        assert runtime.vars['x'] == 10
        assert runtime.vars['y'] == 20

        # First cycle should enter A
        runtime.cycle()
        assert runtime.current_state.path == ('Root', 'A')
        assert runtime.vars['x'] == 30

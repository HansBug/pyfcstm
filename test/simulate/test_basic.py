import pytest
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


@pytest.mark.unittest
class TestSimulationWithSamples:
    """Test simulation using actual sample files."""

    def test_dlc1_traffic_light(self):
        """Test the traffic light example from dlc1.fcstm."""
        with open('test/testfile/sample_codes/dlc1.fcstm', 'r') as f:
            dsl_code = f.read()

        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Initial cycle - should enter InService and then Red
        runtime.cycle()
        assert runtime.current_state.name == 'Red'
        assert runtime.vars['a'] == 0
        assert runtime.vars['b'] == 1
        assert runtime.vars['round_count'] == 0

        # During cycle in Red - should execute during action
        runtime.cycle()
        assert runtime.vars['a'] == 0x4  # 0x1 << 2
        assert runtime.current_state.name == 'Red'

        # Transition Red -> Green
        runtime.cycle()
        assert runtime.current_state.name == 'Green'
        assert runtime.vars['b'] == 0x3

        # Transition Green -> Yellow
        runtime.cycle()
        assert runtime.current_state.name == 'Yellow'
        assert runtime.vars['b'] == 0x2

    def test_dlc6_simplest(self):
        """Test the simplest example from dlc6_simplest.fcstm."""
        with open('test/testfile/sample_codes/dlc6_simplest.fcstm', 'r') as f:
            dsl_code = f.read()

        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Should be able to create runtime without errors
        assert not runtime.is_ended
        runtime.cycle()
        assert not runtime.is_ended


@pytest.mark.unittest
class TestBasicFeatures:
    """Test basic simulation features."""

    def test_simple_transition(self):
        """Test simple state transition."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        enter {
            counter = 1;
        }
    }
    state B {
        enter {
            counter = 2;
        }
    }
    [*] -> A;
    A -> B :: Go;
}
'''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['counter'] == 1
        assert runtime.current_state.name == 'A'

        runtime.cycle(['Root.A.Go'])
        assert runtime.vars['counter'] == 2
        assert runtime.current_state.name == 'B'

    def test_guard_condition(self):
        """Test guard conditions."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }
    state B;
    [*] -> A;
    A -> B : if [counter >= 3];
}
'''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['counter'] == 1
        assert runtime.current_state.name == 'A'

        runtime.cycle()
        assert runtime.vars['counter'] == 2
        assert runtime.current_state.name == 'A'

        runtime.cycle()
        assert runtime.vars['counter'] == 3
        assert runtime.current_state.name == 'B'

    def test_transition_effects(self):
        """Test transition effects."""
        dsl_code = '''
def int a = 0;
def int b = 0;
state Root {
    state A;
    state B;
    [*] -> A;
    A -> B :: Go effect {
        a = 10;
        b = 20;
    };
}
'''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['a'] == 0
        assert runtime.vars['b'] == 0

        runtime.cycle(['Root.A.Go'])
        assert runtime.vars['a'] == 10
        assert runtime.vars['b'] == 20

    def test_exit_state(self):
        """Test exiting to parent state."""
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        enter {
            counter = 1;
        }
        exit {
            counter = 10;
        }
    }
    [*] -> A;
    A -> [*];
}
'''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['counter'] == 1

        runtime.cycle()
        assert runtime.vars['counter'] == 10
        assert runtime.is_ended

    def test_lifecycle_actions(self):
        """Test enter/during/exit actions."""
        dsl_code = '''
def int a = 0;
state Root {
    enter {
        a = 1;
    }
    state S {
        enter {
            a = a + 10;
        }
        during {
            a = a + 100;
        }
        exit {
            a = a + 1000;
        }
    }
    [*] -> S;
    S -> [*] :: Done;
}
'''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['a'] == 111  # Root.enter (1) + S.enter (10) + S.during (100)

        runtime.cycle(['Root.S.Done'])
        assert runtime.vars['a'] == 1111  # + S.exit (1000)
        assert runtime.is_ended

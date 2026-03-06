import pytest
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


@pytest.mark.unittest
class TestSimulationBasics:
    """Test basic simulation functionality."""

    def test_simple_state_machine(self):
        """Test a simple state machine with two states."""
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

        # Initial state
        assert runtime.vars['counter'] == 0
        assert not runtime.is_ended

        # Enter A
        runtime.cycle()
        assert runtime.vars['counter'] == 1
        assert runtime.current_state.name == 'A'

        # Transition to B
        runtime.cycle(['Root.A.Go'])
        assert runtime.vars['counter'] == 2
        assert runtime.current_state.name == 'B'

    def test_variable_initialization(self):
        """Test variable initialization."""
        dsl_code = '''
        def int a = 10;
        def int b = 0xFF;
        def float c = 3.14;
        state Root {
            state S;
            [*] -> S;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        assert runtime.vars['a'] == 10
        assert runtime.vars['b'] == 0xFF
        assert runtime.vars['c'] == 3.14

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


@pytest.mark.unittest
class TestLifecycleActions:
    """Test lifecycle actions (enter/during/exit)."""

    def test_enter_actions(self):
        """Test enter actions."""
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
            }
            [*] -> S;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['a'] == 11  # Root enter (1) + S enter (+10)

    def test_during_actions(self):
        """Test during actions for leaf states."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state A {
                during {
                    counter = counter + 1;
                }
            }
            [*] -> A;
            A -> [*] : if [counter >= 3];
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['counter'] == 1

        runtime.cycle()
        assert runtime.vars['counter'] == 2

        runtime.cycle()
        assert runtime.vars['counter'] == 3
        assert runtime.is_ended

    def test_exit_actions(self):
        """Test exit actions."""
        dsl_code = '''
        def int a = 0;
        state Root {
            state A {
                exit {
                    a = 100;
                }
            }
            state B;
            [*] -> A;
            A -> B :: Go;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['a'] == 0

        runtime.cycle(['Root.A.Go'])
        assert runtime.vars['a'] == 100


@pytest.mark.unittest
class TestAspectActions:
    """Test aspect-oriented during actions."""

    def test_aspect_before_after(self):
        """Test >> during before/after actions."""
        dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter * 10 + 1;
    }
    >> during after {
        counter = counter * 10 + 3;
    }
    state A {
        during {
            counter = counter * 10 + 2;
        }
    }
    [*] -> A;
    A -> [*] : if [counter >= 100];
}
'''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        # Order: before (1) -> during (2) -> after (3) = 123
        assert runtime.vars['counter'] == 123

    def test_nested_aspect_actions(self):
        """Test nested aspect actions."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            >> during before {
                counter = log * 10 + 1;
            }
            state Sub {
                >> during before {
                    counter = log * 10 + 2;
                }
                state A {
                    during {
                        counter = log * 10 + 3;
                    }
                }
                [*] -> A;
            }
            [*] -> Sub;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        # Order: Root before (1) -> Sub before (2) -> A during (3) = 123
        assert runtime.vars['log'] == 123


@pytest.mark.unittest
class TestCompositeStates:
    """Test composite state behavior."""

    def test_composite_during_before_after(self):
        """Test composite state during before/after timing."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state Composite {
                during before {
                    counter = log * 10 + 1;
                }
                during after {
                    counter = log * 10 + 3;
                }
                state A {
                    enter {
                        counter = log * 10 + 2;
                    }
                }
                [*] -> A;
            }
            [*] -> Composite;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        # Order: Composite.during before (1) -> A.enter (2) = 12
        # during after (3) is NOT executed yet
        assert runtime.vars['log'] == 12

    def test_composite_child_to_child_no_during(self):
        """Test that during before/after are NOT triggered on child-to-child transitions."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state Composite {
                during before {
                    counter = log * 100 + 10;
                }
                during after {
                    counter = log * 100 + 20;
                }
                state A;
                state B;
                [*] -> A;
                A -> B :: Go;
            }
            [*] -> Composite;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['log'] == 10  # Only during before on entry

        # Transition A -> B should NOT trigger during before/after
        runtime.cycle(['Root.Composite.A.Go'])
        assert runtime.vars['log'] == 10  # No change!

    def test_composite_exit_triggers_during_after(self):
        """Test that exiting composite state triggers during after."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state Composite {
                during before {
                    counter = log * 100 + 10;
                }
                during after {
                    counter = log * 100 + 20;
                }
                state A;
                [*] -> A;
            }
            state B;
            [*] -> Composite;
            Composite -> B :: Exit;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['log'] == 10

        runtime.cycle(['Root.Composite.Exit'])
        # during after should execute on exit
        assert runtime.vars['log'] == 1020


@pytest.mark.unittest
class TestTransitions:
    """Test transition behavior."""

    def test_guard_conditions(self):
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
            A -> B : if [counter >= 5];
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.current_state.name == 'A'
        assert runtime.vars['counter'] == 1

        for i in range(2, 5):
            runtime.cycle()
            assert runtime.current_state.name == 'A'
            assert runtime.vars['counter'] == i

        runtime.cycle()
        assert runtime.current_state.name == 'B'
        assert runtime.vars['counter'] == 5

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

    def test_event_scoping_local(self):
        """Test local event scoping (::)."""
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
            A -> B :: E;
            B -> A :: E;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['counter'] == 1

        # Trigger A's local E event
        runtime.cycle(['Root.A.E'])
        assert runtime.vars['counter'] == 2

        # Trigger B's local E event (different from A's E)
        runtime.cycle(['Root.B.E'])
        assert runtime.vars['counter'] == 1

    def test_event_scoping_chain(self):
        """Test chain event scoping (:)."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state Sub {
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
                A -> B : E;
                B -> A : E;
            }
            [*] -> Sub;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['counter'] == 1

        # Both transitions share the same event Root.Sub.E
        runtime.cycle(['Root.Sub.E'])
        assert runtime.vars['counter'] == 2

        runtime.cycle(['Root.Sub.E'])
        assert runtime.vars['counter'] == 1

    def test_event_scoping_absolute(self):
        """Test absolute event scoping (/)."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state Sub1 {
                state A;
                [*] -> A;
                A -> [*] : /GlobalEvent;
            }
            state Sub2 {
                state B;
                [*] -> B;
                B -> [*] : /GlobalEvent;
            }
            [*] -> Sub1;
            Sub1 -> Sub2 :: Next;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.current_state.name == 'A'

        # GlobalEvent should work from any state
        runtime.cycle(['Root.GlobalEvent'])
        assert runtime.current_state.name == 'Sub1'

        runtime.cycle(['Root.Sub1.Next'])
        assert runtime.current_state.name == 'B'

        runtime.cycle(['Root.GlobalEvent'])
        assert runtime.current_state.name == 'Sub2'


@pytest.mark.unittest
class TestPseudoStates:
    """Test pseudo state behavior."""

    def test_pseudo_state_skips_aspects(self):
        """Test that pseudo states skip ancestor aspect actions."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            >> during before {
                counter = log * 10 + 1;
            }
            >> during after {
                counter = log * 10 + 3;
            }
            pseudo state A {
                during {
                    counter = log * 10 + 2;
                }
            }
            [*] -> A;
            A -> [*] : if [counter >= 2];
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        # Pseudo state skips aspect actions, only executes its own during
        assert runtime.vars['log'] == 2


@pytest.mark.unittest
class TestAbstractActions:
    """Test abstract action handling."""

    def test_abstract_actions_logged(self):
        """Test that abstract actions are logged but not executed."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state A {
                enter abstract InitHardware;
                during abstract ProcessData;
                exit abstract Cleanup;
            }
            [*] -> A;
            A -> [*] :: Done;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Should not raise errors
        runtime.cycle()
        runtime.cycle(['Root.A.Done'])
        assert runtime.is_ended


@pytest.mark.unittest
class TestReferenceActions:
    """Test reference action behavior."""

    def test_reference_actions(self):
        """Test reference actions."""
        dsl_code = '''
        def int counter = 0;
        state Root {
            state A {
                enter Init {
                    counter = 10;
                }
            }
            state B {
                enter ref A.Init;
            }
            [*] -> A;
            A -> B :: Go;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        assert runtime.vars['counter'] == 10

        runtime.vars['counter'] = 0
        runtime.cycle(['Root.A.Go'])
        # B's enter should reference A's Init
        assert runtime.vars['counter'] == 10


@pytest.mark.unittest
class TestComplexScenarios:
    """Test complex scenarios from sample files."""

    def test_dlc1_traffic_light(self):
        """Test the traffic light example from dlc1.fcstm."""
        with open('test/testfile/sample_codes/dlc1.fcstm', 'r') as f:
            dsl_code = f.read()

        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        # Initial cycle
        runtime.cycle()
        assert runtime.current_state.name == 'Red'
        assert runtime.vars['a'] == 0
        assert runtime.vars['b'] == 1
        assert runtime.vars['round_count'] == 0

        # During cycle in Red
        runtime.cycle()
        assert runtime.vars['a'] == 0x4  # 0x1 << 2

        # Transition Red -> Green
        runtime.cycle()
        assert runtime.current_state.name == 'Green'
        assert runtime.vars['b'] == 0x3

        # Transition Green -> Yellow
        runtime.cycle()
        assert runtime.current_state.name == 'Yellow'
        assert runtime.vars['b'] == 0x2

    def test_hierarchical_state_machine(self):
        """Test a complex hierarchical state machine."""
        dsl_code = '''
        def int level = 0;
        state Root {
            >> during before {
                level = level + 1;
            }
            state System {
                during before {
                    level = level + 10;
                }
                during after {
                    level = level + 100;
                }
                state Active {
                    during {
                        level = level + 1000;
                    }
                }
                state Idle;
                [*] -> Active;
                Active -> Idle :: Pause;
            }
            [*] -> System;
            System -> [*] :: Stop;
        }
        '''
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)

        runtime.cycle()
        # Root.enter -> System.enter -> System.during before (10) -> Active.enter
        assert runtime.vars['level'] == 10

        runtime.cycle()
        # Root >> during before (1) -> Active.during (1000) = 1001
        assert runtime.vars['level'] == 1011

        runtime.cycle(['Root.System.Active.Pause'])
        # Active -> Idle (no during before/after triggered)
        assert runtime.vars['level'] == 1011

        runtime.cycle(['Root.System.Stop'])
        # System.during after (100) should execute
        assert runtime.vars['level'] == 1111
        assert runtime.is_ended

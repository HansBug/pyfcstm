import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


def build_runtime(dsl_code: str) -> SimulationRuntime:
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    sm = parse_dsl_node_to_state_machine(ast)
    return SimulationRuntime(sm)


def assert_runtime_state(runtime: SimulationRuntime, current_path=None, vars=None, is_ended=False):
    assert runtime.is_ended is is_ended
    if current_path is None:
        assert runtime.is_ended
    else:
        assert runtime.current_state.path == current_path
    if vars is not None:
        for key, value in vars.items():
            assert runtime.vars[key] == value


def run_cycle_and_assert(runtime: SimulationRuntime, events=None, *, current_path=None, vars=None, is_ended=False):
    runtime.cycle(events)
    assert_runtime_state(runtime, current_path=current_path, vars=vars, is_ended=is_ended)


@pytest.mark.unittest
class TestSimulationDesignExamples:
    def test_4_1_basic_simple_transition(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }
    state B {
        during {
            counter = counter + 10;
        }
    }
    [*] -> A;
    A -> B :: Go;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'counter': 12})

    def test_4_2_composite_state(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        state B2 {
            during {
                counter = counter + 100;
            }
        }
        [*] -> B1;
        B1 -> B2 :: Next;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoB'], current_path=('Root', 'B', 'B1'), vars={'counter': 11})
        run_cycle_and_assert(runtime, ['Root.B.B1.Next'], current_path=('Root', 'B', 'B2'), vars={'counter': 111})

    def test_4_3_validation_cannot_reach_stoppable(self):
        dsl_code = '''
def int counter = 0;
def int ready = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1;
        [*] -> B1 : if [ready == 1];
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1, 'ready': 0})
        run_cycle_and_assert(runtime, ['Root.A.GoB'], current_path=('Root', 'A'), vars={'counter': 2, 'ready': 0})

    def test_4_4_validation_init_transition_requires_event(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        [*] -> B1 :: Start;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoB'], current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, ['Root.A.GoB', 'Root.B.Start'], current_path=('Root', 'B', 'B1'),
                             vars={'counter': 12})

    def test_4_5_aspect_actions(self):
        dsl_code = '''
def int trace = 0;
state Root {
    >> during before {
        trace = trace * 10 + 1;
    }
    >> during after {
        trace = trace * 10 + 3;
    }

    state A {
        during {
            trace = trace * 10 + 2;
        }
    }

    [*] -> A;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'trace': 123})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'trace': 123123})

    def test_4_6_pseudo_state(self):
        dsl_code = '''
def int trace = 0;
state Root {
    >> during before {
        trace = trace * 10 + 1;
    }
    >> during after {
        trace = trace * 10 + 3;
    }

    pseudo state A {
        during {
            trace = trace * 10 + 2;
        }
    }

    [*] -> A;
    A -> [*] : if [trace >= 2];
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=None, vars={'trace': 2}, is_ended=True)

    def test_4_7_multi_level_non_stoppable(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        state B1 {
            state B1a {
                during {
                    counter = counter + 10;
                }
            }
            [*] -> B1a;
        }
        [*] -> B1;
    }

    state C {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> B :: GoB;
    A -> C :: GoC;
}
'''
        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoB'], current_path=('Root', 'B', 'B1', 'B1a'), vars={'counter': 11})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoC'], current_path=('Root', 'C'), vars={'counter': 101})

    def test_4_8_transition_priority(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }
    state B {
        during {
            counter = counter + 10;
        }
    }
    state C {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> B : if [counter >= 5];
    A -> C : if [counter >= 3];
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 3})
        run_cycle_and_assert(runtime, current_path=('Root', 'C'), vars={'counter': 103})

    def test_4_9_self_transition(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        enter {
            counter = counter + 1;
        }
        during {
            counter = counter + 10;
        }
        exit {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> A :: Loop;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 11})
        run_cycle_and_assert(runtime, ['Root.A.Loop'], current_path=('Root', 'A'), vars={'counter': 122})

    def test_4_10_exit_state(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
        exit {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> [*] : if [counter >= 3];
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 3})
        run_cycle_and_assert(runtime, current_path=None, vars={'counter': 103}, is_ended=True)

    def test_4_11_guard_effect_multilevel_transition(self):
        dsl_code = '''
def int counter = 0;
def int flag = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        enter {
            flag = 1;
        }
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        [*] -> B1 : if [flag == 1];
    }

    state C {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> B : if [counter >= 3] effect {
        flag = 1;
    };
    A -> C :: GoC;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1, 'flag': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 2, 'flag': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 3, 'flag': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'B', 'B1'), vars={'counter': 13, 'flag': 1})

    def test_4_12_validation_failure_multilevel_transition(self):
        dsl_code = '''
def int counter = 0;
def int flag = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        enter {
            flag = 1;
        }
        state B1 {
            during {
                counter = counter + 10;
            }
        }
        [*] -> B1 : if [flag == 2];
    }

    [*] -> A;
    A -> B : if [counter >= 3] effect {
        flag = 1;
    };
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1, 'flag': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 2, 'flag': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 3, 'flag': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 4, 'flag': 0})

    def test_4_13_single_pseudo_state_chain(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P {
        enter {
            counter = counter + 10;
        }
        during {
            counter = counter + 100;
        }
    }

    state B {
        during {
            counter = counter + 1000;
        }
    }

    [*] -> A;
    A -> P :: GoP;
    P -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoP'], current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, ['Root.A.GoP', 'Root.P.GoB'], current_path=('Root', 'B'), vars={'counter': 1112})

    def test_4_14_multiple_pseudo_states_chain(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P1 {
        enter {
            counter = counter + 10;
        }
    }

    pseudo state P2 {
        enter {
            counter = counter + 100;
        }
    }

    state B {
        during {
            counter = counter + 1000;
        }
    }

    [*] -> A;
    A -> P1 :: Go1;
    P1 -> P2 :: Go2;
    P2 -> B :: Go3;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.Go1'], current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, ['Root.A.Go1', 'Root.P1.Go2'], current_path=('Root', 'A'), vars={'counter': 3})
        run_cycle_and_assert(runtime, ['Root.A.Go1', 'Root.P1.Go2', 'Root.P2.Go3'], current_path=('Root', 'B'),
                             vars={'counter': 1113})

    def test_4_15_pseudo_chain_with_guard(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P {
        enter {
            counter = counter + 10;
        }
    }

    state B {
        during {
            counter = counter + 100;
        }
    }

    [*] -> A;
    A -> P : if [counter >= 3];
    P -> B : if [counter >= 15];
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 3})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 4})
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 5})
        run_cycle_and_assert(runtime, current_path=('Root', 'B'), vars={'counter': 115})

    def test_4_16_pseudo_chain_to_machine_end(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    pseudo state P {
        enter {
            counter = counter + 10;
        }
    }

    [*] -> A;
    A -> P :: GoP;
    P -> [*];
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoP'], current_path=None, vars={'counter': 11}, is_ended=True)

    def test_4_17_exit_to_parent_invalid(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state A {
            during {
                counter = counter + 1;
            }
        }

        pseudo state P {
            enter {
                counter = counter + 10;
            }
        }

        [*] -> A;
        A -> P :: GoP;
        P -> [*];
    }

    [*] -> System;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.System.A.GoP'], current_path=('Root', 'System', 'A'), vars={'counter': 2})

    def test_4_17_1_exit_to_parent_then_event_transition(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state A {
            during {
                counter = counter + 1;
            }
        }

        pseudo state P {
            enter {
                counter = counter + 10;
            }
        }

        [*] -> A;
        A -> P :: GoP;
        P -> [*];
    }

    state B {
        during {
            counter = counter + 100;
        }
    }

    [*] -> System;
    System -> B :: ToB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.System.A.GoP'], current_path=('Root', 'System', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, ['Root.System.A.GoP', 'Root.System.ToB'], current_path=('Root', 'B'),
                             vars={'counter': 112})

    def test_4_17_2_exit_to_parent_then_pseudo_then_guard(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state System {
        state A {
            during {
                counter = counter + 1;
            }
        }

        pseudo state P1 {
            enter {
                counter = counter + 10;
            }
        }

        [*] -> A;
        A -> P1 :: GoP;
        P1 -> [*];
    }

    pseudo state P2 {
        enter {
            counter = counter + 100;
        }
    }

    state B {
        during {
            counter = counter + 1000;
        }
    }

    [*] -> System;
    System -> P2;
    P2 -> B : if [counter >= 115];
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.System.A.GoP'], current_path=('Root', 'System', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 3})
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 4})
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 5})
        run_cycle_and_assert(runtime, ['Root.System.A.GoP'], current_path=('Root', 'B'), vars={'counter': 1115})

    def test_4_18_pseudo_chain_inside_composite(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        pseudo state P1 {
            enter {
                counter = counter + 10;
            }
        }

        pseudo state P2 {
            enter {
                counter = counter + 100;
            }
        }

        state B1 {
            during {
                counter = counter + 1000;
            }
        }

        [*] -> P1;
        P1 -> P2;
        P2 -> B1;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoB'], current_path=('Root', 'B', 'B1'), vars={'counter': 1111})

    def test_4_19_evented_pseudo_chain_invalid_then_valid(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        pseudo state P1 {
            enter {
                counter = counter + 10;
            }
        }

        state B1 {
            during {
                counter = counter + 100;
            }
        }

        [*] -> P1;
        P1 -> B1 :: Event;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoB'], current_path=('Root', 'A'), vars={'counter': 2})
        run_cycle_and_assert(runtime, ['Root.A.GoB', 'Root.B.P1.Event'], current_path=('Root', 'B', 'B1'),
                             vars={'counter': 112})

    def test_4_20_mixed_composite_and_pseudo(self):
        dsl_code = '''
def int counter = 0;
state Root {
    state A {
        during {
            counter = counter + 1;
        }
    }

    state B {
        pseudo state P {
            enter {
                counter = counter + 10;
            }
        }

        state C {
            state C1 {
                during {
                    counter = counter + 100;
                }
            }
            [*] -> C1;
        }

        [*] -> P;
        P -> C;
    }

    [*] -> A;
    A -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoB'], current_path=('Root', 'B', 'C', 'C1'), vars={'counter': 111})

    def test_4_21_single_layer_aspect_actions(self):
        dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 10000;
    }

    state A {
        during {
            counter = counter + 100;
        }
    }

    state B {
        during {
            counter = counter + 1000;
        }
    }

    [*] -> A;
    A -> B :: Go;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 10101})
        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'counter': 21102})

    def test_4_22_multi_layer_aspect_actions(self):
        dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 100000;
    }

    state System {
        >> during before {
            counter = counter + 10;
        }

        >> during after {
            counter = counter + 10000;
        }

        state Module {
            >> during before {
                counter = counter + 100;
            }

            >> during after {
                counter = counter + 1000;
            }

            state Active {
                during {
                    counter = counter + 1;
                }
            }

            [*] -> Active;
        }

        [*] -> Module;
    }

    [*] -> System;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'Module', 'Active'), vars={'counter': 111112})

    def test_4_23_pseudo_state_skips_aspect_actions(self):
        dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 10000;
    }

    state A {
        during {
            counter = counter + 100;
        }
    }

    pseudo state P {
        during {
            counter = counter + 1000;
        }
    }

    state B {
        during {
            counter = counter + 100000;
        }
    }

    [*] -> A;
    A -> P :: GoP;
    P -> B :: GoB;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 10101})
        run_cycle_and_assert(runtime, ['Root.A.GoP', 'Root.P.GoB'], current_path=('Root', 'B'),
                             vars={'counter': 121102})

    def test_4_24_multiple_leaf_states_share_aspects(self):
        dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 1000;
    }

    state System {
        >> during before {
            counter = counter + 10;
        }

        >> during after {
            counter = counter + 100;
        }

        state A {
            during {
                counter = counter + 1;
            }
        }

        state B {
            during {
                counter = counter + 10;
            }
        }

        state C {
            during {
                counter = counter + 100;
            }
        }

        [*] -> A;
        A -> B :: GoB;
        B -> C :: GoC;
    }

    [*] -> System;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1112})
        run_cycle_and_assert(runtime, ['Root.System.A.GoB'], current_path=('Root', 'System', 'B'),
                             vars={'counter': 2233})
        run_cycle_and_assert(runtime, ['Root.System.B.GoC'], current_path=('Root', 'System', 'C'),
                             vars={'counter': 3444})

    def test_4_25_cross_hierarchy_transition_actual_runtime_behavior(self):
        dsl_code = '''
def int counter = 0;
state Root {
    >> during before {
        counter = counter + 1;
    }

    >> during after {
        counter = counter + 100000;
    }

    state System1 {
        >> during before {
            counter = counter + 10;
        }

        >> during after {
            counter = counter + 10000;
        }

        state A {
            during {
                counter = counter + 100;
            }
        }

        [*] -> A;
    }

    state System2 {
        >> during before {
            counter = counter + 1000;
        }

        >> during after {
            counter = counter + 1000000;
        }

        state B {
            during {
                counter = counter + 10000;
            }
        }

        [*] -> B;
    }

    [*] -> System1;
    System1 -> System2 :: Go;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'counter': 110111})
        run_cycle_and_assert(runtime, ['Root.System1.Go'], current_path=('Root', 'System1', 'A'), vars={'counter': 220222})

    def test_4_26_cross_hierarchy_transition_with_staged_guards(self):
        dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    >> during before {
        trace = trace + 1;
    }

    >> during after {
        trace = trace + 100000;
    }

    state System1 {
        >> during before {
            trace = trace + 10;
        }

        >> during after {
            trace = trace + 10000;
        }

        state A {
            during {
                phase = phase + 1;
                trace = trace + 100;
            }
        }

        [*] -> A;
        A -> [*] : if [phase >= 3];
    }

    state System2 {
        >> during before {
            trace = trace + 1000;
        }

        >> during after {
            trace = trace + 1000000;
        }

        state B {
            during {
                trace = trace + 10000;
            }
        }

        [*] -> B : if [phase >= 7];
    }

    [*] -> System1;
    System1 -> System2 : if [phase >= 5];
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'phase': 1, 'trace': 110111})
        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'phase': 2, 'trace': 220222})
        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'phase': 3, 'trace': 330333})
        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'phase': 4, 'trace': 440444})
        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'phase': 5, 'trace': 550555})
        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'phase': 6, 'trace': 660666})
        run_cycle_and_assert(runtime, current_path=('Root', 'System1', 'A'), vars={'phase': 7, 'trace': 770777})
        run_cycle_and_assert(runtime, current_path=('Root', 'System2', 'B'), vars={'phase': 7, 'trace': 1881778})
        run_cycle_and_assert(runtime, current_path=('Root', 'System2', 'B'), vars={'phase': 7, 'trace': 2992779})

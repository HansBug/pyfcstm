import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeDfsError

from ._utils import build_c_runtime


class _DualRuntime:
    def __init__(self, simulation_runtime, generated_runtime, dsl_code):
        self._simulation_runtime = simulation_runtime
        self._generated_runtime = generated_runtime
        self._dsl_code = dsl_code

    def close(self):
        self._generated_runtime.close()

    def _assert_aligned(self, when):
        sim_ended = self._simulation_runtime.is_ended
        gen_ended = self._generated_runtime.is_ended
        assert sim_ended == gen_ended, (
            f'{when}: is_ended mismatch for DSL:\n{self._dsl_code}\n'
            f'simulation={sim_ended!r}, generated={gen_ended!r}'
        )

        sim_vars = dict(self._simulation_runtime.vars)
        gen_vars = dict(self._generated_runtime.vars)
        assert sim_vars == gen_vars, (
            f'{when}: vars mismatch for DSL:\n{self._dsl_code}\n'
            f'simulation={sim_vars!r}\n'
            f'generated={gen_vars!r}'
        )

        if sim_ended:
            assert self._generated_runtime.current_state_path is None, (
                f'{when}: generated runtime should be terminated for DSL:\n{self._dsl_code}'
            )
        else:
            assert self._simulation_runtime.current_state.path == self._generated_runtime.current_state_path, (
                f'{when}: current state mismatch for DSL:\n{self._dsl_code}\n'
                f'simulation={self._simulation_runtime.current_state.path!r}\n'
                f'generated={self._generated_runtime.current_state_path!r}'
            )

        assert self._simulation_runtime.brief_stack == self._generated_runtime.brief_stack, (
            f'{when}: brief_stack mismatch for DSL:\n{self._dsl_code}\n'
            f'simulation={self._simulation_runtime.brief_stack!r}\n'
            f'generated={self._generated_runtime.brief_stack!r}'
        )

    def cycle(self, events=None):
        sim_result = self._simulation_runtime.cycle(events)
        self._generated_runtime.cycle(events)
        self._assert_aligned(f'after cycle(events={events!r})')
        return sim_result

    def cycle_expect_error(self, events=None, match=None):
        sim_error = None
        gen_error = None

        try:
            self._simulation_runtime.cycle(events)
        except Exception as err:  # pragma: no cover
            sim_error = err

        try:
            self._generated_runtime.cycle(events)
        except Exception as err:  # pragma: no cover
            gen_error = err

        assert isinstance(sim_error, SimulationRuntimeDfsError), (
            f'expected SimulationRuntimeDfsError for DSL:\n{self._dsl_code}\n'
            f'got: {sim_error!r}'
        )
        assert isinstance(gen_error, RuntimeError), (
            f'expected RuntimeError from generated runtime for DSL:\n{self._dsl_code}\n'
            f'got: {gen_error!r}'
        )
        if match is not None:
            assert match in str(sim_error)
            assert match in str(gen_error)

        self._assert_aligned(f'after cycle error(events={events!r})')
        return sim_error, gen_error

    @property
    def vars(self):
        self._assert_aligned('vars access')
        return self._simulation_runtime.vars

    @property
    def is_ended(self):
        self._assert_aligned('is_ended access')
        return self._simulation_runtime.is_ended

    @property
    def current_state(self):
        self._assert_aligned('current_state access')
        return self._simulation_runtime.current_state

    @property
    def current_state_path(self):
        self._assert_aligned('current_state_path access')
        return self._generated_runtime.current_state_path

    @property
    def brief_stack(self):
        self._assert_aligned('brief_stack access')
        return self._simulation_runtime.brief_stack


def build_runtime(dsl_code):
    simulation_runtime = SimulationRuntime(
        parse_dsl_node_to_state_machine(parse_with_grammar_entry(dsl_code, 'state_machine_dsl'))
    )
    generated_runtime = build_c_runtime(dsl_code)
    runtime = _DualRuntime(simulation_runtime, generated_runtime, dsl_code)
    runtime._assert_aligned('initial build')
    return runtime


def assert_runtime_state(runtime, current_path=None, vars=None, is_ended=False):
    assert runtime.is_ended is is_ended
    if current_path is None:
        assert runtime.is_ended
    else:
        assert runtime.current_state.path == current_path
    if vars is not None:
        for key, value in vars.items():
            assert runtime.vars[key] == value


def run_cycle_and_assert(runtime, events=None, *, current_path=None, vars=None, is_ended=False):
    runtime.cycle(events)
    assert_runtime_state(runtime, current_path=current_path, vars=vars, is_ended=is_ended)


_CASES = [
    (
        '4_1_basic_simple_transition',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (None, ('Root', 'A'), {'counter': 2}, False),
            (['Root.A.Go'], ('Root', 'B'), {'counter': 12}, False),
        ],
    ),
    (
        '4_2_composite_state',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoB'], ('Root', 'B', 'B1'), {'counter': 11}, False),
            (['Root.B.B1.Next'], ('Root', 'B', 'B2'), {'counter': 111}, False),
        ],
    ),
    (
        '4_3_validation_cannot_reach_stoppable',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1, 'ready': 0}, False),
            (['Root.A.GoB'], ('Root', 'A'), {'counter': 2, 'ready': 0}, False),
        ],
    ),
    (
        '4_4_validation_init_transition_requires_event',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoB'], ('Root', 'A'), {'counter': 2}, False),
            (['Root.A.GoB', 'Root.B.Start'], ('Root', 'B', 'B1'), {'counter': 12}, False),
        ],
    ),
    (
        '4_5_aspect_actions',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'trace': 123}, False),
            (None, ('Root', 'A'), {'trace': 123123}, False),
        ],
    ),
    (
        '4_6_pseudo_state',
        '''
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
''',
        [
            (None, None, {'trace': 2}, True),
        ],
    ),
    (
        '4_7_multi_level_non_stoppable',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoB'], ('Root', 'B', 'B1', 'B1a'), {'counter': 11}, False),
        ],
    ),
    (
        '4_8_transition_priority',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (None, ('Root', 'A'), {'counter': 2}, False),
            (None, ('Root', 'A'), {'counter': 3}, False),
            (None, ('Root', 'C'), {'counter': 103}, False),
        ],
    ),
    (
        '4_9_self_transition',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 11}, False),
            (['Root.A.Loop'], ('Root', 'A'), {'counter': 122}, False),
        ],
    ),
    (
        '4_10_exit_state',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (None, ('Root', 'A'), {'counter': 2}, False),
            (None, ('Root', 'A'), {'counter': 3}, False),
            (None, None, {'counter': 103}, True),
        ],
    ),
    (
        '4_11_guard_effect_multilevel_transition',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1, 'flag': 0}, False),
            (None, ('Root', 'A'), {'counter': 2, 'flag': 0}, False),
            (None, ('Root', 'A'), {'counter': 3, 'flag': 0}, False),
            (None, ('Root', 'B', 'B1'), {'counter': 13, 'flag': 1}, False),
        ],
    ),
    (
        '4_12_validation_failure_multilevel_transition',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1, 'flag': 0}, False),
            (None, ('Root', 'A'), {'counter': 2, 'flag': 0}, False),
            (None, ('Root', 'A'), {'counter': 3, 'flag': 0}, False),
            (None, ('Root', 'A'), {'counter': 4, 'flag': 0}, False),
        ],
    ),
    (
        '4_13_single_pseudo_state_chain',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoP'], ('Root', 'A'), {'counter': 2}, False),
            (['Root.A.GoP', 'Root.P.GoB'], ('Root', 'B'), {'counter': 1112}, False),
        ],
    ),
    (
        '4_14_multiple_pseudo_states_chain',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.Go1'], ('Root', 'A'), {'counter': 2}, False),
            (['Root.A.Go1', 'Root.P1.Go2'], ('Root', 'A'), {'counter': 3}, False),
            (['Root.A.Go1', 'Root.P1.Go2', 'Root.P2.Go3'], ('Root', 'B'), {'counter': 1113}, False),
        ],
    ),
    (
        '4_15_pseudo_chain_with_guard',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (None, ('Root', 'A'), {'counter': 2}, False),
            (None, ('Root', 'A'), {'counter': 3}, False),
            (None, ('Root', 'A'), {'counter': 4}, False),
            (None, ('Root', 'A'), {'counter': 5}, False),
            (None, ('Root', 'B'), {'counter': 115}, False),
        ],
    ),
    (
        '4_16_pseudo_chain_to_machine_end',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoP'], None, {'counter': 11}, True),
        ],
    ),
    (
        '4_17_exit_to_parent_invalid',
        '''
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
''',
        [
            (None, ('Root', 'System', 'A'), {'counter': 1}, False),
            (['Root.System.A.GoP'], ('Root', 'System', 'A'), {'counter': 2}, False),
        ],
    ),
    (
        '4_17_1_exit_to_parent_then_event_transition',
        '''
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
''',
        [
            (None, ('Root', 'System', 'A'), {'counter': 1}, False),
            (['Root.System.A.GoP'], ('Root', 'System', 'A'), {'counter': 2}, False),
            (['Root.System.A.GoP', 'Root.System.ToB'], ('Root', 'B'), {'counter': 112}, False),
        ],
    ),
    (
        '4_17_2_exit_to_parent_then_pseudo_then_guard',
        '''
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
''',
        [
            (None, ('Root', 'System', 'A'), {'counter': 1}, False),
            (['Root.System.A.GoP'], ('Root', 'System', 'A'), {'counter': 2}, False),
            (None, ('Root', 'System', 'A'), {'counter': 3}, False),
            (None, ('Root', 'System', 'A'), {'counter': 4}, False),
            (None, ('Root', 'System', 'A'), {'counter': 5}, False),
            (['Root.System.A.GoP'], ('Root', 'B'), {'counter': 1115}, False),
        ],
    ),
    (
        '4_18_pseudo_chain_inside_composite',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoB'], ('Root', 'B', 'B1'), {'counter': 1111}, False),
        ],
    ),
    (
        '4_19_evented_pseudo_chain_invalid_then_valid',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoB'], ('Root', 'A'), {'counter': 2}, False),
            (['Root.A.GoB', 'Root.B.P1.Event'], ('Root', 'B', 'B1'), {'counter': 112}, False),
        ],
    ),
    (
        '4_20_mixed_composite_and_pseudo',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.GoB'], ('Root', 'B', 'C', 'C1'), {'counter': 111}, False),
        ],
    ),
    (
        '4_21_single_layer_aspect_actions',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 10101}, False),
            (['Root.A.Go'], ('Root', 'B'), {'counter': 21102}, False),
        ],
    ),
    (
        '4_22_multi_layer_aspect_actions',
        '''
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
''',
        [
            (None, ('Root', 'System', 'Module', 'Active'), {'counter': 111112}, False),
        ],
    ),
    (
        '4_23_pseudo_state_skips_aspect_actions',
        '''
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
''',
        [
            (None, ('Root', 'A'), {'counter': 10101}, False),
            (['Root.A.GoP', 'Root.P.GoB'], ('Root', 'B'), {'counter': 121102}, False),
        ],
    ),
    (
        '4_24_multiple_leaf_states_share_aspects',
        '''
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
''',
        [
            (None, ('Root', 'System', 'A'), {'counter': 1112}, False),
            (['Root.System.A.GoB'], ('Root', 'System', 'B'), {'counter': 2233}, False),
            (['Root.System.B.GoC'], ('Root', 'System', 'C'), {'counter': 3444}, False),
        ],
    ),
    (
        '4_25_cross_hierarchy_transition_actual_runtime_behavior',
        '''
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
''',
        [
            (None, ('Root', 'System1', 'A'), {'counter': 110111}, False),
            (['Root.System1.Go'], ('Root', 'System1', 'A'), {'counter': 220222}, False),
        ],
    ),
    (
        '4_26_cross_hierarchy_transition_with_staged_guards',
        '''
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
''',
        [
            (None, ('Root', 'System1', 'A'), {'phase': 1, 'trace': 110111}, False),
            (None, ('Root', 'System1', 'A'), {'phase': 2, 'trace': 220222}, False),
            (None, ('Root', 'System1', 'A'), {'phase': 3, 'trace': 330333}, False),
            (None, ('Root', 'System1', 'A'), {'phase': 4, 'trace': 440444}, False),
            (None, ('Root', 'System1', 'A'), {'phase': 5, 'trace': 550555}, False),
            (None, ('Root', 'System1', 'A'), {'phase': 6, 'trace': 660666}, False),
            (None, ('Root', 'System1', 'A'), {'phase': 7, 'trace': 770777}, False),
            (None, ('Root', 'System2', 'B'), {'phase': 7, 'trace': 1881778}, False),
            (None, ('Root', 'System2', 'B'), {'phase': 7, 'trace': 2992779}, False),
        ],
    ),
    (
        '4_27_composite_state_stuck_in_init_wait_without_enabled_init_transition',
        '''
def int phase = 0;
def int trace = 0;
state Root {
    state System {
        enter {
            trace = trace + 1;
        }
        during before {
            trace = trace + 10;
        }

        state A {
            during {
                phase = phase + 1;
                trace = trace + 100;
            }
        }

        [*] -> A : if [phase >= 3];
    }

    [*] -> System;
}
''',
        [
            (None, ('Root',), {'phase': 0, 'trace': 0}, False),
            (None, ('Root',), {'phase': 0, 'trace': 0}, False),
            (None, ('Root',), {'phase': 0, 'trace': 0}, False),
        ],
    ),
    (
        '4_28_post_child_exit_without_follow_up_transition',
        '''
def int phase = 0;
def int trace = 0;
state Root {
    state System {
        during after {
            trace = trace + 1000;
        }

        pseudo state A {
            during {
                phase = phase + 1;
                trace = trace + 10;
            }
        }

        [*] -> A;
        A -> [*] : if [phase >= 2];
    }

    [*] -> System;
}
''',
        [
            (None, ('Root',), {'phase': 0, 'trace': 0}, False),
            (None, ('Root',), {'phase': 0, 'trace': 0}, False),
            (None, ('Root',), {'phase': 0, 'trace': 0}, False),
        ],
    ),
    (
        '4_30_explicit_exit_to_root_ends_runtime',
        '''
def int phase = 0;
def int trace = 0;
state Root {
    state A {
        during {
            phase = phase + 1;
            trace = trace + 10;
        }
    }

    [*] -> A;
    A -> [*] : if [phase >= 2];
}
''',
        [
            (None, ('Root', 'A'), {'phase': 1, 'trace': 10}, False),
            (None, ('Root', 'A'), {'phase': 2, 'trace': 20}, False),
            (None, None, {'phase': 2, 'trace': 20}, True),
            (None, None, {'phase': 2, 'trace': 20}, True),
        ],
    ),
    (
        '4_31_prunes_repeated_speculative_execution_state',
        '''
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

    state Sink {
        state Dead;
        [*] -> Dead : if [counter < 0];
    }

    [*] -> A;
    A -> Sink :: Go;
    A -> B :: Go;
}
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['Root.A.Go'], ('Root', 'B'), {'counter': 11}, False),
        ],
    ),
    (
        '4_33_ref_reuses_named_enter_action',
        '''
def int init_count = 0;
def int trace = 0;
state Root {
    enter CommonInit {
        init_count = init_count + 1;
        trace = trace + 100;
    }

    state A {
        enter ref /CommonInit;
        during {
            trace = trace + 1;
        }
    }

    state B {
        enter ref /CommonInit;
        during {
            trace = trace + 10;
        }
    }

    [*] -> A;
    A -> B :: Go;
}
''',
        [
            (None, ('Root', 'A'), {'init_count': 2, 'trace': 201}, False),
            (['Root.A.Go'], ('Root', 'B'), {'init_count': 3, 'trace': 311}, False),
            (None, ('Root', 'B'), {'init_count': 3, 'trace': 321}, False),
        ],
    ),
    (
        '4_34_ref_targets_abstract_action_without_side_effects',
        '''
def int trace = 0;
state Root {
    enter abstract PlatformInit;

    state A {
        enter ref /PlatformInit;
        during {
            trace = trace + 1;
        }
    }

    state B {
        enter ref /PlatformInit;
        during {
            trace = trace + 10;
        }
    }

    [*] -> A;
    A -> B :: Go;
}
''',
        [
            (None, ('Root', 'A'), {'trace': 1}, False),
            (['Root.A.Go'], ('Root', 'B'), {'trace': 11}, False),
            (None, ('Root', 'B'), {'trace': 21}, False),
        ],
    ),
    (
        '4_35_ref_reuses_named_aspect_action',
        '''
def int trace = 0;
state Root {
    >> during before SharedBefore {
        trace = trace + 100;
    }

    state System {
        >> during before ref /SharedBefore;

        state A {
            during {
                trace = trace + 1;
            }
        }

        state B {
            during {
                trace = trace + 10;
            }
        }

        [*] -> A;
        A -> B :: Go;
    }

    [*] -> System;
}
''',
        [
            (None, ('Root', 'System', 'A'), {'trace': 201}, False),
            (['Root.System.A.Go'], ('Root', 'System', 'B'), {'trace': 411}, False),
            (None, ('Root', 'System', 'B'), {'trace': 621}, False),
        ],
    ),
    (
        '4_100_elevator_door_control',
        '''
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
''',
        [
            (None, ('Root', 'Closed'), {'door_pos': 0, 'hold': 0, 'reopen_count': 0}, False),
            (['Root.Closed.HallCall'], ('Root', 'Opening'), {'door_pos': 50, 'hold': 0, 'reopen_count': 0}, False),
            (None, ('Root', 'Opening'), {'door_pos': 100, 'hold': 0, 'reopen_count': 0}, False),
            (None, ('Root', 'Opened'), {'door_pos': 100, 'hold': 1, 'reopen_count': 0}, False),
            (None, ('Root', 'Opened'), {'door_pos': 100, 'hold': 2, 'reopen_count': 0}, False),
            (None, ('Root', 'Closing'), {'door_pos': 50, 'hold': 2, 'reopen_count': 0}, False),
            (None, ('Root', 'Closing'), {'door_pos': 0, 'hold': 2, 'reopen_count': 0}, False),
            (None, ('Root', 'Closed'), {'door_pos': 0, 'hold': 0, 'reopen_count': 0}, False),
        ],
    ),
    (
        '4_101_storage_water_heater_control',
        '''
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
''',
        [
            (None, ('Root', 'Standby'), {'water_temp': 54, 'draw_count': 0}, False),
            (['Root.Standby.HotWaterDraw'], ('Root', 'Standby'), {'water_temp': 45, 'draw_count': 1}, False),
            (None, ('Root', 'Heating'), {'water_temp': 49, 'draw_count': 1}, False),
            (None, ('Root', 'Heating'), {'water_temp': 53, 'draw_count': 1}, False),
            (None, ('Root', 'Heating'), {'water_temp': 57, 'draw_count': 1}, False),
            (None, ('Root', 'Heating'), {'water_temp': 61, 'draw_count': 1}, False),
            (None, ('Root', 'Standby'), {'water_temp': 60, 'draw_count': 1}, False),
        ],
    ),
    (
        '4_102_traffic_signal_with_pedestrian_request',
        '''
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
''',
        [
            (None, ('Root', 'MainGreen'), {'green_ticks': 1, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0}, False),
            (['Root.MainGreen.PedRequest'], ('Root', 'MainGreen'), {'green_ticks': 2, 'request_latched': 1, 'yellow_ticks': 0, 'walk_ticks': 0}, False),
            (None, ('Root', 'MainGreen'), {'green_ticks': 3, 'request_latched': 1, 'yellow_ticks': 0, 'walk_ticks': 0}, False),
            (None, ('Root', 'PedestrianPhase', 'MainYellow'), {'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 1, 'walk_ticks': 0}, False),
            (None, ('Root', 'PedestrianPhase', 'PedWalk'), {'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 1, 'walk_ticks': 1}, False),
            (None, ('Root', 'PedestrianPhase', 'PedWalk'), {'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 1, 'walk_ticks': 2}, False),
            (None, ('Root', 'MainGreen'), {'green_ticks': 1, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0}, False),
        ],
    ),
    (
        '4_103_ac_charger_session_control',
        '''
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
''',
        [
            (None, ('Root', 'Idle'), {'soc': 70, 'sessions': 0}, False),
            (['Root.Idle.PlugIn'], ('Root', 'Charging'), {'soc': 80, 'sessions': 0}, False),
            (['Root.Charging.Unplug'], ('Root', 'Idle'), {'soc': 80, 'sessions': 1}, False),
            (['Root.Idle.PlugIn'], ('Root', 'Charging'), {'soc': 90, 'sessions': 1}, False),
            (None, ('Root', 'Charging'), {'soc': 100, 'sessions': 1}, False),
        ],
    ),
    (
        '4_104_ats_mains_generator_transfer',
        '''
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
''',
        [
            (None, ('Root', 'OnMains'), {'warmup': 0, 'transfer_count': 0}, False),
            (['Root.OnMains.GridFail'], ('Root', 'StartingGen'), {'warmup': 1, 'transfer_count': 0}, False),
            (None, ('Root', 'StartingGen'), {'warmup': 2, 'transfer_count': 0}, False),
            (None, ('Root', 'OnGenerator'), {'warmup': 2, 'transfer_count': 1}, False),
            (['Root.OnGenerator.GridRestore'], ('Root', 'OnMains'), {'warmup': 0, 'transfer_count': 2}, False),
        ],
    ),
    (
        '4_105_cold_storage_defrost_cycle',
        '''
def int frost = 0;
def int drip_ticks = 0;
state Root {
    state Cooling {
        during {
            frost = frost + 2;
        }
    }

    state DefrostCycle {
        state Defrost {
            during {
                frost = frost - 5;
            }
        }

        state Drip {
            during {
                drip_ticks = drip_ticks + 1;
            }
        }

        [*] -> Defrost;
        Defrost -> Drip : if [frost <= 0] effect {
            frost = 0;
            drip_ticks = 0;
        };
        Drip -> [*] : if [drip_ticks >= 1];
    }

    [*] -> Cooling;
    Cooling -> DefrostCycle : if [frost >= 6];
    DefrostCycle -> Cooling effect {
        drip_ticks = 0;
    };
}
''',
        [
            (None, ('Root', 'Cooling'), {'frost': 2, 'drip_ticks': 0}, False),
            (None, ('Root', 'Cooling'), {'frost': 4, 'drip_ticks': 0}, False),
            (None, ('Root', 'Cooling'), {'frost': 6, 'drip_ticks': 0}, False),
            (None, ('Root', 'DefrostCycle', 'Defrost'), {'frost': 1, 'drip_ticks': 0}, False),
            (None, ('Root', 'DefrostCycle', 'Defrost'), {'frost': -4, 'drip_ticks': 0}, False),
            (None, ('Root', 'DefrostCycle', 'Drip'), {'frost': 0, 'drip_ticks': 1}, False),
            (None, ('Root', 'Cooling'), {'frost': 2, 'drip_ticks': 0}, False),
        ],
    ),
    (
        '4_200_flexible_path_basic_relative',
        '''
def int counter = 0;
state Root {
    state A {
        event go;
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
    A -> B :: go;
}
''',
        [
            (None, ('Root', 'A'), {'counter': 1}, False),
            (['go'], ('Root', 'B'), {'counter': 11}, False),
        ],
    ),
    (
        '4_201_flexible_path_parent_relative',
        '''
def int counter = 0;
state Root {
    event root_event;
    state System {
        event system_event;
        state Active {
            event active_event;
            during {
                counter = counter + 1;
            }
        }
        state Idle {
            during {
                counter = counter + 10;
            }
        }
        [*] -> Active;
        Active -> Idle :: active_event;
        Idle -> Active : system_event;
    }
    [*] -> System;
}
''',
        [
            (None, ('Root', 'System', 'Active'), {'counter': 1}, False),
            (['active_event'], ('Root', 'System', 'Idle'), {'counter': 11}, False),
            (['.system_event'], ('Root', 'System', 'Active'), {'counter': 12}, False),
        ],
    ),
    (
        '4_202_flexible_path_absolute',
        '''
def int counter = 0;
state Root {
    event global_reset;
    state System {
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
        A -> B : /global_reset;
    }
    [*] -> System;
}
''',
        [
            (None, ('Root', 'System', 'A'), {'counter': 1}, False),
            (['/global_reset'], ('Root', 'System', 'B'), {'counter': 11}, False),
        ],
    ),
    (
        '4_203_flexible_path_mixed_formats',
        '''
def int counter = 0;
state Root {
    event global_event;
    state System {
        event system_event;
        state A {
            event local_a;
            during {
                counter = counter + 1;
            }
        }
        state B {
            event local_b;
            during {
                counter = counter + 10;
            }
        }
        [*] -> A;
        A -> B :: local_a;
        A -> B : system_event;
        A -> B : /global_event;
    }
    [*] -> System;
}
''',
        [
            (None, ('Root', 'System', 'A'), {'counter': 1}, False),
            (['local_a'], ('Root', 'System', 'B'), {'counter': 11}, False),
        ],
    ),
]


@pytest.mark.unittest
@pytest.mark.parametrize(
    ('case_name', 'dsl_code', 'steps'),
    _CASES,
    ids=[item[0] for item in _CASES],
)
def test_simulation_design_examples(case_name, dsl_code, steps):
    runtime = build_runtime(dsl_code)
    try:
        for events, current_path, vars_, is_ended in steps:
            run_cycle_and_assert(
                runtime,
                events,
                current_path=current_path,
                vars=vars_,
                is_ended=is_ended,
            )
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_7_multi_level_non_stoppable_alternate_path():
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
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.GoC'], current_path=('Root', 'C'), vars={'counter': 101})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_27_composite_state_stuck_in_init_wait_without_enabled_init_transition_stack():
    dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    state System {
        enter {
            trace = trace + 1;
        }
        during before {
            trace = trace + 10;
        }

        state A {
            during {
                phase = phase + 1;
                trace = trace + 100;
            }
        }

        [*] -> A : if [phase >= 3];
    }

    [*] -> System;
}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_28_post_child_exit_without_follow_up_transition_stack():
    dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    state System {
        during after {
            trace = trace + 1000;
        }

        pseudo state A {
            during {
                phase = phase + 1;
                trace = trace + 10;
            }
        }

        [*] -> A;
        A -> [*] : if [phase >= 2];
    }

    [*] -> System;
}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_30_explicit_exit_to_root_ends_runtime_stack_and_post_end_cycle():
    dsl_code = '''
def int phase = 0;
def int trace = 0;
state Root {
    state A {
        during {
            phase = phase + 1;
            trace = trace + 10;
        }
    }

    [*] -> A;
    A -> [*] : if [phase >= 2];
}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'phase': 1, 'trace': 10})
        assert runtime.brief_stack == [(('Root',), 'init_wait'), (('Root', 'A'), 'active')]
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'phase': 2, 'trace': 20})
        assert runtime.brief_stack == [(('Root',), 'init_wait'), (('Root', 'A'), 'active')]
        run_cycle_and_assert(runtime, current_path=None, vars={'phase': 2, 'trace': 20}, is_ended=True)
        assert runtime.brief_stack == []
        run_cycle_and_assert(runtime, current_path=None, vars={'phase': 2, 'trace': 20}, is_ended=True)
        assert runtime.brief_stack == []
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_32_raises_error_for_non_converging_speculative_dfs():
    depth = 80
    lines = [
        'def int counter = 0;',
        'state Root {',
        '    state A {',
        '        during {',
        '            counter = counter + 1;',
        '        }',
        '    }',
        '    state Deep {',
    ]
    indent = '        '
    for idx in range(depth):
        lines.extend([
            f'{indent}state L{idx} {{',
            f'{indent}    [*] -> L{idx + 1};',
        ])
        indent += '    '
    lines.extend([
        f'{indent}state L{depth} {{',
        f'{indent}    during {{',
        f'{indent}        counter = counter + 1;',
        f'{indent}    }}',
        f'{indent}}}',
    ])
    for idx in reversed(range(depth)):
        indent = '        ' + '    ' * idx
        lines.append(f'{indent}}}')
    lines.extend([
        '        [*] -> L0;',
        '    }',
        '',
        '    [*] -> A;',
        '    A -> Deep :: Go;',
        '}',
    ])
    dsl_code = '\n'.join(lines)
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        before_stack = runtime.brief_stack
        before_vars = dict(runtime.vars)

        runtime.cycle_expect_error(['Root.A.Go'], match='structural stack-depth safety limit')

        assert runtime.brief_stack == before_stack
        assert runtime.vars == before_vars
        assert runtime.is_ended is False
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_100_elevator_door_control_reopen_branch():
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
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'Closed'),
                             vars={'door_pos': 0, 'hold': 0, 'reopen_count': 0})
        run_cycle_and_assert(runtime, ['Root.Closed.HallCall'], current_path=('Root', 'Opening'),
                             vars={'door_pos': 50, 'hold': 0, 'reopen_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Opening'),
                             vars={'door_pos': 100, 'hold': 0, 'reopen_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Opened'),
                             vars={'door_pos': 100, 'hold': 1, 'reopen_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Opened'),
                             vars={'door_pos': 100, 'hold': 2, 'reopen_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Closing'),
                             vars={'door_pos': 50, 'hold': 2, 'reopen_count': 0})
        run_cycle_and_assert(runtime, ['Root.Closing.BeamBlocked'], current_path=('Root', 'Opened'),
                             vars={'door_pos': 100, 'hold': 1, 'reopen_count': 1})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_101_storage_water_heater_control_nominal_branch():
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
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 54, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 53, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 52, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 51, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 50, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 54, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 58, 'draw_count': 0})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_102_traffic_signal_with_pedestrian_request_nominal_branch():
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
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 1, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 2, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 4, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_103_ac_charger_session_control_complete_branch():
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
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'Idle'), vars={'soc': 70, 'sessions': 0})
        run_cycle_and_assert(runtime, ['Root.Idle.PlugIn'], current_path=('Root', 'Charging'),
                             vars={'soc': 80, 'sessions': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Charging'), vars={'soc': 90, 'sessions': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Charging'), vars={'soc': 100, 'sessions': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Complete'), vars={'soc': 100, 'sessions': 0})
        run_cycle_and_assert(runtime, ['Root.Complete.Unplug'], current_path=('Root', 'Idle'),
                             vars={'soc': 100, 'sessions': 1})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_104_ats_mains_generator_transfer_nominal_branch():
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
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'OnMains'), vars={'warmup': 0, 'transfer_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'OnMains'), vars={'warmup': 0, 'transfer_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'OnMains'), vars={'warmup': 0, 'transfer_count': 0})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_105_cold_storage_defrost_cycle_nominal_branch():
    dsl_code = '''
def int frost = 0;
def int drip_ticks = 0;
state Root {
    state Cooling {
        during {
            frost = frost + 2;
        }
    }

    state DefrostCycle {
        state Defrost {
            during {
                frost = frost - 5;
            }
        }

        state Drip {
            during {
                drip_ticks = drip_ticks + 1;
            }
        }

        [*] -> Defrost;
        Defrost -> Drip : if [frost <= 0] effect {
            frost = 0;
            drip_ticks = 0;
        };
        Drip -> [*] : if [drip_ticks >= 1];
    }

    [*] -> Cooling;
    Cooling -> DefrostCycle : if [frost >= 6];
    DefrostCycle -> Cooling effect {
        drip_ticks = 0;
    };
}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 2, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 4, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 6, 'drip_ticks': 0})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_4_203_flexible_path_mixed_formats_variants():
    dsl_code = '''
def int counter = 0;
state Root {
    event global_event;
    state System {
        event system_event;
        state A {
            event local_a;
            during {
                counter = counter + 1;
            }
        }
        state B {
            event local_b;
            during {
                counter = counter + 10;
            }
        }
        [*] -> A;
        A -> B :: local_a;
        A -> B : system_event;
        A -> B : /global_event;
    }
    [*] -> System;
}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['.system_event'], current_path=('Root', 'System', 'B'), vars={'counter': 11})
    finally:
        runtime.close()

    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['/global_event'], current_path=('Root', 'System', 'B'), vars={'counter': 11})
    finally:
        runtime.close()

    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.System.A.local_a'], current_path=('Root', 'System', 'B'),
                             vars={'counter': 11})
    finally:
        runtime.close()


@pytest.mark.unittest
def test_auto_initialization_on_current_state_access():
    dsl_code = '''
def int counter = 0;

state System {
    [*] -> Idle;

    state Idle {
        during {
            counter = counter + 1;
        }
    }

    state Active {
        during {
            counter = counter + 10;
        }
    }

    Idle -> Active : if [counter >= 5];
    Active -> Idle : if [counter >= 50];
}
'''
    runtime = build_runtime(dsl_code)
    try:
        assert runtime.current_state.path == ('System',)
        assert runtime.current_state_path == ('System',)
        assert runtime.vars['counter'] == 0

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Idle')
        assert runtime.current_state_path == ('System', 'Idle')
        assert runtime.vars['counter'] == 1

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Idle')
        assert runtime.vars['counter'] == 2

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Idle')
        assert runtime.vars['counter'] == 3

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Idle')
        assert runtime.vars['counter'] == 4

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Idle')
        assert runtime.vars['counter'] == 5

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.current_state_path == ('System', 'Active')
        assert runtime.vars['counter'] == 15

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 25

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 35
    finally:
        runtime.close()


@pytest.mark.unittest
def test_temporary_variables_are_block_local():
    dsl_code = '''
def int x = 0;
def int y = 0;
state Root {
    state A {
        during {
            tmp = x + 1;
            x = tmp;
        }
    }
    state B {
        enter {
            tmp = x + y;
            y = tmp + 1;
        }
    }

    [*] -> A;
    A -> B :: Go effect {
        tmp = x + 10;
        x = tmp;
    };
}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'x': 1, 'y': 0})
        assert set(runtime.vars.keys()) == {'x', 'y'}
        assert 'tmp' not in runtime.vars

        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'x': 11, 'y': 12})
        assert set(runtime.vars.keys()) == {'x', 'y'}
        assert 'tmp' not in runtime.vars
    finally:
        runtime.close()


@pytest.mark.unittest
@pytest.mark.parametrize(
    ['block_code', 'initial_values', 'expected_values'],
    [
        (
            '''
if [flag == 0] {
    x = x + 10;
}
flag = 1;
''',
            {'x': 0, 'y': 0, 'flag': 0, 'mode': 0},
            {'x': 10, 'y': 0, 'flag': 1, 'mode': 0},
        ),
        (
            '''
if [flag == 1] {
    x = x + 10;
}
x = x + 1;
''',
            {'x': 0, 'y': 0, 'flag': 0, 'mode': 0},
            {'x': 1, 'y': 0, 'flag': 0, 'mode': 0},
        ),
        (
            '''
if [flag == 0] {
    x = x + 10;
} else {
    x = x + 100;
}
''',
            {'x': 0, 'y': 0, 'flag': 1, 'mode': 0},
            {'x': 100, 'y': 0, 'flag': 1, 'mode': 0},
        ),
        (
            '''
if [mode == 0] {
    x = x + 1;
} else if [mode == 1] {
    x = x + 10;
} else {
    x = x + 100;
}
''',
            {'x': 0, 'y': 0, 'flag': 0, 'mode': 1},
            {'x': 10, 'y': 0, 'flag': 0, 'mode': 1},
        ),
        (
            '''
if [mode == 1] {
    tmp = 10;
    if [flag == 1] {
        x = x + tmp;
    } else {
        x = x + 100;
    }
} else {
    x = x + 1000;
}
''',
            {'x': 0, 'y': 0, 'flag': 1, 'mode': 1},
            {'x': 10, 'y': 0, 'flag': 1, 'mode': 1},
        ),
        (
            '''
if [mode == 1] {
    tmp = 10;
    if [flag == 1] {
        x = x + tmp;
    } else {
        x = x + 100;
    }
} else {
    x = x + 1000;
}
''',
            {'x': 0, 'y': 0, 'flag': 1, 'mode': 0},
            {'x': 1000, 'y': 0, 'flag': 1, 'mode': 0},
        ),
        (
            '''
tmp = x + 1;
if [flag == 1] {
    tmp = tmp + 10;
}
x = tmp;
''',
            {'x': 0, 'y': 0, 'flag': 1, 'mode': 0},
            {'x': 11, 'y': 0, 'flag': 1, 'mode': 0},
        ),
        (
            '''
if [flag == 0] {
    x = x + 1;
    y = x + 10;
}
''',
            {'x': 1, 'y': 0, 'flag': 0, 'mode': 0},
            {'x': 2, 'y': 12, 'flag': 0, 'mode': 0},
        ),
    ]
)
def test_if_blocks_in_during_actions(block_code, initial_values, expected_values):
    dsl_code = f'''
def int x = {initial_values["x"]};
def int y = {initial_values["y"]};
def int flag = {initial_values["flag"]};
def int mode = {initial_values["mode"]};
state Root {{
    state A {{
        during {{
{block_code}
        }}
    }}
    [*] -> A;
}}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars=expected_values)
    finally:
        runtime.close()


@pytest.mark.unittest
def test_if_blocks_in_exit_effect_and_enter_actions():
    dsl_code = '''
def int x = 0;
def int flag = 0;
state Root {
    state A {
        exit {
            if [flag == 0] {
                x = x + 1;
            }
        }
    }

    state B {
        enter {
            if [flag == 0] {
                x = x + 10;
            }
        }
    }

    [*] -> A;
    A -> B :: Go effect {
        if [flag == 0] {
            x = x + 100;
        } else {
            x = x + 1000;
        }
    };
}
'''
    runtime = build_runtime(dsl_code)
    try:
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'x': 0, 'flag': 0})
        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'x': 111, 'flag': 0})
    finally:
        runtime.close()

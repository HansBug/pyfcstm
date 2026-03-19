import importlib.util
import logging
import os.path
from tempfile import TemporaryDirectory

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeDfsError
from pyfcstm.template import extract_template


class _DualRuntime:
    def __init__(self, simulation_runtime, generated_runtime, dsl_code):
        self._simulation_runtime = simulation_runtime
        self._generated_runtime = generated_runtime
        self._dsl_code = dsl_code

    def _generated_brief_stack(self):
        state_info = self._generated_runtime._STATE_INFO
        return [
            (tuple(state_info[frame['state']]['path']), frame['mode'])
            for frame in self._generated_runtime._stack
        ]

    def _generated_current_path(self):
        return self._generated_runtime.current_state_path

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
            gen_path = self._generated_current_path()
            assert gen_path is None, (
                f'{when}: generated runtime should be terminated for DSL:\n{self._dsl_code}\n'
                f'generated current_state_path={gen_path!r}'
            )
        else:
            sim_path = self._simulation_runtime.current_state.path
            gen_path = self._generated_current_path()
            assert sim_path == gen_path, (
                f'{when}: current state mismatch for DSL:\n{self._dsl_code}\n'
                f'simulation={sim_path!r}\n'
                f'generated={gen_path!r}'
            )

        sim_stack = self._simulation_runtime.brief_stack
        gen_stack = self._generated_brief_stack()
        assert sim_stack == gen_stack, (
            f'{when}: brief_stack mismatch for DSL:\n{self._dsl_code}\n'
            f'simulation={sim_stack!r}\n'
            f'generated={gen_stack!r}'
        )

    @staticmethod
    def _assert_exceptions_match(sim_exc, gen_exc, dsl_code, events):
        assert sim_exc is not None and gen_exc is not None, (
            f'cycle(events={events!r}) exception mismatch for DSL:\n{dsl_code}\n'
            f'simulation={sim_exc!r}, generated={gen_exc!r}'
        )
        assert type(sim_exc).__name__ == type(gen_exc).__name__, (
            f'cycle(events={events!r}) exception type mismatch for DSL:\n{dsl_code}\n'
            f'simulation={type(sim_exc).__name__}: {sim_exc}\n'
            f'generated={type(gen_exc).__name__}: {gen_exc}'
        )

    def cycle(self, events=None):
        sim_result = None
        gen_result = None
        sim_exc = None
        gen_exc = None

        try:
            sim_result = self._simulation_runtime.cycle(events)
        except Exception as err:  # pragma: no cover - exercised by inherited tests
            sim_exc = err

        try:
            gen_result = self._generated_runtime.cycle(events)
        except Exception as err:  # pragma: no cover - exercised by inherited tests
            gen_exc = err

        if sim_exc is not None or gen_exc is not None:
            self._assert_exceptions_match(sim_exc, gen_exc, self._dsl_code, events)
            raise sim_exc

        assert sim_result == gen_result, (
            f'cycle(events={events!r}) return mismatch for DSL:\n{self._dsl_code}\n'
            f'simulation={sim_result!r}, generated={gen_result!r}'
        )
        self._assert_aligned(f'after cycle(events={events!r})')
        return sim_result

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
        if self._simulation_runtime.is_ended:
            try:
                _ = self._generated_runtime.current_state_path
            except Exception:
                pass
            return self._simulation_runtime.current_state

        self._assert_aligned('current_state access')
        return self._simulation_runtime.current_state

    @property
    def brief_stack(self):
        self._assert_aligned('brief_stack access')
        return self._simulation_runtime.brief_stack


def _build_generated_runtime(dsl_code):
    ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast)

    with TemporaryDirectory() as template_td:
        template_dir = extract_template('python_native', template_td)
        with TemporaryDirectory() as output_td:
            StateMachineCodeRenderer(template_dir).render(model=model, output_dir=output_td)

            module_file = os.path.join(output_td, 'machine.py')
            module_name = 'generated_python_native_runtime_alignment'
            spec = importlib.util.spec_from_file_location(module_name, module_file)
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            machine_cls = getattr(module, '{name}Machine'.format(name=model.root_state.name))
            return machine_cls()


def build_runtime(dsl_code):
    simulation_runtime = SimulationRuntime(
        parse_dsl_node_to_state_machine(parse_with_grammar_entry(dsl_code, 'state_machine_dsl'))
    )
    generated_runtime = _build_generated_runtime(dsl_code)
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
        run_cycle_and_assert(
            runtime,
            ['Root.A.GoB', 'Root.B.Start'],
            current_path=('Root', 'B', 'B1'),
            vars={'counter': 12},
        )

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
        run_cycle_and_assert(runtime, ['Root.System1.Go'], current_path=('Root', 'System1', 'A'),
                             vars={'counter': 220222})

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

    def test_4_27_composite_state_stuck_in_init_wait_without_enabled_init_transition(self, caplog):
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

        with caplog.at_level(logging.WARNING):
            run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        assert 'Unable to reach a stoppable state' in caplog.text

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        assert 'Unable to reach a stoppable state' in caplog.text

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        assert 'Unable to reach a stoppable state' in caplog.text

    def test_4_28_post_child_exit_without_follow_up_transition(self, caplog):
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

        with caplog.at_level(logging.WARNING):
            run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        assert 'Unable to reach a stoppable state' in caplog.text

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        assert 'Unable to reach a stoppable state' in caplog.text

        caplog.clear()
        with caplog.at_level(logging.WARNING):
            run_cycle_and_assert(runtime, current_path=('Root',), vars={'phase': 0, 'trace': 0})
        assert runtime.brief_stack == [(('Root',), 'init_wait')]
        assert 'Unable to reach a stoppable state' in caplog.text

    def test_4_30_explicit_exit_to_root_ends_runtime(self, caplog):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'phase': 1, 'trace': 10})
        assert runtime.brief_stack == [(('Root',), 'init_wait'), (('Root', 'A'), 'active')]
        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'phase': 2, 'trace': 20})
        assert runtime.brief_stack == [(('Root',), 'init_wait'), (('Root', 'A'), 'active')]
        run_cycle_and_assert(runtime, current_path=None, vars={'phase': 2, 'trace': 20}, is_ended=True)
        assert runtime.brief_stack == []

        with caplog.at_level(logging.WARNING):
            run_cycle_and_assert(runtime, current_path=None, vars={'phase': 2, 'trace': 20}, is_ended=True)
        assert runtime.brief_stack == []
        assert 'Runtime already ended, cycle ignored.' in caplog.text

    def test_4_31_prunes_repeated_speculative_execution_state(self):
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

    state Sink {
        state Dead;
        [*] -> Dead : if [counter < 0];
    }

    [*] -> A;
    A -> Sink :: Go;
    A -> B :: Go;
}
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'counter': 11})

    def test_4_32_raises_error_for_non_converging_speculative_dfs(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        before_stack = runtime.brief_stack
        before_vars = dict(runtime.vars)

        with pytest.raises(SimulationRuntimeDfsError, match='structural stack-depth safety limit'):
            runtime.cycle(['Root.A.Go'])

        assert runtime.brief_stack == before_stack
        assert runtime.vars == before_vars
        assert runtime.is_ended is False

    def test_4_33_ref_reuses_named_enter_action(self):
        dsl_code = '''
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
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'init_count': 2, 'trace': 201})
        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'init_count': 3, 'trace': 311})
        run_cycle_and_assert(runtime, current_path=('Root', 'B'), vars={'init_count': 3, 'trace': 321})

    def test_4_34_ref_targets_abstract_action_without_side_effects(self):
        dsl_code = '''
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
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'trace': 1})
        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'trace': 11})
        run_cycle_and_assert(runtime, current_path=('Root', 'B'), vars={'trace': 21})

    def test_4_35_ref_reuses_named_aspect_action(self):
        dsl_code = '''
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
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'trace': 201})
        run_cycle_and_assert(runtime, ['Root.System.A.Go'], current_path=('Root', 'System', 'B'), vars={'trace': 411})
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'B'), vars={'trace': 621})

    def test_4_100_elevator_door_control(self):
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
        run_cycle_and_assert(runtime, current_path=('Root', 'Closing'),
                             vars={'door_pos': 0, 'hold': 2, 'reopen_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Closed'),
                             vars={'door_pos': 0, 'hold': 0, 'reopen_count': 0})

        runtime = build_runtime(dsl_code)
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

    def test_4_101_storage_water_heater_control(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 54, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 53, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 52, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 51, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 50, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 54, 'draw_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 58, 'draw_count': 0})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 54, 'draw_count': 0})
        run_cycle_and_assert(runtime, ['Root.Standby.HotWaterDraw'], current_path=('Root', 'Standby'),
                             vars={'water_temp': 45, 'draw_count': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 49, 'draw_count': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 53, 'draw_count': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 57, 'draw_count': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'Heating'), vars={'water_temp': 61, 'draw_count': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'Standby'), vars={'water_temp': 60, 'draw_count': 1})

    def test_4_102_traffic_signal_with_pedestrian_request(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 1, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 2, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 4, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 1, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, ['Root.MainGreen.PedRequest'], current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 2, 'request_latched': 1, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 3, 'request_latched': 1, 'yellow_ticks': 0, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'PedestrianPhase', 'MainYellow'),
                             vars={'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 1, 'walk_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'PedestrianPhase', 'PedWalk'),
                             vars={'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 1, 'walk_ticks': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'PedestrianPhase', 'PedWalk'),
                             vars={'green_ticks': 3, 'request_latched': 0, 'yellow_ticks': 1, 'walk_ticks': 2})
        run_cycle_and_assert(runtime, current_path=('Root', 'MainGreen'),
                             vars={'green_ticks': 1, 'request_latched': 0, 'yellow_ticks': 0, 'walk_ticks': 0})

    def test_4_103_ac_charger_session_control(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'Idle'), vars={'soc': 70, 'sessions': 0})
        run_cycle_and_assert(runtime, ['Root.Idle.PlugIn'], current_path=('Root', 'Charging'),
                             vars={'soc': 80, 'sessions': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Charging'), vars={'soc': 90, 'sessions': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Charging'), vars={'soc': 100, 'sessions': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Complete'), vars={'soc': 100, 'sessions': 0})
        run_cycle_and_assert(runtime, ['Root.Complete.Unplug'], current_path=('Root', 'Idle'),
                             vars={'soc': 100, 'sessions': 1})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'Idle'), vars={'soc': 70, 'sessions': 0})
        run_cycle_and_assert(runtime, ['Root.Idle.PlugIn'], current_path=('Root', 'Charging'),
                             vars={'soc': 80, 'sessions': 0})
        run_cycle_and_assert(runtime, ['Root.Charging.Unplug'], current_path=('Root', 'Idle'),
                             vars={'soc': 80, 'sessions': 1})
        run_cycle_and_assert(runtime, ['Root.Idle.PlugIn'], current_path=('Root', 'Charging'),
                             vars={'soc': 90, 'sessions': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'Charging'), vars={'soc': 100, 'sessions': 1})

    def test_4_104_ats_mains_generator_transfer(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'OnMains'), vars={'warmup': 0, 'transfer_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'OnMains'), vars={'warmup': 0, 'transfer_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'OnMains'), vars={'warmup': 0, 'transfer_count': 0})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'OnMains'), vars={'warmup': 0, 'transfer_count': 0})
        run_cycle_and_assert(runtime, ['Root.OnMains.GridFail'], current_path=('Root', 'StartingGen'),
                             vars={'warmup': 1, 'transfer_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'StartingGen'), vars={'warmup': 2, 'transfer_count': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'OnGenerator'), vars={'warmup': 2, 'transfer_count': 1})
        run_cycle_and_assert(runtime, ['Root.OnGenerator.GridRestore'], current_path=('Root', 'OnMains'),
                             vars={'warmup': 0, 'transfer_count': 2})

    def test_4_105_cold_storage_defrost_cycle(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 2, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 4, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 6, 'drip_ticks': 0})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 2, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 4, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 6, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'DefrostCycle', 'Defrost'),
                             vars={'frost': 1, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'DefrostCycle', 'Defrost'),
                             vars={'frost': -4, 'drip_ticks': 0})
        run_cycle_and_assert(runtime, current_path=('Root', 'DefrostCycle', 'Drip'), vars={'frost': 0, 'drip_ticks': 1})
        run_cycle_and_assert(runtime, current_path=('Root', 'Cooling'), vars={'frost': 2, 'drip_ticks': 0})

    def test_4_200_flexible_path_basic_relative(self):
        """Test basic relative event paths from current state."""
        dsl_code = '''
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
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['go'], current_path=('Root', 'B'), vars={'counter': 11})

    def test_4_201_flexible_path_parent_relative(self):
        """Test parent-relative event paths with leading dots."""
        dsl_code = '''
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
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'Active'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['active_event'], current_path=('Root', 'System', 'Idle'), vars={'counter': 11})
        run_cycle_and_assert(runtime, ['.system_event'], current_path=('Root', 'System', 'Active'),
                             vars={'counter': 12})

    def test_4_202_flexible_path_absolute(self):
        """Test absolute event paths with leading slash."""
        dsl_code = '''
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
'''
        runtime = build_runtime(dsl_code)

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['/global_reset'], current_path=('Root', 'System', 'B'), vars={'counter': 11})

    def test_4_203_flexible_path_mixed_formats(self):
        """Test mixing different path formats in the same cycle."""
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

        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['local_a'], current_path=('Root', 'System', 'B'), vars={'counter': 11})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['.system_event'], current_path=('Root', 'System', 'B'), vars={'counter': 11})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['/global_event'], current_path=('Root', 'System', 'B'), vars={'counter': 11})

        runtime = build_runtime(dsl_code)
        run_cycle_and_assert(runtime, current_path=('Root', 'System', 'A'), vars={'counter': 1})
        run_cycle_and_assert(runtime, ['Root.System.A.local_a'], current_path=('Root', 'System', 'B'),
                             vars={'counter': 11})

    def test_auto_initialization_on_current_state_access(self):
        """Test that current_state can be accessed before cycle() and returns root state."""
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

        assert runtime.current_state.path == ('System',)
        assert runtime.vars['counter'] == 0

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Idle')
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
        assert runtime.vars['counter'] == 15

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 25

        runtime.cycle()
        assert runtime.current_state.path == ('System', 'Active')
        assert runtime.vars['counter'] == 35


@pytest.mark.unittest
class TestTemporaryVariables:
    def test_temporary_variables_are_block_local(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'x': 1, 'y': 0})
        assert set(runtime.vars.keys()) == {'x', 'y'}
        assert 'tmp' not in runtime.vars

        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'x': 11, 'y': 12})
        assert set(runtime.vars.keys()) == {'x', 'y'}
        assert 'tmp' not in runtime.vars


@pytest.mark.unittest
class TestIfBlockRuntime:
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
    def test_if_blocks_in_during_actions(self, block_code, initial_values, expected_values):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars=expected_values)

    def test_if_blocks_in_exit_effect_and_enter_actions(self):
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

        run_cycle_and_assert(runtime, current_path=('Root', 'A'), vars={'x': 0, 'flag': 0})
        run_cycle_and_assert(runtime, ['Root.A.Go'], current_path=('Root', 'B'), vars={'x': 111, 'flag': 0})

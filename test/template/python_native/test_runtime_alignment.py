import importlib.util
import os.path
from tempfile import TemporaryDirectory

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.template import extract_template

import test.simulate.test_runtime as simulate_runtime_tests


class _RuntimeStateProxy:
    def __init__(self, path):
        self.path = path


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


@pytest.fixture(autouse=True)
def _patch_runtime_builder(monkeypatch):
    monkeypatch.setattr(simulate_runtime_tests, 'build_runtime', build_runtime)


@pytest.mark.unittest
class TestPythonNativeMatchesSimulationDesignExamples(
    simulate_runtime_tests.TestSimulationDesignExamples
):
    pass


@pytest.mark.unittest
class TestPythonNativeMatchesTemporaryVariables(
    simulate_runtime_tests.TestTemporaryVariables
):
    pass


@pytest.mark.unittest
class TestPythonNativeMatchesIfBlockRuntime(
    simulate_runtime_tests.TestIfBlockRuntime
):
    pass

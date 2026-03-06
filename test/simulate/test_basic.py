import pytest
from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime


pytestmark = [pytest.mark.unittest]


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

"""Generated Python runtimes keep the hidden variables of forced transitions at rest."""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

from .test_runtime import _render_python_module

pytestmark = pytest.mark.unittest

MODEL = '''
def int x = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        [*] -> A;
        state A { during { x = x + 1; } }
        state B;
        A -> B :: Go;
    }
    state Idle;
    !Run -> Idle : /Stop;
}
'''

TWO_DECLARATIONS = '''
def int x = 0;
state Root {
    event Stop;
    event Back;
    [*] -> Run;
    state Run { [*] -> A; state A { during { x = x + 1; } } }
    state Idle { [*] -> Wait; state Wait; }
    !Run -> Idle : /Stop;
    !Idle -> Run : /Back;
}
'''


def _simulator_message(source, **kwargs):
    with pytest.raises(ValueError) as caught:
        SimulationRuntime(load_state_machine_from_text(source), **kwargs)
    return str(caught.value)


def test_a_cold_start_begins_with_the_hidden_variable_lowered():
    with _render_python_module(MODEL) as module:
        machine = module.RootMachine()
        assert machine.vars == {'x': 0, '__forced_0': 0}
        machine.cycle()
        machine.cycle(['Root.Stop'])
        assert machine.current_state_path == ('Root', 'Idle')
        assert machine.vars == {'x': 1, '__forced_0': 0}


def test_a_hot_start_does_not_ask_for_the_hidden_variable():
    with _render_python_module(MODEL) as module:
        machine = module.RootMachine(initial_state='Root.Run.B', initial_vars={'x': 5})
        assert machine.vars == {'x': 5, '__forced_0': 0}
        machine.cycle(['Root.Stop'])
        assert machine.current_state_path == ('Root', 'Idle')
        # The value the variable has at rest is accepted when it is supplied.
        again = module.RootMachine(
            initial_state='Root.Run.A', initial_vars={'x': 1, '__forced_0': 0})
        again.cycle()
        assert again.vars == {'x': 2, '__forced_0': 0}


@pytest.mark.parametrize('kwargs', [
    {'initial_state': 'Root.Run.A', 'initial_vars': {'x': 1, '__forced_0': 1}},
    {'initial_vars': {'__forced_0': 1}},
], ids=['hot', 'cold'])
def test_a_raised_hidden_variable_is_rejected_with_the_message_of_the_simulator(kwargs):
    expected = _simulator_message(MODEL, **kwargs)
    assert '__forced_0' in expected and 'forced transition' in expected
    with _render_python_module(MODEL) as module:
        with pytest.raises(ValueError) as caught:
            module.RootMachine(**kwargs)
        assert str(caught.value) == expected


def test_every_hidden_variable_of_several_declarations_is_filled_in():
    with _render_python_module(TWO_DECLARATIONS) as module:
        machine = module.RootMachine(initial_state='Root.Idle.Wait', initial_vars={'x': 3})
        assert machine.vars == {'x': 3, '__forced_0': 0, '__forced_1': 0}
        machine.cycle(['Root.Back'])
        assert machine.current_state_path == ('Root', 'Run', 'A')
        assert machine.vars == {'x': 4, '__forced_0': 0, '__forced_1': 0}
        with pytest.raises(ValueError, match='__forced_1'):
            module.RootMachine(
                initial_state='Root.Idle.Wait', initial_vars={'x': 3, '__forced_1': 2})


def test_a_machine_without_forced_declarations_still_asks_for_every_variable():
    with _render_python_module('''
    def int x = 0;
    def int y = 0;
    state Root { [*] -> A; state A; }
    ''') as module:
        with pytest.raises(ValueError, match='initial_vars must provide all variables'):
            module.RootMachine(initial_state='Root.A', initial_vars={'x': 1})

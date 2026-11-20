"""Hot start of machines whose forced declarations were lowered into a hidden variable."""

import pytest

from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest

MODEL = '''def int x = 0;
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
}'''


def test_the_model_lists_the_variables_of_its_forced_declarations():
    assert load_state_machine_from_text(MODEL).forced_variables == ('__forced_0',)
    plain = load_state_machine_from_text('state Root { [*] -> A; state A; }')
    assert plain.forced_variables == ()


def test_hot_start_does_not_ask_for_the_hidden_variable():
    model = load_state_machine_from_text(MODEL)
    runtime = SimulationRuntime(model, initial_state='Root.Run.B', initial_vars={'x': 5})
    assert runtime.vars == {'x': 5, '__forced_0': 0}
    runtime.cycle(['Root.Stop'])
    assert runtime.current_state.path == ('Root', 'Idle')
    assert runtime.vars == {'x': 5, '__forced_0': 0}


def test_hot_start_accepts_the_only_value_the_variable_has_at_rest():
    model = load_state_machine_from_text(MODEL)
    runtime = SimulationRuntime(
        model, initial_state='Root.Run.A', initial_vars={'x': 1, '__forced_0': 0})
    runtime.cycle()
    assert runtime.vars == {'x': 2, '__forced_0': 0}


def test_hot_start_rejects_a_raised_variable():
    model = load_state_machine_from_text(MODEL)
    with pytest.raises(ValueError) as caught:
        SimulationRuntime(model, initial_state='Root.Run.A', initial_vars={'x': 1, '__forced_0': 1})
    message = str(caught.value)
    assert '__forced_0' in message and 'forced' in message and '1' in message


def test_a_cold_start_rejects_a_raised_variable_as_well():
    model = load_state_machine_from_text(MODEL)
    with pytest.raises(ValueError) as caught:
        SimulationRuntime(model, initial_vars={'__forced_0': 1})
    assert '__forced_0' in str(caught.value)
    runtime = SimulationRuntime(model, initial_vars={'x': 4, '__forced_0': 0})
    runtime.cycle()
    assert runtime.vars == {'x': 5, '__forced_0': 0}


def test_hot_start_still_asks_for_the_variables_of_the_model():
    model = load_state_machine_from_text(MODEL)
    with pytest.raises(ValueError) as caught:
        SimulationRuntime(model, initial_state='Root.Run.A', initial_vars={})
    assert "Missing: ['x']" in str(caught.value)


def test_the_caller_dictionary_is_left_alone():
    model = load_state_machine_from_text(MODEL)
    given = {'x': 2}
    SimulationRuntime(model, initial_state='Root.Run.A', initial_vars=given)
    assert given == {'x': 2}


class TestInitCommand:
    def _processor(self):
        machine = load_state_machine_from_text(MODEL)
        return CommandProcessor(SimulationRuntime(machine), state_machine=machine, use_color=False)

    def test_init_does_not_ask_for_the_hidden_variable(self):
        processor = self._processor()
        result = processor.process('init Root.Run.B x=5')
        assert 'Error' not in result.output, result.output
        processor.process('cycle Root.Stop')
        assert processor.runtime.current_state.path == ('Root', 'Idle')
        assert processor.runtime.vars == {'x': 5, '__forced_0': 0}

    def test_init_reports_a_raised_variable_readably(self):
        processor = self._processor()
        before = processor.runtime
        result = processor.process('init Root.Run.B x=5 __forced_0=1')
        assert result.exit_code == 1
        assert result.output.startswith('Initialization failed:')
        assert '__forced_0' in result.output
        assert processor.runtime is before

    def test_init_still_asks_for_the_variables_of_the_model(self):
        result = self._processor().process('init Root.Run.B')
        assert result.exit_code == 1
        assert "Missing: ['x']" in result.output

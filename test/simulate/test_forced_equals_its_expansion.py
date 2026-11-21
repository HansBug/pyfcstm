"""A forced declaration is syntactic sugar: the simulator treats it exactly like its expansion.

The expansion is the model that the declaring one exports as FCSTM text. Loaded
as an ordinary model it knows nothing about forced declarations, so any special
treatment of the declaring model would make the two behave differently.
"""

import logging

import pytest

from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest

MODEL = '''def int x = 0;
state Root {
    event Stop;
    event Go;
    [*] -> Run;
    state Run {
        [*] -> A;
        state A { during { x = x + 1; } }
        state B;
        A -> B :: Go;
    }
    state Idle;
    !Run -> Idle : /Stop;
    Idle -> Run :: Go;
}'''

EVENT_PLANS = [
    [],
    ['Root.Stop'],
    ['Root.Run.A.Go'],
    ['Root.Run.A.Go', 'Root.Stop', 'Root.Idle.Go'],
    ['Root.Stop', 'Root.Stop'],
]


@pytest.fixture
def pair():
    declared = load_state_machine_from_text(MODEL)
    assert declared.forced_variables == ('__forced_0',)
    expansion = load_state_machine_from_text(str(declared.to_ast_node()))
    assert expansion.forced_variables == ()
    return declared, expansion


def _outcome(call):
    try:
        runtime = call()
    except ValueError as err:
        return 'ValueError', str(err)
    rows = []
    for events in EVENT_PLANS:
        runtime.cycle(events)
        rows.append((runtime.current_state.path if not runtime.is_ended else None,
                     sorted(runtime.vars.items())))
    return rows


def test_a_cold_start_runs_the_same_cycles(pair):
    results = [_outcome(lambda model=model: SimulationRuntime(model)) for model in pair]
    assert results[0] == results[1]
    assert isinstance(results[0], list)


@pytest.mark.parametrize('state', ['Root.Run.A', 'Root.Run.B', 'Root.Idle'])
@pytest.mark.parametrize('hidden', [None, 0, 1])
def test_a_hot_start_gives_the_same_outcome(pair, state, hidden):
    """The hidden variable is an ordinary variable: given or missing, any value."""
    given = {'x': 5} if hidden is None else {'x': 5, '__forced_0': hidden}
    results = [
        _outcome(lambda model=model: SimulationRuntime(
            model, initial_state=state, initial_vars=dict(given)))
        for model in pair
    ]
    assert results[0] == results[1]


def test_a_hot_start_without_the_hidden_variable_is_refused_like_any_missing_variable(pair):
    for model in pair:
        with pytest.raises(ValueError) as caught:
            SimulationRuntime(model, initial_state='Root.Run.A', initial_vars={'x': 1})
        assert "Missing: ['__forced_0']" in str(caught.value)


class TestInitCommand:
    @pytest.fixture(autouse=True)
    def _keep_the_simulator_log_level(self):
        # The command processor sets the level of the simulator's shared
        # logger; put it back so tests that run later in the same process see
        # the logger as they would without these tests.
        logger = logging.getLogger("pyfcstm.simulate")
        level = logger.level
        yield
        logger.setLevel(level)

    @staticmethod
    def _run(model, line):
        processor = CommandProcessor(SimulationRuntime(model), state_machine=model, use_color=False)
        result = processor.process(line)
        processor.process('cycle Root.Stop')
        return (result.exit_code, result.output, processor.runtime.current_state.path,
                sorted(processor.runtime.vars.items()))

    @pytest.mark.parametrize('line', [
        'init Root.Run.B x=5',
        'init Root.Run.B x=5 __forced_0=0',
        'init Root.Run.B x=5 __forced_0=1',
    ])
    def test_init_answers_the_same(self, pair, line):
        assert self._run(pair[0], line) == self._run(pair[1], line)

    def test_init_asks_for_the_hidden_variable_like_any_other(self, pair):
        for model in pair:
            result = CommandProcessor(
                SimulationRuntime(model), state_machine=model, use_color=False
            ).process('init Root.Run.B x=5')
            assert result.exit_code == 1
            assert "Missing: ['__forced_0']" in result.output

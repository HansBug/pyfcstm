"""A forced declaration is syntactic sugar: the simulator treats it exactly like its expansion.

The expansion is the model that the declaring one exports as FCSTM text. Loaded
as an ordinary model it knows nothing about forced declarations, so any special
treatment of the declaring model would make the two behave differently.
"""

import logging
import random

import pytest

from pyfcstm.entry.simulate.commands import CommandProcessor
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.model.region import walk_namespaces
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest

MODELS = {
    'nested': '''def int x = 0;
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
}''',
    'two_declarations_with_guards': '''def int x = 0;
def int y = 0;
state Root {
    event Back;
    [*] -> Run;
    state Run {
        [*] -> A;
        state A { during { x = x + 1; } }
        state B { during { y = y + 1; } }
        A -> B : if [x >= 2];
    }
    state Idle { [*] -> Wait; state Wait { during { y = y + 1; } } }
    !Run -> Idle : if [y == 0 && x >= 3];
    !Idle -> Run : /Back;
}''',
    'wildcard_and_a_pseudo_state': '''def int n = 0;
state Root {
    event Reset;
    event Next;
    [*] -> Run;
    state Run {
        [*] -> J;
        pseudo state J;
        state A { during { n = n + 1; } }
        state B;
        J -> A;
        A -> B :: Next;
    }
    state Leaf { during { n = n + 2; } }
    state Home;
    Run -> Leaf :: Next;
    Leaf -> Run :: Next;
    !* -> Home : /Reset;
}''',
    'with_history': '''def int n = 0;
state Root {
    event Pause;
    event Resume;
    [*] -> Work;
    state Work {
        [*] -> A;
        [H] -> A;
        state A { during { n = n + 1; } }
        state B;
        A -> B : if [n >= 2];
    }
    state Hold;
    !Work -> Hold : /Pause;
    Hold -> Work.[H] : /Resume;
}''',
}


def _events(model):
    names = []
    for namespace in walk_namespaces(model.root_state):
        for edge in namespace.transitions:
            if edge.event is not None and edge.event.path_name not in names:
                names.append(edge.event.path_name)
    return sorted(names)


def _leaves(model):
    return ['.'.join(state.path) for state in model.walk_states()
            if not state.substates and not state.is_pseudo and not state.is_forced_gate]


def _plans(events, seed=7, count=6):
    rng = random.Random(seed)
    return [[name for name in events if rng.random() < 0.4] for _ in range(count)]


@pytest.fixture(params=sorted(MODELS))
def pair(request):
    declared = load_state_machine_from_text(MODELS[request.param])
    assert declared.forced_variables
    expansion = load_state_machine_from_text(str(declared.to_ast_node()))
    assert expansion.forced_variables == ()
    return declared, expansion


def _outcome(model, plans, **start):
    try:
        runtime = SimulationRuntime(model, **start)
    except ValueError as err:
        return 'ValueError', str(err)
    rows = []
    for events in plans:
        result = runtime.cycle(events)
        rows.append((
            runtime.current_state.path if not runtime.is_ended else None,
            sorted(runtime.vars.items()),
            result.delta,
            tuple(result.consumed_events),
        ))
    return rows


def test_a_cold_start_runs_the_same_cycles(pair):
    declared, expansion = pair
    plans = _plans(_events(declared)) + _plans(_events(declared), seed=11)
    outcomes = [_outcome(model, plans) for model in pair]
    assert outcomes[0] == outcomes[1]
    assert isinstance(outcomes[0], list)


@pytest.mark.parametrize('hidden', [None, 0, 1])
def test_a_hot_start_gives_the_same_outcome_at_every_leaf(pair, hidden):
    """The hidden variable is an ordinary variable: given or missing, any value."""
    declared, expansion = pair
    plans = _plans(_events(declared), seed=3, count=4)
    hidden_names = set(declared.forced_variables)
    given = {name: 0 for name in declared.defines if name not in hidden_names}
    if hidden is not None:
        given.update({name: hidden for name in hidden_names})
    for leaf in _leaves(declared):
        outcomes = [_outcome(model, plans, initial_state=leaf, initial_vars=dict(given))
                    for model in pair]
        assert outcomes[0] == outcomes[1], leaf


def test_a_hot_start_without_the_hidden_variable_is_refused_like_any_missing_variable(pair):
    declared, _ = pair
    given = {name: 0 for name in declared.defines if name not in declared.forced_variables}
    leaf = _leaves(declared)[0]
    for model in pair:
        with pytest.raises(ValueError) as caught:
            SimulationRuntime(model, initial_state=leaf, initial_vars=dict(given))
        assert "__forced_0" in str(caught.value) and 'Missing' in str(caught.value)


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
        processor.process('cycle')
        return (result.exit_code, result.output, processor.runtime.current_state.path,
                sorted(processor.runtime.vars.items()))

    @pytest.mark.parametrize('hidden', ['', ' __forced_0=0', ' __forced_0=1'])
    def test_init_answers_the_same(self, pair, hidden):
        declared, _ = pair
        users = ' '.join('%s=0' % name for name in declared.defines
                         if name not in declared.forced_variables)
        line = 'init %s %s%s' % (_leaves(declared)[0], users, hidden)
        assert self._run(pair[0], line) == self._run(pair[1], line)

    def test_init_asks_for_the_hidden_variable_like_any_other(self, pair):
        declared, _ = pair
        users = ' '.join('%s=0' % name for name in declared.defines
                         if name not in declared.forced_variables)
        for model in pair:
            result = CommandProcessor(
                SimulationRuntime(model), state_machine=model, use_color=False
            ).process('init %s %s' % (_leaves(declared)[0], users))
            assert result.exit_code == 1
            assert "__forced_0" in result.output

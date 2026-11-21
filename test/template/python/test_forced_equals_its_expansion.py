"""A generated Python runtime treats a forced declaration exactly like its expansion.

The expansion is the model that the declaring one exports as FCSTM text; loaded
as an ordinary model it knows nothing about forced declarations. The generated
code of both must run the same cycles and take the same hot starts.
"""

import pytest

from pyfcstm.model import load_state_machine_from_text

from test.simulate.test_forced_equals_its_expansion import MODELS, _events, _leaves, _plans

from .test_runtime import _render_python_module

pytestmark = pytest.mark.unittest


@pytest.fixture(params=sorted(MODELS))
def models(request):
    """The declaring model's own text and the text of its expansion."""
    declared = load_state_machine_from_text(MODELS[request.param])
    assert declared.forced_variables
    return declared, MODELS[request.param], str(declared.to_ast_node())


def _run(source, plans, **start):
    with _render_python_module(source) as module:
        try:
            machine = module.RootMachine(**start)
        except ValueError as err:
            return 'ValueError', str(err)
        rows = []
        for events in plans:
            machine.cycle(events)
            rows.append((machine.current_state_path if not machine.is_ended else None,
                         sorted(machine.vars.items())))
        return rows


def test_a_cold_start_runs_the_same_cycles(models):
    declared, own_text, expansion_text = models
    plans = _plans(_events(declared)) + _plans(_events(declared), seed=11)
    outcomes = [_run(source, plans) for source in (own_text, expansion_text)]
    assert outcomes[0] == outcomes[1]
    assert isinstance(outcomes[0], list)


@pytest.mark.parametrize('hidden', [None, 0, 1])
def test_a_hot_start_gives_the_same_outcome(models, hidden):
    """The hidden variable is an ordinary variable: given or missing, any value."""
    declared, own_text, expansion_text = models
    plans = _plans(_events(declared), seed=3, count=4)
    hidden_names = set(declared.forced_variables)
    given = {name: 0 for name in declared.defines if name not in hidden_names}
    if hidden is not None:
        given.update({name: hidden for name in hidden_names})
    leaf = _leaves(declared)[0]
    outcomes = [_run(source, plans, initial_state=leaf, initial_vars=dict(given))
                for source in (own_text, expansion_text)]
    assert outcomes[0] == outcomes[1]


def test_a_hot_start_without_the_hidden_variable_is_refused_like_any_missing_variable(models):
    declared, own_text, expansion_text = models
    given = {name: 0 for name in declared.defines if name not in declared.forced_variables}
    for source in (own_text, expansion_text):
        outcome = _run(source, [], initial_state=_leaves(declared)[0], initial_vars=dict(given))
        assert outcome[0] == 'ValueError'
        assert 'Missing' in outcome[1] and '__forced_0' in outcome[1]

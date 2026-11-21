"""A generated Python runtime treats a forced declaration exactly like its expansion.

The expansion is the model that the declaring one exports as FCSTM text; loaded
as an ordinary model it knows nothing about forced declarations. The generated
code of both must run the same cycles and take the same hot starts.
"""

import pytest

from pyfcstm.model import load_state_machine_from_text

from .test_runtime import _render_python_module

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


def _expansion_text():
    declared = load_state_machine_from_text(MODEL)
    assert declared.forced_variables == ('__forced_0',)
    return str(declared.to_ast_node())


def _run(source, **start):
    with _render_python_module(source) as module:
        try:
            machine = module.RootMachine(**start)
        except ValueError as err:
            return 'ValueError', str(err)
        rows = []
        for events in EVENT_PLANS:
            machine.cycle(events)
            rows.append((machine.current_state_path, sorted(machine.vars.items())))
        return rows


def test_a_cold_start_runs_the_same_cycles():
    declared, expansion = _run(MODEL), _run(_expansion_text())
    assert declared == expansion
    assert isinstance(declared, list)


@pytest.mark.parametrize('state', ['Root.Run.A', 'Root.Run.B', 'Root.Idle'])
@pytest.mark.parametrize('hidden', [None, 0, 1])
def test_a_hot_start_gives_the_same_outcome(state, hidden):
    """The hidden variable is an ordinary variable: given or missing, any value."""
    given = {'x': 5} if hidden is None else {'x': 5, '__forced_0': hidden}
    declared = _run(MODEL, initial_state=state, initial_vars=dict(given))
    expansion = _run(_expansion_text(), initial_state=state, initial_vars=dict(given))
    assert declared == expansion


def test_a_hot_start_without_the_hidden_variable_is_refused_like_any_missing_variable():
    for source in (MODEL, _expansion_text()):
        outcome = _run(source, initial_state='Root.Run.A', initial_vars={'x': 1})
        assert outcome[0] == 'ValueError'
        assert "Missing: ['__forced_0']" in outcome[1]

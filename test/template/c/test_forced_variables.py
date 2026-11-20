"""Generated C runtimes keep the hidden variables of forced transitions at rest."""

import pytest

from ._utils import build_c_runtime, render_c_runtime

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

REJECTED = 'belongs to a forced transition and is 0 whenever the machine rests'


def test_a_cold_start_begins_with_the_hidden_variable_lowered():
    with render_c_runtime(MODEL) as (runtime, _):
        assert runtime.vars == {'x': 0, '__forced_0': 0}
        runtime.cycle()
        runtime.cycle(['Root.Stop'])
        assert runtime.current_state_path == ('Root', 'Idle')
        assert runtime.vars == {'x': 1, '__forced_0': 0}


def test_a_hot_start_with_the_hidden_variable_at_rest_works_from_the_restored_state():
    runtime = build_c_runtime(MODEL, initial_state='Root.Run.B', initial_vars={'x': 5})
    try:
        assert runtime.vars == {'x': 5, '__forced_0': 0}
        runtime.cycle(['Root.Stop'])
        assert runtime.current_state_path == ('Root', 'Idle')
        assert runtime.vars == {'x': 5, '__forced_0': 0}
    finally:
        runtime.close()


@pytest.mark.parametrize('kwargs', [
    {'initial_state': 'Root.Run.A', 'initial_vars': {'x': 1, '__forced_0': 1}},
    {'initial_vars': {'x': 0, '__forced_0': 1}},
], ids=['hot', 'cold'])
def test_a_raised_hidden_variable_is_rejected(kwargs):
    with pytest.raises(ValueError, match=REJECTED) as caught:
        build_c_runtime(MODEL, **kwargs)
    assert '__forced_0' in str(caught.value)

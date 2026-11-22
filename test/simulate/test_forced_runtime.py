"""Forced transitions of models without regions, through the public simulator.

The scenarios that the generated runtimes run as well live in the shared
fixture corpus (``forced_*``). What is here observes something the shared
corpus does not carry: event accounting and what a handler sees.
"""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime

pytestmark = pytest.mark.unittest


def test_an_event_of_a_forced_transition_that_takes_nothing_is_not_used():
    runtime = SimulationRuntime(load_state_machine_from_text('''def int seq = 0;
state Root {
    event Reset;
    [*] -> P;
    state P {
        [*] -> A1 : if [seq < 2];
        state A1 { during { seq = seq + 1; } }
    }
    state Done;
    !P -> P : /Reset;
    P -> Done;
}'''))
    runtime.cycle()
    runtime.cycle()
    # P cannot be entered a second time, so the forced transition does not
    # happen: A1 is not left, the event stays unused, and the unrelated
    # transition P -> Done does not pick the machine up half-way.
    result = runtime.cycle('Root.Reset')
    assert runtime.current_state.path == ('Root', 'P', 'A1')
    assert (result.consumed_events, result.unconsumed_events) == ((), ('Root.Reset',))
    assert result.delta is False
    assert runtime.vars == {'seq': 3, '__forced_0': 0}


def test_an_event_present_during_entry_is_used_once_in_the_cycle_that_takes_the_source_away():
    runtime = SimulationRuntime(load_state_machine_from_text('''state Root {
    event Stop;
    [*] -> P;
    state P {
        [*] -> j;
        pseudo state j;
        state A1;
        j -> A1;
    }
    state Off;
    !P -> Off : /Stop;
}'''))
    # The entry only passes through j, which holds no forced transition.
    first = runtime.cycle('Root.Stop')
    assert runtime.current_state.path == ('Root', 'P', 'A1')
    assert (first.consumed_events, first.unconsumed_events) == ((), ('Root.Stop',))
    second = runtime.cycle('Root.Stop')
    assert runtime.current_state.path == ('Root', 'Off')
    assert second.consumed_events == ('Root.Stop',)


def test_a_handler_sees_the_hidden_variable_while_the_source_is_being_left():
    model = load_state_machine_from_text('''state Root {
    event Stop;
    [*] -> Run;
    state Run {
        exit abstract LeaveRun;
        [*] -> A;
        state A { exit abstract LeaveA; }
    }
    state Idle { enter abstract ArriveIdle; }
    !Run -> Idle : /Stop;
}''')
    runtime = SimulationRuntime(model)
    seen = []
    for path in ('Root.Run.A.LeaveA', 'Root.Run.LeaveRun', 'Root.Idle.ArriveIdle'):
        runtime.register_abstract_handler(
            path, lambda ctx, path=path: seen.append((path.rsplit('.', 1)[-1], ctx.vars['__forced_0'])))
    runtime.cycle()
    runtime.cycle('Root.Stop')
    # The variable is raised by the transition that leaves A, after A's exit
    # action, and lowered by the transition that enters Idle.
    assert seen == [('LeaveA', 0), ('LeaveRun', 1), ('ArriveIdle', 0)]
    assert runtime.vars == {'__forced_0': 0}

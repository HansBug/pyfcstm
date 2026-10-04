"""Same-cycle initial/exit loops through the public simulator and CLI."""

import sys

import pytest
from click.testing import CliRunner

from pyfcstm.entry.cli import cli
from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime, SimulationRuntimeDfsError

pytestmark = pytest.mark.unittest

MODEL = '''
state R {
    state A {
        state B {
            pseudo state P;
            [*] -> P;
        }
        [*] -> B;
    }
    state Idle;
    [*] -> Idle;
    Idle -> A :: go;
    !A -> A :: loop;
}
'''


@pytest.mark.parametrize("recursion_limit", [150, 1000])
def test_nested_initial_loop_reports_path_and_preserves_cycle(recursion_limit):
    runtime = SimulationRuntime(load_state_machine_from_text(MODEL))
    runtime.cycle()
    history = list(runtime.history)
    previous_limit = sys.getrecursionlimit()
    try:
        sys.setrecursionlimit(recursion_limit)
        with pytest.raises(SimulationRuntimeDfsError, match='same cycle') as caught:
            runtime.cycle(['R.Idle.go', 'R.A.loop'])
    finally:
        sys.setrecursionlimit(previous_limit)
    assert 'R.A.B.P' in str(caught.value)
    assert 'stoppable' in str(caught.value)
    assert 'guard' in str(caught.value)
    assert runtime.current_state.path == ('R', 'Idle')
    assert runtime.cycle_count == 1
    assert runtime.history == history
    assert sys.getrecursionlimit() == previous_limit


def test_missing_loop_event_still_rejects_dead_end():
    runtime = SimulationRuntime(load_state_machine_from_text(MODEL))
    runtime.cycle()
    result = runtime.cycle('R.Idle.go')
    assert runtime.current_state.path == ('R', 'Idle')
    assert result.unconsumed_events == ('R.Idle.go',)


@pytest.mark.parametrize('source,events,want', [
    (MODEL.replace('!A -> A :: loop;',
                   '!A -> A :: loop; Idle -> Idle :: go;'),
     ['R.Idle.go', 'R.A.loop'], ('R', 'Idle')),
    ('''state R {
        pseudo state P; state Ready;
        [*] -> P; [*] -> Ready;
        P -> P;
    }''', [], ('R', 'Ready')),
    ('''state R {
        pseudo state P; state Ready;
        [*] -> P; P -> P; P -> Ready;
    }''', [], ('R', 'Ready')),
])
def test_cyclic_candidate_does_not_hide_stoppable_fallback(source, events, want):
    runtime = SimulationRuntime(load_state_machine_from_text(source))
    runtime.cycle()
    result = runtime.cycle(events, diagnostics=True)
    assert runtime.current_state.path == want
    assert result.delta is False


def test_guarded_reentry_can_finish_after_variable_progress():
    runtime = SimulationRuntime(load_state_machine_from_text('''
        def int n = 0;
        state R {
            state A {
                enter { n = n + 1; }
                pseudo state P; state Ready;
                [*] -> P : if [n < 3];
                [*] -> Ready : if [n >= 3];
                P -> [*];
            }
            state Idle;
            [*] -> Idle;
            Idle -> A :: go;
            A -> A;
        }
    '''))
    runtime.cycle()
    result = runtime.cycle('R.Idle.go')
    assert runtime.current_state.path == ('R', 'A', 'Ready')
    assert runtime.vars == {'n': 3}
    assert result.delta is False


def test_cli_nested_initial_loop_has_readable_failure(tmp_path):
    path = tmp_path / 'loop.fcstm'
    path.write_text(MODEL)
    result = CliRunner().invoke(cli, [
        'simulate', '-i', str(path), '--no-color',
        '-e', 'cycle; cycle R.Idle.go R.A.loop',
    ])
    assert result.exit_code == 1
    assert not isinstance(result.exception, RecursionError)
    assert 'same cycle' in result.output
    assert 'R.A.B.P' in result.output
    assert 'guard' in result.output
    assert 'Traceback' not in result.output


def test_initial_pseudo_cycle_without_fallback_raises():
    runtime = SimulationRuntime(load_state_machine_from_text(
        'state R { pseudo state P; [*] -> P; P -> P; }'
    ))
    with pytest.raises(SimulationRuntimeDfsError, match='R.P'):
        runtime.cycle(diagnostics=True)
    assert runtime.cycle_count == 0
    assert runtime.history == []


def test_converging_dead_branches_are_not_a_loop():
    runtime = SimulationRuntime(load_state_machine_from_text('''
        state R {
            pseudo state P; pseudo state Q; pseudo state Dead;
            [*] -> P;
            P -> Dead;
            P -> Q;
            Q -> Dead;
        }
    '''))
    result = runtime.cycle()
    assert result.delta is True
    assert runtime.cycle_count == 1

"""A forced declaration that reaches regions behaves exactly like its expansion.

The expansion is the model that the declaring one exports as FCSTM text. It is
made of ordinary transitions only, so loaded again it knows nothing about the
declaration. Every observable of a cycle has to be the same for both.
"""

import pytest

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.simulate import SimulationRuntime
from test.simulate.test_forced_equals_its_expansion import _events, _plans

pytestmark = pytest.mark.unittest

REGION_MODELS = {
    'two_regions_and_exit_actions': '''def int seq = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1 { exit { seq = seq * 10 + 1; } } }
        region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 2; } } }
    }
    state Idle;
    !Run -> Idle : /Stop;
}''',
    'nested_owner_inside_a_region': '''def int seq = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        exit { seq = seq * 10 + 9; }
        region A {
            [*] -> Inner;
            state Inner {
                exit { seq = seq * 10 + 3; }
                region P { [*] -> P1; state P1 { exit { seq = seq * 10 + 1; } } }
                region Q { [*] -> Q1; state Q1 { exit { seq = seq * 10 + 2; } } }
            }
        }
        region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 4; } } }
    }
    state Idle;
    !Run -> Idle : /Stop;
}''',
    'condition_made_true_while_the_regions_work': '''def int x = 0;
def int work = 0;
state Root {
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1 { during { x = x + 1; } exit { work = work * 10 + 1; } } }
        region B { [*] -> B1; state B1 { during { work = work + 1; } exit { work = work * 10 + 2; } } }
    }
    state Off;
    !Run -> Off : if [x >= 2];
}''',
    'target_that_cannot_be_entered_for_a_while': '''def int n = 0;
def int ready = 0;
def int seq = 0;
state Root {
    event Stop;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1 { exit { seq = seq * 10 + 1; } } }
        region B {
            [*] -> B1;
            state B1 { during { n = n + 1; ready = (n >= 3) ? 1 : 0; } exit { seq = seq * 10 + 2; } }
        }
    }
    state Idle { [*] -> I1 : if [ready > 0]; state I1; }
    !Run -> Idle : /Stop;
}''',
    'two_declarations_on_one_owner': '''def int seq = 0;
state Root {
    event Alpha;
    event Beta;
    [*] -> Run;
    state Run {
        region A { [*] -> A1; state A1 { exit { seq = seq * 10 + 1; } } }
        region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 2; } } }
    }
    state ToAlpha;
    state ToBeta;
    !Run -> ToAlpha : /Alpha;
    !Run -> ToBeta : /Beta;
}''',
    'declaration_above_a_composite_and_an_owner': '''def int seq = 0;
state Root {
    event Halt;
    [*] -> Sys;
    state Sys {
        [*] -> Run;
        state Run {
            region A { [*] -> A1; state A1 { exit { seq = seq * 10 + 1; } } A1 -> A2 : if [seq == 0]; state A2 { exit { seq = seq * 10 + 5; } } }
            region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 2; } } }
        }
    }
    state Safe;
    !Sys -> Safe : /Halt;
}''',
    'declaration_written_inside_a_region': '''def int seq = 0;
state Root {
    event Reset;
    [*] -> P;
    state P {
        region A {
            [*] -> Q;
            state Q { exit { seq = seq * 10 + 4; } state Q1; [*] -> Q1; }
            state Home { enter { seq = seq * 10 + 9; } }
            !Q -> Home : /Reset;
        }
        region B { [*] -> B1; state B1 { exit { seq = seq * 10 + 3; } } }
    }
}''',
}


@pytest.fixture(params=sorted(REGION_MODELS))
def pair(request):
    declared = load_state_machine_from_text(REGION_MODELS[request.param])
    assert declared.forced_variables
    expansion = load_state_machine_from_text(str(declared.to_ast_node()))
    assert expansion.forced_variables == ()
    return declared, expansion


def _outcome(model, plans):
    runtime = SimulationRuntime(model)
    rows = []
    for events in plans:
        result = runtime.cycle(events)
        rows.append((
            str(runtime.configuration),
            sorted(runtime.vars.items()),
            runtime.is_ended,
            result.delta,
            tuple(result.consumed_events),
            tuple(result.unconsumed_events),
        ))
    return rows


def test_the_export_loads_to_the_machine_that_runs(pair):
    declared, expansion = pair
    assert str(expansion.to_ast_node()) == str(declared.to_ast_node())
    assert list(expansion.defines) == list(declared.defines)


def test_a_cold_start_runs_the_same_cycles(pair):
    declared, _ = pair
    names = _events(declared)
    plans = [[]] * 3 + _plans(names, seed=7, count=8) + _plans(names, seed=11, count=8)
    # Every event alone at least once, then all of them together.
    plans += [[name] for name in names] + [list(names)] + [[]] * 4
    outcomes = [_outcome(model, plans) for model in pair]
    assert outcomes[0] == outcomes[1]


def test_the_declaration_is_taken_at_all(pair):
    """A model that never leaves its group would make the comparison empty."""
    declared, _ = pair
    names = _events(declared)
    plans = [[]] * 2 + [[name] for name in names] + [list(names)] + [[]] * 6
    configurations = {row[0] for row in _outcome(declared, plans)}
    assert len(configurations) > 1

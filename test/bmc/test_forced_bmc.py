"""BMC checks machines with forced declarations through their lowered form."""

import json

import pytest

from test.bmc.test_guarded_initial_scaling import bmc_status, run_bmc

pytestmark = pytest.mark.unittest

MODEL = '''def int x = 0;
state Root {
    event Stop;
    [*] -> P;
    state P {
        [*] -> a1;
        state a1;
        a1 -> [*] : if [x > 0];
    }
    state Q;
    !P -> Q : /Stop;
}'''


def _model(tmp_path):
    path = tmp_path / 'model.fcstm'
    path.write_text(MODEL, encoding='utf-8')
    return path


def test_the_forced_declaration_is_taken_with_its_event(tmp_path):
    query = (
        'init state("Root.P.a1");\n'
        'assume event("Root.Stop", 0) == true;\n'
        'check reach <= 1: active("Root.Q");'
    )
    result = run_bmc(_model(tmp_path), query, tmp_path, '--json')
    payload = json.loads(result.stdout)
    assert payload['result']['status'] == 'sat'
    assert payload['replay']['ok'] is True


@pytest.mark.parametrize('havoc', ['havoc *', 'havoc { x }', 'havoc { __forced_0 }'])
def test_a_havocked_start_never_has_a_forced_exit_in_flight(tmp_path, havoc):
    """Without the event the target stays out of reach, whatever is relaxed."""
    query = (
        'init state("Root.P.a1") %s;\n'
        'assume event("Root.Stop", 0) == false;\n'
        'check reach <= 1: active("Root.Q");' % havoc
    )
    assert bmc_status(_model(tmp_path), query, tmp_path) == 'unsat'


def test_a_raised_variable_is_no_legal_start(tmp_path):
    query = (
        'init state("Root.P.a1") havoc { __forced_0 } where var("__forced_0") == 1;\n'
        'check reach <= 1: active("Root.Q");'
    )
    result = run_bmc(_model(tmp_path), query, tmp_path, '--json')
    payload = json.loads(result.stdout)
    assert payload['result']['feasibility']['infeasible_stage'] == 'initialization'
    assert payload['result']['feasibility']['initialization']['status'] == 'unsat'

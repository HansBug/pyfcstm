"""BMC answers about a machine with forced declarations the way it answers about its expansion."""

import json

import pytest

from pyfcstm.model import load_state_machine_from_text
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


QUERIES = {
    'cold': 'check reach <= 3: active("Root.Q");',
    'cold_without_the_event': (
        'assume event("Root.Stop", *) == false;\n'
        'check reach <= 3: active("Root.Q");'
    ),
    'hot_start': 'init state("Root.P.a1");\ncheck reach <= 2: active("Root.Q");',
    'hot_start_without_the_event': (
        'init state("Root.P.a1");\n'
        'assume event("Root.Stop", *) == false;\n'
        'check reach <= 2: active("Root.Q");'
    ),
    'havoc_everything': 'init cold havoc *;\ncheck reach <= 3: active("Root.Q");',
    'havoc_everything_without_the_event': (
        'init cold havoc *;\n'
        'assume event("Root.Stop", *) == false;\n'
        'check reach <= 3: active("Root.Q");'
    ),
    'havoc_everything_from_a_state': (
        'init state("Root.P.a1") havoc *;\n'
        'assume event("Root.Stop", *) == false;\n'
        'check reach <= 1: active("Root.Q");'
    ),
    'havoc_the_hidden_variable_only': (
        'init state("Root.P.a1") havoc { __forced_0 };\n'
        'assume event("Root.Stop", *) == false;\n'
        'check reach <= 1: active("Root.Q");'
    ),
    'invariant_of_the_hidden_variable': (
        'init cold havoc *;\ncheck invariant <= 2: var("__forced_0") == 0;'
    ),
}


@pytest.mark.parametrize('name', sorted(QUERIES))
def test_a_query_gets_the_same_answer_as_on_the_expansion(tmp_path, name):
    """The hidden variable is an ordinary variable, whatever the query relaxes."""
    declared = _model(tmp_path)
    expansion = tmp_path / 'expansion.fcstm'
    expansion.write_text(
        str(load_state_machine_from_text(MODEL).to_ast_node()), encoding='utf-8')
    work = tmp_path / 'work'
    work.mkdir()

    on_declared = bmc_status(declared, QUERIES[name], work)
    on_expansion = bmc_status(expansion, QUERIES[name], work)

    assert on_declared == on_expansion

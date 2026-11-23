"""Built-in template ``c`` and models that declare regions."""

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli
from test.testings.native_semantic_alignment import iter_native_semantic_cases
from test.testings.simulate_semantics import iter_semantic_cases

pytestmark = pytest.mark.unittest

REGION_SOURCE = 'state Root { region Worker { state Idle; [*] -> Idle; } }'


def test_generate_writes_a_runtime_for_a_region_model(tmp_path):
    source = tmp_path / 'regions.fcstm'
    source.write_text(REGION_SOURCE, encoding='utf-8')
    output = tmp_path / 'generated'
    result = simulate_entry(
        pyfcstmcli,
        ['pyfcstm', 'generate', '-i', str(source), '--template', 'c', '-o', str(output)],
    )
    text = result.stdout + result.stderr
    assert result.exitcode == 0, text
    assert 'Traceback' not in text
    assert {'machine.c', 'machine.h'} <= {item.name for item in output.iterdir()}
    header = (output / 'machine.h').read_text(encoding='utf-8')
    # A model with regions has no single current state, so no query for one.
    assert 'current_state_id' not in header
    assert 'hot_start_at' in header
    assert 'configuration_format' in header


def test_the_whole_region_corpus_runs_on_the_c_template():
    selected = {case.id for case in iter_native_semantic_cases('c')}
    regions = {case.id for case in iter_semantic_cases(categories=['regions'])}
    assert regions
    assert regions <= selected

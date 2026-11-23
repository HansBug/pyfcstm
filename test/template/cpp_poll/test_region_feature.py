"""Built-in template ``cpp_poll`` and models that declare regions."""

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli

pytestmark = pytest.mark.unittest

REGION_SOURCE = 'state Root { region Worker { state Idle; [*] -> Idle; } }'


def test_generate_refuses_a_region_model_until_the_template_declares_it(tmp_path):
    source = tmp_path / 'regions.fcstm'
    source.write_text(REGION_SOURCE, encoding='utf-8')
    output = tmp_path / 'generated'
    output.mkdir()
    (output / 'keep.txt').write_text('existing output', encoding='utf-8')
    result = simulate_entry(
        pyfcstmcli,
        ['pyfcstm', 'generate', '-i', str(source), '--template', 'cpp_poll', '-o', str(output)],
    )
    text = result.stdout + result.stderr
    assert result.exitcode != 0
    assert "generate with built-in template 'cpp_poll' does not support region models yet." in text
    assert 'Traceback' not in text
    assert [item.name for item in output.iterdir()] == ['keep.txt']

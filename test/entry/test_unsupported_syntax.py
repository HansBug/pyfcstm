"""Documented CLI commands fail clearly on parsed but unsupported features."""

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli

pytestmark = pytest.mark.unittest


@pytest.mark.parametrize('source', [
    'state Root { region Motor { state A; [*] -> A; } }',
    'state Root { during { if [active("Root")] {} } }',
])
@pytest.mark.parametrize('arguments', [
    ['inspect'], ['inspect', '--collect-errors'], ['inspect', '--format', 'json'],
    ['inspect', '--collect-errors', '--format', 'json'],
    ['plantuml'], ['simulate'], ['diagram'], ['generate'], ['bmc'],
])
def test_cli_refuses_unsupported_model(tmp_path, source, arguments):
    path = tmp_path / 'unsupported.fcstm'
    path.write_text(source, encoding='utf-8')
    if arguments == ['generate']:
        arguments = arguments + ['--template', 'python', '-o', str(tmp_path / 'generated')]
    if arguments == ['bmc']:
        query = tmp_path / 'query.fbmcq'
        query.write_text('check reach <= 1: active("Root");', encoding='utf-8')
        arguments = arguments + ['-q', str(query)]
    result = simulate_entry(pyfcstmcli, ['pyfcstm', *arguments, '-i', str(path)])
    assert result.exitcode != 0
    output = result.stdout + result.stderr
    expected = ('does not support region models yet' if 'region ' in source
                else 'not supported by model construction')
    assert expected in output
    assert 'Traceback' not in output

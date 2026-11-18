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
    ['simulate'], ['diagram'], ['generate'], ['bmc'],
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
                else 'does not support active queries yet')
    assert expected in output
    assert 'Traceback' not in output


@pytest.mark.parametrize('source,expected', [
    ('state Root { region Motor { state A; [*] -> A; } }', 'region 1: Motor'),
    ('state Root { state A; [*] -> A; A -> [*] : if [active("Root.A")]; }', 'active("Root.A")'),
])
def test_plantuml_command_exports_region_and_active_models(tmp_path, source, expected):
    path = tmp_path / 'supported.fcstm'
    path.write_text(source, encoding='utf-8')
    result = simulate_entry(pyfcstmcli, ['pyfcstm', 'plantuml', '-i', str(path)])
    assert result.exitcode == 0
    assert expected in result.stdout
    assert '__active_' not in result.stdout


@pytest.mark.parametrize('output_format', ['human', 'json'])
def test_collecting_inspect_preserves_build_errors_before_backend_refusal(tmp_path, output_format):
    path = tmp_path / 'invalid.fcstm'
    path.write_text('state Root { region Worker { state A; } }', encoding='utf-8')
    result = simulate_entry(pyfcstmcli, [
        'pyfcstm', 'inspect', '-i', str(path), '--collect-errors', '--format', output_format,
    ])
    assert result.exitcode != 0
    output = result.stdout + result.stderr
    assert 'E_INITIAL_TRANSITION_INVALID' in output
    assert 'E_UNSUPPORTED_FEATURE' in output
    assert output.index('E_INITIAL_TRANSITION_INVALID') < output.index('E_UNSUPPORTED_FEATURE')

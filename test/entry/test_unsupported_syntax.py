"""Documented CLI commands fail clearly on parsed but unsupported features."""

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli

pytestmark = pytest.mark.unittest


def _undeclared_template(tmp_path):
    """A custom template directory that does not declare any ``features``."""
    templates = tmp_path / 'undeclared_template'
    templates.mkdir(exist_ok=True)
    (templates / 'config.yaml').write_text('{}', encoding='utf-8')
    (templates / 'machine.txt.j2').write_text('{{ model.root_state.name }}', encoding='utf-8')
    return templates


def _command_arguments(tmp_path, arguments):
    if arguments == ['generate']:
        arguments = arguments + ['-t', str(_undeclared_template(tmp_path)), '-o', str(tmp_path / 'generated')]
    if arguments == ['bmc']:
        query = tmp_path / 'query.fbmcq'
        query.write_text('check reach <= 1: active("Root");', encoding='utf-8')
        arguments = arguments + ['-q', str(query)]
    if arguments == ['simulate']:
        arguments = arguments + ['-e', 'cycle; cycle']
    return arguments


@pytest.mark.parametrize('arguments', [
    ['generate'], ['bmc'],
])
def test_cli_refuses_a_model_with_regions(tmp_path, arguments):
    path = tmp_path / 'unsupported.fcstm'
    path.write_text('state Root { region Motor { state A; [*] -> A; } }', encoding='utf-8')
    arguments = _command_arguments(tmp_path, arguments)
    result = simulate_entry(pyfcstmcli, ['pyfcstm', *arguments, '-i', str(path)])
    assert result.exitcode != 0
    output = result.stdout + result.stderr
    assert 'does not support region models yet' in output
    assert 'Traceback' not in output


REGION_MODEL = """state Root {
    [*] -> Run;
    state Run {
        region Motor { [*] -> Idle; state Idle; }
        region Safety { [*] -> Watch; state Watch; }
    }
}"""


def test_refusal_by_a_custom_template_guides_its_author_and_the_model_writer(tmp_path):
    path = tmp_path / 'machine.fcstm'
    path.write_text(REGION_MODEL, encoding='utf-8')
    arguments = _command_arguments(tmp_path, ['generate'])
    result = simulate_entry(pyfcstmcli, ['pyfcstm', *arguments, '-i', str(path)])
    output = result.stdout + result.stderr
    assert result.exitcode != 0
    assert 'does not support region models yet' in output
    # What happened: how many regions, and where the first one is.
    assert 'declares 2 regions' in output
    assert 'Root.Run.Motor' in output
    # The template author: what to declare, when, and where it is documented.
    assert 'features: [region]' in output
    assert 'config.yaml' in output
    assert 'Declaring model features' in output
    # The model writer: a template that does support regions, or a model without regions.
    assert '--template python' in output
    assert 'take the regions out of the model' in output
    assert 'Traceback' not in output


def test_refusal_by_a_built_in_template_names_the_templates_that_do_support_regions(tmp_path):
    path = tmp_path / 'machine.fcstm'
    path.write_text(REGION_MODEL, encoding='utf-8')
    result = simulate_entry(
        pyfcstmcli,
        ['pyfcstm', 'generate', '-i', str(path), '--template', 'c', '-o', str(tmp_path / 'out')],
    )
    output = result.stdout + result.stderr
    assert result.exitcode != 0
    assert "built-in template 'c' does not support region models yet" in output
    assert 'declares 2 regions' in output
    assert 'Root.Run.Motor' in output
    assert 'Built-in templates that support regions: python' in output
    assert '--template python' in output
    assert 'take the regions out of the model' in output
    # A user cannot edit a built-in template, so it is not told to.
    assert 'features: [region]' not in output
    assert not (tmp_path / 'out').exists()


def test_simulate_runs_a_model_with_regions(tmp_path):
    """``pyfcstm simulate`` drives a model with regions; the command refuses nothing."""
    path = tmp_path / 'regions.fcstm'
    path.write_text(
        'state Root { [*] -> Run; state Run {'
        ' region A { [*] -> X; state X; } region B { [*] -> Y; state Y; } } }',
        encoding='utf-8',
    )
    result = simulate_entry(
        pyfcstmcli, ['pyfcstm', 'simulate', '-i', str(path), '-e', 'cycle; current']
    )
    assert result.exitcode == 0, result.stdout + result.stderr
    assert 'Current State: Root.Run{A: X, B: Y}' in result.stdout
    assert 'does not support' not in result.stdout + result.stderr


@pytest.mark.parametrize('arguments', [
    ['simulate'], ['generate'], ['bmc'],
])
def test_cli_runs_a_model_that_uses_active_queries(tmp_path, arguments):
    """``active()`` is lowered into an ordinary variable, so no command refuses it."""
    path = tmp_path / 'queried.fcstm'
    path.write_text('state Root { during { if [active("Root")] {} } }', encoding='utf-8')
    arguments = _command_arguments(tmp_path, arguments)
    result = simulate_entry(pyfcstmcli, ['pyfcstm', *arguments, '-i', str(path)])
    assert result.exitcode == 0, result.stdout + result.stderr
    assert 'does not support' not in result.stdout + result.stderr


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


@pytest.mark.parametrize('source,expected', [
    ('state Root { region Motor { state A; [*] -> A; } }', 'Motor'),
    ('state Root { state A; [*] -> A; A -> [*] : if [active("Root.A")]; }', 'active(\\"Root.A\\")'),
])
def test_diagram_command_exports_region_and_active_models(tmp_path, source, expected):
    path = tmp_path / 'supported.fcstm'
    path.write_text(source, encoding='utf-8')
    target = tmp_path / 'machine.json'
    result = simulate_entry(pyfcstmcli, ['pyfcstm', 'diagram', '-i', str(path), '-o', str(target)])
    assert result.exitcode == 0, result.stdout + result.stderr
    text = target.read_text(encoding='utf-8')
    assert expected in text
    assert '__active_' not in text

"""Regression tests for the PlantUML CLI configuration boundary."""

from dataclasses import fields

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.entry.base import ClickErrorException
from pyfcstm.entry.plantuml import (
    PLANTUML_OPTION_TYPES,
    _PLANTUML_OPTION_REGISTRY,
    _PLANTUML_PYTHON_ONLY_OPTIONS,
    build_plantuml_output,
    resolve_plantuml_options,
)
from pyfcstm.entry import visualize as visualize_module
from pyfcstm.model.plantuml import PlantUMLOptions


@pytest.fixture()
def input_code_file(tmp_path):
    code_file = tmp_path / 'code.fcstm'
    code_file.write_text(
        'state System {\n'
        '    [*] -> Idle;\n'
        '    state Idle;\n'
        '}\n',
        encoding='utf-8',
    )
    return str(code_file)


def _stderr(result):
    return getattr(result, 'stderr', '') or ''


def test_plantuml_option_registry_covers_model_fields():
    model_fields = {field.name for field in fields(PlantUMLOptions)}
    cli_fields = set(PLANTUML_OPTION_TYPES)
    python_only_fields = set(_PLANTUML_PYTHON_ONLY_OPTIONS)

    assert set(_PLANTUML_OPTION_REGISTRY) == model_fields
    assert cli_fields.isdisjoint(python_only_fields)
    assert cli_fields | python_only_fields == model_fields
    assert python_only_fields == {'custom_colors'}


def test_resolve_plantuml_options_uses_implicit_normal_without_warning():
    options, warnings = resolve_plantuml_options((), dedicated_detail_level=None)

    assert options.detail_level == 'normal'
    assert options.show_lifecycle_actions is None
    assert warnings == ()


def test_resolve_plantuml_options_accepts_detail_level_from_config():
    options, warnings = resolve_plantuml_options(
        ('detail_level=full',), dedicated_detail_level=None
    )

    assert options.detail_level == 'full'
    assert warnings == ()


def test_resolve_plantuml_options_dedicated_level_wins_with_one_warning():
    options, warnings = resolve_plantuml_options(
        ('detail_level=full', 'detail_level=minimal'),
        dedicated_detail_level='normal',
    )

    assert options.detail_level == 'normal'
    assert len(warnings) == 1
    assert '--config[1]' in warnings[0]
    assert '--config[2]' in warnings[0]
    assert '--level' in warnings[0]
    assert 'Using' in warnings[0]


def test_resolve_plantuml_options_normalizes_case_before_comparison():
    options, warnings = resolve_plantuml_options(
        ('detail_level=FULL',), dedicated_detail_level='FuLl'
    )

    assert options.detail_level == 'full'
    assert warnings == ()


def test_resolve_plantuml_options_keeps_last_repeated_config_value():
    options, warnings = resolve_plantuml_options(
        ('max_depth=1', 'max_depth=2'), dedicated_detail_level=None
    )

    assert options.max_depth == 2
    assert len(warnings) == 1
    assert '--config[1]' in warnings[0]
    assert '--config[2]' in warnings[0]


def test_resolve_plantuml_options_does_not_warn_for_preset_override():
    options, warnings = resolve_plantuml_options(
        ('show_lifecycle_actions=false',), dedicated_detail_level='full'
    )

    assert options.detail_level == 'full'
    assert options.show_lifecycle_actions is False
    assert warnings == ()


@pytest.mark.parametrize(
    'assignment, expected_choices',
    [
        ('event_visualization_mode=banana', 'none'),
        ('variable_display_mode=banana', 'note'),
        ('state_name_format=banana', 'name'),
    ],
)
def test_resolve_plantuml_options_rejects_invalid_enum_values(assignment, expected_choices):
    with pytest.raises(ClickErrorException) as error:
        resolve_plantuml_options((assignment,), dedicated_detail_level=None)

    message = str(error.value)
    assert assignment.split('=', 1)[0] in message
    assert 'banana' in message
    assert expected_choices in message


def test_resolve_plantuml_options_rejects_empty_tuple_value():
    with pytest.raises(ClickErrorException, match='at least one element'):
        resolve_plantuml_options(('state_name_format=',), dedicated_detail_level=None)


def test_resolve_plantuml_options_keeps_free_string_value():
    options, warnings = resolve_plantuml_options(
        ('collapsed_state_marker=***',), dedicated_detail_level=None
    )

    assert options.collapsed_state_marker == '***'
    assert warnings == ()


def test_resolve_plantuml_options_rejects_unknown_key_with_supported_keys():
    with pytest.raises(ClickErrorException) as error:
        resolve_plantuml_options(('show_event=true',), dedicated_detail_level=None)

    message = str(error.value)
    assert 'show_event' in message
    assert 'show_events' in message
    assert 'Supported --config options' in message
    assert 'custom_colors' in message


def test_resolve_plantuml_options_rejects_python_only_mapping():
    with pytest.raises(ClickErrorException) as error:
        resolve_plantuml_options(
            ('custom_colors=System.Start:#FF0000',), dedicated_detail_level=None
        )

    message = str(error.value)
    assert 'custom_colors' in message
    assert 'Python API' in message
    assert 'mapping' in message


def test_build_plantuml_output_accepts_config_detail_level(input_code_file):
    output = build_plantuml_output(
        input_code_file,
        config_options=('detail_level=full',),
    )

    assert output.startswith('@startuml')
    assert output.endswith('@enduml')


def test_build_plantuml_output_distinguishes_implicit_and_explicit_normal(
    input_code_file, capsys
):
    build_plantuml_output(
        input_code_file,
        config_options=('detail_level=full',),
    )
    assert 'Warning:' not in capsys.readouterr().err

    build_plantuml_output(
        input_code_file,
        detail_level='normal',
        config_options=('detail_level=full',),
    )
    warning = capsys.readouterr().err
    assert 'conflicting explicit values' in warning
    assert '--level' in warning


def test_plantuml_cli_reports_conflict_on_stderr_only(input_code_file):
    result = simulate_entry(
        pyfcstmcli,
        [
            'pyfcstm',
            'plantuml',
            '-i',
            input_code_file,
            '-l',
            'minimal',
            '-c',
            'detail_level=full',
        ],
    )

    assert result.exitcode == 0
    assert result.stdout.startswith('@startuml')
    assert 'Warning:' not in result.stdout
    assert 'conflicting' in _stderr(result)


def test_plantuml_cli_reports_unknown_key_without_traceback(input_code_file):
    result = simulate_entry(
        pyfcstmcli,
        [
            'pyfcstm',
            'plantuml',
            '-i',
            input_code_file,
            '-c',
            'show_event=true',
        ],
    )

    assert result.exitcode != 0
    error_output = _stderr(result) or result.stdout
    assert 'unknown plantuml' in error_output.lower()
    assert 'show_events' in error_output
    assert 'Traceback' not in error_output


def test_visualize_check_validates_config_before_backend_check(monkeypatch):
    called = []
    monkeypatch.setattr(
        visualize_module,
        'run_plantumlcli_builtin_check',
        lambda **kwargs: called.append(kwargs),
    )

    result = simulate_entry(
        pyfcstmcli,
        [
            'pyfcstm',
            'visualize',
            '--check',
            '-c',
            'unknown_option=true',
        ],
    )

    assert result.exitcode != 0
    assert called == []
    assert 'unknown plantuml' in (_stderr(result) or result.stdout).lower()


def test_visualize_invalid_config_does_not_create_cache(monkeypatch, tmp_path, input_code_file):
    cache_home = tmp_path / 'cache-home'
    output_file = tmp_path / 'existing.png'
    output_file.write_text('sentinel', encoding='utf-8')
    monkeypatch.setenv('XDG_CACHE_HOME', str(cache_home))
    monkeypatch.setattr(
        visualize_module,
        'render_plantuml_diagram',
        lambda *args, **kwargs: pytest.fail('renderer must not run for invalid config'),
    )
    monkeypatch.setattr(
        visualize_module,
        '_render_plantuml_source',
        lambda *args, **kwargs: pytest.fail('DSL rendering must not run for invalid config'),
    )

    result = simulate_entry(
        pyfcstmcli,
        [
            'pyfcstm',
            'visualize',
            '-i',
            input_code_file,
            '-o',
            str(output_file),
            '--no-open',
            '-c',
            'unknown_option=true',
        ],
    )

    assert result.exitcode != 0
    assert not (cache_home / 'pyfcstm').exists()
    assert output_file.read_text(encoding='utf-8') == 'sentinel'


@pytest.mark.parametrize('command', ['plantuml', 'visualize'])
def test_subcommand_help_links_to_configuration_reference(command):
    result = simulate_entry(pyfcstmcli, ['pyfcstm', command, '--help'])

    assert result.exitcode == 0
    help_text = result.stdout
    assert (
        'https://pyfcstm.readthedocs.io/en/latest/reference/visualization_options/'
        in help_text
    )
    assert 'Configuration reference:' in help_text

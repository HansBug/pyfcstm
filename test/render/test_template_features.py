"""Template ``features`` declaration: validation, refusal and acceptance of region models."""

import pytest
import yaml

from pyfcstm.model import load_state_machine_from_text
from pyfcstm.render import StateMachineCodeRenderer
from pyfcstm.utils import ModelValidationError

pytestmark = pytest.mark.unittest

REGION_SOURCE = 'state Root { region Worker { state Idle; [*] -> Idle; } }'
PLAIN_SOURCE = 'state Root { [*] -> Idle; state Idle; }'


def _make_template(tmp_path, config_text):
    """Write a one-file template directory and return its path."""
    templates = tmp_path / 'templates'
    templates.mkdir()
    (templates / 'config.yaml').write_text(config_text, encoding='utf-8')
    (templates / 'machine.txt.j2').write_text(
        '{{ model.root_state.name }}', encoding='utf-8'
    )
    return templates


def test_features_default_to_empty(tmp_path):
    renderer = StateMachineCodeRenderer(str(_make_template(tmp_path, '{}')))
    assert renderer.features == frozenset()


def test_features_lists_the_declared_members(tmp_path):
    templates = _make_template(tmp_path, 'features: [region]\n')
    renderer = StateMachineCodeRenderer(str(templates))
    assert renderer.features == frozenset({'region'})


@pytest.mark.parametrize(
    'config_text, expected',
    [
        ('features: region\n', "'features' must be a list"),
        ('features: {region: true}\n', "'features' must be a list"),
        ('features: [1]\n', 'features[0] must be a string'),
        ('features: [region, 3]\n', 'features[1] must be a string'),
        ('features: [parallel]\n', "unknown feature 'parallel'"),
        ('features: [region, region]\n', "duplicate feature 'region'"),
    ],
)
def test_invalid_features_fail_at_construction(tmp_path, config_text, expected):
    templates = _make_template(tmp_path, config_text)
    with pytest.raises(ValueError) as caught:
        StateMachineCodeRenderer(str(templates))
    assert expected in str(caught.value)
    assert str(templates / 'config.yaml') in str(caught.value)


def test_unknown_feature_message_lists_the_supported_ones(tmp_path):
    templates = _make_template(tmp_path, 'features: [parallel]\n')
    with pytest.raises(ValueError) as caught:
        StateMachineCodeRenderer(str(templates))
    assert 'Supported features: region.' in str(caught.value)


@pytest.mark.parametrize('single_file', [False, True])
def test_undeclared_template_refuses_a_region_model_and_names_itself(
    tmp_path, single_file
):
    model = load_state_machine_from_text(REGION_SOURCE)
    templates = _make_template(tmp_path, '{}')
    output = tmp_path / 'output'
    output.mkdir()
    preserved = output / 'machine.txt'
    preserved.write_text('existing output', encoding='utf-8')
    renderer = StateMachineCodeRenderer(str(templates))
    with pytest.raises(ModelValidationError) as caught:
        if single_file:
            renderer.render_one_file(
                model, str(preserved), str(templates / 'machine.txt.j2')
            )
        else:
            renderer.render(model, str(output), clear_previous_directory=True)
    (diagnostic,) = caught.value.diagnostics
    assert diagnostic.code == 'E_UNSUPPORTED_FEATURE'
    assert diagnostic.refs['feature'] == 'region'
    assert diagnostic.message == (
        "generate with template directory '%s' does not support region models yet."
        % templates
    )
    assert preserved.read_text(encoding='utf-8') == 'existing output'
    assert [item.name for item in output.iterdir()] == ['machine.txt']


@pytest.mark.parametrize('single_file', [False, True])
def test_declared_template_renders_a_region_model(tmp_path, single_file):
    model = load_state_machine_from_text(REGION_SOURCE)
    templates = _make_template(tmp_path, 'features: [region]\n')
    output = tmp_path / 'output'
    renderer = StateMachineCodeRenderer(str(templates))
    if single_file:
        renderer.render_one_file(
            model, str(output / 'machine.txt'), str(templates / 'machine.txt.j2')
        )
    else:
        renderer.render(model, str(output))
    assert (output / 'machine.txt').read_text(encoding='utf-8') == 'Root'


@pytest.mark.parametrize('declared', [False, True])
def test_a_model_without_regions_renders_whatever_the_declaration(tmp_path, declared):
    model = load_state_machine_from_text(PLAIN_SOURCE)
    templates = _make_template(tmp_path, 'features: [region]\n' if declared else '{}')
    output = tmp_path / 'output'
    StateMachineCodeRenderer(str(templates)).render(model, str(output))
    assert (output / 'machine.txt').read_text(encoding='utf-8') == 'Root'


def test_features_do_not_reach_the_template_environment(tmp_path):
    templates = _make_template(tmp_path, 'features: [region]\n')
    renderer = StateMachineCodeRenderer(str(templates))
    assert 'features' not in renderer.env.globals
    assert yaml.safe_load((templates / 'config.yaml').read_text()) == {
        'features': ['region']
    }

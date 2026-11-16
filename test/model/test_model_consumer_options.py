"""Ordinary model exports retain independent visibility controls."""

import pytest

from pyfcstm.model import PlantUMLOptions, load_state_machine_from_text

pytestmark = pytest.mark.unittest

SOURCE = '''def int value = 0;
state Root {
    enter abstract EnterAction;
    during before abstract DuringAction;
    exit abstract ExitAction;
    >> during before abstract AspectAction;
    state Leaf { exit { value = 1; } }
    [*] -> Leaf effect { value = 2; }
}'''


@pytest.mark.parametrize('option,hidden', [
    ('show_enter_actions', 'EnterAction'),
    ('show_during_actions', 'DuringAction'),
    ('show_exit_actions', 'ExitAction'),
    ('show_aspect_actions', 'AspectAction'),
])
def test_ordinary_plantuml_can_hide_each_action_kind(option, hidden):
    model = load_state_machine_from_text(SOURCE)
    options = dict(detail_level='full', show_lifecycle_actions=True,
                   show_abstract_actions=True, show_concrete_actions=True)
    assert hidden in model.to_plantuml(options=PlantUMLOptions(**options))
    options[option] = False
    assert hidden not in model.to_plantuml(options=PlantUMLOptions(**options))


def test_ordinary_plantuml_filters_all_actions_without_empty_labels():
    model = load_state_machine_from_text(SOURCE)
    output = model.to_plantuml(options=PlantUMLOptions(
        detail_level='full', show_lifecycle_actions=True,
        show_abstract_actions=False, show_concrete_actions=False,
    ))
    for name in ['EnterAction', 'DuringAction', 'ExitAction', 'AspectAction']:
        assert name not in output
    assert 'value = 1' not in output
    assert 'state "Root"' in output


def test_ordinary_plantuml_hide_modes_override_enabled_sections():
    model = load_state_machine_from_text(SOURCE)
    output = model.to_plantuml(options=PlantUMLOptions(
        detail_level='full', show_variable_definitions=True,
        variable_display_mode='hide', show_transition_effects=True,
        transition_effect_mode='hide', show_lifecycle_actions=False,
    ))
    assert 'legend' not in output
    assert 'value = 2' not in output


def test_state_plantuml_accepts_a_partial_event_color_map():
    model = load_state_machine_from_text('''state Root {
        state A; state B; [*] -> A;
        A -> B : First;
        B -> A : Second;
    }''')
    output = model.root_state.to_plantuml(
        options=PlantUMLOptions(event_visualization_mode='color'),
        event_colors={'Root.First': '#123456'},
    )
    assert output.count('-[#123456]->') == 1
    assert output.count('-->') == 2

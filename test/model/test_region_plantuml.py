"""PlantUML export of ordered region models."""

import pathlib
import re

import pytest
from hbutils.testing import simulate_entry

from pyfcstm.entry import pyfcstmcli
from pyfcstm.model import PlantUMLOptions, collect_event_transitions, load_state_machine_from_file, \
    load_state_machine_from_text

pytestmark = pytest.mark.unittest

FIXTURES = pathlib.Path(__file__).parent.parent / 'testfile' / 'region_plantuml'
EXAMPLES = ['controller', 'job', 'nested']
LEVELS = ['minimal', 'normal', 'full']


def _golden(example, level):
    return (FIXTURES / ('%s.%s.puml' % (example, level))).read_text(encoding='utf-8')


@pytest.mark.parametrize('level', LEVELS)
@pytest.mark.parametrize('example', EXAMPLES)
def test_export_matches_golden(example, level):
    model = load_state_machine_from_file(str(FIXTURES / ('%s.fcstm' % example)))
    assert model.to_plantuml(level) == _golden(example, level)


@pytest.mark.parametrize('level', LEVELS)
@pytest.mark.parametrize('example', EXAMPLES)
def test_cli_prints_the_same_text(example, level):
    result = simulate_entry(pyfcstmcli, [
        'pyfcstm', 'plantuml', '-i', str(FIXTURES / ('%s.fcstm' % example)), '--level', level])
    assert result.exitcode == 0
    assert result.stdout == _golden(example, level) + '\n'


def test_regions_keep_declaration_order_with_separator_between_them():
    text = load_state_machine_from_file(str(FIXTURES / 'controller.fcstm')).to_plantuml('full')
    assert text.index('"region 1: Safety"') < text.index('"region 2: Motion"')
    assert len(re.findall(r'^\s*--$', text, re.M)) == 1
    nested = load_state_machine_from_file(str(FIXTURES / 'nested.fcstm')).to_plantuml('full')
    assert len(re.findall(r'^\s*--$', nested, re.M)) == 3
    for name in ('A', 'B', 'C', 'A1', 'A2'):
        assert '"region ' in nested and (': %s"' % name) in nested


def test_active_queries_are_shown_as_written_without_generated_flags():
    model = load_state_machine_from_file(str(FIXTURES / 'controller.fcstm'))
    for level in LEVELS:
        text = model.to_plantuml(level)
        assert '__active_' not in text
    full = model.to_plantuml('full')
    assert 'active("Controller.Running.Safety.Tripped")' in full
    # Once as a link label and once inside a state description; neither keeps a
    # JSON escape, because PlantUML would draw the backslash.
    assert full.count('active("Controller.Running.Safety.Tripped")') == 2
    assert '\\"' not in full
    assert 'Tripped :' not in full  # generated flag writes do not describe the state


def test_active_only_model_exports_without_hidden_variable():
    model = load_state_machine_from_text(
        'def int x = 0; state Root { state A; state B; [*] -> A;'
        ' A -> B : if [active("Root.B") || x > 1]; }')
    text = model.to_plantuml('full')
    assert 'active("Root.B")' in text
    assert '__active_' not in text
    assert '| x | int | 0 |' in text


def test_hidden_variable_alone_leaves_no_variable_table():
    model = load_state_machine_from_text(
        'state Root { state A; state B; [*] -> A; A -> B : if [active("Root.B")]; }')
    text = model.to_plantuml('full')
    assert 'legend' not in text and 'note as DefinitionNote' not in text


def test_user_variable_with_generated_looking_prefix_is_kept():
    model = load_state_machine_from_text(
        'def int __active_mine = 0; state Root { state A; state B; [*] -> A;'
        ' A -> B : if [active("Root.B") && __active_mine != 0]; }')
    text = model.to_plantuml('full')
    assert '__active_mine' in text.replace('~', '')
    assert 'active("Root.B")' in text


@pytest.mark.parametrize('depth,expected_marker', [(1, 1), (2, 2), (3, 0)])
def test_max_depth_counts_a_region_as_one_level(depth, expected_marker):
    model = load_state_machine_from_file(str(FIXTURES / 'controller.fcstm'))
    text = model.to_plantuml(PlantUMLOptions(max_depth=depth, collapsed_state_marker='...'))
    assert text.count('"..."') == expected_marker
    assert ('"region 1: Safety"' in text) == (depth >= 2)
    # A collapsed region must not draw links to child states it did not declare.
    assert ('controller__running__safety__normal' in text) == (depth >= 3)


def test_region_aspects_follow_aspect_options():
    model = load_state_machine_from_file(str(FIXTURES / 'controller.fcstm'))
    assert '>> during before' in model.to_plantuml('full')
    assert '>> during before' not in model.to_plantuml(
        PlantUMLOptions(detail_level='full', show_aspect_actions=False))
    assert '>> during before' not in model.to_plantuml('normal')


def test_event_colours_cover_region_events():
    model = load_state_machine_from_text('''state Root {
        event Go;
        state P {
            region A { state X; state Y; [*] -> X; X -> Y : /Go; Y -> X : /Go; }
            region B { state U; [*] -> U; U -> [*] : /Go; }
        }
        [*] -> P;
    }''')
    events = collect_event_transitions(model)
    assert len(events['Root.Go']) == 3
    assert {type(owner).__name__ for owner, _ in events['Root.Go']} == {'Region'}
    text = model.to_plantuml(PlantUMLOptions(event_visualization_mode='color'))
    assert text.count('-[#4E79A7]->') == 3


def test_collapse_empty_states_ignores_generated_flag_writes():
    model = load_state_machine_from_text(
        'state Root { state A; state B { enter abstract Init; } [*] -> A;'
        ' A -> B : if [active("Root.A")]; }')
    text = model.to_plantuml(PlantUMLOptions(detail_level='full', collapse_empty_states=True))
    assert 'root__a :' not in text
    assert 'root__b :' in text


def test_state_export_of_a_parallel_owner_is_self_contained():
    model = load_state_machine_from_file(str(FIXTURES / 'job.fcstm'))
    text = model.root_state.substates['Job'].to_plantuml('minimal')
    assert text.startswith('state "Job" as workflow__job <<composite>>')
    assert '"region 1: A"' in text and '"region 2: B"' in text


REGION_WITH_EFFECT = '''def int x = 0;
state Root {
    region A {
        state P { enter abstract Boot; during { x = 1; } }
        state Q;
        [*] -> P;
        P -> Q : if [active("Root.A.Q") || x > 0] effect { x = 2; }
    }
}'''


@pytest.mark.parametrize('mode,expected', [
    ('note', 'note on link'), ('inline', ' / x = 2;'), ('hide', None),
])
def test_region_transition_effects_follow_effect_mode(mode, expected):
    model = load_state_machine_from_text(REGION_WITH_EFFECT)
    text = model.to_plantuml(PlantUMLOptions(detail_level='full', transition_effect_mode=mode))
    if expected is None:
        assert 'x = 2' not in text.split('state "Root"')[1].split('root__a : ')[0]
    else:
        assert expected in text
    assert 'active("Root.A.Q")' in text


def test_region_without_visible_actions_has_no_description_line():
    model = load_state_machine_from_text(REGION_WITH_EFFECT)
    text = model.to_plantuml(PlantUMLOptions(
        detail_level='full', show_concrete_actions=False, show_abstract_actions=False))
    assert 'root__a__p :' not in text


def test_variable_table_can_be_hidden_for_a_region_model():
    model = load_state_machine_from_text(REGION_WITH_EFFECT)
    text = model.to_plantuml(PlantUMLOptions(variable_display_mode='hide'))
    assert 'legend' not in text and 'DefinitionNote' not in text


def test_region_export_works_without_stereotypes_and_standalone():
    model = load_state_machine_from_text(REGION_WITH_EFFECT)
    region = model.root_state.regions['A']
    assert '<<region>>' in region.to_plantuml('minimal')
    plain = region.to_plantuml(PlantUMLOptions(use_stereotypes=False))
    assert plain.startswith('state "region 1: A" as root__a #line.dashed {')

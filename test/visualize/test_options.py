"""
Tests for :class:`pyfcstm.visualize.options.VisualizeOptions`.
"""
import pytest

from pyfcstm.visualize import VisualizeOptions


@pytest.mark.unittest
class TestVisualizeOptions:
    def test_default_serialises_to_empty(self):
        # All fields default to None → nothing should be passed across to
        # the JS side, so jsfcstm picks its own defaults.
        assert VisualizeOptions().to_jsfcstm_dict() == {}

    def test_all_fields_camelcase(self):
        opts = VisualizeOptions(
            detail_level='full',
            direction='RIGHT',
            show_variable_definitions=True,
            show_events=False,
            event_name_format=['name', 'relpath'],
            show_transition_guards=True,
            show_transition_effects=False,
            transition_effect_mode='note',
            event_visualization_mode='color',
            show_state_events=True,
            show_state_actions=False,
            max_state_events=2,
            max_state_actions=3,
            max_transition_effect_lines=4,
            max_label_length=120,
        )
        out = opts.to_jsfcstm_dict()
        assert out == {
            'detailLevel': 'full',
            'direction': 'RIGHT',
            'showVariableDefinitions': True,
            'showEvents': False,
            'eventNameFormat': ['name', 'relpath'],
            'showTransitionGuards': True,
            'showTransitionEffects': False,
            'transitionEffectMode': 'note',
            'eventVisualizationMode': 'color',
            'showStateEvents': True,
            'showStateActions': False,
            'maxStateEvents': 2,
            'maxStateActions': 3,
            'maxTransitionEffectLines': 4,
            'maxLabelLength': 120,
        }

    def test_partial_only_emits_set_fields(self):
        opts = VisualizeOptions(direction='DOWN')
        assert opts.to_jsfcstm_dict() == {'direction': 'DOWN'}

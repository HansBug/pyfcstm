"""
Unit tests for PlantUML configuration and utility functions.

This module tests the plantuml.py module components:
- PlantUMLOptions configuration class and resolution logic
- format_state_name() and format_event_name() utility functions
- collect_event_transitions() and assign_event_colors() helper functions
"""

import pytest

from pyfcstm.model.model import Event, State, StateMachine, Transition
from pyfcstm.model.plantuml import (
    PlantUMLOptions,
    format_state_name,
    format_event_name,
    collect_event_transitions,
    assign_event_colors,
)


@pytest.mark.unittest
class TestPlantUMLOptionsInit:
    """Test cases for PlantUMLOptions initialization."""

    def test_default_initialization(self):
        """Test default initialization with no arguments."""
        options = PlantUMLOptions()
        assert options.detail_level == 'normal'
        assert options.show_variable_definitions is None
        assert options.variable_display_mode == 'note'
        assert options.state_name_format == ('extra_name',)
        assert options.event_name_format == ('extra_name', 'relpath')
        assert options.show_lifecycle_actions is None
        assert options.show_transition_guards is None
        assert options.collapsed_state_marker == '...'
        assert options.use_skinparam is True
        assert options.use_stereotypes is True

    def test_custom_initialization(self):
        """Test initialization with custom values."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_variable_definitions=False,
            state_name_format=('name',),
            show_lifecycle_actions=True,
        )
        assert options.detail_level == 'minimal'
        assert options.show_variable_definitions is False
        assert options.state_name_format == ('name',)
        assert options.show_lifecycle_actions is True

    def test_invalid_state_name_format_raises_error(self):
        """Test that empty state_name_format raises ValueError."""
        with pytest.raises(ValueError, match="state_name_format must contain at least one element"):
            PlantUMLOptions(state_name_format=())

    def test_invalid_event_name_format_raises_error(self):
        """Test that empty event_name_format raises ValueError."""
        with pytest.raises(ValueError, match="event_name_format must contain at least one element"):
            PlantUMLOptions(event_name_format=())


@pytest.mark.unittest
class TestPlantUMLOptionsFromValue:
    """Test cases for PlantUMLOptions.from_value() normalization."""

    def test_from_value_with_options_instance(self):
        """Test from_value with existing PlantUMLOptions instance."""
        original = PlantUMLOptions(detail_level='minimal')
        result = PlantUMLOptions.from_value(original)
        assert result is original

    def test_from_value_with_none(self):
        """Test from_value with None creates default options."""
        result = PlantUMLOptions.from_value(None)
        assert isinstance(result, PlantUMLOptions)
        assert result.detail_level == 'normal'

    def test_from_value_with_detail_level_string(self):
        """Test from_value with detail level string."""
        result = PlantUMLOptions.from_value('minimal')
        assert isinstance(result, PlantUMLOptions)
        assert result.detail_level == 'minimal'

    def test_from_value_with_invalid_string_raises_error(self):
        """Test from_value with invalid string raises TypeError."""
        with pytest.raises(TypeError, match="Invalid detail level value"):
            PlantUMLOptions.from_value('invalid')

    def test_from_value_with_invalid_type_raises_error(self):
        """Test from_value with invalid type raises TypeError."""
        with pytest.raises(TypeError, match="Invalid plantuml options type"):
            PlantUMLOptions.from_value(123)


@pytest.mark.unittest
class TestPlantUMLOptionsToConfig:
    """Test cases for PlantUMLOptions.to_config() resolution."""

    def test_to_config_minimal_detail_level(self):
        """Test to_config with minimal detail level."""
        options = PlantUMLOptions(detail_level='minimal')
        config = options.to_config()

        assert config.show_variable_definitions is False
        assert config.show_lifecycle_actions is False
        assert config.show_transition_guards is True
        assert config.show_transition_effects is True
        assert config.show_events is True
        assert config.show_pseudo_state_style is False

    def test_to_config_normal_detail_level(self):
        """Test to_config with normal detail level."""
        options = PlantUMLOptions(detail_level='normal')
        config = options.to_config()

        assert config.show_variable_definitions is False
        assert config.show_lifecycle_actions is False
        assert config.show_transition_guards is True
        assert config.show_transition_effects is True
        assert config.show_events is True
        assert config.show_pseudo_state_style is True

    def test_to_config_full_detail_level(self):
        """Test to_config with full detail level."""
        options = PlantUMLOptions(detail_level='full')
        config = options.to_config()

        assert config.show_variable_definitions is True
        assert config.show_lifecycle_actions is True
        assert config.show_transition_guards is True
        assert config.show_transition_effects is True
        assert config.show_events is True
        assert config.show_pseudo_state_style is True

    def test_to_config_inheritance_from_show_lifecycle_actions(self):
        """Test that lifecycle sub-fields inherit from show_lifecycle_actions."""
        options = PlantUMLOptions(show_lifecycle_actions=True)
        config = options.to_config()

        assert config.show_lifecycle_actions is True
        assert config.show_enter_actions is True
        assert config.show_during_actions is True
        assert config.show_exit_actions is True
        assert config.show_aspect_actions is True
        assert config.show_abstract_actions is True
        assert config.show_concrete_actions is True

    def test_to_config_explicit_overrides_inheritance(self):
        """Test that explicit values override inheritance."""
        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            show_enter_actions=False,
            show_during_actions=False,
        )
        config = options.to_config()

        assert config.show_lifecycle_actions is True
        assert config.show_enter_actions is False
        assert config.show_during_actions is False
        assert config.show_exit_actions is True  # Inherited
        assert config.show_aspect_actions is True  # Inherited

    def test_to_config_preserves_non_optional_fields(self):
        """Test that non-optional fields are preserved."""
        options = PlantUMLOptions(
            detail_level='minimal',
            variable_display_mode='legend',
            state_name_format=('name', 'path'),
            collapsed_state_marker='[...]',
            use_skinparam=False,
            use_stereotypes=False,
        )
        config = options.to_config()

        assert config.detail_level == 'minimal'
        assert config.variable_display_mode == 'legend'
        assert config.state_name_format == ('name', 'path')
        assert config.collapsed_state_marker == '[...]'
        assert config.use_skinparam is False
        assert config.use_stereotypes is False


@pytest.mark.unittest
class TestFormatStateName:
    """Test cases for format_state_name() function."""

    def test_format_name_only(self):
        """Test formatting with name only."""
        state = State(name='Running', extra_name='运行中', path=('System', 'Running'), substates={})
        assert format_state_name(state, ('name',)) == 'Running'

    def test_format_extra_name_only(self):
        """Test formatting with extra_name only."""
        state = State(name='Running', extra_name='运行中', path=('System', 'Running'), substates={})
        assert format_state_name(state, ('extra_name',)) == '运行中'

    def test_format_path_only(self):
        """Test formatting with path only."""
        state = State(name='Running', extra_name='运行中', path=('System', 'ModuleA', 'Running'), substates={})
        assert format_state_name(state, ('path',)) == 'System.ModuleA.Running'

    def test_format_extra_name_and_name(self):
        """Test formatting with extra_name and name."""
        state = State(name='Running', extra_name='运行中', path=('System', 'Running'), substates={})
        assert format_state_name(state, ('extra_name', 'name')) == '运行中 (Running)'

    def test_format_multi_part_joining(self):
        """Test multi-part joining format."""
        state = State(name='Running', extra_name='运行中', path=('System', 'Running'), substates={})
        assert format_state_name(state, ('extra_name', 'name', 'path')) == '运行中 (Running / System.Running)'

    def test_format_fallback_when_extra_name_missing(self):
        """Test fallback to name when extra_name is missing."""
        state = State(name='Running', extra_name=None, path=('System', 'Running'), substates={})
        assert format_state_name(state, ('extra_name',)) == 'Running'

    def test_format_empty_tuple_fallback(self):
        """Test fallback to name when format tuple is empty."""
        state = State(name='Running', extra_name=None, path=('System', 'Running'), substates={})
        # Empty tuple should fallback to name
        assert format_state_name(state, ()) == 'Running'


@pytest.mark.unittest
class TestFormatEventName:
    """Test cases for format_event_name() function."""

    def test_format_name_only(self):
        """Test formatting with name only."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ('name',)) == 'Boot'

    def test_format_extra_name_only(self):
        """Test formatting with extra_name only."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ('extra_name',)) == '启动'

    def test_format_path_single_element(self):
        """Test path formatting with single element."""
        event = Event(name='Boot', state_path=(), extra_name='启动')
        assert format_event_name(event, ('path',)) == '/Boot'

    def test_format_path_multiple_elements(self):
        """Test path formatting with multiple elements."""
        event = Event(name='Boot', state_path=('System', 'ModuleA'), extra_name='启动')
        assert format_event_name(event, ('path',)) == '/ModuleA.Boot'

    def test_format_extra_name_and_name(self):
        """Test formatting with extra_name and name."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ('extra_name', 'name')) == '启动 (Boot)'

    def test_format_multi_part_joining(self):
        """Test multi-part joining format."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ('extra_name', 'name', 'path')) == '启动 (Boot / /Boot)'

    def test_format_relpath_without_trans_node(self):
        """Test relpath formatting without trans_node."""
        event = Event(name='TestEvent', state_path=('Root', 'State'), extra_name=None)
        result = format_event_name(event, ('relpath',), trans_node=None)
        assert result == '/State.TestEvent'

    def test_format_relpath_single_element_fallback(self):
        """Test relpath formatting with single element fallback."""
        event = Event(name='TestEvent', state_path=(), extra_name=None)
        result = format_event_name(event, ('relpath',), trans_node=None)
        assert result == '/TestEvent'

    def test_format_empty_tuple_fallback(self):
        """Test fallback to name when format tuple is empty."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ()) == 'Boot'

    def test_format_fallback_when_extra_name_missing(self):
        """Test fallback when extra_name is missing."""
        event = Event(name='Boot', state_path=('System',), extra_name=None)
        assert format_event_name(event, ('extra_name',)) == 'Boot'


@pytest.mark.unittest
class TestCollectEventTransitions:
    """Test cases for collect_event_transitions() function."""

    def test_collect_from_single_state(self):
        """Test collecting events from a single state."""
        event = Event(name='TestEvent', state_path=('Root',), extra_name=None)
        child1 = State(name='Child1', extra_name=None, path=('Root', 'Child1'), substates={})
        child2 = State(name='Child2', extra_name=None, path=('Root', 'Child2'), substates={})
        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={'Child1': child1, 'Child2': child2},
            transitions=[
                Transition(from_state='Child1', to_state='Child2', event=event, guard=None, effects=[])
            ],
        )
        sm = StateMachine(defines={}, root_state=root)

        event_map = collect_event_transitions(sm)

        assert 'Root.TestEvent' in event_map
        assert len(event_map['Root.TestEvent']) == 1

    def test_collect_from_multiple_states(self):
        """Test collecting events from multiple states with same event."""
        event1 = Event(name='Event1', state_path=('Root',), extra_name=None)
        event2 = Event(name='Event2', state_path=('Root',), extra_name=None)

        child1 = State(name='Child1', extra_name=None, path=('Root', 'Child1'), substates={})
        child2 = State(name='Child2', extra_name=None, path=('Root', 'Child2'), substates={})
        child3 = State(name='Child3', extra_name=None, path=('Root', 'Child3'), substates={})

        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={'Child1': child1, 'Child2': child2, 'Child3': child3},
            transitions=[
                Transition(from_state='Child1', to_state='Child2', event=event1, guard=None, effects=[]),
                Transition(from_state='Child2', to_state='Child3', event=event1, guard=None, effects=[]),
                Transition(from_state='Child3', to_state='Child1', event=event2, guard=None, effects=[]),
            ],
        )

        sm = StateMachine(defines={}, root_state=root)
        event_map = collect_event_transitions(sm)

        assert len(event_map) == 2
        assert len(event_map['Root.Event1']) == 2
        assert len(event_map['Root.Event2']) == 1

    def test_collect_from_nested_states(self):
        """Test collecting events from nested states."""
        event = Event(name='TestEvent', state_path=('Root', 'Parent'), extra_name=None)

        grandchild1 = State(
            name='GrandChild1',
            extra_name=None,
            path=('Root', 'Parent', 'Child', 'GrandChild1'),
            substates={},
        )
        grandchild2 = State(
            name='GrandChild2',
            extra_name=None,
            path=('Root', 'Parent', 'Child', 'GrandChild2'),
            substates={},
        )
        child = State(
            name='Child',
            extra_name=None,
            path=('Root', 'Parent', 'Child'),
            substates={'GrandChild1': grandchild1, 'GrandChild2': grandchild2},
            transitions=[
                Transition(from_state='GrandChild1', to_state='GrandChild2', event=event, guard=None, effects=[])
            ],
        )
        parent = State(
            name='Parent',
            extra_name=None,
            path=('Root', 'Parent'),
            substates={'Child': child},
        )
        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={'Parent': parent},
        )

        sm = StateMachine(defines={}, root_state=root)
        event_map = collect_event_transitions(sm)

        assert 'Root.Parent.TestEvent' in event_map
        assert len(event_map['Root.Parent.TestEvent']) == 1

    def test_collect_empty_when_no_events(self):
        """Test that collection returns empty dict when no events."""
        root = State(name='Root', extra_name=None, path=('Root',), substates={})
        sm = StateMachine(defines={}, root_state=root)

        event_map = collect_event_transitions(sm)

        assert event_map == {}


@pytest.mark.unittest
class TestAssignEventColors:
    """Test cases for assign_event_colors() function."""

    def test_assign_default_colors(self):
        """Test assigning default colors to events that appear >= 2 times."""
        event_map = {
            'Root.Event1': [1, 2],  # Appears 2 times
            'Root.Event2': [1, 2],  # Appears 2 times
            'Root.Event3': [1, 2],  # Appears 2 times
        }

        colors = assign_event_colors(event_map)

        assert len(colors) == 3
        assert colors['Root.Event1'] == '#4E79A7'  # First color in palette
        assert colors['Root.Event2'] == '#F28E2B'  # Second color
        assert colors['Root.Event3'] == '#E15759'  # Third color

    def test_assign_colors_only_for_multiple_occurrences(self):
        """Test that colors are only assigned to events appearing >= 2 times."""
        event_map = {
            'Root.Event1': [1],        # Appears 1 time - no color
            'Root.Event2': [1, 2],     # Appears 2 times - gets color
            'Root.Event3': [1, 2, 3],  # Appears 3 times - gets color
        }

        colors = assign_event_colors(event_map)

        assert len(colors) == 2
        assert 'Root.Event1' not in colors  # Only appears once
        assert colors['Root.Event2'] == '#4E79A7'  # First color
        assert colors['Root.Event3'] == '#F28E2B'  # Second color

    def test_assign_custom_colors(self):
        """Test assigning custom colors overrides defaults for events appearing >= 2 times."""
        event_map = {
            'Root.Event1': [1, 2],  # Appears 2 times
            'Root.Event2': [1, 2],  # Appears 2 times
        }
        custom_colors = {
            'Root.Event1': '#FF0000',
        }

        colors = assign_event_colors(event_map, custom_colors)

        assert colors['Root.Event1'] == '#FF0000'  # Custom color
        assert colors['Root.Event2'] == '#4E79A7'  # Default color

    def test_assign_colors_cycling_palette(self):
        """Test that color palette cycles for many events that appear >= 2 times."""
        event_map = {f'Root.Event{i}': [1, 2] for i in range(15)}  # Each event appears 2 times

        colors = assign_event_colors(event_map)

        assert len(colors) == 15
        # First and 11th event should use same color (palette has 10 colors)
        event_keys = sorted(event_map.keys())
        assert colors[event_keys[0]] == colors[event_keys[10]]

    def test_assign_colors_sorted_order(self):
        """Test that colors are assigned in sorted order of event paths for events appearing >= 2 times."""
        event_map = {
            'Root.EventZ': [1, 2],  # Appears 2 times
            'Root.EventA': [1, 2],  # Appears 2 times
            'Root.EventM': [1, 2],  # Appears 2 times
        }

        colors = assign_event_colors(event_map)

        # EventA should get first color (sorted first)
        assert colors['Root.EventA'] == '#4E79A7'
        # EventM should get second color
        assert colors['Root.EventM'] == '#F28E2B'
        # EventZ should get third color
        assert colors['Root.EventZ'] == '#E15759'

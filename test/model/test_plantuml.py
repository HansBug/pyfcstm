"""
Unit tests for PlantUML configuration options.

This module tests the :class:`PlantUMLOptions` configuration class and its
resolution logic, ensuring proper inheritance and fallback behavior.
"""

import textwrap

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import Event, State, parse_dsl_node_to_state_machine
from pyfcstm.model.plantuml import PlantUMLOptions, format_event_name, format_state_name


@pytest.mark.unittest
class TestDetailLevelStrings:
    """Test cases for detail_level string values."""

    def test_detail_level_values(self):
        """Test accepted detail_level strings."""
        assert PlantUMLOptions(detail_level='minimal').detail_level == 'minimal'
        assert PlantUMLOptions(detail_level='normal').detail_level == 'normal'
        assert PlantUMLOptions(detail_level='full').detail_level == 'full'


@pytest.mark.unittest
class TestPlantUMLNameFormatters:
    """Test cases for state/event name formatting helpers."""

    def test_format_state_name_only(self):
        """Test state name formatter with name only."""
        state = State(name='Running', extra_name='运行中', path=('System', 'Running'), substates={})
        assert format_state_name(state, ('name',)) == 'Running'

    def test_format_state_extra_name_and_name(self):
        """Test state name formatter with extra_name and name."""
        state = State(name='Running', extra_name='运行中', path=('System', 'Running'), substates={})
        assert format_state_name(state, ('extra_name', 'name')) == '运行中 (Running)'

    def test_format_state_path(self):
        """Test state name formatter with path element."""
        state = State(name='Running', extra_name='运行中', path=('System', 'ModuleA', 'Running'), substates={})
        assert format_state_name(state, ('path',)) == 'System.ModuleA.Running'

    def test_format_state_fallback_when_extra_name_missing(self):
        """Test state name formatter fallback to name when extra_name is missing."""
        state = State(name='Running', extra_name=None, path=('System', 'Running'), substates={})
        assert format_state_name(state, ('extra_name',)) == 'Running'

    def test_format_state_multi_part_joining(self):
        """Test state name formatter multi-part joining format."""
        state = State(name='Running', extra_name='运行中', path=('System', 'Running'), substates={})
        assert format_state_name(state, ('extra_name', 'name', 'path')) == '运行中 (Running / System.Running)'

    def test_format_event_name_only(self):
        """Test event name formatter with name only."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ('name',)) == 'Boot'

    def test_format_event_extra_name_and_name(self):
        """Test event name formatter with extra_name and name."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ('extra_name', 'name')) == '启动 (Boot)'

    def test_format_event_path(self):
        """Test event name formatter with full path."""
        event = Event(name='Boot', state_path=('System', 'ModuleA'), extra_name='启动')
        assert format_event_name(event, ('path',)) == 'System.ModuleA.Boot'

    def test_format_event_multi_part_joining(self):
        """Test event name formatter multi-part joining format."""
        event = Event(name='Boot', state_path=('System',), extra_name='启动')
        assert format_event_name(event, ('extra_name', 'name', 'path')) == '启动 (Boot / System.Boot)'


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
        assert options.event_name_format == ('extra_name',)
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
            variable_display_mode='legend',
            state_name_format=('name', 'extra_name'),
            show_lifecycle_actions=True,
            max_depth=3,
        )
        assert options.detail_level == 'minimal'
        assert options.show_variable_definitions is False
        assert options.variable_display_mode == 'legend'
        assert options.state_name_format == ('name', 'extra_name')
        assert options.show_lifecycle_actions is True
        assert options.max_depth == 3

    def test_empty_state_name_format_raises_error(self):
        """Test that empty state_name_format raises ValueError."""
        with pytest.raises(ValueError, match="state_name_format must contain at least one element"):
            PlantUMLOptions(state_name_format=())

    def test_empty_event_name_format_raises_error(self):
        """Test that empty event_name_format raises ValueError."""
        with pytest.raises(ValueError, match="event_name_format must contain at least one element"):
            PlantUMLOptions(event_name_format=())


@pytest.mark.unittest
class TestPlantUMLOptionsFromValue:
    """Test cases for PlantUMLOptions.from_value()."""

    def test_from_value_with_options_instance(self):
        """Test that existing options object is returned directly."""
        options = PlantUMLOptions(detail_level='full')
        assert PlantUMLOptions.from_value(options) is options

    def test_from_value_with_detail_level_string(self):
        """Test that detail level string creates options object."""
        options = PlantUMLOptions.from_value('minimal')
        assert isinstance(options, PlantUMLOptions)
        assert options.detail_level == 'minimal'

    def test_from_value_with_none(self):
        """Test that None creates default options object."""
        options = PlantUMLOptions.from_value(None)
        assert isinstance(options, PlantUMLOptions)
        assert options.detail_level == 'normal'

    def test_from_value_with_invalid_detail_level(self):
        """Test that invalid detail level string raises TypeError."""
        with pytest.raises(TypeError, match='Invalid detail level value'):
            PlantUMLOptions.from_value('unknown')

    def test_from_value_with_invalid_type(self):
        """Test that unsupported input type raises TypeError."""
        with pytest.raises(TypeError, match='Invalid plantuml options type'):
            PlantUMLOptions.from_value(123)


@pytest.mark.unittest
class TestPlantUMLOptionsToConfigMinimal:
    """Test cases for to_config() with MINIMAL detail level."""

    def test_minimal_defaults(self):
        """Test MINIMAL detail level defaults."""
        options = PlantUMLOptions(detail_level='minimal')
        config = options.to_config()

        assert config.show_variable_definitions is False
        assert config.show_lifecycle_actions is False
        assert config.show_enter_actions is False
        assert config.show_during_actions is False
        assert config.show_exit_actions is False
        assert config.show_aspect_actions is False
        assert config.show_abstract_actions is False
        assert config.show_concrete_actions is False
        assert config.show_transition_guards is True
        assert config.show_transition_effects is True
        assert config.show_events is True
        assert config.show_pseudo_state_style is False

    def test_minimal_with_overrides(self):
        """Test MINIMAL detail level with user overrides."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_lifecycle_actions=True,
            show_variable_definitions=True,
        )
        config = options.to_config()

        assert config.show_variable_definitions is True
        assert config.show_lifecycle_actions is True
        assert config.show_enter_actions is True  # Inherited from show_lifecycle_actions
        assert config.show_during_actions is True  # Inherited
        assert config.show_exit_actions is True  # Inherited


@pytest.mark.unittest
class TestPlantUMLOptionsToConfigNormal:
    """Test cases for to_config() with NORMAL detail level."""

    def test_normal_defaults(self):
        """Test NORMAL detail level defaults."""
        options = PlantUMLOptions(detail_level='normal')
        config = options.to_config()

        assert config.show_variable_definitions is False
        assert config.show_lifecycle_actions is False
        assert config.show_enter_actions is False
        assert config.show_during_actions is False
        assert config.show_exit_actions is False
        assert config.show_aspect_actions is False
        assert config.show_abstract_actions is False
        assert config.show_concrete_actions is False
        assert config.show_transition_guards is True
        assert config.show_transition_effects is True
        assert config.show_events is True
        assert config.show_pseudo_state_style is True

    def test_normal_with_overrides(self):
        """Test NORMAL detail level with user overrides."""
        options = PlantUMLOptions(
            detail_level='normal',
            show_lifecycle_actions=False,
            show_transition_guards=False,
        )
        config = options.to_config()

        assert config.show_lifecycle_actions is False
        assert config.show_enter_actions is False  # Inherited
        assert config.show_transition_guards is False  # User override
        assert config.show_transition_effects is True  # Default from detail level


@pytest.mark.unittest
class TestPlantUMLOptionsToConfigFull:
    """Test cases for to_config() with FULL detail level."""

    def test_full_defaults(self):
        """Test FULL detail level defaults."""
        options = PlantUMLOptions(detail_level='full')
        config = options.to_config()

        assert config.show_variable_definitions is True
        assert config.show_lifecycle_actions is True
        assert config.show_enter_actions is True
        assert config.show_during_actions is True
        assert config.show_exit_actions is True
        assert config.show_aspect_actions is True
        assert config.show_abstract_actions is True
        assert config.show_concrete_actions is True
        assert config.show_transition_guards is True
        assert config.show_transition_effects is True
        assert config.show_events is True
        assert config.show_pseudo_state_style is True


@pytest.mark.unittest
class TestPlantUMLOptionsInheritance:
    """Test cases for configuration inheritance logic."""

    def test_lifecycle_actions_inheritance(self):
        """Test that lifecycle sub-actions inherit from show_lifecycle_actions."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_lifecycle_actions=True,
        )
        config = options.to_config()

        assert config.show_lifecycle_actions is True
        assert config.show_enter_actions is True
        assert config.show_during_actions is True
        assert config.show_exit_actions is True
        assert config.show_aspect_actions is True

    def test_lifecycle_actions_partial_override(self):
        """Test partial override of lifecycle actions."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_lifecycle_actions=True,
            show_enter_actions=False,
        )
        config = options.to_config()

        assert config.show_lifecycle_actions is True
        assert config.show_enter_actions is False  # User override
        assert config.show_during_actions is True  # Inherited
        assert config.show_exit_actions is True  # Inherited

    def test_abstract_concrete_inheritance(self):
        """Test that abstract/concrete actions inherit from show_lifecycle_actions."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_lifecycle_actions=True,
        )
        config = options.to_config()

        assert config.show_abstract_actions is True
        assert config.show_concrete_actions is True

    def test_abstract_concrete_override(self):
        """Test override of abstract/concrete actions."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_lifecycle_actions=True,
            show_abstract_actions=False,
        )
        config = options.to_config()

        assert config.show_abstract_actions is False  # User override
        assert config.show_concrete_actions is True  # Inherited

    def test_transition_defaults(self):
        """Test transition sub-options default to detail level settings."""
        options = PlantUMLOptions(detail_level='minimal')
        config = options.to_config()

        assert config.show_transition_guards is True
        assert config.show_transition_effects is True

    def test_transition_partial_override(self):
        """Test partial override of transition options."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_transition_guards=False,
        )
        config = options.to_config()

        assert config.show_transition_guards is False  # User override
        assert config.show_transition_effects is True  # Detail-level default

    def test_no_inheritance_when_parent_false(self):
        """Test that inheritance doesn't happen when parent is False."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_lifecycle_actions=False,
        )
        config = options.to_config()

        assert config.show_lifecycle_actions is False
        assert config.show_enter_actions is False
        assert config.show_during_actions is False
        assert config.show_exit_actions is False


@pytest.mark.unittest
class TestPlantUMLOptionsComplexScenarios:
    """Test cases for complex configuration scenarios."""

    def test_all_none_values(self):
        """Test resolution when all values are None."""
        options = PlantUMLOptions(detail_level='normal')
        config = options.to_config()

        # All fields should be resolved to non-None values
        assert config.show_variable_definitions is not None
        assert config.show_lifecycle_actions is not None
        assert config.show_enter_actions is not None
        assert config.show_transition_effects is not None

    def test_mixed_inheritance_levels(self):
        """Test complex inheritance with multiple levels."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_lifecycle_actions=None,  # Will use detail_level default (False)
            show_enter_actions=True,  # Explicit override
        )
        config = options.to_config()

        assert config.show_lifecycle_actions is False  # From MINIMAL
        assert config.show_enter_actions is True  # User override
        assert config.show_during_actions is False  # Inherited from show_lifecycle_actions

    def test_idempotent_to_config(self):
        """Test that calling to_config() multiple times is idempotent."""
        options = PlantUMLOptions(
            detail_level='normal',
            show_lifecycle_actions=True,
        )
        config1 = options.to_config()
        config2 = options.to_config()

        assert config1.show_lifecycle_actions == config2.show_lifecycle_actions
        assert config1.show_enter_actions == config2.show_enter_actions
        assert config1.show_transition_guards == config2.show_transition_guards

    def test_to_config_preserves_non_optional_fields(self):
        """Test that to_config() preserves non-optional fields."""
        options = PlantUMLOptions(
            detail_level='normal',
            variable_display_mode='legend',
            state_name_format=('name', 'path'),
            event_name_format=('extra_name', 'name'),
            abstract_action_marker='symbol',
            max_action_lines=10,
            max_depth=5,
            collapsed_state_marker='+++',
            use_skinparam=False,
            use_stereotypes=False,
            custom_colors={'Event1': '#FF0000'},
        )
        config = options.to_config()

        assert config.variable_display_mode == 'legend'
        assert config.state_name_format == ('name', 'path')
        assert config.event_name_format == ('extra_name', 'name')
        assert config.abstract_action_marker == 'symbol'
        assert config.max_action_lines == 10
        assert config.max_depth == 5
        assert config.collapsed_state_marker == '+++'
        assert config.use_skinparam is False
        assert config.use_stereotypes is False
        assert config.custom_colors == {'Event1': '#FF0000'}


@pytest.mark.unittest
class TestPlantUMLOptionsEdgeCases:
    """Test cases for edge cases and boundary conditions."""

    def test_all_explicit_false(self):
        """Test when all options are explicitly set to False."""
        options = PlantUMLOptions(
            detail_level='normal',
            show_variable_definitions=False,
            show_lifecycle_actions=False,
            show_transition_guards=False,
            show_transition_effects=False,
            show_events=False,
        )
        config = options.to_config()

        assert config.show_variable_definitions is False
        assert config.show_lifecycle_actions is False
        assert config.show_enter_actions is False
        assert config.show_transition_guards is False
        assert config.show_transition_effects is False
        assert config.show_events is False

    def test_all_explicit_true(self):
        """Test when all options are explicitly set to True."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_variable_definitions=True,
            show_lifecycle_actions=True,
            show_enter_actions=True,
            show_during_actions=True,
            show_exit_actions=True,
            show_aspect_actions=True,
            show_abstract_actions=True,
            show_concrete_actions=True,
            show_transition_guards=True,
            show_transition_effects=True,
            show_events=True,
            show_pseudo_state_style=True,
        )
        config = options.to_config()

        assert config.show_variable_definitions is True
        assert config.show_lifecycle_actions is True
        assert config.show_enter_actions is True
        assert config.show_during_actions is True
        assert config.show_exit_actions is True
        assert config.show_aspect_actions is True
        assert config.show_abstract_actions is True
        assert config.show_concrete_actions is True
        assert config.show_transition_guards is True
        assert config.show_transition_effects is True
        assert config.show_events is True
        assert config.show_pseudo_state_style is True

    def test_name_format_single_element(self):
        """Test name format with single element."""
        options = PlantUMLOptions(
            state_name_format=('name',),
            event_name_format=('path',),
        )
        config = options.to_config()

        assert config.state_name_format == ('name',)
        assert config.event_name_format == ('path',)

    def test_name_format_multiple_elements(self):
        """Test name format with multiple elements."""
        options = PlantUMLOptions(
            state_name_format=('extra_name', 'name', 'path'),
            event_name_format=('name', 'extra_name', 'path'),
        )
        config = options.to_config()

        assert config.state_name_format == ('extra_name', 'name', 'path')
        assert config.event_name_format == ('name', 'extra_name', 'path')

    def test_max_values(self):
        """Test with maximum reasonable values."""
        options = PlantUMLOptions(
            max_action_lines=1000,
            max_depth=100,
        )
        config = options.to_config()

        assert config.max_action_lines == 1000
        assert config.max_depth == 100

    def test_none_max_values(self):
        """Test with None max values (unlimited)."""
        options = PlantUMLOptions(
            max_action_lines=None,
            max_depth=None,
        )
        config = options.to_config()

        assert config.max_action_lines is None
        assert config.max_depth is None


@pytest.mark.unittest
class TestPlantUMLOptionsDetailLevelDefaults:
    """Test cases for _get_detail_level_defaults() method."""

    def test_get_minimal_defaults(self):
        """Test getting MINIMAL detail level defaults."""
        options = PlantUMLOptions(detail_level='minimal')
        defaults = options._get_detail_level_defaults()

        assert defaults['show_variable_definitions'] is False
        assert defaults['show_lifecycle_actions'] is False
        assert defaults['show_transition_guards'] is True
        assert defaults['show_transition_effects'] is True
        assert defaults['show_events'] is True
        assert defaults['show_pseudo_state_style'] is False

    def test_get_normal_defaults(self):
        """Test getting NORMAL detail level defaults."""
        options = PlantUMLOptions(detail_level='normal')
        defaults = options._get_detail_level_defaults()

        assert defaults['show_variable_definitions'] is False
        assert defaults['show_lifecycle_actions'] is False
        assert defaults['show_transition_guards'] is True
        assert defaults['show_transition_effects'] is True
        assert defaults['show_events'] is True
        assert defaults['show_pseudo_state_style'] is True

    def test_get_full_defaults(self):
        """Test getting FULL detail level defaults."""
        options = PlantUMLOptions(detail_level='full')
        defaults = options._get_detail_level_defaults()

        assert defaults['show_variable_definitions'] is True
        assert defaults['show_lifecycle_actions'] is True
        assert defaults['show_transition_guards'] is True
        assert defaults['show_transition_effects'] is True
        assert defaults['show_events'] is True
        assert defaults['show_pseudo_state_style'] is True


@pytest.fixture()
def complex_state_machine_for_plantuml():
    """Build a complex state machine used for PlantUML options integration checks."""
    ast_node = parse_with_grammar_entry(
        textwrap.dedent(
            """
            def int temp = 20;
            def int retry_count = 0;
            def int alarm = 0;

            state System named "系统" {
                event Boot named "启动";
                event Reset named "复位";

                >> during before {
                    retry_count = retry_count + 1;
                }
                >> during after abstract GlobalAudit;

                state Standby named "待机" {
                    enter {
                        alarm = 0;
                    }

                    state Waiting;
                    pseudo state Bypass;

                    [*] -> Waiting : Boot;
                    Waiting -> Bypass : if [temp > 100] effect {
                        alarm = 1;
                    };
                    Bypass -> Waiting : /Reset;
                }

                state Active named "工作" {
                    enter abstract Prepare;
                    during before abstract Poll;
                    during after {
                        temp = temp + 1;
                    }
                    exit {
                        retry_count = 0;
                    }

                    state Running;
                    state Cooling;

                    [*] -> Running;
                    Running -> Cooling : if [temp >= 80] effect {
                        alarm = 1;
                    };
                    Cooling -> Running :: Cooled effect {
                        alarm = 0;
                    };
                    Cooling -> [*] :: Stop;
                }

                [*] -> Standby;
                Standby -> Active : /Boot;
                Active -> Standby :: Pause;
            }
            """
        ),
        entry_name='state_machine_dsl',
    )
    return parse_dsl_node_to_state_machine(ast_node)


@pytest.mark.unittest
class TestPlantUMLOptionsComplexExample:
    """Complex end-to-end checks for rendering with the new PlantUMLOptions system."""

    def test_complex_example_customized_rendering(self, complex_state_machine_for_plantuml):
        """Test a complex model rendered with multiple option overrides."""
        options = PlantUMLOptions(
            detail_level='minimal',
            show_variable_definitions=True,
            variable_display_mode='note',
            state_name_format=('extra_name', 'name'),
            show_lifecycle_actions=True,
            show_enter_actions=True,
            show_during_actions=False,
            show_exit_actions=True,
            show_aspect_actions=True,
            show_transition_effects=True,
            transition_effect_mode='note',
            show_pseudo_state_style=True,
        )

        result = complex_state_machine_for_plantuml.to_plantuml(options)

        # variable definitions forced on, despite MINIMAL preset
        assert 'note as DefinitionNote' in result
        assert 'def int temp = 20;' in result

        # custom state naming format is applied
        assert '"系统 (System)"' in result
        assert '"待机 (Standby)"' in result
        assert '"工作 (Active)"' in result

        # pseudo state style is visible
        assert '#line.dotted' in result

        # root aspect actions are shown, but regular during actions are hidden
        assert 'GlobalAudit' in result
        assert 'retry_count = retry_count + 1;' in result
        assert 'temp = temp + 1;' not in result

        # transition effects are shown as notes
        assert 'note on link' in result
        assert 'effect {' in result

    def test_complex_example_transition_visibility_switch(self, complex_state_machine_for_plantuml):
        """Test transition label/detail toggles while keeping arrows visible."""
        options = PlantUMLOptions(
            detail_level='full',
            show_events=False,
            show_transition_guards=False,
            show_transition_effects=False,
        )

        result = complex_state_machine_for_plantuml.to_plantuml(options)

        # Transition arrows are always visible (state aliases are fully qualified).
        assert 'system__standby__waiting --> system__standby__bypass' in result
        assert 'system__active__running --> system__active__cooling' in result
        assert '[*] --> system' in result
        assert 'system --> [*]' in result

        # But event/guard/effect decorations can be hidden.
        assert 'note on link' not in result

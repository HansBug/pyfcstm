"""
Integration tests for PlantUML generation with PlantUMLOptions.

This module tests the integration of PlantUMLOptions with the State and
StateMachine to_plantuml() methods, ensuring proper configuration application.
"""

import pytest

from pyfcstm.model.model import State, StateMachine, VarDefine
from pyfcstm.model.plantuml import PlantUMLOptions
from pyfcstm.model.expr import Integer


@pytest.mark.unittest
class TestStatePlantUMLGeneration:
    """Test cases for State.to_plantuml() with PlantUMLOptions."""

    def test_state_default_options(self):
        """Test state PlantUML generation with default options."""
        state = State(
            name='TestState',
            extra_name='测试状态',
            path=('TestState',),
            substates={},
        )
        result = state.to_plantuml()

        # Default should show extra_name
        assert '"测试状态"' in result
        assert 'as test_state' in result

    def test_state_name_format_name_only(self):
        """Test state name format with name only."""
        state = State(
            name='TestState',
            extra_name='测试状态',
            path=('TestState',),
            substates={},
        )
        options = PlantUMLOptions(state_name_format=('name',))
        result = state.to_plantuml(options)

        assert '"TestState"' in result
        assert '测试状态' not in result

    def test_state_name_format_extra_name_and_name(self):
        """Test state name format with extra_name and name."""
        state = State(
            name='TestState',
            extra_name='测试状态',
            path=('TestState',),
            substates={},
        )
        options = PlantUMLOptions(state_name_format=('extra_name', 'name'))
        result = state.to_plantuml(options)

        assert '"测试状态 (TestState)"' in result

    def test_state_name_format_fallback_when_no_extra_name(self):
        """Test state name format falls back to name when extra_name is missing."""
        state = State(
            name='TestState',
            extra_name=None,
            path=('TestState',),
            substates={},
        )
        options = PlantUMLOptions(state_name_format=('extra_name',))
        result = state.to_plantuml(options)

        # Should fallback to name
        assert '"TestState"' in result

    def test_state_pseudo_style_enabled(self):
        """Test pseudo state style is shown when enabled."""
        state = State(
            name='PseudoState',
            extra_name=None,
            path=('PseudoState',),
            substates={},
            is_pseudo=True,
        )
        options = PlantUMLOptions(show_pseudo_state_style=True)
        result = state.to_plantuml(options)

        assert '#line.dotted' in result

    def test_state_pseudo_style_disabled(self):
        """Test pseudo state style is hidden when disabled."""
        state = State(
            name='PseudoState',
            extra_name=None,
            path=('PseudoState',),
            substates={},
            is_pseudo=True,
        )
        options = PlantUMLOptions(show_pseudo_state_style=False)
        result = state.to_plantuml(options)

        assert '#line.dotted' not in result



    def test_state_to_plantuml_accepts_detail_level_string(self):
        """Test State.to_plantuml accepts detail level string input."""
        state = State(
            name='TestState',
            extra_name='测试状态',
            path=('TestState',),
            substates={},
        )

        result = state.to_plantuml('minimal')

        assert 'state "测试状态" as test_state' in result

    def test_state_to_plantuml_rejects_invalid_option_type(self):
        """Test State.to_plantuml rejects invalid option type."""
        state = State(
            name='TestState',
            extra_name='测试状态',
            path=('TestState',),
            substates={},
        )

        with pytest.raises(TypeError, match='Invalid plantuml options type'):
            state.to_plantuml(1)

    """Test cases for StateMachine.to_plantuml() with PlantUMLOptions."""

    def test_state_machine_default_options(self):
        """Test state machine PlantUML generation with default options."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        var_def = VarDefine(
            name='counter',
            type='int',
            init=Integer(value=0),
        )
        sm = StateMachine(
            defines={'counter': var_def},
            root_state=root_state,
        )

        result = sm.to_plantuml()

        assert '@startuml' in result
        assert '@enduml' in result
        assert 'hide empty description' in result
        # Default NORMAL level now focuses on major transition information
        # and hides verbose variable definitions.
        assert 'defines' not in result
        assert 'counter' not in result

    def test_state_machine_minimal_detail(self):
        """Test state machine with MINIMAL detail level."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        var_def = VarDefine(
            name='counter',
            type='int',
            init=Integer(value=0),
        )
        sm = StateMachine(
            defines={'counter': var_def},
            root_state=root_state,
        )

        options = PlantUMLOptions(detail_level='minimal')
        result = sm.to_plantuml(options)

        # MINIMAL level hides variable definitions
        assert 'defines' not in result
        assert 'counter' not in result

    def test_state_machine_variable_definitions_shown(self):
        """Test variable definitions are shown when enabled."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        var_def = VarDefine(
            name='counter',
            type='int',
            init=Integer(value=0),
        )
        sm = StateMachine(
            defines={'counter': var_def},
            root_state=root_state,
        )

        options = PlantUMLOptions(
            show_variable_definitions=True,
            variable_display_mode='note',
        )
        result = sm.to_plantuml(options)

        assert 'note as DefinitionNote' in result
        assert 'defines {' in result
        assert 'counter' in result

    def test_state_machine_variable_definitions_hidden(self):
        """Test variable definitions are hidden when disabled."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        var_def = VarDefine(
            name='counter',
            type='int',
            init=Integer(value=0),
        )
        sm = StateMachine(
            defines={'counter': var_def},
            root_state=root_state,
        )

        options = PlantUMLOptions(show_variable_definitions=False)
        result = sm.to_plantuml(options)

        assert 'DefinitionNote' not in result
        assert 'defines' not in result

    def test_state_machine_propagates_options_to_states(self):
        """Test that options are propagated to child states."""
        root_state = State(
            name='Root',
            extra_name='根状态',
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={},
            root_state=root_state,
        )

        options = PlantUMLOptions(state_name_format=('name', 'extra_name'))
        result = sm.to_plantuml(options)

        # State name should follow the format
        assert '"Root (根状态)"' in result
    def test_state_machine_to_plantuml_accepts_detail_level_string(self):
        """Test StateMachine.to_plantuml accepts detail level string input."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={},
            root_state=root_state,
        )

        result = sm.to_plantuml('full')

        assert '@startuml' in result
        assert '@enduml' in result

    def test_state_machine_to_plantuml_rejects_invalid_option_type(self):
        """Test StateMachine.to_plantuml rejects invalid option type."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={},
            root_state=root_state,
        )

        with pytest.raises(TypeError, match='Invalid plantuml options type'):
            sm.to_plantuml(object())


@pytest.mark.unittest
class TestPlantUMLOptionsEdgeCases:
    """Test edge cases for PlantUML generation with options."""

    def test_empty_state_machine(self):
        """Test empty state machine with no variables."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={},
            root_state=root_state,
        )

        result = sm.to_plantuml()

        assert '@startuml' in result
        assert '@enduml' in result
        # No variable definitions should be shown
        assert 'DefinitionNote' not in result

    def test_state_with_no_actions(self):
        """Test state with no lifecycle actions."""
        state = State(
            name='EmptyState',
            extra_name=None,
            path=('EmptyState',),
            substates={},
        )

        options = PlantUMLOptions(show_lifecycle_actions=True)
        result = state.to_plantuml(options)

        # Should not have action text
        assert 'EmptyState :' not in result


@pytest.mark.unittest
class TestActionFilteringAndFormatting:
    """Test cases for action filtering and formatting features."""

    def test_show_abstract_actions_only(self):
        """Test showing only abstract actions."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int counter = 0;

        state System {
            state Active {
                enter abstract InitHardware;
                enter {
                    counter = 0;
                }
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        # Show only abstract actions
        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            show_abstract_actions=True,
            show_concrete_actions=False,
        )
        result = sm.to_plantuml(options)

        # Should show abstract action
        assert 'enter abstract InitHardware' in result
        # Should not show concrete action
        assert 'counter = 0' not in result

    def test_show_concrete_actions_only(self):
        """Test showing only concrete actions."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int counter = 0;

        state System {
            state Active {
                enter abstract InitHardware;
                enter {
                    counter = 0;
                }
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        # Show only concrete actions
        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            show_abstract_actions=False,
            show_concrete_actions=True,
        )
        result = sm.to_plantuml(options)

        # Should not show abstract action
        assert 'enter abstract InitHardware' not in result
        # Should show concrete action
        assert 'counter = 0' in result

    def test_show_both_abstract_and_concrete_actions(self):
        """Test showing both abstract and concrete actions."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int counter = 0;

        state System {
            state Active {
                enter abstract InitHardware;
                enter {
                    counter = 0;
                }
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        # Show both types
        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            show_abstract_actions=True,
            show_concrete_actions=True,
        )
        result = sm.to_plantuml(options)

        # Should show both
        assert 'enter abstract InitHardware' in result
        assert 'counter = 0' in result

    def test_abstract_action_marker_text(self):
        """Test abstract action marker with text mode."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        state System {
            state Active {
                enter abstract InitHardware;
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            abstract_action_marker='text',
        )
        result = sm.to_plantuml(options)

        # Should use 'abstract' keyword
        assert 'enter abstract InitHardware' in result
        assert '«abstract»' not in result

    def test_abstract_action_marker_symbol(self):
        """Test abstract action marker with symbol mode."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        state System {
            state Active {
                enter abstract InitHardware;
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            abstract_action_marker='symbol',
        )
        result = sm.to_plantuml(options)

        # Should use symbol marker (may be Unicode escaped in JSON)
        assert ('«abstract»' in result or '\\u00ababstract\\u00bb' in result)
        assert 'InitHardware' in result

    def test_abstract_action_marker_none(self):
        """Test abstract action marker with none mode."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        state System {
            state Active {
                enter abstract InitHardware;
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            abstract_action_marker='none',
        )
        result = sm.to_plantuml(options)

        # Should not have abstract marker
        assert 'enter abstract InitHardware' not in result
        assert '«abstract»' not in result
        # But should still show the action name
        assert 'InitHardware' in result

    def test_max_action_lines_limit(self):
        """Test max_action_lines limits the number of lines shown."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int a = 0;
        def int b = 0;
        def int c = 0;
        def int d = 0;

        state System {
            state Active {
                enter {
                    a = 1;
                    b = 2;
                    c = 3;
                    d = 4;
                }
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        # Limit to 3 lines (enter {, a = 1;, b = 2;)
        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            max_action_lines=3,
        )
        result = sm.to_plantuml(options)

        # Should have ellipsis indicating truncation
        assert '...' in result
        # Should show first lines
        assert 'a = 1' in result
        assert 'b = 2' in result
        # Should not show later lines
        assert 'c = 3' not in result
        assert 'd = 4' not in result

    def test_max_action_lines_no_limit(self):
        """Test max_action_lines with None shows all lines."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int a = 0;
        def int b = 0;
        def int c = 0;
        def int d = 0;

        state System {
            state Active {
                enter {
                    a = 1;
                    b = 2;
                    c = 3;
                    d = 4;
                }
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        # No limit
        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            max_action_lines=None,
        )
        result = sm.to_plantuml(options)

        # Should show all lines
        assert 'a = 1' in result
        assert 'b = 2' in result
        assert 'c = 3' in result
        assert 'd = 4' in result

    def test_combined_filtering_and_formatting(self):
        """Test combined abstract/concrete filtering with formatting."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int counter = 0;

        state System {
            state Active {
                enter abstract InitHardware;
                enter {
                    counter = 0;
                }
                during abstract ProcessData;
                during {
                    counter = counter + 1;
                }
            }

            [*] -> Active;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        # Show only abstract with symbol marker
        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            show_abstract_actions=True,
            show_concrete_actions=False,
            abstract_action_marker='symbol',
        )
        result = sm.to_plantuml(options)

        # Should show abstract actions with symbol
        assert ('«abstract»' in result or '\\u00ababstract\\u00bb' in result)
        assert 'InitHardware' in result
        assert 'ProcessData' in result
        # Should not show concrete actions
        assert 'counter = 0' not in result
        assert 'counter = counter + 1' not in result


@pytest.mark.unittest
class TestCollapseEmptyStates:
    """Test cases for collapse_empty_states feature."""

    def test_collapse_empty_states_disabled(self):
        """Test that empty states show actions when collapse is disabled."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int counter = 0;

        state System {
            state EmptyState;
            state ActiveState {
                enter {
                    counter = 1;
                }
            }

            [*] -> EmptyState;
            EmptyState -> ActiveState;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        options = PlantUMLOptions(
            collapse_empty_states=False,
            show_lifecycle_actions=True,
        )
        result = sm.to_plantuml(options)

        # Empty state should be present
        assert 'EmptyState' in result
        # Active state should show actions
        assert 'counter = 1' in result

    def test_collapse_empty_states_enabled(self):
        """Test that empty states are collapsed when enabled."""
        from pyfcstm.dsl import parse_with_grammar_entry
        from pyfcstm.model.model import parse_dsl_node_to_state_machine

        dsl_code = """
        def int counter = 0;

        state System {
            state EmptyState;
            state ActiveState {
                enter {
                    counter = 1;
                }
            }

            [*] -> EmptyState;
            EmptyState -> ActiveState;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast_node)

        options = PlantUMLOptions(
            collapse_empty_states=True,
            show_lifecycle_actions=True,
        )
        result = sm.to_plantuml(options)

        # Empty state should still be present (structure preserved)
        assert 'EmptyState' in result
        # But should not have action text (EmptyState : ...)
        assert 'System_EmptyState :' not in result
        # Active state should still show actions
        assert 'counter = 1' in result


@pytest.mark.unittest
class TestUseSkinparam:
    """Test cases for use_skinparam feature."""

    def test_use_skinparam_enabled(self):
        """Test that skinparam styling is added when enabled."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={},
            root_state=root_state,
        )

        options = PlantUMLOptions(use_skinparam=True)
        result = sm.to_plantuml(options)

        # Should contain skinparam block
        assert 'skinparam state {' in result
        assert 'BackgroundColor<<pseudo>> LightGray' in result
        assert 'BackgroundColor<<composite>> LightBlue' in result
        assert 'BorderColor<<pseudo>> Gray' in result
        assert 'FontStyle<<pseudo>> italic' in result

    def test_use_skinparam_disabled(self):
        """Test that skinparam styling is not added when disabled."""
        root_state = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={},
            root_state=root_state,
        )

        options = PlantUMLOptions(use_skinparam=False)
        result = sm.to_plantuml(options)

        # Should not contain skinparam block
        assert 'skinparam' not in result


@pytest.mark.unittest
class TestUseStereotypes:
    """Test cases for use_stereotypes feature."""

    def test_use_stereotypes_enabled_pseudo_state(self):
        """Test that pseudo state stereotype is added when enabled."""
        state = State(
            name='PseudoState',
            extra_name=None,
            path=('PseudoState',),
            substates={},
            is_pseudo=True,
        )

        options = PlantUMLOptions(use_stereotypes=True)
        result = state.to_plantuml(options)

        # Should have pseudo stereotype
        assert '<<pseudo>>' in result

    def test_use_stereotypes_enabled_composite_state(self):
        """Test that composite state stereotype is added when enabled."""
        child_state = State(
            name='Child',
            extra_name=None,
            path=('Parent', 'Child'),
            substates={},
        )
        parent_state = State(
            name='Parent',
            extra_name=None,
            path=('Parent',),
            substates={'Child': child_state},
        )

        options = PlantUMLOptions(use_stereotypes=True)
        result = parent_state.to_plantuml(options)

        # Should have composite stereotype
        assert '<<composite>>' in result

    def test_use_stereotypes_enabled_pseudo_composite_state(self):
        """Test that both stereotypes are added for pseudo composite state."""
        child_state = State(
            name='Child',
            extra_name=None,
            path=('Parent', 'Child'),
            substates={},
        )
        parent_state = State(
            name='Parent',
            extra_name=None,
            path=('Parent',),
            substates={'Child': child_state},
            is_pseudo=True,
        )

        options = PlantUMLOptions(use_stereotypes=True)
        result = parent_state.to_plantuml(options)

        # Should have both stereotypes
        assert '<<pseudo,composite>>' in result

    def test_use_stereotypes_disabled(self):
        """Test that stereotypes are not added when disabled."""
        child_state = State(
            name='Child',
            extra_name=None,
            path=('Parent', 'Child'),
            substates={},
        )
        parent_state = State(
            name='Parent',
            extra_name=None,
            path=('Parent',),
            substates={'Child': child_state},
            is_pseudo=True,
        )

        options = PlantUMLOptions(use_stereotypes=False)
        result = parent_state.to_plantuml(options)

        # Should not have stereotypes
        assert '<<pseudo>>' not in result
        assert '<<composite>>' not in result


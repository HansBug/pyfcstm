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



@pytest.mark.unittest
class TestStateMachinePlantUMLGeneration:
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

"""
Comprehensive test coverage for PlantUML generation features.

This module provides additional test cases to ensure complete code coverage
for plantuml.py and to_plantuml() methods in model.py.
"""

import pytest

from pyfcstm.model.model import State, StateMachine, VarDefine, Event, Transition, OnStage, OnAspect, Operation
from pyfcstm.model.plantuml import PlantUMLOptions, format_event_name, collect_event_transitions, assign_event_colors
from pyfcstm.model.expr import Integer, Variable, BinaryOp
from pyfcstm.dsl import node as dsl_nodes


@pytest.mark.unittest
class TestEventNameFormatting:
    """Test cases for format_event_name function coverage."""

    def test_format_event_name_path_single_element(self):
        """Test event path formatting with single element."""
        event = Event(name='TestEvent', state_path=(), extra_name=None)
        result = format_event_name(event, ('path',))

        # Single element path should be /TestEvent
        assert result == '/TestEvent'

    def test_format_event_name_path_multiple_elements(self):
        """Test event path formatting with multiple elements."""
        event = Event(name='TestEvent', state_path=('Root', 'State'), extra_name=None)
        result = format_event_name(event, ('path',))

        # Multiple elements should skip first and prepend /
        assert result == '/State.TestEvent'

    def test_format_event_name_relpath_without_trans_node(self):
        """Test relpath formatting without trans_node."""
        event = Event(name='TestEvent', state_path=('Root', 'State'), extra_name=None)
        result = format_event_name(event, ('relpath',), trans_node=None)

        # Should fallback to path format
        assert result == '/State.TestEvent'

    def test_format_event_name_relpath_single_element_fallback(self):
        """Test relpath formatting with single element fallback."""
        event = Event(name='TestEvent', state_path=(), extra_name=None)
        result = format_event_name(event, ('relpath',), trans_node=None)

        # Single element fallback
        assert result == '/TestEvent'

    def test_format_event_name_empty_parts_fallback(self):
        """Test fallback when all format elements are skipped."""
        event = Event(name='TestEvent', state_path=('Root',), extra_name=None)
        # Use empty tuple to skip all elements
        result = format_event_name(event, ())

        # Should fallback to name
        assert result == 'TestEvent'


@pytest.mark.unittest
class TestStateListMethods:
    """Test cases for State list methods with filters."""

    def test_list_on_durings_with_is_abstract_filter(self):
        """Test list_on_durings with is_abstract filter."""
        abstract_action = OnStage(
            stage='during',
            aspect=None,
            name='AbstractAction',
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=('TestState', 'AbstractAction'),
        )
        concrete_action = OnStage(
            stage='during',
            aspect=None,
            name='ConcreteAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'ConcreteAction'),
        )
        state = State(
            name='TestState',
            extra_name=None,
            path=('TestState',),
            substates={},
            on_durings=[abstract_action, concrete_action],
        )

        # Filter for abstract only
        abstract_only = state.list_on_durings(is_abstract=True, with_ids=False)
        assert len(abstract_only) == 1
        assert abstract_only[0].name == 'AbstractAction'

        # Filter for concrete only
        concrete_only = state.list_on_durings(is_abstract=False, with_ids=False)
        assert len(concrete_only) == 1
        assert concrete_only[0].name == 'ConcreteAction'

    def test_list_on_durings_with_aspect_filter(self):
        """Test list_on_durings with aspect filter."""
        before_action = OnStage(
            stage='during',
            aspect='before',
            name='BeforeAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'BeforeAction'),
        )
        after_action = OnStage(
            stage='during',
            aspect='after',
            name='AfterAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'AfterAction'),
        )
        state = State(
            name='TestState',
            extra_name=None,
            path=('TestState',),
            substates={},
            on_durings=[before_action, after_action],
        )

        # Filter for before aspect
        before_only = state.list_on_durings(aspect='before', with_ids=False)
        assert len(before_only) == 1
        assert before_only[0].name == 'BeforeAction'

    def test_list_on_exits_with_is_abstract_filter(self):
        """Test list_on_exits with is_abstract filter."""
        abstract_exit = OnStage(
            stage='exit',
            aspect=None,
            name='AbstractExit',
            doc=None,
            operations=[],
            is_abstract=True,
            state_path=('TestState', 'AbstractExit'),
        )
        concrete_exit = OnStage(
            stage='exit',
            aspect=None,
            name='ConcreteExit',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'ConcreteExit'),
        )
        state = State(
            name='TestState',
            extra_name=None,
            path=('TestState',),
            substates={},
            on_exits=[abstract_exit, concrete_exit],
        )

        # Filter for abstract only
        abstract_only = state.list_on_exits(is_abstract=True, with_ids=False)
        assert len(abstract_only) == 1
        assert abstract_only[0].name == 'AbstractExit'

    def test_list_on_exits_with_ids(self):
        """Test list_on_exits with with_ids=True."""
        exit_action = OnStage(
            stage='exit',
            aspect=None,
            name='ExitAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'ExitAction'),
        )
        state = State(
            name='TestState',
            extra_name=None,
            path=('TestState',),
            substates={},
            on_exits=[exit_action],
        )

        # Get with IDs
        with_ids = state.list_on_exits(with_ids=True)
        assert len(with_ids) == 1
        assert with_ids[0][0] == 1  # ID should be 1
        assert with_ids[0][1].name == 'ExitAction'


@pytest.mark.unittest
class TestTransitionEffectModes:
    """Test cases for transition effect display modes."""

    def test_transition_effect_inline_mode(self):
        """Test inline transition effect mode."""
        operation = Operation(
            var_name='counter',
            expr=BinaryOp(
                x=Variable('counter'),
                op='+',
                y=Integer(1),
            )
        )
        child1 = State(
            name='Child1',
            extra_name=None,
            path=('Root', 'Child1'),
            substates={},
        )
        child2 = State(
            name='Child2',
            extra_name=None,
            path=('Root', 'Child2'),
            substates={},
        )
        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={'Child1': child1, 'Child2': child2},
            transitions=[
                Transition(
                    from_state='Child1',
                    to_state='Child2',
                    event=None,
                    guard=None,
                    effects=[operation],
                )
            ],
        )

        options = PlantUMLOptions(
            show_transition_effects=True,
            transition_effect_mode='inline'
        )
        result = root.to_plantuml(options)

        # Should have inline effect with /
        assert '/ counter = counter + 1' in result

    def test_transition_effect_note_mode(self):
        """Test note transition effect mode."""
        operation = Operation(
            var_name='counter',
            expr=Integer(0),
        )
        child1 = State(
            name='Child1',
            extra_name=None,
            path=('Root', 'Child1'),
            substates={},
        )
        child2 = State(
            name='Child2',
            extra_name=None,
            path=('Root', 'Child2'),
            substates={},
        )
        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={'Child1': child1, 'Child2': child2},
            transitions=[
                Transition(
                    from_state='Child1',
                    to_state='Child2',
                    event=None,
                    guard=None,
                    effects=[operation],
                )
            ],
        )

        options = PlantUMLOptions(
            show_transition_effects=True,
            transition_effect_mode='note'
        )
        result = root.to_plantuml(options)

        # Should have note on link
        assert 'note on link' in result
        assert 'effect {' in result
        assert 'end note' in result


@pytest.mark.unittest
class TestVariableDisplayModes:
    """Test cases for variable display modes."""

    def test_variable_display_legend_mode(self):
        """Test legend variable display mode."""
        var_def = VarDefine(
            name='counter',
            type='int',
            init=Integer(0),
        )
        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={'counter': var_def},
            root_state=root,
        )

        options = PlantUMLOptions(
            show_variable_definitions=True,
            variable_display_mode='legend'
        )
        result = sm.to_plantuml(options)

        # Should have legend with table
        assert 'legend right' in result
        assert '|= Variable |= Type |= Initial Value |' in result
        assert '| counter | int | 0 |' in result
        assert 'endlegend' in result

    def test_variable_display_note_mode(self):
        """Test note variable display mode."""
        var_def = VarDefine(
            name='counter',
            type='int',
            init=Integer(0),
        )
        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(
            defines={'counter': var_def},
            root_state=root,
        )

        options = PlantUMLOptions(
            show_variable_definitions=True,
            variable_display_mode='note'
        )
        result = sm.to_plantuml(options)

        # Should have note
        assert 'note as DefinitionNote' in result
        assert 'defines {' in result
        assert 'end note' in result


@pytest.mark.unittest
class TestEventColorAssignment:
    """Test cases for event color assignment."""

    def test_assign_event_colors_with_custom_colors(self):
        """Test event color assignment with custom colors."""
        event_map = {
            'Root.Event1': [],
            'Root.Event2': [],
        }
        custom_colors = {
            'Root.Event1': '#FF0000',
        }

        colors = assign_event_colors(event_map, custom_colors)

        # Event1 should use custom color
        assert colors['Root.Event1'] == '#FF0000'
        # Event2 should use default palette
        assert colors['Root.Event2'] in ['#4E79A7', '#F28E2B', '#E15759']

    def test_assign_event_colors_cycling_palette(self):
        """Test that color palette cycles for many events."""
        # Create more events than palette colors (10)
        event_map = {f'Root.Event{i}': [] for i in range(15)}

        colors = assign_event_colors(event_map)

        # Should have 15 colors assigned
        assert len(colors) == 15
        # Colors should cycle (event 10 should use same color as event 0)
        event_keys = sorted(event_map.keys())
        # First color in palette
        first_color = colors[event_keys[0]]
        # 11th event should cycle back to first color
        eleventh_color = colors[event_keys[10]]
        assert first_color == eleventh_color


@pytest.mark.unittest
class TestCollectEventTransitions:
    """Test cases for collect_event_transitions function."""

    def test_collect_event_transitions_multiple_states(self):
        """Test collecting events from multiple states."""
        event1 = Event(name='Event1', state_path=('Root',), extra_name=None)
        event2 = Event(name='Event2', state_path=('Root',), extra_name=None)

        child1 = State(
            name='Child1',
            extra_name=None,
            path=('Root', 'Child1'),
            substates={},
        )
        child2 = State(
            name='Child2',
            extra_name=None,
            path=('Root', 'Child2'),
            substates={},
        )
        child3 = State(
            name='Child3',
            extra_name=None,
            path=('Root', 'Child3'),
            substates={},
        )

        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={'Child1': child1, 'Child2': child2, 'Child3': child3},
            transitions=[
                Transition(
                    from_state='Child1',
                    to_state='Child2',
                    event=event1,
                    guard=None,
                    effects=[],
                ),
                Transition(
                    from_state='Child2',
                    to_state='Child3',
                    event=event1,  # Same event
                    guard=None,
                    effects=[],
                ),
                Transition(
                    from_state='Child3',
                    to_state='Child1',
                    event=event2,  # Different event
                    guard=None,
                    effects=[],
                ),
            ],
        )

        sm = StateMachine(defines={}, root_state=root)
        event_map = collect_event_transitions(sm)

        # Should have 2 events
        assert len(event_map) == 2
        # Event1 should have 2 transitions
        assert len(event_map['Root.Event1']) == 2
        # Event2 should have 1 transition
        assert len(event_map['Root.Event2']) == 1

    def test_collect_event_transitions_nested_states(self):
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
                Transition(
                    from_state='GrandChild1',
                    to_state='GrandChild2',
                    event=event,
                    guard=None,
                    effects=[],
                ),
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

        # Should find the event in nested state
        assert 'Root.Parent.TestEvent' in event_map
        assert len(event_map['Root.Parent.TestEvent']) == 1


@pytest.mark.unittest
class TestPlantUMLEdgeCases:
    """Test edge cases in PlantUML generation."""

    def test_empty_state_machine(self):
        """Test PlantUML generation for empty state machine."""
        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={},
        )
        sm = StateMachine(defines={}, root_state=root)

        result = sm.to_plantuml()

        # Should have basic structure
        assert '@startuml' in result
        assert '@enduml' in result
        assert 'state "Root"' in result

    def test_state_with_all_action_types(self):
        """Test state with enter, during, exit, and aspect actions."""
        enter_action = OnStage(
            stage='enter',
            aspect=None,
            name='EnterAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'EnterAction'),
        )
        during_action = OnStage(
            stage='during',
            aspect=None,
            name='DuringAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'DuringAction'),
        )
        exit_action = OnStage(
            stage='exit',
            aspect=None,
            name='ExitAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'ExitAction'),
        )
        aspect_action = OnAspect(
            stage='during',
            aspect='before',
            name='AspectAction',
            doc=None,
            operations=[],
            is_abstract=False,
            state_path=('TestState', 'AspectAction'),
        )

        state = State(
            name='TestState',
            extra_name=None,
            path=('TestState',),
            substates={},
            on_enters=[enter_action],
            on_durings=[during_action],
            on_exits=[exit_action],
            on_during_aspects=[aspect_action],
        )

        options = PlantUMLOptions(
            show_lifecycle_actions=True,
            show_enter_actions=True,
            show_during_actions=True,
            show_exit_actions=True,
            show_aspect_actions=True,
        )
        result = state.to_plantuml(options)

        # Should show all action types
        assert 'enter' in result
        assert 'during' in result
        assert 'exit' in result
        assert 'before' in result

    def test_multiple_transitions_same_states(self):
        """Test multiple transitions between same states."""
        event1 = Event(name='Event1', state_path=('Root',), extra_name=None)
        event2 = Event(name='Event2', state_path=('Root',), extra_name=None)

        child1 = State(
            name='Child1',
            extra_name=None,
            path=('Root', 'Child1'),
            substates={},
        )
        child2 = State(
            name='Child2',
            extra_name=None,
            path=('Root', 'Child2'),
            substates={},
        )

        root = State(
            name='Root',
            extra_name=None,
            path=('Root',),
            substates={'Child1': child1, 'Child2': child2},
            transitions=[
                Transition(
                    from_state='Child1',
                    to_state='Child2',
                    event=event1,
                    guard=None,
                    effects=[],
                ),
                Transition(
                    from_state='Child1',
                    to_state='Child2',
                    event=event2,
                    guard=None,
                    effects=[],
                ),
            ],
        )

        result = root.to_plantuml()

        # Should have both transitions
        assert result.count('root__child1 --> root__child2') == 2

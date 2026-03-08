"""
Unit tests for the State.resolve_event and StateMachine.resolve_event methods.

This module tests the event resolution functionality:
- State.resolve_event: supports relative, parent-relative, and absolute references
- StateMachine.resolve_event: supports only full path format (State1.State2.event_name)
"""

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model.model import parse_dsl_node_to_state_machine


@pytest.mark.unittest
class TestStateResolveEvent:
    """Test suite for State.resolve_event method."""

    @pytest.fixture
    def simple_hierarchy(self):
        """
        Create a simple state hierarchy with events for testing.

        Structure:
            Root
            ├── events: global_event
            └── System
                ├── events: system_event
                ├── Active
                │   └── events: active_event
                └── Idle
                    └── events: idle_event
        """
        dsl_code = """
        state Root {
            event global_event;

            state System {
                event system_event;

                state Active {
                    event active_event;
                }

                state Idle {
                    event idle_event;
                }

                [*] -> Active;
            }

            [*] -> System;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        state_machine = parse_dsl_node_to_state_machine(ast_node)

        root = state_machine.root_state
        system = root.substates["System"]
        active = system.substates["Active"]
        idle = system.substates["Idle"]

        return {
            "root": root,
            "system": system,
            "active": active,
            "idle": idle,
            "global_event": root.events["global_event"],
            "system_event": system.events["system_event"],
            "active_event": active.events["active_event"],
            "idle_event": idle.events["idle_event"]
        }

    @pytest.fixture
    def deep_hierarchy(self):
        """
        Create a deeper state hierarchy with events for testing.

        Structure:
            Root
            ├── events: root_event
            └── Level1
                ├── events: level1_event
                └── Level2
                    ├── events: level2_event
                    └── Level3
                        ├── events: level3_event
                        └── Level4
                            └── events: level4_event
        """
        dsl_code = """
        state Root {
            event root_event;

            state Level1 {
                event level1_event;

                state Level2 {
                    event level2_event;

                    state Level3 {
                        event level3_event;

                        state Level4 {
                            event level4_event;
                        }

                        [*] -> Level4;
                    }

                    [*] -> Level3;
                }

                [*] -> Level2;
            }

            [*] -> Level1;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        state_machine = parse_dsl_node_to_state_machine(ast_node)

        root = state_machine.root_state
        level1 = root.substates["Level1"]
        level2 = level1.substates["Level2"]
        level3 = level2.substates["Level3"]
        level4 = level3.substates["Level4"]

        return {
            "root": root,
            "level1": level1,
            "level2": level2,
            "level3": level3,
            "level4": level4,
            "root_event": root.events["root_event"],
            "level1_event": level1.events["level1_event"],
            "level2_event": level2.events["level2_event"],
            "level3_event": level3.events["level3_event"],
            "level4_event": level4.events["level4_event"]
        }

    # Test relative events (no leading '/' or '.')
    def test_relative_event_simple(self, simple_hierarchy):
        """Test resolving a simple relative event."""
        active = simple_hierarchy["active"]
        active_event = simple_hierarchy["active_event"]

        resolved = active.resolve_event("active_event")
        assert resolved is active_event
        assert resolved.name == "active_event"
        assert resolved.state_path == ("Root", "System", "Active")

    def test_relative_event_from_root(self, simple_hierarchy):
        """Test resolving a relative event from the root state."""
        root = simple_hierarchy["root"]
        global_event = simple_hierarchy["global_event"]

        resolved = root.resolve_event("global_event")
        assert resolved is global_event

    def test_relative_event_not_found(self, simple_hierarchy):
        """Test that resolving a non-existent relative event raises LookupError."""
        active = simple_hierarchy["active"]

        with pytest.raises(LookupError, match="Event 'nonexistent' not found"):
            active.resolve_event("nonexistent")

    # Test parent-relative events (starting with '.')
    def test_parent_relative_event_one_level(self, simple_hierarchy):
        """Test resolving a parent-relative event going up one level."""
        active = simple_hierarchy["active"]
        system_event = simple_hierarchy["system_event"]

        resolved = active.resolve_event(".system_event")
        assert resolved is system_event
        assert resolved.state_path == ("Root", "System")

    def test_parent_relative_event_two_levels(self, simple_hierarchy):
        """Test resolving a parent-relative event going up two levels."""
        active = simple_hierarchy["active"]
        global_event = simple_hierarchy["global_event"]

        resolved = active.resolve_event("..global_event")
        assert resolved is global_event
        assert resolved.state_path == ("Root",)

    def test_parent_relative_event_deep_hierarchy(self, deep_hierarchy):
        """Test parent-relative events in a deep hierarchy."""
        level4 = deep_hierarchy["level4"]

        # Go up 1 level
        event1 = level4.resolve_event(".level3_event")
        assert event1 is deep_hierarchy["level3_event"]

        # Go up 2 levels
        event2 = level4.resolve_event("..level2_event")
        assert event2 is deep_hierarchy["level2_event"]

        # Go up 3 levels
        event3 = level4.resolve_event("...level1_event")
        assert event3 is deep_hierarchy["level1_event"]

        # Go up 4 levels (to root)
        event4 = level4.resolve_event("....root_event")
        assert event4 is deep_hierarchy["root_event"]

    def test_parent_relative_event_beyond_root_error(self, simple_hierarchy):
        """Test that going beyond root raises an error."""
        active = simple_hierarchy["active"]

        with pytest.raises(ValueError, match="goes beyond root state"):
            active.resolve_event("...error")  # Only 2 levels up to root, 3 is too many

    def test_parent_relative_event_from_root_error(self, simple_hierarchy):
        """Test that parent-relative from root raises an error."""
        root = simple_hierarchy["root"]

        with pytest.raises(ValueError, match="goes beyond root state"):
            root.resolve_event(".error")

    def test_parent_relative_event_not_found(self, simple_hierarchy):
        """Test that resolving a non-existent parent-relative event raises LookupError."""
        active = simple_hierarchy["active"]

        with pytest.raises(LookupError, match="Event 'nonexistent' not found"):
            active.resolve_event(".nonexistent")

    # Test absolute events (starting with '/')
    def test_absolute_event_simple(self, simple_hierarchy):
        """Test resolving a simple absolute event."""
        active = simple_hierarchy["active"]
        global_event = simple_hierarchy["global_event"]

        resolved = active.resolve_event("/global_event")
        assert resolved is global_event

    def test_absolute_event_from_different_states(self, simple_hierarchy):
        """Test that absolute events resolve the same from different states."""
        active = simple_hierarchy["active"]
        idle = simple_hierarchy["idle"]
        system = simple_hierarchy["system"]
        global_event = simple_hierarchy["global_event"]

        event1 = active.resolve_event("/global_event")
        event2 = idle.resolve_event("/global_event")
        event3 = system.resolve_event("/global_event")

        assert event1 is event2 is event3 is global_event

    def test_absolute_event_from_root(self, simple_hierarchy):
        """Test resolving an absolute event from the root state."""
        root = simple_hierarchy["root"]
        global_event = simple_hierarchy["global_event"]

        resolved = root.resolve_event("/global_event")
        assert resolved is global_event

    def test_absolute_event_not_found(self, simple_hierarchy):
        """Test that resolving a non-existent absolute event raises LookupError."""
        active = simple_hierarchy["active"]

        with pytest.raises(LookupError, match="Event 'nonexistent' not found"):
            active.resolve_event("/nonexistent")

    # Test error cases
    def test_empty_event_reference_error(self, simple_hierarchy):
        """Test that empty event reference raises an error."""
        active = simple_hierarchy["active"]

        with pytest.raises(ValueError, match="Event reference cannot be empty"):
            active.resolve_event("")

    def test_absolute_event_just_slash_error(self, simple_hierarchy):
        """Test that absolute event with just '/' raises an error."""
        active = simple_hierarchy["active"]

        with pytest.raises(ValueError, match="Absolute event reference cannot be just '/'"):
            active.resolve_event("/")

    def test_parent_relative_event_only_dots_error(self, simple_hierarchy):
        """Test that parent-relative event with only dots raises an error."""
        active = simple_hierarchy["active"]

        with pytest.raises(ValueError, match="cannot end with dots"):
            active.resolve_event(".")

        with pytest.raises(ValueError, match="cannot end with dots"):
            active.resolve_event("..")

    def test_invalid_event_reference_empty_parts(self, simple_hierarchy):
        """Test that event references with empty parts raise errors."""
        active = simple_hierarchy["active"]

        with pytest.raises(ValueError, match="Invalid relative event reference"):
            active.resolve_event("error..critical")

        with pytest.raises(ValueError, match="Invalid absolute event reference"):
            active.resolve_event("/error..critical")

        with pytest.raises(ValueError, match="Invalid parent-relative event reference"):
            active.resolve_event(".error..critical")

    def test_event_reference_trailing_dot(self, simple_hierarchy):
        """Test that event references with trailing dots raise errors."""
        active = simple_hierarchy["active"]

        with pytest.raises(ValueError, match="Invalid relative event reference"):
            active.resolve_event("error.")

        with pytest.raises(ValueError, match="Invalid absolute event reference"):
            active.resolve_event("/error.")

        with pytest.raises(ValueError, match="Invalid parent-relative event reference"):
            active.resolve_event(".error.")

    # Test state not found errors
    def test_state_not_found_in_hierarchy(self, simple_hierarchy):
        """Test that referencing a non-existent state raises LookupError."""
        active = simple_hierarchy["active"]

        with pytest.raises(LookupError, match="State .* not found in hierarchy"):
            active.resolve_event("/NonExistent.event")

    # Test edge cases
    def test_single_character_event_names(self, simple_hierarchy):
        """Test that single character event names work correctly."""
        # Parse a new state machine with single-character event
        dsl_code = """
        state Root {
            event e;
            event g;

            state System {
                event s;
            }

            [*] -> System;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        state_machine = parse_dsl_node_to_state_machine(ast_node)

        root = state_machine.root_state
        system = root.substates["System"]

        # Test relative event
        e_event = root.events["e"]
        resolved = root.resolve_event("e")
        assert resolved is e_event

        # Test absolute event
        g_event = root.events["g"]
        resolved = system.resolve_event("/g")
        assert resolved is g_event

        # Test parent-relative event
        s_event = system.events["s"]
        resolved = system.resolve_event("s")
        assert resolved is s_event

    def test_numeric_event_names(self, simple_hierarchy):
        """Test that numeric event names work correctly."""
        dsl_code = """
        state Root {
            event event123;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        state_machine = parse_dsl_node_to_state_machine(ast_node)

        root = state_machine.root_state
        event123 = root.events["event123"]

        resolved = root.resolve_event("event123")
        assert resolved is event123

    def test_event_names_with_underscores(self, simple_hierarchy):
        """Test that event names with underscores work correctly."""
        dsl_code = """
        state Root {
            event error_handler;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        state_machine = parse_dsl_node_to_state_machine(ast_node)

        root = state_machine.root_state
        error_event = root.events["error_handler"]

        resolved = root.resolve_event("error_handler")
        assert resolved is error_event

    # Test consistency across different reference types
    def test_reference_type_equivalence(self, simple_hierarchy):
        """Test that different reference types can point to the same event."""
        active = simple_hierarchy["active"]
        system = simple_hierarchy["system"]
        root = simple_hierarchy["root"]
        system_event = simple_hierarchy["system_event"]

        # All these should resolve to the same event
        event1 = active.resolve_event(".system_event")  # From Active, up 1 level
        event2 = system.resolve_event("system_event")  # From System, relative
        event3 = root.resolve_event("/System.system_event")  # From Root, absolute

        assert event1 is event2 is event3 is system_event

    def test_resolve_event_preserves_state_structure(self, simple_hierarchy):
        """Test that resolving events doesn't modify the state structure."""
        active = simple_hierarchy["active"]
        original_path = active.path
        original_parent = active.parent
        original_events = dict(active.events)

        # Resolve various events
        active.resolve_event("active_event")
        active.resolve_event(".system_event")
        active.resolve_event("/global_event")

        # Verify state structure is unchanged
        assert active.path == original_path
        assert active.parent == original_parent
        assert active.events == original_events


@pytest.mark.unittest
class TestStateMachineResolveEvent:
    """Test suite for StateMachine.resolve_event method."""

    @pytest.fixture
    def state_machine(self):
        """
        Create a state machine with events for testing.

        Structure:
            Root
            ├── events: global_event
            └── System
                ├── events: system_event
                ├── Active
                │   └── events: active_event
                └── Idle
                    └── events: idle_event
        """
        dsl_code = """
        state Root {
            event global_event;

            state System {
                event system_event;

                state Active {
                    event active_event;
                }

                state Idle {
                    event idle_event;
                }

                [*] -> Active;
            }

            [*] -> System;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        return parse_dsl_node_to_state_machine(ast_node)

    # Test full path resolution
    def test_resolve_event_full_path_root(self, state_machine):
        """Test resolving an event at the root level."""
        event = state_machine.resolve_event("Root.global_event")

        assert event.name == "global_event"
        assert event.state_path == ("Root",)
        assert event is state_machine.root_state.events["global_event"]

    def test_resolve_event_full_path_nested(self, state_machine):
        """Test resolving an event in a nested state."""
        event = state_machine.resolve_event("Root.System.system_event")

        assert event.name == "system_event"
        assert event.state_path == ("Root", "System")

    def test_resolve_event_full_path_deeply_nested(self, state_machine):
        """Test resolving an event in a deeply nested state."""
        event = state_machine.resolve_event("Root.System.Active.active_event")

        assert event.name == "active_event"
        assert event.state_path == ("Root", "System", "Active")

    def test_resolve_event_multiple_calls_same_event(self, state_machine):
        """Test that multiple calls return the same event object."""
        event1 = state_machine.resolve_event("Root.global_event")
        event2 = state_machine.resolve_event("Root.global_event")

        assert event1 is event2

    # Test error cases
    def test_resolve_event_empty_path(self, state_machine):
        """Test that empty path raises ValueError."""
        with pytest.raises(ValueError, match="Event path cannot be empty"):
            state_machine.resolve_event("")

    def test_resolve_event_path_with_empty_parts(self, state_machine):
        """Test that path with empty parts raises ValueError."""
        with pytest.raises(ValueError, match="contains empty parts"):
            state_machine.resolve_event("Root..System.event")

    def test_resolve_event_too_short_path(self, state_machine):
        """Test that path with only one component raises ValueError."""
        with pytest.raises(ValueError, match="must contain at least state name and event name"):
            state_machine.resolve_event("Root")

    def test_resolve_event_wrong_root_name(self, state_machine):
        """Test that wrong root name raises LookupError."""
        with pytest.raises(LookupError, match="Event path root .* does not match"):
            state_machine.resolve_event("WrongRoot.global_event")

    def test_resolve_event_state_not_found(self, state_machine):
        """Test that non-existent state raises LookupError."""
        with pytest.raises(LookupError, match="State 'NonExistent' not found"):
            state_machine.resolve_event("Root.NonExistent.event")

    def test_resolve_event_event_not_found(self, state_machine):
        """Test that non-existent event raises LookupError."""
        with pytest.raises(LookupError, match="Event 'nonexistent' not found"):
            state_machine.resolve_event("Root.System.nonexistent")

    def test_resolve_event_wrong_state_path(self, state_machine):
        """Test that wrong state path raises LookupError."""
        with pytest.raises(LookupError, match="State .* not found"):
            state_machine.resolve_event("Root.System.WrongState.event")

    # Test that relative/absolute notations are NOT supported
    def test_resolve_event_no_relative_support(self, state_machine):
        """Test that relative paths (without leading /) are not supported as shortcuts."""
        # This should fail because "System.system_event" is not a valid full path
        # (it doesn't start with the root state name)
        with pytest.raises(LookupError, match="Event path root .* does not match"):
            state_machine.resolve_event("System.system_event")

    def test_resolve_event_no_absolute_notation_support(self, state_machine):
        """Test that absolute notation (leading /) is not supported."""
        # The leading slash should be treated as part of the state name,
        # which will not match the root state
        with pytest.raises(LookupError, match="Event path root .* does not match"):
            state_machine.resolve_event("/Root.global_event")

    def test_resolve_event_no_parent_relative_support(self, state_machine):
        """Test that parent-relative notation (leading .) is not supported."""
        # The leading dot should be treated as an empty part
        with pytest.raises(ValueError, match="contains empty parts"):
            state_machine.resolve_event(".Root.global_event")

    # Test edge cases
    def test_resolve_event_single_character_names(self, state_machine):
        """Test resolving events with single-character names."""
        dsl_code = """
        state R {
            event e;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        sm = parse_dsl_node_to_state_machine(ast_node)

        event = sm.resolve_event("R.e")
        assert event.name == "e"

    def test_resolve_event_numeric_names(self, state_machine):
        """Test resolving events with numeric names."""
        dsl_code = """
        state Root123 {
            event event456;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        sm = parse_dsl_node_to_state_machine(ast_node)

        event = sm.resolve_event("Root123.event456")
        assert event.name == "event456"

    def test_resolve_event_with_underscores(self, state_machine):
        """Test resolving events with underscores in names."""
        dsl_code = """
        state Root_State {
            event error_handler;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        sm = parse_dsl_node_to_state_machine(ast_node)

        event = sm.resolve_event("Root_State.error_handler")
        assert event.name == "error_handler"

    def test_resolve_event_deep_hierarchy(self, state_machine):
        """Test resolving events in a deep hierarchy."""
        dsl_code = """
        state Root {
            state L1 {
                state L2 {
                    state L3 {
                        state L4 {
                            event deep_event;
                        }
                        [*] -> L4;
                    }
                    [*] -> L3;
                }
                [*] -> L2;
            }
            [*] -> L1;
        }
        """

        ast_node = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
        sm = parse_dsl_node_to_state_machine(ast_node)

        event = sm.resolve_event("Root.L1.L2.L3.L4.deep_event")
        assert event.name == "deep_event"
        assert event.state_path == ("Root", "L1", "L2", "L3", "L4")


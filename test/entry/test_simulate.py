"""
Unit tests for the simulate entry point components.

This module tests the display, commands, batch processor, and REPL
functionality of the interactive state machine simulator.
"""

import pytest
from io import StringIO
import sys

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime
from pyfcstm.entry.simulate.display import StateDisplay
from pyfcstm.entry.simulate.commands import CommandProcessor, LogLevel, CommandResult
from pyfcstm.entry.simulate.batch import BatchProcessor


# Test DSL code
TEST_DSL = """
def int counter = 0;
def float temperature = 25.0;

state System {
    [*] -> Idle;

    state Idle;
    state Running;

    Idle -> Running :: Start;
    Running -> Idle :: Stop;
}
"""


@pytest.fixture
def runtime():
    """Create a test runtime instance."""
    ast_node = parse_with_grammar_entry(TEST_DSL, entry_name='state_machine_dsl')
    model = parse_dsl_node_to_state_machine(ast_node)
    return SimulationRuntime(model)


@pytest.fixture
def display():
    """Create a display instance without colors."""
    return StateDisplay(use_color=False)


@pytest.fixture
def command_processor(runtime):
    """Create a command processor instance."""
    return CommandProcessor(runtime, use_color=False)


@pytest.fixture
def batch_processor(runtime):
    """Create a batch processor instance."""
    return BatchProcessor(runtime, use_color=False)


class TestStateDisplay:
    """Tests for StateDisplay class."""

    def test_color_detection(self):
        """Test color support detection."""
        display = StateDisplay(use_color=True)
        # Color support depends on terminal, just check it doesn't crash
        assert isinstance(display.use_color, bool)

    def test_colorize_disabled(self, display):
        """Test colorize with colors disabled."""
        result = display._colorize("test", "blue")
        assert result == "test"

    def test_format_current_state(self, runtime, display):
        """Test formatting current state."""
        runtime.cycle()  # Move to Idle
        output = display.format_current_state(runtime)
        assert "Current State:" in output
        assert "System.Idle" in output
        assert "Variables:" in output
        assert "counter" in output
        assert "temperature" in output

    def test_format_current_state_terminated(self, display):
        """Test formatting when state machine is terminated."""
        # Create a minimal runtime with a simple state that exits
        ast_node = parse_with_grammar_entry("""
        state System {
            [*] -> Final;
            state Final;
            Final -> [*] :: Exit;
        }
        """, entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)
        runtime = SimulationRuntime(model)
        runtime.cycle()  # Move to Final
        runtime.cycle(["Exit"])  # Exit to termination

        output = display.format_current_state(runtime)
        # After exiting, current_state might be None or the parent
        assert "Current State:" in output

    def test_format_events_empty(self, display):
        """Test formatting when no events available."""
        output = display.format_events([])
        assert "No events available" in output

    def test_format_events_with_short_names(self, display):
        """Test formatting events with short names."""
        events = [
            ("System.Idle.Start", "Start"),
            ("System.Running.Stop", "Stop"),
        ]
        output = display.format_events(events)
        assert "Available Events:" in output
        assert "Start" in output
        assert "System.Idle.Start" in output

    def test_format_events_without_short_names(self, display):
        """Test formatting events without short names."""
        events = [("GlobalEvent", None)]
        output = display.format_events(events)
        assert "GlobalEvent" in output

    def test_log_output(self, display, capsys):
        """Test log output."""
        display.log("Test message", "info")
        captured = capsys.readouterr()
        assert "Test message" in captured.out


class TestCommandProcessor:
    """Tests for CommandProcessor class."""

    def test_initialization(self, command_processor):
        """Test command processor initialization."""
        assert command_processor.log_level == LogLevel.INFO
        assert command_processor.display is not None

    def test_process_empty_input(self, command_processor):
        """Test processing empty input."""
        result = command_processor.process("")
        assert result.output == ""
        assert not result.should_exit

    def test_handle_current(self, command_processor, runtime):
        """Test /current command."""
        runtime.cycle()  # Move to Idle
        result = command_processor.process("/current")
        assert "System.Idle" in result.output
        assert "counter" in result.output
        assert not result.should_exit

    def test_handle_cycle(self, command_processor, runtime):
        """Test /cycle command."""
        result = command_processor.process("/cycle")
        assert "System.Idle" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_event(self, command_processor, runtime):
        """Test /cycle command with event."""
        runtime.cycle()  # Move to Idle
        result = command_processor.process("/cycle Start")
        assert "System.Running" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_count(self, command_processor, runtime):
        """Test /cycle command with count parameter."""
        result = command_processor.process("/cycle 3")
        # Should show table format for multiple cycles
        assert "Cycle" in result.output
        assert "State" in result.output
        assert "counter" in result.output
        assert "temperature" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_count_table_format(self, command_processor, runtime):
        """Test /cycle command produces table with correct format."""
        result = command_processor.process("/cycle 5")
        # Check table structure
        lines = result.output.split('\n')
        # Should have header, separator, and 5 data rows
        assert len([l for l in lines if l.strip()]) >= 7  # header + separator + 5 rows
        assert "System.Idle" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_large_count(self, command_processor, runtime):
        """Test /cycle command with large count shows truncated table."""
        result = command_processor.process("/cycle 25")
        # Should show first 10, separator, and last 10
        assert "..." in result.output  # Separator row
        assert "Cycle" in result.output
        assert "State" in result.output
        # Count occurrences of "System.Idle" - should be 20 (10 + 10)
        assert result.output.count("System.Idle") == 20
        assert not result.should_exit

    def test_handle_cycle_with_zero_count(self, command_processor, runtime):
        """Test /cycle command with zero count."""
        result = command_processor.process("/cycle 0")
        assert "Error" in result.output
        assert "positive integer" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_negative_count(self, command_processor, runtime):
        """Test /cycle command with negative count."""
        result = command_processor.process("/cycle -5")
        assert "Error" in result.output
        assert "positive integer" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_invalid_count(self, command_processor, runtime):
        """Test /cycle command with invalid count."""
        # Non-numeric first argument should be treated as event name
        result = command_processor.process("/cycle abc")
        # This will fail because 'abc' is not a valid event
        assert "failed" in result.output.lower() or "error" in result.output.lower()
        assert not result.should_exit

    def test_handle_clear(self, command_processor, runtime):
        """Test /clear command."""
        runtime.cycle()  # Move to Idle
        runtime.cycle(["Start"])  # Move to Running
        result = command_processor.process("/clear")
        # After clear, should be back at initial state
        assert "System" in result.output
        assert not result.should_exit

    def test_handle_events(self, command_processor, runtime):
        """Test /events command."""
        runtime.cycle()  # Move to Idle
        result = command_processor.process("/events")
        assert "Start" in result.output
        assert not result.should_exit

    def test_handle_log_get(self, command_processor):
        """Test /log command without arguments."""
        result = command_processor.process("/log")
        assert "info" in result.output
        assert not result.should_exit

    def test_handle_log_set(self, command_processor):
        """Test /log command with level."""
        result = command_processor.process("/log debug")
        assert "debug" in result.output
        assert command_processor.log_level == LogLevel.DEBUG
        assert not result.should_exit

    def test_handle_log_invalid(self, command_processor):
        """Test /log command with invalid level."""
        result = command_processor.process("/log invalid")
        assert "Invalid log level" in result.output
        assert not result.should_exit

    def test_handle_help(self, command_processor):
        """Test /help command."""
        result = command_processor.process("/help")
        assert "/cycle" in result.output
        assert "/clear" in result.output
        assert "/current" in result.output
        assert not result.should_exit

    def test_handle_quit(self, command_processor):
        """Test /quit command."""
        result = command_processor.process("/quit")
        assert "Goodbye" in result.output
        assert result.should_exit

    def test_handle_exit(self, command_processor):
        """Test /exit command."""
        result = command_processor.process("/exit")
        assert "Goodbye" in result.output
        assert result.should_exit

    def test_handle_unknown_command(self, command_processor):
        """Test unknown command."""
        result = command_processor.process("/unknown")
        assert "Unknown command" in result.output
        assert not result.should_exit

    def test_handle_cycle_error(self, command_processor):
        """Test /cycle with invalid event."""
        result = command_processor.process("/cycle InvalidEvent")
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_handle_history_empty(self, command_processor):
        """Test history command with no history."""
        result = command_processor.process("/history")
        assert "No execution history available" in result.output

    def test_handle_history_default(self, command_processor):
        """Test history command with default count."""
        # Execute some cycles to generate history
        command_processor.process("/cycle 5")
        result = command_processor.process("/history")
        assert "Cycle" in result.output
        assert "State" in result.output

    def test_handle_history_with_count(self, command_processor):
        """Test history command with specific count."""
        # Execute cycles
        command_processor.process("/cycle 10")
        result = command_processor.process("/history 3")
        # Should show last 3 entries
        lines = [line for line in result.output.split('\n') if line.strip() and not line.startswith('-')]
        # Header + 3 data rows
        assert len(lines) >= 4

    def test_handle_history_all(self, command_processor):
        """Test history command with 'all' parameter."""
        command_processor.process("/cycle 5")
        result = command_processor.process("/history all")
        assert "Cycle" in result.output
        assert "State" in result.output

    def test_handle_history_invalid_count(self, command_processor):
        """Test history command with invalid count."""
        command_processor.process("/cycle 5")
        result = command_processor.process("/history invalid")
        assert "Error" in result.output

    def test_handle_history_zero_count(self, command_processor):
        """Test history command with zero count."""
        command_processor.process("/cycle 5")
        result = command_processor.process("/history 0")
        assert "Error" in result.output

    def test_handle_setting_list_all(self, command_processor):
        """Test setting command without arguments."""
        result = command_processor.process("/setting")
        assert "Current settings:" in result.output
        assert "table_max_rows" in result.output
        assert "history_size" in result.output
        assert "color" in result.output
        assert "log_level" in result.output

    def test_handle_setting_get(self, command_processor):
        """Test getting a specific setting."""
        result = command_processor.process("/setting history_size")
        assert "history_size" in result.output
        assert "100" in result.output

    def test_handle_setting_set_int(self, command_processor):
        """Test setting an integer value."""
        result = command_processor.process("/setting history_size 50")
        assert "Setting updated" in result.output
        # Verify it was set
        result = command_processor.process("/setting history_size")
        assert "50" in result.output

    def test_handle_setting_set_bool(self, command_processor):
        """Test setting a boolean value."""
        result = command_processor.process("/setting color off")
        assert "Setting updated" in result.output
        # Verify it was set
        result = command_processor.process("/setting color")
        assert "False" in result.output

    def test_handle_setting_set_log_level(self, command_processor):
        """Test setting log level."""
        result = command_processor.process("/setting log_level debug")
        assert "Setting updated" in result.output
        # Verify it was set
        result = command_processor.process("/setting log_level")
        assert "debug" in result.output

    def test_handle_setting_invalid_key(self, command_processor):
        """Test setting with invalid key."""
        result = command_processor.process("/setting invalid_key 123")
        assert "Error" in result.output

    def test_handle_setting_invalid_value(self, command_processor):
        """Test setting with invalid value."""
        result = command_processor.process("/setting history_size invalid")
        assert "Error" in result.output

    def test_handle_setting_history_size_trim(self, command_processor):
        """Test that changing history_size trims existing history."""
        # Generate history
        command_processor.process("/cycle 10")
        # Set smaller history size
        command_processor.process("/setting history_size 3")
        # Check history is trimmed
        result = command_processor.process("/history")
        lines = [line for line in result.output.split('\n') if line.strip() and not line.startswith('-')]
        # Header + 3 data rows
        assert len(lines) == 4
        assert not result.should_exit


class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_initialization(self, batch_processor):
        """Test batch processor initialization."""
        assert batch_processor.command_processor is not None

    def test_execute_single_command(self, batch_processor):
        """Test executing single command."""
        result = batch_processor.execute_commands("current")
        assert "System" in result
        assert "counter" in result

    def test_execute_multiple_commands(self, batch_processor, runtime):
        """Test executing multiple commands."""
        result = batch_processor.execute_commands("cycle; current")
        assert "System.Idle" in result

    def test_execute_with_slash_prefix(self, batch_processor):
        """Test commands with explicit / prefix."""
        result = batch_processor.execute_commands("/current")
        assert "System" in result

    def test_execute_mixed_prefix(self, batch_processor):
        """Test mixed commands with and without prefix."""
        result = batch_processor.execute_commands("current; /current")
        # Should have two outputs
        assert result.count("System") >= 2

    def test_execute_with_exit(self, batch_processor):
        """Test batch execution stops on exit."""
        result = batch_processor.execute_commands("current; quit; current")
        # Should only have one current output before quit
        assert result.count("System") == 1
        assert "Goodbye" in result

    def test_execute_empty_commands(self, batch_processor):
        """Test executing empty command string."""
        result = batch_processor.execute_commands("")
        assert result == ""

    def test_execute_with_whitespace(self, batch_processor):
        """Test commands with extra whitespace."""
        result = batch_processor.execute_commands("  current  ;  current  ")
        assert "System" in result


class TestIntegration:
    """Integration tests for the simulate entry point."""

    def test_full_workflow(self, runtime):
        """Test a complete simulation workflow."""
        # Initial state
        assert runtime.current_state is not None

        # Execute first cycle
        runtime.cycle()
        assert '.'.join(runtime.current_state.path) == "System.Idle"

        # Trigger event
        runtime.cycle(["Start"])
        assert '.'.join(runtime.current_state.path) == "System.Running"

        # Trigger another event
        runtime.cycle(["Stop"])
        assert '.'.join(runtime.current_state.path) == "System.Idle"

    def test_batch_workflow(self, batch_processor):
        """Test batch command workflow."""
        commands = "cycle; current; cycle Start; current; cycle Stop; current"
        result = batch_processor.execute_commands(commands)

        # Each command produces output, cycle also shows current state
        assert "System.Idle" in result
        assert "System.Running" in result

    def test_command_processor_workflow(self, command_processor, runtime):
        """Test command processor workflow."""
        # Start
        result = command_processor.process("/cycle")
        assert "System.Idle" in result.output

        # Check events
        result = command_processor.process("/events")
        assert "Start" in result.output

        # Trigger event
        result = command_processor.process("/cycle Start")
        assert "System.Running" in result.output

        # Clear
        result = command_processor.process("/clear")
        assert "System" in result.output

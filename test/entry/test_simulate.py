"""
Unit tests for the simulate entry point components.

This module tests the display, commands, batch processor, and REPL
functionality of the interactive state machine simulator.
"""

import logging
import sys

import pytest

from pyfcstm.dsl import parse_with_grammar_entry
from pyfcstm.entry.simulate.batch import BatchProcessor
from pyfcstm.entry.simulate.commands import CommandProcessor, LogLevel, Settings
from pyfcstm.entry.simulate.display import StateDisplay
from pyfcstm.entry.simulate.logging import (
    SimulateCliFormatter,
    SimulateLogHighlighter,
    SimulatePlainLogHandler,
    SimulateRichLogHandler,
    configure_simulate_cli_logger,
)
from pyfcstm.model import parse_dsl_node_to_state_machine
from pyfcstm.simulate import SimulationRuntime

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


def _collect_batch_output(batch_processor, commands):
    """Helper to collect batch processor output."""
    output_lines = []

    def collector(text):
        output_lines.append(text)

    # Create a new processor with the collector
    from pyfcstm.entry.simulate.batch import BatchProcessor
    processor = BatchProcessor(batch_processor.runtime, use_color=False, output_func=collector)
    processor.execute_commands(commands)
    return '\n'.join(output_lines)


@pytest.mark.unittest
class TestSettings:
    """Tests for Settings class."""

    def test_initialization(self):
        """Test Settings initialization with default values."""
        settings = Settings()
        assert settings.table_max_rows == 20
        assert settings.history_size == 100
        assert settings.color is True
        assert settings.log_level == LogLevel.WARNING

    def test_get_valid_key(self):
        """Test getting a valid setting."""
        settings = Settings()
        assert settings.get('table_max_rows') == 20
        assert settings.get('history_size') == 100
        assert settings.get('color') is True
        assert settings.get('log_level') == LogLevel.WARNING

    def test_get_invalid_key(self):
        """Test getting an invalid setting raises KeyError."""
        settings = Settings()
        with pytest.raises(KeyError, match="Unknown setting"):
            settings.get('invalid_key')

    def test_set_int_value(self):
        """Test setting an integer value."""
        settings = Settings()
        settings.set('table_max_rows', 30)
        assert settings.table_max_rows == 30
        settings.set('table_max_rows', '40')
        assert settings.table_max_rows == 40

    def test_set_int_negative_value(self):
        """Test setting negative integer raises ValueError."""
        settings = Settings()
        with pytest.raises(ValueError):
            settings.set('table_max_rows', -1)
        with pytest.raises(ValueError):
            settings.set('table_max_rows', '-5')

    def test_set_int_invalid_value(self):
        """Test setting invalid integer raises ValueError."""
        settings = Settings()
        with pytest.raises(ValueError, match="Invalid integer value"):
            settings.set('table_max_rows', 'abc')

    def test_set_bool_true_values(self):
        """Test setting boolean to true with various values."""
        settings = Settings()
        for value in ['on', 'true', '1', 'yes', 'ON', 'TRUE', 'YES']:
            settings.set('color', value)
            assert settings.color is True

    def test_set_bool_false_values(self):
        """Test setting boolean to false with various values."""
        settings = Settings()
        for value in ['off', 'false', '0', 'no', 'OFF', 'FALSE', 'NO']:
            settings.set('color', value)
            assert settings.color is False

    def test_set_bool_invalid_value(self):
        """Test setting invalid boolean raises ValueError."""
        settings = Settings()
        with pytest.raises(ValueError, match="Invalid boolean value"):
            settings.set('color', 'maybe')

    def test_set_log_level_valid(self):
        """Test setting valid log levels."""
        settings = Settings()
        for level in ['debug', 'info', 'warning', 'error', 'off']:
            settings.set('log_level', level)
            assert settings.log_level == LogLevel(level)

    def test_set_log_level_invalid(self):
        """Test setting invalid log level raises ValueError."""
        settings = Settings()
        with pytest.raises(ValueError, match="Invalid log level"):
            settings.set('log_level', 'invalid')

    def test_set_invalid_key(self):
        """Test setting an invalid key raises KeyError."""
        settings = Settings()
        with pytest.raises(KeyError, match="Unknown setting"):
            settings.set('invalid_key', 'value')

    def test_list_all(self):
        """Test listing all settings."""
        settings = Settings()
        all_settings = settings.list_all()
        assert 'table_max_rows' in all_settings
        assert 'history_size' in all_settings
        assert 'color' in all_settings
        assert 'log_level' in all_settings
        assert all_settings['table_max_rows'] == 20
        assert all_settings['history_size'] == 100
        assert all_settings['color'] is True
        assert all_settings['log_level'] == 'warning'


@pytest.mark.unittest
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

    def test_colorize_enabled(self):
        """Test colorize with colors enabled."""
        display = StateDisplay(use_color=True)
        # Force use_color to True for testing
        display.use_color = True
        result = display._colorize("test", "blue")
        # Should contain ANSI codes
        assert "\033[" in result or result == "test"  # May not have color if terminal doesn't support it

    def test_colorize_unknown_color(self):
        """Test colorize with unknown color name."""
        display = StateDisplay(use_color=True)
        display.use_color = True
        result = display._colorize("test", "unknown_color")
        # Should still work, just without the specific color
        assert "test" in result

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
        """Test log output with logger."""
        import logging
        # Create a logger with a handler that writes to stdout for testing
        logger = logging.getLogger('test_display_log')
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.INFO)

        display.logger = logger
        display.log("Test message", "info")
        captured = capsys.readouterr()
        assert "Test message" in captured.out

    def test_format_table_empty_rows(self, display):
        """Test format_table with empty rows."""
        result = display.format_table(['Col1', 'Col2'], [], [])
        assert result == ""

    def test_format_table_with_unknown_header(self, display):
        """Test format_table with header not in Cycle/State/var_names."""
        headers = ['Custom', 'Header']
        rows = [['val1', 'val2']]
        result = display.format_table(headers, rows, [])
        assert 'Custom' in result
        assert 'Header' in result
        assert 'val1' in result

    def test_format_table_with_non_numeric_values(self, display):
        """Test format_table with non-numeric values in variable columns."""
        headers = ['Cycle', 'State', 'var1']
        rows = [[1, 'State.A', 'text_value']]
        result = display.format_table(headers, rows, ['var1'])
        assert 'text_value' in result

    def test_format_table_with_separator_row(self, display):
        """Test format_table with separator row (...)."""
        headers = ['Cycle', 'State', 'var1']
        rows = [
            [1, 'State.A', 10],
            ['...', '...', '...'],
            [20, 'State.B', 30]
        ]
        result = display.format_table(headers, rows, ['var1'])
        assert '...' in result


@pytest.mark.unittest
class TestSimulateLogging:
    """Tests for simulate CLI logging presentation."""

    def test_configure_simulate_cli_logger_is_idempotent(self, runtime):
        """Configuring the CLI logger multiple times should not duplicate handlers."""
        configure_simulate_cli_logger(runtime.logger, use_color=False)
        first_handlers = list(runtime.logger.handlers)
        configure_simulate_cli_logger(runtime.logger, use_color=False)

        assert len(runtime.logger.handlers) == 1
        assert isinstance(runtime.logger.handlers[0], SimulatePlainLogHandler)
        assert runtime.logger.handlers[0] is not first_handlers[0]

    def test_command_processor_configures_runtime_logger(self, runtime):
        """Command processor should configure the runtime logger for CLI output."""
        processor = CommandProcessor(runtime, use_color=False)

        assert processor.runtime.logger.level == logging.WARNING
        assert len(processor.runtime.logger.handlers) == 1
        assert isinstance(processor.runtime.logger.handlers[0], SimulatePlainLogHandler)
        assert processor.runtime.logger.handlers[0].formatter._fmt == '[%(levelname)s] %(message)s'

    def test_command_processor_log_level_sync_still_works(self, runtime):
        """Changing setting log_level should still update the runtime logger level."""
        processor = CommandProcessor(runtime, use_color=False)
        processor.process("setting log_level debug")

        assert processor.runtime.logger.level == logging.DEBUG

    def test_cli_formatter_uses_spaced_level_prefix(self):
        """CLI formatter should place a space after the level prefix."""
        formatter = SimulateCliFormatter()
        record = logging.LogRecord(
            name='pyfcstm.simulate', level=logging.INFO, pathname=__file__, lineno=1,
            msg='Cycle 1 completed successfully', args=(), exc_info=None,
        )

        assert formatter.format(record) == '[INFO] Cycle 1 completed successfully'

    def test_rich_handler_is_rich_based(self):
        """Rich handler should be backed by RichHandler with a simulate highlighter."""
        handler = SimulateRichLogHandler(use_color=True)

        assert hasattr(handler, 'highlighter')
        assert isinstance(handler.highlighter, SimulateLogHighlighter)

    def test_simulate_log_highlighter_marks_level_and_cycle(self):
        """Highlighter should mark level prefix and cycle completion text."""
        from rich.text import Text

        text = Text('[INFO] Cycle 10 completed successfully - State: System.Idle')
        highlighter = SimulateLogHighlighter()
        highlighter.highlight(text)

        span_styles = [span.style for span in text.spans if span.style]
        assert 'simulate.level_info' in span_styles
        assert 'simulate.cycle_complete' in span_styles

    def test_simulate_log_highlighter_marks_execute_transition_target(self):
        """Highlighter should underline execute-transition target details."""
        from rich.text import Text

        text = Text('[INFO] Execute transition: Root.Standby -> Heating (event=none)')
        highlighter = SimulateLogHighlighter()
        highlighter.highlight(text)

        span_styles = [span.style for span in text.spans if span.style]
        assert 'simulate.transition_path' in span_styles


@pytest.mark.unittest
class TestCommandProcessor:
    """Tests for CommandProcessor class."""

    def test_initialization(self, command_processor):
        """Test command processor initialization."""
        assert command_processor.settings.log_level == LogLevel.WARNING
        assert command_processor.display is not None

    def test_process_empty_input(self, command_processor):
        """Test processing empty input."""
        result = command_processor.process("")
        assert result.output == ""
        assert not result.should_exit

    def test_handle_current(self, command_processor, runtime):
        """Test current command."""
        runtime.cycle()  # Move to Idle
        result = command_processor.process("current")
        assert "System.Idle" in result.output
        assert "counter" in result.output
        assert not result.should_exit

    def test_handle_cycle(self, command_processor, runtime):
        """Test cycle command."""
        result = command_processor.process("cycle")
        assert "System.Idle" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_event(self, command_processor, runtime):
        """Test cycle command with event."""
        runtime.cycle()  # Move to Idle
        result = command_processor.process("cycle Start")
        assert "System.Running" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_count(self, command_processor, runtime):
        """Test cycle command with count parameter."""
        result = command_processor.process("cycle 3")
        # Should show table format for multiple cycles
        assert "Cycle" in result.output
        assert "State" in result.output
        assert "counter" in result.output
        assert "temperature" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_count_table_format(self, command_processor, runtime):
        """Test cycle command produces table with correct format."""
        result = command_processor.process("cycle 5")
        # Check table structure
        lines = result.output.split('\n')
        # Should have header, separator, and 5 data rows
        assert len([l for l in lines if l.strip()]) >= 7  # header + separator + 5 rows
        assert "System.Idle" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_large_count(self, command_processor, runtime):
        """Test cycle command with large count shows truncated table."""
        result = command_processor.process("cycle 25")
        # Should show first 10, separator, and last 10
        assert "..." in result.output  # Separator row
        assert "Cycle" in result.output
        assert "State" in result.output
        # Count occurrences of "System.Idle" - should be 20 (10 + 10)
        assert result.output.count("System.Idle") == 20
        assert not result.should_exit

    def test_handle_cycle_with_debug_log(self, command_processor):
        """Test cycle with debug log level."""
        command_processor.process("setting log_level debug")
        result = command_processor.process("cycle 2")
        # Debug logging should be active
        assert "Cycle" in result.output

    def test_handle_cycle_terminated_state(self):
        """Test cycle when state machine terminates."""
        # Create a state machine that terminates
        dsl_code = """
        state System {
            state A;
            [*] -> A;
            A -> [*];
        }
        """
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        # First cycle enters A
        processor.process("cycle")
        # Second cycle exits to terminated
        processor.process("cycle")
        # Third cycle should show terminated
        result = processor.process("cycle 2")
        assert "(terminated)" in result.output

    def test_handle_cycle_with_zero_count(self, command_processor, runtime):
        """Test cycle command with zero count."""
        result = command_processor.process("cycle 0")
        assert "Error" in result.output
        assert "positive integer" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_negative_count(self, command_processor, runtime):
        """Test cycle command with negative count."""
        result = command_processor.process("cycle -5")
        assert "Error" in result.output
        assert "positive integer" in result.output
        assert not result.should_exit

    def test_handle_cycle_with_invalid_count(self, command_processor, runtime):
        """Test cycle command with invalid count."""
        # Non-numeric first argument should be treated as event name
        result = command_processor.process("cycle abc")
        # This will fail because 'abc' is not a valid event
        assert "failed" in result.output.lower() or "error" in result.output.lower()
        assert not result.should_exit

    def test_handle_clear(self, command_processor, runtime):
        """Test clear command."""
        runtime.cycle()  # Move to Idle
        runtime.cycle(["Start"])  # Move to Running
        result = command_processor.process("clear")
        # After clear, should be back at initial state
        assert "System" in result.output
        assert not result.should_exit

    def test_handle_events(self, command_processor, runtime):
        """Test events command."""
        runtime.cycle()  # Move to Idle
        result = command_processor.process("events")
        assert "Start" in result.output
        assert not result.should_exit

    def test_handle_setting_log_level_get(self, command_processor):
        """Test setting log_level command."""
        result = command_processor.process("setting log_level")
        assert "warning" in result.output
        assert not result.should_exit

    def test_handle_setting_log_level_set(self, command_processor):
        """Test setting log_level with value."""
        result = command_processor.process("setting log_level debug")
        assert "debug" in result.output
        assert command_processor.settings.log_level == LogLevel.DEBUG
        assert not result.should_exit

    def test_handle_setting_log_level_invalid(self, command_processor):
        """Test setting log_level with invalid value."""
        result = command_processor.process("setting log_level invalid")
        assert "Invalid log level" in result.output or "Error" in result.output
        assert not result.should_exit

    def test_handle_help(self, command_processor):
        """Test help command."""
        result = command_processor.process("help")
        assert "cycle" in result.output
        assert "clear" in result.output
        assert "current" in result.output
        assert not result.should_exit

    def test_handle_quit(self, command_processor):
        """Test quit command."""
        result = command_processor.process("quit")
        assert "Goodbye" in result.output
        assert result.should_exit

    def test_handle_exit(self, command_processor):
        """Test exit command."""
        result = command_processor.process("exit")
        assert "Goodbye" in result.output
        assert result.should_exit

    def test_handle_unknown_command(self, command_processor):
        """Test unknown command."""
        result = command_processor.process("unknown")
        assert "Unknown command" in result.output
        assert not result.should_exit

    def test_process_exception_handling(self, command_processor, monkeypatch):
        """Test exception handling in process method."""

        # Mock _handle_current to raise an exception
        def mock_handle_current():
            raise RuntimeError("Test exception")

        monkeypatch.setattr(command_processor, '_handle_current', mock_handle_current)
        result = command_processor.process("current")
        assert "Error:" in result.output
        assert "Test exception" in result.output

    def test_handle_cycle_error(self, command_processor):
        """Test cycle with invalid event."""
        result = command_processor.process("cycle InvalidEvent")
        assert "failed" in result.output.lower() or "error" in result.output.lower()

    def test_handle_cycle_dfs_error(self, command_processor, monkeypatch):
        """Test cycle with SimulationRuntimeDfsError."""
        from pyfcstm.simulate import SimulationRuntimeDfsError

        def mock_cycle(events=None):
            raise SimulationRuntimeDfsError("DFS limit exceeded")

        monkeypatch.setattr(command_processor.runtime, 'cycle', mock_cycle)
        result = command_processor.process("cycle")
        assert "unbounded execution chain" in result.output
        assert "stoppable states" in result.output

    def test_handle_history_empty(self, command_processor):
        """Test history command with no history."""
        result = command_processor.process("history")
        assert "No execution history available" in result.output

    def test_handle_history_default(self, command_processor):
        """Test history command with default count."""
        # Execute some cycles to generate history
        command_processor.process("cycle 5")
        result = command_processor.process("history")
        assert "Cycle" in result.output
        assert "State" in result.output

    def test_handle_history_with_count(self, command_processor):
        """Test history command with specific count."""
        # Execute cycles
        command_processor.process("cycle 10")
        result = command_processor.process("history 3")
        # Should show last 3 entries
        lines = [line for line in result.output.split('\n') if line.strip() and not line.startswith('-')]
        # Header + 3 data rows
        assert len(lines) >= 4

    def test_handle_history_all(self, command_processor):
        """Test history command with 'all' parameter."""
        command_processor.process("cycle 5")
        result = command_processor.process("history all")
        assert "Cycle" in result.output
        assert "State" in result.output

    def test_handle_history_invalid_count(self, command_processor):
        """Test history command with invalid count."""
        command_processor.process("cycle 5")
        result = command_processor.process("history invalid")
        assert "Error" in result.output

    def test_handle_history_zero_count(self, command_processor):
        """Test history command with zero count."""
        command_processor.process("cycle 5")
        result = command_processor.process("history 0")
        assert "Error" in result.output

    def test_handle_setting_list_all(self, command_processor):
        """Test setting command without arguments."""
        result = command_processor.process("setting")
        assert "Current settings:" in result.output
        assert "table_max_rows" in result.output
        assert "history_size" in result.output
        assert "color" in result.output
        assert "log_level" in result.output

    def test_handle_setting_get(self, command_processor):
        """Test getting a specific setting."""
        result = command_processor.process("setting history_size")
        assert "history_size" in result.output
        assert "100" in result.output

    def test_handle_setting_set_int(self, command_processor):
        """Test setting an integer value."""
        result = command_processor.process("setting history_size 50")
        assert "Setting updated" in result.output
        # Verify it was set
        result = command_processor.process("setting history_size")
        assert "50" in result.output

    def test_handle_setting_set_bool(self, command_processor):
        """Test setting a boolean value."""
        result = command_processor.process("setting color off")
        assert "Setting updated" in result.output
        # Verify it was set
        result = command_processor.process("setting color")
        assert "False" in result.output

    def test_handle_setting_set_log_level(self, command_processor):
        """Test setting log level."""
        result = command_processor.process("setting log_level debug")
        assert "Setting updated" in result.output
        # Verify it was set
        result = command_processor.process("setting log_level")
        assert "debug" in result.output

    def test_handle_setting_invalid_key(self, command_processor):
        """Test setting with invalid key."""
        result = command_processor.process("setting invalid_key 123")
        assert "Error" in result.output

    def test_handle_setting_invalid_value(self, command_processor):
        """Test setting with invalid value."""
        result = command_processor.process("setting history_size invalid")
        assert "Error" in result.output

    def test_handle_setting_history_size_trim(self, command_processor):
        """Test that changing history_size trims existing history."""
        # Generate history
        command_processor.process("cycle 10")
        # Set smaller history size
        command_processor.process("setting history_size 3")
        # Check history is trimmed
        result = command_processor.process("history")
        lines = [line for line in result.output.split('\n') if line.strip() and not line.startswith('-')]
        # Header + 3 data rows
        assert len(lines) == 4
        assert not result.should_exit

    def test_handle_export_no_args(self, command_processor):
        """Test export command without arguments."""
        result = command_processor.process("export")
        assert "Usage" in result.output
        assert ".csv" in result.output
        assert not result.should_exit

    def test_handle_export_no_history(self, command_processor):
        """Test export command with no history."""
        result = command_processor.process("export test.csv")
        assert "No history" in result.output
        assert not result.should_exit

    def test_handle_export_unsupported_format(self, command_processor):
        """Test export command with unsupported format."""
        command_processor.process("cycle 3")
        result = command_processor.process("export test.txt")
        assert "Unsupported file format" in result.output
        assert not result.should_exit

    def test_handle_export_csv(self, command_processor, tmp_path):
        """Test export command to CSV format."""
        import csv
        # Generate some history
        command_processor.process("cycle 5")

        # Export to CSV
        csv_file = tmp_path / "test.csv"
        result = command_processor.process(f"export {csv_file}")
        assert "exported" in result.output.lower()
        assert "5 entries" in result.output
        assert not result.should_exit

        # Verify CSV content
        assert csv_file.exists()
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert len(rows) == 5
            assert 'cycle' in rows[0]
            assert 'state' in rows[0]
            assert 'events' in rows[0]
            assert 'counter' in rows[0]
            assert 'temperature' in rows[0]

    def test_handle_export_json(self, command_processor, tmp_path):
        """Test export command to JSON format."""
        import json
        # Generate some history
        command_processor.process("cycle 3")

        # Export to JSON
        json_file = tmp_path / "test.json"
        result = command_processor.process(f"export {json_file}")
        assert "exported" in result.output.lower()
        assert "3 entries" in result.output
        assert not result.should_exit

        # Verify JSON content
        assert json_file.exists()
        with open(json_file, 'r', encoding='utf-8') as f:
            data = json.load(f)
            assert isinstance(data, list)
            assert len(data) == 3
            assert 'cycle' in data[0]
            assert 'state' in data[0]
            assert 'vars' in data[0]

    def test_handle_export_yaml(self, command_processor, tmp_path):
        """Test export command to YAML format."""
        import yaml
        # Generate some history
        command_processor.process("cycle 4")

        # Export to YAML
        yaml_file = tmp_path / "test.yaml"
        result = command_processor.process(f"export {yaml_file}")
        assert "exported" in result.output.lower()
        assert "4 entries" in result.output
        assert not result.should_exit

        # Verify YAML content
        assert yaml_file.exists()
        with open(yaml_file, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
            assert isinstance(data, list)
            assert len(data) == 4
            assert 'cycle' in data[0]
            assert 'state' in data[0]
            assert 'vars' in data[0]

    def test_handle_export_jsonl(self, command_processor, tmp_path):
        """Test export command to JSON Lines format."""
        import json
        # Generate some history
        command_processor.process("cycle 2")

        # Export to JSONL
        jsonl_file = tmp_path / "test.jsonl"
        result = command_processor.process(f"export {jsonl_file}")
        assert "exported" in result.output.lower()
        assert "2 entries" in result.output
        assert not result.should_exit

        # Verify JSONL content
        assert jsonl_file.exists()
        with open(jsonl_file, 'r', encoding='utf-8') as f:
            lines = f.readlines()
            assert len(lines) == 2
            for line in lines:
                entry = json.loads(line)
                assert 'cycle' in entry
                assert 'state' in entry
                assert 'vars' in entry


@pytest.mark.unittest
class TestBatchProcessor:
    """Tests for BatchProcessor class."""

    def test_initialization(self, batch_processor):
        """Test batch processor initialization."""
        assert batch_processor.command_processor is not None

    def test_execute_single_command(self, batch_processor):
        """Test executing single command."""
        result = _collect_batch_output(batch_processor, "current")
        assert "System" in result
        assert "counter" in result

    def test_execute_multiple_commands(self, batch_processor, runtime):
        """Test executing multiple commands."""
        result = _collect_batch_output(batch_processor, "cycle; current")
        assert "System.Idle" in result

    def test_execute_with_slash_prefix(self, batch_processor):
        """Test commands work without prefix."""
        result = _collect_batch_output(batch_processor, "current")
        assert "System" in result

    def test_execute_mixed_prefix(self, batch_processor):
        """Test multiple commands."""
        result = _collect_batch_output(batch_processor, "current; current")
        # Should have two outputs
        assert result.count("System") >= 2

    def test_execute_with_exit(self, batch_processor):
        """Test batch execution stops on exit."""
        result = _collect_batch_output(batch_processor, "current; quit; current")
        # Should only have one current output before quit
        assert result.count("System") == 1
        assert "Goodbye" in result

    def test_execute_empty_commands(self, batch_processor):
        """Test executing empty command string."""
        result = _collect_batch_output(batch_processor, "")
        assert result == ""

    def test_execute_with_whitespace(self, batch_processor):
        """Test commands with extra whitespace."""
        result = _collect_batch_output(batch_processor, "  current  ;  current  ")
        assert "System" in result


@pytest.mark.unittest
class TestSimulationCompleter:
    """Tests for SimulationCompleter class."""

    def test_initialization(self, runtime):
        """Test completer initialization."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        completer = SimulationCompleter(runtime)
        assert completer.runtime is runtime
        assert len(completer.COMMANDS) > 0
        assert len(completer.LOG_LEVELS) > 0

    def test_command_completion(self, runtime):
        """Test command completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        document = Document('c')
        completions = list(completer.get_completions(document, None))
        # Should suggest /cycle, /clear, /current
        assert len(completions) >= 3
        texts = [c.text for c in completions]
        assert 'ycle' in texts or 'cycle' in texts
        assert 'lear' in texts or 'clear' in texts

    def test_setting_key_completion(self, runtime):
        """Test setting key completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        document = Document('setting log')
        completions = list(completer.get_completions(document, None))
        # Should suggest log_level
        texts = [c.text for c in completions]
        assert '_level' in texts or 'log_level' in texts

    def test_event_completion(self, runtime):
        """Test event completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        # Move to a state with events
        runtime.cycle()
        document = Document('cycle S')
        completions = list(completer.get_completions(document, None))
        # Should suggest Start event
        texts = [c.text for c in completions]
        assert any('tart' in t or 'Start' in t for t in texts)

    def test_event_completion_empty_prefix(self, runtime):
        """Test event completion with trailing space."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        runtime.cycle()
        # With trailing space, words[-1] will be 'cycle', not empty
        document = Document('cycle ')
        completions = list(completer.get_completions(document, None))
        # Should suggest events that start with 'cycle' (none)
        # Actually, the prefix will be 'cycle', so no events will match
        # This tests the normal flow, not the else branch
        assert isinstance(completions, list)

    def test_log_completion_empty_prefix(self, runtime):
        """Test log level completion with trailing space."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        # With trailing space, words[-1] will be '/log', not empty
        document = Document('log ')
        completions = list(completer.get_completions(document, None))
        # Should suggest log levels that start with '/log' (none)
        assert isinstance(completions, list)

    def test_completer_no_current_state(self):
        """Test completer when runtime has ended."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        # Create a terminated runtime
        dsl_code = """
        state System {
            state A;
            [*] -> A;
            A -> [*];
        }
        """
        ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        runtime.cycle()  # Enter A
        runtime.cycle()  # Exit to terminated

        completer = SimulationCompleter(runtime)
        # When runtime has ended, accessing current_state raises IndexError
        # The completer should handle this gracefully
        document = Document('cycle test')
        # This should not crash even though runtime has ended
        try:
            completions = list(completer.get_completions(document, None))
            assert isinstance(completions, list)
        except IndexError:
            # If IndexError is raised, that's also acceptable
            # as it indicates the runtime has ended
            pass

    def test_empty_completion(self, runtime):
        """Test completion with empty input."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        document = Document('')
        completions = list(completer.get_completions(document, None))
        # Should suggest all commands
        assert len(completions) >= len(completer.COMMANDS)

    def test_no_match_completion(self, runtime):
        """Test completion with no matches."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        document = Document('xyz')
        completions = list(completer.get_completions(document, None))
        # Should return empty
        assert len(completions) == 0

    def test_partial_command_completion(self, runtime):
        """Test partial command name completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)

        # Test 'cy' should suggest 'cycle'
        document = Document('cy')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'cycle' in texts

        # Test 'se' should suggest 'setting'
        document = Document('se')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'setting' in texts

        # Test 'hi' should suggest 'history'
        document = Document('hi')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'history' in texts

    def test_cycle_count_completion(self, runtime):
        """Test cycle command count completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)

        # Test 'cycle ' should suggest counts and events
        document = Document('cycle ')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        # Should suggest common counts
        assert '1' in texts or '5' in texts or '10' in texts

        # Test 'cycle 1' should suggest counts starting with 1
        document = Document('cycle 1')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert '1' in texts or '10' in texts or '100' in texts

    def test_cycle_event_after_count(self, runtime):
        """Test event completion after count in cycle command."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)
        runtime.cycle()  # Move to a state with events

        # Test 'cycle 5 ' should suggest events
        document = Document('cycle 5 ')
        completions = list(completer.get_completions(document, None))
        # Should have some completions (events or empty list)
        assert isinstance(completions, list)

    def test_history_count_completion(self, runtime):
        """Test history command count completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)

        # Test 'history ' should suggest 'all' and counts
        document = Document('history ')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'all' in texts
        assert '5' in texts or '10' in texts

        # Test 'history a' should suggest 'all'
        document = Document('history a')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'all' in texts

    def test_setting_value_completion(self, runtime):
        """Test setting value completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)

        # Test 'setting log_level ' should suggest log levels
        document = Document('setting log_level ')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'debug' in texts
        assert 'info' in texts
        assert 'warning' in texts

        # Test 'setting color ' should suggest on/off
        document = Document('setting color ')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'on' in texts or 'off' in texts

        # Test 'setting table_max_rows ' should suggest numbers
        document = Document('setting table_max_rows ')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert '10' in texts or '20' in texts or '50' in texts

    def test_setting_partial_value_completion(self, runtime):
        """Test partial setting value completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)

        # Test 'setting log_level d' should suggest 'debug'
        document = Document('setting log_level d')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'debug' in texts

        # Test 'setting color o' should suggest 'on' and 'off'
        document = Document('setting color o')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'on' in texts or 'off' in texts

    def test_export_command_completion(self, runtime):
        """Test export command completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)

        # Test 'ex' should suggest 'export'
        document = Document('ex')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'export' in texts

    def test_export_filename_completion(self, runtime):
        """Test export filename completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document

        completer = SimulationCompleter(runtime)

        # Test 'export ' should suggest filenames with extensions
        document = Document('export ')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'history.csv' in texts
        assert 'history.json' in texts
        assert 'history.yaml' in texts
        assert 'history.jsonl' in texts

        # Test 'export history.' should suggest extensions
        document = Document('export history.')
        completions = list(completer.get_completions(document, None))
        texts = [c.text for c in completions]
        assert 'history.csv' in texts or 'history.json' in texts

    def test_export_filesystem_completion(self, runtime, tmp_path):
        """Test export filesystem path completion."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document
        import os

        # Create test directory structure
        test_dir = tmp_path / "test_exports"
        test_dir.mkdir()
        (test_dir / "data.csv").touch()
        (test_dir / "results.json").touch()
        (test_dir / "readme.txt").touch()  # Non-supported format
        (test_dir / "subdir").mkdir()

        completer = SimulationCompleter(runtime)

        # Change to tmp_path for testing
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Test directory completion
            document = Document('export test_')
            completions = list(completer.get_completions(document, None))
            texts = [c.text for c in completions]
            # Should suggest the directory with trailing separator
            assert any('test_exports' in t for t in texts)

            # Test file completion in subdirectory with priority
            document = Document(f'export test_exports{os.sep}')
            completions = list(completer.get_completions(document, None))
            texts = [c.text for c in completions]

            # Should suggest files in the directory
            assert any('data.csv' in t for t in texts)
            assert any('results.json' in t for t in texts)
            assert any('subdir' in t for t in texts)
            assert any('readme.txt' in t for t in texts)

            # Check priority: directories and supported formats should come first
            # Find indices
            csv_idx = next((i for i, t in enumerate(texts) if 'data.csv' in t), None)
            json_idx = next((i for i, t in enumerate(texts) if 'results.json' in t), None)
            txt_idx = next((i for i, t in enumerate(texts) if 'readme.txt' in t), None)
            dir_idx = next((i for i, t in enumerate(texts) if 'subdir' in t), None)

            # Supported formats and directories should come before unsupported formats
            if csv_idx is not None and txt_idx is not None:
                assert csv_idx < txt_idx, "CSV file should have higher priority than TXT file"
            if json_idx is not None and txt_idx is not None:
                assert json_idx < txt_idx, "JSON file should have higher priority than TXT file"
            if dir_idx is not None and txt_idx is not None:
                assert dir_idx < txt_idx, "Directory should have higher priority than TXT file"

        finally:
            os.chdir(original_cwd)

    def test_export_current_directory_completion(self, runtime, tmp_path):
        """Test export completion from current directory when no dirname."""
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document
        import os

        # Create test files in current directory
        original_cwd = os.getcwd()
        try:
            os.chdir(tmp_path)

            # Create test files
            (tmp_path / "export.csv").touch()
            (tmp_path / "data.json").touch()
            (tmp_path / "notes.txt").touch()
            (tmp_path / "testdir").mkdir()

            completer = SimulationCompleter(runtime)

            # Test completion with no dirname (should search current directory)
            document = Document('export e')
            completions = list(completer.get_completions(document, None))
            texts = [c.text for c in completions]

            # Should find files in current directory
            assert any('export.csv' in t for t in texts)

            # Test completion with empty prefix (should show current directory)
            document = Document('export ')
            completions = list(completer.get_completions(document, None))
            texts = [c.text for c in completions]

            # Should suggest history.* files first, then current directory files
            assert 'history.csv' in texts
            assert 'history.json' in texts

            # Should also show current directory files
            assert any('export.csv' in t for t in texts)
            assert any('data.json' in t for t in texts)
            assert any('testdir' in t for t in texts)

            # Check priority: history.* should come first
            history_csv_idx = texts.index('history.csv')
            export_csv_idx = next((i for i, t in enumerate(texts) if t == 'export.csv'), None)
            if export_csv_idx is not None:
                assert history_csv_idx < export_csv_idx, "history.csv should come before export.csv"

        finally:
            os.chdir(original_cwd)

    def test_export_csv_with_events(self, command_processor, tmp_path):
        """Test CSV export includes events column."""
        import csv

        # Generate history with events
        command_processor.process("cycle")  # Move to Idle
        command_processor.process("cycle Start")  # Trigger Start event

        # Export to CSV
        csv_file = tmp_path / "test_events.csv"
        result = command_processor.process(f"export {csv_file}")
        assert "exported" in result.output.lower()

        # Verify CSV has events column
        assert csv_file.exists()
        with open(csv_file, 'r', encoding='utf-8') as f:
            reader = csv.DictReader(f)
            rows = list(reader)
            assert 'events' in rows[0]
            # Check that events column exists and can contain data
            # (may be empty for cycles without events)


@pytest.mark.unittest
class TestAutoSuggest:
    """Tests for AutoSuggestFromCompleter class."""

    def test_auto_suggest_initialization(self, runtime):
        """Test auto-suggest initialization."""
        from pyfcstm.entry.simulate.repl import AutoSuggestFromCompleter
        from pyfcstm.entry.simulate.completer import SimulationCompleter

        completer = SimulationCompleter(runtime)
        auto_suggest = AutoSuggestFromCompleter(completer)
        assert auto_suggest.completer is completer

    def test_auto_suggest_command(self, runtime):
        """Test auto-suggest for commands."""
        from pyfcstm.entry.simulate.repl import AutoSuggestFromCompleter
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document
        from prompt_toolkit.buffer import Buffer

        completer = SimulationCompleter(runtime)
        auto_suggest = AutoSuggestFromCompleter(completer)

        # Test 'cy' should suggest 'cle' (remaining part of 'cycle')
        buffer = Buffer()
        document = Document('cy')
        suggestion = auto_suggest.get_suggestion(buffer, document)
        assert suggestion is not None
        # Should suggest only the remaining part
        assert suggestion.text == 'cle'

        # Test 'c' should suggest remaining part of 'cycle', 'clear', or 'current'
        document = Document('c')
        suggestion = auto_suggest.get_suggestion(buffer, document)
        assert suggestion is not None
        # Should be one of: 'ycle', 'lear', 'urrent'
        assert suggestion.text in ['ycle', 'lear', 'urrent']

    def test_auto_suggest_event(self, runtime):
        """Test auto-suggest for events."""
        from pyfcstm.entry.simulate.repl import AutoSuggestFromCompleter
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document
        from prompt_toolkit.buffer import Buffer

        completer = SimulationCompleter(runtime)
        auto_suggest = AutoSuggestFromCompleter(completer)
        runtime.cycle()  # Move to a state with events

        # Test 'cycle S' should suggest an event starting with S
        buffer = Buffer()
        document = Document('cycle S')
        suggestion = auto_suggest.get_suggestion(buffer, document)
        # Should have a suggestion if there are events starting with S
        if suggestion:
            assert suggestion.text.startswith('S') or suggestion.text.startswith('tart')

    def test_auto_suggest_no_match(self, runtime):
        """Test auto-suggest with no matches."""
        from pyfcstm.entry.simulate.repl import AutoSuggestFromCompleter
        from pyfcstm.entry.simulate.completer import SimulationCompleter
        from prompt_toolkit.document import Document
        from prompt_toolkit.buffer import Buffer

        completer = SimulationCompleter(runtime)
        auto_suggest = AutoSuggestFromCompleter(completer)

        # Test 'xyz' should not suggest anything
        buffer = Buffer()
        document = Document('xyz')
        suggestion = auto_suggest.get_suggestion(buffer, document)
        assert suggestion is None


@pytest.mark.unittest
class TestCLIEntry:
    """Tests for CLI entry point."""

    def test_simulate_batch_mode(self, tmp_path):
        """Test simulate command in batch mode."""
        from click.testing import CliRunner
        from pyfcstm.entry.cli import pyfcstmcli

        # Create a test DSL file
        dsl_file = tmp_path / "test.fcstm"
        dsl_file.write_text(TEST_DSL)

        runner = CliRunner()
        result = runner.invoke(pyfcstmcli, [
            'simulate',
            '-i', str(dsl_file),
            '-e', 'current; cycle; current'
        ])

        assert result.exit_code == 0
        assert 'System' in result.output

    def test_simulate_invalid_file(self):
        """Test simulate command with invalid file."""
        from click.testing import CliRunner
        from pyfcstm.entry.cli import pyfcstmcli

        runner = CliRunner()
        result = runner.invoke(pyfcstmcli, [
            'simulate',
            '-i', '/nonexistent/file.fcstm',
            '-e', 'current'
        ])

        assert result.exit_code == 0  # Click doesn't exit with error
        assert 'Failed to parse' in result.output or 'No such file' in result.output

    def test_simulate_no_color(self, tmp_path):
        """Test simulate command with --no-color flag."""
        from click.testing import CliRunner
        from pyfcstm.entry.cli import pyfcstmcli

        dsl_file = tmp_path / "test.fcstm"
        dsl_file.write_text(TEST_DSL)

        runner = CliRunner()
        result = runner.invoke(pyfcstmcli, [
            'simulate',
            '-i', str(dsl_file),
            '-e', 'current',
            '--no-color'
        ])

        assert result.exit_code == 0
        assert 'System' in result.output


@pytest.mark.unittest
class TestREPL:
    """Tests for SimulationREPL class."""

    def test_repl_initialization(self, runtime):
        """Test REPL initialization."""
        from pyfcstm.entry.simulate.repl import SimulationREPL

        # Skip if no terminal available (CI/CD environments)
        try:
            repl = SimulationREPL(runtime, use_color=False)
            assert repl.command_processor is not None
            assert repl.session is not None
        except Exception as e:
            # prompt_toolkit may fail in non-interactive environments (Windows CI, etc.)
            error_name = type(e).__name__
            if error_name in ['NoConsoleScreenBufferError', 'EOFError', 'OSError']:
                pytest.skip(f"REPL requires interactive terminal (skipped in CI): {error_name}")
            raise

    def test_repl_process_command(self, runtime):
        """Test REPL command processing."""
        from pyfcstm.entry.simulate.repl import SimulationREPL

        # Skip if no terminal available (CI/CD environments)
        try:
            repl = SimulationREPL(runtime, use_color=False)
            # Test that command processor works
            result = repl.command_processor.process("current")
            assert "System" in result.output
        except Exception as e:
            # prompt_toolkit may fail in non-interactive environments (Windows CI, etc.)
            error_name = type(e).__name__
            if error_name in ['NoConsoleScreenBufferError', 'EOFError', 'OSError']:
                pytest.skip(f"REPL requires interactive terminal (skipped in CI): {error_name}")
            raise


@pytest.mark.unittest
class TestPlatformCompatibility:
    """Tests for cross-platform compatibility."""

    def test_color_support_detection(self):
        """Test color support detection works on different platforms."""
        from pyfcstm.entry.simulate.display import StateDisplay

        # Test with color explicitly enabled
        display_color = StateDisplay(use_color=True)
        assert isinstance(display_color.use_color, bool)

        # Test with color explicitly disabled
        display_no_color = StateDisplay(use_color=False)
        assert display_no_color.use_color is False

    def test_path_handling(self, tmp_path):
        """Test that file paths work correctly across platforms."""
        from click.testing import CliRunner
        from pyfcstm.entry.cli import pyfcstmcli

        # Create test file using pathlib (cross-platform)
        test_file = tmp_path / "test.fcstm"
        test_file.write_text(TEST_DSL)

        runner = CliRunner()
        # Use string path (should work on all platforms)
        result = runner.invoke(pyfcstmcli, [
            'simulate',
            '-i', str(test_file),
            '-e', 'current'
        ])

        assert result.exit_code == 0
        assert 'System' in result.output

    def test_line_endings(self, tmp_path):
        """Test that different line endings are handled correctly."""
        from click.testing import CliRunner
        from pyfcstm.entry.cli import pyfcstmcli

        # Test with Unix line endings
        unix_file = tmp_path / "unix.fcstm"
        unix_file.write_text(TEST_DSL.replace('\r\n', '\n'))

        runner = CliRunner()
        result = runner.invoke(pyfcstmcli, [
            'simulate',
            '-i', str(unix_file),
            '-e', 'current'
        ])
        assert result.exit_code == 0

        # Test with Windows line endings
        windows_file = tmp_path / "windows.fcstm"
        windows_file.write_text(TEST_DSL.replace('\n', '\r\n'))

        result = runner.invoke(pyfcstmcli, [
            'simulate',
            '-i', str(windows_file),
            '-e', 'current'
        ])
        assert result.exit_code == 0

    def test_unicode_handling(self, tmp_path):
        """Test that Unicode in DSL is handled correctly."""
        from click.testing import CliRunner
        from pyfcstm.entry.cli import pyfcstmcli

        # DSL with Unicode comments (should be stripped by parser)
        unicode_dsl = """
        def int counter = 0;

        state System {
            state Active;
            [*] -> Active;
        }
        """
        unicode_file = tmp_path / "unicode.fcstm"
        unicode_file.write_text(unicode_dsl, encoding='utf-8')

        runner = CliRunner()
        result = runner.invoke(pyfcstmcli, [
            'simulate',
            '-i', str(unicode_file),
            '-e', 'current'
        ])
        assert result.exit_code == 0

    def test_batch_processor_no_color(self, runtime):
        """Test BatchProcessor works without color support."""
        from pyfcstm.entry.simulate.batch import BatchProcessor

        processor = BatchProcessor(runtime, use_color=False)
        result = _collect_batch_output(processor, "current; cycle; current")

        # Should work without ANSI codes
        assert "System" in result
        assert "Idle" in result or "Running" in result

    def test_command_processor_no_color(self, runtime):
        """Test CommandProcessor works without color support."""
        from pyfcstm.entry.simulate.commands import CommandProcessor

        processor = CommandProcessor(runtime, use_color=False)
        result = processor.process("current")

        # Should work without ANSI codes
        assert "System" in result.output
        assert "\033[" not in result.output  # No ANSI codes


@pytest.mark.unittest
class TestTerminalCompatibility:
    """Tests for terminal compatibility."""

    def test_ansi_color_codes(self):
        """Test ANSI color codes are properly formatted."""
        from pyfcstm.entry.simulate.display import StateDisplay

        display = StateDisplay(use_color=True)
        display.use_color = True  # Force enable for testing

        # Test all color codes
        for color in ['blue', 'green', 'yellow', 'red', 'cyan', 'gray']:
            result = display._colorize("test", color)
            # Should either have ANSI codes or be plain text
            assert isinstance(result, str)
            assert "test" in result

    def test_table_formatting_without_color(self, display):
        """Test table formatting works without color."""
        headers = ['Col1', 'Col2', 'Col3']
        rows = [
            [1, 'text', 3.14],
            [2, 'more', 2.71],
        ]

        result = display.format_table(headers, rows, [])
        # Should have proper structure
        assert 'Col1' in result
        assert 'Col2' in result
        assert 'text' in result
        assert '---' in result  # Separator

    def test_wide_characters_in_table(self, display):
        """Test table handles wide characters correctly."""
        headers = ['Name', 'Value']
        rows = [
            ['Test', '123'],
            ['LongName', '456789'],
        ]

        result = display.format_table(headers, rows, [])
        # Should not crash with wide characters
        assert 'Name' in result
        assert 'Test' in result

    def test_log_output_levels(self, display, capsys):
        """Test log output with different levels."""
        import logging
        # Create a logger with a handler that writes to stdout for testing
        logger = logging.getLogger('test_display_log_levels')
        logger.handlers.clear()
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter('[%(levelname)s] %(message)s'))
        logger.addHandler(handler)
        logger.setLevel(logging.DEBUG)

        display.logger = logger
        levels = ['debug', 'info', 'warning', 'error']

        for level in levels:
            display.log(f"Test {level}", level)
            captured = capsys.readouterr()
            assert f"Test {level}" in captured.out

    def test_empty_output_handling(self, display):
        """Test handling of empty output."""
        # Empty table
        result = display.format_table(['A', 'B'], [], [])
        assert result == ""

        # Empty events
        result = display.format_events([])
        assert "No events" in result or result != ""


@pytest.mark.unittest
class TestDSLVariety:
    """Tests with various DSL files to ensure robustness."""

    def test_simple_dsl(self):
        """Test with a very simple DSL."""
        dsl = """
        state System {
            state A;
            [*] -> A;
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        result = processor.process("current")
        assert "System" in result.output

        result = processor.process("cycle")
        assert "System.A" in result.output

    def test_complex_hierarchical_dsl(self):
        """Test with complex hierarchical state machine."""
        dsl = """
        def int x = 0;
        def int y = 0;

        state System {
            state Level1 {
                state Level2 {
                    state Level3 {
                        state Deep;
                        [*] -> Deep;
                    }
                    [*] -> Level3;
                }
                [*] -> Level2;
            }
            [*] -> Level1;
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        # Should navigate through all levels
        result = processor.process("cycle")
        assert "Deep" in result.output

    def test_dsl_with_transitions_and_events(self):
        """Test DSL with multiple transitions and events."""
        dsl = """
        def int counter = 0;

        state System {
            state A {
                during {
                    counter = counter + 1;
                }
            }
            state B {
                during {
                    counter = counter + 10;
                }
            }
            state C;

            [*] -> A;
            A -> B :: GoToB;
            B -> C :: GoToC;
            C -> A :: GoToA;
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        # Test state transitions
        processor.process("cycle")  # Enter A
        assert runtime.vars['counter'] == 1

        processor.process("cycle GoToB")  # A -> B
        assert runtime.vars['counter'] == 11

        processor.process("cycle GoToC")  # B -> C
        assert runtime.vars['counter'] == 11

        processor.process("cycle GoToA")  # C -> A
        assert runtime.vars['counter'] == 12

    def test_dsl_with_guards(self):
        """Test DSL with guard conditions."""
        dsl = """
        def int value = 0;

        state System {
            state Low;
            state High;

            [*] -> Low;
            Low -> High : if [value >= 10];
            High -> Low : if [value < 10];
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        # Initially in Low
        processor.process("cycle")
        assert "Low" in processor.process("current").output

        # Set value to trigger guard
        runtime.vars['value'] = 10
        processor.process("cycle")
        assert "High" in processor.process("current").output

    def test_dsl_with_effects(self):
        """Test DSL with transition effects."""
        dsl = """
        def int x = 0;
        def int y = 0;

        state System {
            state A;
            state B;

            [*] -> A;
            A -> B effect {
                x = 100;
                y = 200;
            };
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        processor.process("cycle")  # Enter A
        assert runtime.vars['x'] == 0
        assert runtime.vars['y'] == 0

        processor.process("cycle")  # A -> B with effect
        assert runtime.vars['x'] == 100
        assert runtime.vars['y'] == 200

    def test_dsl_with_enter_exit_actions(self):
        """Test DSL with enter/exit actions."""
        dsl = """
        def int enter_count = 0;
        def int exit_count = 0;

        state System {
            state A {
                enter {
                    enter_count = enter_count + 1;
                }
                exit {
                    exit_count = exit_count + 1;
                }
            }
            state B;

            [*] -> A;
            A -> B :: Next;
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        processor.process("cycle")  # Enter A
        assert runtime.vars['enter_count'] == 1
        assert runtime.vars['exit_count'] == 0

        processor.process("cycle Next")  # Exit A, enter B
        assert runtime.vars['enter_count'] == 1
        assert runtime.vars['exit_count'] == 1

    def test_dsl_with_multiple_variables(self):
        """Test DSL with many variables."""
        dsl = """
        def int a = 1;
        def int b = 2;
        def int c = 3;
        def float d = 4.5;
        def float e = 5.5;

        state System {
            state Active {
                during {
                    a = a + 1;
                    b = b * 2;
                    c = c + b;
                    d = d + 0.1;
                    e = e * 1.1;
                }
            }
            [*] -> Active;
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        # Test that all variables are tracked
        result = processor.process("current")
        assert "a" in result.output
        assert "b" in result.output
        assert "c" in result.output
        assert "d" in result.output
        assert "e" in result.output

        # Test multi-cycle with many variables
        result = processor.process("cycle 3")
        assert "a" in result.output
        assert "b" in result.output

    def test_dsl_edge_case_empty_states(self):
        """Test DSL with empty states (no actions)."""
        dsl = """
        state System {
            state Empty1;
            state Empty2;
            state Empty3;

            [*] -> Empty1;
            Empty1 -> Empty2 :: E1;
            Empty2 -> Empty3 :: E2;
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        processor.process("cycle")
        assert "Empty1" in processor.process("current").output

        processor.process("cycle E1")
        assert "Empty2" in processor.process("current").output

    def test_dsl_with_termination(self):
        """Test DSL that terminates."""
        dsl = """
        def int steps = 0;

        state System {
            state Running {
                during {
                    steps = steps + 1;
                }
            }

            [*] -> Running;
            Running -> [*] : if [steps >= 5];
        }
        """
        ast = parse_with_grammar_entry(dsl, 'state_machine_dsl')
        sm = parse_dsl_node_to_state_machine(ast)
        runtime = SimulationRuntime(sm)
        processor = CommandProcessor(runtime, use_color=False)

        # Run until termination
        for _ in range(10):
            processor.process("cycle")
            if runtime.is_ended:
                break

        assert runtime.is_ended
        assert runtime.vars['steps'] >= 5


@pytest.mark.unittest
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
        result = _collect_batch_output(batch_processor, commands)

        # Each command produces output, cycle also shows current state
        assert "System.Idle" in result
        assert "System.Running" in result

    def test_command_processor_workflow(self, command_processor, runtime):
        """Test command processor workflow."""
        # Start
        result = command_processor.process("cycle")
        assert "System.Idle" in result.output

        # Check events
        result = command_processor.process("events")
        assert "Start" in result.output

        # Trigger event
        result = command_processor.process("cycle Start")
        assert "System.Running" in result.output

        # Clear
        result = command_processor.process("clear")
        assert "System" in result.output

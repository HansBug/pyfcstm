"""
Command processor for the simulation REPL.

This module provides command parsing and execution for the interactive
state machine simulator.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

from .display import StateDisplay
from .logging import configure_simulate_cli_logger


class LogLevel(Enum):
    """
    Log level enumeration for controlling output verbosity.

    :cvar DEBUG: Show all messages including debug information
    :cvar INFO: Show informational messages and above
    :cvar WARNING: Show warnings and errors only
    :cvar ERROR: Show errors only
    :cvar OFF: Disable all logging
    """
    DEBUG = "debug"
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    OFF = "off"


class Settings:
    """
    Runtime settings for the simulator.

    :ivar table_max_rows: Maximum rows to display in tables before truncating
    :vartype table_max_rows: int
    :ivar history_size: Maximum number of history entries to keep
    :vartype history_size: int
    :ivar color: Whether to use ANSI colors
    :vartype color: bool
    :ivar log_level: Current log level
    :vartype log_level: LogLevel
    """

    def __init__(self):
        """Initialize settings with default values."""
        self.table_max_rows: int = 20
        self.history_size: int = 100
        self.color: bool = True
        self.log_level: LogLevel = LogLevel.WARNING

    def get(self, key: str) -> Any:
        """
        Get a setting value.

        :param key: Setting key
        :type key: str
        :return: Setting value
        :rtype: Any
        :raises KeyError: If key doesn't exist
        """
        if not hasattr(self, key):
            raise KeyError(f"Unknown setting: {key}")
        return getattr(self, key)

    def set(self, key: str, value: Any) -> None:
        """
        Set a setting value.

        :param key: Setting key
        :type key: str
        :param value: Setting value
        :type value: Any
        :raises KeyError: If key doesn't exist
        :raises ValueError: If value is invalid
        """
        if not hasattr(self, key):
            raise KeyError(f"Unknown setting: {key}")

        # Validate and convert value based on type
        current_value = getattr(self, key)
        if isinstance(current_value, bool):
            if isinstance(value, str):
                if value.lower() in ('on', 'true', '1', 'yes'):
                    value = True
                elif value.lower() in ('off', 'false', '0', 'no'):
                    value = False
                else:
                    raise ValueError(f"Invalid boolean value: {value}")
        elif isinstance(current_value, int):
            try:
                value = int(value)
                if value < 0:
                    raise ValueError(f"Value must be non-negative: {value}")
            except (ValueError, TypeError):
                raise ValueError(f"Invalid integer value: {value}")
        elif isinstance(current_value, LogLevel):
            if isinstance(value, str):
                try:
                    value = LogLevel(value.lower())
                except ValueError:
                    valid_levels = [level.value for level in LogLevel]
                    raise ValueError(f"Invalid log level. Available: {', '.join(valid_levels)}")

        setattr(self, key, value)

    def list_all(self) -> Dict[str, Any]:
        """
        Get all settings as a dictionary.

        :return: Dictionary of all settings
        :rtype: Dict[str, Any]
        """
        return {
            'table_max_rows': self.table_max_rows,
            'history_size': self.history_size,
            'color': self.color,
            'log_level': self.log_level.value if isinstance(self.log_level, LogLevel) else self.log_level,
        }


@dataclass
class CommandResult:
    """
    Result of a command execution.

    :param output: The output text to display to the user
    :type output: str
    :param should_exit: Whether the REPL should exit after this command
    :type should_exit: bool
    """
    output: str
    should_exit: bool = False


class CommandProcessor:
    """
    Processor for handling interactive commands.

    This class routes commands to their handlers and manages command execution
    state including log level.

    :param runtime: The simulation runtime instance
    :type runtime: SimulationRuntime
    :ivar display: State display formatter
    :vartype display: StateDisplay
    :ivar log_level: Current log level
    :vartype log_level: LogLevel
    """

    def __init__(self, runtime, state_machine=None, use_color: bool = True):
        """
        Initialize the command processor.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param state_machine: The state machine model (required for init command)
        :type state_machine: StateMachine, optional
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        """
        self.runtime = runtime
        self.state_machine = state_machine if state_machine is not None else runtime.state_machine
        self.settings = Settings()
        self.settings.color = use_color
        self.display = StateDisplay(use_color=use_color, logger=runtime.logger)

        configure_simulate_cli_logger(self.runtime.logger, use_color=use_color)

        # Sync log level with runtime logger
        self._sync_log_level()

    def _sync_log_level(self):
        """
        Synchronize log level setting with runtime logger.
        """
        import logging
        level_map = {
            LogLevel.DEBUG: logging.DEBUG,
            LogLevel.INFO: logging.INFO,
            LogLevel.WARNING: logging.WARNING,
            LogLevel.ERROR: logging.ERROR,
            LogLevel.OFF: logging.CRITICAL + 10,  # Higher than CRITICAL to disable all
        }
        self.runtime.logger.setLevel(level_map[self.settings.log_level])

    def process(self, user_input: str) -> CommandResult:
        """
        Process a user command.

        :param user_input: The raw user input string
        :type user_input: str
        :return: Command execution result
        :rtype: CommandResult
        """
        parts = user_input.strip().split()
        if not parts:
            return CommandResult("")

        command = parts[0]
        args = parts[1:]

        try:
            if command == 'cycle':
                return self._handle_cycle(args)
            elif command == 'init':
                return self._handle_init(args)
            elif command == 'clear':
                return self._handle_clear()
            elif command == 'current':
                return self._handle_current()
            elif command == 'events':
                return self._handle_events()
            elif command == 'history':
                return self._handle_history(args)
            elif command == 'setting':
                return self._handle_setting(args)
            elif command == 'export':
                return self._handle_export(args)
            elif command == 'help':
                return self._handle_help()
            elif command in ['quit', 'exit']:
                return CommandResult("Goodbye!", should_exit=True)
            else:
                return CommandResult(f"Unknown command: {command}. Type 'help' for available commands.")
        except Exception as e:
            return CommandResult(f"Error: {e}")

    def _handle_cycle(self, events: List[str]) -> CommandResult:
        """
        Handle cycle command with optional count parameter.

        Supports two formats:
        - cycle [events...] - Execute 1 cycle with optional events
        - cycle [count] [events...] - Execute count cycles with optional events

        For count > 1, displays results in table format.

        :param events: List containing optional count and event names
        :type events: List[str]
        :return: Command result with current state or table
        :rtype: CommandResult
        """
        try:
            # Parse arguments: first arg might be count
            count = 1
            event_list = events

            if events:
                # Check if first argument looks like a number
                first_arg = events[0]
                if first_arg.lstrip('-').isdigit():
                    # First argument is a number
                    try:
                        count = int(first_arg)
                        if count <= 0:
                            return CommandResult("Error: cycle count must be a positive integer")
                        event_list = events[1:]
                    except ValueError:
                        return CommandResult(f"Error: invalid cycle count '{first_arg}'")

            # Single cycle - use simple format
            if count == 1:
                if self.settings.log_level == LogLevel.DEBUG:
                    self.display.log(f"Executing cycle with events: {event_list if event_list else 'none'}", "debug")
                self.runtime.cycle(event_list if event_list else None)
                return CommandResult(self.display.format_current_state(self.runtime))

            # Multiple cycles - use table format
            return self._handle_multiple_cycles(count, event_list)

        except Exception as e:
            # Import here to avoid circular dependency
            from ...simulate import SimulationRuntimeDfsError

            if isinstance(e, SimulationRuntimeDfsError):
                return CommandResult(
                    "Cycle execution failed: State machine contains an unbounded execution chain.\n"
                    "This usually means there are too many automatic transitions without a stable state.\n"
                    "Please review your state machine definition for missing stoppable states."
                )
            else:
                return CommandResult(f"Cycle execution failed: {e}")

    def _handle_init(self, args: List[str]) -> CommandResult:
        """
        Handle init command to hot start from a specific state.

        Syntax: init <state_path> [var1=value1 var2=value2 ...]

        This command creates a new runtime instance starting from the specified
        state without executing enter actions. All variables must be provided.

        :param args: Command arguments [state_path, var_assignments...]
        :type args: List[str]
        :return: Command result with new current state
        :rtype: CommandResult
        """
        if not args:
            return CommandResult(
                "Usage: init <state_path> [var1=value1 ...]\n"
                "Example: init System.Active counter=10 flag=1\n"
                "Note: All variables must be provided when using init."
            )

        state_path = args[0]
        var_assignments = args[1:]

        # Parse variable assignments
        initial_vars = {}
        for assignment in var_assignments:
            if '=' not in assignment:
                return CommandResult(
                    f"Error: invalid variable assignment '{assignment}'. "
                    f"Expected format: var=value"
                )
            var_name, var_value_str = assignment.split('=', 1)
            var_name = var_name.strip()
            var_value_str = var_value_str.strip()

            # Parse value
            try:
                var_value = self._parse_value(var_value_str)
            except ValueError as e:
                return CommandResult(f"Error: {e}")

            initial_vars[var_name] = var_value

        # Validate that all variables are provided
        if initial_vars:
            missing_vars = set(self.runtime.vars.keys()) - set(initial_vars.keys())
            if missing_vars:
                return CommandResult(
                    f"Error: All variables must be provided. Missing: {sorted(missing_vars)}\n"
                    f"Available variables: {sorted(self.runtime.vars.keys())}"
                )

        # Create new runtime with hot start
        try:
            # Import here to avoid circular dependency
            from ...simulate import SimulationRuntime

            new_runtime = SimulationRuntime(
                self.state_machine,
                initial_state=state_path,
                initial_vars=initial_vars if initial_vars else None,
                abstract_error_mode=self.runtime._abstract_error_mode,
                history_size=self.runtime.history_size
            )

            # Replace runtime
            self.runtime = new_runtime

            # Reconfigure display with new runtime logger
            self.display = StateDisplay(use_color=self.settings.color, logger=new_runtime.logger)
            configure_simulate_cli_logger(new_runtime.logger, use_color=self.settings.color)
            self._sync_log_level()

            return CommandResult(
                f"Initialized from state: {state_path}\n" +
                self.display.format_current_state(self.runtime)
            )
        except Exception as e:
            return CommandResult(f"Initialization failed: {e}")

    def _parse_value(self, value_str: str) -> float:
        """
        Parse a numeric value from string.

        Supports:
        - Integers: 10, -5
        - Hexadecimal: 0xFF, 0x10
        - Binary: 0b1010, 0b11
        - Floats: 3.14, -2.5
        - Scientific notation: 1e-3, 2.5e2

        :param value_str: String representation of the value
        :type value_str: str
        :return: Parsed numeric value (int or float)
        :rtype: Union[int, float]
        :raises ValueError: If the value cannot be parsed
        """
        value_str = value_str.strip()

        # Hexadecimal
        if value_str.startswith(('0x', '0X')):
            try:
                return int(value_str, 16)
            except ValueError:
                raise ValueError(f"Invalid hexadecimal value: {value_str}")

        # Binary
        if value_str.startswith(('0b', '0B')):
            try:
                return int(value_str, 2)
            except ValueError:
                raise ValueError(f"Invalid binary value: {value_str}")

        # Try integer first
        try:
            return int(value_str)
        except ValueError:
            pass

        # Try float
        try:
            return float(value_str)
        except ValueError:
            raise ValueError(f"Invalid numeric value: {value_str}")

    def _handle_multiple_cycles(self, count: int, event_list: List[str]) -> CommandResult:
        """
        Handle multiple cycle execution with table output.

        :param count: Number of cycles to execute
        :type count: int
        :param event_list: List of events to trigger each cycle
        :type event_list: List[str]
        :return: Command result with table
        :rtype: CommandResult
        """
        # Get starting cycle count
        start_cycle = self.runtime.cycle_count

        # Collect data for all cycles
        table_data = []
        for i in range(count):
            if self.settings.log_level == LogLevel.DEBUG:
                self.display.log(f"Executing cycle {i+1}/{count} with events: {event_list if event_list else 'none'}", "debug")

            self.runtime.cycle(event_list if event_list else None)

            # Collect state and variables
            try:
                state_path = '.'.join(self.runtime.current_state.path)
            except (AttributeError, IndexError):
                state_path = "(terminated)"

            # Use actual cycle count from runtime
            cycle_num = start_cycle + i + 1
            row = [cycle_num, state_path]
            # Add variable values
            for var_name in sorted(self.runtime.vars.keys()):
                row.append(self.runtime.vars[var_name])

            table_data.append(row)

        # Prepare table headers
        headers = ['Cycle', 'State']
        var_names = sorted(self.runtime.vars.keys())
        headers.extend(var_names)

        # Filter rows if count >= 20
        if count >= 20:
            display_data = table_data[:10] + table_data[-10:]
            # Add separator row
            separator_row = ['...'] * len(headers)
            display_data = table_data[:10] + [separator_row] + table_data[-10:]
        else:
            display_data = table_data

        # Generate table using our custom formatter
        table_str = self.display.format_table(headers, display_data, var_names)

        return CommandResult(table_str)

    def _handle_clear(self) -> CommandResult:
        """
        Handle /clear command.

        :return: Command result with reset state
        :rtype: CommandResult
        """
        # Recreate the runtime to reset state
        from ...simulate import SimulationRuntime
        self.runtime = SimulationRuntime(self.runtime.state_machine)
        if self.settings.log_level in [LogLevel.DEBUG, LogLevel.INFO]:
            self.display.log("State machine reset to initial state", "info")
        return CommandResult(self.display.format_current_state(self.runtime))

    def _handle_current(self) -> CommandResult:
        """
        Handle /current command.

        :return: Command result with current state
        :rtype: CommandResult
        """
        return CommandResult(self.display.format_current_state(self.runtime))

    def _handle_events(self) -> CommandResult:
        """
        Handle /events command.

        :return: Command result with available events
        :rtype: CommandResult
        """
        events = self._get_current_events()
        return CommandResult(self.display.format_events(events))

    def _handle_help(self) -> CommandResult:
        """
        Handle help command.

        :return: Command result with help text
        :rtype: CommandResult
        """
        help_text = """Available commands:
  cycle [count] [events...]  - Execute cycle(s) with optional events
                               count: number of cycles (default: 1)
                               Examples: cycle, cycle 5, cycle 3 Start
  init <state> [vars...]     - Hot start from specific state with variables
                               All variables must be provided
                               Examples: init System.Active counter=10 flag=1
                               Supports: hex (0xFF), binary (0b1010), float (3.14)
  clear                      - Reset to initial state
  current                    - Show current state and all variables
  events                     - List available events in current state
  history [n|all]            - Show execution history (default: 10 recent entries)
  setting [key] [value]      - View or change settings (including log_level)
  export <filename>          - Export history to file (.csv, .json, .yaml, .jsonl)
  help                       - Show this help message
  quit, exit                 - Exit simulator

Keyboard shortcuts (interactive mode):
  Tab                        - Auto-complete commands and events
  Ctrl+R                     - Search command history
  Ctrl+C                     - Cancel current input
  Ctrl+D                     - Exit simulator
  Up/Down arrows             - Navigate command history"""
        return CommandResult(help_text)

    def _handle_history(self, args: List[str]) -> CommandResult:
        """
        Handle /history command.

        :param args: Command arguments (count or 'all')
        :type args: List[str]
        :return: Command result with history table
        :rtype: CommandResult
        """
        if not self.runtime.history:
            return CommandResult("No execution history available.")

        # Determine how many entries to show
        if args and args[0].lower() == 'all':
            count = len(self.runtime.history)
        elif args:
            try:
                count = int(args[0])
                if count <= 0:
                    return CommandResult("Error: count must be a positive integer")
            except ValueError:
                return CommandResult(f"Error: invalid count '{args[0]}'")
        else:
            count = 10  # Default

        # Get the most recent entries
        entries = self.runtime.history[-count:]

        # Prepare table data
        headers = ['Cycle', 'State']
        if entries:
            # Get all variable names from the first entry
            var_names = sorted(entries[0]['vars'].keys())
            headers.extend(var_names)

            # Build table rows
            table_data = []
            for entry in entries:
                row = [entry['cycle'], entry['state']]
                for var_name in var_names:
                    row.append(entry['vars'].get(var_name, ''))
                table_data.append(row)

            # Generate table
            table_str = self.display.format_table(headers, table_data, var_names)
            return CommandResult(table_str)
        else:
            return CommandResult("No history entries to display.")

    def _handle_setting(self, args: List[str]) -> CommandResult:
        """
        Handle /setting command.

        :param args: Command arguments (key and optional value)
        :type args: List[str]
        :return: Command result
        :rtype: CommandResult
        """
        if not args:
            # Show all settings
            settings = self.settings.list_all()
            lines = ["Current settings:"]
            for key, value in sorted(settings.items()):
                lines.append(f"  {key} = {value}")
            return CommandResult('\n'.join(lines))

        key = args[0]

        if len(args) == 1:
            # Show specific setting
            try:
                value = self.settings.get(key)
                if isinstance(value, LogLevel):
                    value = value.value
                return CommandResult(f"{key} = {value}")
            except KeyError as e:
                return CommandResult(f"Error: {e}")

        # Set setting
        value = args[1]
        try:
            self.settings.set(key, value)

            # Apply setting changes
            if key == 'color':
                self.display.use_color = self.settings.color
            elif key == 'log_level':
                # Sync log level with runtime logger
                self._sync_log_level()
            elif key == 'history_size':
                # Update runtime history size
                self.runtime.history_size = self.settings.history_size if self.settings.history_size > 0 else None
                # Trim existing history to new size
                if self.runtime.history_size is not None and len(self.runtime.history) > self.runtime.history_size:
                    self.runtime.history = self.runtime.history[-self.runtime.history_size:]

            return CommandResult(f"Setting updated: {key} = {value}")
        except (KeyError, ValueError) as e:
            return CommandResult(f"Error: {e}")

    def _get_current_events(self) -> List[Tuple[str, Optional[str]]]:
        """
        Get available events in the current state.

        :return: List of (full_path, short_name) tuples
        :rtype: List[Tuple[str, Optional[str]]]
        """
        if not self.runtime.current_state:
            return []

        current_state = self.runtime.current_state
        current_state_name = current_state.name
        events = []
        seen_events = set()

        # Check parent's transitions for transitions from current state
        if current_state.parent:
            parent = current_state.parent
            for transition in parent.transitions:
                # Check if this transition is from the current state
                if transition.from_state == current_state_name and transition.event:
                    event_path = '.'.join(transition.event.state_path) + '.' + transition.event.name
                    if event_path not in seen_events:
                        seen_events.add(event_path)
                        # Add full path and short name
                        short_name = transition.event.name
                        if short_name != event_path:
                            events.append((event_path, short_name))
                        else:
                            events.append((event_path, None))

        return events

    def _handle_export(self, args: List[str]) -> CommandResult:
        """
        Handle export command to export history to file.

        Supports multiple formats based on file extension:
        - .csv: CSV format with columns: cycle, state, var1, var2, ...
        - .json: JSON array of history entries
        - .yaml: YAML array of history entries
        - .jsonl: JSON Lines format (one JSON object per line)

        :param args: Command arguments [filename]
        :type args: List[str]
        :return: Command result
        :rtype: CommandResult
        """
        if not args:
            return CommandResult("Usage: export <filename>\nSupported formats: .csv, .json, .yaml, .jsonl")

        filename = args[0]

        # Check if history is empty
        if not self.runtime.history:
            return CommandResult("No history to export. Run some cycles first.")

        # Determine format from extension
        import os
        _, ext = os.path.splitext(filename)
        ext = ext.lower()

        if ext not in ['.csv', '.json', '.yaml', '.jsonl']:
            return CommandResult(f"Unsupported file format: {ext}\nSupported formats: .csv, .json, .yaml, .jsonl")

        try:
            if ext == '.csv':
                self._export_csv(filename)
            elif ext == '.json':
                self._export_json(filename)
            elif ext == '.yaml':
                self._export_yaml(filename)
            elif ext == '.jsonl':
                self._export_jsonl(filename)

            return CommandResult(f"History exported to {filename} ({len(self.runtime.history)} entries)")
        except Exception as e:
            return CommandResult(f"Export failed: {e}")

    def _export_csv(self, filename: str) -> None:
        """
        Export history to CSV format.

        Includes cycle, state, events (semicolon-separated), and all variables.

        :param filename: Output filename
        :type filename: str
        """
        import csv

        # Get all variable names
        var_names = sorted(self.runtime.vars.keys())

        with open(filename, 'w', newline='', encoding='utf-8') as f:
            writer = csv.writer(f)

            # Write header
            header = ['cycle', 'state', 'events'] + var_names
            writer.writerow(header)

            # Write data
            for entry in self.runtime.history:
                cycle_num = entry['cycle']
                state = entry['state']
                events = entry.get('events', [])
                vars_dict = entry['vars']

                # Join events with semicolon to avoid confusion with CSV commas
                events_str = ';'.join(events) if events else ''

                row = [cycle_num, state, events_str]
                for var_name in var_names:
                    row.append(vars_dict.get(var_name, ''))

                writer.writerow(row)

    def _export_json(self, filename: str) -> None:
        """
        Export history to JSON format.

        :param filename: Output filename
        :type filename: str
        """
        import json

        with open(filename, 'w', encoding='utf-8') as f:
            json.dump(self.runtime.history, f, indent=2, ensure_ascii=False)

    def _export_yaml(self, filename: str) -> None:
        """
        Export history to YAML format.

        :param filename: Output filename
        :type filename: str
        """
        import yaml

        with open(filename, 'w', encoding='utf-8') as f:
            yaml.dump(self.runtime.history, f, default_flow_style=False, allow_unicode=True)

    def _export_jsonl(self, filename: str) -> None:
        """
        Export history to JSON Lines format.

        :param filename: Output filename
        :type filename: str
        """
        import json

        with open(filename, 'w', encoding='utf-8') as f:
            for entry in self.runtime.history:
                f.write(json.dumps(entry, ensure_ascii=False) + '\n')

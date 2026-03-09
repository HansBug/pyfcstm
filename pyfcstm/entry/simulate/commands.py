"""
Command processor for the simulation REPL.

This module provides command parsing and execution for the interactive
state machine simulator.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple, Dict, Any
from enum import Enum

from .display import StateDisplay


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

    def __init__(self, runtime, use_color: bool = True):
        """
        Initialize the command processor.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        """
        self.runtime = runtime
        self.settings = Settings()
        self.settings.color = use_color
        self.display = StateDisplay(use_color=use_color)

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
            if command == '/cycle':
                return self._handle_cycle(args)
            elif command == '/clear':
                return self._handle_clear()
            elif command == '/current':
                return self._handle_current()
            elif command == '/events':
                return self._handle_events()
            elif command == '/history':
                return self._handle_history(args)
            elif command == '/setting':
                return self._handle_setting(args)
            elif command == '/help':
                return self._handle_help()
            elif command in ['/quit', '/exit']:
                return CommandResult("Goodbye!", should_exit=True)
            else:
                return CommandResult(f"Unknown command: {command}. Type /help for available commands.")
        except Exception as e:
            return CommandResult(f"Error: {e}")

    def _handle_cycle(self, events: List[str]) -> CommandResult:
        """
        Handle /cycle command with optional count parameter.

        Supports two formats:
        - /cycle [events...] - Execute 1 cycle with optional events
        - /cycle [count] [events...] - Execute count cycles with optional events

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
        Handle /help command.

        :return: Command result with help text
        :rtype: CommandResult
        """
        help_text = """Available commands:
  /cycle [count] [events...]  - Execute cycle(s) with optional events
                                count: number of cycles (default: 1)
                                Examples: /cycle, /cycle 5, /cycle 3 Start
  /clear                      - Reset to initial state
  /current                    - Show current state and all variables
  /events                     - List available events in current state
  /history [n|all]            - Show execution history (default: 10 recent entries)
  /setting [key] [value]      - View or change settings (including log_level)
  /help                       - Show this help message
  /quit, /exit                - Exit simulator

Keyboard shortcuts (interactive mode):
  Tab                         - Auto-complete commands and events
  Ctrl+R                      - Search command history
  Ctrl+C                      - Cancel current input
  Ctrl+D                      - Exit simulator
  Up/Down arrows              - Navigate command history"""
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

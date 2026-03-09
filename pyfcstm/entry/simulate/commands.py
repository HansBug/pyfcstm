"""
Command processor for the simulation REPL.

This module provides command parsing and execution for the interactive
state machine simulator.
"""

from dataclasses import dataclass
from typing import List, Optional, Tuple
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
        self.display = StateDisplay(use_color=use_color)
        self.log_level = LogLevel.INFO

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
            elif command == '/log':
                return self._handle_log(args)
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
                if self.log_level == LogLevel.DEBUG:
                    self.display.log(f"Executing cycle with events: {event_list if event_list else 'none'}", "debug")
                self.runtime.cycle(event_list if event_list else None)
                return CommandResult(self.display.format_current_state(self.runtime))

            # Multiple cycles - use table format
            return self._handle_multiple_cycles(count, event_list)

        except Exception as e:
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
            if self.log_level == LogLevel.DEBUG:
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
        if self.log_level in [LogLevel.DEBUG, LogLevel.INFO]:
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

    def _handle_log(self, args: List[str]) -> CommandResult:
        """
        Handle /log command.

        :param args: Command arguments (log level)
        :type args: List[str]
        :return: Command result
        :rtype: CommandResult
        """
        if not args:
            return CommandResult(f"Current log level: {self.log_level.value}")

        level_str = args[0].lower()
        try:
            self.log_level = LogLevel(level_str)
            return CommandResult(f"Log level set to: {level_str}")
        except ValueError:
            valid_levels = [level.value for level in LogLevel]
            return CommandResult(f"Invalid log level. Available levels: {', '.join(valid_levels)}")

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
  /log [level]                - Set or display log level (debug, info, warning, error, off)
  /help                       - Show this help message
  /quit, /exit                - Exit simulator"""
        return CommandResult(help_text)

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

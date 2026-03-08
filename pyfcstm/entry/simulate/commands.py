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
        Handle /cycle command.

        :param events: List of event names to trigger
        :type events: List[str]
        :return: Command result with current state
        :rtype: CommandResult
        """
        try:
            if self.log_level == LogLevel.DEBUG:
                self.display.log(f"Executing cycle with events: {events if events else 'none'}", "debug")

            self.runtime.cycle(events if events else None)
            return CommandResult(self.display.format_current_state(self.runtime))
        except Exception as e:
            return CommandResult(f"Cycle execution failed: {e}")

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
  /cycle [events...]  - Execute one cycle with optional events
  /clear              - Reset to initial state
  /current            - Show current state and all variables
  /events             - List available events in current state
  /log [level]        - Set or display log level (debug, info, warning, error, off)
  /help               - Show this help message
  /quit, /exit        - Exit simulator"""
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

"""
Auto-completion support for the simulation REPL.

This module provides command and argument completion using prompt_toolkit's
completion framework.
"""

from typing import Iterable

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class SimulationCompleter(Completer):
    """
    Completer for simulation REPL commands and arguments.

    This class provides context-aware completion for commands, event names,
    and log levels in the interactive simulator.

    :param runtime: The simulation runtime instance
    :type runtime: SimulationRuntime
    :ivar COMMANDS: List of available commands
    :vartype COMMANDS: list
    :ivar LOG_LEVELS: List of available log levels
    :vartype LOG_LEVELS: list
    """

    COMMANDS = [
        'cycle', 'clear', 'current', 'events',
        'history', 'setting', 'help', 'quit', 'exit'
    ]

    LOG_LEVELS = ['debug', 'info', 'warning', 'error', 'off']

    def __init__(self, runtime):
        """
        Initialize the completer.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        """
        self.runtime = runtime

    def get_completions(self, document: Document, complete_event) -> Iterable[Completion]:
        """
        Generate completions for the current input.

        :param document: The current document
        :type document: Document
        :param complete_event: The completion event
        :return: Iterator of completion suggestions
        :rtype: Iterable[Completion]
        """
        text = document.text_before_cursor
        words = text.split()

        # Command completion
        if not text or ' ' not in text:
            for cmd in self.COMMANDS:
                if cmd.startswith(text):
                    yield Completion(
                        cmd,
                        start_position=-len(text),
                        display_meta=self._get_command_help(cmd)
                    )

        # Event completion (after cycle)
        elif text.startswith('cycle '):
            # Get the last word being typed
            if words:
                event_prefix = words[-1]
            else:
                event_prefix = ''

            events = self._get_current_events()
            for event in events:
                if event.startswith(event_prefix):
                    yield Completion(
                        event,
                        start_position=-len(event_prefix)
                    )

        # Setting key completion (after setting)
        elif text.startswith('setting '):
            setting_keys = ['table_max_rows', 'history_size', 'color', 'log_level']
            if words and len(words) >= 2:
                key_prefix = words[-1]
            else:
                key_prefix = ''

            for key in setting_keys:
                if key.startswith(key_prefix):
                    yield Completion(
                        key,
                        start_position=-len(key_prefix)
                    )

    def _get_current_events(self) -> list:
        """
        Get available events in the current state.

        Returns both full-path and short event names.

        :return: List of event names
        :rtype: list
        """
        if not self.runtime.current_state:
            return []

        current_state = self.runtime.current_state
        current_state_name = current_state.name
        events = set()

        # Check parent's transitions for transitions from current state
        if current_state.parent:
            parent = current_state.parent
            for transition in parent.transitions:
                # Check if this transition is from the current state
                if transition.from_state == current_state_name and transition.event:
                    # Add full path
                    event_path = '.'.join(transition.event.state_path) + '.' + transition.event.name
                    events.add(event_path)
                    # Add short name
                    events.add(transition.event.name)

        return sorted(events)

    def _get_command_help(self, cmd: str) -> str:
        """
        Get help text for a command.

        :param cmd: The command name
        :type cmd: str
        :return: Help text
        :rtype: str
        """
        help_map = {
            'cycle': 'Execute cycle(s) with optional events',
            'clear': 'Reset to initial state',
            'current': 'Show current state and variables',
            'events': 'List available events',
            'history': 'Show execution history',
            'setting': 'View or change settings',
            'help': 'Show help',
            'quit': 'Exit simulator',
            'exit': 'Exit simulator',
        }
        return help_map.get(cmd, '')

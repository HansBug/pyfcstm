"""
Auto-completion support for the simulation REPL.

This module provides comprehensive command and argument completion using
prompt_toolkit's completion framework. It supports context-aware completion
for all commands including their arguments and values.
"""

from typing import Iterable

from prompt_toolkit.completion import Completer, Completion
from prompt_toolkit.document import Document


class SimulationCompleter(Completer):
    """
    Completer for simulation REPL commands and arguments.

    This class provides comprehensive context-aware completion for:
    - Command names (with partial matching)
    - Event names for cycle command (both full-path and short names)
    - Count values for cycle and history commands
    - Setting keys and values for setting command
    - Log levels for log_level setting

    :param runtime: The simulation runtime instance
    :type runtime: SimulationRuntime
    :ivar COMMANDS: List of available commands
    :vartype COMMANDS: list
    :ivar LOG_LEVELS: List of available log levels
    :vartype LOG_LEVELS: list
    """

    COMMANDS = [
        'cycle', 'clear', 'current', 'events',
        'history', 'setting', 'export', 'help', 'quit', 'exit'
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

        # Command completion - when no space or typing command
        if not words or (len(words) == 1 and ' ' not in text):
            prefix = text.strip()
            for cmd in self.COMMANDS:
                if cmd.startswith(prefix):
                    yield Completion(
                        cmd,
                        start_position=-len(prefix),
                        display_meta=self._get_command_help(cmd)
                    )
            return

        # Get command and check for argument completion
        command = words[0]

        # cycle command - complete with count or events
        if command == 'cycle':
            # If we have only "cycle " or typing first argument
            if len(words) == 1 or (len(words) == 2 and not text.endswith(' ')):
                # Suggest count numbers and events
                prefix = words[1] if len(words) == 2 else ''

                # Suggest common count values
                for count in ['1', '5', '10', '20', '50', '100']:
                    if count.startswith(prefix):
                        yield Completion(
                            count,
                            start_position=-len(prefix),
                            display_meta='cycle count'
                        )

                # Also suggest events
                events = self._get_current_events()
                for event in events:
                    if event.startswith(prefix):
                        yield Completion(
                            event,
                            start_position=-len(prefix),
                            display_meta='event name'
                        )
            else:
                # After count or additional events
                prefix = words[-1] if not text.endswith(' ') else ''
                events = self._get_current_events()
                for event in events:
                    if event.startswith(prefix):
                        yield Completion(
                            event,
                            start_position=-len(prefix),
                            display_meta='event name'
                        )

        # history command - complete with count or 'all'
        elif command == 'history':
            if len(words) == 1 or (len(words) == 2 and not text.endswith(' ')):
                prefix = words[1] if len(words) == 2 else ''

                # Suggest 'all' keyword
                if 'all'.startswith(prefix):
                    yield Completion(
                        'all',
                        start_position=-len(prefix),
                        display_meta='show all history'
                    )

                # Suggest common count values
                for count in ['5', '10', '20', '50', '100']:
                    if count.startswith(prefix):
                        yield Completion(
                            count,
                            start_position=-len(prefix),
                            display_meta='history count'
                        )

        # setting command - complete with keys and values
        elif command == 'setting':
            setting_keys = ['table_max_rows', 'history_size', 'color', 'log_level']

            # First argument - setting key
            if len(words) == 1 or (len(words) == 2 and not text.endswith(' ')):
                prefix = words[1] if len(words) == 2 else ''
                for key in setting_keys:
                    if key.startswith(prefix):
                        yield Completion(
                            key,
                            start_position=-len(prefix),
                            display_meta=self._get_setting_help(key)
                        )

            # Second argument - setting value
            elif len(words) >= 2:
                setting_key = words[1]
                prefix = words[2] if len(words) == 3 and not text.endswith(' ') else ''

                # Suggest values based on setting key
                if setting_key == 'log_level':
                    for level in self.LOG_LEVELS:
                        if level.startswith(prefix):
                            yield Completion(
                                level,
                                start_position=-len(prefix),
                                display_meta='log level'
                            )
                elif setting_key == 'color':
                    for value in ['on', 'off', 'true', 'false']:
                        if value.startswith(prefix):
                            yield Completion(
                                value,
                                start_position=-len(prefix),
                                display_meta='color setting'
                            )
                elif setting_key in ['table_max_rows', 'history_size']:
                    # Suggest common numeric values
                    for value in ['10', '20', '50', '100', '200', '500', '1000']:
                        if value.startswith(prefix):
                            yield Completion(
                                value,
                                start_position=-len(prefix),
                                display_meta='numeric value'
                            )

        # export command - complete with file extensions
        elif command == 'export':
            if len(words) == 1 or (len(words) == 2 and not text.endswith(' ')):
                prefix = words[1] if len(words) == 2 else ''

                # Suggest common filenames with extensions
                for ext in ['.csv', '.json', '.yaml', '.jsonl']:
                    filename = f'history{ext}'
                    if filename.startswith(prefix):
                        yield Completion(
                            filename,
                            start_position=-len(prefix),
                            display_meta=f'{ext[1:].upper()} format'
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
            'export': 'Export history to file',
            'help': 'Show help',
            'quit': 'Exit simulator',
            'exit': 'Exit simulator',
        }
        return help_map.get(cmd, '')

    def _get_setting_help(self, key: str) -> str:
        """
        Get help text for a setting key.

        :param key: The setting key
        :type key: str
        :return: Help text
        :rtype: str
        """
        help_map = {
            'table_max_rows': 'max rows in tables (default: 20)',
            'history_size': 'max history entries (default: 100)',
            'color': 'enable/disable colors (on/off)',
            'log_level': 'logging level (debug/info/warning/error/off)',
        }
        return help_map.get(key, '')

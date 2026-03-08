"""
State display formatting for the simulation REPL.

This module provides the StateDisplay class for formatting state machine
information with ANSI color support for terminal output.
"""

import os
import sys
from typing import List, Tuple, Optional


class StateDisplay:
    """
    Formatter for displaying state machine information in the terminal.

    This class handles formatting of current state, variables, and events
    with ANSI color support. Colors are automatically disabled on terminals
    that don't support them.

    :ivar use_color: Whether to use ANSI color codes
    :vartype use_color: bool
    """

    # ANSI color codes - compatible with both light and dark themes
    COLORS = {
        'reset': '\033[0m',
        'bold': '\033[1m',
        'blue': '\033[94m',  # Blue - labels
        'green': '\033[92m',  # Green - success/normal state
        'yellow': '\033[93m',  # Yellow - variable names
        'red': '\033[91m',  # Red - errors
        'cyan': '\033[96m',  # Cyan - values
        'gray': '\033[90m',  # Gray - secondary info
    }

    def __init__(self, use_color: bool = True):
        """
        Initialize the state display formatter.

        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        """
        # Check if colors should be used
        self.use_color = use_color and self._supports_color()

    def _supports_color(self) -> bool:
        """
        Detect if the terminal supports ANSI colors.

        :return: True if colors are supported
        :rtype: bool
        """
        return (
            hasattr(sys.stdout, 'isatty') and sys.stdout.isatty() and
            'TERM' in os.environ and os.environ['TERM'] != 'dumb'
        )

    def _colorize(self, text: str, color: str) -> str:
        """
        Apply ANSI color to text.

        :param text: The text to colorize
        :type text: str
        :param color: The color name from COLORS dict
        :type color: str
        :return: Colorized text or plain text if colors disabled
        :rtype: str
        """
        if not self.use_color:
            return text
        return f"{self.COLORS.get(color, '')}{text}{self.COLORS['reset']}"

    def format_current_state(self, runtime) -> str:
        """
        Format current state and variable information.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :return: Formatted state and variables display
        :rtype: str
        """
        lines = []

        # Current state
        try:
            if runtime.current_state:
                state_text = '.'.join(runtime.current_state.path)
                state_label = self._colorize("Current State:", 'blue')
                state_value = self._colorize(state_text, 'green')
                lines.append(f"{state_label} {state_value}")
            else:
                state_label = self._colorize("Current State:", 'blue')
                state_value = self._colorize("(terminated)", 'red')
                lines.append(f"{state_label} {state_value}")
        except IndexError:
            # Runtime has ended
            state_label = self._colorize("Current State:", 'blue')
            state_value = self._colorize("(terminated)", 'red')
            lines.append(f"{state_label} {state_value}")

        # Variables
        if runtime.vars:
            var_label = self._colorize("Variables:", 'blue')
            lines.append(var_label)
            for name, value in sorted(runtime.vars.items()):
                name_colored = self._colorize(name, 'yellow')
                value_colored = self._colorize(str(value), 'cyan')
                lines.append(f"  {name_colored} = {value_colored}")

        return "\n".join(lines)

    def format_events(self, events: List[Tuple[str, Optional[str]]]) -> str:
        """
        Format event list.

        :param events: List of (full_path, short_name) tuples
        :type events: List[Tuple[str, Optional[str]]]
        :return: Formatted events display
        :rtype: str
        """
        if not events:
            return self._colorize("No events available in current state", 'gray')

        lines = []
        lines.append(self._colorize("Available Events:", 'blue'))

        for full_path, short_name in events:
            if short_name:
                full_colored = self._colorize(full_path, 'cyan')
                short_colored = self._colorize(short_name, 'green')
                lines.append(f"  • {short_colored} ({full_colored})")
            else:
                event_colored = self._colorize(full_path, 'green')
                lines.append(f"  • {event_colored}")

        return "\n".join(lines)

    def log(self, message: str, level: str = "info"):
        """
        Output log message with level-based coloring.

        :param message: The log message
        :type message: str
        :param level: Log level (debug, info, warning, error), defaults to "info"
        :type level: str, optional
        """
        color_map = {
            'debug': 'gray',
            'info': 'cyan',
            'warning': 'yellow',
            'error': 'red',
        }
        color = color_map.get(level, 'reset')
        prefix = f"[{level.upper()}]" if level != 'info' else ""
        print(f"{self._colorize(prefix, color)} {message}".strip())

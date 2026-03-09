"""
Entry-side logging presentation helpers for simulate CLI.

This module keeps runtime logging on the Python standard library while adding
an optional Rich-based presentation layer for CLI output.
"""

import logging
import sys

try:
    from rich.console import Console
    from rich.highlighter import Highlighter, ReprHighlighter, RegexHighlighter
    from rich.logging import RichHandler
    from rich.theme import Theme
except ImportError:  # pragma: no cover - exercised via fallback path
    Console = None
    Highlighter = None
    ReprHighlighter = None
    RegexHighlighter = None
    RichHandler = None
    Theme = None


class SimulatePlainLogHandler(logging.StreamHandler):
    """
    Plain stderr log handler for simulate CLI.

    :param use_color: Whether colored terminal output is enabled.
    :type use_color: bool
    """

    def __init__(self, use_color: bool = True):
        super().__init__(sys.stderr)
        self.use_color = use_color


class _SimulateRegexHighlighter(RegexHighlighter):
    """Regex-based highlighter for simulate log output."""

    highlights = [
        r"(?P<level_debug>\[DEBUG\])",
        r"(?P<level_info>\[INFO\])",
        r"(?P<level_warning>\[WARNING\])",
        r"(?P<level_error>\[ERROR\])",
        r"(?P<level_critical>\[CRITICAL\])",
        r"(?P<cycle_complete>Cycle\s+\d+\s+completed\s+successfully)",
        r"Execute\s+transition:\s+(?P<transition_path>[^\n]+?\s->\s[^\n]+?\(event=[^)]+\))",
    ]

    base_style = "simulate."


class SimulateLogHighlighter(Highlighter):
    """Combine Rich repr highlighting with simulate-specific regex highlighting."""

    def __init__(self):
        self._repr = ReprHighlighter() if ReprHighlighter is not None else None
        self._regex = _SimulateRegexHighlighter() if RegexHighlighter is not None else None

    def highlight(self, text) -> None:
        if self._repr is not None:
            self._repr.highlight(text)
        if self._regex is not None:
            self._regex.highlight(text)


class SimulateRichLogHandler(RichHandler):
    """
    Rich-based stderr log handler for simulate CLI.

    :param use_color: Whether colored terminal output is enabled.
    :type use_color: bool
    """

    def __init__(self, use_color: bool = True):
        console = Console(
            stderr=True,
            no_color=not use_color,
            soft_wrap=True,
            theme=Theme({
                'simulate.level_debug': 'dim cyan',
                'simulate.level_info': 'green',
                'simulate.level_warning': 'yellow',
                'simulate.level_error': 'bold red',
                'simulate.level_critical': 'bold white on red',
                'simulate.cycle_complete': 'underline bold cyan',
                'simulate.transition_path': 'underline green',
            }) if Theme is not None else None,
        )
        super().__init__(
            console=console,
            show_time=False,
            show_level=False,
            show_path=False,
            markup=False,
            rich_tracebacks=False,
            highlighter=SimulateLogHighlighter() if Highlighter is not None else None,
        )
        self.use_color = use_color


class SimulateCliFormatter(logging.Formatter):
    """
    Formatter for simulate CLI log messages.

    The entry layer owns all simulate CLI formatting, using the compact form
    ``[%(levelname)s] %(message)s`` requested by the user.
    """

    def __init__(self):
        super().__init__('[%(levelname)s] %(message)s')


def create_simulate_log_handler(use_color: bool = True) -> logging.Handler:
    """
    Create a CLI log handler for simulate output.

    Uses Rich when available and colors are enabled. Falls back to a plain
    standard-library handler otherwise.

    :param use_color: Whether colored terminal output is enabled.
    :type use_color: bool
    :return: Configured logging handler.
    :rtype: logging.Handler
    """
    if use_color and RichHandler is not None and Console is not None:
        handler = SimulateRichLogHandler(use_color=use_color)
    else:
        handler = SimulatePlainLogHandler(use_color=use_color)

    handler.setFormatter(SimulateCliFormatter())
    return handler


def configure_simulate_cli_logger(logger: logging.Logger, use_color: bool = True) -> None:
    """
    Configure a runtime logger for CLI presentation.

    This function replaces existing handlers with a single CLI-facing handler so
    output is not duplicated when multiple command processors are created.

    :param logger: Runtime logger to configure.
    :type logger: logging.Logger
    :param use_color: Whether colored terminal output is enabled.
    :type use_color: bool
    :return: ``None``.
    :rtype: None
    """
    for handler in list(logger.handlers):
        logger.removeHandler(handler)

    logger.addHandler(create_simulate_log_handler(use_color=use_color))
    logger.propagate = False

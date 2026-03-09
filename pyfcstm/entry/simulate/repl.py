"""
Enhanced REPL (Read-Eval-Print Loop) for interactive simulation.

This module provides an interactive command-line interface with auto-completion,
history, and suggestions using prompt_toolkit.
"""

import os
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.history import FileHistory
from prompt_toolkit.auto_suggest import AutoSuggestFromHistory
from prompt_toolkit.styles import Style

from .commands import CommandProcessor
from .completer import SimulationCompleter


class SimulationREPL:
    """
    Enhanced REPL for interactive state machine simulation.

    This class provides a rich command-line interface with auto-completion,
    command history, and auto-suggestions using prompt_toolkit.

    :param runtime: The simulation runtime instance
    :type runtime: SimulationRuntime
    :param use_color: Whether to use ANSI colors, defaults to True
    :type use_color: bool, optional
    :ivar command_processor: Command processor instance
    :vartype command_processor: CommandProcessor
    :ivar session: Prompt toolkit session
    :vartype session: PromptSession
    """

    def __init__(self, runtime, use_color: bool = True):
        """
        Initialize the REPL with prompt_toolkit features.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        """
        self.runtime = runtime
        self.command_processor = CommandProcessor(runtime, use_color=use_color)
        self.history = self._get_history()
        self.session = PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromHistory(),
            completer=SimulationCompleter(runtime),
            enable_history_search=True,
            style=self._get_style(),
        )

    def _get_history(self) -> FileHistory:
        """
        Get cross-platform history file path.

        Creates the history directory if it doesn't exist.

        :return: FileHistory instance
        :rtype: FileHistory
        """
        if os.name == 'nt':  # Windows
            history_dir = Path(os.environ.get('APPDATA', Path.home())) / 'pyfcstm'
        else:  # Unix-like (Linux, macOS)
            history_dir = Path.home() / '.config' / 'pyfcstm'

        history_dir.mkdir(parents=True, exist_ok=True)
        return FileHistory(str(history_dir / 'simulate_history'))

    def _get_style(self) -> Style:
        """
        Get prompt style compatible with both light and dark themes.

        :return: Prompt style
        :rtype: Style
        """
        return Style.from_dict({
            'prompt': '#0066cc bold',  # Blue prompt
            'suggestion': 'fg:#888888',  # Gray suggestions
        })

    def run(self):
        """
        Run the REPL main loop with prompt_toolkit.

        This method runs an infinite loop reading user input with auto-completion
        and history support until the user exits with /quit or /exit, or sends
        EOF (Ctrl+D).

        Ctrl+C (KeyboardInterrupt) cancels the current input but does not exit.
        Ctrl+R enables reverse history search.
        """
        while True:
            try:
                user_input = self.session.prompt('simulate> ')
                if not user_input.strip():
                    continue

                result = self.command_processor.process(user_input)
                if result.should_exit:
                    if result.output:
                        print(result.output)
                    break

                if result.output:
                    print(result.output)

            except KeyboardInterrupt:
                # Ctrl+C - continue, don't exit
                print()
                continue
            except EOFError:
                # Ctrl+D - exit gracefully
                print("\nGoodbye!")
                break


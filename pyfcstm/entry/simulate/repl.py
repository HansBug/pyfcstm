"""
Enhanced REPL (Read-Eval-Print Loop) for interactive simulation.

This module provides an interactive command-line interface with auto-completion,
history, and intelligent suggestions using prompt_toolkit.
"""

import os
from pathlib import Path

from prompt_toolkit import PromptSession
from prompt_toolkit.auto_suggest import AutoSuggest, Suggestion
from prompt_toolkit.document import Document
from prompt_toolkit.history import FileHistory
from prompt_toolkit.styles import Style

from .commands import CommandProcessor
from .completer import SimulationCompleter


class AutoSuggestFromCompleter(AutoSuggest):
    """
    Auto-suggest implementation that uses the completer to provide suggestions.

    This class provides inline suggestions (gray text) based on the completer's
    completions, showing the first matching completion as you type. The suggestion
    only shows the remaining part of the completion, not the already-typed text.

    :param completer: The completer to use for suggestions
    :type completer: SimulationCompleter
    """

    def __init__(self, completer):
        """
        Initialize the auto-suggester.

        :param completer: The completer to use for suggestions
        :type completer: SimulationCompleter
        """
        self.completer = completer

    def get_suggestion(self, buffer, document):
        """
        Get suggestion for the current input.

        Returns only the remaining part of the completion that hasn't been typed yet.
        For example, if user typed 'cy' and completion is 'cycle', this returns 'cle'.

        :param buffer: The input buffer
        :param document: The current document
        :type document: Document
        :return: Suggestion or None
        :rtype: Suggestion or None
        """
        # Get completions from the completer
        completions = list(self.completer.get_completions(document, None))

        if completions:
            # Get the first completion
            first_completion = completions[0]

            # The completion.text is the full word to insert
            # The completion.start_position tells us how many characters back to replace
            # We need to figure out what part is already typed
            text_before_cursor = document.text_before_cursor

            # Calculate what's already been typed that matches the completion
            # start_position is negative, indicating how far back to go
            if first_completion.start_position < 0:
                # The prefix is the part that's already typed
                prefix_len = -first_completion.start_position
                # Get the last prefix_len characters
                if prefix_len <= len(text_before_cursor):
                    typed_prefix = text_before_cursor[-prefix_len:]
                    # The suggestion should be the completion minus what's already typed
                    if first_completion.text.startswith(typed_prefix):
                        # Return only the part that needs to be added
                        remaining = first_completion.text[len(typed_prefix):]
                        if remaining:
                            return Suggestion(remaining)
                    else:
                        # If it doesn't start with the prefix, just return the full text
                        return Suggestion(first_completion.text)
            else:
                # If start_position is 0 or positive, just return the full text
                return Suggestion(first_completion.text)

        return None


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

    def __init__(self, runtime, state_machine=None, use_color: bool = True):
        """
        Initialize the REPL with prompt_toolkit features.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param state_machine: The state machine model (required for init command)
        :type state_machine: StateMachine, optional
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        """
        self.runtime = runtime
        self.state_machine = state_machine if state_machine is not None else runtime.state_machine
        self.command_processor = CommandProcessor(runtime, state_machine=self.state_machine, use_color=use_color)
        self.history = self._get_history()
        self.completer = SimulationCompleter(runtime)
        self.session = PromptSession(
            history=self.history,
            auto_suggest=AutoSuggestFromCompleter(self.completer),
            completer=self.completer,
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

"""
Simple REPL (Read-Eval-Print Loop) for interactive simulation.

This module provides a basic interactive command-line interface for the
state machine simulator without external dependencies.
"""

from .commands import CommandProcessor


class SimulationREPL:
    """
    Simple REPL for interactive state machine simulation.

    This class provides a basic command-line interface using Python's built-in
    input() function. For enhanced features like auto-completion and history,
    use the prompt_toolkit-based version.

    :param runtime: The simulation runtime instance
    :type runtime: SimulationRuntime
    :param use_color: Whether to use ANSI colors, defaults to True
    :type use_color: bool, optional
    :ivar command_processor: Command processor instance
    :vartype command_processor: CommandProcessor
    """

    def __init__(self, runtime, use_color: bool = True):
        """
        Initialize the REPL.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        """
        self.runtime = runtime
        self.command_processor = CommandProcessor(runtime, use_color=use_color)

    def run(self):
        """
        Run the REPL main loop.

        This method runs an infinite loop reading user input and executing
        commands until the user exits with /quit or /exit, or sends EOF (Ctrl+D).

        Ctrl+C (KeyboardInterrupt) cancels the current input but does not exit.
        """
        while True:
            try:
                user_input = input('simulate> ')
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

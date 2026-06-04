"""
Batch command processor for non-interactive execution.

This module provides batch processing capabilities for executing multiple
commands in sequence without user interaction.
"""

import sys
from typing import Callable

from .commands import CommandProcessor


def create_cross_platform_output_func() -> Callable[[str], None]:
    """
    Create a cross-platform output function that handles Unicode correctly.

    On Windows, writes directly to binary stdout with UTF-8 encoding to avoid
    cp1252 encoding issues. On other platforms, uses standard print.

    :return: Output function that takes a string and prints it
    :rtype: Callable[[str], None]
    """
    if sys.platform == 'win32':  # pragma: no cover -- Windows CI runner only.
        # On Windows the default ``print()`` path goes through the
        # locale codepage (cp1252) which mangles non-ASCII characters
        # produced by REPL display widgets. We bypass it by writing
        # UTF-8 bytes straight to the binary stdout buffer. The inner
        # try/except is the documented fall-back for environments
        # where stdout has no ``buffer`` attribute or refuses the
        # encode (UnicodeEncodeError); both are platform-specific and
        # cannot be exercised from a Linux CI host.
        def windows_output(text: str) -> None:
            """Output function for Windows with UTF-8 encoding."""
            try:
                if hasattr(sys.stdout, 'buffer'):
                    sys.stdout.buffer.write(text.encode('utf-8'))
                    sys.stdout.buffer.write(b'\n')
                    sys.stdout.flush()
                else:
                    print(text, flush=True)
            except (UnicodeEncodeError, AttributeError):
                print(text, flush=True)

        return windows_output
    else:
        def standard_output(text: str) -> None:
            """Standard output function for non-Windows platforms."""
            print(text, flush=True)

        return standard_output


class BatchProcessor:
    """
    Processor for executing batch commands.

    This class handles parsing and execution of semicolon-separated command
    strings for non-interactive batch processing.

    :param runtime: The simulation runtime instance
    :type runtime: SimulationRuntime
    :param use_color: Whether to use ANSI colors, defaults to True
    :type use_color: bool, optional
    :ivar command_processor: Command processor instance
    :vartype command_processor: CommandProcessor
    """

    def __init__(self, runtime, state_machine=None, use_color: bool = True, output_func: Callable[[str], None] = None):
        """
        Initialize the batch processor.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param state_machine: The state machine model (required for init command)
        :type state_machine: StateMachine, optional
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        :param output_func: Function to output text, defaults to cross-platform output
        :type output_func: Callable[[str], None], optional
        """
        self.runtime = runtime
        self.state_machine = state_machine if state_machine is not None else runtime.state_machine
        self.command_processor = CommandProcessor(
            runtime,
            state_machine=self.state_machine,
            use_color=use_color,
            runtime_replaced_callback=self._replace_runtime,
        )
        self.output_func = output_func or create_cross_platform_output_func()

    def _replace_runtime(self, runtime) -> None:
        """
        Synchronize the batch-level runtime reference after command rebuilds.

        :param runtime: Replacement runtime created by the command processor.
        :type runtime: SimulationRuntime
        :return: ``None``.
        :rtype: None
        """
        self.runtime = runtime

    def execute_commands(self, command_string: str) -> None:
        """
        Execute a batch command string with clear command separators.

        Commands are separated by semicolons. Each command's output is printed
        immediately to maintain proper ordering with log messages.

        :param command_string: Semicolon-separated command string
        :type command_string: str

        Example::

            >>> processor.execute_commands("current; cycle Start; current")
            # Outputs each command result immediately
        """
        commands = [cmd.strip() for cmd in command_string.split(';') if cmd.strip()]

        for i, command in enumerate(commands):
            # Add command header
            separator = "─" * 60
            command_header = f">>> {command}"
            self.output_func(f"{separator}\n{command_header}\n{separator}")

            result = self.command_processor.process(command)
            if result.output:
                self.output_func(result.output)

            # Add spacing between commands
            if i < len(commands) - 1:
                self.output_func("")

            if result.should_exit:
                break

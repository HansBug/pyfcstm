"""
Batch command processor for non-interactive execution.

This module provides batch processing capabilities for executing multiple
commands in sequence without user interaction.
"""

import sys
from typing import List, Callable

from .commands import CommandProcessor


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

    def __init__(self, runtime, use_color: bool = True, output_func: Callable[[str], None] = None):
        """
        Initialize the batch processor.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        :param output_func: Function to output text, defaults to print to stdout
        :type output_func: Callable[[str], None], optional
        """
        self.runtime = runtime
        self.command_processor = CommandProcessor(runtime, use_color=use_color)
        self.output_func = output_func or self._default_output

    def _default_output(self, text: str) -> None:
        """
        Default output function that prints to stdout.

        :param text: Text to output
        :type text: str
        """
        print(text, flush=True)

    def execute_commands(self, command_string: str) -> None:
        """
        Execute a batch command string with clear command separators.

        Commands are separated by semicolons. The '/' prefix is automatically
        added if missing. Each command's output is printed immediately to maintain
        proper ordering with log messages.

        :param command_string: Semicolon-separated command string
        :type command_string: str

        Example::

            >>> processor.execute_commands("current; cycle Start; current")
            # Outputs each command result immediately
        """
        commands = [cmd.strip() for cmd in command_string.split(';') if cmd.strip()]

        for i, command in enumerate(commands):
            # Automatically add / prefix if missing
            if not command.startswith('/'):
                command = '/' + command

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

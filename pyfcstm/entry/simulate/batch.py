"""
Batch command processor for non-interactive execution.

This module provides batch processing capabilities for executing multiple
commands in sequence without user interaction.
"""

from typing import List

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

    def __init__(self, runtime, use_color: bool = True):
        """
        Initialize the batch processor.

        :param runtime: The simulation runtime instance
        :type runtime: SimulationRuntime
        :param use_color: Whether to use ANSI colors, defaults to True
        :type use_color: bool, optional
        """
        self.runtime = runtime
        self.command_processor = CommandProcessor(runtime, use_color=use_color)

    def execute_commands(self, command_string: str) -> str:
        """
        Execute a batch command string.

        Commands are separated by semicolons. The '/' prefix is automatically
        added if missing.

        :param command_string: Semicolon-separated command string
        :type command_string: str
        :return: Combined output from all commands
        :rtype: str

        Example::

            >>> processor.execute_commands("current; cycle Start; current")
            "Current State: System.Idle\\n...\\nCurrent State: System.Running\\n..."
        """
        commands = [cmd.strip() for cmd in command_string.split(';') if cmd.strip()]
        results = []

        for command in commands:
            # Automatically add / prefix if missing
            if not command.startswith('/'):
                command = '/' + command

            result = self.command_processor.process(command)
            if result.output:
                results.append(result.output)

            if result.should_exit:
                break

        return '\n\n'.join(results)

"""
CLI entry point for the interactive state machine simulator.

This module provides the simulate subcommand for the pyfcstm CLI tool.
"""

from pathlib import Path

import click

from .batch import BatchProcessor, create_cross_platform_output_func
from .repl import SimulationREPL


def _add_simulate_subcommand(cli: click.Group) -> click.Group:
    """
    Add the simulate subcommand to the CLI.

    :param cli: The Click CLI group
    :type cli: click.Group
    :return: The modified CLI group
    :rtype: click.Group
    """

    @cli.command(
        'simulate',
        help='Interactive state machine simulator',
    )
    @click.option(
        '-i', '--input-code', 'input_code_file',
        type=str, required=True,
        help='State machine DSL code file path',
    )
    @click.option(
        '-e', '--execute', 'batch_commands',
        type=str, default=None,
        help='Batch commands (semicolon-separated), e.g.: "current; cycle Start; current"',
    )
    @click.option(
        '--no-color', is_flag=True,
        help='Disable color output',
    )
    def simulate(input_code_file: str, batch_commands: str, no_color: bool) -> None:
        """
        Run the interactive state machine simulator.

        This command loads a DSL file, parses it into a state machine model,
        and provides an interactive REPL or batch execution mode.

        :param input_code_file: Path to the DSL file
        :type input_code_file: str
        :param batch_commands: Optional batch command string
        :type batch_commands: str
        :param no_color: Whether to disable color output
        :type no_color: bool
        """
        # Import here to avoid circular dependencies
        from ...dsl import parse_with_grammar_entry
        from ...model import parse_dsl_node_to_state_machine
        from ...simulate import SimulationRuntime
        from ...utils import auto_decode

        # Parse DSL file
        try:
            code = auto_decode(Path(input_code_file).read_bytes())
            ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
            model = parse_dsl_node_to_state_machine(ast_node, path=input_code_file)
        except Exception as e:
            click.echo(f"Failed to parse DSL file: {e}", err=True)
            return

        # Create runtime
        runtime = SimulationRuntime(model)

        # Batch mode
        if batch_commands:
            processor = BatchProcessor(runtime, state_machine=model, use_color=not no_color)
            processor.execute_commands(batch_commands)
            return

        # Interactive mode
        repl = SimulationREPL(runtime, state_machine=model, use_color=not no_color)

        # Print banner with Unicode box-drawing characters
        banner_lines = [
            "╔" + "═" * 58 + "╗",
            "║  State Machine Interactive Simulator" + " " * 21 + "║",
            "╟" + "─" * 58 + "╢",
            "║  Type 'help' to see available commands" + " " * 19 + "║",
            "╚" + "═" * 58 + "╝",
            ""
        ]

        # Use cross-platform output function for banner
        output_func = create_cross_platform_output_func()
        for line in banner_lines:
            output_func(line)

        repl.run()

    return cli

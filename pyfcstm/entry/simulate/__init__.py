"""
CLI entry point for the interactive state machine simulator.

This module provides the simulate subcommand for the pyfcstm CLI tool.
"""

import click
from pathlib import Path

from .repl import SimulationREPL
from .batch import BatchProcessor


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
            model = parse_dsl_node_to_state_machine(ast_node)
        except Exception as e:
            click.echo(f"Failed to parse DSL file: {e}", err=True)
            return

        # Create runtime
        runtime = SimulationRuntime(model)

        # Batch mode
        if batch_commands:
            processor = BatchProcessor(runtime, use_color=not no_color)
            result = processor.execute_commands(batch_commands)
            click.echo(result)
            return

        # Interactive mode
        repl = SimulationREPL(runtime, use_color=not no_color)
        click.echo("╔" + "═" * 58 + "╗")
        click.echo("║  State Machine Interactive Simulator" + " " * 21 + "║")
        click.echo("╟" + "─" * 58 + "╢")
        click.echo("║  Type /help to see available commands" + " " * 19 + "║")
        click.echo("╚" + "═" * 58 + "╝")
        click.echo()
        repl.run()

    return cli

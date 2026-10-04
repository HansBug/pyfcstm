"""
CLI entry point for the interactive state machine simulator.

This module provides the simulate subcommand for the pyfcstm CLI tool.
"""

import json
from functools import partial

import click

from .batch import BatchProcessor, create_cross_platform_output_func
from .repl import SimulationREPL
from .commands import CommandProcessor
from .inputs import _CommandInput, _assignments


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
    @click.option('--diagnostics', is_flag=True, help='Capture and display candidate decision evidence.')
    @click.option('--diagnostics-format', type=click.Choice(['text', 'jsonl']), default='text',
                  help='Diagnostic output; JSONL requires --diagnostics and batch --execute.')
    @click.option('--param', 'parameter_assignments', multiple=True, metavar='NAME=VALUE',
                  help='Set an immutable parameter at construction; repeat for multiple parameters.')
    def simulate(input_code_file: str, batch_commands: str, no_color: bool,
                 diagnostics: bool, diagnostics_format: str, parameter_assignments) -> None:
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
        :param diagnostics: Capture candidate evidence for each cycle.
        :type diagnostics: bool
        :param diagnostics_format: Human ``text`` or batch-only ``jsonl``.
        :type diagnostics_format: str
        :param parameter_assignments: Repeated construction-time name=value pairs.
        """
        # Import here to avoid circular dependencies
        from ...dsl.error import GrammarParseError
        from ...model import load_state_machine_from_file
        from ...simulate import SimulationRuntime, SimulationRuntimeInputSourceError
        from ...utils.validate import ModelValidationError

        if diagnostics_format == 'jsonl' and not batch_commands:
            raise click.UsageError('JSONL diagnostics require batch --execute.')
        if diagnostics_format == 'jsonl' and not diagnostics:
            raise click.UsageError('JSONL output requires --diagnostics.')
        # Use the existing file loader so imported models retain their origins.
        try:
            model = load_state_machine_from_file(input_code_file)
        except (OSError, GrammarParseError, ModelValidationError, UnicodeDecodeError) as e:
            # OSError: input file missing / unreadable (Path.read_bytes).
            # GrammarParseError: DSL syntax issues from ANTLR.
            # ModelValidationError: semantic checks during AST -> model.
            # UnicodeDecodeError: auto_decode could not pick a working codec.
            # Programmer bugs (TypeError, AttributeError, KeyError, ...) and
            # unrelated runtime errors deliberately propagate.
            raise click.ClickException(f"Failed to parse DSL file: {e}") from e

        # Create runtime
        input_source = _CommandInput(tuple(model.inputs))
        try:
            parameters = _assignments(parameter_assignments, CommandProcessor._parse_value)
            runtime = SimulationRuntime(model, parameters=parameters, input_source=input_source)
        except (ValueError, SimulationRuntimeInputSourceError) as err:
            # ValueError: malformed assignments or invalid construction parameters.
            # SimulationRuntimeInputSourceError: rejected input-source contract.
            raise click.ClickException(str(err)) from err

        # Batch mode
        if batch_commands:
            output_func = None
            diagnostic_output = None
            if diagnostics_format == 'jsonl':
                output_func = partial(click.echo, err=True)

                def diagnostic_output(report):
                    click.echo(json.dumps(report.to_dict(), ensure_ascii=False))
            processor = BatchProcessor(
                runtime, state_machine=model, use_color=not no_color,
                output_func=output_func, input_source=input_source,
                diagnostics=diagnostics, diagnostic_output=diagnostic_output,
            )
            exit_code = processor.execute_commands(batch_commands)
            if exit_code:
                raise click.exceptions.Exit(exit_code)
            return

        # Interactive mode
        repl = SimulationREPL(
            runtime, state_machine=model, use_color=not no_color,
            input_source=input_source, diagnostics=diagnostics,
        )

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

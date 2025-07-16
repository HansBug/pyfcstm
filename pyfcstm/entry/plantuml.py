"""
State Machine DSL to PlantUML Converter Module

This module provides functionality to convert state machine DSL code into PlantUML format.
It includes a command-line interface for easy conversion of state machine DSL files
to PlantUML code, which can be used to generate visual state machine diagrams.
"""

import pathlib

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..utils import auto_decode


def _add_plantuml_subcommand(cli: click.Group) -> click.Group:
    """
    Add the 'plantuml' subcommand to the provided CLI group.

    This function adds a subcommand that converts state machine DSL code to PlantUML format.
    The subcommand reads DSL code from a file, parses it into a state machine model,
    and outputs the corresponding PlantUML code.

    :param cli: The click Group to which the subcommand should be added
    :type cli: click.Group

    :return: The modified CLI group with the plantuml subcommand added
    :rtype: click.Group

    Example::

        >>> from click import Group
        >>> cli = Group()
        >>> cli = _add_plantuml_subcommand(cli)
    """

    @cli.command('plantuml', help='Create Plantuml code of a given state machine DSL code.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-code', 'input_code_file', type=str, required=True,
                  help='Input code file of state machine DSL.')
    @click.option('-o', '--output', 'output_file', type=str, default=None,
                  help='Output directory of the code generation, output to stdout when not assigned.')
    def plantuml(input_code_file, output_file):
        """
        Convert state machine DSL code to PlantUML format.

        This command reads state machine DSL code from the specified input file,
        parses it into a state machine model, and outputs the corresponding PlantUML code
        either to a file or to stdout.

        :param input_code_file: Path to the file containing state machine DSL code
        :type input_code_file: str
        :param output_file: Path to the output file for PlantUML code (stdout if None)
        :type output_file: str or None
        """
        code = auto_decode(pathlib.Path(input_code_file).read_bytes())
        ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)
        if output_file is not None:
            with open(output_file, 'w') as f:
                f.write(model.to_plantuml())
        else:
            click.echo(model.to_plantuml())

    return cli

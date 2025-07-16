"""
State Machine Code Generation Module

This module provides command line interface functionality for generating code from a state machine DSL.
It includes functionality to parse DSL code, convert it to a state machine model, and render the model
using templates to generate output code.
"""

import pathlib

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..render import StateMachineCodeRenderer
from ..utils import auto_decode


def _add_generate_subcommand(cli: click.Group) -> click.Group:
    """
    Add the 'generate' subcommand to the CLI group.

    This function adds a 'generate' subcommand to the provided CLI group that allows users to
    generate code from a state machine DSL file using specified templates.

    :param cli: The click Group object to which the subcommand will be added
    :type cli: click.Group

    :return: The modified CLI group with the 'generate' subcommand added
    :rtype: click.Group

    Example::

        >>> app = click.Group()
        >>> app = _add_generate_subcommand(app)
    """

    @cli.command('generate', help='Generate code with template of a given state machine DSL code.',
                 context_settings=CONTEXT_SETTINGS)
    @click.option('-i', '--input-code', 'input_code_file', type=str, required=True,
                  help='Input code file of state machine DSL.')
    @click.option('-t', '--template-dir', 'template_dir', type=str, required=True,
                  help='Template directory of the code generation.')
    @click.option('-o', '--output-dir', 'output_dir', type=str, required=True,
                  help='Output directory of the code generation.')
    @click.option('--clear', '--clear-directory', 'clear_directory', type=bool, is_flag=True,
                  help='Clear the destination directory of the output directory.')
    def generate(input_code_file, template_dir, output_dir, clear_directory):
        """
        Generate code from a state machine DSL file using templates.

        This function reads a state machine DSL file, parses it into an AST node,
        converts the AST node to a state machine model, and renders the model using
        templates to generate output code.

        :param input_code_file: Path to the input DSL code file
        :type input_code_file: str

        :param template_dir: Path to the directory containing templates
        :type template_dir: str

        :param output_dir: Path to the directory where generated code will be written
        :type output_dir: str

        :param clear_directory: Whether to clear the output directory before generating code
        :type clear_directory: bool

        :return: None
        """
        code = auto_decode(pathlib.Path(input_code_file).read_bytes())
        ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)

        renderer = StateMachineCodeRenderer(
            template_dir=template_dir,
        )
        renderer.render(
            model,
            output_dir=output_dir,
            clear_previous_directory=clear_directory
        )

    return cli

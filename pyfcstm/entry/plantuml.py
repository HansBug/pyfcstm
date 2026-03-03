"""
State Machine DSL to PlantUML CLI Integration.

This module integrates a PlantUML generator into a Click-based command-line
interface. It provides a subcommand that reads state machine DSL code from a
file, parses it into an internal model, and emits PlantUML text either to a
file or to standard output.

The module is intended to be used as part of a larger CLI application that
manages multiple subcommands. It does not expose any public API directly;
instead, it contributes functionality through the helper function that
registers the subcommand.

.. note::
   The CLI entry point relies on :func:`pyfcstm.dsl.parse.parse_with_grammar_entry`
   and :func:`pyfcstm.model.model.parse_dsl_node_to_state_machine` to build the
   model and assumes the input file contains valid state machine DSL content.

Example::

    >>> import click
    >>> from pyfcstm.entry.plantuml import _add_plantuml_subcommand
    >>> cli = click.Group()
    >>> _add_plantuml_subcommand(cli)  # doctest: +ELLIPSIS
    <...Group...>

"""

import pathlib

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..utils import auto_decode


def _add_plantuml_subcommand(cli: click.Group) -> click.Group:
    """
    Add the ``plantuml`` subcommand to a Click CLI group.

    This function registers a subcommand that converts state machine DSL code
    into PlantUML format. The registered command reads DSL code from a file,
    parses it into a state machine model, and outputs the corresponding
    PlantUML text to a file or stdout.

    :param cli: The Click group to which the subcommand should be added.
    :type cli: click.Group
    :return: The same CLI group instance with the subcommand registered.
    :rtype: click.Group

    Example::

        >>> from click import Group
        >>> cli = Group()
        >>> _add_plantuml_subcommand(cli)  # doctest: +ELLIPSIS
        <...Group...>
    """

    @cli.command(
        'plantuml',
        help='Create Plantuml code of a given state machine DSL code.',
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        '-i',
        '--input-code',
        'input_code_file',
        type=str,
        required=True,
        help='Input code file of state machine DSL.',
    )
    @click.option(
        '-o',
        '--output',
        'output_file',
        type=str,
        default=None,
        help='Output directory of the code generation, output to stdout when not assigned.',
    )
    def plantuml(input_code_file: str, output_file: str | None) -> None:
        """
        Convert state machine DSL code to PlantUML format.

        This command reads DSL code from the specified file, parses it into a
        state machine model, and emits PlantUML text either to the specified
        output file or to stdout when no output path is provided.

        :param input_code_file: Path to the file containing state machine DSL code.
        :type input_code_file: str
        :param output_file: Path to the output file for PlantUML code. If
            ``None``, output is written to stdout.
        :type output_file: str or None
        :return: ``None``. Output is written to a file or stdout.
        :rtype: None

        :raises UnicodeDecodeError: If the input file cannot be decoded by
            :func:`pyfcstm.utils.decode.auto_decode`.
        :raises AttributeError: If the grammar entry name does not exist in the
            DSL parser.
        :raises pyfcstm.dsl.error.GrammarParseError: If parsing fails for the
            provided DSL input.
        :raises SyntaxError: If the parsed DSL contains invalid state machine
            constructs.

        Example::

            >>> # CLI usage example (shell):
            >>> # pyfcstm plantuml -i example.dsl -o example.puml
            >>> pass
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

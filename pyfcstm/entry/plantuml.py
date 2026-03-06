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
from typing import Optional, Tuple, Dict, Union

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..model.plantuml import PlantUMLOptions
from ..utils import auto_decode, parse_key_value_pairs

# Type hints for PlantUMLOptions fields
PLANTUML_OPTION_TYPES: Dict[str, Union[type, str]] = {
    'detail_level': str,
    'show_variable_definitions': bool,
    'variable_display_mode': str,
    'variable_legend_position': str,
    'state_name_format': 'tuple[str, ...]',
    'show_pseudo_state_style': bool,
    'collapse_empty_states': bool,
    'show_lifecycle_actions': bool,
    'show_enter_actions': bool,
    'show_during_actions': bool,
    'show_exit_actions': bool,
    'show_aspect_actions': bool,
    'show_abstract_actions': bool,
    'show_concrete_actions': bool,
    'abstract_action_marker': str,
    'max_action_lines': int,
    'show_transition_guards': bool,
    'show_transition_effects': bool,
    'transition_effect_mode': str,
    'show_events': bool,
    'event_name_format': 'tuple[str, ...]',
    'event_visualization_mode': str,
    'event_legend_position': str,
    'max_depth': int,
    'collapsed_state_marker': str,
    'use_skinparam': bool,
    'use_stereotypes': bool,
}


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
        help='Output file for PlantUML code, output to stdout when not assigned.',
    )
    @click.option(
        '-l',
        '--level',
        'detail_level',
        type=click.Choice(['minimal', 'normal', 'full'], case_sensitive=False),
        default='normal',
        help='Detail level preset (minimal/normal/full). Default: normal.',
    )
    @click.option(
        '-c',
        '--config',
        'config_options',
        multiple=True,
        help='Configuration options in key=value format. Can be specified multiple times. '
             'Example: -c show_events=true -c max_depth=2',
    )
    def plantuml(
        input_code_file: str,
        output_file: Optional[str],
        detail_level: str,
        config_options: Tuple[str, ...],
    ) -> None:
        """
        Convert state machine DSL code to PlantUML format.

        This command reads DSL code from the specified file, parses it into a
        state machine model, and emits PlantUML text either to the specified
        output file or to stdout when no output path is provided.

        The command supports flexible configuration through detail level presets
        and individual option overrides:

        * Use ``-l/--level`` to select a preset (minimal/normal/full)
        * Use ``-c/--config`` to override specific options with key=value pairs

        :param input_code_file: Path to the file containing state machine DSL code.
        :type input_code_file: str
        :param output_file: Path to the output file for PlantUML code. If
            ``None``, output is written to stdout.
        :type output_file: str or None
        :param detail_level: Detail level preset (minimal/normal/full).
        :type detail_level: str
        :param config_options: Tuple of key=value configuration options.
        :type config_options: Tuple[str, ...]
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
        :raises click.BadParameter: If a config option is not in key=value format.

        Example::

            >>> # Basic usage with default settings
            >>> # pyfcstm plantuml -i example.dsl -o example.puml

            >>> # Use minimal detail level
            >>> # pyfcstm plantuml -i example.dsl -l minimal

            >>> # Override specific options
            >>> # pyfcstm plantuml -i example.dsl -c show_events=true -c max_depth=2

            >>> # Combine preset with overrides
            >>> # pyfcstm plantuml -i example.dsl -l full -c max_depth=3 -c event_visualization_mode=color
        """
        # Parse DSL code
        code = auto_decode(pathlib.Path(input_code_file).read_bytes())
        ast_node = parse_with_grammar_entry(code, entry_name='state_machine_dsl')
        model = parse_dsl_node_to_state_machine(ast_node)

        # Parse configuration options with type hints
        parsed_options = parse_key_value_pairs(config_options, type_hints=PLANTUML_OPTION_TYPES)

        # Create PlantUMLOptions with detail level and overrides
        options = PlantUMLOptions(detail_level=detail_level, **parsed_options)

        # Generate PlantUML output
        plantuml_output = model.to_plantuml(options)

        # Write output
        if output_file is not None:
            with open(output_file, 'w') as f:
                f.write(plantuml_output)
        else:
            click.echo(plantuml_output)

    return cli

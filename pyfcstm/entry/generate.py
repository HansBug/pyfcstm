"""
Command-line interface integration for state machine code generation.

This module wires a ``generate`` subcommand into a Click command group so that
users can generate source code from a state machine DSL file. The subcommand
reads the DSL file, parses it into an AST, converts the AST into a state machine
model, and renders code using template files.

The module is intended to be imported by CLI entry-point modules that assemble
Click command groups. It does not expose public helpers; the main integration
point is the internal :func:`_add_generate_subcommand` used by the package's
CLI bootstrap code.

Example::

    >>> import click
    >>> from pyfcstm.entry.generate import _add_generate_subcommand
    >>> app = click.Group()
    >>> _ = _add_generate_subcommand(app)
    >>> # The resulting app now includes the "generate" subcommand.
"""

from __future__ import annotations

import pathlib
from tempfile import TemporaryDirectory

import click

from .base import CONTEXT_SETTINGS
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..render import StateMachineCodeRenderer
from ..utils import auto_decode


def _add_generate_subcommand(cli: click.Group) -> click.Group:
    """
    Add the ``generate`` subcommand to a Click command group.

    This helper registers a ``generate`` subcommand that reads a state machine
    DSL file, parses it into a model, and renders code into an output directory
    using a template directory.

    :param cli: The Click command group to which the subcommand will be added.
    :type cli: click.Group
    :return: The modified Click command group.
    :rtype: click.Group

    Example::

        >>> import click
        >>> app = click.Group()
        >>> app = _add_generate_subcommand(app)
        >>> # "generate" is now available as a subcommand on app.
    """
    from ..template import list_templates, extract_template

    @cli.command(
        "generate",
        help="Generate code with template of a given state machine DSL code.",
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        "-i",
        "--input-code",
        "input_code_file",
        type=str,
        required=True,
        help="Input code file of state machine DSL.",
    )
    @click.option(
        "-t",
        "--template-dir",
        "template_dir",
        type=str,
        required=False,
        help="Template directory of the code generation.",
    )
    @click.option(
        "--template",
        "template_name",
        type=click.Choice(list_templates(), case_sensitive=True),
        required=False,
        help="Built-in template name of the code generation.",
    )
    @click.option(
        "-o",
        "--output-dir",
        "output_dir",
        type=str,
        required=True,
        help="Output directory of the code generation.",
    )
    @click.option(
        "--clear",
        "--clear-directory",
        "clear_directory",
        type=bool,
        is_flag=True,
        help="Clear the destination directory of the output directory.",
    )
    def generate(
        input_code_file: str,
        template_dir: str,
        template_name: str,
        output_dir: str,
        clear_directory: bool,
    ) -> None:
        """
        Generate code from a state machine DSL file using templates.

        This command reads the DSL file as bytes, decodes it with
        :func:`pyfcstm.utils.auto_decode`, parses it with the grammar entry
        ``state_machine_dsl``, converts the AST to a state machine model, and
        renders output using :class:`pyfcstm.render.StateMachineCodeRenderer`.

        :param input_code_file: Path to the input DSL code file.
        :type input_code_file: str
        :param template_dir: Path to the directory containing templates.
        :type template_dir: str
        :param template_name: Built-in template name to extract before rendering.
        :type template_name: str
        :param output_dir: Path to the directory where generated code will be written.
        :type output_dir: str
        :param clear_directory: Whether to clear the output directory before rendering.
        :type clear_directory: bool
        :return: ``None``.
        :rtype: None

        :raises UnicodeDecodeError: If the input file cannot be decoded.
        :raises AttributeError: If the grammar entry ``state_machine_dsl`` is missing.
        :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
        :raises SyntaxError: If the DSL model is invalid.
        :raises IOError: If reading the input file or writing output files fails.
        :raises jinja2.exceptions.TemplateError: If template rendering fails.

        Example::

            $ pyfcstm generate -i ./machine.dsl -t ./templates -o ./out --clear
            $ pyfcstm generate -i ./machine.dsl --template python -o ./out
        """
        if bool(template_dir) == bool(template_name):
            raise click.UsageError(
                "Exactly one of --template-dir/-t or --template must be provided."
            )

        code = auto_decode(pathlib.Path(input_code_file).read_bytes())
        ast_node = parse_with_grammar_entry(code, entry_name="state_machine_dsl")
        model = parse_dsl_node_to_state_machine(ast_node, path=input_code_file)

        if template_name:
            with TemporaryDirectory() as td:
                extracted_template_dir = extract_template(
                    template_name,
                    td,
                )
                renderer = StateMachineCodeRenderer(template_dir=extracted_template_dir)
                renderer.render(
                    model,
                    output_dir=output_dir,
                    clear_previous_directory=clear_directory,
                )
        else:
            renderer = StateMachineCodeRenderer(template_dir=template_dir)
            renderer.render(
                model,
                output_dir=output_dir,
                clear_previous_directory=clear_directory,
            )

    return cli

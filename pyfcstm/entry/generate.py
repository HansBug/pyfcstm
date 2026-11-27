"""
Command-line interface integration for state machine code generation.

This module wires a ``generate`` subcommand into a Click command group so that
users can generate source code from a state machine DSL file. The subcommand
reads the DSL file, parses it into an AST, converts the AST into a state machine
model, and renders code using template files.

The module is intended to be imported by CLI entry-point modules that assemble
Click command groups. It does not expose public helpers; the main integration
point is the internal ``_add_generate_subcommand`` used by the package's
CLI bootstrap code.

The module contains:

* ``_add_generate_subcommand`` - Register the ``generate`` subcommand on a
  Click group

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
from typing import List

import click

from .base import CONTEXT_SETTINGS, ClickErrorException
from ..dsl import parse_with_grammar_entry
from ..model import parse_dsl_node_to_state_machine
from ..render import StateMachineCodeRenderer
from ..utils import auto_decode
from ..utils.validate import ModelValidationError


def _builtin_templates_with_region_support() -> List[str]:
    """
    List the built-in templates that declare the ``region`` feature.

    The packaged templates are extracted one by one and asked for the
    ``features`` they declare, so the answer follows the templates themselves
    instead of a list kept here. It is only called when a model has been
    refused, so the cost of extracting each template does not matter.

    :return: Names of the built-in templates that render models with regions,
        in the order of :func:`pyfcstm.template.list_templates`.
    :rtype: List[str]
    """
    from ..template import extract_template, list_templates

    names = []
    for name in list_templates():
        with TemporaryDirectory() as work:
            if "region" in StateMachineCodeRenderer(extract_template(name, work)).features:
                names.append(name)
    return names


def _region_refusal_guidance(
    model, builtin: bool, input_code_file: str, output_dir: str
) -> str:
    """
    Explain what a refusal of a model with regions means and what to do next.

    The text answers three questions: what happened (how many regions the
    model declares and where the first one is), what a template author has to
    do (only for a template directory, because nobody edits a built-in one),
    and what a model writer can do right away (a template that supports
    regions, with a command that can be copied, or a model without regions).

    :param model: The refused model; it declares at least one region.
    :type model: pyfcstm.model.model.StateMachine
    :param builtin: Whether the refusing template is a built-in one.
    :type builtin: bool
    :param input_code_file: Input file of the command, used in the suggested command.
    :type input_code_file: str
    :param output_dir: Output directory of the command, used in the suggested command.
    :type output_dir: str
    :return: Several lines of guidance, without a trailing newline.
    :rtype: str
    """
    import shlex

    regions = list(model.walk_regions())
    capable = _builtin_templates_with_region_support()
    lines = [
        "The model declares %d region%s, the first is '%s'."
        % (len(regions), "" if len(regions) == 1 else "s", ".".join(regions[0].path))
    ]
    if not builtin:
        lines.append(
            "If you write this template: its config.yaml does not list `region` under "
            "`features`. List it (`features: [region]`) only once the template really "
            "renders regions, because a template written for a single active path would "
            "generate wrong code for them, which is why it is refused. See \"Declaring "
            "model features\" in templates/README.md."
        )
    lines.append(
        "If you write the model: use a template that supports regions. Built-in "
        "templates that support regions: %s." % ", ".join(capable)
    )
    lines.append(
        "  pyfcstm generate -i %s --template %s -o %s"
        % (shlex.quote(input_code_file), capable[0], shlex.quote(output_dir))
    )
    lines.append("Or take the regions out of the model.")
    return "\n".join(lines)


def _require_template_features(
    model,
    renderer,
    template_label: str,
    builtin: bool,
    input_code_file: str,
    output_dir: str,
) -> None:
    """
    Stop the command when the template cannot render the model.

    The renderer refuses such a model itself; checking here first lets the
    command name the template the way the user selected it (a built-in name
    instead of the temporary directory it was extracted to), turn the refusal
    into a Click error before anything is written, and add the guidance of
    :func:`_region_refusal_guidance`.

    :param model: Model that is about to be rendered.
    :type model: pyfcstm.model.model.StateMachine
    :param renderer: Renderer built for the selected template.
    :type renderer: pyfcstm.render.render.StateMachineCodeRenderer
    :param template_label: How the message names the template, for example
        ``"built-in template 'python'"``.
    :type template_label: str
    :param builtin: Whether the template is a built-in one.
    :type builtin: bool
    :param input_code_file: Input file of the command.
    :type input_code_file: str
    :param output_dir: Output directory of the command.
    :type output_dir: str
    :return: ``None``.
    :rtype: None
    :raises pyfcstm.entry.base.ClickErrorException: If the model declares
        regions and the template does not declare the ``region`` feature.
    """
    if "region" in renderer.features:
        return
    from pyfcstm.model.support import require_supported_model

    try:
        require_supported_model(model, "generate with %s" % template_label)
    except ModelValidationError as err:
        # The template lacks the feature the model needs.
        guidance = _region_refusal_guidance(model, builtin, input_code_file, output_dir)
        raise ClickErrorException("%s\n%s" % (err, guidance)) from err


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
    :raises FileNotFoundError: If the packaged template index is missing; the
        names of the built-in templates are read through
        :func:`pyfcstm.template.list_templates` while the command is being
        registered, to build the choices of ``--template``.
    :raises json.JSONDecodeError: If the packaged template index is not valid
        JSON, for the same reason.

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

        :raises click.UsageError: If neither or both of ``--template-dir`` and
            ``--template`` are given; nothing is read or written in that case.
        :raises pyfcstm.entry.base.ClickErrorException: If building the model
            raises :class:`pyfcstm.utils.validate.ModelValidationError`, or if
            the model declares regions and the selected template does not
            declare the ``region`` feature; the message is the validation error
            text and nothing is written in the second case.
        :raises UnicodeDecodeError: If the input file cannot be decoded.
        :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
        :raises OSError: If reading the input file or writing output files fails.
        :raises jinja2.exceptions.TemplateError: If template rendering fails.

        .. note::
           Only the first two failures are converted into Click errors.  The
           parse, decode, file system and template errors are not caught here
           and propagate out of the command.

        Example::

            $ pyfcstm generate -i ./machine.dsl -t ./templates -o ./out --clear
            $ pyfcstm generate -i ./machine.dsl --template python -o ./out

        With ``--template python`` the output directory receives ``machine.py``
        together with the generated ``README.md`` and ``README_zh.md``.

        A template renders models that declare regions only when its
        ``config.yaml`` lists ``region`` under ``features``. For any other
        template the command stops before it writes anything::

            $ pyfcstm generate -i ./regions.fcstm -t ./old_template -o ./out
            generate with template directory '/abs/old_template' does not support region models yet. (line 4)
            The model declares 2 regions, the first is 'Root.Run.Motor'.
            If you write this template: its config.yaml does not list `region` under `features`. ...
            If you write the model: use a template that supports regions. Built-in templates that support regions: python.
              pyfcstm generate -i ./regions.fcstm --template python -o ./out
            Or take the regions out of the model.

        The text tells a template author what to declare and when, and a model
        writer which built-in templates can render the model, with a command that
        can be copied.
        """
        if bool(template_dir) == bool(template_name):
            raise click.UsageError(
                "Exactly one of --template-dir/-t or --template must be provided."
            )

        code = auto_decode(pathlib.Path(input_code_file).read_bytes())
        ast_node = parse_with_grammar_entry(code, entry_name="state_machine_dsl")
        try:
            model = parse_dsl_node_to_state_machine(ast_node, path=input_code_file)
        except ModelValidationError as err:
            # Model construction rejects the model.
            raise ClickErrorException(str(err)) from err

        if template_name:
            with TemporaryDirectory() as td:
                extracted_template_dir = extract_template(
                    template_name,
                    td,
                )
                renderer = StateMachineCodeRenderer(template_dir=extracted_template_dir)
                _require_template_features(
                    model,
                    renderer,
                    "built-in template '%s'" % template_name,
                    True,
                    input_code_file,
                    output_dir,
                )
                renderer.render(
                    model,
                    output_dir=output_dir,
                    clear_previous_directory=clear_directory,
                )
        else:
            renderer = StateMachineCodeRenderer(template_dir=template_dir)
            _require_template_features(
                model,
                renderer,
                "template directory '%s'" % renderer.template_dir,
                False,
                input_code_file,
                output_dir,
            )
            renderer.render(
                model,
                output_dir=output_dir,
                clear_previous_directory=clear_directory,
            )

    return cli

"""Expose the standalone Python diagram viewer through the CLI."""

from pathlib import Path
from typing import Optional

import click

from ..diagram import DiagramUnavailableError
from ..dsl.error import GrammarParseError
from ..model import load_state_machine_from_file
from ..utils import ModelValidationError
from .base import ClickErrorException

# The suffixes this command can actually produce. `Diagram.save` infers any
# suffix it knows, including the headless SVG/PNG/PDF exports that are
# deliberately unavailable, so those have to be rejected here as a usage error
# rather than surfacing as an internal traceback.
_JSON_SUFFIXES = (".json",)
_HTML_SUFFIXES = (".html", ".htm")


def _validate_output_suffix(output: str, format_name: Optional[str]) -> None:
    """
    Reject an output path this command cannot write.

    :param output: Requested output path.
    :type output: str
    :param format_name: Explicit ``--format`` value, or ``None`` to infer.
    :type format_name: str, optional
    :return: ``None``.
    :rtype: None
    :raises click.UsageError: If the suffix does not match the chosen format,
        or cannot be inferred as JSON or HTML.
    """
    if format_name is not None:
        # An explicit --format governs the write, so any suffix is the caller's
        # choice to make.
        return
    suffix = Path(output).suffix.lower()
    if suffix in _JSON_SUFFIXES + _HTML_SUFFIXES:
        return
    raise click.UsageError(
        "cannot infer an output format from %s; use a .json or .html path, or "
        "pass --format explicitly"
        % ("%r" % suffix if suffix else "a path with no suffix")
    )


def _load_model(input_code_file: str):
    """
    Load the input model, reporting user-input failures as CLI errors.

    A typo in the DSL is the most common way this command fails, and letting it
    escape as a traceback buries the parser's own message — which already names
    the line and column — under an unrelated stack.

    :param input_code_file: Path to the input FCSTM file.
    :type input_code_file: str
    :return: The loaded state machine.
    :rtype: pyfcstm.model.StateMachine
    :raises pyfcstm.entry.base.ClickErrorException: If the file cannot be read,
        decoded, parsed, or assembled into a valid model.
    """
    try:
        return load_state_machine_from_file(input_code_file)
    except FileNotFoundError:
        # The path is validated by click, but it can disappear between the
        # check and the read.
        raise ClickErrorException("Input DSL file not found: %s" % input_code_file)
    except UnicodeDecodeError as err:
        # auto_decode raises this when no supported encoding fits the bytes.
        raise ClickErrorException(
            "Failed to decode input DSL file %s: %s" % (input_code_file, err)
        )
    except OSError as err:
        # Path.read_bytes raises OSError subclasses for permission problems and
        # for a path that turns out to be a directory.
        raise ClickErrorException(
            "Failed to read input DSL file %s: %s" % (input_code_file, err)
        )
    except GrammarParseError as err:
        # Syntax and lexical failures in the user's FCSTM text.
        raise ClickErrorException(
            "Failed to parse input DSL file %s: %s" % (input_code_file, err)
        )
    except ModelValidationError as err:
        # Model-level contract violations after a syntactically valid parse,
        # including a failed import.
        raise ClickErrorException(
            "Invalid state machine model in %s: %s" % (input_code_file, err)
        )


def _write(target, write):
    """
    Run a viewer write, reporting filesystem failures as CLI errors.

    ``_validate_write_target`` already produces a message that names the path
    and the actual problem, and letting the exception escape buried it inside a
    stack — the same defect the input side had.

    :param target: Destination the caller asked for.
    :type target: str or os.PathLike
    :param write: Zero-argument callable performing the write.
    :type write: collections.abc.Callable
    :return: Whatever ``write`` returns.
    :raises pyfcstm.entry.base.ClickErrorException: If the destination cannot
        be written.
    """
    try:
        return write()
    except OSError as err:
        # IsADirectoryError, FileNotFoundError and NotADirectoryError come from
        # _validate_write_target; PermissionError and the rest come from the
        # write itself.
        raise ClickErrorException("Failed to write %s: %s" % (target, err))


@click.command("diagram")
@click.option(
    "-i",
    "input_code_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Input FCSTM file.",
)
@click.option(
    "-o",
    "output",
    type=click.Path(dir_okay=False, writable=True),
    help="Output JSON or standalone HTML path.",
)
@click.option(
    "--format",
    "format_name",
    type=click.Choice(["json", "html"]),
    default=None,
    help="Explicit output format; otherwise infer it from the path.",
)
@click.option(
    "--open",
    "open_window",
    is_flag=True,
    help="Open the generated HTML in a standalone diagram window.",
)
def diagram_command(
    input_code_file: str,
    output: Optional[str],
    format_name: Optional[str],
    open_window: bool,
) -> None:
    """Generate portable JSON or a standalone HTML diagram viewer."""
    model = _load_model(input_code_file)
    view = model.diagram()
    if open_window:
        if format_name not in (None, "html"):
            raise click.UsageError("--open requires HTML output")
        if output is not None and Path(output).suffix.lower() not in (".html", ".htm"):
            raise click.UsageError("--open requires an .html or .htm output path")
        try:
            path = _write(
                output or "the temporary viewer",
                lambda: view.show(output, open_window=True),
            )
        except DiagramUnavailableError as error:
            if output is not None:
                # The document is written before the window is launched, and an
                # explicit output path is never temporary, so it is still there
                # -- naming it is the useful part of this failure.
                click.echo(str(Path(output)))
                raise click.ClickException(str(error))
            # Without -o there is no document left to name. A failed launch
            # removes what it wrote at exit, precisely because no window is
            # showing it, and asking for one more temporary copy would both
            # write another ~30 MB and print a path that is already gone by the
            # time the user reads it. Point at the flag that keeps a document.
            raise click.ClickException(
                "%s; re-run with -o PATH to keep the generated viewer" % error
            )
        click.echo(str(path))
        return
    if output is None:
        if format_name not in (None, "json"):
            raise click.UsageError(
                "JSON is the only format that can be written to stdout"
            )
        click.echo(view.to_json())
        return
    _validate_output_suffix(output, format_name)
    target = Path(output)
    _write(target, lambda: view.save(target, format=format_name))
    click.echo(str(target))


def _add_diagram_subcommand(cli):
    """Register the ``diagram`` command on the top-level Click group."""
    cli.add_command(diagram_command)
    return cli


__all__ = ["diagram_command", "_add_diagram_subcommand"]

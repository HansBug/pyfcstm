"""Expose the standalone Python diagram viewer through the CLI."""

from pathlib import Path
from xml.etree import ElementTree
from typing import Optional

import click

from ..diagram import DiagramRenderLimitError, DiagramUnavailableError
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
#: Formats produced by the optional rendering runtime rather than written
#: directly.  They are listed separately because only these can report that the
#: runtime is missing, and only ``.png`` accepts a scale.
_EXPORT_SUFFIXES = (".svg", ".png", ".pdf")


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
    if suffix in _JSON_SUFFIXES + _HTML_SUFFIXES + _EXPORT_SUFFIXES:
        return
    raise click.UsageError(
        "cannot infer an output format from %s; use a .json, .html, .svg, .png "
        "or .pdf path, or pass --format explicitly"
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
    :rtype: pyfcstm.model.model.StateMachine
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
    # No `writable=True`: Click implements it as `os.access(W_OK)`, which cannot
    # tell a file the user protected from one whose write bit a umask cleared, so
    # it refused to overwrite the library's own output and made a second run
    # impossible. `_validate_write_target` asks about ownership instead, and
    # having one judge is what keeps the CLI and the API agreeing on a file.
    type=click.Path(dir_okay=False),
    help="Output JSON, standalone HTML, SVG, PNG or PDF path.",
)
@click.option(
    "--format",
    "format_name",
    type=click.Choice(["json", "html", "svg", "png", "pdf"]),
    default=None,
    help="Explicit output format; otherwise infer it from the path.",
)
@click.option(
    "--scale",
    "scale",
    type=float,
    default=None,
    help="PNG output scale; only valid for PNG output.",
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
    scale: Optional[float],
    open_window: bool,
) -> None:
    """Generate portable JSON, a standalone HTML viewer, or an SVG/PNG/PDF export."""
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
            # Without -o there is no document to name: no window opened, so
            # nothing was ever reading the ~29 MB that was written and `show`
            # removes it. Point at the flag that keeps one instead.
            raise click.ClickException(
                "%s; re-run with -o PATH to keep the generated viewer" % error
            )
        if output is not None:
            click.echo(str(path))
        # Without -o there is nothing left to name: the window has closed and
        # `show` removed the document, exactly as on the failure branch above.
        # Every other mode of this command prints a path that can be opened now,
        # so printing a removed one would be the only exception -- and
        # `p=$(pyfcstm diagram -i x.fcstm --open)` would collect a dead path.
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
    selected = format_name or target.suffix.lower().lstrip(".")
    if scale is not None and selected != "png":
        raise click.UsageError("--scale is only supported for PNG output")
    _write(
        target,
        lambda: _export(view, target, format_name, 1.0 if scale is None else scale),
    )
    click.echo(str(target))


def _export(view, target, format_name, scale):
    """
    Save one diagram, reporting export failures as CLI errors.

    An unavailable runtime, an out-of-range scale and an oversized output are all
    things the caller can act on, so each becomes a message rather than a stack.

    :param view: Diagram snapshot to save.
    :type view: pyfcstm.diagram.api.Diagram
    :param target: Destination path.
    :type target: pathlib.Path
    :param format_name: Explicit format, or ``None`` to use the suffix.
    :type format_name: str, optional
    :param scale: PNG scale.
    :type scale: float
    :return: The destination path.
    :rtype: pathlib.Path
    :raises pyfcstm.entry.base.ClickErrorException: If the export cannot be
        produced.
    :raises click.UsageError: If the requested scale is out of range.
    """
    try:
        return view.save(target, format=format_name, scale=scale)
    except ValueError as err:
        # An out-of-range scale is a usage error, and Click prints those with the
        # command's own help rather than as a failure of the diagram.
        raise click.UsageError(str(err))
    except DiagramRenderLimitError as err:
        raise ClickErrorException(str(err))
    except DiagramUnavailableError as err:
        raise ClickErrorException(str(err))


@click.command("expand-svg")
@click.option(
    "-i",
    "input_svg_file",
    required=True,
    type=click.Path(exists=True, dir_okay=False, readable=True),
    help="Canonical diagram SVG to expand.",
)
@click.option(
    "-o",
    "output",
    type=click.Path(dir_okay=False),
    help="Destination path; without it the expanded SVG goes to standard output.",
)
def expand_svg_command(input_svg_file: str, output: Optional[str]) -> None:
    """Convert a canonical diagram SVG into a self-contained one.

    A canonical SVG draws its labels as ``<text>`` and names the fonts it wants,
    so it renders correctly only where those fonts are installed.  Expanding
    replaces the glyphs and markers with paths, which makes the document
    self-contained at the cost of being no longer editable as text.

    ``Diagram.to_svg()`` already returns the expanded form.  This command exists
    for a caller that holds a canonical SVG it produced elsewhere -- the editor
    preview is the case it was added for, since a webview has the diagram on
    screen but no fonts to outline it with, and re-rendering from the source
    would silently discard the palette and colour mode the user chose.

    :param input_svg_file: Path to the canonical SVG.
    :type input_svg_file: str
    :param output: Destination path, or ``None`` for standard output.
    :type output: str, optional
    :return: ``None``.
    :rtype: None
    :raises click.UsageError: If the input does not look like an SVG document.
    :raises pyfcstm.entry.base.ClickErrorException: If the input cannot be read
        or does not parse as XML, the optional rendering runtime is unavailable,
        or the result exceeds the documented size limit.  A failure of the
        renderer itself is left to surface, because that is a defect here rather
        than anything about the caller's file.

    Example::

        $ pyfcstm expand-svg -i canonical.svg -o self-contained.svg
        $ pyfcstm expand-svg -i canonical.svg > self-contained.svg
    """
    from ..diagram.api import _atomic_write_text
    from ..diagram.engine import (
        MAX_EXPORT_TEXT_BYTES,
        DiagramAssetEngine,
        check_export_bytes,
    )

    try:
        canonical = Path(input_svg_file).read_text(encoding="utf-8")
    except UnicodeDecodeError as err:
        # auto-decoding is deliberately not used here: an SVG this command can
        # expand is one the renderer produced, and that is always UTF-8.
        raise ClickErrorException(
            "Failed to decode input SVG file %s: %s" % (input_svg_file, err)
        )
    except OSError as err:
        # Path.read_text raises OSError subclasses for permission problems and
        # for a path that turns out to be unreadable after Click checked it.
        raise ClickErrorException(
            "Failed to read input SVG file %s: %s" % (input_svg_file, err)
        )
    if "<svg" not in canonical:
        raise click.UsageError("%s does not look like an SVG document" % input_svg_file)
    # Judge the input here rather than inferring blame from whatever the engine
    # raises. `DiagramAssetError` covers a malformed document, a missing packaged
    # resource and two interpreters fighting over the runtime; reporting all of
    # them as a problem with the caller's file would tell a user with two
    # MiniRacers installed that their perfectly good SVG was broken.
    try:
        ElementTree.fromstring(canonical)
    except ElementTree.ParseError as err:
        # ParseError: the `<svg` test above only says the file mentions one, and
        # this is what a document malformed past that point looks like.
        raise ClickErrorException(
            "Failed to parse input SVG file %s: %s" % (input_svg_file, err)
        )
    try:
        expanded = DiagramAssetEngine().expand_svg(canonical)
        expanded = check_export_bytes(
            expanded.encode("utf-8"), "SVG", MAX_EXPORT_TEXT_BYTES
        ).decode("utf-8")
    except DiagramRenderLimitError as err:
        raise ClickErrorException(str(err))
    except DiagramUnavailableError as err:
        raise ClickErrorException(str(err))
    if output is None:
        click.echo(expanded)
        return
    target = Path(output)
    # The same writer every other diagram output goes through: it asks whether the
    # destination can be written before touching it, then replaces it atomically.
    # `write_text` truncates first, so an interrupt or a full disk would destroy an
    # existing file -- and a directory this command cannot write to would still be
    # overwritten, which is the one difference `diagram -o` does not have.
    _write(target, lambda: _atomic_write_text(target, expanded))
    click.echo(str(target))


def _add_diagram_subcommand(cli):
    """Register the ``diagram`` and ``expand-svg`` commands on the CLI group."""
    cli.add_command(diagram_command)
    cli.add_command(expand_svg_command)
    return cli


__all__ = ["diagram_command", "expand_svg_command", "_add_diagram_subcommand"]

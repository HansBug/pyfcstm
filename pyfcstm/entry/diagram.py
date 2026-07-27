"""Expose the standalone Python diagram viewer through the CLI."""

from pathlib import Path
from typing import Optional

import click

from ..diagram import DiagramUnavailableError
from ..model import load_state_machine_from_file

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
    model = load_state_machine_from_file(input_code_file)
    view = model.diagram()
    if open_window:
        if format_name not in (None, "html"):
            raise click.UsageError("--open requires HTML output")
        if output is not None and Path(output).suffix.lower() not in (".html", ".htm"):
            raise click.UsageError("--open requires an .html or .htm output path")
        try:
            path = view.show(output, open_window=True)
        except DiagramUnavailableError as error:
            # The document is written before the window opens, so the path is
            # the useful part of this failure; without it the user is left with
            # a traceback and a 30 MB file they cannot find. Repeating the call
            # without the launch returns that same path — the document is
            # memoised and a temporary path is reused per snapshot.
            written = view.show(output, open_window=False)
            click.echo(str(written))
            raise click.ClickException(str(error))
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
    view.save(target, format=format_name)
    click.echo(str(target))


def _add_diagram_subcommand(cli):
    """Register the ``diagram`` command on the top-level Click group."""
    cli.add_command(diagram_command)
    return cli


__all__ = ["diagram_command", "_add_diagram_subcommand"]

"""Expose the standalone Python diagram viewer through the CLI."""

from pathlib import Path
from typing import Optional

import click

from ..model import load_state_machine_from_file


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
        path = view.show(output, open_window=True)
        click.echo(str(path))
        return
    if output is None:
        if format_name not in (None, "json"):
            raise click.UsageError("JSON is the only format that can be written to stdout")
        click.echo(view.to_json())
        return
    target = Path(output)
    view.save(target, format=format_name)
    click.echo(str(target))


def _add_diagram_subcommand(cli):
    """Register the ``diagram`` command on the top-level Click group."""
    cli.add_command(diagram_command)
    return cli


__all__ = ["diagram_command", "_add_diagram_subcommand"]

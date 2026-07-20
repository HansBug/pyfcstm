"""Expose the standalone Python diagram viewer through the CLI."""

from pathlib import Path
from typing import Optional

import click

from ..model import load_state_machine_from_file


@click.command("diagram")
@click.option("-i", "input_code_file", required=True, type=click.Path(exists=True, dir_okay=False, readable=True))
@click.option("-o", "output", type=click.Path(dir_okay=False, writable=True))
@click.option("--format", "format_name", type=click.Choice(["json", "html"]), default=None)
@click.option("--open", "open_browser", is_flag=True, help="生成 HTML 后在默认浏览器中打开。")
def diagram_command(input_code_file: str, output: Optional[str], format_name: Optional[str], open_browser: bool) -> None:
    """
    从 FCSTM 文件生成可移植 JSON 或独立 HTML 图形查看器。

    :param input_code_file: 输入 FCSTM 文件路径。
    :type input_code_file: str
    :param output: 输出文件路径；省略时把 JSON 写到标准输出。
    :type output: str, optional
    :param format_name: 显式输出格式，省略时按文件后缀推断。
    :type format_name: str, optional
    :param open_browser: 是否打开生成的 HTML。
    :type open_browser: bool
    :return: ``None``。
    :rtype: None
    """
    model = load_state_machine_from_file(input_code_file)
    view = model.diagram()
    if open_browser:
        if output is not None and Path(output).suffix.lower() not in (".html", ".htm"):
            raise click.UsageError("使用 --open 时输出路径必须以 .html 或 .htm 结尾")
        path = view.show(output, open_browser=True)
        click.echo(str(path))
        return
    if output is None:
        if format_name not in (None, "json"):
            raise click.UsageError("没有输出文件时只能使用 JSON 格式")
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

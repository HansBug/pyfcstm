"""
SysDeSim XML/XMI to FCSTM CLI integration.

This module registers a ``sysdesim`` subcommand that converts one SysDeSim
XML/XMI file into one or more FCSTM DSL files. The command also writes a
phase6 JSON conversion report containing validation results and carried
diagnostics for each emitted output.

Example::

    >>> import click
    >>> from pyfcstm.entry.sysdesim import _add_sysdesim_subcommand
    >>> cli = click.Group()
    >>> _add_sysdesim_subcommand(cli)  # doctest: +ELLIPSIS
    <...Group...>
"""

from __future__ import annotations

import json
import shutil
from pathlib import Path
from typing import Optional

import click

from .base import CONTEXT_SETTINGS, ClickErrorException, command_wrap
from ..convert import build_sysdesim_conversion_report, convert_sysdesim_xml_to_dsls


def _format_sysdesim_cli_error(err: BaseException) -> str:
    """
    Convert a conversion exception into a user-facing CLI error message.

    :param err: Original conversion exception.
    :type err: BaseException
    :return: Human-readable CLI error message.
    :rtype: str
    """
    message = str(err)
    if isinstance(err, KeyError):
        return message.strip("'")
    if isinstance(err, ValueError) and "tick_duration_ms is required when lowering uml:TimeEvent transitions." in message:
        return "The selected SysDeSim machine contains uml:TimeEvent transitions; please provide --tick-duration-ms."
    if isinstance(err, NotImplementedError) and "transition effects yet" in message:
        return "SysDeSim conversion does not support transition effects yet in the current subset."
    if isinstance(err, NotImplementedError) and "cross-region transitions under parallel owner" in message:
        return "SysDeSim conversion does not support cross-region transitions under one parallel owner."
    return message


def _add_sysdesim_subcommand(cli: click.Group) -> click.Group:
    """
    Add the ``sysdesim`` conversion subcommand to a Click CLI group.

    :param cli: Click group to extend.
    :type cli: click.Group
    :return: The same Click group with the new command registered.
    :rtype: click.Group
    """

    @cli.command(
        "sysdesim",
        help="Convert one SysDeSim XML/XMI machine into FCSTM DSL files and a validation report.",
        context_settings=CONTEXT_SETTINGS,
    )
    @click.option(
        "-i",
        "--input-xml",
        "input_xml_file",
        type=str,
        required=True,
        help="Input SysDeSim XML/XMI file.",
    )
    @click.option(
        "-o",
        "--output-dir",
        "output_dir",
        type=str,
        required=True,
        help="Output directory for emitted FCSTM DSL files.",
    )
    @click.option(
        "--machine-name",
        "machine_name",
        type=str,
        default=None,
        help="Exact UML state-machine name to convert.",
    )
    @click.option(
        "--machine-id",
        "machine_id",
        type=str,
        default=None,
        help="Exact UML state-machine xmi:id to convert.",
    )
    @click.option(
        "--tick-duration-ms",
        "tick_duration_ms",
        type=float,
        default=None,
        help="Runtime tick duration in milliseconds required for uml:TimeEvent lowering.",
    )
    @click.option(
        "--report-file",
        "report_file",
        type=str,
        default=None,
        help="Optional JSON report path. Defaults to <output-dir>/sysdesim_conversion_report.json.",
    )
    @click.option(
        "--clear",
        "clear_directory",
        is_flag=True,
        help="Clear the output directory before writing converted files.",
    )
    @command_wrap()
    def sysdesim(
        input_xml_file: str,
        output_dir: str,
        machine_name: Optional[str],
        machine_id: Optional[str],
        tick_duration_ms: Optional[float],
        report_file: Optional[str],
        clear_directory: bool,
    ) -> None:
        """
        Convert a SysDeSim XML/XMI file into FCSTM DSL outputs plus a JSON report.

        :param input_xml_file: Input SysDeSim XML/XMI file.
        :type input_xml_file: str
        :param output_dir: Output directory for emitted FCSTM DSL files.
        :type output_dir: str
        :param machine_name: Exact UML state-machine name to convert.
        :type machine_name: str, optional
        :param machine_id: Exact UML state-machine xmi:id to convert.
        :type machine_id: str, optional
        :param tick_duration_ms: Runtime tick duration in milliseconds used for
            ``uml:TimeEvent`` lowering.
        :type tick_duration_ms: float, optional
        :param report_file: Optional JSON report path.
        :type report_file: str, optional
        :param clear_directory: Whether to clear the output directory first.
        :type clear_directory: bool
        :return: ``None``.
        :rtype: None
        """
        try:
            dsl_outputs = convert_sysdesim_xml_to_dsls(
                input_xml_file,
                machine_name=machine_name,
                machine_id=machine_id,
                tick_duration_ms=tick_duration_ms,
            )
            report = build_sysdesim_conversion_report(
                input_xml_file,
                machine_name=machine_name,
                machine_id=machine_id,
                tick_duration_ms=tick_duration_ms,
            )
        except (KeyError, NotImplementedError, ValueError) as err:
            raise ClickErrorException(_format_sysdesim_cli_error(err))

        output_root = Path(output_dir)
        if clear_directory and output_root.exists():
            shutil.rmtree(str(output_root))
        output_root.mkdir(parents=True, exist_ok=True)

        report_path = Path(report_file) if report_file is not None else output_root / "sysdesim_conversion_report.json"
        report_path.parent.mkdir(parents=True, exist_ok=True)

        output_files = []
        for output_name, dsl_code in dsl_outputs.items():
            output_file = output_root / f"{output_name}.fcstm"
            output_file.write_text(dsl_code, encoding="utf-8")
            output_files.append((output_name, output_file))

        report_data = report.to_dict()
        output_file_by_name = {output_name: str(output_file) for output_name, output_file in output_files}
        for output_item in report_data["outputs"]:
            output_item["output_file"] = output_file_by_name[output_item["output_name"]]
        report_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False, sort_keys=True) + "\n",
            encoding="utf-8",
        )

        click.echo(
            "Converted SysDeSim machine {name!r} into {count} FCSTM output(s).".format(
                name=report.selected_machine_name,
                count=len(output_files),
            )
        )
        for output_name, output_file in output_files:
            click.echo(f"{output_name}: {output_file}")
        click.echo(f"Report: {report_path}")

    return cli

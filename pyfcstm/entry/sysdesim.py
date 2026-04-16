"""
SysDeSim XML/XMI to FCSTM CLI integration.

This module registers a ``sysdesim`` command group. The group keeps the
existing XML/XMI -> FCSTM conversion behavior on the bare
``pyfcstm sysdesim`` entry, and also exposes nested validation/report
subcommands such as ``pyfcstm sysdesim validate``.

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
from typing import Dict, List, Optional, Sequence

import click

from .base import CONTEXT_SETTINGS, ClickErrorException, command_wrap
from ..convert import (
    build_sysdesim_conversion_report,
    build_sysdesim_timeline_import_report,
    convert_sysdesim_xml_to_dsls,
)


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
    if (
        isinstance(err, ValueError)
        and "tick_duration_ms is required when lowering uml:TimeEvent transitions."
        in message
    ):
        return "The selected SysDeSim machine contains uml:TimeEvent transitions; please provide --tick-duration-ms."
    if isinstance(err, NotImplementedError) and "transition effects yet" in message:
        return "SysDeSim conversion does not support transition effects yet in the current subset."
    if (
        isinstance(err, NotImplementedError)
        and "cross-region transitions under parallel owner" in message
    ):
        return "SysDeSim conversion does not support cross-region transitions under one parallel owner."
    return message


def _status_text(ok: bool) -> str:
    """
    Build a colored status label for CLI output.

    :param ok: Whether the represented check succeeded.
    :type ok: bool
    :return: ANSI-colored status label.
    :rtype: str
    """
    return (
        click.style("OK", fg="green", bold=True)
        if ok
        else click.style("FAIL", fg="red", bold=True)
    )


def _solver_status_text(status: str) -> str:
    """
    Build a colored status label for Phase11 solver results.

    :param status: Solver result status.
    :type status: str
    :return: ANSI-colored solver status label.
    :rtype: str
    """
    normalized = status.lower()
    if normalized == "sat":
        return click.style(status.upper(), fg="green", bold=True)
    if normalized == "unsat":
        return click.style(status.upper(), fg="yellow", bold=True)
    return click.style(status.upper(), fg="red", bold=True)


def _count_text(value: int) -> str:
    """
    Build a colored count value for CLI summaries.

    :param value: Integer count to render.
    :type value: int
    :return: ANSI-colored count string.
    :rtype: str
    """
    return click.style(str(value), fg="magenta", bold=True)


def _format_tick_duration_text(tick_duration_ms: Optional[float]) -> str:
    """
    Format one optional tick duration for CLI summaries.

    :param tick_duration_ms: Optional tick duration in milliseconds.
    :type tick_duration_ms: float, optional
    :return: Rendered tick duration text.
    :rtype: str
    """
    if tick_duration_ms is None:
        return "not required"
    return f"{tick_duration_ms:g} ms"


def _fit_text(text: str, width: int) -> str:
    """
    Fit one cell value into a fixed CLI table width.

    :param text: Raw cell text.
    :type text: str
    :param width: Target width.
    :type width: int
    :return: Width-limited cell text.
    :rtype: str
    """
    if len(text) <= width:
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _short_machine_alias(machine_alias: str, main_alias: Optional[str]) -> str:
    """
    Build one short display alias for the Phase11 witness table.

    :param machine_alias: Full machine alias from the report.
    :type machine_alias: str
    :param main_alias: Main output alias when available.
    :type main_alias: str, optional
    :return: Short machine alias.
    :rtype: str
    """
    if main_alias is not None and machine_alias == main_alias:
        return "Main"
    if "_region" in machine_alias:
        return "R{}".format(machine_alias.rsplit("_region", 1)[-1])
    return machine_alias


def _short_state_text(state_path: str) -> str:
    """
    Build one compact state label for the Phase11 witness table.

    :param state_path: Full state path.
    :type state_path: str
    :return: Shortened state label.
    :rtype: str
    """
    if ".Control." in state_path:
        return state_path.split(".Control.", 1)[1]
    if state_path.endswith(".Control"):
        return "Control"
    return state_path.rsplit(".", 1)[-1]


def _format_phase11_actions(actions: Sequence[str], main_alias: Optional[str]) -> str:
    """
    Build one compact action summary for the Phase11 witness table.

    :param actions: Action texts attached to one witness point.
    :type actions: collections.abc.Sequence[str]
    :param main_alias: Main output alias when available.
    :type main_alias: str, optional
    :return: Compact action text.
    :rtype: str
    """
    if not actions:
        return "-"

    rendered = []
    for item in actions:
        if item.startswith("hidden_auto(") and ": " in item and " -> " in item:
            prefix = item[len("hidden_auto(") : -1]
            machine_alias, arc = prefix.split(": ", 1)
            src, dst = arc.split(" -> ", 1)
            rendered.append(
                "tau:{alias} {src}->{dst}".format(
                    alias=_short_machine_alias(machine_alias, main_alias),
                    src=_short_state_text(src),
                    dst=_short_state_text(dst),
                )
            )
        elif item.startswith("SetInput("):
            rendered.append(item[len("SetInput(") : -1])
        else:
            rendered.append(item)
    return ",".join(rendered)


def _emit_phase11_timeline_table(
    timeline_report: Dict[str, object], output_aliases: Sequence[str]
) -> None:
    """
    Print one full SAT witness timeline table.

    :param timeline_report: Phase11 timeline report dict.
    :type timeline_report: dict[str, object]
    :param output_aliases: Output aliases in display order.
    :type output_aliases: collections.abc.Sequence[str]
    :return: ``None``.
    :rtype: None
    """
    timeline_points = timeline_report["timeline_points"]
    if not timeline_points:
        return

    main_alias = output_aliases[0] if output_aliases else None
    machine_headers = [
        _short_machine_alias(alias, main_alias) for alias in output_aliases
    ]
    headers = ["t", "pt", "act"] + machine_headers + ["co"]
    rows = []

    for item in timeline_points:
        state_map = {
            _short_machine_alias(alias, main_alias): _short_state_text(state)
            for alias, state in item["machine_states"]
        }
        point_label = item["point_label"]
        if item["point_kind"] == "auto":
            point_label = "tau@{}".format(point_label)
        co_text = ""
        if item["is_coexistent"]:
            co_text = (
                "start"
                if item["symbol"] == timeline_report["first_coexistence_symbol"]
                else "yes"
            )
        rows.append(
            [
                item["time_value_text"],
                point_label,
                _format_phase11_actions(item["actions"], main_alias),
            ]
            + [state_map.get(header, "-") for header in machine_headers]
            + [co_text]
        )

    widths = []
    for index, header in enumerate(headers):
        max_len = max([len(header)] + [len(row[index]) for row in rows])
        if header == "t":
            width = max(len(header), min(max_len, 8))
        elif header == "pt":
            width = max(len(header), min(max_len, 14))
        elif header == "act":
            width = max(len(header), min(max_len, 28))
        elif header == "co":
            width = max(len(header), min(max_len, 8))
        else:
            width = max(len(header), min(max_len, 14))
        widths.append(width)

    def _row(values: Sequence[str]) -> str:
        return (
            "| "
            + " | ".join(
                _fit_text(str(item), width) for item, width in zip(values, widths)
            )
            + " |"
        )

    click.echo("  witness timeline:")
    click.echo("    - t: solved continuous-time value.")
    click.echo(
        "    - pt: `sXX` is one imported step, `tau@...` is one hidden auto point."
    )
    click.echo("    - act: actions observed at that point.")
    click.echo(
        "    - co: `start` marks the first coexistence point; `yes` means coexistence still holds."
    )
    click.echo("  " + _row(headers))
    click.echo("  " + _row(["-" * width for width in widths]))
    for row in rows:
        click.echo("  " + _row(row))


def _emit_sysdesim_cli_summary(
    report, output_file_by_name: Dict[str, str], report_path: Path
) -> None:
    """
    Print a colored phase6 summary for the conversion report.

    :param report: Structured conversion report.
    :type report: pyfcstm.convert.sysdesim.convert.SysDeSimConversionReport
    :param output_file_by_name: Mapping from output name to emitted file path.
    :type output_file_by_name: dict[str, str]
    :param report_path: Path to the JSON report file.
    :type report_path: pathlib.Path
    :return: ``None``.
    :rtype: None
    """
    click.secho("SysDeSim Conversion Complete", fg="green", bold=True)
    click.echo(
        "{label}: {name} [{machine_id}]".format(
            label=click.style("Machine", fg="cyan", bold=True),
            name=report.selected_machine_name,
            machine_id=report.selected_machine_id,
        )
    )
    click.echo(
        "{label}: {source}".format(
            label=click.style("Source", fg="cyan", bold=True),
            source=report.source_xml_path,
        )
    )
    click.echo(
        "{label}: {tick}".format(
            label=click.style("Tick", fg="cyan", bold=True),
            tick=_format_tick_duration_text(report.tick_duration_ms),
        )
    )
    click.echo(
        "{label}: {count}".format(
            label=click.style("Outputs", fg="cyan", bold=True),
            count=click.style(str(report.output_count), fg="magenta", bold=True),
        )
    )
    click.echo(
        "{label}: {path}".format(
            label=click.style("Report", fg="cyan", bold=True),
            path=report_path,
        )
    )

    for item in report.outputs:
        click.echo(
            "{label}: {path}".format(
                label=click.style(item.output_name, fg="blue", bold=True),
                path=output_file_by_name[item.output_name],
            )
        )
        click.echo(
            "  validation: parser={parser} model={model} guards={guards} events={events} init={init}".format(
                parser=_status_text(item.parser_roundtrip_ok),
                model=_status_text(item.model_build_ok),
                guards=_status_text(item.guard_variables_defined),
                events=_status_text(item.event_paths_valid),
                init=_status_text(item.composite_states_have_init),
            )
        )
        click.echo(
            "  lines: {lines}".format(
                lines=click.style(str(item.dsl_line_count), fg="white", bold=True),
            )
        )
        if item.semantic_note:
            click.echo(
                "  {label}: {message}".format(
                    label=click.style("semantic", fg="yellow", bold=True),
                    message=item.semantic_note,
                )
            )
        if item.diagnostics:
            codes = ", ".join(item.code for item in item.diagnostics)
            click.echo(
                "  {label}: {codes}".format(
                    label=click.style("diagnostics", fg="yellow", bold=True),
                    codes=codes,
                )
            )


def _emit_sysdesim_validate_summary(
    report_data: Dict[str, object], report_path: Path
) -> None:
    """
    Print a colored summary for the timeline validation report.

    :param report_data: JSON-serializable validation report.
    :type report_data: dict[str, object]
    :param report_path: Path to the JSON report file.
    :type report_path: pathlib.Path
    :return: ``None``.
    :rtype: None
    """
    phase78 = report_data["phase78"]
    phase9 = report_data["phase9"]
    phase10 = report_data["phase10"]
    has_phase11 = "phase11" in report_data

    click.secho(
        (
            "SysDeSim State Query Validation Complete"
            if has_phase11
            else "SysDeSim Timeline Import Report Complete"
        ),
        fg="green",
        bold=True,
    )
    click.echo(
        "{label}: {mode}".format(
            label=click.style("Mode", fg="cyan", bold=True),
            mode=(
                "import report + Phase11 state query"
                if has_phase11
                else "import report only (no Phase11 state query provided)"
            ),
        )
    )
    click.echo(
        "{label}: {name}".format(
            label=click.style("Machine", fg="cyan", bold=True),
            name=report_data["selected_machine_name"],
        )
    )
    click.echo(
        "{label}: {name}".format(
            label=click.style("Interaction", fg="cyan", bold=True),
            name=report_data["selected_interaction_name"],
        )
    )
    click.echo(
        "{label}: {source}".format(
            label=click.style("Source", fg="cyan", bold=True),
            source=report_data["source_xml_path"],
        )
    )
    click.echo(
        "{label}: {tick}".format(
            label=click.style("Tick", fg="cyan", bold=True),
            tick=_format_tick_duration_text(report_data["tick_duration_ms"]),
        )
    )
    click.echo(
        "{label}: {path}".format(
            label=click.style("Report", fg="cyan", bold=True),
            path=report_path,
        )
    )

    click.echo(
        "{label}: graph_edges={graph} inputs={inputs} events={events} steps={steps} windows={windows} durations={durations} diagnostics={diagnostics}".format(
            label=click.style("Import Phase78", fg="cyan", bold=True),
            graph=_count_text(len(phase78["machine_graph"])),
            inputs=_count_text(len(phase78["input_candidates"])),
            events=_count_text(len(phase78["event_candidates"])),
            steps=_count_text(len(phase78["steps"])),
            windows=_count_text(len(phase78["time_windows"])),
            durations=_count_text(len(phase78["duration_constraints"])),
            diagnostics=_count_text(len(phase78["diagnostics"])),
        )
    )

    outputs = phase9["outputs"]
    click.echo(
        "{label}: {count}".format(
            label=click.style("Import Phase9 Outputs", fg="cyan", bold=True),
            count=_count_text(len(outputs)),
        )
    )
    for item in outputs:
        click.echo(
            "  {name}: defines={defines} events={events}".format(
                name=click.style(item["output_name"], fg="blue", bold=True),
                defines=_count_text(len(item["define_names"])),
                events=_count_text(len(item["event_runtime_refs"])),
            )
        )
        if item["semantic_note"]:
            click.echo(
                "    {label}: {message}".format(
                    label=click.style("semantic", fg="yellow", bold=True),
                    message=item["semantic_note"],
                )
            )
        if item["diagnostic_codes"]:
            click.echo(
                "    {label}: {codes}".format(
                    label=click.style("diagnostics", fg="yellow", bold=True),
                    codes=", ".join(item["diagnostic_codes"]),
                )
            )

    scenario = phase10["scenario"]
    traces = phase10["traces"]
    click.echo(
        "{label}: scenario={name} steps={steps} temporal_constraints={constraints} bindings={bindings} traces={traces} diagnostics={diagnostics}".format(
            label=click.style("Import Phase10", fg="cyan", bold=True),
            name=scenario["name"],
            steps=_count_text(len(scenario["steps"])),
            constraints=_count_text(len(scenario["temporal_constraints"])),
            bindings=_count_text(len(phase10["bindings"])),
            traces=_count_text(len(traces)),
            diagnostics=_count_text(len(phase10["diagnostics"])),
        )
    )
    click.echo(
        "  {label}:".format(
            label=click.style("initial states", fg="white", bold=True),
        )
    )
    for trace in traces:
        click.echo(
            "    {alias} -> {state}".format(
                alias=click.style(trace["machine_alias"], fg="blue"),
                state=trace["initial_state_path"],
            )
        )

    if not has_phase11:
        click.echo(
            "{label}: no state query was requested; this run only checked the import/report pipeline.".format(
                label=click.style("Phase11", fg="cyan", bold=True)
            )
        )
        return

    phase11 = report_data["phase11"]
    constraint_preview = phase11["constraint_preview"]
    solve_result = phase11["solve_result"]
    timeline_report = phase11["timeline_report"]
    click.echo(
        "{label}: {left} <-> {right}".format(
            label=click.style("Phase11 Query", fg="cyan", bold=True),
            left=click.style(
                "{alias}:{state}".format(
                    alias=solve_result["left_machine_alias"],
                    state=solve_result["left_state_path"],
                ),
                fg="blue",
            ),
            right=click.style(
                "{alias}:{state}".format(
                    alias=solve_result["right_machine_alias"],
                    state=solve_result["right_state_path"],
                ),
                fg="blue",
            ),
        )
    )
    click.echo(
        "  scope: {scope} | candidates: {count} | status: {status}".format(
            scope=phase11["observation_scope"],
            count=_count_text(constraint_preview["candidate_count"]),
            status=_solver_status_text(solve_result["status"]),
        )
    )
    if timeline_report["first_coexistence_symbol"] is not None:
        click.echo(
            "  first coexistence: {symbol} = {time}".format(
                symbol=click.style(
                    timeline_report["first_coexistence_symbol"],
                    fg="magenta",
                    bold=True,
                ),
                time=click.style(
                    str(timeline_report["first_coexistence_time_text"]),
                    fg="magenta",
                    bold=True,
                ),
            )
        )
    if timeline_report["first_coexistence_note"]:
        click.echo(
            "  {label}: {message}".format(
                label=click.style("note", fg="yellow", bold=True),
                message=timeline_report["first_coexistence_note"],
            )
        )
    if timeline_report["first_coexistence_symbol"] is not None:
        _emit_phase11_timeline_table(
            timeline_report, [item["output_name"] for item in phase9["outputs"]]
        )
    elif solve_result["reason"]:
        click.echo(
            "  {label}: {message}".format(
                label=click.style("reason", fg="yellow", bold=True),
                message=solve_result["reason"],
            )
        )


def _run_sysdesim_convert(
    input_xml_file: str,
    output_dir: str,
    machine_name: Optional[str],
    machine_id: Optional[str],
    tick_duration_ms: Optional[float],
    report_file: Optional[str],
    clear_directory: bool,
) -> None:
    """Run the legacy SysDeSim conversion flow."""
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

    report_path = (
        Path(report_file)
        if report_file is not None
        else output_root / "sysdesim_conversion_report.json"
    )
    report_path.parent.mkdir(parents=True, exist_ok=True)

    output_files = []
    for output_name, dsl_code in dsl_outputs.items():
        output_file = output_root / f"{output_name}.fcstm"
        output_file.write_text(dsl_code, encoding="utf-8")
        output_files.append((output_name, output_file))

    report_data = report.to_dict()
    output_file_by_name = {
        output_name: str(output_file) for output_name, output_file in output_files
    }
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
    _emit_sysdesim_cli_summary(report, output_file_by_name, report_path)


def _run_sysdesim_validate(
    input_xml_file: str,
    machine_name: Optional[str],
    interaction_name: Optional[str],
    tick_duration_ms: Optional[float],
    report_file: Optional[str],
    left_machine_alias: Optional[str],
    left_state_ref: Optional[str],
    right_machine_alias: Optional[str],
    right_state_ref: Optional[str],
    observation_scope: str,
) -> None:
    """Run the timeline validation/report flow."""
    try:
        report_data = build_sysdesim_timeline_import_report(
            xml_path=input_xml_file,
            machine_name=machine_name,
            interaction_name=interaction_name,
            tick_duration_ms=tick_duration_ms,
            left_machine_alias=left_machine_alias,
            left_state_ref=left_state_ref,
            right_machine_alias=right_machine_alias,
            right_state_ref=right_state_ref,
            observation_scope=observation_scope,
        )
    except (KeyError, LookupError, NotImplementedError, ValueError) as err:
        raise ClickErrorException(_format_sysdesim_cli_error(err))

    rendered = (
        json.dumps(report_data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
    )
    if report_file is None:
        click.echo(rendered, nl=False)
        return

    report_path = Path(report_file)
    report_path.parent.mkdir(parents=True, exist_ok=True)
    report_path.write_text(rendered, encoding="utf-8")
    _emit_sysdesim_validate_summary(report_data, report_path)
    click.echo(
        "Wrote SysDeSim timeline {kind} to {path}.".format(
            kind=("validation report" if "phase11" in report_data else "import report"),
            path=report_path,
        )
    )


def _add_sysdesim_subcommand(cli: click.Group) -> click.Group:
    """
    Add the ``sysdesim`` conversion subcommand to a Click CLI group.

    :param cli: Click group to extend.
    :type cli: click.Group
    :return: The same Click group with the new command registered.
    :rtype: click.Group
    """

    @cli.group(
        "sysdesim",
        help=(
            "Convert one SysDeSim XML/XMI machine into FCSTM DSL files, or run "
            "timeline validation/report subcommands."
        ),
        context_settings=CONTEXT_SETTINGS,
        invoke_without_command=True,
    )
    @click.option(
        "-i",
        "--input-xml",
        "input_xml_file",
        type=str,
        default=None,
        help="Input SysDeSim XML/XMI file.",
    )
    @click.option(
        "-o",
        "--output-dir",
        "output_dir",
        type=str,
        default=None,
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
    @click.pass_context
    @command_wrap()
    def sysdesim(
        ctx: click.Context,
        input_xml_file: Optional[str],
        output_dir: Optional[str],
        machine_name: Optional[str],
        machine_id: Optional[str],
        tick_duration_ms: Optional[float],
        report_file: Optional[str],
        clear_directory: bool,
    ) -> None:
        """
        Convert SysDeSim XML/XMI into FCSTM outputs when invoked directly.

        :param input_xml_file: Input SysDeSim XML/XMI file.
        :type input_xml_file: str, optional
        :param output_dir: Output directory for emitted FCSTM DSL files.
        :type output_dir: str, optional
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
        if ctx.invoked_subcommand is not None:
            return
        if not input_xml_file:
            raise ClickErrorException("Missing option '--input-xml' / '-i'.")
        if not output_dir:
            raise ClickErrorException("Missing option '--output-dir' / '-o'.")
        _run_sysdesim_convert(
            input_xml_file=input_xml_file,
            output_dir=output_dir,
            machine_name=machine_name,
            machine_id=machine_id,
            tick_duration_ms=tick_duration_ms,
            report_file=report_file,
            clear_directory=clear_directory,
        )

    @sysdesim.command(
        "validate",
        help=(
            "Build a timeline import validation report under sysdesim without "
            "mixing it into the conversion entry."
        ),
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
        "--machine-name",
        "machine_name",
        type=str,
        default=None,
        help="Exact UML state-machine name to inspect.",
    )
    @click.option(
        "--interaction-name",
        "interaction_name",
        type=str,
        default=None,
        help="Exact UML interaction name to inspect.",
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
        help=(
            "Optional JSON report path. Defaults to stdout. When provided, the "
            "CLI prints a readable summary and writes the full JSON report to "
            "the file."
        ),
    )
    @click.option(
        "--left-machine-alias",
        "left_machine_alias",
        type=str,
        default=None,
        help="Optional left machine alias for a Phase11 coexistence query.",
    )
    @click.option(
        "--left-state",
        "left_state_ref",
        type=str,
        default=None,
        help="Optional left state ref for a Phase11 coexistence query.",
    )
    @click.option(
        "--right-machine-alias",
        "right_machine_alias",
        type=str,
        default=None,
        help="Optional right machine alias for a Phase11 coexistence query.",
    )
    @click.option(
        "--right-state",
        "right_state_ref",
        type=str,
        default=None,
        help="Optional right state ref for a Phase11 coexistence query.",
    )
    @click.option(
        "--observation-scope",
        "observation_scope",
        type=click.Choice(["post_step", "open_interval", "both"]),
        default="both",
        show_default=True,
        help="Observation scope used when an optional Phase11 query is included.",
    )
    @command_wrap()
    def sysdesim_validate(
        input_xml_file: str,
        machine_name: Optional[str],
        interaction_name: Optional[str],
        tick_duration_ms: Optional[float],
        report_file: Optional[str],
        left_machine_alias: Optional[str],
        left_state_ref: Optional[str],
        right_machine_alias: Optional[str],
        right_state_ref: Optional[str],
        observation_scope: str,
    ) -> None:
        """
        Build a JSON timeline validation report for one SysDeSim input.

        :param input_xml_file: Input SysDeSim XML/XMI file.
        :type input_xml_file: str
        :param machine_name: Exact UML state-machine name to inspect.
        :type machine_name: str, optional
        :param interaction_name: Exact UML interaction name to inspect.
        :type interaction_name: str, optional
        :param tick_duration_ms: Runtime tick duration in milliseconds used for
            compatibility lowering.
        :type tick_duration_ms: float, optional
        :param report_file: Optional JSON report path. Defaults to stdout. When
            provided, the CLI prints a readable summary and writes the full
            JSON report to the file.
        :type report_file: str, optional
        :param left_machine_alias: Optional left machine alias for one Phase11 query.
        :type left_machine_alias: str, optional
        :param left_state_ref: Optional left state reference for one Phase11 query.
        :type left_state_ref: str, optional
        :param right_machine_alias: Optional right machine alias for one Phase11 query.
        :type right_machine_alias: str, optional
        :param right_state_ref: Optional right state reference for one Phase11 query.
        :type right_state_ref: str, optional
        :param observation_scope: Observation scope for the optional Phase11 query.
        :type observation_scope: str
        :return: ``None``.
        :rtype: None
        """
        _run_sysdesim_validate(
            input_xml_file=input_xml_file,
            machine_name=machine_name,
            interaction_name=interaction_name,
            tick_duration_ms=tick_duration_ms,
            report_file=report_file,
            left_machine_alias=left_machine_alias,
            left_state_ref=left_state_ref,
            right_machine_alias=right_machine_alias,
            right_state_ref=right_state_ref,
            observation_scope=observation_scope,
        )

    return cli

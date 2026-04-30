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
    run_sysdesim_static_pre_checks,
)
from ..convert.sysdesim.ir import IrDiagnostic


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


def _fit_text(text: str, width: int, align: str = "left") -> str:
    """
    Fit one cell value into a fixed CLI table width.

    :param text: Raw cell text.
    :type text: str
    :param width: Target width.
    :type width: int
    :param align: Text alignment inside the fixed width, defaults to ``left``
    :type align: str, optional
    :return: Width-limited cell text.
    :rtype: str
    """
    if len(text) <= width:
        if align == "right":
            return text.rjust(width)
        return text.ljust(width)
    if width <= 3:
        return text[:width]
    return text[: width - 3] + "..."


def _output_status_summary(item) -> str:
    """
    Build one compact validation status text for the conversion summary table.

    :param item: One conversion output report item.
    :type item: pyfcstm.convert.sysdesim.convert.SysDeSimOutputValidationReport
    :return: Compact status summary.
    :rtype: str
    """
    failed_checks = []
    if not item.parser_roundtrip_ok:
        failed_checks.append("parser")
    if not item.model_build_ok:
        failed_checks.append("model")
    if not item.guard_variables_defined:
        failed_checks.append("guards")
    if not item.event_paths_valid:
        failed_checks.append("events")
    if not item.composite_states_have_init:
        failed_checks.append("init")
    if not failed_checks:
        return "OK"
    return "FAIL({})".format(",".join(failed_checks))


def _diagnostic_summary(
    diagnostic_codes: Sequence[str], semantic_note: Optional[str]
) -> str:
    """
    Build one compact diagnostic summary for CLI tables.

    :param diagnostic_codes: Diagnostic codes attached to the output.
    :type diagnostic_codes: collections.abc.Sequence[str]
    :param semantic_note: Optional semantic note attached to the output.
    :type semantic_note: str, optional
    :return: Compact diagnostic summary.
    :rtype: str
    """
    if diagnostic_codes:
        return ",".join(_short_diagnostic_code(code) for code in diagnostic_codes)
    if semantic_note:
        return "semantic"
    return "-"


def _short_diagnostic_code(code: str) -> str:
    """
    Build one compact diagnostic code label for CLI table display.

    :param code: Original diagnostic code.
    :type code: str
    :return: Short diagnostic label.
    :rtype: str
    """
    short_code_map = {
        "parallel_main_machine_semantic_downgrade": "parallel-main",
        "parallel_split_semantic_downgrade": "parallel-split",
        "transition_effect_semantic_downgrade": "tx-effect",
    }
    if code in short_code_map:
        return short_code_map[code]
    if code.endswith("_semantic_downgrade"):
        code = code[: -len("_semantic_downgrade")]
    return code.replace("_", "-")


def _output_diagnostic_summary(item) -> str:
    """
    Build one compact diagnostic summary for the conversion summary table.

    :param item: One conversion output report item.
    :type item: pyfcstm.convert.sysdesim.convert.SysDeSimOutputValidationReport
    :return: Compact diagnostic summary.
    :rtype: str
    """
    return _diagnostic_summary(
        [entry.code for entry in item.diagnostics],
        item.semantic_note,
    )


def _style_sysdesim_table_cell(header: str, text: str, is_header: bool) -> str:
    """
    Style one CLI table cell used by SysDeSim summaries.

    :param header: Column header name.
    :type header: str
    :param text: Already width-fitted cell text.
    :type text: str
    :param is_header: Whether this cell belongs to the header row.
    :type is_header: bool
    :return: Styled cell text.
    :rtype: str
    """
    if is_header:
        return click.style(text, fg="cyan", bold=True)
    if header == "output":
        return click.style(text, fg="blue", bold=True)
    if header == "file":
        return click.style(text, fg="white")
    if header in {"ln", "defines", "events"}:
        return click.style(text, fg="magenta", bold=True)
    if header == "status":
        return click.style(
            text,
            fg=("green" if text.strip() == "OK" else "red"),
            bold=True,
        )
    if header == "diag" and text.strip() != "-":
        return click.style(text, fg="yellow", bold=True)
    return text


def _emit_sysdesim_table(
    headers: Sequence[str],
    rows: Sequence[Sequence[str]],
    max_widths: Dict[str, int],
    alignments: Optional[Dict[str, str]] = None,
) -> None:
    """
    Print one compact styled ASCII table for SysDeSim CLI summaries.

    :param headers: Column headers in display order.
    :type headers: collections.abc.Sequence[str]
    :param rows: Row values in display order.
    :type rows: collections.abc.Sequence[collections.abc.Sequence[str]]
    :param max_widths: Maximum widths keyed by header name.
    :type max_widths: dict[str, int]
    :param alignments: Optional alignment map keyed by header name.
    :type alignments: dict[str, str], optional
    :return: ``None``.
    :rtype: None
    """
    if alignments is None:
        alignments = {}

    widths = []
    for index, header in enumerate(headers):
        max_len = max([len(header)] + [len(str(row[index])) for row in rows])
        widths.append(max(len(header), min(max_len, max_widths[header])))

    border = "+-" + "-+-".join("-" * width for width in widths) + "-+"

    def _row(values: Sequence[str], is_header: bool = False) -> str:
        rendered = []
        for header, value, width in zip(headers, values, widths):
            fitted = _fit_text(
                str(value),
                width,
                align=alignments.get(header, "left"),
            )
            rendered.append(_style_sysdesim_table_cell(header, fitted, is_header))
        return "| " + " | ".join(rendered) + " |"

    click.echo(click.style(border, dim=True))
    click.echo(_row(headers, is_header=True))
    click.echo(click.style(border, dim=True))
    for row in rows:
        click.echo(_row(row))
    click.echo(click.style(border, dim=True))


def _emit_sysdesim_output_table(report, output_file_by_name: Dict[str, str]) -> None:
    """
    Print one compact styled table for conversion outputs.

    :param report: Structured conversion report.
    :type report: pyfcstm.convert.sysdesim.convert.SysDeSimConversionReport
    :param output_file_by_name: Mapping from output name to emitted file path.
    :type output_file_by_name: dict[str, str]
    :return: ``None``.
    :rtype: None
    """
    _emit_sysdesim_table(
        headers=["output", "file", "ln", "status", "diag"],
        rows=[
            [
                item.output_name,
                Path(output_file_by_name[item.output_name]).name,
                str(item.dsl_line_count),
                _output_status_summary(item),
                _output_diagnostic_summary(item),
            ]
            for item in report.outputs
        ],
        max_widths={
            "output": 36,
            "file": 42,
            "ln": 4,
            "status": 24,
            "diag": 18,
        },
        alignments={
            "ln": "right",
        },
    )


def _emit_sysdesim_validate_phase9_table(outputs: Sequence[Dict[str, object]]) -> None:
    """
    Print one compact styled table for validate-mode Phase9 outputs.

    :param outputs: Phase9 output dictionaries in display order.
    :type outputs: collections.abc.Sequence[dict[str, object]]
    :return: ``None``.
    :rtype: None
    """
    _emit_sysdesim_table(
        headers=["output", "defines", "events", "diag"],
        rows=[
            [
                str(item["output_name"]),
                str(len(item["define_names"])),
                str(len(item["event_runtime_refs"])),
                _diagnostic_summary(
                    item["diagnostic_codes"],
                    item["semantic_note"],
                ),
            ]
            for item in outputs
        ],
        max_widths={
            "output": 36,
            "defines": 7,
            "events": 6,
            "diag": 18,
        },
        alignments={
            "defines": "right",
            "events": "right",
        },
    )


def _emit_sysdesim_validate_output_notes(
    outputs: Sequence[Dict[str, object]], report_path: Optional[Path]
) -> None:
    """
    Print one short note for compact validate-mode output diagnostics.

    :param outputs: Phase9 output dictionaries in display order.
    :type outputs: collections.abc.Sequence[dict[str, object]]
    :param report_path: Optional path to the exported JSON report.
    :type report_path: pathlib.Path, optional
    :return: ``None``.
    :rtype: None
    """
    if any(item["diagnostic_codes"] or item["semantic_note"] for item in outputs):
        click.echo("")
        click.echo(
            "{label}: {message}".format(
                label=click.style("Notes", fg="cyan", bold=True),
                message=(
                    "compact diagnostics shown; full details are in {}.".format(
                        report_path.name
                    )
                    if report_path is not None
                    else "compact diagnostics shown; use --report-file to export full JSON diagnostics."
                ),
            )
        )


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
    report,
    output_root: Path,
    output_file_by_name: Dict[str, str],
    report_path: Optional[Path],
) -> None:
    """
    Print a colored phase6 summary for the conversion report.

    :param report: Structured conversion report.
    :type report: pyfcstm.convert.sysdesim.convert.SysDeSimConversionReport
    :param output_root: Directory where FCSTM outputs were written.
    :type output_root: pathlib.Path
    :param output_file_by_name: Mapping from output name to emitted file path.
    :type output_file_by_name: dict[str, str]
    :param report_path: Optional path to the JSON report file.
    :type report_path: pathlib.Path, optional
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
        "{label}: {path}".format(
            label=click.style("Output Dir", fg="cyan", bold=True),
            path=output_root,
        )
    )
    if report_path is not None:
        click.echo(
            "{label}: {path}".format(
                label=click.style("Report", fg="cyan", bold=True),
                path=report_path,
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
    click.echo("")
    _emit_sysdesim_output_table(report, output_file_by_name)

    if any(item.diagnostics or item.semantic_note for item in report.outputs):
        click.echo("")
        click.echo(
            "{label}: {message}".format(
                label=click.style("Notes", fg="cyan", bold=True),
                message=(
                    "compact diagnostics shown; full details are in the JSON report."
                    if report_path is not None
                    else "compact diagnostics shown; use --report-file to export full JSON diagnostics."
                ),
            )
        )


def _emit_sysdesim_validate_summary(
    report_data: Dict[str, object], report_path: Optional[Path]
) -> None:
    """
    Print a colored summary for the timeline validation report.

    :param report_data: JSON-serializable validation report.
    :type report_data: dict[str, object]
    :param report_path: Optional path to the JSON report file.
    :type report_path: pathlib.Path, optional
    :return: ``None``.
    :rtype: None
    """
    phase78 = report_data["phase78"]
    phase9 = report_data["phase9"]
    phase10 = report_data["phase10"]
    has_state_query = "phase11" in report_data

    click.secho(
        (
            "SysDeSim State Query Complete"
            if has_state_query
            else "SysDeSim Timeline Import Report Complete"
        ),
        fg="green",
        bold=True,
    )
    click.echo(
        "{label}: {mode}".format(
            label=click.style("Mode", fg="cyan", bold=True),
            mode=(
                "import report + state query"
                if has_state_query
                else "import report only"
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
    if report_path is not None:
        click.echo(
            "{label}: {path}".format(
                label=click.style("Report", fg="cyan", bold=True),
                path=report_path,
            )
        )

    click.echo(
        "{label}: graph_edges={graph} inputs={inputs} events={events} steps={steps} windows={windows} durations={durations} diagnostics={diagnostics}".format(
            label=click.style("Model Import", fg="cyan", bold=True),
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
            label=click.style("Outputs", fg="cyan", bold=True),
            count=_count_text(len(outputs)),
        )
    )
    click.echo("")
    _emit_sysdesim_validate_phase9_table(outputs)
    _emit_sysdesim_validate_output_notes(outputs, report_path)

    scenario = phase10["scenario"]
    traces = phase10["traces"]
    click.echo("")
    click.echo(
        "{label}: scenario={name} steps={steps} temporal_constraints={constraints} bindings={bindings} traces={traces} diagnostics={diagnostics}".format(
            label=click.style("Scenario", fg="cyan", bold=True),
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
            label=click.style("Initial States", fg="white", bold=True),
        )
    )
    for trace in traces:
        click.echo(
            "    {alias} -> {state}".format(
                alias=click.style(trace["machine_alias"], fg="blue"),
                state=trace["initial_state_path"],
            )
        )

    if not has_state_query:
        click.echo(
            "{label}: not requested.".format(
                label=click.style("State Query", fg="cyan", bold=True)
            )
        )
        return

    phase11 = report_data["phase11"]
    constraint_preview = phase11["constraint_preview"]
    solve_result = phase11["solve_result"]
    timeline_report = phase11["timeline_report"]
    click.echo(
        "{label}: {left} <-> {right}".format(
            label=click.style("State Query", fg="cyan", bold=True),
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


def _diagnostic_level_label(level: str) -> str:
    """
    Build one short colored severity label for a static-check diagnostic.

    :param level: Severity label such as ``error`` or ``warning``.
    :type level: str
    :return: ANSI-colored short tag like ``[ERROR]`` or ``[WARN]``.
    :rtype: str
    """
    normalized = (level or "").lower()
    if normalized == "error":
        return click.style("[ERROR]", fg="red", bold=True)
    if normalized == "warning":
        return click.style("[WARN] ", fg="yellow", bold=True)
    return click.style("[INFO] ", fg="cyan", bold=True)


def _serialize_diagnostic(diag: IrDiagnostic) -> Dict[str, object]:
    """Convert one :class:`IrDiagnostic` into a JSON-serializable dict."""
    payload: Dict[str, object] = {
        "level": diag.level,
        "code": diag.code,
        "message": diag.message,
    }
    if diag.source_id is not None:
        payload["source_id"] = diag.source_id
    if diag.state_path is not None:
        payload["state_path"] = list(diag.state_path)
    if diag.details is not None:
        payload["details"] = diag.details
    if diag.hints:
        payload["hints"] = list(diag.hints)
    return payload


def _emit_static_check_diagnostic(diag: IrDiagnostic) -> None:
    """Print one colored, multi-line static-check diagnostic block to stdout."""
    label = _diagnostic_level_label(diag.level)
    code_text = click.style(diag.code, fg="magenta", bold=True)
    click.echo("{label} {code}".format(label=label, code=code_text))
    for line in (diag.message or "").splitlines():
        click.echo("  " + line)
    if diag.source_id:
        click.echo("  " + click.style("source: ", dim=True) + diag.source_id)
    if diag.details:
        # Only surface the most actionable structured fields here; the full
        # JSON sits in --report-file under ``static_check.diagnostics``.
        for key in (
            "involved_constraint_ids",
            "suggested_first_culprit_constraint_id",
            "involved_steps",
            "machine_alias",
            "state_path",
            "step_id",
            "signal",
            "pre_state_path",
            "transition_source_states",
            "closest_matches",
        ):
            value = diag.details.get(key)
            if not value:
                continue
            if isinstance(value, (list, tuple)):
                rendered = ", ".join(str(item) for item in value)
            else:
                rendered = str(value)
            click.echo("  " + click.style("{}:".format(key), dim=True) + " " + rendered)
    if diag.hints:
        click.echo("  " + click.style("hints:", fg="green", bold=True))
        for hint in diag.hints:
            click.echo("    - " + hint)


def _emit_static_check_summary(diagnostics: Sequence[IrDiagnostic]) -> Dict[str, int]:
    """
    Print a colored static-check section header + per-diagnostic blocks; return
    a counts dict so callers can decide whether to continue.
    """
    error_count = sum(1 for d in diagnostics if (d.level or "").lower() == "error")
    warning_count = sum(
        1 for d in diagnostics if (d.level or "").lower() == "warning"
    )
    if not diagnostics:
        click.echo(
            "{label}  {message}".format(
                label=click.style("Static Pre-check", fg="cyan", bold=True),
                message=click.style("OK (no static issues found)", fg="green"),
            )
        )
        return {"errors": 0, "warnings": 0}

    parts = []
    if error_count:
        parts.append(
            click.style(
                "{} error{}".format(error_count, "" if error_count == 1 else "s"),
                fg="red",
                bold=True,
            )
        )
    if warning_count:
        parts.append(
            click.style(
                "{} warning{}".format(warning_count, "" if warning_count == 1 else "s"),
                fg="yellow",
                bold=True,
            )
        )
    summary = ", ".join(parts) if parts else "0 issues"
    click.echo(
        "{label}  {message}".format(
            label=click.style("Static Pre-check", fg="cyan", bold=True),
            message=summary,
        )
    )
    for diag in diagnostics:
        click.echo("")
        _emit_static_check_diagnostic(diag)
    click.echo("")
    return {"errors": error_count, "warnings": warning_count}


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

    output_files = []
    for output_name, dsl_code in dsl_outputs.items():
        output_file = output_root / f"{output_name}.fcstm"
        output_file.write_text(dsl_code, encoding="utf-8")
        output_files.append((output_name, output_file))

    report_data = report.to_dict()
    output_file_by_name = {
        output_name: str(output_file) for output_name, output_file in output_files
    }
    report_path = None
    if report_file is not None:
        report_path = Path(report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        for output_item in report_data["outputs"]:
            output_item["output_file"] = output_file_by_name[output_item["output_name"]]
        report_path.write_text(
            json.dumps(report_data, indent=2, ensure_ascii=False, sort_keys=True)
            + "\n",
            encoding="utf-8",
        )

    _emit_sysdesim_cli_summary(report, output_root, output_file_by_name, report_path)


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
    skip_static_check: bool = False,
) -> None:
    """Run the timeline validation/report flow."""
    static_diagnostics: List[IrDiagnostic] = []
    if not skip_static_check:
        try:
            static_diagnostics = run_sysdesim_static_pre_checks(
                xml_path=input_xml_file,
                machine_name=machine_name,
                interaction_name=interaction_name,
                tick_duration_ms=tick_duration_ms,
                left_machine_alias=left_machine_alias,
                left_state_ref=left_state_ref,
                right_machine_alias=right_machine_alias,
                right_state_ref=right_state_ref,
            )
        except (KeyError, LookupError, NotImplementedError, ValueError) as err:
            raise ClickErrorException(_format_sysdesim_cli_error(err))
        counts = _emit_static_check_summary(static_diagnostics)
        if counts["errors"]:
            click.echo(
                click.style(
                    "Static pre-check found {} blocking error(s); skipping SMT-based "
                    "validation. Fix the issues above (or pass --no-static-check to "
                    "force-run SMT) and try again.".format(counts["errors"]),
                    fg="red",
                    bold=True,
                )
            )
            if report_file is not None:
                static_payload = {
                    "static_check": {
                        "skipped": False,
                        "blocking_errors": counts["errors"],
                        "warnings": counts["warnings"],
                        "diagnostics": [
                            _serialize_diagnostic(d) for d in static_diagnostics
                        ],
                    }
                }
                report_path = Path(report_file)
                report_path.parent.mkdir(parents=True, exist_ok=True)
                report_path.write_text(
                    json.dumps(
                        static_payload, indent=2, ensure_ascii=False, sort_keys=True
                    )
                    + "\n",
                    encoding="utf-8",
                )
            raise ClickErrorException(
                "static pre-check failed with {} blocking error(s)".format(
                    counts["errors"]
                )
            )
        if counts["warnings"]:
            click.echo(
                click.style(
                    "Static pre-check passed with warnings; continuing to "
                    "SMT-based validation.",
                    fg="yellow",
                )
            )

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

    report_data["static_check"] = {
        "skipped": skip_static_check,
        "blocking_errors": sum(
            1 for d in static_diagnostics if (d.level or "").lower() == "error"
        ),
        "warnings": sum(
            1 for d in static_diagnostics if (d.level or "").lower() == "warning"
        ),
        "diagnostics": [_serialize_diagnostic(d) for d in static_diagnostics],
    }

    report_path = None
    if report_file is not None:
        rendered = (
            json.dumps(report_data, indent=2, ensure_ascii=False, sort_keys=True) + "\n"
        )
        report_path = Path(report_file)
        report_path.parent.mkdir(parents=True, exist_ok=True)
        report_path.write_text(rendered, encoding="utf-8")

    _emit_sysdesim_validate_summary(report_data, report_path)

    if report_path is not None:
        click.echo(
            "Wrote SysDeSim timeline {kind} to {path}.".format(
                kind=(
                    "validation report" if "phase11" in report_data else "import report"
                ),
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
        help=(
            "Optional JSON report path. When provided, the CLI writes the full "
            "conversion report JSON; otherwise no JSON report is exported."
        ),
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
            "Optional JSON report path. When provided, the CLI writes the full "
            "timeline report JSON; otherwise no JSON report is exported."
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
    @click.option(
        "--no-static-check",
        "skip_static_check",
        is_flag=True,
        default=False,
        help=(
            "Skip the static pre-check phase (timing UNSAT detection, state "
            "reachability, signal-drop warnings, query-name validation). The "
            "downstream SMT validation will still run, but blocking errors at "
            "the model/scenario level are no longer surfaced ahead of time."
        ),
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
        skip_static_check: bool,
    ) -> None:
        """
        Build one readable timeline validation summary for one SysDeSim input.

        :param input_xml_file: Input SysDeSim XML/XMI file.
        :type input_xml_file: str
        :param machine_name: Exact UML state-machine name to inspect.
        :type machine_name: str, optional
        :param interaction_name: Exact UML interaction name to inspect.
        :type interaction_name: str, optional
        :param tick_duration_ms: Runtime tick duration in milliseconds used for
            compatibility lowering.
        :type tick_duration_ms: float, optional
        :param report_file: Optional JSON report path. When provided, the CLI
            writes the full timeline report JSON; otherwise no JSON report is
            exported.
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
            skip_static_check=skip_static_check,
        )

    @sysdesim.command(
        "static-check",
        help=(
            "Run the static pre-check phase only (no SMT). Reports timing "
            "contradictions, unreachable states, dropped signals, and unknown "
            "query state references in a colored terminal-friendly form."
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
            "Optional JSON report path. When provided, the CLI writes a JSON "
            "document containing the structured static-check diagnostics."
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
        "--warn-as-error",
        "warn_as_error",
        is_flag=True,
        default=False,
        help=(
            "Treat warning-level diagnostics (e.g. dropped signals) as blocking "
            "errors. Useful in CI pipelines where any modeling smell should "
            "fail the build."
        ),
    )
    @command_wrap()
    def sysdesim_static_check(
        input_xml_file: str,
        machine_name: Optional[str],
        interaction_name: Optional[str],
        tick_duration_ms: Optional[float],
        report_file: Optional[str],
        left_machine_alias: Optional[str],
        left_state_ref: Optional[str],
        right_machine_alias: Optional[str],
        right_state_ref: Optional[str],
        warn_as_error: bool,
    ) -> None:
        """
        Run the static pre-check phase only and exit non-zero on errors.

        :param input_xml_file: Input SysDeSim XML/XMI file.
        :type input_xml_file: str
        :param machine_name: Exact UML state-machine name to inspect.
        :type machine_name: str, optional
        :param interaction_name: Exact UML interaction name to inspect.
        :type interaction_name: str, optional
        :param tick_duration_ms: Runtime tick duration in milliseconds used
            for compatibility lowering.
        :type tick_duration_ms: float, optional
        :param report_file: Optional JSON report path.
        :type report_file: str, optional
        :param left_machine_alias: Optional Phase11 left machine alias.
        :type left_machine_alias: str, optional
        :param left_state_ref: Optional Phase11 left state ref.
        :type left_state_ref: str, optional
        :param right_machine_alias: Optional Phase11 right machine alias.
        :type right_machine_alias: str, optional
        :param right_state_ref: Optional Phase11 right state ref.
        :type right_state_ref: str, optional
        :param warn_as_error: Whether to treat warnings as blocking errors.
        :type warn_as_error: bool
        :return: ``None``.
        :rtype: None
        """
        try:
            diagnostics = run_sysdesim_static_pre_checks(
                xml_path=input_xml_file,
                machine_name=machine_name,
                interaction_name=interaction_name,
                tick_duration_ms=tick_duration_ms,
                left_machine_alias=left_machine_alias,
                left_state_ref=left_state_ref,
                right_machine_alias=right_machine_alias,
                right_state_ref=right_state_ref,
            )
        except (KeyError, LookupError, NotImplementedError, ValueError) as err:
            raise ClickErrorException(_format_sysdesim_cli_error(err))
        counts = _emit_static_check_summary(diagnostics)

        if report_file is not None:
            payload = {
                "static_check": {
                    "warn_as_error": warn_as_error,
                    "blocking_errors": counts["errors"],
                    "warnings": counts["warnings"],
                    "diagnostics": [_serialize_diagnostic(d) for d in diagnostics],
                }
            }
            report_path = Path(report_file)
            report_path.parent.mkdir(parents=True, exist_ok=True)
            report_path.write_text(
                json.dumps(payload, indent=2, ensure_ascii=False, sort_keys=True)
                + "\n",
                encoding="utf-8",
            )

        blocking = counts["errors"] + (counts["warnings"] if warn_as_error else 0)
        if blocking:
            raise ClickErrorException(
                "static pre-check found {} blocking issue(s)".format(blocking)
            )

    return cli

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
import os
import platform
import re
import shutil
import subprocess
import sys
import tempfile
import webbrowser
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Tuple

import click

from .base import CONTEXT_SETTINGS, ClickErrorException, command_wrap
from ..convert import (
    build_sysdesim_conversion_report,
    build_sysdesim_timeline_import_report,
    convert_sysdesim_xml_to_dsls,
    render_sysdesim_timeline_png,
    render_sysdesim_timeline_svg,
    run_sysdesim_static_pre_checks,
)
from ..convert.sysdesim.ir import IrDiagnostic
from ..convert.sysdesim.render import (
    SysdesimRenderError,
    build_overlay_from_diagnostics,
)
from ..convert.sysdesim.timeline_verify import (
    SysDeSimPhase10Report,
    build_sysdesim_phase10_report,
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


def _fit_text(text: str, width: int, align: str = "left") -> str:
    """
    Fit one cell value into a fixed CLI table width.

    :param text: Raw cell text.
    :type text: str
    :param width: Target width.
    :type width: int
    :param align: Text alignment inside the fixed width — ``left``,
        ``right``, or ``center``. Defaults to ``left``.
    :type align: str, optional
    :return: Width-limited cell text.
    :rtype: str
    """
    if len(text) <= width:
        if align == "right":
            return text.rjust(width)
        if align == "center":
            return text.center(width)
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


def _format_phase11_action_token(item: str, main_alias: Optional[str]) -> str:
    """Normalize one action string from the witness timeline.

    Backwards-compatible with the older ``emit(X)`` / ``SetInput(y=2300)``
    encodings used by earlier reports as well as the newer symmetric
    ``X<--`` (inbound emit) / ``-->X`` (outbound signal) / ``y=2300``
    (assignment) encodings.
    """
    if item.startswith("hidden_auto(") and ": " in item and " -> " in item:
        prefix = item[len("hidden_auto(") : -1]
        machine_alias, arc = prefix.split(": ", 1)
        src, dst = arc.split(" -> ", 1)
        return "tau:{alias} {src}->{dst}".format(
            alias=_short_machine_alias(machine_alias, main_alias),
            src=_short_state_text(src),
            dst=_short_state_text(dst),
        )
    if item.startswith("SetInput("):
        return item[len("SetInput(") : -1]
    if item.startswith("emit(") and item.endswith(")"):
        return "{}<--".format(item[len("emit(") : -1])
    return item


def _classify_action_token(token: str) -> str:
    """Categorize one normalized action token for ANSI styling."""
    if token.startswith("tau:"):
        return "tau"
    if token.endswith("<--"):
        return "inbound"
    if token.startswith("-->"):
        return "outbound"
    if "=" in token:
        return "assignment"
    return "other"


_ACTION_TOKEN_COLORS: Dict[str, Dict[str, object]] = {
    "tau": {"fg": "yellow"},
    "inbound": {"fg": "cyan", "bold": True},
    "outbound": {"fg": "magenta", "bold": True},
    "assignment": {"fg": "blue"},
    "other": {},
}


def _format_phase11_actions(
    actions: Sequence[str],
    main_alias: Optional[str],
    *,
    colorize: bool = False,
) -> str:
    """
    Build one compact action summary for the Phase11 witness table.

    :param actions: Action texts attached to one witness point.
    :type actions: collections.abc.Sequence[str]
    :param main_alias: Main output alias when available.
    :type main_alias: str, optional
    :param colorize: If true, wrap each action token in ANSI styling that
        emphasizes the kind of event it represents
        (inbound emit / outbound signal / tau auto-transition / variable
        assignment).
    :type colorize: bool
    :return: Compact action text, optionally ANSI-colored.
    :rtype: str
    """
    if not actions:
        return "-"

    rendered = []
    for item in actions:
        token = _format_phase11_action_token(item, main_alias)
        if colorize:
            style = _ACTION_TOKEN_COLORS.get(_classify_action_token(token), {})
            rendered.append(click.style(token, **style))
        else:
            rendered.append(token)
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
    headers = ["t", "act"] + machine_headers + ["co"]
    plain_rows: List[List[str]] = []
    colored_rows: List[List[str]] = []

    first_coex_symbol = timeline_report["first_coexistence_symbol"]
    for index, item in enumerate(timeline_points):
        state_map = {
            _short_machine_alias(alias, main_alias): _short_state_text(state)
            for alias, state in item["machine_states"]
        }
        if index == 0:
            co_text = "initial"
        elif item["is_coexistent"]:
            co_text = "start" if item["symbol"] == first_coex_symbol else "yes"
        else:
            co_text = ""
        plain_act = _format_phase11_actions(item["actions"], main_alias)
        colored_act = _format_phase11_actions(
            item["actions"], main_alias, colorize=True
        )
        if co_text == "start":
            colored_co = click.style("start", fg="green", bold=True)
        elif co_text == "yes":
            colored_co = click.style("yes", fg="green")
        elif co_text == "initial":
            colored_co = click.style("initial", fg="cyan")
        else:
            colored_co = ""
        machine_cells = [state_map.get(header, "-") for header in machine_headers]
        plain_rows.append(
            [item["time_value_text"], plain_act] + machine_cells + [co_text]
        )
        colored_rows.append(
            [item["time_value_text"], colored_act] + machine_cells + [colored_co]
        )

    widths = []
    aligns: List[str] = []
    for index, header in enumerate(headers):
        max_len = max([len(header)] + [len(row[index]) for row in plain_rows])
        if header == "t":
            width = max(len(header), min(max_len, 8))
            aligns.append("right")
        elif header == "act":
            width = max(len(header), min(max_len, 28))
            aligns.append("center")
        elif header == "co":
            width = max(len(header), min(max_len, 8))
            aligns.append("center")
        else:
            width = max(len(header), min(max_len, 14))
            aligns.append("center")
        widths.append(width)

    def _fit_with_ansi(plain: str, colored: str, width: int, align: str) -> str:
        """Fit a colored cell to ``width`` columns using ``plain`` for length."""
        if len(plain) > width:  # pragma: no cover - widths are computed from observed cell lengths so truncation never triggers in practice
            if width <= 3:
                return plain[:width]
            return plain[: width - 3] + "..."
        gap = width - len(plain)
        if align == "right":
            return (" " * gap) + colored
        if align == "center":
            left_pad = gap // 2
            right_pad = gap - left_pad
            return (" " * left_pad) + colored + (" " * right_pad)
        return colored + (" " * gap)  # pragma: no cover - left-align path unused by the witness table

    def _row_plain(values: Sequence[str]) -> str:
        return (
            "| "
            + " | ".join(
                _fit_text(str(item), width, align)
                for item, width, align in zip(values, widths, aligns)
            )
            + " |"
        )

    def _row_colored(
        plain: Sequence[str], colored: Sequence[str], header_row: bool = False
    ) -> str:
        cell_aligns = ["center"] * len(aligns) if header_row else aligns
        return (
            "| "
            + " | ".join(
                _fit_with_ansi(str(p), str(c), width, align)
                for p, c, width, align in zip(plain, colored, widths, cell_aligns)
            )
            + " |"
        )

    header_cells = [click.style(h, fg="cyan", bold=True) for h in headers]
    click.echo("  witness timeline:")
    click.echo("    - t: solved continuous-time value.")
    click.echo(
        "    - act: actions observed at that point. "
        "`Sig9<--` = inbound emit, `-->Sig13` = outbound signal, "
        "`tau:R3 S->X` = hidden auto-transition, `y=2300` = SetInput."
    )
    click.echo(
        "    - co: `initial` marks the initial state, `start` marks the first "
        "coexistence point, `yes` means coexistence still holds. The `start` "
        "and `yes` rows are underlined in color terminals."
    )
    def _apply_row_style(line: str, *, underline: bool, bold: bool) -> str:
        """Re-apply line-level ANSI attributes after each inner reset.

        ``click.style`` resets every attribute on ``\\x1b[0m``, which our
        per-cell coloring emits at the end of each colored token. To keep an
        outer underline active across the whole row we open the row-level
        styles, then re-open them after every inner reset.
        """
        if not underline and not bold:  # pragma: no cover - only called with underline=True
            return line
        opener = ""
        if underline:
            opener += "\x1b[4m"
        if bold:
            opener += "\x1b[1m"
        return opener + line.replace("\x1b[0m", "\x1b[0m" + opener) + "\x1b[0m"

    click.echo("  " + _row_colored(headers, header_cells, header_row=True))
    click.echo("  " + _row_plain(["-" * width for width in widths]))
    for plain, colored in zip(plain_rows, colored_rows):
        co_text = plain[-1]
        line = _row_colored(plain, colored)
        if co_text == "start":
            line = _apply_row_style(line, underline=True, bold=True)
        elif co_text == "yes":
            line = _apply_row_style(line, underline=True, bold=False)
        click.echo("  " + line)


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


def _diagnostics_from_report_dict(report: Dict) -> List[IrDiagnostic]:
    """Reconstruct minimal :class:`IrDiagnostic` instances from a JSON report.

    Accepts either the static-check-only report shape (``{"static_check": {...}}``)
    or the validate-report shape (which embeds ``static_check`` alongside the
    timeline import sections). Unrecognized shapes silently yield an empty list
    so the caller can still render the baseline diagram.
    """
    static = report.get("static_check") if isinstance(report, dict) else None
    raw = (static or {}).get("diagnostics") or []
    out: List[IrDiagnostic] = []
    for entry in raw:
        if not isinstance(entry, dict):
            continue
        details = entry.get("details")
        if isinstance(details, list):
            details = None  # ignore malformed
        hints = entry.get("hints")
        if isinstance(hints, list):
            hints_list = [str(h) for h in hints]
        else:
            hints_list = None
        state_path = entry.get("state_path")
        if isinstance(state_path, list):
            state_tuple: Optional[Tuple[str, ...]] = tuple(str(s) for s in state_path)
        else:
            state_tuple = None
        out.append(
            IrDiagnostic(
                level=str(entry.get("level") or ""),
                code=str(entry.get("code") or ""),
                message=str(entry.get("message") or ""),
                source_id=entry.get("source_id"),
                state_path=state_tuple,
                details=details if isinstance(details, dict) else None,
                hints=hints_list,
            )
        )
    return out


def _resolve_render_format(output_path: str, output_format: str = "auto") -> str:
    """Pick ``svg`` or ``png`` from an explicit format choice + output path.

    ``auto`` infers from the file extension (defaults to ``svg`` when neither
    ``.svg`` nor ``.png``).
    """
    fmt = (output_format or "auto").lower()
    if fmt in ("svg", "png"):
        return fmt
    ext = Path(output_path).suffix.lower()
    return "png" if ext == ".png" else "svg"


# Cache the discovered CJK font path so we only pay the ``fc-match`` /
# filesystem-probe cost once per CLI process.
_CJK_FONT_DISCOVERY_CACHE: Optional[Tuple[str, ...]] = None

# Filename-pattern regex of fonts that are known to carry CJK glyph
# coverage. Matched case-insensitively against the file's basename so we
# don't depend on absolute paths or specific OS layouts. Covers Microsoft
# YaHei / SimSun / SimHei / DengXian (Windows), Apple PingFang / Hiragino /
# Songti / STHeiti / STSong (macOS), Google Noto / Source Han / WenQuanYi /
# DroidSans / UMing / UKai (Linux distro packages), and a few legacy
# popular fallbacks.
_CJK_FONT_NAME_RE = re.compile(
    r"(?:"
    r"msyh|simsun|simhei|simfang|simkai|deng|fzheiti|fangsong|kaiti|"
    r"pingfang|hiragino|songti|stheiti|stsong|stkaiti|stxihei|"
    r"applesd?gothic|appleminchocho|"
    r"notosans?(?:hk|jp|kr|sc|tc)?cjk|notoserif?(?:hk|jp|kr|sc|tc)?cjk|"
    r"sourcehan(?:sans|serif)|"
    r"wqy[-_]?(?:micro)?(?:zen|hei|microhei)|"
    r"droidsans(?:fallback)?|"
    r"u(?:ming|kai)|cwtex|fireflysung"
    r")",
    re.IGNORECASE,
)

_FONT_FILE_EXTS = (".ttc", ".otc", ".ttf", ".otf")


def _platform_font_dirs() -> Tuple[str, ...]:
    """Return the per-platform font-search directories without hard-coding files.

    Order is "system → site → user" so per-user installs are picked up if
    present but don't shadow well-known system fonts. Non-existent entries
    are filtered downstream.
    """
    system = platform.system()
    if system == "Windows":
        # Win10+ allows per-user font installs under %LOCALAPPDATA%; older
        # Windows only knows %WINDIR%\Fonts.
        windir = os.environ.get("WINDIR") or os.environ.get("SystemRoot") or r"C:\Windows"
        local_app = os.environ.get("LOCALAPPDATA")
        dirs = [os.path.join(windir, "Fonts")]
        if local_app:
            dirs.append(os.path.join(local_app, "Microsoft", "Windows", "Fonts"))
        return tuple(dirs)
    if system == "Darwin":
        home = os.path.expanduser("~")
        return (
            "/System/Library/Fonts",
            "/System/Library/Fonts/Supplemental",
            "/Library/Fonts",
            os.path.join(home, "Library", "Fonts"),
        )
    # Treat everything else (Linux + BSD + cygwin) as XDG-style.
    home = os.path.expanduser("~")
    xdg_data = os.environ.get("XDG_DATA_HOME") or os.path.join(home, ".local", "share")
    extra: List[str] = []
    xdg_data_dirs = os.environ.get("XDG_DATA_DIRS") or ""
    for entry in xdg_data_dirs.split(os.pathsep):
        entry = entry.strip()
        if entry:
            extra.append(os.path.join(entry, "fonts"))
    return tuple([
        "/usr/share/fonts",
        "/usr/local/share/fonts",
        os.path.join(xdg_data, "fonts"),
        os.path.join(home, ".fonts"),
        *extra,
    ])


def _scan_dir_for_cjk_fonts(root: str, max_files: int = 4096) -> List[str]:
    """Walk ``root`` looking for font files whose name matches the CJK regex.

    Bounded by ``max_files`` so a pathological font dir does not freeze the
    CLI. Returns a list of absolute paths in os-walk order (i.e. roughly
    deterministic per host but not strictly sorted).
    """
    found: List[str] = []
    if not root or not os.path.isdir(root):
        return found
    seen = 0
    for dirpath, _dirnames, filenames in os.walk(root):
        for name in filenames:
            seen += 1
            if seen > max_files:
                return found
            base, ext = os.path.splitext(name)
            if ext.lower() not in _FONT_FILE_EXTS:
                continue
            if not _CJK_FONT_NAME_RE.search(base):
                continue
            found.append(os.path.join(dirpath, name))
    return found


def _discover_cjk_font_files() -> Tuple[str, ...]:
    """Best-effort cross-platform lookup of CJK-capable font files.

    The renderer's V8 isolate has no access to system fonts, and the bundled
    fallback (DejaVu Sans) has no CJK coverage. This helper tries, in order:

    1. ``PYFCSTM_CJK_FONT_FILE`` env var (one or more os-pathsep-separated
       absolute paths). Provides an explicit override for sealed/CI hosts.
    2. ``fc-match -f '%{file}\\n' 'sans-serif:lang=zh-cn'`` (fontconfig).
       Standard on Linux / macOS-via-Homebrew / MSYS2; reads the user's
       fontconfig preferences instead of guessing path layouts.
    3. ``fc-list :lang=zh-cn file`` (fontconfig multi-result fallback).
    4. A name-pattern regex scan over per-platform font directories. Uses
       :data:`_CJK_FONT_NAME_RE` so the heuristic is filename-shape based
       (matches ``msyh`` / ``NotoSansCJK*`` / ``PingFang*`` / ``wqy-zenhei``
       / etc.) rather than depending on exact absolute paths.

    Returns a tuple of one or more existing font-file paths, deduplicated
    in priority order. Cached after the first successful resolution.
    """
    global _CJK_FONT_DISCOVERY_CACHE
    if _CJK_FONT_DISCOVERY_CACHE is not None:
        return _CJK_FONT_DISCOVERY_CACHE

    found: List[str] = []

    def _push(path: Optional[str]) -> None:
        if not path:
            return
        path = str(path).strip()
        if not path or not os.path.isfile(path):
            return
        # Skip the DejaVu fallback the bundle already ships.
        if "DejaVu" in os.path.basename(path):
            return
        if path in found:
            return
        found.append(path)

    # 1. Environment-variable override.
    env_paths = os.environ.get("PYFCSTM_CJK_FONT_FILE")
    if env_paths:
        for entry in env_paths.split(os.pathsep):
            _push(entry)

    # 2. fontconfig: fc-match (single best match).
    fc_match = shutil.which("fc-match")
    if fc_match:
        try:
            result = subprocess.run(
                [fc_match, "-f", "%{file}\n", "sans-serif:lang=zh-cn"],
                capture_output=True,
                text=True,
                timeout=5,
            )
        except (OSError, subprocess.SubprocessError):  # pragma: no cover - fontconfig binaries are stable in CI
            result = None
        if result and result.returncode == 0:
            for line in (result.stdout or "").splitlines():
                _push(line)

    # 3. fontconfig: fc-list (broader probe in case fc-match returned the
    # DejaVu fallback or a non-CJK substitute).
    if not found:
        fc_list = shutil.which("fc-list")
        if fc_list:
            try:
                result = subprocess.run(
                    [fc_list, ":lang=zh-cn", "file"],
                    capture_output=True,
                    text=True,
                    timeout=5,
                )
            except (OSError, subprocess.SubprocessError):  # pragma: no cover
                result = None
            if result and result.returncode == 0:
                for line in (result.stdout or "").splitlines():
                    # ``fc-list ... file`` returns ``/path/to/font.ttc:`` lines.
                    candidate = line.strip().rstrip(":").strip()
                    _push(candidate)

    # 4. Per-platform font-directory scan with filename-pattern matching.
    if not found:
        for root in _platform_font_dirs():
            for cand in _scan_dir_for_cjk_fonts(root):
                _push(cand)

    _CJK_FONT_DISCOVERY_CACHE = tuple(found)
    return _CJK_FONT_DISCOVERY_CACHE


def _resolve_render_font_files(
    user_font_files: Optional[Sequence[str]] = None,
) -> Optional[List[str]]:
    """Combine user-supplied ``--font-file`` paths with auto-detected CJK fonts.

    User overrides take precedence (passed first); auto-detected fonts are
    appended so the renderer always has at least one CJK-capable buffer to
    fall back on. Returns ``None`` when nothing is available, keeping the
    bundle's DejaVu-only default behavior.
    """
    out: List[str] = []
    if user_font_files:
        out.extend(str(p) for p in user_font_files)
    for cand in _discover_cjk_font_files():
        if cand not in out:
            out.append(cand)
    return out or None


def _render_overlay_diagram(
    *,
    phase10_report: SysDeSimPhase10Report,
    output_path: str,
    output_format: str,
    diagnostics: Sequence[IrDiagnostic],
    summary_lines: Sequence[str] = (),
    title: Optional[str] = None,
    font_files: Optional[Sequence[str]] = None,
    coexistence_timeline: Optional[Dict] = None,
    include_state_cells: bool = True,
) -> Tuple[str, int]:
    """Render the sequence diagram with a diagnostics-driven overlay.

    Returns the resolved ``(format, byte_size)`` written to ``output_path``.
    When ``coexistence_timeline`` is given (or ``include_state_cells`` is
    explicitly true), the overlay also carries the per-step state-cell
    table that mirrors the validate CLI's ``co`` table on the diagram.
    """
    overlay = build_overlay_from_diagnostics(
        phase10_report=phase10_report,
        diagnostics=diagnostics,
        summary_lines=summary_lines,
        coexistence_timeline=coexistence_timeline,
        include_state_cells=include_state_cells,
    )
    fmt = _resolve_render_format(output_path, output_format)
    try:
        if fmt == "svg":
            svg_text = render_sysdesim_timeline_svg(
                phase10_report=phase10_report,
                title=title,
                overlay=overlay,
            )
            payload = svg_text.encode("utf-8")
        else:
            # PNG goes through resvg-wasm in the V8 isolate, which only sees
            # the bundled DejaVu fallback. Auto-detect a system CJK font so
            # Chinese state / signal names render instead of being silently
            # dropped from the rasterized output.
            payload = render_sysdesim_timeline_png(
                phase10_report=phase10_report,
                title=title,
                overlay=overlay,
                font_files=_resolve_render_font_files(font_files),
            )
    except SysdesimRenderError as err:
        raise ClickErrorException(str(err))
    out_path = Path(output_path)
    out_path.parent.mkdir(parents=True, exist_ok=True)
    out_path.write_bytes(payload)
    return fmt, out_path.stat().st_size


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
    render_diagram: Optional[str] = None,
    render_format: str = "auto",
    font_files: Optional[Sequence[str]] = None,
) -> None:
    """Run the timeline validation/report flow."""
    static_diagnostics: List[IrDiagnostic] = []
    phase10_for_render: Optional[SysDeSimPhase10Report] = None
    if render_diagram:
        try:
            phase10_for_render = build_sysdesim_phase10_report(
                input_xml_file,
                machine_name=machine_name,
                interaction_name=interaction_name,
                tick_duration_ms=tick_duration_ms,
            )
        except (KeyError, LookupError, NotImplementedError, ValueError) as err:
            raise ClickErrorException(_format_sysdesim_cli_error(err))
    if not skip_static_check:
        try:
            if phase10_for_render is not None:
                static_diagnostics = run_sysdesim_static_pre_checks(
                    phase10_report=phase10_for_render,
                    left_machine_alias=left_machine_alias,
                    left_state_ref=left_state_ref,
                    right_machine_alias=right_machine_alias,
                    right_state_ref=right_state_ref,
                )
            else:
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
            if render_diagram and phase10_for_render is not None:
                fmt, size = _render_overlay_diagram(
                    phase10_report=phase10_for_render,
                    output_path=render_diagram,
                    output_format=render_format,
                    diagnostics=static_diagnostics,
                    summary_lines=(
                        ["Validation skipped: static pre-check has blocking errors."]
                    ),
                    font_files=font_files,
                    include_state_cells=True,
                )
                click.echo(
                    "{label}  Wrote overlay {fmt} to {path} ({size} bytes).".format(
                        label=click.style(
                            "SysDeSim Validate Render", fg="cyan", bold=True
                        ),
                        fmt=fmt.upper(),
                        path=render_diagram,
                        size=size,
                    )
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

    if render_diagram and phase10_for_render is not None:
        summary_lines: List[str] = []
        timeline_report = (report_data.get("phase11") or {}).get("timeline_report")
        coexistence_payload: Optional[Dict] = None
        if isinstance(timeline_report, dict):
            coexistence_payload = timeline_report
            symbol = timeline_report.get("first_coexistence_symbol")
            time_text = timeline_report.get("first_coexistence_time_text")
            note = timeline_report.get("first_coexistence_note")
            if symbol is not None:
                summary_lines.append(
                    "First coexistence: {sym} = {t}".format(
                        sym=symbol, t=time_text
                    )
                )
            elif note:
                summary_lines.append("Phase11: {}".format(note))
        fmt, size = _render_overlay_diagram(
            phase10_report=phase10_for_render,
            output_path=render_diagram,
            output_format=render_format,
            diagnostics=static_diagnostics,
            summary_lines=summary_lines,
            coexistence_timeline=coexistence_payload,
            font_files=font_files,
            include_state_cells=True,
        )
        click.echo(
            "{label}  Wrote overlay {fmt} to {path} ({size} bytes).".format(
                label=click.style(
                    "SysDeSim Validate Render", fg="cyan", bold=True
                ),
                fmt=fmt.upper(),
                path=render_diagram,
                size=size,
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
    @click.option(
        "--render-diagram",
        "render_diagram",
        type=str,
        default=None,
        help=(
            "Optional path to write a sequence-diagram overlay rendering of "
            "the validation findings. Format inferred from the extension "
            "(``.svg`` / ``.png``). Includes a banner summarizing static-check "
            "counts plus any Phase11 first-coexistence point, and per-step "
            "markers for dropped signals / UNSAT durations."
        ),
    )
    @click.option(
        "--render-format",
        "render_format",
        type=click.Choice(["svg", "png", "auto"]),
        default="auto",
        show_default=True,
        help=(
            "Output format for ``--render-diagram``. ``auto`` infers from the "
            "extension; defaults to ``svg`` when neither ``.svg`` nor ``.png``."
        ),
    )
    @click.option(
        "--font-file",
        "font_files",
        type=str,
        multiple=True,
        help=(
            "Additional font file(s) to load for PNG rendering. The CLI auto-"
            "detects a system CJK font for Chinese state / signal names; "
            "use this flag to override or supplement the detection. "
            "Repeatable."
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
        render_diagram: Optional[str],
        render_format: str,
        font_files: Tuple[str, ...],
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
        :param render_diagram: Optional output path for an overlay-rendered
            sequence diagram of the validation findings.
        :type render_diagram: str, optional
        :param render_format: Output format for ``render_diagram``.
        :type render_format: str
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
            render_diagram=render_diagram,
            render_format=render_format,
            font_files=list(font_files) if font_files else None,
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
    @click.option(
        "--render-diagram",
        "render_diagram",
        type=str,
        default=None,
        help=(
            "Optional path to write a sequence-diagram overlay rendering of "
            "the static-check findings. Format inferred from the extension "
            "(``.svg`` / ``.png``). Diagnostic markers ride on top of the "
            "baseline diagram (banner, dropped-signal badges, UNSAT lane tags)."
        ),
    )
    @click.option(
        "--render-format",
        "render_format",
        type=click.Choice(["svg", "png", "auto"]),
        default="auto",
        show_default=True,
        help=(
            "Output format for ``--render-diagram``. ``auto`` infers from the "
            "extension; defaults to ``svg`` when neither ``.svg`` nor ``.png``."
        ),
    )
    @click.option(
        "--font-file",
        "font_files",
        type=str,
        multiple=True,
        help=(
            "Additional font file(s) to load for PNG rendering. The CLI auto-"
            "detects a system CJK font for Chinese state / signal names; "
            "use this flag to override or supplement the detection. "
            "Repeatable."
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
        render_diagram: Optional[str],
        render_format: str,
        font_files: Tuple[str, ...],
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
        :param render_diagram: Optional output path for an overlay-rendered
            sequence diagram of the static-check findings.
        :type render_diagram: str, optional
        :param render_format: Output format for ``render_diagram``.
        :type render_format: str
        :return: ``None``.
        :rtype: None
        """
        try:
            phase10 = build_sysdesim_phase10_report(
                input_xml_file,
                machine_name=machine_name,
                interaction_name=interaction_name,
                tick_duration_ms=tick_duration_ms,
            )
            diagnostics = run_sysdesim_static_pre_checks(
                phase10_report=phase10,
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

        if render_diagram:
            fmt, size = _render_overlay_diagram(
                phase10_report=phase10,
                output_path=render_diagram,
                output_format=render_format,
                diagnostics=diagnostics,
                font_files=list(font_files) if font_files else None,
                include_state_cells=True,
            )
            click.echo(
                "{label}  Wrote overlay {fmt} to {path} ({size} bytes).".format(
                    label=click.style(
                        "SysDeSim Static Check Render", fg="cyan", bold=True
                    ),
                    fmt=fmt.upper(),
                    path=render_diagram,
                    size=size,
                )
            )

        blocking = counts["errors"] + (counts["warnings"] if warn_as_error else 0)
        if blocking:
            raise ClickErrorException(
                "static pre-check found {} blocking issue(s)".format(blocking)
            )

    @sysdesim.command(
        "sequence-render",
        help=(
            "Render the SysDeSim sequence diagram of one interaction as SVG "
            "or PNG, in the visual style of the SysDeSim XMI tool's own "
            "export (actor boxes at top, lifelines, numbered message arrows, "
            "inline time brackets, variable-assignment pills on the left). "
            "PNG output uses an embedded resvg-wasm rasterizer; pass "
            "--font-file to add CJK / region-specific glyph coverage."
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
        "-o",
        "--output",
        "output_file",
        type=str,
        default=None,
        help=(
            "Output file path. Format inferred from the extension "
            "(``.svg`` / ``.png``); use ``--format`` to force. Optional "
            "when ``--preview`` is set (a temporary file is written)."
        ),
    )
    @click.option(
        "--format",
        "output_format",
        type=click.Choice(["svg", "png", "auto"]),
        default="auto",
        show_default=True,
        help=(
            "Output format. ``auto`` infers the format from the ``--output`` "
            "extension (defaults to SVG when the extension is missing or the "
            "render is preview-only)."
        ),
    )
    @click.option(
        "--preview",
        "preview",
        is_flag=True,
        default=False,
        help=(
            "Open the rendered diagram in the system default browser after "
            "writing. When combined with no ``--output``, the file is "
            "written to a temporary location."
        ),
    )
    @click.option(
        "--font-file",
        "font_files",
        type=str,
        multiple=True,
        help=(
            "Additional font file(s) to load for PNG rendering on top of "
            "the bundled DejaVu Sans fallback. Use this to add CJK / "
            "region-specific glyph coverage. Repeatable."
        ),
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
        help="Exact UML interaction name to render.",
    )
    @click.option(
        "--tick-duration-ms",
        "tick_duration_ms",
        type=float,
        default=None,
        help="Runtime tick duration in milliseconds for uml:TimeEvent lowering.",
    )
    @click.option(
        "--title",
        "title",
        type=str,
        default=None,
        help="Override the diagram title (defaults to the interaction name).",
    )
    @click.option(
        "--diagnostics-file",
        "diagnostics_file",
        type=str,
        default=None,
        help=(
            "Optional path to a JSON report (produced by ``static-check "
            "--report-file`` or ``validate --report-file``). When provided, "
            "the renderer overlays banner + diagnostic markers on top of the "
            "baseline diagram."
        ),
    )
    @command_wrap()
    def sysdesim_sequence_render(
        input_xml_file: str,
        output_file: Optional[str],
        output_format: str,
        preview: bool,
        font_files: Tuple[str, ...],
        machine_name: Optional[str],
        interaction_name: Optional[str],
        tick_duration_ms: Optional[float],
        title: Optional[str],
        diagnostics_file: Optional[str],
    ) -> None:
        """
        Render one SysDeSim sequence diagram as SVG or PNG.

        :param input_xml_file: Input SysDeSim XML/XMI file.
        :type input_xml_file: str
        :param output_file: Output file path. Optional when ``preview`` is set.
        :type output_file: str, optional
        :param output_format: One of ``svg``, ``png``, or ``auto``.
        :type output_format: str
        :param preview: Whether to open the rendered diagram in the system
            default browser after writing.
        :type preview: bool
        :param font_files: Additional font files for PNG rendering.
        :type font_files: tuple[str, ...]
        :param machine_name: Optional state-machine selector.
        :type machine_name: str, optional
        :param interaction_name: Optional interaction selector.
        :type interaction_name: str, optional
        :param tick_duration_ms: Optional tick duration for time-event lowering.
        :type tick_duration_ms: float, optional
        :param title: Optional title override.
        :type title: str, optional
        :param diagnostics_file: Optional path to a previously-written
            static-check or validate JSON report. When given, diagnostic
            overlay markers are layered on top of the baseline diagram.
        :type diagnostics_file: str, optional
        :return: ``None``.
        :rtype: None
        """
        if not output_file and not preview:
            raise ClickErrorException(
                "Provide --output / -o, --preview, or both."
            )

        resolved_format = output_format
        if resolved_format == "auto":
            if output_file:
                ext = Path(output_file).suffix.lower()
                resolved_format = "png" if ext == ".png" else "svg"
            else:
                resolved_format = "svg"

        overlay_payload: Optional[Dict] = None
        phase10_for_overlay: Optional[SysDeSimPhase10Report] = None
        if diagnostics_file:
            try:
                with open(diagnostics_file, "r", encoding="utf-8") as fp:
                    diag_doc = json.load(fp)
            except (OSError, ValueError) as err:
                raise ClickErrorException(
                    "Cannot read diagnostics file {}: {}".format(
                        diagnostics_file, err
                    )
                )
            try:
                phase10_for_overlay = build_sysdesim_phase10_report(
                    input_xml_file,
                    machine_name=machine_name,
                    interaction_name=interaction_name,
                    tick_duration_ms=tick_duration_ms,
                )
            except (KeyError, LookupError, NotImplementedError, ValueError) as err:
                raise ClickErrorException(_format_sysdesim_cli_error(err))
            diag_objs = _diagnostics_from_report_dict(diag_doc)
            overlay_payload = build_overlay_from_diagnostics(
                phase10_report=phase10_for_overlay,
                diagnostics=diag_objs,
            )

        try:
            if resolved_format == "svg":
                if phase10_for_overlay is not None:
                    svg_text = render_sysdesim_timeline_svg(
                        phase10_report=phase10_for_overlay,
                        title=title,
                        overlay=overlay_payload,
                    )
                else:
                    svg_text = render_sysdesim_timeline_svg(
                        xml_path=input_xml_file,
                        machine_name=machine_name,
                        interaction_name=interaction_name,
                        tick_duration_ms=tick_duration_ms,
                        title=title,
                    )
                payload = svg_text.encode("utf-8")
            else:
                # Auto-detect a CJK system font so Chinese state / signal
                # names rasterize instead of being silently dropped by
                # resvg-wasm. User ``--font-file`` paths take precedence.
                resolved_font_files = _resolve_render_font_files(
                    list(font_files) if font_files else None
                )
                if phase10_for_overlay is not None:
                    payload = render_sysdesim_timeline_png(
                        phase10_report=phase10_for_overlay,
                        title=title,
                        overlay=overlay_payload,
                        font_files=resolved_font_files,
                    )
                else:
                    payload = render_sysdesim_timeline_png(
                        xml_path=input_xml_file,
                        machine_name=machine_name,
                        interaction_name=interaction_name,
                        tick_duration_ms=tick_duration_ms,
                        title=title,
                        font_files=resolved_font_files,
                    )
        except (KeyError, LookupError, NotImplementedError, ValueError) as err:
            raise ClickErrorException(_format_sysdesim_cli_error(err))
        except SysdesimRenderError as err:
            raise ClickErrorException(str(err))

        if output_file:
            out_path = Path(output_file)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            out_path.write_bytes(payload)
        else:
            tmp = tempfile.NamedTemporaryFile(
                mode="wb",
                suffix="." + resolved_format,
                prefix="pyfcstm-sysdesim-",
                delete=False,
            )
            try:
                tmp.write(payload)
            finally:
                tmp.close()
            out_path = Path(tmp.name)

        click.echo(
            "{label}  Wrote sequence-diagram {fmt} to {path} ({size} bytes).".format(
                label=click.style("SysDeSim Sequence Render", fg="cyan", bold=True),
                fmt=resolved_format.upper(),
                path=str(out_path),
                size=out_path.stat().st_size,
            )
        )

        if preview:
            opened = webbrowser.open(out_path.as_uri())
            click.echo(
                "{label}  {message}".format(
                    label=click.style("Preview", fg="cyan", bold=True),
                    message=(
                        "opened {} in the system default browser.".format(out_path)
                        if opened
                        else "no browser available; file written to {}.".format(out_path)
                    ),
                )
            )

    return cli

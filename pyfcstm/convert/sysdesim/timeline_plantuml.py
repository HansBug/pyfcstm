"""
PlantUML sequence-diagram export for SysDeSim timeline reports.

This module implements the Phase 12 timeline visualization path for the
current SysDeSim importer. The exported diagram is intentionally timeline-
first: it renders imported sequence points and duration relationships from the
already-built timeline report rather than re-parsing the raw XML into a
separate display model.

The primary public APIs are :func:`build_sysdesim_timeline_plantuml` and
:func:`build_sysdesim_timeline_plantuml_from_xml`.
"""

from __future__ import annotations

from dataclasses import dataclass
import re
from typing import Dict, List, Optional, Tuple

from .timeline import (
    SysDeSimMessageObservation,
    SysDeSimStateInvariantObservation,
)
from .timeline_verify import SysDeSimPhase10Report, build_sysdesim_phase10_report

_PLANTUML_PARTICIPANT_PADDING = 50
_PLANTUML_SAFE_ID_RE = re.compile(r"[^0-9A-Za-z_]+")


@dataclass(frozen=True)
class SysDeSimTimelinePlantumlOptions:
    """
    Rendering options for SysDeSim timeline PlantUML export.

    :param include_hidden_auto: Whether hidden auto-transition occurrences
        should be rendered as additional notes, defaults to ``False``.
    :type include_hidden_auto: bool, optional
    :param include_debug_comments: Whether source observation ids and other
        traceability comments should be emitted into the PlantUML text,
        defaults to ``False``.
    :type include_debug_comments: bool, optional
    :param title: Optional explicit diagram title. When omitted, the selected
        interaction name is used.
    :type title: str, optional
    """

    include_hidden_auto: bool = False
    include_debug_comments: bool = False
    title: Optional[str] = None


def _escape_text(text: Optional[str]) -> str:
    """Escape plain text for inline PlantUML labels."""
    if text is None:
        return ""
    return (
        str(text)
        .replace("\\", "\\\\")
        .replace("\r\n", "\\n")
        .replace("\r", "\\n")
        .replace("\n", "\\n")
    )


def _participant_alias(index: int) -> str:
    """Build a stable participant alias."""
    return f"P{index + 1}"


def _constraint_anchor_name(constraint_id: str, side: str) -> str:
    """Build one PlantUML-safe teoz anchor name for a temporal constraint."""
    safe_id = _PLANTUML_SAFE_ID_RE.sub("_", constraint_id).strip("_")
    if not safe_id:
        safe_id = "constraint"
    if safe_id[0].isdigit():
        safe_id = f"C_{safe_id}"
    return f"{safe_id}__{side}"


def _constraint_value_text(min_text: Optional[str], max_text: Optional[str], strict_lower: bool) -> str:
    """Render one normalized temporal interval as short human-readable text."""
    if min_text == max_text and min_text is not None:
        value = min_text
    elif min_text is None and max_text is None:
        value = "unbounded"
    elif min_text is None:
        value = f"<= {max_text}"
    elif max_text is None:
        value = f">= {min_text}"
    else:
        value = f"{min_text}-{max_text}"

    if strict_lower:
        return f"{value} (strict lower)"
    return value


def _message_label(observation: SysDeSimMessageObservation) -> str:
    """Pick the best user-facing label for one message observation."""
    for candidate in (
        observation.display_name,
        observation.signal_name,
        observation.raw_name,
    ):
        if candidate:
            return candidate
    if observation.direction == "self":
        return "self"
    return "message"


def _extract_outbound_signal_name(notes: Tuple[str, ...]) -> Optional[str]:
    """Extract the exported outbound signal label from step notes."""
    for item in notes:
        if item.startswith("outbound_signal="):
            value = item.split("=", 1)[1].strip()
            if value:
                return value
    return None


def _collect_auto_notes(report: SysDeSimPhase10Report) -> Dict[str, List[str]]:
    """Collect hidden auto-transition note texts keyed by source step id."""
    result: Dict[str, List[str]] = {}
    for trace in report.traces:
        for execution in trace.steps:
            if not execution.auto_occurrences:
                continue
            bucket = result.setdefault(execution.step_id, [])
            for item in execution.auto_occurrences:
                bucket.append(
                    "[{symbol}] {machine}: {src} -> {dst}".format(
                        symbol=item.occurrence_symbol,
                        machine=trace.machine_alias,
                        src=item.from_state_path,
                        dst=item.to_state_path,
                    )
                )
    return result


def _assign_temporal_constraint_columns(
    report: SysDeSimPhase10Report,
) -> Tuple[Dict[str, int], int]:
    """
    Assign temporal constraints to right-side columns to reduce overlap.

    Constraints whose step ranges overlap are placed on different columns using
    a greedy interval-coloring strategy in step-order space.
    """
    step_index = {item.step_id: idx for idx, item in enumerate(report.scenario.steps)}
    ordered_constraints = sorted(
        report.scenario.temporal_constraints,
        key=lambda item: (
            step_index[item.left_step_id],
            step_index[item.right_step_id],
            item.constraint_id,
        ),
    )

    last_right_index_by_column: List[int] = []
    column_by_constraint_id: Dict[str, int] = {}
    for item in ordered_constraints:
        left_idx = step_index[item.left_step_id]
        right_idx = step_index[item.right_step_id]
        assigned_column = None
        for column, last_right_idx in enumerate(last_right_index_by_column):
            if left_idx > last_right_idx:
                assigned_column = column
                last_right_index_by_column[column] = right_idx
                break
        if assigned_column is None:
            assigned_column = len(last_right_index_by_column)
            last_right_index_by_column.append(right_idx)
        column_by_constraint_id[item.constraint_id] = assigned_column

    return column_by_constraint_id, len(last_right_index_by_column)


def build_sysdesim_timeline_plantuml(
    report: SysDeSimPhase10Report,
    options: Optional[SysDeSimTimelinePlantumlOptions] = None,
) -> str:
    """
    Build PlantUML sequence-diagram text from one SysDeSim Phase 10 report.

    The function only consumes already-normalized importer outputs. It does not
    reconstruct the diagram from raw XML independently.

    :param report: Phase 10 timeline report produced from the SysDeSim import
        chain.
    :type report: SysDeSimPhase10Report
    :param options: Optional rendering options.
    :type options: SysDeSimTimelinePlantumlOptions, optional
    :return: Full PlantUML source text.
    :rtype: str
    """
    options = options or SysDeSimTimelinePlantumlOptions()

    phase78_report = report.phase9_report.phase78_report
    interaction = phase78_report.phase56_report.interaction

    participant_alias_by_id: Dict[str, str] = {}
    participant_order: List[Tuple[str, str]] = []
    for index, lifeline in enumerate(interaction.lifelines):
        alias = _participant_alias(index)
        participant_alias_by_id[lifeline.lifeline_id] = alias
        label = lifeline.raw_name or lifeline.normalized_name or alias
        participant_order.append((alias, label))

    default_alias = participant_order[0][0] if participant_order else "P0"
    internal_alias = next(
        (
            participant_alias_by_id[lifeline.lifeline_id]
            for lifeline in interaction.lifelines
            if lifeline.is_machine_internal
        ),
        default_alias,
    )
    message_index = {
        item.message_id: item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimMessageObservation)
    }
    invariant_index = {
        item.invariant_id: item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimStateInvariantObservation)
    }
    constraint_column_by_id, constraint_column_count = _assign_temporal_constraint_columns(report)
    time_lane_aliases = [f"PT{index + 1}" for index in range(constraint_column_count)]
    constraint_anchor_name_by_id = {
        item.constraint_id: {
            "left": _constraint_anchor_name(item.constraint_id, "left"),
            "right": _constraint_anchor_name(item.constraint_id, "right"),
        }
        for item in report.scenario.temporal_constraints
    }

    anchor_specs_by_step: Dict[str, List[Tuple[int, str]]] = {}
    for item in report.scenario.temporal_constraints:
        column = constraint_column_by_id[item.constraint_id]
        anchor_specs_by_step.setdefault(item.left_step_id, []).append(
            (column, constraint_anchor_name_by_id[item.constraint_id]["left"])
        )
        anchor_specs_by_step.setdefault(item.right_step_id, []).append(
            (column, constraint_anchor_name_by_id[item.constraint_id]["right"])
        )

    auto_notes_by_step = _collect_auto_notes(report) if options.include_hidden_auto else {}

    title = options.title or interaction.interaction_name or report.scenario.name or "SysDeSim Timeline"

    lines = [
        "@startuml",
        "!pragma teoz true",
        "hide footbox",
        f"skinparam ParticipantPadding {_PLANTUML_PARTICIPANT_PADDING}",
        "skinparam sequenceMessageAlign center",
        'skinparam responseMessageBelowArrow true',
        f"title {_escape_text(title)}",
        "",
    ]
    for alias, label in participant_order:
        lines.append(f'participant "{_escape_text(label)}" as {alias}')
    for alias in time_lane_aliases:
        lines.append(f'participant " " as {alias}')
    if participant_order:
        lines.append("")

    if options.include_debug_comments:
        lines.extend(
            [
                "' Phase12 timeline visualization",
                f"' interaction={interaction.interaction_name}",
                f"' steps={len(report.scenario.steps)}",
                f"' temporal_constraints={len(report.scenario.temporal_constraints)}",
                "",
            ]
        )

    for step in report.scenario.steps:
        source_id = step.source_observation_ids[0] if step.source_observation_ids else None

        if options.include_debug_comments:
            comment_bits = [f"step={step.step_id}"]
            if source_id:
                comment_bits.append(f"source_observation_id={source_id}")
            lines.append("' " + " ".join(comment_bits))

        message_observation = message_index.get(source_id or "")
        invariant_observation = invariant_index.get(source_id or "")

        if message_observation is not None:
            source_alias = participant_alias_by_id.get(
                message_observation.source_lifeline_id or "",
                internal_alias,
            )
            target_alias = participant_alias_by_id.get(
                message_observation.target_lifeline_id or "",
                internal_alias,
            )
            outbound_signal_name = _extract_outbound_signal_name(step.notes)
            if message_observation.direction == "outbound" and outbound_signal_name:
                label = outbound_signal_name
            else:
                label = _message_label(message_observation)
            lines.append(
                "{{{anchor}}} {src} -> {dst} : [{step}] {label}".format(
                    anchor=step.step_id,
                    src=source_alias,
                    dst=target_alias,
                    step=step.step_id,
                    label=_escape_text(label),
                )
            )
        elif invariant_observation is not None:
            target_alias = participant_alias_by_id.get(
                invariant_observation.lifeline_id or "",
                internal_alias,
            )
            note_text = invariant_observation.raw_text or ""
            lines.append(
                "{{{anchor}}} {target} -> {target} : [{step}] {text}".format(
                    anchor=step.step_id,
                    target=target_alias,
                    step=step.step_id,
                    text=_escape_text(note_text),
                )
            )
        else:
            note_text = "; ".join(_escape_text(item) for item in step.notes) if step.notes else "anchor"
            lines.append(
                "{{{anchor}}} {target} -> {target} : [{step}] {text}".format(
                    anchor=step.step_id,
                    target=internal_alias,
                    step=step.step_id,
                    text=note_text,
                )
            )

        for column, anchor_name in sorted(anchor_specs_by_step.get(step.step_id, ())):
            lane_alias = time_lane_aliases[column]
            lines.append(
                "{{{anchor}}} {lane} -[#white]> {lane} : @{step}".format(
                    anchor=anchor_name,
                    lane=lane_alias,
                    step=_escape_text(step.step_id),
                )
            )

        for auto_note in auto_notes_by_step.get(step.step_id, ()):
            lines.append(f"note over {internal_alias} : {_escape_text(auto_note)}")

        lines.append("")

    for item in report.scenario.temporal_constraints:
        if options.include_debug_comments:
            lines.append(f"' temporal_constraint_id={item.constraint_id}")
        lines.append(
            "{{{left}}} <-> {{{right}}} : {value}".format(
                left=constraint_anchor_name_by_id[item.constraint_id]["left"],
                right=constraint_anchor_name_by_id[item.constraint_id]["right"],
                value=_escape_text(
                    _constraint_value_text(
                        item.min_seconds_text,
                        item.max_seconds_text,
                        item.strict_lower,
                    )
                ),
            )
        )

    if report.scenario.temporal_constraints:
        lines.append("")

    lines.extend(
        [
            "legend right",
            f"|= key |= value |",
            f"| interaction | {_escape_text(interaction.interaction_name)} |",
            f"| steps | {len(report.scenario.steps)} |",
            f"| normalized constraints | {len(report.scenario.temporal_constraints)} |",
            "endlegend",
            "@enduml",
            "",
        ]
    )
    return "\n".join(lines)


def build_sysdesim_timeline_plantuml_from_xml(
    xml_path: str,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    options: Optional[SysDeSimTimelinePlantumlOptions] = None,
) -> str:
    """
    Build PlantUML sequence-diagram text directly from one SysDeSim XML file.

    This is a thin convenience wrapper over
    :func:`build_sysdesim_phase10_report` and
    :func:`build_sysdesim_timeline_plantuml`.

    :param xml_path: SysDeSim XML/XMI file path.
    :type xml_path: str
    :param machine_name: Optional exact UML state-machine name.
    :type machine_name: str, optional
    :param interaction_name: Optional exact UML interaction name.
    :type interaction_name: str, optional
    :param options: Optional rendering options.
    :type options: SysDeSimTimelinePlantumlOptions, optional
    :return: Full PlantUML source text.
    :rtype: str
    """
    report = build_sysdesim_phase10_report(
        xml_path,
        machine_name=machine_name,
        interaction_name=interaction_name,
    )
    return build_sysdesim_timeline_plantuml(report, options=options)


__all__ = [
    "SysDeSimTimelinePlantumlOptions",
    "build_sysdesim_timeline_plantuml",
    "build_sysdesim_timeline_plantuml_from_xml",
]

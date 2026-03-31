"""
PlantUML sequence-diagram export for SysDeSim timeline reports.

This module implements the Phase 12 timeline visualization path for the
current SysDeSim importer. The exported diagram is intentionally review-first:
it renders the imported interaction order, imported ``SetInput`` observations,
normalized temporal constraints, and optional hidden auto-transition notes from
the already-built timeline report rather than re-parsing the raw XML into a
separate display model.

The primary public APIs are :func:`build_sysdesim_timeline_plantuml` and
:func:`build_sysdesim_timeline_plantuml_from_xml`.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple

from .timeline import (
    SysDeSimMessageObservation,
    SysDeSimStateInvariantObservation,
)
from .timeline_verify import SysDeSimPhase10Report, build_sysdesim_phase10_report


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
    all_aliases = tuple(alias for alias, _ in participant_order)
    all_alias_text = ",".join(all_aliases) if all_aliases else default_alias

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
    right_constraint_index: Dict[str, List[Tuple[str, str]]] = {}
    for item in report.scenario.temporal_constraints:
        right_constraint_index.setdefault(item.right_step_id, []).append(
            (
                item.constraint_id,
                "{left} -> {right} : {value}".format(
                    left=item.left_step_id,
                    right=item.right_step_id,
                    value=_constraint_value_text(
                        item.min_seconds_text,
                        item.max_seconds_text,
                        item.strict_lower,
                    ),
                ),
            )
        )

    auto_notes_by_step = _collect_auto_notes(report) if options.include_hidden_auto else {}

    title = options.title or interaction.interaction_name or report.scenario.name or "SysDeSim Timeline"

    lines = [
        "@startuml",
        "hide footbox",
        "skinparam sequenceMessageAlign center",
        'skinparam responseMessageBelowArrow true',
        f"title {_escape_text(title)}",
        "",
    ]
    for alias, label in participant_order:
        lines.append(f'participant "{_escape_text(label)}" as {alias}')
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
                "{src} -> {dst} : [{step}] {label}".format(
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
            lines.append(f"note over {target_alias} : [{step.step_id}] {_escape_text(note_text)}")
        else:
            note_text = "; ".join(_escape_text(item) for item in step.notes) if step.notes else "anchor"
            lines.append(f"note over {internal_alias} : [{step.step_id}] {note_text}")

        for constraint_id, constraint_text in right_constraint_index.get(step.step_id, ()):
            if options.include_debug_comments:
                lines.append(f"' temporal_constraint_id={constraint_id}")
            lines.append(
                f"note over {all_alias_text} : [{constraint_id}] {_escape_text(constraint_text)}"
            )

        for auto_note in auto_notes_by_step.get(step.step_id, ()):
            lines.append(f"note over {internal_alias} : {_escape_text(auto_note)}")

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

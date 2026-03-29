"""
Hand-build a timeline candidate from one SysDeSim XMI sample.

This script is intentionally sample-driven and conservative. It does not try to
become the production importer. Its purpose is:

* inspect one real SysDeSim XMI file,
* extract a state-machine-centric event subset,
* detect composite-source outgoing transitions that should be treated as force
  transitions,
* convert sequence-diagram observations into a readable timeline candidate.

Example::

    python tools/sysdesim_hand_timeline_sample.py path/to/model.xml
"""

from __future__ import annotations

import argparse
import re
import xml.etree.ElementTree as ET
from typing import Dict, List, Optional, Tuple

from pyfcstm.convert.sysdesim.convert import load_sysdesim_xml

_XMI_NS = "http://www.omg.org/spec/XMI/20131001"
_XMI_ID = f"{{{_XMI_NS}}}id"
_XMI_TYPE = f"{{{_XMI_NS}}}type"
_ASSIGN_RE = re.compile(r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*([^\s].*?)\s*$")


def _normalize_name(name: str) -> str:
    """Normalize a free-text variable name into a stable timeline key."""
    raw = re.sub(r"[^0-9A-Za-z_]+", "_", name.strip())
    raw = re.sub(r"_+", "_", raw).strip("_").lower()
    if raw == "rmt":
        return "r_mt"
    return raw


def _parse_state_invariant_body(fragment: ET.Element) -> Optional[Tuple[str, str]]:
    """Extract a simple ``name=value`` assignment from one state invariant."""
    body_text = None
    for sub in fragment.iter():
        if sub.tag.split("}")[-1] == "body":
            text = (sub.text or "").strip()
            if text:
                body_text = text
                break
    if not body_text:
        return None

    match = _ASSIGN_RE.match(body_text)
    if not match:
        return None
    return _normalize_name(match.group(1)), match.group(2).strip()


def _build_signal_maps(root: ET.Element) -> Tuple[Dict[str, str], Dict[str, str]]:
    """Build signal-id and signal-event-id lookup tables."""
    signal_names: Dict[str, str] = {}
    signal_event_to_signal: Dict[str, str] = {}
    for element in root.iter():
        etype = element.get(_XMI_TYPE)
        if etype == "uml:Signal":
            signal_names[element.get(_XMI_ID)] = element.get("name") or ""
        elif etype == "uml:SignalEvent":
            event_id = element.get(_XMI_ID)
            signal_id = element.get("signal")
            if event_id and signal_id:
                signal_event_to_signal[event_id] = signal_id
    return signal_names, signal_event_to_signal


def _resolve_signal_name(
    ref_id: Optional[str],
    signal_names: Dict[str, str],
    signal_event_to_signal: Dict[str, str],
) -> str:
    """Resolve a signal or signal-event identifier into the final signal name."""
    if not ref_id:
        return ""
    if ref_id in signal_names:
        return signal_names[ref_id]
    signal_id = signal_event_to_signal.get(ref_id)
    if signal_id:
        return signal_names.get(signal_id, signal_id)
    return ""


def _build_interaction_maps(
    root: ET.Element,
) -> Tuple[Dict[str, str], Dict[str, str], Dict[str, str]]:
    """Build lifeline and message-occurrence lookup tables for one interaction."""
    lifeline_names: Dict[str, str] = {}
    occurrence_to_lifeline: Dict[str, str] = {}
    fragment_to_lifeline: Dict[str, str] = {}
    for element in root.iter():
        etype = element.get(_XMI_TYPE)
        if etype == "uml:Lifeline":
            lifeline_names[element.get(_XMI_ID)] = element.get("name") or ""
        elif etype == "uml:MessageOccurrenceSpecification":
            occurrence_id = element.get(_XMI_ID)
            covered = element.get("covered") or ""
            if occurrence_id:
                occurrence_to_lifeline[occurrence_id] = covered
                fragment_to_lifeline[occurrence_id] = covered
        elif etype == "uml:StateInvariant":
            fragment_id = element.get(_XMI_ID)
            covered = element.get("covered") or ""
            if fragment_id:
                fragment_to_lifeline[fragment_id] = covered
    return lifeline_names, occurrence_to_lifeline, fragment_to_lifeline


def _pick_internal_lifeline(
    interaction: ET.Element,
    fragment_to_lifeline: Dict[str, str],
) -> Optional[str]:
    """Infer the machine-internal lifeline from state-invariant coverage."""
    invariant_counts: Dict[str, int] = {}
    for fragment in interaction.findall("./fragment"):
        if fragment.get(_XMI_TYPE) != "uml:StateInvariant":
            continue
        covered = fragment_to_lifeline.get(fragment.get(_XMI_ID) or "", "")
        if not covered:
            continue
        invariant_counts[covered] = invariant_counts.get(covered, 0) + 1
    if not invariant_counts:
        return None
    return max(sorted(invariant_counts), key=lambda key: invariant_counts[key])


def _classify_message_direction(
    message: ET.Element,
    occurrence_to_lifeline: Dict[str, str],
    internal_lifeline_id: Optional[str],
) -> str:
    """Classify one message relative to the inferred internal lifeline."""
    send_lifeline = occurrence_to_lifeline.get(message.get("sendEvent") or "", "")
    receive_lifeline = occurrence_to_lifeline.get(message.get("receiveEvent") or "", "")
    if not internal_lifeline_id:
        return "unknown"
    if receive_lifeline == internal_lifeline_id and send_lifeline != internal_lifeline_id:
        return "inbound"
    if send_lifeline == internal_lifeline_id and receive_lifeline != internal_lifeline_id:
        return "outbound"
    if send_lifeline == internal_lifeline_id and receive_lifeline == internal_lifeline_id:
        return "self"
    return "external"


def _extract_machine_signal_summary(xml_path: str) -> Tuple[List[str], List[Tuple[str, str, str]]]:
    """Extract machine-relevant signal names and composite-source force edges."""
    machine = load_sysdesim_xml(xml_path)[0]
    vertices = {vertex.vertex_id: vertex for vertex in machine.walk_vertices()}
    relevant_signals = set()
    force_edges: List[Tuple[str, str, str]] = []
    for transition in machine.walk_transitions():
        if transition.trigger_kind == "signal" and transition.trigger_ref_id:
            # Resolve signal-event id through raw XML in the caller.
            relevant_signals.add(transition.trigger_ref_id)
        source = vertices[transition.source_id]
        target = vertices[transition.target_id]
        if source.is_composite:
            force_edges.append((source.raw_name or source.vertex_id, target.raw_name or target.vertex_id, transition.trigger_ref_id or ""))
    return sorted(relevant_signals), force_edges


def _resolve_duration_constraints(
    root: ET.Element,
    receive_step_by_message_id: Dict[str, str],
) -> List[Tuple[str, str, str]]:
    """Resolve duration constraints between message steps."""
    idx = {element.get(_XMI_ID): element for element in root.iter() if element.get(_XMI_ID)}
    observation_pair_by_id: Dict[str, Tuple[str, str]] = {}
    for element in root.iter():
        if element.get(_XMI_TYPE) == "uml:DurationObservation":
            raw = (element.get("event") or "").split()
            if len(raw) == 2 and element.get(_XMI_ID):
                observation_pair_by_id[element.get(_XMI_ID)] = (raw[0], raw[1])

    constraints: List[Tuple[str, str, str]] = []
    for element in root.iter():
        if element.get(_XMI_TYPE) != "uml:DurationConstraint":
            continue
        spec = next((child for child in list(element) if child.tag.split("}")[-1] == "specification"), None)
        if spec is None:
            continue

        min_duration = idx.get(spec.get("min"))
        max_duration = idx.get(spec.get("max"))
        if min_duration is None or max_duration is None:
            continue

        min_obs = min_duration.get("observation")
        max_obs = max_duration.get("observation")
        if not min_obs or not max_obs:
            continue

        min_pair = observation_pair_by_id.get(min_obs)
        max_pair = observation_pair_by_id.get(max_obs)
        if min_pair is None or max_pair is None or min_pair != max_pair:
            continue

        def _literal(duration_element: ET.Element) -> Optional[str]:
            literal = next((child for child in duration_element.iter() if child.get("value")), None)
            return literal.get("value") if literal is not None else None

        min_value = _literal(min_duration)
        max_value = _literal(max_duration)
        if min_value is None or max_value is None:
            continue

        left_step = receive_step_by_message_id.get(min_pair[0])
        right_step = receive_step_by_message_id.get(min_pair[1])
        if left_step is None or right_step is None:
            continue

        value = min_value if min_value == max_value else f"{min_value}-{max_value}"
        constraints.append((left_step, right_step, value))
    return constraints


def _resolve_time_windows(
    root: ET.Element,
    receive_step_by_message_id: Dict[str, str],
) -> List[Tuple[str, str]]:
    """Resolve per-step time-window anchors from ``TimeConstraint``."""
    idx = {element.get(_XMI_ID): element for element in root.iter() if element.get(_XMI_ID)}
    observation_event_by_id: Dict[str, str] = {}
    for element in root.iter():
        if element.get(_XMI_TYPE) == "uml:TimeObservation" and element.get(_XMI_ID):
            observation_event_by_id[element.get(_XMI_ID)] = element.get("event") or ""

    windows: List[Tuple[str, str]] = []
    for element in root.iter():
        if element.get(_XMI_TYPE) != "uml:TimeConstraint":
            continue
        spec = next((child for child in list(element) if child.tag.split("}")[-1] == "specification"), None)
        if spec is None:
            continue

        min_expr = idx.get(spec.get("min"))
        max_expr = idx.get(spec.get("max"))
        if min_expr is None or max_expr is None:
            continue

        min_obs = min_expr.get("observation")
        max_obs = max_expr.get("observation")
        if not min_obs or not max_obs:
            continue

        min_event = observation_event_by_id.get(min_obs)
        max_event = observation_event_by_id.get(max_obs)
        if not min_event or not max_event or min_event != max_event:
            continue

        step_id = receive_step_by_message_id.get(min_event)
        if step_id is None:
            continue

        def _literal(time_expr: ET.Element) -> Optional[str]:
            literal = next((child for child in time_expr.iter() if child.get("value")), None)
            return literal.get("value") if literal is not None else None

        min_value = _literal(min_expr)
        max_value = _literal(max_expr)
        if min_value is None or max_value is None:
            continue

        value = min_value if min_value == max_value else f"{min_value}-{max_value}"
        windows.append((step_id, value))
    return windows


def build_manual_timeline(xml_path: str) -> str:
    """Build a readable timeline candidate for one real sample."""
    root = ET.parse(xml_path).getroot()
    signal_names, signal_event_to_signal = _build_signal_maps(root)
    relevant_signal_event_ids, force_edges_raw = _extract_machine_signal_summary(xml_path)
    relevant_signal_names = {
        _resolve_signal_name(event_id, signal_names, signal_event_to_signal) or event_id
        for event_id in relevant_signal_event_ids
    }

    interaction = next(element for element in root.iter() if element.get(_XMI_TYPE) == "uml:Interaction")
    lifeline_names, occurrence_to_lifeline, fragment_to_lifeline = _build_interaction_maps(root)
    internal_lifeline_id = _pick_internal_lifeline(interaction, fragment_to_lifeline)
    internal_lifeline_name = lifeline_names.get(internal_lifeline_id or "", "<unknown>")
    messages = interaction.findall("./message")
    msg_by_recv = {message.get("receiveEvent"): message for message in messages}

    lines: List[str] = []
    lines.append("sample_summary:")
    lines.append(f"  inferred_internal_lifeline: {internal_lifeline_name}")
    lines.append("  machine_relevant_signals:")
    for name in sorted(relevant_signal_names):
        lines.append(f"    - {name}")
    inbound_relevant_signals = set()
    outbound_relevant_signals = set()
    for message in messages:
        signal_name = _resolve_signal_name(message.get("signature"), signal_names, signal_event_to_signal)
        if signal_name not in relevant_signal_names:
            continue
        direction = _classify_message_direction(message, occurrence_to_lifeline, internal_lifeline_id)
        if direction == "inbound":
            inbound_relevant_signals.add(signal_name)
        elif direction == "outbound":
            outbound_relevant_signals.add(signal_name)
    lines.append("  inbound_machine_relevant_signals:")
    for name in sorted(inbound_relevant_signals):
        lines.append(f"    - {name}")
    lines.append("  outbound_machine_relevant_signals:")
    for name in sorted(outbound_relevant_signals):
        lines.append(f"    - {name}")
    lines.append("  force_transitions:")
    for source_name, target_name, signal_event_id in force_edges_raw:
        signal_name = _resolve_signal_name(signal_event_id, signal_names, signal_event_to_signal) or signal_event_id or "<none>"
        lines.append(f"    - from: {source_name}")
        lines.append(f"      to: {target_name}")
        lines.append(f"      event: {signal_name}")
        lines.append("      semantics: force_transition")
    lines.append("  direction_mismatches:")
    if outbound_relevant_signals:
        for name in sorted(outbound_relevant_signals):
            lines.append(f"    - {name}: machine transition consumes this signal, but the interaction observes it as outbound")
    else:
        lines.append("    - none")

    lines.append("manual_timeline_candidate:")
    lines.append("  notes:")
    lines.append("    - This is a sample-driven candidate, not the final importer output.")
    lines.append("    - Steps come from interaction receive-side message order plus state-invariant observations.")
    lines.append(
        "    - The internal lifeline is inferred from where StateInvariant fragments appear; only external-to-internal messages become emit candidates."
    )
    lines.append(
        "    - Internal-to-external messages are preserved as empty timing anchors with annotations, so duration constraints still have stable endpoints."
    )
    lines.append("    - Internal self-messages and unnamed messages without signature are represented as anchor steps.")
    lines.append("    - StateInvariant bodies like name=value are lowered into SetInput candidates.")
    lines.append("    - Signal references may point either to uml:Signal or to uml:SignalEvent; the sample script resolves both.")
    lines.append("  steps:")

    step_index = 0
    receive_step_by_message_id: Dict[str, str] = {}
    first_observed_inputs: Dict[str, Tuple[str, str]] = {}

    for fragment in interaction.findall("./fragment"):
        ftype = fragment.get(_XMI_TYPE)
        if ftype == "uml:MessageOccurrenceSpecification":
            message = msg_by_recv.get(fragment.get(_XMI_ID))
            if message is None:
                continue

            step_index += 1
            step_id = f"s{step_index:02d}"
            receive_step_by_message_id[message.get(_XMI_ID)] = step_id

            signature_id = message.get("signature")
            signal_name = _resolve_signal_name(signature_id, signal_names, signal_event_to_signal)
            direction = _classify_message_direction(message, occurrence_to_lifeline, internal_lifeline_id)
            send_lifeline_name = lifeline_names.get(
                occurrence_to_lifeline.get(message.get("sendEvent") or "", ""),
                "<unknown>",
            )
            receive_lifeline_name = lifeline_names.get(
                occurrence_to_lifeline.get(message.get("receiveEvent") or "", ""),
                "<unknown>",
            )
            lines.append(f"    - id: {step_id}")
            lines.append(f"      direction: {direction}")
            lines.append(f"      endpoints: {send_lifeline_name} -> {receive_lifeline_name}")
            if signature_id and signal_name and direction == "inbound":
                relevant = "true" if signal_name in relevant_signal_names else "false"
                lines.append("      actions:")
                lines.append(f"        - emit: {signal_name}")
                lines.append(f"      machine_relevant: {relevant}")
                if message.get("name"):
                    lines.append(f"      note: inbound signal {signal_name}; display_name={message.get('name')}")
            elif signature_id and signal_name:
                relevant = "true" if signal_name in relevant_signal_names else "false"
                lines.append("      actions: []")
                lines.append("      kind: anchor")
                lines.append(f"      machine_relevant: {relevant}")
                if direction == "outbound":
                    note = f"outbound signal observation; signal={signal_name}"
                elif direction == "self":
                    note = f"internal self-message anchor; signal={signal_name}"
                else:
                    note = f"non-inbound message anchor; signal={signal_name}"
                if message.get("name"):
                    note = f"{note}; display_name={message.get('name')}"
                lines.append(f"      note: {note}")
            else:
                lines.append("      actions: []")
                lines.append("      kind: anchor")
                if direction == "self":
                    lines.append("      note: internal self-message anchor without signature")
                else:
                    lines.append("      note: unlabeled interaction anchor without signature")

        elif ftype == "uml:StateInvariant":
            parsed = _parse_state_invariant_body(fragment)
            if parsed is None:
                continue
            name, value = parsed
            step_index += 1
            step_id = f"s{step_index:02d}"
            first_observed_inputs.setdefault(name, (step_id, value))
            lines.append(f"    - id: {step_id}")
            lines.append("      direction: observation")
            lines.append("      actions:")
            lines.append(f"        - set: {{{name}: {value}}}")
            lines.append("      source: state_invariant")

    lines.append("  first_observed_inputs:")
    for name in sorted(first_observed_inputs):
        step_id, value = first_observed_inputs[name]
        lines.append(f"    {name}:")
        lines.append(f"      step: {step_id}")
        lines.append(f"      value: {value}")

    constraints = _resolve_duration_constraints(root, receive_step_by_message_id)
    windows = _resolve_time_windows(root, receive_step_by_message_id)
    lines.append("  time_windows:")
    for step_id, value in windows:
        lines.append(f"    - step: {step_id}")
        lines.append(f"      value: {value}")
    lines.append("  duration_constraints:")
    for left_step, right_step, value in constraints:
        lines.append(f"    - between: [{left_step}, {right_step}]")
        lines.append(f"      value: {value}")

    return "\n".join(lines)


def main() -> None:
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(description="Hand-build a timeline candidate from one SysDeSim sample.")
    parser.add_argument("xml_path", help="Path to the SysDeSim XMI/XML sample.")
    args = parser.parse_args()
    print(build_manual_timeline(args.xml_path))


if __name__ == "__main__":
    main()

"""
Phase5/6 timeline-oriented extraction helpers for SysDeSim XML/XMI inputs.

This module sits beside the FCSTM compatibility converter and focuses on the
timeline-first view of one SysDeSim sample:

* Phase5: extract interaction lifelines, messages, state invariants, and
  duration/time constraints into a stable observation stream.
* Phase6: expose a unified transition-trigger abstraction and normalized name
  binding hints shared by interaction observations and machine triggers.
* Phase7: classify machine-graph transitions plus input/event binding
  candidates for a timeline-first import IR.
* Phase8: turn the observation stream into ordered step, ``SetInput``, and
  ``emit`` candidates with timing-anchor metadata.

The APIs in this file still stop short of producing a final executable timeline
scenario. They intentionally keep the output at the "reviewable intermediate
data" layer so the user can inspect what was actually extracted from the real
sample before later runtime/SMT binding stages.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from typing import Dict, Iterable, List, Optional, Tuple
from xml.etree import ElementTree as ET

from unidecode import unidecode

from ...dsl import node as dsl_nodes
from .convert import load_sysdesim_machine, normalize_machine
from .ir import IrDiagnostic, IrMachine, IrSignal, IrTransition
from .xmi import SysDeSimRawXmiDocument, load_sysdesim_raw_xmi

_XMI_NS = "http://www.omg.org/spec/XMI/20131001"
_XMI_ID = f"{{{_XMI_NS}}}id"
_XMI_TYPE = f"{{{_XMI_NS}}}type"
_ASSIGNMENT_TEXT = re.compile(
    r"^\s*([A-Za-z_][A-Za-z0-9_]*)\s*=\s*(.+?)\s*$", re.DOTALL
)
_CONDITION_IDENTIFIER = re.compile(r"\b[A-Za-z_][A-Za-z0-9_]*\b")
_CONDITION_KEYWORDS = {"and", "or", "not", "true", "false", "True", "False"}
_NAME_TOKEN = re.compile(r"[a-z0-9]+")


def _xmi_id(element: ET.Element) -> str:
    """Return the required ``xmi:id`` from one XML element."""
    return element.attrib[_XMI_ID]


def _xmi_type(element: ET.Element) -> str:
    """Return the raw ``xmi:type`` string from one XML element."""
    return element.attrib.get(_XMI_TYPE, "")


def _normalize_name_key(text: str) -> str:
    """
    Normalize one raw variable-like name into a comparison key.

    The current rule is deliberately simple and stable:

    * ASCII-fold via :func:`unidecode`
    * lower-case
    * keep only alphanumeric token content
    * drop separators such as ``_`` and whitespace

    This is enough for the current sample patterns such as ``Rmt`` / ``rmt`` /
    ``R_mt`` -> ``rmt``.
    """

    ascii_text = unidecode(text or "").lower()
    return "".join(_NAME_TOKEN.findall(ascii_text))


def _extract_expr_variable_names(expr: Optional[dsl_nodes.Expr]) -> Iterable[str]:
    """Yield variable names referenced inside one parsed DSL expression."""
    if expr is None:
        return
    if isinstance(expr, dsl_nodes.Name):
        yield expr.name
    elif isinstance(expr, dsl_nodes.BinaryOp):
        yield from _extract_expr_variable_names(expr.expr1)
        yield from _extract_expr_variable_names(expr.expr2)
    elif isinstance(expr, dsl_nodes.ConditionalOp):
        yield from _extract_expr_variable_names(expr.cond)
        yield from _extract_expr_variable_names(expr.value_true)
        yield from _extract_expr_variable_names(expr.value_false)
    elif isinstance(expr, dsl_nodes.Paren):
        yield from _extract_expr_variable_names(expr.expr)
    elif isinstance(expr, dsl_nodes.UnaryOp):
        yield from _extract_expr_variable_names(expr.expr)
    elif isinstance(expr, dsl_nodes.UFunc):
        yield from _extract_expr_variable_names(expr.expr)


def _condition_signature(text: Optional[str]) -> Optional[str]:
    """Build a whitespace-insensitive signature for one condition string."""
    if text is None:
        return None
    normalized = text.strip()
    if not normalized:
        return None
    return re.sub(r"\s+", "", normalized)


def _normalize_condition_text(text: str) -> str:
    """Normalize variable-like identifiers inside one condition text."""

    def _replace(match: re.Match) -> str:
        token = match.group(0)
        if token in _CONDITION_KEYWORDS:
            return token
        normalized = _normalize_name_key(token)
        return normalized or token

    return _CONDITION_IDENTIFIER.sub(_replace, text)


def _first_non_empty_body(element: Optional[ET.Element]) -> Optional[str]:
    """Return the first non-empty ``body`` text or ``value`` inside one element."""
    if element is None:
        return None
    value = element.attrib.get("value")
    if value and value.strip():
        return value.strip()
    for body in element.findall("body"):
        text = (body.text or "").strip()
        if text:
            return text
    for child in element:
        nested = _first_non_empty_body(child)
        if nested:
            return nested
    return None


def _parse_assignment_text(
    text: Optional[str],
) -> Tuple[Optional[str], Optional[str], Optional[str]]:
    """
    Parse a simple ``name=value`` observation text.

    :return: ``(raw_name, normalized_name, value_text)`` triple.
    """

    if text is None:
        return None, None, None
    match = _ASSIGNMENT_TEXT.fullmatch(text.strip())
    if not match:
        return None, None, None
    raw_name = match.group(1)
    return raw_name, _normalize_name_key(raw_name), match.group(2).strip()


def _extract_interval_bound_text(
    raw_document: SysDeSimRawXmiDocument, bound_id: Optional[str]
) -> Optional[str]:
    """Resolve the human-readable literal text behind one time/duration bound id."""
    if not bound_id:
        return None
    element = raw_document.xmi_index.get(bound_id)
    if element is None:
        return None
    value = _first_non_empty_body(element)
    if value:
        return value
    nested_expr = element.find("expr")
    if nested_expr is not None:
        value = _first_non_empty_body(nested_expr)
        if value:
            return value
    return element.attrib.get("name") or None


def _message_display_name(
    message_element: ET.Element, signal_name: Optional[str]
) -> str:
    """Return the preferred human-readable message label."""
    return message_element.attrib.get("name", "") or signal_name or ""


def _direction_from_lifelines(
    source_lifeline_id: Optional[str],
    target_lifeline_id: Optional[str],
    internal_lifeline_ids: Iterable[str],
) -> str:
    """Classify one message direction relative to the internal machine lifeline(s)."""
    internal_ids = set(internal_lifeline_ids)
    if source_lifeline_id and source_lifeline_id == target_lifeline_id:
        return "self"
    source_internal = source_lifeline_id in internal_ids
    target_internal = target_lifeline_id in internal_ids
    if (not source_internal) and target_internal:
        return "inbound"
    if source_internal and (not target_internal):
        return "outbound"
    if source_internal and target_internal:
        return "internal"
    return "external"


@dataclass(frozen=True)
class SysDeSimTimelineLifeline:
    """One lifeline extracted from a UML interaction."""

    lifeline_id: str
    raw_name: str
    normalized_name: str
    represents_id: Optional[str]
    is_machine_internal: bool


@dataclass(frozen=True)
class SysDeSimMessageObservation:
    """One message observation anchored inside the interaction order."""

    kind: str
    order_index: int
    message_id: str
    raw_name: str
    display_name: str
    normalized_name: str
    signal_id: Optional[str]
    signal_name: Optional[str]
    signature_type: Optional[str]
    send_occurrence_id: Optional[str]
    receive_occurrence_id: Optional[str]
    source_lifeline_id: Optional[str]
    source_lifeline_name: Optional[str]
    target_lifeline_id: Optional[str]
    target_lifeline_name: Optional[str]
    direction: str


@dataclass(frozen=True)
class SysDeSimStateInvariantObservation:
    """One ``StateInvariant`` observation, optionally parsed as ``name=value``."""

    kind: str
    order_index: int
    invariant_id: str
    lifeline_id: Optional[str]
    lifeline_name: Optional[str]
    raw_text: Optional[str]
    assignment_name: Optional[str]
    normalized_name: Optional[str]
    value_text: Optional[str]


@dataclass(frozen=True)
class SysDeSimDurationConstraintObservation:
    """One duration constraint anchored to two interaction elements."""

    kind: str
    order_index: int
    constraint_id: str
    constrained_element_ids: Tuple[str, ...]
    min_text: Optional[str]
    max_text: Optional[str]
    min_observation_id: Optional[str]
    max_observation_id: Optional[str]


@dataclass(frozen=True)
class SysDeSimTimeConstraintObservation:
    """One time-window constraint anchored to one interaction element."""

    kind: str
    order_index: int
    constraint_id: str
    constrained_element_ids: Tuple[str, ...]
    min_text: Optional[str]
    max_text: Optional[str]
    min_observation_id: Optional[str]
    max_observation_id: Optional[str]


@dataclass(frozen=True)
class SysDeSimActivityAssignmentObservation:
    """One simple assignment-like observation parsed from an activity object."""

    activity_id: str
    raw_text: str
    assignment_name: str
    normalized_name: str
    value_text: str


@dataclass(frozen=True)
class SysDeSimInteractionExtract:
    """Phase5 extraction result for one UML interaction."""

    interaction_id: str
    interaction_name: str
    lifelines: Tuple[SysDeSimTimelineLifeline, ...]
    internal_lifeline_ids: Tuple[str, ...]
    observation_stream: Tuple[object, ...]
    activity_assignment_observations: Tuple[SysDeSimActivityAssignmentObservation, ...]


@dataclass(frozen=True)
class SysDeSimTriggerSignal:
    """Unified trigger abstraction for a signal-triggered machine edge."""

    kind: str
    signal_id: str
    signal_name: str
    signal_display_name: Optional[str]
    trigger_ref_id: Optional[str]


@dataclass(frozen=True)
class SysDeSimTriggerCondition:
    """Unified trigger abstraction for a guard/change-condition edge."""

    kind: str
    raw_text: str
    normalized_text: str
    variable_names: Tuple[str, ...]
    normalized_variable_names: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimTriggerNone:
    """Unified trigger abstraction for a plain no-trigger edge."""

    kind: str


@dataclass(frozen=True)
class SysDeSimTimelineTransitionView:
    """Phase6 trigger-normalized view of one machine transition."""

    source_id: str
    source_path: Tuple[str, ...]
    target_id: str
    target_path: Tuple[str, ...]
    transition_ids: Tuple[str, ...]
    trigger: object


@dataclass(frozen=True)
class SysDeSimNameBindingHint:
    """Name-alignment hint shared by trigger conditions and observation inputs."""

    normalized_name: str
    observation_names: Tuple[str, ...]
    trigger_variable_names: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimPhase56Report:
    """Reviewable intermediate result for the current Phase5/6 extraction scope."""

    selected_machine_name: str
    selected_interaction_name: str
    interaction: SysDeSimInteractionExtract
    transitions: Tuple[SysDeSimTimelineTransitionView, ...]
    name_hints: Tuple[SysDeSimNameBindingHint, ...]
    diagnostics: Tuple[IrDiagnostic, ...]


@dataclass(frozen=True)
class SysDeSimTimelineMachineTransition:
    """Timeline-first machine-graph edge derived from one normalized transition."""

    source_id: str
    source_path: Tuple[str, ...]
    source_vertex_type: str
    target_id: str
    target_path: Tuple[str, ...]
    target_vertex_type: str
    transition_ids: Tuple[str, ...]
    semantic_kind: str
    trigger: object
    machine_event_path: Optional[str]
    guard_text: Optional[str]
    force_transition: bool
    notes: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimTimelineInputCandidate:
    """Candidate binding between scenario-side input names and machine names."""

    normalized_name: str
    role: str
    scenario_names: Tuple[str, ...]
    machine_local_names: Tuple[str, ...]
    observation_values: Tuple[str, ...]
    trigger_expressions: Tuple[str, ...]
    write_texts: Tuple[str, ...]
    note: Optional[str]


@dataclass(frozen=True)
class SysDeSimTimelineEventCandidate:
    """Candidate binding between interaction signal observations and machine events."""

    normalized_name: str
    scenario_event_name: str
    machine_event_path: Optional[str]
    machine_signal_names: Tuple[str, ...]
    message_directions: Tuple[str, ...]
    message_ids: Tuple[str, ...]
    message_display_names: Tuple[str, ...]
    transition_ids: Tuple[str, ...]
    emit_allowed: bool
    is_machine_relevant: bool
    note: Optional[str]


@dataclass(frozen=True)
class SysDeSimTimelineSetInputAction:
    """One candidate ``SetInput`` action extracted from a state invariant."""

    kind: str
    input_name: str
    raw_name: str
    machine_local_names: Tuple[str, ...]
    value_text: str
    source_observation_id: str


@dataclass(frozen=True)
class SysDeSimTimelineEmitAction:
    """One candidate ``emit`` action extracted from an inbound signal message."""

    kind: str
    scenario_event_name: str
    machine_event_path: str
    source_message_id: str


@dataclass(frozen=True)
class SysDeSimTimelineStepCandidate:
    """One ordered step candidate derived from the interaction observation stream."""

    step_id: str
    order_index: int
    anchor_kind: str
    actions: Tuple[object, ...]
    source_observation_ids: Tuple[str, ...]
    source_kinds: Tuple[str, ...]
    direction: Optional[str]
    notes: Tuple[str, ...]


@dataclass(frozen=True)
class SysDeSimTimelineStepTimeWindow:
    """One step-local time-window candidate resolved from a ``TimeConstraint``."""

    step_id: str
    constraint_id: str
    source_message_id: str
    value_text: str


@dataclass(frozen=True)
class SysDeSimTimelineDurationConstraint:
    """One between-step duration candidate resolved from a ``DurationConstraint``."""

    left_step_id: str
    right_step_id: str
    constraint_id: str
    left_source_message_id: str
    right_source_message_id: str
    value_text: str


@dataclass(frozen=True)
class SysDeSimPhase78Report:
    """Reviewable intermediate result for the current Phase7/8 extraction scope."""

    selected_machine_name: str
    selected_interaction_name: str
    phase56_report: SysDeSimPhase56Report
    machine_graph: Tuple[SysDeSimTimelineMachineTransition, ...]
    input_candidates: Tuple[SysDeSimTimelineInputCandidate, ...]
    event_candidates: Tuple[SysDeSimTimelineEventCandidate, ...]
    steps: Tuple[SysDeSimTimelineStepCandidate, ...]
    time_windows: Tuple[SysDeSimTimelineStepTimeWindow, ...]
    duration_constraints: Tuple[SysDeSimTimelineDurationConstraint, ...]
    diagnostics: Tuple[IrDiagnostic, ...]


def _extract_activity_assignment_observations(
    raw_document: SysDeSimRawXmiDocument,
) -> Tuple[SysDeSimActivityAssignmentObservation, ...]:
    """Extract conservative ``name=value`` observations from activity names/bodies."""
    results = []
    for activity in raw_document.elements_by_xmi_type.get("uml:Activity", ()):
        candidate_texts = []
        raw_name = activity.attrib.get("name", "")
        if raw_name:
            candidate_texts.append(raw_name)
        for body in activity.findall(".//body"):
            text = (body.text or "").strip()
            if text:
                candidate_texts.append(text)
        for candidate in candidate_texts:
            assignment_name, normalized_name, value_text = _parse_assignment_text(
                candidate
            )
            if assignment_name is None or normalized_name is None or value_text is None:
                continue
            results.append(
                SysDeSimActivityAssignmentObservation(
                    activity_id=_xmi_id(activity),
                    raw_text=candidate,
                    assignment_name=assignment_name,
                    normalized_name=normalized_name,
                    value_text=value_text,
                )
            )
            break
    return tuple(results)


def _iter_interaction_children_by_type(
    interaction_element: ET.Element, raw_type: str
) -> Iterable[ET.Element]:
    """Yield direct interaction children that match one raw ``xmi:type``."""
    for child in interaction_element:
        if _xmi_type(child) == raw_type:
            yield child


def _extract_interaction(
    raw_document: SysDeSimRawXmiDocument, interaction_element: ET.Element
) -> SysDeSimInteractionExtract:
    """Extract one interaction into lifelines plus a stable observation stream."""
    lifeline_elements = list(
        _iter_interaction_children_by_type(interaction_element, "uml:Lifeline")
    )
    fragment_elements = list(
        _iter_interaction_children_by_type(
            interaction_element, "uml:MessageOccurrenceSpecification"
        )
    )
    fragment_elements.extend(
        list(
            _iter_interaction_children_by_type(
                interaction_element, "uml:StateInvariant"
            )
        )
    )
    fragment_elements.extend(
        list(
            _iter_interaction_children_by_type(
                interaction_element, "uml:BehaviorExecutionSpecification"
            )
        )
    )

    ordered_fragments = [
        child
        for child in interaction_element
        if child.tag == "fragment" or _xmi_type(child).startswith("uml:")
    ]
    fragment_order_by_id = {}
    for child in interaction_element.findall("fragment"):
        fragment_order_by_id[_xmi_id(child)] = len(fragment_order_by_id)

    internal_lifeline_ids = []
    for fragment in interaction_element.findall("fragment"):
        if _xmi_type(fragment) != "uml:StateInvariant":
            continue
        covered_id = fragment.attrib.get("covered")
        if covered_id and covered_id not in internal_lifeline_ids:
            internal_lifeline_ids.append(covered_id)

    lifeline_map = {}
    lifelines = []
    for lifeline in lifeline_elements:
        item = SysDeSimTimelineLifeline(
            lifeline_id=_xmi_id(lifeline),
            raw_name=lifeline.attrib.get("name", ""),
            normalized_name=_normalize_name_key(lifeline.attrib.get("name", "")),
            represents_id=lifeline.attrib.get("represents"),
            is_machine_internal=_xmi_id(lifeline) in internal_lifeline_ids,
        )
        lifelines.append(item)
        lifeline_map[item.lifeline_id] = item

    message_anchor_order = {}
    observation_items = []

    for message in _iter_interaction_children_by_type(
        interaction_element, "uml:Message"
    ):
        message_id = _xmi_id(message)
        send_occurrence_id = message.attrib.get("sendEvent")
        receive_occurrence_id = message.attrib.get("receiveEvent")
        order_candidates = [
            fragment_order_by_id[item]
            for item in (send_occurrence_id, receive_occurrence_id)
            if item in fragment_order_by_id
        ]
        order_index = (
            min(order_candidates) if order_candidates else len(observation_items)
        )
        message_anchor_order[message_id] = order_index

        send_occurrence = (
            raw_document.xmi_index.get(send_occurrence_id)
            if send_occurrence_id is not None
            else None
        )
        receive_occurrence = (
            raw_document.xmi_index.get(receive_occurrence_id)
            if receive_occurrence_id is not None
            else None
        )
        source_lifeline_id = (
            send_occurrence.attrib.get("covered")
            if send_occurrence is not None
            else None
        )
        target_lifeline_id = (
            receive_occurrence.attrib.get("covered")
            if receive_occurrence is not None
            else None
        )
        signature_id = message.attrib.get("signature")
        signature_element = (
            raw_document.xmi_index.get(signature_id)
            if signature_id is not None
            else None
        )
        signal_name = (
            signature_element.attrib.get("name")
            if signature_element is not None
            and _xmi_type(signature_element) == "uml:Signal"
            else None
        )
        display_name = _message_display_name(message, signal_name)
        observation_items.append(
            SysDeSimMessageObservation(
                kind="message",
                order_index=order_index,
                message_id=message_id,
                raw_name=message.attrib.get("name", ""),
                display_name=display_name,
                normalized_name=_normalize_name_key(display_name),
                signal_id=signature_id if signal_name is not None else None,
                signal_name=signal_name,
                signature_type=_xmi_type(signature_element)
                if signature_element is not None
                else None,
                send_occurrence_id=send_occurrence_id,
                receive_occurrence_id=receive_occurrence_id,
                source_lifeline_id=source_lifeline_id,
                source_lifeline_name=(
                    lifeline_map[source_lifeline_id].raw_name
                    if source_lifeline_id in lifeline_map
                    else None
                ),
                target_lifeline_id=target_lifeline_id,
                target_lifeline_name=(
                    lifeline_map[target_lifeline_id].raw_name
                    if target_lifeline_id in lifeline_map
                    else None
                ),
                direction=_direction_from_lifelines(
                    source_lifeline_id, target_lifeline_id, internal_lifeline_ids
                ),
            )
        )

    for fragment in interaction_element.findall("fragment"):
        if _xmi_type(fragment) != "uml:StateInvariant":
            continue
        raw_text = _first_non_empty_body(fragment.find("invariant"))
        assignment_name, normalized_name, value_text = _parse_assignment_text(raw_text)
        covered_id = fragment.attrib.get("covered")
        observation_items.append(
            SysDeSimStateInvariantObservation(
                kind="state_invariant",
                order_index=fragment_order_by_id[_xmi_id(fragment)],
                invariant_id=_xmi_id(fragment),
                lifeline_id=covered_id,
                lifeline_name=(
                    lifeline_map[covered_id].raw_name
                    if covered_id in lifeline_map
                    else None
                ),
                raw_text=raw_text,
                assignment_name=assignment_name,
                normalized_name=normalized_name,
                value_text=value_text,
            )
        )

    rule_fallback_order = len(fragment_order_by_id) + 1000
    for offset, rule in enumerate(interaction_element.findall("ownedRule")):
        rule_type = _xmi_type(rule)
        if rule_type not in {"uml:DurationConstraint", "uml:TimeConstraint"}:
            continue
        constrained_ids = tuple(
            item for item in rule.attrib.get("constrainedElement", "").split() if item
        )
        order_candidates = [
            message_anchor_order[item]
            for item in constrained_ids
            if item in message_anchor_order
        ]
        order_index = (
            min(order_candidates) if order_candidates else rule_fallback_order + offset
        )
        specification = rule.find("specification")
        min_id = specification.attrib.get("min") if specification is not None else None
        max_id = specification.attrib.get("max") if specification is not None else None
        common_kwargs = dict(
            order_index=order_index,
            constraint_id=_xmi_id(rule),
            constrained_element_ids=constrained_ids,
            min_text=_extract_interval_bound_text(raw_document, min_id),
            max_text=_extract_interval_bound_text(raw_document, max_id),
            min_observation_id=(
                raw_document.xmi_index[min_id].attrib.get("observation")
                if min_id and min_id in raw_document.xmi_index
                else None
            ),
            max_observation_id=(
                raw_document.xmi_index[max_id].attrib.get("observation")
                if max_id and max_id in raw_document.xmi_index
                else None
            ),
        )
        if rule_type == "uml:DurationConstraint":
            observation_items.append(
                SysDeSimDurationConstraintObservation(
                    kind="duration_constraint", **common_kwargs
                )
            )
        else:
            observation_items.append(
                SysDeSimTimeConstraintObservation(
                    kind="time_constraint", **common_kwargs
                )
            )

    observation_items.sort(
        key=lambda item: (
            item.order_index,
            item.kind,
            getattr(
                item,
                "message_id",
                getattr(item, "invariant_id", getattr(item, "constraint_id", "")),
            ),
        )
    )

    return SysDeSimInteractionExtract(
        interaction_id=_xmi_id(interaction_element),
        interaction_name=interaction_element.attrib.get("name", ""),
        lifelines=tuple(lifelines),
        internal_lifeline_ids=tuple(internal_lifeline_ids),
        observation_stream=tuple(observation_items),
        activity_assignment_observations=_extract_activity_assignment_observations(
            raw_document
        ),
    )


def extract_sysdesim_interactions(
    xml_path: str,
) -> Tuple[SysDeSimInteractionExtract, ...]:
    """
    Extract all UML interactions from one SysDeSim XML/XMI file.

    :param xml_path: Path to the source XML/XMI file.
    :type xml_path: str
    :return: Extracted interactions in document order.
    :rtype: tuple[SysDeSimInteractionExtract, ...]
    """

    raw_document = load_sysdesim_raw_xmi(xml_path)
    return tuple(
        _extract_interaction(raw_document, element)
        for element in raw_document.elements_by_xmi_type.get("uml:Interaction", ())
    )


def _build_transition_trigger(machine: IrMachine, transition: IrTransition) -> object:
    """Build the Phase6 unified trigger abstraction for one normalized transition."""
    if transition.trigger_kind == "signal" and transition.trigger_ref_id is not None:
        signal_event = machine.get_signal_event(transition.trigger_ref_id)
        signal = machine.get_signal(signal_event.signal_id)
        return SysDeSimTriggerSignal(
            kind="signal",
            signal_id=signal.signal_id,
            signal_name=signal.safe_name or signal.raw_name,
            signal_display_name=signal.display_name,
            trigger_ref_id=transition.trigger_ref_id,
        )
    if transition.guard_expr_raw:
        variable_names = tuple(
            sorted(set(_extract_expr_variable_names(transition.guard_expr_ir)))
        )
        return SysDeSimTriggerCondition(
            kind="condition",
            raw_text=transition.guard_expr_raw,
            normalized_text=_normalize_condition_text(transition.guard_expr_raw),
            variable_names=variable_names,
            normalized_variable_names=tuple(
                _normalize_name_key(item) for item in variable_names
            ),
        )
    return SysDeSimTriggerNone(kind="none")


def _transition_group_key(
    machine: IrMachine, transition: IrTransition
) -> Tuple[object, ...]:
    """Build the Phase6 grouping key used for unified-trigger transition views."""
    trigger = _build_transition_trigger(machine, transition)
    if isinstance(trigger, SysDeSimTriggerSignal):
        trigger_key = ("signal", trigger.signal_id)
    elif isinstance(trigger, SysDeSimTriggerCondition):
        trigger_key = ("condition", _condition_signature(trigger.normalized_text))
    else:
        trigger_key = ("none", None)
    return transition.source_id, transition.target_id, trigger_key


def _build_transition_views(
    machine: IrMachine,
) -> Tuple[SysDeSimTimelineTransitionView, ...]:
    """Build grouped Phase6 transition views from one normalized machine."""
    grouped: Dict[Tuple[object, ...], List[IrTransition]] = {}
    for transition in machine.walk_transitions():
        grouped.setdefault(_transition_group_key(machine, transition), []).append(
            transition
        )

    views = []
    for transitions in grouped.values():
        first = transitions[0]
        first_trigger = _build_transition_trigger(machine, first)
        if isinstance(first_trigger, SysDeSimTriggerCondition):
            raw_texts = sorted(
                {
                    item.guard_expr_raw
                    for item in transitions
                    if item.guard_expr_raw is not None and item.guard_expr_raw.strip()
                }
            )
            variable_names = sorted(
                {
                    variable_name
                    for item in transitions
                    for variable_name in _extract_expr_variable_names(
                        item.guard_expr_ir
                    )
                }
            )
            trigger = SysDeSimTriggerCondition(
                kind="condition",
                raw_text=raw_texts[0]
                if len(raw_texts) == 1
                else _normalize_condition_text(raw_texts[0]),
                normalized_text=_normalize_condition_text(first.guard_expr_raw or ""),
                variable_names=tuple(variable_names),
                normalized_variable_names=tuple(
                    _normalize_name_key(item) for item in variable_names
                ),
            )
        else:
            trigger = first_trigger
        views.append(
            SysDeSimTimelineTransitionView(
                source_id=first.source_id,
                source_path=machine.state_path(first.source_id),
                target_id=first.target_id,
                target_path=machine.state_path(first.target_id),
                transition_ids=tuple(item.transition_id for item in transitions),
                trigger=trigger,
            )
        )
    views.sort(
        key=lambda item: (item.source_path, item.target_path, item.transition_ids)
    )
    return tuple(views)


def _build_name_hints(
    interaction: SysDeSimInteractionExtract,
    transitions: Tuple[SysDeSimTimelineTransitionView, ...],
) -> Tuple[SysDeSimNameBindingHint, ...]:
    """Build normalized name-alignment hints shared by observations and triggers."""
    observation_names: Dict[str, List[str]] = {}
    trigger_names: Dict[str, List[str]] = {}

    for item in interaction.observation_stream:
        if isinstance(item, SysDeSimStateInvariantObservation):
            if item.normalized_name and item.assignment_name:
                observation_names.setdefault(item.normalized_name, []).append(
                    item.assignment_name
                )
    for item in interaction.activity_assignment_observations:
        observation_names.setdefault(item.normalized_name, []).append(
            item.assignment_name
        )

    for transition in transitions:
        trigger = transition.trigger
        if isinstance(trigger, SysDeSimTriggerCondition):
            for raw_name, normalized_name in zip(
                trigger.variable_names, trigger.normalized_variable_names
            ):
                trigger_names.setdefault(normalized_name, []).append(raw_name)

    keys = sorted(set(observation_names) | set(trigger_names))
    return tuple(
        SysDeSimNameBindingHint(
            normalized_name=key,
            observation_names=tuple(sorted(set(observation_names.get(key, [])))),
            trigger_variable_names=tuple(sorted(set(trigger_names.get(key, [])))),
        )
        for key in keys
    )


def build_sysdesim_phase56_report(
    xml_path: str,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
) -> SysDeSimPhase56Report:
    """
    Build the current Phase5/6 intermediate extraction report.

    :param xml_path: Path to the source XML/XMI file.
    :type xml_path: str
    :param machine_name: Optional machine name to select, defaults to ``None``.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction name to select, defaults to
        ``None``.
    :type interaction_name: str, optional
    :return: Reviewable Phase5/6 report.
    :rtype: SysDeSimPhase56Report
    :raises KeyError: If the requested interaction name is not found.
    """

    interactions = extract_sysdesim_interactions(xml_path)
    if interaction_name is None:
        if not interactions:
            raise KeyError("No uml:Interaction found in the SysDeSim XML/XMI file.")
        interaction = interactions[0]
    else:
        for item in interactions:
            if item.interaction_name == interaction_name:
                interaction = item
                break
        else:
            raise KeyError(
                "SysDeSim interaction name {!r} not found in {!r}.".format(
                    interaction_name, xml_path
                )
            )

    machine = normalize_machine(
        load_sysdesim_machine(xml_path, machine_name=machine_name)
    )
    transitions = _build_transition_views(machine)
    return SysDeSimPhase56Report(
        selected_machine_name=machine.display_name or machine.name,
        selected_interaction_name=interaction.interaction_name,
        interaction=interaction,
        transitions=transitions,
        name_hints=_build_name_hints(interaction, transitions),
        diagnostics=tuple(machine.diagnostics),
    )


def _unique_non_empty(items: Iterable[Optional[str]]) -> Tuple[str, ...]:
    """Return unique non-empty strings while preserving their first-seen order."""
    results = []
    seen = set()
    for item in items:
        if item is None:
            continue
        text = item.strip()
        if not text or text in seen:
            continue
        seen.add(text)
        results.append(text)
    return tuple(results)


def _combine_interval_text(
    min_text: Optional[str], max_text: Optional[str]
) -> Optional[str]:
    """Combine one min/max interval pair into a single readable value."""
    if min_text and max_text:
        return min_text if min_text == max_text else f"{min_text}-{max_text}"
    return min_text or max_text


def _is_force_transition(
    machine: IrMachine, transition: SysDeSimTimelineTransitionView
) -> bool:
    """Return whether one grouped machine edge should be treated as force transition."""
    source_vertex = machine.get_vertex(transition.source_id)
    if source_vertex.vertex_type != "state" or not source_vertex.is_composite:
        return False
    descendants = set(machine.descendant_state_ids(transition.source_id))
    return (
        transition.target_id != transition.source_id
        and transition.target_id not in descendants
    )


def _build_machine_graph(
    machine: IrMachine,
    transitions: Tuple[SysDeSimTimelineTransitionView, ...],
) -> Tuple[SysDeSimTimelineMachineTransition, ...]:
    """Build the Phase7 machine-graph view used by the timeline importer."""
    results = []
    for transition in transitions:
        source_vertex = machine.get_vertex(transition.source_id)
        target_vertex = machine.get_vertex(transition.target_id)
        notes = []
        machine_event_path = None
        guard_text = None
        if isinstance(transition.trigger, SysDeSimTriggerSignal):
            semantic_kind = "signal_transition"
            machine_event_path = f"/{transition.trigger.signal_name}"
        elif isinstance(transition.trigger, SysDeSimTriggerCondition):
            semantic_kind = "condition_transition"
            guard_text = transition.trigger.raw_text
        elif source_vertex.vertex_type == "pseudostate":
            semantic_kind = "initial_transition"
        else:
            semantic_kind = "auto_transition"
            notes.append("hidden_internal_transition")
            notes.append("continuous_time_binding_deferred")

        force_transition = _is_force_transition(machine, transition)
        if force_transition:
            notes.append("force_transition")

        results.append(
            SysDeSimTimelineMachineTransition(
                source_id=transition.source_id,
                source_path=transition.source_path,
                source_vertex_type=source_vertex.vertex_type,
                target_id=transition.target_id,
                target_path=transition.target_path,
                target_vertex_type=target_vertex.vertex_type,
                transition_ids=transition.transition_ids,
                semantic_kind=semantic_kind,
                trigger=transition.trigger,
                machine_event_path=machine_event_path,
                guard_text=guard_text,
                force_transition=force_transition,
                notes=tuple(notes),
            )
        )
    results.sort(
        key=lambda item: (
            item.source_path,
            item.target_path,
            item.semantic_kind,
            item.transition_ids,
        )
    )
    return tuple(results)


def _build_input_candidates(
    interaction: SysDeSimInteractionExtract,
    transitions: Tuple[SysDeSimTimelineTransitionView, ...],
) -> Tuple[SysDeSimTimelineInputCandidate, ...]:
    """Build input-binding candidates shared by observations and condition triggers."""
    evidence: Dict[str, Dict[str, List[str]]] = {}

    def _entry(normalized_name: str) -> Dict[str, List[str]]:
        return evidence.setdefault(
            normalized_name,
            {
                "scenario_names": [],
                "machine_local_names": [],
                "observation_values": [],
                "trigger_expressions": [],
                "write_texts": [],
            },
        )

    for item in interaction.observation_stream:
        if not isinstance(item, SysDeSimStateInvariantObservation):
            continue
        if not item.normalized_name or not item.assignment_name:
            continue
        entry = _entry(item.normalized_name)
        entry["scenario_names"].append(item.assignment_name)
        if item.value_text:
            entry["observation_values"].append(item.value_text)

    for item in interaction.activity_assignment_observations:
        entry = _entry(item.normalized_name)
        entry["machine_local_names"].append(item.assignment_name)
        entry["write_texts"].append(item.raw_text)

    for transition in transitions:
        if not isinstance(transition.trigger, SysDeSimTriggerCondition):
            continue
        for raw_name, normalized_name in zip(
            transition.trigger.variable_names,
            transition.trigger.normalized_variable_names,
        ):
            entry = _entry(normalized_name)
            entry["machine_local_names"].append(raw_name)
            entry["trigger_expressions"].append(transition.trigger.raw_text)

    results = []
    for normalized_name in sorted(evidence):
        item = evidence[normalized_name]
        scenario_names = _unique_non_empty(item["scenario_names"])
        machine_local_names = _unique_non_empty(item["machine_local_names"])
        observation_values = _unique_non_empty(item["observation_values"])
        trigger_expressions = _unique_non_empty(item["trigger_expressions"])
        write_texts = _unique_non_empty(item["write_texts"])

        if trigger_expressions and not write_texts:
            role = "external_input"
            note = (
                "Condition/change variables default to external inputs until "
                "explicit write evidence appears."
            )
        elif trigger_expressions and write_texts:
            role = "ambiguous"
            note = (
                "The name appears both in trigger conditions and in write-side "
                "activity text; keep it reviewable instead of forcing one role."
            )
        elif write_texts:
            role = "internal_state"
            note = "Only write-side activity evidence exists for this name."
        else:
            role = "observation_only"
            note = "The name is observed in the interaction but not referenced by current triggers."

        results.append(
            SysDeSimTimelineInputCandidate(
                normalized_name=normalized_name,
                role=role,
                scenario_names=scenario_names,
                machine_local_names=machine_local_names,
                observation_values=observation_values,
                trigger_expressions=trigger_expressions,
                write_texts=write_texts,
                note=note,
            )
        )
    return tuple(results)


def _build_event_candidates(
    interaction: SysDeSimInteractionExtract,
    machine_graph: Tuple[SysDeSimTimelineMachineTransition, ...],
) -> Tuple[Tuple[SysDeSimTimelineEventCandidate, ...], Tuple[IrDiagnostic, ...]]:
    """Build event-binding candidates shared by message observations and machine signals."""
    machine_signal_index: Dict[str, Dict[str, List[str]]] = {}
    for transition in machine_graph:
        if transition.semantic_kind != "signal_transition":
            continue
        trigger = transition.trigger
        if not isinstance(trigger, SysDeSimTriggerSignal):
            continue
        key = _normalize_name_key(trigger.signal_name)
        entry = machine_signal_index.setdefault(
            key,
            {
                "machine_event_paths": [],
                "machine_signal_names": [],
                "transition_ids": [],
            },
        )
        if transition.machine_event_path:
            entry["machine_event_paths"].append(transition.machine_event_path)
        entry["machine_signal_names"].append(trigger.signal_name)
        entry["transition_ids"].extend(transition.transition_ids)

    grouped_messages: Dict[str, List[SysDeSimMessageObservation]] = {}
    for item in interaction.observation_stream:
        if not isinstance(item, SysDeSimMessageObservation) or not item.signal_name:
            continue
        grouped_messages.setdefault(_normalize_name_key(item.signal_name), []).append(
            item
        )

    results = []
    diagnostics = []
    for normalized_name in sorted(grouped_messages):
        messages = sorted(
            grouped_messages[normalized_name],
            key=lambda item: (item.order_index, item.message_id),
        )
        machine_item = machine_signal_index.get(normalized_name, {})
        machine_event_paths = _unique_non_empty(
            machine_item.get("machine_event_paths", [])
        )
        machine_signal_names = _unique_non_empty(
            machine_item.get("machine_signal_names", [])
        )
        transition_ids = _unique_non_empty(machine_item.get("transition_ids", []))
        message_directions = _unique_non_empty(item.direction for item in messages)
        message_ids = tuple(item.message_id for item in messages)
        message_display_names = _unique_non_empty(
            item.display_name for item in messages
        )
        is_machine_relevant = bool(machine_event_paths or machine_signal_names)
        emit_allowed = is_machine_relevant and "inbound" in message_directions
        scenario_event_name = messages[0].signal_name or messages[0].display_name

        note = None
        if (
            is_machine_relevant
            and "outbound" in message_directions
            and "inbound" not in message_directions
        ):
            note = (
                "The state machine consumes this signal, but the interaction only "
                "shows outbound observations."
            )
            diagnostics.append(
                IrDiagnostic(
                    level="warning",
                    code="timeline_outbound_machine_signal",
                    message=(
                        "Signal {!r} is machine-relevant, but the interaction only "
                        "observes it as outbound."
                    ).format(scenario_event_name),
                    source_id=messages[0].message_id,
                )
            )
        elif is_machine_relevant and len(message_directions) > 1:
            note = (
                "This signal appears with mixed directions; only inbound "
                "message instances can become emit candidates."
            )
        elif not is_machine_relevant:
            note = "This signal appears in the interaction but not in the current machine trigger set."

        results.append(
            SysDeSimTimelineEventCandidate(
                normalized_name=normalized_name,
                scenario_event_name=scenario_event_name,
                machine_event_path=machine_event_paths[0]
                if machine_event_paths
                else None,
                machine_signal_names=machine_signal_names,
                message_directions=message_directions,
                message_ids=message_ids,
                message_display_names=message_display_names,
                transition_ids=transition_ids,
                emit_allowed=emit_allowed,
                is_machine_relevant=is_machine_relevant,
                note=note,
            )
        )

    return tuple(results), tuple(diagnostics)


def _sort_step_actions(actions: Iterable[object]) -> Tuple[object, ...]:
    """Sort step actions so that ``SetInput`` stays before ``emit`` within one step."""
    order = {"set_input": 0, "emit": 1}
    return tuple(
        sorted(actions, key=lambda item: order.get(getattr(item, "kind", ""), 99))
    )


def _build_step_candidates(
    interaction: SysDeSimInteractionExtract,
    input_candidates: Tuple[SysDeSimTimelineInputCandidate, ...],
    event_candidates: Tuple[SysDeSimTimelineEventCandidate, ...],
) -> Tuple[
    Tuple[SysDeSimTimelineStepCandidate, ...],
    Tuple[SysDeSimTimelineStepTimeWindow, ...],
    Tuple[SysDeSimTimelineDurationConstraint, ...],
]:
    """Build ordered step, time-window, and duration candidates from the observation stream."""
    input_candidate_index = {item.normalized_name: item for item in input_candidates}
    event_candidate_index = {item.normalized_name: item for item in event_candidates}

    steps = []
    time_windows = []
    duration_constraints = []
    message_step_by_id: Dict[str, str] = {}
    step_counter = 0

    for item in interaction.observation_stream:
        if isinstance(item, SysDeSimMessageObservation):
            step_counter += 1
            step_id = f"s{step_counter:02d}"
            actions = []
            notes = []
            event_candidate = (
                event_candidate_index.get(_normalize_name_key(item.signal_name))
                if item.signal_name
                else None
            )
            if (
                item.signal_name
                and item.direction == "inbound"
                and event_candidate is not None
                and event_candidate.is_machine_relevant
                and event_candidate.machine_event_path
            ):
                actions.append(
                    SysDeSimTimelineEmitAction(
                        kind="emit",
                        scenario_event_name=item.signal_name,
                        machine_event_path=event_candidate.machine_event_path,
                        source_message_id=item.message_id,
                    )
                )
            else:
                if item.direction == "outbound" and item.signal_name:
                    notes.append(f"outbound_signal={item.signal_name}")
                    if (
                        event_candidate is not None
                        and event_candidate.is_machine_relevant
                    ):
                        notes.append("machine_relevant_direction_mismatch")
                elif item.direction == "self":
                    notes.append("self_message")
                    if item.signal_name:
                        notes.append(f"self_signal={item.signal_name}")
                elif item.direction == "inbound" and item.signal_name:
                    notes.append(f"inbound_observation={item.signal_name}")
                elif not item.signal_name:
                    notes.append("no_signature_message")

            if item.raw_name and item.raw_name != item.display_name:
                notes.append(f"display_name={item.raw_name}")

            steps.append(
                SysDeSimTimelineStepCandidate(
                    step_id=step_id,
                    order_index=item.order_index,
                    anchor_kind="message",
                    actions=_sort_step_actions(actions),
                    source_observation_ids=(item.message_id,),
                    source_kinds=(item.kind,),
                    direction=item.direction,
                    notes=tuple(notes),
                )
            )
            message_step_by_id[item.message_id] = step_id

        elif isinstance(item, SysDeSimStateInvariantObservation):
            if (
                not item.assignment_name
                or not item.normalized_name
                or item.value_text is None
            ):
                continue
            step_counter += 1
            step_id = f"s{step_counter:02d}"
            input_candidate = input_candidate_index.get(item.normalized_name)
            machine_local_names = (
                input_candidate.machine_local_names
                if input_candidate is not None
                else ()
            )
            actions = [
                SysDeSimTimelineSetInputAction(
                    kind="set_input",
                    input_name=item.normalized_name,
                    raw_name=item.assignment_name,
                    machine_local_names=machine_local_names,
                    value_text=item.value_text,
                    source_observation_id=item.invariant_id,
                )
            ]
            steps.append(
                SysDeSimTimelineStepCandidate(
                    step_id=step_id,
                    order_index=item.order_index,
                    anchor_kind="state_invariant",
                    actions=_sort_step_actions(actions),
                    source_observation_ids=(item.invariant_id,),
                    source_kinds=(item.kind,),
                    direction=None,
                    notes=(),
                )
            )

    for item in interaction.observation_stream:
        if isinstance(item, SysDeSimTimeConstraintObservation):
            if len(item.constrained_element_ids) != 1:
                continue
            source_message_id = item.constrained_element_ids[0]
            step_id = message_step_by_id.get(source_message_id)
            value_text = _combine_interval_text(item.min_text, item.max_text)
            if step_id is None or value_text is None:
                continue
            time_windows.append(
                SysDeSimTimelineStepTimeWindow(
                    step_id=step_id,
                    constraint_id=item.constraint_id,
                    source_message_id=source_message_id,
                    value_text=value_text,
                )
            )
        elif isinstance(item, SysDeSimDurationConstraintObservation):
            if len(item.constrained_element_ids) != 2:
                continue
            left_message_id, right_message_id = item.constrained_element_ids
            left_step_id = message_step_by_id.get(left_message_id)
            right_step_id = message_step_by_id.get(right_message_id)
            value_text = _combine_interval_text(item.min_text, item.max_text)
            if left_step_id is None or right_step_id is None or value_text is None:
                continue
            duration_constraints.append(
                SysDeSimTimelineDurationConstraint(
                    left_step_id=left_step_id,
                    right_step_id=right_step_id,
                    constraint_id=item.constraint_id,
                    left_source_message_id=left_message_id,
                    right_source_message_id=right_message_id,
                    value_text=value_text,
                )
            )

    return tuple(steps), tuple(time_windows), tuple(duration_constraints)


def build_sysdesim_phase78_report(
    xml_path: str,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
) -> SysDeSimPhase78Report:
    """
    Build the current Phase7/8 timeline-import report.

    :param xml_path: Path to the source XML/XMI file.
    :type xml_path: str
    :param machine_name: Optional machine name to select, defaults to ``None``.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction name to select, defaults to
        ``None``.
    :type interaction_name: str, optional
    :return: Reviewable Phase7/8 report.
    :rtype: SysDeSimPhase78Report
    """

    phase56_report = build_sysdesim_phase56_report(
        xml_path, machine_name=machine_name, interaction_name=interaction_name
    )
    machine = normalize_machine(
        load_sysdesim_machine(xml_path, machine_name=machine_name)
    )
    machine_graph = _build_machine_graph(machine, phase56_report.transitions)
    input_candidates = _build_input_candidates(
        phase56_report.interaction, phase56_report.transitions
    )
    event_candidates, event_diagnostics = _build_event_candidates(
        phase56_report.interaction, machine_graph
    )
    steps, time_windows, duration_constraints = _build_step_candidates(
        phase56_report.interaction, input_candidates, event_candidates
    )
    diagnostics = tuple(phase56_report.diagnostics) + tuple(event_diagnostics)

    return SysDeSimPhase78Report(
        selected_machine_name=phase56_report.selected_machine_name,
        selected_interaction_name=phase56_report.selected_interaction_name,
        phase56_report=phase56_report,
        machine_graph=machine_graph,
        input_candidates=input_candidates,
        event_candidates=event_candidates,
        steps=steps,
        time_windows=time_windows,
        duration_constraints=duration_constraints,
        diagnostics=diagnostics,
    )


__all__ = [
    "SysDeSimActivityAssignmentObservation",
    "SysDeSimDurationConstraintObservation",
    "SysDeSimInteractionExtract",
    "SysDeSimMessageObservation",
    "SysDeSimNameBindingHint",
    "SysDeSimPhase56Report",
    "SysDeSimPhase78Report",
    "SysDeSimStateInvariantObservation",
    "SysDeSimTimelineDurationConstraint",
    "SysDeSimTimelineEmitAction",
    "SysDeSimTimelineEventCandidate",
    "SysDeSimTimelineInputCandidate",
    "SysDeSimTimeConstraintObservation",
    "SysDeSimTimelineLifeline",
    "SysDeSimTimelineMachineTransition",
    "SysDeSimTimelineSetInputAction",
    "SysDeSimTimelineStepCandidate",
    "SysDeSimTimelineStepTimeWindow",
    "SysDeSimTimelineTransitionView",
    "SysDeSimTriggerCondition",
    "SysDeSimTriggerNone",
    "SysDeSimTriggerSignal",
    "build_sysdesim_phase56_report",
    "build_sysdesim_phase78_report",
    "extract_sysdesim_interactions",
]

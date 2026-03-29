"""
Phase5/6 timeline-oriented extraction helpers for SysDeSim XML/XMI inputs.

This module sits beside the FCSTM compatibility converter and focuses on the
timeline-first view of one SysDeSim sample:

* Phase5: extract interaction lifelines, messages, state invariants, and
  duration/time constraints into a stable observation stream.
* Phase6: expose a unified transition-trigger abstraction and normalized name
  binding hints shared by interaction observations and machine triggers.

The APIs in this file do not try to build final timeline steps yet. They stop
at the "reviewable intermediate data" layer so the user can inspect what was
actually extracted from the real sample before Phase7/8 candidate generation.
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


__all__ = [
    "SysDeSimActivityAssignmentObservation",
    "SysDeSimDurationConstraintObservation",
    "SysDeSimInteractionExtract",
    "SysDeSimMessageObservation",
    "SysDeSimNameBindingHint",
    "SysDeSimPhase56Report",
    "SysDeSimStateInvariantObservation",
    "SysDeSimTimeConstraintObservation",
    "SysDeSimTimelineLifeline",
    "SysDeSimTimelineTransitionView",
    "SysDeSimTriggerCondition",
    "SysDeSimTriggerNone",
    "SysDeSimTriggerSignal",
    "build_sysdesim_phase56_report",
    "extract_sysdesim_interactions",
]

"""
SysDeSim XML to FCSTM phase0-3 conversion helpers.

This module contains the full phase0-3 pipeline:

1. Parse SysDeSim XML into the dataclass IR.
2. Normalize names, variables, and guard expressions.
3. Build FCSTM DSL AST for the supported subset.
4. Emit DSL text and validate it with the existing parser/model stack.

The implementation intentionally stops before cross-level lowering and
parallel-region splitting. Those cases are rejected explicitly so the
supported boundary stays clear.

The module contains:

* :func:`load_sysdesim_xml` and :func:`load_sysdesim_machine` for XML loading.
* :func:`normalize_machine` for identifier and guard normalization.
* :func:`build_machine_ast` and :func:`emit_program` for FCSTM emission.
* :func:`validate_program_roundtrip` for parser/model validation.
* :func:`convert_sysdesim_xml_to_ast` and
  :func:`convert_sysdesim_xml_to_dsl` for one-shot conversion.

Example::

    >>> from pyfcstm.convert.sysdesim.convert import load_sysdesim_machine, normalize_machine
    >>> machine = load_sysdesim_machine("sample.sysdesim.xml")
    >>> machine = normalize_machine(machine)
    >>> machine.safe_name is not None
    True
"""

from __future__ import annotations

import math
import re
import xml.etree.ElementTree as ET
from dataclasses import dataclass, field
from typing import Dict, Iterable, List, Optional, Tuple

from unidecode import unidecode

from ...dsl import parse_condition, parse_with_grammar_entry
from ...dsl import node as dsl_nodes
from ...model.model import parse_dsl_node_to_state_machine
from .ir import (
    IrActionRef,
    IrDiagnostic,
    IrMachine,
    IrRegion,
    IrSignal,
    IrSignalEvent,
    IrTimeEvent,
    IrTransition,
    IrVariable,
    IrVertex,
)

_XMI_NS = "http://www.omg.org/spec/XMI/20131001"
_XMI_ID = f"{{{_XMI_NS}}}id"
_XMI_TYPE = f"{{{_XMI_NS}}}type"
_VALID_FCSTM_ID = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_TIME_LITERAL = re.compile(r"^\s*(\d+(?:\.\d+)?)\s*(s|ms|us)\s*$")
_DEFAULT_FLOAT = {"uml:LiteralReal", "uml:LiteralUnlimitedNatural"}
_DEFAULT_INT = {"uml:LiteralInteger", "uml:LiteralNatural"}


@dataclass(frozen=True)
class _LoweredTimeTransition:
    """
    Internal lowering metadata for one original UML time-triggered transition.

    :param transition_id: Original transition identifier.
    :type transition_id: str
    :param source_id: Source state identifier.
    :type source_id: str
    :param timer_name: Generated timer variable name.
    :type timer_name: str
    :param ticks: Timer threshold in runtime ticks.
    :type ticks: int
    :param guard_expr: Final lowered guard expression.
    :type guard_expr: pyfcstm.dsl.node.Expr
    """

    transition_id: str
    source_id: str
    timer_name: str
    ticks: int
    guard_expr: dsl_nodes.Expr


@dataclass(frozen=True)
class _LoweredExitChainTransition:
    """
    Internal synthetic exit transition produced for composite timeout lowering.

    :param source_id: Direct child state that should exit upward.
    :type source_id: str
    :param guard_expr: Guard shared by the full propagated timeout chain.
    :type guard_expr: pyfcstm.dsl.node.Expr
    """

    source_id: str
    guard_expr: dsl_nodes.Expr


@dataclass
class _AstBuildContext:
    """
    Internal AST-build context containing phase3 lowering products.

    :param time_transitions_by_id: Lowered time transitions keyed by original
        transition identifier.
    :type time_transitions_by_id: dict[str, _LoweredTimeTransition]
    :param time_transitions_in_order: Lowered time transitions in source order.
    :type time_transitions_in_order: list[_LoweredTimeTransition]
    :param time_transitions_by_source_id: Lowered time transitions keyed by
        source state identifier.
    :type time_transitions_by_source_id: dict[str, list[_LoweredTimeTransition]]
    :param propagated_exit_chains: Synthetic exit transitions keyed by the
        composite state that owns the containing region.
    :type propagated_exit_chains: dict[str, list[_LoweredExitChainTransition]]
    """

    time_transitions_by_id: Dict[str, _LoweredTimeTransition] = field(default_factory=dict)
    time_transitions_in_order: List[_LoweredTimeTransition] = field(default_factory=list)
    time_transitions_by_source_id: Dict[str, List[_LoweredTimeTransition]] = field(default_factory=dict)
    propagated_exit_chains: Dict[str, List[_LoweredExitChainTransition]] = field(default_factory=dict)


def _xmi_id(element: ET.Element) -> str:
    """
    Return the XMI identifier of an XML element.

    :param element: XML element expected to carry an XMI identifier.
    :type element: xml.etree.ElementTree.Element
    :return: Value of the ``xmi:id`` attribute.
    :rtype: str
    :raises KeyError: If the element does not define ``xmi:id``.
    """
    return element.attrib[_XMI_ID]


def _xmi_type(element: ET.Element) -> str:
    """
    Return the UML/XMI type tag of an XML element.

    :param element: XML element that may carry an ``xmi:type`` attribute.
    :type element: xml.etree.ElementTree.Element
    :return: Raw ``xmi:type`` value, or ``''`` when missing.
    :rtype: str
    """
    return element.attrib.get(_XMI_TYPE, "")


def _text_or_none(text: Optional[str]) -> Optional[str]:
    """
    Return stripped text or ``None`` for empty values.

    :param text: Input text that may contain surrounding whitespace.
    :type text: str, optional
    :return: Stripped non-empty text, or ``None`` when the input is empty.
    :rtype: str, optional
    """
    if text is None:
        return None
    text = text.strip()
    return text or None


def _parse_action_ref(element: Optional[ET.Element]) -> Optional[IrActionRef]:
    """
    Build an action reference from an XML action node.

    :param element: XML element describing an entry, exit, or effect action.
    :type element: xml.etree.ElementTree.Element, optional
    :return: Parsed action reference, or ``None`` when the element is absent.
    :rtype: IrActionRef, optional
    """
    if element is None:
        return None
    return IrActionRef(
        action_id=_xmi_id(element),
        raw_name=element.attrib.get("name", ""),
    )


def _parse_constraint_body(container: ET.Element) -> Optional[str]:
    """
    Extract the first non-empty opaque-expression body from a UML container.

    :param container: UML element that may own one or more ``ownedRule`` nodes.
    :type container: xml.etree.ElementTree.Element
    :return: First non-empty rule body, or ``None`` when not found.
    :rtype: str, optional
    """
    for rule in container.findall("ownedRule"):
        specification = rule.find("specification")
        if specification is None:
            continue
        body = _text_or_none(specification.findtext("body"))
        if body is not None:
            return body
    return None


def _parse_default_value(element: ET.Element) -> Optional[str]:
    """
    Parse a primitive default value from a UML property element.

    :param element: UML property element that may define ``defaultValue``.
    :type element: xml.etree.ElementTree.Element
    :return: Default value as source text, or ``None`` when absent.
    :rtype: str, optional
    """
    default = element.find("defaultValue")
    if default is None:
        return None
    if _xmi_type(default) in _DEFAULT_INT:
        return default.attrib.get("value", "0")
    if _xmi_type(default) in _DEFAULT_FLOAT:
        return default.attrib.get("value", "0.0")
    value = default.attrib.get("value")
    if value is not None:
        return value
    return _text_or_none(default.text)


def _parse_primitive_type_name(
    element: ET.Element, xmi_index: Dict[str, ET.Element]
) -> Optional[str]:
    """
    Map a UML primitive type reference to the FCSTM type name.

    :param element: UML property element containing a type reference.
    :type element: xml.etree.ElementTree.Element
    :param xmi_index: Index of XML elements keyed by ``xmi:id``.
    :type xmi_index: dict[str, xml.etree.ElementTree.Element]
    :return: Normalized FCSTM type name, or ``None`` when no type is available.
    :rtype: str, optional
    """
    type_ref = element.attrib.get("type")
    if type_ref and type_ref in xmi_index:
        name = xmi_index[type_ref].attrib.get("name", "")
        lowered = name.lower()
        if lowered in {"integer", "int"}:
            return "int"
        if lowered in {"real", "float", "double"}:
            return "float"
        return lowered or name

    type_element = element.find("type")
    if type_element is None:
        return None

    href = type_element.attrib.get("href", "")
    if href:
        suffix = href.rsplit("#", 1)[-1].rsplit("/", 1)[-1].lower()
        if suffix in {"integer", "int"}:
            return "int"
        if suffix in {"real", "float", "double"}:
            return "float"
        return suffix or None

    name = type_element.attrib.get("name")
    if name:
        lowered = name.lower()
        if lowered in {"integer", "int"}:
            return "int"
        if lowered in {"real", "float", "double"}:
            return "float"
        return lowered

    return None


def _parse_variables(
    machine_element: ET.Element,
    parent_map: Dict[ET.Element, ET.Element],
    xmi_index: Dict[str, ET.Element],
) -> List[IrVariable]:
    """
    Parse explicit UML properties owned by the machine's owning class.

    :param machine_element: UML state machine element.
    :type machine_element: xml.etree.ElementTree.Element
    :param parent_map: Lookup table from child element to parent element.
    :type parent_map: dict[xml.etree.ElementTree.Element, xml.etree.ElementTree.Element]
    :param xmi_index: Index of XML elements keyed by ``xmi:id``.
    :type xmi_index: dict[str, xml.etree.ElementTree.Element]
    :return: Parsed variable definitions owned by the surrounding class.
    :rtype: list[IrVariable]
    """
    owner = parent_map.get(machine_element)
    if owner is None:
        return []

    variables = []
    for child in owner.findall("ownedAttribute"):
        if _xmi_type(child) != "uml:Property":
            continue
        variables.append(
            IrVariable(
                variable_id=_xmi_id(child),
                raw_name=child.attrib.get("name", ""),
                type_name=_parse_primitive_type_name(child, xmi_index),
                default_value=_parse_default_value(child),
                is_synthetic=False,
            )
        )
    return variables


def _parse_time_event(element: ET.Element) -> IrTimeEvent:
    """
    Parse one UML ``TimeEvent`` element.

    :param element: XML element describing a UML time event.
    :type element: xml.etree.ElementTree.Element
    :return: Parsed time-event IR object.
    :rtype: IrTimeEvent
    """
    raw_literal = ""
    when_element = element.find("when")
    if when_element is not None:
        expr_element = when_element.find("expr")
        if expr_element is not None:
            raw_literal = expr_element.attrib.get("value", "")
    return IrTimeEvent(
        time_event_id=_xmi_id(element),
        raw_literal=raw_literal,
        is_relative=element.attrib.get("isRelative", "false").lower() == "true",
    )


def _parse_region(
    region_element: ET.Element,
    owner_state_id: Optional[str],
    event_types: Dict[str, str],
) -> IrRegion:
    """
    Recursively parse one UML region into IR.

    :param region_element: XML region element to parse.
    :type region_element: xml.etree.ElementTree.Element
    :param owner_state_id: Owning composite-state identifier, or ``None`` for
        the root region
    :type owner_state_id: str, optional
    :param event_types: Mapping from event identifiers to trigger kinds.
    :type event_types: dict[str, str]
    :return: Parsed region IR, including nested vertices and child regions.
    :rtype: IrRegion
    """
    region = IrRegion(region_id=_xmi_id(region_element), owner_state_id=owner_state_id)

    for subvertex in region_element.findall("subvertex"):
        raw_type = _xmi_type(subvertex)
        if raw_type == "uml:State":
            child_regions = [
                _parse_region(child_region, _xmi_id(subvertex), event_types)
                for child_region in subvertex.findall("region")
            ]
            vertex = IrVertex(
                vertex_id=_xmi_id(subvertex),
                vertex_type="state",
                raw_name=subvertex.attrib.get("name", ""),
                parent_region_id=region.region_id,
                entry_action=_parse_action_ref(subvertex.find("entry")),
                exit_action=_parse_action_ref(subvertex.find("exit")),
                state_invariant=_parse_constraint_body(subvertex),
                regions=child_regions,
                is_composite=bool(child_regions),
                is_parallel_owner=len(child_regions) > 1,
            )
        elif raw_type == "uml:Pseudostate":
            vertex = IrVertex(
                vertex_id=_xmi_id(subvertex),
                vertex_type="pseudostate",
                raw_name=subvertex.attrib.get("name", ""),
                parent_region_id=region.region_id,
            )
        elif raw_type == "uml:FinalState":
            vertex = IrVertex(
                vertex_id=_xmi_id(subvertex),
                vertex_type="final",
                raw_name=subvertex.attrib.get("name", ""),
                parent_region_id=region.region_id,
            )
        else:
            vertex = IrVertex(
                vertex_id=_xmi_id(subvertex),
                vertex_type=raw_type.rsplit(":", 1)[-1].lower() or "unknown",
                raw_name=subvertex.attrib.get("name", ""),
                parent_region_id=region.region_id,
            )
        region.vertices.append(vertex)

    for transition_element in region_element.findall("transition"):
        trigger_element = transition_element.find("trigger")
        trigger_ref_id = trigger_element.attrib.get("event") if trigger_element is not None else None
        trigger_kind = "none" if trigger_ref_id is None else event_types.get(trigger_ref_id, "unknown")
        region.transitions.append(
            IrTransition(
                transition_id=_xmi_id(transition_element),
                source_id=transition_element.attrib["source"],
                target_id=transition_element.attrib["target"],
                trigger_kind=trigger_kind,
                trigger_ref_id=trigger_ref_id,
                guard_expr_raw=_parse_constraint_body(transition_element),
                effect_action=_parse_action_ref(transition_element.find("effect")),
                source_region_id=region.region_id,
                target_region_id=region.region_id,
            )
        )

    return region


def load_sysdesim_xml(xml_path: str) -> List[IrMachine]:
    """
    Parse all UML state machines from a SysDeSim XML/XMI file.

    The loader scans the document for UML signals, signal events, time events,
    and state machines, then builds :class:`IrMachine` objects for every
    ``uml:StateMachine`` that has at least one region.

    :param xml_path: Path to the SysDeSim XML/XMI file.
    :type xml_path: str
    :return: Parsed state machines in document order.
    :rtype: list[IrMachine]
    :raises OSError: If the file cannot be read.
    :raises xml.etree.ElementTree.ParseError: If the XML is malformed.

    Example::

        >>> machines = load_sysdesim_xml("sample.sysdesim.xml")
        >>> isinstance(machines, list)
        True
    """
    tree = ET.parse(xml_path)
    root = tree.getroot()
    parent_map = {child: parent for parent in root.iter() for child in parent}
    xmi_index = {element.attrib[_XMI_ID]: element for element in root.iter() if _XMI_ID in element.attrib}

    signals: List[IrSignal] = []
    signal_events: List[IrSignalEvent] = []
    time_events: List[IrTimeEvent] = []
    event_types: Dict[str, str] = {}

    for element in root.iter():
        raw_type = _xmi_type(element)
        if raw_type == "uml:Signal":
            signals.append(IrSignal(signal_id=_xmi_id(element), raw_name=element.attrib.get("name", "")))
        elif raw_type == "uml:SignalEvent":
            signal_events.append(
                IrSignalEvent(
                    event_id=_xmi_id(element),
                    signal_id=element.attrib["signal"],
                    raw_name=element.attrib.get("name", ""),
                )
            )
            event_types[_xmi_id(element)] = "signal"
        elif raw_type == "uml:TimeEvent":
            time_events.append(_parse_time_event(element))
            event_types[_xmi_id(element)] = "time"

    machines = []
    for element in root.iter():
        if _xmi_type(element) != "uml:StateMachine":
            continue
        regions = element.findall("region")
        if not regions:
            continue

        machine = IrMachine(
            machine_id=_xmi_id(element),
            name=element.attrib.get("name", ""),
            root_region=_parse_region(regions[0], None, event_types),
            signals=[IrSignal(**signal.__dict__) for signal in signals],
            signal_events=[IrSignalEvent(**signal_event.__dict__) for signal_event in signal_events],
            time_events=[IrTimeEvent(**time_event.__dict__) for time_event in time_events],
            variables=_parse_variables(element, parent_map, xmi_index),
            diagnostics=[],
        )
        if len(regions) > 1:
            machine.diagnostics.append(
                IrDiagnostic(
                    level="warning",
                    code="multiple_root_regions",
                    message="Top-level state machine has multiple regions; phase0-2 only uses the first root region.",
                    source_id=machine.machine_id,
                )
            )
        machines.append(machine)

    return machines


def load_sysdesim_machine(
    xml_path: str,
    *,
    machine_name: Optional[str] = None,
    machine_id: Optional[str] = None,
) -> IrMachine:
    """
    Load one state machine from a SysDeSim XML/XMI file.

    When ``machine_id`` is provided it takes precedence over ``machine_name``.
    If neither selector is given, the first parsed machine is returned.

    :param xml_path: Path to the SysDeSim XML/XMI file.
    :type xml_path: str
    :param machine_name: Exact UML state-machine name to load, defaults to
        ``None``
    :type machine_name: str, optional
    :param machine_id: Exact UML state-machine ``xmi:id`` to load, defaults to
        ``None``
    :type machine_id: str, optional
    :return: Matching state-machine IR object.
    :rtype: IrMachine
    :raises KeyError: If the requested machine name or identifier is not found.
    :raises ValueError: If the file contains no ``uml:StateMachine`` elements.
    :raises OSError: If the file cannot be read.
    :raises xml.etree.ElementTree.ParseError: If the XML is malformed.

    Example::

        >>> machine = load_sysdesim_machine("sample.sysdesim.xml", machine_name="Door Cycle")
        >>> machine.name
        'Door Cycle'
    """
    machines = load_sysdesim_xml(xml_path)
    if machine_id is not None:
        for machine in machines:
            if machine.machine_id == machine_id:
                return machine
        raise KeyError(f"SysDeSim machine id {machine_id!r} not found in {xml_path!r}.")
    if machine_name is not None:
        for machine in machines:
            if machine.name == machine_name:
                return machine
        raise KeyError(f"SysDeSim machine name {machine_name!r} not found in {xml_path!r}.")
    if not machines:
        raise ValueError(f"No uml:StateMachine found in {xml_path!r}.")
    return machines[0]


def _stable_suffix(raw_id: str, length: int = 6) -> str:
    """
    Return a short stable suffix derived from a source identifier.

    :param raw_id: Source identifier used as the entropy source.
    :type raw_id: str
    :param length: Number of trailing alphanumeric characters to keep, defaults
        to ``6``
    :type length: int
    :return: Sanitized suffix suitable for generated identifiers.
    :rtype: str
    """
    text = re.sub(r"[^A-Za-z0-9]+", "", raw_id)
    if not text:
        text = "sysdesim"
    return text[-length:]


def _tokenize_name(raw_name: str) -> List[str]:
    """
    Tokenize a raw label into ASCII name parts via transliteration.

    :param raw_name: Raw source label.
    :type raw_name: str
    :return: Alphanumeric tokens derived from the transliterated label.
    :rtype: list[str]
    """
    text = unidecode(raw_name or "")
    return [token for token in re.split(r"[^A-Za-z0-9]+", text) if token]


def _base_upper_camel(raw_name: str) -> str:
    """
    Normalize a label to ``UpperCamelCase``.

    :param raw_name: Raw source label.
    :type raw_name: str
    :return: Camel-cased identifier base.
    :rtype: str
    """
    tokens = _tokenize_name(raw_name)
    return "".join(token[:1].upper() + token[1:] for token in tokens)


def _base_upper_snake(raw_name: str) -> str:
    """
    Normalize a label to ``UPPER_SNAKE_CASE``.

    :param raw_name: Raw source label.
    :type raw_name: str
    :return: Upper-snake identifier base.
    :rtype: str
    """
    tokens = _tokenize_name(raw_name)
    return "_".join(token.upper() for token in tokens)


def _base_lower_snake(raw_name: str) -> str:
    """
    Normalize a label to ``lower_snake_case``.

    :param raw_name: Raw source label.
    :type raw_name: str
    :return: Lower-snake identifier base.
    :rtype: str
    """
    tokens = _tokenize_name(raw_name)
    return "_".join(token.lower() for token in tokens)


def _with_unique_suffix(base: str, stable_id: str) -> str:
    """
    Append a deterministic suffix when a normalized name collides.

    :param base: Candidate normalized name.
    :type base: str
    :param stable_id: Source identifier used to derive the suffix.
    :type stable_id: str
    :return: Unique candidate name with a deterministic suffix when needed.
    :rtype: str
    """
    suffix = _stable_suffix(stable_id)
    return f"{base}_{suffix}" if base else suffix


def _make_state_name(vertex: IrVertex) -> str:
    """
    Build the FCSTM identifier for a state-like vertex.

    :param vertex: Vertex whose name should be normalized.
    :type vertex: IrVertex
    :return: FCSTM-safe state identifier.
    :rtype: str
    """
    base = _base_upper_camel(vertex.raw_name)
    if base:
        return base
    return f"__sysdesim_{vertex.vertex_type}_{_stable_suffix(vertex.vertex_id)}"


def _make_action_name(action: IrActionRef) -> str:
    """
    Build the FCSTM identifier for an action placeholder.

    :param action: Action reference whose name should be normalized.
    :type action: IrActionRef
    :return: FCSTM-safe action identifier.
    :rtype: str
    """
    base = _base_upper_camel(action.raw_name)
    if base:
        return base
    return f"__sysdesim_action_{_stable_suffix(action.action_id)}"


def _make_event_name(raw_name: str, stable_id: str) -> str:
    """
    Build the FCSTM identifier for a signal-derived event.

    :param raw_name: Raw source event or signal name.
    :type raw_name: str
    :param stable_id: Source identifier used for collision-resistant fallback.
    :type stable_id: str
    :return: FCSTM-safe event identifier.
    :rtype: str
    """
    base = _base_upper_snake(raw_name)
    if base:
        return base
    return f"__sysdesim_evt_{_stable_suffix(stable_id).upper()}"


def make_internal_name(prefix: str, scope_tokens: Iterable[str], stable_id: str) -> str:
    """
    Create a deterministic ``__sysdesim_*`` internal identifier.

    :param prefix: Category prefix such as ``'var'`` or ``'flag_route'``.
    :type prefix: str
    :param scope_tokens: Additional normalized scope tokens to embed in the
        name.
    :type scope_tokens: collections.abc.Iterable[str]
    :param stable_id: Source identifier used to derive the trailing suffix.
    :type stable_id: str
    :return: Internal identifier reserved for converter-generated artifacts.
    :rtype: str

    Example::

        >>> make_internal_name("flag_route", ["pump_loop"], "transition-001").startswith("__sysdesim_")
        True
    """
    scope_part = "_".join(token for token in scope_tokens if token)
    suffix = _stable_suffix(stable_id).lower()
    if scope_part:
        return f"__sysdesim_{prefix}_{scope_part}_{suffix}"
    return f"__sysdesim_{prefix}_{suffix}"


def _normalize_region_vertices(vertices: List[IrVertex]) -> None:
    """
    Normalize names for all vertices in a region subtree.

    :param vertices: Vertices in the current region subtree.
    :type vertices: list[IrVertex]
    :return: ``None``.
    :rtype: None
    """
    seen = {}
    for vertex in vertices:
        if vertex.vertex_type == "state":
            base = _make_state_name(vertex)
            candidate = base if base not in seen else _with_unique_suffix(base, vertex.vertex_id)
            seen[candidate] = vertex.vertex_id
            vertex.safe_name = candidate
        else:
            vertex.safe_name = _make_state_name(vertex)
        vertex.display_name = vertex.raw_name

        for action in [vertex.entry_action, vertex.exit_action]:
            if action is not None:
                action.safe_name = _make_action_name(action)
                action.display_name = action.raw_name

        for region in vertex.regions:
            _normalize_region_vertices(region.vertices)


def _normalize_variables(variables: List[IrVariable]) -> None:
    """
    Validate and normalize explicit and synthetic variables.

    Explicit variables must already use legal ASCII FCSTM identifiers and must
    declare ``int`` or ``float`` types. Synthetic variables are renamed into the
    reserved ``__sysdesim_*`` namespace.

    :param variables: Variables to validate and normalize in place.
    :type variables: list[IrVariable]
    :return: ``None``.
    :rtype: None
    :raises ValueError: If an explicit variable name or type is unsupported.
    """
    for variable in variables:
        variable.display_name = variable.raw_name
        if variable.is_synthetic:
            variable.safe_name = make_internal_name(
                "var",
                [_base_lower_snake(variable.raw_name)],
                variable.variable_id,
            )
            continue

        if not _VALID_FCSTM_ID.fullmatch(variable.raw_name):
            raise ValueError(
                f"Unsupported explicit variable name {variable.raw_name!r}; "
                f"phase0-2 only accepts legal ASCII FCSTM identifiers."
            )
        if variable.type_name not in {"int", "float", None}:
            raise ValueError(
                f"Unsupported explicit variable type {variable.type_name!r}; "
                f"phase0-2 only supports int and float."
            )
        variable.safe_name = variable.raw_name


def _normalize_events(machine: IrMachine) -> None:
    """
    Normalize signal and event names for FCSTM export.

    :param machine: Machine whose signal names should be normalized in place.
    :type machine: IrMachine
    :return: ``None``.
    :rtype: None
    """
    seen = {}
    for signal in machine.signals:
        base = _make_event_name(signal.raw_name, signal.signal_id)
        candidate = base if seen.get(base) in {None, signal.signal_id} else _with_unique_suffix(base, signal.signal_id)
        seen[candidate] = signal.signal_id
        signal.safe_name = candidate
        signal.display_name = signal.raw_name

    for signal_event in machine.signal_events:
        signal = machine.get_signal(signal_event.signal_id)
        signal_event.safe_name = signal.safe_name
        signal_event.display_name = signal.display_name


def _normalize_time_events(machine: IrMachine) -> None:
    """
    Parse supported time literal formats into normalized delay/unit fields.

    :param machine: Machine whose time events should be normalized in place.
    :type machine: IrMachine
    :return: ``None``.
    :rtype: None
    """
    for time_event in machine.time_events:
        if not time_event.raw_literal:
            continue
        match = _TIME_LITERAL.fullmatch(time_event.raw_literal)
        if match:
            time_event.normalized_delay = float(match.group(1))
            time_event.normalized_unit = match.group(2)


def normalize_machine(machine: IrMachine) -> IrMachine:
    """
    Normalize names, variables, events, and parsed guards for one IR machine.

    This step assigns FCSTM-safe names, parses guard expressions into the
    existing DSL condition AST, and refreshes indexes so later phases can rely
    on normalized metadata.

    :param machine: Machine IR object to normalize.
    :type machine: IrMachine
    :return: The same machine instance after in-place normalization.
    :rtype: IrMachine
    :raises ValueError: If explicit variables use unsupported names or types.
    :raises pyfcstm.dsl.error.GrammarParseError: If a guard expression fails to
        parse.

    Example::

        >>> machine = load_sysdesim_machine("sample.sysdesim.xml")
        >>> normalized = normalize_machine(machine)
        >>> normalized is machine
        True
    """
    machine.safe_name = _make_state_name(
        IrVertex(vertex_id=machine.machine_id, vertex_type="state", raw_name=machine.name)
    )
    machine.display_name = machine.name
    _normalize_region_vertices(machine.root_region.vertices)
    _normalize_events(machine)
    _normalize_variables(machine.variables)
    _normalize_time_events(machine)

    for transition in machine.walk_transitions():
        if transition.guard_expr_raw and transition.guard_expr_raw.strip():
            transition.guard_expr_ir = parse_condition(transition.guard_expr_raw).expr
        else:
            transition.guard_expr_raw = None
            transition.guard_expr_ir = None

    machine.rebuild_indexes()
    return machine


def _timeout_source_scope_tokens(machine: IrMachine, source_id: str) -> List[str]:
    """
    Build normalized source-path tokens used in time-lowering timer names.

    :param machine: Normalized machine containing the source state.
    :type machine: IrMachine
    :param source_id: Source state identifier.
    :type source_id: str
    :return: Lower-snake tokens derived from the full source-state path.
    :rtype: list[str]
    """
    raw_path = machine.state_path(source_id, use_safe_name=False)
    safe_path = machine.state_path(source_id, use_safe_name=True)
    tokens = []
    for raw_name, safe_name in zip(raw_path, safe_path):
        token = _base_lower_snake(raw_name)
        if not token and safe_name is not None:
            token = _base_lower_snake(safe_name)
        if token:
            tokens.append(token)
    if tokens:
        return tokens

    source = machine.get_vertex(source_id)
    fallback = _base_lower_snake(source.safe_name or source.vertex_id)
    return [fallback] if fallback else [_stable_suffix(source.vertex_id).lower()]


def _make_time_event_timer_name(machine: IrMachine, transition: IrTransition) -> str:
    """
    Build the synthetic timer variable name for one UML time transition.

    :param machine: Normalized machine containing the transition.
    :type machine: IrMachine
    :param transition: Original time-triggered transition.
    :type transition: IrTransition
    :return: Reserved timer variable name.
    :rtype: str
    """
    scope_part = "_".join(_timeout_source_scope_tokens(machine, transition.source_id))
    transition_suffix = _stable_suffix(transition.transition_id).lower()
    return f"__sysdesim_after_{scope_part}__tx_{transition_suffix}_ticks"


def _convert_time_event_to_ticks(time_event: IrTimeEvent, tick_duration_ms: float) -> int:
    """
    Convert one normalized UML time literal into runtime ticks.

    :param time_event: Time-event metadata with parsed delay and unit.
    :type time_event: IrTimeEvent
    :param tick_duration_ms: Configured duration of one runtime tick in
        milliseconds.
    :type tick_duration_ms: float
    :return: Required runtime ticks computed with ``ceil`` rounding.
    :rtype: int
    :raises NotImplementedError: If the event is absolute rather than relative.
    :raises ValueError: If the literal cannot be parsed into a supported unit.
    """
    if not time_event.is_relative:
        raise NotImplementedError(
            f"Phase3 only supports relative uml:TimeEvent values: {time_event.time_event_id}"
        )
    if time_event.normalized_delay is None or time_event.normalized_unit is None:
        raise ValueError(f"Unsupported uml:TimeEvent literal {time_event.raw_literal!r}.")

    unit_factor_us = {
        "s": 1_000_000.0,
        "ms": 1_000.0,
        "us": 1.0,
    }.get(time_event.normalized_unit)
    if unit_factor_us is None:  # pragma: no cover - guarded by _TIME_LITERAL
        raise ValueError(f"Unsupported uml:TimeEvent unit {time_event.normalized_unit!r}.")

    delay_us = time_event.normalized_delay * unit_factor_us
    tick_us = tick_duration_ms * 1_000.0
    return int(math.ceil(delay_us / tick_us))


def _build_timeout_guard_expr(
    timer_name: str,
    ticks: int,
    original_guard: Optional[dsl_nodes.Expr],
) -> dsl_nodes.Expr:
    """
    Build the final guard expression used by a lowered timeout transition.

    :param timer_name: Generated timer variable name.
    :type timer_name: str
    :param ticks: Timer threshold in runtime ticks.
    :type ticks: int
    :param original_guard: Original transition guard, defaults to ``None``
    :type original_guard: pyfcstm.dsl.node.Expr, optional
    :return: Lowered timeout guard.
    :rtype: pyfcstm.dsl.node.Expr
    """
    timeout_guard = dsl_nodes.BinaryOp(
        dsl_nodes.Name(timer_name),
        ">=",
        dsl_nodes.Integer(str(ticks)),
    )
    if original_guard is None:
        return timeout_guard
    return dsl_nodes.BinaryOp(dsl_nodes.Paren(timeout_guard), "&&", original_guard)


def _register_propagated_timeout_exit_chain(
    machine: IrMachine,
    composite_source: IrVertex,
    guard_expr: dsl_nodes.Expr,
    sink: Dict[str, List[_LoweredExitChainTransition]],
) -> None:
    """
    Register synthetic upward-exit transitions for one composite timeout source.

    :param machine: Normalized machine containing the composite subtree.
    :type machine: IrMachine
    :param composite_source: Composite source state that owns the timeout.
    :type composite_source: IrVertex
    :param guard_expr: Guard shared by the full timeout exit chain.
    :type guard_expr: pyfcstm.dsl.node.Expr
    :param sink: Output mapping keyed by composite owner state identifier.
    :type sink: dict[str, list[_LoweredExitChainTransition]]
    :return: ``None``.
    :rtype: None
    """
    if not composite_source.regions:
        return

    region = composite_source.regions[0]
    for child in region.vertices:
        if child.vertex_type != "state":
            continue
        sink.setdefault(composite_source.vertex_id, []).append(
            _LoweredExitChainTransition(source_id=child.vertex_id, guard_expr=guard_expr)
        )
        if child.is_composite:
            _register_propagated_timeout_exit_chain(machine, child, guard_expr, sink)


def _build_ast_context(machine: IrMachine, tick_duration_ms: Optional[float]) -> _AstBuildContext:
    """
    Build the internal lowering context required for phase3 AST emission.

    :param machine: Normalized machine to lower.
    :type machine: IrMachine
    :param tick_duration_ms: Configured duration of one runtime tick in
        milliseconds, or ``None`` when no time event is expected.
    :type tick_duration_ms: float, optional
    :return: Internal AST-build context.
    :rtype: _AstBuildContext
    :raises ValueError: If time-triggered transitions exist without a valid
        ``tick_duration_ms`` value.
    :raises NotImplementedError: If a time event is attached to an unsupported
        source shape.
    """
    time_transitions = [transition for transition in machine.walk_transitions() if transition.trigger_kind == "time"]
    if not time_transitions:
        return _AstBuildContext()

    if tick_duration_ms is None:
        raise ValueError("tick_duration_ms is required when lowering uml:TimeEvent transitions.")
    if tick_duration_ms <= 0:
        raise ValueError("tick_duration_ms must be greater than 0.")

    context = _AstBuildContext()
    for transition in time_transitions:
        source = machine.get_vertex(transition.source_id)
        if source.vertex_type != "state":
            raise NotImplementedError(
                f"Phase3 only supports state-backed uml:TimeEvent sources: {transition.transition_id}"
            )
        if transition.effect_action is not None:
            raise NotImplementedError(
                f"Phase3 does not lower transition effects yet: {transition.transition_id}"
            )

        time_event = machine.get_time_event(transition.trigger_ref_id)
        timer_name = _make_time_event_timer_name(machine, transition)
        ticks = _convert_time_event_to_ticks(time_event, tick_duration_ms)
        guard_expr = _build_timeout_guard_expr(timer_name, ticks, transition.guard_expr_ir)

        lowered = _LoweredTimeTransition(
            transition_id=transition.transition_id,
            source_id=transition.source_id,
            timer_name=timer_name,
            ticks=ticks,
            guard_expr=guard_expr,
        )
        context.time_transitions_by_id[transition.transition_id] = lowered
        context.time_transitions_in_order.append(lowered)
        context.time_transitions_by_source_id.setdefault(transition.source_id, []).append(lowered)

        if source.is_composite:
            _register_propagated_timeout_exit_chain(
                machine,
                source,
                guard_expr,
                context.propagated_exit_chains,
            )

    return context


def _display_name_or_none(raw_name: Optional[str], safe_name: Optional[str]) -> Optional[str]:
    """
    Return the display name only when it differs from the FCSTM identifier.

    :param raw_name: Original source name.
    :type raw_name: str, optional
    :param safe_name: Normalized FCSTM-safe identifier.
    :type safe_name: str, optional
    :return: Display name to emit in a ``named`` clause, or ``None`` when the
        names already match.
    :rtype: str, optional
    """
    if not raw_name or raw_name == safe_name:
        return None
    return raw_name


def _is_init_pseudostate(machine: IrMachine, region: IrRegion, vertex: IrVertex) -> bool:
    """
    Return whether a pseudostate matches the phase2 init-state heuristic.

    The phase2 pipeline only supports unnamed pseudostates with no incoming
    transitions and at least one outgoing transition.

    :param machine: Machine containing the region. The argument is accepted for
        interface consistency with other validation helpers.
    :type machine: IrMachine
    :param region: Region that owns the candidate pseudostate.
    :type region: IrRegion
    :param vertex: Candidate vertex.
    :type vertex: IrVertex
    :return: Whether the vertex can be treated as the region's init pseudostate.
    :rtype: bool
    """
    if vertex.vertex_type != "pseudostate":
        return False
    incoming = 0
    outgoing = 0
    for transition in region.transitions:
        if transition.source_id == vertex.vertex_id:
            outgoing += 1
        if transition.target_id == vertex.vertex_id:
            incoming += 1
    return not vertex.raw_name and incoming == 0 and outgoing > 0


def _validate_phase2_region(machine: IrMachine, region: IrRegion) -> None:
    """
    Reject structures that are outside the phase2 support boundary.

    :param machine: Machine being validated.
    :type machine: IrMachine
    :param region: Region to validate recursively.
    :type region: IrRegion
    :return: ``None``.
    :rtype: None
    :raises NotImplementedError: If the region requires unsupported lowering
        features such as parallel regions, unsupported pseudostates, or
        cross-level transitions.
    :raises ValueError: If a composite region does not define exactly one init
        pseudostate.
    """
    init_pseudostates = []
    for vertex in region.vertices:
        if vertex.vertex_type == "state":
            if len(vertex.regions) > 1:
                raise NotImplementedError(
                    f"Phase2 does not support multi-region composite state yet: {vertex.vertex_id}"
                )
            for child_region in vertex.regions:
                _validate_phase2_region(machine, child_region)
        elif vertex.vertex_type == "pseudostate" and _is_init_pseudostate(machine, region, vertex):
            init_pseudostates.append(vertex)
        elif vertex.vertex_type == "pseudostate":
            raise NotImplementedError(
                f"Phase2 only supports init-pseudostate lowering: {vertex.vertex_id}"
            )

    if region.owner_state_id is not None and region.vertices and len(init_pseudostates) != 1:
        raise ValueError(f"Composite state region {region.region_id} must have exactly one init pseudostate.")

    for transition in region.transitions:
        if transition.is_cross_region or transition.is_cross_level:
            raise NotImplementedError(
                f"Phase2 does not support cross-level/cross-region transitions: {transition.transition_id}"
            )


def _build_transition(
    machine: IrMachine,
    transition: IrTransition,
    context: _AstBuildContext,
) -> dsl_nodes.TransitionDefinition:
    """
    Convert a supported IR transition to a DSL transition node.

    :param machine: Normalized machine containing the transition.
    :type machine: IrMachine
    :param transition: Transition to convert.
    :type transition: IrTransition
    :return: FCSTM DSL transition definition.
    :rtype: pyfcstm.dsl.node.TransitionDefinition
    :raises NotImplementedError: If the transition uses unsupported trigger,
        effect, or topology features.
    """
    source = machine.get_vertex(transition.source_id)
    target = machine.get_vertex(transition.target_id)

    lowered_time_transition = context.time_transitions_by_id.get(transition.transition_id)
    if transition.trigger_kind == "time":
        if lowered_time_transition is None:  # pragma: no cover - build_machine_ast prepares this eagerly
            raise RuntimeError(f"Missing lowered time-transition metadata: {transition.transition_id}")
        if transition.effect_action is not None:
            raise NotImplementedError(
                f"Phase3 does not lower transition effects yet: {transition.transition_id}"
            )
        if source.vertex_type != "state" or target.vertex_type != "state":
            raise NotImplementedError(
                f"Phase3 only supports state-to-state uml:TimeEvent transitions: {transition.transition_id}"
            )
        return dsl_nodes.TransitionDefinition(
            from_state=source.safe_name,
            to_state=target.safe_name,
            event_id=None,
            condition_expr=lowered_time_transition.guard_expr,
            post_operations=[],
        )
    if transition.trigger_kind not in {"signal", "none"}:
        raise NotImplementedError(
            f"Phase2 only supports signal/none triggers: {transition.transition_id}"
        )
    if transition.trigger_kind == "signal" and transition.guard_expr_ir is not None:
        raise NotImplementedError(
            f"Phase2 does not support transitions with both signal and guard: {transition.transition_id}"
        )
    if transition.effect_action is not None:
        raise NotImplementedError(
            f"Phase2 does not lower transition effects yet: {transition.transition_id}"
        )

    if source.vertex_type == "pseudostate":
        return dsl_nodes.TransitionDefinition(
            from_state=dsl_nodes.INIT_STATE,
            to_state=target.safe_name,
            event_id=None,
            condition_expr=transition.guard_expr_ir,
            post_operations=[],
        )

    if source.vertex_type != "state" or target.vertex_type != "state":
        raise NotImplementedError(
            f"Phase2 only supports init pseudostate and state-to-state transitions: {transition.transition_id}"
        )

    event_id = None
    if transition.trigger_kind == "signal":
        signal_event = machine.get_signal_event(transition.trigger_ref_id)
        signal = machine.get_signal(signal_event.signal_id)
        event_id = dsl_nodes.ChainID([signal.safe_name], is_absolute=True)

    return dsl_nodes.TransitionDefinition(
        from_state=source.safe_name,
        to_state=target.safe_name,
        event_id=event_id,
        condition_expr=transition.guard_expr_ir,
        post_operations=[],
    )


def _build_state(
    machine: IrMachine,
    vertex: IrVertex,
    context: _AstBuildContext,
    *,
    event_definitions: Optional[List[dsl_nodes.EventDefinition]] = None,
) -> dsl_nodes.StateDefinition:
    """
    Recursively build a DSL state subtree from a normalized IR vertex.

    :param machine: Normalized machine containing the vertex.
    :type machine: IrMachine
    :param vertex: State vertex to convert.
    :type vertex: IrVertex
    :param event_definitions: Event definitions to attach to the current state,
        defaults to ``None``
    :type event_definitions: list[pyfcstm.dsl.node.EventDefinition], optional
    :return: FCSTM DSL state definition.
    :rtype: pyfcstm.dsl.node.StateDefinition
    :raises NotImplementedError: If the state owns unsupported parallel regions.
    """
    enters = []
    durings: List[dsl_nodes.DuringStatement] = []
    exits = []
    during_aspects: List[dsl_nodes.DuringAspectStatement] = []
    if vertex.entry_action is not None:
        enters.append(dsl_nodes.EnterAbstractFunction(vertex.entry_action.safe_name, None))
    if vertex.exit_action is not None:
        exits.append(dsl_nodes.ExitAbstractFunction(vertex.exit_action.safe_name, None))

    time_transitions = context.time_transitions_by_source_id.get(vertex.vertex_id, [])
    if time_transitions:
        enters.append(
            dsl_nodes.EnterOperations(
                [dsl_nodes.OperationAssignment(item.timer_name, dsl_nodes.Integer("0")) for item in time_transitions]
            )
        )
        increment_operations = [
            dsl_nodes.OperationAssignment(
                item.timer_name,
                dsl_nodes.BinaryOp(dsl_nodes.Name(item.timer_name), "+", dsl_nodes.Integer("1")),
            )
            for item in time_transitions
        ]
        if vertex.is_composite:
            during_aspects.append(dsl_nodes.DuringAspectOperations("after", increment_operations))
        else:
            durings.append(dsl_nodes.DuringOperations(None, increment_operations))

    substates: List[dsl_nodes.StateDefinition] = []
    transitions: List[dsl_nodes.TransitionDefinition] = []
    if len(vertex.regions) > 1:  # pragma: no cover - rejected earlier by _validate_phase2_region
        raise NotImplementedError(
            f"Phase2 does not support multi-region composite state yet: {vertex.vertex_id}"
        )

    if vertex.regions:
        region = vertex.regions[0]
        init_pseudostates = {
            child.vertex_id for child in region.vertices if _is_init_pseudostate(machine, region, child)
        }
        for child in region.vertices:
            if child.vertex_type == "state":
                substates.append(_build_state(machine, child, context))
        regular_transitions: List[dsl_nodes.TransitionDefinition] = []
        lowered_timeout_transitions: List[dsl_nodes.TransitionDefinition] = []
        for transition in region.transitions:
            if transition.source_id in init_pseudostates:
                regular_transitions.append(_build_transition(machine, transition, context))
                continue
            source = machine.get_vertex(transition.source_id)
            target = machine.get_vertex(transition.target_id)
            if source.parent_region_id == region.region_id and target.parent_region_id == region.region_id:
                built_transition = _build_transition(machine, transition, context)
                if transition.trigger_kind == "time":
                    lowered_timeout_transitions.append(built_transition)
                else:
                    regular_transitions.append(built_transition)
        transitions.extend(regular_transitions)
        transitions.extend(lowered_timeout_transitions)
        if vertex.vertex_id in context.propagated_exit_chains:
            transitions.extend(
                [
                    dsl_nodes.TransitionDefinition(
                        from_state=machine.get_vertex(item.source_id).safe_name,
                        to_state=dsl_nodes.EXIT_STATE,
                        event_id=None,
                        condition_expr=item.guard_expr,
                        post_operations=[],
                    )
                    for item in context.propagated_exit_chains[vertex.vertex_id]
                ]
            )

    return dsl_nodes.StateDefinition(
        name=vertex.safe_name,
        extra_name=_display_name_or_none(vertex.display_name, vertex.safe_name),
        events=event_definitions or [],
        substates=substates,
        transitions=transitions,
        enters=enters,
        durings=durings,
        exits=exits,
        during_aspects=during_aspects,
    )


def build_machine_ast(
    machine: IrMachine,
    *,
    tick_duration_ms: Optional[float] = None,
) -> dsl_nodes.StateMachineDSLProgram:
    """
    Build a phase3 FCSTM AST program from a normalized IR machine.

    The input machine is expected to have already passed
    :func:`normalize_machine`. This function validates the supported subset,
    converts variables to ``def`` assignments, hoists root signals to FCSTM
    event definitions, lowers ``uml:TimeEvent`` triggers into internal timer
    variables and guards, and recursively lowers states and transitions.

    :param machine: Normalized machine IR object.
    :type machine: IrMachine
    :param tick_duration_ms: Duration of one runtime tick in milliseconds when
        lowering ``uml:TimeEvent`` transitions, defaults to ``None``
    :type tick_duration_ms: float, optional
    :return: FCSTM DSL program AST.
    :rtype: pyfcstm.dsl.node.StateMachineDSLProgram
    :raises ValueError: If the machine violates a structural invariant or time
        lowering requires missing/invalid configuration.
    :raises NotImplementedError: If the machine requires unsupported lowering.

    Example::

        >>> machine = normalize_machine(load_sysdesim_machine("sample.sysdesim.xml"))
        >>> program = build_machine_ast(machine)
        >>> program.root_state.name == machine.safe_name
        True
    """
    machine.rebuild_indexes()
    _validate_phase2_region(machine, machine.root_region)
    context = _build_ast_context(machine, tick_duration_ms)

    root_vertex = IrVertex(
        vertex_id=machine.machine_id,
        vertex_type="state",
        raw_name=machine.name,
        safe_name=machine.safe_name,
        display_name=machine.display_name,
        parent_region_id=None,
        regions=[machine.root_region],
        is_composite=True,
    )
    root_events = [
        dsl_nodes.EventDefinition(
            name=signal.safe_name,
            extra_name=_display_name_or_none(signal.display_name, signal.safe_name),
        )
        for signal in machine.signals
    ]
    definitions = []
    for variable in machine.variables:
        if variable.safe_name is None or variable.type_name is None or variable.default_value is None:
            continue
        if variable.type_name == "int":
            expr = dsl_nodes.Integer(str(variable.default_value))
        elif variable.type_name == "float":
            expr = dsl_nodes.Float(str(variable.default_value))
        else:
            raise ValueError(f"Unsupported variable type {variable.type_name!r}.")
        definitions.append(dsl_nodes.DefAssignment(name=variable.safe_name, type=variable.type_name, expr=expr))
    for lowered_time_transition in context.time_transitions_in_order:
        definitions.append(
            dsl_nodes.DefAssignment(
                name=lowered_time_transition.timer_name,
                type="int",
                expr=dsl_nodes.Integer("0"),
            )
        )

    return dsl_nodes.StateMachineDSLProgram(
        definitions=definitions,
        root_state=_build_state(machine, root_vertex, context, event_definitions=root_events),
    )


def emit_program(program: dsl_nodes.StateMachineDSLProgram) -> str:
    """
    Serialize a DSL program AST to FCSTM text.

    :param program: FCSTM DSL AST program.
    :type program: pyfcstm.dsl.node.StateMachineDSLProgram
    :return: Rendered FCSTM DSL source code.
    :rtype: str
    """
    return str(program)


def validate_program_roundtrip(program: dsl_nodes.StateMachineDSLProgram) -> Tuple[dsl_nodes.StateMachineDSLProgram, object]:
    """
    Round-trip the emitted DSL through the parser and model builder.

    This helper serializes the program, parses it back through the grammar
    entry ``state_machine_dsl``, and then builds the runtime model object used
    elsewhere in the codebase.

    :param program: FCSTM DSL AST program to validate.
    :type program: pyfcstm.dsl.node.StateMachineDSLProgram
    :return: Tuple of parsed DSL AST and built state-machine model.
    :rtype: tuple[pyfcstm.dsl.node.StateMachineDSLProgram, object]
    :raises pyfcstm.dsl.error.GrammarParseError: If the emitted DSL cannot be
        parsed.
    :raises pyfcstm.utils.validate.ModelValidationError: If the parsed program
        cannot be converted into a valid model.
    """
    dsl_code = str(program)
    parsed = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    model = parse_dsl_node_to_state_machine(parsed)
    return parsed, model


def convert_sysdesim_xml_to_ast(
    xml_path: str,
    *,
    machine_name: Optional[str] = None,
    machine_id: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
) -> dsl_nodes.StateMachineDSLProgram:
    """
    Load, normalize, validate, and convert one SysDeSim machine to FCSTM AST.

    :param xml_path: Path to the SysDeSim XML/XMI file.
    :type xml_path: str
    :param machine_name: Exact UML state-machine name to load, defaults to
        ``None``
    :type machine_name: str, optional
    :param machine_id: Exact UML state-machine ``xmi:id`` to load, defaults to
        ``None``
    :type machine_id: str, optional
    :param tick_duration_ms: Duration of one runtime tick in milliseconds when
        lowering ``uml:TimeEvent`` transitions, defaults to ``None``
    :type tick_duration_ms: float, optional
    :return: Converted FCSTM DSL AST program.
    :rtype: pyfcstm.dsl.node.StateMachineDSLProgram
    :raises KeyError: If the requested machine cannot be found.
    :raises ValueError: If the source file contains no state machine or violates
        a phase2 structural invariant.
    :raises NotImplementedError: If the source machine requires unsupported
        lowering features.
    :raises OSError: If the file cannot be read.
    :raises xml.etree.ElementTree.ParseError: If the XML is malformed.
    :raises pyfcstm.dsl.error.GrammarParseError: If emitted DSL fails parser
        validation.

    Example::

        >>> program = convert_sysdesim_xml_to_ast("sample.sysdesim.xml")
        >>> hasattr(program, "root_state")
        True
    """
    machine = load_sysdesim_machine(xml_path, machine_name=machine_name, machine_id=machine_id)
    normalize_machine(machine)
    program = build_machine_ast(machine, tick_duration_ms=tick_duration_ms)
    validate_program_roundtrip(program)
    return program


def convert_sysdesim_xml_to_dsl(
    xml_path: str,
    *,
    machine_name: Optional[str] = None,
    machine_id: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
) -> str:
    """
    Load, normalize, validate, and convert one SysDeSim machine to FCSTM DSL text.

    :param xml_path: Path to the SysDeSim XML/XMI file.
    :type xml_path: str
    :param machine_name: Exact UML state-machine name to load, defaults to
        ``None``
    :type machine_name: str, optional
    :param machine_id: Exact UML state-machine ``xmi:id`` to load, defaults to
        ``None``
    :type machine_id: str, optional
    :param tick_duration_ms: Duration of one runtime tick in milliseconds when
        lowering ``uml:TimeEvent`` transitions, defaults to ``None``
    :type tick_duration_ms: float, optional
    :return: Rendered FCSTM DSL text for the selected machine.
    :rtype: str
    :raises KeyError: If the requested machine cannot be found.
    :raises ValueError: If the source file contains no state machine or violates
        a phase2 structural invariant.
    :raises NotImplementedError: If the source machine requires unsupported
        lowering features.
    :raises OSError: If the file cannot be read.
    :raises xml.etree.ElementTree.ParseError: If the XML is malformed.
    :raises pyfcstm.dsl.error.GrammarParseError: If emitted DSL fails parser
        validation.

    Example::

        >>> dsl_code = convert_sysdesim_xml_to_dsl("sample.sysdesim.xml")
        >>> isinstance(dsl_code, str)
        True
    """
    return emit_program(
        convert_sysdesim_xml_to_ast(
            xml_path,
            machine_name=machine_name,
            machine_id=machine_id,
            tick_duration_ms=tick_duration_ms,
        )
    )

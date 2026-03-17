"""
SysDeSim XML to FCSTM phase0-2 conversion helpers.

This module contains the full phase0-2 pipeline:

1. Parse SysDeSim XML into the dataclass IR.
2. Normalize names, variables, and guard expressions.
3. Build FCSTM DSL AST for the supported subset.
4. Emit DSL text and validate it with the existing parser/model stack.

The implementation intentionally stops before time-event lowering, cross-level
lowering, and parallel-region splitting. Those cases are rejected explicitly so
the supported boundary stays clear.
"""

from __future__ import annotations

import re
import xml.etree.ElementTree as ET
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


def _xmi_id(element: ET.Element) -> str:
    """Return the XMI identifier of an XML element."""
    return element.attrib[_XMI_ID]


def _xmi_type(element: ET.Element) -> str:
    """Return the UML/XMI type tag of an XML element."""
    return element.attrib.get(_XMI_TYPE, "")


def _text_or_none(text: Optional[str]) -> Optional[str]:
    """Return stripped text or ``None`` for empty values."""
    if text is None:
        return None
    text = text.strip()
    return text or None


def _parse_action_ref(element: Optional[ET.Element]) -> Optional[IrActionRef]:
    """Build an action reference from an XML action node."""
    if element is None:
        return None
    return IrActionRef(
        action_id=_xmi_id(element),
        raw_name=element.attrib.get("name", ""),
    )


def _parse_constraint_body(container: ET.Element) -> Optional[str]:
    """Extract the first non-empty opaque-expression body from a UML container."""
    for rule in container.findall("ownedRule"):
        specification = rule.find("specification")
        if specification is None:
            continue
        body = _text_or_none(specification.findtext("body"))
        if body is not None:
            return body
    return None


def _parse_default_value(element: ET.Element) -> Optional[str]:
    """Parse a primitive default value from a UML property element."""
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
    """Map a UML primitive type reference to the FCSTM type name."""
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
    """Parse explicit UML properties owned by the machine's owning class."""
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
    """Parse one UML ``TimeEvent`` element."""
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
    """Recursively parse one UML region into IR."""
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
    """Parse all UML state machines from a SysDeSim XML/XMI file."""
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
    """Load one state machine from a SysDeSim XML/XMI file."""
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
    """Return a short stable suffix derived from a source identifier."""
    text = re.sub(r"[^A-Za-z0-9]+", "", raw_id)
    if not text:
        text = "sysdesim"
    return text[-length:]


def _tokenize_name(raw_name: str) -> List[str]:
    """Tokenize a raw label into ASCII name parts via transliteration."""
    text = unidecode(raw_name or "")
    return [token for token in re.split(r"[^A-Za-z0-9]+", text) if token]


def _base_upper_camel(raw_name: str) -> str:
    """Normalize a label to UpperCamelCase."""
    tokens = _tokenize_name(raw_name)
    return "".join(token[:1].upper() + token[1:] for token in tokens)


def _base_upper_snake(raw_name: str) -> str:
    """Normalize a label to UPPER_SNAKE_CASE."""
    tokens = _tokenize_name(raw_name)
    return "_".join(token.upper() for token in tokens)


def _base_lower_snake(raw_name: str) -> str:
    """Normalize a label to lower_snake_case."""
    tokens = _tokenize_name(raw_name)
    return "_".join(token.lower() for token in tokens)


def _with_unique_suffix(base: str, stable_id: str) -> str:
    """Append a deterministic suffix when a normalized name collides."""
    suffix = _stable_suffix(stable_id)
    return f"{base}_{suffix}" if base else suffix


def _make_state_name(vertex: IrVertex) -> str:
    """Build the FCSTM identifier for a state-like vertex."""
    base = _base_upper_camel(vertex.raw_name)
    if base:
        return base
    return f"__sysdesim_{vertex.vertex_type}_{_stable_suffix(vertex.vertex_id)}"


def _make_action_name(action: IrActionRef) -> str:
    """Build the FCSTM identifier for an action placeholder."""
    base = _base_upper_camel(action.raw_name)
    if base:
        return base
    return f"__sysdesim_action_{_stable_suffix(action.action_id)}"


def _make_event_name(raw_name: str, stable_id: str) -> str:
    """Build the FCSTM identifier for a signal-derived event."""
    base = _base_upper_snake(raw_name)
    if base:
        return base
    return f"__sysdesim_evt_{_stable_suffix(stable_id).upper()}"


def make_internal_name(prefix: str, scope_tokens: Iterable[str], stable_id: str) -> str:
    """Create a deterministic ``__sysdesim_*`` internal identifier."""
    scope_part = "_".join(token for token in scope_tokens if token)
    suffix = _stable_suffix(stable_id).lower()
    if scope_part:
        return f"__sysdesim_{prefix}_{scope_part}_{suffix}"
    return f"__sysdesim_{prefix}_{suffix}"


def _normalize_region_vertices(vertices: List[IrVertex]) -> None:
    """Normalize names for all vertices in a region subtree."""
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
    """Validate and normalize explicit and synthetic variables."""
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
    """Normalize signal and event names for FCSTM export."""
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
    """Parse supported time literal formats into normalized delay/unit fields."""
    for time_event in machine.time_events:
        if not time_event.raw_literal:
            continue
        match = _TIME_LITERAL.fullmatch(time_event.raw_literal)
        if match:
            time_event.normalized_delay = float(match.group(1))
            time_event.normalized_unit = match.group(2)


def normalize_machine(machine: IrMachine) -> IrMachine:
    """Normalize names, variables, events, and parsed guards for one IR machine."""
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


def _display_name_or_none(raw_name: Optional[str], safe_name: Optional[str]) -> Optional[str]:
    """Return the display name only when it differs from the FCSTM identifier."""
    if not raw_name or raw_name == safe_name:
        return None
    return raw_name


def _is_init_pseudostate(machine: IrMachine, region: IrRegion, vertex: IrVertex) -> bool:
    """Return whether a pseudostate matches the phase2 init-state heuristic."""
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
    """Reject structures that are outside the phase2 support boundary."""
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


def _build_transition(machine: IrMachine, transition: IrTransition) -> dsl_nodes.TransitionDefinition:
    """Convert a supported IR transition to a DSL transition node."""
    source = machine.get_vertex(transition.source_id)
    target = machine.get_vertex(transition.target_id)

    if transition.trigger_kind == "time":
        raise NotImplementedError(
            f"Phase2 does not support uml:TimeEvent transitions yet: {transition.transition_id}"
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
    *,
    event_definitions: Optional[List[dsl_nodes.EventDefinition]] = None,
) -> dsl_nodes.StateDefinition:
    """Recursively build a DSL state subtree from a normalized IR vertex."""
    enters = []
    exits = []
    if vertex.entry_action is not None:
        enters.append(dsl_nodes.EnterAbstractFunction(vertex.entry_action.safe_name, None))
    if vertex.exit_action is not None:
        exits.append(dsl_nodes.ExitAbstractFunction(vertex.exit_action.safe_name, None))

    substates: List[dsl_nodes.StateDefinition] = []
    transitions: List[dsl_nodes.TransitionDefinition] = []
    if len(vertex.regions) > 1:
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
                substates.append(_build_state(machine, child))
        for transition in region.transitions:
            if transition.source_id in init_pseudostates:
                transitions.append(_build_transition(machine, transition))
                continue
            source = machine.get_vertex(transition.source_id)
            target = machine.get_vertex(transition.target_id)
            if source.parent_region_id == region.region_id and target.parent_region_id == region.region_id:
                transitions.append(_build_transition(machine, transition))

    return dsl_nodes.StateDefinition(
        name=vertex.safe_name,
        extra_name=_display_name_or_none(vertex.display_name, vertex.safe_name),
        events=event_definitions or [],
        substates=substates,
        transitions=transitions,
        enters=enters,
        exits=exits,
    )


def build_machine_ast(machine: IrMachine) -> dsl_nodes.StateMachineDSLProgram:
    """Build a phase2 FCSTM AST program from a normalized IR machine."""
    machine.rebuild_indexes()
    _validate_phase2_region(machine, machine.root_region)

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

    return dsl_nodes.StateMachineDSLProgram(
        definitions=definitions,
        root_state=_build_state(machine, root_vertex, event_definitions=root_events),
    )


def emit_program(program: dsl_nodes.StateMachineDSLProgram) -> str:
    """Serialize a DSL program AST to FCSTM text."""
    return str(program)


def validate_program_roundtrip(program: dsl_nodes.StateMachineDSLProgram) -> Tuple[dsl_nodes.StateMachineDSLProgram, object]:
    """Round-trip the emitted DSL through the parser and model builder."""
    dsl_code = str(program)
    parsed = parse_with_grammar_entry(dsl_code, entry_name="state_machine_dsl")
    model = parse_dsl_node_to_state_machine(parsed)
    return parsed, model


def convert_sysdesim_xml_to_ast(
    xml_path: str,
    *,
    machine_name: Optional[str] = None,
    machine_id: Optional[str] = None,
) -> dsl_nodes.StateMachineDSLProgram:
    """Load, normalize, validate, and convert one SysDeSim machine to FCSTM AST."""
    machine = load_sysdesim_machine(xml_path, machine_name=machine_name, machine_id=machine_id)
    normalize_machine(machine)
    program = build_machine_ast(machine)
    validate_program_roundtrip(program)
    return program


def convert_sysdesim_xml_to_dsl(
    xml_path: str,
    *,
    machine_name: Optional[str] = None,
    machine_id: Optional[str] = None,
) -> str:
    """Load, normalize, validate, and convert one SysDeSim machine to FCSTM DSL text."""
    return emit_program(
        convert_sysdesim_xml_to_ast(
            xml_path,
            machine_name=machine_name,
            machine_id=machine_id,
        )
    )

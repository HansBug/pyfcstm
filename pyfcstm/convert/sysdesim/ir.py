"""
Intermediate representation for the SysDeSim-to-FCSTM conversion pipeline.

This module defines the minimal dataclass-based IR used by phase0-2 of the
converter. The IR is intentionally close to the SysDeSim XML structure so the
loader can populate it directly, while still exposing normalized names,
transition metadata, and indexed graph queries needed by later lowering stages.
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple


@dataclass
class IrDiagnostic:
    """Diagnostic message collected during loading or normalization."""

    level: str
    code: str
    message: str
    source_id: Optional[str] = None
    state_path: Optional[Tuple[str, ...]] = None


@dataclass
class IrActionRef:
    """Reference to an entry, exit, or effect action object in the source XML."""

    action_id: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class IrVariable:
    """Variable definition retained in the conversion IR."""

    variable_id: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None
    type_name: Optional[str] = None
    default_value: Optional[str] = None
    is_synthetic: bool = False


@dataclass
class IrSignal:
    """Signal definition parsed from a UML ``Signal`` element."""

    signal_id: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class IrSignalEvent:
    """Event wrapper that points to a signal definition."""

    event_id: str
    signal_id: str
    raw_name: str = ""
    safe_name: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class IrTimeEvent:
    """Time-trigger definition parsed from a UML ``TimeEvent`` element."""

    time_event_id: str
    raw_literal: str
    is_relative: bool
    normalized_delay: Optional[float] = None
    normalized_unit: Optional[str] = None


@dataclass
class IrTransition:
    """Transition edge in the SysDeSim IR graph."""

    transition_id: str
    source_id: str
    target_id: str
    trigger_kind: str
    trigger_ref_id: Optional[str]
    guard_expr_raw: Optional[str]
    guard_expr_ir: Optional[Any] = None
    effect_action: Optional[IrActionRef] = None
    source_region_id: Optional[str] = None
    target_region_id: Optional[str] = None
    is_cross_level: bool = False
    is_cross_region: bool = False
    origin_kind: str = "original"


@dataclass
class IrRegion:
    """Region node containing vertices and transitions."""

    region_id: str
    owner_state_id: Optional[str]
    vertices: List["IrVertex"] = field(default_factory=list)
    transitions: List[IrTransition] = field(default_factory=list)


@dataclass
class IrVertex:
    """Vertex node representing a state, pseudostate, or final state."""

    vertex_id: str
    vertex_type: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None
    parent_region_id: Optional[str] = None
    entry_action: Optional[IrActionRef] = None
    exit_action: Optional[IrActionRef] = None
    state_invariant: Optional[str] = None
    regions: List[IrRegion] = field(default_factory=list)
    is_composite: bool = False
    is_parallel_owner: bool = False


@dataclass
class IrMachine:
    """Root IR object for one SysDeSim state machine."""

    machine_id: str
    name: str
    root_region: IrRegion
    signals: List[IrSignal] = field(default_factory=list)
    signal_events: List[IrSignalEvent] = field(default_factory=list)
    time_events: List[IrTimeEvent] = field(default_factory=list)
    variables: List[IrVariable] = field(default_factory=list)
    diagnostics: List[IrDiagnostic] = field(default_factory=list)
    safe_name: Optional[str] = None
    display_name: Optional[str] = None
    _vertex_index: Dict[str, IrVertex] = field(default_factory=dict, init=False, repr=False)
    _transition_index: Dict[str, IrTransition] = field(default_factory=dict, init=False, repr=False)
    _region_index: Dict[str, IrRegion] = field(default_factory=dict, init=False, repr=False)
    _signal_index: Dict[str, IrSignal] = field(default_factory=dict, init=False, repr=False)
    _signal_event_index: Dict[str, IrSignalEvent] = field(default_factory=dict, init=False, repr=False)
    _time_event_index: Dict[str, IrTimeEvent] = field(default_factory=dict, init=False, repr=False)
    _variable_index: Dict[str, IrVariable] = field(default_factory=dict, init=False, repr=False)

    def __post_init__(self) -> None:
        """Build indexes immediately after construction."""
        self.rebuild_indexes()

    def walk_regions(self) -> Iterator[IrRegion]:
        """Yield all regions in depth-first order."""
        stack = [self.root_region]
        while stack:
            region = stack.pop()
            yield region
            for vertex in reversed(region.vertices):
                stack.extend(reversed(vertex.regions))

    def walk_vertices(self) -> Iterator[IrVertex]:
        """Yield all vertices in depth-first order."""
        for region in self.walk_regions():
            yield from region.vertices

    def walk_transitions(self) -> Iterator[IrTransition]:
        """Yield all transitions across all regions."""
        for region in self.walk_regions():
            yield from region.transitions

    def rebuild_indexes(self) -> None:
        """Rebuild lookup indexes and derived transition metadata."""
        self._vertex_index = {}
        self._transition_index = {}
        self._region_index = {}
        self._signal_index = {item.signal_id: item for item in self.signals}
        self._signal_event_index = {item.event_id: item for item in self.signal_events}
        self._time_event_index = {item.time_event_id: item for item in self.time_events}
        self._variable_index = {item.variable_id: item for item in self.variables}

        for region in self.walk_regions():
            self._region_index[region.region_id] = region
            for vertex in region.vertices:
                self._vertex_index[vertex.vertex_id] = vertex
            for transition in region.transitions:
                self._transition_index[transition.transition_id] = transition

        for transition in self.walk_transitions():
            source = self._vertex_index[transition.source_id]
            target = self._vertex_index[transition.target_id]
            transition.source_region_id = source.parent_region_id
            transition.target_region_id = target.parent_region_id
            transition.is_cross_region = transition.source_region_id != transition.target_region_id
            transition.is_cross_level = transition.is_cross_region

    def get_vertex(self, vertex_id: str) -> IrVertex:
        """Return a vertex by its stable source identifier."""
        return self._vertex_index[vertex_id]

    def get_transition(self, transition_id: str) -> IrTransition:
        """Return a transition by its stable source identifier."""
        return self._transition_index[transition_id]

    def get_region(self, region_id: str) -> IrRegion:
        """Return a region by its stable source identifier."""
        return self._region_index[region_id]

    def get_signal(self, signal_id: str) -> IrSignal:
        """Return a signal by its stable source identifier."""
        return self._signal_index[signal_id]

    def get_signal_event(self, event_id: str) -> IrSignalEvent:
        """Return a signal event by its stable source identifier."""
        return self._signal_event_index[event_id]

    def get_time_event(self, event_id: str) -> IrTimeEvent:
        """Return a time event by its stable source identifier."""
        return self._time_event_index[event_id]

    def get_variable(self, variable_id: str) -> IrVariable:
        """Return a variable by its stable source identifier."""
        return self._variable_index[variable_id]

    def state_id_path(self, vertex_id: str) -> Tuple[str, ...]:
        """Return the owning state-id path for a vertex."""
        current = self.get_vertex(vertex_id)
        path: List[str] = []
        while True:
            if current.vertex_type == "state":
                path.append(current.vertex_id)
            if current.parent_region_id is None:
                break
            region = self.get_region(current.parent_region_id)
            if region.owner_state_id is None:
                break
            current = self.get_vertex(region.owner_state_id)
        return tuple(reversed(path))

    def state_path(self, vertex_id: str, use_safe_name: bool = False) -> Tuple[str, ...]:
        """Return the owning state-name path for a vertex."""
        names = []
        for state_id in self.state_id_path(vertex_id):
            vertex = self.get_vertex(state_id)
            names.append(vertex.safe_name if use_safe_name and vertex.safe_name else vertex.raw_name)
        return tuple(names)

    def descendant_state_ids(self, state_id: str) -> Tuple[str, ...]:
        """Return all descendant state identifiers for a state."""
        descendants: List[str] = []
        stack = [self.get_vertex(state_id)]
        while stack:
            current = stack.pop()
            for region in current.regions:
                for vertex in region.vertices:
                    if vertex.vertex_type == "state":
                        descendants.append(vertex.vertex_id)
                        stack.append(vertex)
        return tuple(descendants)

    def region_count(self, state_id: str) -> int:
        """Return the number of regions directly owned by a state."""
        return len(self.get_vertex(state_id).regions)

    def lca_state_id(self, left_vertex_id: str, right_vertex_id: str) -> Optional[str]:
        """Return the lowest common ancestor state identifier for two vertices."""
        left_path = self.state_id_path(left_vertex_id)
        right_path = self.state_id_path(right_vertex_id)
        lca = None
        for left_item, right_item in zip(left_path, right_path):
            if left_item != right_item:
                break
            lca = left_item
        return lca

    def to_dict(self) -> Dict[str, Any]:
        """Serialize the IR object tree to a plain dictionary."""
        return asdict(self)

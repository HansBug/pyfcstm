"""
Intermediate representation for the SysDeSim-to-FCSTM conversion pipeline.

This module defines the minimal dataclass-based IR used by phase0-2 of the
converter. The IR is intentionally close to the SysDeSim XML structure so the
loader can populate it directly, while still exposing normalized names,
transition metadata, and indexed graph queries needed by later lowering stages.

The module contains:

* :class:`IrDiagnostic` - Structured diagnostics collected during conversion.
* :class:`IrActionRef` - References to source action objects.
* :class:`IrVariable` - Variable definitions preserved in IR form.
* :class:`IrSignal`, :class:`IrSignalEvent`, :class:`IrTimeEvent` - Event data.
* :class:`IrTransition`, :class:`IrRegion`, :class:`IrVertex` - Graph nodes.
* :class:`IrMachine` - Root object with traversal and lookup helpers.

Example::

    >>> from pyfcstm.convert.sysdesim.ir import IrMachine, IrRegion
    >>> machine = IrMachine(machine_id="m1", name="Demo", root_region=IrRegion("r1", None))
    >>> tuple(machine.walk_regions())
    (IrRegion(region_id='r1', owner_state_id=None, vertices=[], transitions=[]),)
"""

from __future__ import annotations

from dataclasses import asdict, dataclass, field
from typing import Any, Dict, Iterator, List, Optional, Tuple


@dataclass
class IrDiagnostic:
    """
    Diagnostic message collected during loading or normalization.

    :param level: Severity label such as ``'warning'`` or ``'error'``.
    :type level: str
    :param code: Stable machine-readable diagnostic code.
    :type code: str
    :param message: Human-readable diagnostic text.
    :type message: str
    :param source_id: Identifier of the related source object, defaults to ``None``
    :type source_id: str, optional
    :param state_path: Optional owning state path for context, defaults to ``None``
    :type state_path: tuple[str, ...], optional
    :param details: Optional structured payload carrying machine-readable
        evidence for the diagnostic (constraint ids, step ids, suggested fix
        hints, etc). Defaults to ``None`` for backward compatibility.
    :type details: dict[str, Any], optional
    :param hints: Optional list of human-readable repair hints, defaults to
        ``None``.
    :type hints: list[str], optional
    """

    level: str
    code: str
    message: str
    source_id: Optional[str] = None
    state_path: Optional[Tuple[str, ...]] = None
    details: Optional[Dict[str, Any]] = None
    hints: Optional[List[str]] = None


@dataclass
class IrActionRef:
    """
    Reference to an entry, exit, or effect action object in the source XML.

    :param action_id: Stable source identifier of the action element.
    :type action_id: str
    :param raw_name: Original action name read from XML.
    :type raw_name: str
    :param safe_name: FCSTM-safe identifier assigned during normalization,
        defaults to ``None``
    :type safe_name: str, optional
    :param display_name: Display name preserved for emitted ``named`` clauses,
        defaults to ``None``
    :type display_name: str, optional
    """

    action_id: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class IrVariable:
    """
    Variable definition retained in the conversion IR.

    :param variable_id: Stable source identifier of the UML property.
    :type variable_id: str
    :param raw_name: Original variable name from the source model.
    :type raw_name: str
    :param safe_name: FCSTM-safe identifier assigned during normalization,
        defaults to ``None``
    :type safe_name: str, optional
    :param display_name: Human-readable name preserved for diagnostics or
        display, defaults to ``None``
    :type display_name: str, optional
    :param type_name: Normalized FCSTM type name, defaults to ``None``
    :type type_name: str, optional
    :param default_value: Default literal value as text, defaults to ``None``
    :type default_value: str, optional
    :param is_synthetic: Whether the variable was synthesized by the converter,
        defaults to ``False``
    :type is_synthetic: bool
    """

    variable_id: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None
    type_name: Optional[str] = None
    default_value: Optional[str] = None
    is_synthetic: bool = False


@dataclass
class IrSignal:
    """
    Signal definition parsed from a UML ``Signal`` element.

    :param signal_id: Stable source identifier of the signal.
    :type signal_id: str
    :param raw_name: Original signal name from XML.
    :type raw_name: str
    :param safe_name: FCSTM-safe event identifier, defaults to ``None``
    :type safe_name: str, optional
    :param display_name: Human-readable label preserved for FCSTM ``named``
        clauses, defaults to ``None``
    :type display_name: str, optional
    """

    signal_id: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class IrSignalEvent:
    """
    Event wrapper that points to a signal definition.

    :param event_id: Stable source identifier of the signal event.
    :type event_id: str
    :param signal_id: Referenced signal identifier.
    :type signal_id: str
    :param raw_name: Original event name from XML, defaults to ``''``
    :type raw_name: str
    :param safe_name: FCSTM-safe event identifier, defaults to ``None``
    :type safe_name: str, optional
    :param display_name: Display name preserved during normalization,
        defaults to ``None``
    :type display_name: str, optional
    """

    event_id: str
    signal_id: str
    raw_name: str = ""
    safe_name: Optional[str] = None
    display_name: Optional[str] = None


@dataclass
class IrTimeEvent:
    """
    Time-trigger definition parsed from a UML ``TimeEvent`` element.

    :param time_event_id: Stable source identifier of the time event.
    :type time_event_id: str
    :param raw_literal: Raw time literal from the UML time expression.
    :type raw_literal: str
    :param is_relative: Whether the event is relative rather than absolute.
    :type is_relative: bool
    :param normalized_delay: Parsed numeric delay value, defaults to ``None``
    :type normalized_delay: float, optional
    :param normalized_unit: Parsed unit such as ``'s'`` or ``'ms'``,
        defaults to ``None``
    :type normalized_unit: str, optional
    """

    time_event_id: str
    raw_literal: str
    is_relative: bool
    normalized_delay: Optional[float] = None
    normalized_unit: Optional[str] = None


@dataclass
class IrTransition:
    """
    Transition edge in the SysDeSim IR graph.

    :param transition_id: Stable source identifier of the transition.
    :type transition_id: str
    :param source_id: Source vertex identifier.
    :type source_id: str
    :param target_id: Target vertex identifier.
    :type target_id: str
    :param trigger_kind: Trigger category such as ``'signal'``, ``'time'``, or
        ``'none'``
    :type trigger_kind: str
    :param trigger_ref_id: Referenced trigger event identifier, defaults to
        ``None``
    :type trigger_ref_id: str, optional
    :param guard_expr_raw: Raw guard expression text, defaults to ``None``
    :type guard_expr_raw: str, optional
    :param guard_expr_ir: Parsed guard expression node, defaults to ``None``
    :type guard_expr_ir: Any, optional
    :param effect_action: Optional transition effect reference, defaults to
        ``None``
    :type effect_action: IrActionRef, optional
    :param source_region_id: Source region identifier, defaults to ``None``
    :type source_region_id: str, optional
    :param target_region_id: Target region identifier, defaults to ``None``
    :type target_region_id: str, optional
    :param is_cross_level: Whether the transition crosses state nesting levels,
        defaults to ``False``
    :type is_cross_level: bool
    :param is_cross_region: Whether the transition crosses region boundaries,
        defaults to ``False``
    :type is_cross_region: bool
    :param origin_kind: Marker describing where the transition came from,
        defaults to ``'original'``
    :type origin_kind: str
    """

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
    """
    Region node containing vertices and transitions.

    :param region_id: Stable source identifier of the region.
    :type region_id: str
    :param owner_state_id: Owning composite-state identifier, or ``None`` for
        the root region
    :type owner_state_id: str, optional
    :param vertices: Vertices directly contained in the region, defaults to an
        empty list
    :type vertices: list[IrVertex]
    :param transitions: Transitions directly contained in the region, defaults
        to an empty list
    :type transitions: list[IrTransition]
    """

    region_id: str
    owner_state_id: Optional[str]
    vertices: List["IrVertex"] = field(default_factory=list)
    transitions: List[IrTransition] = field(default_factory=list)


@dataclass
class IrVertex:
    """
    Vertex node representing a state, pseudostate, or final state.

    :param vertex_id: Stable source identifier of the vertex.
    :type vertex_id: str
    :param vertex_type: Vertex category such as ``'state'`` or
        ``'pseudostate'``
    :type vertex_type: str
    :param raw_name: Original source name.
    :type raw_name: str
    :param safe_name: FCSTM-safe identifier assigned during normalization,
        defaults to ``None``
    :type safe_name: str, optional
    :param display_name: Human-readable name preserved for emitted ``named``
        clauses, defaults to ``None``
    :type display_name: str, optional
    :param parent_region_id: Owning region identifier, defaults to ``None``
    :type parent_region_id: str, optional
    :param entry_action: Optional entry action reference, defaults to ``None``
    :type entry_action: IrActionRef, optional
    :param exit_action: Optional exit action reference, defaults to ``None``
    :type exit_action: IrActionRef, optional
    :param do_action: Optional do-activity action reference, defaults to ``None``
    :type do_action: IrActionRef, optional
    :param state_invariant: Raw state invariant text, defaults to ``None``
    :type state_invariant: str, optional
    :param regions: Child regions owned by the vertex, defaults to an empty list
    :type regions: list[IrRegion]
    :param is_composite: Whether the vertex owns child regions, defaults to
        ``False``
    :type is_composite: bool
    :param is_parallel_owner: Whether the vertex owns multiple regions,
        defaults to ``False``
    :type is_parallel_owner: bool
    """

    vertex_id: str
    vertex_type: str
    raw_name: str
    safe_name: Optional[str] = None
    display_name: Optional[str] = None
    parent_region_id: Optional[str] = None
    entry_action: Optional[IrActionRef] = None
    exit_action: Optional[IrActionRef] = None
    do_action: Optional[IrActionRef] = None
    state_invariant: Optional[str] = None
    regions: List[IrRegion] = field(default_factory=list)
    is_composite: bool = False
    is_parallel_owner: bool = False


@dataclass
class IrMachine:
    """
    Root IR object for one SysDeSim state machine.

    The object owns the full graph and maintains lookup indexes for vertices,
    regions, transitions, events, and variables. Call :meth:`rebuild_indexes`
    after making structural changes to keep derived metadata consistent.

    :param machine_id: Stable source identifier of the state machine.
    :type machine_id: str
    :param name: Original machine name from XML.
    :type name: str
    :param root_region: Root region of the machine.
    :type root_region: IrRegion
    :param signals: Signal definitions used by the machine, defaults to an
        empty list
    :type signals: list[IrSignal]
    :param signal_events: Signal-event wrappers, defaults to an empty list
    :type signal_events: list[IrSignalEvent]
    :param time_events: Time-event definitions, defaults to an empty list
    :type time_events: list[IrTimeEvent]
    :param variables: Variable definitions, defaults to an empty list
    :type variables: list[IrVariable]
    :param diagnostics: Collected diagnostics, defaults to an empty list
    :type diagnostics: list[IrDiagnostic]
    :param safe_name: FCSTM-safe machine identifier, defaults to ``None``
    :type safe_name: str, optional
    :param display_name: Display name used for FCSTM ``named`` clauses,
        defaults to ``None``
    :type display_name: str, optional

    :ivar root_region: Root region of the IR tree.
    :vartype root_region: IrRegion
    :ivar diagnostics: Diagnostics collected during loading and normalization.
    :vartype diagnostics: list[IrDiagnostic]

    Example::

        >>> machine = IrMachine(machine_id="m1", name="Demo", root_region=IrRegion("r1", None))
        >>> machine.safe_name is None
        True
        >>> tuple(machine.walk_vertices())
        ()
    """

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
    _vertex_index: Dict[str, IrVertex] = field(
        default_factory=dict, init=False, repr=False
    )
    _transition_index: Dict[str, IrTransition] = field(
        default_factory=dict, init=False, repr=False
    )
    _region_index: Dict[str, IrRegion] = field(
        default_factory=dict, init=False, repr=False
    )
    _signal_index: Dict[str, IrSignal] = field(
        default_factory=dict, init=False, repr=False
    )
    _signal_event_index: Dict[str, IrSignalEvent] = field(
        default_factory=dict, init=False, repr=False
    )
    _time_event_index: Dict[str, IrTimeEvent] = field(
        default_factory=dict, init=False, repr=False
    )
    _variable_index: Dict[str, IrVariable] = field(
        default_factory=dict, init=False, repr=False
    )

    def __post_init__(self) -> None:
        """
        Build indexes immediately after construction.

        :return: ``None``.
        :rtype: None
        """
        self.rebuild_indexes()

    def walk_regions(self) -> Iterator[IrRegion]:
        """
        Yield all regions in depth-first order.

        :return: Iterator over the root region and every nested child region.
        :rtype: collections.abc.Iterator[IrRegion]
        """
        stack = [self.root_region]
        while stack:
            region = stack.pop()
            yield region
            for vertex in reversed(region.vertices):
                stack.extend(reversed(vertex.regions))

    def walk_vertices(self) -> Iterator[IrVertex]:
        """
        Yield all vertices in depth-first order.

        :return: Iterator over every vertex reachable from the root region.
        :rtype: collections.abc.Iterator[IrVertex]
        """
        for region in self.walk_regions():
            yield from region.vertices

    def walk_transitions(self) -> Iterator[IrTransition]:
        """
        Yield all transitions across all regions.

        :return: Iterator over every transition in the machine.
        :rtype: collections.abc.Iterator[IrTransition]
        """
        for region in self.walk_regions():
            yield from region.transitions

    def rebuild_indexes(self) -> None:
        """
        Rebuild lookup indexes and derived transition metadata.

        This method updates the internal dictionaries used by the ``get_*``
        helpers and refreshes derived transition flags such as
        :attr:`IrTransition.is_cross_region`.

        :return: ``None``.
        :rtype: None
        """
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
            transition.is_cross_region = (
                transition.source_region_id != transition.target_region_id
            )
            transition.is_cross_level = transition.is_cross_region

    def get_vertex(self, vertex_id: str) -> IrVertex:
        """
        Return a vertex by its stable source identifier.

        :param vertex_id: Vertex identifier from the source model.
        :type vertex_id: str
        :return: Matching vertex object.
        :rtype: IrVertex
        :raises KeyError: If ``vertex_id`` is not indexed.
        """
        return self._vertex_index[vertex_id]

    def get_transition(self, transition_id: str) -> IrTransition:
        """
        Return a transition by its stable source identifier.

        :param transition_id: Transition identifier from the source model.
        :type transition_id: str
        :return: Matching transition object.
        :rtype: IrTransition
        :raises KeyError: If ``transition_id`` is not indexed.
        """
        return self._transition_index[transition_id]

    def get_region(self, region_id: str) -> IrRegion:
        """
        Return a region by its stable source identifier.

        :param region_id: Region identifier from the source model.
        :type region_id: str
        :return: Matching region object.
        :rtype: IrRegion
        :raises KeyError: If ``region_id`` is not indexed.
        """
        return self._region_index[region_id]

    def get_signal(self, signal_id: str) -> IrSignal:
        """
        Return a signal by its stable source identifier.

        :param signal_id: Signal identifier from the source model.
        :type signal_id: str
        :return: Matching signal object.
        :rtype: IrSignal
        :raises KeyError: If ``signal_id`` is not indexed.
        """
        return self._signal_index[signal_id]

    def get_signal_event(self, event_id: str) -> IrSignalEvent:
        """
        Return a signal event by its stable source identifier.

        :param event_id: Signal-event identifier from the source model.
        :type event_id: str
        :return: Matching signal-event object.
        :rtype: IrSignalEvent
        :raises KeyError: If ``event_id`` is not indexed.
        """
        return self._signal_event_index[event_id]

    def get_time_event(self, event_id: str) -> IrTimeEvent:
        """
        Return a time event by its stable source identifier.

        :param event_id: Time-event identifier from the source model.
        :type event_id: str
        :return: Matching time-event object.
        :rtype: IrTimeEvent
        :raises KeyError: If ``event_id`` is not indexed.
        """
        return self._time_event_index[event_id]

    def get_variable(self, variable_id: str) -> IrVariable:
        """
        Return a variable by its stable source identifier.

        :param variable_id: Variable identifier from the source model.
        :type variable_id: str
        :return: Matching variable object.
        :rtype: IrVariable
        :raises KeyError: If ``variable_id`` is not indexed.
        """
        return self._variable_index[variable_id]

    def state_id_path(self, vertex_id: str) -> Tuple[str, ...]:
        """
        Return the owning state-id path for a vertex.

        The path includes only vertices whose type is ``'state'`` and is ordered
        from the outermost owning state to the innermost owning state.

        :param vertex_id: Identifier of the vertex whose ancestry should be
            resolved.
        :type vertex_id: str
        :return: Tuple of owning state identifiers.
        :rtype: tuple[str, ...]
        :raises KeyError: If ``vertex_id`` does not exist.
        """
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

    def state_path(
        self, vertex_id: str, use_safe_name: bool = False
    ) -> Tuple[str, ...]:
        """
        Return the owning state-name path for a vertex.

        :param vertex_id: Identifier of the vertex whose ancestry should be
            resolved.
        :type vertex_id: str
        :param use_safe_name: Whether to prefer normalized FCSTM-safe names over
            raw source names, defaults to ``False``
        :type use_safe_name: bool
        :return: Tuple of owning state names.
        :rtype: tuple[str, ...]
        :raises KeyError: If ``vertex_id`` does not exist.
        """
        names = []
        for state_id in self.state_id_path(vertex_id):
            vertex = self.get_vertex(state_id)
            names.append(
                vertex.safe_name
                if use_safe_name and vertex.safe_name
                else vertex.raw_name
            )
        return tuple(names)

    def descendant_state_ids(self, state_id: str) -> Tuple[str, ...]:
        """
        Return all descendant state identifiers for a state.

        :param state_id: Identifier of the owning state.
        :type state_id: str
        :return: Tuple of descendant state identifiers in depth-first order.
        :rtype: tuple[str, ...]
        :raises KeyError: If ``state_id`` does not exist.
        """
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
        """
        Return the number of regions directly owned by a state.

        :param state_id: Identifier of the state vertex.
        :type state_id: str
        :return: Number of direct child regions.
        :rtype: int
        :raises KeyError: If ``state_id`` does not exist.
        """
        return len(self.get_vertex(state_id).regions)

    def lca_state_id(self, left_vertex_id: str, right_vertex_id: str) -> Optional[str]:
        """
        Return the lowest common ancestor state identifier for two vertices.

        :param left_vertex_id: Identifier of the first vertex.
        :type left_vertex_id: str
        :param right_vertex_id: Identifier of the second vertex.
        :type right_vertex_id: str
        :return: Shared lowest common ancestor state identifier, or ``None`` if
            the vertices do not share an owning state.
        :rtype: str, optional
        :raises KeyError: If either vertex identifier does not exist.
        """
        left_path = self.state_id_path(left_vertex_id)
        right_path = self.state_id_path(right_vertex_id)
        lca = None
        for left_item, right_item in zip(left_path, right_path):
            if left_item != right_item:
                break
            lca = left_item
        return lca

    def to_dict(self) -> Dict[str, Any]:
        """
        Serialize the IR object tree to a plain dictionary.

        :return: Recursive dictionary produced by :func:`dataclasses.asdict`.
        :rtype: dict[str, Any]
        """
        return asdict(self)

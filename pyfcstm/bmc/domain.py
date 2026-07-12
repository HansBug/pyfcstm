"""Domain numbering model for FCSTM bounded model checking.

The domain layer assigns stable integer identifiers to the model objects that a
bounded trace formula needs before macro-step expansion or solver lowering.  It
is intentionally model-aware but query-independent: every state, event, and
persistent variable in the :class:`pyfcstm.model.StateMachine` receives a stable
identifier, and later BMC layers decide which identifiers are relevant to a
particular query.

Design contracts:

* Normal model states use non-negative ids, while the terminal and cold-init
  sentinel states use fixed negative ids.
* Frame references cover ``F_0..F_N`` and step references cover
  ``E_0..E_{N-1}`` for a positive bound ``N``.
* ``F_0`` may be constrained by cold, hot, or terminated initial conditions,
  so its allowed-state set is broader than recurrence frames.
* Step/event input slots are independent; the domain layer never adds implicit
  at-most-one event constraints.
* :meth:`to_canonical` returns only JSON-stable plain Python objects so domain
  dumps can be used directly as golden fixtures and preparation summaries.

The module contains:

* :data:`STATE_INIT_ID` and :data:`STATE_TERMINATE_ID` - Fixed sentinel
  state identifiers.
* :class:`StateDomainEntry` - Stable state id metadata.
* :class:`EventDomainEntry` - Stable event id metadata.
* :class:`VarDomainEntry` - Stable persistent variable id metadata.
* :class:`FrameRef`, :class:`StepRef`, and :class:`EventInputRef` - Bounded
  trace reference objects.
* :class:`BmcDomain` - Complete domain snapshot with lookup helpers.
* :func:`build_bmc_domain` - Construct a domain snapshot from a state machine.

Example::

    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root;')
    >>> domain = build_bmc_domain(model, bound=1)
    >>> domain.state_path_to_id('Root') >= 0
    True
    >>> domain.state_by_id(STATE_TERMINATE_ID).name
    'STATE_TERMINATE'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Optional, Sequence, Tuple

from .errors import InvalidBmcDomain
from pyfcstm.model import Event, State, StateMachine

STATE_INIT_ID = -3
# The retired -2 slot is intentionally never reused, so old diagnostic traces
# cannot be confused with the cold-init sentinel.
STATE_TERMINATE_ID = -1
_STATE_INIT_PATH = "$STATE_INIT"
_STATE_TERMINATE_PATH = "$STATE_TERMINATE"

_CanonicalDict = Dict[str, Any]
_STATE_ENTRY_FIELDS = (
    "id",
    "path",
    "name",
    "kind",
    "parent_path",
    "is_root",
    "is_stoppable",
    "is_sentinel",
    "is_generated_combo_pseudo",
)
_STATE_ENTRY_BOOL_FIELDS = (
    "is_root",
    "is_stoppable",
    "is_sentinel",
    "is_generated_combo_pseudo",
)
_STATE_SENTINEL_IDS = {STATE_INIT_ID, STATE_TERMINATE_ID}
_EVENT_ENTRY_FIELDS = (
    "id",
    "path",
    "name",
    "owner_state_path",
    "owner_state_id",
    "owner_is_generated_combo_pseudo",
)


def _validate_positive_bound(bound: object, field_name: str = "bound") -> int:
    if isinstance(bound, bool) or not isinstance(bound, int):
        raise InvalidBmcDomain(f"{field_name} must be a positive integer.")
    if bound <= 0:
        raise InvalidBmcDomain(f"{field_name} must be a positive integer.")
    return bound


def _validate_index(index: object, field_name: str) -> int:
    if isinstance(index, bool) or not isinstance(index, int):
        raise InvalidBmcDomain(f"{field_name} must be an integer.")
    return index


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidBmcDomain(f"{field_name} must be a non-empty string.")
    return value


def _require_bool(value: object, field_name: str) -> bool:
    if not isinstance(value, bool):
        raise InvalidBmcDomain(f"{field_name} must be a boolean.")
    return value


def _state_entry_value(entry: object, field_name: str) -> object:
    if not hasattr(entry, field_name):
        raise InvalidBmcDomain("State entry is missing %s." % field_name)
    return getattr(entry, field_name)


def _validate_state_entry(entry: object) -> None:
    values = {field: _state_entry_value(entry, field) for field in _STATE_ENTRY_FIELDS}
    state_id = _validate_index(values["id"], "state id")
    state_path = _require_non_empty_string(values["path"], "state path")
    state_name = _require_non_empty_string(values["name"], "state name")
    kind_value = values["kind"]
    if not isinstance(kind_value, str) or kind_value not in {
        "leaf",
        "composite",
        "pseudo",
        "sentinel",
    }:
        raise InvalidBmcDomain(f"Unsupported state kind: {kind_value!r}.")
    kind = kind_value
    if values["parent_path"] is None:
        parent_path = None
    else:
        parent_path = _require_non_empty_string(values["parent_path"], "parent_path")
    is_root = _require_bool(values["is_root"], "is_root")
    is_stoppable = _require_bool(values["is_stoppable"], "is_stoppable")
    is_sentinel = _require_bool(values["is_sentinel"], "is_sentinel")
    is_generated_combo_pseudo = _require_bool(
        values["is_generated_combo_pseudo"],
        "is_generated_combo_pseudo",
    )

    is_sentinel_kind = kind == "sentinel"
    if is_sentinel != is_sentinel_kind:
        raise InvalidBmcDomain("State sentinel flag must match sentinel kind.")
    if is_sentinel:
        if state_id not in _STATE_SENTINEL_IDS:
            raise InvalidBmcDomain("Sentinel state ids must use fixed BMC ids.")
        if parent_path is not None:
            raise InvalidBmcDomain("Sentinel states cannot have parent paths.")
        if is_root:
            raise InvalidBmcDomain("Sentinel states cannot be root states.")
        if is_stoppable:
            raise InvalidBmcDomain("Sentinel states cannot be stoppable.")
        if is_generated_combo_pseudo:
            raise InvalidBmcDomain(
                "Sentinel states cannot be generated combo pseudo states."
            )
    elif state_id < 0:
        raise InvalidBmcDomain("Model state ids must be non-negative.")

    if not is_sentinel:
        if is_root and kind == "pseudo":
            raise InvalidBmcDomain("Root state cannot be a pseudo state.")
        if is_root and parent_path is not None:
            raise InvalidBmcDomain("Root state cannot have a parent path.")
        if parent_path is None:
            if state_path != state_name:
                raise InvalidBmcDomain(
                    "State path without parent must match state name."
                )
        else:
            expected_path = "%s.%s" % (parent_path, state_name)
            if state_path != expected_path:
                raise InvalidBmcDomain(
                    "State path does not match parent path and name."
                )

    if is_stoppable and kind != "leaf":
        raise InvalidBmcDomain("Only non-sentinel leaf states can be stoppable.")
    if is_generated_combo_pseudo and kind != "pseudo":
        raise InvalidBmcDomain("Generated combo states must be pseudo states.")


def _event_entry_value(entry: object, field_name: str) -> object:
    if not hasattr(entry, field_name):
        raise InvalidBmcDomain("Event entry is missing %s." % field_name)
    return getattr(entry, field_name)


def _validate_event_entry(entry: object) -> None:
    values = {field: _event_entry_value(entry, field) for field in _EVENT_ENTRY_FIELDS}
    event_id = _validate_index(values["id"], "event id")
    if event_id < 0:
        raise InvalidBmcDomain("Event ids must be non-negative.")
    event_path = _require_non_empty_string(values["path"], "event path")
    event_name = _require_non_empty_string(values["name"], "event name")
    owner_state_path = _require_non_empty_string(
        values["owner_state_path"],
        "owner_state_path",
    )
    owner_state_id = _validate_index(values["owner_state_id"], "owner_state_id")
    if owner_state_id < 0:
        raise InvalidBmcDomain("Event owner state id must be a model state id.")
    _require_bool(
        values["owner_is_generated_combo_pseudo"],
        "owner_is_generated_combo_pseudo",
    )

    expected_path = "%s.%s" % (owner_state_path, event_name)
    if event_path != expected_path:
        raise InvalidBmcDomain("Event path does not match owner state path and name.")


def _path_name(path: Sequence[str]) -> str:
    return ".".join(path)


def _state_kind(state: State) -> str:
    if state.is_pseudo:
        return "pseudo"
    if state.is_leaf_state:
        return "leaf"
    return "composite"


@dataclass(frozen=True)
class StateDomainEntry:
    """Stable identifier metadata for a model state or sentinel state.

    :param id: Stable state identifier. Normal model states use non-negative
        values; sentinel states use fixed negative values.
    :type id: int
    :param path: Dot-separated full state path.  Sentinel states use reserved
        ``$``-prefixed paths such as ``"$STATE_TERMINATE"``.
    :type path: str
    :param name: State name.  Sentinel states use their reserved sentinel names.
    :type name: str
    :param kind: ``"leaf"``, ``"composite"``, ``"pseudo"``, or
        ``"sentinel"``.
    :type kind: str
    :param parent_path: Dot-separated parent state path, defaults to ``None``.
    :type parent_path: str, optional
    :param is_root: Whether this entry is the root model state, defaults to
        ``False``.
    :type is_root: bool, optional
    :param is_stoppable: Whether the state is a stoppable runtime leaf,
        defaults to ``False``.
    :type is_stoppable: bool, optional
    :param is_sentinel: Whether this entry is a sentinel, defaults to
        ``False``.
    :type is_sentinel: bool, optional
    :param is_generated_combo_pseudo: Whether the state is a trusted generated
        combo relay pseudo state, defaults to ``False``.
    :type is_generated_combo_pseudo: bool, optional

    Example::

        >>> StateDomainEntry(0, 'Root', 'Root', 'leaf').to_canonical()['path']
        'Root'
    """

    id: int
    path: str
    name: str
    kind: str
    parent_path: Optional[str] = None
    is_root: bool = False
    is_stoppable: bool = False
    is_sentinel: bool = False
    is_generated_combo_pseudo: bool = False

    def __post_init__(self) -> None:
        _validate_state_entry(self)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable state entry dictionary.

        :return: Canonical state entry.
        :rtype: Dict[str, object]

        Example::

            >>> StateDomainEntry(0, 'Root', 'Root', 'leaf').to_canonical()['node']
            'state_domain_entry'
        """
        return {
            "node": "state_domain_entry",
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "kind": self.kind,
            "parent_path": self.parent_path,
            "is_root": self.is_root,
            "is_stoppable": self.is_stoppable,
            "is_sentinel": self.is_sentinel,
            "is_generated_combo_pseudo": self.is_generated_combo_pseudo,
        }


@dataclass(frozen=True)
class EventDomainEntry:
    """Stable identifier metadata for a model event.

    :param id: Stable event identifier.
    :type id: int
    :param path: Dot-separated full event path.
    :type path: str
    :param name: Event short name.
    :type name: str
    :param owner_state_path: Dot-separated path of the declaring owner state.
    :type owner_state_path: str
    :param owner_state_id: State-domain id of the declaring owner state.
    :type owner_state_id: int
    :param owner_is_generated_combo_pseudo: Whether the owner is a generated
        combo pseudo state, defaults to ``False``.
    :type owner_is_generated_combo_pseudo: bool, optional

    Example::

        >>> EventDomainEntry(0, 'Root.Go', 'Go', 'Root', 0).owner_state_path
        'Root'
    """

    id: int
    path: str
    name: str
    owner_state_path: str
    owner_state_id: int
    owner_is_generated_combo_pseudo: bool = False

    def __post_init__(self) -> None:
        _validate_event_entry(self)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable event entry dictionary.

        :return: Canonical event entry.
        :rtype: Dict[str, object]

        Example::

            >>> EventDomainEntry(0, 'Root.Go', 'Go', 'Root', 0).to_canonical()['node']
            'event_domain_entry'
        """
        return {
            "node": "event_domain_entry",
            "id": self.id,
            "path": self.path,
            "name": self.name,
            "owner_state_path": self.owner_state_path,
            "owner_state_id": self.owner_state_id,
            "owner_is_generated_combo_pseudo": self.owner_is_generated_combo_pseudo,
        }


@dataclass(frozen=True)
class VarDomainEntry:
    """Stable identifier metadata for a persistent model variable.

    :param id: Stable variable identifier.
    :type id: int
    :param name: Persistent variable name.
    :type name: str
    :param declared_type: Declared FCSTM variable type.
    :type declared_type: str

    Example::

        >>> VarDomainEntry(0, 'counter', 'int').to_canonical()['declared_type']
        'int'
    """

    id: int
    name: str
    declared_type: str

    def __post_init__(self) -> None:
        _validate_index(self.id, "variable id")
        if self.id < 0:
            raise InvalidBmcDomain("Variable ids must be non-negative.")
        _require_non_empty_string(self.name, "variable name")
        _require_non_empty_string(self.declared_type, "declared_type")

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable variable entry dictionary.

        :return: Canonical variable entry.
        :rtype: Dict[str, object]

        Example::

            >>> VarDomainEntry(0, 'x', 'int').to_canonical()['node']
            'var_domain_entry'
        """
        return {
            "node": "var_domain_entry",
            "id": self.id,
            "name": self.name,
            "declared_type": self.declared_type,
        }


@dataclass(frozen=True)
class FrameRef:
    """Reference to a bounded trace frame ``F_i``.

    ``F_0`` is the initial frame and can represent cold root, hot arbitrary
    state, or terminated initial conditions.  Recurrence frames ``F_1..F_N``
    are produced by macro-step transitions and are later constrained to stable
    leaf or sentinel states.

    :param index: Frame index.
    :type index: int
    :param bound: Positive BMC bound.
    :type bound: int

    Example::

        >>> FrameRef(0, 2).role
        'initial'
        >>> FrameRef(2, 2).name
        'F_2'
    """

    index: int
    bound: int

    def __post_init__(self) -> None:
        _validate_positive_bound(self.bound)
        _validate_index(self.index, "frame index")
        if self.index < 0 or self.index > self.bound:
            raise InvalidBmcDomain("frame index must satisfy 0 <= index <= bound.")

    @property
    def name(self) -> str:
        """Return the canonical frame name.

        :return: Frame name such as ``"F_0"``.
        :rtype: str

        Example::

            >>> FrameRef(1, 2).name
            'F_1'
        """
        return "F_%d" % self.index

    @property
    def role(self) -> str:
        """Return the frame role.

        :return: ``"initial"`` for ``F_0`` and ``"transition"`` otherwise.
        :rtype: str

        Example::

            >>> FrameRef(0, 1).role
            'initial'
        """
        return "initial" if self.index == 0 else "transition"

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable frame dictionary.

        :return: Canonical frame reference.
        :rtype: Dict[str, object]

        Example::

            >>> FrameRef(1, 2).to_canonical()['name']
            'F_1'
        """
        return {
            "node": "frame_ref",
            "index": self.index,
            "bound": self.bound,
            "name": self.name,
            "role": self.role,
        }

    def __str__(self) -> str:
        """Return the canonical frame name.

        :return: Frame name.
        :rtype: str

        Example::

            >>> str(FrameRef(0, 1))
            'F_0'
        """
        return self.name


@dataclass(frozen=True)
class StepRef:
    """Reference to a bounded trace step input ``E_i``.

    :param index: Step index.
    :type index: int
    :param bound: Positive BMC bound.
    :type bound: int

    Example::

        >>> StepRef(0, 1).name
        'E_0'
    """

    index: int
    bound: int

    def __post_init__(self) -> None:
        _validate_positive_bound(self.bound)
        _validate_index(self.index, "step index")
        if self.index < 0 or self.index >= self.bound:
            raise InvalidBmcDomain("step index must satisfy 0 <= index < bound.")

    @property
    def name(self) -> str:
        """Return the canonical step name.

        :return: Step name such as ``"E_0"``.
        :rtype: str

        Example::

            >>> StepRef(0, 2).name
            'E_0'
        """
        return "E_%d" % self.index

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable step dictionary.

        :return: Canonical step reference.
        :rtype: Dict[str, object]

        Example::

            >>> StepRef(0, 2).to_canonical()['node']
            'step_ref'
        """
        return {
            "node": "step_ref",
            "index": self.index,
            "bound": self.bound,
            "name": self.name,
        }

    def __str__(self) -> str:
        """Return the canonical step name.

        :return: Step name.
        :rtype: str

        Example::

            >>> str(StepRef(0, 1))
            'E_0'
        """
        return self.name


@dataclass(frozen=True)
class EventInputRef:
    """Reference to one event input slot at one step.

    :param step_index: Step index.
    :type step_index: int
    :param event_id: Event-domain id.
    :type event_id: int
    :param event_path: Dot-separated event path used in the display name.
    :type event_path: str

    Example::

        >>> EventInputRef(0, 2, 'Root.Go').name
        'E_0[Root.Go]'
    """

    step_index: int
    event_id: int
    event_path: str

    def __post_init__(self) -> None:
        _validate_index(self.step_index, "step_index")
        _validate_index(self.event_id, "event_id")
        if self.step_index < 0:
            raise InvalidBmcDomain("step_index must be non-negative.")
        if self.event_id < 0:
            raise InvalidBmcDomain("event_id must be non-negative.")
        _require_non_empty_string(self.event_path, "event_path")

    @property
    def name(self) -> str:
        """Return the canonical event input display name.

        :return: Input slot name such as ``"E_0[Root.Go]"``.
        :rtype: str

        Example::

            >>> EventInputRef(0, 1, 'Root.Go').name
            'E_0[Root.Go]'
        """
        return "E_%d[%s]" % (self.step_index, self.event_path)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable event input dictionary.

        :return: Canonical event input reference.
        :rtype: Dict[str, object]

        Example::

            >>> EventInputRef(0, 1, 'Root.Go').to_canonical()['event_id']
            1
        """
        return {
            "node": "event_input_ref",
            "step_index": self.step_index,
            "event_id": self.event_id,
            "event_path": self.event_path,
            "name": self.name,
        }


@dataclass(frozen=True)
class BmcDomain:
    """Complete bounded model checking domain snapshot.

    :param bound: Positive BMC bound.
    :type bound: int
    :param states: State-domain entries, including sentinel entries.
    :type states: Tuple[StateDomainEntry, ...]
    :param events: Event-domain entries.
    :type events: Tuple[EventDomainEntry, ...]
    :param variables: Persistent variable-domain entries.
    :type variables: Tuple[VarDomainEntry, ...]
    :param frames: Frame references ``F_0..F_N``.
    :type frames: Tuple[FrameRef, ...]
    :param steps: Step references ``E_0..E_{N-1}``.
    :type steps: Tuple[StepRef, ...]
    :param event_inputs: Step/event input slots.  Domain snapshots require the
        full step-by-event Cartesian product; query and relation layers perform
        later pruning or cardinality constraints.
    :type event_inputs: Tuple[EventInputRef, ...]
    :param initial_state_ids: State ids allowed at ``F_0``.
    :type initial_state_ids: Tuple[int, ...]
    :param stable_state_ids: State ids allowed at recurrence frame boundaries.
    :type stable_state_ids: Tuple[int, ...]
    :param model: Optional source model back-reference used by model-aware BMC
        layers, defaults to ``None``.  It is intentionally excluded from
        equality and canonical snapshots.
    :type model: StateMachine, optional

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> domain.to_canonical()['node']
        'bmc_domain'
    """

    bound: int
    states: Tuple[StateDomainEntry, ...]
    events: Tuple[EventDomainEntry, ...]
    variables: Tuple[VarDomainEntry, ...]
    frames: Tuple[FrameRef, ...]
    steps: Tuple[StepRef, ...]
    event_inputs: Tuple[EventInputRef, ...]
    initial_state_ids: Tuple[int, ...]
    stable_state_ids: Tuple[int, ...]
    model: Optional[StateMachine] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        _validate_positive_bound(self.bound)
        self._normalize_sequence("states", self.states, StateDomainEntry)
        self._normalize_sequence("events", self.events, EventDomainEntry)
        self._normalize_sequence("variables", self.variables, VarDomainEntry)
        self._normalize_sequence("frames", self.frames, FrameRef)
        self._normalize_sequence("steps", self.steps, StepRef)
        self._normalize_sequence("event_inputs", self.event_inputs, EventInputRef)
        self._normalize_int_sequence("initial_state_ids", self.initial_state_ids)
        self._normalize_int_sequence("stable_state_ids", self.stable_state_ids)
        self._validate_state_entries()
        self._validate_event_entries()
        self._validate_unique_entries()
        self._validate_sentinel_entries()
        self._validate_state_topology()
        self._validate_trace_references()
        self._validate_event_owners()
        self._validate_event_inputs()
        self._validate_allowed_state_ids()
        if self.model is not None and not isinstance(self.model, StateMachine):
            raise InvalidBmcDomain("model must be StateMachine when provided.")

    @property
    def frame0_state_ids(self) -> Tuple[int, ...]:
        """Return state ids allowed in the initial frame.

        :return: Initial-frame state ids.
        :rtype: Tuple[int, ...]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> domain.frame0_state_ids == domain.initial_state_ids
            True
        """
        return self.initial_state_ids

    @property
    def recurrence_state_ids(self) -> Tuple[int, ...]:
        """Return state ids allowed at recurrence frame boundaries.

        :return: Recurrence-frame state ids.
        :rtype: Tuple[int, ...]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> domain.recurrence_state_ids == domain.stable_state_ids
            True
        """
        return self.stable_state_ids

    def _normalize_sequence(
        self, field_name: str, value: Sequence[Any], item_type: type
    ) -> None:
        if not isinstance(value, (list, tuple)):
            raise InvalidBmcDomain(f"{field_name} must be a sequence.")
        items = tuple(value)
        if not all(isinstance(item, item_type) for item in items):
            raise InvalidBmcDomain(
                f"{field_name} must contain {item_type.__name__} objects."
            )
        sort_key = {
            "states": lambda item: (item.id, item.path),
            "events": lambda item: (item.id, item.path),
            "variables": lambda item: (item.id, item.name),
            "frames": lambda item: item.index,
            "steps": lambda item: item.index,
            "event_inputs": lambda item: (item.step_index, item.event_id),
        }[field_name]
        items = tuple(sorted(items, key=sort_key))
        object.__setattr__(self, field_name, items)

    def _normalize_int_sequence(self, field_name: str, value: Sequence[int]) -> None:
        if not isinstance(value, (list, tuple)):
            raise InvalidBmcDomain(f"{field_name} must be a sequence.")
        raw_items = tuple(value)
        if not all(
            not isinstance(item, bool) and isinstance(item, int) for item in raw_items
        ):
            raise InvalidBmcDomain(f"{field_name} must contain integer ids.")
        items = tuple(sorted(raw_items))
        object.__setattr__(self, field_name, items)

    def _validate_state_entries(self) -> None:
        for entry in self.states:
            _validate_state_entry(entry)

    def _validate_event_entries(self) -> None:
        for entry in self.events:
            _validate_event_entry(entry)

    def _validate_unique_entries(self) -> None:
        self._validate_unique("state id", (entry.id for entry in self.states))
        self._validate_unique("state path", (entry.path for entry in self.states))
        self._validate_unique("event id", (entry.id for entry in self.events))
        self._validate_unique("event path", (entry.path for entry in self.events))
        self._validate_unique("variable id", (entry.id for entry in self.variables))
        self._validate_unique("variable name", (entry.name for entry in self.variables))
        self._validate_unique("frame index", (frame.index for frame in self.frames))
        self._validate_unique("step index", (step.index for step in self.steps))
        self._validate_unique("initial state id", self.initial_state_ids)
        self._validate_unique("stable state id", self.stable_state_ids)
        self._validate_unique(
            "event input slot",
            ((item.step_index, item.event_id) for item in self.event_inputs),
        )

    def _validate_sentinel_entries(self) -> None:
        entries_by_id = {entry.id: entry for entry in self.states}
        terminate = entries_by_id.get(STATE_TERMINATE_ID)
        init = entries_by_id.get(STATE_INIT_ID)
        if init is None:
            raise InvalidBmcDomain("Domain must contain the init sentinel.")
        if terminate is None:
            raise InvalidBmcDomain("Domain must contain the terminate sentinel.")
        if (
            terminate.path != _STATE_TERMINATE_PATH
            or terminate.name != "STATE_TERMINATE"
            or terminate.kind != "sentinel"
            or not terminate.is_sentinel
        ):
            raise InvalidBmcDomain("Terminate sentinel entry is malformed.")
        if (
            init.path != _STATE_INIT_PATH
            or init.name != "STATE_INIT"
            or init.kind != "sentinel"
            or not init.is_sentinel
        ):
            raise InvalidBmcDomain("Init sentinel entry is malformed.")

    def _validate_state_topology(self) -> None:
        """Validate model-state parent and root topology.

        :return: ``None``.
        :rtype: None
        :raises InvalidBmcDomain: If model state paths, names, root flags, or
            parent links are inconsistent.
        """
        entries_by_path = {entry.path: entry for entry in self.states}
        model_entries = [entry for entry in self.states if not entry.is_sentinel]
        root_entries = [entry for entry in model_entries if entry.is_root]
        if len(root_entries) != 1:
            raise InvalidBmcDomain("Domain must contain exactly one model root state.")

        for entry in model_entries:
            if entry.is_root:
                continue
            if entry.parent_path is None:
                raise InvalidBmcDomain(
                    "Non-root state %r must have a parent path." % (entry.path,)
                )
            parent = entries_by_path.get(entry.parent_path)
            if parent is None or parent.is_sentinel:
                raise InvalidBmcDomain(
                    "State %r parent path is unknown." % (entry.path,)
                )
            if parent.kind != "composite":
                raise InvalidBmcDomain(
                    "State %r parent must be a composite state." % (entry.path,)
                )

    def _validate_trace_references(self) -> None:
        if len(self.frames) != self.bound + 1:
            raise InvalidBmcDomain("Domain must contain bound + 1 frames.")
        if len(self.steps) != self.bound:
            raise InvalidBmcDomain("Domain must contain bound steps.")
        frame_indexes = {frame.index for frame in self.frames}
        step_indexes = {step.index for step in self.steps}
        if frame_indexes != set(range(self.bound + 1)):
            raise InvalidBmcDomain("Frame indexes must cover 0..bound.")
        if step_indexes != set(range(self.bound)):
            raise InvalidBmcDomain("Step indexes must cover 0..bound-1.")
        for frame in self.frames:
            if frame.bound != self.bound:
                raise InvalidBmcDomain("Frame bound does not match domain bound.")
        for step in self.steps:
            if step.bound != self.bound:
                raise InvalidBmcDomain("Step bound does not match domain bound.")

    def _validate_event_owners(self) -> None:
        entries_by_id = {entry.id: entry for entry in self.states}
        for event in self.events:
            owner = entries_by_id.get(event.owner_state_id)
            if owner is None:
                raise InvalidBmcDomain(
                    "Event %r has unknown owner state id: %r."
                    % (event.path, event.owner_state_id)
                )
            if owner.path != event.owner_state_path:
                raise InvalidBmcDomain(
                    "Event %r owner path does not match owner state id." % (event.path,)
                )
            _require_bool(
                event.owner_is_generated_combo_pseudo,
                "owner_is_generated_combo_pseudo",
            )
            if owner.is_generated_combo_pseudo != event.owner_is_generated_combo_pseudo:
                raise InvalidBmcDomain(
                    "Event %r owner generated-combo flag is inconsistent."
                    % (event.path,)
                )

    def _validate_event_inputs(self) -> None:
        step_indexes = {step.index for step in self.steps}
        events_by_id = {event.id: event for event in self.events}
        expected_slots = set()
        for step in self.steps:
            for event in self.events:
                expected_slots.add((step.index, event.id))

        actual_slots = set()
        for item in self.event_inputs:
            if item.step_index not in step_indexes:
                raise InvalidBmcDomain(
                    "Event input %r uses an unknown step index." % (item.name,)
                )
            event = events_by_id.get(item.event_id)
            if event is None:
                raise InvalidBmcDomain(
                    "Event input %r uses an unknown event id." % (item.name,)
                )
            if item.event_path != event.path:
                raise InvalidBmcDomain(
                    "Event input %r path does not match event id." % (item.name,)
                )
            actual_slots.add((item.step_index, item.event_id))

        if actual_slots != expected_slots:
            missing = sorted(expected_slots - actual_slots)
            raise InvalidBmcDomain(
                "Domain is missing event input slot: %r." % (missing[0],)
            )

    def _validate_allowed_state_ids(self) -> None:
        state_ids = {entry.id for entry in self.states}
        missing_initial = [
            item for item in self.initial_state_ids if item not in state_ids
        ]
        if missing_initial:
            raise InvalidBmcDomain(
                "initial_state_ids contains unknown state id: %r."
                % (missing_initial[0],)
            )
        missing_stable = [
            item for item in self.stable_state_ids if item not in state_ids
        ]
        if missing_stable:
            raise InvalidBmcDomain(
                "stable_state_ids contains unknown state id: %r." % (missing_stable[0],)
            )

        expected_initial = tuple(
            sorted(
                [entry.id for entry in self.states if not entry.is_sentinel]
                + [STATE_INIT_ID, STATE_TERMINATE_ID]
            )
        )
        if self.initial_state_ids != expected_initial:
            raise InvalidBmcDomain(
                "initial_state_ids must contain every model state id plus "
                "the init and terminate sentinels only."
            )

        expected_stable = tuple(
            sorted(
                [
                    entry.id
                    for entry in self.states
                    if entry.kind == "leaf" and entry.is_stoppable
                ]
                + [STATE_TERMINATE_ID]
            )
        )
        if self.stable_state_ids != expected_stable:
            raise InvalidBmcDomain(
                "stable_state_ids must contain stoppable model state ids plus "
                "the terminate sentinel only."
            )

    @staticmethod
    def _validate_unique(name: str, values: Iterable[Any]) -> None:
        seen = set()
        for value in values:
            if value in seen:
                raise InvalidBmcDomain("Duplicate %s: %r." % (name, value))
            seen.add(value)

    def state_by_id(self, state_id: int) -> StateDomainEntry:
        """Return the state entry with ``state_id``.

        :param state_id: State id to look up.
        :type state_id: int
        :return: Matching state-domain entry.
        :rtype: StateDomainEntry
        :raises InvalidBmcDomain: If no state has ``state_id``.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> domain.state_by_id(domain.state_path_to_id('Root')).path
            'Root'
        """
        _validate_index(state_id, "state_id")
        for entry in self.states:
            if entry.id == state_id:
                return entry
        raise InvalidBmcDomain("Unknown state id: %r." % (state_id,))

    def state_by_path(self, path: str) -> StateDomainEntry:
        """Return the state entry with ``path``.

        :param path: Dot-separated state path.  Sentinel states use reserved
            ``$``-prefixed paths such as ``"$STATE_TERMINATE"``.
        :type path: str
        :return: Matching state-domain entry.
        :rtype: StateDomainEntry
        :raises InvalidBmcDomain: If no state has ``path``.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> domain.state_by_path('$STATE_TERMINATE').name
            'STATE_TERMINATE'
        """
        _require_non_empty_string(path, "state path")
        for entry in self.states:
            if entry.path == path:
                return entry
        raise InvalidBmcDomain("Unknown state path: %r." % (path,))

    def state_path_to_id(self, path: str) -> int:
        """Return the id for a state path.

        :param path: Dot-separated state path.  Sentinel states use reserved
            ``$``-prefixed paths such as ``"$STATE_TERMINATE"``.
        :type path: str
        :return: State id.
        :rtype: int
        :raises InvalidBmcDomain: If ``path`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> domain.state_path_to_id('$STATE_INIT')
            -3
        """
        return self.state_by_path(path).id

    def state_id_to_path(self, state_id: int) -> str:
        """Return the path for a state id.

        :param state_id: State id.
        :type state_id: int
        :return: Dot-separated state path, or a reserved ``$``-prefixed
            sentinel path.
        :rtype: str
        :raises InvalidBmcDomain: If ``state_id`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> domain.state_id_to_path(STATE_TERMINATE_ID)
            '$STATE_TERMINATE'
        """
        return self.state_by_id(state_id).path

    def event_by_id(self, event_id: int) -> EventDomainEntry:
        """Return the event entry with ``event_id``.

        :param event_id: Event id to look up.
        :type event_id: int
        :return: Matching event-domain entry.
        :rtype: EventDomainEntry
        :raises InvalidBmcDomain: If no event has ``event_id``.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { event Go; state A; [*] -> A; }')
            >>> build_bmc_domain(model, 1).event_by_id(0).path
            'Root.Go'
        """
        _validate_index(event_id, "event_id")
        for entry in self.events:
            if entry.id == event_id:
                return entry
        raise InvalidBmcDomain("Unknown event id: %r." % (event_id,))

    def event_by_path(self, path: str) -> EventDomainEntry:
        """Return the event entry with ``path``.

        :param path: Dot-separated event path.
        :type path: str
        :return: Matching event-domain entry.
        :rtype: EventDomainEntry
        :raises InvalidBmcDomain: If ``path`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { event Go; state A; [*] -> A; }')
            >>> build_bmc_domain(model, 1).event_by_path('Root.Go').name
            'Go'
        """
        _require_non_empty_string(path, "event path")
        for entry in self.events:
            if entry.path == path:
                return entry
        raise InvalidBmcDomain("Unknown event path: %r." % (path,))

    def event_path_to_id(self, path: str) -> int:
        """Return the id for an event path.

        :param path: Dot-separated event path.
        :type path: str
        :return: Event id.
        :rtype: int
        :raises InvalidBmcDomain: If ``path`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { event Go; state A; [*] -> A; }')
            >>> build_bmc_domain(model, 1).event_path_to_id('Root.Go')
            0
        """
        return self.event_by_path(path).id

    def event_id_to_path(self, event_id: int) -> str:
        """Return the path for an event id.

        :param event_id: Event id.
        :type event_id: int
        :return: Dot-separated event path.
        :rtype: str
        :raises InvalidBmcDomain: If ``event_id`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { event Go; state A; [*] -> A; }')
            >>> build_bmc_domain(model, 1).event_id_to_path(0)
            'Root.Go'
        """
        return self.event_by_id(event_id).path

    def variable_by_id(self, variable_id: int) -> VarDomainEntry:
        """Return the variable entry with ``variable_id``.

        :param variable_id: Variable id.
        :type variable_id: int
        :return: Matching variable-domain entry.
        :rtype: VarDomainEntry
        :raises InvalidBmcDomain: If ``variable_id`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('def int x = 0; state Root;')
            >>> build_bmc_domain(model, 1).variable_by_id(0).name
            'x'
        """
        _validate_index(variable_id, "variable_id")
        for entry in self.variables:
            if entry.id == variable_id:
                return entry
        raise InvalidBmcDomain("Unknown variable id: %r." % (variable_id,))

    def variable_by_name(self, name: str) -> VarDomainEntry:
        """Return the variable entry with ``name``.

        :param name: Persistent variable name.
        :type name: str
        :return: Matching variable-domain entry.
        :rtype: VarDomainEntry
        :raises InvalidBmcDomain: If ``name`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('def int x = 0; state Root;')
            >>> build_bmc_domain(model, 1).variable_by_name('x').declared_type
            'int'
        """
        _require_non_empty_string(name, "variable name")
        for entry in self.variables:
            if entry.name == name:
                return entry
        raise InvalidBmcDomain("Unknown variable name: %r." % (name,))

    def variable_name_to_id(self, name: str) -> int:
        """Return the id for a persistent variable name.

        :param name: Persistent variable name.
        :type name: str
        :return: Variable id.
        :rtype: int
        :raises InvalidBmcDomain: If ``name`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('def int x = 0; state Root;')
            >>> build_bmc_domain(model, 1).variable_name_to_id('x')
            0
        """
        return self.variable_by_name(name).id

    def variable_id_to_name(self, variable_id: int) -> str:
        """Return the name for a variable id.

        :param variable_id: Variable id.
        :type variable_id: int
        :return: Variable name.
        :rtype: str
        :raises InvalidBmcDomain: If ``variable_id`` is unknown.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('def int x = 0; state Root;')
            >>> build_bmc_domain(model, 1).variable_id_to_name(0)
            'x'
        """
        return self.variable_by_id(variable_id).name

    def event_input(self, step: StepRef, event_id: int) -> EventInputRef:
        """Return the input slot for ``step`` and ``event_id``.

        :param step: Step reference.
        :type step: StepRef
        :param event_id: Event-domain id.
        :type event_id: int
        :return: Matching event input reference.
        :rtype: EventInputRef
        :raises InvalidBmcDomain: If the step or event id is outside this
            domain.

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { event Go; state A; [*] -> A; }')
            >>> domain = build_bmc_domain(model, 1)
            >>> domain.event_input(StepRef(0, 1), domain.event_path_to_id('Root.Go')).name
            'E_0[Root.Go]'
        """
        if not isinstance(step, StepRef):
            raise InvalidBmcDomain("step must be a StepRef.")
        if step.bound != self.bound:
            raise InvalidBmcDomain("step bound does not match domain bound.")
        _validate_index(event_id, "event_id")
        self.event_by_id(event_id)
        for entry in self.event_inputs:
            if entry.step_index == step.index and entry.event_id == event_id:
                return entry
        raise InvalidBmcDomain(
            "Unknown event input slot: step=%r, event_id=%r." % (step.index, event_id)
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable domain dictionary.

        :return: Canonical domain snapshot.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> domain.to_canonical()['sentinels']['terminate']
            -1
        """
        return {
            "node": "bmc_domain",
            "bound": self.bound,
            "states": [entry.to_canonical() for entry in self.states],
            "events": [entry.to_canonical() for entry in self.events],
            "variables": [entry.to_canonical() for entry in self.variables],
            "frames": [entry.to_canonical() for entry in self.frames],
            "steps": [entry.to_canonical() for entry in self.steps],
            "event_inputs": [entry.to_canonical() for entry in self.event_inputs],
            "initial_state_ids": list(self.initial_state_ids),
            "frame0_state_ids": list(self.frame0_state_ids),
            "stable_state_ids": list(self.stable_state_ids),
            "recurrence_state_ids": list(self.recurrence_state_ids),
            "sentinels": {
                "init": STATE_INIT_ID,
                "terminate": STATE_TERMINATE_ID,
            },
        }


def _sentinel_entries() -> Tuple[StateDomainEntry, StateDomainEntry]:
    return (
        StateDomainEntry(
            id=STATE_INIT_ID,
            path=_STATE_INIT_PATH,
            name="STATE_INIT",
            kind="sentinel",
            is_sentinel=True,
        ),
        StateDomainEntry(
            id=STATE_TERMINATE_ID,
            path=_STATE_TERMINATE_PATH,
            name="STATE_TERMINATE",
            kind="sentinel",
            is_sentinel=True,
        ),
    )


def _model_state_entries(model: StateMachine) -> Tuple[StateDomainEntry, ...]:
    states = sorted(model.walk_states(), key=lambda state: _path_name(state.path))
    return tuple(
        StateDomainEntry(
            id=index,
            path=_path_name(state.path),
            name=state.name,
            kind=_state_kind(state),
            parent_path=_path_name(state.parent.path)
            if state.parent is not None
            else None,
            is_root=state.is_root_state,
            is_stoppable=state.is_stoppable,
            is_sentinel=False,
            is_generated_combo_pseudo=bool(
                getattr(state, "_generated_combo_pseudo", False)
            ),
        )
        for index, state in enumerate(states)
    )


def _collect_events(model: StateMachine) -> Tuple[Event, ...]:
    events_by_path = {}
    for state in model.walk_states():
        for event in state.events.values():
            events_by_path[event.path_name] = event
        for transition in state.transitions:
            if transition.event is not None:
                events_by_path[transition.event.path_name] = transition.event
    return tuple(events_by_path[path] for path in sorted(events_by_path))


def _event_entries(
    events: Sequence[Event], states_by_path: Dict[str, StateDomainEntry]
) -> Tuple[EventDomainEntry, ...]:
    entries = []
    for index, event in enumerate(events):
        owner_state_path = _path_name(event.state_path)
        owner_entry = states_by_path.get(owner_state_path)
        if owner_entry is None:
            raise InvalidBmcDomain(
                "Event %r has unknown owner state %r."
                % (event.path_name, owner_state_path)
            )
        entries.append(
            EventDomainEntry(
                id=index,
                path=event.path_name,
                name=event.name,
                owner_state_path=owner_state_path,
                owner_state_id=owner_entry.id,
                owner_is_generated_combo_pseudo=owner_entry.is_generated_combo_pseudo,
            )
        )
    return tuple(entries)


def _variable_entries(model: StateMachine) -> Tuple[VarDomainEntry, ...]:
    return tuple(
        VarDomainEntry(index, name, define.type)
        for index, (name, define) in enumerate(model.defines.items())
    )


def build_bmc_domain(model: StateMachine, bound: int) -> BmcDomain:
    """Build a BMC domain snapshot from a state machine and bound.

    The domain contains all model states, all resolved model events, all
    persistent variable declarations, fixed sentinel states, frame references,
    step references, and independent step/event input slots.  It does not bind
    a query, build macro-step cases, or allocate solver symbols.

    :param model: State machine to number.
    :type model: StateMachine
    :param bound: Positive BMC bound.
    :type bound: int
    :return: Complete BMC domain snapshot.
    :rtype: BmcDomain
    :raises InvalidBmcDomain: If ``model`` is not a state machine or ``bound``
        is not positive.

    Example::

        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { event Go; state A; [*] -> A; }')
        >>> domain = build_bmc_domain(model, 1)
        >>> domain.event_path_to_id('Root.Go')
        0
    """
    if not isinstance(model, StateMachine):
        raise InvalidBmcDomain("model must be StateMachine.")
    bound = _validate_positive_bound(bound)

    model_state_entries = _model_state_entries(model)
    states_by_path = {entry.path: entry for entry in model_state_entries}
    states = tuple(
        sorted(_sentinel_entries() + model_state_entries, key=lambda e: e.id)
    )
    events = _event_entries(_collect_events(model), states_by_path)
    variables = _variable_entries(model)
    frames = tuple(FrameRef(index, bound) for index in range(bound + 1))
    steps = tuple(StepRef(index, bound) for index in range(bound))
    event_inputs = tuple(
        EventInputRef(step.index, event.id, event.path)
        for step in steps
        for event in events
    )

    normal_state_ids = tuple(entry.id for entry in model_state_entries)
    initial_state_ids = tuple(
        sorted(normal_state_ids + (STATE_INIT_ID, STATE_TERMINATE_ID))
    )
    stable_state_ids = tuple(
        sorted(
            tuple(entry.id for entry in model_state_entries if entry.is_stoppable)
            + (STATE_TERMINATE_ID,)
        )
    )

    return BmcDomain(
        bound=bound,
        states=states,
        events=events,
        variables=variables,
        frames=frames,
        steps=steps,
        event_inputs=event_inputs,
        initial_state_ids=initial_state_ids,
        stable_state_ids=stable_state_ids,
        model=model,
    )


__all__ = [
    "STATE_INIT_ID",
    "STATE_TERMINATE_ID",
    "StateDomainEntry",
    "EventDomainEntry",
    "VarDomainEntry",
    "FrameRef",
    "StepRef",
    "EventInputRef",
    "BmcDomain",
    "build_bmc_domain",
]

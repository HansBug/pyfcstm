"""Top-level FCSTM BMC query data model.

The query model is intentionally parser-independent.  It captures the shape of
``*.fbmcq`` files after syntax parsing but before model-aware semantic binding,
state/event resolution, solver lowering, or witness replay.  Parser and binder
layers can construct these frozen dataclasses from ANTLR parse trees and then
bind them against :class:`pyfcstm.model.StateMachine` objects.

Design contracts:

* Query objects are data-only and must not import ``pyfcstm.verify`` or solver
  internals.
* :func:`str` on every concrete query object returns canonical ``.fbmcq`` DSL
  text that later parser work must accept for round-trip tests.
* :func:`repr` remains the dataclass debugging representation and is not a DSL
  surface.
* :meth:`to_canonical` is the language-neutral golden shape for parser,
  binder, and compiler parity tests.

The module contains:

* :class:`InitialSpec` - Cold, terminated, or state hot-start initial condition.
* :class:`FrameAssumption`, :class:`EventAssumption`, and
  :class:`EventCardinalityAssumption` - Environment assumptions.
* :class:`BmcProperty` - Skeleton for reachability, safety, response, and cover
  goals.
* :class:`BmcQuery` - Complete query root object.

Example::

    >>> from pyfcstm.bmc.ast import Active
    >>> from pyfcstm.bmc.query import BmcProperty, BmcQuery
    >>> query = BmcQuery(property=BmcProperty("reach", 3, predicate=Active("Root.Done")))
    >>> query.to_canonical()["property"]["kind"]
    'reach'
"""

from __future__ import annotations

import json
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, ClassVar, Dict, Optional, Tuple, Union

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

from pyfcstm.bmc.ast import BmcCondExpr
from pyfcstm.bmc.errors import InvalidBmcQuery

_CanonicalDict = Dict[str, Any]
_QuerySelector = Union[int, Literal["*"], str]

_INITIAL_MODES = {"cold", "terminated", "state"}
_FRAME_ASSUMPTION_KINDS = {"always", "at"}
_EVENT_CARDINALITY_KINDS = {"any", "at_most_one"}
_PROPERTY_KINDS = {
    "reach",
    "forbid",
    "invariant",
    "must_reach",
    "exists_always",
    "response",
    "cover",
}


def _canonical_condition(expr: Optional[BmcCondExpr]) -> Optional[_CanonicalDict]:
    if expr is None:
        return None
    return expr.to_canonical()


def _require_condition(value: Optional[BmcCondExpr], field_name: str) -> None:
    if not isinstance(value, BmcCondExpr):
        raise InvalidBmcQuery(f"{field_name} must be BmcCondExpr.")


def _validate_choice(value: str, choices: set, field_name: str) -> None:
    if not isinstance(value, str) or value not in choices:
        raise InvalidBmcQuery(f"Unsupported {field_name}: {value!r}.")


def _require_non_empty_string(value: object, field_name: str) -> None:
    if not isinstance(value, str) or not value:
        raise InvalidBmcQuery(f"{field_name} must be a non-empty string.")


def _normalize_positive_integer(value: int, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBmcQuery(f"{field_name} must be a positive integer.")
    if value <= 0:
        raise InvalidBmcQuery(f"{field_name} must be a positive integer.")
    return value


def _normalize_frame(frame: Optional[int]) -> Optional[int]:
    if frame is None:
        return None
    if isinstance(frame, bool) or not isinstance(frame, int):
        raise InvalidBmcQuery("frame must be a non-negative integer.")
    if frame < 0:
        raise InvalidBmcQuery("frame must be a non-negative integer.")
    return frame


def _is_ascii_decimal(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _normalize_selector(selector: _QuerySelector) -> _QuerySelector:
    if isinstance(selector, bool):
        raise InvalidBmcQuery(
            "selector must be '*', a non-negative integer, or an inclusive range."
        )
    if isinstance(selector, int):
        if selector < 0:
            raise InvalidBmcQuery("selector must be non-negative.")
        return selector
    if isinstance(selector, str):
        if selector == "*":
            return selector
        if _is_ascii_decimal(selector):
            return int(selector)
        parts = selector.split("..")
        if len(parts) == 2 and all(_is_ascii_decimal(part) for part in parts):
            start, end = (int(parts[0]), int(parts[1]))
            if start <= end:
                if start == end:
                    return start
                return "%d..%d" % (start, end)
    raise InvalidBmcQuery(
        "selector must be '*', a non-negative integer, or an inclusive range."
    )


def _quote_string(value: str) -> str:
    return json.dumps(value, ensure_ascii=False)


def _selector_to_dsl(selector: _QuerySelector) -> str:
    return str(selector)


def _bool_to_dsl(value: bool) -> str:
    return "true" if value else "false"


def _format_block(lines: Tuple[str, ...]) -> str:
    return "\n".join("    %s" % line for line in lines)


@dataclass(frozen=True)
class InitialSpec:
    """Initial BMC frame specification.

    :param mode: Initial mode: ``"cold"``, ``"terminated"``, or ``"state"``.
        Defaults to ``"cold"``.
    :type mode: str, optional
    :param state_path: State path for ``mode="state"``, defaults to ``None``.
    :type state_path: Optional[str], optional
    :param predicate: Optional initial-state predicate that contributes only to
        the initial condition, defaults to ``None``.
    :type predicate: Optional[BmcCondExpr], optional

    Example::

        >>> InitialSpec().to_canonical()["mode"]
        'cold'
        >>> InitialSpec(mode="state", state_path="Root.Active").state_path
        'Root.Active'
    """

    _node_name: ClassVar[str] = "initial_spec"

    mode: str = "cold"
    state_path: Optional[str] = None
    predicate: Optional[BmcCondExpr] = None

    def __post_init__(self) -> None:
        _validate_choice(self.mode, _INITIAL_MODES, "initial mode")
        if self.mode == "state" and (
            not isinstance(self.state_path, str) or not self.state_path
        ):
            raise InvalidBmcQuery(
                "state_path is required when initial mode is 'state'."
            )
        if self.mode != "state" and self.state_path is not None:
            raise InvalidBmcQuery(
                "state_path is only valid when initial mode is 'state'."
            )
        if self.predicate is not None:
            _require_condition(self.predicate, "predicate")

    def to_canonical(self) -> _CanonicalDict:
        """Return a stable canonical initial-spec dictionary.

        :return: Canonical initial specification.
        :rtype: Dict[str, object]

        Example::

            >>> InitialSpec().to_canonical()["node"]
            'initial_spec'
        """
        return {
            "node": self._node_name,
            "mode": self.mode,
            "state_path": self.state_path,
            "predicate": _canonical_condition(self.predicate),
        }

    def __str__(self) -> str:
        """Return the canonical ``.fbmcq`` DSL spelling for this initial clause.

        :return: Initial clause text.
        :rtype: str

        Example::

            >>> str(InitialSpec())
            'init cold;'
        """
        if self.mode == "state":
            target = "state(%s)" % _quote_string(self.state_path or "")
        else:
            target = self.mode
        if self.predicate is None:
            return "init %s;" % target
        return "init %s where %s;" % (target, self.predicate)


class BmcAssumption(ABC):
    """Base class for BMC environment assumptions.

    :cvar _node_name: Canonical node tag emitted by
        :meth:`BmcAssumption.to_canonical`.
    :type _node_name: str

    Example::

        >>> from pyfcstm.bmc.ast import BoolLiteral
        >>> isinstance(FrameAssumption("always", BoolLiteral("true")), BmcAssumption)
        True
    """

    _node_name: ClassVar[str] = "assumption"

    def to_canonical(self) -> _CanonicalDict:
        """Return a stable canonical assumption dictionary.

        :return: Canonical assumption dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.ast import BoolLiteral
            >>> FrameAssumption("always", BoolLiteral("true")).to_canonical()["node"]
            'frame_assumption'
        """
        result = {"node": self._node_name}
        result.update(self._canonical_payload())
        return result

    def __str__(self) -> str:
        """Return the canonical ``.fbmcq`` DSL spelling for this assumption.

        :return: Assumption clause text.
        :rtype: str

        Example::

            >>> from pyfcstm.bmc.ast import BoolLiteral
            >>> str(FrameAssumption("always", BoolLiteral("true")))
            'assume always: true;'
        """
        return self._to_dsl()

    @abstractmethod
    def _canonical_payload(self) -> _CanonicalDict:
        raise NotImplementedError  # pragma: no cover

    @abstractmethod
    def _to_dsl(self) -> str:
        raise NotImplementedError  # pragma: no cover


@dataclass(frozen=True)
class FrameAssumption(BmcAssumption):
    """Assumption over frame predicates.

    :param kind: ``"always"`` for all frames or ``"at"`` for one frame.
    :type kind: str
    :param predicate: Condition predicate constrained by this assumption.
    :type predicate: BmcCondExpr
    :param frame: Required non-negative frame index for ``kind="at"``, defaults
        to ``None``.
    :type frame: Optional[int], optional

    Example::

        >>> from pyfcstm.bmc.ast import BoolLiteral
        >>> FrameAssumption("at", BoolLiteral("true"), frame=0).to_canonical()["frame"]
        0
    """

    _node_name: ClassVar[str] = "frame_assumption"

    kind: str
    predicate: BmcCondExpr
    frame: Optional[int] = None

    def __post_init__(self) -> None:
        _validate_choice(self.kind, _FRAME_ASSUMPTION_KINDS, "frame assumption kind")
        _require_condition(self.predicate, "predicate")
        frame = _normalize_frame(self.frame)
        if self.kind == "at" and frame is None:
            raise InvalidBmcQuery("frame is required for 'at' frame assumptions.")
        if self.kind == "always" and frame is not None:
            raise InvalidBmcQuery("frame is only valid for 'at' frame assumptions.")
        object.__setattr__(self, "frame", frame)

    def _canonical_payload(self) -> _CanonicalDict:
        return {
            "kind": self.kind,
            "frame": self.frame,
            "predicate": self.predicate.to_canonical(),
        }

    def _to_dsl(self) -> str:
        if self.kind == "always":
            return "assume always: %s;" % self.predicate
        return "assume at %d: %s;" % (self.frame, self.predicate)


@dataclass(frozen=True)
class EventAssumption(BmcAssumption):
    """Assumption over one event selection expression.

    :param event_path: Event path referenced by the query.
    :type event_path: str
    :param selector: Frame selector such as ``"*"``, ``0``, or ``"0..3"``.
        Defaults to ``"*"``.
    :type selector: int or str, optional
    :param expected: Whether the event is expected to be true, defaults to
        ``True``.
    :type expected: bool, optional

    Example::

        >>> EventAssumption("Root.Start", selector="0..2").to_canonical()["selector"]
        '0..2'
    """

    _node_name: ClassVar[str] = "event_assumption"

    event_path: str
    selector: _QuerySelector = "*"
    expected: bool = True

    def __post_init__(self) -> None:
        _require_non_empty_string(self.event_path, "event_path")
        selector = _normalize_selector(self.selector)
        if not isinstance(self.expected, bool):
            raise InvalidBmcQuery("expected must be a boolean value.")
        object.__setattr__(self, "selector", selector)

    def _canonical_payload(self) -> _CanonicalDict:
        return {
            "event_path": self.event_path,
            "selector": self.selector,
            "expected": self.expected,
        }

    def _to_dsl(self) -> str:
        return "assume event(%s, %s) == %s;" % (
            _quote_string(self.event_path),
            _selector_to_dsl(self.selector),
            _bool_to_dsl(self.expected),
        )


@dataclass(frozen=True)
class EventCardinalityAssumption(BmcAssumption):
    """Cardinality assumption over a group of event paths.

    :param kind: Cardinality kind, either ``"any"`` or ``"at_most_one"``.
    :type kind: str
    :param event_paths: Event paths for ``"at_most_one"``. ``"any"`` uses an
        empty tuple because it is equivalent to omitting the cardinality
        assumption, defaults to ``()``.  ``"at_most_one"`` paths must be unique.
    :type event_paths: Tuple[str, ...], optional

    Example::

        >>> EventCardinalityAssumption("at_most_one", ("A.Go", "A.Stop")).to_canonical()["kind"]
        'at_most_one'
        >>> EventCardinalityAssumption("any").to_canonical()["event_paths"]
        ()
    """

    _node_name: ClassVar[str] = "event_cardinality_assumption"

    kind: str
    event_paths: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        _validate_choice(self.kind, _EVENT_CARDINALITY_KINDS, "event cardinality kind")
        if isinstance(self.event_paths, str) or not isinstance(
            self.event_paths, (list, tuple)
        ):
            raise InvalidBmcQuery("event_paths must be a sequence of strings.")
        event_paths = tuple(self.event_paths)
        if self.kind == "at_most_one" and not event_paths:
            raise InvalidBmcQuery("event_paths must not be empty for at_most_one.")
        if self.kind == "any" and event_paths:
            raise InvalidBmcQuery("event_paths is only valid for at_most_one.")
        if not all(isinstance(path, str) and path for path in event_paths):
            raise InvalidBmcQuery("event_paths must contain non-empty strings.")
        if len(set(event_paths)) != len(event_paths):
            raise InvalidBmcQuery("event_paths must not contain duplicate paths.")
        object.__setattr__(self, "event_paths", event_paths)

    def _canonical_payload(self) -> _CanonicalDict:
        return {"kind": self.kind, "event_paths": self.event_paths}

    def _to_dsl(self) -> str:
        if self.kind == "any":
            return "assume events cardinality any;"
        lines = tuple(
            "%s%s"
            % (_quote_string(path), "," if index < len(self.event_paths) - 1 else "")
            for index, path in enumerate(self.event_paths)
        )
        return "assume events cardinality at_most_one {\n%s\n};" % _format_block(lines)


@dataclass(frozen=True)
class BmcProperty:
    """BMC query objective skeleton.

    :param kind: Property kind such as ``"reach"``, ``"forbid"``,
        ``"invariant"``, ``"must_reach"``, ``"exists_always"``,
        ``"response"``, or ``"cover"``.
    :type kind: str
    :param bound: Positive inclusive query bound.
    :type bound: int
    :param predicate: Predicate for single-body properties, including
        ``kind="cover"`` with a later binder-validated :class:`Case` predicate,
        defaults to ``None``.
    :type predicate: Optional[BmcCondExpr], optional
    :param trigger: Trigger predicate for ``kind="response"``, defaults to
        ``None``.
    :type trigger: Optional[BmcCondExpr], optional
    :param response: Response predicate for ``kind="response"``, defaults to
        ``None``.
    :type response: Optional[BmcCondExpr], optional
    :param within: Positive response window for ``kind="response"``, defaults
        to ``None``.
    :type within: Optional[int], optional

    Example::

        >>> from pyfcstm.bmc.ast import Active
        >>> BmcProperty("reach", 2, predicate=Active("Root.Done")).to_canonical()["bound"]
        2
    """

    _node_name: ClassVar[str] = "property"

    kind: str
    bound: int
    predicate: Optional[BmcCondExpr] = None
    trigger: Optional[BmcCondExpr] = None
    response: Optional[BmcCondExpr] = None
    within: Optional[int] = None

    def __post_init__(self) -> None:
        _validate_choice(self.kind, _PROPERTY_KINDS, "property kind")
        object.__setattr__(
            self, "bound", _normalize_positive_integer(self.bound, "bound")
        )
        if self.kind == "response":
            _require_condition(self.trigger, "response trigger")
            _require_condition(self.response, "response predicate")
            if self.within is None:
                raise InvalidBmcQuery("response window is required.")
            object.__setattr__(
                self,
                "within",
                _normalize_positive_integer(self.within, "response window"),
            )
            if self.predicate is not None:
                raise InvalidBmcQuery(
                    "response properties only accept trigger, response predicate, and window."
                )
            return

        _require_condition(self.predicate, "property predicate")
        if (
            self.trigger is not None
            or self.response is not None
            or self.within is not None
        ):
            raise InvalidBmcQuery("single-body properties only accept predicate.")

    def to_canonical(self) -> _CanonicalDict:
        """Return a stable canonical property dictionary.

        :return: Canonical property dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.ast import Active
            >>> BmcProperty("forbid", 1, predicate=Active("Root.Bad")).to_canonical()["kind"]
            'forbid'
        """
        return {
            "node": self._node_name,
            "kind": self.kind,
            "bound": self.bound,
            "predicate": _canonical_condition(self.predicate),
            "trigger": _canonical_condition(self.trigger),
            "response": _canonical_condition(self.response),
            "within": self.within,
        }

    def __str__(self) -> str:
        """Return the canonical ``.fbmcq`` DSL spelling for this property.

        :return: Check clause text.
        :rtype: str

        Example::

            >>> from pyfcstm.bmc.ast import Active
            >>> str(BmcProperty("reach", 2, predicate=Active("Root.Done")))
            'check reach <= 2: active("Root.Done");'
        """
        if self.kind == "response":
            lines = (
                "trigger %s" % self.trigger,
                "-> within %d %s" % (self.within, self.response),
            )
            return "check response <= %d:\n%s;" % (self.bound, _format_block(lines))
        return "check %s <= %d: %s;" % (self.kind, self.bound, self.predicate)


@dataclass(frozen=True)
class BmcQuery:
    """Complete FCSTM BMC query root object.

    :param property: Query objective.
    :type property: BmcProperty
    :param initial: Initial frame specification, defaults to
        :class:`InitialSpec` with ``mode="cold"``.
    :type initial: InitialSpec, optional
    :param assumptions: Tuple of environment assumptions, defaults to empty.
    :type assumptions: Tuple[BmcAssumption, ...], optional

    Example::

        >>> from pyfcstm.bmc.ast import Active
        >>> query = BmcQuery(property=BmcProperty("reach", 1, predicate=Active("Root.Done")))
        >>> query.initial.mode
        'cold'
    """

    _node_name: ClassVar[str] = "bmc_query"

    property: BmcProperty
    initial: InitialSpec = field(default_factory=InitialSpec)
    assumptions: Tuple[BmcAssumption, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.property, BmcProperty):
            raise InvalidBmcQuery("property must be BmcProperty.")
        if not isinstance(self.initial, InitialSpec):
            raise InvalidBmcQuery("initial must be InitialSpec.")
        if not isinstance(self.assumptions, (list, tuple)):
            raise InvalidBmcQuery(
                "assumptions must be a sequence of BmcAssumption objects."
            )
        assumptions = tuple(self.assumptions)
        if not all(isinstance(assumption, BmcAssumption) for assumption in assumptions):
            raise InvalidBmcQuery("assumptions must contain BmcAssumption objects.")
        object.__setattr__(self, "assumptions", assumptions)

    def to_canonical(self) -> _CanonicalDict:
        """Return a stable canonical query dictionary.

        :return: Canonical query dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.ast import Active
            >>> query = BmcQuery(property=BmcProperty("reach", 1, predicate=Active("Root.Done")))
            >>> query.to_canonical()["node"]
            'bmc_query'
        """
        return {
            "node": self._node_name,
            "initial": self.initial.to_canonical(),
            "assumptions": tuple(
                assumption.to_canonical() for assumption in self.assumptions
            ),
            "property": self.property.to_canonical(),
        }

    def __str__(self) -> str:
        """Return the canonical ``.fbmcq`` DSL spelling for this query.

        :return: Complete query file text.
        :rtype: str

        Example::

            >>> from pyfcstm.bmc.ast import Active
            >>> query = BmcQuery(property=BmcProperty("reach", 1, predicate=Active("Root.Done")))
            >>> str(query).splitlines()[0]
            'init cold;'
        """
        clauses = [str(self.initial)]
        clauses.extend(str(assumption) for assumption in self.assumptions)
        clauses.append(str(self.property))
        return "\n\n".join(clauses)


__all__ = [
    "InitialSpec",
    "BmcAssumption",
    "FrameAssumption",
    "EventAssumption",
    "EventCardinalityAssumption",
    "BmcProperty",
    "BmcQuery",
]

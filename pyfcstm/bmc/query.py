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
  binder, and compiler parity tests.  Collection fields in canonical output use
  JSON-stable ``list`` values even when the frozen dataclass stores them as
  tuples internally.

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
import re
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
_ID_RE = re.compile(r"^[A-Za-z_][A-Za-z0-9_]*$")
_FBMCQ_BARE_VAR_RESERVED = {
    "init",
    "cold",
    "terminated",
    "state",
    "where",
    "havoc",
    "assume",
    "always",
    "at",
    "event",
    "events",
    "cardinality",
    "any",
    "at_most_one",
    "check",
    "reach",
    "forbid",
    "invariant",
    "must_reach",
    "exists_always",
    "response",
    "cover",
    "trigger",
    "within",
    "var",
    "cycle",
    "active",
    "case",
    "called",
    "current",
    "pi",
    "E",
    "tau",
    "and",
    "or",
    "not",
    "implies",
    "iff",
    "xor",
    "true",
    "false",
    "True",
    "False",
    "TRUE",
    "FALSE",
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
    """Normalize event-assumption cycle selectors.

    Decimal strings are accepted as user-facing convenience and normalized to
    integers.  Inclusive ranges with leading zeros are normalized to canonical
    decimal range text, and a degenerate range such as ``"03..03"`` collapses
    to integer ``3``.  The event atom's ``"current"`` selector is intentionally
    not accepted here because event assumptions quantify over concrete cycles
    or ranges.
    """
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


def _is_safe_bare_init_var_ref(name: str) -> bool:
    return bool(_ID_RE.fullmatch(name)) and name not in _FBMCQ_BARE_VAR_RESERVED


def _init_var_ref_to_dsl(name: str) -> str:
    if _is_safe_bare_init_var_ref(name):
        return name
    return _quote_string(name)


@dataclass(frozen=True)
class InitialVariablePolicy:
    """Initial-frame persistent-variable initializer policy.

    The policy controls which FCSTM declaration initializers are skipped while
    constructing ``F_0``.  A skipped variable remains a free initial-frame
    symbol that can still be constrained by the surrounding initial ``where``
    predicate.

    :param havoc_all: Whether ``havoc *`` skips every persistent-variable
        initializer, defaults to ``False``.
    :type havoc_all: bool, optional
    :param havoc_variables: Specific variable names skipped by
        ``havoc { ... }``, defaults to ``()``.
    :type havoc_variables: Tuple[str, ...], optional

    Example::

        >>> InitialVariablePolicy(havoc_variables=("x",)).to_canonical()["havoc_variables"]
        ['x']
        >>> str(InitialVariablePolicy(havoc_all=True))
        'havoc *'
    """

    _node_name: ClassVar[str] = "initial_variable_policy"

    havoc_all: bool = False
    havoc_variables: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.havoc_all, bool):
            raise InvalidBmcQuery("havoc_all must be a boolean value.")
        if isinstance(self.havoc_variables, str) or not isinstance(
            self.havoc_variables, (list, tuple)
        ):
            raise InvalidBmcQuery("havoc_variables must be a sequence of strings.")
        variables = tuple(self.havoc_variables)
        if not all(isinstance(name, str) and name for name in variables):
            raise InvalidBmcQuery("havoc_variables must contain non-empty strings.")
        if len(set(variables)) != len(variables):
            raise InvalidBmcQuery("havoc_variables must not contain duplicate names.")
        if self.havoc_all and variables:
            raise InvalidBmcQuery("havoc_all cannot be combined with havoc_variables.")
        object.__setattr__(self, "havoc_variables", variables)

    @property
    def is_empty(self) -> bool:
        """Return whether the policy leaves all declaration initializers intact.

        :return: ``True`` when no ``havoc`` clause is present.
        :rtype: bool

        Example::

            >>> InitialVariablePolicy().is_empty
            True
        """
        return not self.havoc_all and not self.havoc_variables

    def havoc_names(self, domain_or_names: object) -> Tuple[str, ...]:
        """Return variable names skipped by this policy.

        :param domain_or_names: Either a BMC domain-like object with a
            ``variables`` attribute or an iterable of variable names.
        :type domain_or_names: object
        :return: Names whose declaration initializers are skipped.
        :rtype: Tuple[str, ...]
        :raises pyfcstm.bmc.errors.InvalidBmcQuery: If ``domain_or_names`` does
            not provide names needed by ``havoc *``.

        Example::

            >>> InitialVariablePolicy(havoc_variables=("x",)).havoc_names(("x", "y"))
            ('x',)
        """
        if not self.havoc_all:
            return self.havoc_variables
        if hasattr(domain_or_names, "variables"):
            return tuple(item.name for item in domain_or_names.variables)
        try:
            names = tuple(domain_or_names)  # type: ignore[arg-type]
        except TypeError as err:
            # TypeError: non-iterable domain_or_names cannot expand wildcard
            # havoc; this is a public API misuse rather than a solver failure.
            raise InvalidBmcQuery(
                "havoc_names needs a domain or variable-name iterable for havoc *."
            ) from err
        if not all(isinstance(name, str) and name for name in names):
            raise InvalidBmcQuery(
                "havoc_names variable-name iterable must contain non-empty strings."
            )
        return names

    def to_canonical(self) -> _CanonicalDict:
        """Return a stable canonical initial-variable-policy dictionary.

        :return: Canonical policy dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> InitialVariablePolicy(havoc_all=True).to_canonical()["havoc_all"]
            True
        """
        return {
            "node": self._node_name,
            "havoc_all": self.havoc_all,
            "havoc_variables": list(self.havoc_variables),
        }

    def __str__(self) -> str:
        """Return the canonical ``havoc`` clause text.

        :return: ``havoc`` clause text, or ``""`` for the empty policy.
        :rtype: str

        Example::

            >>> str(InitialVariablePolicy())
            ''
            >>> str(InitialVariablePolicy(havoc_variables=("x", "event")))
            'havoc { x, "event" }'
        """
        if self.havoc_all:
            return "havoc *"
        if not self.havoc_variables:
            return ""
        refs = ", ".join(_init_var_ref_to_dsl(name) for name in self.havoc_variables)
        return "havoc { %s }" % refs


@dataclass(frozen=True)
class InitialSpec:
    """Initial BMC frame specification.

    :param mode: Initial mode: ``"cold"``, ``"terminated"``, or ``"state"``.
        Defaults to ``"cold"``.
    :type mode: str, optional
    :param state_path: State path for ``mode="state"``, defaults to ``None``.
    :type state_path: Optional[str], optional
    :param predicate: Optional initial-state predicate that contributes only to
        the initial condition, defaults to ``None``.  The predicate is valid
        for all modes and renders as a ``where`` clause, for example
        ``init cold where active("Root.A");``.
    :type predicate: Optional[BmcCondExpr], optional
    :param variable_policy: Initial-frame variable initializer policy, defaults
        to an empty policy that keeps all declaration initializers.
    :type variable_policy: InitialVariablePolicy, optional

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
    variable_policy: InitialVariablePolicy = field(
        default_factory=InitialVariablePolicy
    )

    def __post_init__(self) -> None:
        _validate_choice(self.mode, _INITIAL_MODES, "initial mode")
        if self.mode == "state":
            _require_non_empty_string(self.state_path, "state_path")
        if self.mode != "state" and self.state_path is not None:
            raise InvalidBmcQuery(
                "state_path is only valid when initial mode is 'state'."
            )
        if self.predicate is not None:
            _require_condition(self.predicate, "predicate")
        if not isinstance(self.variable_policy, InitialVariablePolicy):
            raise InvalidBmcQuery("variable_policy must be InitialVariablePolicy.")

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
            "variable_policy": self.variable_policy.to_canonical(),
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
        clauses = ["init", target]
        policy_text = str(self.variable_policy)
        if policy_text:
            clauses.append(policy_text)
        if self.predicate is not None:
            clauses.extend(("where", str(self.predicate)))
        return "%s;" % " ".join(clauses)


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
        empty tuple internally because it is equivalent to omitting the
        cardinality assumption, defaults to ``()``.  ``"at_most_one"`` paths
        must be unique.
    :type event_paths: Tuple[str, ...], optional

    Example::

        >>> EventCardinalityAssumption("at_most_one", ("A.Go", "A.Stop")).to_canonical()["kind"]
        'at_most_one'
        >>> EventCardinalityAssumption("any").to_canonical()["event_paths"]
        []
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
        return {"kind": self.kind, "event_paths": list(self.event_paths)}

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
        Canonical output renders assumptions as a JSON-stable list.
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
            "assumptions": [
                assumption.to_canonical() for assumption in self.assumptions
            ],
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
    "InitialVariablePolicy",
    "InitialSpec",
    "BmcAssumption",
    "FrameAssumption",
    "EventAssumption",
    "EventCardinalityAssumption",
    "BmcProperty",
    "BmcQuery",
]

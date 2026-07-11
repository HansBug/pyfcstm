"""Semantic binding for parser-independent FCSTM BMC queries.

The binding layer sits between the ``.fbmcq`` parser and later BMC engine or
solver lowering code.  It validates query-context rules that are deliberately
not encoded in the grammar, optionally resolves model paths through a
:class:`pyfcstm.bmc.domain.BmcDomain`, and returns a stable, JSON-friendly
binding snapshot.

Design contracts:

* Structure-only binding does not import :mod:`pyfcstm.model`,
  :mod:`pyfcstm.solver`, :mod:`pyfcstm.verify`, or ``z3``.
* Parser errors remain :class:`pyfcstm.bmc.errors.BmcQueryParseError`; semantic
  binding errors use :class:`pyfcstm.bmc.errors.InvalidBmcQuery` with a
  :class:`BmcBindingDiagnostic` attached.
* Bound objects preserve the original parser AST and expose
  :meth:`to_canonical` for golden tests and future engine handoff.
* This binding layer keeps frame-local predicates conservative: omitted and
  ``current`` frame selectors are accepted, while explicit integer frame
  selectors are rejected outside event assumptions.

The module contains:

* :class:`BmcBindingDiagnostic` - Stable binding diagnostic.
* :class:`BoundReference` - Model reference discovered during binding.
* :class:`BoundInitialSpec`, :class:`BoundAssumption`,
  :class:`BoundProperty`, and :class:`BoundBmcQuery` - Normalized bound query
  snapshots.
* :func:`bind_bmc_query_structure` - Query-only semantic binding.
* :func:`bind_bmc_query` - Optional model/domain-aware binding.

Example::

    >>> from pyfcstm.bmc.parse import parse_bmc_query
    >>> from pyfcstm.bmc.binding import bind_bmc_query_structure
    >>> bound = bind_bmc_query_structure(parse_bmc_query('check reach <= 1: true;'))
    >>> bound.property.kind
    'reach'
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional, Sequence, Tuple

from .ast import (
    Active,
    BmcCondExpr,
    BmcNumExpr,
    BoolLiteral,
    CallCount,
    CallFilter,
    CallStepSelector,
    Called,
    Case,
    CondBinaryOp,
    CondConditionalOp,
    CondUnaryOp,
    Cycle,
    Event,
    FloatLiteral,
    FrameVar,
    IntLiteral,
    MathConst,
    NameRef,
    NumBinaryOp,
    NumConditionalOp,
    NumUnaryOp,
    NumericComparison,
    Terminated,
    UFuncCall,
)
from .errors import InvalidBmcDomain, InvalidBmcQuery
from .query import (
    BmcAssumption,
    BmcProperty,
    BmcQuery,
    EventAssumption,
    EventCardinalityAssumption,
    FrameAssumption,
    InitialVariablePolicy,
    InitialSpec,
)

_CanonicalDict = Dict[str, Any]
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
_RESERVED_STATE_PATHS = {"$STATE_INIT", "$STATE_TERMINATE"}
_CALL_RUNTIME_ROLES = {
    "state_enter",
    "state_exit",
    "leaf_during",
    "plain_during_before",
    "plain_during_after",
    "aspect_during_before",
    "aspect_during_after",
    "transition_effect",
}


def _is_non_empty_text(value: object) -> bool:
    return isinstance(value, str) and bool(value.strip())


def _require_query(query: object) -> BmcQuery:
    if not isinstance(query, BmcQuery):
        _raise_binding_error(
            "query_type",
            "query",
            "query must be a BmcQuery object.",
        )
    _validate_query_shape(query)
    return query


@dataclass(frozen=True)
class BmcBindingDiagnostic:
    """Stable diagnostic emitted by the BMC query binder.

    :param code: Stable machine-readable diagnostic code.
    :type code: str
    :param path: Semantic node path such as ``"property.predicate"``.
    :type path: str
    :param message: Human-readable diagnostic message.
    :type message: str

    Example::

        >>> diag = BmcBindingDiagnostic('bad_context', 'property', 'not allowed')
        >>> diag.to_canonical()['code']
        'bad_context'
    """

    code: str
    path: str
    message: str

    def __post_init__(self) -> None:
        if not _is_non_empty_text(self.code):
            raise InvalidBmcQuery("diagnostic code must be a non-empty string.")
        if not _is_non_empty_text(self.path):
            raise InvalidBmcQuery("diagnostic path must be a non-empty string.")
        if not _is_non_empty_text(self.message):
            raise InvalidBmcQuery("diagnostic message must be a non-empty string.")

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable diagnostic dictionary.

        :return: Canonical diagnostic dictionary.
        :rtype: Dict[str, str]

        Example::

            >>> BmcBindingDiagnostic('code', 'path', 'message').to_canonical()['path']
            'path'
        """
        return {"code": self.code, "path": self.path, "message": self.message}

    def __str__(self) -> str:
        """Return a compact diagnostic string.

        :return: Human-readable diagnostic summary.
        :rtype: str

        Example::

            >>> str(BmcBindingDiagnostic('code', 'path', 'message'))
            'code at path: message'
        """
        return f"{self.code} at {self.path}: {self.message}"


@dataclass(frozen=True)
class BoundReference:
    """Reference discovered and optionally resolved during query binding.

    :param kind: Reference category: ``"state"``, ``"event"``, or
        ``"variable"``.
    :type kind: str
    :param name: Query-visible name or path.
    :type name: str
    :param path: Semantic expression path where the reference was found.
    :type path: str
    :param spelling: Source spelling family such as ``"active"``,
        ``"event"``, ``"bare"``, or ``"var_call"``.
    :type spelling: str
    :param resolved_id: Domain id when model/domain-aware binding is used,
        defaults to ``None``.
    :type resolved_id: int, optional
    :param declared_type: Variable declared type for resolved variable refs,
        defaults to ``None``.
    :type declared_type: str, optional

    Example::

        >>> BoundReference('variable', 'x', 'property.predicate', 'bare').to_canonical()['name']
        'x'
    """

    kind: str
    name: str
    path: str
    spelling: str
    resolved_id: Optional[int] = None
    declared_type: Optional[str] = None

    def __post_init__(self) -> None:
        for field_name in ("kind", "name", "path", "spelling"):
            value = getattr(self, field_name)
            if not _is_non_empty_text(value):
                raise InvalidBmcQuery(
                    f"BoundReference {field_name} must be a non-empty string."
                )
        if self.kind not in {"state", "event", "variable"}:
            raise InvalidBmcQuery(f"Unsupported bound reference kind: {self.kind!r}.")
        if self.resolved_id is not None and (
            isinstance(self.resolved_id, bool) or not isinstance(self.resolved_id, int)
        ):
            raise InvalidBmcQuery("resolved_id must be an integer or None.")
        if self.declared_type is not None and not _is_non_empty_text(
            self.declared_type
        ):
            raise InvalidBmcQuery("declared_type must be a string or None.")

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable reference dictionary.

        :return: Canonical reference dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> BoundReference('state', 'Root', 'initial', 'state_path').to_canonical()['kind']
            'state'
        """
        return {
            "node": "bound_reference",
            "kind": self.kind,
            "name": self.name,
            "path": self.path,
            "spelling": self.spelling,
            "resolved_id": self.resolved_id,
            "declared_type": self.declared_type,
        }


@dataclass(frozen=True)
class BoundInitialSpec:
    """Bound initial-frame query specification.

    :param source: Original parser-independent initial spec.
    :type source: InitialSpec
    :param resolved_state_id: Domain state id for ``mode="state"`` when
        resolved, defaults to ``None``.
    :type resolved_state_id: int, optional
    :param resolved_havoc_variables: Domain-order variable names whose
        declaration initializers are skipped, or ``None`` when no domain was
        supplied, defaults to ``None``.
    :type resolved_havoc_variables: Tuple[str, ...], optional

    Example::

        >>> BoundInitialSpec(InitialSpec()).to_canonical()['mode']
        'cold'
    """

    source: InitialSpec
    resolved_state_id: Optional[int] = None
    resolved_havoc_variables: Optional[Tuple[str, ...]] = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, InitialSpec):
            raise InvalidBmcQuery("source must be InitialSpec.")
        if self.resolved_state_id is not None and (
            isinstance(self.resolved_state_id, bool)
            or not isinstance(self.resolved_state_id, int)
        ):
            raise InvalidBmcQuery("resolved_state_id must be an integer or None.")
        if self.resolved_havoc_variables is not None:
            if isinstance(self.resolved_havoc_variables, str) or not isinstance(
                self.resolved_havoc_variables, (list, tuple)
            ):
                raise InvalidBmcQuery(
                    "resolved_havoc_variables must be a sequence or None."
                )
            names = tuple(self.resolved_havoc_variables)
            if not all(isinstance(name, str) and name for name in names):
                raise InvalidBmcQuery(
                    "resolved_havoc_variables must contain non-empty strings."
                )
            if len(set(names)) != len(names):
                raise InvalidBmcQuery(
                    "resolved_havoc_variables must not contain duplicate names."
                )
            object.__setattr__(self, "resolved_havoc_variables", names)

    @property
    def mode(self) -> str:
        """Return the initial mode.

        :return: Initial mode string.
        :rtype: str
        """
        return self.source.mode

    @property
    def predicate(self) -> Optional[BmcCondExpr]:
        """Return the optional initial predicate.

        :return: Initial predicate or ``None``.
        :rtype: Optional[BmcCondExpr]
        """
        return self.source.predicate

    @property
    def variable_policy(self) -> InitialVariablePolicy:
        """Return the source initial variable policy.

        :return: Initial variable policy.
        :rtype: pyfcstm.bmc.query.InitialVariablePolicy
        """
        return self.source.variable_policy

    def havoc_names(self, domain: object) -> Tuple[str, ...]:
        """Return domain-resolved initial ``havoc`` variable names.

        :param domain: BMC domain used when a wildcard policy must be expanded.
        :type domain: object
        :return: Variable names skipped by the initial variable policy.
        :rtype: Tuple[str, ...]

        Example::

            >>> BoundInitialSpec(InitialSpec()).havoc_names(())
            ()
        """
        if self.resolved_havoc_variables is not None:
            return self.resolved_havoc_variables
        return self.source.variable_policy.havoc_names(domain)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable bound initial-spec dictionary.

        :return: Canonical bound initial specification.
        :rtype: Dict[str, object]

        Example::

            >>> BoundInitialSpec(InitialSpec()).to_canonical()['node']
            'bound_initial_spec'
        """
        result = self.source.to_canonical()
        result.update(
            {
                "node": "bound_initial_spec",
                "resolved_state_id": self.resolved_state_id,
                "resolved_havoc_variables": (
                    None
                    if self.resolved_havoc_variables is None
                    else list(self.resolved_havoc_variables)
                ),
            }
        )
        return result


@dataclass(frozen=True)
class BoundAssumption:
    """Bound query assumption.

    :param source: Original assumption object.
    :type source: BmcAssumption
    :param kind: Bound assumption category.
    :type kind: str
    :param frame: Frame index for frame assumptions, defaults to ``None``.
    :type frame: int, optional
    :param cycles: Event cycles selected by event assumptions.
    :type cycles: Tuple[int, ...], optional
    :param resolved_event_ids: Resolved event ids for event assumptions,
        defaults to ``()``.
    :type resolved_event_ids: Tuple[int, ...], optional

    Example::

        >>> from pyfcstm.bmc.ast import BoolLiteral
        >>> src = FrameAssumption('always', BoolLiteral('true'))
        >>> BoundAssumption(src, 'frame').to_canonical()['kind']
        'frame'
    """

    source: BmcAssumption
    kind: str
    frame: Optional[int] = None
    cycles: Tuple[int, ...] = ()
    resolved_event_ids: Tuple[int, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source, BmcAssumption):
            raise InvalidBmcQuery("source must be BmcAssumption.")
        if self.kind not in {"frame", "event", "event_cardinality"}:
            raise InvalidBmcQuery(f"Unsupported bound assumption kind: {self.kind!r}.")
        if self.frame is not None and (
            isinstance(self.frame, bool) or not isinstance(self.frame, int)
        ):
            raise InvalidBmcQuery("frame must be an integer or None.")
        if self.frame is not None and self.frame < 0:
            raise InvalidBmcQuery("frame must be non-negative or None.")
        for field_name in ("cycles", "resolved_event_ids"):
            value = getattr(self, field_name)
            if not isinstance(value, (list, tuple)):
                raise InvalidBmcQuery(f"{field_name} must be a sequence.")
            normalized = tuple(value)
            if not all(
                not isinstance(item, bool) and isinstance(item, int)
                for item in normalized
            ):
                raise InvalidBmcQuery(f"{field_name} must contain integers.")
            object.__setattr__(self, field_name, normalized)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable bound assumption dictionary.

        :return: Canonical bound assumption.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.ast import BoolLiteral
            >>> src = FrameAssumption('always', BoolLiteral('true'))
            >>> BoundAssumption(src, 'frame').to_canonical()['node']
            'bound_assumption'
        """
        return {
            "node": "bound_assumption",
            "kind": self.kind,
            "source": self.source.to_canonical(),
            "frame": self.frame,
            "cycles": list(self.cycles),
            "resolved_event_ids": list(self.resolved_event_ids),
        }


@dataclass(frozen=True)
class BoundProperty:
    """Bound BMC query property.

    :param source: Original property object.
    :type source: BmcProperty
    :param case_label: Cover case label when ``kind="cover"``, defaults to
        ``None``.
    :type case_label: str, optional

    Example::

        >>> from pyfcstm.bmc.ast import BoolLiteral
        >>> prop = BmcProperty('reach', 1, predicate=BoolLiteral('true'))
        >>> BoundProperty(prop).bound
        1
    """

    source: BmcProperty
    case_label: Optional[str] = None

    def __post_init__(self) -> None:
        if not isinstance(self.source, BmcProperty):
            raise InvalidBmcQuery("source must be BmcProperty.")
        if self.source.kind not in _PROPERTY_KINDS:
            raise InvalidBmcQuery(
                f"Unsupported bound property kind: {self.source.kind!r}."
            )
        if self.case_label is not None and not _is_non_empty_text(self.case_label):
            raise InvalidBmcQuery("case_label must be a non-empty string or None.")
        if self.case_label is not None and self.source.kind != "cover":
            raise InvalidBmcQuery("case_label is only valid for cover properties.")

    @property
    def kind(self) -> str:
        """Return the property kind.

        :return: Property kind.
        :rtype: str
        """
        return self.source.kind

    @property
    def bound(self) -> int:
        """Return the positive query bound.

        :return: Query bound.
        :rtype: int
        """
        return self.source.bound

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable bound property dictionary.

        :return: Canonical bound property.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.ast import BoolLiteral
            >>> prop = BmcProperty('reach', 1, predicate=BoolLiteral('true'))
            >>> BoundProperty(prop).to_canonical()['kind']
            'reach'
        """
        result = self.source.to_canonical()
        result.update({"node": "bound_property", "case_label": self.case_label})
        return result


@dataclass(frozen=True)
class BoundBmcQuery:
    """Complete semantically bound BMC query snapshot.

    :param query: Original parser-independent query.
    :type query: BmcQuery
    :param initial: Bound initial specification.
    :type initial: BoundInitialSpec
    :param assumptions: Bound assumptions.
    :type assumptions: Tuple[BoundAssumption, ...]
    :param property: Bound property.
    :type property: BoundProperty
    :param references: References found while binding, defaults to ``()``.
    :type references: Tuple[BoundReference, ...], optional

    Example::

        >>> from pyfcstm.bmc.ast import BoolLiteral
        >>> prop = BmcProperty('reach', 1, predicate=BoolLiteral('true'))
        >>> bound = BoundBmcQuery(BmcQuery(property=prop), BoundInitialSpec(InitialSpec()), (), BoundProperty(prop))
        >>> bound.to_canonical()['node']
        'bound_bmc_query'
    """

    query: BmcQuery
    initial: BoundInitialSpec
    assumptions: Tuple[BoundAssumption, ...]
    property: BoundProperty
    references: Tuple[BoundReference, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.query, BmcQuery):
            raise InvalidBmcQuery("query must be BmcQuery.")
        if not isinstance(self.initial, BoundInitialSpec):
            raise InvalidBmcQuery("initial must be BoundInitialSpec.")
        if not isinstance(self.property, BoundProperty):
            raise InvalidBmcQuery("property must be BoundProperty.")
        self._normalize_sequence("assumptions", self.assumptions, BoundAssumption)
        self._normalize_sequence("references", self.references, BoundReference)

    def _normalize_sequence(
        self, field_name: str, value: Sequence[Any], item_type: type
    ) -> None:
        if not isinstance(value, (list, tuple)):
            raise InvalidBmcQuery(f"{field_name} must be a sequence.")
        items = tuple(value)
        if not all(isinstance(item, item_type) for item in items):
            raise InvalidBmcQuery(
                f"{field_name} must contain {item_type.__name__} objects."
            )
        object.__setattr__(self, field_name, items)

    def to_ast_node(self) -> BmcQuery:
        """Return the parser-independent query AST bound by this snapshot.

        Binding metadata such as resolved ids and declared variable types is
        intentionally not represented in the returned query object.  Callers can
        render the returned :class:`pyfcstm.bmc.query.BmcQuery` back to
        canonical ``.fbmcq`` text, parse it again, and re-bind it with the same
        model or domain when binding metadata must be reproduced.

        :return: Original parser-independent BMC query object.
        :rtype: pyfcstm.bmc.query.BmcQuery

        Example::

            >>> from pyfcstm.bmc.ast import BoolLiteral
            >>> prop = BmcProperty('reach', 1, predicate=BoolLiteral('true'))
            >>> query = BmcQuery(property=prop)
            >>> bound = BoundBmcQuery(query, BoundInitialSpec(InitialSpec()), (), BoundProperty(prop))
            >>> bound.to_ast_node() is query
            True
        """
        return self.query

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable bound query dictionary.

        :return: Canonical bound query.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.ast import BoolLiteral
            >>> prop = BmcProperty('reach', 1, predicate=BoolLiteral('true'))
            >>> bound = BoundBmcQuery(BmcQuery(property=prop), BoundInitialSpec(InitialSpec()), (), BoundProperty(prop))
            >>> bound.to_canonical()['property']['bound']
            1
        """
        return {
            "node": "bound_bmc_query",
            "query": self.query.to_canonical(),
            "initial": self.initial.to_canonical(),
            "assumptions": [item.to_canonical() for item in self.assumptions],
            "property": self.property.to_canonical(),
            "references": [item.to_canonical() for item in self.references],
        }


def _raise_binding_error(code: str, path: str, message: str) -> None:
    diagnostic = BmcBindingDiagnostic(code, path, message)
    error = InvalidBmcQuery(str(diagnostic))
    error.diagnostic = diagnostic
    raise error


def _require_non_empty_field(value: object, path: str, field_name: str) -> None:
    if not _is_non_empty_text(value):
        _raise_binding_error(
            "query_shape",
            path,
            f"{field_name} must be a non-empty string.",
        )


def _require_condition_field(value: object, path: str, field_name: str) -> None:
    if not isinstance(value, BmcCondExpr):
        _raise_binding_error(
            "query_shape",
            path,
            f"{field_name} must be a BmcCondExpr object.",
        )


def _require_positive_integer_field(value: object, path: str, field_name: str) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value <= 0:
        _raise_binding_error(
            "query_shape",
            path,
            f"{field_name} must be a positive integer.",
        )


def _require_non_negative_integer_field(
    value: object, path: str, field_name: str
) -> None:
    if isinstance(value, bool) or not isinstance(value, int) or value < 0:
        _raise_binding_error(
            "query_shape",
            path,
            f"{field_name} must be a non-negative integer.",
        )


def _validate_initial_shape(initial: object) -> None:
    if not isinstance(initial, InitialSpec):
        _raise_binding_error(
            "query_shape",
            "initial",
            "initial must be an InitialSpec object.",
        )
    if initial.mode not in _INITIAL_MODES:
        _raise_binding_error(
            "query_shape",
            "initial.mode",
            f"Unsupported initial mode: {initial.mode!r}.",
        )
    if initial.mode == "state":
        _require_non_empty_field(initial.state_path, "initial.state_path", "state_path")
    elif initial.state_path is not None:
        _raise_binding_error(
            "query_shape",
            "initial.state_path",
            "state_path is only valid when initial mode is 'state'.",
        )
    if initial.predicate is not None:
        _require_condition_field(
            initial.predicate, "initial.predicate", "initial predicate"
        )
    policy = initial.variable_policy
    if not isinstance(policy, InitialVariablePolicy):
        _raise_binding_error(
            "query_shape",
            "initial.variable_policy",
            "variable_policy must be InitialVariablePolicy.",
        )
    if not isinstance(policy.havoc_all, bool):
        _raise_binding_error(
            "query_shape",
            "initial.variable_policy.havoc_all",
            "havoc_all must be a boolean value.",
        )
    if isinstance(policy.havoc_variables, str) or not isinstance(
        policy.havoc_variables, (list, tuple)
    ):
        _raise_binding_error(
            "query_shape",
            "initial.variable_policy.havoc_variables",
            "havoc_variables must be a sequence of strings.",
        )
    havoc_variables = tuple(policy.havoc_variables)
    if policy.havoc_all and havoc_variables:
        _raise_binding_error(
            "query_shape",
            "initial.variable_policy",
            "havoc_all cannot be combined with havoc_variables.",
        )
    seen = set()
    for index, name in enumerate(havoc_variables):
        if not _is_non_empty_text(name):
            _raise_binding_error(
                "query_shape",
                f"initial.variable_policy.havoc_variables[{index}]",
                "havoc variable name must be a non-empty string.",
            )
        if name in seen:
            _raise_binding_error(
                "duplicate_havoc_variable",
                f"initial.variable_policy.havoc_variables[{index}]",
                "initial havoc variables must not contain duplicate names.",
            )
        seen.add(name)


def _validate_frame_assumption_shape(assumption: FrameAssumption, path: str) -> None:
    if assumption.kind not in _FRAME_ASSUMPTION_KINDS:
        _raise_binding_error(
            "query_shape",
            path + ".kind",
            f"Unsupported frame assumption kind: {assumption.kind!r}.",
        )
    _require_condition_field(assumption.predicate, path + ".predicate", "predicate")
    if assumption.kind == "at":
        _require_non_negative_integer_field(assumption.frame, path + ".frame", "frame")
    elif assumption.frame is not None:
        _raise_binding_error(
            "query_shape",
            path + ".frame",
            "frame is only valid for 'at' frame assumptions.",
        )


def _validate_event_assumption_shape(assumption: EventAssumption, path: str) -> None:
    _require_non_empty_field(assumption.event_path, path + ".event_path", "event_path")
    selector = assumption.selector
    if selector != "*" and not (
        isinstance(selector, int) and not isinstance(selector, bool) and selector >= 0
    ):
        if not (
            isinstance(selector, str)
            and ".." in selector
            and len(selector.split("..")) == 2
            and all(_is_ascii_decimal(part) for part in selector.split(".."))
        ):
            _raise_binding_error(
                "event_selector_invalid",
                path + ".selector",
                "event assumption selector must be '*', an integer, or an inclusive range.",
            )
    if not isinstance(assumption.expected, bool):
        _raise_binding_error(
            "query_shape",
            path + ".expected",
            "expected must be a boolean value.",
        )


def _validate_cardinality_assumption_shape(
    assumption: EventCardinalityAssumption, path: str
) -> None:
    if assumption.kind not in _EVENT_CARDINALITY_KINDS:
        _raise_binding_error(
            "query_shape",
            path + ".kind",
            f"Unsupported event cardinality kind: {assumption.kind!r}.",
        )
    if isinstance(assumption.event_paths, str) or not isinstance(
        assumption.event_paths, (list, tuple)
    ):
        _raise_binding_error(
            "query_shape",
            path + ".event_paths",
            "event_paths must be a sequence of strings.",
        )
    event_paths = tuple(assumption.event_paths)
    if assumption.kind == "at_most_one" and not event_paths:
        _raise_binding_error(
            "query_shape",
            path + ".event_paths",
            "event_paths must not be empty for at_most_one.",
        )
    if assumption.kind == "any" and event_paths:
        _raise_binding_error(
            "query_shape",
            path + ".event_paths",
            "event_paths is only valid for at_most_one.",
        )
    for event_index, event_path in enumerate(event_paths):
        _require_non_empty_field(
            event_path,
            f"{path}.event_paths[{event_index}]",
            "event path",
        )
    if len(set(event_paths)) != len(event_paths):
        _raise_binding_error(
            "query_shape",
            path + ".event_paths",
            "event_paths must not contain duplicate paths.",
        )


def _validate_assumption_shape(assumption: object, path: str) -> None:
    if isinstance(assumption, FrameAssumption):
        _validate_frame_assumption_shape(assumption, path)
        return
    if isinstance(assumption, EventAssumption):
        _validate_event_assumption_shape(assumption, path)
        return
    if isinstance(assumption, EventCardinalityAssumption):
        _validate_cardinality_assumption_shape(assumption, path)
        return
    _raise_binding_error(
        "assumption_type",
        path,
        f"Unsupported assumption object: {type(assumption).__name__}.",
    )


def _validate_property_shape(property_node: object) -> None:
    if not isinstance(property_node, BmcProperty):
        _raise_binding_error(
            "query_shape",
            "property",
            "property must be a BmcProperty object.",
        )
    if property_node.kind not in _PROPERTY_KINDS:
        _raise_binding_error(
            "query_shape",
            "property.kind",
            f"Unsupported property kind: {property_node.kind!r}.",
        )
    _require_positive_integer_field(property_node.bound, "property.bound", "bound")
    if property_node.kind == "response":
        _require_condition_field(
            property_node.trigger, "property.trigger", "response trigger"
        )
        _require_condition_field(
            property_node.response, "property.response", "response predicate"
        )
        _require_positive_integer_field(
            property_node.within, "property.within", "response window"
        )
        if property_node.predicate is not None:
            _raise_binding_error(
                "query_shape",
                "property.predicate",
                "response properties only accept trigger, response predicate, and window.",
            )
        return
    _require_condition_field(
        property_node.predicate, "property.predicate", "property predicate"
    )
    if (
        property_node.trigger is not None
        or property_node.response is not None
        or property_node.within is not None
    ):
        _raise_binding_error(
            "query_shape",
            "property",
            "single-body properties only accept predicate.",
        )


def _validate_query_shape(query: BmcQuery) -> None:
    _validate_initial_shape(query.initial)
    if isinstance(query.assumptions, str) or not isinstance(
        query.assumptions, (list, tuple)
    ):
        _raise_binding_error(
            "query_shape",
            "assumptions",
            "assumptions must be a sequence of BmcAssumption objects.",
        )
    for index, assumption in enumerate(query.assumptions):
        _validate_assumption_shape(assumption, f"assumptions[{index}]")
    _validate_property_shape(query.property)


class _BindingContext:
    def __init__(self, bound: int, domain: object = None) -> None:
        self.bound = bound
        self.domain = domain
        self.references: List[BoundReference] = []

    @property
    def has_domain(self) -> bool:
        return self.domain is not None

    def add_reference(
        self,
        kind: str,
        name: str,
        path: str,
        spelling: str,
        resolved_id: Optional[int] = None,
        declared_type: Optional[str] = None,
    ) -> None:
        self.references.append(
            BoundReference(kind, name, path, spelling, resolved_id, declared_type)
        )


def _resolve_state(
    ctx: _BindingContext, state_path: str, path: str, spelling: str
) -> Optional[int]:
    _require_non_empty_field(state_path, path, "state path")
    if state_path in _RESERVED_STATE_PATHS:
        _raise_binding_error(
            "reserved_state_path",
            path,
            "Reserved BMC sentinel states are not user-addressable state paths.",
        )
    if not ctx.has_domain:
        ctx.add_reference("state", state_path, path, spelling)
        return None
    try:
        entry = ctx.domain.state_by_path(state_path)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: domain lookup fails when the query references an
        # unknown state path; re-surface it as a query-binding diagnostic.
        _raise_binding_error("unknown_state", path, str(err))
    ctx.add_reference("state", state_path, path, spelling, entry.id)
    return entry.id


def _resolve_event(
    ctx: _BindingContext, event_path: str, path: str, spelling: str
) -> Optional[int]:
    _require_non_empty_field(event_path, path, "event path")
    if not ctx.has_domain:
        ctx.add_reference("event", event_path, path, spelling)
        return None
    try:
        entry = ctx.domain.event_by_path(event_path)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: domain lookup fails when the query references an
        # unknown event path; convert it into an InvalidBmcQuery diagnostic.
        _raise_binding_error("unknown_event", path, str(err))
    ctx.add_reference("event", event_path, path, spelling, entry.id)
    return entry.id


def _resolve_variable(
    ctx: _BindingContext, name: str, path: str, spelling: str
) -> Optional[int]:
    _require_non_empty_field(name, path, "variable name")
    if not ctx.has_domain:
        ctx.add_reference("variable", name, path, spelling)
        return None
    try:
        entry = ctx.domain.variable_by_name(name)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: domain lookup fails when the query references an
        # unknown persistent variable; convert it into a binding diagnostic.
        _raise_binding_error("unknown_variable", path, str(err))
    ctx.add_reference("variable", name, path, spelling, entry.id, entry.declared_type)
    return entry.id


def _iter_model_actions(model: object):
    if model is None or not hasattr(model, "walk_states"):
        return ()
    actions = []
    for state in model.walk_states():
        for attr_name in (
            "on_enters",
            "on_durings",
            "on_exits",
            "on_during_aspects",
        ):
            actions.extend(getattr(state, attr_name, ()) or ())
    return tuple(actions)


def _domain_model(ctx: _BindingContext) -> object:
    if not ctx.has_domain:
        return None
    return getattr(ctx.domain, "model", None)


def _named_abstract_action_paths(ctx: _BindingContext) -> Tuple[str, ...]:
    return tuple(
        sorted(
            {
                action.func_name
                for action in _iter_model_actions(_domain_model(ctx))
                if getattr(action, "is_abstract", False)
                and getattr(action, "name", None) is not None
            }
        )
    )


def _named_ref_action_paths(ctx: _BindingContext) -> Tuple[str, ...]:
    return tuple(
        sorted(
            {
                action.func_name
                for action in _iter_model_actions(_domain_model(ctx))
                if getattr(action, "is_ref", False)
                and getattr(action, "name", None) is not None
            }
        )
    )


def _resolve_call_action(ctx: _BindingContext, action_path: str, path: str) -> None:
    _require_non_empty_field(action_path, path, "action")
    model = _domain_model(ctx)
    if model is None:
        return
    choices = _named_abstract_action_paths(ctx)
    if action_path not in choices:
        _raise_binding_error(
            "unknown_call_action",
            path,
            "call action must name an existing named abstract action.",
        )


def _resolve_named_ref(ctx: _BindingContext, ref_path: str, path: str) -> None:
    _require_non_empty_field(ref_path, path, "named_ref")
    model = _domain_model(ctx)
    if model is None:
        return
    choices = _named_ref_action_paths(ctx)
    if ref_path not in choices:
        _raise_binding_error(
            "unknown_named_ref",
            path,
            "named_ref must name an existing named ref action.",
        )


def _validate_current_frame(frame: object, path: str) -> None:
    if frame != "current":
        _raise_binding_error(
            "explicit_frame_selector",
            path,
            "Frame-local predicates only allow omitted/current frame selectors.",
        )


def _is_ascii_decimal(value: str) -> bool:
    return bool(value) and all("0" <= char <= "9" for char in value)


def _validate_event_cycles(selector: object, bound: int, path: str) -> Tuple[int, ...]:
    if selector == "*":
        return tuple(range(bound))
    if isinstance(selector, int) and not isinstance(selector, bool):
        if 0 <= selector < bound:
            return (selector,)
        _raise_binding_error(
            "event_selector_out_of_range",
            path,
            "event selector must satisfy 0 <= k < bound.",
        )
    if isinstance(selector, str) and ".." in selector:
        start_text, end_text = selector.split("..", 1)
        if not (_is_ascii_decimal(start_text) and _is_ascii_decimal(end_text)):
            _raise_binding_error(
                "event_selector_invalid",
                path,
                "event range endpoints must be ASCII decimal integers.",
            )
        start, end = int(start_text), int(end_text)
        if 0 <= start <= end < bound:
            return tuple(range(start, end + 1))
        _raise_binding_error(
            "event_range_out_of_range",
            path,
            "event range must satisfy 0 <= start <= end < bound.",
        )
    _raise_binding_error(
        "event_selector_invalid",
        path,
        "event assumption selector must be '*', an integer, or an inclusive range.",
    )


def _bind_call_step_selector(selector: CallStepSelector, bound: int, path: str) -> None:
    if not isinstance(selector, CallStepSelector):
        _raise_binding_error(
            "call_step_selector_type",
            path,
            "call step selector must be a CallStepSelector.",
        )
    points = [point for point in (selector.start, selector.end) if point is not None]
    for index, point in enumerate(points):
        if point.kind == "absolute" and not (0 <= point.value < bound):
            _raise_binding_error(
                "call_step_out_of_range",
                "%s[%d]" % (path, index),
                "absolute call step selector must satisfy 0 <= k < bound.",
            )


def _bind_call_where_num_expr(
    ctx: _BindingContext, expr: BmcNumExpr, path: str
) -> None:
    if isinstance(expr, NameRef):
        _resolve_variable(ctx, expr.name, path, "call_where_bare")
        return
    if isinstance(expr, FrameVar):
        _resolve_variable(ctx, expr.name, path, "call_where_var_call")
        return
    if isinstance(expr, Cycle):
        _raise_binding_error(
            "cycle_not_allowed",
            path,
            "bare cycle is not a call-time snapshot variable and is not allowed "
            "inside call where filters.",
        )
    if isinstance(expr, (IntLiteral, FloatLiteral, MathConst)):
        return
    if isinstance(expr, CallCount):
        _raise_binding_error(
            "call_count_not_allowed",
            path,
            "call_count() is not allowed inside call where filters.",
        )
    if isinstance(expr, NumUnaryOp):
        _bind_call_where_num_expr(ctx, expr.operand, path + ".operand")
        return
    if isinstance(expr, NumBinaryOp):
        _bind_call_where_num_expr(ctx, expr.left, path + ".left")
        _bind_call_where_num_expr(ctx, expr.right, path + ".right")
        return
    if isinstance(expr, NumConditionalOp):
        _bind_call_where_condition(ctx, expr.condition, path + ".condition")
        _bind_call_where_num_expr(ctx, expr.if_true, path + ".if_true")
        _bind_call_where_num_expr(ctx, expr.if_false, path + ".if_false")
        return
    if isinstance(expr, UFuncCall):
        _bind_call_where_num_expr(ctx, expr.operand, path + ".operand")
        return
    _raise_binding_error(
        "unsupported_call_where_numeric_expr",
        path,
        "Unsupported call where numeric expression: %s." % type(expr).__name__,
    )


def _bind_call_where_condition(
    ctx: _BindingContext, expr: BmcCondExpr, path: str
) -> None:
    if isinstance(expr, BoolLiteral):
        return
    if isinstance(expr, NumericComparison):
        _bind_call_where_num_expr(ctx, expr.left, path + ".left")
        _bind_call_where_num_expr(ctx, expr.right, path + ".right")
        return
    if isinstance(expr, CondUnaryOp):
        _bind_call_where_condition(ctx, expr.operand, path + ".operand")
        return
    if isinstance(expr, CondBinaryOp):
        _bind_call_where_condition(ctx, expr.left, path + ".left")
        _bind_call_where_condition(ctx, expr.right, path + ".right")
        return
    if isinstance(expr, CondConditionalOp):
        _bind_call_where_condition(ctx, expr.condition, path + ".condition")
        _bind_call_where_condition(ctx, expr.if_true, path + ".if_true")
        _bind_call_where_condition(ctx, expr.if_false, path + ".if_false")
        return
    if isinstance(expr, (Active, Terminated, Event, Case, Called)):
        _raise_binding_error(
            "call_where_atom_not_allowed",
            path,
            "call where filters may only use snapshot variables, literals, "
            "numeric operators, comparisons, and logical operators.",
        )
    _raise_binding_error(
        "unsupported_call_where_condition_expr",
        path,
        "Unsupported call where condition expression: %s." % type(expr).__name__,
    )


def _bind_call_filter(ctx: _BindingContext, filter_node: CallFilter, path: str) -> None:
    if not isinstance(filter_node, CallFilter):
        _raise_binding_error(
            "call_filter_type", path, "call filter must be CallFilter."
        )
    if filter_node.action is not None:
        _resolve_call_action(ctx, filter_node.action, path + ".action")
    _bind_call_step_selector(filter_node.effective_step, ctx.bound, path + ".step")
    if filter_node.stage is not None and filter_node.stage not in {
        "enter",
        "during",
        "exit",
    }:
        _raise_binding_error(
            "call_stage",
            path + ".stage",
            "call stage must be 'enter', 'during', or 'exit'.",
        )
    if filter_node.role is not None and filter_node.role not in _CALL_RUNTIME_ROLES:
        _raise_binding_error(
            "call_role",
            path + ".role",
            "call role must be one of the supported runtime roles.",
        )
    if filter_node.state is not None:
        _resolve_state(ctx, filter_node.state, path + ".state", "call_state")
    if filter_node.active_leaf is not None:
        _resolve_state(
            ctx, filter_node.active_leaf, path + ".active_leaf", "call_active_leaf"
        )
    if filter_node.named_ref is not None:
        _resolve_named_ref(ctx, filter_node.named_ref, path + ".named_ref")
    if filter_node.where is not None:
        _bind_call_where_condition(ctx, filter_node.where, path + ".where")


def _bind_numeric_expr(
    ctx: _BindingContext,
    expr: BmcNumExpr,
    path: str,
    allow_cycle: bool,
    allow_call: bool = False,
) -> None:
    if isinstance(expr, NameRef):
        _resolve_variable(ctx, expr.name, path, "bare")
        return
    if isinstance(expr, FrameVar):
        _resolve_variable(ctx, expr.name, path, "var_call")
        return
    if isinstance(expr, Cycle):
        if not allow_cycle:
            _raise_binding_error(
                "cycle_not_allowed",
                path,
                "bare cycle is not allowed in this binding context.",
            )
        return
    if isinstance(expr, CallCount):
        if not allow_call:
            _raise_binding_error(
                "call_count_not_allowed",
                path,
                "call_count() is not allowed in this binding context.",
            )
        _bind_call_filter(ctx, expr.filter, path + ".filter")
        return
    if isinstance(expr, NumUnaryOp):
        _bind_numeric_expr(
            ctx, expr.operand, path + ".operand", allow_cycle, allow_call
        )
        return
    if isinstance(expr, NumBinaryOp):
        _bind_numeric_expr(ctx, expr.left, path + ".left", allow_cycle, allow_call)
        _bind_numeric_expr(ctx, expr.right, path + ".right", allow_cycle, allow_call)
        return
    if isinstance(expr, NumConditionalOp):
        _bind_condition_expr(
            ctx,
            expr.condition,
            path + ".condition",
            _ConditionRules.frame_local(allow_cycle=allow_cycle, allow_call=allow_call),
        )
        _bind_numeric_expr(
            ctx, expr.if_true, path + ".if_true", allow_cycle, allow_call
        )
        _bind_numeric_expr(
            ctx, expr.if_false, path + ".if_false", allow_cycle, allow_call
        )
        return
    if isinstance(expr, UFuncCall):
        _bind_numeric_expr(
            ctx, expr.operand, path + ".operand", allow_cycle, allow_call
        )
        return
    if isinstance(expr, (IntLiteral, FloatLiteral, MathConst)):
        return
    _raise_binding_error(
        "unsupported_numeric_expr",
        path,
        f"Unsupported numeric expression object: {type(expr).__name__}.",
    )


@dataclass(frozen=True)
class _ConditionRules:
    allow_cycle: bool = True
    allow_event_current: bool = False
    allow_call: bool = False

    @classmethod
    def frame_local(
        cls, allow_cycle: bool = True, allow_call: bool = False
    ) -> "_ConditionRules":
        return cls(allow_cycle=allow_cycle, allow_call=allow_call)


def _bind_condition_expr(
    ctx: _BindingContext, expr: BmcCondExpr, path: str, rules: _ConditionRules
) -> None:
    if isinstance(expr, NumericComparison):
        _bind_numeric_expr(
            ctx, expr.left, path + ".left", rules.allow_cycle, rules.allow_call
        )
        _bind_numeric_expr(
            ctx, expr.right, path + ".right", rules.allow_cycle, rules.allow_call
        )
        return
    if isinstance(expr, CondUnaryOp):
        _bind_condition_expr(ctx, expr.operand, path + ".operand", rules)
        return
    if isinstance(expr, CondBinaryOp):
        _bind_condition_expr(ctx, expr.left, path + ".left", rules)
        _bind_condition_expr(ctx, expr.right, path + ".right", rules)
        return
    if isinstance(expr, CondConditionalOp):
        _bind_condition_expr(ctx, expr.condition, path + ".condition", rules)
        _bind_condition_expr(ctx, expr.if_true, path + ".if_true", rules)
        _bind_condition_expr(ctx, expr.if_false, path + ".if_false", rules)
        return
    if isinstance(expr, Active):
        _validate_current_frame(expr.frame, path + ".frame")
        _resolve_state(ctx, expr.state_path, path, "active")
        return
    if isinstance(expr, Terminated):
        _validate_current_frame(expr.frame, path + ".frame")
        return
    if isinstance(expr, Event):
        if rules.allow_event_current and expr.selector == "current":
            _resolve_event(ctx, expr.event_path, path, "event")
            return
        _raise_binding_error(
            "event_not_allowed",
            path,
            "event atoms are not allowed in this binding context.",
        )
    if isinstance(expr, Case):
        _raise_binding_error(
            "case_not_allowed",
            path,
            "case atoms are only allowed as the naked cover predicate.",
        )
    if isinstance(expr, Called):
        if not rules.allow_call:
            _raise_binding_error(
                "called_not_allowed",
                path,
                "called() is not allowed in this binding context.",
            )
        _bind_call_filter(ctx, expr.call_filter, path + ".filter")
        return
    if isinstance(expr, BoolLiteral):
        return
    _raise_binding_error(
        "unsupported_condition_expr",
        path,
        f"Unsupported condition expression object: {type(expr).__name__}.",
    )


def _domain_variable_names(ctx: _BindingContext) -> Tuple[str, ...]:
    if not ctx.has_domain:
        return ()
    return tuple(var.name for var in ctx.domain.variables)


def _bind_initial_variable_policy(
    ctx: _BindingContext, policy: InitialVariablePolicy
) -> Optional[Tuple[str, ...]]:
    if policy.havoc_all:
        if not ctx.has_domain:
            return None
        names = _domain_variable_names(ctx)
        for index, name in enumerate(names):
            _resolve_variable(
                ctx,
                name,
                "initial.variable_policy.havoc_all[%d]" % index,
                "havoc",
            )
        return names

    resolved = []
    seen = set()
    for index, name in enumerate(policy.havoc_variables):
        path = "initial.variable_policy.havoc_variables[%d]" % index
        if name in seen:
            _raise_binding_error(
                "duplicate_havoc_variable",
                path,
                "initial havoc variables must not contain duplicate names.",
            )
        seen.add(name)
        _resolve_variable(ctx, name, path, "havoc")
        resolved.append(name)
    if not ctx.has_domain:
        return tuple(resolved)
    domain_order = {
        name: index for index, name in enumerate(_domain_variable_names(ctx))
    }
    return tuple(sorted(resolved, key=lambda name: domain_order[name]))


def _bind_initial(ctx: _BindingContext, initial: InitialSpec) -> BoundInitialSpec:
    resolved_state_id = None
    if initial.mode == "state":
        resolved_state_id = _resolve_state(
            ctx, initial.state_path or "", "initial.state_path", "state_path"
        )
    resolved_havoc_variables = _bind_initial_variable_policy(
        ctx, initial.variable_policy
    )
    if initial.predicate is not None:
        _bind_condition_expr(
            ctx,
            initial.predicate,
            "initial.predicate",
            _ConditionRules.frame_local(allow_cycle=False),
        )
    return BoundInitialSpec(initial, resolved_state_id, resolved_havoc_variables)


def _bind_frame_assumption(
    ctx: _BindingContext, assumption: FrameAssumption, index: int
) -> BoundAssumption:
    path = f"assumptions[{index}]"
    if assumption.kind == "at" and (
        assumption.frame is None
        or isinstance(assumption.frame, bool)
        or not isinstance(assumption.frame, int)
        or assumption.frame < 0
        or assumption.frame > ctx.bound
    ):
        _raise_binding_error(
            "frame_selector_out_of_range",
            path + ".frame",
            "assume at frame must satisfy 0 <= k <= bound.",
        )
    _bind_condition_expr(
        ctx,
        assumption.predicate,
        path + ".predicate",
        _ConditionRules.frame_local(allow_cycle=True),
    )
    return BoundAssumption(assumption, "frame", frame=assumption.frame)


def _bind_event_assumption(
    ctx: _BindingContext, assumption: EventAssumption, index: int
) -> BoundAssumption:
    path = f"assumptions[{index}]"
    cycles = _validate_event_cycles(assumption.selector, ctx.bound, path + ".selector")
    resolved_id = _resolve_event(
        ctx, assumption.event_path, path + ".event_path", "event_assumption"
    )
    resolved_ids = () if resolved_id is None else (resolved_id,)
    return BoundAssumption(
        assumption, "event", cycles=cycles, resolved_event_ids=resolved_ids
    )


def _bind_cardinality_assumption(
    ctx: _BindingContext, assumption: EventCardinalityAssumption, index: int
) -> BoundAssumption:
    resolved_ids = []
    for event_index, event_path in enumerate(assumption.event_paths):
        resolved_id = _resolve_event(
            ctx,
            event_path,
            f"assumptions[{index}].event_paths[{event_index}]",
            "cardinality_event",
        )
        if resolved_id is not None:
            resolved_ids.append(resolved_id)
    return BoundAssumption(
        assumption,
        "event_cardinality",
        resolved_event_ids=tuple(resolved_ids),
    )


def _bind_assumptions(
    ctx: _BindingContext, assumptions: Sequence[BmcAssumption]
) -> Tuple[BoundAssumption, ...]:
    bound_assumptions = []
    for index, assumption in enumerate(assumptions):
        if isinstance(assumption, FrameAssumption):
            bound_assumptions.append(_bind_frame_assumption(ctx, assumption, index))
        elif isinstance(assumption, EventAssumption):
            bound_assumptions.append(_bind_event_assumption(ctx, assumption, index))
        elif isinstance(assumption, EventCardinalityAssumption):
            bound_assumptions.append(
                _bind_cardinality_assumption(ctx, assumption, index)
            )
        else:
            _raise_binding_error(
                "assumption_type",
                f"assumptions[{index}]",
                f"Unsupported assumption object: {type(assumption).__name__}.",
            )
    return tuple(bound_assumptions)


def _bind_property(ctx: _BindingContext, property_node: BmcProperty) -> BoundProperty:
    kind = property_node.kind
    if kind == "response":
        _bind_condition_expr(
            ctx,
            property_node.trigger,
            "property.trigger",
            _ConditionRules(
                allow_cycle=True, allow_event_current=True, allow_call=True
            ),
        )
        _bind_condition_expr(
            ctx,
            property_node.response,
            "property.response",
            _ConditionRules.frame_local(allow_cycle=True, allow_call=True),
        )
        return BoundProperty(property_node)
    if kind == "cover":
        predicate = property_node.predicate
        if not isinstance(predicate, Case) or predicate.frame != "current":
            _raise_binding_error(
                "cover_predicate",
                "property.predicate",
                'cover properties require a naked case("label") predicate.',
            )
        _require_non_empty_field(
            predicate.label, "property.predicate.label", "case label"
        )
        return BoundProperty(property_node, case_label=predicate.label)
    _bind_condition_expr(
        ctx,
        property_node.predicate,
        "property.predicate",
        _ConditionRules.frame_local(allow_cycle=True, allow_call=True),
    )
    return BoundProperty(property_node)


def _bind_query_with_domain(query: BmcQuery, domain: object = None) -> BoundBmcQuery:
    ctx = _BindingContext(query.property.bound, domain=domain)
    initial = _bind_initial(ctx, query.initial)
    assumptions = _bind_assumptions(ctx, query.assumptions)
    property_node = _bind_property(ctx, query.property)
    return BoundBmcQuery(
        query=query,
        initial=initial,
        assumptions=assumptions,
        property=property_node,
        references=tuple(ctx.references),
    )


def bind_bmc_query_structure(query: BmcQuery) -> BoundBmcQuery:
    """Bind a BMC query without loading or resolving a model domain.

    :param query: Parser-independent BMC query object.
    :type query: BmcQuery
    :return: Query-only bound snapshot.
    :rtype: BoundBmcQuery
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If the query violates semantic
        context rules.

    Example::

        >>> from pyfcstm.bmc.parse import parse_bmc_query
        >>> bound = bind_bmc_query_structure(parse_bmc_query('check reach <= 1: true;'))
        >>> bound.property.bound
        1
    """
    return _bind_query_with_domain(_require_query(query), domain=None)


def _domain_from_model(model: object, bound: int) -> object:
    from .domain import build_bmc_domain

    try:
        return build_bmc_domain(model, bound)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: build_bmc_domain rejects non-StateMachine values or
        # inconsistent models; expose it as a stable binding diagnostic.
        _raise_binding_error("invalid_model", "model", str(err))


def _validate_domain_bound(domain: object, query_bound: int) -> None:
    from .domain import BmcDomain

    if not isinstance(domain, BmcDomain):
        _raise_binding_error("domain_type", "domain", "domain must be BmcDomain.")
    if domain.bound != query_bound:
        _raise_binding_error(
            "domain_bound_mismatch",
            "domain.bound",
            f"domain bound {domain.bound} does not match query bound {query_bound}.",
        )


def bind_bmc_query(
    query: BmcQuery, model: object = None, domain: object = None
) -> BoundBmcQuery:
    """Bind a BMC query with optional model/domain resolution.

    :param query: Parser-independent BMC query object.
    :type query: BmcQuery
    :param model: Optional state machine.  When supplied without ``domain``, a
        :class:`pyfcstm.bmc.domain.BmcDomain` is built from ``query``'s bound.
    :type model: object, optional
    :param domain: Optional pre-built domain.  Its bound must match
        ``query.property.bound``.
    :type domain: object, optional
    :return: Bound query snapshot.
    :rtype: BoundBmcQuery
    :raises pyfcstm.bmc.errors.InvalidBmcQuery: If query binding fails, both
        ``model`` and ``domain`` are supplied, or the supplied domain bound does
        not match the query bound.

    Example::

        >>> from pyfcstm.bmc.parse import parse_bmc_query
        >>> bind_bmc_query(parse_bmc_query('check reach <= 1: true;')).property.kind
        'reach'
    """
    query = _require_query(query)
    if model is not None and domain is not None:
        _raise_binding_error(
            "model_domain_conflict",
            "model",
            "bind_bmc_query accepts either model or domain, not both.",
        )
    if domain is not None:
        _validate_domain_bound(domain, query.property.bound)
        return _bind_query_with_domain(query, domain=domain)
    if model is not None:
        resolved_domain = _domain_from_model(model, query.property.bound)
        return _bind_query_with_domain(query, domain=resolved_domain)
    return bind_bmc_query_structure(query)


__all__ = [
    "BmcBindingDiagnostic",
    "BoundReference",
    "BoundInitialSpec",
    "BoundAssumption",
    "BoundProperty",
    "BoundBmcQuery",
    "bind_bmc_query_structure",
    "bind_bmc_query",
]

"""Macro-step case contracts for FCSTM bounded model checking.

The macro contract layer defines the data objects exchanged between future
macro-step expansion and solver-relation lowering.  It does not traverse a
runtime state machine, build Z3 transition relations, or append partition
repair constraints to user formulas.  Instead, it makes the shape of each case
explicit: source and target ids, stable labels, event uses, a bare case
condition ``gamma``, and an explicit writeback recipe for every persistent
variable.

Design contracts:

* :class:`CycleCase.condition` is the bare case condition.  It never includes
  the pre-state source guard; later relation builders form ``source_guard and
  gamma`` before emitting ``A => R``.
* :class:`VarUpdate` entries are explicit and complete.  Carry-over variables
  are represented as writeback entries rather than left unconstrained.
* Fallback and semantic-delta helpers subtract only their source-appropriate
  ordinary accepted success-case conditions: stable fallback accepts transition
  cases only, while entry semantic delta accepts transition or initial cases.
  Build-diagnostic conditions are excluded only where the issue design requires
  them.  Failed candidate metadata is kept for diagnostics and never removes
  uncovered regions.
* Partition verification is a build-time/test-time self-check.  It returns a
  diagnostic summary or raises :class:`pyfcstm.bmc.errors.BmcBuildError`; it
  never produces clauses for ``Core_N`` or ``Phi_N``.

The module contains:

* :class:`BoolTemplate` - Small solver-independent boolean recipe for contract
  tests and partition self-checks.
* :class:`EventUse` and :class:`VarUpdate` - Event-use and writeback metadata.
* :class:`CycleCase` - One macro-step relation case.
* :class:`MacroStepFormal` - Source-local buckets of success, delta, and build
  diagnostic conditions.
* Helper constructors for absorb, fallback, semantic-delta, and partition
  checks.

Example::

    >>> from pyfcstm.bmc.domain import build_bmc_domain
    >>> from pyfcstm.bmc.macro import terminated_absorb_case
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
    >>> terminated_absorb_case(domain).label
    '__terminate__::absorb::__terminate__::0'
"""

from __future__ import annotations

import itertools
import json
from dataclasses import dataclass, field
from typing import Any, Dict, Mapping, Optional, Sequence, Tuple

from pyfcstm.bmc.domain import STATE_DIAGNOSTIC_ID, STATE_TERMINATE_ID, BmcDomain
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcDomain, InvalidBmcEncoding
from pyfcstm.bmc.source import (
    DIAGNOSTIC_CASE_PATH,
    TERMINATE_CASE_PATH,
    MacroStepSource,
)

_CanonicalDict = Dict[str, Any]
_BOOL_KINDS = {"true", "false", "atom", "not", "and", "or"}
_CASE_KINDS = {"transition", "fallback", "initial", "absorb", "diagnostic", "delta"}
_ACCEPTED_CASE_KINDS = {"transition", "initial"}
_EVENT_POLARITIES = {"positive", "negative"}
_EVENT_REASONS = {"trigger", "priority", "fallback", "descent", "assumption"}
_RESERVED_CASE_PATHS = {TERMINATE_CASE_PATH, DIAGNOSTIC_CASE_PATH}
_SOURCE_STATE_ATOM_PREFIX = "__source_state__:"


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidBmcEncoding("%s must be a non-empty string." % field_name)
    return value


def _validate_index(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBmcEncoding("%s must be an integer." % field_name)
    return value


def _validate_choice(value: object, choices: set, field_name: str) -> str:
    if not isinstance(value, str) or value not in choices:
        raise InvalidBmcEncoding("Unsupported %s: %r." % (field_name, value))
    return value


def _canonical_key(item: Any) -> str:
    if hasattr(item, "to_canonical"):
        value = item.to_canonical()
    else:
        value = item
    return json.dumps(value, sort_keys=True, separators=(",", ":"))


@dataclass(frozen=True)
class BoolTemplate:
    """Solver-independent boolean condition recipe.

    ``BoolTemplate`` is intentionally small.  It is sufficient for macro contract
    tests and partition proofs, while later solver lowering can map
    richer case recipes into Z3 without changing the surrounding case contract.

    :param kind: ``"true"``, ``"false"``, ``"atom"``, ``"not"``,
        ``"and"``, or ``"or"``.
    :type kind: str
    :param name: Atom name for ``kind="atom"``, defaults to ``None``.
    :type name: str, optional
    :param operands: Child boolean templates for composite nodes, defaults to
        an empty tuple.
    :type operands: Tuple[BoolTemplate, ...], optional

    Example::

        >>> gamma = BoolTemplate.atom('gamma')
        >>> BoolTemplate.not_(gamma).evaluate({'gamma': False})
        True
    """

    kind: str
    name: Optional[str] = None
    operands: Tuple["BoolTemplate", ...] = ()

    def __post_init__(self) -> None:
        kind = _validate_choice(self.kind, _BOOL_KINDS, "boolean template kind")
        object.__setattr__(self, "kind", kind)
        operands = tuple(self.operands)
        if not all(isinstance(item, BoolTemplate) for item in operands):
            raise InvalidBmcEncoding("operands must contain BoolTemplate objects.")
        if kind == "atom":
            object.__setattr__(
                self,
                "name",
                _require_non_empty_string(self.name, "atom name"),
            )
            if operands:
                raise InvalidBmcEncoding("atom templates cannot have operands.")
        elif kind in {"true", "false"}:
            if self.name is not None:
                raise InvalidBmcEncoding("constant templates cannot have names.")
            if operands:
                raise InvalidBmcEncoding("constant templates cannot have operands.")
        elif kind == "not":
            if self.name is not None:
                raise InvalidBmcEncoding("not templates cannot have names.")
            if len(operands) != 1:
                raise InvalidBmcEncoding("not templates must have one operand.")
        else:
            if self.name is not None:
                raise InvalidBmcEncoding("compound templates cannot have names.")
            if not operands:
                raise InvalidBmcEncoding("compound templates must have operands.")
            operands = tuple(sorted(operands, key=_canonical_key))
        object.__setattr__(self, "operands", operands)

    @classmethod
    def true(cls) -> "BoolTemplate":
        """Return the constant true condition.

        :return: Constant true condition.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.true().evaluate({})
            True
        """
        return cls("true")

    @classmethod
    def false(cls) -> "BoolTemplate":
        """Return the constant false condition.

        :return: Constant false condition.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.false().evaluate({})
            False
        """
        return cls("false")

    @classmethod
    def atom(cls, name: str) -> "BoolTemplate":
        """Return an atom condition.

        :param name: Atom name.
        :type name: str
        :return: Atom condition.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.atom('go').variables
            ('go',)
        """
        return cls("atom", name=name)

    @classmethod
    def not_(cls, operand: "BoolTemplate") -> "BoolTemplate":
        """Return logical negation of ``operand``.

        :param operand: Operand condition.
        :type operand: BoolTemplate
        :return: Negated condition.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.not_(BoolTemplate.false()).evaluate({})
            True
        """
        return cls("not", operands=(operand,))

    @classmethod
    def and_(cls, *operands: "BoolTemplate") -> "BoolTemplate":
        """Return logical conjunction of ``operands``.

        :param operands: Operand conditions.
        :type operands: BoolTemplate
        :return: Conjunction, or constant true for an empty input.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.and_().evaluate({})
            True
        """
        if not operands:
            return cls.true()
        if not all(isinstance(item, BoolTemplate) for item in operands):
            raise InvalidBmcEncoding("operands must contain BoolTemplate objects.")
        if len(operands) == 1:
            return operands[0]
        return cls("and", operands=tuple(operands))

    @classmethod
    def or_(cls, *operands: "BoolTemplate") -> "BoolTemplate":
        """Return logical disjunction of ``operands``.

        :param operands: Operand conditions.
        :type operands: BoolTemplate
        :return: Disjunction, or constant false for an empty input.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.or_().evaluate({})
            False
        """
        if not operands:
            return cls.false()
        if not all(isinstance(item, BoolTemplate) for item in operands):
            raise InvalidBmcEncoding("operands must contain BoolTemplate objects.")
        if len(operands) == 1:
            return operands[0]
        return cls("or", operands=tuple(operands))

    @property
    def variables(self) -> Tuple[str, ...]:
        """Return atom names referenced by this template.

        :return: Sorted unique atom names.
        :rtype: Tuple[str, ...]

        Example::

            >>> BoolTemplate.or_(BoolTemplate.atom('b'), BoolTemplate.atom('a')).variables
            ('a', 'b')
        """
        if self.kind == "atom":
            return (self.name or "",)
        values = set()
        for operand in self.operands:
            values.update(operand.variables)
        return tuple(sorted(values))

    def evaluate(self, values: Mapping[str, bool]) -> bool:
        """Evaluate this template on a boolean assignment.

        :param values: Mapping from atom names to booleans.
        :type values: Mapping[str, bool]
        :return: Evaluated boolean value.
        :rtype: bool
        :raises BmcBuildError: If an atom is missing or a value is not boolean.

        Example::

            >>> expr = BoolTemplate.and_(BoolTemplate.atom('a'), BoolTemplate.not_(BoolTemplate.atom('b')))
            >>> expr.evaluate({'a': True, 'b': False})
            True
        """
        if self.kind == "true":
            return True
        if self.kind == "false":
            return False
        if self.kind == "atom":
            if self.name not in values:
                raise BmcBuildError("missing boolean assignment for %r." % self.name)
            value = values[self.name]
            if not isinstance(value, bool):
                raise BmcBuildError("boolean assignment %r must be bool." % self.name)
            return value
        if self.kind == "not":
            return not self.operands[0].evaluate(values)
        if self.kind == "and":
            return all(operand.evaluate(values) for operand in self.operands)
        if self.kind == "or":
            return any(operand.evaluate(values) for operand in self.operands)
        raise BmcBuildError("unsupported boolean template kind: %r." % self.kind)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable condition recipe.

        :return: Canonical condition dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> BoolTemplate.atom('gamma').to_canonical()['name']
            'gamma'
        """
        result = {"node": "bool_template", "kind": self.kind}
        if self.kind == "atom":
            result["name"] = self.name
        if self.operands:
            result["operands"] = [item.to_canonical() for item in self.operands]
        return result


@dataclass(frozen=True)
class EventUse:
    """Event input usage metadata for one case.

    :param event_id: Domain event id.
    :type event_id: int
    :param path: Fully qualified event path.
    :type path: str
    :param polarity: ``"positive"`` or ``"negative"``.
    :type polarity: str
    :param reason: Usage reason such as ``"trigger"`` or ``"priority"``.
    :type reason: str

    Example::

        >>> EventUse(0, 'Root.Go', 'positive', 'trigger').polarity
        'positive'
    """

    event_id: int
    path: str
    polarity: str
    reason: str

    def __post_init__(self) -> None:
        event_id = _validate_index(self.event_id, "event_id")
        if event_id < 0:
            raise InvalidBmcEncoding("event_id must be non-negative.")
        object.__setattr__(self, "event_id", event_id)
        object.__setattr__(
            self,
            "path",
            _require_non_empty_string(self.path, "event path"),
        )
        object.__setattr__(
            self,
            "polarity",
            _validate_choice(self.polarity, _EVENT_POLARITIES, "event polarity"),
        )
        object.__setattr__(
            self,
            "reason",
            _validate_choice(self.reason, _EVENT_REASONS, "event reason"),
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable event-use dictionary.

        :return: Canonical event-use metadata.
        :rtype: Dict[str, object]

        Example::

            >>> EventUse(0, 'Root.Go', 'positive', 'trigger').to_canonical()['reason']
            'trigger'
        """
        return {
            "node": "event_use",
            "event_id": self.event_id,
            "path": self.path,
            "polarity": self.polarity,
            "reason": self.reason,
        }


@dataclass(frozen=True)
class VarUpdate:
    """Persistent-variable writeback recipe for one macro-step case.

    :param variable_id: Domain variable id.
    :type variable_id: int
    :param variable_name: Persistent variable name.
    :type variable_name: str
    :param expression: Stable expression digest or recipe key used by later
        lowering.
    :type expression: str
    :param is_carry: Whether this update is explicit carry-over, defaults to
        ``False``.
    :type is_carry: bool, optional

    Example::

        >>> VarUpdate(0, 'x', 'pre:x', is_carry=True).is_carry
        True
    """

    variable_id: int
    variable_name: str
    expression: str
    is_carry: bool = False

    def __post_init__(self) -> None:
        object.__setattr__(
            self,
            "variable_id",
            _validate_index(self.variable_id, "variable_id"),
        )
        if self.variable_id < 0:
            raise InvalidBmcEncoding("variable_id must be non-negative.")
        object.__setattr__(
            self,
            "variable_name",
            _require_non_empty_string(self.variable_name, "variable_name"),
        )
        object.__setattr__(
            self,
            "expression",
            _require_non_empty_string(self.expression, "expression"),
        )
        if not isinstance(self.is_carry, bool):
            raise InvalidBmcEncoding("is_carry must be a boolean.")

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable variable update dictionary.

        :return: Canonical variable update.
        :rtype: Dict[str, object]

        Example::

            >>> VarUpdate(0, 'x', 'pre:x').to_canonical()['variable_name']
            'x'
        """
        return {
            "node": "var_update",
            "variable_id": self.variable_id,
            "variable_name": self.variable_name,
            "expression": self.expression,
            "is_carry": self.is_carry,
        }


def carry_var_updates(domain: BmcDomain) -> Tuple[VarUpdate, ...]:
    """Return explicit carry-over updates for every persistent variable.

    :param domain: Domain snapshot whose variables should be carried.
    :type domain: BmcDomain
    :return: Complete carry-over update tuple sorted by variable id.
    :rtype: Tuple[VarUpdate, ...]
    :raises InvalidBmcEncoding: If ``domain`` is not a BMC domain.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('def int x = 0; state Root;'), 1)
        >>> carry_var_updates(domain)[0].expression
        'pre:x'
    """
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    return tuple(
        VarUpdate(entry.id, entry.name, "pre:%s" % entry.name, is_carry=True)
        for entry in domain.variables
    )


def var_update_for(
    domain: BmcDomain,
    variable: object,
    expression: str,
    is_carry: bool = False,
) -> VarUpdate:
    """Build one variable update from a domain variable id or name.

    :param domain: Domain snapshot that owns the variable.
    :type domain: BmcDomain
    :param variable: Variable id or name.
    :type variable: int or str
    :param expression: Stable expression digest or recipe key.
    :type expression: str
    :param is_carry: Whether this update is carry-over, defaults to ``False``.
    :type is_carry: bool, optional
    :return: Variable update entry.
    :rtype: VarUpdate
    :raises InvalidBmcEncoding: If ``variable`` cannot be resolved.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('def int x = 0; state Root;'), 1)
        >>> var_update_for(domain, 'x', 'x+1').variable_id
        0
    """
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    try:
        if isinstance(variable, str):
            entry = domain.variable_by_name(variable)
        elif isinstance(variable, bool) or not isinstance(variable, int):
            raise InvalidBmcEncoding("variable must be a variable id or name.")
        else:
            entry = domain.variable_by_id(variable)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: BmcDomain lookup rejects unknown variable ids or
        # names supplied by this writeback recipe constructor.
        raise InvalidBmcEncoding(str(err)) from err
    return VarUpdate(entry.id, entry.name, expression, is_carry=is_carry)


def build_var_updates(
    domain: BmcDomain,
    updates: Sequence[VarUpdate],
) -> Tuple[VarUpdate, ...]:
    """Validate and normalize a complete writeback tuple.

    :param domain: Domain snapshot whose persistent variables must be covered.
    :type domain: BmcDomain
    :param updates: Candidate variable updates.
    :type updates: Sequence[VarUpdate]
    :return: Updates sorted by variable id.
    :rtype: Tuple[VarUpdate, ...]
    :raises InvalidBmcEncoding: If an update is missing, duplicated, or
        references an unknown variable.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('def int x = 0; state Root;'), 1)
        >>> build_var_updates(domain, carry_var_updates(domain))[0].variable_name
        'x'
    """
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    if not isinstance(updates, (list, tuple)):
        raise InvalidBmcEncoding("updates must be a sequence.")
    items = tuple(updates)
    if not all(isinstance(item, VarUpdate) for item in items):
        raise InvalidBmcEncoding("updates must contain VarUpdate objects.")

    by_id = {}
    by_name = {}
    for item in items:
        if item.variable_id in by_id:
            raise InvalidBmcEncoding(
                "Duplicate variable update id: %r." % item.variable_id
            )
        if item.variable_name in by_name:
            raise InvalidBmcEncoding(
                "Duplicate variable update name: %r." % item.variable_name
            )
        try:
            entry = domain.variable_by_id(item.variable_id)
        except InvalidBmcDomain as err:
            # InvalidBmcDomain: domain.variable_by_id rejects unknown variable ids
            # supplied by this macro-step writeback recipe.
            raise InvalidBmcEncoding(str(err)) from err
        if entry.name != item.variable_name:
            raise InvalidBmcEncoding("Variable update id/name mismatch.")
        by_id[item.variable_id] = item
        by_name[item.variable_name] = item

    expected_ids = tuple(entry.id for entry in domain.variables)
    actual_ids = tuple(sorted(by_id))
    if actual_ids != expected_ids:
        raise InvalidBmcEncoding("var_update must cover every persistent variable.")
    return tuple(by_id[index] for index in expected_ids)


def _expected_case_path(domain: BmcDomain, state_id: int) -> str:
    try:
        if state_id == STATE_TERMINATE_ID:
            domain.state_by_id(STATE_TERMINATE_ID)
            return TERMINATE_CASE_PATH
        if state_id == STATE_DIAGNOSTIC_ID:
            domain.state_by_id(STATE_DIAGNOSTIC_ID)
            return DIAGNOSTIC_CASE_PATH
        entry = domain.state_by_id(state_id)
        if entry.path in _RESERVED_CASE_PATHS:
            raise InvalidBmcEncoding(
                "Model case path must not use reserved macro-step paths."
            )
        return entry.path
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: BmcDomain lookup rejects unknown source or target ids
        # supplied by this macro-step case contract.
        raise InvalidBmcEncoding(str(err)) from err


def _validate_case_state(
    domain: BmcDomain, state_id: int, path: str, role: str
) -> None:
    expected = _expected_case_path(domain, state_id)
    if path != expected:
        raise InvalidBmcEncoding("%s path does not match %s id." % (role, role))


def _derive_is_diagnostic(kind: str, target_state_id: int) -> bool:
    return kind in {"diagnostic", "delta"} or (
        kind == "absorb" and target_state_id == STATE_DIAGNOSTIC_ID
    )


def _validate_non_reserved_condition_atoms(
    condition: BoolTemplate,
    field_name: str,
) -> None:
    for variable in condition.variables:
        if variable.startswith(_SOURCE_STATE_ATOM_PREFIX):
            raise InvalidBmcEncoding(
                "%s uses reserved source-state atom namespace: %r."
                % (field_name, variable)
            )


def _normalize_accepted_cases(
    accepted_cases: Sequence["CycleCase"],
    source: MacroStepSource,
    helper_name: str,
    allowed_kinds: Sequence[str],
) -> Tuple["CycleCase", ...]:
    if not isinstance(accepted_cases, (list, tuple)):
        raise InvalidBmcEncoding("accepted_cases must be a sequence.")
    accepted = tuple(accepted_cases)
    allowed = tuple(allowed_kinds)
    if not allowed or any(kind not in _ACCEPTED_CASE_KINDS for kind in allowed):
        raise InvalidBmcEncoding("accepted case kind policy is invalid.")
    if not all(isinstance(item, CycleCase) for item in accepted):
        raise InvalidBmcEncoding("accepted_cases must contain CycleCase objects.")
    for case in accepted:
        if case.kind not in allowed:
            raise InvalidBmcEncoding(
                "accepted_cases for %s may only contain ordinary accepted cases."
                % helper_name
            )
        if case.is_diagnostic:
            raise InvalidBmcEncoding(
                "accepted_cases for %s must not contain diagnostic cases." % helper_name
            )
        if case.target_state_id < 0 or case.target_state_path in _RESERVED_CASE_PATHS:
            raise InvalidBmcEncoding(
                "accepted_cases for %s must target model states." % helper_name
            )
        if case.source_state_id != source.source_state_id:
            raise InvalidBmcEncoding(
                "accepted case source id must match %s source." % helper_name
            )
        if case.source_state_path != source.source_state_path:
            raise InvalidBmcEncoding(
                "accepted case source path must match %s source." % helper_name
            )
    return accepted


@dataclass(frozen=True)
class CycleCase:
    """One macro-step relation case before solver lowering.

    :param kind: Case kind such as ``"transition"``, ``"fallback"``,
        ``"absorb"``, or ``"delta"``.
    :type kind: str
    :param source_state_id: Domain state id of the source boundary.
    :type source_state_id: int
    :param source_state_path: Source path used by the case label.
    :type source_state_path: str
    :param target_state_id: Domain state id of the target boundary.
    :type target_state_id: int
    :param target_state_path: Target path used by the case label.
    :type target_state_path: str
    :param label: Stable label in
        ``source_path::case_kind::target_path::ordinal`` form.
    :type label: str
    :param condition: Bare case condition ``gamma`` without a source guard.
    :type condition: BoolTemplate
    :param var_update: Explicit updates for every persistent variable.
    :type var_update: Tuple[VarUpdate, ...]
    :param used_events: Event inputs read by this case, defaults to ``()``.
    :type used_events: Tuple[EventUse, ...], optional
    :param failed_conditions: Diagnostic-only failed candidate conditions,
        defaults to ``()``.
    :type failed_conditions: Tuple[BoolTemplate, ...], optional
    :param domain: Optional domain used for eager validation, defaults to
        ``None``.
    :type domain: BmcDomain, optional

    :ivar is_diagnostic: Derived diagnostic classification.  It is true for
        ``delta`` cases and diagnostic absorb cases.
    :vartype is_diagnostic: bool

    Example::

        >>> case = CycleCase('transition', 0, 'Root', 0, 'Root', 'Root::transition::Root::0', BoolTemplate.true(), ())
        >>> case.condition.evaluate({})
        True
    """

    kind: str
    source_state_id: int
    source_state_path: str
    target_state_id: int
    target_state_path: str
    label: str
    condition: BoolTemplate
    var_update: Tuple[VarUpdate, ...]
    used_events: Tuple[EventUse, ...] = ()
    failed_conditions: Tuple[BoolTemplate, ...] = ()
    domain: Optional[BmcDomain] = field(default=None, repr=False, compare=False)
    is_diagnostic: bool = field(init=False)

    def __post_init__(self) -> None:
        kind = _validate_choice(self.kind, _CASE_KINDS, "case kind")
        source_id = _validate_index(self.source_state_id, "source_state_id")
        target_id = _validate_index(self.target_state_id, "target_state_id")
        source_path = _require_non_empty_string(
            self.source_state_path,
            "source_state_path",
        )
        target_path = _require_non_empty_string(
            self.target_state_path,
            "target_state_path",
        )
        label = _require_non_empty_string(self.label, "label")
        if not isinstance(self.condition, BoolTemplate):
            raise InvalidBmcEncoding("condition must be BoolTemplate.")
        _validate_non_reserved_condition_atoms(self.condition, "condition")
        used_events = tuple(self.used_events)
        if not all(isinstance(item, EventUse) for item in used_events):
            raise InvalidBmcEncoding("used_events must contain EventUse objects.")
        failed_conditions = tuple(self.failed_conditions)
        if not all(isinstance(item, BoolTemplate) for item in failed_conditions):
            raise InvalidBmcEncoding(
                "failed_conditions must contain BoolTemplate objects."
            )
        var_update = tuple(self.var_update)
        if not all(isinstance(item, VarUpdate) for item in var_update):
            raise InvalidBmcEncoding("var_update must contain VarUpdate objects.")

        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "source_state_id", source_id)
        object.__setattr__(self, "target_state_id", target_id)
        object.__setattr__(self, "source_state_path", source_path)
        object.__setattr__(self, "target_state_path", target_path)
        object.__setattr__(self, "label", label)
        object.__setattr__(
            self,
            "used_events",
            tuple(sorted(used_events, key=_canonical_key)),
        )
        object.__setattr__(
            self,
            "failed_conditions",
            tuple(sorted(failed_conditions, key=_canonical_key)),
        )
        object.__setattr__(
            self,
            "var_update",
            tuple(sorted(var_update, key=lambda item: item.variable_id)),
        )
        object.__setattr__(
            self, "is_diagnostic", _derive_is_diagnostic(kind, target_id)
        )

        self._validate_label()
        self._validate_kind_shape()
        if self.domain is not None:
            if not isinstance(self.domain, BmcDomain):
                raise InvalidBmcEncoding("domain must be BmcDomain.")
            self._validate_against_domain(self.domain)

    def _validate_label(self) -> None:
        parts = self.label.split("::")
        if len(parts) != 4:
            raise InvalidBmcEncoding("label must use source::kind::target::ordinal.")
        source_path, kind, target_path, ordinal = parts
        if source_path != self.source_state_path:
            raise InvalidBmcEncoding("label source path does not match case source.")
        if kind != self.kind:
            raise InvalidBmcEncoding("label case kind does not match case kind.")
        if target_path != self.target_state_path:
            raise InvalidBmcEncoding("label target path does not match case target.")
        if not ordinal or not all("0" <= char <= "9" for char in ordinal):
            raise InvalidBmcEncoding("label ordinal must be a decimal integer.")

    def _validate_kind_shape(self) -> None:
        if self.kind == "absorb":
            if self.source_state_id != self.target_state_id:
                raise InvalidBmcEncoding("absorb cases must self-loop.")
            if self.source_state_id not in {STATE_TERMINATE_ID, STATE_DIAGNOSTIC_ID}:
                raise InvalidBmcEncoding("absorb cases must use sentinel states.")
        if self.kind in {"delta", "diagnostic"}:
            if self.target_state_id != STATE_DIAGNOSTIC_ID:
                raise InvalidBmcEncoding(
                    "diagnostic and delta cases target diagnostic."
                )

    def _validate_against_domain(self, domain: BmcDomain) -> None:
        _validate_case_state(
            domain,
            self.source_state_id,
            self.source_state_path,
            "source",
        )
        _validate_case_state(
            domain,
            self.target_state_id,
            self.target_state_path,
            "target",
        )
        for event_use in self.used_events:
            try:
                event = domain.event_by_id(event_use.event_id)
            except InvalidBmcDomain as err:
                # InvalidBmcDomain: BmcDomain lookup rejects unknown event ids
                # referenced by this case's event-use metadata.
                raise InvalidBmcEncoding(str(err)) from err
            if event.path != event_use.path:
                raise InvalidBmcEncoding("EventUse path does not match event id.")
        object.__setattr__(
            self,
            "var_update",
            build_var_updates(domain, self.var_update),
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable case dictionary.

        :return: Canonical cycle-case dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> case = CycleCase('transition', 0, 'Root', 0, 'Root', 'Root::transition::Root::0', BoolTemplate.true(), ())
            >>> case.to_canonical()['is_diagnostic']
            False
        """
        return {
            "node": "cycle_case",
            "kind": self.kind,
            "source_state_id": self.source_state_id,
            "source_state_path": self.source_state_path,
            "target_state_id": self.target_state_id,
            "target_state_path": self.target_state_path,
            "label": self.label,
            "is_diagnostic": self.is_diagnostic,
            "used_events": [item.to_canonical() for item in self.used_events],
            "condition": self.condition.to_canonical(),
            "var_update": [item.to_canonical() for item in self.var_update],
            "failed_conditions": [
                item.to_canonical() for item in self.failed_conditions
            ],
        }


@dataclass(frozen=True)
class PartitionCheckResult:
    """Summary of a source-local boolean partition self-check.

    :param variables: Boolean atom names enumerated by the truth-table check.
    :type variables: Tuple[str, ...]
    :param assignment_count: Number of assignments checked.
    :type assignment_count: int
    :param bucket_count: Number of partition buckets.
    :type bucket_count: int

    Example::

        >>> PartitionCheckResult(('a',), 2, 2).to_canonical()['assignment_count']
        2
    """

    variables: Tuple[str, ...]
    assignment_count: int
    bucket_count: int

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable partition-check summary.

        :return: Canonical self-check summary.
        :rtype: Dict[str, object]

        Example::

            >>> PartitionCheckResult((), 1, 1).to_canonical()['node']
            'partition_check_result'
        """
        return {
            "node": "partition_check_result",
            "variables": list(self.variables),
            "assignment_count": self.assignment_count,
            "bucket_count": self.bucket_count,
            "scope": "build-time-self-check",
        }


@dataclass(frozen=True)
class MacroStepFormal:
    """Source-local macro-step case buckets.

    :param source: Source profile that produced these buckets.
    :type source: MacroStepSource
    :param success_cases: Ordinary relation cases such as transitions,
        fallbacks, and absorbs.
    :type success_cases: Tuple[CycleCase, ...]
    :param delta_cases: Semantic delta relation cases, defaults to ``()``.
    :type delta_cases: Tuple[CycleCase, ...], optional
    :param build_diagnostic_conditions: Build/encoder diagnostic conditions,
        defaults to ``()``.
    :type build_diagnostic_conditions: Tuple[BoolTemplate, ...], optional

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.macro import MacroStepFormal, terminated_absorb_case
        >>> from pyfcstm.bmc.source import terminated_source
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> formal = MacroStepFormal(terminated_source(domain), (terminated_absorb_case(domain),))
        >>> formal.cases[0].kind
        'absorb'
    """

    source: MacroStepSource
    success_cases: Tuple[CycleCase, ...]
    delta_cases: Tuple[CycleCase, ...] = ()
    build_diagnostic_conditions: Tuple[BoolTemplate, ...] = ()

    def __post_init__(self) -> None:
        if not isinstance(self.source, MacroStepSource):
            raise InvalidBmcEncoding("source must be MacroStepSource.")
        if not isinstance(self.success_cases, (list, tuple)):
            raise InvalidBmcEncoding("success_cases must be a sequence.")
        if not isinstance(self.delta_cases, (list, tuple)):
            raise InvalidBmcEncoding("delta_cases must be a sequence.")
        if not isinstance(self.build_diagnostic_conditions, (list, tuple)):
            raise InvalidBmcEncoding("build_diagnostic_conditions must be a sequence.")
        success_cases = tuple(self.success_cases)
        delta_cases = tuple(self.delta_cases)
        diagnostics = tuple(self.build_diagnostic_conditions)
        if not all(isinstance(item, CycleCase) for item in success_cases):
            raise InvalidBmcEncoding("success_cases must contain CycleCase objects.")
        if not all(isinstance(item, CycleCase) for item in delta_cases):
            raise InvalidBmcEncoding("delta_cases must contain CycleCase objects.")
        if not all(isinstance(item, BoolTemplate) for item in diagnostics):
            raise InvalidBmcEncoding(
                "build_diagnostic_conditions must contain BoolTemplate objects."
            )
        success_cases = tuple(sorted(success_cases, key=lambda item: item.label))
        delta_cases = tuple(sorted(delta_cases, key=lambda item: item.label))
        diagnostics = tuple(sorted(diagnostics, key=_canonical_key))
        object.__setattr__(self, "success_cases", success_cases)
        object.__setattr__(self, "delta_cases", delta_cases)
        object.__setattr__(self, "build_diagnostic_conditions", diagnostics)
        self._validate_buckets()

    @property
    def cases(self) -> Tuple[CycleCase, ...]:
        """Return ordinary and delta relation cases in stable order.

        :return: ``success_cases + delta_cases``.
        :rtype: Tuple[CycleCase, ...]

        Example::

            >>> source = MacroStepSource('entry', 'initial', 0, 'Root')
            >>> MacroStepFormal(source, (), ()).cases
            Traceback (most recent call last):
            ...
            pyfcstm.bmc.errors.InvalidBmcEncoding: MacroStepFormal must contain at least one relation case.
        """
        return self.success_cases + self.delta_cases

    def _validate_buckets(self) -> None:
        if not self.success_cases and not self.delta_cases:
            raise InvalidBmcEncoding(
                "MacroStepFormal must contain at least one relation case."
            )
        labels = set()
        for case in self.cases:
            if case.label in labels:
                raise InvalidBmcEncoding("Duplicate cycle case label: %r." % case.label)
            labels.add(case.label)
            if case.source_state_id != self.source.source_state_id:
                raise InvalidBmcEncoding("case source id must match formal source.")
            if case.source_state_path != self.source.source_state_path:
                raise InvalidBmcEncoding("case source path must match formal source.")
            self._validate_case_domain_contract(case)
        for case in self.success_cases:
            if case.kind == "delta":
                raise InvalidBmcEncoding("success_cases must not contain delta cases.")
            self._validate_success_case_shape(case)
        if self.delta_cases and not self.source.allows_semantic_delta:
            raise InvalidBmcEncoding("delta_cases require an entry source.")
        if self.source.kind != "entry" and self.build_diagnostic_conditions:
            raise InvalidBmcEncoding(
                "build diagnostics are only recorded on entry source formals."
            )
        if self.source.kind == "stable_leaf":
            if not any(case.kind == "fallback" for case in self.success_cases):
                raise InvalidBmcEncoding("stable leaf formal requires a fallback case.")
        if self.source.kind == "terminated":
            self._validate_sentinel_absorb(STATE_TERMINATE_ID)
        if self.source.kind == "diagnostic":
            self._validate_sentinel_absorb(STATE_DIAGNOSTIC_ID)
        for case in self.delta_cases:
            if case.kind != "delta":
                raise InvalidBmcEncoding("delta_cases may only contain delta cases.")

    def _validate_case_domain_contract(self, case: CycleCase) -> None:
        if self.source.domain is not None:
            case._validate_against_domain(self.source.domain)

    def _validate_success_case_shape(self, case: CycleCase) -> None:
        if self.source.kind == "stable_leaf":
            if case.kind not in {"transition", "fallback"}:
                raise InvalidBmcEncoding(
                    "stable leaf success cases may only be transition or fallback."
                )
            if (
                case.target_state_id < 0
                or case.target_state_path in _RESERVED_CASE_PATHS
            ):
                raise InvalidBmcEncoding(
                    "stable leaf success cases must target model states."
                )
            if case.kind == "fallback" and (
                case.target_state_id != self.source.source_state_id
                or case.target_state_path != self.source.source_state_path
            ):
                raise InvalidBmcEncoding("fallback cases must self-loop source.")
        elif self.source.kind == "entry":
            if case.kind not in {"transition", "initial", "diagnostic"}:
                raise InvalidBmcEncoding(
                    "entry success cases may only be transition, initial, or diagnostic."
                )
            if case.kind in {"transition", "initial"} and (
                case.target_state_id < 0
                or case.target_state_path in _RESERVED_CASE_PATHS
            ):
                raise InvalidBmcEncoding(
                    "entry transition and initial cases must target model states."
                )

    def _validate_sentinel_absorb(self, sentinel_id: int) -> None:
        if self.delta_cases:
            raise InvalidBmcEncoding("sentinel absorb formals cannot have delta cases.")
        if len(self.success_cases) != 1:
            raise InvalidBmcEncoding("sentinel absorb formal must contain one case.")
        case = self.success_cases[0]
        if case.kind != "absorb":
            raise InvalidBmcEncoding("sentinel formal case must be absorb.")
        if case.source_state_id != sentinel_id or case.target_state_id != sentinel_id:
            raise InvalidBmcEncoding("sentinel absorb case must self-loop sentinel id.")

    def verify_partition(
        self,
        max_assignments: int = 4096,
    ) -> PartitionCheckResult:
        """Verify local case buckets with the truth-table self-checker.

        :param max_assignments: Maximum assignments to enumerate, defaults to
            ``4096``.
        :type max_assignments: int, optional
        :return: Partition self-check summary.
        :rtype: PartitionCheckResult
        :raises BmcBuildError: If the buckets overlap, leave a gap, or cannot
            be checked within the assignment budget.

        Example::

            >>> source = MacroStepSource('entry', 'initial', 0, 'Root')
            >>> case = CycleCase('delta', 0, 'Root', -2, '__diagnostic__', 'Root::delta::__diagnostic__::0', BoolTemplate.true(), ())
            >>> MacroStepFormal(source, (), (case,)).verify_partition().bucket_count
            1
        """
        return verify_source_partition(
            self.source,
            self.success_cases,
            self.delta_cases,
            self.build_diagnostic_conditions,
            max_assignments=max_assignments,
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable formal dictionary.

        :return: Canonical macro-step formal.
        :rtype: Dict[str, object]

        Example::

            >>> source = MacroStepSource('entry', 'initial', 0, 'Root')
            >>> case = CycleCase('delta', 0, 'Root', -2, '__diagnostic__', 'Root::delta::__diagnostic__::0', BoolTemplate.true(), ())
            >>> MacroStepFormal(source, (), (case,)).to_canonical()['source']['kind']
            'entry'
        """
        return {
            "node": "macro_step_formal",
            "source": self.source.to_canonical(),
            "success_cases": [case.to_canonical() for case in self.success_cases],
            "delta_cases": [case.to_canonical() for case in self.delta_cases],
            "build_diagnostic_conditions": [
                item.to_canonical() for item in self.build_diagnostic_conditions
            ],
        }


def case_antecedent_condition(case: CycleCase) -> BoolTemplate:
    """Return ``source_guard and gamma`` for diagnostic comparison.

    The returned recipe mirrors the later relation-builder boundary but
    is still solver-independent.  It proves that the source guard is composed
    outside :attr:`CycleCase.condition`.  Source guards use the reserved
    ``"__source_state__:"`` atom namespace so synthetic case conditions cannot
    collide with the helper's guard atom.

    :param case: Case whose antecedent should be represented.
    :type case: CycleCase
    :return: Source-guarded antecedent recipe.
    :rtype: BoolTemplate
    :raises InvalidBmcEncoding: If ``case`` is not a cycle case.

    Example::

        >>> case = CycleCase(
        ...     'transition', 0, 'Root', 0, 'Root',
        ...     'Root::transition::Root::0', BoolTemplate.atom('g'), ()
        ... )
        >>> case_antecedent_condition(case).variables
        ('__source_state__:0', 'g')
    """
    if not isinstance(case, CycleCase):
        raise InvalidBmcEncoding("case must be CycleCase.")
    return BoolTemplate.and_(
        BoolTemplate.atom("%s%d" % (_SOURCE_STATE_ATOM_PREFIX, case.source_state_id)),
        case.condition,
    )


def terminated_absorb_case(domain: BmcDomain) -> CycleCase:
    """Build the terminate sentinel absorb case.

    :param domain: Domain snapshot whose sentinel and variables are used.
    :type domain: BmcDomain
    :return: Terminated self-loop absorb case.
    :rtype: CycleCase

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> terminated_absorb_case(domain).is_diagnostic
        False
    """
    return CycleCase(
        "absorb",
        STATE_TERMINATE_ID,
        TERMINATE_CASE_PATH,
        STATE_TERMINATE_ID,
        TERMINATE_CASE_PATH,
        "%s::absorb::%s::0" % (TERMINATE_CASE_PATH, TERMINATE_CASE_PATH),
        BoolTemplate.true(),
        carry_var_updates(domain),
        domain=domain,
    )


def diagnostic_absorb_case(domain: BmcDomain) -> CycleCase:
    """Build the diagnostic sentinel absorb case.

    :param domain: Domain snapshot whose sentinel and variables are used.
    :type domain: BmcDomain
    :return: Diagnostic self-loop absorb case.
    :rtype: CycleCase

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> diagnostic_absorb_case(domain).is_diagnostic
        True
    """
    return CycleCase(
        "absorb",
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        "%s::absorb::%s::0" % (DIAGNOSTIC_CASE_PATH, DIAGNOSTIC_CASE_PATH),
        BoolTemplate.true(),
        carry_var_updates(domain),
        domain=domain,
    )


def _case_label(source_path: str, kind: str, target_path: str, ordinal: int) -> str:
    return "%s::%s::%s::%d" % (source_path, kind, target_path, ordinal)


def build_fallback_case(
    domain: BmcDomain,
    source: MacroStepSource,
    accepted_cases: Sequence[CycleCase],
    failed_conditions: Sequence[BoolTemplate] = (),
    ordinal: int = 0,
) -> CycleCase:
    """Build a stable leaf fallback self-cycle.

    The fallback condition negates only accepted case conditions.  Failed
    candidate conditions are copied as metadata and do not shrink the fallback
    region.

    :param domain: Domain snapshot whose variables are carried.
    :type domain: BmcDomain
    :param source: Stable leaf source.
    :type source: MacroStepSource
    :param accepted_cases: Accepted transition cases for the same stable leaf
        source.
    :type accepted_cases: Sequence[CycleCase]
    :param failed_conditions: Diagnostic-only failed conditions, defaults to
        ``()``.
    :type failed_conditions: Sequence[BoolTemplate], optional
    :param ordinal: Label ordinal, defaults to ``0``.
    :type ordinal: int, optional
    :return: Fallback case.
    :rtype: CycleCase
    :raises InvalidBmcEncoding: If ``source`` is not a stable leaf source.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.source import stable_leaf_source
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> source = stable_leaf_source(domain, 'Root')
        >>> build_fallback_case(domain, source, ()).condition.evaluate({})
        True
    """
    if not isinstance(source, MacroStepSource) or source.kind != "stable_leaf":
        raise InvalidBmcEncoding("fallback case requires a stable_leaf source.")
    ordinal = _validate_index(ordinal, "ordinal")
    if ordinal < 0:
        raise InvalidBmcEncoding("ordinal must be non-negative.")
    accepted = _normalize_accepted_cases(
        accepted_cases,
        source,
        "fallback",
        ("transition",),
    )
    if not isinstance(failed_conditions, (list, tuple)):
        raise InvalidBmcEncoding("failed_conditions must be a sequence.")
    failed = tuple(failed_conditions)
    if not all(isinstance(item, BoolTemplate) for item in failed):
        raise InvalidBmcEncoding("failed_conditions must contain BoolTemplate objects.")
    if accepted:
        condition = BoolTemplate.not_(
            BoolTemplate.or_(*[case.condition for case in accepted])
        )
    else:
        condition = BoolTemplate.true()
    return CycleCase(
        "fallback",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        _case_label(
            source.source_state_path,
            "fallback",
            source.source_state_path,
            ordinal,
        ),
        condition,
        carry_var_updates(domain),
        failed_conditions=failed,
        domain=domain,
    )


def build_semantic_delta_case(
    domain: BmcDomain,
    source: MacroStepSource,
    accepted_cases: Sequence[CycleCase],
    build_diagnostic_conditions: Sequence[BoolTemplate] = (),
    failed_conditions: Sequence[BoolTemplate] = (),
    ordinal: int = 0,
) -> CycleCase:
    """Build a non-stoppable entry uncovered-region delta case.

    The delta condition negates accepted case conditions and build-diagnostic
    conditions.  Failed candidate conditions are copied as metadata only.

    :param domain: Domain snapshot whose variables are carried.
    :type domain: BmcDomain
    :param source: Initial entry source.
    :type source: MacroStepSource
    :param accepted_cases: Accepted transition or initial success cases for the
        same entry source.
    :type accepted_cases: Sequence[CycleCase]
    :param build_diagnostic_conditions: Build diagnostic conditions excluded
        from semantic delta, defaults to ``()``.
    :type build_diagnostic_conditions: Sequence[BoolTemplate], optional
    :param failed_conditions: Diagnostic-only failed candidate conditions,
        defaults to ``()``.
    :type failed_conditions: Sequence[BoolTemplate], optional
    :param ordinal: Label ordinal, defaults to ``0``.
    :type ordinal: int, optional
    :return: Semantic delta case targeting the diagnostic sentinel.
    :rtype: CycleCase
    :raises InvalidBmcEncoding: If ``source`` does not allow semantic delta.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.source import entry_source
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> case = build_semantic_delta_case(domain, entry_source(domain), ())
        >>> case.target_state_id
        -2
    """
    if not isinstance(source, MacroStepSource) or not source.allows_semantic_delta:
        raise InvalidBmcEncoding("semantic delta case requires an entry source.")
    ordinal = _validate_index(ordinal, "ordinal")
    if ordinal < 0:
        raise InvalidBmcEncoding("ordinal must be non-negative.")
    accepted = _normalize_accepted_cases(
        accepted_cases,
        source,
        "delta",
        ("transition", "initial"),
    )
    if not isinstance(build_diagnostic_conditions, (list, tuple)):
        raise InvalidBmcEncoding("build_diagnostic_conditions must be a sequence.")
    diagnostics = tuple(build_diagnostic_conditions)
    if not all(isinstance(item, BoolTemplate) for item in diagnostics):
        raise InvalidBmcEncoding(
            "build_diagnostic_conditions must contain BoolTemplate objects."
        )
    if not isinstance(failed_conditions, (list, tuple)):
        raise InvalidBmcEncoding("failed_conditions must be a sequence.")
    failed = tuple(failed_conditions)
    if not all(isinstance(item, BoolTemplate) for item in failed):
        raise InvalidBmcEncoding("failed_conditions must contain BoolTemplate objects.")
    excluded = [case.condition for case in accepted]
    excluded.extend(diagnostics)
    if excluded:
        condition = BoolTemplate.not_(BoolTemplate.or_(*excluded))
    else:
        condition = BoolTemplate.true()
    return CycleCase(
        "delta",
        source.source_state_id,
        source.source_state_path,
        STATE_DIAGNOSTIC_ID,
        DIAGNOSTIC_CASE_PATH,
        _case_label(
            source.source_state_path,
            "delta",
            DIAGNOSTIC_CASE_PATH,
            ordinal,
        ),
        condition,
        carry_var_updates(domain),
        failed_conditions=failed,
        domain=domain,
    )


def verify_boolean_partition(
    buckets: Sequence[BoolTemplate],
    variables: Optional[Sequence[str]] = None,
    max_assignments: int = 4096,
) -> PartitionCheckResult:
    """Verify that boolean buckets are complete and pairwise disjoint.

    This helper is deliberately a self-check.  It enumerates a small synthetic
    boolean universe and raises :class:`BmcBuildError` on gaps, overlaps, or an
    assignment budget overflow.  It returns only a summary and never returns
    solver clauses.

    :param buckets: Boolean bucket conditions.
    :type buckets: Sequence[BoolTemplate]
    :param variables: Optional explicit universe variables, defaults to the
        union of bucket atoms.
    :type variables: Sequence[str], optional
    :param max_assignments: Maximum truth-table assignments, defaults to
        ``4096``.
    :type max_assignments: int, optional
    :return: Partition self-check summary.
    :rtype: PartitionCheckResult
    :raises BmcBuildError: If the partition is not exactly-one or cannot be
        checked.

    Example::

        >>> a = BoolTemplate.atom('a')
        >>> verify_boolean_partition((a, BoolTemplate.not_(a))).assignment_count
        2
    """
    if not isinstance(buckets, (list, tuple)):
        raise BmcBuildError("partition buckets must be a sequence.")
    items = tuple(buckets)
    if not items:
        raise BmcBuildError("partition must contain at least one bucket.")
    if not all(isinstance(item, BoolTemplate) for item in items):
        raise BmcBuildError("partition buckets must be BoolTemplate objects.")
    if isinstance(max_assignments, bool) or not isinstance(max_assignments, int):
        raise BmcBuildError("max_assignments must be a positive integer.")
    if max_assignments <= 0:
        raise BmcBuildError("max_assignments must be a positive integer.")

    if variables is None:
        names = sorted(
            set(itertools.chain.from_iterable(item.variables for item in items))
        )
    else:
        if not isinstance(variables, (list, tuple)):
            raise BmcBuildError("partition variables must be a sequence.")
        raw_names = tuple(variables)
        if not all(isinstance(name, str) and name for name in raw_names):
            raise BmcBuildError("partition variables must be non-empty strings.")
        names = sorted(set(raw_names))
    assignment_count = 2 ** len(names)
    if assignment_count > max_assignments:
        raise BmcBuildError("partition check exceeded assignment budget.")

    gaps = []
    overlaps = []
    for values in itertools.product((False, True), repeat=len(names)):
        assignment = dict(zip(names, values))
        true_indexes = [
            index for index, item in enumerate(items) if item.evaluate(assignment)
        ]
        if len(true_indexes) != 1:
            if true_indexes:
                overlaps.append((assignment, true_indexes))
            else:
                gaps.append(assignment)
    if overlaps or gaps:
        parts = []
        if overlaps:
            assignment, true_indexes = overlaps[0]
            parts.append("overlap at assignment %r: %r" % (assignment, true_indexes))
        if gaps:
            parts.append("gap at assignment %r" % gaps[0])
        raise BmcBuildError("partition violation: %s." % "; ".join(parts))
    return PartitionCheckResult(tuple(names), assignment_count, len(items))


def verify_source_partition(
    source: MacroStepSource,
    success_cases: Sequence[CycleCase],
    delta_cases: Sequence[CycleCase] = (),
    build_diagnostic_conditions: Sequence[BoolTemplate] = (),
    max_assignments: int = 4096,
) -> PartitionCheckResult:
    """Verify one source's local case partition.

    Build-diagnostic conditions form one extra local bucket.  That bucket must
    be disjoint from every success and delta case, and the combined buckets must
    still cover the whole synthetic boolean universe.

    :param source: Macro-step source profile.
    :type source: MacroStepSource
    :param success_cases: Ordinary success cases.
    :type success_cases: Sequence[CycleCase]
    :param delta_cases: Semantic delta cases, defaults to ``()``.
    :type delta_cases: Sequence[CycleCase], optional
    :param build_diagnostic_conditions: Build diagnostic conditions, defaults
        to ``()``.
    :type build_diagnostic_conditions: Sequence[BoolTemplate], optional
    :param max_assignments: Maximum truth-table assignments, defaults to
        ``4096``.
    :type max_assignments: int, optional
    :return: Partition self-check summary.
    :rtype: PartitionCheckResult
    :raises BmcBuildError: If the buckets are not complete and disjoint.
    :raises InvalidBmcEncoding: If delta cases are used for a source that does
        not allow semantic delta.

    Example::

        >>> source = MacroStepSource('entry', 'initial', 0, 'Root')
        >>> delta = CycleCase(
        ...     'delta', 0, 'Root', -2, '__diagnostic__',
        ...     'Root::delta::__diagnostic__::0', BoolTemplate.true(), ()
        ... )
        >>> verify_source_partition(source, (), (delta,)).bucket_count
        1
    """
    if not isinstance(source, MacroStepSource):
        raise InvalidBmcEncoding("source must be MacroStepSource.")
    if not isinstance(success_cases, (list, tuple)):
        raise InvalidBmcEncoding("success_cases must be a sequence.")
    if not isinstance(delta_cases, (list, tuple)):
        raise InvalidBmcEncoding("delta_cases must be a sequence.")
    if not isinstance(build_diagnostic_conditions, (list, tuple)):
        raise InvalidBmcEncoding("build_diagnostic_conditions must be a sequence.")
    success = tuple(success_cases)
    delta = tuple(delta_cases)
    diagnostics = tuple(build_diagnostic_conditions)
    if delta and not source.allows_semantic_delta:
        raise InvalidBmcEncoding("delta cases require an entry source.")
    for case in success + delta:
        if not isinstance(case, CycleCase):
            raise InvalidBmcEncoding("partition cases must be CycleCase objects.")
        if case.source_state_id != source.source_state_id:
            raise InvalidBmcEncoding("partition case source id mismatch.")
        if case.source_state_path != source.source_state_path:
            raise InvalidBmcEncoding("partition case source path mismatch.")
    for case in success:
        if case.kind == "delta":
            raise InvalidBmcEncoding("success_cases must not contain delta cases.")
    for case in delta:
        if case.kind != "delta":
            raise InvalidBmcEncoding("delta_cases may only contain delta cases.")
    if not all(isinstance(item, BoolTemplate) for item in diagnostics):
        raise InvalidBmcEncoding(
            "build_diagnostic_conditions must contain BoolTemplate objects."
        )
    buckets = [case.condition for case in success]
    buckets.extend(case.condition for case in delta)
    if diagnostics:
        buckets.append(BoolTemplate.or_(*diagnostics))
    return verify_boolean_partition(buckets, max_assignments=max_assignments)


__all__ = [
    "BoolTemplate",
    "EventUse",
    "VarUpdate",
    "CycleCase",
    "PartitionCheckResult",
    "MacroStepFormal",
    "carry_var_updates",
    "var_update_for",
    "build_var_updates",
    "case_antecedent_condition",
    "terminated_absorb_case",
    "diagnostic_absorb_case",
    "build_fallback_case",
    "build_semantic_delta_case",
    "verify_boolean_partition",
    "verify_source_partition",
]

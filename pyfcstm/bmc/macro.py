"""Macro-step case contracts for FCSTM bounded model checking.

The macro contract layer defines the solver-independent data objects exchanged
between runtime-aligned macro-step expansion and later relation lowering.  It
records **which flat control path** a macro-step can take: source/target state
ids, event/guard control atoms, priority exclusions expressed through accepted
case labels, and the ordered model action blocks that would execute on that
path.  It deliberately does not lower operations into variable writeback
expressions, split action-local ``if`` blocks, or construct Z3 implications.

Design contracts:

* :class:`CycleCase.condition` contains only control-path atoms.  Valid atom
  prefixes are ``event:``, ``guard:``, and ``accepted:``; action-local control
  flow and variable writeback constraints belong to later lowering.
* :class:`GuardRequirement` stores the raw model guard plus the action-block
  anchor at which that guard is checked.  Later lowering interleaves action
  lowering and guard lowering instead of substituting guards in this layer.
* :class:`ActionBlock` preserves runtime action block boundaries and operation
  statement objects.  A block may contain an :class:`pyfcstm.model.IfBlock`, but
  that nested branch is not part of the case condition.
* :class:`PriorityExclusion` records declaration-order masks through
  ``accepted:<case_label>`` atoms.  The accepted atom denotes the already lowered
  antecedent of a prior accepted path, not a raw event or guard trigger.
* Partition verification is a build-time/test-time self-check.  It first accepts
  structural accepted/fallback masks that are disjoint by construction, then
  falls back to a bounded truth-table checker for small non-canonical shapes. It
  never produces clauses for ``Core_N`` or ``Phi_N``.

The module contains:

* :class:`BoolTemplate` - A small boolean recipe used by contract tests and
  partition self-checks.
* :class:`EventUse`, :class:`GuardRequirement`, :class:`ActionBlock`, and
  :class:`PriorityExclusion` - Metadata for the flat macro-step path plan.
* :class:`CycleCase` - One macro-step relation case before solver lowering.
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
from typing import Any, Dict, List, Mapping, Optional, Sequence, Set, Tuple

from pyfcstm.bmc.domain import STATE_INIT_ID, STATE_TERMINATE_ID, BmcDomain
from pyfcstm.bmc.errors import BmcBuildError, InvalidBmcDomain, InvalidBmcEncoding
from pyfcstm.bmc.source import (
    INIT_CASE_PATH,
    TERMINATE_CASE_PATH,
    MacroStepSource,
)
from pyfcstm.model import Expr, IfBlock, Operation, OperationStatement

_CanonicalDict = Dict[str, Any]
_BOOL_KINDS = {"true", "false", "atom", "not", "and", "or"}
_CASE_KINDS = {"transition", "fallback", "initial", "absorb", "delta"}
_ACCEPTED_CASE_KINDS = {"transition", "initial"}
_EVENT_POLARITIES = {"positive", "negative"}
_EVENT_REASONS = {"trigger", "priority", "fallback", "descent", "assumption"}
_GUARD_POLARITIES = {"positive", "negative"}
_GUARD_REASONS = {
    "transition_guard",
    "initial_guard",
    "pseudo_guard",
    "parent_continuation_guard",
    "priority",
    "fallback",
    "delta_exclusion",
}
_PRIORITY_REASONS = {"transition_priority", "initial_priority", "fallback", "delta"}
_ACTION_BLOCK_KINDS = {"state_action", "aspect_action", "transition_effect"}
_ACTION_RUNTIME_ROLES = {
    "state_enter",
    "state_exit",
    "leaf_during",
    "plain_during_before",
    "plain_during_after",
    "aspect_during_before",
    "aspect_during_after",
    "transition_effect",
}
_RESERVED_CASE_PATHS = {INIT_CASE_PATH, TERMINATE_CASE_PATH}
_SOURCE_STATE_ATOM_PREFIX = "__source_state__:"
_EVENT_ATOM_PREFIX = "event:"
_GUARD_ATOM_PREFIX = "guard:"
_ACCEPTED_ATOM_PREFIX = "accepted:"
_VALID_CONDITION_PREFIXES = (
    _EVENT_ATOM_PREFIX,
    _GUARD_ATOM_PREFIX,
    _ACCEPTED_ATOM_PREFIX,
)


def _internal_bmc_error(detail: str) -> BmcBuildError:
    return BmcBuildError(
        "internal error: %s This indicates a pyfcstm BMC bug or a corrupted "
        "internal object; please report this issue with the FCSTM input, BMC "
        "query or expansion source, and traceback at "
        "https://github.com/HansBug/pyfcstm/issues." % detail
    )


def _require_non_empty_string(value: object, field_name: str) -> str:
    if not isinstance(value, str) or not value:
        raise InvalidBmcEncoding("%s must be a non-empty string." % field_name)
    return value


def _validate_index(value: object, field_name: str) -> int:
    if isinstance(value, bool) or not isinstance(value, int):
        raise InvalidBmcEncoding("%s must be an integer." % field_name)
    return value


def _validate_choice(value: object, choices: Set[str], field_name: str) -> str:
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

    ``BoolTemplate`` intentionally supports only constants, atoms, ``not``,
    ``and``, and ``or``.  That is enough for macro contract checks while later
    solver lowering can map the recorded event, guard, and accepted atoms into
    Z3 formulas.

    :param kind: ``"true"``, ``"false"``, ``"atom"``, ``"not"``,
        ``"and"``, or ``"or"``.
    :type kind: str
    :param name: Atom name for ``kind="atom"``, defaults to ``None``.
    :type name: str, optional
    :param operands: Child boolean templates for composite nodes, defaults to
        an empty tuple.
    :type operands: Tuple[BoolTemplate, ...], optional

    Example::

        >>> gamma = BoolTemplate.atom('event:Root.Go')
        >>> BoolTemplate.not_(gamma).evaluate({'event:Root.Go': False})
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

            >>> BoolTemplate.atom('guard:g0').variables
            ('guard:g0',)
        """
        return cls("atom", name=name)

    @classmethod
    def not_(cls, operand: "BoolTemplate") -> "BoolTemplate":
        """Return logical negation of ``operand``.

        :param operand: Operand condition.
        :type operand: BoolTemplate
        :return: Negated condition with simple identities reduced.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.not_(BoolTemplate.false()).evaluate({})
            True
        """
        if not isinstance(operand, BoolTemplate):
            raise InvalidBmcEncoding("operand must be BoolTemplate.")
        if operand.kind == "true":
            return cls.false()
        if operand.kind == "false":
            return cls.true()
        if operand.kind == "not":
            return operand.operands[0]
        return cls("not", operands=(operand,))

    @classmethod
    def and_(cls, *operands: "BoolTemplate") -> "BoolTemplate":
        """Return logical conjunction of ``operands``.

        :param operands: Operand conditions.
        :type operands: BoolTemplate
        :return: Reduced conjunction, or constant true for an empty input.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.and_().evaluate({})
            True
        """
        if not operands:
            return cls.true()
        if not all(isinstance(item, BoolTemplate) for item in operands):
            raise InvalidBmcEncoding("operands must contain BoolTemplate objects.")
        flattened = []
        pending = list(operands)
        while pending:
            operand = pending.pop(0)
            if operand.kind == "false":
                return cls.false()
            if operand.kind == "true":
                continue
            if operand.kind == "and":
                pending[:0] = operand.operands
            else:
                flattened.append(operand)
        by_key = {_canonical_key(item): item for item in flattened}
        reduced = tuple(by_key[key] for key in sorted(by_key))
        if not reduced:
            return cls.true()
        if len(reduced) == 1:
            return reduced[0]
        return cls("and", operands=reduced)

    @classmethod
    def or_(cls, *operands: "BoolTemplate") -> "BoolTemplate":
        """Return logical disjunction of ``operands``.

        :param operands: Operand conditions.
        :type operands: BoolTemplate
        :return: Reduced disjunction, or constant false for an empty input.
        :rtype: BoolTemplate

        Example::

            >>> BoolTemplate.or_().evaluate({})
            False
        """
        if not operands:
            return cls.false()
        if not all(isinstance(item, BoolTemplate) for item in operands):
            raise InvalidBmcEncoding("operands must contain BoolTemplate objects.")
        flattened = []
        pending = list(operands)
        while pending:
            operand = pending.pop(0)
            if operand.kind == "true":
                return cls.true()
            if operand.kind == "false":
                continue
            if operand.kind == "or":
                pending[:0] = operand.operands
            else:
                flattened.append(operand)
        by_key = {_canonical_key(item): item for item in flattened}
        reduced = tuple(by_key[key] for key in sorted(by_key))
        if not reduced:
            return cls.false()
        if len(reduced) == 1:
            return reduced[0]
        return cls("or", operands=reduced)

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
            return (self._atom_name(),)
        values = set()
        for operand in self.operands:
            values.update(operand.variables)
        return tuple(sorted(values))

    def _atom_name(self) -> str:
        name = self.name
        if name is None:
            raise _internal_bmc_error(
                "atom template is missing a name."
            )  # pragma: no cover
        return name

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
            name = self._atom_name()
            if name not in values:
                raise BmcBuildError("missing boolean assignment for %r." % name)
            value = values[name]
            if not isinstance(value, bool):
                raise BmcBuildError("boolean assignment %r must be bool." % name)
            return value
        if self.kind == "not":
            return not self.operands[0].evaluate(values)
        if self.kind == "and":
            return all(operand.evaluate(values) for operand in self.operands)
        if self.kind == "or":
            return any(operand.evaluate(values) for operand in self.operands)
        raise _internal_bmc_error(  # pragma: no cover
            "unsupported boolean template kind while evaluating: %r." % self.kind
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable condition recipe.

        :return: Canonical condition dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> BoolTemplate.atom('guard:g0').to_canonical()['name']
            'guard:g0'
        """
        result = {"node": "bool_template", "kind": self.kind}  # type: _CanonicalDict
        if self.kind == "atom":
            result["name"] = self._atom_name()
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
            self, "path", _require_non_empty_string(self.path, "event path")
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
class GuardRequirement:
    """Raw transition guard requirement anchored to an action-block prefix.

    :param requirement_id: Stable per-formal guard requirement id.
    :type requirement_id: str
    :param owner_state_id: Domain id of the state whose chooser owns the guard.
    :type owner_state_id: int
    :param owner_state_path: Dot-separated owner state path.
    :type owner_state_path: str
    :param transition_label: Human-readable transition label.
    :type transition_label: str
    :param expr: Raw model expression evaluated by the runtime guard check.
    :type expr: pyfcstm.model.Expr
    :param polarity: Guard polarity, normally ``"positive"``.
    :type polarity: str
    :param reason: Guard-use reason such as ``"transition_guard"``.
    :type reason: str
    :param after_action_block_index: Number of action blocks that have executed
        before the guard is checked.
    :type after_action_block_index: int

    Example::

        >>> from pyfcstm.model.expr import Boolean
        >>> GuardRequirement('g0', 0, 'Root', 'Root -> A', Boolean(True), 'positive', 'transition_guard', 0).atom_name
        'guard:g0'
    """

    requirement_id: str
    owner_state_id: int
    owner_state_path: str
    transition_label: str
    expr: Expr
    polarity: str
    reason: str
    after_action_block_index: int

    def __post_init__(self) -> None:
        owner_state_id = _validate_index(self.owner_state_id, "owner_state_id")
        if owner_state_id < 0:
            raise InvalidBmcEncoding("owner_state_id must be non-negative.")
        if not isinstance(self.expr, Expr):
            raise InvalidBmcEncoding("guard requirement expr must be Expr.")
        anchor = _validate_index(
            self.after_action_block_index, "after_action_block_index"
        )
        if anchor < 0:
            raise InvalidBmcEncoding("after_action_block_index must be non-negative.")
        object.__setattr__(
            self,
            "requirement_id",
            _require_non_empty_string(self.requirement_id, "requirement_id"),
        )
        object.__setattr__(self, "owner_state_id", owner_state_id)
        object.__setattr__(
            self,
            "owner_state_path",
            _require_non_empty_string(self.owner_state_path, "owner_state_path"),
        )
        object.__setattr__(
            self,
            "transition_label",
            _require_non_empty_string(self.transition_label, "transition_label"),
        )
        object.__setattr__(
            self,
            "polarity",
            _validate_choice(self.polarity, _GUARD_POLARITIES, "guard polarity"),
        )
        object.__setattr__(
            self,
            "reason",
            _validate_choice(self.reason, _GUARD_REASONS, "guard reason"),
        )
        object.__setattr__(self, "after_action_block_index", anchor)

    @property
    def atom_name(self) -> str:
        """Return the boolean atom name for this guard.

        :return: Atom name in the ``guard:<id>`` namespace.
        :rtype: str

        Example::

            >>> from pyfcstm.model.expr import Boolean
            >>> GuardRequirement('g0', 0, 'Root', 't', Boolean(True), 'positive', 'transition_guard', 0).atom_name
            'guard:g0'
        """
        return "%s%s" % (_GUARD_ATOM_PREFIX, self.requirement_id)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable guard requirement dictionary.

        :return: Canonical guard requirement metadata.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.model.expr import Boolean
            >>> GuardRequirement('g0', 0, 'Root', 't', Boolean(True), 'positive', 'transition_guard', 0).to_canonical()['atom']
            'guard:g0'
        """
        return {
            "node": "guard_requirement",
            "requirement_id": self.requirement_id,
            "atom": self.atom_name,
            "owner_state_id": self.owner_state_id,
            "owner_state_path": self.owner_state_path,
            "transition_label": self.transition_label,
            "expr": _expr_to_text(self.expr),
            "polarity": self.polarity,
            "reason": self.reason,
            "after_action_block_index": self.after_action_block_index,
        }


@dataclass(frozen=True)
class PriorityExclusion:
    """Priority mask that excludes previously accepted control paths.

    The event and guard-id fields are explanation metadata for the excluded
    accepted cases. They do not add conjuncts to the case condition. Lowering
    code must treat ``excluded_condition`` and ``CycleCase.condition`` as the
    truth sources and use the metadata only
    for witness/debug completeness.

    :param decision_id: Stable id for the chooser decision point.
    :type decision_id: str
    :param reason: Exclusion reason such as ``"transition_priority"``.
    :type reason: str
    :param excluded_case_labels: Case labels excluded by this mask.
    :type excluded_case_labels: Tuple[str, ...]
    :param excluded_condition: Boolean template over ``accepted:`` atoms.
    :type excluded_condition: BoolTemplate
    :param event_paths: Event paths read by excluded cases, defaults to ``()``.
    :type event_paths: Tuple[str, ...], optional
    :param guard_requirement_ids: Guard ids read by excluded cases, defaults to
        ``()``.
    :type guard_requirement_ids: Tuple[str, ...], optional

    Example::

        >>> mask = PriorityExclusion('d0', 'transition_priority', ('c0',), BoolTemplate.atom('accepted:c0'))
        >>> mask.excluded_case_labels
        ('c0',)
    """

    decision_id: str
    reason: str
    excluded_case_labels: Tuple[str, ...]
    excluded_condition: BoolTemplate
    event_paths: Tuple[str, ...] = ()
    guard_requirement_ids: Tuple[str, ...] = ()

    def __post_init__(self) -> None:
        labels = tuple(self.excluded_case_labels)
        if not labels:
            raise InvalidBmcEncoding("excluded_case_labels must not be empty.")
        if not all(isinstance(item, str) and item for item in labels):
            raise InvalidBmcEncoding(
                "excluded_case_labels must contain non-empty strings."
            )
        if not isinstance(self.excluded_condition, BoolTemplate):
            raise InvalidBmcEncoding("excluded_condition must be BoolTemplate.")
        for atom in self.excluded_condition.variables:
            if not atom.startswith(_ACCEPTED_ATOM_PREFIX):
                raise InvalidBmcEncoding(
                    "priority excluded_condition must use accepted atoms."
                )
        object.__setattr__(
            self,
            "decision_id",
            _require_non_empty_string(self.decision_id, "decision_id"),
        )
        object.__setattr__(
            self,
            "reason",
            _validate_choice(self.reason, _PRIORITY_REASONS, "priority reason"),
        )
        object.__setattr__(self, "excluded_case_labels", tuple(sorted(labels)))
        object.__setattr__(self, "event_paths", tuple(sorted(set(self.event_paths))))
        object.__setattr__(
            self,
            "guard_requirement_ids",
            tuple(sorted(set(self.guard_requirement_ids))),
        )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable priority-exclusion dictionary.

        :return: Canonical priority metadata.
        :rtype: Dict[str, object]

        Example::

            >>> PriorityExclusion('d0', 'transition_priority', ('c0',), BoolTemplate.atom('accepted:c0')).to_canonical()['reason']
            'transition_priority'
        """
        return {
            "node": "priority_exclusion",
            "decision_id": self.decision_id,
            "reason": self.reason,
            "excluded_case_labels": list(self.excluded_case_labels),
            "excluded_condition": self.excluded_condition.to_canonical(),
            "event_paths": list(self.event_paths),
            "guard_requirement_ids": list(self.guard_requirement_ids),
        }


@dataclass(frozen=True)
class ActionBlock:
    """Runtime action block recorded for a macro-step path.

    :param block_kind: Public block kind: ``"state_action"``,
        ``"aspect_action"``, or ``"transition_effect"``.
    :type block_kind: str
    :param runtime_role: Runtime role explaining why the block executes, such as
        ``"state_enter"``, ``"leaf_during"``, ``"aspect_during_before"``, or
        ``"transition_effect"``.
    :type runtime_role: str
    :param owner_state_id: Domain id of the state that owns the block.
    :type owner_state_id: int
    :param owner_state_path: Dot-separated owner state path.
    :type owner_state_path: str
    :param operations: Ordered model statements in the block.
    :type operations: Tuple[pyfcstm.model.OperationStatement, ...]
    :param action_name: Optional model action function name, defaults to
        ``None``.
    :type action_name: str, optional
    :param transition_label: Optional transition label for effect blocks,
        defaults to ``None``.
    :type transition_label: str, optional
    :param is_abstract: Whether this block represents an abstract hook, defaults
        to ``False``.
    :type is_abstract: bool, optional
    :param active_leaf_path: Runtime active leaf path when the block executes,
        defaults to ``None`` for legacy callers.
    :type active_leaf_path: str, optional
    :param execution_state_path: Runtime public state path passed to abstract
        handler context, defaults to ``None`` and falls back to owner state.
    :type execution_state_path: str, optional
    :param named_ref: Named reference callsite path when this block was reached
        through ``ref``, defaults to ``None``.
    :type named_ref: str, optional

    Example::

        >>> ActionBlock('state_action', 'leaf_during', 0, 'Root', ()).operations
        ()
    """

    block_kind: str
    runtime_role: str
    owner_state_id: int
    owner_state_path: str
    operations: Tuple[OperationStatement, ...]
    action_name: Optional[str] = None
    transition_label: Optional[str] = None
    is_abstract: bool = False
    active_leaf_path: Optional[str] = None
    execution_state_path: Optional[str] = None
    named_ref: Optional[str] = None

    def __post_init__(self) -> None:
        owner_state_id = _validate_index(self.owner_state_id, "owner_state_id")
        if owner_state_id < 0:
            raise InvalidBmcEncoding("owner_state_id must be non-negative.")
        operations = tuple(self.operations)
        if not all(isinstance(item, OperationStatement) for item in operations):
            raise InvalidBmcEncoding(
                "operations must contain OperationStatement objects."
            )
        if not isinstance(self.is_abstract, bool):
            raise InvalidBmcEncoding("is_abstract must be a boolean.")
        object.__setattr__(
            self,
            "block_kind",
            _validate_choice(self.block_kind, _ACTION_BLOCK_KINDS, "block_kind"),
        )
        object.__setattr__(
            self,
            "runtime_role",
            _validate_choice(self.runtime_role, _ACTION_RUNTIME_ROLES, "runtime_role"),
        )
        object.__setattr__(self, "owner_state_id", owner_state_id)
        object.__setattr__(
            self,
            "owner_state_path",
            _require_non_empty_string(self.owner_state_path, "owner_state_path"),
        )
        object.__setattr__(self, "operations", operations)
        if self.action_name is not None:
            object.__setattr__(
                self,
                "action_name",
                _require_non_empty_string(self.action_name, "action_name"),
            )
        if self.transition_label is not None:
            object.__setattr__(
                self,
                "transition_label",
                _require_non_empty_string(self.transition_label, "transition_label"),
            )
        if self.active_leaf_path is not None:
            object.__setattr__(
                self,
                "active_leaf_path",
                _require_non_empty_string(self.active_leaf_path, "active_leaf_path"),
            )
        if self.execution_state_path is not None:
            object.__setattr__(
                self,
                "execution_state_path",
                _require_non_empty_string(
                    self.execution_state_path, "execution_state_path"
                ),
            )
        if self.named_ref is not None:
            object.__setattr__(
                self,
                "named_ref",
                _require_non_empty_string(self.named_ref, "named_ref"),
            )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable action-block dictionary.

        :return: Canonical action-block metadata.
        :rtype: Dict[str, object]

        Example::

            >>> ActionBlock('state_action', 'leaf_during', 0, 'Root', ()).to_canonical()['block_kind']
            'state_action'
        """
        return {
            "node": "action_block",
            "block_kind": self.block_kind,
            "runtime_role": self.runtime_role,
            "owner_state_id": self.owner_state_id,
            "owner_state_path": self.owner_state_path,
            "action_name": self.action_name,
            "transition_label": self.transition_label,
            "is_abstract": self.is_abstract,
            "active_leaf_path": self.active_leaf_path,
            "execution_state_path": self.execution_state_path,
            "named_ref": self.named_ref,
            "operations": [_statement_to_canonical(item) for item in self.operations],
        }


def _expr_to_text(expr: Expr) -> str:
    return str(expr.to_ast_node())


def _statement_to_canonical(statement: OperationStatement) -> _CanonicalDict:
    if isinstance(statement, Operation):
        return {
            "node": "operation",
            "var_name": statement.var_name,
            "expr": _expr_to_text(statement.expr),
        }
    if isinstance(statement, IfBlock):
        branches = []
        for branch in statement.branches:
            branches.append(
                {
                    "condition": _expr_to_text(branch.condition)
                    if branch.condition is not None
                    else None,
                    "statements": [
                        _statement_to_canonical(item) for item in branch.statements
                    ],
                }
            )
        return {"node": "if_block", "branches": branches}
    return {"node": type(statement).__name__}


def _expected_case_path(domain: BmcDomain, state_id: int) -> str:
    try:
        if state_id == STATE_INIT_ID:
            domain.state_by_id(STATE_INIT_ID)
            return INIT_CASE_PATH
        if state_id == STATE_TERMINATE_ID:
            domain.state_by_id(STATE_TERMINATE_ID)
            return TERMINATE_CASE_PATH
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


def _condition_atoms(condition: BoolTemplate) -> Tuple[str, ...]:
    return condition.variables


def _validate_condition_atom_prefixes(condition: BoolTemplate, field_name: str) -> None:
    for atom in _condition_atoms(condition):
        if atom.startswith(_SOURCE_STATE_ATOM_PREFIX):
            raise InvalidBmcEncoding(
                "%s uses reserved source-state atom namespace: %r." % (field_name, atom)
            )
        if not atom.startswith(_VALID_CONDITION_PREFIXES):
            raise InvalidBmcEncoding(
                "%s uses unsupported macro condition atom namespace: %r."
                % (field_name, atom)
            )


def _validate_partition_atom_prefixes(
    conditions: Sequence[BoolTemplate],
    variables: Optional[Sequence[str]] = None,
) -> None:
    for condition in conditions:
        _validate_condition_atom_prefixes(condition, "partition bucket")
    if variables is None:
        return
    for atom in variables:
        if atom.startswith(_SOURCE_STATE_ATOM_PREFIX):
            raise BmcBuildError(
                "partition variables use reserved source-state atom namespace: %r."
                % atom
            )
        if not atom.startswith(_VALID_CONDITION_PREFIXES):
            raise BmcBuildError(
                "partition variables use unsupported macro condition atom namespace: %r."
                % atom
            )


def _event_atom_paths(condition: BoolTemplate) -> Tuple[str, ...]:
    return tuple(
        sorted(
            atom[len(_EVENT_ATOM_PREFIX) :]
            for atom in condition.variables
            if atom.startswith(_EVENT_ATOM_PREFIX)
        )
    )


def _guard_atom_ids(condition: BoolTemplate) -> Tuple[str, ...]:
    return tuple(
        sorted(
            atom[len(_GUARD_ATOM_PREFIX) :]
            for atom in condition.variables
            if atom.startswith(_GUARD_ATOM_PREFIX)
        )
    )


def _accepted_atom_labels(condition: BoolTemplate) -> Tuple[str, ...]:
    return tuple(
        sorted(
            atom[len(_ACCEPTED_ATOM_PREFIX) :]
            for atom in condition.variables
            if atom.startswith(_ACCEPTED_ATOM_PREFIX)
        )
    )


def _condition_uses_expected_accepted_prefix(
    condition: BoolTemplate, labels: Sequence[str]
) -> bool:
    """Return whether ``condition`` has exactly the expected accepted mask."""
    expected = tuple(labels)
    if not expected:
        return not _accepted_atom_labels(condition)
    expected_mask = BoolTemplate.not_(
        BoolTemplate.or_(
            *[
                BoolTemplate.atom("%s%s" % (_ACCEPTED_ATOM_PREFIX, label))
                for label in expected
            ]
        )
    )
    expected_mask_key = _canonical_key(expected_mask)
    if _canonical_key(condition) == expected_mask_key:
        return True
    if condition.kind != "and":
        return False
    mask_count = 0
    for operand in condition.operands:
        if _canonical_key(operand) == expected_mask_key:
            mask_count += 1
            continue
        if _accepted_atom_labels(operand):
            return False
    return mask_count == 1


def _condition_uses_exact_accepted_complement(
    condition: BoolTemplate,
    labels: Sequence[str],
    extra_exclusions: Sequence[BoolTemplate] = (),
) -> bool:
    exclusions = [
        BoolTemplate.atom("%s%s" % (_ACCEPTED_ATOM_PREFIX, label)) for label in labels
    ]
    exclusions.extend(extra_exclusions)
    expected = (
        BoolTemplate.not_(BoolTemplate.or_(*exclusions))
        if exclusions
        else BoolTemplate.true()
    )
    return _canonical_key(condition) == _canonical_key(expected)


def _event_uses_from_paths(
    domain: BmcDomain, paths: Sequence[str], polarity: str, reason: str
) -> Tuple[EventUse, ...]:
    result = []
    for path in sorted(set(paths)):
        try:
            entry = domain.event_by_path(path)
        except InvalidBmcDomain as err:
            # InvalidBmcDomain: domain.event_by_path rejects event paths copied
            # from malformed macro control atoms.
            raise InvalidBmcEncoding(str(err)) from err
        result.append(EventUse(entry.id, entry.path, polarity, reason))
    return tuple(result)


def _event_uses_from_condition(
    condition: BoolTemplate, domain: BmcDomain, polarity: str, reason: str
) -> Tuple[EventUse, ...]:
    return _event_uses_from_paths(
        domain, _event_atom_paths(condition), polarity, reason
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
    if not allowed or not all(kind in _ACCEPTED_CASE_KINDS for kind in allowed):
        raise _internal_bmc_error(  # pragma: no cover
            "_normalize_accepted_cases only accepts ordinary macro case kind policies."
        )
    if not all(isinstance(item, CycleCase) for item in accepted):
        raise InvalidBmcEncoding("accepted_cases must contain CycleCase objects.")
    for case in accepted:
        if case.kind not in allowed:
            raise InvalidBmcEncoding(
                "accepted_cases for %s may only contain ordinary accepted cases with kinds %r."
                % (helper_name, allowed)
            )
        if not _is_model_or_terminate_target(case):
            raise InvalidBmcEncoding(
                "accepted_cases for %s must target model states or terminate."
                % helper_name
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
    :param label: Stable label in ``source_path::case_kind::target_path::ordinal``
        form.
    :type label: str
    :param condition: Bare control-path condition without a source-state guard.
    :type condition: BoolTemplate
    :param action_blocks: Runtime action blocks executed by this path.
    :type action_blocks: Tuple[ActionBlock, ...]
    :param used_events: Event inputs read by this case, defaults to ``()``.
    :type used_events: Tuple[EventUse, ...], optional
    :param guard_requirements: Guard requirements read by this case, defaults to
        ``()``.
    :type guard_requirements: Tuple[GuardRequirement, ...], optional
    :param priority_exclusions: Priority masks applied by this case, defaults to
        ``()``.
    :type priority_exclusions: Tuple[PriorityExclusion, ...], optional
    :param failed_conditions: Diagnostic-only failed candidate conditions,
        defaults to ``()``.
    :type failed_conditions: Tuple[BoolTemplate, ...], optional
    :param domain: Optional domain used for eager validation, defaults to
        ``None``.
    :type domain: BmcDomain, optional

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
    action_blocks: Tuple[ActionBlock, ...]
    used_events: Tuple[EventUse, ...] = ()
    guard_requirements: Tuple[GuardRequirement, ...] = ()
    priority_exclusions: Tuple[PriorityExclusion, ...] = ()
    failed_conditions: Tuple[BoolTemplate, ...] = ()
    domain: Optional[BmcDomain] = field(default=None, repr=False, compare=False)

    def __post_init__(self) -> None:
        kind = _validate_choice(self.kind, _CASE_KINDS, "case kind")
        source_id = _validate_index(self.source_state_id, "source_state_id")
        target_id = _validate_index(self.target_state_id, "target_state_id")
        source_path = _require_non_empty_string(
            self.source_state_path, "source_state_path"
        )
        target_path = _require_non_empty_string(
            self.target_state_path, "target_state_path"
        )
        label = _require_non_empty_string(self.label, "label")
        if not isinstance(self.condition, BoolTemplate):
            raise InvalidBmcEncoding("condition must be BoolTemplate.")
        _validate_condition_atom_prefixes(self.condition, "condition")
        action_blocks = tuple(self.action_blocks)
        if not all(isinstance(item, ActionBlock) for item in action_blocks):
            raise InvalidBmcEncoding("action_blocks must contain ActionBlock objects.")
        used_events = tuple(self.used_events)
        if not all(isinstance(item, EventUse) for item in used_events):
            raise InvalidBmcEncoding("used_events must contain EventUse objects.")
        guard_requirements = tuple(self.guard_requirements)
        if not all(isinstance(item, GuardRequirement) for item in guard_requirements):
            raise InvalidBmcEncoding(
                "guard_requirements must contain GuardRequirement objects."
            )
        priority_exclusions = tuple(self.priority_exclusions)
        if not all(isinstance(item, PriorityExclusion) for item in priority_exclusions):
            raise InvalidBmcEncoding(
                "priority_exclusions must contain PriorityExclusion objects."
            )
        failed_conditions = tuple(self.failed_conditions)
        if not all(isinstance(item, BoolTemplate) for item in failed_conditions):
            raise InvalidBmcEncoding(
                "failed_conditions must contain BoolTemplate objects."
            )
        for item in failed_conditions:
            _validate_condition_atom_prefixes(item, "failed_conditions")

        object.__setattr__(self, "kind", kind)
        object.__setattr__(self, "source_state_id", source_id)
        object.__setattr__(self, "target_state_id", target_id)
        object.__setattr__(self, "source_state_path", source_path)
        object.__setattr__(self, "target_state_path", target_path)
        object.__setattr__(self, "label", label)
        object.__setattr__(self, "action_blocks", action_blocks)
        event_by_key = {_canonical_key(item): item for item in used_events}
        object.__setattr__(
            self,
            "used_events",
            tuple(event_by_key[key] for key in sorted(event_by_key)),
        )
        object.__setattr__(
            self,
            "guard_requirements",
            tuple(sorted(guard_requirements, key=lambda item: item.requirement_id)),
        )
        object.__setattr__(
            self,
            "priority_exclusions",
            tuple(sorted(priority_exclusions, key=lambda item: item.decision_id)),
        )
        object.__setattr__(
            self,
            "failed_conditions",
            tuple(sorted(failed_conditions, key=_canonical_key)),
        )
        self._validate_label()
        self._validate_kind_shape()
        self._validate_local_atom_links()
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
            if self.source_state_id != STATE_TERMINATE_ID:
                raise InvalidBmcEncoding(
                    "absorb cases must use the terminate sentinel."
                )
        if self.kind == "delta":
            if self.target_state_id != self.source_state_id:
                raise InvalidBmcEncoding("delta cases must self-loop source state.")
            if self.target_state_path != self.source_state_path:
                raise InvalidBmcEncoding("delta cases must self-loop source path.")

    def _validate_local_atom_links(self) -> None:
        condition_guard_ids = set(_guard_atom_ids(self.condition))
        for failed in self.failed_conditions:
            condition_guard_ids.update(_guard_atom_ids(failed))
        declared_guard_ids = {item.requirement_id for item in self.guard_requirements}
        missing = sorted(condition_guard_ids - declared_guard_ids)
        if missing:
            raise InvalidBmcEncoding(
                "guard atoms must have matching GuardRequirement: %r." % missing[0]
            )
        if len(declared_guard_ids) != len(self.guard_requirements):
            raise InvalidBmcEncoding("Duplicate guard requirement id.")
        condition_guard_ids = set(_guard_atom_ids(self.condition))
        if any(
            item.requirement_id in condition_guard_ids
            and item.after_action_block_index > len(self.action_blocks)
            for item in self.guard_requirements
        ):
            raise InvalidBmcEncoding("guard anchor exceeds action block count.")

    def _validate_against_domain(self, domain: BmcDomain) -> None:
        _validate_case_state(
            domain, self.source_state_id, self.source_state_path, "source"
        )
        _validate_case_state(
            domain, self.target_state_id, self.target_state_path, "target"
        )
        used_event_paths = set()
        for event_use in self.used_events:
            try:
                event = domain.event_by_id(event_use.event_id)
            except InvalidBmcDomain as err:
                # InvalidBmcDomain: BmcDomain lookup rejects unknown event ids
                # referenced by this case's event-use metadata.
                raise InvalidBmcEncoding(str(err)) from err
            if event.path != event_use.path:
                raise InvalidBmcEncoding("EventUse path does not match event id.")
            used_event_paths.add(event.path)
        for event_path in _event_atom_paths(self.condition) + tuple(
            path for item in self.failed_conditions for path in _event_atom_paths(item)
        ):
            try:
                domain.event_by_path(event_path)
            except InvalidBmcDomain as err:
                # InvalidBmcDomain: BmcDomain lookup rejects event atoms that
                # reference paths outside the case's domain snapshot.
                raise InvalidBmcEncoding(str(err)) from err
            if event_path not in used_event_paths:
                raise InvalidBmcEncoding(
                    "event atoms in case conditions must be listed in used_events."
                )
        for guard in self.guard_requirements:
            _validate_case_state(
                domain, guard.owner_state_id, guard.owner_state_path, "guard owner"
            )
        for block in self.action_blocks:
            _validate_case_state(
                domain, block.owner_state_id, block.owner_state_path, "action owner"
            )

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable case dictionary.

        :return: Canonical cycle-case dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> case = CycleCase('transition', 0, 'Root', 0, 'Root', 'Root::transition::Root::0', BoolTemplate.true(), ())
            >>> case.to_canonical()['kind']
            'transition'
        """
        return {
            "node": "cycle_case",
            "kind": self.kind,
            "source_state_id": self.source_state_id,
            "source_state_path": self.source_state_path,
            "target_state_id": self.target_state_id,
            "target_state_path": self.target_state_path,
            "label": self.label,
            "used_events": [item.to_canonical() for item in self.used_events],
            "guard_requirements": [
                item.to_canonical() for item in self.guard_requirements
            ],
            "priority_exclusions": [
                item.to_canonical() for item in self.priority_exclusions
            ],
            "action_blocks": [item.to_canonical() for item in self.action_blocks],
            "condition": self.condition.to_canonical(),
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

        >>> PartitionCheckResult(('event:Root.Go',), 2, 2).to_canonical()['assignment_count']
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


def _is_model_or_terminate_target(case: CycleCase) -> bool:
    if case.target_state_id == STATE_TERMINATE_ID:
        return case.target_state_path == TERMINATE_CASE_PATH
    return (
        case.target_state_id >= 0 and case.target_state_path not in _RESERVED_CASE_PATHS
    )


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
            >>> case = CycleCase('delta', 0, 'Root', 0, 'Root', 'Root::delta::Root::0', BoolTemplate.true(), ())
            >>> MacroStepFormal(source, (), (case,)).cases[0].kind
            'delta'
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
        self._validate_accepted_atom_registry(labels)
        for case in self.success_cases:
            if case.kind == "delta":
                raise InvalidBmcEncoding("success_cases must not contain delta cases.")
            self._validate_success_case_shape(case)
        if self.delta_cases and not self.source.allows_semantic_delta:
            raise InvalidBmcEncoding("delta_cases require a delta-capable source.")
        if not self.source.allows_semantic_delta and self.build_diagnostic_conditions:
            raise InvalidBmcEncoding(
                "build diagnostics are only recorded on delta-capable source formals."
            )
        if self.source.kind == "stable_leaf":
            if not any(case.kind == "fallback" for case in self.success_cases):
                raise InvalidBmcEncoding("stable leaf formal requires a fallback case.")
        if self.source.kind == "terminated":
            self._validate_sentinel_absorb(STATE_TERMINATE_ID)
        for case in self.delta_cases:
            if case.kind != "delta":
                raise InvalidBmcEncoding("delta_cases may only contain delta cases.")

    def _validate_case_domain_contract(self, case: CycleCase) -> None:
        if self.source.domain is not None:
            case._validate_against_domain(self.source.domain)

    def _validate_accepted_atom_registry(self, labels: Set[str]) -> None:
        for case in self.cases:
            for condition in (case.condition,) + case.failed_conditions:
                for label in _accepted_atom_labels(condition):
                    if label not in labels:
                        raise InvalidBmcEncoding(
                            "accepted atom references unknown case label: %r." % label
                        )
            for priority in case.priority_exclusions:
                for label in priority.excluded_case_labels:
                    if label not in labels:
                        raise InvalidBmcEncoding(
                            "priority exclusion references unknown case label: %r."
                            % label
                        )

    def _validate_success_case_shape(self, case: CycleCase) -> None:
        if self.source.kind == "stable_leaf":
            if case.kind not in {"transition", "fallback"}:
                raise InvalidBmcEncoding(
                    "stable leaf success cases may only be transition or fallback."
                )
            if case.kind == "fallback" and (
                case.target_state_id != self.source.source_state_id
                or case.target_state_path != self.source.source_state_path
            ):
                raise InvalidBmcEncoding("fallback cases must self-loop source.")
            if case.kind == "transition" and not _is_model_or_terminate_target(case):
                raise InvalidBmcEncoding(
                    "stable leaf transitions must target model states or terminate."
                )
        elif self.source.kind in {"init", "entry"}:
            if case.kind not in {"transition", "initial"}:
                raise InvalidBmcEncoding(
                    "entry success cases may only be transition or initial."
                )
            if not _is_model_or_terminate_target(case):
                raise InvalidBmcEncoding(
                    "entry transition and initial cases must target model states or terminate."
                )

    def _validate_sentinel_absorb(self, sentinel_id: int) -> None:
        if sentinel_id != STATE_TERMINATE_ID:  # pragma: no cover - private guard.
            raise InvalidBmcEncoding("only terminate sentinel absorb is supported.")
        _validate_sentinel_absorb_partition(
            self.success_cases,
            sentinel_id,
            TERMINATE_CASE_PATH,
        )

    def verify_partition(self, max_assignments: int = 4096) -> PartitionCheckResult:
        """Verify local case buckets with structural and truth-table self-checks.

        :param max_assignments: Maximum assignments to enumerate, defaults to
            ``4096``.
        :type max_assignments: int, optional
        :return: Partition self-check summary.
        :rtype: PartitionCheckResult
        :raises BmcBuildError: If the buckets overlap, leave a gap, or exceed
            the assignment budget for a non-structural shape.

        Example::

            >>> source = MacroStepSource('entry', 'initial', 0, 'Root')
            >>> case = CycleCase('delta', 0, 'Root', 0, 'Root', 'Root::delta::Root::0', BoolTemplate.true(), ())
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
            >>> case = CycleCase('delta', 0, 'Root', 0, 'Root', 'Root::delta::Root::0', BoolTemplate.true(), ())
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


def case_path_condition(case: CycleCase) -> BoolTemplate:
    """Return the solver-independent control-path condition for ``case``.

    The helper intentionally returns :attr:`CycleCase.condition` without adding
    a source-state guard.  Later relation builders are responsible for building
    the final antecedent and emitting ``Implies(A, R)``.

    :param case: Case whose control-path condition should be returned.
    :type case: CycleCase
    :return: Bare case condition.
    :rtype: BoolTemplate
    :raises InvalidBmcEncoding: If ``case`` is not a cycle case.

    Example::

        >>> case = CycleCase('transition', 0, 'Root', 0, 'Root', 'Root::transition::Root::0', BoolTemplate.true(), ())
        >>> case_path_condition(case).evaluate({})
        True
    """
    if not isinstance(case, CycleCase):
        raise InvalidBmcEncoding("case must be CycleCase.")
    return case.condition


def terminated_absorb_case(domain: BmcDomain) -> CycleCase:
    """Build the terminate sentinel absorb case.

    :param domain: Domain snapshot whose sentinel entries are used.
    :type domain: BmcDomain
    :return: Terminated self-loop absorb case.
    :rtype: CycleCase

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> terminated_absorb_case(domain).kind
        'absorb'
    """
    return CycleCase(
        "absorb",
        STATE_TERMINATE_ID,
        TERMINATE_CASE_PATH,
        STATE_TERMINATE_ID,
        TERMINATE_CASE_PATH,
        "%s::absorb::%s::0" % (TERMINATE_CASE_PATH, TERMINATE_CASE_PATH),
        BoolTemplate.true(),
        (),
        domain=domain,
    )


def _case_label(source_path: str, kind: str, target_path: str, ordinal: int) -> str:
    return "%s::%s::%s::%d" % (source_path, kind, target_path, ordinal)


def _accepted_condition(accepted: Sequence[CycleCase]) -> BoolTemplate:
    if not accepted:
        return BoolTemplate.false()
    return BoolTemplate.or_(
        *[
            BoolTemplate.atom("%s%s" % (_ACCEPTED_ATOM_PREFIX, case.label))
            for case in accepted
        ]
    )


def _priority_exclusion_for_accepted(
    decision_id: str,
    reason: str,
    accepted: Sequence[CycleCase],
) -> Optional[PriorityExclusion]:
    if not accepted:
        return None
    event_paths = sorted(
        {event.path for case in accepted for event in case.used_events}
    )
    guard_ids = sorted(
        {guard.requirement_id for case in accepted for guard in case.guard_requirements}
    )
    return PriorityExclusion(
        decision_id,
        reason,
        tuple(case.label for case in accepted),
        _accepted_condition(accepted),
        tuple(event_paths),
        tuple(guard_ids),
    )


def build_fallback_case(
    domain: BmcDomain,
    source: MacroStepSource,
    accepted_cases: Sequence[CycleCase],
    failed_conditions: Sequence[BoolTemplate] = (),
    ordinal: int = 0,
    guard_requirements: Sequence[GuardRequirement] = (),
) -> CycleCase:
    """Build a stable leaf fallback self-cycle.

    The fallback condition negates accepted case labels rather than reusing raw
    trigger/guard predicates.  Failed candidate conditions remain diagnostic
    metadata and do not shrink the fallback region.

    :param domain: Domain snapshot whose event ids are used.
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
    :param guard_requirements: Guard metadata for atoms referenced by failed
        diagnostic conditions, defaults to ``()``.
    :type guard_requirements: Sequence[GuardRequirement], optional
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
        accepted_cases, source, "fallback", ("transition",)
    )
    if not isinstance(failed_conditions, (list, tuple)):
        raise InvalidBmcEncoding("failed_conditions must be a sequence.")
    failed = tuple(failed_conditions)
    if not all(isinstance(item, BoolTemplate) for item in failed):
        raise InvalidBmcEncoding("failed_conditions must contain BoolTemplate objects.")
    guards = tuple(guard_requirements)
    if not all(isinstance(item, GuardRequirement) for item in guards):
        raise InvalidBmcEncoding(
            "guard_requirements must contain GuardRequirement objects."
        )
    excluded = _accepted_condition(accepted)
    condition = BoolTemplate.not_(excluded) if accepted else BoolTemplate.true()
    used_events = _event_uses_from_paths(
        domain,
        [event.path for case in accepted for event in case.used_events],
        "negative",
        "fallback",
    )
    used_events += _event_uses_from_condition(condition, domain, "negative", "fallback")
    used_events += _event_uses_from_condition(
        BoolTemplate.or_(*failed), domain, "negative", "fallback"
    )
    priority = _priority_exclusion_for_accepted(
        "fallback:%s:%d" % (source.source_state_path, ordinal), "fallback", accepted
    )
    return CycleCase(
        "fallback",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        _case_label(
            source.source_state_path, "fallback", source.source_state_path, ordinal
        ),
        condition,
        (),
        used_events=used_events,
        guard_requirements=guards,
        priority_exclusions=(priority,) if priority is not None else (),
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
    guard_requirements: Sequence[GuardRequirement] = (),
) -> CycleCase:
    """Build a non-stoppable entry uncovered-region delta case.

    The delta condition negates accepted case labels and build-diagnostic
    conditions.  Failed candidate conditions remain diagnostic metadata only.

    :param domain: Domain snapshot whose event ids are used.
    :type domain: BmcDomain
    :param source: Initial entry source.
    :type source: MacroStepSource
    :param accepted_cases: Accepted transition or initial success cases.
    :type accepted_cases: Sequence[CycleCase]
    :param build_diagnostic_conditions: Build diagnostic conditions excluded
        from semantic delta, defaults to ``()``.
    :type build_diagnostic_conditions: Sequence[BoolTemplate], optional
    :param failed_conditions: Diagnostic-only failed candidate conditions,
        defaults to ``()``.
    :type failed_conditions: Sequence[BoolTemplate], optional
    :param ordinal: Label ordinal, defaults to ``0``.
    :type ordinal: int, optional
    :param guard_requirements: Guard metadata for atoms referenced by failed
        diagnostic conditions, defaults to ``()``.
    :type guard_requirements: Sequence[GuardRequirement], optional
    :return: Semantic delta case that self-loops the source.
    :rtype: CycleCase
    :raises InvalidBmcEncoding: If ``source`` does not allow semantic delta.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.source import entry_source
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> case = build_semantic_delta_case(domain, entry_source(domain), ())
        >>> case.target_state_id == case.source_state_id
        True
    """
    if not isinstance(source, MacroStepSource) or not source.allows_semantic_delta:
        raise InvalidBmcEncoding("semantic delta case requires a delta-capable source.")
    ordinal = _validate_index(ordinal, "ordinal")
    if ordinal < 0:
        raise InvalidBmcEncoding("ordinal must be non-negative.")
    accepted = _normalize_accepted_cases(
        accepted_cases, source, "delta", ("transition", "initial")
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
    guards = tuple(guard_requirements)
    if not all(isinstance(item, GuardRequirement) for item in guards):
        raise InvalidBmcEncoding(
            "guard_requirements must contain GuardRequirement objects."
        )
    excluded = []
    if accepted:
        excluded.append(_accepted_condition(accepted))
    excluded.extend(diagnostics)
    condition = (
        BoolTemplate.not_(BoolTemplate.or_(*excluded))
        if excluded
        else BoolTemplate.true()
    )
    used_events = _event_uses_from_paths(
        domain,
        [event.path for case in accepted for event in case.used_events],
        "negative",
        "fallback",
    )
    used_events += _event_uses_from_condition(condition, domain, "negative", "fallback")
    used_events += _event_uses_from_condition(
        BoolTemplate.or_(*failed), domain, "negative", "fallback"
    )
    priority = _priority_exclusion_for_accepted(
        "delta:%s:%d" % (source.source_state_path, ordinal), "delta", accepted
    )
    return CycleCase(
        "delta",
        source.source_state_id,
        source.source_state_path,
        source.source_state_id,
        source.source_state_path,
        _case_label(
            source.source_state_path, "delta", source.source_state_path, ordinal
        ),
        condition,
        (),
        used_events=used_events,
        guard_requirements=guards,
        priority_exclusions=(priority,) if priority is not None else (),
        failed_conditions=failed,
        domain=domain,
    )


def _resolve_accepted_atoms(
    condition: BoolTemplate,
    registry: Mapping[str, BoolTemplate],
    active: Optional[Set[str]] = None,
) -> BoolTemplate:
    if active is None:
        active = set()
    if condition.kind == "atom":
        atom = condition._atom_name()
        if not atom.startswith(_ACCEPTED_ATOM_PREFIX):
            return condition
        label = atom[len(_ACCEPTED_ATOM_PREFIX) :]
        if label not in registry:
            raise BmcBuildError(
                "accepted atom references unknown case label: %r." % label
            )
        if label in active:
            raise BmcBuildError(
                "accepted atom cycle detected for case label: %r." % label
            )
        active.add(label)
        resolved = _resolve_accepted_atoms(registry[label], registry, active)
        active.remove(label)
        return resolved
    if condition.kind in {"true", "false"}:
        return condition
    if condition.kind == "not":
        return BoolTemplate.not_(
            _resolve_accepted_atoms(condition.operands[0], registry, active)
        )
    if condition.kind == "and":
        return BoolTemplate.and_(
            *[
                _resolve_accepted_atoms(item, registry, active)
                for item in condition.operands
            ]
        )
    if condition.kind == "or":
        return BoolTemplate.or_(
            *[
                _resolve_accepted_atoms(item, registry, active)
                for item in condition.operands
            ]
        )
    raise _internal_bmc_error(  # pragma: no cover
        "unsupported boolean template kind while resolving accepted atoms: %r."
        % condition.kind
    )


def _validate_sentinel_absorb_partition(
    success: Sequence[CycleCase],
    sentinel_id: int,
    sentinel_path: str,
) -> None:
    """Validate the exact shape of a sentinel self-absorb partition.

    The validator is intentionally fail-fast: if one malformed bucket violates
    several constraints, the first constraint in this function's structural
    order determines the reported message. Tests should construct one target
    violation per case when asserting specific diagnostics.

    :param success: Success bucket under validation.
    :type success: Sequence[CycleCase]
    :param sentinel_id: Fixed sentinel state id expected for the source.
    :type sentinel_id: int
    :param sentinel_path: Fixed sentinel state path expected for the source.
    :type sentinel_path: str
    :return: ``None``.
    :rtype: None
    :raises InvalidBmcEncoding: If the buckets are not a single pure sentinel
        absorb self-loop.
    """
    if len(success) != 1:
        raise InvalidBmcEncoding("sentinel absorb formal must contain one case.")
    case = success[0]
    if case.kind != "absorb":
        raise InvalidBmcEncoding("sentinel formal case must be absorb.")
    if (
        case.source_state_id != sentinel_id
        or case.target_state_id != sentinel_id
        or case.source_state_path != sentinel_path
        or case.target_state_path != sentinel_path
    ):
        raise InvalidBmcEncoding(
            "sentinel absorb case must self-loop the source sentinel."
        )
    expected_label = "%s::absorb::%s::0" % (sentinel_path, sentinel_path)
    if case.label != expected_label:
        raise InvalidBmcEncoding("sentinel absorb label must be canonical.")
    if case.condition.kind != "true":
        raise InvalidBmcEncoding("sentinel absorb condition must be true.")
    if case.action_blocks:
        raise InvalidBmcEncoding("sentinel absorb case cannot have action blocks.")
    if case.used_events:
        raise InvalidBmcEncoding("sentinel absorb case cannot use events.")
    if case.guard_requirements:
        raise InvalidBmcEncoding("sentinel absorb case cannot have guard requirements.")
    if case.priority_exclusions:
        raise InvalidBmcEncoding(
            "sentinel absorb case cannot have priority exclusions."
        )
    if case.failed_conditions:
        raise InvalidBmcEncoding("sentinel absorb case cannot have failed conditions.")


def _structural_partition_result(
    source: MacroStepSource,
    success: Sequence[CycleCase],
    delta: Sequence[CycleCase],
    diagnostics: Sequence[BoolTemplate],
    variables: Sequence[str],
) -> Optional[PartitionCheckResult]:
    if source.kind == "terminated":
        sentinel_id = STATE_TERMINATE_ID
        sentinel_path = TERMINATE_CASE_PATH
        if delta or diagnostics:
            raise _internal_bmc_error(  # pragma: no cover
                "sentinel structural partition received delta or diagnostic buckets "
                "after public preflight."
            )
        _validate_sentinel_absorb_partition(success, sentinel_id, sentinel_path)
        return PartitionCheckResult(tuple(variables), 0, 1)

    cases = tuple(success) + tuple(delta)
    accepted_cases = [case for case in cases if case.kind in _ACCEPTED_CASE_KINDS]
    terminal_cases = [case for case in cases if case.kind not in _ACCEPTED_CASE_KINDS]
    accepted_labels: List[str] = []
    remaining: List[CycleCase] = list(accepted_cases)
    while remaining:
        candidates = [
            case
            for case in remaining
            if _condition_uses_expected_accepted_prefix(case.condition, accepted_labels)
        ]
        if len(candidates) != 1:
            return None
        selected = candidates[0]
        accepted_labels.append(selected.label)
        remaining.remove(selected)

    if len(terminal_cases) != 1:
        return None
    terminal = terminal_cases[0]
    if terminal.kind == "fallback":
        if source.kind != "stable_leaf" or delta or diagnostics:
            return None
        if not _condition_uses_exact_accepted_complement(
            terminal.condition, accepted_labels
        ):
            return None
    elif terminal.kind == "delta":
        if not source.allows_semantic_delta:
            # Public verify_source_partition() rejects non-delta-capable delta buckets
            # before structural recognition; reaching this branch means an
            # internal caller bypassed that preflight.
            raise _internal_bmc_error(  # pragma: no cover
                "delta structural partition reached a non-entry source after "
                "public preflight."
            )
        if not _condition_uses_exact_accepted_complement(
            terminal.condition, accepted_labels, diagnostics
        ):
            return None
    else:  # pragma: no cover - public preflight admits only fallback/delta here.
        return None

    if diagnostics and (not source.allows_semantic_delta or not delta):
        # The fallback branch rejects build-time buckets above, public preflight
        # rejects non-delta-capable sources, and the only accepted diagnostic
        # shape has a delta bucket. Keep this as a loud structural guard for
        # corrupted internal callers.
        raise _internal_bmc_error(  # pragma: no cover
            "build-condition structural partition reached an unsupported source or "
            "missing delta bucket after public preflight."
        )
    bucket_count = len(cases) + (1 if diagnostics else 0)
    return PartitionCheckResult(tuple(variables), 0, bucket_count)


def verify_boolean_partition(
    buckets: Sequence[BoolTemplate],
    variables: Optional[Sequence[str]] = None,
    max_assignments: int = 4096,
) -> PartitionCheckResult:
    """Verify that boolean buckets are complete and pairwise disjoint.

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
    :raises BmcBuildError: If the partition is not exactly one or cannot be
        checked.

    Example::

        >>> a = BoolTemplate.atom('event:Root.Go')
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
    _validate_partition_atom_prefixes(items, names)
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

    Canonical accepted/fallback masks are verified structurally to avoid
    rejecting large declaration-priority partitions merely because their event
    or guard atom count exceeds the fallback truth-table budget.  Non-canonical
    shapes are resolved through the source-local accepted-case registry and then
    checked by bounded truth-table enumeration.

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
    :raises InvalidBmcEncoding: If the source/case buckets have an invalid
        shape, including unsupported delta buckets or malformed sentinel absorb
        partitions.

    Example::

        >>> source = MacroStepSource('entry', 'initial', 0, 'Root')
        >>> case = CycleCase('delta', 0, 'Root', 0, 'Root', 'Root::delta::Root::0', BoolTemplate.true(), ())
        >>> verify_source_partition(source, (), (case,)).bucket_count
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
    if source.kind == "terminated":
        if delta:
            raise InvalidBmcEncoding("sentinel absorb formal cannot have delta cases.")
        if diagnostics:
            raise InvalidBmcEncoding(
                "sentinel absorb formal cannot have build diagnostics."
            )
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

    if source.kind == "terminated":
        structural = _structural_partition_result(
            source, success, delta, diagnostics, ()
        )
        if structural is not None:
            return structural

    _validate_partition_atom_prefixes(
        [case.condition for case in success + delta] + list(diagnostics)
    )
    registry = {case.label: case.condition for case in success + delta}
    buckets = [_resolve_accepted_atoms(case.condition, registry) for case in success]
    buckets.extend(_resolve_accepted_atoms(case.condition, registry) for case in delta)
    if diagnostics:
        buckets.append(BoolTemplate.or_(*diagnostics))
    variables = sorted(
        set(itertools.chain.from_iterable(bucket.variables for bucket in buckets))
    )
    if 2 ** len(variables) > max_assignments:
        structural = _structural_partition_result(
            source, success, delta, diagnostics, variables
        )
        if structural is not None:
            return structural
    return verify_boolean_partition(buckets, max_assignments=max_assignments)


__all__ = [
    "BoolTemplate",
    "EventUse",
    "GuardRequirement",
    "PriorityExclusion",
    "ActionBlock",
    "CycleCase",
    "PartitionCheckResult",
    "MacroStepFormal",
    "case_path_condition",
    "terminated_absorb_case",
    "build_fallback_case",
    "build_semantic_delta_case",
    "verify_boolean_partition",
    "verify_source_partition",
]

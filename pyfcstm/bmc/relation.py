"""Build solver-level BMC core trace relations.

This module lowers the solver-independent BMC preparation and macro-step
handoff objects into the first SMT formula layer.  The public entry point
:func:`build_bmc_core_formula` consumes a
:class:`pyfcstm.bmc.engine.BmcPreparedContext`, allocates bounded frame / step
symbols, expands macro-step cases, and constructs the core formula
``Core_N = D_N ∧ I_0 ∧ T_N ∧ ENV_N``.

The relation builder deliberately stops before property compilation.  It does
not decide whether a query is reachable, forbidden, covered, or healthy; later
layers can add objective predicates, witness decoding, and optional health or
runtime-error observations on top of the returned core formula.  Semantic
no-progress observations that are part of the core transition relation are
exposed directly as ``Delta_i`` and ``Gamma_i`` symbols.

Public concepts:

* :class:`BmcTraceSymbols` - Z3 symbols for frames, event inputs, and case
  selectors.
* :class:`BmcCaseRelation` - One lowered macro-step case implication.
* :class:`BmcStepRelation` - All case implications for one symbolic step.
* :class:`BmcCoreFormula` - The complete ``D_N`` / ``I_0`` / ``T_N`` /
  ``ENV_N`` bundle.

Example::

    >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('state Root;')
    >>> context = BmcEngine(model).prepare('check reach <= 1: terminated();')
    >>> core = build_bmc_core_formula(context)
    >>> core.to_canonical()['node']
    'bmc_core_formula'
"""

from __future__ import annotations

import hashlib
import math
import re
from dataclasses import dataclass, field
from typing import (
    Any,
    Callable,
    Dict,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
    Union,
)

import z3

from .ast import (
    Active,
    BmcCondExpr,
    BmcNumExpr,
    BoolLiteral,
    CallCount,
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
from .binding import BoundAssumption
from .domain import (
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcDomain,
)
from .engine import BmcPreparedContext
from .errors import BmcBuildError, UnsupportedBmcQuery
from .expand import expand_macro_step_cases
from .macro import (
    ActionBlock,
    BoolTemplate,
    CycleCase,
    GuardRequirement,
    MacroStepFormal,
)
from .query import EventCardinalityAssumption, FrameAssumption
from .source import (
    entry_source,
    init_source,
    source_from_initial_spec,
    stable_leaf_source,
    terminated_source,
)
from .provenance import BmcTrackedConstraint
from pyfcstm.model import Expr
from pyfcstm.solver.domain import DomainConstraint, DomainSource, translate_expr_domain
from pyfcstm.solver.operation import execute_operations_domain

_CanonicalDict = Dict[str, Any]
_Z3Expr = Union[z3.ArithRef, z3.BoolRef]
_CallCountLowerer = Callable[[CallCount, int, Optional[int]], _Z3Expr]
_EVENT_ATOM_PREFIX = "event:"
_GUARD_ATOM_PREFIX = "guard:"
_ACCEPTED_ATOM_PREFIX = "accepted:"
_ISSUE_URL = "https://github.com/HansBug/pyfcstm/issues"


@dataclass(frozen=True)
class _RelationFrameDomain:
    frame0_state_ids: Tuple[int, ...]
    recurrence_state_ids: Tuple[int, ...]


@dataclass(frozen=True)
class BmcAbstractCallRecord:
    """Lowered abstract-call occurrence with call-time symbolic snapshot.

    :param ordinal: Zero-based call order within the lowered case.
    :type ordinal: int
    :param action_name: Resolved abstract action name.
    :type action_name: str
    :param stage: Coarse public call stage, one of ``enter``, ``during``, or
        ``exit``.  Transition effects are intentionally grouped under
        ``during`` at this coarse layer; use ``role`` for exact runtime-role
        filtering.
    :type stage: str
    :param role: Runtime role that produced the call.
    :type role: str
    :param state_path: Runtime public state path approximation.
    :type state_path: str
    :param active_leaf_path: Runtime active leaf approximation.
    :type active_leaf_path: str
    :param named_ref: Named reference callsite, defaults to ``None``.
    :type named_ref: str, optional
    :param snapshot: Mapping from persistent variable names to call-time Z3
        expressions.
    :type snapshot: Mapping[str, z3.ArithRef]

    Example::

        >>> import z3
        >>> BmcAbstractCallRecord(0, 'A', 'during', 'leaf_during', 'Root', 'Root', None, {'x': z3.Int('x')}).to_canonical()['action_name']
        'A'
    """

    ordinal: int
    action_name: str
    stage: str
    role: str
    state_path: str
    active_leaf_path: str
    named_ref: Optional[str]
    snapshot: Mapping[str, z3.ArithRef]

    def __post_init__(self) -> None:
        if isinstance(self.ordinal, bool) or not isinstance(self.ordinal, int):
            raise BmcBuildError("call record ordinal must be an integer.")
        if self.ordinal < 0:
            raise BmcBuildError("call record ordinal must be non-negative.")
        for field_name in (
            "action_name",
            "stage",
            "role",
            "state_path",
            "active_leaf_path",
        ):
            value = getattr(self, field_name)
            if not isinstance(value, str) or not value:
                raise BmcBuildError("%s must be a non-empty string." % field_name)
        if self.named_ref is not None and (
            not isinstance(self.named_ref, str) or not self.named_ref
        ):
            raise BmcBuildError("named_ref must be None or a non-empty string.")
        snapshot = dict(self.snapshot)
        if not all(isinstance(name, str) and name for name in snapshot):
            raise BmcBuildError("call snapshot keys must be non-empty strings.")
        if not all(z3.is_arith(value) for value in snapshot.values()):
            raise BmcBuildError(
                "call snapshot values must be arithmetic Z3 expressions."
            )
        object.__setattr__(self, "snapshot", snapshot)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable call-record summary.

        :return: Canonical call record.
        :rtype: Dict[str, object]
        """
        return {
            "node": "bmc_abstract_call_record",
            "ordinal": self.ordinal,
            "action_name": self.action_name,
            "stage": self.stage,
            "role": self.role,
            "state_path": self.state_path,
            "active_leaf_path": self.active_leaf_path,
            "named_ref": self.named_ref,
            "snapshot": {
                name: _z3_text(expr) for name, expr in sorted(self.snapshot.items())
            },
        }


def _internal_bmc_error(detail: str) -> BmcBuildError:
    return BmcBuildError(
        "internal BMC bug: %s This indicates that pyfcstm's BMC relation "
        "builder received an inconsistent internal object or missed a required "
        "precondition; please report this with the FCSTM input, .fbmcq query, "
        "and traceback at %s." % (detail, _ISSUE_URL)
    )


def _require_context(context: object) -> BmcPreparedContext:
    if not isinstance(context, BmcPreparedContext):
        raise BmcBuildError("context must be BmcPreparedContext.")
    if context.domain.model is not context.model:
        raise BmcBuildError(
            "context.domain must be built from context.model for relation building."
        )
    return context


def _z3_text(expr: z3.ExprRef) -> str:
    return str(expr)


def _and(items: Iterable[z3.ExprRef]) -> z3.BoolRef:
    values = tuple(items)
    if not values:
        return z3.BoolVal(True)
    if len(values) == 1:
        return values[0]
    return z3.And(*values)


def _formula_from_groups(
    groups: Sequence[BmcTrackedConstraint],
) -> z3.BoolRef:
    """Rebuild one aggregate formula from ordered source groups.

    Each source group represents one domain-level fact and may contain more
    than one Boolean expression. Flattening groups in registration order
    preserves the relation builder's existing S-expression shape while making
    the tracked partition the source of the aggregate formula.

    :param groups: Ordered source groups for one formula component.
    :type groups: Sequence[pyfcstm.bmc.provenance.BmcTrackedConstraint]
    :return: Conjunction of all group expressions.
    :rtype: z3.BoolRef

    Examples::

        >>> import z3
        >>> from pyfcstm.bmc.provenance import BmcSourceRef, BmcTrackedConstraint
        >>> group = BmcTrackedConstraint(
        ...     "x", "kernel", "domain", (z3.Bool("x"),),
        ...     BmcSourceRef("generated", None, None),
        ... )
        >>> str(_formula_from_groups((group,)))
        'x'
    """
    return _and(expression for group in groups for expression in group.expressions)


def _append_tracked_group(
    groups: List[BmcTrackedConstraint],
    *,
    stable_id: str,
    stage: str,
    category: str,
    expressions: Iterable[z3.ExprRef],
    source_ref,
    refs: Optional[Mapping[str, object]] = None,
) -> None:
    """Register one non-empty source group at its formula creation site.

    The relation layer owns the Z3-specific validation while the provenance
    module remains solver-independent.  Keeping registration adjacent to the
    original conjunct construction prevents a later AST walk from guessing
    which generated expression came from which domain fact.

    :param groups: Mutable target group list.
    :type groups: List[BmcTrackedConstraint]
    :param stable_id: Deterministic group identifier.
    :type stable_id: str
    :param stage: Formula stage.
    :type stage: str
    :param category: Domain group category.
    :type category: str
    :param expressions: Boolean Z3 expressions for the group.
    :type expressions: Iterable[z3.ExprRef]
    :param source_ref: BMC source reference.
    :type source_ref: pyfcstm.bmc.provenance.BmcSourceRef
    :param refs: Stable frame/step/case metadata, defaults to ``None``.
    :type refs: Optional[Mapping[str, object]], optional
    :return: ``None``.
    :rtype: None
    :raises pyfcstm.bmc.errors.BmcBuildError: If an expression is not Boolean.

    Examples::

        >>> import z3
        >>> from pyfcstm.bmc.provenance import BmcSourceRef
        >>> groups = []
        >>> _append_tracked_group(
        ...     groups, stable_id="x", stage="kernel", category="domain",
        ...     expressions=(z3.BoolVal(True),),
        ...     source_ref=BmcSourceRef("generated", None, None),
        ... )
        >>> groups[0].stable_id
        'x'
    """
    values = tuple(expressions)
    if not values:
        raise BmcBuildError("tracked group expressions must be non-empty.")
    if not all(z3.is_bool(value) for value in values):
        raise BmcBuildError("tracked group expressions must be Boolean.")
    groups.append(
        BmcTrackedConstraint(
            stable_id=stable_id,
            stage=stage,
            category=category,
            expressions=values,
            source_ref=source_ref,
            refs=refs or {},
        )
    )


def _or(items: Iterable[z3.ExprRef]) -> z3.BoolRef:
    values = tuple(items)
    if not values:  # pragma: no cover - relation callers pass non-empty domains.
        return z3.BoolVal(False)
    if len(values) == 1:  # pragma: no cover - current state domains include sentinels.
        return values[0]
    return z3.Or(*values)


def _state_in(symbol: z3.ArithRef, state_ids: Sequence[int]) -> z3.BoolRef:
    ids = tuple(state_ids)
    if not ids:  # pragma: no cover - BmcDomain validates allowed state sets.
        raise _internal_bmc_error("state domain set is empty while building D_N.")
    return _or(symbol == z3.IntVal(state_id) for state_id in ids)


def _safe_symbol_fragment(value: str) -> str:
    body = re.sub(r"[^0-9A-Za-z_]+", "_", value).strip("_") or "item"
    digest = hashlib.sha1(value.encode("utf-8")).hexdigest()[:10]
    return "%s_%s" % (body[:80], digest)


def _case_transition_labels(case: CycleCase) -> Tuple[str, ...]:
    """Return distinct model-transition labels recorded by one macro case."""
    labels = {
        item.transition_label
        for item in case.guard_requirements
        if item.transition_label is not None
    }
    labels.update(
        item.transition_label
        for item in case.action_blocks
        if item.transition_label is not None
    )
    return tuple(sorted(labels))


def _model_state_by_path(context: BmcPreparedContext, path: str):
    return next(
        (
            state
            for state in context.model.walk_states()
            if ".".join(state.path) == path
        ),
        None,
    )


def _unique_event_transition(context: BmcPreparedContext, case: CycleCase):
    """Return an event-only model transition when the source is unambiguous."""
    if case.kind != "transition":
        return None
    event_paths = {
        item.path
        for item in case.used_events
        if item.polarity == "positive" and item.reason == "trigger"
    }
    if len(event_paths) != 1:
        return None
    owner = _model_state_by_path(context, case.source_state_path)
    if owner is None:
        return None
    matches = [
        transition
        for transition in owner.transitions_from
        if transition.event is not None and transition.event.path_name in event_paths
    ]
    return matches[0] if len(matches) == 1 else None


def _case_source_reference(
    context: BmcPreparedContext,
    case: CycleCase,
    generated_ref,
) -> Tuple[Any, Tuple[str, ...]]:
    """Resolve a uniquely transition-backed case to its model source span.

    Macro cases may combine several micro-transitions or contain only synthetic
    fallback control.  Such cases deliberately retain the generated reference;
    provenance must never pretend that one source span explains a composite or
    synthetic formula.
    """
    labels = _case_transition_labels(case)
    if not labels:
        transition = _unique_event_transition(context, case)
        if transition is not None:
            reference = context._source_registry.model_reference(transition)
            if reference.path is not None or reference.span is not None:
                return reference, labels
        return generated_ref, labels
    if len(labels) != 1:
        return generated_ref, labels

    parts = labels[0].rsplit("::", 2)
    if len(parts) != 3:
        return generated_ref, labels
    owner_path, index_text, _edge = parts
    try:
        transition_index = int(index_text)
    except ValueError:
        return generated_ref, labels
    if transition_index < 0:
        return generated_ref, labels

    owner = _model_state_by_path(context, owner_path)
    if owner is None:
        return generated_ref, labels
    transitions = tuple(owner.init_transitions) + tuple(owner.transitions_from)
    if transition_index >= len(transitions):
        return generated_ref, labels

    reference = context._source_registry.model_reference(transitions[transition_index])
    if reference.path is None and reference.span is None:
        return generated_ref, labels
    return reference, labels


def _domain_constraints_exprs(
    items: Sequence[DomainConstraint],
) -> Tuple[z3.ExprRef, ...]:
    return tuple(item.constraint for item in items)


def _failure_message(kind: str, reason: str, label: str) -> str:
    return "unsupported_bmc_core: %s failed while lowering %s: %s" % (
        kind,
        label,
        reason,
    )


def _raise_expr_failure(result, label: str) -> None:
    failure = getattr(result, "failure", None)
    if failure is None:
        return
    message = _failure_message(failure.kind, failure.reason, label)
    if failure.kind in {"not_implemented", "z3_error", "type_error", "value_error"}:
        raise UnsupportedBmcQuery(message)
    raise BmcBuildError(
        message
    )  # pragma: no cover - current translators use known failure kinds.


def _expect_bool(expr: _Z3Expr, label: str) -> z3.BoolRef:
    if not z3.is_bool(expr):  # pragma: no cover - binder/model typing prevents this.
        raise UnsupportedBmcQuery("%s must lower to a Boolean expression." % label)
    return expr


def _expect_arith(expr: _Z3Expr, label: str) -> z3.ArithRef:
    if not z3.is_arith(expr):  # pragma: no cover - binder/model typing prevents this.
        raise UnsupportedBmcQuery("%s must lower to a numeric expression." % label)
    return expr


@dataclass(frozen=True)
class _LoweredValue:
    expr: _Z3Expr
    definedness_constraints: Tuple[DomainConstraint, ...] = ()


@dataclass(frozen=True)
class _LoweredBoolTemplate:
    expr: z3.BoolRef
    definedness_constraints: Tuple[DomainConstraint, ...] = ()


@dataclass(frozen=True)
class BmcTraceSymbols:
    """Z3 symbols for one bounded BMC trace.

    :param domain: Domain snapshot that owns the symbols.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param frame_states: State-id symbols for ``F_0..F_N``.
    :type frame_states: Tuple[z3.ArithRef, ...]
    :param frame_vars: Per-frame persistent-variable symbols.
    :type frame_vars: Tuple[Mapping[str, z3.ArithRef], ...]
    :param event_inputs: Per-step event-input symbols.
    :type event_inputs: Tuple[Mapping[str, z3.BoolRef], ...]
    :param delta_flags: Per-step semantic-delta observation symbols.
    :type delta_flags: Tuple[z3.BoolRef, ...]
    :param gamma_flags: Per-step fallback observation symbols.
    :type gamma_flags: Tuple[z3.BoolRef, ...]
    :param case_selectors: Per-step case-selector symbols.
    :type case_selectors: Tuple[Mapping[str, z3.BoolRef], ...]

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
        >>> symbols = BmcTraceSymbols.allocate(domain, {0: ('case0',)})
        >>> symbols.frame_state(0).sort().name()
        'Int'
        >>> 'case0' in symbols.case_selectors[0]
        True
    """

    domain: BmcDomain
    frame_states: Tuple[z3.ArithRef, ...]
    frame_vars: Tuple[Mapping[str, z3.ArithRef], ...]
    event_inputs: Tuple[Mapping[str, z3.BoolRef], ...]
    delta_flags: Tuple[z3.BoolRef, ...]
    gamma_flags: Tuple[z3.BoolRef, ...]
    case_selectors: Tuple[Mapping[str, z3.BoolRef], ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not isinstance(self.domain, BmcDomain):
            raise BmcBuildError("domain must be BmcDomain.")
        if len(self.frame_states) != self.domain.bound + 1:
            raise BmcBuildError("frame_states must contain bound + 1 symbols.")
        if len(self.frame_vars) != self.domain.bound + 1:
            raise BmcBuildError("frame_vars must contain bound + 1 mappings.")
        if len(self.event_inputs) != self.domain.bound:
            raise BmcBuildError("event_inputs must contain bound mappings.")
        if len(self.delta_flags) != self.domain.bound:
            raise BmcBuildError("delta_flags must contain bound symbols.")
        if len(self.gamma_flags) != self.domain.bound:
            raise BmcBuildError("gamma_flags must contain bound symbols.")
        if not all(z3.is_bool(item) for item in self.delta_flags):
            raise BmcBuildError("delta_flags must contain Z3 Boolean expressions.")
        if not all(z3.is_bool(item) for item in self.gamma_flags):
            raise BmcBuildError("gamma_flags must contain Z3 Boolean expressions.")
        if len(self.case_selectors) != self.domain.bound:
            raise BmcBuildError("case_selectors must contain bound mappings.")
        object.__setattr__(
            self,
            "frame_vars",
            tuple(
                {key: value for key, value in mapping.items()}
                for mapping in self.frame_vars
            ),
        )
        object.__setattr__(
            self,
            "event_inputs",
            tuple(
                {key: value for key, value in mapping.items()}
                for mapping in self.event_inputs
            ),
        )
        object.__setattr__(
            self,
            "case_selectors",
            tuple(
                {key: value for key, value in mapping.items()}
                for mapping in self.case_selectors
            ),
        )

    @classmethod
    def allocate(
        cls,
        domain: BmcDomain,
        case_labels_by_step: Optional[Mapping[int, Sequence[str]]] = None,
    ) -> "BmcTraceSymbols":
        """Allocate trace symbols for ``domain``.

        :param domain: Domain snapshot to allocate for.
        :type domain: pyfcstm.bmc.domain.BmcDomain
        :param case_labels_by_step: Optional mapping from step index to case
            labels that need selector symbols, defaults to ``None``.
        :type case_labels_by_step: Optional[Mapping[int, Sequence[str]]], optional
        :return: Allocated symbol bundle.
        :rtype: BmcTraceSymbols
        :raises pyfcstm.bmc.errors.BmcBuildError: If the domain is malformed.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> BmcTraceSymbols.allocate(domain).to_canonical()['node']
            'bmc_trace_symbols'
        """
        if not isinstance(domain, BmcDomain):
            raise BmcBuildError("domain must be BmcDomain.")
        labels_by_step = case_labels_by_step or {}
        frame_states = tuple(
            z3.Int("F_%d_state" % frame.index) for frame in domain.frames
        )
        frame_vars = []
        for frame in domain.frames:
            mapping = {}
            for var in domain.variables:
                symbol_name = "F_%d_%s" % (frame.index, _safe_symbol_fragment(var.name))
                if var.declared_type == "int":
                    mapping[var.name] = z3.Int(symbol_name)
                elif var.declared_type == "float":
                    mapping[var.name] = z3.Real(symbol_name)
                else:  # pragma: no cover - BmcDomain only admits int/float vars.
                    raise BmcBuildError(
                        "Unsupported persistent variable type for BMC relation: %r."
                        % var.declared_type
                    )
            frame_vars.append(mapping)
        event_inputs = []
        for step in domain.steps:
            mapping = {}
            for event in domain.events:
                mapping[event.path] = z3.Bool(
                    "E_%d_event_%d_%s"
                    % (step.index, event.id, _safe_symbol_fragment(event.path))
                )
            event_inputs.append(mapping)
        delta_flags = tuple(z3.Bool("Delta_%d" % step.index) for step in domain.steps)
        gamma_flags = tuple(z3.Bool("Gamma_%d" % step.index) for step in domain.steps)
        case_selectors = []
        for step in domain.steps:
            labels = tuple(labels_by_step.get(step.index, ()))
            if len(set(labels)) != len(labels):
                raise _internal_bmc_error(
                    "duplicate case labels supplied for step %d." % step.index
                )
            case_selectors.append(
                {
                    label: z3.Bool(
                        "C_%d_%s" % (step.index, _safe_symbol_fragment(label))
                    )
                    for label in labels
                }
            )
        return cls(
            domain=domain,
            frame_states=frame_states,
            frame_vars=tuple(frame_vars),
            event_inputs=tuple(event_inputs),
            delta_flags=delta_flags,
            gamma_flags=gamma_flags,
            case_selectors=tuple(case_selectors),
        )

    def frame_state(self, frame_index: int) -> z3.ArithRef:
        """Return the state symbol for a frame.

        :param frame_index: Frame index in ``0..N``.
        :type frame_index: int
        :return: State-id symbol.
        :rtype: z3.ArithRef
        :raises pyfcstm.bmc.errors.BmcBuildError: If ``frame_index`` is invalid.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> BmcTraceSymbols.allocate(domain).frame_state(0).decl().name()
            'F_0_state'
        """
        if frame_index < 0 or frame_index >= len(self.frame_states):
            raise BmcBuildError("frame index out of range: %r." % frame_index)
        return self.frame_states[frame_index]

    def frame_var(self, frame_index: int, name: str) -> z3.ArithRef:
        """Return a persistent-variable symbol for a frame.

        :param frame_index: Frame index in ``0..N``.
        :type frame_index: int
        :param name: Persistent variable name.
        :type name: str
        :return: Variable symbol.
        :rtype: z3.ArithRef
        :raises pyfcstm.bmc.errors.BmcBuildError: If the frame or variable is
            unknown.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('def int x = 0; state Root;'), 1)
            >>> BmcTraceSymbols.allocate(domain).frame_var(0, 'x').sort().name()
            'Int'
        """
        if frame_index < 0 or frame_index >= len(self.frame_vars):
            raise BmcBuildError("frame index out of range: %r." % frame_index)
        try:
            return self.frame_vars[frame_index][name]
        except KeyError as err:
            # KeyError: the requested variable name is absent from this domain's
            # persistent-variable symbol mapping.
            raise BmcBuildError("Unknown frame variable: %r." % name) from err

    def event_input(self, step_index: int, event_path: str) -> z3.BoolRef:
        """Return an event-input symbol for a step.

        :param step_index: Step index in ``0..N-1``.
        :type step_index: int
        :param event_path: Fully resolved event path.
        :type event_path: str
        :return: Event-input symbol.
        :rtype: z3.BoolRef
        :raises pyfcstm.bmc.errors.BmcBuildError: If the step or event is
            unknown.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root { event Go; state A; [*] -> A; }')
            >>> domain = build_bmc_domain(model, 1)
            >>> BmcTraceSymbols.allocate(domain).event_input(0, 'Root.Go').sort().name()
            'Bool'
        """
        if step_index < 0 or step_index >= len(self.event_inputs):
            raise BmcBuildError("step index out of range: %r." % step_index)
        try:
            return self.event_inputs[step_index][event_path]
        except KeyError as err:
            # KeyError: the requested event path is absent from this domain's
            # per-step event-input mapping.
            raise BmcBuildError("Unknown event input: %r." % event_path) from err

    def delta_flag(self, step_index: int) -> z3.BoolRef:
        """Return the semantic-delta observation symbol for a step.

        :param step_index: Step index in ``0..N-1``.
        :type step_index: int
        :return: ``Delta_i`` observation symbol.
        :rtype: z3.BoolRef
        :raises pyfcstm.bmc.errors.BmcBuildError: If ``step_index`` is invalid.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> BmcTraceSymbols.allocate(domain).delta_flag(0).sort().name()
            'Bool'
        """
        if step_index < 0 or step_index >= len(self.delta_flags):
            raise BmcBuildError("step index out of range: %r." % step_index)
        return self.delta_flags[step_index]

    def gamma_flag(self, step_index: int) -> z3.BoolRef:
        """Return the fallback observation symbol for a step.

        :param step_index: Step index in ``0..N-1``.
        :type step_index: int
        :return: ``Gamma_i`` observation symbol.
        :rtype: z3.BoolRef
        :raises pyfcstm.bmc.errors.BmcBuildError: If ``step_index`` is invalid.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> BmcTraceSymbols.allocate(domain).gamma_flag(0).sort().name()
            'Bool'
        """
        if step_index < 0 or step_index >= len(self.gamma_flags):
            raise BmcBuildError("step index out of range: %r." % step_index)
        return self.gamma_flags[step_index]

    def active_state(self, frame_index: int, state_path: str) -> z3.BoolRef:
        """Return the ancestor-or-self active predicate for ``state_path``.

        :param frame_index: Frame index in ``0..N``.
        :type frame_index: int
        :param state_path: Model state path queried by ``active(...)``.
        :type state_path: str
        :return: Z3 predicate for public active-path observation.
        :rtype: z3.BoolRef
        :raises pyfcstm.bmc.errors.BmcBuildError: If the frame is invalid.
        :raises pyfcstm.bmc.errors.InvalidBmcDomain: If ``state_path`` is unknown.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> BmcTraceSymbols.allocate(domain).active_state(0, 'Root').sort().name()
            'Bool'
        """
        frame = self.frame_state(frame_index)
        target = self.domain.state_by_path(state_path)
        if target.is_sentinel:
            return z3.BoolVal(False)
        target_path = target.path
        active_ids: List[int] = []
        for entry in self.domain.states:
            if entry.id == STATE_INIT_ID:
                if target.is_root:
                    active_ids.append(entry.id)
                continue
            if entry.id == STATE_TERMINATE_ID or entry.is_sentinel:
                continue
            current = entry.path
            while True:
                if current == target_path:
                    active_ids.append(entry.id)
                    break
                parent = self.domain.state_by_path(current).parent_path
                if parent is None:
                    break
                current = parent
        return _or(frame == z3.IntVal(state_id) for state_id in active_ids)

    def case_selector(self, step_index: int, label: str) -> z3.BoolRef:
        """Return a case-selector symbol for a step.

        :param step_index: Step index in ``0..N-1``.
        :type step_index: int
        :param label: Macro-step case label.
        :type label: str
        :return: Case-selector symbol.
        :rtype: z3.BoolRef
        :raises pyfcstm.bmc.errors.BmcBuildError: If the selector is unknown.

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> symbols = BmcTraceSymbols.allocate(domain, {0: ('Root::fallback::Root::0',)})
            >>> symbols.case_selector(0, 'Root::fallback::Root::0').sort().name()
            'Bool'
        """
        if step_index < 0 or step_index >= len(self.case_selectors):
            raise BmcBuildError("step index out of range: %r." % step_index)
        try:
            return self.case_selectors[step_index][label]
        except KeyError as err:
            # KeyError: the requested case label is absent from this step's
            # selector mapping.
            raise BmcBuildError("Unknown case selector: %r." % label) from err

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable symbol summary.

        :return: Canonical symbol dictionary.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc.domain import build_bmc_domain
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> domain = build_bmc_domain(load_state_machine_from_text('state Root;'), 1)
            >>> BmcTraceSymbols.allocate(domain).to_canonical()['frame_states'][0]
            'F_0_state'
        """
        return {
            "node": "bmc_trace_symbols",
            "bound": self.domain.bound,
            "frame_states": [_z3_text(item) for item in self.frame_states],
            "frame_vars": [
                {name: _z3_text(expr) for name, expr in sorted(mapping.items())}
                for mapping in self.frame_vars
            ],
            "event_inputs": [
                {name: _z3_text(expr) for name, expr in sorted(mapping.items())}
                for mapping in self.event_inputs
            ],
            "delta_flags": [_z3_text(item) for item in self.delta_flags],
            "gamma_flags": [_z3_text(item) for item in self.gamma_flags],
            "case_selectors": [
                {name: _z3_text(expr) for name, expr in sorted(mapping.items())}
                for mapping in self.case_selectors
            ],
        }


@dataclass(frozen=True)
class BmcCaseRelation:
    """Lowered relation for one macro-step case.

    :param step_index: Step index owning this case.
    :type step_index: int
    :param case: Macro-step case that was lowered.
    :type case: pyfcstm.bmc.macro.CycleCase
    :param selector: Case-selector symbol bound to ``antecedent``.  The
        relation builder treats macro-step partition validity as an upstream
        contract: selector equality exposes selected cases but does not
        independently diagnose malformed partitions.
    :type selector: z3.BoolRef
    :param antecedent: Source guard and lowered case condition.
    :type antecedent: z3.BoolRef
    :param consequent: Target-state, post-var, and definedness constraints.
    :type consequent: z3.BoolRef
    :param implication: ``z3.Implies(antecedent, consequent)``.
    :type implication: z3.BoolRef
    :param selector_constraint: Equality between selector and antecedent.
    :type selector_constraint: z3.BoolRef
    :param post_var_exprs: Final expression for every persistent variable.
    :type post_var_exprs: Mapping[str, z3.ArithRef]
    :param guard_terms: Lowered guard terms keyed by requirement id.
    :type guard_terms: Mapping[str, z3.BoolRef]
    :param definedness_constraints: Runtime-definedness constraints in source
        order.
    :type definedness_constraints: Tuple[pyfcstm.solver.domain.DomainConstraint, ...]

    Example::

        >>> import z3
        >>> from pyfcstm.bmc.macro import BoolTemplate, CycleCase
        >>> case = CycleCase('fallback', 0, 'Root', 0, 'Root', 'Root::fallback::Root::0', BoolTemplate.true(), ())
        >>> rel = BmcCaseRelation(0, case, z3.Bool('c'), z3.BoolVal(True), z3.BoolVal(True), z3.BoolVal(True), z3.BoolVal(True), {}, {}, ())
        >>> rel.to_canonical()['case_label']
        'Root::fallback::Root::0'
    """

    step_index: int
    case: CycleCase
    selector: z3.BoolRef
    antecedent: z3.BoolRef
    consequent: z3.BoolRef
    implication: z3.BoolRef
    selector_constraint: z3.BoolRef
    post_var_exprs: Mapping[str, z3.ArithRef]
    guard_terms: Mapping[str, z3.BoolRef]
    definedness_constraints: Tuple[DomainConstraint, ...] = ()
    call_records: Tuple[BmcAbstractCallRecord, ...] = ()

    def __post_init__(self) -> None:
        if isinstance(self.step_index, bool) or not isinstance(self.step_index, int):
            raise BmcBuildError("step_index must be an integer.")
        if self.step_index < 0:
            raise BmcBuildError("step_index must be non-negative.")
        if not isinstance(self.case, CycleCase):
            raise BmcBuildError("case must be CycleCase.")
        for name in (
            "selector",
            "antecedent",
            "consequent",
            "implication",
            "selector_constraint",
        ):
            if not z3.is_bool(getattr(self, name)):
                raise BmcBuildError("%s must be a Z3 Boolean expression." % name)
        post_vars = {key: value for key, value in self.post_var_exprs.items()}
        if not all(z3.is_arith(value) for value in post_vars.values()):
            raise BmcBuildError(
                "post_var_exprs must contain Z3 arithmetic expressions."
            )
        guard_terms = {key: value for key, value in self.guard_terms.items()}
        if not all(z3.is_bool(value) for value in guard_terms.values()):
            raise BmcBuildError("guard_terms must contain Z3 Boolean expressions.")
        if not all(
            isinstance(item, DomainConstraint) for item in self.definedness_constraints
        ):
            raise BmcBuildError(
                "definedness_constraints must contain DomainConstraint objects."
            )
        if not all(
            isinstance(item, BmcAbstractCallRecord) for item in self.call_records
        ):
            raise BmcBuildError(
                "call_records must contain BmcAbstractCallRecord objects."
            )
        object.__setattr__(self, "post_var_exprs", post_vars)
        object.__setattr__(self, "guard_terms", guard_terms)
        object.__setattr__(
            self, "definedness_constraints", tuple(self.definedness_constraints)
        )
        object.__setattr__(self, "call_records", tuple(self.call_records))

    @property
    def formula(self) -> z3.BoolRef:
        """Return selector binding and implication for this case.

        :return: Case formula.
        :rtype: z3.BoolRef

        Example::

            >>> import z3
            >>> from pyfcstm.bmc.macro import BoolTemplate, CycleCase
            >>> case = CycleCase('fallback', 0, 'Root', 0, 'Root', 'Root::fallback::Root::0', BoolTemplate.true(), ())
            >>> rel = BmcCaseRelation(0, case, z3.Bool('c'), z3.BoolVal(True), z3.BoolVal(True), z3.BoolVal(True), z3.BoolVal(True), {}, {}, ())
            >>> rel.formula.sort().name()
            'Bool'
        """
        return _and((self.selector_constraint, self.implication))

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable case-relation dictionary.

        :return: Canonical case relation.
        :rtype: Dict[str, object]

        Example::

            >>> import z3
            >>> from pyfcstm.bmc.macro import BoolTemplate, CycleCase
            >>> case = CycleCase('fallback', 0, 'Root', 0, 'Root', 'Root::fallback::Root::0', BoolTemplate.true(), ())
            >>> rel = BmcCaseRelation(0, case, z3.Bool('c'), z3.BoolVal(True), z3.BoolVal(True), z3.BoolVal(True), z3.BoolVal(True), {}, {}, ())
            >>> rel.to_canonical()['node']
            'bmc_case_relation'
        """
        return {
            "node": "bmc_case_relation",
            "step_index": self.step_index,
            "case_label": self.case.label,
            "case_kind": self.case.kind,
            "source_state_id": self.case.source_state_id,
            "target_state_id": self.case.target_state_id,
            "consumed_events": list(self.case.consumed_events),
            "selector": _z3_text(self.selector),
            "antecedent": _z3_text(self.antecedent),
            "consequent": _z3_text(self.consequent),
            "implication": _z3_text(self.implication),
            "selector_constraint": _z3_text(self.selector_constraint),
            "post_var_exprs": {
                name: _z3_text(expr)
                for name, expr in sorted(self.post_var_exprs.items())
            },
            "guard_terms": {
                name: _z3_text(expr) for name, expr in sorted(self.guard_terms.items())
            },
            "definedness_constraints": [
                _z3_text(item.constraint) for item in self.definedness_constraints
            ],
            "call_records": [item.to_canonical() for item in self.call_records],
        }


@dataclass(frozen=True)
class BmcStepRelation:
    """Lowered relation for one symbolic BMC step.

    :param step_index: Step index in ``0..N-1``.
    :type step_index: int
    :param formals: Macro-step formals consumed by this step.
    :type formals: Tuple[pyfcstm.bmc.macro.MacroStepFormal, ...]
    :param case_relations: Lowered case relations.
    :type case_relations: Tuple[BmcCaseRelation, ...]
    :param formula: Conjunction of selector bindings, implications, and step
        observation constraints.
    :type formula: z3.BoolRef
    :param delta_constraint: Equality tying ``Delta_i`` to delta antecedents.
    :type delta_constraint: z3.BoolRef
    :param gamma_constraint: Equality tying ``Gamma_i`` to fallback antecedents.
    :type gamma_constraint: z3.BoolRef
    :param progress_mutex_constraint: Mutual exclusion of delta and gamma.
    :type progress_mutex_constraint: z3.BoolRef

    Example::

        >>> import z3
        >>> step = BmcStepRelation(0, (), (), z3.BoolVal(True))
        >>> step.to_canonical()['step_index']
        0
    """

    step_index: int
    formals: Tuple[MacroStepFormal, ...]
    case_relations: Tuple[BmcCaseRelation, ...]
    formula: z3.BoolRef
    delta_constraint: z3.BoolRef = field(default_factory=lambda: z3.BoolVal(True))
    gamma_constraint: z3.BoolRef = field(default_factory=lambda: z3.BoolVal(True))
    progress_mutex_constraint: z3.BoolRef = field(
        default_factory=lambda: z3.BoolVal(True)
    )

    def __post_init__(self) -> None:
        if isinstance(self.step_index, bool) or not isinstance(self.step_index, int):
            raise BmcBuildError("step_index must be an integer.")
        if self.step_index < 0:
            raise BmcBuildError("step_index must be non-negative.")
        if not all(isinstance(item, MacroStepFormal) for item in self.formals):
            raise BmcBuildError("formals must contain MacroStepFormal objects.")
        if not all(isinstance(item, BmcCaseRelation) for item in self.case_relations):
            raise BmcBuildError("case_relations must contain BmcCaseRelation objects.")
        if not z3.is_bool(self.formula):
            raise BmcBuildError("formula must be a Z3 Boolean expression.")
        for name in (
            "delta_constraint",
            "gamma_constraint",
            "progress_mutex_constraint",
        ):
            if not z3.is_bool(getattr(self, name)):
                raise BmcBuildError("%s must be a Z3 Boolean expression." % name)
        object.__setattr__(self, "formals", tuple(self.formals))
        object.__setattr__(self, "case_relations", tuple(self.case_relations))

    @property
    def case_registry(self) -> Mapping[str, BmcCaseRelation]:
        """Return lowered cases keyed by label for this step.

        :return: Case-label mapping.
        :rtype: Mapping[str, BmcCaseRelation]

        Example::

            >>> import z3
            >>> BmcStepRelation(0, (), (), z3.BoolVal(True)).case_registry
            {}
        """
        return {item.case.label: item for item in self.case_relations}

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable step-relation dictionary.

        :return: Canonical step relation.
        :rtype: Dict[str, object]

        Example::

            >>> import z3
            >>> BmcStepRelation(0, (), (), z3.BoolVal(True)).to_canonical()['node']
            'bmc_step_relation'
        """
        return {
            "node": "bmc_step_relation",
            "step_index": self.step_index,
            "source_count": len(self.formals),
            "case_count": len(self.case_relations),
            "formula": _z3_text(self.formula),
            "delta_constraint": _z3_text(self.delta_constraint),
            "gamma_constraint": _z3_text(self.gamma_constraint),
            "progress_mutex_constraint": _z3_text(self.progress_mutex_constraint),
            "cases": [item.to_canonical() for item in self.case_relations],
        }


@dataclass(frozen=True)
class BmcCoreFormula:
    """Complete solver-level core formula for a bounded trace.

    :param context: Prepared BMC context consumed by the builder.
    :type context: pyfcstm.bmc.engine.BmcPreparedContext
    :param symbols: Trace symbols used by the formulas.
    :type symbols: BmcTraceSymbols
    :param domain_formula: ``D_N`` domain constraints.
    :type domain_formula: z3.BoolRef
    :param initial_formula: ``I_0`` initial-frame constraints.
    :type initial_formula: z3.BoolRef
    :param transition_formula: ``T_N`` transition relation.
    :type transition_formula: z3.BoolRef
    :param environment_formula: ``ENV_N`` environment assumptions.
    :type environment_formula: z3.BoolRef
    :param core: ``D_N ∧ I_0 ∧ T_N ∧ ENV_N``.
    :type core: z3.BoolRef
    :param steps: Lowered step relations.
    :type steps: Tuple[BmcStepRelation, ...]
    :param diagnostics: Reserved build-time diagnostics, defaults to ``()``.
        Relation-level semantic-delta information is currently exposed through
        case metadata, so this tuple is empty in the initial core-relation
        builder.
    :type diagnostics: Tuple[str, ...], optional

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> context = BmcEngine(model).prepare('check reach <= 1: terminated();')
        >>> build_bmc_core_formula(context).to_canonical()['bound']
        1
    """

    context: BmcPreparedContext
    symbols: BmcTraceSymbols
    domain_formula: z3.BoolRef
    initial_formula: z3.BoolRef
    transition_formula: z3.BoolRef
    environment_formula: z3.BoolRef
    core: z3.BoolRef
    steps: Tuple[BmcStepRelation, ...]
    diagnostics: Tuple[str, ...] = ()
    _tracked_groups: Tuple[BmcTrackedConstraint, ...] = field(
        default_factory=tuple, repr=False, compare=False
    )

    def __post_init__(self) -> None:
        _require_context(self.context)
        if not isinstance(self.symbols, BmcTraceSymbols):
            raise BmcBuildError("symbols must be BmcTraceSymbols.")
        for name in (
            "domain_formula",
            "initial_formula",
            "transition_formula",
            "environment_formula",
            "core",
        ):
            if not z3.is_bool(getattr(self, name)):
                raise BmcBuildError("%s must be a Z3 Boolean expression." % name)
        if not all(isinstance(item, BmcStepRelation) for item in self.steps):
            raise BmcBuildError("steps must contain BmcStepRelation objects.")
        if not all(isinstance(item, str) for item in self.diagnostics):
            raise BmcBuildError("diagnostics must contain strings.")
        object.__setattr__(self, "steps", tuple(self.steps))
        object.__setattr__(self, "diagnostics", tuple(self.diagnostics))
        groups = tuple(self._tracked_groups)
        if not all(isinstance(item, BmcTrackedConstraint) for item in groups):
            raise BmcBuildError(
                "tracked groups must contain BmcTrackedConstraint objects."
            )
        stable_ids = [item.stable_id for item in groups]
        if len(set(stable_ids)) != len(stable_ids):
            raise BmcBuildError("tracked groups must have unique stable ids.")
        for group in groups:
            for expression in group.expressions:
                if not z3.is_bool(expression):
                    raise BmcBuildError(
                        "tracked group expressions must be Z3 Boolean expressions."
                    )
                if expression.ctx != self.core.ctx:
                    raise BmcBuildError(
                        "tracked group expressions must share the core Z3 context."
                    )
        object.__setattr__(self, "_tracked_groups", groups)

    def to_canonical(self) -> _CanonicalDict:
        """Return a JSON-stable core-formula summary.

        :return: Canonical core formula.
        :rtype: Dict[str, object]

        Example::

            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('state Root;')
            >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
            >>> core.to_canonical()['node']
            'bmc_core_formula'
        """
        return {
            "node": "bmc_core_formula",
            "bound": self.context.bound,
            "formulas": {
                "D_N": _z3_text(self.domain_formula),
                "I_0": _z3_text(self.initial_formula),
                "T_N": _z3_text(self.transition_formula),
                "ENV_N": _z3_text(self.environment_formula),
                "Core_N": _z3_text(self.core),
            },
            "symbols": self.symbols.to_canonical(),
            "steps": [item.to_canonical() for item in self.steps],
            "diagnostics": list(self.diagnostics),
        }


def _z3_arith_binary(
    op: str, left: z3.ArithRef, right: z3.ArithRef, label: str
) -> _Z3Expr:
    try:
        if op == "+":
            return left + right
        if op == "-":
            return left - right
        if op == "*":
            return left * right
        if op == "/":
            return left / right
        if op == "%":
            return left % right
        if op == "**":
            return left**right
        if op == "&":  # pragma: no cover - reserved for future BitVec profile.
            return left & right
        if op == "|":  # pragma: no cover - reserved for future BitVec profile.
            return left | right
        if op == "^":  # pragma: no cover - reserved for future BitVec profile.
            return left ^ right
        if op == "<<":  # pragma: no cover - reserved for future BitVec profile.
            return left << right
        if op == ">>":  # pragma: no cover - reserved for future BitVec profile.
            return left >> right
    except TypeError as err:
        # TypeError: Python or Z3 operator overloads reject unsupported operand
        # sort combinations, such as bitwise operators on Real expressions.
        raise UnsupportedBmcQuery(
            "%s is unsupported for operator %s: %s" % (label, op, err)
        ) from err
    except (
        z3.Z3Exception
    ) as err:  # pragma: no cover - TypeError covers current sort failures.
        # Z3Exception: Z3 rejects malformed arithmetic expressions or sort
        # combinations after overload dispatch.
        raise UnsupportedBmcQuery(
            "%s is unsupported for operator %s: %s" % (label, op, err)
        ) from err
    raise UnsupportedBmcQuery(  # pragma: no cover - AST validates operator names.
        "%s uses unsupported numeric operator %r." % (label, op)
    )


def _z3_comparison(
    op: str, left: z3.ArithRef, right: z3.ArithRef, label: str
) -> z3.BoolRef:
    try:
        if op == "<":
            return left < right
        if op == "<=":
            return left <= right
        if op == ">":
            return left > right
        if op == ">=":
            return left >= right
        if op == "==":
            return left == right
        if op == "!=":
            return left != right
    except (
        TypeError
    ) as err:  # pragma: no cover - current AST/binder keeps comparisons well typed.
        # TypeError: Python/Z3 comparison overloads reject unsupported operand
        # shapes before Z3 creates an expression.
        raise UnsupportedBmcQuery(
            "%s comparison %s is unsupported: %s" % (label, op, err)
        ) from err
    except (
        z3.Z3Exception
    ) as err:  # pragma: no cover - current AST/binder keeps comparisons well typed.
        # Z3Exception: Z3 rejects malformed comparison sort combinations.
        raise UnsupportedBmcQuery(
            "%s comparison %s is unsupported: %s" % (label, op, err)
        ) from err
    raise UnsupportedBmcQuery(  # pragma: no cover - AST validates operator names.
        "%s uses unsupported comparison operator %r." % (label, op)
    )


def _z3_ufunc(func: str, operand: z3.ArithRef, label: str) -> _LoweredValue:
    constraints = []
    try:
        if func == "abs":
            return _LoweredValue(z3.If(operand >= 0, operand, -operand))
        if func == "sign":
            zero = z3.IntVal(0) if z3.is_int(operand) else z3.RealVal(0)
            one = z3.IntVal(1) if z3.is_int(operand) else z3.RealVal(1)
            minus_one = z3.IntVal(-1) if z3.is_int(operand) else z3.RealVal(-1)
            return _LoweredValue(
                z3.If(operand == zero, zero, z3.If(operand > zero, one, minus_one))
            )
        if func == "floor":
            return _LoweredValue(operand if z3.is_int(operand) else z3.ToInt(operand))
        if func == "ceil":
            return _LoweredValue(operand if z3.is_int(operand) else -z3.ToInt(-operand))
        if func == "trunc":
            if z3.is_int(operand):
                return _LoweredValue(operand)
            return _LoweredValue(
                z3.If(operand >= 0, z3.ToInt(operand), -z3.ToInt(-operand))
            )
        if func == "round":
            from pyfcstm.solver.expr import python_round_to_z3

            return _LoweredValue(python_round_to_z3(operand))
        if func == "sqrt":
            constraints.append(
                DomainConstraint(operand >= 0, DomainSource(label=label))
            )
            root = z3.Sqrt(operand if z3.is_real(operand) else z3.ToReal(operand))
            return _LoweredValue(root, tuple(constraints))
    except TypeError as err:  # pragma: no cover - current ufunc calls are arith-sorted.
        # TypeError: Python/Z3 overloads reject unsupported function operands.
        raise UnsupportedBmcQuery(
            "%s function %s is unsupported: %s" % (label, func, err)
        ) from err
    except (
        z3.Z3Exception
    ) as err:  # pragma: no cover - current ufunc calls are arith-sorted.
        # Z3Exception: Z3 rejects unsupported function operand sorts.
        raise UnsupportedBmcQuery(
            "%s function %s is unsupported: %s" % (label, func, err)
        ) from err
    raise UnsupportedBmcQuery("%s uses unsupported function %r." % (label, func))


def _resolve_frame(frame_selector: object, current_frame: int, bound: int) -> int:
    if frame_selector == "current":
        return current_frame
    if isinstance(frame_selector, bool) or not isinstance(
        frame_selector, int
    ):  # pragma: no cover - binder validates selectors.
        raise BmcBuildError("Invalid frame selector: %r." % (frame_selector,))
    if (
        frame_selector < 0 or frame_selector > bound
    ):  # pragma: no cover - binder validates selectors.
        raise BmcBuildError("Frame selector out of range: %r." % frame_selector)
    return frame_selector  # pragma: no cover - binder disallows explicit frame selectors here.


def _resolve_step(selector: object, current_step: Optional[int], bound: int) -> int:
    if (
        selector == "current"
    ):  # pragma: no cover - relation callers currently use frame predicates.
        if (
            current_step is None
        ):  # pragma: no cover - frame-only callers have no step context.
            raise UnsupportedBmcQuery(
                "event(..., current) needs a transition step context."
            )
        return current_step
    if isinstance(selector, bool) or not isinstance(
        selector, int
    ):  # pragma: no cover - binder validates selectors.
        raise BmcBuildError("Invalid step selector: %r." % (selector,))
    if (
        selector < 0 or selector >= bound
    ):  # pragma: no cover - binder validates selectors.
        raise BmcBuildError("Step selector out of range: %r." % selector)
    return (
        selector  # pragma: no cover - relation callers currently use frame predicates.
    )


def _lower_bmc_num_expr(
    expr: BmcNumExpr,
    symbols: BmcTraceSymbols,
    *,
    frame_index: int,
    step_index: Optional[int] = None,
    call_count_lowerer: Optional[_CallCountLowerer] = None,
) -> _LoweredValue:
    label = "BMC numeric expression %s" % expr
    if isinstance(expr, IntLiteral):
        return _LoweredValue(z3.IntVal(expr.value))
    if isinstance(expr, FloatLiteral):
        return _LoweredValue(z3.RealVal(str(expr.value)))
    if isinstance(expr, NameRef):
        return _LoweredValue(symbols.frame_var(frame_index, expr.name))
    if isinstance(expr, FrameVar):
        return _LoweredValue(symbols.frame_var(frame_index, expr.name))
    if isinstance(expr, Cycle):
        return _LoweredValue(z3.IntVal(frame_index))
    if isinstance(expr, CallCount):
        if call_count_lowerer is None:
            raise UnsupportedBmcQuery(
                "call_count() needs property call-record context."
            )
        return _LoweredValue(call_count_lowerer(expr, frame_index, step_index))
    if isinstance(expr, MathConst):
        constants = {"pi": math.pi, "E": math.e, "tau": math.tau}
        return _LoweredValue(z3.RealVal(str(constants[expr.name])))
    if isinstance(expr, NumUnaryOp):
        operand = _lower_bmc_num_expr(
            expr.operand,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        value = _expect_arith(operand.expr, label)
        if expr.op == "+":
            return _LoweredValue(value, operand.definedness_constraints)
        if expr.op == "-":
            return _LoweredValue(-value, operand.definedness_constraints)
        raise UnsupportedBmcQuery(  # pragma: no cover - AST validates operator names.
            "%s uses unsupported unary operator %r." % (label, expr.op)
        )
    if isinstance(expr, NumBinaryOp):
        left = _lower_bmc_num_expr(
            expr.left,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        right = _lower_bmc_num_expr(
            expr.right,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        left_expr = _expect_arith(left.expr, label)
        right_expr = _expect_arith(right.expr, label)
        constraints = [*left.definedness_constraints, *right.definedness_constraints]
        if expr.op in ("/", "%"):
            constraints.append(
                DomainConstraint(right_expr != 0, DomainSource(label=label))
            )
        return _LoweredValue(
            _z3_arith_binary(expr.op, left_expr, right_expr, label),
            tuple(constraints),
        )
    if isinstance(expr, NumConditionalOp):
        condition = _lower_bmc_cond_expr(
            expr.condition,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        condition_expr = _expect_bool(condition.expr, label)
        if z3.is_true(condition_expr):
            if_true = _lower_bmc_num_expr(
                expr.if_true,
                symbols,
                frame_index=frame_index,
                step_index=step_index,
                call_count_lowerer=call_count_lowerer,
            )
            return _LoweredValue(
                _expect_arith(if_true.expr, label),
                (*condition.definedness_constraints, *if_true.definedness_constraints),
            )
        if z3.is_false(condition_expr):
            if_false = _lower_bmc_num_expr(
                expr.if_false,
                symbols,
                frame_index=frame_index,
                step_index=step_index,
                call_count_lowerer=call_count_lowerer,
            )
            return _LoweredValue(
                _expect_arith(if_false.expr, label),
                (
                    *condition.definedness_constraints,
                    *if_false.definedness_constraints,
                ),
            )
        if_true = _lower_bmc_num_expr(
            expr.if_true,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        if_false = _lower_bmc_num_expr(
            expr.if_false,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        return _LoweredValue(
            z3.If(
                condition_expr,
                _expect_arith(if_true.expr, label),
                _expect_arith(if_false.expr, label),
            ),
            (
                *condition.definedness_constraints,
                *_guarded_domain_constraints(
                    condition_expr, if_true.definedness_constraints
                ),
                *_guarded_domain_constraints(
                    z3.Not(condition_expr), if_false.definedness_constraints
                ),
            ),
        )
    if isinstance(expr, UFuncCall):
        operand = _lower_bmc_num_expr(
            expr.operand,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        result = _z3_ufunc(expr.func, _expect_arith(operand.expr, label), label)
        return _LoweredValue(
            result.expr,
            (*operand.definedness_constraints, *result.definedness_constraints),
        )
    raise UnsupportedBmcQuery(  # pragma: no cover - current AST class set is closed.
        "Unsupported BMC numeric expression: %s." % type(expr).__name__
    )


def _lower_bmc_cond_expr(
    expr: BmcCondExpr,
    symbols: BmcTraceSymbols,
    *,
    frame_index: int,
    step_index: Optional[int] = None,
    call_count_lowerer: Optional[_CallCountLowerer] = None,
) -> _LoweredValue:
    label = "BMC condition expression %s" % expr
    if isinstance(expr, BoolLiteral):
        return _LoweredValue(z3.BoolVal(expr.value))
    if isinstance(expr, NumericComparison):
        left = _lower_bmc_num_expr(
            expr.left,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        right = _lower_bmc_num_expr(
            expr.right,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        return _LoweredValue(
            _z3_comparison(
                expr.op,
                _expect_arith(left.expr, label),
                _expect_arith(right.expr, label),
                label,
            ),
            (*left.definedness_constraints, *right.definedness_constraints),
        )
    if isinstance(expr, CondUnaryOp):
        operand = _lower_bmc_cond_expr(
            expr.operand,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        if expr.op == "!":
            return _LoweredValue(
                z3.Not(_expect_bool(operand.expr, label)),
                operand.definedness_constraints,
            )
        raise UnsupportedBmcQuery(  # pragma: no cover - AST validates operator names.
            "%s uses unsupported condition unary operator %r." % (label, expr.op)
        )
    if isinstance(expr, CondBinaryOp):
        left = _lower_bmc_cond_expr(
            expr.left,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        left_expr = _expect_bool(left.expr, label)
        if expr.op == "&&" and z3.is_false(left_expr):
            return _LoweredValue(z3.BoolVal(False), left.definedness_constraints)
        if expr.op == "||" and z3.is_true(left_expr):
            return _LoweredValue(z3.BoolVal(True), left.definedness_constraints)
        right = _lower_bmc_cond_expr(
            expr.right,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        right_expr = _expect_bool(right.expr, label)
        if expr.op == "&&":
            value = z3.And(left_expr, right_expr)
            definedness_constraints = (
                *left.definedness_constraints,
                *_guarded_domain_constraints(left_expr, right.definedness_constraints),
            )
        elif expr.op == "||":
            value = z3.Or(left_expr, right_expr)
            definedness_constraints = (
                *left.definedness_constraints,
                *_guarded_domain_constraints(
                    z3.Not(left_expr), right.definedness_constraints
                ),
            )
        elif expr.op == "=>":
            value = z3.Implies(left_expr, right_expr)
            definedness_constraints = (
                *left.definedness_constraints,
                *right.definedness_constraints,
            )
        elif expr.op == "xor":
            value = z3.Xor(left_expr, right_expr)
            definedness_constraints = (
                *left.definedness_constraints,
                *right.definedness_constraints,
            )
        elif expr.op in {"iff", "=="}:
            value = left_expr == right_expr
            definedness_constraints = (
                *left.definedness_constraints,
                *right.definedness_constraints,
            )
        elif expr.op == "!=":
            value = left_expr != right_expr
            definedness_constraints = (
                *left.definedness_constraints,
                *right.definedness_constraints,
            )
        else:
            raise UnsupportedBmcQuery(  # pragma: no cover - AST validates operator names.
                "%s uses unsupported condition operator %r." % (label, expr.op)
            )
        return _LoweredValue(value, definedness_constraints)
    if isinstance(expr, CondConditionalOp):
        condition = _lower_bmc_cond_expr(
            expr.condition,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        condition_expr = _expect_bool(condition.expr, label)
        if z3.is_true(condition_expr):
            if_true = _lower_bmc_cond_expr(
                expr.if_true,
                symbols,
                frame_index=frame_index,
                step_index=step_index,
                call_count_lowerer=call_count_lowerer,
            )
            return _LoweredValue(
                _expect_bool(if_true.expr, label),
                (*condition.definedness_constraints, *if_true.definedness_constraints),
            )
        if z3.is_false(condition_expr):
            if_false = _lower_bmc_cond_expr(
                expr.if_false,
                symbols,
                frame_index=frame_index,
                step_index=step_index,
                call_count_lowerer=call_count_lowerer,
            )
            return _LoweredValue(
                _expect_bool(if_false.expr, label),
                (
                    *condition.definedness_constraints,
                    *if_false.definedness_constraints,
                ),
            )
        if_true = _lower_bmc_cond_expr(
            expr.if_true,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        if_false = _lower_bmc_cond_expr(
            expr.if_false,
            symbols,
            frame_index=frame_index,
            step_index=step_index,
            call_count_lowerer=call_count_lowerer,
        )
        return _LoweredValue(
            z3.If(
                condition_expr,
                _expect_bool(if_true.expr, label),
                _expect_bool(if_false.expr, label),
            ),
            (
                *condition.definedness_constraints,
                *_guarded_domain_constraints(
                    condition_expr, if_true.definedness_constraints
                ),
                *_guarded_domain_constraints(
                    z3.Not(condition_expr), if_false.definedness_constraints
                ),
            ),
        )
    if isinstance(expr, Active):
        frame = _resolve_frame(expr.frame, frame_index, symbols.domain.bound)
        return _LoweredValue(symbols.active_state(frame, expr.state_path))
    if isinstance(expr, Terminated):
        frame = _resolve_frame(expr.frame, frame_index, symbols.domain.bound)
        return _LoweredValue(
            symbols.frame_state(frame) == z3.IntVal(STATE_TERMINATE_ID)
        )
    if isinstance(
        expr, Event
    ):  # pragma: no cover - environment assumptions lower event atoms separately.
        step = _resolve_step(expr.selector, step_index, symbols.domain.bound)
        event = symbols.domain.event_by_path(expr.event_path)
        return _LoweredValue(symbols.event_input(step, event.path))
    if isinstance(expr, Case):  # pragma: no cover - objective compiler owns case atoms.
        step = _resolve_step(expr.frame, step_index, symbols.domain.bound)
        return _LoweredValue(symbols.case_selector(step, expr.label))
    if isinstance(expr, Called):
        if call_count_lowerer is None:
            raise UnsupportedBmcQuery("called() needs property call-record context.")
        count_expr = call_count_lowerer(
            CallCount(expr.call_filter), frame_index, step_index
        )
        return _LoweredValue(_expect_arith(count_expr, label) >= z3.IntVal(1))
    raise UnsupportedBmcQuery(  # pragma: no cover - current AST class set is closed.
        "Unsupported BMC condition expression: %s." % type(expr).__name__
    )


def _translate_model_expr(expr: Expr, env: Mapping[str, _Z3Expr], label: str):
    result = translate_expr_domain(
        expr,
        dict(env),
        source=DomainSource(label=label),
        prune_unreachable=True,
    )
    _raise_expr_failure(result, label)
    if (
        result.z3_expr is None
    ):  # pragma: no cover - failures return through _raise_expr_failure.
        raise _internal_bmc_error("expression %s translated without a value." % label)
    return result


@dataclass(frozen=True)
class _CaseLowering:
    case: CycleCase
    guard_terms: Mapping[str, z3.BoolRef]
    guard_definedness: Mapping[str, Tuple[DomainConstraint, ...]]
    final_env: Mapping[str, z3.ArithRef]
    definedness_constraints: Tuple[DomainConstraint, ...]
    call_records: Tuple[BmcAbstractCallRecord, ...] = ()


def _guarded_domain_constraints(
    guard: z3.BoolRef,
    constraints: Sequence[DomainConstraint],
) -> Tuple[DomainConstraint, ...]:
    if z3.is_true(guard):
        return tuple(constraints)
    return tuple(
        DomainConstraint(z3.Implies(guard, item.constraint), item.source)
        for item in constraints
    )


def _append_guarded_constraints(
    target: List[DomainConstraint],
    guard: z3.BoolRef,
    constraints: Sequence[DomainConstraint],
) -> None:
    target.extend(_guarded_domain_constraints(guard, constraints))


def _lower_guard_requirement(
    guard: GuardRequirement,
    env: Mapping[str, _Z3Expr],
    constraints: Sequence[DomainConstraint],
    case_label: str,
) -> Tuple[z3.BoolRef, Tuple[DomainConstraint, ...]]:
    label = "guard %s in case %s" % (guard.requirement_id, case_label)
    result = _translate_model_expr(guard.expr, env, label)
    guard_expr = _expect_bool(result.z3_expr, label)
    if (
        guard.polarity == "negative"
    ):  # pragma: no cover - current expander emits positive guard requirements.
        guard_expr = z3.Not(guard_expr)
    elif (
        guard.polarity != "positive"
    ):  # pragma: no cover - GuardRequirement validates polarity.
        raise _internal_bmc_error("unknown guard polarity %r." % guard.polarity)
    return guard_expr, (*constraints, *result.definedness_constraints)


_RUNTIME_ROLE_TO_STAGE = {
    "state_enter": "enter",
    "state_exit": "exit",
    "leaf_during": "during",
    "plain_during_before": "during",
    "plain_during_after": "during",
    "aspect_during_before": "during",
    "aspect_during_after": "during",
    "transition_effect": "during",
}


def _stage_from_runtime_role(role: str) -> str:
    try:
        return _RUNTIME_ROLE_TO_STAGE[role]
    except KeyError as err:
        # KeyError: forged ActionBlock-like inputs can bypass the public
        # ActionBlock runtime-role validation and reach this private helper.
        raise BmcBuildError("unknown action runtime role %r." % role) from err


def _execute_action_block(
    block: ActionBlock,
    env: Mapping[str, _Z3Expr],
    case_label: str,
) -> Tuple[
    Mapping[str, z3.ArithRef],
    Tuple[DomainConstraint, ...],
    Tuple[BmcAbstractCallRecord, ...],
]:
    if block.is_abstract:
        action_name = block.action_name
        if action_name is None:
            return dict(env), (), ()
        stage = _stage_from_runtime_role(block.runtime_role)
        snapshot = {
            name: _expect_arith(
                value, "call snapshot %s in case %s" % (name, case_label)
            )
            for name, value in env.items()
        }
        record = BmcAbstractCallRecord(
            0,
            action_name,
            stage,
            block.runtime_role,
            block.execution_state_path or block.owner_state_path,
            block.active_leaf_path or block.owner_state_path,
            block.named_ref,
            snapshot,
        )
        return dict(env), (), (record,)
    execution = execute_operations_domain(
        list(block.operations),
        dict(env),
        source=DomainSource(
            label="action block %s in case %s" % (block.runtime_role, case_label)
        ),
        prune_unreachable=True,
    )
    if execution.failure is not None:
        failure = execution.failure
        message = _failure_message(
            failure.kind,
            failure.reason,
            "action block %s in case %s" % (block.runtime_role, case_label),
        )
        raise UnsupportedBmcQuery(message)
    return dict(execution.env), tuple(execution.definedness_constraints), ()


def _prepare_case_lowering(
    case: CycleCase, pre_env: Mapping[str, _Z3Expr]
) -> _CaseLowering:
    guards_by_anchor: Dict[int, List[GuardRequirement]] = {}
    for guard in case.guard_requirements:
        guards_by_anchor.setdefault(guard.after_action_block_index, []).append(guard)
    env = dict(pre_env)
    guard_terms: Dict[str, z3.BoolRef] = {}
    guard_definedness: Dict[str, Tuple[DomainConstraint, ...]] = {}
    definedness: List[DomainConstraint] = []
    call_records: List[BmcAbstractCallRecord] = []
    for anchor in range(len(case.action_blocks) + 1):
        for guard in sorted(
            guards_by_anchor.get(anchor, ()), key=lambda item: item.requirement_id
        ):
            term, new_definedness = _lower_guard_requirement(
                guard, env, definedness, case.label
            )
            guard_terms[guard.requirement_id] = term
            guard_definedness[guard.requirement_id] = tuple(new_definedness)
            definedness = list(new_definedness)
        if anchor < len(case.action_blocks):
            env, block_definedness, block_call_records = _execute_action_block(
                case.action_blocks[anchor], env, case.label
            )
            definedness.extend(block_definedness)
            for record in block_call_records:
                call_records.append(
                    BmcAbstractCallRecord(
                        len(call_records),
                        record.action_name,
                        record.stage,
                        record.role,
                        record.state_path,
                        record.active_leaf_path,
                        record.named_ref,
                        record.snapshot,
                    )
                )
    return _CaseLowering(
        case=case,
        guard_terms=guard_terms,
        guard_definedness=guard_definedness,
        final_env=env,
        definedness_constraints=tuple(definedness),
        call_records=tuple(call_records),
    )


def _lower_bool_template(
    template: BoolTemplate,
    lowering: _CaseLowering,
    accepted_lookup,
    active: Set[str],
    symbols: BmcTraceSymbols,
    step_index: int,
) -> _LoweredBoolTemplate:
    if template.kind == "true":
        return _LoweredBoolTemplate(z3.BoolVal(True))
    if (
        template.kind == "false"
    ):  # pragma: no cover - false macro paths are pruned before lowering.
        return _LoweredBoolTemplate(z3.BoolVal(False))
    if template.kind == "not":
        operand = _lower_bool_template(
            template.operands[0],
            lowering,
            accepted_lookup,
            active,
            symbols,
            step_index,
        )
        return _LoweredBoolTemplate(
            z3.Not(operand.expr), operand.definedness_constraints
        )
    if template.kind == "and":
        expr = z3.BoolVal(True)
        definedness: List[DomainConstraint] = []
        for item in template.operands:
            lowered = _lower_bool_template(
                item,
                lowering,
                accepted_lookup,
                active,
                symbols,
                step_index,
            )
            _append_guarded_constraints(
                definedness, expr, lowered.definedness_constraints
            )
            expr = z3.And(expr, lowered.expr)
        return _LoweredBoolTemplate(expr, tuple(definedness))
    if template.kind == "or":
        expr = z3.BoolVal(False)
        definedness = []
        for item in template.operands:
            lowered = _lower_bool_template(
                item,
                lowering,
                accepted_lookup,
                active,
                symbols,
                step_index,
            )
            _append_guarded_constraints(
                definedness, z3.Not(expr), lowered.definedness_constraints
            )
            expr = z3.Or(expr, lowered.expr)
        return _LoweredBoolTemplate(expr, tuple(definedness))
    if template.kind == "atom":
        atom = template.name
        if atom is None:  # pragma: no cover - BoolTemplate validates atom names.
            raise _internal_bmc_error("BoolTemplate atom has no name.")
        if atom.startswith(_EVENT_ATOM_PREFIX):
            return _LoweredBoolTemplate(
                symbols.event_input(step_index, atom[len(_EVENT_ATOM_PREFIX) :])
            )
        if atom.startswith(_GUARD_ATOM_PREFIX):
            guard_id = atom[len(_GUARD_ATOM_PREFIX) :]
            try:
                return _LoweredBoolTemplate(
                    lowering.guard_terms[guard_id],
                    lowering.guard_definedness[guard_id],
                )
            except KeyError as err:  # pragma: no cover - macro validation pairs guard atoms and requirements.
                # KeyError: macro validation should have guaranteed that guard
                # atoms have matching guard requirements.
                raise _internal_bmc_error("missing guard term %r." % guard_id) from err
        if atom.startswith(_ACCEPTED_ATOM_PREFIX):
            label = atom[len(_ACCEPTED_ATOM_PREFIX) :]
            return accepted_lookup(label, active)
        raise BmcBuildError(  # pragma: no cover - BoolTemplate atom namespace is validated by macro contract.
            "Unsupported macro condition atom namespace: %r." % atom
        )
    raise _internal_bmc_error(  # pragma: no cover - BoolTemplate validates kinds.
        "unsupported BoolTemplate kind %r." % template.kind
    )


def _build_case_relation(
    step_index: int,
    symbols: BmcTraceSymbols,
    lowering: _CaseLowering,
    antecedents: Mapping[str, _LoweredBoolTemplate],
) -> BmcCaseRelation:
    case = lowering.case
    selector = symbols.case_selector(step_index, case.label)
    source_guard = symbols.frame_state(step_index) == z3.IntVal(case.source_state_id)
    condition = antecedents[case.label].expr
    antecedent = _and((source_guard, condition))
    post_constraints: List[z3.ExprRef] = [
        symbols.frame_state(step_index + 1) == z3.IntVal(case.target_state_id)
    ]
    if case.kind == "absorb":
        post_constraints.extend(
            z3.Not(symbols.event_input(step_index, event.path))
            for event in symbols.domain.events
        )
    post_var_exprs = {}
    for var in symbols.domain.variables:
        try:
            value = lowering.final_env[var.name]
        except (
            KeyError
        ) as err:  # pragma: no cover - operation executor preserves visible names.
            # KeyError: execute_operations_domain must preserve every variable
            # visible in the incoming persistent environment.
            raise _internal_bmc_error(
                "case %s did not produce a post expression for %s."
                % (case.label, var.name)
            ) from err
        arith_value = _expect_arith(
            value, "post variable %s for case %s" % (var.name, case.label)
        )
        post_var_exprs[var.name] = arith_value
        post_constraints.append(
            symbols.frame_var(step_index + 1, var.name) == arith_value
        )
    definedness_constraints = (
        *antecedents[case.label].definedness_constraints,
        *lowering.definedness_constraints,
    )
    post_constraints.extend(_domain_constraints_exprs(definedness_constraints))
    consequent = _and(post_constraints)
    implication = z3.Implies(antecedent, consequent)
    selector_constraint = selector == antecedent
    return BmcCaseRelation(
        step_index=step_index,
        case=case,
        selector=selector,
        antecedent=antecedent,
        consequent=consequent,
        implication=implication,
        selector_constraint=selector_constraint,
        post_var_exprs=post_var_exprs,
        guard_terms=lowering.guard_terms,
        definedness_constraints=definedness_constraints,
        call_records=lowering.call_records,
    )


def _build_step_relation(
    step_index: int,
    symbols: BmcTraceSymbols,
    formals: Sequence[MacroStepFormal],
) -> BmcStepRelation:
    case_list = [case for formal in formals for case in formal.cases]
    if len({case.label for case in case_list}) != len(
        case_list
    ):  # pragma: no cover - macro labels are unique.
        raise _internal_bmc_error("duplicate case labels in step %d." % step_index)
    pre_env = {
        var.name: symbols.frame_var(step_index, var.name)
        for var in symbols.domain.variables
    }
    lowerings = {
        case.label: _prepare_case_lowering(case, pre_env) for case in case_list
    }
    condition_cache: Dict[str, _LoweredBoolTemplate] = {}

    def accepted_lookup(label: str, active: Set[str]) -> _LoweredBoolTemplate:
        if (
            label not in lowerings
        ):  # pragma: no cover - macro validation keeps accepted labels local.
            raise _internal_bmc_error(
                "accepted atom references unknown case label %r in step %d."
                % (label, step_index)
            )
        accepted_case = lowerings[label].case
        source_guard = symbols.frame_state(step_index) == z3.IntVal(
            accepted_case.source_state_id
        )
        condition = condition_for(label, active)
        return _LoweredBoolTemplate(
            _and((source_guard, condition.expr)),
            _guarded_domain_constraints(
                source_guard, condition.definedness_constraints
            ),
        )

    def condition_for(label: str, active: Set[str]) -> _LoweredBoolTemplate:
        if label in condition_cache:
            return condition_cache[label]
        if (
            label in active
        ):  # pragma: no cover - macro validation rejects recursive accepted dependencies.
            raise _internal_bmc_error(
                "recursive accepted-case dependency while lowering %r." % label
            )
        active.add(label)
        lowering = lowerings[label]
        value = _lower_bool_template(
            lowering.case.condition,
            lowering,
            accepted_lookup,
            active,
            symbols,
            step_index,
        )
        active.remove(label)
        condition_cache[label] = value
        return value

    for case in case_list:
        condition_for(case.label, set())

    relations = tuple(
        _build_case_relation(
            step_index, symbols, lowerings[case.label], condition_cache
        )
        for case in case_list
    )
    delta_flag = symbols.delta_flag(step_index)
    gamma_flag = symbols.gamma_flag(step_index)
    delta_constraint = delta_flag == _or(
        relation.antecedent for relation in relations if relation.case.kind == "delta"
    )
    gamma_constraint = gamma_flag == _or(
        relation.antecedent
        for relation in relations
        if relation.case.kind == "fallback"
    )
    progress_mutex_constraint = z3.Not(z3.And(delta_flag, gamma_flag))
    formula = _and(
        tuple(item.formula for item in relations)
        + (delta_constraint, gamma_constraint, progress_mutex_constraint)
    )
    return BmcStepRelation(
        step_index=step_index,
        formals=tuple(formals),
        case_relations=relations,
        formula=formula,
        delta_constraint=delta_constraint,
        gamma_constraint=gamma_constraint,
        progress_mutex_constraint=progress_mutex_constraint,
    )


def _initial_source(context: BmcPreparedContext):
    source = source_from_initial_spec(
        context.domain, context.bound_query.initial.source
    )
    if context.bound_query.initial.mode == "state":
        if (
            context.bound_query.initial.resolved_state_id != source.source_state_id
        ):  # pragma: no cover - binder/source helpers share one domain.
            raise _internal_bmc_error(
                "bound initial state id does not match initial source id."
            )
    return source


def _relation_frame_domain(context: BmcPreparedContext) -> _RelationFrameDomain:
    source = _initial_source(context)
    recurrence_ids = set(context.domain.stable_state_ids)
    if source.allows_semantic_delta:
        recurrence_ids.add(source.source_state_id)
    return _RelationFrameDomain(
        frame0_state_ids=tuple(context.domain.frame0_state_ids),
        recurrence_state_ids=tuple(sorted(recurrence_ids)),
    )


def _recurrence_formals(
    domain: BmcDomain,
    frame_domain: _RelationFrameDomain,
) -> Tuple[MacroStepFormal, ...]:
    formals = []
    for state_id in frame_domain.recurrence_state_ids:
        if state_id == STATE_INIT_ID:
            source = init_source(domain, origin="recurrence")
        elif state_id == STATE_TERMINATE_ID:
            source = terminated_source(domain, origin="recurrence")
        else:
            entry = domain.state_by_id(state_id)
            if entry.is_stoppable:
                source = stable_leaf_source(domain, state_id, origin="recurrence")
            else:
                source = entry_source(domain, state_id, origin="recurrence")
        formals.append(expand_macro_step_cases(source))
    return tuple(formals)


def _formals_by_step(
    context: BmcPreparedContext,
    frame_domain: _RelationFrameDomain,
) -> Tuple[Tuple[MacroStepFormal, ...], ...]:
    initial = (expand_macro_step_cases(_initial_source(context)),)
    if context.bound == 1:
        return (initial,)
    recurrence = _recurrence_formals(context.domain, frame_domain)
    # Recurrence formals are step-invariant immutable macro contracts, so the
    # same tuple can be shared safely across recurrence steps.
    return (initial,) + tuple(recurrence for _ in range(1, context.bound))


def _build_domain_formula(
    symbols: BmcTraceSymbols,
    frame_domain: _RelationFrameDomain,
    groups: List[BmcTrackedConstraint],
    source_ref_factory,
) -> z3.BoolRef:
    constraints = [_state_in(symbols.frame_state(0), frame_domain.frame0_state_ids)]
    _append_tracked_group(
        groups,
        stable_id="domain.frame.0000.state",
        stage="kernel",
        category="domain.frame_state",
        expressions=(constraints[0],),
        source_ref=source_ref_factory(),
        refs={"frame": 0, "kind": "state"},
    )
    for frame_index in range(1, symbols.domain.bound + 1):
        constraint = _state_in(
            symbols.frame_state(frame_index), frame_domain.recurrence_state_ids
        )
        constraints.append(constraint)
        _append_tracked_group(
            groups,
            stable_id="domain.frame.%04d.state" % frame_index,
            stage="kernel",
            category="domain.frame_state",
            expressions=(constraint,),
            source_ref=source_ref_factory(),
            refs={"frame": frame_index, "kind": "state"},
        )
    return _and(constraints)


def _build_initial_formula(
    context: BmcPreparedContext,
    symbols: BmcTraceSymbols,
    groups: List[BmcTrackedConstraint],
) -> z3.BoolRef:
    source = _initial_source(context)
    constraints: List[z3.ExprRef] = []
    target_constraint = symbols.frame_state(0) == z3.IntVal(source.source_state_id)
    constraints.append(target_constraint)
    _append_tracked_group(
        groups,
        stable_id="initial.target",
        stage="initialization",
        category="initial.target",
        expressions=(target_constraint,),
        source_ref=context._source_registry.query_reference(
            context.query, context.query.initial
        ),
        refs={"frame": 0, "target": source.source_state_id},
    )
    env: Dict[str, _Z3Expr] = {
        var.name: symbols.frame_var(0, var.name) for var in context.domain.variables
    }
    havoc_names = set(context.bound_query.initial.havoc_names(context.domain))
    for var in context.domain.variables:
        if var.name in havoc_names:
            continue
        define = context.model.defines[var.name]
        result = _translate_model_expr(
            define.init, env, "initializer for %s" % var.name
        )
        value = _expect_arith(result.z3_expr, "initializer for %s" % var.name)
        define_ref = context._source_registry.model_reference(define)
        for defined_index, item in enumerate(result.definedness_constraints):
            constraints.append(item.constraint)
            _append_tracked_group(
                groups,
                stable_id="initial.variable.%s.definedness.%04d"
                % (var.name, defined_index),
                stage="initialization",
                category="definedness",
                expressions=(item.constraint,),
                source_ref=define_ref,
                refs={"variable": var.name, "kind": "initializer"},
            )
        assignment = symbols.frame_var(0, var.name) == value
        constraints.append(assignment)
        _append_tracked_group(
            groups,
            stable_id="initial.variable.%s" % var.name,
            stage="initialization",
            category="initial.variable",
            expressions=(assignment,),
            source_ref=define_ref,
            refs={"variable": var.name, "frame": 0},
        )
    predicate = context.bound_query.initial.predicate
    if predicate is not None:
        lowered = _lower_bmc_cond_expr(predicate, symbols, frame_index=0)
        predicate_ref = context._source_registry.query_reference(
            context.query, context.query.initial.predicate
        )
        for defined_index, item in enumerate(lowered.definedness_constraints):
            constraints.append(item.constraint)
            _append_tracked_group(
                groups,
                stable_id="initial.where.definedness.%04d" % defined_index,
                stage="initialization",
                category="definedness",
                expressions=(item.constraint,),
                source_ref=predicate_ref,
                refs={"frame": 0, "kind": "where"},
            )
        where_constraint = _expect_bool(lowered.expr, "initial where predicate")
        constraints.append(where_constraint)
        _append_tracked_group(
            groups,
            stable_id="initial.where",
            stage="initialization",
            category="initial.where",
            expressions=(where_constraint,),
            source_ref=predicate_ref,
            refs={"frame": 0},
        )
    return _and(constraints)


def _build_environment_formula(
    context: BmcPreparedContext,
    symbols: BmcTraceSymbols,
    groups: List[BmcTrackedConstraint],
) -> z3.BoolRef:
    constraints: List[z3.ExprRef] = []
    for assumption_index, assumption in enumerate(context.bound_query.assumptions):
        if not isinstance(
            assumption, BoundAssumption
        ):  # pragma: no cover - BoundBmcQuery validates assumptions.
            raise _internal_bmc_error(
                "bound assumptions contain a non-BoundAssumption object."
            )
        if assumption.kind == "frame":
            source = assumption.source
            if not isinstance(
                source, FrameAssumption
            ):  # pragma: no cover - binder preserves source type.
                raise _internal_bmc_error(
                    "frame bound assumption has wrong source type."
                )
            frames = (
                range(context.bound + 1)
                if source.kind == "always"
                else (assumption.frame,)
            )
            for frame in frames:
                if (
                    frame is None
                ):  # pragma: no cover - binder sets frame for at-assumptions.
                    raise _internal_bmc_error("frame assumption has no frame index.")
                lowered = _lower_bmc_cond_expr(
                    source.predicate, symbols, frame_index=frame
                )
                source_ref = context._source_registry.query_reference(
                    context.query, source
                )
                for defined_index, item in enumerate(lowered.definedness_constraints):
                    constraints.append(item.constraint)
                    _append_tracked_group(
                        groups,
                        stable_id="assumption.%04d.frame.%04d.definedness.%04d"
                        % (assumption_index, frame, defined_index),
                        stage="assumptions",
                        category="definedness",
                        expressions=(item.constraint,),
                        source_ref=source_ref,
                        refs={"assumption": assumption_index, "frame": frame},
                    )
                frame_constraint = _expect_bool(lowered.expr, "frame assumption")
                constraints.append(frame_constraint)
                _append_tracked_group(
                    groups,
                    stable_id="assumption.%04d.frame.%04d" % (assumption_index, frame),
                    stage="assumptions",
                    category="assumption.frame",
                    expressions=(frame_constraint,),
                    source_ref=source_ref,
                    refs={"assumption": assumption_index, "frame": frame},
                )
            continue
        if assumption.kind == "event":
            if (
                len(assumption.resolved_event_ids) != 1
            ):  # pragma: no cover - binder resolves one event per event assumption.
                raise _internal_bmc_error(
                    "event assumption must resolve exactly one event id."
                )
            event = context.domain.event_by_id(assumption.resolved_event_ids[0])
            expected = bool(getattr(assumption.source, "expected"))
            source_ref = context._source_registry.query_reference(
                context.query, assumption.source
            )
            for cycle in assumption.cycles:
                event_expr = symbols.event_input(cycle, event.path)
                event_constraint = event_expr if expected else z3.Not(event_expr)
                constraints.append(event_constraint)
                _append_tracked_group(
                    groups,
                    stable_id="assumption.%04d.event.%04d" % (assumption_index, cycle),
                    stage="assumptions",
                    category="assumption.event",
                    expressions=(event_constraint,),
                    source_ref=source_ref,
                    refs={"assumption": assumption_index, "step": cycle},
                )
            continue
        if assumption.kind == "event_cardinality":
            source = assumption.source
            if not isinstance(
                source, EventCardinalityAssumption
            ):  # pragma: no cover - binder preserves source type.
                raise _internal_bmc_error(
                    "event-cardinality assumption has wrong source type."
                )
            if source.kind == "any":
                continue
            if (
                source.kind != "at_most_one"
            ):  # pragma: no cover - query model validates cardinality kinds.
                raise UnsupportedBmcQuery(
                    "Unsupported event cardinality kind: %r." % source.kind
                )
            events = [
                context.domain.event_by_id(event_id)
                for event_id in assumption.resolved_event_ids
            ]
            for step in range(context.bound):
                cardinality_constraint = z3.AtMost(
                    *[symbols.event_input(step, event.path) for event in events], 1
                )
                constraints.append(cardinality_constraint)
                _append_tracked_group(
                    groups,
                    stable_id="assumption.%04d.cardinality.%04d"
                    % (assumption_index, step),
                    stage="assumptions",
                    category="assumption.cardinality",
                    expressions=(cardinality_constraint,),
                    source_ref=context._source_registry.query_reference(
                        context.query, assumption.source
                    ),
                    refs={"assumption": assumption_index, "step": step},
                )
            continue
        raise _internal_bmc_error(  # pragma: no cover - BoundAssumption validates known kinds.
            "unknown bound assumption kind %r." % assumption.kind
        )
    return _and(constraints)


def build_bmc_core_formula(context: BmcPreparedContext) -> BmcCoreFormula:
    """Build ``Core_N`` for a prepared BMC context.

    The returned formula is exactly the core relation layer:
    ``D_N ∧ I_0 ∧ T_N ∧ ENV_N``.  Health gates, objective predicates,
    solving, and witness replay are intentionally left to later layers.

    :param context: Prepared BMC context from :class:`pyfcstm.bmc.BmcEngine`.
    :type context: pyfcstm.bmc.engine.BmcPreparedContext
    :return: Solver-level core formula bundle.
    :rtype: BmcCoreFormula
    :raises pyfcstm.bmc.errors.BmcBuildError: If the prepared context or macro
        handoff data is internally inconsistent.
    :raises pyfcstm.bmc.errors.UnsupportedBmcQuery: If a well-formed query or
        action uses a solver feature not supported by this relation builder.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root;')
        >>> context = BmcEngine(model).prepare('check reach <= 1: terminated();')
        >>> build_bmc_core_formula(context).core.sort().name()
        'Bool'
    """
    prepared = _require_context(context)
    frame_domain = _relation_frame_domain(prepared)
    formals_by_step = _formals_by_step(prepared, frame_domain)
    case_labels_by_step = {
        step_index: tuple(case.label for formal in formals for case in formal.cases)
        for step_index, formals in enumerate(formals_by_step)
    }
    symbols = BmcTraceSymbols.allocate(prepared.domain, case_labels_by_step)
    groups: List[BmcTrackedConstraint] = []
    steps = tuple(
        _build_step_relation(step_index, symbols, formals)
        for step_index, formals in enumerate(formals_by_step)
    )
    generated_ref = prepared._source_registry.reference("generated", None, None)

    domain_start = len(groups)
    _build_domain_formula(
        symbols,
        frame_domain,
        groups,
        lambda: generated_ref,
    )
    domain_formula = _formula_from_groups(groups[domain_start:])

    initial_start = len(groups)
    _build_initial_formula(prepared, symbols, groups)
    initial_formula = _formula_from_groups(groups[initial_start:])

    transition_start = len(groups)
    for step in steps:
        _append_tracked_group(
            groups,
            stable_id="transition.step.%04d" % step.step_index,
            stage="kernel",
            category="transition.step",
            expressions=(step.formula,),
            source_ref=generated_ref,
            refs={"step": step.step_index},
        )
    transition_formula = _formula_from_groups(groups[transition_start:])

    # Keep case-level provenance outside the aggregate transition slice.  The
    # private ledger becomes more precise without changing the historical T_N
    # expression or its canonical ordering.
    for step in steps:
        for case_index, case_relation in enumerate(step.case_relations):
            source_ref, transition_labels = _case_source_reference(
                prepared, case_relation.case, generated_ref
            )
            refs = {
                "step": step.step_index,
                "case_index": case_index,
                "case_label": case_relation.case.label,
                "case_kind": case_relation.case.kind,
                "transition_labels": list(transition_labels),
            }
            if not transition_labels and source_ref.kind == "fcstm":
                refs["source_inference"] = "unique_event"
            _append_tracked_group(
                groups,
                stable_id="transition.case.%04d.%04d" % (step.step_index, case_index),
                stage="kernel",
                category="transition.case",
                expressions=(case_relation.formula,),
                source_ref=source_ref,
                refs=refs,
            )

    environment_start = len(groups)
    _build_environment_formula(prepared, symbols, groups)
    environment_formula = _formula_from_groups(groups[environment_start:])
    core = _and(
        (domain_formula, initial_formula, transition_formula, environment_formula)
    )
    return BmcCoreFormula(
        context=prepared,
        symbols=symbols,
        domain_formula=domain_formula,
        initial_formula=initial_formula,
        transition_formula=transition_formula,
        environment_formula=environment_formula,
        core=core,
        steps=steps,
        diagnostics=(),
        _tracked_groups=tuple(groups),
    )


__all__ = [
    "BmcAbstractCallRecord",
    "BmcTraceSymbols",
    "BmcCaseRelation",
    "BmcStepRelation",
    "BmcCoreFormula",
    "build_bmc_core_formula",
]

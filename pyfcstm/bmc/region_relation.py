"""Core trace relation for models that declare regions.

A state that owns regions advances them one after another inside one cycle,
every region on the values the previous one left behind.  This module lowers
that cycle into one Z3 step relation without enumerating the combinations of
the regions' paths:

* every region has its own **position symbol** per frame, holding the id of
  the state its branch rests in, or ``REGION_DONE_ID`` once the region finished,
  or ``REGION_INACTIVE_ID`` while the owner is not resting;
* the regions of an owner are lowered in declaration order, each from the unit
  expansions of :mod:`pyfcstm.bmc.region_expand`, and the persistent variables
  flow from one region to the next through fresh **intermediate symbols**, so
  the formula grows with the sum of the regions, not with their product;
* a path that enters a state owning regions carries the whole initialization of
  that group, and a region that finishes carries the check that the owner can
  still continue -- both are decided from the values the path left behind, the
  way the runtime validates a candidate before it commits to it;
* frame constraints tie every region position to the state that owns it, so no
  frame can hold a region at a position its owner does not allow;
* every scope that declares ``>> during`` aspects carries two **flags** in the
  values that flow from unit to unit: whether its before actions already ran in
  this cycle, and whether it owes its after actions.  A unit is lowered once
  per combination of the before flags it can read and does not know, which are
  only those of scopes it shares with a region that worked earlier, and the
  owed after actions are settled one scope at a time -- so the formula grows
  with the number of such scopes, not with the number of their subsets.

:func:`build_region_core_formula` returns the same
:class:`pyfcstm.bmc.relation.BmcCoreFormula` as the single-path builder.  The
region facts of each step are available through ``region_steps``.

The module contains:

* :class:`RegionCaseRelation` - One lowered path of a region unit.
* :class:`RegionStepRelation` - All lowered paths of one step.
* :func:`region_frame_constraints` - Position invariants of one frame.
* :func:`build_region_core_formula` - Build ``Core_N`` for a model with regions.

Example::

    >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     region A { [*] -> P; state P; }
    ...     region B { [*] -> Q; state Q; }
    ... }
    ... ''')
    >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
    >>> len(core.region_steps)
    1
"""

from __future__ import annotations

from dataclasses import dataclass, field, replace
from typing import (
    Dict,
    FrozenSet,
    Iterable,
    List,
    Mapping,
    Optional,
    Sequence,
    Set,
    Tuple,
)

import z3

from .domain import (
    REGION_DONE_ID,
    REGION_INACTIVE_ID,
    REGION_PENDING_ID,
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcDomain,
    RegionDomainEntry,
)
from .engine import BmcPreparedContext
from .errors import BmcBuildError
from pyfcstm.model.region import walk_namespaces
from .region_expand import (
    ATOM_REGION_DONE,
    ATOM_REGION_ENTER,
    RegionCase,
    RegionUnitFormal,
    expand_cold_unit,
    expand_continue_unit,
    expand_flush_unit,
    expand_init_unit,
    expand_leaf_unit,
    expand_wait_unit,
)
from .region_start import DONE as START_DONE
from .region_start import PENDING as START_PENDING
from .relation import (
    BmcAbstractCallRecord,
    BmcCoreFormula,
    BmcRuntimeErrorSite,
    BmcStepRelation,
    BmcTraceSymbols,
    _CaseLowering,
    _LoweredBoolTemplate,
    _and,
    _append_tracked_group,
    _build_domain_formula,
    _build_environment_formula,
    _build_initial_formula,
    _error_site,
    _execute_action_block,
    _expect_arith,
    _guarded_domain_constraints,
    _formula_from_groups,
    _initial_source,
    _internal_bmc_error,
    _lower_bool_template,
    _lower_guard_requirement,
    _or,
    _prepare_case_lowering,
    _relation_frame_domain,
    _require_context,
    _translate_model_expr,
)
from pyfcstm.dsl.role import VariableRole
from .provenance import BmcTrackedConstraint
from pyfcstm.solver.domain import DomainConstraint

_Env = Dict[str, z3.ArithRef]
# A fact assigns a frame-position symbol under a condition.
_Fact = Tuple[z3.BoolRef, z3.ArithRef, z3.ArithRef]


@dataclass(frozen=True)
class RegionCaseRelation:
    """One lowered path of a region unit.

    :param step_index: Step index owning this path.
    :type step_index: int
    :param case: Flat path that was lowered.
    :type case: pyfcstm.bmc.region_expand.RegionCase
    :param selector: Boolean symbol bound to ``antecedent``.
    :type selector: z3.BoolRef
    :param antecedent: Gate of the unit and lowered path condition.
    :type antecedent: z3.BoolRef
    :param consequent: Position, variable and definedness constraints.
    :type consequent: z3.BoolRef
    :param implication: ``z3.Implies(antecedent, consequent)``.
    :type implication: z3.BoolRef
    :param order: Rank of the unit this path belongs to among the units lowered
        in the step.  Units are lowered in the order the runtime runs them, so
        sorting the paths a model selected by ``order`` lists them in execution
        order; every copy of one unit shares its rank, defaults to ``0``.
    :type order: int, optional
    :param children: Paths of the units that this path starts when it enters a
        state that owns regions: the start of each region in order, and the
        continuation of the owner when every region finished right away.  A
        child is only part of the run when this path is, and its ``selector``
        is the condition expression of the path itself rather than a symbol, so
        building it adds nothing to the formula; defaults to ``()``.
    :type children: Tuple[RegionCaseRelation, ...], optional
    :param call_records: Abstract actions the path calls, in call order, with the
        values the variables had at the moment of the call; defaults to ``()``.
    :type call_records: Tuple[pyfcstm.bmc.relation.BmcAbstractCallRecord, ...], optional
    :param flushes: Settlements of ``>> during after`` actions that the start of
        a group runs when one of its regions ends its branch right away, in
        execution order; defaults to ``()``.
    :type flushes: Tuple[RegionFlushRelation, ...], optional

    Example::

        >>> import z3
        >>> from pyfcstm.bmc.macro import BoolTemplate
        >>> from pyfcstm.bmc.region_expand import RegionCase
        >>> case = RegionCase('fallback', 'u::fallback::P::0', 'u', 'leaf', 3, 'Root.P',
        ...                   BoolTemplate.true(), (), (), (), (), ())
        >>> t = z3.BoolVal(True)
        >>> RegionCaseRelation(0, case, t, t, t, t).case.kind
        'fallback'
        >>> RegionCaseRelation(0, case, t, t, t, t, 2).order
        2
    """

    step_index: int
    case: RegionCase
    selector: z3.BoolRef
    antecedent: z3.BoolRef
    consequent: z3.BoolRef
    implication: z3.BoolRef
    order: int = 0
    children: Tuple["RegionCaseRelation", ...] = ()
    call_records: Tuple[BmcAbstractCallRecord, ...] = ()
    flushes: Tuple["RegionFlushRelation", ...] = ()


@dataclass(frozen=True)
class RegionFlushRelation:
    """The ``>> during after`` actions one scope runs when a flush settles it.

    A flush runs at the end of a region's branch and at the end of the cycle.
    It settles the scopes that owe their after actions one at a time, innermost
    first, so each scope is a unit of its own.

    :param step_index: Step index owning this flush.
    :type step_index: int
    :param order: Rank of the flush among the units lowered in the step, in the
        same ranking as :attr:`RegionCaseRelation.order`.
    :type order: int
    :param scope: Path of the scope that is settled.
    :type scope: str
    :param prefix: Path of the region whose branch just ended, or ``''`` for the
        flush that ends the cycle.
    :type prefix: str
    :param condition: Condition under which the scope owes its after actions and
        the flush runs.
    :type condition: z3.BoolRef
    :param call_records: Abstract actions the settlement calls, in call order.
    :type call_records: Tuple[pyfcstm.bmc.relation.BmcAbstractCallRecord, ...]

    Example::

        >>> import z3
        >>> flush = RegionFlushRelation(0, 3, 'Root', '', z3.BoolVal(True), ())
        >>> (flush.scope, flush.prefix)
        ('Root', '')
    """

    step_index: int
    order: int
    scope: str
    prefix: str
    condition: z3.BoolRef
    call_records: Tuple[BmcAbstractCallRecord, ...]


@dataclass(frozen=True)
class RegionOccurrence:
    """One path or settlement of a step together with the condition it runs under.

    A path that a group start runs only runs when the path that started the group
    does, so its own selector is not enough; the condition of an occurrence is the
    conjunction along the way from the path that runs unconditionally.

    :param order: Rank of the unit in the step, see :attr:`RegionCaseRelation.order`.
    :type order: int
    :param condition: Condition under which the occurrence is part of the cycle.
    :type condition: z3.BoolRef
    :param case: The path, or ``None`` for a settlement.
    :type case: RegionCaseRelation, optional
    :param flush: The settlement, or ``None`` for a path.
    :type flush: RegionFlushRelation, optional
    :param positions: For every call record, in the same order, where the machine
        is at the moment of that call: what the handler is told about the whole
        position.  Empty when the step has no start to fold from; defaults to
        ``()``.
    :type positions: Tuple[PositionSnapshot, ...], optional

    Example::

        >>> import z3
        >>> flush = RegionFlushRelation(0, 3, 'Root', '', z3.BoolVal(True), ())
        >>> RegionOccurrence(3, z3.BoolVal(True), None, flush).call_records
        ()
    """

    order: int
    condition: z3.BoolRef
    case: Optional[RegionCaseRelation]
    flush: Optional[RegionFlushRelation]
    positions: Tuple[PositionSnapshot, ...] = ()

    @property
    def call_records(self) -> Tuple[BmcAbstractCallRecord, ...]:
        """Return the abstract calls the occurrence makes, in call order.

        :return: The call records of the path or of the settlement.
        :rtype: Tuple[pyfcstm.bmc.relation.BmcAbstractCallRecord, ...]

        Example::

            >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
            >>> from pyfcstm.model import load_state_machine_from_text
            >>> model = load_state_machine_from_text('''
            ... state Root {
            ...     region A { [*] -> P; state P { during abstract Work; } }
            ... }
            ... ''')
            >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
            >>> [len(item.call_records) for item in region_occurrences(core.region_steps[0])]
            [0, 1]
        """
        item = self.case if self.case is not None else self.flush
        return item.call_records


def region_occurrences(step: "RegionStepRelation") -> Tuple[RegionOccurrence, ...]:
    """List every path and settlement of a step with the condition it runs under.

    The occurrences come in execution order.  A path that was lowered for a
    group start, which no solved model selected on its own, is listed under the
    path that starts the group.

    :param step: Paths of one step of a model with regions.
    :type step: RegionStepRelation
    :return: Occurrences sorted by the rank of their unit.
    :rtype: Tuple[RegionOccurrence, ...]

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
        >>> [item.case.case.public_label for item in region_occurrences(core.region_steps[0])]
        ['__init__::initial::Root::0', 'Root::initial::Root.A.P::0', 'Root::initial::Root.B.Q::0']
    """
    found: List[RegionOccurrence] = []

    def walk_cases(relations, ancestors) -> None:
        for relation in relations:
            condition = _and(tuple(ancestors) + (relation.selector,))
            found.append(RegionOccurrence(relation.order, condition, relation, None))
            walk_cases(relation.children, tuple(ancestors) + (relation.selector,))
            for flush in relation.flushes:
                found.append(
                    RegionOccurrence(
                        flush.order,
                        _and(tuple(ancestors) + (relation.selector, flush.condition)),
                        None,
                        flush,
                    )
                )

    # A step that cannot be rolled back adds nothing to the conditions.
    ran = () if z3.is_false(step.rolled_back) else (z3.Not(step.rolled_back),)
    walk_cases(step.cases, ran)
    for flush in step.flushes:
        found.append(
            RegionOccurrence(flush.order, _and(ran + (flush.condition,)), None, flush)
        )
    ordered = sorted(found, key=lambda item: item.order)
    if step.start is None:
        return tuple(ordered)
    return tuple(_with_positions(step, ordered))


def _with_positions(
    step: "RegionStepRelation", ordered: Sequence[RegionOccurrence]
) -> List[RegionOccurrence]:
    """Give every occurrence the positions its calls see.

    The positions fold the way the runtime moves them: from where the cycle
    starts, every path in the order it runs moves the place it runs in to where
    it ends, under the condition it runs under, and a path that starts a group
    sets the regions of that group to wait for their start.  A call made while a
    path runs sees the place that path runs in as the top of the stack it has
    built so far, and a settlement sees the positions as they are.
    """
    owned = dict(step.owned)
    ids = dict(step.state_ids)
    main = step.start.main
    regions: Dict[str, z3.ExprRef] = dict(step.start.regions)
    result: List[RegionOccurrence] = []

    def move(where: Optional[str], value: z3.ExprRef, condition: z3.BoolRef) -> None:
        nonlocal main
        if where is None:
            main = z3.If(condition, value, main)
        else:
            regions[where] = z3.If(condition, value, regions[where])

    for occurrence in ordered:
        snapshots: List[PositionSnapshot] = []
        if occurrence.case is None:
            snapshots = [
                PositionSnapshot(main, dict(regions))
                for _ in occurrence.call_records
            ]
        else:
            case = occurrence.case.case
            for record in occurrence.case.call_records:
                top = (record.stack_states or ())[-1] if record.stack_states else None
                seen_main = main
                seen = dict(regions)
                if case.home is None:
                    # A call outside every region runs with a state on the stack.
                    seen_main = z3.IntVal(ids[top])
                else:
                    seen[case.home] = (
                        z3.IntVal(ids[top])
                        if top is not None
                        else z3.IntVal(REGION_PENDING_ID)
                    )
                snapshots.append(PositionSnapshot(seen_main, seen))
            if case.target_kind == "terminate":
                move(None, z3.IntVal(STATE_TERMINATE_ID), occurrence.condition)
            else:
                value = (
                    z3.IntVal(REGION_DONE_ID)
                    if case.target_kind == "done"
                    else z3.IntVal(case.target_state_id)
                )
                move(case.home, value, occurrence.condition)
                if case.target_kind == "owner":
                    for path in owned.get(case.target_state_path, ()):
                        regions[path] = z3.If(
                            occurrence.condition, z3.IntVal(REGION_PENDING_ID), regions[path]
                        )
        result.append(replace(occurrence, positions=tuple(snapshots)))
    return result


@dataclass(frozen=True)
class PositionSnapshot:
    """Where the machine is at one moment of a cycle, as expressions.

    :param main: The state the machine rests in outside every region, as a state
        id.
    :type main: z3.ExprRef
    :param regions: The position of every region by its path: a state id,
        ``REGION_DONE_ID``, ``REGION_PENDING_ID`` or ``REGION_INACTIVE_ID``.
    :type regions: Mapping[str, z3.ExprRef]

    Example::

        >>> import z3
        >>> PositionSnapshot(z3.IntVal(1), {'Root.A': z3.IntVal(2)}).regions['Root.A']
        2
    """

    main: z3.ExprRef
    regions: Mapping[str, z3.ExprRef]


@dataclass(frozen=True)
class RegionStepRelation:
    """All lowered paths of one step of a model with regions.

    :param step_index: Step index in ``0..N-1``.
    :type step_index: int
    :param cases: Lowered paths of the units that run in this step.
    :type cases: Tuple[RegionCaseRelation, ...]
    :param constraints: Every constraint of the step: path implications,
        intermediate-symbol definitions and frame facts.
    :type constraints: Tuple[z3.BoolRef, ...]
    :param flushes: Settlements of ``>> during after`` actions that run in the
        step outside a group start, in execution order; defaults to ``()``.
    :type flushes: Tuple[RegionFlushRelation, ...], optional
    :param rolled_back: Condition under which the whole cycle is rolled back
        after its paths were lowered: a hot start whose waiting region cannot
        start.  The cycle is then a Delta, so none of its paths ran; defaults
        to ``False``.
    :type rolled_back: z3.BoolRef, optional
    :param start: Where the machine is when the cycle starts, which is what the
        positions a call sees are folded from; ``None`` leaves the calls of the
        step without positions; defaults to ``None``.
    :type start: PositionSnapshot, optional
    :param owned: The regions of every owner, by the owner's path, for the start
        of a group; defaults to ``()`` (read as no owner).
    :type owned: Tuple[Tuple[str, Tuple[str, ...]], ...], optional
    :param state_ids: The id of every state by its path; defaults to ``()``.
    :type state_ids: Tuple[Tuple[str, int], ...], optional

    Example::

        >>> RegionStepRelation(0, (), ()).step_index
        0
    """

    step_index: int
    cases: Tuple[RegionCaseRelation, ...]
    constraints: Tuple[z3.BoolRef, ...]
    flushes: Tuple[RegionFlushRelation, ...] = ()
    rolled_back: z3.BoolRef = field(default_factory=lambda: z3.BoolVal(False))
    start: Optional[PositionSnapshot] = None
    owned: Tuple[Tuple[str, Tuple[str, ...]], ...] = ()
    state_ids: Tuple[Tuple[str, int], ...] = ()


@dataclass(frozen=True)
class _Namespace:
    """Where a unit runs: the main namespace or inside one region of an owner."""

    region: Optional[RegionDomainEntry]
    others_live: Optional[z3.BoolRef]
    parent: Optional["_Namespace"]


@dataclass
class _UnitResult:
    """Outcome of lowering a unit.

    :ivar ok: Condition under which one of the paths of the unit applies.
    :ivar facts: Frame position assignments, each guarded by the path that makes it.
    :ivar defs: Definedness requirements of the paths, each guarded by its path.
    :ivar fallback: Condition under which the applying path only ran during actions.
    :ivar cases: Lowered paths kept for inspection: every path of a unit that runs in
        the step, or of a unit that a group start runs, in the order of its variants.
    """

    ok: z3.BoolRef
    facts: List[_Fact] = field(default_factory=list)
    defs: List[Tuple[z3.BoolRef, DomainConstraint]] = field(default_factory=list)
    fallback: z3.BoolRef = field(default_factory=lambda: z3.BoolVal(False))
    cases: List[RegionCaseRelation] = field(default_factory=list)


@dataclass
class _Entry:
    """Outcome of starting the regions of a state that owns regions.

    :ivar ok: Whether the whole group can start, and continue if all regions finished.
    :ivar out_pos: Position of the enclosing namespace after the start.
    :ivar env_out: Values after the start.
    :ivar facts: Frame position assignments of the started regions.
    :ivar defs: Definedness requirements of the start paths.
    :ivar cases: Lowered paths of the units the start runs, in execution order.
    :ivar flushes: Settlements the start runs, in execution order.
    """

    ok: z3.BoolRef
    out_pos: z3.ArithRef
    env_out: _Env
    facts: List[_Fact]
    defs: List[Tuple[z3.BoolRef, DomainConstraint]]
    cases: List[RegionCaseRelation] = field(default_factory=list)
    flushes: List[RegionFlushRelation] = field(default_factory=list)


class _Units:
    """Lazily expanded units of one build, keyed by what they start from."""

    def __init__(self, domain: BmcDomain) -> None:
        """Create an empty cache of unit expansions for one domain."""
        self._domain = domain
        self.relevant: Dict[Tuple[str, Optional[str]], Tuple[str, ...]] = {}
        self._cache: Dict[
            Tuple[str, Optional[str], FrozenSet[str], bool], RegionUnitFormal
        ] = {}

    def get(
        self,
        spec: Tuple[str, Optional[str]],
        before_done: FrozenSet[str] = frozenset(),
        plain_pending: bool = False,
    ) -> RegionUnitFormal:
        """Return the unit of ``spec`` for the scopes whose before actions ran."""
        key = (spec[0], spec[1], before_done, plain_pending)
        if key not in self._cache:
            kind, path = spec
            if kind == "leaf":
                unit = expand_leaf_unit(self._domain, path, before_done=before_done)
            elif kind == "init":
                unit = expand_init_unit(
                    self._domain,
                    path,
                    before_done=before_done,
                    plain_pending=plain_pending,
                )
            elif kind == "cont":
                unit = expand_continue_unit(self._domain, path, before_done=before_done)
            elif kind == "wait":
                unit = expand_wait_unit(self._domain, path, before_done=before_done)
            else:
                unit = expand_cold_unit(self._domain, before_done=before_done)
            self._cache[key] = unit
        return self._cache[key]

    def flush(self, owed: FrozenSet[str]) -> RegionUnitFormal:
        """Return the unit that runs the after actions of the owing scopes."""
        key = ("flush", None, owed, False)
        if key not in self._cache:
            self._cache[key] = expand_flush_unit(self._domain, owed)
        return self._cache[key]


def _regions_of(domain: BmcDomain, owner_path: str) -> Tuple[RegionDomainEntry, ...]:
    """Return the regions of ``owner_path`` in declaration order."""
    return tuple(
        sorted(
            (item for item in domain.regions if item.owner_path == owner_path),
            key=lambda item: item.ordinal,
        )
    )


def _owner_resting(
    symbols: BmcTraceSymbols, domain: BmcDomain, frame_index: int, owner_path: str
) -> z3.BoolRef:
    """Return whether the state that owns regions rests in a frame."""
    entry = domain.state_by_path(owner_path)
    region = next(
        (item for item in domain.regions if item.owner_path == owner_path), None
    )
    if region is None or region.enclosing_region_path is None:
        return symbols.frame_state(frame_index) == z3.IntVal(entry.id)
    enclosing = next(
        item for item in domain.regions if item.path == region.enclosing_region_path
    )
    return z3.And(
        symbols.region_position(frame_index, enclosing.path) == z3.IntVal(entry.id),
        _owner_resting(symbols, domain, frame_index, enclosing.owner_path),
    )


def reported_call_state(
    domain: BmcDomain, record: BmcAbstractCallRecord
) -> Tuple[str, str]:
    """Return the state and the active leaf a handler is told for a call.

    A call of a plain action reports the state that owns it.  A ``>> during``
    aspect declared above a group of regions wraps the whole group: the handler
    is told the state of the first owner of at least two regions on the way from
    the scope that declares the aspect down to the state the call belongs to, and
    the state itself when no such owner is on the way.  An owner of one region
    is passed through, as the plain composite it behaves like.  It describes the
    calls a unit of work makes; the call of an aspect that a flush settles is
    told the state the machine rests in at that moment, which no record knows.

    :param domain: Domain of a model that declares regions.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param record: A lowered call record.
    :type record: pyfcstm.bmc.relation.BmcAbstractCallRecord
    :return: The reported state and the reported active leaf.
    :rtype: Tuple[str, str]

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     >> during before abstract Tick;
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
        >>> occurrence = [item for item in region_occurrences(core.region_steps[0]) if item.call_records][0]
        >>> reported_call_state(core.context.domain, occurrence.call_records[0])
        ('Root', 'Root')
    """
    if not record.role.startswith("aspect_") or record.scope_path is None:
        return record.state_path, record.active_leaf_path
    reported = _wrapped_state(domain, record.scope_path, record.state_path)
    return reported, reported


def _wrapped_state(domain: BmcDomain, scope: str, state_path: str) -> str:
    """Return the deepest state common to everything an aspect of ``scope`` wraps.

    ``state_path`` is the state the aspect runs for: the leaf that does the during
    work, or a state this function already returned.  On the way from ``scope``
    down to it the first owner of at least two regions is the answer, because an
    aspect above it wraps the whole group; without one the state itself is.
    """
    chain: List[str] = []
    entry = domain.state_by_path(state_path)
    while True:
        chain.append(entry.path)
        if entry.region_path is not None:
            # A state in a region has the region, not the owner, as its parent
            # path; the owner is the next state up.
            above = next(
                item.owner_path for item in domain.regions if item.path == entry.region_path
            )
        elif entry.parent_path is not None:
            above = entry.parent_path
        else:
            break
        entry = domain.state_by_path(above)
    for path in reversed(chain):
        if path != scope and not path.startswith(scope + "."):
            continue
        if len(_regions_of(domain, path)) >= 2:
            return path
    return state_path


def _settled_states(domain: BmcDomain, scope: str) -> Tuple[str, ...]:
    """Return every state the handler of an after action of ``scope`` can be told.

    The action settles after a leaf below the scope did during work, and the
    state it reports is the one that leaf determines, so the candidates are what
    :func:`_wrapped_state` gives for the leaves below the scope, sorted.
    """
    return tuple(
        sorted(
            {
                _wrapped_state(domain, scope, entry.path)
                for entry in domain.states
                if entry.is_stoppable and entry.path.startswith(scope + ".")
            }
        )
    )


def _in_region(domain: BmcDomain, path: str) -> bool:
    """Return whether the state at ``path`` sits inside a region, at any depth."""
    current = domain.state_by_path(path)
    while current is not None:
        if current.region_path is not None:
            return True
        current = (
            domain.state_by_path(current.parent_path)
            if current.parent_path is not None
            else None
        )
    return False


def start_position_ids(
    domain: BmcDomain, start
) -> Tuple[int, Dict[str, int]]:
    """Return the ids of the position a hot start of a model with regions begins in.

    :param domain: Region-aware domain of the model.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param start: Where every region rests, as read by
        :func:`pyfcstm.bmc.region_start.resolve_region_start`.
    :type start: pyfcstm.bmc.region_start.RegionStart
    :return: The id of the state the machine rests in outside every region, and for
        every region of a resting owner the id of its position: a state id,
        :data:`pyfcstm.bmc.domain.REGION_DONE_ID` or
        :data:`pyfcstm.bmc.domain.REGION_PENDING_ID`.
    :rtype: Tuple[int, Dict[str, int]]

    Example::

        >>> from pyfcstm.bmc.domain import REGION_PENDING_ID, build_bmc_domain
        >>> from pyfcstm.bmc.region_start import resolve_region_start
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> domain = build_bmc_domain(model, 1)
        >>> main, ids = start_position_ids(domain, resolve_region_start(domain, 'Root{A: P}'))
        >>> (main == domain.state_path_to_id('Root'), ids['Root.B'] == REGION_PENDING_ID)
        (True, True)
    """
    ids: Dict[str, int] = {}
    for path, value in start.positions.items():
        if value == START_PENDING:
            ids[path] = REGION_PENDING_ID
        elif value == START_DONE:
            ids[path] = REGION_DONE_ID
        else:
            ids[path] = domain.state_path_to_id(value)
    return domain.state_path_to_id(start.main), ids


def _outside_stable_positions(
    domain: BmcDomain, ids: Mapping[str, int]
) -> Dict[str, int]:
    """Return the positions of a start that a frame only holds right at the start.

    A region that waits for initialization, or a branch that rests in a state only a
    cycle can leave, is a position no frame has once the machine has made progress.
    """
    stable = {item.path: set(item.position_state_ids) for item in domain.regions}
    return {
        path: value
        for path, value in ids.items()
        if value != REGION_DONE_ID and value not in stable[path]
    }


def region_frame_constraints(
    symbols: BmcTraceSymbols,
    frame_index: int,
    start: Optional[Tuple[int, Mapping[str, int]]] = None,
) -> Tuple[z3.BoolRef, ...]:
    """Return the position invariants of one frame.

    The main state symbol only takes ids of the main namespace; a region holds
    ``REGION_INACTIVE_ID`` exactly while the state that owns it is not resting,
    and otherwise a position of its own or ``REGION_DONE_ID``; a resting owner
    keeps at least one region at work, because a group whose regions all finished
    hands control back in the same cycle.

    :param symbols: Trace symbols of a model with regions.
    :type symbols: pyfcstm.bmc.relation.BmcTraceSymbols
    :param frame_index: Frame index in ``0..N``.
    :type frame_index: int
    :param start: For a hot start, the id of the state the machine rests in outside
        every region and the position ids of the regions, see
        :func:`start_position_ids`.  A frame may hold a position that a hot start
        begins in but that no frame holds after progress, such as a region that
        waits for initialization, only when it holds the whole start position:
        that is the frame of a cycle that made no progress.  Defaults to ``None``.
    :type start: Tuple[int, Mapping[str, int]], optional
    :return: Constraints that every frame of a trace satisfies.
    :rtype: Tuple[z3.BoolRef, ...]
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``frame_index`` is invalid.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.bmc.relation import BmcTraceSymbols
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> symbols = BmcTraceSymbols.allocate(build_bmc_domain(model, 1))
        >>> len(region_frame_constraints(symbols, 0)) > 0
        True
    """
    domain = symbols.domain
    constraints: List[z3.BoolRef] = []
    state = symbols.frame_state(frame_index)
    main_ids = [
        entry.id
        for entry in domain.states
        if not entry.is_sentinel
        and (entry.is_stoppable or entry.owns_regions)
        and not _in_region(domain, entry.path)
    ]
    if start is not None and start[0] not in main_ids:
        # A hot start can begin in a state the machine does not rest in, a plain
        # composite state or a pseudo state; only the cycle that leaves it is
        # left, or a cycle that found no way on and so stayed there.
        main_ids.append(start[0])
    constraints.append(
        _or(
            state == z3.IntVal(item)
            for item in sorted(main_ids + [STATE_INIT_ID, STATE_TERMINATE_ID])
        )
    )
    owners = sorted({item.owner_path for item in domain.regions})
    for owner_path in owners:
        resting = _owner_resting(symbols, domain, frame_index, owner_path)
        regions = _regions_of(domain, owner_path)
        for region in regions:
            position = symbols.region_position(frame_index, region.path)
            extra = (
                ()
                if start is None
                else tuple(
                    value
                    for path, value in _outside_stable_positions(
                        domain, start[1]
                    ).items()
                    if path == region.path
                )
            )
            allowed = _or(
                position == z3.IntVal(item)
                for item in tuple(region.position_state_ids) + (REGION_DONE_ID,) + extra
            )
            constraints.append(z3.Implies(resting, allowed))
            constraints.append(
                z3.Implies(z3.Not(resting), position == z3.IntVal(REGION_INACTIVE_ID))
            )
        constraints.append(
            z3.Implies(
                resting,
                _or(
                    symbols.region_position(frame_index, region.path)
                    != z3.IntVal(REGION_DONE_ID)
                    for region in regions
                ),
            )
        )
    if start is not None:
        main_id, ids = start
        at_start = _at_start(symbols, frame_index, main_id, ids)
        for path, value in _outside_stable_positions(domain, ids).items():
            constraints.append(
                z3.Implies(
                    symbols.region_position(frame_index, path) == z3.IntVal(value),
                    at_start,
                )
            )
    return tuple(constraints)


def _at_start(
    symbols: BmcTraceSymbols, frame_index: int, main_id: int, ids: Mapping[str, int]
) -> z3.BoolRef:
    """Return the condition that a frame holds the position a hot start began in."""
    return _and(
        [symbols.frame_state(frame_index) == z3.IntVal(main_id)]
        + [
            symbols.region_position(frame_index, path) == z3.IntVal(value)
            for path, value in sorted(ids.items())
        ]
    )


class _StepBuilder:
    """Lowers one step of a model with regions."""

    def __init__(
        self,
        prepared: BmcPreparedContext,
        symbols: BmcTraceSymbols,
        units: _Units,
        step_index: int,
        analysis: bool = False,
    ) -> None:
        """Collect what one step needs: symbols, units, aspect scopes and value slots.

        The values that flow from unit to unit are the persistent variables plus, for
        every scope that declares aspects, a flag for its before actions and a flag for
        its after actions.

        With ``analysis`` the step is lowered to locate runtime errors instead of to
        describe the cycle: nothing is required to be defined, so an operation that
        raises can still be part of a model, and every operation the runtime
        evaluates, also on a candidate that dead-ends or loses to a higher
        priority, becomes a requirement kept in :attr:`requirements`.
        """
        self.analysis = analysis
        # Operations that make a hot start of a model with regions fail in a cycle:
        # the start of a region that waits, and the cycle of a branch that rests in
        # a state only a cycle can leave.  Any one of them makes the whole cycle a
        # Delta.
        self._hot_fail: List[z3.BoolRef] = []
        # Under which condition each operation of the step has to be defined; only
        # filled by an analysis.
        self.requirements: List[Tuple[z3.BoolRef, DomainConstraint]] = []
        self.prepared = prepared
        self.symbols = symbols
        self.units = units
        self.step = step_index
        self.domain = prepared.domain
        start = prepared.bound_query.initial.resolved_start
        # The position a hot start begins in, as ids; ``start_waits`` says that
        # some part of it needs a cycle of its own to be initialized.
        self.main_id: Optional[int] = None
        self.start_ids: Dict[str, int] = {}
        self.start_waits = False
        if start is not None:
            self.main_id, self.start_ids = start_position_ids(self.domain, start)
            main = self.domain.state_by_id(self.main_id)
            self.start_waits = bool(
                _outside_stable_positions(self.domain, self.start_ids)
            ) or not (main.is_stoppable or main.owns_regions)
        self.persistent = tuple(self.domain.persistent_variable_names)
        frame_vars = symbols.frame_vars[step_index]
        self.int_names = tuple(
            name for name in self.persistent if z3.is_int(frame_vars[name])
        )
        # Scopes that declare ``>> during`` aspects.  Each keeps two flags in
        # the values that flow from unit to unit: whether its before actions
        # already ran in this cycle, and whether it owes its after actions.
        self.before_scopes, self.after_scopes = _aspect_scopes(prepared.model)
        self.has_aspects = bool(self.before_scopes or self.after_scopes)
        # Owners whose plain ``during before`` waits for the first real child.
        self.pending_owners = frozenset(
            ".".join(state.path)
            for state in prepared.model.walk_states()
            if state.regions and state.list_on_durings(aspect="before")
        )
        # The handler of an abstract after action is told a state that the leaf
        # which made the scope owe determines.  A scope where that can be more
        # than one state keeps it in a slot next to its owed flag.
        self.settled_states = {
            scope: _settled_states(self.domain, scope) for scope in self.after_scopes
        }
        self.settled_keys = tuple(
            "$w:%s" % scope
            for scope in self.after_scopes
            if len(self.settled_states[scope]) > 1
            and any(
                block.is_abstract
                for block in units.flush(frozenset({scope})).cases[0].action_blocks
            )
        )
        self.ledger_keys = tuple(
            ["$b:%s" % path for path in self.before_scopes]
            + ["$o:%s" % path for path in self.after_scopes]
        ) + self.settled_keys
        self.slots = self.persistent + self.ledger_keys
        region_paths = [region.path for region in self.domain.regions]
        # After flags of scopes inside a region are cleared when the branch of
        # that region ends, so they are never set when a cycle ends.
        self.region_owed_keys = frozenset(
            "$o:%s" % scope
            for scope in self.after_scopes
            if any(_under(scope, item) for item in region_paths)
        )
        self.constraints: List[z3.BoolRef] = []
        self.cases: List[RegionCaseRelation] = []
        # Where the settlements of the flush being lowered are kept: the step, or
        # the group start that is being lowered.
        self.flushes: List[RegionFlushRelation] = []
        self._flush_sink: List[RegionFlushRelation] = self.flushes
        self.delta_terms: List[z3.BoolRef] = []
        self.rollback_terms: List[z3.BoolRef] = []
        self.gamma_terms: List[z3.BoolRef] = []
        self._counter = 0
        # Rank handed to the next unit that is lowered; see ``RegionCaseRelation.order``.
        self._unit_counter = 0
        # Owners whose entry is being decided, with the values they were
        # entered on: re-entering one on the very same values is the loop the
        # runtime reports, and re-entering on other values may still end.
        self._entering: List[Tuple[str, _Env]] = []

    # ------------------------------------------------------------------
    # symbols
    # ------------------------------------------------------------------
    def fresh_int(self, tag: str) -> z3.ArithRef:
        """Return a fresh integer symbol named after the step and ``tag``."""
        self._counter += 1
        return z3.Int("R_%d_%d_%s" % (self.step, self._counter, tag))

    def fresh_env(
        self,
        tag: str,
        base: Optional[_Env] = None,
        touch: Optional[FrozenSet[str]] = None,
    ) -> _Env:
        """Return fresh symbols for the slots of the values that flow between units.

        With ``base`` and ``touch`` only the flags named in ``touch`` get a fresh
        symbol; every other flag keeps the expression it has in ``base``, so a
        flag nothing can change stays known.
        """
        self._counter += 1
        frame_vars = self.symbols.frame_vars[self.step]
        env: _Env = {
            name: (z3.Int if z3.is_int(frame_vars[name]) else z3.Real)(
                "R_%d_%d_%s_%s" % (self.step, self._counter, tag, name)
            )
            for name in self.persistent
        }
        for key in self.ledger_keys:
            if touch is not None and key not in touch:
                env[key] = base[key]
                continue
            sort = z3.Int if key in self.settled_keys else z3.Bool
            env[key] = sort(
                "R_%d_%d_%s_%s" % (self.step, self._counter, tag, _symbol("", key))
            )
        return env

    def region_env(self, tag: str, base: _Env, region_path: str) -> _Env:
        """Return the symbols one region writes its values into.

        The variables are fresh.  A flag is fresh only when the region can
        change it, which is the case for the scopes inside the region and for
        the scopes the region sits in; the flag of any other scope keeps the
        expression it has in ``base``.
        """
        touch = set()
        for prefix, scopes in (
            ("$b:", self.before_scopes),
            ("$o:", self.after_scopes),
            ("$w:", self.after_scopes),
        ):
            for scope in scopes:
                if _under(scope, region_path) or region_path.startswith(scope + "."):
                    touch.add(prefix + scope)
        return self.fresh_env(tag, base, frozenset(touch))

    def start_env(self, frame_vars: Mapping[str, z3.ArithRef]) -> _Env:
        """Return the values at the start of a cycle: no aspect has run yet."""
        env: _Env = dict(frame_vars)
        for key in self.ledger_keys:
            # A settled state is only read while its scope owes, and the path
            # that makes the scope owe writes it; any value will do before that.
            env[key] = (
                z3.IntVal(STATE_INIT_ID) if key in self.settled_keys else z3.BoolVal(False)
            )
        return env

    def env_equal(
        self, left: Mapping[str, z3.ArithRef], right: Mapping[str, z3.ArithRef]
    ) -> z3.BoolRef:
        """Return the constraint that two sets of values agree in every slot, flags included.

        A slot that holds the very same expression on both sides needs no
        constraint, which is what a flag that was handed on unchanged looks like.
        """
        return _and(
            self._same(left[name], right[name])
            for name in self.slots
            if not left[name].eq(right[name])
        )

    def _same(self, left: z3.ArithRef, right: z3.ArithRef) -> z3.BoolRef:
        """Return the constraint that one slot holds a value.

        An analysis does not require a value written to an ``int`` variable to be
        integral, since that is what it looks for; the variable then takes the
        integer part of what was written, so that the rest of the cycle, whose
        values the analysis fixes, still has a solution.
        """
        if self.analysis and z3.is_int(left) and not z3.is_int(right):
            return left == z3.ToInt(right)
        return left == right

    def vars_equal(
        self, left: Mapping[str, z3.ArithRef], right: Mapping[str, z3.ArithRef]
    ) -> z3.BoolRef:
        """Return the constraint that two sets of values agree in the persistent variables."""
        return _and(self._same(left[name], right[name]) for name in self.persistent)

    def persistent_env(self, env: Mapping[str, object]) -> _Env:
        """Return the persistent variables of ``env`` as arithmetic expressions."""
        return {
            name: _expect_arith(env[name], "variable %s" % name)
            for name in self.persistent
        }

    def pre_env(self, env: Mapping[str, z3.ArithRef]) -> Dict[str, object]:
        """Return what the actions and guards of a path read: variables, inputs, parameters."""
        merged: Dict[str, object] = {name: env[name] for name in self.persistent}
        merged.update(self.symbols.step_inputs[self.step])
        merged.update(self.symbols.parameters)
        return merged

    def resting_next(self, owner_path: str) -> z3.BoolRef:
        """Return whether ``owner_path`` rests in the next frame."""
        return _owner_resting(self.symbols, self.domain, self.step + 1, owner_path)

    def position_in(self, region: RegionDomainEntry) -> z3.ArithRef:
        """Return the position symbol of a region in the frame the step starts from."""
        return self.symbols.region_position(self.step, region.path)

    def position_next(self, region: RegionDomainEntry) -> z3.ArithRef:
        """Return the position symbol of a region in the frame the step leads to."""
        return self.symbols.region_position(self.step + 1, region.path)

    # ------------------------------------------------------------------
    # one unit
    # ------------------------------------------------------------------
    def flags(
        self, env: Mapping[str, object], keys: Iterable[str]
    ) -> List[Tuple[Tuple[str, ...], z3.BoolRef]]:
        """Enumerate the values the before flags ``keys`` can take on ``env``.

        A flag that is known to be clear is not branched on.  The before actions
        of the scopes around a leaf run outside-in ahead of its first work, so
        a scope's flag is only set once the flags of the scopes around it are:
        an unknown flag is only taken as set where those are set as well, which
        leaves one combination more than there are unknown flags on a chain of
        scopes instead of every subset of them.  Each combination comes with
        the condition that selects it.
        """
        options: List[Tuple[Tuple[str, ...], z3.BoolRef]] = [((), z3.BoolVal(True))]
        keys = list(keys)
        for key in sorted(keys, key=lambda item: (item.count("."), item)):
            around = [
                other
                for other in keys
                if other != key and key[3:].startswith(other[3:] + ".")
            ]
            flag = z3.simplify(env[key])
            if z3.is_false(flag):
                continue
            updated = []
            for on, cond in options:
                if all(other in on for other in around):
                    updated.append((on + (key,), z3.And(cond, flag)))
                updated.append((on, z3.And(cond, z3.Not(flag))))
            options = updated
        return options

    def lower_unit(
        self,
        spec: Tuple[str, Optional[str]],
        gate: z3.BoolRef,
        env_in: _Env,
        ns: Optional[_Namespace],
        tag: str,
        outputs: Optional[Tuple[z3.ArithRef, _Env]],
        record: bool,
        pending_io: Optional[Tuple[z3.BoolRef, z3.BoolRef]] = None,
        capture: bool = False,
    ) -> _UnitResult:
        """Lower the paths of a unit that starts under ``gate`` on ``env_in``.

        ``outputs`` is the position symbol and the variable symbols the selected
        path writes; with ``None`` the unit is only asked whether it can
        succeed.  ``record`` keeps the lowered paths for inspection, which only
        the paths that really run in the step want.  A unit whose paths depend
        on which before actions already ran, or on whether the plain
        during-before of the owner is still pending, is lowered once for every
        combination those flags can take; see :meth:`flags` for which
        combinations that is.  ``pending_io`` holds the pending flag a start
        unit reads and the symbol it writes.  ``capture`` keeps the lowered paths
        of a unit that a group start runs, without constraining anything: they
        describe what the path that starts the group did.
        """
        order = self._unit_counter
        self._unit_counter += 1
        if not self.has_aspects and pending_io is None:
            return self._lower_variant(
                self.units.get(spec),
                gate,
                env_in,
                ns,
                tag,
                outputs,
                record,
                None,
                frozenset(),
                capture,
                order,
            )
        merged = _UnitResult(z3.BoolVal(False))
        oks = []
        fallbacks = []
        # Only the scopes a path of this unit can pass matter to it; the flag
        # of any other scope is handed on as it is.
        scopes = self.relevant_before(spec) if self.has_aspects else ()
        before_options = self.flags(env_in, ["$b:%s" % path for path in scopes])
        if pending_io is None:
            pending_options = [(False, z3.BoolVal(True))]
        else:
            flag = z3.simplify(pending_io[0])
            if z3.is_true(flag):
                pending_options = [(True, z3.BoolVal(True))]
            else:
                pending_options = [
                    (True, pending_io[0]),
                    (False, z3.Not(pending_io[0])),
                ]
        for index, (on, condition) in enumerate(before_options):
            done = frozenset(key[len("$b:") :] for key in on)
            for pending_index, (pending, pending_condition) in enumerate(
                pending_options
            ):
                part = self._lower_variant(
                    self.units.get(spec, done, pending),
                    z3.And(gate, condition, pending_condition),
                    env_in,
                    ns,
                    "%s_v%d_%d" % (tag, index, pending_index),
                    outputs,
                    record,
                    pending_io,
                    frozenset(scopes),
                    capture,
                    order,
                )
                oks.append(part.ok)
                fallbacks.append(part.fallback)
                merged.facts.extend(part.facts)
                merged.defs.extend(part.defs)
                merged.cases.extend(part.cases)
        merged.ok = _or(oks)
        merged.fallback = _or(fallbacks)
        return merged

    def relevant_before(self, spec: Tuple[str, Optional[str]]) -> Tuple[str, ...]:
        """Return the scopes whose before flag a path of the unit can read or set.

        These are the scopes around the leaves whose ``during`` chain some path
        of the unit runs: expanded with no flag set, every such scope ends up
        marked on the path that passes it.
        """
        if spec not in self.units.relevant:
            touched = set()
            for case in self.units.get(spec).cases:
                touched.update(case.before_done)
            self.units.relevant[spec] = tuple(
                path for path in self.before_scopes if path in touched
            )
        return self.units.relevant[spec]

    def _lower_variant(
        self,
        unit: RegionUnitFormal,
        gate: z3.BoolRef,
        env_in: _Env,
        ns: Optional[_Namespace],
        tag: str,
        outputs: Optional[Tuple[z3.ArithRef, _Env]],
        record: bool,
        pending_io: Optional[Tuple[z3.BoolRef, z3.BoolRef]] = None,
        variant_scopes: FrozenSet[str] = frozenset(),
        capture: bool = False,
        order: int = 0,
    ) -> _UnitResult:
        """Lower the paths of one expansion variant of a unit; see :meth:`lower_unit`.

        ``variant_scopes`` are the scopes whose before flag this variant fixes:
        such a flag is set after a path that ran or found the scope's before
        actions and clear after any other path, while the flag of a scope the
        unit cannot pass keeps the expression it came in with.
        """
        pre_env = self.pre_env(env_in)
        prepared_cases = []
        started_here: Dict[str, List[z3.BoolRef]] = {}
        dead_paths: Set[str] = set()
        for case in unit.cases:
            lowering = _prepare_case_lowering(
                case, pre_env, self.persistent, None, self.int_names
            )
            final_env = self.persistent_env(lowering.final_env)
            for path in self.before_scopes:
                key = "$b:%s" % path
                if path in case.before_done:
                    final_env[key] = z3.BoolVal(True)
                elif path in variant_scopes:
                    final_env[key] = z3.BoolVal(False)
                else:
                    final_env[key] = env_in[key]
            owed_leaves = dict(case.owed_leaves)
            for path in self.after_scopes:
                key = "$o:%s" % path
                final_env[key] = z3.BoolVal(True) if path in case.owed else env_in[key]
                key = "$w:%s" % path
                if key not in self.settled_keys:
                    continue
                if path in case.owed:
                    final_env[key] = z3.IntVal(
                        self.domain.state_path_to_id(
                            _wrapped_state(self.domain, path, owed_leaves[path])
                        )
                    )
                else:
                    final_env[key] = env_in[key]
            entry = None
            terms: Dict[str, z3.BoolRef] = {}
            nested: Dict[str, Tuple[DomainConstraint, ...]] = {}
            case_tag = "%s_%s" % (tag, len(prepared_cases))
            if _statically_false(case.condition, lowering.guard_terms):
                # A guard on the path is already false on these values, so the
                # path is dead and what follows it is never built.
                terms[ATOM_REGION_ENTER] = z3.BoolVal(False)
                terms[ATOM_REGION_DONE] = z3.BoolVal(False)
                dead_paths.add(case.label)
            elif case.target_kind == "owner":
                before_entry = len(self.constraints)
                entry = self.entry(case.target_state_path, final_env, ns, case_tag)
                # What the start says about the values only holds where the
                # path got as far as the start; it is put back below.
                started_here[case.label] = self.constraints[before_entry:]
                del self.constraints[before_entry:]
                terms[ATOM_REGION_ENTER] = entry.ok
                nested[ATOM_REGION_ENTER] = _implied(entry.defs)
            elif case.target_kind == "done":
                before_check = len(self.constraints)
                viable, viable_defs = self.done_viable(ns, final_env, case_tag)
                started_here[case.label] = self.constraints[before_check:]
                del self.constraints[before_check:]
                terms[ATOM_REGION_DONE] = viable
                nested[ATOM_REGION_DONE] = _implied(viable_defs)
            prepared_cases.append(
                (
                    case,
                    replace(
                        lowering,
                        region_terms=terms,
                        region_definedness=nested,
                        priority_first=True,
                    ),
                    final_env,
                    entry,
                )
            )

        lowerings = {case.label: item for case, item, _, _ in prepared_cases}
        condition_cache: Dict[str, _LoweredBoolTemplate] = {}
        accepted_cache: Dict[str, _LoweredBoolTemplate] = {}

        def accepted_lookup(label, active):
            if label not in accepted_cache:
                condition = condition_for(label, active)
                accepted_cache[label] = _LoweredBoolTemplate(
                    _and((gate, condition.expr)),
                    _guarded_domain_constraints(
                        gate, condition.definedness_constraints
                    ),
                )
            return accepted_cache[label]

        def condition_for(label, active):
            if label in condition_cache:
                return condition_cache[label]
            if label in active:  # pragma: no cover - macro expansion has no cycles.
                raise _internal_bmc_error(
                    "recursive accepted-case dependency while lowering %r." % label
                )
            active.add(label)
            value = _lower_bool_template(
                lowerings[label].case.condition,
                lowerings[label],
                accepted_lookup,
                active,
                self.symbols,
                self.step,
            )
            active.remove(label)
            condition_cache[label] = value
            return value

        for case, _, _, _ in prepared_cases:
            condition_for(case.label, set())

        result = _UnitResult(z3.BoolVal(False))
        # Whenever the unit runs, the guards it evaluates have to be defined,
        # whichever path ends up taken and also when none does: the runtime
        # raises as soon as a guard fails to evaluate.  The constraints of a
        # condition already hold each guard to what is evaluated before it.
        if self.analysis:
            result.defs.extend(
                self._point_requirements(unit, gate, pre_env, accepted_lookup)
            )
        for condition in condition_cache.values():
            for item in condition.definedness_constraints:
                result.defs.append((gate, item))
                if record and not self.analysis:
                    self.constraints.append(z3.Implies(gate, item.constraint))
        # A path that ends in a group start or in the check that a finished
        # region may stay finished has run its actions before that is decided,
        # so they have to be defined whenever the path got that far, also when
        # the start or the check then turns out to fail.
        for case, lowering, _, _ in prepared_cases:
            decided = (ATOM_REGION_ENTER, ATOM_REGION_DONE)
            if not any(name in lowering.region_terms for name in decided):
                continue
            if case.label in dead_paths:
                continue
            relaxed = replace(
                lowering,
                region_terms={name: z3.BoolVal(True) for name in lowering.region_terms},
                region_definedness={},
            )
            reached = _and(
                (
                    gate,
                    _lower_bool_template(
                        case.condition,
                        relaxed,
                        accepted_lookup,
                        set(),
                        self.symbols,
                        self.step,
                    ).expr,
                )
            )
            for item in lowering.definedness_constraints:
                result.defs.append((reached, item))
                if record and not self.analysis:
                    self.constraints.append(z3.Implies(reached, item.constraint))
            self.constraints.extend(
                z3.Implies(reached, item) for item in started_here.get(case.label, ())
            )
        antecedents = []
        fallback = []
        for case, lowering, final_env, entry in prepared_cases:
            condition = condition_cache[case.label]
            antecedent = _and((gate, condition.expr))
            antecedents.append(antecedent)
            if case.kind == "fallback":
                fallback.append(antecedent)
            definedness = (
                *condition.definedness_constraints,
                *lowering.definedness_constraints,
            )
            if entry is not None:
                result.facts.extend(
                    (z3.And(antecedent, cond), sym, value)
                    for cond, sym, value in entry.facts
                )
            if outputs is None:
                continue
            if entry is None and case.target_kind == "owner":
                # The path was found dead before its entry was built.
                continue
            out_pos, env_out = outputs
            parts: List[z3.BoolRef] = []
            if case.target_kind == "leaf":
                parts.append(out_pos == z3.IntVal(case.target_state_id))
            elif case.target_kind == "done":
                parts.append(out_pos == z3.IntVal(REGION_DONE_ID))
            elif case.target_kind == "terminate":
                parts.append(out_pos == z3.IntVal(STATE_TERMINATE_ID))
            else:
                parts.append(out_pos == entry.out_pos)
            source_env = entry.env_out if entry is not None else final_env
            if entry is None:
                for key in self.ledger_keys:
                    if env_out[key].eq(env_in[key]) and not final_env[key].eq(
                        env_in[key]
                    ):  # pragma: no cover - a unit only changes flags it can pass.
                        raise _internal_bmc_error(
                            "flag %s is changed by a unit that was taken not to "
                            "touch it (%s)." % (key, case.label)
                        )
            parts.append(self.env_equal(env_out, source_env))
            if pending_io is not None:
                parts.append(pending_io[1] == z3.BoolVal(case.plain_pending_after))
            result.defs.extend((antecedent, item) for item in definedness)
            if entry is not None:
                result.defs.extend(
                    (z3.And(antecedent, cond), item) for cond, item in entry.defs
                )
            if record and not self.analysis:
                parts.extend(
                    z3.Implies(antecedent, item.constraint) for item in definedness
                )
                if entry is not None:
                    parts.extend(
                        z3.Implies(z3.And(antecedent, cond), item.constraint)
                        for cond, item in entry.defs
                    )
            consequent = _and(parts)
            implication = z3.Implies(antecedent, consequent)
            self.constraints.append(implication)
            if record:
                selector = z3.Bool("C_%d_%s" % (self.step, _symbol(tag, case.label)))
                self.constraints.append(selector == antecedent)
            else:
                selector = antecedent
            relation = RegionCaseRelation(
                self.step,
                case,
                selector,
                antecedent,
                consequent,
                implication,
                order,
                tuple(entry.cases) if entry is not None else (),
                tuple(lowering.call_records),
                tuple(entry.flushes) if entry is not None else (),
            )
            result.cases.append(relation)
            if record:
                self.cases.append(relation)
        result.ok = _or(antecedents)
        result.fallback = _or(fallback)
        return result

    def _point_requirements(
        self,
        unit: RegionUnitFormal,
        gate: z3.BoolRef,
        pre_env: Mapping[str, object],
        accepted_lookup,
    ) -> List[Tuple[z3.BoolRef, DomainConstraint]]:
        """Return what each operation the runtime evaluates in ``unit`` requires.

        The runtime evaluates the guards and actions of a candidate before it
        decides on the candidate, so an operation on a path that dead-ends or
        that a higher priority wins over can raise as well.  Every such
        operation is an evaluation point of the unit; each is lowered once, on
        the values the point before it left, and is reached under ``gate`` and
        the control condition recorded for it.

        :param unit: Expansion variant being lowered.
        :param gate: Condition under which the unit runs.
        :param pre_env: Values the unit starts on.
        :param accepted_lookup: Lowers the acceptance atoms of the unit's paths.
        :return: Pairs of the condition an operation is reached under and what
            has to be defined there, in evaluation order.
        """
        envs: Dict[int, Mapping[str, object]] = {}
        terms: Dict[int, Mapping[str, z3.BoolRef]] = {}
        found: List[Tuple[z3.BoolRef, DomainConstraint]] = []
        relaxed = {
            ATOM_REGION_ENTER: z3.BoolVal(True),
            ATOM_REGION_DONE: z3.BoolVal(True),
        }
        for point in unit.evaluation_points:
            env = pre_env if point.parent is None else envs[id(point.parent)]
            guard_terms = {} if point.parent is None else terms[id(point.parent)]
            if point.guard is not None:
                term, own = _lower_guard_requirement(
                    point.guard,
                    env,
                    (),
                    "transition %s" % point.guard.transition_label,
                )
                guard_terms = dict(guard_terms, **{point.guard.requirement_id: term})
            else:
                block = point.block
                env, own, _calls = _execute_action_block(
                    block,
                    env,
                    "transition %s" % block.transition_label
                    if block.transition_label is not None
                    else "state %s" % block.owner_state_path,
                    self.domain.persistent_variable_names,
                    None,
                    self.int_names,
                )
            envs[id(point)] = env
            terms[id(point)] = guard_terms
            if not own:
                continue
            reached = _lower_bool_template(
                point.condition,
                _CaseLowering(
                    None,
                    guard_terms,
                    {key: () for key in guard_terms},
                    env,
                    (),
                    region_terms=relaxed,
                ),
                accepted_lookup,
                set(),
                self.symbols,
                self.step,
            ).expr
            found.extend((_and((gate, reached)), item) for item in own)
        return found

    def sites(self) -> Tuple[BmcRuntimeErrorSite, ...]:
        """Return the runtime-error sites of the step, in evaluation order.

        Only an analysis collects requirements; a site holds where an operation
        is reached and what it needs to be defined does not hold.
        """
        return tuple(
            _error_site(self.step, item, _and((cond, z3.Not(item.constraint))))
            for cond, item in self.requirements
        )

    # ------------------------------------------------------------------
    # entering a state that owns regions, and finishing a region
    # ------------------------------------------------------------------
    def entry(
        self,
        owner_path: str,
        env_in: _Env,
        ns: Optional[_Namespace],
        tag: str,
    ) -> _Entry:
        """Initialize the regions of ``owner_path`` in order on ``env_in``."""
        owner = self.domain.state_by_path(owner_path)
        out_pos = self.fresh_int("%s_pos" % tag)
        env_out = self.fresh_env("%s_env" % tag)
        for entered, entered_env in self._entering:
            if entered == owner_path and all(
                entered_env[name].eq(env_in[name]) for name in self.slots
            ):
                # Same owner on the same values: nothing can change, so this
                # path is the loop the runtime rejects.
                return _Entry(z3.BoolVal(False), out_pos, env_out, [], [])
        limit = self.prepared.options.max_group_reentries
        if sum(1 for entered, _ in self._entering if entered == owner_path) >= limit:
            raise BmcBuildError(
                "state %r re-enters its own group more than %d times inside one "
                "cycle, so the relation cannot be bounded; raise "
                "BmcOptions.max_group_reentries to unroll it deeper."
                % (owner_path, limit)
            )
        self._entering.append((owner_path, env_in))
        outer_sink = self._flush_sink
        entry_flushes: List[RegionFlushRelation] = []
        self._flush_sink = entry_flushes
        try:
            regions = _regions_of(self.domain, owner_path)
            env = env_in
            positions: Dict[str, z3.ArithRef] = {}
            ok_terms: List[z3.BoolRef] = []
            facts: List[_Fact] = []
            defs: List[Tuple[z3.BoolRef, DomainConstraint]] = []
            nested_facts: List[_Fact] = []
            begun: List[RegionCaseRelation] = []
            pending = z3.BoolVal(True) if owner_path in self.pending_owners else None
            for index, region in enumerate(regions):
                position = self.fresh_int("%s_r%d" % (tag, index))
                pending_io = None
                if pending is not None:
                    next_pending = z3.Bool(
                        "R_%d_%s_pending%d" % (self.step, _symbol(tag, ""), index)
                    )
                    pending_io = (pending, next_pending)
                    pending = next_pending
                unit = self.units.get(("init", region.path))
                # A unit that assigns nothing leaves the values as they are, so
                # they keep their expressions and a loop stays recognizable.
                env_next = (
                    env
                    if not self.has_aspects
                    and pending_io is None
                    and _assigns_nothing(unit)
                    else self.region_env("%s_r%d" % (tag, index), env, region.path)
                )
                others_live = _or(
                    [z3.BoolVal(index < len(regions) - 1)]
                    + [
                        positions[item.path] != z3.IntVal(REGION_DONE_ID)
                        for item in regions[:index]
                    ]
                )
                region_ns = _Namespace(region, others_live, ns)
                before_start = len(self.constraints)
                result = self.lower_unit(
                    ("init", region.path),
                    z3.BoolVal(True),
                    env,
                    region_ns,
                    "%s_r%d" % (tag, index),
                    (position, env_next),
                    record=False,
                    pending_io=pending_io,
                    capture=True,
                )
                begun.extend(result.cases)
                # A region is only started when the ones before it started, so
                # what its start says about the values holds only there.
                reached = _and(ok_terms)
                self.constraints[before_start:] = [
                    z3.Implies(reached, item)
                    for item in self.constraints[before_start:]
                ]
                ok_terms.append(result.ok)
                nested_facts.extend(result.facts)
                defs.extend((_and((reached, cond)), item) for cond, item in result.defs)
                positions[region.path] = position
                # The branch of a region is over: the scopes below it that owe
                # an after action run it now.
                flushed = len(defs)
                before_flush = len(self.constraints)
                env = self.flush(
                    region.path,
                    z3.BoolVal(True),
                    env_next,
                    "%s_f%d" % (tag, index),
                    defs,
                )
                started = _and(ok_terms)
                defs[flushed:] = [
                    (_and((started, cond)), item) for cond, item in defs[flushed:]
                ]
                self.constraints[before_flush:] = [
                    z3.Implies(started, item)
                    for item in self.constraints[before_flush:]
                ]
            if z3.is_false(z3.simplify(_and(ok_terms))):
                # A region cannot start on these values, so the whole entry
                # fails and what follows an entry is never reached.  What the
                # starts evaluated on the way still has to be defined.
                return _Entry(z3.BoolVal(False), out_pos, env_out, [], defs)
            # The regions can only all be done right after starting when each of
            # them has a start path that ends in a finished region or in a nested
            # group; otherwise the owner certainly rests and what would follow a
            # finished group is never reached.
            may_finish = all(
                any(
                    case.target_kind in ("done", "owner")
                    for case in self.units.get(("init", region.path)).cases
                )
                for region in regions
            )
            all_done = (
                _and(
                    positions[item.path] == z3.IntVal(REGION_DONE_ID)
                    for item in regions
                )
                if may_finish
                else z3.BoolVal(False)
            )
            self.constraints.append(
                z3.Implies(
                    z3.Not(all_done),
                    z3.And(
                        out_pos == z3.IntVal(owner.id), self.env_equal(env_out, env)
                    ),
                )
            )
            if may_finish:
                # The owner only continues when every region started.
                cont = self.lower_unit(
                    ("cont", owner_path),
                    z3.And(all_done, _and(ok_terms)),
                    env,
                    ns,
                    "%s_c" % tag,
                    (out_pos, env_out),
                    record=False,
                    capture=True,
                )
                begun.extend(cont.cases)
            else:
                cont = _UnitResult(z3.BoolVal(False))
            resting = out_pos == z3.IntVal(owner.id)
            for region in regions:
                facts.append(
                    (resting, self.position_next(region), positions[region.path])
                )
            facts.extend(
                (z3.And(resting, cond), sym, value) for cond, sym, value in nested_facts
            )
            facts.extend(cont.facts)
            defs.extend(cont.defs)
            ok = z3.And(_and(ok_terms), z3.Or(z3.Not(all_done), cont.ok))
            return _Entry(ok, out_pos, env_out, facts, defs, begun, entry_flushes)
        finally:
            self._flush_sink = outer_sink
            self._entering.pop()

    def done_viable(
        self, ns: _Namespace, env: _Env, tag: str
    ) -> Tuple[z3.BoolRef, List[Tuple[z3.BoolRef, DomainConstraint]]]:
        """Return whether a region that just finished may stay finished.

        The second value is what that check requires to be defined: the guards
        of the continuation of the owner are only evaluated when no other
        region is still working.
        """
        region = ns.region
        alone = z3.Not(ns.others_live)
        before_check = len(self.constraints)
        cont = self.lower_unit(
            ("cont", region.owner_path),
            z3.BoolVal(True),
            env,
            ns.parent,
            "%s_v" % tag,
            None,
            record=False,
        )
        # The continuation is only tried when no other region is still working,
        # so what its starts say about the values holds only there.
        self.constraints[before_check:] = [
            z3.Implies(alone, item) for item in self.constraints[before_check:]
        ]
        return z3.Or(ns.others_live, cont.ok), [
            (z3.And(alone, cond), item) for cond, item in cont.defs
        ]

    # ------------------------------------------------------------------
    # one group of regions advancing in a cycle
    # ------------------------------------------------------------------
    def advance_group(
        self,
        owner_path: str,
        gate: z3.BoolRef,
        env_in: _Env,
        ns: Optional[_Namespace],
        tag: str,
        static: Optional[Mapping[str, int]] = None,
    ):
        """Advance every working region of a resting owner, in order.

        With ``static`` the position of every region is known, because the group
        rests in the position a hot start began in: ``static`` maps each region path
        to its position id and only the unit of that position is lowered.  A region
        that waits for initialization then runs its start, and a branch that rests
        in a state only a cycle can leave runs the cycle that leaves it; neither can
        be sure to succeed, and their failure is kept in ``_hot_fail``.
        """
        regions = _regions_of(self.domain, owner_path)
        env = env_in
        after: Dict[str, z3.ArithRef] = {}
        fallback_terms: List[z3.BoolRef] = []
        # A hot start does not enter the owner, so the plain ``during before`` that
        # waits for the first real child of a group being entered never runs, not
        # even when every region of the owner waits for its start.
        for index, region in enumerate(regions):
            position_in = self.position_in(region)
            live = z3.And(
                position_in != z3.IntVal(REGION_DONE_ID),
                position_in != z3.IntVal(REGION_INACTIVE_ID),
            )
            q = self.fresh_int("%s_q%d" % (tag, index))
            env_out = self.region_env("%s_e%d" % (tag, index), env, region.path)
            others_live = _or(
                [
                    after[item.path] != z3.IntVal(REGION_DONE_ID)
                    for item in regions[:index]
                ]
                + [
                    z3.And(
                        self.position_in(item) != z3.IntVal(REGION_DONE_ID),
                        self.position_in(item) != z3.IntVal(REGION_INACTIVE_ID),
                    )
                    for item in regions[index + 1 :]
                ]
            )
            region_ns = _Namespace(region, others_live, ns)
            self.constraints.append(
                z3.Implies(
                    z3.And(gate, z3.Not(live)),
                    z3.And(q == position_in, self.env_equal(env_out, env)),
                )
            )
            region_fallback: List[z3.BoolRef] = []
            if static is None:
                positions = tuple(region.position_state_ids)
            elif static[region.path] == REGION_DONE_ID:
                positions = ()
            else:
                positions = (static[region.path],)
            for position_id in positions:
                # A start that failed in an earlier unit made the cycle a Delta, so
                # this unit does not run: none of its operations is evaluated and
                # none of them has to be defined.
                ran = self._ran_so_far()
                unit_gate = z3.And(
                    gate,
                    *([] if ran is None else [ran]),
                    position_in == z3.IntVal(position_id),
                )
                unit_tag = "%s_w%d_%d" % (tag, index, position_id)
                if position_id == REGION_PENDING_ID:
                    # The region has not been initialized: its turn starts it.
                    result = self.lower_unit(
                        ("init", region.path),
                        unit_gate,
                        env,
                        region_ns,
                        unit_tag,
                        (q, env_out),
                        record=True,
                    )
                    self._hot_fail.append(z3.And(unit_gate, z3.Not(result.ok)))
                    self._emit_facts(result)
                    region_fallback.append(result.fallback)
                    continue
                entry = self.domain.state_by_id(position_id)
                if entry.owns_regions:
                    # The branch rests in a state that owns regions of its own:
                    # its regions advance first, and once they all finished
                    # the state continues inside this region.
                    sub_env, sub_after, sub_done, sub_fallback = self.advance_group(
                        entry.path, unit_gate, env, region_ns, unit_tag, static
                    )
                    keep = z3.And(unit_gate, z3.Not(sub_done))
                    self.constraints.append(
                        z3.Implies(
                            keep,
                            z3.And(
                                q == z3.IntVal(position_id),
                                self.env_equal(env_out, sub_env),
                            ),
                        )
                    )
                    self.assert_positions_next(entry.path, keep, sub_after)
                    result = self.lower_unit(
                        ("cont", entry.path),
                        z3.And(unit_gate, sub_done),
                        sub_env,
                        region_ns,
                        "%s_c" % unit_tag,
                        (q, env_out),
                        record=True,
                    )
                    # Only the branch that rests in this owner can be a fallback
                    # here: for any other position the group below it is not
                    # running, and its terms hold vacuously.
                    result.fallback = z3.And(unit_gate, z3.Not(sub_done), sub_fallback)
                elif not entry.is_stoppable:
                    # The branch rests in a plain composite state that waits for its
                    # initial transition, or in a pseudo state: a cycle has to leave it.
                    result = self.lower_unit(
                        ("wait", entry.path),
                        unit_gate,
                        env,
                        region_ns,
                        unit_tag,
                        (q, env_out),
                        record=True,
                    )
                    self._hot_fail.append(z3.And(unit_gate, z3.Not(result.ok)))
                else:
                    result = self.lower_unit(
                        ("leaf", entry.path),
                        unit_gate,
                        env,
                        region_ns,
                        unit_tag,
                        (q, env_out),
                        record=True,
                    )
                self._emit_facts(result)
                region_fallback.append(result.fallback)
            fallback_terms.append(
                z3.Or(z3.Not(z3.And(gate, live)), _or(region_fallback))
            )
            after[region.path] = q
            # The branch of the region is over: the scopes below it that owe an
            # after action run it now.
            env = self.flush(region.path, gate, env_out, "%s_f%d" % (tag, index))
        all_done = _and(
            after[item.path] == z3.IntVal(REGION_DONE_ID) for item in regions
        )
        return env, after, all_done, _and(fallback_terms)

    def assert_positions_next(
        self, owner_path: str, keep: z3.BoolRef, after: Mapping[str, z3.ArithRef]
    ) -> None:
        """Carry the positions of a group that stays resting into the next frame."""
        resting = self.resting_next(owner_path)
        for region in _regions_of(self.domain, owner_path):
            self.constraints.append(
                z3.Implies(
                    z3.And(keep, resting),
                    self.position_next(region) == after[region.path],
                )
            )

    # ------------------------------------------------------------------
    # sources of a step
    # ------------------------------------------------------------------
    def flush(
        self,
        prefix: str,
        gate: z3.BoolRef,
        env_in: _Env,
        tag: str,
        defs: Optional[List[Tuple[z3.BoolRef, DomainConstraint]]] = None,
    ) -> _Env:
        """Run the after actions that the scopes under ``prefix`` owe.

        The scopes are settled one at a time, innermost first, in the order a
        flush runs them: a scope that owes runs its after actions on the values
        the scope before it left, and a scope that does not owe leaves them
        alone.  That is two branches per scope, so the settlement grows with
        the number of scopes and not with the number of their subsets.  The
        settled flags become ``False`` and every other flag keeps its
        expression.

        The definedness of the actions is a requirement of the step, unless
        ``defs`` is given: a flush that belongs to entering a group only counts
        when the path that enters is taken, so its requirements are appended to
        ``defs`` and that path carries them.
        """
        keys = ["$o:%s" % path for path in self.after_scopes if _under(path, prefix)]
        if not prefix:
            # The flags of scopes inside a region were settled when the branch
            # of that region ended.
            keys = [key for key in keys if key not in self.region_owed_keys]
        live = [key for key in keys if not z3.is_false(z3.simplify(env_in[key]))]
        if not live:
            return env_in
        env = env_in
        order = sorted(
            (key[len("$o:") :] for key in live), key=lambda item: (-len(item), item)
        )
        for index, scope in enumerate(order):
            owes = env_in["$o:%s" % scope]
            case = self.units.flush(frozenset({scope})).cases[0]
            lowering = _prepare_case_lowering(
                case, self.pre_env(env), self.persistent, None, self.int_names
            )
            order = self._unit_counter
            self._unit_counter += 1
            # One settlement per state its handlers can be told; without a call
            # the state does not matter and one settlement is enough.
            told = self.settled_states[scope] if lowering.call_records else ()
            for state_path in told or (None,):
                condition = z3.And(gate, owes)
                if "$w:%s" % scope in self.settled_keys:
                    condition = z3.And(
                        condition,
                        env_in["$w:%s" % scope]
                        == z3.IntVal(self.domain.state_path_to_id(state_path)),
                    )
                self._flush_sink.append(
                    RegionFlushRelation(
                        self.step,
                        order,
                        scope,
                        prefix,
                        condition,
                        tuple(
                            replace(
                                record,
                                state_path=state_path,
                                active_leaf_path=state_path,
                            )
                            for record in lowering.call_records
                        ),
                    )
                )
            out = self.fresh_env("%s_s%d" % (tag, index), env, frozenset())
            parts = [self.vars_equal(out, self.persistent_env(lowering.final_env))]
            if defs is not None:
                defs.extend((owes, item) for item in lowering.definedness_constraints)
            elif self.analysis:
                self.requirements.extend(
                    (z3.And(gate, owes), item)
                    for item in lowering.definedness_constraints
                )
            else:
                parts.extend(
                    item.constraint for item in lowering.definedness_constraints
                )
            self.constraints.append(z3.Implies(z3.And(gate, owes), _and(parts)))
            self.constraints.append(
                z3.Implies(z3.And(gate, z3.Not(owes)), self.vars_equal(out, env))
            )
            env = out
        for key in keys:
            env[key] = z3.BoolVal(False)
        return env

    def next_env(self, tag: str) -> _Env:
        """Return where a source writes the values it leaves behind.

        Without aspects these are the variables of the next frame. With aspects
        the cycle still ends with a flush, so the source writes intermediate
        values and :meth:`finish_step` carries them into the next frame.
        """
        if self.has_aspects:
            env = self.fresh_env(tag)
            # Nothing inside a region still owes an after action when a cycle
            # ends, so those flags are known here.
            for key in self.region_owed_keys:
                env[key] = z3.BoolVal(False)
            return env
        return dict(self.symbols.frame_vars[self.step + 1])

    def finish_step(self, gate: z3.BoolRef, env_mid: _Env) -> None:
        """Run the flush that ends a cycle and write the next frame's variables."""
        if not self.has_aspects:
            return
        next_vars = self.symbols.frame_vars[self.step + 1]
        ended = self.symbols.frame_state(self.step + 1) == z3.IntVal(STATE_TERMINATE_ID)
        # A cycle that ends the machine owes no flush.
        self.constraints.append(
            z3.Implies(z3.And(gate, ended), self.vars_equal(next_vars, env_mid))
        )
        live = z3.And(gate, z3.Not(ended))
        env_end = self.flush("", live, env_mid, "end")
        self.constraints.append(z3.Implies(live, self.vars_equal(next_vars, env_end)))

    def build_leaf_source(self, state_id: int) -> None:
        """Lower the step of a frame that rests in a leaf outside every region."""
        entry = self.domain.state_by_id(state_id)
        gate = self.symbols.frame_state(self.step) == z3.IntVal(state_id)
        env_mid = self.next_env("m%d" % state_id)
        result = self.lower_unit(
            ("leaf", entry.path),
            gate,
            self.start_env(self.symbols.frame_vars[self.step]),
            None,
            "m%d" % state_id,
            (self.symbols.frame_state(self.step + 1), env_mid),
            record=True,
        )
        self._emit_facts(result)
        self.finish_step(gate, env_mid)
        self.gamma_terms.append(z3.And(gate, result.fallback))

    def at_start(self) -> z3.BoolRef:
        """Return the condition that the frame of this step holds the start position."""
        return _at_start(self.symbols, self.step, self.main_id, self.start_ids)

    def build_owner_source(self, state_id: int, apart_from_start: bool = False) -> None:
        """Lower the step of a frame that rests in a state that owns regions.

        The regions advance in order; if all finished the continuation of the owner
        runs in the same step, otherwise the owner keeps resting.  A frame that holds
        the start position of a hot start that waits is the business of
        :meth:`build_hot_owner_source`, and ``apart_from_start`` leaves it out.
        """
        entry = self.domain.state_by_id(state_id)
        gate = self.symbols.frame_state(self.step) == z3.IntVal(state_id)
        if apart_from_start:
            gate = z3.And(gate, z3.Not(self.at_start()))
        tag = "g%d" % state_id
        env_after, after, all_done, fallback = self.advance_group(
            entry.path,
            gate,
            self.start_env(self.symbols.frame_vars[self.step]),
            None,
            tag,
        )
        next_vars = self.next_env("%s_n" % tag)
        keep = z3.And(gate, z3.Not(all_done))
        self.constraints.append(
            z3.Implies(
                keep,
                z3.And(
                    self.symbols.frame_state(self.step + 1) == z3.IntVal(state_id),
                    self.env_equal(next_vars, env_after),
                ),
            )
        )
        self.assert_positions_next(entry.path, keep, after)
        result = self.lower_unit(
            ("cont", entry.path),
            z3.And(gate, all_done),
            env_after,
            None,
            "%s_c" % tag,
            (self.symbols.frame_state(self.step + 1), next_vars),
            record=True,
        )
        self._emit_facts(result)
        self.finish_step(gate, next_vars)
        self.gamma_terms.append(z3.And(gate, z3.Not(all_done), fallback))

    def build_hot_owner_source(self, state_id: int) -> None:
        """Lower the step of the frame that holds the position of a hot start that waits.

        The position is known, so only the units of that position are lowered: a
        region that waits runs its start, a branch in a state only a cycle can leave
        runs the cycle that leaves it, and the other regions work as they do in any
        cycle.  The start of a waiting region may fail, and then the whole cycle is a
        Delta: the machine keeps the start position and the variables.
        """
        entry = self.domain.state_by_id(state_id)
        gate = z3.And(
            self.symbols.frame_state(self.step) == z3.IntVal(state_id),
            self.at_start(),
        )
        tag = "h%d" % state_id
        first_constraint = len(self.constraints)
        first_failure = len(self._hot_fail)
        env_after, after, all_done, fallback = self.advance_group(
            entry.path,
            gate,
            self.start_env(self.symbols.frame_vars[self.step]),
            None,
            tag,
            self.start_ids,
        )
        next_vars = self.next_env("%s_n" % tag)
        keep = z3.And(gate, z3.Not(all_done))
        self.constraints.append(
            z3.Implies(
                keep,
                z3.And(
                    self.symbols.frame_state(self.step + 1) == z3.IntVal(state_id),
                    self.env_equal(next_vars, env_after),
                ),
            )
        )
        self.assert_positions_next(entry.path, keep, after)
        ran = self._ran_so_far()
        result = self.lower_unit(
            ("cont", entry.path),
            z3.And(gate, all_done, *([] if ran is None else [ran])),
            env_after,
            None,
            "%s_c" % tag,
            (self.symbols.frame_state(self.step + 1), next_vars),
            record=True,
        )
        self._emit_facts(result)
        failed = _or(self._hot_fail[first_failure:])
        # A cycle that fails rolls back as a whole: nothing the units say about the
        # next frame holds, and the next frame is this one again.  What the units
        # say about the values that flow inside the cycle stays, because whether
        # a start fails is decided by those values.
        next_frame = {
            symbol.get_id()
            for symbol in (
                [self.symbols.frame_state(self.step + 1)]
                + [
                    self.symbols.region_position(self.step + 1, region.path)
                    for region in self.domain.regions
                ]
                + list(self.symbols.frame_vars[self.step + 1].values())
            )
        }
        self.constraints[first_constraint:] = [
            z3.Implies(z3.Not(failed), item) if _mentions(item, next_frame) else item
            for item in self.constraints[first_constraint:]
        ]
        self.finish_step(z3.And(gate, z3.Not(failed)), next_vars)
        delta = z3.And(gate, failed)
        self.delta_terms.append(delta)
        # The paths that were lowered for the cycle did not run: it is a Delta.
        self.rollback_terms.append(delta)
        self.constraints.append(
            z3.Implies(
                delta,
                z3.And(
                    self.symbols.frame_state(self.step + 1) == z3.IntVal(state_id),
                    self.vars_equal(
                        dict(self.symbols.frame_vars[self.step + 1]),
                        dict(self.symbols.frame_vars[self.step]),
                    ),
                    *[
                        self.symbols.region_position(self.step + 1, path)
                        == z3.IntVal(value)
                        for path, value in sorted(self.start_ids.items())
                    ],
                ),
            )
        )
        self.gamma_terms.append(z3.And(gate, z3.Not(failed), z3.Not(all_done), fallback))

    def build_wait_source(self, state_id: int) -> None:
        """Lower the step of a frame that rests in a state only a cycle can leave.

        A hot start can name a plain composite state, which waits for its initial
        transition, or a pseudo state.  Like the cold start, the cycle may find no
        way on, and then it is a Delta that keeps the machine where it is.
        """
        entry = self.domain.state_by_id(state_id)
        gate = self.symbols.frame_state(self.step) == z3.IntVal(state_id)
        tag = "w%d" % state_id
        env_mid = self.next_env(tag)
        result = self.lower_unit(
            ("wait", entry.path),
            gate,
            self.start_env(self.symbols.frame_vars[self.step]),
            None,
            tag,
            (self.symbols.frame_state(self.step + 1), env_mid),
            record=True,
        )
        self._emit_facts(result)
        self.finish_step(z3.And(gate, result.ok), env_mid)
        delta = z3.And(gate, z3.Not(result.ok))
        self.delta_terms.append(delta)
        self.constraints.append(
            z3.Implies(
                delta,
                z3.And(
                    self.symbols.frame_state(self.step + 1) == z3.IntVal(state_id),
                    self.vars_equal(
                        dict(self.symbols.frame_vars[self.step + 1]),
                        dict(self.symbols.frame_vars[self.step]),
                    ),
                ),
            )
        )

    def initial_env(self) -> _Env:
        """Return the values of frame 0 with the declared initializers filled in.

        The initial frame is pinned to these values anyway, and knowing them as
        constants lets a guard that depends on them be decided while the
        relation is built, which is what ends a group that re-enters itself.
        """
        env: _Env = dict(self.symbols.frame_vars[0])
        lookup: Dict[str, object] = dict(env)
        lookup.update(self.symbols.parameters)
        initial = self.prepared.bound_query.initial
        havoc = set(initial.havoc_names(self.domain))
        for var in self.domain.variables:
            if var.name in havoc or var.role == VariableRole.INPUT:
                continue
            if var.name not in env:
                continue
            define = self.prepared.model.defines[var.name]
            value = _expect_arith(
                _translate_model_expr(
                    define.init, lookup, "initializer for %s" % var.name
                ).z3_expr,
                "initializer for %s" % var.name,
            )
            if value.sort() == env[var.name].sort():
                env[var.name] = value
        return env

    def build_cold_source(self) -> None:
        """Lower the step of the cold-start sentinel; a start that cannot complete is a Delta."""
        gate = self.symbols.frame_state(self.step) == z3.IntVal(STATE_INIT_ID)
        env_in = self.start_env(
            self.initial_env()
            if self.step == 0
            else dict(self.symbols.frame_vars[self.step])
        )
        env_mid = self.next_env("cold")
        result = self.lower_unit(
            ("cold", None),
            gate,
            env_in,
            None,
            "cold",
            (self.symbols.frame_state(self.step + 1), env_mid),
            record=True,
        )
        self._emit_facts(result)
        self.finish_step(z3.And(gate, result.ok), env_mid)
        delta = z3.And(gate, z3.Not(result.ok))
        self.delta_terms.append(delta)
        self.constraints.append(
            z3.Implies(
                delta,
                z3.And(
                    self.symbols.frame_state(self.step + 1) == z3.IntVal(STATE_INIT_ID),
                    self.vars_equal(
                        dict(self.symbols.frame_vars[self.step + 1]),
                        dict(self.symbols.frame_vars[self.step]),
                    ),
                ),
            )
        )

    def build_absorb_source(self) -> None:
        """Lower the step of a terminated frame: it stays terminated and takes no event."""
        gate = self.symbols.frame_state(self.step) == z3.IntVal(STATE_TERMINATE_ID)
        self.constraints.append(
            z3.Implies(
                gate,
                z3.And(
                    self.symbols.frame_state(self.step + 1)
                    == z3.IntVal(STATE_TERMINATE_ID),
                    self.vars_equal(
                        dict(self.symbols.frame_vars[self.step + 1]),
                        dict(self.symbols.frame_vars[self.step]),
                    ),
                    *[
                        z3.Not(self.symbols.event_input(self.step, event.path))
                        for event in self.domain.events
                    ],
                ),
            )
        )

    def _ran_so_far(self) -> Optional[z3.BoolRef]:
        """Return the condition that no unit of the step has failed to start yet.

        ``None`` when no unit can fail, which is every step except a hot start.
        """
        if not self._hot_fail:
            return None
        return z3.Not(_or(self._hot_fail))

    def _emit_facts(self, result: _UnitResult) -> None:
        """Constrain the frame positions that the paths of a unit assign.

        The unit is one that runs in the step, so an analysis also takes the
        requirements it collected.

        :param result: Lowered unit.
        """
        self.constraints.extend(
            z3.Implies(cond, sym == value) for cond, sym, value in result.facts
        )
        if self.analysis:
            self.requirements.extend(result.defs)

    def finish(self) -> Tuple[z3.BoolRef, z3.BoolRef, z3.BoolRef]:
        """Return the constraints that tie Delta and Gamma of the step to its paths."""
        delta_flag = self.symbols.delta_flag(self.step)
        gamma_flag = self.symbols.gamma_flag(self.step)
        delta_constraint = delta_flag == _or(self.delta_terms)
        gamma_constraint = gamma_flag == _or(self.gamma_terms)
        mutex = z3.Not(z3.And(delta_flag, gamma_flag))
        return delta_constraint, gamma_constraint, mutex


def _mentions(expr: z3.ExprRef, targets: Set[int]) -> bool:
    """Return whether ``expr`` contains one of the terms with the ids in ``targets``."""
    seen: Set[int] = set()
    pending = [expr]
    while pending:
        term = pending.pop()
        key = term.get_id()
        if key in seen:
            continue
        seen.add(key)
        if key in targets:
            return True
        pending.extend(term.children())
    return False


def _implied(
    pairs: Iterable[Tuple[z3.BoolRef, DomainConstraint]],
) -> Tuple[DomainConstraint, ...]:
    """Turn requirements that each hold under a condition into plain constraints."""
    return tuple(
        DomainConstraint(z3.Implies(cond, item.constraint), item.source, item.kind)
        for cond, item in pairs
    )


def _statically_false(template, guard_terms: Mapping[str, z3.BoolRef]) -> bool:
    """Return whether a path condition is false whatever the other atoms are.

    Guards that have already been decided on the values at hand are used; every
    other atom is unknown.
    """

    def truth(node) -> Optional[bool]:
        if node.kind == "true":
            return True
        if node.kind == "atom":
            name = node.name
            if name.startswith("guard:") and name[len("guard:") :] in guard_terms:
                term = z3.simplify(guard_terms[name[len("guard:") :]])
                if z3.is_true(term):
                    return True
                if z3.is_false(term):
                    return False
            return None
        values = [truth(item) for item in node.operands]
        if node.kind == "not":
            return None if values[0] is None else not values[0]
        if node.kind == "and":
            if any(item is False for item in values):
                return False
            return True if all(item is True for item in values) else None
        # An "or" is as good as unknown unless one operand is certainly true:
        # the conditions seen here only or together atoms that are unknown.
        return True if any(item is True for item in values) else None

    return truth(template) is False


def _aspect_scopes(model) -> Tuple[Tuple[str, ...], Tuple[str, ...]]:
    """Return the paths of the scopes that declare before and after aspects."""
    before = []
    after = []
    for namespace in walk_namespaces(model.root_state):
        path = ".".join(namespace.path)
        if namespace.list_on_during_aspects(aspect="before"):
            before.append(path)
        if namespace.list_on_during_aspects(aspect="after"):
            after.append(path)
    return tuple(sorted(before)), tuple(sorted(after))


def _under(path: str, prefix: str) -> bool:
    """Return whether the scope ``path`` is the scope ``prefix`` or sits below it."""
    return not prefix or path == prefix or path.startswith(prefix + ".")


def _assigns_nothing(unit: RegionUnitFormal) -> bool:
    """Return whether no path of the unit can change a variable.

    A path that enters a state owning regions starts those regions, and that
    runs their actions, so such a unit is never taken to leave values alone.
    """
    return not any(
        case.target_kind == "owner"
        or any(block.operations for block in case.action_blocks)
        for case in unit.cases
    )


def _symbol(tag: str, label: str) -> str:
    """Return a solver-safe symbol fragment for a tag and a case label."""
    from .relation import _safe_symbol_fragment

    return _safe_symbol_fragment("%s::%s" % (tag, label))


def _build_step(
    prepared: BmcPreparedContext,
    symbols: BmcTraceSymbols,
    units: _Units,
    frame_domain,
    step_index: int,
    analysis: bool = False,
) -> _StepBuilder:
    """Lower every source a step can start from.

    :param prepared: Prepared context of a model with regions.
    :param symbols: Symbols of the trace.
    :param units: Unit expansions shared by the steps being built.
    :param frame_domain: States a frame can rest in.
    :param step_index: Zero-based step to lower.
    :param analysis: Lower the step to locate runtime errors instead of to
        describe the cycle, see :class:`_StepBuilder`; defaults to ``False``.
    :return: The builder holding the constraints, paths and flags of the step.
    """
    domain = prepared.domain
    builder = _StepBuilder(prepared, symbols, units, step_index, analysis)
    if step_index == 0:
        source = _initial_source(prepared)
        source_ids = (source.source_state_id,)
    else:
        source_ids = frame_domain.recurrence_state_ids
    for state_id in source_ids:
        if state_id == STATE_INIT_ID:
            builder.build_cold_source()
        elif state_id == STATE_TERMINATE_ID:
            builder.build_absorb_source()
        elif domain.state_by_id(state_id).owns_regions:
            if not _in_region(domain, domain.state_by_id(state_id).path):
                if builder.start_waits and state_id == builder.main_id:
                    builder.build_hot_owner_source(state_id)
                    builder.build_owner_source(state_id, apart_from_start=True)
                else:
                    builder.build_owner_source(state_id)
        elif not _in_region(domain, domain.state_by_id(state_id).path):
            if domain.state_by_id(state_id).is_stoppable:
                builder.build_leaf_source(state_id)
            else:
                builder.build_wait_source(state_id)
    return builder


def region_error_analysis(
    core: BmcCoreFormula,
) -> Tuple[Tuple[z3.BoolRef, Tuple[BmcRuntimeErrorSite, ...]], ...]:
    """Locate the runtime errors of every cycle of a model with regions.

    The relation of a cycle requires every operation it runs to be defined, so a
    cycle in which the runtime raises has no solution there.  This builds each
    cycle a second time without that requirement and keeps what it would have
    required as error sites: an operation is a site when the runtime evaluates
    it, also on a candidate that dead-ends or loses to a higher priority, and a
    model that holds a site with the skeleton of its cycle is a cycle in which
    that operation raises.

    :param core: Core formula of a model with regions.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :return: For every cycle the skeleton, which fixes the values of the cycle
        and nothing else, and the sites of the cycle in evaluation order.
    :rtype: Tuple[Tuple[z3.BoolRef, Tuple[pyfcstm.bmc.relation.BmcRuntimeErrorSite, ...]], ...]
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``core`` has no regions.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.bmc.region_relation import region_error_analysis
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... input int d;
        ... def int x = 0;
        ... state Root {
        ...     region A { [*] -> P; state P { during { x = 10 % d; } } }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
        >>> [(len(sites) > 0) for _, sites in region_error_analysis(core)]
        [True]
    """
    if not core.region_steps:
        raise BmcBuildError("the core formula has no regions.")
    prepared = core.context
    frame_domain = _relation_frame_domain(prepared)
    units = _Units(prepared.domain)
    found = []
    for step_index in range(prepared.domain.bound):
        builder = _build_step(
            prepared, core.symbols, units, frame_domain, step_index, analysis=True
        )
        delta_constraint, gamma_constraint, mutex = builder.finish()
        skeleton = _and(
            tuple(builder.constraints) + (delta_constraint, gamma_constraint, mutex)
        )
        found.append((skeleton, builder.sites()))
    return tuple(found)


def build_region_core_formula(context: BmcPreparedContext) -> BmcCoreFormula:
    """Build ``Core_N`` for a prepared context whose model has regions.

    The result has the shape of :func:`pyfcstm.bmc.relation.build_bmc_core_formula`
    for a model without regions; ``region_steps`` additionally carries the paths
    of every step.  Only a cold start (and an already terminated start) is
    supported for a model with regions.

    :param context: Prepared BMC context of a model with regions.
    :type context: pyfcstm.bmc.engine.BmcPreparedContext
    :return: Solver-level core formula bundle.
    :rtype: pyfcstm.bmc.relation.BmcCoreFormula
    :raises pyfcstm.bmc.errors.UnsupportedBmcQuery: If the model or the query
        uses something the region relation does not support yet.
    :raises pyfcstm.bmc.errors.BmcBuildError: If the prepared context is
        internally inconsistent.

    Example::

        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 2: terminated();'))
        >>> [step.step_index for step in core.region_steps]
        [0, 1]
    """
    prepared = _require_context(context)
    if not prepared.domain.regions:
        raise BmcBuildError("the region relation needs a model with regions.")
    frame_domain = _relation_frame_domain(prepared)
    symbols = BmcTraceSymbols.allocate(prepared.domain)
    units = _Units(prepared.domain)
    groups: List[BmcTrackedConstraint] = []
    generated_ref = prepared._source_registry.reference("generated", None, None)
    domain = prepared.domain

    steps = []
    region_steps = []
    for step_index in range(domain.bound):
        builder = _build_step(prepared, symbols, units, frame_domain, step_index)
        delta_constraint, gamma_constraint, mutex = builder.finish()
        formula = _and(
            tuple(builder.constraints) + (delta_constraint, gamma_constraint, mutex)
        )
        steps.append(
            BmcStepRelation(
                step_index,
                (),
                (),
                formula,
                delta_constraint,
                gamma_constraint,
                mutex,
            )
        )
        region_steps.append(
            RegionStepRelation(
                step_index,
                tuple(builder.cases),
                tuple(builder.constraints),
                tuple(builder.flushes),
                _or(builder.rollback_terms),
                PositionSnapshot(
                    symbols.frame_state(step_index),
                    {
                        region.path: symbols.region_position(step_index, region.path)
                        for region in domain.regions
                    },
                ),
                tuple(
                    (owner, tuple(region.path for region in _regions_of(domain, owner)))
                    for owner in sorted({item.owner_path for item in domain.regions})
                ),
                tuple((entry.path, entry.id) for entry in domain.states),
            )
        )

    start = prepared.bound_query.initial.resolved_start
    start_ids = None if start is None else start_position_ids(domain, start)
    domain_start = len(groups)
    _build_domain_formula(symbols, frame_domain, groups, lambda: generated_ref)
    for frame_index in range(domain.bound + 1):
        _append_tracked_group(
            groups,
            stable_id="domain.frame.%04d.regions" % frame_index,
            stage="kernel",
            category="domain.frame_state",
            expressions=region_frame_constraints(symbols, frame_index, start_ids),
            source_ref=generated_ref,
            refs={"frame": frame_index, "kind": "regions"},
        )
    domain_formula = _formula_from_groups(groups[domain_start:])

    initial_start = len(groups)
    initial_error_sites: list = []
    _build_initial_formula(prepared, symbols, groups, initial_error_sites)
    if start_ids is not None and start_ids[1]:
        _append_tracked_group(
            groups,
            stable_id="initial.positions",
            stage="initialization",
            category="initial.target",
            expressions=tuple(
                symbols.region_position(0, path) == z3.IntVal(value)
                for path, value in sorted(start_ids[1].items())
            ),
            source_ref=prepared._source_registry.query_reference(
                prepared.query, prepared.query.initial
            ),
            refs={"frame": 0, "target": start_ids[0]},
        )
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
        steps=tuple(steps),
        diagnostics=("slicing_skipped:regions",),
        cone_slice=None,
        _tracked_groups=tuple(groups),
        _tracked_case_groups=(),
        _initial_error_sites=tuple(initial_error_sites),
        region_steps=tuple(region_steps),
    )


__all__ = [
    "RegionCaseRelation",
    "RegionFlushRelation",
    "PositionSnapshot",
    "RegionOccurrence",
    "RegionStepRelation",
    "region_error_analysis",
    "region_occurrences",
    "reported_call_state",
    "region_frame_constraints",
    "build_region_core_formula",
]

"""Region-aware macro-step expansion for FCSTM bounded model checking.

A state that owns regions advances its regions one after another in one cycle,
each region on the values the previous one left behind.  One flat list of
macro-step cases per *machine* would need a case for every combination of the
paths of all regions, which grows with the product of the regions.  This module
therefore expands one *unit* at a time and leaves the gluing to
:mod:`pyfcstm.bmc.region_relation`:

* a ``work`` unit is one stable leaf, in the main namespace or inside a region,
  and every path one cycle can take from it;
* an ``init`` unit is one region that is being initialized, which happens when a
  state that owns regions is entered;
* a ``cont`` unit is a state that owns regions after every region finished, and
  the transitions that continue from it;
* a ``cold`` unit is the cold start of the whole machine.

A unit ends where the single-path expander would also have to stop, and in
three more places: a path that enters a state owning regions stops there (the
regions are initialized by ``init`` units), and a path that leaves a region
through ``[*]`` stops with a *done* result.  Those two results carry an atom
(:data:`ATOM_REGION_ENTER`, :data:`ATOM_REGION_DONE`) that stands for "the rest
of the cycle can still be completed from here"; the relation layer decides it
from the values the path left behind, exactly as the runtime validates a
candidate before committing to it.

The module contains:

* :class:`RegionCase` - One flat path of a unit.
* :class:`RegionUnitFormal` - All paths of one unit.
* :func:`expand_leaf_unit`, :func:`expand_init_unit`,
  :func:`expand_continue_unit`, :func:`expand_cold_unit` - Unit expanders.

Example::

    >>> from pyfcstm.bmc.domain import build_bmc_domain
    >>> from pyfcstm.bmc.region_expand import expand_leaf_unit
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... def int x = 0;
    ... state Root {
    ...     region A { [*] -> P; state P { during { x = x + 1; } } }
    ...     region B { [*] -> Q; state Q; }
    ... }
    ... ''')
    >>> unit = expand_leaf_unit(build_bmc_domain(model, 1), 'Root.A.P')
    >>> [case.kind for case in unit.cases]
    ['fallback']
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

from .domain import REGION_DONE_ID, STATE_INIT_ID, BmcDomain
from .errors import BmcBuildError, InvalidBmcDomain, InvalidBmcEncoding
from .expand import (
    _CASE_KIND_INITIAL,
    _CASE_KIND_TRANSITION,
    _Expansion,
    _FormalStackFrame,
    _MacroExpander,
    _MacroFrontier,
    _MacroOutcome,
    MacroExpansionOptions,
)
from .macro import (
    ActionBlock,
    BoolTemplate,
    EventUse,
    GuardRequirement,
    PriorityExclusion,
)
from .source import INIT_CASE_PATH, TERMINATE_CASE_PATH
from pyfcstm.model import State, Transition
from pyfcstm.model.region import Region

ATOM_REGION_DONE = "region:done"
ATOM_REGION_ENTER = "region:enter"
REGION_DONE_CASE_PATH = "__region_done__"
_OWNER_ENTERED_MODE = "owner_entered"


@dataclass(frozen=True)
class RegionCase:
    """One flat path of a unit before solver lowering.

    :param kind: ``"transition"``, ``"fallback"`` or ``"initial"``.
    :type kind: str
    :param label: Case label that is unique among all units of a domain.
    :type label: str
    :param unit_id: Identifier of the unit this path belongs to.
    :type unit_id: str
    :param target_kind: ``"leaf"`` when the path ends on a stable leaf,
        ``"owner"`` when it enters a state that owns regions, ``"done"`` when
        the region finished, ``"terminate"`` when the machine ended.
    :type target_kind: str
    :param target_state_id: Id of the leaf or of the owner for the first two
        target kinds, a sentinel id otherwise.
    :type target_state_id: int
    :param target_state_path: Path of the target, or a reserved path.
    :type target_state_path: str
    :param condition: Control-path condition over event, guard, accepted and
        region atoms.
    :type condition: pyfcstm.bmc.macro.BoolTemplate
    :param action_blocks: Action blocks the path executes, in order.
    :type action_blocks: Tuple[pyfcstm.bmc.macro.ActionBlock, ...]
    :param used_events: Event inputs the path reads.
    :type used_events: Tuple[pyfcstm.bmc.macro.EventUse, ...]
    :param guard_requirements: Guards the path evaluates.
    :type guard_requirements: Tuple[pyfcstm.bmc.macro.GuardRequirement, ...]
    :param priority_exclusions: Priority masks the path applies.
    :type priority_exclusions: Tuple[pyfcstm.bmc.macro.PriorityExclusion, ...]
    :param consumed_events: Event paths consumed by executed transitions.
    :type consumed_events: Tuple[str, ...]

    Example::

        >>> from pyfcstm.bmc.macro import BoolTemplate
        >>> case = RegionCase('fallback', 'u::fallback::P::0', 'u', 'leaf', 3, 'Root.A.P',
        ...                   BoolTemplate.true(), (), (), (), (), ())
        >>> case.target_kind
        'leaf'
    """

    kind: str
    label: str
    unit_id: str
    target_kind: str
    target_state_id: int
    target_state_path: str
    condition: BoolTemplate
    action_blocks: Tuple[ActionBlock, ...]
    used_events: Tuple[EventUse, ...]
    guard_requirements: Tuple[GuardRequirement, ...]
    priority_exclusions: Tuple[PriorityExclusion, ...]
    consumed_events: Tuple[str, ...]
    failed_conditions: Tuple[BoolTemplate, ...] = ()


@dataclass(frozen=True)
class RegionUnitFormal:
    """All flat paths of one unit.

    :param unit_id: Identifier of the unit, for example ``"work:Root.A.P"``.
    :type unit_id: str
    :param kind: ``"work"``, ``"init"``, ``"cont"`` or ``"cold"``.
    :type kind: str
    :param cases: Success paths of the unit.
    :type cases: Tuple[RegionCase, ...]
    :param failed: Conditions under which a candidate was tried and rejected;
        diagnostic only.
    :type failed: Tuple[pyfcstm.bmc.macro.BoolTemplate, ...]

    Example::

        >>> RegionUnitFormal('work:Root.P', 'work', (), ()).kind
        'work'
    """

    unit_id: str
    kind: str
    cases: Tuple[RegionCase, ...]
    failed: Tuple[BoolTemplate, ...] = ()


@dataclass(frozen=True)
class _UnitSource:
    """Duck-typed source that the shared expander base class reads."""

    kind: str
    source_state_id: int
    source_state_path: str
    domain: BmcDomain
    allows_semantic_delta: bool = False
    uses_stable_fallback: bool = False


class _RegionExpander(_MacroExpander):
    """Single-path expander extended with regions as stack frames."""

    def __init__(self, source: _UnitSource, options: MacroExpansionOptions) -> None:
        super().__init__(source, options)  # type: ignore[arg-type]
        self._region_paths = {region.path: region for region in self.domain.regions}
        self._owner_by_region_path = {
            region.path: region.owner_path for region in self.domain.regions
        }

    # ------------------------------------------------------------------
    # frontier construction
    # ------------------------------------------------------------------
    def region_of(self, path: str) -> Region:
        """Return the model region at ``path``."""
        owner_path = self._owner_by_region_path[path]
        owner = self.states_by_path[owner_path]
        return owner.regions[path.rsplit(".", 1)[1]]

    def namespace_frames(self, leaf: State) -> Tuple[_FormalStackFrame, ...]:
        """Return the frames from the namespace root down to ``leaf``.

        The namespace root is the region the leaf sits in, or the machine root
        for a leaf outside every region.  Frames above a region belong to other
        units and are not part of this unit's stack.
        """
        chain = []
        current = leaf
        region = None
        while current is not None:
            chain.append(_FormalStackFrame(current, "active"))
            parent = current.parent
            if isinstance(parent, Region):
                region = parent
                break
            current = parent
        chain.reverse()
        if region is not None:
            chain.insert(0, _FormalStackFrame(region, "active"))
        return tuple(chain)

    def owner_frames(self, owner: State) -> Tuple[_FormalStackFrame, ...]:
        """Return the frames down to a state that owns regions and finished them."""
        frames = list(self.namespace_frames(owner))
        frames[-1] = _FormalStackFrame(owner, "post_child_exit")
        return tuple(frames)

    # ------------------------------------------------------------------
    # overridden single-path pieces
    # ------------------------------------------------------------------
    def _state_id(self, path: str) -> int:
        owner_path = self._owner_by_region_path.get(path)
        if owner_path is not None:
            # A region has no state id; blocks that belong to a region name its
            # owner, which is the closest state the domain knows.
            return super()._state_id(owner_path)
        return super()._state_id(path)

    @staticmethod
    def _transition_index(owner, transition: Transition) -> int:
        candidates = [owner.init_transitions]
        if hasattr(owner, "transitions_from"):
            candidates.append(owner.transitions_from)
        for transitions in candidates:
            for index, item in enumerate(transitions):
                if item is transition:
                    return index
        raise BmcBuildError(
            "transition object was not found on its owner state or region."
        )

    def _active_leaf_path(
        self, frontier: _MacroFrontier, runtime_state_path: str
    ) -> str:
        for frame in reversed(frontier.stack):
            state = frame.state
            if (
                not isinstance(state, Region)
                and state.is_leaf_state
                and not state.is_pseudo
            ):
                return ".".join(state.path)
        return runtime_state_path

    def _finalize_exit_to_parent(self, frontier: _MacroFrontier) -> _MacroFrontier:
        if frontier.stack and isinstance(frontier.stack[-1].state, Region):
            # The child left through ``[*]`` directly under a region: the region
            # is done, and it has no ``during after`` action to run.
            return self._replace_top(
                frontier, _FormalStackFrame(frontier.stack[-1].state, "post_child_exit")
            )
        return super()._finalize_exit_to_parent(frontier)

    def _enter_state(
        self, frontier: _MacroFrontier, state: State
    ) -> Tuple[_MacroFrontier, ...]:
        if not state.regions:
            return super()._enter_state(frontier, state)
        current = self._replace_frontier(
            frontier,
            stack=frontier.stack + (_FormalStackFrame(state, "active"),),
        )
        for on_enter in state.on_enters:
            current = self._record_func(
                current, state, on_enter, "state_action", "state_enter"
            )
        # The regions are started by init units, so the path stops here.
        return (
            self._replace_top(current, _FormalStackFrame(state, _OWNER_ENTERED_MODE)),
        )

    def _expand_frontier(self, frontier: _MacroFrontier) -> _Expansion:
        # The head repeats the single-path expander's safety and loop checks,
        # because a region frame has to be dispatched before the leaf test the
        # base class applies to every top frame.
        if frontier.depth >= self.options.max_micro_steps:
            raise BmcBuildError(
                "macro-step expansion exceeded the micro-step safety limit."
            )
        if len(frontier.stack) > self.options.max_stack_depth:
            raise BmcBuildError(
                "macro-step expansion exceeded the stack-depth safety limit."
            )
        if frontier.condition.kind == "false":
            return _Expansion((), (), ())
        signature = self._frontier_signature(frontier)
        for previous_signature, previous_action_count in frontier.path_signatures:
            if previous_signature != signature:
                continue
            if len(frontier.action_blocks) > previous_action_count:
                raise BmcBuildError(
                    "macro-step expansion encountered an action-dependent pseudo loop."
                )
            self._remember_failed_guard_requirements(frontier)
            return _Expansion((), (frontier.condition,), ())
        frontier = self._replace_frontier(
            frontier,
            path_signatures=frontier.path_signatures
            + ((signature, len(frontier.action_blocks)),),
            depth=frontier.depth + 1,
        )
        if frontier.stack:
            top = frontier.stack[-1]
            if isinstance(top.state, Region):
                if top.mode == "post_child_exit":
                    return _Expansion((self._done_outcome(frontier),), (), ())
                return self._expand_initial_transitions(frontier)
            if top.mode == _OWNER_ENTERED_MODE:
                return _Expansion((self._owner_outcome(frontier, top.state),), (), ())
        return self._dispatch_frontier(frontier)

    def _dispatch_frontier(self, frontier: _MacroFrontier) -> _Expansion:
        """Dispatch a frontier on its top frame the way the base class does."""
        if not frontier.stack:
            return _Expansion((self._terminate_outcome(frontier),), (), ())
        top = frontier.stack[-1]
        state = top.state
        if state.is_leaf_state and top.mode == "after_entry":
            active = self._replace_top(frontier, _FormalStackFrame(state, "active"))
            if state.is_stoppable:
                return _Expansion((self._stable_outcome(active, state),), (), ())
            return self._expand_frontier(active)
        if state.is_leaf_state:
            return self._expand_leaf_active(frontier)
        if top.mode == "init_wait":
            return self._expand_initial_transitions(frontier)
        if top.mode == "post_child_exit":
            return self._expand_parent_continuation(frontier)
        raise BmcBuildError(
            "unsupported macro frontier stack frame mode: %r." % top.mode
        )

    # ------------------------------------------------------------------
    # outcomes
    # ------------------------------------------------------------------
    def _done_outcome(self, frontier: _MacroFrontier) -> _MacroOutcome:
        return _MacroOutcome(
            self._allocate_case_label(frontier.case_kind, REGION_DONE_CASE_PATH),
            REGION_DONE_ID,
            REGION_DONE_CASE_PATH,
            BoolTemplate.and_(frontier.condition, BoolTemplate.atom(ATOM_REGION_DONE)),
            frontier.used_events,
            frontier.action_blocks,
            frontier.guard_requirements,
            frontier.priority_exclusions,
            frontier.case_kind,
            consumed_events=frontier.consumed_events,
        )

    def _owner_outcome(self, frontier: _MacroFrontier, owner: State) -> _MacroOutcome:
        path = ".".join(owner.path)
        return _MacroOutcome(
            self._allocate_case_label(frontier.case_kind, path),
            self._state_id(path),
            path,
            BoolTemplate.and_(frontier.condition, BoolTemplate.atom(ATOM_REGION_ENTER)),
            frontier.used_events,
            frontier.action_blocks,
            frontier.guard_requirements,
            frontier.priority_exclusions,
            frontier.case_kind,
            consumed_events=frontier.consumed_events,
        )

    def classify_target(self, outcome: _MacroOutcome) -> str:
        """Return the target kind of an outcome."""
        if outcome.target_state_path == TERMINATE_CASE_PATH:
            return "terminate"
        if outcome.target_state_path == REGION_DONE_CASE_PATH:
            return "done"
        entry = self.domain.state_by_id(outcome.target_state_id)
        return "owner" if entry.owns_regions else "leaf"

    # ------------------------------------------------------------------
    # unit expansion
    # ------------------------------------------------------------------
    def expand_unit(self, unit_id: str, unit_kind: str, frontiers) -> RegionUnitFormal:
        """Expand the given start frontiers into the cases of one unit."""
        expansion = self._merge_expansions(
            self._expand_frontier(frontier) for frontier in frontiers
        )
        cases = tuple(
            RegionCase(
                outcome.case_kind,
                outcome.label,
                unit_id,
                self.classify_target(outcome),
                outcome.target_state_id,
                outcome.target_state_path,
                outcome.condition,
                outcome.action_blocks,
                outcome.used_events,
                outcome.guard_requirements,
                outcome.priority_exclusions,
                outcome.consumed_events,
                outcome.failed_conditions,
            )
            for outcome in expansion.outcomes
        )
        return RegionUnitFormal(unit_id, unit_kind, cases, expansion.failed)


def _base_frontier(case_kind: str) -> _MacroFrontier:
    return _MacroFrontier(
        (),
        BoolTemplate.true(),
        (),
        (),
        (),
        (),
        case_kind,
    )


def _make_expander(
    domain: BmcDomain,
    unit_id: str,
    kind: str,
    options: Optional[MacroExpansionOptions],
    source_state_id: int,
) -> _RegionExpander:
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    if domain.model is None:
        raise InvalidBmcEncoding("region expansion requires a model-backed domain.")
    options = options or MacroExpansionOptions()
    source = _UnitSource(kind, source_state_id, unit_id, domain)
    return _RegionExpander(source, options)


def _leaf_state(domain: BmcDomain, path: str) -> State:
    try:
        entry = domain.state_by_path(path)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: BmcDomain lookup rejects paths that are not states.
        raise InvalidBmcEncoding(str(err)) from err
    if not entry.is_stoppable:
        raise InvalidBmcEncoding("a work unit starts at a stoppable leaf.")
    model = domain.model
    for state in model.walk_states():
        if ".".join(state.path) == path:
            return state
    raise InvalidBmcEncoding("state %r is not in the model." % path)


def expand_leaf_unit(
    domain: BmcDomain,
    leaf_path: str,
    options: Optional[MacroExpansionOptions] = None,
) -> RegionUnitFormal:
    """Expand every path one cycle can take from a stable leaf.

    The leaf may sit in the main namespace or inside a region.  For a leaf in a
    region the stack holds that region's states only: what happens above the
    region belongs to other units.

    :param domain: Region-aware domain of the model.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param leaf_path: Dot-separated path of a stoppable leaf.
    :type leaf_path: str
    :param options: Expansion safety options, defaults to ``None``.
    :type options: pyfcstm.bmc.expand.MacroExpansionOptions, optional
    :return: The paths of the unit.
    :rtype: RegionUnitFormal
    :raises pyfcstm.bmc.errors.InvalidBmcEncoding: If ``leaf_path`` is not a
        stoppable leaf of the domain's model.
    :raises pyfcstm.bmc.errors.BmcBuildError: If the expansion cannot be bounded.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; P -> [*]; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> unit = expand_leaf_unit(build_bmc_domain(model, 1), 'Root.A.P')
        >>> sorted(case.target_kind for case in unit.cases)
        ['done', 'leaf']
    """
    leaf = _leaf_state(domain, leaf_path)
    unit_id = "work:%s" % leaf_path
    expander = _make_expander(
        domain, unit_id, "work", options, domain.state_path_to_id(leaf_path)
    )
    frames = expander.namespace_frames(leaf)
    frontier = _MacroFrontier(
        frames, BoolTemplate.true(), (), (), (), (), _CASE_KIND_TRANSITION
    )
    return expander.expand_unit(unit_id, "work", (frontier,))


def expand_init_unit(
    domain: BmcDomain,
    region_path: str,
    options: Optional[MacroExpansionOptions] = None,
) -> RegionUnitFormal:
    """Expand the initialization of one region.

    :param domain: Region-aware domain of the model.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param region_path: Dot-separated path of a region.
    :type region_path: str
    :param options: Expansion safety options, defaults to ``None``.
    :type options: pyfcstm.bmc.expand.MacroExpansionOptions, optional
    :return: The initialization paths of the region.
    :rtype: RegionUnitFormal
    :raises pyfcstm.bmc.errors.InvalidBmcEncoding: If ``region_path`` is not a
        region of the domain.
    :raises pyfcstm.bmc.errors.BmcBuildError: If the expansion cannot be bounded.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> unit = expand_init_unit(build_bmc_domain(model, 1), 'Root.B')
        >>> [(case.kind, case.target_state_path) for case in unit.cases]
        [('initial', 'Root.B.Q')]
    """
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    entries = {region.path: region for region in domain.regions}
    if region_path not in entries:
        raise InvalidBmcEncoding("region %r is not in the domain." % region_path)
    unit_id = "init:%s" % region_path
    expander = _make_expander(
        domain, unit_id, "init", options, entries[region_path].owner_id
    )
    region = expander.region_of(region_path)
    frontier = _MacroFrontier(
        (_FormalStackFrame(region, "init_wait"),),
        BoolTemplate.true(),
        (),
        (),
        (),
        (),
        _CASE_KIND_INITIAL,
    )
    return expander.expand_unit(unit_id, "init", (frontier,))


def expand_continue_unit(
    domain: BmcDomain,
    owner_path: str,
    options: Optional[MacroExpansionOptions] = None,
) -> RegionUnitFormal:
    """Expand the continuation of a state whose regions all finished.

    The unit starts with the owner's plain ``during after`` actions, which run
    when the group hands control back, and then follows the owner's outgoing
    transitions in declaration order.

    :param domain: Region-aware domain of the model.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param owner_path: Dot-separated path of a state that owns regions.
    :type owner_path: str
    :param options: Expansion safety options, defaults to ``None``.
    :type options: pyfcstm.bmc.expand.MacroExpansionOptions, optional
    :return: The continuation paths of the owner.
    :rtype: RegionUnitFormal
    :raises pyfcstm.bmc.errors.InvalidBmcEncoding: If ``owner_path`` is not a
        region-owning state of the domain.
    :raises pyfcstm.bmc.errors.BmcBuildError: If the expansion cannot be bounded.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     [*] -> Run;
        ...     state Run {
        ...         region A { [*] -> P; state P; P -> [*]; }
        ...         region B { [*] -> Q; state Q; Q -> [*]; }
        ...     }
        ...     state Done;
        ...     Run -> Done;
        ... }
        ... ''')
        >>> unit = expand_continue_unit(build_bmc_domain(model, 1), 'Root.Run')
        >>> [case.target_state_path for case in unit.cases]
        ['Root.Done']
    """
    if not isinstance(domain, BmcDomain):
        raise InvalidBmcEncoding("domain must be BmcDomain.")
    try:
        entry = domain.state_by_path(owner_path)
    except InvalidBmcDomain as err:
        # InvalidBmcDomain: BmcDomain lookup rejects paths that are not states.
        raise InvalidBmcEncoding(str(err)) from err
    if not entry.owns_regions:
        raise InvalidBmcEncoding("state %r does not own regions." % owner_path)
    unit_id = "cont:%s" % owner_path
    expander = _make_expander(domain, unit_id, "cont", options, entry.id)
    owner = expander.states_by_path[owner_path]
    frontier = _MacroFrontier(
        expander.owner_frames(owner),
        BoolTemplate.true(),
        (),
        (),
        (),
        (),
        _CASE_KIND_TRANSITION,
    )
    for on_during_after in owner.list_on_durings(aspect="after"):
        frontier = expander._record_func(
            frontier, owner, on_during_after, "state_action", "plain_during_after"
        )
    return expander.expand_unit(unit_id, "cont", (frontier,))


def expand_cold_unit(
    domain: BmcDomain,
    options: Optional[MacroExpansionOptions] = None,
) -> RegionUnitFormal:
    """Expand the cold start of the whole machine.

    :param domain: Region-aware domain of the model.
    :type domain: pyfcstm.bmc.domain.BmcDomain
    :param options: Expansion safety options, defaults to ``None``.
    :type options: pyfcstm.bmc.expand.MacroExpansionOptions, optional
    :return: The paths of the first cycle.
    :rtype: RegionUnitFormal
    :raises pyfcstm.bmc.errors.InvalidBmcEncoding: If the domain has no model.
    :raises pyfcstm.bmc.errors.BmcBuildError: If the expansion cannot be bounded.

    Example::

        >>> from pyfcstm.bmc.domain import build_bmc_domain
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('state Root { [*] -> A; state A; }')
        >>> unit = expand_cold_unit(build_bmc_domain(model, 1))
        >>> [(case.kind, case.target_state_path) for case in unit.cases]
        [('initial', 'Root.A')]
    """
    unit_id = INIT_CASE_PATH
    expander = _make_expander(domain, unit_id, "cold", options, STATE_INIT_ID)
    frontiers = expander._enter_state(
        _base_frontier(_CASE_KIND_INITIAL), expander.model.root_state
    )
    return expander.expand_unit(unit_id, "cold", frontiers)


__all__ = [
    "ATOM_REGION_DONE",
    "ATOM_REGION_ENTER",
    "REGION_DONE_CASE_PATH",
    "RegionCase",
    "RegionUnitFormal",
    "expand_leaf_unit",
    "expand_init_unit",
    "expand_continue_unit",
    "expand_cold_unit",
]

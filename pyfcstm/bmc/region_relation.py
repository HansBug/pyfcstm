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
  frame can hold a region at a position its owner does not allow.

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
from typing import Dict, List, Mapping, Optional, Tuple

import z3

from .domain import (
    REGION_DONE_ID,
    REGION_INACTIVE_ID,
    STATE_INIT_ID,
    STATE_TERMINATE_ID,
    BmcDomain,
    RegionDomainEntry,
)
from .engine import BmcPreparedContext
from .errors import BmcBuildError, UnsupportedBmcQuery
from .region_expand import (
    ATOM_REGION_DONE,
    ATOM_REGION_ENTER,
    RegionCase,
    RegionUnitFormal,
    expand_cold_unit,
    expand_continue_unit,
    expand_init_unit,
    expand_leaf_unit,
)
from .relation import (
    BmcCoreFormula,
    BmcStepRelation,
    BmcTraceSymbols,
    _LoweredBoolTemplate,
    _and,
    _append_tracked_group,
    _build_domain_formula,
    _build_environment_formula,
    _build_initial_formula,
    _expect_arith,
    _formula_from_groups,
    _initial_source,
    _internal_bmc_error,
    _lower_bool_template,
    _or,
    _prepare_case_lowering,
    _relation_frame_domain,
    _require_context,
    _translate_model_expr,
)
from pyfcstm.dsl.role import VariableRole
from .provenance import BmcTrackedConstraint
from pyfcstm.solver.domain import DomainConstraint

# How many times one owner may be entered inside the entry of itself before the
# build gives up.  A group that re-enters itself keeps going until a value stops
# it, so the depth depends on data; past this depth the formula would no longer
# describe the runtime, and the build fails instead of guessing.
GROUP_REENTRY_LIMIT = 16
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

    Example::

        >>> import z3
        >>> from pyfcstm.bmc.macro import BoolTemplate
        >>> from pyfcstm.bmc.region_expand import RegionCase
        >>> case = RegionCase('fallback', 'u::fallback::P::0', 'u', 'leaf', 3, 'Root.P',
        ...                   BoolTemplate.true(), (), (), (), (), ())
        >>> t = z3.BoolVal(True)
        >>> RegionCaseRelation(0, case, t, t, t, t).case.kind
        'fallback'
    """

    step_index: int
    case: RegionCase
    selector: z3.BoolRef
    antecedent: z3.BoolRef
    consequent: z3.BoolRef
    implication: z3.BoolRef


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

    Example::

        >>> RegionStepRelation(0, (), ()).step_index
        0
    """

    step_index: int
    cases: Tuple[RegionCaseRelation, ...]
    constraints: Tuple[z3.BoolRef, ...]


@dataclass(frozen=True)
class _Namespace:
    """Where a unit runs: the main namespace or inside one region of an owner."""

    region: Optional[RegionDomainEntry]
    others_live: Optional[z3.BoolRef]
    parent: Optional["_Namespace"]


@dataclass
class _UnitResult:
    ok: z3.BoolRef
    facts: List[_Fact] = field(default_factory=list)
    defs: List[Tuple[z3.BoolRef, DomainConstraint]] = field(default_factory=list)
    fallback: z3.BoolRef = field(default_factory=lambda: z3.BoolVal(False))


@dataclass
class _Entry:
    ok: z3.BoolRef
    out_pos: z3.ArithRef
    env_out: _Env
    facts: List[_Fact]
    defs: List[Tuple[z3.BoolRef, DomainConstraint]]


class _Units:
    """Lazily expanded units of one build, keyed by what they start from."""

    def __init__(self, domain: BmcDomain) -> None:
        self._domain = domain
        self._leaf: Dict[str, RegionUnitFormal] = {}
        self._init: Dict[str, RegionUnitFormal] = {}
        self._cont: Dict[str, RegionUnitFormal] = {}
        self._cold: Optional[RegionUnitFormal] = None

    def leaf(self, path: str) -> RegionUnitFormal:
        if path not in self._leaf:
            self._leaf[path] = expand_leaf_unit(self._domain, path)
        return self._leaf[path]

    def init(self, region_path: str) -> RegionUnitFormal:
        if region_path not in self._init:
            self._init[region_path] = expand_init_unit(self._domain, region_path)
        return self._init[region_path]

    def cont(self, owner_path: str) -> RegionUnitFormal:
        if owner_path not in self._cont:
            self._cont[owner_path] = expand_continue_unit(self._domain, owner_path)
        return self._cont[owner_path]

    def cold(self) -> RegionUnitFormal:
        if self._cold is None:
            self._cold = expand_cold_unit(self._domain)
        return self._cold


def _regions_of(domain: BmcDomain, owner_path: str) -> Tuple[RegionDomainEntry, ...]:
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


def _in_region(domain: BmcDomain, path: str) -> bool:
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


def region_frame_constraints(
    symbols: BmcTraceSymbols, frame_index: int
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
            allowed = _or(
                position == z3.IntVal(item)
                for item in tuple(region.position_state_ids) + (REGION_DONE_ID,)
            )
            constraints.append(z3.Implies(resting, allowed))
            constraints.append(
                z3.Implies(
                    z3.Not(resting), position == z3.IntVal(REGION_INACTIVE_ID)
                )
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
    return tuple(constraints)


class _StepBuilder:
    """Lowers one step of a model with regions."""

    def __init__(
        self,
        prepared: BmcPreparedContext,
        symbols: BmcTraceSymbols,
        units: _Units,
        step_index: int,
    ) -> None:
        self.prepared = prepared
        self.symbols = symbols
        self.units = units
        self.step = step_index
        self.domain = prepared.domain
        self.persistent = tuple(self.domain.persistent_variable_names)
        frame_vars = symbols.frame_vars[step_index]
        self.int_names = tuple(
            name for name in self.persistent if z3.is_int(frame_vars[name])
        )
        self.constraints: List[z3.BoolRef] = []
        self.cases: List[RegionCaseRelation] = []
        self.delta_terms: List[z3.BoolRef] = []
        self.gamma_terms: List[z3.BoolRef] = []
        self._counter = 0
        # Owners whose entry is being decided, with the values they were
        # entered on: re-entering one on the very same values is the loop the
        # runtime reports, and re-entering on other values may still end.
        self._entering: List[Tuple[str, _Env]] = []

    # ------------------------------------------------------------------
    # symbols
    # ------------------------------------------------------------------
    def fresh_int(self, tag: str) -> z3.ArithRef:
        self._counter += 1
        return z3.Int("R_%d_%d_%s" % (self.step, self._counter, tag))

    def fresh_env(self, tag: str) -> _Env:
        self._counter += 1
        frame_vars = self.symbols.frame_vars[self.step]
        return {
            name: (z3.Int if z3.is_int(frame_vars[name]) else z3.Real)(
                "R_%d_%d_%s_%s" % (self.step, self._counter, tag, name)
            )
            for name in self.persistent
        }

    def env_equal(self, left: Mapping[str, z3.ArithRef], right: Mapping[str, z3.ArithRef]) -> z3.BoolRef:
        return _and(left[name] == right[name] for name in self.persistent)

    def persistent_env(self, env: Mapping[str, object]) -> _Env:
        return {
            name: _expect_arith(env[name], "variable %s" % name)
            for name in self.persistent
        }

    def pre_env(self, env: Mapping[str, z3.ArithRef]) -> Dict[str, object]:
        merged: Dict[str, object] = dict(env)
        merged.update(self.symbols.step_inputs[self.step])
        merged.update(self.symbols.parameters)
        return merged

    def resting_next(self, owner_path: str) -> z3.BoolRef:
        return _owner_resting(self.symbols, self.domain, self.step + 1, owner_path)

    def position_in(self, region: RegionDomainEntry) -> z3.ArithRef:
        return self.symbols.region_position(self.step, region.path)

    def position_next(self, region: RegionDomainEntry) -> z3.ArithRef:
        return self.symbols.region_position(self.step + 1, region.path)

    # ------------------------------------------------------------------
    # one unit
    # ------------------------------------------------------------------
    def lower_unit(
        self,
        unit: RegionUnitFormal,
        gate: z3.BoolRef,
        env_in: _Env,
        ns: Optional[_Namespace],
        tag: str,
        outputs: Optional[Tuple[z3.ArithRef, _Env]],
        record: bool,
    ) -> _UnitResult:
        """Lower the paths of a unit that starts under ``gate`` on ``env_in``.

        ``outputs`` is the position symbol and the variable symbols the selected
        path writes; with ``None`` the unit is only asked whether it can
        succeed.  ``record`` keeps the lowered paths for inspection, which only
        the paths that really run in the step want.
        """
        pre_env = self.pre_env(env_in)
        prepared_cases = []
        for case in unit.cases:
            lowering = _prepare_case_lowering(
                case, pre_env, self.persistent, None, self.int_names
            )
            final_env = self.persistent_env(lowering.final_env)
            entry = None
            terms: Dict[str, z3.BoolRef] = {}
            case_tag = "%s_%s" % (tag, len(prepared_cases))
            if _statically_false(case.condition, lowering.guard_terms):
                # A guard on the path is already false on these values, so the
                # path is dead and what follows it is never built.
                terms[ATOM_REGION_ENTER] = z3.BoolVal(False)
                terms[ATOM_REGION_DONE] = z3.BoolVal(False)
            elif case.target_kind == "owner":
                entry = self.entry(case.target_state_path, final_env, ns, case_tag)
                terms[ATOM_REGION_ENTER] = entry.ok
            elif case.target_kind == "done":
                terms[ATOM_REGION_DONE] = self.done_viable(ns, final_env, case_tag)
            prepared_cases.append(
                (case, replace(lowering, region_terms=terms), final_env, entry)
            )

        lowerings = {case.label: item for case, item, _, _ in prepared_cases}
        condition_cache: Dict[str, _LoweredBoolTemplate] = {}
        accepted_cache: Dict[str, _LoweredBoolTemplate] = {}

        def accepted_lookup(label, active):
            if label not in accepted_cache:
                accepted_cache[label] = _LoweredBoolTemplate(
                    _and((gate, condition_for(label, active).expr))
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
            parts.append(self.env_equal(env_out, source_env))
            result.defs.extend(
                (antecedent, item) for item in definedness
            )
            if entry is not None:
                result.defs.extend(
                    (z3.And(antecedent, cond), item) for cond, item in entry.defs
                )
            if record:
                parts.extend(
                    z3.Implies(antecedent, item.constraint)
                    for item in definedness
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
                self.cases.append(
                    RegionCaseRelation(
                        self.step, case, selector, antecedent, consequent, implication
                    )
                )
        result.ok = _or(antecedents)
        result.fallback = _or(fallback)
        return result

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
                entered_env[name].eq(env_in[name]) for name in self.persistent
            ):
                # Same owner on the same values: nothing can change, so this
                # path is the loop the runtime rejects.
                return _Entry(z3.BoolVal(False), out_pos, env_out, [], [])
        if sum(1 for entered, _ in self._entering if entered == owner_path) >= (
            GROUP_REENTRY_LIMIT
        ):
            raise BmcBuildError(
                "state %r re-enters its own group more than %d times inside one "
                "cycle, so the relation cannot be bounded."
                % (owner_path, GROUP_REENTRY_LIMIT)
            )
        self._entering.append((owner_path, env_in))
        try:
            regions = _regions_of(self.domain, owner_path)
            env = env_in
            positions: Dict[str, z3.ArithRef] = {}
            ok_terms: List[z3.BoolRef] = []
            facts: List[_Fact] = []
            defs: List[Tuple[z3.BoolRef, DomainConstraint]] = []
            nested_facts: List[_Fact] = []
            for index, region in enumerate(regions):
                position = self.fresh_int("%s_r%d" % (tag, index))
                unit = self.units.init(region.path)
                # A unit that assigns nothing leaves the values as they are, so
                # they keep their expressions and a loop stays recognizable.
                env_next = (
                    env if _assigns_nothing(unit) else self.fresh_env("%s_r%d" % (tag, index))
                )
                others_live = _or(
                    [z3.BoolVal(index < len(regions) - 1)]
                    + [
                        positions[item.path] != z3.IntVal(REGION_DONE_ID)
                        for item in regions[:index]
                    ]
                )
                region_ns = _Namespace(region, others_live, ns)
                result = self.lower_unit(
                    unit,
                    z3.BoolVal(True),
                    env,
                    region_ns,
                    "%s_r%d" % (tag, index),
                    (position, env_next),
                    record=False,
                )
                ok_terms.append(result.ok)
                nested_facts.extend(result.facts)
                defs.extend(result.defs)
                positions[region.path] = position
                env = env_next
            if z3.is_false(z3.simplify(_and(ok_terms))):
                # A region cannot start on these values, so the whole entry
                # fails and what follows an entry is never reached.
                return _Entry(z3.BoolVal(False), out_pos, env_out, [], [])
            all_done = _and(
                positions[item.path] == z3.IntVal(REGION_DONE_ID) for item in regions
            )
            self.constraints.append(
                z3.Implies(
                    z3.Not(all_done),
                    z3.And(
                        out_pos == z3.IntVal(owner.id), self.env_equal(env_out, env)
                    ),
                )
            )
            cont = self.lower_unit(
                self.units.cont(owner_path),
                all_done,
                env,
                ns,
                "%s_c" % tag,
                (out_pos, env_out),
                record=False,
            )
            resting = out_pos == z3.IntVal(owner.id)
            for region in regions:
                facts.append((resting, self.position_next(region), positions[region.path]))
            facts.extend(
                (z3.And(resting, cond), sym, value) for cond, sym, value in nested_facts
            )
            facts.extend(cont.facts)
            defs.extend(cont.defs)
            ok = z3.And(_and(ok_terms), z3.Or(z3.Not(all_done), cont.ok))
            return _Entry(ok, out_pos, env_out, facts, defs)
        finally:
            self._entering.pop()

    def done_viable(
        self, ns: Optional[_Namespace], env: _Env, tag: str
    ) -> z3.BoolRef:
        """Return whether a region that just finished may stay finished."""
        if ns is None or ns.region is None:
            raise _internal_bmc_error("a region finished outside every region.")
        region = ns.region
        cont = self.lower_unit(
            self.units.cont(region.owner_path),
            z3.BoolVal(True),
            env,
            ns.parent,
            "%s_v" % tag,
            None,
            record=False,
        )
        return z3.Or(ns.others_live, cont.ok)

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
    ):
        """Advance every working region of a resting owner, in order."""
        regions = _regions_of(self.domain, owner_path)
        env = env_in
        after: Dict[str, z3.ArithRef] = {}
        fallback_terms: List[z3.BoolRef] = []
        for index, region in enumerate(regions):
            position_in = self.position_in(region)
            live = z3.And(
                position_in != z3.IntVal(REGION_DONE_ID),
                position_in != z3.IntVal(REGION_INACTIVE_ID),
            )
            q = self.fresh_int("%s_q%d" % (tag, index))
            env_out = self.fresh_env("%s_e%d" % (tag, index))
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
            for position_id in region.position_state_ids:
                entry = self.domain.state_by_id(position_id)
                unit_gate = z3.And(gate, position_in == z3.IntVal(position_id))
                if entry.owns_regions:
                    raise UnsupportedBmcQuery(
                        "a state that owns regions inside a region is not "
                        "supported by the BMC relation yet."
                    )
                result = self.lower_unit(
                    self.units.leaf(entry.path),
                    unit_gate,
                    env,
                    region_ns,
                    "%s_w%d_%d" % (tag, index, position_id),
                    (q, env_out),
                    record=True,
                )
                self.constraints.extend(
                    z3.Implies(cond, sym == value) for cond, sym, value in result.facts
                )
                self.constraints.extend(
                    z3.Implies(cond, item.constraint) for cond, item in []
                )
                region_fallback.append(result.fallback)
            fallback_terms.append(
                z3.Or(z3.Not(z3.And(gate, live)), _or(region_fallback))
            )
            after[region.path] = q
            env = env_out
        all_done = _and(after[item.path] == z3.IntVal(REGION_DONE_ID) for item in regions)
        return env, after, all_done, _and(fallback_terms)

    # ------------------------------------------------------------------
    # sources of a step
    # ------------------------------------------------------------------
    def build_leaf_source(self, state_id: int) -> None:
        entry = self.domain.state_by_id(state_id)
        gate = self.symbols.frame_state(self.step) == z3.IntVal(state_id)
        result = self.lower_unit(
            self.units.leaf(entry.path),
            gate,
            dict(self.symbols.frame_vars[self.step]),
            None,
            "m%d" % state_id,
            (
                self.symbols.frame_state(self.step + 1),
                dict(self.symbols.frame_vars[self.step + 1]),
            ),
            record=True,
        )
        self._emit_facts(result)
        self.gamma_terms.append(z3.And(gate, result.fallback))

    def build_owner_source(self, state_id: int) -> None:
        entry = self.domain.state_by_id(state_id)
        gate = self.symbols.frame_state(self.step) == z3.IntVal(state_id)
        tag = "g%d" % state_id
        env_after, after, all_done, fallback = self.advance_group(
            entry.path,
            gate,
            dict(self.symbols.frame_vars[self.step]),
            None,
            tag,
        )
        next_vars = dict(self.symbols.frame_vars[self.step + 1])
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
        for region in _regions_of(self.domain, entry.path):
            self.constraints.append(
                z3.Implies(
                    z3.And(keep, self.resting_next(entry.path)),
                    self.position_next(region) == after[region.path],
                )
            )
        result = self.lower_unit(
            self.units.cont(entry.path),
            z3.And(gate, all_done),
            env_after,
            None,
            "%s_c" % tag,
            (self.symbols.frame_state(self.step + 1), next_vars),
            record=True,
        )
        self._emit_facts(result)
        self.gamma_terms.append(z3.And(gate, z3.Not(all_done), fallback))

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
        gate = self.symbols.frame_state(self.step) == z3.IntVal(STATE_INIT_ID)
        env_in = (
            self.initial_env()
            if self.step == 0
            else dict(self.symbols.frame_vars[self.step])
        )
        result = self.lower_unit(
            self.units.cold(),
            gate,
            env_in,
            None,
            "cold",
            (
                self.symbols.frame_state(self.step + 1),
                dict(self.symbols.frame_vars[self.step + 1]),
            ),
            record=True,
        )
        self._emit_facts(result)
        delta = z3.And(gate, z3.Not(result.ok))
        self.delta_terms.append(delta)
        self.constraints.append(
            z3.Implies(
                delta,
                z3.And(
                    self.symbols.frame_state(self.step + 1) == z3.IntVal(STATE_INIT_ID),
                    self.env_equal(
                        dict(self.symbols.frame_vars[self.step + 1]),
                        dict(self.symbols.frame_vars[self.step]),
                    ),
                ),
            )
        )

    def build_absorb_source(self) -> None:
        gate = self.symbols.frame_state(self.step) == z3.IntVal(STATE_TERMINATE_ID)
        self.constraints.append(
            z3.Implies(
                gate,
                z3.And(
                    self.symbols.frame_state(self.step + 1)
                    == z3.IntVal(STATE_TERMINATE_ID),
                    self.env_equal(
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

    def _emit_facts(self, result: _UnitResult) -> None:
        self.constraints.extend(
            z3.Implies(cond, sym == value) for cond, sym, value in result.facts
        )

    def finish(self) -> Tuple[z3.BoolRef, z3.BoolRef, z3.BoolRef]:
        delta_flag = self.symbols.delta_flag(self.step)
        gamma_flag = self.symbols.gamma_flag(self.step)
        delta_constraint = delta_flag == _or(self.delta_terms)
        gamma_constraint = gamma_flag == _or(self.gamma_terms)
        mutex = z3.Not(z3.And(delta_flag, gamma_flag))
        return delta_constraint, gamma_constraint, mutex


def _statically_false(template, guard_terms: Mapping[str, z3.BoolRef]) -> bool:
    """Return whether a path condition is false whatever the other atoms are.

    Guards that have already been decided on the values at hand are used; every
    other atom is unknown.
    """

    def truth(node) -> Optional[bool]:
        if node.kind == "true":
            return True
        if node.kind == "false":
            return False
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
        if any(item is True for item in values):
            return True
        return False if all(item is False for item in values) else None

    return truth(template) is False


def _assigns_nothing(unit: RegionUnitFormal) -> bool:
    """Return whether no path of the unit executes an operation."""
    return not any(
        block.operations for case in unit.cases for block in case.action_blocks
    )


def _symbol(tag: str, label: str) -> str:
    from .relation import _safe_symbol_fragment

    return _safe_symbol_fragment("%s::%s" % (tag, label))


def _check_supported(prepared: BmcPreparedContext) -> None:
    model = prepared.model
    for state in model.walk_states():
        owner_scopes = [state]
        for scope in owner_scopes:
            if scope.list_on_during_aspects(aspect=None):
                raise UnsupportedBmcQuery(
                    "'>> during' aspects in a model with regions are not "
                    "supported by the BMC relation yet."
                )
    for region in prepared.domain.regions:
        owner = prepared.domain.model
        del owner
    for state in model.walk_states():
        if state.regions and state.list_on_durings(aspect="before"):
            raise UnsupportedBmcQuery(
                "a plain 'during before' on a state that owns regions is not "
                "supported by the BMC relation yet."
            )
    if prepared.bound_query.initial.mode == "state":
        raise UnsupportedBmcQuery(
            "a hot start of a model with regions is not supported by the BMC "
            "relation yet."
        )


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
    _check_supported(prepared)
    frame_domain = _relation_frame_domain(prepared)
    symbols = BmcTraceSymbols.allocate(prepared.domain)
    units = _Units(prepared.domain)
    groups: List[BmcTrackedConstraint] = []
    generated_ref = prepared._source_registry.reference("generated", None, None)
    domain = prepared.domain

    steps = []
    region_steps = []
    for step_index in range(domain.bound):
        builder = _StepBuilder(prepared, symbols, units, step_index)
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
                    builder.build_owner_source(state_id)
            elif not _in_region(domain, domain.state_by_id(state_id).path):
                builder.build_leaf_source(state_id)
        delta_constraint, gamma_constraint, mutex = builder.finish()
        formula = _and(
            tuple(builder.constraints)
            + (delta_constraint, gamma_constraint, mutex)
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
                step_index, tuple(builder.cases), tuple(builder.constraints)
            )
        )

    domain_start = len(groups)
    _build_domain_formula(symbols, frame_domain, groups, lambda: generated_ref)
    for frame_index in range(domain.bound + 1):
        _append_tracked_group(
            groups,
            stable_id="domain.frame.%04d.regions" % frame_index,
            stage="kernel",
            category="domain.frame_state",
            expressions=region_frame_constraints(symbols, frame_index),
            source_ref=generated_ref,
            refs={"frame": frame_index, "kind": "regions"},
        )
    domain_formula = _formula_from_groups(groups[domain_start:])

    initial_start = len(groups)
    initial_error_sites: list = []
    _build_initial_formula(prepared, symbols, groups, initial_error_sites)
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
    "RegionStepRelation",
    "region_frame_constraints",
    "build_region_core_formula",
]

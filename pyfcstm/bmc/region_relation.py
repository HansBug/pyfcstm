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
from typing import Dict, FrozenSet, Iterable, List, Mapping, Optional, Tuple

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
    _guarded_domain_constraints,
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
    """Outcome of lowering a unit.

    :ivar ok: Condition under which one of the paths of the unit applies.
    :ivar facts: Frame position assignments, each guarded by the path that makes it.
    :ivar defs: Definedness requirements of the paths, each guarded by its path.
    :ivar fallback: Condition under which the applying path only ran during actions.
    """

    ok: z3.BoolRef
    facts: List[_Fact] = field(default_factory=list)
    defs: List[Tuple[z3.BoolRef, DomainConstraint]] = field(default_factory=list)
    fallback: z3.BoolRef = field(default_factory=lambda: z3.BoolVal(False))


@dataclass
class _Entry:
    """Outcome of starting the regions of a state that owns regions.

    :ivar ok: Whether the whole group can start, and continue if all regions finished.
    :ivar out_pos: Position of the enclosing namespace after the start.
    :ivar env_out: Values after the start.
    :ivar facts: Frame position assignments of the started regions.
    :ivar defs: Definedness requirements of the start paths.
    """

    ok: z3.BoolRef
    out_pos: z3.ArithRef
    env_out: _Env
    facts: List[_Fact]
    defs: List[Tuple[z3.BoolRef, DomainConstraint]]


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
        """Collect what one step needs: symbols, units, aspect scopes and value slots.

        The values that flow from unit to unit are the persistent variables plus, for
        every scope that declares aspects, a flag for its before actions and a flag for
        its after actions.
        """
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
        self.ledger_keys = tuple(
            ["$b:%s" % path for path in self.before_scopes]
            + ["$o:%s" % path for path in self.after_scopes]
        )
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
            env[key] = z3.Bool(
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
        for prefix, scopes in (("$b:", self.before_scopes), ("$o:", self.after_scopes)):
            for scope in scopes:
                if _under(scope, region_path) or region_path.startswith(scope + "."):
                    touch.add(prefix + scope)
        return self.fresh_env(tag, base, frozenset(touch))

    def start_env(self, frame_vars: Mapping[str, z3.ArithRef]) -> _Env:
        """Return the values at the start of a cycle: no aspect has run yet."""
        env: _Env = dict(frame_vars)
        for key in self.ledger_keys:
            env[key] = z3.BoolVal(False)
        return env

    def env_equal(
        self, left: Mapping[str, z3.ArithRef], right: Mapping[str, z3.ArithRef]
    ) -> z3.BoolRef:
        """Return the constraint that two sets of values agree in every slot, flags included.

        A slot that holds the very same expression on both sides needs no
        constraint, which is what a flag that was handed on unchanged looks like.
        """
        return _and(
            left[name] == right[name]
            for name in self.slots
            if not left[name].eq(right[name])
        )

    def vars_equal(
        self, left: Mapping[str, z3.ArithRef], right: Mapping[str, z3.ArithRef]
    ) -> z3.BoolRef:
        """Return the constraint that two sets of values agree in the persistent variables."""
        return _and(left[name] == right[name] for name in self.persistent)

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
        unit reads and the symbol it writes.
        """
        if not self.has_aspects and pending_io is None:
            return self._lower_variant(
                self.units.get(spec), gate, env_in, ns, tag, outputs, record, None
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
                )
                oks.append(part.ok)
                fallbacks.append(part.fallback)
                merged.facts.extend(part.facts)
                merged.defs.extend(part.defs)
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
    ) -> _UnitResult:
        """Lower the paths of one expansion variant of a unit; see :meth:`lower_unit`.

        ``variant_scopes`` are the scopes whose before flag this variant fixes:
        such a flag is set after a path that ran or found the scope's before
        actions and clear after any other path, while the flag of a scope the
        unit cannot pass keeps the expression it came in with.
        """
        pre_env = self.pre_env(env_in)
        prepared_cases = []
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
            for path in self.after_scopes:
                key = "$o:%s" % path
                final_env[key] = z3.BoolVal(True) if path in case.owed else env_in[key]
            entry = None
            terms: Dict[str, z3.BoolRef] = {}
            nested: Dict[str, Tuple[DomainConstraint, ...]] = {}
            case_tag = "%s_%s" % (tag, len(prepared_cases))
            if _statically_false(case.condition, lowering.guard_terms):
                # A guard on the path is already false on these values, so the
                # path is dead and what follows it is never built.
                terms[ATOM_REGION_ENTER] = z3.BoolVal(False)
                terms[ATOM_REGION_DONE] = z3.BoolVal(False)
            elif case.target_kind == "owner":
                entry = self.entry(case.target_state_path, final_env, ns, case_tag)
                terms[ATOM_REGION_ENTER] = entry.ok
                nested[ATOM_REGION_ENTER] = _implied(entry.defs)
            elif case.target_kind == "done":
                viable, viable_defs = self.done_viable(ns, final_env, case_tag)
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
        for condition in condition_cache.values():
            for item in condition.definedness_constraints:
                result.defs.append((gate, item))
                if record:
                    self.constraints.append(z3.Implies(gate, item.constraint))
        # A path that ends in a group start or in the check that a finished
        # region may stay finished has run its actions before that is decided,
        # so they have to be defined whenever the path got that far, also when
        # the start or the check then turns out to fail.
        for case, lowering, _, _ in prepared_cases:
            decided = (ATOM_REGION_ENTER, ATOM_REGION_DONE)
            if not any(name in lowering.region_terms for name in decided):
                continue
            if any(z3.is_false(lowering.region_terms.get(name)) for name in decided):
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
                if record:
                    self.constraints.append(z3.Implies(reached, item.constraint))
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
            if record:
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
                entered_env[name].eq(env_in[name]) for name in self.slots
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
                result = self.lower_unit(
                    ("init", region.path),
                    z3.BoolVal(True),
                    env,
                    region_ns,
                    "%s_r%d" % (tag, index),
                    (position, env_next),
                    record=False,
                    pending_io=pending_io,
                )
                # A region is only started when the ones before it started.
                reached = _and(ok_terms)
                ok_terms.append(result.ok)
                nested_facts.extend(result.facts)
                defs.extend((_and((reached, cond)), item) for cond, item in result.defs)
                positions[region.path] = position
                # The branch of a region is over: the scopes below it that owe
                # an after action run it now.
                flushed = len(defs)
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
                )
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
            return _Entry(ok, out_pos, env_out, facts, defs)
        finally:
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
        cont = self.lower_unit(
            ("cont", region.owner_path),
            z3.BoolVal(True),
            env,
            ns.parent,
            "%s_v" % tag,
            None,
            record=False,
        )
        alone = z3.Not(ns.others_live)
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
            for position_id in region.position_state_ids:
                entry = self.domain.state_by_id(position_id)
                unit_gate = z3.And(gate, position_in == z3.IntVal(position_id))
                unit_tag = "%s_w%d_%d" % (tag, index, position_id)
                if entry.owns_regions:
                    # The branch rests in a state that owns regions of its own:
                    # its regions advance first, and once they all finished
                    # the state continues inside this region.
                    sub_env, sub_after, sub_done, sub_fallback = self.advance_group(
                        entry.path, unit_gate, env, region_ns, unit_tag
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
            out = self.fresh_env("%s_s%d" % (tag, index), env, frozenset())
            parts = [self.vars_equal(out, self.persistent_env(lowering.final_env))]
            if defs is None:
                parts.extend(
                    item.constraint for item in lowering.definedness_constraints
                )
            else:
                defs.extend((owes, item) for item in lowering.definedness_constraints)
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

    def build_owner_source(self, state_id: int) -> None:
        """Lower the step of a frame that rests in a state that owns regions.

        The regions advance in order; if all finished the continuation of the owner
        runs in the same step, otherwise the owner keeps resting.
        """
        entry = self.domain.state_by_id(state_id)
        gate = self.symbols.frame_state(self.step) == z3.IntVal(state_id)
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

    def _emit_facts(self, result: _UnitResult) -> None:
        """Constrain the frame positions that the paths of a unit assign."""
        self.constraints.extend(
            z3.Implies(cond, sym == value) for cond, sym, value in result.facts
        )

    def finish(self) -> Tuple[z3.BoolRef, z3.BoolRef, z3.BoolRef]:
        """Return the constraints that tie Delta and Gamma of the step to its paths."""
        delta_flag = self.symbols.delta_flag(self.step)
        gamma_flag = self.symbols.gamma_flag(self.step)
        delta_constraint = delta_flag == _or(self.delta_terms)
        gamma_constraint = gamma_flag == _or(self.gamma_terms)
        mutex = z3.Not(z3.And(delta_flag, gamma_flag))
        return delta_constraint, gamma_constraint, mutex


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


def _check_supported(prepared: BmcPreparedContext) -> None:
    """Refuse what the region relation does not support yet.

    :raises UnsupportedBmcQuery: For a hot start of a model with regions.
    """
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

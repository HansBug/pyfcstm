"""Decode what a model with regions did in one cycle of a solved BMC trace.

The core formula of a model with regions (see :mod:`pyfcstm.bmc.region_relation`)
describes a cycle as the paths of several units: a leaf that works, the start of
the regions of a state, the continuation of a state whose regions all finished,
and the settlements of ``>> during after`` actions.  Once the solver found a
model, this module answers what happened in a cycle:

* which paths ran, in the order the runtime runs them;
* which abstract actions were called, with the variables they saw and the
  configuration of the whole machine **at the moment of the call**.

The runtime hands a handler a snapshot of the tree it is executing, so the
snapshot of a call is not the configuration at the end of the cycle: a region
that has not started yet reads ``[init]``, one that finished its branch reads the
state it ended in, and the region that is running reads the state the call is
made in.  The decoder rebuilds that tree by replaying the selected paths in
order: it starts from the positions of the frame the cycle begins in, and every
path moves the position of the region it runs in once it has made its calls.

The module contains:

* :class:`RegionCall` - One abstract action called in a cycle.
* :class:`RegionStepTrace` - The paths and calls of one cycle.
* :class:`RegionStepSummary` - What a cycle did, in the terms of a witness step.
* :func:`trace_region_step` - Decode one cycle of a solved model.
* :func:`summarize_region_step` - Sum up a cycle for a witness step.
* :func:`frame_configuration` - Configuration text of a frame of a solved model.

Example::

    >>> import z3
    >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
    >>> from pyfcstm.bmc.region_witness import trace_region_step
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> model = load_state_machine_from_text('''
    ... state Root {
    ...     region A { [*] -> P; state P { during abstract Work; } }
    ...     region B { [*] -> Q; state Q; }
    ... }
    ... ''')
    >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
    >>> solver = z3.Solver()
    >>> solver.add(core.core)
    >>> solver.check()
    sat
    >>> trace = trace_region_step(core, solver.model(), 0)
    >>> [(call.action_name, call.configuration) for call in trace.calls]
    [('Root.A.P.Work', 'Root{A: P, B: [init]}')]
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Mapping, Optional, Tuple, Union

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
from .errors import BmcBuildError
from .macro import ActionBlock, EventUse, GuardRequirement
from .region_expand import RegionCase
from .region_relation import (
    RegionCaseRelation,
    RegionFlushRelation,
    region_occurrences,
    reported_call_state,
)
from .relation import BmcAbstractCallRecord, BmcCoreFormula
from pyfcstm.model import Configuration

_DONE = "done"
_PENDING = "pending"
_Where = Union[str, None]


@dataclass(frozen=True)
class RegionCall:
    """One abstract action called in a cycle of a model with regions.

    :param action_name: Resolved abstract action name.
    :type action_name: str
    :param stage: Coarse call stage, ``enter``, ``during`` or ``exit``.
    :type stage: str
    :param role: Runtime role that produced the call.
    :type role: str
    :param state: State path the handler reports: the host of the action, or for
        an aspect the deepest state the aspect wraps at that moment.
    :type state: str
    :param active_leaf: Path the handler reports as the active leaf.
    :type active_leaf: str
    :param named_ref: Path of the named ``ref`` action at the call site, or
        ``None``.
    :type named_ref: str, optional
    :param snapshot: Values of the persistent variables at the call.
    :type snapshot: Mapping[str, Union[int, float]]
    :param configuration: Configuration text of the whole machine at the call.
    :type configuration: str

    Example::

        >>> call = RegionCall('Root.A.Work', 'during', 'leaf_during', 'Root.A',
        ...                   'Root.A', None, {'x': 0}, 'Root.A')
        >>> (call.stage, call.configuration)
        ('during', 'Root.A')
    """

    action_name: str
    stage: str
    role: str
    state: str
    active_leaf: str
    named_ref: Optional[str]
    snapshot: Mapping[str, Union[int, float]]
    configuration: str


@dataclass(frozen=True)
class RegionStepSummary:
    """What a cycle of a model with regions did, in the terms of a witness step.

    A cycle is not one case but the paths of every unit that ran, so the things a
    witness step reads off its case, the events its paths use, the events they
    consume and the guards and actions they run, are the union over the paths.
    The summary offers them under the names the single-path code reads, which is
    why :attr:`case` is the summary itself.

    :param step_index: Zero-based cycle.
    :type step_index: int
    :param trace: The paths and abstract calls of the cycle.
    :type trace: RegionStepTrace
    :param local_cases: ``(scope, kind, label)`` of every path that has a public
        label, in execution order.
    :type local_cases: Tuple[Tuple[Optional[str], str, str], ...]
    :param used_events: Event uses of the paths, in execution order.
    :type used_events: Tuple[pyfcstm.bmc.macro.EventUse, ...]
    :param consumed_events: Events the paths consumed, in execution order.
    :type consumed_events: Tuple[str, ...]
    :param guard_requirements: Guards the paths evaluate.
    :type guard_requirements: Tuple[pyfcstm.bmc.macro.GuardRequirement, ...]
    :param action_blocks: Action blocks the paths run.
    :type action_blocks: Tuple[pyfcstm.bmc.macro.ActionBlock, ...]
    :param antecedent: Condition under which every path of the cycle ran.
    :type antecedent: z3.BoolRef

    Example::

        >>> import z3
        >>> summary = RegionStepSummary(0, RegionStepTrace((), ()), (), (), (), (), (), z3.BoolVal(True))
        >>> summary.case is summary
        True
    """

    step_index: int
    trace: RegionStepTrace
    local_cases: Tuple[Tuple[Optional[str], str, str], ...]
    used_events: Tuple[EventUse, ...]
    consumed_events: Tuple[str, ...]
    guard_requirements: Tuple[GuardRequirement, ...]
    action_blocks: Tuple[ActionBlock, ...]
    antecedent: z3.BoolRef

    @property
    def case(self) -> "RegionStepSummary":
        """Return the summary as the single case the single-path code reads.

        :return: This summary.
        :rtype: RegionStepSummary

        Example::

            >>> import z3
            >>> summary = RegionStepSummary(0, RegionStepTrace((), ()), (), (), (), (), (), z3.BoolVal(True))
            >>> summary.case is summary
            True
        """
        return self

    def kind(self, delta: bool, gamma: bool, source_terminated: bool) -> str:
        """Sum the cycle up as one case kind.

        :param delta: Whether the cycle was a Delta.
        :type delta: bool
        :param gamma: Whether the cycle only ran fallbacks.
        :type gamma: bool
        :param source_terminated: Whether the machine had already terminated.
        :type source_terminated: bool
        :return: ``"absorb"`` after termination, ``"delta"`` for a Delta,
            ``"fallback"`` when every region only ran its during actions,
            ``"transition"`` when some path was a transition and ``"initial"``
            when the cycle only started things.
        :rtype: str

        Example::

            >>> import z3
            >>> summary = RegionStepSummary(0, RegionStepTrace((), ()), (), (), (), (), (), z3.BoolVal(True))
            >>> (summary.kind(True, False, False), summary.kind(False, False, True))
            ('delta', 'absorb')
        """
        if source_terminated:
            return "absorb"
        if delta:
            return "delta"
        if gamma:
            return "fallback"
        if any(kind == "transition" for _, kind, _ in self.local_cases):
            return "transition"
        return "initial"


@dataclass(frozen=True)
class RegionStepTrace:
    """The paths a cycle ran and the calls it made, in execution order.

    :param paths: Paths that ran, each a :class:`RegionCaseRelation`; units that
        a group start runs follow the path that started the group.
    :type paths: Tuple[pyfcstm.bmc.region_relation.RegionCaseRelation, ...]
    :param calls: Abstract actions called, in call order.
    :type calls: Tuple[RegionCall, ...]

    Example::

        >>> RegionStepTrace((), ()).calls
        ()
    """

    paths: Tuple[RegionCaseRelation, ...]
    calls: Tuple[RegionCall, ...]


def _value(model: z3.ModelRef, expr: z3.ExprRef) -> Union[int, float]:
    """Read a numeric value of a solved model.

    :param model: Solved model.
    :param expr: Arithmetic expression to evaluate.
    :return: An ``int`` for an integer value, a ``float`` for a rational one.
    """
    value = model.eval(expr, True)
    if z3.is_int_value(value):
        return value.as_long()
    return float(value.numerator_as_long()) / float(value.denominator_as_long())


def _holds(model: z3.ModelRef, expr: z3.BoolRef) -> bool:
    """Return whether ``expr`` is true in ``model``."""
    return z3.is_true(model.eval(expr, True))


class _Machine:
    """The tree the runtime is executing, rebuilt while a cycle is replayed.

    :param domain: Domain of the model.
    :param main: Path of the state the machine rests in outside every region, or
        ``None`` before the cold start.
    :param positions: Where each region of a resting owner is: a state path,
        ``"done"`` or ``"pending"``.
    """

    def __init__(
        self, domain: BmcDomain, main: Optional[str], positions: Dict[str, str]
    ) -> None:
        self.domain = domain
        self.main = main
        self.positions = positions
        self.regions = {region.path: region for region in domain.regions}
        self.owned: Dict[str, List[RegionDomainEntry]] = {}
        for region in domain.regions:
            self.owned.setdefault(region.owner_path, []).append(region)

    def enter(self, path: str) -> None:
        """Mark the regions of ``path`` as not started when it is a group."""
        for region in self.owned.get(path, ()):
            self.positions[region.path] = _PENDING

    def settle(self, home: _Where, target_kind: str, target_path: str) -> None:
        """Move the position a unit runs in to where the unit ended.

        :param home: Region the unit runs in, ``None`` for the main namespace.
        :param target_kind: ``leaf``, ``owner``, ``done`` or ``terminate``.
        :param target_path: Path of the state the unit ended in.
        """
        if target_kind == "terminate":
            self.main = None
            return
        value = _DONE if target_kind == "done" else target_path
        if home is None:
            self.main = value
        else:
            self.positions[home] = value
        if target_kind == "owner":
            self.enter(target_path)

    def node(
        self,
        path: str,
        cursor: _Where = None,
        cursor_top: _Where = None,
    ) -> Dict[str, object]:
        """Build the configuration node of the state at ``path``.

        :param path: State path of the node.
        :param cursor: Region that is running, or ``None``.
        :param cursor_top: State the running region is in right now, or ``None``
            while it has not entered a state.
        """
        node: Dict[str, object] = {"state": path, "regions": []}
        for region in self.owned.get(path, ()):
            if region.path == cursor:
                value = cursor_top if cursor_top is not None else _PENDING
            else:
                value = self.positions.get(region.path, _PENDING)
            if value == _PENDING:
                continue
            node["regions"].append(  # type: ignore[union-attr]
                {
                    "name": region.name,
                    "configuration": None
                    if value == _DONE
                    else self.node(value, cursor, cursor_top),
                }
            )
        return node

    def tree(
        self,
        cursor: _Where = None,
        cursor_top: _Where = None,
        main_top: _Where = None,
    ) -> Dict[str, object]:
        """Build the whole configuration tree at this moment.

        :param cursor: Region that is running, or ``None``.
        :param cursor_top: State the running region is in right now.
        :param main_top: State the machine is in outside every region, when the
            unit that is running overrides it.
        """
        top = main_top if main_top is not None else self.main
        return self.node(top, cursor, cursor_top)


def _start_machine(
    core: BmcCoreFormula, model: z3.ModelRef, step_index: int
) -> _Machine:
    """Read the positions of the frame a cycle starts in."""
    domain = core.context.domain
    symbols = core.symbols
    ids = {entry.id: entry.path for entry in domain.states}
    main_id = model.eval(symbols.frame_state(step_index), True).as_long()
    main = None if main_id in (STATE_INIT_ID, STATE_TERMINATE_ID) else ids[main_id]
    positions: Dict[str, str] = {}
    for region in domain.regions:
        value = model.eval(symbols.region_position(step_index, region.path), True)
        value = value.as_long()
        if value == REGION_INACTIVE_ID:
            continue
        if value == REGION_DONE_ID:
            positions[region.path] = _DONE
        elif value == REGION_PENDING_ID:
            positions[region.path] = _PENDING
        else:
            positions[region.path] = ids[value]
    machine = _Machine(domain, main, positions)
    return machine


def _call(
    record: BmcAbstractCallRecord,
    model: z3.ModelRef,
    machine: _Machine,
    tree: Dict[str, object],
) -> RegionCall:
    """Turn a lowered call record into the call a handler sees."""
    state, leaf = reported_call_state(machine.domain, record)
    return RegionCall(
        record.action_name,
        record.stage,
        record.role,
        state,
        leaf,
        record.named_ref,
        {name: _value(model, expr) for name, expr in sorted(record.snapshot.items())},
        str(Configuration.from_dict(machine.domain.model, _transient(tree))),
    )


def _transient(tree: Dict[str, object]) -> Dict[str, object]:
    """Return ``tree`` as the dictionary a transient configuration reads."""
    return {**tree, "mode": "transient"}


def _record_case(
    machine: _Machine,
    model: z3.ModelRef,
    relation: RegionCaseRelation,
    calls: List[RegionCall],
) -> None:
    """Replay one path: make its calls, then move the position it ran in."""
    case: RegionCase = relation.case
    for record in relation.call_records:
        stack = record.stack_states or ()
        top = stack[-1] if stack else None
        if case.home is None:
            tree = machine.tree(main_top=top)
        else:
            tree = machine.tree(cursor=case.home, cursor_top=top)
        calls.append(_call(record, model, machine, tree))
    machine.settle(case.home, case.target_kind, case.target_state_path)


def _record_flush(
    machine: _Machine,
    model: z3.ModelRef,
    relation: RegionFlushRelation,
    calls: List[RegionCall],
) -> None:
    """Replay one settlement: its calls see the tree as it is."""
    for record in relation.call_records:
        tree = machine.tree()
        calls.append(_call(record, model, machine, tree))


def trace_region_step(
    core: BmcCoreFormula, model: z3.ModelRef, step_index: int
) -> RegionStepTrace:
    """Decode the paths and the abstract calls of one cycle of a solved model.

    The paths come back in the order the runtime runs them, and every call
    carries the configuration the runtime hands the handler at that moment.

    :param core: Core formula of a model with regions.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param model: Solved model of a formula that contains ``core``.
    :type model: z3.ModelRef
    :param step_index: Zero-based cycle to decode.
    :type step_index: int
    :return: The paths and calls of the cycle.
    :rtype: RegionStepTrace
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``core`` has no regions or
        ``step_index`` is not a cycle of it.

    Example::

        >>> import z3
        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.bmc.region_witness import trace_region_step
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 2: terminated();'))
        >>> solver = z3.Solver()
        >>> solver.add(core.core)
        >>> solver.check()
        sat
        >>> [item.case.public_label for item in trace_region_step(core, solver.model(), 0).paths]
        ['__init__::initial::Root::0', 'Root::initial::Root.A.P::0', 'Root::initial::Root.B.Q::0']
        >>> trace_region_step(core, solver.model(), 5)
        Traceback (most recent call last):
            ...
        pyfcstm.bmc.errors.BmcBuildError: step 5 is not a cycle of this core formula.
    """
    if not core.region_steps:
        raise BmcBuildError("the core formula has no regions.")
    if not 0 <= step_index < len(core.region_steps):
        raise BmcBuildError(
            "step %d is not a cycle of this core formula." % step_index
        )
    step = core.region_steps[step_index]
    machine = _start_machine(core, model, step_index)
    calls: List[RegionCall] = []
    paths: List[RegionCaseRelation] = []
    for occurrence in region_occurrences(step):
        if not _holds(model, occurrence.condition):
            continue
        if occurrence.flush is not None:
            _record_flush(machine, model, occurrence.flush, calls)
        else:
            paths.append(occurrence.case)
            _record_case(machine, model, occurrence.case, calls)
    return RegionStepTrace(tuple(paths), tuple(calls))


def summarize_region_step(
    core: BmcCoreFormula, model: z3.ModelRef, step_index: int
) -> RegionStepSummary:
    """Sum up a cycle of a solved model for a witness step.

    :param core: Core formula of a model with regions.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param model: Solved model of a formula that contains ``core``.
    :type model: z3.ModelRef
    :param step_index: Zero-based cycle to sum up.
    :type step_index: int
    :return: The paths and calls of the cycle with what a witness step reads off
        them.
    :rtype: RegionStepSummary
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``core`` has no regions or
        ``step_index`` is not a cycle of it.

    Example::

        >>> import z3
        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.bmc.region_witness import summarize_region_step
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
        >>> solver = z3.Solver()
        >>> solver.add(core.core)
        >>> solver.check()
        sat
        >>> [label for _, _, label in summarize_region_step(core, solver.model(), 0).local_cases]
        ['__init__::initial::Root::0', 'Root::initial::Root.A.P::0', 'Root::initial::Root.B.Q::0']
    """
    trace = trace_region_step(core, model, step_index)
    paths = trace.paths
    used: List[EventUse] = []
    consumed: List[str] = []
    guards: List[GuardRequirement] = []
    blocks: List[ActionBlock] = []
    for item in paths:
        used.extend(item.case.used_events)
        consumed.extend(item.case.consumed_events)
        guards.extend(item.case.guard_requirements)
        blocks.extend(item.case.action_blocks)
    return RegionStepSummary(
        step_index,
        trace,
        tuple(
            (item.case.scope, item.case.kind, item.case.public_label)
            for item in paths
            if item.case.public_label
        ),
        tuple(used),
        tuple(consumed),
        tuple(guards),
        tuple(blocks),
        z3.And(*[item.antecedent for item in paths]) if paths else z3.BoolVal(True),
    )


def frame_configuration(
    core: BmcCoreFormula, model: z3.ModelRef, frame_index: int
) -> Optional[str]:
    """Return the configuration text of a frame of a solved model.

    :param core: Core formula of a model with regions.
    :type core: pyfcstm.bmc.relation.BmcCoreFormula
    :param model: Solved model of a formula that contains ``core``.
    :type model: z3.ModelRef
    :param frame_index: Frame index in ``0..N``.
    :type frame_index: int
    :return: The text of the position the machine rests in, as the simulator
        prints it; a region that waits for initialization reads ``[init]``.
        ``None`` for the cold-start frame and after termination, where the machine
        rests nowhere.
    :rtype: Optional[str]
    :raises pyfcstm.bmc.errors.BmcBuildError: If ``core`` has no regions.

    Example::

        >>> import z3
        >>> from pyfcstm.bmc import BmcEngine, build_bmc_core_formula
        >>> from pyfcstm.bmc.region_witness import frame_configuration
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> model = load_state_machine_from_text('''
        ... state Root {
        ...     region A { [*] -> P; state P; }
        ...     region B { [*] -> Q; state Q; }
        ... }
        ... ''')
        >>> core = build_bmc_core_formula(BmcEngine(model).prepare('check reach <= 1: terminated();'))
        >>> solver = z3.Solver()
        >>> solver.add(core.core)
        >>> solver.check()
        sat
        >>> (frame_configuration(core, solver.model(), 0), frame_configuration(core, solver.model(), 1))
        (None, 'Root{A: P, B: Q}')
    """
    if not core.region_steps:
        raise BmcBuildError("the core formula has no regions.")
    machine = _start_machine(core, model, frame_index)
    if machine.main is None:
        return None
    return str(
        Configuration.from_dict(core.context.domain.model, _transient(machine.tree()))
    )


__all__ = [
    "RegionCall",
    "RegionStepSummary",
    "RegionStepTrace",
    "frame_configuration",
    "summarize_region_step",
    "trace_region_step",
]

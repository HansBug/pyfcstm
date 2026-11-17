"""
Ordering diagnostics for the regions of a parallel owner state.

The regions of one owner run in declaration order within a cycle, on one shared
set of variables. A later region therefore sees what an earlier region wrote in
the same cycle, while an earlier region sees a later region's results only one
cycle late. Two situations deserve a message, and both are judged on the model
as written, before ``active()`` queries are lowered to hidden flag variables:

* ``I_REGION_BACKWARD_READ`` (information): an earlier region reads a variable
  that a later region writes, or queries with ``active()`` a state that sits in
  a later region. The earlier region reads the previous cycle's value. That is
  the defined behavior of ordered regions, so it is only reported to let the
  author confirm the order.
* ``W_REGION_BLIND_OVERWRITE`` (warning): a later region assigns a variable
  that an earlier region also writes, without using the earlier value. Several
  regions writing one variable is fine when the later write builds on the
  earlier one (``x = x + y``); it is a warning only when the earlier write is
  lost for certain.

The module contains:

* :func:`collect_region_order_diagnostics` - Collect both diagnostics for a
  state machine.

A write is "blind" when its new value does not read the old one, nothing read
the old value earlier in the same action or effect block (including the
conditions of enclosing and preceding ``if`` branches), the guard of the owning
transition does not read it, the guards of the state's outgoing transitions do
not read it (they are checked before the state's ``during`` runs), and no
region between the two writers reads it. A read of the variable in some other
state of the same region does not make the write non-blind, because the
analysis cannot tell which state is active when the earlier region wrote.

Example::

    >>> from pyfcstm.diagnostics import inspect_model
    >>> from pyfcstm.model import load_state_machine_from_text
    >>> machine = load_state_machine_from_text('''
    ... def int out = 0;
    ... def int y = 0;
    ... state Root {
    ...     region First { state A { during { out = 1; } } [*] -> A; }
    ...     region Second { state B { during { out = y + 2; } } [*] -> B; }
    ... }
    ... ''')
    >>> [d.code for d in inspect_model(machine).diagnostics
    ...  if d.code == 'W_REGION_BLIND_OVERWRITE']
    ['W_REGION_BLIND_OVERWRITE']
"""

from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Dict, FrozenSet, List, Optional, Set, Tuple

from ...utils.validate import ModelDiagnostic, Span
from .use_def import collect_expr_variables

if TYPE_CHECKING:  # pragma: no cover
    from ...model.model import StateMachine


@dataclass
class _Write:
    """One assignment to a model variable inside a region.

    :ivar span: Source span of the assignment statement.
    :ivar blind: ``True`` when nothing in the same block, the owning guard or
        the state's outgoing guards reads the old value, and the statement is
        the first write of that variable in its block.
    """

    span: Optional[Span]
    blind: bool


@dataclass
class _RegionAccess:
    """Variable and ``active()`` accesses collected from one region subtree.

    :ivar path: Dotted path of the region.
    :ivar reads: First read site (span) of each variable, in encounter order.
    :ivar queries: First query site (span) of each queried state path.
    :ivar writes: All assignments of each variable, in encounter order.
    """

    path: str
    reads: Dict[str, Optional[Span]] = field(default_factory=dict)
    queries: Dict[Tuple[str, ...], Optional[Span]] = field(default_factory=dict)
    writes: Dict[str, List[_Write]] = field(default_factory=dict)


def collect_region_order_diagnostics(machine: Optional['StateMachine']) -> List[ModelDiagnostic]:
    """
    Report ordering information and blind overwrites between sibling regions.

    Every state that owns regions is examined on its own; regions nested in a
    region are covered when their own owner is reached, and their accesses also
    count for the enclosing region. A model without regions yields no
    diagnostics.

    :param machine: State machine as written (before ``active()`` lowering), or
        ``None``.
    :type machine: Optional[pyfcstm.model.model.StateMachine]
    :return: ``I_REGION_BACKWARD_READ`` and ``W_REGION_BLIND_OVERWRITE``
        diagnostics, ordered by owner, then by region declaration order.
    :rtype: List[pyfcstm.utils.validate.ModelDiagnostic]

    Example::

        >>> from pyfcstm.diagnostics.analyzers.region_order import (
        ...     collect_region_order_diagnostics)
        >>> from pyfcstm.model import load_state_machine_from_text
        >>> machine = load_state_machine_from_text('''
        ... def int level = 0;
        ... def int seen = 0;
        ... state Root {
        ...     region Reader { state Idle { during { seen = level; } } [*] -> Idle; }
        ...     region Writer { state Busy { during { level = level + 1; } } [*] -> Busy; }
        ... }
        ... ''')
        >>> [(d.code, d.refs['target']) for d in collect_region_order_diagnostics(machine)]
        [('I_REGION_BACKWARD_READ', 'level')]
        >>> collect_region_order_diagnostics(None)
        []
    """
    from ...model.model import State
    from ...model.region import walk_namespaces

    if machine is None:
        return []
    defined = set(machine.defines)
    diagnostics: List[ModelDiagnostic] = []
    for namespace in walk_namespaces(machine.root_state):
        if isinstance(namespace, State) and namespace.regions:
            accesses = [
                _collect_region_access(region, defined, machine.root_state)
                for region in namespace.regions.values()
            ]
            owner_path = '.'.join(namespace.path)
            diagnostics.extend(_backward_read_diagnostics(owner_path, accesses))
            diagnostics.extend(_blind_overwrite_diagnostics(owner_path, accesses))
    return diagnostics


def _backward_read_diagnostics(owner_path: str, accesses: List[_RegionAccess]) -> List[ModelDiagnostic]:
    """Information for reads of what a later region writes or contains."""
    diagnostics: List[ModelDiagnostic] = []
    for index, reader in enumerate(accesses):
        later = accesses[index + 1:]
        for name, span in reader.reads.items():
            writers = [item.path for item in later if name in item.writes]
            if writers:
                diagnostics.append(_backward_read(owner_path, reader.path, 'variable', name, writers, span))
        for target, span in reader.queries.items():
            dotted = '.'.join(target)
            holders = [
                item.path for item in later
                if target[:len(item.path.split('.'))] == tuple(item.path.split('.'))
            ]
            if holders:
                diagnostics.append(_backward_read(owner_path, reader.path, 'active', dotted, holders, span))
    return diagnostics


def _backward_read(owner_path, reader_path, kind, target, writers, span) -> ModelDiagnostic:
    """Build one ``I_REGION_BACKWARD_READ`` diagnostic."""
    noun = 'variable' if kind == 'variable' else 'state activity'
    return ModelDiagnostic(
        code='I_REGION_BACKWARD_READ',
        severity='info',
        message=(
            f'Region {reader_path!r} reads {noun} {target!r}, which is produced by the later '
            f'region {", ".join(repr(item) for item in writers)}; it sees the value from the '
            'previous cycle.'
        ),
        span=span,
        refs={
            'owner_path': owner_path,
            'reader_region': reader_path,
            'target_kind': kind,
            'target': target,
            'writer_regions': list(writers),
        },
    )


def _blind_overwrite_diagnostics(owner_path: str, accesses: List[_RegionAccess]) -> List[ModelDiagnostic]:
    """Warnings for later-region writes that discard an earlier region's value."""
    diagnostics: List[ModelDiagnostic] = []
    for index, access in enumerate(accesses):
        for name, writes in access.writes.items():
            previous = next(
                (position for position in range(index - 1, -1, -1) if name in accesses[position].writes),
                None,
            )
            if previous is None:
                continue
            if any(name in item.reads for item in accesses[previous + 1:index]):
                continue
            for write in writes:
                if write.blind:
                    diagnostics.append(ModelDiagnostic(
                        code='W_REGION_BLIND_OVERWRITE',
                        severity='warning',
                        message=(
                            f'Region {access.path!r} overwrites variable {name!r} without using '
                            f'the value written by the earlier region {accesses[previous].path!r}.'
                        ),
                        span=write.span,
                        refs={
                            'owner_path': owner_path,
                            'region': access.path,
                            'previous_region': accesses[previous].path,
                            'variable': name,
                        },
                    ))
    return diagnostics


def _collect_region_access(region, defined: Set[str], root) -> _RegionAccess:
    """Collect every access in the subtree of ``region``, in source order."""
    from ...model.model import State
    from ...model.region import walk_namespaces

    access = _RegionAccess(path='.'.join(region.path))
    for namespace in walk_namespaces(region):
        outgoing = _outgoing_guard_reads(namespace, defined)
        for transition in namespace.transitions:
            guard_reads = _note_expression(access, transition.guard, defined, root, getattr(transition, '_span', None))
            _scan_block(access, transition.effects, defined, root, frozenset(guard_reads))
        actions = (
            (*namespace.on_enters, *namespace.on_durings, *namespace.on_exits, *namespace.on_during_aspects)
            if isinstance(namespace, State) else namespace.on_during_aspects
        )
        for action in actions:
            # The guards of a state's outgoing transitions are checked before its
            # ``during`` and aspect actions run, and before its ``exit`` runs.
            initial = frozenset() if getattr(action, 'stage', None) == 'enter' else outgoing
            _scan_block(access, action.operations or (), defined, root, initial)
    return access


def _outgoing_guard_reads(namespace, defined: Set[str]) -> FrozenSet[str]:
    """Variables read by the guards of the transitions leaving a state."""
    from ...model.model import State

    parent = namespace.parent if isinstance(namespace, State) else None
    if parent is None:
        return frozenset()
    names: Set[str] = set()
    for transition in parent.transitions:
        if transition.from_state == namespace.name and transition.guard is not None:
            names |= {item for item in collect_expr_variables(transition.guard) if item in defined}
    return frozenset(names)


def _note_expression(access, expression, defined, root, span) -> Set[str]:
    """Record the reads and ``active()`` queries of an expression; return its variables."""
    from ...model.active import _target
    from ...model.expr import ActiveStateQuery

    if expression is None:
        return set()
    names = {item for item in collect_expr_variables(expression) if item in defined}
    for name in dict.fromkeys(item for item in collect_expr_variables(expression) if item in defined):
        access.reads.setdefault(name, span)
    for node in expression._iter_all_subs():
        if isinstance(node, ActiveStateQuery):
            target, reason = _target(root, node)
            if reason is None:
                access.queries.setdefault(tuple(target.path), span)
    return names


def _scan_block(access, statements, defined, root, reads_before: FrozenSet[str]) -> Set[str]:
    """Scan a statement list; return every variable read so far, including leaks from branches.

    ``reads_before`` holds variables whose old value was already used before the
    block starts (the owning guard, or outgoing guards). A write is blind only
    when its variable is not read by its own expression, by ``reads_before``, by
    any earlier statement or enclosing condition, and was not written earlier in
    a straight line of the same block.
    """
    return _scan(access, statements, defined, root, set(reads_before), frozenset())


def _scan(access, statements, defined, root, reads: Set[str], written: FrozenSet[str]) -> Set[str]:
    """Recursive worker of :func:`_scan_block`."""
    from ...model.model import Operation

    written = set(written)
    for statement in statements:
        if isinstance(statement, Operation):
            used = _note_expression(access, statement.expr, defined, root, getattr(statement, '_span', None))
            name = statement.var_name
            if name in defined:
                blind = name not in used and name not in reads and name not in written
                access.writes.setdefault(name, []).append(_Write(getattr(statement, '_span', None), blind))
                written.add(name)
            reads |= used
        else:
            seen = set(reads)
            for branch in statement.branches:
                if branch.condition is not None:
                    seen |= _note_expression(access, branch.condition, defined, root, getattr(branch, '_span', None))
                seen |= _scan(access, branch.statements, defined, root, set(seen), frozenset(written))
            reads |= seen
    return reads

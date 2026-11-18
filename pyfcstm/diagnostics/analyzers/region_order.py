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
  author confirm the order. A read that follows a write of the same variable
  in the same action chain reads the region's own fresh value and is not
  reported.
* ``W_REGION_BLIND_OVERWRITE`` (warning): a later region overwrites, in every
  cycle and without ever looking at it, a variable that an earlier region
  wrote, so the earlier write is lost every cycle. Writing one variable from
  several regions is fine on its own, and so is the common "default value in
  front, override behind" pattern; only a certain loss is reported.

A later region ``B`` overwrites a variable ``v`` *blindly in every cycle* when
all of these hold:

* every non-pseudo leaf state of ``B`` writes ``v`` unconditionally at the top
  level of its ``during`` actions (or of a ``>> during before`` aspect that
  runs ahead of them), so whichever state ``B`` rests in, ``v`` is overwritten;
* nothing in ``B`` reads ``v`` ahead of that write: no guard, effect,
  ``enter``, ``exit``, right-hand side, ``if`` condition or earlier statement,
  and no state that does not write ``v``;
* ``B`` cannot finish (it has no ``[*]`` exit, because a finished region stops
  writing), contains no nested parallel owner, and has no abstract or ``ref``
  action that a handler could use to read ``v``.

The earlier write of region ``A`` is lost when no statement that runs after it
in the same cycle reads ``v`` (later statements of the same block, the same
leaf's other ``during`` actions and ``>> during after`` aspects), no region
between ``A`` and ``B`` reads ``v`` or has an abstract action, and ``A`` has no
abstract action. Aspects declared on the owner or further out run once per cycle
around the whole group of regions, so they neither use ``A``'s value nor shield
it; they are ignored here.

The module contains:

* :func:`collect_region_order_diagnostics` - Collect both diagnostics for a
  state machine.

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
from typing import TYPE_CHECKING, Dict, Iterable, List, Optional, Set, Tuple

from ...utils.validate import ModelDiagnostic, Span
from .use_def import collect_expr_variables

if TYPE_CHECKING:  # pragma: no cover
    from ...model.model import StateMachine

# One event of an action chain: ``('read', name, span)``, ``('query', path,
# span)``, ``('write', name, span, sure)``, ``('cover', name, span, sure)``
# or a branch marker ``('begin',)`` / ``('end',)``; see ``_statements_events``.
_Event = Tuple


@dataclass
class _Write:
    """One assignment to a model variable inside a region.

    :ivar span: Source span of the assignment statement.
    :ivar consumed: ``True`` when something that runs after it in the same
        cycle may read the value it stored.
    """

    span: Optional[Span]
    consumed: bool = False


@dataclass
class _RegionAccess:
    """Variable and ``active()`` accesses collected from one region subtree.

    :ivar path: Dotted path of the region.
    :ivar uncovered_reads: First site of each variable read before the region
        wrote it in the same chain, in encounter order. Reads that follow an
        unconditional write of the same variable in the same chain read the
        region's own value and are not listed.
    :ivar any_reads: Every variable read anywhere in the subtree.
    :ivar queries: First query site of each queried state path.
    :ivar writes: All assignments of each variable, in encounter order.
    :ivar certain: Variables the region overwrites in every cycle, mapped to the
        site of the overwriting statement.
    :ivar has_abstract: An abstract or ``ref`` action exists in the subtree.
    :ivar has_exit: A transition to ``[*]`` exists in the subtree.
    :ivar has_nested_owner: A state with regions is nested in the subtree.
    """

    path: str
    uncovered_reads: Dict[str, Optional[Span]] = field(default_factory=dict)
    any_reads: Set[str] = field(default_factory=set)
    queries: Dict[Tuple[str, ...], Optional[Span]] = field(default_factory=dict)
    writes: Dict[str, List[_Write]] = field(default_factory=dict)
    certain: Dict[str, Optional[Span]] = field(default_factory=dict)
    has_abstract: bool = False
    has_exit: bool = False
    has_nested_owner: bool = False
    _leaf_covers: List[Dict[str, Optional[Span]]] = field(default_factory=list)
    _plain_writes: List[Tuple[str, _Write]] = field(default_factory=list)


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
        for name, span in reader.uncovered_reads.items():
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
    """Warnings for later regions that overwrite an earlier region's value in every cycle."""
    diagnostics: List[ModelDiagnostic] = []
    for index, access in enumerate(accesses):
        for name, span in access.certain.items():
            previous = next(
                (position for position in range(index - 1, -1, -1) if name in accesses[position].writes),
                None,
            )
            if previous is None:
                continue
            earlier = accesses[previous]
            if earlier.has_abstract or any(
                    name in item.uncovered_reads or item.has_abstract
                    for item in accesses[previous + 1:index]
            ):
                continue
            lost = [write for write in earlier.writes[name] if not write.consumed]
            if not lost:
                continue
            diagnostics.append(ModelDiagnostic(
                code='W_REGION_BLIND_OVERWRITE',
                severity='warning',
                message=(
                    f'Region {access.path!r} overwrites variable {name!r} in every cycle without using '
                    f'the value written by the earlier region {earlier.path!r}; that earlier write is lost whenever it runs.'
                ),
                span=span,
                refs={
                    'owner_path': owner_path,
                    'region': access.path,
                    'previous_region': earlier.path,
                    'variable': name,
                    'previous_write_span': lost[0].span,
                },
            ))
    return diagnostics


def _collect_region_access(region, defined: Set[str], root) -> _RegionAccess:
    """Collect every access in the subtree of ``region`` and judge what it overwrites."""
    access = _RegionAccess(path='.'.join(region.path))
    _walk(region, (), (), access, defined, root, nested=False)
    for name, write in access._plain_writes:
        write.consumed = name in access.any_reads
    leaves = access._leaf_covers
    if leaves and not (access.has_abstract or access.has_exit or access.has_nested_owner):
        for name, span in leaves[0].items():
            if name not in access.uncovered_reads and all(name in leaf for leaf in leaves):
                access.certain[name] = span
    return access


def _walk(namespace, before, after, access, defined, root, nested: bool) -> None:
    """Visit a state or region, recording plain blocks and leaf action chains.

    ``before`` and ``after`` are the ``>> during`` actions of the enclosing
    namespaces inside the region being collected, outermost first for
    ``before`` and innermost first for ``after``, which is the order a leaf runs
    them in. Inside a nested parallel owner (``nested``) nothing is treated as a
    certain per-cycle chain: every block is recorded as a plain block.
    """
    from ...dsl import EXIT_STATE
    from ...model.model import State

    for transition in namespace.transitions:
        if transition.to_state is EXIT_STATE:
            access.has_exit = True
        _plain(access, _expression_events(transition.guard, defined, root, _span_of(transition)))
        _plain(access, _statements_events(transition.effects, defined, root))

    own_before = [item for item in namespace.on_during_aspects if item.aspect == 'before']
    own_after = [item for item in namespace.on_during_aspects if item.aspect == 'after']
    if nested:
        for action in (*own_before, *own_after):
            _plain_action(access, action, defined, root)
    deeper_before, deeper_after = [*before, *own_before], [*own_after, *after]

    if isinstance(namespace, State):
        for action in (*namespace.on_enters, *namespace.on_exits):
            _plain_action(access, action, defined, root)
        if namespace.regions:
            access.has_nested_owner = True
            for region in namespace.regions.values():
                _walk(region, (), (), access, defined, root, True)
        if not (namespace.substates or namespace.regions):
            if nested or namespace.is_pseudo:
                for action in namespace.on_durings:
                    _plain_action(access, action, defined, root)
            else:
                _leaf(namespace, deeper_before, deeper_after, access, defined, root)
            return
        # A composite's own ``during before`` / ``during after`` actions run when it
        # is entered and left, not around every cycle of its leaves.
        for action in namespace.on_durings:
            _plain_action(access, action, defined, root)
    for child in namespace.substates.values():
        _walk(child, deeper_before, deeper_after, access, defined, root, nested)


def _leaf(state, before, after, access, defined, root) -> None:
    """Scan the action chain a leaf runs in a cycle: before aspects, during, after aspects."""
    chain: List[_Event] = []
    for action in (*before, *(item for item in state.on_durings if item.aspect is None), *after):
        if action.is_abstract or action.is_ref:
            access.has_abstract = True
            continue
        chain.extend(_statements_events(action.operations, defined, root))
    covered: Set[str] = set()
    stack: List[Set[str]] = []
    sure: Dict[str, Optional[Span]] = {}
    for position, event in enumerate(chain):
        kind = event[0]
        if kind == 'read':
            access.any_reads.add(event[1])
            if event[1] not in covered:
                access.uncovered_reads.setdefault(event[1], event[2])
        elif kind == 'query':
            access.queries.setdefault(event[1], event[2])
        elif kind == 'begin':
            stack.append(set(covered))
        elif kind == 'end':
            covered = stack.pop()
        elif kind == 'cover':
            covered.add(event[1])
            if event[3]:
                sure.setdefault(event[1], event[2])
        else:
            _, name, span, is_sure = event
            write = _Write(span, consumed=any(
                later[0] == 'read' and later[1] == name for later in chain[position + 1:]
            ))
            access.writes.setdefault(name, []).append(write)
            covered.add(name)
            if is_sure:
                sure.setdefault(name, span)
    access._leaf_covers.append(sure)


def _plain_action(access, action, defined, root) -> None:
    """Record an action that is not part of a leaf's per-cycle chain."""
    if action.is_abstract or action.is_ref:
        access.has_abstract = True
        return
    _plain(access, _statements_events(action.operations, defined, root))


def _plain(access, events: Iterable[_Event]) -> None:
    """Record events of a block outside every leaf chain: all its reads are uncovered."""
    for event in events:
        kind = event[0]
        if kind == 'read':
            access.any_reads.add(event[1])
            access.uncovered_reads.setdefault(event[1], event[2])
        elif kind == 'query':
            access.queries.setdefault(event[1], event[2])
        elif kind == 'write':
            write = _Write(event[2])
            access.writes.setdefault(event[1], []).append(write)
            access._plain_writes.append((event[1], write))


def _span_of(node) -> Optional[Span]:
    """Source span of a model node, when it has one."""
    return getattr(node, '_span', None)


def _expression_events(expression, defined: Set[str], root, span) -> List[_Event]:
    """Events of one expression: its variable reads and ``active()`` queries."""
    from ...model.active import _target
    from ...model.expr import ActiveStateQuery

    if expression is None:
        return []
    events: List[_Event] = [
        ('read', name, span)
        for name in dict.fromkeys(item for item in collect_expr_variables(expression) if item in defined)
    ]
    for node in expression._iter_all_subs():
        if isinstance(node, ActiveStateQuery):
            # Model construction already rejected every query that names no
            # state, so the target always resolves here.
            target, _ = _target(root, node)
            events.append(('query', tuple(target.path), span))
    return events


def _statements_events(statements, defined: Set[str], root, sure: bool = True) -> List[_Event]:
    """Flatten a statement list into events in textual order.

    The right-hand side of an assignment is read before the assignment writes.
    A write event is ``('write', name, span, sure)``: ``sure`` is true only when
    the statement runs on every path through the whole chain (it is not inside
    any ``if``). Every write covers the reads that follow it in its own block. A branch is wrapped in ``('begin',)`` and ``('end',)`` so that
    the covering done inside it ends with it. When an ``if`` has an ``else`` and
    every branch writes a variable at its top level, a ``('cover', name, span,
    sure)`` event follows the statement, because every path wrote the variable.
    """
    from ...model.model import Operation

    events: List[_Event] = []
    for statement in statements:
        if isinstance(statement, Operation):
            span = _span_of(statement)
            events.extend(_expression_events(statement.expr, defined, root, span))
            if statement.var_name in defined:
                events.append(('write', statement.var_name, span, sure))
            continue
        branch_writes: List[Dict[str, Optional[Span]]] = []
        for branch in statement.branches:
            events.extend(_expression_events(branch.condition, defined, root, _span_of(branch)))
            inner = _statements_events(branch.statements, defined, root, False)
            events.append(('begin',))
            events.extend(inner)
            events.append(('end',))
            branch_writes.append({
                item[1]: item[2] for item in reversed(inner)
                if item[0] == 'write'
            })
        if statement.branches[-1].condition is None:
            for name, span in branch_writes[0].items():
                if all(name in item for item in branch_writes):
                    events.append(('cover', name, span, sure))
    return events

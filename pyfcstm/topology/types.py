"""
Shared data types for topological verification.

This module defines the result and counterexample dataclasses returned by
:func:`pyfcstm.topology.check_reachability`,
:func:`pyfcstm.topology.check_finiteness`, and
:func:`pyfcstm.topology.check_inevitability`. It also defines the
:data:`END_NODE` sentinel that the macro graph uses to model the
``[*]``-exit-from-root transition (legitimate machine termination).

Internal collections key nodes by :func:`node_key`, which returns a
hashable identifier (``State.path`` tuple, or the END sentinel) instead of
the :class:`pyfcstm.model.State` object itself. State dataclasses do not
provide a stable hash, so this indirection is required for sets, dicts,
and frozensets.

The module contains:

* :data:`END_NODE` - Sentinel object representing legitimate termination.
* :func:`node_key` - Hashable key for graph nodes.
* :class:`MacroEdge` - One ``leaf -> next-leaf-or-END`` macro edge.
* :class:`TopologyGraph` - Frozen view over the flattened macro graph.
* :class:`ReachabilityResult` - Verdict for
  :func:`pyfcstm.topology.check_reachability`.
* :class:`FinitenessCounterexample`, :class:`FinitenessResult` -
  Counterexample + verdict for finiteness.
* :class:`InevitabilityCounterexample`, :class:`InevitabilityResult` -
  Counterexample + verdict for inevitability.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Dict, List, Optional, Tuple, Union

from ..model import State

try:
    from typing import Literal
except (ImportError, ModuleNotFoundError):  # pragma: no cover - py37 fallback
    from typing_extensions import Literal


class _EndNodeSentinel:
    """
    Internal singleton type for :data:`END_NODE`.

    The sentinel compares by identity and produces a stable ``repr()`` /
    ``str()`` so debug output reads ``[*]`` rather than ``<object ...>``.
    """

    __slots__ = ()

    def __repr__(self) -> str:  # pragma: no cover - trivial
        return "<END_NODE>"

    def __str__(self) -> str:  # pragma: no cover - trivial
        return "[*]"


END_NODE = _EndNodeSentinel()
"""Sentinel marking the synthetic ``__END__`` node in :class:`TopologyGraph`."""

NodeTyping = Union[State, _EndNodeSentinel]
NodeKey = Tuple[str, ...]
"""Hashable key type. Either a state path tuple or the END sentinel tuple."""

END_KEY: NodeKey = ("__END__",)
"""Reserved :func:`node_key` value for :data:`END_NODE`."""


def node_key(node: NodeTyping) -> NodeKey:
    """
    Hashable identifier for a graph node.

    :param node: A :class:`pyfcstm.model.State` instance or :data:`END_NODE`.
    :type node: Union[State, _EndNodeSentinel]
    :return: ``("__END__",)`` for :data:`END_NODE`, otherwise the state's
        :attr:`State.path` tuple.
    :rtype: Tuple[str, ...]
    """
    if node is END_NODE:
        return END_KEY
    return tuple(node.path)


def format_node(node: NodeTyping) -> str:
    """
    Render a graph node as a human-readable dotted path or ``[*]``.

    :param node: A leaf state or :data:`END_NODE`.
    :type node: Union[State, _EndNodeSentinel]
    :return: Dotted state path (``"Root.A"``) or ``"[*]"``.
    :rtype: str
    """
    if node is END_NODE:
        return "[*]"
    return ".".join(node.path)


@dataclass(frozen=True)
class MacroEdge:
    """
    One directed edge in the leaf-only macro graph.

    A macro edge collapses one simulator-level transition firing
    (potentially involving several exit/entry hops across the state
    hierarchy) into a single ``source_leaf -> target_leaf_or_END`` arrow.

    :param source: Source leaf state.
    :type source: State
    :param target: Target leaf state, or :data:`END_NODE`.
    :type target: Union[State, _EndNodeSentinel]
    :param label: Human-readable label for diagnostics (e.g.
        ``"Root.A -> Root.B"`` or ``"Root.A -> [*]"``). Not used by the
        algorithms themselves.
    :type label: str
    """

    source: State
    target: NodeTyping
    label: str


@dataclass(frozen=True)
class TopologyGraph:
    """
    Immutable view over the flattened leaf-only macro graph.

    Nodes are the source machine's leaf states plus :data:`END_NODE`. All
    indexed lookups go through :func:`node_key`; the dataclass also keeps
    a ``key -> node`` map so callers can recover :class:`State` objects
    when iterating adjacency.

    :param leaves: Tuple of all leaf states in walk order.
    :type leaves: Tuple[State, ...]
    :param initial_leaves: Initial leaves obtained from the root's init
        chain (with branching when intermediate composites have multiple
        ``[*] -> X`` transitions).
    :type initial_leaves: Tuple[State, ...]
    :param edges: Full edge list, deterministic by traversal order.
    :type edges: Tuple[MacroEdge, ...]
    :param adjacency: ``key -> tuple(key, ...)`` map. Successor tuples
        preserve edge insertion order.
    :type adjacency: dict
    :param node_by_key: ``key -> node`` map used to recover the
        :class:`State` (or :data:`END_NODE`) from a key produced by
        :func:`node_key`.
    :type node_by_key: dict
    :param warnings: Diagnostics emitted during graph construction.
    :type warnings: Tuple[str, ...]
    """

    leaves: Tuple[State, ...]
    initial_leaves: Tuple[State, ...]
    edges: Tuple[MacroEdge, ...]
    adjacency: Dict[NodeKey, Tuple[NodeKey, ...]]
    node_by_key: Dict[NodeKey, NodeTyping]
    warnings: Tuple[str, ...] = field(default_factory=tuple)

    def successors(self, node: NodeTyping) -> Tuple[NodeTyping, ...]:
        """
        Return outgoing successors of *node*.

        :param node: A leaf state or :data:`END_NODE`.
        :type node: Union[State, _EndNodeSentinel]
        :return: Tuple of successor nodes in edge-insertion order. Empty
            when the node is :data:`END_NODE` or has no outgoing edges.
        :rtype: Tuple[Union[State, _EndNodeSentinel], ...]
        """
        keys = self.adjacency.get(node_key(node), ())
        return tuple(self.node_by_key[k] for k in keys)

    def node_for_key(self, key: NodeKey) -> NodeTyping:
        """
        Recover the original node object from a :func:`node_key` value.

        :param key: A key produced by :func:`node_key`.
        :type key: Tuple[str, ...]
        :return: The corresponding :class:`State` instance or
            :data:`END_NODE`.
        :rtype: Union[State, _EndNodeSentinel]
        :raises KeyError: If *key* was never registered.
        """
        return self.node_by_key[key]


@dataclass(frozen=True)
class ReachabilityResult:
    """
    Verdict produced by :func:`pyfcstm.topology.check_reachability`.

    :param reachable: ``True`` when *target* is reachable from *source* in
        the macro graph.
    :type reachable: bool
    :param witness_path: One witness path from *source* to *target* as a
        tuple of nodes. ``None`` when ``reachable`` is ``False``.
    :type witness_path: Optional[Tuple[Union[State, _EndNodeSentinel], ...]]
    :param reach_nodes: All nodes reachable from *source*, in BFS
        discovery order.
    :type reach_nodes: Tuple[Union[State, _EndNodeSentinel], ...]
    :param unreach_leaves: All leaves of the source machine not in
        :attr:`reach_nodes`, in walk order. Useful for the dead-state
        diagnostic from section 3.4.3 step 11 of the design report.
    :type unreach_leaves: Tuple[State, ...]
    :param source: Resolved source leaf used for the query.
    :type source: State
    :param target: Resolved target leaf used for the query.
    :type target: State
    """

    reachable: bool
    witness_path: Optional[Tuple[NodeTyping, ...]]
    reach_nodes: Tuple[NodeTyping, ...]
    unreach_leaves: Tuple[State, ...]
    source: State
    target: State

    def format_witness(self) -> str:
        """
        Render :attr:`witness_path` as ``A -> B -> ... -> target``.

        :return: Arrow-joined path, or an empty string when no witness.
        :rtype: str
        """
        if not self.witness_path:
            return ""
        return " -> ".join(format_node(n) for n in self.witness_path)


@dataclass(frozen=True)
class FinitenessCounterexample:
    """
    Witness for a finiteness violation.

    A counterexample is either a *deadlock* (reachable non-:data:`END_NODE`
    leaf with no outgoing macro edges) or a *trap cycle* (reachable
    non-trivial SCC that cannot reach :data:`END_NODE`).

    :param kind: ``"deadlock"`` or ``"trap_cycle"``.
    :type kind: Literal["deadlock", "trap_cycle"]
    :param prefix: Path from *source* to the witness node (deadlock leaf)
        or cycle entry (trap cycle).
    :type prefix: Tuple[State, ...]
    :param cycle: For ``"trap_cycle"``, the closed cycle. Empty for
        ``"deadlock"``.
    :type cycle: Tuple[State, ...]
    :param deadlock_leaf: For ``"deadlock"``, the offending leaf.
        ``None`` for ``"trap_cycle"``.
    :type deadlock_leaf: Optional[State]
    """

    kind: Literal["deadlock", "trap_cycle"]
    prefix: Tuple[State, ...]
    cycle: Tuple[State, ...] = ()
    deadlock_leaf: Optional[State] = None

    def format(self) -> str:
        """
        Render the counterexample as a single arrow-joined line.

        :return: Formatted string. Examples: ``"A -> B -> deadlock(C)"``
            or ``"A -> B -> [cycle: X -> Y -> X]"``.
        :rtype: str
        """
        prefix_txt = " -> ".join(format_node(n) for n in self.prefix)
        if self.kind == "deadlock":
            tail = "deadlock({})".format(format_node(self.deadlock_leaf)) if self.deadlock_leaf is not None else "deadlock"
            return "{} -> {}".format(prefix_txt, tail) if prefix_txt else tail
        cycle_txt = " -> ".join(format_node(n) for n in self.cycle)
        return "{} -> [cycle: {}]".format(prefix_txt, cycle_txt) if prefix_txt else "[cycle: {}]".format(cycle_txt)


@dataclass(frozen=True)
class FinitenessResult:
    """
    Verdict produced by :func:`pyfcstm.topology.check_finiteness`.

    :param finite: ``True`` when every macro path from *source* terminates
        cleanly at :data:`END_NODE`.
    :type finite: bool
    :param counterexample: First-found witness when ``finite`` is
        ``False``; ``None`` otherwise.
    :type counterexample: Optional[FinitenessCounterexample]
    :param source: Resolved source leaf used for the query.
    :type source: State
    :param violating_node_count: Total number of leaves reachable from
        *source* that cannot reach :data:`END_NODE`. Zero when finite.
    :type violating_node_count: int
    """

    finite: bool
    counterexample: Optional[FinitenessCounterexample]
    source: State
    violating_node_count: int = 0


@dataclass(frozen=True)
class InevitabilityCounterexample:
    """
    Witness that *target* is NOT inevitable from *source*.

    Four counterexample kinds:

    * ``"unreachable"`` - *target* is not in ``reach(source)``.
    * ``"alt_end"`` - residual graph (target removed) lets *source* reach
      :data:`END_NODE`.
    * ``"cycle"`` - residual graph contains a reachable non-trivial SCC.
    * ``"deadlock"`` - residual graph contains a reachable non-target
      leaf with out-degree zero.

    :param kind: One of ``"unreachable"``, ``"alt_end"``, ``"cycle"``,
        ``"deadlock"``.
    :type kind: Literal["unreachable", "alt_end", "cycle", "deadlock"]
    :param prefix: Path from *source* to either the terminating node or
        the cycle entry, in residual-graph traversal order.
    :type prefix: Tuple[State, ...]
    :param cycle: Closed cycle for ``"cycle"`` kind; empty otherwise.
    :type cycle: Tuple[State, ...]
    :param terminal: For ``"alt_end"`` / ``"deadlock"``, the terminating
        node. ``None`` for ``"cycle"`` / ``"unreachable"``.
    :type terminal: Optional[Union[State, _EndNodeSentinel]]
    """

    kind: Literal["unreachable", "alt_end", "cycle", "deadlock"]
    prefix: Tuple[State, ...]
    cycle: Tuple[State, ...] = ()
    terminal: Optional[NodeTyping] = None

    def format(self) -> str:
        """
        Render the counterexample as a single arrow-joined line.

        :return: Formatted string varying by :attr:`kind`.
        :rtype: str
        """
        prefix_txt = " -> ".join(format_node(n) for n in self.prefix)
        if self.kind == "alt_end":
            return "{} -> [*]".format(prefix_txt) if prefix_txt else "[*]"
        if self.kind == "deadlock":
            tail = "deadlock({})".format(format_node(self.terminal)) if self.terminal is not None else "deadlock"
            return "{} -> {}".format(prefix_txt, tail) if prefix_txt else tail
        if self.kind == "cycle":
            cycle_txt = " -> ".join(format_node(n) for n in self.cycle)
            return "{} -> [cycle: {}]".format(prefix_txt, cycle_txt) if prefix_txt else "[cycle: {}]".format(cycle_txt)
        return "target unreachable from source: {}".format(prefix_txt) if prefix_txt else "target unreachable from source"


@dataclass(frozen=True)
class InevitabilityResult:
    """
    Verdict produced by :func:`pyfcstm.topology.check_inevitability`.

    :param inevitable: ``True`` when every maximal macro path from
        *source* passes through *target*.
    :type inevitable: bool
    :param counterexample: First-found witness when ``inevitable`` is
        ``False``; ``None`` otherwise.
    :type counterexample: Optional[InevitabilityCounterexample]
    :param source: Resolved source leaf used for the query.
    :type source: State
    :param target: Resolved target leaf used for the query.
    :type target: State
    """

    inevitable: bool
    counterexample: Optional[InevitabilityCounterexample]
    source: State
    target: State


__all__ = [
    "END_KEY",
    "END_NODE",
    "FinitenessCounterexample",
    "FinitenessResult",
    "InevitabilityCounterexample",
    "InevitabilityResult",
    "MacroEdge",
    "NodeKey",
    "NodeTyping",
    "ReachabilityResult",
    "TopologyGraph",
    "format_node",
    "node_key",
]

"""
Topological reachability verification (section 3.4 of the design report).

This module answers "starting from a *source* leaf, can the macro graph
reach a *target* leaf?". The implementation is a plain BFS over
:class:`pyfcstm.topology.TopologyGraph`; guards and variables are ignored.

The module contains:

* :func:`check_reachability` - Public verification entry point.
* :func:`bfs_reach` - Reusable BFS helper that all three algorithm modules
  share.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.topology import check_reachability
    >>> dsl = '''
    ... state Root {
    ...     state A;
    ...     state B;
    ...     [*] -> A;
    ...     A -> B;
    ...     B -> [*];
    ... }
    ... '''
    >>> sm = parse_dsl_node_to_state_machine(
    ...     parse_with_grammar_entry(dsl, 'state_machine_dsl'))
    >>> result = check_reachability(sm, target='Root.B')
    >>> result.reachable
    True
    >>> result.format_witness()
    'Root.A -> Root.B'
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Union

from ..model import State, StateMachine
from .graph import build_topology_graph, resolve_to_leaves
from .types import (
    END_KEY,
    END_NODE,
    NodeKey,
    NodeTyping,
    ReachabilityResult,
    TopologyGraph,
    node_key,
)

__all__ = [
    "bfs_reach",
    "check_reachability",
]


def bfs_reach(
        graph: TopologyGraph,
        sources: Tuple[NodeTyping, ...],
        target: Optional[NodeTyping] = None,
) -> Tuple[Tuple[NodeTyping, ...], Dict[NodeKey, NodeKey]]:
    """
    Run a BFS over *graph* starting from each node in *sources*.

    Returns the discovery-ordered reach tuple and a parent map keyed by
    :func:`pyfcstm.topology.node_key`. When *target* is given and reached,
    BFS stops early (the result is the prefix discovered up to and
    including *target*).

    :param graph: Macro graph view.
    :type graph: TopologyGraph
    :param sources: One or more start nodes.
    :type sources: Tuple[Union[State, _EndNodeSentinel], ...]
    :param target: Optional early-termination target. ``None`` runs BFS
        until exhausted.
    :type target: Optional[Union[State, _EndNodeSentinel]]
    :return: ``(reach_nodes, parents)``. ``parents[key]`` gives the
        predecessor key used to first discover the node; source nodes map
        to themselves.
    :rtype: Tuple[Tuple[Union[State, _EndNodeSentinel], ...], Dict[Tuple[str, ...], Tuple[str, ...]]]
    """
    reach: List[NodeTyping] = []
    seen: Set[NodeKey] = set()
    parents: Dict[NodeKey, NodeKey] = {}
    queue: deque = deque()
    target_key = node_key(target) if target is not None else None
    for src in sources:
        src_key = node_key(src)
        if src_key in seen:
            continue
        seen.add(src_key)
        reach.append(src)
        parents[src_key] = src_key
        queue.append((src_key, src))
    while queue:
        key, _node = queue.popleft()
        if target_key is not None and key == target_key:
            break
        for succ_key in graph.adjacency.get(key, ()):
            if succ_key in seen:
                continue
            seen.add(succ_key)
            succ_node = graph.node_by_key[succ_key]
            reach.append(succ_node)
            parents[succ_key] = key
            queue.append((succ_key, succ_node))
    return tuple(reach), parents


def reconstruct_path(
        graph: TopologyGraph,
        parents: Dict[NodeKey, NodeKey],
        target: NodeTyping,
) -> Tuple[NodeTyping, ...]:
    """
    Walk *parents* backward from *target* to reconstruct a witness path.

    :param graph: Macro graph view used to recover :class:`State` objects
        from keys.
    :type graph: TopologyGraph
    :param parents: Parent map from :func:`bfs_reach`.
    :type parents: Dict[Tuple[str, ...], Tuple[str, ...]]
    :param target: Destination node.
    :type target: Union[State, _EndNodeSentinel]
    :return: Tuple of nodes from source to target inclusive.
    :rtype: Tuple[Union[State, _EndNodeSentinel], ...]
    """
    target_key = node_key(target)
    path_keys: List[NodeKey] = []
    cur = target_key
    seen: Set[NodeKey] = set()
    while True:
        path_keys.append(cur)
        seen.add(cur)
        parent = parents.get(cur)
        if parent is None or parent == cur or parent in seen:
            break
        cur = parent
    path_keys.reverse()
    return tuple(graph.node_by_key[k] for k in path_keys)


def _resolve_state_argument(
        sm: StateMachine,
        value: Union[State, str],
        role: str,
) -> State:
    """
    Normalize a ``State`` or dotted-path string into a concrete state.

    :param sm: State machine the value is interpreted against.
    :type sm: StateMachine
    :param value: Either a :class:`State` from *sm* or a full dotted path.
    :type value: Union[State, str]
    :param role: Role label used in error messages (``"target"`` /
        ``"source"``).
    :type role: str
    :return: Resolved state object.
    :rtype: State
    :raises TypeError: If *value* is not a State or str.
    :raises LookupError: If the path cannot be resolved.
    """
    if isinstance(value, State):
        return value
    if isinstance(value, str):
        return sm.resolve_state(value)
    raise TypeError(
        "{} argument must be a pyfcstm.model.State or a dotted path string, got {!r}".format(
            role, type(value).__name__
        )
    )


def check_reachability(
        sm: StateMachine,
        target: Union[State, str],
        source: Optional[Union[State, str]] = None,
        graph: Optional[TopologyGraph] = None,
) -> ReachabilityResult:
    """
    Check whether *target* is topologically reachable from *source*.

    *target* and *source* may be either leaf or composite states. A
    composite argument is auto-resolved into its initial leaves via
    :func:`pyfcstm.topology.resolve_to_leaves`. A composite *target* is
    "reached" iff any of its initial leaves is reached.

    :param sm: State machine to verify.
    :type sm: StateMachine
    :param target: Target leaf or composite state. Strings are passed
        through :meth:`pyfcstm.model.StateMachine.resolve_state`.
    :type target: Union[State, str]
    :param source: Source leaf or composite state. ``None`` (default) uses
        the root's init chain.
    :type source: Optional[Union[State, str]]
    :param graph: Optional pre-built :class:`TopologyGraph`. Pass to reuse
        across multiple queries on the same machine.
    :type graph: Optional[TopologyGraph]
    :return: Verdict and witness path / unreach diagnostics.
    :rtype: ReachabilityResult
    :raises LookupError: If *source* or *target* cannot be resolved.
    :raises ValueError: If *source* is a composite with no init chain.
    """
    if graph is None:
        graph = build_topology_graph(sm)

    target_state = _resolve_state_argument(sm, target, "target")
    target_leaves = resolve_to_leaves(target_state)
    target_keys: Set[NodeKey] = {node_key(s) for s in target_leaves}

    if source is None:
        source_leaves = graph.initial_leaves
        source_state = source_leaves[0] if source_leaves else sm.root_state
    else:
        source_state = _resolve_state_argument(sm, source, "source")
        source_leaves = resolve_to_leaves(source_state)
    source_repr = source_state if source_state.is_leaf_state else (
        source_leaves[0] if source_leaves else source_state
    )

    reach_nodes, parents = bfs_reach(graph, source_leaves)
    reach_keys = set(parents.keys())

    leaf_keys_in_machine: Set[NodeKey] = {node_key(l) for l in graph.leaves}
    unreach_leaves = tuple(
        l for l in graph.leaves if node_key(l) not in reach_keys
    )

    hit_key = next((k for k in target_keys if k in reach_keys), None)
    if hit_key is not None:
        hit_state = graph.node_by_key[hit_key]
        witness = reconstruct_path(graph, parents, hit_state)
        return ReachabilityResult(
            reachable=True,
            witness_path=witness,
            reach_nodes=reach_nodes,
            unreach_leaves=unreach_leaves,
            source=source_repr,
            target=hit_state if isinstance(hit_state, State) else target_state,
        )

    target_repr = target_leaves[0] if target_leaves else target_state
    return ReachabilityResult(
        reachable=False,
        witness_path=None,
        reach_nodes=reach_nodes,
        unreach_leaves=unreach_leaves,
        source=source_repr,
        target=target_repr,
    )

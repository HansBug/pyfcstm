"""
Topological finiteness verification (section 3.5 of the design report).

The state machine is *finite* from *source* iff every maximal macro path
eventually reaches the synthetic :data:`pyfcstm.topology.END_NODE`. In
pure-topology semantics this is equivalent to two combined conditions on
the induced subgraph ``reach(source)``:

1. The subgraph contains no non-trivial strongly connected component (any
   cycle is a witness of a potential infinite trace, even if the cycle
   has an outgoing escape edge).
2. The subgraph has no leaf with out-degree zero other than
   :data:`END_NODE` (any such leaf is a hard topological deadlock).

Violations are classified into two counterexample geometries:

* **Deadlock**: a leaf in ``reach(source)`` that originally has zero
  outgoing macro edges and is not :data:`END_NODE`.
* **Trap cycle**: a non-trivial SCC reachable from *source*.

Deadlocks are reported first when both kinds are present, since they are
easier for users to read.

The module contains:

* :func:`check_finiteness` - Public verification entry point.
* Internal helpers: backward BFS, Tarjan SCC, cycle reconstruction.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.topology import check_finiteness
    >>> dsl_ok = '''
    ... state Root {
    ...     state A;
    ...     state B;
    ...     [*] -> A;
    ...     A -> B;
    ...     B -> [*];
    ... }
    ... '''
    >>> sm = parse_dsl_node_to_state_machine(
    ...     parse_with_grammar_entry(dsl_ok, 'state_machine_dsl'))
    >>> check_finiteness(sm).finite
    True
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Union

from ..model import State, StateMachine
from .graph import build_topology_graph, resolve_to_leaves
from .reachability import _resolve_state_argument, bfs_reach
from .types import (
    END_KEY,
    END_NODE,
    FinitenessCounterexample,
    FinitenessResult,
    NodeKey,
    NodeTyping,
    TopologyGraph,
    node_key,
)

__all__ = [
    "check_finiteness",
]


def _backward_reach_from_end(graph: TopologyGraph) -> Set[NodeKey]:
    """
    Compute the set of node keys that can reach :data:`END_NODE`.

    Builds the reverse adjacency on the fly and BFS-walks it from
    ``END_KEY``.

    :param graph: Macro graph view.
    :type graph: TopologyGraph
    :return: Set of keys that have at least one macro path to
        :data:`END_NODE` (including ``END_KEY`` itself).
    :rtype: Set[Tuple[str, ...]]
    """
    reverse_adj: Dict[NodeKey, List[NodeKey]] = {}
    for src_key, succ_keys in graph.adjacency.items():
        reverse_adj.setdefault(src_key, [])
        for s_key in succ_keys:
            reverse_adj.setdefault(s_key, []).append(src_key)
    seen: Set[NodeKey] = {END_KEY}
    queue: deque = deque([END_KEY])
    while queue:
        cur = queue.popleft()
        for pred in reverse_adj.get(cur, ()):
            if pred in seen:
                continue
            seen.add(pred)
            queue.append(pred)
    return seen


def _induced_adjacency(
        graph: TopologyGraph,
        keep: Set[NodeKey],
) -> Dict[NodeKey, Tuple[NodeKey, ...]]:
    """
    Induce *graph*'s adjacency onto *keep*.

    :param graph: Macro graph view.
    :type graph: TopologyGraph
    :param keep: Subset of keys to keep.
    :type keep: Set[Tuple[str, ...]]
    :return: New adjacency map with edges pointing outside *keep* pruned.
    :rtype: Dict[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]
    """
    induced: Dict[NodeKey, Tuple[NodeKey, ...]] = {}
    for key in keep:
        succs = graph.adjacency.get(key, ())
        induced[key] = tuple(s for s in succs if s in keep)
    return induced


def _tarjan_scc(
        adjacency: Dict[NodeKey, Tuple[NodeKey, ...]],
        keys_in_order: Tuple[NodeKey, ...],
) -> List[List[NodeKey]]:
    """
    Tarjan's strongly-connected-components algorithm on *adjacency*.

    *keys_in_order* fixes the iteration order so the returned SCCs are
    deterministic regardless of dict ordering.

    :param adjacency: Adjacency map.
    :type adjacency: Dict[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]
    :param keys_in_order: Deterministic key enumeration order.
    :type keys_in_order: Tuple[Tuple[str, ...], ...]
    :return: List of SCCs.
    :rtype: List[List[Tuple[str, ...]]]
    """
    index_counter = [0]
    stack: List[NodeKey] = []
    on_stack: Set[NodeKey] = set()
    indices: Dict[NodeKey, int] = {}
    lowlinks: Dict[NodeKey, int] = {}
    result: List[List[NodeKey]] = []

    def strongconnect(v: NodeKey) -> None:
        indices[v] = index_counter[0]
        lowlinks[v] = index_counter[0]
        index_counter[0] += 1
        stack.append(v)
        on_stack.add(v)
        for w in adjacency.get(v, ()):
            if w not in indices:
                strongconnect(w)
                lowlinks[v] = min(lowlinks[v], lowlinks[w])
            elif w in on_stack:
                lowlinks[v] = min(lowlinks[v], indices[w])
        if lowlinks[v] == indices[v]:
            component: List[NodeKey] = []
            while True:
                w = stack.pop()
                on_stack.discard(w)
                component.append(w)
                if w == v:
                    break
            result.append(component)

    for key in keys_in_order:
        if key not in indices:
            strongconnect(key)
    return result


def _is_nontrivial_scc(
        component: List[NodeKey],
        adjacency: Dict[NodeKey, Tuple[NodeKey, ...]],
) -> bool:
    """
    Return ``True`` when *component* contains at least one edge.

    Singleton SCCs are non-trivial iff they have a self-loop.

    :param component: One SCC from :func:`_tarjan_scc`.
    :type component: List[Tuple[str, ...]]
    :param adjacency: Adjacency map for self-loop detection.
    :type adjacency: Dict[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]
    :return: ``True`` for non-trivial SCC, ``False`` otherwise.
    :rtype: bool
    """
    if len(component) >= 2:
        return True
    only = component[0]
    return only in adjacency.get(only, ())


def _reconstruct_cycle_in_scc(
        scc_keys: Set[NodeKey],
        adjacency: Dict[NodeKey, Tuple[NodeKey, ...]],
        entry: NodeKey,
) -> Tuple[NodeKey, ...]:
    """
    Find one closed cycle inside *scc_keys* starting and ending at *entry*.

    Runs a DFS restricted to *scc_keys*. The first back edge onto *entry*
    yields a cycle. Falls back to ``(entry,)`` if no cycle is reconstructed
    (should not happen for non-trivial SCCs).

    :param scc_keys: Keys belonging to a non-trivial SCC.
    :type scc_keys: Set[Tuple[str, ...]]
    :param adjacency: Adjacency map for traversal.
    :type adjacency: Dict[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]
    :param entry: Entry node key.
    :type entry: Tuple[str, ...]
    :return: Cycle ``(entry, v1, ..., entry)``.
    :rtype: Tuple[Tuple[str, ...], ...]
    """
    path: List[NodeKey] = [entry]
    on_path: Set[NodeKey] = {entry}
    found: List[NodeKey] = []

    def dfs(node: NodeKey) -> bool:
        for succ in adjacency.get(node, ()):
            if succ not in scc_keys:
                continue
            if succ == entry and len(path) >= 1:
                found.extend(path + [entry])
                return True
            if succ in on_path:
                continue
            path.append(succ)
            on_path.add(succ)
            if dfs(succ):
                return True
            on_path.discard(succ)
            path.pop()
        return False

    dfs(entry)
    if found:
        return tuple(found)
    return (entry,)


def _path_to_key(
        parents: Dict[NodeKey, NodeKey],
        key: NodeKey,
) -> Tuple[NodeKey, ...]:
    """
    Reconstruct a BFS prefix from any source up to *key*.

    :param parents: Parent map from :func:`bfs_reach`.
    :type parents: Dict[Tuple[str, ...], Tuple[str, ...]]
    :param key: Destination node key.
    :type key: Tuple[str, ...]
    :return: Path of keys, source-first.
    :rtype: Tuple[Tuple[str, ...], ...]
    """
    path: List[NodeKey] = []
    cur = key
    seen: Set[NodeKey] = set()
    while True:
        path.append(cur)
        seen.add(cur)
        parent = parents.get(cur)
        if parent is None or parent == cur or parent in seen:
            break
        cur = parent
    path.reverse()
    return tuple(path)


def _keys_to_states(
        graph: TopologyGraph,
        keys: Tuple[NodeKey, ...],
) -> Tuple[State, ...]:
    """
    Convert a tuple of keys to a tuple of :class:`State` objects.

    Filters out the END sentinel and any keys that do not resolve to a
    :class:`State`.

    :param graph: Macro graph view.
    :type graph: TopologyGraph
    :param keys: Tuple of node keys.
    :type keys: Tuple[Tuple[str, ...], ...]
    :return: Tuple of :class:`State` objects in the same order.
    :rtype: Tuple[State, ...]
    """
    out: List[State] = []
    for k in keys:
        n = graph.node_by_key.get(k)
        if isinstance(n, State):
            out.append(n)
    return tuple(out)


def check_finiteness(
        sm: StateMachine,
        source: Optional[Union[State, str]] = None,
        graph: Optional[TopologyGraph] = None,
) -> FinitenessResult:
    """
    Verify that every macro path from *source* reaches :data:`END_NODE`.

    Reports the first-found counterexample (deadlock leaf or trap cycle)
    plus a total violating-leaf count. Deterministic for a given *graph*
    (key iteration order follows :attr:`TopologyGraph.leaves` walk order).

    :param sm: State machine to verify.
    :type sm: StateMachine
    :param source: Source leaf or composite. ``None`` defaults to the
        root's init chain. Composite sources are resolved through
        :func:`pyfcstm.topology.resolve_to_leaves`.
    :type source: Optional[Union[State, str]]
    :param graph: Optional pre-built :class:`TopologyGraph`.
    :type graph: Optional[TopologyGraph]
    :return: Verdict with optional counterexample.
    :rtype: FinitenessResult
    :raises LookupError: If *source* cannot be resolved.
    :raises ValueError: If *source* is a composite with no init chain.

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.topology import check_finiteness
        >>> dsl_bad = '''
        ... state Root {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B;
        ...     B -> A;
        ... }
        ... '''
        >>> sm = parse_dsl_node_to_state_machine(
        ...     parse_with_grammar_entry(dsl_bad, 'state_machine_dsl'))
        >>> r = check_finiteness(sm)
        >>> r.finite
        False
        >>> r.counterexample.kind
        'trap_cycle'
    """
    if graph is None:
        graph = build_topology_graph(sm)

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

    # Induced subgraph of reach(source).
    induced = _induced_adjacency(graph, reach_keys)
    reach_ordered = tuple(
        node_key(leaf) for leaf in graph.leaves if node_key(leaf) in reach_keys
    )

    # Real deadlocks: leaves in reach(source) that have zero out-edges in
    # the ORIGINAL graph (not just the induced one — induced has the same
    # out-degree because we induce on reach_keys which is closed under
    # successors).
    deadlocks = tuple(
        k for k in reach_ordered
        if not graph.adjacency.get(k, ()) and k != END_KEY
    )

    # Non-trivial SCCs reachable from source.
    sccs = _tarjan_scc(induced, reach_ordered)
    nontrivial_components = [
        c for c in sccs if _is_nontrivial_scc(c, induced)
    ]

    violating_keys: Set[NodeKey] = set(deadlocks)
    for component in nontrivial_components:
        violating_keys.update(component)
    violating_keys.discard(END_KEY)

    if not violating_keys:
        return FinitenessResult(
            finite=True,
            counterexample=None,
            source=source_repr,
            violating_node_count=0,
        )

    # Prefer deadlock reporting first (easier to read for users).
    if deadlocks:
        k = deadlocks[0]
        prefix_keys = _path_to_key(parents, k)
        prefix_states = _keys_to_states(graph, prefix_keys[:-1])
        leaf = graph.node_by_key[k]
        cex = FinitenessCounterexample(
            kind="deadlock",
            prefix=prefix_states,
            deadlock_leaf=leaf if isinstance(leaf, State) else None,
        )
        return FinitenessResult(
            finite=False,
            counterexample=cex,
            source=source_repr,
            violating_node_count=len(violating_keys),
        )

    # Otherwise report the first non-trivial SCC.
    component = nontrivial_components[0]
    scc_keys: Set[NodeKey] = set(component)
    entry = next(k for k in reach_ordered if k in scc_keys)
    prefix_keys = _path_to_key(parents, entry)
    prefix_states = _keys_to_states(graph, prefix_keys[:-1])
    cycle_keys = _reconstruct_cycle_in_scc(scc_keys, induced, entry)
    cycle_states = _keys_to_states(graph, cycle_keys)
    return FinitenessResult(
        finite=False,
        counterexample=FinitenessCounterexample(
            kind="trap_cycle",
            prefix=prefix_states,
            cycle=cycle_states,
        ),
        source=source_repr,
        violating_node_count=len(violating_keys),
    )

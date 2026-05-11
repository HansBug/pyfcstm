"""
Topological inevitability verification (section 3.6 of the design report).

The state machine *inevitably* reaches *target* from *source* iff every
maximal macro path starting at *source* passes through *target*. The
implementation follows the residual-graph reasoning from section 3.6.2,
with reinforcement clauses tailored to the FCSTM topology:

1. Compute ``R = reach(source)``.
2. If *target* is not in ``R``, report ``unreachable``.
3. Build the residual subgraph ``G_R'`` by inducing on ``R`` and deleting
   every target leaf.
4. In ``G_R'``, look for any of three target-avoiding witnesses:

   * ``alt_end`` - :data:`pyfcstm.topology.END_NODE` is reachable from
     *source*.
   * ``cycle`` - a non-trivial SCC is reachable from *source*.
   * ``deadlock`` - a non-target leaf with out-degree zero is reachable.

5. If none of the above exist, *target* is inevitable.

The cycle / deadlock clauses extend the design report's bare "is END
reachable in residual?" check, because the FCSTM macro graph has exactly
one legitimate terminal node (:data:`END_NODE`). Without those clauses,
trap regions would be misreported as inevitable.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.topology import check_inevitability
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
    >>> check_inevitability(sm, target='Root.B').inevitable
    True
"""

from __future__ import annotations

from collections import deque
from typing import Dict, List, Optional, Set, Tuple, Union

from ..model import State, StateMachine
from .graph import build_topology_graph, resolve_to_leaves
from .reachability import _resolve_state_argument, bfs_reach
from .finiteness import (
    _is_nontrivial_scc,
    _keys_to_states,
    _path_to_key,
    _reconstruct_cycle_in_scc,
    _tarjan_scc,
)
from .types import (
    END_KEY,
    END_NODE,
    InevitabilityCounterexample,
    InevitabilityResult,
    NodeKey,
    NodeTyping,
    TopologyGraph,
    node_key,
)

__all__ = [
    "check_inevitability",
]


def _residual_adjacency(
        graph: TopologyGraph,
        reach_keys: Set[NodeKey],
        removed: Set[NodeKey],
) -> Dict[NodeKey, Tuple[NodeKey, ...]]:
    """
    Build the residual subgraph adjacency by inducing on *reach_keys* and
    excising every key in *removed*.

    :param graph: Macro graph view.
    :type graph: TopologyGraph
    :param reach_keys: Keys of nodes reachable from the verification
        source.
    :type reach_keys: Set[Tuple[str, ...]]
    :param removed: Keys deleted from the induced subgraph (target's
        leaves).
    :type removed: Set[Tuple[str, ...]]
    :return: Residual adjacency map.
    :rtype: Dict[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]
    """
    induced: Dict[NodeKey, Tuple[NodeKey, ...]] = {}
    for k in reach_keys:
        if k in removed:
            continue
        succs = graph.adjacency.get(k, ())
        induced[k] = tuple(s for s in succs if s in reach_keys and s not in removed)
    return induced


def _residual_reach(
        adjacency: Dict[NodeKey, Tuple[NodeKey, ...]],
        sources: Tuple[NodeKey, ...],
) -> Tuple[Set[NodeKey], Dict[NodeKey, NodeKey]]:
    """
    BFS over a residual adjacency map.

    :param adjacency: Residual adjacency.
    :type adjacency: Dict[Tuple[str, ...], Tuple[Tuple[str, ...], ...]]
    :param sources: BFS source keys (must be present in *adjacency*).
    :type sources: Tuple[Tuple[str, ...], ...]
    :return: ``(reach_keys, parents)`` mirroring :func:`bfs_reach`'s
        shape.
    :rtype: Tuple[Set[Tuple[str, ...]], Dict[Tuple[str, ...], Tuple[str, ...]]]
    """
    seen: Set[NodeKey] = set()
    parents: Dict[NodeKey, NodeKey] = {}
    queue: deque = deque()
    for src in sources:
        if src in seen or src not in adjacency:
            continue
        seen.add(src)
        parents[src] = src
        queue.append(src)
    while queue:
        cur = queue.popleft()
        for succ in adjacency.get(cur, ()):
            if succ in seen:
                continue
            seen.add(succ)
            parents[succ] = cur
            queue.append(succ)
    return seen, parents


def check_inevitability(
        sm: StateMachine,
        target: Union[State, str],
        source: Optional[Union[State, str]] = None,
        graph: Optional[TopologyGraph] = None,
) -> InevitabilityResult:
    """
    Check whether every macro path from *source* passes through *target*.

    Refer to the module docstring for the full residual-graph algorithm.
    Guards and variable semantics are ignored.

    :param sm: State machine to verify.
    :type sm: StateMachine
    :param target: Target leaf or composite to test for inevitability.
    :type target: Union[State, str]
    :param source: Source leaf or composite. ``None`` defaults to the
        root's init chain.
    :type source: Optional[Union[State, str]]
    :param graph: Optional pre-built :class:`TopologyGraph`.
    :type graph: Optional[TopologyGraph]
    :return: Verdict with optional counterexample.
    :rtype: InevitabilityResult
    :raises LookupError: If *source* or *target* cannot be resolved.
    :raises ValueError: If *source* is a composite with no init chain.

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.topology import check_inevitability
        >>> dsl = '''
        ... state Root {
        ...     state A;
        ...     state B;
        ...     state C;
        ...     [*] -> A;
        ...     A -> B;
        ...     A -> C;
        ...     B -> [*];
        ...     C -> [*];
        ... }
        ... '''
        >>> sm = parse_dsl_node_to_state_machine(
        ...     parse_with_grammar_entry(dsl, 'state_machine_dsl'))
        >>> check_inevitability(sm, target='Root.B').inevitable
        False
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
    target_repr = target_leaves[0] if target_leaves else target_state

    reach_nodes, reach_parents = bfs_reach(graph, source_leaves)
    reach_keys = set(reach_parents.keys())

    if not (target_keys & reach_keys):
        # Target unreachable from source.
        sample_key: Optional[NodeKey] = (
            END_KEY if END_KEY in reach_keys else None
        )
        if sample_key is None:
            source_key_set = {node_key(s) for s in source_leaves}
            sample_key = next(
                (k for k in reach_keys if k not in source_key_set),
                node_key(source_leaves[0]) if source_leaves else None,
            )
        prefix: Tuple[State, ...] = ()
        if sample_key is not None:
            keys_path = _path_to_key(reach_parents, sample_key)
            prefix = _keys_to_states(graph, keys_path)
        cex = InevitabilityCounterexample(
            kind="unreachable",
            prefix=prefix,
            terminal=None,
        )
        return InevitabilityResult(
            inevitable=False,
            counterexample=cex,
            source=source_repr,
            target=target_repr,
        )

    removed: Set[NodeKey] = target_keys & reach_keys
    residual = _residual_adjacency(graph, reach_keys, removed)

    source_keys = tuple(node_key(s) for s in source_leaves)
    live_sources = tuple(k for k in source_keys if k in residual)
    if not live_sources:
        # Every source IS a target leaf → target trivially inevitable.
        return InevitabilityResult(
            inevitable=True,
            counterexample=None,
            source=source_repr,
            target=target_repr,
        )

    res_reach, res_parents = _residual_reach(residual, live_sources)

    if END_KEY in res_reach:
        path = _path_to_key(res_parents, END_KEY)
        prefix = _keys_to_states(graph, path)
        cex = InevitabilityCounterexample(
            kind="alt_end",
            prefix=prefix,
            terminal=END_NODE,
        )
        return InevitabilityResult(
            inevitable=False,
            counterexample=cex,
            source=source_repr,
            target=target_repr,
        )

    # Deadlock: a non-target leaf reachable in residual that ALSO had
    # out-degree zero in the ORIGINAL graph. A residual deadlock that only
    # appeared because target removal stripped all its out-edges is *not*
    # a counterexample — it actually witnesses inevitability (every
    # original move from that node had to pass through target).
    nodes_in_order = tuple(node_key(l) for l in graph.leaves if node_key(l) in res_reach)
    for k in nodes_in_order:
        if residual.get(k, ()):
            continue
        if graph.adjacency.get(k, ()):
            # Had out-edges originally; emptied only by target removal.
            continue
        path = _path_to_key(res_parents, k)
        prefix = _keys_to_states(graph, path[:-1])
        leaf = graph.node_by_key.get(k)
        cex = InevitabilityCounterexample(
            kind="deadlock",
            prefix=prefix,
            terminal=leaf,
        )
        return InevitabilityResult(
            inevitable=False,
            counterexample=cex,
            source=source_repr,
            target=target_repr,
        )

    # Cycle: any reachable non-trivial SCC in residual.
    sccs = _tarjan_scc(residual, nodes_in_order)
    for component in sccs:
        if not _is_nontrivial_scc(component, residual):
            continue
        scc_keys: Set[NodeKey] = set(component)
        if not (scc_keys & res_reach):
            continue
        entry = next(k for k in nodes_in_order if k in scc_keys)
        path = _path_to_key(res_parents, entry)
        prefix = _keys_to_states(graph, path[:-1] if path else ())
        cycle_keys = _reconstruct_cycle_in_scc(scc_keys, residual, entry)
        cycle_states = _keys_to_states(graph, cycle_keys)
        cex = InevitabilityCounterexample(
            kind="cycle",
            prefix=prefix,
            cycle=cycle_states,
        )
        return InevitabilityResult(
            inevitable=False,
            counterexample=cex,
            source=source_repr,
            target=target_repr,
        )

    return InevitabilityResult(
        inevitable=True,
        counterexample=None,
        source=source_repr,
        target=target_repr,
    )

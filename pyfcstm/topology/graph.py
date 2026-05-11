"""
Macro graph construction for topological verification.

This module flattens a hierarchical :class:`pyfcstm.model.StateMachine` into a
*leaf-only* directed graph (:class:`pyfcstm.topology.TopologyGraph`) that the
three verification algorithms operate on.

Construction rules:

* **Nodes** are the state machine's leaf states (both ``stoppable`` and
  ``pseudo``) plus the synthetic :data:`pyfcstm.topology.END_NODE` sentinel
  representing legitimate runtime termination via ``Root -> [*]``.

* **Initial leaves** are obtained by descending the root's
  :attr:`pyfcstm.model.State.init_transitions` chain. When an intermediate
  composite carries multiple ``[*] -> X`` declarations, all branches are
  enumerated (topological over-approximation: any init could fire in the
  absence of guard information).

* **Macro edges** are produced one per ``Transition`` declaration that is
  reachable from a leaf via the simulator's transition-resolution chain:

  - ``L -> SiblingLeaf``: direct macro edge.
  - ``L -> SiblingComposite``: one macro edge per leaf yielded by descending
    the composite's init chain.
  - ``L -> [*]``: bubble up to ``L.parent``; recursively apply the same
    rules. Reaches :data:`pyfcstm.topology.END_NODE` only when the bubble
    hits the root's synthetic ``Root -> [*]`` exit transition.

* **Forced transitions** (``!State``, ``!*``) are already expanded by the DSL
  listener into ordinary transitions, so no special handling is needed at
  this layer.

* **Off-cliff edges**: if ``L -> [*]`` bubbles up to a non-root composite
  ``P`` whose :attr:`transitions_from` is empty, no macro edge is emitted
  for that chain. A diagnostic is appended to
  :attr:`TopologyGraph.warnings`.

The module contains:

* :func:`build_topology_graph` - Top-level entry that returns a
  :class:`TopologyGraph` for a parsed :class:`StateMachine`.
* :func:`resolve_to_leaves` - Init-chain descent helper, also used by
  the three algorithm modules.

.. note::

   The macro graph deliberately ignores guards, events, and variable
   semantics. Every declared transition is treated as a possible move. This
   matches the design intent of sections 3.4-3.6 of the formal
   verification report.
"""

from __future__ import annotations

from typing import Dict, List, Set, Tuple

from ..dsl import EXIT_STATE, INIT_STATE
from ..model import State, StateMachine, Transition
from .types import (
    END_KEY,
    END_NODE,
    MacroEdge,
    NodeKey,
    NodeTyping,
    TopologyGraph,
    node_key,
)

__all__ = [
    "build_topology_graph",
    "resolve_to_leaves",
]


def resolve_to_leaves(state: State) -> Tuple[State, ...]:
    """
    Enumerate every leaf reachable by descending *state*'s init chain.

    For a leaf input, returns ``(state,)``. For a composite input, walks
    ``state.init_transitions`` and recurses into every target child. When
    no init transitions are declared but the state has substates, raises
    :exc:`ValueError`.

    :param state: A leaf or composite state.
    :type state: State
    :return: Tuple of leaves in declaration order, without duplicates.
    :rtype: Tuple[State, ...]
    :raises ValueError: If *state* is a composite with no declared init
        transitions, which would make the initial configuration undefined.
    """
    seen: List[State] = []
    seen_keys: Set[NodeKey] = set()
    _descend_init_chain(state, seen, seen_keys, _visiting=set())
    return tuple(seen)


def _descend_init_chain(
        state: State,
        out: List[State],
        out_keys: Set[NodeKey],
        _visiting: Set[NodeKey],
) -> None:
    """
    Recursive helper for :func:`resolve_to_leaves`.

    Appends every newly discovered leaf to *out* (deduplicated via
    *out_keys*) and uses *_visiting* to defend against cyclic init chains.

    :param state: Current state in the descent.
    :type state: State
    :param out: Mutable output list of leaves in discovery order.
    :type out: List[State]
    :param out_keys: Companion set used to deduplicate *out*.
    :type out_keys: Set[Tuple[str, ...]]
    :param _visiting: Set of composite state keys currently on the descent
        stack; short-circuits cyclic init chains defensively.
    :type _visiting: Set[Tuple[str, ...]]
    """
    key = node_key(state)
    if state.is_leaf_state:
        if key not in out_keys:
            out_keys.add(key)
            out.append(state)
        return
    if key in _visiting:
        return
    inits = state.init_transitions
    if not inits:
        raise ValueError(
            "Composite state {!r} has no init transition declared; "
            "cannot determine its initial leaf.".format(".".join(state.path))
        )
    next_visiting = _visiting | {key}
    for transition in inits:
        target_name = transition.to_state
        if target_name is EXIT_STATE or target_name is INIT_STATE:
            continue
        child = state.substates.get(target_name)
        if child is None:
            continue
        _descend_init_chain(child, out, out_keys, next_visiting)


def build_topology_graph(sm: StateMachine) -> TopologyGraph:
    """
    Flatten *sm* into a leaf-only macro graph.

    Walks every leaf state of *sm* and enumerates each leaf's outgoing macro
    edges by following the simulator's transition-resolution chain in the
    absence of guards/events.

    :param sm: Parsed state machine.
    :type sm: StateMachine
    :return: Flattened macro graph view.
    :rtype: TopologyGraph
    :raises ValueError: If any reachable composite state has no init
        transitions.

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.topology import build_topology_graph
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
        >>> g = build_topology_graph(sm)
        >>> [l.name for l in g.initial_leaves]
        ['A']
        >>> sorted(e.label for e in g.edges)
        ['Root.A -> Root.B', 'Root.B -> [*]']
    """
    leaves = tuple(s for s in sm.root_state.walk_states() if s.is_leaf_state)
    initial_leaves = resolve_to_leaves(sm.root_state)

    node_by_key: Dict[NodeKey, NodeTyping] = {END_KEY: END_NODE}
    for leaf in leaves:
        node_by_key.setdefault(node_key(leaf), leaf)

    edges: List[MacroEdge] = []
    warnings: List[str] = []
    for leaf in leaves:
        _emit_edges_for_leaf(leaf, edges, warnings)

    adjacency: Dict[NodeKey, List[NodeKey]] = {END_KEY: []}
    for leaf in leaves:
        adjacency.setdefault(node_key(leaf), [])
    for edge in edges:
        src_key = node_key(edge.source)
        tgt_key = node_key(edge.target)
        adjacency.setdefault(src_key, []).append(tgt_key)
        # Defensive: ensure node_by_key has every edge endpoint.
        if isinstance(edge.target, State):
            node_by_key.setdefault(tgt_key, edge.target)

    frozen_adj: Dict[NodeKey, Tuple[NodeKey, ...]] = {
        k: tuple(v) for k, v in adjacency.items()
    }

    return TopologyGraph(
        leaves=leaves,
        initial_leaves=initial_leaves,
        edges=tuple(edges),
        adjacency=frozen_adj,
        node_by_key=node_by_key,
        warnings=tuple(warnings),
    )


def _emit_edges_for_leaf(
        leaf: State,
        out_edges: List[MacroEdge],
        out_warnings: List[str],
) -> None:
    """
    Enumerate every outgoing macro edge from *leaf* and append to
    *out_edges*.

    Iterates ``leaf.transitions_from`` first. Each transition is either a
    direct sibling target (Case A) or a ``[*]`` exit that bubbles up
    (Case B). Sibling composites are resolved through
    :func:`resolve_to_leaves`.

    :param leaf: The macro-graph source leaf to enumerate.
    :type leaf: State
    :param out_edges: Mutable output list to which discovered edges are
        appended in declaration order.
    :type out_edges: List[MacroEdge]
    :param out_warnings: Mutable diagnostic list; receives one entry per
        off-cliff exit chain that gets dropped.
    :type out_warnings: List[str]
    """
    if leaf.is_root_state:
        # Single-state machine: root is itself the only leaf.
        out_edges.append(MacroEdge(
            source=leaf,
            target=END_NODE,
            label="{} -> [*]".format(".".join(leaf.path)),
        ))
        return

    for transition in leaf.transitions_from:
        _emit_edges_for_transition(
            origin=leaf,
            current=leaf,
            transition=transition,
            out_edges=out_edges,
            out_warnings=out_warnings,
            _bubble_stack=set(),
        )


def _emit_edges_for_transition(
        origin: State,
        current: State,
        transition: Transition,
        out_edges: List[MacroEdge],
        out_warnings: List[str],
        _bubble_stack: Set[NodeKey],
) -> None:
    """
    Translate one ``Transition`` declared on/from *current* into macro
    edges from *origin*.

    Three cases:

    1. *transition*.to_state is :data:`pyfcstm.dsl.EXIT_STATE` and *current*
       is root: emit ``origin -> END_NODE``.
    2. *transition*.to_state is :data:`pyfcstm.dsl.EXIT_STATE` and *current*
       is non-root: bubble up via :func:`_emit_edges_from_exit`.
    3. *transition*.to_state is a sibling state name under
       ``current.parent``: resolve to landing leaves via
       :func:`resolve_to_leaves` and emit one macro edge per landing.

    :param origin: The leaf that owns the macro edges being emitted.
    :type origin: State
    :param current: Current state in the bubble-up chain.
    :type current: State
    :param transition: The DSL transition being interpreted.
    :type transition: Transition
    :param out_edges: Mutable output list.
    :type out_edges: List[MacroEdge]
    :param out_warnings: Mutable diagnostic list.
    :type out_warnings: List[str]
    :param _bubble_stack: Set of state keys already on the bubble chain.
    :type _bubble_stack: Set[Tuple[str, ...]]
    """
    to_state = transition.to_state
    if to_state is EXIT_STATE:
        if current.is_root_state:
            out_edges.append(MacroEdge(
                source=origin,
                target=END_NODE,
                label="{} -> [*]".format(".".join(origin.path)),
            ))
            return
        _emit_edges_from_exit(origin, current, out_edges, out_warnings, _bubble_stack)
        return

    if to_state is INIT_STATE:  # defensive: not a legal to_state
        return

    parent = current.parent
    if parent is None:  # defensive
        return
    sibling = parent.substates.get(to_state)
    if sibling is None:
        out_warnings.append(
            "Transition {origin} via {label!r} references unknown sibling {tgt!r}; edge dropped.".format(
                origin=".".join(origin.path),
                label="{} -> {}".format(".".join(current.path), to_state),
                tgt=to_state,
            )
        )
        return

    try:
        landings = resolve_to_leaves(sibling)
    except ValueError as exc:
        out_warnings.append(
            "Transition {origin} -> {tgt}: composite has no init chain ({msg}); edge dropped.".format(
                origin=".".join(origin.path),
                tgt=".".join(sibling.path),
                msg=str(exc),
            )
        )
        return

    if not landings:
        out_warnings.append(
            "Transition {origin} -> {tgt}: composite resolved to no leaf; edge dropped.".format(
                origin=".".join(origin.path),
                tgt=".".join(sibling.path),
            )
        )
        return

    for landing in landings:
        out_edges.append(MacroEdge(
            source=origin,
            target=landing,
            label="{} -> {}".format(".".join(origin.path), ".".join(landing.path)),
        ))


def _emit_edges_from_exit(
        origin: State,
        current: State,
        out_edges: List[MacroEdge],
        out_warnings: List[str],
        _bubble_stack: Set[NodeKey],
) -> None:
    """
    Handle ``current -> [*]`` by bubbling up to ``current.parent``.

    Once at ``current.parent``, every transition in
    ``current.parent.transitions_from`` is interpreted via
    :func:`_emit_edges_for_transition`. This mirrors what the simulator
    does after a ``[*]`` exit: pop the stack and consult the parent's
    outgoing transitions.

    When ``current.parent`` has no ``transitions_from`` at all (off-cliff
    case), no edge is emitted and one diagnostic is appended.

    :param origin: The leaf that owns the macro edges being emitted.
    :type origin: State
    :param current: The state being exited.
    :type current: State
    :param out_edges: Mutable output list.
    :type out_edges: List[MacroEdge]
    :param out_warnings: Mutable diagnostic list.
    :type out_warnings: List[str]
    :param _bubble_stack: Set of state keys already on the bubble chain.
    :type _bubble_stack: Set[Tuple[str, ...]]
    """
    parent = current.parent
    if parent is None:
        out_edges.append(MacroEdge(
            source=origin,
            target=END_NODE,
            label="{} -> [*]".format(".".join(origin.path)),
        ))
        return
    parent_key = node_key(parent)
    if parent_key in _bubble_stack:
        out_warnings.append(
            "Exit chain from {origin} re-entered {state}; bubble loop broken.".format(
                origin=".".join(origin.path),
                state=".".join(parent.path),
            )
        )
        return
    next_bubble = _bubble_stack | {parent_key}
    parent_transitions = parent.transitions_from
    if not parent_transitions:
        out_warnings.append(
            "Exit chain from {origin} bubbles into {state} which has no transitions_from; "
            "edge dropped (simulator would stall here).".format(
                origin=".".join(origin.path),
                state=".".join(parent.path),
            )
        )
        return
    for transition in parent_transitions:
        _emit_edges_for_transition(
            origin=origin,
            current=parent,
            transition=transition,
            out_edges=out_edges,
            out_warnings=out_warnings,
            _bubble_stack=next_bubble,
        )

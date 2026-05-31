"""Topological verification algorithms for :mod:`pyfcstm.verify`.

The algorithms in this module intentionally stay at the structural layer. They
ignore guard satisfiability, event availability, and runtime variable evolution;
their results therefore describe topological reachability rather than concrete
execution reachability.
"""

from collections import deque
from dataclasses import dataclass
from typing import Deque, Dict, Iterable, List, Optional, Sequence, Set, Tuple

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

from ..dsl import EXIT_STATE, INIT_STATE
from ..model import State, StateMachine

EXIT_ROOT_SINK = "⊥_root"
"""Synthetic sink used for transitions that exit the root state."""


@dataclass(frozen=True)
class LeafLevelGraph:
    """Leaf-level macro graph projected from a hierarchical state machine.

    :param nodes: Dotted paths of leaf states in stable sorted order.
    :type nodes: Tuple[str, ...]
    :param edges: Mapping from each leaf path, and optionally
        :data:`EXIT_ROOT_SINK`, to sorted successor paths.
    :type edges: Dict[str, Tuple[str, ...]]
    """

    nodes: Tuple[str, ...]
    edges: Dict[str, Tuple[str, ...]]


@dataclass(frozen=True)
class FinitenessReport:
    """Result for :func:`topological_finite`.

    :param finite: ``True`` when every root-reachable leaf can reach the root
        exit sink in the topological graph.
    :type finite: bool
    :param counterexamples: Counterexamples as ``('trap_cycle', scc_tuple)`` or
        ``('deadlock', state_path)`` entries.
    :type counterexamples: Tuple[Tuple[Literal['trap_cycle', 'deadlock'], object], ...]
    """

    finite: bool
    counterexamples: Tuple[Tuple[Literal["trap_cycle", "deadlock"], object], ...]


@dataclass(frozen=True)
class InevitabilityReport:
    """Result for :func:`topological_inevitable_terminator`.

    :param inevitable: ``True`` when no root-reachable topological path can stay
        in a cycle or deadlock forever.
    :type inevitable: bool
    :param counterexample_path: Representative non-terminating SCC or deadlock
        path, or ``None`` when :attr:`inevitable` is true.
    :type counterexample_path: Optional[Tuple[str, ...]]
    """

    inevitable: bool
    counterexample_path: Optional[Tuple[str, ...]]


def _state_path(state: State) -> str:
    return ".".join(state.path)


def _leaf_states(machine: StateMachine) -> Tuple[State, ...]:
    return tuple(state for state in machine.walk_states() if state.is_leaf_state)


def _dedupe_sorted(items: Iterable[str]) -> Tuple[str, ...]:
    return tuple(sorted(set(items)))


def _successors(edges: Dict[str, Tuple[str, ...]], node: str) -> Tuple[str, ...]:
    return edges.get(node, tuple())


def _project_target(parent_state: State, target: object) -> Tuple[str, ...]:
    """Project a transition target into leaf-level graph successors."""
    if target is EXIT_STATE:
        if parent_state.is_root_state:
            return (EXIT_ROOT_SINK,)

        parent_parent = parent_state.parent
        assert parent_parent is not None
        projected: List[str] = []
        for transition in parent_state.transitions_from:
            if transition.to_state is EXIT_STATE:
                projected.extend(_project_target(parent_parent, EXIT_STATE))
            else:
                projected.extend(_project_target(parent_parent, transition.to_state))
        return _dedupe_sorted(projected)

    if isinstance(target, str):
        target_state = parent_state.substates[target]
        return _initial_leaf_targets(target_state)

    raise TypeError(  # pragma: no cover
        # Grammar-produced model transitions use only string state names and
        # INIT/EXIT singletons. This guard exposes future model extensions
        # loudly instead of silently treating an unknown endpoint as safe.
        f"Unsupported transition target: {target!r}."
    )


def _initial_leaf_targets(state: State) -> Tuple[str, ...]:
    """Project entering ``state`` to the leaves reached by initial descent."""
    if state.is_leaf_state:
        return (_state_path(state),)

    projected: List[str] = []
    for transition in state.init_transitions:
        projected.extend(_project_target(state, transition.to_state))
    return _dedupe_sorted(projected)


def build_leaf_level_macro_graph(machine: StateMachine) -> LeafLevelGraph:
    """Build the guard-agnostic leaf-level macro graph for ``machine``.

    The projection follows normal leaf-to-leaf transitions, expands composite
    targets through their initial transitions, and bubbles ``Leaf -> [*]``
    transitions through parent outgoing transitions. If a non-root parent has no
    outgoing transition, the bubble is an off-cliff exit and contributes no edge.

    :param machine: State machine to project.
    :type machine: StateMachine
    :return: Leaf-level macro graph.
    :rtype: LeafLevelGraph
    """
    leaves = _leaf_states(machine)
    nodes = tuple(sorted(_state_path(state) for state in leaves))
    edge_sets: Dict[str, Set[str]] = {node: set() for node in nodes}

    for parent_state in machine.walk_states():
        for transition in parent_state.transitions:
            if transition.from_state is INIT_STATE:
                continue

            if not isinstance(transition.from_state, str):
                raise TypeError(  # pragma: no cover
                    # Grammar-produced non-init transition sources are strings.
                    # A future model endpoint type should be made explicit here.
                    f"Unsupported transition source: {transition.from_state!r}."
                )

            source_state = parent_state.substates[transition.from_state]
            if not source_state.is_leaf_state:
                continue

            source_path = _state_path(source_state)
            edge_sets.setdefault(source_path, set()).update(
                _project_target(parent_state, transition.to_state)
            )

    if machine.root_state.is_leaf_state:
        edge_sets.setdefault(_state_path(machine.root_state), set()).add(EXIT_ROOT_SINK)

    edges = {node: tuple(sorted(targets)) for node, targets in edge_sets.items()}
    edges.setdefault(EXIT_ROOT_SINK, tuple())
    return LeafLevelGraph(nodes=nodes, edges=edges)


def _closure_from(
    edges: Dict[str, Tuple[str, ...]],
    starts: Iterable[str],
) -> Set[str]:
    seen: Set[str] = set()
    queue: Deque[str] = deque(starts)
    while queue:
        node = queue.popleft()
        if node in seen:
            continue
        seen.add(node)
        for successor in _successors(edges, node):
            if successor not in seen:
                queue.append(successor)
    return seen


def topological_reachable_set(machine: StateMachine) -> Dict[str, Tuple[str, ...]]:
    """Compute guard-agnostic reachable leaf states for every model state.

    Composite states are first projected through their initial descent and then
    closed over the leaf-level macro graph. Leaf-state results omit the leaf
    itself, matching the existing inspect reachability convention for cycles.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Mapping from every state path to sorted reachable leaf paths.
    :rtype: Dict[str, Tuple[str, ...]]
    """
    graph = build_leaf_level_macro_graph(machine)
    result: Dict[str, Tuple[str, ...]] = {}
    for state in machine.walk_states():
        state_path = _state_path(state)
        starts = _initial_leaf_targets(state)
        reachable = _closure_from(graph.edges, starts)
        reachable.discard(EXIT_ROOT_SINK)
        if state.is_leaf_state:
            reachable.discard(state_path)
        result[state_path] = tuple(sorted(reachable))
    return result


def unreachable_states(machine: StateMachine) -> Tuple[str, ...]:
    """Return non-pseudo leaf states unreachable from the root topology.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Sorted unreachable leaf state paths.
    :rtype: Tuple[str, ...]
    """
    root_path = _state_path(machine.root_state)
    reachable = set(topological_reachable_set(machine).get(root_path, tuple()))
    reachable.add(root_path)
    return tuple(
        sorted(
            _state_path(state)
            for state in machine.walk_states()
            if state.is_leaf_state
            and not state.is_pseudo
            and _state_path(state) not in reachable
        )
    )


def _scc_components(
    nodes: Sequence[str], edges: Dict[str, Tuple[str, ...]]
) -> Tuple[Tuple[str, ...], ...]:
    node_set = set(nodes)
    ordered_nodes = sorted(node_set)
    visited: Set[str] = set()
    finish_order: List[str] = []

    for start in ordered_nodes:
        if start in visited:
            continue

        visit_stack: List[Tuple[str, bool]] = [(start, False)]
        while visit_stack:
            node, expanded = visit_stack.pop()
            if expanded:
                finish_order.append(node)
                continue
            if node in visited:
                continue

            visited.add(node)
            visit_stack.append((node, True))
            successors = [
                successor
                for successor in edges.get(node, tuple())
                if successor in node_set and successor not in visited
            ]
            for successor in reversed(sorted(successors)):
                visit_stack.append((successor, False))

    reverse_edges: Dict[str, List[str]] = {node: [] for node in ordered_nodes}
    for source in ordered_nodes:
        for target in edges.get(source, tuple()):
            if target in node_set:
                reverse_edges[target].append(source)

    components: List[Tuple[str, ...]] = []
    assigned: Set[str] = set()
    for start in reversed(finish_order):
        if start in assigned:
            continue

        component: List[str] = []
        collect_stack = [start]
        assigned.add(start)
        while collect_stack:
            node = collect_stack.pop()
            component.append(node)
            for predecessor in reversed(sorted(reverse_edges.get(node, []))):
                if predecessor not in assigned:
                    assigned.add(predecessor)
                    collect_stack.append(predecessor)

        components.append(tuple(sorted(component)))

    return tuple(sorted(components))


def _is_cyclic_component(
    component: Tuple[str, ...],
    edges: Dict[str, Tuple[str, ...]],
) -> bool:
    if len(component) > 1:
        return True
    if len(component) == 0:  # pragma: no cover
        # SCC decomposition only emits non-empty components. Keep this guard so
        # the helper remains total if it is reused with hand-built component
        # data.
        return False
    node = component[0]
    return node in edges.get(node, tuple())


def strongly_connected_components(machine: StateMachine) -> Tuple[Tuple[str, ...], ...]:
    """Return non-trivial SCCs in the leaf-level topology graph.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Sorted non-trivial SCCs.
    :rtype: Tuple[Tuple[str, ...], ...]
    """
    graph = build_leaf_level_macro_graph(machine)
    return tuple(
        component
        for component in _scc_components(graph.nodes, graph.edges)
        if _is_cyclic_component(component, graph.edges)
    )


def _root_reachable_leaf_paths(
    machine: StateMachine,
    graph: LeafLevelGraph,
) -> Set[str]:
    reachable = _closure_from(graph.edges, _initial_leaf_targets(machine.root_state))
    reachable.discard(EXIT_ROOT_SINK)
    return reachable


def _nodes_that_can_reach_sink(graph: LeafLevelGraph) -> Set[str]:
    reverse_edges: Dict[str, Set[str]] = {node: set() for node in graph.nodes}
    reverse_edges[EXIT_ROOT_SINK] = set()
    for source, targets in graph.edges.items():
        for target in targets:
            reverse_edges.setdefault(target, set()).add(source)

    can_reach = _closure_from(
        {node: tuple(sorted(targets)) for node, targets in reverse_edges.items()},
        (EXIT_ROOT_SINK,),
    )
    can_reach.discard(EXIT_ROOT_SINK)
    return can_reach


def topological_finite(machine: StateMachine) -> FinitenessReport:
    """Check whether all root-reachable leaves can reach the root exit sink.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Finiteness report with trap-cycle and deadlock counterexamples.
    :rtype: FinitenessReport
    """
    graph = build_leaf_level_macro_graph(machine)
    reachable = _root_reachable_leaf_paths(machine, graph)
    can_reach_sink = _nodes_that_can_reach_sink(graph)

    counterexamples: List[Tuple[Literal["trap_cycle", "deadlock"], object]] = []
    for component in strongly_connected_components(machine):
        if not reachable.intersection(component):
            continue
        if not any(node in can_reach_sink for node in component):
            counterexamples.append(("trap_cycle", component))

    for node in sorted(reachable):
        if node in can_reach_sink:
            continue
        if len(graph.edges.get(node, tuple())) == 0:
            counterexamples.append(("deadlock", node))

    return FinitenessReport(
        finite=not counterexamples,
        counterexamples=tuple(counterexamples),
    )


def topological_inevitable_terminator(machine: StateMachine) -> InevitabilityReport:
    """Check whether every topological path must eventually terminate.

    This is an intentionally structural check: any root-reachable deadlock or
    cycle is enough to produce a non-inevitability counterexample, even when
    another outgoing edge could exit at runtime.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Inevitability report.
    :rtype: InevitabilityReport
    """
    graph = build_leaf_level_macro_graph(machine)
    reachable = _root_reachable_leaf_paths(machine, graph)

    for component in strongly_connected_components(machine):
        if reachable.intersection(component):
            return InevitabilityReport(
                inevitable=False,
                counterexample_path=component,
            )

    for node in sorted(reachable):
        if len(graph.edges.get(node, tuple())) == 0:
            return InevitabilityReport(
                inevitable=False,
                counterexample_path=(node,),
            )

    return InevitabilityReport(inevitable=True, counterexample_path=None)


def _event_consumers(machine: StateMachine) -> Dict[str, Set[str]]:
    consumers: Dict[str, Set[str]] = {}
    for parent_state in machine.walk_states():
        parent_path = _state_path(parent_state)
        for transition in parent_state.transitions:
            event = transition.event
            if event is None:
                continue

            event_name = event.path_name
            if transition.from_state is INIT_STATE:
                source_path = parent_path
            elif isinstance(transition.from_state, str):
                source_path = _state_path(parent_state.substates[transition.from_state])
            else:
                raise TypeError(  # pragma: no cover
                    # Grammar-produced non-init transition sources are strings.
                    # A future model endpoint type should be made explicit here.
                    f"Unsupported transition source: {transition.from_state!r}."
                )
            consumers.setdefault(event_name, set()).add(source_path)
    return consumers


def _root_reachable_state_paths(
    machine: StateMachine,
    graph: LeafLevelGraph,
) -> Set[str]:
    reachable_leaves = _root_reachable_leaf_paths(machine, graph)
    reachable_paths = set(reachable_leaves)
    reachable_paths.add(_state_path(machine.root_state))

    for state in machine.walk_states():
        if state.is_leaf_state:
            continue
        if reachable_leaves.intersection(_initial_leaf_targets(state)):
            reachable_paths.add(_state_path(state))
    return reachable_paths


def event_emission_to_consumer_reachable(machine: StateMachine) -> Tuple[str, ...]:
    """Return events whose consumer source states are all unreachable.

    Unused declared events are ignored here; they remain the responsibility of
    the existing design-health unused-event check.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Sorted qualified event names whose consumers are all unreachable.
    :rtype: Tuple[str, ...]
    """
    graph = build_leaf_level_macro_graph(machine)
    reachable = _root_reachable_state_paths(machine, graph)
    unreachable_events = []
    for event_name, sources in _event_consumers(machine).items():
        if sources and all(source not in reachable for source in sources):
            unreachable_events.append(event_name)
    return tuple(sorted(unreachable_events))


__all__ = [
    "EXIT_ROOT_SINK",
    "FinitenessReport",
    "InevitabilityReport",
    "LeafLevelGraph",
    "build_leaf_level_macro_graph",
    "event_emission_to_consumer_reachable",
    "strongly_connected_components",
    "topological_finite",
    "topological_inevitable_terminator",
    "topological_reachable_set",
    "unreachable_states",
]

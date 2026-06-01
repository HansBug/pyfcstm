"""Topological verification algorithms for :mod:`pyfcstm.verify`.

This module implements the group-1 verification algorithms that work only on
the hierarchical state topology. The algorithms project a
:class:`pyfcstm.model.StateMachine` into a leaf-level macro graph and then run
structural graph queries over that projection. They intentionally ignore guard
satisfiability, event availability, transition ordering, and runtime variable
evolution; positive reachability results are therefore over-approximations of
runtime behavior, while unreachable results describe structural topology facts.

The module contains:

* :class:`LeafLevelGraph` - Immutable container for the projected leaf graph.
* :class:`FinitenessReport` - Report object for
  :func:`topological_finite`.
* :class:`InevitabilityReport` - Report object for
  :func:`topological_inevitable_terminator`.
* :func:`build_leaf_level_macro_graph` - Build the guard-agnostic projection.
* :func:`topological_reachable_set` - Compute reachable leaf states.
* :func:`unreachable_states` - Find structurally unreachable leaf states.
* :func:`strongly_connected_components` - Find cyclic leaf-level regions.
* :func:`topological_finite` - Detect reachable no-exit regions.
* :func:`topological_inevitable_terminator` - Detect non-terminating topology.
* :func:`event_emission_to_consumer_reachable` - Detect events whose consumers
  are all unreachable.

.. note::
   The graph projection is independent from the diagnostics package.
   Diagnostic integration is expected to wrap these functions and translate
   their plain Python return values into diagnostic payloads.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> ast = parse_with_grammar_entry("state Root;", "state_machine_dsl")
    >>> machine = parse_dsl_node_to_state_machine(ast)
    >>> graph = build_leaf_level_macro_graph(machine)
    >>> graph.nodes
    ('Root',)
    >>> graph.edges[EXIT_ROOT_SINK]
    ()
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
    """
    Leaf-level macro graph projected from a hierarchical state machine.

    Each node is a dotted path for a leaf state in the source model. Edges
    describe guard-agnostic macro steps between leaf states after expanding
    composite targets through their initial transitions and bubbling leaf exits
    through parent transitions. The synthetic :data:`EXIT_ROOT_SINK` key is
    present in :attr:`edges` so callers can query root termination uniformly.

    :param nodes: Dotted paths of leaf states in stable sorted order.
    :type nodes: Tuple[str, ...]
    :param edges: Mapping from each leaf path, and optionally
        :data:`EXIT_ROOT_SINK`, to sorted successor paths.
    :type edges: Dict[str, Tuple[str, ...]]

    Example::

        >>> graph = LeafLevelGraph(
        ...     nodes=("Root.Idle",),
        ...     edges={"Root.Idle": (EXIT_ROOT_SINK,), EXIT_ROOT_SINK: ()},
        ... )
        >>> graph.nodes
        ('Root.Idle',)
        >>> graph.edges["Root.Idle"]
        ('⊥_root',)
    """

    nodes: Tuple[str, ...]
    edges: Dict[str, Tuple[str, ...]]


@dataclass(frozen=True)
class FinitenessReport:
    """
    Result for :func:`topological_finite`.

    The report is true when every root-reachable leaf can eventually reach the
    synthetic root-exit sink in the topology graph. Counterexamples are plain
    tuples so later diagnostic layers can choose their own payload shape without
    coupling the topology package to the diagnostics package.

    :param finite: ``True`` when every root-reachable leaf can reach the root
        exit sink in the topological graph.
    :type finite: bool
    :param counterexamples: Counterexamples as ``('trap_cycle', scc_tuple)`` or
        ``('deadlock', state_path)`` entries.
    :type counterexamples: Tuple[Tuple[Literal['trap_cycle', 'deadlock'], object], ...]

    Example::

        >>> report = FinitenessReport(finite=False, counterexamples=(
        ...     ("deadlock", "Root.Stuck"),
        ... ))
        >>> report.finite
        False
        >>> report.counterexamples[0][0]
        'deadlock'
    """

    finite: bool
    counterexamples: Tuple[Tuple[Literal["trap_cycle", "deadlock"], object], ...]


@dataclass(frozen=True)
class InevitabilityReport:
    """
    Result for :func:`topological_inevitable_terminator`.

    The report is true only when the topology has no root-reachable cycle or
    deadlock that could keep execution away from the root terminator forever.
    A false report contains one representative path or SCC; it is not intended
    to enumerate every possible non-terminating region.

    :param inevitable: ``True`` when no root-reachable topological path can stay
        in a cycle or deadlock forever.
    :type inevitable: bool
    :param counterexample_path: Representative non-terminating SCC or deadlock
        path, or ``None`` when :attr:`inevitable` is true.
    :type counterexample_path: Optional[Tuple[str, ...]]

    Example::

        >>> report = InevitabilityReport(
        ...     inevitable=False,
        ...     counterexample_path=("Root.Loop",),
        ... )
        >>> report.inevitable
        False
        >>> report.counterexample_path
        ('Root.Loop',)
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
    """
    Build the guard-agnostic leaf-level macro graph for ``machine``.

    The projection follows normal leaf-to-leaf transitions, expands composite
    targets through their initial transitions, and bubbles ``Leaf -> [*]``
    transitions through parent outgoing transitions. Parent-level transitions
    whose source is a composite state are therefore considered only after a
    descendant leaf explicitly exits to that parent; they are not copied onto
    every active descendant leaf. If a non-root parent has no outgoing
    transition, the bubble is an off-cliff exit and contributes no edge. A root
    leaf is treated as root-exit-capable by adding an edge to
    :data:`EXIT_ROOT_SINK`.

    :param machine: State machine to project.
    :type machine: StateMachine
    :return: Leaf-level macro graph.
    :rtype: LeafLevelGraph
    :raises TypeError: If a transition endpoint uses a model object type that
        is not produced by the FCSTM grammar pipeline.

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state Idle;
        ...     [*] -> Idle;
        ...     Idle -> [*];
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> graph = build_leaf_level_macro_graph(machine)
        >>> graph.edges["Root.Idle"]
        ('⊥_root',)
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
    """
    Compute guard-agnostic reachable leaf states for every model state.

    Composite states are first projected through their initial descent and then
    closed over the leaf-level macro graph. Leaf-state results omit the leaf
    itself, matching the existing inspect reachability convention for cycles.
    The returned mapping is keyed by dotted state paths for all states, not only
    leaves.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Mapping from every state path to sorted reachable leaf paths.
    :rtype: Dict[str, Tuple[str, ...]]

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> topological_reachable_set(machine)["Root.A"]
        ('Root.B',)
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
    """
    Return non-pseudo leaf states unreachable from the root topology.

    The result uses topology reachability from the root initial descent and
    filters out pseudo leaf states. Composite states are not returned directly;
    their unreachable leaf descendants are reported instead.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Sorted unreachable leaf state paths.
    :rtype: Tuple[str, ...]

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     state Lost;
        ...     [*] -> A;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> unreachable_states(machine)
        ('Root.Lost',)
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
    """
    Return non-trivial SCCs in the leaf-level topology graph.

    A non-trivial SCC is either a component with more than one leaf or a single
    leaf with a self-loop. The implementation is iterative so deeply nested or
    wide generated models are not limited by Python's recursion depth.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Sorted non-trivial SCCs.
    :rtype: Tuple[Tuple[str, ...], ...]

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B;
        ...     B -> A;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> strongly_connected_components(machine)
        (('Root.A', 'Root.B'),)
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
    """
    Check whether all root-reachable leaves can reach the root exit sink.

    This check accepts models where every reachable leaf has at least one
    topological route to termination, even if runtime guards could block that
    route. It reports closed trap cycles that cannot reach the root sink and
    deadlock leaves with no outgoing projected edge.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Finiteness report with trap-cycle and deadlock counterexamples.
    :rtype: FinitenessReport

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     state B;
        ...     [*] -> A;
        ...     A -> B;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> report = topological_finite(machine)
        >>> report.finite
        False
        >>> report.counterexamples
        (('deadlock', 'Root.B'),)
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
    """
    Check whether every topological path must eventually terminate.

    This is an intentionally structural check: any root-reachable deadlock or
    cycle is enough to produce a non-inevitability counterexample, even when
    another outgoing edge could exit at runtime.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Inevitability report.
    :rtype: InevitabilityReport

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     state A;
        ...     [*] -> A;
        ...     A -> A;
        ...     A -> [*];
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> report = topological_inevitable_terminator(machine)
        >>> report.inevitable
        False
        >>> report.counterexample_path
        ('Root.A',)
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


def _root_reachable_initial_state_paths(
    machine: StateMachine,
    graph: LeafLevelGraph,
) -> Set[str]:
    reachable_leaves = _root_reachable_leaf_paths(machine, graph)
    reachable_paths = {_state_path(machine.root_state)}

    for state in machine.walk_states():
        if state.is_leaf_state:
            continue
        if reachable_leaves.intersection(_initial_leaf_targets(state)):
            reachable_paths.add(_state_path(state))
    return reachable_paths


def _root_reachable_boundary_state_paths(
    machine: StateMachine,
    graph: LeafLevelGraph,
) -> Set[str]:
    reachable_leaves = _root_reachable_leaf_paths(machine, graph)
    boundary_paths: Set[str] = set()
    queue: Deque[State] = deque()

    def add_boundary(state: State) -> None:
        state_path = _state_path(state)
        if state_path in boundary_paths:
            return
        boundary_paths.add(state_path)
        queue.append(state)

    for leaf in _leaf_states(machine):
        if _state_path(leaf) not in reachable_leaves:
            continue
        if not any(transition.to_state is EXIT_STATE for transition in leaf.transitions_from):
            continue

        parent = leaf.parent
        if parent is not None and not parent.is_root_state:
            add_boundary(parent)

    while queue:
        state = queue.popleft()
        for transition in state.transitions_from:
            if transition.to_state is not EXIT_STATE:
                continue

            parent = state.parent
            if parent is not None and not parent.is_root_state:
                add_boundary(parent)

    return boundary_paths


def _event_consumer_reachability(
    machine: StateMachine,
    graph: LeafLevelGraph,
) -> Dict[str, List[bool]]:
    active_leaves = _root_reachable_leaf_paths(machine, graph)
    init_sources = _root_reachable_initial_state_paths(machine, graph)
    boundary_sources = _root_reachable_boundary_state_paths(machine, graph)
    consumers: Dict[str, List[bool]] = {}

    for parent_state in machine.walk_states():
        parent_path = _state_path(parent_state)
        for transition in parent_state.transitions:
            event = transition.event
            if event is None:
                continue

            event_name = event.path_name
            if transition.from_state is INIT_STATE:
                reachable = parent_path in init_sources
            elif isinstance(transition.from_state, str):
                source_state = parent_state.substates[transition.from_state]
                source_path = _state_path(source_state)
                if source_state.is_leaf_state:
                    reachable = source_path in active_leaves
                else:
                    reachable = source_path in boundary_sources
            else:
                raise TypeError(  # pragma: no cover
                    # Grammar-produced non-init transition sources are strings.
                    # A future model endpoint type should be made explicit here.
                    f"Unsupported transition source: {transition.from_state!r}."
                )
            consumers.setdefault(event_name, []).append(reachable)
    return consumers


def event_emission_to_consumer_reachable(machine: StateMachine) -> Tuple[str, ...]:
    """
    Return events whose consumer source states are all unreachable.

    Unused declared events are ignored here; they remain the responsibility of
    the existing design-health unused-event check.
    A transition is treated as an event consumer at the point where its source
    can be selected. Leaf-source consumers are reachable when their leaf is
    root-reachable. Initial-transition consumers are reachable when the owning
    composite can be entered. Composite-source consumers are reachable only when
    a root-reachable descendant leaf can explicitly exit to the composite
    boundary, because parent-level transitions are considered after
    ``Leaf -> [*]`` bubble semantics rather than while any descendant leaf is
    merely active. If every consumer source for a used event is outside these
    root-reachable topology points, the event's qualified name is returned.

    :param machine: State machine to inspect.
    :type machine: StateMachine
    :return: Sorted qualified event names whose consumers are all unreachable.
    :rtype: Tuple[str, ...]

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> source = '''
        ... state Root {
        ...     event Panic;
        ...     state A;
        ...     state Lost;
        ...     [*] -> A;
        ...     Lost -> A : Panic;
        ... }
        ... '''
        >>> ast = parse_with_grammar_entry(source, "state_machine_dsl")
        >>> machine = parse_dsl_node_to_state_machine(ast)
        >>> event_emission_to_consumer_reachable(machine)
        ('Root.Panic',)
    """
    graph = build_leaf_level_macro_graph(machine)
    unreachable_events = []
    for event_name, source_reachability in _event_consumer_reachability(
        machine, graph
    ).items():
        if source_reachability and not any(source_reachability):
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

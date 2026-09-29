"""Potential closed routing loops before a stoppable state is entered."""

from ...utils.validate import ModelDiagnostic


def collect_initial_livelock_warnings(states, transitions):
    """Find closed same-cycle components, overapproximating guards and events.

    Composite entry and continuation after a child exits are separate nodes:
    conflating them would report ordinary resets of stable children as loops.
    Leaf entry stops the search unless the leaf is pseudo. Any edge leaving a
    component suppresses its warning, including guarded escapes; deciding
    which guards and events actually enable a loop remains a runtime concern.
    """
    by_path = {state.path: state for state in states}
    # Collect-mode parsing preserves unresolved endpoints for error reporting.
    endpoints = set(by_path) | {'[*]'}
    if any(t.from_path not in endpoints or t.to_path not in endpoints for t in transitions):
        return []
    edges = {}
    evidence = {}
    for state in states:
        edges[(state.path, 'entry')] = []
        if state.is_composite:
            edges[(state.path, 'post_child_exit')] = []

    for transition in transitions:
        if transition.from_path == '[*]':
            source = (by_path[transition.to_path].parent_path, 'entry')
        else:
            state = by_path[transition.from_path]
            if state.is_leaf and not state.is_pseudo:
                continue
            source = (state.path, 'post_child_exit' if state.is_composite else 'entry')
        if transition.to_path == '[*]':
            parent = by_path[transition.from_path].parent_path
            # Exiting a direct child of the root terminates the whole machine.
            target = (parent, 'post_child_exit') if by_path[parent].parent_path else ('', 'terminated')
        else:
            target = (transition.to_path, 'entry')
        edges[source].append(target)
        evidence.setdefault(source, []).append(transition)

    diagnostics = []
    for component in _routing_components(edges):
        if len(component) == 1 and component[0] not in edges[component[0]]:
            continue
        members = set(component)
        if any(target not in members for node in component for target in edges[node]):
            continue
        paths = sorted({node[0] for node in component})
        relevant = [transition for node in component for transition in evidence[node]]
        diagnostics.append(ModelDiagnostic(
            code='W_INITIAL_LIVELOCK',
            severity='warning',
            span=by_path[paths[0]].span,
            message=(
                'Potential same-cycle initial/pseudo routing livelock among '
                f'{", ".join(paths)}: no structural escape reaches a stoppable '
                'state or termination. Add a route to a non-pseudo leaf or '
                'machine exit, or remove the cyclic reset. Guards and events '
                'are overapproximated.'
            ),
            refs={
                'state_paths': paths,
                'transitions': {
                    str(t.transition_index): {
                        'from_path': t.from_path, 'to_path': t.to_path,
                        'event': t.event, 'guard': t.guard,
                    }
                    for t in sorted(relevant, key=lambda item: item.transition_index)
                },
            },
        ))
    return diagnostics


def _routing_components(edges):
    """Iterative Kosaraju traversal, without importing optional verify modules."""
    visited = set()
    order = []
    reverse = {node: [] for node in edges}
    for source, targets in edges.items():
        for target in targets:
            if target in reverse:
                reverse[target].append(source)
    for start in edges:
        stack = [(start, False)]
        while stack:
            node, expanded = stack.pop()
            if expanded:
                order.append(node)
            elif node not in visited:
                visited.add(node)
                stack.append((node, True))
                stack.extend((target, False) for target in edges.get(node, ()))
    assigned = set()
    for start in reversed(order):
        if start in assigned or start not in edges:
            continue
        component = []
        stack = [start]
        assigned.add(start)
        while stack:
            node = stack.pop()
            component.append(node)
            for predecessor in reverse[node]:
                if predecessor not in assigned:
                    assigned.add(predecessor)
                    stack.append(predecessor)
        yield tuple(sorted(component))

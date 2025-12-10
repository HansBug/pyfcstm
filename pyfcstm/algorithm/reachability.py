from typing import Union

from natsort import natsorted

from ..dsl import node as dsl_nodes
from ..model import State


def _sort_node_key(node: Union[str, dsl_nodes._StateSingletonMark]):
    if node == dsl_nodes.INIT_STATE:
        return 0, ''
    elif node == dsl_nodes.EXIT_STATE:
        return 2, ''
    else:
        return 1, node


def path_reachability(state: State, from_state: Union[str, dsl_nodes._StateSingletonMark],
                      to_state: Union[str, dsl_nodes._StateSingletonMark]):
    d_from_edges = {}
    s_edges = set()
    for transition in state.transitions:
        s_edges.add((transition.from_state, transition.to_state))
        if transition.from_state not in d_from_edges:
            d_from_edges[transition.from_state] = set()
        d_from_edges[transition.from_state].add(transition.to_state)

    queue = [from_state]
    s_queue = {from_state}
    state_sources = {}
    f = 0
    while f < len(queue):
        head = queue[f]
        f += 1
        for next_state in natsorted(d_from_edges.get(head) or [], key=_sort_node_key):
            if next_state not in s_queue:
                s_queue.add(next_state)
                queue.append(next_state)
                state_sources[next_state] = head

    if to_state in state_sources:
        path = [to_state]
        node = to_state
        while node in state_sources:
            node = state_sources[node]
            path.append(node)
        return True, path[::-1]
    else:
        return False, None

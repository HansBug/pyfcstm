"""
Verification helpers for symbolic exploration of pyfcstm state machines.

This package currently exposes the symbolic breadth-first search utilities used
to explore reachable verification states under Z3 constraints. The public API
is intentionally small and centers on :func:`bfs_search`, which returns a
search context containing retained symbolic frames and lazily created event
variables.

The package exports:

* :class:`SearchFrame` - One symbolic frame in the explored search graph.
* :class:`StateSearchSpace` - Retained frames for one state/type bucket.
* :class:`StateSearchContext` - Search queue, state buckets, and event vars.
* :func:`bfs_search` - Symbolically explore a state machine with BFS.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.verify import bfs_search
    >>> dsl_code = '''
    ... state Root {
    ...     state Idle;
    ...     [*] -> Idle;
    ... }
    ... '''
    >>> ast = parse_with_grammar_entry(dsl_code, 'state_machine_dsl')
    >>> sm = parse_dsl_node_to_state_machine(ast)
    >>> ctx = bfs_search(sm, 'Root.Idle', max_cycle=1)
    >>> ('Root.Idle', 'leaf') in ctx.spaces
    True
"""

from .search import SearchFrame, StateSearchSpace, StateSearchContext, bfs_search

__all__ = [
    'SearchFrame',
    'StateSearchSpace',
    'StateSearchContext',
    'bfs_search',
]

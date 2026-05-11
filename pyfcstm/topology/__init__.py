"""
Topological verification helpers for hierarchical state machines.

This package provides pure-topology, guard-agnostic implementations of the
three property checks documented in sections 3.4-3.6 of the FCSTM formal
verification report:

* :func:`check_reachability` (section 3.4) - "Can ``target`` be reached
  from ``source``?"
* :func:`check_finiteness` (section 3.5) - "Does every macro path from
  ``source`` eventually terminate via ``[*]``?"
* :func:`check_inevitability` (section 3.6) - "Does every macro path from
  ``source`` pass through ``target``?"

All three checks operate on a *leaf-only macro graph* built by
:func:`build_topology_graph`. The graph collapses every simulator-level
transition (including the bubble-up chain implied by ``X -> [*]`` exits
and the descent chain implied by ``[*] -> Composite`` initial transitions)
into a single ``leaf -> leaf`` or ``leaf -> END_NODE`` edge. Guards,
events, and variable values are deliberately ignored; every declared
transition is treated as a possible move.

The public API:

* :func:`check_reachability` - Topological reachability verdict.
* :func:`check_finiteness` - Topological finiteness verdict.
* :func:`check_inevitability` - Topological inevitability verdict.
* :func:`build_topology_graph` - One-shot macro graph builder.
* :func:`resolve_to_leaves` - Init-chain descent helper.
* :data:`END_NODE` - Synthetic terminal sentinel used in macro paths.
* :class:`TopologyGraph` - Frozen macro graph view.
* :class:`MacroEdge` - One ``leaf -> next-leaf-or-END`` edge.
* :class:`ReachabilityResult`, :class:`FinitenessResult`,
  :class:`InevitabilityResult` - Verdict dataclasses returned by the
  three checks.
* :class:`FinitenessCounterexample`,
  :class:`InevitabilityCounterexample` - Counterexample dataclasses
  embedded in the verdicts.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.topology import (
    ...     check_reachability, check_finiteness, check_inevitability,
    ... )
    >>> dsl = '''
    ... state Root {
    ...     state Idle;
    ...     state Active;
    ...     state Safe;
    ...     [*] -> Idle;
    ...     Idle -> Active;
    ...     Active -> Safe;
    ...     Safe -> [*];
    ... }
    ... '''
    >>> sm = parse_dsl_node_to_state_machine(
    ...     parse_with_grammar_entry(dsl, 'state_machine_dsl'))
    >>> check_reachability(sm, target='Root.Safe').reachable
    True
    >>> check_finiteness(sm).finite
    True
    >>> check_inevitability(sm, target='Root.Safe').inevitable
    True
"""

from .graph import build_topology_graph, resolve_to_leaves
from .reachability import bfs_reach, check_reachability
from .finiteness import check_finiteness
from .inevitability import check_inevitability
from .render import (
    TopologyRenderError,
    build_render_payload,
    render_topology_png,
    render_topology_svg,
)
from .types import (
    END_KEY,
    END_NODE,
    FinitenessCounterexample,
    FinitenessResult,
    InevitabilityCounterexample,
    InevitabilityResult,
    MacroEdge,
    NodeKey,
    NodeTyping,
    ReachabilityResult,
    TopologyGraph,
    format_node,
    node_key,
)

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
    "TopologyRenderError",
    "bfs_reach",
    "build_render_payload",
    "build_topology_graph",
    "check_finiteness",
    "check_inevitability",
    "check_reachability",
    "format_node",
    "node_key",
    "render_topology_png",
    "render_topology_svg",
    "resolve_to_leaves",
]

"""
SVG / PNG rendering for pyfcstm topological verification results.

This module ships a JavaScript bundle (built from ``js/topology_render/``
via esbuild and packaged under ``pyfcstm/topology/_render_assets``) and
runs it in a single embedded V8 isolate via :mod:`py_mini_racer`. The
Python side serializes a :class:`pyfcstm.topology.ReachabilityResult`,
:class:`pyfcstm.topology.FinitenessResult`, or
:class:`pyfcstm.topology.InevitabilityResult` together with the macro
graph into JSON, then asks the JS bundle to produce an SVG or PNG.

The module contains:

* :func:`render_topology_svg` - Render any topology result to SVG.
* :func:`render_topology_png` - Same payload, PNG output via resvg-wasm.
* :class:`TopologyRenderError` - Raised when the JS bundle fails to load
  or the renderer raises.
* :func:`build_render_payload` - Internal serializer; exposed for callers
  that want to drive the JS bundle directly.

.. note::

   PNG rendering pays a one-time resvg-wasm instantiation cost (tens of
   milliseconds) on the first call after process start. SVG rendering
   is cheap and re-entrant.

Example::

    >>> from pyfcstm.dsl import parse_with_grammar_entry
    >>> from pyfcstm.model import parse_dsl_node_to_state_machine
    >>> from pyfcstm.topology import check_reachability, render_topology_svg
    >>> sm = parse_dsl_node_to_state_machine(parse_with_grammar_entry(
    ...     'state R { state A; state B; [*] -> A; A -> B; B -> [*]; }',
    ...     'state_machine_dsl'))
    >>> result = check_reachability(sm, target='R.B')
    >>> svg = render_topology_svg(sm, result)
    >>> svg.startswith('<?xml')
    True
"""

from __future__ import annotations

import base64
import json
import os
import threading
from typing import Any, Dict, List, Optional, Sequence, Tuple, Union

from ..model import State, StateMachine
from .graph import build_topology_graph
from .types import (
    END_KEY,
    END_NODE,
    FinitenessResult,
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
    "TopologyRenderError",
    "build_render_payload",
    "render_topology_png",
    "render_topology_svg",
]


_RENDER_ASSET_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "_render_assets",
    "pyfcstm-topology-render.js",
)

_runtime_lock = threading.Lock()
_runtime_cached = None
_PNG_INIT_LOCK = threading.Lock()
_PNG_INIT_MAX_SPINS = 400
_RENDER_MAX_SPINS = 1200


class TopologyRenderError(RuntimeError):
    """Raised when the JS bundle fails to load or the renderer raises."""


def _import_mini_racer():
    """Import the MiniRacer class.

    Same import path works for both the legacy ``py-mini-racer`` (Python
    3.7) and the modern ``mini-racer`` (Python 3.8+) PyPI distributions.

    :return: The ``MiniRacer`` class.
    :rtype: type
    :raises TopologyRenderError: If the dependency is not installed.
    """
    try:
        from py_mini_racer import MiniRacer
        return MiniRacer
    except ImportError as err:
        raise TopologyRenderError(
            "Topology rendering requires the optional 'py-mini-racer' "
            "(Python 3.7) or 'mini-racer' (Python 3.8+) dependency. "
            "Install with `pip install pyfcstm[sysdesim_render]` or add the "
            "package directly to your environment."
        ) from err


def _get_runtime():
    """Get a process-wide cached MiniRacer instance with the JS bundle loaded.

    :return: ``(ctx, version_text)`` pair, cached after the first call.
    :rtype: Tuple[Any, str]
    :raises TopologyRenderError: If the bundle cannot be loaded or fails
        the version probe.
    """
    global _runtime_cached
    with _runtime_lock:
        if _runtime_cached is not None:
            return _runtime_cached
        MiniRacer = _import_mini_racer()
        ctx = MiniRacer()
        with open(_RENDER_ASSET_PATH, "r", encoding="utf-8") as bundle_file:
            ctx.eval(bundle_file.read())
        try:
            version_text = ctx.eval("PyfcstmTopology.version()")
        except Exception as err:
            raise TopologyRenderError(
                "Loaded JS bundle did not expose PyfcstmTopology.version(): {!r}".format(err)
            )
        _runtime_cached = (ctx, str(version_text))
        return _runtime_cached


def _ensure_png_runtime(ctx):
    """Drive the JS-side resvg-wasm initialization to completion on *ctx*.

    Idempotent: subsequent calls on the same context return immediately.

    :param ctx: MiniRacer context.
    :type ctx: Any
    :raises TopologyRenderError: If wasm init fails.
    """
    with _PNG_INIT_LOCK:
        if getattr(ctx, "_pyfcstm_topology_png_initialized", False):
            return
        ctx.eval("PyfcstmTopology.startPngInit()")
        for _ in range(_PNG_INIT_MAX_SPINS):
            state = ctx.eval("PyfcstmTopology.pngInitState()")
            if state == "ready":
                ctx._pyfcstm_topology_png_initialized = True
                return
            if state == "error":
                try:
                    ctx.eval("PyfcstmTopology.isPngReady()")
                except Exception as err:
                    raise TopologyRenderError(
                        "resvg-wasm init failed: {!r}".format(err)
                    ) from err
                raise TopologyRenderError(
                    "resvg-wasm init reported error without throwing."
                )
            ctx.eval("0")
        raise TopologyRenderError(
            "resvg-wasm init did not complete after {} drains.".format(_PNG_INIT_MAX_SPINS)
        )


def _run_render(ctx, payload_text, options_text):
    """Drive ``startRender`` + spin ``renderState`` until ``ready`` or ``error``.

    :param ctx: MiniRacer context.
    :type ctx: Any
    :param payload_text: JSON payload string.
    :type payload_text: str
    :param options_text: JSON options string.
    :type options_text: str
    :return: SVG string emitted by the JS bundle.
    :rtype: str
    :raises TopologyRenderError: If the JS render raises or never settles.
    """
    try:
        ctx.eval(
            "PyfcstmTopology.startRender({payload}, {options})".format(
                payload=payload_text, options=options_text
            )
        )
    except Exception as err:
        raise TopologyRenderError("startRender raised: {!r}".format(err)) from err
    for _ in range(_RENDER_MAX_SPINS):
        state = ctx.eval("PyfcstmTopology.renderState()")
        if state == "ready":
            try:
                return str(ctx.eval("PyfcstmTopology.renderResult()"))
            except Exception as err:
                raise TopologyRenderError(
                    "renderResult raised: {!r}".format(err)
                ) from err
        if state == "error":
            try:
                ctx.eval("PyfcstmTopology.renderResult()")
            except Exception as err:
                raise TopologyRenderError(
                    "Topology render failed: {!r}".format(err)
                ) from err
            raise TopologyRenderError(
                "Topology render reported error without throwing."
            )
        ctx.eval("0")
    raise TopologyRenderError(
        "Topology render did not complete after {} drains.".format(_RENDER_MAX_SPINS)
    )


def _key_to_id(key):
    """Convert a node_key value to a stable string ID.

    :param key: A node key.
    :type key: Tuple[str, ...]
    :return: ``"__END__"`` for the END sentinel, otherwise dotted path.
    :rtype: str
    """
    if key == END_KEY:
        return "__END__"
    return ".".join(key)


def _node_id_for(node):
    """Convert a :class:`State` or :data:`END_NODE` into its render ID.

    :param node: A leaf state or the END sentinel.
    :type node: Union[State, _EndNodeSentinel]
    :return: Stable render ID.
    :rtype: str
    """
    return _key_to_id(node_key(node))


def _short_label(node):
    """Trim a node label down to its leaf-name (last path segment).

    :param node: A leaf state or the END sentinel.
    :type node: Union[State, _EndNodeSentinel]
    :return: ``"[*]"`` for END, otherwise the leaf name.
    :rtype: str
    """
    if node is END_NODE:
        return "[*]"
    if not isinstance(node, State):
        return str(node)
    return node.path[-1] if node.path else node.name


def _build_graph_section(graph):
    """Serialize the macro graph into the JSON shape the JS bundle consumes.

    :param graph: Macro graph view.
    :type graph: TopologyGraph
    :return: ``(nodes_payload, edges_payload)`` tuple.
    :rtype: Tuple[List[Dict[str, Any]], List[Dict[str, Any]]]
    """
    nodes = []
    seen_ids = set()
    for leaf in graph.leaves:
        nid = _node_id_for(leaf)
        if nid in seen_ids:
            continue
        seen_ids.add(nid)
        nodes.append({
            "id": nid,
            "label": _short_label(leaf),
            "path": list(leaf.path),
            "kind": "pseudo" if leaf.is_pseudo else "leaf",
        })
    if "__END__" not in seen_ids:
        nodes.append({"id": "__END__", "label": "[*]", "kind": "end"})

    edges = []
    for idx, edge in enumerate(graph.edges):
        edges.append({
            "id": "e{}".format(idx),
            "source": _node_id_for(edge.source),
            "target": _node_id_for(edge.target),
        })
    return nodes, edges


def _build_reach_overlay(result):
    """Serialize a :class:`ReachabilityResult` into the JS overlay payload.

    :param result: Reachability verdict.
    :type result: ReachabilityResult
    :return: Overlay dictionary the JS renderer understands.
    :rtype: Dict[str, Any]
    """
    source_id = _node_id_for(result.source) if result.source is not None else None
    target_id = _node_id_for(result.target) if result.target is not None else None
    witness_ids = [_node_id_for(n) for n in (result.witness_path or ())]
    reach_ids = [_node_id_for(n) for n in result.reach_nodes]
    banner = (
        "reachable: {} -> {}".format(
            ".".join(result.source.path), ".".join(result.target.path)
        )
        if result.reachable
        else "unreachable: target '{}' not reachable from '{}'".format(
            ".".join(result.target.path), ".".join(result.source.path)
        )
    )
    return {
        "kind": "reach",
        "verdict": "ok" if result.reachable else "fail",
        "source": source_id,
        "target": target_id,
        "witness_path": witness_ids,
        "reach_set": reach_ids,
        "banner": banner,
    }


def _build_finite_overlay(result):
    """Serialize a :class:`FinitenessResult` into the JS overlay payload.

    :param result: Finiteness verdict.
    :type result: FinitenessResult
    :return: Overlay dictionary the JS renderer understands.
    :rtype: Dict[str, Any]
    """
    cex = result.counterexample
    cycle_ids = []
    prefix_ids = []
    deadlock_id = None
    prefix_path = []
    if result.finite:
        banner = "finite OK - every macro path from '{}' reaches [*].".format(
            ".".join(result.source.path)
        )
    elif cex is not None:
        prefix_ids = [_node_id_for(s) for s in cex.prefix]
        if cex.kind == "trap_cycle":
            cycle_ids = [_node_id_for(s) for s in cex.cycle]
            cycle_text = " -> ".join(_short_label(s) for s in cex.cycle)
            banner = "infinite FAIL - trap cycle [{}] reachable from '{}' ({} violating leaf)".format(
                cycle_text, ".".join(result.source.path), result.violating_node_count
            )
        elif cex.kind == "deadlock":
            deadlock_id = _node_id_for(cex.deadlock_leaf) if cex.deadlock_leaf is not None else None
            banner = "infinite FAIL - deadlock at '{}' reachable from '{}'".format(
                ".".join(cex.deadlock_leaf.path) if cex.deadlock_leaf is not None else "?",
                ".".join(result.source.path),
            )
        else:
            banner = "infinite FAIL"
        if cex.kind == "trap_cycle" and cex.cycle:
            prefix_path = prefix_ids + [_node_id_for(cex.cycle[0])]
        elif cex.kind == "deadlock" and cex.deadlock_leaf is not None:
            prefix_path = prefix_ids + [_node_id_for(cex.deadlock_leaf)]
    else:
        banner = "infinite FAIL"
    return {
        "kind": "finite",
        "verdict": "ok" if result.finite else "fail",
        "source": _node_id_for(result.source) if result.source is not None else None,
        "cycle": cycle_ids,
        "prefix": prefix_ids,
        "prefix_path": prefix_path,
        "deadlock_leaf": deadlock_id,
        "banner": banner,
    }


def _build_inev_overlay(result):
    """Serialize an :class:`InevitabilityResult` into the JS overlay payload.

    :param result: Inevitability verdict.
    :type result: InevitabilityResult
    :return: Overlay dictionary the JS renderer understands.
    :rtype: Dict[str, Any]
    """
    cex = result.counterexample
    cycle_ids = []
    cex_path_ids = []
    deadlock_id = None
    cex_kind = None
    target_path = ".".join(result.target.path)
    source_path = ".".join(result.source.path)
    if result.inevitable:
        banner = "inevitable OK - every macro path from '{}' passes through '{}'.".format(
            source_path, target_path
        )
        return {
            "kind": "inev",
            "verdict": "ok",
            "source": _node_id_for(result.source),
            "target": _node_id_for(result.target),
            "banner": banner,
        }
    if cex is not None:
        cex_kind = cex.kind
        cex_path_ids = [_node_id_for(s) for s in cex.prefix]
        if cex.kind == "alt_end":
            cex_path_ids.append("__END__")
            banner = "avoidable FAIL - alt-end path bypasses '{}': {} -> [*]".format(
                target_path, " -> ".join(_short_label(s) for s in cex.prefix) or "(start)"
            )
        elif cex.kind == "cycle":
            cycle_ids = [_node_id_for(s) for s in cex.cycle]
            if cex.cycle:
                cex_path_ids.append(_node_id_for(cex.cycle[0]))
            banner = "avoidable FAIL - trap cycle bypasses '{}': cycle [{}]".format(
                target_path,
                " -> ".join(_short_label(s) for s in cex.cycle),
            )
        elif cex.kind == "deadlock":
            term = cex.terminal
            if isinstance(term, State):
                deadlock_id = _node_id_for(term)
                cex_path_ids.append(deadlock_id)
            banner = "avoidable FAIL - deadlock bypasses '{}': {}".format(
                target_path, cex.format()
            )
        elif cex.kind == "unreachable":
            banner = "avoidable FAIL - target '{}' unreachable from '{}'".format(
                target_path, source_path
            )
        else:
            banner = "avoidable FAIL"
    else:
        banner = "avoidable FAIL"
    return {
        "kind": "inev",
        "verdict": "fail",
        "source": _node_id_for(result.source),
        "target": _node_id_for(result.target),
        "cex_kind": cex_kind,
        "cex_path": cex_path_ids,
        "cycle": cycle_ids,
        "deadlock_leaf": deadlock_id,
        "banner": banner,
    }


def build_render_payload(sm, result, title=None, direction="DOWN", graph=None):
    """
    Serialize *sm* + *result* into the JSON shape the JS bundle consumes.

    Exposed publicly so callers that want to drive the JS bundle directly
    (e.g. for caching or custom transports) can reuse the payload format.

    :param sm: State machine the result was computed against.
    :type sm: StateMachine
    :param result: A verdict produced by one of the three checks.
    :type result: Union[ReachabilityResult, FinitenessResult, InevitabilityResult]
    :param title: Optional diagram title.
    :type title: Optional[str]
    :param direction: ELK layout direction (``"DOWN"`` or ``"RIGHT"``).
    :type direction: str
    :param graph: Optional pre-built :class:`TopologyGraph`.
    :type graph: Optional[TopologyGraph]
    :return: Dict ready to JSON-encode for the JS bundle.
    :rtype: Dict[str, Any]
    :raises TypeError: If *result* is not one of the three supported
        result dataclasses.
    """
    if graph is None:
        graph = build_topology_graph(sm)
    nodes, edges = _build_graph_section(graph)
    if isinstance(result, ReachabilityResult):
        overlay = _build_reach_overlay(result)
        default_title = "Reachability"
    elif isinstance(result, FinitenessResult):
        overlay = _build_finite_overlay(result)
        default_title = "Finiteness"
    elif isinstance(result, InevitabilityResult):
        overlay = _build_inev_overlay(result)
        default_title = "Inevitability"
    else:
        raise TypeError(
            "render result must be ReachabilityResult / FinitenessResult / "
            "InevitabilityResult, got {!r}".format(type(result).__name__)
        )
    return {
        "title": title or default_title,
        "direction": direction,
        "nodes": nodes,
        "edges": edges,
        "overlay": overlay,
    }


def render_topology_svg(sm, result, title=None, direction="DOWN", graph=None):
    """
    Render a topology verification result to an SVG document string.

    :param sm: State machine the result was computed against.
    :type sm: StateMachine
    :param result: A verdict from :func:`pyfcstm.topology.check_reachability`,
        :func:`pyfcstm.topology.check_finiteness`, or
        :func:`pyfcstm.topology.check_inevitability`.
    :type result: Union[ReachabilityResult, FinitenessResult, InevitabilityResult]
    :param title: Optional override for the banner title.
    :type title: Optional[str]
    :param direction: ELK layout direction (``"DOWN"`` or ``"RIGHT"``).
    :type direction: str
    :param graph: Optional pre-built :class:`TopologyGraph`.
    :type graph: Optional[TopologyGraph]
    :return: SVG document text (UTF-8, with XML prolog).
    :rtype: str
    :raises TopologyRenderError: If the JS bundle cannot be loaded or the
        renderer raises.

    Example::

        >>> from pyfcstm.dsl import parse_with_grammar_entry
        >>> from pyfcstm.model import parse_dsl_node_to_state_machine
        >>> from pyfcstm.topology import check_reachability, render_topology_svg
        >>> sm = parse_dsl_node_to_state_machine(parse_with_grammar_entry(
        ...     'state R { state A; state B; [*] -> A; A -> B; B -> [*]; }',
        ...     'state_machine_dsl'))
        >>> svg = render_topology_svg(sm, check_reachability(sm, target='R.B'))
        >>> '<svg' in svg
        True
    """
    payload = build_render_payload(sm, result, title=title, direction=direction, graph=graph)
    ctx, _version = _get_runtime()
    payload_text = json.dumps(payload, ensure_ascii=False)
    return _run_render(ctx, payload_text, "{}")


def render_topology_png(sm, result, title=None, direction="DOWN", graph=None,
                        resvg_options=None, font_files=None, font_buffers=None):
    """
    Render a topology verification result to PNG bytes (via resvg-wasm).

    Internally renders the SVG first, then rasterizes via the bundled
    ``@resvg/resvg-wasm``. The first PNG render after process start pays
    a one-time wasm-instantiation cost.

    :param sm: State machine the result was computed against.
    :type sm: StateMachine
    :param result: A verdict from one of the three checks.
    :type result: Union[ReachabilityResult, FinitenessResult, InevitabilityResult]
    :param title: Optional banner title override.
    :type title: Optional[str]
    :param direction: ELK direction (``"DOWN"`` or ``"RIGHT"``).
    :type direction: str
    :param graph: Optional pre-built :class:`TopologyGraph`.
    :type graph: Optional[TopologyGraph]
    :param resvg_options: Optional resvg rendering options.
    :type resvg_options: Optional[Dict[str, Any]]
    :param font_files: Optional list of font-file paths to load.
    :type font_files: Optional[Sequence[str]]
    :param font_buffers: Optional list of pre-loaded font byte buffers.
    :type font_buffers: Optional[Sequence[bytes]]
    :return: PNG bytes (begins with the PNG magic header).
    :rtype: bytes
    :raises TopologyRenderError: If wasm init or rendering fails.
    """
    svg_text = render_topology_svg(sm, result, title=title, direction=direction, graph=graph)
    ctx, _version = _get_runtime()
    _ensure_png_runtime(ctx)

    options = {}
    if resvg_options:
        options["resvg"] = resvg_options

    font_buffer_b64_list = []
    for font_path in font_files or ():
        with open(font_path, "rb") as font_file:
            font_buffer_b64_list.append(
                base64.b64encode(font_file.read()).decode("ascii")
            )
    for buffer in font_buffers or ():
        font_buffer_b64_list.append(base64.b64encode(buffer).decode("ascii"))
    if font_buffer_b64_list:
        options["fontBuffersB64"] = font_buffer_b64_list

    svg_text_json = json.dumps(svg_text)
    options_json = json.dumps(options, ensure_ascii=False)
    try:
        b64_text = ctx.eval(
            "PyfcstmTopology.renderPng({svg}, {options})".format(
                svg=svg_text_json, options=options_json
            )
        )
    except Exception as err:
        raise TopologyRenderError(
            "renderPng raised: {!r}".format(err)
        ) from err
    return base64.b64decode(str(b64_text))

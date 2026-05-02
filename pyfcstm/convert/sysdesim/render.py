"""
SVG sequence-diagram rendering for SysDeSim timelines.

This module ships a small JavaScript bundle (built from
``js/sysdesim_render/`` via esbuild and packaged under
``pyfcstm/convert/sysdesim/_render_assets``) and runs it in a single embedded
V8 isolate via :mod:`py_mini_racer`. The Python side is responsible for
turning a :class:`SysDeSimPhase10Report` into a JSON-serializable timeline
description; the JS side is responsible for laying it out and emitting an
SVG string visually compatible with the SysDeSim XMI tooling's own export.

The module contains:

* :func:`render_sysdesim_timeline_svg` - Public Python API that turns a
  pre-built Phase10 report (or, by convenience, an XML path) into an SVG
  string.
* :func:`_build_timeline_json` - Internal serializer that flattens the
  Phase10 report into the JSON payload the JS bundle expects.

.. note::

   The JS bundle is intentionally self-contained: it does not require ELK.js
   or any DOM API. Sequence diagrams have a deterministic layout (one column
   per lifeline, one row per scenario step) so a generic graph layout engine
   does not buy us anything for the first cut.

Example::

    >>> from pyfcstm.convert.sysdesim import render_sysdesim_timeline_svg
    >>> svg = render_sysdesim_timeline_svg(xml_path='./model.xml')
    >>> svg.startswith('<?xml')  # doctest: +SKIP
    True
"""

from __future__ import annotations

import base64
import json
import os
import threading
from typing import Any, Dict, List, Optional, Tuple

from .timeline import (
    SysDeSimMessageObservation,
    SysDeSimStateInvariantObservation,
)
from .timeline_verify import (
    SysDeSimPhase10Report,
    build_sysdesim_phase10_report,
)


_RENDER_ASSET_PATH = os.path.join(
    os.path.dirname(os.path.abspath(__file__)),
    "_render_assets",
    "pyfcstm-sysdesim-render.js",
)


_runtime_lock = threading.Lock()
_runtime_cached: Optional[Tuple[object, str]] = None  # (MiniRacer ctx, version_text)
_PNG_INIT_LOCK = threading.Lock()
_PNG_INIT_MAX_SPINS = 400


class SysdesimRenderError(RuntimeError):
    """Raised when the JS bundle fails to load or render."""


def _import_mini_racer():
    """
    Import :class:`py_mini_racer.MiniRacer`. The same import path works for
    both the legacy ``py-mini-racer`` (Python 3.7) and the modern
    ``mini-racer`` (Python 3.8+) PyPI distributions.
    """
    try:
        from py_mini_racer import MiniRacer  # type: ignore
        return MiniRacer
    except ImportError as err:  # pragma: no cover - depends on extras install
        raise SysdesimRenderError(
            "SysDeSim SVG rendering requires the optional 'py-mini-racer' "
            "(Python 3.7) or 'mini-racer' (Python 3.8+) dependency. "
            "Install with `pip install pyfcstm[sysdesim_render]` or add the "
            "package directly to your environment."
        ) from err


def _get_runtime():
    """Get a process-wide cached MiniRacer instance with the JS bundle loaded."""
    global _runtime_cached
    with _runtime_lock:
        if _runtime_cached is not None:
            return _runtime_cached
        MiniRacer = _import_mini_racer()
        ctx = MiniRacer()
        with open(_RENDER_ASSET_PATH, "r", encoding="utf-8") as bundle_file:
            ctx.eval(bundle_file.read())
        # Probe that the bundle exposes the expected entry function.
        try:
            version_text = ctx.eval("PyfcstmSysdesim.version()")
        except Exception as err:  # pragma: no cover - bundle smoke check
            raise SysdesimRenderError(
                "Loaded JS bundle did not expose PyfcstmSysdesim.version(): {!r}".format(
                    err
                )
            )
        _runtime_cached = (ctx, str(version_text))
        return _runtime_cached


def _lifeline_id(lifeline_id: Optional[str]) -> Optional[str]:
    """Pass-through helper kept for future ID-mangling needs."""
    return lifeline_id


def _build_timeline_json(report: SysDeSimPhase10Report, *, title: Optional[str] = None) -> Dict[str, Any]:
    """
    Flatten a :class:`SysDeSimPhase10Report` into the JSON shape the JS
    renderer consumes.

    The renderer expects the following keys::

        {
          "title": "...",
          "lifelines": [
            {"id": "...", "display_name": "控制",
             "is_machine_internal": true},
            ...
          ],
          "steps": [
            {"step_id": "s01",
             "actions": [{"kind": "set_input", "input_name": "y",
                          "value_text": "2300"}, ...],
             "outbound_signals": ["Sig11"],
             "message": {"source_lifeline_id": "...",
                         "target_lifeline_id": "...",
                         "signal_name": "Sig9",
                         "label": "Sig9"} or null,
             "invariant": {"lifeline_id": "...", "text": "y < 2200"} or null
            },
            ...
          ],
          "temporal_constraints": [
            {"constraint_id": "...", "left_step_id": "s17",
             "right_step_id": "s20", "min_seconds_text": "1s",
             "max_seconds_text": "1s", "strict_lower": false},
            ...
          ]
        }
    """
    phase78 = report.phase9_report.phase78_report
    interaction = phase78.phase56_report.interaction

    lifelines = [
        {
            "id": lifeline.lifeline_id,
            "display_name": lifeline.raw_name or lifeline.normalized_name or lifeline.lifeline_id,
            "is_machine_internal": bool(lifeline.is_machine_internal),
        }
        for lifeline in interaction.lifelines
    ]

    message_index = {
        item.message_id: item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimMessageObservation)
    }
    invariant_index = {
        item.invariant_id: item
        for item in interaction.observation_stream
        if isinstance(item, SysDeSimStateInvariantObservation)
    }

    steps_payload: List[Dict[str, Any]] = []
    for step in report.scenario.steps:
        actions: List[Dict[str, Any]] = []
        for action in getattr(step, "actions", ()) or ():
            kind = getattr(action, "kind", None)
            if kind == "set_input":
                actions.append(
                    {
                        "kind": "set_input",
                        "input_name": getattr(action, "input_name", None),
                        "value_text": getattr(action, "value_text", None),
                    }
                )
            elif kind == "emit":
                actions.append(
                    {
                        "kind": "emit",
                        "event_name": getattr(action, "event_name", None),
                    }
                )

        outbound_signals: List[str] = []
        for note in getattr(step, "notes", ()) or ():
            if isinstance(note, str) and note.startswith("outbound_signal="):
                signal_name = note.split("=", 1)[1].strip()
                if signal_name:
                    outbound_signals.append(signal_name)

        source_id = step.source_observation_ids[0] if step.source_observation_ids else None
        message_payload: Optional[Dict[str, Any]] = None
        invariant_payload: Optional[Dict[str, Any]] = None
        if source_id and source_id in message_index:
            obs = message_index[source_id]
            signal_name = obs.signal_name or obs.display_name or obs.raw_name or ""
            if obs.direction == "outbound" and outbound_signals:
                label = outbound_signals[0]
            else:
                label = obs.display_name or obs.raw_name or signal_name
            message_payload = {
                "message_id": obs.message_id,
                "source_lifeline_id": _lifeline_id(obs.source_lifeline_id),
                "target_lifeline_id": _lifeline_id(obs.target_lifeline_id),
                "signal_name": signal_name,
                "label": label,
                "direction": obs.direction,
            }
        elif source_id and source_id in invariant_index:
            obs = invariant_index[source_id]
            invariant_payload = {
                "invariant_id": obs.invariant_id,
                "lifeline_id": _lifeline_id(obs.lifeline_id),
                "text": obs.raw_text or "",
            }

        steps_payload.append(
            {
                "step_id": step.step_id,
                "actions": actions,
                "outbound_signals": outbound_signals,
                "message": message_payload,
                "invariant": invariant_payload,
            }
        )

    constraints_payload = [
        {
            "constraint_id": item.constraint_id,
            "kind": item.kind,
            "left_step_id": item.left_step_id,
            "right_step_id": item.right_step_id,
            "min_seconds_text": item.min_seconds_text,
            "max_seconds_text": item.max_seconds_text,
            "strict_lower": bool(item.strict_lower),
            "note": item.note,
        }
        for item in report.scenario.temporal_constraints
    ]

    return {
        "title": title
        or interaction.interaction_name
        or report.scenario.name
        or "SysDeSim Timeline",
        "lifelines": lifelines,
        "steps": steps_payload,
        "temporal_constraints": constraints_payload,
    }


def render_sysdesim_timeline_svg(
    *,
    xml_path: Optional[str] = None,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
    phase10_report: Optional[SysDeSimPhase10Report] = None,
    title: Optional[str] = None,
    theme: Optional[Dict[str, Any]] = None,
) -> str:
    """
    Render a SysDeSim sequence-diagram SVG.

    Either ``xml_path`` or ``phase10_report`` must be supplied. When
    ``phase10_report`` is omitted, this function imports the XML internally
    via :func:`build_sysdesim_phase10_report`.

    :param xml_path: Path to the SysDeSim XML/XMI file, optional if a
        pre-built ``phase10_report`` is given.
    :type xml_path: str, optional
    :param machine_name: Optional state-machine name selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration for ``uml:TimeEvent``
        lowering.
    :type tick_duration_ms: float, optional
    :param phase10_report: Pre-built Phase10 report.
    :type phase10_report: SysDeSimPhase10Report, optional
    :param title: Override diagram title.
    :type title: str, optional
    :param theme: Optional theme overrides forwarded to the JS renderer.
    :type theme: dict[str, Any], optional
    :return: SVG document text (UTF-8, with XML prolog).
    :rtype: str
    :raises SysdesimRenderError: If the JS bundle cannot be loaded or the
        renderer raises.
    :raises ValueError: If neither ``xml_path`` nor ``phase10_report`` is
        provided.
    """
    if phase10_report is None:
        if xml_path is None:
            raise ValueError("Either xml_path or phase10_report must be provided.")
        phase10_report = build_sysdesim_phase10_report(
            xml_path,
            machine_name=machine_name,
            interaction_name=interaction_name,
            tick_duration_ms=tick_duration_ms,
        )
    timeline_json = _build_timeline_json(phase10_report, title=title)
    options: Dict[str, Any] = {}
    if theme:
        options["theme"] = theme

    ctx, _version = _get_runtime()
    timeline_text = json.dumps(timeline_json, ensure_ascii=False)
    options_text = json.dumps(options, ensure_ascii=False)
    try:
        return ctx.eval(
            "PyfcstmSysdesim.render({timeline}, {options})".format(
                timeline=timeline_text, options=options_text
            )
        )
    except Exception as err:  # pragma: no cover - JS bundle is deterministic; defensive only
        raise SysdesimRenderError(
            "JS renderer raised: {!r}".format(err)
        ) from err


def _ensure_png_runtime(ctx) -> None:
    """
    Drive the JS-side resvg-wasm initialization to completion on ``ctx``.

    ``initWasm`` returns a Promise; py-mini-racer cannot ``await`` promises
    directly, but V8 drains microtasks between successive ``ctx.eval()``
    calls, which advances the resolution chain. The first call kicks off the
    init; we then spin on ``pngInitState()`` and trigger drains via no-op
    evals until the JS side reports ``ready`` or ``error``.

    Init runs at most once per MiniRacer context (idempotent). We tag the
    context with a private attribute so subsequent renders skip re-init.
    """
    with _PNG_INIT_LOCK:
        if getattr(ctx, "_pyfcstm_png_initialized", False):
            return
        ctx.eval("PyfcstmSysdesim.startPngInit()")
        for _ in range(_PNG_INIT_MAX_SPINS):
            state = ctx.eval("PyfcstmSysdesim.pngInitState()")
            if state == "ready":
                ctx._pyfcstm_png_initialized = True
                return
            if state == "error":
                try:
                    ctx.eval("PyfcstmSysdesim.isPngReady()")
                except Exception as err:
                    raise SysdesimRenderError(
                        "resvg-wasm init failed: {!r}".format(err)
                    ) from err
                raise SysdesimRenderError(  # pragma: no cover - defensive: JS sets either ready or error
                    "resvg-wasm init reported error without throwing."
                )
            # noop drain to advance microtasks; in practice resvg-wasm init
            # completes on the first ``pngInitState()`` poll so this branch
            # only triggers on slow hardware, which is hard to hit reliably
            # from a unit test.
            ctx.eval("0")  # pragma: no cover
        raise SysdesimRenderError(  # pragma: no cover - 400 drains is far above any observed init time
            "resvg-wasm init did not complete after {} drains.".format(_PNG_INIT_MAX_SPINS)
        )


def render_sysdesim_timeline_png(
    *,
    xml_path: Optional[str] = None,
    machine_name: Optional[str] = None,
    interaction_name: Optional[str] = None,
    tick_duration_ms: Optional[float] = None,
    phase10_report: Optional[SysDeSimPhase10Report] = None,
    title: Optional[str] = None,
    theme: Optional[Dict[str, Any]] = None,
    resvg_options: Optional[Dict[str, Any]] = None,
    font_files: Optional[List[str]] = None,
    font_buffers: Optional[List[bytes]] = None,
) -> bytes:
    """
    Render a SysDeSim sequence-diagram PNG (via resvg-wasm).

    Internally renders the SVG first and then rasterizes via the bundled
    ``@resvg/resvg-wasm`` running in the same V8 isolate as the SVG
    renderer. The first PNG render after process start pays a one-time
    wasm-instantiation cost (typically tens of milliseconds); subsequent
    renders only pay the SVG layout + raster time.

    Either ``xml_path`` or ``phase10_report`` must be supplied.

    :param xml_path: Path to the SysDeSim XML/XMI file, optional if a
        pre-built ``phase10_report`` is given.
    :type xml_path: str, optional
    :param machine_name: Optional state-machine name selector.
    :type machine_name: str, optional
    :param interaction_name: Optional interaction selector.
    :type interaction_name: str, optional
    :param tick_duration_ms: Optional tick duration for ``uml:TimeEvent``
        lowering.
    :type tick_duration_ms: float, optional
    :param phase10_report: Pre-built Phase10 report.
    :type phase10_report: SysDeSimPhase10Report, optional
    :param title: Override diagram title.
    :type title: str, optional
    :param theme: Optional theme overrides forwarded to the JS renderer.
    :type theme: dict[str, Any], optional
    :param resvg_options: Optional resvg rendering options
        (``dpi``/``fitTo``/``background``/etc., see resvg-wasm docs).
    :type resvg_options: dict[str, Any], optional
    :param font_files: Optional list of font-file paths to load. Useful for
        adding CJK / region-specific glyph coverage on top of the bundled
        DejaVu Sans fallback.
    :type font_files: list[str], optional
    :param font_buffers: Optional list of pre-loaded font byte buffers.
        Equivalent to ``font_files`` but for callers that already have the
        bytes in memory.
    :type font_buffers: list[bytes], optional
    :return: PNG bytes (begins with the standard ``\\x89PNG`` magic).
    :rtype: bytes
    :raises SysdesimRenderError: If the JS bundle cannot be loaded, the
        resvg-wasm init fails, or the renderer raises.
    :raises ValueError: If neither ``xml_path`` nor ``phase10_report`` is
        provided.

    Example::

        >>> from pyfcstm.convert.sysdesim import render_sysdesim_timeline_png
        >>> png = render_sysdesim_timeline_png(xml_path='./model.xml')  # doctest: +SKIP
        >>> png[:8] == b'\\x89PNG\\r\\n\\x1a\\n'  # doctest: +SKIP
        True
    """
    if phase10_report is None:
        if xml_path is None:
            raise ValueError("Either xml_path or phase10_report must be provided.")
        phase10_report = build_sysdesim_phase10_report(
            xml_path,
            machine_name=machine_name,
            interaction_name=interaction_name,
            tick_duration_ms=tick_duration_ms,
        )
    timeline_json = _build_timeline_json(phase10_report, title=title)
    options: Dict[str, Any] = {}
    if theme:
        options["theme"] = theme
    if resvg_options:
        options["resvg"] = resvg_options

    font_buffer_b64_list: List[str] = []
    for font_path in font_files or ():
        with open(font_path, "rb") as font_file:
            font_buffer_b64_list.append(
                base64.b64encode(font_file.read()).decode("ascii")
            )
    for buffer in font_buffers or ():
        font_buffer_b64_list.append(base64.b64encode(buffer).decode("ascii"))
    if font_buffer_b64_list:
        options["fontBuffersB64"] = font_buffer_b64_list

    ctx, _version = _get_runtime()
    _ensure_png_runtime(ctx)
    timeline_text = json.dumps(timeline_json, ensure_ascii=False)
    options_text = json.dumps(options, ensure_ascii=False)
    try:
        b64_text = ctx.eval(
            "PyfcstmSysdesim.renderPng({timeline}, {options})".format(
                timeline=timeline_text, options=options_text
            )
        )
    except Exception as err:  # pragma: no cover - resvg-wasm failures are surfaced as SysdesimRenderError
        raise SysdesimRenderError(
            "JS PNG renderer raised: {!r}".format(err)
        ) from err
    return base64.b64decode(b64_text)


__all__ = [
    "SysdesimRenderError",
    "render_sysdesim_timeline_png",
    "render_sysdesim_timeline_svg",
]

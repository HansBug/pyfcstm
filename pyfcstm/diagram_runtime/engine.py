"""
Run the shared offline diagram renderer inside a constrained MiniRacer host.

This module is an internal feasibility surface for PR-A. The public Python
``StateMachine.diagram`` API is intentionally deferred to the continuation
work described by PR #383.
"""

import base64
import json
import math
import pkgutil
import time
from typing import Any, Dict


class DiagramAssetError(RuntimeError):
    """Raised when the embedded renderer or its generated assets fail."""


def _asset_bytes(name: str) -> bytes:
    """Load one generated asset through the Python 3.7-compatible resource API."""
    data = pkgutil.get_data("pyfcstm.assets", name)
    if data is None:
        raise DiagramAssetError("missing generated diagram asset: %s" % name)
    return data


class DiagramAssetEngine:
    """
    Drive the shared ES2017 renderer and resvg bridge in MiniRacer.

    :param timeout: Maximum seconds for one ELK/render polling operation,
        which must be finite and positive, defaults to ``30.0``.
    :type timeout: float, optional

    Example::

        >>> engine = DiagramAssetEngine()
        >>> svg = engine.render_svg({"diagram": diagram_data})
        >>> svg.startswith("<svg")
        True
    """

    def __init__(self, timeout: float = 30.0) -> None:
        numeric_timeout = float(timeout)
        if not math.isfinite(numeric_timeout) or numeric_timeout <= 0:
            raise ValueError("timeout must be a finite positive number")
        self.timeout = numeric_timeout
        self._context = self._create_context()
        self._resvg_ready = False
        self._load_bundle()

    @staticmethod
    def _create_context() -> Any:
        """Create the Python-version-appropriate MiniRacer context."""
        try:
            from py_mini_racer import MiniRacer
        except ImportError as top_level_error:
            # Legacy py-mini-racer exports MiniRacer from this submodule.
            try:
                from py_mini_racer.py_mini_racer import MiniRacer
            except ImportError:
                # Preserve a modern package's native import/ABI failure when
                # neither supported export shape is available.
                raise top_level_error
        return MiniRacer()

    def _eval(self, source: str) -> Any:
        """Evaluate JavaScript and preserve the native exception boundary."""
        return self._context.eval(source)

    def _load_bundle(self) -> None:
        """Load the host shim and verified renderer bundle once."""
        self._eval(_asset_bytes("host-shim.js").decode("utf-8"))
        self._eval("globalThis.__pyfcstm_embedded_host = true;")
        self._eval(_asset_bytes("renderer.js").decode("utf-8"))

    def _poll(self, request_id: str) -> Dict[str, Any]:
        """Read one renderer job status from the JS context."""
        value = self._eval("__pyfcstm_render_poll(%s)" % json.dumps(request_id))
        return json.loads(str(value))

    def render_svg(self, request: Dict[str, Any]) -> str:
        """
        Render a canonical DiagramData request to SVG.

        :param request: JSON-compatible object containing ``diagram`` and
            optional renderer options.
        :type request: dict
        :return: UTF-8 SVG text.
        :rtype: str
        :raises DiagramAssetError: If the JS job reports an error or times out.
        """
        request_id = "pyfcstm-%d" % time.monotonic_ns()
        self._eval(
            "__pyfcstm_render_start(%s, %s)"
            % (
                json.dumps(json.dumps(request, ensure_ascii=False)),
                json.dumps(request_id),
            )
        )
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            status = self._poll(request_id)
            if status.get("status") == "done":
                self._eval("__pyfcstm_render_drop(%s)" % json.dumps(request_id))
                return str(status["svg"])
            if status.get("status") == "error":
                self._eval("__pyfcstm_render_drop(%s)" % json.dumps(request_id))
                raise DiagramAssetError(
                    str(status.get("error", "unknown renderer error"))
                )
            time.sleep(0.001)
        self._eval("__pyfcstm_render_drop(%s)" % json.dumps(request_id))
        raise DiagramAssetError("diagram renderer timed out after %.1fs" % self.timeout)

    def _ensure_resvg(self) -> None:
        """Compile the pinned WASM and register the deterministic font once."""
        if self._resvg_ready:
            return
        wasm = base64.b64encode(_asset_bytes("resvg.wasm")).decode("ascii")
        self._eval("__pyfcstm_resvg_init(%s)" % json.dumps(wasm))
        deadline = time.monotonic() + self.timeout
        while time.monotonic() < deadline:
            status = str(self._eval("__pyfcstm_resvg_status"))
            if status == "ok":
                font = base64.b64encode(
                    _asset_bytes("fonts/JetBrainsMono-Regular.ttf")
                ).decode("ascii")
                self._eval("__pyfcstm_resvg_register_font(%s)" % json.dumps(font))
                self._resvg_ready = True
                return
            if status == "error":
                raise DiagramAssetError(str(self._eval("__pyfcstm_resvg_error")))
            time.sleep(0.001)
        raise DiagramAssetError("resvg WASM initialization timed out")

    def render_png(self, svg: str, scale: float = 1.0) -> bytes:
        """
        Rasterize SVG text with the pinned resvg WASM backend.

        :param svg: SVG text returned by :meth:`render_svg`.
        :type svg: str
        :param scale: Finite positive raster scale, defaults to ``1.0``.
        :type scale: float, optional
        :return: PNG bytes.
        :rtype: bytes
        :raises ValueError: If ``scale`` is not finite and positive.
        :raises DiagramAssetError: If resvg reports a rendering failure.
        """
        numeric_scale = float(scale)
        if not math.isfinite(numeric_scale) or numeric_scale <= 0:
            raise ValueError("scale must be a finite positive number")
        self._ensure_resvg()
        encoded = self._eval(
            "__pyfcstm_resvg_png(%s, %s)"
            % (json.dumps(svg), json.dumps(numeric_scale))
        )
        return base64.b64decode(str(encoded))

    def expand_svg(self, svg: str) -> str:
        """
        Expand SVG markers and text into resvg's normalized vector SVG.

        :param svg: SVG text.
        :type svg: str
        :return: Normalized vector SVG text.
        :rtype: str
        """
        self._ensure_resvg()
        return str(self._eval("__pyfcstm_resvg_expand(%s)" % json.dumps(svg)))

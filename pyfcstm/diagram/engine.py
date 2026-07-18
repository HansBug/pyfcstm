"""
Run the shared offline diagram renderer inside a constrained MiniRacer host.

This module is an internal feasibility surface for PR-A. The public Python
``StateMachine.diagram`` API is intentionally deferred to the continuation
work described by PR #383.
"""

import base64
import inspect
import json
import math
import pkgutil
import time
from typing import Any, Dict, Optional


class DiagramAssetError(RuntimeError):
    """Raised when the embedded renderer or its generated assets fail."""


class DiagramEngineMetadataError(DiagramAssetError):
    """Raised when installed MiniRacer distributions cannot be inspected."""


class DiagramEngineConflictError(DiagramAssetError):
    """
    Report mutually exclusive MiniRacer distributions.

    This error is raised before a JavaScript context is created when both
    ``mini-racer`` and ``py-mini-racer`` are installed in one environment.
    """


def _asset_bytes(name: str) -> bytes:
    """Load one generated asset through the Python 3.7-compatible resource API."""
    data = pkgutil.get_data("pyfcstm.diagram.assets", name)
    if data is None:
        raise DiagramAssetError("missing generated diagram asset: %s" % name)
    return data


class DiagramAssetEngine:
    """
    Drive the shared ES2017 renderer and resvg bridge in MiniRacer.

    :param timeout: Maximum seconds for one ELK/render polling operation,
        which must be finite and positive, defaults to ``30.0``.
    :type timeout: float, optional
    :param max_memory: Optional V8 heap limit in bytes applied to each
        JavaScript evaluation, defaults to ``None``.
    :type max_memory: int, optional

    Example::

        >>> engine = DiagramAssetEngine()
        >>> svg = engine.render_svg({"diagram": diagram_data})
        >>> svg.startswith("<svg")
        True
    """

    def __init__(self, timeout: float = 30.0, max_memory: Optional[int] = None) -> None:
        numeric_timeout = float(timeout)
        if not math.isfinite(numeric_timeout) or numeric_timeout <= 0:
            raise ValueError("timeout must be a finite positive number")
        if max_memory is not None:
            if isinstance(max_memory, bool) or not isinstance(max_memory, int):
                raise ValueError("max_memory must be a finite positive integer or None")
            if max_memory <= 0:
                raise ValueError("max_memory must be a finite positive integer or None")
        self.timeout = numeric_timeout
        self.max_memory = max_memory
        self._context = None
        self._resvg_ready = False
        self._timeout_uses_seconds = False
        self._interrupt_errors = ()
        self._ensure_context()

    @staticmethod
    def _distribution_version(name: str) -> Optional[str]:
        """Return one distribution version, or ``None`` when absent."""
        try:
            from importlib import metadata
        except ImportError:
            # Python 3.7 has no stdlib importlib.metadata; the backport is
            # optional, so fall back to setuptools when it is unavailable.
            try:
                import importlib_metadata as metadata
            except ImportError:
                try:
                    from pkg_resources import DistributionNotFound, get_distribution
                except ImportError as err:
                    # ImportError: Python 3.7 has no metadata provider and the
                    # optional backport/setuptools fallback is unavailable.
                    raise DiagramEngineMetadataError(
                        "cannot inspect installed MiniRacer distributions; "
                        "install importlib-metadata or setuptools"
                    ) from err
                try:
                    return str(get_distribution(name).version)
                except DistributionNotFound:
                    return None
        try:
            return str(metadata.version(name))
        except metadata.PackageNotFoundError:
            return None

    @staticmethod
    def _distribution_installed(name: str) -> bool:
        """Return whether a MiniRacer distribution is installed."""
        return DiagramAssetEngine._distribution_version(name) is not None

    def _create_context(self) -> Any:
        """Create the Python-version-appropriate MiniRacer context."""
        if self._distribution_installed("mini-racer") and self._distribution_installed(
            "py-mini-racer"
        ):
            modern_version = self._distribution_version("mini-racer") or "unknown"
            legacy_version = self._distribution_version("py-mini-racer") or "unknown"
            raise DiagramEngineConflictError(
                "mini-racer %s and py-mini-racer %s are installed together; "
                "install exactly one runtime for this Python version"
                % (modern_version, legacy_version)
            )
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
        try:
            from py_mini_racer import JSOOMException, JSTimeoutException
        except ImportError:
            # py-mini-racer 0.6 keeps these exception classes in its legacy
            # module; modern mini-racer exports them at package top level.
            from py_mini_racer.py_mini_racer import JSOOMException, JSTimeoutException
        self._interrupt_errors = (JSTimeoutException, JSOOMException)
        self._timeout_uses_seconds = (
            "timeout_sec" in inspect.signature(MiniRacer.eval).parameters
        )
        return MiniRacer()

    def _ensure_context(self) -> None:
        """Create and initialize a context after startup or interruption."""
        if self._context is None:
            self._context = self._create_context()
            self._load_bundle()

    def _discard_context(self) -> None:
        """Drop a context that was interrupted or exceeded its heap limit."""
        context = self._context
        self._context = None
        self._resvg_ready = False
        if context is None:
            return
        close = getattr(context, "close", None)
        if callable(close):
            close()

    def _eval(self, source: str, timeout: Optional[float] = None) -> Any:
        """
        Evaluate JavaScript with the native MiniRacer resource limits.

        :param source: JavaScript source text to evaluate.
        :type source: str
        :param timeout: Evaluation limit in seconds, defaults to the engine
            timeout.
        :type timeout: float, optional
        :return: The converted MiniRacer result.
        :rtype: object
        :raises DiagramAssetError: If MiniRacer interrupts execution.
        """
        numeric_timeout = self.timeout if timeout is None else float(timeout)
        if not math.isfinite(numeric_timeout) or numeric_timeout <= 0:
            raise ValueError("timeout must be a finite positive number")
        self._ensure_context()
        try:
            if self._timeout_uses_seconds:
                return self._context.eval(
                    source,
                    timeout_sec=numeric_timeout,
                    max_memory=self.max_memory,
                )
            # py-mini-racer 0.6 accepts milliseconds and does not understand
            # the modern ``timeout_sec`` keyword.
            timeout_ms = max(1, int(math.ceil(numeric_timeout * 1000.0)))
            return self._context.eval(
                source,
                timeout=timeout_ms,
                max_memory=self.max_memory,
            )
        except Exception as err:
            # JSTimeoutException/JSOOMException are the only expected native
            # interruption failures; every other exception must propagate.
            if not isinstance(err, self._interrupt_errors):
                raise
            self._discard_context()
            raise DiagramAssetError(
                "embedded MiniRacer evaluation exceeded its time or memory limit"
            ) from err

    def _load_bundle(self) -> None:
        """Load the host shim and verified renderer bundle once."""
        self._eval(_asset_bytes("host-shim.js").decode("utf-8"))
        self._eval("globalThis.__pyfcstm_embedded_host = true;")
        self._eval(_asset_bytes("renderer.js").decode("utf-8"))

    def _poll(self, request_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Read one renderer job status from the JS context."""
        value = self._eval(
            "__pyfcstm_render_poll(%s)" % json.dumps(request_id), timeout=timeout
        )
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
        deadline = time.monotonic() + self.timeout
        self._eval(
            "__pyfcstm_render_start(%s, %s)"
            % (
                json.dumps(json.dumps(request, ensure_ascii=False)),
                json.dumps(request_id),
            ),
            timeout=self.timeout,
        )
        while time.monotonic() < deadline:
            remaining = max(0.001, deadline - time.monotonic())
            status = self._poll(request_id, timeout=remaining)
            if status.get("status") == "done":
                self._eval(
                    "__pyfcstm_render_drop(%s)" % json.dumps(request_id),
                    timeout=remaining,
                )
                return str(status["svg"])
            if status.get("status") == "error":
                self._eval(
                    "__pyfcstm_render_drop(%s)" % json.dumps(request_id),
                    timeout=remaining,
                )
                error = str(status.get("error", "unknown renderer error"))
                self._discard_context()
                raise DiagramAssetError(error)
            time.sleep(0.001)
        # The renderer promise may still be pending in the old context.  A
        # Python-side deadline is therefore terminal too: discard the whole
        # context instead of allowing the next request to observe stale jobs.
        self._discard_context()
        raise DiagramAssetError("diagram renderer timed out after %.1fs" % self.timeout)

    def _ensure_resvg(self) -> None:
        """Compile the pinned WASM and register the deterministic font once."""
        if self._resvg_ready:
            return
        wasm = base64.b64encode(_asset_bytes("resvg.wasm")).decode("ascii")
        deadline = time.monotonic() + self.timeout
        self._eval("__pyfcstm_resvg_init(%s)" % json.dumps(wasm), timeout=self.timeout)
        while time.monotonic() < deadline:
            remaining = max(0.001, deadline - time.monotonic())
            status = str(self._eval("__pyfcstm_resvg_status", timeout=remaining))
            if status == "ok":
                font = base64.b64encode(
                    _asset_bytes("fonts/JetBrainsMono-Regular.ttf")
                ).decode("ascii")
                self._eval(
                    "__pyfcstm_resvg_register_font(%s)" % json.dumps(font),
                    timeout=remaining,
                )
                self._resvg_ready = True
                return
            if status == "error":
                error = str(self._eval("__pyfcstm_resvg_error", timeout=remaining))
                self._discard_context()
                raise DiagramAssetError(error)
            time.sleep(0.001)
        self._discard_context()
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
            % (json.dumps(svg), json.dumps(numeric_scale)),
            timeout=self.timeout,
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
        return str(
            self._eval(
                "__pyfcstm_resvg_expand(%s)" % json.dumps(svg),
                timeout=self.timeout,
            )
        )

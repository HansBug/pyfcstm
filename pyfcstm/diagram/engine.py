"""
Run the shared offline diagram renderer inside a constrained MiniRacer host.

This module is an internal feasibility surface for PR-A. The public Python
``StateMachine.diagram`` API is intentionally deferred to the continuation
work described by PR #383.
"""

import base64
import binascii
import inspect
import json
import math
import pkgutil
import re
import time
from pathlib import Path
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


_LATIN_FONT_ASSET_PATHS = (
    "fonts/JetBrainsMono-Regular.ttf",
    "fonts/JetBrainsMono-Medium.ttf",
    "fonts/JetBrainsMono-Bold.ttf",
)

_CJK_FONT_ASSET_PATHS = {
    "sc": ("fonts/NotoSansSC-Regular.otf", "fonts/NotoSansSC-Bold.otf"),
    "tc": ("fonts/NotoSansTC-Regular.otf", "fonts/NotoSansTC-Bold.otf"),
    "hk": ("fonts/NotoSansHK-Regular.otf", "fonts/NotoSansHK-Bold.otf"),
    "jp": ("fonts/NotoSansJP-Regular.otf", "fonts/NotoSansJP-Bold.otf"),
    "kr": ("fonts/NotoSansKR-Regular.otf", "fonts/NotoSansKR-Bold.otf"),
}

_CJK_FONT_FAMILIES = {
    "sc": "Noto Sans SC",
    "tc": "Noto Sans TC",
    "hk": "Noto Sans HK",
    "jp": "Noto Sans JP",
    "kr": "Noto Sans KR",
}
_CJK_LOCALE_PATTERN = re.compile(
    r"Noto Sans(?: Mono CJK|)\s+(SC|TC|HK|JP|KR)\b", re.IGNORECASE
)

_ASSET_ISSUE_URL = "https://github.com/HansBug/pyfcstm/issues"


def _is_development_checkout() -> bool:
    """Return whether the package is running from the repository checkout."""
    root = Path(__file__).resolve().parents[2]
    return (root / "Makefile").is_file() and (
        root / "tools" / "build_diagram_assets.py"
    ).is_file()


def _asset_failure(
    name: str, cause: str, error: Optional[BaseException] = None
) -> DiagramAssetError:
    """Build a loud, actionable error for a missing or unusable asset."""
    detail = str(cause).strip() or "the resource failed validation"
    if error is not None and str(error).strip():
        detail = "%s: %s" % (detail, str(error).strip())
    if _is_development_checkout():
        action = (
            "This appears to be a development checkout; run `make build_assets` "
            "and retry."
        )
    else:
        action = (
            "This appears to be an installed package or CLI; report this failure "
            "at %s with the Python version, pyfcstm version, and this full error."
            % _ASSET_ISSUE_URL
        )
    return DiagramAssetError(
        "pyfcstm diagram asset failure for %s: %s. %s" % (name, detail, action)
    )


def _asset_bytes(name: str) -> bytes:
    """Load and minimally validate one generated asset."""
    try:
        data = pkgutil.get_data("pyfcstm.diagram.assets", name)
    except OSError as err:
        # OSError: importlib/pkgutil could not read a packaged resource.
        raise _asset_failure(
            name, "the packaged resource could not be read", err
        ) from err
    if data is None:
        raise _asset_failure(name, "the expected packaged resource is missing")
    if not data:
        raise _asset_failure(name, "the packaged resource is empty")
    if name.endswith(".js"):
        try:
            text = data.decode("utf-8")
        except UnicodeDecodeError as err:
            raise _asset_failure(
                name, "the JavaScript resource is not valid UTF-8", err
            ) from err
        if not text.strip():
            raise _asset_failure(name, "the JavaScript resource is empty")
    elif name == "resvg.wasm" and not data.startswith(b"\x00asm"):
        raise _asset_failure(name, "the resource is not a WebAssembly binary")
    elif name.startswith("fonts/") and not (
        data.startswith((b"\x00\x01\x00\x00", b"true", b"OTTO", b"ttcf"))
    ):
        raise _asset_failure(name, "the resource is not a supported OpenType font")
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
        self._resvg_locale = None
        self._timeout_uses_seconds = False
        self._interrupt_errors = ()
        self._asset_eval_errors = ()
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
            from py_mini_racer import (
                JSEvalException,
                JSOOMException,
                JSParseException,
                JSTimeoutException,
            )
        except ImportError:
            # py-mini-racer 0.6 keeps these exception classes in its legacy
            # module; modern mini-racer exports them at package top level.
            from py_mini_racer.py_mini_racer import (
                JSEvalException,
                JSOOMException,
                JSParseException,
                JSTimeoutException,
            )
        self._interrupt_errors = (JSTimeoutException, JSOOMException)
        self._asset_eval_errors = (JSEvalException, JSParseException)
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
        self._resvg_locale = None
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
        try:
            host_shim = _asset_bytes("host-shim.js").decode("utf-8")
            renderer = _asset_bytes("renderer.js").decode("utf-8")
        except DiagramAssetError:
            self._discard_context()
            raise
        if "__pyfcstm_render_start" not in renderer:
            self._discard_context()
            raise _asset_failure(
                "renderer.js",
                "the bundle does not expose the required renderer entrypoint",
            )
        self._eval_asset("host-shim.js", host_shim)
        self._eval_asset("host-shim.js", "globalThis.__pyfcstm_embedded_host = true;")
        self._eval_asset("renderer.js", renderer)

    def _eval_asset(
        self, name: str, source: str, timeout: Optional[float] = None
    ) -> Any:
        """Evaluate an asset and attach the asset name to JavaScript failures."""
        try:
            return self._eval(source, timeout=timeout)
        except self._asset_eval_errors as err:
            self._discard_context()
            raise _asset_failure(
                name, "the JavaScript resource could not be evaluated", err
            ) from err

    def _poll(self, request_id: str, timeout: Optional[float] = None) -> Dict[str, Any]:
        """Read one renderer job status from the JS context."""
        value = self._eval_asset(
            "renderer.js",
            "__pyfcstm_render_poll(%s)" % json.dumps(request_id),
            timeout=timeout,
        )
        try:
            status = json.loads(str(value))
        except (TypeError, ValueError) as err:
            # TypeError/ValueError: a corrupted renderer returned non-JSON
            # polling data instead of its documented status envelope.
            raise _asset_failure(
                "renderer.js", "the renderer returned invalid job status data", err
            ) from err
        if not isinstance(status, dict):
            raise _asset_failure(
                "renderer.js", "the renderer returned a non-object job status"
            )
        return status

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
        self._eval_asset(
            "renderer.js",
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
                self._eval_asset(
                    "renderer.js",
                    "__pyfcstm_render_drop(%s)" % json.dumps(request_id),
                    timeout=remaining,
                )
                try:
                    svg = str(status["svg"])
                except KeyError as err:
                    raise _asset_failure(
                        "renderer.js", "the completed job omitted its SVG output", err
                    ) from err
                if not svg.lstrip().startswith("<svg"):
                    raise _asset_failure(
                        "renderer.js", "the renderer returned malformed SVG output"
                    )
                return svg
            if status.get("status") == "error":
                self._eval_asset(
                    "renderer.js",
                    "__pyfcstm_render_drop(%s)" % json.dumps(request_id),
                    timeout=remaining,
                )
                error = str(status.get("error", "unknown renderer error"))
                self._discard_context()
                raise _asset_failure(
                    "renderer.js", "the renderer job failed", ValueError(error)
                )
            time.sleep(0.001)
        # The renderer promise may still be pending in the old context.  A
        # Python-side deadline is therefore terminal too: discard the whole
        # context instead of allowing the next request to observe stale jobs.
        self._discard_context()
        raise DiagramAssetError("diagram renderer timed out after %.1fs" % self.timeout)

    def _ensure_resvg(self, cjk_locale: str = "sc") -> None:
        """Compile resvg and lazily register the selected locale's font pair."""
        locale = str(cjk_locale).lower()
        if locale not in _CJK_FONT_ASSET_PATHS:
            raise ValueError("unsupported CJK locale: %s" % cjk_locale)
        if self._resvg_ready and self._resvg_locale != locale:
            # resvg retains parsed font data inside the WASM heap. Recreate the
            # context when switching locales so a long-lived Python process
            # does not accumulate every CJK face it has rendered.
            self._discard_context()
        wasm_bytes = _asset_bytes("resvg.wasm")
        wasm = base64.b64encode(wasm_bytes).decode("ascii")
        deadline = time.monotonic() + self.timeout
        if not self._resvg_ready:
            self._eval_asset(
                "resvg.wasm",
                "__pyfcstm_resvg_init(%s)" % json.dumps(wasm),
            )
        while time.monotonic() < deadline:
            remaining = max(0.001, deadline - time.monotonic())
            status = (
                "ok"
                if self._resvg_ready
                else str(
                    self._eval_asset(
                        "resvg.wasm", "__pyfcstm_resvg_status", timeout=remaining
                    )
                )
            )
            if status == "ok" and self._resvg_locale != locale:
                font_paths = _LATIN_FONT_ASSET_PATHS + _CJK_FONT_ASSET_PATHS[locale]
                fonts = [
                    base64.b64encode(_asset_bytes(path)).decode("ascii")
                    for path in font_paths
                ]
                self._eval_asset(
                    "fonts/*",
                    "__pyfcstm_resvg_register_fonts(%s, %s)"
                    % (json.dumps(fonts), json.dumps(_CJK_FONT_FAMILIES[locale])),
                    timeout=remaining,
                )
                self._resvg_ready = True
                self._resvg_locale = locale
                return
            if status == "ok":
                return
            if status == "error":
                error = str(
                    self._eval_asset(
                        "resvg.wasm", "__pyfcstm_resvg_error", timeout=remaining
                    )
                )
                self._discard_context()
                raise _asset_failure(
                    "resvg.wasm", "WASM initialization failed", ValueError(error)
                )
            time.sleep(0.001)
        self._discard_context()
        raise _asset_failure("resvg.wasm", "resvg WASM initialization timed out")

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
        self._ensure_resvg(self._locale_from_svg(svg))
        encoded = self._eval_asset(
            "resvg.wasm",
            "__pyfcstm_resvg_png(%s, %s)"
            % (json.dumps(svg), json.dumps(numeric_scale)),
        )
        try:
            result = base64.b64decode(str(encoded), validate=True)
        except (ValueError, binascii.Error) as err:
            # ValueError/binascii.Error: the WASM bridge returned malformed
            # base64 instead of a PNG payload.
            raise _asset_failure(
                "resvg.wasm", "the renderer returned invalid PNG data", err
            ) from err
        if not result.startswith(b"\x89PNG\r\n\x1a\n"):
            raise _asset_failure(
                "resvg.wasm", "the renderer returned a non-PNG payload"
            )
        return result

    def expand_svg(self, svg: str) -> str:
        """
        Expand SVG markers and text into resvg's normalized vector SVG.

        :param svg: SVG text.
        :type svg: str
        :return: Normalized vector SVG text.
        :rtype: str
        """
        self._ensure_resvg(self._locale_from_svg(svg))
        expanded = str(
            self._eval_asset(
                "resvg.wasm",
                "__pyfcstm_resvg_expand(%s)" % json.dumps(svg),
                timeout=self.timeout,
            )
        )
        stripped = expanded.strip()
        if not stripped.startswith("<svg") or not (
            stripped.endswith("</svg>") or stripped.endswith("/>")
        ):
            raise _asset_failure(
                "resvg.wasm", "the renderer returned malformed expanded SVG output"
            )
        return expanded

    @staticmethod
    def _locale_from_svg(svg: str) -> str:
        """Infer the embedded CJK face from an SVG font-family attribute."""
        match = _CJK_LOCALE_PATTERN.search(str(svg))
        return match.group(1).lower() if match else "sc"

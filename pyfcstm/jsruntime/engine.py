"""
JavaScript engine adapter used by :mod:`pyfcstm.visualize`.

The renderer pipeline lives entirely inside a JS sandbox driven by a
single shared bundle (``pyfcstm/jsruntime/bundle.js``). This module
hides which mini-racer flavour is in use:

* On Python 3.8+ we prefer ``mini-racer`` (the modern fork).
* On Python 3.7 we fall back to ``py-mini-racer`` 0.6.x.

Both libraries expose an ``eval(code)`` method that compiles + executes
JavaScript in V8. The output of ``eval`` returns to Python; the wrapper
in this module also takes care of:

* loading the host shim (``shim.js``) so jsfcstm / elkjs / resvg-wasm
  see the globals they expect;
* loading the prebuilt JS bundle (``bundle.js``) once per engine;
* compiling the resvg WebAssembly blob once per engine;
* registering a default monospace font for the resvg renderer;
* wrapping ``__fcstm_export(...)`` calls and turning the base64 result
  back into Python ``bytes``.

Public API:

* :func:`get_engine` — process-wide singleton accessor
* :class:`JsEngine` — abstract base / interface
* :func:`reset_engine` — drop the cached singleton (useful for tests)
"""
import base64
import json
import sys
import threading
from pathlib import Path
from typing import Optional

__all__ = [
    'JsEngine',
    'JsEngineError',
    'JsEngineUnavailableError',
    'get_engine',
    'reset_engine',
    'BUNDLE_DIR',
]

BUNDLE_DIR = Path(__file__).resolve().parent
SHIM_PATH = BUNDLE_DIR / 'shim.js'
BUNDLE_PATH = BUNDLE_DIR / 'bundle.js'
WASM_PATH = BUNDLE_DIR / 'resvg.wasm'
DEFAULT_FONT_PATH = BUNDLE_DIR / 'fonts' / 'JetBrainsMono-Regular.ttf'


class JsEngineError(RuntimeError):
    """Raised when the JS bundle reports a runtime / pipeline error."""


class JsEngineUnavailableError(ImportError):
    """
    Raised when no compatible mini-racer flavour can be imported.

    Usually means the user installed plain ``pyfcstm`` and forgot to
    install the ``viz`` extras (``pip install pyfcstm[viz]``).
    """


class JsEngine:
    """
    Abstract interface implemented by the two mini-racer adapters.

    Concrete subclasses must implement :meth:`_eval_raw`. Every other
    method on this class is built on top of it, including the
    ``__fcstm_export`` wrapper used by :mod:`pyfcstm.visualize`.
    """

    name: str = 'jsengine'

    def __init__(self) -> None:
        self._initialized = False
        self._font_loaded = False

    # ------------------------------------------------------------------
    # subclass hook
    # ------------------------------------------------------------------
    def _eval_raw(self, code: str):  # pragma: no cover - overridden
        raise NotImplementedError

    # ------------------------------------------------------------------
    # one-shot setup
    # ------------------------------------------------------------------
    def initialize(self) -> None:
        """
        Load the shim, the JS bundle, and the resvg WASM blob.

        Idempotent — subsequent calls are no-ops. Splitting this from
        :meth:`__init__` keeps the engine cheap to construct in tests
        that never actually need to render anything.
        """
        if self._initialized:
            return
        self._eval_raw(SHIM_PATH.read_text(encoding='utf-8'))
        self._eval_raw(BUNDLE_PATH.read_text(encoding='utf-8'))
        wasm_b64 = base64.b64encode(WASM_PATH.read_bytes()).decode('ascii')
        self._eval_raw(f'__fcstm_init_wasm({json.dumps(wasm_b64)})')
        status = self._eval_raw('__fcstm_wasm_status')
        if status != 'ok':
            err = self._eval_raw('__fcstm_wasm_error')
            raise JsEngineError(
                f'resvg WASM init failed (status={status!r}): {err}'
            )
        self._initialized = True

    def ensure_default_font(self) -> None:
        """Register the bundled JetBrains Mono Regular face once."""
        if self._font_loaded:
            return
        font_b64 = base64.b64encode(
            DEFAULT_FONT_PATH.read_bytes()
        ).decode('ascii')
        self._eval_raw(f'__fcstm_register_font({json.dumps(font_b64)})')
        self._font_loaded = True

    # ------------------------------------------------------------------
    # render
    # ------------------------------------------------------------------
    def export(self, fmt: str, dsl_text: str, options: Optional[dict],
               scale: float = 1.0) -> bytes:
        """
        Drive a single ``__fcstm_export`` round-trip.

        :param fmt: ``'svg'`` or ``'png'``.
        :param dsl_text: The FCSTM DSL source as a Python ``str``.
        :param options: Optional preview-options dict; passed through to
            :func:`resolveFcstmDiagramPreviewOptions` on the JS side. May
            be ``None`` to use defaults.
        :param scale: Raster scale factor (only meaningful for PNG).
        :return: Raw bytes of the rendered output (UTF-8 SVG bytes for
            ``'svg'``, PNG bytes for ``'png'``).
        :raises JsEngineError: If the JS pipeline reports an error.
        """
        self.initialize()
        self.ensure_default_font()
        opts_arg = json.dumps(json.dumps(options)) if options else 'null'
        call = (
            f'__fcstm_export({json.dumps(fmt)}, {json.dumps(dsl_text)}, '
            f'{opts_arg}, {float(scale)!r})'
        )
        self._eval_raw(call)
        err = self._eval_raw('__fcstm_export_error')
        if err:
            raise JsEngineError(str(err))
        result = self._eval_raw('__fcstm_export_result')
        if result is None:
            raise JsEngineError(
                'JS bundle returned no result and no error '
                '(microtask queue may not have drained)'
            )
        return base64.b64decode(result)


class MiniRacerEngine(JsEngine):
    """Adapter for the modern ``mini-racer`` package (Python 3.8+)."""

    name = 'mini-racer'

    def __init__(self) -> None:
        super().__init__()
        from py_mini_racer import MiniRacer  # type: ignore[import-not-found]
        self._ctx = MiniRacer()

    def _eval_raw(self, code: str):
        return self._ctx.eval(code)


class PyMiniRacerEngine(JsEngine):
    """Adapter for the legacy ``py-mini-racer`` 0.6.x (Python 3.7)."""

    name = 'py-mini-racer'

    def __init__(self) -> None:
        super().__init__()
        from py_mini_racer.py_mini_racer import (  # type: ignore[import-not-found]
            MiniRacer,
        )
        self._ctx = MiniRacer()

    def _eval_raw(self, code: str):
        return self._ctx.eval(code)


def _build_engine() -> JsEngine:
    """
    Pick the engine adapter that fits the current Python version and
    the installed mini-racer flavour.

    Both wheels publish under the ``py_mini_racer`` import name. The
    modern wheel exposes the class straight off the top-level package;
    the 0.6.x line nests it inside a submodule and is what we used to
    rely on for Python 3.7. We try the modern path first regardless of
    Python version so a 3.7 user who somehow installed the new wheel
    still gets the new behaviour.
    """
    if sys.version_info >= (3, 8):
        try:
            return MiniRacerEngine()
        except ImportError:
            pass
    try:
        return PyMiniRacerEngine()
    except ImportError as exc:  # pragma: no cover - exercised in tests
        raise JsEngineUnavailableError(
            'No compatible mini-racer flavour is installed. '
            'Install the visualization extras: pip install pyfcstm[viz]'
        ) from exc


_engine_lock = threading.Lock()
_engine_instance: Optional[JsEngine] = None


def get_engine() -> JsEngine:
    """
    Return a process-wide singleton engine.

    The bundle and the resvg WASM blob each take ~100ms to load, so we
    reuse the same V8 context across calls.
    """
    global _engine_instance
    with _engine_lock:
        if _engine_instance is None:
            _engine_instance = _build_engine()
        return _engine_instance


def reset_engine() -> None:
    """Drop the cached singleton (used by tests to enforce isolation)."""
    global _engine_instance
    with _engine_lock:
        _engine_instance = None

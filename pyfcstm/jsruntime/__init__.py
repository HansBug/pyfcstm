"""
Embedded JavaScript runtime backing :mod:`pyfcstm.visualize`.

Exposes the engine adapter and the file paths of the bundled assets,
so callers (and tests) can introspect them without poking at private
internals.
"""
from .engine import (
    BUNDLE_DIR,
    JsEngine,
    JsEngineError,
    JsEngineUnavailableError,
    get_engine,
    reset_engine,
)

__all__ = [
    'BUNDLE_DIR',
    'JsEngine',
    'JsEngineError',
    'JsEngineUnavailableError',
    'get_engine',
    'reset_engine',
]

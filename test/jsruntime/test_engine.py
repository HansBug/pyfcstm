"""
Tests for :mod:`pyfcstm.jsruntime`.

Hits every branch in ``engine.py``. The engine itself is exercised
end-to-end (it loads the real bundle + the real WASM) because there is
no realistic way to mock an entire V8 context without losing the value
of the test.
"""
import sys

import pytest

from pyfcstm import jsruntime
from pyfcstm.jsruntime import (
    BUNDLE_DIR,
    JsEngine,
    JsEngineError,
    JsEngineUnavailableError,
    get_engine,
    reset_engine,
)
from pyfcstm.jsruntime import engine as engine_module


SIMPLE_DSL = (
    'def int counter = 0;\n'
    'state Demo { [*] -> Idle; state Idle; }\n'
)


@pytest.fixture(autouse=True)
def _reset_singleton():
    reset_engine()
    yield
    reset_engine()


@pytest.mark.unittest
class TestEnginePublicSurface:
    def test_paths_exist(self):
        assert (BUNDLE_DIR / 'shim.js').is_file()
        assert (BUNDLE_DIR / 'bundle.js').is_file()
        assert (BUNDLE_DIR / 'resvg.wasm').is_file()
        assert (BUNDLE_DIR / 'fonts' / 'JetBrainsMono-Regular.ttf').is_file()

    def test_get_engine_returns_singleton(self):
        first = get_engine()
        second = get_engine()
        assert first is second

    def test_reset_engine_drops_singleton(self):
        first = get_engine()
        reset_engine()
        second = get_engine()
        assert first is not second


@pytest.mark.unittest
class TestRender:
    def test_export_svg_returns_utf8_bytes(self):
        e = get_engine()
        out = e.export('svg', SIMPLE_DSL, None, 1.0)
        text = out.decode('utf-8')
        assert text.startswith('<svg')
        assert 'data-fcstm-canvas="true"' in text

    def test_export_png_starts_with_png_magic(self):
        e = get_engine()
        out = e.export('png', SIMPLE_DSL, {'direction': 'DOWN'}, 1.0)
        assert out[:8] == b'\x89PNG\r\n\x1a\n'

    def test_initialize_is_idempotent(self):
        e = get_engine()
        e.initialize()
        e.initialize()  # second call is a no-op

    def test_ensure_default_font_is_idempotent(self):
        e = get_engine()
        e.initialize()
        e.ensure_default_font()
        e.ensure_default_font()

    def test_unsupported_format_raises(self):
        e = get_engine()
        with pytest.raises(JsEngineError, match='Unsupported format'):
            e.export('webp', SIMPLE_DSL, None, 1.0)

    def test_invalid_dsl_raises(self):
        e = get_engine()
        with pytest.raises(JsEngineError):
            e.export('svg', 'garbage that does not parse', None, 1.0)

    def test_export_with_options_dict(self):
        e = get_engine()
        out = e.export(
            'svg', SIMPLE_DSL,
            {'direction': 'RIGHT', 'detailLevel': 'minimal'}, 1.0,
        )
        text = out.decode('utf-8')
        assert 'data-fcstm-direction="RIGHT"' in text


@pytest.mark.unittest
class TestEngineSelection:
    """
    Cover both :class:`MiniRacerEngine` and :class:`PyMiniRacerEngine`
    plus the fallback / unavailable paths in :func:`_build_engine`.
    """

    def test_modern_path(self, monkeypatch):
        captured = {}

        class _Fake(JsEngine):
            name = 'fake-modern'

            def __init__(self):
                super().__init__()
                captured['modern'] = True

            def _eval_raw(self, code):  # pragma: no cover - unused
                raise AssertionError

        monkeypatch.setattr(engine_module, 'MiniRacerEngine', _Fake)
        monkeypatch.setattr(sys, 'version_info', (3, 11, 0, 'final', 0))
        engine = engine_module._build_engine()
        assert engine.name == 'fake-modern'
        assert captured == {'modern': True}

    def test_modern_path_falls_back_to_legacy(self, monkeypatch):
        order = []

        class _ModernFails(JsEngine):
            name = 'modern-fails'

            def __init__(self):
                order.append('modern')
                raise ImportError('no mini-racer')

            def _eval_raw(self, code):  # pragma: no cover - unused
                raise AssertionError

        class _Legacy(JsEngine):
            name = 'fake-legacy'

            def __init__(self):
                super().__init__()
                order.append('legacy')

            def _eval_raw(self, code):  # pragma: no cover - unused
                raise AssertionError

        monkeypatch.setattr(engine_module, 'MiniRacerEngine', _ModernFails)
        monkeypatch.setattr(engine_module, 'PyMiniRacerEngine', _Legacy)
        monkeypatch.setattr(sys, 'version_info', (3, 11, 0, 'final', 0))
        engine = engine_module._build_engine()
        assert engine.name == 'fake-legacy'
        assert order == ['modern', 'legacy']

    def test_legacy_path_for_python37(self, monkeypatch):
        order = []

        class _Legacy(JsEngine):
            name = 'legacy37'

            def __init__(self):
                super().__init__()
                order.append('legacy')

            def _eval_raw(self, code):  # pragma: no cover - unused
                raise AssertionError

        class _ModernShouldNotConstruct(JsEngine):
            name = 'modern'

            def __init__(self):  # pragma: no cover - guarded by version check
                order.append('modern')
                raise AssertionError(
                    'modern engine must not be tried on Python 3.7'
                )

            def _eval_raw(self, code):  # pragma: no cover - unused
                raise AssertionError

        monkeypatch.setattr(
            engine_module, 'MiniRacerEngine', _ModernShouldNotConstruct,
        )
        monkeypatch.setattr(engine_module, 'PyMiniRacerEngine', _Legacy)
        monkeypatch.setattr(sys, 'version_info', (3, 7, 12, 'final', 0))
        engine = engine_module._build_engine()
        assert engine.name == 'legacy37'
        assert order == ['legacy']

    def test_no_engine_available(self, monkeypatch):
        class _Fail(JsEngine):
            def __init__(self):
                raise ImportError('not installed')

            def _eval_raw(self, code):  # pragma: no cover - unused
                raise AssertionError

        monkeypatch.setattr(engine_module, 'MiniRacerEngine', _Fail)
        monkeypatch.setattr(engine_module, 'PyMiniRacerEngine', _Fail)
        monkeypatch.setattr(sys, 'version_info', (3, 11, 0, 'final', 0))
        with pytest.raises(JsEngineUnavailableError):
            engine_module._build_engine()


@pytest.mark.unittest
class TestEngineErrorPaths:
    def test_initialize_propagates_wasm_error(self, monkeypatch):
        """
        Force ``__fcstm_wasm_status`` to report failure so the init
        guard raises with the captured error string.
        """
        e = get_engine()
        e.initialize()  # warm up so subsequent monkeypatch is the only failure
        # Now reset the singleton with a wrapper that pretends WASM failed.

        class _BrokenWasm(JsEngine):
            name = 'broken-wasm'

            def __init__(self):
                super().__init__()
                # Reuse the real engine's V8 context so SHIM/BUNDLE load.
                self._real = engine_module._build_engine()

            def _eval_raw(self, code):
                # Force the WASM status check to fail by lying on the
                # status read. Otherwise pass through.
                if code == '__fcstm_wasm_status':
                    return 'error'
                if code == '__fcstm_wasm_error':
                    return 'simulated WASM init failure'
                return self._real._eval_raw(code)

        broken = _BrokenWasm()
        with pytest.raises(JsEngineError, match='simulated WASM init failure'):
            broken.initialize()

    def test_export_returns_no_result_raises(self, monkeypatch):
        """
        If the JS bundle returns neither a result nor an error (e.g. if
        the microtask queue did not drain), the wrapper must surface a
        diagnostic instead of silently returning ``b''``.
        """
        real = get_engine()
        real.initialize()
        real.ensure_default_font()

        class _Stub(JsEngine):
            name = 'stub'

            def __init__(self):
                super().__init__()
                # Prevent initialize/ensure_default_font from doing real work.
                self._initialized = True
                self._font_loaded = True

            def _eval_raw(self, code):
                if code == '__fcstm_export_error':
                    return None
                if code == '__fcstm_export_result':
                    return None
                return None

        stub = _Stub()
        with pytest.raises(JsEngineError, match='no result'):
            stub.export('svg', SIMPLE_DSL, None, 1.0)


@pytest.mark.unittest
class TestPackageReexports:
    def test_top_level_exports(self):
        for name in (
            'BUNDLE_DIR', 'JsEngine', 'JsEngineError',
            'JsEngineUnavailableError', 'get_engine', 'reset_engine',
        ):
            assert hasattr(jsruntime, name), name


@pytest.mark.unittest
class TestPyMiniRacerAdapter:
    """
    Exercise :class:`PyMiniRacerEngine` directly by injecting a stub
    ``py_mini_racer.py_mini_racer`` module — the legacy 0.6.x wheel
    cannot coexist with the modern fork in the same env, so we cannot
    rely on having both installed.
    """

    def test_legacy_adapter_dispatches(self, monkeypatch):
        import types

        observed = []

        class _StubMiniRacer:
            def eval(self, code):  # noqa: A003 - mirror real API
                observed.append(code)
                return 'ok'

        fake_pkg = types.ModuleType('py_mini_racer')
        fake_inner = types.ModuleType('py_mini_racer.py_mini_racer')
        fake_inner.MiniRacer = _StubMiniRacer
        fake_pkg.py_mini_racer = fake_inner
        monkeypatch.setitem(sys.modules, 'py_mini_racer', fake_pkg)
        monkeypatch.setitem(
            sys.modules, 'py_mini_racer.py_mini_racer', fake_inner,
        )

        engine = engine_module.PyMiniRacerEngine()
        assert engine.name == 'py-mini-racer'
        result = engine._eval_raw('1 + 1')
        assert result == 'ok'
        assert observed == ['1 + 1']

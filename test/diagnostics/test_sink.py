"""
Unit tests for :class:`pyfcstm.diagnostics.DiagnosticSink`.

PR-2 of the Layer 1 structured-diagnostic refactor (see issue #103) routes
every semantic error in ``model.py`` through this sink. These tests pin
down the two-mode contract:

* **strict** (default) — each ``emit()`` of an error-severity diagnostic
  raises :class:`pyfcstm.utils.validate.ModelValidationError` immediately.
* **collect** — errors accumulate, the caller decides when to surface them.
"""

import pytest

from pyfcstm.diagnostics import DiagnosticSink
from pyfcstm.diagnostics.sink import _emit
from pyfcstm.utils import ModelDiagnostic, ModelValidationError


def _err(code: str = 'E_X', message: str = 'm') -> ModelDiagnostic:
    return ModelDiagnostic(code=code, severity='error', message=message)


def _warn(code: str = 'W_X', message: str = 'm') -> ModelDiagnostic:
    return ModelDiagnostic(code=code, severity='warning', message=message)


@pytest.mark.unittest
class TestDiagnosticSinkStrict:
    def test_default_is_strict(self):
        sink = DiagnosticSink()
        assert sink.collect is False

    def test_strict_emit_raises_immediately(self):
        sink = DiagnosticSink()
        with pytest.raises(ModelValidationError) as info:
            sink.emit(_err('E_UNDEFINED_VAR', 'oops'))
        assert info.value.diagnostics[0].code == 'E_UNDEFINED_VAR'

    def test_strict_emit_carries_previous_diagnostics(self):
        # If a sink had a warning queued before an error, the raise must
        # include the warning too (downstream tooling wants the full
        # picture, not just the line that aborted).
        sink = DiagnosticSink()
        sink.emit(_warn('W_DEADLOCK', 'd1'))
        with pytest.raises(ModelValidationError) as info:
            sink.emit(_err('E_X', 'oops'))
        codes = [d.code for d in info.value.diagnostics]
        assert codes == ['W_DEADLOCK', 'E_X']

    def test_strict_warning_does_not_raise(self):
        sink = DiagnosticSink()
        # Warnings are recorded but never abort the build.
        sink.emit(_warn('W_DEADLOCK', 'd'))
        assert not sink.has_errors()
        assert sink.diagnostics[0].code == 'W_DEADLOCK'


@pytest.mark.unittest
class TestDiagnosticSinkCollect:
    def test_collect_emit_does_not_raise(self):
        sink = DiagnosticSink(collect=True)
        sink.emit(_err('E_X', 'a'))
        sink.emit(_err('E_Y', 'b'))
        sink.emit(_warn('W_Z', 'c'))
        codes = [d.code for d in sink.diagnostics]
        assert codes == ['E_X', 'E_Y', 'W_Z']

    def test_collect_has_errors_reflects_severity(self):
        sink = DiagnosticSink(collect=True)
        sink.emit(_warn('W_Z', 'c'))
        assert not sink.has_errors()
        sink.emit(_err('E_X', 'a'))
        assert sink.has_errors()

    def test_finalize_or_raise_raises_on_errors(self):
        sink = DiagnosticSink(collect=True)
        sink.emit(_err('E_X', 'a'))
        sink.emit(_err('E_Y', 'b'))
        with pytest.raises(ModelValidationError) as info:
            sink.finalize_or_raise()
        assert len(info.value.diagnostics) == 2

    def test_finalize_or_raise_is_noop_without_errors(self):
        sink = DiagnosticSink(collect=True)
        sink.emit(_warn('W_Z', 'c'))
        # No error severity present — must NOT raise.
        sink.finalize_or_raise()
        # Warnings still recorded after no-op.
        assert sink.diagnostics[0].code == 'W_Z'

    def test_finalize_or_raise_is_noop_in_strict_mode(self):
        sink = DiagnosticSink(collect=False)
        # Strict mode would have raised at emit time; in this fixture we
        # never emit, so finalize is just a no-op for symmetry.
        sink.finalize_or_raise()


@pytest.mark.unittest
class TestDiagnosticsSnapshot:
    def test_diagnostics_property_returns_copy(self):
        sink = DiagnosticSink(collect=True)
        sink.emit(_err('E_X', 'a'))
        snap = sink.diagnostics
        snap.append(_err('E_FAKE', 'fake'))  # mutate snapshot
        # Original sink unchanged.
        assert len(sink.diagnostics) == 1
        assert sink.diagnostics[0].code == 'E_X'

    def test_collect_property(self):
        assert DiagnosticSink(collect=True).collect is True
        assert DiagnosticSink(collect=False).collect is False


@pytest.mark.unittest
class TestEmitHelper:
    """``_emit`` is a convenience wrapper that supports both sink-routed
    and direct-raise call sites without conditional plumbing."""

    def test_emit_with_none_sink_raises_immediately(self):
        with pytest.raises(ModelValidationError) as info:
            _emit(None, _err('E_X', 'oops'))
        assert info.value.diagnostics[0].code == 'E_X'

    def test_emit_with_strict_sink_raises(self):
        sink = DiagnosticSink()
        with pytest.raises(ModelValidationError):
            _emit(sink, _err('E_X', 'oops'))

    def test_emit_with_collect_sink_accumulates(self):
        sink = DiagnosticSink(collect=True)
        _emit(sink, _err('E_X', 'a'))
        _emit(sink, _err('E_Y', 'b'))
        assert [d.code for d in sink.diagnostics] == ['E_X', 'E_Y']

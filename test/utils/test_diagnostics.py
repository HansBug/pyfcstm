"""
Unit tests for :class:`pyfcstm.utils.validate.Span` and
:class:`pyfcstm.utils.validate.ModelDiagnostic`, plus the extended
:class:`pyfcstm.utils.validate.ModelValidationError` introduced in PR-1 of
the Layer 1 structured-diagnostic refactor (see issue #103).

These tests pin down the public contract of the new dataclasses and
verify the multi-inheritance backwards-compatibility trick that lets
PR-2 swap ``raise SyntaxError`` for ``raise ModelValidationError``
without breaking any caller that catches ``SyntaxError``.
"""

import pytest

from pyfcstm.utils import (
    IValidatable,
    ModelDiagnostic,
    ModelValidationError,
    Span,
    ValidationError,
)


@pytest.mark.unittest
class TestSpan:
    def test_basic_construction(self):
        span = Span(line=3, column=7)
        assert span.line == 3
        assert span.column == 7
        assert span.end_line is None
        assert span.end_column is None

    def test_construction_with_end_position(self):
        span = Span(line=3, column=7, end_line=3, end_column=20)
        assert span.end_line == 3
        assert span.end_column == 20

    def test_is_frozen(self):
        span = Span(line=1, column=1)
        with pytest.raises(Exception):
            span.line = 2  # noqa

    def test_equality(self):
        assert Span(line=1, column=1) == Span(line=1, column=1)
        assert Span(line=1, column=1) != Span(line=1, column=2)


@pytest.mark.unittest
class TestModelDiagnostic:
    def test_minimal_construction(self):
        diag = ModelDiagnostic(
            code='E_UNDEFINED_VAR',
            severity='error',
            message="Unknown variable 'x'",
        )
        assert diag.code == 'E_UNDEFINED_VAR'
        assert diag.severity == 'error'
        assert diag.span is None
        assert diag.refs == {}
        assert diag.is_error()

    def test_full_construction_with_refs_and_span(self):
        span = Span(line=5, column=21)
        diag = ModelDiagnostic(
            code='E_UNDEFINED_VAR',
            severity='error',
            message="Unknown guard variable",
            span=span,
            refs={'var_name': 'unknown_var', 'referenced_in': 'guard'},
        )
        assert diag.span is span
        assert diag.refs['var_name'] == 'unknown_var'
        assert diag.refs['referenced_in'] == 'guard'

    def test_warning_severity_is_not_error(self):
        diag = ModelDiagnostic(
            code='W_DEADLOCK_LEAF',
            severity='warning',
            message="Deadlock leaf",
        )
        assert not diag.is_error()

    def test_refs_default_is_independent_per_instance(self):
        """Guard against the classic dataclass-mutable-default trap."""
        a = ModelDiagnostic(code='E_X', severity='error', message='m')
        b = ModelDiagnostic(code='E_Y', severity='error', message='m')
        a.refs['k'] = 1
        assert 'k' not in b.refs

    def test_rejects_invalid_severity_capitalized(self):
        with pytest.raises(ValueError, match='severity'):
            ModelDiagnostic(code='E_X', severity='Error', message='m')

    def test_rejects_invalid_severity_uppercase(self):
        with pytest.raises(ValueError, match='severity'):
            ModelDiagnostic(code='E_X', severity='ERROR', message='m')

    def test_rejects_invalid_severity_typo(self):
        with pytest.raises(ValueError, match='severity'):
            ModelDiagnostic(code='E_X', severity='err', message='m')

    def test_is_frozen_top_level_fields(self):
        """``frozen=True`` covers code / severity / message / span; ``refs``
        is intentionally mutable (PR-2 emit needs to populate it)."""
        diag = ModelDiagnostic(code='E_X', severity='error', message='m')
        with pytest.raises(Exception):
            diag.code = 'E_Y'  # noqa
        with pytest.raises(Exception):
            diag.severity = 'warning'  # noqa
        with pytest.raises(Exception):
            diag.message = 'other'  # noqa
        # refs remains mutable by design
        diag.refs['k'] = 1
        assert diag.refs['k'] == 1

    def test_format_line(self):
        diag = ModelDiagnostic(code='E_X', severity='error', message='oops')
        assert diag.format_line() == '[error/E_X] oops'


@pytest.mark.unittest
class TestModelValidationError:
    def test_inherits_from_syntax_error(self):
        """
        Backwards-compatibility trick: PR-2 will replace
        ``raise SyntaxError(...)`` in model.py with
        ``raise ModelValidationError(...)``. All ``except SyntaxError:``
        callers must continue to work.
        """
        err = ModelValidationError([ValidationError('A')])
        assert isinstance(err, SyntaxError)
        assert isinstance(err, Exception)

    def test_legacy_errors_only_construction(self):
        err = ModelValidationError([ValidationError('A'), ValidationError('B')])
        assert len(err.errors) == 2
        assert err.diagnostics == []
        assert '2 errors' in str(err)

    def test_diagnostics_only_construction(self):
        diag = ModelDiagnostic(
            code='E_UNDEFINED_VAR',
            severity='error',
            message='unknown var',
        )
        err = ModelValidationError(diagnostics=[diag])
        assert err.errors == []
        assert len(err.diagnostics) == 1
        assert err.diagnostics[0] is diag
        assert 'E_UNDEFINED_VAR' in str(err)

    def test_mixed_errors_and_diagnostics(self):
        diag = ModelDiagnostic(code='E_X', severity='error', message='mx')
        err = ModelValidationError(
            errors=[ValidationError('A')],
            diagnostics=[diag],
        )
        assert len(err.errors) == 1
        assert len(err.diagnostics) == 1

    def test_caught_via_syntax_error_handler(self):
        """The whole point of the multi-inheritance trick."""
        try:
            raise ModelValidationError(
                diagnostics=[ModelDiagnostic(code='E_X', severity='error', message='m')]
            )
        except SyntaxError as e:
            assert isinstance(e, ModelValidationError)
            assert e.diagnostics[0].code == 'E_X'
        else:
            pytest.fail("ModelValidationError should be catchable as SyntaxError")

    def test_default_construction_is_empty(self):
        err = ModelValidationError()
        assert err.errors == []
        assert err.diagnostics == []
        assert str(err)  # non-empty fallback message

    def test_custom_message_overrides_summary(self):
        err = ModelValidationError(
            diagnostics=[ModelDiagnostic(code='E_X', severity='error', message='m')],
            message="custom top-level message",
        )
        assert 'custom top-level message' in str(err)

    def test_ivalidatable_still_raises_model_validation_error(self):
        """The IValidatable mixin must continue to work after the refactor."""

        class _BadModel(IValidatable):
            def _v(self) -> None:
                raise ValidationError("bad")

            __validators__ = [_v]

        with pytest.raises(ModelValidationError) as info:
            _BadModel().validate()
        assert len(info.value.errors) == 1

    def test_span_propagates_to_syntax_error_lineno(self):
        """
        I2 from PR-107 review: when at least one diagnostic carries a Span,
        the SyntaxError 4-tuple (filename, lineno, offset, text) must be
        populated so downstream ``except SyntaxError as e: e.lineno`` keeps
        working after PR-2 swaps the raise type.
        """
        diag = ModelDiagnostic(
            code='E_X',
            severity='error',
            message='m',
            span=Span(line=7, column=3),
        )
        err = ModelValidationError(diagnostics=[diag])
        assert err.lineno == 7
        assert err.offset == 3
        assert err.filename is None
        assert err.text is None

    def test_no_span_means_lineno_none(self):
        diag = ModelDiagnostic(code='E_X', severity='error', message='m')
        err = ModelValidationError(diagnostics=[diag])
        assert err.lineno is None
        assert err.offset is None

    def test_first_span_wins_when_multiple_diagnostics(self):
        diags = [
            ModelDiagnostic(code='E_X', severity='error', message='m1'),  # no span
            ModelDiagnostic(
                code='E_Y', severity='error', message='m2',
                span=Span(line=10, column=5),
            ),
            ModelDiagnostic(
                code='E_Z', severity='error', message='m3',
                span=Span(line=20, column=8),
            ),
        ]
        err = ModelValidationError(diagnostics=diags)
        # First diagnostic with a span wins, not first diagnostic outright.
        assert err.lineno == 10
        assert err.offset == 5

    def test_summary_unifies_error_and_diagnostic_format(self):
        """
        M2 from PR-107 review: legacy ValidationError entries and structured
        ModelDiagnostic entries now share the ``[severity/code] message``
        prefix format.
        """
        diag = ModelDiagnostic(code='E_X', severity='error', message='dx')
        err = ModelValidationError(
            errors=[ValidationError('legacy_err')],
            diagnostics=[diag],
        )
        s = str(err)
        # legacy error path also uses the unified [severity/code] prefix
        assert '[error/VALIDATION]' in s
        assert 'legacy_err' in s
        # diagnostic path uses ``format_line()``
        assert '[error/E_X] dx' in s

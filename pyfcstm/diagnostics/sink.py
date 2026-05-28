"""
Runtime sink for emitting :class:`pyfcstm.utils.validate.ModelDiagnostic`.

The sink lets a single pass of model construction (or, later, design-health
inspection) operate in two modes through one code path:

* **strict** (the default) — each ``emit()`` raises a
  :class:`pyfcstm.utils.validate.ModelValidationError` immediately, carrying
  the diagnostic just produced plus any earlier ones. This preserves the
  pre-PR-2 behavior where the very first semantic error aborts the build.

* **collect** — ``emit()`` appends to an internal list and returns; the
  caller is expected to call :meth:`finalize` (or read :attr:`diagnostics`
  directly) at the end of the pass to inspect / surface every diagnostic
  found, even though the resulting model may be partial.

Downstream consumers (LLM agent loops, IDE integrations, the future
``jsfcstm`` visualization layer) dispatch on
:attr:`ModelDiagnostic.code`. The sink is purely a runtime helper — the
contract surface is the diagnostic objects themselves, not this class.
"""

from typing import List, Optional

from ..utils.validate import ModelDiagnostic, ModelValidationError


class DiagnosticSink:
    """
    Collects :class:`ModelDiagnostic` objects emitted during a pass.

    :param collect: When ``False`` (the default), every ``emit()`` call
        raises :class:`ModelValidationError` immediately, carrying the
        accumulated diagnostics. When ``True``, errors are accumulated and
        the caller decides when to surface them.
    :type collect: bool

    Example::

        >>> from pyfcstm.diagnostics.sink import DiagnosticSink
        >>> from pyfcstm.utils import ModelDiagnostic
        >>> sink = DiagnosticSink(collect=True)
        >>> sink.emit(ModelDiagnostic(code='E_X', severity='error', message='x'))
        >>> sink.emit(ModelDiagnostic(code='E_Y', severity='error', message='y'))
        >>> [d.code for d in sink.diagnostics]
        ['E_X', 'E_Y']
        >>> sink.has_errors()
        True
    """

    def __init__(self, collect: bool = False) -> None:
        self._collect = bool(collect)
        self._diagnostics: List[ModelDiagnostic] = []

    @property
    def collect(self) -> bool:
        """
        :return: ``True`` if the sink accumulates diagnostics, ``False`` if
            it raises immediately.
        :rtype: bool
        """
        return self._collect

    @property
    def diagnostics(self) -> List[ModelDiagnostic]:
        """
        :return: A snapshot copy of the diagnostics accumulated so far.
        :rtype: List[ModelDiagnostic]
        """
        return list(self._diagnostics)

    def has_errors(self) -> bool:
        """
        :return: ``True`` if at least one accumulated diagnostic has
            ``severity == 'error'``.
        :rtype: bool
        """
        return any(d.is_error() for d in self._diagnostics)

    def emit(self, diagnostic: ModelDiagnostic) -> None:
        """
        Record a diagnostic. In strict mode, raise immediately.

        :param diagnostic: The structured diagnostic to record.
        :type diagnostic: pyfcstm.utils.validate.ModelDiagnostic
        :raises pyfcstm.utils.validate.ModelValidationError: When the sink
            is in strict mode (the default) and the diagnostic has error
            severity.
        """
        self._diagnostics.append(diagnostic)
        if not self._collect and diagnostic.is_error():
            raise ModelValidationError(diagnostics=list(self._diagnostics))

    def finalize_or_raise(self) -> None:
        """
        In collect mode, raise a single :class:`ModelValidationError`
        carrying all accumulated error diagnostics if any are present.
        In strict mode this is a no-op (errors already raised at emit time).

        :raises pyfcstm.utils.validate.ModelValidationError: When collect
            mode accumulated at least one error-severity diagnostic.
        """
        if self._collect and self.has_errors():
            raise ModelValidationError(diagnostics=list(self._diagnostics))


def _emit(
        sink: Optional[DiagnosticSink],
        diagnostic: ModelDiagnostic,
        prior_diagnostics: Optional[List[ModelDiagnostic]] = None,
) -> None:
    """
    Convenience helper: route ``diagnostic`` through ``sink`` if one is
    provided; otherwise raise immediately as :class:`ModelValidationError`.

    Used by code paths that want to support both "callers pass a sink" and
    "callers expect classic raise behavior" without conditional plumbing at
    every call site.

    When ``sink`` is ``None`` and ``prior_diagnostics`` is provided, the
    raised :class:`ModelValidationError` carries those prior entries before
    the new ``diagnostic`` — matching the strict-mode
    :meth:`DiagnosticSink.emit` semantics where accumulated context (e.g.
    earlier warnings) is preserved into the raise.

    :param sink: Active sink, or ``None`` to raise immediately.
    :type sink: pyfcstm.diagnostics.sink.DiagnosticSink, optional
    :param diagnostic: The structured diagnostic to route.
    :type diagnostic: pyfcstm.utils.validate.ModelDiagnostic
    :param prior_diagnostics: Optional list of diagnostics already
        accumulated by the caller; included in the raise on the
        ``sink is None`` path. Defaults to ``None``.
    :type prior_diagnostics: List[ModelDiagnostic], optional
    :raises pyfcstm.utils.validate.ModelValidationError: When ``sink`` is
        ``None`` or when the sink is in strict mode.
    """
    if sink is None:
        all_diagnostics: List[ModelDiagnostic] = (
            list(prior_diagnostics) if prior_diagnostics else []
        )
        all_diagnostics.append(diagnostic)
        raise ModelValidationError(diagnostics=all_diagnostics)
    sink.emit(diagnostic)

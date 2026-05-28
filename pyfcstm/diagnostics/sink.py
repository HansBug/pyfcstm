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

from typing import List, Optional, Type

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
        *,
        exc_cls: Type[ModelValidationError] = ModelValidationError,
        prior_diagnostics: Optional[List[ModelDiagnostic]] = None,
) -> None:
    """
    Convenience helper: route ``diagnostic`` through ``sink`` if one is
    provided in collect mode; otherwise raise the typed ``exc_cls``.

    Used by code paths that want to support all three sink dispositions
    without writing the ``if sink is None: raise; elif sink.collect: emit;
    else: raise typed`` ladder at every call site:

    * ``sink=None`` (no sink) — raise ``exc_cls`` carrying ``[diagnostic]``
      plus any optional ``prior_diagnostics`` already accumulated by the
      caller.
    * ``sink`` provided AND ``sink.collect=True`` — append the diagnostic
      to the sink and return; the caller is responsible for surfacing the
      collected list later.
    * ``sink`` provided AND ``sink.collect=False`` (strict) — also raise
      ``exc_cls``, but include the sink's previously accumulated entries
      (e.g. earlier warnings) in the raise. The diagnostic is also
      appended to the sink so post-raise inspection sees a consistent
      history.

    The strict-sink path is what makes ``ModelValueError`` /
    ``ModelLookupError`` reachable when a caller layers a sink onto an
    existing API that historically raised ``ValueError`` / ``LookupError``.
    Without ``exc_cls``, strict-sink mode would silently downgrade those
    raises to plain :class:`ModelValidationError`, breaking
    ``except ValueError:`` / ``except LookupError:`` catch handlers.

    :param sink: Active sink, or ``None`` to raise immediately.
    :type sink: pyfcstm.diagnostics.sink.DiagnosticSink, optional
    :param diagnostic: The structured diagnostic to route.
    :type diagnostic: pyfcstm.utils.validate.ModelDiagnostic
    :param exc_cls: Exception class to raise when ``sink`` is ``None`` or
        strict. Must inherit :class:`ModelValidationError`; defaults to
        :class:`ModelValidationError` itself. Callers that want
        ``except ValueError:`` / ``except LookupError:`` catch
        compatibility should pass :class:`ModelValueError` or
        :class:`ModelLookupError`.
    :type exc_cls: Type[ModelValidationError], optional
    :param prior_diagnostics: Optional list of diagnostics already
        accumulated by the caller; prepended to the raise's diagnostics
        list. Defaults to ``None``.
    :type prior_diagnostics: List[ModelDiagnostic], optional
    :raises pyfcstm.utils.validate.ModelValidationError: Of type
        ``exc_cls``. Only raised when ``sink`` is ``None`` or
        ``sink.collect`` is ``False``.

    Example::

        >>> from pyfcstm.diagnostics import DiagnosticSink
        >>> from pyfcstm.diagnostics.sink import _emit
        >>> from pyfcstm.utils import ModelDiagnostic
        >>> from pyfcstm.utils.validate import ModelValueError
        >>> sink = DiagnosticSink(collect=True)
        >>> _emit(sink, ModelDiagnostic(
        ...     code='E_EVENT_REF_INVALID', severity='error', message='m',
        ... ), exc_cls=ModelValueError)
        >>> [d.code for d in sink.diagnostics]
        ['E_EVENT_REF_INVALID']
    """
    accumulated: List[ModelDiagnostic] = (
        list(prior_diagnostics) if prior_diagnostics else []
    )

    if sink is None:
        accumulated.append(diagnostic)
        raise exc_cls(diagnostics=accumulated)

    if sink.collect:
        sink.emit(diagnostic)
        return

    # Strict sink (collect=False): emit raises ``ModelValidationError``
    # internally with all prior sink entries + the new one. We catch and
    # translate to ``exc_cls`` so legacy ``except ValueError:`` /
    # ``except LookupError:`` handlers stay alive.
    try:
        sink.emit(diagnostic)
    except ModelValidationError as err:
        raise exc_cls(
            diagnostics=accumulated + list(err.diagnostics),
        ) from err

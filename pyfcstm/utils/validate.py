"""
Validation framework utilities for model validation workflows.

This module provides a lightweight validation framework for Python models. It
defines base exceptions for validation failures and a mixin-style interface
(:class:`IValidatable`) that allows classes to register validation rules and
perform aggregated validation.

The module contains the following main components:

* :class:`ValidationError` - Exception for a single validation rule failure
* :class:`ModelValidationError` - Aggregated exception for multiple failures
* :class:`IValidatable` - Mixin interface for defining and running validators

Example::

    >>> from pyfcstm.utils.validate import IValidatable, ValidationError
    >>>
    >>> class MyModel(IValidatable):
    ...     def __init__(self, value: int):
    ...         self.value = value
    ...
    ...     def _validate_positive(self) -> None:
    ...         if self.value <= 0:
    ...             raise ValidationError("Value must be positive.")
    ...
    ...     __validators__ = [_validate_positive]
    ...
    >>> model = MyModel(1)
    >>> model.validate()
    >>> bad_model = MyModel(0)
    >>> try:
    ...     bad_model.validate()
    ... except Exception as err:
    ...     print(type(err).__name__)
    ModelValidationError
"""

import os
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional

try:
    from typing import Literal
except ImportError:  # pragma: no cover
    # Python < 3.8 fallback. The CI matrix on Python >= 3.8 never
    # executes this branch.
    from typing_extensions import Literal

from hbutils.string import plural_word


@dataclass(frozen=True)
class Span:
    """
    Source-code location used as the anchor for a :class:`ModelDiagnostic`.

    All coordinates are 1-based. ``end_line`` / ``end_column`` are optional;
    when omitted the span is treated as pointing at a single source position.

    :param line: 1-based source line where the diagnostic anchor begins.
    :type line: int
    :param column: 1-based source column where the diagnostic anchor begins.
    :type column: int
    :param end_line: 1-based source line where the diagnostic anchor ends,
        defaults to ``None``.
    :type end_line: int, optional
    :param end_column: 1-based source column where the diagnostic anchor ends,
        defaults to ``None``.
    :type end_column: int, optional

    Example::

        >>> from pyfcstm.utils.validate import Span
        >>> span = Span(line=3, column=12)
        >>> span.line, span.column
        (3, 12)
        >>> Span(line=3, column=12, end_line=3, end_column=20).end_column
        20
    """

    line: int
    column: int
    end_line: Optional[int] = None
    end_column: Optional[int] = None


_ALLOWED_SEVERITIES = ('error', 'warning', 'info')


@dataclass(frozen=True)
class ModelDiagnostic:
    """
    Structured semantic or design-health diagnostic produced by the model layer.

    Designed as the **stable contract** between :mod:`pyfcstm.model` and
    downstream consumers such as IDE integrations, LLM agent loops, and
    evaluation scripts. Consumers should dispatch on :attr:`code` only and
    treat :attr:`message` as human-facing text that may change between
    releases.

    The full set of valid :attr:`code` values together with their
    :attr:`refs` payload schema lives in
    :mod:`pyfcstm.diagnostics.codes` (loaded from ``pyfcstm/diagnostics/codes.yaml``);
    this dataclass intentionally does not validate ``code`` at construction
    time so that experimental codes can be emitted in tests.

    :attr:`severity` is enforced at construction time to be one of
    ``'error'`` / ``'warning'`` / ``'info'`` — a typo such as ``'Error'``
    would otherwise cause :meth:`is_error` to silently return ``False`` and
    skew downstream dispatch.

    The dataclass is frozen so the public contract surface (``code`` /
    ``severity`` / ``message`` / ``span``) cannot be mutated after
    construction. ``refs`` remains a mutable ``dict`` because PR-2 needs to
    populate it during emit — downstream consumers should treat it as
    read-only.

    :param code: Stable diagnostic code, e.g. ``'E_UNDEFINED_VAR'``,
        ``'W_DEADLOCK_LEAF'``. Always treated as the public contract.
    :type code: str
    :param severity: Either ``'error'``, ``'warning'``, or ``'info'``.
    :type severity: str
    :param message: Human-readable rendering of the diagnostic. **Not** part
        of the contract — downstream tools must not regex-match against it.
    :type message: str
    :param span: Optional source position, defaults to ``None``.
    :type span: pyfcstm.utils.validate.Span, optional
    :param refs: Structured payload keyed by field names defined in
        ``codes.yaml`` for this code. Defaults to an empty dict.
    :type refs: Dict[str, Any]

    Example::

        >>> from pyfcstm.utils.validate import ModelDiagnostic, Span
        >>> diag = ModelDiagnostic(
        ...     code='E_UNDEFINED_VAR',
        ...     severity='error',
        ...     message="Unknown guard variable 'unknown_var' in transition",
        ...     span=Span(line=5, column=21),
        ...     refs={'var_name': 'unknown_var', 'referenced_in': 'guard'},
        ... )
        >>> diag.code
        'E_UNDEFINED_VAR'
        >>> diag.is_error()
        True
        >>> diag.refs['var_name']
        'unknown_var'
    """

    code: str
    severity: Literal['error', 'warning', 'info']
    message: str
    span: Optional[Span] = None
    refs: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self) -> None:
        if self.severity not in _ALLOWED_SEVERITIES:
            raise ValueError(
                "ModelDiagnostic.severity must be one of "
                f"{_ALLOWED_SEVERITIES!r}, got {self.severity!r}"
            )

    def is_error(self) -> bool:
        """
        Return ``True`` if this diagnostic has error severity.

        :return: ``True`` for ``severity == 'error'``, ``False`` otherwise.
        :rtype: bool
        """
        return self.severity == 'error'

    def format_line(self) -> str:
        """
        Render this diagnostic as a single human-readable summary line.

        Used by :meth:`ModelValidationError._build_summary_message` so that
        both legacy :class:`ValidationError` entries and structured
        :class:`ModelDiagnostic` entries share the same ``[code] message``
        prefix style in aggregated error output.

        :return: A one-line ``[severity/code] message`` representation.
        :rtype: str
        """
        return f"[{self.severity}/{self.code}] {self.message}"


class ValidationError(Exception):
    """
    Base exception class for validation errors.

    This exception should be raised when a single validation rule fails. It is
    designed to be caught and collected by :class:`IValidatable`.

    Example::

        >>> raise ValidationError("Invalid value.")
        Traceback (most recent call last):
            ...
        ValidationError: Invalid value.
    """
    pass


class ModelValidationError(SyntaxError):
    """
    Exception class for aggregating multiple validation errors.

    This exception contains a list of :class:`ValidationError` instances and
    formats them into a readable error message.

    It multi-inherits from :class:`SyntaxError` for backwards compatibility:
    callers that previously caught ``SyntaxError`` raised from
    :mod:`pyfcstm.model` continue to work after later PRs in the Layer 1
    refactor switch raise sites to this class.

    In addition to the legacy :attr:`errors` list, instances may also carry
    a :attr:`diagnostics` list of structured :class:`ModelDiagnostic`
    objects when raised from the new collect-mode pipeline. Existing
    callers that do not read :attr:`diagnostics` continue to work as before.

    :param errors: List of validation errors that occurred, defaults to ``None``.
    :type errors: List[ValidationError], optional
    :param diagnostics: List of structured diagnostics, defaults to ``None``.
    :type diagnostics: List[ModelDiagnostic], optional
    :param message: Pre-formatted summary message, defaults to ``None``.
        When omitted, a summary is built from :attr:`errors` /
        :attr:`diagnostics`.
    :type message: str, optional

    :ivar errors: Stored validation errors.
    :vartype errors: List[ValidationError]
    :ivar diagnostics: Stored structured diagnostics.
    :vartype diagnostics: List[ModelDiagnostic]

    Example::

        >>> err = ModelValidationError([ValidationError("A"), ValidationError("B")])
        >>> "2 errors" in str(err)
        True
        >>> isinstance(err, SyntaxError)
        True
        >>> err.diagnostics
        []
    """

    def __init__(
            self,
            errors: Optional[List[ValidationError]] = None,
            diagnostics: Optional[List[ModelDiagnostic]] = None,
            message: Optional[str] = None,
    ) -> None:
        self.errors: List[ValidationError] = list(errors) if errors else []
        self.diagnostics: List[ModelDiagnostic] = list(diagnostics) if diagnostics else []
        if message is None:
            message = self._build_summary_message()

        # SyntaxError carries a (filename, lineno, offset, text) 4-tuple
        # behind e.filename / e.lineno / e.offset / e.text. Without this
        # tuple, downstream code that catches us via the SyntaxError MRO
        # back-compat hatch sees lineno=None / offset=None, regressing
        # the source-position signal that callers may already depend on.
        # Map the first diagnostic that carries a Span onto this 4-tuple.
        span = next(
            (d.span for d in self.diagnostics if d.span is not None),
            None,
        )
        if span is not None:
            super().__init__(message, (None, span.line, span.column, None))
        else:
            super().__init__(message)

    def _build_summary_message(self) -> str:
        # Single-entry path: emit the underlying message verbatim so that
        # downstream consumers (and existing tests) that match the raw
        # ``SyntaxError`` message text continue to work after PR-2's
        # ``raise SyntaxError(...)`` -> ``raise ModelValidationError(...)``
        # migration. The "Model diagnostics, N items in total:" wrapper
        # only adds value when there is more than one entry to enumerate.
        #
        # Threshold semantics (M2 from PR-110 review): the fast path only
        # fires when one of ``errors`` / ``diagnostics`` is empty and the
        # other has exactly one entry. The mixed 1+1 case still routes to
        # the enumerated multi-item format on purpose — that case carries
        # two semantically distinct entries (one legacy validation error
        # plus one structured diagnostic) that deserve enumeration. PR-3
        # may revisit this if a new aggregated raise type emerges.
        single_error = len(self.errors) == 1 and not self.diagnostics
        single_diag = len(self.diagnostics) == 1 and not self.errors
        if single_error:
            return str(self.errors[0])
        if single_diag:
            return self.diagnostics[0].message

        parts: List[str] = []
        if self.errors:
            error_lines = [
                f"{i}. [error/VALIDATION] {e}"
                for i, e in enumerate(self.errors, start=1)
            ]
            parts.append(
                f"Model validation error, {plural_word(len(self.errors), 'error')} in total:"
                f"{os.linesep}"
                f"{os.linesep.join(error_lines)}"
            )
        if self.diagnostics:
            diag_lines = [
                f"{i}. {d.format_line()}"
                for i, d in enumerate(self.diagnostics, start=1)
            ]
            parts.append(
                f"Model diagnostics, {plural_word(len(self.diagnostics), 'item')} in total:"
                f"{os.linesep}"
                f"{os.linesep.join(diag_lines)}"
            )
        if not parts:
            return "Model validation error."
        return os.linesep.join(parts)


class ModelValueError(ModelValidationError, ValueError):
    """
    Raised by model lookup APIs when an input string is syntactically
    invalid as a value (empty, bad format, dotted path that exceeds the
    root state, ...).

    Multi-inherits from :class:`ModelValidationError` (which itself
    multi-inherits :class:`SyntaxError`) and from :class:`ValueError`, so:

    * ``except ValueError:`` continues to catch this — preserving the
      pre-PR-3 behavior at every call site that already handles
      ``ValueError`` raised from ``State.resolve_event`` /
      ``StateMachine.resolve_event``.
    * ``except SyntaxError:`` continues to catch too (inherited via
      :class:`ModelValidationError`), keeping the PR-2 multi-inheritance
      contract consistent.
    * The new ``except ModelValueError:`` (or ``ModelValidationError``)
      lets diagnostic-aware consumers dispatch on the typed class.

    All structured diagnostics emitted via this exception carry
    ``code='E_EVENT_REF_INVALID'`` per the contract in
    ``pyfcstm/diagnostics/codes.yaml``.

    Example::

        >>> from pyfcstm.utils.validate import ModelValueError
        >>> try:
        ...     raise ModelValueError(message="invalid ref")
        ... except ValueError as e:
        ...     isinstance(e, ModelValueError)
        True
    """


class ModelLookupError(ModelValidationError, LookupError):
    """
    Raised by model lookup APIs when a state path or event name cannot be
    found in the live state hierarchy.

    Multi-inherits :class:`ModelValidationError` and :class:`LookupError`,
    so:

    * ``except LookupError:`` continues to catch this — preserving the
      pre-PR-3 behavior at every call site that already handles
      ``LookupError`` raised from ``State.resolve_event`` /
      ``StateMachine.resolve_event``.
    * ``except SyntaxError:`` and ``except ModelValidationError:`` both
      catch as well (inherited path).

    Structured diagnostics emitted via this exception carry
    ``code='E_EVENT_NOT_FOUND'`` per the contract in
    ``pyfcstm/diagnostics/codes.yaml``.

    Example::

        >>> from pyfcstm.utils.validate import ModelLookupError
        >>> try:
        ...     raise ModelLookupError(message="state not found")
        ... except LookupError as e:
        ...     isinstance(e, ModelLookupError)
        True
    """


class IValidatable:
    """
    Interface class for implementing validatable objects.

    Classes inheriting from :class:`IValidatable` should define their validation
    rules in the :attr:`__validators__` class variable as a list of validator
    methods. Each validator should accept the instance as the sole parameter
    and raise :class:`ValidationError` if the rule fails.

    :cvar __validators__: List of validator functions to be applied
    :type __validators__: List[Callable[["IValidatable"], None]]

    Example::

        >>> class MyModel(IValidatable):
        ...     def _validate_non_empty(self) -> None:
        ...         if not getattr(self, "value", None):
        ...             raise ValidationError("Value is empty.")
        ...
        ...     __validators__ = [_validate_non_empty]
        ...
        >>> model = MyModel()
        >>> try:
        ...     model.validate()
        ... except ModelValidationError as err:
        ...     isinstance(err.errors[0], ValidationError)
        True
    """

    __validators__: List[Callable[["IValidatable"], None]] = []

    def _validate_for_errors(self) -> List[ValidationError]:
        """
        Execute all validators and collect validation errors.

        Each validator registered in :attr:`__validators__` is called with the
        current instance. Any :class:`ValidationError` raised is collected.

        :return: List of validation errors that occurred
        :rtype: List[ValidationError]
        """
        errors: List[ValidationError] = []
        for validator in self.__validators__:
            try:
                validator(self)
            except ValidationError as err:
                errors.append(err)
        return errors

    def validate(self) -> None:
        """
        Validate the object using all registered validators.

        :raises ModelValidationError: If any validation errors occur

        Example::

            >>> class MyModel(IValidatable):
            ...     def _validate(self) -> None:
            ...         raise ValidationError("Always invalid.")
            ...
            ...     __validators__ = [_validate]
            ...
            >>> try:
            ...     MyModel().validate()
            ... except ModelValidationError as err:
            ...     len(err.errors)
            1
        """
        errors = self._validate_for_errors()
        if errors:
            raise ModelValidationError(errors)

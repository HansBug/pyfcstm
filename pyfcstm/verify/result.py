"""Raw verification result helpers.

This module defines the small result objects returned by raw verification
algorithms.  The payload deliberately stays below the diagnostics layer:
algorithms return kind strings and plain dictionaries, while later integration
can decide how those payloads become user-facing diagnostics.

Example::

    >>> from pyfcstm.verify.result import make_diag, skip_result
    >>> make_diag("W_DEAD_GUARD", "dead_guard", state="Root.A")["data"]
    {'state': 'Root.A'}
    >>> skip_result("unknown", "solver returned unknown").kind
    'unknown'
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Tuple

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal


ResultKind = Literal[
    "sat",
    "unsat",
    "unknown",
    "timeout",
    "undecidable_skip",
]


@dataclass(frozen=True)
class AlgorithmResult:
    """Result returned by one raw verification algorithm.

    :param kind: Normalized solver or skip outcome.
    :type kind: ResultKind
    :param diagnostics: Raw diagnostic dictionaries produced by the algorithm.
        These stay diagnostics-layer independent.
    :type diagnostics: Tuple[dict, ...]
    :param reason: Optional reason for ``unknown`` / ``timeout`` / skip results,
        defaults to ``None``.
    :type reason: Optional[str], optional

    Example::

        >>> result = AlgorithmResult("sat", diagnostics=({"code": "W", "data": {}},))
        >>> result.kind
        'sat'
        >>> len(result.diagnostics)
        1
    """

    kind: ResultKind
    diagnostics: Tuple[dict, ...] = ()
    reason: Optional[str] = None


def make_diag(code: str, algorithm_name: str, **data) -> dict:
    """Create a raw verify diagnostic payload.

    :param code: Future diagnostics code.
    :type code: str
    :param algorithm_name: Algorithm that emitted the payload.
    :type algorithm_name: str
    :param data: Algorithm-specific payload fields.
    :type data: object
    :return: Raw diagnostic dictionary.
    :rtype: dict

    Example::

        >>> make_diag("W_DEAD_GUARD", "dead_guard", state="Root.A")
        {'code': 'W_DEAD_GUARD', 'algorithm_name': 'dead_guard', 'data': {'state': 'Root.A'}}
    """
    return {
        "code": code,
        "algorithm_name": algorithm_name,
        "data": data,
    }


def skip_result(kind: ResultKind, reason: Optional[str]) -> AlgorithmResult:
    """Create a skip or indeterminate result.

    :param kind: Result kind.
    :type kind: ResultKind
    :param reason: Optional reason text.
    :type reason: Optional[str]
    :return: Algorithm result.
    :rtype: AlgorithmResult

    Example::

        >>> skip_result("undecidable_skip", "unsupported expression")
        AlgorithmResult(kind='undecidable_skip', diagnostics=(), reason='unsupported expression')
    """
    return AlgorithmResult(kind=kind, diagnostics=(), reason=reason)


_make_diag = make_diag
_skip_result = skip_result


__all__ = [
    "AlgorithmResult",
    "ResultKind",
    "make_diag",
    "skip_result",
]

"""Raw verification result helpers."""

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
    :return: Raw diagnostic dictionary.
    :rtype: dict
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

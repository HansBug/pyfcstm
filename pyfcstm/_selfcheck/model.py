"""Immutable self-check results and a single-writer append-only ledger."""

import threading
import time
from dataclasses import dataclass, field
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


TERMINAL_STATUSES = (
    "PASS",
    "WARN",
    "SKIP",
    "BLOCKED",
    "FAIL",
    "ERROR",
    "TIMEOUT",
    "CRASH",
)


@dataclass(frozen=True)
class CheckSpec:
    """
    Describe one statically registered self-check.

    :param check_id: Stable result identifier.
    :type check_id: str
    :param worker_key: Static registry key used by the hidden worker.
    :type worker_key: str
    :param required: Whether a non-PASS status affects the public exit code.
    :type required: bool
    :param prerequisites: Check IDs that must complete first, defaults to ``()``.
    :type prerequisites: Tuple[str, ...], optional

    Example::

        >>> CheckSpec("artifact.self_dispatch", "self_dispatch").required
        True
    """

    check_id: str
    worker_key: str
    required: bool = True
    prerequisites: Tuple[str, ...] = ()


@dataclass(frozen=True)
class CheckResult:
    """
    Represent one terminal check result.

    :param check_id: Stable check identifier.
    :type check_id: str
    :param status: One value from :data:`TERMINAL_STATUSES`.
    :type status: str
    :param required: Whether this result is required for exit status.
    :type required: bool
    :param summary: Concise human-facing summary, defaults to ``''``.
    :type summary: str, optional
    :param details: Full diagnostic text, defaults to ``''``.
    :type details: str, optional
    :param reason: Stable machine-readable reason, defaults to ``None``.
    :type reason: Optional[str], optional
    :param return_code: Worker return code, defaults to ``None``.
    :type return_code: Optional[int], optional
    :param transport: ``file`` or ``stdout``, defaults to ``None``.
    :type transport: Optional[str], optional
    :param truncated_bytes: Number of discarded stream bytes, defaults to ``0``.
    :type truncated_bytes: int, optional
    :param duration_ms: Worker duration in milliseconds, defaults to ``0.0``.
    :type duration_ms: float, optional

    Example::

        >>> CheckResult("demo", "PASS", True).status
        'PASS'
    """

    check_id: str
    status: str
    required: bool
    summary: str = ""
    details: str = ""
    reason: Optional[str] = None
    return_code: Optional[int] = None
    transport: Optional[str] = None
    truncated_bytes: int = 0
    duration_ms: float = 0.0

    def __post_init__(self):
        if self.status not in TERMINAL_STATUSES:
            raise ValueError("unknown self-check status: {}".format(self.status))

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a JSON-compatible result mapping.

        :return: JSON-compatible result fields.
        :rtype: Dict[str, Any]

        Example::

            >>> CheckResult("demo", "PASS", True).to_dict()["status"]
            'PASS'
        """
        return {
            "check_id": self.check_id,
            "status": self.status,
            "required": self.required,
            "summary": self.summary,
            "details": self.details,
            "reason": self.reason,
            "return_code": self.return_code,
            "transport": self.transport,
            "truncated_bytes": self.truncated_bytes,
            "duration_ms": self.duration_ms,
        }


@dataclass(frozen=True)
class LedgerEvent:
    """
    Represent one append-only ledger event.

    :param sequence: Monotonic event sequence number.
    :type sequence: int
    :param kind: Event kind such as ``terminal`` or ``duplicate_terminal``.
    :type kind: str
    :param check_id: Related check ID, defaults to ``None``.
    :type check_id: Optional[str], optional
    :param payload: JSON-compatible event payload, defaults to ``{}``.
    :type payload: Mapping[str, Any], optional
    :param timestamp_ns: Monotonic timestamp, defaults to the current clock.
    :type timestamp_ns: int, optional

    Example::

        >>> LedgerEvent(1, "pending", "demo").kind
        'pending'
    """

    sequence: int
    kind: str
    check_id: Optional[str]
    payload: Mapping[str, Any] = field(default_factory=dict)
    timestamp_ns: int = field(default_factory=time.monotonic_ns)


@dataclass(frozen=True)
class ReportSnapshot:
    """
    Frozen report view derived from one ledger check tuple.

    :param checks: Terminal results in deterministic check-ID order.
    :type checks: Tuple[CheckResult, ...]
    :param metadata: Session and environment metadata.
    :type metadata: Mapping[str, Any]
    :param counts: Counts derived from ``checks``.
    :type counts: Mapping[str, int]

    Example::

        >>> ReportSnapshot((), {}, {}).counts
        {}
    """

    checks: Tuple[CheckResult, ...]
    metadata: Mapping[str, Any]
    counts: Mapping[str, int]

    def to_dict(self) -> Dict[str, Any]:
        """
        Return a stable JSON-compatible report mapping.

        :return: Snapshot schema, metadata, checks, and status counts.
        :rtype: Dict[str, Any]

        Example::

            >>> ReportSnapshot((), {}, {}).to_dict()["schema"]
            'pyfcstm-selfcheck/v1'
        """
        return {
            "schema": "pyfcstm-selfcheck/v1",
            "metadata": dict(self.metadata),
            "checks": [check.to_dict() for check in self.checks],
            "counts": dict(self.counts),
        }


class Ledger:
    """
    Single-writer ledger with terminal-result compare-and-set semantics.

    Example::

        >>> ledger = Ledger()
        >>> ledger.reserve((CheckSpec("demo", "demo"),))
        >>> ledger.has_result("demo")
        False
    """

    def __init__(self):
        self._lock = threading.RLock()
        self._specs: Dict[str, CheckSpec] = {}
        self._states: Dict[str, str] = {}
        self._results: Dict[str, CheckResult] = {}
        self._events = []
        self._sequence = 0

    @property
    def events(self) -> Tuple[LedgerEvent, ...]:
        """Return an immutable event view."""
        with self._lock:
            return tuple(self._events)

    def _append(self, kind: str, check_id: Optional[str], payload: Mapping[str, Any]):
        self._sequence += 1
        self._events.append(LedgerEvent(self._sequence, kind, check_id, dict(payload)))

    def reserve(self, specs: Iterable[CheckSpec]) -> None:
        """
        Reserve selected checks as pending, rejecting duplicate IDs.

        :param specs: Check specifications to register.
        :type specs: Iterable[CheckSpec]
        :return: ``None``.
        :rtype: None
        :raises ValueError: If a check ID is already reserved.

        Example::

            >>> ledger = Ledger()
            >>> ledger.reserve((CheckSpec("demo", "demo"),))
            >>> ledger.get_state("demo")
            'PENDING'
        """
        with self._lock:
            for spec in specs:
                if spec.check_id in self._specs:
                    raise ValueError("duplicate check id: {}".format(spec.check_id))
                self._reserve_one(spec)

    def _reserve_one(self, spec: CheckSpec) -> None:
        """Register one previously unseen spec while the ledger lock is held."""
        self._specs[spec.check_id] = spec
        self._states[spec.check_id] = "PENDING"
        self._append("pending", spec.check_id, {"worker_key": spec.worker_key})

    def ensure_reserved(self, spec: CheckSpec) -> None:
        """
        Ensure one selected spec exists in the ledger during emergency cleanup.

        This method is intentionally separate from :meth:`reserve`: an interrupt
        can arrive while the bulk reservation is running, and cleanup must not
        retry that interrupted operation.

        :param spec: Selected check specification to register if missing.
        :type spec: CheckSpec
        :return: ``None``.
        :rtype: None

        Example::

            >>> ledger = Ledger()
            >>> ledger.ensure_reserved(CheckSpec("demo", "demo"))
            >>> ledger.get_state("demo")
            'PENDING'
        """
        with self._lock:
            if spec.check_id not in self._specs:
                self._reserve_one(spec)

    def commit(self, result: CheckResult) -> bool:
        """
        Commit one terminal result and return whether it won the CAS.

        :param result: Terminal result to commit.
        :type result: CheckResult
        :return: ``True`` for the first commit, ``False`` for a duplicate.
        :rtype: bool
        :raises KeyError: If the result ID was not reserved.

        Example::

            >>> ledger = Ledger()
            >>> ledger.reserve((CheckSpec("demo", "demo"),))
            >>> ledger.commit(CheckResult("demo", "PASS", True))
            True
        """
        with self._lock:
            if result.check_id not in self._specs:
                raise KeyError(result.check_id)
            if result.check_id in self._results:
                self._append("duplicate_terminal", result.check_id, result.to_dict())
                return False
            self._results[result.check_id] = result
            self._states[result.check_id] = result.status
            self._append("terminal", result.check_id, result.to_dict())
            return True

    def mark_running(self, check_id: str) -> bool:
        """
        Mark a reserved check as running before starting its worker.

        :param check_id: Stable identifier reserved in this ledger.
        :type check_id: str
        :return: ``True`` when the state changed to ``RUNNING``.
        :rtype: bool
        :raises KeyError: If the check was not reserved.
        :raises RuntimeError: If the check is no longer pending.

        Example::

            >>> ledger = Ledger()
            >>> ledger.reserve((CheckSpec("demo", "demo"),))
            >>> ledger.mark_running("demo")
            True
        """
        with self._lock:
            if check_id not in self._specs:
                raise KeyError(check_id)
            if check_id in self._results:
                return False
            if self._states.get(check_id) != "PENDING":
                raise RuntimeError("check is not pending: {}".format(check_id))
            self._states[check_id] = "RUNNING"
            self._append("running", check_id, {})
            return True

    def get_state(self, check_id: str) -> Optional[str]:
        """
        Return the current lifecycle state for a reserved check.

        :param check_id: Stable identifier reserved in this ledger.
        :type check_id: str
        :return: ``PENDING``, ``RUNNING``, a terminal status, or ``None``.
        :rtype: Optional[str]
        """
        with self._lock:
            return self._states.get(check_id)

    def has_result(self, check_id: str) -> bool:
        """
        Return whether a check already owns a terminal result.

        :param check_id: Stable check identifier.
        :type check_id: str
        :return: ``True`` after a terminal commit, otherwise ``False``.
        :rtype: bool

        Example::

            >>> ledger = Ledger()
            >>> ledger.reserve((CheckSpec("demo", "demo"),))
            >>> ledger.has_result("demo")
            False
        """
        with self._lock:
            return check_id in self._results

    def get_result(self, check_id: str) -> Optional[CheckResult]:
        """
        Return a committed result, or ``None`` while the check is pending.

        :param check_id: Stable identifier reserved in this ledger.
        :type check_id: str
        :return: The terminal result, or ``None`` before terminal commit.
        :rtype: Optional[CheckResult]

        Example::

            >>> ledger = Ledger()
            >>> ledger.reserve((CheckSpec("demo", "demo"),))
            >>> ledger.get_result("demo") is None
            True
        """
        with self._lock:
            return self._results.get(check_id)

    def freeze(self, metadata: Mapping[str, Any]) -> ReportSnapshot:
        """
        Freeze all selected results into one deterministic snapshot.

        :param metadata: Immutable report metadata to copy into the snapshot.
        :type metadata: Mapping[str, Any]
        :return: Frozen snapshot containing every terminal result.
        :rtype: ReportSnapshot
        :raises RuntimeError: If any reserved check lacks a terminal result.

        Example::

            >>> ledger = Ledger()
            >>> ledger.reserve((CheckSpec("demo", "demo"),))
            >>> ledger.commit(CheckResult("demo", "PASS", True))
            >>> ledger.freeze({}).counts
            {'PASS': 1}
        """
        with self._lock:
            missing = [
                check_id for check_id in self._specs if check_id not in self._results
            ]
            if missing:
                raise RuntimeError(
                    "pending self-checks: {}".format(", ".join(sorted(missing)))
                )
            checks = tuple(self._results[key] for key in sorted(self._results))
            counts: Dict[str, int] = {}
            for result in checks:
                counts[result.status] = counts.get(result.status, 0) + 1
            return ReportSnapshot(checks, dict(metadata), counts)

"""Typed self-check contracts and the ordered single-writer result ledger.

The module contains the semantic boundary shared by local checks, isolated
workers, the supervisor, and report renderers.  It intentionally contains no
thread synchronization: the supervisor is the only ledger writer.

The module contains:

* :class:`CheckSpec` - Static identity and execution policy for one check.
* :class:`CheckOutcome` - Typed semantic result returned by a check callback.
* :class:`CheckResult` - Semantic outcome plus optional process diagnostics.
* :class:`ReportSnapshot` - Immutable report input derived from the ledger.
* :class:`Ledger` - Ordered lifecycle state owned by the supervisor.
"""

from collections import Counter
from collections.abc import Mapping as MappingABC
from dataclasses import asdict, dataclass
from types import MappingProxyType
from typing import Any, Dict, Iterable, Mapping, Optional, Tuple


CHECK_OUTCOME_STATUSES = ("PASS", "WARN", "SKIP", "FAIL", "ERROR")
TERMINAL_STATUSES = CHECK_OUTCOME_STATUSES + ("BLOCKED", "TIMEOUT", "CRASH")
_RESULT_KEYS = (
    "id group title status required duration_ms summary reason expected observed "
    "evidence remediation prerequisite exception pid returncode signal ntstatus "
    "timeout transport stdout stderr encoding truncated_bytes"
).split()


@dataclass(frozen=True)
class ArtifactContext:
    """Describe the filesystem boundary used by an artifact worker.

    :param kind: Artifact kind such as ``source`` or ``wheel``.
    :type kind: str
    :param root: Absolute root from which the worker may import and read files.
    :type root: str
    :param allowed_roots: Additional absolute roots allowed for diagnostics.
    :type allowed_roots: Tuple[str, ...]
    :param allow_site_packages: Whether the worker may use user/site packages.
    :type allow_site_packages: bool

    Example::

        >>> import tempfile
        >>> with tempfile.TemporaryDirectory() as root:
        ...     ArtifactContext("source", root, (root,)).kind
        'source'
    """

    kind: str
    root: str
    allowed_roots: Tuple[str, ...] = ()
    allow_site_packages: bool = False

    def __post_init__(self) -> None:
        import os

        if not self.kind:
            raise ValueError("artifact context kind must not be empty")
        root = os.path.abspath(os.fspath(self.root))
        if not os.path.isdir(root):
            raise ValueError("artifact context root must be a directory")
        object.__setattr__(self, "root", root)
        normalized = tuple(
            os.path.abspath(os.fspath(path)) for path in self.allowed_roots
        )
        if root not in normalized:
            normalized = (root,) + normalized
        object.__setattr__(self, "allowed_roots", normalized)


def _freeze_value(value: Any) -> Any:
    """Recursively freeze report metadata before exposing it to callers."""
    if isinstance(value, MappingABC):
        return MappingProxyType(
            {key: _freeze_value(item) for key, item in value.items()}
        )
    if isinstance(value, (list, tuple)):
        return tuple(map(_freeze_value, value))
    return value


def _thaw_value(value: Any) -> Any:
    """Convert frozen report values back to JSON-compatible containers."""
    if isinstance(value, MappingABC):
        return {key: _thaw_value(item) for key, item in value.items()}
    if isinstance(value, tuple):
        return list(map(_thaw_value, value))
    return value


@dataclass(frozen=True)
class CheckSpec:
    """Describe one statically registered self-check.

    :param check_id: Stable result identifier.
    :type check_id: str
    :param worker_key: Static registry key used by local or worker execution.
    :type worker_key: str
    :param title: Human-facing check title, defaults to the check ID.
    :type title: str, optional
    :param required: Whether a failing result affects the exit code.
    :type required: bool, optional
    :param prerequisites: Check IDs that must finish first.
    :type prerequisites: Tuple[str, ...], optional
    :param execution: ``'local'`` or ``'worker'``.
    :type execution: str, optional
    :param timeout_seconds: Base worker deadline before scaling.
    :type timeout_seconds: float, optional
    :param safety: Static callback safety class, defaults to ``'pure'``.
    :type safety: str, optional
    :param prerequisite_policy: How a warning prerequisite propagates,
        defaults to ``'allow_warn'``.
    :type prerequisite_policy: str, optional
    :param explicit_skip: Whether the caller explicitly selected this check
        for a terminal ``SKIP`` result, defaults to ``False``.
    :type explicit_skip: bool, optional

    Example::

        >>> CheckSpec("runtime.metadata", "runtime_metadata").execution
        'worker'
    """

    check_id: str
    worker_key: str
    title: str = ""
    required: bool = True
    prerequisites: Tuple[str, ...] = ()
    execution: str = "worker"
    timeout_seconds: float = 30.0
    safety: str = "pure"
    prerequisite_policy: str = "allow_warn"
    explicit_skip: bool = False

    def __post_init__(self) -> None:
        if not self.check_id:
            raise ValueError("self-check ID must not be empty")
        if not self.worker_key:
            raise ValueError("self-check worker key must not be empty")
        if self.execution not in ("local", "worker"):
            raise ValueError(
                "unknown self-check execution boundary: {}".format(self.execution)
            )
        import math

        if not math.isfinite(self.timeout_seconds) or self.timeout_seconds <= 0.0:
            raise ValueError("self-check timeout must be positive")
        if self.safety not in ("pure", "blocking", "native", "external"):
            raise ValueError(
                "unknown self-check safety class: {}".format(self.safety)
            )
        if self.prerequisite_policy not in ("allow_warn", "skip_on_warn"):
            raise ValueError(
                "unknown self-check prerequisite policy: {}".format(
                    self.prerequisite_policy
                )
            )
        if self.execution == "local" and self.safety != "pure":
            raise ValueError("local self-checks must use the pure safety class")
        if not self.title:
            object.__setattr__(self, "title", self.check_id)


@dataclass(frozen=True)
class CheckOutcome:
    """Represent the typed semantic result returned by a check callback.

    :param status: Callback-owned status such as ``PASS`` or ``FAIL``.
    :type status: str
    :param summary: Concise human-facing result summary.
    :type summary: str
    :param reason: Stable machine-readable reason.
    :type reason: Optional[str], optional
    :param expected: Expected condition or value.
    :type expected: Optional[str], optional
    :param observed: Observed condition or value.
    :type observed: Optional[str], optional
    :param evidence: Full diagnostic evidence or traceback.
    :type evidence: str, optional
    :param remediation: Suggested corrective action.
    :type remediation: Optional[str], optional
    :param exception: Full exception traceback when applicable.
    :type exception: Optional[str], optional

    Example::

        >>> CheckOutcome("PASS", "runtime metadata is available").status
        'PASS'
    """

    status: str
    summary: str
    reason: Optional[str] = None
    expected: Optional[str] = None
    observed: Optional[str] = None
    evidence: str = ""
    remediation: Optional[str] = None
    exception: Optional[str] = None

    def __post_init__(self) -> None:
        if self.status not in CHECK_OUTCOME_STATUSES:
            raise ValueError(
                "check callback cannot return status: {}".format(self.status)
            )


@dataclass(frozen=True)
class CheckResult:
    """Represent one terminal check result and its process diagnostics.

    :param check_id: Stable check identifier.
    :type check_id: str
    :param status: One value from :data:`TERMINAL_STATUSES`.
    :type status: str
    :param required: Whether this result affects the public exit code.
    :type required: bool
    :param summary: Concise result summary.
    :type summary: str, optional
    :param title: Human-facing check title.
    :type title: str, optional
    :param prerequisites: Selected prerequisite IDs.
    :type prerequisites: Tuple[str, ...], optional

    Example::

        >>> CheckResult("runtime.metadata", "PASS", True).status
        'PASS'
    """

    check_id: str
    status: str
    required: bool
    summary: str = ""
    title: str = ""
    prerequisites: Tuple[str, ...] = ()
    reason: Optional[str] = None
    expected: Optional[str] = None
    observed: Optional[str] = None
    evidence: str = ""
    remediation: Optional[str] = None
    exception: Optional[str] = None
    return_code: Optional[int] = None
    transport: Optional[str] = None
    truncated_bytes: int = 0
    duration_ms: float = 0.0
    pid: Optional[int] = None
    signal: Optional[int] = None
    ntstatus: Optional[str] = None
    stdout: str = ""
    stderr: str = ""
    encoding: str = "utf-8"
    timeout: bool = False

    def __post_init__(self) -> None:
        if self.status not in TERMINAL_STATUSES:
            raise ValueError("unknown self-check status: {}".format(self.status))
        if not self.title:
            object.__setattr__(self, "title", self.check_id)

    @classmethod
    def from_outcome(
        cls, spec: CheckSpec, outcome: CheckOutcome, **diagnostics: Any
    ) -> "CheckResult":
        """Combine a static specification, semantic outcome, and diagnostics.

        :param spec: Selected check specification.
        :type spec: CheckSpec
        :param outcome: Typed callback outcome.
        :type outcome: CheckOutcome
        :param diagnostics: Optional process diagnostic fields.
        :type diagnostics: Any
        :return: A complete terminal result.
        :rtype: CheckResult

        Example::

            >>> spec = CheckSpec("runtime.metadata", "runtime_metadata")
            >>> CheckResult.from_outcome(spec, CheckOutcome("PASS", "ok")).title
            'runtime.metadata'
        """
        return cls(
            check_id=spec.check_id,
            status=outcome.status,
            required=spec.required,
            summary=outcome.summary,
            title=spec.title,
            prerequisites=spec.prerequisites,
            reason=outcome.reason,
            expected=outcome.expected,
            observed=outcome.observed,
            evidence=outcome.evidence,
            remediation=outcome.remediation,
            exception=outcome.exception,
            **diagnostics,
        )

    def to_dict(self) -> Dict[str, Any]:
        """Return the canonical JSON-compatible result mapping.

        :return: Canonical result fields without compatibility aliases.
        :rtype: Dict[str, Any]
        """
        payload = asdict(self)
        check_id = payload.pop("check_id")
        payload.update(
            id=check_id,
            group=check_id.split(".", 1)[0],
            prerequisite=list(payload.pop("prerequisites")),
            returncode=payload.pop("return_code"),
        )
        return {key: payload[key] for key in _RESULT_KEYS}


@dataclass(frozen=True)
class ReportSnapshot:
    """Store the immutable report view derived from one ledger.

    :param checks: Terminal results in stable registry order.
    :type checks: Tuple[CheckResult, ...]
    :param metadata: Session, environment, and output metadata.
    :type metadata: Mapping[str, Any]
    :param counts: Positive status counts derived from ``checks``.
    :type counts: Mapping[str, int]

    Example::

        >>> snapshot = ReportSnapshot((), {"exit_code": 0}, {})
        >>> snapshot.to_dict()["schema_version"]
        'pyfcstm-selfcheck/v1'
    """

    checks: Tuple[CheckResult, ...]
    metadata: Mapping[str, Any]
    counts: Mapping[str, int]

    def __post_init__(self) -> None:
        object.__setattr__(self, "checks", tuple(self.checks))
        object.__setattr__(self, "metadata", _freeze_value(self.metadata))
        object.__setattr__(self, "counts", _freeze_value(self.counts))

    def to_dict(self) -> Dict[str, Any]:
        """Return the canonical ``pyfcstm-selfcheck/v1`` report mapping.

        :return: Canonical top-level report fields.
        :rtype: Dict[str, Any]
        """
        metadata = _thaw_value(self.metadata)
        return {
            "schema_version": "pyfcstm-selfcheck/v1",
            "report_id": metadata.get("session_id"),
            "started_at": metadata.get("started_at"),
            "finished_at": metadata.get("finished_at"),
            "profile": metadata.get("profile"),
            "environment": metadata.get("environment", {}),
            "artifact": metadata.get("artifact", {}),
            "dependencies": metadata.get("dependencies", []),
            "capabilities": metadata.get("capabilities", {}),
            "results": [check.to_dict() for check in self.checks],
            "summary": _thaw_value(self.counts),
            "exit_code": metadata.get("exit_code"),
        }


class Ledger:
    """Track selected checks in stable order for one supervisor session.

    The supervisor is the only writer. Duplicate terminal commits are
    programming errors; duplicate worker frames are rejected by the protocol
    before reaching this class.

    Example::

        >>> ledger = Ledger()
        >>> ledger.reserve((CheckSpec("demo", "demo"),))
        >>> ledger.get_state("demo")
        'PENDING'
    """

    def __init__(self) -> None:
        self._order = []
        self._states: Dict[str, str] = {}
        self._results: Dict[str, CheckResult] = {}

    def reserve(self, specs: Iterable[CheckSpec]) -> None:
        """Reserve selected checks as pending.

        :param specs: Check specifications in execution/report order.
        :type specs: Iterable[CheckSpec]
        :raises ValueError: If an ID is reserved more than once.
        """
        for spec in specs:
            if spec.check_id in self._states:
                raise ValueError("duplicate check id: {}".format(spec.check_id))
            self._order.append(spec.check_id)
            self._states[spec.check_id] = "PENDING"

    def ensure_reserved(self, spec: CheckSpec) -> None:
        """Reserve one spec without re-entering bulk setup."""
        if spec.check_id not in self._states:
            self._order.append(spec.check_id)
            self._states[spec.check_id] = "PENDING"

    def mark_running(self, check_id: str) -> None:
        """Move one pending check to ``RUNNING``.

        :param check_id: Reserved check identifier.
        :type check_id: str
        :raises KeyError: If the check was not reserved.
        :raises RuntimeError: If the check is not pending.
        """
        if check_id not in self._states:
            raise KeyError(check_id)
        if self._states[check_id] != "PENDING":
            raise RuntimeError("check is not pending: {}".format(check_id))
        self._states[check_id] = "RUNNING"

    def commit(self, result: CheckResult) -> None:
        """Commit exactly one terminal result.

        :param result: Terminal result to store.
        :type result: CheckResult
        :raises KeyError: If the result ID was not reserved.
        :raises RuntimeError: If a terminal result already exists.
        """
        if result.check_id not in self._states:
            raise KeyError(result.check_id)
        if result.check_id in self._results:
            raise RuntimeError("duplicate terminal result: {}".format(result.check_id))
        self._results[result.check_id] = result
        self._states[result.check_id] = result.status

    def get_state(self, check_id: str) -> Optional[str]:
        """Return the lifecycle state for *check_id*, if reserved."""
        return self._states.get(check_id)

    def get_result(self, check_id: str) -> Optional[CheckResult]:
        """Return the committed result for *check_id*, if available."""
        return self._results.get(check_id)

    def freeze(self, metadata: Mapping[str, Any]) -> ReportSnapshot:
        """Freeze all selected terminal results into one snapshot.

        :param metadata: Report metadata copied into the snapshot.
        :type metadata: Mapping[str, Any]
        :return: Immutable result tuple and derived positive counts.
        :rtype: ReportSnapshot
        :raises RuntimeError: If any selected check lacks a terminal result.
        """
        missing = [key for key in self._order if key not in self._results]
        if missing:
            raise RuntimeError(
                "pending self-checks: {}".format(", ".join(sorted(missing)))
            )
        checks = tuple(self._results[key] for key in self._order)
        counts = dict(Counter(result.status for result in checks))
        return ReportSnapshot(checks, metadata, counts)

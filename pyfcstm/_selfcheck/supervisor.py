"""Run selected self-checks serially under one single-writer supervisor.

The supervisor resolves prerequisites, executes exactly one local callback or
isolated worker at a time, commits its terminal result, and only then advances
to the next check. It owns the ledger, final snapshot, report, and exit code.
"""

import os
import sys
import time
import traceback
import uuid
from dataclasses import replace
from typing import Iterable, Sequence

from .arguments import SelfCheckArgumentError, _requested_output_format
from .arguments import parse_selfcheck_args
from .environment import collect_environment
from .model import (
    CheckOutcome,
    CheckResult,
    CheckSpec,
    Ledger,
    ReportSnapshot,
)
from .process import run_check_process
from .registry import (
    CAPABILITY_CHECK_IDS,
    collect_dependency_diagnostics,
    get_worker,
    registry_metadata,
    selected_specs,
)
from .report import (
    render_json,
    write_human,
    write_human_plan,
    write_human_result,
    write_human_start,
    write_human_environment,
    write_human_summary,
    write_report,
)


_PROFILE_DEADLINES = {"default": 180.0, "full": 300.0, "visualize": 300.0}
_FAILING_STATUSES = ("BLOCKED", "FAIL", "ERROR", "TIMEOUT", "CRASH")
_STRICT_WARN_REASONS = frozenset(
    (
        "capability_unavailable",
        "identity_invalid",
        "identity_incomplete",
        "identity_stale",
        "identity_unavailable",
        "metadata_unavailable",
        "resource_missing",
        "resource_invalid",
    )
)


def _runtime_artifact_kind() -> str:
    """Classify the running source, installed package, or frozen artifact."""
    package_root = os.path.dirname(os.path.abspath(__file__))
    package_parent = os.path.dirname(os.path.dirname(package_root))
    if getattr(sys, "frozen", False):
        return "frozen"
    if os.path.exists(os.path.join(package_parent, ".git")):
        return "source"
    try:
        entries = os.listdir(package_parent)
    except OSError:
        return "source"
    for name in entries:
        if name.startswith("pyfcstm-") and name.endswith(".dist-info"):
            return "wheel"
        if name.startswith("pyfcstm") and name.endswith(".egg-info"):
            # Editable installs expose legacy egg-info beside the package and
            # do not provide the wheel RECORD closure.
            return "source"
    return "source"


def _artifact_metadata(redact: bool = True):
    """Return stable artifact identity fields for every report mode.

    :param redact: Hide filesystem paths when true.
    :type redact: bool
    :return: JSON-compatible artifact identity metadata.
    :rtype: Dict[str, object]

    Example::

        >>> data = _artifact_metadata()
        >>> data["kind"] in ("source", "wheel", "frozen-onefile", "frozen-onedir", "frozen-unknown")
        True

    ``sdist`` is selected by the artifact build context, not inferred from a
    live runtime package directory.
    """
    package_root = os.path.dirname(os.path.abspath(__file__))
    package_parent = os.path.dirname(os.path.dirname(package_root))
    kind = _runtime_artifact_kind()
    executable = getattr(sys, "executable", None)
    data = {
        "kind": kind,
        "frozen": bool(getattr(sys, "frozen", False)),
        "root": package_parent,
        "executable": os.path.abspath(executable) if executable else None,
    }
    if redact:
        data["root"] = "<redacted>"
        if data["executable"] is not None:
            data["executable"] = "<redacted>"
    return data


def _validate_specs(specs):
    """Return registry validation diagnostics before any callback is started."""
    seen = set()
    errors = []
    for index, spec in enumerate(specs):
        if not isinstance(spec, CheckSpec):
            errors.append(
                "invalid self-check specification at index {}: {}".format(
                    index, type(spec).__name__
                )
            )
            continue
        if spec.check_id in seen:
            errors.append("duplicate self-check ID: {}".format(spec.check_id))
        seen.add(spec.check_id)
        if spec.execution == "local" and spec.safety != "pure":
            errors.append(
                "blocking local callback is not allowed: {}".format(spec.check_id)
            )
    return tuple(errors)


def _exit_code(snapshot: ReportSnapshot, fail_on_warn: bool) -> int:
    """Compute the stable public exit code for *snapshot*."""
    for result in snapshot.checks:
        if result.required and (
            result.status in _FAILING_STATUSES
            or (fail_on_warn and result.status == "WARN")
        ):
            return 1
    return 0


def _error_outcome(summary: str, reason: str) -> CheckOutcome:
    """Build an ``ERROR`` outcome with the active exception traceback."""
    evidence = traceback.format_exc()
    return CheckOutcome(
        "ERROR",
        summary,
        reason=reason,
        evidence=evidence,
        exception=evidence,
    )


def _run_local_check(spec: CheckSpec) -> CheckResult:
    """Run a bootstrap-safe callback in the supervisor process.

    :param spec: Selected local check specification.
    :type spec: CheckSpec
    :return: Terminal typed result with elapsed time.
    :rtype: CheckResult
    """
    started = time.monotonic()
    try:
        worker = get_worker(spec.worker_key)
    except KeyError:
        outcome = _error_outcome("local check is not registered", "unknown_local_check")
    else:
        try:
            outcome = worker()
            if not isinstance(outcome, CheckOutcome):
                raise TypeError("self-check worker must return CheckOutcome")
        except SystemExit:
            outcome = _error_outcome(
                "local check raised SystemExit", "local_check_system_exit"
            )
        except BaseException as err:
            # Registered callbacks may raise any ordinary Exception; control
            # sentinels remain visible to the supervisor and are re-raised.
            if not isinstance(err, Exception):
                raise
            outcome = _error_outcome(
                "local check raised an exception", "local_check_exception"
            )
    return CheckResult.from_outcome(
        spec, outcome, duration_ms=(time.monotonic() - started) * 1000
    )


def _commit_terminal(
    ledger: Ledger,
    spec: CheckSpec,
    status: str,
    summary: str,
    reason: str,
    evidence: str = "",
) -> None:
    """Build and commit one terminal result through the single writer."""
    ledger.ensure_reserved(spec)
    ledger.commit(
        CheckResult(
            spec.check_id,
            status,
            spec.required,
            summary=summary,
            title=spec.title,
            prerequisites=spec.prerequisites,
            reason=reason,
            evidence=evidence,
        )
    )


def _replace_terminal(
    ledger: Ledger,
    spec: CheckSpec,
    status: str,
    summary: str,
    reason: str,
    evidence: str = "",
) -> None:
    """Replace one provisional terminal result with final diagnostics."""
    ledger.replace(
        CheckResult(
            spec.check_id,
            status,
            spec.required,
            summary=summary,
            title=spec.title,
            prerequisites=spec.prerequisites,
            reason=reason,
            evidence=evidence,
        )
    )


def _normalize_required_warning(spec: CheckSpec, result: CheckResult) -> CheckResult:
    """Turn strict required warnings into failures without changing optional probes."""
    if (
        spec.required
        and result.status == "WARN"
        and result.reason in _STRICT_WARN_REASONS
    ):
        return replace(
            result,
            status="FAIL",
            summary="required capability or resource is unavailable: {}".format(
                result.summary
            ),
        )
    return result


def _terminalize_unfinished(
    ledger: Ledger,
    specs: Iterable[CheckSpec],
    interrupted: bool,
    evidence: str = "",
) -> None:
    """Give every selected unfinished check one terminal result."""
    running_status = "CRASH" if interrupted else "ERROR"
    summary = (
        "self-check interrupted" if interrupted else "self-check infrastructure error"
    )
    reason = "supervisor_interrupted" if interrupted else "supervisor_infrastructure"
    for spec in specs:
        if not isinstance(spec, CheckSpec):
            # A malformed registry entry is already represented by the
            # synthetic registry/infrastructure result.
            continue
        if ledger.get_result(spec.check_id) is not None:
            continue
        status = (
            running_status
            if ledger.get_state(spec.check_id) == "RUNNING"
            else "BLOCKED"
        )
        _commit_terminal(ledger, spec, status, summary, reason, evidence)


def _argument_snapshot(error: BaseException) -> ReportSnapshot:
    """Build a canonical pre-ledger snapshot for argument errors."""
    now = time.time()
    result = CheckResult.from_outcome(
        CheckSpec("selfcheck.arguments", "synthetic", title="self-check arguments"),
        CheckOutcome(
            "ERROR",
            "invalid self-check arguments",
            reason="argument_error",
            evidence="{}: {}".format(type(error).__name__, error),
        ),
    )
    metadata = {"started_at": now, "finished_at": now, "exit_code": 2}
    return ReportSnapshot((result,), metadata, {"ERROR": 1})


def _emit_snapshot(snapshot: ReportSnapshot, output_format: str, color: str) -> int:
    """Emit the frozen snapshot once; bootstrap owns output recovery."""
    if output_format == "json":
        print(render_json(snapshot), flush=True)
    else:
        write_human(snapshot, color)
    return int(snapshot.metadata["exit_code"])


def _run_selected_checks(
    ledger: Ledger, specs, options, global_deadline: float, progress=None
) -> None:
    """Execute selected checks once, in registry order."""
    def commit_terminal(spec, status, summary, reason, evidence=""):
        _commit_terminal(ledger, spec, status, summary, reason, evidence)
        if progress is not None:
            progress(ledger.get_result(spec.check_id))

    def commit_result(result):
        ledger.commit(result)
        if progress is not None:
            progress(result)

    for spec in specs:
        if spec.explicit_skip:
            commit_terminal(
                spec,
                "SKIP",
                "check was explicitly skipped",
                "explicit_skip",
            )
            continue
        prerequisites = [ledger.get_result(item) for item in spec.prerequisites]
        if any(result is None for result in prerequisites):
            commit_terminal(
                spec,
                "BLOCKED",
                "prerequisite was never resolved",
                "prerequisite_unresolved",
            )
            continue
        skipped_capability = any(
            result.status == "WARN" and spec.prerequisite_policy == "skip_on_warn"
            for result in prerequisites
        )
        failed_capability = any(
            result.status in ("FAIL", "ERROR", "TIMEOUT", "CRASH", "BLOCKED")
            and prerequisite_id in CAPABILITY_CHECK_IDS
            for prerequisite_id, result in zip(spec.prerequisites, prerequisites)
        )
        skipped_prerequisite = any(
            result.status == "SKIP" for result in prerequisites
        )
        if skipped_capability:
            commit_terminal(
                spec,
                "SKIP",
                "capability prerequisite is unavailable",
                "capability_unavailable",
            )
            continue
        if failed_capability:
            commit_terminal(
                spec,
                "BLOCKED",
                "capability prerequisite failed",
                "prerequisite_failed",
            )
            continue
        if skipped_prerequisite:
            commit_terminal(
                spec,
                "SKIP",
                "prerequisite was skipped",
                "prerequisite_skipped",
            )
            continue
        if any(
            result.status not in ("PASS", "WARN")
            or (
                result.status == "WARN"
                and spec.prerequisite_policy != "allow_warn"
            )
            for result in prerequisites
        ):
            commit_terminal(spec, "BLOCKED", "prerequisite failed", "prerequisite_failed")
            continue
        remaining = global_deadline - time.monotonic()
        if remaining <= 0.0:
            commit_terminal(
                spec,
                "BLOCKED",
                "global self-check deadline exceeded",
                "global_deadline",
            )
            continue
        ledger.mark_running(spec.check_id)
        timeout = min(spec.timeout_seconds * options.timeout_scale, remaining)
        try:
            if spec.execution == "local":
                result = _run_local_check(spec)
            else:
                if options.network:
                    result = run_check_process(
                        spec,
                        timeout=timeout,
                        timeout_scale=options.timeout_scale,
                        network=True,
                    )
                else:
                    result = run_check_process(
                        spec,
                        timeout=timeout,
                        timeout_scale=options.timeout_scale,
                    )
        except BaseException as err:
            # Process failures are isolated so independent checks continue;
            # non-Exception control sentinels must still propagate.
            if not isinstance(err, Exception):
                raise
            evidence = traceback.format_exc()
            commit_terminal(
                spec,
                "ERROR",
                "worker supervisor error",
                "worker_supervisor_error",
                evidence,
            )
            continue
        commit_result(_normalize_required_warning(spec, result))


def run_supervisor(arguments: Sequence[str], start_emitted: bool = False) -> int:
    """Run selected checks and emit one final report.

    :param arguments: Arguments after the public ``--self-check`` token.
    :type arguments: Sequence[str]
    :param start_emitted: Whether the bootstrap already emitted the immediate
        human-mode header, defaults to ``False``.
    :type start_emitted: bool, optional
    :return: Stable self-check exit code.
    :rtype: int

    Example::

        >>> import contextlib
        >>> import io
        >>> with contextlib.redirect_stdout(io.StringIO()):
        ...     code = run_supervisor(("--format", "json", "--network"))
        >>> code
        2
    """
    try:
        options = parse_selfcheck_args(arguments)
    except SelfCheckArgumentError as err:
        output_format = _requested_output_format(arguments)
        return _emit_snapshot(_argument_snapshot(err), output_format, "never")

    streaming_human = options.output_format == "human"
    if streaming_human and not start_emitted:
        # This line intentionally runs before registry/dependency discovery so
        # a slow import or native probe cannot look like a hung command.
        write_human_start(options.profile, options.color)

    ledger = Ledger()
    specs = ()
    report_specs = ()
    report_spec = None
    progress = None
    emitted = [0]
    metadata = {
        "session_id": uuid.uuid4().hex,
        "profile": options.profile,
        "started_at": time.time(),
        "artifact": _artifact_metadata(options.redact),
    }
    forced_exit = None
    try:
        specs = selected_specs(options.profile)
        validation_errors = _validate_specs(specs)
        registry_spec = None
        if validation_errors:
            registry_spec = CheckSpec(
                "selfcheck.registry",
                "synthetic",
                title="self-check registry",
            )
            report_specs = (registry_spec,)
        else:
            report_specs = tuple(specs)
        if options.report:
            report_spec = CheckSpec(
                "selfcheck.report_write",
                "synthetic",
                title="self-check report write",
            )
            report_specs = tuple(report_specs) + (report_spec,)
        if streaming_human:
            write_human_plan(len(report_specs), options.profile, options.color)

            def progress(result):
                emitted[0] += 1
                write_human_result(
                    result, emitted[0], len(report_specs), options.color
                )

        if validation_errors:
            # ``report_specs`` is the complete terminal result set for this
            # branch, so the streamed denominator matches the final snapshot.
            specs = (registry_spec,)
            ledger.reserve(specs)
            metadata["dependencies"] = []
            metadata["capabilities"] = {
                "registry": dict(registry_metadata(options.profile)),
                "dependency_diagnostics": list(collect_dependency_diagnostics()),
            }
            metadata["environment"] = collect_environment(options.redact)
            if streaming_human:
                write_human_environment(metadata["environment"], options.color)
            _commit_terminal(
                ledger,
                registry_spec,
                "ERROR",
                "self-check registry is invalid",
                "registry_invalid",
                evidence="\n".join(validation_errors),
            )
            if progress is not None:
                progress(ledger.get_result(registry_spec.check_id))
            forced_exit = 1
            specs = (registry_spec,)
        else:
            ledger.reserve(specs)
            metadata["dependencies"] = [
                {"id": spec.check_id, "prerequisite": list(spec.prerequisites)}
                for spec in specs
            ]
            registry_info = dict(registry_metadata(options.profile))
            metadata["capabilities"] = {
                "registry": registry_info,
                "dependency_diagnostics": list(collect_dependency_diagnostics()),
            }
            metadata["environment"] = collect_environment(options.redact)
            if streaming_human:
                write_human_environment(metadata["environment"], options.color)
            deadline_seconds = _PROFILE_DEADLINES[options.profile] * options.timeout_scale
            _run_selected_checks(
                ledger,
                specs,
                options,
                time.monotonic() + deadline_seconds,
                progress=progress,
            )
    except KeyboardInterrupt:
        forced_exit = 130
        _terminalize_unfinished(
            ledger,
            specs,
            interrupted=True,
        )
    except BaseException as err:
        # Registry, environment, and process setup failures are recoverable;
        # keyboard/control sentinels remain outside this boundary.
        if not isinstance(err, Exception):
            raise
        forced_exit = 3
        evidence = traceback.format_exc()
        infrastructure_spec = CheckSpec(
            "selfcheck.infrastructure",
            "synthetic",
            title="self-check infrastructure",
        )
        if infrastructure_spec.check_id not in {
            getattr(item, "check_id", None) for item in report_specs
        }:
            report_specs = tuple(report_specs) + (infrastructure_spec,)
        if options.report and report_spec is None:
            report_spec = CheckSpec(
                "selfcheck.report_write",
                "synthetic",
                title="self-check report write",
            )
            report_specs = tuple(report_specs) + (report_spec,)
        if streaming_human and progress is None:
            write_human_plan(len(report_specs), options.profile, options.color)

            def progress(result):
                emitted[0] += 1
                write_human_result(
                    result, emitted[0], len(report_specs), options.color
                )

            if metadata.get("environment"):
                write_human_environment(metadata["environment"], options.color)
        _terminalize_unfinished(
            ledger,
            specs,
            interrupted=False,
            evidence=evidence,
        )
        _commit_terminal(
            ledger,
            infrastructure_spec,
            "ERROR",
            "self-check infrastructure error",
            "infrastructure_error",
            evidence,
        )
        if progress is not None:
            progress(ledger.get_result(infrastructure_spec.check_id))

    metadata["finished_at"] = time.time()
    provisional = ledger.freeze(metadata)
    exit_code = (
        forced_exit
        if forced_exit is not None
        else _exit_code(provisional, options.fail_on_warn)
    )
    metadata["exit_code"] = exit_code
    snapshot = ledger.freeze(metadata)

    if options.report:
        # Commit a provisional PASS before writing so the on-disk report and
        # final stdout can share one exact snapshot.  A failed write replaces
        # this terminal result with its complete diagnostic evidence.
        if report_spec is None:
            report_spec = CheckSpec(
                "selfcheck.report_write",
                "synthetic",
                title="self-check report write",
            )
        _commit_terminal(
            ledger,
            report_spec,
            "PASS",
            "report destination is writable",
            "report_write_pending",
        )
        snapshot = ledger.freeze(metadata)
        try:
            report_error = write_report(options.report, snapshot)
        except (OSError, TypeError, UnicodeError, ValueError) as err:
            report_error = "{}: {}\n{}".format(
                type(err).__name__, err, traceback.format_exc()
            )
        if report_error is not None:
            _replace_terminal(
                ledger,
                report_spec,
                "ERROR",
                "report write failed",
                "report_write",
                report_error,
            )
            metadata["exit_code"] = 1 if forced_exit is None else forced_exit
            snapshot = ledger.freeze(metadata)
        if progress is not None:
            progress(ledger.get_result(report_spec.check_id))

    if streaming_human:
        write_human_summary(snapshot, options.color)
        return int(snapshot.metadata["exit_code"])
    return _emit_snapshot(snapshot, options.output_format, options.color)

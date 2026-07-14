"""Run selected self-checks serially under one single-writer supervisor.

The supervisor resolves prerequisites, executes exactly one local callback or
isolated worker at a time, commits its terminal result, and only then advances
to the next check. It owns the ledger, final snapshot, report, and exit code.
"""

import json
import time
import traceback
import uuid
from typing import Iterable, Sequence

from .arguments import SelfCheckArgumentError, _requested_output_format
from .arguments import parse_selfcheck_args
from .environment import collect_environment
from .model import CheckOutcome, CheckResult, CheckSpec, Ledger, ReportSnapshot
from .process import run_check_process
from .registry import get_worker, selected_specs
from .report import emergency_write, render_json, write_human, write_report
from .report import _silence_broken_stdout


_PROFILE_DEADLINES = {"default": 180.0, "full": 300.0, "visualize": 300.0}
_FAILING_STATUSES = ("BLOCKED", "FAIL", "ERROR", "TIMEOUT", "CRASH")


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
            # Callback failures are ordinary Exceptions; control sentinels
            # remain visible to the caller.
            if not isinstance(err, Exception):
                raise
            outcome = _error_outcome(
                "local check raised an exception", "local_check_exception"
            )
    return CheckResult.from_outcome(
        spec, outcome, duration_ms=(time.monotonic() - started) * 1000
    )


def _terminal_result(
    spec: CheckSpec,
    status: str,
    summary: str,
    reason: str,
    evidence: str = "",
) -> CheckResult:
    """Build a supervisor-owned terminal result for *spec*."""
    return CheckResult(
        spec.check_id,
        status,
        spec.required,
        summary=summary,
        title=spec.title,
        prerequisites=spec.prerequisites,
        reason=reason,
        evidence=evidence,
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
    ledger.commit(_terminal_result(spec, status, summary, reason, evidence))


def _commit_blocked(ledger: Ledger, spec: CheckSpec, summary: str, reason: str) -> None:
    """Commit one supervisor-owned blocked result."""
    _commit_terminal(ledger, spec, "BLOCKED", summary, reason)


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
        if ledger.get_result(spec.check_id) is not None:
            continue
        status = (
            running_status
            if ledger.get_state(spec.check_id) == "RUNNING"
            else "BLOCKED"
        )
        _commit_terminal(ledger, spec, status, summary, reason, evidence)


def _commit_synthetic(
    ledger: Ledger,
    check_id: str,
    title: str,
    summary: str,
    reason: str,
    evidence: str,
) -> None:
    """Commit one supervisor-owned synthetic error at most once."""
    spec = CheckSpec(check_id, "synthetic", title=title)
    _commit_terminal(ledger, spec, "ERROR", summary, reason, evidence)


def _argument_snapshot(error: BaseException) -> ReportSnapshot:
    """Build a canonical pre-ledger snapshot for argument errors."""
    now = time.time()
    result = CheckResult(
        "selfcheck.arguments",
        "ERROR",
        True,
        summary="invalid self-check arguments",
        title="self-check arguments",
        reason="argument_error",
        evidence="{}: {}".format(type(error).__name__, error),
    )
    metadata = {"started_at": now, "finished_at": now, "exit_code": 2}
    return ReportSnapshot((result,), metadata, {"ERROR": 1})


def _output_failure_snapshot(snapshot: ReportSnapshot, evidence: str) -> ReportSnapshot:
    """Add one emergency-only output diagnostic to a frozen snapshot."""
    result = CheckResult(
        "selfcheck.output",
        "ERROR",
        True,
        summary="self-check output failure",
        title="self-check output",
        reason="output_failure",
        evidence=evidence,
    )
    metadata = dict(snapshot.metadata)
    metadata["exit_code"] = 130 if metadata.get("exit_code") == 130 else 3
    counts = dict(snapshot.counts)
    counts["ERROR"] = counts.get("ERROR", 0) + 1
    return ReportSnapshot(snapshot.checks + (result,), metadata, counts)


def _emit_final(
    snapshot: ReportSnapshot,
    output_format: str,
    color: str,
    report_path: str = None,
) -> int:
    """Emit one final snapshot, using one emergency diagnostic on failure."""
    try:
        if output_format == "json":
            print(render_json(snapshot), flush=True)
        else:
            write_human(snapshot, color)
    except (Exception, SystemExit) as err:
        evidence = traceback.format_exc()
        emergency_snapshot = _output_failure_snapshot(snapshot, evidence)
        report_error = None
        if report_path:
            try:
                report_error = write_report(report_path, emergency_snapshot)
            except BaseException as report_exception:
                # A report rewrite can fail independently after output failed;
                # keep that diagnostic in the emergency channel, but preserve
                # non-runtime control sentinels for the outer bootstrap.
                if not isinstance(report_exception, (Exception, SystemExit)):
                    raise
                report_error = "{}: {}".format(
                    type(report_exception).__name__, report_exception
                )
        if report_error:
            emergency_snapshot = _output_failure_snapshot(
                snapshot,
                evidence + "\nreport rewrite failed: " + report_error,
            )
        try:
            if output_format == "json":
                try:
                    message = json.dumps(
                        emergency_snapshot.to_dict(),
                        ensure_ascii=True,
                        sort_keys=True,
                        separators=(",", ":"),
                    )
                except (TypeError, ValueError) as serialization_error:
                    # The emergency snapshot contains only built-in values; keep
                    # a plain diagnostic if a future field violates that rule.
                    message = "self-check output failure [selfcheck.output ERROR]: {}\n{}".format(
                        serialization_error, evidence
                    )
                emergency_write(message + "\n", "json")
            else:
                message = (
                    "self-check output failure [selfcheck.output ERROR]:\n{}".format(
                        evidence
                    )
                )
                if report_error:
                    message += "report rewrite failed: {}\n".format(report_error)
                emergency_write(
                    message,
                    output_format,
                )
        finally:
            _silence_broken_stdout(err)
        return int(emergency_snapshot.metadata["exit_code"])
    return int(snapshot.metadata["exit_code"])


def _run_selected_checks(
    ledger: Ledger, specs, options, global_deadline: float
) -> None:
    """Execute selected checks once, in registry order."""
    for spec in specs:
        prerequisites = [ledger.get_result(item) for item in spec.prerequisites]
        if any(result is None for result in prerequisites):
            _commit_blocked(
                ledger,
                spec,
                "prerequisite was never resolved",
                "prerequisite_unresolved",
            )
            continue
        if any(
            result.status not in ("PASS", "WARN", "SKIP") for result in prerequisites
        ):
            _commit_blocked(ledger, spec, "prerequisite failed", "prerequisite_failed")
            continue
        remaining = global_deadline - time.monotonic()
        if remaining <= 0.0:
            _commit_blocked(
                ledger, spec, "global self-check deadline exceeded", "global_deadline"
            )
            continue
        ledger.mark_running(spec.check_id)
        timeout = min(spec.timeout_seconds * options.timeout_scale, remaining)
        try:
            result = (
                _run_local_check(spec)
                if spec.execution == "local"
                else run_check_process(
                    spec, timeout=timeout, timeout_scale=options.timeout_scale
                )
            )
        except BaseException as err:
            # Process failures are isolated so independent checks continue.
            if not isinstance(err, Exception):
                raise
            evidence = traceback.format_exc()
            result = _terminal_result(
                spec,
                "ERROR",
                "worker supervisor error",
                "worker_supervisor_error",
                evidence,
            )
        ledger.commit(result)


def run_supervisor(arguments: Sequence[str]) -> int:
    """Run selected checks and emit one final report.

    :param arguments: Arguments after the public ``--self-check`` token.
    :type arguments: Sequence[str]
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
        return _emit_final(_argument_snapshot(err), output_format, "never")

    ledger = Ledger()
    specs = ()
    metadata = {
        "session_id": uuid.uuid4().hex,
        "profile": options.profile,
        "started_at": time.time(),
    }
    forced_exit = None
    try:
        specs = selected_specs(options.profile)
        ledger.reserve(specs)
        metadata["dependencies"] = [
            {"id": spec.check_id, "prerequisite": list(spec.prerequisites)}
            for spec in specs
        ]
        metadata["environment"] = collect_environment(options.redact)
        deadline_seconds = _PROFILE_DEADLINES[options.profile] * options.timeout_scale
        _run_selected_checks(
            ledger, specs, options, time.monotonic() + deadline_seconds
        )
    except KeyboardInterrupt:
        forced_exit = 130
        _terminalize_unfinished(
            ledger,
            specs,
            interrupted=True,
        )
    except BaseException as err:
        if not isinstance(err, (Exception, SystemExit)):
            raise
        forced_exit = 3
        evidence = traceback.format_exc()
        _terminalize_unfinished(
            ledger,
            specs,
            interrupted=False,
            evidence=evidence,
        )
        _commit_synthetic(
            ledger,
            "selfcheck.infrastructure",
            "self-check infrastructure",
            "self-check infrastructure error",
            "infrastructure_error",
            evidence,
        )

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
        try:
            report_error = write_report(options.report, snapshot)
        except BaseException as err:
            if isinstance(err, (KeyboardInterrupt, SystemExit)):
                raise
            if not isinstance(err, Exception):
                raise
            report_error = "{}: {}\n{}".format(
                type(err).__name__, err, traceback.format_exc()
            )
        if report_error is not None:
            _commit_synthetic(
                ledger,
                "selfcheck.report_write",
                "self-check report write",
                "report write failed",
                "report_write",
                report_error,
            )
            metadata["exit_code"] = 1 if forced_exit is None else forced_exit
            snapshot = ledger.freeze(metadata)

    return _emit_final(snapshot, options.output_format, options.color, options.report)

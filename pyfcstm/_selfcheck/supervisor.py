"""Supervisor orchestration for the standard-library self-check command."""

import time
import traceback
import uuid
from typing import Sequence

from .arguments import SelfCheckArgumentError
from .arguments import parse_selfcheck_args
from .environment import collect_environment
from .model import CheckResult
from .model import CheckSpec
from .model import Ledger
from .process import run_check_process
from .registry import selected_specs
from .report import emergency_write
from .report import render_human
from .report import render_json
from .report import write_report


_PROFILE_DEADLINES = {
    "default": 180.0,
    "full": 300.0,
    "visualize": 300.0,
}
_EXPECTED_INFRA_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    KeyError,
    TypeError,
    ImportError,
    AttributeError,
    UnicodeError,
)


def _exit_code(snapshot, fail_on_warn: bool) -> int:
    """Compute the stable public exit code from one snapshot."""
    for result in snapshot.checks:
        if result.required and result.status in (
            "FAIL",
            "BLOCKED",
            "ERROR",
            "TIMEOUT",
            "CRASH",
        ):
            return 1
        if fail_on_warn and result.required and result.status == "WARN":
            return 1
    return 0


def _make_infrastructure_snapshot(phase: str, error: BaseException):
    """Return a serializable :class:`ReportSnapshot` for setup failures."""
    from .model import ReportSnapshot

    result = CheckResult(
        "selfcheck.infrastructure",
        "ERROR",
        True,
        summary="self-check infrastructure error",
        details="{}: {}\n{}".format(phase, error, traceback.format_exc()),
        reason="infrastructure_error",
    )
    return ReportSnapshot((result,), {"phase": phase}, {"ERROR": 1})


def _emit_snapshot(snapshot, options) -> bool:
    """Render one snapshot while preserving the selected output channel."""
    try:
        output = (
            render_json(snapshot)
            if options.output_format == "json"
            else render_human(snapshot, options.color)
        )
        print(output, end="")
        return True
    except (OSError, UnicodeError, ValueError, TypeError) as err:
        emergency_write(
            "self-check render error: {}\n".format(err), options.output_format
        )
        return False


def run_supervisor(arguments: Sequence[str]) -> int:
    """
    Run selected checks and emit one final report.

    :param arguments: Arguments after the public ``--self-check`` token.
    :type arguments: Sequence[str]
    :return: Stable self-check exit code.
    :rtype: int
    """
    try:
        options = parse_selfcheck_args(arguments)
    except SelfCheckArgumentError as err:
        emergency_write("self-check argument error: {}\n".format(err), "json")
        return 2

    started = time.time()
    ledger = Ledger()
    specs = ()
    try:
        specs = selected_specs(options.profile)
        ledger.reserve(specs)
        metadata = {
            "session_id": uuid.uuid4().hex,
            "profile": options.profile,
            "timeout_scale": options.timeout_scale,
            "registry_coverage": 1,
            "environment": collect_environment(options.redact),
            "started_at": started,
        }
        global_deadline = time.monotonic() + _PROFILE_DEADLINES[options.profile] * (
            options.timeout_scale
        )
        metadata["global_deadline_seconds"] = _PROFILE_DEADLINES[options.profile] * (
            options.timeout_scale
        )
        for spec in specs:
            prerequisite_results = [
                ledger.get_result(item) for item in spec.prerequisites
            ]
            if any(result is None for result in prerequisite_results):
                ledger.commit(
                    CheckResult(
                        spec.check_id,
                        "BLOCKED",
                        spec.required,
                        summary="prerequisite did not complete",
                        reason="prerequisite_pending",
                    )
                )
                continue
            if any(
                result.status not in ("PASS", "WARN", "SKIP")
                for result in prerequisite_results
            ):
                ledger.commit(
                    CheckResult(
                        spec.check_id,
                        "BLOCKED",
                        spec.required,
                        summary="prerequisite failed",
                        reason="prerequisite_failed",
                    )
                )
                continue
            remaining = global_deadline - time.monotonic()
            if remaining <= 0.0:
                ledger.commit(
                    CheckResult(
                        spec.check_id,
                        "BLOCKED",
                        spec.required,
                        summary="global self-check deadline exceeded",
                        reason="global_deadline",
                    )
                )
                continue
            timeout = min(30.0 * options.timeout_scale, remaining)
            try:
                if options.timeout_scale == 1.0:
                    result = run_check_process(spec, timeout=timeout)
                else:
                    result = run_check_process(
                        spec, timeout=timeout, timeout_scale=options.timeout_scale
                    )
            except _EXPECTED_INFRA_ERRORS as err:
                result = CheckResult(
                    spec.check_id,
                    "ERROR",
                    spec.required,
                    summary="worker supervisor error",
                    details="{}: {}".format(type(err).__name__, err),
                    reason="worker_supervisor_error",
                )
            if result.status == "PASS" and result.summary.startswith(
                "__SELFCHECK_WARN__:"
            ):
                result = CheckResult(
                    result.check_id,
                    "WARN",
                    result.required,
                    summary=result.summary.split(":", 1)[1],
                )
            ledger.commit(result)
        metadata["finished_at"] = time.time()
        snapshot = ledger.freeze(metadata)
    except KeyboardInterrupt:
        for index, spec in enumerate(specs if "specs" in locals() else ()):
            if not ledger.has_result(spec.check_id):
                status = "CRASH" if index == 0 else "BLOCKED"
                ledger.commit(
                    CheckResult(
                        spec.check_id,
                        status,
                        spec.required,
                        summary="self-check interrupted",
                        reason="supervisor_interrupted",
                    )
                )
        try:
            snapshot = ledger.freeze({"interrupted": True})
            output = (
                render_json(snapshot)
                if options.output_format == "json"
                else render_human(snapshot, options.color)
            )
            print(output, end="")
        except (OSError, UnicodeError, ValueError, RuntimeError):
            # A second failure while producing the partial Ctrl-C report is handled by emergency output.
            emergency_write(
                "self-check interrupted before report completion\n",
                options.output_format,
            )
        emergency_write("self-check interrupted\n", options.output_format)
        return 130
    except _EXPECTED_INFRA_ERRORS as err:
        # Setup/snapshot failures still emit a canonical JSON or human snapshot.
        snapshot = _make_infrastructure_snapshot("supervisor", err)
        _emit_snapshot(snapshot, options)
        return 3
    except BaseException as err:
        # Third-party checks may raise any Exception subclass; non-runtime sentinels remain visible.
        if not isinstance(err, (Exception, SystemExit)):
            raise
        snapshot = _make_infrastructure_snapshot("supervisor", err)
        _emit_snapshot(snapshot, options)
        return 3

    if options.report:
        report_error = write_report(options.report, snapshot)
        if report_error is not None:
            synthetic_id = "selfcheck.report_write"
            ledger.reserve((CheckSpec(synthetic_id, "synthetic"),))
            ledger.commit(
                CheckResult(
                    synthetic_id,
                    "ERROR",
                    True,
                    summary="report write failed",
                    details=report_error,
                    reason="report_write",
                )
            )
            metadata["report_error"] = report_error
            snapshot = ledger.freeze(metadata)

    if not _emit_snapshot(snapshot, options):
        return 1
    return _exit_code(snapshot, options.fail_on_warn)

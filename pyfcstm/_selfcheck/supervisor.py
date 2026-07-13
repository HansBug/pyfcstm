"""Supervisor orchestration for the standard-library self-check command."""

import json
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
    """Return a pre-ledger snapshot for argument/bootstrap failures.

    This path is intentionally separate from :func:`_finalize_infrastructure`,
    which must preserve a populated ledger after checks have been reserved.
    """
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


def _append_synthetic(
    ledger: Ledger,
    check_id: str,
    summary: str,
    details: str,
    reason: str,
) -> None:
    """Append one synthetic terminal diagnostic without replacing the ledger."""
    if ledger.get_state(check_id) is None:
        ledger.reserve((CheckSpec(check_id, "synthetic"),))
    if not ledger.has_result(check_id):
        ledger.commit(
            CheckResult(
                check_id,
                "ERROR",
                True,
                summary=summary,
                details=details,
                reason=reason,
            )
        )


def _fallback_json(snapshot) -> str:
    """Serialize a snapshot without calling the primary renderer again."""
    return json.dumps(
        snapshot.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def _fallback_human(snapshot) -> str:
    """Render a minimal human report when the configured renderer is broken."""
    lines = ["pyfcstm self-check", "=================="]
    for result in snapshot.checks:
        lines.append("{} {}: {}".format(result.status, result.check_id, result.summary))
        if result.status not in ("PASS", "WARN", "SKIP") and result.details:
            lines.append(result.details)
    lines.append("Counts: {}".format(json.dumps(dict(snapshot.counts), sort_keys=True)))
    return "\n".join(lines) + "\n"


def _finalize_infrastructure(
    ledger: Ledger, specs, metadata, phase: str, error: BaseException
):
    """Finalize reserved checks before adding one infrastructure diagnostic."""
    details = "{}: {}\n{}".format(phase, error, traceback.format_exc())
    for spec in specs:
        state = ledger.get_state(spec.check_id)
        if state is None:
            ledger.ensure_reserved(spec)
            state = ledger.get_state(spec.check_id)
        if state is None or ledger.has_result(spec.check_id):
            continue
        status = "ERROR" if state == "RUNNING" else "BLOCKED"
        ledger.commit(
            CheckResult(
                spec.check_id,
                status,
                spec.required,
                summary="self-check infrastructure error",
                details=details,
                reason="supervisor_infrastructure",
            )
        )
    _append_synthetic(
        ledger,
        "selfcheck.infrastructure",
        "self-check infrastructure error",
        details,
        "infrastructure_error",
    )
    metadata = dict(metadata)
    metadata["phase"] = phase
    metadata["finished_at"] = time.time()
    return ledger.freeze(metadata)


def _emit_snapshot(snapshot, options, ledger=None, metadata=None) -> bool:
    """Render one snapshot and retain a machine-readable fallback on failure."""
    snapshot, output, rendered = _render_snapshot(
        snapshot, options, ledger=ledger, metadata=metadata
    )
    del snapshot
    if output is None:
        return False
    print(output, end="")
    return rendered


def _render_snapshot(snapshot, options, ledger=None, metadata=None):
    """Prepare output while returning the final ledger-backed snapshot."""
    try:
        output = (
            render_json(snapshot)
            if options.output_format == "json"
            else render_human(snapshot, options.color)
        )
        return snapshot, output, True
    except BaseException as err:
        if not isinstance(err, (Exception, SystemExit)):
            raise
        details = "{}: {}\n{}".format(type(err).__name__, err, traceback.format_exc())
        if ledger is not None:
            _append_synthetic(
                ledger,
                "selfcheck.render",
                "self-check renderer failed",
                details,
                "render_error",
            )
            final_metadata = dict(metadata or snapshot.metadata)
            final_metadata["finished_at"] = time.time()
            snapshot = ledger.freeze(final_metadata)
        try:
            output = (
                _fallback_json(snapshot)
                if options.output_format == "json"
                else _fallback_human(snapshot)
            )
            return snapshot, output, False
        except BaseException as fallback_error:
            if not isinstance(fallback_error, (Exception, SystemExit)):
                raise
            emergency_write(
                "self-check render error: {}\n".format(fallback_error),
                options.output_format,
            )
        return snapshot, None, False


def _emit_argument_error(arguments: Sequence[str], error: BaseException) -> None:
    """Emit argument failures through the requested human or JSON channel."""
    output_format = "human"
    for index, argument in enumerate(arguments):
        if argument == "--format=json" or (
            argument == "--format"
            and index + 1 < len(arguments)
            and arguments[index + 1] == "json"
        ):
            output_format = "json"
            break
        if argument == "--format" and (
            index + 1 == len(arguments) or arguments[index + 1].startswith("--")
        ):
            output_format = "json"
            break
    if output_format == "json":
        snapshot = _make_infrastructure_snapshot("arguments", error)
        try:
            print(render_json(snapshot))
        except BaseException as render_error:
            if not isinstance(render_error, (Exception, SystemExit)):
                raise
            print(_fallback_json(snapshot))
    else:
        emergency_write("self-check argument error: {}\n".format(error), output_format)


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
        _emit_argument_error(arguments, err)
        return 2

    started = time.time()
    ledger = Ledger()
    specs = ()
    metadata = {
        "session_id": uuid.uuid4().hex,
        "profile": options.profile,
        "timeout_scale": options.timeout_scale,
        "registry_coverage": 1,
        "started_at": started,
    }
    try:
        specs = selected_specs(options.profile)
        ledger.reserve(specs)
        metadata["environment"] = collect_environment(options.redact)
        global_deadline = time.monotonic() + _PROFILE_DEADLINES[options.profile] * (
            options.timeout_scale
        )
        metadata["global_deadline_seconds"] = _PROFILE_DEADLINES[options.profile] * (
            options.timeout_scale
        )
        unresolved = list(specs)
        while unresolved:
            progressed = False
            deferred = []
            for spec in unresolved:
                prerequisite_results = [
                    ledger.get_result(item) for item in spec.prerequisites
                ]
                if any(result is None for result in prerequisite_results):
                    deferred.append(spec)
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
                    progressed = True
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
                    progressed = True
                    continue
                ledger.mark_running(spec.check_id)
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
                ledger.commit(result)
                progressed = True
            if not progressed:
                for spec in deferred:
                    ledger.commit(
                        CheckResult(
                            spec.check_id,
                            "BLOCKED",
                            spec.required,
                            summary="prerequisite was never resolved",
                            reason="prerequisite_unresolved",
                        )
                    )
                unresolved = []
            else:
                unresolved = deferred
        metadata["finished_at"] = time.time()
        snapshot = ledger.freeze(metadata)
    except KeyboardInterrupt:
        for spec in specs:
            if ledger.get_state(spec.check_id) is None:
                ledger.ensure_reserved(spec)
            if not ledger.has_result(spec.check_id):
                status = (
                    "CRASH"
                    if ledger.get_state(spec.check_id) == "RUNNING"
                    else "BLOCKED"
                )
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
            interrupted_metadata = dict(metadata)
            interrupted_metadata["interrupted"] = True
            interrupted_metadata["finished_at"] = time.time()
            snapshot = ledger.freeze(interrupted_metadata)
            _emit_snapshot(
                snapshot,
                options,
                ledger=ledger,
                metadata=interrupted_metadata,
            )
        except BaseException as report_error:
            if not isinstance(report_error, (Exception, SystemExit)):
                raise
            emergency_write(
                "self-check interrupted before report completion: {}\n".format(
                    report_error
                ),
                options.output_format,
            )
        return 130
    except _EXPECTED_INFRA_ERRORS as err:
        # Setup/snapshot failures still emit a canonical JSON or human snapshot.
        snapshot = _finalize_infrastructure(ledger, specs, metadata, "supervisor", err)
        _emit_snapshot(snapshot, options)
        return 3
    except BaseException as err:
        # Third-party checks may raise any Exception subclass; non-runtime sentinels remain visible.
        if not isinstance(err, (Exception, SystemExit)):
            raise
        snapshot = _finalize_infrastructure(ledger, specs, metadata, "supervisor", err)
        _emit_snapshot(snapshot, options)
        return 3

    try:
        output = None
        if options.report:
            # Render first so renderer diagnostics enter the ledger before the
            # report is serialized; both channels then use one final snapshot.
            snapshot, output, _ = _render_snapshot(
                snapshot, options, ledger=ledger, metadata=metadata
            )
            try:
                report_error = write_report(options.report, snapshot)
            except BaseException as error:
                if isinstance(error, (KeyboardInterrupt, SystemExit)):
                    raise
                if not isinstance(error, Exception):
                    raise
                report_error = "{}: {}\n{}".format(
                    type(error).__name__, error, traceback.format_exc()
                )
            if report_error is not None:
                _append_synthetic(
                    ledger,
                    "selfcheck.report_write",
                    "report write failed",
                    report_error,
                    "report_write",
                )
                metadata["report_error"] = report_error
                snapshot = ledger.freeze(metadata)
                snapshot, output, _ = _render_snapshot(
                    snapshot, options, ledger=ledger, metadata=metadata
                )
        else:
            snapshot, output, _ = _render_snapshot(
                snapshot, options, ledger=ledger, metadata=metadata
            )

        if output is None:
            return 1
        print(output, end="")
    except KeyboardInterrupt:
        interrupted_metadata = dict(metadata)
        interrupted_metadata["interrupted"] = True
        interrupted_metadata["finished_at"] = time.time()
        snapshot = ledger.freeze(interrupted_metadata)
        _emit_snapshot(snapshot, options, ledger=ledger, metadata=interrupted_metadata)
        return 130
    except BaseException as error:
        if not isinstance(error, (Exception, SystemExit)):
            raise
        _append_synthetic(
            ledger,
            "selfcheck.finalization",
            "self-check finalization failed",
            "{}: {}\n{}".format(type(error).__name__, error, traceback.format_exc()),
            "finalization_error",
        )
        metadata["finished_at"] = time.time()
        snapshot = ledger.freeze(metadata)
        _emit_snapshot(snapshot, options, ledger=ledger, metadata=metadata)
        return 3
    return _exit_code(snapshot, options.fail_on_warn)

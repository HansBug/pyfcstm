"""Execute one isolated check synchronously under the supervisor.

The caller starts one worker, exchanges the fixed gate through one
``subprocess.communicate`` call, commits its terminal result, and only then can
advance to the next registry entry. Worker output is spooled to temporary files
and fed to a bounded capture after process completion. POSIX workers also
receive an operating-system file-size limit so a runaway stream is stopped at
the physical boundary. This module does not create threads or schedule checks
concurrently.
"""

import errno
import os
import signal
import subprocess
import sys
import tempfile
import time
from typing import Optional

from ._win32 import JobAssignmentError, attach_process, format_ntstatus
from .model import ArtifactContext, CheckResult, CheckSpec
from .arguments import _WORKER_DISPATCH_ARGUMENT
from .protocol import build_start_gate
from .protocol import FRAME_PREFIX
from .protocol import MAX_ENVELOPE_BYTES
from .protocol import make_nonce
from .protocol import read_result_file
from .protocol import read_stdout_frames


STREAM_LIMIT = 2 * 1024 * 1024
SPOOL_LIMIT = 8 * 1024 * 1024
SIGTERM_GRACE = 0.5
MAX_PROTOCOL_FRAMES = 2
_CAPTURE_CHUNK_SIZE = 64 * 1024
_PATH_SEPARATOR = os.pathsep
_ISOLATED_ENV = (
    "PYTHONPATH",
    "PYTHONHOME",
    "PYTHONSTARTUP",
    "PYTHONUSERBASE",
    "PYTHONPYCACHEPREFIX",
    "PYTHONMALLOC",
    "PYTHONFAULTHANDLER",
    "PYTHONIOENCODING",
    "PYTHONUTF8",
    "PYTHONLEGACYWINDOWSSTDIO",
    "PYTHONLEGACYWINDOWSFSENCODING",
    "PYTHONINSPECT",
    "PYTHONWARNINGS",
)


def _limit_worker_output_files() -> None:
    """Apply the physical output quota inside a POSIX worker process.

    The parent turns a setup failure into a structured child result before any
    registered callback can run.
    """
    try:
        import resource

        _, hard_limit = resource.getrlimit(resource.RLIMIT_FSIZE)
        limit = SPOOL_LIMIT if hard_limit < 0 else min(SPOOL_LIMIT, hard_limit)
        resource.setrlimit(resource.RLIMIT_FSIZE, (limit, limit))
    except (AttributeError, ImportError, OSError, ValueError):
        # A worker without an enforceable quota must fail closed before its
        # callback can emit unbounded output.
        os._exit(127)


def _output_limit_signal(return_code: Optional[int]) -> bool:
    """Return whether a POSIX worker was killed by its file-size quota."""
    signal_number = getattr(signal, "SIGXFSZ", None)
    return signal_number is not None and return_code == -signal_number


def _should_limit_worker_output() -> bool:
    """Return whether the parent may impose ``RLIMIT_FSIZE`` on a worker.

    A frozen PyInstaller executable is itself the bootloader process.  Its
    child must be allowed to extract the bundled archive before Python starts;
    the worker-side ``_OutputBudget`` still bounds stdout/stderr after startup.
    """
    return os.name == "posix" and not getattr(sys, "frozen", False)


class _BoundedCapture:
    """Keep bounded head/tail bytes from one pipe."""

    def __init__(self, limit: int = STREAM_LIMIT, capture_protocol: bool = False):
        self.limit = limit
        self.head = bytearray()
        self.tail = bytearray()
        self._complete = bytearray()
        self.total = 0
        self.capture_protocol = capture_protocol
        self._protocol_pending = bytearray()
        self.protocol_frames = []

    def _append_business(self, data: bytes) -> None:
        previous_total = self.total
        self.total += len(data)
        remaining = self.limit // 2
        if self._complete is not None:
            if previous_total < self.limit:
                self._complete.extend(data[: self.limit - previous_total])
            if self.total > self.limit:
                self._complete = None
        if len(self.head) < remaining:
            self.head.extend(data[: remaining - len(self.head)])
        self.tail.extend(data)
        if len(self.tail) > remaining:
            del self.tail[: len(self.tail) - remaining]

    def append(self, data: bytes) -> None:
        """Append business output and independently extract protocol frames."""
        if not self.capture_protocol:
            self._append_business(data)
            return
        self._protocol_pending.extend(data)
        self._extract_protocol_frames()

    def _extract_protocol_frames(self) -> None:
        """Extract frames even when business output has no preceding newline."""
        while True:
            start = self._protocol_pending.find(FRAME_PREFIX)
            if start < 0:
                keep = max(0, len(FRAME_PREFIX) - 1)
                if len(self._protocol_pending) > keep:
                    self._append_business(bytes(self._protocol_pending[:-keep]))
                    del self._protocol_pending[:-keep]
                return
            if start:
                self._append_business(bytes(self._protocol_pending[:start]))
                del self._protocol_pending[:start]
            newline = self._protocol_pending.find(b"\x0a", len(FRAME_PREFIX))
            if newline < 0:
                if len(self._protocol_pending) > MAX_ENVELOPE_BYTES + 1:
                    frame = bytes(self._protocol_pending[: MAX_ENVELOPE_BYTES + 1])
                    if len(self.protocol_frames) < MAX_PROTOCOL_FRAMES:
                        self.protocol_frames.append(frame)
                    del self._protocol_pending[: MAX_ENVELOPE_BYTES + 1]
                return
            frame = bytes(self._protocol_pending[: newline + 1])
            del self._protocol_pending[: newline + 1]
            if len(self.protocol_frames) < MAX_PROTOCOL_FRAMES:
                self.protocol_frames.append(frame[: MAX_ENVELOPE_BYTES + 1])

    def finish(self) -> None:
        """Flush incomplete protocol candidates after the pipe reaches EOF."""
        if not self.capture_protocol or not self._protocol_pending:
            return
        self._extract_protocol_frames()
        start = self._protocol_pending.find(FRAME_PREFIX)
        if start < 0:
            self._append_business(bytes(self._protocol_pending))
        # ``_extract_protocol_frames`` removes business bytes before every
        # protocol prefix, so a remaining candidate is either absent or starts
        # at offset zero.
        if start >= 0 and len(self.protocol_frames) < MAX_PROTOCOL_FRAMES:
            self.protocol_frames.append(
                bytes(self._protocol_pending[start : start + MAX_ENVELOPE_BYTES + 1])
            )
        self._protocol_pending.clear()

    def text(self) -> str:
        """Decode captured bytes without allowing invalid output to crash reporting."""
        return self.raw().decode("utf-8", "backslashreplace")

    def raw(self) -> bytes:
        """Return bounded bytes without duplicating short streams."""
        if self.total <= self.limit:
            return bytes(self._complete)
        marker = b"\n...[truncated]...\n"
        if self.limit <= len(marker):
            return marker[: self.limit]
        payload_limit = self.limit - len(marker)
        head_limit = min(len(self.head), payload_limit // 2)
        tail_limit = payload_limit - head_limit
        return bytes(self.head[:head_limit] + marker + self.tail[-tail_limit:])

    def protocol_bytes(self) -> bytes:
        """Return protocol-prefixed lines independently of business-output capture."""
        return b"".join(self.protocol_frames)

    @property
    def truncated_bytes(self) -> int:
        return max(0, self.total - self.limit)

    def mark_overflow(self, overflow_bytes: int = 1) -> None:
        """Record bytes discarded by an external physical quota."""
        self.total = max(self.total, self.limit + max(1, int(overflow_bytes)))


def _capture_stream(stream, data, capture_protocol: bool) -> _BoundedCapture:
    """Build a bounded capture from a spool or an already returned byte string."""
    capture = _BoundedCapture(capture_protocol=capture_protocol)
    if data is not None:
        capture.append(data or b"")
    elif stream is not None:
        try:
            stream.seek(0)
            while True:
                chunk = stream.read(_CAPTURE_CHUNK_SIZE)
                if not chunk:
                    break
                capture.append(chunk)
        except (OSError, ValueError) as err:
            capture.append(
                ("self-check output read failed: {}".format(err)).encode(
                    "utf-8", "backslashreplace"
                )
            )
    capture.finish()
    return capture


def _close_capture_stream(stream) -> None:
    """Close one optional parent-owned output spool without escaping cleanup."""
    if stream is None:
        return
    try:
        stream.close()
    except (OSError, ValueError):
        # The subprocess module may already have closed an inherited handle.
        pass


def _diagnostics(
    stream_errors, base: str = "", cleanup_error: Optional[str] = None
) -> str:
    """Combine semantic, stream-read, and cleanup diagnostics in stable order."""
    parts = [base] if base else []
    parts.extend(stream_errors)
    if cleanup_error:
        parts.append("cleanup=" + cleanup_error)
    return "\n".join(parts)


def _record_error(errors, label: str, error: BaseException) -> None:
    """Append one compact cleanup diagnostic."""
    errors.append("{}:{}".format(label, type(error).__name__))


def _wait_process(process, grace: float, errors, kill_on_timeout: bool) -> None:
    """Wait once and optionally hard-kill an unsettled process."""
    try:
        process.wait(timeout=grace)
        return
    except subprocess.TimeoutExpired:
        if not kill_on_timeout:
            return
    except (OSError, ChildProcessError, ValueError) as err:
        # Popen wait can fail after native cleanup has already reaped the child.
        _record_error(errors, "process_wait", err)
        return
    try:
        process.kill()
    except (OSError, ValueError) as err:
        # The process may disappear between the timeout and hard-kill call.
        _record_error(errors, "process_kill", err)
    try:
        process.wait(timeout=grace)
    except (OSError, subprocess.TimeoutExpired, ChildProcessError, ValueError) as err:
        # A failed reap remains visible but must not block report completion.
        _record_error(errors, "process_wait", err)


def _wait_for_group_exit(pid: int, grace: float, errors) -> None:
    """Wait briefly for a killed POSIX process group to disappear."""
    deadline = time.monotonic() + max(0.1, grace)
    while True:
        try:
            os.killpg(pid, 0)
        except ProcessLookupError:
            return
        except OSError as err:
            # Permission or platform errors make group state unobservable.
            _record_error(errors, "group_probe", err)
            return
        remaining = deadline - time.monotonic()
        if remaining <= 0.0:
            _record_error(
                errors, "group_wait", subprocess.TimeoutExpired("process-group", grace)
            )
            return
        time.sleep(min(0.01, remaining))


def _finish_job(job, process, grace: float, terminate: bool) -> Optional[str]:
    """Finish one Windows Job Object with explicit Win7 termination fallback."""
    errors = []
    if terminate:
        try:
            job.terminate(1)
        except (JobAssignmentError, OSError, ValueError) as err:
            # Native job termination can fail in restricted/nested job setups.
            _record_error(errors, "job_terminate", err)
            try:
                process.terminate()
            except (OSError, ValueError) as fallback_err:
                # Direct termination is the last available leader fallback.
                _record_error(errors, "process_terminate", fallback_err)
    _wait_process(process, grace, errors, kill_on_timeout=terminate)
    try:
        job.close()
    except (OSError, ValueError) as err:
        # Handle-close failures are diagnostic after termination was attempted.
        _record_error(errors, "job_close", err)
    return "; ".join(errors) if errors else None


def _terminate(
    process, job, posix_group: bool, grace: float = SIGTERM_GRACE
) -> Optional[str]:
    """Terminate one worker tree and return cleanup diagnostics."""
    if job is not None:
        return _finish_job(job, process, grace, terminate=True)
    errors = []
    if posix_group:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError as err:
            # The group may already have exited before graceful termination.
            _record_error(errors, "sigterm", err)
        _wait_process(process, grace, errors, kill_on_timeout=False)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as err:
            # Non-ESRCH kill failures leave explicit cleanup evidence.
            _record_error(errors, "sigkill", err)
        else:
            _wait_for_group_exit(process.pid, grace, errors)
        _wait_process(process, grace, errors, kill_on_timeout=False)
    else:
        try:
            process.terminate()
        except (OSError, ValueError) as err:
            # The process may already be gone when direct termination begins.
            _record_error(errors, "process_terminate", err)
        _wait_process(process, grace, errors, kill_on_timeout=True)
    return "; ".join(errors) if errors else None


def _command_for_worker(
    check: CheckSpec,
    nonce: str,
    result_mode: str,
    result_file: Optional[str],
):
    import sys

    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command.extend(["-m", "pyfcstm"])
    command.extend(
        [
            _WORKER_DISPATCH_ARGUMENT,
            "--check-id",
            check.check_id,
            "--worker-key",
            check.worker_key,
            "--nonce",
            nonce,
            "--result-mode",
            result_mode,
        ]
    )
    if result_file is not None:
        command.extend(["--result-file", result_file])
    return command


def _artifact_environment(context: ArtifactContext) -> dict:
    """Build a sanitized environment for one artifact worker."""
    environment = {}
    for name in ("PATH", "SystemRoot", "TEMP", "TMP", "COMSPEC"):
        value = os.environ.get(name)
        if value:
            environment[name] = value
    for name in _ISOLATED_ENV:
        environment.pop(name, None)
    environment["PYTHONNOUSERSITE"] = "1"
    environment["PYTHONDONTWRITEBYTECODE"] = "1"
    environment["PYFCSTM_SELFCHECK_ARTIFACT_KIND"] = context.kind
    environment["PYFCSTM_SELFCHECK_ARTIFACT_ROOT"] = context.root
    environment["PYFCSTM_SELFCHECK_ALLOWED_ROOTS"] = _PATH_SEPARATOR.join(
        context.allowed_roots
    )
    environment["PYFCSTM_SELFCHECK_ALLOW_SITE_PACKAGES"] = (
        "1" if context.allow_site_packages else "0"
    )
    return environment


def _set_network_environment(environment: dict, enabled: bool) -> None:
    """Pass the explicit network opt-in to isolated callbacks."""
    environment["PYFCSTM_SELFCHECK_NETWORK"] = "1" if enabled else "0"


def _spool_size(stream) -> Optional[int]:
    """Return one spool's physical size without making cleanup fatal."""
    if stream is None:
        return None
    try:
        return int(os.fstat(stream.fileno()).st_size)
    except (AttributeError, OSError, ValueError):
        return None


def _cleanup_session(session_dir: Optional[str], result_file: Optional[str]) -> None:
    """Remove worker transport files before deleting the private session directory."""
    errors = []
    if result_file is not None:
        try:
            os.unlink(result_file)
        except OSError as err:
            if err.errno != errno.ENOENT:
                errors.append("result_unlink:{}".format(type(err).__name__))
    if session_dir is not None:
        try:
            os.rmdir(session_dir)
        except OSError as err:
            errors.append("session_rmdir:{}".format(type(err).__name__))
    if errors:
        _write_cleanup_diagnostic("transport cleanup", "; ".join(errors))


def _write_cleanup_diagnostic(label: str, error: Optional[str]) -> None:
    """Write last-resort cleanup evidence without replacing the check result."""
    if not error:
        return
    try:
        os.write(
            2,
            ("self-check {}: {}\n".format(label, error)).encode(
                "ascii", "backslashreplace"
            ),
        )
    except OSError:
        # The structured result remains authoritative if raw stderr is unavailable.
        pass


def _make_result(
    check: CheckSpec,
    status: str,
    summary: str,
    reason: Optional[str],
    started: float,
    evidence: str = "",
    process=None,
    return_code: Optional[int] = None,
    result_mode: Optional[str] = None,
    stdout_capture: Optional[_BoundedCapture] = None,
    stderr_capture: Optional[_BoundedCapture] = None,
    timeout: bool = False,
    ntstatus: Optional[str] = None,
    envelope=None,
) -> CheckResult:
    """Build one terminal result from semantic and process observations."""
    stdout = stdout_capture.text() if stdout_capture is not None else ""
    stderr = stderr_capture.text() if stderr_capture is not None else ""
    truncated = sum(
        capture.truncated_bytes
        for capture in (stdout_capture, stderr_capture)
        if capture is not None
    )
    envelope = envelope or {}
    return CheckResult(
        check.check_id,
        status,
        check.required,
        summary=summary,
        title=check.title,
        prerequisites=check.prerequisites,
        reason=reason,
        expected=envelope.get("expected"),
        observed=envelope.get("observed"),
        evidence=evidence,
        remediation=envelope.get("remediation"),
        exception=envelope.get("exception"),
        return_code=return_code,
        transport=result_mode,
        truncated_bytes=truncated,
        duration_ms=(time.monotonic() - started) * 1000,
        pid=getattr(process, "pid", None),
        signal=-return_code if return_code is not None and return_code < 0 else None,
        ntstatus=ntstatus,
        stdout=stdout,
        stderr=stderr,
        timeout=timeout,
    )


def run_check_process(
    check: CheckSpec,
    timeout: float,
    timeout_scale: float = 1.0,
    artifact_context: Optional[ArtifactContext] = None,
    network: bool = False,
) -> CheckResult:
    """
    Run one check in a fresh process and classify its terminal result.

    :param check: Registered check specification.
    :type check: CheckSpec
    :param timeout: Monotonic deadline in seconds.
    :type timeout: float
    :param timeout_scale: Multiplier for start-gate and termination grace,
        defaults to ``1.0``.
    :type timeout_scale: float, optional
    :param artifact_context: Optional import/filesystem boundary for artifact
        checks, defaults to ``None``.
    :type artifact_context: ArtifactContext, optional
    :param network: Whether the caller explicitly enabled network probes,
        defaults to ``False``.
    :type network: bool, optional
    :return: A terminal result, including bounded process diagnostics.
    :rtype: CheckResult

    Example::

        >>> run_check_process(CheckSpec("artifact.self_dispatch", "self_dispatch"), 10.0).status
        'PASS'
    """
    started = time.monotonic()
    nonce = make_nonce()
    scaled_grace = min(5.0, max(0.1, SIGTERM_GRACE * timeout_scale))
    session_dir = None
    result_file = None
    result_mode = "file"
    try:
        session_dir = tempfile.mkdtemp(prefix="pyfcstm-selfcheck-")
        result_file = os.path.join(session_dir, "result.log")
        with open(result_file, "wb"):
            pass
    except (OSError, IOError):
        result_mode = "stdout"
        result_file = None

    command = _command_for_worker(check, nonce, result_mode, result_file)
    child_environment = (
        _artifact_environment(artifact_context)
        if artifact_context is not None
        else os.environ.copy()
    )
    child_environment["PYFCSTM_SELFCHECK_WORKER_PROCESS"] = "1"
    _set_network_environment(child_environment, network)
    stdout_spool = None
    stderr_spool = None
    spool_error = None
    try:
        stdout_spool = tempfile.TemporaryFile(mode="w+b")
        stderr_spool = tempfile.TemporaryFile(mode="w+b")
    except (OSError, ValueError) as err:
        spool_error = err
        _close_capture_stream(stdout_spool)
        _close_capture_stream(stderr_spool)
        stdout_spool = None
        stderr_spool = None
    if spool_error is not None:
        _cleanup_session(session_dir, result_file)
        return _make_result(
            check,
            "ERROR",
            "worker output capture is unavailable",
            "output_capture_limit",
            started,
            evidence="temporary output spool initialization failed: {}: {}".format(
                type(spool_error).__name__, spool_error
            ),
        )
    popen_kwargs = {
        "stdin": subprocess.PIPE,
        "stdout": stdout_spool or subprocess.PIPE,
        "stderr": stderr_spool or subprocess.PIPE,
        "bufsize": 0,
        "env": child_environment,
    }
    package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    package_parent = os.path.dirname(package_dir)
    if artifact_context is None:
        # Put the package under test first while preserving caller-provided
        # import roots for worker callbacks and installation diagnostics.
        inherited_pythonpath = child_environment.get("PYTHONPATH")
        child_environment["PYTHONPATH"] = _PATH_SEPARATOR.join(
            path for path in (package_parent, inherited_pythonpath) if path
        )
        popen_kwargs["cwd"] = session_dir or package_dir
    else:
        popen_kwargs["cwd"] = artifact_context.root
        if not artifact_context.allow_site_packages and not getattr(sys, "frozen", False):
            # ``-E``/``-s`` are Python interpreter switches; passing them to a
            # PyInstaller executable turns them into application arguments and
            # prevents its hidden worker dispatch from starting.
            command.insert(1, "-s")
            command.insert(1, "-E")
    posix_group = os.name == "posix"
    if posix_group:
        popen_kwargs["start_new_session"] = True
        # Non-frozen interpreters can enforce the quota before any callback or
        # descendant starts.  Frozen bootloaders defer the same limit until the
        # worker has completed archive extraction (see ``worker.py``).
        if not getattr(sys, "frozen", False):
            popen_kwargs["preexec_fn"] = _limit_worker_output_files
    elif os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    try:
        process = subprocess.Popen(command, **popen_kwargs)
    except (OSError, ValueError) as err:
        _close_capture_stream(stdout_spool)
        _close_capture_stream(stderr_spool)
        _cleanup_session(session_dir, result_file)
        return _make_result(
            check,
            "ERROR",
            "worker spawn failed",
            "spawn_failed",
            started,
            evidence=str(err),
        )

    job = None
    try:
        if os.name == "nt":
            try:
                job = attach_process(process)
            except BaseException as err:
                # Any ordinary native setup failure must clean the already-spawned
                # worker; control sentinels are cleaned and then re-raised.
                cleanup_error = _terminate(process, None, False, scaled_grace)
                if isinstance(err, (KeyboardInterrupt, SystemExit)):
                    raise
                if not isinstance(err, Exception):
                    raise
                details = str(err)
                if cleanup_error:
                    details += "; cleanup=" + cleanup_error
                return _make_result(
                    check,
                    "ERROR",
                    "worker isolation unavailable",
                    "isolation_unavailable",
                    started,
                    evidence=details,
                    process=process,
                )

        stdout_data = None if stdout_spool is not None else b""
        stderr_data = None if stderr_spool is not None else b""
        communication_errors = []
        cleanup_error = None
        timed_out = False
        monitored_limit = False
        deadline = started + timeout
        if (
            stdout_spool is not None
            and stderr_spool is not None
            and getattr(process, "stdin", None) is not None
            and callable(getattr(process, "poll", None))
        ):
            # File-backed workers have no pipe-drain hazard.  Send the gate once,
            # then poll the two files so Windows/frozen workers are bounded even
            # when native code writes directly to inherited stdout/stderr.
            try:
                process.stdin.write(build_start_gate(nonce))
                process.stdin.flush()
                process.stdin.close()
            except (AttributeError, OSError, ValueError) as err:
                cleanup_error = _terminate(process, job, posix_group, scaled_grace)
                job = None
                details = "worker_communication:{}".format(type(err).__name__)
                if cleanup_error:
                    details += "; cleanup=" + cleanup_error
                return _make_result(
                    check,
                    "ERROR",
                    "worker communication failed",
                    "worker_communication",
                    started,
                    evidence=details,
                    process=process,
                    result_mode=result_mode,
                )
            while process.poll() is None:
                physical_output = (
                    _spool_size(stdout_spool),
                    _spool_size(stderr_spool),
                )
                if any(
                    size is not None and size >= SPOOL_LIMIT
                    for size in physical_output
                ):
                    monitored_limit = True
                    cleanup_error = _terminate(process, job, posix_group, scaled_grace)
                    job = None
                    break
                remaining = deadline - time.monotonic()
                if remaining <= 0.0:
                    timed_out = True
                    cleanup_error = _terminate(process, job, posix_group, scaled_grace)
                    job = None
                    break
                time.sleep(min(0.01, remaining))
            if process.poll() is None:
                _wait_process(process, scaled_grace, communication_errors, kill_on_timeout=True)
            stdout_data = stderr_data = None
        else:
            try:
                stdout_data, stderr_data = process.communicate(
                    input=build_start_gate(nonce),
                    timeout=max(0.0, deadline - time.monotonic()),
                )
            except subprocess.TimeoutExpired as err:
                timed_out = True
                stdout_data = err.output if stdout_spool is None else None
                stderr_data = err.stderr if stderr_spool is None else None
                cleanup_error = _terminate(process, job, posix_group, scaled_grace)
                job = None
                try:
                    stdout_data, stderr_data = process.communicate(timeout=scaled_grace)
                except subprocess.TimeoutExpired as drain_error:
                    communication_errors.append("output_drain:TimeoutExpired")
                    if stdout_spool is None:
                        stdout_data = drain_error.output or stdout_data
                    if stderr_spool is None:
                        stderr_data = drain_error.stderr or stderr_data
                except (OSError, ValueError) as drain_error:
                    # Pipe reads can fail with OSError after tree termination;
                    # communicate rejects already-closed streams with ValueError.
                    communication_errors.append(
                        "output_drain:{}".format(type(drain_error).__name__)
                    )
            except (OSError, ValueError) as err:
                # communicate surfaces native pipe failures as OSError and invalid
                # stream lifecycle state as ValueError.
                cleanup_error = _terminate(process, job, posix_group, scaled_grace)
                job = None
                details = "worker_communication:{}".format(type(err).__name__)
                if cleanup_error:
                    details += "; cleanup=" + cleanup_error
                return _make_result(
                    check,
                    "ERROR",
                    "worker communication failed",
                    "worker_communication",
                    started,
                    evidence=details,
                    process=process,
                    result_mode=result_mode,
                )

        stdout_capture = _capture_stream(
            stdout_spool, stdout_data, capture_protocol=result_mode == "stdout"
        )
        stderr_capture = _capture_stream(
            stderr_spool, stderr_data, capture_protocol=False
        )
        process_fields = {
            "process": process,
            "result_mode": result_mode,
            "stdout_capture": stdout_capture,
            "stderr_capture": stderr_capture,
        }
        return_code = process.returncode
        physical_output = {
            "stdout": _spool_size(stdout_spool),
            "stderr": _spool_size(stderr_spool),
        }
        oversized = {
            name: size
            for name, size in physical_output.items()
            if size is not None and size >= SPOOL_LIMIT
        }
        quota_signal = _output_limit_signal(return_code)
        if monitored_limit or quota_signal or oversized:
            for name, capture in (
                ("stdout", stdout_capture),
                ("stderr", stderr_capture),
            ):
                size = physical_output.get(name)
                if size is not None and size >= SPOOL_LIMIT:
                    capture.mark_overflow(
                        max(1, size - SPOOL_LIMIT) if size > SPOOL_LIMIT else 1
                    )
            cleanup_error = _terminate(process, job, posix_group, scaled_grace)
            job = None
            details = _diagnostics(
                communication_errors,
                base="output capture physical limit exceeded: {} (limit={} bytes)".format(
                    oversized or {"signal": return_code}, SPOOL_LIMIT
                ),
                cleanup_error=cleanup_error,
            )
            process_fields["return_code"] = return_code
            return _make_result(
                check,
                "ERROR",
                "worker output capture limit exceeded",
                "output_capture_limit",
                started,
                evidence=details,
                **process_fields
            )
        if return_code and not timed_out:
            # A crashed/non-zero worker may have left descendants in its process
            # group even though the group leader has already exited.
            cleanup_error = _terminate(process, job, posix_group, scaled_grace)
            job = None
        process_fields["return_code"] = return_code
        if timed_out:
            details = _diagnostics(communication_errors, cleanup_error=cleanup_error)
            return _make_result(
                check,
                "TIMEOUT",
                "worker deadline exceeded",
                "worker_deadline_exceeded",
                started,
                evidence=details,
                timeout=True,
                **process_fields,
            )

        outcome = (
            read_result_file(result_file, nonce, check.check_id)
            if result_mode == "file"
            else read_stdout_frames(
                stdout_capture.protocol_bytes(), nonce, check.check_id
            )
        )
        if outcome.envelope is not None:
            details = _diagnostics(
                communication_errors,
                base=str(outcome.envelope.get("evidence", "")),
                cleanup_error=cleanup_error,
            )
            return _make_result(
                check,
                outcome.envelope["status"],
                str(outcome.envelope.get("summary", "")),
                outcome.envelope.get("reason"),
                started,
                evidence=details,
                envelope=outcome.envelope,
                **process_fields,
            )
        details = _diagnostics(communication_errors, cleanup_error=cleanup_error)
        ntstatus = format_ntstatus(return_code) if os.name == "nt" else None
        if ntstatus:
            details = (details + "\n" if details else "") + "ntstatus=" + ntstatus
        status = "ERROR"
        reason = outcome.error_code or "missing_result"
        if reason == "missing_result" and return_code:
            reason = (
                "worker_protocol_error"
                if return_code == 3
                else "worker_exit_without_envelope"
            )
            status = "ERROR" if return_code == 3 else "CRASH"
        return _make_result(
            check,
            status,
            "worker result unavailable",
            reason,
            started,
            evidence=details,
            ntstatus=ntstatus,
            **process_fields,
        )
    except BaseException as err:
        # Interrupts and unexpected callback/setup exceptions must not leave a
        # worker or descendant process alive after the parent unwinds.
        cleanup_error = _terminate(process, job, posix_group, scaled_grace)
        job = None
        _write_cleanup_diagnostic("interrupted cleanup", cleanup_error)
        if isinstance(err, (KeyboardInterrupt, SystemExit)):
            raise
        if not isinstance(err, Exception):
            raise
        raise
    finally:
        if job is not None:
            cleanup_error = _finish_job(job, process, scaled_grace, terminate=True)
            _write_cleanup_diagnostic("job cleanup", cleanup_error)
        _cleanup_session(session_dir, result_file)
        _close_capture_stream(stdout_spool)
        _close_capture_stream(stderr_spool)

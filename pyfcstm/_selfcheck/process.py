"""Fresh subprocess execution, bounded stream capture, and timeout cleanup."""

import errno
import os
import queue
import signal
import subprocess
import tempfile
import threading
import time
from typing import Optional

from ._win32 import JobAssignmentError
from ._win32 import attach_process
from .model import CheckResult, CheckSpec
from .protocol import build_start_gate
from .protocol import FRAME_PREFIX
from .protocol import MAX_ENVELOPE_BYTES
from .protocol import make_nonce
from .protocol import read_result_file
from .protocol import read_stdout_frames


STREAM_LIMIT = 2 * 1024 * 1024
START_GATE_TIMEOUT = 2.0
SIGTERM_GRACE = 0.5
MAX_PROTOCOL_FRAMES = 2


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
        if not self._protocol_pending:
            return
        start = self._protocol_pending.find(FRAME_PREFIX)
        if start < 0:
            self._append_business(bytes(self._protocol_pending))
        elif start:
            self._append_business(bytes(self._protocol_pending[:start]))
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
        return bytes(self.head + b"\n...[truncated]...\n" + self.tail)

    def protocol_bytes(self) -> bytes:
        """Return protocol-prefixed lines independently of business-output capture."""
        return b"".join(self.protocol_frames)

    @property
    def truncated_bytes(self) -> int:
        return max(0, self.total - self.limit)


def _drain(stream, capture: _BoundedCapture, events) -> None:
    """Drain one pipe in a dedicated thread, including Windows anonymous pipes."""
    try:
        while True:
            data = stream.read(65536)
            if not data:
                break
            capture.append(data)
    except (OSError, ValueError) as err:
        # Pipe closure and invalid stream handles are recorded, not propagated from a reader thread.
        events.put("stream_error:{}".format(type(err).__name__))
    finally:
        capture.finish()
        events.put("stream_done")


def _terminate(
    process, job, posix_group: bool, grace: float = SIGTERM_GRACE
) -> Optional[str]:
    """Terminate a worker and report cleanup diagnostics without raising."""
    errors = []

    def record(label, error):
        errors.append("{}:{}".format(label, type(error).__name__))

    def wait_for_group_exit(pid):
        """Wait briefly for SIGKILL to remove descendants after the leader exits."""
        deadline = time.monotonic() + max(0.1, grace)
        while True:
            try:
                os.killpg(pid, 0)
            except ProcessLookupError:
                return
            except OSError as err:
                record("group_probe", err)
                return
            remaining = deadline - time.monotonic()
            if remaining <= 0.0:
                record("group_wait", subprocess.TimeoutExpired("process-group", grace))
                return
            time.sleep(min(0.01, remaining))

    if job is not None:
        try:
            job.terminate(1)
        except (JobAssignmentError, OSError, ValueError) as err:
            record("job_terminate", err)
            try:
                process.terminate()
            except (OSError, ProcessLookupError, ValueError) as fallback_err:
                record("process_terminate", fallback_err)
        try:
            job.close()
        except (OSError, ValueError) as err:
            record("job_close", err)
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except (OSError, ProcessLookupError, ValueError) as err:
                record("process_kill", err)
            try:
                process.wait(timeout=grace)
            except (OSError, subprocess.TimeoutExpired, ChildProcessError) as err:
                record("process_wait", err)
        except (OSError, ChildProcessError, ValueError) as err:
            record("process_wait", err)
    elif posix_group:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except (OSError, ProcessLookupError) as err:
            record("sigterm", err)
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            pass
        except (OSError, ChildProcessError, ValueError) as err:
            record("process_wait", err)
        # The group can outlive its leader when a descendant ignores SIGTERM.
        # ProcessLookupError means the group has already disappeared and is safe.
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as err:
            record("sigkill", err)
        else:
            wait_for_group_exit(process.pid)
        try:
            process.wait(timeout=grace)
        except (
            OSError,
            subprocess.TimeoutExpired,
            ChildProcessError,
            ValueError,
        ) as err:
            record("process_wait", err)
    else:
        try:
            process.terminate()
        except (OSError, ProcessLookupError, ValueError) as err:
            record("process_terminate", err)
        try:
            process.wait(timeout=grace)
        except subprocess.TimeoutExpired:
            try:
                process.kill()
            except (OSError, ProcessLookupError, ValueError) as err:
                record("process_kill", err)
            try:
                process.wait(timeout=grace)
            except (OSError, subprocess.TimeoutExpired, ChildProcessError) as err:
                record("process_wait", err)
        except (OSError, ChildProcessError, ValueError) as err:
            record("process_wait", err)
    return "; ".join(errors) if errors else None


def _close_job(job) -> Optional[str]:
    """Terminate explicit-fallback jobs before releasing their native handle."""
    errors = []
    if not getattr(job, "kill_on_close", True):
        try:
            job.terminate(1)
        except (JobAssignmentError, OSError, ValueError) as err:
            errors.append("job_terminate:{}".format(type(err).__name__))
    try:
        job.close()
    except (OSError, ValueError) as err:
        errors.append("job_close:{}".format(type(err).__name__))
    return "; ".join(errors) if errors else None


def _send_start_gate(process, nonce: str, timeout: float):
    """Write and close the GO frame within a bounded cross-platform window."""
    outcome = queue.Queue(maxsize=1)

    def write_gate() -> None:
        error = None
        try:
            process.stdin.write(build_start_gate(nonce))
            process.stdin.flush()
        except (AttributeError, OSError, ValueError) as err:
            error = "start_gate_write:{}".format(type(err).__name__)
        finally:
            try:
                process.stdin.close()
            except (AttributeError, OSError, ValueError):
                pass
            outcome.put(error)

    writer = threading.Thread(
        target=write_gate, name="selfcheck-start-gate", daemon=True
    )
    writer.start()
    writer.join(timeout=max(0.0, timeout))
    if writer.is_alive():
        try:
            process.stdin.close()
        except (AttributeError, OSError, ValueError):
            # Closing the pipe is the only portable way to wake a blocked writer.
            pass
        # Do not spend a second full gate budget waiting for a broken stream.
        writer.join(timeout=0.0)
        return "start_gate_timeout", writer
    try:
        return outcome.get_nowait(), writer
    except queue.Empty:
        return "start_gate_missing_result", writer


def _command_for_worker(
    check: CheckSpec,
    nonce: str,
    result_mode: str,
    result_file: Optional[str],
    test_mode: Optional[str] = None,
):
    import sys

    command = [sys.executable]
    if not getattr(sys, "frozen", False):
        command.extend(["-m", "pyfcstm"])
    command.extend(
        [
            "--_pyfcstm-selfcheck-worker-v1",
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
    if test_mode is not None:
        command.extend(["--test-mode", test_mode])
    return command


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
        diagnostic = "self-check cleanup: {}\n".format("; ".join(errors)).encode(
            "utf-8", "backslashreplace"
        )
        try:
            os.write(2, diagnostic)
        except OSError:
            # The raw descriptor is the final diagnostic channel when normal stderr is unavailable.
            return


def run_check_process(
    check: CheckSpec,
    timeout: float,
    timeout_scale: float = 1.0,
    test_mode: Optional[str] = None,
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
    :param test_mode: Internal test-only worker fault mode, defaults to ``None``.
    :type test_mode: Optional[str], optional
    :return: A terminal result, including bounded process diagnostics.
    :rtype: CheckResult

    Example::

        >>> run_check_process(CheckSpec("artifact.self_dispatch", "self_dispatch"), 10.0).status
        'PASS'
    """
    started = time.monotonic()
    nonce = make_nonce()
    scaled_gate_timeout = min(START_GATE_TIMEOUT * timeout_scale, max(0.0, timeout))
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

    command = _command_for_worker(
        check, nonce, result_mode, result_file, test_mode=test_mode
    )
    child_environment = os.environ.copy()
    # Test fault injection is opt-in through this private function argument;
    # a stale caller environment must never change a normal release worker.
    child_environment.pop("PYFCSTM_SELFCHECK_TEST_MODE", None)
    popen_kwargs = {
        "stdin": subprocess.PIPE,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "bufsize": 0,
        "env": child_environment,
    }
    if test_mode is not None:
        child_environment["PYFCSTM_SELFCHECK_TEST_MODE"] = test_mode
    posix_group = os.name == "posix"
    if posix_group:
        popen_kwargs["start_new_session"] = True
    elif os.name == "nt":
        popen_kwargs["creationflags"] = getattr(
            subprocess, "CREATE_NEW_PROCESS_GROUP", 0
        )
    try:
        process = subprocess.Popen(command, **popen_kwargs)
    except (OSError, ValueError) as err:
        _cleanup_session(session_dir, result_file)
        return CheckResult(
            check.check_id,
            "ERROR",
            check.required,
            summary="worker spawn failed",
            details=str(err),
            reason="spawn_failed",
        )

    job = None
    job_cleaned = False
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
                return CheckResult(
                    check.check_id,
                    "ERROR",
                    check.required,
                    summary="worker isolation unavailable",
                    details=details,
                    reason="isolation_unavailable",
                )

        stdout_capture = _BoundedCapture(capture_protocol=result_mode == "stdout")
        stderr_capture = _BoundedCapture()
        events = queue.Queue()
        stdout_thread = threading.Thread(
            target=_drain, args=(process.stdout, stdout_capture, events), daemon=True
        )
        stderr_thread = threading.Thread(
            target=_drain, args=(process.stderr, stderr_capture, events), daemon=True
        )
        stdout_thread.start()
        stderr_thread.start()
        gate_error, gate_thread = _send_start_gate(process, nonce, scaled_gate_timeout)
        if gate_error is not None:
            cleanup_error = _terminate(process, job, posix_group, scaled_grace)
            job_cleaned = job is not None
            gate_thread.join(timeout=scaled_grace)
            details = gate_error
            if cleanup_error:
                details += "; cleanup=" + cleanup_error
            return CheckResult(
                check.check_id,
                "ERROR",
                check.required,
                summary="start gate failed",
                details=details,
                reason="start_gate",
            )

        deadline = started + timeout
        try:
            remaining = max(0.0, deadline - time.monotonic())
            return_code = process.wait(timeout=remaining)
            timed_out = False
        except subprocess.TimeoutExpired:
            timed_out = True
            cleanup_error = _terminate(process, job, posix_group, scaled_grace)
            job_cleaned = job is not None
            try:
                return_code = process.wait(timeout=scaled_grace)
            except (OSError, ValueError, ChildProcessError, subprocess.TimeoutExpired):
                return_code = process.returncode
        cleanup_error = None
        if return_code:
            # A crashed/non-zero worker may have left descendants in its process
            # group even though the group leader has already exited.
            cleanup_error = _terminate(process, job, posix_group, scaled_grace)
            job_cleaned = job is not None
        stdout_thread.join(timeout=2.0)
        stderr_thread.join(timeout=2.0)
        if timed_out:
            details = stderr_capture.text()
            if cleanup_error:
                details += ("\n" if details else "") + "cleanup=" + cleanup_error
            return CheckResult(
                check.check_id,
                "TIMEOUT",
                check.required,
                summary="worker deadline exceeded",
                details=details,
                return_code=return_code,
                transport=result_mode,
                truncated_bytes=stdout_capture.truncated_bytes
                + stderr_capture.truncated_bytes,
                duration_ms=(time.monotonic() - started) * 1000,
            )

        outcome = (
            read_result_file(result_file, nonce, check.check_id)
            if result_mode == "file"
            else read_stdout_frames(
                stdout_capture.protocol_bytes(), nonce, check.check_id
            )
        )
        if outcome.envelope is not None:
            status = outcome.envelope["status"]
            details = str(outcome.envelope.get("details", ""))
            if stderr_capture.total:
                details += ("\n" if details else "") + stderr_capture.text()
            if cleanup_error:
                details += ("\n" if details else "") + "cleanup=" + cleanup_error
            return CheckResult(
                check.check_id,
                status,
                check.required,
                summary=str(outcome.envelope.get("summary", "")),
                details=details,
                reason=outcome.envelope.get("reason"),
                return_code=return_code,
                transport=result_mode,
                truncated_bytes=stdout_capture.truncated_bytes
                + stderr_capture.truncated_bytes,
                duration_ms=(time.monotonic() - started) * 1000,
            )
        if outcome.error_code is not None:
            if outcome.error_code in ("missing_result",) and return_code:
                status = "CRASH"
                reason = "worker_exit_without_envelope"
            else:
                status = "ERROR"
                reason = outcome.error_code
        elif return_code:
            status = "CRASH"
            reason = "worker_exit_without_envelope"
        else:
            status = "ERROR"
            reason = "missing_result"
        return CheckResult(
            check.check_id,
            status,
            check.required,
            summary="worker result unavailable",
            details=stderr_capture.text()
            + (
                ("\n" if stderr_capture.total else "") + "cleanup=" + cleanup_error
                if cleanup_error
                else ""
            ),
            reason=reason,
            return_code=return_code,
            transport=result_mode,
            truncated_bytes=stdout_capture.truncated_bytes
            + stderr_capture.truncated_bytes,
            duration_ms=(time.monotonic() - started) * 1000,
        )
    except BaseException as err:
        # Interrupts and unexpected callback/setup exceptions must not leave a
        # worker or descendant process alive after the parent unwinds.
        cleanup_error = _terminate(process, job, posix_group, scaled_grace)
        job_cleaned = job is not None
        if cleanup_error:
            try:
                os.write(
                    2,
                    ("self-check interrupted cleanup: " + cleanup_error + "\n").encode(
                        "ascii", "backslashreplace"
                    ),
                )
            except OSError:
                # The original exception remains authoritative when stderr is unavailable.
                pass
        if isinstance(err, (KeyboardInterrupt, SystemExit)):
            raise
        if not isinstance(err, Exception):
            raise
        raise
    finally:
        if job is not None:
            if not job_cleaned:
                cleanup_error = _close_job(job)
                if cleanup_error:
                    try:
                        os.write(
                            2,
                            ("self-check job cleanup: " + cleanup_error + "\n").encode(
                                "ascii", "backslashreplace"
                            ),
                        )
                    except OSError:
                        # The process result remains authoritative when stderr is unavailable.
                        pass
        _cleanup_session(session_dir, result_file)

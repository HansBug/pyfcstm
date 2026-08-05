"""Execute one isolated check synchronously under the supervisor.

The caller starts one worker, exchanges the fixed gate through one
``subprocess.communicate`` call, commits its terminal result, and only then can
advance to the next registry entry. Worker output is spooled to temporary files
and fed to a bounded capture after process completion. This module does not
create threads or schedule checks concurrently.
"""

import contextlib
import errno
import os
import signal
import subprocess
import tempfile
import time
import traceback
from typing import Optional

from ._win32 import JobAssignmentError, attach_process, format_ntstatus
from .model import CheckResult, CheckSpec
from .arguments import _WORKER_DISPATCH_ARGUMENT
from .protocol import build_start_gate
from .protocol import FRAME_PREFIX
from .protocol import MAX_ENVELOPE_BYTES
from .protocol import make_nonce
from .protocol import read_result_file
from .protocol import read_stdout_frames


STREAM_LIMIT = 2 * 1024 * 1024
SIGTERM_GRACE = 0.5
MAX_PROTOCOL_FRAMES = 2
_CAPTURE_CHUNK_SIZE = 64 * 1024
_PATH_SEPARATOR = os.pathsep


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
    if process is None:
        # Ownership handlers established before the spawn can reach cleanup with
        # nothing spawned yet; that is a clean exit, not a termination failure.
        return None
    if job is not None:
        return _finish_job(job, process, grace, terminate=True)
    errors = []
    if posix_group:
        try:
            os.killpg(process.pid, signal.SIGTERM)
        except OSError as err:
            # The group may already have exited before graceful termination.
            if err.errno != errno.ESRCH:
                _record_error(errors, "sigterm", err)
        _wait_process(process, grace, errors, kill_on_timeout=False)
        try:
            os.killpg(process.pid, signal.SIGKILL)
        except ProcessLookupError:
            pass
        except OSError as err:
            # Non-ESRCH kill failures leave explicit cleanup evidence.
            if err.errno != errno.ESRCH:
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


def _set_network_environment(environment: dict, enabled: bool) -> None:
    """Pass the explicit network opt-in to isolated callbacks."""
    environment["PYFCSTM_SELFCHECK_NETWORK"] = "1" if enabled else "0"


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
    exception: Optional[str] = None,
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
        exception=envelope.get("exception") or exception,
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


def _make_session_directory() -> Optional[str]:
    """
    Create the private session directory, or report that none is available.

    A plain function rather than part of :func:`_session_transport`, because
    tolerating the failure needs a handler and opening one inside that context
    manager would nest it inside the handler that owns the directory. From
    CPython 3.11 the inner ``try`` escapes the outer one, which skips the
    owner's ``finally`` entirely.

    :return: The new directory, or ``None`` when it could not be created.
    :rtype: str or None
    """
    try:
        return tempfile.mkdtemp(prefix="pyfcstm-selfcheck-")
    except (OSError, IOError):
        # A full, damaged, or read-only temporary filesystem leaves the stdout
        # transport as the only way for a worker to report its result.
        return None


def _create_empty_file(path: str) -> bool:
    """
    Create or truncate one file and report whether it is now usable.

    :param path: Path the caller has already bound for cleanup.
    :type path: str
    :return: Whether the file exists and is writable.
    :rtype: bool
    """
    try:
        with open(path, "wb"):
            pass
    except (OSError, IOError):
        # The session directory can be unwritable even when it was created.
        return False
    return True


@contextlib.contextmanager
def _session_transport():
    """
    Own the private session directory and the worker result file inside it.

    A system that can provide neither still yields, with ``result_file`` set to
    ``None``, so the caller falls back to the stdout transport instead of
    failing the check outright.

    :return: An iterator yielding ``(session_dir, result_file, result_mode)``.
    :rtype: collections.abc.Iterator[tuple]
    """
    session_dir = None
    result_file = None
    try:
        session_dir = _make_session_directory()
        if session_dir is not None:
            # Name the file before creating it. Cleanup here is by path, not by
            # handle, and _cleanup_session tolerates a path that was never
            # created -- but it cannot remove a directory whose file it was
            # never told about, so binding the name afterwards would leave the
            # create-truncate as a window that leaks the whole session
            # directory.
            result_file = os.path.join(session_dir, "result.log")
            if not _create_empty_file(result_file):
                result_file = None
        yield session_dir, result_file, "file" if result_file else "stdout"
    finally:
        _cleanup_session(session_dir, result_file)


def _make_output_spool():
    """
    Create one bounded output spool, or describe why it is unavailable.

    Split out of :func:`_output_spools` for the reason given in
    :func:`_make_session_directory`: the handler that tolerates the failure must
    not be nested inside the handler that owns the spool.

    :return: ``(spool, setup_error)``; exactly one of the two is ``None``.
    :rtype: tuple
    """
    try:
        return tempfile.TemporaryFile(mode="w+b"), None
    except (OSError, ValueError) as err:
        # Temporary output storage can be unavailable on a damaged or
        # read-only system; never fall back to unbounded PIPE collection.
        return None, "{}: {}".format(type(err).__name__, err)


@contextlib.contextmanager
def _output_spools():
    """
    Own the two bounded spool files that collect worker stdout and stderr.

    Both spools are yielded as ``None`` when either could not be created, so a
    half-created pair is never used for bounded capture.

    :return: An iterator yielding ``(stdout_spool, stderr_spool, setup_error)``.
    :rtype: collections.abc.Iterator[tuple]
    """
    stdout_spool = None
    stderr_spool = None
    try:
        stdout_spool, setup_error = _make_output_spool()
        if setup_error is None:
            stderr_spool, setup_error = _make_output_spool()
        if setup_error is None:
            yield stdout_spool, stderr_spool, None
        else:
            # A half-created pair must never be used for bounded capture; both
            # spools are still released by this handler.
            yield None, None, setup_error
    finally:
        _close_capture_stream(stdout_spool)
        _close_capture_stream(stderr_spool)


class _WorkerTree:
    """
    One spawned worker process together with the job object that bounds it.

    Termination is recorded so that the owning context manager stays quiet when
    the caller already terminated the tree and folded the diagnostics into a
    check result.

    :param process: The spawned worker.
    :type process: subprocess.Popen
    :param posix_group: Whether the worker leads its own POSIX process group.
    :type posix_group: bool
    :param grace: Seconds allowed between graceful and forceful termination.
    :type grace: float

    :ivar job: Native job object bounding the tree on Windows, else ``None``.
    :vartype job: Any
    """

    def __init__(self, process, posix_group: bool, grace: float):
        self.process = process
        self.job = None
        self._posix_group = posix_group
        self._grace = grace
        self._terminated = False

    def terminate(self) -> Optional[str]:
        """
        Terminate the tree at most once and return cleanup diagnostics.

        :return: Cleanup diagnostics, or ``None`` when nothing needed doing.
        :rtype: str or None
        """
        if self._terminated:
            return None
        self._terminated = True
        job, self.job = self.job, None
        return _terminate(self.process, job, self._posix_group, self._grace)


def _spawn_worker_process(spawned: list, command, popen_kwargs) -> Optional[Exception]:
    """
    Spawn one worker into a caller-owned list and report any spawn failure.

    Split out of :func:`_worker_tree` for the reason given in
    :func:`_make_session_directory`: the handler that tolerates the failure must
    not be nested inside the handler that terminates the worker.

    The child is appended to a list the caller created *before* calling, rather
    than returned. A return would put the handover after the spawn, and an
    interrupt in between would leave the child with no owner at all -- and an
    orphaned process is the one leak in this module that the operating system
    will not reclaim when the parent exits.

    :param spawned: Caller-owned list that receives the child on success.
    :type spawned: list
    :param command: Argument vector for the worker process.
    :type command: collections.abc.Sequence[str]
    :param popen_kwargs: Keyword arguments for :class:`subprocess.Popen`.
    :type popen_kwargs: dict
    :return: The spawn failure, or ``None`` when the child started.
    :rtype: Exception or None
    """
    try:
        spawned.append(subprocess.Popen(command, **popen_kwargs))
    except (OSError, ValueError) as err:
        # The spawn fails when the interpreter path is unusable, the working
        # directory was removed, or the environment is rejected by the OS.
        # Reported rather than raised so the caller can classify it as one check
        # result instead of unwinding the whole run.
        return err
    return None


@contextlib.contextmanager
def _worker_tree(command, popen_kwargs, posix_group: bool, grace: float):
    """
    Own one spawned worker tree for exactly as long as the ``with`` block runs.

    The worker is spawned inside the ``try``, so no statement runs between the
    spawn and the handler that terminates it.

    :param command: Argument vector for the worker process.
    :type command: collections.abc.Sequence[str]
    :param popen_kwargs: Keyword arguments for :class:`subprocess.Popen`.
    :type popen_kwargs: dict
    :param posix_group: Whether the worker leads its own POSIX process group.
    :type posix_group: bool
    :param grace: Seconds allowed between graceful and forceful termination.
    :type grace: float
    :return: An iterator yielding ``(tree, spawn_error)``; ``tree`` is ``None``
        exactly when the spawn failed.
    :rtype: collections.abc.Iterator[tuple]
    """
    spawned = []
    tree = None
    try:
        spawn_error = _spawn_worker_process(spawned, command, popen_kwargs)
        if spawned:
            tree = _WorkerTree(spawned[0], posix_group, grace)
        yield tree, spawn_error
    finally:
        if spawned:
            # ``tree`` is unset only when an interrupt landed between the spawn
            # and the line that wraps it; the child still needs terminating, and
            # a fresh wrapper does that with no job attached, which is correct
            # because nothing got far enough to attach one.
            owner = tree if tree is not None else _WorkerTree(
                spawned[0], posix_group, grace
            )
            _write_cleanup_diagnostic("worker cleanup", owner.terminate())


def run_check_process(
    check: CheckSpec,
    timeout: float,
    timeout_scale: float = 1.0,
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
    # Every resource below is owned by the stack before it is acquired, so an
    # interrupt anywhere in this function still releases it. Handlers opened
    # while a resource is held would not: from CPython 3.11 a nested ``try:``
    # compiles to a ``NOP`` that no exception-table entry covers.
    with contextlib.ExitStack() as stack:
        session_dir, result_file, result_mode = stack.enter_context(
            _session_transport()
        )
        stdout_spool, stderr_spool, capture_setup_error = stack.enter_context(
            _output_spools()
        )
        if capture_setup_error and result_mode == "stdout":
            return _make_result(
                check,
                "ERROR",
                "bounded worker output capture is unavailable",
                "capture_unavailable",
                started,
                evidence=capture_setup_error,
                result_mode=result_mode,
            )
        command = _command_for_worker(check, nonce, result_mode, result_file)
        child_environment = os.environ.copy()
        child_environment["PYFCSTM_SELFCHECK_WORKER_PROCESS"] = "1"
        _set_network_environment(child_environment, network)
        popen_kwargs = {
            "stdin": subprocess.PIPE,
            "stdout": stdout_spool or subprocess.DEVNULL,
            "stderr": stderr_spool or subprocess.DEVNULL,
            "bufsize": 0,
            "env": child_environment,
        }
        package_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
        package_parent = os.path.dirname(package_dir)
        # Put the package under test first while preserving caller-provided import
        # roots for worker callbacks and runtime diagnostics.
        inherited_pythonpath = child_environment.get("PYTHONPATH")
        child_environment["PYTHONPATH"] = _PATH_SEPARATOR.join(
            path for path in (package_parent, inherited_pythonpath) if path
        )
        popen_kwargs["cwd"] = session_dir or package_dir
        posix_group = os.name == "posix"
        if posix_group:
            popen_kwargs["start_new_session"] = True
        elif os.name == "nt":
            popen_kwargs["creationflags"] = getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )
        tree, spawn_error = stack.enter_context(
            _worker_tree(command, popen_kwargs, posix_group, scaled_grace)
        )
        if spawn_error is not None:
            return _make_result(
                check,
                "ERROR",
                "worker spawn failed",
                "spawn_failed",
                started,
                evidence=str(spawn_error),
            )
        process = tree.process

        if os.name == "nt":
            try:
                tree.job = attach_process(process)
            except Exception as err:
                # Native job setup fails in restricted or already-nested job
                # environments. Only Exception is caught: a control sentinel
                # unwinds to the owning context manager, which terminates the
                # worker there rather than turning it into a check result.
                cleanup_error = tree.terminate()
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

        stdout_data = None
        stderr_data = None
        communication_errors = []
        cleanup_error = None
        timed_out = False
        deadline = started + timeout
        try:
            stdout_data, stderr_data = process.communicate(
                input=build_start_gate(nonce),
                timeout=max(0.0, deadline - time.monotonic()),
            )
        except subprocess.TimeoutExpired as err:
            timed_out = True
            stdout_data = err.output if stdout_spool is None else None
            stderr_data = err.stderr if stderr_spool is None else None
            cleanup_error = tree.terminate()
            try:
                stdout_data, stderr_data = process.communicate(timeout=scaled_grace)
            except subprocess.TimeoutExpired as drain_error:
                communication_errors.append(
                    "output_drain:TimeoutExpired: {}\n{}".format(
                        drain_error,
                        traceback.format_exc().rstrip(),
                    )
                )
                if stdout_spool is None:
                    stdout_data = drain_error.output or stdout_data
                if stderr_spool is None:
                    stderr_data = drain_error.stderr or stderr_data
            except (OSError, ValueError) as drain_error:
                communication_errors.append(
                    "output_drain:{}: {}\n{}".format(
                        type(drain_error).__name__,
                        drain_error,
                        traceback.format_exc().rstrip(),
                    )
                )
        except (OSError, ValueError) as err:
            cleanup_error = tree.terminate()
            exception = traceback.format_exc()
            details = "worker_communication:{}: {}\n{}".format(
                type(err).__name__, err, exception.rstrip()
            )
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
                exception=exception,
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
        if not timed_out:
            # A normally returning worker may still leave descendants in its
            # process group; always close the group before the next check.
            cleanup_error = tree.terminate()
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
        details = _diagnostics(
            communication_errors,
            base=outcome.diagnostic or "",
            cleanup_error=cleanup_error,
        )
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

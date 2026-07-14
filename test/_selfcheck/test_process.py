"""Black-box process isolation tests for self-check workers."""

import os
import subprocess
import sys
import time
from pathlib import Path

import pytest

from pyfcstm._selfcheck import process as process_module
from pyfcstm._selfcheck.model import CheckSpec
from pyfcstm._selfcheck.process import (
    STREAM_LIMIT,
    _BoundedCapture,
    _command_for_worker,
    run_check_process,
)
from pyfcstm._selfcheck.protocol import encode_result_frame


_FIXTURE = Path(__file__).with_name("fixtures") / "worker_process.py"


def _install_fixture(monkeypatch, scenario, child_pid_file=None):
    def command(check, nonce, result_mode, result_file):
        result = [
            sys.executable,
            str(_FIXTURE),
            "--check-id",
            check.check_id,
            "--nonce",
            nonce,
            "--result-mode",
            result_mode,
            "--scenario",
            scenario,
        ]
        if result_file is not None:
            result.extend(("--result-file", result_file))
        if child_pid_file is not None:
            result.extend(("--child-pid-file", str(child_pid_file)))
        return result

    monkeypatch.setattr(process_module, "_command_for_worker", command)


def _spec(name="fixture.process"):
    return CheckSpec(name, "fixture", title="process fixture")


def _pid_alive(pid):
    try:
        os.kill(pid, 0)
    except ProcessLookupError:
        return False
    except PermissionError:
        return True
    return True


def _wait_for_pid_exit(pid, timeout=3.0):
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if not _pid_alive(pid):
            return True
        time.sleep(0.02)
    return not _pid_alive(pid)


def _wait_for_file(path, timeout=2.0):
    """Wait for a real worker fixture to publish its child PID evidence."""
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        if path.exists():
            return True
        time.sleep(0.01)
    return path.exists()


@pytest.mark.unittest
def test_artifact_self_dispatch_runs_in_fresh_process():
    """The real hidden worker completes through the production command path."""
    result = run_check_process(
        CheckSpec(
            "artifact.self_dispatch",
            "self_dispatch",
            title="isolated self-dispatch",
        ),
        timeout=10.0,
    )
    assert result.status == "PASS"
    assert result.pid and result.pid != os.getpid()
    assert result.transport == "file"


@pytest.mark.unittest
def test_process_supervision_does_not_create_threads(monkeypatch):
    """One isolated check is supervised synchronously by the calling thread."""

    class ForbiddenThreading:
        @staticmethod
        def Thread(*args, **kwargs):
            del args, kwargs
            raise AssertionError("self-check created a thread")

    _install_fixture(monkeypatch, "pass")
    monkeypatch.setattr(
        process_module, "threading", ForbiddenThreading(), raising=False
    )
    assert run_check_process(_spec(), timeout=5.0).status == "PASS"


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("scenario", "status", "reason"),
    [
        ("error", "ERROR", None),
        ("no_result", "ERROR", "missing_result"),
        ("malformed", "ERROR", "invalid_frame"),
        ("truncated", "ERROR", "missing_lf"),
        ("duplicate", "ERROR", "duplicate_frame"),
        ("wrong_nonce", "ERROR", "wrong_nonce"),
        ("crash", "CRASH", "worker_exit_without_envelope"),
        ("abort", "CRASH", "worker_exit_without_envelope"),
    ],
)
def test_worker_fault_categories_are_normalized(monkeypatch, scenario, status, reason):
    """Representative protocol and hard-exit faults never crash the parent."""
    _install_fixture(monkeypatch, scenario)
    result = run_check_process(_spec("fixture." + scenario), timeout=5.0)
    assert result.status == status
    if reason is not None:
        assert result.reason == reason


@pytest.mark.unittest
def test_valid_envelope_is_authoritative_over_nonzero_exit(monkeypatch):
    """A complete semantic frame wins over the worker diagnostic return code."""
    _install_fixture(monkeypatch, "nonzero_envelope")
    result = run_check_process(_spec(), timeout=5.0)
    assert result.status == "PASS"
    assert result.return_code == 7


@pytest.mark.unittest
def test_worker_protocol_write_failure_is_error(monkeypatch):
    """Infrastructure exit code 3 without a frame is not misreported as crash."""
    _install_fixture(monkeypatch, "exit3_no_frame")
    result = run_check_process(_spec(), timeout=5.0)
    assert result.status == "ERROR"
    assert result.reason == "worker_protocol_error"


@pytest.mark.unittest
def test_timeout_preserves_output_and_terminates_worker(monkeypatch):
    """Deadline expiry returns bounded evidence after process-tree cleanup."""
    _install_fixture(monkeypatch, "hang")
    result = run_check_process(_spec(), timeout=0.2)
    assert result.status == "TIMEOUT"
    assert result.timeout is True
    assert result.duration_ms < 5000


@pytest.mark.unittest
@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group contract")
@pytest.mark.parametrize("scenario", ["spawn_hang", "crash_spawn"])
def test_timeout_and_crash_clean_up_grandchildren(monkeypatch, tmp_path, scenario):
    """Both timeout and leader crash remove descendants from the worker group."""
    child_pid_file = tmp_path / "child.pid"
    _install_fixture(monkeypatch, scenario, child_pid_file)
    result = run_check_process(_spec(), timeout=2.0)
    assert result.status in ("TIMEOUT", "CRASH")
    assert _wait_for_file(child_pid_file)
    child_pid = int(child_pid_file.read_text(encoding="ascii"))
    assert _wait_for_pid_exit(child_pid)


@pytest.mark.unittest
@pytest.mark.parametrize("scenario", ["huge_stderr", "huge_stdout"])
def test_stream_capture_is_bounded(monkeypatch, scenario):
    """Large business output is bounded before entering the final report."""
    _install_fixture(monkeypatch, scenario)
    result = run_check_process(_spec(), timeout=5.0)
    assert result.status == "PASS"
    assert result.truncated_bytes > 0
    assert (
        len(result.stdout.encode()) + len(result.stderr.encode())
        < 2 * STREAM_LIMIT + 100
    )


@pytest.mark.unittest
def test_invalid_utf8_diagnostics_remain_reportable(monkeypatch):
    """Invalid worker bytes use backslash escaping instead of breaking JSON."""
    _install_fixture(monkeypatch, "invalid_utf8")
    result = run_check_process(_spec(), timeout=5.0)
    assert result.status == "PASS"
    assert "\\xff" in result.stderr


@pytest.mark.unittest
def test_temp_failure_uses_stdout_protocol_fallback(monkeypatch):
    """A missing private temp directory does not disable isolated checking."""
    _install_fixture(monkeypatch, "pass")
    monkeypatch.setattr(
        "tempfile.mkdtemp", lambda **kwargs: (_ for _ in ()).throw(OSError("no temp"))
    )
    result = run_check_process(_spec(), timeout=5.0)
    assert result.status == "PASS"
    assert result.transport == "stdout"


@pytest.mark.unittest
def test_stdout_protocol_survives_oversized_unterminated_business_output(monkeypatch):
    """Fallback protocol extraction is independent from bounded business output."""
    _install_fixture(monkeypatch, "huge_stdout")
    monkeypatch.setattr(
        "tempfile.mkdtemp", lambda **kwargs: (_ for _ in ()).throw(OSError("no temp"))
    )
    result = run_check_process(_spec(), timeout=5.0)
    assert result.status == "PASS"
    assert result.transport == "stdout"
    assert result.truncated_bytes > 0


@pytest.mark.unittest
@pytest.mark.parametrize("scenario", ["stdout_noise", "stdout_short_noise"])
def test_stdout_noise_without_a_frame_is_reportable(monkeypatch, scenario):
    """Real stdout business output remains bounded when no frame is emitted."""
    _install_fixture(monkeypatch, scenario)
    monkeypatch.setattr(
        "tempfile.mkdtemp", lambda **kwargs: (_ for _ in ()).throw(OSError("no temp"))
    )
    result = run_check_process(_spec(), timeout=5.0)
    assert result.status == "ERROR"
    assert result.reason == "missing_result"


@pytest.mark.unittest
def test_worker_session_files_are_removed(monkeypatch, tmp_path):
    """Result transport files and the private session directory are temporary."""
    session = tmp_path / "session"
    session.mkdir()
    _install_fixture(monkeypatch, "pass")
    monkeypatch.setattr("tempfile.mkdtemp", lambda **kwargs: str(session))
    assert run_check_process(_spec(), timeout=5.0).status == "PASS"
    assert not session.exists()


@pytest.mark.unittest
def test_spawn_failure_is_a_structured_error(monkeypatch):
    """An unavailable executable becomes a check result instead of an exception."""
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("spawn failed")),
    )
    result = run_check_process(_spec(), timeout=1.0)
    assert result.status == "ERROR"
    assert result.reason == "spawn_failed"


@pytest.mark.unittest
def test_worker_command_switches_for_frozen_artifact(monkeypatch):
    """Frozen workers re-enter the same executable without Python ``-m``."""
    check = _spec("demo")
    source = _command_for_worker(check, "7" * 32, "stdout", None)
    assert source[:3] == [sys.executable, "-m", "pyfcstm"]
    monkeypatch.setattr(sys, "frozen", True, raising=False)
    frozen = _command_for_worker(check, "7" * 32, "stdout", None)
    assert frozen[0] == sys.executable
    assert "-m" not in frozen


@pytest.mark.unittest
def test_bounded_capture_extracts_protocol_without_preceding_newline():
    """A framed result remains recoverable after unterminated business bytes."""
    capture = _BoundedCapture(limit=32, capture_protocol=True)
    frame = encode_result_frame(
        {
            "schema": "pyfcstm-selfcheck-worker/v1",
            "check_id": "demo",
            "nonce": "8" * 32,
            "status": "PASS",
        }
    )
    capture.append(b"business" + frame)
    capture.finish()
    assert capture.raw() == b"business"
    assert capture.protocol_bytes() == frame


@pytest.mark.unittest
def test_keyboard_interrupt_terminates_started_worker(monkeypatch):
    """An interrupt during wait still invokes bounded cleanup before re-raising."""
    cleaned = []

    class Process:
        pid = 12345
        returncode = None

        def communicate(self, input=None, timeout=None):
            del input, timeout
            raise KeyboardInterrupt()

    monkeypatch.setattr(process_module.os, "name", "nt")
    monkeypatch.setattr("subprocess.Popen", lambda *args, **kwargs: Process())
    monkeypatch.setattr(process_module, "attach_process", lambda process: object())
    monkeypatch.setattr(
        process_module,
        "_terminate",
        lambda process, job, posix_group, grace: cleaned.append(process) or None,
    )
    with pytest.raises(KeyboardInterrupt):
        run_check_process(_spec(), timeout=1.0)
    assert cleaned


@pytest.mark.unittest
def test_bounded_capture_handles_partial_and_oversized_protocol_frames():
    """EOF and oversized protocol candidates remain bounded and observable."""
    from pyfcstm._selfcheck.protocol import FRAME_PREFIX, MAX_ENVELOPE_BYTES

    noise = _BoundedCapture(capture_protocol=True)
    noise.append(b"ordinary output")
    noise.finish()
    assert noise.raw() == b"ordinary output"

    partial = _BoundedCapture(capture_protocol=True)
    partial.append(b"prefix" + FRAME_PREFIX + b"partial")
    partial.finish()
    assert partial.raw() == b"prefix"
    assert partial.protocol_frames

    oversized = _BoundedCapture(capture_protocol=True)
    oversized.append(FRAME_PREFIX + b"x" * (MAX_ENVELOPE_BYTES + 2))
    assert oversized.protocol_frames
    assert len(oversized._protocol_pending) <= MAX_ENVELOPE_BYTES + 1

    short = _BoundedCapture(capture_protocol=True)
    short.append(b"x")
    short.finish()
    assert short.raw() == b"x"


@pytest.mark.unittest
def test_capture_and_spool_cleanup_failures_are_bounded(monkeypatch):
    """Output spool read/close failures become bounded diagnostic bytes."""

    class BrokenStream:
        def seek(self, position):
            del position
            raise OSError("seek")

        def close(self):
            raise ValueError("closed")

    capture = process_module._capture_stream(BrokenStream(), None, False)
    assert "output read failed: seek" in capture.text()
    process_module._close_capture_stream(None)
    process_module._close_capture_stream(BrokenStream())


@pytest.mark.unittest
def test_job_and_direct_cleanup_failures_are_bounded():
    """Native and direct cleanup errors are returned as diagnostic evidence."""
    from pyfcstm._selfcheck._win32 import JobAssignmentError

    class Process:
        pid = 7

        def __init__(self):
            self.calls = []
            self.waits = 0

        def terminate(self):
            self.calls.append("terminate")

        def kill(self):
            self.calls.append("kill")
            raise OSError("kill")

        def wait(self, timeout=None):
            self.calls.append(("wait", timeout))
            self.waits += 1
            if self.waits == 1:
                raise __import__("subprocess").TimeoutExpired("worker", timeout)
            raise ChildProcessError("gone")

    class Job:
        def terminate(self, code):
            del code
            raise JobAssignmentError("job")

        def close(self):
            raise OSError("close")

    process = Process()
    details = process_module._terminate(process, Job(), False, grace=0.01)
    assert "job_terminate:JobAssignmentError" in details
    assert "job_close:OSError" in details

    process = Process()
    process.terminate = lambda: (_ for _ in ()).throw(OSError("terminate"))
    details = process_module._terminate(process, None, False, grace=0.01)
    assert "process_terminate:OSError" in details
    assert "process_kill:OSError" in details


@pytest.mark.unittest
def test_wait_helpers_record_timeout_and_kill_failures():
    """Cleanup waits remain bounded when kill and reap both fail."""
    errors = []

    class Process:
        def __init__(self):
            self.waits = 0

        def wait(self, timeout=None):
            del timeout
            self.waits += 1
            if self.waits == 1:
                raise __import__("subprocess").TimeoutExpired("worker", 0.01)
            raise OSError("reap")

        def kill(self):
            raise OSError("kill")

    process_module._wait_process(Process(), 0.01, errors, kill_on_timeout=False)
    assert errors == []
    process_module._wait_process(Process(), 0.01, errors, kill_on_timeout=True)
    assert "process_kill:OSError" in errors
    assert "process_wait:OSError" in errors

    errors = []

    class Gone:
        @staticmethod
        def wait(timeout=None):
            del timeout
            raise OSError("gone")

    process_module._wait_process(Gone(), 0.01, errors, kill_on_timeout=True)
    assert "process_wait:OSError" in errors


@pytest.mark.unittest
def test_group_cleanup_probe_errors_and_deadlines_are_reportable(monkeypatch):
    """POSIX group cleanup records both probe and bounded-wait failures."""
    errors = []
    monkeypatch.setattr(
        process_module.os,
        "killpg",
        lambda pid, signal: (_ for _ in ()).throw(OSError("probe")),
        raising=False,
    )
    process_module._wait_for_group_exit(17, 0.01, errors)
    assert "group_probe:OSError" in errors

    clock = iter((0.0, 1.0))
    monkeypatch.setattr(process_module.time, "monotonic", lambda: next(clock))
    monkeypatch.setattr(process_module.time, "sleep", lambda interval: None)
    monkeypatch.setattr(
        process_module.os, "killpg", lambda pid, signal: None, raising=False
    )
    errors = []
    process_module._wait_for_group_exit(17, 0.01, errors)
    assert "group_wait:TimeoutExpired" in errors


@pytest.mark.unittest
def test_job_cleanup_records_direct_termination_failure():
    """Job termination falls back to the leader and records that failure."""
    from pyfcstm._selfcheck._win32 import JobAssignmentError

    class Process:
        pid = 17

        def terminate(self):
            raise OSError("leader")

        def wait(self, timeout=None):
            del timeout
            return 0

    class Job:
        def terminate(self, code):
            del code
            raise JobAssignmentError("job")

        def close(self):
            return None

    details = process_module._finish_job(Job(), Process(), 0.01, terminate=True)
    assert "process_terminate:OSError" in details


@pytest.mark.unittest
def test_posix_cleanup_records_non_esrch_sigkill_failure(monkeypatch):
    """A non-ESRCH hard-kill error remains explicit cleanup evidence."""
    calls = []
    sigkill = getattr(process_module.signal, "SIGKILL", process_module.signal.SIGTERM)
    if not hasattr(process_module.signal, "SIGKILL"):
        monkeypatch.setattr(process_module.signal, "SIGKILL", sigkill, raising=False)

    def killpg(pid, signal):
        calls.append(signal)
        if signal == sigkill:
            raise OSError("killpg")

    class Process:
        pid = 17

        @staticmethod
        def wait(timeout=None):
            del timeout
            return 0

    monkeypatch.setattr(process_module.os, "killpg", killpg, raising=False)
    details = process_module._terminate(Process(), None, True, grace=0.01)
    assert "sigkill:OSError" in details
    assert calls == [process_module.signal.SIGTERM, sigkill]


@pytest.mark.unittest
def test_posix_cleanup_targets_the_entire_process_group(monkeypatch):
    """POSIX cleanup sends graceful and hard signals to the worker group."""
    if os.name != "posix":
        pytest.skip("POSIX process groups are unavailable")
    calls = []

    def killpg(pid, sig):
        calls.append((pid, sig))
        if sig == 0:
            raise ProcessLookupError()

    class Process:
        pid = 17

        @staticmethod
        def wait(timeout=None):
            del timeout
            return 1

    monkeypatch.setattr(process_module.os, "killpg", killpg)
    assert process_module._terminate(Process(), None, True, grace=0.01) is None
    assert (17, process_module.signal.SIGTERM) in calls
    assert (17, process_module.signal.SIGKILL) in calls


@pytest.mark.unittest
def test_native_containment_failure_terminates_started_worker(monkeypatch):
    """A Windows Job assignment failure never leaves the worker running."""
    from types import SimpleNamespace

    class Process:
        pid = 23
        returncode = None

        def __init__(self):
            self.terminated = False

        def terminate(self):
            self.terminated = True
            self.returncode = 1

        def wait(self, timeout=None):
            del timeout
            return self.returncode

    process = Process()
    fake_os = SimpleNamespace(
        name="nt",
        path=os.path,
        environ=os.environ,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
    )
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(
        process_module,
        "attach_process",
        lambda child: (_ for _ in ()).throw(OSError("assignment")),
    )
    result = run_check_process(_spec(), timeout=0.1)
    assert result.status == "ERROR"
    assert result.reason == "isolation_unavailable"
    assert process.terminated is True


@pytest.mark.unittest
def test_native_containment_failure_preserves_cleanup_evidence(monkeypatch):
    """Windows isolation failures include cleanup diagnostics from the leader."""
    from types import SimpleNamespace

    class Process:
        pid = 23
        returncode = None

        def terminate(self):
            self.returncode = 1

        def wait(self, timeout=None):
            del timeout
            return self.returncode

    process = Process()
    fake_os = SimpleNamespace(
        name="nt",
        path=os.path,
        environ=os.environ,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
    )
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(
        process_module,
        "attach_process",
        lambda child: (_ for _ in ()).throw(OSError("assignment")),
    )
    monkeypatch.setattr(process_module, "_terminate", lambda *args: "leader_cleanup")
    result = run_check_process(_spec(), timeout=0.1)
    assert result.reason == "isolation_unavailable"
    assert "cleanup=leader_cleanup" in result.evidence


@pytest.mark.unittest
def test_native_containment_control_sentinel_is_re_raised(monkeypatch):
    """Control sentinels from native setup are cleaned and propagated."""
    from types import SimpleNamespace

    class Process:
        pid = 23

        def terminate(self):
            return None

        def wait(self, timeout=None):
            del timeout
            return 1

    process = Process()
    fake_os = SimpleNamespace(
        name="nt",
        path=os.path,
        environ=os.environ,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
    )
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(
        process_module,
        "attach_process",
        lambda child: (_ for _ in ()).throw(SystemExit(4)),
    )
    monkeypatch.setattr(process_module, "_terminate", lambda *args: None)
    with pytest.raises(SystemExit):
        run_check_process(_spec(), timeout=0.1)


@pytest.mark.unittest
def test_native_containment_non_runtime_sentinel_is_re_raised(monkeypatch):
    """Unexpected control sentinels from native setup are not swallowed."""
    from types import SimpleNamespace

    class Process:
        pid = 23

        def terminate(self):
            return None

        def wait(self, timeout=None):
            del timeout
            return 1

    process = Process()
    fake_os = SimpleNamespace(
        name="nt",
        path=os.path,
        environ=os.environ,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
    )
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(
        process_module,
        "attach_process",
        lambda child: (_ for _ in ()).throw(GeneratorExit()),
    )
    monkeypatch.setattr(process_module, "_terminate", lambda *args: None)
    with pytest.raises(GeneratorExit):
        run_check_process(_spec(), timeout=0.1)


@pytest.mark.unittest
def test_worker_communication_failure_retains_cleanup_evidence(monkeypatch):
    """A subprocess communication failure retains cleanup diagnostics."""

    class Process:
        pid = 29
        returncode = None

        @staticmethod
        def communicate(input=None, timeout=None):
            del input, timeout
            raise OSError("pipe failed")

    monkeypatch.setattr(process_module.os, "name", "nt")
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(process_module, "attach_process", lambda process: object())
    monkeypatch.setattr(
        process_module, "_terminate", lambda *args, **kwargs: "cleanup failed"
    )
    result = run_check_process(_spec(), timeout=0.1)
    assert result.reason == "worker_communication"
    assert "cleanup=cleanup failed" in result.evidence


@pytest.mark.unittest
def test_transport_cleanup_failures_are_reported(capfd, monkeypatch):
    """Transport cleanup errors are visible while spawn failure stays typed."""
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("spawn")),
    )
    monkeypatch.setattr(
        process_module.os,
        "unlink",
        lambda path: (_ for _ in ()).throw(OSError("unlink")),
    )
    monkeypatch.setattr(
        process_module.os,
        "rmdir",
        lambda path: (_ for _ in ()).throw(OSError("rmdir")),
    )
    result = run_check_process(_spec(), timeout=1.0)
    assert result.reason == "spawn_failed"
    assert "transport cleanup" in capfd.readouterr().err


@pytest.mark.unittest
def test_cleanup_diagnostic_failure_does_not_escape(monkeypatch):
    """Unavailable raw stderr does not replace the structured spawn result."""
    monkeypatch.setattr(
        "subprocess.Popen",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("spawn")),
    )
    monkeypatch.setattr(
        process_module.os,
        "unlink",
        lambda path: (_ for _ in ()).throw(OSError("unlink")),
    )
    monkeypatch.setattr(
        process_module.os,
        "rmdir",
        lambda path: (_ for _ in ()).throw(OSError("rmdir")),
    )
    monkeypatch.setattr(
        process_module.os,
        "write",
        lambda descriptor, data: (_ for _ in ()).throw(OSError("stderr")),
    )
    result = run_check_process(_spec(), timeout=1.0)
    assert result.status == "ERROR"
    assert result.reason == "spawn_failed"


@pytest.mark.unittest
def test_worker_drain_failure_is_normalized_as_timeout(monkeypatch):
    """Pipe drain failures after timeout stay in the timeout result."""

    class Process:
        pid = 29
        returncode = 0

        def __init__(self):
            self.calls = 0

        def communicate(self, input=None, timeout=None):
            del input, timeout
            self.calls += 1
            if self.calls == 1:
                raise subprocess.TimeoutExpired("worker", 0.01, output=b"partial")
            raise OSError("drain")

    process = Process()
    monkeypatch.setattr(process_module.os, "name", "posix")
    monkeypatch.setattr(
        process_module.tempfile,
        "TemporaryFile",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("spool")),
    )
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(process_module, "_terminate", lambda *args: None)
    result = run_check_process(_spec(), timeout=0.01)
    assert result.status == "TIMEOUT"
    assert "output_drain:OSError" in result.evidence


@pytest.mark.unittest
def test_worker_drain_timeout_is_normalized_as_timeout(monkeypatch):
    """A second timeout during output drain remains bounded and reportable."""

    class Process:
        pid = 29
        returncode = 0

        def __init__(self):
            self.calls = 0

        def communicate(self, input=None, timeout=None):
            del input, timeout
            self.calls += 1
            raise subprocess.TimeoutExpired("worker", 0.01, output=b"partial")

    process = Process()
    monkeypatch.setattr(process_module.os, "name", "posix")
    monkeypatch.setattr(
        process_module.tempfile,
        "TemporaryFile",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("spool")),
    )
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(process_module, "_terminate", lambda *args: None)
    result = run_check_process(_spec(), timeout=0.01)
    assert result.status == "TIMEOUT"
    assert "output_drain:TimeoutExpired" in result.evidence


@pytest.mark.unittest
def test_windows_crash_status_includes_ntstatus(monkeypatch):
    """A Windows-style crash code is retained in the public result."""
    from types import SimpleNamespace

    class Process:
        pid = 29
        returncode = -1073741819

        @staticmethod
        def terminate():
            return None

        @staticmethod
        def wait(timeout=None):
            del timeout
            return 0

        @staticmethod
        def communicate(input=None, timeout=None):
            del input, timeout
            return b"", b""

    fake_os = SimpleNamespace(
        name="nt",
        path=os.path,
        environ=os.environ,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
    )
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(process_module, "attach_process", lambda process: None)
    result = run_check_process(_spec(), timeout=1.0)
    assert result.status == "CRASH"
    assert result.ntstatus == "0xC0000005 (ACCESS_VIOLATION)"


@pytest.mark.unittest
def test_result_parser_exception_is_re_raised_after_cleanup(monkeypatch):
    """Unexpected parser exceptions are not silently converted to PASS."""
    _install_fixture(monkeypatch, "pass")
    monkeypatch.setattr(
        process_module,
        "read_result_file",
        lambda *args: (_ for _ in ()).throw(RuntimeError("parser")),
    )
    with pytest.raises(RuntimeError, match="parser"):
        run_check_process(_spec(), timeout=5.0)


@pytest.mark.unittest
def test_non_runtime_parser_sentinel_is_re_raised_after_cleanup(monkeypatch):
    """Non-runtime parser sentinels remain visible after worker cleanup."""
    _install_fixture(monkeypatch, "pass")
    monkeypatch.setattr(
        process_module,
        "read_result_file",
        lambda *args: (_ for _ in ()).throw(GeneratorExit()),
    )
    with pytest.raises(GeneratorExit):
        run_check_process(_spec(), timeout=5.0)


@pytest.mark.unittest
def test_final_job_cleanup_runs_for_non_kill_on_close_job(monkeypatch):
    """A successful Windows worker still closes its Job Object in ``finally``."""
    from types import SimpleNamespace

    class Process:
        pid = 31
        returncode = 0

        @staticmethod
        def communicate(input=None, timeout=None):
            del input, timeout
            return b"", b""

        @staticmethod
        def wait(timeout=None):
            del timeout
            return 0

    class Job:
        kill_on_close = True

        def __init__(self):
            self.closed = False

        def close(self):
            self.closed = True

    job = Job()
    fake_os = SimpleNamespace(
        name="nt",
        path=os.path,
        environ=os.environ,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
    )
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(process_module, "attach_process", lambda process: job)
    result = run_check_process(_spec(), timeout=1.0)
    assert result.status == "ERROR"
    assert job.closed is True

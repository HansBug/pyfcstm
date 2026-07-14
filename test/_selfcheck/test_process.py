"""Black-box process isolation tests for self-check workers."""

import os
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
    result = run_check_process(_spec(), timeout=0.4)
    assert result.status in ("TIMEOUT", "CRASH")
    assert child_pid_file.exists()
    child_pid = int(child_pid_file.read_text(encoding="ascii"))
    assert _wait_for_pid_exit(child_pid)


@pytest.mark.unittest
@pytest.mark.parametrize("scenario", ["huge_stderr", "huge_stdout"])
def test_stream_capture_is_bounded(monkeypatch, scenario):
    """Unbounded business output cannot exhaust supervisor memory."""
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
        stdin = type(
            "Input",
            (),
            {
                "write": lambda self, data: None,
                "flush": lambda self: None,
                "close": lambda self: None,
            },
        )()
        stdout = type("Output", (), {"read": lambda self, size: b""})()
        stderr = type("Output", (), {"read": lambda self, size: b""})()

        def wait(self, timeout=None):
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
def test_start_gate_write_is_independently_bounded():
    """A blocked or broken stdin writer cannot consume the worker deadline."""
    import threading

    release = threading.Event()

    class BlockingInput:
        def write(self, data):
            del data
            release.wait(2.0)

        def flush(self):
            return None

        def close(self):
            return None

    process = type("Process", (), {"stdin": BlockingInput()})()
    error, writer = process_module._send_start_gate(process, "4" * 32, 0.01)
    assert error == "start_gate_timeout"
    release.set()
    writer.join(timeout=1.0)

    class BrokenInput(BlockingInput):
        def write(self, data):
            del data
            raise OSError("closed")

    process.stdin = BrokenInput()
    error, writer = process_module._send_start_gate(process, "5" * 32, 1.0)
    writer.join(timeout=1.0)
    assert error == "start_gate_write:OSError"


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


@pytest.mark.unittest
def test_stream_reader_records_pipe_failure():
    """Reader failures become bounded diagnostics instead of thread crashes."""

    class BrokenStream:
        def read(self, size):
            del size
            raise OSError("closed")

    errors = []
    process_module._drain(BrokenStream(), _BoundedCapture(), errors)
    assert errors == ["stream_error:OSError"]


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
def test_start_gate_failure_retains_cleanup_evidence(monkeypatch):
    """A failed GO gate returns one structured error with cleanup diagnostics."""

    class Stream:
        @staticmethod
        def read(size):
            del size
            return b""

    class Process:
        pid = 29
        stdin = Stream()
        stdout = Stream()
        stderr = Stream()

    class GateThread:
        @staticmethod
        def join(timeout=None):
            del timeout

    monkeypatch.setattr(process_module.os, "name", "nt")
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: Process())
    monkeypatch.setattr(process_module, "attach_process", lambda process: object())
    monkeypatch.setattr(
        process_module,
        "_send_start_gate",
        lambda *args: ("gate failed", GateThread()),
    )
    monkeypatch.setattr(
        process_module, "_terminate", lambda *args, **kwargs: "cleanup failed"
    )
    result = run_check_process(_spec(), timeout=0.1)
    assert result.reason == "start_gate"
    assert "cleanup=cleanup failed" in result.evidence

"""Tests for fresh worker process lifecycle and bounded capture."""

import pytest


def _is_windows_isolation_error(result):
    """Return whether a Windows runner rejected nested Job Object assignment."""
    import os

    if os.name == "nt" and result.reason == "isolation_unavailable":
        assert result.status == "ERROR"
        return True
    return False


@pytest.mark.unittest
def test_artifact_self_dispatch_runs_in_fresh_process():
    """The real PR-2 check uses the current interpreter and returns PASS."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    result = run_check_process(
        CheckSpec("artifact.self_dispatch", "self_dispatch"), timeout=10.0
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"
    assert result.transport in ("file", "stdout")
    assert result.return_code == 0


@pytest.mark.unittest
def test_timeout_terminates_process_group(monkeypatch):
    """A hanging fixture is normalized to TIMEOUT without waiting forever."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "hang")
    result = run_check_process(CheckSpec("fixture.hang", "self_dispatch"), timeout=0.2)
    if _is_windows_isolation_error(result):
        return
    assert result.status == "TIMEOUT"


@pytest.mark.unittest
def test_temp_failure_uses_stdout_frame_fallback(monkeypatch):
    """When the session directory cannot be created, both sides use stdout mode."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    def fail_mkdtemp(*args, **kwargs):
        raise OSError("injected temp failure")

    monkeypatch.setattr("tempfile.mkdtemp", fail_mkdtemp)
    result = run_check_process(
        CheckSpec("artifact.self_dispatch", "self_dispatch"), timeout=10.0
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"
    assert result.transport == "stdout"


@pytest.mark.parametrize(
    ("mode", "status"),
    [
        ("crash", "CRASH"),
        ("abort", "CRASH"),
        ("system_exit", "ERROR"),
        ("keyboard_interrupt", "ERROR"),
        ("no_result", "ERROR"),
        ("truncated", "ERROR"),
        ("wrong_nonce", "ERROR"),
        ("duplicate", "ERROR"),
        ("malformed", "ERROR"),
    ],
)
@pytest.mark.unittest
def test_fault_modes_are_normalized_without_parent_crash(monkeypatch, mode, status):
    """Hard exits and protocol faults remain local to one check."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", mode)
    result = run_check_process(
        CheckSpec("fixture." + mode, "self_dispatch"), timeout=5.0
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == status


@pytest.mark.unittest
def test_stream_capture_is_bounded(monkeypatch):
    """Oversized stderr is drained and reported with truncation metadata."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "huge_output")
    result = run_check_process(
        CheckSpec("fixture.huge_output", "self_dispatch"), timeout=5.0
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"
    assert result.truncated_bytes > 0


@pytest.mark.unittest
def test_invalid_utf8_diagnostics_do_not_break_result(monkeypatch):
    """Invalid diagnostic bytes are preserved through backslash replacement."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "invalid_utf8")
    result = run_check_process(CheckSpec("fixture.invalid_utf8", "self_dispatch"), 5.0)
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"
    assert "\\xff" in result.details


@pytest.mark.unittest
def test_valid_envelope_is_authoritative_over_nonzero_return_code(monkeypatch):
    """A valid PASS envelope remains PASS while preserving the worker rc."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "nonzero_envelope")
    result = run_check_process(
        CheckSpec("fixture.nonzero_envelope", "self_dispatch"), 5.0
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"
    assert result.return_code == 7


@pytest.mark.unittest
def test_start_gate_write_has_an_independent_deadline():
    """A blocked stdin writer is bounded before the worker deadline."""
    import threading

    from pyfcstm._selfcheck.process import _send_start_gate

    release = threading.Event()

    class BlockingStdin:
        def write(self, data):
            del data
            release.wait(2.0)

        def flush(self):
            return None

        def close(self):
            return None

    class Process:
        stdin = BlockingStdin()

    error, writer = _send_start_gate(Process(), "4" * 32, 0.01)
    assert error == "start_gate_timeout"
    release.set()
    writer.join(timeout=1.0)


@pytest.mark.unittest
def test_start_gate_write_errors_are_normalized():
    """Broken stdin and close handles return a stable gate diagnostic."""
    from pyfcstm._selfcheck.process import _send_start_gate

    class BrokenStdin:
        def write(self, data):
            del data
            raise OSError("pipe")

        def flush(self):
            return None

        def close(self):
            raise OSError("closed")

    class Process:
        stdin = BrokenStdin()

    error, writer = _send_start_gate(Process(), "8" * 32, 1.0)
    writer.join(timeout=1.0)
    assert error.startswith("start_gate_write:")


@pytest.mark.unittest
def test_capture_handles_oversized_protocol_and_pending_data():
    """Protocol capture remains bounded even for an oversized frame line."""
    from pyfcstm._selfcheck.process import _BoundedCapture
    from pyfcstm._selfcheck.process import FRAME_PREFIX
    from pyfcstm._selfcheck.process import MAX_ENVELOPE_BYTES

    capture = _BoundedCapture(capture_protocol=True)
    capture.append(FRAME_PREFIX + b"x" * MAX_ENVELOPE_BYTES + b"\n")
    assert capture.protocol_frames
    capture.append(b"y" * (MAX_ENVELOPE_BYTES + 1))
    assert len(capture._protocol_pending) <= MAX_ENVELOPE_BYTES + 1


@pytest.mark.unittest
def test_stream_reader_records_pipe_errors():
    """Reader-thread pipe errors are converted into queue events."""
    import queue

    from pyfcstm._selfcheck.process import _BoundedCapture
    from pyfcstm._selfcheck.process import _drain

    class BrokenStream:
        def read(self, size):
            del size
            raise OSError("closed")

    events = queue.Queue()
    _drain(BrokenStream(), _BoundedCapture(), events)
    assert events.get_nowait().startswith("stream_error:")
    assert events.get_nowait() == "stream_done"


@pytest.mark.unittest
def test_worker_command_switches_to_frozen_dispatch(monkeypatch):
    """Frozen workers reuse the executable instead of importing as a module."""
    import sys

    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import _command_for_worker

    monkeypatch.setattr(sys, "frozen", True, raising=False)
    command = _command_for_worker(CheckSpec("demo", "demo"), "7" * 32, "stdout", None)
    assert "-m" not in command
    assert "--_pyfcstm-selfcheck-worker-v1" in command


@pytest.mark.unittest
def test_cleanup_failures_are_returned_as_diagnostics():
    """Termination failures do not escape the process supervisor."""
    from pyfcstm._selfcheck._win32 import JobAssignmentError
    from pyfcstm._selfcheck.process import _terminate

    class Job:
        def terminate(self, code):
            del code
            raise JobAssignmentError("injected")

        def close(self):
            return None

    class Process:
        pid = 1
        returncode = 1

        def terminate(self):
            return None

        def wait(self, timeout=None):
            del timeout
            return self.returncode

    assert "job_terminate" in (_terminate(Process(), Job(), False) or "")


@pytest.mark.unittest
def test_termination_fallback_paths_are_bounded(monkeypatch):
    """POSIX and non-POSIX fallback cleanup handles kill/wait failures."""
    import subprocess

    import pyfcstm._selfcheck.process as process_module

    class Process:
        pid = 9
        returncode = 1

        def __init__(self):
            self.wait_calls = 0

        def terminate(self):
            raise OSError("terminate")

        def kill(self):
            raise OSError("kill")

        def wait(self, timeout=None):
            del timeout
            self.wait_calls += 1
            if self.wait_calls == 1:
                raise subprocess.TimeoutExpired("worker", 0.1)
            raise ChildProcessError("gone")

    monkeypatch.setattr(
        process_module.os,
        "killpg",
        lambda *args: (_ for _ in ()).throw(OSError("killpg")),
        raising=False,
    )
    monkeypatch.setattr(
        process_module.signal,
        "SIGKILL",
        getattr(process_module.signal, "SIGTERM", 15),
        raising=False,
    )
    assert process_module._terminate(Process(), None, True) is not None
    assert process_module._terminate(Process(), None, False) is not None


@pytest.mark.unittest
def test_timeout_cleans_up_grandchild_on_posix(monkeypatch, tmp_path):
    """POSIX process-group cleanup removes a child spawned by a hanging worker."""
    import os
    import time

    if os.name != "posix":
        pytest.skip("POSIX process groups are tested on POSIX")
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    pid_file = tmp_path / "child.pid"
    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "spawn")
    monkeypatch.setenv("PYFCSTM_SELFCHECK_CHILD_PID_FILE", str(pid_file))
    result = run_check_process(CheckSpec("fixture.spawn", "self_dispatch"), 0.3)
    assert result.status == "TIMEOUT"
    child_pid = int(pid_file.read_text(encoding="ascii"))
    deadline = time.time() + 2.0
    while time.time() < deadline:
        try:
            os.kill(child_pid, 0)
        except OSError:
            break
        time.sleep(0.05)
    else:
        pytest.fail("spawned worker child survived timeout cleanup")


@pytest.mark.unittest
def test_protocol_frame_survives_oversized_business_stdout(monkeypatch):
    """Protocol parsing remains independent from the bounded business stream."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "huge_stdout")
    result = run_check_process(
        CheckSpec("fixture.huge_stdout", "self_dispatch"), timeout=5.0
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"
    assert result.truncated_bytes > 0


@pytest.mark.unittest
def test_spawn_failure_is_an_error(monkeypatch):
    """Popen errors are converted into one terminal result."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    def fail_popen(*args, **kwargs):
        raise OSError("injected spawn failure")

    monkeypatch.setattr("subprocess.Popen", fail_popen)
    result = run_check_process(CheckSpec("fixture.spawn", "self_dispatch"), timeout=1.0)
    assert result.status == "ERROR"

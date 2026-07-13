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

    result = run_check_process(
        CheckSpec("fixture.hang", "self_dispatch"), timeout=0.2, test_mode="hang"
    )
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


@pytest.mark.parametrize("mode", [None, "hang"])
@pytest.mark.unittest
def test_worker_session_files_are_removed_after_completion(monkeypatch, tmp_path, mode):
    """Normal and timeout paths remove result files and their private directory."""
    import tempfile

    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setattr(tempfile, "tempdir", str(tmp_path))
    result = run_check_process(
        CheckSpec("fixture.cleanup", "self_dispatch"),
        timeout=0.2 if mode else 5.0,
        test_mode=mode,
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status in ("PASS", "TIMEOUT")
    assert list(tmp_path.iterdir()) == []


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

    result = run_check_process(
        CheckSpec("fixture." + mode, "self_dispatch"), timeout=5.0, test_mode=mode
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == status


@pytest.mark.unittest
def test_stream_capture_is_bounded(monkeypatch):
    """Oversized stderr is drained and reported with truncation metadata."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    result = run_check_process(
        CheckSpec("fixture.huge_output", "self_dispatch"),
        timeout=5.0,
        test_mode="huge_output",
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

    result = run_check_process(
        CheckSpec("fixture.invalid_utf8", "self_dispatch"),
        5.0,
        test_mode="invalid_utf8",
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"
    assert "\\xff" in result.details


@pytest.mark.unittest
def test_valid_envelope_is_authoritative_over_nonzero_return_code(monkeypatch):
    """A valid PASS envelope remains PASS while preserving the worker rc."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    result = run_check_process(
        CheckSpec("fixture.nonzero_envelope", "self_dispatch"),
        5.0,
        test_mode="nonzero_envelope",
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
    capture.append(FRAME_PREFIX + b"y\n" * 20)
    assert len(capture.protocol_frames) <= 2
    capture.append(b"y" * (MAX_ENVELOPE_BYTES + 1))
    assert len(capture._protocol_pending) <= MAX_ENVELOPE_BYTES + 1


@pytest.mark.unittest
def test_capture_preserves_all_bytes_before_limit():
    """Streams below the cap retain their complete diagnostic payload."""
    from pyfcstm._selfcheck.process import _BoundedCapture

    capture = _BoundedCapture(limit=20)
    capture.append(b"abcdefghijklm")
    assert capture.truncated_bytes == 0
    assert capture.raw() == b"abcdefghijklm"


@pytest.mark.unittest
def test_stdout_protocol_frame_can_follow_unterminated_business_output():
    """Protocol extraction does not require business output to end in LF."""
    from pyfcstm._selfcheck.process import _BoundedCapture
    from pyfcstm._selfcheck.protocol import _decode_frame
    from pyfcstm._selfcheck.protocol import encode_result_frame

    nonce = "1" * 32
    frame = encode_result_frame(
        {
            "schema": "pyfcstm-selfcheck-worker/v1",
            "check_id": "fixture.stdout",
            "nonce": nonce,
            "status": "PASS",
        }
    )
    capture = _BoundedCapture(limit=128, capture_protocol=True)
    capture.append(b"business-output-without-lf" + frame)
    capture.finish()
    assert (
        _decode_frame(capture.protocol_bytes(), nonce, "fixture.stdout")["status"]
        == "PASS"
    )
    assert capture.raw() == b"business-output-without-lf"
    assert capture.truncated_bytes == 0


@pytest.mark.unittest
def test_protocol_capture_flushes_partial_and_oversized_frames():
    """EOF turns incomplete protocol candidates into bounded parse failures."""
    from pyfcstm._selfcheck.process import _BoundedCapture
    from pyfcstm._selfcheck.process import FRAME_PREFIX
    from pyfcstm._selfcheck.process import MAX_ENVELOPE_BYTES

    noise = _BoundedCapture(capture_protocol=True)
    noise.append(b"partial-noise")
    noise.finish()
    assert noise.raw() == b"partial-noise"

    partial = _BoundedCapture(capture_protocol=True)
    partial.append(b"prefix-noise" + FRAME_PREFIX + b"partial")
    partial.finish()
    assert partial.protocol_frames
    assert partial.raw() == b"prefix-noise"

    oversized = _BoundedCapture(capture_protocol=True)
    oversized.append(FRAME_PREFIX + b"x" * (MAX_ENVELOPE_BYTES + 2))
    assert oversized.protocol_frames
    assert len(oversized._protocol_pending) <= MAX_ENVELOPE_BYTES + 1


@pytest.mark.unittest
def test_windows_job_termination_waits_for_process_exit():
    """Job cleanup waits even when the native job path reports success."""
    from pyfcstm._selfcheck.process import _terminate

    calls = []

    class Job:
        def terminate(self, code):
            calls.append(("job_terminate", code))

        def close(self):
            calls.append(("job_close",))

    class Process:
        pid = 11

        def wait(self, timeout=None):
            calls.append(("wait", timeout))
            return 0

        def kill(self):
            calls.append(("kill",))

    assert _terminate(Process(), Job(), False) is None
    assert [item[0] for item in calls] == ["job_terminate", "job_close", "wait"]


@pytest.mark.unittest
def test_keyboard_interrupt_terminates_started_worker(monkeypatch):
    """A parent interrupt cleans the worker before propagating to supervisor."""
    import os
    from types import SimpleNamespace

    import pyfcstm._selfcheck.process as process_module
    from pyfcstm._selfcheck.model import CheckSpec

    class Stream:
        def read(self, size):
            del size
            return b""

    class Process:
        pid = 4242
        returncode = None
        stdin = Stream()
        stdout = Stream()
        stderr = Stream()

    process = Process()
    fake_os = SimpleNamespace(
        name="posix",
        path=os.path,
        environ=os.environ,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
        killpg=lambda *args: None,
    )
    terminated = []
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(
        process_module,
        "_send_start_gate",
        lambda *args: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr(
        process_module,
        "_terminate",
        lambda *args, **kwargs: terminated.append(args) or None,
    )
    with pytest.raises(KeyboardInterrupt):
        process_module.run_check_process(
            CheckSpec("fixture.interrupt", "self_dispatch"), timeout=1.0
        )
    assert terminated and terminated[0][0] is process


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
def test_stale_test_mode_environment_is_not_forwarded(monkeypatch):
    """A caller's test-injection environment cannot alter a production run."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.process import run_check_process

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "hang")
    result = run_check_process(
        CheckSpec("fixture.stale_mode", "self_dispatch"), timeout=2.0
    )
    if _is_windows_isolation_error(result):
        return
    assert result.status == "PASS"


@pytest.mark.parametrize("error_type", [OSError, MemoryError, RuntimeError])
@pytest.mark.unittest
def test_native_attach_error_terminates_started_worker(monkeypatch, error_type):
    """Native setup failures still terminate the already-created worker."""
    import os
    from types import SimpleNamespace

    import pyfcstm._selfcheck.process as process_module
    from pyfcstm._selfcheck.model import CheckSpec

    class Stream:
        def read(self, size):
            del size
            return b""

    class Process:
        pid = 4242
        returncode = None

        def __init__(self):
            self.calls = []
            self.stdin = Stream()
            self.stdout = Stream()
            self.stderr = Stream()

        def terminate(self):
            self.calls.append("terminate")

        def kill(self):
            self.calls.append("kill")

        def wait(self, timeout=None):
            self.calls.append(("wait", timeout))
            self.returncode = 1
            return 1

    process = Process()
    fake_os = SimpleNamespace(
        name="nt",
        path=os.path,
        unlink=os.unlink,
        rmdir=os.rmdir,
        write=os.write,
        environ=os.environ,
    )
    monkeypatch.setattr(process_module, "os", fake_os)
    monkeypatch.setattr(process_module.subprocess, "Popen", lambda *a, **k: process)
    monkeypatch.setattr(
        process_module,
        "attach_process",
        lambda child: (_ for _ in ()).throw(error_type("native attach")),
    )
    result = process_module.run_check_process(
        CheckSpec("fixture.native", "self_dispatch"), timeout=0.1
    )
    assert result.status == "ERROR"
    assert result.reason == "isolation_unavailable"
    assert "terminate" in process.calls


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
def test_explicit_job_cleanup_terminates_before_close():
    """Windows 7 fallback cleanup terminates descendants on normal return."""
    from pyfcstm._selfcheck.process import _close_job

    calls = []

    class Job:
        kill_on_close = False

        def terminate(self, code):
            calls.append(("terminate", code))

        def close(self):
            calls.append(("close",))

    assert _close_job(Job()) is None
    assert calls == [("terminate", 1), ("close",)]


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
    monkeypatch.setenv("PYFCSTM_SELFCHECK_CHILD_PID_FILE", str(pid_file))
    result = run_check_process(
        CheckSpec("fixture.spawn", "self_dispatch"), 0.3, test_mode="spawn"
    )
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

    result = run_check_process(
        CheckSpec("fixture.huge_stdout", "self_dispatch"),
        timeout=5.0,
        test_mode="huge_stdout",
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

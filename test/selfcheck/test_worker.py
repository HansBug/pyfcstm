"""Tests for hidden worker execution and result submission."""

import io
import json

import pytest


@pytest.mark.unittest
def test_worker_passes_start_gate_and_writes_stdout_frame(monkeypatch):
    """A registered worker emits one valid frame after the exact GO bytes."""
    from pyfcstm._selfcheck.worker import run_worker

    nonce = "0" * 32
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    output = io.BytesIO()
    monkeypatch.setattr("sys.stdout", io.TextIOWrapper(output, write_through=True))
    code = run_worker(
        {
            "check_id": "artifact.self_dispatch",
            "worker_key": "self_dispatch",
            "nonce": nonce,
            "result_mode": "stdout",
        }
    )
    assert code == 0
    payload = json.loads(output.getvalue().split(b" ", 1)[1])
    assert payload["status"] == "PASS"


@pytest.mark.unittest
def test_worker_system_exit_is_an_error_envelope(monkeypatch, tmp_path):
    """Worker exceptions become detailed ERROR envelopes rather than crashes."""
    from pyfcstm._selfcheck import registry
    from pyfcstm._selfcheck.protocol import read_result_file
    from pyfcstm._selfcheck.worker import run_worker

    registry.register_test_override(
        "system_exit", lambda: (_ for _ in ()).throw(SystemExit(7))
    )
    nonce = "1" * 32
    result_file = tmp_path / "result.log"
    result_file.touch()
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    code = run_worker(
        {
            "check_id": "fixture.system_exit",
            "worker_key": "system_exit",
            "nonce": nonce,
            "result_mode": "file",
            "result_file": str(result_file),
        }
    )
    assert code == 7
    outcome = read_result_file(str(result_file), nonce)
    assert outcome.envelope["status"] == "ERROR"
    assert outcome.envelope["return_code"] == 7


@pytest.mark.unittest
def test_worker_keyboard_interrupt_is_an_error_envelope(monkeypatch, tmp_path):
    """KeyboardInterrupt is serialized before the worker exits."""
    from pyfcstm._selfcheck import registry
    from pyfcstm._selfcheck.protocol import read_result_file
    from pyfcstm._selfcheck.worker import run_worker

    registry.register_test_override(
        "keyboard_interrupt", lambda: (_ for _ in ()).throw(KeyboardInterrupt())
    )
    nonce = "b" * 32
    result_file = tmp_path / "result.log"
    result_file.touch()
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    code = run_worker(
        {
            "check_id": "fixture.keyboard_interrupt",
            "worker_key": "keyboard_interrupt",
            "nonce": nonce,
            "result_mode": "file",
            "result_file": str(result_file),
        }
    )
    assert code == 130
    assert read_result_file(str(result_file), nonce).envelope["return_code"] == 130


@pytest.mark.unittest
def test_worker_protocol_failures_are_reported(monkeypatch, tmp_path):
    """Invalid nonce, gate, and worker key never execute a check."""
    from pyfcstm._selfcheck.protocol import read_result_file
    from pyfcstm._selfcheck.worker import run_worker

    assert (
        run_worker(
            {
                "check_id": "demo",
                "worker_key": "self_dispatch",
                "nonce": "bad",
                "result_mode": "stdout",
            }
        )
        == 3
    )
    nonce = "2" * 32
    result_file = tmp_path / "result.log"
    result_file.touch()
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"WRONG\n")))
    assert (
        run_worker(
            {
                "check_id": "demo",
                "worker_key": "self_dispatch",
                "nonce": nonce,
                "result_mode": "file",
                "result_file": str(result_file),
            }
        )
        == 3
    )
    assert read_result_file(str(result_file), nonce).envelope["status"] == "ERROR"


@pytest.mark.unittest
def test_worker_start_gate_read_errors_are_normalized(monkeypatch):
    """A broken stdin stream is distinguishable from a nonce mismatch."""
    from pyfcstm._selfcheck.worker import _read_start_gate

    class BrokenBuffer:
        def readline(self, size):
            del size
            raise OSError("closed")

    class Input:
        buffer = BrokenBuffer()

    monkeypatch.setattr("sys.stdin", Input())
    assert _read_start_gate("9" * 32, timeout=1.0).startswith("start_gate_read:")


@pytest.mark.unittest
def test_worker_start_gate_read_has_a_deadline(monkeypatch):
    """A worker invoked without input does not block forever in the gate."""
    import threading

    from pyfcstm._selfcheck.worker import _read_start_gate

    release = threading.Event()

    class BlockingBuffer:
        def readline(self, size):
            del size
            release.wait(2.0)
            return b""

    class Input:
        buffer = BlockingBuffer()

    monkeypatch.setattr("sys.stdin", Input())
    assert _read_start_gate("5" * 32, timeout=0.01) == "start_gate_timeout"
    release.set()


@pytest.mark.unittest
def test_worker_write_failures_are_reported(monkeypatch):
    """Missing file targets and broken stdout are protocol diagnostics."""
    from pyfcstm._selfcheck.worker import _write_frame

    assert _write_frame("file", None, b"frame") == "missing_result_file"

    class BrokenBuffer:
        def write(self, data):
            del data
            raise OSError("closed")

        def flush(self):
            return None

    class BrokenStdout:
        buffer = BrokenBuffer()

    monkeypatch.setattr("sys.stdout", BrokenStdout())
    assert _write_frame("stdout", None, b"frame").startswith("result_write:")


@pytest.mark.unittest
def test_file_frame_transport_requests_binary_mode(monkeypatch):
    """Windows text-mode translation cannot alter the fixed LF byte."""
    import os

    from pyfcstm._selfcheck.worker import _write_frame

    calls = []
    monkeypatch.setattr("os.open", lambda path, flags: calls.append((path, flags)) or 9)
    monkeypatch.setattr("os.write", lambda descriptor, data: len(data))
    monkeypatch.setattr("os.fsync", lambda descriptor: None)
    monkeypatch.setattr("os.close", lambda descriptor: None)
    assert _write_frame("file", "result.log", b"frame") is None
    assert calls[0][1] & getattr(os, "O_BINARY", 0) == getattr(os, "O_BINARY", 0)


@pytest.mark.unittest
def test_worker_survives_faulthandler_registration_failure(monkeypatch, tmp_path):
    """Unsupported stderr streams do not prevent a valid result envelope."""
    from pyfcstm._selfcheck.protocol import read_result_file
    from pyfcstm._selfcheck.worker import run_worker

    monkeypatch.setattr(
        "faulthandler.enable",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("unsupported")),
    )
    nonce = "6" * 32
    result_file = tmp_path / "result.log"
    result_file.touch()
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    assert (
        run_worker(
            {
                "check_id": "fixture.faulthandler",
                "worker_key": "self_dispatch",
                "nonce": nonce,
                "result_mode": "file",
                "result_file": str(result_file),
            }
        )
        == 0
    )
    assert read_result_file(str(result_file), nonce).envelope["status"] == "PASS"


@pytest.mark.parametrize(
    "mode",
    [
        "warn",
        "duplicate",
        "wrong_nonce",
        "malformed",
        "no_result",
        "truncated",
        "nonzero_envelope",
    ],
)
@pytest.mark.unittest
def test_worker_injected_modes_are_exercisable_in_process(monkeypatch, tmp_path, mode):
    """Direct worker tests cover protocol branches before subprocess classification."""
    from pyfcstm._selfcheck.protocol import read_result_file
    from pyfcstm._selfcheck.worker import run_worker

    nonce = "3" * 32
    result_file = tmp_path / (mode + ".log")
    result_file.touch()
    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", mode)
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    code = run_worker(
        {
            "check_id": "fixture." + mode,
            "worker_key": "self_dispatch",
            "nonce": nonce,
            "result_mode": "file",
            "result_file": str(result_file),
        }
    )
    assert code == (
        7 if mode == "nonzero_envelope" else 3 if mode == "truncated" else 0
    )
    if mode == "warn":
        assert read_result_file(str(result_file), nonce).envelope["status"] == "WARN"
    elif mode == "nonzero_envelope":
        assert read_result_file(str(result_file), nonce).envelope["status"] == "PASS"
    else:
        assert read_result_file(str(result_file), nonce).error_code is not None


@pytest.mark.unittest
def test_worker_unknown_key_and_exception_are_enveloped(monkeypatch, tmp_path):
    """Unknown registry keys and ordinary exceptions remain detailed errors."""
    from pyfcstm._selfcheck import registry
    from pyfcstm._selfcheck.protocol import read_result_file
    from pyfcstm._selfcheck.worker import run_worker

    nonce = "4" * 32
    result_file = tmp_path / "result.log"
    result_file.touch()
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    assert (
        run_worker(
            {
                "check_id": "fixture.unknown",
                "worker_key": "missing",
                "nonce": nonce,
                "result_mode": "file",
                "result_file": str(result_file),
            }
        )
        == 3
    )
    result_file.unlink()
    result_file.touch()
    registry.register_test_override(
        "ordinary_error", lambda: (_ for _ in ()).throw(ValueError("bad"))
    )
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    assert (
        run_worker(
            {
                "check_id": "fixture.error",
                "worker_key": "ordinary_error",
                "nonce": nonce,
                "result_mode": "file",
                "result_file": str(result_file),
            }
        )
        == 1
    )
    assert read_result_file(str(result_file), nonce).envelope["status"] == "ERROR"


@pytest.mark.parametrize("mode", ["crash", "abort"])
@pytest.mark.unittest
def test_worker_hard_exit_paths_reach_isolation_boundary(monkeypatch, mode):
    """Hard-exit calls are intentionally outside the worker envelope catch."""
    from pyfcstm._selfcheck.worker import run_worker

    nonce = "a" * 32
    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", mode)
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    if mode == "crash":
        monkeypatch.setattr(
            "os._exit", lambda code: (_ for _ in ()).throw(RuntimeError(code))
        )
    else:
        monkeypatch.setattr(
            "os.abort", lambda: (_ for _ in ()).throw(RuntimeError("abort"))
        )
    with pytest.raises(RuntimeError):
        run_worker(
            {
                "check_id": "fixture." + mode,
                "worker_key": "self_dispatch",
                "nonce": nonce,
                "result_mode": "stdout",
            }
        )

"""Contract tests for the hidden one-shot self-check worker."""

import io
import os
from types import SimpleNamespace

import pytest

from pyfcstm._selfcheck.model import CheckOutcome
from pyfcstm._selfcheck.protocol import read_result_file, read_stdout_frames
from pyfcstm._selfcheck import registry
from pyfcstm._selfcheck import worker as worker_module
from pyfcstm._selfcheck.worker import _read_start_gate, _write_frame, run_worker


@pytest.fixture(autouse=True)
def isolated_worker_os(monkeypatch):
    """Keep worker transport fault injection away from the interpreter-wide ``os``."""
    isolated_os = SimpleNamespace(**vars(worker_module.os))
    monkeypatch.setattr(worker_module, "os", isolated_os)
    return isolated_os


@pytest.mark.unittest
def test_worker_os_fault_injection_is_module_local(monkeypatch):
    """Worker transport fault injection never replaces global ``os`` functions."""
    original_write = os.write
    monkeypatch.setattr(worker_module.os, "write", lambda descriptor, data: 0)
    assert os.write is original_write


def _arguments(nonce, mode="stdout", result_file=None, worker_key="test_pass"):
    return {
        "check_id": "fixture.worker",
        "worker_key": worker_key,
        "nonce": nonce,
        "result_mode": mode,
        "result_file": result_file,
    }


def _install_streams(monkeypatch, nonce):
    output = io.BytesIO()
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    monkeypatch.setattr("sys.stdout", io.TextIOWrapper(output, write_through=True))
    return output


def _register(monkeypatch, worker_key, worker):
    monkeypatch.setitem(registry._WORKERS, worker_key, worker)


@pytest.mark.unittest
def test_worker_writes_typed_pass_outcome(monkeypatch):
    """A typed callback produces one nonce-bound authoritative frame."""
    nonce = "1" * 32
    output = _install_streams(monkeypatch, nonce)
    _register(
        monkeypatch,
        "test_pass",
        lambda: CheckOutcome(
            "PASS",
            "worker ready",
            expected="typed outcome",
            observed="typed outcome",
        ),
    )

    assert run_worker(_arguments(nonce)) == 0
    result = read_stdout_frames(output.getvalue(), nonce, "fixture.worker")
    assert result.error_code is None
    assert result.envelope["status"] == "PASS"
    assert result.envelope["expected"] == "typed outcome"


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("worker_key", "factory", "reason", "return_code"),
    [
        (
            "test_system_exit",
            lambda: (_ for _ in ()).throw(SystemExit(7)),
            "worker_system_exit",
            7,
        ),
        (
            "test_keyboard_interrupt",
            lambda: (_ for _ in ()).throw(KeyboardInterrupt()),
            "worker_interrupted",
            130,
        ),
        (
            "test_exception",
            lambda: (_ for _ in ()).throw(RuntimeError("boom")),
            "worker_exception",
            1,
        ),
        (
            "test_invalid_type",
            lambda: "not typed",
            "worker_exception",
            1,
        ),
    ],
)
def test_worker_converts_callback_failures_to_error_frames(
    monkeypatch, worker_key, factory, reason, return_code
):
    """Callback control/error paths remain structured protocol outcomes."""
    nonce = "2" * 32
    output = _install_streams(monkeypatch, nonce)
    _register(monkeypatch, worker_key, factory)

    assert run_worker(_arguments(nonce, worker_key=worker_key)) == return_code
    result = read_stdout_frames(output.getvalue(), nonce, "fixture.worker")
    assert result.envelope["status"] == "ERROR"
    assert result.envelope["reason"] == reason
    assert "Traceback" in result.envelope["exception"]


@pytest.mark.unittest
def test_worker_reports_unknown_static_key(monkeypatch):
    """The hidden CLI never resolves arbitrary module or callable paths."""
    nonce = "3" * 32
    output = _install_streams(monkeypatch, nonce)

    assert run_worker(_arguments(nonce, worker_key="missing")) == 3
    result = read_stdout_frames(output.getvalue(), nonce, "fixture.worker")
    assert result.envelope["reason"] == "unknown_worker"


@pytest.mark.unittest
@pytest.mark.parametrize(
    "payload",
    [b"WRONG\n", b"GO " + b"4" * 32 + b"\ntrailing"],
)
def test_start_gate_rejects_mismatch_and_trailing_data(monkeypatch, payload):
    """A worker cannot execute before one exact containment gate."""
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(payload)))
    assert _read_start_gate("4" * 32) in (
        "start_gate_mismatch",
        "start_gate_trailing_data",
    )


@pytest.mark.unittest
def test_start_gate_read_does_not_create_a_thread(monkeypatch):
    """The hidden worker reads its one gate synchronously."""

    class ForbiddenThreading:
        @staticmethod
        def Thread(*args, **kwargs):
            del args, kwargs
            raise AssertionError("self-check created a thread")

    nonce = "9" * 32
    monkeypatch.setattr(
        "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
    )
    monkeypatch.setattr(worker_module, "threading", ForbiddenThreading(), raising=False)
    assert _read_start_gate(nonce) is None


@pytest.mark.unittest
def test_worker_start_gate_failure_is_an_error_frame(monkeypatch):
    """Gate failures remain observable when the result channel is usable."""
    nonce = "5" * 32
    output = io.BytesIO()
    monkeypatch.setattr("sys.stdin", io.TextIOWrapper(io.BytesIO(b"WRONG\n")))
    monkeypatch.setattr("sys.stdout", io.TextIOWrapper(output, write_through=True))

    assert run_worker(_arguments(nonce)) == 3
    result = read_stdout_frames(output.getvalue(), nonce, "fixture.worker")
    assert result.envelope["status"] == "ERROR"
    assert result.envelope["reason"] == "start_gate_mismatch"


@pytest.mark.unittest
def test_worker_start_gate_read_failure_is_reported(monkeypatch):
    """A closed worker stdin produces a typed protocol error."""
    nonce = "5" * 32
    output = io.BytesIO()

    class BrokenBuffer:
        def read(self, size):
            del size
            raise OSError("stdin closed")

    class BrokenStdin:
        buffer = BrokenBuffer()

    monkeypatch.setattr("sys.stdin", BrokenStdin())
    monkeypatch.setattr("sys.stdout", io.TextIOWrapper(output, write_through=True))
    assert run_worker(_arguments(nonce)) == 3
    result = read_stdout_frames(output.getvalue(), nonce, "fixture.worker")
    assert result.envelope["reason"].startswith("start_gate_read:")


@pytest.mark.unittest
def test_worker_file_transport_appends_one_frame(monkeypatch, tmp_path):
    """File transport remains append-only and fsynced by the worker."""
    nonce = "6" * 32
    result_file = tmp_path / "result.log"
    result_file.write_bytes(b"")
    _install_streams(monkeypatch, nonce)
    _register(monkeypatch, "test_file", lambda: CheckOutcome("WARN", "optional"))

    assert (
        run_worker(_arguments(nonce, "file", str(result_file), worker_key="test_file"))
        == 0
    )
    result = read_result_file(str(result_file), nonce, "fixture.worker")
    assert result.envelope["status"] == "WARN"


@pytest.mark.unittest
def test_worker_result_write_failure_is_reported(monkeypatch, capfd):
    """A broken result transport returns infrastructure code 3 and evidence."""
    nonce = "7" * 32
    with monkeypatch.context() as worker_patch:
        _install_streams(worker_patch, nonce)
        _register(worker_patch, "test_write", lambda: CheckOutcome("PASS", "ready"))
        worker_patch.setattr(
            "pyfcstm._selfcheck.worker._write_frame",
            lambda mode, path, frame: "result_write:OSError",
        )

        assert run_worker(_arguments(nonce, worker_key="test_write")) == 3
    assert "result_write:OSError" in capfd.readouterr().err


@pytest.mark.unittest
def test_worker_file_mode_requires_a_result_path(monkeypatch, capfd):
    """The public worker rejects file transport without a destination."""
    nonce = "7" * 32
    with monkeypatch.context() as worker_patch:
        output = _install_streams(worker_patch, nonce)
        _register(
            worker_patch,
            "test_missing_file",
            lambda: CheckOutcome("PASS", "ready"),
        )
        arguments = _arguments(
            nonce,
            mode="file",
            result_file=None,
            worker_key="test_missing_file",
        )
        assert run_worker(arguments) == 3
        assert output.getvalue() == b""
    assert "missing_result_file" in capfd.readouterr().err


@pytest.mark.unittest
def test_worker_stdout_write_failure_is_reported(monkeypatch, capfd):
    """A broken stdout transport is normalized without raising."""
    nonce = "8" * 32

    class BrokenBuffer:
        def write(self, value):
            del value
            raise OSError("stdout closed")

        def flush(self):
            raise OSError("stdout closed")

    class BrokenStdout:
        buffer = BrokenBuffer()

    with monkeypatch.context() as worker_patch:
        worker_patch.setattr(
            "sys.stdin", io.TextIOWrapper(io.BytesIO(b"GO " + nonce.encode() + b"\n"))
        )
        worker_patch.setattr("sys.stdout", BrokenStdout())
        _register(
            worker_patch,
            "test_stdout_failure",
            lambda: CheckOutcome("PASS", "ready"),
        )
        assert run_worker(_arguments(nonce, worker_key="test_stdout_failure")) == 3
    assert "result_write:OSError" in capfd.readouterr().err


@pytest.mark.unittest
def test_worker_error_channel_failure_still_returns_protocol_exit(monkeypatch):
    """A broken stderr does not turn a transport error into an exception."""
    nonce = "8" * 32
    _install_streams(monkeypatch, nonce)
    _register(monkeypatch, "test_error_channel", lambda: CheckOutcome("PASS", "ready"))
    monkeypatch.setattr(worker_module, "_write_frame", lambda *args: "write failed")
    monkeypatch.setattr(
        worker_module.os,
        "write",
        lambda descriptor, data: (_ for _ in ()).throw(OSError("stderr closed")),
    )
    assert run_worker(_arguments(nonce, worker_key="test_error_channel")) == 3


@pytest.mark.unittest
def test_worker_survives_faulthandler_registration_failure(monkeypatch):
    """Restricted stderr does not prevent a valid result frame."""
    nonce = "8" * 32
    output = _install_streams(monkeypatch, nonce)
    _register(monkeypatch, "test_faulthandler", lambda: CheckOutcome("PASS", "ok"))
    monkeypatch.setattr(
        "faulthandler.enable",
        lambda **kwargs: (_ for _ in ()).throw(RuntimeError("restricted")),
    )

    assert run_worker(_arguments(nonce, worker_key="test_faulthandler")) == 0
    assert read_stdout_frames(output.getvalue(), nonce).envelope["status"] == "PASS"


@pytest.mark.unittest
def test_file_frame_transport_requests_binary_append_mode(monkeypatch):
    """Windows file transport requests binary append semantics."""
    calls = []
    monkeypatch.setattr(
        worker_module.os, "open", lambda path, flags: calls.append(flags) or 9
    )
    monkeypatch.setattr(worker_module.os, "write", lambda descriptor, data: len(data))
    monkeypatch.setattr(worker_module.os, "fsync", lambda descriptor: None)
    monkeypatch.setattr(worker_module.os, "close", lambda descriptor: None)

    assert _write_frame("file", "result.log", b"frame") is None
    assert calls and calls[0] & getattr(__import__("os"), "O_APPEND")


@pytest.mark.unittest
def test_worker_frame_transport_retries_short_writes(monkeypatch):
    """File transport waits for every frame byte after a short native write."""
    writes = []

    def short_write(descriptor, data):
        del descriptor
        writes.append(bytes(data))
        return 1

    monkeypatch.setattr(worker_module.os, "open", lambda path, flags: 9)
    monkeypatch.setattr(worker_module.os, "write", short_write)
    monkeypatch.setattr(worker_module.os, "fsync", lambda descriptor: None)
    monkeypatch.setattr(worker_module.os, "close", lambda descriptor: None)

    assert _write_frame("file", "result.log", b"frame") is None
    assert b"".join(chunk[:1] for chunk in writes) == b"frame"


@pytest.mark.unittest
def test_public_worker_reports_short_stdout_write(monkeypatch):
    """The hidden worker converts an unavailable stdout transport to exit 3."""
    nonce = "5" * 32
    _install_streams(monkeypatch, nonce)
    _register(
        monkeypatch,
        "test_short_stdout",
        lambda: CheckOutcome("PASS", "worker ready"),
    )

    class ShortBuffer:
        def write(self, data):
            del data
            return 0

        def flush(self):
            return None

    monkeypatch.setattr(
        "sys.stdout", type("BrokenStdout", (), {"buffer": ShortBuffer()})()
    )
    monkeypatch.setattr(worker_module.os, "write", lambda descriptor, data: len(data))
    assert run_worker(_arguments(nonce, worker_key="test_short_stdout")) == 3


@pytest.mark.unittest
def test_public_worker_reports_short_file_write(monkeypatch, tmp_path):
    """The hidden worker converts an unavailable file transport to exit 3."""
    nonce = "6" * 32
    _install_streams(monkeypatch, nonce)
    _register(
        monkeypatch,
        "test_short_file",
        lambda: CheckOutcome("PASS", "worker ready"),
    )
    monkeypatch.setattr(worker_module.os, "write", lambda descriptor, data: 0)

    result_file = str(tmp_path / "result.log")
    assert (
        run_worker(
            _arguments(
                nonce,
                mode="file",
                result_file=result_file,
                worker_key="test_short_file",
            )
        )
        == 3
    )


@pytest.mark.unittest
def test_worker_rejects_invalid_nonce_before_start_gate(monkeypatch):
    """Malformed nonce input never reaches stdin or a callback."""
    assert run_worker(_arguments("invalid")) == 3


@pytest.mark.unittest
def test_worker_preserves_generator_exit_from_callback(monkeypatch):
    """Non-runtime callback sentinels are not converted to error envelopes."""
    nonce = "9" * 32
    _install_streams(monkeypatch, nonce)
    _register(
        monkeypatch,
        "test_generator_exit",
        lambda: (_ for _ in ()).throw(GeneratorExit()),
    )
    with pytest.raises(GeneratorExit):
        run_worker(_arguments(nonce, worker_key="test_generator_exit"))

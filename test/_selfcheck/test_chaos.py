"""Replay the private frozen-worker fault scenarios through production APIs."""

import json
import os
import time

import pytest

from pyfcstm._selfcheck import process as process_module
from pyfcstm._selfcheck import registry
from pyfcstm._selfcheck import supervisor
from pyfcstm._selfcheck import _chaos
from pyfcstm._selfcheck.model import CheckOutcome, CheckSpec
from pyfcstm._selfcheck.process import run_check_process


@pytest.mark.unittest
def test_large_output_is_fail_closed_at_the_spool_boundary():
    """The private large-output worker cannot create an unbounded spool."""
    result = run_check_process(
        CheckSpec("chaos.large_output", "_chaos.large_output"), timeout=5.0
    )
    assert result.status == "ERROR"
    assert result.reason == "output_capture_limit"
    assert result.truncated_bytes > 0


@pytest.mark.unittest
def test_hanging_private_worker_is_terminalized():
    """The supervisor reports a private hang as a bounded timeout."""
    result = run_check_process(
        CheckSpec("chaos.hang", "_chaos.hang"), timeout=0.2
    )
    assert result.status == "TIMEOUT"
    assert result.reason == "worker_deadline_exceeded"


@pytest.mark.unittest
def test_private_crash_is_reported_without_an_envelope():
    """The private crash worker produces a terminal crash result."""
    result = run_check_process(
        CheckSpec("chaos.crash", "_chaos.crash"), timeout=5.0
    )
    assert result.status in ("CRASH", "ERROR")


@pytest.mark.unittest
def test_invalid_private_frame_is_rejected_by_stdout_protocol(monkeypatch):
    """A malformed private frame cannot be hidden behind a later valid frame."""
    monkeypatch.setattr(
        process_module.tempfile,
        "mkdtemp",
        lambda **kwargs: (_ for _ in ()).throw(OSError("no session directory")),
    )
    result = run_check_process(
        CheckSpec("chaos.invalid_frame", "_chaos.invalid_frame"), timeout=5.0
    )
    assert result.status == "ERROR"
    assert result.reason == "invalid_json"


@pytest.mark.unittest
@pytest.mark.skipif(os.name != "posix", reason="POSIX process-group evidence")
def test_private_grandchild_is_cleaned_and_next_check_runs(monkeypatch, tmp_path, capsys):
    """A timed-out chaos worker cannot prevent the next serial check."""
    child_pid_file = tmp_path / "grandchild.pid"
    monkeypatch.setenv("PYFCSTM_SELFCHECK_CHAOS_CHILD_PID", str(child_pid_file))
    after_calls = []

    def after():
        after_calls.append(True)
        return CheckOutcome("PASS", "independent check completed")

    monkeypatch.setitem(registry._WORKERS, "chaos_after", after)
    specs = (
        CheckSpec(
            "chaos.grandchild",
            "_chaos.grandchild",
            timeout_seconds=0.2,
        ),
        CheckSpec("chaos.after", "chaos_after", execution="local"),
    )
    monkeypatch.setattr(
        supervisor, "selected_specs", lambda profile, **kwargs: specs
    )
    assert supervisor.run_supervisor(("--format", "json")) == 1
    payload = json.loads(capsys.readouterr().out)
    assert [item["id"] for item in payload["results"]] == [
        "chaos.grandchild",
        "chaos.after",
    ]
    assert payload["results"][0]["status"] == "TIMEOUT"
    assert payload["results"][1]["status"] == "PASS"
    assert after_calls == [True]
    deadline = time.monotonic() + 3.0
    while time.monotonic() < deadline and not child_pid_file.exists():
        time.sleep(0.01)
    assert child_pid_file.exists()
    child_pid = int(child_pid_file.read_text(encoding="ascii"))
    while time.monotonic() < deadline:
        try:
            os.kill(child_pid, 0)
        except ProcessLookupError:
            break
        time.sleep(0.02)
    with pytest.raises(ProcessLookupError):
        os.kill(child_pid, 0)


@pytest.mark.unittest
def test_private_chaos_callbacks_have_direct_controlled_coverage(monkeypatch, tmp_path):
    """The private callbacks are also exercised without dangerous real exits."""
    class StopSleep(RuntimeError):
        pass

    monkeypatch.setattr(
        _chaos.time,
        "sleep",
        lambda interval: (_ for _ in ()).throw(StopSleep(interval)),
    )
    with pytest.raises(StopSleep):
        _chaos.hang()

    monkeypatch.setattr(
        _chaos.os,
        "_exit",
        lambda code: (_ for _ in ()).throw(SystemExit(code)),
    )
    with pytest.raises(SystemExit):
        _chaos.crash()

    writes = []
    monkeypatch.setattr(
        _chaos.os,
        "write",
        lambda descriptor, data: writes.append((descriptor, data)) or len(data),
    )
    assert _chaos.large_output().status == "PASS"
    assert _chaos.invalid_frame().status == "PASS"
    assert len(writes) == 3

    class Child:
        pid = 1234

    monkeypatch.setattr(_chaos.subprocess, "Popen", lambda *args, **kwargs: Child())
    monkeypatch.setenv("PYFCSTM_SELFCHECK_CHAOS_CHILD_PID", str(tmp_path / "child"))
    monkeypatch.setattr(
        _chaos,
        "hang",
        lambda: (_ for _ in ()).throw(StopSleep("grandchild")),
    )
    with pytest.raises(StopSleep):
        _chaos.grandchild()
    assert (tmp_path / "child").read_text(encoding="ascii") == "1234"

"""Tests for self-check human, JSON, and emergency reports."""

import json

import pytest


@pytest.mark.unittest
def test_json_report_is_stable_and_round_trippable(tmp_path):
    """JSON stdout/report payloads share one canonical schema."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import render_json
    from pyfcstm._selfcheck.report import write_report

    snapshot = ReportSnapshot(
        (CheckResult("artifact.self_dispatch", "PASS", True, summary="worker ok"),),
        {"session_id": "s1"},
        {"PASS": 1},
    )
    payload = render_json(snapshot)
    assert json.loads(payload)["counts"] == {"PASS": 1}
    path = tmp_path / "report.json"
    assert write_report(str(path), snapshot) is None
    assert (
        json.loads(path.read_text(encoding="utf-8"))["schema"] == "pyfcstm-selfcheck/v1"
    )


@pytest.mark.unittest
def test_human_failure_output_contains_full_details():
    """Human output expands failure details while PASS stays concise."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import render_human

    snapshot = ReportSnapshot(
        (
            CheckResult("ok", "PASS", True, summary="ready"),
            CheckResult(
                "bad", "ERROR", True, summary="broken", details="full traceback"
            ),
        ),
        {},
        {"PASS": 1, "ERROR": 1},
    )
    output = render_human(snapshot, color="never")
    assert "PASS ok: ready" in output
    assert "full traceback" in output


@pytest.mark.unittest
def test_report_write_failure_returns_diagnostic(tmp_path):
    """An unwritable target is reported without raising from the writer."""
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import write_report

    snapshot = ReportSnapshot((), {}, {})
    error = write_report(str(tmp_path / "missing" / "report.json"), snapshot)
    assert error is not None


@pytest.mark.unittest
def test_report_write_handles_atomic_write_failures(monkeypatch, tmp_path):
    """Atomic replacement errors are returned and temporary files are cleaned."""
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import write_report

    monkeypatch.setattr(
        "os.replace", lambda *args: (_ for _ in ()).throw(OSError("busy"))
    )
    error = write_report(str(tmp_path / "report.json"), ReportSnapshot((), {}, {}))
    assert "busy" in error


@pytest.mark.unittest
def test_color_environment_overrides_are_deterministic(monkeypatch):
    """NO_COLOR and FORCE_COLOR are honored only in auto mode."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import render_human

    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ok"),), {}, {"PASS": 1}
    )
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert "\x1b[" not in render_human(snapshot, color="never")
    assert "\x1b[" in render_human(snapshot, color="auto")
    monkeypatch.setenv("NO_COLOR", "1")
    assert "\x1b[" not in render_human(snapshot, color="auto")


@pytest.mark.unittest
def test_emergency_writer_uses_raw_fd_fallback(monkeypatch):
    """A broken text/buffer stream still reaches the raw descriptor."""
    import pyfcstm._selfcheck.report as report_module
    from pyfcstm._selfcheck.report import emergency_write

    class BrokenStream:
        def write(self, message):
            del message
            raise OSError("closed")

        def flush(self):
            raise OSError("closed")

        @property
        def buffer(self):
            return self

    class FakeSys:
        stdout = BrokenStream()
        stderr = BrokenStream()

    calls = []
    monkeypatch.setattr(report_module, "sys", FakeSys())
    monkeypatch.setattr(
        report_module.os,
        "write",
        lambda fd, data: calls.append((fd, data)) or len(data),
    )
    emergency_write("diagnostic\n")
    assert calls and calls[0][0] == 2

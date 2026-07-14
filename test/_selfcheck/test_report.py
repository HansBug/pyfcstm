"""Tests for canonical JSON, human diagnostics, and emergency output."""

import json

import pytest

from pyfcstm._selfcheck.model import CheckResult, ReportSnapshot
from pyfcstm._selfcheck.report import (
    _color_requested,
    emergency_write,
    render_human,
    render_json,
    write_human,
    write_report,
)


def _metadata(exit_code=0):
    return {
        "session_id": "session",
        "started_at": 1.0,
        "finished_at": 2.0,
        "profile": "default",
        "environment": {
            "version": "0.5.0",
            "revision": "abc123",
            "frozen": False,
            "platform": "TestOS-1.0",
            "architecture": "64bit",
            "python_version": "3.10.10",
            "implementation": "CPython",
            "stdout_encoding": "utf-8",
        },
        "artifact": {},
        "dependencies": [],
        "capabilities": {},
        "exit_code": exit_code,
    }


@pytest.mark.unittest
def test_json_report_is_canonical_and_round_trippable(tmp_path):
    """Stdout and atomically written reports share one exact schema."""
    snapshot = ReportSnapshot(
        (CheckResult("runtime.metadata", "PASS", True, summary="ready"),),
        _metadata(),
        {"PASS": 1},
    )
    payload = json.loads(render_json(snapshot))
    assert payload["summary"] == {"PASS": 1}
    assert "checks" not in payload and "counts" not in payload
    destination = tmp_path / "report.json"
    assert write_report(str(destination), snapshot) is None
    assert json.loads(destination.read_text(encoding="utf-8")) == payload


@pytest.mark.unittest
def test_human_report_contains_environment_header_and_failure_evidence():
    """Copied human output identifies the runtime and expands failed checks."""
    snapshot = ReportSnapshot(
        (
            CheckResult("ok", "PASS", True, summary="ready"),
            CheckResult(
                "bad",
                "ERROR",
                True,
                summary="broken",
                reason="worker_exception",
                evidence="full traceback",
                stdout="child stdout",
                stderr="child stderr",
            ),
        ),
        _metadata(exit_code=1),
        {"PASS": 1, "ERROR": 1},
    )
    output = render_human(snapshot, color="never")
    assert "pyfcstm self-check 0.5.0  revision=abc123  mode=source" in output
    assert "System: TestOS-1.0 64bit  Python=3.10.10 (CPython)" in output
    assert "[1/2] PASS ok (ready)" in output
    assert "[2/2] ERROR bad (broken)" in output
    assert "full traceback" in output
    assert "child stdout" in output and "child stderr" in output
    assert "Conclusion: [ FAILED ]" in output


@pytest.mark.unittest
def test_human_summary_omits_zero_counts_and_colors_emitted_statuses(monkeypatch):
    """Only positive status counts are shown and each keeps its color role."""
    monkeypatch.setattr("pyfcstm._selfcheck.report._color_requested", lambda mode: True)
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report._windows_vt_supported", lambda stream: True
    )
    snapshot = ReportSnapshot(
        (
            CheckResult("ok", "PASS", True, summary="ready"),
            CheckResult("warn", "WARN", False, summary="optional"),
        ),
        _metadata(),
        {"PASS": 1, "WARN": 1},
    )
    output = render_human(snapshot, color="always")
    assert "\x1b[32mPASS\x1b[0m = 1" in output
    assert "\x1b[33mWARN\x1b[0m = 1" in output
    assert "SKIP = 0" not in output
    assert "\x1b[1;33m[ WARNINGS ]\x1b[0m" in output


@pytest.mark.unittest
def test_human_positions_use_equal_numeric_widths():
    """The numerator is left-padded to the denominator width without zeros."""
    checks = tuple(
        CheckResult("check{:02d}".format(index), "PASS", True, summary="ready")
        for index in range(12)
    )
    output = render_human(
        ReportSnapshot(checks, _metadata(), {"PASS": 12}), color="never"
    )
    assert "[ 1/12] PASS" in output
    assert "[12/12] PASS" in output
    assert "[01/12]" not in output


@pytest.mark.unittest
def test_report_write_failure_returns_diagnostic(tmp_path):
    """Missing destination directories remain observable without raising."""
    snapshot = ReportSnapshot((), _metadata(), {})
    error = write_report(str(tmp_path / "missing" / "report.json"), snapshot)
    assert error == "report_directory_missing"


@pytest.mark.unittest
def test_report_atomic_replace_failure_is_diagnostic(monkeypatch, tmp_path):
    """A failed final replace cleans its temporary file and returns evidence."""
    snapshot = ReportSnapshot((), _metadata(), {})
    monkeypatch.setattr(
        "os.replace", lambda source, target: (_ for _ in ()).throw(OSError("replace"))
    )
    error = write_report(str(tmp_path / "report.json"), snapshot)
    assert error.startswith("OSError: replace")
    assert not list(tmp_path.glob(".pyfcstm-selfcheck-*.tmp"))


@pytest.mark.unittest
def test_color_environment_precedence(monkeypatch):
    """Explicit never wins; FORCE_COLOR only affects automatic mode."""
    monkeypatch.setattr("sys.stdout.isatty", lambda: False)
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    assert _color_requested("auto") is True
    assert _color_requested("never") is False
    monkeypatch.delenv("FORCE_COLOR")
    monkeypatch.setenv("NO_COLOR", "1")
    assert _color_requested("auto") is False


@pytest.mark.unittest
def test_windows_without_vt_uses_console_attribute_fallback(monkeypatch, capsys):
    """Requested Win7 colors are translated instead of silently discarded."""
    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ready"),),
        _metadata(),
        {"PASS": 1},
    )
    observed = []
    monkeypatch.setattr("pyfcstm._selfcheck.report.os.name", "nt")
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report._windows_vt_supported", lambda stream: False
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report.write_console_ansi",
        lambda text, stream: observed.append(text) or True,
    )

    write_human(snapshot, color="always")
    assert capsys.readouterr().out == ""
    assert observed and "\x1b[32mPASS\x1b[0m" in observed[0]


@pytest.mark.unittest
def test_windows_console_probe_uses_pointer_sized_handle(monkeypatch):
    """The VT probe preserves 64-bit handles and reads the console mode bit."""
    try:
        __import__("ctypes.wintypes")
    except ValueError as err:
        pytest.skip("ctypes.wintypes unavailable: {}".format(err))
    import ctypes
    from ctypes import wintypes
    from types import SimpleNamespace

    from pyfcstm._selfcheck import report

    class Function:
        def __init__(self, callback):
            self.callback = callback
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            return self.callback(*args)

    get_handle = Function(lambda value: 0x123456789 if value == -11 else 0)

    def get_mode(handle, pointer):
        assert handle == 0x123456789
        pointer._obj.value = 0x0004
        return 1

    kernel = SimpleNamespace(
        GetStdHandle=get_handle,
        GetConsoleMode=Function(get_mode),
    )
    monkeypatch.setattr(report, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    assert report._windows_vt_supported(object()) is True
    assert get_handle.restype is wintypes.HANDLE


@pytest.mark.unittest
def test_windows_console_fallback_failure_writes_one_plain_report(monkeypatch, capsys):
    """A failed native color preflight falls back to one complete plain report."""
    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ready"),),
        _metadata(),
        {"PASS": 1},
    )
    monkeypatch.setattr("pyfcstm._selfcheck.report.os.name", "nt")
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report._windows_vt_supported", lambda stream: False
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report.write_console_ansi", lambda text, stream: False
    )
    write_human(snapshot, color="always")
    output = capsys.readouterr().out
    assert output.count("pyfcstm self-check 0.5.0") == 1
    assert "\x1b[" not in output


@pytest.mark.unittest
def test_json_emergency_output_preserves_stdout_purity(monkeypatch, capfd):
    """JSON-mode emergency text bypasses stdout and uses binary stderr."""
    assert emergency_write("emergency\n", "json") is None
    captured = capfd.readouterr()
    assert captured.out == ""
    assert "emergency" in captured.err


@pytest.mark.unittest
def test_emergency_writer_uses_raw_fd_after_stream_failures(monkeypatch, capfd):
    """Broken Python streams fall through to raw descriptor two."""

    class BrokenStdout:
        def write(self, value):
            raise OSError("stdout")

        def flush(self):
            raise OSError("stdout")

    class BrokenStderr:
        class Buffer:
            def write(self, value):
                raise OSError("stderr")

            def flush(self):
                raise OSError("stderr")

        buffer = Buffer()

    with monkeypatch.context() as stream_patch:
        stream_patch.setattr("sys.stdout", BrokenStdout())
        stream_patch.setattr("sys.stderr", BrokenStderr())
        emergency_write("raw fallback\n", "human")
    assert "raw fallback" in capfd.readouterr().err


@pytest.mark.unittest
def test_emergency_writer_uses_temp_file_when_all_channels_fail(monkeypatch, tmp_path):
    """The final fallback records evidence in a private temporary file."""

    class Broken:
        def write(self, value):
            raise OSError("broken")

        def flush(self):
            raise OSError("broken")

        buffer = None

    emergency = tmp_path / "emergency.log"
    monkeypatch.setattr("sys.stdout", Broken())
    monkeypatch.setattr("sys.stderr", Broken())
    real_write = __import__("os").write

    def write(descriptor, data):
        if descriptor == 2:
            raise OSError("fd")
        return real_write(descriptor, data)

    monkeypatch.setattr("os.write", write)
    monkeypatch.setattr(
        "tempfile.mkstemp",
        lambda **kwargs: (
            __import__("os").open(
                str(emergency), __import__("os").O_CREAT | __import__("os").O_WRONLY
            ),
            str(emergency),
        ),
    )
    assert emergency_write("saved\n", "human") == str(emergency)
    assert emergency.read_text(encoding="utf-8") == "saved\n"

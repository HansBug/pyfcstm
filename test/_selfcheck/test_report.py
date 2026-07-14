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
    report = json.loads(payload)
    assert report["schema_version"] == "pyfcstm-selfcheck/v1"
    assert report["results"][0]["id"] == "artifact.self_dispatch"
    assert report["profile"] is None


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
    assert "[1/2] PASS ok (ready)" in output
    assert "[2/2] ERROR bad (broken)" in output
    assert "full traceback" in output
    assert "PASS = 1" in output
    assert "ERROR = 1" in output
    assert "WARN = 0" not in output
    assert "Conclusion: [ FAILED ]" in output


@pytest.mark.unittest
def test_human_summary_lists_positive_status_counts_and_colors_them(monkeypatch):
    """Human summaries omit zero counts and color every emitted status."""
    import pyfcstm._selfcheck.report as report_module
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import render_human

    snapshot = ReportSnapshot(
        (
            CheckResult("ok", "PASS", True, summary="ready"),
            CheckResult("warning", "WARN", False, summary="optional"),
        ),
        {},
        {"PASS": 1, "WARN": 1},
    )
    monkeypatch.setattr(report_module, "_windows_vt_supported", lambda stream: True)
    output = render_human(snapshot, color="always")
    assert "\x1b[32mPASS\x1b[0m = 1" in output
    assert "\x1b[33mWARN\x1b[0m = 1" in output
    assert "SKIP = 0" not in output
    assert "BLOCKED = 0" not in output
    assert "\x1b[1;33m[ WARNINGS ]\x1b[0m" in output


@pytest.mark.unittest
def test_human_check_lines_align_variable_width_indices():
    """Human check positions use spaces, not leading zeroes, for alignment."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import render_human

    checks = tuple(
        CheckResult("check{:02d}".format(index), "PASS", True, summary="ready")
        for index in range(1, 13)
    )
    output = render_human(
        ReportSnapshot(checks, {}, {"PASS": len(checks)}), color="never"
    )
    assert "[ 1/12] PASS check01 (ready)" in output
    assert "[10/12] PASS check10 (ready)" in output
    assert "[12/12] PASS check12 (ready)" in output
    assert "[01/12]" not in output


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
    import pyfcstm._selfcheck.report as report_module
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import render_human

    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ok"),), {}, {"PASS": 1}
    )
    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.setenv("FORCE_COLOR", "1")
    # This test isolates FORCE_COLOR from the separate Win7/no-VT fallback.
    monkeypatch.setattr(report_module, "_windows_vt_supported", lambda stream: True)
    assert "\x1b[" not in render_human(snapshot, color="never")
    assert "\x1b[" in render_human(snapshot, color="auto")
    monkeypatch.setenv("NO_COLOR", "1")
    assert "\x1b[" not in render_human(snapshot, color="auto")


@pytest.mark.unittest
def test_windows_without_vt_support_falls_back_to_plain_status_labels(monkeypatch):
    """Win7-style consoles do not receive raw ANSI escape sequences."""
    import ctypes
    from types import SimpleNamespace

    import pyfcstm._selfcheck.report as report_module
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import ReportSnapshot
    from pyfcstm._selfcheck.report import render_human

    class Kernel:
        def GetStdHandle(self, value):
            del value
            return 1

        def GetConsoleMode(self, handle, mode):
            del handle, mode
            return 0

    monkeypatch.setattr(report_module.os, "name", "nt")
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(kernel32=Kernel()),
        raising=False,
    )
    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ready"),), {}, {"PASS": 1}
    )
    output = render_human(snapshot, color="always")
    assert "\x1b[" not in output
    assert "[1/1] PASS ok (ready)" in output


@pytest.mark.unittest
def test_windows_vt_probe_declares_pointer_sized_handles(monkeypatch):
    """The Win32 console probe preserves 64-bit HANDLE values."""
    import ctypes
    from types import SimpleNamespace

    try:
        from ctypes import wintypes
    except ValueError as err:
        pytest.skip("ctypes.wintypes unavailable: {}".format(err))

    import pyfcstm._selfcheck.report as report_module

    class Function:
        def __init__(self, callback):
            self.callback = callback
            self.argtypes = None
            self.restype = None

        def __call__(self, *args):
            return self.callback(*args)

    get_std_handle = Function(lambda value: 0x123456789 if value == -11 else 0)

    def set_console_mode(handle, mode):
        del handle
        assert isinstance(mode._obj, wintypes.DWORD)
        mode._obj.value = 0x0004
        return 1

    get_console_mode = Function(set_console_mode)
    kernel = SimpleNamespace(
        GetStdHandle=get_std_handle,
        GetConsoleMode=get_console_mode,
    )
    monkeypatch.setattr(report_module.os, "name", "nt")
    monkeypatch.setattr(
        ctypes,
        "windll",
        SimpleNamespace(kernel32=kernel),
        raising=False,
    )

    assert report_module._windows_vt_supported(object()) is True
    assert get_std_handle.restype is wintypes.HANDLE
    assert get_console_mode.restype is wintypes.BOOL


@pytest.mark.unittest
def test_windows_vt_probe_handles_native_attribute_failure(monkeypatch):
    """A partial Win32 ctypes surface falls back without raising."""
    import ctypes
    from types import SimpleNamespace

    import pyfcstm._selfcheck.report as report_module

    class Kernel:
        def GetStdHandle(self, value):
            del value
            raise OSError("console unavailable")

    monkeypatch.setattr(report_module.os, "name", "nt")
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=Kernel()), raising=False
    )
    assert report_module._windows_vt_supported(object()) is False


@pytest.mark.unittest
def test_auto_color_requires_a_tty_when_force_color_is_absent(monkeypatch):
    """Auto mode stays plain for redirected output."""
    from types import SimpleNamespace

    import pyfcstm._selfcheck.report as report_module

    class Stream:
        def isatty(self):
            return False

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(report_module, "sys", SimpleNamespace(stdout=Stream()))
    assert report_module._color_enabled("auto") is False


@pytest.mark.unittest
def test_json_emergency_writer_uses_binary_stderr(monkeypatch):
    """JSON emergency output bypasses text stdout to preserve machine purity."""
    from types import SimpleNamespace

    import pyfcstm._selfcheck.report as report_module

    class Buffer:
        def __init__(self):
            self.data = b""

        def write(self, data):
            self.data += data

        def flush(self):
            return None

    stderr = Buffer()
    monkeypatch.setattr(
        report_module, "sys", SimpleNamespace(stderr=SimpleNamespace(buffer=stderr))
    )
    assert report_module.emergency_write("diagnostic\n", "json") is None
    assert stderr.data == b"diagnostic\n"


@pytest.mark.unittest
def test_report_cleanup_failure_is_best_effort(monkeypatch, tmp_path):
    """A failed temporary-file unlink never escapes the report writer."""
    import pyfcstm._selfcheck.report as report_module
    from pyfcstm._selfcheck.model import ReportSnapshot

    monkeypatch.setattr(
        report_module.os,
        "replace",
        lambda *args: (_ for _ in ()).throw(OSError("busy")),
    )
    monkeypatch.setattr(
        report_module.os,
        "unlink",
        lambda *args: (_ for _ in ()).throw(OSError("locked")),
    )
    error = report_module.write_report(
        str(tmp_path / "report.json"), ReportSnapshot((), {}, {})
    )
    assert "busy" in error


@pytest.mark.unittest
def test_emergency_writer_returns_none_when_temp_fallback_fails(monkeypatch):
    """The emergency chain reports no path when every final sink is broken."""
    from types import SimpleNamespace

    import pyfcstm._selfcheck.report as report_module

    class BrokenStream:
        def write(self, message):
            del message
            raise OSError("closed")

        def flush(self):
            raise OSError("closed")

        @property
        def buffer(self):
            return self

    monkeypatch.setattr(
        report_module,
        "sys",
        SimpleNamespace(stdout=BrokenStream(), stderr=BrokenStream()),
    )
    monkeypatch.setattr(
        report_module.os,
        "write",
        lambda fd, data: (_ for _ in ()).throw(OSError("fd closed")),
    )
    monkeypatch.setattr(
        report_module.tempfile, "mkstemp", lambda **kwargs: (9, "/tmp/no-report")
    )
    monkeypatch.setattr(report_module.os, "close", lambda fd: None)
    monkeypatch.setattr(report_module.os, "unlink", lambda path: None)
    assert report_module.emergency_write("diagnostic\n") is None


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


@pytest.mark.unittest
def test_emergency_writer_uses_safe_temp_report_when_all_streams_fail(monkeypatch):
    """The final emergency layer leaves a durable diagnostic when descriptors fail."""
    import pyfcstm._selfcheck.report as report_module

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

    monkeypatch.setattr(report_module, "sys", FakeSys())
    original_write = report_module.os.write

    def fail_stderr(fd, data):
        if fd == 2:
            raise OSError("closed")
        return original_write(fd, data)

    monkeypatch.setattr(report_module.os, "write", fail_stderr)
    path = report_module.emergency_write("diagnostic\n")
    assert path is not None
    try:
        assert report_module.tempfile is not None
        with open(path, "rb") as stream:
            assert stream.read() == b"diagnostic\n"
    finally:
        report_module.os.unlink(path)

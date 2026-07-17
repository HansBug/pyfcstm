"""Tests for canonical JSON, human diagnostics, and emergency output."""

import json
from types import SimpleNamespace

import pytest

from pyfcstm._selfcheck.model import CheckResult, ReportSnapshot
from pyfcstm._selfcheck.report import (
    _color_requested,
    render_human,
    render_human_result,
    render_human_summary,
    render_json,
    write_human,
    write_human_environment,
    write_human_plan,
    write_human_result,
    write_human_start,
    write_human_summary,
    write_report,
)


def _ctypes_for_native_seam(monkeypatch):
    """Provide scalar ctypes aliases when Python 3.7 cannot import wintypes."""
    import ctypes

    try:
        from ctypes import wintypes
    except ValueError:
        wintypes = SimpleNamespace(
            BOOL=ctypes.c_int,
            DWORD=ctypes.c_uint32,
            HANDLE=ctypes.c_void_p,
        )
        monkeypatch.setattr(ctypes, "wintypes", wintypes, raising=False)
    return ctypes


def _metadata(exit_code=0):
    return {
        "session_id": "session",
        "started_at": 1.0,
        "finished_at": 2.0,
        "profile": "default",
        "environment": {
            "version": "0.5.0",
            "revision": "abc123",
            "commit": "def456",
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
    assert (
        "pyfcstm self-check 0.5.0  revision=abc123  commit=def456  mode=source"
        in output
    )
    assert "System: TestOS-1.0 64bit  Python=3.10.10 (CPython)" in output
    assert "[1/2] PASS ok (ready)" in output
    assert "[2/2] ERROR bad (broken)" in output
    assert "full traceback" in output
    assert "child stdout" in output and "child stderr" in output
    assert "Conclusion: [ FAILED ]" in output


@pytest.mark.unittest
def test_human_failure_details_include_semantic_diagnostics():
    """Human failures expose expected, observed, remediation, and exception."""
    result = CheckResult(
        "resource.guide",
        "FAIL",
        True,
        summary="guide checksum mismatch",
        reason="resource_invalid",
        expected="sha256=abc",
        observed="sha256=def",
        remediation="run make sha256",
        exception="Traceback (most recent call last):\nValueError: mismatch",
    )
    rendered = render_human_result(result, 1, 1, color="never")
    for value in (
        "expected: sha256=abc",
        "observed: sha256=def",
        "remediation: run make sha256",
        "exception:",
        "ValueError: mismatch",
    ):
        assert value in rendered


@pytest.mark.unittest
def test_human_traceback_is_indented_and_not_duplicated():
    """Shared evidence/exception tracebacks render once with stable indentation."""
    traceback_text = (
        "Traceback (most recent call last):\n"
        "  File \"probe.py\", line 1, in probe\n"
        "ValueError: failed"
    )
    result = CheckResult(
        "core.probe",
        "FAIL",
        True,
        summary="probe failed",
        reason="probe_failed",
        evidence="command=['probe']\n" + traceback_text,
        exception=traceback_text,
    )
    rendered = render_human_result(result, 1, 1, color="never")
    assert rendered.count("Traceback (most recent call last)") == 1
    assert "  evidence:\n    command=['probe']" in rendered
    assert "  exception:\n    Traceback (most recent call last):" in rendered
    assert "      File \"probe.py\", line 1, in probe" in rendered


@pytest.mark.unittest
def test_human_pass_and_optional_results_expose_concrete_facts():
    """PASS stays factual, WARN is moderate, and SKIP stays on one line."""
    passed = CheckResult(
        "native.z3.solve",
        "PASS",
        True,
        summary="solve Int x constrained by x == 1",
        expected="status=sat model[x]=1",
        observed="status=sat model[x]=1",
    )
    rendered = render_human_result(passed, 1, 12, color="never")
    assert "[ 1/12] PASS native.z3.solve" in rendered
    assert "expected=status=sat model[x]=1" in rendered
    assert "observed=status=sat model[x]=1" in rendered

    multiline = CheckResult(
        "visualize.java",
        "PASS",
        False,
        summary="run java -version",
        expected="returncode=0\nand version output",
        observed="java version\nJava Runtime\nJava VM",
    )
    rendered = render_human_result(multiline, 2, 12, color="never")
    assert rendered.count("\n") == 1
    assert "expected=returncode=0 and version output" in rendered
    assert "observed=java version Java Runtime Java VM" in rendered

    warned = CheckResult(
        "visualize.java",
        "WARN",
        False,
        summary="Java is unavailable",
        reason="capability_unavailable",
        expected="java on PATH",
        observed="not found",
        remediation="install a JRE",
        return_code=0,
        pid=123,
        duration_ms=42.0,
    )
    rendered = render_human_result(warned, 2, 12, color="never")
    assert "reason: capability_unavailable" in rendered
    assert "expected: java on PATH" in rendered
    assert "observed: not found" in rendered
    assert "remediation: install a JRE" in rendered
    assert "return_code:" not in rendered
    assert "pid:" not in rendered
    assert "duration_ms:" not in rendered

    skipped = CheckResult(
        "visualize.local_render",
        "SKIP",
        False,
        summary="capability prerequisite is unavailable",
        reason="prerequisite_skipped",
        prerequisites=("visualize.java", "visualize.plantuml_jar"),
    )
    rendered = render_human_result(skipped, 3, 12, color="never")
    assert rendered.count("\n") == 1
    assert "capability prerequisite is unavailable: visualize.java, visualize.plantuml_jar" in rendered
    assert "reason:" not in rendered
    assert "prerequisite:" not in rendered


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
def test_incremental_human_output_flushes_header_results_and_summary(capsys):
    """Human mode exposes each completed result without changing JSON rendering."""
    check = CheckResult("demo", "PASS", True, summary="ready")
    snapshot = ReportSnapshot((check,), _metadata(), {"PASS": 1})
    write_human_start("default", color="never")
    write_human_plan(1, "default", color="never")
    write_human_environment(snapshot.metadata["environment"], color="never")
    write_human_result(check, 1, 1, color="never")
    write_human_summary(snapshot, color="never")
    output = capsys.readouterr().out
    assert output.splitlines()[0].startswith("pyfcstm self-check 0.6.0")
    assert "running 1 checks" in output
    assert "revision=abc123  commit=def456" in output
    assert "[1/1] PASS demo (ready)" in output
    assert "Conclusion: [ PASSED ]" in output
    assert "SKIP = 0" not in output
    assert "[1/1] PASS demo (ready)" in render_human_result(check, 1, 1, "never")
    assert "Conclusion: [ PASSED ]" in render_human_summary(snapshot, "never")


@pytest.mark.unittest
def test_public_human_render_uses_posix_vt_path(monkeypatch):
    """The public human renderer enables ANSI output on POSIX terminals."""
    import pyfcstm._selfcheck.report as report

    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ready"),),
        _metadata(),
        {"PASS": 1},
    )
    monkeypatch.setattr(report.os, "name", "posix")
    output = report.render_human(snapshot, color="always")
    assert "\x1b[32mPASS\x1b[0m" in output


@pytest.mark.unittest
def test_public_human_render_handles_vt_probe_import_failure(monkeypatch):
    """A native console import failure degrades to plain public output."""
    import builtins

    import pyfcstm._selfcheck.report as report

    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ready"),),
        _metadata(),
        {"PASS": 1},
    )
    real_import = builtins.__import__

    def fail_ctypes(name, *args, **kwargs):
        if name == "ctypes":
            raise ValueError("ctypes unavailable")
        return real_import(name, *args, **kwargs)

    monkeypatch.setattr(report.os, "name", "nt")
    monkeypatch.setattr(builtins, "__import__", fail_ctypes)
    output = report.render_human(snapshot, color="always")
    assert "\x1b[32mPASS\x1b[0m" not in output
    assert "PASS ok (ready)" in output


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
def test_report_cleanup_failure_is_bounded(monkeypatch, tmp_path):
    """A temporary-file unlink failure does not escape report writing."""
    snapshot = ReportSnapshot((), _metadata(), {})
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report.os.replace",
        lambda source, target: (_ for _ in ()).throw(OSError("replace")),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report.os.unlink",
        lambda path: (_ for _ in ()).throw(OSError("unlink")),
    )
    assert write_report(str(tmp_path / "report.json"), snapshot).startswith(
        "OSError: replace"
    )


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
def test_incremental_windows_without_vt_keeps_console_color_roles(monkeypatch):
    """Streaming output passes ANSI roles to the Win7 attribute translator."""
    snapshot = ReportSnapshot(
        (CheckResult("ok", "PASS", True, summary="ready"),),
        _metadata(),
        {"PASS": 1},
    )
    observed = []
    import pyfcstm._selfcheck.report as report

    monkeypatch.setattr(
        report, "os", SimpleNamespace(name="nt", environ=report.os.environ)
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report._windows_vt_supported", lambda stream: False
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report.write_console_ansi",
        lambda text, stream: observed.append(text) or True,
    )

    write_human_start("default", color="always")
    write_human_result(snapshot.checks[0], 1, 1, color="always")
    write_human_summary(snapshot, color="always")

    assert "\x1b[36mpyfcstm self-check" in observed[0]
    assert "\x1b[32mPASS\x1b[0m" in observed[1]
    assert "\x1b[1;32m[ PASSED ]\x1b[0m" in observed[2]


@pytest.mark.unittest
def test_incremental_windows_fallback_failure_writes_plain_text(monkeypatch, capsys):
    """A failed Win7 color preflight never leaks ANSI from streaming output."""
    check = CheckResult("ok", "PASS", True, summary="ready")
    import pyfcstm._selfcheck.report as report

    monkeypatch.setattr(
        report, "os", SimpleNamespace(name="nt", environ=report.os.environ)
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report._windows_vt_supported", lambda stream: False
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.report.write_console_ansi", lambda text, stream: False
    )

    write_human_result(check, 1, 1, color="always")

    output = capsys.readouterr().out
    assert output == "[1/1] PASS ok (ready)\n"
    assert "\x1b[" not in output


@pytest.mark.unittest
def test_windows_console_probe_uses_pointer_sized_handle(monkeypatch):
    """The VT probe preserves 64-bit handles and reads the console mode bit."""
    import ctypes
    from types import SimpleNamespace

    from pyfcstm._selfcheck import report

    _ctypes_for_native_seam(monkeypatch)
    from ctypes import wintypes

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
def test_windows_console_probe_reports_unavailable_api(monkeypatch):
    """The Windows probe degrades cleanly when native APIs are unavailable."""
    import pyfcstm._selfcheck.report as report

    ctypes = _ctypes_for_native_seam(monkeypatch)
    monkeypatch.setattr(report, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=object()), raising=False
    )
    assert report._windows_vt_supported(object()) is False


@pytest.mark.unittest
def test_windows_console_probe_rejects_non_vt_mode(monkeypatch):
    """A console without the VT mode bit uses the Win7 fallback."""
    import pyfcstm._selfcheck.report as report

    ctypes = _ctypes_for_native_seam(monkeypatch)

    class Function:
        def __call__(self, *args):
            if len(args) == 1:
                return 10
            return 0

    kernel = SimpleNamespace(GetStdHandle=Function(), GetConsoleMode=Function())
    monkeypatch.setattr(report, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    assert report._windows_vt_supported(object()) is False


@pytest.mark.unittest
def test_windows_console_probe_accepts_vt_mode(monkeypatch):
    """The probe returns true when the console exposes VT processing."""
    import pyfcstm._selfcheck.report as report

    ctypes = _ctypes_for_native_seam(monkeypatch)

    class Function:
        def __init__(self, result):
            self.result = result

        def __call__(self, *args):
            if len(args) == 2:
                args[1]._obj.value = 0x0004
            return self.result

    kernel = SimpleNamespace(GetStdHandle=Function(10), GetConsoleMode=Function(1))
    monkeypatch.setattr(report, "os", SimpleNamespace(name="nt"))
    monkeypatch.setattr(
        ctypes, "windll", SimpleNamespace(kernel32=kernel), raising=False
    )
    assert report._windows_vt_supported(object()) is True


@pytest.mark.unittest
def test_windows_console_probe_import_failure_is_supported(monkeypatch):
    """Python 3.7's unavailable wintypes module selects the safe fallback."""
    import ctypes
    import pyfcstm._selfcheck.report as report

    monkeypatch.setattr(report, "os", SimpleNamespace(name="nt"))
    monkeypatch.delattr(ctypes, "wintypes", raising=False)
    assert report._windows_vt_supported(object()) is False


@pytest.mark.unittest
def test_auto_color_uses_terminal_detection(monkeypatch):
    """Automatic color mode consults the current stdout TTY state."""
    import pyfcstm._selfcheck.report as report

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(
        report,
        "sys",
        SimpleNamespace(stdout=SimpleNamespace(isatty=lambda: True)),
    )
    assert report._color_requested("auto") is True


@pytest.mark.unittest
def test_auto_color_without_force_or_tty_is_plain(monkeypatch):
    """Automatic output stays plain when neither environment nor TTY requests color."""
    import pyfcstm._selfcheck.report as report

    monkeypatch.delenv("NO_COLOR", raising=False)
    monkeypatch.delenv("FORCE_COLOR", raising=False)
    monkeypatch.setattr(
        report,
        "sys",
        SimpleNamespace(stdout=SimpleNamespace(isatty=lambda: False)),
    )
    assert report._color_requested("auto") is False


@pytest.mark.unittest
def test_failure_details_skip_empty_evidence_and_render_stdout():
    """Failure detail rendering omits empty fields while retaining child output."""
    snapshot = ReportSnapshot(
        (
            CheckResult(
                "bad",
                "ERROR",
                True,
                summary="broken",
                reason="worker_exception",
                stdout="child stdout",
            ),
        ),
        _metadata(exit_code=0),
        {"ERROR": 1},
    )
    output = render_human(snapshot, color="never")
    assert "stdout:" in output
    assert "child stdout" in output
    assert "evidence:" not in output


@pytest.mark.unittest
def test_human_report_handles_missing_environment_and_explicit_failure_code():
    """The public renderer remains complete with sparse metadata and exit code 1."""
    snapshot = ReportSnapshot((), {"environment": {}}, {"ERROR": 1})
    output = render_human(snapshot, color="never")
    assert "revision=unavailable" in output
    assert "encoding=unavailable" in output
    assert "Conclusion: [ FAILED ]" in output

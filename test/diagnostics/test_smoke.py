"""
Unit tests for :mod:`pyfcstm.diagnostics.smoke`.

These cover:

* :func:`run_smoke_test` exits zero on a clean install (the CI environment
  the test suite runs under is presumed to be one).
* The runner is **catastrophe-tolerant**: a case that raises an
  ``Exception``, ``SystemExit``, or even ``KeyboardInterrupt`` does not
  propagate out of the runner and is surfaced as a structured FAIL row.
* PASS / FAIL formatting includes the case name, method, and (on FAIL)
  the exception type, message, traceback, and remediation hint.
* The CLI flag (:func:`_run_smoke_test` callback) wires through to
  ``ctx.exit(failed_count)``.
"""

from __future__ import annotations

import io
import re
import subprocess
import sys
from contextlib import redirect_stdout
from pathlib import Path

import pytest
from click.testing import CliRunner

from pyfcstm.diagnostics import smoke as smoke_module
from pyfcstm.diagnostics.smoke import (
    SmokeCase,
    SmokeResult,
    _format_traceback,
    _run_one,
    run_smoke_test,
)


_ANSI = re.compile(r"\x1b\[[0-9;]*m")


def _strip_ansi(text: str) -> str:
    """Drop ANSI escapes so substring assertions ignore color codes."""
    return _ANSI.sub("", text)


@pytest.mark.unittest
def test_run_smoke_test_returns_zero_on_clean_install():
    """The repo's own test environment ships every required dep, so the
    full smoke battery must come back at 0 failures. If this regresses,
    the *runner itself* is busted - look at the first FAIL line in the
    captured output for the broken case."""
    buf = io.StringIO()
    with redirect_stdout(buf):
        failed = run_smoke_test()
    output = _strip_ansi(buf.getvalue())
    assert failed == 0, (
        "run_smoke_test() reported {} failures on clean install. Output:\n{}"
    ).format(failed, output)
    # Sanity: every group header is in the output.
    for group_label in (
        "Python runtime",
        "Third-party libraries",
        "Native binaries",
        "Internal modules",
        "Static resources",
        "End-to-end SysDeSim CLI paths",
    ):
        assert group_label in output, (
            "missing group header {!r} in smoke output".format(group_label)
        )
    assert "Smoke test summary" in output


@pytest.mark.unittest
def test_runner_catches_runtime_errors():
    """A SmokeCase whose ``func`` raises ``RuntimeError`` becomes a FAIL
    result, not an exception out of the runner."""

    def _explode():
        raise RuntimeError("boom from inside the case")

    case = SmokeCase(
        name="synthetic_explode",
        method="raise RuntimeError",
        func=_explode,
        remediation="this is a synthetic case used by tests",
    )
    result = _run_one(case)
    assert isinstance(result, SmokeResult)
    assert result.status == "FAIL"
    assert isinstance(result.error, RuntimeError)
    assert "boom from inside the case" in str(result.error)
    assert result.error_traceback is not None
    assert "RuntimeError" in result.error_traceback


@pytest.mark.unittest
def test_runner_catches_baseexception_subtypes():
    """``KeyboardInterrupt`` / ``SystemExit`` / ``Exception`` all stay
    inside the runner. The smoke runner is the **last line of defence**
    when an install is broken; if a case manages to escape control
    flow, this contract is busted."""

    for exc_factory in (
        lambda: KeyboardInterrupt("synthetic"),
        lambda: SystemExit(7),
        lambda: ValueError("synthetic value error"),
    ):
        def _raise(_factory=exc_factory):
            raise _factory()

        case = SmokeCase(
            name="synthetic_baseexc__" + type(exc_factory()).__name__,
            method="raise BaseException subtype",
            func=_raise,
        )
        result = _run_one(case)
        assert result.status == "FAIL"
        assert result.error is not None


@pytest.mark.unittest
def test_runner_completes_when_some_cases_fail(monkeypatch):
    """Even if half the cases fail, the runner finishes the rest, prints
    a summary, and returns the count of failures."""

    def _ok():
        pass

    def _bad():
        raise RuntimeError("planted failure")

    cases = [
        SmokeCase(name="ok_a", method="noop", func=_ok),
        SmokeCase(name="bad_a", method="raise", func=_bad,
                  remediation="don't actually fix this, it's synthetic"),
        SmokeCase(name="ok_b", method="noop", func=_ok),
        SmokeCase(name="bad_b", method="raise", func=_bad),
    ]
    monkeypatch.setattr(
        smoke_module, "_build_case_groups", lambda: [("Synthetic", cases)],
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        failed = run_smoke_test()
    output = _strip_ansi(buf.getvalue())

    assert failed == 2, (
        "expected 2 failures, got {}; output:\n{}".format(failed, output)
    )
    # All four cases printed, in order.
    for needle in ("ok_a", "bad_a", "ok_b", "bad_b"):
        assert needle in output, (
            "missing case {!r} in output:\n{}".format(needle, output)
        )
    assert "[PASS]" in output
    assert "[FAIL]" in output
    # Failed-cases section
    assert "Failed cases:" in output
    assert "planted failure" in output
    # Remediation surfaces under the failing case it was attached to.
    assert "don't actually fix this" in output


@pytest.mark.unittest
def test_pass_row_shows_method_and_elapsed(monkeypatch):
    """PASS rows are short and structured: name, method, elapsed."""
    monkeypatch.setattr(
        smoke_module, "_build_case_groups",
        lambda: [("Synthetic", [
            SmokeCase(name="quick_pass", method="literally nothing",
                      func=lambda: None),
        ])],
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        failed = run_smoke_test()
    output = _strip_ansi(buf.getvalue())
    assert failed == 0
    assert "[PASS] quick_pass" in output
    assert "literally nothing" in output
    # Timing column is present (some "ms" value).
    assert "ms)" in output


@pytest.mark.unittest
def test_fail_row_shows_category_and_remediation(monkeypatch):
    """FAIL rows include category, message, traceback, and remediation."""

    def _raise():
        raise FileNotFoundError("/no/such/path")

    monkeypatch.setattr(
        smoke_module, "_build_case_groups",
        lambda: [("Synthetic", [
            SmokeCase(
                name="missing_lib",
                method="open(/no/such/path)",
                func=_raise,
                remediation="install foo via pip install foo",
            ),
        ])],
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        failed = run_smoke_test()
    output = _strip_ansi(buf.getvalue())
    assert failed == 1
    assert "[FAIL] missing_lib" in output
    assert "category:" in output
    assert "FileNotFoundError" in output
    assert "message:" in output
    assert "/no/such/path" in output
    assert "traceback" in output.lower()
    assert "remediation:" in output
    assert "pip install foo" in output


@pytest.mark.unittest
def test_format_traceback_keeps_head_and_trims_middle():
    """``_format_traceback`` keeps the head line, the bottom N frames,
    and trims a marker in the middle for very long tracebacks."""
    long_tb = "Traceback (most recent call last):\n" + "\n".join(
        '  File "f.py", line {}, in foo\n    line {}'.format(i, i)
        for i in range(40)
    ) + "\nValueError: deep failure"
    out = _format_traceback(ValueError("x"), long_tb, max_frames=3)
    text = "\n".join(out)
    assert text.startswith("Traceback (most recent call last):")
    assert "earlier frames trimmed" in text
    assert "ValueError: deep failure" in text


@pytest.mark.unittest
def test_format_traceback_passes_short_traceback_unchanged():
    """Short traces are not trimmed."""
    short_tb = (
        "Traceback (most recent call last):\n"
        '  File "f.py", line 1, in foo\n'
        "    raise ValueError('boom')\n"
        "ValueError: boom"
    )
    out = _format_traceback(ValueError("boom"), short_tb, max_frames=3)
    assert "earlier frames trimmed" not in "\n".join(out)
    assert "ValueError: boom" in "\n".join(out)


@pytest.mark.unittest
def test_cli_flag_invokes_runner_and_propagates_exit_code(monkeypatch):
    """``pyfcstm --smoke-test`` exits with the failure count."""
    from pyfcstm.entry.cli import pyfcstmcli

    # Plant exactly 2 failures + 1 pass via the case registry.
    monkeypatch.setattr(
        smoke_module, "_build_case_groups",
        lambda: [("Synthetic", [
            SmokeCase(name="ok", method="noop", func=lambda: None),
            SmokeCase(
                name="bad1", method="raise A",
                func=lambda: (_ for _ in ()).throw(RuntimeError("x")),
            ),
            SmokeCase(
                name="bad2", method="raise B",
                func=lambda: (_ for _ in ()).throw(RuntimeError("y")),
            ),
        ])],
    )
    runner = CliRunner()
    result = runner.invoke(pyfcstmcli, ["--smoke-test"], color=False)
    output = _strip_ansi(result.output)
    assert result.exit_code == 2, (
        "expected exit code 2 (= 2 failures), got {}; output:\n{}".format(
            result.exit_code, output,
        )
    )
    assert "[PASS] ok" in output
    assert "[FAIL] bad1" in output
    assert "[FAIL] bad2" in output


@pytest.mark.unittest
def test_cli_flag_returns_zero_on_clean_run():
    """``pyfcstm --smoke-test`` returns exit code 0 on a healthy install."""
    from pyfcstm.entry.cli import pyfcstmcli

    runner = CliRunner()
    result = runner.invoke(pyfcstmcli, ["--smoke-test"], color=False)
    assert result.exit_code == 0, (
        "expected exit code 0 on clean install, got {}; output:\n{}".format(
            result.exit_code, _strip_ansi(result.output),
        )
    )
    output = _strip_ansi(result.output)
    assert "All checks passed" in output


@pytest.mark.unittest
def test_help_text_advertises_smoke_test_flag():
    """The top-level ``--help`` mentions the new flag so it is discoverable."""
    from pyfcstm.entry.cli import pyfcstmcli

    runner = CliRunner()
    result = runner.invoke(pyfcstmcli, ["--help"], color=False)
    assert result.exit_code == 0, result.output
    assert "--smoke-test" in result.output


@pytest.mark.unittest
def test_python_dash_m_pyfcstm_smoke_test_short_circuits_entry_chain():
    """``python -m pyfcstm --smoke-test`` must NOT pull in the regular
    ``pyfcstm.entry`` chain.

    The whole point of the short-circuit in ``pyfcstm/__main__.py`` is
    to keep the smoke runner alive when subcommand modules fail to
    import (e.g. ANTLR-generated grammar files moved aside, optional
    extras missing). We verify that property by spawning a fresh
    interpreter, running ``python -m pyfcstm --smoke-test``, and
    asserting it returns the canonical summary line. We do not rely on
    a particular exit code (the test environment may legitimately have
    failures depending on the ``make tpl`` state of the dev checkout)
    - we only insist that the runner *finishes* and prints its
    structured summary.
    """
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "pyfcstm", "--smoke-test"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = _strip_ansi(proc.stdout)
    summary_line = next(
        (ln for ln in output.splitlines() if ln.startswith("Smoke test summary:")),
        None,
    )
    assert summary_line is not None, (
        "python -m pyfcstm --smoke-test produced no summary line; runner "
        "may have crashed mid-flight.\nstdout:\n{}\nstderr:\n{}".format(
            output, proc.stderr,
        )
    )
    # Optional: assert the runner reports a single "X PASS" or
    # "X PASS, Y FAIL" structured summary.
    assert " PASS" in summary_line, summary_line


@pytest.mark.unittest
def test_dash_m_diagnostics_runs_independently_of_entry_chain():
    """``python -m pyfcstm.diagnostics`` is the apocalypse-grade entry.

    It must work even when the regular ``pyfcstm.entry`` subcommand
    chain is broken, because that's exactly when users will reach for
    it. We verify by running the module directly (no entry chain in
    the import graph) and confirming the summary line.
    """
    repo_root = Path(__file__).resolve().parents[2]
    proc = subprocess.run(
        [sys.executable, "-m", "pyfcstm.diagnostics"],
        cwd=str(repo_root),
        capture_output=True,
        text=True,
        timeout=120,
    )
    output = _strip_ansi(proc.stdout)
    summary_line = next(
        (ln for ln in output.splitlines() if ln.startswith("Smoke test summary:")),
        None,
    )
    assert summary_line is not None, (
        "python -m pyfcstm.diagnostics produced no summary line; runner "
        "may have crashed mid-flight.\nstdout:\n{}\nstderr:\n{}".format(
            output, proc.stderr,
        )
    )
    assert " PASS" in summary_line, summary_line


@pytest.mark.unittest
def test_smoke_runner_finishes_when_every_case_raises_baseexception(monkeypatch):
    """The runner must finish even when every single case explodes.

    This is the strongest possible reliability assertion: even with
    100% of the cases blowing up - across the whole BaseException
    family - the runner returns a summary count rather than crashing.
    """

    def _explode_runtime():
        raise RuntimeError("synthetic runtime")

    def _explode_systemexit():
        raise SystemExit(7)

    def _explode_keyboard():
        raise KeyboardInterrupt("synthetic ^C")

    def _explode_baseexc():
        raise BaseException("raw BaseException")

    cases = [
        SmokeCase("a", "raises RuntimeError", _explode_runtime),
        SmokeCase("b", "raises SystemExit",   _explode_systemexit),
        SmokeCase("c", "raises KeyboardInterrupt", _explode_keyboard),
        SmokeCase("d", "raises BaseException", _explode_baseexc),
    ]
    monkeypatch.setattr(
        smoke_module, "_build_case_groups", lambda: [("Synthetic", cases)],
    )
    buf = io.StringIO()
    with redirect_stdout(buf):
        failed = run_smoke_test()
    output = _strip_ansi(buf.getvalue())
    assert failed == 4, (
        "expected 4 failures (all cases blow up), got {}; output:\n{}".format(
            failed, output,
        )
    )
    # Each case appears as a FAIL row.
    for name in ("a", "b", "c", "d"):
        assert "[FAIL] " + name in output, (
            "case {!r} did not produce a FAIL row; output:\n{}".format(name, output)
        )
    assert "Smoke test summary" in output, (
        "no summary line - runner crashed; output:\n{}".format(output)
    )

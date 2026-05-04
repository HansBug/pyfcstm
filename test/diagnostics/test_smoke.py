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
import os
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
    _collect_environment_facts,
    _format_traceback,
    _run_one,
    _safe_env_value,
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
def test_safe_env_value_returns_placeholder_on_exception():
    """``_safe_env_value`` must turn *any* exception into a placeholder
    string instead of raising. The environment dump runs before any
    smoke case, and an exception there would prevent the whole battery
    from starting."""

    def _explode():
        raise OSError(28, "synthetic disk full")

    result = _safe_env_value(_explode)
    assert isinstance(result, str)
    assert "(unavailable" in result
    assert "OSError" in result


@pytest.mark.unittest
def test_safe_env_value_handles_baseexception_subtypes():
    """Even SystemExit / KeyboardInterrupt must be trapped inside the
    environment reader. The runner's defence-in-depth contract goes
    all the way down to fact collection."""

    for factory in (
        lambda: (_ for _ in ()).throw(SystemExit(1)),
        lambda: (_ for _ in ()).throw(KeyboardInterrupt("synthetic")),
        lambda: (_ for _ in ()).throw(BaseException("raw")),
    ):
        result = _safe_env_value(factory)
        assert isinstance(result, str), result
        assert "(unavailable" in result, result


@pytest.mark.unittest
def test_safe_env_value_stringifies_non_strings():
    """Numbers / booleans / None / objects must come back as strings."""
    assert _safe_env_value(lambda: 42) == "42"
    assert _safe_env_value(lambda: True) == "True"
    assert _safe_env_value(lambda: None) == "(none)"
    assert _safe_env_value(lambda: ["a", "b"]) == "['a', 'b']"


@pytest.mark.unittest
def test_environment_collector_returns_structured_sections():
    """Sanity: the collector returns one or more (label, [(k,v)]) tuples
    on a healthy interpreter, with at least the canonical Python /
    OS / Process sections present."""
    sections = _collect_environment_facts()
    section_labels = {label for label, _ in sections}
    assert "Python interpreter" in section_labels
    assert "OS / platform" in section_labels
    assert "Process" in section_labels
    assert "Locale / encoding" in section_labels
    assert "pyfcstm package" in section_labels

    # Every value is already stringified.
    for _label, rows in sections:
        for key, value in rows:
            assert isinstance(key, str)
            assert isinstance(value, str)


@pytest.mark.unittest
def test_environment_collector_does_not_crash_when_specific_readers_break(monkeypatch):
    """If individual platform readers are sabotaged, the collector
    still returns a structured result; the broken row carries the
    placeholder rather than the whole block being dropped."""

    def _broken_libc_ver():
        raise RuntimeError("synthetic platform.libc_ver() failure")

    def _broken_getcwd():
        raise OSError(2, "synthetic ENOENT on cwd")

    monkeypatch.setattr("platform.libc_ver", _broken_libc_ver, raising=False)
    monkeypatch.setattr("os.getcwd", _broken_getcwd)

    sections = _collect_environment_facts()
    flat = [
        (section, key, value)
        for section, rows in sections
        for key, value in rows
    ]
    # The broken cwd reader must surface as a placeholder under Process,
    # not abort the whole Process section nor the rest of the dump.
    cwd_row = next(
        ((s, k, v) for (s, k, v) in flat if s == "Process" and k == "cwd"),
        None,
    )
    assert cwd_row is not None, "cwd row dropped from Process section"
    assert "(unavailable" in cwd_row[2], cwd_row[2]
    # Sections downstream of the broken reader are still present.
    section_labels = {label for label, _ in sections}
    assert "Locale / encoding" in section_labels
    assert "Time" in section_labels
    assert "pyfcstm package" in section_labels


@pytest.mark.unittest
def test_run_smoke_test_survives_environment_collector_explosion(monkeypatch):
    """If the collector itself blows up (worse than any individual
    reader), :func:`run_smoke_test` still runs every smoke case.

    The environment dump is supposed to be a *header* in the output;
    a broken header must not gate the diagnostics body."""

    def _explode():
        raise RuntimeError("synthetic top-level collector failure")

    monkeypatch.setattr(smoke_module, "_collect_environment_facts", _explode)

    # Plant a tiny synthetic case battery so the run is fast and we
    # know exactly what to expect.
    monkeypatch.setattr(
        smoke_module, "_build_case_groups",
        lambda: [("Synthetic", [
            SmokeCase(name="ok", method="noop", func=lambda: None),
        ])],
    )

    buf = io.StringIO()
    with redirect_stdout(buf):
        failed = run_smoke_test()
    output = _strip_ansi(buf.getvalue())
    assert failed == 0, "case battery did not run; output:\n{}".format(output)
    assert "[PASS] ok" in output, output
    assert "environment introspection failed" in output, output


@pytest.mark.unittest
def test_build_info_facts_optional_in_dev_tree():
    """Without ``pyfcstm/config/build_info.py`` (dev/source mode), the
    build-info collector returns ``[]`` and never raises. The wider
    environment dump must still complete and contain the expected
    sections."""
    from pyfcstm.diagnostics.smoke import _collect_build_info_facts

    # Force-remove the module so the import inside the collector hits
    # the missing-file branch even if a previous test already imported
    # it.
    for mod in list(sys.modules):
        if mod == "pyfcstm.config.build_info":
            del sys.modules[mod]

    rows = _collect_build_info_facts()
    # Either the file is genuinely absent (rows == []) or it exists
    # with all-None placeholders (also no rows generated). Both are
    # "no baked build info"; both are valid dev-mode outputs.
    assert isinstance(rows, list)
    if rows:
        # If the test environment happens to have a build_info.py with
        # populated values, every row must still be a (str, str) pair.
        for key, value in rows:
            assert isinstance(key, str)
            assert isinstance(value, str)


@pytest.mark.unittest
def test_build_info_facts_with_populated_module(monkeypatch, tmp_path):
    """Inject a synthetic ``pyfcstm.config.build_info`` and confirm the
    collector surfaces every expected key (commit / branch / build
    time / dirty + files / host)."""
    import types

    from pyfcstm.diagnostics.smoke import _collect_build_info_facts

    fake_module = types.ModuleType("pyfcstm.config.build_info")
    fake_module.BUILD_COMMIT = "abc123def456"
    fake_module.BUILD_COMMIT_SHORT = "abc123def456"
    fake_module.BUILD_BRANCH = "test-branch"
    fake_module.BUILD_TIME_UTC = "2026-05-04T01:23:45Z"
    fake_module.BUILD_DIRTY = True
    fake_module.BUILD_DIRTY_FILES = ("path/a.py", "path/b.py")
    fake_module.BUILD_HOST = "test-host"
    monkeypatch.setitem(
        sys.modules, "pyfcstm.config.build_info", fake_module
    )

    rows = _collect_build_info_facts()
    flat = dict(rows)
    assert flat.get("baked commit") == "abc123def456"
    assert flat.get("baked branch") == "test-branch"
    assert flat.get("baked build time (UTC)") == "2026-05-04T01:23:45Z"
    assert flat.get("baked dirty?") == "yes"
    assert "path/a.py" in flat.get("baked dirty files", "")
    assert "path/b.py" in flat.get("baked dirty files", "")
    assert flat.get("baked build host") == "test-host"


@pytest.mark.unittest
def test_build_info_facts_swallows_corrupt_module(monkeypatch):
    """A corrupt ``pyfcstm.config.build_info`` (e.g. it raises during
    its own initialization) must surface as a placeholder row rather
    than tearing down the diagnostics dump."""
    import types

    from pyfcstm.diagnostics.smoke import _collect_build_info_facts

    class _BoomModule(types.ModuleType):
        def __getattr__(self, name):
            raise RuntimeError("synthetic build_info corruption: " + name)

    monkeypatch.setitem(
        sys.modules,
        "pyfcstm.config.build_info",
        _BoomModule("pyfcstm.config.build_info"),
    )

    # Each ``getattr`` call inside the collector becomes a placeholder.
    # The collector itself must not raise.
    rows = _collect_build_info_facts()
    assert isinstance(rows, list)


@pytest.mark.unittest
def test_classify_build_mode_dev_tree_with_git():
    """Dev source tree (no build_info, has .git) gets the source-mode line."""
    from pyfcstm.diagnostics.smoke import _classify_build_mode

    text = _classify_build_mode(has_build_info=False, has_git=True)
    assert "source / dev checkout" in text
    assert not text.startswith("WARNING:")


@pytest.mark.unittest
def test_classify_build_mode_packaged_install():
    """Packaged install (build_info present, no .git) is described as such."""
    from pyfcstm.diagnostics.smoke import _classify_build_mode

    text = _classify_build_mode(has_build_info=True, has_git=False)
    assert "packaged install" in text
    assert not text.startswith("WARNING:")


@pytest.mark.unittest
def test_classify_build_mode_frozen_with_build_info(monkeypatch):
    """Frozen exe with baked build info is the expected PyInstaller case."""
    from pyfcstm.diagnostics import smoke as smoke_module

    monkeypatch.setattr(smoke_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(smoke_module.sys, "_MEIPASS", "/tmp/_MEIfake", raising=False)

    text = smoke_module._classify_build_mode(has_build_info=True, has_git=False)
    assert "frozen PyInstaller" in text
    assert "baked build info present" in text
    assert not text.startswith("WARNING:")


@pytest.mark.unittest
def test_classify_build_mode_frozen_without_build_info_warns(monkeypatch):
    """Frozen exe missing baked build info MUST raise a WARNING.

    This is the canary for "tools/write_build_info.py was skipped at
    build time"; without the warning, a user would see an opaque exe
    with no way to recover commit / build-time state."""
    from pyfcstm.diagnostics import smoke as smoke_module

    monkeypatch.setattr(smoke_module.sys, "frozen", True, raising=False)
    monkeypatch.setattr(smoke_module.sys, "_MEIPASS", "/tmp/_MEIfake", raising=False)

    text = smoke_module._classify_build_mode(has_build_info=False, has_git=False)
    assert text.startswith("WARNING:")
    assert "missing" in text
    assert "rebuild" in text.lower() or "Rebuild" in text


@pytest.mark.unittest
def test_environment_dump_includes_build_mode_row():
    """The Build / git section must always include a ``mode`` row, even
    in dev tree where no baked info exists. The mode line is the user's
    primary signal for "how am I running this binary right now?"."""
    sections = _collect_environment_facts()
    build_section = dict(sections).get("Build / git")
    assert build_section is not None, "Build / git section missing"
    keys = [k for k, _ in build_section]
    assert "mode" in keys, (
        "Build / git section missing required 'mode' row; got rows: {}".format(keys)
    )


@pytest.mark.unittest
def test_diagnostics_main_returns_int_failure_count():
    """``pyfcstm.diagnostics.__main__:main`` returns the failed-case
    count as an int, even if the install is healthy (= 0).
    """
    from pyfcstm.diagnostics.__main__ import main

    rc = main()
    assert isinstance(rc, int), "main() return type: {!r}".format(type(rc))
    # On a clean dev tree we expect zero failures; if this test fires
    # in a context where a case legitimately fails, the assertion
    # message will surface that.
    assert rc >= 0, "main() returned negative count: {}".format(rc)


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

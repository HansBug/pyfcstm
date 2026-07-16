"""Render one frozen self-check snapshot through bounded output channels.

Human and JSON output share the same immutable snapshot. The module also owns
atomic JSON report replacement and the Windows 7 console color fallback; the
bootstrap owns last-resort output recovery.
"""

import json
import os
import sys
import tempfile
from typing import Optional

from ._win32 import write_console_ansi
from .model import ReportSnapshot


_STATUS_ORDER = (
    "PASS",
    "WARN",
    "SKIP",
    "BLOCKED",
    "FAIL",
    "ERROR",
    "TIMEOUT",
    "CRASH",
)
_FAILURE_STATUSES = ("BLOCKED", "FAIL", "ERROR", "TIMEOUT", "CRASH")
_FULL_DETAIL_STATUSES = ("BLOCKED", "FAIL", "ERROR", "TIMEOUT", "CRASH")
_STATUS_COLORS = {status: "\x1b[31m" for status in _FAILURE_STATUSES}
_STATUS_COLORS.update({"PASS": "\x1b[32m", "WARN": "\x1b[33m", "SKIP": "\x1b[36m"})


def _windows_vt_supported(stream) -> bool:
    """Return whether the current Windows console accepts VT sequences.

    Windows 7 consoles do not expose ``ENABLE_VIRTUAL_TERMINAL_PROCESSING``;
    those consoles deliberately fall back to stable uncoloured status labels.
    """
    if os.name != "nt":
        return True
    try:
        import ctypes
        from ctypes import wintypes
    except (ImportError, ValueError):
        # Python 3.7 POSIX builds may reject ctypes.wintypes during import.
        return False
    try:
        kernel32 = ctypes.windll.kernel32
        get_std_handle = kernel32.GetStdHandle
        get_std_handle.argtypes = [wintypes.DWORD]
        get_std_handle.restype = wintypes.HANDLE
        get_console_mode = kernel32.GetConsoleMode
        get_console_mode.argtypes = [
            wintypes.HANDLE,
            ctypes.POINTER(wintypes.DWORD),
        ]
        get_console_mode.restype = wintypes.BOOL
        handle = get_std_handle(-11)
        mode = wintypes.DWORD()
        if not get_console_mode(handle, ctypes.byref(mode)):
            return False
        return bool(mode.value & 0x0004)
    except (AttributeError, OSError, TypeError, ValueError, ctypes.ArgumentError):
        return False


def _color_requested(mode: str) -> bool:
    """Resolve whether the user/environment requested colored human output."""
    if mode in ("never", "always"):
        return mode == "always"
    if os.environ.get("NO_COLOR", "").strip():
        return False
    if os.environ.get("FORCE_COLOR") == "1":
        return True
    return bool(getattr(sys.stdout, "isatty", lambda: False)())  # pragma: no branch


def render_json(snapshot: ReportSnapshot) -> str:
    """
    Render one canonical JSON snapshot without ANSI output.

    :param snapshot: Frozen snapshot to serialize.
    :type snapshot: ReportSnapshot
    :return: Canonical JSON text without a trailing newline.
    :rtype: str

    Example::

        >>> render_json(ReportSnapshot((), {}, {})).startswith('{')
        True
    """
    return json.dumps(
        snapshot.to_dict(), ensure_ascii=True, sort_keys=True, separators=(",", ":")
    )


def _paint_status(status: str, use_color: bool) -> str:
    """Format one status token, optionally wrapped in ANSI color."""
    if not use_color:
        return status
    return "{}{}\x1b[0m".format(_STATUS_COLORS.get(status, ""), status)


def _stream_color_state(color: str):
    """Return the requested/VT-safe color state for incremental output."""
    requested = _color_requested(color)
    return requested and _windows_vt_supported(sys.stdout)


def _write_human_text(text: str, color: str = "auto") -> None:
    """Write a human fragment immediately, including the Win7 fallback."""
    requested = _color_requested(color)
    ansi = requested and _windows_vt_supported(sys.stdout)
    if requested and os.name == "nt" and not ansi:
        if write_console_ansi(text, sys.stdout):
            return
    try:
        sys.stdout.write(text)
        sys.stdout.flush()
    except (UnicodeError, OSError, ValueError) as err:
        # Legacy Windows consoles and redirected streams can reject a Unicode
        # diagnostic.  ASCII backslash escapes keep the result observable.
        fallback = text.encode("ascii", "backslashreplace").decode("ascii")
        try:
            sys.stdout.write(fallback)
            sys.stdout.flush()
        except (UnicodeError, OSError, ValueError):
            # The bootstrap's emergency channel handles a completely closed
            # stdout; do not hide the original encoding/stream failure here.
            raise err


def _stream_version_line(profile: str, use_color: bool) -> str:
    """Build the cheap first line emitted before dependency discovery."""
    try:
        from pyfcstm.config.meta import __VERSION__
    except (ImportError, AttributeError):
        # The bootstrap still reports a useful line if package metadata is damaged.
        version = "unavailable"
    else:
        version = __VERSION__
    mode = "frozen" if getattr(sys, "frozen", False) else "source"
    cyan = "\x1b[36m" if use_color else ""
    reset = "\x1b[0m" if use_color else ""
    return "{}pyfcstm self-check {}  mode={}  profile={}{}\n".format(
        cyan, version, mode, profile, reset
    )


def write_human_start(profile: str = "default", color: str = "auto") -> None:
    """Flush the lightweight human-mode header before checks start."""
    _write_human_text(_stream_version_line(profile, _stream_color_state(color)), color)


def write_human_plan(total: int, profile: str, color: str = "auto") -> None:
    """Flush the selected-check count as soon as the static registry is ready."""
    _write_human_text(
        "pyfcstm self-check: running {} checks  profile={}\n".format(
            total, profile
        ),
        color,
    )


def write_human_environment(environment, color: str = "auto") -> None:
    """Flush the collected system and build identity line before probes run."""
    revision = environment.get("revision") or "unavailable"
    commit = environment.get("commit") or "unavailable"
    platform_name = environment.get("platform") or "unavailable"
    architecture = environment.get("architecture") or environment.get("machine")
    python_version = environment.get("python_version") or "unavailable"
    implementation = environment.get("implementation") or "unavailable"
    encoding = next(
        (
            environment.get(key)
            for key in ("stdout_encoding", "preferred_encoding", "filesystem_encoding")
            if environment.get(key)
        ),
        "unavailable",
    )
    _write_human_text(
        "System: {} {}  Python={} ({})  encoding={}  revision={}  commit={}\n".format(
            platform_name,
            architecture or "unavailable",
            python_version,
            implementation,
            encoding,
            revision,
            commit,
        ),
        color,
    )


def _diagnostic_text_lines(check) -> list:
    """Return non-empty traceback and process-output diagnostic blocks."""
    lines = []
    evidence = check.evidence
    exception = check.exception
    if exception and evidence.rstrip().endswith(exception.rstrip()):
        evidence = evidence[: -len(exception.rstrip())].rstrip()
    for name, value in (
        ("evidence", evidence),
        ("exception", exception),
        ("stdout", check.stdout),
        ("stderr", check.stderr),
    ):
        if value:
            lines.append(name + ":")
            lines.extend("  " + line for line in value.splitlines())
    return lines


def _warning_detail_lines(check) -> list:
    """Return moderate diagnostics for an optional warning."""
    fields = (
        ("reason", check.reason),
        ("expected", check.expected),
        ("observed", check.observed),
        ("remediation", check.remediation),
    )
    lines = [
        "{}: {}".format(name, value) for name, value in fields if value is not None
    ]
    lines.extend(_diagnostic_text_lines(check))
    return ["  " + line for line in lines]


def _failure_detail_lines(check) -> list:
    """Return complete diagnostics for a failing red-status check."""
    fields = (
        ("reason", check.reason),
        (
            "prerequisite",
            ", ".join(check.prerequisites) if check.prerequisites else None,
        ),
        ("expected", check.expected),
        ("observed", check.observed),
        ("remediation", check.remediation),
        ("return_code", check.return_code),
        ("pid", check.pid),
        ("signal", check.signal),
        ("ntstatus", check.ntstatus),
        ("timeout", "true" if check.timeout else None),
        ("truncated_bytes", check.truncated_bytes or None),
        (
            "duration_ms",
            "{:.1f}".format(check.duration_ms) if check.duration_ms else None,
        ),
    )
    lines = [
        "{}: {}".format(name, value) for name, value in fields if value is not None
    ]
    lines.extend(_diagnostic_text_lines(check))
    return ["  " + line for line in lines]


def _result_summary(check) -> str:
    """Return one concrete summary, including PASS expected/observed facts."""
    summary = " ".join(str(check.summary or check.reason or "no summary").split())
    if check.status == "SKIP" and check.prerequisites:
        return "{}: {}".format(summary, ", ".join(check.prerequisites))
    if check.status != "PASS":
        return summary
    facts = []
    if check.expected is not None:
        facts.append("expected={}".format(" ".join(str(check.expected).split())))
    if check.observed is not None:
        facts.append("observed={}".format(" ".join(str(check.observed).split())))
    return "{}; {}".format(summary, "; ".join(facts)) if facts else summary


def _result_detail_lines(check) -> list:
    """Return status-appropriate human diagnostics for one completed check."""
    if check.status == "WARN":
        return _warning_detail_lines(check)
    if check.status in _FULL_DETAIL_STATUSES:
        return _failure_detail_lines(check)
    return []


def render_human_result(
    check, index: int, total: int, color: str = "auto"
) -> str:
    """Render one completed check for incremental human output.

    :param check: Completed :class:`CheckResult` instance.
    :param index: One-based position in the selected registry.
    :param total: Number of selected checks.
    :param color: ``auto``, ``always``, or ``never``.
    :return: One newline-terminated result fragment.
    :rtype: str
    """
    use_color = _color_requested(color) and _windows_vt_supported(sys.stdout)
    index_width = len(str(max(1, total)))
    position = "[{:>{}}/{}]".format(index, index_width, total)
    status = _paint_status(check.status, use_color)
    summary = _result_summary(check)
    lines = ["{} {} {} ({})".format(position, status, check.check_id, summary)]
    lines.extend(_result_detail_lines(check))
    return "\n".join(lines) + "\n"


def write_human_result(check, index: int, total: int, color: str = "auto") -> None:
    """Flush one completed check and its failure details immediately."""
    _write_human_text(render_human_result(check, index, total, color), color)


def _summary_lines(snapshot: ReportSnapshot, use_color: bool):
    """Build positive-count summary and the final styled conclusion."""
    counts = snapshot.counts
    lines = ["", "Summary:"]
    for status in _STATUS_ORDER:
        count = counts.get(status, 0)
        if count <= 0:
            continue
        lines.append("  {} = {}".format(_paint_status(status, use_color), count))
    exit_code = snapshot.metadata.get("exit_code")
    failed = exit_code not in (None, 0)
    if not failed and exit_code is None:
        failed = sum(counts.get(status, 0) for status in _FAILURE_STATUSES) > 0
    conclusion = "FAILED" if failed else "PASSED"
    if not failed and any(
        counts.get(status, 0) for status in ("WARN", "SKIP", "BLOCKED")
    ):
        conclusion = "WARNINGS"
    if use_color:
        conclusion_style = {
            "PASSED": "\x1b[1;32m",
            "WARNINGS": "\x1b[1;33m",
            "FAILED": "\x1b[1;97;41m",
        }[conclusion]
        conclusion = "{}[ {} ]\x1b[0m".format(conclusion_style, conclusion)
    else:
        conclusion = "[ {} ]".format(conclusion)
    lines.append("Conclusion: {}".format(conclusion))
    return lines


def render_human_summary(snapshot: ReportSnapshot, color: str = "auto") -> str:
    """Render only the final positive-count summary and conclusion."""
    use_color = _color_requested(color) and _windows_vt_supported(sys.stdout)
    return "\n".join(_summary_lines(snapshot, use_color)) + "\n"


def write_human_summary(snapshot: ReportSnapshot, color: str = "auto") -> None:
    """Flush the final summary after all incremental result lines."""
    _write_human_text(render_human_summary(snapshot, color), color)


def _render_human(snapshot: ReportSnapshot, use_color: bool) -> str:
    """Render one human report with a fixed, terminal-friendly layout."""
    total = len(snapshot.checks)
    environment = snapshot.metadata.get("environment", {})
    version, revision, commit = (
        environment.get(key) or "unavailable"
        for key in ("version", "revision", "commit")
    )
    mode = "frozen" if environment.get("frozen") else "source"
    platform_name = environment.get("platform") or "unavailable"
    architecture = environment.get("architecture") or environment.get("machine")
    python_version, implementation = (
        environment.get(key) or "unavailable"
        for key in ("python_version", "implementation")
    )
    encoding = next(
        (
            environment.get(key)
            for key in ("stdout_encoding", "preferred_encoding", "filesystem_encoding")
            if environment.get(key)
        ),
        "unavailable",
    )
    cyan = "\x1b[36m" if use_color else ""
    reset = "\x1b[0m" if use_color else ""
    lines = [
        "{}pyfcstm self-check {}  revision={}  commit={}  mode={}{}".format(
            cyan, version, revision, commit, mode, reset
        ),
        "System: {} {}  Python={} ({})  encoding={}".format(
            platform_name,
            architecture or "unavailable",
            python_version,
            implementation,
            encoding,
        ),
        "pyfcstm self-check: running {} checks".format(total),
        "",
    ]
    index_width = len(str(max(1, total)))
    for index, check in enumerate(snapshot.checks, 1):
        summary = _result_summary(check)
        position = "[{:>{}}/{}]".format(index, index_width, total)
        status = _paint_status(check.status, use_color)
        lines.append("{} {} {} ({})".format(position, status, check.check_id, summary))
        lines.extend(_result_detail_lines(check))

    lines.extend(_summary_lines(snapshot, use_color)[1:])
    return "\n".join(lines) + "\n"


def render_human(snapshot: ReportSnapshot, color: str = "auto") -> str:
    """
    Render a human-readable report.

    :param snapshot: Frozen snapshot to render.
    :type snapshot: ReportSnapshot
    :param color: ``auto``, ``always``, or ``never``.
    :type color: str
    :return: Human report text.
    :rtype: str

    Example::

        >>> "running 0 checks" in render_human(ReportSnapshot((), {}, {}), color="never")
        True
    """
    use_color = _color_requested(color) and _windows_vt_supported(sys.stdout)
    return _render_human(snapshot, use_color=use_color)


def write_human(snapshot: ReportSnapshot, color: str = "auto") -> None:
    """Write a human report with ANSI or the Windows 7 attribute fallback.

    :param snapshot: Frozen snapshot to render and emit.
    :type snapshot: ReportSnapshot
    :param color: ``auto``, ``always``, or ``never``.
    :type color: str
    :return: ``None``.
    :rtype: None

    Example::

        >>> import contextlib
        >>> import io
        >>> stream = io.StringIO()
        >>> with contextlib.redirect_stdout(stream):
        ...     write_human(ReportSnapshot((), {}, {}), color="never")
        >>> "running 0 checks" in stream.getvalue()
        True
    """
    requested = _color_requested(color)
    ansi = requested and _windows_vt_supported(sys.stdout)
    if requested and os.name == "nt" and not ansi:
        if write_console_ansi(_render_human(snapshot, use_color=True), sys.stdout):
            return
    sys.stdout.write(_render_human(snapshot, use_color=ansi))
    sys.stdout.flush()


def write_report(path: str, snapshot: ReportSnapshot) -> Optional[str]:
    """
    Atomically write a report beside its destination.

    :param path: Destination JSON report path.
    :type path: str
    :param snapshot: Frozen snapshot to serialize.
    :type snapshot: ReportSnapshot
    :return: ``None`` on success or a diagnostic string on failure.
    :rtype: Optional[str]

    Example::

        >>> with tempfile.TemporaryDirectory() as directory:
        ...     path = os.path.join(directory, "report.json")
        ...     error = write_report(path, ReportSnapshot((), {}, {}))
        >>> error is None
        True
    """
    parent = os.path.dirname(os.path.abspath(path)) or "."
    temporary = None
    try:
        if not os.path.isdir(parent):
            return "report_directory_missing"
        descriptor, temporary = tempfile.mkstemp(
            prefix=".pyfcstm-selfcheck-", suffix=".tmp", dir=parent
        )
        with os.fdopen(descriptor, "w", encoding="utf-8") as stream:
            stream.write(render_json(snapshot))
            stream.write("\n")
            stream.flush()
            os.fsync(stream.fileno())
        os.replace(temporary, path)
        temporary = None
        return None
    except (OSError, UnicodeError, ValueError) as err:
        # Permission, encoding, and atomic-replace errors must remain diagnostic.
        return "{}: {}".format(type(err).__name__, err)
    finally:
        if temporary is not None:
            try:
                os.unlink(temporary)
            except OSError:
                pass

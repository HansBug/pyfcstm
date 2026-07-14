"""Render one frozen self-check snapshot through bounded output channels.

Human and JSON output share the same immutable snapshot. The module also owns
atomic JSON report replacement, Windows 7 console color fallback, and the
last-resort stdout/stderr/raw-fd/temporary-file diagnostic chain.
"""

import json
import errno
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
_STATUS_COLORS = {status: "\x1b[31m" for status in _FAILURE_STATUSES}
_STATUS_COLORS.update({"PASS": "\x1b[32m", "WARN": "\x1b[33m", "SKIP": "\x1b[36m"})


def _silence_broken_stdout(error: BaseException) -> None:
    """Redirect a broken stdout descriptor so interpreter shutdown stays stable."""
    if (
        not isinstance(error, BrokenPipeError)
        and getattr(error, "errno", None) != errno.EPIPE
    ):
        return
    replacement = None
    descriptor = None
    try:
        descriptor = sys.stdout.fileno()
        replacement = os.open(os.devnull, os.O_WRONLY)
        if replacement != descriptor:
            os.dup2(replacement, descriptor)
    except (AttributeError, OSError, ValueError):
        # StringIO lacks fileno, fd operations can fail, and closed streams can
        # reject fileno with ValueError; the emergency channel still continues.
        return
    finally:
        if replacement is not None and replacement != descriptor:
            try:
                os.close(replacement)
            except OSError:
                # The replacement may already be closed after a failed dup2.
                pass


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
    return os.environ.get("FORCE_COLOR") == "1" or bool(
        getattr(sys.stdout, "isatty", lambda: False)()
    )


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


def _failure_detail_lines(check) -> list:
    """Return indented diagnostics for a non-successful check."""
    fields = (
        ("reason", check.reason),
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
    for name, value in (
        ("evidence", check.evidence),
        ("stdout", check.stdout),
        ("stderr", check.stderr),
    ):
        if value:
            lines.append(name + ":")
            lines.extend("  " + line for line in value.splitlines())
    return ["  " + line for line in lines]


def _render_human(snapshot: ReportSnapshot, use_color: bool) -> str:
    """Render one human report with a fixed, terminal-friendly layout."""
    counts = snapshot.counts
    total = len(snapshot.checks)
    environment = snapshot.metadata.get("environment", {})
    version = environment.get("version") or "unavailable"
    revision = environment.get("revision") or "unavailable"
    mode = "frozen" if environment.get("frozen") else "source"
    platform_name = environment.get("platform") or "unavailable"
    architecture = environment.get("architecture") or environment.get("machine")
    python_version = environment.get("python_version") or "unavailable"
    implementation = environment.get("implementation") or "unavailable"
    encoding = (
        environment.get("stdout_encoding")
        or environment.get("preferred_encoding")
        or environment.get("filesystem_encoding")
        or "unavailable"
    )
    cyan = "\x1b[36m" if use_color else ""
    reset = "\x1b[0m" if use_color else ""
    lines = [
        "{}pyfcstm self-check {}  revision={}  mode={}{}".format(
            cyan, version, revision, mode, reset
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
        summary = check.summary or check.reason or "no summary"
        position = "[{:>{}}/{}]".format(index, index_width, total)
        status = _paint_status(check.status, use_color)
        lines.append("{} {} {} ({})".format(position, status, check.check_id, summary))
        if check.status in _FAILURE_STATUSES:
            lines.extend(_failure_detail_lines(check))

    lines.extend(("", "Summary:"))
    for status in _STATUS_ORDER:
        count = counts.get(status, 0)
        if count <= 0:
            continue
        label = _paint_status(status, use_color)
        lines.append("  {} = {}".format(label, count))
    exit_code = snapshot.metadata.get("exit_code")
    failed = exit_code not in (None, 0) or (
        exit_code is None and any(counts.get(status, 0) for status in _FAILURE_STATUSES)
    )
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
        conclusion = "{}[ {} ]{}".format(conclusion_style, conclusion, reset)
    else:
        conclusion = "[ {} ]".format(conclusion)
    lines.append("Conclusion: {}".format(conclusion))
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


def emergency_write(message: str, output_format: str = "human") -> Optional[str]:
    """
    Attempt the documented stdout/stderr/raw-fd emergency chain.

    :param message: Diagnostic text to emit.
    :type message: str
    :param output_format: ``human`` or ``json``; JSON preserves stdout purity,
        defaults to ``'human'``.
    :type output_format: str, optional
    :return: Emergency report path when every stream is unavailable, otherwise
        ``None``.
    :rtype: Optional[str]

    Example::

        >>> import contextlib
        >>> import io
        >>> stream = io.StringIO()
        >>> with contextlib.redirect_stdout(stream):
        ...     result = emergency_write("diagnostic\\n")
        >>> result is None and stream.getvalue() == "diagnostic\\n"
        True
    """
    encoded = message.encode("utf-8", "backslashreplace")
    try:
        if output_format != "json":
            sys.stdout.write(message)
            sys.stdout.flush()
            return
    except (OSError, UnicodeError, ValueError) as err:
        _silence_broken_stdout(err)
        pass
    try:
        sys.stderr.buffer.write(encoded)
        sys.stderr.buffer.flush()
        return
    except (OSError, AttributeError, ValueError):
        pass
    try:
        os.write(2, encoded)
    except OSError:
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(
                prefix="pyfcstm-selfcheck-emergency-", suffix=".log"
            )
            try:
                os.write(descriptor, encoded)
                os.fsync(descriptor)
            finally:
                os.close(descriptor)
            return temporary
        except (OSError, ValueError):
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            return None

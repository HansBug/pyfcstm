"""Human, JSON, and emergency self-check reporting."""

import json
import os
import sys
import tempfile
from typing import Optional

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
_STATUS_COLORS = {
    "PASS": "\x1b[32m",
    "WARN": "\x1b[33m",
    "SKIP": "\x1b[36m",
    "BLOCKED": "\x1b[31m",
    "FAIL": "\x1b[31m",
    "ERROR": "\x1b[31m",
    "TIMEOUT": "\x1b[31m",
    "CRASH": "\x1b[31m",
}
_FAILURE_STATUSES = ("BLOCKED", "FAIL", "ERROR", "TIMEOUT", "CRASH")


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


def _color_enabled(mode: str) -> bool:
    """Resolve color mode with the documented environment overrides."""
    if mode == "never":
        return False
    if mode == "always":
        return _windows_vt_supported(sys.stdout)
    if os.environ.get("NO_COLOR", "").strip():
        return False
    if os.environ.get("FORCE_COLOR") == "1":
        return _windows_vt_supported(sys.stdout)
    return bool(
        getattr(sys.stdout, "isatty", lambda: False)()
    ) and _windows_vt_supported(sys.stdout)


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
    lines = []
    if check.reason:
        lines.append("reason: {}".format(check.reason))
    if check.return_code is not None:
        lines.append("return_code: {}".format(check.return_code))
    if check.pid is not None:
        lines.append("pid: {}".format(check.pid))
    if check.signal is not None:
        lines.append("signal: {}".format(check.signal))
    if check.ntstatus:
        lines.append("ntstatus: {}".format(check.ntstatus))
    if check.timeout:
        lines.append("timeout: true")
    if check.truncated_bytes:
        lines.append("truncated_bytes: {}".format(check.truncated_bytes))
    if check.duration_ms:
        lines.append("duration_ms: {:.1f}".format(check.duration_ms))
    if check.details:
        lines.append("details:")
        lines.extend("  " + line for line in check.details.splitlines())
    if check.stdout and "stdout:\n" not in check.details:
        lines.append("stdout:")
        lines.extend("  " + line for line in check.stdout.splitlines())
    if check.stderr and "stderr:\n" not in check.details:
        lines.append("stderr:")
        lines.extend("  " + line for line in check.stderr.splitlines())
    return ["  " + line for line in lines]


def _conclusion(snapshot, counts: dict) -> str:
    """Derive a human conclusion while preserving required-check exit policy."""
    exit_code = snapshot.metadata.get("exit_code")
    failed = (
        exit_code != 0
        if exit_code is not None
        else any(counts[status] for status in _FAILURE_STATUSES)
    )
    if failed:
        return "FAILED"
    if any(counts[status] for status in ("WARN", "SKIP", "BLOCKED")):
        return "WARNINGS"
    return "PASSED"


def _render_human(snapshot: ReportSnapshot, use_color: bool) -> str:
    """Render one human report with a fixed, terminal-friendly layout."""
    counts = {status: int(snapshot.counts.get(status, 0)) for status in _STATUS_ORDER}
    total = len(snapshot.checks)
    cyan = "\x1b[36m" if use_color else ""
    reset = "\x1b[0m" if use_color else ""
    lines = [
        "{}pyfcstm self-check: running {} checks{}".format(cyan, total, reset),
        "",
    ]
    for index, check in enumerate(snapshot.checks, 1):
        summary = check.summary or check.reason or "no summary"
        status = "[{}]".format(_paint_status(check.status, use_color))
        lines.append(
            "{} [{:02d}/{:02d}] {} ({})".format(
                status, index, total, check.check_id, summary
            )
        )
        if check.status in _FAILURE_STATUSES:
            lines.extend(_failure_detail_lines(check))

    lines.extend(("", "Summary:"))
    for status in _STATUS_ORDER:
        count = counts[status]
        if count <= 0:
            continue
        label = _paint_status(status, use_color)
        lines.append("  {} = {}".format(label, count))
    conclusion = _conclusion(snapshot, counts)
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


def _render_human_fallback(snapshot: ReportSnapshot) -> str:
    """Render the same layout without ANSI when the primary path is broken."""
    return _render_human(snapshot, use_color=False)


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

        >>> render_human(ReportSnapshot((), {}, {}), color="never").splitlines()[0]
        'pyfcstm self-check: running 0 checks'
    """
    return _render_human(snapshot, use_color=_color_enabled(color))


def write_report(path: str, snapshot: ReportSnapshot) -> Optional[str]:
    """
    Atomically write a report beside its destination.

    :param path: Destination JSON report path.
    :type path: str
    :param snapshot: Frozen snapshot to serialize.
    :type snapshot: ReportSnapshot
    :return: ``None`` on success or a diagnostic string on failure.
    :rtype: Optional[str]
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
    except (OSError, IOError, UnicodeError, ValueError) as err:
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
    """
    encoded = message.encode("utf-8", "backslashreplace")
    try:
        if output_format != "json":
            sys.stdout.write(message)
            sys.stdout.flush()
            return
    except (OSError, UnicodeError, ValueError):
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
        descriptor = None
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(
                prefix="pyfcstm-selfcheck-emergency-", suffix=".log"
            )
            os.write(descriptor, encoded)
            os.fsync(descriptor)
            os.close(descriptor)
            descriptor = None
            return temporary
        except (OSError, ValueError):
            if descriptor is not None:
                try:
                    os.close(descriptor)
                except OSError:
                    pass
            if temporary is not None:
                try:
                    os.unlink(temporary)
                except OSError:
                    pass
            return None

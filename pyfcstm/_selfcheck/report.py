"""Human, JSON, and emergency self-check reporting."""

import json
import os
import sys
import tempfile
from typing import Optional

from .model import ReportSnapshot


def _color_enabled(mode: str) -> bool:
    """Resolve color mode with the documented environment overrides."""
    if mode == "never":
        return False
    if mode == "always":
        return True
    if os.environ.get("NO_COLOR") is not None:
        return False
    if os.environ.get("FORCE_COLOR") == "1":
        return True
    return bool(getattr(sys.stdout, "isatty", lambda: False)())


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
        'pyfcstm self-check'
    """
    use_color = _color_enabled(color)
    green = "\x1b[32m" if use_color else ""
    red = "\x1b[31m" if use_color else ""
    yellow = "\x1b[33m" if use_color else ""
    reset = "\x1b[0m" if use_color else ""
    lines = ["pyfcstm self-check", "=================="]
    for check in snapshot.checks:
        prefix = (
            green
            if check.status == "PASS"
            else yellow
            if check.status in ("WARN", "SKIP")
            else red
        )
        lines.append(
            "{}{} {}: {}{}".format(
                prefix, check.status, check.check_id, check.summary, reset
            )
        )
        if check.status not in ("PASS", "WARN", "SKIP") and check.details:
            lines.append(check.details)
    lines.append("Counts: {}".format(json.dumps(dict(snapshot.counts), sort_keys=True)))
    return "\n".join(lines) + "\n"


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


def emergency_write(message: str, output_format: str = "human") -> None:
    """
    Attempt the documented stdout/stderr/raw-fd emergency chain.

    :param message: Diagnostic text to emit.
    :type message: str
    :param output_format: ``human`` or ``json``; JSON preserves stdout purity,
        defaults to ``'human'``.
    :type output_format: str, optional
    :return: ``None``.
    :rtype: None
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
        pass

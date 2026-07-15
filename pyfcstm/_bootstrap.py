"""
Minimal command bootstrap for version reporting.

The bootstrap deliberately depends only on the Python standard library and
the lightweight :mod:`pyfcstm.config` namespace. This lets a damaged optional
CLI dependency be diagnosed with a version command before Click and command
implementations are imported.

Example::

    >>> from pyfcstm._bootstrap import is_version_request
    >>> is_version_request(['--version'])
    True
"""

import errno
import os
import platform
import sys
import json
import tempfile
import traceback
from typing import Optional, Sequence

from .config import BUILD_COMMIT, BUILD_REVISION, BUILD_TIME_UTC
from .config.meta import __AUTHOR__, __AUTHOR_EMAIL__, __TITLE__, __VERSION__
from ._selfcheck.arguments import _WORKER_DISPATCH_ARGUMENT
from ._selfcheck.arguments import _requested_output_format
from ._selfcheck.arguments import format_selfcheck_help
from ._selfcheck.arguments import format_worker_help


_VERSION_ARGUMENTS = ("-v", "-V", "--version")


def _write_stream_all(stream, data) -> None:
    """Write all bytes/text or raise when the diagnostic channel short-writes."""
    offset = 0
    while offset < len(data):
        written = stream.write(data[offset:])
        if not isinstance(written, int) or written <= 0 or written > len(data) - offset:
            raise OSError(errno.EIO, "diagnostic stream short write")
        offset += written


def _write_fd_all(descriptor: int, data: bytes) -> None:
    """Write all bytes to a raw descriptor or raise on a short write."""
    offset = 0
    while offset < len(data):
        written = os.write(descriptor, data[offset:])
        if not isinstance(written, int) or written <= 0 or written > len(data) - offset:
            raise OSError(errno.EIO, "diagnostic descriptor short write")
        offset += written


def is_version_request(arguments: Sequence[str]) -> bool:
    """
    Return whether arguments are exactly one root-level version request.

    :param arguments: Command-line arguments without the executable name.
    :type arguments: Sequence[str]
    :return: Whether the bootstrap should print version information itself.
    :rtype: bool

    Example::

        >>> is_version_request(("--version",))
        True
    """
    return len(arguments) == 1 and arguments[0] in _VERSION_ARGUMENTS


def run_selfcheck(arguments: Sequence[str]) -> int:
    """
    Lazily dispatch the standard-library self-check supervisor.

    :param arguments: Arguments after ``--self-check``.
    :type arguments: Sequence[str]
    :return: Stable self-check exit code.
    :rtype: int

    Example::

        >>> import contextlib
        >>> import io
        >>> with contextlib.redirect_stdout(io.StringIO()):
        ...     code = run_selfcheck(("--format", "json", "--network"))
        >>> code
        2
    """
    from ._selfcheck.supervisor import run_supervisor

    return run_supervisor(arguments)


def run_worker(arguments: Sequence[str]) -> int:
    """
    Lazily parse and dispatch the hidden worker without importing Click.

    :param arguments: Arguments after the hidden worker token.
    :type arguments: Sequence[str]
    :return: Worker process exit code.
    :rtype: int

    Example::

        >>> run_worker(("--check-id", "demo", "--worker-key", "demo",
        ...             "--nonce", "invalid", "--result-mode", "stdout"))
        3
    """
    from ._selfcheck.arguments import SelfCheckArgumentError
    from ._selfcheck.arguments import parse_worker_args
    from ._selfcheck.worker import run_worker as execute_worker

    try:
        options = parse_worker_args(arguments)
    except SelfCheckArgumentError:
        return 3
    return execute_worker(options.__dict__)


def _emit_bootstrap_error(message: str, output_format: str = "human") -> int:
    """Write a last-resort diagnostic without importing the normal CLI graph."""
    if output_format == "json":
        result = dict.fromkeys(
            "id group title status required duration_ms summary reason expected "
            "observed evidence remediation prerequisite exception pid returncode "
            "signal ntstatus timeout transport stdout stderr encoding truncated_bytes".split(),
            None,
        )
        result.update(
            id="selfcheck.infrastructure",
            group="selfcheck",
            title="self-check bootstrap error",
            status="ERROR",
            required=True,
            duration_ms=0.0,
            summary="self-check bootstrap error",
            reason="bootstrap_error",
            evidence=message,
            exception=message,
            prerequisite=[],
            timeout=False,
            stdout="",
            stderr="",
            encoding="utf-8",
            truncated_bytes=0,
        )
        data = (
            json.dumps(
                {
                    "schema_version": "pyfcstm-selfcheck/v1",
                    "report_id": None,
                    "started_at": None,
                    "finished_at": None,
                    "profile": None,
                    "environment": {},
                    "artifact": {},
                    "dependencies": [],
                    "capabilities": {},
                    "results": [result],
                    "summary": {"ERROR": 1},
                    "exit_code": 3,
                },
                ensure_ascii=True,
                sort_keys=True,
                separators=(",", ":"),
            )
            + "\n"
        ).encode("ascii")
        try:
            _write_stream_all(sys.stdout.buffer, data)
            sys.stdout.buffer.flush()
            return 3
        except AttributeError as err:
            # A text-only stdout has no binary buffer, so the complete payload
            # can safely use its text interface.
            _silence_broken_stdout(err)
            try:
                _write_stream_all(sys.stdout, data.decode("ascii"))
                sys.stdout.flush()
                return 3
            except (AttributeError, OSError, UnicodeError, ValueError) as text_error:
                # Fall through to the raw stderr channel when stdout is unavailable.
                _silence_broken_stdout(text_error)
                pass
        except (OSError, ValueError) as err:
            # A binary short write may have left a partial JSON prefix in the
            # stream; never append a second JSON document through that channel.
            _silence_broken_stdout(err)
    _emergency_write(
        ("self-check bootstrap error: " + message + "\n").encode(
            "utf-8", "backslashreplace"
        )
    )
    return 3


def _run_guarded(action, arguments: Sequence[str], output_format: str) -> int:
    """Run one bootstrap action behind the final diagnostic boundary."""
    try:
        return action(arguments)
    except KeyboardInterrupt:
        return 130
    except BaseException as err:
        # Import/runtime Exceptions and SystemExit are reportable; other
        # control sentinels propagate from this final boundary.
        if not isinstance(err, (Exception, SystemExit)):
            raise
        _silence_broken_stdout(err)
        traceback_text = traceback.format_exc()
        return _emit_bootstrap_error(
            "{}: {}\n{}".format(type(err).__name__, err, traceback_text),
            output_format,
        )


def _silence_broken_stdout(error: BaseException) -> None:
    """Redirect an EPIPE stdout descriptor before interpreter shutdown."""
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
        return
    finally:
        if replacement is not None and replacement != descriptor:
            try:
                os.close(replacement)
            except OSError:
                pass


def _emergency_write(data: bytes) -> Optional[str]:
    """Write bytes through stderr, raw fd two, then a private temp file."""
    try:
        _write_stream_all(sys.stderr.buffer, data)
        sys.stderr.buffer.flush()
        return None
    except (AttributeError, OSError, ValueError):
        pass
    try:
        _write_fd_all(2, data)
        return None
    except OSError:
        temporary = None
        try:
            descriptor, temporary = tempfile.mkstemp(
                prefix="pyfcstm-selfcheck-emergency-", suffix=".log"
            )
            try:
                _write_fd_all(descriptor, data)
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


def format_version_info() -> str:
    """
    Format human-readable package and optional build identity information.

    :return: Multi-line version information without a trailing newline.
    :rtype: str

    Example::

        >>> "Python:" in format_version_info()
        True
    """
    lines = [
        "{0}, version {1}.".format(__TITLE__.capitalize(), __VERSION__),
        "Developed by {0} ({1}).".format(__AUTHOR__, __AUTHOR_EMAIL__),
    ]
    if BUILD_REVISION is None:
        lines.append("Revision: unavailable")
    else:
        lines.append("Revision: {0}".format(BUILD_REVISION))
    if BUILD_COMMIT is not None:
        lines.append("Commit: {0}".format(BUILD_COMMIT))
    if BUILD_TIME_UTC is not None:
        lines.append("Built: {0}".format(BUILD_TIME_UTC))
    lines.extend(
        (
            "Python: {0}".format(platform.python_version()),
            "Platform: {0}".format(platform.platform()),
        )
    )
    return "\n".join(lines)


def main(arguments: Optional[Sequence[str]] = None) -> int:
    """
    Run the root command bootstrap or lazily dispatch to the Click CLI.

    :param arguments: Optional command-line arguments without the executable
        name. Defaults to :data:`sys.argv` when omitted.
    :type arguments: Optional[Sequence[str]]
    :return: ``0`` when the bootstrap handled a version request.
    :rtype: int

    Example::

        >>> main(("--version", "unexpected"))
        2
    """
    command_arguments = tuple(sys.argv[1:] if arguments is None else arguments)
    if is_version_request(command_arguments):
        sys.stdout.write(format_version_info() + "\n")
        return 0

    if command_arguments and command_arguments[0] in _VERSION_ARGUMENTS:
        # Root version flags never fall through to Click when combined with
        # other options.
        return 2
    if command_arguments and command_arguments[0] in (
        "--self-check",
        _WORKER_DISPATCH_ARGUMENT,
    ):
        dispatch, rest = command_arguments[0], command_arguments[1:]
        if any(item in ("-h", "--help") for item in rest):
            sys.stdout.write(
                format_selfcheck_help()
                if dispatch == "--self-check"
                else format_worker_help()
            )
            return 0
        conflict = "--self-check" in rest or (
            dispatch == "--self-check" and _WORKER_DISPATCH_ARGUMENT in rest
        )
        if conflict:
            return _emit_bootstrap_error(
                "--self-check and {} are mutually exclusive".format(
                    _WORKER_DISPATCH_ARGUMENT
                ),
                _requested_output_format(rest),
            )
        return _run_guarded(
            run_selfcheck if dispatch == "--self-check" else run_worker,
            rest,
            _requested_output_format(rest) if dispatch == "--self-check" else "human",
        )

    from .entry import pyfcstmcli

    pyfcstmcli(args=list(command_arguments), prog_name="pyfcstm")
    return 0

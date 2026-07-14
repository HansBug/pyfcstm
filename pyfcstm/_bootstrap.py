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

import os
import platform
import sys
import json
from typing import Optional, Sequence

from .config import BUILD_COMMIT, BUILD_REVISION, BUILD_TIME_UTC
from .config.meta import __AUTHOR__, __AUTHOR_EMAIL__, __TITLE__, __VERSION__
from ._selfcheck.arguments import _WORKER_DISPATCH_ARGUMENT
from ._selfcheck.arguments import _requested_output_format
from ._selfcheck.arguments import format_selfcheck_help
from ._selfcheck.arguments import format_worker_help


_VERSION_ARGUMENTS = ("-v", "-V", "--version")


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
                    "results": [
                        {
                            "id": "selfcheck.infrastructure",
                            "group": "selfcheck",
                            "title": "self-check bootstrap error",
                            "status": "ERROR",
                            "required": True,
                            "duration_ms": 0.0,
                            "summary": "self-check bootstrap error",
                            "reason": "bootstrap_error",
                            "expected": None,
                            "observed": None,
                            "evidence": message,
                            "remediation": None,
                            "prerequisite": [],
                            "exception": message,
                            "pid": None,
                            "returncode": None,
                            "signal": None,
                            "ntstatus": None,
                            "timeout": False,
                            "transport": None,
                            "stdout": "",
                            "stderr": "",
                            "encoding": "utf-8",
                            "truncated_bytes": 0,
                        }
                    ],
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
            sys.stdout.buffer.write(data)
            sys.stdout.buffer.flush()
            return 3
        except (AttributeError, OSError, ValueError):
            try:
                sys.stdout.write(data.decode("ascii"))
                sys.stdout.flush()
                return 3
            except (AttributeError, OSError, UnicodeError, ValueError):
                # Fall through to the raw stderr channel when stdout is unavailable.
                pass
    data = ("self-check bootstrap error: " + message + "\n").encode(
        "utf-8", "backslashreplace"
    )
    try:
        os.write(2, data)
    except OSError:
        # There is no stronger channel if the process has lost stderr.
        pass
    return 3


def _run_guarded(action, arguments: Sequence[str], output_format: str) -> int:
    """Run one bootstrap action behind the final diagnostic boundary."""
    try:
        return action(arguments)
    except KeyboardInterrupt:
        return 130
    except BaseException as err:
        # Import/runtime Exceptions and SystemExit are reportable bootstrap
        # failures. GeneratorExit and other control sentinels still propagate.
        if not isinstance(err, (Exception, SystemExit)):
            raise
        return _emit_bootstrap_error(
            "{}: {}".format(type(err).__name__, err), output_format
        )


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
    if command_arguments and command_arguments[0] == "--self-check":
        if any(item in ("-h", "--help") for item in command_arguments[1:]):
            sys.stdout.write(format_selfcheck_help())
            return 0
        if _WORKER_DISPATCH_ARGUMENT in command_arguments[1:]:
            return _emit_bootstrap_error(
                "--self-check and {} are mutually exclusive".format(
                    _WORKER_DISPATCH_ARGUMENT
                ),
                _requested_output_format(command_arguments[1:]),
            )
        return _run_guarded(
            run_selfcheck,
            command_arguments[1:],
            _requested_output_format(command_arguments[1:]),
        )
    if command_arguments and command_arguments[0] == _WORKER_DISPATCH_ARGUMENT:
        if any(item in ("-h", "--help") for item in command_arguments[1:]):
            sys.stdout.write(format_worker_help())
            return 0
        if "--self-check" in command_arguments[1:]:
            return _emit_bootstrap_error(
                "--self-check and {} are mutually exclusive".format(
                    _WORKER_DISPATCH_ARGUMENT
                ),
                _requested_output_format(command_arguments[1:]),
            )
        return _run_guarded(run_worker, command_arguments[1:], "human")

    from .entry import pyfcstmcli

    pyfcstmcli(args=list(command_arguments), prog_name="pyfcstm")
    return 0

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

import platform
import sys
from typing import Optional, Sequence

from .config import BUILD_COMMIT, BUILD_REVISION, BUILD_TIME_UTC
from .config.meta import __AUTHOR__, __AUTHOR_EMAIL__, __TITLE__, __VERSION__


_VERSION_ARGUMENTS = ("-v", "-V", "--version")


def is_version_request(arguments: Sequence[str]) -> bool:
    """
    Return whether arguments are exactly one root-level version request.

    :param arguments: Command-line arguments without the executable name.
    :type arguments: Sequence[str]
    :return: Whether the bootstrap should print version information itself.
    :rtype: bool
    """
    return len(arguments) == 1 and arguments[0] in _VERSION_ARGUMENTS


def format_version_info() -> str:
    """
    Format human-readable package and optional build identity information.

    :return: Multi-line version information without a trailing newline.
    :rtype: str
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
    """
    command_arguments = tuple(sys.argv[1:] if arguments is None else arguments)
    if is_version_request(command_arguments):
        sys.stdout.write(format_version_info() + "\n")
        return 0

    from .entry import pyfcstmcli

    pyfcstmcli(args=list(command_arguments), prog_name="pyfcstm")
    return 0

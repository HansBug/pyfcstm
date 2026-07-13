"""Best-effort environment collection for self-check diagnostics."""

import os
import platform
import sys
from typing import Any, Dict


def collect_environment(redact: bool = True) -> Dict[str, Any]:
    """
    Collect stable process and package environment fields.

    :param redact: Hide the current working directory and executable path when true.
    :type redact: bool
    :return: JSON-compatible environment mapping.
    :rtype: Dict[str, Any]

    Example::

        >>> "python" in collect_environment()
        True
    """
    from pyfcstm import __commit__, __revision__, __version__

    data = {
        "python": sys.version,
        "python_executable": sys.executable,
        "implementation": platform.python_implementation(),
        "platform": platform.platform(),
        "machine": platform.machine(),
        "architecture": platform.architecture()[0],
        "encoding": getattr(sys.stdout, "encoding", None),
        "version": __version__,
        "commit": __commit__,
        "revision": __revision__,
        "frozen": bool(getattr(sys, "frozen", False)),
    }
    if redact:
        data["python_executable"] = "<redacted>"
    else:
        data["cwd"] = os.getcwd()
    return data

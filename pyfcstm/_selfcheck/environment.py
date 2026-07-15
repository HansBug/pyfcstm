"""Field-isolated environment collection for self-check diagnostics."""

import locale
import os
import platform
import sys
import tempfile
from typing import Any, Callable, Dict


_FIELD_ERRORS = (
    OSError,
    RuntimeError,
    ValueError,
    TypeError,
    AttributeError,
    UnicodeError,
)


def _collect_field(
    data: Dict[str, Any], errors: Dict[str, str], name: str, callback: Callable[[], Any]
) -> None:
    """Collect one diagnostic field without discarding successful siblings."""
    try:
        data[name] = callback()
    except _FIELD_ERRORS as err:
        # Platform, locale, filesystem, and generated identity access can raise
        # these documented ordinary failures on damaged installations.
        data[name] = None
        errors[name] = "{}: {}".format(type(err).__name__, err)


def collect_environment(redact: bool = True) -> Dict[str, Any]:
    """Collect stable allowlisted runtime and package fields independently.

    :param redact: Hide absolute executable, cwd, and temp paths when true.
    :type redact: bool
    :return: JSON-compatible environment fields plus collection errors.
    :rtype: Dict[str, Any]

    Example::

        >>> data = collect_environment()
        >>> "python_version" in data and "collection_errors" in data
        True
    """
    import pyfcstm

    data: Dict[str, Any] = {}
    errors: Dict[str, str] = {}
    fields = (
        ("python", lambda: sys.version),
        ("python_version", platform.python_version),
        ("implementation", platform.python_implementation),
        ("platform", platform.platform),
        ("system", platform.system),
        ("release", platform.release),
        ("machine", platform.machine),
        ("architecture", lambda: platform.architecture()[0]),
        ("stdout_encoding", lambda: getattr(sys.stdout, "encoding", None)),
        ("filesystem_encoding", sys.getfilesystemencoding),
        ("preferred_encoding", lambda: locale.getpreferredencoding(False)),
        ("python_executable", lambda: sys.executable),
        ("cwd", os.getcwd),
        ("temp_directory", tempfile.gettempdir),
        ("version", lambda: getattr(pyfcstm, "__version__")),
        ("commit", lambda: getattr(pyfcstm, "__commit__")),
        ("revision", lambda: getattr(pyfcstm, "__revision__")),
    )
    for name, callback in fields:
        _collect_field(data, errors, name, callback)

    data["frozen"] = bool(getattr(sys, "frozen", False))
    if redact:
        for name in ("python_executable", "cwd", "temp_directory"):
            if data.get(name) is not None:
                data[name] = "<redacted>"
    data["collection_errors"] = errors
    return data

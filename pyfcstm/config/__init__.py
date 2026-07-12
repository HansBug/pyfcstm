"""
Build and package configuration values.

This namespace exposes static project metadata and optional build identity
values. A source checkout may not contain generated build metadata; in that
supported state the commit, revision, dirty, and build-time fields are
``None`` while the package remains importable. Generated ``build_info.py`` is
parsed as literal data and never imported or executed.

The package contains:

.. list-table::
   :header-rows: 1

   * - Value group
     - Purpose
   * - :data:`BUILD_COMMIT`, :data:`BUILD_REVISION`, :data:`BUILD_DIRTY`
     - Optional identity for a built wheel, sdist, or frozen artifact.
   * - :data:`BUILD_INFO_ERROR`
     - A diagnostic string when generated identity data is present but invalid.

Example::

    >>> import pyfcstm.config
    >>> pyfcstm.config.BUILD_COMMIT is None or isinstance(pyfcstm.config.BUILD_COMMIT, str)
    True
"""

import importlib.util
from pathlib import Path
from typing import Optional, Tuple

from ._build_identity import BuildIdentity
from ._build_identity import BuildInfoDataError
from ._build_identity import _load_build_identity_transport
from ._build_identity import load_build_identity_file


_BUILD_INFO_PATH = Path(__file__).with_name("build_info.py")


def _load_build_identity(path: Path) -> Tuple[BuildIdentity, Optional[str]]:
    """Load optional generated identity data without allowing it to execute."""
    try:
        return load_build_identity_file(path), None
    except FileNotFoundError:
        # A source checkout that has not run the build generator is supported.
        return BuildIdentity.unknown(), None
    except (OSError, UnicodeError, SyntaxError, ValueError, TypeError) as err:
        # Each class can arise while reading, decoding, parsing, or validating generated data.
        return BuildIdentity.unknown(), "{}: {}".format(type(err).__name__, err)


def _load_frozen_build_identity() -> Tuple[BuildIdentity, Optional[str]]:
    """Read bundled generated metadata without executing its module body."""
    module_name = __name__ + ".build_info"
    try:
        spec = importlib.util.find_spec(module_name)
    except ModuleNotFoundError as err:
        # Only the optional generated module is absent; dependency failures must surface.
        if err.name != module_name:
            raise
        return BuildIdentity.unknown(), None
    except (ImportError, AttributeError, ValueError) as err:
        # Frozen import metadata can be missing, incomplete, or malformed.
        return BuildIdentity.unknown(), "{}: {}".format(type(err).__name__, err)
    if spec is None:
        return BuildIdentity.unknown(), None
    if spec.loader is None or not hasattr(spec.loader, "get_code"):
        return BuildIdentity.unknown(), "ImportError: build info loader has no code"

    try:
        code = spec.loader.get_code(module_name)
    except (
        ImportError,
        OSError,
        EOFError,
        SyntaxError,
        ValueError,
        TypeError,
        RuntimeError,
    ) as err:
        # Bundled bytecode loaders use these errors for missing or damaged code data.
        return BuildIdentity.unknown(), "{}: {}".format(type(err).__name__, err)
    if code is None:
        return (
            BuildIdentity.unknown(),
            "ImportError: build info loader returned no code",
        )
    try:
        payload = code.co_consts[0]
    except (AttributeError, IndexError) as err:
        # A malformed loader result may not expose a module code constant table.
        return BuildIdentity.unknown(), "{}: {}".format(type(err).__name__, err)
    try:
        return _load_build_identity_transport(payload), None
    except BuildInfoDataError as err:
        # Static payload decoding and schema validation reject damaged metadata.
        return BuildIdentity.unknown(), "{}: {}".format(type(err).__name__, err)


def _collect_frozen_build_info():  # pragma: no cover
    """Expose the generated module to static frozen-application analysis."""
    from . import build_info

    return build_info


if _BUILD_INFO_PATH.is_file():
    _identity, BUILD_INFO_ERROR = _load_build_identity(_BUILD_INFO_PATH)
else:
    _identity, BUILD_INFO_ERROR = _load_frozen_build_identity()
BUILD_COMMIT = _identity.commit
BUILD_COMMIT_ALGORITHM = _identity.algorithm
BUILD_COMMIT_SHORT = _identity.commit_short
BUILD_DIRTY = _identity.dirty
BUILD_REVISION = _identity.revision
BUILD_REVISION_SHORT = _identity.revision_short
BUILD_REF = _identity.ref
BUILD_TIME_UTC = _identity.time_utc
BUILD_SOURCE = _identity.source

__all__ = [
    "BUILD_COMMIT",
    "BUILD_COMMIT_ALGORITHM",
    "BUILD_COMMIT_SHORT",
    "BUILD_DIRTY",
    "BUILD_REVISION",
    "BUILD_REVISION_SHORT",
    "BUILD_REF",
    "BUILD_TIME_UTC",
    "BUILD_SOURCE",
    "BUILD_INFO_ERROR",
]

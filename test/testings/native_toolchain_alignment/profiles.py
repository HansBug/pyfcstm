"""
Native toolchain profile registry for native toolchain pytest alignment.

Profiles describe how pytest should configure, build, and run generated C-family
artifacts under a concrete native toolchain. The initial registry deliberately starts with two
public Linux CMake profiles and keeps the registry small so later matrix work can
extend the profiles without changing the selection contract.

The module contains:

* :class:`ToolchainProfile` - Immutable profile configuration.
* :class:`ProfileSelectionError` - Raised for missing or unknown profile names.
* :class:`ToolchainMissingError` - Raised when a public profile lacks a tool.
* :func:`native_toolchain_enabled` - Check the pytest option / environment flag.
* :func:`resolve_selected_profile` - Resolve the selected profile by name.

Example::

    >>> profile = get_profile("linux-gcc-o2")
    >>> profile.optimization
    '-O2'
"""

import os
import shutil
from dataclasses import dataclass, field
from typing import Iterable, List, Optional, Sequence

RUN_ENV_VAR = "PYFCSTM_RUN_NATIVE_TOOLCHAIN"
PROFILE_ENV_VAR = "PYFCSTM_NATIVE_TOOLCHAIN_PROFILE"
ARTIFACT_DIR_ENV_VAR = "PYFCSTM_NATIVE_TOOLCHAIN_ARTIFACT_DIR"
_ENABLE_VALUES = {"1", "true", "yes", "on"}


class ProfileSelectionError(ValueError):
    """
    Raised when native toolchain profile selection is invalid.

    :param args: Error message arguments accepted by :class:`ValueError`.
    :type args: object

    Example::

        >>> str(ProfileSelectionError("missing profile"))
        'missing profile'
    """


class ToolchainMissingError(RuntimeError):
    """
    Raised when a public native toolchain profile cannot find required tools.

    :param args: Error message arguments accepted by :class:`RuntimeError`.
    :type args: object

    Example::

        >>> "gcc" in str(ToolchainMissingError("missing gcc"))
        True
    """


@dataclass(frozen=True)
class ToolchainProfile:
    """
    Native toolchain profile used by native toolchain pytest alignment.

    :param name: Unique profile name, such as ``"linux-gcc-o2"``.
    :type name: str
    :param build_mode: Build mode, currently ``"cmake-run"`` for native run profiles.
    :type build_mode: str
    :param cc: C compiler command in argv-list form.
    :type cc: typing.Sequence[str]
    :param cxx: C++ compiler command in argv-list form.
    :type cxx: typing.Sequence[str]
    :param c_flags: Extra C flags passed through CMake.
    :type c_flags: typing.Sequence[str]
    :param cxx_flags: Extra C++ flags passed through CMake.
    :type cxx_flags: typing.Sequence[str]
    :param link_flags: Extra link flags, defaults to an empty sequence.
    :type link_flags: typing.Sequence[str], optional
    :param required_binaries: Binaries that must be discoverable on ``PATH``.
    :type required_binaries: typing.Sequence[str]
    :param missing_tool_message: Diagnostic template used when tools are
        missing.
    :type missing_tool_message: str
    :param optimization: Optimization flag name.
    :type optimization: str
    :param public_required: Whether missing tools are hard failures.
    :type public_required: bool
    :param timeout_seconds: Per-command timeout.
    :type timeout_seconds: int

    Example::

        >>> profile = ToolchainProfile(
        ...     "demo", "cmake-run", ("cc",), ("c++",), ("-O2",), ("-O2",),
        ...     required_binaries=("cc", "c++"), optimization="-O2",
        ... )
        >>> profile.name
        'demo'
    """

    name: str
    build_mode: str
    cc: Sequence[str]
    cxx: Sequence[str]
    c_flags: Sequence[str]
    cxx_flags: Sequence[str]
    link_flags: Sequence[str] = field(default_factory=tuple)
    required_binaries: Sequence[str] = field(default_factory=tuple)
    missing_tool_message: str = "Install the missing native toolchain binaries."
    optimization: Optional[str] = None
    public_required: bool = True
    timeout_seconds: int = 240

    @property
    def compiler(self) -> Optional[str]:
        """
        Return the primary C compiler executable name.

        :return: First C compiler argv item, or ``None`` when absent.
        :rtype: str, optional

        Example::

            >>> get_profile("linux-gcc-o2").compiler
            'gcc'
        """
        return self.cc[0] if self.cc else None

    @property
    def primary_tool(self) -> str:
        """
        Return the primary tool used in reports.

        :return: Compiler name for native CMake-run profiles.
        :rtype: str

        Example::

            >>> get_profile("linux-clang-o2").primary_tool
            'clang'
        """
        return self.compiler or self.name


_PUBLIC_PROFILES = (
    ToolchainProfile(
        name="linux-gcc-o2",
        build_mode="cmake-run",
        cc=("gcc",),
        cxx=("g++",),
        c_flags=("-std=c99", "-O2", "-Wall", "-Wextra", "-pedantic"),
        cxx_flags=("-std=c++98", "-O2", "-Wall", "-Wextra", "-pedantic"),
        required_binaries=("cmake", "gcc", "g++"),
        missing_tool_message="Install cmake, gcc, and g++ before running linux-gcc-o2.",
        optimization="-O2",
    ),
    ToolchainProfile(
        name="linux-clang-o2",
        build_mode="cmake-run",
        cc=("clang",),
        cxx=("clang++",),
        c_flags=("-std=c99", "-O2", "-Wall", "-Wextra", "-pedantic"),
        cxx_flags=("-std=c++98", "-O2", "-Wall", "-Wextra", "-pedantic"),
        required_binaries=("cmake", "clang", "clang++"),
        missing_tool_message="Install cmake, clang, and clang++ before running linux-clang-o2.",
        optimization="-O2",
    ),
)
PROFILES = {profile.name: profile for profile in _PUBLIC_PROFILES}


def _env_enabled() -> bool:
    return os.environ.get(RUN_ENV_VAR, "").strip().lower() in _ENABLE_VALUES


def native_toolchain_enabled(config=None) -> bool:
    """
    Return whether native toolchain tests are explicitly enabled.

    :param config: Optional pytest config object that may expose
        ``--run-native-toolchain``.
    :type config: typing.Any, optional
    :return: ``True`` when the pytest option or environment flag enables native toolchain tests.
    :rtype: bool

    Example::

        >>> native_toolchain_enabled(None) in (True, False)
        True
    """
    option_enabled = False
    if config is not None:
        option_enabled = bool(config.getoption("--run-native-toolchain", default=False))
    return option_enabled or _env_enabled()


def iter_profiles() -> Sequence[ToolchainProfile]:
    """
    Return the public native toolchain profiles in registry order.

    :return: Tuple-like sequence of profiles.
    :rtype: typing.Sequence[ToolchainProfile]

    Example::

        >>> [profile.name for profile in iter_profiles()]
        ['linux-gcc-o2', 'linux-clang-o2']
    """
    return _PUBLIC_PROFILES


def get_profile(name: str) -> ToolchainProfile:
    """
    Return a profile by name.

    :param name: Profile name.
    :type name: str
    :return: Matching toolchain profile.
    :rtype: ToolchainProfile
    :raises ProfileSelectionError: If ``name`` is unknown.

    Example::

        >>> get_profile("linux-gcc-o2").build_mode
        'cmake-run'
    """
    try:
        return PROFILES[name]
    except KeyError as err:
        raise ProfileSelectionError(
            "unknown native toolchain profile %r; known profiles: %s"
            % (name, ", ".join(sorted(PROFILES)))
        ) from err


def selected_profile_name() -> Optional[str]:
    """
    Return the selected profile name from the environment.

    :return: Selected profile name, or ``None`` when unset.
    :rtype: str, optional

    Example::

        >>> selected_profile_name() is None or isinstance(selected_profile_name(), str)
        True
    """
    value = os.environ.get(PROFILE_ENV_VAR)
    if value is None or not value.strip():
        return None
    return value.strip()


def resolve_selected_profile(config=None) -> ToolchainProfile:
    """
    Resolve the explicitly selected native toolchain profile.

    :param config: Optional pytest config object. The object is accepted for API
        symmetry with :func:`native_toolchain_enabled`; profile selection itself
        comes from ``PYFCSTM_NATIVE_TOOLCHAIN_PROFILE``.
    :type config: typing.Any, optional
    :return: Selected profile.
    :rtype: ToolchainProfile
    :raises ProfileSelectionError: If native toolchain tests are disabled, the
        profile is missing, or the profile name is unknown.

    Example::

        >>> import os
        >>> old_run = os.environ.get(RUN_ENV_VAR)
        >>> old_profile = os.environ.get(PROFILE_ENV_VAR)
        >>> os.environ[RUN_ENV_VAR] = "1"
        >>> os.environ[PROFILE_ENV_VAR] = "linux-gcc-o2"
        >>> resolve_selected_profile().name
        'linux-gcc-o2'
        >>> _restore = os.environ.pop(RUN_ENV_VAR, None)
        >>> _restore = os.environ.pop(PROFILE_ENV_VAR, None)
        >>> if old_run is not None:
        ...     os.environ[RUN_ENV_VAR] = old_run
        >>> if old_profile is not None:
        ...     os.environ[PROFILE_ENV_VAR] = old_profile
    """
    if not native_toolchain_enabled(config):
        raise ProfileSelectionError("native toolchain tests require explicit opt-in")
    name = selected_profile_name()
    if name is None:
        raise ProfileSelectionError(
            "%s must be set when native toolchain tests are enabled" % PROFILE_ENV_VAR
        )
    return get_profile(name)


def missing_required_tools(profile: ToolchainProfile) -> List[str]:
    """
    Return missing executable names for ``profile``.

    :param profile: Toolchain profile to inspect.
    :type profile: ToolchainProfile
    :return: Missing executable names in profile order.
    :rtype: list

    Example::

        >>> profile = ToolchainProfile(
        ...     "demo", "cmake-run", ("definitely-not-pyfcstm-cc",), (), (),
        ...     (), required_binaries=("definitely-not-pyfcstm-cc",),
        ... )
        >>> missing = missing_required_tools(profile)
        >>> "definitely-not-pyfcstm-cc" in missing
        True
    """
    missing = []
    for binary in profile.required_binaries:
        if shutil.which(binary) is None:
            missing.append(binary)
    return missing


def ensure_required_tools(profile: ToolchainProfile) -> None:
    """
    Fail if a public native toolchain profile lacks required tools.

    :param profile: Toolchain profile to validate.
    :type profile: ToolchainProfile
    :return: ``None``.
    :rtype: None
    :raises ToolchainMissingError: If required tools are not available.

    Example::

        >>> profile = ToolchainProfile(
        ...     "demo", "cmake-run", (), (), (), (),
        ...     required_binaries=("definitely-not-pyfcstm-cc",),
        ... )
        >>> ensure_required_tools(profile)
        Traceback (most recent call last):
        ...
        test.testings.native_toolchain_alignment.profiles.ToolchainMissingError: ...
    """
    missing = missing_required_tools(profile)
    if missing:
        raise ToolchainMissingError(
            "%s; missing binaries: %s"
            % (profile.missing_tool_message, ", ".join(missing))
        )


def shell_join(argv: Iterable[str]) -> str:
    """
    Join a short argv list for human-readable diagnostics.

    :param argv: Command arguments.
    :type argv: typing.Iterable[str]
    :return: Space-separated diagnostic string.
    :rtype: str

    Example::

        >>> shell_join(["gcc", "--version"])
        'gcc --version'
    """
    return " ".join(argv)

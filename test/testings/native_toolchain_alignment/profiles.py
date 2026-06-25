"""
Native toolchain profile registry for native toolchain pytest alignment.

Profiles describe how pytest should configure, build, run, or analyze generated
C-family artifacts under concrete host, cross, sanitizer, compile-only, and
static-analysis toolchains. The registry is test-local and intentionally keeps
all toolchain knowledge outside production APIs: tests select exactly one
profile through the environment, then the runner applies that profile to every
shared semantic fixture.

The module contains:

* :class:`ToolchainProfile` - Immutable profile configuration.
* :class:`ProfileSelectionError` - Raised for missing or unknown profile names.
* :class:`ToolchainMissingError` - Raised when a selected profile lacks tools.
* :func:`iter_profiles` - Iterate public and manual profile definitions.
* :func:`resolve_selected_profile` - Resolve the selected profile by name.

.. list-table:: Profile families
   :header-rows: 1

   * - Family
     - Representative profile
     - Runner behavior
   * - Hosted CMake run
     - ``linux-gcc-o2``
     - Configure, build, execute, and compare public observations.
   * - Cross run
     - ``linux-aarch64-gcc-o2``
     - Cross-compile and execute through a configured emulator prefix.
   * - Compile only
     - ``arm-none-eabi-gcc-o2``
     - Compile generated runtime, harness, and C++ header probe without linking.
   * - Static analysis
     - ``linux-cppcheck``
     - Scan generated runtime plus harness and store a report-only artifact.
   * - Manual self-hosted
     - ``manual-armclang-compile``
     - Provide non-public entry points for licensed or self-hosted toolchains.

Example::

    >>> profile = get_profile("linux-gcc-o2")
    >>> profile.optimization
    '-O2'
    >>> get_profile("linux-cppcheck").build_mode
    'analyze-only'
"""

import os
import shutil
from dataclasses import dataclass, field
from typing import Iterable, List, Mapping, Optional, Sequence

RUN_ENV_VAR = "PYFCSTM_RUN_NATIVE_TOOLCHAIN"
PROFILE_ENV_VAR = "PYFCSTM_NATIVE_TOOLCHAIN_PROFILE"
ARTIFACT_DIR_ENV_VAR = "PYFCSTM_NATIVE_TOOLCHAIN_ARTIFACT_DIR"
_ENABLE_VALUES = {"1", "true", "yes", "on"}

BUILD_MODE_CMAKE_RUN = "cmake-run"
BUILD_MODE_CROSS_QEMU_RUN = "cross-qemu-run"
BUILD_MODE_COMPILE_ONLY = "compile-only"
BUILD_MODE_ANALYZE_ONLY = "analyze-only"
BUILD_MODE_SELF_HOSTED_COMPILE = "self-hosted-compile"


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
    Raised when a native toolchain profile cannot find required tools.

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

    A profile is a concrete toolchain configuration rather than a production
    API. Runnable profiles compile and execute the generated harness;
    compile-only profiles stop after non-empty object files are produced;
    analyze-only profiles scan the generated runtime and harness while writing a
    report artifact.

    :param name: Unique profile name, such as ``"linux-gcc-o2"``.
    :type name: str
    :param build_mode: Build mode, such as ``"cmake-run"`` or
        ``"compile-only"``.
    :type build_mode: str
    :param cc: C compiler command in argv-list form.
    :type cc: typing.Sequence[str]
    :param cxx: C++ compiler command in argv-list form.
    :type cxx: typing.Sequence[str]
    :param c_flags: Extra C flags passed to the C compiler.
    :type c_flags: typing.Sequence[str]
    :param cxx_flags: Extra C++ flags passed to the C++ compiler.
    :type cxx_flags: typing.Sequence[str]
    :param link_flags: Extra link flags, defaults to an empty sequence.
    :type link_flags: typing.Sequence[str], optional
    :param required_binaries: Binaries that must be discoverable on ``PATH``.
    :type required_binaries: typing.Sequence[str]
    :param missing_tool_message: Diagnostic template used when tools are
        missing.
    :type missing_tool_message: str
    :param optimization: Optimization flag name.
    :type optimization: str, optional
    :param public_required: Whether missing tools are hard failures. Public
        profiles use ``True``; licensed self-hosted placeholders use ``False``.
    :type public_required: bool
    :param timeout_seconds: Per-command timeout.
    :type timeout_seconds: int
    :param cmake_generator: Optional CMake generator name.
    :type cmake_generator: str, optional
    :param cmake_args: Additional CMake configure arguments.
    :type cmake_args: typing.Sequence[str], optional
    :param run_prefix: Command prefix used to execute a cross-built binary.
    :type run_prefix: typing.Sequence[str], optional
    :param run_environment: Environment variables added while running a binary.
    :type run_environment: typing.Mapping[str, str], optional
    :param analysis_tool: Static-analysis command in argv-list form.
    :type analysis_tool: typing.Sequence[str], optional
    :param analysis_args: Additional static-analysis arguments.
    :type analysis_args: typing.Sequence[str], optional
    :param analysis_ruleset: Human-readable static-analysis ruleset name.
    :type analysis_ruleset: str, optional
    :param report_only: Whether analyzer findings are recorded without turning
        ordinary diagnostics into failures.
    :type report_only: bool

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
    cmake_generator: Optional[str] = None
    cmake_args: Sequence[str] = field(default_factory=tuple)
    run_prefix: Sequence[str] = field(default_factory=tuple)
    run_environment: Mapping[str, str] = field(default_factory=dict)
    analysis_tool: Sequence[str] = field(default_factory=tuple)
    analysis_args: Sequence[str] = field(default_factory=tuple)
    analysis_ruleset: Optional[str] = None
    report_only: bool = False

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

        :return: Analyzer command, compiler command, or profile name.
        :rtype: str

        Example::

            >>> get_profile("linux-clang-o2").primary_tool
            'clang'
            >>> get_profile("linux-cppcheck").primary_tool
            'cppcheck'
        """
        if self.analysis_tool:
            return self.analysis_tool[0]
        return self.compiler or self.name


def _host_profile(
    name: str,
    cc: str,
    cxx: str,
    optimization: str,
    extra_c_flags: Sequence[str] = (),
    extra_cxx_flags: Sequence[str] = (),
    link_flags: Sequence[str] = (),
    required_binaries: Optional[Sequence[str]] = None,
    cmake_generator: Optional[str] = None,
    cmake_args: Sequence[str] = (),
    run_prefix: Sequence[str] = (),
    run_environment: Optional[Mapping[str, str]] = None,
    timeout_seconds: int = 240,
) -> ToolchainProfile:
    required = tuple(required_binaries or ("cmake", cc, cxx))
    c_flags = ("-std=c99", optimization, "-Wall", "-Wextra", "-pedantic")
    cxx_flags = (
        "-std=c++98",
        "-fno-exceptions",
        "-fno-rtti",
        optimization,
        "-Wall",
        "-Wextra",
        "-pedantic",
    )
    return ToolchainProfile(
        name=name,
        build_mode=BUILD_MODE_CMAKE_RUN
        if not run_prefix
        else BUILD_MODE_CROSS_QEMU_RUN,
        cc=(cc,),
        cxx=(cxx,),
        c_flags=c_flags + tuple(extra_c_flags),
        cxx_flags=cxx_flags + tuple(extra_cxx_flags),
        link_flags=tuple(link_flags),
        required_binaries=required,
        missing_tool_message="Install %s before running %s."
        % (", ".join(required), name),
        optimization=optimization,
        timeout_seconds=timeout_seconds,
        cmake_generator=cmake_generator,
        cmake_args=tuple(cmake_args),
        run_prefix=tuple(run_prefix),
        run_environment=dict(run_environment or {}),
    )


def _msvc_profile(name: str, cc: str, cxx: str, optimization: str) -> ToolchainProfile:
    return ToolchainProfile(
        name=name,
        build_mode=BUILD_MODE_CMAKE_RUN,
        cc=(cc,),
        cxx=(cxx,),
        c_flags=(optimization, "/W4"),
        cxx_flags=(optimization, "/W4", "/TP", "/permissive-", "/GR-"),
        required_binaries=("cmake", "ninja", cc, cxx),
        missing_tool_message=(
            "Install CMake, Ninja, and the Visual Studio C/C++ tools before running %s."
            % name
        ),
        optimization=optimization,
        timeout_seconds=300,
        cmake_generator="Ninja",
        cmake_args=("-DPYFCSTM_NATIVE_C_STANDARD=11",),
    )


def _compile_only_profile(
    name: str, cc: str, cxx: str, optimization: str, required_binaries: Sequence[str]
) -> ToolchainProfile:
    return ToolchainProfile(
        name=name,
        build_mode=BUILD_MODE_COMPILE_ONLY,
        cc=(cc,),
        cxx=(cxx,),
        c_flags=("-std=c99", optimization, "-Wall", "-Wextra", "-pedantic"),
        cxx_flags=(
            "-std=c++98",
            "-fno-exceptions",
            "-fno-rtti",
            optimization,
            "-Wall",
            "-Wextra",
            "-pedantic",
        ),
        required_binaries=tuple(required_binaries),
        missing_tool_message="Install %s before running %s."
        % (
            ", ".join(required_binaries),
            name,
        ),
        optimization=optimization,
        timeout_seconds=240,
    )


def _analysis_profile(
    name: str,
    tool: str,
    args: Sequence[str],
    ruleset: str,
    required_binaries: Sequence[str],
) -> ToolchainProfile:
    return ToolchainProfile(
        name=name,
        build_mode=BUILD_MODE_ANALYZE_ONLY,
        cc=(),
        cxx=(),
        c_flags=("-std=c99",),
        cxx_flags=("-std=c++98",),
        required_binaries=tuple(required_binaries),
        missing_tool_message="Install %s before running %s."
        % (
            ", ".join(required_binaries),
            name,
        ),
        timeout_seconds=240,
        analysis_tool=(tool,),
        analysis_args=tuple(args),
        analysis_ruleset=ruleset,
        report_only=True,
    )


def _manual_compile_profile(name: str, cc: str, cxx: str) -> ToolchainProfile:
    return ToolchainProfile(
        name=name,
        build_mode=BUILD_MODE_SELF_HOSTED_COMPILE,
        cc=(cc,),
        cxx=(cxx,),
        c_flags=("-std=c99", "-O2"),
        cxx_flags=("-std=c++98", "-fno-exceptions", "-fno-rtti", "-O2"),
        required_binaries=(cc, cxx),
        missing_tool_message=(
            "Run this manual native toolchain profile only on a self-hosted runner "
            "where the licensed compiler is installed."
        ),
        optimization="-O2",
        public_required=False,
        timeout_seconds=300,
    )


_GCC_PROFILES = tuple(
    _host_profile("linux-gcc-%s" % suffix, "gcc", "g++", flag)
    for suffix, flag in (("o0", "-O0"), ("o2", "-O2"), ("o3", "-O3"), ("os", "-Os"))
)
_CLANG_PROFILES = tuple(
    _host_profile("linux-clang-%s" % suffix, "clang", "clang++", flag)
    for suffix, flag in (("o0", "-O0"), ("o2", "-O2"), ("o3", "-O3"), ("os", "-Os"))
)
_M32_PROFILES = tuple(
    _host_profile(
        "linux-gcc-m32-%s" % suffix,
        "gcc",
        "g++",
        flag,
        extra_c_flags=("-m32",),
        extra_cxx_flags=("-m32",),
        link_flags=("-m32",),
        required_binaries=("cmake", "gcc", "g++"),
    )
    for suffix, flag in (("o2", "-O2"), ("os", "-Os"))
)
_AARCH64_PROFILES = tuple(
    _host_profile(
        "linux-aarch64-gcc-%s" % suffix,
        "aarch64-linux-gnu-gcc",
        "aarch64-linux-gnu-g++",
        flag,
        required_binaries=(
            "cmake",
            "aarch64-linux-gnu-gcc",
            "aarch64-linux-gnu-g++",
            "qemu-aarch64",
        ),
        cmake_args=("-DCMAKE_SYSTEM_NAME=Linux", "-DCMAKE_SYSTEM_PROCESSOR=aarch64"),
        run_prefix=("qemu-aarch64", "-L", "/usr/aarch64-linux-gnu"),
        timeout_seconds=360,
    )
    for suffix, flag in (("o2", "-O2"), ("os", "-Os"))
)
_ARM_COMPILE_PROFILES = tuple(
    _compile_only_profile(
        "arm-none-eabi-gcc-%s" % suffix,
        "arm-none-eabi-gcc",
        "arm-none-eabi-g++",
        flag,
        ("arm-none-eabi-gcc", "arm-none-eabi-g++"),
    )
    for suffix, flag in (("o2", "-O2"), ("os", "-Os"))
)
_MACOS_PROFILES = tuple(
    _host_profile("macos-appleclang-%s" % suffix, "clang", "clang++", flag)
    for suffix, flag in (("o0", "-O0"), ("o2", "-O2"), ("o3", "-O3"), ("os", "-Os"))
)
_MINGW_PROFILES = tuple(
    _host_profile(
        "windows-mingw-%s" % suffix,
        "gcc",
        "g++",
        flag,
        required_binaries=("cmake", "ninja", "gcc", "g++"),
        cmake_generator="Ninja",
        timeout_seconds=300,
    )
    for suffix, flag in (("o0", "-O0"), ("o2", "-O2"), ("o3", "-O3"))
)
_MSVC_PROFILES = (
    _msvc_profile("windows-msvc-od", "cl", "cl", "/Od"),
    _msvc_profile("windows-msvc-o2", "cl", "cl", "/O2"),
)
_CLANGCL_PROFILES = (
    _msvc_profile("windows-clangcl-od", "clang-cl", "clang-cl", "/Od"),
    _msvc_profile("windows-clangcl-o2", "clang-cl", "clang-cl", "/O2"),
)
_SANITIZER_PROFILES = (
    _host_profile(
        "linux-clang-asan-ubsan",
        "clang",
        "clang++",
        "-O1",
        extra_c_flags=("-fsanitize=address,undefined", "-fno-omit-frame-pointer"),
        extra_cxx_flags=("-fsanitize=address,undefined", "-fno-omit-frame-pointer"),
        link_flags=("-fsanitize=address,undefined",),
        required_binaries=("cmake", "clang", "clang++"),
        run_environment=(
            ("ASAN_OPTIONS", "detect_leaks=1:strict_string_checks=1"),
            ("UBSAN_OPTIONS", "print_stacktrace=1"),
        ),
        timeout_seconds=360,
    ),
)
_ANALYSIS_PROFILES = (
    _analysis_profile(
        "linux-cppcheck",
        "cppcheck",
        (
            "--enable=warning,style,performance,portability",
            "--inline-suppr",
        ),
        "cppcheck warning/style/performance/portability report-only",
        ("cppcheck",),
    ),
    _analysis_profile(
        "linux-clang-tidy",
        "clang-tidy",
        (
            "--checks=bugprone-*,clang-analyzer-*,performance-*",
            "-header-filter=.*",
            "--",
            "-Iharness",
        ),
        "clang-tidy bugprone/clang-analyzer/performance report-only",
        ("clang-tidy",),
    ),
)
_MANUAL_PROFILES = (
    _manual_compile_profile("manual-armclang-compile", "armclang", "armclang"),
    _manual_compile_profile("manual-iar-compile", "iccarm", "iccarm"),
    _manual_compile_profile("manual-ti-clang-compile", "tiarmclang", "tiarmclang"),
    _manual_compile_profile("manual-greenhills-compile", "ccarm", "cxarm"),
    _manual_compile_profile("manual-tasking-compile", "ctc", "cptc"),
    _manual_compile_profile("manual-qnx-qcc-compile", "qcc", "q++"),
)

_PUBLIC_PROFILES = (
    _GCC_PROFILES
    + _CLANG_PROFILES
    + _M32_PROFILES
    + _AARCH64_PROFILES
    + _ARM_COMPILE_PROFILES
    + _MACOS_PROFILES
    + _MINGW_PROFILES
    + _MSVC_PROFILES
    + _CLANGCL_PROFILES
    + _SANITIZER_PROFILES
    + _ANALYSIS_PROFILES
)
_ALL_PROFILES = _PUBLIC_PROFILES + _MANUAL_PROFILES
PROFILES = {profile.name: profile for profile in _ALL_PROFILES}


def _env_enabled() -> bool:
    return os.environ.get(RUN_ENV_VAR, "").strip().lower() in _ENABLE_VALUES


def native_toolchain_enabled(config=None) -> bool:
    """
    Return whether native toolchain tests are explicitly enabled.

    :param config: Optional pytest config object that may expose
        ``--run-native-toolchain``.
    :type config: typing.Any, optional
    :return: ``True`` when the pytest option or environment flag enables native
        toolchain tests.
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
    Return public native toolchain profiles in registry order.

    :return: Tuple-like sequence of public profiles.
    :rtype: typing.Sequence[ToolchainProfile]

    Example::

        >>> iter_profiles()[0].name
        'linux-gcc-o0'
        >>> get_profile("linux-aarch64-gcc-o2").run_prefix[:1]
        ('qemu-aarch64',)
        >>> get_profile("linux-gcc-o2") in iter_profiles()
        True
    """
    return _PUBLIC_PROFILES


def iter_manual_profiles() -> Sequence[ToolchainProfile]:
    """
    Return non-public self-hosted native toolchain profiles.

    :return: Tuple-like sequence of manual profiles.
    :rtype: typing.Sequence[ToolchainProfile]

    Example::

        >>> iter_manual_profiles()[0].public_required
        False
    """
    return _MANUAL_PROFILES


def iter_all_profiles() -> Sequence[ToolchainProfile]:
    """
    Return public and manual profiles in registry order.

    :return: Tuple-like sequence of every registered profile.
    :rtype: typing.Sequence[ToolchainProfile]

    Example::

        >>> get_profile("manual-armclang-compile") in iter_all_profiles()
        True
    """
    return _ALL_PROFILES


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
    Fail if a native toolchain profile lacks required tools.

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
        >>> try:
        ...     ensure_required_tools(profile)
        ... except ToolchainMissingError as err:
        ...     "definitely-not-pyfcstm-cc" in str(err)
        True
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

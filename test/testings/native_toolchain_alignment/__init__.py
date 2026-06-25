"""
Native toolchain alignment helper map.

The package contains pytest-only helpers for native toolchain alignment. It
keeps the heavy C/C++ compiler matrix outside production code while exposing a
small module map for tests and reviewers.

.. list-table:: Module map
   :header-rows: 1

   * - Module
     - Responsibility
   * - ``profiles``
     - Explicit opt-in switch handling, public profile registry, manual
       self-hosted profile registry, and build-mode constants.
   * - ``harness``
     - Case-specific C/C++ harness and CMake project rendering.
   * - ``runner``
     - Configure/build/run, compile-only, analyze-only, and observation checks.
   * - ``report``
     - ``commands.json``, ``result.json``, and ``observations.jsonl`` schema
       helpers.

.. list-table:: Runner families
   :header-rows: 1

   * - Family
     - Profile examples
   * - Runnable hosted / emulated
     - ``linux-gcc-o2``, ``linux-aarch64-gcc-o2``, ``windows-msvc-o2``.
   * - Compile only
     - ``arm-none-eabi-gcc-o2`` and manual licensed-toolchain entries.
   * - Analyze only
     - ``linux-cppcheck`` and ``linux-clang-tidy``.

Example::

    >>> from test.testings.native_toolchain_alignment import get_profile
    >>> get_profile("linux-gcc-o2").name
    'linux-gcc-o2'
"""

from .profiles import (
    ARTIFACT_DIR_ENV_VAR,
    BUILD_MODE_ANALYZE_ONLY,
    BUILD_MODE_CMAKE_RUN,
    BUILD_MODE_COMPILE_ONLY,
    BUILD_MODE_CROSS_QEMU_RUN,
    BUILD_MODE_SELF_HOSTED_COMPILE,
    PROFILE_ENV_VAR,
    RUN_ENV_VAR,
    ProfileSelectionError,
    ToolchainMissingError,
    ToolchainProfile,
    get_profile,
    iter_all_profiles,
    iter_manual_profiles,
    iter_profiles,
    native_toolchain_enabled,
    resolve_selected_profile,
)
from .runner import NativeToolchainExecutionError, run_native_toolchain_case

__all__ = [
    "ARTIFACT_DIR_ENV_VAR",
    "BUILD_MODE_ANALYZE_ONLY",
    "BUILD_MODE_CMAKE_RUN",
    "BUILD_MODE_COMPILE_ONLY",
    "BUILD_MODE_CROSS_QEMU_RUN",
    "BUILD_MODE_SELF_HOSTED_COMPILE",
    "PROFILE_ENV_VAR",
    "RUN_ENV_VAR",
    "NativeToolchainExecutionError",
    "ProfileSelectionError",
    "ToolchainMissingError",
    "ToolchainProfile",
    "get_profile",
    "iter_all_profiles",
    "iter_manual_profiles",
    "iter_profiles",
    "native_toolchain_enabled",
    "resolve_selected_profile",
    "run_native_toolchain_case",
]

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
     - Explicit opt-in switch handling and native profile registry.
   * - ``harness``
     - Case-specific C harness and CMake project rendering.
   * - ``runner``
     - Configure/build/run orchestration and observation checks.
   * - ``report``
     - ``commands.json``, ``result.json``, and ``observations.jsonl`` schema
       helpers.

Example::

    >>> from test.testings.native_toolchain_alignment import get_profile
    >>> get_profile("linux-gcc-o2").name
    'linux-gcc-o2'
"""

from .profiles import (
    ARTIFACT_DIR_ENV_VAR,
    PROFILE_ENV_VAR,
    RUN_ENV_VAR,
    ProfileSelectionError,
    ToolchainMissingError,
    ToolchainProfile,
    get_profile,
    iter_profiles,
    native_toolchain_enabled,
    resolve_selected_profile,
)
from .runner import NativeToolchainExecutionError, run_native_toolchain_case

__all__ = [
    "ARTIFACT_DIR_ENV_VAR",
    "PROFILE_ENV_VAR",
    "RUN_ENV_VAR",
    "NativeToolchainExecutionError",
    "ProfileSelectionError",
    "ToolchainMissingError",
    "ToolchainProfile",
    "get_profile",
    "iter_profiles",
    "native_toolchain_enabled",
    "resolve_selected_profile",
    "run_native_toolchain_case",
]

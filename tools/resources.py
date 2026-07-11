"""
Collect the small PyInstaller data-resource allowlist for standalone executables.

The production collector intentionally keeps only runtime data that cannot be
found by PyInstaller's normal Python-module analysis: pyfcstm diagnostic data,
packaged template ZIP assets, and the Z3 native library. Development resources
such as LLM prompts, ANTLR source metadata, diagnostic maintenance notes, and Z3
headers remain in the repository but are not bundled into the executable.

Example::

    $ python tools/resources.py --check
    $ python tools/resources.py
"""

import argparse
import importlib
import os
import os.path
import platform
from typing import Iterator, Mapping, Optional, Sequence, Tuple

try:
    from importlib import metadata as importlib_metadata
except ImportError:
    # Python 3.7 does not provide importlib.metadata, so the supported legacy
    # interpreter uses the importlib-metadata backport from requirements.txt.
    import importlib_metadata


ResourceMapping = Tuple[str, str]

PYFCSTM_DATA_ALLOWLIST = (
    "diagnostics/codes.yaml",
    "diagnostics/schema.json",
    "template/index.json",
    "template/c.zip",
    "template/c_poll.zip",
    "template/cpp.zip",
    "template/cpp_poll.zip",
    "template/python.zip",
)

RESOURCE_AUDIT_CLASSIFICATION = {
    "keep": (
        "pyfcstm/diagnostics/codes.yaml",
        "pyfcstm/diagnostics/schema.json",
        "pyfcstm/template/index.json",
        "pyfcstm/template/c.zip",
        "pyfcstm/template/c_poll.zip",
        "pyfcstm/template/cpp.zip",
        "pyfcstm/template/cpp_poll.zip",
        "pyfcstm/template/python.zip",
        "icons/pyfcstm.png",
        "z3/lib/libz3 dynamic library for solver-backed diagnostics",
    ),
    "drop": (
        "pyfcstm/llm/**",
        "pyfcstm/diagnostics/inspect_llm_report_schema.json",
        "pyfcstm/diagnostics/README*",
        "pyfcstm/dsl/grammar/*.g4",
        "pyfcstm/dsl/grammar/*.interp",
        "pyfcstm/dsl/grammar/*.tokens",
        "z3/include/**",
        "z3 header files",
    ),
}

_Z3_LIBRARY_NAMES = ("libz3.dylib", "libz3.dll", "z3.dll")
_Z3_LIBRARY_PREFIXES = ("libz3.so",)


def _project_version() -> str:
    """Return the pyfcstm package version without importing the package."""
    meta = {}
    meta_path = os.path.abspath(
        os.path.join(os.path.dirname(__file__), "..", "pyfcstm", "config", "meta.py")
    )
    with open(meta_path, "r", encoding="utf-8") as file:
        exec(file.read(), meta)
    return str(meta["__VERSION__"])


def _normalized_platform_name() -> str:
    sys_platform = platform.system().lower()
    if sys_platform:
        if sys_platform.startswith("darwin"):
            return "macos"
        if sys_platform.startswith("windows"):
            return "windows"
        if sys_platform.startswith("linux"):
            return "linux"
        return sys_platform.replace(" ", "_")
    return "unknown"


def _normalized_machine_name() -> str:
    machine = platform.machine().lower().replace(" ", "_").replace("-", "_")
    aliases = {
        "amd64": "x86_64",
        "x64": "x86_64",
        "aarch64": "arm64",
    }
    return aliases.get(machine, machine or "unknown")


def get_executable_name() -> str:
    """
    Return the canonical platform-independent PyInstaller executable stem.

    PyInstaller appends ``.exe`` on Windows, so the shared stem deliberately
    excludes the platform suffix. The root Makefile adds that suffix only when
    resolving the final artifact path.

    :return: Versioned executable stem with normalized platform and machine.
    :rtype: str

    Example::

        >>> get_executable_name().startswith('pyfcstm-')
        True
    """
    return "pyfcstm-{0}-{1}-{2}".format(
        _project_version(), _normalized_platform_name(), _normalized_machine_name()
    )


def get_executable_path(dist_dir: str = "dist") -> str:
    """
    Return the canonical standalone CLI path under ``dist_dir``.

    :param dist_dir: Directory containing PyInstaller output, defaults to
        ``"dist"``.
    :type dist_dir: str, optional
    :return: Platform-specific executable path, including ``.exe`` on Windows.
    :rtype: str

    Example::

        >>> os.path.basename(get_executable_path()).startswith('pyfcstm-')
        True
    """
    suffix = ".exe" if os.name == "nt" else ""
    return os.path.join(dist_dir, get_executable_name() + suffix).replace(os.sep, "/")


class ResourceCollectionError(RuntimeError):
    """
    Report an invalid resource collection input or self-check fixture.

    :param message: Human-readable resource collection failure.
    :type message: str

    Example::

        >>> ResourceCollectionError('missing').args[0]
        'missing'
    """


def list_installed_packages() -> Iterator[str]:
    """
    Yield installed distribution names visible to the current interpreter.

    This helper is retained for local inspection, but production PyInstaller
    resources are not collected by scanning every installed package.

    :return: Installed package distribution names.
    :rtype: typing.Iterator[str]

    Example::

        >>> isinstance(next(list_installed_packages()), str)
        True
    """
    installed_packages = importlib_metadata.distributions()
    for dist in installed_packages:
        yield dist.metadata["Name"]


def _imported_package_root(package: str) -> str:
    module = importlib.import_module(package)
    package_file = getattr(module, "__file__", None)
    if not package_file:
        raise ResourceCollectionError(
            "package has no filesystem location: {0}".format(package)
        )
    if os.path.splitext(os.path.basename(package_file))[0] != "__init__":
        raise ResourceCollectionError(
            "package is not a directory package: {0}".format(package)
        )
    return os.path.dirname(os.path.abspath(package_file))


def _normalize_package_root(package_root: Optional[str], package: str) -> str:
    if package_root is None:
        return _imported_package_root(package)
    return os.path.abspath(os.path.normpath(package_root))


def _mapping_for_package_file(package_root: str, file_path: str) -> ResourceMapping:
    package_name = os.path.basename(os.path.abspath(package_root))
    package_parent = os.path.dirname(os.path.abspath(package_root))
    destination = os.path.dirname(
        os.path.relpath(os.path.abspath(file_path), package_parent)
    )
    if not destination.startswith(package_name):
        raise ResourceCollectionError(
            "resource escapes package root: {0}".format(file_path)
        )
    return os.path.abspath(file_path), destination


def list_resources(package_root: Optional[str] = None) -> Iterator[str]:
    """
    Yield the exact pyfcstm runtime data allowlist for PyInstaller.

    :param package_root: Optional ``pyfcstm`` package directory. Tests and
        repo-only self-checks may inject a temporary package root; production
        calls import :mod:`pyfcstm` to locate the installed package.
    :type package_root: str, optional
    :return: Absolute paths for allowed pyfcstm data files.
    :rtype: typing.Iterator[str]
    :raises ResourceCollectionError: If an allowlisted file is missing.

    Example::

        >>> files = list(list_resources())
        >>> any(path.endswith('pyfcstm/template/index.json') for path in files)
        True
    """
    root_dir = _normalize_package_root(package_root, "pyfcstm")
    for relative_path in PYFCSTM_DATA_ALLOWLIST:
        resource_path = os.path.abspath(
            os.path.join(root_dir, *relative_path.split("/"))
        )
        if not os.path.isfile(resource_path):
            raise ResourceCollectionError(
                "required pyfcstm resource is missing: {0}".format(resource_path)
            )
        yield resource_path


def get_resources_from_mine(
    package_root: Optional[str] = None,
) -> Iterator[ResourceMapping]:
    """
    Yield PyInstaller ``--add-data`` mappings for pyfcstm runtime data.

    :param package_root: Optional injected ``pyfcstm`` package directory.
    :type package_root: str, optional
    :return: ``(source, destination_directory)`` resource mappings.
    :rtype: typing.Iterator[typing.Tuple[str, str]]

    Example::

        >>> mappings = list(get_resources_from_mine())
        >>> any(dst == 'pyfcstm/template' for _, dst in mappings)
        True
    """
    root_dir = _normalize_package_root(package_root, "pyfcstm")
    for resource_file in list_resources(root_dir):
        yield _mapping_for_package_file(root_dir, resource_file)


def _is_z3_dynamic_library(path: str) -> bool:
    file_name = os.path.basename(path).lower()
    return file_name in _Z3_LIBRARY_NAMES or any(
        file_name.startswith(prefix) for prefix in _Z3_LIBRARY_PREFIXES
    )


def get_resources_from_package(
    package: str, package_root: Optional[str] = None
) -> Iterator[ResourceMapping]:
    """
    Yield precise PyInstaller data mappings for a supported dependency package.

    Only ``z3`` is supported because the standalone executable needs Z3's
    native library but must not bundle headers or development metadata.

    :param package: Supported package name, currently ``"z3"``.
    :type package: str
    :param package_root: Optional injected package root for self-checks.
    :type package_root: str, optional
    :return: ``(source, destination_directory)`` resource mappings.
    :rtype: typing.Iterator[typing.Tuple[str, str]]
    :raises ResourceCollectionError: If ``package`` is unsupported or no Z3
        dynamic library is found.

    Example::

        >>> mappings = list(get_resources_from_package('z3'))
        >>> any('libz3' in os.path.basename(src) for src, _ in mappings)
        True
    """
    if package != "z3":
        raise ResourceCollectionError(
            "unsupported dependency resource package: {0}".format(package)
        )

    try:
        root_dir = _normalize_package_root(package_root, package)
    except ImportError as error:
        # importlib.import_module(package) raises ImportError when z3-solver is
        # not installed in the build interpreter; a missing solver dependency is
        # a packaging error for the standalone executable.
        raise ResourceCollectionError(
            "required dependency package is missing: {0}".format(package)
        ) from error

    found = False
    package_parent = os.path.dirname(root_dir)
    for root, _, files in os.walk(root_dir):
        for file_name in files:
            src_file = os.path.abspath(os.path.join(root, file_name))
            if not _is_z3_dynamic_library(src_file):
                continue
            found = True
            yield src_file, os.path.dirname(os.path.relpath(src_file, package_parent))
    if not found:
        raise ResourceCollectionError(
            "no Z3 dynamic library found under: {0}".format(root_dir)
        )


def get_resource_files(
    pyfcstm_package_root: Optional[str] = None,
    z3_package_root: Optional[str] = None,
) -> Iterator[ResourceMapping]:
    """
    Yield all PyInstaller data resources for the standalone CLI executable.

    :param pyfcstm_package_root: Optional injected ``pyfcstm`` package root.
    :type pyfcstm_package_root: str, optional
    :param z3_package_root: Optional injected ``z3`` package root.
    :type z3_package_root: str, optional
    :return: ``(source, destination_directory)`` resource mappings.
    :rtype: typing.Iterator[typing.Tuple[str, str]]

    Example::

        >>> mappings = list(get_resource_files())
        >>> any(dst == 'pyfcstm/diagnostics' for _, dst in mappings)
        True
    """
    yield from get_resources_from_mine(pyfcstm_package_root)
    yield from get_resources_from_package("z3", z3_package_root)


def print_resource_mappings() -> None:
    """
    Print PyInstaller ``--add-data`` arguments for the current environment.

    :return: ``None``.
    :rtype: None

    Example::

        $ python tools/resources.py
    """
    for resource_file, destination in get_resource_files():
        mapping = "{0}{1}{2}".format(resource_file, os.pathsep, destination)
        print("--add-data {0!r}".format(mapping))


def _write_file(path: str, payload: str = "fixture") -> None:
    os.makedirs(os.path.dirname(path), exist_ok=True)
    with open(path, "w", encoding="utf-8") as file:
        file.write(payload)


def _assert_no_forbidden_mappings(mappings: Sequence[ResourceMapping]) -> None:
    forbidden_fragments = (
        "pyfcstm/llm/",
        "inspect_llm_report_schema.json",
        "diagnostics/README",
        "GrammarParser.g4",
        "GrammarLexer.interp",
        "GrammarLexer.tokens",
        "z3/include/",
        "z3.h",
    )
    normalized_sources = [source.replace(os.sep, "/") for source, _ in mappings]
    for source in normalized_sources:
        if any(fragment in source for fragment in forbidden_fragments):
            raise ResourceCollectionError(
                "forbidden resource was collected: {0}".format(source)
            )


def run_self_check() -> Mapping[str, object]:
    """
    Run repo-only positive and adversarial resource collector checks.

    The self-check injects temporary pyfcstm and z3 package roots to prove that
    the allowlist keeps required runtime data while dropping LLM resources,
    ANTLR development metadata, diagnostic maintenance files, and Z3 headers.

    :return: Summary of self-check scenarios.
    :rtype: collections.abc.Mapping[str, object]
    :raises ResourceCollectionError: If the collector keeps a forbidden file or
        fails to reject an incomplete allowlist fixture.

    Example::

        >>> run_self_check()['status']  # doctest: +SKIP
        'ok'
    """
    import tempfile

    checks = []
    with tempfile.TemporaryDirectory(prefix="pyfcstm-resources-check-") as directory:
        pyfcstm_root = os.path.join(directory, "pyfcstm")
        for relative_path in PYFCSTM_DATA_ALLOWLIST:
            _write_file(os.path.join(pyfcstm_root, *relative_path.split("/")))
        forbidden_pyfcstm_files = (
            "llm/fcstm_grammar_guide.md",
            "diagnostics/inspect_llm_report_schema.json",
            "diagnostics/README.md",
            "dsl/grammar/GrammarParser.g4",
            "dsl/grammar/GrammarLexer.interp",
            "dsl/grammar/GrammarLexer.tokens",
        )
        for relative_path in forbidden_pyfcstm_files:
            _write_file(os.path.join(pyfcstm_root, *relative_path.split("/")))

        z3_root = os.path.join(directory, "z3")
        _write_file(os.path.join(z3_root, "__init__.py"))
        _write_file(os.path.join(z3_root, "z3.py"))
        _write_file(os.path.join(z3_root, "include", "z3.h"))
        _write_file(os.path.join(z3_root, "lib", "libz3.so"))
        _write_file(os.path.join(z3_root, "lib", "libz3.so.4.15"))

        mappings = list(get_resource_files(pyfcstm_root, z3_root))
        _assert_no_forbidden_mappings(mappings)
        expected_count = len(PYFCSTM_DATA_ALLOWLIST) + 2
        if len(mappings) != expected_count:
            raise ResourceCollectionError(
                "unexpected resource count: {0} != {1}".format(
                    len(mappings), expected_count
                )
            )
        checks.append("allowlist-positive")

        missing_root = os.path.join(directory, "missing-pyfcstm")
        os.makedirs(missing_root, exist_ok=True)
        try:
            list(get_resources_from_mine(missing_root))
        except ResourceCollectionError:
            checks.append("missing-required-negative")
        else:
            raise ResourceCollectionError(
                "missing pyfcstm resources unexpectedly passed"
            )

        header_only_z3 = os.path.join(directory, "header-only-z3")
        _write_file(os.path.join(header_only_z3, "__init__.py"))
        _write_file(os.path.join(header_only_z3, "include", "z3.h"))
        try:
            list(get_resources_from_package("z3", header_only_z3))
        except ResourceCollectionError:
            checks.append("z3-header-negative")
        else:
            raise ResourceCollectionError(
                "header-only z3 resources unexpectedly passed"
            )

    return {
        "status": "ok",
        "checks": checks,
        "classification": RESOURCE_AUDIT_CLASSIFICATION,
    }


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the resource mapping printer or the repo-only self-check.

    :param argv: Optional argument vector without the program name.
    :type argv: typing.Sequence[str], optional
    :return: Process exit status code.
    :rtype: int
    """
    parser = argparse.ArgumentParser(
        description="List standalone executable PyInstaller resource mappings"
    )
    parser.add_argument(
        "--check", action="store_true", help="run repo-only collector self-checks"
    )
    parser.add_argument(
        "--artifact-name",
        action="store_true",
        help="print the canonical standalone CLI artifact name",
    )
    parser.add_argument(
        "--artifact-path",
        action="store_true",
        help="print the canonical standalone CLI artifact path",
    )
    args = parser.parse_args(argv)
    if args.check:
        result = run_self_check()
        print(
            "resources self-check: {0} ({1})".format(
                result["status"], ", ".join(result["checks"])
            )
        )
    elif args.artifact_name:
        print(get_executable_name())
    elif args.artifact_path:
        print(get_executable_path())
    else:
        print_resource_mappings()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

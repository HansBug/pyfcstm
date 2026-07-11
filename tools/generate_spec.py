#!/usr/bin/env python
"""
Generate the standalone executable spec with a narrow resource allowlist.

The generated spec keeps the CLI runtime modules and hidden imports required by
pyfcstm while delegating data-file selection to :mod:`tools.resources`. That
resource collector includes only diagnostic data, packaged templates, the
application icon, and Z3 native libraries; it excludes development resources
such as LLM prompts, ANTLR source metadata, diagnostic maintenance notes, and Z3
headers.

Example::

    $ python tools/generate_spec.py --check
    $ python tools/generate_spec.py -o pyfcstm.spec
"""

import argparse
import ast
import sys
from pathlib import Path
from typing import Callable, List, Optional, Sequence, Tuple


HIDDEN_IMPORTS = [
    # Force-include the diagnostics package so its bundled codes.yaml and
    # schema.json assets are reachable in standalone builds even if the current
    # import chain changes.
    "pyfcstm.diagnostics",
    "pyfcstm.diagnostics.codes",
    # C, C polling, C++, and C++ polling template configs resolve these
    # render helpers by dotted string at runtime, which PyInstaller cannot
    # infer from static imports.
    "pyfcstm.render.c_runtime",
]


EXCLUDED_MODULES = [
    # The standalone executable excludes non-runtime pyfcstm helper surfaces.
    "pyfcstm.llm",
    # GUI, data-science, and notebook stacks that are not used by the CLI.
    "tkinter",
    "matplotlib",
    "numpy",
    "pandas",
    "scipy",
    "IPython",
    "jupyter",
    "notebook",
    # Test and documentation helpers that should never ship in the standalone build.
    "pytest",
    "unittest",
    "doctest",
    "pydoc",
    # Packaging and installer tooling that is only present in the build environment.
    "PyInstaller",
    "_pyinstaller_hooks_contrib",
    "altgraph",
    "macholib",
    "pefile",
    "win32ctypes",
    "distutils",
    "setuptools",
    "pip",
    # Icon generation dependencies observed in Release Test environments.
    "PIL",
    "cairosvg",
    "cairocffi",
    "cffi",
    "_cffi_backend",
    "cssselect2",
    "defusedxml",
    "tinycss2",
    "webencodings",
    # Miscellaneous stdlib/test helpers that are not required by the CLI runtime.
    "xmlrpc",
    "http.server",
    "_pytest",
    "py",
]

FORBIDDEN_DATA_FRAGMENTS = (
    "pyfcstm/llm/",
    "inspect_llm_report_schema.json",
    "pyfcstm/diagnostics/README",
    "GrammarParser.g4",
    "GrammarLexer.g4",
    "GrammarParser.interp",
    "GrammarLexer.interp",
    "GrammarParser.tokens",
    "GrammarLexer.tokens",
    "z3/include/",
    "z3.h",
)

DataCollector = Callable[[], Sequence[Tuple[str, str]]]


def _executable_name() -> str:
    try:
        from tools.resources import get_executable_name
    except ImportError as error:
        # Direct ``python tools/generate_spec.py`` execution puts tools/ on
        # sys.path instead of the repository root. Only that import-layout
        # failure falls back to the sibling module; dependency import errors
        # from inside tools.resources still propagate.
        if error.name != "tools":
            raise
        from resources import get_executable_name

    return get_executable_name()


def collect_datas(
    bundle_icon: Optional[Path] = None,
    resource_collector: Optional[DataCollector] = None,
) -> List[Tuple[str, str]]:
    """
    Collect data files that need to be packaged by PyInstaller.

    :param bundle_icon: Optional PNG icon included as runtime data for help or
        downstream artifact inspection.
    :type bundle_icon: pathlib.Path, optional
    :param resource_collector: Optional injectable collector for repo-only
        self-checks. Production calls use :func:`tools.resources.get_resource_files`.
    :type resource_collector: typing.Callable[[], typing.Sequence[typing.Tuple[str, str]]], optional
    :return: PyInstaller ``datas`` tuples.
    :rtype: typing.List[typing.Tuple[str, str]]
    :raises ImportError: If the local resource collector cannot be imported.
    :raises tools.resources.ResourceCollectionError: If required resources are
        missing or invalid.

    Example::

        >>> datas = collect_datas(resource_collector=lambda: [("/tmp/x", "pyfcstm")])
        >>> datas
        [('/tmp/x', 'pyfcstm')]
    """
    if resource_collector is None:
        try:
            from tools.resources import get_resource_files
        except ImportError as error:
            # Direct ``python tools/generate_spec.py`` execution puts tools/ on
            # sys.path instead of the repository root. Only that import-layout
            # failure falls back to the sibling module; dependency import errors
            # from inside tools.resources still propagate.
            if error.name != "tools":
                raise
            from resources import get_resource_files

        def resource_collector() -> Sequence[Tuple[str, str]]:
            return tuple(get_resource_files())

    datas = list(resource_collector())

    if bundle_icon:
        bundle_icon_path = Path(bundle_icon)
        if bundle_icon_path.exists():
            datas.append((str(bundle_icon_path), "icons"))
        else:
            print(
                "Warning: Could not find bundled icon: {0}".format(bundle_icon_path),
                file=sys.stderr,
            )

    return datas


def resolve_executable_icon(icon_dir: str) -> Optional[str]:
    """
    Resolve the native executable icon path for the current platform.

    :param icon_dir: Directory containing generated application icons.
    :type icon_dir: str
    :return: Platform-specific icon path, or ``None`` when the platform does
        not use a PyInstaller executable icon.
    :rtype: typing.Optional[str]

    Example::

        >>> resolve_executable_icon('/definitely/missing') is None
        True
    """
    icon_root = Path(icon_dir)
    if sys.platform.startswith("win"):
        icon_path = icon_root / "pyfcstm.ico"
    elif sys.platform == "darwin":
        icon_path = icon_root / "pyfcstm.icns"
    else:
        return None

    if icon_path.exists():
        return str(icon_path)

    print(
        "Warning: Could not find executable icon: {0}".format(icon_path),
        file=sys.stderr,
    )
    return None


def _normalized_data_sources(datas: Sequence[Tuple[str, str]]) -> List[str]:
    return [
        "{0}/{1}".format(destination, Path(source).name).replace("\\", "/")
        for source, destination in datas
    ]


def _assert_datas_are_scoped(
    datas: Sequence[Tuple[str, str]],
) -> None:
    normalized = _normalized_data_sources(datas)
    for entry in normalized:
        if any(fragment in entry for fragment in FORBIDDEN_DATA_FRAGMENTS):
            raise ValueError(
                "forbidden PyInstaller data entry collected: {0}".format(entry)
            )


def generate_spec(
    icon_dir: str = "build/icons",
    resource_collector: Optional[DataCollector] = None,
    executable_name: Optional[str] = None,
) -> Tuple[str, int]:
    """
    Generate PyInstaller spec file content.

    :param icon_dir: Directory containing generated application icons.
    :type icon_dir: str
    :param resource_collector: Optional injectable data collector for self-checks.
    :type resource_collector: typing.Callable[[], typing.Sequence[typing.Tuple[str, str]]], optional
    :param executable_name: Optional PyInstaller executable name. Production
        builds use :func:`tools.resources.get_executable_name`.
    :type executable_name: str, optional
    :return: Generated spec text and data-file count.
    :rtype: typing.Tuple[str, int]
    :raises ValueError: If a forbidden artifact entry is collected.

    Example::

        >>> spec, count = generate_spec(
        ...     icon_dir="/definitely/missing",
        ...     resource_collector=lambda: [("/tmp/libz3.so", "z3/lib")],
        ...     executable_name="pyfcstm-test",
        ... )
        >>> "Analysis(" in spec and count == 1
        True
    """
    icon_root = Path(icon_dir)
    datas = collect_datas(
        bundle_icon=icon_root / "pyfcstm.png", resource_collector=resource_collector
    )
    _assert_datas_are_scoped(datas)
    executable_icon = resolve_executable_icon(str(icon_root))
    if executable_name is None:
        executable_name = _executable_name()

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

# Standalone executable configuration: keep runtime resources narrow and auditable.
# This file is automatically generated by tools/generate_spec.py

a = Analysis(
    ['pyfcstm_cli.py'],
    pathex=[],
    binaries=[],
    datas={datas!r},
    hiddenimports={HIDDEN_IMPORTS!r},
    hookspath=[],
    hooksconfig={{}},
    runtime_hooks=[],
    # Exclude unnecessary modules to reduce size and avoid non-runtime resources.
    excludes={EXCLUDED_MODULES!r},
    noarchive=False,
)

from tools.sanitize_pyinstaller_inputs import (
    install_sanitized_bootstrap_modules,
    sanitize_analysis_inputs,
)

sanitize_analysis_inputs(a)
install_sanitized_bootstrap_modules()

# Use compressed PYZ archive.
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None
)

exe = EXE(
    pyz,
    a.scripts,
    a.binaries,
    a.datas,
    [],
    name={executable_name!r},
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,
    upx=True,
    upx_exclude=[],
    runtime_tmpdir=None,
    console=True,
    disable_windowed_traceback=False,
    argv_emulation=False,
    target_arch=None,
    codesign_identity=None,
    entitlements_file=None,
    icon={executable_icon!r},
)
"""

    return spec_content, len(datas)


def run_self_check() -> dict:
    """
    Run repo-only checks for generated spec resource convergence.

    :return: Summary of self-check scenarios.
    :rtype: dict
    :raises ValueError: If generated data includes forbidden resources or the
        adversarial collector is not rejected.

    Example::

        >>> run_self_check()['status']  # doctest: +SKIP
        'ok'
    """
    checks = []
    safe_datas = (
        ("/tmp/pyfcstm/diagnostics/codes.yaml", "pyfcstm/diagnostics"),
        ("/tmp/pyfcstm/diagnostics/schema.json", "pyfcstm/diagnostics"),
        ("/tmp/pyfcstm/template/index.json", "pyfcstm/template"),
        ("/tmp/pyfcstm/template/c.zip", "pyfcstm/template"),
        ("/tmp/pyfcstm/template/c_poll.zip", "pyfcstm/template"),
        ("/tmp/pyfcstm/template/cpp.zip", "pyfcstm/template"),
        ("/tmp/pyfcstm/template/cpp_poll.zip", "pyfcstm/template"),
        ("/tmp/pyfcstm/template/python.zip", "pyfcstm/template"),
        ("/tmp/z3/lib/libz3.so", "z3/lib"),
    )
    spec_content, data_count = generate_spec(
        icon_dir="/definitely/missing",
        resource_collector=lambda: safe_datas,
        executable_name="pyfcstm-0.5.0-linux-x86_64",
    )
    ast.parse(spec_content)
    if data_count != len(safe_datas):
        raise ValueError("unexpected self-check data count: {0}".format(data_count))
    if "pyfcstm.diagnostics.codes" not in spec_content:
        raise ValueError("diagnostics hidden import missing from generated spec")
    if "pyfcstm.render.c_runtime" not in spec_content:
        raise ValueError(
            "C-family runtime renderer hidden import missing from generated spec"
        )
    if "pyfcstm.llm" not in spec_content:
        raise ValueError("LLM module exclusion missing from generated spec")
    checks.append("spec-positive")

    forbidden_datas = safe_datas + (
        ("/tmp/pyfcstm/llm/fcstm_grammar_guide.md", "pyfcstm/llm"),
    )
    try:
        generate_spec(
            icon_dir="/definitely/missing",
            resource_collector=lambda: forbidden_datas,
            executable_name="pyfcstm-0.5.0-linux-x86_64",
        )
    except ValueError:
        checks.append("forbidden-data-negative")
    else:
        raise ValueError("forbidden data collector unexpectedly passed")

    return {"status": "ok", "checks": checks}


def main(argv: Optional[Sequence[str]] = None) -> int:
    """
    Run the spec generator command line interface.

    :param argv: Optional argument vector without the program name.
    :type argv: typing.Sequence[str], optional
    :return: Process exit status code.
    :rtype: int
    """
    parser = argparse.ArgumentParser(
        description="Generate an optimized standalone executable PyInstaller spec"
    )
    parser.add_argument(
        "-o",
        "--output",
        default="pyfcstm.spec",
        help="Output spec file path (default: pyfcstm.spec)",
    )
    parser.add_argument(
        "--icon-dir",
        default="build/icons",
        help="Generated application icon directory (default: build/icons)",
    )
    parser.add_argument(
        "--check", action="store_true", help="run repo-only generator self-checks"
    )
    parser.add_argument(
        "--executable-name",
        help="override the PyInstaller executable name (defaults to canonical artifact name)",
    )
    args = parser.parse_args(argv)

    if args.check:
        result = run_self_check()
        print(
            "generate_spec self-check: {0} ({1})".format(
                result["status"], ", ".join(result["checks"])
            )
        )
        return 0

    spec_content, data_count = generate_spec(
        icon_dir=args.icon_dir, executable_name=args.executable_name
    )

    with open(args.output, "w", encoding="utf-8") as file:
        file.write(spec_content)

    print("Generated {0} with {1} data files".format(args.output, data_count))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

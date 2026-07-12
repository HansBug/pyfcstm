#!/usr/bin/env python
"""
Generate optimized PyInstaller spec file with all necessary resource files
"""

import argparse
import sys
from pathlib import Path


HIDDEN_IMPORTS = [
    # The executable script enters the stdlib-only bootstrap. Explicitly keep
    # the lazy normal CLI graph reachable for every non-version invocation.
    "pyfcstm.entry",
    "pyfcstm.entry.base",
    "pyfcstm.entry.cli",
    "pyfcstm.entry.dispatch",
    "pyfcstm.entry.bmc",
    "pyfcstm.entry.generate",
    "pyfcstm.entry.inspect",
    "pyfcstm.entry.plantuml",
    "pyfcstm.entry.visualize",
    "pyfcstm.entry.simulate",
    "pyfcstm.entry.simulate.batch",
    "pyfcstm.entry.simulate.commands",
    "pyfcstm.entry.simulate.completer",
    "pyfcstm.entry.simulate.display",
    "pyfcstm.entry.simulate.events",
    "pyfcstm.entry.simulate.logging",
    "pyfcstm.entry.simulate.repl",
    # Force-include the diagnostics package so its bundled `codes.yaml`
    # asset is reachable in the standalone build even when no current
    # import chain references it. PR-2 of issue #103 will make
    # `pyfcstm.model` import this at runtime — pre-bundling here keeps
    # the CI Build matrix green across the rename / refactor.
    "pyfcstm.diagnostics",
    "pyfcstm.diagnostics.codes",
    # pyfcstm.bmc exposes model-aware layers through importlib-based lazy
    # exports. PyInstaller cannot discover those module names statically.
    "pyfcstm.bmc.binding",
    "pyfcstm.bmc.domain",
    "pyfcstm.bmc.source",
    "pyfcstm.bmc.macro",
    "pyfcstm.bmc.expand",
    "pyfcstm.bmc.engine",
    "pyfcstm.bmc.relation",
    "pyfcstm.bmc.properties",
    "pyfcstm.bmc.pipeline",
    "pyfcstm.bmc.witness",
]


EXCLUDED_MODULES = [
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


def collect_datas(bundle_icon=None):
    """Collect data files that need to be packaged"""
    datas = []

    # Try to collect resources from tools.resources
    try:
        from tools.resources import get_resource_files

        for src_file, dst_dir in get_resource_files():
            datas.append((src_file, dst_dir))
    except Exception as e:
        print(
            f"Warning: Could not collect resources from tools.resources: {e}",
            file=sys.stderr,
        )

    if bundle_icon:
        bundle_icon_path = Path(bundle_icon)
        if bundle_icon_path.exists():
            datas.append((str(bundle_icon_path), "icons"))
        else:
            print(
                f"Warning: Could not find bundled icon: {bundle_icon_path}",
                file=sys.stderr,
            )

    build_info_path = Path("pyfcstm/config/build_info.py")
    if not build_info_path.is_file():
        raise FileNotFoundError(
            "missing generated build identity: run make build_info before generating a spec"
        )
    # Onedir builds retain their public executable as ``pyfcstm``. Keeping
    # data below ``pyfcstm/config`` would collide with that executable, so
    # the config loader also probes this private bundle-only data directory.
    datas.append((str(build_info_path.resolve()), "_pyfcstm_build"))

    return datas


def resolve_executable_icon(icon_dir):
    """Resolve the native executable icon path for the current platform."""
    icon_root = Path(icon_dir)
    if sys.platform.startswith("win"):
        icon_path = icon_root / "pyfcstm.ico"
    elif sys.platform == "darwin":
        icon_path = icon_root / "pyfcstm.icns"
    else:
        return None

    if icon_path.exists():
        return str(icon_path)

    print(f"Warning: Could not find executable icon: {icon_path}", file=sys.stderr)
    return None


def generate_spec(icon_dir="build/icons", mode="onefile"):
    """Generate spec file content"""
    if mode not in {"onefile", "onedir"}:
        raise ValueError(f"Unsupported PyInstaller mode: {mode!r}")
    icon_root = Path(icon_dir)
    datas = collect_datas(bundle_icon=icon_root / "pyfcstm.png")
    executable_icon = resolve_executable_icon(icon_root)
    if mode == "onedir":
        executable_inputs = "[],\n    exclude_binaries=True"
        tail = """
coll = COLLECT(
    exe,
    a.binaries,
    a.zipfiles,
    a.datas,
    strip=True,
    upx=True,
    upx_exclude=[],
    name='pyfcstm',
)
"""
    else:
        executable_inputs = "a.binaries,\n    a.datas,\n    []"
        tail = ""

    spec_content = f"""# -*- mode: python ; coding: utf-8 -*-

# Optimized configuration: reduce size, improve startup speed
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
    # Exclude unnecessary modules to reduce size
    excludes={EXCLUDED_MODULES!r},
    noarchive=False,
)

# Use compressed PYZ archive
pyz = PYZ(
    a.pure,
    a.zipped_data,
    cipher=None
)

exe = EXE(
    pyz,
    a.scripts,
    {executable_inputs},
    name='pyfcstm',
    debug=False,
    bootloader_ignore_signals=False,
    strip=True,              # Enable symbol stripping to reduce size
    upx=True,                # Enable UPX compression
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
{tail}"""

    return spec_content, len(datas)


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Generate optimized PyInstaller spec file with all necessary resource files"
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
        "--mode",
        choices=("onefile", "onedir"),
        default="onefile",
        help="PyInstaller bundle mode (default: onefile)",
    )
    args = parser.parse_args()

    spec_content, data_count = generate_spec(icon_dir=args.icon_dir, mode=args.mode)

    # Write spec file
    with open(args.output, "w", encoding="utf-8") as f:
        f.write(spec_content)

    print(f"Generated {args.output} with {data_count} data files")

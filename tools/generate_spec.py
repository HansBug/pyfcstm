#!/usr/bin/env python
"""
Generate optimized PyInstaller spec file with all necessary resource files
"""
import argparse
import sys
from pathlib import Path


EXCLUDED_MODULES = [
    # GUI, data-science, and notebook stacks that are not used by the CLI.
    'tkinter',
    'matplotlib',
    'numpy',
    'pandas',
    'scipy',
    'IPython',
    'jupyter',
    'notebook',
    # Test and documentation helpers that should never ship in the standalone build.
    'pytest',
    'unittest',
    'doctest',
    'pydoc',
    # Packaging and installer tooling that is only present in the build environment.
    'PyInstaller',
    '_pyinstaller_hooks_contrib',
    'altgraph',
    'macholib',
    'pefile',
    'win32ctypes',
    'distutils',
    'setuptools',
    'pip',
    # Icon generation dependencies observed in Release Test environments.
    'PIL',
    'cairosvg',
    'cairocffi',
    'cffi',
    '_cffi_backend',
    'cssselect2',
    'defusedxml',
    'tinycss2',
    'webencodings',
    # Miscellaneous stdlib/test helpers that are not required by the CLI runtime.
    'xmlrpc',
    'http.server',
    '_pytest',
    'py',
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
        print(f"Warning: Could not collect resources from tools.resources: {e}", file=sys.stderr)

    if bundle_icon:
        bundle_icon_path = Path(bundle_icon)
        if bundle_icon_path.exists():
            datas.append((str(bundle_icon_path), 'icons'))
        else:
            print(f"Warning: Could not find bundled icon: {bundle_icon_path}", file=sys.stderr)

    return datas


def collect_third_party_binaries_and_hiddenimports():
    """
    Pull in native binaries + lazy-loaded modules from third-party deps that
    do not ship a stock PyInstaller hook.

    The current consumer is :mod:`py_mini_racer` / :mod:`mini_racer`, which
    bundles the V8 isolate as a platform-specific shared library that
    PyInstaller's import-tracer alone does not pick up. Without it, the
    standalone exe imports the Python wrapper but fails at first
    ``MiniRacer()`` instantiation - exactly the regression that the
    sequence-render CLI smoke tests catch.

    PyInstaller's :func:`collect_dynamic_libs` does not cover
    py-mini-racer's ``libmini_racer.glibc.so`` filename pattern on every
    PyInstaller release we support (the 4.7+ baseline missed the
    multi-suffix form), so we belt-and-suspenders the result with a plain
    filesystem walk over the package directory.
    """
    import importlib

    binaries = []
    hiddenimports = []
    datas_extra = []

    try:
        from PyInstaller.utils.hooks import collect_all
    except Exception as exc:  # pragma: no cover - PyInstaller absent at runtime is impossible here
        print(
            f"Warning: PyInstaller hooks not importable: {exc}",
            file=sys.stderr,
        )
        collect_all = None

    for module_name in ('py_mini_racer', 'mini_racer'):
        # First try the official helper.
        if collect_all is not None:
            try:
                mod_datas, mod_binaries, mod_hiddenimports = collect_all(module_name)
            except Exception as exc:
                # Expected on Pythons where only one of the two distributions
                # is installed. Skip silently for the missing one.
                print(
                    f"Note: collect_all({module_name!r}) skipped: {exc}",
                    file=sys.stderr,
                )
            else:
                datas_extra.extend(mod_datas)
                binaries.extend(mod_binaries)
                hiddenimports.extend(mod_hiddenimports)

        # Belt-and-suspenders: walk the package dir for native libraries.
        # py-mini-racer ships ``libmini_racer.glibc.so`` (Linux),
        # ``libmini_racer.dylib`` (macOS), ``mini_racer.dll`` (Windows).
        try:
            mod = importlib.import_module(module_name)
        except ImportError:
            continue
        mod_init = getattr(mod, '__file__', None)
        if not mod_init:
            continue
        mod_dir = Path(mod_init).parent
        if not mod_dir.is_dir():
            continue
        # Every shared-library extension we expect to see for this dep.
        patterns = (
            '*.so', '*.so.*',
            '*.dylib',
            '*.dll', '*.pyd',
        )
        seen_paths = set()
        for pattern in patterns:
            for native_file in mod_dir.rglob(pattern):
                resolved = str(native_file.resolve())
                if resolved in seen_paths:
                    continue
                seen_paths.add(resolved)
                # py-mini-racer's ``_get_lib_path`` (see py_mini_racer.py:35)
                # under PyInstaller resolves to ``<_MEIPASS>/<libname>`` *flat*
                # at the bundle root, NOT under the package subdirectory. So
                # we have to plant the native lib at ``'.'``. Also stage a
                # copy under the package subdir so non-bundled fallbacks
                # (``pkg_resources.resource_filename``) still resolve, e.g.
                # if a future py-mini-racer release inverts the lookup order.
                binaries.append((resolved, '.'))
                relative_dir = native_file.parent.relative_to(mod_dir.parent)
                binaries.append((resolved, str(relative_dir)))
        # Hidden import for safety: PyInstaller's tracer occasionally drops
        # the wrapper module when it is only referenced via dotted import.
        if module_name not in hiddenimports:
            hiddenimports.append(module_name)

    # Deduplicate binaries based on (src_resolved, dst_dir)
    deduped = []
    seen = set()
    for entry in binaries:
        try:
            key = (str(Path(entry[0]).resolve()), entry[1])
        except Exception:
            key = entry
        if key in seen:
            continue
        seen.add(key)
        deduped.append(entry)
    return deduped, hiddenimports, datas_extra


def resolve_executable_icon(icon_dir):
    """Resolve the native executable icon path for the current platform."""
    icon_root = Path(icon_dir)
    if sys.platform.startswith('win'):
        icon_path = icon_root / 'pyfcstm.ico'
    elif sys.platform == 'darwin':
        icon_path = icon_root / 'pyfcstm.icns'
    else:
        return None

    if icon_path.exists():
        return str(icon_path)

    print(f"Warning: Could not find executable icon: {icon_path}", file=sys.stderr)
    return None


def generate_spec(icon_dir='build/icons'):
    """Generate spec file content"""
    icon_root = Path(icon_dir)
    datas = collect_datas(bundle_icon=icon_root / 'pyfcstm.png')
    binaries, hiddenimports, datas_extra = collect_third_party_binaries_and_hiddenimports()
    datas = datas + datas_extra
    executable_icon = resolve_executable_icon(icon_root)

    spec_content = f'''# -*- mode: python ; coding: utf-8 -*-

# Optimized configuration: reduce size, improve startup speed
# This file is automatically generated by tools/generate_spec.py

a = Analysis(
    ['pyfcstm_cli.py'],
    pathex=[],
    binaries={binaries!r},
    datas={datas!r},
    hiddenimports={hiddenimports!r},
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
    a.binaries,
    a.datas,
    [],
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
'''

    return spec_content, len(datas)


if __name__ == '__main__':
    parser = argparse.ArgumentParser(
        description='Generate optimized PyInstaller spec file with all necessary resource files'
    )
    parser.add_argument(
        '-o', '--output',
        default='pyfcstm.spec',
        help='Output spec file path (default: pyfcstm.spec)'
    )
    parser.add_argument(
        '--icon-dir',
        default='build/icons',
        help='Generated application icon directory (default: build/icons)'
    )
    args = parser.parse_args()

    spec_content, data_count = generate_spec(icon_dir=args.icon_dir)

    # Write spec file
    with open(args.output, 'w', encoding='utf-8') as f:
        f.write(spec_content)

    print(f"Generated {args.output} with {data_count} data files")

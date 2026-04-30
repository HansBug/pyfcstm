"""
Package the JS runtime bundle consumed by :mod:`pyfcstm.jsruntime`.

The bundle is a single self-contained IIFE that contains:

* the public ``jsfcstm`` pipeline (parser → AST → state-machine model →
  diagram IR → ELK graph → ELK layout → SVG string);
* a ``@resvg/resvg-wasm`` binding that turns the SVG into a PNG, with the
  WASM binary supplied separately by the host as base64;
* a small set of base64 helpers and a font-buffer slot.

The script drives ``esbuild`` directly through ``npx``. It does **not**
modify ``pyfcstm/jsruntime/resvg.wasm`` or any font asset — those are
plain copies maintained by hand alongside the bundle.

Usage::

    python tools/package_jsbundle.py

The output goes to ``pyfcstm/jsruntime/bundle.js`` by default. The
``jsfcstm`` source root and output path can be overridden::

    python tools/package_jsbundle.py --jsfcstm editors/jsfcstm \\
        --output pyfcstm/jsruntime/bundle.js
"""
import argparse
import os
import shutil
import subprocess
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
BUNDLE_DIR = REPO_ROOT / 'tools' / 'jsbundle'
ENTRY = BUNDLE_DIR / 'entry.js'
EMPTY_SHIM = BUNDLE_DIR / 'empty.js'
DEFAULT_OUTPUT = REPO_ROOT / 'pyfcstm' / 'jsruntime' / 'bundle.js'
DEFAULT_JSFCSTM = REPO_ROOT / 'editors' / 'jsfcstm'


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        '--jsfcstm', type=Path, default=DEFAULT_JSFCSTM,
        help='Path to editors/jsfcstm root (must already have node_modules).',
    )
    parser.add_argument(
        '--output', type=Path, default=DEFAULT_OUTPUT,
        help='Output bundle path.',
    )
    parser.add_argument(
        '--no-minify', action='store_true',
        help='Skip esbuild --minify (useful for debugging stack traces).',
    )
    return parser.parse_args()


def link_module(node_modules: Path, name: str, target: Path) -> None:
    """
    Drop a symlink ``node_modules/<name>`` pointing at ``target``.

    Replaces an existing entry to keep repeat invocations idempotent.
    """
    link = node_modules / name
    if link.is_symlink() or link.exists():
        if link.is_dir() and not link.is_symlink():
            shutil.rmtree(link)
        else:
            link.unlink()
    link.parent.mkdir(parents=True, exist_ok=True)
    link.symlink_to(target, target_is_directory=True)


def ensure_node_modules(jsfcstm_dir: Path) -> Path:
    """
    Wire ``tools/jsbundle/node_modules`` so esbuild can resolve every
    require() in :mod:`tools.jsbundle.entry`. We point at the existing
    ``editors/jsfcstm/node_modules`` symlink-style instead of running
    ``npm install`` here, so the bundle build does not depend on the
    network (the jsfcstm subproject already pinned everything).
    """
    src_modules = jsfcstm_dir / 'node_modules'
    if not src_modules.is_dir():
        raise SystemExit(
            f'editors/jsfcstm/node_modules not found at {src_modules}; '
            f'run `cd editors/jsfcstm && npm install` first.'
        )
    bundle_modules = BUNDLE_DIR / 'node_modules'
    bundle_modules.mkdir(parents=True, exist_ok=True)
    # jsfcstm itself goes under @pyfcstm/jsfcstm so the bundle entry can
    # `require('@pyfcstm/jsfcstm/...')` matching what the workspace uses.
    (bundle_modules / '@pyfcstm').mkdir(exist_ok=True)
    link_module(bundle_modules / '@pyfcstm', 'jsfcstm', jsfcstm_dir)
    for name in ('elkjs', 'antlr4',
                 'vscode-languageserver', 'vscode-languageserver-textdocument'):
        sub = src_modules / name
        if not sub.exists():
            raise SystemExit(f'expected dependency missing in jsfcstm: {sub}')
        link_module(bundle_modules, name, sub)
    # @resvg/resvg-wasm is declared in tools/jsbundle/package.json — install
    # it locally if not yet present, otherwise use the existing copy.
    resvg_link = bundle_modules / '@resvg' / 'resvg-wasm'
    if not resvg_link.exists():
        subprocess.run(
            ['npm', 'install', '--no-save', '@resvg/resvg-wasm@2.6.2'],
            cwd=str(BUNDLE_DIR), check=True,
        )
    return bundle_modules


def run_esbuild(output: Path, *, minify: bool) -> None:
    """
    Invoke esbuild via ``npx``.

    ``--keep-names`` is mandatory because the parser layer relies on
    ``constructor.name`` string equality (ANTLR-generated context classes
    such as ``Def_assignmentContext``); without it the AST silently
    builds with no rootState and the downstream model returns ``null``.

    ``--main-fields=main,module`` is needed because esbuild's
    ``--platform=neutral`` ignores ``main`` by default.
    """
    args = [
        'npx', '--yes', 'esbuild',
        str(ENTRY),
        '--bundle',
        '--format=iife',
        '--platform=neutral',
        '--target=es2017',
        '--keep-names',
        '--main-fields=main,module',
        f'--alias:fs={EMPTY_SHIM}',
        f'--alias:path={EMPTY_SHIM}',
        f'--alias:url={EMPTY_SHIM}',
        f'--alias:node:url={EMPTY_SHIM}',
        f'--outfile={output}',
    ]
    if minify:
        args.append('--minify')
    output.parent.mkdir(parents=True, exist_ok=True)
    subprocess.run(args, check=True)


def main() -> None:
    args = parse_args()
    if not ENTRY.is_file():
        raise SystemExit(f'bundle entry missing: {ENTRY}')
    ensure_node_modules(args.jsfcstm)
    run_esbuild(args.output, minify=not args.no_minify)
    size = args.output.stat().st_size
    print(f'wrote {args.output} ({size / 1024:.0f} KB)')


if __name__ == '__main__':
    main()

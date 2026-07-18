"""
Build and verify the ignored Python diagram runtime assets.

The command is intentionally a small, deterministic coordinator rather than
part of the public package. It builds the shared ES2017 renderer from the
canonical jsfcstm source, downloads the pinned resvg 0.37 compatibility
artifacts when they are absent, copies the fixed font, and writes a manifest
with byte hashes. ``make build_assets`` is the supported entry point.

The generated files live under ``pyfcstm/assets`` and are ignored by git.
The source lock and this script remain tracked so a clean checkout can
recreate the same package contents.
"""

import argparse
import hashlib
import json
import os
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, List, Set, Tuple


ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT / "pyfcstm" / "assets"
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "asset-lock.json"
ENTRY_PATH = ROOT / "tools" / "diagram_assets" / "python-renderer-entry.ts"
BRIDGE_PATH = ROOT / "tools" / "diagram_assets" / "resvg-bridge.js"
HOST_SHIM_PATH = ROOT / "tools" / "diagram_assets" / "host-shim.js"
JSFCSTM_DIR = ROOT / "editors" / "jsfcstm"
JSFCSTM_LOCK_PATH = JSFCSTM_DIR / "package-lock.json"
ELK_PACKAGE_DIR = JSFCSTM_DIR / "node_modules" / "elkjs"
ELK_API_PATH = JSFCSTM_DIR / "node_modules" / "elkjs" / "lib" / "elk-api.js"
ELK_WORKER_PATH = JSFCSTM_DIR / "node_modules" / "elkjs" / "lib" / "elk-worker.min.js"
ASSET_MARKERS = {
    ".gitignore",
    ".gitkeep",
    "__init__.py",
    "NOTICE.txt",
    "LICENSE-MPL-2.0.txt",
    "LICENSE-EPL-2.0.txt",
    "LICENSE-OFL-1.1.txt",
}


def _node_command(name: str) -> str:
    """Return a subprocess-safe Node command for the current platform."""
    # Windows exposes npm/npx through ``.cmd`` shims. ``shell=False`` (the
    # required safe subprocess mode) does not resolve those shims by their
    # extensionless names on all supported Python versions.
    return name + ".cmd" if os.name == "nt" else name


def sha256_bytes(data: bytes) -> str:
    """Return the lower-case SHA-256 digest for ``data``."""
    return hashlib.sha256(data).hexdigest()


def read_lock() -> Dict[str, object]:
    """Load the checked-in asset lock and validate its top-level shape."""
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    if lock.get("schema") != "pyfcstm-diagram-assets/1":
        raise ValueError("unsupported diagram asset lock schema")
    return lock


def download_locked(url: str, expected_sha256: str) -> bytes:
    """
    Download one immutable asset and verify its digest.

    :param url: Immutable source URL recorded in the lock file.
    :type url: str
    :param expected_sha256: Required SHA-256 digest.
    :type expected_sha256: str
    :return: Downloaded bytes.
    :rtype: bytes
    :raises urllib.error.HTTPError: If the source returns an HTTP error.
    :raises urllib.error.URLError: If the source cannot be reached.
    :raises ValueError: If the downloaded digest differs from the lock.
    """
    with urllib.request.urlopen(url, timeout=120) as response:
        data = response.read()
    actual = sha256_bytes(data)
    if actual != expected_sha256:
        raise ValueError(
            "locked diagram asset hash mismatch for %s: expected %s, got %s"
            % (url, expected_sha256, actual)
        )
    return data


def ensure_js_dependencies() -> None:
    """
    Restore the exact jsfcstm dependency tree required by the asset entry.

    ``python-renderer-entry.ts`` imports ELK from the jsfcstm lockfile rather
    than from an ambient global installation. A clean Python checkout therefore
    needs one deterministic ``npm ci`` before esbuild can resolve that import;
    an existing complete tree is reused so repeated make targets stay cheap.

    :return: ``None``.
    :rtype: None
    :raises subprocess.CalledProcessError: If the lockfile install fails.
    :raises FileNotFoundError: If npm is unavailable or the install omits ELK.
    """
    if ELK_API_PATH.is_file() and ELK_WORKER_PATH.is_file():
        return
    subprocess.run(
        [
            _node_command("npm"),
            "ci",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
        ],
        cwd=str(JSFCSTM_DIR),
        check=True,
    )
    if not ELK_API_PATH.is_file() or not ELK_WORKER_PATH.is_file():
        raise FileNotFoundError(
            "npm ci completed without the locked elkjs API/worker assets"
        )


def elk_tree_sha256() -> str:
    """Return a deterministic digest of every installed ELK package file."""
    if not ELK_PACKAGE_DIR.is_dir():
        raise FileNotFoundError("installed elkjs package directory is missing")
    digest = hashlib.sha256()
    files = []
    for path in ELK_PACKAGE_DIR.rglob("*"):
        if path.is_symlink():
            raise ValueError("installed elkjs package contains a symlink")
        if path.is_file():
            files.append((path.relative_to(ELK_PACKAGE_DIR).as_posix(), path))
    for relative_text, path in sorted(files, key=lambda item: item[0]):
        relative = relative_text.encode("utf-8")
        data = path.read_bytes()
        # npm extracts text files with the platform's native newline policy
        # on some Windows/npm combinations; the package tarball is LF-based.
        if path.suffix.lower() in (".js", ".json", ".md") or relative_text.endswith(
            ".d.ts"
        ):
            data = data.replace(b"\r\n", b"\n")
        digest.update(relative)
        digest.update(b"\0")
        digest.update(data)
        digest.update(b"\0")
    return digest.hexdigest()


def validate_elk_provenance(lock: Dict[str, object]) -> None:
    """Require package-lock metadata and installed ELK bytes to match."""
    try:
        package_lock = json.loads(JSFCSTM_LOCK_PATH.read_text(encoding="utf-8"))
        package = package_lock["packages"]["node_modules/elkjs"]
    except (KeyError, OSError, TypeError, ValueError) as err:
        # KeyError/TypeError/ValueError: package-lock.json has no valid ELK
        # entry; OSError: the tracked lock file cannot be read.
        raise ValueError("jsfcstm package-lock lacks a valid elkjs entry") from err
    renderer = lock.get("renderer")
    if not isinstance(renderer, dict) or not isinstance(renderer.get("elkjs"), dict):
        raise ValueError("diagram asset lock lacks elkjs provenance")
    provenance = renderer["elkjs"]
    expected = {
        "name": "elkjs",
        "version": package.get("version"),
        "repository": "https://github.com/kieler/elkjs",
        "sourceUrl": "https://github.com/kieler/elkjs/tree/v%s"
        % package.get("version"),
        "resolved": package.get("resolved"),
        "integrity": package.get("integrity"),
        "license": package.get("license"),
        "treeSha256": provenance.get("treeSha256"),
    }
    if provenance != expected:
        raise ValueError("diagram asset ELK provenance differs from package-lock")
    expected_tree = provenance.get("treeSha256")
    if not isinstance(expected_tree, str) or expected_tree != elk_tree_sha256():
        raise ValueError("installed elkjs bytes differ from the locked tree digest")


def load_locked_file(path: Path, url: str, expected_sha256: str) -> bytes:
    """
    Reuse a matching local generated file or fetch a verified replacement.

    :param path: Generated asset path.
    :type path: pathlib.Path
    :param url: Immutable source URL.
    :type url: str
    :param expected_sha256: Required digest.
    :type expected_sha256: str
    :return: Verified bytes.
    :rtype: bytes
    """
    if path.is_file():
        data = path.read_bytes()
        if sha256_bytes(data) == expected_sha256:
            return data
    data = download_locked(url, expected_sha256)
    return data


def build_renderer(
    output: Path, esbuild_version: str
) -> Tuple[bytes, Dict[str, object]]:
    """
    Build the canonical renderer as a minified ES2017 IIFE.

    :param output: Temporary output path for the JS bundle.
    :type output: pathlib.Path
    :param esbuild_version: Exact esbuild package version to invoke.
    :type esbuild_version: str
    :return: Bundle bytes and esbuild metafile data.
    :rtype: tuple[bytes, dict]
    :raises subprocess.CalledProcessError: If esbuild fails.
    """
    metafile = output.with_suffix(".meta.json")
    command = [
        _node_command("npx"),
        "--yes",
        "esbuild@%s" % esbuild_version,
        str(ENTRY_PATH),
        "--bundle",
        "--format=iife",
        "--platform=neutral",
        "--target=es2017",
        "--keep-names",
        "--main-fields=main,module",
        "--minify",
        "--metafile=%s" % metafile,
        "--outfile=%s" % output,
    ]
    subprocess.run(command, cwd=str(ROOT), check=True)
    metadata = json.loads(metafile.read_text(encoding="utf-8"))
    return output.read_bytes(), _canonicalize_metafile(metadata)


def _canonicalize_metafile(metadata: Dict[str, object]) -> Dict[str, object]:
    """Remove random staging paths from esbuild metafile output keys."""
    outputs = metadata.get("outputs")
    if not isinstance(outputs, dict):
        return metadata
    canonical_outputs = {}
    for output_path, output_metadata in outputs.items():
        # esbuild records the temporary staging directory in the output key.
        # Keep only the logical filename so manifest hashes stay stable.
        logical_name = str(output_path).replace("\\", "/").rsplit("/", 1)[-1]
        if logical_name in canonical_outputs:
            raise ValueError(
                "esbuild metafile has duplicate logical output: %s" % logical_name
            )
        canonical_outputs[logical_name] = output_metadata
    canonical = dict(metadata)
    canonical["outputs"] = canonical_outputs
    return canonical


def _check_metafile_determinism() -> None:
    """Verify that temporary output directory names cannot affect hashes."""
    base = {"bytes": 1, "inputs": {"entry.ts": {"bytesInOutput": 1}}}
    first = _canonicalize_metafile(
        {"inputs": {}, "outputs": {"/tmp/stage-a/renderer-core.js": base}}
    )
    second = _canonicalize_metafile(
        {"inputs": {}, "outputs": {"/tmp/stage-b/renderer-core.js": base}}
    )
    first_encoded = json.dumps(first, sort_keys=True, separators=(",", ":"))
    second_encoded = json.dumps(second, sort_keys=True, separators=(",", ":"))
    if first_encoded != second_encoded:
        raise ValueError("esbuild metafile canonicalization is not deterministic")


def _check_clean_symlink_safety() -> None:
    """Verify cleanup refuses a root symlink before touching its target."""
    global ASSET_DIR
    with tempfile.TemporaryDirectory(prefix="pyfcstm-asset-check-") as temp_dir:
        temporary_root = Path(temp_dir)
        outside = temporary_root / "outside"
        outside.mkdir()
        victim = outside / "victim.txt"
        victim.write_text("must survive", encoding="ascii")
        linked_root = temporary_root / "assets"
        try:
            linked_root.symlink_to(outside, target_is_directory=True)
        except OSError:
            # Some Windows checkouts deny symlink creation without elevation;
            # the production guard remains fail-closed when symlinks exist.
            return
        original = ASSET_DIR
        ASSET_DIR = linked_root
        try:
            try:
                clean_assets()
            except OSError:
                pass
            else:
                raise AssertionError("cleanup accepted a symlinked asset root")
        finally:
            ASSET_DIR = original
        if victim.read_text(encoding="ascii") != "must survive":
            raise AssertionError("cleanup touched a path outside the asset root")


def load_font(font_path: Path, lock: Dict[str, object]) -> bytes:
    """Load the locked JetBrains Mono face without publishing it yet."""
    font_lock = lock["fonts"]
    if not isinstance(font_lock, dict):
        raise ValueError("font lock must be an object")
    url = str(font_lock["url"])
    digest = str(font_lock["sha256"])
    return load_locked_file(font_path, url, digest)


def build_manifest(
    lock: Dict[str, object],
    files: Iterable[Tuple[str, bytes]],
    metafile: Dict[str, object],
    esbuild_version: str,
) -> bytes:
    """Return deterministic manifest metadata for all generated resources."""
    entries = []
    for relative, data in sorted(files):
        entries.append(
            {"path": relative, "bytes": len(data), "sha256": sha256_bytes(data)}
        )
    manifest = {
        "schema": "pyfcstm-diagram-assets/1",
        "renderer": lock["renderer"],
        "files": entries,
        "esbuild": {
            "version": esbuild_version,
            "target": "es2017",
            "format": "iife",
            "metafileSha256": sha256_bytes(
                json.dumps(metafile, sort_keys=True, separators=(",", ":")).encode(
                    "utf-8"
                )
            ),
        },
    }
    return (json.dumps(manifest, ensure_ascii=True, indent=2) + "\n").encode("utf-8")


def _relative_files(root: Path) -> Set[str]:
    """Return all regular-file paths below ``root`` in POSIX form."""
    if not root.is_dir():
        return set()
    return {
        path.relative_to(root).as_posix()
        for path in root.rglob("*")
        if path.is_file() and not path.is_symlink()
    }


def _assert_no_symlink_tree(root: Path) -> None:
    """Reject symlink entries before a generated tree is consumed."""
    if root.is_symlink():
        raise OSError("diagram asset tree is a symlink: %s" % root)
    if not root.is_dir():
        return
    for path in root.rglob("*"):
        if path.is_symlink():
            raise OSError("diagram asset tree contains a symlink: %s" % path)


def _assert_no_symlink_components(path: Path) -> None:
    """Reject symlink components between the asset root and ``path``."""
    if ASSET_DIR.is_symlink():
        raise OSError("diagram asset root is a symlink: %s" % ASSET_DIR)
    relative = path.relative_to(ASSET_DIR)
    current = ASSET_DIR
    for component in relative.parts:
        current /= component
        if current.is_symlink():
            raise OSError("diagram asset path contains a symlink: %s" % current)


def tracked_asset_paths() -> Set[str]:
    """
    Return tracked paths below ``pyfcstm/assets``.

    The git query keeps cleanup and validation aligned with future tracked
    package markers. Source archives without git metadata use the current
    marker set as a compatibility fallback.

    :return: Relative paths from ``pyfcstm/assets``.
    :rtype: set[str]
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", "pyfcstm/assets"],
            cwd=str(ROOT),
            check=False,
            capture_output=True,
            text=True,
        )
    except OSError:
        # OSError: source archives may not have the git executable; preserve
        # the checked-in package markers so cleanup remains non-destructive.
        return set(ASSET_MARKERS)
    if result.returncode != 0:
        return set(ASSET_MARKERS)
    prefix = "pyfcstm/assets/"
    paths = {
        line.strip()[len(prefix) :]
        for line in result.stdout.splitlines()
        if line.strip().startswith(prefix)
    }
    # Keep the checked-in marker contract even before a new marker file has
    # been staged; this prevents a local rebuild from deleting it.
    return paths | set(ASSET_MARKERS)


def _remove_path(path: Path) -> None:
    """Remove one generated file or directory during publication rollback."""
    if path.is_symlink() or path.is_file():
        path.unlink()
    elif path.is_dir():
        shutil.rmtree(str(path))


def _prune_empty_asset_dirs() -> None:
    """Remove empty generated directories without touching package markers."""
    if not ASSET_DIR.is_dir():
        return
    for path in sorted(
        ASSET_DIR.rglob("*"), key=lambda item: len(item.parts), reverse=True
    ):
        if path.is_dir() and not path.is_symlink():
            if not any(path.iterdir()):
                path.rmdir()


def publish_assets(staging: Path) -> None:
    """
    Atomically publish staged generated resources with rollback protection.

    :param staging: Directory containing only generated package files.
    :type staging: pathlib.Path
    :return: ``None``.
    :rtype: None
    :raises OSError: If a publish or rollback filesystem operation fails.
    """
    _assert_no_symlink_tree(ASSET_DIR)
    _assert_no_symlink_tree(staging)
    tracked = tracked_asset_paths()
    staged = _relative_files(staging)
    existing = _relative_files(ASSET_DIR) - tracked
    backup = staging.parent / (staging.name + "-backup")
    backup.mkdir()
    backed_up: List[str] = []
    published: List[str] = []
    try:
        for relative in sorted(staged | existing):
            destination = ASSET_DIR / relative
            _assert_no_symlink_components(destination.parent)
            if destination.exists() or destination.is_symlink():
                saved = backup / relative
                saved.parent.mkdir(parents=True, exist_ok=True)
                os.replace(str(destination), str(saved))
                backed_up.append(relative)
            if relative in staged:
                destination.parent.mkdir(parents=True, exist_ok=True)
                os.replace(str(staging / relative), str(destination))
                published.append(relative)
        _prune_empty_asset_dirs()
    except (OSError, shutil.Error):
        # OSError/shutil.Error: a filesystem move, directory creation, or
        # rollback operation failed while publishing the staged asset set.
        for relative in reversed(published):
            _remove_path(ASSET_DIR / relative)
        for relative in reversed(backed_up):
            saved = backup / relative
            destination = ASSET_DIR / relative
            destination.parent.mkdir(parents=True, exist_ok=True)
            os.replace(str(saved), str(destination))
        raise
    finally:
        if backup.exists():
            shutil.rmtree(str(backup))


def build_assets() -> None:
    """
    Build all diagram assets and verify their locked provenance.

    :return: ``None``.
    :rtype: None
    :raises ValueError: If a source lock, hash, or size gate is invalid.
    :raises OSError: If the generated directory cannot be written.
    """
    lock = read_lock()
    # Refuse to follow a checkout-provided symlink before any local asset is
    # read or the generated directory is created.  Publication performs the
    # same check later, but build inputs must be protected too.
    _assert_no_symlink_tree(ASSET_DIR)
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    renderer_lock = lock["renderer"]
    if not isinstance(renderer_lock, dict):
        raise ValueError("renderer lock must be an object")
    esbuild_version = str(renderer_lock.get("esbuildVersion", ""))
    if not esbuild_version:
        raise ValueError("renderer lock must pin esbuildVersion")
    ensure_js_dependencies()
    validate_elk_provenance(lock)
    with tempfile.TemporaryDirectory(
        prefix=".pyfcstm-diagram-assets-", dir=str(ASSET_DIR.parent)
    ) as temporary:
        temporary_root = Path(temporary)
        renderer_path = temporary_root / "renderer-core.js"
        renderer, metafile = build_renderer(renderer_path, esbuild_version)
        bundle = load_locked_file(
            ASSET_DIR / "resvg-binding.js",
            str(renderer_lock["resvgBundleUrl"]),
            str(renderer_lock["resvgBundleSha256"]),
        )
        wasm = load_locked_file(
            ASSET_DIR / "resvg.wasm",
            str(renderer_lock["resvgWasmUrl"]),
            str(renderer_lock["resvgWasmSha256"]),
        )
        max_wasm = int(renderer_lock["resvgWasmMaxBytes"])
        if len(wasm) > max_wasm:
            raise ValueError("resvg WASM exceeds the locked byte budget")
        font = load_font(ASSET_DIR / "fonts" / "JetBrainsMono-Regular.ttf", lock)
        bridge = BRIDGE_PATH.read_bytes()
        host_shim = HOST_SHIM_PATH.read_bytes()
        combined = renderer + b"\n" + bundle + b"\n" + bridge
        files = [
            ("renderer.js", combined),
            ("resvg-binding.js", bundle),
            ("resvg.wasm", wasm),
            ("resvg-bridge.js", bridge),
            ("host-shim.js", host_shim),
            ("fonts/JetBrainsMono-Regular.ttf", font),
        ]
        manifest = build_manifest(lock, files, metafile, esbuild_version)
        files.append(("manifest.json", manifest))
        staging = temporary_root / "staged"
        for relative, data in files:
            path = staging / relative
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_bytes(data)
        publish_assets(staging)

    print(
        "built %s (%d bytes)"
        % (ASSET_DIR / "renderer.js", (ASSET_DIR / "renderer.js").stat().st_size)
    )


def clean_assets() -> None:
    """Remove generated files while preserving tracked package markers."""
    _assert_no_symlink_tree(ASSET_DIR)
    if not ASSET_DIR.is_dir():
        return
    tracked = tracked_asset_paths()
    for path in sorted(ASSET_DIR.rglob("*"), reverse=True):
        if not (path.is_file() or path.is_symlink()):
            continue
        relative = path.relative_to(ASSET_DIR).as_posix()
        if relative not in tracked:
            path.unlink()
    _prune_empty_asset_dirs()


def main(argv=None) -> int:
    """
    Run the asset builder command line interface.

    :param argv: Optional argument sequence, defaults to ``None``.
    :type argv: list[str], optional
    :return: Process exit status.
    :rtype: int
    """
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--clean", action="store_true", help="remove generated assets")
    parser.add_argument(
        "--check",
        action="store_true",
        help="run deterministic asset-builder self-checks",
    )
    args = parser.parse_args(argv)
    if args.clean and args.check:
        parser.error("--clean and --check cannot be combined")
    if args.check:
        _check_metafile_determinism()
        _check_clean_symlink_safety()
        print("diagram asset builder: deterministic and safety self-check passed")
    elif args.clean:
        clean_assets()
    else:
        build_assets()
    return 0


if __name__ == "__main__":
    sys.exit(main())

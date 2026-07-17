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
import shutil
import subprocess
import sys
import tempfile
import urllib.request
from pathlib import Path
from typing import Dict, Iterable, Tuple


ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT / "pyfcstm" / "assets"
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "asset-lock.json"
ENTRY_PATH = ROOT / "tools" / "diagram_assets" / "python-renderer-entry.ts"
BRIDGE_PATH = ROOT / "tools" / "diagram_assets" / "resvg-bridge.js"
HOST_SHIM_PATH = ROOT / "tools" / "diagram_assets" / "host-shim.js"
JSFCSTM_DIR = ROOT / "editors" / "jsfcstm"


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


def ensure_locked_file(path: Path, url: str, expected_sha256: str) -> bytes:
    """
    Reuse a matching local generated file or fetch and atomically replace it.

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
    temporary = path.with_suffix(path.suffix + ".tmp")
    temporary.write_bytes(data)
    temporary.replace(path)
    return data


def build_renderer(output: Path, esbuild_version: str) -> Tuple[bytes, Dict[str, object]]:
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
        "npx",
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
    return output.read_bytes(), json.loads(metafile.read_text(encoding="utf-8"))


def copy_font(font_path: Path, lock: Dict[str, object]) -> bytes:
    """Copy the locked JetBrains Mono face into the generated asset tree."""
    font_path.parent.mkdir(parents=True, exist_ok=True)
    font_lock = lock["fonts"]
    if not isinstance(font_lock, dict):
        raise ValueError("font lock must be an object")
    url = str(font_lock["url"])
    digest = str(font_lock["sha256"])
    return ensure_locked_file(font_path, url, digest)


def write_manifest(
    lock: Dict[str, object],
    files: Iterable[Tuple[str, bytes]],
    metafile: Dict[str, object],
    esbuild_version: str,
) -> None:
    """Write deterministic manifest metadata for all generated resources."""
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
    path = ASSET_DIR / "manifest.json"
    path.write_text(
        json.dumps(manifest, ensure_ascii=True, indent=2) + "\n", encoding="utf-8"
    )


def build_assets() -> None:
    """
    Build all diagram assets and verify their locked provenance.

    :return: ``None``.
    :rtype: None
    :raises ValueError: If a source lock, hash, or size gate is invalid.
    :raises OSError: If the generated directory cannot be written.
    """
    lock = read_lock()
    ASSET_DIR.mkdir(parents=True, exist_ok=True)
    renderer_lock = lock["renderer"]
    if not isinstance(renderer_lock, dict):
        raise ValueError("renderer lock must be an object")
    esbuild_version = str(renderer_lock.get("esbuildVersion", ""))
    if not esbuild_version:
        raise ValueError("renderer lock must pin esbuildVersion")
    with tempfile.TemporaryDirectory(prefix="pyfcstm-diagram-assets-") as temporary:
        renderer_path = Path(temporary) / "renderer-core.js"
        renderer, metafile = build_renderer(renderer_path, esbuild_version)
        bundle = ensure_locked_file(
            ASSET_DIR / "resvg-binding.js",
            str(renderer_lock["resvgBundleUrl"]),
            str(renderer_lock["resvgBundleSha256"]),
        )
        wasm = ensure_locked_file(
            ASSET_DIR / "resvg.wasm",
            str(renderer_lock["resvgWasmUrl"]),
            str(renderer_lock["resvgWasmSha256"]),
        )
        max_wasm = int(renderer_lock["resvgWasmMaxBytes"])
        if len(wasm) > max_wasm:
            raise ValueError("resvg WASM exceeds the locked byte budget")
        font = copy_font(ASSET_DIR / "fonts" / "JetBrainsMono-Regular.ttf", lock)

        (ASSET_DIR / "fonts").mkdir(parents=True, exist_ok=True)
        (ASSET_DIR / "resvg-bridge.js").write_text(
            BRIDGE_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )
        (ASSET_DIR / "host-shim.js").write_text(
            HOST_SHIM_PATH.read_text(encoding="utf-8"), encoding="utf-8"
        )
        combined = (
            renderer
            + b"\n"
            + bundle
            + b"\n"
            + (ASSET_DIR / "resvg-bridge.js").read_bytes()
        )
        (ASSET_DIR / "renderer.js").write_bytes(combined)
        files = [
            ("renderer.js", combined),
            ("resvg-binding.js", bundle),
            ("resvg.wasm", wasm),
            ("resvg-bridge.js", (ASSET_DIR / "resvg-bridge.js").read_bytes()),
            ("host-shim.js", (ASSET_DIR / "host-shim.js").read_bytes()),
            ("fonts/JetBrainsMono-Regular.ttf", font),
        ]
        write_manifest(lock, files, metafile, esbuild_version)

    print(
        "built %s (%d bytes)"
        % (ASSET_DIR / "renderer.js", (ASSET_DIR / "renderer.js").stat().st_size)
    )


def clean_assets() -> None:
    """Remove generated files while preserving tracked package markers."""
    if not ASSET_DIR.is_dir():
        return
    for path in sorted(ASSET_DIR.iterdir()):
        if path.name in {
            "__init__.py",
            ".gitkeep",
            "NOTICE.txt",
            "LICENSE-MPL-2.0.txt",
            ".gitignore",
        }:
            continue
        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()


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
    args = parser.parse_args(argv)
    if args.clean:
        clean_assets()
    else:
        build_assets()
    return 0


if __name__ == "__main__":
    sys.exit(main())

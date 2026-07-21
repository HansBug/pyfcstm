"""
Build and verify the ignored Python diagram runtime assets.

The command is intentionally a small, deterministic coordinator rather than
part of the public package. It builds the shared ES2017 renderer from the
canonical jsfcstm source, copies the exact official resvg 2.6.2 package
artifacts, copies the fixed Latin and locale-specific CJK fonts, and writes a manifest
with byte hashes. ``make build_assets`` is the supported entry point.

The generated files live under ``pyfcstm/diagram/assets`` and are ignored by git.
The source lock and this script remain tracked so a clean checkout can
recreate the same package contents.
"""

import argparse
import hashlib
from http.client import IncompleteRead
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
import time
import urllib.error
import urllib.request
from pathlib import Path, PurePosixPath
from typing import Dict, Iterable, List, Set, Tuple


ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT / "pyfcstm" / "diagram" / "assets"
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "asset-lock.json"
ENTRY_PATH = ROOT / "tools" / "diagram_assets" / "python-renderer-entry.ts"
VIEWER_BUILD_PATH = ROOT / "tools" / "diagram_assets" / "build_viewer.js"
BRIDGE_PATH = ROOT / "tools" / "diagram_assets" / "resvg-bridge.js"
HOST_SHIM_PATH = ROOT / "tools" / "diagram_assets" / "host-shim.js"
JSFCSTM_DIR = ROOT / "editors" / "jsfcstm"
VSCODE_DIR = ROOT / "editors" / "vscode"
ANTLR_JAR_PATH = ROOT / "antlr-4.9.3.jar"
JSFCSTM_LOCK_PATH = JSFCSTM_DIR / "package-lock.json"
ELK_PACKAGE_DIR = JSFCSTM_DIR / "node_modules" / "elkjs"
ELK_API_PATH = JSFCSTM_DIR / "node_modules" / "elkjs" / "lib" / "elk-api.js"
ELK_WORKER_PATH = JSFCSTM_DIR / "node_modules" / "elkjs" / "lib" / "elk-worker.min.js"
RESVG_PACKAGE_DIR = JSFCSTM_DIR / "node_modules" / "@resvg" / "resvg-wasm"
ASSET_MARKERS = {
    ".gitignore",
    "README.md",
    "__init__.py",
    "NOTICE.txt",
    "LICENSE-MPL-2.0.txt",
    "LICENSE-EPL-2.0.txt",
    "LICENSE-OFL-1.1.txt",
    "LICENSE-MIT.txt",
}
_DOWNLOAD_ATTEMPTS = 3
_DOWNLOAD_BACKOFF_SECONDS = 1.0
_TRANSIENT_HTTP_CODES = frozenset({408, 429, 500, 502, 503, 504})


def _node_command(name: str) -> str:
    """Return a subprocess-safe Node command for the current platform."""
    # Windows exposes npm/npx through ``.cmd`` shims. ``shell=False`` (the
    # required safe subprocess mode) does not resolve those shims by their
    # extensionless names on all supported Python versions.
    return name + ".cmd" if os.name == "nt" and name in ("npm", "npx") else name


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
    :raises urllib.error.HTTPError: If the source returns a non-transient HTTP
        error or remains unavailable after the retry budget.
    :raises urllib.error.URLError: If the source cannot be reached after the
        retry budget.
    :raises http.client.IncompleteRead: If the source repeatedly closes the
        response before the locked payload is complete.
    :raises TimeoutError: If the source repeatedly exceeds the network timeout.
    :raises OSError: If the remote connection repeatedly closes unexpectedly.
    :raises ValueError: If the downloaded digest differs from the lock.
    """
    for attempt in range(_DOWNLOAD_ATTEMPTS):
        try:
            with urllib.request.urlopen(url, timeout=120) as response:
                data = response.read()
            break
        except urllib.error.HTTPError as err:
            # HTTPError: retry only service throttling/outage responses; a
            # permanent 4xx must fail immediately instead of hiding a bad lock.
            if (
                err.code not in _TRANSIENT_HTTP_CODES
                or attempt + 1 >= _DOWNLOAD_ATTEMPTS
            ):
                raise
        except (urllib.error.URLError, TimeoutError, OSError, IncompleteRead):
            # URLError: DNS/TLS/network failure; TimeoutError: socket timeout;
            # OSError: the peer closed/reset the connection; IncompleteRead:
            # response.read() received only part of the HTTP body.
            if attempt + 1 >= _DOWNLOAD_ATTEMPTS:
                raise
        time.sleep(_DOWNLOAD_BACKOFF_SECONDS * (2**attempt))
    actual = sha256_bytes(data)
    if actual != expected_sha256:
        raise ValueError(
            "locked diagram asset hash mismatch for %s: expected %s, got %s"
            % (url, expected_sha256, actual)
        )
    return data


def _installed_esbuild_is_usable() -> bool:
    """Return whether the existing local esbuild tree executes the lock version."""
    try:
        package_lock = json.loads(JSFCSTM_LOCK_PATH.read_text(encoding="utf-8"))
        package = package_lock["packages"]["node_modules/esbuild"]
        package_json = json.loads(
            (JSFCSTM_DIR / "node_modules" / "esbuild" / "package.json").read_text(
                encoding="utf-8"
            )
        )
    except (KeyError, OSError, TypeError, UnicodeDecodeError, ValueError):
        # KeyError/TypeError/ValueError/UnicodeDecodeError: lock or installed
        # metadata is malformed; OSError: a local package file is unavailable.
        return False
    expected_version = package.get("version")
    if (
        not isinstance(expected_version, str)
        or package_json.get("version") != expected_version
    ):
        return False
    if package_json.get("name") != "esbuild":
        return False
    wrapper = JSFCSTM_DIR / "node_modules" / "esbuild" / "bin" / "esbuild"
    if not wrapper.is_file() or wrapper.stat().st_size == 0:
        return False
    try:
        result = subprocess.run(
            [_node_command("npx"), "--no-install", "esbuild", "--version"],
            cwd=str(JSFCSTM_DIR),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.PIPE,
            text=True,
        )
    except OSError:
        # OSError: npx is unavailable or the existing executable cannot start.
        return False
    return result.returncode == 0 and result.stdout.strip() == expected_version


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
    if (
        ELK_API_PATH.is_file()
        and ELK_WORKER_PATH.is_file()
        and (RESVG_PACKAGE_DIR / "index.min.js").is_file()
        and (RESVG_PACKAGE_DIR / "index_bg.wasm").is_file()
        and (RESVG_PACKAGE_DIR / "package.json").is_file()
        and (JSFCSTM_DIR / "node_modules" / "esbuild").is_dir()
        and _installed_esbuild_is_usable()
    ):
        return
    subprocess.run(
        [
            _node_command("npm"),
            "ci",
            "--include=dev",
            "--ignore-scripts",
            "--no-audit",
            "--no-fund",
        ],
        cwd=str(JSFCSTM_DIR),
        check=True,
    )
    if (
        not ELK_API_PATH.is_file()
        or not ELK_WORKER_PATH.is_file()
        or not (RESVG_PACKAGE_DIR / "index.min.js").is_file()
        or not (RESVG_PACKAGE_DIR / "index_bg.wasm").is_file()
    ):
        raise FileNotFoundError(
            "npm ci completed without the locked ELK/resvg package assets"
        )


def ensure_viewer_dependencies() -> None:
    """Build the local jsfcstm package and install viewer build dependencies.

    The Python diagram asset job starts from a clean checkout and does not run
    the VSCode extension packaging job first.  The standalone viewer reuses
    Vue components from that extension, so the asset target owns this small
    build-time installation.  ``--package-lock=false`` keeps generated local
    file-package metadata out of the source tree; the tracked lock remains the
    provenance record for published extension builds.

    :return: ``None``.
    :rtype: None
    :raises subprocess.CalledProcessError: If the JS package or dependency install fails.
    :raises FileNotFoundError: If the expected viewer package files are absent.
    """
    local_tarball = JSFCSTM_DIR / "jsfcstm.tgz"
    if not local_tarball.is_file() or not (JSFCSTM_DIR / "dist").is_dir():
        if not ANTLR_JAR_PATH.is_file():
            # The JS parser build only needs the jar. The aggregate ``antlr``
            # target also rewrites tracked Python requirement files, which
            # would make release artifacts appear dirty on Windows.
            subprocess.run(["make", "antlr-4.9.3.jar"], cwd=str(ROOT), check=True)
        subprocess.run([_node_command("npm"), "run", "build"], cwd=str(JSFCSTM_DIR), check=True)
        subprocess.run([_node_command("npm"), "run", "pack:local"], cwd=str(JSFCSTM_DIR), check=True)
    required = (
        VSCODE_DIR / "node_modules" / "vue" / "compiler-sfc",
        VSCODE_DIR / "node_modules" / "unplugin-vue",
        VSCODE_DIR / "node_modules" / "svg2pdf.js",
        VSCODE_DIR / "node_modules" / "esbuild",
    )
    if all(path.exists() for path in required):
        return
    subprocess.run(
        [
            _node_command("npm"),
            "install",
            "--ignore-scripts",
            "--package-lock=false",
            "--no-audit",
            "--no-fund",
        ],
        cwd=str(VSCODE_DIR),
        check=True,
    )
    missing = [str(path) for path in required if not path.exists()]
    if missing:
        raise FileNotFoundError("viewer dependency installation omitted: %s" % ", ".join(missing))


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


def validate_esbuild_provenance(lock: Dict[str, object]) -> None:
    """Require the exact lockfile esbuild package used by the builder."""
    renderer = lock.get("renderer")
    if not isinstance(renderer, dict):
        raise ValueError("diagram asset lock lacks renderer provenance")
    expected_version = renderer.get("esbuildVersion")
    if not isinstance(expected_version, str) or not expected_version:
        raise ValueError("diagram asset lock lacks esbuildVersion")
    try:
        package_lock = json.loads(JSFCSTM_LOCK_PATH.read_text(encoding="utf-8"))
        root_package = package_lock["packages"][""]
        package = package_lock["packages"]["node_modules/esbuild"]
    except (KeyError, OSError, TypeError, ValueError) as err:
        # KeyError/TypeError/ValueError: package-lock.json has no valid local
        # esbuild entry; OSError: the tracked lock file cannot be read.
        raise ValueError("jsfcstm package-lock lacks a valid esbuild entry") from err
    dev_dependencies = root_package.get("devDependencies")
    if not isinstance(dev_dependencies, dict):
        raise ValueError("jsfcstm package-lock lacks devDependencies")
    if dev_dependencies.get("esbuild") != expected_version:
        raise ValueError("jsfcstm esbuild devDependency differs from asset lock")
    if package.get("version") != expected_version:
        raise ValueError("installed esbuild version differs from asset lock")
    if not package.get("resolved") or not package.get("integrity"):
        raise ValueError("jsfcstm esbuild entry lacks resolved/integrity provenance")


def validate_viewer_provenance(lock: Dict[str, object]) -> None:
    """Require the locked viewer PDF exporter and esbuild metadata."""
    viewer = lock.get("viewer")
    if not isinstance(viewer, dict):
        raise ValueError("diagram asset lock lacks viewer provenance")
    exporter = viewer.get("svg2pdf")
    if not isinstance(exporter, dict):
        raise ValueError("viewer lock lacks svg2pdf provenance")
    expected_version = exporter.get("version")
    if not isinstance(expected_version, str) or not expected_version:
        raise ValueError("viewer lock lacks svg2pdf version")
    try:
        package_lock = json.loads((VSCODE_DIR / "package-lock.json").read_text(encoding="utf-8"))
        root_package = package_lock["packages"][""]
        package = package_lock["packages"]["node_modules/svg2pdf.js"]
    except (KeyError, OSError, TypeError, ValueError) as err:
        # KeyError/TypeError/ValueError: the tracked viewer lock has no valid
        # exporter entry; OSError: the lock file cannot be read.
        raise ValueError("vscode package-lock lacks a valid svg2pdf.js entry") from err
    dependencies = root_package.get("dependencies")
    if not isinstance(dependencies, dict) or dependencies.get("svg2pdf.js") != expected_version:
        raise ValueError("vscode svg2pdf.js dependency differs from asset lock")
    if package.get("version") != expected_version:
        raise ValueError("installed svg2pdf.js version differs from asset lock")
    if package.get("resolved") != exporter.get("resolved") or package.get("integrity") != exporter.get("integrity"):
        raise ValueError("svg2pdf.js lock provenance differs from package-lock")
    if package.get("license") != exporter.get("license"):
        raise ValueError("svg2pdf.js license differs from asset lock")
    installed = VSCODE_DIR / "node_modules" / "svg2pdf.js" / "package.json"
    if not installed.is_file():
        raise FileNotFoundError("installed svg2pdf.js package is missing")
    installed_package = json.loads(installed.read_text(encoding="utf-8"))
    if installed_package.get("version") != expected_version:
        raise ValueError("installed svg2pdf.js package version differs from asset lock")


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


def validate_resvg_provenance(lock: Dict[str, object]) -> Dict[str, object]:
    """Validate the installed official resvg package and return its lock entry."""
    renderer = lock.get("renderer")
    if not isinstance(renderer, dict):
        raise ValueError("diagram asset lock lacks renderer provenance")
    package_lock_entry = renderer.get("resvgPackage")
    if not isinstance(package_lock_entry, dict):
        raise ValueError("diagram asset lock lacks official resvg package provenance")
    package_path = RESVG_PACKAGE_DIR / "package.json"
    try:
        package = json.loads(package_path.read_text(encoding="utf-8"))
        package_lock = json.loads(JSFCSTM_LOCK_PATH.read_text(encoding="utf-8"))
        installed_lock = package_lock["packages"]["node_modules/@resvg/resvg-wasm"]
    except (KeyError, OSError, TypeError, ValueError) as err:
        # KeyError/TypeError/ValueError: package metadata lacks the expected
        # official entry; OSError: a clean install omitted package metadata.
        raise ValueError("official resvg package metadata is unavailable") from err
    expected_identity = {
        "name": "@resvg/resvg-wasm",
        "version": "2.6.2",
        "license": "MPL-2.0",
    }
    expected_lock_fields = {
        "bindingPath": "index.min.js",
        "wasmPath": "index_bg.wasm",
        "bindingSha256": "590115ae25dead0d688da192f2d31586cdf1f8c70fe294919419c168e03e5c42",
        "wasmSha256": "22bf6e9f9a100d972da0411a69c5ba504367fc1fa87b3b64e3f35e53926d2d70",
        "tarballSha256": "ff51acbb5ee0074601b75c3bea9226a18d346752af787f6d2d3adcdd98493d71",
        "sourceCommit": "9ca058462ac529120c8cc84ddcd6fef644cc5406",
        "patchedSourceCommit": "3495d8705b302d6d266748516973606ca9657906",
        "sourceArchiveSha256": "7ce8697451237577d473361aa688917a48cba00c4a8f3302a833455c9c2013fa",
        "patchedSourceArchiveSha256": "08d15a07f930ee4dfb7971b792697c32059b25a5c10aa283ee672488a2417713",
    }
    if any(package.get(key) != value for key, value in expected_identity.items()):
        raise ValueError("installed resvg package identity differs from the asset lock")
    if any(
        package_lock_entry.get(key) != value
        for key, value in expected_lock_fields.items()
    ):
        raise ValueError("official resvg lock field differs from the pinned value")
    for key in ("version", "resolved", "integrity"):
        if installed_lock.get(key) != package_lock_entry.get(key):
            raise ValueError("resvg package-lock %s differs from the asset lock" % key)
    if installed_lock.get("integrity") != (
        "sha512-FqALmHI8D4o6lk/LRWDnhw95z5eO+eAa6ORjVg09YRR7BkcM6oPHU9uyC0gtQG5vpFLvgpeU4+zEAz2H8APHNw=="
    ):
        raise ValueError(
            "resvg package-lock integrity is not the pinned official value"
        )
    return package_lock_entry


def load_local_locked_file(path: Path, expected_sha256: str) -> bytes:
    """Read one installed package file and verify its immutable digest."""
    if not path.is_file():
        raise FileNotFoundError("locked resvg package file is missing: %s" % path)
    data = path.read_bytes()
    actual = sha256_bytes(data)
    if actual != expected_sha256:
        raise ValueError(
            "locked resvg package hash mismatch for %s: expected %s, got %s"
            % (path, expected_sha256, actual)
        )
    return data


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
        "--no-install",
        "esbuild",
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
    # Resolve the lockfile-installed esbuild from jsfcstm's local node_modules;
    # running npx from the repository root would incorrectly report it missing.
    subprocess.run(command, cwd=str(JSFCSTM_DIR), check=True)
    metadata = json.loads(metafile.read_text(encoding="utf-8"))
    return output.read_bytes(), _canonicalize_metafile(metadata)


def build_viewer(output_dir: Path) -> Tuple[bytes, bytes, Dict[str, object]]:
    """Build the standalone Vue viewer that reuses the VSCode preview components."""
    try:
        subprocess.run(
            [_node_command("node"), str(VIEWER_BUILD_PATH), str(output_dir)],
            cwd=str(ROOT),
            check=True,
        )
    except OSError as err:
        # OSError: Node is unavailable, so the browser asset cannot be built.
        raise RuntimeError("Node.js is required to build the standalone diagram viewer") from err
    viewer_path = output_dir / "viewer.js"
    css_path = output_dir / "viewer.css"
    meta_path = output_dir / "viewer.meta.json"
    if not viewer_path.is_file() or not css_path.is_file():
        raise FileNotFoundError("standalone viewer build did not produce viewer.js/viewer.css")
    metadata = json.loads(meta_path.read_text(encoding="utf-8")) if meta_path.is_file() else {}
    inputs = metadata.get("inputs", {})
    forbidden = ("canvg", "html2canvas", "fast-png", "dompurify")
    if isinstance(inputs, dict):
        bundled_forbidden = sorted(
            path for path in inputs
            if any("/node_modules/%s/" % name in str(path).replace("\\", "/") for name in forbidden)
        )
        if bundled_forbidden:
            raise ValueError(
                "standalone viewer bundles forbidden raster dependencies: %s"
                % ", ".join(bundled_forbidden)
            )
    viewer = viewer_path.read_bytes()
    forbidden_bytes = tuple(name.encode("ascii") for name in forbidden)
    bundled_forbidden_bytes = sorted(
        name for name, marker in zip(forbidden, forbidden_bytes) if marker in viewer
    )
    if bundled_forbidden_bytes:
        raise ValueError(
            "standalone viewer output contains forbidden raster dependency names: %s"
            % ", ".join(bundled_forbidden_bytes)
        )
    # Vue devtools metadata is not needed in a packaged offline viewer and
    # may otherwise leak the maintainer's checkout path into every HTML file.
    viewer = re.sub(br'__file\",\"[^\"]+\"', b'__file\",\"\"', viewer)
    return viewer, css_path.read_bytes(), _canonicalize_metafile(metadata)


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


def font_specs(lock: Dict[str, object]) -> List[Dict[str, object]]:
    """Return the validated deterministic font face specifications."""
    font_lock = lock.get("fonts")
    if not isinstance(font_lock, dict):
        raise ValueError("font lock must be an object")
    faces = font_lock.get("faces")
    if not isinstance(faces, list) or not faces:
        raise ValueError("font lock must contain a non-empty faces list")
    required = {"path", "family", "style", "url", "sha256", "maxBytes"}
    result = []
    seen = set()
    for face in faces:
        if not isinstance(face, dict) or not required.issubset(face):
            raise ValueError("font lock contains an incomplete face entry")
        path = str(face["path"])
        posix_path = PurePosixPath(path)
        safe_path = (
            path == posix_path.as_posix()
            and not posix_path.is_absolute()
            and posix_path.parts[:1] == ("fonts",)
            and len(posix_path.parts) == 2
            and all(part not in ("", ".", "..") for part in posix_path.parts)
            and "\\" not in path
        )
        if path in seen or not safe_path:
            raise ValueError("font lock contains a duplicate or unsafe font path")
        if not str(face["sha256"]).isalnum() or len(str(face["sha256"])) != 64:
            raise ValueError("font lock contains an invalid font digest")
        if int(face["maxBytes"]) <= 0:
            raise ValueError("font lock contains an invalid font size budget")
        seen.add(path)
        result.append(face)
    default_family = str(font_lock.get("defaultFamily", ""))
    if not default_family:
        raise ValueError("font lock must define defaultFamily")
    if sum(int(face["maxBytes"]) for face in result) > int(
        font_lock.get("maxTotalBytes", 0)
    ):
        raise ValueError("font lock total font budget is smaller than face budgets")
    return result


def _check_font_path_safety() -> None:
    """Reject font-lock paths that could escape the generated asset root."""
    lock = read_lock()
    fonts = lock["fonts"]
    if not isinstance(fonts, dict) or not isinstance(fonts.get("faces"), list):
        raise AssertionError("font lock self-check fixture is malformed")
    invalid_paths = (
        "fonts/../setup.py",
        "fonts/../../../.github/workflows/test.yml",
        "../fonts/Regular.ttf",
        "/tmp/Regular.ttf",
        "C:/windows/font.ttf",
        "fonts\\..\\setup.py",
    )
    for invalid in invalid_paths:
        candidate = json.loads(json.dumps(lock))
        candidate["fonts"]["faces"][0]["path"] = invalid
        try:
            font_specs(candidate)
        except ValueError:
            continue
        raise AssertionError("font path escape was accepted: %s" % invalid)


def _check_download_retry() -> None:
    """Verify transient download failures consume a bounded retry budget."""
    original_urlopen = urllib.request.urlopen
    original_sleep = time.sleep
    attempts = []
    sleeps = []
    payload = b"locked-diagram-asset"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return payload

    def flaky_urlopen(_url, timeout):
        assert timeout == 120
        attempts.append(timeout)
        if len(attempts) == 1:
            raise IncompleteRead(b"partial", 10)
        if len(attempts) == 2:
            raise OSError("simulated remote disconnect")
        return Response()

    try:
        urllib.request.urlopen = flaky_urlopen
        time.sleep = lambda delay: sleeps.append(delay)
        result = download_locked("https://example.invalid/asset", sha256_bytes(payload))
    finally:
        urllib.request.urlopen = original_urlopen
        time.sleep = original_sleep
    if result != payload or len(attempts) != 3 or sleeps != [1.0, 2.0]:
        raise AssertionError(
            "download retry self-check used an unexpected schedule: %s/%s"
            % (attempts, sleeps)
        )


def load_fonts(lock: Dict[str, object]) -> List[Tuple[str, bytes]]:
    """Load every locked font face without publishing it yet."""
    loaded = []
    for face in font_specs(lock):
        relative = str(face["path"])
        data = load_locked_file(
            ASSET_DIR / relative,
            str(face["url"]),
            str(face["sha256"]),
        )
        if len(data) > int(face["maxBytes"]):
            raise ValueError("font exceeds the locked byte budget: %s" % relative)
        loaded.append((relative, data))
    total = sum(len(data) for _relative, data in loaded)
    if total > int(lock["fonts"]["maxTotalBytes"]):
        raise ValueError("combined fonts exceed the locked byte budget")
    return loaded


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
        "viewer": lock["viewer"],
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
    Return tracked paths below ``pyfcstm/diagram/assets``.

    The git query keeps cleanup and validation aligned with future tracked
    package markers. Source archives without git metadata use the current
    marker set as a compatibility fallback.

    :return: Relative paths from ``pyfcstm/diagram/assets``.
    :rtype: set[str]
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--", "pyfcstm/diagram/assets"],
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
    prefix = "pyfcstm/diagram/assets/"
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
    ensure_viewer_dependencies()
    validate_esbuild_provenance(lock)
    validate_viewer_provenance(lock)
    validate_elk_provenance(lock)
    resvg_package = validate_resvg_provenance(lock)
    with tempfile.TemporaryDirectory(
        prefix=".pyfcstm-diagram-assets-", dir=str(ASSET_DIR.parent)
    ) as temporary:
        temporary_root = Path(temporary)
        renderer_path = temporary_root / "renderer-core.js"
        renderer, metafile = build_renderer(renderer_path, esbuild_version)
        viewer_dir = temporary_root / "viewer-build"
        viewer_dir.mkdir()
        viewer, viewer_css, viewer_metafile = build_viewer(viewer_dir)
        metafile["viewer"] = viewer_metafile
        bundle = load_local_locked_file(
            RESVG_PACKAGE_DIR / str(resvg_package["bindingPath"]),
            str(resvg_package["bindingSha256"]),
        )
        wasm = load_local_locked_file(
            RESVG_PACKAGE_DIR / str(resvg_package["wasmPath"]),
            str(resvg_package["wasmSha256"]),
        )
        max_wasm = int(renderer_lock["resvgWasmMaxBytes"])
        if len(wasm) > max_wasm:
            raise ValueError("resvg WASM exceeds the locked byte budget")
        fonts = load_fonts(lock)
        bridge = BRIDGE_PATH.read_bytes()
        host_shim = HOST_SHIM_PATH.read_bytes()
        combined = renderer + b"\n" + bundle + b"\n" + bridge
        files = [
            ("renderer.js", combined),
            ("resvg-binding.js", bundle),
            ("resvg.wasm", wasm),
            ("resvg-bridge.js", bridge),
            ("host-shim.js", host_shim),
            ("viewer.js", viewer),
            ("viewer.css", viewer_css),
            *fonts,
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
        validate_esbuild_provenance(read_lock())
        _check_clean_symlink_safety()
        _check_font_path_safety()
        _check_download_retry()
        print("diagram asset builder: deterministic and safety self-check passed")
    elif args.clean:
        clean_assets()
    else:
        build_assets()
    return 0


if __name__ == "__main__":
    sys.exit(main())

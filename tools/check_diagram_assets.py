"""Validate generated Python diagram assets and their git/package boundary."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT / "pyfcstm" / "diagram" / "assets"
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "asset-lock.json"
TRACKED_MARKERS = {
    ".gitignore",
    "README.md",
    "__init__.py",
    "NOTICE.txt",
    "LICENSE-MPL-2.0.txt",
    "LICENSE-EPL-2.0.txt",
    "LICENSE-OFL-1.1.txt",
    "LICENSE-MIT.txt",
}

GENERATED_ASSETS = {
    "renderer.js",
    "resvg-binding.js",
    "resvg-bridge.js",
    "host-shim.js",
    "viewer.js",
    "viewer.css",
    "resvg.wasm",
    "manifest.json",
    "fonts/JetBrainsMono-Regular.ttf",
    "fonts/JetBrainsMono-Medium.ttf",
    "fonts/JetBrainsMono-Bold.ttf",
    "fonts/NotoSansSC-Regular.otf",
    "fonts/NotoSansSC-Bold.otf",
    "fonts/NotoSansTC-Regular.otf",
    "fonts/NotoSansTC-Bold.otf",
    "fonts/NotoSansHK-Regular.otf",
    "fonts/NotoSansHK-Bold.otf",
    "fonts/NotoSansJP-Regular.otf",
    "fonts/NotoSansJP-Bold.otf",
    "fonts/NotoSansKR-Regular.otf",
    "fonts/NotoSansKR-Bold.otf",
}

EXPECTED_FONT_PATHS = frozenset(
    {
        "fonts/JetBrainsMono-Regular.ttf",
        "fonts/JetBrainsMono-Medium.ttf",
        "fonts/JetBrainsMono-Bold.ttf",
        "fonts/NotoSansSC-Regular.otf",
        "fonts/NotoSansSC-Bold.otf",
        "fonts/NotoSansTC-Regular.otf",
        "fonts/NotoSansTC-Bold.otf",
        "fonts/NotoSansHK-Regular.otf",
        "fonts/NotoSansHK-Bold.otf",
        "fonts/NotoSansJP-Regular.otf",
        "fonts/NotoSansJP-Bold.otf",
        "fonts/NotoSansKR-Regular.otf",
        "fonts/NotoSansKR-Bold.otf",
    }
)

CONTROLLED_TEXT_MARKERS = frozenset(TRACKED_MARKERS)


def digest(path: Path) -> str:
    """Return the SHA-256 digest of a generated asset."""
    return hashlib.sha256(path.read_bytes()).hexdigest()


def is_tracked(relative: str) -> bool:
    """
    Return whether git tracks one asset path.

    :param relative: Repository-relative path to inspect.
    :type relative: str
    :return: ``True`` when the path is tracked.
    :rtype: bool
    :raises RuntimeError: If git cannot answer the query.
    """
    try:
        result = subprocess.run(
            ["git", "ls-files", "--error-unmatch", "--", relative],
            cwd=str(ROOT),
            check=False,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
    except OSError as err:
        # OSError: the maintenance checker cannot enforce the tracked/ignored
        # package boundary without a usable git executable.
        raise RuntimeError("git is required for diagram asset boundary checks") from err
    if result.returncode == 0:
        return True
    if result.returncode == 1:
        return False
    raise RuntimeError("git could not inspect diagram asset path: %s" % relative)


def git_boundary_available() -> bool:
    """Return whether Git marker checks can run for this source tree.

    Source archives intentionally have no ``.git`` directory.  Their asset
    content, hashes, and allow-list remain fully checkable, but Git-specific
    tracked/ignored assertions are not meaningful there.

    :return: ``True`` when ``ROOT`` is the repository root of a Git checkout.
    :rtype: bool
    """
    try:
        result = subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            cwd=str(ROOT),
            check=False,
            stdout=subprocess.PIPE,
            stderr=subprocess.DEVNULL,
            text=True,
        )
    except OSError:
        # OSError: source archives may not contain the git executable.
        return False
    if result.returncode != 0:
        return False
    try:
        return Path(result.stdout.strip()).resolve() == ROOT.resolve()
    except (OSError, RuntimeError):
        # OSError/RuntimeError: an invalid or inaccessible Git root cannot
        # prove that the boundary belongs to this project.
        return False


def main() -> int:
    """
    Validate hashes, size limits, syntax, and the asset boundary.

    Git tracked/ignored checks run when this is a repository checkout.  A
    source archive has no Git metadata, so the content and allow-list checks
    remain enforced while only those Git-specific assertions are skipped.

    :return: Process exit status.
    :rtype: int
    :raises ValueError: If any asset contract is violated.
    :raises OSError: If an asset or required command is unavailable.
    """
    manifest_path = ASSET_DIR / "manifest.json"
    if ASSET_DIR.is_symlink():
        raise ValueError("diagram asset root is a symlink: %s" % ASSET_DIR)
    for candidate in ASSET_DIR.rglob("*"):
        if candidate.is_symlink():
            raise ValueError("diagram asset tree contains a symlink: %s" % candidate)
    lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    if manifest.get("schema") != "pyfcstm-diagram-assets/1":
        raise ValueError("unexpected diagram asset manifest schema")
    entries: List[Dict[str, object]] = manifest.get("files", [])
    expected = {str(item["path"]): item for item in entries}
    required = GENERATED_ASSETS - {"manifest.json"}
    if set(expected) != required:
        raise ValueError(
            "manifest asset list does not match the required generated set"
        )

    actual_files = {
        path.relative_to(ASSET_DIR).as_posix()
        for path in ASSET_DIR.rglob("*")
        if path.is_file() and "__pycache__" not in path.parts
    }
    allowed_files = GENERATED_ASSETS | TRACKED_MARKERS
    extras = sorted(actual_files - allowed_files)
    if extras:
        raise ValueError(
            "diagram asset tree contains unregistered files: %s" % ", ".join(extras)
        )

    enforce_git_boundary = git_boundary_available()

    for relative, item in expected.items():
        path = ASSET_DIR / relative
        if not path.is_file():
            raise ValueError("missing generated asset: %s" % path)
        actual_digest = digest(path)
        if actual_digest != item["sha256"] or path.stat().st_size != item["bytes"]:
            raise ValueError("manifest mismatch for generated asset: %s" % relative)
        if enforce_git_boundary:
            result = subprocess.run(
                ["git", "check-ignore", "--quiet", str(path.relative_to(ROOT))],
                cwd=str(ROOT),
                check=False,
            )
            if result.returncode != 0:
                raise ValueError("generated asset is not ignored by git: %s" % relative)
            repository_path = "pyfcstm/diagram/assets/" + relative
            if is_tracked(repository_path):
                raise ValueError("generated asset is tracked by git: %s" % relative)

    for relative in sorted(TRACKED_MARKERS):
        path = ASSET_DIR / relative
        if not path.is_file():
            raise ValueError("missing tracked asset marker: %s" % path)
        if enforce_git_boundary:
            repository_path = "pyfcstm/diagram/assets/" + relative
            if not is_tracked(repository_path):
                raise ValueError(
                    "tracked asset marker is not tracked by git: %s" % relative
                )
            result = subprocess.run(
                ["git", "check-ignore", "--quiet", str(path.relative_to(ROOT))],
                cwd=str(ROOT),
                check=False,
            )
            if result.returncode == 0:
                raise ValueError(
                    "tracked asset marker is ignored by git: %s" % relative
                )

    for relative in sorted(CONTROLLED_TEXT_MARKERS):
        try:
            (ASSET_DIR / relative).read_bytes().decode("utf-8")
        except UnicodeDecodeError as err:
            # UnicodeDecodeError: a controlled asset marker is not valid UTF-8
            # and cannot be read consistently by package consumers.
            raise ValueError(
                "controlled diagram asset must be UTF-8 text: %s" % relative
            ) from err

    renderer = (ASSET_DIR / "renderer.js").read_text(encoding="utf-8")
    if 'orient="auto-start-reverse"' in renderer:
        raise ValueError("generated renderer still contains auto-start-reverse")
    if 'orient="auto"' not in renderer:
        raise ValueError(
            "generated renderer does not contain the canonical auto marker"
        )
    if 'refX="10"' not in renderer:
        raise ValueError("generated renderer does not align marker tips to endpoints")
    renderer_lock = lock["renderer"]
    if not isinstance(renderer_lock, dict):
        raise ValueError("renderer lock must be an object")
    resvg_package = renderer_lock.get("resvgPackage")
    if not isinstance(resvg_package, dict):
        raise ValueError("renderer lock lacks official resvg package provenance")
    required_resvg = {
        "name": "@resvg/resvg-wasm",
        "version": "2.6.2",
        "license": "MPL-2.0",
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
    for key, expected_value in required_resvg.items():
        if resvg_package.get(key) != expected_value:
            raise ValueError("official resvg lock field is invalid: %s" % key)
    package_lock_path = ROOT / "editors" / "jsfcstm" / "package-lock.json"
    try:
        package_lock = json.loads(package_lock_path.read_text(encoding="utf-8"))
        installed_lock = package_lock["packages"]["node_modules/@resvg/resvg-wasm"]
    except (KeyError, OSError, TypeError, ValueError) as err:
        # KeyError/TypeError/ValueError: the tracked npm lock has no valid
        # official package entry; OSError: the lock file cannot be read.
        raise ValueError("jsfcstm package-lock lacks official resvg 2.6.2") from err
    for key in ("version", "resolved", "integrity"):
        if installed_lock.get(key) != resvg_package.get(key):
            raise ValueError("resvg package-lock differs from asset lock: %s" % key)
    if manifest["renderer"] != renderer_lock:
        raise ValueError("generated manifest renderer lock differs from source lock")
    viewer_lock = lock.get("viewer")
    if not isinstance(viewer_lock, dict) or manifest.get("viewer") != viewer_lock:
        raise ValueError("generated manifest viewer lock differs from source lock")
    try:
        viewer_package = json.loads(
            (ROOT / "editors" / "vscode" / "package-lock.json").read_text(encoding="utf-8")
        )["packages"]["node_modules/svg2pdf.js"]
    except (KeyError, OSError, TypeError, ValueError) as err:
        # KeyError/TypeError/ValueError: the tracked viewer lock lacks the
        # exporter entry; OSError: the lock file cannot be read.
        raise ValueError("vscode package-lock lacks svg2pdf.js") from err
    exporter = viewer_lock.get("svg2pdf")
    if not isinstance(exporter, dict) or any(
        viewer_package.get(key) != exporter.get(key)
        for key in ("version", "resolved", "integrity", "license")
    ):
        raise ValueError("svg2pdf.js package provenance differs from asset lock")
    esbuild_meta = manifest.get("esbuild")
    if not isinstance(esbuild_meta, dict):
        raise ValueError("generated manifest is missing esbuild metadata")
    if esbuild_meta.get("version") != renderer_lock.get("esbuildVersion"):
        raise ValueError("manifest esbuild version differs from source lock")
    if len((ASSET_DIR / "resvg.wasm").read_bytes()) > int(
        renderer_lock["resvgWasmMaxBytes"]
    ):
        raise ValueError("resvg WASM exceeds the locked size budget")
    for path in (ASSET_DIR / "manifest.json", ASSET_DIR / "NOTICE.txt"):
        text = path.read_text(encoding="utf-8")
        if "resvg037" in text or "resvg 0.37" in text:
            raise ValueError(
                "diagram asset metadata still references custom resvg 0.37"
            )

    fonts_lock = lock.get("fonts")
    if not isinstance(fonts_lock, dict):
        raise ValueError("font lock must be an object")
    faces = fonts_lock.get("faces")
    if not isinstance(faces, list) or not faces:
        raise ValueError("font lock must contain a non-empty faces list")
    locked_paths = set()
    total_bytes = 0
    for face in faces:
        if not isinstance(face, dict):
            raise ValueError("font lock contains a non-object face")
        relative = str(face.get("path", ""))
        if relative in locked_paths or relative not in expected:
            raise ValueError("font lock path is missing or duplicated: %s" % relative)
        entry = expected[relative]
        if entry["sha256"] != face.get("sha256"):
            raise ValueError(
                "manifest font hash differs from source font lock: %s" % relative
            )
        if int(entry["bytes"]) > int(face["maxBytes"]):
            raise ValueError("font exceeds the locked size budget: %s" % relative)
        locked_paths.add(relative)
        total_bytes += int(entry["bytes"])
    if locked_paths != {
        relative for relative in expected if relative.startswith("fonts/")
    }:
        raise ValueError("manifest font list differs from source font lock")
    if locked_paths != EXPECTED_FONT_PATHS:
        missing = sorted(EXPECTED_FONT_PATHS - locked_paths)
        extra = sorted(locked_paths - EXPECTED_FONT_PATHS)
        raise ValueError(
            "diagram font set must contain all 13 locked faces; missing=%s extra=%s"
            % (", ".join(missing) or "none", ", ".join(extra) or "none")
        )
    if total_bytes > int(fonts_lock.get("maxTotalBytes", 0)):
        raise ValueError("combined fonts exceed the locked size budget")
    if str(fonts_lock.get("defaultFamily", "")) != "JetBrains Mono":
        raise ValueError("font lock default family must be JetBrains Mono")
    if str(fonts_lock.get("defaultCjkLocale", "")) not in {
        "sc",
        "tc",
        "hk",
        "jp",
        "kr",
    }:
        raise ValueError("font lock default CJK locale is invalid")

    subprocess.run(["node", "--check", str(ASSET_DIR / "renderer.js")], check=True)
    if enforce_git_boundary:
        print("diagram assets: hashes, size, syntax, and ignore rules passed")
    else:
        print("diagram assets: hashes, size, and syntax passed (Git boundary skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

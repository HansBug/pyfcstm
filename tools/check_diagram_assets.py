"""Validate generated Python diagram assets and their git/package boundary."""

import hashlib
import json
import subprocess
from pathlib import Path
from typing import Dict, List


ROOT = Path(__file__).resolve().parent.parent
ASSET_DIR = ROOT / "pyfcstm" / "assets"
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "asset-lock.json"
TRACKED_MARKERS = {
    ".gitignore",
    ".gitkeep",
    "__init__.py",
    "NOTICE.txt",
    "LICENSE-MPL-2.0.txt",
    "LICENSE-EPL-2.0.txt",
    "LICENSE-OFL-1.1.txt",
}

GENERATED_ASSETS = {
    "renderer.js",
    "resvg-binding.js",
    "resvg-bridge.js",
    "host-shim.js",
    "resvg.wasm",
    "manifest.json",
    "fonts/JetBrainsMono-Regular.ttf",
}


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
            repository_path = "pyfcstm/assets/" + relative
            if is_tracked(repository_path):
                raise ValueError("generated asset is tracked by git: %s" % relative)

    for relative in sorted(TRACKED_MARKERS):
        path = ASSET_DIR / relative
        if not path.is_file():
            raise ValueError("missing tracked asset marker: %s" % path)
        if enforce_git_boundary:
            repository_path = "pyfcstm/assets/" + relative
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
    if manifest["renderer"] != renderer_lock:
        raise ValueError("generated manifest renderer lock differs from source lock")
    esbuild_meta = manifest.get("esbuild")
    if not isinstance(esbuild_meta, dict):
        raise ValueError("generated manifest is missing esbuild metadata")
    if esbuild_meta.get("version") != renderer_lock.get("esbuildVersion"):
        raise ValueError("manifest esbuild version differs from source lock")
    if len((ASSET_DIR / "resvg.wasm").read_bytes()) > int(
        renderer_lock["resvgWasmMaxBytes"]
    ):
        raise ValueError("resvg WASM exceeds the locked size budget")

    fonts_lock = lock.get("fonts")
    if not isinstance(fonts_lock, dict):
        raise ValueError("font lock must be an object")
    default_font = str(fonts_lock.get("default", ""))
    font_path = "fonts/" + default_font
    if font_path not in expected:
        raise ValueError("manifest is missing the locked default font: %s" % font_path)
    font_entry = expected[font_path]
    if font_entry["sha256"] != fonts_lock.get("sha256"):
        raise ValueError("manifest font hash differs from source font lock")
    if int(font_entry["bytes"]) > int(fonts_lock["maxBytes"]):
        raise ValueError("font exceeds the locked size budget")

    subprocess.run(["node", "--check", str(ASSET_DIR / "renderer.js")], check=True)
    if enforce_git_boundary:
        print("diagram assets: hashes, size, syntax, and ignore rules passed")
    else:
        print("diagram assets: hashes, size, and syntax passed (Git boundary skipped)")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

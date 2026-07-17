"""Check wheel and sdist archives for the generated diagram resources."""

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Iterable


GENERATED_REQUIRED = {
    "pyfcstm/assets/renderer.js",
    "pyfcstm/assets/resvg-binding.js",
    "pyfcstm/assets/resvg-bridge.js",
    "pyfcstm/assets/host-shim.js",
    "pyfcstm/assets/resvg.wasm",
    "pyfcstm/assets/manifest.json",
    "pyfcstm/assets/fonts/JetBrainsMono-Regular.ttf",
}

LEGAL_REQUIRED = {
    "pyfcstm/assets/NOTICE.txt",
    "pyfcstm/assets/LICENSE-MPL-2.0.txt",
    "pyfcstm/assets/LICENSE-EPL-2.0.txt",
    "pyfcstm/assets/LICENSE-OFL-1.1.txt",
}

PACKAGE_REQUIRED = (
    GENERATED_REQUIRED
    | LEGAL_REQUIRED
    | {
        "pyfcstm/assets/__init__.py",
    }
)

OPTIONAL_SOURCE_MARKERS = {
    "pyfcstm/assets/.gitignore",
    "pyfcstm/assets/.gitkeep",
}

_SHA256 = re.compile(r"^[0-9a-f]{64}$")


def check_members(members: Iterable[str], read_member) -> None:
    """Validate exact package members and manifest-listed content hashes."""
    names = set(members)
    missing = sorted(PACKAGE_REQUIRED - names)
    if missing:
        raise ValueError("archive is missing diagram assets: %s" % ", ".join(missing))
    asset_files = {
        name
        for name in names
        if name.startswith("pyfcstm/assets/") and not name.endswith("/")
    }
    extras = sorted(asset_files - PACKAGE_REQUIRED - OPTIONAL_SOURCE_MARKERS)
    if extras:
        raise ValueError(
            "archive contains unregistered diagram assets: %s" % ", ".join(extras)
        )
    manifest = json.loads(read_member("pyfcstm/assets/manifest.json").decode("utf-8"))
    if manifest.get("schema") != "pyfcstm-diagram-assets/1":
        raise ValueError("archive diagram manifest has an unsupported schema")
    manifest_items = manifest.get("files")
    if not isinstance(manifest_items, list):
        raise ValueError("archive diagram manifest files must be a list")
    expected_paths = {
        path[len("pyfcstm/assets/") :]
        for path in GENERATED_REQUIRED
        if path != "pyfcstm/assets/manifest.json"
    }
    seen = set()
    if len(manifest_items) != len(expected_paths):
        raise ValueError("archive diagram manifest has an incomplete file list")
    for item in manifest_items:
        if not isinstance(item, dict):
            raise ValueError("archive diagram manifest contains a non-object entry")
        relative = item.get("path")
        if not isinstance(relative, str) or relative in seen:
            raise ValueError("archive diagram manifest contains a duplicate path")
        if relative not in expected_paths:
            raise ValueError(
                "archive diagram manifest contains an unknown path: %s" % relative
            )
        seen.add(relative)
        size = item.get("bytes")
        digest = item.get("sha256")
        if not isinstance(size, int) or size < 0:
            raise ValueError(
                "archive diagram manifest has invalid byte size: %s" % relative
            )
        if not isinstance(digest, str) or not _SHA256.fullmatch(digest):
            raise ValueError(
                "archive diagram manifest has invalid SHA-256: %s" % relative
            )
        path = "pyfcstm/assets/" + item["path"]
        data = read_member(path)
        if len(data) != size:
            raise ValueError("archive asset size differs from manifest: %s" % path)
        actual_digest = hashlib.sha256(data).hexdigest()
        if actual_digest != digest:
            raise ValueError("archive asset hash differs from manifest: %s" % path)
    if seen != expected_paths:
        raise ValueError("archive diagram manifest is missing one or more assets")


def check_wheel(path: Path) -> None:
    """Check one wheel zip archive."""
    with zipfile.ZipFile(str(path)) as archive:
        check_members(archive.namelist(), archive.read)


def check_sdist(path: Path) -> None:
    """Check one gzip-compressed sdist archive."""
    with tarfile.open(str(path), mode="r:gz") as archive:
        files: Dict[str, bytes] = {}
        for member in archive.getmembers():
            if not member.isfile():
                continue
            stream = archive.extractfile(member)
            if stream is not None:
                files[member.name.split("/", 1)[-1]] = stream.read()

        def read_member(name: str) -> bytes:
            return files[name]

        # ``files`` already strips the archive's versioned top-level
        # directory, leaving package-relative names such as
        # ``pyfcstm/assets/renderer.js``.  Do not strip that package prefix a
        # second time: the required set and manifest reader use the same
        # package-relative namespace.
        check_members(set(files), read_member)


def _self_check() -> None:
    """Exercise the positive and adversarial archive contracts in memory."""
    files = {
        path: (b"x" if path.endswith(".js") else b"asset")
        for path in PACKAGE_REQUIRED
        if path != "pyfcstm/assets/manifest.json"
    }
    manifest_entries = []
    for path in sorted(GENERATED_REQUIRED - {"pyfcstm/assets/manifest.json"}):
        data = files[path]
        manifest_entries.append(
            {
                "path": path[len("pyfcstm/assets/") :],
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    files["pyfcstm/assets/manifest.json"] = json.dumps(
        {"schema": "pyfcstm-diagram-assets/1", "files": manifest_entries}
    ).encode("utf-8")
    check_members(set(files), files.__getitem__)

    corrupted = dict(files)
    corrupted["pyfcstm/assets/renderer.js"] = b"y"
    try:
        check_members(set(corrupted), corrupted.__getitem__)
    except ValueError:
        # A same-length byte mutation must be rejected by the manifest hash.
        pass
    else:
        raise AssertionError("same-length archive corruption was accepted")

    missing_license = dict(files)
    del missing_license["pyfcstm/assets/LICENSE-EPL-2.0.txt"]
    try:
        check_members(set(missing_license), missing_license.__getitem__)
    except ValueError:
        # Legal provenance is a required distribution member.
        pass
    else:
        raise AssertionError("missing third-party license was accepted")


def main() -> int:
    """Validate every wheel and sdist under ``dist``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    parser.add_argument(
        "--check", action="store_true", help="run the archive checker self-check"
    )
    args = parser.parse_args()
    if args.check:
        _self_check()
        print("diagram package checker: adversarial self-check passed")
        return 0
    wheels = sorted(args.dist_dir.glob("*.whl"))
    sdists = sorted(args.dist_dir.glob("*.tar.gz"))
    if not wheels or not sdists:
        raise ValueError("dist directory must contain one wheel and one sdist")
    for wheel in wheels:
        check_wheel(wheel)
    for sdist in sdists:
        check_sdist(sdist)
    print(
        "diagram package archives: %d wheel(s), %d sdist(s) passed"
        % (len(wheels), len(sdists))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

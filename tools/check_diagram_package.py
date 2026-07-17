"""Check wheel and sdist archives for the generated diagram resources."""

import argparse
import json
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Iterable


REQUIRED = {
    "pyfcstm/assets/renderer.js",
    "pyfcstm/assets/resvg-binding.js",
    "pyfcstm/assets/resvg-bridge.js",
    "pyfcstm/assets/host-shim.js",
    "pyfcstm/assets/resvg.wasm",
    "pyfcstm/assets/manifest.json",
    "pyfcstm/assets/fonts/JetBrainsMono-Regular.ttf",
}

TRACKED_MARKERS = {
    "pyfcstm/assets/.gitignore",
    "pyfcstm/assets/.gitkeep",
    "pyfcstm/assets/__init__.py",
    "pyfcstm/assets/NOTICE.txt",
    "pyfcstm/assets/LICENSE-MPL-2.0.txt",
}


def check_members(members: Iterable[str], read_member) -> None:
    """Validate required members and manifest-listed byte sizes."""
    names = set(members)
    missing = sorted(REQUIRED - names)
    if missing:
        raise ValueError("archive is missing diagram assets: %s" % ", ".join(missing))
    asset_files = {
        name
        for name in names
        if name.startswith("pyfcstm/assets/") and not name.endswith("/")
    }
    extras = sorted(asset_files - REQUIRED - TRACKED_MARKERS)
    if extras:
        raise ValueError(
            "archive contains unregistered diagram assets: %s" % ", ".join(extras)
        )
    manifest = json.loads(read_member("pyfcstm/assets/manifest.json").decode("utf-8"))
    for item in manifest["files"]:
        path = "pyfcstm/assets/" + item["path"]
        data = read_member(path)
        if len(data) != item["bytes"]:
            raise ValueError("archive asset size differs from manifest: %s" % path)


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


def main() -> int:
    """Validate the newest wheel and sdist under ``dist``."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--dist-dir", type=Path, default=Path("dist"))
    args = parser.parse_args()
    wheels = sorted(args.dist_dir.glob("*.whl"))
    sdists = sorted(args.dist_dir.glob("*.tar.gz"))
    if not wheels or not sdists:
        raise ValueError("dist directory must contain one wheel and one sdist")
    check_wheel(wheels[-1])
    check_sdist(sdists[-1])
    print("diagram package archives: wheel and sdist assets passed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

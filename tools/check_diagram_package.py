"""Check wheel and sdist archives for the generated diagram resources."""

import argparse
import hashlib
import json
import re
import tarfile
import zipfile
from pathlib import Path
from typing import Dict, Iterable, Optional


ROOT = Path(__file__).resolve().parent.parent
SOURCE_MANIFEST_PATH = ROOT / "pyfcstm" / "assets" / "manifest.json"


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


def check_members(
    members: Iterable[str],
    read_member,
    source_manifest: Optional[Dict[str, object]] = None,
    source_manifest_bytes: Optional[bytes] = None,
    source_files: Optional[Dict[str, bytes]] = None,
) -> Dict[str, str]:
    """Validate exact package members and manifest-listed content hashes.

    :param members: Archive member names.
    :param read_member: Callable returning bytes for one member name.
    :param source_manifest: Current source-tree manifest, when available.
        Distribution checks compare against it so a tampered archive cannot
        make a coordinated asset/manifest mutation self-consistent.
    :type source_manifest: dict, optional
    :param source_manifest_bytes: Authoritative source manifest bytes, when
        available.  Archives must preserve these bytes exactly.
    :type source_manifest_bytes: bytes, optional
    :param source_files: Source-tree bytes for package markers, when available.
        Archive markers must match these bytes exactly.
    :type source_files: dict, optional
    :return: SHA-256 digests for every required package member.
    :rtype: dict
    """
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
    manifest_bytes = read_member("pyfcstm/assets/manifest.json")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("schema") != "pyfcstm-diagram-assets/1":
        raise ValueError("archive diagram manifest has an unsupported schema")
    if source_manifest is not None and manifest != source_manifest:
        raise ValueError("archive diagram manifest differs from the source manifest")
    if source_manifest_bytes is not None and manifest_bytes != source_manifest_bytes:
        raise ValueError("archive diagram manifest bytes differ from the source")
    if source_files is not None:
        for path in PACKAGE_REQUIRED - {"pyfcstm/assets/manifest.json"}:
            expected = source_files.get(path)
            if expected is None or read_member(path) != expected:
                raise ValueError(
                    "archive package marker differs from source: %s" % path
                )
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
    return {
        path: hashlib.sha256(read_member(path)).hexdigest() for path in PACKAGE_REQUIRED
    }


def check_wheel(
    path: Path,
    source_manifest: Optional[Dict[str, object]] = None,
    source_manifest_bytes: Optional[bytes] = None,
    source_files: Optional[Dict[str, bytes]] = None,
) -> Dict[str, str]:
    """Check one wheel zip archive."""
    with zipfile.ZipFile(str(path)) as archive:
        return check_members(
            archive.namelist(),
            archive.read,
            source_manifest,
            source_manifest_bytes,
            source_files,
        )


def check_sdist(
    path: Path,
    source_manifest: Optional[Dict[str, object]] = None,
    source_manifest_bytes: Optional[bytes] = None,
    source_files: Optional[Dict[str, bytes]] = None,
) -> Dict[str, str]:
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
        return check_members(
            set(files),
            read_member,
            source_manifest,
            source_manifest_bytes,
            source_files,
        )


def load_source_manifest() -> Dict[str, object]:
    """Load the manifest used to build the distribution archives."""
    try:
        value = json.loads(SOURCE_MANIFEST_PATH.read_text(encoding="utf-8"))
    except (OSError, ValueError) as err:
        # OSError: the source build did not produce the generated manifest;
        # ValueError: the manifest is not valid JSON.  Both must fail closed.
        raise ValueError(
            "source diagram manifest is unavailable or invalid: %s"
            % SOURCE_MANIFEST_PATH
        ) from err
    if not isinstance(value, dict):
        raise ValueError("source diagram manifest must be a JSON object")
    return value


def load_source_manifest_bytes() -> bytes:
    """Load the exact generated manifest bytes used by package builds."""
    try:
        return SOURCE_MANIFEST_PATH.read_bytes()
    except OSError as err:
        # OSError: the source build did not produce the authoritative manifest.
        raise ValueError(
            "source diagram manifest bytes are unavailable: %s" % SOURCE_MANIFEST_PATH
        ) from err


def load_source_files() -> Dict[str, bytes]:
    """Load source package markers used to anchor archive provenance."""
    source_files = {}
    for relative in PACKAGE_REQUIRED - {"pyfcstm/assets/manifest.json"}:
        path = ROOT / relative
        try:
            source_files[relative] = path.read_bytes()
        except OSError as err:
            # OSError: a source marker is absent or unreadable; accepting an
            # archive without its authoritative marker would be fail-open.
            raise ValueError(
                "source diagram package marker is unavailable: %s" % path
            ) from err
    return source_files


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
    source_manifest = json.loads(files["pyfcstm/assets/manifest.json"].decode("utf-8"))
    source_files = {
        path: data
        for path, data in files.items()
        if path != "pyfcstm/assets/manifest.json"
    }
    source_manifest_bytes = files["pyfcstm/assets/manifest.json"]
    check_members(
        set(files),
        files.__getitem__,
        source_manifest,
        source_manifest_bytes,
        source_files,
    )

    corrupted = dict(files)
    corrupted["pyfcstm/assets/renderer.js"] = b"y"
    try:
        check_members(set(corrupted), corrupted.__getitem__)
    except ValueError:
        # A same-length byte mutation must be rejected by the manifest hash.
        pass
    else:
        raise AssertionError("same-length archive corruption was accepted")

    coordinated = dict(files)
    coordinated["pyfcstm/assets/renderer.js"] = b"y"
    coordinated_manifest = json.loads(json.dumps(source_manifest))
    for item in coordinated_manifest["files"]:
        if item["path"] == "renderer.js":
            item["bytes"] = 1
            item["sha256"] = hashlib.sha256(b"y").hexdigest()
    coordinated["pyfcstm/assets/manifest.json"] = json.dumps(
        coordinated_manifest
    ).encode("utf-8")
    try:
        check_members(
            set(coordinated),
            coordinated.__getitem__,
            source_manifest,
            source_manifest_bytes,
            source_files,
        )
    except ValueError:
        # Updating an archive asset and its embedded manifest must still fail
        # against the source manifest/marker ledger.
        pass
    else:
        raise AssertionError("coordinated archive asset mutation was accepted")

    reformatted = dict(files)
    reformatted["pyfcstm/assets/manifest.json"] = json.dumps(
        source_manifest, sort_keys=True, indent=4
    ).encode("utf-8")
    try:
        check_members(
            set(reformatted),
            reformatted.__getitem__,
            source_manifest,
            source_manifest_bytes,
            source_files,
        )
    except ValueError:
        # A semantically equivalent but byte-different manifest is not the
        # manifest emitted by the source build and must be rejected.
        pass
    else:
        raise AssertionError("manifest byte reformatting was accepted")

    legal_corrupted = dict(files)
    legal_corrupted["pyfcstm/assets/LICENSE-EPL-2.0.txt"] = b"tampered"
    try:
        check_members(
            set(legal_corrupted),
            legal_corrupted.__getitem__,
            source_manifest,
            source_manifest_bytes,
            source_files,
        )
    except ValueError:
        # Legal files are source-anchored even though they are not generated.
        pass
    else:
        raise AssertionError("legal marker mutation was accepted")

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
    source_manifest = load_source_manifest()
    source_manifest_bytes = load_source_manifest_bytes()
    source_files = load_source_files()
    archive_snapshots = []
    for wheel in wheels:
        archive_snapshots.append(
            check_wheel(wheel, source_manifest, source_manifest_bytes, source_files)
        )
    for sdist in sdists:
        archive_snapshots.append(
            check_sdist(sdist, source_manifest, source_manifest_bytes, source_files)
        )
    if any(snapshot != archive_snapshots[0] for snapshot in archive_snapshots[1:]):
        raise ValueError("diagram asset bytes differ across wheel and sdist archives")
    print(
        "diagram package archives: %d wheel(s), %d sdist(s) passed"
        % (len(wheels), len(sdists))
    )
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

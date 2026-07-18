"""Check wheel and sdist archives for the generated diagram resources."""

import argparse
import hashlib
import io
import json
import re
import tarfile
import tempfile
import zipfile
from pathlib import Path
from pathlib import PurePosixPath, PureWindowsPath
from typing import Dict, Iterable, Optional


ROOT = Path(__file__).resolve().parent.parent
SOURCE_MANIFEST_PATH = ROOT / "pyfcstm" / "diagram" / "assets" / "manifest.json"


GENERATED_REQUIRED = {
    "pyfcstm/diagram/assets/renderer.js",
    "pyfcstm/diagram/assets/resvg-binding.js",
    "pyfcstm/diagram/assets/resvg-bridge.js",
    "pyfcstm/diagram/assets/host-shim.js",
    "pyfcstm/diagram/assets/resvg.wasm",
    "pyfcstm/diagram/assets/manifest.json",
    "pyfcstm/diagram/assets/fonts/JetBrainsMono-Regular.ttf",
}

LEGAL_REQUIRED = {
    "pyfcstm/diagram/assets/NOTICE.txt",
    "pyfcstm/diagram/assets/LICENSE-MPL-2.0.txt",
    "pyfcstm/diagram/assets/LICENSE-EPL-2.0.txt",
    "pyfcstm/diagram/assets/LICENSE-OFL-1.1.txt",
}

DOCUMENTATION_REQUIRED = {
    "pyfcstm/diagram/assets/README.md",
}

PACKAGE_REQUIRED = (
    GENERATED_REQUIRED
    | LEGAL_REQUIRED
    | DOCUMENTATION_REQUIRED
    | {
        "pyfcstm/diagram/assets/__init__.py",
    }
)

OPTIONAL_SOURCE_MARKERS = {
    "pyfcstm/diagram/assets/.gitignore",
}

LEGACY_PATH_PREFIXES = (
    "pyfcstm/assets",
    "pyfcstm/diagram_runtime",
)

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
    legacy = sorted(
        name
        for name in names
        if any(
            name == prefix or name.startswith(prefix + "/")
            for prefix in LEGACY_PATH_PREFIXES
        )
    )
    if legacy:
        raise ValueError(
            "archive contains retired diagram paths: %s" % ", ".join(legacy)
        )
    missing = sorted(PACKAGE_REQUIRED - names)
    if missing:
        raise ValueError("archive is missing diagram assets: %s" % ", ".join(missing))
    asset_files = {
        name
        for name in names
        if name.startswith("pyfcstm/diagram/assets/") and not name.endswith("/")
    }
    extras = sorted(asset_files - PACKAGE_REQUIRED - OPTIONAL_SOURCE_MARKERS)
    if extras:
        raise ValueError(
            "archive contains unregistered diagram assets: %s" % ", ".join(extras)
        )
    manifest_bytes = read_member("pyfcstm/diagram/assets/manifest.json")
    manifest = json.loads(manifest_bytes.decode("utf-8"))
    if manifest.get("schema") != "pyfcstm-diagram-assets/1":
        raise ValueError("archive diagram manifest has an unsupported schema")
    if source_manifest is not None and manifest != source_manifest:
        raise ValueError("archive diagram manifest differs from the source manifest")
    if source_manifest_bytes is not None and manifest_bytes != source_manifest_bytes:
        raise ValueError("archive diagram manifest bytes differ from the source")
    if source_files is not None:
        for path in PACKAGE_REQUIRED - {"pyfcstm/diagram/assets/manifest.json"}:
            expected = source_files.get(path)
            if expected is None or read_member(path) != expected:
                raise ValueError(
                    "archive package marker differs from source: %s" % path
                )
    manifest_items = manifest.get("files")
    if not isinstance(manifest_items, list):
        raise ValueError("archive diagram manifest files must be a list")
    expected_paths = {
        path[len("pyfcstm/diagram/assets/") :]
        for path in GENERATED_REQUIRED
        if path != "pyfcstm/diagram/assets/manifest.json"
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
        path = "pyfcstm/diagram/assets/" + item["path"]
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
        roots = set()
        for member in archive.getmembers():
            member_path = PurePosixPath(member.name)
            windows_path = PureWindowsPath(member.name)
            parts = member_path.parts
            if (
                "\\" in member.name
                or member_path.is_absolute()
                or windows_path.is_absolute()
                or windows_path.drive
                or not parts
                or parts[0] in ("", ".", "..")
                or ".." in parts
                or ".." in windows_path.parts
            ):
                raise ValueError(
                    "sdist contains an unsafe member path: %s" % member.name
                )
            roots.add(parts[0])
            if member.isdir():
                continue
            if not member.isfile() or member.issym() or member.islnk():
                raise ValueError(
                    "sdist contains a non-regular member: %s" % member.name
                )
            if len(parts) < 2:
                raise ValueError("sdist contains a root-level file: %s" % member.name)
            stream = archive.extractfile(member)
            if stream is None:
                raise ValueError("sdist member cannot be read: %s" % member.name)
            relative = "/".join(parts[1:])
            if relative in files:
                raise ValueError("sdist contains duplicate member path: %s" % relative)
            files[relative] = stream.read()

        if len(roots) != 1:
            raise ValueError("sdist must contain exactly one top-level directory")

        def read_member(name: str) -> bytes:
            return files[name]

        # ``files`` already strips the archive's versioned top-level
        # directory, leaving package-relative names such as
        # ``pyfcstm/diagram/assets/renderer.js``.  Do not strip that package prefix a
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
    for relative in PACKAGE_REQUIRED - {"pyfcstm/diagram/assets/manifest.json"}:
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
        if path != "pyfcstm/diagram/assets/manifest.json"
    }
    manifest_entries = []
    for path in sorted(GENERATED_REQUIRED - {"pyfcstm/diagram/assets/manifest.json"}):
        data = files[path]
        manifest_entries.append(
            {
                "path": path[len("pyfcstm/diagram/assets/") :],
                "bytes": len(data),
                "sha256": hashlib.sha256(data).hexdigest(),
            }
        )
    files["pyfcstm/diagram/assets/manifest.json"] = json.dumps(
        {"schema": "pyfcstm-diagram-assets/1", "files": manifest_entries}
    ).encode("utf-8")
    source_manifest = json.loads(
        files["pyfcstm/diagram/assets/manifest.json"].decode("utf-8")
    )
    source_files = {
        path: data
        for path, data in files.items()
        if path != "pyfcstm/diagram/assets/manifest.json"
    }
    source_manifest_bytes = files["pyfcstm/diagram/assets/manifest.json"]
    check_members(
        set(files),
        files.__getitem__,
        source_manifest,
        source_manifest_bytes,
        source_files,
    )

    corrupted = dict(files)
    corrupted["pyfcstm/diagram/assets/renderer.js"] = b"y"
    try:
        check_members(set(corrupted), corrupted.__getitem__)
    except ValueError:
        # A same-length byte mutation must be rejected by the manifest hash.
        pass
    else:
        raise AssertionError("same-length archive corruption was accepted")

    coordinated = dict(files)
    coordinated["pyfcstm/diagram/assets/renderer.js"] = b"y"
    coordinated_manifest = json.loads(json.dumps(source_manifest))
    for item in coordinated_manifest["files"]:
        if item["path"] == "renderer.js":
            item["bytes"] = 1
            item["sha256"] = hashlib.sha256(b"y").hexdigest()
    coordinated["pyfcstm/diagram/assets/manifest.json"] = json.dumps(
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
    reformatted["pyfcstm/diagram/assets/manifest.json"] = json.dumps(
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
    legal_corrupted["pyfcstm/diagram/assets/LICENSE-EPL-2.0.txt"] = b"tampered"
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

    with tempfile.TemporaryDirectory(prefix="pyfcstm-sdist-check-") as directory:

        def write_archive(path: Path, entries) -> None:
            """Write tar entries while preserving special-member metadata."""
            with tarfile.open(str(path), mode="w:gz") as archive:
                for name, data, kind in entries:
                    info = tarfile.TarInfo(name)
                    if kind == "symlink":
                        info.type = tarfile.SYMTYPE
                        info.linkname = data
                        archive.addfile(info)
                    elif kind == "hardlink":
                        info.type = tarfile.LNKTYPE
                        info.linkname = data
                        archive.addfile(info)
                    else:
                        payload = (
                            data if isinstance(data, bytes) else data.encode("utf-8")
                        )
                        info.size = len(payload)
                        archive.addfile(info, io.BytesIO(payload))

        root = "pyfcstm-0.0.0"
        valid_entries = [
            (root + "/" + name, data, "file") for name, data in files.items()
        ]

        def expect_failure(label: str, entries, message: str) -> None:
            """Require one specific checker failure for a regression probe."""
            probe_path = Path(directory) / (label + ".tar.gz")
            write_archive(probe_path, entries)
            try:
                check_sdist(probe_path)
            except ValueError as err:
                # ValueError is the public checker failure for malformed sdist
                # paths/members; any other exception indicates a broken probe.
                if message not in str(err):
                    raise AssertionError(
                        "%s failed for the wrong reason: %s" % (label, err)
                    ) from err
            else:
                raise AssertionError("%s was accepted" % label)

        # Keep the root-shadow probe otherwise valid so it cannot pass merely
        # because check_members reports missing assets.
        expect_failure(
            "shadow-root",
            valid_entries
            + [("shadow/pyfcstm/diagram/assets/shadow.js", b"tampered", "file")],
            "exactly one top-level directory",
        )
        expect_failure(
            "duplicate-member",
            valid_entries
            + [(root + "/pyfcstm/diagram/assets/renderer.js", b"duplicate", "file")],
            "duplicate member path",
        )
        expect_failure(
            "absolute-member",
            valid_entries
            + [("/absolute/pyfcstm/diagram/assets/renderer.js", b"x", "file")],
            "unsafe member path",
        )
        expect_failure(
            "parent-member",
            valid_entries
            + [(root + "/../pyfcstm/diagram/assets/renderer.js", b"x", "file")],
            "unsafe member path",
        )
        expect_failure(
            "windows-parent-member",
            valid_entries + [(root + "/..\\shadow/renderer.js", b"x", "file")],
            "unsafe member path",
        )
        expect_failure(
            "windows-drive-member",
            valid_entries + [("C:/pyfcstm/diagram/assets/renderer.js", b"x", "file")],
            "unsafe member path",
        )
        expect_failure(
            "root-level-member",
            valid_entries + [("README", b"x", "file")],
            "root-level file",
        )
        expect_failure(
            "symlink-member",
            valid_entries
            + [
                (
                    root + "/pyfcstm/diagram/assets/link.js",
                    "renderer.js",
                    "symlink",
                )
            ],
            "non-regular member",
        )
        expect_failure(
            "hardlink-member",
            valid_entries
            + [
                (
                    root + "/pyfcstm/diagram/assets/link.js",
                    root + "/pyfcstm/diagram/assets/renderer.js",
                    "hardlink",
                )
            ],
            "non-regular member",
        )
        expect_failure(
            "legacy-asset-path",
            valid_entries
            + [(root + "/pyfcstm/assets/manifest.json", b"retired", "file")],
            "retired diagram paths",
        )

    missing_license = dict(files)
    del missing_license["pyfcstm/diagram/assets/LICENSE-EPL-2.0.txt"]
    try:
        check_members(set(missing_license), missing_license.__getitem__)
    except ValueError:
        # Legal provenance is a required distribution member.
        pass
    else:
        raise AssertionError("missing third-party license was accepted")

    legacy = dict(files)
    legacy["pyfcstm/assets/manifest.json"] = b"retired"
    try:
        check_members(set(legacy), legacy.__getitem__)
    except ValueError as err:
        # A broad MANIFEST.in include must not resurrect the retired asset
        # directory in a source archive.
        if "retired diagram paths" not in str(err):
            raise AssertionError(
                "legacy asset path failed for the wrong reason: %s" % err
            ) from err
    else:
        raise AssertionError("retired asset path was accepted")


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

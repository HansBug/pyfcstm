"""Re-fetch and verify official resvg package/source provenance.

The normal asset checker validates local hashes.  This maintenance command is
the separate network gate that proves the locked npm tarball, source archives,
license files, and patched resvg dependency can still be recovered from their
declared immutable URLs.
"""

import argparse
import hashlib
import io
import json
import re
import tarfile
from pathlib import Path
from typing import Dict
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "asset-lock.json"
PACKAGE_LOCK_PATH = ROOT / "editors" / "jsfcstm" / "package-lock.json"


def _sha256(data: bytes) -> str:
    """Return the SHA-256 digest for one downloaded object."""
    return hashlib.sha256(data).hexdigest()


def _download(url: str) -> bytes:
    """Download one immutable source object with a bounded timeout."""
    request = Request(url, headers={"User-Agent": "pyfcstm-diagram-provenance/1"})
    try:
        with urlopen(request, timeout=60) as response:
            return response.read()
    except (HTTPError, URLError, OSError) as err:
        # HTTPError/URLError: the immutable upstream URL cannot be reached;
        # OSError: the local network stream failed while reading the object.
        raise RuntimeError("unable to download provenance URL: %s" % url) from err


def _archive_urls(url: str):
    """Yield equivalent GitHub archive endpoints for one commit URL."""
    yield url
    match = re.fullmatch(
        r"https://codeload\.github\.com/([^/]+/[^/]+)/tar\.gz/([^/]+)", url
    )
    if match:
        repository, commit = match.groups()
        yield "https://github.com/%s/archive/%s.tar.gz" % (repository, commit)


def _download_archive(url: str, expected_sha256: str) -> bytes:
    """Download a commit archive, tolerating GitHub endpoint variants."""
    failures = []
    for candidate in _archive_urls(url):
        try:
            data = _download(candidate)
        except RuntimeError as err:
            # RuntimeError: one equivalent GitHub endpoint may be unavailable;
            # the next immutable endpoint is still attempted.
            failures.append(str(err))
            continue
        actual = _sha256(data)
        if actual == expected_sha256:
            return data
        failures.append("%s returned %s" % (candidate, actual))
    raise RuntimeError(
        "source archive hash mismatch for %s; tried immutable endpoints (%s)"
        % (url, "; ".join(failures))
    )


def _archive_member(data: bytes, suffix: str) -> bytes:
    """Read one regular tar member whose path ends with ``suffix``."""
    try:
        archive = tarfile.open(fileobj=io.BytesIO(data), mode="r:gz")
    except (OSError, tarfile.TarError) as err:
        # OSError/tarfile.TarError: the upstream source archive is not a valid
        # gzip-compressed tar stream.
        raise RuntimeError("source archive is not a readable tar.gz") from err
    with archive:
        matches = [
            item
            for item in archive.getmembers()
            if item.isfile() and item.name.endswith(suffix)
        ]
        if len(matches) != 1:
            raise RuntimeError(
                "source archive member is missing or ambiguous: %s" % suffix
            )
        stream = archive.extractfile(matches[0])
        if stream is None:
            raise RuntimeError("source archive member cannot be read: %s" % suffix)
        return stream.read()


def _load_lock() -> Dict[str, object]:
    """Read the source and package locks."""
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        package_lock = json.loads(PACKAGE_LOCK_PATH.read_text(encoding="utf-8"))
    except (OSError, UnicodeDecodeError, ValueError) as err:
        # OSError/UnicodeDecodeError/ValueError: source or npm lock metadata
        # is absent or cannot be parsed before network verification starts.
        raise RuntimeError("diagram provenance lock is unavailable") from err
    renderer = lock.get("renderer")
    if not isinstance(renderer, dict) or not isinstance(
        renderer.get("resvgPackage"), dict
    ):
        raise RuntimeError("asset lock lacks official resvg provenance")
    package = renderer["resvgPackage"]
    installed = (package_lock.get("packages") or {}).get(
        "node_modules/@resvg/resvg-wasm"
    )
    if not isinstance(installed, dict):
        raise RuntimeError("package-lock lacks @resvg/resvg-wasm")
    for field in ("version", "resolved", "integrity"):
        if installed.get(field) != package.get(field):
            raise RuntimeError("package-lock differs from asset lock: %s" % field)
    return package


def verify(package: Dict[str, object], check_tarball: bool = True) -> Dict[str, str]:
    """Verify npm and exact source archives against the asset lock."""
    result: Dict[str, str] = {}
    if check_tarball:
        resolved = str(package["resolved"])
        tarball = _download(resolved)
        actual = _sha256(tarball)
        if actual != package["tarballSha256"]:
            raise RuntimeError("npm tarball hash mismatch: %s" % actual)
        result["tarballSha256"] = actual

    for url_key, hash_key, member_key in (
        ("sourceArchiveUrl", "sourceArchiveSha256", "sourceFiles"),
        ("patchedSourceArchiveUrl", "patchedSourceArchiveSha256", "sourceFiles"),
    ):
        url = str(package[url_key])
        archive_data = _download_archive(url, str(package[hash_key]))
        actual = _sha256(archive_data)
        if url_key == "sourceArchiveUrl":
            license_data = _archive_member(archive_data, "/LICENSE")
            cargo_data = _archive_member(archive_data, "/Cargo.toml")
            if _sha256(license_data) != package[member_key]["LICENSE"]:
                raise RuntimeError("resvg-js LICENSE hash mismatch")
            if _sha256(cargo_data) != package[member_key]["Cargo.toml"]:
                raise RuntimeError("resvg-js Cargo.toml hash mismatch")
            cargo_text = cargo_data.decode("utf-8")
            if 'version = "0.34.0"' not in cargo_text:
                raise RuntimeError("resvg-js Cargo.toml does not pin resvg 0.34.0")
            patched_commit = str(package["patchedSourceCommit"])
            if not any(
                token in cargo_text for token in (patched_commit, patched_commit[:8])
            ):
                raise RuntimeError(
                    "resvg-js Cargo.toml does not record the patched source commit"
                )
        else:
            license_data = _archive_member(archive_data, "/resvg/LICENSE.txt")
            expected = package[member_key]["patched-resvg/LICENSE.txt"]
            if _sha256(license_data) != expected:
                raise RuntimeError("patched resvg LICENSE.txt hash mismatch")
        result[hash_key] = actual
    return result


def main(argv=None) -> int:
    """Run the network provenance maintenance gate."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--skip-tarball",
        action="store_true",
        help="skip npm tarball download while debugging source archive failures",
    )
    args = parser.parse_args(argv)
    result = verify(_load_lock(), check_tarball=not args.skip_tarball)
    print(json.dumps(result, sort_keys=True))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

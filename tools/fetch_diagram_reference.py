"""Restore the frozen custom diagram reference bundle for CI maintenance gates."""

import argparse
import base64
import binascii
import hashlib
import json
import shutil
import tarfile
import tempfile
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "reference-lock.json"


def _download(url: str) -> bytes:
    """Download one immutable reference archive."""
    request = Request(url, headers={"User-Agent": "pyfcstm-diagram-reference/1"})
    try:
        with urlopen(request, timeout=120) as response:
            return response.read()
    except (HTTPError, URLError, OSError) as err:
        # HTTPError/URLError: the pinned archive cannot be fetched; OSError:
        # the local network stream failed before the archive was complete.
        raise RuntimeError("unable to download diagram reference archive") from err


def _safe_extract(data: bytes, destination: Path) -> None:
    """Extract a tar archive without permitting path traversal."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as stream:
            stream.write(data)
            stream.flush()
            with tarfile.open(stream.name, mode="r:gz") as archive:
                root = destination.resolve()
                for member in archive.getmembers():
                    candidate = (destination / member.name).resolve()
                    if root != candidate and root not in candidate.parents:
                        raise RuntimeError(
                            "diagram reference archive contains a path traversal"
                        )
                archive.extractall(destination)
    except (OSError, tarfile.TarError) as err:
        # OSError/tarfile.TarError: the downloaded bytes are not a readable
        # gzip tar archive or the temporary file cannot be accessed.
        raise RuntimeError("diagram reference archive is not a valid tar.gz") from err


def main(argv=None) -> int:
    """Restore and verify one locked reference archive."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", type=Path, required=True)
    parser.add_argument("--runtime", required=True, help="Python major.minor")
    args = parser.parse_args(argv)
    try:
        lock = json.loads(LOCK_PATH.read_text(encoding="utf-8"))
        entry = lock["runtimes"][args.runtime]
        url = str(entry["url"])
        expected = str(entry["sha256"])
        encoding = str(entry.get("encoding", "identity"))
    except (KeyError, OSError, TypeError, UnicodeDecodeError, ValueError) as err:
        # KeyError/TypeError/ValueError: the tracked lock has no valid runtime
        # entry; OSError/UnicodeDecodeError: the lock cannot be read.
        raise RuntimeError("diagram reference lock is unavailable") from err
    data = _download(url)
    if encoding == "base64":
        try:
            data = base64.b64decode(data, validate=True)
        except (ValueError, binascii.Error) as err:
            # ValueError/binascii.Error: the text gist is not a valid base64
            # representation of the locked binary reference archive.
            raise RuntimeError("diagram reference base64 payload is malformed") from err
    elif encoding != "identity":
        raise RuntimeError("unsupported diagram reference encoding: %s" % encoding)
    actual = hashlib.sha256(data).hexdigest()
    if actual != expected:
        raise RuntimeError(
            "diagram reference archive hash mismatch: expected %s, got %s"
            % (expected, actual)
        )
    output = args.output.resolve()
    if output.exists():
        shutil.rmtree(output)
    output.mkdir(parents=True)
    _safe_extract(data, output)
    reference = output / "reference.json"
    if not reference.is_file():
        raise RuntimeError("diagram reference archive lacks reference.json")
    print(str(reference))
    return 0


if __name__ == "__main__":
    raise SystemExit(main())

"""Restore the frozen custom diagram reference bundle for CI maintenance gates."""

import argparse
import base64
import binascii
import hashlib
from http.client import IncompleteRead
import json
import shutil
import tarfile
import tempfile
import time
from pathlib import Path
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


ROOT = Path(__file__).resolve().parent.parent
LOCK_PATH = ROOT / "tools" / "diagram_assets" / "reference-lock.json"
_TRANSIENT_HTTP_CODES = frozenset((408, 429, 500, 502, 503, 504))
_DOWNLOAD_ATTEMPTS = 3
_DOWNLOAD_BACKOFF_SECONDS = 1.0


def _download(url: str) -> bytes:
    """Download one immutable reference archive with bounded retries."""
    request = Request(url, headers={"User-Agent": "pyfcstm-diagram-reference/1"})
    for attempt in range(_DOWNLOAD_ATTEMPTS):
        try:
            with urlopen(request, timeout=120) as response:
                return response.read()
        except HTTPError as err:
            # HTTPError: retry only transient throttling/outage responses; a
            # permanent status or an exhausted retry budget fails immediately.
            if (
                err.code not in _TRANSIENT_HTTP_CODES
                or attempt + 1 >= _DOWNLOAD_ATTEMPTS
            ):
                raise RuntimeError(
                    "unable to download diagram reference archive (HTTP %d)" % err.code
                ) from err
        except (IncompleteRead, URLError, TimeoutError, OSError) as err:
            # IncompleteRead: the response body ended early; URLError:
            # DNS/TLS failure; TimeoutError: socket timeout; OSError: peer
            # reset or another local stream failure.
            if attempt + 1 >= _DOWNLOAD_ATTEMPTS:
                raise RuntimeError(
                    "unable to download diagram reference archive after %d attempts"
                    % _DOWNLOAD_ATTEMPTS
                ) from err
        time.sleep(_DOWNLOAD_BACKOFF_SECONDS * (2**attempt))
    raise RuntimeError("unable to download diagram reference archive")


def _check_download_retry() -> None:
    """Verify transient failures retry and permanent HTTP errors do not."""
    original_urlopen = globals()["urlopen"]
    original_sleep = time.sleep
    attempts = []
    sleeps = []
    payload = b"locked-reference-archive"

    class Response:
        def __enter__(self):
            return self

        def __exit__(self, *_args):
            return False

        def read(self):
            return payload

    def flaky_urlopen(_request, timeout):
        if timeout != 120:
            raise AssertionError("reference download changed its timeout")
        attempts.append(len(attempts) + 1)
        if len(attempts) == 1:
            raise IncompleteRead(b"partial", 10)
        if len(attempts) == 2:
            raise OSError("simulated remote disconnect")
        return Response()

    try:
        globals()["urlopen"] = flaky_urlopen
        time.sleep = lambda delay: sleeps.append(delay)
        if _download("https://example.invalid/reference.tar.gz") != payload:
            raise AssertionError("retry self-check returned an unexpected payload")
    finally:
        globals()["urlopen"] = original_urlopen
        time.sleep = original_sleep
    if attempts != [1, 2, 3] or sleeps != [1.0, 2.0]:
        raise AssertionError(
            "reference retry self-check used an unexpected schedule: %s/%s"
            % (attempts, sleeps)
        )

    status_attempts = []
    status_sleeps = []

    def transient_status_urlopen(_request, timeout):
        if timeout != 120:
            raise AssertionError("reference download changed its timeout")
        status_attempts.append(1)
        if len(status_attempts) == 1:
            raise HTTPError(
                "https://example.invalid/reference.tar.gz", 503, "busy", {}, None
            )
        return Response()

    try:
        globals()["urlopen"] = transient_status_urlopen
        time.sleep = lambda delay: status_sleeps.append(delay)
        if _download("https://example.invalid/reference.tar.gz") != payload:
            raise AssertionError("transient HTTP retry returned an unexpected payload")
    finally:
        globals()["urlopen"] = original_urlopen
        time.sleep = original_sleep
    if status_attempts != [1, 1] or status_sleeps != [1.0]:
        raise AssertionError(
            "transient HTTP retry self-check used an unexpected schedule: %s/%s"
            % (status_attempts, status_sleeps)
        )

    permanent_attempts = []

    def permanent_urlopen(_request, timeout):
        if timeout != 120:
            raise AssertionError("reference download changed its timeout")
        permanent_attempts.append(1)
        raise HTTPError(
            "https://example.invalid/reference.tar.gz", 404, "missing", {}, None
        )

    try:
        globals()["urlopen"] = permanent_urlopen

        def no_sleep(_delay):
            raise AssertionError("permanent HTTP errors must not sleep")

        time.sleep = no_sleep
        try:
            _download("https://example.invalid/reference.tar.gz")
        except RuntimeError:
            # RuntimeError: _download wraps the expected permanent HTTP 404.
            pass
        else:
            raise AssertionError("permanent HTTP error was accepted")
    finally:
        globals()["urlopen"] = original_urlopen
        time.sleep = original_sleep
    if permanent_attempts != [1]:
        raise AssertionError("permanent HTTP error was retried")


def _safe_extract(data: bytes, destination: Path) -> None:
    """Extract a tar archive without permitting path traversal."""
    try:
        with tempfile.NamedTemporaryFile(suffix=".tar.gz") as stream:
            stream.write(data)
            stream.flush()
            with tarfile.open(stream.name, mode="r:gz") as archive:
                root = destination.resolve()
                for member in archive.getmembers():
                    if member.issym() or member.islnk():
                        raise RuntimeError(
                            "diagram reference archive contains a link member"
                        )
                    if not (member.isdir() or member.isfile()):
                        raise RuntimeError(
                            "diagram reference archive contains an unsupported member"
                        )
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
    parser.add_argument("--output", type=Path)
    parser.add_argument("--runtime", help="Python major.minor")
    parser.add_argument(
        "--check",
        action="store_true",
        help="run the bounded download retry self-check without network access",
    )
    args = parser.parse_args(argv)
    if args.check:
        _check_download_retry()
        print("diagram reference fetcher: retry self-check passed")
        return 0
    if args.output is None or args.runtime is None:
        parser.error("--output and --runtime are required unless --check is used")
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

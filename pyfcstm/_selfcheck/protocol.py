"""Wire-level framing and validation for self-check worker results."""

import json
import re
from dataclasses import dataclass
from typing import Any, Dict, List, Optional


FRAME_PREFIX = b"PYFCSTM_SELF_CHECK_RESULT_V1 "
WORKER_SCHEMA = "pyfcstm-selfcheck-worker/v1"
MAX_ENVELOPE_BYTES = 8 * 1024 * 1024
MAX_RESULT_FILE_BYTES = MAX_ENVELOPE_BYTES * 2
_NONCE_RE = re.compile(r"[0-9a-f]{32}")


@dataclass(frozen=True)
class FrameReadOutcome:
    """
    Result of reading a file or stdout frame stream.

    :param envelope: Validated JSON envelope, defaults to ``None``.
    :type envelope: Optional[Dict[str, Any]], optional
    :param error_code: Stable protocol error, defaults to ``None``.
    :type error_code: Optional[str], optional
    :param frame_count: Number of valid or attempted frames, defaults to ``0``.
    :type frame_count: int, optional

    Example::

        >>> FrameReadOutcome(error_code="missing_result").error_code
        'missing_result'
    """

    envelope: Optional[Dict[str, Any]] = None
    error_code: Optional[str] = None
    frame_count: int = 0


def make_nonce() -> str:
    """Return a cryptographically random 32-character lowercase nonce."""
    import secrets

    return secrets.token_hex(16)


def is_valid_nonce(nonce: str) -> bool:
    """Return whether *nonce* has the fixed wire representation."""
    return isinstance(nonce, str) and _NONCE_RE.fullmatch(nonce) is not None


def build_start_gate(nonce: str) -> bytes:
    """
    Build the parent-to-worker start gate.

    :param nonce: Lowercase 32-character worker nonce.
    :type nonce: str
    :return: Bytes containing ``b"GO "`` + nonce + one real LF byte.
    :rtype: bytes
    :raises ValueError: If the nonce is not valid.

    Example::

        >>> build_start_gate("0" * 32)[-1:]
        b'\\n'
    """
    if not is_valid_nonce(nonce):
        raise ValueError("invalid self-check nonce")
    return b"GO " + nonce.encode("ascii") + b"\x0a"


def encode_result_frame(envelope: Dict[str, Any]) -> bytes:
    """
    Encode one canonical result frame.

    :param envelope: JSON-compatible worker envelope.
    :type envelope: Dict[str, Any]
    :return: Prefix, canonical JSON, and one LF byte.
    :rtype: bytes
    :raises ValueError: If the frame exceeds the protocol size limit.

    Example::

        >>> encode_result_frame({"schema": WORKER_SCHEMA, "nonce": "0" * 32, "status": "PASS"})[-1:]
        b'\\n'
    """
    encoded = json.dumps(
        envelope, ensure_ascii=True, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    frame = FRAME_PREFIX + encoded + b"\x0a"
    if len(frame) > MAX_ENVELOPE_BYTES:
        raise ValueError("envelope_too_large")
    return frame


def _decode_frame(
    frame: bytes, expected_nonce: str, expected_check_id: Optional[str] = None
) -> Dict[str, Any]:
    if len(frame) > MAX_ENVELOPE_BYTES:
        raise ValueError("envelope_too_large")
    if not frame.endswith(b"\x0a"):
        raise ValueError("missing_lf")
    body = frame[:-1]
    if not body.startswith(FRAME_PREFIX):
        raise ValueError("invalid_prefix")
    try:
        payload = json.loads(body[len(FRAME_PREFIX) :].decode("ascii"))
    except (UnicodeDecodeError, ValueError) as err:
        # Invalid UTF-8/JSON is a protocol fault, not a worker PASS.
        raise ValueError("invalid_json") from err
    if not isinstance(payload, dict):
        raise ValueError("invalid_envelope")
    if payload.get("schema") != WORKER_SCHEMA:
        raise ValueError("schema_mismatch")
    if payload.get("nonce") != expected_nonce:
        raise ValueError("wrong_nonce")
    if expected_check_id is not None and payload.get("check_id") != expected_check_id:
        raise ValueError("wrong_check_id")
    if payload.get("status") not in (
        "PASS",
        "WARN",
        "SKIP",
        "BLOCKED",
        "FAIL",
        "ERROR",
        "TIMEOUT",
        "CRASH",
    ):
        raise ValueError("invalid_status")
    return payload


def _read_frames(
    data: bytes,
    expected_nonce: str,
    allow_non_frame_lines: bool,
    expected_check_id: Optional[str] = None,
) -> FrameReadOutcome:
    if len(data) > MAX_RESULT_FILE_BYTES:
        return FrameReadOutcome(error_code="result_stream_too_large")
    if not data:
        return FrameReadOutcome(error_code="missing_result")
    lines = data.splitlines(keepends=True)
    frames: List[Dict[str, Any]] = []
    for line in lines:
        if not line.startswith(FRAME_PREFIX):
            if not allow_non_frame_lines:
                return FrameReadOutcome(
                    error_code="invalid_frame", frame_count=len(frames)
                )
            continue
        try:
            frames.append(_decode_frame(line, expected_nonce, expected_check_id))
        except ValueError as err:
            return FrameReadOutcome(error_code=str(err), frame_count=len(frames) + 1)
        if len(frames) > 1:
            return FrameReadOutcome(
                error_code="duplicate_frame", frame_count=len(frames)
            )
    if not frames:
        return FrameReadOutcome(error_code="missing_result")
    return FrameReadOutcome(envelope=frames[0], frame_count=1)


def read_result_file(
    path: str, expected_nonce: str, expected_check_id: Optional[str] = None
) -> FrameReadOutcome:
    """
    Read an append-only result file with bounded bytes.

    :param path: Result file path written by the worker.
    :type path: str
    :param expected_nonce: Nonce established by the parent start gate.
    :type expected_nonce: str
    :param expected_check_id: Optional check identifier to enforce, defaults to
        ``None``.
    :type expected_check_id: Optional[str], optional
    :return: Parsed envelope or a stable protocol error.
    :rtype: FrameReadOutcome

    Example::

        >>> read_result_file("missing", "0" * 32).error_code.startswith("result_file:")
        True
    """
    try:
        with open(path, "rb") as stream:
            data = stream.read(MAX_RESULT_FILE_BYTES + 1)
    except (OSError, IOError) as err:
        # Missing or inaccessible result files are protocol infrastructure failures.
        return FrameReadOutcome(error_code="result_file:{}".format(type(err).__name__))
    return _read_frames(
        data,
        expected_nonce,
        allow_non_frame_lines=False,
        expected_check_id=expected_check_id,
    )


def read_stdout_frames(
    data: bytes, expected_nonce: str, expected_check_id: Optional[str] = None
) -> FrameReadOutcome:
    """
    Read stdout protocol frames while ignoring non-frame diagnostics.

    :param data: Captured worker stdout bytes.
    :type data: bytes
    :param expected_nonce: Nonce established by the parent start gate.
    :type expected_nonce: str
    :param expected_check_id: Optional check identifier to enforce, defaults to
        ``None``.
    :type expected_check_id: Optional[str], optional
    :return: Parsed envelope or a stable protocol error.
    :rtype: FrameReadOutcome

    Example::

        >>> read_stdout_frames(b"noise\\n", "0" * 32).error_code
        'missing_result'
    """
    return _read_frames(
        data,
        expected_nonce,
        allow_non_frame_lines=True,
        expected_check_id=expected_check_id,
    )

"""Tests for the self-check worker wire protocol."""

import json

import pytest


@pytest.mark.unittest
def test_start_gate_is_exactly_36_bytes_with_real_lf():
    """The start gate has a fixed byte representation."""
    from pyfcstm._selfcheck.protocol import build_start_gate

    frame = build_start_gate("0" * 32)
    assert frame == b"GO " + (b"0" * 32) + b"\n"
    assert len(frame) == 36
    assert frame[-1:] == b"\x0a"


@pytest.mark.unittest
def test_nonce_rejects_trailing_newline_and_other_non_hex_bytes():
    """Nonce validation is a full-string wire check, not a prefix check."""
    from pyfcstm._selfcheck.protocol import build_start_gate

    for invalid in ("0" * 32 + "\n", "0" * 32 + "\r\n", "0" * 31 + "g"):
        with pytest.raises(ValueError, match="invalid self-check nonce"):
            build_start_gate(invalid)


@pytest.mark.unittest
def test_protocol_rejects_invalid_nonce_and_oversized_envelope():
    """Nonce and raw-frame limits are enforced before transport use."""
    from pyfcstm._selfcheck.protocol import MAX_ENVELOPE_BYTES
    from pyfcstm._selfcheck.protocol import build_start_gate
    from pyfcstm._selfcheck.protocol import encode_result_frame

    with pytest.raises(ValueError, match="invalid self-check nonce"):
        build_start_gate("bad")
    with pytest.raises(ValueError, match="envelope_too_large"):
        encode_result_frame(
            {
                "schema": "pyfcstm-selfcheck-worker/v1",
                "nonce": "0" * 32,
                "status": "PASS",
                "details": "x" * MAX_ENVELOPE_BYTES,
            }
        )


@pytest.mark.unittest
def test_append_only_result_file_counts_duplicate_frames(tmp_path):
    """Two durable frames are a duplicate, even when written before polling."""
    from pyfcstm._selfcheck.protocol import FRAME_PREFIX
    from pyfcstm._selfcheck.protocol import read_result_file

    nonce = "0" * 32
    payload = {
        "schema": "pyfcstm-selfcheck-worker/v1",
        "nonce": nonce,
        "status": "PASS",
    }
    frame = (
        FRAME_PREFIX
        + json.dumps(payload, sort_keys=True, separators=(",", ":")).encode("ascii")
        + b"\n"
    )
    path = tmp_path / "result.log"
    path.write_bytes(frame + frame)
    outcome = read_result_file(str(path), nonce)
    assert outcome.error_code == "duplicate_frame"


@pytest.mark.unittest
def test_frame_size_cap_applies_to_file_and_stdout(tmp_path):
    """The raw frame cap is enforced before unbounded JSON parsing."""
    from pyfcstm._selfcheck.protocol import FRAME_PREFIX
    from pyfcstm._selfcheck.protocol import MAX_ENVELOPE_BYTES
    from pyfcstm._selfcheck.protocol import read_result_file

    oversized = FRAME_PREFIX + (b"x" * MAX_ENVELOPE_BYTES) + b"\n"
    result_file = tmp_path / "result.log"
    result_file.write_bytes(oversized)
    outcome = read_result_file(str(result_file), "0" * 32)
    assert outcome.error_code == "envelope_too_large"


@pytest.mark.unittest
def test_valid_frame_uses_real_lf_and_nonce(tmp_path):
    """A valid frame is accepted only with the expected nonce and LF."""
    from pyfcstm._selfcheck.protocol import encode_result_frame
    from pyfcstm._selfcheck.protocol import read_result_file

    nonce = "1" * 32
    frame = encode_result_frame(
        {"schema": "pyfcstm-selfcheck-worker/v1", "nonce": nonce, "status": "PASS"}
    )
    assert frame.endswith(b"\x0a")
    path = tmp_path / "result.log"
    path.write_bytes(frame)
    outcome = read_result_file(str(path), nonce)
    assert outcome.envelope["status"] == "PASS"


@pytest.mark.unittest
def test_expected_check_id_is_part_of_frame_validation(tmp_path):
    """A same-nonce frame for another check cannot be credited to this check."""
    from pyfcstm._selfcheck.protocol import encode_result_frame
    from pyfcstm._selfcheck.protocol import read_result_file

    nonce = "4" * 32
    path = tmp_path / "result.log"
    path.write_bytes(
        encode_result_frame(
            {
                "schema": "pyfcstm-selfcheck-worker/v1",
                "check_id": "other.check",
                "nonce": nonce,
                "status": "PASS",
            }
        )
    )
    assert (
        read_result_file(
            str(path), nonce, expected_check_id="expected.check"
        ).error_code
        == "wrong_check_id"
    )


@pytest.mark.unittest
def test_result_file_rejects_non_frame_bytes_after_valid_frame(tmp_path):
    """The append-only file transport must not hide trailing corruption."""
    from pyfcstm._selfcheck.protocol import encode_result_frame
    from pyfcstm._selfcheck.protocol import read_result_file

    nonce = "2" * 32
    frame = encode_result_frame(
        {"schema": "pyfcstm-selfcheck-worker/v1", "nonce": nonce, "status": "PASS"}
    )
    path = tmp_path / "result.log"
    path.write_bytes(frame + b"corrupt\n")
    assert read_result_file(str(path), nonce).error_code == "invalid_frame"


@pytest.mark.unittest
def test_stdout_reader_allows_business_noise_around_frame():
    """Stdout transport keeps non-protocol diagnostics separate from the frame."""
    from pyfcstm._selfcheck.protocol import encode_result_frame
    from pyfcstm._selfcheck.protocol import read_stdout_frames

    nonce = "3" * 32
    frame = encode_result_frame(
        {"schema": "pyfcstm-selfcheck-worker/v1", "nonce": nonce, "status": "PASS"}
    )
    outcome = read_stdout_frames(b"noise\n" + frame + b"tail\n", nonce)
    assert outcome.envelope["status"] == "PASS"


@pytest.mark.unittest
def test_wrong_nonce_and_missing_lf_are_protocol_errors(tmp_path):
    """Nonce mismatch and a missing real LF never become PASS."""
    from pyfcstm._selfcheck.protocol import FRAME_PREFIX
    from pyfcstm._selfcheck.protocol import read_result_file

    path = tmp_path / "result.log"
    payload = {
        "schema": "pyfcstm-selfcheck-worker/v1",
        "nonce": "f" * 32,
        "status": "PASS",
    }
    raw = FRAME_PREFIX + json.dumps(
        payload, sort_keys=True, separators=(",", ":")
    ).encode("ascii")
    path.write_bytes(raw)
    assert read_result_file(str(path), "0" * 32).error_code == "missing_lf"
    path.write_bytes(raw + b"\n")
    assert read_result_file(str(path), "0" * 32).error_code == "wrong_nonce"


@pytest.mark.unittest
def test_protocol_rejects_invalid_json_prefix_schema_and_status(tmp_path):
    """Every malformed frame maps to a stable protocol error."""
    from pyfcstm._selfcheck.protocol import FRAME_PREFIX
    from pyfcstm._selfcheck.protocol import read_result_file

    path = tmp_path / "result.log"
    for raw, expected in (
        (b"bad\n", "invalid_frame"),
        (FRAME_PREFIX + b"{\xff}\n", "invalid_json"),
        (
            FRAME_PREFIX
            + b'{"schema":"wrong","nonce":"'
            + b"0" * 32
            + b'","status":"PASS"}\n',
            "schema_mismatch",
        ),
        (
            FRAME_PREFIX
            + b'{"schema":"pyfcstm-selfcheck-worker/v1","nonce":"'
            + b"0" * 32
            + b'","status":"NOPE"}\n',
            "invalid_status",
        ),
        (FRAME_PREFIX + b"[]\n", "invalid_envelope"),
    ):
        path.write_bytes(raw)
        assert read_result_file(str(path), "0" * 32).error_code == expected


@pytest.mark.unittest
def test_protocol_reader_reports_stream_and_file_errors(monkeypatch, tmp_path):
    """Unreadable files and overlarge streams remain explicit protocol errors."""
    from pyfcstm._selfcheck.protocol import MAX_RESULT_FILE_BYTES
    from pyfcstm._selfcheck.protocol import read_result_file
    from pyfcstm._selfcheck.protocol import read_stdout_frames

    path = tmp_path / "result.log"
    path.write_bytes(b"")
    monkeypatch.setattr(
        "builtins.open",
        lambda *args, **kwargs: (_ for _ in ()).throw(OSError("closed")),
    )
    assert read_result_file(str(path), "0" * 32).error_code.startswith("result_file:")
    assert (
        read_stdout_frames(b"x" * (MAX_RESULT_FILE_BYTES + 1), "0" * 32).error_code
        == "result_stream_too_large"
    )

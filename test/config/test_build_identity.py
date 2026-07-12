"""Tests for strict generated build identity data."""

import subprocess
from datetime import datetime, timezone

import pytest

from pyfcstm.config import _build_identity
from pyfcstm.config import _load_build_identity


def _identity():
    return _build_identity._identity_from_commit(
        "a" * 40,
        False,
        "main",
        datetime(2026, 7, 12, tzinfo=timezone.utc),
        "git",
    )


@pytest.mark.unittest
class TestBuildIdentityData:
    def test_round_trip_generated_literal_data(self, tmp_path):
        path = tmp_path / "build_info.py"
        identity = _identity()

        _build_identity.write_build_identity_file(path, identity)

        assert _build_identity.load_build_identity_file(path) == identity

    def test_rejects_code_without_executing_generated_file(self, tmp_path):
        path = tmp_path / "build_info.py"
        marker = tmp_path / "executed"
        path.write_text(
            "from pathlib import Path\nPath({!r}).write_text('executed')\n".format(
                str(marker)
            ),
            encoding="utf-8",
        )

        with pytest.raises(_build_identity.BuildInfoDataError):
            _build_identity.load_build_identity_file(path)

        assert not marker.exists()

    @pytest.mark.parametrize(
        "replacement",
        [
            "BUILD_DIRTY = 'False'",
            "BUILD_EXTRA = 'unexpected'",
            "BUILD_SOURCE = 'unknown'",
            "BUILD_COMMIT = 'abc",
        ],
    )
    def test_invalid_schema_or_literal_is_rejected(self, tmp_path, replacement):
        path = tmp_path / "build_info.py"
        _build_identity.write_build_identity_file(path, _identity())
        content = path.read_text(encoding="utf-8")
        if replacement.startswith("BUILD_DIRTY"):
            content = content.replace("BUILD_DIRTY = False", replacement)
        elif replacement.startswith("BUILD_EXTRA"):
            content += replacement + "\n"
        elif replacement.startswith("BUILD_SOURCE"):
            content = content.replace("BUILD_SOURCE = 'git'", replacement)
        else:
            content = content.replace("BUILD_COMMIT = '" + "a" * 40 + "'", replacement)
        path.write_text(content, encoding="utf-8")

        with pytest.raises(_build_identity.BuildInfoDataError):
            _build_identity.load_build_identity_file(path)

    def test_rejects_utf8_bom_and_null_bytes(self, tmp_path):
        path = tmp_path / "build_info.py"
        _build_identity.write_build_identity_file(path, _identity())
        payload = path.read_bytes()

        path.write_bytes(b"\xef\xbb\xbf" + payload)
        with pytest.raises(_build_identity.BuildInfoDataError):
            _build_identity.load_build_identity_file(path)

        path.write_bytes(payload + b"\x00")
        with pytest.raises(_build_identity.BuildInfoDataError):
            _build_identity.load_build_identity_file(path)

    def test_accepts_crlf_literal_data(self, tmp_path):
        path = tmp_path / "build_info.py"
        _build_identity.write_build_identity_file(path, _identity())
        path.write_bytes(path.read_bytes().replace(b"\n", b"\r\n"))

        assert _build_identity.load_build_identity_file(path).commit == "a" * 40

    def test_config_fallback_reports_invalid_data_without_importing_it(self, tmp_path):
        path = tmp_path / "build_info.py"
        path.write_text("raise RuntimeError('must not run')\n", encoding="utf-8")

        identity, error = _load_build_identity(path)

        assert identity.commit is None
        assert error is not None
        assert "BuildInfoDataError" in error

    def test_no_git_metadata_does_not_search_parent_directories(
        self, monkeypatch, tmp_path
    ):
        def _unexpected_git(*args, **kwargs):
            raise AssertionError(
                "a source tree without .git must not search its parent"
            )

        monkeypatch.setattr(_build_identity, "_run_git", _unexpected_git)

        assert (
            _build_identity._read_live_git_identity(
                tmp_path, datetime(2026, 7, 12, tzinfo=timezone.utc)
            )
            is None
        )

    def test_ci_override_is_available_without_git_metadata(self, tmp_path):
        path = tmp_path / "build_info.py"

        identity = _build_identity.ensure_build_identity(
            path,
            cwd=tmp_path,
            environment={
                "PYFCSTM_BUILD_COMMIT": "b" * 40,
                "PYFCSTM_BUILD_DIRTY": "true",
                "PYFCSTM_BUILD_REF": "release/0.5",
                "SOURCE_DATE_EPOCH": "1783814400",
            },
        )

        assert identity.source == "ci-override"
        assert identity.revision == "b" * 40 + "-dirty"
        assert identity.time_utc == "2026-07-12T00:00:00Z"
        assert _build_identity.load_build_identity_file(path) == identity

    @pytest.mark.parametrize(
        ("live_dirty", "override_dirty"),
        ((False, "true"), (True, "false")),
    )
    def test_ci_override_dirty_status_must_match_live_git(
        self, monkeypatch, tmp_path, live_dirty, override_dirty
    ):
        live_identity = _build_identity._identity_from_commit(
            "c" * 40,
            live_dirty,
            "main",
            datetime(2026, 7, 12, tzinfo=timezone.utc),
            "git",
        )
        monkeypatch.setattr(
            _build_identity, "_read_live_git_identity", lambda *args: live_identity
        )

        with pytest.raises(
            _build_identity.BuildInfoDataError,
            match="PYFCSTM_BUILD_DIRTY does not match live Git status",
        ):
            _build_identity.ensure_build_identity(
                tmp_path / "build_info.py",
                cwd=tmp_path,
                environment={
                    "PYFCSTM_BUILD_COMMIT": "c" * 40,
                    "PYFCSTM_BUILD_DIRTY": override_dirty,
                },
            )

    def test_carried_identity_is_relabelled_without_git_metadata(self, tmp_path):
        path = tmp_path / "build_info.py"
        _build_identity.write_build_identity_file(path, _identity())

        carried = _build_identity.ensure_build_identity(
            path, cwd=tmp_path, environment={}
        )

        assert carried.commit == "a" * 40
        assert carried.source == "sdist-carried"
        assert _build_identity.load_build_identity_file(path).source == "sdist-carried"

    @pytest.mark.parametrize("source_date_epoch", ("invalid", "-1"))
    def test_invalid_source_date_epoch_fails_closed(self, tmp_path, source_date_epoch):
        with pytest.raises(_build_identity.BuildInfoDataError):
            _build_identity.ensure_build_identity(
                tmp_path / "build_info.py",
                cwd=tmp_path,
                environment={"SOURCE_DATE_EPOCH": source_date_epoch},
            )

    def test_replace_failure_keeps_the_previous_identity_file(
        self, monkeypatch, tmp_path
    ):
        path = tmp_path / "build_info.py"
        _build_identity.write_build_identity_file(path, _identity())
        expected = path.read_bytes()

        def _replace_failure(*args, **kwargs):
            raise PermissionError("destination is open")

        monkeypatch.setattr(_build_identity.os, "replace", _replace_failure)

        with pytest.raises(PermissionError):
            _build_identity.write_build_identity_file(path, _identity())

        assert path.read_bytes() == expected
        assert not list(tmp_path.glob(".build_info.*.tmp"))

    def test_old_git_object_format_fallback_uses_commit_length(self, monkeypatch):
        responses = {
            ("rev-parse", "--verify", "HEAD^{commit}"): subprocess.CompletedProcess(
                [], 0, "a" * 40 + "\n", ""
            ),
            ("rev-parse", "--show-object-format"): subprocess.CompletedProcess(
                [], 129, "", "unknown option"
            ),
            (
                "status",
                "--porcelain",
                "--untracked-files=normal",
            ): subprocess.CompletedProcess([], 0, "", ""),
            ("symbolic-ref", "--quiet", "--short", "HEAD"): subprocess.CompletedProcess(
                [], 0, "main\n", ""
            ),
        }

        def _run_git(arguments, cwd):
            return responses[tuple(arguments)]

        monkeypatch.setattr(_build_identity, "_run_git", _run_git)

        identity = _build_identity._read_live_git_identity(
            _build_identity.Path.cwd(), datetime(2026, 7, 12, tzinfo=timezone.utc)
        )

        assert identity is not None
        assert identity.algorithm == "sha1"
        assert identity.commit == "a" * 40

    def test_windows_writer_skips_directory_fsync(self, monkeypatch, tmp_path):
        path = tmp_path / "build_info.py"
        original_open = _build_identity.os.open

        def _reject_directory_open(path_value, flags, *args, **kwargs):
            if flags == _build_identity.os.O_RDONLY:
                raise AssertionError("directory fsync must not run on Windows")
            return original_open(path_value, flags, *args, **kwargs)

        monkeypatch.setattr(_build_identity, "_is_windows", lambda: True)
        monkeypatch.setattr(_build_identity.os, "open", _reject_directory_open)

        _build_identity.write_build_identity_file(path, _identity())

        assert _build_identity.load_build_identity_file(path).commit == "a" * 40

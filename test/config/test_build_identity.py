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

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("BUILD_COMMIT_ALGORITHM", "md5", "BUILD_COMMIT_ALGORITHM"),
            ("BUILD_SOURCE", "manual", "BUILD_SOURCE"),
            ("BUILD_COMMIT_SHORT", 12, "BUILD_COMMIT_SHORT"),
            ("BUILD_DIRTY", 0, "BUILD_DIRTY"),
        ],
    )
    def test_invalid_identity_field_types_and_values_are_rejected(
        self, field, value, message
    ):
        values = _identity().values()
        values[field] = value

        with pytest.raises(_build_identity.BuildInfoDataError, match=message):
            _build_identity._validate_identity_values(values)

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("BUILD_COMMIT_ALGORITHM", "sha1", "requires BUILD_COMMIT"),
            ("BUILD_COMMIT_SHORT", "a" * 12, "required when identity fields"),
            ("BUILD_SOURCE", "git", "requires BUILD_COMMIT"),
        ],
    )
    def test_empty_identity_rejects_dependent_values(self, field, value, message):
        values = _build_identity.BuildIdentity.unknown().values()
        values[field] = value

        with pytest.raises(_build_identity.BuildInfoDataError, match=message):
            _build_identity._validate_identity_values(values)

    @pytest.mark.parametrize(
        ("field", "value", "message"),
        [
            ("BUILD_DIRTY", None, "BUILD_DIRTY is required"),
            ("BUILD_SOURCE", "unknown", "BUILD_SOURCE must identify"),
            ("BUILD_COMMIT_SHORT", "b" * 12, "BUILD_COMMIT_SHORT"),
            ("BUILD_REVISION", "a" * 40 + "-dirty", "BUILD_REVISION does not match"),
            ("BUILD_REVISION_SHORT", "a" * 12 + "-dirty", "BUILD_REVISION_SHORT"),
            ("BUILD_TIME_UTC", "2026-07-12", "BUILD_TIME_UTC"),
            ("BUILD_TIME_UTC", "2026-02-31T00:00:00Z", "not a valid UTC timestamp"),
            ("BUILD_REF", "main\nother", "BUILD_REF must not contain"),
        ],
    )
    def test_complete_identity_rejects_inconsistent_values(self, field, value, message):
        values = _identity().values()
        values[field] = value

        with pytest.raises(_build_identity.BuildInfoDataError, match=message):
            _build_identity._validate_identity_values(values)

    def test_rejects_missing_identity_fields(self):
        values = _identity().values()
        del values["BUILD_REF"]

        with pytest.raises(_build_identity.BuildInfoDataError, match="missing"):
            _build_identity._validate_identity_values(values)

    def test_unknown_identity_is_a_valid_empty_state(self):
        assert (
            _build_identity._validate_identity_values(
                _build_identity.BuildIdentity.unknown().values()
            )
            == _build_identity.BuildIdentity.unknown()
        )

    def test_rejects_invalid_commit_algorithm_duplicate_and_non_literal(self, tmp_path):
        values = _identity().values()
        values["BUILD_COMMIT"] = "z" * 40
        with pytest.raises(_build_identity.BuildInfoDataError, match="object ID"):
            _build_identity._validate_identity_values(values)

        values = _identity().values()
        values["BUILD_COMMIT_ALGORITHM"] = "sha256"
        with pytest.raises(_build_identity.BuildInfoDataError, match="must be sha1"):
            _build_identity._validate_identity_values(values)

        path = tmp_path / "build_info.py"
        _build_identity.write_build_identity_file(path, _identity())
        path.write_text(
            path.read_text(encoding="utf-8") + "BUILD_REF = None\n",
            encoding="utf-8",
        )
        with pytest.raises(_build_identity.BuildInfoDataError, match="duplicate"):
            _build_identity.load_build_identity_file(path)

        path.write_text("BUILD_COMMIT = object()\n", encoding="utf-8")
        with pytest.raises(_build_identity.BuildInfoDataError, match="not a literal"):
            _build_identity.load_build_identity_file(path)

    def test_rejects_invalid_utf8_identity_data(self, tmp_path):
        path = tmp_path / "build_info.py"
        path.write_bytes(b"\xff")

        with pytest.raises(_build_identity.BuildInfoDataError, match="valid UTF-8"):
            _build_identity.load_build_identity_file(path)

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

    @pytest.mark.parametrize(
        ("error", "expected"),
        [
            (OSError(_build_identity.errno.ENOENT, "git is absent"), None),
            (OSError(_build_identity.errno.EACCES, "git is inaccessible"), OSError),
        ],
    )
    def test_git_executable_failures_have_precise_fallback_behavior(
        self, monkeypatch, tmp_path, error, expected
    ):
        (tmp_path / ".git").mkdir()

        def _raise_git(*args, **kwargs):
            raise error

        monkeypatch.setattr(_build_identity, "_run_git", _raise_git)
        if expected is None:
            assert (
                _build_identity._read_live_git_identity(
                    tmp_path, datetime(2026, 7, 12, tzinfo=timezone.utc)
                )
                is None
            )
        else:
            with pytest.raises(expected):
                _build_identity._read_live_git_identity(
                    tmp_path, datetime(2026, 7, 12, tzinfo=timezone.utc)
                )

    def test_git_failure_and_invalid_identity_are_rejected(self, monkeypatch, tmp_path):
        (tmp_path / ".git").mkdir()
        monkeypatch.setattr(
            _build_identity,
            "_run_git",
            lambda *args: subprocess.CompletedProcess([], 1, "", "missing HEAD"),
        )
        assert (
            _build_identity._read_live_git_identity(
                tmp_path, datetime(2026, 7, 12, tzinfo=timezone.utc)
            )
            is None
        )

        monkeypatch.setattr(
            _build_identity,
            "_run_git",
            lambda *args: subprocess.CompletedProcess([], 0, "not-a-commit\n", ""),
        )
        with pytest.raises(_build_identity.BuildInfoDataError, match="invalid commit"):
            _build_identity._read_live_git_identity(
                tmp_path, datetime(2026, 7, 12, tzinfo=timezone.utc)
            )

    def test_git_runner_and_required_git_value_failure(self, tmp_path):
        result = _build_identity._run_git(("--version",), tmp_path)
        assert result.returncode == 0

        with pytest.raises(
            _build_identity.BuildInfoDataError, match="git status failed"
        ):
            _build_identity._git_value(("status",), tmp_path)

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

    def test_ci_override_commit_must_match_live_git(self, monkeypatch, tmp_path):
        live_identity = _identity()
        monkeypatch.setattr(
            _build_identity, "_read_live_git_identity", lambda *args: live_identity
        )

        with pytest.raises(
            _build_identity.BuildInfoDataError,
            match="PYFCSTM_BUILD_COMMIT does not match live Git HEAD",
        ):
            _build_identity.ensure_build_identity(
                tmp_path / "build_info.py",
                cwd=tmp_path,
                environment={"PYFCSTM_BUILD_COMMIT": "b" * 40},
            )

    def test_live_identity_is_written_without_a_ci_override(
        self, monkeypatch, tmp_path
    ):
        live_identity = _identity()
        monkeypatch.setattr(
            _build_identity, "_read_live_git_identity", lambda *args: live_identity
        )

        resolved = _build_identity.ensure_build_identity(
            tmp_path / "build_info.py", cwd=tmp_path, environment={}
        )

        assert resolved == live_identity

    @pytest.mark.parametrize(
        ("value", "expected"),
        [("1", True), (" true ", True), ("0", False), ("FALSE", False)],
    )
    def test_ci_dirty_parser_accepts_documented_values(self, value, expected):
        assert _build_identity._parse_ci_dirty(value) is expected

    def test_ci_dirty_parser_rejects_unknown_values(self):
        with pytest.raises(_build_identity.BuildInfoDataError, match="BUILD_DIRTY"):
            _build_identity._parse_ci_dirty("yes")

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

    def test_out_of_range_source_date_epoch_fails_closed(self, tmp_path):
        with pytest.raises(
            _build_identity.BuildInfoDataError, match="supported UTC range"
        ):
            _build_identity.ensure_build_identity(
                tmp_path / "build_info.py",
                cwd=tmp_path,
                environment={"SOURCE_DATE_EPOCH": "999999999999999999999"},
            )

    def test_requirements_fail_closed_without_any_identity(self, tmp_path):
        with pytest.raises(
            _build_identity.BuildInfoDataError, match="commit is required"
        ):
            _build_identity.ensure_build_identity(
                tmp_path / "build_info.py",
                cwd=tmp_path,
                environment={},
                require_commit=True,
            )
        with pytest.raises(_build_identity.BuildInfoDataError, match="clean build"):
            _build_identity.ensure_build_identity(
                tmp_path / "build_info.py",
                cwd=tmp_path,
                environment={},
                require_clean=True,
            )

    def test_invalid_commit_and_git_format_mismatch_fail_closed(
        self, monkeypatch, tmp_path
    ):
        with pytest.raises(_build_identity.BuildInfoDataError, match="build commit"):
            _build_identity._identity_from_commit(
                "ABC",
                False,
                None,
                datetime(2026, 7, 12, tzinfo=timezone.utc),
                "ci-override",
            )

        (tmp_path / ".git").mkdir()
        responses = {
            ("rev-parse", "--verify", "HEAD^{commit}"): subprocess.CompletedProcess(
                [], 0, "a" * 40 + "\n", ""
            ),
            ("rev-parse", "--show-object-format"): subprocess.CompletedProcess(
                [], 0, "sha256\n", ""
            ),
        }
        monkeypatch.setattr(
            _build_identity,
            "_run_git",
            lambda arguments, cwd: responses[tuple(arguments)],
        )
        with pytest.raises(_build_identity.BuildInfoDataError, match="object format"):
            _build_identity._read_live_git_identity(
                tmp_path, datetime(2026, 7, 12, tzinfo=timezone.utc)
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

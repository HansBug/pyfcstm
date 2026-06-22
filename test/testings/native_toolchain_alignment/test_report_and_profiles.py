import json

import pytest

from test.testings.native_toolchain_alignment.profiles import (
    PROFILE_ENV_VAR,
    RUN_ENV_VAR,
    ProfileSelectionError,
    ToolchainProfile,
    get_profile,
    iter_profiles,
    missing_required_tools,
    native_toolchain_enabled,
    resolve_selected_profile,
)
from test.testings.native_toolchain_alignment.report import (
    NativeCommandRecord,
    NativeToolchainResult,
    validate_command_data,
    validate_observation_data,
    validate_result_data,
)


@pytest.mark.unittest
def test_profiles_freeze_initial_public_profile_names():
    assert [profile.name for profile in iter_profiles()] == [
        "linux-gcc-o2",
        "linux-clang-o2",
    ]
    assert get_profile("linux-gcc-o2").build_mode == "cmake-run"


@pytest.mark.unittest
def test_profile_selection_fails_when_enabled_without_profile(monkeypatch):
    monkeypatch.setenv(RUN_ENV_VAR, "1")
    monkeypatch.delenv(PROFILE_ENV_VAR, raising=False)

    with pytest.raises(ProfileSelectionError, match=PROFILE_ENV_VAR):
        resolve_selected_profile()


@pytest.mark.unittest
def test_profile_selection_fails_for_unknown_profile(monkeypatch):
    monkeypatch.setenv(RUN_ENV_VAR, "1")
    monkeypatch.setenv(PROFILE_ENV_VAR, "unknown-profile")

    with pytest.raises(ProfileSelectionError, match="unknown native toolchain profile"):
        resolve_selected_profile()


@pytest.mark.unittest
def test_missing_required_tools_reports_public_tool_names():
    profile = ToolchainProfile(
        "demo",
        "cmake-run",
        (),
        (),
        (),
        (),
        required_binaries=("definitely-not-pyfcstm-tool",),
    )

    assert missing_required_tools(profile) == ["definitely-not-pyfcstm-tool"]


@pytest.mark.unittest
def test_report_schema_rejects_missing_fields_and_bad_types(tmp_path):
    command = NativeCommandRecord("version", ["cc", "--version"], str(tmp_path))
    result = NativeToolchainResult(
        "case",
        "c",
        "linux-gcc-o2",
        "cmake-run",
        "gcc",
        "gcc 1",
        "gcc",
        "gcc 1",
        "-O2",
        "passed",
        "passed",
        "ok",
        commands=[command],
    ).to_dict()

    validate_command_data(command.to_dict())
    validate_result_data(result)

    bad_result = dict(result)
    bad_result.pop("schema_version")
    with pytest.raises(ValueError, match="missing fields"):
        validate_result_data(bad_result)

    bad_result = dict(result)
    bad_result["duration_seconds"] = True
    with pytest.raises(ValueError, match="duration_seconds"):
        validate_result_data(bad_result)

    bad_result = dict(result)
    bad_result["artifact_paths"] = ["generated", 1]
    with pytest.raises(ValueError, match="artifact_paths"):
        validate_result_data(bad_result)

    bad_command = command.to_dict()
    bad_command["argv"] = "cc --version"
    with pytest.raises(ValueError, match="argv"):
        validate_command_data(bad_command)

    bad_command = command.to_dict()
    bad_command["duration_seconds"] = False
    with pytest.raises(ValueError, match="duration_seconds"):
        validate_command_data(bad_command)


@pytest.mark.unittest
def test_observation_schema_requires_version_and_public_fields():
    data = {
        "schema_version": "1",
        "case_id": "demo",
        "template_name": "c",
        "phase": "step",
        "step_index": 0,
        "cycle_index": 0,
        "events": [],
        "current_state": "Root.A",
        "is_ended": False,
        "vars": {},
        "handler_calls": [],
        "last_error": None,
        "api_return": 1,
    }
    validate_observation_data(json.loads(json.dumps(data)))

    data["schema_version"] = "2"
    with pytest.raises(ValueError, match="schema_version"):
        validate_observation_data(data)

    data["schema_version"] = "1"
    data["events"] = ["Root.A.Go", 1]
    with pytest.raises(ValueError, match="events"):
        validate_observation_data(data)

    data["events"] = []
    data["phase"] = "unknown"
    with pytest.raises(ValueError, match="phase"):
        validate_observation_data(data)


@pytest.mark.unittest
def test_native_toolchain_enabled_accepts_option_or_environment(monkeypatch):
    class Config:
        def __init__(self, enabled):
            self.enabled = enabled

        def getoption(self, name, default=False):
            assert name == "--run-native-toolchain"
            return self.enabled

    monkeypatch.delenv(RUN_ENV_VAR, raising=False)
    assert native_toolchain_enabled(Config(False)) is False
    assert native_toolchain_enabled(Config(True)) is True

    monkeypatch.setenv(RUN_ENV_VAR, "1")
    assert native_toolchain_enabled(Config(False)) is True


@pytest.mark.unittest
def test_result_schema_rejects_unknown_classification(tmp_path):
    result = NativeToolchainResult(
        "case",
        "c",
        "linux-gcc-o2",
        "cmake-run",
        "gcc",
        "gcc 1",
        "gcc",
        "gcc 1",
        "-O2",
        "failed",
        "unexpected",
        "bad",
    ).to_dict()

    with pytest.raises(ValueError, match="classification"):
        validate_result_data(result)

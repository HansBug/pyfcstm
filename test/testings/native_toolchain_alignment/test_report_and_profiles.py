import json
from pathlib import Path

import pytest

from test.testings.native_toolchain_alignment.profiles import (
    PROFILE_ENV_VAR,
    RUN_ENV_VAR,
    ProfileSelectionError,
    ToolchainProfile,
    get_profile,
    iter_all_profiles,
    iter_manual_profiles,
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
from test.testings.native_toolchain_alignment.runner import (
    _analysis_argv,
    _analysis_targets,
    _case_artifact_dir,
    _tool_stem,
)


@pytest.mark.unittest
def test_profiles_cover_public_matrix_and_manual_entries():
    profile_names = [profile.name for profile in iter_profiles()]

    assert profile_names[:4] == [
        "linux-gcc-o0",
        "linux-gcc-o2",
        "linux-gcc-o3",
        "linux-gcc-os",
    ]
    for name in [
        "linux-clang-o0",
        "linux-clang-o2",
        "linux-gcc-m32-o2",
        "linux-aarch64-gcc-o2",
        "arm-none-eabi-gcc-o2",
        "macos-appleclang-o2",
        "windows-mingw-o2",
        "windows-msvc-o2",
        "windows-clangcl-o2",
        "linux-clang-asan-ubsan",
        "linux-cppcheck",
        "linux-clang-tidy",
    ]:
        assert name in profile_names
    assert get_profile("linux-gcc-o2").build_mode == "cmake-run"
    assert get_profile("arm-none-eabi-gcc-o2").build_mode == "compile-only"
    assert get_profile("linux-cppcheck").build_mode == "analyze-only"
    assert get_profile("linux-cppcheck").report_only is True
    assert "-DPYFCSTM_NATIVE_C_STANDARD=11" in get_profile("windows-msvc-o2").cmake_args
    assert all(profile.public_required for profile in iter_profiles())
    assert all(not profile.public_required for profile in iter_manual_profiles())
    assert get_profile("manual-armclang-compile") in iter_all_profiles()


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


@pytest.mark.unittest
def test_report_schema_accepts_compile_and_analysis_classifications():
    command = NativeCommandRecord("analyze", ["cppcheck", "machine.c"], "/tmp")
    result = NativeToolchainResult(
        "case",
        "c",
        "linux-cppcheck",
        "analyze-only",
        None,
        None,
        "cppcheck",
        "cppcheck 2",
        None,
        "passed",
        "analysis_report_only",
        "report",
        commands=[command],
        analysis_ruleset="demo",
        analysis_report_path="analysis-report.txt",
        report_only=True,
    ).to_dict()

    validate_result_data(result)

    result["classification"] = "compile_failure"
    result["status"] = "failed"
    validate_result_data(result)


@pytest.mark.unittest
def test_report_schema_accepts_compile_stage_variants():
    for stage in ["compile-machine-c", "compile-harness-c", "compile-header-cxx"]:
        validate_command_data(
            NativeCommandRecord(stage, ["cc", "-c", "machine.c"], "/tmp").to_dict()
        )


@pytest.mark.unittest
def test_case_artifact_directory_normalizes_relative_root(tmp_path, monkeypatch):
    monkeypatch.chdir(tmp_path)

    artifact_dir = _case_artifact_dir("artifacts", "c", "linux-gcc-o2", "case")

    assert artifact_dir == str(tmp_path / "artifacts" / "c" / "linux-gcc-o2" / "case")


@pytest.mark.unittest
def test_analysis_targets_cover_generated_and_harness_sources(tmp_path):
    artifact_dir = tmp_path / "artifact"
    for relative_path in [
        "generated/machine.c",
        "generated/machine.h",
        "generated/future_runtime.cpp",
        "harness/machine.c",
        "harness/machine.h",
        "harness/harness.c",
        "harness/readme.txt",
    ]:
        path = artifact_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("/* sentinel */\n", encoding="utf-8")

    targets = {
        path.relative_to(artifact_dir).as_posix()
        for path in map(Path, _analysis_targets(str(artifact_dir)))
    }

    assert targets == {
        "generated/machine.c",
        "generated/machine.h",
        "harness/harness.c",
        "harness/machine.c",
        "harness/machine.h",
    }


@pytest.mark.unittest
def test_analysis_argv_inserts_targets_before_compile_separator(tmp_path):
    artifact_dir = tmp_path / "artifact"
    for relative_path in [
        "generated/machine.c",
        "generated/machine.h",
        "harness/machine.c",
        "harness/harness.c",
    ]:
        path = artifact_dir / relative_path
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("/* sentinel */\n", encoding="utf-8")
    profile = get_profile("linux-clang-tidy")

    argv = _analysis_argv(profile, str(artifact_dir))

    separator = argv.index("--")
    assert str(artifact_dir / "generated" / "machine.c") in argv[:separator]
    assert str(artifact_dir / "generated" / "machine.h") in argv[:separator]
    assert str(artifact_dir / "harness" / "machine.c") in argv[:separator]
    assert str(artifact_dir / "harness" / "harness.c") in argv[:separator]
    assert "-std=c99" in argv[separator + 1 :]


@pytest.mark.unittest
def test_tool_stem_accepts_windows_executable_suffixes():
    assert _tool_stem(("cl",)) == "cl"
    assert _tool_stem(("cl.exe",)) == "cl"
    assert _tool_stem(("C:/VS/VC/Tools/MSVC/bin/clang-cl.exe",)) == "clang-cl"


@pytest.mark.unittest
def test_compile_only_profile_records_non_running_contract():
    profile = get_profile("arm-none-eabi-gcc-o2")

    assert profile.build_mode == "compile-only"
    assert profile.run_prefix == ()
    assert profile.compiler == "arm-none-eabi-gcc"

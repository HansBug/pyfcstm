import datetime as _dt
import os
import signal
import subprocess

import pytest

from test.testings import native_semantic_alignment as native_alignment
from test.testings.native_semantic_alignment import (
    _GeneratedNativeAlignmentRuntime,
    GENERATED_C_ALIGNMENT,
    NativeAlignmentMatrixError,
    load_native_capability_matrix,
    native_capability_by_runner_case,
)
from test.testings.simulate_semantics import iter_semantic_cases


@pytest.mark.unittest
def test_native_capability_matrix_has_no_expected_failures_after_alignment():
    entries = load_native_capability_matrix()
    matrix = native_capability_by_runner_case(entries)
    case_ids = {case.id for case in iter_semantic_cases()}

    assert entries == ()
    assert matrix == {}
    assert "aspect_context_reports_active_leaf" in case_ids
    assert "failed_initial_cycle_skips_abstract_handler_callbacks" in case_ids


@pytest.mark.unittest
def test_native_capability_matrix_uses_stable_schema_fields():
    entries = load_native_capability_matrix()
    assert all(hasattr(entry, "since") for entry in entries)
    assert not any(hasattr(entry, "since_pr") for entry in entries)
    assert all(_dt.date.fromisoformat(entry.since) for entry in entries)


@pytest.mark.unittest
def test_native_capability_matrix_rejects_missing_tracking(tmp_path):
    matrix_file = tmp_path / "runner_capabilities.yaml"
    matrix_file.write_text(
        "version: 1\n"
        "known_failures:\n"
        "  - runner: generated_c_alignment\n"
        "    case: design_basic_simple_transition\n"
        "    classification: state_or_ended_mismatch\n"
        "    observation: state_or_ended\n"
        "    support: expected_failure\n"
        "    skip_reason: known gap\n"
        "    since: '2026-06-17'\n",
        encoding="utf-8",
    )

    with pytest.raises(NativeAlignmentMatrixError, match="missing fields"):
        load_native_capability_matrix(str(matrix_file))


@pytest.mark.unittest
def test_native_capability_matrix_file_is_single_fact_source():
    path = os.path.join(
        "test", "fixtures", "simulate_semantics", "runner_capabilities.yaml"
    )
    assert os.path.isfile(path)


@pytest.mark.unittest
def test_native_subprocess_classifies_sigfpe_as_unexpected_after_repair(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-signal.SIGFPE,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(native_alignment.subprocess, "run", fake_run)

    result = native_alignment.run_native_alignment_case_subprocess(
        GENERATED_C_ALIGNMENT, "expression_failure_raises_expression_error"
    )

    assert result.status == "unexpected_failure"
    assert result.classification == "sigfpe"
    assert result.expected_classification is None
    assert result.support is None
    assert result.returncode == -signal.SIGFPE


@pytest.mark.unittest
def test_native_subprocess_reports_non_sigfpe_signal_as_unexpected(monkeypatch):
    sigsegv = getattr(signal, "SIGSEGV", 11)

    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=-sigsegv,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(native_alignment.subprocess, "run", fake_run)

    result = native_alignment.run_native_alignment_case_subprocess(
        GENERATED_C_ALIGNMENT, "expression_failure_raises_expression_error"
    )

    assert result.status == "unexpected_failure"
    assert result.classification == "native_crash"
    assert result.expected_classification is None
    assert result.returncode == -sigsegv


@pytest.mark.unittest
def test_native_subprocess_reports_windows_arithmetic_crash_as_unexpected(
    monkeypatch,
):
    windows_arithmetic_returncodes = [
        0xC000008E,
        0xC0000090,
        0xC0000094,
        0xC0000095,
    ]

    for returncode in windows_arithmetic_returncodes:

        def fake_run(cmd, **kwargs):
            return subprocess.CompletedProcess(
                args=cmd,
                returncode=returncode,
                stdout="",
                stderr="",
            )

        monkeypatch.setattr(native_alignment.subprocess, "run", fake_run)

        result = native_alignment.run_native_alignment_case_subprocess(
            GENERATED_C_ALIGNMENT, "expression_failure_raises_expression_error"
        )

        assert result.status == "unexpected_failure"
        assert result.classification == "sigfpe"
        assert result.expected_classification is None
        assert result.returncode == returncode


@pytest.mark.unittest
def test_native_subprocess_reports_windows_non_arithmetic_crash_as_unexpected(
    monkeypatch,
):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=0xC0000005,
            stdout="",
            stderr="",
        )

    monkeypatch.setattr(native_alignment.subprocess, "run", fake_run)

    result = native_alignment.run_native_alignment_case_subprocess(
        GENERATED_C_ALIGNMENT, "expression_failure_raises_expression_error"
    )

    assert result.status == "unexpected_failure"
    assert result.classification == "native_crash"
    assert result.expected_classification is None
    assert result.returncode == 0xC0000005


@pytest.mark.unittest
def test_native_subprocess_reports_worker_failure_as_unexpected(monkeypatch):
    def fake_run(cmd, **kwargs):
        return subprocess.CompletedProcess(
            args=cmd,
            returncode=1,
            stdout="",
            stderr="Traceback (most recent call last):\nNameError: harness_bug\n",
        )

    monkeypatch.setattr(native_alignment.subprocess, "run", fake_run)

    result = native_alignment.run_native_alignment_case_subprocess(
        GENERATED_C_ALIGNMENT, "aspect_context_reports_active_leaf"
    )

    assert result.status == "unexpected_failure"
    assert result.classification == "worker_failure"
    assert result.expected_classification is None
    assert result.returncode == 1


@pytest.mark.unittest
def test_alignment_runtime_large_integer_filter_retains_other_exact_values():
    class _StubSimulation:
        is_ended = False
        vars = {"big": 10**100, "fraction": 1.25}

        class _State:
            path = ("Root", "A")

        current_state = _State()

    class _StubNative:
        is_ended = False
        vars = {"big": 0, "fraction": 1.5}
        current_state_path = ("Root", "A")

    runtime = _GeneratedNativeAlignmentRuntime(
        _StubSimulation(), _StubNative(), "state Root { state A; [*] -> A; }"
    )

    with pytest.raises(AssertionError, match="vars mismatch"):
        runtime._assert_aligned("probe")

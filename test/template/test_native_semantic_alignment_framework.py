import signal
import subprocess

import pytest

from test.testings import native_semantic_alignment as native_alignment
from test.testings.native_semantic_alignment import (
    _GeneratedNativeAlignmentRuntime,
    GENERATED_C_ALIGNMENT,
)


@pytest.mark.unittest
def test_native_alignment_hard_failure_results_have_no_legacy_metadata():
    result = native_alignment.NativeAlignmentResult(
        GENERATED_C_ALIGNMENT,
        "design_basic_simple_transition",
        "failed",
        "state_or_ended_mismatch",
        "state mismatch",
    )

    hard_failure = native_alignment._hard_failure_result(result)

    assert hard_failure.status == "unexpected_failure"
    assert hard_failure.classification == "state_or_ended_mismatch"
    assert set(hard_failure.to_dict()) == {
        "case_id",
        "classification",
        "message",
        "returncode",
        "runner",
        "status",
    }


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

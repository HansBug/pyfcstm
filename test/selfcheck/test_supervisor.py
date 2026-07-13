"""Tests for supervisor orchestration and stable exit codes."""

import json

import pytest


@pytest.mark.unittest
def test_supervisor_default_profile_returns_json_snapshot(capsys):
    """The default public self-check completes without importing Click first."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    code = run_supervisor(("--format", "json"))
    captured = capsys.readouterr()
    assert code == 0
    payload = json.loads(captured.out)
    assert payload["schema"] == "pyfcstm-selfcheck/v1"
    assert payload["counts"]["PASS"] == 1


@pytest.mark.unittest
def test_fail_on_warn_changes_exit_only(monkeypatch, capsys):
    """The warning result is preserved while the policy changes the exit code."""
    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "warn")
    from pyfcstm._selfcheck.supervisor import run_supervisor

    assert run_supervisor(("--format", "json")) == 0
    capsys.readouterr()
    assert run_supervisor(("--format", "json", "--fail-on-warn")) == 1
    assert json.loads(capsys.readouterr().out)["counts"]["WARN"] == 1


@pytest.mark.unittest
def test_supervisor_argument_and_report_failures_are_stable(tmp_path, capsys):
    """Bad arguments return 2 and report failures become synthetic ERROR."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    assert run_supervisor(("--network",)) == 2
    capsys.readouterr()
    report_path = tmp_path / "missing" / "report.json"
    assert run_supervisor(("--format", "json", "--report", str(report_path))) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["ERROR"] == 1


@pytest.mark.unittest
def test_supervisor_ctrl_c_returns_partial_summary(monkeypatch, capsys):
    """A first supervisor KeyboardInterrupt maps to 130."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert run_supervisor(("--format", "json")) == 130
    assert "interrupted" in capsys.readouterr().out


@pytest.mark.unittest
def test_supervisor_normalizes_legacy_warning_marker(monkeypatch, capsys):
    """A worker warning marker is normalized before ledger commit."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda *args, **kwargs: CheckResult(
            "artifact.self_dispatch",
            "PASS",
            True,
            summary="__SELFCHECK_WARN__:legacy warning",
        ),
    )
    assert run_supervisor(("--format", "json")) == 0
    assert json.loads(capsys.readouterr().out)["counts"] == {"WARN": 1}


@pytest.mark.unittest
def test_supervisor_infrastructure_failure_returns_three(monkeypatch, capsys):
    """Registry or ledger failures use the infrastructure exit code."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (_ for _ in ()).throw(RuntimeError("registry broken")),
    )
    assert run_supervisor(("--format", "json")) == 3
    assert "infrastructure error" in capsys.readouterr().err

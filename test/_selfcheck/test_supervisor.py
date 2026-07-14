"""Tests for supervisor orchestration and stable exit codes."""

import json

import pytest


@pytest.mark.unittest
def test_supervisor_default_profile_returns_json_snapshot(capsys):
    """The default public self-check completes without importing Click first."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    code = run_supervisor(("--format", "json"))
    captured = capsys.readouterr()
    payload = json.loads(captured.out)
    artifact = next(
        item
        for item in payload["checks"]
        if item["check_id"] == "artifact.self_dispatch"
    )
    if artifact.get("reason") == "isolation_unavailable":
        assert code == 1
        assert payload["counts"]["ERROR"] == 1
        return
    assert code == 0
    assert payload["schema"] == "pyfcstm-selfcheck/v1"
    assert payload["counts"]["PASS"] == 2


@pytest.mark.unittest
def test_fail_on_warn_changes_exit_only(monkeypatch, capsys):
    """The warning result is preserved while the policy changes the exit code."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda spec, timeout: CheckResult(
            spec.check_id,
            "WARN",
            spec.required,
            summary="injected warning",
        ),
    )
    assert run_supervisor(("--format", "json")) == 0
    capsys.readouterr()
    assert run_supervisor(("--format", "json", "--fail-on-warn")) == 1
    assert json.loads(capsys.readouterr().out)["counts"]["WARN"] == 1


@pytest.mark.unittest
def test_supervisor_runs_local_checks_without_spawning_worker(monkeypatch, capsys):
    """A local check uses the registry callback in the supervisor process."""
    from pyfcstm._selfcheck.model import CheckResult, CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (CheckSpec("local.demo", "local_demo", execution="local"),),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.get_worker",
        lambda key: (lambda: "local callback") if key == "local_demo" else None,
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda *args, **kwargs: CheckResult("local.demo", "ERROR", True),
    )
    assert run_supervisor(("--format", "json")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"][0]["summary"] == "local callback"


@pytest.mark.unittest
def test_supervisor_argument_and_report_failures_are_stable(
    tmp_path, capsys, monkeypatch
):
    """Bad arguments return 2 and report failures become synthetic ERROR."""
    from pyfcstm._selfcheck.supervisor import run_supervisor
    from pyfcstm._selfcheck.model import CheckResult

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda spec, timeout: CheckResult(
            spec.check_id, "PASS", spec.required, summary="injected pass"
        ),
    )

    assert run_supervisor(("--network",)) == 2
    capsys.readouterr()
    report_path = tmp_path / "missing" / "report.json"
    assert run_supervisor(("--format", "json", "--report", str(report_path))) == 1
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"]["ERROR"] == 1


@pytest.mark.unittest
def test_supervisor_report_exception_becomes_synthetic_error(monkeypatch, capsys):
    """An unexpected report writer exception cannot escape JSON mode."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda spec, timeout: CheckResult(
            spec.check_id, "PASS", spec.required, summary="injected pass"
        ),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.write_report",
        lambda path, snapshot: (_ for _ in ()).throw(RuntimeError("writer broken")),
    )
    assert run_supervisor(("--format", "json", "--report", "report.json")) == 1
    payload = json.loads(capsys.readouterr().out)
    errors = {item["check_id"]: item for item in payload["checks"]}
    assert errors["selfcheck.report_write"]["reason"] == "report_write"
    assert "writer broken" in errors["selfcheck.report_write"]["details"]


@pytest.mark.unittest
def test_supervisor_renderer_exception_keeps_json_stdout_valid(monkeypatch, capsys):
    """A primary renderer failure emits a synthetic JSON diagnostic."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda spec, timeout: CheckResult(
            spec.check_id, "PASS", spec.required, summary="injected pass"
        ),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.render_json",
        lambda snapshot: (_ for _ in ()).throw(OSError("renderer broken")),
    )
    assert run_supervisor(("--format", "json")) == 1
    payload = json.loads(capsys.readouterr().out)
    errors = {item["check_id"]: item for item in payload["checks"]}
    assert errors["selfcheck.render"]["reason"] == "render_error"
    assert "renderer broken" in errors["selfcheck.render"]["details"]


@pytest.mark.unittest
def test_report_and_stdout_share_renderer_diagnostic_snapshot(
    monkeypatch, capsys, tmp_path
):
    """A renderer failure is present in both report and stdout snapshots."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.report import render_json as canonical_render_json
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda spec, timeout: CheckResult(
            spec.check_id, "PASS", spec.required, summary="injected pass"
        ),
    )
    calls = []

    def fail_once(snapshot):
        if not calls:
            calls.append(snapshot)
            raise OSError("renderer broken")
        return canonical_render_json(snapshot)

    monkeypatch.setattr("pyfcstm._selfcheck.supervisor.render_json", fail_once)
    report_path = tmp_path / "report.json"
    assert run_supervisor(("--format", "json", "--report", str(report_path))) == 1
    stdout_payload = json.loads(capsys.readouterr().out)
    report_payload = json.loads(report_path.read_text(encoding="utf-8"))
    assert stdout_payload == report_payload
    assert any(
        item["check_id"] == "selfcheck.render" for item in stdout_payload["checks"]
    )


@pytest.mark.unittest
def test_supervisor_renderer_exception_has_human_fallback(monkeypatch, capsys):
    """Human mode retains a readable diagnostic when its renderer fails."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda spec, timeout: CheckResult(
            spec.check_id, "PASS", spec.required, summary="injected pass"
        ),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.render_human",
        lambda snapshot, color: (_ for _ in ()).throw(RuntimeError("human broken")),
    )
    assert run_supervisor(()) == 1
    output = capsys.readouterr().out
    assert "selfcheck.render" in output
    assert "human broken" in output


@pytest.mark.unittest
def test_supervisor_unexpected_setup_exception_is_serialized(monkeypatch, capsys):
    """Unlisted ordinary setup exceptions still receive infrastructure output."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.collect_environment",
        lambda redact: (_ for _ in ()).throw(AssertionError("shape assertion")),
    )
    assert run_supervisor(("--format", "json")) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"][-1]["reason"] == "infrastructure_error"
    assert "shape assertion" in payload["checks"][-1]["details"]


@pytest.mark.unittest
def test_supervisor_ctrl_c_renderer_failure_keeps_json_valid(monkeypatch, capsys):
    """Ctrl-C report rendering also uses the canonical fallback path."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda *args, **kwargs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.render_json",
        lambda snapshot: (_ for _ in ()).throw(OSError("interrupt renderer")),
    )
    assert run_supervisor(("--format", "json")) == 130
    payload = json.loads(capsys.readouterr().out)
    assert any(item["check_id"] == "selfcheck.render" for item in payload["checks"])


@pytest.mark.unittest
def test_supervisor_argument_error_keeps_json_stdout_valid(capsys):
    """Invalid JSON-mode options still produce a canonical machine result."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    assert run_supervisor(("--format", "json", "--unknown")) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"][0]["reason"] == "infrastructure_error"


@pytest.mark.unittest
def test_supervisor_equals_format_keeps_json_stdout_valid(capsys):
    """The compact ``--format=json`` spelling preserves JSON error output."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    assert run_supervisor(("--unknown", "--format=json")) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"][0]["reason"] == "infrastructure_error"


@pytest.mark.unittest
def test_supervisor_missing_format_value_keeps_json_stdout_valid(capsys):
    """A malformed trailing format flag still uses the machine channel."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    assert run_supervisor(("--unknown", "--format")) == 2
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"][0]["reason"] == "infrastructure_error"


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
def test_supervisor_ctrl_c_marks_running_and_pending_checks_distinctly(
    monkeypatch, capsys
):
    """Only the check interrupted while running becomes CRASH."""
    from pyfcstm._selfcheck.model import CheckResult, CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (CheckSpec("first", "first"), CheckSpec("second", "second")),
    )

    def interrupt_second(spec, timeout):
        if spec.check_id == "first":
            return CheckResult(spec.check_id, "PASS", True, summary="done")
        raise KeyboardInterrupt()

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process", interrupt_second
    )
    assert run_supervisor(("--format", "json")) == 130
    payload = json.loads(capsys.readouterr().out)
    assert [(item["check_id"], item["status"]) for item in payload["checks"]] == [
        ("first", "PASS"),
        ("second", "CRASH"),
    ]


@pytest.mark.unittest
def test_supervisor_ctrl_c_before_worker_marks_check_blocked(monkeypatch, capsys):
    """A pre-worker interrupt leaves the selected check BLOCKED."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (CheckSpec("demo", "demo"),),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.collect_environment",
        lambda redact: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert run_supervisor(("--format", "json")) == 130
    payload = json.loads(capsys.readouterr().out)
    assert [(item["check_id"], item["status"]) for item in payload["checks"]] == [
        ("demo", "BLOCKED")
    ]


@pytest.mark.unittest
def test_supervisor_ctrl_c_during_reserve_keeps_partial_ledger_valid(
    monkeypatch, capsys
):
    """A reserve interruption still produces a terminal result for reserved items."""
    from pyfcstm._selfcheck.model import CheckSpec, Ledger
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (CheckSpec("demo", "demo"),),
    )
    original_reserve = Ledger.reserve

    def interrupted_reserve(ledger, specs):
        original_reserve(ledger, specs)
        raise KeyboardInterrupt()

    monkeypatch.setattr(Ledger, "reserve", interrupted_reserve)
    assert run_supervisor(("--format", "json")) == 130
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"][0]["status"] == "BLOCKED"


@pytest.mark.unittest
def test_supervisor_ctrl_c_before_any_reservation_keeps_summary_valid(
    monkeypatch, capsys
):
    """Cleanup does not retry a bulk reserve that was interrupted immediately."""
    from pyfcstm._selfcheck.model import CheckSpec, Ledger
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (CheckSpec("demo", "demo"),),
    )
    monkeypatch.setattr(
        Ledger,
        "reserve",
        lambda self, specs: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert run_supervisor(("--format", "json")) == 130
    payload = json.loads(capsys.readouterr().out)
    assert payload["checks"][0]["check_id"] == "demo"
    assert payload["checks"][0]["status"] == "BLOCKED"


@pytest.mark.unittest
def test_supervisor_preserves_status_for_legacy_warning_marker(monkeypatch, capsys):
    """A result status remains authoritative over summary text."""
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
    assert json.loads(capsys.readouterr().out)["counts"] == {"PASS": 2}


@pytest.mark.unittest
def test_supervisor_does_not_drop_reserved_checks_on_setup_failure(monkeypatch, capsys):
    """Infrastructure failure preserves every selected check in the snapshot."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (CheckSpec("demo", "demo"),),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.collect_environment",
        lambda redact: (_ for _ in ()).throw(TypeError("environment shape")),
    )
    assert run_supervisor(("--format", "json")) == 3
    payload = json.loads(capsys.readouterr().out)
    assert {item["check_id"] for item in payload["checks"]} == {
        "demo",
        "selfcheck.infrastructure",
    }
    assert {item["check_id"]: item["status"] for item in payload["checks"]} == {
        "demo": "BLOCKED",
        "selfcheck.infrastructure": "ERROR",
    }


@pytest.mark.unittest
def test_supervisor_defers_reverse_ordered_prerequisites(monkeypatch, capsys):
    """A dependent check runs after a later-listed prerequisite passes."""
    from pyfcstm._selfcheck.model import CheckResult, CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (
            CheckSpec("dependent", "dependent", prerequisites=("base",)),
            CheckSpec("base", "base"),
        ),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda spec, timeout: CheckResult(spec.check_id, "PASS", True, summary="ran"),
    )
    assert run_supervisor(("--format", "json")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert {item["check_id"]: item["status"] for item in payload["checks"]} == {
        "base": "PASS",
        "dependent": "PASS",
    }


@pytest.mark.unittest
def test_supervisor_blocks_dependent_after_failed_prerequisite(monkeypatch, capsys):
    """A failed prerequisite blocks its dependent on the next scheduling pass."""
    from pyfcstm._selfcheck.model import CheckResult, CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (
            CheckSpec("dependent", "dependent", prerequisites=("base",)),
            CheckSpec("base", "base"),
        ),
    )

    def fail_base(spec, timeout):
        status = "ERROR" if spec.check_id == "base" else "PASS"
        return CheckResult(spec.check_id, status, True, summary="result")

    monkeypatch.setattr("pyfcstm._selfcheck.supervisor.run_check_process", fail_base)
    assert run_supervisor(("--format", "json")) == 1
    payload = json.loads(capsys.readouterr().out)
    assert {
        item["check_id"]: (item["status"], item["reason"]) for item in payload["checks"]
    } == {
        "base": ("ERROR", None),
        "dependent": ("BLOCKED", "prerequisite_failed"),
    }


@pytest.mark.unittest
def test_supervisor_marks_unresolved_dependency_cycle_blocked(monkeypatch, capsys):
    """A dependency cycle converges to BLOCKED instead of looping forever."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (
            CheckSpec("a", "a", prerequisites=("b",)),
            CheckSpec("b", "b", prerequisites=("a",)),
        ),
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda *args, **kwargs: pytest.fail("cycle must not start a worker"),
    )
    assert run_supervisor(("--format", "json")) == 1
    payload = json.loads(capsys.readouterr().out)
    assert {item["reason"] for item in payload["checks"]} == {"prerequisite_unresolved"}


@pytest.mark.unittest
def test_supervisor_infrastructure_failure_returns_three(monkeypatch, capsys):
    """Registry or ledger failures use the infrastructure exit code."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (_ for _ in ()).throw(RuntimeError("registry broken")),
    )
    assert run_supervisor(("--format", "json")) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"] == {"ERROR": 1}
    assert payload["checks"][0]["reason"] == "infrastructure_error"


@pytest.mark.unittest
def test_supervisor_unexpected_named_setup_error_has_json_snapshot(monkeypatch, capsys):
    """Named setup failures never leave JSON mode without a machine-readable result."""
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.collect_environment",
        lambda redact: (_ for _ in ()).throw(TypeError("environment shape")),
    )
    assert run_supervisor(("--format", "json")) == 3
    payload = json.loads(capsys.readouterr().out)
    reasons = {item["check_id"]: item["reason"] for item in payload["checks"]}
    assert reasons["selfcheck.infrastructure"] == "infrastructure_error"
    assert any("environment shape" in item["details"] for item in payload["checks"])


@pytest.mark.unittest
def test_supervisor_global_deadline_blocks_unstarted_checks(monkeypatch, capsys):
    """A depleted global budget finalizes every selected check as BLOCKED."""
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.supervisor import run_supervisor

    monkeypatch.setitem(
        __import__(
            "pyfcstm._selfcheck.supervisor", fromlist=["_PROFILE_DEADLINES"]
        ).__dict__["_PROFILE_DEADLINES"],
        "default",
        0.0,
    )
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.selected_specs",
        lambda profile: (
            CheckSpec("first", "first"),
            CheckSpec("second", "second"),
        ),
    )
    called = []
    monkeypatch.setattr(
        "pyfcstm._selfcheck.supervisor.run_check_process",
        lambda *args, **kwargs: called.append((args, kwargs)),
    )
    assert run_supervisor(("--format", "json")) == 1
    payload = json.loads(capsys.readouterr().out)
    assert called == []
    assert payload["counts"] == {"BLOCKED": 2}


@pytest.mark.unittest
def test_supervisor_scaled_timeout_passes_scale_to_worker(monkeypatch, capsys):
    """Non-default timeout scaling uses the explicit worker scale parameter."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.supervisor import run_supervisor

    calls = []

    def run_worker(spec, timeout, timeout_scale):
        calls.append((spec.check_id, timeout, timeout_scale))
        return CheckResult(spec.check_id, "PASS", spec.required, summary="scaled")

    monkeypatch.setattr("pyfcstm._selfcheck.supervisor.run_check_process", run_worker)
    assert run_supervisor(("--format", "json", "--timeout-scale", "0.5")) == 0
    capsys.readouterr()
    assert calls and calls[0][2] == 0.5


@pytest.mark.unittest
def test_render_snapshot_fallback_failure_uses_emergency_writer(monkeypatch):
    """If both renderers fail, the final emergency channel still runs."""
    from types import SimpleNamespace

    import pyfcstm._selfcheck.supervisor as supervisor_module
    from pyfcstm._selfcheck.model import ReportSnapshot

    options = SimpleNamespace(output_format="json", color="never")
    snapshot = ReportSnapshot((), {}, {})
    monkeypatch.setattr(
        supervisor_module,
        "render_json",
        lambda current: (_ for _ in ()).throw(RuntimeError("primary")),
    )
    monkeypatch.setattr(
        supervisor_module,
        "_fallback_json",
        lambda current: (_ for _ in ()).throw(ValueError("fallback")),
    )
    messages = []
    monkeypatch.setattr(
        supervisor_module,
        "emergency_write",
        lambda message, output_format: messages.append((message, output_format)),
    )
    result, output, rendered = supervisor_module._render_snapshot(snapshot, options)
    assert result is snapshot
    assert output is None
    assert rendered is False
    assert messages and "fallback" in messages[0][0]


@pytest.mark.unittest
def test_render_snapshot_preserves_non_exception_control_sentinel(monkeypatch):
    """Unexpected BaseException sentinels are not silently swallowed."""
    from types import SimpleNamespace

    import pyfcstm._selfcheck.supervisor as supervisor_module
    from pyfcstm._selfcheck.model import ReportSnapshot

    monkeypatch.setattr(
        supervisor_module,
        "render_json",
        lambda snapshot: (_ for _ in ()).throw(BaseException("sentinel")),
    )
    with pytest.raises(BaseException, match="sentinel"):
        supervisor_module._render_snapshot(
            ReportSnapshot((), {}, {}),
            SimpleNamespace(output_format="json", color="never"),
        )

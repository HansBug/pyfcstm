"""Behavioral tests for the contracted single-writer supervisor."""

import json

import pytest

from pyfcstm._selfcheck import supervisor
from pyfcstm._selfcheck import registry
from pyfcstm._selfcheck.model import CheckOutcome, CheckResult, CheckSpec, Ledger


def _payload(capsys):
    return json.loads(capsys.readouterr().out)


def _result(spec, status="PASS", summary="ready"):
    return CheckResult.from_outcome(spec, CheckOutcome(status, summary))


def _install_worker_specs(monkeypatch, specs, callback=None):
    monkeypatch.setattr(supervisor, "selected_specs", lambda profile: tuple(specs))
    monkeypatch.setattr(
        supervisor,
        "run_check_process",
        callback or (lambda spec, timeout, timeout_scale: _result(spec)),
    )


@pytest.mark.unittest
def test_default_profile_returns_one_canonical_snapshot(capsys):
    """The real two-check foundation shares one exact JSON schema."""
    assert supervisor.run_supervisor(("--format", "json")) == 0
    payload = _payload(capsys)
    assert [item["id"] for item in payload["results"]] == [
        "runtime.metadata",
        "artifact.self_dispatch",
    ]
    assert payload["summary"] == {"PASS": 2}
    assert payload["dependencies"][1]["prerequisite"] == ["runtime.metadata"]
    assert "checks" not in payload and "counts" not in payload


@pytest.mark.unittest
def test_fail_on_warn_only_changes_exit_policy(monkeypatch, capsys):
    """A typed WARN remains WARN when strict exit policy is enabled."""
    spec = CheckSpec("optional.warning", "warning")
    _install_worker_specs(
        monkeypatch,
        (spec,),
        lambda spec, timeout, timeout_scale: _result(spec, "WARN", "optional"),
    )
    assert supervisor.run_supervisor(("--format", "json")) == 0
    assert _payload(capsys)["results"][0]["status"] == "WARN"
    assert supervisor.run_supervisor(("--format", "json", "--fail-on-warn")) == 1
    assert _payload(capsys)["results"][0]["status"] == "WARN"


@pytest.mark.unittest
def test_local_typed_check_does_not_spawn(monkeypatch, capsys):
    """Bootstrap-safe checks execute locally through the same outcome contract."""
    spec = CheckSpec("local.demo", "local_demo", execution="local")
    monkeypatch.setitem(
        registry._WORKERS, "local_demo", lambda: CheckOutcome("PASS", "local")
    )
    monkeypatch.setattr(supervisor, "selected_specs", lambda profile: (spec,))
    monkeypatch.setattr(
        supervisor,
        "run_check_process",
        lambda *args, **kwargs: (_ for _ in ()).throw(AssertionError("spawned")),
    )
    assert supervisor.run_supervisor(("--format", "json")) == 0
    assert _payload(capsys)["results"][0]["summary"] == "local"


@pytest.mark.unittest
def test_argument_errors_keep_json_stdout_parseable(capsys):
    """Syntax/profile failures return exit 2 with the canonical schema."""
    assert supervisor.run_supervisor(("--format", "json", "--network")) == 2
    payload = _payload(capsys)
    assert payload["exit_code"] == 2
    assert payload["results"][0]["reason"] == "argument_error"
    assert set(payload) == {
        "schema_version",
        "report_id",
        "started_at",
        "finished_at",
        "profile",
        "environment",
        "artifact",
        "dependencies",
        "capabilities",
        "results",
        "summary",
        "exit_code",
    }


@pytest.mark.unittest
@pytest.mark.parametrize("raises", [False, True])
def test_report_write_failure_becomes_one_synthetic_result(
    monkeypatch, capsys, tmp_path, raises
):
    """A report destination failure changes stdout and exit without recursion."""
    spec = CheckSpec("demo", "demo")
    _install_worker_specs(monkeypatch, (spec,))

    def fail(*args):
        if raises:
            raise RuntimeError("writer broken")
        return "writer broken"

    monkeypatch.setattr(supervisor, "write_report", fail)
    assert (
        supervisor.run_supervisor(
            ("--format", "json", "--report", str(tmp_path / "report.json"))
        )
        == 1
    )
    payload = _payload(capsys)
    assert [item["id"] for item in payload["results"]] == [
        "demo",
        "selfcheck.report_write",
    ]
    assert payload["results"][-1]["reason"] == "report_write"


@pytest.mark.unittest
def test_report_file_and_stdout_share_the_same_snapshot(monkeypatch, capsys, tmp_path):
    """Successful report and stdout JSON serialize one frozen snapshot."""
    spec = CheckSpec("demo", "demo")
    _install_worker_specs(monkeypatch, (spec,))
    report = tmp_path / "report.json"
    assert supervisor.run_supervisor(("--format", "json", "--report", str(report))) == 0
    assert json.loads(report.read_text(encoding="utf-8")) == _payload(capsys)


@pytest.mark.unittest
def test_misordered_prerequisite_is_blocked_without_reordering(monkeypatch, capsys):
    """Registry order is execution order; the supervisor never reschedules."""
    dependent = CheckSpec("dependent", "dependent", prerequisites=("base",))
    base = CheckSpec("base", "base")
    calls = []

    def run(spec, timeout, timeout_scale):
        calls.append(spec.check_id)
        return _result(spec)

    _install_worker_specs(monkeypatch, (dependent, base), run)
    assert supervisor.run_supervisor(("--format", "json")) == 1
    payload = _payload(capsys)
    assert calls == ["base"]
    assert [item["id"] for item in payload["results"]] == ["dependent", "base"]
    assert payload["results"][0]["status"] == "BLOCKED"
    assert payload["results"][0]["reason"] == "prerequisite_unresolved"


@pytest.mark.unittest
def test_failed_prerequisite_blocks_only_its_dependent(monkeypatch, capsys):
    """A semantic FAIL becomes BLOCKED downstream without aborting the session."""
    base = CheckSpec("base", "base")
    dependent = CheckSpec("dependent", "dependent", prerequisites=("base",))

    def run(spec, timeout, timeout_scale):
        return _result(spec, "FAIL" if spec.check_id == "base" else "PASS")

    _install_worker_specs(monkeypatch, (base, dependent), run)
    assert supervisor.run_supervisor(("--format", "json")) == 1
    results = {item["id"]: item for item in _payload(capsys)["results"]}
    assert results["base"]["status"] == "FAIL"
    assert results["dependent"]["status"] == "BLOCKED"
    assert results["dependent"]["reason"] == "prerequisite_failed"


@pytest.mark.unittest
def test_dependency_cycle_is_terminalized_as_blocked(monkeypatch, capsys):
    """Unresolvable selected dependencies cannot remain pending at freeze."""
    specs = (
        CheckSpec("a", "a", prerequisites=("b",)),
        CheckSpec("b", "b", prerequisites=("a",)),
    )
    _install_worker_specs(monkeypatch, specs)
    assert supervisor.run_supervisor(("--format", "json")) == 1
    assert {item["status"] for item in _payload(capsys)["results"]} == {"BLOCKED"}


@pytest.mark.unittest
def test_interrupt_marks_running_and_pending_checks_distinctly(monkeypatch, capsys):
    """The first Ctrl-C produces a complete partial snapshot and exit 130."""
    specs = (CheckSpec("first", "first"), CheckSpec("second", "second"))

    def interrupt(spec, timeout, timeout_scale):
        raise KeyboardInterrupt()

    _install_worker_specs(monkeypatch, specs, interrupt)
    assert supervisor.run_supervisor(("--format", "json")) == 130
    results = {item["id"]: item for item in _payload(capsys)["results"]}
    assert results["first"]["status"] == "CRASH"
    assert results["second"]["status"] == "BLOCKED"
    assert {item["reason"] for item in results.values()} == {"supervisor_interrupted"}


@pytest.mark.unittest
def test_interrupt_during_reservation_repairs_selected_ledger(monkeypatch, capsys):
    """Partially reserved selected IDs are all represented in the final report."""
    specs = (CheckSpec("first", "first"), CheckSpec("second", "second"))
    monkeypatch.setattr(supervisor, "selected_specs", lambda profile: specs)
    original = Ledger.reserve

    def interrupted_reserve(self, selected):
        original(self, (selected[0],))
        raise KeyboardInterrupt()

    monkeypatch.setattr(Ledger, "reserve", interrupted_reserve)
    assert supervisor.run_supervisor(("--format", "json")) == 130
    assert [item["id"] for item in _payload(capsys)["results"]] == [
        "first",
        "second",
    ]


@pytest.mark.unittest
def test_registry_setup_failure_returns_infrastructure_snapshot(monkeypatch, capsys):
    """A pre-check ordinary exception remains a canonical exit-3 report."""
    monkeypatch.setattr(
        supervisor,
        "selected_specs",
        lambda profile: (_ for _ in ()).throw(RuntimeError("registry broken")),
    )
    assert supervisor.run_supervisor(("--format", "json")) == 3
    payload = _payload(capsys)
    assert payload["exit_code"] == 3
    assert payload["results"][0]["id"] == "selfcheck.infrastructure"
    assert "registry broken" in payload["results"][0]["evidence"]


@pytest.mark.unittest
def test_worker_supervision_error_does_not_abort_independent_check(monkeypatch, capsys):
    """One ordinary process-boundary exception is isolated to its check."""
    specs = (CheckSpec("broken", "broken"), CheckSpec("healthy", "healthy"))

    def run(spec, timeout, timeout_scale):
        if spec.check_id == "broken":
            raise OSError("process unavailable")
        return _result(spec)

    _install_worker_specs(monkeypatch, specs, run)
    assert supervisor.run_supervisor(("--format", "json")) == 1
    results = {item["id"]: item for item in _payload(capsys)["results"]}
    assert results["broken"]["status"] == "ERROR"
    assert results["healthy"]["status"] == "PASS"


@pytest.mark.unittest
def test_global_deadline_blocks_unstarted_checks(monkeypatch, capsys):
    """The global deadline terminalizes every unstarted selected check."""
    specs = (CheckSpec("first", "first"), CheckSpec("second", "second"))
    _install_worker_specs(monkeypatch, specs)
    monkeypatch.setitem(supervisor._PROFILE_DEADLINES, "default", 0.0)
    assert supervisor.run_supervisor(("--format", "json")) == 1
    payload = _payload(capsys)
    assert payload["summary"] == {"BLOCKED": 2}
    assert {item["reason"] for item in payload["results"]} == {"global_deadline"}


@pytest.mark.unittest
def test_check_timeout_and_cli_scale_are_combined(monkeypatch, capsys):
    """Per-check timeout policy is scaled before crossing the process boundary."""
    spec = CheckSpec("scaled", "scaled", timeout_seconds=4.0)
    observed = []

    def run(spec, timeout, timeout_scale):
        observed.append((timeout, timeout_scale))
        return _result(spec)

    _install_worker_specs(monkeypatch, (spec,), run)
    assert supervisor.run_supervisor(("--format", "json", "--timeout-scale", "2")) == 0
    _payload(capsys)
    assert observed == [(8.0, 2.0)]

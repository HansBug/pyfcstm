"""Behavioral tests for the contracted single-writer supervisor."""

import json
import errno
import contextlib
import os
import subprocess
import sys

import pytest

from pyfcstm._selfcheck import supervisor
from pyfcstm._selfcheck import registry
from pyfcstm._selfcheck.model import (
    CheckOutcome,
    CheckResult,
    CheckSpec,
    Ledger,
)


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
@pytest.mark.parametrize(
    ("worker_key", "callback", "reason"),
    [
        ("missing_local", None, "unknown_local_check"),
        ("local_invalid", lambda: "not typed", "local_check_exception"),
        (
            "local_error",
            lambda: (_ for _ in ()).throw(ValueError("broken")),
            "local_check_exception",
        ),
        (
            "local_exit",
            lambda: (_ for _ in ()).throw(SystemExit(2)),
            "local_check_system_exit",
        ),
    ],
)
def test_local_public_supervisor_faults_are_structured(
    monkeypatch, capsys, worker_key, callback, reason
):
    """Real local callback faults become typed results without spawning."""
    spec = CheckSpec("local.fault", worker_key, execution="local")
    if callback is not None:
        monkeypatch.setitem(registry._WORKERS, worker_key, callback)
    monkeypatch.setattr(supervisor, "selected_specs", lambda profile: (spec,))
    assert supervisor.run_supervisor(("--format", "json")) == 1
    payload = _payload(capsys)
    assert payload["results"][0]["status"] == "ERROR"
    assert payload["results"][0]["reason"] == reason


@pytest.mark.unittest
def test_local_generator_exit_is_not_swallowed(monkeypatch):
    """Non-runtime control sentinels remain visible at the local boundary."""
    spec = CheckSpec("local.exit", "local_exit", execution="local")
    monkeypatch.setitem(
        registry._WORKERS,
        "local_exit",
        lambda: (_ for _ in ()).throw(GeneratorExit()),
    )
    monkeypatch.setattr(supervisor, "selected_specs", lambda profile: (spec,))
    with pytest.raises(GeneratorExit):
        supervisor.run_supervisor(("--format", "json"))


@pytest.mark.unittest
def test_terminalize_unfinished_skips_already_committed_results():
    """Infrastructure cleanup does not duplicate an existing terminal result."""
    spec = CheckSpec("demo.done", "demo")
    ledger = Ledger()
    ledger.reserve((spec,))
    ledger.mark_running(spec.check_id)
    ledger.commit(_result(spec))
    supervisor._terminalize_unfinished(ledger, (spec,), interrupted=False)
    assert len(ledger.freeze({}).checks) == 1


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
def test_human_output_failure_becomes_a_terminal_diagnostic(monkeypatch, capfd):
    """A failed final human write returns exit 3 instead of escaping."""
    spec = CheckSpec("demo", "demo")
    _install_worker_specs(monkeypatch, (spec,))
    monkeypatch.setattr(
        supervisor,
        "write_human",
        lambda *args: (_ for _ in ()).throw(OSError("stdout failed")),
    )

    assert supervisor.run_supervisor(()) == 3
    captured = capfd.readouterr()
    assert "self-check output failure" in captured.out + captured.err


@pytest.mark.unittest
def test_public_supervisor_broken_pipe_keeps_shutdown_stable(monkeypatch, capfd):
    """A real human-output broken pipe reaches the emergency diagnostic chain."""

    class BrokenStdout:
        def write(self, value):
            del value
            raise BrokenPipeError(errno.EPIPE, "closed")

        def flush(self):
            return None

        def fileno(self):
            # Python 3.14's argparse probes stdout during parser creation;
            # an invalid descriptor keeps that probe non-throwing while still
            # forcing the emergency path after the write failure.
            return -1

    spec = CheckSpec("demo", "demo")
    _install_worker_specs(monkeypatch, (spec,))
    with contextlib.redirect_stdout(BrokenStdout()):
        assert supervisor.run_supervisor(("--color", "never")) == 3
    assert "self-check output failure" in capfd.readouterr().err


@pytest.mark.unittest
def test_json_render_failure_keeps_stdout_clean(monkeypatch, capfd):
    """A broken JSON renderer falls back to stderr and returns exit 3."""
    spec = CheckSpec("demo", "demo")
    _install_worker_specs(monkeypatch, (spec,))
    monkeypatch.setattr(
        supervisor,
        "render_json",
        lambda *args: (_ for _ in ()).throw(ValueError("renderer failed")),
    )

    assert supervisor.run_supervisor(("--format", "json")) == 3
    captured = capfd.readouterr()
    assert captured.out == ""
    assert "self-check output failure" in captured.err
    assert "renderer failed" in captured.err


@pytest.mark.unittest
@pytest.mark.skipif(os.name != "posix", reason="POSIX broken-pipe contract")
@pytest.mark.parametrize(
    "arguments",
    [
        ("--self-check", "--color", "never"),
        ("--self-check", "--format", "json", "--network"),
    ],
)
def test_closed_stdout_pipe_returns_stable_output_error(arguments):
    """A real closed stdout pipe yields exit 3 and an emergency diagnostic."""
    read_descriptor, write_descriptor = os.pipe()
    os.close(read_descriptor)
    try:
        process = subprocess.run(
            [sys.executable, "-m", "pyfcstm"] + list(arguments),
            stdout=write_descriptor,
            stderr=subprocess.PIPE,
            timeout=15.0,
        )
    finally:
        os.close(write_descriptor)
    assert process.returncode == 3
    assert b"self-check output failure" in process.stderr


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
@pytest.mark.parametrize("error", [KeyboardInterrupt(), SystemExit(9)])
def test_report_control_sentinels_are_re_raised(monkeypatch, error):
    """Report finalization preserves interpreter-control sentinels."""
    spec = CheckSpec("demo", "demo")
    _install_worker_specs(monkeypatch, (spec,))

    def fail(*args):
        del args
        raise error

    monkeypatch.setattr(supervisor, "write_report", fail)
    with pytest.raises(type(error)):
        supervisor.run_supervisor(("--format", "json", "--report", "report.json"))


@pytest.mark.unittest
def test_report_non_runtime_control_sentinel_is_re_raised(monkeypatch):
    """Unexpected BaseException subclasses remain visible to callers."""

    class UnexpectedControl(BaseException):
        pass

    spec = CheckSpec("demo", "demo")
    _install_worker_specs(monkeypatch, (spec,))

    def fail(*args):
        del args
        raise UnexpectedControl("report control")

    monkeypatch.setattr(supervisor, "write_report", fail)
    with pytest.raises(UnexpectedControl):
        supervisor.run_supervisor(("--format", "json", "--report", "report.json"))


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
def test_worker_checks_finish_one_at_a_time_in_registry_order(monkeypatch, capsys):
    """A worker result is committed before the next registry entry starts."""
    specs = (CheckSpec("first", "first"), CheckSpec("second", "second"))
    events = []
    active = []

    def run(spec, timeout, timeout_scale):
        del timeout, timeout_scale
        assert not active
        active.append(spec.check_id)
        events.append(("start", spec.check_id))
        result = _result(spec)
        events.append(("finish", spec.check_id))
        active.pop()
        return result

    _install_worker_specs(monkeypatch, specs, run)
    assert supervisor.run_supervisor(("--format", "json")) == 0
    assert [item["id"] for item in _payload(capsys)["results"]] == [
        "first",
        "second",
    ]
    assert events == [
        ("start", "first"),
        ("finish", "first"),
        ("start", "second"),
        ("finish", "second"),
    ]


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

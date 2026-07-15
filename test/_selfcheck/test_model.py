"""Contract tests for typed self-check results and the ordered ledger."""

import math

import pytest

from pyfcstm._selfcheck.model import (
    CheckOutcome,
    CheckResult,
    CheckSpec,
    Ledger,
)


@pytest.mark.unittest
def test_spec_and_typed_outcome_build_canonical_result():
    """Static policy and callback semantics combine without magic strings."""
    spec = CheckSpec(
        "artifact.self_dispatch",
        "self_dispatch",
        title="isolated self-dispatch",
        prerequisites=("runtime.metadata",),
    )
    outcome = CheckOutcome(
        "PASS",
        "worker ready",
        expected="worker starts",
        observed="worker started",
    )

    result = CheckResult.from_outcome(spec, outcome, pid=42)
    payload = result.to_dict()
    assert payload["id"] == spec.check_id
    assert payload["group"] == "artifact"
    assert payload["title"] == spec.title
    assert payload["prerequisite"] == ["runtime.metadata"]
    assert payload["expected"] == "worker starts"
    assert payload["pid"] == 42
    assert "check_id" not in payload


@pytest.mark.unittest
@pytest.mark.parametrize("status", ["BLOCKED", "TIMEOUT", "CRASH"])
def test_callback_rejects_supervisor_and_parent_owned_statuses(status):
    """Callbacks cannot claim lifecycle/process statuses they do not own."""
    with pytest.raises(ValueError, match="cannot return status"):
        CheckOutcome(status, "invalid")


@pytest.mark.unittest
def test_spec_validates_execution_and_timeout():
    """Invalid execution policy fails during static registry construction."""
    with pytest.raises(ValueError, match="ID must not be empty"):
        CheckSpec("", "demo")
    with pytest.raises(ValueError, match="worker key must not be empty"):
        CheckSpec("demo", "")
    with pytest.raises(ValueError, match="execution boundary"):
        CheckSpec("demo", "demo", execution="thread")
    with pytest.raises(ValueError, match="timeout"):
        CheckSpec("demo", "demo", timeout_seconds=0.0)
    for invalid in (math.inf, math.nan):
        with pytest.raises(ValueError, match="timeout"):
            CheckSpec("demo", "demo", timeout_seconds=invalid)
    with pytest.raises(ValueError, match="unknown self-check status"):
        CheckResult("demo", "UNKNOWN", True)


@pytest.mark.unittest
def test_ledger_preserves_registry_order_and_derives_counts():
    """Snapshot order and counts come from the same terminal result tuple."""
    first = CheckSpec("runtime.metadata", "runtime", execution="local")
    second = CheckSpec(
        "artifact.self_dispatch",
        "dispatch",
        prerequisites=(first.check_id,),
    )
    ledger = Ledger()
    ledger.reserve((first, second))
    ledger.mark_running(first.check_id)
    ledger.commit(CheckResult.from_outcome(first, CheckOutcome("PASS", "one")))
    ledger.mark_running(second.check_id)
    ledger.commit(CheckResult.from_outcome(second, CheckOutcome("WARN", "two")))

    snapshot = ledger.freeze({"profile": "default"})
    assert [item.check_id for item in snapshot.checks] == [
        first.check_id,
        second.check_id,
    ]
    assert snapshot.counts == {"PASS": 1, "WARN": 1}


@pytest.mark.unittest
def test_ledger_rejects_invalid_lifecycle_operations():
    """The single writer still enforces reservation and one terminal commit."""
    spec = CheckSpec("demo", "demo")
    ledger = Ledger()
    ledger.reserve((spec,))
    with pytest.raises(KeyError):
        ledger.mark_running("missing")
    with pytest.raises(ValueError, match="duplicate check id"):
        ledger.reserve((spec,))
    with pytest.raises(KeyError):
        ledger.commit(CheckResult("missing", "PASS", True))
    with pytest.raises(RuntimeError, match="pending self-checks"):
        ledger.freeze({})

    ledger.mark_running(spec.check_id)
    result = CheckResult.from_outcome(spec, CheckOutcome("PASS", "ready"))
    ledger.commit(result)
    with pytest.raises(RuntimeError, match="duplicate terminal"):
        ledger.commit(result)
    with pytest.raises(RuntimeError, match="not pending"):
        ledger.mark_running(spec.check_id)


@pytest.mark.unittest
def test_snapshot_uses_one_exact_top_level_schema():
    """Unshipped compact-schema aliases never enter the public JSON contract."""
    spec = CheckSpec("demo", "demo")
    ledger = Ledger()
    ledger.reserve((spec,))
    ledger.commit(CheckResult.from_outcome(spec, CheckOutcome("PASS", "ready")))
    payload = ledger.freeze(
        {
            "session_id": "session",
            "started_at": 1.0,
            "finished_at": 2.0,
            "profile": "default",
            "environment": {},
            "artifact": {},
            "dependencies": [],
            "capabilities": {},
            "exit_code": 0,
        }
    ).to_dict()
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
def test_report_snapshot_freezes_nested_metadata():
    """External metadata mutation cannot rewrite a frozen report snapshot."""
    spec = CheckSpec("demo", "demo")
    ledger = Ledger()
    ledger.reserve((spec,))
    ledger.commit(CheckResult.from_outcome(spec, CheckOutcome("PASS", "ready")))
    metadata = {"environment": {"paths": ["/private"]}, "exit_code": 0}
    snapshot = ledger.freeze(metadata)
    metadata["environment"]["paths"].append("/changed")
    assert snapshot.to_dict()["environment"]["paths"] == ["/private"]
    with pytest.raises(TypeError):
        snapshot.metadata["exit_code"] = 1

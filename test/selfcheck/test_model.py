"""Tests for self-check ledger and snapshot invariants."""

import threading

import pytest


@pytest.mark.unittest
def test_terminal_commit_is_single_writer_and_duplicate_is_diagnostic():
    """Concurrent terminal submissions leave one result and one diagnostic."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.model import Ledger

    ledger = Ledger()
    ledger.reserve((CheckSpec("artifact.self_dispatch", "self_dispatch"),))
    results = []

    def submit(status):
        results.append(
            ledger.commit(
                CheckResult("artifact.self_dispatch", status, True, summary=status)
            )
        )

    threads = [
        threading.Thread(target=submit, args=("PASS",)),
        threading.Thread(target=submit, args=("ERROR",)),
    ]
    for thread in threads:
        thread.start()
    for thread in threads:
        thread.join()

    assert sorted(results) == [False, True]
    snapshot = ledger.freeze({"registry_coverage": 1})
    assert len(snapshot.checks) == 1
    assert (
        sum(result.status == "PASS" for result in snapshot.checks)
        + sum(result.status == "ERROR" for result in snapshot.checks)
        == 1
    )
    assert any(event.kind == "duplicate_terminal" for event in ledger.events)


@pytest.mark.unittest
def test_snapshot_counts_are_derived_from_same_check_tuple():
    """Snapshot counts cannot drift from the rendered result list."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.model import Ledger

    ledger = Ledger()
    ledger.reserve((CheckSpec("artifact.self_dispatch", "self_dispatch"),))
    ledger.commit(
        CheckResult("artifact.self_dispatch", "WARN", True, summary="optional warning")
    )
    snapshot = ledger.freeze({})
    assert snapshot.counts == {"WARN": 1}
    assert snapshot.to_dict()["counts"] == {"WARN": 1}


@pytest.mark.unittest
def test_ledger_rejects_duplicate_specs_unknown_results_and_pending_snapshot():
    """Ledger infrastructure errors remain explicit rather than producing partial PASS."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.model import Ledger

    ledger = Ledger()
    spec = CheckSpec("demo", "demo")
    ledger.reserve((spec,))
    with pytest.raises(ValueError):
        ledger.reserve((spec,))
    with pytest.raises(KeyError):
        ledger.commit(CheckResult("unknown", "PASS", True))
    with pytest.raises(RuntimeError):
        ledger.freeze({})


@pytest.mark.unittest
def test_ledger_tracks_running_state_before_terminal_commit():
    """The ledger distinguishes a running check from an unstarted check."""
    from pyfcstm._selfcheck.model import CheckResult
    from pyfcstm._selfcheck.model import CheckSpec
    from pyfcstm._selfcheck.model import Ledger

    ledger = Ledger()
    ledger.reserve((CheckSpec("demo", "demo"),))
    with pytest.raises(KeyError):
        ledger.mark_running("missing")
    assert ledger.get_state("demo") == "PENDING"
    assert ledger.mark_running("demo") is True
    assert ledger.get_state("demo") == "RUNNING"
    assert any(event.kind == "running" for event in ledger.events)
    assert ledger.commit(CheckResult("demo", "PASS", True)) is True
    assert ledger.get_state("demo") == "PASS"
    assert ledger.mark_running("demo") is False

    ledger.reserve((CheckSpec("other", "other"),))
    assert ledger.mark_running("other") is True
    with pytest.raises(RuntimeError, match="not pending"):
        ledger.mark_running("other")


@pytest.mark.unittest
def test_ledger_ensure_reserved_is_idempotent():
    """Emergency cleanup can register a spec without retrying bulk reserve."""
    from pyfcstm._selfcheck.model import CheckSpec, Ledger

    ledger = Ledger()
    spec = CheckSpec("demo", "demo")
    ledger.ensure_reserved(spec)
    ledger.ensure_reserved(spec)
    assert ledger.get_state("demo") == "PENDING"
    assert [event.kind for event in ledger.events] == ["pending"]


@pytest.mark.unittest
def test_check_result_rejects_unknown_status():
    """Result construction cannot introduce a non-contract status."""
    from pyfcstm._selfcheck.model import CheckResult

    with pytest.raises(ValueError, match="unknown self-check status"):
        CheckResult("demo", "UNKNOWN", True)

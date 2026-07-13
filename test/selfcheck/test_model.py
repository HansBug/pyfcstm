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
def test_check_result_rejects_unknown_status():
    """Result construction cannot introduce a non-contract status."""
    from pyfcstm._selfcheck.model import CheckResult

    with pytest.raises(ValueError, match="unknown self-check status"):
        CheckResult("demo", "UNKNOWN", True)

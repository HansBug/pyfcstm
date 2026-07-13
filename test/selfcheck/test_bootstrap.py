"""Tests for pre-Click self-check bootstrap dispatch."""

import sys

import pytest


@pytest.mark.unittest
def test_selfcheck_dispatch_does_not_import_click(monkeypatch):
    """Self-check mode is handled before the Click command graph."""
    from pyfcstm import _bootstrap

    invoked = []
    monkeypatch.setattr(
        _bootstrap, "run_selfcheck", lambda args: invoked.append(tuple(args)) or 0
    )
    sys.modules.pop("click", None)
    assert _bootstrap.main(("--self-check", "--format", "json")) == 0
    assert invoked == [("--format", "json")]
    assert "click" not in sys.modules


@pytest.mark.unittest
def test_hidden_worker_dispatch_is_exact_and_pre_click(monkeypatch):
    """Hidden worker mode is separate from supervisor and ordinary Click."""
    from pyfcstm import _bootstrap

    invoked = []
    monkeypatch.setattr(
        _bootstrap, "run_worker", lambda args: invoked.append(tuple(args)) or 0
    )
    assert _bootstrap.main(("--_pyfcstm-selfcheck-worker-v1", "--nonce", "x")) == 0
    assert invoked == [("--nonce", "x")]


@pytest.mark.unittest
def test_bootstrap_runtime_failure_keeps_json_stdout_machine_readable(
    monkeypatch, capsys
):
    """A bootstrap boundary failure still emits the canonical JSON shape."""
    import json

    from pyfcstm import _bootstrap

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(ZeroDivisionError("boom")),
    )
    assert _bootstrap.main(("--self-check", "--format", "json")) == 3
    payload = json.loads(capsys.readouterr().out)
    assert payload["counts"] == {"ERROR": 1}
    assert "boom" in payload["checks"][0]["details"]

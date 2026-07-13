"""Tests for the static self-check registry."""

import pytest


@pytest.mark.unittest
def test_registry_worker_modes_and_package_version(monkeypatch):
    """The artifact probe reports pass, warn, and failure deterministically."""
    from pyfcstm._selfcheck import registry

    monkeypatch.delenv("PYFCSTM_SELFCHECK_TEST_MODE", raising=False)
    assert "worker imported" in registry.get_worker("self_dispatch")()
    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "warn")
    assert registry.get_worker("self_dispatch")().startswith("__SELFCHECK_WARN__:")
    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "fail")
    with pytest.raises(RuntimeError, match="injected self-check failure"):
        registry.get_worker("self_dispatch")()


@pytest.mark.unittest
def test_registry_profiles_are_stable():
    """All PR-2 profiles expose exactly the implemented probe."""
    from pyfcstm._selfcheck.registry import selected_specs

    for profile in ("default", "full", "visualize"):
        specs = selected_specs(profile)
        assert [spec.check_id for spec in specs] == ["artifact.self_dispatch"]


@pytest.mark.unittest
def test_registry_failure_and_hang_modes_are_observable(monkeypatch):
    """Failure fixtures do not get mistaken for a healthy artifact."""
    import pyfcstm

    from pyfcstm._selfcheck import registry

    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "fail")
    with pytest.raises(RuntimeError, match="injected self-check failure"):
        registry.get_worker("self_dispatch")()
    monkeypatch.setenv("PYFCSTM_SELFCHECK_TEST_MODE", "hang")
    monkeypatch.setattr(
        "time.sleep", lambda seconds: (_ for _ in ()).throw(RuntimeError(seconds))
    )
    with pytest.raises(RuntimeError):
        registry.get_worker("self_dispatch")()
    monkeypatch.delenv("PYFCSTM_SELFCHECK_TEST_MODE", raising=False)
    original_version = pyfcstm.__version__
    try:
        pyfcstm.__version__ = None
        with pytest.raises(RuntimeError, match="package version is unavailable"):
            registry.get_worker("self_dispatch")()
    finally:
        pyfcstm.__version__ = original_version

"""Tests for the static built-in self-check registry."""

import pytest

from pyfcstm._selfcheck.model import CheckOutcome
from pyfcstm._selfcheck.registry import get_worker, selected_specs


@pytest.mark.unittest
def test_registry_profiles_select_the_stable_pr2_checks():
    """All PR-2 profiles select the same ordered two-check foundation."""
    for profile in ("default", "full", "visualize"):
        specs = selected_specs(profile)
        assert [item.check_id for item in specs] == [
            "runtime.metadata",
            "artifact.self_dispatch",
        ]
        assert specs[0].execution == "local"
        assert specs[1].prerequisites == ("runtime.metadata",)
        assert all(item.timeout_seconds == 30.0 for item in specs)


@pytest.mark.unittest
def test_builtin_callbacks_return_typed_outcomes():
    """Registry callbacks expose semantic outcomes rather than marker strings."""
    for key in ("runtime_metadata", "self_dispatch"):
        outcome = get_worker(key)()
        assert isinstance(outcome, CheckOutcome)
        assert outcome.status == "PASS"


@pytest.mark.unittest
def test_unknown_registry_key_is_not_dynamically_imported():
    """Arbitrary module/callable paths are rejected by the static map."""
    with pytest.raises(KeyError):
        get_worker("package.module:callable")

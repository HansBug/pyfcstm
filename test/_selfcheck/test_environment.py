"""Tests for self-check environment reporting."""

import pytest


@pytest.mark.unittest
def test_environment_can_include_unredacted_cwd():
    """The opt-in unredacted mode exposes a diagnostic cwd field."""
    from pyfcstm._selfcheck.environment import collect_environment

    data = collect_environment(redact=False)
    assert data["cwd"]
    assert data["python_executable"]

"""Tests for self-check environment reporting."""

import pytest


@pytest.mark.unittest
@pytest.mark.parametrize(
    ("target", "field"),
    [
        ("platform.python_version", "python_version"),
        ("platform.python_implementation", "implementation"),
        ("platform.platform", "platform"),
        ("platform.system", "system"),
        ("platform.release", "release"),
        ("platform.machine", "machine"),
        ("platform.architecture", "architecture"),
        ("locale.getpreferredencoding", "preferred_encoding"),
        ("sys.getfilesystemencoding", "filesystem_encoding"),
        ("os.getcwd", "cwd"),
        ("tempfile.gettempdir", "temp_directory"),
    ],
)
def test_environment_provider_failures_preserve_sibling_fields(
    monkeypatch, target, field
):
    """Each ordinary provider failure is isolated to its diagnostic field."""
    from pyfcstm._selfcheck.environment import collect_environment

    def fail(*args, **kwargs):
        del args, kwargs
        raise OSError("unavailable")

    monkeypatch.setattr(target, fail)
    data = collect_environment(redact=False)
    assert data[field] is None
    assert data["collection_errors"][field] == "OSError: unavailable"
    assert data["version"]
    assert data["python_executable"]


@pytest.mark.unittest
def test_environment_can_include_unredacted_cwd():
    """The opt-in unredacted mode exposes a diagnostic cwd field."""
    from pyfcstm._selfcheck.environment import collect_environment

    data = collect_environment(redact=False)
    assert data["cwd"]
    assert data["python_executable"]

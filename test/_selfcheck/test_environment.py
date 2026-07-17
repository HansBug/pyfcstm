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


@pytest.mark.unittest
def test_environment_redaction_skips_unavailable_path(monkeypatch):
    """Redaction preserves a field-specific collection failure."""
    from pyfcstm._selfcheck.environment import collect_environment

    monkeypatch.setattr(
        "pyfcstm._selfcheck.environment.os.getcwd",
        lambda: (_ for _ in ()).throw(OSError("cwd unavailable")),
    )
    data = collect_environment(redact=True)
    assert data["cwd"] is None
    assert data["collection_errors"]["cwd"] == "OSError: cwd unavailable"
    assert data["python_executable"] == "<redacted>"


@pytest.mark.unittest
def test_environment_identity_fields_fail_independently(monkeypatch):
    """A missing package identity field does not discard runtime metadata."""
    import pyfcstm

    monkeypatch.delattr(pyfcstm, "__commit__", raising=False)
    from pyfcstm._selfcheck.environment import collect_environment

    data = collect_environment(redact=False)
    assert data["commit"] is None
    assert data["collection_errors"]["commit"].startswith("AttributeError:")
    assert data["python_version"]

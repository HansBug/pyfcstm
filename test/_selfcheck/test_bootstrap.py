"""Tests for pre-Click self-check bootstrap dispatch."""

import io
import json
import sys
import contextlib
from types import SimpleNamespace

import pytest


@pytest.mark.unittest
def test_selfcheck_dispatch_does_not_import_click(monkeypatch):
    """Self-check mode is handled before the Click command graph."""
    from pyfcstm import _bootstrap

    invoked = []
    monkeypatch.setattr(
        _bootstrap, "run_selfcheck", lambda args: invoked.append(tuple(args)) or 0
    )
    monkeypatch.delitem(sys.modules, "click", raising=False)
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
    assert _bootstrap.main(("--self-check-worker", "--nonce", "x")) == 0
    assert invoked == [("--nonce", "x")]


@pytest.mark.parametrize(
    "arguments",
    (
        ("--self-check", "--self-check-worker"),
        ("--self-check-worker", "--self-check"),
    ),
)
@pytest.mark.unittest
def test_mutually_exclusive_dispatch_emits_diagnostic(capfd, arguments):
    """Mutually exclusive root dispatch tokens never fail silently."""
    from pyfcstm import _bootstrap

    assert _bootstrap.main(arguments) == 3
    captured = capfd.readouterr()
    assert "mutually exclusive" in captured.err


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
    assert payload["summary"] == {"ERROR": 1}
    assert "boom" in payload["results"][0]["evidence"]
    assert "checks" not in payload and "counts" not in payload
    assert payload["schema_version"] == "pyfcstm-selfcheck/v1"
    assert payload["exit_code"] == 3
    assert set(payload["results"][0]) == {
        "id",
        "group",
        "title",
        "status",
        "required",
        "duration_ms",
        "summary",
        "reason",
        "expected",
        "observed",
        "evidence",
        "remediation",
        "prerequisite",
        "exception",
        "pid",
        "returncode",
        "signal",
        "ntstatus",
        "timeout",
        "transport",
        "stdout",
        "stderr",
        "encoding",
        "truncated_bytes",
    }


@pytest.mark.unittest
def test_requested_output_format_respects_option_values_and_separator():
    """Emergency format detection does not scan consumed values or ``--`` args."""
    from pyfcstm import _bootstrap

    assert _bootstrap._requested_output_format(("--format", "json")) == "json"
    assert _bootstrap._requested_output_format(("--report", "--format=json")) == "human"
    assert _bootstrap._requested_output_format(("--", "--format=json")) == "human"


@pytest.mark.unittest
def test_selfcheck_help_is_available_before_click(capsys):
    """The self-check options have a dedicated help path before Click."""
    from pyfcstm import _bootstrap

    assert _bootstrap.main(("--self-check", "--help")) == 0
    output = capsys.readouterr().out
    assert "pyfcstm --self-check" in output
    assert "--profile" in output
    assert "--self-check-worker" not in output


@pytest.mark.unittest
def test_hidden_worker_help_is_available_before_click(capsys):
    """The private worker entry point documents its protocol options."""
    from pyfcstm import _bootstrap

    assert _bootstrap.main(("--self-check-worker", "--help")) == 0
    output = capsys.readouterr().out
    assert "pyfcstm --self-check-worker" in output
    assert "internal entry point" in output
    assert "--check-id" in output
    assert "--result-mode" in output


@pytest.mark.unittest
def test_public_selfcheck_dispatch_runs_the_real_supervisor(capsys):
    """The public bootstrap path executes real local and isolated checks."""
    from pyfcstm import _bootstrap

    assert _bootstrap.main(("--self-check", "--format", "json")) == 0
    payload = json.loads(capsys.readouterr().out)
    assert payload["exit_code"] == 0
    assert [item["status"] for item in payload["results"]] == ["PASS", "PASS"]


class _BinaryTextStream:
    """Minimal text facade exposing the binary stream used by the protocol."""

    def __init__(self, data=b""):
        self.buffer = io.BytesIO(data)

    def write(self, value):
        return self.buffer.write(value.encode("utf-8"))

    def flush(self):
        return None


def _closed_stdout():
    """Return a stdout facade whose binary and text writes fail."""

    def fail(*args):
        del args
        raise OSError("closed")

    return SimpleNamespace(
        buffer=SimpleNamespace(write=fail, flush=fail),
        write=fail,
        flush=fail,
    )


@pytest.mark.unittest
def test_public_worker_dispatch_runs_real_registry_callback(monkeypatch):
    """The hidden dispatch accepts the real nonce gate and emits one frame."""
    from pyfcstm import _bootstrap
    from pyfcstm._selfcheck.protocol import build_start_gate, read_stdout_frames

    nonce = "a" * 32
    stdin = _BinaryTextStream(build_start_gate(nonce))
    stdout = _BinaryTextStream()
    monkeypatch.setattr(sys, "stdin", stdin)
    monkeypatch.setattr(sys, "stdout", stdout)

    assert (
        _bootstrap.main(
            (
                "--self-check-worker",
                "--check-id",
                "runtime.metadata",
                "--worker-key",
                "runtime_metadata",
                "--nonce",
                nonce,
                "--result-mode",
                "stdout",
            )
        )
        == 0
    )
    outcome = read_stdout_frames(stdout.buffer.getvalue(), nonce, "runtime.metadata")
    assert outcome.envelope["status"] == "PASS"


@pytest.mark.unittest
def test_public_worker_dispatch_rejects_invalid_arguments(capsys):
    """Malformed hidden-worker input returns the stable protocol exit code."""
    from pyfcstm import _bootstrap

    assert _bootstrap.main(("--self-check-worker", "--check-id", "missing")) == 3
    assert "error" in capsys.readouterr().err.lower()


@pytest.mark.unittest
def test_public_bootstrap_version_and_ordinary_cli_routes(capsys):
    """Version and ordinary command routes remain available beside self-check."""
    from pyfcstm import _bootstrap

    assert _bootstrap.main(("--version",)) == 0
    assert "Revision:" in capsys.readouterr().out
    assert _bootstrap.main(("--version", "extra")) == 2
    with pytest.raises(SystemExit) as exited:
        _bootstrap.main(("--help",))
    assert exited.value.code == 0
    assert "Usage:" in capsys.readouterr().out or "Commands" in capsys.readouterr().out


@pytest.mark.unittest
def test_public_bootstrap_reports_human_failure_when_stdout_is_unavailable(
    monkeypatch, capfd
):
    """The final bootstrap boundary falls through to stderr without raising."""
    from pyfcstm import _bootstrap

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("broken bootstrap")),
    )
    with contextlib.redirect_stdout(_closed_stdout()):
        assert _bootstrap.main(("--self-check",)) == 3
    assert "broken bootstrap" in capfd.readouterr().err


@pytest.mark.unittest
def test_public_bootstrap_emergency_temp_file_is_last_resort(monkeypatch, tmp_path):
    """The public boundary persists diagnostics when stderr and fd two fail."""
    from pyfcstm import _bootstrap

    class Broken:
        buffer = None

        def write(self, value):
            del value
            raise OSError("stream closed")

        def flush(self):
            raise OSError("stream closed")

    destination = tmp_path / "emergency.log"
    real_write = _bootstrap.os.write

    def write(fd, data):
        if fd == 2:
            raise OSError("fd closed")
        return real_write(fd, data)

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("fatal")),
    )
    monkeypatch.setattr(_bootstrap.sys, "stderr", Broken())
    monkeypatch.setattr(_bootstrap.os, "write", write)
    monkeypatch.setattr(
        _bootstrap.tempfile,
        "mkstemp",
        lambda **kwargs: (
            _bootstrap.os.open(
                str(destination), _bootstrap.os.O_CREAT | _bootstrap.os.O_WRONLY
            ),
            str(destination),
        ),
    )

    assert _bootstrap.main(("--self-check",)) == 3
    assert "fatal" in destination.read_text(encoding="utf-8")


@pytest.mark.unittest
def test_public_bootstrap_broken_pipe_keeps_emergency_boundary(monkeypatch, capfd):
    """A public EPIPE result is silenced before interpreter shutdown."""
    from pyfcstm import _bootstrap

    class Broken:
        def write(self, value):
            del value
            raise BrokenPipeError("closed")

        def flush(self):
            return None

        def fileno(self):
            return -1

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(BrokenPipeError("closed")),
    )
    with contextlib.redirect_stdout(Broken()):
        assert _bootstrap.main(("--self-check",)) == 3
    assert "BrokenPipeError" in capfd.readouterr().err


@pytest.mark.unittest
def test_public_bootstrap_json_fallback_handles_unavailable_text_and_stderr(
    monkeypatch,
):
    """JSON diagnostics survive binary/text stdout and stderr failures."""
    from pyfcstm import _bootstrap

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("broken bootstrap")),
    )
    monkeypatch.setattr(
        _bootstrap,
        "os",
        type(
            "BrokenOS",
            (),
            {
                "write": staticmethod(
                    lambda fd, data: (_ for _ in ()).throw(OSError("closed"))
                )
            },
        )(),
    )
    with contextlib.redirect_stdout(_closed_stdout()):
        assert _bootstrap.main(("--self-check", "--format", "json")) == 3

    import os

    fallback_text = []

    def fail_binary(*args):
        del args
        raise OSError("binary stream closed")

    fallback_stdout = SimpleNamespace(
        buffer=SimpleNamespace(write=fail_binary, flush=fail_binary),
        write=fallback_text.append,
        flush=lambda: None,
    )
    monkeypatch.setattr(_bootstrap, "os", os)
    with contextlib.redirect_stdout(fallback_stdout):
        assert _bootstrap.main(("--self-check", "--format", "json")) == 3
    assert '"schema_version":"pyfcstm-selfcheck/v1"' in "".join(fallback_text)


@pytest.mark.unittest
def test_guarded_bootstrap_preserves_control_sentinels(monkeypatch):
    """KeyboardInterrupt and non-runtime sentinels are not mislabeled errors."""
    from pyfcstm import _bootstrap

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(KeyboardInterrupt()),
    )
    assert _bootstrap.main(("--self-check",)) == 130

    monkeypatch.setattr(
        _bootstrap, "run_selfcheck", lambda args: (_ for _ in ()).throw(GeneratorExit())
    )
    with pytest.raises(GeneratorExit):
        _bootstrap.main(("--self-check",))


@pytest.mark.unittest
def test_version_formatter_reports_all_build_identity_fields(monkeypatch):
    """Available revision, commit, and UTC build fields appear in version text."""
    from pyfcstm import _bootstrap

    monkeypatch.setattr(_bootstrap, "BUILD_REVISION", "r" * 40)
    monkeypatch.setattr(_bootstrap, "BUILD_COMMIT", "c" * 40)
    monkeypatch.setattr(_bootstrap, "BUILD_TIME_UTC", "2026-07-14T00:00:00Z")
    output = _bootstrap.format_version_info()
    assert "Revision: " + "r" * 40 in output
    assert "Commit: " + "c" * 40 in output
    assert "Built: 2026-07-14T00:00:00Z" in output

    monkeypatch.setattr(_bootstrap, "BUILD_REVISION", None)
    assert "Revision: unavailable" in _bootstrap.format_version_info()


@pytest.mark.unittest
def test_public_bootstrap_returns_after_ordinary_cli_dispatch(monkeypatch):
    """A normal command delegates to Click and returns when it does."""
    from pyfcstm import _bootstrap
    from pyfcstm import entry

    invoked = []
    monkeypatch.setattr(
        entry,
        "pyfcstmcli",
        lambda **kwargs: invoked.append(kwargs),
    )
    assert _bootstrap.main(("status",)) == 0
    assert invoked == [{"args": ["status"], "prog_name": "pyfcstm"}]

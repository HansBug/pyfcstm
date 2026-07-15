"""Tests for pre-Click self-check bootstrap dispatch."""

import io
import json
import os
import subprocess
import sys
import contextlib
from pathlib import Path
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
def test_bootstrap_emits_human_header_before_supervisor_work(monkeypatch, capsys):
    """Human self-check mode reports startup before the supervisor runs."""
    from pyfcstm import _bootstrap
    from pyfcstm._selfcheck import supervisor

    observed = {}

    def fake_supervisor(arguments, start_emitted=False):
        observed["arguments"] = tuple(arguments)
        observed["start_emitted"] = start_emitted
        observed["output"] = capsys.readouterr().out
        return 0

    monkeypatch.setattr(supervisor, "run_supervisor", fake_supervisor)
    assert _bootstrap.run_selfcheck(("--profile", "full", "--color", "never")) == 0
    assert observed["start_emitted"] is True
    assert observed["arguments"] == ("--profile", "full", "--color", "never")
    assert observed["output"].startswith("pyfcstm self-check 0.6.0")
    assert "profile=full" in observed["output"]


@pytest.mark.unittest
def test_bootstrap_keeps_json_output_machine_readable(monkeypatch, capsys):
    """JSON mode does not receive the human startup line."""
    from pyfcstm import _bootstrap
    from pyfcstm._selfcheck import supervisor

    monkeypatch.setattr(supervisor, "run_supervisor", lambda args, start_emitted=False: 0)
    assert _bootstrap.run_selfcheck(("--format", "json")) == 0
    assert capsys.readouterr().out == ""


@pytest.mark.unittest
def test_bootstrap_option_peek_respects_argument_separator():
    """The early header probe does not inspect values after ``--``."""
    from pyfcstm import _bootstrap

    assert (
        _bootstrap._peek_selfcheck_option(
            ("--", "--profile=full"), "--profile", "default"
        )
        == "default"
    )


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
    assert "Traceback (most recent call last)" in payload["results"][0]["evidence"]
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
def test_bootstrap_renderer_failure_keeps_traceback_in_canonical_json(
    monkeypatch, capsys
):
    """A final renderer failure retains its traceback in the emergency result."""
    from pyfcstm import _bootstrap
    from pyfcstm._selfcheck import supervisor

    def fail_renderer(snapshot):
        del snapshot
        raise RuntimeError("renderer failed")

    monkeypatch.setattr(supervisor, "render_json", fail_renderer)
    assert _bootstrap.main(("--self-check", "--format", "json")) == 3
    payload = json.loads(capsys.readouterr().out)
    evidence = payload["results"][0]["evidence"]
    assert "renderer failed" in evidence
    assert "Traceback (most recent call last)" in evidence


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
    from pyfcstm._selfcheck.registry import EXPECTED_CHECK_IDS

    assert [item["id"] for item in payload["results"]] == [
        "runtime.metadata",
        *EXPECTED_CHECK_IDS,
    ]
    assert all(item["status"] in ("PASS", "WARN", "SKIP") for item in payload["results"])


@pytest.mark.unittest
def test_module_entry_runs_public_selfcheck_in_a_fresh_process():
    """The installed module entry completes self-check without test doubles."""
    repository_root = Path(__file__).resolve().parents[2]
    environment = os.environ.copy()
    inherited_pythonpath = environment.get("PYTHONPATH")
    environment["PYTHONPATH"] = os.pathsep.join(
        item for item in (str(repository_root), inherited_pythonpath) if item
    )
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "pyfcstm",
            "--self-check",
            "--format",
            "json",
            "--color",
            "never",
        ],
        cwd=str(repository_root),
        env=environment,
        capture_output=True,
        text=True,
        # The full serial registry is materially slower on Windows/Python 3.8.
        timeout=120,
    )
    assert result.returncode == 0
    payload = json.loads(result.stdout)
    assert payload["schema_version"] == "pyfcstm-selfcheck/v1"
    assert payload["exit_code"] == 0
    from pyfcstm._selfcheck.registry import EXPECTED_CHECK_IDS

    assert [item["id"] for item in payload["results"]] == [
        "runtime.metadata",
        *EXPECTED_CHECK_IDS,
    ]
    assert all(item["status"] in ("PASS", "WARN", "SKIP") for item in payload["results"])
    assert result.stderr == ""


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

    def write_text(value):
        fallback_text.append(value)
        return len(value)

    fallback_stdout = SimpleNamespace(
        write=write_text,
        flush=lambda: None,
    )
    monkeypatch.setattr(_bootstrap, "os", os)
    with contextlib.redirect_stdout(fallback_stdout):
        assert _bootstrap.main(("--self-check", "--format", "json")) == 3
    assert '"schema_version":"pyfcstm-selfcheck/v1"' in "".join(fallback_text)


@pytest.mark.unittest
def test_public_bootstrap_json_fallback_reports_text_stdout_failure(monkeypatch):
    """A text-only stdout failure still reaches the emergency channel."""
    from pyfcstm import _bootstrap

    def fail(*args):
        del args
        raise OSError("text stdout closed")

    stderr = _BinaryTextStream()
    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("text fallback")),
    )
    monkeypatch.setattr(
        _bootstrap,
        "sys",
        SimpleNamespace(
            stdout=SimpleNamespace(write=fail, flush=fail),
            stderr=stderr,
        ),
    )

    assert _bootstrap.main(("--self-check", "--format", "json")) == 3
    assert b"text fallback" in stderr.buffer.getvalue()


@pytest.mark.unittest
def test_public_bootstrap_does_not_append_json_after_binary_short_write(
    monkeypatch, capfd
):
    """A binary stdout short write falls through without a second JSON prefix."""
    from pyfcstm import _bootstrap

    class PartialBinary:
        def __init__(self):
            self.data = bytearray()
            self.calls = 0

        def write(self, value):
            self.calls += 1
            if self.calls > 1:
                return 0
            self.data.extend(value[:7])
            return 7

        def flush(self):
            return None

    binary = PartialBinary()
    stderr = io.BytesIO()
    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("partial bootstrap")),
    )
    monkeypatch.setattr(
        _bootstrap,
        "sys",
        SimpleNamespace(
            stdout=SimpleNamespace(buffer=binary),
            stderr=SimpleNamespace(buffer=stderr),
        ),
    )
    assert _bootstrap.main(("--self-check", "--format", "json")) == 3
    assert bytes(binary.data).count(b'{"schema_version"') == 0
    assert b"partial bootstrap" in stderr.getvalue()


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

    monkeypatch.setattr(_bootstrap, "BUILD_COMMIT", None)
    monkeypatch.setattr(_bootstrap, "BUILD_TIME_UTC", None)
    output = _bootstrap.format_version_info()
    assert "Commit:" not in output
    assert "Built:" not in output


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


@pytest.mark.unittest
def test_public_main_uses_raw_stderr_fd_when_stderr_stream_is_broken(monkeypatch):
    """The module entry point keeps diagnostics observable after stream failure."""
    from pyfcstm import _bootstrap
    from pyfcstm.__main__ import main

    class BrokenStderr:
        buffer = None

        def write(self, value):
            del value
            raise OSError("stderr closed")

        def flush(self):
            raise OSError("stderr closed")

    writes = []

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("raw fd fallback")),
    )
    monkeypatch.setattr(_bootstrap.sys, "stderr", BrokenStderr())
    monkeypatch.setattr(
        _bootstrap.os,
        "write",
        lambda descriptor, data: writes.append((descriptor, data)) or len(data),
    )

    assert main(("--self-check",)) == 3
    assert writes and writes[0][0] == 2
    assert b"raw fd fallback" in writes[0][1]


@pytest.mark.unittest
def test_public_main_survives_short_raw_stderr_write(monkeypatch):
    """A zero-byte raw diagnostic write falls through without escaping."""
    from pyfcstm import _bootstrap
    from pyfcstm.__main__ import main

    class BrokenStderr:
        buffer = None

        def write(self, value):
            del value
            raise OSError("stderr closed")

        def flush(self):
            raise OSError("stderr closed")

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("short raw write")),
    )
    monkeypatch.setattr(_bootstrap.sys, "stderr", BrokenStderr())
    monkeypatch.setattr(_bootstrap.os, "write", lambda descriptor, data: 0)
    monkeypatch.setattr(
        _bootstrap.tempfile,
        "mkstemp",
        lambda **kwargs: (_ for _ in ()).throw(OSError("temp unavailable")),
    )

    assert main(("--self-check",)) == 3


@pytest.mark.unittest
def test_public_main_survives_unwritable_emergency_temp_file(monkeypatch, tmp_path):
    """The final diagnostic boundary also survives temp-file and unlink failures."""
    import os

    from pyfcstm import _bootstrap
    from pyfcstm.__main__ import main

    class BrokenStderr:
        buffer = None

        def write(self, value):
            del value
            raise OSError("stderr closed")

        def flush(self):
            raise OSError("stderr closed")

    destination = tmp_path / "emergency.log"
    unlink_attempts = []

    def make_temp_file(**kwargs):
        del kwargs
        return os.open(str(destination), os.O_CREAT | os.O_WRONLY), str(destination)

    def fail_write(descriptor, data):
        del descriptor, data
        raise OSError("emergency file closed")

    def fail_unlink(path):
        unlink_attempts.append(path)
        raise OSError("unlink denied")

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(RuntimeError("unrecoverable")),
    )
    monkeypatch.setattr(_bootstrap.sys, "stderr", BrokenStderr())
    monkeypatch.setattr(_bootstrap.os, "write", fail_write)
    monkeypatch.setattr(_bootstrap.tempfile, "mkstemp", make_temp_file)
    monkeypatch.setattr(_bootstrap.os, "unlink", fail_unlink)

    assert main(("--self-check",)) == 3
    assert unlink_attempts == [str(destination)]


@pytest.mark.unittest
def test_public_main_ignores_devnull_close_failure(monkeypatch):
    """A failure while closing the EPIPE replacement cannot abort diagnostics."""
    import contextlib

    from pyfcstm import _bootstrap
    from pyfcstm.__main__ import main

    class BrokenStdout:
        def write(self, value):
            del value
            raise BrokenPipeError("stdout closed")

        def flush(self):
            return None

        def fileno(self):
            return 41

    real_close = _bootstrap.os.close
    closed = []

    def close(descriptor):
        closed.append(descriptor)
        if descriptor == 42:
            raise OSError("replacement close failed")
        return real_close(descriptor)

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(BrokenPipeError("stdout closed")),
    )
    monkeypatch.setattr(_bootstrap.os, "open", lambda path, flags: 42)
    monkeypatch.setattr(_bootstrap.os, "dup2", lambda source, target: None)
    monkeypatch.setattr(_bootstrap.os, "close", close)

    with contextlib.redirect_stdout(BrokenStdout()):
        assert main(("--self-check",)) == 3
    assert closed == [42]


@pytest.mark.unittest
def test_public_main_handles_devnull_reusing_stdout_descriptor(monkeypatch):
    """An EPIPE replacement that reuses stdout needs no duplicate close."""
    from pyfcstm import _bootstrap
    from pyfcstm.__main__ import main

    class BrokenStdout:
        def write(self, value):
            del value
            raise BrokenPipeError("stdout closed")

        def flush(self):
            return None

        def fileno(self):
            return 41

    monkeypatch.setattr(
        _bootstrap,
        "run_selfcheck",
        lambda args: (_ for _ in ()).throw(BrokenPipeError("stdout closed")),
    )

    def reuse_stdout(path, flags):
        del path, flags
        return 41

    def unexpected_dup2(source, target):
        del source, target
        raise AssertionError("same descriptor must not be duplicated")

    monkeypatch.setattr(
        _bootstrap,
        "os",
        SimpleNamespace(
            devnull=os.devnull,
            O_WRONLY=os.O_WRONLY,
            open=reuse_stdout,
            dup2=unexpected_dup2,
            close=os.close,
        ),
    )

    stderr = _BinaryTextStream()
    with contextlib.redirect_stdout(BrokenStdout()), contextlib.redirect_stderr(stderr):
        assert main(("--self-check",)) == 3
    assert not sys.stdout.closed
    assert b"BrokenPipeError" in stderr.buffer.getvalue()

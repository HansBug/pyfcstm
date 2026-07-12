"""Coverage for the ``python -m pyfcstm`` bootstrap entry point."""

import subprocess
import sys

import pytest

import pyfcstm.__main__ as main_module


@pytest.mark.unittest
class TestMainModule:
    def test_main_module_exposes_bootstrap(self):
        """``__main__`` re-exports the standard-library bootstrap callable."""
        from pyfcstm._bootstrap import main

        assert main_module.main is main

    def test_main_module_invocation_runs_cli(self):
        """``python -m pyfcstm --help`` runs the CLI and exits cleanly."""
        result = subprocess.run(
            [sys.executable, "-m", "pyfcstm", "--help"],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Usage:" in result.stdout or "Commands" in result.stdout

    def test_main_module_runpy_executes_bootstrap_branch(self, monkeypatch):
        """Run the module branch with a recording bootstrap implementation."""
        import runpy

        invoked = []

        def _record_main(*args, **kwargs):
            invoked.append((args, kwargs))
            return 0

        from pyfcstm import _bootstrap

        monkeypatch.setattr(_bootstrap, "main", _record_main)
        with pytest.raises(SystemExit) as captured:
            runpy.run_module("pyfcstm", run_name="__main__", alter_sys=False)
        assert captured.value.code == 0
        assert invoked, "bootstrap should have been called via __main__"

    def test_module_version_does_not_import_click(self):
        """A root version request completes before normal CLI imports."""
        result = subprocess.run(
            [
                sys.executable,
                "-c",
                "import sys; from pyfcstm._bootstrap import main; "
                "code = main(['--version']); "
                "raise SystemExit(code if 'click' not in sys.modules and "
                "'pyfcstm.entry' not in sys.modules else 99)",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Revision:" in result.stdout

    @pytest.mark.parametrize(
        ("arguments", "expected"),
        [
            (("-v",), True),
            (("-V",), True),
            (("--version",), True),
            ((), False),
            (("--version", "bmc"), False),
            (("bmc",), False),
        ],
    )
    def test_version_request_detection_is_exact(self, arguments, expected):
        """Only one root version flag bypasses the ordinary CLI graph."""
        from pyfcstm._bootstrap import is_version_request

        assert is_version_request(arguments) is expected

    def test_bootstrap_dispatches_non_version_commands(self, monkeypatch):
        """Ordinary commands still use the established Click entry point."""
        from pyfcstm import _bootstrap
        from pyfcstm import entry

        invoked = []

        def _record_cli(args, prog_name):
            invoked.append((args, prog_name))

        monkeypatch.setattr(entry, "pyfcstmcli", _record_cli)

        assert _bootstrap.main(("bmc", "--help")) == 0
        assert invoked == [(["bmc", "--help"], "pyfcstm")]

    def test_version_formatter_includes_available_identity(self, monkeypatch):
        """Build identity lines appear only when a build supplied them."""
        from pyfcstm import _bootstrap

        monkeypatch.setattr(_bootstrap, "BUILD_REVISION", "a" * 40)
        monkeypatch.setattr(_bootstrap, "BUILD_COMMIT", "a" * 40)
        monkeypatch.setattr(_bootstrap, "BUILD_TIME_UTC", "2026-07-12T00:00:00Z")

        output = _bootstrap.format_version_info()

        assert "Revision: " + "a" * 40 in output
        assert "Commit: " + "a" * 40 in output
        assert "Built: 2026-07-12T00:00:00Z" in output

    def test_bootstrap_prints_root_version_request(self, capsys):
        """A direct version request prints and returns before CLI dispatch."""
        from pyfcstm import _bootstrap

        assert _bootstrap.main(("--version",)) == 0
        assert "Revision:" in capsys.readouterr().out

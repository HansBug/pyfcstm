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
                "raise SystemExit(main(['--version']) if 'click' not in sys.modules else 99)",
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert "Revision:" in result.stdout

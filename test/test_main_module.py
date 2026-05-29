"""
Coverage for ``python -m pyfcstm`` entry point.

The ``__main__.py`` module dispatches to :func:`pyfcstm.entry.pyfcstmcli`
when invoked as a script. We exercise it by importing the module and by
running the ``-m`` invocation in a subprocess for the ``__name__ ==
'__main__'`` branch.
"""
import subprocess
import sys

import pytest

import pyfcstm.__main__ as main_module


@pytest.mark.unittest
class TestMainModule:
    def test_main_module_exposes_cli(self):
        """``__main__`` re-exports the documented CLI entry callable."""
        from pyfcstm.entry import pyfcstmcli

        assert main_module.pyfcstmcli is pyfcstmcli

    def test_main_module_invocation_runs_cli(self):
        """``python -m pyfcstm --help`` runs the CLI and exits cleanly."""
        result = subprocess.run(
            [sys.executable, '-m', 'pyfcstm', '--help'],
            capture_output=True,
            text=True,
            timeout=30,
        )
        assert result.returncode == 0
        assert 'Usage:' in result.stdout or 'Commands' in result.stdout

    def test_main_module_runpy_executes_cli_branch(self, monkeypatch):
        """Use runpy to execute the ``__main__`` block in-process so the
        ``pyfcstmcli()`` call on line 21 shows up in coverage. We replace
        the bound name with a recording stub so we don't actually run the
        CLI dispatcher (which would hit sys.exit)."""
        import runpy

        invoked = []

        def _record_cli(*args, **kwargs):
            invoked.append((args, kwargs))

        # runpy will re-import the module and bind a fresh ``pyfcstmcli``
        # name from pyfcstm.entry. Patch the source of that import so the
        # name resolves to our recorder.
        from pyfcstm import entry as _entry
        monkeypatch.setattr(_entry, 'pyfcstmcli', _record_cli)
        runpy.run_module('pyfcstm', run_name='__main__', alter_sys=False)
        assert invoked, 'pyfcstmcli should have been called via __main__'

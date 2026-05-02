"""PyInstaller entry script.

Mirrors ``pyfcstm/__main__.py``: short-circuits ``--smoke-test`` to
``pyfcstm.diagnostics`` before importing the regular CLI subcommand
chain, so a broken install can still produce a structured diagnostics
report instead of an opaque ImportError.
"""
import sys


def _maybe_smoke_short_circuit() -> None:
    if "--smoke-test" not in sys.argv:
        return
    try:
        from pyfcstm.diagnostics.__main__ import main as _smoke_main
    except BaseException as exc:  # pragma: no cover - last-ditch fallback
        sys.stderr.write(
            "[FATAL] could not import pyfcstm.diagnostics: {!r}\n".format(exc)
        )
        sys.exit(2)
    sys.exit(_smoke_main())


_maybe_smoke_short_circuit()

from pyfcstm.entry import pyfcstmcli  # noqa: E402 - intentional after the short-circuit

if __name__ == '__main__':
    pyfcstmcli()

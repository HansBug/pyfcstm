"""
Command-line entry point for the :mod:`pyfcstm` package.

This module exposes the console entry point that launches the CLI
implementation provided by :func:`pyfcstm.entry.pyfcstmcli`. When the module
is executed as a script, it invokes the CLI handler.

Before the regular CLI machinery is imported, this entry checks for the
``--smoke-test`` flag in :data:`sys.argv` and short-circuits straight to
:mod:`pyfcstm.diagnostics`. The point of ``--smoke-test`` is to be the
last line of defence when the rest of the install is broken; importing
the full subcommand chain first would let, for example, a missing ANTLR
grammar file explode before the smoke runner could ever print a single
``[FAIL]`` row.

The module contains the following main components:

* :func:`pyfcstm.entry.pyfcstmcli` - CLI handler invoked on script execution

Example::

    >>> # Execute via Python module invocation
    >>> # python -m pyfcstm
    >>> # python -m pyfcstm --smoke-test   (short-circuits to diagnostics)

"""
import sys


def _maybe_smoke_short_circuit() -> None:
    """Run ``pyfcstm.diagnostics`` and exit, when ``--smoke-test`` is present.

    This intentionally avoids importing :mod:`pyfcstm.entry` so a broken
    subcommand module (e.g. due to a missing ANTLR-generated file or a
    busted optional extra) does not prevent the diagnostics runner from
    starting. The diagnostics package only depends on the Python standard
    library and on the lightweight :mod:`pyfcstm` package ``__init__``.
    """
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

from .entry import pyfcstmcli  # noqa: E402 - intentional after the short-circuit

if __name__ == '__main__':
    pyfcstmcli()

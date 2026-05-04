"""
Stand-alone CLI entry for ``python -m pyfcstm.diagnostics``.

This entry deliberately bypasses :mod:`pyfcstm.entry.cli` and the entire
subcommand chain. ``--smoke-test`` is the last line of defence when
something is broken with the install; if the regular console-script
entry imported subcommand modules first, a busted ``pyfcstm.dsl.grammar``
(missing generated files, ANTLR runtime mismatch, ...) would explode at
import time before the smoke runner ever got a chance to print a single
diagnostic. Running diagnostics through this module avoids that
chicken-and-egg problem because :mod:`pyfcstm.diagnostics` only depends
on the Python standard library and on :mod:`pyfcstm` itself, whose
``__init__`` is a one-line version export.

Usage::

    python -m pyfcstm.diagnostics            # alias for --smoke-test
    python -m pyfcstm.diagnostics --smoke-test
"""

from __future__ import annotations

import sys


def main() -> int:
    """Drive the smoke runner, swallowing every conceivable failure.

    Returns the count of failed cases (``0`` = clean install). On
    catastrophic runner-level failures (the smoke runner itself can't be
    imported or raises despite its internal isolation), prints a single
    structured FATAL line and returns a distinct non-zero exit code so
    automation can tell apart "the runner ran and N cases failed" from
    "we never got to a runner".
    """
    try:
        from pyfcstm.diagnostics import run_smoke_test
    except BaseException as exc:  # pragma: no cover - we *are* the fallback
        sys.stderr.write(
            "[FATAL] could not import pyfcstm.diagnostics: {!r}\n"
            "        This usually means the wheel was installed with a "
            "broken module layout. Try `pip install --force-reinstall pyfcstm`.\n".format(
                exc
            )
        )
        return 2
    try:
        return run_smoke_test()
    except BaseException as exc:  # pragma: no cover - the runner is supposed to never raise
        sys.stderr.write(
            "[FATAL] smoke runner raised: {!r}\n"
            "        File this as a pyfcstm bug; the runner is supposed "
            "to always finish.\n".format(exc)
        )
        return 3


if __name__ == "__main__":
    sys.exit(main())

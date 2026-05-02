"""
Diagnostic utilities for the :mod:`pyfcstm` package.

The diagnostics surface is built around :func:`run_smoke_test`, which runs
a battery of independent self-checks covering imports, native dependencies
(``z3-solver``, ``py-mini-racer`` / ``mini-racer``), bundled static assets
(JS render bundle, built-in template archives, ANTLR grammar resources),
and the minimum end-to-end paths through the parser, model layer,
expression renderer, simulator, and SysDeSim CLI pipelines.

The runner is designed to be the **last line of defence** when the user
hits a broken installation: every case is isolated, exceptions never
escape the runner, and the worst-case output still tells a human or LLM
exactly what is missing and why.

Example::

    >>> from pyfcstm.diagnostics import run_smoke_test
    >>> exit_code = run_smoke_test()  # doctest: +SKIP

The module contains:

* :func:`run_smoke_test` - Public entry that walks every registered
  smoke case and prints a colored PASS/FAIL summary.
"""

from .smoke import run_smoke_test

__all__ = ["run_smoke_test"]

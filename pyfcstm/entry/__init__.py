"""
Entry points for the :mod:`pyfcstm.entry` package.

This package exposes the command-line interface (CLI) entry point for the
``pyfcstm`` application. The primary public object is the CLI group imported
as :data:`pyfcstmcli`, which can be used to invoke CLI commands programmatically
or to register it with external tooling.

The package contains the following main components:

.. list-table::
   :header-rows: 1

   * - Entry
     - Purpose
   * - :data:`pyfcstmcli`
     - CLI group object for the ``pyfcstm`` command-line tool.
   * - :func:`build_bmc_output`
     - Run one BMC model/query pair and build a human or JSON report.
   * - :func:`write_bmc_output`
     - Atomically replace a file with a completed BMC report.

Example::

    >>> from pyfcstm.entry import pyfcstmcli
    >>> # The object is typically used by CLI frameworks.
    >>> # Actual invocation is usually handled by the CLI framework itself.

.. note::
   The underlying CLI implementation is defined in :mod:`pyfcstm.entry.cli`.
   This package module merely re-exports the CLI group for convenience.

"""

from .cli import cli as pyfcstmcli
from .bmc import build_bmc_output, write_bmc_output

__all__ = ["pyfcstmcli", "build_bmc_output", "write_bmc_output"]

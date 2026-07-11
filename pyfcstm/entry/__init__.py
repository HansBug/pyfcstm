"""
Entry points for the :mod:`pyfcstm.entry` package.

This package exposes the command-line interface (CLI) entry point for the
``pyfcstm`` application. The primary public object is the CLI group imported
as :data:`pyfcstmcli`, which can be used to invoke CLI commands programmatically
or to register it with external tooling.

Module roadmap
--------------

.. list-table::
   :header-rows: 1

   * - Module
     - Responsibility
   * - :mod:`pyfcstm.entry.cli`
     - Builds the root Click command group exported as :data:`pyfcstmcli`.
   * - :mod:`pyfcstm.entry.inspect`
     - Produces human-readable and structured model diagnostics.
   * - :mod:`pyfcstm.entry.generate`
     - Generates target-language artifacts from custom or built-in templates.
   * - :mod:`pyfcstm.entry.plantuml`
     - Exports FCSTM models as PlantUML source.
   * - :mod:`pyfcstm.entry.visualize`
     - Renders PlantUML source to image files and optionally opens them.
   * - :mod:`pyfcstm.entry.simulate`
     - Provides batch and interactive simulation commands.

Example::

    >>> from pyfcstm.entry import pyfcstmcli
    >>> # The object is typically used by CLI frameworks.
    >>> # Actual invocation is usually handled by the CLI framework itself.

.. note::
   The underlying CLI implementation is defined in :mod:`pyfcstm.entry.cli`.
   This package module merely re-exports the CLI group for convenience.
"""

from .cli import cli as pyfcstmcli

__all__ = ["pyfcstmcli"]

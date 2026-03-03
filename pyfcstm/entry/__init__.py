"""
Entry points for the :mod:`pyfcstm.entry` package.

This package exposes the command-line interface (CLI) entry point for the
``pyfcstm`` application. The primary public object is the CLI group imported
as :data:`pyfcstmcli`, which can be used to invoke CLI commands programmatically
or to register it with external tooling.

The package contains the following main components:

* :data:`pyfcstmcli` - CLI group object for the ``pyfcstm`` command-line tool

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

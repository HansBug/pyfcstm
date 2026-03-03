"""
Command-line entry point for the :mod:`pyfcstm` package.

This module exposes the console entry point that launches the CLI
implementation provided by :func:`pyfcstm.entry.pyfcstmcli`. When the module
is executed as a script, it invokes the CLI handler.

The module contains the following main components:

* :func:`pyfcstm.entry.pyfcstmcli` - CLI handler invoked on script execution

Example::

    >>> # Execute via Python module invocation
    >>> # python -m pyfcstm

"""
from .entry import pyfcstmcli

if __name__ == '__main__':
    pyfcstmcli()

"""
Command-line entry point for the :mod:`pyfcstm` package.

This module delegates to the standard-library bootstrap in
:mod:`pyfcstm._bootstrap`. Root-level version requests can therefore report
build identity without importing Click or the normal CLI command graph.

Example::

    >>> # Execute via Python module invocation
    >>> # python -m pyfcstm

"""

from ._bootstrap import main

if __name__ == "__main__":
    raise SystemExit(main())

"""
PyFCSTM package namespace and version export.

This package provides the root namespace for the ``pyfcstm`` project and
exposes the package version via :data:`__version__`. It is intentionally
minimal, serving as a stable import point for version introspection and
future public exports.

The package currently provides the following public attribute:

* :data:`__version__` - The installed package version string

Example::

    >>> import pyfcstm
    >>> pyfcstm.__name__
    'pyfcstm'
    >>> pyfcstm.__version__

"""

from .config.meta import __VERSION__ as __version__

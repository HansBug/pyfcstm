"""
PyFCSTM package namespace and build identity exports.

The root namespace provides stable package version and optional build identity
attributes. A development checkout that has not generated build metadata still
exports every attribute with ``None`` identity values, so diagnostics and
version reporting can start without Git or third-party dependencies.

The package provides:

.. list-table::
   :header-rows: 1

   * - Attribute
     - Meaning
   * - :data:`__version__`
     - The package release version.
   * - :data:`__commit__`, :data:`__revision__`
     - Optional full Git object ID and human-facing build revision.
   * - :data:`__dirty__`, :data:`__build_time__`
     - Optional dirty-state flag and UTC build timestamp.

Example::

    >>> import pyfcstm
    >>> isinstance(pyfcstm.__version__, str)
    True
    >>> pyfcstm.__revision__ is None or isinstance(pyfcstm.__revision__, str)
    True
"""

from .config import (
    BUILD_COMMIT as __commit__,
    BUILD_DIRTY as __dirty__,
    BUILD_REVISION as __revision__,
    BUILD_TIME_UTC as __build_time__,
)
from .config.meta import __VERSION__ as __version__


__all__ = [
    "__version__",
    "__commit__",
    "__dirty__",
    "__revision__",
    "__build_time__",
]

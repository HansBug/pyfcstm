"""
Modeling package initialization and re-exports for the :mod:`pyfcstm.model` namespace.

This module aggregates public classes, expressions, and model utilities from
submodules to provide a convenient import surface for end users. It re-exports
base interfaces for AST and PlantUML serialization, as well as all public
symbols defined in the :mod:`pyfcstm.model.expr`, :mod:`pyfcstm.model.model`,
and :mod:`pyfcstm.model.plantuml` modules.

The following public components are defined directly in this module:

* :class:`AstExportable` - Abstract base class for AST serialization support
* :class:`PlantUMLExportable` - Abstract base class for PlantUML serialization support

Example::

    >>> from pyfcstm.model import AstExportable, PlantUMLExportable
    >>> isinstance(AstExportable(), AstExportable)
    True

.. note::
   This module re-exports names using ``from ... import *``. Refer to the
   :mod:`pyfcstm.model.expr`, :mod:`pyfcstm.model.model`, and
   :mod:`pyfcstm.model.plantuml` modules for detailed documentation of those symbols.
"""

from .base import AstExportable, PlantUMLExportable
from .expr import *
from .model import *
from .plantuml import *

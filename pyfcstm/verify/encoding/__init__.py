"""Verification encoding helpers for FCSTM runtime semantics.

The encoding package is an internal implementation layer used by
:mod:`pyfcstm.verify.algorithms`.  It translates FCSTM runtime semantics into
Z3 expressions, operation environments, initial-entry contexts, and lifecycle
condition points.  Public callers should normally use the algorithm functions
exported from :mod:`pyfcstm.verify` instead of importing these helpers.

Encoding map:

.. list-table::
   :header-rows: 1

   * - Module
     - Responsibility
     - Main consumers
   * - :mod:`pyfcstm.verify.encoding.expr`
     - Expression translation with runtime-definedness constraints.
     - Guard, effect, and lifecycle algorithms.
   * - :mod:`pyfcstm.verify.encoding.guard`
     - Transition guard translation and guard-domain extraction.
     - Guard and effect algorithms.
   * - :mod:`pyfcstm.verify.encoding.initial`
     - Declaration initializer constraints and root initial path contexts.
     - Forced-guard, lifecycle, and composite-initial algorithms.
   * - :mod:`pyfcstm.verify.encoding.operation`
     - Path-sensitive operation execution wrappers.
     - Effect and lifecycle algorithms.
   * - :mod:`pyfcstm.verify.encoding.trigger`
     - Event and guard trigger encoding for transitions.
     - Transition-shadow and composite-initial algorithms.
   * - :mod:`pyfcstm.verify.encoding.lifecycle`
     - First-cycle lifecycle operation and condition extraction.
     - Lifecycle algorithms.
   * - :mod:`pyfcstm.verify.encoding._core`
     - Shared implementation details re-exported by the thin topic modules.
     - Maintainers only.

Example::

    >>> from pyfcstm.verify.encoding import expr
    >>> # Topic modules expose helpers, but public checks live in pyfcstm.verify.
    >>> hasattr(expr, "_expr_z3_and_domains_or_result")
    True
"""

__all__ = [
    "expr",
    "guard",
    "initial",
    "lifecycle",
    "operation",
    "trigger",
]

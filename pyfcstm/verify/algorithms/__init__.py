"""Raw verification algorithm entry points.

This package groups raw verification algorithms by the model feature they
analyze.  Public callers should usually import the algorithms from
:mod:`pyfcstm.verify`, while this package documents the implementation layout
used by maintainers and by the registry.

Algorithm map:

.. list-table::
   :header-rows: 1

   * - Module
     - Algorithms
     - Checks
   * - :mod:`pyfcstm.verify.algorithms.guard`
     - :func:`dead_guard`, :func:`guard_tautology`,
       :func:`forced_guard_unsat_under_init`
     - Guard satisfiability, guard validity, and forced guard feasibility
       under declaration initial values.
   * - :mod:`pyfcstm.verify.algorithms.effect`
     - :func:`effect_no_op_under_guard`, :func:`effect_contradicts_guard`
     - Transition effect observability and post-effect guard consistency.
   * - :mod:`pyfcstm.verify.algorithms.transition`
     - :func:`transition_shadowed_by_predecessor`,
       :func:`composite_init_guards_incomplete`
     - Declaration-order trigger coverage and composite initial-transition
       input coverage.
   * - :mod:`pyfcstm.verify.algorithms.lifecycle`
     - :func:`enter_postcondition_implies_during_precondition`
     - First-cycle ``enter`` / ``during`` condition determinacy.

Example::

    >>> from pyfcstm.verify import dead_guard
    >>> from pyfcstm.verify.algorithms import dead_guard as grouped_dead_guard
    >>> # The grouped package re-exports the same callable as the public API.
    >>> grouped_dead_guard is dead_guard
    True
"""

from .effect import effect_contradicts_guard, effect_no_op_under_guard
from .guard import dead_guard, forced_guard_unsat_under_init, guard_tautology
from .lifecycle import enter_postcondition_implies_during_precondition
from .transition import (
    composite_init_guards_incomplete,
    transition_shadowed_by_predecessor,
)

__all__ = [
    "composite_init_guards_incomplete",
    "dead_guard",
    "effect_contradicts_guard",
    "effect_no_op_under_guard",
    "enter_postcondition_implies_during_precondition",
    "forced_guard_unsat_under_init",
    "guard_tautology",
    "transition_shadowed_by_predecessor",
]

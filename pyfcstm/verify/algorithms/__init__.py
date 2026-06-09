"""Raw verification algorithm entry points."""

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

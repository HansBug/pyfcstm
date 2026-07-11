"""Public API for verification algorithms, metadata, and inspect gating.

The top-level package exports the core raw verification algorithms so callers
do not need to know the internal ``pyfcstm.verify.algorithms`` module layout.
Use this module as the stable import surface for raw verification entry points,
algorithm metadata, and inspect eligibility helpers.

Module map:

.. list-table::
   :header-rows: 1

   * - Area
     - Public entry
     - Purpose
   * - Raw algorithms
     - :func:`dead_guard`, :func:`guard_tautology`,
       :func:`forced_guard_unsat_under_init`,
       :func:`effect_no_op_under_guard`, :func:`effect_contradicts_guard`,
       :func:`transition_shadowed_by_predecessor`,
       :func:`enter_postcondition_implies_during_precondition`, and
       :func:`composite_init_guards_incomplete`
     - Run one precise verification check and return
       :class:`AlgorithmResult`.
   * - Registry
     - :data:`REGISTRY`
     - Store :class:`VerifyAlgorithmMeta` for every implemented verification
       algorithm.
   * - Inspect gating
     - :func:`eligible_for_inspect`, :func:`iter_inspect_eligible`
     - Decide which raw algorithms may be used by automatic inspect workflows.
   * - Inspect execution
     - :class:`InspectRunResult`, :func:`run_inspect_algorithms`
     - Execute inspect-eligible algorithms and preserve normalized raw results
       for later diagnostics conversion.
   * - Taxonomy
     - :class:`VerifyAlgorithmMeta` and the ``Literal`` aliases
     - Describe algorithm complexity, theory, scope, and fallback risk.
   * - Internal encoding
     - ``pyfcstm.verify.encoding``
     - Shared FCSTM-to-SMT encoding helpers used by algorithm implementations;
       callers normally should not import this package directly.

Examples::

    >>> from pyfcstm.verify import REGISTRY, dead_guard
    >>> # The public top-level algorithm is the same callable registered here.
    >>> REGISTRY["dead_guard"].impl is dead_guard
    True
"""

from .algorithms import (
    composite_init_guards_incomplete,
    dead_guard,
    effect_contradicts_guard,
    effect_no_op_under_guard,
    enter_postcondition_implies_during_precondition,
    forced_guard_unsat_under_init,
    guard_tautology,
    transition_shadowed_by_predecessor,
)
from .inspect_adapter import (
    InspectRunResult,
    InspectAccessForbiddenError,
    eligible_for_inspect,
    iter_inspect_eligible,
    run_inspect_algorithms,
)
from .registry import REGISTRY
from .result import AlgorithmResult, ResultKind
from .taxonomy import (
    CALL_COUNT_SCALING_ORDER,
    COMPLEXITY_TIER_ORDER,
    CallCountScaling,
    Closedness,
    ComplexityTier,
    FallbackUnknownRisk,
    FormulaSizeScaling,
    SMTLogic,
    VerificationScope,
    VerifyAlgorithmMeta,
)

__all__ = [
    "CALL_COUNT_SCALING_ORDER",
    "COMPLEXITY_TIER_ORDER",
    "REGISTRY",
    "AlgorithmResult",
    "CallCountScaling",
    "Closedness",
    "ComplexityTier",
    "FallbackUnknownRisk",
    "FormulaSizeScaling",
    "InspectAccessForbiddenError",
    "InspectRunResult",
    "SMTLogic",
    "ResultKind",
    "VerificationScope",
    "VerifyAlgorithmMeta",
    "composite_init_guards_incomplete",
    "dead_guard",
    "effect_contradicts_guard",
    "effect_no_op_under_guard",
    "enter_postcondition_implies_during_precondition",
    "eligible_for_inspect",
    "forced_guard_unsat_under_init",
    "guard_tautology",
    "iter_inspect_eligible",
    "run_inspect_algorithms",
    "transition_shadowed_by_predecessor",
]

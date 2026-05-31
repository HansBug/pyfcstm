"""
Formal verification algorithm taxonomy for pyfcstm.

This module defines the metadata contract used by :mod:`pyfcstm.verify`
to classify verification algorithms before they are implemented or wired
into diagnostics. The taxonomy is intentionally independent from
``pyfcstm.diagnostics`` so Track A can evolve without depending on the
Layer 2 inspect surface.
"""

from dataclasses import dataclass
from typing import Callable, Optional, Tuple

try:
    from typing import Literal
except ImportError:  # pragma: no cover - Python < 3.8 compatibility
    from typing_extensions import Literal

Closedness = Literal["closed", "queried"]
ComplexityTier = Literal[
    "structural",
    "smt_linear",
    "smt_nonlinear_decidable",
    "smt_undecidable_heuristic",
    "bmc_search",
]
SMTLogic = Literal[
    "QF_UF",
    "QF_LIA",
    "QF_LRA",
    "QF_LIRA",
    "QF_UFLIA",
    "QF_UFLRA",
    "QF_BV",
    "QF_FP",
    "QF_NIA",
    "QF_NRA",
    "QF_UFNRA",
    "QF_NIRA",
    "transcendental",
]
FormulaSizeScaling = Literal[
    "none",
    "constant",
    "linear",
    "quadratic",
    "exponential_in_bitwidth",
    "exponential_in_vars",
    "doubly_exponential",
]
CallCountScaling = Literal[
    "none",
    "one",
    "linear_in_states",
    "linear_in_transitions",
    "linear_in_vars",
    "linear_in_leaves",
    "quadratic_in_outgoing_per_state",
    "quadratic_in_states",
    "vars_times_transitions",
    "k_unrollings",
    "k_unrollings_times_branching",
]
FallbackUnknownRisk = Literal[
    "none",
    "low",
    "medium",
    "high",
    "guaranteed_possible",
]
VerificationScope = Literal[
    "topological_only",
    "smt_local",
    "bmc_unrolled",
]

COMPLEXITY_TIER_ORDER = (
    "structural",
    "smt_linear",
    "smt_nonlinear_decidable",
    "smt_undecidable_heuristic",
)
CALL_COUNT_SCALING_ORDER = (
    "none",
    "one",
    "linear_in_states",
    "linear_in_transitions",
    "linear_in_vars",
    "linear_in_leaves",
    "quadratic_in_outgoing_per_state",
    "quadratic_in_states",
    "vars_times_transitions",
)


@dataclass(frozen=True)
class VerifyAlgorithmMeta:
    """
    Metadata describing one verification algorithm.

    :param name: Stable registry key and public algorithm name.
    :type name: str
    :param description: Short human-readable algorithm summary.
    :type description: str
    :param closedness: Whether the algorithm can run without an explicit query.
    :type closedness: Closedness
    :param complexity_tier: Engineering complexity tier used by inspect gating.
    :type complexity_tier: ComplexityTier
    :param smt_logic: SMT-LIB logic family, or ``None`` for structural algorithms.
    :type smt_logic: Optional[SMTLogic]
    :param formula_size_scaling: Size growth of each generated formula.
    :type formula_size_scaling: FormulaSizeScaling
    :param call_count_scaling: Number of algorithm or solver calls over model size.
    :type call_count_scaling: CallCountScaling
    :param incremental: Whether the implementation is expected to reuse solver state.
    :type incremental: bool
    :param fallback_unknown_risk: Risk that the algorithm must return inconclusive.
    :type fallback_unknown_risk: FallbackUnknownRisk
    :param recommended_tactic: Z3 tactic name, or ``None`` when no solver is used.
    :type recommended_tactic: Optional[str]
    :param quantifier_alternation_depth: Quantifier alternation depth of formulas.
    :type quantifier_alternation_depth: int
    :param max_bitwidth: Maximum fixed bit-width if applicable, otherwise ``None``.
    :type max_bitwidth: Optional[int]
    :param theory_combination: SMT theory names combined by the algorithm.
    :type theory_combination: Tuple[str, ...]
    :param verification_scope: Boundary label for downstream result consumers.
    :type verification_scope: Optional[VerificationScope]
    :param dominant_dim: Dominant model dimensions for cost explanations.
    :type dominant_dim: Tuple[str, ...]
    :param diagnostic_codes: Diagnostics the algorithm may emit when integrated.
    :type diagnostic_codes: Tuple[str, ...]
    :param impl: Implementation callable, or ``None`` while the algorithm is pending.
    :type impl: Optional[Callable]
    """

    name: str
    description: str
    closedness: Closedness
    complexity_tier: ComplexityTier
    smt_logic: Optional[SMTLogic]
    formula_size_scaling: FormulaSizeScaling
    call_count_scaling: CallCountScaling
    incremental: bool
    fallback_unknown_risk: FallbackUnknownRisk
    recommended_tactic: Optional[str]
    quantifier_alternation_depth: int
    max_bitwidth: Optional[int]
    theory_combination: Tuple[str, ...]
    verification_scope: Optional[VerificationScope]
    dominant_dim: Tuple[str, ...]
    diagnostic_codes: Tuple[str, ...]
    impl: Optional[Callable]


__all__ = [
    "CALL_COUNT_SCALING_ORDER",
    "COMPLEXITY_TIER_ORDER",
    "CallCountScaling",
    "Closedness",
    "ComplexityTier",
    "FallbackUnknownRisk",
    "FormulaSizeScaling",
    "SMTLogic",
    "VerificationScope",
    "VerifyAlgorithmMeta",
]

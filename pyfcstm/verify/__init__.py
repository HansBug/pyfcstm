"""Public API for pyfcstm verification metadata and inspect gating."""

from .inspect_adapter import (
    InspectAccessForbiddenError,
    eligible_for_inspect,
    iter_inspect_eligible,
)
from .registry import REGISTRY
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
    "CallCountScaling",
    "Closedness",
    "ComplexityTier",
    "FallbackUnknownRisk",
    "FormulaSizeScaling",
    "InspectAccessForbiddenError",
    "SMTLogic",
    "VerificationScope",
    "VerifyAlgorithmMeta",
    "eligible_for_inspect",
    "iter_inspect_eligible",
]

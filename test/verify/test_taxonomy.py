import dataclasses

try:
    from typing import get_args
except ImportError:  # pragma: no cover - Python 3.7 compatibility
    from typing_extensions import get_args

import pytest

from pyfcstm.verify.taxonomy import (
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


pytestmark = pytest.mark.unittest


EXPECTED_FIELDS = (
    "name",
    "description",
    "closedness",
    "complexity_tier",
    "smt_logic",
    "formula_size_scaling",
    "call_count_scaling",
    "incremental",
    "fallback_unknown_risk",
    "recommended_tactic",
    "quantifier_alternation_depth",
    "max_bitwidth",
    "theory_combination",
    "verification_scope",
    "dominant_dim",
    "diagnostic_codes",
    "impl",
)


def test_verify_algorithm_meta_has_exact_contract_fields():
    assert dataclasses.is_dataclass(VerifyAlgorithmMeta)
    assert getattr(VerifyAlgorithmMeta, "__dataclass_params__").frozen is True
    assert (
        tuple(field.name for field in dataclasses.fields(VerifyAlgorithmMeta))
        == EXPECTED_FIELDS
    )


def test_verify_algorithm_meta_is_frozen():
    meta = VerifyAlgorithmMeta(
        name="example",
        description="example algorithm",
        closedness="closed",
        complexity_tier="structural",
        smt_logic=None,
        formula_size_scaling="none",
        call_count_scaling="one",
        incremental=False,
        fallback_unknown_risk="none",
        recommended_tactic=None,
        quantifier_alternation_depth=0,
        max_bitwidth=None,
        theory_combination=(),
        verification_scope="topological_only",
        dominant_dim=("states",),
        diagnostic_codes=(),
        impl=None,
    )
    with pytest.raises(dataclasses.FrozenInstanceError):
        setattr(meta, "name", "changed")


def test_literal_value_sets_match_issue_contract():
    assert set(get_args(Closedness)) == {"closed", "queried"}
    assert set(get_args(ComplexityTier)) == {
        "structural",
        "smt_linear",
        "smt_nonlinear_decidable",
        "smt_undecidable_heuristic",
    }
    assert set(get_args(SMTLogic)) == {
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
    }
    assert set(get_args(FormulaSizeScaling)) == {
        "none",
        "constant",
        "linear",
        "quadratic",
        "exponential_in_bitwidth",
        "exponential_in_vars",
        "doubly_exponential",
    }
    assert set(get_args(CallCountScaling)) == {
        "none",
        "one",
        "linear_in_states",
        "linear_in_transitions",
        "linear_in_vars",
        "linear_in_leaves",
        "quadratic_in_outgoing_per_state",
        "quadratic_in_states",
        "vars_times_transitions",
    }
    assert set(get_args(FallbackUnknownRisk)) == {
        "none",
        "low",
        "medium",
        "high",
        "guaranteed_possible",
    }
    assert set(get_args(VerificationScope)) == {
        "topological_only",
        "smt_local",
    }


def test_inspect_order_constants_cover_the_complete_taxonomy():
    assert COMPLEXITY_TIER_ORDER == (
        "structural",
        "smt_linear",
        "smt_nonlinear_decidable",
        "smt_undecidable_heuristic",
    )
    assert CALL_COUNT_SCALING_ORDER == (
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
    assert set(COMPLEXITY_TIER_ORDER) == set(get_args(ComplexityTier))
    assert set(CALL_COUNT_SCALING_ORDER) == set(get_args(CallCountScaling))


def test_public_verify_package_reexports_core_contract():
    import pyfcstm.verify as verify

    for name in (
        "VerifyAlgorithmMeta",
        "REGISTRY",
        "InspectAccessForbiddenError",
        "eligible_for_inspect",
        "iter_inspect_eligible",
        "COMPLEXITY_TIER_ORDER",
        "CALL_COUNT_SCALING_ORDER",
    ):
        assert hasattr(verify, name)
        assert name in verify.__all__

from typing import cast

import pytest

from pyfcstm.verify import (
    REGISTRY,
    InspectAccessForbiddenError,
    eligible_for_inspect,
    iter_inspect_eligible,
)
from pyfcstm.verify.taxonomy import (
    CallCountScaling,
    ComplexityTier,
    VerifyAlgorithmMeta,
)


pytestmark = pytest.mark.unittest


def _meta(**overrides):
    values = {
        "name": "custom",
        "description": "custom algorithm",
        "closedness": "closed",
        "complexity_tier": "structural",
        "smt_logic": None,
        "formula_size_scaling": "none",
        "call_count_scaling": "one",
        "incremental": False,
        "fallback_unknown_risk": "none",
        "recommended_tactic": None,
        "quantifier_alternation_depth": 0,
        "max_bitwidth": None,
        "theory_combination": (),
        "verification_scope": "topological_only",
        "dominant_dim": ("states",),
        "diagnostic_codes": (),
        "impl": None,
    }
    values.update(overrides)
    return VerifyAlgorithmMeta(**values)


def test_structural_closed_algorithm_is_eligible_by_default():
    assert eligible_for_inspect(REGISTRY["topological_reachable_set"]) is True


def test_smt_linear_requires_opt_in_complexity_tier():
    assert eligible_for_inspect(REGISTRY["dead_guard"]) is False
    assert (
        eligible_for_inspect(
            REGISTRY["dead_guard"],
            max_complexity_tier="smt_linear",
        )
        is True
    )
    assert (
        eligible_for_inspect(
            REGISTRY["enter_postcondition_implies_during_precondition"],
            max_complexity_tier="smt_linear",
        )
        is True
    )


def test_queried_and_bmc_algorithms_are_never_eligible():
    assert (
        eligible_for_inspect(
            REGISTRY["bounded_reachability"],
            max_complexity_tier="smt_undecidable_heuristic",
            max_call_count_scaling="vars_times_transitions",
        )
        is False
    )
    queried_structural = _meta(closedness="queried", complexity_tier="structural")
    assert eligible_for_inspect(queried_structural) is False
    closed_bmc = _meta(
        closedness="closed",
        complexity_tier="bmc_search",
        call_count_scaling="k_unrollings",
    )
    assert eligible_for_inspect(closed_bmc) is False


def test_bmc_search_max_complexity_tier_is_forbidden():
    with pytest.raises(InspectAccessForbiddenError, match="bmc_search"):
        eligible_for_inspect(
            REGISTRY["topological_reachable_set"],
            max_complexity_tier="bmc_search",
        )


def test_call_count_limit_blocks_more_expensive_closed_algorithm():
    assert (
        eligible_for_inspect(
            REGISTRY["topological_reachable_set"],
            max_call_count_scaling="one",
        )
        is False
    )
    assert (
        eligible_for_inspect(
            REGISTRY["topological_reachable_set"],
            max_call_count_scaling="linear_in_states",
        )
        is True
    )


def test_call_count_scaling_outside_inspect_order_is_not_eligible():
    k_unroll = _meta(call_count_scaling="k_unrollings")
    assert (
        eligible_for_inspect(
            k_unroll,
            max_complexity_tier="smt_undecidable_heuristic",
            max_call_count_scaling="vars_times_transitions",
        )
        is False
    )


def test_invalid_inspect_limits_raise_instead_of_disabling_all_algorithms():
    for invalid_tier in ("smt_lienar", None):
        with pytest.raises(InspectAccessForbiddenError):
            eligible_for_inspect(
                REGISTRY["topological_reachable_set"],
                max_complexity_tier=cast(ComplexityTier, invalid_tier),
            )

    for invalid_call_count in (
        "linear_in_transition",
        "k_unrollings",
        "k_unrollings_times_branching",
        None,
    ):
        with pytest.raises(InspectAccessForbiddenError):
            eligible_for_inspect(
                REGISTRY["topological_reachable_set"],
                max_call_count_scaling=cast(CallCountScaling, invalid_call_count),
            )


def test_nonlinear_and_undecidable_tier_boundaries_have_no_extra_algorithms():
    expected = tuple(
        meta.name for meta in iter_inspect_eligible(max_complexity_tier="smt_linear")
    )
    for tier in ("smt_nonlinear_decidable", "smt_undecidable_heuristic"):
        assert (
            tuple(meta.name for meta in iter_inspect_eligible(max_complexity_tier=tier))
            == expected
        )


def test_iter_inspect_eligible_preserves_registry_order():
    assert tuple(meta.name for meta in iter_inspect_eligible()) == (
        "topological_reachable_set",
        "unreachable_states",
        "strongly_connected_components",
        "topological_finite",
        "topological_inevitable_terminator",
        "event_emission_to_consumer_reachable",
    )
    assert tuple(
        meta.name for meta in iter_inspect_eligible(max_complexity_tier="smt_linear")
    ) == (
        "topological_reachable_set",
        "unreachable_states",
        "strongly_connected_components",
        "topological_finite",
        "topological_inevitable_terminator",
        "event_emission_to_consumer_reachable",
        "dead_guard",
        "guard_tautology",
        "forced_guard_unsat_under_init",
        "effect_no_op_under_guard",
        "effect_contradicts_guard",
        "transition_shadowed_by_predecessor",
        "enter_postcondition_implies_during_precondition",
        "composite_init_guards_incomplete",
    )
    assert tuple(
        meta.name
        for meta in iter_inspect_eligible(
            max_complexity_tier="smt_linear",
            max_call_count_scaling="linear_in_states",
        )
    ) == (
        "topological_reachable_set",
        "unreachable_states",
        "strongly_connected_components",
        "topological_finite",
        "topological_inevitable_terminator",
        "composite_init_guards_incomplete",
    )

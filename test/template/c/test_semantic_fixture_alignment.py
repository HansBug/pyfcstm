import pytest

from test.testings.native_semantic_alignment import (
    GENERATED_C_ALIGNMENT,
    run_native_alignment_case,
    run_native_alignment_case_subprocess,
)
from test.testings.simulate_semantics import load_semantic_case


@pytest.mark.unittest
def test_generated_c_alignment_shared_fixture_smoke():
    case = load_semantic_case("design_basic_simple_transition")

    result = run_native_alignment_case(GENERATED_C_ALIGNMENT, case)

    assert result.status == "passed"
    assert result.classification is None


@pytest.mark.unittest
def test_generated_c_alignment_subprocess_reports_known_native_failure():
    result = run_native_alignment_case_subprocess(
        GENERATED_C_ALIGNMENT, "aspect_context_reports_active_leaf"
    )

    assert result.status == "expected_failure"
    assert result.classification == "handler_mismatch"
    assert result.expected_classification == "handler_mismatch"
    assert result.support == "expected_failure"
    assert result.tracking == "https://github.com/HansBug/pyfcstm/issues/218"


_NATIVE_EXPRESSION_DIAGNOSTIC_CASES = (
    "expression_error_preserves_runtime_snapshot",
    "expression_failure_if_condition_raises_expression_error",
    "expression_failure_raises_expression_error",
    "expression_failure_transition_effect_raises_expression_error",
    "expression_failure_transition_guard_raises_expression_error",
    "hot_start_initial_vars_override_skips_int_initializer",
    "hot_start_leaf_defers_during_expression_error",
    "expression_large_integer_safe_diagnostics",
    "expression_type_error_wraps_transition_effect",
    "sign_function_aligns_aspect_guard_effect_math",
    "sign_function_controls_guard_transition",
    "sign_function_handles_all_signs",
    "sign_function_preserves_complex_action_precedence",
    "sign_function_updates_during_action",
    "similar_state_paths_keep_actions_distinct",
    "design_speculative_dfs_safety_limit",
    "ended_runtime_ignores_event_inputs",
    "hot_start_rejects_overdeep_leaf_stack",
    "pseudo_self_loop_step_limit_raises_dfs_error",
)


@pytest.mark.unittest
@pytest.mark.parametrize("case_id", _NATIVE_EXPRESSION_DIAGNOSTIC_CASES)
def test_generated_c_alignment_expression_diagnostic_cases_pass(case_id):
    result = run_native_alignment_case_subprocess(GENERATED_C_ALIGNMENT, case_id)

    assert result.status == "passed"
    assert result.classification is None

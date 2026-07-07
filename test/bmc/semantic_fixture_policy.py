"""BMC semantic-fixture ledger for relation-layer alignment tests.

This module records the current BMC-core handling policy for the shared
``test/fixtures/simulate_semantics`` corpus.  The policy is intentionally a
test-only ledger: production BMC APIs remain independent from fixture buckets,
while the tests can verify that every temporary exclusion has an explicit
follow-up category and every relation-supported case is actually checked.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Iterable, Tuple


@dataclass(frozen=True)
class BmcSemanticFixturePolicy:
    """Expected BMC-core handling for one semantic fixture case.

    :param mode: One of ``"hard_pass"``, ``"partial"``,
        ``"expected_unsupported"``, ``"temporary_exclude"``, or
        ``"long_term_exclude"``.
    :type mode: str
    :param bucket: Issue-ledger bucket used by the BMC alignment plan.
    :type bucket: str
    :param reason: Human-readable reason for this policy entry.
    :type reason: str
    :param ignored_expect_fields: Expectation fields intentionally ignored by a
        partial runner, defaults to ``()``.
    :type ignored_expect_fields: Tuple[str, ...], optional

    Example::

        >>> policy = policy_for_case("design_basic_simple_transition")
        >>> policy.mode
        'hard_pass'
        >>> policy.ignored_expect_fields
        ()
    """

    mode: str
    bucket: str
    reason: str
    ignored_expect_fields: Tuple[str, ...] = ()


PLAIN_BEFORE_ALIGNMENT_CASES = {
    "combo_initial_guard_not_polluted_by_plain_before",
    "combo_initial_plain_before_deferred",
    "manual_initial_pseudo_lifecycle_plain_before_deferred",
}

INITIAL_DELTA_ALIGNMENT_CASES = {
    "design_composite_stuck_in_init_wait",
    "failed_initial_cycle_preserves_root_entry_lifecycle",
    "hot_start_deep_evented_initial_waits_for_event",
    "design_post_child_exit_without_follow_up",
}

NUMERIC_UNSUPPORTED_CASES = {
    "persistent_default_int_initializer_normalizes_integer_float",
    "persistent_effect_writeback_normalizes_integer_float",
    "persistent_int_writeback_normalizes_integer_float",
}

HANDLER_CALL_PARTIAL_CASES = {
    "abstract_handler_context_metadata",
    "abstract_handler_context_vars_are_read_only",
    "abstract_hook_context_hot_start_leaf",
    "abstract_hook_ref_context_reports_callsite_metadata",
    "aspect_context_reports_active_leaf",
    "composite_initial_handler_log_after_transition_uses_selected_child",
    "composite_initial_handler_log_keeps_stable_branch_before_exit_branch",
    "composite_initial_handler_log_uses_enter_selected_child",
    "failed_initial_cycle_skips_abstract_handler_callbacks",
    "hot_start_composite_evented_initial_skips_entry_boundary_before",
    "lifecycle_ref_chain_resolves_long_acyclic_chain",
    "named_ref_context_reports_callsite",
    "ref_abstract_handler_reports_calling_state",
    "ref_context_uses_callsite_stage",
}

TEMPORARY_BMC_CORE_EXCLUDE_CASES = {
    # Future runtime-error relation work.
    "design_speculative_dfs_safety_limit",
    "expression_error_preserves_runtime_snapshot",
    "expression_failure_if_condition_raises_expression_error",
    "expression_failure_raises_expression_error",
    "expression_failure_transition_effect_raises_expression_error",
    "expression_failure_transition_guard_raises_expression_error",
    "expression_type_error_wraps_transition_effect",
    "hot_start_leaf_defers_during_expression_error",
    "persistent_operation_writeback_rejects_float_and_rolls_back",
    "pseudo_self_loop_step_limit_raises_dfs_error",
}

CONSTRUCTOR_DIAGNOSTIC_EXCLUDE_CASES = {
    "hot_start_initial_vars_reject_bool_values",
    "hot_start_initial_vars_reject_string_values",
    "hot_start_rejects_blocked_composite_initial",
    "hot_start_rejects_overdeep_leaf_stack",
    "hot_start_rejects_unstable_pseudo_leaf",
    "persistent_default_int_initializer_rejects_non_integer_float",
}

BMC_CORE_FIXTURE_LEDGER_CASES = (
    PLAIN_BEFORE_ALIGNMENT_CASES
    | INITIAL_DELTA_ALIGNMENT_CASES
    | NUMERIC_UNSUPPORTED_CASES
    | HANDLER_CALL_PARTIAL_CASES
    | TEMPORARY_BMC_CORE_EXCLUDE_CASES
    | CONSTRUCTOR_DIAGNOSTIC_EXCLUDE_CASES
)


def _temporary_policy(case_id: str) -> BmcSemanticFixturePolicy:
    return BmcSemanticFixturePolicy(
        mode="temporary_exclude",
        bucket="runtime_step_error",
        reason="Runtime step-error semantics are scheduled for later BMC diagnostic research.",
    )


def policy_for_case(case_id: str) -> BmcSemanticFixturePolicy:
    """Return the BMC-core fixture policy for ``case_id``.

    :param case_id: Semantic fixture id.
    :type case_id: str
    :return: Fixture handling policy.
    :rtype: BmcSemanticFixturePolicy

    Example::

        >>> policy_for_case("combo_initial_plain_before_deferred").bucket
        'initial_plain_before'
        >>> policy_for_case("abstract_handler_context_metadata").mode
        'partial'
    """
    if case_id in PLAIN_BEFORE_ALIGNMENT_CASES:
        return BmcSemanticFixturePolicy(
            mode="hard_pass",
            bucket="initial_plain_before",
            reason="Initial pseudo/combo plain-before ordering is covered by the current BMC relation.",
        )
    if case_id in INITIAL_DELTA_ALIGNMENT_CASES:
        return BmcSemanticFixturePolicy(
            mode="hard_pass",
            bucket="initialization_delta",
            reason="STATE_INIT and delta/gamma no-progress semantics are covered by the current BMC relation.",
        )
    if case_id in NUMERIC_UNSUPPORTED_CASES:
        return BmcSemanticFixturePolicy(
            mode="expected_unsupported",
            bucket="numeric_unsupported",
            reason="Current Int bitwise / integer-normalization lowering is unsupported and must fail loudly.",
        )
    if case_id in HANDLER_CALL_PARTIAL_CASES:
        return BmcSemanticFixturePolicy(
            mode="partial",
            bucket="abstract_handler_calls",
            reason="State, ended, and vars must align now; handler_calls wait for abstract call records.",
            ignored_expect_fields=("handler_calls",),
        )
    if case_id in TEMPORARY_BMC_CORE_EXCLUDE_CASES:
        return _temporary_policy(case_id)
    if case_id in CONSTRUCTOR_DIAGNOSTIC_EXCLUDE_CASES:
        return BmcSemanticFixturePolicy(
            mode="long_term_exclude",
            bucket="constructor_diagnostic",
            reason="Constructor/init diagnostics are outside the current BMC-core relation surface.",
        )
    return BmcSemanticFixturePolicy(
        mode="hard_pass",
        bucket="baseline",
        reason="No known BMC-core exclusion; full public state/vars expectations must pass.",
    )


def policy_by_case(case_ids: Iterable[str]) -> Dict[str, BmcSemanticFixturePolicy]:
    """Return policies keyed by case id for ``case_ids``.

    :param case_ids: Iterable of fixture ids.
    :type case_ids: Iterable[str]
    :return: Mapping from id to policy.
    :rtype: Dict[str, BmcSemanticFixturePolicy]

    Example::

        >>> policies = policy_by_case([
        ...     "design_basic_simple_transition",
        ...     "combo_initial_plain_before_deferred",
        ... ])
        >>> sorted(policies)
        ['combo_initial_plain_before_deferred', 'design_basic_simple_transition']
    """
    return {case_id: policy_for_case(case_id) for case_id in case_ids}

# Simulate semantic fixtures

This corpus turns existing simulator and built-in Python template alignment
semantics into data files. Each case lives in `cases/<id>.fcstm` plus
`cases/<id>.yaml` and is executed by helpers in
`test/testings/simulate_semantics.py`.

This corpus is a fixture/test-harness change only. It does not change production
runtime semantics and does not activate known simulator bug reproductions.

The shared corpus is intentionally narrow and public-API based. Every YAML case
defaults to the simulator plus generated Python alignment runners, and the only
runner-selection field is `exclude_runners` for explicit exceptions. Do not add
`runners`, top-level boundary markers, CLI command scenarios, model-construction
diagnostics, runtime options, log/warning assertions, stack snapshots, cycle
counters, history records, or any other private simulator surface to this
corpus.

## How to run

```bash
python -m pytest test/simulate/test_semantic_fixtures.py -v
python -m pytest test/template/python/test_semantic_fixture_alignment.py -v
SKIP_SLOW_TESTS=1 make unittest
```

## Adding a case

1. Add `cases/<id>.fcstm` with the DSL source.
2. Add `cases/<id>.yaml` using `schema_version: 1` and the schema in
   `schema.md`.
3. Keep `id` equal to the YAML/FCSTM basename.
4. Set `origin.files` to the exact original pytest function(s).
5. Omit `runners`; the loader applies all current shared runners by default.
6. Use `exclude_runners` only when a current shared runner cannot consume the
   case and the exclusion is intentional.
7. Keep only the public observation surface: `state`, `vars`, `vars_exact`,
   `vars_keys`, `vars_absent`, `ended`, constructor or hot-start outcomes,
   per-step cycle state and vars, `handler_calls`, and `cycle_result`.
8. Preserve every original behavior either through the shared public observation
   surface or through an ordinary pytest outside this corpus.
9. Run the fixture tests and the ordinary pytest coverage that owns any
   non-shared behavior.

## Public-observation checklist

Use this checklist before deleting or replacing any inline original test:

- `origin.files` points to the original class/function.
- The `.fcstm` file is semantically equivalent to the original DSL string;
  indentation cleanup is okay, DSL changes are not.
- The YAML cycle/event sequence matches the original call sequence exactly.
- Event input strings are not rewritten to a different path form.
- Every helper assertion and every bare assertion either has a public YAML
  equivalent or remains in ordinary pytest coverage.
- Runtime log assertions, Python warning assertions, stack snapshots, cycle
  counters, history records, and CLI output stay outside this shared corpus.
- `set(runtime.vars.keys())` and temporary-variable non-leakage use
  `vars_keys` and/or `vars_absent`.
- Exception tests keep class and message assertions under `raises` and keep
  rollback state/vars assertions when the original checked them.
- CLI tests stay as ordinary pytest coverage instead of shared fixture YAML.
- Abstract-handler callbacks use `handlers` plus `handler_calls`; shared cases
  keep only public hook-call records. Handler error metadata belongs in
  ordinary simulator pytest coverage.
- Anonymous abstract warning dedupe metadata is a simulator-internal diagnostic
  and belongs in dedicated `test/simulate/` pytest coverage, not shared fixture
  YAML.
- Python API shape tests that YAML cannot represent, such as tuple or State
  object hot-start inputs, stay as dedicated Python tests.

## Migration-equivalence review table template

Reviewers can use this fixed template when checking a migrated case:

| Original test | Fixture id | DSL equivalent? | Cycle/events equivalent? | Assertions preserved? | Notes |
|---|---|---|---|---|---|
| `path::Class::test_name` | `case_id` | yes/no | yes/no | yes/no | Missing or changed assertions. |

## Current fixture index

The table below is generated from the current YAML metadata and is intended to
make anti-drift review straightforward. `origin.files` points to the original
inline tests or upstream issue/PR evidence that supplied each fixture's
semantics.

| Fixture id | Runners | Assertion types | Origin files |
|---|---|---|---|
| `abstract_handler_context_metadata` | simulation, generated_python_alignment | handler_calls, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `abstract_handler_context_vars_are_read_only` | simulation, generated_python_alignment | ended, handler_calls, cycle_result, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614012639) |
| `abstract_hook_context_hot_start_leaf` | simulation, generated_python_alignment | handler_calls, hot_start, state, vars | [source](https://github.com/HansBug/pyfcstm/pull/205)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694732793) |
| `abstract_hook_ref_context_reports_callsite_metadata` | simulation, generated_python_alignment | handler_calls, state, vars | [source](https://github.com/HansBug/pyfcstm/pull/205)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694000657) |
| `aspect_context_reports_active_leaf` | simulation, generated_python_alignment | handler_calls, state, vars | [source](https://github.com/HansBug/pyfcstm/pull/205)<br>`test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `auto_initialization_on_current_state_access` | simulation, generated_python_alignment | initial, state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_auto_initialization_on_current_state_access`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_auto_initialization_on_current_state_access` |
| `cold_initial_chain_stack_modes_are_active` | simulation, generated_python_alignment | state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_guard_after_event_transition_uses_pre_before_vars` | simulation, generated_python_alignment | cycle_result, events, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_guard_after_leaf_transition_uses_enter_state` | simulation, generated_python_alignment | state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_guard_after_named_ref_before_uses_pre_ref_vars` | simulation, generated_python_alignment | cycle_result, events, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_guard_can_select_terminal_branch_before_plain_before` | simulation, generated_python_alignment | ended, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_guard_uses_enter_state_before_plain_before` | simulation, generated_python_alignment | state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_guard_with_effect_runs_before_plain_before` | simulation, generated_python_alignment | state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_handler_log_after_transition_uses_selected_child` | simulation, generated_python_alignment | events, handler_calls, state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_handler_log_keeps_stable_branch_before_exit_branch` | simulation, generated_python_alignment | handler_calls, state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_handler_log_uses_enter_selected_child` | simulation, generated_python_alignment | handler_calls, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_nested_entry_order_survives_deep_choice` | simulation, generated_python_alignment | events, state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `composite_initial_skips_unstable_candidates_root_entry` | simulation, generated_python_alignment | ended, cycle_result, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614352350) |
| `cycle_result_event_accounting` | simulation, generated_python_alignment | cycle_result, events, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `cycle_result_event_transition` | simulation, generated_python_alignment | cycle_result, events, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `cycle_result_stable_leaf` | simulation, generated_python_alignment | cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `design_aspect_actions` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_5_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_5_aspect_actions` |
| `design_basic_simple_transition` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_1_basic_simple_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_1_basic_simple_transition` |
| `design_composite_state` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_2_composite_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_2_composite_state` |
| `design_composite_stuck_in_init_wait` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_27_composite_state_stuck_in_init_wait_without_enabled_init_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_27_composite_state_stuck_in_init_wait_without_enabled_init_transition` |
| `design_cross_hierarchy_transition_actual_runtime_behavior` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_25_cross_hierarchy_transition_actual_runtime_behavior`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_25_cross_hierarchy_transition_actual_runtime_behavior` |
| `design_cross_hierarchy_transition_with_staged_guards` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_26_cross_hierarchy_transition_with_staged_guards`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_26_cross_hierarchy_transition_with_staged_guards` |
| `design_evented_pseudo_chain_invalid_then_valid` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_19_evented_pseudo_chain_invalid_then_valid`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_19_evented_pseudo_chain_invalid_then_valid` |
| `design_exit_state` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_10_exit_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_10_exit_state` |
| `design_exit_to_parent_invalid` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_17_exit_to_parent_invalid`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_17_exit_to_parent_invalid` |
| `design_exit_to_parent_then_event_transition` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_17_1_exit_to_parent_then_event_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_17_1_exit_to_parent_then_event_transition` |
| `design_exit_to_parent_then_pseudo_guard` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_17_2_exit_to_parent_then_pseudo_then_guard`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_17_2_exit_to_parent_then_pseudo_then_guard` |
| `design_explicit_exit_to_root_ends_runtime` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_30_explicit_exit_to_root_ends_runtime`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_30_explicit_exit_to_root_ends_runtime` |
| `design_guard_effect_multilevel_transition` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_11_guard_effect_multilevel_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_11_guard_effect_multilevel_transition` |
| `design_mixed_composite_and_pseudo` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_20_mixed_composite_and_pseudo`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_20_mixed_composite_and_pseudo` |
| `design_multi_layer_aspect_actions` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_22_multi_layer_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_22_multi_layer_aspect_actions` |
| `design_multi_level_non_stoppable_deep` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable` |
| `design_multi_level_non_stoppable_leaf` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable` |
| `design_multiple_leaf_states_share_aspects` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_24_multiple_leaf_states_share_aspects`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_24_multiple_leaf_states_share_aspects` |
| `design_post_child_exit_without_follow_up` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_28_post_child_exit_without_follow_up_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_28_post_child_exit_without_follow_up_transition` |
| `design_pseudo_chain_inside_composite` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_18_pseudo_chain_inside_composite`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_18_pseudo_chain_inside_composite` |
| `design_pseudo_chain_multiple` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_14_multiple_pseudo_states_chain`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_14_multiple_pseudo_states_chain` |
| `design_pseudo_chain_single` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_13_single_pseudo_state_chain`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_13_single_pseudo_state_chain` |
| `design_pseudo_chain_to_machine_end` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_16_pseudo_chain_to_machine_end`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_16_pseudo_chain_to_machine_end` |
| `design_pseudo_chain_with_guard` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_15_pseudo_chain_with_guard`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_15_pseudo_chain_with_guard` |
| `design_pseudo_skips_aspect_actions` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_23_pseudo_state_skips_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_23_pseudo_state_skips_aspect_actions` |
| `design_pseudo_state` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_6_pseudo_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_6_pseudo_state` |
| `design_ref_abstract_action_without_side_effects` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_34_ref_targets_abstract_action_without_side_effects`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_34_ref_targets_abstract_action_without_side_effects` |
| `design_ref_named_aspect_action` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_35_ref_reuses_named_aspect_action`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_35_ref_reuses_named_aspect_action` |
| `design_ref_named_enter_action` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_33_ref_reuses_named_enter_action`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_33_ref_reuses_named_enter_action` |
| `design_self_transition` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_9_self_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_9_self_transition` |
| `design_single_layer_aspect_actions` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_21_single_layer_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_21_single_layer_aspect_actions` |
| `design_speculative_dfs_safety_limit` | simulation, generated_python_alignment | ended, exception, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_32_raises_error_for_non_converging_speculative_dfs`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_32_raises_error_for_non_converging_speculative_dfs` |
| `design_speculative_prunes_repeated_state` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_31_prunes_repeated_speculative_execution_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_31_prunes_repeated_speculative_execution_state` |
| `design_transition_priority` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_8_transition_priority`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_8_transition_priority` |
| `design_validation_cannot_reach_stoppable` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_3_validation_cannot_reach_stoppable`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_3_validation_cannot_reach_stoppable` |
| `design_validation_failure_multilevel_transition` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_12_validation_failure_multilevel_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_12_validation_failure_multilevel_transition` |
| `design_validation_init_transition_requires_event` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_4_validation_init_transition_requires_event`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_4_validation_init_transition_requires_event` |
| `ended_runtime_ignores_event_inputs` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `event_input_bare_string_path` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `event_input_model_event_object` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `event_path_absolute` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_202_flexible_path_absolute`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_202_flexible_path_absolute` |
| `event_path_basic_relative` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_200_flexible_path_basic_relative`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_200_flexible_path_basic_relative` |
| `event_path_mixed_formats_absolute` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_mixed_formats_full` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_mixed_formats_parent_relative` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_mixed_formats_relative` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_parent_relative` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_201_flexible_path_parent_relative`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_201_flexible_path_parent_relative` |
| `expression_error_preserves_runtime_snapshot` | simulation, generated_python_alignment | raises, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `expression_failure_if_condition_raises_expression_error` | simulation, generated_python_alignment | exception | `test/fixtures/simulate_semantics/cases/expression_failure_if_condition_raises_expression_error.fcstm` |
| `expression_failure_raises_expression_error` | simulation, generated_python_alignment | exception | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_200_dsl_expression_failure_raises_expression_error` |
| `expression_failure_transition_effect_raises_expression_error` | simulation, generated_python_alignment | exception, state, vars | `test/fixtures/simulate_semantics/cases/expression_failure_transition_effect_raises_expression_error.fcstm` |
| `expression_failure_transition_guard_raises_expression_error` | simulation, generated_python_alignment | exception, state, vars | `test/fixtures/simulate_semantics/cases/expression_failure_transition_guard_raises_expression_error.fcstm` |
| `expression_large_integer_safe_diagnostics` | simulation, generated_python_alignment | cycle_result, state, vars | `test/simulate/test_runtime_expression_diagnostics.py::test_large_integer_cycle_does_not_depend_on_disabled_debug_logging`<br>`test/simulate/test_runtime_expression_diagnostics.py::test_large_integer_cycle_uses_safe_debug_logging` |
| `expression_logical_and_short_circuits_in_guard` | simulation, generated_python_alignment | cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `expression_logical_and_short_circuits_in_if` | simulation, generated_python_alignment | cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `expression_logical_or_short_circuits_in_guard` | simulation, generated_python_alignment | cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `expression_logical_or_short_circuits_in_if` | simulation, generated_python_alignment | cycle_result, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `expression_type_error_wraps_transition_effect` | simulation, generated_python_alignment | raises, state, vars | `test/simulate/test_runtime_expression_diagnostics.py::test_transition_effect_type_error_is_wrapped_and_rolls_back` |
| `failed_initial_cycle_preserves_root_entry_lifecycle` | simulation, generated_python_alignment | ended, cycle_result, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614005134) |
| `failed_initial_cycle_skips_abstract_handler_callbacks` | simulation, generated_python_alignment | ended, handler_calls, cycle_result, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614005134) |
| `forced_pseudo_candidate_skips_unstable_branch` | simulation, generated_python_alignment | state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `hot_start_accepts_structural_depth_limit_leaf` | simulation, generated_python_alignment | initial, state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_composite_evented_initial_skips_entry_boundary_before` | simulation, generated_python_alignment | initial, state, vars, cycle_result, handler_calls | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `hot_start_composite_state_with_init` | simulation, generated_python_alignment | initial, state, vars, cycle_result, ended | `test/simulate/test_hot_start.py::TestHotStartCompositeState::test_hot_start_from_composite_state_with_init` |
| `hot_start_composite_waits_for_initial_event` | simulation, generated_python_alignment | initial, state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `hot_start_deep_evented_initial_waits_for_event` | simulation, generated_python_alignment | initial, state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_evented_initial_matches_cold_suffix` | simulation, generated_python_alignment | initial, state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_initial_vars_override_skips_int_initializer` | simulation, generated_python_alignment | initial, state, vars, constructor_exception | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694623177) |
| `hot_start_initial_vars_reject_bool_values` | simulation, generated_python_alignment | constructor_exception | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_initial_vars_reject_string_values` | simulation, generated_python_alignment | constructor_exception | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_leaf_defers_during_expression_error` | simulation, generated_python_alignment | exception | [source](https://github.com/HansBug/pyfcstm/pull/153#issuecomment-4627323375) |
| `hot_start_leaf_state` | simulation, generated_python_alignment | initial, state, vars, cycle_result, ended | `test/simulate/test_hot_start.py::TestHotStartLeafState::test_hot_start_from_leaf_state_string_path` |
| `hot_start_rejects_blocked_composite_initial` | simulation, generated_python_alignment | constructor_exception | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_rejects_overdeep_leaf_stack` | simulation, generated_python_alignment | initial, exception | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_rejects_unstable_pseudo_leaf` | simulation, generated_python_alignment | constructor_exception | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture`<br>`test/template/python/test_semantic_fixture_alignment.py::test_generated_python_alignment_semantic_fixture` |
| `hot_start_skips_enter_actions` | simulation, generated_python_alignment | initial, state, vars, cycle_result, ended | `test/simulate/test_hot_start.py::TestHotStartWithLifecycleActions::test_hot_start_skips_enter_actions` |
| `hot_start_with_aspect_actions` | simulation, generated_python_alignment | initial, state, vars, cycle_result, ended | `test/simulate/test_hot_start.py::TestHotStartWithLifecycleActions::test_hot_start_with_aspect_actions` |
| `hot_start_with_composite_during_before_after` | simulation, generated_python_alignment | initial, state, vars, cycle_result, ended | `test/simulate/test_hot_start.py::TestHotStartWithLifecycleActions::test_hot_start_with_composite_during_before_after` |
| `if_blocks_during_else_branch` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_else_if_branch` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_false_then_continues` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_nested_outer_else` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_nested_true_branch` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_sequential_updates` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_temp_reassigned` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_then_without_else` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_exit_effect_enter_actions` | simulation, generated_python_alignment | state, vars, cycle_result, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_exit_effect_and_enter_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_exit_effect_and_enter_actions` |
| `lifecycle_ref_chain_resolves_long_acyclic_chain` | simulation, generated_python_alignment | handler_calls, state, vars | [source](https://github.com/HansBug/pyfcstm/pull/205)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694663908) |
| `named_ref_context_reports_callsite` | simulation, generated_python_alignment | handler_calls, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `persistent_default_float_initializer_converts_int` | simulation, generated_python_alignment | initial, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694530145) |
| `persistent_default_int_initializer_normalizes_integer_float` | simulation, generated_python_alignment | initial, state, vars, exception | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694530145) |
| `persistent_default_int_initializer_rejects_non_integer_float` | simulation, generated_python_alignment | constructor_exception | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694530145) |
| `persistent_effect_writeback_normalizes_integer_float` | simulation, generated_python_alignment | state, vars, exception | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694002673) |
| `persistent_initial_vars_override_skips_initializer` | simulation, generated_python_alignment | initial, state, vars, ended | [source](https://github.com/HansBug/pyfcstm/issues/156#issuecomment-4633663497) |
| `persistent_int_writeback_normalizes_integer_float` | simulation, generated_python_alignment | state, vars, exception | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694002673)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694852936) |
| `persistent_operation_writeback_rejects_float_and_rolls_back` | simulation, generated_python_alignment | exception, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/156#issuecomment-4631935935) |
| `post_child_exit_continuation_skips_unstable_candidates` | simulation, generated_python_alignment | ended, cycle_result, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614271348) |
| `pseudo_candidate_skips_unstable_branch` | simulation, generated_python_alignment | state, vars, cycle_result | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `pseudo_self_loop_step_limit_raises_dfs_error` | simulation, generated_python_alignment | exception, state, vars | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `ref_abstract_handler_reports_calling_state` | simulation, generated_python_alignment | ended, handler_calls, cycle_result, state, vars_exact | [source](https://github.com/HansBug/pyfcstm/pull/205)<br>[source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614012639) |
| `ref_context_uses_callsite_stage` | simulation, generated_python_alignment | handler_calls, state, vars_exact | `test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture` |
| `root_exit_runs_root_cleanup` | simulation, generated_python_alignment | ended, cycle_result, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614013960) |
| `scenario_ac_charger_session_control_normal` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control` |
| `scenario_ac_charger_session_control_unplug` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control` |
| `scenario_ats_mains_generator_transfer_outage` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer` |
| `scenario_ats_mains_generator_transfer_restore` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer` |
| `scenario_cold_storage_defrost_cycle_defrost` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle` |
| `scenario_cold_storage_defrost_cycle_normal` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle` |
| `scenario_elevator_door_control_blocked` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_100_elevator_door_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_100_elevator_door_control` |
| `scenario_elevator_door_control_normal` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_100_elevator_door_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_100_elevator_door_control` |
| `scenario_storage_water_heater_control_cooldown` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control` |
| `scenario_storage_water_heater_control_draw` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control` |
| `scenario_traffic_signal_with_pedestrian_request_normal` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request` |
| `scenario_traffic_signal_with_pedestrian_request_pedestrian` | simulation, generated_python_alignment | ended, cycle_result, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request` |
| `sign_function_aligns_aspect_guard_effect_math` | simulation, generated_python_alignment | state, vars, cycle_result | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694810781)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4695001326) |
| `sign_function_controls_guard_transition` | simulation, generated_python_alignment | state, vars, cycle_result | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694810781)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4695001326) |
| `sign_function_handles_all_signs` | simulation, generated_python_alignment | state, vars, cycle_result | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694810781)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4695001326) |
| `sign_function_preserves_complex_action_precedence` | simulation, generated_python_alignment | state, vars, cycle_result | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694810781)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4695001326) |
| `sign_function_updates_during_action` | simulation, generated_python_alignment | state, vars, cycle_result | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694810781)<br>[source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4695001326) |
| `similar_state_paths_keep_actions_distinct` | simulation, generated_python_alignment | state, vars, cycle_result | [source](https://github.com/HansBug/pyfcstm/issues/199#issuecomment-4694962840) |
| `temporary_variables_are_block_local` | simulation, generated_python_alignment | ended, cycle_result, state, vars, vars_absent, vars_keys | `test/simulate/test_runtime.py::TestTemporaryVariables::test_temporary_variables_are_block_local`<br>`test/template/python/test_runtime_alignment.py::TestTemporaryVariables::test_temporary_variables_are_block_local` |
| `transition_into_composite_skips_unstable_initial_candidate` | simulation, generated_python_alignment | ended, cycle_result, state, vars | [source](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614352350) |

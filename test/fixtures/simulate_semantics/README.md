# Simulate semantic fixtures

This corpus turns existing simulator and built-in Python template alignment
semantics into data files.  Each case lives in `cases/<id>.fcstm` plus
`cases/<id>.yaml` and is executed by helpers in
`test/testings/simulate_semantics.py`.

This corpus is a fixture/test-harness change only. It does not change production
runtime semantics and does not activate known simulator bug reproductions. The
tracking context is [issue #143](https://github.com/HansBug/pyfcstm/issues/143)
and [PR #145](https://github.com/HansBug/pyfcstm/pull/145).

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
5. Choose runners deliberately:
   - `simulation` for `SimulationRuntime` semantics.
   - `generated_python_alignment` only when the generated Python runtime is
     expected to match the simulator for this behavior.
   - `cli_command` for `CommandProcessor`/REPL-command behavior.
6. Express every original assertion in YAML. Do not weaken a migrated test to
   only state/vars if the original asserted logs, stack, exception class,
   exception message, temporary-variable absence, return value, or CLI output.
7. Run the fixture tests and the original tests that the case came from.

## Anti-drift migration checklist

Use this checklist before deleting or replacing any inline original test:

- `origin.files` points to the original class/function.
- The `.fcstm` file is semantically equivalent to the original DSL string;
  indentation cleanup is okay, DSL changes are not.
- The YAML cycle/event sequence matches the original call sequence exactly.
- Event input strings are not rewritten to a different path form.
- Every helper assertion and every bare assertion has a YAML equivalent.
- Runtime log assertions use `logs`; Python warning assertions use `warnings`.
- `brief_stack` assertions use `stack`.
- `set(runtime.vars.keys())` and temporary-variable non-leakage use
  `vars_keys` and/or `vars_absent`.
- Exception tests keep class and message assertions under `raises` and keep
  rollback state/vars assertions when the original checked them.
- CLI tests keep output assertions under `output_contains` /
  `output_not_contains` / `error_contains`.
- Abstract-handler callbacks use `handlers` plus `handler_calls`; log-mode
  handler error metadata uses `abstract_handler_errors`.
- Python API shape tests that YAML cannot represent, such as tuple or State
  object hot-start inputs, stay as dedicated Python tests.

## Migration-equivalence review table template

Reviewers can use this fixed template when checking a migrated case:

| Original test | Fixture id | DSL equivalent? | Cycle/events equivalent? | Assertions preserved? | Notes |
|---|---|---|---|---|---|
| `path::Class::test_name` | `case_id` | yes/no | yes/no | yes/no | Missing or changed assertions. |

## Current migration index

The table below is generated from the current YAML metadata and is intended to
make anti-drift review straightforward. `origin.files` points to the original
inline tests that supplied each fixture's semantics; fully migrated runtime and
Python-template alignment tests are now executed through the fixture runners, so
those origin paths may be visible only through repository history or the
[migration pull request](https://github.com/HansBug/pyfcstm/pull/145) after the
inline files are removed.

| Fixture id | Runners | Assertion types | Origin files |
|---|---|---|---|
| `abstract_handler_context_vars_are_read_only` | simulation | cycle_count, ended, handler_calls, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614012639) |
| `abstract_handler_raise_mode_blocks_later_cycles` | simulation | cycle_count, ended, error_info, error_state, handler_calls, exception, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614012639) |
| `auto_initialization_on_current_state_access` | simulation, generated_python_alignment | initial, stack, state, vars, return, ended | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_auto_initialization_on_current_state_access`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_auto_initialization_on_current_state_access` |
| `cli_init_basic` | cli_command | cli_output, state, vars, ended | `test/simulate/test_cli_init.py::TestCLIInitCommand::test_init_command_basic` |
| `cli_init_composite_state` | cli_command | cli_output, state, vars, stack, cycle_count, ended | `test/simulate/test_cli_init.py::TestCLIInitCommand::test_init_command_composite_state` |
| `cli_init_then_cycle` | cli_command | cli_output, state, vars, cycle_count, ended | `test/simulate/test_cli_init.py::TestCLIInitCommand::test_init_command_then_cycle` |
| `composite_initial_skips_unstable_candidates_root_entry` | simulation, generated_python_alignment | ended, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614352350) |
| `design_aspect_actions` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_5_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_5_aspect_actions` |
| `design_basic_simple_transition` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_1_basic_simple_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_1_basic_simple_transition` |
| `design_composite_state` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_2_composite_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_2_composite_state` |
| `design_composite_stuck_in_init_wait` | simulation, generated_python_alignment | ended, logs, return, stack, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_27_composite_state_stuck_in_init_wait_without_enabled_init_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_27_composite_state_stuck_in_init_wait_without_enabled_init_transition` |
| `design_cross_hierarchy_transition_actual_runtime_behavior` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_25_cross_hierarchy_transition_actual_runtime_behavior`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_25_cross_hierarchy_transition_actual_runtime_behavior` |
| `design_cross_hierarchy_transition_with_staged_guards` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_26_cross_hierarchy_transition_with_staged_guards`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_26_cross_hierarchy_transition_with_staged_guards` |
| `design_evented_pseudo_chain_invalid_then_valid` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_19_evented_pseudo_chain_invalid_then_valid`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_19_evented_pseudo_chain_invalid_then_valid` |
| `design_exit_state` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_10_exit_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_10_exit_state` |
| `design_exit_to_parent_invalid` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_17_exit_to_parent_invalid`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_17_exit_to_parent_invalid` |
| `design_exit_to_parent_then_event_transition` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_17_1_exit_to_parent_then_event_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_17_1_exit_to_parent_then_event_transition` |
| `design_exit_to_parent_then_pseudo_guard` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_17_2_exit_to_parent_then_pseudo_then_guard`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_17_2_exit_to_parent_then_pseudo_then_guard` |
| `design_explicit_exit_to_root_ends_runtime` | simulation, generated_python_alignment | ended, logs, return, stack, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_30_explicit_exit_to_root_ends_runtime`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_30_explicit_exit_to_root_ends_runtime` |
| `design_guard_effect_multilevel_transition` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_11_guard_effect_multilevel_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_11_guard_effect_multilevel_transition` |
| `design_mixed_composite_and_pseudo` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_20_mixed_composite_and_pseudo`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_20_mixed_composite_and_pseudo` |
| `design_multi_layer_aspect_actions` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_22_multi_layer_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_22_multi_layer_aspect_actions` |
| `design_multi_level_non_stoppable_deep` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable` |
| `design_multi_level_non_stoppable_leaf` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_7_multi_level_non_stoppable` |
| `design_multiple_leaf_states_share_aspects` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_24_multiple_leaf_states_share_aspects`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_24_multiple_leaf_states_share_aspects` |
| `design_post_child_exit_without_follow_up` | simulation, generated_python_alignment | ended, logs, return, stack, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_28_post_child_exit_without_follow_up_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_28_post_child_exit_without_follow_up_transition` |
| `post_child_exit_continuation_skips_unstable_candidates` | simulation, generated_python_alignment | ended, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614271348) |
| `design_pseudo_chain_inside_composite` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_18_pseudo_chain_inside_composite`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_18_pseudo_chain_inside_composite` |
| `design_pseudo_chain_multiple` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_14_multiple_pseudo_states_chain`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_14_multiple_pseudo_states_chain` |
| `design_pseudo_chain_single` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_13_single_pseudo_state_chain`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_13_single_pseudo_state_chain` |
| `design_pseudo_chain_to_machine_end` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_16_pseudo_chain_to_machine_end`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_16_pseudo_chain_to_machine_end` |
| `design_pseudo_chain_with_guard` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_15_pseudo_chain_with_guard`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_15_pseudo_chain_with_guard` |
| `design_pseudo_skips_aspect_actions` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_23_pseudo_state_skips_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_23_pseudo_state_skips_aspect_actions` |
| `design_pseudo_state` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_6_pseudo_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_6_pseudo_state` |
| `design_ref_abstract_action_without_side_effects` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_34_ref_targets_abstract_action_without_side_effects`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_34_ref_targets_abstract_action_without_side_effects` |
| `design_ref_named_aspect_action` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_35_ref_reuses_named_aspect_action`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_35_ref_reuses_named_aspect_action` |
| `design_ref_named_enter_action` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_33_ref_reuses_named_enter_action`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_33_ref_reuses_named_enter_action` |
| `design_self_transition` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_9_self_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_9_self_transition` |
| `design_single_layer_aspect_actions` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_21_single_layer_aspect_actions`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_21_single_layer_aspect_actions` |
| `design_speculative_dfs_safety_limit` | simulation, generated_python_alignment | ended, exception, return, stack, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_32_raises_error_for_non_converging_speculative_dfs`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_32_raises_error_for_non_converging_speculative_dfs` |
| `design_speculative_prunes_repeated_state` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_31_prunes_repeated_speculative_execution_state`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_31_prunes_repeated_speculative_execution_state` |
| `design_transition_priority` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_8_transition_priority`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_8_transition_priority` |
| `design_validation_cannot_reach_stoppable` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_3_validation_cannot_reach_stoppable`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_3_validation_cannot_reach_stoppable` |
| `design_validation_failure_multilevel_transition` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_12_validation_failure_multilevel_transition`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_12_validation_failure_multilevel_transition` |
| `design_validation_init_transition_requires_event` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_4_validation_init_transition_requires_event`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_4_validation_init_transition_requires_event` |
| `event_path_absolute` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_202_flexible_path_absolute`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_202_flexible_path_absolute` |
| `event_path_basic_relative` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_200_flexible_path_basic_relative`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_200_flexible_path_basic_relative` |
| `event_path_invalid_raises_event_error` | simulation | ended, exception, stack, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_200_invalid_event_path_raises_event_error` |
| `event_path_mixed_formats_absolute` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_mixed_formats_full` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_mixed_formats_parent_relative` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_mixed_formats_relative` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_203_flexible_path_mixed_formats` |
| `event_path_parent_relative` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_201_flexible_path_parent_relative`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_201_flexible_path_parent_relative` |
| `expression_failure_raises_expression_error` | simulation | ended, exception, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_200_dsl_expression_failure_raises_expression_error` |
| `failed_cycle_rolls_back_logged_abstract_handler_errors` | simulation | abstract_handler_errors, cycle_count, ended, handler_calls, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614012639) |
| `failed_initial_cycle_preserves_root_entry_lifecycle` | simulation | cycle_count, ended, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614005134) |
| `failed_initial_cycle_skips_abstract_handler_callbacks` | simulation | cycle_count, ended, handler_calls, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614005134) |
| `hot_start_composite_state_with_init` | simulation | initial, state, vars, stack, return, ended | `test/simulate/test_hot_start.py::TestHotStartCompositeState::test_hot_start_from_composite_state_with_init` |
| `hot_start_leaf_state` | simulation | initial, state, vars, stack, return, ended | `test/simulate/test_hot_start.py::TestHotStartLeafState::test_hot_start_from_leaf_state_string_path` |
| `hot_start_skips_enter_actions` | simulation | initial, state, vars, return, ended | `test/simulate/test_hot_start.py::TestHotStartWithLifecycleActions::test_hot_start_skips_enter_actions` |
| `hot_start_with_aspect_actions` | simulation | initial, state, vars, return, ended | `test/simulate/test_hot_start.py::TestHotStartWithLifecycleActions::test_hot_start_with_aspect_actions` |
| `hot_start_with_composite_during_before_after` | simulation | initial, state, vars, return, ended | `test/simulate/test_hot_start.py::TestHotStartWithLifecycleActions::test_hot_start_with_composite_during_before_after` |
| `if_blocks_during_else_branch` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_else_if_branch` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_false_then_continues` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_nested_outer_else` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_nested_true_branch` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_sequential_updates` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_temp_reassigned` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_during_then_without_else` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_during_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_during_actions` |
| `if_blocks_exit_effect_enter_actions` | simulation, generated_python_alignment | state, vars, return, ended | `test/simulate/test_runtime.py::TestIfBlockRuntime::test_if_blocks_in_exit_effect_and_enter_actions`<br>`test/template/python/test_runtime_alignment.py::TestIfBlockRuntime::test_if_blocks_in_exit_effect_and_enter_actions` |
| `lifecycle_action_ref_cycle_raises_diagnostic` | simulation | exception | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614298619) |
| `rejected_transition_candidate_defers_anonymous_warning` | simulation | cycle_count, ended, return, stack, state, vars, warnings | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614148256) |
| `ref_abstract_handler_reports_calling_state` | simulation | cycle_count, ended, handler_calls, return, stack, state, vars_exact | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614012639) |
| `root_exit_runs_root_cleanup` | simulation, generated_python_alignment | ended, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614013960) |
| `scenario_ac_charger_session_control_normal` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control` |
| `scenario_ac_charger_session_control_unplug` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_103_ac_charger_session_control` |
| `scenario_ats_mains_generator_transfer_outage` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer` |
| `scenario_ats_mains_generator_transfer_restore` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_104_ats_mains_generator_transfer` |
| `scenario_cold_storage_defrost_cycle_defrost` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle` |
| `scenario_cold_storage_defrost_cycle_normal` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_105_cold_storage_defrost_cycle` |
| `scenario_elevator_door_control_blocked` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_100_elevator_door_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_100_elevator_door_control` |
| `scenario_elevator_door_control_normal` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_100_elevator_door_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_100_elevator_door_control` |
| `scenario_storage_water_heater_control_cooldown` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control` |
| `scenario_storage_water_heater_control_draw` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_101_storage_water_heater_control` |
| `scenario_traffic_signal_with_pedestrian_request_normal` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request` |
| `scenario_traffic_signal_with_pedestrian_request_pedestrian` | simulation, generated_python_alignment | ended, return, state, vars | `test/simulate/test_runtime.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request`<br>`test/template/python/test_runtime_alignment.py::TestSimulationDesignExamples::test_4_102_traffic_signal_with_pedestrian_request` |
| `temporary_variables_are_block_local` | simulation, generated_python_alignment | ended, return, state, vars, vars_absent, vars_keys | `test/simulate/test_runtime.py::TestTemporaryVariables::test_temporary_variables_are_block_local`<br>`test/template/python/test_runtime_alignment.py::TestTemporaryVariables::test_temporary_variables_are_block_local` |
| `transition_into_composite_skips_unstable_initial_candidate` | simulation, generated_python_alignment | ended, return, stack, state, vars | [issue #143 comment](https://github.com/HansBug/pyfcstm/issues/143#issuecomment-4614352350) |

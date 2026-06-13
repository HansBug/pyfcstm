# Python template alignment coverage ledger

This ledger records the final regression coverage for the legal-trace
alignment work tracked by [issue #199](https://github.com/HansBug/pyfcstm/issues/199)
and planned by [PR #200](https://github.com/HansBug/pyfcstm/pull/200).
It is intentionally written in terms of domain behavior and shared semantic
fixture ids so future maintenance can verify simulator/template alignment
without knowing the execution plan that introduced each case.

The alignment scope is limited to legal FCSTM DSL models, legal cold or hot
starts, legal `cycle(events)` sequences, and observation-only abstract
handler/hook callbacks. It does not cover illegal API input, registry mechanics,
CLI/REPL behavior, jsfcstm/editor/solver behavior, thread safety, malicious
Python objects, or generated event-accounting parity that the built-in Python
runtime does not currently promise.

## Canonical behavior coverage

| Behavior | Primary fixture or test coverage | Repair PR |
|---|---|---|
| Composite entry chooses the initial transition before plain `during before`. | `composite_initial_guard_uses_enter_state_before_plain_before`, `composite_initial_guard_with_effect_runs_before_plain_before`, `composite_initial_nested_entry_order_survives_deep_choice` | [PR #202](https://github.com/HansBug/pyfcstm/pull/202) |
| Pseudo or non-stoppable candidates are validated speculatively and unstable candidates do not block later valid candidates. | `pseudo_candidate_skips_unstable_branch`, `forced_pseudo_candidate_skips_unstable_branch`, `post_child_exit_continuation_skips_unstable_candidates` | [PR #202](https://github.com/HansBug/pyfcstm/pull/202) |
| Non-converging speculative pseudo chains surface the DFS safety diagnostic instead of becoming a normal rollback cycle. | `pseudo_self_loop_step_limit_raises_dfs_error`, `design_speculative_dfs_safety_limit` | [PR #202](https://github.com/HansBug/pyfcstm/pull/202) |
| Hot-started composites may wait for evented initial transitions without replaying the already-entered boundary. | `hot_start_composite_waits_for_initial_event`, `hot_start_evented_initial_matches_cold_suffix`, `hot_start_deep_evented_initial_waits_for_event` | [PR #203](https://github.com/HansBug/pyfcstm/pull/203) |
| Hot-start constructor safety matches simulator structural-depth limits. | `hot_start_accepts_structural_depth_limit_leaf`, `hot_start_rejects_overdeep_leaf_stack` | [PR #203](https://github.com/HansBug/pyfcstm/pull/203) |
| Persistent `int` and `float` variables normalize consistently for default initializers, hot-start overrides, lifecycle actions, and transition effects. | `persistent_default_int_initializer_normalizes_integer_float`, `persistent_int_writeback_normalizes_integer_float`, `persistent_effect_writeback_normalizes_integer_float`, `persistent_initial_vars_override_skips_initializer`, `hot_start_initial_vars_override_skips_int_initializer` | [PR #204](https://github.com/HansBug/pyfcstm/pull/204) |
| Observation-only abstract hook context uses callsite state and stage metadata for direct calls, refs, aspects, hot starts, and long acyclic ref chains. | `abstract_hook_ref_context_reports_callsite_metadata`, `abstract_hook_context_hot_start_leaf`, `ref_abstract_handler_reports_calling_state`, `lifecycle_ref_chain_resolves_long_acyclic_chain` | [PR #205](https://github.com/HansBug/pyfcstm/pull/205) |
| Generated helper names remain unique for legal nested-vs-flat state paths with similar display names. | `similar_state_paths_keep_actions_distinct` | [PR #206](https://github.com/HansBug/pyfcstm/pull/206) |
| Python expression rendering supports simulator-supported `sign()` in lifecycle actions, guards, effects, aspects, and complex arithmetic. | `sign_function_updates_during_action`, `sign_function_handles_all_signs`, `sign_function_controls_guard_transition`, `sign_function_aligns_aspect_guard_effect_math`, `sign_function_preserves_complex_action_precedence`, `test/render/test_expr.py` | [PR #206](https://github.com/HansBug/pyfcstm/pull/206) |

## Duplicate and control record coverage

| Record | Coverage decision | Evidence |
|---|---|---|
| `E4-DFS-LIMIT-001` | Covered by the DFS safety fixture family. | `pseudo_self_loop_step_limit_raises_dfs_error`, `design_speculative_dfs_safety_limit` |
| `A6-DUP-001`, `A7-DUP-001` | Split across lifecycle/pseudo validation coverage and hook/ref callsite metadata coverage. | `composite_initial_guard_after_named_ref_before_uses_pre_ref_vars`, `forced_pseudo_candidate_skips_unstable_branch`, `abstract_hook_ref_context_reports_callsite_metadata` |
| `B1`, `C1`, `C2`, `E3`, `E9` matched legal-model probes | Covered by representative deep, hot-start, mode-cross-product, and long-run shared fixtures rather than by checking in every generated probe. | `hot_start_deep_evented_initial_waits_for_event`, `scenario_ats_mains_generator_transfer_outage`, `scenario_elevator_door_control_normal`, `scenario_traffic_signal_with_pedestrian_request_pedestrian` |
| `B6` hot/cold equivalence | Covered as the evented-initial hot-start duplicate/control that compares the hot-start suffix against the cold-entered boundary behavior. | `hot_start_evented_initial_matches_cold_suffix` |
| `B2`, `B3`, `D1`, `D2`, `D3`, `C5` lifecycle, transition, and validation neighborhood probes | Covered by composite-entry, pseudo-candidate, DFS, constructor, and persistent-normalization shared fixtures. | `composite_initial_skips_unstable_candidates_root_entry`, `forced_pseudo_candidate_skips_unstable_branch`, `pseudo_self_loop_step_limit_raises_dfs_error`, `persistent_int_writeback_normalizes_integer_float` |
| `B5`, `B10`, `D6`, `E2` hook/ref context probes | Covered by direct ref/aspect context and long ref-chain shared fixtures. | `abstract_hook_ref_context_reports_callsite_metadata`, `ref_abstract_handler_reports_calling_state`, `lifecycle_ref_chain_resolves_long_acyclic_chain` |
| `D9` constructor parity audit | Covered by generated constructor parity helper tests and initial-vars override fixtures. | `test_generated_alignment_constructor_outcome_helper_covers_three_modes`, `persistent_initial_vars_override_skips_initializer`, `hot_start_initial_vars_override_skips_int_initializer` |
| `D10` packaged template audit | Covered by packaged extraction assertions in the unit suite and by the explicit source-template render/alignment command recorded in the closure PR. | `test_generated_python_alignment_uses_packaged_builtin_template`, `make tpl`, `pytest test/template/python/test_semantic_fixture_alignment.py -q` |
| `C8` expression-domain fuzz | `sign()` variants are covered as the repaired expression-rendering class; non-`sign()` matched probes remain final controls. The negative `cbrt` exploratory note remains a manual-review lead, not a repaired bug. | `sign_function_controls_guard_transition`, `sign_function_updates_during_action`, `sign_function_aligns_aspect_guard_effect_math`, `sign_function_preserves_complex_action_precedence` |
| `E7` event-resolution free probe | Fully qualified and documented relative event-path controls are covered. Bare current-model `Event` object mismatches remain out of this alignment repair scope unless separately accepted as a contract. | `event_path_absolute`, `event_path_parent_relative`, `event_path_mixed_formats_full` |

## Verification gates

The final closure gate is:

```bash
make tpl
make rst_auto
pytest test/render/test_expr.py -q
pytest test/simulate/test_semantic_fixtures.py -q
pytest test/template/python/test_semantic_fixture_alignment.py -q
pytest test/template/python/test_runtime.py -q
SKIP_SLOW_TESTS=1 make unittest
```

Representative generated Python artifacts must pass `ruff check` and
`ruff format --check`. For extreme legal DSL expressions, a formatter-only
line-wrapping rewrite with passing runtime alignment and lint remains a
non-blocking style concern under the repository guidance in
[CLAUDE.md](../../../CLAUDE.md).

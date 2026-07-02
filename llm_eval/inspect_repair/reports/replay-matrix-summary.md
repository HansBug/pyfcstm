# Inspect Repair Replay Matrix Summary

- Mode: `replay`
- Case count: 48
- Passed: 48/48
- Fixture set: all manifest fixtures
- Providers: `codex`, `claude`, `codex-deepseek`
- Formats: `llm-json`, `llm-md`
- Gate: parse/model/inspect must leave zero error and warning diagnostics; informational fall-through diagnostics may remain.

| Fixture | Provider | Format | Success | Failure category | Remaining diagnostics | Artifact |
|---|---|---|---:|---|---|---|
| combo_trigger_single | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/combo_trigger_single/claude/llm-json` |
| combo_trigger_single | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/combo_trigger_single/claude/llm-md` |
| combo_trigger_single | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/combo_trigger_single/codex/llm-json` |
| combo_trigger_single | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/combo_trigger_single/codex/llm-md` |
| combo_trigger_single | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/combo_trigger_single/codex-deepseek/llm-json` |
| combo_trigger_single | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/combo_trigger_single/codex-deepseek/llm-md` |
| guard_vars_never_change | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/guard_vars_never_change/claude/llm-json` |
| guard_vars_never_change | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/guard_vars_never_change/claude/llm-md` |
| guard_vars_never_change | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/guard_vars_never_change/codex/llm-json` |
| guard_vars_never_change | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/guard_vars_never_change/codex/llm-md` |
| guard_vars_never_change | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/guard_vars_never_change/codex-deepseek/llm-json` |
| guard_vars_never_change | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/guard_vars_never_change/codex-deepseek/llm-md` |
| multi_diag_stacking | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/multi_diag_stacking/claude/llm-json` |
| multi_diag_stacking | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/multi_diag_stacking/claude/llm-md` |
| multi_diag_stacking | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/multi_diag_stacking/codex/llm-json` |
| multi_diag_stacking | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/multi_diag_stacking/codex/llm-md` |
| multi_diag_stacking | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/multi_diag_stacking/codex-deepseek/llm-json` |
| multi_diag_stacking | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/multi_diag_stacking/codex-deepseek/llm-md` |
| redundant_transition_self_assign | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/redundant_transition_self_assign/claude/llm-json` |
| redundant_transition_self_assign | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/redundant_transition_self_assign/claude/llm-md` |
| redundant_transition_self_assign | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/redundant_transition_self_assign/codex/llm-json` |
| redundant_transition_self_assign | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/redundant_transition_self_assign/codex/llm-md` |
| redundant_transition_self_assign | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/redundant_transition_self_assign/codex-deepseek/llm-json` |
| redundant_transition_self_assign | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/redundant_transition_self_assign/codex-deepseek/llm-md` |
| static_contradictory_guard | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/static_contradictory_guard/claude/llm-json` |
| static_contradictory_guard | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/static_contradictory_guard/claude/llm-md` |
| static_contradictory_guard | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/static_contradictory_guard/codex/llm-json` |
| static_contradictory_guard | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/static_contradictory_guard/codex/llm-md` |
| static_contradictory_guard | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/static_contradictory_guard/codex-deepseek/llm-json` |
| static_contradictory_guard | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/static_contradictory_guard/codex-deepseek/llm-md` |
| suggested_action_adversarial | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/suggested_action_adversarial/claude/llm-json` |
| suggested_action_adversarial | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/suggested_action_adversarial/claude/llm-md` |
| suggested_action_adversarial | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/suggested_action_adversarial/codex/llm-json` |
| suggested_action_adversarial | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/suggested_action_adversarial/codex/llm-md` |
| suggested_action_adversarial | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/suggested_action_adversarial/codex-deepseek/llm-json` |
| suggested_action_adversarial | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/suggested_action_adversarial/codex-deepseek/llm-md` |
| unreachable_state | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/unreachable_state/claude/llm-json` |
| unreachable_state | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/unreachable_state/claude/llm-md` |
| unreachable_state | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/unreachable_state/codex/llm-json` |
| unreachable_state | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/unreachable_state/codex/llm-md` |
| unreachable_state | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/unreachable_state/codex-deepseek/llm-json` |
| unreachable_state | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED, I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/unreachable_state/codex-deepseek/llm-md` |
| verify_backed_dead_guard | claude | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/verify_backed_dead_guard/claude/llm-json` |
| verify_backed_dead_guard | claude | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/verify_backed_dead_guard/claude/llm-md` |
| verify_backed_dead_guard | codex | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/verify_backed_dead_guard/codex/llm-json` |
| verify_backed_dead_guard | codex | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/verify_backed_dead_guard/codex/llm-md` |
| verify_backed_dead_guard | codex-deepseek | llm-json | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/verify_backed_dead_guard/codex-deepseek/llm-json` |
| verify_backed_dead_guard | codex-deepseek | llm-md | yes | passed | I_TRANSITION_NEVER_EVENT_TRIGGERED | `llm_eval/inspect_repair/artifacts/verify_backed_dead_guard/codex-deepseek/llm-md` |

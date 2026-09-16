# BMC solving benchmark

Run `cd24a68e137b`, measured from `HEAD` = `36ae48d50779`.
Baseline `baseline-0cc43647` = `0cc43647ad85c99347fbdd8eab0259279a5f40d0`; reference arm `default`.

5 measured repetitions per sample after 1 discarded warmups per arm, each sample in its own interpreter running from a detached worktree of its arm's commit.

Arms: `baseline-0cc43647` = `0cc43647ad85`; `default` = `36ae48d50779`; `logic` = `36ae48d50779` with options `{"compile": {}, "solve": {"solver_profile": "logic"}}`; `tactic` = `36ae48d50779` with options `{"compile": {}, "solve": {"solver_profile": "tactic"}}`.

## Correctness gate H0

| Case | Query | expected | arm | status | satisfied | outcome | replay | failed samples | H0 |
|---|---|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `conveyor_counters` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `heater_logging` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `pump_supervisor_hooks` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `ratio_estimator` | `forbid` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `ratio_estimator` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `default` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | reference, expected met |
| `ratio_estimator` | `reach` | `unsat` | `logic` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `tactic` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `telemetry_outputs` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |

## Solve time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` |
|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 8.4 | 8.6 | 9.3 | 8.1 |
| `claude_distributed_elevator_can` | `invariant` | 8.9 | 8.7 | 9.6 | 8.2 |
| `claude_distributed_elevator_can` | `reach` | 19.8 | 20.5 | 20.7 | 9.1 |
| `claude_platooning_join_protocol` | `forbid` | 22.5 | 23.7 | 13.5 | 16.1 |
| `claude_platooning_join_protocol` | `invariant` | 20.8 | 21.4 | 15.8 | 16.7 |
| `claude_platooning_join_protocol` | `reach` | 16.3 | 17.1 | 14.3 | 16.6 |
| `claude_traffic_emergency_priority` | `forbid` | 13.3 | 13.7 | 12.2 | 12.8 |
| `claude_traffic_emergency_priority` | `invariant` | 11.4 | 11.4 | 12.6 | 12.9 |
| `claude_traffic_emergency_priority` | `reach` | 25.9 | 26.1 | 17.3 | 17.0 |
| `claude_vtol_mission_supervision` | `forbid` | 16.4 | 16.7 | 11.1 | 12.8 |
| `claude_vtol_mission_supervision` | `invariant` | 17.2 | 17.7 | 10.9 | 12.9 |
| `claude_vtol_mission_supervision` | `reach` | 16.4 | 16.9 | 11.7 | 13.1 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 5.5 | 5.6 | 6.2 | 7.8 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 6.4 | 6.6 | 6.9 | 9.4 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 7.5 | 7.6 | 8.1 | 9.7 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 11.5 | 11.7 | 9.6 | 10.3 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 12.0 | 12.0 | 9.6 | 10.7 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 7.7 | 7.7 | 8.7 | 11.1 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 6.7 | 6.8 | 8.4 | 7.8 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 6.9 | 7.0 | 8.7 | 13.4 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 23.4 | 23.5 | 17.8 | 13.4 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 16.2 | 16.5 | 15.4 | 16.3 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 16.3 | 16.9 | 14.2 | 15.9 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 9.1 | 9.0 | 9.8 | 8.6 |
| `codex_distributed_elevator_can` | `forbid` | 28.0 | 27.9 | 28.6 | 17.6 |
| `codex_distributed_elevator_can` | `invariant` | 35.5 | 36.0 | 37.0 | 19.4 |
| `codex_distributed_elevator_can` | `reach` | 17.2 | 17.3 | 17.7 | 10.9 |
| `codex_platooning_join_protocol` | `forbid` | 26.8 | 27.3 | 20.9 | 23.1 |
| `codex_platooning_join_protocol` | `invariant` | 29.3 | 29.5 | 16.7 | 22.4 |
| `codex_platooning_join_protocol` | `reach` | 26.9 | 27.5 | 21.2 | 23.7 |
| `codex_traffic_emergency_priority` | `forbid` | 10.7 | 11.2 | 14.4 | 10.8 |
| `codex_traffic_emergency_priority` | `invariant` | 9.5 | 9.7 | 13.9 | 6.5 |
| `codex_traffic_emergency_priority` | `reach` | 22.0 | 22.1 | 14.9 | 14.3 |
| `codex_vtol_mission_supervision` | `forbid` | 65.0 | 65.9 | 38.6 | 59.2 |
| `codex_vtol_mission_supervision` | `invariant` | 39.9 | 41.2 | 30.5 | 27.9 |
| `codex_vtol_mission_supervision` | `reach` | 152.5 | 154.8 | 43.2 | 67.6 |
| `conveyor_counters` | `forbid` | 14.8 | 15.4 | 15.7 | 8.4 |
| `conveyor_counters` | `invariant` | 14.8 | 14.5 | 15.3 | 8.4 |
| `conveyor_counters` | `reach` | 16.0 | 16.1 | 16.7 | 5.6 |
| `heater_logging` | `forbid` | 6.1 | 6.1 | 6.7 | 6.0 |
| `heater_logging` | `invariant` | 5.9 | 6.2 | 6.7 | 6.1 |
| `heater_logging` | `reach` | 5.8 | 6.1 | 6.4 | 3.5 |
| `pump_supervisor_hooks` | `forbid` | 4.0 | 4.2 | 6.2 | 5.0 |
| `pump_supervisor_hooks` | `invariant` | 4.3 | 4.4 | 6.1 | 5.1 |
| `pump_supervisor_hooks` | `reach` | 3.1 | 3.6 | 5.1 | 2.4 |
| `ratio_estimator` | `forbid` | 5.7 | 5.9 | 6.6 | 7.7 |
| `ratio_estimator` | `invariant` | 5.0 | 5.2 | 5.9 | 8.0 |
| `ratio_estimator` | `reach` | 5.7 | 5.7 | 6.6 | 29.1 |
| `telemetry_outputs` | `forbid` | 10.3 | 10.6 | 11.3 | 14.1 |
| `telemetry_outputs` | `invariant` | 10.6 | 10.7 | 11.5 | 13.9 |
| `telemetry_outputs` | `reach` | 10.2 | 10.6 | 11.2 | 7.7 |

## Build time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` |
|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 398.8 | 406.4 | 415.8 | 410.2 |
| `claude_distributed_elevator_can` | `invariant` | 405.0 | 402.9 | 408.3 | 409.1 |
| `claude_distributed_elevator_can` | `reach` | 397.7 | 396.9 | 400.5 | 400.7 |
| `claude_platooning_join_protocol` | `forbid` | 283.7 | 285.2 | 287.1 | 292.5 |
| `claude_platooning_join_protocol` | `invariant` | 287.5 | 282.0 | 285.6 | 286.3 |
| `claude_platooning_join_protocol` | `reach` | 281.6 | 279.6 | 278.5 | 286.2 |
| `claude_traffic_emergency_priority` | `forbid` | 1049.6 | 1032.7 | 1041.6 | 1041.7 |
| `claude_traffic_emergency_priority` | `invariant` | 1027.0 | 1037.2 | 1062.2 | 1063.0 |
| `claude_traffic_emergency_priority` | `reach` | 1044.1 | 1041.6 | 1045.5 | 1034.0 |
| `claude_vtol_mission_supervision` | `forbid` | 235.1 | 235.1 | 233.3 | 233.4 |
| `claude_vtol_mission_supervision` | `invariant` | 240.3 | 238.9 | 237.9 | 241.9 |
| `claude_vtol_mission_supervision` | `reach` | 233.9 | 235.6 | 237.7 | 238.8 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 125.3 | 125.5 | 123.7 | 123.8 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 126.4 | 127.2 | 129.7 | 125.7 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 122.7 | 122.5 | 124.0 | 123.3 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 141.1 | 141.0 | 142.0 | 144.1 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 144.6 | 144.8 | 148.3 | 146.5 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 139.5 | 140.8 | 141.1 | 139.6 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 482.7 | 481.8 | 480.7 | 473.8 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 493.2 | 492.5 | 494.5 | 488.7 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 482.7 | 484.2 | 480.6 | 472.3 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 284.2 | 291.7 | 279.9 | 281.9 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 291.2 | 291.0 | 289.1 | 287.2 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 285.7 | 285.3 | 282.3 | 283.5 |
| `codex_distributed_elevator_can` | `forbid` | 526.3 | 535.8 | 528.9 | 524.8 |
| `codex_distributed_elevator_can` | `invariant` | 530.8 | 532.7 | 536.4 | 527.0 |
| `codex_distributed_elevator_can` | `reach` | 525.8 | 523.6 | 529.8 | 528.2 |
| `codex_platooning_join_protocol` | `forbid` | 361.5 | 363.8 | 370.6 | 364.6 |
| `codex_platooning_join_protocol` | `invariant` | 367.3 | 369.8 | 362.7 | 369.9 |
| `codex_platooning_join_protocol` | `reach` | 366.3 | 366.0 | 365.0 | 363.0 |
| `codex_traffic_emergency_priority` | `forbid` | 1078.2 | 1084.2 | 1095.2 | 1093.5 |
| `codex_traffic_emergency_priority` | `invariant` | 1090.8 | 1084.3 | 1086.9 | 1081.4 |
| `codex_traffic_emergency_priority` | `reach` | 1072.2 | 1076.4 | 1089.8 | 1092.3 |
| `codex_vtol_mission_supervision` | `forbid` | 25361.9 | 25382.0 | 25250.2 | 25267.9 |
| `codex_vtol_mission_supervision` | `invariant` | 25211.5 | 25131.4 | 25107.0 | 25134.5 |
| `codex_vtol_mission_supervision` | `reach` | 25210.5 | 25347.6 | 25289.3 | 25274.0 |
| `conveyor_counters` | `forbid` | 192.0 | 195.2 | 192.3 | 195.9 |
| `conveyor_counters` | `invariant` | 195.5 | 195.7 | 197.8 | 200.5 |
| `conveyor_counters` | `reach` | 220.9 | 218.1 | 222.5 | 224.2 |
| `heater_logging` | `forbid` | 138.4 | 138.6 | 139.9 | 139.2 |
| `heater_logging` | `invariant` | 139.0 | 141.3 | 140.0 | 140.1 |
| `heater_logging` | `reach` | 140.1 | 138.8 | 140.4 | 139.3 |
| `pump_supervisor_hooks` | `forbid` | 104.8 | 104.8 | 106.2 | 106.0 |
| `pump_supervisor_hooks` | `invariant` | 105.7 | 104.7 | 106.1 | 106.6 |
| `pump_supervisor_hooks` | `reach` | 71.2 | 71.5 | 72.3 | 71.2 |
| `ratio_estimator` | `forbid` | 75.1 | 74.3 | 74.9 | 74.9 |
| `ratio_estimator` | `invariant` | 74.9 | 75.8 | 77.4 | 76.9 |
| `ratio_estimator` | `reach` | 72.2 | 71.3 | 70.6 | 70.8 |
| `telemetry_outputs` | `forbid` | 235.9 | 236.1 | 235.8 | 238.1 |
| `telemetry_outputs` | `invariant` | 237.5 | 234.5 | 237.5 | 238.6 |
| `telemetry_outputs` | `reach` | 235.1 | 235.9 | 241.4 | 239.9 |

## Replay time by arm (p50 ms, sat only)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` |
|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a |
| `claude_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a |
| `claude_distributed_elevator_can` | `reach` | 9.1 | 9.1 | 9.1 | 9.1 |
| `claude_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a |
| `claude_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a |
| `claude_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `invariant` | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `reach` | 11.9 | 12.0 | 11.9 | 11.9 |
| `claude_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `invariant` | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `reach` | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `reach` | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 8.4 | 8.4 | 8.5 | 8.3 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | n/a | n/a | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 9.9 | 9.5 | 9.7 | 9.3 |
| `codex_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a |
| `codex_distributed_elevator_can` | `reach` | 9.6 | 9.5 | 9.6 | 10.3 |
| `codex_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a |
| `codex_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a |
| `codex_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_traffic_emergency_priority` | `invariant` | 13.9 | 13.6 | 13.6 | 13.6 |
| `codex_traffic_emergency_priority` | `reach` | 13.9 | 14.0 | 13.9 | 14.7 |
| `codex_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a |
| `codex_vtol_mission_supervision` | `invariant` | 27.5 | 27.4 | 27.9 | 26.4 |
| `codex_vtol_mission_supervision` | `reach` | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `forbid` | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `invariant` | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `reach` | 11.3 | 11.0 | 11.0 | 11.3 |
| `heater_logging` | `forbid` | n/a | n/a | n/a | n/a |
| `heater_logging` | `invariant` | n/a | n/a | n/a | n/a |
| `heater_logging` | `reach` | 7.9 | 7.9 | 7.8 | 7.9 |
| `pump_supervisor_hooks` | `forbid` | n/a | n/a | n/a | n/a |
| `pump_supervisor_hooks` | `invariant` | n/a | n/a | n/a | n/a |
| `pump_supervisor_hooks` | `reach` | 5.7 | 5.3 | 5.3 | 5.3 |
| `ratio_estimator` | `forbid` | 4.3 | 4.2 | 4.2 | 4.2 |
| `ratio_estimator` | `invariant` | n/a | n/a | n/a | n/a |
| `ratio_estimator` | `reach` | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `forbid` | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `invariant` | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `reach` | 15.2 | 14.9 | 15.0 | 15.1 |

## Formula size (distinct Z3 AST nodes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` |
|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `2036` | `2036` | `2036` | `2036` |
| `claude_distributed_elevator_can` | `invariant` | `2048` | `2048` | `2048` | `2048` |
| `claude_distributed_elevator_can` | `reach` | `2015` | `2015` | `2015` | `2015` |
| `claude_platooning_join_protocol` | `forbid` | `2303` | `2303` | `2303` | `2303` |
| `claude_platooning_join_protocol` | `invariant` | `2315` | `2315` | `2315` | `2315` |
| `claude_platooning_join_protocol` | `reach` | `2291` | `2291` | `2291` | `2291` |
| `claude_traffic_emergency_priority` | `forbid` | `3509` | `3509` | `3509` | `3509` |
| `claude_traffic_emergency_priority` | `invariant` | `3521` | `3521` | `3521` | `3521` |
| `claude_traffic_emergency_priority` | `reach` | `3486` | `3486` | `3486` | `3486` |
| `claude_vtol_mission_supervision` | `forbid` | `2047` | `2047` | `2047` | `2047` |
| `claude_vtol_mission_supervision` | `invariant` | `2059` | `2059` | `2059` | `2059` |
| `claude_vtol_mission_supervision` | `reach` | `2035` | `2035` | `2035` | `2035` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `1010` | `1010` | `1010` | `1010` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `1022` | `1022` | `1022` | `1022` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `993` | `993` | `993` | `993` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `1314` | `1314` | `1314` | `1314` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `1326` | `1326` | `1326` | `1326` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `1302` | `1302` | `1302` | `1302` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `2045` | `2045` | `2045` | `2045` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `2057` | `2057` | `2057` | `2057` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `2023` | `2023` | `2023` | `2023` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `2574` | `2574` | `2574` | `2574` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `2586` | `2586` | `2586` | `2586` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `2562` | `2562` | `2562` | `2562` |
| `codex_distributed_elevator_can` | `forbid` | `2126` | `2126` | `2126` | `2126` |
| `codex_distributed_elevator_can` | `invariant` | `2138` | `2138` | `2138` | `2138` |
| `codex_distributed_elevator_can` | `reach` | `2102` | `2102` | `2102` | `2102` |
| `codex_platooning_join_protocol` | `forbid` | `2572` | `2572` | `2572` | `2572` |
| `codex_platooning_join_protocol` | `invariant` | `2584` | `2584` | `2584` | `2584` |
| `codex_platooning_join_protocol` | `reach` | `2560` | `2560` | `2560` | `2560` |
| `codex_traffic_emergency_priority` | `forbid` | `3456` | `3456` | `3456` | `3456` |
| `codex_traffic_emergency_priority` | `invariant` | `3468` | `3468` | `3468` | `3468` |
| `codex_traffic_emergency_priority` | `reach` | `3429` | `3429` | `3429` | `3429` |
| `codex_vtol_mission_supervision` | `forbid` | `13456` | `13456` | `13456` | `13456` |
| `codex_vtol_mission_supervision` | `invariant` | `13468` | `13468` | `13468` | `13468` |
| `codex_vtol_mission_supervision` | `reach` | `13444` | `13444` | `13444` | `13444` |
| `conveyor_counters` | `forbid` | `1789` | `1789` | `1789` | `1789` |
| `conveyor_counters` | `invariant` | `1819` | `1819` | `1819` | `1819` |
| `conveyor_counters` | `reach` | `2033` | `2033` | `2033` | `2033` |
| `heater_logging` | `forbid` | `1231` | `1231` | `1231` | `1231` |
| `heater_logging` | `invariant` | `1243` | `1243` | `1243` | `1243` |
| `heater_logging` | `reach` | `1216` | `1216` | `1216` | `1216` |
| `pump_supervisor_hooks` | `forbid` | `1056` | `1056` | `1056` | `1056` |
| `pump_supervisor_hooks` | `invariant` | `1070` | `1070` | `1070` | `1070` |
| `pump_supervisor_hooks` | `reach` | `686` | `686` | `686` | `686` |
| `ratio_estimator` | `forbid` | `717` | `717` | `717` | `717` |
| `ratio_estimator` | `invariant` | `737` | `737` | `737` | `737` |
| `ratio_estimator` | `reach` | `716` | `716` | `716` | `716` |
| `telemetry_outputs` | `forbid` | `2421` | `2421` | `2421` | `2421` |
| `telemetry_outputs` | `invariant` | `2442` | `2442` | `2442` | `2442` |
| `telemetry_outputs` | `reach` | `2399` | `2399` | `2399` | `2399` |

## Peak child RSS (bytes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` |
|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `92540928` | `92749824` | `93093888` | `88711168` |
| `claude_distributed_elevator_can` | `invariant` | `92893184` | `92823552` | `93106176` | `90386432` |
| `claude_distributed_elevator_can` | `reach` | `92868608` | `93302784` | `93237248` | `90791936` |
| `claude_platooning_join_protocol` | `forbid` | `92966912` | `92880896` | `93478912` | `90927104` |
| `claude_platooning_join_protocol` | `invariant` | `93245440` | `93478912` | `93478912` | `91262976` |
| `claude_platooning_join_protocol` | `reach` | `93347840` | `92979200` | `93544448` | `90972160` |
| `claude_traffic_emergency_priority` | `forbid` | `94593024` | `95100928` | `94912512` | `90308608` |
| `claude_traffic_emergency_priority` | `invariant` | `95019008` | `94715904` | `95580160` | `91668480` |
| `claude_traffic_emergency_priority` | `reach` | `94830592` | `94961664` | `95338496` | `92618752` |
| `claude_vtol_mission_supervision` | `forbid` | `92823552` | `92430336` | `93089792` | `90206208` |
| `claude_vtol_mission_supervision` | `invariant` | `92569600` | `92688384` | `92958720` | `90763264` |
| `claude_vtol_mission_supervision` | `reach` | `92512256` | `92483584` | `92844032` | `90263552` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `91262976` | `91045888` | `91463680` | `89649152` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `91312128` | `91308032` | `91586560` | `89821184` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `91021312` | `91107328` | `91787264` | `89731072` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `91484160` | `91447296` | `92045312` | `89821184` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `91488256` | `91430912` | `91652096` | `90046464` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `91439104` | `91525120` | `91672576` | `89894912` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `92434432` | `92663808` | `92618752` | `88780800` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `92594176` | `92708864` | `92614656` | `90824704` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `93093888` | `92844032` | `92983296` | `91000832` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `92729344` | `92667904` | `93351936` | `91226112` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `93036544` | `92844032` | `93356032` | `91258880` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `92602368` | `92569600` | `92819456` | `90877952` |
| `codex_distributed_elevator_can` | `forbid` | `93405184` | `93745152` | `94023680` | `91525120` |
| `codex_distributed_elevator_can` | `invariant` | `93601792` | `93609984` | `94294016` | `91643904` |
| `codex_distributed_elevator_can` | `reach` | `93245440` | `93593600` | `93720576` | `91316224` |
| `codex_platooning_join_protocol` | `forbid` | `93827072` | `93884416` | `94564352` | `91799552` |
| `codex_platooning_join_protocol` | `invariant` | `94269440` | `94146560` | `94932992` | `91914240` |
| `codex_platooning_join_protocol` | `reach` | `94093312` | `94146560` | `94683136` | `91668480` |
| `codex_traffic_emergency_priority` | `forbid` | `95236096` | `95207424` | `95866880` | `92151808` |
| `codex_traffic_emergency_priority` | `invariant` | `95711232` | `95588352` | `96153600` | `92479488` |
| `codex_traffic_emergency_priority` | `reach` | `95584256` | `95584256` | `96030720` | `92962816` |
| `codex_vtol_mission_supervision` | `forbid` | `118042624` | `120049664` | `120283136` | `118444032` |
| `codex_vtol_mission_supervision` | `invariant` | `118939648` | `120061952` | `118099968` | `115630080` |
| `codex_vtol_mission_supervision` | `reach` | `118366208` | `117964800` | `119496704` | `116023296` |
| `conveyor_counters` | `forbid` | `92786688` | `93024256` | `93360128` | `88526848` |
| `conveyor_counters` | `invariant` | `92758016` | `92827648` | `93274112` | `88502272` |
| `conveyor_counters` | `reach` | `93282304` | `93261824` | `93749248` | `89030656` |
| `heater_logging` | `forbid` | `90329088` | `90349568` | `90656768` | `85835776` |
| `heater_logging` | `invariant` | `89939968` | `90472448` | `91262976` | `85970944` |
| `heater_logging` | `reach` | `89960448` | `90087424` | `90849280` | `86188032` |
| `pump_supervisor_hooks` | `forbid` | `89309184` | `89444352` | `90341376` | `86274048` |
| `pump_supervisor_hooks` | `invariant` | `89288704` | `89681920` | `90292224` | `85966848` |
| `pump_supervisor_hooks` | `reach` | `89083904` | `89100288` | `89784320` | `86003712` |
| `ratio_estimator` | `forbid` | `90431488` | `90386432` | `92086272` | `90996736` |
| `ratio_estimator` | `invariant` | `89985024` | `90079232` | `91668480` | `90210304` |
| `ratio_estimator` | `reach` | `89837568` | `89792512` | `91652096` | `91475968` |
| `telemetry_outputs` | `forbid` | `92258304` | `92057600` | `93585408` | `86896640` |
| `telemetry_outputs` | `invariant` | `92266496` | `92315648` | `93671424` | `87097344` |
| `telemetry_outputs` | `reach` | `92139520` | `92282880` | `93483008` | `87003136` |

## Failures and instability

Failed samples: none.
Unstable published fields: none.

## Thresholds

H0 (correctness): **pass** for every arm and query.

| Gate | Arm | Median p50 improvement | Worst query regression | H0 | Adopt |
|---|---|---|---|---|---|
| T1 | `logic` | 2.54% | 46.88% | pass | NOT MET |
| T2 | `tactic` | 7.74% | 409.44% | pass | NOT MET |

Median improvement compares medians of per-query solve p50; worst regression compares each query with its own default p50. Missing measurements or H0 failures prevent adoption.

## Measurement map

| Metric | Source | Note |
|---|---|---|
| `build_ms` | `compile_bmc_query wall time in the child` | prepare, core relation, and property compilation; the region an encoding option changes |
| `solve_ms` | `solve_bmc_property wall time in the child` | the staged primary solve including its verdict; the region a solver option changes |
| `replay_ms` | `decode_bmc_result_trace + replay_bmc_witness wall time in the child` | only when the primary status is sat; absent otherwise |
| `total_elapsed_ms` | `result.total_elapsed_ms` | production ledger; the solver's own accounting of the whole solve |
| `formula_dag_nodes` | `distinct Z3 AST ids reachable from core.core and objective_formula` | a size measure that does not depend on printing or on the process; what a slice shrinks.  Counted after the peak memory reading |
| `status / property_satisfied / outcome / replay_ok` | `result fields and replay.ok` | the correctness gate compares these between arms and against case.json |
| `peak_child_rss_bytes` | `resource.getrusage(RUSAGE_SELF).ru_maxrss in the child, read right after replay` | the kernel high-water mark of the production path; absent where the resource module is unavailable, never zero |
| `solver_statistics` | `result.solver_statistics immediately after the primary check` | actual Z3 statistics; keys vary by profile/version. rlimit count and num allocs are context-wide, not per-query work and not adoption gates |
| `pyfcstm_file` | `pyfcstm.__file__ in the child` | not published; the parent refuses a sample whose package did not come from the arm's worktree |

Confirm this report is a function of the raw records with:

```bash
python tools/run_bmc_solving_benchmark.py --rebuild cd24a68e137b
```

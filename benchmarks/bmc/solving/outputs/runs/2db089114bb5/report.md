# BMC solving benchmark

Run `2db089114bb5`, measured from `HEAD` = `2db089114bb5`.
Baseline `baseline-0cc43647` = `0cc43647ad85c99347fbdd8eab0259279a5f40d0`; reference arm `default`.

5 measured repetitions per sample after 1 discarded warmups per arm, each sample in its own interpreter running from a detached worktree of its arm's commit.

Arms: `baseline-0cc43647` = `0cc43647ad85`; `default` = `2db089114bb5`; `logic` = `2db089114bb5` with options `{"compile": {}, "solve": {"solver_profile": "logic"}}`; `tactic` = `2db089114bb5` with options `{"compile": {}, "solve": {"solver_profile": "tactic"}}`; `cone_slicing` = `2db089114bb5` with options `{"compile": {"cone_slicing": true}, "solve": {}}`.

## Correctness gate H0

| Case | Query | expected | arm | status | satisfied | outcome | replay | failed samples | H0 |
|---|---|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `cone_slicing` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `cone_slicing` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `conveyor_counters` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `heater_logging` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `pump_supervisor_hooks` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `ratio_estimator` | `forbid` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `cone_slicing` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `ratio_estimator` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `default` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | reference, expected met |
| `ratio_estimator` | `reach` | `unsat` | `logic` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `tactic` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `cone_slicing` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `telemetry_outputs` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |

## Solve time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` |
|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 8.9 | 9.0 | 9.6 | 8.7 | 8.9 |
| `claude_distributed_elevator_can` | `invariant` | 9.3 | 9.4 | 9.8 | 9.1 | 9.4 |
| `claude_distributed_elevator_can` | `reach` | 21.4 | 14.7 | 15.2 | 8.9 | 14.8 |
| `claude_platooning_join_protocol` | `forbid` | 23.8 | 23.9 | 14.4 | 16.7 | 22.1 |
| `claude_platooning_join_protocol` | `invariant` | 21.9 | 22.1 | 16.4 | 17.7 | 22.8 |
| `claude_platooning_join_protocol` | `reach` | 17.3 | 17.5 | 15.0 | 17.0 | 15.5 |
| `claude_traffic_emergency_priority` | `forbid` | 14.3 | 14.5 | 13.1 | 13.2 | 14.0 |
| `claude_traffic_emergency_priority` | `invariant` | 11.8 | 12.1 | 13.9 | 13.5 | 11.7 |
| `claude_traffic_emergency_priority` | `reach` | 27.3 | 27.3 | 18.3 | 18.2 | 27.3 |
| `claude_vtol_mission_supervision` | `forbid` | 17.4 | 17.4 | 11.4 | 13.6 | 17.4 |
| `claude_vtol_mission_supervision` | `invariant` | 18.3 | 18.4 | 11.4 | 13.6 | 18.4 |
| `claude_vtol_mission_supervision` | `reach` | 17.2 | 17.5 | 12.5 | 13.9 | 17.5 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 6.2 | 6.1 | 6.4 | 8.4 | 6.1 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 6.8 | 7.0 | 7.4 | 10.0 | 7.0 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 7.7 | 8.0 | 8.4 | 10.3 | 8.0 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 11.9 | 12.1 | 9.8 | 10.7 | 14.0 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 12.5 | 12.5 | 9.5 | 11.3 | 10.0 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 7.9 | 8.1 | 9.6 | 11.3 | 7.5 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 7.1 | 7.2 | 8.9 | 8.2 | 7.0 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 7.0 | 7.5 | 9.0 | 14.1 | 6.9 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 24.2 | 24.2 | 19.3 | 14.0 | 24.5 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 16.6 | 16.9 | 16.8 | 17.3 | 16.3 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 16.9 | 17.1 | 14.9 | 16.8 | 14.7 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 9.5 | 9.4 | 10.0 | 8.9 | 20.1 |
| `codex_distributed_elevator_can` | `forbid` | 29.0 | 29.4 | 29.8 | 18.6 | 28.5 |
| `codex_distributed_elevator_can` | `invariant` | 37.7 | 37.5 | 37.9 | 20.2 | 28.8 |
| `codex_distributed_elevator_can` | `reach` | 17.7 | 17.7 | 18.5 | 11.8 | 17.6 |
| `codex_platooning_join_protocol` | `forbid` | 28.1 | 28.5 | 23.2 | 24.2 | 31.0 |
| `codex_platooning_join_protocol` | `invariant` | 31.6 | 31.2 | 17.3 | 24.0 | 32.7 |
| `codex_platooning_join_protocol` | `reach` | 27.8 | 28.5 | 22.5 | 24.4 | 20.4 |
| `codex_traffic_emergency_priority` | `forbid` | 11.9 | 11.5 | 15.0 | 11.4 | 10.0 |
| `codex_traffic_emergency_priority` | `invariant` | 10.1 | 10.2 | 14.4 | 6.9 | 23.6 |
| `codex_traffic_emergency_priority` | `reach` | 22.9 | 23.4 | 15.7 | 14.2 | 23.2 |
| `codex_vtol_mission_supervision` | `forbid` | 67.9 | 68.2 | 40.5 | 63.5 | 49.8 |
| `codex_vtol_mission_supervision` | `invariant` | 42.7 | 42.3 | 32.2 | 30.7 | 56.6 |
| `codex_vtol_mission_supervision` | `reach` | 161.2 | 159.1 | 45.3 | 71.1 | 119.2 |
| `conveyor_counters` | `forbid` | 16.2 | 16.1 | 16.8 | 9.2 | 10.1 |
| `conveyor_counters` | `invariant` | 15.3 | 15.6 | 16.6 | 8.9 | 11.5 |
| `conveyor_counters` | `reach` | 17.0 | 17.2 | 17.5 | 5.9 | 27.6 |
| `heater_logging` | `forbid` | 6.6 | 6.5 | 7.2 | 6.5 | 4.8 |
| `heater_logging` | `invariant` | 6.3 | 6.6 | 7.0 | 6.4 | 5.1 |
| `heater_logging` | `reach` | 6.3 | 6.4 | 6.9 | 3.7 | 12.9 |
| `pump_supervisor_hooks` | `forbid` | 4.3 | 4.5 | 6.5 | 5.5 | 4.4 |
| `pump_supervisor_hooks` | `invariant` | 4.5 | 4.5 | 6.3 | 5.5 | 4.7 |
| `pump_supervisor_hooks` | `reach` | 3.3 | 3.6 | 5.0 | 2.1 | 3.7 |
| `ratio_estimator` | `forbid` | 6.2 | 6.7 | 7.8 | 8.7 | 6.7 |
| `ratio_estimator` | `invariant` | 5.5 | 5.4 | 6.3 | 8.4 | 5.3 |
| `ratio_estimator` | `reach` | 5.8 | 6.1 | 7.0 | 31.5 | 6.3 |
| `telemetry_outputs` | `forbid` | 11.5 | 11.4 | 12.2 | 15.2 | 7.4 |
| `telemetry_outputs` | `invariant` | 11.7 | 11.9 | 12.6 | 14.7 | 7.5 |
| `telemetry_outputs` | `reach` | 11.1 | 11.5 | 12.1 | 8.3 | 23.3 |

## Build time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` |
|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 424.4 | 415.5 | 415.1 | 433.8 | 419.9 |
| `claude_distributed_elevator_can` | `invariant` | 421.6 | 422.1 | 423.0 | 428.1 | 421.5 |
| `claude_distributed_elevator_can` | `reach` | 420.5 | 415.4 | 412.1 | 414.8 | 415.1 |
| `claude_platooning_join_protocol` | `forbid` | 296.5 | 294.8 | 295.7 | 299.3 | 286.2 |
| `claude_platooning_join_protocol` | `invariant` | 298.7 | 297.1 | 298.8 | 300.5 | 289.8 |
| `claude_platooning_join_protocol` | `reach` | 295.7 | 293.2 | 296.5 | 294.9 | 301.7 |
| `claude_traffic_emergency_priority` | `forbid` | 1074.9 | 1098.6 | 1097.3 | 1078.1 | 1048.4 |
| `claude_traffic_emergency_priority` | `invariant` | 1070.0 | 1082.1 | 1099.3 | 1088.4 | 1046.6 |
| `claude_traffic_emergency_priority` | `reach` | 1068.7 | 1081.1 | 1085.7 | 1075.5 | 1090.5 |
| `claude_vtol_mission_supervision` | `forbid` | 246.5 | 245.9 | 252.3 | 249.6 | 248.1 |
| `claude_vtol_mission_supervision` | `invariant` | 251.5 | 249.8 | 250.4 | 249.9 | 250.9 |
| `claude_vtol_mission_supervision` | `reach` | 247.1 | 248.9 | 251.1 | 247.8 | 245.2 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 139.0 | 132.6 | 131.5 | 131.2 | 130.3 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 134.0 | 133.7 | 133.3 | 133.6 | 134.8 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 129.5 | 130.1 | 128.2 | 128.6 | 128.5 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 149.5 | 149.7 | 147.7 | 148.7 | 131.1 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 153.3 | 153.6 | 152.3 | 152.0 | 137.5 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 149.7 | 149.0 | 157.5 | 149.4 | 130.9 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 502.7 | 497.0 | 498.0 | 495.8 | 487.1 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 502.2 | 507.8 | 512.2 | 505.0 | 502.9 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 492.2 | 498.7 | 528.1 | 501.8 | 502.0 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 293.9 | 293.6 | 308.1 | 292.7 | 287.2 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 296.4 | 298.5 | 301.5 | 294.5 | 286.7 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 291.9 | 293.5 | 292.5 | 292.1 | 286.4 |
| `codex_distributed_elevator_can` | `forbid` | 550.9 | 556.3 | 544.7 | 550.5 | 454.5 |
| `codex_distributed_elevator_can` | `invariant` | 553.2 | 555.0 | 548.0 | 551.4 | 454.2 |
| `codex_distributed_elevator_can` | `reach` | 544.6 | 544.3 | 542.6 | 577.6 | 544.3 |
| `codex_platooning_join_protocol` | `forbid` | 378.6 | 377.8 | 401.0 | 376.8 | 349.1 |
| `codex_platooning_join_protocol` | `invariant` | 388.8 | 383.5 | 380.2 | 382.3 | 352.8 |
| `codex_platooning_join_protocol` | `reach` | 380.7 | 376.9 | 381.7 | 375.3 | 348.5 |
| `codex_traffic_emergency_priority` | `forbid` | 1120.8 | 1124.2 | 1131.5 | 1119.2 | 1010.6 |
| `codex_traffic_emergency_priority` | `invariant` | 1119.1 | 1121.0 | 1119.2 | 1149.2 | 1006.9 |
| `codex_traffic_emergency_priority` | `reach` | 1107.7 | 1121.3 | 1112.5 | 1115.7 | 1124.3 |
| `codex_vtol_mission_supervision` | `forbid` | 26492.9 | 26516.5 | 26475.2 | 26452.1 | 25941.0 |
| `codex_vtol_mission_supervision` | `invariant` | 26531.1 | 26297.6 | 26560.6 | 26609.8 | 26347.1 |
| `codex_vtol_mission_supervision` | `reach` | 26423.7 | 26478.5 | 26517.1 | 26450.9 | 25873.8 |
| `conveyor_counters` | `forbid` | 205.2 | 202.1 | 204.7 | 208.3 | 175.7 |
| `conveyor_counters` | `invariant` | 211.3 | 210.2 | 211.7 | 209.0 | 192.3 |
| `conveyor_counters` | `reach` | 234.7 | 234.7 | 234.7 | 236.6 | 213.0 |
| `heater_logging` | `forbid` | 147.0 | 147.4 | 145.8 | 148.1 | 106.3 |
| `heater_logging` | `invariant` | 147.7 | 147.6 | 148.0 | 148.7 | 108.0 |
| `heater_logging` | `reach` | 147.7 | 147.3 | 145.9 | 144.9 | 104.6 |
| `pump_supervisor_hooks` | `forbid` | 111.7 | 111.6 | 111.6 | 111.9 | 112.7 |
| `pump_supervisor_hooks` | `invariant` | 111.8 | 111.9 | 114.9 | 119.0 | 113.7 |
| `pump_supervisor_hooks` | `reach` | 77.3 | 80.5 | 79.8 | 76.7 | 76.0 |
| `ratio_estimator` | `forbid` | 81.8 | 83.4 | 86.7 | 86.3 | 83.9 |
| `ratio_estimator` | `invariant` | 82.3 | 80.9 | 80.9 | 80.3 | 80.3 |
| `ratio_estimator` | `reach` | 75.8 | 75.7 | 79.0 | 78.6 | 78.7 |
| `telemetry_outputs` | `forbid` | 258.5 | 250.0 | 252.8 | 253.8 | 200.9 |
| `telemetry_outputs` | `invariant` | 251.9 | 250.9 | 254.0 | 252.8 | 191.3 |
| `telemetry_outputs` | `reach` | 259.3 | 255.7 | 254.0 | 255.2 | 197.1 |

## Replay time by arm (p50 ms, sat only)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` |
|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `claude_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `claude_distributed_elevator_can` | `reach` | 9.6 | 9.4 | 9.3 | 9.8 | 9.5 |
| `claude_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `claude_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `claude_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `reach` | 12.7 | 12.5 | 12.5 | 12.7 | 12.4 |
| `claude_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `reach` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `reach` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 8.9 | 8.7 | 9.0 | 8.8 | 8.7 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 10.0 | 9.8 | 10.0 | 9.7 | 12.7 |
| `codex_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `codex_distributed_elevator_can` | `reach` | 10.2 | 9.9 | 9.8 | 11.0 | 10.0 |
| `codex_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `codex_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a | n/a |
| `codex_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_traffic_emergency_priority` | `invariant` | 14.6 | 14.4 | 14.6 | 14.9 | 19.0 |
| `codex_traffic_emergency_priority` | `reach` | 14.7 | 14.6 | 14.6 | 14.6 | 14.8 |
| `codex_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `codex_vtol_mission_supervision` | `invariant` | 28.7 | 28.9 | 28.6 | 28.3 | 31.7 |
| `codex_vtol_mission_supervision` | `reach` | n/a | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `reach` | 11.7 | 11.7 | 11.7 | 11.5 | 17.2 |
| `heater_logging` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `heater_logging` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `heater_logging` | `reach` | 8.6 | 8.6 | 8.4 | 8.1 | 11.4 |
| `pump_supervisor_hooks` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `pump_supervisor_hooks` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `pump_supervisor_hooks` | `reach` | 6.4 | 6.0 | 5.6 | 5.7 | 5.7 |
| `ratio_estimator` | `forbid` | 4.6 | 4.8 | 5.1 | 4.8 | 4.5 |
| `ratio_estimator` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `ratio_estimator` | `reach` | n/a | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `forbid` | n/a | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `invariant` | n/a | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `reach` | 16.2 | 15.8 | 16.2 | 16.2 | 24.1 |

## Formula size (distinct Z3 AST nodes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` |
|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `2036` | `2036` | `2036` | `2036` | `2036` |
| `claude_distributed_elevator_can` | `invariant` | `2048` | `2048` | `2048` | `2048` | `2048` |
| `claude_distributed_elevator_can` | `reach` | `2015` | `2015` | `2015` | `2015` | `2015` |
| `claude_platooning_join_protocol` | `forbid` | `2303` | `2303` | `2303` | `2303` | `2265` |
| `claude_platooning_join_protocol` | `invariant` | `2315` | `2315` | `2315` | `2315` | `2277` |
| `claude_platooning_join_protocol` | `reach` | `2291` | `2291` | `2291` | `2291` | `2253` |
| `claude_traffic_emergency_priority` | `forbid` | `3509` | `3509` | `3509` | `3509` | `3444` |
| `claude_traffic_emergency_priority` | `invariant` | `3521` | `3521` | `3521` | `3521` | `3456` |
| `claude_traffic_emergency_priority` | `reach` | `3486` | `3486` | `3486` | `3486` | `3486` |
| `claude_vtol_mission_supervision` | `forbid` | `2047` | `2047` | `2047` | `2047` | `2047` |
| `claude_vtol_mission_supervision` | `invariant` | `2059` | `2059` | `2059` | `2059` | `2059` |
| `claude_vtol_mission_supervision` | `reach` | `2035` | `2035` | `2035` | `2035` | `2035` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `1010` | `1010` | `1010` | `1010` | `1010` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `1022` | `1022` | `1022` | `1022` | `1022` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `993` | `993` | `993` | `993` | `993` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `1314` | `1314` | `1314` | `1314` | `1200` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `1326` | `1326` | `1326` | `1326` | `1212` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `1302` | `1302` | `1302` | `1302` | `1188` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `2045` | `2045` | `2045` | `2045` | `2007` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `2057` | `2057` | `2057` | `2057` | `2019` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `2023` | `2023` | `2023` | `2023` | `2023` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `2574` | `2574` | `2574` | `2574` | `2554` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `2586` | `2586` | `2586` | `2586` | `2566` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `2562` | `2562` | `2562` | `2562` | `2542` |
| `codex_distributed_elevator_can` | `forbid` | `2126` | `2126` | `2126` | `2126` | `1998` |
| `codex_distributed_elevator_can` | `invariant` | `2138` | `2138` | `2138` | `2138` | `2010` |
| `codex_distributed_elevator_can` | `reach` | `2102` | `2102` | `2102` | `2102` | `2102` |
| `codex_platooning_join_protocol` | `forbid` | `2572` | `2572` | `2572` | `2572` | `2428` |
| `codex_platooning_join_protocol` | `invariant` | `2584` | `2584` | `2584` | `2584` | `2440` |
| `codex_platooning_join_protocol` | `reach` | `2560` | `2560` | `2560` | `2560` | `2416` |
| `codex_traffic_emergency_priority` | `forbid` | `3456` | `3456` | `3456` | `3456` | `3194` |
| `codex_traffic_emergency_priority` | `invariant` | `3468` | `3468` | `3468` | `3468` | `3206` |
| `codex_traffic_emergency_priority` | `reach` | `3429` | `3429` | `3429` | `3429` | `3429` |
| `codex_vtol_mission_supervision` | `forbid` | `13456` | `13456` | `13456` | `13456` | `13264` |
| `codex_vtol_mission_supervision` | `invariant` | `13468` | `13468` | `13468` | `13468` | `13276` |
| `codex_vtol_mission_supervision` | `reach` | `13444` | `13444` | `13444` | `13444` | `13205` |
| `conveyor_counters` | `forbid` | `1789` | `1789` | `1789` | `1789` | `1573` |
| `conveyor_counters` | `invariant` | `1819` | `1819` | `1819` | `1819` | `1603` |
| `conveyor_counters` | `reach` | `2033` | `2033` | `2033` | `2033` | `1785` |
| `heater_logging` | `forbid` | `1231` | `1231` | `1231` | `1231` | `987` |
| `heater_logging` | `invariant` | `1243` | `1243` | `1243` | `1243` | `999` |
| `heater_logging` | `reach` | `1216` | `1216` | `1216` | `1216` | `972` |
| `pump_supervisor_hooks` | `forbid` | `1056` | `1056` | `1056` | `1056` | `1056` |
| `pump_supervisor_hooks` | `invariant` | `1070` | `1070` | `1070` | `1070` | `1070` |
| `pump_supervisor_hooks` | `reach` | `686` | `686` | `686` | `686` | `686` |
| `ratio_estimator` | `forbid` | `717` | `717` | `717` | `717` | `717` |
| `ratio_estimator` | `invariant` | `737` | `737` | `737` | `737` | `737` |
| `ratio_estimator` | `reach` | `716` | `716` | `716` | `716` | `716` |
| `telemetry_outputs` | `forbid` | `2421` | `2421` | `2421` | `2421` | `1992` |
| `telemetry_outputs` | `invariant` | `2442` | `2442` | `2442` | `2442` | `2013` |
| `telemetry_outputs` | `reach` | `2399` | `2399` | `2399` | `2399` | `1970` |

## Peak child RSS (bytes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` |
|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `92626944` | `92971008` | `93233152` | `89296896` | `92618752` |
| `claude_distributed_elevator_can` | `invariant` | `92864512` | `92934144` | `92979200` | `90374144` | `92807168` |
| `claude_distributed_elevator_can` | `reach` | `92643328` | `92975104` | `93528064` | `91017216` | `93224960` |
| `claude_platooning_join_protocol` | `forbid` | `93245440` | `93196288` | `93413376` | `90656768` | `93151232` |
| `claude_platooning_join_protocol` | `invariant` | `93257728` | `93364224` | `93888512` | `91533312` | `92987392` |
| `claude_platooning_join_protocol` | `reach` | `92958720` | `93077504` | `93888512` | `91193344` | `93360128` |
| `claude_traffic_emergency_priority` | `forbid` | `94879744` | `95088640` | `94916608` | `90177536` | `94507008` |
| `claude_traffic_emergency_priority` | `invariant` | `95203328` | `94990336` | `95514624` | `91987968` | `94945280` |
| `claude_traffic_emergency_priority` | `reach` | `95043584` | `95444992` | `95412224` | `92389376` | `95281152` |
| `claude_vtol_mission_supervision` | `forbid` | `92397568` | `92594176` | `92729344` | `90742784` | `92610560` |
| `claude_vtol_mission_supervision` | `invariant` | `92622848` | `92966912` | `92971008` | `91009024` | `92975104` |
| `claude_vtol_mission_supervision` | `reach` | `92643328` | `92524544` | `92868608` | `90480640` | `92680192` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `91131904` | `91009024` | `91295744` | `90218496` | `91529216` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `91664384` | `91299840` | `91582464` | `90099712` | `91287552` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `91074560` | `91287552` | `91774976` | `89952256` | `91660288` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `91656192` | `91271168` | `92049408` | `89780224` | `91660288` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `91578368` | `91701248` | `91869184` | `89956352` | `91459584` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `91582464` | `91705344` | `91914240` | `90222592` | `91553792` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `92438528` | `92700672` | `92954624` | `89169920` | `92704768` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `92364800` | `92827648` | `93134848` | `90705920` | `92721152` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `93237248` | `92897280` | `93081600` | `90669056` | `93233152` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `92573696` | `93233152` | `93360128` | `91054080` | `92897280` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `93102080` | `93233152` | `93487104` | `91533312` | `93102080` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `92860416` | `92725248` | `93114368` | `90836992` | `92913664` |
| `codex_distributed_elevator_can` | `forbid` | `93696000` | `93450240` | `94101504` | `91373568` | `93114368` |
| `codex_distributed_elevator_can` | `invariant` | `94019584` | `93728768` | `94343168` | `91537408` | `93884416` |
| `codex_distributed_elevator_can` | `reach` | `93847552` | `93499392` | `93896704` | `91615232` | `93544448` |
| `codex_platooning_join_protocol` | `forbid` | `93782016` | `94015488` | `94416896` | `91652096` | `93855744` |
| `codex_platooning_join_protocol` | `invariant` | `93609984` | `94408704` | `94941184` | `91791360` | `94007296` |
| `codex_platooning_join_protocol` | `reach` | `94019584` | `94244864` | `94932992` | `91725824` | `94015488` |
| `codex_traffic_emergency_priority` | `forbid` | `94957568` | `95313920` | `96256000` | `92577792` | `94855168` |
| `codex_traffic_emergency_priority` | `invariant` | `95617024` | `95637504` | `96174080` | `92377088` | `95203328` |
| `codex_traffic_emergency_priority` | `reach` | `95645696` | `95981568` | `96374784` | `92966912` | `95731712` |
| `codex_vtol_mission_supervision` | `forbid` | `118804480` | `118964224` | `119156736` | `116355072` | `117252096` |
| `codex_vtol_mission_supervision` | `invariant` | `121090048` | `118984704` | `119185408` | `115597312` | `117415936` |
| `codex_vtol_mission_supervision` | `reach` | `117014528` | `119562240` | `117276672` | `116113408` | `118071296` |
| `conveyor_counters` | `forbid` | `92884992` | `92958720` | `93655040` | `88510464` | `92184576` |
| `conveyor_counters` | `invariant` | `92647424` | `93347840` | `93270016` | `88313856` | `91856896` |
| `conveyor_counters` | `reach` | `93384704` | `93102080` | `93761536` | `88788992` | `92450816` |
| `heater_logging` | `forbid` | `90341376` | `90288128` | `91000832` | `86351872` | `89432064` |
| `heater_logging` | `invariant` | `90476544` | `90120192` | `91267072` | `86265856` | `89694208` |
| `heater_logging` | `reach` | `90341376` | `90284032` | `91152384` | `86540288` | `89694208` |
| `pump_supervisor_hooks` | `forbid` | `89698304` | `89546752` | `90480640` | `86216704` | `89313280` |
| `pump_supervisor_hooks` | `invariant` | `89329664` | `89497600` | `89944064` | `86269952` | `89731072` |
| `pump_supervisor_hooks` | `reach` | `89149440` | `89042944` | `89833472` | `86171648` | `89403392` |
| `ratio_estimator` | `forbid` | `89976832` | `90599424` | `91471872` | `91099136` | `90607616` |
| `ratio_estimator` | `invariant` | `89874432` | `89907200` | `91619328` | `90337280` | `90107904` |
| `ratio_estimator` | `reach` | `89718784` | `90087424` | `91430912` | `91791360` | `90132480` |
| `telemetry_outputs` | `forbid` | `92442624` | `91652096` | `93536256` | `86908928` | `90669056` |
| `telemetry_outputs` | `invariant` | `92442624` | `92430336` | `94023680` | `86896640` | `90742784` |
| `telemetry_outputs` | `reach` | `92160000` | `92176384` | `93339648` | `87113728` | `90742784` |

## Failures and instability

Failed samples: none.
Unstable published fields: none.

## Thresholds

H0 (correctness): **pass** for every arm and query.

| Gate | Arm | Median p50 improvement | Worst query regression | H0 | Adopt |
|---|---|---|---|---|---|
| T1 | `logic` | -1.49% | 45.97% | pass | NOT MET |
| T2 | `tactic` | 5.17% | 417.94% | pass | NOT MET |

Median improvement compares medians of per-query solve p50; worst regression compares each query with its own default p50. Missing measurements or H0 failures prevent adoption.

### T3: conservative cone slicing

- sliced_queries: 32
- unsliced_queries: 19
- dag_reduction: 6.09%
- solve_regression: -0.78%
- unsliced_regression: -0.19%
- fallback_samples: 0
- complete: True
- accepted: False

T3: **NOT MET**. Ratios compare medians of per-query measurements within each actual slice partition. The unsliced metric is the p50 of each sample's build plus solve time. Solve time includes internal replay and any fallback. Missing measurements, an empty partition, or H0 failure prevent adoption.

## Measurement map

| Metric | Source | Note |
|---|---|---|
| `build_ms` | `compile_bmc_query wall time in the child` | prepare, core relation, and property compilation; the region an encoding option changes |
| `solve_ms` | `solve_bmc_property wall time in the child` | staged solving plus internal slicing verification and any full-model retry |
| `replay_ms` | `decode_bmc_result_trace + replay_bmc_witness wall time in the child` | primary SAT witness and response incomplete suffix, when present |
| `total_elapsed_ms` | `result.total_elapsed_ms` | production ledger; the solver's own accounting of the whole solve |
| `formula_dag_nodes` | `distinct Z3 AST ids reachable from core.core and objective_formula` | a size measure that does not depend on printing or on the process; what a slice shrinks.  Counted after the peak memory reading |
| `status / property_satisfied / outcome / replay_ok` | `result fields and replay.ok` | the correctness gate compares these between arms and against case.json |
| `peak_child_rss_bytes` | `resource.getrusage(RUSAGE_SELF).ru_maxrss in the child, read right after replay` | the kernel high-water mark of the production path; absent where the resource module is unavailable, never zero |
| `solver_statistics` | `result.solver_statistics immediately after the primary check` | actual Z3 statistics; keys vary by profile/version. rlimit count and num allocs are context-wide, not per-query work and not adoption gates |
| `pyfcstm_file` | `pyfcstm.__file__ in the child` | not published; the parent refuses a sample whose package did not come from the arm's worktree |

Confirm this report is a function of the raw records with:

```bash
python tools/run_bmc_solving_benchmark.py --rebuild 2db089114bb5
```

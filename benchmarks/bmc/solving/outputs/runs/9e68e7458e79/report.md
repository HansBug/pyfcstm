# BMC solving benchmark

Run `9e68e7458e79`, measured from `HEAD` = `9e68e7458e79`.
Baseline `baseline-0cc43647` = `0cc43647ad85c99347fbdd8eab0259279a5f40d0`; reference arm `default`.

5 measured repetitions per sample after 1 discarded warmups per arm, each sample in its own interpreter running from a detached worktree of its arm's commit.

Arms: `baseline-0cc43647` = `0cc43647ad85`; `default` = `9e68e7458e79`; `logic` = `9e68e7458e79` with options `{"compile": {}, "solve": {"solver_profile": "logic"}}`; `tactic` = `9e68e7458e79` with options `{"compile": {}, "solve": {"solver_profile": "tactic"}}`; `cone_slicing` = `9e68e7458e79` with options `{"compile": {"cone_slicing": true}, "solve": {}}`; `slicing-2db08911` = `2db089114bb5` with options `{"compile": {"cone_slicing": true}, "solve": {}}`.

## Correctness gate H0

| Case | Query | expected | arm | status | satisfied | outcome | replay | failed samples | H0 |
|---|---|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `slicing-2db08911` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `slicing-2db08911` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `slicing-2db08911` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `slicing-2db08911` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `slicing-2db08911` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `cone_slicing` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `slicing-2db08911` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `cone_slicing` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `slicing-2db08911` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `logic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `tactic` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `cone_slicing` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `slicing-2db08911` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `conveyor_counters` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `heater_logging` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `pump_supervisor_hooks` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `ratio_estimator` | `forbid` | `sat` | `logic` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `tactic` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `cone_slicing` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `slicing-2db08911` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `ratio_estimator` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `default` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | reference, expected met |
| `ratio_estimator` | `reach` | `unsat` | `logic` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `tactic` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `cone_slicing` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `slicing-2db08911` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `forbid` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `invariant` | `unsat` | `logic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `tactic` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `cone_slicing` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `slicing-2db08911` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `telemetry_outputs` | `reach` | `sat` | `logic` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `tactic` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `cone_slicing` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `slicing-2db08911` | `sat` | true | `witness_found` | true | 0 | pass |

## Solve time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 12.0 | 12.4 | 14.5 | 12.1 | 13.5 | 14.0 |
| `claude_distributed_elevator_can` | `invariant` | 13.3 | 12.8 | 12.4 | 10.8 | 11.7 | 12.2 |
| `claude_distributed_elevator_can` | `reach` | 24.9 | 17.3 | 18.4 | 11.0 | 18.4 | 18.6 |
| `claude_platooning_join_protocol` | `forbid` | 30.6 | 31.6 | 20.0 | 23.2 | 29.2 | 30.1 |
| `claude_platooning_join_protocol` | `invariant` | 31.9 | 31.9 | 22.8 | 24.8 | 32.0 | 31.2 |
| `claude_platooning_join_protocol` | `reach` | 22.4 | 22.4 | 19.3 | 21.5 | 19.0 | 19.9 |
| `claude_traffic_emergency_priority` | `forbid` | 19.5 | 20.5 | 16.0 | 16.7 | 18.2 | 18.8 |
| `claude_traffic_emergency_priority` | `invariant` | 17.8 | 17.6 | 18.9 | 17.4 | 15.8 | 16.5 |
| `claude_traffic_emergency_priority` | `reach` | 39.0 | 39.8 | 25.9 | 24.8 | 37.5 | 38.7 |
| `claude_vtol_mission_supervision` | `forbid` | 24.5 | 25.0 | 16.8 | 19.3 | 24.0 | 29.3 |
| `claude_vtol_mission_supervision` | `invariant` | 25.5 | 27.0 | 16.6 | 22.4 | 26.6 | 27.5 |
| `claude_vtol_mission_supervision` | `reach` | 22.2 | 22.4 | 17.1 | 19.5 | 23.7 | 22.4 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 7.1 | 7.1 | 7.7 | 10.2 | 6.9 | 6.8 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 7.4 | 7.8 | 8.2 | 11.0 | 7.5 | 7.3 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 10.8 | 12.7 | 11.8 | 12.5 | 9.9 | 10.2 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 12.4 | 12.5 | 10.1 | 10.7 | 14.6 | 14.7 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 12.9 | 12.8 | 9.9 | 11.6 | 10.3 | 10.4 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 8.6 | 8.3 | 9.4 | 11.8 | 7.6 | 7.5 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 7.7 | 8.4 | 9.6 | 8.6 | 7.4 | 7.6 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 7.4 | 8.3 | 9.6 | 14.8 | 7.3 | 7.1 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 24.7 | 24.4 | 19.5 | 14.4 | 24.9 | 25.1 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 17.6 | 17.4 | 16.7 | 18.0 | 17.3 | 17.7 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 17.5 | 18.0 | 15.1 | 17.7 | 15.4 | 15.1 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 10.1 | 10.6 | 10.7 | 9.5 | 21.0 | 21.1 |
| `codex_distributed_elevator_can` | `forbid` | 29.4 | 29.5 | 31.9 | 19.2 | 29.8 | 30.1 |
| `codex_distributed_elevator_can` | `invariant` | 38.9 | 39.1 | 38.8 | 21.0 | 30.3 | 30.9 |
| `codex_distributed_elevator_can` | `reach` | 19.0 | 18.8 | 19.2 | 12.0 | 18.3 | 18.3 |
| `codex_platooning_join_protocol` | `forbid` | 29.1 | 29.5 | 23.6 | 25.1 | 30.8 | 32.0 |
| `codex_platooning_join_protocol` | `invariant` | 32.6 | 31.5 | 18.3 | 24.8 | 32.3 | 33.3 |
| `codex_platooning_join_protocol` | `reach` | 29.1 | 29.3 | 23.0 | 25.2 | 21.2 | 21.7 |
| `codex_traffic_emergency_priority` | `forbid` | 11.4 | 11.6 | 15.6 | 12.1 | 10.4 | 11.4 |
| `codex_traffic_emergency_priority` | `invariant` | 10.3 | 10.3 | 15.0 | 6.9 | 24.1 | 24.7 |
| `codex_traffic_emergency_priority` | `reach` | 23.6 | 23.7 | 16.0 | 14.5 | 24.0 | 23.8 |
| `codex_vtol_mission_supervision` | `forbid` | 69.4 | 68.3 | 40.9 | 66.7 | 54.3 | 50.9 |
| `codex_vtol_mission_supervision` | `invariant` | 43.1 | 44.6 | 33.9 | 32.0 | 59.1 | 60.9 |
| `codex_vtol_mission_supervision` | `reach` | 161.5 | 160.5 | 46.9 | 72.0 | 125.9 | 124.7 |
| `conveyor_counters` | `forbid` | 16.4 | 16.6 | 16.8 | 9.7 | 10.3 | 10.7 |
| `conveyor_counters` | `invariant` | 15.3 | 16.0 | 16.8 | 9.0 | 11.1 | 12.0 |
| `conveyor_counters` | `reach` | 18.1 | 17.6 | 18.5 | 6.2 | 26.3 | 25.9 |
| `heater_logging` | `forbid` | 6.6 | 6.6 | 7.2 | 6.9 | 4.8 | 5.1 |
| `heater_logging` | `invariant` | 6.5 | 6.6 | 7.3 | 6.8 | 5.0 | 5.2 |
| `heater_logging` | `reach` | 6.5 | 6.6 | 7.2 | 3.9 | 13.5 | 13.8 |
| `pump_supervisor_hooks` | `forbid` | 4.5 | 4.8 | 6.9 | 5.2 | 4.9 | 4.7 |
| `pump_supervisor_hooks` | `invariant` | 4.8 | 4.8 | 6.6 | 5.4 | 4.8 | 4.8 |
| `pump_supervisor_hooks` | `reach` | 3.3 | 3.8 | 5.3 | 2.2 | 3.5 | 3.6 |
| `ratio_estimator` | `forbid` | 6.4 | 6.5 | 7.5 | 8.2 | 6.5 | 6.6 |
| `ratio_estimator` | `invariant` | 5.4 | 5.8 | 6.5 | 9.2 | 5.7 | 5.6 |
| `ratio_estimator` | `reach` | 6.3 | 6.1 | 6.9 | 31.8 | 6.2 | 6.3 |
| `telemetry_outputs` | `forbid` | 11.5 | 11.1 | 12.7 | 15.9 | 7.3 | 7.2 |
| `telemetry_outputs` | `invariant` | 11.5 | 11.5 | 12.6 | 15.0 | 7.3 | 7.5 |
| `telemetry_outputs` | `reach` | 11.0 | 11.6 | 12.1 | 8.6 | 23.7 | 23.3 |

## Build time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 586.4 | 744.8 | 615.3 | 611.5 | 603.1 | 630.6 |
| `claude_distributed_elevator_can` | `invariant` | 617.9 | 562.7 | 552.3 | 522.1 | 539.2 | 554.5 |
| `claude_distributed_elevator_can` | `reach` | 515.4 | 518.4 | 531.5 | 508.6 | 538.2 | 561.9 |
| `claude_platooning_join_protocol` | `forbid` | 381.8 | 378.0 | 395.7 | 391.1 | 374.8 | 388.0 |
| `claude_platooning_join_protocol` | `invariant` | 433.5 | 436.4 | 448.3 | 428.6 | 424.8 | 426.1 |
| `claude_platooning_join_protocol` | `reach` | 375.3 | 375.1 | 376.8 | 364.8 | 365.2 | 360.0 |
| `claude_traffic_emergency_priority` | `forbid` | 1516.4 | 1495.8 | 1518.6 | 1439.0 | 1437.7 | 1437.6 |
| `claude_traffic_emergency_priority` | `invariant` | 1500.2 | 1692.2 | 1584.4 | 1483.8 | 1478.3 | 1476.9 |
| `claude_traffic_emergency_priority` | `reach` | 1648.5 | 1602.5 | 1550.2 | 1513.1 | 1491.2 | 1435.0 |
| `claude_vtol_mission_supervision` | `forbid` | 352.7 | 349.3 | 357.1 | 359.0 | 348.2 | 361.3 |
| `claude_vtol_mission_supervision` | `invariant` | 358.5 | 365.8 | 398.0 | 376.0 | 364.5 | 373.2 |
| `claude_vtol_mission_supervision` | `reach` | 334.7 | 316.2 | 351.0 | 337.7 | 337.6 | 316.2 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 158.9 | 157.4 | 160.3 | 157.2 | 146.4 | 147.2 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 149.3 | 147.6 | 148.9 | 153.7 | 149.1 | 148.7 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 182.8 | 195.5 | 181.0 | 159.7 | 160.1 | 160.3 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 153.0 | 153.5 | 156.7 | 149.6 | 137.4 | 140.5 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 159.9 | 156.7 | 160.9 | 158.9 | 141.6 | 144.5 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 159.6 | 158.4 | 155.0 | 152.8 | 136.6 | 137.3 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 538.6 | 552.5 | 552.6 | 524.6 | 518.3 | 522.2 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 539.9 | 554.0 | 539.7 | 520.1 | 526.7 | 524.9 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 525.4 | 506.1 | 521.2 | 518.9 | 531.0 | 535.3 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 306.9 | 305.4 | 304.2 | 310.7 | 303.7 | 306.7 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 308.3 | 306.6 | 305.6 | 306.7 | 298.6 | 298.9 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 310.7 | 311.5 | 310.9 | 310.4 | 300.0 | 298.1 |
| `codex_distributed_elevator_can` | `forbid` | 568.4 | 566.4 | 573.8 | 577.7 | 474.0 | 475.6 |
| `codex_distributed_elevator_can` | `invariant` | 578.3 | 575.2 | 569.9 | 564.4 | 473.9 | 488.1 |
| `codex_distributed_elevator_can` | `reach` | 568.2 | 578.0 | 571.1 | 573.1 | 571.3 | 567.5 |
| `codex_platooning_join_protocol` | `forbid` | 394.7 | 395.7 | 400.6 | 400.8 | 352.7 | 358.5 |
| `codex_platooning_join_protocol` | `invariant` | 398.6 | 397.8 | 392.0 | 401.0 | 365.1 | 359.0 |
| `codex_platooning_join_protocol` | `reach` | 394.9 | 391.1 | 396.0 | 392.9 | 365.8 | 362.1 |
| `codex_traffic_emergency_priority` | `forbid` | 1149.2 | 1150.7 | 1166.3 | 1165.1 | 1066.6 | 1033.9 |
| `codex_traffic_emergency_priority` | `invariant` | 1160.6 | 1156.0 | 1189.4 | 1185.0 | 1055.6 | 1050.0 |
| `codex_traffic_emergency_priority` | `reach` | 1158.0 | 1152.1 | 1144.5 | 1159.7 | 1176.1 | 1160.4 |
| `codex_vtol_mission_supervision` | `forbid` | 26895.1 | 26629.6 | 26555.6 | 27021.6 | 26800.0 | 26662.5 |
| `codex_vtol_mission_supervision` | `invariant` | 27343.8 | 27193.0 | 27543.5 | 27560.4 | 27209.8 | 28213.4 |
| `codex_vtol_mission_supervision` | `reach` | 27003.5 | 26795.3 | 27071.3 | 26726.7 | 26869.4 | 26672.9 |
| `conveyor_counters` | `forbid` | 216.3 | 212.8 | 216.7 | 217.4 | 183.3 | 187.9 |
| `conveyor_counters` | `invariant` | 215.6 | 216.4 | 217.4 | 221.6 | 190.5 | 188.8 |
| `conveyor_counters` | `reach` | 243.3 | 244.8 | 244.6 | 246.3 | 204.9 | 204.9 |
| `heater_logging` | `forbid` | 154.7 | 152.0 | 154.5 | 156.2 | 110.0 | 113.7 |
| `heater_logging` | `invariant` | 154.4 | 152.6 | 154.1 | 153.6 | 109.5 | 110.9 |
| `heater_logging` | `reach` | 153.1 | 151.8 | 157.7 | 154.9 | 109.8 | 110.2 |
| `pump_supervisor_hooks` | `forbid` | 114.3 | 115.2 | 114.6 | 114.9 | 116.1 | 116.2 |
| `pump_supervisor_hooks` | `invariant` | 118.5 | 118.5 | 119.8 | 117.3 | 118.3 | 116.9 |
| `pump_supervisor_hooks` | `reach` | 78.1 | 80.4 | 79.4 | 79.7 | 79.4 | 80.2 |
| `ratio_estimator` | `forbid` | 82.9 | 83.8 | 81.4 | 82.2 | 83.1 | 83.1 |
| `ratio_estimator` | `invariant` | 82.7 | 83.9 | 81.9 | 82.0 | 82.7 | 81.7 |
| `ratio_estimator` | `reach` | 75.8 | 76.9 | 78.4 | 77.9 | 79.7 | 81.1 |
| `telemetry_outputs` | `forbid` | 260.9 | 254.8 | 263.9 | 262.5 | 198.1 | 199.3 |
| `telemetry_outputs` | `invariant` | 255.6 | 254.6 | 261.1 | 260.9 | 198.1 | 201.1 |
| `telemetry_outputs` | `reach` | 255.6 | 256.2 | 259.5 | 275.7 | 195.3 | 198.3 |

## Replay time by arm (p50 ms, sat only)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_distributed_elevator_can` | `reach` | 11.8 | 11.5 | 11.8 | 11.7 | 12.1 | 12.1 |
| `claude_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_traffic_emergency_priority` | `reach` | 17.9 | 18.3 | 19.1 | 16.9 | 17.5 | 16.4 |
| `claude_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 8.9 | 8.8 | 9.4 | 9.6 | 9.1 | 9.6 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 11.1 | 10.3 | 10.2 | 10.4 | 3.2 | 13.6 |
| `codex_distributed_elevator_can` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_distributed_elevator_can` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_distributed_elevator_can` | `reach` | 10.6 | 11.1 | 10.1 | 10.8 | 10.6 | 10.4 |
| `codex_platooning_join_protocol` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_platooning_join_protocol` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_platooning_join_protocol` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_traffic_emergency_priority` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_traffic_emergency_priority` | `invariant` | 14.3 | 14.8 | 15.1 | 14.8 | 5.1 | 19.7 |
| `codex_traffic_emergency_priority` | `reach` | 15.1 | 14.9 | 15.6 | 15.4 | 15.0 | 15.1 |
| `codex_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `codex_vtol_mission_supervision` | `invariant` | 30.3 | 29.4 | 29.5 | 30.3 | 4.4 | 33.7 |
| `codex_vtol_mission_supervision` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `conveyor_counters` | `reach` | 12.2 | 12.0 | 11.9 | 11.9 | 5.3 | 17.0 |
| `heater_logging` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `heater_logging` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `heater_logging` | `reach` | 8.6 | 8.8 | 8.6 | 8.6 | 3.7 | 12.4 |
| `pump_supervisor_hooks` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `pump_supervisor_hooks` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `pump_supervisor_hooks` | `reach` | 6.3 | 6.0 | 6.3 | 5.8 | 5.7 | 5.7 |
| `ratio_estimator` | `forbid` | 4.8 | 4.5 | 4.8 | 4.5 | 4.6 | 4.6 |
| `ratio_estimator` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `ratio_estimator` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `telemetry_outputs` | `reach` | 16.7 | 16.5 | 16.5 | 17.1 | 8.1 | 24.0 |

## Complete API path by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 658.1 | 817.1 | 696.8 | 687.0 | 677.0 | 711.7 |
| `claude_distributed_elevator_can` | `invariant` | 696.6 | 634.4 | 623.1 | 592.9 | 606.2 | 626.9 |
| `claude_distributed_elevator_can` | `reach` | 613.4 | 602.4 | 622.9 | 584.0 | 621.3 | 653.1 |
| `claude_platooning_join_protocol` | `forbid` | 468.8 | 462.6 | 465.4 | 467.3 | 456.2 | 472.6 |
| `claude_platooning_join_protocol` | `invariant` | 523.2 | 527.8 | 545.0 | 511.8 | 515.6 | 515.5 |
| `claude_platooning_join_protocol` | `reach` | 447.1 | 450.3 | 448.5 | 438.0 | 438.7 | 435.0 |
| `claude_traffic_emergency_priority` | `forbid` | 1631.7 | 1610.4 | 1630.0 | 1543.6 | 1549.1 | 1549.4 |
| `claude_traffic_emergency_priority` | `invariant` | 1616.9 | 1815.2 | 1709.3 | 1598.0 | 1588.1 | 1594.7 |
| `claude_traffic_emergency_priority` | `reach` | 1804.9 | 1760.5 | 1699.2 | 1644.4 | 1630.1 | 1588.8 |
| `claude_vtol_mission_supervision` | `forbid` | 446.2 | 431.2 | 434.1 | 441.4 | 430.8 | 449.5 |
| `claude_vtol_mission_supervision` | `invariant` | 444.8 | 470.7 | 486.1 | 460.6 | 452.2 | 455.0 |
| `claude_vtol_mission_supervision` | `reach` | 409.8 | 388.7 | 430.4 | 410.9 | 411.5 | 390.9 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 233.5 | 231.3 | 234.7 | 233.9 | 214.8 | 218.1 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 221.0 | 217.4 | 222.5 | 228.8 | 219.4 | 216.6 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 271.6 | 285.6 | 289.6 | 244.9 | 238.5 | 241.7 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 200.6 | 201.2 | 203.3 | 193.7 | 184.1 | 192.6 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 210.0 | 203.3 | 206.0 | 203.8 | 188.2 | 191.1 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 204.9 | 202.9 | 200.7 | 199.3 | 178.5 | 178.8 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 598.2 | 615.1 | 610.0 | 580.3 | 572.8 | 578.0 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 595.7 | 613.5 | 598.3 | 581.2 | 581.4 | 579.3 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 608.0 | 585.5 | 596.3 | 591.3 | 617.7 | 617.7 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 366.9 | 365.4 | 364.0 | 369.9 | 363.3 | 365.7 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 367.4 | 367.4 | 363.4 | 366.2 | 357.4 | 356.4 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 376.2 | 375.9 | 375.3 | 375.1 | 367.0 | 377.2 |
| `codex_distributed_elevator_can` | `forbid` | 646.3 | 645.5 | 657.8 | 647.6 | 554.6 | 557.8 |
| `codex_distributed_elevator_can` | `invariant` | 666.6 | 664.9 | 658.0 | 634.3 | 553.8 | 574.4 |
| `codex_distributed_elevator_can` | `reach` | 648.8 | 661.5 | 653.5 | 646.0 | 659.0 | 646.7 |
| `codex_platooning_join_protocol` | `forbid` | 472.6 | 475.2 | 473.3 | 475.5 | 431.6 | 439.5 |
| `codex_platooning_join_protocol` | `invariant` | 488.0 | 483.2 | 458.1 | 473.4 | 444.5 | 440.7 |
| `codex_platooning_join_protocol` | `reach` | 475.5 | 468.8 | 471.2 | 467.1 | 440.4 | 433.6 |
| `codex_traffic_emergency_priority` | `forbid` | 1235.2 | 1235.2 | 1255.9 | 1252.4 | 1155.5 | 1120.5 |
| `codex_traffic_emergency_priority` | `invariant` | 1260.1 | 1254.5 | 1296.3 | 1282.5 | 1155.7 | 1167.4 |
| `codex_traffic_emergency_priority` | `reach` | 1269.4 | 1268.7 | 1248.2 | 1263.5 | 1290.9 | 1273.6 |
| `codex_vtol_mission_supervision` | `forbid` | 27015.5 | 26745.7 | 26647.4 | 27146.0 | 26904.0 | 26763.6 |
| `codex_vtol_mission_supervision` | `invariant` | 27469.1 | 27316.7 | 27659.0 | 27673.9 | 27334.1 | 28366.6 |
| `codex_vtol_mission_supervision` | `reach` | 27229.1 | 27004.5 | 27168.4 | 26845.6 | 27048.3 | 26851.7 |
| `conveyor_counters` | `forbid` | 272.6 | 271.4 | 275.0 | 267.7 | 237.3 | 240.2 |
| `conveyor_counters` | `invariant` | 272.7 | 275.6 | 275.7 | 271.7 | 243.1 | 243.1 |
| `conveyor_counters` | `reach` | 314.0 | 313.8 | 316.9 | 306.3 | 276.4 | 287.3 |
| `heater_logging` | `forbid` | 200.5 | 197.5 | 201.1 | 202.6 | 152.8 | 157.2 |
| `heater_logging` | `invariant` | 198.8 | 197.2 | 198.7 | 198.1 | 152.6 | 154.6 |
| `heater_logging` | `reach` | 206.7 | 205.7 | 214.0 | 204.9 | 166.0 | 176.0 |
| `pump_supervisor_hooks` | `forbid` | 155.9 | 157.0 | 158.3 | 156.9 | 158.4 | 158.7 |
| `pump_supervisor_hooks` | `invariant` | 163.6 | 161.2 | 163.8 | 160.0 | 161.8 | 158.7 |
| `pump_supervisor_hooks` | `reach` | 124.8 | 126.2 | 129.0 | 123.8 | 126.3 | 126.4 |
| `ratio_estimator` | `forbid` | 127.6 | 129.1 | 130.8 | 131.3 | 128.7 | 129.6 |
| `ratio_estimator` | `invariant` | 123.2 | 124.2 | 122.7 | 126.8 | 122.4 | 122.2 |
| `ratio_estimator` | `reach` | 117.3 | 117.9 | 120.8 | 144.9 | 124.3 | 121.8 |
| `telemetry_outputs` | `forbid` | 310.7 | 304.7 | 316.2 | 315.1 | 243.9 | 244.8 |
| `telemetry_outputs` | `invariant` | 306.3 | 305.8 | 310.7 | 315.6 | 244.5 | 248.2 |
| `telemetry_outputs` | `reach` | 323.7 | 322.5 | 325.9 | 346.1 | 264.9 | 285.7 |

## Build, solve and replay by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 599.1 | 756.7 | 629.2 | 623.6 | 614.5 | 644.7 |
| `claude_distributed_elevator_can` | `invariant` | 631.4 | 577.3 | 564.5 | 532.8 | 550.7 | 567.0 |
| `claude_distributed_elevator_can` | `reach` | 549.4 | 547.2 | 562.3 | 530.4 | 568.0 | 591.8 |
| `claude_platooning_join_protocol` | `forbid` | 412.3 | 408.4 | 413.7 | 413.0 | 404.6 | 418.3 |
| `claude_platooning_join_protocol` | `invariant` | 465.4 | 466.4 | 471.0 | 453.3 | 456.8 | 459.7 |
| `claude_platooning_join_protocol` | `reach` | 398.1 | 397.8 | 396.1 | 387.1 | 384.4 | 380.7 |
| `claude_traffic_emergency_priority` | `forbid` | 1534.9 | 1516.7 | 1534.7 | 1454.8 | 1455.9 | 1461.7 |
| `claude_traffic_emergency_priority` | `invariant` | 1517.4 | 1710.2 | 1605.1 | 1501.3 | 1494.5 | 1496.6 |
| `claude_traffic_emergency_priority` | `reach` | 1706.0 | 1662.1 | 1597.6 | 1550.5 | 1545.1 | 1490.3 |
| `claude_vtol_mission_supervision` | `forbid` | 379.2 | 374.3 | 373.4 | 380.1 | 372.2 | 388.0 |
| `claude_vtol_mission_supervision` | `invariant` | 383.8 | 390.9 | 420.3 | 397.5 | 392.8 | 400.7 |
| `claude_vtol_mission_supervision` | `reach` | 355.8 | 338.1 | 368.2 | 357.2 | 361.3 | 338.7 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 165.4 | 164.4 | 169.3 | 167.0 | 153.6 | 154.0 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 156.8 | 155.4 | 157.0 | 165.0 | 156.9 | 155.9 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 192.3 | 206.4 | 195.1 | 172.4 | 170.4 | 170.5 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 167.1 | 167.1 | 166.9 | 160.2 | 151.3 | 155.2 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 172.1 | 169.4 | 171.4 | 170.6 | 151.8 | 155.1 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 167.7 | 166.7 | 165.7 | 164.9 | 143.9 | 144.8 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 547.0 | 561.0 | 562.2 | 533.1 | 525.7 | 529.7 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 547.3 | 562.3 | 549.2 | 534.6 | 534.0 | 531.9 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 559.0 | 539.1 | 550.3 | 543.3 | 566.4 | 569.5 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 324.4 | 322.8 | 320.7 | 328.4 | 320.8 | 323.4 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 325.9 | 324.7 | 320.7 | 324.4 | 314.2 | 314.1 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 330.7 | 332.8 | 333.1 | 329.7 | 324.3 | 334.1 |
| `codex_distributed_elevator_can` | `forbid` | 597.7 | 595.8 | 605.7 | 597.2 | 503.8 | 505.9 |
| `codex_distributed_elevator_can` | `invariant` | 617.4 | 613.8 | 608.7 | 585.5 | 503.3 | 519.0 |
| `codex_distributed_elevator_can` | `reach` | 597.1 | 606.9 | 600.6 | 596.7 | 600.7 | 595.8 |
| `codex_platooning_join_protocol` | `forbid` | 422.7 | 426.4 | 423.7 | 425.8 | 383.4 | 390.8 |
| `codex_platooning_join_protocol` | `invariant` | 431.6 | 433.9 | 410.3 | 425.0 | 397.4 | 393.3 |
| `codex_platooning_join_protocol` | `reach` | 424.0 | 420.4 | 418.4 | 416.7 | 387.0 | 383.5 |
| `codex_traffic_emergency_priority` | `forbid` | 1160.5 | 1162.5 | 1182.2 | 1179.1 | 1076.9 | 1045.5 |
| `codex_traffic_emergency_priority` | `invariant` | 1184.6 | 1181.2 | 1219.3 | 1207.2 | 1085.0 | 1094.8 |
| `codex_traffic_emergency_priority` | `reach` | 1196.9 | 1191.2 | 1176.4 | 1190.2 | 1215.5 | 1198.0 |
| `codex_vtol_mission_supervision` | `forbid` | 26964.1 | 26697.3 | 26596.5 | 27093.6 | 26854.9 | 26714.8 |
| `codex_vtol_mission_supervision` | `invariant` | 27415.4 | 27266.7 | 27606.8 | 27621.3 | 27269.9 | 28308.3 |
| `codex_vtol_mission_supervision` | `reach` | 27170.0 | 26955.4 | 27119.3 | 26797.4 | 26995.3 | 26797.8 |
| `conveyor_counters` | `forbid` | 232.7 | 229.1 | 233.3 | 227.5 | 193.4 | 198.5 |
| `conveyor_counters` | `invariant` | 231.9 | 232.4 | 234.3 | 231.0 | 201.7 | 200.9 |
| `conveyor_counters` | `reach` | 274.0 | 274.3 | 275.1 | 264.7 | 236.1 | 247.0 |
| `heater_logging` | `forbid` | 161.3 | 159.3 | 161.7 | 162.8 | 115.1 | 119.2 |
| `heater_logging` | `invariant` | 161.3 | 159.3 | 161.0 | 160.4 | 114.9 | 116.3 |
| `heater_logging` | `reach` | 168.1 | 167.2 | 173.5 | 167.6 | 127.0 | 136.8 |
| `pump_supervisor_hooks` | `forbid` | 118.7 | 120.4 | 121.6 | 120.4 | 120.7 | 121.0 |
| `pump_supervisor_hooks` | `invariant` | 123.4 | 123.2 | 126.3 | 123.0 | 123.0 | 121.5 |
| `pump_supervisor_hooks` | `reach` | 88.2 | 90.5 | 90.6 | 87.6 | 88.7 | 89.6 |
| `ratio_estimator` | `forbid` | 93.6 | 94.7 | 94.8 | 95.5 | 94.5 | 94.7 |
| `ratio_estimator` | `invariant` | 88.0 | 89.7 | 88.2 | 91.2 | 88.4 | 87.2 |
| `ratio_estimator` | `reach` | 82.3 | 83.5 | 85.5 | 109.2 | 86.3 | 87.5 |
| `telemetry_outputs` | `forbid` | 271.9 | 266.5 | 276.6 | 278.5 | 206.2 | 206.5 |
| `telemetry_outputs` | `invariant` | 267.6 | 266.9 | 273.7 | 276.1 | 205.4 | 208.1 |
| `telemetry_outputs` | `reach` | 282.5 | 284.6 | 287.9 | 304.0 | 227.0 | 245.3 |

## Complete paths by reference SAT/UNSAT status

| Reference status | Metric | Arm | Queries | Default p50 ms | Arm p50 ms | Change | Worst change | Worst query |
|---|---|---|---|---|---|---|---|---|
| sat | api_total_ms | baseline-0cc43647 | 13 | 585.5 | 608.0 | 3.84% | 3.84% | codex_deepseek_traffic_emergency_priority/reach |
| sat | api_total_ms | default | 13 | 585.5 | 585.5 | 0.00% | 0.00% | claude_distributed_elevator_can/reach |
| sat | api_total_ms | logic | 13 | 585.5 | 596.3 | 1.85% | 4.00% | heater_logging/reach |
| sat | api_total_ms | tactic | 13 | 585.5 | 584.0 | -0.25% | 7.32% | telemetry_outputs/reach |
| sat | api_total_ms | cone_slicing | 13 | 585.5 | 617.7 | 5.51% | 5.51% | codex_deepseek_traffic_emergency_priority/reach |
| sat | api_total_ms | slicing-2db08911 | 13 | 585.5 | 617.7 | 5.50% | 8.42% | claude_distributed_elevator_can/reach |
| sat | pipeline_ms | baseline-0cc43647 | 13 | 539.1 | 549.4 | 1.92% | 3.69% | codex_deepseek_traffic_emergency_priority/reach |
| sat | pipeline_ms | default | 13 | 539.1 | 539.1 | 0.00% | 0.00% | claude_distributed_elevator_can/reach |
| sat | pipeline_ms | logic | 13 | 539.1 | 550.3 | 2.08% | 3.75% | heater_logging/reach |
| sat | pipeline_ms | tactic | 13 | 539.1 | 530.4 | -1.62% | 6.84% | telemetry_outputs/reach |
| sat | pipeline_ms | cone_slicing | 13 | 539.1 | 566.4 | 5.07% | 5.07% | codex_deepseek_traffic_emergency_priority/reach |
| sat | pipeline_ms | slicing-2db08911 | 13 | 539.1 | 569.5 | 5.64% | 8.15% | claude_distributed_elevator_can/reach |
| unsat | api_total_ms | baseline-0cc43647 | 38 | 388.7 | 409.8 | 5.43% | 9.81% | claude_distributed_elevator_can/invariant |
| unsat | api_total_ms | default | 38 | 388.7 | 388.7 | 0.00% | 0.00% | claude_distributed_elevator_can/forbid |
| unsat | api_total_ms | logic | 38 | 388.7 | 430.4 | 10.73% | 10.73% | claude_vtol_mission_supervision/reach |
| unsat | api_total_ms | tactic | 38 | 388.7 | 410.9 | 5.70% | 22.85% | ratio_estimator/reach |
| unsat | api_total_ms | cone_slicing | 38 | 388.7 | 411.5 | 5.85% | 5.85% | claude_vtol_mission_supervision/reach |
| unsat | api_total_ms | slicing-2db08911 | 38 | 388.7 | 390.9 | 0.57% | 4.26% | claude_vtol_mission_supervision/forbid |
| unsat | pipeline_ms | baseline-0cc43647 | 38 | 338.1 | 355.8 | 5.26% | 9.37% | claude_distributed_elevator_can/invariant |
| unsat | pipeline_ms | default | 38 | 338.1 | 338.1 | 0.00% | 0.00% | claude_distributed_elevator_can/forbid |
| unsat | pipeline_ms | logic | 38 | 338.1 | 368.2 | 8.92% | 8.92% | claude_vtol_mission_supervision/reach |
| unsat | pipeline_ms | tactic | 38 | 338.1 | 357.2 | 5.65% | 30.79% | ratio_estimator/reach |
| unsat | pipeline_ms | cone_slicing | 38 | 338.1 | 361.3 | 6.87% | 6.87% | claude_vtol_mission_supervision/reach |
| unsat | pipeline_ms | slicing-2db08911 | 38 | 338.1 | 338.7 | 0.18% | 4.85% | ratio_estimator/reach |

Groups use the default arm's status. Medians aggregate per-query p50s; worst change compares each query with its own default. Positive change means slower. These diagnostic groups do not alter H0 or T3.

## Formula size (distinct Z3 AST nodes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `2036` | `2036` | `2036` | `2036` | `2036` | `2036` |
| `claude_distributed_elevator_can` | `invariant` | `2048` | `2048` | `2048` | `2048` | `2048` | `2048` |
| `claude_distributed_elevator_can` | `reach` | `2015` | `2015` | `2015` | `2015` | `2015` | `2015` |
| `claude_platooning_join_protocol` | `forbid` | `2303` | `2303` | `2303` | `2303` | `2265` | `2265` |
| `claude_platooning_join_protocol` | `invariant` | `2315` | `2315` | `2315` | `2315` | `2277` | `2277` |
| `claude_platooning_join_protocol` | `reach` | `2291` | `2291` | `2291` | `2291` | `2253` | `2253` |
| `claude_traffic_emergency_priority` | `forbid` | `3509` | `3509` | `3509` | `3509` | `3444` | `3444` |
| `claude_traffic_emergency_priority` | `invariant` | `3521` | `3521` | `3521` | `3521` | `3456` | `3456` |
| `claude_traffic_emergency_priority` | `reach` | `3486` | `3486` | `3486` | `3486` | `3486` | `3486` |
| `claude_vtol_mission_supervision` | `forbid` | `2047` | `2047` | `2047` | `2047` | `2047` | `2047` |
| `claude_vtol_mission_supervision` | `invariant` | `2059` | `2059` | `2059` | `2059` | `2059` | `2059` |
| `claude_vtol_mission_supervision` | `reach` | `2035` | `2035` | `2035` | `2035` | `2035` | `2035` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `1010` | `1010` | `1010` | `1010` | `1010` | `1010` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `1022` | `1022` | `1022` | `1022` | `1022` | `1022` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `993` | `993` | `993` | `993` | `993` | `993` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `1314` | `1314` | `1314` | `1314` | `1200` | `1200` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `1326` | `1326` | `1326` | `1326` | `1212` | `1212` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `1302` | `1302` | `1302` | `1302` | `1188` | `1188` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `2045` | `2045` | `2045` | `2045` | `2007` | `2007` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `2057` | `2057` | `2057` | `2057` | `2019` | `2019` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `2023` | `2023` | `2023` | `2023` | `2023` | `2023` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `2574` | `2574` | `2574` | `2574` | `2554` | `2554` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `2586` | `2586` | `2586` | `2586` | `2566` | `2566` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `2562` | `2562` | `2562` | `2562` | `2542` | `2542` |
| `codex_distributed_elevator_can` | `forbid` | `2126` | `2126` | `2126` | `2126` | `1998` | `1998` |
| `codex_distributed_elevator_can` | `invariant` | `2138` | `2138` | `2138` | `2138` | `2010` | `2010` |
| `codex_distributed_elevator_can` | `reach` | `2102` | `2102` | `2102` | `2102` | `2102` | `2102` |
| `codex_platooning_join_protocol` | `forbid` | `2572` | `2572` | `2572` | `2572` | `2428` | `2428` |
| `codex_platooning_join_protocol` | `invariant` | `2584` | `2584` | `2584` | `2584` | `2440` | `2440` |
| `codex_platooning_join_protocol` | `reach` | `2560` | `2560` | `2560` | `2560` | `2416` | `2416` |
| `codex_traffic_emergency_priority` | `forbid` | `3456` | `3456` | `3456` | `3456` | `3194` | `3194` |
| `codex_traffic_emergency_priority` | `invariant` | `3468` | `3468` | `3468` | `3468` | `3206` | `3206` |
| `codex_traffic_emergency_priority` | `reach` | `3429` | `3429` | `3429` | `3429` | `3429` | `3429` |
| `codex_vtol_mission_supervision` | `forbid` | `13456` | `13456` | `13456` | `13456` | `13264` | `13264` |
| `codex_vtol_mission_supervision` | `invariant` | `13468` | `13468` | `13468` | `13468` | `13276` | `13276` |
| `codex_vtol_mission_supervision` | `reach` | `13444` | `13444` | `13444` | `13444` | `13205` | `13205` |
| `conveyor_counters` | `forbid` | `1789` | `1789` | `1789` | `1789` | `1573` | `1573` |
| `conveyor_counters` | `invariant` | `1819` | `1819` | `1819` | `1819` | `1603` | `1603` |
| `conveyor_counters` | `reach` | `2033` | `2033` | `2033` | `2033` | `1785` | `1785` |
| `heater_logging` | `forbid` | `1231` | `1231` | `1231` | `1231` | `987` | `987` |
| `heater_logging` | `invariant` | `1243` | `1243` | `1243` | `1243` | `999` | `999` |
| `heater_logging` | `reach` | `1216` | `1216` | `1216` | `1216` | `972` | `972` |
| `pump_supervisor_hooks` | `forbid` | `1056` | `1056` | `1056` | `1056` | `1056` | `1056` |
| `pump_supervisor_hooks` | `invariant` | `1070` | `1070` | `1070` | `1070` | `1070` | `1070` |
| `pump_supervisor_hooks` | `reach` | `686` | `686` | `686` | `686` | `686` | `686` |
| `ratio_estimator` | `forbid` | `717` | `717` | `717` | `717` | `717` | `717` |
| `ratio_estimator` | `invariant` | `737` | `737` | `737` | `737` | `737` | `737` |
| `ratio_estimator` | `reach` | `716` | `716` | `716` | `716` | `716` | `716` |
| `telemetry_outputs` | `forbid` | `2421` | `2421` | `2421` | `2421` | `1992` | `1992` |
| `telemetry_outputs` | `invariant` | `2442` | `2442` | `2442` | `2442` | `2013` | `2013` |
| `telemetry_outputs` | `reach` | `2399` | `2399` | `2399` | `2399` | `1970` | `1970` |

## Peak child RSS (bytes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `92975104` | `93106176` | `93368320` | `89174016` | `92975104` | `92971008` |
| `claude_distributed_elevator_can` | `invariant` | `93106176` | `92971008` | `93364224` | `90456064` | `93102080` | `93061120` |
| `claude_distributed_elevator_can` | `reach` | `93241344` | `93097984` | `93634560` | `90955776` | `93306880` | `93233152` |
| `claude_platooning_join_protocol` | `forbid` | `93106176` | `93454336` | `93769728` | `91275264` | `93495296` | `93491200` |
| `claude_platooning_join_protocol` | `invariant` | `93626368` | `93626368` | `93892608` | `91398144` | `93503488` | `93626368` |
| `claude_platooning_join_protocol` | `reach` | `92971008` | `93368320` | `93663232` | `91402240` | `93057024` | `93233152` |
| `claude_traffic_emergency_priority` | `forbid` | `94937088` | `95195136` | `95207424` | `90746880` | `94695424` | `94679040` |
| `claude_traffic_emergency_priority` | `invariant` | `95211520` | `95330304` | `95727616` | `91926528` | `94687232` | `94928896` |
| `claude_traffic_emergency_priority` | `reach` | `95465472` | `95465472` | `95584256` | `92803072` | `95309824` | `95203328` |
| `claude_vtol_mission_supervision` | `forbid` | `92581888` | `92618752` | `92921856` | `90877952` | `92700672` | `92839936` |
| `claude_vtol_mission_supervision` | `invariant` | `92975104` | `93102080` | `93097984` | `90873856` | `92930048` | `92979200` |
| `claude_vtol_mission_supervision` | `reach` | `92536832` | `92372992` | `93040640` | `90615808` | `92704768` | `92520448` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `91013120` | `90877952` | `91443200` | `89882624` | `91402240` | `90873856` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `91656192` | `91258880` | `91578368` | `89808896` | `91041792` | `91516928` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `91533312` | `91398144` | `91488256` | `89739264` | `91398144` | `91164672` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `91529216` | `91787264` | `91893760` | `90226688` | `91402240` | `91529216` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `91725824` | `91467776` | `91566080` | `90128384` | `91004928` | `91398144` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `91344896` | `91082752` | `91791360` | `89886720` | `91119616` | `90877952` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `92504064` | `92839936` | `93114368` | `88354816` | `92311552` | `92368896` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `92844032` | `92725248` | `93028352` | `91000832` | `92835840` | `92614656` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `92917760` | `92909568` | `92823552` | `90693632` | `92594176` | `92975104` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `92975104` | `93097984` | `92995584` | `90992640` | `92688384` | `92585984` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `92991488` | `92971008` | `93077504` | `91078656` | `92966912` | `92901376` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `93102080` | `93097984` | `92717056` | `91090944` | `92975104` | `92778496` |
| `codex_distributed_elevator_can` | `forbid` | `93757440` | `93659136` | `94154752` | `91140096` | `93626368` | `93429760` |
| `codex_distributed_elevator_can` | `invariant` | `93523968` | `94150656` | `94285824` | `91561984` | `93515776` | `93655040` |
| `codex_distributed_elevator_can` | `reach` | `93761536` | `93679616` | `93765632` | `91660288` | `93888512` | `93396992` |
| `codex_platooning_join_protocol` | `forbid` | `93843456` | `94134272` | `94179328` | `91668480` | `94015488` | `93949952` |
| `codex_platooning_join_protocol` | `invariant` | `93888512` | `94416896` | `94482432` | `91783168` | `94085120` | `94281728` |
| `codex_platooning_join_protocol` | `reach` | `94023680` | `94429184` | `94810112` | `91926528` | `93343744` | `93323264` |
| `codex_traffic_emergency_priority` | `forbid` | `95232000` | `95399936` | `95965184` | `92192768` | `94179328` | `95199232` |
| `codex_traffic_emergency_priority` | `invariant` | `95395840` | `95662080` | `96051200` | `92585984` | `94695424` | `94908416` |
| `codex_traffic_emergency_priority` | `reach` | `95391744` | `95580160` | `96239616` | `92827648` | `95539200` | `95490048` |
| `codex_vtol_mission_supervision` | `forbid` | `120066048` | `117637120` | `119160832` | `115789824` | `118120448` | `119406592` |
| `codex_vtol_mission_supervision` | `invariant` | `119054336` | `117166080` | `118988800` | `117370880` | `117653504` | `119132160` |
| `codex_vtol_mission_supervision` | `reach` | `117051392` | `118980608` | `118030336` | `115634176` | `119046144` | `116846592` |
| `conveyor_counters` | `forbid` | `92737536` | `92774400` | `93216768` | `88780800` | `92012544` | `92262400` |
| `conveyor_counters` | `invariant` | `93102080` | `92823552` | `93499392` | `88502272` | `91795456` | `92057600` |
| `conveyor_counters` | `reach` | `93495296` | `93429760` | `94023680` | `88907776` | `92717056` | `92717056` |
| `heater_logging` | `forbid` | `90210304` | `90165248` | `90935296` | `86286336` | `89395200` | `89362432` |
| `heater_logging` | `invariant` | `90230784` | `90148864` | `90693632` | `86413312` | `89174016` | `89436160` |
| `heater_logging` | `reach` | `90312704` | `90476544` | `91115520` | `86552576` | `89460736` | `89649152` |
| `pump_supervisor_hooks` | `forbid` | `89354240` | `89698304` | `90238976` | `86163456` | `89358336` | `89354240` |
| `pump_supervisor_hooks` | `invariant` | `89276416` | `89686016` | `90476544` | `85991424` | `89690112` | `89427968` |
| `pump_supervisor_hooks` | `reach` | `89309184` | `88915968` | `90099712` | `86183936` | `88981504` | `89161728` |
| `ratio_estimator` | `forbid` | `90419200` | `90120192` | `92188672` | `90861568` | `90509312` | `90480640` |
| `ratio_estimator` | `invariant` | `89976832` | `90021888` | `91799552` | `89952256` | `90353664` | `90218496` |
| `ratio_estimator` | `reach` | `90218496` | `89874432` | `90865664` | `91267072` | `90251264` | `89583616` |
| `telemetry_outputs` | `forbid` | `92319744` | `92045312` | `93454336` | `87072768` | `91009024` | `90484736` |
| `telemetry_outputs` | `invariant` | `92004352` | `92192768` | `93892608` | `86925312` | `91009024` | `90734592` |
| `telemetry_outputs` | `reach` | `91959296` | `91897856` | `93708288` | `86933504` | `91009024` | `91009024` |

## Failures and instability

Failed samples: none.
Unstable published fields: none.

## Thresholds

H0 (correctness): **pass** for every arm and query.

| Gate | Arm | Median p50 improvement | Worst query regression | H0 | Adopt |
|---|---|---|---|---|---|
| T1 | `logic` | 2.05% | 45.30% | pass | NOT MET |
| T2 | `tactic` | 21.61% | 422.66% | pass | NOT MET |

Median improvement compares medians of per-query solve p50; worst regression compares each query with its own default p50. Missing measurements or H0 failures prevent adoption.

### T3: conservative cone slicing

- sliced_queries: 32
- unsliced_queries: 19
- dag_reduction: 6.09%
- solve_regression: 4.47%
- unsliced_regression: 6.87%
- fallback_samples: 0
- complete: True
- accepted: False

T3: **NOT MET**. Ratios compare medians of per-query measurements within each actual slice partition. The unsliced metric is the p50 of each sample's build plus solve time. Solve time includes internal replay and any fallback. Missing measurements, an empty partition, or H0 failure prevent adoption.

### T3: conservative cone slicing

- sliced_queries: 32
- unsliced_queries: 19
- dag_reduction: 6.09%
- solve_regression: 7.92%
- unsliced_regression: 0.18%
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
| `api_total_ms` | `wall time from loading the model/query through final witness replay` | fresh-process public API path; excludes interpreter startup, imports, JSON serialization and benchmark diagnostics |
| `pipeline_ms` | `build_ms + solve_ms + (replay_ms or zero), per sample` | includes internal verification and external replay without double-counting; excludes model/query file loading |
| `total_elapsed_ms` | `result.total_elapsed_ms` | production ledger; the solver's own accounting of the whole solve |
| `formula_dag_nodes` | `distinct Z3 AST ids reachable from core.core and objective_formula` | a size measure that does not depend on printing or on the process; what a slice shrinks.  Counted after the peak memory reading |
| `status / property_satisfied / outcome / replay_ok` | `result fields and replay.ok` | the correctness gate compares these between arms and against case.json |
| `peak_child_rss_bytes` | `resource.getrusage(RUSAGE_SELF).ru_maxrss in the child, read right after replay` | the kernel high-water mark of the production path; absent where the resource module is unavailable, never zero |
| `solver_statistics` | `result.solver_statistics immediately after the primary check` | actual Z3 statistics; keys vary by profile/version. rlimit count and num allocs are context-wide, not per-query work and not adoption gates |
| `pyfcstm_file` | `pyfcstm.__file__ in the child` | not published; the parent refuses a sample whose package did not come from the arm's worktree |

Confirm this report is a function of the raw records with:

```bash
python tools/run_bmc_solving_benchmark.py --rebuild 9e68e7458e79
```

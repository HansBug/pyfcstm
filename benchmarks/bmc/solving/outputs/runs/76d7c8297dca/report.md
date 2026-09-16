# BMC solving benchmark

Run `76d7c8297dca`, measured from `HEAD` = `76d7c8297dca` (the working tree also had uncommitted changes; see manifest.json).
Baseline `baseline-0cc43647` = `0cc43647ad85c99347fbdd8eab0259279a5f40d0`; reference arm `default`.

5 measured repetitions per sample after 1 discarded warmups per arm, each sample in its own interpreter running from a detached worktree of its arm's commit.

Arms: `baseline-0cc43647` = `0cc43647ad85`; `default` = `76d7c8297dca`.

## Correctness gate H0

| Case | Query | expected | arm | status | satisfied | outcome | replay | failed samples | H0 |
|---|---|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | 0 | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `conveyor_counters` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `conveyor_counters` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `conveyor_counters` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `heater_logging` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `heater_logging` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `heater_logging` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `heater_logging` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `pump_supervisor_hooks` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |
| `ratio_estimator` | `forbid` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | 0 | pass |
| `ratio_estimator` | `forbid` | `sat` | `default` | `sat` | false | `property_violated` | true | 0 | reference, expected met |
| `ratio_estimator` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `ratio_estimator` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `ratio_estimator` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | pass |
| `ratio_estimator` | `reach` | `unsat` | `default` | `unsat` | n/a | `scenario_infeasible` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | 0 | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | 0 | reference, expected met |
| `telemetry_outputs` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | 0 | pass |
| `telemetry_outputs` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | 0 | reference, expected met |

## Solve time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 8.4 | 8.5 |
| `claude_distributed_elevator_can` | `invariant` | 8.8 | 9.1 |
| `claude_distributed_elevator_can` | `reach` | 13.8 | 13.8 |
| `claude_platooning_join_protocol` | `forbid` | 20.4 | 20.1 |
| `claude_platooning_join_protocol` | `invariant` | 21.4 | 21.7 |
| `claude_platooning_join_protocol` | `reach` | 13.9 | 14.1 |
| `claude_traffic_emergency_priority` | `forbid` | 13.3 | 13.6 |
| `claude_traffic_emergency_priority` | `invariant` | 11.3 | 11.3 |
| `claude_traffic_emergency_priority` | `reach` | 25.9 | 26.3 |
| `claude_vtol_mission_supervision` | `forbid` | 14.7 | 14.3 |
| `claude_vtol_mission_supervision` | `invariant` | 21.6 | 22.2 |
| `claude_vtol_mission_supervision` | `reach` | 16.1 | 16.1 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 5.5 | 5.6 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 6.5 | 6.6 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 7.5 | 7.4 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 11.8 | 11.7 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 12.1 | 11.9 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 7.7 | 7.7 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 6.7 | 7.0 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 6.6 | 6.6 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 27.1 | 26.9 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 16.2 | 16.9 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 17.4 | 17.8 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 9.0 | 9.0 |
| `codex_distributed_elevator_can` | `forbid` | 36.6 | 36.3 |
| `codex_distributed_elevator_can` | `invariant` | 35.5 | 36.0 |
| `codex_distributed_elevator_can` | `reach` | 19.8 | 19.6 |
| `codex_platooning_join_protocol` | `forbid` | 33.0 | 32.8 |
| `codex_platooning_join_protocol` | `invariant` | 28.3 | 28.1 |
| `codex_platooning_join_protocol` | `reach` | 27.9 | 28.3 |
| `codex_traffic_emergency_priority` | `forbid` | 12.2 | 13.4 |
| `codex_traffic_emergency_priority` | `invariant` | 9.6 | 9.6 |
| `codex_traffic_emergency_priority` | `reach` | 19.1 | 18.9 |
| `codex_vtol_mission_supervision` | `forbid` | 62.8 | 63.3 |
| `codex_vtol_mission_supervision` | `invariant` | 39.6 | 39.9 |
| `codex_vtol_mission_supervision` | `reach` | 153.8 | 155.0 |
| `conveyor_counters` | `forbid` | 15.0 | 15.4 |
| `conveyor_counters` | `invariant` | 14.6 | 14.5 |
| `conveyor_counters` | `reach` | 15.3 | 15.5 |
| `heater_logging` | `forbid` | 5.9 | 6.2 |
| `heater_logging` | `invariant` | 6.0 | 6.0 |
| `heater_logging` | `reach` | 5.9 | 5.8 |
| `pump_supervisor_hooks` | `forbid` | 4.3 | 4.2 |
| `pump_supervisor_hooks` | `invariant` | 4.2 | 4.1 |
| `pump_supervisor_hooks` | `reach` | 3.0 | 3.1 |
| `ratio_estimator` | `forbid` | 5.9 | 5.8 |
| `ratio_estimator` | `invariant` | 5.0 | 5.1 |
| `ratio_estimator` | `reach` | 5.5 | 5.6 |
| `telemetry_outputs` | `forbid` | 10.6 | 10.7 |
| `telemetry_outputs` | `invariant` | 10.8 | 11.1 |
| `telemetry_outputs` | `reach` | 10.2 | 10.3 |

## Build time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 399.0 | 399.7 |
| `claude_distributed_elevator_can` | `invariant` | 405.7 | 401.1 |
| `claude_distributed_elevator_can` | `reach` | 403.6 | 397.4 |
| `claude_platooning_join_protocol` | `forbid` | 283.8 | 285.6 |
| `claude_platooning_join_protocol` | `invariant` | 291.8 | 294.4 |
| `claude_platooning_join_protocol` | `reach` | 288.7 | 283.6 |
| `claude_traffic_emergency_priority` | `forbid` | 1048.6 | 1053.7 |
| `claude_traffic_emergency_priority` | `invariant` | 1035.1 | 1035.4 |
| `claude_traffic_emergency_priority` | `reach` | 1041.0 | 1043.8 |
| `claude_vtol_mission_supervision` | `forbid` | 235.3 | 234.9 |
| `claude_vtol_mission_supervision` | `invariant` | 241.4 | 240.7 |
| `claude_vtol_mission_supervision` | `reach` | 241.2 | 238.2 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 125.3 | 124.7 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 129.0 | 129.3 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 125.1 | 123.9 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 143.1 | 144.4 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 146.8 | 145.2 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 142.7 | 143.5 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 479.5 | 482.1 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 487.6 | 478.3 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 479.3 | 478.5 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 282.3 | 285.4 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 286.0 | 290.7 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 276.7 | 279.9 |
| `codex_distributed_elevator_can` | `forbid` | 531.4 | 535.3 |
| `codex_distributed_elevator_can` | `invariant` | 531.4 | 532.9 |
| `codex_distributed_elevator_can` | `reach` | 525.3 | 522.8 |
| `codex_platooning_join_protocol` | `forbid` | 367.2 | 361.9 |
| `codex_platooning_join_protocol` | `invariant` | 367.2 | 368.1 |
| `codex_platooning_join_protocol` | `reach` | 362.0 | 372.2 |
| `codex_traffic_emergency_priority` | `forbid` | 1080.6 | 1077.7 |
| `codex_traffic_emergency_priority` | `invariant` | 1086.4 | 1095.3 |
| `codex_traffic_emergency_priority` | `reach` | 1064.6 | 1074.4 |
| `codex_vtol_mission_supervision` | `forbid` | 25551.0 | 25492.0 |
| `codex_vtol_mission_supervision` | `invariant` | 25589.2 | 25425.0 |
| `codex_vtol_mission_supervision` | `reach` | 25562.5 | 25569.3 |
| `conveyor_counters` | `forbid` | 192.0 | 196.8 |
| `conveyor_counters` | `invariant` | 198.1 | 200.9 |
| `conveyor_counters` | `reach` | 219.5 | 223.4 |
| `heater_logging` | `forbid` | 139.8 | 143.3 |
| `heater_logging` | `invariant` | 139.8 | 141.8 |
| `heater_logging` | `reach` | 138.4 | 138.9 |
| `pump_supervisor_hooks` | `forbid` | 106.1 | 106.3 |
| `pump_supervisor_hooks` | `invariant` | 106.9 | 105.0 |
| `pump_supervisor_hooks` | `reach` | 72.3 | 72.7 |
| `ratio_estimator` | `forbid` | 75.3 | 76.0 |
| `ratio_estimator` | `invariant` | 75.6 | 77.6 |
| `ratio_estimator` | `reach` | 71.7 | 72.9 |
| `telemetry_outputs` | `forbid` | 240.1 | 239.9 |
| `telemetry_outputs` | `invariant` | 237.0 | 242.4 |
| `telemetry_outputs` | `reach` | 236.4 | 236.8 |

## Replay time by arm (p50 ms, sat only)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | n/a | n/a |
| `claude_distributed_elevator_can` | `invariant` | n/a | n/a |
| `claude_distributed_elevator_can` | `reach` | 9.2 | 9.1 |
| `claude_platooning_join_protocol` | `forbid` | n/a | n/a |
| `claude_platooning_join_protocol` | `invariant` | n/a | n/a |
| `claude_platooning_join_protocol` | `reach` | n/a | n/a |
| `claude_traffic_emergency_priority` | `forbid` | n/a | n/a |
| `claude_traffic_emergency_priority` | `invariant` | n/a | n/a |
| `claude_traffic_emergency_priority` | `reach` | 11.8 | 12.4 |
| `claude_vtol_mission_supervision` | `forbid` | n/a | n/a |
| `claude_vtol_mission_supervision` | `invariant` | n/a | n/a |
| `claude_vtol_mission_supervision` | `reach` | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `forbid` | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `invariant` | n/a | n/a |
| `codex_deepseek_distributed_elevator_can` | `reach` | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `forbid` | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `invariant` | n/a | n/a |
| `codex_deepseek_platooning_join_protocol` | `reach` | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | n/a | n/a |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 8.5 | 8.6 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 9.5 | 9.5 |
| `codex_distributed_elevator_can` | `forbid` | n/a | n/a |
| `codex_distributed_elevator_can` | `invariant` | n/a | n/a |
| `codex_distributed_elevator_can` | `reach` | 9.9 | 10.1 |
| `codex_platooning_join_protocol` | `forbid` | n/a | n/a |
| `codex_platooning_join_protocol` | `invariant` | n/a | n/a |
| `codex_platooning_join_protocol` | `reach` | n/a | n/a |
| `codex_traffic_emergency_priority` | `forbid` | n/a | n/a |
| `codex_traffic_emergency_priority` | `invariant` | 13.8 | 13.8 |
| `codex_traffic_emergency_priority` | `reach` | 14.7 | 14.1 |
| `codex_vtol_mission_supervision` | `forbid` | n/a | n/a |
| `codex_vtol_mission_supervision` | `invariant` | 27.7 | 28.0 |
| `codex_vtol_mission_supervision` | `reach` | n/a | n/a |
| `conveyor_counters` | `forbid` | n/a | n/a |
| `conveyor_counters` | `invariant` | n/a | n/a |
| `conveyor_counters` | `reach` | 10.9 | 11.4 |
| `heater_logging` | `forbid` | n/a | n/a |
| `heater_logging` | `invariant` | n/a | n/a |
| `heater_logging` | `reach` | 7.9 | 7.9 |
| `pump_supervisor_hooks` | `forbid` | n/a | n/a |
| `pump_supervisor_hooks` | `invariant` | n/a | n/a |
| `pump_supervisor_hooks` | `reach` | 5.4 | 5.4 |
| `ratio_estimator` | `forbid` | 4.4 | 4.4 |
| `ratio_estimator` | `invariant` | n/a | n/a |
| `ratio_estimator` | `reach` | n/a | n/a |
| `telemetry_outputs` | `forbid` | n/a | n/a |
| `telemetry_outputs` | `invariant` | n/a | n/a |
| `telemetry_outputs` | `reach` | 14.5 | 15.0 |

## Formula size (distinct Z3 AST nodes)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `2036` | `2036` |
| `claude_distributed_elevator_can` | `invariant` | `2048` | `2048` |
| `claude_distributed_elevator_can` | `reach` | `2015` | `2015` |
| `claude_platooning_join_protocol` | `forbid` | `2303` | `2303` |
| `claude_platooning_join_protocol` | `invariant` | `2315` | `2315` |
| `claude_platooning_join_protocol` | `reach` | `2291` | `2291` |
| `claude_traffic_emergency_priority` | `forbid` | `3509` | `3509` |
| `claude_traffic_emergency_priority` | `invariant` | `3521` | `3521` |
| `claude_traffic_emergency_priority` | `reach` | `3486` | `3486` |
| `claude_vtol_mission_supervision` | `forbid` | `2047` | `2047` |
| `claude_vtol_mission_supervision` | `invariant` | `2059` | `2059` |
| `claude_vtol_mission_supervision` | `reach` | `2035` | `2035` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `1010` | `1010` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `1022` | `1022` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `993` | `993` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `1314` | `1314` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `1326` | `1326` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `1302` | `1302` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `2045` | `2045` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `2057` | `2057` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `2023` | `2023` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `2574` | `2574` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `2586` | `2586` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `2562` | `2562` |
| `codex_distributed_elevator_can` | `forbid` | `2126` | `2126` |
| `codex_distributed_elevator_can` | `invariant` | `2138` | `2138` |
| `codex_distributed_elevator_can` | `reach` | `2102` | `2102` |
| `codex_platooning_join_protocol` | `forbid` | `2572` | `2572` |
| `codex_platooning_join_protocol` | `invariant` | `2584` | `2584` |
| `codex_platooning_join_protocol` | `reach` | `2560` | `2560` |
| `codex_traffic_emergency_priority` | `forbid` | `3456` | `3456` |
| `codex_traffic_emergency_priority` | `invariant` | `3468` | `3468` |
| `codex_traffic_emergency_priority` | `reach` | `3429` | `3429` |
| `codex_vtol_mission_supervision` | `forbid` | `13456` | `13456` |
| `codex_vtol_mission_supervision` | `invariant` | `13468` | `13468` |
| `codex_vtol_mission_supervision` | `reach` | `13444` | `13444` |
| `conveyor_counters` | `forbid` | `1789` | `1789` |
| `conveyor_counters` | `invariant` | `1819` | `1819` |
| `conveyor_counters` | `reach` | `2033` | `2033` |
| `heater_logging` | `forbid` | `1231` | `1231` |
| `heater_logging` | `invariant` | `1243` | `1243` |
| `heater_logging` | `reach` | `1216` | `1216` |
| `pump_supervisor_hooks` | `forbid` | `1056` | `1056` |
| `pump_supervisor_hooks` | `invariant` | `1070` | `1070` |
| `pump_supervisor_hooks` | `reach` | `686` | `686` |
| `ratio_estimator` | `forbid` | `717` | `717` |
| `ratio_estimator` | `invariant` | `737` | `737` |
| `ratio_estimator` | `reach` | `716` | `716` |
| `telemetry_outputs` | `forbid` | `2421` | `2421` |
| `telemetry_outputs` | `invariant` | `2442` | `2442` |
| `telemetry_outputs` | `reach` | `2399` | `2399` |

## Peak child RSS (bytes)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `92901376` | `92770304` |
| `claude_distributed_elevator_can` | `invariant` | `92913664` | `92745728` |
| `claude_distributed_elevator_can` | `reach` | `93216768` | `93196288` |
| `claude_platooning_join_protocol` | `forbid` | `92925952` | `93081600` |
| `claude_platooning_join_protocol` | `invariant` | `93188096` | `93466624` |
| `claude_platooning_join_protocol` | `reach` | `93278208` | `93175808` |
| `claude_traffic_emergency_priority` | `forbid` | `95440896` | `95047680` |
| `claude_traffic_emergency_priority` | `invariant` | `95043584` | `95195136` |
| `claude_traffic_emergency_priority` | `reach` | `95375360` | `95215616` |
| `claude_vtol_mission_supervision` | `forbid` | `92667904` | `92598272` |
| `claude_vtol_mission_supervision` | `invariant` | `92688384` | `92745728` |
| `claude_vtol_mission_supervision` | `reach` | `92622848` | `92618752` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `91299840` | `91299840` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `91484160` | `91508736` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `91254784` | `91328512` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `91836416` | `91574272` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `91701248` | `91570176` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `91566080` | `91574272` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `92676096` | `92745728` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `92831744` | `92991488` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `92839936` | `93196288` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `92954624` | `93097984` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `93208576` | `92946432` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `92872704` | `93089792` |
| `codex_distributed_elevator_can` | `forbid` | `93745152` | `93732864` |
| `codex_distributed_elevator_can` | `invariant` | `93868032` | `93937664` |
| `codex_distributed_elevator_can` | `reach` | `93605888` | `93982720` |
| `codex_platooning_join_protocol` | `forbid` | `94089216` | `94253056` |
| `codex_platooning_join_protocol` | `invariant` | `94195712` | `94121984` |
| `codex_platooning_join_protocol` | `reach` | `93958144` | `94060544` |
| `codex_traffic_emergency_priority` | `forbid` | `95571968` | `95576064` |
| `codex_traffic_emergency_priority` | `invariant` | `95793152` | `95965184` |
| `codex_traffic_emergency_priority` | `reach` | `95776768` | `95748096` |
| `codex_vtol_mission_supervision` | `forbid` | `117547008` | `116989952` |
| `codex_vtol_mission_supervision` | `invariant` | `119250944` | `120774656` |
| `codex_vtol_mission_supervision` | `reach` | `117923840` | `117592064` |
| `conveyor_counters` | `forbid` | `92999680` | `92737536` |
| `conveyor_counters` | `invariant` | `93208576` | `92975104` |
| `conveyor_counters` | `reach` | `93659136` | `93478912` |
| `heater_logging` | `forbid` | `90181632` | `90243072` |
| `heater_logging` | `invariant` | `90349568` | `90456064` |
| `heater_logging` | `reach` | `90705920` | `90521600` |
| `pump_supervisor_hooks` | `forbid` | `89804800` | `89804800` |
| `pump_supervisor_hooks` | `invariant` | `89522176` | `89485312` |
| `pump_supervisor_hooks` | `reach` | `89346048` | `89219072` |
| `ratio_estimator` | `forbid` | `90714112` | `90382336` |
| `ratio_estimator` | `invariant` | `90120192` | `90169344` |
| `ratio_estimator` | `reach` | `90066944` | `89985024` |
| `telemetry_outputs` | `forbid` | `92426240` | `92422144` |
| `telemetry_outputs` | `invariant` | `92303360` | `92545024` |
| `telemetry_outputs` | `reach` | `92418048` | `92332032` |

## Failures and instability

Failed samples: none.
Unstable published fields: none.

## Thresholds

H0 (correctness): **pass** for every arm and query.
T1-T3 are not evaluated: no arm sets an option, so this run only establishes the baseline and default distributions.

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
| `pyfcstm_file` | `pyfcstm.__file__ in the child` | not published; the parent refuses a sample whose package did not come from the arm's worktree |

Confirm this report is a function of the raw records with:

```bash
python tools/run_bmc_solving_benchmark.py --rebuild 76d7c8297dca
```

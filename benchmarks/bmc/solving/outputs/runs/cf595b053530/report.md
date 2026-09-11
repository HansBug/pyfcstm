# BMC solving benchmark

Run `cf595b053530`, candidate `cf595b053530`.
Baseline `baseline-0cc43647` = `0cc43647ad85c99347fbdd8eab0259279a5f40d0`; reference arm `default`.

5 measured repetitions per sample after 1 discarded warmups, each sample in its own interpreter.

Arms: `baseline-0cc43647` = revision `0cc43647ad85`; `default` = working tree.

## Correctness gate H0

| Case | Query | expected | arm | status | satisfied | outcome | replay | H0 |
|---|---|---|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `claude_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | pass |
| `claude_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `claude_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | pass |
| `claude_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_deepseek_distributed_elevator_can` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_deepseek_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_distributed_elevator_can` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_distributed_elevator_can` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `codex_distributed_elevator_can` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_platooning_join_protocol` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_platooning_join_protocol` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_platooning_join_protocol` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_traffic_emergency_priority` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | pass |
| `codex_traffic_emergency_priority` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `codex_traffic_emergency_priority` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_vtol_mission_supervision` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | pass |
| `codex_vtol_mission_supervision` | `invariant` | `sat` | `default` | `sat` | false | `property_violated` | true | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | false | `no_witness` | n/a | pass |
| `codex_vtol_mission_supervision` | `reach` | `unsat` | `default` | `unsat` | false | `no_witness` | n/a | pass |
| `conveyor_counters` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `conveyor_counters` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `conveyor_counters` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `conveyor_counters` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `conveyor_counters` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `conveyor_counters` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `heater_logging` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `heater_logging` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `heater_logging` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `heater_logging` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `heater_logging` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `heater_logging` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `pump_supervisor_hooks` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `pump_supervisor_hooks` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `pump_supervisor_hooks` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |
| `ratio_estimator` | `forbid` | `sat` | `baseline-0cc43647` | `sat` | false | `property_violated` | true | pass |
| `ratio_estimator` | `forbid` | `sat` | `default` | `sat` | false | `property_violated` | true | pass |
| `ratio_estimator` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `ratio_estimator` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `ratio_estimator` | `reach` | `unsat` | `baseline-0cc43647` | `unsat` | n/a | `scenario_infeasible` | n/a | pass |
| `ratio_estimator` | `reach` | `unsat` | `default` | `unsat` | n/a | `scenario_infeasible` | n/a | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `telemetry_outputs` | `forbid` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `baseline-0cc43647` | `unsat` | true | `property_satisfied` | n/a | pass |
| `telemetry_outputs` | `invariant` | `unsat` | `default` | `unsat` | true | `property_satisfied` | n/a | pass |
| `telemetry_outputs` | `reach` | `sat` | `baseline-0cc43647` | `sat` | true | `witness_found` | true | pass |
| `telemetry_outputs` | `reach` | `sat` | `default` | `sat` | true | `witness_found` | true | pass |

## Solve time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 9.0 | 8.9 |
| `claude_distributed_elevator_can` | `invariant` | 9.3 | 9.2 |
| `claude_distributed_elevator_can` | `reach` | 12.7 | 12.7 |
| `claude_platooning_join_protocol` | `forbid` | 21.3 | 22.0 |
| `claude_platooning_join_protocol` | `invariant` | 22.6 | 22.2 |
| `claude_platooning_join_protocol` | `reach` | 15.4 | 14.9 |
| `claude_traffic_emergency_priority` | `forbid` | 14.3 | 14.2 |
| `claude_traffic_emergency_priority` | `invariant` | 11.7 | 12.0 |
| `claude_traffic_emergency_priority` | `reach` | 27.4 | 27.5 |
| `claude_vtol_mission_supervision` | `forbid` | 15.0 | 15.2 |
| `claude_vtol_mission_supervision` | `invariant` | 23.3 | 22.6 |
| `claude_vtol_mission_supervision` | `reach` | 17.4 | 17.0 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 5.8 | 5.9 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 6.8 | 6.7 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 7.8 | 7.9 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 13.7 | 12.3 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 12.6 | 12.4 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 8.4 | 8.3 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 7.2 | 7.4 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 7.2 | 7.1 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 28.9 | 29.0 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 16.3 | 16.6 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 17.3 | 17.6 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 9.6 | 9.6 |
| `codex_distributed_elevator_can` | `forbid` | 37.5 | 36.8 |
| `codex_distributed_elevator_can` | `invariant` | 37.2 | 37.6 |
| `codex_distributed_elevator_can` | `reach` | 20.3 | 20.8 |
| `codex_platooning_join_protocol` | `forbid` | 35.7 | 33.9 |
| `codex_platooning_join_protocol` | `invariant` | 29.7 | 29.8 |
| `codex_platooning_join_protocol` | `reach` | 32.5 | 30.6 |
| `codex_traffic_emergency_priority` | `forbid` | 12.7 | 12.8 |
| `codex_traffic_emergency_priority` | `invariant` | 10.1 | 10.5 |
| `codex_traffic_emergency_priority` | `reach` | 19.4 | 19.8 |
| `codex_vtol_mission_supervision` | `forbid` | 85.2 | 94.5 |
| `codex_vtol_mission_supervision` | `invariant` | 44.3 | 44.5 |
| `codex_vtol_mission_supervision` | `reach` | 162.3 | 161.1 |
| `conveyor_counters` | `forbid` | 15.5 | 16.4 |
| `conveyor_counters` | `invariant` | 15.0 | 15.2 |
| `conveyor_counters` | `reach` | 14.6 | 14.2 |
| `heater_logging` | `forbid` | 6.3 | 6.4 |
| `heater_logging` | `invariant` | 6.5 | 6.3 |
| `heater_logging` | `reach` | 6.6 | 6.2 |
| `pump_supervisor_hooks` | `forbid` | 4.7 | 4.3 |
| `pump_supervisor_hooks` | `invariant` | 4.5 | 4.5 |
| `pump_supervisor_hooks` | `reach` | 3.2 | 3.4 |
| `ratio_estimator` | `forbid` | 6.0 | 6.1 |
| `ratio_estimator` | `invariant` | 5.1 | 5.1 |
| `ratio_estimator` | `reach` | 6.5 | 5.9 |
| `telemetry_outputs` | `forbid` | 11.0 | 10.9 |
| `telemetry_outputs` | `invariant` | 11.4 | 11.1 |
| `telemetry_outputs` | `reach` | 10.7 | 10.6 |

## Build time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | 441.0 | 447.9 |
| `claude_distributed_elevator_can` | `invariant` | 435.8 | 448.3 |
| `claude_distributed_elevator_can` | `reach` | 431.8 | 436.2 |
| `claude_platooning_join_protocol` | `forbid` | 309.0 | 312.5 |
| `claude_platooning_join_protocol` | `invariant` | 305.8 | 315.8 |
| `claude_platooning_join_protocol` | `reach` | 310.8 | 307.1 |
| `claude_traffic_emergency_priority` | `forbid` | 1132.5 | 1137.7 |
| `claude_traffic_emergency_priority` | `invariant` | 1148.8 | 1147.2 |
| `claude_traffic_emergency_priority` | `reach` | 1139.7 | 1137.1 |
| `claude_vtol_mission_supervision` | `forbid` | 245.2 | 264.5 |
| `claude_vtol_mission_supervision` | `invariant` | 263.4 | 255.5 |
| `claude_vtol_mission_supervision` | `reach` | 249.1 | 255.7 |
| `codex_deepseek_distributed_elevator_can` | `forbid` | 139.8 | 133.1 |
| `codex_deepseek_distributed_elevator_can` | `invariant` | 138.2 | 144.0 |
| `codex_deepseek_distributed_elevator_can` | `reach` | 129.8 | 130.1 |
| `codex_deepseek_platooning_join_protocol` | `forbid` | 151.7 | 153.3 |
| `codex_deepseek_platooning_join_protocol` | `invariant` | 159.2 | 160.8 |
| `codex_deepseek_platooning_join_protocol` | `reach` | 156.8 | 153.2 |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | 509.1 | 515.3 |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | 528.7 | 516.6 |
| `codex_deepseek_traffic_emergency_priority` | `reach` | 514.2 | 506.5 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | 298.2 | 300.3 |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | 307.2 | 301.6 |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 294.2 | 309.3 |
| `codex_distributed_elevator_can` | `forbid` | 571.2 | 563.7 |
| `codex_distributed_elevator_can` | `invariant` | 569.7 | 565.7 |
| `codex_distributed_elevator_can` | `reach` | 572.5 | 569.1 |
| `codex_platooning_join_protocol` | `forbid` | 390.5 | 391.0 |
| `codex_platooning_join_protocol` | `invariant` | 389.2 | 397.6 |
| `codex_platooning_join_protocol` | `reach` | 394.2 | 393.9 |
| `codex_traffic_emergency_priority` | `forbid` | 1166.5 | 1158.4 |
| `codex_traffic_emergency_priority` | `invariant` | 1144.5 | 1150.1 |
| `codex_traffic_emergency_priority` | `reach` | 1142.6 | 1146.2 |
| `codex_vtol_mission_supervision` | `forbid` | 28408.4 | 34121.3 |
| `codex_vtol_mission_supervision` | `invariant` | 29153.7 | 28329.5 |
| `codex_vtol_mission_supervision` | `reach` | 26827.2 | 26795.1 |
| `conveyor_counters` | `forbid` | 203.6 | 207.3 |
| `conveyor_counters` | `invariant` | 211.6 | 213.7 |
| `conveyor_counters` | `reach` | 230.0 | 228.8 |
| `heater_logging` | `forbid` | 146.0 | 146.7 |
| `heater_logging` | `invariant` | 148.2 | 149.8 |
| `heater_logging` | `reach` | 148.4 | 145.5 |
| `pump_supervisor_hooks` | `forbid` | 117.5 | 111.7 |
| `pump_supervisor_hooks` | `invariant` | 111.5 | 111.3 |
| `pump_supervisor_hooks` | `reach` | 76.1 | 80.2 |
| `ratio_estimator` | `forbid` | 78.5 | 79.8 |
| `ratio_estimator` | `invariant` | 79.7 | 79.4 |
| `ratio_estimator` | `reach` | 77.5 | 77.8 |
| `telemetry_outputs` | `forbid` | 243.9 | 246.6 |
| `telemetry_outputs` | `invariant` | 249.9 | 255.7 |
| `telemetry_outputs` | `reach` | 245.3 | 245.9 |

## Replay time by arm (p50 ms, sat only)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | n/a | n/a |
| `claude_distributed_elevator_can` | `invariant` | n/a | n/a |
| `claude_distributed_elevator_can` | `reach` | 10.1 | 9.8 |
| `claude_platooning_join_protocol` | `forbid` | n/a | n/a |
| `claude_platooning_join_protocol` | `invariant` | n/a | n/a |
| `claude_platooning_join_protocol` | `reach` | n/a | n/a |
| `claude_traffic_emergency_priority` | `forbid` | n/a | n/a |
| `claude_traffic_emergency_priority` | `invariant` | n/a | n/a |
| `claude_traffic_emergency_priority` | `reach` | 12.4 | 12.9 |
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
| `codex_deepseek_traffic_emergency_priority` | `reach` | 8.9 | 9.0 |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | n/a | n/a |
| `codex_deepseek_vtol_mission_supervision` | `reach` | 10.1 | 10.3 |
| `codex_distributed_elevator_can` | `forbid` | n/a | n/a |
| `codex_distributed_elevator_can` | `invariant` | n/a | n/a |
| `codex_distributed_elevator_can` | `reach` | 10.5 | 10.9 |
| `codex_platooning_join_protocol` | `forbid` | n/a | n/a |
| `codex_platooning_join_protocol` | `invariant` | n/a | n/a |
| `codex_platooning_join_protocol` | `reach` | n/a | n/a |
| `codex_traffic_emergency_priority` | `forbid` | n/a | n/a |
| `codex_traffic_emergency_priority` | `invariant` | 14.7 | 15.2 |
| `codex_traffic_emergency_priority` | `reach` | 14.6 | 15.3 |
| `codex_vtol_mission_supervision` | `forbid` | n/a | n/a |
| `codex_vtol_mission_supervision` | `invariant` | 30.5 | 30.5 |
| `codex_vtol_mission_supervision` | `reach` | n/a | n/a |
| `conveyor_counters` | `forbid` | n/a | n/a |
| `conveyor_counters` | `invariant` | n/a | n/a |
| `conveyor_counters` | `reach` | 11.6 | 11.5 |
| `heater_logging` | `forbid` | n/a | n/a |
| `heater_logging` | `invariant` | n/a | n/a |
| `heater_logging` | `reach` | 8.3 | 8.5 |
| `pump_supervisor_hooks` | `forbid` | n/a | n/a |
| `pump_supervisor_hooks` | `invariant` | n/a | n/a |
| `pump_supervisor_hooks` | `reach` | 5.5 | 5.9 |
| `ratio_estimator` | `forbid` | 4.6 | 4.5 |
| `ratio_estimator` | `invariant` | n/a | n/a |
| `ratio_estimator` | `reach` | n/a | n/a |
| `telemetry_outputs` | `forbid` | n/a | n/a |
| `telemetry_outputs` | `invariant` | n/a | n/a |
| `telemetry_outputs` | `reach` | 15.3 | 15.7 |

## Formula size and solver effort

| Case | Query | `baseline-0cc43647` nodes / rlimit | `default` nodes / rlimit |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `2036` / `336378` | `2036` / `336378` |
| `claude_distributed_elevator_can` | `invariant` | `2048` / `347144` | `2048` / `347144` |
| `claude_distributed_elevator_can` | `reach` | `2015` / `395657` | `2015` / `395657` |
| `claude_platooning_join_protocol` | `forbid` | `2303` / `296069` | `2303` / `296069` |
| `claude_platooning_join_protocol` | `invariant` | `2315` / `304814` | `2315` / `304814` |
| `claude_platooning_join_protocol` | `reach` | `2291` / `274434` | `2291` / `274434` |
| `claude_traffic_emergency_priority` | `forbid` | `3509` / `436171` | `3509` / `436171` |
| `claude_traffic_emergency_priority` | `invariant` | `3521` / `423872` | `3521` / `423872` |
| `claude_traffic_emergency_priority` | `reach` | `3486` / `606285` | `3486` / `606285` |
| `claude_vtol_mission_supervision` | `forbid` | `2047` / `242968` | `2047` / `242968` |
| `claude_vtol_mission_supervision` | `invariant` | `2059` / `269332` | `2059` / `269332` |
| `claude_vtol_mission_supervision` | `reach` | `2035` / `251632` | `2035` / `251632` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `1010` / `111636` | `1010` / `111636` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `1022` / `121364` | `1022` / `121364` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `993` / `142095` | `993` / `142095` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `1314` / `155559` | `1314` / `155559` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `1326` / `156587` | `1326` / `156587` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `1302` / `145745` | `1302` / `145745` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `2045` / `239090` | `2045` / `239090` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `2057` / `272785` | `2057` / `272785` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `2023` / `433233` | `2023` / `433233` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `2574` / `319379` | `2574` / `319379` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `2586` / `349634` | `2586` / `349634` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `2562` / `274332` | `2562` / `274332` |
| `codex_distributed_elevator_can` | `forbid` | `2126` / `4871008` | `2126` / `4871008` |
| `codex_distributed_elevator_can` | `invariant` | `2138` / `5050549` | `2138` / `5050549` |
| `codex_distributed_elevator_can` | `reach` | `2102` / `5217206` | `2102` / `5217206` |
| `codex_platooning_join_protocol` | `forbid` | `2572` / `447242` | `2572` / `447242` |
| `codex_platooning_join_protocol` | `invariant` | `2584` / `412829` | `2584` / `412829` |
| `codex_platooning_join_protocol` | `reach` | `2560` / `415062` | `2560` / `415062` |
| `codex_traffic_emergency_priority` | `forbid` | `3456` / `447278` | `3456` / `447278` |
| `codex_traffic_emergency_priority` | `invariant` | `3468` / `462831` | `3468` / `462831` |
| `codex_traffic_emergency_priority` | `reach` | `3429` / `565725` | `3429` / `565725` |
| `codex_vtol_mission_supervision` | `forbid` | `13456` / `3848533` | `13456` / `3848533` |
| `codex_vtol_mission_supervision` | `invariant` | `13468` / `3956894` | `13468` / `3956894` |
| `codex_vtol_mission_supervision` | `reach` | `13444` / `4100921` | `13444` / `4100921` |
| `conveyor_counters` | `forbid` | `1789` / `148056` | `1789` / `148056` |
| `conveyor_counters` | `invariant` | `1819` / `146106` | `1819` / `146106` |
| `conveyor_counters` | `reach` | `2033` / `173588` | `2033` / `173588` |
| `heater_logging` | `forbid` | `1231` / `93122` | `1231` / `93122` |
| `heater_logging` | `invariant` | `1243` / `93115` | `1243` / `93115` |
| `heater_logging` | `reach` | `1216` / `93223` | `1216` / `93223` |
| `pump_supervisor_hooks` | `forbid` | `1056` / `69666` | `1056` / `69666` |
| `pump_supervisor_hooks` | `invariant` | `1070` / `71569` | `1070` / `71569` |
| `pump_supervisor_hooks` | `reach` | `686` / `38299` | `686` / `38299` |
| `ratio_estimator` | `forbid` | `717` / `49036` | `717` / `49036` |
| `ratio_estimator` | `invariant` | `737` / `46365` | `737` / `46365` |
| `ratio_estimator` | `reach` | `716` / `23735` | `716` / `23735` |
| `telemetry_outputs` | `forbid` | `2421` / `226615` | `2421` / `226615` |
| `telemetry_outputs` | `invariant` | `2442` / `235176` | `2442` / `235176` |
| `telemetry_outputs` | `reach` | `2399` / `226962` | `2399` / `226962` |

## Peak child RSS (bytes)

| Case | Query | `baseline-0cc43647` | `default` |
|---|---|---|---|
| `claude_distributed_elevator_can` | `forbid` | `92983296` | `92983296` |
| `claude_distributed_elevator_can` | `invariant` | `93134848` | `93085696` |
| `claude_distributed_elevator_can` | `reach` | `94502912` | `94593024` |
| `claude_platooning_join_protocol` | `forbid` | `95039488` | `94863360` |
| `claude_platooning_join_protocol` | `invariant` | `95129600` | `95043584` |
| `claude_platooning_join_protocol` | `reach` | `94846976` | `94900224` |
| `claude_traffic_emergency_priority` | `forbid` | `95260672` | `95244288` |
| `claude_traffic_emergency_priority` | `invariant` | `95404032` | `95285248` |
| `claude_traffic_emergency_priority` | `reach` | `97116160` | `97140736` |
| `claude_vtol_mission_supervision` | `forbid` | `94195712` | `94195712` |
| `claude_vtol_mission_supervision` | `invariant` | `94388224` | `94523392` |
| `claude_vtol_mission_supervision` | `reach` | `94179328` | `94355456` |
| `codex_deepseek_distributed_elevator_can` | `forbid` | `93011968` | `93011968` |
| `codex_deepseek_distributed_elevator_can` | `invariant` | `93229056` | `93216768` |
| `codex_deepseek_distributed_elevator_can` | `reach` | `93298688` | `93229056` |
| `codex_deepseek_platooning_join_protocol` | `forbid` | `93413376` | `93437952` |
| `codex_deepseek_platooning_join_protocol` | `invariant` | `93478912` | `93536256` |
| `codex_deepseek_platooning_join_protocol` | `reach` | `93396992` | `93356032` |
| `codex_deepseek_traffic_emergency_priority` | `forbid` | `92839936` | `92819456` |
| `codex_deepseek_traffic_emergency_priority` | `invariant` | `94404608` | `94502912` |
| `codex_deepseek_traffic_emergency_priority` | `reach` | `94826496` | `94711808` |
| `codex_deepseek_vtol_mission_supervision` | `forbid` | `94797824` | `94638080` |
| `codex_deepseek_vtol_mission_supervision` | `invariant` | `94863360` | `94806016` |
| `codex_deepseek_vtol_mission_supervision` | `reach` | `94814208` | `94765056` |
| `codex_distributed_elevator_can` | `forbid` | `95080448` | `95068160` |
| `codex_distributed_elevator_can` | `invariant` | `95232000` | `95227904` |
| `codex_distributed_elevator_can` | `reach` | `95502336` | `95539200` |
| `codex_platooning_join_protocol` | `forbid` | `95686656` | `95617024` |
| `codex_platooning_join_protocol` | `invariant` | `95760384` | `95723520` |
| `codex_platooning_join_protocol` | `reach` | `95645696` | `95719424` |
| `codex_traffic_emergency_priority` | `forbid` | `95707136` | `95686656` |
| `codex_traffic_emergency_priority` | `invariant` | `95870976` | `95916032` |
| `codex_traffic_emergency_priority` | `reach` | `96735232` | `96710656` |
| `codex_vtol_mission_supervision` | `forbid` | `118632448` | `118587392` |
| `codex_vtol_mission_supervision` | `invariant` | `122130432` | `122175488` |
| `codex_vtol_mission_supervision` | `reach` | `121733120` | `121634816` |
| `conveyor_counters` | `forbid` | `94162944` | `94126080` |
| `conveyor_counters` | `invariant` | `94203904` | `94085120` |
| `conveyor_counters` | `reach` | `94433280` | `94412800` |
| `heater_logging` | `forbid` | `92102656` | `92098560` |
| `heater_logging` | `invariant` | `92250112` | `92164096` |
| `heater_logging` | `reach` | `92192768` | `92241920` |
| `pump_supervisor_hooks` | `forbid` | `91742208` | `91680768` |
| `pump_supervisor_hooks` | `invariant` | `91664384` | `91824128` |
| `pump_supervisor_hooks` | `reach` | `91537408` | `91488256` |
| `ratio_estimator` | `forbid` | `93528064` | `93487104` |
| `ratio_estimator` | `invariant` | `93208576` | `93138944` |
| `ratio_estimator` | `reach` | `92020736` | `92065792` |
| `telemetry_outputs` | `forbid` | `94064640` | `94072832` |
| `telemetry_outputs` | `invariant` | `94191616` | `94076928` |
| `telemetry_outputs` | `reach` | `94150656` | `94113792` |

## Failures and instability

Failed samples: none.
Unstable published fields: none.

## Thresholds

H0 (correctness): **pass** for every arm and query.
T1-T3 are not evaluated: no arm sets an option, so this run only establishes the baseline and default distributions.

## Measurement map

| Metric | Source | Note |
|---|---|---|
| `build_ms` | `compile_bmc_query wall time in the child` | prepare, core relation, and property compilation; the region an encoding knob changes |
| `solve_ms` | `solve_bmc_property wall time in the child` | the staged primary solve including its verdict; the region a solver knob changes |
| `replay_ms` | `decode_bmc_result_trace + replay_bmc_witness wall time in the child` | only when the primary status is sat; absent otherwise |
| `total_elapsed_ms` | `result.total_elapsed_ms` | production ledger; the solver's own accounting of the whole solve |
| `formula_dag_nodes` | `distinct Z3 AST ids reachable from core.core and objective_formula` | a size measure that does not depend on printing; what a slice shrinks |
| `rlimit_count` | `z3 statistics 'rlimit count' of one plain side check of the same conjunction, outside the timed region` | Z3's own effort counter, steadier than wall time but not identical across processes: two arms running identical code differed by about one percent on one sat query |
| `status / property_satisfied / outcome / replay_ok` | `result fields and replay.ok` | the correctness gate compares these between arms and against case.json |
| `peak_child_rss_bytes` | `maximum of sampled psutil RSS readings of the child process` | a sampled maximum, not a kernel high-water mark: a spike shorter than the 0.002 s interval can be missed.  Absent rather than zero when psutil is unavailable |

Reconstruct this report from the raw records with:

```bash
python tools/run_bmc_solving_benchmark.py --rebuild cf595b053530
```

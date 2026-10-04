# Accepted-condition resolution benchmark

Baseline: `df5416b18b00497dd2fe5820b092d814dba4343c`; candidate: `235d29cf8a832848135a58a69e45949321c6f847`.

API timing includes loading, compilation, solving and ordinary replay; imports and report serialization are excluded. Partition-local caches are released normally during compilation. RSS is the independent process high-water mark before diagnostic size traversal.

Measured samples: 510; SAT replays: 130.

| Query | API baseline ms | API candidate ms | API change | RSS change |
|---|---:|---:|---:|---:|
| claude_distributed_elevator_can/forbid | 489.902 | 475.908 | -2.86% | +0.20% |
| claude_distributed_elevator_can/invariant | 469.875 | 473.492 | +0.77% | +0.04% |
| claude_distributed_elevator_can/reach | 511.725 | 500.920 | -2.11% | +0.03% |
| claude_platooning_join_protocol/forbid | 357.192 | 357.307 | +0.03% | +0.12% |
| claude_platooning_join_protocol/invariant | 357.101 | 358.353 | +0.35% | +0.16% |
| claude_platooning_join_protocol/reach | 350.706 | 348.459 | -0.64% | -0.16% |
| claude_traffic_emergency_priority/forbid | 1156.903 | 1162.745 | +0.51% | -0.03% |
| claude_traffic_emergency_priority/invariant | 1164.180 | 1163.759 | -0.04% | +0.33% |
| claude_traffic_emergency_priority/reach | 1191.221 | 1182.097 | -0.77% | +0.20% |
| claude_vtol_mission_supervision/forbid | 303.469 | 304.858 | +0.46% | +0.16% |
| claude_vtol_mission_supervision/invariant | 306.863 | 307.734 | +0.28% | +0.79% |
| claude_vtol_mission_supervision/reach | 304.120 | 304.332 | +0.07% | +0.25% |
| codex_deepseek_distributed_elevator_can/forbid | 192.617 | 191.154 | -0.76% | +0.13% |
| codex_deepseek_distributed_elevator_can/invariant | 195.718 | 195.765 | +0.02% | -0.21% |
| codex_deepseek_distributed_elevator_can/reach | 193.897 | 192.205 | -0.87% | -0.09% |
| codex_deepseek_platooning_join_protocol/forbid | 193.083 | 193.110 | +0.01% | +0.11% |
| codex_deepseek_platooning_join_protocol/invariant | 199.317 | 198.352 | -0.48% | +0.05% |
| codex_deepseek_platooning_join_protocol/reach | 187.653 | 189.505 | +0.99% | -0.22% |
| codex_deepseek_traffic_emergency_priority/forbid | 548.065 | 559.124 | +2.02% | -0.32% |
| codex_deepseek_traffic_emergency_priority/invariant | 563.850 | 554.374 | -1.68% | -0.18% |
| codex_deepseek_traffic_emergency_priority/reach | 576.983 | 562.693 | -2.48% | -0.62% |
| codex_deepseek_vtol_mission_supervision/forbid | 434.995 | 439.614 | +1.06% | +0.62% |
| codex_deepseek_vtol_mission_supervision/invariant | 465.936 | 433.302 | -7.00% | +0.36% |
| codex_deepseek_vtol_mission_supervision/reach | 356.723 | 355.358 | -0.38% | +0.24% |
| codex_distributed_elevator_can/forbid | 686.475 | 614.535 | -10.48% | -0.18% |
| codex_distributed_elevator_can/invariant | 778.632 | 798.080 | +2.50% | -0.31% |
| codex_distributed_elevator_can/reach | 688.043 | 683.273 | -0.69% | +0.33% |
| codex_platooning_join_protocol/forbid | 504.018 | 531.789 | +5.51% | -0.15% |
| codex_platooning_join_protocol/invariant | 565.467 | 537.026 | -5.03% | -0.28% |
| codex_platooning_join_protocol/reach | 491.908 | 505.345 | +2.73% | +0.19% |
| codex_traffic_emergency_priority/forbid | 1295.356 | 1231.280 | -4.95% | +0.06% |
| codex_traffic_emergency_priority/invariant | 1301.845 | 1268.588 | -2.55% | +0.19% |
| codex_traffic_emergency_priority/reach | 1471.395 | 1387.846 | -5.68% | +0.41% |
| codex_vtol_mission_supervision/forbid | 27609.673 | 7322.465 | -73.48% | -7.87% |
| codex_vtol_mission_supervision/invariant | 27332.479 | 7309.284 | -73.26% | -5.87% |
| codex_vtol_mission_supervision/reach | 28799.374 | 7644.301 | -73.46% | -7.69% |
| conveyor_counters/forbid | 267.221 | 267.563 | +0.13% | -0.01% |
| conveyor_counters/invariant | 267.167 | 270.711 | +1.33% | +0.12% |
| conveyor_counters/reach | 308.913 | 310.855 | +0.63% | -0.10% |
| heater_logging/forbid | 195.951 | 196.371 | +0.21% | +0.21% |
| heater_logging/invariant | 196.316 | 192.557 | -1.91% | +0.13% |
| heater_logging/reach | 200.597 | 205.255 | +2.32% | -0.28% |
| pump_supervisor_hooks/forbid | 155.678 | 154.820 | -0.55% | +0.07% |
| pump_supervisor_hooks/invariant | 154.897 | 154.419 | -0.31% | +0.13% |
| pump_supervisor_hooks/reach | 124.888 | 124.069 | -0.66% | +0.18% |
| ratio_estimator/forbid | 127.329 | 127.378 | +0.04% | -0.10% |
| ratio_estimator/invariant | 123.368 | 123.049 | -0.26% | -0.16% |
| ratio_estimator/reach | 118.514 | 117.661 | -0.72% | -0.16% |
| telemetry_outputs/forbid | 309.096 | 308.016 | -0.35% | -0.02% |
| telemetry_outputs/invariant | 305.148 | 307.898 | +0.90% | -0.16% |
| telemetry_outputs/reach | 323.400 | 326.036 | +0.82% | -0.32% |

VTOL reach target: True. Other-query API failures: 1. RSS failures: 0. Borderline queries requiring the registered follow-up: 1.

The first-round judgment remains authoritative; follow-up measurements do not replace it.


See [analysis identifier correction](analysis-note.md) for the preserved initial analysis and unchanged sampling record.

# Accepted-condition resolution benchmark

Baseline: `df5416b18b00497dd2fe5820b092d814dba4343c`; candidate: `235d29cf8a832848135a58a69e45949321c6f847`.

API timing includes loading, compilation, solving and ordinary replay; imports and report serialization are excluded. Partition-local caches are released normally during compilation. RSS is the independent process high-water mark before diagnostic size traversal.

Measured samples: 20; SAT replays: 0.

| Query | API baseline ms | API candidate ms | API change | RSS change |
|---|---:|---:|---:|---:|
| codex_platooning_join_protocol/forbid | 462.193 | 463.058 | +0.19% | +0.14% |

VTOL reach target: None. Other-query API failures: 0. RSS failures: 0. Borderline queries requiring the registered follow-up: 0.

The first-round judgment remains authoritative; follow-up measurements do not replace it.

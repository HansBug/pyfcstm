# Production condition-resolution reuse: assessment

The diagnosed hotspot improves by about 73% in normal production calls, without experimental caches or retained diagnostic formulas. The first-round performance acceptance is **not fully green**: one of the other 48 queries exceeds its 5% API regression limit. The registered follow-up does not reproduce that magnitude, but does not replace the first-round verdict.

## Hotspot and public CLI

Baseline: `df5416b18b00497dd2fe5820b092d814dba4343c`; production candidate: `235d29cf8a832848135a58a69e45949321c6f847`. Both ran from clean detached worktrees. The production change only reuses completed condition resolution within one source partition. Normal cache release is included.

| Codex VTOL query | API baseline ms | API candidate ms | Change |
|---|---:|---:|---:|
| forbid | 27609.673 | 7322.465 | -73.48% |
| invariant | 27332.479 | 7309.284 | -73.26% |
| reach | 28799.374 | 7644.301 | -73.46% |

The API pipeline includes model loading, compilation, solving and ordinary replay; it excludes imports and report serialization. Each query/arm has one warmup and five measured samples, with alternating arm order.

| CLI query | Baseline ms | Candidate ms | Change |
|---|---:|---:|---:|
| codex_traffic_emergency_priority/invariant | 1338.043 | 1303.833 | -2.56% |
| codex_traffic_emergency_priority/reach | 1359.517 | 1298.551 | -4.48% |
| codex_vtol_mission_supervision/invariant | 27960.983 | 7565.323 | -72.94% |
| codex_vtol_mission_supervision/reach | 28260.564 | 7708.546 | -72.72% |
| heater_logging/invariant | 266.524 | 265.588 | -0.35% |
| heater_logging/reach | 276.008 | 277.624 | +0.59% |

CLI call timing includes Click dispatch and JSON report serialization, with ordinary production cleanup. Startup/imports and measurement transport are excluded from `call_ms` and recorded separately as `process_ms`. These are invocations of the documented Click command, not timings of a packaged standalone executable. All six CLI groups have five measured samples per revision and one warmup.

## The remaining first-round guard failure

| Round: codex_platooning_join_protocol/forbid | Samples per arm | API baseline ms | API candidate ms | Change |
|---|---:|---:|---:|---:|
| Primary | 5 | 504.018 | 531.789 | +5.51% |
| Registered follow-up | 10 | 462.193 | 463.058 | +0.19% |

The primary candidate samples range from 472.040 to 649.624 ms; the baseline ranges from 492.584 to 566.331 ms. The follow-up ranges are 446.042–480.149 ms and 455.150–476.736 ms respectively. The unchanged baseline itself shifts between rounds, including model-loading time before the optimized code runs. This is evidence of timing variability, not proof of a specific operating-system, frequency or scheduling cause. There is no stable 5.51% regression in these two rounds.

No production change was made to obtain the follow-up. The primary 5.51% failure remains recorded; the second round is 0.19% and is not used to turn the original failure into a pass. Further cache layers are not justified by this single unstable measurement. Maintainer review must explicitly address the first-round guard failure under the registered stopping rule.

## Memory and correctness

All 51 primary query groups satisfy the 10% peak-RSS median growth limit. Individual process high-water marks remain in raw records; they were read before the diagnostic formula-size traversal.
Codex VTOL reach peak-RSS medians are 111.57 → 102.99 MiB. This is a measured result for this workload, not a general memory-saving guarantee.

- Primary API: 510 measured records plus 102 warmups; 130 measured SAT replays pass; corpus expectations and formula DAG sizes match.
- Follow-up API: 20 measured records plus two warmups for the single registered borderline query.
- CLI: 60 measured records plus 12 warmups; statuses/outcomes match the API and every command returns the expected report.
- Independent semantic observations: 51 queries × two revisions. Core formula, objective, macro-contract and partition-check fingerprints match in every pair; all 26 SAT replays pass. All paired witness fingerprints also match in this run after excluding the documented solver timing fields. Multiple-solution queries still have the existing contract permitting different legal witnesses.
- Source-partition validation and assignment enumeration are retained. The semantic observer retains formulas to hash them, so its timings are diagnostic only and are not used for performance acceptance.
- Local production validation: `SKIP_SLOW_TESTS=1 make unittest WORKERS=4` reports 49,171 passed and 936 skipped; `make doctest` reports 1,113 passed. Macro-contract tests report 38 passed. RST generation, Ruff, test boundaries, resource ownership and benchmark self-checks pass. Existing skips and assertions were not weakened.

The cache is local to one `verify_source_partition` call and stores completed results only. Input trees remain owned by cases/registry, so identity keys cannot be reused within the call. Cycle/missing-reference rejection, canonical results, variable sets, assignment budgets and structural fallback remain intact. Repeated and concurrent public partition calls are covered. No public option, JSON field, solver profile default or slicing default changes. Historical T1–T3 judgments remain unchanged.

## Evidence and reproduction

- [Primary report](report.md), [manifest](manifest.json), [raw records](raw.jsonl).
- [Registered follow-up](../235d29cf-followup/report.md).
- [CLI records](cli/raw.jsonl) and [CLI medians](cli/summary.json).
- [Independent baseline semantics](semantics-baseline/raw.jsonl), [candidate semantics](semantics-candidate/raw.jsonl), and [verified assessment](assessment.json).
- [Analysis identifier correction](analysis-note.md): the original analyzer selected the Claude VTOL model by mistake; the original diagnostic target is the Codex VTOL model. All 51 queries and every sample were retained, numerical thresholds stayed fixed, and the initial derived analysis is preserved separately.

```bash
python tools/run_bmc_resolution_benchmark.py --check
python tools/run_bmc_resolution_benchmark.py --rebuild --output benchmarks/bmc/solving/outputs/resolution_runs/235d29cf
python tools/run_bmc_resolution_benchmark.py --rebuild --output benchmarks/bmc/solving/outputs/resolution_runs/235d29cf-followup
python benchmarks/bmc/solving/outputs/resolution_runs/235d29cf/analyze.py
```

To remeasure, recreate clean baseline/candidate worktrees and use new output directories. The benchmark README gives the primary/follow-up commands. `cli_compare.py` records the six CLI groups; `tools/profile_bmc_construction.py --checkout <tree> --specs benchmarks/bmc/solving/outputs/resolution_runs/235d29cf/semantics-specs.json --output <new-directory>` reproduces the semantic observations. The `baseline` experimental arm in those semantic specs means no experimental cache is installed; the candidate production cache remains active.

This report describes the recorded Linux/Python/Z3 environment and corpus. Supported-version/platform CI and the PR workflow state are tracked in [PR #485](https://github.com/HansBug/pyfcstm/pull/485).

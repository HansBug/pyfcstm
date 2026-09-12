# BMC solving benchmark

Run `9e68e7458e79-unsliced-control`, measured from `HEAD` = `9e68e7458e79` (the working tree also had uncommitted changes; see manifest.json).
Baseline `baseline-0cc43647` = `0cc43647ad85c99347fbdd8eab0259279a5f40d0`; reference arm `default`.

5 measured repetitions per sample after 1 discarded warmups per arm, each sample in its own interpreter running from a detached worktree of its arm's commit.

**Partial run**: only the cases `claude_vtol_mission_supervision` were measured.

Arms: `baseline-0cc43647` = `0cc43647ad85`; `default` = `9e68e7458e79`; `logic` = `9e68e7458e79` with options `{"compile": {}, "solve": {"solver_profile": "logic"}}`; `tactic` = `9e68e7458e79` with options `{"compile": {}, "solve": {"solver_profile": "tactic"}}`; `cone_slicing` = `9e68e7458e79` with options `{"compile": {"cone_slicing": true}, "solve": {}}`; `slicing-2db08911` = `2db089114bb5` with options `{"compile": {"cone_slicing": true}, "solve": {}}`.

## Correctness gate H0

| Case | Query | expected | arm | status | satisfied | outcome | replay | failed samples | H0 |
|---|---|---|---|---|---|---|---|---|---|
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

## Solve time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_vtol_mission_supervision` | `forbid` | 17.7 | 17.9 | 12.3 | 14.5 | 17.7 | 17.9 |
| `claude_vtol_mission_supervision` | `invariant` | 19.4 | 18.9 | 11.8 | 14.4 | 19.7 | 18.8 |
| `claude_vtol_mission_supervision` | `reach` | 17.7 | 18.4 | 12.8 | 14.1 | 17.8 | 18.3 |

## Build time by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_vtol_mission_supervision` | `forbid` | 252.8 | 253.4 | 259.0 | 263.8 | 258.0 | 260.0 |
| `claude_vtol_mission_supervision` | `invariant` | 261.3 | 257.8 | 260.9 | 256.5 | 259.4 | 258.1 |
| `claude_vtol_mission_supervision` | `reach` | 253.8 | 255.6 | 255.4 | 257.8 | 257.8 | 253.6 |

## Replay time by arm (p50 ms, sat only)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_vtol_mission_supervision` | `forbid` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `invariant` | n/a | n/a | n/a | n/a | n/a | n/a |
| `claude_vtol_mission_supervision` | `reach` | n/a | n/a | n/a | n/a | n/a | n/a |

## Complete API path by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_vtol_mission_supervision` | `forbid` | 312.3 | 313.6 | 312.3 | 319.4 | 319.2 | 320.0 |
| `claude_vtol_mission_supervision` | `invariant` | 322.8 | 318.2 | 314.8 | 311.7 | 320.2 | 319.1 |
| `claude_vtol_mission_supervision` | `reach` | 314.4 | 315.1 | 308.7 | 313.2 | 318.0 | 314.2 |

## Build, solve and replay by arm (p50 ms)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_vtol_mission_supervision` | `forbid` | 270.8 | 271.8 | 271.3 | 278.0 | 276.0 | 277.9 |
| `claude_vtol_mission_supervision` | `invariant` | 281.1 | 276.9 | 272.4 | 271.0 | 278.8 | 277.2 |
| `claude_vtol_mission_supervision` | `reach` | 271.0 | 274.1 | 267.9 | 271.9 | 275.2 | 271.7 |

## Complete paths by reference SAT/UNSAT status

| Reference status | Metric | Arm | Queries | Default p50 ms | Arm p50 ms | Change | Worst change | Worst query |
|---|---|---|---|---|---|---|---|---|
| unsat | api_total_ms | baseline-0cc43647 | 3 | 315.1 | 314.4 | -0.23% | 1.46% | claude_vtol_mission_supervision/invariant |
| unsat | api_total_ms | default | 3 | 315.1 | 315.1 | 0.00% | 0.00% | claude_vtol_mission_supervision/forbid |
| unsat | api_total_ms | logic | 3 | 315.1 | 312.3 | -0.91% | -0.41% | claude_vtol_mission_supervision/forbid |
| unsat | api_total_ms | tactic | 3 | 315.1 | 313.2 | -0.62% | 1.85% | claude_vtol_mission_supervision/forbid |
| unsat | api_total_ms | cone_slicing | 3 | 315.1 | 319.2 | 1.28% | 1.79% | claude_vtol_mission_supervision/forbid |
| unsat | api_total_ms | slicing-2db08911 | 3 | 315.1 | 319.1 | 1.24% | 2.03% | claude_vtol_mission_supervision/forbid |
| unsat | pipeline_ms | baseline-0cc43647 | 3 | 274.1 | 271.0 | -1.11% | 1.54% | claude_vtol_mission_supervision/invariant |
| unsat | pipeline_ms | default | 3 | 274.1 | 274.1 | 0.00% | 0.00% | claude_vtol_mission_supervision/forbid |
| unsat | pipeline_ms | logic | 3 | 274.1 | 271.3 | -1.03% | -0.22% | claude_vtol_mission_supervision/forbid |
| unsat | pipeline_ms | tactic | 3 | 274.1 | 271.9 | -0.80% | 2.26% | claude_vtol_mission_supervision/forbid |
| unsat | pipeline_ms | cone_slicing | 3 | 274.1 | 276.0 | 0.71% | 1.54% | claude_vtol_mission_supervision/forbid |
| unsat | pipeline_ms | slicing-2db08911 | 3 | 274.1 | 277.2 | 1.14% | 2.23% | claude_vtol_mission_supervision/forbid |

Groups use the default arm's status. Medians aggregate per-query p50s; worst change compares each query with its own default. Positive change means slower. These diagnostic groups do not alter H0 or T3.

## Formula size (distinct Z3 AST nodes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_vtol_mission_supervision` | `forbid` | `2047` | `2047` | `2047` | `2047` | `2047` | `2047` |
| `claude_vtol_mission_supervision` | `invariant` | `2059` | `2059` | `2059` | `2059` | `2059` | `2059` |
| `claude_vtol_mission_supervision` | `reach` | `2035` | `2035` | `2035` | `2035` | `2035` | `2035` |

## Peak child RSS (bytes)

| Case | Query | `baseline-0cc43647` | `default` | `logic` | `tactic` | `cone_slicing` | `slicing-2db08911` |
|---|---|---|---|---|---|---|---|
| `claude_vtol_mission_supervision` | `forbid` | `92401664` | `92585984` | `92475392` | `90877952` | `92839936` | `92487680` |
| `claude_vtol_mission_supervision` | `invariant` | `92835840` | `92651520` | `93237248` | `90742784` | `92999680` | `92913664` |
| `claude_vtol_mission_supervision` | `reach` | `92319744` | `92700672` | `92905472` | `91144192` | `92585984` | `92708864` |

## Failures and instability

Failed samples: none.
Unstable published fields: none.

## Thresholds

H0 (correctness): **pass** for every arm and query.

| Gate | Arm | Median p50 improvement | Worst query regression | H0 | Adopt |
|---|---|---|---|---|---|
| T1 | `logic` | 33.15% | -30.33% | pass | pass |
| T2 | `tactic` | 21.33% | -18.91% | pass | pass |

Median improvement compares medians of per-query solve p50; worst regression compares each query with its own default p50. Missing measurements or H0 failures prevent adoption.

### T3: conservative cone slicing

- sliced_queries: 0
- unsliced_queries: 3
- dag_reduction: None
- solve_regression: None
- unsliced_regression: 0.71%
- fallback_samples: 0
- complete: True
- accepted: False

T3: **NOT MET**. Ratios compare medians of per-query measurements within each actual slice partition. The unsliced metric is the p50 of each sample's build plus solve time. Solve time includes internal replay and any fallback. Missing measurements, an empty partition, or H0 failure prevent adoption.

### T3: conservative cone slicing

- sliced_queries: 0
- unsliced_queries: 3
- dag_reduction: None
- solve_regression: None
- unsliced_regression: 1.14%
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
python tools/run_bmc_solving_benchmark.py --rebuild 9e68e7458e79-unsliced-control
```

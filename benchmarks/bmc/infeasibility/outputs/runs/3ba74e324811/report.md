# BMC infeasibility explanation benchmark

Run `3ba74e324811`, candidate `3ba74e324811`.
Baseline `baseline-901f30e9` = `901f30e981c29eb8e304b33d61985652d2e85b2e`.

5 measured repetitions per sample after 1 discarded warmups, each sample in its own interpreter.

## Wall time by arm (p50 ms)

| Case | expected | baseline-901f30e9 | none | formal | proof |
|---|---|---|---|---|---|
| `cross_step` | `formal` | 1.8 | 1.8 | 23.8 | 30.1 |
| `empty_interval` | `proof` | 1.8 | 1.9 | 16.7 | 22.5 |
| `event_conflict` | `formal` | 1.7 | 1.8 | 13.1 | 13.1 |
| `feasible` | `none` | 1.8 | 1.8 | 1.8 | 1.8 |
| `two_states` | `proof` | 1.8 | 1.8 | 16.7 | 20.9 |
| `two_values` | `proof` | 1.7 | 1.7 | 16.0 | 21.1 |

## What each arm achieved

| Case | arm | achieved | status | core | proof nodes |
|---|---|---|---|---|---|
| `cross_step` | `baseline-901f30e9` | `-` | `-` | - | - |
| `cross_step` | `none` | `-` | `-` | - | - |
| `cross_step` | `formal` | `formal` | `complete` | 4 | - |
| `cross_step` | `proof` | `formal` | `partial` | 4 | - |
| `empty_interval` | `baseline-901f30e9` | `-` | `-` | - | - |
| `empty_interval` | `none` | `-` | `-` | - | - |
| `empty_interval` | `formal` | `formal` | `complete` | 2 | - |
| `empty_interval` | `proof` | `proof` | `complete` | 2 | 3 |
| `event_conflict` | `baseline-901f30e9` | `-` | `-` | - | - |
| `event_conflict` | `none` | `-` | `-` | - | - |
| `event_conflict` | `formal` | `formal` | `partial` | 2 | - |
| `event_conflict` | `proof` | `formal` | `partial` | 2 | - |
| `feasible` | `baseline-901f30e9` | `-` | `-` | - | - |
| `feasible` | `none` | `-` | `-` | - | - |
| `feasible` | `formal` | `-` | `-` | - | - |
| `feasible` | `proof` | `-` | `-` | - | - |
| `two_states` | `baseline-901f30e9` | `-` | `-` | - | - |
| `two_states` | `none` | `-` | `-` | - | - |
| `two_states` | `formal` | `formal` | `complete` | 2 | - |
| `two_states` | `proof` | `proof` | `complete` | 2 | 3 |
| `two_values` | `baseline-901f30e9` | `-` | `-` | - | - |
| `two_values` | `none` | `-` | `-` | - | - |
| `two_values` | `formal` | `formal` | `complete` | 2 | - |
| `two_values` | `proof` | `proof` | `complete` | 2 | 3 |

## Failures, degradation, and instability

Failed samples: none.
Unstable published fields: none.
Degraded at `proof` depth: `cross_step`, `event_conflict`.

## Measurement map

| Metric | Source | Note |
|---|---|---|
| `classification` | `refinement_checks[component_*].elapsed_ms` | production ledger; the staged feasibility probe that fixes the family |
| `core_extraction` | `refinement_checks[unsat_core].elapsed_ms` | production ledger |
| `core_minimization` | `refinement_checks[unsat_core_minimization].elapsed_ms` | production ledger |
| `proof_input_verification` | `refinement_checks[core_binding].elapsed_ms` | production ledger; the two-directional check of every input node |
| `proof_construction` | `refinement_checks[proof_construction].elapsed_ms` | production ledger; covers closure construction AND derived-side rule_checker verification, which are not separable here |
| `proof_linearization` | `benchmark-only: direct timing of pyfcstm.bmc.proof_text.linearize_proof` | not in the production ledger; timed in the child process around a documented module function, and reported as instrumentation |
| `total_elapsed_ms` | `result.total_elapsed_ms` | production ledger; whole solve including the mandatory verdict |
| `peak_child_rss_bytes` | `psutil high-water mark of the child process` | absent rather than zero when psutil is unavailable |
| `solver_checks` | `len(result.feasibility.refinement_checks)` | production ledger; how many extra checks the depth cost |

Reconstruct this report from the raw records with:

```bash
python tools/run_bmc_infeasibility_benchmark.py --rebuild 3ba74e324811
```

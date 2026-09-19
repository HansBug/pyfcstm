# Shared UNSAT kernel and symbol identities: expanded workload survey

This report supplements the [original measurement](../readable_formulas/report.md).
Its transition/default result remains **FAIL** against the original numeric gate;
the maintainer accepted that particular small increase on 2026-09-20. That
acceptance does not automatically apply to other failures in this survey.

## Scope and frozen protocol

The baseline is `92a85f1ec4e0db20e05e341e088931a49c91ced5`; the candidate runtime
is `94989748b5708ec6fea6db3f8ffca42e6d158414`. Both run from `git archive` package
snapshots, not worktrees. The follow-up changes only a module docstring and
benchmark artifacts; it does not change executable production code.

[workloads.json](workloads.json) stores the exact model/query strings and their
origins. It contains **29 queries / 47 case-mode combinations**:

- Counter bounds 8, 32 and 128; 16, 64 and 128 long-named variables; 64 variables
  at bound 32; a 64-variable short-name control. Every generated variable is
  updated on each transition, rather than merely declared and ignored.
- Sixteen ordered guards; per-step input and shared parameter roles; existing
  elevator, VTOL, pump lifecycle-hook and ratio-estimator models.
- Initialization/transition, event, state, interval and division-definedness
  conflicts, each in `none`, `formal` and `proof` modes.
- The complete resource-pool and dose-editor models from design revision 29,
  with the recorded Intake and cold queries respectively, in all three modes.
  This measures those two queries, not the all-initial-state proof matrix.
- Seven property kinds across the matrix, including two response bounds and
  SAT witnesses with mandatory public replay.
- Two exact original measurement queries, including the accepted default
  transition conflict, in all three modes.

Nine process pairs alternate baseline/candidate launch order. Each pair uses
the same shuffled combination order (seeds 19200 through 19208). Every process
first warms all combinations once and then measures each once. No measured
samples are removed. GC stays enabled, is included in elapsed times and is
recorded rather than subtracted. Lightweight solver-call/GC instrumentation is
identical on both sides. `PYTHONHASHSEED=0` is fixed.

API timing includes model parsing, formula construction, solving, explanation
construction when requested, and mandatory SAT replay. It excludes interpreter
startup/imports. Public human-text rendering is timed separately after solving;
its size is recorded because native formulas contain more information than the
old text. Peak RSS includes the entire worker process and is not a per-query
memory estimate. Phase medians are separate distributions and need not sum to
the total median. Process CPU time and host load are also retained.

The existing thresholds remain unchanged:

| Gate | Threshold |
|---|---|
| Default API | `median <= max(baseline * 1.05, baseline + 2ms)` |
| Enabled explanation API | `median <= max(baseline * 1.15, baseline + 5ms)` |
| Worker peak RSS | `median <= max(baseline * 1.10, baseline + 8192KiB)` |
| Observed behavior | status, property truth, response incomplete status, infeasible stage and achieved explanation status/mode |
| Diagnostic comparison | solver-check counts and selected core IDs, recorded separately from property truth |

Every solve has a 30,000ms solver budget. This does not bound parsing,
compilation or text rendering. A worker has a 1,200s outer timeout; a terminated
worker is an error, not a sample silently omitted from the results.

## Pilot changes and environmental limits

Pilots overlapped local validation and are not used as performance evidence.
An initial pilot without streamed progress was interrupted before completing a
sample. A later 16-way modulo-guard pilot was interrupted in baseline formula
construction, specifically guarded definedness construction. The repeated
scaling case was changed to sixteen equality guards. The original VTOL bound
10 was reduced to 4 after a baseline pilot took about 38.8 seconds under
concurrent validation. These scope changes happened before measured pairs;
they are not dropped measured outliers. The excluded modulo case remains an
unmeasured limitation, not evidence of a regression caused by the candidate.

The matrix was also expanded during piloting to all property kinds, a
short-name control and two original queries. Frozen sources and protocol are
in [manifest.json](manifest.json); the raw sample header includes runner,
worker, workload and package-source hashes. Pilot logs are retained with the
task evidence. All agent-owned tests/builds finish before the measured run.
Other workloads on this shared Linux host are not controlled. Consequently,
wall-time differences near a gate require caution; this is a broader local
compatibility survey, not isolated hardware or a cross-platform benchmark.

## Measured results

All values below are API wall-clock milliseconds. Each side has 9 retained samples per combination; 846 measured calls in total, plus warmup. Parentheses show candidate change from baseline median.

| Query | Mode | Baseline median [min, max] | Candidate median [min, max] | Change | Gate |
|---|---|---:|---:|---:|---|
| `codex_deepseek_distributed_elevator_can_reach` | none | 126.365 [124.032, 149.659] | 131.682 [126.128, 137.222] | +4.21% | **PASS** |
| `codex_vtol_mission_supervision_invariant` | none | 5363.776 [5283.747, 5416.023] | 5357.858 [5289.884, 5400.624] | -0.11% | **PASS** |
| `counter_bound_128` | none | 456.826 [451.414, 488.659] | 492.427 [463.634, 506.695] | +7.79% | **FAIL** |
| `counter_bound_32` | none | 114.752 [112.613, 131.446] | 119.168 [117.910, 137.398] | +3.85% | **PASS** |
| `counter_bound_8` | none | 31.669 [31.178, 54.104] | 32.883 [32.298, 37.205] | +3.83% | **PASS** |
| `cross_step` | formal | 40.713 [40.092, 41.571] | 45.167 [44.036, 46.037] | +10.94% | **PASS** |
| `cross_step` | none | 14.841 [14.386, 15.011] | 15.176 [14.597, 16.411] | +2.26% | **PASS** |
| `cross_step` | proof | 87.190 [85.354, 104.412] | 64.475 [62.817, 67.760] | -26.05% | **PASS** |
| `definedness` | formal | 20.624 [20.205, 21.622] | 21.563 [21.053, 23.488] | +4.55% | **PASS** |
| `definedness` | none | 10.167 [9.624, 11.258] | 10.112 [9.713, 12.614] | -0.54% | **PASS** |
| `definedness` | proof | 25.136 [24.825, 26.382] | 26.357 [25.918, 29.184] | +4.86% | **PASS** |
| `dose_editor` | formal | 772.147 [760.682, 784.779] | 900.150 [879.993, 916.875] | +16.58% | **FAIL** |
| `dose_editor` | none | 169.363 [160.890, 181.878] | 167.360 [163.927, 176.527] | -1.18% | **PASS** |
| `dose_editor` | proof | 783.041 [767.050, 809.151] | 902.579 [887.092, 921.218] | +15.27% | **FAIL** |
| `empty_interval` | formal | 30.381 [29.880, 34.234] | 32.247 [30.821, 35.122] | +6.14% | **PASS** |
| `empty_interval` | none | 15.842 [15.563, 17.298] | 16.161 [15.928, 17.672] | +2.02% | **PASS** |
| `empty_interval` | proof | 36.397 [35.213, 40.260] | 38.635 [37.457, 64.063] | +6.15% | **PASS** |
| `event_conflict` | formal | 26.527 [25.473, 49.880] | 26.811 [26.215, 27.904] | +1.07% | **PASS** |
| `event_conflict` | none | 15.845 [15.258, 17.741] | 15.998 [15.681, 36.836] | +0.97% | **PASS** |
| `event_conflict` | proof | 28.447 [28.063, 33.052] | 28.938 [28.393, 30.937] | +1.72% | **PASS** |
| `inputs_parameters` | none | 77.329 [76.321, 85.487] | 80.215 [78.310, 89.499] | +3.73% | **PASS** |
| `long_variables_128_bound_8` | none | 717.449 [706.533, 746.439] | 745.746 [726.144, 762.980] | +3.94% | **PASS** |
| `long_variables_16_bound_8` | none | 92.477 [91.093, 95.779] | 97.173 [95.367, 101.487] | +5.08% | **FAIL** |
| `long_variables_64_bound_32` | none | 1210.879 [1188.003, 1265.627] | 1242.138 [1229.681, 1249.410] | +2.58% | **PASS** |
| `long_variables_64_bound_8` | none | 325.199 [318.697, 346.507] | 330.257 [323.910, 337.628] | +1.56% | **PASS** |
| `original_sat_reach` | formal | 41.949 [40.708, 73.353] | 43.247 [41.860, 58.235] | +3.09% | **PASS** |
| `original_sat_reach` | none | 41.818 [40.843, 48.167] | 42.937 [41.310, 67.082] | +2.68% | **PASS** |
| `original_sat_reach` | proof | 41.356 [40.228, 42.334] | 43.241 [42.079, 46.392] | +4.56% | **PASS** |
| `original_transition_conflict` | formal | 99.656 [97.652, 108.704] | 112.261 [111.013, 113.574] | +12.65% | **PASS** |
| `original_transition_conflict` | none | 43.133 [41.391, 45.586] | 43.990 [43.003, 44.789] | +1.99% | **PASS** |
| `original_transition_conflict` | proof | 530.002 [526.535, 542.818] | 201.111 [195.641, 214.903] | -62.05% | **PASS** |
| `pool` | formal | 348.504 [325.541, 351.378] | 405.951 [390.879, 422.494] | +16.48% | **FAIL** |
| `pool` | none | 85.339 [84.284, 88.893] | 86.975 [84.554, 92.688] | +1.92% | **PASS** |
| `pool` | proof | 357.117 [339.646, 373.764] | 415.283 [391.213, 440.513] | +16.29% | **FAIL** |
| `property_cover` | none | 31.999 [31.009, 35.465] | 34.053 [33.064, 35.231] | +6.42% | **FAIL** |
| `property_exists_always` | none | 32.573 [32.054, 56.950] | 33.774 [33.219, 35.894] | +3.69% | **PASS** |
| `property_forbid` | none | 33.028 [31.936, 35.555] | 33.973 [32.961, 35.909] | +2.86% | **PASS** |
| `property_must_reach` | none | 33.296 [32.150, 55.837] | 33.833 [33.311, 37.361] | +1.61% | **PASS** |
| `pump_supervisor_hooks_reach` | none | 68.292 [66.013, 95.208] | 69.466 [68.272, 92.954] | +1.72% | **PASS** |
| `ratio_estimator_invariant` | none | 69.688 [67.943, 78.100] | 73.320 [69.268, 80.294] | +5.21% | **FAIL** |
| `response_bound_1` | none | 7.509 [6.970, 26.436] | 7.597 [7.232, 9.222] | +1.17% | **PASS** |
| `response_bound_16` | none | 65.713 [64.848, 66.967] | 69.819 [65.502, 71.772] | +6.25% | **FAIL** |
| `short_variables_64_bound_8` | none | 311.747 [304.730, 328.183] | 322.707 [314.070, 335.122] | +3.52% | **PASS** |
| `sixteen_guards` | none | 2100.586 [2088.628, 2154.480] | 2119.236 [2102.951, 2134.962] | +0.89% | **PASS** |
| `two_states` | formal | 29.341 [29.030, 30.468] | 30.757 [29.824, 31.750] | +4.83% | **PASS** |
| `two_states` | none | 15.413 [15.142, 16.341] | 15.994 [15.706, 17.550] | +3.77% | **PASS** |
| `two_states` | proof | 34.852 [34.355, 54.372] | 35.288 [34.240, 51.115] | +1.25% | **PASS** |

**38/47 timing gates passed; 9 failed.** Default paths span -1.18% to +7.79%. The 29 default cases have 5 failed gates; 4 enabled-explanation combinations fail the 15%/+5ms gate. No gate was relaxed.

All 47 combinations have identical status, property truth, response incomplete status, infeasible stage, achieved mode and explanation completion status in every pair. There are no UNKNOWN or timeout samples. Where a core is published, its identifiers agree in every pair. Core equality here compares selected source-group IDs, not a proof of general equivalence.

Solver-check counts differ in some pairs for the two complex models in formal/proof modes. The baseline itself varies between repetitions. Thus the original small-matrix claim of identical call counts does not generalize; this survey records agreement of semantic observations separately.

| Complex query | Mode | Baseline calls across repetitions | Candidate calls across repetitions | Achieved |
|---|---|---|---|---|
| dose_editor | formal | [132, 133, 134] | [132, 133, 134] | partial formal |
| dose_editor | proof | [134, 135, 136, 137] | [134, 135, 136] | partial formal |
| pool | formal | [98, 99, 100] | [98, 99, 100] | partial formal |
| pool | proof | [100, 101, 102, 103] | [100, 101, 102, 103] | partial formal |

Both complex models requested in proof mode still achieve **partial formal**, consistently with the baseline. This is not a newly completed readable proof.

Worker peak RSS median is **147,180 -> 147,588 KiB (+408 KiB)**, passing the frozen gate. These are maximum-over-entire-matrix process values; they do not establish per-query allocation overhead.

Compared with the previous experiment, the original transition/default query now measures a +1.99% median change and passes. The old +5.19% result remains in its report; this run does not retroactively change it. The original transition/proof improvement is reproduced at -62.05%, and cross-step/proof improves by -26.05%. Neither result is a general BMC speedup.

### Failures and phase evidence

| Query/mode | API delta | Excess over gate | Compile median: baseline -> candidate | Solve/replay/explanation median: baseline -> candidate | Slower pairs |
|---|---:|---:|---:|---:|---:|
| counter_bound_128/none | +35.601 | +12.760 | 427.109 -> 462.191 | 28.354 -> 28.760 | 9/9 |
| dose_editor/formal | +128.003 | +12.181 | 133.333 -> 136.435 | 615.571 -> 747.253 | 9/9 |
| dose_editor/proof | +119.538 | +2.082 | 133.766 -> 137.534 | 630.262 -> 748.859 | 9/9 |
| long_variables_16_bound_8/none | +4.696 | +0.072 | 75.295 -> 79.773 | 5.009 -> 5.139 | 9/9 |
| pool/formal | +57.447 | +5.172 | 65.651 -> 69.062 | 265.855 -> 318.765 | 9/9 |
| pool/proof | +58.166 | +4.599 | 66.962 -> 69.582 | 278.374 -> 333.084 | 9/9 |
| property_cover/none | +2.054 | +0.054 | 28.589 -> 30.548 | 1.925 -> 2.075 | 8/9 |
| ratio_estimator_invariant/none | +3.632 | +0.147 | 57.933 -> 59.792 | 6.267 -> 7.216 | 6/9 |
| response_bound_16/none | +4.106 | +0.821 | 61.387 -> 65.047 | 2.895 -> 3.036 | 8/9 |

Large-bound counter overhead is concentrated in compilation; the complex-model extra time is concentrated inside solve/explanation construction. The public final text-assembly pass is below a millisecond in these cases, but that does **not** imply formula rendering is free: core item strings are built earlier inside the solve/explanation phase. Profile evidence below separates those responsibilities.

Three default failures are very close to their numeric gates: 16 long variables (+0.072ms beyond gate), cover (+0.054ms), ratio estimator (+0.147ms). The bound-128 case adds about 35.6ms and is slower in all nine pairs; it cannot be summarized as merely the previously accepted 0.091ms gate miss. Response bound 16 adds about 4.1ms. The four complex explanation paths add approximately 57–128ms and are slower in all nine pairs.


### Targeted profile diagnosis

After the measured pairs, separate `cProfile` runs exercised public
`compile_bmc_query`/`solve_bmc_property` for three cases, with one warmup and
three profiled repetitions per version. [profile_queries.py](profile_queries.py)
and [profile_summary.json](profile_summary.json) retain the procedure and
selected function records. These runs change execution cost through profiling;
the numbers below locate work and must not replace uninstrumented timings.
Nested cumulative times must not be added together.

- **Default bound 128:** the candidate registers 1,151 symbolic identities.
  `SymbolNames.register` has a profiled cumulative median of 38.153ms; BMC trace
  symbol construction's `__post_init__` takes 40.547ms. This is consistent with
  the measured compile-phase increase (427.109 -> 462.191ms). No explanation is
  requested. The default cost is identity construction, not extra core solving.
- **Pool/formal:** 8 core items are built/rendered. Profiled
  `normalized_fact_for` improves from 239.805 to 126.677ms, while native
  `SymbolNames.render` adds 236.461ms. Total `build_core_item` grows from
  243.448 to 368.419ms. The new cost is full formula reading during explanation
  construction, partly offset by faster identity-based fact recognition.
- **Dose editor/formal:** 9 core items are built/rendered. Profiled fact
  recognition improves from 652.789 to 350.764ms; native formula rendering costs
  592.843ms. Total core-item construction grows from 656.880 to 949.781ms.
  Final report-line joining remains cheap because those formula strings are
  already built before that phase.

Call counts for the two complex explanations differ by a few checks across
seeds on both versions, while final source-group cores and semantic outcomes
remain identical in this experiment. This supports variability in the
extraction/minimization work, not a change in the user-facing property result;
it is not an exact attribution of every extra check.

The evidence suggests two distinct future optimization targets: reduce repeated
Z3 introspection during construction-time registration without weakening public
input validation, and reduce traversal/formatting work for complete core
formulas without dropping operators, source identity or expression content.
Neither target was implemented in this documentation/measurement follow-up.

The expanded conclusion is narrower and better supported than a universal
"about 5%" statement: measured default overhead reaches 7.79% on the simple
large-bound case; complex enabled explanations reach roughly 15–17%; some
existing proof paths improve substantially. Correctness observations agree for
all tested combinations, but this does not establish a universal performance
bound or automatically approve these additional numeric failures. The old
accepted exception and the new failures remain separately visible.

## Reproduction

Use the repository's Python environment, including its Z3 and replay
dependencies, on Linux. From the repository root:

```bash
benchmark_sources=$(mktemp -d /tmp/bmc-core-sources.XXXXXX)
mkdir "$benchmark_sources/baseline" "$benchmark_sources/candidate"
git archive 92a85f1ec4e0db20e05e341e088931a49c91ced5 pyfcstm | tar -x -C "$benchmark_sources/baseline"
git archive 94989748b5708ec6fea6db3f8ffca42e6d158414 pyfcstm | tar -x -C "$benchmark_sources/candidate"
python benchmarks/bmc/infeasibility/outputs/expanded_workloads/run.py \
  "$benchmark_sources/baseline" "$benchmark_sources/candidate" \
  "$benchmark_sources/samples.jsonl" --pairs 9
python benchmarks/bmc/infeasibility/outputs/expanded_workloads/summarize.py \
  "$benchmark_sources/samples.jsonl" "$benchmark_sources/summary.json"
```

`run.py` refuses to overwrite its raw output. Optional repeated `--case NAME`
arguments restrict exploratory or diagnostic runs; they must not be used to
claim a complete matrix. These scripts are benchmark tools, not product APIs
or unit-test dependencies.

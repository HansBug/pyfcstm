# BMC construction diagnosis

After [PR #483](https://github.com/HansBug/pyfcstm/pull/483) merged into
[umbrella #478](https://github.com/HansBug/pyfcstm/pull/478), the measured
implementation is `1aa4315a105eba0c4ae9e7998b9b2517b7ef65e4`. This diagnosis
changes repository-local experiment tooling and evidence only. No experimental
cache is installed in the package, and no default option changes.

The largest confirmed bottleneck is repeated expansion of shared accepted-case
conditions during macro partition validation. A second, distinct bottleneck is
relation lowering, including repeated small SAT feasibility checks. Final
property solving and witness output are not the dominant costs in the measured
construction-heavy examples. These are workload-specific findings, not a claim
that Z3 solving can never dominate another model or a larger bound.

## What the earlier optimization achieved

The [formal six-arm run](../../runs/9e68e7458e79/report.md) remains the acceptance
record: 1,530 records, 390 successful SAT replays, H0 passed, no slicing fallback.
T1/T2 remain unmet: logic improves the aggregate solve p50 by 2.05% but its
worst query regresses 45.30%; tactic improves the aggregate by 21.61% but its
worst query regresses 422.66%. Tactic clears the 15% aggregate target but fails
the 10% per-query regression ceiling. T3 still misses both the 20% DAG reduction
goal (6.09% achieved) and the 5% unsliced build + solve ceiling (6.87% observed regression); sliced
solve regression of 4.47% is within its 5% ceiling. The narrow unsliced control
rerun did not reproduce that regression's magnitude, but does not supersede the
formal failed gate.

Witness reuse eliminated genuine duplicate work. Against the same-round initial
slicing implementation, actual sliced SAT API p50 improved 3.78%; the all-query
p50 improved only 0.64%. Removing a small phase cannot deliver a large whole-call
improvement when construction dominates. Conservative slicing removes assignment
work but retains control guards, priorities and necessary definedness checks.
Solver profiles affect final property checks; they do not change macro validation
or the domain/operation helpers' construction-time solvers. Construction dominance
explains the limited whole-call upside, not the failure of T1/T2 themselves: those
are solver-only gates, and the measured profiles failed their required median
improvement and/or worst-query regression limits. This diagnosis does not isolate
the internal Z3 reasons for those worst-query regressions.

The numeric thresholds are reasonable adoption criteria, but were not established
as achievable predictions from a prior cost decomposition. Treating them as an
expected end-to-end gain was insufficiently supported. The implementation met
much of its correctness and opt-in delivery scope; the larger performance
expectation was not met. The missing engineering step was measuring which work
could actually be removed before choosing the optimization and its forecast.
Neither lowering the gates nor broadening unsafe slicing fixes that problem.

The hotspot modules `bmc/macro.py`, `bmc/expand.py`, and
`solver/{logical,domain,operation}.py` are unchanged between the before-series
baseline `0cc43647ad85c99347fbdd8eab0259279a5f40d0` and the merge commit. The
recurrence-formal sharing also predates this series. These are existing
optimization opportunities, not evidence that this series introduced the
large construction bottleneck.

## Measurement contract

All measurements use a detached, clean checkout of the merge commit and fresh,
sequential child processes. The public `build_bmc_output(..., json_output=True)`
call includes file loading, construction, property solving, ordinary witness
replay and report serialization. Imports, interpreter startup, modified-bound
input preparation and post-call fingerprints are outside the timer. Thus these
numbers are not cold CLI startup latency, and differ slightly from the formal
runner's timer, which excludes serialization. Observers retain the compiled
formula and partition summaries for post-call checks in every arm, changing their
normal release time. Installing patches and releasing experimental cache
containers are outside the timer as well. A production end-to-end gate must
include normal cache/formula cleanup; these are observed API microexperiments,
not untouched CLI latency measurements.

Low-frequency wrappers record disjoint phases by subtracting nested observed
calls. The phase table uses the sample whose whole-call time is the median;
separate medians of each phase need not sum to a real call. cProfile runs are
separate samples used for attribution and call counts only: inclusive function
times overlap and must not be summed or used as ordinary speedup measurements.

Caches are monkeypatches scoped to one public call in an isolated interpreter.
They retain object references to prevent identity reuse, and are explicitly
experimental. The accepted-condition cache is scoped by the fixed source
registry and only stores completed resolutions. Missing-reference and cycle
rejection still run. Canonical-key caching applies only to frozen `BoolTemplate`
objects. No validation is disabled.

The SAT probe experiment records all domain/operation requests in both arms. Its
cache reuses only definite `sat`/`unsat` results for exactly the same ordered Z3
ASTs in the same context, without a timeout or requested model. Budgeted,
model-producing and indeterminate requests bypass caching. Request observers add
some overhead and retain expressions in both arms, so compare within that
campaign, not against the older macro-only baseline.

Peak RSS is the process high-water mark measured immediately after the public
call, before fingerprinting, while caches are retained. RSS includes imports and
native allocations and is not an incremental heap allocation count. Samples run
on one Linux x86_64 host; exact Python/Z3 versions and host metadata are in raw
records and manifests. Host load and CPU scheduling were not isolated or measured.
Three ordinary repetitions and rotated order provide microexperiment evidence,
not confidence intervals or a cross-platform performance guarantee.

## Confirmed macro bottleneck

[The macro resolver](https://github.com/HansBug/pyfcstm/blob/1aa4315a105eba0c4ae9e7998b9b2517b7ef65e4/pyfcstm/bmc/macro.py#L1921)
recursively resolves `accepted:` references with no reuse of completed results.
Shared conditions are repeatedly expanded and reconstructed as trees. Boolean
constructors sort and deduplicate using
[canonical JSON keys](https://github.com/HansBug/pyfcstm/blob/1aa4315a105eba0c4ae9e7998b9b2517b7ef65e4/pyfcstm/bmc/macro.py#L135),
which recursively serialize those trees again.

[Source partition validation](https://github.com/HansBug/pyfcstm/blob/1aa4315a105eba0c4ae9e7998b9b2517b7ef65e4/pyfcstm/bmc/macro.py#L2177)
resolves the buckets and traverses their variables before deciding whether the
structural fallback applies. Its cost is not measured by the final Z3 DAG node
count: Z3 sharing happens after this Python work.

VTOL reach, three ordinary repetitions per arm. Times are ms, p50 (min–max).

| Arm | Call time | Reduction vs baseline | Peak RSS p50, MiB |
|---|---|---|---|
| baseline | 36243.96 (27682.19–36629.61) | 0.00% | 137.6 |
| canonical_cache | 22149.39 (22141.27–24438.37) | 38.89% | 679.3 |
| accepted_cache | 10225.86 (9755.77–10293.40) | 71.79% | 131.7 |
| combined_cache | 7987.31 (7832.97–8045.14) | 77.96% | 170.2 |

Other reach inputs in the same factorial, n=3 per cell, call p50 in ms:

| Case | Baseline | Accepted reuse | Combined reuse |
|---|---|---|---|
| `claude_traffic_emergency_priority` | 1681.92 | 1698.25 | 1709.90 |
| `codex_traffic_emergency_priority` | 1691.79 | 1644.37 | 1633.00 |
| `conveyor_counters` | 413.63 | 402.47 | 401.90 |
| `ratio_estimator` | 162.68 | 165.25 | 162.72 |

For VTOL reach, the median baseline call spends 32,245 ms of 36,244 ms (89.0%) in
partition validation, 3,050 ms in relation steps, and 155 ms in final solving
including verification. Even eliminating that final solving phase entirely would
save only about 0.43% on this sample. The combined cache sample spends 3,680 ms
in partition validation and 3,314 ms in relation steps: after the first bottleneck
shrinks, another becomes material.

Separate VTOL cProfile runs reduce original resolver invocations from 804,189 to
992 and canonical-key invocations from 959,720 to 1,539. Formula, macro and
partition fingerprints are exactly unchanged. This is direct causal evidence of
redundant work, beyond a wall-time correlation. Remaining `variables` traversals
(1,784,323 calls) and `evaluate` traversals (2,384,327 calls) remain unchanged in
that profile; reuse there is a plausible next hypothesis, not a tested benefit.

Canonical caching alone retains many temporary trees: its RSS cost rules it out
as the first production approach. Accepted-result reuse is the smaller, higher
priority intervention. Its slightly lower measured RSS does not establish a
memory-saving guarantee. Combined caching offers additional speed at a memory
cost and needs separate justification.

## Corpus phase survey and bound controls

In the baseline survey, relation steps are the largest disjoint phase on 48 of
51 queries; partition validation is largest on all three VTOL queries. The table
shows each model’s reach query, one observation each, in ms. Other construction
bookkeeping and output phases are omitted from this table but retained in raw data.

| Case | Call | Partition | Relation steps | Final solve/verification | Load |
|---|---|---|---|---|---|
| `claude_distributed_elevator_can` | 511.6 | 8.0 | 324.0 | 33.7 | 32.5 |
| `claude_platooning_join_protocol` | 373.2 | 0.6 | 181.9 | 35.2 | 29.9 |
| `claude_traffic_emergency_priority` | 1285.2 | 4.0 | 929.8 | 49.8 | 59.8 |
| `claude_vtol_mission_supervision` | 314.6 | 0.9 | 140.9 | 35.1 | 27.8 |
| `codex_deepseek_distributed_elevator_can` | 211.8 | 0.2 | 80.7 | 26.8 | 46.7 |
| `codex_deepseek_platooning_join_protocol` | 200.6 | 0.2 | 84.0 | 25.2 | 22.7 |
| `codex_deepseek_traffic_emergency_priority` | 628.5 | 3.3 | 425.6 | 65.6 | 32.7 |
| `codex_deepseek_vtol_mission_supervision` | 375.1 | 3.6 | 171.3 | 26.8 | 28.2 |
| `codex_distributed_elevator_can` | 677.3 | 111.0 | 356.6 | 57.3 | 39.7 |
| `codex_platooning_join_protocol` | 489.4 | 0.5 | 268.1 | 48.3 | 39.8 |
| `codex_traffic_emergency_priority` | 1290.4 | 103.6 | 891.2 | 47.7 | 59.3 |
| `codex_vtol_mission_supervision` | 27602.6 | 24468.8 | 2353.7 | 123.1 | 37.3 |
| `conveyor_counters` | 314.7 | 0.5 | 150.5 | 33.2 | 27.9 |
| `heater_logging` | 199.0 | 0.1 | 86.6 | 22.6 | 22.7 |
| `pump_supervisor_hooks` | 129.1 | 0.2 | 37.0 | 20.9 | 23.3 |
| `ratio_estimator` | 124.0 | 0.3 | 35.4 | 24.4 | 21.2 |
| `telemetry_outputs` | 315.9 | 0.3 | 147.3 | 29.8 | 24.4 |

A single baseline sweep totals 104.47 seconds of observed calls. The three VTOL
queries account for 78.85% of that sum; partition validation accounts for 70.69%,
relation steps 19.10%, and final solve/verification 1.86%. This describes a sweep
with one of each query, not typical user latency or a statistically estimated
aggregate speedup. Optimizing VTOL chiefly improves this outlier and sweep cost;
relation work matters to the many other models.

The corpus campaign is one observation per query/arm and primarily checks
semantic equivalence and broadens phase coverage. It is not a distribution of
per-query latency estimates and must not be presented as a new formal benchmark.

Three repetitions per arm/input, p50 (min–max), ms:

| Bound | Arm | Call | Partition | Relation steps | Partition checks | Enumerated assignments |
|---|---|---|---|---|---|---|
| 1 | baseline | 80.07 (79.52–83.64) | 0.04 | 2.57 | 1 | 1 |
| 1 | combined_cache | 80.90 (78.89–82.90) | 0.04 | 2.59 | 1 | 1 |
| 2 | baseline | 24274.76 (24228.43–24457.51) | 23845.70 | 252.05 | 13 | 1330 |
| 2 | combined_cache | 3088.25 (3077.19–3163.39) | 2664.75 | 253.08 | 13 | 1330 |
| 5 | baseline | 25833.36 (25310.31–25954.24) | 24413.38 | 1054.18 | 13 | 1330 |
| 5 | combined_cache | 4122.93 (4037.56–4144.15) | 2727.11 | 1039.05 | 13 | 1330 |

[The existing relation builder](https://github.com/HansBug/pyfcstm/blob/1aa4315a105eba0c4ae9e7998b9b2517b7ef65e4/pyfcstm/bmc/relation.py#L2612)
already shares immutable recurrence formals across time steps. Bound 1 needs only
the initial source; bounds of at least 2 expand the recurrence sources once.
The large macro setup is therefore not repeated independently at every frame.
Increasing the bound adds relation lowering and solver work. Do not attribute the
current bottleneck to a missing across-frame macro cache that already exists.

The same cache contrast with `cone_slicing=True`, normal query bounds, n=3:

| Case | Baseline call ms | Combined cache call ms | Reduction |
|---|---|---|---|
| `codex_vtol_mission_supervision` | 26323.49 (26297.15–26449.13) | 5148.52 (5104.88–5205.77) | 80.44% |
| `conveyor_counters` | 274.26 (272.26–275.45) | 275.58 (271.73–281.00) | -0.48% |

VTOL still spends 23,910 ms in partition validation with slicing enabled; the
combined cache reduces that phase to 2,698 ms. This corroborates that the macro
bottleneck is outside the assignment slice. Conveyor has negligible macro work
and shows no benefit. This is a cache experiment under slicing, not a slicing
on/off speed comparison; do not compare absolute times across campaigns.

## Relation lowering and small SAT probes

For `claude_traffic_emergency_priority/reach`, the macro factorial's median
baseline call takes 1,682 ms, including about 1,221 ms in relation steps and only
5.5 ms in partition validation. Macro caches do not materially improve it.
The separate profile identifies 739 calls to `solver.logical.is_sat`, including
603 conditional branch feasibility calls. Every original request constructs a
fresh solver. This work is inside construction, even though it invokes Z3.

Three ordinary repetitions for each contrasted arm, p50 (min–max), ms:

| Case | Control call | With exact SAT reuse | Reduction | Hits/requests | RSS p50 MiB |
|---|---|---|---|---|---|
| `claude_traffic_emergency_priority` | 1217.66 (1212.98–1232.46) | 882.44 (876.98–893.99) | 27.53% | 486/739 | 115.9 → 116.3 |
| `codex_traffic_emergency_priority` | 1282.56 (1248.93–1308.10) | 999.66 (985.87–1002.38) | 22.06% | 657/937 | 116.7 → 117.0 |
| `conveyor_counters` | 307.27 (303.80–307.53) | 278.80 (277.05–281.14) | 9.26% | 135/151 | 115.1 → 114.9 |
| `ratio_estimator` | 119.92 (119.85–120.27) | 115.03 (114.38–115.52) | 4.08% | 28/29 | 111.4 → 111.5 |
| `codex_vtol_mission_supervision` (after combined macro cache) | 5652.15 (5644.20–5666.32) | 5183.08 (5170.47–5213.00) | 8.30% | 1856/1902 | 169.1 → 170.6 |

The additional VTOL baseline without macro caches has one sample only. It is a
correctness anchor; the timing contrast above compares the two n=3 arms after
macro caching, not that single baseline sample.

In the separate traffic profile, the original `logical.is_sat` and
`_check_solver` each execute 739 times without reuse and 253 times with reuse.
The 603 branch-feasibility requests remain present and their results stay
identical; only repeated solving is avoided. This verifies the repeated-request
hypothesis. After reuse, relation steps still occupy most of the traffic call;
expression lowering, relation assembly and provenance remain relevant. For VTOL,
1,856 of 1,902 requests repeat, but removing those checks yields only a further
8.30% whole-call reduction after macro caching. A high hit rate is not itself
a whole-call speedup forecast.

## Correctness evidence and limits

The four completed campaigns contain **286 records: 274 ordinary observations
and 12 separate profiles**, with **107 successful SAT replays**. Macro factorial:
70 records; full corpus: 153; bound/slicing controls: 30; SAT probes: 33. All
required formula, macro, partition, verdict and replay comparisons pass. All SAT
probe request fingerprints pass. Two corpus records select different valid
elevator witnesses; the other completed comparisons keep identical normalized
witnesses. The earlier strict-witness attempt is excluded from these totals.

One initial corpus attempt required identical witness bytes for every SAT query
and stopped on the first elevator example. Its manifest, baseline record and
failure log are preserved under `witness_equality_probe/`; it is not counted as a
successful campaign. The refined observer retains complete normalized witnesses,
records equality separately, and continues to require exact core/objective,
macro-contract and partition-check fingerprints, equal verdicts, and successful
ordinary replay. SAT probe campaigns additionally require identical ordered
request formulas, budgets, model flags and normalized statuses.

The elevator query uses `init cold havoc *` and permits multiple valid witnesses.
The differing records contain actual different initial values and upward versus
downward traces, not merely timing metadata. Both satisfy the same formula and
pass ordinary replay. This matches the umbrella's existing contract for
multi-solution queries. The exact cause of solver witness selection changes was
not isolated; semantic equivalence does not promise stable witness bytes.
Applications that snapshot a particular arbitrary solver witness should be
included in compatibility review before a production change.

The self-check covers cache hook restoration, missing references, accepted cycles,
definite SAT/UNSAT reuse, timeout/model bypass, and refusal to cache unknown or
timeout. This does not establish complete safety for malformed graphs, registry
mutation, multiple threads/contexts, all seven property families, every public
API composition, or Python 3.7–3.14 and every supported OS. The 51-query corpus
covers reach/forbid/invariant. Production changes need the existing broader
semantic fixtures and supported-version checks.

## Next work, in order

1. Implement reuse of completed accepted-condition resolution with ownership
   limited to one source partition or build. Preserve all validation, deterministic
   canonical output and ordinary witness replay. Prove cache lifetime, cycle and
   error behavior and repeated builds; rerun the formal benchmark and measure RSS.
2. Implement exact, definite SAT feasibility reuse scoped to the BMC build.
   Preserve context identity, request formulas, timeout/model behavior, unknown
   propagation and diagnostic metadata. Validate it independently on the full
   corpus and broader property/definedness fixtures, with memory and worst-query
   regressions measured before adoption.
3. Evaluate residual variable/evaluation traversals and repeated lowering only
   after profiling the first production change. Earlier structural recognition is
   another hypothesis but must preserve variable metadata and invalid-input
   diagnostics; it was not tested here.
4. Keep solver profiles and slicing opt-in, and retain T1–T3 failures. Any future
   default change or umbrella merge to main requires separate review and current
   gates; these microexperiments do not make that decision.

This round identifies concrete opportunities within the present framework. It
adds no cache, dependency, public flag, schema field or behavior change to the
production package. Existing users do not execute the experimental arms.

## Reproduction and verification

The first factorial and aborted strict-witness probe use the tool at
`b96b8932` (SHA256
`c67d73751505ac1d9ba82fae09f7146d8954e453130439042e55c3e9d32dd3b8`).
The other three campaigns use `88a25ed1` (SHA256
`bb1d70383a91ee699febc987c519487f85a5d4fb8b9f32d7aa5cf3c408e24639`).
Their manifests contain every input specification, order and repetition. Python
3.10.1 and Z3 4.15.4 were used. Use the matching installed dependencies and a new
output directory for each rerun; timings need not reproduce exactly.

From the repository root, with that Python environment activated:

```bash
git worktree add --detach /tmp/bmc-diagnosis-checkout 1aa4315a105eba0c4ae9e7998b9b2517b7ef65e4
git show b96b8932:tools/profile_bmc_construction.py > /tmp/profile-macro.py
git show 88a25ed1:tools/profile_bmc_construction.py > /tmp/profile-construction.py
python - <<'PYTHON'
import json
from pathlib import Path
root = Path('benchmarks/bmc/solving/outputs/construction_profiles/1aa4315a105e')
for name in ('macro_cache', 'corpus', 'scaling', 'sat_probes'):
    specs = json.loads((root / name / 'manifest.json').read_text())['specs']
    Path('/tmp/' + name + '-specs.json').write_text(json.dumps(specs))
PYTHON
python /tmp/profile-macro.py --checkout /tmp/bmc-diagnosis-checkout --specs /tmp/macro_cache-specs.json --output /tmp/macro_cache-reproduction
for campaign in corpus scaling sat_probes; do
    python /tmp/profile-construction.py --checkout /tmp/bmc-diagnosis-checkout --specs "/tmp/$campaign-specs.json" --output "/tmp/$campaign-reproduction"
done
python tools/profile_bmc_construction.py --check
python benchmarks/bmc/solving/outputs/construction_profiles/1aa4315a105e/analyze.py > /tmp/bmc-summary-rebuilt.json
cmp benchmarks/bmc/solving/outputs/construction_profiles/1aa4315a105e/summary.json /tmp/bmc-summary-rebuilt.json
```

[analyze.py](analyze.py) verifies record counts, specification order, cross-arm
contracts and successful SAT replay while rebuilding [summary.json](summary.json).
This rebuild does not rerun measurements or overwrite them. Raw records and
manifests are preserved in [macro_cache](macro_cache/), [corpus](corpus/),
[scaling](scaling/) and [sat_probes](sat_probes/). The failed stricter observation
is preserved in [witness_equality_probe](witness_equality_probe/).

Proportional checks: experiment self-check, resource ownership gate, Ruff,
complete campaign contracts, byte-identical summary reconstruction, the existing
benchmark `--check`, and `git diff --check` all passed.
`make unittest` does not apply because `pyfcstm/`, `templates/` and `test/` are
unchanged. `make rst_auto` does not apply to tools outside `PYTHON_CODE_DIR`;
`make doctest` does not apply because packaged docstrings and its gate are
unchanged. `make contents` does not apply to benchmark Markdown outside Sphinx.
These are scope-based exclusions, not claims that a new production optimization
has passed the full package suite.

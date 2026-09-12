# BMC solving benchmark

Every user-visible BMC option changes how the formula is built or how Z3 is
constructed, never what the property means.  So the question for any such knob
is the same twice over: does every answer stay identical, and what does it
cost?  This directory holds the corpus, the arm table, the pre-registered
thresholds, an oracle that checks the corpus expectations against the
simulator, the schema for a run, and the saved runs that answer it.

The first knobs measured here are a solver profile (logic fragment or tactic
selection) and cone-of-influence slicing.  Later work on iterative deepening
and unbounded proofs is expected to reuse the same corpus and runner, which is
why the arm table is data rather than a frozen list of names.

## Running it

```bash
python tools/run_bmc_solving_benchmark.py --check
python tools/run_bmc_solving_benchmark.py --self-test
python tools/run_bmc_solving_benchmark.py --oracle
python tools/run_bmc_solving_benchmark.py --run --repetitions 5 --warmups 1
python tools/run_bmc_solving_benchmark.py --run --cases telemetry_outputs,ratio_estimator --run-id scratch
python tools/run_bmc_solving_benchmark.py --rebuild <run-id>
```

`make bmc_solving_benchmark_check` runs `--check` and `--self-test`;
`make bmc_solving_benchmark` runs those and then a measurement.

`--check` validates the corpus, the arm table, this README's threshold rows,
`schema.json`, and every saved run, without solving anything; it also says
when a saved run was measured against a corpus or README that has since
changed.  `--self-test` proves each of those gates can fail, by mutating a
scratch copy of the corpus and expecting `--check` to reject it, and proves a
rebuild is a pure function of `raw.jsonl`.  `--oracle` re-derives every
enumerable expectation from the simulator (see below).  `--run` writes a new
immutable run under `outputs/runs/<run-id>/`; `--cases` restricts it to named
cases and the manifest records the filter, and `--timeout-ms` forwards a solver
budget to every arm, also recorded.  `--rebuild` recomputes `summary.json` and
`report.md` from `raw.jsonl` and compares them byte for byte with the saved
files, which is how a reader confirms the aggregation is a function of the
recorded samples and not of the process that produced them; it never
overwrites a saved file, and only writes the two when a run was interrupted
before they existed.

This is not a pytest suite and must not become one.  Distribution
measurements are not assertions, and a test that fails because the machine
was busy teaches nothing.  The API and the invariants are covered by
`test/bmc/`.

## The arms

An arm is one commit plus two option sets.  Every arm, including the one for
the current revision, runs from a detached worktree of its commit; the child
reports `pyfcstm.__file__` and the parent refuses a sample whose package did
not come from that worktree.  What sits untracked in the working tree can
therefore not reach a measurement, and `manifest.json` records the working
tree listing as evidence rather than as a taint.

The option sets are forwarded unchanged: `compile` becomes
`BmcOptions(**compile)` and `solve` becomes keyword arguments of
`solve_bmc_property`.  A key the production API does not know raises
`TypeError` there, so an arm cannot measure the default under a new name, and
an arm with empty sets calls the API exactly as an older revision expects.

| Arm | What it isolates |
|---|---|
| `baseline-0cc43647` | The last `main` commit before any solving option existed, `0cc43647ad85c99347fbdd8eab0259279a5f40d0`. Separates an overhead the option infrastructure adds on every run from the option itself. |
| `default` | The current revision with both option sets empty. Every other arm is compared against it under H0. |
| `logic` | The current revision with `solver_profile=logic`; probes choose a fragment or fall back to default. |
| `tactic` | The current revision with `solver_profile=tactic`; the simplify/propagate-values/solve-eqs/smt pipeline is used for main staged checks. |
| `cone_slicing` | The current revision with `cone_slicing=True`; conservative write elimination, complete witness reconstruction and at most one full-model retry. |

The change that adds an option appends its arm to `_ARMS` in the runner and
to this table, and evaluates its own T row.  Without `baseline`, an overhead
the infrastructure imposes on every run would be invisible.  Without
`default`, that overhead would be charged to the option.

## The corpus

17 cases, 51 queries: 13 `sat` and 38 `unsat`.  Twelve cases are
LLM-generated models copied from `llm_eval/outputs/` -- copied, not
referenced, so the benchmark keeps running if that directory changes -- and
five are handwritten to exercise one shape each.  The LLM models are the
population this benchmark is for: every one that parses and inspects without
an error-level diagnostic is included, which is all twelve.  Eleven of them
declare six or more persistent variables; the twelfth declares four and is
kept because a benchmark that drops the smallest real model is choosing its
own result.

Most queries come out `unsat`.  That is a fact about LLM-generated
controllers, not a defect of the corpus: they declare many input-like
variables that no action ever writes, so most safety properties hold
trivially and the solver has to exhaust the whole bounded search to say so.
An `unsat` answer is where solver effort goes, which is what a solving
benchmark should be measuring.  Half of the `reach` queries relax every
initial value with `havoc *` so the search space is not fixed by the
declared initializers; `case.json` says which.

| Case | Role | Source | Queries | Why |
|---|---|---|---|---|
| `claude_distributed_elevator_can` | `llm_generated` | `llm_eval/outputs/claude/distributed_elevator_can/model.fcstm` | reach `sat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `claude_platooning_join_protocol` | `llm_generated` | `llm_eval/outputs/claude/platooning_join_protocol/model.fcstm` | reach `unsat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `claude_traffic_emergency_priority` | `llm_generated` | `llm_eval/outputs/claude/traffic_emergency_priority/model.fcstm` | reach `sat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `claude_vtol_mission_supervision` | `llm_generated` | `llm_eval/outputs/claude/vtol_mission_supervision/model.fcstm` | reach `unsat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_deepseek_distributed_elevator_can` | `llm_generated` | `llm_eval/outputs/codex-deepseek/distributed_elevator_can/model.fcstm` | reach `unsat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_deepseek_platooning_join_protocol` | `llm_generated` | `llm_eval/outputs/codex-deepseek/platooning_join_protocol/model.fcstm` | reach `unsat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_deepseek_traffic_emergency_priority` | `llm_generated` | `llm_eval/outputs/codex-deepseek/traffic_emergency_priority/model.fcstm` | reach `sat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_deepseek_vtol_mission_supervision` | `llm_generated` | `llm_eval/outputs/codex-deepseek/vtol_mission_supervision/model.fcstm` | reach `sat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_distributed_elevator_can` | `llm_generated` | `llm_eval/outputs/codex/distributed_elevator_can/model.fcstm` | reach `sat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_platooning_join_protocol` | `llm_generated` | `llm_eval/outputs/codex/platooning_join_protocol/model.fcstm` | reach `unsat`, forbid `unsat`, invariant `unsat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_traffic_emergency_priority` | `llm_generated` | `llm_eval/outputs/codex/traffic_emergency_priority/model.fcstm` | reach `sat`, forbid `unsat`, invariant `sat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `codex_vtol_mission_supervision` | `llm_generated` | `llm_eval/outputs/codex/vtol_mission_supervision/model.fcstm` | reach `unsat`, forbid `unsat`, invariant `sat` | LLM-generated model from the evaluation corpus; the population the benchmark is for. |
| `conveyor_counters` | `slicing_positive` | handwritten | reach `sat`, forbid `unsat`, invariant `unsat` | The stat_* counters are written inside a composite by enter blocks and effects, never read. |
| `heater_logging` | `slicing_positive` | handwritten | reach `sat`, forbid `unsat`, invariant `unsat` | The log_* variables accumulate in during blocks and read only themselves and kept variables. |
| `pump_supervisor_hooks` | `abstract_skip` | handwritten | reach `sat`, forbid `unsat`, invariant `unsat` | Abstract enter/during/exit hooks observe the whole environment, so a slice must skip this model. |
| `ratio_estimator` | `definedness_trap` | handwritten | reach `unsat`, forbid `sat`, invariant `unsat` | mean is never read but is computed by a division whose divisor is zero on the first Report entry. |
| `telemetry_outputs` | `slicing_positive` | handwritten | reach `sat`, forbid `unsat`, invariant `unsat` | Four out_* variables are written every round and never read; the slice should drop them. |

Roles:

- `llm_generated`: the population; measured as found.
- `slicing_positive`: variables written on every round and never read by a
  guard or a property, so a cone-of-influence slice has something to drop.
- `definedness_trap`: an unread variable computed by a division whose
  divisor is zero on the first pass.  Dropping the unread assignment also
  drops the division's definedness condition, so a slice that ignores this
  produces a witness the runtime cannot replay; the cold-start `reach` query
  is `scenario_infeasible` and must stay so under every arm.
- `abstract_skip`: abstract lifecycle hooks observe the whole variable
  environment, so a slice must leave this model alone.

Each `case.json` records what every query returned under `default` when the
corpus was frozen: `status`, `property_satisfied`, and `outcome`.  Those are
the expectations H0 reads back.  They protect against drift.  Whether they
were right when recorded is the oracle's question.

## The oracle

Speed without a correct answer is worthless, and the expectations above come
from the encoder being measured.  `--oracle` therefore re-derives each one
with `SimulationRuntime`, the runtime that already replays every witness,
without touching the encoder: it enumerates the frame-0 assignments the
query admits, explores every execution up to the bound with every subset of
events per step, prunes a step whose action is undefined (a division by
zero, or a non-integer quotient written to an integer variable, exactly the
steps the encoder's definedness conditions exclude), and decides the query
from its semantics.  A `reach` or `forbid` is `sat` when some frame satisfies
the body; an `invariant` is `sat` when some frame violates it.

Its reach is bounded and stated per query.  A model with more than four
events is explored with the empty step and single events only, an
under-approximation that can find a witness the encoder missed but cannot
refute an encoder `sat`.  A `havoc *` initialization is not enumerable and is
skipped; a `where` clause with only a lower bound is sampled at three values.

Coverage when the corpus was frozen: 34 queries match exactly under
exhaustive exploration, 11 are consistent under an under-approximation or a
sampled initialization, and 6 `havoc *` `reach` queries are skipped.  Five of
those six are `sat` and their witnesses replay on the runtime in every run;
one, `codex_deepseek_distributed_elevator_can/reach`, is `unsat` and rests on
the encoder alone.  No query disagrees.

## Method

Each sample runs in a fresh interpreter.  Z3 keeps state between checks
within one process, so a second measurement in the same interpreter measures
a warmed solver rather than the sample.  Every child runs with its arm's
worktree as the working directory, which is what makes `import pyfcstm`
resolve to that commit; the parent verifies it from the child's own report.

Warmups run once per arm, before the corpus loop, and are discarded.  A
sample is already a fresh process, so all a warmup can warm is the page
cache and the worktree's compiled bytecode; one per arm covers that.

Three regions are timed separately in the child: `build_ms` is
`compile_bmc_query`, the region an encoding option changes; `solve_ms` is
`solve_bmc_property`, the region a solver option changes; `replay_ms` is
decoding and replaying the witness, only when the primary status is `sat`.
`total_elapsed_ms` is the solver's own accounting from the result.

`formula_dag_nodes` counts distinct Z3 AST ids reachable from the core formula
and the objective.  It is the one size measure here that is stable across
processes, and it is what a slice shrinks.  New runs also record `BmcSolveResult.solver_statistics`, captured directly
from the production solver after the primary check. Each available statistic
has a distribution in `summary.json`; missing keys stay absent. Keys depend
on the Z3 version and solver profile. In particular, `rlimit count` and
`num allocs` are context-wide counters, including earlier compilation work;
they must not be read as per-query work or compared as adoption gates.
The older baseline release does not publish statistics and is left absent.
`solver_profile` and `solver_logic` record what actually ran; a `logic` arm
with a null logic used the default solver after no probe matched.

Peak memory is `ru_maxrss` read by the child right after replay, before the
size walk allocates anything, so it is the kernel high-water mark of the
production path.  It is absent, never zero, where the `resource` module does
not exist.

The manifest binds the input digests, the README digest, the baseline and
candidate commits, the working tree listing, and the machine and dependency
facts.  A saved run is never overwritten; a correction creates a new run id.

## Pre-registered thresholds

These rows were written and committed before the first measurement and are
read back by `--check`.  A threshold that is not met is recorded as not met.
It is never moved to fit a result, and an option that misses its row stays
opt-in with the measured numbers written next to it.

| Id | Applies to | Rule |
|---|---|---|
| H0 | every arm other than `default` | Compared with `default`, query by query, `status`, `property_satisfied`, `outcome`, and replay `ok` are all identical, and `status`, `property_satisfied` and `outcome` equal the `case.json` expectation. A field that varies between repetitions fails, and so does any sample that crashed. The count of `unknown` and `timeout` answers does not increase. A miss means the option does not merge, whatever it costs or saves. |
| T1 | a `solver_profile=logic` arm | The median over queries of the per-query `solve_ms` p50 improves by at least 15% against `default`, and no single query regresses by more than 10%. |
| T2 | a `solver_profile=tactic` arm | As T1. |
| T3 | a `cone_slicing` arm | On the queries whose model has at least one variable the slice drops, `formula_dag_nodes` falls by at least 20% and `solve_ms` p50 does not regress by more than 5%. On the queries with nothing to drop, `build_ms` plus `solve_ms` p50 grows by at most 5%. The slice falls back to the full model zero times across the corpus. |

H0 is evaluated by the runner for every run and printed in the report; a
SAT sample must replay successfully even if both arms would otherwise agree
on a failed replay. The `default` row itself must match the expectation.

The numeric T1/T2 thresholds are copied from `_SOLVER_THRESHOLDS` into each
new `manifest.json` as `solver_thresholds`, and the run schema pins their
values to the table above. The report computes both gates from those frozen
values: median improvement is `1 - median(candidate p50) / median(default
p50)`, while worst regression is the maximum per-query ratio minus one.
Missing measurements or failed H0 prevent adoption. Ratios in the report
are percentages. Historical manifests without these fields
remain byte-for-byte rebuildable.

The slicing arm enables `BmcOptions(cone_slicing=True)`. Its T3 numbers are
frozen in `slicing_thresholds`. Queries are partitioned by the actual
`dropped_variables`, including any attempted slice that falls back. DAG and
solve ratios compare medians across the per-query measurements in the sliced
partition. The unsliced ratio compares medians of per-query p50s of each
sample's `build_ms + solve_ms`. Both partitions must be represented; missing
measurements or failed H0 prevent adoption. Fallback must be zero in every
sample, not merely at the median.

Slicing preserves guards, ordered branch conditions, abstract models and
potentially partial arithmetic, including their dependencies. The
`definedness_trap` case must retain the dangerous assignment; it does not
need to trigger fallback. Unit tests exercise fallback independently.
`solve_ms` includes the production slice verification and any full-model
rebuild and retry. External decoding and replay are additionally measured
in `replay_ms`, including response incomplete suffixes. A failed suffix
replay fails H0, even when the primary result has no SAT witness. Complete
witness values are checked against the ordinary simulator in semantic tests;
queries with multiple legal solutions need not choose the same path.

## What a run settles

The [solver-profile run](outputs/runs/cd24a68e137b/report.md) measures commit
`36ae48d5` with a clean manifest on Linux x86_64, CPython 3.10.1 and Z3
4.15.4: 1,020 samples, zero failures, 260 successful SAT replays and H0
passing for all 51 queries in every arm. Median query p50 is 11.950 ms for
the old baseline and 12.036 ms for default (0.72% higher).

| Profile | Median query p50 | Improvement against default | Worst regression | Adoption gate |
|---|---:|---:|---:|---|
| `logic` | 11.730 ms | 2.54% | 46.88% | T1 not met |
| `tactic` | 11.105 ms | 7.74% | 409.44% | T2 not met |

Logic's worst regression is `pump_supervisor_hooks/forbid` (4.245 to
6.235 ms); tactic's is `ratio_estimator/reach` (5.711 to 29.092 ms).
Both remain opt-in. These measurements describe one environment and do
not guarantee a speedup for another workload. H0 here verifies semantic
verdicts and successful replay, not equality of the particular valid
witness selected by each solver strategy.

A run with only `baseline` and `default` establishes the two reference
distributions and proves H0 holds between them, which is the precondition
for reading any later arm.  A run with an option arm answers, per query,
whether the option changed an answer (it must not) and what it did to solve
time, build time, formula size and memory.  It does not settle whether the
option should become the default; that is a separate decision made with the
run as evidence.

### Conservative slicing measurements

The [five-arm run](outputs/runs/2db089114bb5/report.md) binds clean implementation
commit `2db089114bb5137aaf5a94d18af9949066f4bb6c` on Linux x86_64, CPython
3.10.1 and Z3 4.15.4. It contains 1,275 measured samples, zero failures,
325 successful SAT replays and no slicing fallback. H0 passes every arm and
query. Of the 51 queries, 32 actually remove variables and 19 do not.

| T3 component | Default | Slicing | Change | Requirement |
|---|---:|---:|---:|---|
| Sliced queries: formula DAG p50 | 2,399 nodes | 2,253 nodes | 6.09% fewer | At least 20% fewer: not met |
| Sliced queries: query solve p50 | 15.650 ms | 15.528 ms | 0.78% faster | At most 5% regression: met |
| Unsliced queries: query build + solve p50 | 263.482 ms | 262.975 ms | 0.19% faster | At most 5% regression: met |
| Fallback samples | — | 0 | — | Zero: met |

T3 is **not met**, so slicing remains disabled by default. These aggregates
use the runner's existing discrete percentile helper: sort the values and
select index `round(0.5 * (n - 1))`, with a zero-based index. For 32 queries,
this selects the 17th observation. Five repetitions determine each query's
p50 before aggregation across queries.

The small aggregate solve change does not promise a speedup on each query.
The largest solve regression is `codex_traffic_emergency_priority/invariant`:
10.178 to 23.586 ms (**131.73% slower**). Sliced SAT candidates incur runtime
verification inside solve, and external decoding/replay is still additional
work. Among sliced queries with replay, external replay p50 rises from
11.650 to 17.184 ms. Keep this cost in end-to-end comparisons.

Removing output variables leaves state, event, selector, initial-value and
control-flow constraints intact. For example, `codex_vtol_mission_supervision/reach`
removes five of ten variables but DAG size falls only from 13,444 to 13,205
nodes. Its build p50 is 26,478.520 ms before slicing and 25,873.804 ms after;
solve p50 is 159.082 and 119.164 ms respectively. Formula construction
therefore remains the dominant cost on this query. Further performance work
should first profile construction rather than assume more write removal
will address the main cost.

The same run again leaves solver profiles opt-in: logic's aggregate solve
change is a 1.49% regression with a worst query regression of 45.97%; tactic
improves 5.17% in aggregate but regresses 417.94% on its worst query. T1 and
T2 remain unmet. Results are specific to the recorded environment and corpus;
no default option changes follow from this run.

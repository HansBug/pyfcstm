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
processes, and it is what a slice shrinks.  A solver-effort counter is not
published: Z3's `rlimit count` is cumulative per context and the production
solver does not expose its statistics, so an honest per-solve reading needs
production support first.

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

H0 is evaluated by the runner for every run and printed in the report; the
`default` row itself can only miss the expectation.  T1 to T3 are evaluated
by the change that introduces the option, against the run it commits,
because only that change knows which queries its option can touch.

## What a run settles

A run with only `baseline` and `default` establishes the two reference
distributions and proves H0 holds between them, which is the precondition
for reading any later arm.  A run with an option arm answers, per query,
whether the option changed an answer (it must not) and what it did to solve
time, build time, formula size and memory.  It does not settle whether the
option should become the default; that is a separate decision made with the
run as evidence.

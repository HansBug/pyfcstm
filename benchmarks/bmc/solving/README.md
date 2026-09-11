# BMC solving benchmark

Every user-visible BMC option changes how the formula is built or how Z3 is
constructed, never what the property means.  So the question for any such knob
is the same twice over: does every answer stay identical, and what does it
cost?  This directory holds the corpus, the arm table, the pre-registered
thresholds, the schema for a run, and the saved runs that answer it.

The first knobs measured here are a solver profile (logic fragment or tactic
selection) and cone-of-influence slicing.  Later work on iterative deepening
and unbounded proofs is expected to reuse the same corpus and runner, which is
why the arm table is data rather than four frozen names.

## Running it

```bash
python tools/run_bmc_solving_benchmark.py --check
python tools/run_bmc_solving_benchmark.py --self-test
python tools/run_bmc_solving_benchmark.py --run --repetitions 5 --warmups 1
python tools/run_bmc_solving_benchmark.py --rebuild <run-id>
```

`make bmc_solving_benchmark_check` runs the first two; `make bmc_solving_benchmark`
runs all of that and then a measurement.

`--check` validates the corpus, the arm table, this README's threshold rows,
`schema.json`, and every saved run, without solving anything.  `--self-test`
proves each of those gates can fail, by mutating a scratch copy of the corpus
and expecting `--check` to reject it, and proves a rebuild is a pure function
of `raw.jsonl`.  `--run` writes a new immutable run under
`outputs/runs/<run-id>/`.  `--rebuild` regenerates `summary.json` and
`report.md` from `raw.jsonl`, which is how a reader confirms the aggregation
is a function of the recorded samples and not of the process that produced
them.

This is not a pytest suite and must not become one.  Distribution
measurements are not assertions, and a test that fails because the machine
was busy teaches nothing.  The API and the invariants are covered by
`test/bmc/`.

## The arms

An arm is one revision plus one set of options forwarded to the child.  The
child refuses an option key it does not know, so adding an arm without
teaching the child what it measures fails instead of measuring the default
under a new name.

| Arm | What it isolates |
|---|---|
| `baseline-0cc43647` | The umbrella's creation base, `0cc43647ad85c99347fbdd8eab0259279a5f40d0`, checked out into a detached worktree. Separates an overhead the option infrastructure adds on every run from the option itself. |
| `default` | The working tree with no option set. Every other arm is compared against it under H0. |

Sub-PRs that add an option append their arms here and to `_ARMS` in the
runner, and evaluate their own T rows.  Without `baseline`, an overhead the
infrastructure imposes on every run would be invisible.  Without `default`,
that overhead would be charged to the option.

## The corpus

17 cases, 51 queries: 13 `sat` and 38 `unsat`.  12 cases are
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
the expectations H0 reads back.  They protect against drift; they are not a
claim that the tool was right when they were recorded.

## Method

Each sample runs in a fresh interpreter.  Z3 keeps state between checks
within one process, so a second measurement in the same interpreter measures
a warmed solver rather than the sample.  Running separately also makes peak
RSS meaningful: it is the child's high-water mark rather than the runner's.
The baseline arm runs the same child with the detached worktree as its
working directory, which is what makes `import pyfcstm` resolve to that
revision; the package is not installed into the interpreter, so the working
directory decides.

Warmups run first and are discarded, and their count is recorded separately.

Three regions are timed separately in the child: `build_ms` is
`compile_bmc_query`, the region an encoding knob changes; `solve_ms` is
`solve_bmc_property`, the region a solver knob changes; `replay_ms` is
decoding and replaying the witness, only when the primary status is `sat`.
`total_elapsed_ms` is the solver's own accounting from the result.

Two size measures do not depend on wall time.  `formula_dag_nodes` counts
distinct Z3 AST ids reachable from the core formula and the objective, which
is what a slice shrinks.  `rlimit_count` is Z3's own effort counter, read from one
plain side check of the same conjunction after every timed region has ended;
`solve_bmc_property` owns its solver and does not expose statistics, so this
is the closest honest reading and the report says so.  It is steadier than
wall time but not identical across processes: in the smoke run two arms
running identical code differed by about one percent on one `sat` query, so
read small differences as noise.

RSS uses `psutil` from the existing development environment.  No runtime
dependency is added.  When `psutil` is unavailable the metric is reported
absent, never as zero.  The number is a **sampled maximum, not a kernel
high-water mark**: the child is polled every 2 ms, so a spike shorter than
that can be missed.

The manifest binds the input digests, the README digest, the baseline and
candidate commits, the dirty-state evidence, and the machine and dependency
facts.  A saved run is never overwritten; a correction creates a new run id.

## Pre-registered thresholds

These rows were written and committed before the first measurement and are
read back by `--check`.  A threshold that is not met is recorded as not met.
It is never moved to fit a result, and an option that misses its row stays
opt-in with the measured numbers written next to it.

| Id | Applies to | Rule |
|---|---|---|
| H0 | every arm other than the baseline | Compared with `default`, query by query, `status`, `property_satisfied`, `outcome`, and replay `ok` are all identical, and `status` equals the `case.json` expectation. A field that varies between repetitions fails. The count of `unknown` and `timeout` answers does not increase. A miss means the option does not merge, whatever it costs or saves. |
| T1 | a `solver_profile=logic` arm | The median over queries of the per-query `solve_ms` p50 improves by at least 15% against `default`, and no single query regresses by more than 10%. |
| T2 | a `solver_profile=tactic` arm | As T1. |
| T3 | a `cone_slicing` arm | On the queries whose model has at least one variable the slice drops, `formula_dag_nodes` falls by at least 20% and `solve_ms` p50 does not regress by more than 5%. On the queries with nothing to drop, `build_ms` plus `solve_ms` p50 grows by at most 5%. The slice falls back to the full model zero times across the corpus. |

H0 is evaluated by the runner for every run and printed in the report.  T1 to
T3 are evaluated by the sub-PR that introduces the option, against the run it
commits, because only that sub-PR knows which queries its option can touch.

## What a run settles

A run with only `baseline` and `default` establishes the two reference
distributions and proves H0 holds between them, which is the precondition
for reading any later arm.  A run with an option arm answers, per query,
whether the option changed an answer (it must not) and what it did to solve
time, build time, formula size, and deterministic effort.  It does not
settle whether the option should become the default; that is a separate
decision made with the run as evidence.

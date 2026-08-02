# BMC infeasibility explanation benchmark

The optional explanation (`pyfcstm bmc --explain-infeasibility`) is opt-in, so the
question a user has is what each depth costs. This directory holds the corpus, the
schema for a run, and the saved runs.

## Running it

```bash
python tools/run_bmc_infeasibility_benchmark.py --check
python tools/run_bmc_infeasibility_benchmark.py --run --repetitions 5 --warmups 1
python tools/run_bmc_infeasibility_benchmark.py --rebuild <run-id>
```

`--check` validates the corpus and layout without measuring anything. `--run`
writes a new immutable run under `outputs/runs/<run-id>/`. `--rebuild` regenerates
`summary.json` and `report.md` from `raw.jsonl`, which is how a reader confirms
the aggregation is a function of the recorded samples and not of the process that
produced them.

This is not a pytest suite and must not become one. Distribution measurements are
not assertions, and a test that fails because the machine was busy teaches
nothing. The API and the invariants are covered by `test/bmc/`.

## The four arms

| Arm | What it isolates |
|---|---|
| `baseline-901f30e9` | The revision before the provenance infrastructure landed (`901f30e981c29eb8e304b33d61985652d2e85b2e`). |
| `none` | The infrastructure present, no explanation requested. Separates a cost every run pays from one the explanation adds. |
| `formal` | Classification, source core, minimization. |
| `proof` | Everything in `formal`, plus closure construction, verification, and linearization. |

Without `baseline`, an overhead the infrastructure imposes on every run would be
invisible. Without `none`, that overhead would be charged to the explanation.

## The corpus

Eight handwritten cases. Five close at `proof` depth — between them reaching every
rule the reference page marks reachable — two degrade to `formal`, and one is
feasible so the explanation does no work at all. The degrading and feasible
cases are part of the corpus rather than exceptions to it: a benchmark that only
measures cases which succeed reports a cost the user will not see.

| Case | Expected depth | What it exercises |
|---|---|---|
| `two_values` | `proof` | One variable pinned to two values at one frame. |
| `empty_interval` | `proof` | Bounds no value satisfies. |
| `two_states` | `proof` | Two states required of one frame. |
| `state_domain` | `proof` | Every state at a frame excluded at once. |
| `definedness` | `proof` | An operation that cannot stay defined. |
| `cross_step` | `formal` | A conflict visible only after accumulating across a step, which has no core member to attribute its key facts to. |
| `event_conflict` | `formal` | An event assumption published as `structural_constraint`, whose content no rule reads. |
| `feasible` | `none` | A feasible scenario; nothing to explain. |

## Method

Each sample runs in a fresh interpreter. Z3 keeps state between checks within one
process, so a second measurement in the same interpreter measures a warmed solver
rather than the sample. Running separately also makes peak RSS meaningful: it is
the child's high-water mark rather than the runner's.

Warmups run first and are discarded, and their count is recorded separately.

RSS uses `psutil` from the existing development/documentation environment. No
runtime dependency is added. When `psutil` is unavailable the metric is reported
absent, never as zero — a zero would read as a measurement.

The number is a **sampled maximum, not a kernel high-water mark**: the child is
polled every 2 ms, so a spike shorter than that can be missed. Polling flat out
would catch more of them and would also compete for CPU with the run whose
timings the same report publishes, which is the worse trade. The manifest records
the interval so a reader knows what the number is.

The manifest binds the input digests, the baseline and candidate commits, the
dirty-state evidence, and the machine and dependency facts. A saved run is never
overwritten; a correction creates a new run id.

## What the measurement map settles

The umbrella asks for proof construction, verification, and linearization as
separate metrics. The production ledger does not publish three entries:

```text
component_assumptions
unsat_core
unsat_core_minimization
core_binding
proof_construction
```

`core_binding` is the input-side verification. `proof_construction` covers closure
construction **and** derived-side `rule_checker` verification together; they are
not separable there. Linearization has no ledger entry at all, so it is timed in
the child around `pyfcstm.bmc.proof_text.linearize_proof` — a documented module
function with its own API page — and reported as benchmark-only instrumentation.

Choosing a reading silently at report time would make numbers incomparable between
runs, so the choice is frozen in `_MEASUREMENT_MAP` and repeated in every report.

## Reading a run

`report.md` leads with wall time per arm so the amplification is visible, then
records what each arm actually achieved, then which rules each case reached with
its node and edge counts and per-method verification totals, then failures,
degradation, and any published field that varied across repetitions. Instability in a published field
is a finding and is surfaced rather than collapsed into an average.

No hard millisecond thresholds are asserted. Distributions and amplification
factors are reported instead, because a threshold with no data behind it fails on
a slow machine and passes a real regression on a fast one.

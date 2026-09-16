# Preferred explanation measurements

This corpus measures the opt-in `explanation_preference="editable"` strategy against ordinary formal explanations. It is a quality/cost experiment, not a speedup claim. The baseline is umbrella commit `a20d8e6d5b00efbf58edeb4db9890a05bef4e74e`.

The runner's fixed corpus covers a two-step and a 100-step multi-conflict query, an assumptions-only conflict, a feasible query, and the 100-step query with only 5 ms of auxiliary budget. The first two have alternative independently contradictory subsets: a model-transition conflict and an initialization conflict. The strategy should select the query's `initial.where` plus its conflicting assumption; the ordinary solver may choose another valid core. The assumptions-only example has no selection improvement available. The feasible example must perform no preference search. The short budget must degrade honestly rather than claim minimality.

Reproduce on Linux with GNU `/usr/bin/time` and the repository's Python dependencies:

```bash
mkdir -p /tmp/preferred-baseline
# This is a source archive for measurement, not an implementation worktree.
git archive a20d8e6d5b00efbf58edeb4db9890a05bef4e74e pyfcstm | tar -x -C /tmp/preferred-baseline
python tools/benchmark_preferred_explanations.py \
  --baseline /tmp/preferred-baseline \
  --output /tmp/preferred-new-run
```

The runner verifies the baseline's three relevant implementation files against the recorded Git revision. Each run records the current SHA, source hashes, tracked source diff, runner hash, Python/Z3/platform versions, full model/query texts, and all observations. Official runs use a clean implementation commit; the evidence-only follow-up commit does not change those source files. A run refuses to overwrite an existing output directory. Do not edit historical manifests or raw samples.

Each case/arm/surface has one discarded warmup and five alternating measured samples in fresh subprocesses. The arms are the old default, new default, and new preferred selection. API timing includes model loading, query compilation, solving and canonical serialization, but excludes imports; `solve_ms` separately records the complete solve call. CLI wall time also includes interpreter startup, JSON serialization and normal process shutdown. RSS is GNU time's whole-process peak, in KiB. Solver-check instrumentation runs only in separate untimed observations. Timing rows retain all samples and report median and range, not only favorable averages.

`auxiliary_ms` is the existing explanation's reported elapsed time. It is not a complete accounting of late narrative/proof work and is not a hard wall-time guarantee. The finite budget limits solver work at phase/probe boundaries; an individual Python setup operation can overrun it. The small-budget row reports the observed overrun and actual quality status. No numeric performance acceptance threshold was specified for this experiment. Synthetic cases are not a representative distribution of production models; no production-wide overhead percentage follows from them.

Rebuild a report from its immutable raw observations:

```bash
python tools/benchmark_preferred_explanations.py --rebuild /tmp/preferred-new-run
```

The rebuild changes only `report.md`; it must reproduce the same presentation for the saved raw data. Recorded runs live under `outputs/runs/`. Runtime branch coverage is measured separately from performance, so coverage instrumentation is absent from timed subprocesses.

Recorded run: [measurements](outputs/runs/8d897a964a98/report.md), [validation and limitations](outputs/runs/8d897a964a98/validation.md), and [diff coverage](outputs/runs/8d897a964a98/diff-coverage.json).

# Construction text rendering measurements

Run from the repository root: `python benchmarks/bmc/infeasibility/outputs/readable_construction/measure.py`.

Seven alternating-order measurements after a warmup, on a shared Linux host with no concurrent local tests or documentation builds during the recorded run. The timer covers only `report.text_lines`; model loading, compilation, binding checks and output I/O are outside it. `samples.json` records every sample, Python/Z3/platform and source hashes. No samples were discarded and no performance gate was changed.

| Model | Text mode | Median ms | Lines | Characters |
|---|---|---:|---:|---:|
| dose_editor | compact | 537.028 | 2636 | 133257 |
| dose_editor | expanded | 1349.696 | 5870 | 276651 |
| dose_editor | selected_compact | 13.495 | 64 | 3416 |
| pool | compact | 401.155 | 2300 | 109388 |
| pool | expanded | 1236.161 | 5014 | 233261 |

`compact` and `expanded` include all step cases: 87 for the editor (bound 6), 93 for the pool (bound 8). `selected_compact` includes the editor's Review -> Trim at step 2 and Trim -> Ready at step 3, as in the runnable documentation example. These selections do not claim a feasible trace or an UNSAT core. Native formula output can be large; `expanded=True` deliberately includes full submitted formulas as well as expanded assignments.

Profiling observed zero Z3 `check` calls during compact rendering, and each compiled solve formula was unchanged afterwards. This experiment does not measure capture memory or establish a cross-platform upper bound. Rendering remains an explicit Python API operation, separate from solving; it is not automatically enabled for existing users.

The earlier `source_construction` experiment measured local action rendering in the preceding implementation. Its render column is historical and is not a baseline for this broader report (which also includes effective conditions, priority dependencies, guards, source groups and frame boundaries). The earlier capture/default API measurements are also historical; they were not rerun for this text-only extension. Existing formula/result tests and the full unit suite separately check behavior.

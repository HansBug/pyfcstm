# Scoped frame report rendering measurements

This measures explicit text generation, not BMC solve speed. Both renderers receive the same captured reports in the same Python process. The previous renderer is loaded from local Git revision `fc76dee2114330691e0f4da660b919e658fd3f48`; the current sources are identified by SHA-256 in `samples.json`.

Run from the repository root:

```bash
python benchmarks/bmc/infeasibility/outputs/frame_relations/measure.py --baseline fc76dee2114330691e0f4da660b919e658fd3f48
```

Seven alternating warmed measurements per variant, with compilation, binding checks and file I/O outside the timer. No other task-local tests/builds ran during measurement; this is a shared Linux host, not a dedicated performance machine. Range is min–max, not a confidence interval. The new layout adds complete frame output and changes formatting, so output sizes differ.

| Model / selection | View | Previous median (ms) | Current median [range] (ms) | Change | Current lines / characters |
|---|---|---:|---:|---:|---:|
| dose_editor (87 cases) | compact | 530.776 | 114.743 [112.577–115.633] | -78.4% | 2859 / 112991 |
| dose_editor (87 cases) | expanded | 1335.838 | 273.263 [267.860–276.592] | -79.5% | 7267 / 281538 |
| dose_editor (2 selected cases) | selected_compact | 13.724 | 4.959 [4.870–5.876] | -63.9% | 76 / 3316 |
| dose_editor (2 selected cases) | selected_expanded | — | 8.695 [8.349–9.248] | not measured | 154 / 6398 |
| pool (93 cases) | compact | 399.187 | 86.856 [85.767–88.039] | -78.2% | 2581 / 95836 |
| pool (93 cases) | expanded | 1225.712 | 234.522 [228.877–247.254] | -80.9% | 5428 / 217084 |

All measured variants performed **zero Z3 solver checks** during profiled rendering, and the compiled solve formula was byte-for-byte unchanged after all renders. These are display-only measurements. Detailed construction capture remains opt-in; this experiment does not remeasure or claim zero overhead for capture, compilation, solving, or memory.

The current path walks recorded ASTs once per scoped formatter, reuses local terms, and avoids the old repeated native printing/simplification. The difference is consistent with that implementation change; the experiment is not a universal speedup guarantee. Full expansion remains larger and slower than the default view. The exact samples, Python/Z3/platform versions, baseline renderer hash and current source hashes are in `samples.json`.

# Source construction performance

Baseline: 7cea5bed. Seven interleaved groups, one warmup and one measured pass per worker; nine workloads, three modes. Shared Linux host; GC enabled. Times are medians in milliseconds. API includes parse/compile/solve and mandatory replay; capture checking and full local rendering are separate. No samples discarded.

| Case | Baseline API | Default API | Change | Recorded API | Capture vs default | Check | Render |
|---|---:|---:|---:|---:|---:|---:|---:|
| long_variables_64_bound_8 | 333.767 | 333.699 | -0.02% | 346.579 | +3.86% | 44.598 | 302.899 |
| counter_bound_8 | 33.301 | 33.065 | -0.71% | 34.989 | +5.82% | 2.806 | 4.709 |
| inputs_parameters | 80.115 | 80.644 | +0.66% | 85.475 | +5.99% | 9.676 | 8.519 |
| sixteen_guards | 2090.368 | 2096.426 | +0.29% | 2130.587 | +1.63% | 55.569 | 160.128 |
| original_sat_reach | 43.319 | 42.377 | -2.17% | 45.267 | +6.82% | 3.662 | 4.744 |
| pool | 85.606 | 86.896 | +1.51% | 91.611 | +5.43% | 10.860 | 104.506 |
| definedness | 9.988 | 9.935 | -0.53% | 10.003 | +0.68% | 0.153 | 0.002 |
| dose_editor | 166.774 | 167.124 | +0.21% | 177.519 | +6.22% | 28.572 | 144.419 |
| counter_bound_128 | 482.166 | 492.055 | +2.05% | 526.066 | +6.91% | 49.738 | 84.402 |

All property/status signatures and compile/solve solver-call counts agree across variants. All captured reports completed their binding checks. This is not evidence of complete UNSAT derivations.

Process peak RSS includes every workload and, for recorded workers, subsequent checking/rendering; it is not capture-only memory.
- baseline: median 138588 KiB, range 137888–139356 KiB.
- default: median 139476 KiB, range 137772–139904 KiB.
- recorded: median 138880 KiB, range 138408–139708 KiB.

## Reproduction and limits

`run.py` is the exact archived runner used on the measured host (its absolute snapshot paths are recorded, not portable defaults). `samples.jsonl` begins with source and measurement-script SHA-256 hashes. The baseline was extracted with `git archive`, not a worktree. To repeat against your own snapshots, run `worker.py BASELINE_ROOT 19200`, `worker.py CANDIDATE_ROOT 19200`, and `worker.py CANDIDATE_ROOT 19200 --record`, rotating that order over seeds 19200 through 19206. Each worker verifies its imported package root and emits raw JSON. Run them sequentially, not alongside tests or documentation builds.

The captured report includes all transition cases, not just an extracted conflict core. Thus the render measurement intentionally exposes the cost of full expansion; a consumer selecting fewer source groups may render less. Capture itself makes no additional solver calls. Checking does perform additional reachability checks and its budget does not preempt Python operations. Process peak RSS is too coarse to establish a capture-only memory bound. No cross-platform performance claim is made.

The default median change ranges from -2.17% to +2.05%; capture adds +0.68% to +6.91% relative to this candidate's default path. These observations do not modify earlier performance thresholds or establish a new acceptance rule. The full recorded-text cost is substantial (up to 302.899 ms in this matrix) and is not enabled implicitly.

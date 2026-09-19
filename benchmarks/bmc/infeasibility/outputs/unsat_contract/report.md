# Generic UNSAT core contract: compatibility measurement

Baseline: `92a85f1ec4e0db20e05e341e088931a49c91ced5` (planning umbrella, same production code as its main baseline). Candidate: the source changes accompanying this report.

Environment: Linux-6.8.0-137-generic-x86_64-with-glibc2.39, Python 3.10.1.

## Protocol and gates

Frozen before measurement: 2026-09-18.
Baseline: 92a85f1 (umbrella planning head). Candidate: local feat/bmc-unsat-core-contract.
Compare the same model-load + compile + solve public API pipeline, explanation none/formal/proof.
Acceptance per case/mode median: none <= max(baseline * 1.05, baseline + 2 ms);
formal/proof <= max(baseline * 1.15, baseline + 5 ms).
Absolute tolerance prevents sub-millisecond scheduling differences dominating tiny cases.
Peak RSS <= max(baseline * 1.10, baseline + 8 MiB), measured process-wide including imports/warmup.
No increase in solver check count for explanation=none. No verdict or achieved-mode changes.
Each process warms every case once, then records one sample. Seven alternating baseline/candidate pairs.
No end-to-end CLI/startup claim; no claim for future source instrumentation or automatic reasoning.

Each process runs all 12 case/mode combinations once for warmup and once for measurement. Seven alternating baseline/candidate pairs yield seven samples per combination. Imports and interpreter startup are excluded from API timings; RSS includes them. Both versions use the same interpreter and installed dependencies. No other verification suite ran during sampling. Z3 check counting adds the same small wrapper to both versions.

Raw observations: [samples.json](samples.json). Timing is model load + query compile + public solve, including normal SAT replay. RSS is the process high-water mark, not incremental source-ledger allocation.

## Observations

| Case | Mode | Baseline median [min, max] ms | Candidate median [min, max] ms | Change | Solver calls, both | Gate |
|---|---|---:|---:|---:|---:|---|
| sat_reach | none | 45.577 [44.694, 48.003] | 45.786 [45.130, 47.934] | +0.46% | 8 | PASS |
| sat_reach | formal | 45.569 [43.864, 46.157] | 46.460 [44.369, 49.674] | +1.95% | 8 | PASS |
| sat_reach | proof | 45.759 [45.123, 48.522] | 47.040 [44.502, 47.902] | +2.80% | 8 | PASS |
| unsat_objective | none | 46.061 [44.975, 46.937] | 47.019 [44.416, 49.884] | +2.08% | 9 | PASS |
| unsat_objective | formal | 45.724 [44.637, 47.607] | 46.610 [44.774, 47.148] | +1.94% | 9 | PASS |
| unsat_objective | proof | 46.277 [45.006, 49.960] | 47.342 [45.127, 48.508] | +2.30% | 9 | PASS |
| assumption_conflict | none | 46.881 [45.410, 53.213] | 46.932 [45.041, 51.177] | +0.11% | 10 | PASS |
| assumption_conflict | formal | 80.790 [79.436, 85.294] | 81.653 [79.147, 85.348] | +1.07% | 17 | PASS |
| assumption_conflict | proof | 86.251 [83.544, 88.011] | 86.666 [83.019, 90.242] | +0.48% | 21 | PASS |
| transition_conflict | none | 46.506 [45.681, 48.732] | 47.090 [46.176, 48.155] | +1.26% | 10 | PASS |
| transition_conflict | formal | 105.196 [102.746, 106.744] | 105.998 [102.132, 110.532] | +0.76% | 28 | PASS |
| transition_conflict | proof | 577.721 [559.181, 588.523] | 573.186 [556.940, 588.959] | -0.78% | 80 | PASS |

Peak RSS median: baseline 94,208 KiB; candidate 94,640 KiB (+432 KiB, +0.46%). The RSS gate passes. Solver result, property truth and achieved explanation mode match for every corresponding observation.

These observations were collected after switching extraction to native compound formula assumptions, which avoids named activation-symbol collisions. The earlier development measurement is superseded. All local gates pass. This is a small regression check of shared-kernel extraction, not a speedup claim, a general workload survey, or a cost estimate for future provenance/refinement/reasoning. The new generic entry is explicit opt-in; its work is not added to ordinary property solves. The existing scenario explanation reuses the kernel.

## Frozen compatibility contract

- Developer entry: `pyfcstm.bmc.unsat.explain_unsat_core` with the dataclasses documented in the bilingual result reference. No implicit property interpretation or public JSON additions in this change.
- Existing `infeasibility_explanation="none"|"formal"|"proof"` API and `--infeasibility-explanation` CLI remain supported with their existing defaults.
- The later unified product option is reserved as `unsat_explanation` / `--unsat-explanation`, with `none` (default), `core`, `formal`, and `proof`. These options are **planned, not implemented here**. Existing scenario options remain compatibility aliases for their original scenario scope; contradictory simultaneous explicit requests must be rejected instead of silently overriding one another.
- `core` promises a rechecked core only; `formal`/`proof` must separately report achieved depth, checked support and closure. Future adapters must pass the actual query objective and query identity. No property verdict is inferred from UNSAT by this module.
- Public JSON must remain free of schema/product version dispatch fields. The later integrated result contract and schema are delivered together.

## Reproduction

Extract baseline package source with `git archive 92a85f1 pyfcstm | tar -x -C BASELINE_DIR`. Save the following worker as a temporary Python file, run it with the baseline directory or candidate repository as its argument. Run seven pairs, alternating which version starts. The worker warms all cases before recording one observation per combination. Linux `resource` supplies RSS in KiB for this experiment.

```python
import json
import resource
import sys
import time
sys.path.insert(0, sys.argv[1])
import z3
from pyfcstm.bmc import compile_bmc_query, solve_bmc_property
from pyfcstm.model import load_state_machine_from_text

MODEL = '''def int x = 0;
state Root { state A; state B; [*] -> A;
A -> A effect { x = x + 1; }; A -> B; }
'''
CASES = {
    'sat_reach': 'check reach <= 8: x > 3;',
    'unsat_objective': 'check invariant <= 8: x >= 0;',
    'assumption_conflict': 'assume at 1: x > 2; assume at 1: x < 1; check reach <= 8: x > 0;',
    'transition_conflict': 'assume at 1: x == 0; assume at 2: x == 99; check reach <= 8: x > 0;',
}
original = z3.Solver.check
calls = []
def check(self, *args):
    calls.append(1)
    return original(self, *args)
z3.Solver.check = check
rows = []
for warmup in (True, False):
    for name, query in CASES.items():
        for mode in ('none', 'formal', 'proof'):
            calls.clear()
            start = time.perf_counter()
            model = load_state_machine_from_text(MODEL)
            result = solve_bmc_property(compile_bmc_query(model, query), infeasibility_explanation=mode)
            elapsed = (time.perf_counter() - start) * 1000
            explanation = result.feasibility.explanation
            if not warmup:
                rows.append(dict(case=name, mode=mode, ms=elapsed, solver_calls=len(calls),
                                 status=result.status, satisfied=result.property_satisfied,
                                 achieved=explanation.achieved_mode if explanation else None))
print(json.dumps(dict(rows=rows, rss_kib=resource.getrusage(resource.RUSAGE_SELF).ru_maxrss)))
```

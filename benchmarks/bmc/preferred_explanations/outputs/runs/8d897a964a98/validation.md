# Local validation and review

Implementation: `f41fe8377aed611e4e388556344131be235e45fa`. Measured clean commit: `8d897a964a986c9421018b4c01895832d3f7a1f7` (only fixes the benchmark's expected successful reach outcome to `witness_found`; production sources are identical). The evidence-only follow-up does not change those sources. `manifest.json` records their hashes and an empty tracked production diff.

## Behavior and tests

- TDD started with 28 failing preference/CLI contracts before implementation. The final addition contains 56 cases, including independently verified alternative MUSes, final-core UNSAT and each-delete SAT, proof rebuilding/fallback, all solver profiles, actual slicing with dynamic inputs, replay fallback, external unknown/timeout injection, controlled deadlines, interrupts, defaults and schema mutations.
- Final `SKIP_SLOW_TESTS=1 make unittest WORKERS=4`: **51,261 passed, 1,010 skipped**, 584.11 s. This is the repository's normal lightweight full suite, not every optional native/template/platform suite.
- Final `make doctest`: **1,122 passed**, 17.90 s.
- Targeted coverage run: **351 passed**. Changed production statements: **73/73**. Branch arcs originating on changed production lines: **48/48**. No new coverage exclusions. The denominator is the production diff against the umbrella baseline, not the whole repository, tests, or benchmark tools.

Reproduce the coverage audit from the repository root:

```bash
COVERAGE_FILE=/tmp/preferred-final.coverage pytest \
  test/bmc/test_preferred_explanations.py \
  test/bmc/test_response_trigger_diagnostics.py \
  test/bmc/test_infeasibility.py \
  test/bmc/test_feasibility_explanation_wiring.py \
  test/entry/test_bmc.py -q \
  --cov=pyfcstm.bmc.infeasibility --cov=pyfcstm.bmc.witness \
  --cov=pyfcstm.entry.bmc --cov-branch \
  --cov-report=json:/tmp/preferred-final-coverage.json
python benchmarks/bmc/preferred_explanations/outputs/runs/8d897a964a98/audit_coverage.py
```

`diff-coverage.json` records source hashes, executed changed lines/arcs and empty missing lists. The audit asserts both missing lists are empty.

## Documentation and gates

- `make rst_auto`, touched-file Ruff, `make test_boundary_check`, `make resource_ownership_check`, and `git diff --check` passed.
- English and Chinese HTML built in separate initially fresh `/tmp/preferred-html-en` and `/tmp/preferred-html-zh` roots with `NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=<language> sphinx-build -b html docs/source <root>`. English was rebuilt after fixing new heading lengths.
- `python tools/check_bmc_docs.py --check --html-root-en /tmp/preferred-html-en --html-root-zh /tmp/preferred-html-zh` passed. All six affected how-to/reference HTML pages expose both new options and contain no problematic nodes.
- `python -m pyfcstm bmc --help` matches the new flags and defaults. Public CLI tests cover expected core IDs, exit status, JSON and human output, and invalid combinations.
- The global `check_cli_reference_docs.py --check` still reports **22 pre-existing mismatches** for expand-svg, diagram and inspect. Running the same checker against an archive of the umbrella baseline produces an identical diagnostic list after normalizing root paths. There are no new BMC mismatches. These unrelated entries were left unchanged.
- HTML has existing unrelated warnings (missing simulator demo outputs, duplicate/cross references and existing generated catalog headings). New content has no remaining warning. No new equations, diagrams or generated demo resources were introduced, so `make contents` is not applicable to these prose-only additions; intentional API RST generation is included.
- Bilingual depth review: concrete model/query/command, actual scenario-infeasible exit 3, final core, proof success/fallback, invalid combinations, fixed preference ordering, scope, optional metadata, source-group minimality and deadline limitations are covered. Existing tutorial and navigation remain intact. This is an agent's local review, not a substitute for maintainer review.

## Measurement checks and interpretation

The official run used no parallel test jobs, coverage instrumentation or timed check observer. All **195 records** were verified: 150 measured samples (30 case/surface/arm groups with five each), 30 discarded warmups and 15 separate check-count observations. Baseline/current source hashes matched; the current production diff was empty. Rebuilding `report.md` from raw data was byte-identical. The runner refuses an existing output directory. Earlier exploratory or failed runner-development attempts are not mixed into this run.

- Default-off API/CLI medians differ from the baseline by approximately **-1.2% to +0.7%** across these five synthetic cases. This is not a universal zero-overhead guarantee.
- Short multi-conflict query: ordinary API 48.832 ms, preferred 62.795 ms; checks 13 -> 23. The selected initialization member changes from `initial.variable.y` to query-authored `initial.where`.
- Long multi-conflict query: ordinary API 606.446 ms, preferred 1787.071 ms; CLI 1532.164 -> 2717.793 ms; checks 13 -> 219. Full-scope deletion has a substantial cost.
- Single conflict: same two assumptions, checks 10 -> 11, API 196.049 -> 230.851 ms. There is no selection benefit to claim here.
- Feasible query: one check for every arm, preference not applicable.
- 5 ms feedback budget: main scenario-infeasible verdict survives; preference reports timeout and no core. Reported explanation time is about 109 ms because Python setup can overrun a probe/phase deadline. Early stopping avoids constructing later phases after exhaustion, but this remains a **soft budget**, not hard realtime. A shorter overall run here is abandoned optional work, not equal-quality acceleration.

## Local source review

Reviewed the public solve/CLI flow and its default branch, full-scope provenance, unchanged classification, UNSAT-only deletion invariant, independent final validation, selected-core proof binding, generic solver boundary, main/feedback deadline capping, default payload omission, actual slicing/fallback, dynamic inputs and exception propagation. No unresolved issue was found on those normal paths that blocks maintainer review. Limitations above are intentional and visible.

Push/PR publication does not claim CI success or merge readiness. Per maintainer instruction, CI is not watched after push; human review and a request to inspect CI come next.

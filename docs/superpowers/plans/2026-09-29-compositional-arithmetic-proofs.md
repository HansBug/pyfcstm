# Compositional Arithmetic Proofs Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement task by task.

**Goal:** Reconstruct related arithmetic proofs through shared semantics and
parameterized exact evidence, using Z3 as the only backend.

**Architecture:** Semantic facts enter the existing polynomial evidence DAG.
Search and offline replay remain separate; rendering consumes checked evidence.

**Tech Stack:** Python standard library, existing z3-solver and pytest.

**Spec:** ../specs/2026-09-29-compositional-arithmetic-proofs.md

## Global Constraints

Python 3.7–3.14; Windows, Linux, macOS; no new runtime dependencies; current
repository only. Preserve exact domains, source provenance, scopes and budgets.
Long output tests use text_aligner. No silently accepted unsupported inference.

## Review Focus

- Zero/negative bases and exponents must not acquire invalid positivity facts.
- Uninterpreted functions with familiar names must not acquire builtin semantics.
- Facts from another native node or sibling scope must not leak into a proof.
- Equivalent expressions and nested roots must compose without case-specific rules.
- High degrees/shared expressions must respect limits without false completeness.

## Semantic evidence

Files: core.py, polynomial.py, new semantics.py, io.py, text.py, __init__.py;
test/solver/proof/test_semantics.py and test_loading.py.

- [x] Write failing public expression families for rational-power sign and
  positive-base variable-power positivity, including SAT boundary controls.
- [x] Introduce add_semantic_facts(search) and check_semantic_step(step, graph,
  normalizer, facts), using existing polynomial helpers and indexed premises.
- [x] Extend portable PolynomialStep evidence only with the fields required to
  identify semantic operations; validate and render those fields.
- [x] Make the family tests pass, add negative replay tests and full-text goldens.

## Algebraic composition

Files: polynomial.py, semantics.py, test_polynomial.py, test_semantics.py.

- [x] Write red families for odd degrees 3/5/7/9 and root identities/compositions,
  with expanded/factored/renamed/nested variants and satisfiable perturbations.
- [x] Replace cubic-only candidate generation with parameterized exact identities.
- [x] Share semantic and algebraic facts in a budgeted deduction loop, retaining
  only changed/relevant candidates and final proof dependencies.
- [x] Validate every generated step independently; confirm mutations are rejected.

## Real consumers and verification

Files: test/bmc/test_solver_proof_coverage.py, proof_readings, proof documentation.

- [x] Exercise compound FCSTM guards and FBMCQ objectives through real BMC cores,
  including multiple frames, transitions and query-only contradictions.
- [x] Run pytest test/solver/proof test/bmc/test_solver_proof_coverage.py with
  branch coverage; require no missing changed-code branches.
- [x] Run make unittest RANGE_DIR=./solver/proof, full lightweight repository
  tests, boundary/resource gates, generated API docs and bilingual docs builds.
- [x] Obtain independent public-surface review and resolve findings with TDD.
- [x] Commit/push, publish a new PR comment with actual complete proof text,
  inspect current-head CI and perform requirement-by-requirement completion audit.

## Verified handoff

The implementation and portability tests at
[08c598aa](https://github.com/HansBug/pyfcstm/commit/08c598aad3a8c1d8169655e23ae4ba158c40324d)
passed the [Code Test workflow](https://github.com/HansBug/pyfcstm/actions/runs/36596873387)
and [Docs Check workflow](https://github.com/HansBug/pyfcstm/actions/runs/36596879721).
All 23 platform/Python unit-test combinations passed, including the previously
failing macOS/Python 3.14 full-text regression. The aggregate gate passed.

- The proof module plus real BMC consumers: 757 passed; 3127 statements and
  1702 branches covered, with no missing lines or branches.
- The requested proof-directory make entry: 729 passed.
- The full lightweight repository regression: 52003 passed, 1010 skipped.
- Bilingual documentation, test-boundary, resource-ownership and API toctree
  checks passed. Documentation builds retained 19 existing warnings each.
- Native proof generation remains live in integration tests. Fixed captured
  reports independently replay their polynomial evidence and compare complete
  bilingual text with text_aligner; rendering cannot start a new solver.
- No runtime dependency or backend was added. Scope, domains, exact arithmetic,
  replay rejection and selected-evidence pruning retain dedicated tests.
- The [new capability comment](https://github.com/HansBug/pyfcstm/pull/505#issuecomment-5893630812)
  contains executable public API usage, complete generated proof text, actual
  BMC input, verification results and explicit completeness/minimality limits.

This handoff records the tested implementation; it does not broaden the stated
arithmetic completeness boundary or migrate the old BMC explanation API.
The pull request is left open for the maintainer to merge.

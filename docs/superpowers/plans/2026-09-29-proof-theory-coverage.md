# Generated Formula Proof Coverage Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline. The user has
> authorized execution in the current repository, without a worktree.

**Goal:** Explain native UNSAT proofs for the formulas our encoders generate.
**Architecture:** Extend existing portable evidence analysis and deterministic
reading, adding checked theory deductions where the native certificate is too
coarse. Keep the original graph, scope and source identities intact.
**Tech Stack:** Existing Z3, Python standard library, pytest, text_aligner.
**Spec:** ../specs/2026-09-29-proof-theory-coverage.md

## Global Constraints

- Python 3.7–3.14, Windows/Linux/macOS, no new runtime dependencies.
- TDD, full long-text assertions and 100% changed production branch coverage.
- No blanket theory trust, full-query circular reconstruction or schema versions.
- Current checkout; preserve unrelated .omx files. BMC contract unchanged.

## Review Focus

- False axiom or disconnected equality evidence must never become checked.
- PB literals can be negated, weighted or share Boolean subexpressions.
- Division/modulo semantics differ with operand signs and numeric sorts.
- Nonlinear lemmas may lack enough native parameters; missing derivations cannot
  be concealed by generic titles or solver-only rechecks.
- Reconstructed evidence cannot leak branch hypotheses or lose offline identity.

## Task 1: Native logical rules

**Files:** solver/proof/rules.py; test/solver/test_proof_rules.py.
**Interfaces:** existing analyze_proof(ProofGraph), ProofNode local_check/kind.
- [x] Write public analyzer regressions for true-axiom and trans*; reject false
  axioms, incompatible relations and disconnected endpoint chains.
- [x] Run focused tests and observe unsupported-rule failures.
- [x] Check literal truth and relation-edge connectivity with scope unchanged.
- [x] Run solver suite; capture real integer-division proofs exercising rules.

## Task 2: Generated formula inventory and theory evidence

**Files:** test/solver/test_proof_theories.py; test/bmc/test_solver_proof_coverage.py;
solver/proof/{core,rules,text,io,interval}.py.
**Interfaces:** explain_unsat remains the entry point; portable certificates
supply exact facts/derivations to analyze_proof and ProofReading.to_text.
- [x] Add real encoder and native proof surveys for every supported operation
  family and actual theory parameters, including compositions and boundaries.
- [x] Write failing complete-reading and independently expected evidence tests
  for PB cardinality, triangle equality, integer bounds/division/modulo and casts.
- [x] Implement each checked deduction with RED/GREEN cycles, offline roundtrips
  and full EN/ZH text_aligner outputs. Respect all external premises and scopes.
- [x] Add negative public-evidence tests rejecting invalid certificates.

## Task 3: Nonlinear deductions and local reconstruction

**Files:** theory evidence files from Task 2; test/solver/test_proof_theories.py.
**Interfaces:** theory deductions are part of the same graph/reading; preserve
exact original native nodes and distinguish reconstructed derivations.
- [x] Survey real multiplication, powers/root and rounding proof paths and write
  failing tests for the previously partial integer square and mixed cases.
- [x] Implement algebraic/interval/integer case deductions supported by evidence.
- [x] If native hints require local reconstruction, test its premise boundary,
  termination/budget and explicit failure before implementing it.
- [x] Run generated-formula combinations and verify complete evidence or genuine
  solver/resource limitations; do not redefine missing interpretation as support.

## Task 4: Release evidence and documentation

**Files:** test owners above; bilingual proof docs and executable demo.
**Interfaces:** exact code-to-output paired examples; current public contracts.
- [x] Measure branch coverage, add behavioral regressions for remaining arcs.
- [ ] Update bilingual documentation and runnable examples with actual outputs.
- [ ] Run full unittest, rst_auto, doctest, relevant boundary/resource, docs and
  package gates. Review generated artifacts and complete proof outputs.
- [x] One fresh whole-change review, fixes through RED/GREEN, rerun affected gates.
- [ ] Push to existing PR, publish a new full-output comment, follow applicable
  CI to success and audit main base, head, clean status and mergeability.

## Proof package boundary

Keep all proof-specific implementation under `pyfcstm.solver.proof`, including native capture. Export public evidence and extension interfaces through its `__init__.py`; consumers must import from this package. Shared budgets, symbols and UNSAT query/core utilities remain in the parent solver package. Preserve offline loading without Z3.

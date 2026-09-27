# Generic UNSAT Proof Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan
> inline. Steps use checkbox syntax. The user explicitly authorized execution,
> testing, a main-based PR and an example comment.

**Goal:** Deliver standalone native UNSAT proofs with readable, source-linked,
expandable deductions and extensibility, with full changed-branch coverage.

**Architecture:** Named constraints enter an isolated Z3 proof context. A typed
evidence DAG and scope/rule analysis feed a deterministic reading layer; explicit
source and fold adapters let BMC or other callers add domain meaning.

**Tech Stack:** Python standard library, existing z3-solver, pytest and coverage.

**Spec:** ../specs/2026-09-27-unsat-proof-design.md

## Global Constraints

- Python 3.7–3.14; Windows/Linux/macOS; no new runtime dependency.
- Full original inputs first; background retained; minimization optional.
- Plain data evidence, no product/schema dispatch fields, honest partial states.
- All changed production code: 100% executable line and branch coverage.
- Public-path tests only; RED before implementation; no coverage exclusions.
- Existing BMC contract remains intact until its subsequent integration.
- Commit only after applicable make unittest, rst_auto and doctest gates.

## Review Focus

- Duplicate equal ASTs must not silently select one necessary source (Task 1/2).
- A local hypothesis must never escape a discharged branch (Task 3).
- Folded claims must retain external premises and scope (Task 4).
- UNKNOWN during deletion cannot establish minimality (Task 5).
- Offline exports must validate references without importing Z3 (Task 2/6).

## Task 1: Exact inputs, symbols and shared budget

**Files:** `pyfcstm/solver/unsat.py`, `symbols.py`, `budget.py`;
`test/solver/test_unsat.py`, `test_symbols.py`, `test_budget.py`.

**Interfaces:** Produce UnsatConstraint, UnsatQuery, SymbolNames, SolveBudget and
checked `explain_unsat_core`; keep BMC dependencies out of these modules.

- [ ] Write tests for grouped constraints, background-only contradiction, empty
  SAT query, duplicates, bad IDs/sorts/contexts, symbol collision and timeout.
- [ ] Run `pytest test/solver/test_unsat.py -q`; observe missing API failure.
- [ ] Port the existing generic input/core algorithms and naming behavior from
  the construction branch, adapting only the required standalone contract.
- [ ] Run new tests and `pytest test/solver -q`; require green before proceeding.

## Task 2: Native evidence and portable data

**Files:** `pyfcstm/solver/proof.py`, `_z3_proof.py`;
`test/solver/test_proof.py`.

**Interfaces:** Produce ProofGraph, ProofNode, shared typed terms and input
bindings; exact translated query yields captured native proof or SAT/UNKNOWN.

- [ ] Write public tests: the linear example has False root and exact input
  bindings, duplicate origins remain, nested expressions share terms, native
  parameters survive, SAT has no proof, output is JSON serializable.
- [ ] Run tests and observe missing capture/graph behavior.
- [ ] Implement isolated translation, native DAG import and pure data contracts.
- [ ] Run tests; inspect real linear and ITE native output against input records.

## Task 3: Scope and inference analysis

**Files:** `pyfcstm/solver/proof_rules.py`, `proof.py`, `_z3_proof.py`;
`test/solver/test_proof_rules.py`.

**Interfaces:** Produce ProofRuleHandler and RuleAnalysis, scope/check states and
exact arithmetic certificates; consume Task 2 terms/nodes.

- [ ] Write tests for branch discharge, shared hypotheses, definitions,
  equality/substitution, strict rational arithmetic, integer inequalities,
  unsupported theory/binder status and conflicting extension handlers.
- [ ] Run and observe absent analysis failures.
- [ ] Implement rule analysis from native parameters and explicit scopes.
- [ ] Run public tests with real Z3 and verify every accepted root is closed.

## Task 4: Readable deductions and checked domain folds

**Files:** `pyfcstm/solver/proof_text.py`, `proof.py`;
`test/solver/test_proof_reading.py`.

**Interfaces:** Produce SourceDescription/SourceAdapter, SourceLink,
ProofExtensions, ReadingFolder/FoldProposal, ProofReading and ReadingBlock.

- [ ] Write tests requiring complete EN/ZH linear and ITE deductions, premise
  references, expandable arithmetic, sources, missing-source status, an actual
  application adapter, a valid fold and rejection of a missing premise/changed
  conclusion/escaping hypothesis; unknown IDs raise documented errors.
- [ ] Run and observe missing reader behavior.
- [ ] Implement deterministic rendering and evidence-preserving fold checks.
- [ ] Run tests and manually read the complete real example outputs.

## Task 5: Orchestration and optional minimization

**Files:** `pyfcstm/solver/proof.py`, `_z3_proof.py`, `unsat.py`;
`test/solver/test_proof.py`, `test_unsat.py`.

**Interfaces:** `explain_unsat(query, *, mode='proof', minimize=False,
timeout_ms=None, names=None, extensions=None) -> UnsatReport`.

- [ ] Write tests for full-first proof, unique three-group minimal example,
  background preservation, shared deadline, exhausted/UNKNOWN deletion, no
  cross-execution evidence mixing, core mode and invalid option combinations.
- [ ] Observe failures, implement using the same core engine/shared budget.
- [ ] Run tests and compare full/reduced queries independently with real Z3.

## Task 6: Public exports, offline reading and documentation

**Files:** `pyfcstm/solver/__init__.py`, public module docstrings, generated
`docs/source/api_doc/solver/`, solver user guide and executable examples;
`test/solver/test_proof_reading.py`, public-import tests.

**Interfaces:** Lazy package exports, canonical roundtrip/loader and documented
calling examples; source/reading extensions require no BMC imports.

- [ ] Write roundtrip tests for valid reports and malformed IDs/references,
  duplicate graph identities, cycles, enum values and unavailable results.
- [ ] Observe RED, implement checked offline reconstruction and lazy exports.
- [ ] Read documentation_authoring.md; add bilingual use/reference material with
  actual outputs and explicit unsupported-rule/minimization boundaries.
- [ ] Run the examples, API generation, doctests and affected doc builds.

## Task 7: Coverage, regression and fresh review

**Files:** tests owning uncovered behavior; only necessary implementation fixes.

- [ ] Run coverage with branches and inspect every missing changed line/arc.
- [ ] Add public behavior tests first for each reachable gap; simplify genuinely
  unreachable guards rather than forging state or excluding coverage.
- [ ] Require 100% coverage on new modules and changed branches in existing code.
- [ ] Run `SKIP_SLOW_TESTS=1 make unittest`, `make rst_auto`, `make doctest`,
  boundary/resource checks as applicable and package import smoke checks.
- [ ] Commit reviewed increments; dispatch one fresh whole-branch reviewer,
  address findings via RED/GREEN, rerun all affected/full gates.

## Task 8: Pull request and real capability comment

**Files:** PR body and new comment, generated demo outputs as appropriate.

- [ ] Verify GitHub identity; push feature branch and create PR against main with
  `kind: feature` and `area: verification` labels.
- [ ] Post a new comment with executable linear, branch, minimization and source
  extension examples, their real complete text output and known limits.
- [ ] Follow all required CI/review checks on the exact head; fix failures.
- [ ] Revalidate base/head, clean diff, coverage, comments, non-draft status and
  mergeability. Report ready only after the completion evidence supports it.

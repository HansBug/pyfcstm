# Proof Merge Acceptance Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Preserve existing uncommitted implementation work; do not create a worktree.

**Goal:** Close the remaining proof usability, budget, diagnostic and acceptance gaps before declaring the solver proof module ready to merge.

**Architecture:** Keep capture, analysis, checked certificates and reading as separate stages of the existing implementation. Preserve evidence monotonically under interruption, prioritize requested core reduction, and derive compact views from the existing proof DAG without changing logical claims.

**Tech Stack:** Python 3.7–3.14, existing z3-solver, Fraction, pytest and text_aligner; no new runtime dependency.

**Spec:** ../specs/2026-09-30-arithmetic-proof-reliability.md

## Global Constraints

- Work in the current repository; preserve unrelated untracked artifacts.
- Support Windows, mainstream Linux and macOS within the existing dependency envelope.
- No compatibility shim, alternative proof framework or new backend.
- Never conflate readable completeness, local certificate checking, trusted native rules or source completeness.
- Long expected text uses text_aligner; single-line contracts use equality.
- A stopped search cannot establish minimality, validity or completion.
- Each repair follows failing regression, shared implementation fix, negative controls, verification, then a focused commit.

## Current evidence

At local HEAD 0f4635ac, the previous recorded subsystem run passed 843 tests
with 100% statement/branch coverage of proof modules. This is historical evidence,
not verification of the current working tree or the whole repository.

The current working tree modifies text.py, test_detail.py and four text fixtures.
A fresh `pytest test/solver/proof/test_detail.py -q` reports 33 passed, 1 failed:
the 50-link standard reading is 129129 bytes, above its 98304-byte regression target.
Recorded 250-link readings are 1796367 bytes brief and 2528441 bytes standard.

A fresh public 250-link experiment with minimize=True and timeout_ms=5000 returned:
core mode: UNSAT, a retained core, minimality not_proven (acceptance timed out);
proof mode: UNSAT, proof unavailable, no core (capture exhausted the budget).
This demonstrates a scheduling limitation, not incorrect minimality reporting.

Source inspection confirms analysis accumulates annotations locally and returns
only at the end. _assemble catches BudgetExpired without those annotations.
Generic invalid_inference records a gap but emits no warning; polynomial replay
failure already has its own warning.

## Review Focus

- Interruption after useful analysis must retain completed checks without treating pending scope work as passed (Task 1).
- Fixed background, duplicate inputs and incomplete deletion checks must not yield false necessity claims (Task 2).
- Folded conditional reasoning must retain local assumptions, discharge boundaries, source links and gaps (Task 3).
- Malformed portable certificates and plugin claims must not become independently checked evidence (Task 4).
- Equivalent formulas and actual multi-frame BMC encodings must preserve supported behavior; native unknown remains explicit (Task 5).

## Task 1: Preserve analysis progress and centralize invalid-evidence diagnostics

Files: pyfcstm/solver/proof/{core,rules,io,text}.py;
test/solver/proof/test_{core,rules,loading,detail}.py.

Interfaces: retain explain_unsat and analyze_proof signatures. Extend ProofAnalysis
with an optional stop_reason; keep completed annotated nodes and untouched nodes
in the same graph. Untouched nodes retain local_check='not_run'. Scope/rule checks
remain partial unless a failure has already been established. The public report
retains UNSAT, captured evidence and the exact stop stage.

- [ ] Add a regression interrupting analysis after a checked prefix; assert its certificates survive, unchecked suffix stays not_run, and root scope is not passed.
- [ ] Run it and record failure before changing the implementation.
- [ ] Catch BudgetExpired at the analysis ownership boundary, return accumulated annotations and explicit unfinished diagnostics, and propagate stop_reason through _assemble. Do not spend an expired budget rebuilding a full reading.
- [ ] Emit RuntimeWarning for invalid internal/native evidence with node, rule and reason; retain structured gaps. Expected unsupported rules and budget exhaustion remain ordinary partial outcomes. Avoid duplicate warnings for the same mismatch.
- [ ] Add canonical roundtrip, partial text fixtures and a public rule-handler invalid-result warning regression; run the four named test modules and commit.

## Task 2: Prioritize requested minimization

Files: pyfcstm/solver/proof/core.py; pyfcstm/solver/unsat.py only if core scheduling requires it;
test/solver/proof/test_core.py and existing core tests.

Interfaces: keep explain_unsat(..., minimize=True, timeout_ms=...) and CoreEvidence.
Run core extraction/reduction first when minimization is explicitly requested;
reprove the accepted subset using the remaining shared budget. full_proof is
optional and must not require a full original proof before reduction can start.
Update its docstring and all consumers rather than pretending it is always present.

- [ ] Add a deterministic stage-order regression and a public budget-limited large-query regression; assert core progress survives even when reproof cannot finish.
- [ ] Observe failure with the current capture-before-minimization order.
- [ ] Reorder orchestration, preserving core_check, subset_minimality, stop_reason and fixed background. Never reset the total deadline for reproof.
- [ ] Cover background-only UNSAT, duplicate/equivalent groups, irrelevant large groups, unknown deletion checks and timeout during final acceptance/reproof.
- [ ] Assert only completed deletion acceptance yields subset_minimality='proven'; document that this is group-level subset minimality, not minimum cardinality or shortest derivation.
- [ ] Run core/proof integration tests, update canonical/text expectations and commit.

## Task 3: Finish useful brief and standard readings

Files: pyfcstm/solver/proof/text.py; test/solver/proof/test_detail.py;
test/solver/proof/proof_readings/; bilingual proof reference pages.

Interfaces: preserve to_text(language, detail), expand(block_id), get_term_text.
Brief is a dependency-linked guide; standard is a compact derivation; detailed
retains evidence detail. Display aliases must resolve to durable original IDs.

- [ ] Retain the failing size regression and the passing scoped-fold/index-rebuild regressions. Review the uncommitted _References experiment; remove it if its complexity does not materially address repeated dependency sets.
- [ ] Keep the single-pass batched folding improvement. Build brief from semantic steps, inputs and contradiction with explicit references to omitted derivations; expose every gap and preserve scope qualification.
- [ ] For standard, share repeated expressions/dependency sets structurally; avoid expanding the same transitive dependency list per block. Every shared reference must have a definition and a documented route back to evidence.
- [ ] Verify 50/100/250 conditional chains; target <=64 KiB brief and <=512 KiB standard at 250 links, without truncating claims or hiding gaps. These are workload usability targets, not universal bounds for arbitrary proofs.
- [ ] Full-text compare both languages on fixed portable graphs; assert canonical evidence is unchanged, references resolve, and assumption/discharge/source information is preserved.
- [ ] Run test_detail.py and related reading tests, record separate capture/analysis/render timings, then commit.

## Task 4: Audit the common evidence boundary

Files: pyfcstm/solver/proof/{io,rules,integer,interval,polynomial,semantics}.py;
test/solver/proof/test_{loading,integer,intervals,polynomial,semantics}.py.

Interfaces: retain existing typed certificate families and canonical loader.
Reuse existing validation/replay; add no generic checker framework.

- [ ] Enumerate each producer, independent checker, serialized fields and scope inputs; inspect each consumer before changing shared normalization.
- [ ] Exercise public canonical loading with changed coefficients, duplicate keys, wrong sorts, missing premises, altered endpoints, wrong conclusions and sibling-scope references.
- [ ] For confirmed acceptance bugs, record RED then fix at the shared validator/checker boundary and run all affected certificate families. Do not report private-only malformed helper calls as public defects.
- [ ] Verify trusted native rules and extension claims remain visibly distinct from checked certificates; reading_status='complete' must not imply a standalone proof kernel.
- [ ] Run the named suites and commit only confirmed fixes; report a clean audit if no additional reachable defect is found.

## Task 5: Validate the BMC operation surface and native limits

Files: test/bmc/test_solver_proof_coverage.py; test/solver/proof/test_theories.py;
existing proof reference documentation. Production changes only for reproduced gaps.

- [ ] Map actual BMC/FBMCQ construction sites to operators, native obligations, producers/checkers and tests; include implication/ITE, frame/state equalities, event cardinality, priority/history, arithmetic casts, division/remainder and nonlinear/root conditions emitted by the current implementation.
- [ ] Cover actual FCSTM+FBMCQ contradictions, FBMCQ-only contradictions, constant/derived true and false guards, multi-frame effects, dead branches, aliases and unrelated conditions. Include SAT perturbations.
- [ ] Vary assertion order, names, factored/expanded forms and cast placement. Preserve full generated outputs using fixed portable evidence where native layouts vary by platform.
- [ ] Recheck parity-product and algebraic unknown cases against identical ordinary/proof-mode native queries; record native solve separately from capture and analysis.
- [ ] Use proof-preserving preprocessing only with demonstrated benefit and original-input mapping. Any added arithmetic lemma needs an exact certificate and original dependencies; otherwise retain explicit native unknown/timeout.
- [ ] Produce a coverage mapping with supported families and residual native/search limits. Finite tests do not establish completeness of arbitrary nonlinear arithmetic.

## Task 6: Acceptance and publication

- [ ] Run `pytest test/solver/proof test/bmc/test_solver_proof_coverage.py` with branch coverage; require all tests green and 100% changed-proof coverage.
- [ ] Run `make unittest RANGE_DIR=./solver/proof WORKERS=4` and `SKIP_SLOW_TESTS=1 make unittest WORKERS=8`.
- [ ] Run `make test_boundary_check resource_ownership_check`, `python tools/check_api_doc_toctree.py --check --self-check`, `make docs_en docs_zh`, and `git diff --check`.
- [ ] Review every public source mapping and text/API claim against evidence; obtain final independent review and resolve public-reachable findings with regressions.
- [ ] Under the existing publication authorization, push the reviewed commits, inspect CI for that exact head, then add the requested PR comment with runnable input, full generated readable text, measurements and limits.
- [ ] Declare readiness only after the code, current tests, documentation and exact-head CI agree. Retain explicit limits rather than claiming universal proof support.

## Execution order and stopping rules

Tasks 1 and 2 establish reliable reports under finite budgets; Task 3 establishes
useful output; Task 4 checks evidence integrity; Task 5 closes the actual BMC
surface; Task 6 gates merge readiness. Preserve the current rendering experiments
until Task 3 resolves or removes them; do not publish an intermediate failing tree.
Each task ends with a focused verified commit. An unexpected native limitation
must be classified before deciding whether any production change is justified.

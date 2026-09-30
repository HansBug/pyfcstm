# Arithmetic Proof Reliability Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task-by-task. Checkboxes denote implementation work that has not started.

**Goal:** Fix arithmetic evidence failures by shared semantics and improve proof usability without another backend.

**Architecture:** Preserve the existing capture/evidence/replay/reading pipeline. Make numeric and integer semantics reusable, extend the existing integer and polynomial certificate producers, and keep candidate search separate from accepted proof evidence. Optimize capture and rendering only after stage-specific profiling.

**Tech Stack:** Python 3.7-3.14, standard-library Fraction, existing z3-solver and pytest.

**Spec:** ../specs/2026-09-30-arithmetic-proof-reliability.md

## Global Constraints

- Current repository only; no worktree, no new backend or runtime dependency.
- Windows, Linux, macOS and Python 3.7-3.14 remain supported.
- No silent domain strengthening, unchecked derived premises, or source metadata as evidence.
- Preserve local scopes, exact query meaning and one shared cooperative deadline.
- No backwards-compatibility layer is required, but changed portable evidence must have matching IO, replay, text and documentation.
- All durable fixtures belong under test/solver/proof or test/bmc; long text uses text_aligner.
- This document is a repair proposal. Production code has not been changed for it.

## Review Focus

- Display precision/options must not alter numeric evidence, including negative and nonterminating rationals.
- Real casts of integer expressions retain a lattice; genuine reals and uninterpreted functions do not acquire one.
- Permuted native clauses, duplicate premises and BMC frame aliases must not change soundness or cause false-invalid results.
- Square templates taken from other terms are candidates only; conditional semantic facts never cross scopes.
- Timeout/minimization/compact output must preserve explicit gaps and necessary input/source dependencies.

## Exact numeric capture

Files: pyfcstm/solver/proof/_z3_proof.py; test/solver/proof/test_core.py and test_theories.py.

Interface: retain capture_proof(query, budget, names, source_adapter). Add a private
_exact_rational_text(value) -> str used only for native Int/Real rational numerals.
Use as_long / numerator_as_long / denominator_as_long; never str(numeral) or a float.
Audit declaration parameters and algebraic sexprs separately; do not replace exact
root-object evidence with decimal approximations.

- [ ] Write subprocess-isolated public API tests for decimal display on/off,
  precisions 2/10/30, negative rationals, large integers and algebraic literals.
- [ ] Observe RED for x>=1/3 and x<=1/4 under decimal display.
- [ ] Implement exact extraction without changing global Z3 options.
- [ ] Verify identical semantic numeric fields and complete readings; add a full
  text_aligner case and canonical roundtrip, then commit this focused repair.

## Integer-valued arithmetic normalization

Files: new pyfcstm/solver/proof/arithmetic.py; rules.py, interval.py,
polynomial.py, integer.py; test_rules.py, test_intervals.py, test_semantics.py.

Interface: integer_lattice(term_id, graph) -> Optional[Tuple[Fraction, Fraction]]
returns offset and nonnegative step such that the value lies in offset+step*Z;
None means unproved, step 0 is an exact constant. It is internal to proof.
Use exact closure for Int terms, rational constants, to_real, addition/subtraction
and rational scaling. Unknown operators/real functions return None. Cache per graph,
not globally. Strengthen a bound only by this proved lattice and exact rounding.
Use the helper consistently in native Farkas, integer, interval and polynomial
normalization; replay must recompute the same semantic property independently.

- [ ] Write public floor/ceil failure families with casts, signs, rational
  thresholds, nested arithmetic, frame aliases and genuine-real SAT controls.
- [ ] Observe the valid floor/ceil reports becoming invalid before the repair.
- [ ] Implement shared lattice analysis and exact strict/nonstrict bound rounding.
- [ ] Verify the original native weights after normalization. Do not relabel a
  failed certificate trusted; preserve explicit invalid evidence diagnostics.
- [ ] Add bilingual full-text and mutation tests; run all existing arithmetic
  certificate suites and commit.

## Integer range and congruence evidence

Files: integer.py, core.py, rules.py, io.py, text.py; test_integer.py,
test_loading.py; test/bmc/test_solver_proof_coverage.py.

Interfaces: retain divisibility_certificate(node, graph, budget) and independent
replay. Extend its evidence to cover an integer expression constrained to an
interval containing no admissible residue, rather than requiring every bound to
have an exact opposite. Record the contributing local bounds, exact rational
combination weights, integer-valued expression, residue/modulus and interval.
The checker must derive both interval endpoints and integrality/congruence from
those premises; a producer's claimed range or residue is not trusted.

Algorithm: retain the cheap equality-pair path; then combine established equalities
and integer bounds with the native coefficient proposal. Compute exact gcd/residue
and lattice-rounded endpoints, and check that the feasible interval contains no
value of that residue. Nonlinear Int terms can be integer atoms for this check;
using product values or factor properties requires separate polynomial evidence.
Candidate search may use existing Z3 rational coefficient models, not a native
UNSAT answer as a certificate. The arith/gcd-test label must not prevent other
checked arithmetic producers from solving the same local obligation.

- [ ] Add failing real-BMC mod-3 and product-equals-7 regressions, direct prime-11,
  negative modulus, modulo sums and affine variants; include SAT perturbations.
- [ ] Capture actual local obligations as fixtures and observe RED.
- [ ] Extend generation and offline replay together; add typed portable fields
  only for evidence the checker consumes. Update IO/text in the same commit.
- [ ] Reject changed weights, omitted premises, bad residue/modulus, strictness,
  nonintegral atoms and sibling-scope evidence.
- [ ] Verify no unsupported gcd obligations in the specified families, then commit.

## Composite-square reconstruction and layout robustness

Files: polynomial.py, semantics.py, rules.py; test_polynomial.py,
test_semantics.py and test/bmc/test_solver_proof_coverage.py.

Interfaces: retain polynomial_certificate and check_polynomial_certificate.
Reuse existing square/product/sum/equality_product steps for new witnesses.
Add private square_candidates(node, graph, normalizer, budget), yielding exact
sparse factors. Candidate discovery may inspect original expression structure,
but only unconditional square identities are imported from outside local terms.
Domain-dependent sign/power facts still need local premises.

Algorithm: include bases of explicit even powers/repeated products, composite
monomial differences and rational affine factors. For degree-two polynomials,
try exact rational symmetric-matrix LDL decomposition; accept only decompositions
whose nonnegative weighted squares replay to the exact polynomial. For higher
degrees use a bounded monomial basis suggested by actual terms; do not claim a
complete SOS algorithm. Deduplicate candidates and materialize only witness-used
steps. Preserve shared equality, sign and integer-bound evidence with explicit
premise provenance rather than flattening away semantic links.

- [ ] Add RED affine/product square sums and the quartic BMC case; run direct and
  BMC embeddings, expanded/factored forms, reordered terms and frame aliases.
- [ ] Implement candidates and exact decomposition using Fraction and existing
  algebra helpers; no new numeric or SDP backend.
- [ ] Verify every returned certificate independently; add negative coefficient,
  wrong factor/domain and non-PSD controls.
- [ ] Require complete readings for the listed families under unchanged generous
  budgets; preserve explicit limits for larger unsupported searches, then commit.

## Native timeout and checked preprocessing experiment

Files: test/bmc/test_solver_proof_coverage.py; _z3_proof.py, integer.py and rules.py
only if an exact checked preprocessing benefit is demonstrated.

- [ ] Preserve the parity-product case and compare identical assertions under
  ordinary solving, proof arithmetic 2 and proof arithmetic 6. Measure phases.
- [ ] Test general divisibility multiplication/addition consequences (for example
  m divides x implies m divides x*y) with explicit integer-domain premises.
- [ ] If using these consequences before native capture, retain their exact
  certificates and original dependencies and splice them into the returned graph.
  A helper lemma must never be exposed as an unexplained asserted input.
- [ ] Verify original-query SAT controls, negative/zero divisor cases and shared
  total deadlines. If the native solver still times out, report it as a native
  capability boundary, separate from reconstruction failures; do not mask it.

## Capture, analysis and reading scalability

Files: _z3_proof.py, core.py, rules.py, text.py; test_core.py, test_detail.py,
test_reading.py; test/bmc/test_solver_proof_coverage.py.

Interfaces: preserve to_text(language, detail), expand(block_id), get_term_text
and per-call extensions. Preserve the distinction between guide and full evidence.
Use existing folds and references; do not add a second proof-rendering framework.

- [ ] Profile native solve/proof creation, DAG export, rule analysis, reading
  construction and each text view separately for 50/100/250 conditional links.
- [ ] Inspect native node/edge growth before attributing cost to Python. Add a
  targeted regression for each repeated traversal/allocation actually found.
- [ ] Remove repeated DAG work using per-invocation memoization and indexed
  structures. Do not weaken replay or simply increase timeouts.
- [ ] Make brief a selected-input/semantic-chain/contradiction guide with explicit
  expansion references. Keep hypothesis boundaries and every gap visible.
- [ ] Factor repeated standard-view premise sets and formula definitions; keep
  exact evidence retrievable. Measure the proposed <=64KiB brief / <=512KiB
  standard targets for the recorded 250-link workload.
- [ ] Full-text fixture tests use text_aligner; expansion preserves the same
  claims, input dependencies, source links and open/discharged assumptions.
- [ ] Report timing improvements by phase on the same host; CI checks structural
  work bounds and semantics rather than fragile subsecond timing assertions.

## Partial progress, diagnostics and minimization

Files: core.py, rules.py, text.py, io.py; test_core.py, test_rules.py,
test_loading.py, test_sources.py and test_detail.py.

- [ ] Add a public budget-limited mixed-easy/hard query showing analysis progress
  loss; use deterministic budget instrumentation only to pin that public behavior.
- [ ] Preserve completed node checks on analysis timeout. Keep unchecked nodes
  explicitly pending/unsupported, retain native UNSAT/captured evidence, and
  distinguish scope-check progress from arithmetic-check progress.
- [ ] Add a RuntimeWarning for an internal generated/checkable evidence mismatch,
  with node/rule/cause; also retain structured diagnostics. Ordinary expected
  search exhaustion remains an explicit gap, not an exception or false-invalid.
- [ ] Audit minimize=True with background, duplicate equivalent inputs, irrelevant
  constraints and exhausted reproof budgets. Preserve proven subset-minimality
  separately from chosen proof scope; source unions are not necessity claims.
- [ ] If initial full-proof work starves minimization in a public reproduction,
  perform checked core reduction before optional full-proof reconstruction, with
  explicit full_proof availability. Do not silently promise both under no budget.
- [ ] Verify canonical roundtrip and all bilingual views of partial reports, then commit.

## Final acceptance and publication

- [ ] Promote disposable public experiments to independent test-tree fixtures.
  Maintain a source-operation/semantic-obligation/producer/checker/test mapping.
- [ ] For each required family, vary names, assertion order, cast placement,
  equivalent arithmetic forms, irrelevant inputs, native layouts and BMC frames.
- [ ] Run `pytest test/solver/proof test/bmc/test_solver_proof_coverage.py` with
  branch coverage and require 100% for changed proof code.
- [ ] Run `make unittest RANGE_DIR=./solver/proof WORKERS=4` and
  `SKIP_SLOW_TESTS=1 make unittest WORKERS=8`.
- [ ] Run `make test_boundary_check resource_ownership_check`,
  `python tools/check_api_doc_toctree.py --check --self-check`, and
  `make docs_en docs_zh`.
- [ ] Obtain independent review of reachable public behavior; resolve findings
  through RED/GREEN regressions, not status relabeling.
- [ ] Push code and await the exact code-head CI matrix and aggregate gate.
- [ ] Publish a new capability comment with runnable inputs, complete generated
  text blocks, before/after measurements and remaining native/search boundaries.
- [ ] Audit every requirement against current evidence before declaring ready.
  Do not infer universal coverage from test counts or coverage percentages.

## Execution order

Exact capture -> integer lattice -> integer range/congruence -> composite squares.
Then reassess native preprocessing, profile/repair scalability, preserve partial
progress, and perform final acceptance. Each implementation task follows
failing test -> minimal shared fix -> independent replay/negative controls ->
focused tests -> commit. No unrequested unrelated cleanup.

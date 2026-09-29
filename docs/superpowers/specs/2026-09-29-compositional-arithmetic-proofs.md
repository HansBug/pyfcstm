# Compositional arithmetic proof reconstruction

## Objective

Keep Z3 as the only native backend. Replace formula-specific arithmetic search
with compositional semantic facts and parameterized exact algebraic evidence.
Preserve the current public proof/query/source contracts unless a portable
certificate field must change; backward compatibility is not required.

The user approved implementation, TDD, full changed-code branch coverage, real
BMC experiments, and a new pull-request comment with complete readable output.
Work directly in the current repository, without a worktree.

## Boundaries

- Python 3.7–3.14; Windows, Linux, macOS; no added runtime dependency.
- Do not change the submitted conjunction, silently strengthen domains, or
  treat repeated Z3 UNSAT answers as an independently reconstructed proof.
- Use native coefficients when available; reconstruct only the missing local
  arithmetic obligations. All generated facts retain their premises.
- Arbitrary nonlinear arithmetic is not promised complete. Unknown semantics,
  exhausted search limits, and genuinely unsupported evidence stay explicit.
- This change provides the solver core; it does not replace BMC's old public
  explanation interface or change property polarity/window semantics.

## Architecture

The existing portable term DAG and local proof premises define each arithmetic
obligation. A semantic elaborator visits only reachable arithmetic expressions
and derives domain-conditional facts for powers and roots. Facts share the
existing sparse rational polynomial representation and indexed derivation DAG.
The search composes sign, equality and polynomial consequences. Candidate search
and offline certificate replay remain separate. Native proof evidence is kept.

Semantic rules are parameterized by the original typed operation and exact
exponent, not by case names, source names, proof node IDs or literal degrees.
Examples include positive-base power positivity, nonnegative rational-power
identities and odd integral-power order for arbitrary admitted degrees.
Negative and zero bases/exponents are handled by their actual side conditions.
No source metadata may introduce a logical premise.

The polynomial search replaces the hardcoded cubic construction with a generic
integer-power identity construction. It iterates relevant semantic/algebraic
consequences until a contradiction is obtained, no new facts are available, or
the existing shared budget/explicit expansion limit is reached. It reuses exact
normalization, sign elimination and certificate pruning already in the module.

Product candidates are searched jointly before their evidence is materialized.
Only candidates used by an exact combination witness become proof steps.
Equality-rewritten bounds retain their derivations but their reduced forms
supply future factors; equality multiplication records are not additional
factor candidates. Actual local order bounds are normalized and searched before
speculative atom orders. This avoids consuming the evidence-growth limit while
enumerating irrelevant intermediate products. The existing Z3 linear solver
finds rational weights for the joint candidate pool, after exact support pruning.

Portable evidence records the operation term and the prior fact indices needed
for every semantic rule. Replay validates the original operator, sorts,
exponent, side conditions, exact resulting polynomial and strictness. Unknown
rules or changed evidence must fail replay. Text rendering exposes the rule,
its necessary conditions and exact conclusion in English and Chinese.

## Precision and assurance

Only the dependency closure of the final contradiction is retained in each
certificate. Input-group minimization keeps its existing subset-minimality
contract; no globally shortest-proof claim is introduced. Reading completeness
and independent rule checking remain separate.

## Acceptance

The acceptance inventory follows the actual expression translator and BMC
compiler, rather than counting native proof rule names:

- Boolean conjunction/disjunction, implication, conditional updates, branch
  assumptions and discharge: `test_rules.py`, `test_detail.py`, `test_guards.py`
  and the actual control-flow cases in `test_solver_proof_coverage.py`.
- Exact linear arithmetic and integer divisibility: `test_rules.py` and
  `test_integer.py`; strict bounds and zero-weight premises have separate tests.
- Integer division, remainder and conversion axioms: `test_theories.py` and
  `test_intervals.py`, plus the actual remainder-guard BMC case. These checks
  do not claim completeness for arbitrary combinations of integer arithmetic.
- Polynomial signs, equality substitution and products: `test_polynomial.py`
  and `test_semantics.py`. Test both forward multiplication and reverse factor
  reasoning, including zero boundaries; knowing a factor is merely nonnegative
  never licenses cancellation without further evidence.
- Powers and roots: `test_semantics.py` exercises domain-conditioned facts,
  parameterized degrees, nested expressions, reordered/renamed inputs and
  satisfiable controls. Real BMC cases include assignment aliases across frames
  and contradictions entirely inside FBMCQ assumptions.
- Boolean event cardinality: `test_theories.py` and the real three-event BMC
  encoding. Weighted evidence is checked separately from source projection.
- Source projection, portable loading and all reading detail levels have their
  own tests; full text uses `text_aligner`.

This inventory identifies the verification entry points, not a theorem of
completeness. Native mechanical rules may remain explicitly trusted even when
the reading has no gaps. Symbolic real exponents have supported sign facts,
not a general exponential decision procedure. Translation rejection or native
UNKNOWN must not be converted into a purported UNSAT proof.

1. Regression families for rational powers, positive-base variable powers,
   odd/even integral order and compositions of principal roots.
2. Renaming, operand ordering, expanded/factored form and nested expressions
   preserve supported semantics; SAT controls and certificate mutation tests
   reject invalid deductions.
3. Real FCSTM expression translation and BMC core queries exercise the families.
4. Full text snapshots use text_aligner; all detail modes/languages round-trip.
5. Changed production code has 100% branch coverage, full repository regression
   and current-head CI pass, independent review findings are resolved.
6. Documentation and a new PR comment explain capabilities, real proof text,
   remaining explicit boundaries and verification results. Do not merge the PR.

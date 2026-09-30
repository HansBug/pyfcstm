# Arithmetic proof reliability and usable readings

## Purpose

Make the Z3-based solver proof component reliable for the arithmetic and control
constraints actually emitted by pyfcstm, and make its output usable by humans
and LLM harnesses. This is a proposed repair design, not a completed change.
Use the current checkout. Do not introduce another solver/backend/dependency.
Do not merge or replace the old BMC explanation interface as part of this repair.

## Observed failures at 2610a756

The public experiments under `.superpowers/review-core-challenge/` are disposable
investigation artifacts. Durable regression inputs must live under `test/`.

- Enabling Z3 decimal display causes exact rational capture to emit an
  approximation ending in `?`; ordinary `explain_unsat` raises ValueError.
- Nonnegative real x with `ToReal(ToInt(x)) < 0` is UNSAT but its valid native
  proof is marked invalid. The analogous ceil case also fails. The same problem
  occurs in an actual BMC floor-product query.
- Actual BMC queries `x%3==1 && (x+2)%3!=0` and
  `x>1 && y>1 && x*y==7` retain unsupported gcd-test obligations. A public solver
  product-equals-11 case also does so. Equality-pair-only gcd reconstruction is
  insufficient for native integer range reasoning and nonlinear integer atoms.
- `(x*y-1)**2+(x-y)**2<0` and `(2*x+3*y-1)**2+(x-y)**2<0`
  have partial readings. Candidate squares do not span these composite factors.
- `x**4+y**4<2*x*x*y*y` has a complete direct solver reading, but a real BMC
  embedding returns partial after about 21.6 seconds with a 120-second budget.
  Native proof layout changes the local obligations that must be reconstructed.
- A 250-link conditional increment chain is decided by an ordinary native
  solver in approximately 0.002 seconds, but the report took 24.7 seconds;
  brief/standard/detailed text measured 5,001,416 / 7,271,683 / 7,209,157 bytes.
  These local measurements include native proof production and do not identify
  the time spent by each stage; profiling is required before changing algorithms.
- Assembly timeout preserves captured evidence but loses completed analysis
  progress because analysis returns only after the entire graph is processed.
- `x%2==0 && (x*y)%2!=0` times out in both ordinary native solving and native
  proof configuration 6 at 10 seconds; configuration 2 reports incompleteness.
  This is not evidence that the Python translator alone causes the timeout.

## Required behavior

1. Exact portable values are independent of Z3 presentation settings.
2. Integer-valued real expressions preserve their integer lattice through
   casts, arithmetic and rounding. Replayers independently validate any bound
   strengthening. General real expressions must never acquire integrality.
3. Native gcd reasoning is reconstructed with explicit equality, range and
   congruence evidence. Unsupported native layouts are not labeled invalid just
   because an incomplete interpretation failed; actual invalid certificates
   remain invalid and produce observable diagnostics.
4. Square/sign/equality/integer evidence composes without formula-name cases.
   Input expression structure can propose candidates, but only local premises
   and explicitly proved domain conditions may establish facts.
5. The listed solver and BMC arithmetic regressions, including their renamed,
   reordered, cast, expanded, factored and frame-alias variants, must have complete
   readings. No blanket completeness claim for arbitrary nonlinear arithmetic.
6. The original conjunction, source relationships and local assumptions are
   preserved. A source description or a solver UNSAT answer is not a certificate.
7. Capture, reconstruction and rendering costs are measured separately. Avoid
   repeated work over a DAG. Brief output is a guide with retrievable evidence,
   not a second near-complete listing of native deductions.
8. Timeout/unknown, unsupported reconstruction, exhausted search and rejected
   evidence remain distinguishable. Completed evidence survives interruption
   of optional analysis; no incomplete result is labeled complete.
9. Input subset-minimality, final dependency pruning and global shortest proof
   are separate guarantees. Only the first two are promised.
10. All certificate changes update generation, independent replay, canonical IO,
    English/Chinese rendering, docs and tests together.

## Native solving boundary

The parity-product timeout remains an explicit end-to-end challenge. Compare
identical assertions under ordinary and proof-enabled native configurations.
Investigate exact congruence consequences before changing retry policies. If
certified derived lemmas are supplied to Z3, their derivations must be spliced
back to original input occurrences; they must never become unexplained inputs.
No unverified lemma injection or hidden multiplication of the shared deadline.
A universal guarantee that every pyfcstm formula terminates with a proof is not
an acceptance criterion. This challenge must be reported separately from cases
where Z3 has already returned UNSAT but reconstruction is incomplete.

## Acceptance

- Reproduce each reported defect before fixing it; demonstrate RED then GREEN.
- Keep SAT/domain/strictness negative controls and reject mutated certificates.
- Run all source-generated regressions at solver and real BMC boundaries.
- Complete text comparisons use text_aligner; single-line values use ==.
- Fixed captured evidence determines golden text. Live Z3 generation checks
  semantics, evidence, statuses and canonical roundtrips without prescribing a
  platform-specific native proof path.
- Changed proof code: 100% statements and branches, plus adversarial behavior
  tests. Coverage percentage alone is not a completeness claim.
- Profile 50/100/250-link chains. Proposed reading target for the recorded
  250-link case: brief <= 64 KiB, standard <= 512 KiB, with explicit expansion
  to all retained deductions, gaps and source links. These are workload targets,
  not universal output-size bounds. Baseline/after timings use the same host.
- Verify Python 3.7-3.14 and Windows/Linux/macOS through the existing CI matrix.
- Independent review, full repository regression, docs/gates and exact code-head
  CI must pass before publishing a new merge-readiness conclusion.

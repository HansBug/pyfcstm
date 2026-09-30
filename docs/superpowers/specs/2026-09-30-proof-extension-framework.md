# Proof extension framework

## Goal and approved scope

Organize the existing Z3 proof translation and local reconstruction behind
explicit extension seams. Preserve all mathematical capabilities, strategy
ordering, evidence selection, minimization, scopes, source mappings, budgets,
diagnostics and English/Chinese readings. Work in the current checkout.

The user authorized implementation after discussing this design. This is an
engineering refactor, not a new proof search algorithm. Do not introduce a new
backend, global mutable plugin registration, cross-strategy saturation, proof
ranking, or production BMC explanation migration.

## Design

1. A small explicit certificate catalog associates the existing six typed
   payloads and node fields with replay and reading handlers. Preserve the
   canonical dataclasses and field names. Online reconstruction and offline
   loading use the same replay dispatch; structural validation remains strict.
2. Local reconstruction has a uniform result containing inference kind,
   checking status, typed evidence and diagnostics. Native labels select the
   existing fast paths, followed by the existing fallback order. Scope and
   report-state aggregation stay in the common analyzer.
3. Evidence reading handlers own family-specific prose. The common renderer
   retains formula references, scopes, sources, folds, detail levels and final
   conclusions. No mathematics or search runs during rendering/loading.
4. Extend through ordinary functions and immutable descriptors. Reuse existing
   ProofExtensions for per-call native interpreters, source adapters and domain
   folds. Only export interfaces needed by callers from proof/__init__.py.

## Invariants

- Python 3.7–3.14, Windows/Linux/macOS; no new dependency.
- Native evidence remains the backbone; reconstruction supplies local details.
- Checking never invokes reconstruction or Z3. Pure exact arithmetic may be shared.
- Strategies cannot change native conclusions or discharge hypotheses.
- Shared budget and completed-prefix preservation remain intact.
- Trusted/checked, partial/complete and source completeness remain distinct.
- Group subset-minimality and dependency pruning retain their existing meaning.
- Fixed evidence must produce identical canonical data and full reading text.
- Preserve all existing negative controls and observable invalid-evidence warnings.

## Acceptance

TDD for new dispatch contracts, with existing behavior characterized before
moving code. All changed proof modules require 100% statement/branch coverage.
Full text comparisons use text_aligner. Run real BMC regressions, the prescribed
proof make target, whole-repository lightweight CI suite, bilingual docs,
generated API docs and repository gates. Obtain independent final review, push
reviewed changes and verify CI for the final head. Update the PR comment with
architecture, actual full proof output and final evidence; do not merge.

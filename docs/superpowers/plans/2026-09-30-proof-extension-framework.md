# Proof Extension Framework Implementation Plan

> **For agentic workers:** Use superpowers:executing-plans inline, followed by a fresh final reviewer. The user authorized implementation; preserve the current checkout and do not create a worktree.

**Goal:** Make existing proof interpretation, reconstruction and evidence handling extensible without changing proof behavior.

**Architecture:** Use immutable certificate descriptors, a uniform local reconstruction result, and evidence-specific reading functions. Keep scope/input/report orchestration separate and preserve existing public canonical data.

**Tech Stack:** Python 3.7–3.14, dataclasses, existing Z3, pytest and text_aligner.

**Spec:** ../specs/2026-09-30-proof-extension-framework.md

## Global Constraints

- Current checkout; no dependency, backend or global mutable registration.
- Preserve strategy order, budgets, mathematical rules, minimality and full text.
- No BMC production migration, saturation engine or candidate scoring.
- Keep checked and trusted evidence distinct; all failures remain observable.

## Review Focus

- Offline proof loading must remain Z3-free and reject corrupted evidence.
- Local reconstruction must retain fast-path/fallback order and stop at first accepted evidence.
- Timeout must retain completed checks without promoting unfinished scopes.
- Multiple evidence fields in portable snapshots retain validation and presentation order.
- Domain folds, source alternatives and brief formula references remain lossless.

## Task 1: Certificate replay catalog

Files: new proof/evidence.py and test/solver/proof/test_evidence.py;
existing proof/io.py and checker modules.

Interface: immutable CertificateHandler descriptors expose field, kind, payload
type and replay(node, graph, certificate, budget=None); certificate_handlers()
returns the fixed catalog. iter_evidence(node) yields attached descriptors and
payloads. Loading and later reconstruction share this dispatch.

- [ ] Write catalog tests using real captured evidence: correct family selection, absent evidence, replay success and mutated evidence rejection; run RED.
- [ ] Implement the minimal catalog and uniform checker signatures; run GREEN.
- [ ] Route offline replay through the catalog, preserving all existing reference/sort checks and error messages.
- [ ] Run pytest test/solver/proof/test_evidence.py test/solver/proof/test_loading.py test/solver/proof/test_integer.py; require all pass; commit.

## Task 2: Local reconstruction contract

Files: new proof/reconstruction.py, test/solver/proof/test_reconstruction.py;
proof/rules.py and evidence.py.

Interface: reconstruct(node, graph, budget) returns a frozen Reconstruction
containing kind, local_check, evidence fields and diagnostic gaps. Existing
mathematical helpers stay reusable; analyzer owns scopes and extension priority.

- [ ] Characterize native fast paths, linear/interval/equality/polynomial fallback order, invalid evidence and shared deadline using fixed graphs; add failing contract tests.
- [ ] Move dispatch out of analyze_proof and use common evidence replay without changing search algorithms or warning semantics.
- [ ] Run all proof tests and actual BMC proof regressions; compare fixed canonical evidence and text; commit.

## Task 3: Certificate reading handlers

Files: proof/text.py, evidence.py, a focused proof/evidence_text.py if needed;
test/solver/proof/test_evidence.py and existing full-text tests.

Interface: family reading functions receive existing graph/terms/detail/reference
context and append the same lines; catalog selects the appropriate handler.

- [ ] Add a failing dispatch test proving each attached family reaches its renderer; pin multiple-evidence presentation order.
- [ ] Extract family rendering bodies without changing prose, formula aliases or layout. Keep generic folds/scopes/sources in text.py.
- [ ] Run all full-text fixtures with text_aligner, canonical roundtrips and real BMC cases; commit.

## Task 4: Documentation, coverage and merge acceptance

- [ ] Document the internal extension recipe, native translation versus local reconstruction, trust boundaries and stable public extension interfaces in bilingual docs.
- [ ] Run proof plus real BMC coverage with branch measurement; close every changed-module uncovered statement/branch with meaningful tests.
- [ ] Run make unittest RANGE_DIR=./solver/proof WORKERS=4 and SKIP_SLOW_TESTS=1 make unittest WORKERS=8 sequentially.
- [ ] Run boundary/resource gates, API toctree self-check, bilingual docs, repeated generated RST and git diff --check.
- [ ] Obtain fresh whole-branch review; resolve reachable findings with RED→GREEN tests.
- [ ] Push, verify final-head CI, update PR comment with full generated proof and architecture, verify rendered output, and declare ready without merging.

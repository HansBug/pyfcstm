# Transition Triggers Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [x]`) syntax for tracking.

**Goal:** Enforce one trigger per model edge and one ordered trigger sequence per AST transition, eliminating silent condition loss.

**Architecture:** AST EventTerm/GuardTerm sequences lower into model EventTrigger/GuardTrigger edges. Each consumer switches on the sole trigger, with no legacy mutable aliases.

**Tech Stack:** Python dataclasses, existing parser and Jinja templates, pytest/coverage.

**Spec:** [Transition trigger contract](../specs/2026-09-30-transition-triggers.md)

## Global Constraints

Python 3.7–3.14; Windows/Linux/macOS; no new dependencies; public JSON contracts unchanged; Python and JavaScript tests independent. Legacy Python constructor compatibility is intentionally not required.

## Review Focus

- Guard evaluation after a source exit in sequential combo must not move before that exit.
- Local/absolute/imported events and initial-event scopes must survive round trips.
- Forced single triggers and combo provenance must retain their restrictions and spans.
- Failed public assignments must leave objects unchanged; copy and replacement of valid objects must work.
- Every generated runtime and analysis consumer must preserve lawful transition behavior.

## Tasks

- [x] Write public AST/model contract tests; run against main and record expected failures.
- [x] Replace AST trigger types and fields in `pyfcstm/dsl/node.py`, listener and import assembly; migrate DSL tests. Verify parsing/formatting and immutable sequence contract.
- [x] Replace model fields with validated EventTrigger/GuardTrigger in `pyfcstm/model/model.py` and exports; migrate combo lowering, AST export and PlantUML. Verify public model and round-trip tests.
- [x] Migrate runtime, inspect/diagram, verify/BMC and templates using typed trigger branches. Migrate constructor assertions and generated sample tests without altering public JSON fields. Run focused suites after each group.
- [ ] Update bilingual model/DSL documentation and examples; regenerate packaged templates and API RST; verify docs and doctests.
- [x] Run full repository unittest gate and full template suites; collect statement/branch coverage and close changed-code gaps through public tests.
- [ ] Review diff independently, repair findings, create/push draft PR, watch CI and reviews until all gates pass; mark ready, leave unmerged.

## Local verification evidence

- Clean full unittest run with branch coverage: 51,265 passed, 1,010 skipped.
- Changed production Python statements: 279/279; branch arcs: 184/184, measured against the base commit. No coverage exclusions added.
- All five built-in template suites: 1,342 passed, 10 skipped (explicit native-toolchain matrix opt-in remains separate).
- Full doctest after main integration: 1,125 passed. Both language HTML builds succeeded with 18 existing warnings each; rendered pages contain no problematic-reference spans.
- Generated API RST, documentation contents, lint/format, resource ownership, test boundaries, terminology, and diagram data parity checked.
- Independent review found no actionable public-path defects; contract checks and event-scope round trips passed.
- [PR #513](https://github.com/HansBug/pyfcstm/pull/513) is open as a draft. Latest main was integrated; its new BMC event-enumeration test was migrated to the trigger API. Full BMC integration run: 6,452 passed, 30 skipped. Independent integration review found no defects. Clean integrated full unittest passed with the counts above. Remote CI and ready status are tracked on the PR.

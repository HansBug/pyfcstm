# Ordered region syntax implementation plan

> **For agentic workers:** Use superpowers:executing-plans to implement this plan task by task. Preserve complete test transcripts and inspect coverage before declaring readiness.

**Goal:** Parse and round-trip named regions and active-state conditions in Python and jsfcstm, preserve existing identifiers, and explicitly reject unsupported model construction.

**Architecture:** Extend the shared ANTLR grammar and each frontend's typed AST. Preserve region declaration order. Keep model semantics behind a structured unsupported-feature diagnostic until the model implementation is available.

**Tech Stack:** ANTLR 4.9.3, Python dataclasses, TypeScript, pytest/coverage.py, mocha/c8, Pygments and TextMate.

**Spec:** [Frozen design](https://github.com/HansBug/pyfcstm/issues/248), [umbrella execution plan](https://github.com/HansBug/pyfcstm/pull/564).

## Global constraints

- Support Python 3.7–3.14 and the existing Node.js 16 package floor; do not introduce dependencies.
- Preserve all existing language behavior, including `region` and `active` as identifiers.
- Python and JavaScript tests remain independent and keep fixtures in their respective test trees.
- Run computation-intensive checks on the authorized SSH host; keep local verification small.
- Require 100% branch coverage for new code and complete modified functions, retain full-file reports, and introduce no coverage exclusions to hide missing cases. Generated ANTLR code follows the existing coverage configuration and is verified through grammar behavior tests.
- Save every test command, full output, exit status, and source revision; publish the evidence from a new pull-request comment.
- Do not implement region runtime behavior, state-query lowering, region path resolution, or the later structural diagnostics.
- Do not change public inspect/BMC payload versioning or the FBMCQ language.

## Review focus

- Contextual words in import lexer modes, action names, event paths, history paths, and numeric expressions must retain their identity.
- Nested regions, documented declarations, escaped query strings, and all condition positions must preserve AST shape and declaration order.
- Unsupported syntax reached through imports, nested actions, or collect-mode model construction must not yield a silently incomplete model.
- Editor formatting and highlighting must distinguish syntax from identifiers and preserve region order.
- Existing parse-tree consumers, generated samples, model exports, and standalone expression APIs must remain compatible.

## Task 1: Shared grammar and Python AST

**Files:** `pyfcstm/dsl/grammar/GrammarLexer.g4`, `GrammarParser.g4` and generated files; `pyfcstm/dsl/node.py`, `listener.py`; `test/dsl/test_region_syntax.py`, `test_active_query.py`, `test_contextual_identifiers.py`.

**Interfaces:** Produce `RegionDefinition`, `StateDefinition.regions`, and `ActiveStateQuery(path: str)` through existing public parsing entry points. Preserve ordinary token accessors where practical; contextual names are accepted in every former identifier position.

- [ ] Write independent literal expectations for region structure/order, single and nested regions, documented aspects, contextual names, condition precedence and malformed syntax.
- [ ] Run the new tests and retain the expected unsupported-syntax failures.
- [ ] Add contextual tokens, restricted region statements and the condition atom; regenerate parsers.
- [ ] Implement AST nodes/listener bindings, canonical round trips and source metadata.
- [ ] Run new tests and existing DSL tests; inspect complete modified-function coverage. Expected: all behavior checks pass and all relevant branches are exercised.

## Task 2: Unsupported model construction

**Files:** `pyfcstm/model/model.py`, `expr.py`, import assembly if necessary; a focused model capability helper; `pyfcstm/diagnostics/codes.yaml`; tests under `test/model/` and `test/entry/`.

**Interfaces:** Consume the new AST nodes; report structured unsupported-feature errors from strict construction and return `(None, diagnostics)` in collect mode. Standalone expression conversion also refuses active-state queries explicitly.

- [ ] Write strict, collect, nested, imported and standalone-expression rejection tests through public APIs; run RED.
- [ ] Implement the shared rejection boundary without creating a partial executable model or mutating the caller AST.
- [ ] Test documented CLI entry points with valid unsupported files; verify controlled failures and ordinary-model success.
- [ ] Run model/entry regressions and inspect complete modified-function coverage. Expected: controlled errors with feature and source context, no unsupported execution.

## Task 3: JavaScript AST and capability boundary

**Files:** `editors/jsfcstm/src/ast/model.ts`, `builder.ts`, model/diagnostic boundary as needed; independent `editors/jsfcstm/test/region-syntax.test.ts`, `active-query.test.ts`, contextual-identifier and capability tests.

**Interfaces:** Consume the shared grammar; expose corresponding typed nodes and ordered region collections through `parseAstDocument`; refuse unsupported model construction through existing public contracts.

- [ ] Write independent parser/AST/name/range and rejection expectations; build and run RED remotely.
- [ ] Add AST types and builders, include regions in composite classification and guard model construction.
- [ ] Exercise all condition shapes, import paths and error collection paths independently of Python tests.
- [ ] Run the full JavaScript suite and collect c8 branch data. Expected: all tests pass and complete affected functions have 100% branch coverage.

## Task 4: Highlighting and formatting

**Files:** `pyfcstm/highlight/pygments_lexer.py`, `editors/fcstm.tmLanguage.json`, `editors/validate.py`, relevant jsfcstm editor code and tests.

**Interfaces:** Recognize declarations and active-state queries contextually; retain normal identifier highlighting and formatter AST equivalence.

- [ ] Add positive and negative highlighting cases and formatter idempotence/order cases; run RED.
- [ ] Implement contextual highlighting and only necessary formatter/token changes.
- [ ] Run `make -C editors/vscode syntaxes` then `python editors/validate.py`.
- [ ] Run relevant Python/JS tests and inspect coverage. Expected: canonical and packaged grammars agree, formatting preserves AST and order.

## Task 5: Full verification and coverage closure

**Files:** affected behavior tests, generated API RST and evidence artifacts.

**Interfaces:** Consume all frontend changes; produce complete, revision-linked evidence and coverage reports.

- [ ] Run full Python and JavaScript suites, doctests, API RST generation, test-boundary and public-payload checks on the remote host; use all explicitly required umbrella commands.
- [ ] Compare branch coverage against all new and modified functions and close each reachable gap using public behavior tests; report generated-parser behavior evidence separately.
- [ ] Run representative public parsing/round-trip/rejection examples with complete text output.
- [ ] Inspect generated diffs, compatibility results and test independence. Expected: no unexplained changes or missing coverage.

## Task 6: Review and pull-request readiness

**Files:** final branch, PR description, evidence manifest and new PR comment.

**Interfaces:** Produce a ready sub-PR targeting `dev/region-umbrella` with complete evidence; do not merge it.

- [ ] Obtain a fresh whole-branch review under repository public-surface scope; reproduce and fix actionable findings with RED/GREEN evidence.
- [ ] Verify final revision with required local/remote gates and CI; rerun checks affected by fixes.
- [ ] Publish full test transcripts, examples and coverage accounting in a new comment with durable links.
- [ ] Reconcile the actual diff, required checks, review results and acceptance checklist before marking ready for review/merge.

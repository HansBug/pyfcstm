# CLAUDE.md

AGENTS.md is a symbolic link to CLAUDE.md, so do not modify both files separately.

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## AI / Vibe Coding First Principles

Vibe coding is fine for quick exploration, but once you touch repository code you fall back to engineering discipline: requirements before implementation, behavior before code, verification before completion.

- Make the goal, boundaries, inputs, outputs, and success criteria explicit before writing code.
- Prefer the smallest verifiable change; don't let one task balloon into unrelated refactors.
- Every generated piece of code must be readable, explainable, testable, and revertible by a human.
- Don't blindly accept AI output; review it the same way you would review a human teammate's commit.
- Stick to the existing architecture, naming, tests, and tooling — don't start a parallel style of your own.
- Name modules, functions, classes, tests, fixtures, docstrings, pydoc text, and generated artifacts for the concrete
  behavior or domain concept they implement, not for temporary project-management labels such as PR slice IDs, roadmap
  phases, or plan bullets. A reader should be able to understand what something does without knowing the execution plan
  that introduced it.
- Keep workflow metadata out of code and API surfaces: do not put PR numbers, issue IDs, roadmap stages/phases, review
  rounds, or rollout slice names into identifiers, schema field names, runtime messages, test ids, or pydoc/docstrings.
  If Markdown documentation genuinely needs to reference a concrete workflow item, use an explicit hyperlink such as
  [PR #123](https://github.com/HansBug/pyfcstm/pull/123) or
  [issue #456](https://github.com/HansBug/pyfcstm/issues/456).
  Domain terms such as lifecycle stage names or control-system phase variables remain acceptable when they describe the
  modeled behavior rather than the implementation workflow.
- Keep Python and JavaScript unit tests strictly independent. Python tests may use fixtures and literals under
  [test/](test/),
  but must not call Node.js, jsfcstm, or resources outside the Python test tree. jsfcstm tests may use fixtures and
  literals under [editors/jsfcstm/test/](editors/jsfcstm/test/), but must not call Python code or the repository-level
  [test/](test/) tree. Either
  side's tests must keep running if the other side's implementation and test directories are removed.
- After each change, run checks proportional to the risk; nothing that hasn't been verified may be claimed as done.
- When requirements are unclear, an action is destructive, or you're near a security boundary, stop and surface assumptions and risks before proceeding.

References: OpenAI's [AGENTS.md guide](https://developers.openai.com/codex/guides/agents-md), the [agents.md GitHub](https://github.com/openai/agents.md), and Tweag's [Agentic Coding vs Vibe Coding](https://github.com/tweag/agentic-coding-handbook/blob/main/VIBE_CODING.md).

## Exception Handling Policy (no broad catches)

Broad `except Exception:` (Python) / `} catch {` / `} catch (e) {` (TypeScript / JavaScript) are **prohibited unless every expected exception class is named and justified inline**. The rule:

1. **Catch the smallest possible class.** Do not write `except Exception` when you really mean `except (ValueError, KeyError)`. Do not write `} catch (error) {` when you really mean `} catch (error: SyntaxError) {` (or its equivalent guard inside the handler).
2. **Document why each expected class can fire.** Every caught class needs an inline comment naming the call site / failure mode that produces it. A bare `except SomeError:` without explanation is not acceptable — the next reader must be able to understand *what* throws that class.
3. **Re-raise anything outside the documented set.** If the catch site cannot enumerate the failure modes (i.e. it really does need to be broad), it must check the actual exception type and re-raise on anything unexpected. Pattern:
   ```python
   try:
       ...
   except (ExpectedA, ExpectedB) as err:
       # ExpectedA: <when this fires>; ExpectedB: <when this fires>
       handle(err)
   # Anything else propagates and surfaces the bug.
   ```
   TypeScript equivalent:
   ```ts
   try {
       ...
   } catch (err) {
       if (!(err instanceof ExpectedA) && !(err instanceof ExpectedB)) {
           // Each branch above documents *why* it can fire.
           throw err;
       }
       handle(err);
   }
   ```
4. **Never silently swallow.** A `} catch {}` with no body, or `except Exception: pass` / `... return None`, is allowed only when the function's contract explicitly says "swallow everything and degrade gracefully" *and* the swallow site logs / records the dropped error somewhere observable. Otherwise the unexpected class becomes a silent CI-passing prod bug.
5. **Exceptions to the rule (literal exceptions):** the `ModelValidationError` belt-and-braces re-raise in
   [pyfcstm/model/imports.py](pyfcstm/model/imports.py) is allowed because it explicitly checks
   `if not sink.collect: raise` and forwards the structured diagnostics — the broad catch is just a re-entry point, not
   a swallow. Document the equivalent pattern at any new broad catch you introduce.

Applies to all code in [pyfcstm/](pyfcstm/), [editors/jsfcstm/src/](editors/jsfcstm/src/),
[editors/vscode/src/](editors/vscode/src/), and any new code under those trees. Auto-generated grammar files
([pyfcstm/dsl/grammar/](pyfcstm/dsl/grammar/), [editors/jsfcstm/src/dsl/grammar/](editors/jsfcstm/src/dsl/grammar/))
are exempt — they are produced by ANTLR.

## Conversation Language

Reply in whatever language the user wrote their most recent message in. Do not default to English on your own. If the user writes in Chinese, reply in Chinese; if the user writes in English, reply in English; if the user mixes languages, mirror their dominant language and keep technical terms in their original form. When the user switches languages mid-conversation, switch with them on the very next turn — do not keep using the previous language.

This rule applies to prose only (explanations, summaries, questions, status updates). Do NOT translate code, identifiers, file paths, commit messages, shell commands, CLI output, log lines, API responses, or anything that must stay verbatim for correctness. Code comments and docstrings follow the repository's existing convention (this repo uses English for code comments and reST docstrings — keep it that way regardless of conversation language).

## Project Overview

**pyfcstm** is the Python Finite Control State Machine Framework. It parses the **FCSTM (Finite Control State
Machine) Domain-Specific Language (DSL)** and generates executable code in multiple target languages. It focuses on
modeling Hierarchical State Machines (Harel Statecharts) with a Jinja2-based templated code generation system.

This repository must support cross-platform environments (Windows, mainstream Linux distributions, and macOS), older system platforms (for example Windows 7), older Python versions (for example Python 3.7), and a broad Python version range (3.7-3.14), so always account for that compatibility envelope when writing code or introducing dependencies.

## Current Repository Status

As of 2026-03, the repository is no longer only a generic template experiment. The current codebase already includes:

- Repository-source built-in templates under [templates/](templates/), with [templates/python/](templates/python/) as the reference implementation
- Packaged built-in template assets under [pyfcstm/template/](pyfcstm/template/), including
  [pyfcstm/template/index.json](pyfcstm/template/index.json), extraction helpers, and packaged zip assets
- CLI support for both custom template directories and packaged built-in templates via `pyfcstm generate -t ...` and `pyfcstm generate --template python ...`
- Expression rendering and statement rendering infrastructure under [pyfcstm/render/](pyfcstm/render/), with built-in statement styles for `dsl`, `c`, `cpp`, `python`, `java`, `js`, `ts`, `rust`, and `go`
- Dedicated template tests under [test/template/](test/template/), including generated-runtime tests and runtime-alignment tests for the built-in `python` template
- A render/template tutorial path in [docs/source/tutorials/render/](docs/source/tutorials/render/) that now reflects the current renderer, template packaging, and testing model

When updating repository guidance, do not describe built-in templates, statement rendering, or CLI `--template` support as planned-only features. They are current behavior.

## Common Commands

### Testing

```bash
make unittest                                        # Run all tests
make unittest RANGE_DIR=./config                     # Specific directory
make unittest COV_TYPES="xml term-missing"           # With coverage types
make unittest MIN_COVERAGE=80                        # With minimum coverage
make unittest WORKERS=4                              # With parallel workers
make test_boundary_check                              # Validate pytest boundary rules

# Run a single test file or function directly:
pytest test/simulate/test_semantic_fixtures.py -v
pytest test/simulate/test_semantic_fixtures.py::test_simulation_semantic_fixture -v

# Fast path: run the same lightweight template subset used by the default Code Test workflow.
SKIP_SLOW_TESTS=1 make unittest          # skips C-family full semantic/native alignment, keeps Python full + wrapper smoke
```

The `SKIP_SLOW_TESTS=1` env var is read by [test/conftest.py](test/conftest.py). It skips the broad
[test/template/c/](test/template/c/) and [test/template/c_poll/](test/template/c_poll/) paths, plus the full semantic
alignment and explicit native-toolchain alignment tests under [test/template/cpp/](test/template/cpp/) and
[test/template/cpp_poll/](test/template/cpp_poll/). C++ wrapper smoke tests, the Python template, simulator, model, DSL,
render, and verify tests still run. This is now the default `Code Test` workflow subset; selected non-Python template
full suites run in dedicated `template_full` jobs instead of the main unittest matrix.

### Template Suite Detector

The repository includes a tools-only detector and runner for template-suite selection. They are repo-local helpers with
explicit `--check` self-checks; they are **not** part of the public `pyfcstm` package. The default GitHub `Code Test`
workflow uses the lightweight template subset from `SKIP_SLOW_TESTS=1 make unittest`, then runs representative and
selected full template suites through dedicated jobs.

```bash
python tools/detect_template_suites.py --check

python tools/detect_template_suites.py \
  --changed-files /tmp/changed-files.txt \
  --commit-message-file /tmp/commit-message.txt \
  --event-name local \
  --json

python tools/detect_template_suites.py \
  --changed-files /tmp/changed-files.txt \
  --commit-message-file /tmp/commit-message.txt \
  --event-name local \
  --include-suites c,c_poll \
  --json
```

Run selected template suites locally with the companion runner:

```bash
python tools/run_template_suites.py --check
PYFCSTM_TEMPLATE_SUITES=python make template_unittest
PYFCSTM_TEMPLATE_SUITES=c,c_poll make template_unittest
PYFCSTM_TEMPLATE_SUITES=cpp,cpp_poll make template_unittest
PYFCSTM_TEMPLATE_SUITES=template_representative make template_unittest
PYFCSTM_TEMPLATE_SUITES=all make template_unittest TEMPLATE_UNITTEST_ARGS="--dry-run"
PYFCSTM_RUN_NATIVE_TOOLCHAIN=1 make template_unittest TEMPLATE_UNITTEST_ARGS="--include-suites c --run-native-toolchain"
```

`make template_unittest` depends on `tpl`, so it refreshes packaged built-in template assets before running pytest;
direct `python tools/run_template_suites.py ...` invocations package templates by default unless `--no-package` is passed. The
runner clears any inherited `SKIP_SLOW_TESTS`, `PYFCSTM_TEMPLATE_SUITES`, and `PYFCSTM_SKIP_TEMPLATE_SUITES` values from
the pytest subprocess for explicit template-suite runs; otherwise selecting `c`, `c_poll`, `cpp`, or `cpp_poll` could
become a false-green skip or leak selector state into tests. Explicit suite selection does not automatically add the
`default` lightweight set; use `PYFCSTM_TEMPLATE_SUITES=default,c` when you want contract checks plus one full suite.
Native toolchain tests remain explicit opt-in through `--run-native-toolchain` or `PYFCSTM_RUN_NATIVE_TOOLCHAIN=1`, and
the opt-in requires at least one selected C-family suite (`c`, `c_poll`, `cpp`, or `cpp_poll`).

Recognized suite tokens are `default`, `template_core`, `template_representative`, `python`, `c`, `c_poll`, `cpp`,
`cpp_poll`, and `all`. The special `all` token expands to `python,c,c_poll,cpp,cpp_poll`; fixed/default suites do not
enter the detector's dynamic `matrix.include` output.

Commit-message labels use exact bracketed forms such as `[tpl:c]`, `[tpl:c_poll]`, `[tpl:all]`, and `[skip-tpl:c]`;
whitespace or extra/nested brackets are invalid for both `[tpl:*]` and `[skip-tpl:*]` labels, so `[tpl: c]`,
`[tpl:c ]`, `[tpl :c]`, `[skip-tpl : c]`, and `[tpl:c]]` fail instead of normalizing or being silently ignored.
Multiple labels may be combined. Each bracketed label accepts one suite token only; use repeated labels such as
`[tpl:c] [tpl:c_poll]` instead of comma-separated text inside one label. The parser is context-free: a live label inside
prose or a Markdown code block is still parsed as an instruction, so use neutral examples such as `tpl:c` when
documenting labels without intending to select a suite.

Path-detected suites are protected. `PYFCSTM_SKIP_TEMPLATE_SUITES` and `[skip-tpl:*]` may remove only manually selected
dynamic suites; they cannot remove path-detected suites and cannot disable fixed/default jobs. The detector is
intentionally conservative across C-family wrapper dependencies: changes under `templates/c/**` select both `c` and
`cpp`, while changes under `templates/c_poll/**` select both `c_poll` and `cpp_poll`. Unknown labels or suite tokens
are hard failures, not warnings. The current JSON schema version is `template-suite-detector/v1`; renaming or removing
fields requires a new schema version.

In GitHub Actions, `workflow_dispatch` accepts `template_suites` and `skip_template_suites` inputs. A dispatch without a
positive `template_suites` value fails closed to `all`; a skip-only dispatch cannot narrow coverage to an empty matrix.
The `Code Test` workflow intentionally avoids workflow-level `on.push.paths` / `paths-ignore` gating: every push enters
the workflow, and suite selection happens inside detector, representative, full-suite, and aggregate-gate jobs so branch
protection does not get stuck on path-filtered pending checks. On non-default branch pushes, detector paths are computed
from the merge-base with the repository default branch to the pushed head, not merely from the last pushed commit range;
that keeps the latest required check covering the whole branch diff even after a later docs-only follow-up commit.
Default-branch pushes still use the GitHub push event's `before..sha` range, and any diff lookup failure fails closed to
`all`. Use the existing commit-message skip tokens for truly docs-only pushes that should bypass expensive jobs.
The stable aggregate check is named `template-suite-gate`; branch protection should depend on that gate rather than on
per-suite dynamic job names such as `Template full (c)`. Code-test skip tokens skip the expensive unittest/
representative/full jobs only after detector success; unknown template labels, malformed detector output, missing detector
outputs, or detector failures must still fail the stable gate. These global skip tokens bypass selected/path-protected full
suites only as whole-workflow skip controls; per-suite `[skip-tpl:*]` / `PYFCSTM_SKIP_TEMPLATE_SUITES` requests still
cannot remove path-protected suites. The dynamic full-suite job runs on Ubuntu with Python 3.11 and clears inherited
`SKIP_SLOW_TESTS` before invoking `make template_unittest`, so protected or manually selected full suites cannot be
converted into false-green skips.

### CI Workflow Commit-Message Triggers

[.github/workflows/test.yml](.github/workflows/test.yml) honors five magic substrings in the **head commit message**.
They are checked with GitHub Actions' `contains()`, which is a **plain substring match** — there are no word boundaries,
no regex anchors. A natural-language phrase that happens to embed one of these substrings will silently trigger the
gate. Always grep your commit message against the table below before pushing.

| Substring | Trigger | Effect |
|---|---|---|
| `ci skip` | head commit message contains this substring anywhere | Skips the expensive Code Test test jobs (`Code test`, representative, and selected full suites), `jsfcstm test`, and `CLI Build`; the lightweight detector / `template-suite-gate` may still report a successful skip summary for branch-protection stability. Use for docs-only / comment-only commits. |
| `test skip` | head commit message contains this substring anywhere | Skips the expensive Code Test test jobs (`Code test`, representative, and selected full suites) and the `jsfcstm test` workflow. `CLI Build` still runs; the lightweight detector / `template-suite-gate` may still report a successful skip summary. |
| `[skip-slow]` | head commit message contains this substring anywhere | Legacy compatibility token. The default `Code Test` unittest matrix already runs with `SKIP_SLOW_TESTS=1`; selected/path-protected full template suites still run in `template_full` jobs and explicitly clear `SKIP_SLOW_TESTS`. |
| `[python skip]` | head commit message contains this substring anywhere | Skips the expensive Code Test test jobs (`Code test`, representative, and selected full suites) AND `CLI Build` jobs. The `jsfcstm test` job still runs; the lightweight detector / `template-suite-gate` may still report a successful skip summary. Use for jsfcstm-only changes (TypeScript / mocha updates) where the Python matrix would only burn CI minutes. |
| `[js skip]` | head commit message contains this substring anywhere | Skips only the `jsfcstm test` workflow. The Python unittest matrix and `CLI Build` still run. Use for Python-only / Makefile changes that obviously can't affect the jsfcstm TypeScript build. |

**Footgun:** because `contains()` is substring match, phrases like `"slow-test skip mechanism"` or `"document the ci skip flag"` will activate `test skip` / `ci skip` respectively. If you need to mention these tokens in a commit body, either rephrase (`"slow-test gating"`, `"document the ci-bypass flag"`) or quote them with characters that break the literal substring (e.g. `` `ci-skip` ``, `ci_skip`). When in doubt, run:

```bash
git log -1 --format='%B' | grep -iE 'ci skip|test skip|\[skip-slow\]|\[python skip\]|\[js skip\]'
```

before pushing — if any line matches and that wasn't your intent, amend.

### Building and Packaging

```bash
make package    # Build package (sdist and wheel)
make build      # Build standalone executable with PyInstaller
make test_cli   # Test CLI executable
make clean      # Clean build artifacts
make tpl        # Package repository templates into pyfcstm/template
make tpl_clean  # Remove packaged template zip assets and index
make templates_package  # Alias of make tpl
```

### Documentation

```bash
make docs                        # Build documentation locally (auto-detects language)
make docs_en / make docs_zh      # Build for specific language
make pdocs                       # Production documentation with versioning
make rst_auto                    # Generate RST from Python source files
make rst_auto RANGE_DIR=model    # Generate RST for specific directory
make sha256                      # Update generated SHA-256 sidecar files
make docs_auto                   # Generate Python docstrings (requires hbllmutils)
make todos_auto                  # Complete TODO comments (requires hbllmutils)
make tests_auto                  # Generate unit tests (requires hbllmutils)
make docs_auto AUTO_OPTIONS="--model-name deepseek-V3 --param max_tokens=200000"
```

### ANTLR Grammar Development

```bash
make antlr        # Download ANTLR jar and setup (requires Java)
make antlr_build  # Regenerate parser from grammar files after modifying GrammarParser.g4 or GrammarLexer.g4
```

### Sample Test Generation

```bash
make sample / make sample_clean  # Generate/clean test files from sample DSL files
```

### VSCode Extension

```bash
make vscode / make vscode_clean  # Build/clean VSCode extension package
```

### Logo Generation

```bash
make logos / make logos_clean    # Generate/clean PNG logos from SVG sources
```

### CLI Usage

```bash
pyfcstm plantuml -i input.fcstm -o output.puml
pyfcstm generate -i input.fcstm -t template_dir/ -o output_dir/
pyfcstm generate -i input.fcstm --template python -o output_dir/
pyfcstm generate -i input.fcstm -t template_dir/ -o output_dir/ --clear
pyfcstm simulate -i input.fcstm                                      # Interactive mode
pyfcstm simulate -i input.fcstm -e "cycle; cycle Start; current"     # Batch mode
pyfcstm simulate -i input.fcstm -e "init System.Active counter=10; cycle 5"  # Hot start batch

# Interactive hot start:
# > init System.Active counter=10 flag=1
# > cycle
```

### Code Formatters For Generated Templates

When working on multi-language generated templates, prefer the smallest practical formatter set instead of a
language-by-language best-of-breed matrix. The repository guidance uses the following minimal toolset to cover the
mainstream target languages that pyfcstm cares about:

- `ruff`: `py`
- `dprint`: `js`, `ts`, and also common text/config formats such as `json`, `yaml`, `toml`, `md`, `html`, and `css`
- `clang-format`: `c`, `cpp`, and `java`
- `rustfmt`: `rust`
- `gofmt`: `go`

When prompting an LLM to generate template code, prefer instructions such as "make the output acceptable to the
formatter defaults" instead of writing large hand-authored style guides. Avoid manual column alignment or other
styling that formatters will immediately rewrite.

Recommended installation commands:

```bash
# ruff
python3 -m pip install --user ruff
# or: brew install ruff
# or: choco install ruff

# dprint
npm install -g dprint
# or: brew install dprint
# or: choco install dprint
# Then create a dprint.json with the needed plugins:
printf '{"plugins": []}\n' > dprint.json
dprint config add oxc

# clang-format
sudo apt install clang-format
# or: brew install clang-format
# or: choco install llvm
# rootless Linux fallback:
python3 -m pip install --user clang-format

# rustfmt
rustup component add rustfmt

# gofmt (installed with the Go toolchain)
# Linux package manager example:
sudo apt install golang-go
# or: brew install go
# or: choco install golang
```

Single-file reformat commands:

```bash
# Python via ruff
ruff format path/to/file.py

# JavaScript / TypeScript via dprint
# Requires a configured dprint.json that includes the oxc plugin.
dprint fmt path/to/file.js
dprint fmt path/to/file.ts

# C / C++ / Java via clang-format
clang-format -i path/to/file.c
clang-format -i path/to/file.cpp
clang-format -i path/to/File.java

# Explicit convergence check for generated C / C++ / Java artifacts
# when you need a concrete 4-space indentation rule during template work:
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/file.c
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/file.cpp
clang-format -i -style='{BasedOnStyle: LLVM, IndentWidth: 4}' path/to/File.java

# Rust via rustfmt
rustfmt path/to/file.rs

# Go via gofmt
gofmt -w path/to/file.go
```

Per-tool coverage summary:

- `ruff`
  - Primary coverage here: `py`
- `dprint`
  - Primary coverage here: `js`, `ts`
  - Also useful for generated support files such as `json`, `yaml`, `toml`, `md`, `html`, and `css`
- `clang-format`
  - Primary coverage here: `c`, `cpp`, `java`
  - This is a pragmatic low-tool-count choice for Java in template work, even though some Java projects prefer `google-java-format`
- `rustfmt`
  - Coverage: `rust`
- `gofmt`
  - Coverage: `go`

If a generated template language falls outside this set, add a dedicated formatter only when there is a concrete need.
Do not expand the formatter matrix casually.

Mandatory completion rule for built-in template work:

- Treat formatter/linter gates as pragmatic quality gates for generated artifacts, not as absolute style objectives.
  Their job is to catch obvious roughness and keep generated output professional, tidy, and integration-friendly; they
  must not become a reason to contort generated runtime design when semantics, performance, compatibility, or
  simulator/template alignment would be harmed.
- This rule applies to all current and future target-language formatter flows, including `ruff`, `dprint`,
  `clang-format`, `rustfmt`, `gofmt`, and any formatter added later for languages such as Java, JavaScript, Rust, Ruby,
  or Go. Future template READMEs and test gates must state this same pragmatic standard instead of presenting
  formatter output as an unlimited pursuit of style perfection.
- The generated target-language artifacts must be acceptable to the corresponding formatter defaults for representative
  outputs of that language. For generated Python, representative `machine.py` artifacts should pass both `ruff check`
  and `ruff format --check` in template tests, while rare extreme formatter-only rewrites that are lint-clean,
  runtime-correct, and simulator-aligned may be documented as non-blocking when the task is not specifically about that
  shape.
- Template-facing documentation artifacts that ship with the generated output, especially generated `README.md` / `README_zh.md` files and their embedded code snippets, must also be kept formatter-friendly for the relevant language and text formatter set.
- For template changes, "done" means representative generated outputs satisfy the intended formatter flow, semantic
  alignment tests pass, and any known formatter-only exceptions are explicitly documented as non-blocking with their
  runtime/lint evidence. Do not add complex generation machinery solely to silence weak formatter-only rewrites.
- When adding or changing a multi-language built-in template, explicitly design the generated code shape and README examples so they stabilize under the formatter set listed above instead of relying on hand-aligned formatting.
- Use the formatter that matches the emitted language and verify convergence with that formatter, not with ad-hoc manual styling:
  - `py`: `ruff format`
  - `js` / `ts` and common generated text/config assets: `dprint fmt`
  - `c` / `cpp` / `java`: `clang-format`; for template verification, use a 4-space indentation configuration and require the output to stabilize under repeated formatting
  - `rust`: `rustfmt`
  - `go`: `gofmt`

## Architecture Overview

### Core Components

**DSL Parsing Pipeline** ([pyfcstm/dsl/](pyfcstm/dsl/))

- [grammar/GrammarParser.g4](pyfcstm/dsl/grammar/GrammarParser.g4) and
  [grammar/GrammarLexer.g4](pyfcstm/dsl/grammar/GrammarLexer.g4): ANTLR4 grammar for states, transitions, events, expressions; hierarchical state definitions
- [parse.py](pyfcstm/dsl/parse.py): Entry point `parse_with_grammar_entry()` for parsing DSL code strings
- [listener.py](pyfcstm/dsl/listener.py): ANTLR listener constructing AST nodes; visitor pattern for each grammar rule
- [node.py](pyfcstm/dsl/node.py): AST node dataclasses with DSL/PlantUML export methods
- [error.py](pyfcstm/dsl/error.py): DSL parsing error handling with detailed error messages

**Model Layer** ([pyfcstm/model/](pyfcstm/model/))

- [model.py](pyfcstm/model/model.py): Core classes: `StateMachine`, `State`, `Transition`, `Event`, `Operation`, `VarDefine`, `OnStage`/`OnAspect`
- [expr.py](pyfcstm/model/expr.py): Expression system supporting literals, variables, unary/binary operators, bitwise ops, function calls
- [base.py](pyfcstm/model/base.py): Base classes `AstExportable` and `PlantUMLExportable`
- Model methods: `walk_states()` for traversal, `find_state()` for lookups, export capabilities

**Rendering Engine** ([pyfcstm/render/](pyfcstm/render/))

- [render.py](pyfcstm/render/render.py): `StateMachineCodeRenderer` - loads templates, processes `.j2` files, copies static files, gitignore-style ignores
- [env.py](pyfcstm/render/env.py): Jinja2 sandboxed environment with custom globals, filters, and tests
- [expr.py](pyfcstm/render/expr.py): Expression rendering for `dsl`, `c`, `cpp`, `python` styles; `{{ expr | expr_render(style='c') }}`
- [statement.py](pyfcstm/render/statement.py): Statement rendering for executable operation blocks; `{{ stmt | stmt_render(style='python') }}` and `{{ action.operations | stmts_render(style='python') }}`
- [func.py](pyfcstm/render/func.py): `process_item_to_object()` converts config items to Python objects (imports, templates, values)

**Built-In Template Assets** ([templates/](templates/), [pyfcstm/template/](pyfcstm/template/))

- [templates/](templates/): Editable built-in template source directories tracked in the repository
- [templates/python/](templates/python/): Current reference built-in runtime template; use this as the baseline when designing future language templates
- [pyfcstm/template/](pyfcstm/template/): Packaged built-in template assets,
  [index.json](pyfcstm/template/index.json), and extraction helpers such as `extract_template()`
- [tools/package_templates.py](tools/package_templates.py) + `make tpl`: Package repository template sources into distributable built-in template assets

**Simulation Runtime** ([pyfcstm/simulate/](pyfcstm/simulate/))

- [runtime.py](pyfcstm/simulate/runtime.py): `SimulationRuntime` for cycle-based execution
  - Execution stack of active states from root to leaf; speculative validation before transitions
  - **Hot Start**: builds frame stack directly to target state without enter actions
    - Leaf states use `'active'` mode; Composite states use `'init_wait'` mode
    - `initial_vars` must provide all variables; DFS finds stoppable paths
    - Safety limits: 1000 steps max, 64 stack depth max
- [context.py](pyfcstm/simulate/context.py): Read-only execution context for abstract handlers
- [decorators.py](pyfcstm/simulate/decorators.py): `@abstract_handler` decorator for handler registration

**Constraint Solver** ([pyfcstm/solver/](pyfcstm/solver/))

- [expr.py](pyfcstm/solver/expr.py): Translates model expressions into Z3 constraint expressions
- [solve.py](pyfcstm/solver/solve.py): Z3-based constraint solving for guard reachability analysis
- [operation.py](pyfcstm/solver/operation.py): Converts state machine operations into solver constraints
- Uses `z3-solver` library; enables static analysis of transition guard satisfiability

**Entry Points** ([pyfcstm/entry/](pyfcstm/entry/))

- [cli.py](pyfcstm/entry/cli.py): Click-based CLI; `pyfcstmcli()` registered as console script
- [plantuml.py](pyfcstm/entry/plantuml.py): PlantUML diagram generation from state machine models
- [generate.py](pyfcstm/entry/generate.py): Orchestrates parsing DSL, building model, and rendering with either `--template-dir` or built-in `--template`
- [dispatch.py](pyfcstm/entry/dispatch.py): Command dispatching logic for CLI subcommands
- [simulate/](pyfcstm/entry/simulate/): Interactive simulation REPL (sub-package) with
  [repl.py](pyfcstm/entry/simulate/repl.py), [commands.py](pyfcstm/entry/simulate/commands.py),
  [completer.py](pyfcstm/entry/simulate/completer.py), [display.py](pyfcstm/entry/simulate/display.py),
  [batch.py](pyfcstm/entry/simulate/batch.py), [logging.py](pyfcstm/entry/simulate/logging.py)

**Configuration** ([pyfcstm/config/](pyfcstm/config/))

- [meta.py](pyfcstm/config/meta.py): `__VERSION__`, `__TITLE__`, `__DESCRIPTION__`, `__AUTHOR__`, `__AUTHOR_EMAIL__`

**Utilities** ([pyfcstm/utils/](pyfcstm/utils/))

- [validate.py](pyfcstm/utils/validate.py): `IValidatable`, `ValidationError`, `ModelValidationError`
- [text.py](pyfcstm/utils/text.py): `normalize()`, `to_identifier()` - converts to `[0-9a-zA-Z_]+` via `unidecode`
- [doc.py](pyfcstm/utils/doc.py): `format_multiline_comment()` - cleans `/* */` ANTLR4 comments
- [safe.py](pyfcstm/utils/safe.py): `sequence_safe()` - underscore-separated identifier conversion
- [binary.py](pyfcstm/utils/binary.py), [decode.py](pyfcstm/utils/decode.py): Binary detection, `auto_decode()` for encoding handling
- [jinja2.py](pyfcstm/utils/jinja2.py): `add_builtins_to_env()`, `add_settings_for_env()`
- [json.py](pyfcstm/utils/json.py): `IJsonOp` for serialization

### Key Architectural Patterns

**Three-Stage Pipeline**: DSL Text → AST Nodes → State Machine Model → Generated Code

**Template System**: Jinja2 with custom filters and expression styles defined in `config.yaml`. `expr_styles` enables
cross-language expression rendering (DSL expressions rendered as C, Python, etc.).

**Hierarchical State Machines**: Nested states with lifecycle actions (`enter`, `during`, `exit`) and
aspect-oriented programming via `>> during before/after` actions.

**Event Scoping**: Local (`::` source state), chain (`:` parent state), absolute (`/` root state).

## DSL Language Reference

The detailed prompt-facing FCSTM language guide now lives in
[pyfcstm/llm/fcstm_grammar_guide.md](pyfcstm/llm/fcstm_grammar_guide.md). Downstream prompt builders should read it
through the public API instead of copying long DSL snippets from this file:

```python
from pyfcstm.llm import (
    get_grammar_guide_prompt_for_llm,
    get_grammar_guide_prompt_metadata_for_llm,
    get_grammar_guide_prompt_path_for_llm,
)
```

When changing DSL syntax, model semantics, or LLM-facing parse rules, update
the packaged guide, its Markdown example tests, and the standalone
[llm_eval/](llm_eval/) fixtures or reports when the change affects LLM
generation behavior.

The packaged LLM guide is protected by
[pyfcstm/llm/fcstm_grammar_guide.md.sha256](pyfcstm/llm/fcstm_grammar_guide.md.sha256). After editing
[pyfcstm/llm/fcstm_grammar_guide.md](pyfcstm/llm/fcstm_grammar_guide.md), run `make sha256` and commit the guide and
checksum together. The hash is computed from LF-normalized UTF-8 prompt text to keep Windows and Unix checkouts
consistent.

Before committing repository code or public Python API changes, run `make rst_auto` and include any intentional generated
RST updates in the same commit.

### Quick Reference

- Variables must be declared before the single top-level root `state`; current
  persistent variable types are `int` and `float`.
- Leaf states use `state Name;`; composite states use `state Name { ... }` and
  each composite must choose an initial child with `[*] -> Child;`.
- Transition forms are deliberately narrow: plain transition, event transition,
  guard transition, and guard-plus-effect transition. Do not combine event
  syntax and guard syntax on the same transition.
- Event scopes are `:: EventName` for source-local events, `: EventName` for
  containing-state events, and `: /GlobalEvent` for root-scoped events.
- Transitions resolve targets in the current state scope. Do not write an
  outer-scope transition directly to an inner leaf state that is owned by a
  composite; put the transition inside the owning composite, or transition to
  the composite and let its initial transition choose the child.
- Forced transitions such as `!State -> Target :: Event;` and
  `!* -> Target :: Event;` expand to multiple normal transitions and cannot
  have `effect` blocks.
- Arithmetic (`num_expression`) and logical (`cond_expression`) expressions are
  separate. Assignments require arithmetic expressions; guards require boolean
  conditions; comparisons bridge numeric expressions into conditions.
- Condition operators include `&&` / `and`, `||` / `or`, `!` / `not`, `=>` /
  `implies`, `xor`, `iff`, and condition equality/inequality. Do not use `->`
  for implication, and do not use `^` as boolean xor; numeric `^` remains
  bitwise xor.
- Concrete `enter` / `during` / `exit` / `effect` blocks may use block-local
  temporary variables by assigning to a previously undeclared name. The name is
  local to that block and can only be read after assignment.
- `enter abstract Name;`, named lifecycle actions, and `ref` are valid lifecycle
  forms. A `ref` points to a named lifecycle action, not to a state or event.
- Initial entry through a composite runs composite `enter`, initial
  transition decision/effect, plain `during before`, then selected child
  `enter`. A child-to-child transition runs source child `exit`, transition
  effect, then target child `enter`; plain composite
  `during before` / `during after` do not wrap child-to-child transitions.
- `>> during before` and `>> during after` are aspect actions for descendant
  leaf-state cycles. Plain leaf `during` executes during ordinary active cycles.

## Python Docstring Style Guide

Use **reStructuredText (reST)** format exclusively, following PEP 257 and Sphinx standards.

### Core Principles

1. **Format**: reST markup exclusively
2. **Completeness**: Document all public APIs (modules, classes, functions, methods)
3. **Clarity**: Explain "why" and "what", not just "how"
4. **Cross-references**: Use reST roles (`:class:`, `:func:`, `:mod:`)
5. **Examples**: Include practical usage examples for public APIs
6. **Tone**: Professional, clear, technical but accessible

### Docstring Templates

**Module**:
```python
"""
Brief one-line description.

Longer description of purpose, main capabilities, and fit in the larger system.

The module contains:
* :class:`ClassName` - Brief description
* :func:`function_name` - Brief description

.. note::
   Important caveats about usage or requirements.

Example::

    >>> from module import something
    >>> result = something()
    >>> result
    expected_output
"""
```

**Class**:
```python
class ClassName:
    """
    Brief one-line description.

    Longer explanation of purpose, responsibilities, and usage patterns.

    :param param_name: Description of constructor parameter
    :type param_name: ParamType
    :param optional_param: Description, defaults to ``default_value``
    :type optional_param: ParamType, optional

    :ivar instance_var: Description of instance variable
    :vartype instance_var: VarType
    :cvar class_var: Description of class variable
    :type class_var: ClassVarType

    Example::

        >>> obj = ClassName(param_name=value)
        >>> obj.method()
        expected_result
    """
```

**Function/Method**:
```python
def function_name(param1: Type1, param2: Type2 = default) -> ReturnType:
    """
    Brief one-line description.

    Longer explanation of behavior, algorithm, or important details.

    :param param1: Description of the first parameter
    :type param1: Type1
    :param param2: Description, defaults to ``default``
    :type param2: Type2, optional
    :return: Description of what is returned
    :rtype: ReturnType
    :raises ExceptionType: Description of when raised
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.

    Example::

        >>> result = function_name(arg1, arg2)
        >>> result
        expected_output
    """
```

**Dataclass**:
```python
@dataclass
class DataClassName:
    """
    Brief description of what this dataclass represents.

    :param field1: Description of the first field
    :type field1: Type1
    :param field2: Description of the second field
    :type field2: Type2

    Example::

        >>> obj = DataClassName(field1=value1, field2=value2)
        >>> obj.field1
        value1
    """
    field1: Type1
    field2: Type2
```

### Parameter, Return, and Exception Patterns

```python
:param param_name: Description                           # Required parameter
:type param_name: type_annotation
:param param_name: Description, defaults to ``value``   # Optional parameter
:type param_name: type_annotation, optional
:return: Description of what is returned
:rtype: ReturnType
:return: ``None``.                                       # For None-returning functions
:rtype: None
:raises ExceptionType: When this exception is raised
:raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
```

### Cross-References and Markup

- `:class:`ClassName``, `:func:`function_name``, `:meth:`Class.method_name``
- `:mod:`module.name``, `:exc:`ExceptionType``, `:data:`variable_name``, `:attr:`attribute_name``
- Instance variables: `:ivar:` / `:vartype:`; Class variables: `:cvar:` / `:type:`
- Inline code: double backticks `` ``value`` `` (not single backticks)

### Inline Markup Boundary Rules

**CRITICAL**: In reST/Sphinx, inline strong emphasis (`**bold**`) and inline literals (``code``) need valid
boundaries on both sides. If plain text touches the opening marker from the left or the closing marker from the right,
the markup may fail to parse and render literally.

**Incorrect**:
- `prefix**text**`
- `**text**suffix`
- `建模**层次状态机**。`
- `前文``code``后文`
- ``code``suffix
- `中文**加粗**文本`
- `中文``code``文本`

**Correct**:
- `prefix **text**`
- `**text** suffix`
- `prefix ``code`` suffix`
- `建模\ **层次状态机**。`
- `**text**.`
- `前文 **加粗** 后文`
- `前文 ``code`` 后文`
- `**加粗**\ 后文`
- ``code``\ 后文

**Preferred Safe Default For Chinese Prose Or Tight Inline Text**:
- `前文\ **加粗**\ 后文`
- `前文\ ``code``\ 后文`

If visible whitespace or punctuation is acceptable, plain spaces or punctuation are fine. If you want the rendered
output to stay visually tight to surrounding Chinese text, prefer `\ ` on both sides as the safest default. Do not
use single backticks for inline code in reST.

**Additional Practical Rules From This Codebase**:
- Do not assume full-width Chinese punctuation is a safe boundary for inline markup. In practice, patterns like
  `**text**（...）` and ``code``（...） may still render as problematic in Sphinx/docutils.
- For inline literals specifically, the most common failure pattern in Chinese docs is a valid opening marker with an
  invalid trailing boundary, especially ``literal`` immediately followed by full-width `（`.
- Common real failure patterns:
  - `**普通详细级别**（默认）`
  - `**1. pip 安装**（推荐）：`
  - `1. **本地事件**（``::``）：作用域限定于源状态的命名空间`
  - `**场景 1：初始进入**（``HierarchyDemo -> Parent -> ChildA``）`
  - ``A.enter``（未定义）
  - `执行 ``A.enter``（未定义）`
  - `检查转换：``A -> B :: Go``（事件匹配！）`
  - `**整数：** ``123``、``0xFF``（十六进制）、``0b1010``（二进制）`
  - `- ``variable_display_mode`` (str)：显示模式 - ``'note'``、``'legend'`` 或 ``'hide'``（默认：``'legend'``）`
- Safe fixes:
  - `**普通详细级别**\ （默认）`
  - `**1. pip 安装**\ （推荐）：`
  - `1. **本地事件**\ （``::``）：作用域限定于源状态的命名空间`
  - `**场景 1：初始进入**\ （``HierarchyDemo -> Parent -> ChildA``）`
  - ``A.enter``\ （未定义）
  - `执行 ``A.enter``\ （未定义）`
  - `检查转换：``A -> B :: Go``\ （事件匹配！）`
  - `**整数：** ``123``、``0xFF``\ （十六进制）、``0b1010``\ （二进制）`
  - `- ``variable_display_mode`` (str)：显示模式 - ``'note'``、``'legend'`` 或 ``'hide'``\ （默认：``'legend'``）`

**Inline Literal Repair Heuristic**:
- If HTML shows a literal leaking as raw ```` and the source already has a valid left boundary, first check whether the
  closing `` is glued to `（`.
- In that case, prefer the minimal repair: add trailing `\ ` after the literal, for example
  `执行 ``A.enter``\ （未定义）`.
- If multiple literals appear in one sentence, repair each bad trailing boundary independently.

**Verification Rule**:
- For bulk `.rst` cleanup, do not trust source regex checks alone.
- Rebuild Sphinx HTML and inspect rendered output for `class="problematic"` spans or literal `**` / ```` that leaked
  through parsing.
- Treat generated HTML as the source of truth when deciding whether inline markup cleanup is complete.

### Examples in Docstrings

```python
Example::

    >>> from pyfcstm.utils.text import normalize
    >>> normalize("Hello World!")
    'Hello_World'
    >>> normalize("test-case")
    'test_case'
```

For CLI examples, use `$` prefix without `>>>`. For FCSTM DSL in Sphinx docs, use `.. code-block:: fcstm`.
For including external FCSTM files: `.. literalinclude:: example.fcstm` with `:language: fcstm`.

**Real example from codebase** ([pyfcstm/entry/generate.py](pyfcstm/entry/generate.py)):
```python
def generate(input_code_file: str, template_dir: str, output_dir: str, clear_directory: bool) -> None:
    """
    Generate code from a state machine DSL file using templates.

    This command reads the DSL file as bytes, decodes it with
    :func:`pyfcstm.utils.auto_decode`, parses it with the grammar entry
    ``state_machine_dsl``, converts the AST to a state machine model, and
    renders output using :class:`pyfcstm.render.StateMachineCodeRenderer`.

    :param input_code_file: Path to the input DSL code file.
    :type input_code_file: str
    :param template_dir: Path to the directory containing templates.
    :type template_dir: str
    :param output_dir: Path to the directory where generated code will be written.
    :type output_dir: str
    :param clear_directory: Whether to clear the output directory before rendering.
    :type clear_directory: bool
    :return: ``None``.
    :rtype: None
    :raises pyfcstm.dsl.error.GrammarParseError: If DSL parsing fails.
    :raises IOError: If reading the input file or writing output files fails.

    Example::

        $ pyfcstm generate -i ./machine.dsl -t ./templates -o ./out --clear
    """
```

### Special Directives

```python
.. note::
   Important information or caveats about usage.
.. warning::
   Critical warnings about potential issues or dangers.
```

### Checklist

- [ ] Brief one-line summary at the top
- [ ] Longer explanation for non-trivial functions/classes
- [ ] All params documented with `:param:` and `:type:`
- [ ] Return value with `:return:` and `:rtype:`
- [ ] All exceptions with `:raises:`
- [ ] Cross-references use reST roles (`:class:`, `:func:`, etc.)
- [ ] Examples for public APIs
- [ ] Inline code uses double backticks
- [ ] Inline `**strong**` and ``literal`` markup has valid left/right boundaries; in Chinese prose or tight inline text, prefer `\ **strong**\` and `\ ``literal``\`
- [ ] Do not leave closing `**` or ```` directly before full-width Chinese punctuation such as `（`; use `\ ` when in doubt
- [ ] For large markup cleanup, verify against generated HTML and look for `class="problematic"`
- [ ] Optional params marked with `, optional`; defaults shown in description

### Anti-Patterns

**DON'T**: Google/NumPy style; omit types (always include `:type:` and `:rtype:`); single backticks for inline code;
`**strong**` or ``literal`` markup glued directly to adjacent text; assuming only the trailing boundary matters;
vague descriptions ("Does something");
bare class/function names without reST roles; volatile implementation details.

**DO**: reST format consistently; explain "why" and "what"; use cross-references; include practical examples;
update docstrings when code changes.

### Common Patterns in pyfcstm

**AST and Model Conversions**:
```python
def to_ast_node(self) -> dsl_nodes.ASTNode:
    """
    Convert this model object to an AST node representation.

    :return: An AST node representing this object.
    :rtype: pyfcstm.dsl.node.ASTNode
    """
```

**State Machine Domain Concepts**: Use domain-specific terminology consistently: states, transitions, events,
lifecycle actions, guards, effects, composite states, leaf states, aspect actions.

**Template and Rendering Context**: Document Jinja2 template integration and expression rendering styles when relevant.

**Real example from codebase** ([pyfcstm/render/render.py](pyfcstm/render/render.py)):
```python
class StateMachineCodeRenderer:
    """
    Renderer for generating code from state machine models using templates.

    This class handles rendering of state machine models into code by combining
    a template directory with a configuration file. It creates a Jinja2
    environment, registers expression rendering styles, and maps template files
    to rendering operations or file copying operations.

    :param template_dir: Directory containing the templates and configuration
    :type template_dir: str
    :param config_file: Name of the configuration file within the template directory,
        defaults to ``'config.yaml'``
    :type config_file: str, optional

    :ivar template_dir: Absolute path to the template directory
    :vartype template_dir: str
    :ivar env: Jinja2 environment used for rendering
    :vartype env: jinja2.Environment

    Example::

        >>> renderer = StateMachineCodeRenderer('./templates')
        >>> renderer.render(my_state_machine, './output', clear_previous_directory=True)
    """
```

## Development Notes

### LLM-Based Documentation Generation

```bash
# RST generation (no additional setup needed)
make rst_auto                    # Generate RST for all Python files
make rst_auto RANGE_DIR=model    # Specific directory
python auto_rst_top_index.py -i pyfcstm -o docs/source/api_doc.rst

# LLM features (requires: pip install hbllmutils + configure .llmconfig.yaml)
make docs_auto    # Generate Python docstrings
make todos_auto   # Complete TODO comments
make tests_auto   # Generate unit tests
make docs_auto AUTO_OPTIONS="--model-name deepseek-V3 --param max_tokens=200000"
```

Common `AUTO_OPTIONS`: `--param max_tokens=N`, `--model-name MODEL`, `--no-ignore-module pyfcstm`, `--timeout SECONDS`.

Key file: `.llmconfig.yaml` (gitignored, contains API credentials; copy from
[.llmconfig.yaml.example](.llmconfig.yaml.example)).

#### File Structure

```
pyfcstm/
├── auto_rst.py                    # RST generation from Python files
├── auto_rst_top_index.py          # Top-level API index generation
├── .llmconfig.yaml.example        # Example LLM configuration
├── .llmconfig.yaml                # Your LLM configuration (gitignored)
├── LLM_DOCS_README.md             # Detailed documentation
└── docs/source/api_doc/           # Generated RST files
```

#### Best Practices

1. **Start with RST Generation** - Generate RST files first to establish structure
2. **Review LLM Output** - Always review generated docstrings and code before committing
3. **Incremental Updates** - Use `RANGE_DIR` to target specific modules
4. **Version Control** - Commit generated documentation separately from code changes
5. **API Token Security** - Never commit `.llmconfig.yaml` to git

**Commit Message Style**: Follow the dominant repository convention from recent history.

- For normal commits, prefer `type(scope): imperative summary`, such as
  `feat(model): add StateMachine.resolve_state path resolver` or
  `test(utils): strengthen fixed-int tests with live Z3 BitVec alignment`.
- Use short lowercase types such as `feat`, `fix`, `docs`, `test`, `refactor`, `chore`; keep the scope lowercase when present
  (`model`, `solver`, `utils`, `makefile`, `verify`, etc.). Omit the scope only when the change genuinely spans the whole repository.
- Write the summary as a concise imperative phrase starting with a lowercase verb (`add`, `update`, `improve`, `align`, `compress`,
  `clean up`); do not add a trailing period.
- For non-trivial changes, add a blank line and then a body. Match the common repository pattern:
  a short overview sentence or paragraph first, followed by `-` bullet points for concrete changes, tests, compatibility notes,
  docs updates, or behavior clarifications.
- When a bullet needs to wrap, continue it on the next line with indentation rather than starting a new bullet.
- Preserve standard trailers when applicable, especially `Co-Authored-By: Name <email>`.
- Merge commits should keep the generated style used in history, such as `Merge branch 'main' into dev/...` or
  `Merge pull request #52 from HansBug/dev/fixed`.

See [pyfcstm/llm/fcstm_grammar_guide.md](pyfcstm/llm/fcstm_grammar_guide.md) for the packaged LLM grammar guide.

### `gh` / `glab` Identity Rule

Any `gh` or `glab` invocation that acts on behalf of a user (viewing private data, creating issues/PRs/MRs, commenting, approving, pushing releases, etc.) MUST run as an identity whose login/email matches the current repo's `git config user.name` and `git config user.email`. Running under whatever account happens to be "active" in the CLI is NOT acceptable — tokens silently carry over the wrong identity across repos and produce PRs/comments authored by the wrong user.

Mandatory procedure before running `gh` / `glab`:

1. Read the repo identity:

   ```bash
   git -C . config user.name
   git -C . config user.email
   ```

2. Enumerate CLI-available identities and confirm one matches BOTH the name and the email above:

   ```bash
   gh auth status           # GitHub: lists all logged-in accounts, active flag, scopes
   glab auth status         # GitLab: lists hosts and usernames
   ```

   If no authenticated identity matches the repo's `user.name` / `user.email`, STOP. Do not fall back to the currently active account. Ask the user to `gh auth login` / `glab auth login` with the correct identity, or to tell you which stored identity should map to this repo.

3. Once the matching identity is known, DO NOT rely on `gh auth switch` — that mutates global CLI state and can leak into unrelated repos/sessions. Instead, resolve that identity's token and force it inline as an environment variable directly in front of every `gh` / `glab` command in the same command line. This scopes the override to that single process.

Concrete executable examples:

```bash
# GitHub — always prefix with the resolved token for the matching login.
# The --user flag picks the exact stored account, regardless of which is "active".
GH_TOKEN="$(gh auth token --user HansBug)" gh pr list
GH_TOKEN="$(gh auth token --user HansBug)" gh pr create --title "..." --body "..."
GH_TOKEN="$(gh auth token --user HansBug)" gh pr view 123 --json title,author,state
GH_TOKEN="$(gh auth token --user HansBug)" gh api user --jq '.login'   # verify: must print HansBug

# Multiple gh calls in one shell line — prefix each, or export for a single subshell:
( export GH_TOKEN="$(gh auth token --user HansBug)"; \
  gh pr list && gh pr view 123 )

# GitLab — same pattern. glab honors GITLAB_TOKEN (and GITLAB_HOST for self-hosted).
GITLAB_TOKEN="$(glab config get token -h gitlab.com)" glab mr list
GITLAB_TOKEN="$(glab config get token -h gitlab.example.com)" GITLAB_HOST=gitlab.example.com \
  glab mr create --title "..." --description "..."
```

Verification step (do this once per session, before the first state-changing call):

```bash
# GitHub: the login printed here MUST equal `git config user.name` (or its mapped GitHub login),
# and `gh api user --jq '.email'` — when non-null — MUST equal `git config user.email`.
GH_TOKEN="$(gh auth token --user <login>)" gh api user --jq '.login, .email'

# GitLab:
GITLAB_TOKEN="$(glab config get token -h gitlab.com)" glab api user --jq '.username, .email'
```

Hard rules:

- Never run `gh pr create`, `gh pr merge`, `gh pr comment`, `gh release create`, `gh issue create/comment`, `glab mr create/merge/comment`, `glab issue create/comment`, or any other state-changing call without the inline token prefix scoped to the matching identity.
- Never use `gh auth switch` / `glab auth set-default` as a substitute — those are process-global and violate this rule.
- If `gh auth token --user <login>` returns empty or errors, STOP and surface the problem to the user; do not silently fall through to the active account.
- Read-only, non-sensitive queries that do not depend on identity (e.g., `gh api repos/owner/repo --jq '.default_branch'` on a public repo) may skip the prefix, but when in doubt, prefix anyway — the cost is zero.

### ANTLR Grammar Modifications

When modifying [pyfcstm/dsl/grammar/GrammarParser.g4](pyfcstm/dsl/grammar/GrammarParser.g4) or
[pyfcstm/dsl/grammar/GrammarLexer.g4](pyfcstm/dsl/grammar/GrammarLexer.g4):

1. Ensure Java is installed
2. `make antlr` - download ANTLR jar (only needed once)
3. `make antlr_build` - regenerate parser code
4. Update [pyfcstm/dsl/listener.py](pyfcstm/dsl/listener.py) and [pyfcstm/dsl/node.py](pyfcstm/dsl/node.py) if grammar structure changes
5. Update syntax highlighting:
   - [pyfcstm/highlight/pygments_lexer.py](pyfcstm/highlight/pygments_lexer.py) (Pygments lexer, reference implementation)
   - [editors/fcstm.tmLanguage.json](editors/fcstm.tmLanguage.json) (TextMate grammar)
6. `python editors/validate.py` - verify all 20+ checkpoints pass (100% required)

**Operator Ordering**: Multi-character operators before single-character ones:
- `**` before `*`; `<<` before `<`; `<=`, `>=`, `==`, `!=` before `<`, `>`, `!`; `&&`, `||` before `!`

**Adding New Keywords**: [pyfcstm/dsl/grammar/GrammarParser.g4](pyfcstm/dsl/grammar/GrammarParser.g4) or
[pyfcstm/dsl/grammar/GrammarLexer.g4](pyfcstm/dsl/grammar/GrammarLexer.g4) → `make antlr_build` →
update [pyfcstm/highlight/pygments_lexer.py](pyfcstm/highlight/pygments_lexer.py) (appropriate `words()` group) →
update [editors/fcstm.tmLanguage.json](editors/fcstm.tmLanguage.json) (keywords repository section) →
`python editors/validate.py`.

### Template Development

Current built-in template layout and release flow:

- Repository template sources live under [templates/](templates/)
- Packaged built-in template assets live under [pyfcstm/template/](pyfcstm/template/)
- `make tpl` refreshes packaged template zip assets and `index.json`
- After modifying repository template sources, run `make tpl` before template-related unit tests so the packaged built-in templates used by tests are up to date
- The CLI extracts built-in templates first, then hands the extracted directory to `StateMachineCodeRenderer`
- The current reference implementation is [templates/python/](templates/python/), with tests in
  [test/template/python/](test/template/python/)

Template directories must contain:
- `config.yaml`: Defines `expr_styles`, `stmt_styles`, `globals`, `filters`, `tests`, `ignores`
- `.j2` files: Jinja2 templates with state machine model as context
- Static files: Copied directly to output (preserve directory structure)

Key template objects:
- `model`, `model.walk_states()`
- `state.name`, `state.is_leaf_state`, `state.transitions`, `state.parent`
- `transition.from_state`, `transition.to_state`, `transition.guard`, `transition.effects`

Use `{{ expr | expr_render(style='c') }}` to render expressions in target language syntax.
Use `{{ stmt | stmt_render(style='python') }}` or `{{ action.operations | stmts_render(style='python') }}`
for executable operation blocks. Do not use `operation_stmt_render` / `operation_stmts_render` when the goal is target-language runtime code; those are for DSL echo text.

For built-in template work, the current design bar is defined by the `python` template:

- Behavioral parity with `pyfcstm.simulate.SimulationRuntime` is a hard requirement, not a best effort. Future built-in language templates should be validated against the simulator with alignment tests.
- Full semantic-alignment coverage is required when a built-in runtime template claims parity with the simulator. Do not ship a new language template on a cherry-picked subset of alignment cases; every applicable alignment scenario and representative example expected for that runtime family must be covered unless an exclusion is explicitly justified and documented.
- Generated artifacts should be as self-contained as the target language reasonably allows. Prefer standard-library or language-core features and avoid introducing third-party runtime dependencies unless there is a very strong reason.
- The target language version and platform envelope should be broad and explicit. Match the spirit of the Python template: low dependency footprint, wide version compatibility, and cross-platform behavior.
- Do not require users to edit generated files to implement abstract behavior. Instead, expose stable, language-idiomatic extension points for abstract actions and related hooks. The Python template uses protected hook override methods as the reference pattern.
- Preserve naming clarity for generated extension points so DSL authors can map states, actions, and abstract behavior back to code quickly, ideally with IDE completion support.
- Keep public integration surfaces, generated README files, and generated-file guidance clear and inspectable. Generated
  implementation bodies may be mechanical and performance-oriented, but they must still look professional enough for
  downstream integration.
- Ensure the final generated code, generated support files, and generated README examples satisfy the corresponding
  pragmatic formatter flow for representative outputs. Formatter/linter gates are not absolute style goals; rare
  formatter-only edge cases may be documented as non-blocking when runtime semantics, performance, compatibility, and
  simulator/template alignment remain correct.
- For changes to [templates/python/](templates/python/), verify representative generated `machine.py` outputs with both `ruff check` and
  `ruff format --check`. Ordinary representative output that fails lint or formatting is not ready; rare extreme
  formatter-only rewrites fall under the non-blocking exception policy above when explicitly justified.
- When adding a new built-in template, update all of the following together: [templates/](templates/), packaged template assets, CLI/template metadata, maintainer docs, generated docs if applicable, and the corresponding tests.

### Testing Strategy

- Tests in [test/](test/); use `@pytest.mark.unittest`
- Unit tests must not depend on local files ignored by version control (for example, gitignored files).
- Unit test suites must be strictly self-contained within their owning test tree. Python tests may use fixtures,
  helpers, and expected data under [test/](test/), and jsfcstm tests may use fixtures, helpers, and expected data under
  [editors/jsfcstm/test/](editors/jsfcstm/test/); neither side may read from, execute, import from, or assume the
  presence of the other side's test tree. A Python unit test must still run if
  [editors/jsfcstm/](editors/jsfcstm/) is removed, and a jsfcstm unit test must still run if [test/](test/) is removed.
- When both Python and jsfcstm need to cover the same behavior, duplicate the DSL text, expected diagnostics,
  snapshots, or fixtures as checked-in literals/files inside each side's own test tree. Do not share unit-test
  fixtures across those trees, do not shell out to the other runtime (for example Python tests invoking Node.js or
  jsfcstm tests invoking Python), and do not rely on build artifacts from the other side.
- Unit tests may import the production code under test and use production assets through the public runtime/build
  entry points, but test-only data, helper scripts, and golden outputs must live in the corresponding test tree.
- Unit tests under [test/](test/) should keep production [pyfcstm/](pyfcstm/) behavior as the primary code under test, with
  test-tree files acting as fixtures, helpers, schemas, harnesses, and expected data for that behavior.
  It is acceptable to test fixture loaders, schema validation, and harness behavior when those checks protect
  production-behavior fixture execution or prevent test-semantics drift. Do not add pytest cases whose primary
  assertion target is only test-tree documentation or maintenance metadata, such as README inventory tables or
  migration indexes. If fixture inventories, test documentation, or other test-tree maintenance data need executable
  validation, put that check in a maintenance command outside the unit-test suite (for example under [tools/](tools/)) and run
  it explicitly.
- Python unit tests must enter built-in template behavior through production package/runtime surfaces. Tests may use
  packaged template assets through `pyfcstm.template`, `pyfcstm.template.extract_template(...)`,
  `pyfcstm.template.list_templates()`, `pyfcstm.template.get_template_info(...)`,
  `StateMachineCodeRenderer` pointed at an extracted packaged template, or CLI paths such as
  `pyfcstm generate --template ...`. Tests may also create throwaway templates under their own temporary directories or
  under [test/](test/) when the test target is the renderer itself.
- Python unit tests must not directly read, render, compare, or assert against repository root `templates/` source
  directories. Avoid source-layout shortcuts such as `_REPO_ROOT / "templates"`,
  `Path(__file__).parents[...] / "templates"`, or `os.path.join(..., "templates")` in [test/](test/) when the behavior
  under test can be reached through packaged template assets or public CLI/runtime entry points.
- Python unit tests must not import `tools.*`, execute `tools.*`, or assert private helper behavior from maintenance
  scripts. Packaging, release, source-template packaging, source-install smoke, symlink/stub resolution, and similar
  maintenance checks should live as explicit commands under [tools/](tools/) or Makefile targets, not as default
  `pytest -m unittest` cases. Do not delete that coverage when migrating it out of pytest; keep a reproducible
  maintenance command.
- Keep generated README executable documentation tests in pytest when they validate runnable quick starts,
  compile/run commands, formatter-friendly code blocks, public API examples, or integration commands emitted by
  generated artifacts. Do not use pytest primarily to assert repo-source maintainer README wording, prose inventories,
  comment-only text, or documentation synchronization that is not production behavior.
- Native template tests are part of the unit-test contract when they verify generated runtime behavior. C / C++ /
  C++ wrapper native compile, native run, CMake, ctypes, formatter, and native alignment checks must be preserved when
  their inputs are generated through packaged template or public API paths.
- `make unittest` intentionally depends on `make tpl` so packaged built-in template assets are refreshed before the
  Python unit-test suite runs. Do not remove that dependency merely to avoid packaging work in tests; instead, keep
  pytest on packaged/public inputs and move source-template maintenance coverage to explicit tooling commands.
- Run `make test_boundary_check` when changing test infrastructure, template tests, maintenance tooling, or
  repository guidance that affects the pytest boundary. This command is a pytest-external guard for direct `tools.*`
  imports/execution, repo-root `templates/` access, and source-install smoke markers under [test/](test/).
- Shared test utilities and fixtures in [test/testings/](test/testings/)
- Sample DSL files in [test/testfile/sample_codes/](test/testfile/sample_codes/) (auto-generate tests via `make sample`)
- Negative cases in [test/testfile/sample_neg_codes/](test/testfile/sample_neg_codes/)
- Test timeout: 300 seconds (configured in [pytest.ini](pytest.ini))
- Built-in template coverage lives under [test/template/](test/template/)
- For built-in templates, keep at least these layers when applicable:
  renderer/template extraction tests, generated-artifact tests, runtime-alignment tests against `SimulationRuntime`, and CLI path tests for `pyfcstm generate --template ...`
- For runtime templates that mirror an existing built-in runtime family, treat the reference alignment corpus as the minimum bar. Do not silently drop examples or keep only the easy cases; the final template is not ready until the full intended semantic-alignment set passes.
- For `C` / `C++` template unit tests and generated-runtime build checks, use `cmake` as the build driver instead of trying to hand-discover or manually orchestrate the host C compiler toolchain. The test contract should be expressed in terms of `cmake` configure/build success.

### Dependencies

Core ([requirements.txt](requirements.txt)): `antlr4-python3-runtime==4.9.3`, `jinja2>=3`, `pyyaml`, `click>=8`, `hbutils>=0.14.0`,
`pathspec`, `z3-solver<=4.15.4` (constraint solver), `prompt_toolkit>=3.0.0` + `rich>=13,<14` (simulation REPL UI),
`pygments>=2.10.0` (syntax highlighting), `unidecode`, `chardet`. Development
([requirements-dev.txt](requirements-dev.txt)): `ruff`.

### Documentation Editing

**CRITICAL RULE**: Always edit source files only. Never edit generated files directly—they will be overwritten.

#### Documentation Authoring Discipline

Before adding, restructuring, or substantially expanding user-facing documentation, read
[docs/documentation_authoring.md](docs/documentation_authoring.md). That file is repository-maintainer guidance, not a
Sphinx toctree page; it is intentionally made discoverable through this `CLAUDE.md` entry.

Documentation changes must start from a concrete coverage inventory and must preserve the separation between Tutorials,
How-to Guides, Explanations, and Reference material. Use real commands, real outputs, explicit failure boundaries,
traceable generated resources, synchronized language variants where applicable, and the Chinese terminology discipline
below. Review documentation PRs with the C/I/M criteria in that guide, in addition to the reST, generated-file, and
multilingual rules in this section.

#### Documentation Structure

Files in [docs/source/](docs/source/):
- `*.rst`/`*.md`: Documentation pages
- `*.mk`: Makefile fragments for resource generation
- [conf.py](docs/source/conf.py): Sphinx configuration
- Subdirectories include [tutorials/](docs/source/tutorials/), [api_doc/](docs/source/api_doc/),
  [_static/](docs/source/_static/), and [_templates/](docs/source/_templates/).

#### reST Inline Markup Rules

**CRITICAL**: For `.rst` content, check both the left boundary of the opening marker and the right boundary of the
closing marker for inline strong emphasis (`**text**`) and inline literals (``code``).

- Wrong: `prefix**text**`, `**text**suffix`, `建模**层次状态机**。`, `前文``code``后文`
- Correct: `prefix **text**`, `**text** suffix`, `建模\ **层次状态机**。`, `前文 ``code`` 后文`
- Safe default for Chinese prose: `前文\ **加粗**\ 后文`, `前文\ ``code``\ 后文`
- Do not trust full-width Chinese punctuation as a safe boundary. Real broken cases in this repo included:
  - `**普通详细级别**（默认）`
  - `**1. pip 安装**（推荐）：`
  - `1. **本地事件**（``::``）：...`
  - `**场景 1：初始进入**（``HierarchyDemo -> Parent -> ChildA``）`
  - ``A.enter``（未定义）
  - `执行 ``A.enter``（未定义）`
  - `检查转换：``A -> B :: Go``（事件匹配！）`
  - `**整数：** ``123``、``0xFF``（十六进制）、``0b1010``（二进制）`
  - `- ``variable_display_mode`` ... ``'hide'``（默认：``'legend'``）`
- Safe forms for those cases:
  - `**普通详细级别**\ （默认）`
  - `**1. pip 安装**\ （推荐）：`
  - `1. **本地事件**\ （``::``）：...`
  - `**场景 1：初始进入**\ （``HierarchyDemo -> Parent -> ChildA``）`
  - ``A.enter``\ （未定义）
  - `执行 ``A.enter``\ （未定义）`
  - `检查转换：``A -> B :: Go``\ （事件匹配！）`
  - `**整数：** ``123``、``0xFF``\ （十六进制）、``0b1010``\ （二进制）`
  - `- ``variable_display_mode`` ... ``'hide'``\ （默认：``'legend'``）`

If you do not want visible spaces in rendered Chinese text, prefer `\ ` on both sides as the default safe pattern.

Do not use single backticks for inline code in reST. Use double backticks only: ``code``.

#### reST Verification Workflow

- When fixing inline markup at scale, rebuild Sphinx HTML instead of relying only on source scans.
- Preferred check command:
  `NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=zh sphinx-build -b html docs/source /tmp/pyfcstm-html-check-zh`
- Then inspect generated HTML for parse failures:
  `rg -n 'class="problematic"|\\*\\*[^<]*\\*\\*' /tmp/pyfcstm-html-check-zh -g '*.html'`
- If you are specifically checking inline literals, also use:
  `rg -n '<span class="problematic"[^\\n]*>``</span>|<span class="problematic"[^\\n]*>`</span>' /tmp/pyfcstm-html-check-zh -g '*.html'`
- Use rendered HTML as the final authority for whether `**` / ```` issues are actually fixed.

#### File Generation Rules

| Source | Generated |
|--------|-----------|
| `*.fcstm` | `*.fcstm.puml` → `*.fcstm.puml.{png,svg}` |
| `*.puml` | `*.puml.{png,svg}` |
| `*.gv` | `*.gv.{png,svg}` |
| `*.demo.py` | `*.demo.py.txt` |
| `*.demox.py` | `*.demox.py.{txt,err,exitcode}` |
| `*.plot.py` | `*.plot.py.svg` |
| `*.demo.sh` | `*.demo.sh.txt` |
| `*.demox.sh` | `*.demox.sh.{txt,err,exitcode}` |
| `*.ipynb` | `*.result.ipynb` |

#### Build Commands

```bash
# From docs/source/
make -f all.mk build      # Generate all resources (diagrams, demos, notebooks)
make -f all.mk clean      # Clean all generated resources
make -f all.mk cleanplt   # Clean plot outputs only

# From docs/
make html       # Build HTML documentation (includes resource generation)
make contents   # Generate resources only (without building HTML)
make prod       # Production build with versioning
make clean      # Clean generated resources
make doc_clean  # Clean Sphinx build output only
```

#### DO and DO NOT

**DO NOT** edit generated files:
- `*.fcstm.puml`, `*.fcstm.puml.{png,svg}` (from `.fcstm`)
- `*.puml.{png,svg}` (from `.puml`)
- `*.gv.{png,svg}` (from `.gv`)
- `*.py.txt`, `*.py.err`, `*.py.exitcode`, `*.py.svg` (from demo scripts)
- `*.sh.txt`, `*.sh.err`, `*.sh.exitcode` (from shell scripts)
- `*.result.ipynb` (from `.ipynb`)
- [docs/source/index.rst](docs/source/index.rst) (generated during build—do not edit directly)

**DO** edit source files:
- `*.fcstm` for FSM state machines
- `*.puml` only if no corresponding `*.fcstm` exists
- `*.gv` for Graphviz diagrams
- `*.demo.py`, `*.demox.py`, `*.plot.py`, `*.demo.sh`, `*.demox.sh` for demos
- `*.ipynb` for notebooks (with outputs cleared)
- `*.rst`, `*.md` for documentation text

Run `make contents` before committing Sphinx source or documentation resource changes that may refresh generated
outputs. For policy-only files outside the Sphinx tree, or prose-only changes that do not affect generated resources,
record why `make contents` is not applicable; otherwise run it and commit any intentional generated updates.

#### Example Workflow

```bash
# Editing an FSM diagram:
vim docs/source/tutorials/example.fcstm           # Edit source
make -f docs/source/fcstms.mk SOURCE=docs/source build  # Regenerate
cd docs && make html                              # Build docs

# Editing a demo script:
vim docs/source/tutorials/example.demo.py         # Edit source
make -f docs/source/demos.mk SOURCE=docs/source build   # Regenerate output
cd docs && make html                              # Build docs
```

#### Documentation Dependencies

```bash
pip install -r requirements.txt
pip install -r requirements-doc.txt
```

Requires: `sphinx`, `sphinx-multiversion`, `plantumlcli`, `graphviz` (`dot`), `jupyter`, `nbconvert`.

### Multilingual Documentation Support

Language selection via `READTHEDOCS_LANGUAGE` env var (default `en`). [docs/source/conf.py](docs/source/conf.py) copies
`index_<lang>.rst` → `index.rst` at build time. Language codes normalized (`zh-CN`, `zh_CN` → `zh`).

#### Chinese Technical Terminology Discipline

Chinese documentation should read as Chinese prose, not as English prose with Chinese glue words. In ordinary Chinese
sentences, prefer Chinese technical terms. When an English term is genuinely needed for precision, write it only at the
first occurrence on the same page as ``中文术语（English term）`` and use the Chinese term alone afterwards.

Examples:

- First occurrence: ``组合转换（combo transition）``; later occurrences: ``组合转换``.
- First occurrence: ``强制转换（forced transition）``; later occurrences: ``强制转换``.
- First occurrence: ``伪中继状态（pseudo relay state）``; later occurrences: ``伪中继状态``.

This rule applies to normal paragraphs, list items, table headings, table cells, figure captions, and tutorial
explanations. Do not repeatedly sprinkle words such as ``combo``, ``forced``, ``relay``, ``runtime``, ``source``,
``target``, ``generated``, ``checked``, ``form``, or ``fact`` through Chinese prose after the concept has been
introduced.

Literal correctness still wins where text is not prose. Keep the following verbatim:

- code, commands, file paths, module paths, API names, identifiers, and generated output
- DSL keywords such as ``state``, ``enter``, ``during``, ``exit``, and ``effect``
- grammar rule names such as ``combo_transition_trigger``
- JSON field names, diagnostic codes, target template names, and target identifiers such as ``c``, ``cpp``, and
  ``python``
- short source-code labels where translating would make the example inaccurate

When reviewing Chinese documentation, treat unnecessary English-term repetition as a real documentation-quality issue.
If a page needs a terminology reminder, add a compact term list near the beginning and then keep later prose Chinese.

#### File Naming Conventions

- Root level: `index_en.rst`, `index_zh.rst` (sources); `index.rst` (generated—do not edit directly)
- Subsections: `index.rst` = English default; `index_zh.rst` = Chinese translation
- Shared resources (images, demos, code) should be language-agnostic (no duplication per language)
- API docs ([api_doc/](docs/source/api_doc/)) typically have no language variants

#### Build for Specific Language

```bash
cd docs && make html                          # English (default)
cd docs && READTHEDOCS_LANGUAGE=zh make html  # Chinese
```

#### Translation Workflow

When creating a new section:
1. Create English version as `index.rst`
2. Create Chinese version as `index_zh.rst`
3. Update parent index files to reference correct language versions:

```rst
.. toctree::
    :maxdepth: 2

    tutorials/installation/index_zh    # Chinese version reference
    tutorials/dsl/index                # English/default version reference
```

When translating: preserve all reST directives, file references, and code blocks; keep images/demos language-agnostic.

#### DO and DO NOT

**DO**:
- Create `index_zh.rst` for Chinese translations of subsections
- Use `index.rst` as English default for subsections
- Update parent index files to reference the correct language versions
- Test both language builds locally before committing

**DO NOT**:
- Edit [docs/source/index.rst](docs/source/index.rst) directly (generated at build time)
- Create `index_en.rst` for subsections (use `index.rst` as English default)
- Duplicate shared resources (images, demos) per language
- Translate code examples or API documentation (keep language-agnostic)

#### Translation Checklist

- [ ] Create `index_zh.rst` with translated content
- [ ] Preserve all reST directives (`:maxdepth:`, `.. literalinclude::`, etc.)
- [ ] Keep file references unchanged (images/demos work for all languages)
- [ ] Update parent index to reference `index_zh` for Chinese builds
- [ ] Verify shared resources are language-agnostic
- [ ] Test: `READTHEDOCS_LANGUAGE=zh make html`
- [ ] Check all links and references work correctly

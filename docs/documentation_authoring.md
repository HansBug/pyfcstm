# Documentation Authoring Discipline

This file is repository-maintainer guidance for writing and reviewing pyfcstm documentation. It is not a Sphinx page and is not listed in any `docs/source` toctree. It is made discoverable through `CLAUDE.md`; agents and maintainers should read it before adding, restructuring, or substantially expanding user-facing documentation.

The goal is to make documentation changes executable and reviewable, not merely well intentioned. A documentation PR is not ready just because it adds prose: the prose must have a clear page role, complete coverage for the affected capability, real examples, explicit boundaries, synchronized language variants where applicable, and verification evidence proportional to the change.

## Scope

These rules apply to documentation work for these current areas:

| Area | Typical source of truth | Typical documentation targets |
|---|---|---|
| DSL | `pyfcstm/dsl/`, `pyfcstm/model/`, `pyfcstm/diagnostics/`, `pyfcstm/llm/fcstm_grammar_guide.md` | `tutorials/dsl/`, `how_to/dsl/`, `reference/dsl/`, `explanations/dsl_semantics/` |
| Generation | `pyfcstm/entry/generate.py`, `pyfcstm/render/`, `pyfcstm/template/`, `templates/`, `test/template/` | `tutorials/generation/`, `how_to/generation/`, `reference/builtin_templates/`, `reference/template_config/`, template explanations |
| Inspect and diagnostics | `pyfcstm/entry/inspect.py`, `pyfcstm/diagnostics/`, inspect tests | `tutorials/inspect/`, `how_to/inspect/`, `reference/inspect_report/`, `reference/diagnostics_codes/`, `explanations/diagnostics/` |
| Simulation | `pyfcstm/simulate/`, `pyfcstm/entry/simulate/`, semantic fixture tests | `tutorials/simulation/`, `how_to/simulation/`, `explanations/execution_semantics/` |
| Visualization | PlantUML / visualization entry points, options objects, docs resources | `tutorials/visualization/`, `how_to/visualization/`, `reference/visualization_options/` |
| Templates | `pyfcstm/render/`, `pyfcstm/template/`, `templates/`, template tests | `how_to/templates/`, `reference/template_config/`, `reference/builtin_templates/`, `explanations/template_rendering/` |
| CLI workflows | `pyfcstm/entry/`, Click command definitions, CLI tests | `how_to/cli_workflows/`, `reference/cli/`, tutorials that run commands |
| Installation | Packaging metadata, requirements files, documented environment support | `how_to/installation/`, quick-start prerequisites |
| Grammar tooling | ANTLR grammar files, highlight lexers, editor tooling, validation scripts | `how_to/grammar_editor/`, `reference/grammar_tooling/`, `explanations/grammar_tooling/` |
| Architecture and execution explanations | `pyfcstm/` package layout, model/render/simulate/solver internals | `explanations/architecture/`, `explanations/execution_semantics/`, `explanations/template_rendering/` |

When a new documentation area appears, extend the table and use the same inventory template below instead of inventing a parallel process.

## Page roles

pyfcstm documentation follows four roles. Choose the role before writing the page.

| Role | Purpose | Must contain | Must not become |
|---|---|---|---|
| Tutorials | A guided first-success path for learning. | A small complete path, commands or code the reader can follow, observable stage feedback, and one or two links to deeper material. | A parameter catalog, schema dump, or exhaustive language reference. |
| How-to guides | Task recipes for users who already know what they want to do. | A task-shaped title, prerequisites, steps, commands or code, expected output, common mistakes, and next links. | A concept essay, broad tour, or mixed bag of unrelated tasks. |
| Explanations | Why the system behaves this way. | Semantics, ordering, design motivation, tradeoffs, diagrams or traces where useful, and boundaries. | A copy of syntax tables or CLI help with no reasoning. |
| Reference | Accurate facts readers can look up. | Tables, fields, defaults, legal and illegal forms, edge cases, diagnostics, and links to source facts. | A narrative tutorial or a vague overview that omits exact facts. |

If one page naturally wants to do all four jobs, split it. A short roadmap page may link to sibling pages, but it must not use a toctree to make those sibling pages children. Prefer splitting first by page role, then by capability family when one role page becomes too broad. For example, a DSL rewrite should normally keep a short learning tutorial, task-oriented how-to sections, a dense reference, and one or more semantic explanation pages rather than one giant mixed page.

## Module coverage inventory

Before writing or restructuring a module, create a coverage inventory. This can live in the PR body, a migration note, or the documentation file itself when it is useful to readers. Free-form prose is not enough; the inventory must cover every required field.

### Required inventory fields

| Field | Required content | Failure mode if omitted |
|---|---|---|
| Scope | The exact capability family being documented. | Reviewers cannot tell what is in or out. |
| Source facts | Code paths, tests, schema files, generated assets, or existing docs used as evidence. | The page may describe imagined behavior. |
| Capability list | The concrete commands, syntax forms, report fields, runtime behaviors, or template features in scope. | Coverage gaps hide inside prose. |
| Tutorial path | The smallest first-success path, if this module has one. | Tutorials become tours without a working endpoint. |
| How-to tasks | The concrete user tasks that need recipes. | Recipes become generic feature descriptions. |
| Explanation topics | The semantics, ordering, design choices, or boundaries that need conceptual treatment. | Explanations become restated reference tables. |
| Reference facts | Parameters, fields, defaults, allowed values, grammar forms, diagnostics, and compatibility facts. | Reference pages become incomplete overviews. |
| Boundaries and counterexamples | Unsupported forms, common invalid inputs, deployment risks, or edge cases. | Users cannot distinguish safe use from risky use. |
| Diagnostics and errors | Relevant diagnostic codes, stderr behavior, warning scope, or failure messages. | Error examples are missing or misleading. |
| Examples and resources | `.fcstm`, `.puml`, `.demo.*`, images, command snippets, expected output, and where they live. | Examples become unverifiable or detached from generation chains. |
| Migration and landing pages | Where old headings, old URLs, and moved assets now land. | Existing information appears lost. |
| Verification | Commands or review checks that prove the documentation matches the implementation. | “Done” cannot be audited. |

A missing required field is an Important review finding by default. It becomes Critical when the missing field can hide a behavior gap, incorrect fact, broken example, or lost migration content. A field is too vague to audit when it contains only a label, slogan, or one-word placeholder instead of concrete file paths, commands, pages, examples, or review checks. Treat vague fields as missing until the author adds enough detail for another maintainer to reproduce the reasoning.

### Example inventory: generation module

This example shows the minimum specificity expected for a non-DSL module.

| Field | Example content |
|---|---|
| Scope | Built-in and custom template generation through `pyfcstm generate`. |
| Source facts | `pyfcstm/entry/generate.py`, `pyfcstm/render/render.py`, `pyfcstm/template/`, `templates/`, `test/template/`, CLI help output. |
| Capability list | Generate from `--template python`; generate from custom `--template-dir` / `-t`; clear output with `--clear`; package built-in templates with `make tpl`; use generated README guidance. |
| Tutorial path | Generate the Python built-in template from one small `.fcstm` file, inspect generated files, run the generated runtime or a short smoke command if the tutorial scope includes execution. |
| How-to tasks | Choose a built-in template; use a custom template directory; refresh packaged template assets; clear an output directory safely; troubleshoot missing template names. |
| Explanation topics | Renderer pipeline, Jinja2 context, expression and statement rendering styles, packaged template extraction, built-in template parity expectations. |
| Reference facts | CLI options and aliases; built-in template names; template config keys; generated artifact expectations; formatter/linter expectations for generated artifacts. |
| Boundaries and counterexamples | Do not bypass packaged built-in templates by reading repository `templates/` from unit tests; do not promise C/C++ template behavior without native-toolchain checks; explain when custom template failures are user-template errors. |
| Diagnostics and errors | CLI errors for unknown template name, missing input, invalid DSL, output conflicts, and template render failures where current implementation exposes them. |
| Examples and resources | Reuse small checked-in `.fcstm` sources; keep long scripts as `.demo.*`; show short command/output snippets in prose; keep generated outputs produced by the documented build chain. |
| Migration and landing pages | If old generation tutorial sections move to how-to or reference pages, keep a landing page or migration table that answers where each old heading went. |
| Verification | `git diff --check`; CLI help comparison if options are documented; focused docs build if Sphinx pages changed; template tests or `make tpl` only when template assets or template docs are materially changed. |


## Merge-blocking depth gate for substantial documentation PRs

A substantial documentation PR is any change that adds, restructures, or materially expands user-facing documentation for
a capability family. These PRs must pass this depth gate before they can be called ready. This gate is intentionally strict:
if one required item is missing, the PR must stay open and the missing item must be fixed or explicitly removed from the PR
scope. A green Sphinx build, drift marker check, or reviewer skim is not enough.

### Depth multipliers for repair or hardening PRs

When a PR exists specifically because earlier documentation was too thin, the author must set an explicit depth target in
the PR body and judge the result against the starting page shape. The multiplier is a floor for information density and
coverage, not permission to pad prose.

| Page role | Minimum hardening target | What counts toward the target | What does not count |
|---|---:|---|---|
| Reference | At least five times the previous useful coverage for the affected capability, or a complete closed-list reference when the closed list is smaller. | Field/option tables, defaults, legal values, illegal values, examples, counterexamples, diagnostics, side effects, and implementation links. | Repeated overview prose, marker comments alone, copied CLI help with no boundary explanation. |
| How-to guide | At least three times the previous useful task coverage for affected tasks, unless every task already has concrete examples and outputs. | Task prerequisites, input files, commands, expected output or success signal, file side effects, troubleshooting, and next links. | Bare command lists, long opaque scripts in prose, references to examples without explaining what they prove. |
| Explanation | At least three times the previous useful explanatory coverage for affected concepts, unless the concept is already covered with traces and diagrams. | Data-flow traces, execution/order reasoning, design motivation, diagrams, boundary examples, and counterexamples. | Directory listings, repeated reference facts, architecture slogans, diagrams with no explanatory claim. |

If a page cannot or should not meet the multiplier because the scope is intentionally narrow, the PR body must state the
narrow scope and list which sibling page owns the omitted tutorial, how-to, explanation, or reference obligations. Without
that explicit ownership map, the omission is an Important finding by default.

### Reference-page requirements

Reference pages for command-heavy, schema-heavy, option-heavy, or field-heavy capabilities must be complete enough for a
reader to make a correct decision without reading implementation code. For every public command, option group, report
field group, template config key group, or visualization field group in scope, include all applicable items:

- exact spelling and aliases;
- required/optional status and default value;
- accepted value types and closed choices;
- legal examples, with at least three non-equivalent examples for tricky or high-impact items;
- illegal examples or counterexamples for common mistakes;
- stdout, stderr, exit status, file side effects, cache or overwrite behavior where the feature is command-facing;
- relevant diagnostics, warnings, policy rejections, or backend failures;
- implementation or generated-asset source facts used to verify the row.

A marker-based drift checker may prove that a row exists, but it does not prove that the prose is sufficient. The PR must
still include human review evidence for reference depth. For CLI and visualization references specifically, a hardening PR
must include short reproducible examples for success and failure paths, not only option tables.

### How-to-page requirements

Every task in a how-to page must be runnable or explicitly marked as schematic. Runnable tasks must include:

1. the starting assumption or input file;
2. the command or code to run;
3. a short expected output excerpt or an unambiguous success signal;
4. the file or directory side effect, if any;
5. the first troubleshooting step when the task fails;
6. a link to the relevant reference page for exhaustive facts.

A how-to page that only lists commands is not ready. If a command output is too long, show a small excerpt and say it is
truncated. If a long workflow is needed, put it in a `.demo.*` or `.demox.*` source file and show only focused snippets in
prose.

### Explanation-page requirements

Explanation pages must teach the mechanism, not just name the modules. For every complex behavior or architecture path in
scope, include at least one of the following, and prefer several when the concept is central:

- an end-to-end trace from input to output;
- an ordering table or timeline;
- a before/after, authored/expanded, or source/generated comparison;
- a diagram whose caption says exactly what it proves;
- a counterexample showing what the mechanism does not prove.

Diagrams are subject to visual review. If a diagram is added or materially reused, the PR must verify the rendered HTML,
check that the image is readable at the chosen width, and state what the figure proves. A figure that merely decorates the
page is not acceptable evidence.

### Strict review rule

Reviewers must apply this section as a merge gate. Missing reference rows, missing examples, missing outputs, missing
failure boundaries, missing bilingual parity, missing migration records, or missing verification evidence are not optional
polish items. Classify them with the C/I/M guide below and keep the PR out of ready state until every Critical and
Important item is resolved. Minor wording issues can be deferred, but only when they do not hide a coverage, correctness,
or reproducibility gap.

### Zero-exception ready and merge rule

This guide is not advisory for substantial documentation PRs. If a required item in the inventory, depth gate,
role-specific contract, module-specific checklist, bilingual policy, migration record, generated-resource chain, or
verification section applies to the PR scope, it must be satisfied before the PR is called ready. Missing one required
item is enough to reject ready-to-merge status.

Authors and reviewers must not substitute automated green checks for this review. Sphinx proves syntax and linkability;
drift checkers prove selected marker coverage; CI proves configured jobs. None of those checks proves that prose is
thick enough, that examples are useful to humans, that failure boundaries are explained, that diagrams teach the right
claim, or that bilingual pages expose the same risks. The PR body or a linked PR comment must therefore include
human-review evidence for each affected documentation family:

- which tutorial, how-to, explanation, and reference obligations are in scope;
- which obligations are intentionally out of scope and which sibling page or follow-up owns them;
- which exact pages were read for thickness rather than only checked by tools;
- which runnable examples were executed or intentionally kept schematic;
- which generated resources and diagrams were regenerated or visually inspected;
- which bilingual pages were compared for capability, examples, warnings, and failure-boundary parity.

When a substantial PR exists because a page was too thin, reviewers should assume the previous shape was insufficient
until the author shows concrete coverage growth. For command- or field-heavy pages, this means rows plus examples,
counterexamples, output signals, side effects, and repair steps. For how-to pages, this means task cards with inputs,
commands, outputs, side effects, and troubleshooting. For explanations, this means mechanism traces, ordering or
boundary reasoning, counterexamples, and diagram claims where diagrams are used. If any of those elements is absent
without a scoped ownership handoff, the finding is at least Important.

## Module-specific coverage floors

"DSL-level" documentation quality does not mean every module must have the same line count as the DSL pages. It means
the documentation is complete enough that a reader can learn the first successful path, perform common tasks, understand
the design boundaries, and look up exact facts without guessing from source code. For every capability family in scope:

- each public capability must have a landing point in at least one role page: tutorial, how-to, explanation, or
  reference;
- every command-heavy or schema-heavy capability must include legal forms, illegal forms, error behavior, and repair
  guidance;
- every runnable path must state its input, command or code, expected output or success signal, and verification source;
- every reference table must be traceable to implementation facts, schema files, generated assets, or tests;
- every split across multiple pages must name which page owns the tutorial, task recipe, explanation, and reference
  responsibilities so that gaps are not hidden by overlap;
- every bilingual module must teach the same capabilities, examples, warnings, and boundaries in both languages.

The checklists below are current minimum floors for high-traffic modules. They are not a replacement for the inventory
template above; they make the inventory concrete enough for a no-context reviewer to judge whether a page is too thin.

### Generation, rendering, and templates

Generation and template documentation must separate three audiences:

| Audience | Primary pages | Boundary |
|---|---|---|
| Generated-code users | `tutorials/generation/`, `how_to/generation/`, generated `README` files | They need to choose a built-in template, run generation, and integrate generated output. |
| Template authors | `how_to/templates/`, `reference/template_config/`, `explanations/template_rendering/` | They need to write or debug a trusted template directory. |
| Template maintainers | `templates/README*.md`, `templates/*/README*.md`, template tests | They need source-template packaging, formatter, native, and semantic-alignment maintenance rules. |

Required source-fact checklist:

- `pyfcstm/entry/generate.py`;
- `pyfcstm/render/render.py`, `pyfcstm/render/env.py`, `pyfcstm/render/func.py`,
  `pyfcstm/render/expr.py`, `pyfcstm/render/statement.py`, and `pyfcstm/render/c_runtime.py`;
- `pyfcstm/template/__init__.py` and `pyfcstm/template/index.json`;
- `templates/README*.md`, `templates/*/README*.md`, `templates/*/README*.j2`,
  `templates/*/config.yaml`, and `templates/*/template.json`;
- `tools/package_templates.py`, `setup.py`, and `MANIFEST.in` when documenting built-in template packaging,
  source-install, or maintainer workflows;
- `test/entry/test_generate.py`, `test/render/*`, and `test/template/*` when documenting CLI errors, renderer
  validation, generated-runtime behavior, or built-in template guarantees.

Minimum capability checklist:

- `pyfcstm generate` with exactly one of `--template` or `--template-dir` / `-t`;
- `--clear` behavior and data-loss boundary;
- built-in template names, metadata, generated files, entry points, experimental status, and generated README contract;
- custom template directory structure, required `config.yaml`, `.j2` output path rules, static-copy rules, `.git` skip,
  and `ignores`;
- renderer config top-level keys, defaults, section types, `base_lang`, item loading forms
  (`type: template`, `type: import`, `type: value`), and validation errors;
- expression and statement style use, including the distinction between runtime statement rendering and DSL echo
  rendering;
- built-in packaging flow through `make tpl` and packaged-template extraction;
- target-specific boundaries for Python, C, C polling, C++ wrapper, and C++ polling templates;
- formatter, compiler, smoke-test, native-toolchain, and simulator-alignment evidence for claims that mention those
  guarantees.

Reference floors:

- `reference/template_config/` must cover every renderer config validation branch that is already protected by
  `test/render/*`, including invalid root objects, unknown top-level keys, invalid section types, missing `base_lang`,
  invalid `ignores`, and invalid object-loading items.
- `reference/builtin_templates/` must cover every current entry in `pyfcstm/template/index.json` and each template's
  user-visible generated-file and entry-point contract. A matrix of names alone is too thin.
- Generation-related CLI reference must include the missing-template, both-template-options, unknown-template, invalid
  config, and template render failure classes that are visible to users.
- C-family generation claims must read the renderer helper layer that the templates import. If a page documents C/C++
  target-specific expression, condition, action-body, reset, diagnostic, or failure behavior, `pyfcstm/render/c_runtime.py`
  and the generated-template tests are mandatory source facts.

### Inspect and diagnostics

Inspect and diagnostics documentation must treat report shape and diagnostic codes as reference-grade API facts, not as
examples that can be summarized loosely.

Required source-fact checklist:

- `pyfcstm/entry/inspect.py`;
- `pyfcstm/diagnostics/schema.json`;
- `pyfcstm/diagnostics/inspect_llm_report_schema.json`;
- `pyfcstm/diagnostics/codes.yaml`;
- `test/entry/test_inspect.py`, `test/diagnostics/`, and `test/verify/test_inspect_adapter.py`, including any
  tests that validate `codes.yaml` structure or registry drift.

Minimum capability checklist:

- inspect CLI options, output formats, output file behavior, ANSI/color policy, suffix warning, and invalid-input
  boundaries;
- `ModelInspect` top-level fields, metrics, diagnostics, summary sections, source metadata, and schema-version facts;
- LLM-oriented report fields and their intended repair-guidance boundary;
- diagnostic-code registry counts or distribution, severity levels, emission context where discoverable, capability
  tiers when verify-specific diagnostics depend on them, and code ownership;
- verify-policy rejection examples where inspect output is consumed by verification tooling.

Reference floors:

- `reference/inspect_report/` must contain enough field-level detail for a user to parse the JSON without reading the
  Python implementation.
- `reference/diagnostics_codes/` must explain the complete registry shape and cannot document only the most common
  codes unless the omitted groups are explicitly linked or deferred with a reason. The minimum acceptable shape is a
  complete one-row-per-code table or an equivalent generated appendix that lists every current code from `codes.yaml`,
  its severity, short meaning, and documented trigger context. If the complete table is maintained by hand instead of
  generated from `codes.yaml`, the PR must include or point to a drift check that compares the documented code set,
  severities, and trigger-context fields with the registry; otherwise the reference is not auditable.
- Verification must include at least one human-output check, one JSON parse check, one LLM-report check when that report
  is in scope, and one invalid-input or policy-rejection example when failure behavior is documented.
- Diagnostics references must distinguish default static checks from diagnostics that require `--enable-verify`,
  solver-backed analysis, or a specific verify complexity tier when that distinction is part of the implementation. If
  the source registry does not expose a machine-readable trigger field, the documentation must state how the trigger was
  inferred or explicitly defer the trigger-detail table.
- When LLM-oriented inspect output is documented, `inspect_llm_report_schema.json` needs its own field-level coverage or
  a clearly linked subsection under `reference/inspect_report/`; it should not be reduced to a tutorial excerpt. The
  coverage must account for every top-level field and nested schema object that is part of the public report contract,
  including type, required/optional status, diagnostic linkage, and any repair-guidance semantics. If the schema table is
  hand-maintained, the PR must include or point to a drift check or generated-table workflow that keeps it aligned with
  the JSON schema.

### Simulation and execution semantics

Simulation documentation must preserve the exact execution-order contract. A thin command tutorial is not enough when a
page claims to explain runtime behavior.

Required source-fact checklist:

- `pyfcstm/simulate/runtime.py`, `pyfcstm/simulate/context.py`, and `pyfcstm/simulate/decorators.py`;
- `pyfcstm/entry/simulate/` command modules;
- semantic fixture cases under `test/fixtures/simulate_semantics/cases/`;
- `test/testings/simulate_semantics.py` and simulation/runtime tests that define rollback, hot-start, and handler
  behavior.

Minimum capability checklist:

- CLI batch mode, REPL commands, event input forms, settings defaults, output/export shapes, and common errors;
- runtime constructor and cycle contract for Python API users;
- abstract handler registration and context-read boundaries;
- cold entry, composite initial entry, leaf `during`, transition guard/effect, source exit, target entry, aspect
  `during before` / `during after`, pseudo/combo routing, post-exit continuation, hot start, terminal/end handling, and
  speculative validation rollback;
- which examples are verified through an installed CLI, `PYTHONPATH=. python -m pyfcstm`, `CliRunner`, direct runtime
  tests, or docs demo generation.

Reference floors:

- A simulation reference page or section must exist when public simulation commands or API facts are documented; leaving
  all exact facts in tutorials and explanations is too thin. At minimum it must cover CLI options, batch and REPL
  commands, settings, event input forms, export/history formats, relevant Python API constructors or methods, and public
  exceptions such as DFS or validation failures.
- Execution-order explanations must include an ordering matrix or trace examples for the semantic cases they claim to
  cover. If a scenario is intentionally omitted, say which fixture or behavior family owns it.
- Runtime-semantics explanations must map fixture families to the behaviors they prove when semantic fixture tests are
  the evidence source. Important families include lifecycle ordering, aspect actions, pseudo chains, combo routing,
  speculative validation rollback, hot start, terminal/end handling, and abstract-handler context.
- If simulation examples use checked-in `.demo.*` files without a common Makefile target, the page or PR must still
  record the exact manual command used to regenerate each output; otherwise the output is not auditable.

### CLI workflows, installation, and visualization

Command and environment documentation must be verified against actual entry points instead of copied from memory.

Required source-fact checklist:

- `pyfcstm/entry/cli.py`, `pyfcstm/entry/dispatch.py`, and the subcommand modules under `pyfcstm/entry/`;
- `setup.py`, `requirements.txt`, `requirements-test.txt`, `requirements-doc.txt`, and relevant Makefile targets when
  documenting installation or environment facts;
- `pyfcstm/model/plantuml.py`, visualization option objects, and visualization entry points when documenting PlantUML
  or image rendering;
- `test/entry/*`, `test/model/test_plantuml.py`, `test/utils/test_parse.py`, visualization tests, and docs `.demo.*`
  resources when documenting command behavior, `-c key=value` parsing, or rendered-output behavior.

Minimum CLI workflow checklist:

- top-level `pyfcstm --help` / `python -m pyfcstm --help` and every documented subcommand's `--help`;
- stdout, stderr, exit status, input-file requirements, output-file defaults, overwrite behavior, and file side effects;
- missing input, unknown option, invalid config, and invalid command examples where users are likely to see them;
- a short expected output or success signal for every command-heavy how-to step, or an explicit note that the command is
  schematic.
- When CLI help or options are changed or documented, the PR must record the exact help commands that were compared.
  For failure examples, distinguish Click usage errors, Click choice errors, repository `ClickErrorException` errors,
  and downstream runtime/backend failures when they have different exit codes or streams.

Minimum installation checklist:

- ordinary package installation, source-checkout usage, editable/developer usage when documented, and `python -m pyfcstm`
  fallback when console scripts are unavailable;
- Python version support, core dependencies, test dependencies, documentation dependencies, and feature-specific external
  dependencies as separate rows. The source facts for this matrix include `setup.py`, every relevant
  `requirements*.txt` file, and any Makefile or workflow target that installs extra tooling;
- common failures such as `pyfcstm: command not found`, mismatched `pip` and Python interpreter, unsupported Python
  version, missing PlantUML backend, and missing native toolchain;
- release-artifact claims only when they are traceable to a current release workflow or release page. Otherwise write a
  conditional link instead of a platform or checksum promise.

Minimum visualization checklist:

- distinction between `plantuml` source export and `visualize` rendered-image export;
- renderer selection, `--check`, `--no-open`, output suffix behavior, cache behavior, and headless/CI behavior;
- local PlantUML jar versus remote server setup, including network and privacy boundaries for remote rendering;
- `-c key=value` parser facts, legal value forms, illegal examples, unknown keys, and options that must be set through
  dedicated flags rather than generic config;
- `PlantUMLOptions` fields, defaults, presets, and resolution order when those facts appear in reference pages.
- visualization pages that mention direct rendering must account for tested behavior families such as strict-open
  handling, GUI suppression through environment or CI detection, local/remote/auto renderer checks, suffix mismatch, and
  backend success-without-output failures. If a behavior is intentionally omitted from user docs, say which reference or
  test owns the boundary.

Reference floors:

- `reference/cli/` must stay aligned with actual Click help for every public subcommand.
- Installation reference material must distinguish core package requirements from optional docs, rendering, and native
  generated-runtime tooling.
- `reference/visualization_options/` must cover the option dataclass, CLI parser value forms, environment variables,
  and failure boundaries instead of listing only friendly presets.

## Page contracts and failure boundaries

### Tutorial contract

A tutorial page is acceptable when it:

- starts from a realistic beginner state;
- has one primary success path;
- uses short commands or code blocks that a reader can copy;
- shows meaningful intermediate or final output;
- explains what changed after each step;
- links to how-to, explanation, and reference pages instead of embedding them all.

A tutorial page is not acceptable when it:

- only lists options, grammar forms, or fields;
- has no observable success result;
- requires a long opaque shell script in the prose;
- jumps between unrelated tasks;
- depends on generated files that cannot be reproduced from documented sources.

### How-to contract

A how-to page is acceptable when it:

- has task-shaped headings such as “Generate code with a built-in template”;
- states prerequisites and assumptions;
- gives ordered steps;
- includes short expected output or a clear success signal;
- shows common mistakes and fixes when the task is error-prone;
- links to reference pages for exhaustive facts.

A how-to page is not acceptable when it:

- reads like a concept essay;
- mixes several unrelated tasks without separate headings;
- omits expected output for command-heavy steps;
- hides failure behavior behind “should work” wording;
- duplicates a reference table instead of linking to it.

### Explanation contract

An explanation page is acceptable when it:

- answers why a behavior or design exists;
- describes order of execution, data flow, or semantic boundaries;
- uses diagrams, traces, or before/after forms when they clarify the behavior;
- distinguishes stable facts from inferences;
- names known limits and non-goals.

An explanation page is not acceptable when it:

- merely repeats syntax or CLI facts;
- lacks a concrete example, trace, or diagram for a complex behavior;
- states broad claims without boundaries;
- blurs implementation details with user-facing semantics;
- omits important risk scope, such as warning only for C/C++ generated deployment when Python output is unaffected.

### Reference contract

A reference page is acceptable when it:

- can be used without reading a tutorial first;
- lists exact forms, fields, options, defaults, and allowed values;
- includes legal and illegal examples for tricky syntax or schema fields;
- links diagnostics to the relevant invalid forms;
- is dense, searchable, and precise.

A reference page is not acceptable when it:

- is mostly tour prose;
- lacks tables or structured facts for option-heavy or schema-heavy material;
- omits invalid examples for common mistakes;
- describes generated or expanded behavior without showing the expanded form;
- uses vague terms such as “some options” where a closed list is available.

## Examples, counterexamples, and generated resources

Examples must be small, real, and attached to a clear purpose.

- Prefer one short command plus a short output excerpt over a large embedded shell script.
- Put long runnable workflows in `.demo.*`, `.demox.*`, or equivalent source files when they need to be regenerated.
- Mark negative examples explicitly so users do not copy invalid DSL or invalid configuration by mistake.
- For DSL sugar such as combo transitions or forced transitions, show the authored form and the expanded or effective form when that helps users understand semantics.
- For diagnostics examples, include enough input and output for a reader or LLM to repair the issue.
- For generated docs resources, follow the source-output rules in `CLAUDE.md` under Documentation Editing → File Generation Rules. This file does not define a second generation chain.

If a command output is truncated, say so. Do not invent fields, diagnostics, template names, CLI options, or generated files that the current implementation does not produce.

## Diagram and figure discipline

A diagram is documentation evidence, not decoration. When adding PlantUML, SVG, PNG, or Graphviz figures, explain at least one of the following:

- the authored DSL structure;
- the expanded or generated structure;
- the runtime or simulation trace;
- the inspect/report fields that confirm the behavior;
- the boundary that the diagram is meant to clarify.

Figures derived from source files must keep their source-output pair traceable. If only the prose moves and the resource path stays in place, record why that location remains authoritative.

## Bilingual and Chinese terminology discipline

When a page has both English and Chinese variants, keep them synchronized in scope, examples, file references, and warnings. They do not need word-for-word translation, but they must teach the same capability and expose the same risks. If only one language changes, record the reason and the follow-up plan in the PR body or migration note.

Chinese prose should use Chinese terms. When an English term is needed for precision, introduce it once per page in the form `中文术语（English term）`, then use the Chinese term afterwards. Use the same Chinese term for the same English concept across related pages unless a page explicitly explains why a different translation is intentional. For included fragments or shared snippets, treat the rendered page as the reader-facing boundary: the final page should introduce the term before relying on the Chinese-only form.

For substantial bilingual PRs, each changed Chinese page should include an explicit terminology handoff for the core
concepts it discusses. A compact term sentence near the top of the page is acceptable when the page covers many
command, option, renderer, template, grammar, or diagnostics concepts. The handoff must cover the terms a reviewer would
otherwise need to search for, such as command-facing words (for example stdout, stderr, exit status, side effect),
visualization words (renderer, backend, cache, suffix, headless), grammar-tooling words (parser, lexer, listener,
completion), and documentation-policy words (reference, how-to, explanation) when those concepts are central to the page.
Do not rely on a repository-wide glossary to satisfy a per-page first-use requirement unless the page links to that
glossary before using the term.

Keep these verbatim for correctness:

- code, commands, CLI output, file paths, module paths, API names, identifiers, JSON fields, diagnostic codes;
- DSL keywords such as `state`, `enter`, `during`, `exit`, and `effect`;
- target template names such as `python`, `c`, `cpp`, `c_poll`, and `cpp_poll`;
- grammar rule names and other implementation labels where translation would make examples inaccurate.

Unnecessary repeated English words in Chinese prose are reviewable documentation-quality defects. They are Minor when local and harmless, Important when they make a page hard to read or inconsistent, and Critical when they obscure a safety or deployment boundary.

## Navigation and roadmap discipline

The root `docs/source/index_en.rst` and `docs/source/index_zh.rst` are the sidebar authority. Major leaf pages should be listed directly under the relevant top-level caption so the left navigation exposes them.

Roadmap, map, guide, or overview pages are sibling pages under their module. They may link to other pages with ordinary links, but they must not use a toctree to make those pages children. This keeps the sidebar hierarchy flat and predictable.

The generated API reference remains the complete API map and stays in the Reference area as the final API entry. Do not replace generated API toctrees with hand-written API pages. If API page introductions need changing, update the generator that creates them instead of editing generated output directly.

## Migration and landing-page discipline

When restructuring existing docs, readers must be able to answer “where did this old information go?”

Track at least:

| Old item | Required migration record |
|---|---|
| Old page | New page, landing page, or explicit deletion reason. |
| Old heading | New heading or merged destination. |
| Old resource | New resource path, retained path, or deletion reason. |
| Generated output | Source file that regenerates it and the command used when relevant. |
| Old URL | Landing page or compatibility note when the old URL was user-visible. |

Deletion is acceptable only when the content is stale, duplicated, or replaced by a better current source. Say which case applies.

## Verification checklist

Choose checks proportional to the change. Do not claim anything you did not verify.

Always consider:

```bash
git diff --check
```

For Sphinx source changes, run language-appropriate HTML checks. For broad or bilingual reST changes, prefer both:

```bash
NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=en sphinx-build -b html docs/source /tmp/pyfcstm-html-check-en
NO_CONTENTS_BUILD=1 READTHEDOCS_LANGUAGE=zh sphinx-build -b html docs/source /tmp/pyfcstm-html-check-zh
rg -n 'class="problematic"|<span class="problematic"' /tmp/pyfcstm-html-check-en /tmp/pyfcstm-html-check-zh -g '*.html'
```

`rg` is the preferred local scan tool because it is already used throughout this repository's maintainer guidance. If it is not available, use an equivalent recursive grep command, for example:

```bash
grep -RInE --include='*.html' 'class="problematic"|<span class="problematic"' /tmp/pyfcstm-html-check-en /tmp/pyfcstm-html-check-zh
```

For bilingual page changes, also perform a content-synchronization review. Confirm that each changed English or Chinese page has the corresponding language update, or record an explicit deferral. Compare changed headings, commands, examples, warnings, file paths, and diagnostics; a clean HTML build only proves syntax, not translation coverage.

For Chinese documentation changes, run the terminology gate and fix or justify every hit:

```bash
make docs_terminology_check
```

For generated documentation resources, use the generation workflow documented in `CLAUDE.md` rather than editing generated outputs directly. The broad `CLAUDE.md` reminder to run `make contents` applies to Sphinx/source-resource documentation changes that may refresh generated outputs. For policy-only files outside the Sphinx tree, or prose-only changes that do not affect generated resources, record why `make contents` is not applicable; otherwise run it and include any intentional generated updates.

For public Python API or generated API index changes, run `make rst_auto` and include intentional generated RST updates.

For code or tests touched by a documentation task, run the relevant unit tests. Use `SKIP_SLOW_TESTS=1 make unittest` for normal iteration when native-toolchain template tests are not in scope. For commit-message CI routing, follow the current trigger table in `CLAUDE.md`; do not treat any one token as a universal docs rule.

## Reviewer C/I/M guide

Use these levels for documentation reviews.

### Critical

A Critical issue blocks ready-to-merge. Examples:

- The documentation states behavior that is false for the current implementation.
- A capability family in scope has no coverage inventory and the gap could hide missing behavior.
- A command, DSL example, schema example, or generated output is non-reproducible but presented as valid.
- Navigation or toctree changes break discoverability or create an incorrect parent-child structure.
- A migration deletes or hides existing user-visible information without a reason.
- Risk scope is wrong, for example saying a warning applies to all generated targets when it only affects C/C++ deployment.
- No verification evidence is provided, or the claimed verification steps use tools, paths, or inputs that are unavailable in the repository environment and cannot be independently repeated.

### Important

An Important issue should be fixed before merge unless explicitly deferred with a reason. Examples:

- Required inventory fields are present but too vague to audit.
- A page role is mixed enough that readers cannot tell whether it is a tutorial, how-to, explanation, or reference.
- Expected output or failure behavior is missing from a command-heavy guide.
- Chinese terminology discipline is inconsistent across a page, or related pages use different Chinese terms for the same English concept without an explicit reason.
- A diagram is added without explaining what it proves.
- Verification commands do not match the files actually changed.
- Bilingual changes update one language but omit the matching language page without an explicit deferral.

### Minor

A Minor issue is useful to fix but should not block progress by itself. Examples:

- Local wording can be clearer.
- A link would be more convenient in an additional place.
- A table could be reordered for readability.
- A non-essential example could be shorter.

When this guide is changed, apply the same C/I/M rules to the change itself. If the guide would allow a thin, unverifiable, or ambiguous version of itself to pass, the guide is not ready.

## Self-check for this guide

This section records how the guide satisfies its own rules. Keep it updated when the guide changes materially.

| Inventory field | This guide's answer |
|---|---|
| Scope | Maintainer and agent discipline for writing, restructuring, and reviewing pyfcstm documentation. |
| Source facts | `CLAUDE.md` documentation rules, the current Diátaxis documentation tree under `docs/source/`, repository-local source and test coverage for high-traffic documentation modules, and repository commands listed in maintainer guidance. |
| Capability list | Define page roles, require coverage inventory, set module-specific coverage floors, set example and diagram rules, preserve bilingual terminology discipline, protect navigation/migration structure, define verification expectations, and classify review findings. |
| Tutorial path | Not applicable: this is a maintainer policy file, not a user tutorial. The guide explicitly stays outside the Sphinx toctree. |
| How-to tasks | Decide page role, fill module inventory, write acceptable pages, reject unacceptable pages, verify documentation changes, and review with C/I/M levels. |
| Explanation topics | Why documentation needs role separation, traceable examples, explicit boundaries, bilingual synchronization, and proportional verification. |
| Reference facts | Required inventory fields, module-specific source-fact checklists and coverage floors, page contract tables, migration record fields, verification commands, and C/I/M examples. |
| Boundaries and counterexamples | The guide names unacceptable page shapes, zero-verification PRs, false implementation claims, untraceable migrations, broken navigation, and wrong risk scope. |
| Diagnostics and errors | Documentation review defects are classified as Critical, Important, or Minor; product diagnostic codes are referenced only when target documentation needs them. |
| Examples and resources | The generation-module inventory is the worked non-DSL example; command snippets are short and tied to repository guidance. |
| Migration and landing pages | The guide does not move user-facing pages; it adds a `CLAUDE.md` entry so the non-Sphinx policy file remains discoverable. |
| Verification | `git diff --check`, `make docs_terminology_check`, and reviewer C/I/M checks are the relevant verification path for this policy-only change; `make contents`, Sphinx HTML, and `make rst_auto` checks become required when the corresponding Sphinx source, generated documentation resource, public Python API, or generated API index changes are in scope. |

Applied to this guide itself:

- Tutorial contract: not applicable because this file is not a tutorial and says so.
- How-to contract: satisfied by concrete task rules for inventory, examples, navigation, migration, verification, and review.
- Explanation contract: satisfied by rationale for role separation, boundaries, and verification.
- Reference contract: satisfied by structured fields, failure modes, examples, commands, and C/I/M tables.
- Critical self-check: a future edit that removes verification requirements, makes inventory fields optional, hides this file from `CLAUDE.md`, or permits false implementation facts must block merge.

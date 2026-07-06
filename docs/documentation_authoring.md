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

For generated documentation resources, use the generation workflow documented in `CLAUDE.md` rather than editing generated outputs directly. Run `make contents` when source resources changed and generated outputs must be refreshed.

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
| Source facts | `CLAUDE.md` documentation rules, the current Diátaxis documentation tree under `docs/source/`, PR review patterns from the tutorials overhaul, and repository commands listed in maintainer guidance. |
| Capability list | Define page roles, require coverage inventory, set example and diagram rules, preserve bilingual terminology discipline, protect navigation/migration structure, define verification expectations, and classify review findings. |
| Tutorial path | Not applicable: this is a maintainer policy file, not a user tutorial. The guide explicitly stays outside the Sphinx toctree. |
| How-to tasks | Decide page role, fill module inventory, write acceptable pages, reject unacceptable pages, verify documentation changes, and review with C/I/M levels. |
| Explanation topics | Why documentation needs role separation, traceable examples, explicit boundaries, bilingual synchronization, and proportional verification. |
| Reference facts | Required inventory fields, page contract tables, migration record fields, verification commands, and C/I/M examples. |
| Boundaries and counterexamples | The guide names unacceptable page shapes, zero-verification PRs, false implementation claims, untraceable migrations, broken navigation, and wrong risk scope. |
| Diagnostics and errors | Documentation review defects are classified as Critical, Important, or Minor; product diagnostic codes are referenced only when target documentation needs them. |
| Examples and resources | The generation-module inventory is the worked non-DSL example; command snippets are short and tied to repository guidance. |
| Migration and landing pages | The guide does not move user-facing pages; it adds a `CLAUDE.md` entry so the non-Sphinx policy file remains discoverable. |
| Verification | `git diff --check`, `make rst_auto`, and reviewer C/I/M checks are the relevant verification path for this policy-only change; Sphinx HTML checks are required only when Sphinx source pages change. |

Applied to this guide itself:

- Tutorial contract: not applicable because this file is not a tutorial and says so.
- How-to contract: satisfied by concrete task rules for inventory, examples, navigation, migration, verification, and review.
- Explanation contract: satisfied by rationale for role separation, boundaries, and verification.
- Reference contract: satisfied by structured fields, failure modes, examples, commands, and C/I/M tables.
- Critical self-check: a future edit that removes verification requirements, makes inventory fields optional, hides this file from `CLAUDE.md`, or permits false implementation facts must block merge.

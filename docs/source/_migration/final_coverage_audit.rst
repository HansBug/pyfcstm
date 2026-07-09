:orphan:

Final documentation coverage audit
==================================

Purpose
-------

This page is the durable final audit record for the documentation information
architecture split in PR-U. It is intentionally orphaned: it is a maintainer
coverage ledger, not a reader-facing page in the public navigation.

The audit answers three questions for every major pyfcstm capability family:

* Which Tutorial, How-to, Explanation, and Reference page owns the reader-facing
  content?
* Which code, schema, test, generated resource, or migration record is the
  source fact for that ownership claim?
* Are there unresolved gaps in examples, boundaries, diagnostics, migration, or
  bilingual parity?

The answer for PR-U is that the documentation now has explicit owners for every
capability family audited below. Remaining gaps are marked ``None`` except where
PR-U fixed a drift directly.

Source facts used by this audit
-------------------------------

.. list-table:: Audit source facts
   :header-rows: 1

   * - Area
     - Evidence read during PR-U
     - Why it matters
   * - Umbrella planning
     - PR #312 body, especially the PR-U row and final ready conditions.
     - Defines the required capability families and matrix fields.
   * - Authoring discipline
     - ``CLAUDE.md`` and ``docs/documentation_authoring.md``.
     - Defines page roles, inventory fields, depth gates, migration rules,
       bilingual policy, and C/I/M review criteria.
   * - Navigation roots
     - ``docs/source/index_en.rst`` and ``docs/source/index_zh.rst``.
     - Proves leaf pages are mounted directly under the root sidebar and the API
       reference remains last in the Reference area.
   * - Existing migration log
     - ``docs/source/_migration/tutorials_ia.rst``.
     - Tracks the PR-F through PR-Q migration and the PR-U handoff link.
   * - User docs
     - ``docs/source/tutorials/``, ``docs/source/how_to/``,
       ``docs/source/explanations/``, and ``docs/source/reference/``.
     - Supplies page owners, examples, resources, warnings, and reference facts.
   * - API reference
     - ``docs/source/api_doc_en.rst``, ``docs/source/api_doc_zh.rst``, and
       generated ``docs/source/api_doc/``.
     - Supplies the final API map while staying separate from CLI, DSL, report,
       and template reference pages.
   * - Implementation facts
     - ``pyfcstm/dsl/``, ``pyfcstm/model/``, ``pyfcstm/diagnostics/``,
       ``pyfcstm/entry/``, ``pyfcstm/render/``, ``pyfcstm/template/``,
       ``pyfcstm/simulate/``, ``pyfcstm/highlight/``, ``editors/``,
       ``templates/``, ``test/``, and ``tools/``.
     - Prevents the audit from describing imagined behavior.

Global navigation invariants
----------------------------

.. list-table:: Navigation invariants
   :header-rows: 1

   * - Invariant
     - Owner path
     - PR-U result
     - Verification
   * - Tutorials, How-to, Explanations, and Reference leaf pages are mounted
       directly from the root sidebar.
     - ``docs/source/index_en.rst`` and ``docs/source/index_zh.rst``.
     - ``None`` gap. The root files list concrete leaf pages under each caption.
     - Inline navigation audit script in the PR-U verification plan.
   * - Roadmap and map pages are sibling guide pages, not parents of their
       module pages.
     - ``tutorials/index*``, ``how_to/index*``, ``explanations/index*``, and
       ``reference/index*``.
     - ``None`` gap. These pages contain prose and links but no ``.. toctree::``.
     - Inline roadmap audit script.
   * - API reference is the last item in the Reference area.
     - Root Reference toctrees and ``api_doc_en.rst`` / ``api_doc_zh.rst``.
     - ``None`` gap. API docs are last and remain generated infrastructure.
     - Inline API ordering audit script plus rendered HTML spot check.
   * - Migration audit pages are not public navigation pages.
     - ``docs/source/_migration/tutorials_ia.rst`` and this file.
     - ``None`` gap. Both files are orphan maintainer records.
     - Sphinx build plus source review.

Coverage matrix field legend
----------------------------

Each family table uses the following compact fields:

``Owners``
    ``T=`` tutorial owner, ``H=`` how-to owner, ``E=`` explanation owner, and
    ``R=`` reference owner. ``N/A`` entries include a reason in the row.
``Source facts``
    Implementation paths, schemas, tests, PR slices, or generated resources used
    to verify the row.
``Examples/resources``
    Concrete files, command outputs, diagrams, or snippets readers can follow.
``Boundaries/diagnostics``
    Unsupported forms, warnings, error behavior, diagnostics, or counterexamples.
``Migration/verification/gap``
    Landing-page ownership, verification command, and remaining gap status.

DSL
---

.. list-table:: DSL coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - Variables, numeric types, and assignment basics
     - T=``tutorials/dsl/index*``; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*``.
     - ``pyfcstm/dsl/grammar/GrammarParser.g4``; ``pyfcstm/model/model.py``; ``pyfcstm/model/expr.py``; ``pyfcstm/llm/fcstm_grammar_guide.md``.
     - DSL tutorial snippets and reference examples for ``int`` / ``float`` declarations and assignments.
     - Persistent variables must be declared before the root state; block-local temporaries are local to an action block.
     - Migration tracked by PR-G and PR-K records; gap ``None``.
   * - State naming, reserved generated names, and identifier normalization
     - T=``tutorials/dsl/index*`` introduces normal state names; H=``how_to/dsl/index*`` covers safe naming tasks; E=``explanations/dsl_semantics/index*`` covers generated combo relays; R=``reference/dsl/index*``.
     - ``pyfcstm/utils/text.py``; ``pyfcstm/utils/safe.py``; combo pseudo-state helpers in ``pyfcstm/model/model.py``.
     - Reference naming rows and combo expansion examples.
     - User-authored names that look like generated ``__combo_*`` pseudo states do not regain trusted generated metadata.
     - Gap ``None``.
   * - Root state, initial transition, default entry, and terminal behavior
     - T=``tutorials/dsl/index*`` and ``tutorials/quick_start/index*``; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*`` and ``explanations/execution_semantics/index*``; R=``reference/dsl/index*`` and ``reference/simulation/index*``.
     - Grammar initial-transition rules, model loading, and simulation runtime frame handling.
     - Tutorial first machine and simulation examples.
     - Each composite chooses an initial child; terminal and stoppable paths affect runtime progression and hot start.
     - Gap ``None``.
   * - Leaf and composite state hierarchy
     - T=``tutorials/dsl/index*``; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*``.
     - ``State.walk_states()``, ``State.find_state()``, grammar state-definition rules.
     - Hierarchical examples and generated PlantUML diagrams.
     - Outer-scope transitions must not bypass the owning composite's entry semantics.
     - Gap ``None``.
   * - Transition forms, guards, and effects
     - T=``tutorials/dsl/index*``; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*``.
     - Grammar transition alternatives, listener node construction, model transition validation.
     - Guard/action tutorial snippets and reference legal/illegal forms.
     - Event syntax and guard syntax are deliberately not combined in one transition form.
     - Gap ``None``.
   * - Event scopes and event injection names
     - T=``tutorials/dsl/index*``; H=``how_to/dsl/index*`` and ``how_to/simulation/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*`` and ``reference/simulation/index*``.
     - Grammar event rules; runtime event matching; generated template event constants.
     - Local ``::``, chain ``:``, root ``:/`` examples and simulation event injection commands.
     - Wrong scope silently targets a different event namespace or fails to match.
     - Gap ``None``.
   * - Forced transitions and pseudo/combo expansion
     - T=``tutorials/dsl/index*`` gives the learning boundary; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*``.
     - Combo expansion helpers and diagnostics analyzers.
     - Expanded-after examples and diagrams from PR-K.
     - Forced transitions cannot carry effect blocks; combo relays are generated implementation structure, not user API.
     - Gap ``None``.
   * - Arithmetic, logical, bitwise, and function-call expressions
     - T=``tutorials/dsl/index*``; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*``.
     - ``pyfcstm/model/expr.py``; ``pyfcstm/render/expr.py``; solver expression lowering.
     - Reference operator tables and examples for implication, xor, iff, bitwise operators, and numeric comparisons.
     - Boolean xor is ``xor``; numeric ``^`` remains bitwise xor; assignment expressions are numeric, guards are conditions.
     - Gap ``None``.
   * - Operation blocks and block-local temporaries
     - T=``tutorials/dsl/index*``; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*`` and ``reference/template_config/index*``.
     - ``pyfcstm/render/statement.py``; solver operation lowering; action-block model nodes.
     - Assignment and temporary examples in DSL and renderer references.
     - Temporaries can be read only after assignment in the same concrete block.
     - Gap ``None``.
   * - Lifecycle actions, abstract actions, named actions, and ``ref``
     - T=``tutorials/dsl/index*``; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*`` and ``explanations/execution_semantics/index*``; R=``reference/dsl/index*`` and ``reference/simulation/index*``.
     - Grammar lifecycle rules; ``SimulationRuntime`` action dispatch; generated template README contracts.
     - Examples for ``enter abstract``, named actions, and ``ref`` reuse.
     - ``ref`` targets named lifecycle actions, not states or events.
     - Gap ``None``.
   * - Aspect actions and overlay order
     - T=``tutorials/dsl/index*`` introduces aspects briefly; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*`` and ``explanations/execution_semantics/index*``; R=``reference/dsl/index*``.
     - ``OnStage`` / ``OnAspect`` model fields and runtime ordering tests.
     - During-before / during-after trace tables.
     - Composite plain during actions do not wrap child-to-child transitions in the same way as descendant leaf cycles.
     - Gap ``None``.
   * - Imports and imported state-machine facts
     - T=N/A: imports are not needed for first success; H=``how_to/dsl/index*``; E=``explanations/dsl_semantics/index*``; R=``reference/dsl/index*``.
     - ``pyfcstm/model/imports.py`` and import validation tests.
     - Import how-to examples and diagnostics.
     - Import failures surface as model validation errors with structured diagnostics.
     - Gap ``None``.
   * - Validation and DSL diagnostics ownership
     - T=``tutorials/inspect/index*`` after the first DSL path; H=``how_to/inspect/index*`` and ``how_to/dsl/index*``; E=``explanations/diagnostics/index*``; R=``reference/diagnostics_codes/index*`` and ``reference/dsl/index*``.
     - ``pyfcstm/diagnostics/codes.yaml``; inspect schemas and diagnostics tests.
     - Invalid DSL and model-validation examples.
     - Grammar parse failures differ from model diagnostics and target deployment warnings.
     - Gap ``None``.

Simulation
----------

.. list-table:: Simulation coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - First simulated cycle and current-state display
     - T=``tutorials/simulation/index*`` and ``tutorials/quick_start/index*``; H=``how_to/simulation/index*``; E=``explanations/execution_semantics/index*``; R=``reference/simulation/index*``.
     - ``pyfcstm/simulate/runtime.py`` and ``pyfcstm/entry/simulate/batch.py``.
     - Tutorial commands and expected current-state output.
     - Runtime output is state-machine behavior, not generated-template proof.
     - PR-H and PR-N records; gap ``None``.
   * - Batch commands and event injection
     - T=``tutorials/simulation/index*``; H=``how_to/simulation/index*`` and ``how_to/cli_workflows/index*``; E=``explanations/execution_semantics/index*``; R=``reference/simulation/index*`` and ``reference/cli/index*``.
     - Batch parser, command dispatcher, event matching tests.
     - ``cycle``, ``cycle <count>``, and event examples.
     - Command-layer failures and model-layer failures have different exit/status behavior.
     - Gap ``None``.
   * - Interactive REPL commands
     - T=``tutorials/simulation/index*``; H=``how_to/simulation/index*``; E=``explanations/execution_semantics/index*``; R=``reference/simulation/index*``.
     - ``pyfcstm/entry/simulate/repl.py`` and command classes.
     - REPL task cards and reference command table.
     - Prompt UI depends on ``prompt_toolkit`` and ``rich``.
     - Gap ``None``.
   * - Hot start and initial variable requirements
     - T=N/A: not part of first run; H=``how_to/simulation/index*``; E=``explanations/execution_semantics/index*``; R=``reference/simulation/index*``.
     - ``SimulationRuntime.init`` / hot-start helpers and semantic fixtures.
     - Hot-start examples with required variables.
     - Missing variables, unreachable stoppable paths, depth limits, and safety limits are documented.
     - Gap ``None``.
   * - History and export formats
     - T=N/A: advanced task; H=``how_to/simulation/index*``; E=``explanations/execution_semantics/index*``; R=``reference/simulation/index*``.
     - CLI export implementation and tests.
     - YAML/JSON/JSONL/CSV examples and snippets.
     - Export shape is runtime trace evidence, not model source of truth.
     - Gap ``None``.
   * - Settings and abstract handlers
     - T=N/A; H=``how_to/simulation/index*``; E=``explanations/execution_semantics/index*``; R=``reference/simulation/index*`` and API docs for ``pyfcstm.simulate``.
     - ``pyfcstm/simulate/context.py`` and ``decorators.py``.
     - Abstract handler examples and context access notes.
     - Handlers are extension points; generated templates have separate hook contracts.
     - Gap ``None``.
   * - Execution stack, lifecycle order, and rollback
     - T=``tutorials/simulation/index*`` for observable order; H=``how_to/simulation/index*``; E=``explanations/execution_semantics/index*``; R=``reference/simulation/index*``.
     - ``SimulationRuntime`` frame stack and semantic alignment fixtures.
     - Trace tables for enter/during/exit/effect ordering.
     - Speculative validation precedes committing transitions.
     - Gap ``None``.
   * - Pseudo/combo relay and terminal handling
     - T=N/A for first run; H=``how_to/simulation/index*``; E=``explanations/execution_semantics/index*`` and ``explanations/dsl_semantics/index*``; R=``reference/simulation/index*`` and ``reference/dsl/index*``.
     - Combo relay expansion, runtime relay execution, semantic tests.
     - PR-K/PR-N examples.
     - Relay nodes are generated semantic helpers, not user states to target directly.
     - Gap ``None``.

Inspect and diagnostics
-----------------------

.. list-table:: Inspect and diagnostics coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - First human report
     - T=``tutorials/inspect/index*``; H=``how_to/inspect/index*``; E=``explanations/diagnostics/index*``; R=``reference/inspect_report/index*``.
     - ``pyfcstm/entry/inspect.py`` and inspect renderer.
     - Inspect tutorial report snippets.
     - Human output is for reading, not schema-stable automation.
     - PR-C, PR-O, and PR-R records; gap ``None``.
   * - JSON report schema
     - T=``tutorials/inspect/index*``; H=``how_to/inspect/index*``; E=``explanations/diagnostics/index*``; R=``reference/inspect_report/index*``.
     - ``pyfcstm/diagnostics/schema.json`` and report tests.
     - JSON examples and field reference.
     - Consumers should use the schema and field names, not human report layout.
     - ``tools/check_diagnostics_reference_docs.py --check``; gap ``None``.
   * - LLM JSON and Markdown reports
     - T=N/A: repair workflow; H=``how_to/inspect/index*``; E=``explanations/diagnostics/index*``; R=``reference/inspect_report/index*``.
     - ``inspect_llm_report_schema.json`` and LLM render code.
     - LLM report examples and repair guidance.
     - LLM reports guide fixes; they do not execute or prove repairs.
     - Gap ``None``.
   * - Severity gates and CI usage
     - T=N/A; H=``how_to/inspect/index*`` and ``how_to/cli_workflows/index*``; E=``explanations/diagnostics/index*``; R=``reference/cli/index*`` and ``reference/diagnostics_codes/index*``.
     - Inspect CLI options, diagnostics severity policy, tests.
     - CI gate commands and failure signals.
     - Severity is not the same as runtime risk.
     - Gap ``None``.
   * - Source spans, suffix warnings, and model validation
     - T=``tutorials/inspect/index*``; H=``how_to/inspect/index*``; E=``explanations/diagnostics/index*``; R=``reference/inspect_report/index*``.
     - Diagnostics sink, model validation, renderers.
     - Source-span snippets and invalid-model examples.
     - Invalid DSL parse failures may prevent a structured model report.
     - Gap ``None``.
   * - Diagnostic codes and analyzer families
     - T=N/A; H=``how_to/inspect/index*``; E=``explanations/diagnostics/index*``; R=``reference/diagnostics_codes/index*``.
     - ``pyfcstm/diagnostics/codes.yaml`` and analyzers.
     - Diagnostic code tables and example findings.
     - Codes are emitted by analyzer capability and target profile, not every run.
     - ``tools/check_diagnostics_reference_docs.py --check``; gap ``None``.
   * - ``--enable-verify`` and target deployment warnings
     - T=N/A; H=``how_to/inspect/index*``; E=``explanations/diagnostics/index*``; R=``reference/cli/index*`` and diagnostics reference pages.
     - Verify integration and target-profile diagnostics.
     - PR-O/PR-R examples.
     - Static inspect cannot prove every runtime path unless verify capability is enabled and applicable.
     - Gap ``None``.

Generation
----------

.. list-table:: Generation coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - First built-in Python generation
     - T=``tutorials/generation/index*``; H=``how_to/generation/index*``; E=``explanations/template_rendering/index*``; R=``reference/builtin_templates/index*`` and ``reference/cli/index*``.
     - ``pyfcstm/entry/generate.py``; packaged template extraction; Python template tests.
     - ``docs/source/tutorials/generation/simple_machine.fcstm`` and Python consumer smoke.
     - Built-in templates are selected with ``--template``, not repository ``templates/`` paths.
     - PR-B and PR-P records; gap ``None``.
   * - Custom template directory generation
     - T=N/A: author task; H=``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/template_config/index*``.
     - ``StateMachineCodeRenderer`` and renderer config validation tests.
     - Minimal custom template examples.
     - Custom template failures are trusted-template authoring errors, not built-in template regressions.
     - Gap ``None``.
   * - Output clearing and data-loss boundary
     - T=``tutorials/generation/index*`` notes safe first run; H=``how_to/generation/index*``; E=``explanations/template_rendering/index*``; R=``reference/cli/index*`` and ``reference/template_config/index*``.
     - Generate CLI and renderer output cleanup code.
     - ``--clear`` task cards.
     - ``--clear`` can remove output files and directories in the target output tree.
     - Gap ``None``.
   * - Built-in extraction and generated README contract
     - T=``tutorials/generation/index*``; H=``how_to/generation/index*``; E=``explanations/template_rendering/index*``; R=``reference/builtin_templates/index*``.
     - ``pyfcstm/template/__init__.py``; ``pyfcstm/template/index.json``; template README templates.
     - Generated README references and smoke commands.
     - Generated README is model-specific and can contain names not known to generic docs.
     - Gap ``None``.
   * - Python, C, C polling, C++ wrapper, and C++ polling families
     - T=Python first run only; H=``how_to/generation/index*``; E=``explanations/template_rendering/index*``; R=``reference/builtin_templates/index*``.
     - ``templates/*/template.json``; ``pyfcstm/template/index.json``; ``test/template/*``.
     - Native smoke scripts and generated README contracts.
     - Native evidence depends on available toolchain and template-specific runtime family.
     - PR-U fixed template metadata drift in ``reference/builtin_templates/index_zh.rst``; gap ``Fixed in PR-U``.
   * - Unknown template, mutually exclusive template options, invalid config, and render failures
     - T=N/A; H=``how_to/generation/index*`` and ``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/cli/index*`` and ``reference/template_config/index*``.
     - CLI error handling, renderer validation tests, template config checker.
     - Failure examples and troubleshooting cards.
     - Renderer failures are bounded to input DSL/model, config, trusted helper loading, or Jinja rendering.
     - ``tools/check_template_reference_docs.py --check``; gap ``None`` after PR-U fix.

Templates and renderer configuration
------------------------------------

.. list-table:: Template coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - Template directory layout and ``.j2`` path mapping
     - T=N/A; H=``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/template_config/index*``.
     - ``pyfcstm/render/render.py`` and renderer tests.
     - Minimal template directory and nested output examples.
     - ``config.yaml`` is read as config, not rendered as output.
     - PR-I and PR-P records; gap ``None``.
   * - Static copy, ``.git`` skipping, and ``ignores``
     - T=N/A; H=``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/template_config/index*``.
     - Renderer copy logic and pathspec handling.
     - Static asset examples and ignore markers.
     - Ignore patterns apply to template inputs; generated outputs still need normal output hygiene.
     - Gap ``None``.
   * - ``expr_styles`` and expression rendering aliases
     - T=N/A; H=``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/template_config/index*``.
     - ``pyfcstm/render/expr.py`` and style tests.
     - ``expr_render`` examples for DSL, Python, C, C++, JavaScript, TypeScript, Rust, Go, and Java style names where documented.
     - Expression rendering does not define runtime scheduling.
     - Gap ``None``.
   * - ``stmt_styles`` and runtime statement rendering
     - T=N/A; H=``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/template_config/index*``.
     - ``pyfcstm/render/statement.py`` and tests.
     - ``stmt_render`` / ``stmts_render`` examples.
     - ``operation_stmt_render`` is DSL echo text, not target-language runtime code.
     - Gap ``None``.
   * - ``globals``, ``filters``, ``tests`` and object loading forms
     - T=N/A; H=``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/template_config/index*``.
     - ``pyfcstm/render/func.py`` and validation tests.
     - ``type: template``, ``type: import``, and ``type: value`` examples.
     - Unknown type, missing fields, non-dict entries, and import failures are documented invalid forms.
     - Gap ``None``.
   * - C-family helper facts and target-runtime boundaries
     - T=N/A; H=``how_to/generation/index*`` and ``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/builtin_templates/index*`` and ``reference/template_config/index*``.
     - ``pyfcstm/render/c_runtime.py`` and C-family template tests.
     - C action/condition/reset body references and native smoke notes.
     - Do not hide runtime logic in Python helper prose; generated target code and tests own runtime claims.
     - Gap ``None``.
   * - Packaging, source install, and built-in template metadata
     - T=N/A; H=``how_to/generation/index*``; E=``explanations/template_rendering/index*``; R=``reference/builtin_templates/index*``.
     - ``tools/package_templates.py``; ``tools/check_template_packaging.py``; ``tools/check_template_source_install.py``; ``pyfcstm/template/index.json``.
     - Built-in template metadata matrix.
     - Source-template files and packaged zip assets must stay synchronized.
     - PR-U fixed Chinese metadata description drift; gap ``Fixed in PR-U``.

Visualization
-------------

.. list-table:: Visualization coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - PlantUML source export
     - T=``tutorials/visualization/index*``; H=``how_to/visualization/index*``; E=``explanations/architecture/index*``; R=``reference/visualization_options/index*`` and ``reference/cli/index*``.
     - ``pyfcstm/entry/plantuml.py``; model PlantUML export code.
     - ``docs/source/tutorials/visualization/example.fcstm`` and generated ``.puml`` resources.
     - PlantUML source export does not require external image rendering.
     - PR-F and PR-Q records; gap ``None``.
   * - Rendered SVG/PNG output and renderer boundary
     - T=``tutorials/visualization/index*``; H=``how_to/visualization/index*``; E=``explanations/architecture/index*``; R=``reference/visualization_options/index*``.
     - Visualize entry point, renderer options, external renderer dependencies.
     - Existing rendered SVG/PNG examples.
     - Rendering depends on available renderer/toolchain and may fail outside pyfcstm model semantics.
     - Gap ``None``.
   * - Detail levels, depth, and readability controls
     - T=``tutorials/visualization/index*``; H=``how_to/visualization/index*``; E=``explanations/architecture/index*``; R=``reference/visualization_options/index*``.
     - ``PlantUMLOptions`` and visualization reference checker.
     - Detail-level comparison examples.
     - Large models need focused diagrams instead of all-detail dumps.
     - ``tools/check_visualization_reference_docs.py --check``; gap ``None``.
   * - CLI ``-c`` typed values and Python-only options
     - T=N/A; H=``how_to/visualization/index*``; E=``explanations/architecture/index*``; R=``reference/visualization_options/index*`` and ``reference/cli/index*``.
     - CLI config parser and ``PlantUMLOptions`` fields.
     - Legal/illegal option examples.
     - Some Python API fields are not valid through CLI ``-c``.
     - Gap ``None``.
   * - Generated-resource chain and visual review
     - T=``tutorials/visualization/index*``; H=``how_to/visualization/index*``; E=``explanations/architecture/index*``; R=``reference/visualization_options/index*``.
     - Docs resource generation rules and PR-Q architecture figure update.
     - ``.fcstm`` → ``.puml`` → image resource chains.
     - Figures must state what they prove and remain readable in rendered HTML.
     - Gap ``None``.

CLI workflows
-------------

.. list-table:: CLI workflow coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - Top-level help and command selection
     - T=``tutorials/quick_start/index*``; H=``how_to/cli_workflows/index*``; E=``explanations/architecture/index*``; R=``reference/cli/index*``.
     - ``pyfcstm/entry/cli.py`` and Click command tree.
     - Help output examples and quick-start command chain.
     - Help text is a lookup aid, not a replacement for task recipes.
     - ``tools/check_cli_reference_docs.py --check``; gap ``None``.
   * - ``simulate`` command family
     - T=``tutorials/simulation/index*``; H=``how_to/simulation/index*`` and ``how_to/cli_workflows/index*``; E=``explanations/execution_semantics/index*``; R=``reference/cli/index*`` and ``reference/simulation/index*``.
     - Simulate CLI, REPL, batch, export code.
     - Batch command snippets and output excerpts.
     - Batch command-layer errors and runtime errors have distinct surfaces.
     - Gap ``None``.
   * - ``inspect`` command family
     - T=``tutorials/inspect/index*``; H=``how_to/inspect/index*`` and ``how_to/cli_workflows/index*``; E=``explanations/diagnostics/index*``; R=``reference/cli/index*``.
     - Inspect CLI and diagnostics renderer.
     - Human, JSON, LLM JSON, LLM Markdown commands.
     - CI severity gate is policy, not semantic proof.
     - Gap ``None``.
   * - ``generate`` command family
     - T=``tutorials/generation/index*``; H=``how_to/generation/index*`` and ``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/cli/index*``.
     - Generate CLI and renderer code.
     - Built-in and custom-template command examples.
     - Exactly one of ``--template`` or ``--template-dir`` should be selected for one run.
     - Gap ``None``.
   * - ``plantuml`` and ``visualize`` command families
     - T=``tutorials/visualization/index*``; H=``how_to/visualization/index*`` and ``how_to/cli_workflows/index*``; E=``explanations/architecture/index*``; R=``reference/cli/index*`` and ``reference/visualization_options/index*``.
     - Visualization entry points and option parsing.
     - PlantUML source and rendered diagram commands.
     - External renderer failures are not DSL/model validation failures.
     - Gap ``None``.
   * - stdout, stderr, exit status, file side effects, and reproducibility
     - T=``tutorials/quick_start/index*`` for first signals; H=``how_to/cli_workflows/index*``; E=``explanations/architecture/index*``; R=``reference/cli/index*``.
     - Click entry points, tests, and reference drift checker.
     - Task acceptance cards in CLI how-to.
     - A green command can still leave generated files that need explicit review.
     - Gap ``None``.

Installation
------------

.. list-table:: Installation coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - PyPI and virtualenv installation
     - T=``tutorials/quick_start/index*`` prerequisites; H=``how_to/installation/index*``; E=``explanations/architecture/index*`` for dependency boundary; R=``reference/cli/index*`` for post-install command availability.
     - Packaging metadata and requirements files.
     - Installation demo scripts.
     - Environment support includes broad Python and platform compatibility constraints.
     - PR-F and PR-Q records; gap ``None``.
   * - CLI smoke after installation
     - T=``tutorials/quick_start/index*``; H=``how_to/installation/index*`` and ``how_to/cli_workflows/index*``; E=``explanations/architecture/index*``; R=``reference/cli/index*``.
     - CLI entry point and install-check demos.
     - ``pyfcstm --help`` and command smoke snippets.
     - CLI import success does not prove optional external renderers are installed.
     - Gap ``None``.
   * - Documentation dependencies and resource builders
     - T=N/A; H=``how_to/installation/index*`` and docs build guidance; E=``explanations/architecture/index*``; R=``reference/visualization_options/index*`` where renderer facts matter.
     - ``requirements-doc.txt`` and docs Makefiles.
     - Sphinx and resource-generation commands.
     - Generated resources must be changed through sources, not edited directly.
     - Gap ``None``.
   * - Optional external renderers and native toolchains
     - T=N/A; H=``how_to/installation/index*`` and ``how_to/visualization/index*``; E=``explanations/template_rendering/index*``; R=``reference/visualization_options/index*`` and ``reference/builtin_templates/index*``.
     - PlantUML, Graphviz, native toolchain and template test guidance.
     - Native smoke / renderer troubleshooting notes.
     - Optional tool absence should be reported as environment boundary.
     - Gap ``None``.
   * - Source install and template extraction
     - T=N/A; H=``how_to/installation/index*`` and ``how_to/generation/index*``; E=``explanations/template_rendering/index*``; R=``reference/builtin_templates/index*``.
     - ``tools/check_template_source_install.py`` and package manifest files.
     - Source-install built-in template extraction check.
     - Source install checks can be slower and should be run when packaging/source-install facts are claimed.
     - Gap ``None``.

Grammar tooling
---------------

.. list-table:: Grammar tooling coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - ANTLR grammar and generated parser
     - T=N/A for users; H=``how_to/grammar_editor/index*``; E=``explanations/grammar_tooling/index*``; R=``reference/grammar_tooling/index*``.
     - ``pyfcstm/dsl/grammar/*.g4`` and generated parser files.
     - ``make antlr`` / ``make antlr_build`` commands.
     - Generated grammar files are exempt from normal broad-catch style edits.
     - PR-I and PR-Q records; gap ``None``.
   * - Listener/model coupling
     - T=N/A; H=``how_to/grammar_editor/index*``; E=``explanations/grammar_tooling/index*``; R=``reference/grammar_tooling/index*`` and API docs for model objects.
     - ``pyfcstm/dsl/listener.py``, ``pyfcstm/dsl/node.py``, and ``pyfcstm/model/``.
     - Syntax-support trace and boundary examples.
     - Grammar acceptance alone does not prove model semantic validity.
     - Gap ``None``.
   * - Pygments, TextMate, Sublime, VSCode, and jsfcstm editor assets
     - T=N/A; H=``how_to/grammar_editor/index*``; E=``explanations/grammar_tooling/index*``; R=``reference/grammar_tooling/index*``.
     - ``pyfcstm/highlight/``, ``editors/`` assets, and validation scripts.
     - Editor-update checklist.
     - Unit test trees remain isolated across Python and jsfcstm.
     - Gap ``None``.
   * - Operator ordering and keyword updates
     - T=N/A; H=``how_to/grammar_editor/index*``; E=``explanations/grammar_tooling/index*``; R=``reference/grammar_tooling/index*``.
     - Grammar files, highlighters, and ``editors/validate.py``.
     - Operator-order and keyword checklist tables.
     - Multi-character operators must precede single-character operators.
     - Gap ``None``.
   * - LLM grammar guide checksum
     - T=N/A; H=``how_to/grammar_editor/index*`` for maintenance; E=``explanations/grammar_tooling/index*``; R=``reference/grammar_tooling/index*``.
     - ``pyfcstm/llm/fcstm_grammar_guide.md`` and ``.sha256``.
     - ``make sha256`` guidance.
     - Guide and checksum must be committed together when syntax-facing content changes.
     - PR-U checksum verification script; gap ``None``.

Architecture and execution explanations
---------------------------------------

.. list-table:: Architecture and explanation coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - DSL to AST to model to consumers pipeline
     - T=``tutorials/quick_start/index*`` observes the pipeline; H=``how_to/cli_workflows/index*`` for commands; E=``explanations/architecture/index*``; R=API docs and individual reference pages.
     - ``pyfcstm/dsl/``, ``pyfcstm/model/``, entry commands.
     - Architecture diagram and command flow snippets.
     - API docs are not the only source for CLI, DSL, report, or template facts.
     - PR-D, PR-I, PR-Q records; gap ``None``.
   * - Diagnostics, simulation, rendering, and visualization responsibility boundaries
     - T=domain tutorials by task; H=domain how-to pages; E=``explanations/architecture/index*``, ``explanations/diagnostics/index*``, ``explanations/execution_semantics/index*``, and ``explanations/template_rendering/index*``; R=domain reference pages.
     - Entry points, runtime, diagnostics, renderer, visualization code.
     - Pipeline traces and boundary examples.
     - Inspect does not execute runtime cycles; renderer does not choose simulator semantics; visualization does not validate target code.
     - Gap ``None``.
   * - Template asset split and packaged built-ins
     - T=``tutorials/generation/index*``; H=``how_to/generation/index*`` and ``how_to/templates/index*``; E=``explanations/template_rendering/index*``; R=``reference/builtin_templates/index*`` and ``reference/template_config/index*``.
     - ``templates/``, ``pyfcstm/template/``, package tools.
     - Built-in extraction and generated README examples.
     - Repository source templates are maintainer assets; packaged templates are user-facing built-ins.
     - Gap ``None``.
   * - Generated artifact discipline and docs source-output chains
     - T=visualization/generation tutorials where outputs appear; H=``how_to/visualization/index*`` and maintainer docs; E=``explanations/architecture/index*``; R=resource-generation rules in ``CLAUDE.md``.
     - Docs Makefiles and generated resources.
     - ``.fcstm`` → ``.puml`` → images and demo source-output chains.
     - Generated files should not be edited directly.
     - Gap ``None``.
   * - Simulation versus generated runtime relationship
     - T=``tutorials/simulation/index*`` and ``tutorials/generation/index*``; H=``how_to/simulation/index*`` and ``how_to/generation/index*``; E=``explanations/execution_semantics/index*`` and ``explanations/template_rendering/index*``; R=``reference/simulation/index*`` and ``reference/builtin_templates/index*``.
     - Simulator, template tests, semantic alignment fixtures.
     - Runtime trace and generated-runtime smoke examples.
     - Simulator parity is a hard template claim only where tests cover it.
     - Gap ``None``.

API reference
-------------

.. list-table:: API reference coverage ledger
   :header-rows: 1

   * - Sub-capability
     - Owners
     - Source facts
     - Examples/resources
     - Boundaries/diagnostics
     - Migration/verification/gap
   * - API landing intro and generated module tree
     - T=N/A: API reference is not a tutorial; H=N/A: API reference is not a task recipe; E=``explanations/architecture/index*`` explains how API docs fit; R=``api_doc_en.rst``, ``api_doc_zh.rst``, and generated ``api_doc/``.
     - ``auto_rst_top_index.py`` and generated API RST files.
     - API landing pages with introduction before the module tree.
     - API docs serve readers who already know module/class/function names.
     - ``make rst_auto``; gap ``None``.
   * - Reference map handoff
     - T=N/A; H=N/A; E=``explanations/architecture/index*``; R=``reference/index*`` and API docs.
     - Root Reference toctree and reference map pages.
     - Reference map cards and API landing links.
     - CLI, DSL, inspect report, diagnostics, simulation, visualization, template config, and built-in template facts stay in their own reference pages.
     - API-overreach audit script; gap ``None``.
   * - Root toctree order
     - T=N/A; H=N/A; E=N/A; R=root ``index_en.rst`` / ``index_zh.rst``.
     - Root toctree source.
     - Sidebar order in rendered HTML.
     - API reference must remain last in Reference.
     - Inline navigation audit script; gap ``None``.

Landing pages and migration ownership
-------------------------------------

.. list-table:: Tutorial entry audit
   :header-rows: 1

   * - Entry
     - Current role
     - New owner pages
     - Verification and gap
   * - ``tutorials/quick_start/index*``
     - Active tutorial.
     - First run across simulate, inspect, generate, and visualization; deeper facts are owned by how-to and reference pages.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/dsl/index*``
     - Active tutorial.
     - DSL first-success learning path; exhaustive syntax lives in ``reference/dsl/index*`` and ``how_to/dsl/index*``.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/simulation/index*``
     - Active tutorial.
     - First simulation run; task and semantics owners are ``how_to/simulation/index*`` and ``explanations/execution_semantics/index*``.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/inspect/index*``
     - Active tutorial.
     - First inspect report; CI/LLM/schema owners are how-to, explanation, and reference pages.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/generation/index*``
     - Active tutorial.
     - First Python generation; built-in template and renderer facts are owned by generation/template pages.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/visualization/index*``
     - Active tutorial.
     - First diagram path; options and renderer tasks are owned by visualization how-to/reference.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/cli/index*``
     - Compatibility landing page.
     - ``how_to/cli_workflows/index*``, ``reference/cli/index*``, ``how_to/installation/index*``, and quick start.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/installation/index*``
     - Compatibility landing page.
     - ``how_to/installation/index*`` and quick start.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/grammar/index*``
     - Compatibility landing page.
     - ``how_to/grammar_editor/index*``, ``explanations/grammar_tooling/index*``, ``reference/grammar_tooling/index*``, and DSL reference.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/render/index*``
     - Compatibility landing page.
     - ``how_to/templates/index*``, ``explanations/template_rendering/index*``, ``reference/template_config/index*``, and built-in template reference.
     - EN/ZH present and non-empty; gap ``None``.
   * - ``tutorials/structure/index*``
     - Compatibility landing page.
     - ``explanations/architecture/index*``, execution semantics, template rendering, and API docs.
     - EN/ZH present and non-empty; gap ``None``.

Bilingual and terminology audit
-------------------------------

.. list-table:: Bilingual audit
   :header-rows: 1

   * - Check
     - Evidence
     - Result
   * - Page pairs exist for current user-facing leaf pages.
     - Root toctree entries and ``find docs/source/{tutorials,how_to,explanations,reference}`` review.
     - ``None`` gap for audited pages.
   * - Chinese prose terminology gate.
     - ``tools/check_docs_terminology.py --self-check``, ``tools/check_docs_terminology.py --check``, and ``make docs_terminology_check``.
     - ``None`` gap after PR-T; PR-U keeps the gate in verification.
   * - Same capability and boundary parity.
     - Family matrix rows compare EN/ZH owner pages rather than line-by-line translation.
     - ``None`` gap for audited families.
   * - Metadata that must remain verbatim.
     - Built-in template ``description`` values from ``pyfcstm/template/index.json`` and ``templates/<name>/template.json``.
     - PR-U changed the Chinese built-in template metadata table to mirror exact source descriptions while surrounding prose explains why the values stay verbatim.

Verification matrix
-------------------

.. list-table:: PR-U verification matrix
   :header-rows: 1

   * - Command or review
     - Evidence target
     - Result expected for ready
   * - ``make rst_auto``
     - Generated API landing pages and API tree.
     - No unexpected generated diff after intentional API intro generation.
   * - ``git diff --check``
     - Whitespace and patch hygiene.
     - Clean.
   * - ``python tools/check_cli_reference_docs.py --check``
     - CLI reference markers and command boundary facts.
     - Pass.
   * - ``python tools/check_visualization_reference_docs.py --check``
     - Visualization option/reference markers.
     - Pass.
   * - ``python tools/check_diagnostics_reference_docs.py --check``
     - Diagnostic code/report marker drift.
     - Pass.
   * - ``python tools/check_template_reference_docs.py --check``
     - Template config and built-in template marker drift.
     - Pass after PR-U metadata description fix.
   * - ``python tools/check_template_packaging.py``
     - Repository-source built-in template packaging contracts.
     - Pass.
   * - ``python tools/check_template_source_install.py``
     - Source-install built-in template extraction.
     - Pass.
   * - ``python tools/check_docs_terminology.py --self-check`` and ``--check``
     - Terminology checker regression tests and default page scan.
     - Pass; success may be silent.
   * - ``make docs_terminology_check``
     - Makefile terminology gate.
     - Pass.
   * - ``make test_boundary_check``
     - Pytest boundary guard for templates/tools/test-tree rules.
     - Pass.
   * - Inline navigation/API/landing audit scripts
     - Root sidebar, roadmap pages, old tutorial entries, API reference order, and API overreach.
     - Pass.
   * - EN/ZH Sphinx HTML builds and problematic scans
     - Rendered documentation syntax, inline markup, and raw problematic spans.
       Raw ``**`` scans exclude Sphinx highlighted source-code views under
       ``_modules`` and generated API code pages because those pages intentionally
       display source text and executable examples.
     - Pass.
   * - Multiagent implementation review
     - Human-depth, coverage, migration, and verification review.
     - No unresolved C/I findings.

Remaining gaps
--------------

.. list-table:: Final gap ledger
   :header-rows: 1

   * - Gap
     - Status
     - Evidence
   * - Chinese built-in template metadata descriptions did not mirror the source
       metadata strings required by ``tools/check_template_reference_docs.py``.
     - Fixed in PR-U.
     - ``docs/source/reference/builtin_templates/index_zh.rst`` now mirrors the
       exact ``description`` strings while the surrounding Chinese prose explains
       why these metadata values remain verbatim.
   * - Final all-family role/coverage audit had no durable repository record.
     - Fixed in PR-U.
     - This file plus the PR-U section in ``tutorials_ia.rst``.
   * - PR-R, PR-S, and PR-T were represented in umbrella PR discussion but not
       summarized in the migration log.
     - Fixed in PR-U.
     - ``tutorials_ia.rst`` PR-U handoff section points from the migration log to
       the final audit and summarizes the final slices.
   * - Remaining capability owner, migration, bilingual, API-overreach, or
       navigation gaps.
     - None after PR-U audit.
     - Covered by the matrix and verification list above.
